# Backend - Updated for PostgreSQL
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, abort
import json
import os
import psycopg2
from psycopg2.extras import DictCursor, RealDictCursor
from datetime import datetime, timedelta, date
import re
import uuid
import time
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, FileField, RadioField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
from itsdangerous import URLSafeTimedSerializer
import smtplib
from email.mime.text import MIMEText
from functools import wraps
from urllib.parse import urlparse
import os
from dotenv import load_dotenv
import traceback
import uuid
import logging
from flask import current_app
from flask_mail import Mail
from io import BytesIO
import base64
import requests
from flask_wtf.csrf import CSRFProtect
from authlib.integrations.flask_client import OAuth
from openai_nutrition_final import OpenAINutritionScanner
from flask import send_from_directory
from flask import Response
from garminconnect import Garmin
from flask_apscheduler import APScheduler
from openai import OpenAI
from wtforms.validators import Optional
from smartwatch import smartwatch_bp, garmin_clients, auto_sync_all_garmin_users


logging.basicConfig(level=logging.DEBUG)

# Load environment variables
load_dotenv()
client = OpenAI()
print("=== Environment Variables Debug ===")
print(f"MAIL_SERVER from env: '{os.getenv('MAIL_SERVER')}'")
print(f"MAIL_PORT from env: '{os.getenv('MAIL_PORT')}'")  
print(f"MAIL_USERNAME from env: '{os.getenv('MAIL_USERNAME')}'")
print(f"MAIL_USE_SSL from env: '{os.getenv('MAIL_USE_SSL')}'")
print("=====================================")
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key')
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.zoho.eu')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 465))
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'True') == 'True'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('DEFAULT_MAIL_SENDER')
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,       # Prevents JavaScript access
    SESSION_COOKIE_SECURE=True,         # HTTPS only
    SESSION_COOKIE_SAMESITE='Lax',      # Helps prevent CSRF
    REMEMBER_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_SECURE=True,
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
    SESSION_COOKIE_NAME='your_app_session'
)
app.register_blueprint(smartwatch_bp)
mail = Mail(app)
app.config['OAUTH_PROVIDERS'] = {
    'google': {
        'client_id': os.getenv('GOOGLE_CLIENT_ID'),
        'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
        'server_metadata_url': 'https://accounts.google.com/.well-known/openid-configuration',
        'client_kwargs': {'scope': 'openid email profile'}
    },
    'github': {
        'client_id': os.getenv('GITHUB_CLIENT_ID'),
        'client_secret': os.getenv('GITHUB_CLIENT_SECRET'),
        'authorize_url': 'https://github.com/login/oauth/authorize',
        'access_token_url': 'https://github.com/login/oauth/access_token',
        'userinfo_url': 'https://api.github.com/user',
        'client_kwargs': {'scope': 'user:email'}
    },
    'facebook': {
        'client_id': os.getenv('FACEBOOK_CLIENT_ID'),
        'client_secret': os.getenv('FACEBOOK_CLIENT_SECRET'),
        'authorize_url': 'https://www.facebook.com/v18.0/dialog/oauth',
        'access_token_url': 'https://graph.facebook.com/v18.0/oauth/access_token',
        'userinfo_url': 'https://graph.facebook.com/me?fields=id,name,email',
        'client_kwargs': {'scope': 'email public_profile'}
    }
}

# Initialize extensions
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Sisäänkirjautuminen vaadittu!"
login_manager.login_message_category = 'info'
csrf = CSRFProtect(app)
login_manager.remember_cookie_duration = timedelta(days=30)
login_manager.session_protection = "strong"

# Initialize OAuth
oauth = OAuth(app)
# Create OAuth clients
google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    api_base_url='https://openidconnect.googleapis.com/v1/',
    client_kwargs={'scope': 'openid email profile'}

)
facebook = oauth.register(
    name='facebook',
    client_id=os.getenv('FACEBOOK_CLIENT_ID'),
    client_secret=os.getenv('FACEBOOK_CLIENT_SECRET'),
    access_token_url='https://graph.facebook.com/v18.0/oauth/access_token',
    authorize_url='https://www.facebook.com/v18.0/dialog/oauth',
    api_base_url='https://graph.facebook.com/v18.0/',
    client_kwargs={'scope': 'email public_profile'}
)

github = oauth.register(
    name='github',
    client_id=os.getenv("GITHUB_CLIENT_ID"),
    client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'}
)
scheduler = APScheduler()
garmin_clients = {}
_nutrition_scanner = OpenAINutritionScanner()
def get_scanner():
    return _nutrition_scanner
def normalize_key(key):
    """Normalize food key while preserving non-ASCII characters"""
    if key is None:
        return ""
    # Preserve all Unicode letters and numbers, plus allowed special characters
    normalized = re.sub(r'[^\w\s\-.,%+&]', '', key, flags=re.UNICODE)
    # Collapse multiple spaces and trim
    normalized = re.sub(r'\s+', ' ', normalized).strip().lower()
    return normalized

# Add the safe_float function here
def safe_float(value, default=0.0, min_val=0.001, max_val=10000.0):
    """Safely convert to float with clamping and default handling"""
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    try:
        num = float(value)
        if num < min_val:
            return min_val
        if num > max_val:
            return max_val
        return num
    except ValueError:
        return default

# Database connection using Neon.tech URL
def get_db_connection():
    """
    Returns a psycopg2 connection to the database.
    Chooses local or Neon DB based on DB_ENV environment variable.
    """
    db_env = os.getenv("DB_ENV", "local").lower()  # default to local
    if db_env == "neon":
        DATABASE_URL = os.getenv("NEON_DB_URL")
    else:
        DATABASE_URL = os.getenv("LOCAL_DB_URL")

    if not DATABASE_URL:
        raise ValueError(f"No database URL defined for DB_ENV={db_env}")

    print(f"Connecting to database ({db_env}): {DATABASE_URL.split('@')[-1]}")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        raise
def add_garmin_sync_preferences():
    """Add user preferences for Garmin sync intervals"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            DO $$
            BEGIN
                -- Add sync interval column (in minutes)
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='users' AND column_name='garmin_sync_interval'
                ) THEN
                    ALTER TABLE users ADD COLUMN garmin_sync_interval INTEGER DEFAULT 60;
                END IF;
                
                -- Add auto-sync enabled flag
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='users' AND column_name='garmin_auto_sync_enabled'
                ) THEN
                    ALTER TABLE users ADD COLUMN garmin_auto_sync_enabled BOOLEAN DEFAULT TRUE;
                END IF;
            END
            $$;
        """)
        
        conn.commit()
        print("✅ Garmin sync preference columns added")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error adding columns: {e}")
        
    finally:
        cursor.close()
        conn.close()        
# Initialize database
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            role TEXT NOT NULL DEFAULT 'user',
            reset_token TEXT,
            reset_token_expiration TIMESTAMP,
            tdee REAL,
            weight REAL
        )
    ''')
    # 1.5. OAauth
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS oauth_connections (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        provider TEXT NOT NULL,
        provider_user_id TEXT NOT NULL,
        access_token TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(provider, provider_user_id)
    )
''')
    # Ensure columns exist (safe migration)
    cursor.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='users' AND column_name='tdee'
            ) THEN
                ALTER TABLE users ADD COLUMN tdee REAL;
            END IF;
            
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='users' AND column_name='weight'
            ) THEN
                ALTER TABLE users ADD COLUMN weight REAL;
            END IF;
        END
        $$;
    """)

    # 2. Foods table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS foods (
            key TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            carbs REAL NOT NULL,
            sugars REAL,
            fiber REAL,
            proteins REAL NOT NULL,
            fats REAL NOT NULL,
            saturated REAL,
            salt REAL,
            calories REAL NOT NULL,
            grams REAL,
            entire REAL,
            serving REAL,
            bigserving REAL,
            ean TEXT UNIQUE,
            owner_id INTEGER REFERENCES users(id) ON DELETE CASCADE       
        )
    ''')

    # 3. Food usage
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_usage (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            food_key TEXT NOT NULL REFERENCES foods(key) ON DELETE CASCADE,
            count INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, food_key)
        )
    ''')

    # 4. User sessions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            data TEXT NOT NULL,
            PRIMARY KEY (user_id, date),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # 5. Food templates
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_templates (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, name) -- prevent duplicate names per user
        )
    ''')

    # 6. Food template items
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_template_items (
            id SERIAL PRIMARY KEY,
            template_id INTEGER NOT NULL REFERENCES food_templates(id) ON DELETE CASCADE,
            food_key TEXT NOT NULL REFERENCES foods(key) ON DELETE CASCADE,
            grams REAL NOT NULL
        )
    ''')

    # Add index for performance
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_food_template_items_template_id
        ON food_template_items(template_id)
    ''')

    # 7. Workout templates
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workout_templates (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (created_by, name) -- prevent duplicate names per user
        )
    ''')

    # 8. Workout template exercises
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workout_template_exercises (
            id SERIAL PRIMARY KEY,
            template_id INTEGER NOT NULL REFERENCES workout_templates(id) ON DELETE CASCADE,
            exercise_id INTEGER NOT NULL REFERENCES exercises(id),
            reps INTEGER NOT NULL,
            weight REAL NOT NULL,
            rir REAL,
            comments TEXT
        )
    ''')
    # 9. Garmin Credentials (encrypted storage)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS garmin_connections (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            garmin_email TEXT NOT NULL,
            garmin_session_data TEXT,  -- Stores encrypted session tokens
            last_sync TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 11. Garmin Activities Cache
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS garmin_activities (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            activity_id BIGINT NOT NULL,  -- Garmin's activity ID
            activity_name TEXT,
            activity_type TEXT,
            start_time TIMESTAMP,
            duration_seconds INTEGER,
            distance_meters REAL,
            calories INTEGER,
            avg_hr INTEGER,
            max_hr INTEGER,
            avg_speed REAL,
            elevation_gain REAL,
            date DATE,  -- For easy querying
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, activity_id)
        )
    ''')

    # Create indexes for performance
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_garmin_daily_user_date 
        ON garmin_daily_data(user_id, date DESC)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_garmin_activities_user_date 
        ON garmin_activities(user_id, date DESC)
    ''')    
 # Create admin user if not exists
    admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')
    cursor.execute('SELECT 1 FROM users WHERE email = %s', (admin_email,))
    admin_exists = cursor.fetchone()
    if not admin_exists:
        admin_password = os.getenv('ADMIN_PASSWORD', 'admin_password')
        hashed_password = bcrypt.generate_password_hash(admin_password).decode('utf-8')
        cursor.execute('''
            INSERT INTO users (username, email, password, role)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (email) DO NOTHING
        ''', ('admin', admin_email, hashed_password, 'admin'))
    
    # Check if foods table is empty
    cursor.execute("SELECT COUNT(*) FROM foods")
    if cursor.fetchone()[0] == 0:
        # Insert default food
        cursor.execute('''
            INSERT INTO foods 
            (key, name, carbs, sugars, fiber, proteins, fats, saturated, salt, calories, grams, half, entire, serving, bigserving, ean)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            'broccoli',
            'Broccoli',
            7, 1.5, 2.6, 2.8, 0.4, 0.1, 0.03, 34, 100, 150, 300, 85, None
        ))
    cursor.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name='users' AND column_name='auto_add_workout_calories'
        ) THEN
            ALTER TABLE users ADD COLUMN auto_add_workout_calories BOOLEAN DEFAULT FALSE;
        END IF;
        
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name='users' AND column_name='gender'
        ) THEN
            ALTER TABLE users ADD COLUMN gender TEXT;
        END IF;
    END
    $$;
    """)   
    cursor.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='users' AND column_name='auto_import_garmin_cardio'
            ) THEN
                ALTER TABLE users ADD COLUMN auto_import_garmin_cardio BOOLEAN DEFAULT TRUE;
            END IF;
        END
        $$;
    """)
    add_garmin_sync_preferences()     
    conn.commit()
    cursor.close()
    conn.close()

     
def init_workout_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            muscle_group TEXT NOT NULL,
            description TEXT,
            created_by_admin BOOLEAN DEFAULT TRUE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workout_sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            date DATE NOT NULL,
            muscle_group TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # ========== CARDIO TABLES START HERE ==========
    
    # CREATE CARDIO EXERCISES TABLE
    # CREATE CARDIO EXERCISES TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cardio_exercises (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL DEFAULT 'cardio',
            met_value REAL DEFAULT 5.0,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Check if table is empty before inserting defaults
    cursor.execute("SELECT COUNT(*) FROM cardio_exercises")
    count = cursor.fetchone()[0]
    
    if count == 0:
        cursor.execute("""
            INSERT INTO cardio_exercises (name, type, met_value) VALUES
            ('Juoksu (Data)', 'juoksu', 9.8),
            ('Pyöräily (Data)', 'pyöräily', 8.0),
            ('Sisäpyöräily (Data))', 'pyöräily', 7.0),
            ('Kävely (Data)', 'kävely', 3.5),
            ('Vaellus (Data)', 'vaellus', 6.0),
            ('Uinti (Data)', 'uinti', 6.0),
            ('Crosstrainer (Data)', 'crosstrainer', 5.0),
            ('Soutu (Data)', 'soutulaite', 7.0),
            ('Muu Cardio', 'cardio', 5.0)
        """)
        print("[INIT] Inserted default cardio exercises")
    # CREATE CARDIO SESSIONS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cardio_sessions (
            id SERIAL PRIMARY KEY,
            session_id INTEGER NOT NULL REFERENCES workout_sessions(id) ON DELETE CASCADE,
            cardio_exercise_id INTEGER NOT NULL REFERENCES cardio_exercises(id),
            duration_minutes REAL NOT NULL,
            distance_km REAL,
            avg_pace_min_per_km REAL,
            avg_heart_rate INTEGER,
            max_heart_rate INTEGER,
            watts REAL,
            calories_burned REAL NOT NULL DEFAULT 0,
            notes TEXT,
            garmin_activity_id BIGINT UNIQUE,
            is_saved BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_cardio_sessions_session_id 
        ON cardio_sessions(session_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_cardio_sessions_garmin_activity 
        ON cardio_sessions(garmin_activity_id) 
        WHERE garmin_activity_id IS NOT NULL
    """)
    
    # ========== CARDIO TABLES END HERE ==========

    # Only create workout_sets if 'exercises' and 'workout_sessions' exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workout_sets (
            id SERIAL PRIMARY KEY,
            session_id INTEGER NOT NULL,
            exercise_id INTEGER NOT NULL,
            reps INTEGER NOT NULL,
            weight REAL NOT NULL,
            volume REAL GENERATED ALWAYS AS (reps * weight) STORED,
            rir REAL,
            comments TEXT,
            FOREIGN KEY (session_id) REFERENCES workout_sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (exercise_id) REFERENCES exercises(id)
        )
    """)
    # Add missing columns safely
    try:
        cursor.execute("ALTER TABLE workout_sets ADD COLUMN IF NOT EXISTS rir REAL")
        cursor.execute("ALTER TABLE workout_sets ADD COLUMN IF NOT EXISTS comments TEXT")
        cursor.execute("ALTER TABLE workout_sessions ADD COLUMN IF NOT EXISTS is_saved BOOLEAN DEFAULT FALSE")
        cursor.execute("ALTER TABLE workout_sessions ADD COLUMN IF NOT EXISTS workout_type TEXT DEFAULT 'strength'")
    except Exception as e:
        print(f"[WARNING] Error adding columns: {e}")

    # Add default exercises if table is empty
    default_exercises = [
        # Example: ('Bench Press', 'Chest', 'Barbell bench press exercise')
    ]
    for name, group, desc in default_exercises:
        cursor.execute(
            "INSERT INTO exercises (name, muscle_group, description) "
            "SELECT %s, %s, %s WHERE NOT EXISTS "
            "(SELECT 1 FROM exercises WHERE name = %s)",
            (name, group, desc, name)
        )

    conn.commit()
    cursor.close()
    conn.close()
    print("[INIT] Workout database initialized safely.")

from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if current_user.role != 'admin':
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

# List all news posts (admin)
@app.route('/admin/news')
@login_required
@admin_required
def admin_news_list():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT np.*, u.username 
        FROM news_post np
        JOIN users u ON np.author_id = u.id
        ORDER BY np.created_at DESC
    """)
    posts = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('admin/news_list.html', posts=posts)

# Create news post
@app.route('/admin/news/create', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_news_create():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        icon_class = request.form.get('icon_class', 'fas fa-newspaper')
        icon_color = request.form.get('icon_color', 'text-primary')
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO news_post (title, content, icon_class, icon_color, author_id, is_published)
            VALUES (%s, %s, %s, %s, %s, TRUE)
        """, (title, content, icon_class, icon_color, current_user.id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        flash('News post created successfully!', 'success')
        return redirect(url_for('admin_news_list'))
    
    return render_template('admin/news_form.html', post=None)

# Edit news post
@app.route('/admin/news/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_news_edit(post_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        icon_class = request.form.get('icon_class')
        icon_color = request.form.get('icon_color')
        
        cur.execute("""
            UPDATE news_post 
            SET title = %s, content = %s, icon_class = %s, icon_color = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (title, content, icon_class, icon_color, post_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        flash('News post updated successfully!', 'success')
        return redirect(url_for('admin_news_list'))
    
    # GET request - fetch post data
    cur.execute('SELECT * FROM news_post WHERE id = %s', (post_id,))
    post = cur.fetchone()
    
    cur.close()
    conn.close()
    
    if not post:
        flash('Post not found', 'danger')
        return redirect(url_for('admin_news_list'))
    
    return render_template('admin/news_form.html', post=post)

# Delete news post
@app.route('/admin/news/delete/<int:post_id>', methods=['POST'])
@login_required
@admin_required
def admin_news_delete(post_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute('DELETE FROM news_post WHERE id = %s', (post_id,))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'News post deleted successfully!'})
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500

# Toggle publish status
@app.route('/admin/news/toggle/<int:post_id>', methods=['POST'])
@login_required
@admin_required
def admin_news_toggle(post_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            UPDATE news_post 
            SET is_published = NOT is_published 
            WHERE id = %s
            RETURNING is_published
        """, (post_id,))
        
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'is_published': result[0]})
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500


# Forms (unchanged)
class RegistrationForm(FlaskForm):
    username = StringField(
        'Username',
        validators=[
            DataRequired(message="username_required"),
            Length(min=4, max=20, message="username_length")
        ]
    )
    email = StringField(
        'Email',
        validators=[
            DataRequired(message="email_required"),
            Email(message="email_invalid")
        ]
    )
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(message="password_required")
        ]
    )
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(message="confirm_required"),
            EqualTo('password', message="password_must_match")
        ]
    )
    submit = SubmitField('Register')

    def validate_username(self, username):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s', (username.data,))
        user = cursor.fetchone()
        conn.close()
        if user:
            raise ValidationError('username_error')

    def validate_email(self, email):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = %s', (email.data,))
        user = cursor.fetchone()
        conn.close()
        if user:
            raise ValidationError('email_error')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class UpdateProfileForm(FlaskForm):
    username = StringField(
        'Username',
        validators=[DataRequired(), Length(min=4, max=20)]
    )
    email = StringField(
        'Email',
        validators=[DataRequired(), Email()]
    )

    # Optional fields - safe to access even if DB column doesn't exist
    full_name = StringField('Full Name')
    main_sport = StringField('Main Sport / Activity')
    socials = StringField('(@) Socials')

    # Avatar fields
    avatar_choice = RadioField("Choose Avatar", choices=[], default="default.png", validators=[Optional()])
    avatar_upload = FileField("Or Upload Avatar")

    submit = SubmitField('Update')

    # -------------------------------
    # Validators
    # -------------------------------
    def validate_username(self, username):
        current_username = getattr(current_user, 'username', None)
        if not current_username or username.data == current_username:
            return  # no change, no check needed

        # Check uniqueness in DB
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT id FROM users WHERE username = %s', (username.data,))
            user = cursor.fetchone()
            if user:
                raise ValidationError('username_error')
        finally:
            cursor.close()
            conn.close()

    def validate_email(self, email):
        current_email = getattr(current_user, 'email', None)
        if not current_email or email.data == current_email:
            return  # no change, no check needed

        # Check uniqueness in DB
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT id FROM users WHERE email = %s', (email.data,))
            user = cursor.fetchone()
            if user:
                raise ValidationError('email_error')
        finally:
            cursor.close()
            conn.close()

class RequestResetForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')

# User model
class User(UserMixin):
    def __init__(self, id, username, email, role, tdee=None, weight=None):
        self.id = id
        self.username = username
        self.email = email
        self.role = role
        self.tdee = tdee
        self.weight = weight

    def get_reset_token(self, expires_sec=1800):
        """
        Generate a secure password reset token that expires in `expires_sec` seconds.
        """
        s = URLSafeTimedSerializer(
            secret_key=current_app.config['SECRET_KEY'],
            salt='password-reset-salt'  # namespaced for reset tokens
        )
        return s.dumps({'user_id': self.id})

    # -------------------------------
    # Password reset token verification
    # -------------------------------
    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        """
        Verify a password reset token. Returns user_id if valid, None if invalid/expired.
        """
        s = URLSafeTimedSerializer(
            secret_key=current_app.config['SECRET_KEY'],
            salt='password-reset-salt'
        )
        try:
            data = s.loads(token, max_age=expires_sec)
            return data.get('user_id')
        except Exception:
            return None


# User loader
@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        return User(
            id=user['id'],
            username=user['username'],
            email=user['email'],
            role=user['role'],
            tdee=user.get('tdee'),        # Add TDEE
            weight=user.get('weight')     # Add weight
        )
    return None

# Helper functions
def format_date_finnish(date_str):
    """Format date with Finnish day names"""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        today = datetime.now().date()
        
        weekdays_fi = [
            "Maanantai", "Tiistai", "Keskiviikko", "Torstai", 
            "Perjantai", "Lauantai", "Sunnuntai"
        ]
        
        if date_obj.date() == today:
            return f"Tänään {date_obj.strftime('%d.%m')}"
        elif date_obj.date() == today - timedelta(days=1):
            return f"Eilen {date_obj.strftime('%d.%m')}"
        elif date_obj.date() == today + timedelta(days=1):
            return f"Huomenna {date_obj.strftime('%d.%m')}"
        else:
            weekday_fi = weekdays_fi[date_obj.weekday()]
            return f"{weekday_fi} {date_obj.strftime('%d.%m')}"
    except:
        return date_str
def calculate_calories(carbs, proteins, fats):
    return carbs * 4 + proteins * 4 + fats * 9

def get_foods():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute('SELECT * FROM foods')
    foods = cursor.fetchall()
    conn.close()
    return {food['key']: dict(food) for food in foods}

def get_food_by_key(key):
    normalized_key = normalize_key(key)
    print(f"🔍 Looking up food key: '{key}' → normalized: '{normalized_key}'")
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    try:
        cursor.execute('SELECT * FROM foods WHERE key = %s', (normalized_key,))
        food = cursor.fetchone()
        
        if food:
            print(f"✔️ Found food by exact match: {food['name']}, fiber={food['fiber']}")
            return dict(food)
        
        # Fallback to case-insensitive search if exact match fails
        print("⚠️ No exact match, trying case-insensitive search")
        cursor.execute('SELECT * FROM foods WHERE LOWER(key) = LOWER(%s)', (normalized_key,))
        food = cursor.fetchone()
        
        if food:
            print(f"⚠️ Found by case-insensitive fallback: {food['name']}")
            return dict(food)
        
        # Try searching by name as a last resort
        print("⚠️ No key match, trying name search")
        cursor.execute('SELECT * FROM foods WHERE LOWER(name) = LOWER(%s)', (normalized_key,))
        food = cursor.fetchone()
        
        if food:
            print(f"⚠️ Found by name match: {food['name']}")
            return dict(food)
        
        print(f"❌ Food not found for key: '{normalized_key}'")
        return None
    finally:
        conn.close()

def save_food(food_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO foods 
            (key, name, carbs, sugars, fiber, proteins, fats, saturated, salt, calories, grams, half, entire, serving, bigserving, ean)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (key) DO UPDATE SET
                name = EXCLUDED.name,
                carbs = EXCLUDED.carbs,
                sugars = EXCLUDED.sugars,
                fiber = EXCLUDED.fiber,
                proteins = EXCLUDED.proteins,
                fats = EXCLUDED.fats,
                saturated = EXCLUDED.saturated,
                salt = EXCLUDED.salt,
                calories = EXCLUDED.calories,
                grams = EXCLUDED.grams,
                half = EXCLUDED.half,
                entire = EXCLUDED.entire,
                serving = EXCLUDED.serving,
                bigserving = EXCLUDED.bigserving,
                ean = EXCLUDED.ean
        ''', (
            food_data['key'],
            food_data['name'],
            food_data['carbs'],
            food_data['sugars'],
            food_data['fiber'],
            food_data['proteins'],
            food_data['fats'],
            food_data['saturated'],
            food_data['salt'],
            food_data['calories'],
            food_data['grams'],
            food_data.get('half'),
            food_data.get('entire'),
            food_data.get('serving'),
            food_data.get('bigserving'),
            food_data.get('ean')
        ))
        conn.commit()
    finally:
        conn.close()

def get_food_usage(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute('SELECT food_key, count FROM food_usage WHERE user_id = %s', (user_id,))
    usage = cursor.fetchall()
    conn.close()
    return {row['food_key']: row['count'] for row in usage}

def increment_food_usage(user_id, food_key):
    normalized_key = normalize_key(food_key)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO food_usage (user_id, food_key, count)
            VALUES (%s, %s, 1)
            ON CONFLICT (user_id, food_key) DO UPDATE SET count = food_usage.count + 1
        ''', (user_id, normalized_key))
        conn.commit()
    finally:
        conn.close()

def get_session_history(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute(
        'SELECT date, data FROM user_sessions WHERE user_id = %s',
        (user_id,)
    )
    sessions = cursor.fetchall()
    conn.close()
    return {row['date']: json.loads(row['data']) for row in sessions}

def save_session_history(user_id, session_history):
    # This function is kept for compatibility but not used in PostgreSQL version
    pass

def get_current_session(user_id, date=None):
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT data FROM user_sessions 
            WHERE user_id = %s AND date = %s
        ''', (user_id, date))
        
        result = cursor.fetchone()
        
        if result:
            return json.loads(result[0]), date
        else:
            return [], date
    finally:
        conn.close()

def save_current_session(user_id, eaten_items, date):
    conn = get_db_connection()
    cursor = conn.cursor()
    data_str = json.dumps(eaten_items)
    try:
        cursor.execute('''
            INSERT INTO user_sessions (user_id, date, data)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, date) DO UPDATE SET data = EXCLUDED.data
        ''', (user_id, date, data_str))
        conn.commit()
    finally:
        conn.close()

def calculate_group_breakdown(eaten_items):
    groups = {}
    for item in eaten_items:
        group = item.get('group', 'Ungrouped')
        if group not in groups:
            groups[group] = {
                "items": [],
                "calories": 0,
                "carbs": 0,
                "proteins": 0,
                "fats": 0,
                "saturated": 0,
                "salt": 0
            }
        
        groups[group]["items"].append(item)
        groups[group]["calories"] += item['calories']
        groups[group]["carbs"] += item['carbs']
        groups[group]["proteins"] += item['proteins']
        groups[group]["fats"] += item['fats']
        groups[group]["saturated"] += item.get('saturated', 0)
        groups[group]["salt"] += item.get('salt', 0)
    
    return groups

def calculate_totals(eaten_items):
    total_carbs = sum(item['carbs'] for item in eaten_items)
    total_sugars = sum(item.get('sugars', 0.0) for item in eaten_items)
    total_fiber = sum(item.get('fiber', 0.0) for item in eaten_items)
    total_proteins = sum(item['proteins'] for item in eaten_items)
    total_fats = sum(item['fats'] for item in eaten_items)
    total_saturated = sum(item.get('saturated', 0.0) for item in eaten_items)
    total_salt = sum(item.get('salt', 0.0) for item in eaten_items)
    total_calories = sum(item['calories'] for item in eaten_items)
    
    return {
        "calories": total_calories,
        "carbs": total_carbs,
        "sugars": total_sugars,
        "fiber": total_fiber,
        "proteins": total_proteins,
        "fats": total_fats,
        "saturated": total_saturated,
        "salt": total_salt
    }

def get_daily_totals(day_data):
    # Handle case where day_data might be None or empty
    if not day_data:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        
    total_calories = sum(item['calories'] for item in day_data)
    total_proteins = sum(item['proteins'] for item in day_data)
    total_fats = sum(item['fats'] for item in day_data)
    total_carbs = sum(item['carbs'] for item in day_data)
    total_sugars = sum(item['sugars'] for item in day_data)
    total_salt = sum(item.get('salt', 0.0) for item in day_data)
    total_saturated = sum(item.get('saturated', 0.0) for item in day_data)
    total_fiber = sum(item.get('fiber', 0.0) for item in day_data)
    
    return (
        total_calories,
        total_proteins,
        total_fats,
        total_carbs,
        total_sugars,
        total_salt,
        total_saturated,
        total_fiber
    )

def format_date(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return date_obj.strftime("%A (%d.%m.%Y)")

# Email functions
def send_reset_email(user):
    """
    Sends a password reset email using Zoho SMTP (SSL, port 465)
    """
    token = user.get_reset_token()

    body = f"""Hei {user.username},

Nollataksesi salasanasi, klikkaa alla olevaa linkkiä:
{url_for('reset_token', token=token, _external=True)}

Jos et ole pyytänyt salasanan nollausta, voit jättää tämän viestin huomioimatta.
"""
    msg = MIMEText(body)
    msg['Subject'] = 'Salasanan nollaus / Password Reset'
    msg['From'] = current_app.config['MAIL_USERNAME']
    msg['To'] = user.email

    try:
        # Enable debug output
        current_app.logger.info(f"Attempting to send email using server: {current_app.config['MAIL_SERVER']}:{current_app.config['MAIL_PORT']}")
        current_app.logger.info(f"Username: {current_app.config['MAIL_USERNAME']}")
        
        with smtplib.SMTP_SSL(
            current_app.config['MAIL_SERVER'],
            current_app.config['MAIL_PORT']
        ) as server:
            # Enable SMTP debug output
            server.set_debuglevel(1)  # Add this for detailed SMTP logs
            
            current_app.logger.info("SMTP connection established")
            
            server.login(
                current_app.config['MAIL_USERNAME'],
                current_app.config['MAIL_PASSWORD']
            )
            
            current_app.logger.info("SMTP authentication successful")
            
            server.send_message(msg)
            current_app.logger.info(f"Email sent successfully to {user.email}")
            
        return True
    except smtplib.SMTPAuthenticationError as e:
        current_app.logger.error(f"SMTP Authentication error: {e}")
        return False
    except smtplib.SMTPException as e:
        current_app.logger.error(f"SMTP error: {e}")
        return False
    except Exception as e:
        current_app.logger.error(f"General error sending email to {user.email}: {e}")
        return False

# Admin decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if current_user.role != 'admin':
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

def update_food_keys_normalization():
    print("Normalizing food keys to new standard...")
    conn = get_db_connection()
    cursor = conn.cursor()
    updated_count = 0
    
    try:
        cursor.execute("SELECT key, name FROM foods")
        foods = cursor.fetchall()
        
        for old_key, name in foods:
            new_key = normalize_key(old_key)
            
            if old_key != new_key:
                print(f"Updating key: {old_key} -> {new_key}")
                updated_count += 1
                
                # Update foods table
                cursor.execute(
                    "UPDATE foods SET key = %s WHERE key = %s",
                    (new_key, old_key)
                )
                
                # Update food_usage table
                cursor.execute(
                    "UPDATE food_usage SET food_key = %s WHERE food_key = %s",
                    (new_key, old_key)
                )
        
        conn.commit()
        print(f"Food keys normalized successfully. Updated {updated_count} keys.")
    except Exception as e:
        print(f"Error normalizing keys: {e}")
        conn.rollback()
    finally:
        conn.close()
def calculate_calorie_status(calorie_difference):
    abs_diff = abs(calorie_difference)
    if abs_diff <= 50:
        return {
            'status': 'maintaining',
            'class': 'status-maintain',
            'display': f"{abs_diff:.0f}"
        }
    elif calorie_difference > 0:
        return {
            'status': 'calories over',
            'class': 'status-gain', 
            'display': f"{abs_diff:.0f}"
        }
    else:
        return {
            'status': 'calories left',
            'class': 'status-loss',
            'display': f"{abs_diff:.0f}"
        }
    
# Initialize database and migrate data
init_db()
update_food_keys_normalization()


def normalize_food_keys():
    print("Normalizing food keys...")
    conn = get_db_connection()
    cursor = conn.cursor()
    update_food_keys_normalization()

    try:
        # Get all foods
        cursor.execute("SELECT key, name FROM foods")
        foods = cursor.fetchall()
        
        for key, name in foods:
            # Create normalized key
            normalized_key = re.sub(r'[^a-z0-9_]', '', name.lower().replace(' ', '_'))
            
            if key != normalized_key:
                print(f"Updating key: {key} -> {normalized_key}")
                
                # Update foods table
                cursor.execute(
                    "UPDATE foods SET key = %s WHERE key = %s",
                    (normalized_key, key)
                )
                
                # Update food_usage table
                cursor.execute(
                    "UPDATE food_usage SET food_key = %s WHERE food_key = %s",
                    (normalized_key, key)
                )
        
        conn.commit()
        print("Food keys normalized successfully")
    except Exception as e:
        print(f"Error normalizing keys: {e}")
        conn.rollback()
    finally:
        conn.close()

# Routes
def generate_date_range(center_date_str, range_days=3):
    """Generate a list of dates centered around the given date"""
    from datetime import datetime, timedelta
    
    # Parse the center date
    if isinstance(center_date_str, str):
        center_date = datetime.strptime(center_date_str, "%Y-%m-%d")
    else:
        center_date = center_date_str
    
    dates = []
    for i in range(-range_days, range_days + 1):
        date_obj = center_date + timedelta(days=i)
        date_str = date_obj.strftime("%Y-%m-%d")
        formatted_date = format_date_finnish(date_str)
        dates.append((date_str, formatted_date))
    
    return dates

@app.route('/load_more_dates', methods=['POST'])
@login_required
def load_more_dates():
    """Load more dates for the date selector"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        direction = data.get('direction')
        current_dates = data.get('current_dates', [])
        
        if not current_dates:
            return jsonify({'error': 'No current dates provided'}), 400
            
        if direction == 'past':
            # Get the earliest date - extract just the date string part
            earliest_date_data = current_dates[0]
            earliest_date_str = earliest_date_data[0] if isinstance(earliest_date_data, list) else earliest_date_data
            
            earliest_date = datetime.strptime(earliest_date_str, "%Y-%m-%d")
            
            new_dates = []
            for i in range(1, 4):  # Add 3 dates before
                date_obj = earliest_date - timedelta(days=i)
                date_str = date_obj.strftime("%Y-%m-%d")
                formatted_date = format_date_finnish(date_str)
                new_dates.insert(0, [date_str, formatted_date])
                
            return jsonify({
                'success': True,
                'new_dates': new_dates,
                'position': 'prepend'
            })
            
        elif direction == 'future':
            # Get the latest date - extract just the date string part
            latest_date_data = current_dates[-1]
            latest_date_str = latest_date_data[0] if isinstance(latest_date_data, list) else latest_date_data
            
            latest_date = datetime.strptime(latest_date_str, "%Y-%m-%d")
            
            new_dates = []
            for i in range(1, 4):  # Add 3 dates after
                date_obj = latest_date + timedelta(days=i)
                date_str = date_obj.strftime("%Y-%m-%d")
                formatted_date = format_date_finnish(date_str)
                new_dates.append([date_str, formatted_date])
                
            return jsonify({
                'success': True,
                'new_dates': new_dates,
                'position': 'append'
            })
        else:
            return jsonify({'error': 'Invalid direction'}), 400
            
    except Exception as e:
        print(f"Error in load_more_dates: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
@app.route('/')
@login_required
def index():
    # ✅ UPDATED: Use dynamic TDEE calculation instead of static current_user.tdee
    current_weight = current_user.weight or 0
    
    # Get current TDEE including workout adjustments
    tdee_data = get_user_current_tdee(current_user.id)
    current_tdee = tdee_data["daily_tdee"]  # This includes workout calories if enabled

    # Get session data
    eaten_items, current_date = get_current_session(current_user.id)
    totals = calculate_totals(eaten_items)
    food_usage = get_food_usage(current_user.id)
    group_breakdown = calculate_group_breakdown(eaten_items)

    # Generate initial dates for selector - 3 days past, today, 3 days future
    dates = generate_date_range(current_date, range_days=3)

    current_date_formatted = format_date(current_date)

    # Ensure each item has a 'key' property
    for group, group_data in group_breakdown.items():
        for item in group_data['items']:
            if 'key' not in item:
                item['key'] = item['id']

    return render_template(
        'index.html',
        eaten_items=eaten_items,
        totals=totals,
        current_date=current_date,
        current_date_formatted=current_date_formatted,
        dates=dates,
        food_usage=food_usage,
        group_breakdown=group_breakdown,
        current_tdee=current_tdee,
        current_weight=current_weight,
        # ✅ NEW: Pass additional TDEE info for display
        tdee_data=tdee_data  # Contains base_tdee, workout_calories, daily_tdee, auto_enabled
    )
@app.route("/delete-data", methods=["GET", "POST"])
def delete_data():
    if request.method == "POST":
        user_id = request.form.get("user_id")  # Or however FB sends it
        # TODO: implement deletion logic from your DB
        # e.g., remove user account + related data
        return jsonify({"status": "success", "message": f"Data deleted for user {user_id}"})
    
    # If accessed via browser, just show instructions
    return render_template("delete_data.html")
@app.route('/terms')
def terms():
    return render_template('terms.html')
@app.route('/privacy')
def privacy():
    return render_template('privacy.html')
@app.route('/custom_food')
@login_required
def custom_food():
    return render_template('custom_food.html')
@app.route('/activity')
@login_required
def activity():
    return render_template('activity.html')

# Authentication routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        email = form.email.data.lower()  # normalize to lowercase
        username = form.username.data

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO users (username, email, password) VALUES (%s, %s, %s)',
                (username, email, hashed_password)
            )
            conn.commit()
            flash('register_success', 'success')
            return redirect(url_for('login'))
        except psycopg2.IntegrityError as e:
            flash('register_error', 'danger')
            app.logger.error(f"Registration error: {e}")
        finally:
            conn.close()
    
    return render_template('register.html', title='Register', form=form)
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower()

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        conn.close()

        if user and bcrypt.check_password_hash(user['password'], form.password.data):
            user_obj = User(
                id=user['id'],
                username=user['username'],
                email=user['email'],
                role=user['role']
            )
            
            # ✅ Make session permanent based on "remember me"
            login_user(user_obj, remember=form.remember.data)
            
            # ✅ NEW: Make session permanent
            if form.remember.data:
                session.permanent = True
            
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('login_failed', 'danger')

    return render_template('login.html', title='Login', form=form)


@app.route('/debug_foods')
def debug_foods():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute('SELECT key, name FROM foods')
    foods = cursor.fetchall()
    conn.close()
    
    return jsonify([{'key': f['key'], 'name': f['name']} for f in foods])

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


from werkzeug.utils import secure_filename
from PIL import Image
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

import json

LEVEL_CAP = 999

def xp_to_next_level(level: int, base_xp: int = 120, exp: float = 1.72) -> int:
    """
    XP required to advance from `level` to `level + 1`.
    """
    if level >= LEVEL_CAP:
        return 10**12  # effectively unreachable
    return max(50, int(round(base_xp * (level ** exp))))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = UpdateProfileForm()
    print(f"Request method: {request.method}")
    predefined_avatars = ['default.png'] + [f'avatar{i}.png' for i in range(1, 20)]
    form.avatar_choice.choices = [(avatar, avatar.split('.')[0].capitalize()) for avatar in predefined_avatars]
    print(f"Request method: {request.method}")

    if request.method == 'POST':
        if not form.validate_on_submit():
            for field, errors in form.errors.items():
                print(f"  Field '{field}': {errors}")
        print("="*60)
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)

    current_weight = None
    current_tdee = None
    current_avatar = 'default.png'
    extra_columns_exist = False
    role = getattr(current_user, 'role', 'user')
    tdee_data = get_user_current_tdee(current_user.id)
    
    # XP/Level defaults
    user_level = 1
    user_xp = 0
    xp_to_next = 100
    user_socials = "[]"  # Initialize here at the top

    try:
        # Check for extra columns including privacy controls
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name IN ('full_name','main_sport','socials','show_full_name','show_main_sport','show_health_metrics','show_socials')
        """)
        columns = [row['column_name'] for row in cursor.fetchall()]
        extra_columns_exist = any(col in columns for col in ['full_name', 'main_sport', 'socials'])

        # Build select query with level/xp and privacy controls
        select_cols = ['username', 'email', 'weight', 'tdee', 'avatar'] + columns
        
        # Check if level and xp_points columns exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name IN ('level', 'xp_points')
        """)
        level_columns = [row['column_name'] for row in cursor.fetchall()]
        
        if 'level' in level_columns:
            select_cols.append('level')
        if 'xp_points' in level_columns:
            select_cols.append('xp_points')
        
        cursor.execute(f"SELECT {', '.join(select_cols)} FROM users WHERE id = %s", (current_user.id,))
        user_data = cursor.fetchone()

        if user_data:
            current_weight = user_data.get('weight')
            current_tdee = user_data.get('tdee')
            current_avatar = user_data.get('avatar') or 'default.png'
            
            # Extract level and XP
            user_level = user_data.get('level', 1) or 1
            user_xp = user_data.get('xp_points', 0) or 0
            
            # Calculate XP needed for next level
            xp_to_next = xp_to_next_level(user_level) if callable(globals().get('xp_to_next_level')) else 100
            
            # Get socials data
            user_socials = user_data.get('socials') or "[]"
            if isinstance(user_socials, (list, dict)):
                user_socials = json.dumps(user_socials)

        if form.validate_on_submit():
            # Handle email lowercase
            email_lower = form.email.data.lower()

            # Avatar handling
            avatar_filename = current_avatar
            if hasattr(form, 'avatar_upload') and form.avatar_upload.data:
                file = form.avatar_upload.data
                if file and allowed_file(file.filename):
                    timestamp = str(int(time.time()))
                    filename = secure_filename(file.filename)
                    name, ext = os.path.splitext(filename)
                    unique_filename = f"{name}_{timestamp}{ext}"
                    filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
                    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                    file.save(filepath)
                    img = Image.open(filepath)
                    img.thumbnail((200, 200))
                    img.save(filepath)
                    avatar_filename = unique_filename
                else:
                    flash('Invalid file type. Please upload PNG, JPG, JPEG, or GIF.', 'danger')
            elif hasattr(form, 'avatar_choice') and form.avatar_choice.data:
                avatar_filename = form.avatar_choice.data if form.avatar_choice.data in predefined_avatars else 'default.png'

            # Build update query dynamically
            update_query = "UPDATE users SET username = %s, email = %s, avatar = %s"
            update_params = [form.username.data, email_lower, avatar_filename]

            # Handle privacy controls
            privacy_fields = ['show_full_name', 'show_main_sport', 'show_health_metrics', 'show_socials']
            for privacy_field in privacy_fields:
                if privacy_field in columns:
                    # Get checkbox value (True if checked, False if not)
                    privacy_value = request.form.get(privacy_field) == 'on'
                    update_query += f", {privacy_field} = %s"
                    update_params.append(privacy_value)

            for col in columns:
                if col in privacy_fields:
                    continue  # Already handled above
                elif col == "socials":
                    # Get socials from form field (uses name="socials")
                    socials_json = request.form.get("socials", "[]")
                    
                    
                    try:
                        socials_data = json.loads(socials_json)
                        
                    except json.JSONDecodeError as e:
                       
                        socials_data = []
                    
                    update_query += ", socials = %s"
                    update_params.append(json.dumps(socials_data))

            update_query += " WHERE id = %s"
            update_params.append(current_user.id)



            cursor.execute(update_query, tuple(update_params))
            conn.commit()
            cursor.execute(f"SELECT {', '.join(select_cols)} FROM users WHERE id = %s", (current_user.id,))
            user_data = cursor.fetchone()
            if user_data:
                form.socials.data = user_data.get('socials', '[]')

                return redirect(
                        url_for('profile', toast_msg='Profiili päivitetty!', toast_cat='success')
                    )

        elif user_data:
            # Pre-fill form
            form.username.data = user_data.get('username', '')
            form.email.data = user_data.get('email', '')
            form.socials.data = user_data.get('socials', '[]')
            
            for col in columns:
                if col == "socials":
                    continue  # Skip - we handle this separately via user_socials variable
                elif hasattr(form, col):
                    getattr(form, col).data = user_data.get(col, '')
            form.avatar_choice.data = current_avatar if current_avatar in predefined_avatars else 'default.png'

    except psycopg2.IntegrityError:
        flash('Username or email already taken', 'danger')
    except Exception:
        import traceback
        print(traceback.format_exc())
        flash('An unexpected error occurred.', 'danger')
    finally:
        cursor.close()
        conn.close()

    return render_template(
        'profile.html',
        title='Profile',
        form=form,
        current_weight=current_weight,
        current_tdee=current_tdee,
        current_avatar=current_avatar,
        role=role,
        extra_columns_exist=extra_columns_exist,
        predefined_avatars=predefined_avatars,
        tdee_data=tdee_data,
        user_level=user_level,
        user_xp=user_xp,
        xp_to_next_level=xp_to_next,
        viewed_user=None,
        is_owner=True,
        user_socials=user_socials
    )


@app.route('/profile/<int:user_id>', methods=['GET'])
@login_required
def view_profile(user_id):
    """Render a public profile (view-only) for any user"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    extra_columns_exist = False
    role = 'user'
    tdee_data = None
    predefined_avatars = ['default.png'] + [f'avatar{i}.png' for i in range(1, 20)]
    current_avatar = 'default.png'
    user_level = 1
    user_xp = 0
    xp_to_next = 100
    current_weight = None
    current_tdee = None

    try:
        # Check for extra columns including privacy controls
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name IN ('full_name','main_sport','socials','show_full_name','show_main_sport','show_health_metrics','show_socials')
        """)
        columns = [row['column_name'] for row in cursor.fetchall()]
        extra_columns_exist = any(col in columns for col in ['full_name', 'main_sport', 'socials'])

        # Build select query with privacy controls
        select_cols = ['id', 'username', 'email', 'weight', 'tdee', 'avatar', 'role'] + columns
        
        # Check if level and xp_points columns exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name IN ('level', 'xp_points')
        """)
        level_columns = [row['column_name'] for row in cursor.fetchall()]
        
        if 'level' in level_columns:
            select_cols.append('level')
        if 'xp_points' in level_columns:
            select_cols.append('xp_points')

        # Find requested user with all data
        cursor.execute(f"SELECT {', '.join(select_cols)} FROM users WHERE id = %s", (user_id,))
        user_data = cursor.fetchone()

        if not user_data:
            flash('User not found', 'danger')
            return redirect(url_for('index'))

        # Avatar
        current_avatar = user_data.get('avatar') or 'default.png'
        # Level/xp logic
        user_level = user_data.get('level', 1) or 1
        user_xp = user_data.get('xp_points', 0) or 0
        xp_to_next = xp_to_next_level(user_level) if callable(globals().get('xp_to_next_level')) else 100
        # Metrics (only if user allows it)
        if user_data.get('show_health_metrics', False) or user_id == current_user.id:
            current_weight = user_data.get('weight')
            current_tdee = user_data.get('tdee')
        role = user_data.get('role', 'user')
        
        # TDEE data only if health metrics are public or it's own profile
        if user_data.get('show_health_metrics', False) or user_id == current_user.id:
            tdee_data = get_user_current_tdee(user_data['id']) if callable(globals().get('get_user_current_tdee')) else None

        # Create dummy form for template compatibility
        form = UpdateProfileForm()
        form.avatar_choice.choices = [(avatar, avatar.split('.')[0].capitalize()) for avatar in predefined_avatars]
        
        # Pre-fill form data
        form.username.data = user_data.get('username', '')
        form.email.data = user_data.get('email', '')
        for col in columns:
            if col.startswith('show_'):
                continue  # Skip privacy controls
            elif col == "socials":
                # Parse socials JSON safely - CORRECTED to use 'socials' (matches HTML name attribute)
                socials_json = request.form.get("socials", "[]")
                
            elif hasattr(form, col):
                getattr(form, col).data = user_data.get(col, '')

    except Exception as e:
        print(f"Error loading profile: {e}")
        flash('Error loading profile', 'danger')
        return redirect(url_for('index'))
    finally:
        cursor.close()
        conn.close()

    return render_template(
        'profile.html',
        title='Profile',
        form=form,
        current_weight=current_weight,
        current_tdee=current_tdee,
        current_avatar=current_avatar,
        role=role,
        extra_columns_exist=extra_columns_exist,
        predefined_avatars=predefined_avatars,
        tdee_data=tdee_data,
        user_level=user_level,
        user_xp=user_xp,
        xp_to_next_level=xp_to_next,
        viewed_user=user_data,
        is_owner=(user_id == current_user.id)
    )
@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    form = RequestResetForm()
    if form.validate_on_submit():
        email = form.email.data.lower()  # normalize to lowercase

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        conn.close()

        if user:
            user_obj = User(
                id=user['id'],
                username=user['username'],
                email=user['email'],
                role=user['role']
            )
            if send_reset_email(user_obj):
                flash('Sähköposti lähetetty! ohjeet salasanan uusimiseen tulossa!', 'info')
            else:
                flash('Sähköpostia ei voi lähettää. Kokeile myöhemmin uudelleen', 'danger')
        else:
            flash('Käyttäjää ei löydy tuolla sähköpostilla', 'warning')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user_id = User.verify_reset_token(token)
    if user_id is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        flash('User not found', 'warning')
        return redirect(url_for('reset_request'))
    
    user_obj = User(
        id=user['id'],
        username=user['username'],
        email=user['email'],
        role=user['role']
    )
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET password = %s WHERE id = %s', 
            (hashed_password, user_obj.id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('login', toast_msg='Salasana on päivitetty! voit kirjautua sisään uudella', toast_cat='success'))
    return render_template('reset_token.html', title='Reset Password', form=form)

@app.route('/get_favourite_grams', methods=['POST'])
@login_required
def get_favourite_grams():
    try:
        food_id = request.form.get('food_id')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT last_grams FROM user_food_preferences 
            WHERE user_id = %s AND food_id = %s
        ''', (current_user.id, food_id))
        result = cursor.fetchone()
        conn.close()
        
        return jsonify({
            'success': True,
            'last_grams': result[0] if result else None   # ✅ use index
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    
from flask import request, jsonify
from flask_login import login_required, current_user
from psycopg2.extras import DictCursor

@app.route('/search_foods', methods=['POST'])
@login_required
def search_foods():
    query = request.form.get('query', '').strip().lower()
    limit = int(request.form.get('limit', 25))
    offset = int(request.form.get('offset', 0))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)

    user_id = current_user.id
    is_admin = current_user.role == 'admin'

    # Visibility clause & parameters
    if is_admin:
        visibility_clause = "TRUE"
        params = [user_id]  # for user usage join
    else:
        visibility_clause = "(f.owner_id IS NULL OR f.owner_id = %s)"
        params = [user_id, user_id]  # one for user usage JOIN, one for visibility

    if not query:
        sql = f"""
            SELECT f.*, 
                   COALESCE(u.count, 0) AS usage,
                   COALESCE(g.count, 0) AS global_usage
            FROM foods f
            LEFT JOIN food_usage u ON f.key = u.food_key AND u.user_id = %s
            LEFT JOIN food_usage_global g ON f.key = g.food_key
            WHERE {visibility_clause}
            ORDER BY usage DESC, global_usage DESC, name ASC
            LIMIT %s OFFSET %s
        """
        cursor.execute(sql, params + [limit, offset])
    else:
        # Split query into separate keywords
        words = query.split()

        # Build AND conditions like:
        # LOWER(f.name) LIKE %word1% AND LOWER(f.name) LIKE %word2% ...
        word_conditions = " AND ".join([f"LOWER(f.name) LIKE %s" for _ in words])
        word_params = [f"%{w}%" for w in words]

        sql = f"""
            SELECT f.*, 
                   COALESCE(u.count, 0) AS usage,
                   COALESCE(g.count, 0) AS global_usage
            FROM foods f
            LEFT JOIN food_usage u ON f.key = u.food_key AND u.user_id = %s
            LEFT JOIN food_usage_global g ON f.key = g.food_key
            WHERE {visibility_clause}
              AND (
                    {word_conditions}
                    OR f.ean = %s
                  )
            ORDER BY 
                usage DESC,
                global_usage DESC,
                name ASC
            LIMIT %s OFFSET %s
        """
        cursor.execute(sql, params + word_params + [query, limit, offset])

    foods = cursor.fetchall()
    conn.close()

    result = []
    for f in foods:
        d = {
            "id": f.get("id") or f.get("key"),
            "name": f.get("name"),
            "calories": f.get("calories"),
            "serving_size": f.get("serving"),
            "half_size": f.get("half"),
            "entire_size": f.get("entire"),
            "bigserving_size": f.get("bigserving"),
            "usage": f.get("usage"),
            "ean": f.get("ean"),
            "groups": ["breakfast", "lunch", "dinner", "snack"],
        }
        result.append(d)

    return jsonify(result)

    

@app.route('/get_food_details', methods=['POST'])
@login_required
def get_food_details():
    try:
        food_id = request.form.get('food_id')
        unit_type = request.form.get('unit_type')
        units = request.form.get('units')
        
        # Normalize key
        normalized_key = normalize_key(food_id)
        print(f"\n=== /get_food_details REQUEST ===")
        print(f"Raw food_id: '{food_id}'")
        print(f"Normalized key: '{normalized_key}'")

        # Fetch food from DB with visibility check
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)

        if current_user.role == 'admin':
            cursor.execute('SELECT * FROM foods WHERE key = %s', (normalized_key,))
        else:
            cursor.execute('''
                SELECT * FROM foods
                WHERE key = %s AND (owner_id IS NULL OR owner_id = %s)
            ''', (normalized_key, current_user.id))

        food = cursor.fetchone()
        conn.close()

        if not food:
            print(f"❌ Food not found or not visible: '{normalized_key}'")
            return jsonify({'error': 'Food not found or not accessible'}), 404

        # Default to grams if no units provided
        if not units or float(units) <= 0:
            units = 100
            unit_type = 'grams'
        else:
            units = float(units)

        # Convert units to grams
        grams = units  # Default to grams
        if unit_type == 'half' and food.get('half') is not None:
            grams = units * food['half']
        elif unit_type == 'entire' and food.get('entire') is not None:
            grams = units * food['entire']
        elif unit_type == 'serving' and food.get('serving') is not None:
            grams = units * food['serving']
        elif unit_type == 'bigserving' and food.get('bigserving') is not None:
            grams = units * food['bigserving']
        else:
            unit_type = 'grams'

        factor = grams / 100
        carbs = food['carbs'] * factor
        proteins = food['proteins'] * factor
        fats = food['fats'] * factor
        salt = food.get('salt', 0.0) * factor
        calories = food['calories'] * factor

        print(f"✅ Found food: {food['name']}")
        print(f"Calculated nutrition for {grams}g:")
        print(f"- Calories: {calories}")
        print(f"- Carbs: {carbs}")
        print(f"- Proteins: {proteins}")
        print(f"- Fats: {fats}")

        return jsonify({
            "success": True,
            "name": food["name"],
            "units": units,
            "unit_type": unit_type,
            "calories": calories,
            "proteins": proteins,
            "carbs": carbs,
            "fats": fats,
            "salt": salt,
            "serving_size": food.get("serving"),
            "half_size": food.get("half"),
            "entire_size": food.get("entire"),
            "bigserving_size": food.get("bigserving")
        })

    except Exception as e:
        print(f"🔥 Error in get_food_details: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/log_food', methods=['POST'])
@login_required
def log_food():
    try:
        user_id = current_user.id
        food_id = request.form.get('food_id')
        normalized_key = normalize_key(food_id)
        unit_type = request.form.get('unit_type')
        units = float(request.form.get('units'))
        meal_group = request.form.get('meal_group')
        date = request.form.get('date', datetime.now().strftime("%Y-%m-%d"))

                # Store the last used grams for this food
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_food_preferences (user_id, food_id, last_grams)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, food_id) 
            DO UPDATE SET last_grams = EXCLUDED.last_grams
        ''', (current_user.id, food_id, units))
        conn.commit()
        conn.close()

        print(f"Logging food: original='{food_id}', normalized='{normalized_key}'")
        
        food = get_food_by_key(normalized_key)
        if not food:
            print(f"Food not found: '{normalized_key}'")
            return jsonify({'error': 'Food not found'}), 404

        # Convert units to grams
        if unit_type == 'grams':
            grams = units
        elif unit_type == 'half' and food.get('half') is not None:
            grams = units * food['half']
        elif unit_type == 'entire' and food.get('entire') is not None:
            grams = units * food['entire']
        elif unit_type == 'serving' and food.get('serving') is not None:
            grams = units * food['serving']
        elif unit_type == 'bigserving' and food.get('bigserving') is not None:
            grams = units * food['bigserving']       
        else:
            grams = units
            unit_type = 'grams'
        
        factor = grams / 100
        carbs = food['carbs'] * factor
        proteins = food['proteins'] * factor
        fats = food['fats'] * factor
        salt = safe_float(food.get('salt')) * factor
        sugars = safe_float(food.get('sugars')) * factor
        fiber = safe_float(food.get('fiber')) * factor
        saturated = safe_float(food.get('saturated')) * factor
        calories = food['calories'] * factor

        item = {
            "id": str(uuid.uuid4()),
            "name": food['name'],
            "key": food['key'],
            "grams": grams,
            "units": units,
            "unit_type": unit_type,
            "carbs": carbs,
            "sugars": sugars,
            "fiber": fiber,
            "proteins": proteins,
            "fats": fats,
            "saturated": saturated,
            "salt": salt,
            "calories": calories,
            "group": meal_group
        }

        # Update session
        eaten_items, current_date = get_current_session(user_id, date)
        eaten_items.append(item)
        save_current_session(user_id, eaten_items, date)

        # Update food usage
        increment_food_usage(user_id, food['key'])

        # Return updated session, totals and breakdown
        totals = calculate_totals(eaten_items)
        group_breakdown = calculate_group_breakdown(eaten_items)
        
        return jsonify({
            'session': eaten_items,
            'totals': totals,
            'breakdown': group_breakdown,
            'new_item': item,  # Add the new item for optimized updates
            'is_mobile': request.headers.get('User-Agent').lower().find('mobile') != -1
        })

    except Exception as e:
        print(f"Error in log_food: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
@app.route('/update_session', methods=['POST'])
@login_required
def update_session():
    user_id = current_user.id
    date_str = request.form.get('date', datetime.now().strftime("%Y-%m-%d"))
    
    # ✅ UPDATED: Use dynamic TDEE calculation for specific date
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        target_date = datetime.now().date()
    
    # Get TDEE for the specific date (includes workout adjustments if enabled)
    tdee_data = get_user_current_tdee(user_id, target_date)
    current_tdee = tdee_data["daily_tdee"]
    
    eaten_items, current_date = get_current_session(user_id, date_str)
    totals = calculate_totals(eaten_items)
    group_breakdown = calculate_group_breakdown(eaten_items)
    current_date_formatted = format_date(current_date)
    
    # Calculate calorie difference and status
    calorie_difference = current_tdee - totals['calories']  # TDEE - calories consumed
    status_dict = calculate_calorie_status(calorie_difference)
    calorie_status = status_dict['status']
    calorie_status_class = status_dict['class']
    calorie_difference_str = status_dict['display']
    
    return jsonify({
        'session': eaten_items,
        'totals': totals,
        'breakdown': group_breakdown,
        'current_date_formatted': current_date_formatted,
        'calorie_difference': calorie_difference_str,
        'calorie_status': calorie_status,
        'calorie_status_class': calorie_status_class,
        # ✅ NEW: Include TDEE breakdown in response
        'tdee_data': {
            'base_tdee': tdee_data["base_tdee"],
            'garmin_source': tdee_data.get("garmin_source"),
            'daily_tdee': tdee_data["daily_tdee"],
            'auto_enabled': tdee_data.get("auto_enabled", False)
        }
    })

@app.route('/delete_food', methods=['POST'])
@admin_required
def delete_food():
    food_id = request.form.get('food_id')  # Get raw food ID without normalization
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Delete usage first
        cursor.execute('DELETE FROM food_usage WHERE food_key = %s', (food_id,))
        # Then delete food
        cursor.execute('DELETE FROM foods WHERE key = %s', (food_id,))
        conn.commit()
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500
    finally:
        conn.close()

@app.route('/delete_item', methods=['POST'])
@login_required
def delete_item():
    user_id = current_user.id
    item_id = request.form.get('item_id')
    date = request.form.get('date', datetime.now().strftime("%Y-%m-%d"))
    
    eaten_items, current_date = get_current_session(user_id, date)
    eaten_items = [item for item in eaten_items if item.get('id') != item_id]
        
    save_current_session(user_id, eaten_items, date)
    
    totals = calculate_totals(eaten_items)
    group_breakdown = calculate_group_breakdown(eaten_items)
    current_date_formatted = format_date(current_date)
    return jsonify({
        'session': eaten_items,
        'totals': totals,
        'current_date_formatted': current_date_formatted,
        'breakdown': group_breakdown
    })

@app.route('/clear_session', methods=['POST'])
@login_required
def clear_session():
    user_id = current_user.id
    date = request.form.get('date', datetime.now().strftime("%Y-%m-%d"))
    save_current_session(user_id, [], date)
    group_breakdown = calculate_group_breakdown([])
    current_date_formatted = format_date(date)
    return jsonify({
        'session': [],
        'totals': calculate_totals([]),
        'current_date_formatted': current_date_formatted,
        'breakdown': group_breakdown
    })


# ===== MOVE/COPY FUNCTIONALITY ===== #
@app.route('/move_items', methods=['POST'])
@login_required
def move_items():
    return move_or_copy_items_optimized(remove_original=True)

@app.route('/copy_items', methods=['POST'])
@login_required
def copy_items():
    return move_or_copy_items_optimized(remove_original=False)

def move_or_copy_items_optimized(remove_original=True):
    try:
        user_id = current_user.id
        date = request.form.get('date', datetime.now().strftime("%Y-%m-%d"))
        new_group = request.form.get('new_group')
        target_date = request.form.get('target_date', date)
        item_ids = json.loads(request.form.get('item_ids', '[]'))
        
        if not item_ids or not new_group:
            return jsonify({'error': 'Missing required parameters'}), 400

        # --- Load source session ---
        eaten_items, _ = get_current_session(user_id, date)

        # --- Prepare items to transfer ---
        items_to_transfer = []
        for item in eaten_items:
            if item['id'] in item_ids:
                new_item = item.copy()
                new_item['group'] = new_group
                if not remove_original:  # copy → new ID
                    new_item['id'] = str(uuid.uuid4())
                items_to_transfer.append(new_item)

        # --- Case 1: same date move/copy ---
        if target_date == date:
            if remove_original:
                eaten_items = [i for i in eaten_items if i['id'] not in item_ids]
            eaten_items.extend(items_to_transfer)
            save_current_session(user_id, eaten_items, date)

            target_items = eaten_items  # alias since same date

        # --- Case 2: cross-date move/copy ---
        else:
            if remove_original:
                eaten_items = [i for i in eaten_items if i['id'] not in item_ids]
                save_current_session(user_id, eaten_items, date)

            target_items, _ = get_current_session(user_id, target_date)
            target_items.extend(items_to_transfer)
            save_current_session(user_id, target_items, target_date)

        # --- Recalculate totals/breakdown for target session ---
        recalculated_totals = calculate_totals(target_items)
        recalculated_breakdown = calculate_group_breakdown(target_items)
        current_date_formatted = format_date(target_date)

        # --- Build response payload (same as update_grams) ---
        response_data = {
            'success': True,
            'action': 'move' if remove_original else 'copy',
            'session': target_items,
            'totals': recalculated_totals,
            'breakdown': recalculated_breakdown,
            'current_date_formatted': current_date_formatted,
        }

        return jsonify(response_data)

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def format_item_for_frontend(item):
    """Format item for frontend display, handling both units and grams-only items"""
    try:
        return {
            'id': item.get('id', ''),
            'key': item.get('key', ''),
            'name': item.get('name', ''),
            'calories': float(item.get('calories', 0)),
            'proteins': float(item.get('proteins', 0)),
            'carbs': float(item.get('carbs', 0)),
            'fats': float(item.get('fats', 0)),
            'saturated': float(item.get('saturated', 0)),
            'fiber': float(item.get('fiber', 0)),
            'sugars': float(item.get('sugars', 0)),
            'salt': float(item.get('salt', 0)),
            # ✅ Use 'grams' directly if available, otherwise fallback to 'units'
            'grams': float(item.get('grams', item.get('units', 0))),
            'group': item.get('group', 'other')
        }
    except Exception as e:
        print(f"Error formatting item for frontend: {e}")
        # Return a safe default
        return {
            'id': item.get('id', ''),
            'key': item.get('key', ''),
            'name': item.get('name', 'Unknown'),
            'calories': 0,
            'proteins': 0,
            'carbs': 0,
            'fats': 0,
            'saturated': 0,
            'fiber': 0,
            'sugars': 0,
            'salt': 0,
            'grams': 0,
            'group': item.get('group', 'other')
        }

def calculate_group_breakdown(eaten_items):
    """
    Enhanced group breakdown calculation with complete nutritional data
    """
    breakdown = {}
    
    for item in eaten_items:
        group = item.get('group', 'other')
        
        if group not in breakdown:
            breakdown[group] = {
                'calories': 0,
                'proteins': 0,
                'carbs': 0,
                'fats': 0,
                'saturated': 0,
                'fiber': 0,
                'sugars': 0,
                'salt': 0,
                'items': []
            }
        
        # Add to group totals
        breakdown[group]['calories'] += float(item['calories'])
        breakdown[group]['proteins'] += float(item['proteins'])
        breakdown[group]['carbs'] += float(item['carbs'])
        breakdown[group]['fats'] += float(item['fats'])
        breakdown[group]['saturated'] += float(item.get('saturated', 0))
        breakdown[group]['fiber'] += float(item.get('fiber', 0))
        breakdown[group]['sugars'] += float(item.get('sugars', 0))
        breakdown[group]['salt'] += float(item.get('salt', 0))
        
        # Add formatted item to group
        breakdown[group]['items'].append(format_item_for_frontend(item))
    
    return breakdown



@app.route('/update_grams', methods=['POST'])
@login_required
def update_grams():
    try:
        print("Received update_grams request")
        user_id = current_user.id
        item_id = request.form.get('item_id')
        new_grams = request.form.get('new_grams')
        date = request.form.get('date', datetime.now().strftime("%Y-%m-%d"))
        
        print(f"Params: id={item_id}, grams={new_grams}, date={date}")
        
        if not item_id:
            print("⚠️ Empty item_id received!")
            return jsonify({'error': 'Empty item ID'}), 400
        
        eaten_items, current_date = get_current_session(user_id, date)
        print(f"Current session has {len(eaten_items)} items")
        
        # Find item by ID
        item_found = None
        for item in eaten_items:
            if item.get('id') == item_id:
                item_found = item
                break

        if not item_found:
            print(f"❌ Item not found with id: '{item_id}'. Available IDs: {[item.get('id') for item in eaten_items]}")
            return jsonify({'error': 'Item not found'}), 404

        print(f"Food name from session: {item_found['name']}")
        
        # Lookup food by key
        food_key = item_found['key']
        food = get_food_by_key(food_key)
        
        if not food:
            print(f"Food not found in database for key: '{food_key}'")
            return jsonify({'error': 'Food not found'}), 404
        
        # Convert to grams
        factor = float(new_grams) / 100.0
        item_found['grams'] = float(new_grams)
        item_found['units'] = float(new_grams)
        item_found['unit_type'] = 'grams'

        # Core macros
        item_found['carbs']      = food.get('carbs', 0.0) * factor
        item_found['proteins']   = food.get('proteins', 0.0) * factor
        item_found['fats']       = food.get('fats', 0.0) * factor
        item_found['calories']   = food.get('calories', 0.0) * factor

        # Extra nutrients
        item_found['fiber']      = food.get('fiber', 0.0) * factor
        item_found['sugars']     = food.get('sugars', 0.0) * factor
        item_found['salt']       = food.get('salt', 0.0) * factor
        item_found['saturated']  = food.get('saturated', 0.0) * factor
        
        # Save session
        save_current_session(user_id, eaten_items, date)
        
        # Recalculate totals
        totals = calculate_totals(eaten_items)
        group_breakdown = calculate_group_breakdown(eaten_items)
        current_date_formatted = format_date(current_date)
        
        return jsonify({
            'session': eaten_items,
            'totals': totals,
            'current_date_formatted': current_date_formatted,
            'breakdown': group_breakdown
        })
    except Exception as e:
        print(f"Error in update_grams: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
def get_visible_foods(user):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if user.role == 'admin':
            # Admin sees all foods
            cursor.execute('SELECT * FROM foods')
        else:
            # Regular user sees global + their own foods
            cursor.execute('''
                SELECT * FROM foods
                WHERE owner_id IS NULL OR owner_id = %s
            ''', (user.id,))
        return cursor.fetchall()
    finally:
        conn.close()    

@app.route('/save_food', methods=['POST'])
@login_required
def save_food_route():
    print("Received form data:", request.form.to_dict())
    conn = None
    try:
        # Extract form data
        name = request.form.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Pakko nimetä!'}), 400

        ean = request.form.get('ean') or None

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check for duplicate EAN globally
        if ean:
            cursor.execute('SELECT key FROM foods WHERE ean = %s', (ean,))
            existing_food = cursor.fetchone()
            if existing_food:
                return jsonify({
                    'success': False,
                    'error': f'EAN {ean} käytössä jo: {existing_food[0]}'
                }), 400

        # Helper to parse floats
        def parse_optional_float(value):
            try:
                return float(value.strip()) if value else None
            except (ValueError, AttributeError):
                return None

        # Nutrients
        carbs = parse_optional_float(request.form.get('carbs'))
        sugars = parse_optional_float(request.form.get('sugars'))
        fiber = parse_optional_float(request.form.get('fiber'))
        proteins = parse_optional_float(request.form.get('proteins'))
        fats = parse_optional_float(request.form.get('fats'))
        saturated = parse_optional_float(request.form.get('saturated'))
        salt = parse_optional_float(request.form.get('salt'))

        # Portion fields
        serving = parse_optional_float(request.form.get('serving'))
        half = parse_optional_float(request.form.get('half'))
        entire = parse_optional_float(request.form.get('entire'))
        bigserving = parse_optional_float(request.form.get('bigserving'))
        # Grams (default 100)
        grams = parse_optional_float(request.form.get('grams')) or 100
        if grams < 0.001:
            grams = 0.001

        # Calories
        calories_input = request.form.get('calories')
        if calories_input:
            try:
                calories = float(calories_input)
                calculated_calories = calculate_calories(carbs or 0, proteins or 0, fats or 0)
                if abs(calories - calculated_calories) > calculated_calories * 0.5:
                    calories = calculated_calories
            except ValueError:
                calories = calculate_calories(carbs or 0, proteins or 0, fats or 0)
        else:
            calories = calculate_calories(carbs or 0, proteins or 0, fats or 0)

        # Unique key
        base_key = re.sub(r'[^a-z0-9_]', '', name.lower().replace(' ', '_')) or "custom_food"
        key = base_key
        counter = 1
        while True:
            cursor.execute('SELECT 1 FROM foods WHERE key = %s', (key,))
            if not cursor.fetchone():
                break
            key = f"{base_key}_{counter}"
            counter += 1
            if counter > 100:
                key = f"custom_{uuid.uuid4().hex[:8]}"
                break

        # Determine owner: admin foods are global, others are private
        owner_id = None if current_user.role == 'admin' else current_user.id

        # Insert food
        cursor.execute('''
            INSERT INTO foods
            (key, name, carbs, sugars, fiber, proteins, fats, saturated, salt, calories, grams, half, entire, serving, bigserving, ean, owner_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            key, name, carbs, sugars, fiber, proteins, fats, saturated, salt,
            calories, grams, half, entire, serving, bigserving, ean, owner_id
        ))

        # Initialize usage per user
        cursor.execute('''
            INSERT INTO food_usage (user_id, food_key, count)
            VALUES (%s, %s, 1)
            ON CONFLICT (user_id, food_key)
            DO UPDATE SET count = food_usage.count + 1
        ''', (current_user.id, key))

        conn.commit()
        return jsonify({'success': True})

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()




def calculate_calories(carbs, proteins, fats):
    """
    Calculate calories using the standard formula:
    carbs * 4 + proteins * 4 + fats * 9
    """
    return carbs * 4 + proteins * 4 + fats * 9

def calculate_weekly_averages(session_history):
    weekly_data = {}

    for date_str, items in session_history.items():
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            year, week_num, _ = date_obj.isocalendar()
            week_key = f"{year}-W{week_num:02d}"

            if week_key not in weekly_data:
                weekly_data[week_key] = {
                    "days": [],
                    "calories": 0,
                    "proteins": 0,
                    "fats": 0,
                    "carbs": 0,
                    "sugars": 0,

                    "salt": 0,
                    "saturated": 0,
                    "fiber": 0,
                    "count": 0
                }

            calories, proteins, fats, carbs, sugars, salt, saturated, fiber = get_daily_totals(items)
            weekly_data[week_key]["days"].append(date_str)
            weekly_data[week_key]["calories"] += calories
            weekly_data[week_key]["proteins"] += proteins
            weekly_data[week_key]["fats"] += fats
            weekly_data[week_key]["carbs"] += carbs
            weekly_data[week_key]["sugars"] += sugars
            weekly_data[week_key]["salt"] += salt
            weekly_data[week_key]["saturated"] += saturated
            weekly_data[week_key]["fiber"] += fiber
            weekly_data[week_key]["count"] += 1

        except Exception as e:
            app.logger.error(f"Error processing date {date_str}: {e}")
            continue

    result = []
    for week_key, data in weekly_data.items():
        count = data["count"]
        if count > 0:
            result.append({
                "week": week_key,
                "start_date": min(data["days"]),
                "end_date": max(data["days"]),
                "avg_calories": data["calories"] / count,
                "avg_proteins": data["proteins"] / count,
                "avg_fats": data["fats"] / count,
                "avg_carbs": data["carbs"] / count,
                "avg_sugars": data["sugars"] / count,
                "avg_salt": data["salt"] / count,
                "avg_saturated": data["saturated"] / count,
                "avg_fiber": data["fiber"] / count
            })

    result.sort(key=lambda x: x["end_date"], reverse=True)
    return result

def calculate_weekly_projection(tdee, weekly_avg):
    """
    Calculate projected weekly weight change based on TDEE vs weekly average calories.

    Args:
        tdee (float): User's daily maintenance calories.
        weekly_avg (float): Average daily calories over the past 7 days.

    Returns:
        dict: projected weight change in kg and daily balance.
    """
    daily_balance = weekly_avg - tdee               # calories/day above/below TDEE
    projected_change_kg = (daily_balance * 7) / 7700  # 7700 kcal ~ 1 kg fat

    return {
        "daily_balance": daily_balance,
        "projected_change_kg": projected_change_kg
    }
@app.route('/history')
@login_required
def history():
    user_id = current_user.id
    
    # ✅ Fetch user_tdee from users table
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute("SELECT tdee FROM users WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    conn.close()
    user_tdee = row["tdee"] if row and row["tdee"] is not None else 0  # default 0 if not set

    session_history = get_session_history(user_id)
    today = datetime.today()
    daily_dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(-3, 4)]

    history_data = []
    today_str = today.strftime("%Y-%m-%d")

    # Fill history_data
    for date in daily_dates:
        day_data = session_history.get(date, [])
        calories, proteins, fats, carbs, sugars, salt, saturated, fiber = get_daily_totals(day_data)
        history_data.append({
            'date': format_date(date),
            'date_raw': date,
            'calories': calories,
            'proteins': proteins,
            'fats': fats,
            'sugars': sugars,
            'carbs': carbs,
            'salt': salt,
            'saturated': saturated,
            'fiber': fiber
        })

    # Today's totals
    today_data = session_history.get(today_str, [])
    today_calories, today_proteins, today_fats, today_carbs, today_salt, today_saturated, today_fiber, today_sugars = get_daily_totals(today_data)

    # Weekly averages
    weekly_data = calculate_weekly_averages(session_history)
    
    # ✅ Calculate weekly projection using the provided function
    weekly_projection = None
    daily_balance = 0
    projected_change_kg = 0
    
    if weekly_data and len(weekly_data) > 0 and user_tdee > 0:
        weekly_avg_calories = weekly_data[0]['avg_calories']  # Get current week's average
        weekly_projection = calculate_weekly_projection(user_tdee, weekly_avg_calories)
        daily_balance = weekly_projection['daily_balance']
        projected_change_kg = weekly_projection['projected_change_kg']

    return render_template(
        'history.html',
        history_data=history_data,
        weekly_data=weekly_data,
        today_calories=today_calories,
        today_protein=today_proteins,
        today_fats=today_fats,
        today_carbs=today_carbs,
        today_salt=today_salt,
        today_saturated=today_saturated,
        today_fiber=today_fiber,
        user_tdee=user_tdee,
        daily_balance=daily_balance,  # ✅ New variable
        projected_change_kg=projected_change_kg  # ✅ New variable
    )


# food templates #
@app.route('/save_template_food', methods=['POST'])
@login_required
def save_template_food():
    try:
        name = request.form.get('name')
        items_json = request.form.get('items', '[]')
        
        print(f"Template save request: name={name}, items={items_json}")
        
        if not name:
            return jsonify({'success': False, 'error': 'Pohjan nimi on pakollinen!'})
        
        try:
            items = json.loads(items_json)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return jsonify({'success': False, 'error': 'Invalid items format'})
        
        if not items or len(items) == 0:
            return jsonify({'success': False, 'error': 'Pohjan luomiseen vaaditaan ainakin 1 ruoka-aine'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if template with this name already exists
        cursor.execute(
            'SELECT id FROM food_templates WHERE user_id = %s AND name = %s',
            (current_user.id, name)
        )
        if cursor.fetchone():
            return jsonify({'success': False, 'error': 'Tämän niminen pohja on jo käytössä'})
        
        # Save template to database
        cursor.execute(
            'INSERT INTO food_templates (user_id, name) VALUES (%s, %s) RETURNING id',
            (current_user.id, name)
        )
        template_id = cursor.fetchone()[0]
        
        # Save template items with validation
        valid_items = 0
        for item in items:
            food_key = item.get('food_key')
            grams = item.get('grams')
            
            # Validate required fields
            if not food_key or grams is None:
                print(f"Missing food_key or grams for item: {item}")
                continue
            
            # Convert grams to float if it's a string
            try:
                grams = float(grams)
                if grams <= 0:
                    print(f"Invalid grams value (must be positive): {grams}")
                    continue
            except (ValueError, TypeError):
                print(f"Invalid grams value: {grams}")
                continue
            
            # Verify the food_key exists in foods table
            cursor.execute('SELECT key FROM foods WHERE key = %s', (food_key,))
            if not cursor.fetchone():
                print(f"Invalid food_key: {food_key}")
                continue
            
            # Insert into template items
            cursor.execute(
                'INSERT INTO food_template_items (template_id, food_key, grams) VALUES (%s, %s, %s)',
                (template_id, food_key, grams)
            )
            valid_items += 1
        
        if valid_items == 0:
            conn.rollback()
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'No valid items to save as template'})
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"Template saved successfully with {valid_items} items")
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error saving template: {str(e)}")
        import traceback
        traceback.print_exc()
        
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/get_templates_food', methods=['GET'])
@login_required
def get_templates_food():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT id, name FROM food_templates WHERE user_id = %s ORDER BY created_at DESC',
            (current_user.id,)
        )
        templates = cursor.fetchall()
        
        return jsonify([{'id': t[0], 'name': t[1]} for t in templates])
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    
@app.route('/apply_template_food', methods=['POST'])
@login_required
def apply_template_food():
    try:
        template_id = request.form.get('template_id')
        meal_group = request.form.get('meal_group', 'other')
        date_str = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
        user_id = current_user.id
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get template items
        cursor.execute('''
            SELECT f.key, f.name, f.carbs, f.proteins, f.fats, f.saturated, f.fiber, 
                   f.sugars, f.salt, f.calories, fti.grams
            FROM food_template_items fti
            JOIN foods f ON fti.food_key = f.key
            WHERE fti.template_id = %s
        ''', (template_id,))
        
        template_items = cursor.fetchall()
        
        if not template_items:
            return jsonify({'success': False, 'error': 'Pohjaa ei löydy'})
        
        # Get current session data
        session_data, _ = get_current_session(current_user.id, date_str)
        
        # Add each template item to the session
        for item in template_items:
            food_key = item[0]
            name = item[1]
            # Nutrition values per 100g
            carbs_per_100 = item[2] or 0
            proteins_per_100 = item[3] or 0
            fats_per_100 = item[4] or 0
            saturated_per_100 = item[5] or 0
            fiber_per_100 = item[6] or 0
            sugars_per_100 = item[7] or 0
            salt_per_100 = item[8] or 0
            calories_per_100 = item[9] or 0
            grams = item[10] or 0
            
            # Calculate actual values based on grams
            factor = grams / 100.0
            
            session_data.append({
                'id': str(uuid.uuid4()),
                'key': food_key,
                'name': name,
                'carbs': carbs_per_100 * factor,
                'proteins': proteins_per_100 * factor,
                'fats': fats_per_100 * factor,
                'saturated': saturated_per_100 * factor,
                'fiber': fiber_per_100 * factor,
                'sugars': sugars_per_100 * factor,
                'salt': salt_per_100 * factor,
                'calories': calories_per_100 * factor,
                'grams': grams,
                'group': meal_group
            })
        
        # Save updated session
        save_current_session(current_user.id, session_data, date_str)
        
        # Get updated breakdown and totals
        totals = calculate_totals(session_data)
        breakdown = calculate_group_breakdown(session_data)
        
        return jsonify({
            'success': True,
            'session': session_data,
            'totals': totals,
            'breakdown': breakdown
        })
    except Exception as e:
        print(f"Error applying template: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})
@app.route('/debug_templates')
@login_required
def debug_templates():
    """Endpoint to check existing templates for the current user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT id, name FROM food_templates WHERE user_id = %s',
            (current_user.id,)
        )
        templates = cursor.fetchall()
        
        return jsonify({
            'success': True,
            'templates': [{'id': t[0], 'name': t[1]} for t in templates]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        if conn:
            conn.close()
@app.route('/delete_template_food', methods=['POST'])
@login_required
def delete_template_food():
    try:
        template_id = request.form.get('template_id')
        
        if not template_id:
            return jsonify({'success': False, 'error': 'Template ID is required'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify the template belongs to the current user
        cursor.execute(
            'SELECT id FROM food_templates WHERE id = %s AND user_id = %s',
            (template_id, current_user.id)
        )
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Template not found or access denied'})
        
        # Delete template items first (foreign key constraint)
        cursor.execute(
            'DELETE FROM food_template_items WHERE template_id = %s',
            (template_id,)
        )
        
        # Delete the template
        cursor.execute(
            'DELETE FROM food_templates WHERE id = %s',
            (template_id,)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error deleting template: {str(e)}")
        import traceback
        traceback.print_exc()
        
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
@app.route('/get_template_preview', methods=['GET'])
@login_required
def get_template_preview():
    try:
        template_id = request.args.get('template_id')
        
        if not template_id:
            return jsonify({'success': False, 'error': 'Template ID required'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get template items with food details
        cursor.execute('''
            SELECT f.name, fti.grams
            FROM food_template_items fti
            JOIN foods f ON fti.food_key = f.key
            WHERE fti.template_id = %s
            ORDER BY fti.id
        ''', (template_id,))
        
        items = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'items': [{'name': item[0], 'grams': item[1]} for item in items]
        })
        
    except Exception as e:
        print(f"Error getting template preview: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/save_recipe', methods=['POST'])
@login_required
def save_recipe():
    try:
        recipe_name = request.form.get('recipe_name')
        selected_ids = json.loads(request.form.get('selected_ids'))
        date = request.form.get('date', datetime.now().strftime("%Y-%m-%d"))
        
        # Get the current session
        user_id = current_user.id
        eaten_items, _ = get_current_session(user_id, date)
        
        # Filter selected items
        recipe_items = [item for item in eaten_items if item['id'] in selected_ids]
        
        if not recipe_items:
            return jsonify(success=False, error="No items selected for recipe"), 400
        
        # Calculate total nutrition
        total_grams = sum(item['grams'] for item in recipe_items)
        
        # Store individual ingredients with their original data
        ingredients = []
        for item in recipe_items:
            ingredients.append({
                "id": item['id'],
                "name": item['name'],
                "key": item['key'],
                "grams": item['grams'],
                "calories_per_100g": item['calories'] / item['grams'] * 100,
                "proteins_per_100g": item['proteins'] / item['grams'] * 100,
                "carbs_per_100g": item['carbs'] / item['grams'] * 100,
                "fats_per_100g": item['fats'] / item['grams'] * 100,
                "sugars_per_100g": item.get('sugars', 0) / item['grams'] * 100,
                "fiber_per_100g": item.get('fiber', 0) / item['grams'] * 100,
                "saturated_per_100g": item.get('saturated', 0) / item['grams'] * 100,
                "salt_per_100g": item.get('salt', 0) / item['grams'] * 100
            })
        
        recipe_data = {
            "name": recipe_name,
            "key": normalize_key(recipe_name),
            "carbs": sum(item['carbs'] for item in recipe_items) / total_grams * 100,
            "sugars": sum(item.get('sugars', 0) for item in recipe_items) / total_grams * 100,
            "fiber": sum(item.get('fiber', 0) for item in recipe_items) / total_grams * 100,
            "proteins": sum(item['proteins'] for item in recipe_items) / total_grams * 100,
            "fats": sum(item['fats'] for item in recipe_items) / total_grams * 100,
            "saturated": sum(item.get('saturated', 0) for item in recipe_items) / total_grams * 100,
            "salt": sum(item.get('salt', 0) for item in recipe_items) / total_grams * 100,
            "calories": sum(item['calories'] for item in recipe_items) / total_grams * 100,
            "grams": 100,
            "entire": total_grams,
            "is_recipe": True,
            "ingredients": ingredients
        }
        
        # Save the recipe
        save_food(recipe_data)
        
        return jsonify(success=True)
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500

@app.route('/admin')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute('SELECT id, username, email, role, created_at FROM users')
    users = cursor.fetchall()
    conn.close()
    return render_template('admin.html', users=users)

# ===== WORKOUT ROUTES =====
@app.route('/workout')
@login_required
def workout():
    return render_template('workout.html', current_user_role=current_user.role)

@app.route('/workout/get_current_week', methods=['GET'])
@login_required
def get_current_week():
    today = datetime.today()
    start_date = today - timedelta(days=today.weekday())  # Monday
    week_dates = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    current_date = today.strftime("%Y-%m-%d")

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)

    week_data = {}

    try:
        for date_str in week_dates:
            # Fetch all sessions for that day
            cursor.execute("""
                SELECT ws.id, ws.focus_type, ws.name
                FROM workout_sessions ws
                WHERE ws.user_id = %s AND ws.date = %s
            """, (current_user.id, date_str))
            sessions = cursor.fetchall()

            day_sessions = []
            for session_row in sessions:
                session_id, focus_type, name = session_row

                # Fetch sets for this session (strength training)
                cursor.execute("""
                    SELECT wset.id, wset.exercise_id, wset.reps, wset.weight, ex.name, ex.muscle_group
                    FROM workout_sets wset
                    JOIN exercises ex ON ex.id = wset.exercise_id
                    WHERE wset.session_id = %s
                """, (session_id,))
                sets = cursor.fetchall()

                # ✅ UPDATED: Use the same cardio query as get_workout_session for consistency
                cursor.execute('''
                    SELECT DISTINCT
                        cs.id,
                        cs.duration_minutes,
                        cs.distance_km,
                        cs.avg_pace_min_per_km,
                        cs.avg_heart_rate,
                        cs.watts,
                        cs.calories_burned,
                        cs.notes,
                        ce.name as exercise_name,
                        ce.type as exercise_type,
                        ce.met_value,
                        cs.created_at
                    FROM cardio_sessions cs
                    JOIN workout_sessions ws ON cs.session_id = ws.id
                    JOIN cardio_exercises ce ON cs.cardio_exercise_id = ce.id
                    WHERE ws.user_id = %s AND ws.date = %s
                    ORDER BY cs.created_at DESC, cs.id DESC
                ''', (current_user.id, date_str))
                
                cardio_data = cursor.fetchall()

                exercises_data = {}
                for s in sets:
                    ex_id, ex_id_dup, reps, weight, ex_name, muscle_group = s
                    if ex_id not in exercises_data:
                        exercises_data[ex_id] = {
                            "id": ex_id,
                            "name": ex_name,
                            "muscle_group": muscle_group,
                            "sets": []
                        }
                    exercises_data[ex_id]["sets"].append({"reps": reps, "weight": weight})

                # ✅ UPDATED: Process cardio data consistently
                cardio_sessions = []
                seen_cardio_ids = set()
                
                for row in cardio_data:
                    if row['id'] not in seen_cardio_ids:
                        seen_cardio_ids.add(row['id'])
                        cardio_sessions.append({
                            'id': row['id'],
                            'exercise_name': row['exercise_name'],
                            'exercise_type': row['exercise_type'],
                            'met_value': float(row['met_value']),
                            'duration_minutes': float(row['duration_minutes']),
                            'distance_km': float(row['distance_km']) if row['distance_km'] else None,
                            'avg_pace_min_per_km': float(row['avg_pace_min_per_km']) if row['avg_pace_min_per_km'] else None,
                            'avg_heart_rate': row['avg_heart_rate'],
                            'watts': row['watts'],
                            'calories_burned': float(row['calories_burned']),
                            'notes': row['notes']
                        })

                # Build comparison data per exercise (previous session with same focus_type + exercise)
                comparison_data = []
                for ex_id, ex_data in exercises_data.items():
                    cursor.execute("""
                        SELECT ws.date, wset.reps, wset.weight
                        FROM workout_sessions ws
                        JOIN workout_sets wset ON wset.session_id = ws.id
                        WHERE ws.user_id = %s
                          AND ws.focus_type = %s
                          AND wset.exercise_id = %s
                          AND ws.id != %s
                        ORDER BY ws.date DESC
                        LIMIT 1
                    """, (current_user.id, focus_type, ex_id, session_id))
                    last = cursor.fetchone()

                    current_sets = ex_data["sets"]
                    total_reps = sum(s["reps"] for s in current_sets)
                    total_volume = sum(s["reps"] * s["weight"] for s in current_sets)

                    if last:
                        last_reps = last[1]
                        last_weight = last[2]
                        last_volume = last_reps * last_weight
                        comparison_data.append({
                            "name": ex_data["name"],
                            "lastDate": last[0].isoformat() if isinstance(last[0], datetime) else last[0],
                            "currentSets": current_sets,
                            "lastReps": last_reps,
                            "lastWeight": last_weight,
                            "lastVolume": last_volume
                        })
                    else:
                        comparison_data.append({
                            "name": ex_data["name"],
                            "lastDate": None,
                            "currentSets": current_sets,
                            "lastReps": 0,
                            "lastWeight": 0,
                            "lastVolume": 0
                        })

                day_sessions.append({
                    "sessionId": session_id,
                    "focus_type": focus_type,
                    "name": name,
                    "exercises": list(exercises_data.values()),
                    "cardio_sessions": cardio_sessions,  # ✅ Already included
                    "comparisonData": comparison_data
                })

            week_data[date_str] = day_sessions

        return jsonify(dates=week_dates, current_date=current_date, week_sessions=week_data)

    finally:
        cursor.close()
        conn.close()

@app.route('/workout/init_session', methods=['POST'])
@login_required
def init_workout_session():
    user_id = current_user.id
    date = request.form.get('date', datetime.now().strftime("%Y-%m-%d"))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO workout_sessions (user_id, date, muscle_group) "
            "VALUES (%s, %s, 'General') ON CONFLICT (user_id, date) DO NOTHING "
            "RETURNING id",
            (user_id, date)
        )
        session_id = cursor.fetchone()[0] if cursor.rowcount > 0 else None
        conn.commit()
        return jsonify(success=True, session_id=session_id)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500
    finally:
        conn.close()


@app.route('/workout/get_session', methods=['POST'])
@login_required
def get_workout_session():
    user_id = current_user.id
    date_str = request.form.get('date')
    
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify(error="Invalid date format"), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    
    try:
        # ============================================================================
        # PRIORITY 1: Look for UNSAVED session first
        # ============================================================================
        cursor.execute(
            "SELECT id, notes, is_saved, workout_type, name, focus_type FROM workout_sessions "
            "WHERE user_id = %s AND date = %s AND is_saved = false "
            "ORDER BY id DESC LIMIT 1",
            (user_id, date)
        )
        session_data = cursor.fetchone()
        
        # ============================================================================
        # PRIORITY 2: If no unsaved session, look for saved session (for reference)
        # ============================================================================
        if not session_data:
            cursor.execute(
                "SELECT id, notes, is_saved, workout_type, name, focus_type FROM workout_sessions "
                "WHERE user_id = %s AND date = %s "
                "ORDER BY is_saved ASC, id DESC LIMIT 1",
                (user_id, date)
            )
            session_data = cursor.fetchone()
        
        if not session_data:
            conn.close()
            return jsonify({
                'success': True,
                'session': None,
                'exercises': [],
                'cardio_sessions': []
            })
        
        session_id = session_data['id']
        
        # ============================================================================
        # Fetch cardio ONLY for this specific session (not all cardio for the day)
        # ============================================================================
        cursor.execute('''
            SELECT DISTINCT
                cs.id,
                cs.duration_minutes,
                cs.distance_km,
                cs.avg_pace_min_per_km,
                cs.avg_heart_rate,
                cs.watts,
                cs.calories_burned,
                cs.notes,
                cs.is_saved,
                ce.name as exercise_name,
                ce.type as exercise_type,
                ce.met_value,
                cs.created_at
            FROM cardio_sessions cs
            JOIN cardio_exercises ce ON cs.cardio_exercise_id = ce.id
            WHERE cs.session_id = %s
            ORDER BY cs.created_at DESC, cs.id DESC
        ''', (session_id,))

        cardio_sessions = []
        seen_ids = set()
        
        for row in cursor.fetchall():
            if row['id'] not in seen_ids:
                seen_ids.add(row['id'])
                cardio_sessions.append({
                    'id': row['id'],
                    'exercise_name': row['exercise_name'],
                    'exercise_type': row['exercise_type'],
                    'met_value': float(row['met_value']),
                    'duration_minutes': float(row['duration_minutes']),
                    'distance_km': float(row['distance_km']) if row['distance_km'] else None,
                    'avg_pace_min_per_km': float(row['avg_pace_min_per_km']) if row['avg_pace_min_per_km'] else None,
                    'avg_heart_rate': row['avg_heart_rate'],
                    'watts': row['watts'],
                    'calories_burned': float(row['calories_burned']),
                    'notes': row['notes'],
                    'is_saved': row['is_saved']
                })
        
        session = {
            "id": session_data['id'],
            "notes": session_data['notes'],
            "is_saved": session_data['is_saved'],
            "workout_type": session_data['workout_type'],
            "name": session_data['name'],
            "focus_type": session_data['focus_type']
        }

        # Get sets for this session and group by exercise
        cursor.execute(
            "SELECT s.id, e.id AS exercise_id, e.name AS exercise_name, "
            "e.muscle_group, s.reps, s.weight, s.volume, s.rir, s.comments, s.is_saved "
            "FROM workout_sets s "
            "JOIN exercises e ON s.exercise_id = e.id "
            "WHERE s.session_id = %s "
            "ORDER BY e.name, s.id",
            (session_id,)
        )
        sets = cursor.fetchall()
        
        # Group sets by exercise
        exercises = {}
        for row in sets:
            ex_id = row['exercise_id']
            if ex_id not in exercises:
                exercises[ex_id] = {
                    'id': ex_id,
                    'name': row['exercise_name'],
                    'muscle_group': row['muscle_group'],
                    'sets': []
                }
            exercises[ex_id]['sets'].append({
                'id': row['id'],
                'reps': row['reps'],
                'weight': row['weight'],
                'volume': row['volume'],
                'rir': row['rir'],
                'comments': row['comments'],
                'is_saved': row['is_saved']
            })
        
        conn.close()
    
        return jsonify({
            'success': True,
            'session': dict(session),
            'exercises': list(exercises.values()),
            'cardio_sessions': cardio_sessions
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        conn.close()


        
    
@app.route('/workout/save_set', methods=['POST'])
@login_required
def save_workout_set():
    user_id = current_user.id
    date_str = request.form.get('date')
    exercise_id = request.form.get('exercise_id')
    reps = request.form.get('reps')
    weight = request.form.get('weight')
    muscle_group = request.form.get('muscle_group')
    rir = request.form.get('rir')
    
    # Handle "Failure" case properly
    if rir == "Failure":
        rir = -1
    elif rir and rir.strip():
        try:
            rir = float(rir)  # Convert numbers to float
        except ValueError:
            rir = None
    else:
        rir = None
    comments = request.form.get('comments')
    
    # Get sets_count from form data
    sets_count = int(request.form.get('sets_count', 1))
    
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        reps = int(reps)
        weight = float(weight)
        rir = float(rir) if rir else None
    except (ValueError, TypeError) as e:
        return jsonify(success=False, error=f"Invalid input data: {str(e)}"), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    set_ids = []
    
    try:
        # ============================================================================
        # CRITICAL: Get or create UNSAVED session only
        # ============================================================================
        cursor.execute(
            "SELECT id FROM workout_sessions "
            "WHERE user_id = %s AND date = %s AND is_saved = false "
            "ORDER BY id DESC LIMIT 1",
            (user_id, date)
        )
        session = cursor.fetchone()
        
        if not session:
            cursor.execute(
                "INSERT INTO workout_sessions (user_id, date, name, focus_type, is_saved) "
                "VALUES (%s, %s, %s, %s, false) RETURNING id",
                (user_id, date, 'Unnamed Workout', 'general')
            )
            session_id = cursor.fetchone()[0]
            app.logger.info(f"Created new unsaved session {session_id} for date {date}")
        else:
            session_id = session[0]
            app.logger.info(f"Using existing unsaved session {session_id} for date {date}")
        
        # Insert multiple sets with is_saved = false
        # NOTE: volume is auto-calculated, don't insert it manually
        for i in range(sets_count):
            cursor.execute(
                "INSERT INTO workout_sets (session_id, exercise_id, reps, weight, rir, comments, is_saved) "
                "VALUES (%s, %s, %s, %s, %s, %s, false) RETURNING id",
                (session_id, exercise_id, reps, weight, rir, comments)
            )
            set_ids.append(cursor.fetchone()[0])
        
        conn.commit()
        return jsonify(success=True, set_ids=set_ids, session_id=session_id)
    
    except Exception as e:
        conn.rollback()
        app.logger.error(f"Error saving workout set: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify(success=False, error=str(e)), 500
    finally:
        conn.close()



@app.route('/workout/delete_set', methods=['POST'])
@login_required
def delete_workout_set():
    set_id = request.form.get('set_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "DELETE FROM workout_sets WHERE id = %s",
            (set_id,)
        )
        conn.commit()
        return jsonify(success=True)
    
    except Exception as e:
        conn.rollback()
        return jsonify(success=False, error=str(e)), 500
    finally:
        conn.close()

@app.route('/workout/add_exercise', methods=['POST'])
@admin_required
def add_exercise():
    name = request.form.get('name')
    muscle_group = request.form.get('muscle_group')
    description = request.form.get('description')
    
    if not name or not muscle_group:
        return jsonify(success=False, error="Nimi ja lihasryhmä vaaditaan"), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO exercises (name, muscle_group, description) "
            "VALUES (%s, %s, %s) RETURNING id",
            (name, muscle_group, description)
        )
        exercise_id = cursor.fetchone()[0]
        conn.commit()
        return jsonify(success=True, exercise_id=exercise_id)
    
    except psycopg2.IntegrityError:
        return jsonify(success=False, error="Liike on jo olemassa"), 400
    except Exception as e:
        conn.rollback()
        return jsonify(success=False, error=str(e)), 500
    finally:
        conn.close()

@app.route('/workout/delete_exercise', methods=['POST'])
@admin_required
def delete_exercise():
    exercise_id = request.form.get('exercise_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "DELETE FROM exercises WHERE id = %s",
            (exercise_id,)
        )
        conn.commit()
        return jsonify(success=True)
    
    except Exception as e:
        conn.rollback()
        return jsonify(success=False, error=str(e)), 500
    finally:
        conn.close()

def format_duration(total_seconds):
    """Convert seconds to human readable format like '1h 23m' or '45m' or '2h'"""
    if not total_seconds or total_seconds <= 0:
        return "0m"
    
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    
    if hours > 0 and minutes > 0:
        return f"{hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h"
    elif minutes > 0:
        return f"{minutes}m"
    else:
        return "< 1m"
        
@app.route('/workout/history', methods=['GET'])
@login_required
def workout_history():
    user_id = current_user.id
    period = request.args.get('period', 'daily')

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)

    try:
        # In /workout/history, update the daily section:
        if period == 'daily':
            # Get all workout sessions - filter by saved sessions
            cursor.execute('''
                SELECT 
                    s.date,
                    s.name as workout_name,
                    s.id as session_id,
                    e.muscle_group,
                    ws.reps,
                    ws.volume,
                    ws.is_saved
                FROM workout_sessions s
                LEFT JOIN workout_sets ws ON s.id = ws.session_id
                LEFT JOIN exercises e ON ws.exercise_id = e.id
                WHERE s.user_id = %s AND s.is_saved = true
                ORDER BY s.date DESC
            ''', (user_id,))
            rows = cursor.fetchall()

            # Group by date and session
            daily_data = {}
            for row in rows:
                date = row['date']
                session_id = row['session_id']
                
                if date not in daily_data:
                    daily_data[date] = {
                        'workout_names': set(),
                        'session_ids': set(),
                        'total_sets': 0,
                        'total_reps': 0,
                        'total_volume': 0.0,
                    }
                
                # Always capture session info
                if session_id:
                    daily_data[date]['session_ids'].add(session_id)
                    if row['workout_name']:
                        daily_data[date]['workout_names'].add(row['workout_name'])
                
                # Aggregate from saved sets (only count if we have actual set data)
                if row['is_saved'] and row['muscle_group'] and row['reps'] is not None:
                    daily_data[date]['total_sets'] += 1
                    daily_data[date]['total_reps'] += row['reps']
                    daily_data[date]['total_volume'] += float(row['volume'] or 0)

            history = []
            for date, data in sorted(daily_data.items(), reverse=True):
                # Skip dates with no sessions
                if not data['session_ids']:
                    continue

                # Calculate ACTUAL duration and calories from ALL saved cardio sessions for this day
                cursor.execute('''
                    SELECT 
                        COALESCE(SUM(cs.duration_minutes), 0) as total_duration_minutes,
                        COALESCE(SUM(cs.calories_burned), 0) as total_calories
                    FROM cardio_sessions cs
                    JOIN workout_sessions ws ON cs.session_id = ws.id
                    WHERE ws.user_id = %s AND ws.date = %s AND ws.is_saved = true AND cs.is_saved = TRUE
                ''', (user_id, date))
                
                cardio_totals = cursor.fetchone()
                total_duration_minutes = float(cardio_totals['total_duration_minutes'] or 0)
                total_calories = float(cardio_totals['total_calories'] or 0)
                
                # Convert minutes to seconds for consistency
                duration_seconds = int(total_duration_minutes * 60)
                duration_formatted = format_duration(duration_seconds)

                # Get muscles per day (only saved sets from saved sessions)
                cursor.execute('''
                    SELECT e.muscle_group,
                        COUNT(ws.id) AS sets,
                        SUM(ws.reps) AS reps,
                        SUM(ws.volume) AS volume
                    FROM workout_sessions s
                    JOIN workout_sets ws ON s.id = ws.session_id
                    JOIN exercises e ON ws.exercise_id = e.id
                    WHERE s.user_id = %s AND s.date = %s AND s.is_saved = true AND ws.is_saved = TRUE
                    GROUP BY e.muscle_group
                ''', (user_id, date))
                muscles_data = cursor.fetchall()
                muscles = {}
                for m in muscles_data:
                    if m['muscle_group']:
                        muscles[m['muscle_group']] = {
                            'total_sets': m['sets'] or 0,
                            'total_reps': m['reps'] or 0,
                            'total_volume': float(m['volume'] or 0)
                        }
                
                # Format workout names
                workout_names_list = list(data['workout_names'])
                if len(workout_names_list) > 1:
                    workout_name_display = ', '.join(workout_names_list[:2])
                    if len(workout_names_list) > 2:
                        workout_name_display += f' +{len(workout_names_list)-2} lisää'
                else:
                    workout_name_display = workout_names_list[0] if workout_names_list else 'Unnamed Workout'
                
                history.append({
                    'date': date,
                    'workout_name': workout_name_display,
                    'duration_seconds': duration_seconds,
                    'duration_formatted': duration_formatted,
                    'calories_burned': total_calories,
                    'sessions_count': len(data['session_ids']),  # This will now show "2" for 2 sessions
                    'total_sets': data['total_sets'],
                    'total_reps': data['total_reps'],
                    'total_volume': data['total_volume'],
                    'muscles': muscles
                })


        else:
            date_trunc = 'week' if period == 'weekly' else 'month'
            period_limit = 12 if period == 'weekly' else 6

            # Get all workout sessions without filtering on sets
            cursor.execute(f'''
                SELECT 
                    DATE_TRUNC('{date_trunc}', s.date)::DATE AS period_start,
                    s.id AS session_id,
                    s.name as workout_name,
                    e.muscle_group,
                    ws.reps,
                    ws.volume,
                    ws.is_saved
                FROM workout_sessions s
                LEFT JOIN workout_sets ws ON s.id = ws.session_id
                LEFT JOIN exercises e ON ws.exercise_id = e.id
                WHERE s.user_id = %s AND s.is_saved = true
                ORDER BY period_start DESC
            ''', (user_id,))
            rows = cursor.fetchall()

            period_map = {}
            for row in rows:
                period_start = row['period_start']
                if period_start not in period_map:
                    period_map[period_start] = {
                        'sessions': set(),
                        'sessions_with_saved_sets': set(),
                        'workout_names': set(),
                        'muscles': {},
                        'total_sets': 0,
                        'total_reps': 0,
                        'total_volume': 0.0,
                        'has_saved_sets': False
                    }

                # Always capture session name
                if row['session_id']:
                    period_map[period_start]['sessions'].add(row['session_id'])
                    if row['workout_name']:
                        period_map[period_start]['workout_names'].add(row['workout_name'])

                # Only aggregate muscle data from SAVED sets
                if row['is_saved'] and row['muscle_group'] and row['reps'] is not None:
                    period_map[period_start]['has_saved_sets'] = True
                    period_map[period_start]['sessions_with_saved_sets'].add(row['session_id'])
                    
                    muscle = row['muscle_group']
                    if muscle not in period_map[period_start]['muscles']:
                        period_map[period_start]['muscles'][muscle] = {
                            'sets': 0,
                            'reps': 0,
                            'volume': 0.0
                        }

                    period_map[period_start]['muscles'][muscle]['sets'] += 1
                    period_map[period_start]['muscles'][muscle]['reps'] += row['reps']
                    period_map[period_start]['muscles'][muscle]['volume'] += float(row['volume'] or 0)

                    # Update totals
                    period_map[period_start]['total_sets'] += 1
                    period_map[period_start]['total_reps'] += row['reps']
                    period_map[period_start]['total_volume'] += float(row['volume'] or 0)

            # Convert to final history list
            history = []
            for period_start, data in sorted(period_map.items(), reverse=True):
                # Skip periods with no saved sets
                if not data['has_saved_sets']:
                    continue
                
                # Calculate ACTUAL duration and calories from cardio sessions for this period
                cursor.execute(f'''
                    SELECT 
                        COALESCE(SUM(cs.duration_minutes), 0) as total_duration_minutes,
                        COALESCE(SUM(cs.calories_burned), 0) as total_calories
                    FROM cardio_sessions cs
                    JOIN workout_sessions ws ON cs.session_id = ws.id
                    WHERE ws.user_id = %s 
                    AND DATE_TRUNC('{date_trunc}', ws.date)::DATE = %s
                    AND cs.is_saved = TRUE
                ''', (user_id, period_start))
                
                cardio_totals = cursor.fetchone()
                total_duration_minutes = float(cardio_totals['total_duration_minutes'] or 0)
                total_calories = float(cardio_totals['total_calories'] or 0)
                
                # Convert to seconds
                duration_seconds = int(total_duration_minutes * 60)
                duration_formatted = format_duration(duration_seconds)
                
                # Create workout names summary
                workout_names_list = list(data['workout_names'])
                if len(workout_names_list) > 2:
                    workout_names_display = f"{', '.join(workout_names_list[:2])} +{len(workout_names_list)-2} lisää"
                else:
                    workout_names_display = ', '.join(workout_names_list) if workout_names_list else 'Various Workouts'

                entry = {
                    'workout_names': workout_names_list,
                    'workout_names_display': workout_names_display,
                    'duration_seconds': duration_seconds,
                    'duration_formatted': duration_formatted,
                    'calories_burned': total_calories,
                    'sessions_count': len(data['sessions_with_saved_sets']),
                    'total_sets': data['total_sets'],
                    'total_reps': data['total_reps'],
                    'total_volume': data['total_volume'],
                    'muscles': {}
                }

                for muscle, stats in data['muscles'].items():
                    entry['muscles'][muscle] = {
                        'total_sets': stats['sets'],
                        'total_reps': stats['reps'],
                        'total_volume': stats['volume']
                    }

                if period == 'weekly':
                    entry['week_start'] = period_start
                else:
                    entry['month_start'] = period_start

                history.append(entry)

            history = history[:period_limit]

        return jsonify(history=history, period=period)

    except Exception as e:
        app.logger.error(f"Workout History Error: {str(e)}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify(error="Could not load workout history"), 500
    finally:
        conn.close()



@app.route('/workout/update_set', methods=['POST'])
@login_required
def update_workout_set():
    set_id = request.form.get('set_id')
    reps = request.form.get('reps')
    weight = request.form.get('weight')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE workout_sets 
            SET reps = %s, weight = %s 
            WHERE id = %s
        ''', (int(reps), float(weight), set_id))
        conn.commit()
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500
    finally:
        conn.close()

# ===== WORKOUT TEMPLATE ROUTES =====
@app.route('/workout/save_template', methods=['POST'])
@admin_required  # Keep admin-only for creation
def save_workout_template():
    try:
        name = request.form.get('name')
        date_str = request.form.get('date')
        user_id = current_user.id
        
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify(error="Invalid date format"), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create template (admin only)
        cursor.execute(
            "INSERT INTO workout_templates (name, created_by) "
            "VALUES (%s, %s) RETURNING id",
            (name, user_id)
        )
        template_id = cursor.fetchone()[0]
        
        # Get session exercises
        cursor.execute(
            "SELECT exercise_id, reps, weight, rir, comments "
            "FROM workout_sets WHERE session_id IN ("
            "SELECT id FROM workout_sessions "
            "WHERE user_id = %s AND date = %s)"
            ,
            (user_id, date_obj)
        )
        sets = cursor.fetchall()
        
        # Add to template
        for set_data in sets:
            cursor.execute(
                "INSERT INTO workout_template_exercises "
                "(template_id, exercise_id, reps, weight, rir, comments) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (template_id, *set_data)
            )
        
        conn.commit()
        return jsonify(success=True)
    except Exception as e:
        return jsonify(error=str(e)), 500
    finally:
        conn.close()

@app.route('/workout/templates', methods=['GET'])
@login_required
def get_workout_templates():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        # Get all public templates (created by admin)
        cursor.execute(
            "SELECT id, name, created_at FROM workout_templates ORDER BY name"
        )
        templates = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(templates=templates)
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/workout/templates/<int:template_id>', methods=['GET'])
@login_required
def get_workout_template(template_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        # Get template metadata
        cursor.execute(
            "SELECT id, name, created_at FROM workout_templates WHERE id = %s",
            (template_id,)
        )
        template = cursor.fetchone()
        if not template:
            conn.close()
            return jsonify(success=False, error="Template not found"), 404
        
        # Aggregate exercises: group + count sets
        cursor.execute('''
            SELECT e.muscle_group, e.name AS exercise, COUNT(*) AS sets
            FROM workout_template_exercises t
            JOIN exercises e ON t.exercise_id = e.id
            WHERE t.template_id = %s
            GROUP BY e.muscle_group, e.name
            ORDER BY e.muscle_group, e.name
        ''', (template_id,))
        exercises = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return jsonify(
            success=True, 
            template=dict(template),
            exercises=exercises
        )
    
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500
        
        
@app.route('/workout/apply_template', methods=['POST'])
@login_required
def apply_workout_template():
    conn = None
    try:
        template_id = request.form.get('template_id')
        date_str = request.form.get('date')
        user_id = current_user.id
        
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError) as e:
            return jsonify(success=False, error=f"Invalid date: {str(e)}"), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify template exists (public to all users)
        cursor.execute(
            "SELECT id FROM workout_templates WHERE id = %s",
            (template_id,)
        )
        if not cursor.fetchone():
            return jsonify(success=False, error="Template not found"), 404
        
        # Get template exercises
        cursor.execute('''
            SELECT exercise_id, reps, weight, rir, comments
            FROM workout_template_exercises
            WHERE template_id = %s
        ''', (template_id,))
        exercises = cursor.fetchall()
        
        # ============================================================================
        # CRITICAL: Use SAME logic as save_set and add_cardio
        # Find existing UNSAVED session or create new one
        # ============================================================================
        cursor.execute(
            "SELECT id FROM workout_sessions "
            "WHERE user_id = %s AND date = %s AND is_saved = false "
            "ORDER BY id DESC LIMIT 1",
            (user_id, date)
        )
        session = cursor.fetchone()
        
        if not session:
            cursor.execute(
                "INSERT INTO workout_sessions (user_id, date, name, focus_type, is_saved) "
                "VALUES (%s, %s, %s, %s, false) RETURNING id",
                (user_id, date, 'Unnamed Workout', 'general')
            )
            session_id = cursor.fetchone()[0]
            app.logger.info(f"Created new unsaved session {session_id} for template on {date}")
        else:
            session_id = session[0]
            app.logger.info(f"Using existing unsaved session {session_id} for template on {date}")
        
        # Add sets to session with is_saved = false
        sets_added = 0
        for ex in exercises:
            cursor.execute(
                "INSERT INTO workout_sets "
                "(session_id, exercise_id, reps, weight, rir, comments, is_saved) "
                "VALUES (%s, %s, %s, %s, %s, %s, false)",
                (session_id, ex[0], ex[1], ex[2], ex[3], ex[4])
            )
            sets_added += 1
        
        conn.commit()
        
        app.logger.info(f"Applied template {template_id} to session {session_id} - added {sets_added} sets")
        
        return jsonify(success=True, session_id=session_id, sets_added=sets_added)
    except Exception as e:
        if conn:
            conn.rollback()
        app.logger.error(f"Error applying template: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify(success=False, error=str(e)), 500
    finally:
        if conn:
            conn.close()

@app.route("/workout/copy_session", methods=["POST"])
@login_required
def copy_session():
    source_date = request.form.get("source_date")
    target_date = request.form.get("target_date")
    user_id = current_user.id
    
    # Enhanced debug logging
    print(f"Copy request: {source_date} -> {target_date} for user {user_id}")
    
    # Validate dates
    if not source_date or not target_date:
        print("Missing source_date or target_date")
        return jsonify({"success": False, "error": "Missing source or target date"})
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)

    try:
        # Check if source session exists
        cursor.execute(
            "SELECT * FROM workout_sessions WHERE user_id = %s AND date = %s",
            (user_id, source_date)
        )
        source_session = cursor.fetchone()
        
        if not source_session:
            print(f"Source session not found for date {source_date}")
            return jsonify({"success": False, "error": "Source session not found"})

        print(f"Found source session: {source_session['id']}")

        # Delete existing target session if it exists
        cursor.execute(
            "DELETE FROM workout_sessions WHERE user_id = %s AND date = %s",
            (user_id, target_date)
        )
        
        # Use source muscle_group (or fallback)
        muscle_group = source_session["muscle_group"] or "All"

        # Insert new session for target date
        cursor.execute(
            "INSERT INTO workout_sessions (user_id, date, name, focus_type, muscle_group) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (user_id, target_date, source_session["name"], source_session["focus_type"], muscle_group)
        )
        new_session_id = cursor.fetchone()["id"]
        print(f"Created new session: {new_session_id}")

        # Copy sets
        cursor.execute(
            "SELECT * FROM workout_sets WHERE session_id = %s",
            (source_session["id"],)
        )
        sets = cursor.fetchall()
        
        sets_copied = 0
        for s in sets:
            cursor.execute(
                "INSERT INTO workout_sets (session_id, exercise_id, reps, weight, rir, comments) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (new_session_id, s["exercise_id"], s["reps"], s["weight"], s["rir"], s["comments"])
            )
            sets_copied += 1

        print(f"Copied {sets_copied} sets")
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"success": True, "message": f"Copied {sets_copied} sets"})

    except Exception as e:
        print(f"Error copying session: {str(e)}")
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"success": False, "error": str(e)})

# Get all exercises endpoint
@app.route('/workout/exercises')
@login_required
def get_exercises_list():
    user_id = current_user.id
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    
    try:
        # Get ALL exercises with optional user stats and trend calculation
        cursor.execute('''
            WITH exercise_volumes AS (
                SELECT 
                    e.id,
                    e.name,
                    e.muscle_group,
                    COALESCE(MAX(ws.weight), 0) AS personal_best,
                    MAX(s.date) AS last_performed,
                    COALESCE(SUM(ws.volume), 0) AS total_volume,
                    -- Calculate monthly volumes for trend
                    COALESCE(SUM(CASE 
                        WHEN s.date >= date_trunc('month', CURRENT_DATE) 
                        THEN ws.volume 
                        ELSE 0 
                    END), 0) AS current_month_volume,
                    COALESCE(SUM(CASE 
                        WHEN s.date >= date_trunc('month', CURRENT_DATE) - INTERVAL '1 month'
                        AND s.date < date_trunc('month', CURRENT_DATE)
                        THEN ws.volume 
                        ELSE 0 
                    END), 0) AS previous_month_volume
                FROM exercises e
                LEFT JOIN workout_sets ws ON e.id = ws.exercise_id
                LEFT JOIN workout_sessions s ON ws.session_id = s.id AND s.user_id = %s
                GROUP BY e.id, e.name, e.muscle_group
            )
            SELECT 
                *,
                CASE 
                    WHEN previous_month_volume > 0 
                    THEN ((current_month_volume - previous_month_volume) / previous_month_volume::float) * 100
                    ELSE 0 
                END AS volume_trend
            FROM exercise_volumes
            ORDER BY name
        ''', (user_id,))
        
        exercises = []
        for row in cursor.fetchall():
            exercises.append({
                'id': row['id'],
                'name': row['name'],
                'muscle_group': row['muscle_group'],
                'personal_best': float(row['personal_best'] or 0),
                'last_performed': row['last_performed'].strftime('%Y-%m-%d') if row['last_performed'] else None,
                'total_volume': float(row['total_volume'] or 0),
                'volume_trend': float(row['volume_trend'] or 0)
            })
        
        return jsonify(exercises=exercises)
        
    except Exception as e:
        app.logger.error(f"Exercises Error: {str(e)}")
        return jsonify(error="Could not load exercises"), 500
    finally:
        conn.close()

# Get exercise details endpoint
@app.route('/workout/exercise/<int:exercise_id>')
@login_required
def get_exercise_history(exercise_id):
    user_id = current_user.id
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    
    try:
        # Get exercise name
        cursor.execute('SELECT name FROM exercises WHERE id = %s', (exercise_id,))
        exercise = cursor.fetchone()
        if not exercise:
            return jsonify(error="Exercise not found"), 404
        
        # Get exercise history
        cursor.execute('''
            SELECT 
                s.date,
                COUNT(ws.id) AS sets,
                MAX(ws.weight) AS best_weight,
                MAX(ws.weight || 'kg × ' || ws.reps) AS best_set,
                SUM(ws.volume) AS volume
            FROM workout_sets ws
            JOIN workout_sessions s ON ws.session_id = s.id
            WHERE s.user_id = %s AND ws.exercise_id = %s
            GROUP BY s.date
            ORDER BY s.date DESC
        ''', (user_id, exercise_id))
        
        history = []
        rows = cursor.fetchall()
        
        for row in rows:
            volume = float(row['volume'] or 0)
            
            history.append({
                'date': row['date'].strftime('%Y-%m-%d'),
                'sets': row['sets'],
                'best_weight': float(row['best_weight'] or 0),
                'best_set': row['best_set'] or '-',
                'volume': volume
            })
        
        # Get personal best
        cursor.execute('''
            SELECT MAX(ws.weight) AS personal_best
            FROM workout_sets ws
            JOIN workout_sessions s ON ws.session_id = s.id
            WHERE s.user_id = %s AND ws.exercise_id = %s
        ''', (user_id, exercise_id))
        personal_best = float(cursor.fetchone()['personal_best'] or 0)
        
        # Get monthly volume (current month)
        cursor.execute('''
            SELECT SUM(ws.volume) AS monthly_volume
            FROM workout_sets ws
            JOIN workout_sessions s ON ws.session_id = s.id
            WHERE s.user_id = %s AND ws.exercise_id = %s
            AND s.date >= date_trunc('month', CURRENT_DATE)
            AND s.date < date_trunc('month', CURRENT_DATE) + INTERVAL '1 month'
        ''', (user_id, exercise_id))
        monthly_volume = float(cursor.fetchone()['monthly_volume'] or 0)
        
        # Get best set (set with highest volume)
        cursor.execute('''
            SELECT weight, reps, volume
            FROM workout_sets ws
            JOIN workout_sessions s ON ws.session_id = s.id
            WHERE s.user_id = %s AND ws.exercise_id = %s
            ORDER BY volume DESC
            LIMIT 1
        ''', (user_id, exercise_id))
        best_set_row = cursor.fetchone()
        best_set = f"{best_set_row['weight']}kg × {best_set_row['reps']}" if best_set_row else '-'
        
        return jsonify({
            'name': exercise['name'],
            'personal_best': personal_best,
            'monthly_volume': monthly_volume,
            'best_set': {
                'weight': float(best_set_row['weight']) if best_set_row else 0,
                'reps': int(best_set_row['reps']) if best_set_row else 0,
                'formatted': f"{best_set_row['weight']}kg × {best_set_row['reps']}" if best_set_row else '-'
                },
            'history': history
        })
        
    except Exception as e:
        app.logger.error(f"Exercise History Error: {str(e)}")
        return jsonify(error="Could not load exercise history"), 500
    finally:
        conn.close()
              
@app.route('/save_metrics', methods=['POST'])
@login_required
def save_metrics():
    """
    Enhanced save_metrics route that handles TDEE calculations from different modes:
    - Easy mode: Uses original activity-based calculation
    - Advanced mode: Uses steps + activity calories (BMR + steps_calories + activity_calories)
    - Custom mode: Uses user-provided TDEE directly
    """
    try:
        # Get basic metrics that are always required
        weight = float(request.form.get('weight', 0))
        
        # Get TDEE based on calculation mode
        tdee = float(request.form.get('tdee', 0))

        # Get gender (optional, defaults to None if not provided)
        gender = request.form.get('gender', None)
        
        # Optional: Get calculation mode for logging/analytics
        calc_mode = request.form.get('mode', 'unknown')

        auto_add_workout_calories = request.form.get('auto_add_workout_calories') == 'true'
        
        # Validate inputs
        if not weight or weight <= 0:
            return jsonify(success=False, error="Valid weight is required"), 400
            
        if not tdee or tdee <= 0:
            return jsonify(success=False, error="Valid TDEE is required"), 400
            
        # Optional: Log the calculation mode for analytics
        print(f"User {current_user.id} updated metrics via {calc_mode} mode: TDEE={tdee}, Weight={weight},Gender={gender}")

        # Update database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET tdee = %s, weight = %s, gender = %s, auto_add_workout_calories = %s WHERE id = %s",
            (tdee, weight, gender, auto_add_workout_calories, current_user.id)
        )
        conn.commit()
        
        return jsonify(
            success=True, 
            message="Metrics saved successfully!",
            data={
                "tdee": tdee,
                "weight": weight,
                "gender": gender,
                "mode": calc_mode,
                "auto_add_workout_calories": auto_add_workout_calories
            }
        )
        
    except ValueError as e:
        print(f"ValueError in save_metrics: {e}")
        return jsonify(success=False, error="Invalid numeric values provided"), 400
        
    except Exception as e:
        print(f"Error saving metrics: {e}")
        return jsonify(success=False, error=str(e)), 500
        
    finally:
        if 'conn' in locals() and conn:
            conn.close()


# Optional: Add a separate endpoint for step-to-calorie calculations if needed elsewhere
@app.route('/calculate_steps_calories', methods=['POST'])
@login_required
def calculate_steps_calories():
    """
    Utility endpoint to calculate calories from steps using the weight-adjusted formula
    Formula: calories = steps × (0.04 × (weight_kg / 70))
    """
    try:
        steps = int(request.form.get('steps', 0))
        weight = float(request.form.get('weight', 70))
        
        if steps < 0 or weight <= 0:
            return jsonify(success=False, error="Invalid input values"), 400
            
        # Weight-adjusted calories per step (base: 0.04 cal/step for 70kg person)
        calories_per_step = 0.04 * (weight / 70)
        total_calories = round(steps * calories_per_step)
        
        return jsonify(
            success=True,
            data={
                "steps": steps,
                "weight": weight,
                "calories_per_step": round(calories_per_step, 4),
                "total_calories": total_calories
            }
        )
        
    except (ValueError, TypeError) as e:
        return jsonify(success=False, error="Invalid input format"), 400
        
    except Exception as e:
        print(f"Error calculating step calories: {e}")
        return jsonify(success=False, error=str(e)), 500

@app.route('/workout/update_rir', methods=['POST'])
def update_rir():
    data = request.json
    set_id = data.get('set_id')
    rir = data.get('rir')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the set exists
    cursor.execute("SELECT id FROM workout_sets WHERE id = %s", (set_id,))
    if cursor.fetchone() is None:
        conn.close()
        return jsonify({'success': False, 'error': 'Set not found'})

    # Handle "Failure" case (stored as -1)
    rir_value = -1 if rir == "Failure" else (int(rir) if rir else None)

    cursor.execute(
        "UPDATE workout_sets SET rir = %s WHERE id = %s",
        (rir_value, set_id)
    )

    conn.commit()
    conn.close()

    return jsonify({'success': True})

@app.route('/workout/update_comment', methods=['POST'])
def update_comment():
    data = request.json
    set_id = data.get('set_id')
    comment = data.get('comment')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the set exists
    cursor.execute("SELECT id FROM workout_sets WHERE id = %s", (set_id,))
    if cursor.fetchone() is None:
        conn.close()
        return jsonify({'success': False, 'error': 'Set not found'})

    cursor.execute(
        "UPDATE workout_sets SET comments = %s WHERE id = %s",
        (comment, set_id)
    )

    conn.commit()
    conn.close()

    return jsonify({'success': True})

@app.route('/get_nutrition_targets')
@login_required
def get_nutrition_targets():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT weight FROM users WHERE id = %s", (current_user.id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    user_weight = result[0] if result and result[0] else 0

    targets = {
        'proteins': user_weight * 2,
        'fats': user_weight * 0.8,
        'salt': 5,
        'saturated': 20,
        'sugars': 60,
        'fiber': 30
    }

    return jsonify(targets)
from datetime import datetime  # ensure this import

def get_user_current_tdee(user_id, target_date=None):
    """
    Get user's current TDEE, including workout adjustments if auto calories is enabled
    
    Args:
        user_id: User ID
        target_date: Date to get TDEE for (defaults to today)
    
    Returns:
        dict: {
            "base_tdee": float,
            "workout_calories": float,
            "daily_tdee": float,
            "auto_enabled": bool
        }
    """
    if target_date is None:
        target_date = datetime.now().date()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get user settings
        cursor.execute(
            "SELECT auto_add_workout_calories, tdee FROM users WHERE id = %s",
            (user_id,)
        )
        user_data = cursor.fetchone()
        
        if not user_data:
            return {"base_tdee": 0, "workout_calories": 0, "daily_tdee": 0, "auto_enabled": False}
        
        auto_enabled, base_tdee = user_data
        base_tdee = float(base_tdee or 0)
        
        if not auto_enabled:
            return {
                "base_tdee": base_tdee,
                "workout_calories": 0,
                "daily_tdee": base_tdee,
                "auto_enabled": False
            }
        
        # Get daily adjustment if auto calories is enabled
        cursor.execute(
            "SELECT workout_calories, adjusted_tdee FROM daily_tdee_adjustments WHERE user_id = %s AND date = %s",
            (user_id, target_date)
        )
        adjustment = cursor.fetchone()
        
        if adjustment:
            workout_calories, adjusted_tdee = adjustment
            return {
                "base_tdee": base_tdee,
                "workout_calories": float(workout_calories or 0),
                "daily_tdee": float(adjusted_tdee or base_tdee),
                "auto_enabled": True
            }
        else:
            # No workout today, return base TDEE
            return {
                "base_tdee": base_tdee,
                "workout_calories": 0,
                "daily_tdee": base_tdee,
                "auto_enabled": True
            }
    
    finally:
        conn.close()
LEVEL_CAP = 999

def xp_to_next_level(level: int, base_xp: int = 120, exp: float = 1.72) -> int:
    """
    XP required to advance from `level` to `level + 1`.
    Tuned for:
      - Early users: ~2-3 levels/week if very active
      - After level 10: ~1 level/week if active
      - Long-tail diminishing returns; practical long-term 50-60 range
    """
    if level >= LEVEL_CAP:
        return 10**12  # effectively unreachable to prevent further leveling
    # Minimum floor to avoid zero at very low levels
    return max(50, int(round(base_xp * (level ** exp))))

def clamp_level(level: int) -> int:
    return min(max(level, 1), LEVEL_CAP)
def safe_add_user_level_columns(cursor):
    """
    Defensive migration: add level and xp_points to users table if not present.
    This allows drop-in replacement without requiring a separate migration step.
    """
    try:
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='users'
        """)
        cols = {r[0] for r in cursor.fetchall()}
        alter_needed = []
        if 'level' not in cols:
            alter_needed.append("ADD COLUMN level INTEGER DEFAULT 1")
        if 'xp_points' not in cols:
            alter_needed.append("ADD COLUMN xp_points INTEGER DEFAULT 0")
        if alter_needed:
            cursor.execute(f"ALTER TABLE users {', '.join(alter_needed)};")
    except Exception as _migration_err:
        # Non-fatal; if migration fails due to permissions, continue assuming columns exist.
        pass
@app.route("/workout/save", methods=["POST"])
@login_required
def save_workout():
    user_id = current_user.id
    data = request.get_json()

    name = data.get('name', 'Unnamed Workout')
    focus_type = data.get('focus_type', 'general')
    date_str = data.get('date')
    exercises = data.get('exercises', [])
    timer_data = data.get('timer_data', {})
    cardio_sessions = data.get('cardio_sessions', [])

    if not focus_type or not date_str:
        return jsonify({"success": False, "error": "Focus vaihtoehto on valittava"}), 400

    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError) as e:
        return jsonify(success=False, error=f"Invalid date: {str(e)}"), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        safe_add_user_level_columns(cursor)
        conn.commit()

        # ============================================================================
        # STEP 1: Find the EXISTING unsaved session or create new one
        # ============================================================================
        cursor.execute("""
            SELECT id FROM workout_sessions
            WHERE user_id = %s AND date = %s AND is_saved = false
            ORDER BY id DESC
            LIMIT 1
        """, (user_id, date))
        
        existing_session = cursor.fetchone()
        
        if existing_session:
            session_id = existing_session[0]
            # Update the session name and focus_type
            cursor.execute("""
                UPDATE workout_sessions
                SET name = %s, focus_type = %s
                WHERE id = %s
            """, (name, focus_type, session_id))
            app.logger.info(f"Found existing unsaved session {session_id}, marking as saved")
        else:
            # No unsaved session exists, create a new one
            cursor.execute(
                "INSERT INTO workout_sessions (user_id, date, name, focus_type, is_saved) "
                "VALUES (%s, %s, %s, %s, false) RETURNING id",
                (user_id, date, name, focus_type)
            )
            session_id = cursor.fetchone()[0]
            app.logger.info(f"Created new workout session {session_id} named '{name}' for {date}")

        # ============================================================================
        # STEP 2: Mark ALL unsaved sets and cardio in this session as saved
        # ============================================================================
        
        # Mark all unsaved workout_sets in this session as saved
        cursor.execute("""
            UPDATE workout_sets
            SET is_saved = true
            WHERE session_id = %s AND is_saved = false
            RETURNING id
        """, (session_id,))
        updated_sets = cursor.fetchall()
        app.logger.info(f"Marked {len(updated_sets)} workout_sets as saved in session {session_id}")

        # Mark all unsaved cardio_sessions in this session as saved
        cursor.execute("""
            UPDATE cardio_sessions
            SET is_saved = true
            WHERE session_id = %s AND is_saved = false
            RETURNING id
        """, (session_id,))
        updated_cardio = cursor.fetchall()
        app.logger.info(f"Marked {len(updated_cardio)} cardio_sessions as saved in session {session_id}")

        # Now mark the session itself as saved
        cursor.execute("""
            UPDATE workout_sessions
            SET is_saved = true
            WHERE id = %s
        """, (session_id,))

        # Get ALL the sets in this session (now all marked as saved)
        cursor.execute("""
            SELECT id, exercise_id, reps, weight
            FROM workout_sets
            WHERE session_id = %s
        """, (session_id,))
        saved_sets_rows = cursor.fetchall()
        app.logger.info(f"Processing {len(saved_sets_rows)} sets for XP calculation")

        # Get ALL the cardio in this session for stats
        cursor.execute("""
            SELECT id, duration_minutes, calories_burned
            FROM cardio_sessions
            WHERE session_id = %s
        """, (session_id,))
        saved_cardio_rows = cursor.fetchall()
        app.logger.info(f"Processing {len(saved_cardio_rows)} cardio sessions for stats")

        # ============================================================================
        # STEP 3: Save timer data to the session
        # ============================================================================
        if timer_data.get('totalSeconds') is not None:
            cursor.execute(
                "UPDATE workout_sessions SET "
                "workout_duration_seconds = %s, "
                "weight_calories_burned = %s "
                "WHERE id = %s",
                (
                    int(timer_data.get('totalSeconds') or 0),
                    float(timer_data.get('calories', 0) or 0.0),
                    session_id
                )
            )

        # ============================================================================
        # STEP 4: Calculate total calories (weights + cardio) for this session
        # ============================================================================
        total_calories = float(timer_data.get('calories', 0) or 0.0)
        total_duration_seconds = int(timer_data.get('totalSeconds', 0) or 0)

        cardio_calories = 0.0
        cardio_duration = 0

        try:
            cursor.execute(
                """
                SELECT COALESCE(SUM(cs.calories_burned), 0) as total_cardio_calories,
                       COALESCE(SUM(cs.duration_minutes * 60), 0) as total_cardio_seconds
                FROM cardio_sessions cs
                WHERE cs.session_id = %s
                """,
                (session_id,)
            )
            cardio_totals = cursor.fetchone()
            if cardio_totals:
                cardio_calories = float(cardio_totals[0] or 0.0)
                cardio_duration = int(cardio_totals[1] or 0)
                total_calories += cardio_calories
                total_duration_seconds += cardio_duration
        except Exception:
            pass

        # Update session with combined totals
        cursor.execute(
            "UPDATE workout_sessions SET "
            "total_calories_burned = %s, "
            "total_duration_seconds = %s "
            "WHERE id = %s",
            (float(total_calories), int(total_duration_seconds), session_id)
        )

        # ============================================================================
        # STEP 5: Build comparison data and achievements from saved sets
        # ============================================================================
        set_comparisons = []
        personal_records = []
        improvements = []
        new_exercises_count = 0
        total_sets = 0
        current_total_volume = 0
        volume_improvements = 0
        sets_improvements = 0

        # Organize saved sets by exercise
        saved_sets_by_exercise = {}
        for set_id, exercise_id, reps, weight in saved_sets_rows:
            if exercise_id not in saved_sets_by_exercise:
                saved_sets_by_exercise[exercise_id] = []
            saved_sets_by_exercise[exercise_id].append({
                "reps": int(reps),
                "weight": float(weight)
            })

        # Process each exercise that has saved sets
        for exercise_id, current_sets in saved_sets_by_exercise.items():
            # Get exercise name from the exercises data or database
            exercise_name = "Unknown Exercise"
            for ex in exercises:
                ex_id = ex.get("id") or ex.get("exercise_id") or ex.get("exerciseId")
                if ex_id == exercise_id:
                    exercise_name = ex.get("name") or ex.get("exercise_name") or ex.get("exerciseName") or "Unknown Exercise"
                    break
            
            # If not found in exercises data, get from database
            if exercise_name == "Unknown Exercise":
                cursor.execute("SELECT name FROM exercises WHERE id = %s", (exercise_id,))
                ex_result = cursor.fetchone()
                if ex_result:
                    exercise_name = ex_result[0]

            # Get most recent SAVED session for this exercise and focus type (exclude current session)
            cursor.execute("""
                SELECT ws.id, ws.date
                FROM workout_sessions ws
                JOIN workout_sets wset ON wset.session_id = ws.id
                WHERE ws.user_id = %s
                  AND ws.focus_type = %s
                  AND wset.exercise_id = %s
                  AND ws.id != %s
                  AND ws.is_saved = true
                  AND wset.is_saved = true
                ORDER BY ws.date DESC
                LIMIT 1
            """, (current_user.id, focus_type, exercise_id, session_id))
            previous_session = cursor.fetchone()

            total_sets += len(current_sets)

            # Current session calculations
            if current_sets:
                heaviest_set = max(current_sets, key=lambda s: s["weight"])
                best_set = max(current_sets, key=lambda s: s["reps"] * s["weight"])
                total_volume_ex = sum(s["reps"] * s["weight"] for s in current_sets)
                current_total_volume += total_volume_ex
            else:
                continue

            if previous_session:
                previous_session_id, previous_date = previous_session

                # Get the last SAVED set data from previous session for this exercise
                cursor.execute("""
                    SELECT reps, weight
                    FROM workout_sets
                    WHERE session_id = %s AND exercise_id = %s AND is_saved = true
                    ORDER BY id DESC
                    LIMIT 1
                """, (previous_session_id, exercise_id))
                last_set = cursor.fetchone()

                # Get stats from previous session for this exercise (only saved sets)
                cursor.execute("""
                    SELECT COUNT(*) as set_count, COALESCE(SUM(reps * weight), 0) as total_volume
                    FROM workout_sets
                    WHERE session_id = %s AND exercise_id = %s AND is_saved = true
                """, (previous_session_id, exercise_id))
                previous_stats = cursor.fetchone()

                if last_set and previous_stats:
                    last_reps, last_weight = int(last_set[0] or 0), float(last_set[1] or 0.0)
                    last_set_count, last_total_volume_ex = int(previous_stats[0] or 0), float(previous_stats[1] or 0.0)
                    last_volume = last_reps * last_weight

                    # PRs
                    if (best_set["reps"] * best_set["weight"]) > last_volume and last_volume > 0:
                        personal_records.append({
                            "exercise": exercise_name,
                            "type": "bestSet",
                            "weight": best_set["weight"],
                            "reps": best_set["reps"],
                            "previousBest": {"weight": last_weight, "reps": last_reps}
                        })
                    if heaviest_set["weight"] > last_weight and last_weight > 0:
                        personal_records.append({
                            "exercise": exercise_name,
                            "type": "heaviestWeight",
                            "weight": heaviest_set["weight"],
                            "reps": None,
                            "previousBest": {"weight": last_weight, "reps": last_reps}
                        })

                    # Per-set comparisons
                    for idx, s in enumerate(current_sets, start=1):
                        reps = int(s.get("reps") or 0)
                        weight = float(s.get("weight") or 0.0)
                        current_volume = reps * weight
                        volume_change = current_volume - last_volume
                        set_comparisons.append({
                            "setId": f"{exercise_id}-{idx}",
                            "exerciseId": exercise_id,
                            "currentReps": reps,
                            "currentWeight": weight,
                            "currentVolume": current_volume,
                            "previousReps": last_reps,
                            "previousWeight": last_weight,
                            "previousVolume": last_volume,
                            "volumeChange": volume_change,
                            "noPrevious": False,
                            "isNew": False
                        })

                    # Improvements
                    if total_volume_ex > last_total_volume_ex:
                        volume_improvements += 1
                        improvements.append({
                            "exercise": exercise_name,
                            "type": "volume",
                            "volumeChange": total_volume_ex - last_total_volume_ex
                        })

                    if len(current_sets) > last_set_count:
                        sets_improvements += 1
                        improvements.append({
                            "exercise": exercise_name,
                            "type": "sets",
                            "setsChange": len(current_sets) - last_set_count
                        })
                else:
                    # Previous session exists but no data for this exercise
                    new_exercises_count += 1
                    for idx, s in enumerate(current_sets, start=1):
                        reps = int(s.get("reps") or 0)
                        weight = float(s.get("weight") or 0.0)
                        current_volume = reps * weight
                        set_comparisons.append({
                            "setId": f"{exercise_id}-{idx}",
                            "exerciseId": exercise_id,
                            "currentReps": reps,
                            "currentWeight": weight,
                            "currentVolume": current_volume,
                            "previousReps": 0,
                            "previousWeight": 0.0,
                            "previousVolume": 0.0,
                            "volumeChange": current_volume,
                            "noPrevious": True,
                            "isNew": True
                        })
            else:
                # First time doing this exercise in this focus type
                new_exercises_count += 1
                for idx, s in enumerate(current_sets, start=1):
                    reps = int(s.get("reps") or 0)
                    weight = float(s.get("weight") or 0.0)
                    current_volume = reps * weight
                    set_comparisons.append({
                        "setId": f"{exercise_id}-{idx}",
                        "exerciseId": exercise_id,
                        "currentReps": reps,
                        "currentWeight": weight,
                        "currentVolume": current_volume,
                        "previousReps": 0,
                        "previousWeight": 0.0,
                        "previousVolume": 0.0,
                        "volumeChange": current_volume,
                        "noPrevious": True,
                        "isNew": True
                    })

        # Get previous session totals for same focus_type (exclude current session)
        cursor.execute("""
            SELECT ws.id
            FROM workout_sessions ws
            WHERE ws.user_id = %s
            AND ws.focus_type = %s
            AND ws.name = %s
            AND ws.id != %s
            AND ws.is_saved = true
            ORDER BY ws.date DESC
            LIMIT 1
        """, (current_user.id, focus_type, name, session_id))
        last_session_result = cursor.fetchone()

        if not last_session_result:
            cursor.execute("""
                SELECT ws.id
                FROM workout_sessions ws
                WHERE ws.user_id = %s
                AND ws.focus_type = %s
                AND ws.id != %s
                AND ws.is_saved = true
                ORDER BY ws.date DESC
                LIMIT 1
            """, (current_user.id, focus_type, session_id))
            last_session_result = cursor.fetchone()

        last_total_volume = 0.0
        last_total_sets = 0

        if last_session_result:
            last_session_id = last_session_result[0]

            cursor.execute("""
                SELECT COALESCE(SUM(reps * weight), 0) as total_volume
                FROM workout_sets
                WHERE session_id = %s AND is_saved = true
            """, (last_session_id,))
            volume_result = cursor.fetchone()
            last_total_volume = float(volume_result[0] or 0.0)

            cursor.execute("""
                SELECT COUNT(*) as total_sets
                FROM workout_sets
                WHERE session_id = %s AND is_saved = true
            """, (last_session_id,))
            sets_result = cursor.fetchone()
            last_total_sets = int(sets_result[0] or 0)

        volume_change_percent = ((current_total_volume - last_total_volume) / last_total_volume * 100.0) if last_total_volume else 0.0
        sets_change = total_sets - last_total_sets

        conn.commit()

        # ============================================================================
        # STEP 6: Auto-add workout calories to TDEE if enabled
        # ============================================================================
        auto_calories_enabled = False
        daily_tdee = None
        base_tdee = None
        try:
            cursor.execute(
                "SELECT auto_add_workout_calories, tdee FROM users WHERE id = %s",
                (user_id,)
            )
            user_settings = cursor.fetchone()

            if user_settings and user_settings[0]:
                auto_calories_enabled = True
                base_tdee = float(user_settings[1] or 0.0)
                
                # Get total workout calories for the entire day (all saved sessions)
                cursor.execute("""
                    SELECT COALESCE(SUM(total_calories_burned), 0)
                    FROM workout_sessions
                    WHERE user_id = %s AND date = %s AND is_saved = true
                """, (user_id, date))
                day_total_calories = float(cursor.fetchone()[0] or 0.0)
                
                daily_tdee = base_tdee + day_total_calories

                cursor.execute("""
                    INSERT INTO daily_tdee_adjustments (user_id, date, base_tdee, workout_calories, adjusted_tdee)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, date)
                    DO UPDATE SET
                        base_tdee = EXCLUDED.base_tdee,
                        workout_calories = EXCLUDED.workout_calories,
                        adjusted_tdee = EXCLUDED.adjusted_tdee,
                        updated_at = NOW()
                """, (user_id, date, base_tdee, day_total_calories, daily_tdee))
        except Exception:
            pass

        # ============================================================================
        # STEP 7: XP REWARDS LOGIC
        # ============================================================================
        xp_sources = {}
        
        xp_cardio_duration = float(cardio_duration) * 0.01
        xp_sources['cardio_duration'] = xp_cardio_duration
        xp_cardio_calories = float(cardio_calories) * 0.2
        xp_sources['cardio_calories'] = xp_cardio_calories
        xp_weights_volume = float(current_total_volume) * 0.03
        xp_sources['weights_volume'] = xp_weights_volume
        xp_new_exercises = int(new_exercises_count) * 25.0
        xp_sources['new_exercises'] = xp_new_exercises
        xp_personal_bests = float(len(personal_records)) * 30.0
        xp_sources['personal_bests'] = xp_personal_bests
        
        xp_gain = int(round(sum(xp_sources.values())))

        cursor.execute("SELECT COALESCE(xp_points,0), COALESCE(level,1) FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        current_xp = int(row[0] or 0)
        current_level = clamp_level(int(row[1] or 1))

        new_levels = 0
        pool = current_xp + xp_gain
        level_cursor = current_level

        while pool >= xp_to_next_level(level_cursor) and level_cursor < LEVEL_CAP:
            need = xp_to_next_level(level_cursor)
            pool -= need
            level_cursor += 1
            new_levels += 1
            if level_cursor >= LEVEL_CAP:
                level_cursor = LEVEL_CAP
                pool = 0
                break

        cursor.execute(
            "UPDATE users SET xp_points = %s, level = %s WHERE id = %s",
            (int(pool), int(level_cursor), user_id)
        )

        conn.commit()

        # ============================================================================
        # STEP 8: Return response
        # ============================================================================
        return jsonify({
            "success": True,
            "session_id": session_id,
            "session_name": name,
            "exercises_saved": len(saved_sets_by_exercise),
            "timer_data": {
                "totalSeconds": int(timer_data.get('totalSeconds') or 0),
                "calories": float(timer_data.get('calories', 0) or 0.0)
            },
            "total_calories": float(total_calories),
            "total_duration_seconds": int(total_duration_seconds),
            "auto_calories_enabled": bool(auto_calories_enabled),
            "base_tdee": float(base_tdee) if base_tdee is not None else None,
            "daily_tdee": float(daily_tdee) if daily_tdee is not None else None,
            "comparisonData": {
                "setComparisons": set_comparisons,
                "totalSets": int(total_sets),
                "setsChange": int(sets_change),
                "totalVolume": float(current_total_volume),
                "volumeChange": float(round(volume_change_percent, 2))
            },
            "achievements": {
                "personalRecords": personal_records,
                "improvements": improvements,
                "newExercises": int(new_exercises_count),
                "volumeImprovements": int(volume_improvements),
                "setsImprovements": int(sets_improvements)
            },
            "xp": {
                "gained": int(xp_gain),
                "sources": {
                    "cardio_duration": int(round(xp_cardio_duration)),
                    "cardio_calories": int(round(xp_cardio_calories)),
                    "weights_volume": int(round(xp_weights_volume)),
                    "new_exercises": int(round(xp_new_exercises)),
                    "personal_bests": int(round(xp_personal_bests))
                },
                "levels_gained": int(new_levels),
                "level_before": int(current_level),
                "level_after": int(level_cursor),
                "current_xp": int(pool),
                "xp_to_next_level": int(xp_to_next_level(level_cursor))
            }
        })

    except Exception as e:
        conn.rollback()
        import traceback
        app.logger.error(f"Error in /workout/save: {str(e)}")
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "error": f"Database error: {str(e)}"}), 500
    finally:
        cursor.close()
        conn.close()







def get_oauth_connection(provider, provider_user_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute(
        'SELECT * FROM oauth_connections WHERE provider = %s AND provider_user_id = %s',
        (provider, provider_user_id)
    )
    connection = cursor.fetchone()
    conn.close()
    return connection

def create_oauth_connection(user_id, provider, provider_user_id, access_token):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO oauth_connections (user_id, provider, provider_user_id, access_token) '
        'VALUES (%s, %s, %s, %s) '
        'ON CONFLICT (provider, provider_user_id) DO UPDATE SET access_token = EXCLUDED.access_token',
        (user_id, provider, provider_user_id, access_token)
    )
    conn.commit()
    conn.close()

def get_user_by_oauth(provider, provider_user_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute('''
        SELECT u.* FROM users u 
        JOIN oauth_connections oc ON u.id = oc.user_id 
        WHERE oc.provider = %s AND oc.provider_user_id = %s
    ''', (provider, provider_user_id))
    user = cursor.fetchone()
    conn.close()
    return user
@app.route('/login/<provider>')
def oauth_login(provider):
    if provider == 'google':
        redirect_uri = url_for('oauth_authorize', provider='google', _external=True)
        return google.authorize_redirect(redirect_uri)
    elif provider == 'github':
        redirect_uri = url_for('oauth_authorize', provider='github', _external=True)
        return github.authorize_redirect(redirect_uri)
    elif provider == 'facebook':
        redirect_uri = url_for('oauth_authorize', provider='facebook', _external=True)
        return facebook.authorize_redirect(redirect_uri)
    else:
        flash('Unsupported OAuth provider', 'danger')
        return redirect(url_for('login'))

@app.route('/oauth/authorize/<provider>')
def oauth_authorize(provider):
    try:
        if provider == 'google':
            token = google.authorize_access_token()
            resp = google.get('userinfo')
            userinfo = resp.json()
            email = userinfo['email']
            provider_user_id = userinfo['sub']
        elif provider == 'github':
            token = github.authorize_access_token()
            resp = github.get('user')
            userinfo = resp.json()
            email = userinfo.get('email')
        elif provider == 'facebook':
            token = facebook.authorize_access_token()
            resp = facebook.get('me?fields=id,name,email')
            userinfo = resp.json()
            email = userinfo.get('email')
            provider_user_id = str(userinfo['id'])
            # If email is not public, make another request to get emails
            if not email:
                resp = github.get('user/emails')
                emails = resp.json()
                email = next((e['email'] for e in emails if e['primary']), emails[0]['email'])
            provider_user_id = str(userinfo['id'])
        else:
            flash('Unsupported OAuth provider', 'danger')
            return redirect(url_for('login'))
        
        # Check if we already have this OAuth connection
        existing_connection = get_oauth_connection(provider, provider_user_id)
        
        if existing_connection:
            # Existing user - log them in
            user = load_user(existing_connection['user_id'])
            login_user(user)
            return redirect(url_for('index'))
        
        # Check if user with this email already exists
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        
        if user:
            # Link OAuth to existing account
            create_oauth_connection(user['id'], provider, provider_user_id, token['access_token'])
            user_obj = User(
                id=user['id'],
                username=user['username'],
                email=user['email'],
                role=user['role']
            )
            login_user(user_obj)
            return redirect(url_for('index', toast_msg='Käyttäjätili yhdisttety onnistuneesti!', toast_cat='success'))
        else:
            # Create new user
            username = email.split('@')[0]
            # Ensure username is unique
            counter = 1
            base_username = username
            while True:
                cursor.execute('SELECT id FROM users WHERE username = %s', (username,))
                if not cursor.fetchone():
                    break
                username = f"{base_username}_{counter}"
                counter += 1
            
            # Create user without password
            hashed_password = bcrypt.generate_password_hash(str(uuid.uuid4())).decode('utf-8')
            cursor.execute(
                'INSERT INTO users (username, email, password) VALUES (%s, %s, %s) RETURNING id',
                (username, email, hashed_password)
            )
            user_id = cursor.fetchone()[0]
            conn.commit()
            
            # Create OAuth connection
            create_oauth_connection(user_id, provider, provider_user_id, token['access_token'])
            
            user_obj = User(
                id=user_id,
                username=username,
                email=email,
                role='user'
            )
            login_user(user_obj)
            flash(f'Käyttäjätili luotu käyttäen {provider}!', 'success')
            return redirect(url_for('index'))
            
    except Exception as e:
        flash(f'OAuth kirjautuminen epäonnistui: {str(e)}', 'danger')
        return redirect(url_for('login'))
    
@app.route('/scan_nutrition_label', methods=['POST'])
def scan_nutrition_label():
    try:
        # Load image_data (unchanged)…
        image_data = None
        if 'file' in request.files and request.files['file'].filename:
            image_data = request.files['file'].read()
        else:
            raw = request.form.get('image', '')
            if raw.startswith('data:'):
                raw = raw.split(',',1)[1]
            image_data = base64.b64decode(raw) if raw else None
        if not image_data:
            return jsonify(success=False, error='No image provided'), 400

        # OCR scan
        scanner = get_scanner()
        result = scanner.scan_nutrition_label(image_data)

        # Normalize keys
        form_data = {}
        if result.get('success'):
            data = result['nutrition_data']
            # Map alternate saturated keys
            if 'saturatedfats' in data and 'saturated' not in data:
                data['saturated'] = data['saturatedfats']
            if 'saturated_fats' in data and 'saturated' not in data:
                data['saturated'] = data['saturated_fats']
            # Build output
            for key in ['calories','fats','saturated','carbs','fiber','proteins','salt','sugars']:
                if key in data:
                    form_data[key] = round(data[key],1)

        # Return form_data + raw_text for debugging
        return jsonify(
            success=result.get('success', False),
            form_data=form_data,
            raw_text=result.get('raw_text', []),
            per_100g=result.get('per_100g', True),
            message=result.get('message','')
        ), (200 if result.get('success') else 500)

    except Exception as e:
        return jsonify(success=False, error=str(e)), 500
@app.route("/workout/similar_names", methods=["POST"])
@login_required
def get_similar_workout_names():
    data = request.get_json()
    query = data.get("query", "").strip()
    
    if len(query) < 2:  # Only search after 2+ characters
        return jsonify({"suggestions": []})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Find similar workout names using ILIKE for case-insensitive partial matching
        cursor.execute("""
            SELECT DISTINCT name, date, focus_type, id
            FROM workout_sessions 
            WHERE user_id = %s 
            AND name ILIKE %s 
            AND name != %s
            ORDER BY date DESC
            LIMIT 5
        """, (current_user.id, f"%{query}%", query))
        
        suggestions = []
        for row in cursor.fetchall():
            suggestions.append({
                "name": row[0],
                "date": row[1].strftime("%Y-%m-%d"),
                "focus_type": row[2],
                "session_id": row[3]
            })
        
        return jsonify({"suggestions": suggestions})
        
    except Exception as e:
        return jsonify({"suggestions": [], "error": str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route("/workout/copy_from_session", methods=["POST"])
@login_required
def copy_from_session():
    session_id = request.form.get("session_id")
    target_date = request.form.get("target_date")
    
    print(f"DEBUG: session_id={session_id}, target_date={target_date}")
    
    if not session_id or not target_date:
        return jsonify({"success": False, "error": "Missing session_id or target_date"})
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    
    try:
        # Get the source session with debug info
        cursor.execute("""
            SELECT * FROM workout_sessions 
            WHERE id = %s AND user_id = %s
        """, (session_id, current_user.id))
        
        source_session = cursor.fetchone()
        print(f"DEBUG: Source session found: {source_session}")
        
        if not source_session:
            return jsonify({"success": False, "error": "Source session not found"})
        
        # Delete existing target session if it exists
        cursor.execute("""
            DELETE FROM workout_sessions 
            WHERE user_id = %s AND date = %s
        """, (current_user.id, target_date))
        
        deleted_count = cursor.rowcount
        print(f"DEBUG: Deleted {deleted_count} existing sessions for target date")
        
        # Create new session for target date
        cursor.execute("""
            INSERT INTO workout_sessions (user_id, date, name, focus_type)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (
            current_user.id, 
            target_date, 
            source_session["name"], 
            source_session["focus_type"]
        ))
        
        new_session_result = cursor.fetchone()
        new_session_id = new_session_result["id"]
        print(f"DEBUG: Created new session with ID: {new_session_id}")
        
        # Get sets from source session
        cursor.execute("""
            SELECT exercise_id, reps, weight, rir, comments
            FROM workout_sets 
            WHERE session_id = %s
        """, (session_id,))
        
        source_sets = cursor.fetchall()
        print(f"DEBUG: Found {len(source_sets)} sets to copy")
        
        # Copy all sets from source session
        sets_copied = 0
        for set_data in source_sets:
            cursor.execute("""
                INSERT INTO workout_sets (session_id, exercise_id, reps, weight, rir, comments)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                new_session_id, 
                set_data["exercise_id"], 
                set_data["reps"], 
                set_data["weight"], 
                set_data["rir"], 
                set_data["comments"]
            ))
            sets_copied += 1
        
        print(f"DEBUG: Successfully copied {sets_copied} sets")
        conn.commit()
        
        return jsonify({
            "success": True, 
            "message": f"Copied {sets_copied} sets to {target_date}",
            "debug": {
                "source_session_id": session_id,
                "new_session_id": new_session_id,
                "sets_copied": sets_copied
            }
        })
        
    except Exception as e:
        print(f"DEBUG: Error in copy_from_session: {str(e)}")
        conn.rollback()
        return jsonify({"success": False, "error": str(e)})
    finally:
        cursor.close()
        conn.close()
@app.route('/workout/cardio-exercises')
@login_required
def get_cardio_exercises():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    
    try:
        cursor.execute('''
            SELECT id, name, type, met_value, description
            FROM cardio_exercises
            ORDER BY type, met_value
        ''')
        
        exercises = []
        for row in cursor.fetchall():
            exercises.append({
                'id': row['id'],
                'name': row['name'],
                'type': row['type'],
                'met_value': float(row['met_value']),
                'description': row['description']
            })
        
        # Group by type for easier frontend handling
        grouped_exercises = {}
        for exercise in exercises:
            exercise_type = exercise['type']
            if exercise_type not in grouped_exercises:
                grouped_exercises[exercise_type] = []
            grouped_exercises[exercise_type].append(exercise)
        
        return jsonify(exercises=grouped_exercises)
        
    except Exception as e:
        app.logger.error(f"Cardio Exercises Error: {str(e)}")
        return jsonify(error="Could not load cardio exercises"), 500
    finally:
        conn.close()

# Add cardio session endpoint
@app.route('/workout/add-cardio', methods=['POST'])
@login_required
def add_cardio_session():
    user_id = current_user.id
    data = request.json

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)

    try:
        # ✅ Validate and parse date
        date_str = data.get('date', datetime.now().strftime("%Y-%m-%d"))
        try:
            session_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify(error="Invalid date format"), 400

        # ✅ Validate required fields
        if not data.get('cardio_exercise_id') or not data.get('duration_minutes'):
            return jsonify(error="Missing required fields"), 400

        # ✅ Check for duplicate cardio session
        cursor.execute('''
            SELECT cs.id FROM cardio_sessions cs
            JOIN workout_sessions ws ON cs.session_id = ws.id
            WHERE ws.user_id = %s AND ws.date = %s 
            AND cs.cardio_exercise_id = %s AND cs.duration_minutes = %s
            AND cs.created_at > NOW() - INTERVAL '5 seconds'
        ''', (user_id, session_date, data['cardio_exercise_id'], data['duration_minutes']))
        
        existing = cursor.fetchone()
        if existing:
            return jsonify(error="Duplicate cardio session detected"), 409

        # ✅ Get user weight & gender from database (with fallback)
        cursor.execute('SELECT weight, gender FROM users WHERE id = %s', (user_id,))
        user_record = cursor.fetchone()
        
        if user_record and user_record['weight']:
            weight_kg = float(user_record['weight'])
        else:
            weight_kg = data.get('weight_kg', 70.0)
            
        gender = (user_record['gender'].lower() if user_record and user_record['gender'] else "male")

        app.logger.info(f"Using weight: {weight_kg}kg, gender: {gender} for user {user_id}")

        # ============================================================================
        # CRITICAL: Use SAME logic as save_set - find or create UNSAVED session
        # ============================================================================
        cursor.execute('''
            SELECT id FROM workout_sessions 
            WHERE user_id = %s AND date = %s AND is_saved = false
            ORDER BY id DESC LIMIT 1
        ''', (user_id, session_date))

        session = cursor.fetchone()
        if not session:
            cursor.execute('''
                INSERT INTO workout_sessions (user_id, date, name, focus_type, is_saved)
                VALUES (%s, %s, %s, %s, false) RETURNING id
            ''', (user_id, session_date, 'Unnamed Workout', 'general'))
            session_id = cursor.fetchone()['id']
            app.logger.info(f"Created new unsaved session {session_id} for cardio on date {session_date}")
        else:
            session_id = session['id']
            app.logger.info(f"Using existing unsaved session {session_id} for cardio on date {session_date}")

        # ✅ Get cardio exercise details
        cursor.execute('''
            SELECT met_value, name FROM cardio_exercises WHERE id = %s
        ''', (data['cardio_exercise_id'],))

        exercise = cursor.fetchone()
        if not exercise:
            return jsonify(error="Cardio exercise not found"), 404

        met_value = float(exercise['met_value'])
        duration_minutes = float(data['duration_minutes'])
        duration_hours = duration_minutes / 60.0

        # ✅ Calories burned calculation
        calories_burned = 0
        calculation_method = "MET"

        # Method 1: Watts-based
        if data.get('watts') and float(data['watts']) > 0:
            watts = float(data['watts'])
            calories_burned = watts * duration_hours * 3.6
            calculation_method = "Watts"

        # Method 2: Distance-based (running/walking)
        elif data.get('distance_km') and float(data['distance_km']) > 0:
            distance_km = float(data['distance_km'])
            speed_kmh = distance_km / duration_hours
            
            if speed_kmh > 6:  # Running
                if speed_kmh >= 16:
                    running_met = 15.0
                elif speed_kmh >= 13:
                    running_met = 12.0
                elif speed_kmh >= 11:
                    running_met = 11.0
                elif speed_kmh >= 9:
                    running_met = 9.0
                elif speed_kmh >= 8:
                    running_met = 8.0
                else:
                    running_met = 7.0
                    
                calories_burned = running_met * weight_kg * duration_hours
                calculation_method = f"Distance-Running ({speed_kmh:.1f} km/h)"
            else:  # Walking
                if speed_kmh >= 5.5:
                    walking_met = 4.3
                elif speed_kmh >= 4.8:
                    walking_met = 3.8
                elif speed_kmh >= 4.0:
                    walking_met = 3.5
                elif speed_kmh >= 3.2:
                    walking_met = 3.0
                else:
                    walking_met = 2.5
                    
                calories_burned = walking_met * weight_kg * duration_hours
                calculation_method = f"Distance-Walking ({speed_kmh:.1f} km/h)"

        # Method 3: Standard MET
        else:
            calories_burned = met_value * weight_kg * duration_hours
            calculation_method = "MET"

        # ✅ Heart rate adjustment (overrides other calculations)
        if data.get('avg_heart_rate') and data.get('age'):
            hr = float(data['avg_heart_rate'])
            age = float(data['age'])
            
            if gender == 'male':
                calories_burned = duration_minutes * (0.6309 * hr + 0.1988 * weight_kg + 0.2017 * age - 55.0969) / 4.184
            else:
                calories_burned = duration_minutes * (0.4472 * hr - 0.1263 * weight_kg + 0.074 * age - 20.4022) / 4.184
            
            calculation_method = f"Heart Rate ({hr} bpm)"

        calories_burned = max(0, calories_burned)

        # ✅ Insert cardio session with is_saved = false
        cursor.execute('''
            INSERT INTO cardio_sessions 
            (session_id, cardio_exercise_id, duration_minutes, distance_km, 
             avg_pace_min_per_km, avg_heart_rate, watts, calories_burned, notes, is_saved, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, false, NOW())
            RETURNING id
        ''', (
            session_id,
            data['cardio_exercise_id'],
            duration_minutes,
            data.get('distance_km'),
            data.get('avg_pace_min_per_km'),
            data.get('avg_heart_rate'),
            data.get('watts'),
            calories_burned,
            data.get('notes', '')
        ))

        cardio_session_id = cursor.fetchone()['id']
        conn.commit()

        return jsonify({
            'success': True,
            'cardio_session_id': cardio_session_id,
            'calories_burned': round(calories_burned, 1),
            'calculation_method': calculation_method,
            'weight_used': weight_kg,
            'gender_used': gender,
            'session_id': session_id,
            'exercise_name': exercise['name']
        })

    except Exception as e:
        conn.rollback()
        app.logger.error(f"Add Cardio Error: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify(error="Could not add cardio session"), 500
    finally:
        conn.close()




# Delete cardio session
@app.route('/workout/cardio-sessions/<int:session_id>', methods=['DELETE'])
@login_required
def delete_cardio_session(session_id):
    user_id = current_user.id
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    
    try:
        # ✅ Get session details before deletion for logging
        cursor.execute('''
            SELECT cs.id, ce.name as exercise_name, ws.date
            FROM cardio_sessions cs
            JOIN workout_sessions ws ON cs.session_id = ws.id
            JOIN cardio_exercises ce ON cs.cardio_exercise_id = ce.id
            WHERE cs.id = %s AND ws.user_id = %s
        ''', (session_id, user_id))
        
        session_info = cursor.fetchone()
        if not session_info:
            return jsonify(error="Cardio session not found"), 404
        
        # ✅ Delete only the specific cardio session
        cursor.execute('DELETE FROM cardio_sessions WHERE id = %s', (session_id,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        
        app.logger.info(f"Deleted cardio session {session_id} ({session_info['exercise_name']}) for user {user_id} on {session_info['date']}, rows affected: {deleted_count}")
        
        return jsonify({
            'success': True, 
            'deleted_id': session_id,
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        conn.rollback()
        app.logger.error(f"Delete Cardio Session Error: {str(e)}")
        return jsonify(error="Could not delete cardio session"), 500
    finally:
        conn.close()
@app.route('/user/profile-data', methods=['GET'])
@login_required
def get_user_profile_data():
    """Get user profile data (weight, gender) for frontend calculations"""
    user_id = current_user.id
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    
    try:
        cursor.execute('SELECT weight, gender FROM users WHERE id = %s', (user_id,))
        user_record = cursor.fetchone()
        
        if user_record:
            return jsonify({
                'success': True,
                'weight': user_record['weight'],
                'gender': user_record['gender']
            })
        else:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
            
    except Exception as e:
        app.logger.error(f"Get User Profile Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Could not get user profile data'
        }), 500
    finally:
        conn.close()

@app.route('/workout/history/muscle/<muscle_group>', methods=['GET'])
@login_required
def workout_history_muscle_detail(muscle_group):
    """Get detailed exercise data for a specific muscle group WITH PR indicators"""
    user_id = current_user.id
    period = request.args.get('period', 'daily')
    date_filter = request.args.get('date')
    week_start = request.args.get('week_start')
    month_start = request.args.get('month_start')
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    
    try:
        if period == 'daily' and date_filter:
            cursor.execute('''
                SELECT 
                    e.id as exercise_id,
                    e.name as exercise_name,
                    ws.reps,
                    ws.weight,
                    ws.volume,
                    ws.id
                FROM workout_sessions s
                JOIN workout_sets ws ON s.id = ws.session_id
                JOIN exercises e ON ws.exercise_id = e.id
                WHERE s.user_id = %s 
                AND s.date = %s
                AND LOWER(e.muscle_group) = LOWER(%s)
                AND ws.is_saved = TRUE
                ORDER BY e.name, ws.id
            ''', (user_id, date_filter, muscle_group))
            
        elif period == 'weekly' and week_start:
            cursor.execute('''
                SELECT 
                    e.id as exercise_id,
                    e.name as exercise_name,
                    ws.reps,
                    ws.weight,
                    ws.volume,
                    ws.id,
                    s.date
                FROM workout_sessions s
                JOIN workout_sets ws ON s.id = ws.session_id
                JOIN exercises e ON ws.exercise_id = e.id
                WHERE s.user_id = %s 
                AND s.date >= %s::date
                AND s.date < %s::date + INTERVAL '7 days'
                AND LOWER(e.muscle_group) = LOWER(%s)
                AND ws.is_saved = TRUE
                ORDER BY e.name, s.date DESC, ws.id
            ''', (user_id, week_start, week_start, muscle_group))
            
        elif period == 'monthly' and month_start:
            cursor.execute('''
                SELECT 
                    e.id as exercise_id,
                    e.name as exercise_name,
                    ws.reps,
                    ws.weight,
                    ws.volume,
                    ws.id,
                    s.date
                FROM workout_sessions s
                JOIN workout_sets ws ON s.id = ws.session_id
                JOIN exercises e ON ws.exercise_id = e.id
                WHERE s.user_id = %s 
                AND DATE_TRUNC('month', s.date) = %s::date
                AND LOWER(e.muscle_group) = LOWER(%s)
                AND ws.is_saved = TRUE
                ORDER BY e.name, s.date DESC, ws.id
            ''', (user_id, month_start, muscle_group))
        else:
            return jsonify(error="Invalid parameters"), 400
            
        rows = cursor.fetchall()
        
        # Group by exercise and check for PRs
        exercises = {}
        for row in rows:
            ex_id = row['exercise_id']
            ex_name = row['exercise_name']
            
            if ex_id not in exercises:
                exercises[ex_id] = {
                    'exercise_id': ex_id,
                    'exercise_name': ex_name,
                    'sets': []
                }
            
            # Calculate set number
            set_number = len(exercises[ex_id]['sets']) + 1
            
            # Check if this is a PR (heaviest weight for this exercise)
            cursor.execute('''
                SELECT MAX(weight) as max_weight
                FROM workout_sets ws
                JOIN workout_sessions s ON ws.session_id = s.id
                WHERE s.user_id = %s 
                AND ws.exercise_id = %s
                AND s.date < %s
                AND ws.is_saved = TRUE
            ''', (user_id, ex_id, date_filter if date_filter else row.get('date')))
            
            prev_max = cursor.fetchone()
            prev_max_weight = float(prev_max['max_weight'] or 0) if prev_max else 0
            current_weight = float(row['weight'] or 0)
            
            # PR flags
            is_heaviest_weight = current_weight > prev_max_weight and prev_max_weight > 0
            
            # Check for best set (weight * reps)
            current_volume_per_set = current_weight * int(row['reps'] or 0)
            cursor.execute('''
                SELECT MAX(reps * weight) as max_volume
                FROM workout_sets ws
                JOIN workout_sessions s ON ws.session_id = s.id
                WHERE s.user_id = %s 
                AND ws.exercise_id = %s
                AND s.date < %s
                AND ws.is_saved = TRUE
            ''', (user_id, ex_id, date_filter if date_filter else row.get('date')))
            
            prev_best = cursor.fetchone()
            prev_best_volume = float(prev_best['max_volume'] or 0) if prev_best else 0
            is_best_set = current_volume_per_set > prev_best_volume and prev_best_volume > 0
            
            exercises[ex_id]['sets'].append({
                'set_number': set_number,
                'reps': row['reps'],
                'weight': current_weight,
                'volume': float(row['volume'] or 0),
                'date': row.get('date', date_filter),
                'is_heaviest_weight': is_heaviest_weight,
                'is_best_set': is_best_set,
                'has_pr': is_heaviest_weight or is_best_set
            })
        
        return jsonify(exercises=list(exercises.values()))
        
    except Exception as e:
        app.logger.error(f"Muscle detail error: {str(e)}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify(error="Could not load muscle group details"), 500
    finally:
        conn.close()


@app.route('/workout/history/cardio', methods=['GET'])
@login_required
def workout_history_cardio():
    """Get cardio session history for a given period"""
    user_id = current_user.id
    period = request.args.get('period', 'daily')
    date_filter = request.args.get('date')
    week_start = request.args.get('week_start')
    month_start = request.args.get('month_start')
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    
    try:
        if period == 'daily' and date_filter:
            cursor.execute('''
                SELECT DISTINCT
                    cs.id,
                    cs.duration_minutes,
                    cs.distance_km,
                    cs.avg_pace_min_per_km,
                    cs.avg_heart_rate,
                    cs.watts,
                    cs.calories_burned,
                    cs.notes,
                    ce.name as exercise_name,
                    ce.type as exercise_type,
                    ce.met_value,
                    cs.created_at
                FROM cardio_sessions cs
                JOIN workout_sessions ws ON cs.session_id = ws.id
                JOIN cardio_exercises ce ON cs.cardio_exercise_id = ce.id
                WHERE ws.user_id = %s 
                AND ws.date = %s
                AND cs.is_saved = TRUE
                ORDER BY cs.created_at DESC, cs.id DESC
            ''', (user_id, date_filter))
            
        elif period == 'weekly' and week_start:
            cursor.execute('''
                SELECT DISTINCT
                    cs.id,
                    cs.duration_minutes,
                    cs.distance_km,
                    cs.avg_pace_min_per_km,
                    cs.avg_heart_rate,
                    cs.watts,
                    cs.calories_burned,
                    cs.notes,
                    ce.name as exercise_name,
                    ce.type as exercise_type,
                    ce.met_value,
                    cs.created_at,
                    ws.date
                FROM cardio_sessions cs
                JOIN workout_sessions ws ON cs.session_id = ws.id
                JOIN cardio_exercises ce ON cs.cardio_exercise_id = ce.id
                WHERE ws.user_id = %s 
                AND ws.date >= %s::date
                AND ws.date < %s::date + INTERVAL '7 days'
                AND cs.is_saved = TRUE
                ORDER BY ws.date DESC, cs.created_at DESC, cs.id DESC
            ''', (user_id, week_start, week_start))
            
        elif period == 'monthly' and month_start:
            cursor.execute('''
                SELECT DISTINCT
                    cs.id,
                    cs.duration_minutes,
                    cs.distance_km,
                    cs.avg_pace_min_per_km,
                    cs.avg_heart_rate,
                    cs.watts,
                    cs.calories_burned,
                    cs.notes,
                    ce.name as exercise_name,
                    ce.type as exercise_type,
                    ce.met_value,
                    cs.created_at,
                    ws.date
                FROM cardio_sessions cs
                JOIN workout_sessions ws ON cs.session_id = ws.id
                JOIN cardio_exercises ce ON cs.cardio_exercise_id = ce.id
                WHERE ws.user_id = %s 
                AND DATE_TRUNC('month', ws.date) = %s::date
                AND cs.is_saved = TRUE
                ORDER BY ws.date DESC, cs.created_at DESC, cs.id DESC
            ''', (user_id, month_start))
        else:
            return jsonify(cardio_sessions=[])
            
        rows = cursor.fetchall()
        
        cardio_sessions = []
        for row in rows:
            session = {
                'cardio_type': row['exercise_name'],
                'exercise_type': row['exercise_type'],
                'duration_minutes': row['duration_minutes'],
                'distance_km': float(row['distance_km'] or 0),
                'avg_pace_min_per_km': row['avg_pace_min_per_km'],
                'avg_heart_rate': row['avg_heart_rate'],
                'watts': row['watts'],
                'calories_burned': float(row['calories_burned'] or 0),
                'notes': row['notes'],
                'met_value': row['met_value'],
                'date': row.get('date')
            }
            cardio_sessions.append(session)
        
        return jsonify(cardio_sessions=cardio_sessions)
        
    except Exception as e:
        app.logger.error(f"Cardio history error: {str(e)}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify(error="Could not load cardio sessions"), 500
    finally:
        conn.close()

            
@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory('static', 'manifest.json', mimetype='application/manifest+json')

@app.route('/sw.js')
def serve_sw():
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

@app.route('/offline.html')
def offline():
    return render_template('offline.html')
@app.route('/sitemap.xml', methods=['GET'])
def sitemap():
    pages = []
    ten_days_ago = (datetime.now()).date().isoformat()

    # Loop through all registered routes
    for rule in app.url_map.iter_rules():
        # Skip special routes
        if "GET" in rule.methods and not any([
            rule.rule.startswith("/static"),
            rule.rule.startswith("/api"),
            "<" in rule.rule  # exclude dynamic URLs like /user/<id>
        ]):
            url = url_for(rule.endpoint, _external=True)
            pages.append(url)

    # Build the XML sitemap
    sitemap_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    )

    for page in pages:
        sitemap_xml += f"""
        <url>
            <loc>{page}</loc>
            <lastmod>{ten_days_ago}</lastmod>
        </url>"""
    sitemap_xml += "</urlset>"

    return Response(sitemap_xml, mimetype='application/xml')

@app.route('/main')
@login_required
@admin_required
def main():
    """Main page with workout of the week, news, and best lifts of today"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    
    # User is already authenticated and verified as admin by the decorators above
    # No need to check is_admin or role here
    
    # Fetch published news posts
    cursor.execute("""
        SELECT np.*, u.username 
        FROM news_post np
        JOIN "users" u ON np.author_id = u.id
        WHERE np.is_published = TRUE
        ORDER BY np.created_at DESC
        LIMIT 4
    """)
    news_posts = cursor.fetchall()
    
    try:
        # Get today's date
        today = datetime.now().date()
        
        # Get top 20 best lifts of today (highest volume in a single set)
        cursor.execute("""
            SELECT 
                u.id as user_id,
                u.username,
                u.avatar,
                COALESCE(u.level, 1) as level,
                e.name as exercise_name,
                ws.reps,
                ws.weight,
                (ws.reps * ws.weight) as volume
            FROM workout_sets ws
            JOIN workout_sessions wses ON ws.session_id = wses.id
            JOIN users u ON wses.user_id = u.id
            JOIN exercises e ON ws.exercise_id = e.id
            WHERE wses.date = %s
            AND ws.is_saved = true
            ORDER BY volume DESC
            LIMIT 20
        """, (today,))
        
        best_lifts = cursor.fetchall()
        
        # Format best lifts data
        lifts_data = []
        for lift in best_lifts:
            lifts_data.append({
                'user_id': lift['user_id'],
                'username': lift['username'],
                'avatar': lift['avatar'] or 'default.png',
                'level': lift['level'],
                'exercise_name': lift['exercise_name'],
                'reps': lift['reps'],
                'weight': lift['weight'],
                'volume': lift['volume']
            })
        
        cursor.close()
        conn.close()
        
        # Since user is verified as admin by decorator, is_admin is always True
        return render_template('main.html', 
                            news_posts=news_posts, 
                            best_lifts=best_lifts,
                            is_admin=True,
                            is_authenticated=True)
    
    except Exception as e:
        app.logger.error(f"Error loading main page: {e}")
        flash('Error loading main page', 'danger')
        cursor.close()
        conn.close()
        return redirect(url_for('index'))
 

if __name__ == '__main__':
    try:
        print("[INIT] Initializing main database...")
        init_db()
        print("[INIT] Main database initialized.")

        print("[INIT] Initializing workout database...")
        init_workout_db()
        print("[INIT] Workout database initialized.")

        print("[INIT] Updating food keys normalization...")
        update_food_keys_normalization()
        print("[INIT] Food keys updated.")

        # ===== NEW: Initialize Scheduler =====
        print("[INIT] Configuring automatic Garmin sync scheduler...")
        
        # Configure scheduler
        app.config['SCHEDULER_API_ENABLED'] = False  # Disable REST API for security
        app.config['SCHEDULER_TIMEZONE'] = 'UTC'     # Use UTC for consistency
        
        # Initialize scheduler with app
        scheduler.init_app(app)
        
        # Add the auto-sync job - runs every 30 minutes
        scheduler.add_job(
            id='auto_sync_garmin',
            func=auto_sync_all_garmin_users,
            trigger='interval',
            minutes=30,  # Sync every 30 minutes
            max_instances=1,  # Prevent overlapping runs
            replace_existing=True
        )
        
        # Start the scheduler
        scheduler.start()
        print("[SCHEDULER] ✅ Automatic Garmin sync enabled - running every 30 minutes")
        
        print("[START] Running Flask app...")
        app.run(debug=False)

    except Exception as e:
        print(f"[ERROR] Initialization failed: {e}")
