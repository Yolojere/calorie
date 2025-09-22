# Backend - Updated for PostgreSQL
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, abort
import json
import os
import psycopg2
from psycopg2.extras import DictCursor, RealDictCursor
from datetime import datetime, timedelta
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
from easyocr_nutrition_scanner_clean import EnhancedSimpleScanner
logging.basicConfig(level=logging.DEBUG)

# Load environment variables
load_dotenv()


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key')
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
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
    }
}

# Initialize extensions
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Sisäänkirjautuminen vaadittu!"
login_manager.login_message_category = 'info'
csrf = CSRFProtect(app)

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
    access_token_url='https://graph.facebook.com/v16.0/oauth/access_token',
    authorize_url='https://www.facebook.com/v16.0/dialog/oauth',
    api_base_url='https://graph.facebook.com/v16.0/',
    client_kwargs={'scope': 'email'}  # add 'public_profile' if needed
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

_nutrition_scanner = EnhancedSimpleScanner()
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
    conn.commit()
    cursor.close()
    conn.close()

     
def init_workout_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Ensure 'users' table exists before creating foreign key references
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            muscle_group TEXT NOT NULL,
            description TEXT,
            created_by_admin BOOLEAN DEFAULT TRUE
        )
    """)

    # Only create workout_sessions if 'users' table exists
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
    avatar_choice = RadioField("Choose Avatar", choices=[], default="default.png")
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
    
    session_history = get_session_history(user_id)
    return session_history.get(date, []), date

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
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        
    total_calories = sum(item['calories'] for item in day_data)
    total_proteins = sum(item['proteins'] for item in day_data)
    total_fats = sum(item['fats'] for item in day_data)
    total_carbs = sum(item['carbs'] for item in day_data)
    total_salt = sum(item.get('salt', 0.0) for item in day_data)
    total_saturated = sum(item.get('saturated', 0.0) for item in day_data)
    total_fiber = sum(item.get('fiber', 0.0) for item in day_data)
    
    return (
        total_calories,
        total_proteins,
        total_fats,
        total_carbs,
        total_salt,
        total_saturated,
        total_fiber
    )

def format_date(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return date_obj.strftime("%A (%d.%m.%Y)")

# Email functions
def send_reset_email(user):
    token = user.get_reset_token()
    msg = MIMEText(f'''Nollataksesi salasanasi, klikkaa alla olevaa linkkiä:
{url_for('reset_token', token=token, _external=True)}

jos et ole pyytänyt salasanan nollausta, voit jättää tämän viestin huomioimatta.
''')
    msg['Subject'] = 'Password Reset Request'
    msg['From'] = app.config['MAIL_USERNAME']
    msg['To'] = user.email
    
    try:
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
        return True
    except Exception as e:
        app.logger.error(f"Error sending email: {e}")
        return False

# Admin decorator
def admin_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return func(*args, **kwargs)
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
@app.route('/')
@login_required
def index():
    # Use current_user directly
    current_weight = current_user.weight or 0
    current_tdee = current_user.tdee or 0

    # Get session data
    eaten_items, current_date = get_current_session(current_user.id)
    totals = calculate_totals(eaten_items)
    food_usage = get_food_usage(current_user.id)
    group_breakdown = calculate_group_breakdown(eaten_items)

    # Generate dates for selector - 3 days past, today, 3 days future
    dates = []
    today = datetime.now()
    for i in range(-3, 4):
        date_str = (today + timedelta(days=i)).strftime("%Y-%m-%d")
        formatted_date = format_date_finnish(date_str)
        dates.append((date_str, formatted_date))

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
        current_weight=current_weight
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
        email = form.email.data.lower()  # normalize to lowercase

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
            login_user(user_obj, remember=form.remember.data)
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

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = UpdateProfileForm()
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)

    current_weight = None
    current_tdee = None
    current_avatar = 'default.png'
    extra_columns_exist = False
    role = getattr(current_user, 'role', 'user')

    predefined_avatars = ['default.png'] + [f'avatar{i}.png' for i in range(1, 16)]
    form.avatar_choice.choices = [(avatar, avatar.split('.')[0].capitalize()) for avatar in predefined_avatars]

    try:
        # Check for extra columns
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name IN ('full_name','main_sport','socials')
        """)
        columns = [row['column_name'] for row in cursor.fetchall()]
        extra_columns_exist = bool(columns)

        select_cols = ['username', 'email', 'weight', 'tdee', 'avatar'] + columns
        cursor.execute(f"SELECT {', '.join(select_cols)} FROM users WHERE id = %s", (current_user.id,))
        user_data = cursor.fetchone()

        if user_data:
            current_weight = user_data.get('weight')
            current_tdee = user_data.get('tdee')
            current_avatar = user_data.get('avatar') or 'default.png'

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

            for col in columns:
                if col == "socials":
                    # Parse socials JSON safely
                    socials_json = request.form.get("socials", "[]")
                    try:
                        socials_data = json.loads(socials_json)
                    except json.JSONDecodeError:
                        socials_data = []
                    update_query += ", socials = %s"
                    update_params.append(json.dumps(socials_data))  # always store as JSON string
                else:
                    update_query += f", {col} = %s"
                    update_params.append(getattr(form, col).data if hasattr(form, col) else '')

            update_query += " WHERE id = %s"
            update_params.append(current_user.id)

            cursor.execute(update_query, tuple(update_params))
            conn.commit()
            flash('Your profile has been updated!', 'success')
            return redirect(url_for('profile'))

        elif user_data:
            # Pre-fill form
            form.username.data = user_data.get('username', '')
            form.email.data = user_data.get('email', '')
            for col in columns:
                if col == "socials":
                    # Preload socials JSON into hidden input
                    form.socials.data = user_data.get('socials') or "[]"
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
        predefined_avatars=predefined_avatars
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
        flash('Salasana on päivitetty! voit kirjautua sisään uudella', 'success')
        return redirect(url_for('login'))
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
    
@app.route('/search_foods', methods=['POST'])
@login_required
def search_foods():
    query = request.form.get('query', '').strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)

    user_id = current_user.id
    is_admin = current_user.role == 'admin'

    # Visibility clause & parameters
    if is_admin:
        visibility_clause = "TRUE"
        params = [user_id]  # only for usage join
    else:
        visibility_clause = "(f.owner_id IS NULL OR f.owner_id = %s)"
        params = [user_id, user_id]  # one for JOIN, one for visibility

    if not query:
        sql = f"""
            SELECT f.*, COALESCE(u.count, 0) AS usage
            FROM foods f
            LEFT JOIN food_usage u ON f.key = u.food_key AND u.user_id = %s
            WHERE {visibility_clause}
            ORDER BY usage DESC, name ASC
            LIMIT 15
        """
        cursor.execute(sql, params)
    else:
        sql = f"""
            SELECT f.*, COALESCE(u.count, 0) AS usage
            FROM foods f
            LEFT JOIN food_usage u ON f.key = u.food_key AND u.user_id = %s
            WHERE {visibility_clause}
              AND (LOWER(f.name) LIKE %s OR LOWER(f.name) LIKE %s OR f.ean = %s)
            ORDER BY 
                CASE 
                    WHEN LOWER(f.name) LIKE %s THEN 0
                    WHEN LOWER(f.name) LIKE %s THEN 1
                    ELSE 2
                END,
                usage DESC,
                name ASC
            LIMIT 15
        """
        cursor.execute(sql, params + [
            f"{query}%",   # starts with
            f"%{query}%",  # contains
            query,         # EAN exact
            f"{query}%",   # order by startswith
            f"%{query}%",  # order by contains
        ])

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
            "groups": ["breakfast", "lunch", "dinner", "snack"],  # still included
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
    date = request.form.get('date', datetime.now().strftime("%Y-%m-%d"))
    
    # Fetch current TDEE from user profile
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT tdee FROM users WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    current_tdee = user_data[0] if user_data and user_data[0] else 0
    cursor.close()
    conn.close()
    
    eaten_items, current_date = get_current_session(user_id, date)
    totals = calculate_totals(eaten_items)
    group_breakdown = calculate_group_breakdown(eaten_items)
    current_date_formatted = format_date(current_date)
    
    # Calculate calorie difference and status
    calorie_difference = current_tdee - totals['calories']  # Fixed: TDEE - calories consumed
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
        'calorie_status_class': calorie_status_class
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

                    "salt": 0,
                    "saturated": 0,
                    "fiber": 0,
                    "count": 0
                }

            calories, proteins, fats, carbs, salt, saturated, fiber = get_daily_totals(items)
            weekly_data[week_key]["days"].append(date_str)
            weekly_data[week_key]["calories"] += calories
            weekly_data[week_key]["proteins"] += proteins
            weekly_data[week_key]["fats"] += fats
            weekly_data[week_key]["carbs"] += carbs
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
        calories, proteins, fats, carbs, salt, saturated, fiber = get_daily_totals(day_data)
        history_data.append({
            'date': format_date(date),
            'date_raw': date,
            'calories': calories,
            'proteins': proteins,
            'fats': fats,
            'carbs': carbs,
            'salt': salt,
            'saturated': saturated,
            'fiber': fiber
        })

    # Today's totals
    today_data = session_history.get(today_str, [])
    today_calories, today_proteins, today_fats, today_carbs, today_salt, today_saturated, today_fiber = get_daily_totals(today_data)

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
    cursor = conn.cursor()

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

                # Fetch sets for this session
                cursor.execute("""
                    SELECT wset.id, wset.exercise_id, wset.reps, wset.weight, ex.name, ex.muscle_group
                    FROM workout_sets wset
                    JOIN exercises ex ON ex.id = wset.exercise_id
                    WHERE wset.session_id = %s
                """, (session_id,))
                sets = cursor.fetchall()

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
        # Fetch the session WITHOUT muscle_group
        cursor.execute(
            "SELECT id, notes, is_saved, workout_type, name, focus_type FROM workout_sessions "
            "WHERE user_id = %s AND date = %s",
            (user_id, date)
        )
        session_data = cursor.fetchone()
        
        if not session_data:
            conn.close()
            return jsonify({
                'success': True,
                'session': None,
                'exercises': []
            })
        
        session = {
            "id": session_data['id'],
            "notes": session_data['notes'],
            "is_saved": session_data['is_saved'],
            "workout_type": session_data['workout_type'],
            "name": session_data['name'],
            "focus_type": session_data['focus_type']
        }

        session_id = session['id']
        
        # Get sets for this session and group by exercise
        cursor.execute(
            "SELECT s.id, e.id AS exercise_id, e.name AS exercise_name, "
            "e.muscle_group, s.reps, s.weight, s.volume, s.rir, s.comments "
            "FROM workout_sets s "
            "JOIN exercises e ON s.exercise_id = e.id "
            "WHERE session_id = %s "
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
                'comments': row['comments']
            })
        
        conn.close()
    
        return jsonify({
            'success': True,
            'session': dict(session),
            'exercises': list(exercises.values())
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
    
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
        # Get or create session
        cursor.execute(
            "SELECT id FROM workout_sessions "
            "WHERE user_id = %s AND date = %s",
            (user_id, date)
        )
        session = cursor.fetchone()
        
        if not session:
            cursor.execute(
                "INSERT INTO workout_sessions (user_id, date, muscle_group) "
                "VALUES (%s, %s, %s) RETURNING id",
                (user_id, date, muscle_group)
            )
            session_id = cursor.fetchone()[0]
        else:
            session_id = session[0]
        
        # Insert multiple sets
        for i in range(sets_count):
            cursor.execute(
                "INSERT INTO workout_sets (session_id, exercise_id, reps, weight, rir, comments) "
                "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (session_id, exercise_id, reps, weight, rir, comments)
            )
            set_ids.append(cursor.fetchone()[0])
        
        conn.commit()
        return jsonify(success=True, set_ids=set_ids)
    
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

@app.route('/workout/history', methods=['GET'])
@login_required
def workout_history():
    user_id = current_user.id
    period = request.args.get('period', 'daily')  # daily, weekly, monthly

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)

    try:
        if period == 'daily':
            # Get daily totals
            cursor.execute('''
                SELECT 
                    s.date,
                    COUNT(ws.id) AS total_sets,
                    SUM(ws.reps) AS total_reps,
                    SUM(ws.volume) AS total_volume
                FROM workout_sessions s
                LEFT JOIN workout_sets ws ON s.id = ws.session_id
                LEFT JOIN exercises e ON ws.exercise_id = e.id
                WHERE s.user_id = %s
                GROUP BY s.date
                ORDER BY s.date DESC
                LIMIT 30;
            ''', (user_id,))
            rows = cursor.fetchall()

            history = []
            for row in rows:
                date = row['date']

                # Get muscles per day
                cursor.execute('''
                    SELECT e.muscle_group,
                           COUNT(ws.id) AS sets,
                           SUM(ws.reps) AS reps,
                           SUM(ws.volume) AS volume
                    FROM workout_sessions s
                    LEFT JOIN workout_sets ws ON s.id = ws.session_id
                    LEFT JOIN exercises e ON ws.exercise_id = e.id
                    WHERE s.user_id = %s AND s.date = %s
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

                history.append({
                    'date': date,
                    'sessions_count': len(set([date])),  # adjust if multiple sessions per day
                    'total_sets': row['total_sets'] or 0,
                    'total_reps': row['total_reps'] or 0,
                    'total_volume': float(row['total_volume'] or 0),
                    'muscles': muscles
                })

        else:
            date_trunc = 'week' if period == 'weekly' else 'month'
            period_limit = 12 if period == 'weekly' else 6

            cursor.execute(f'''
                SELECT 
                    DATE_TRUNC('{date_trunc}', s.date)::DATE AS period_start,
                    s.id AS session_id,
                    e.muscle_group,
                    ws.reps,
                    ws.volume
                FROM workout_sessions s
                LEFT JOIN workout_sets ws ON s.id = ws.session_id
                LEFT JOIN exercises e ON ws.exercise_id = e.id
                WHERE s.user_id = %s
                ORDER BY period_start DESC
            ''', (user_id,))
            rows = cursor.fetchall()

            period_map = {}
            for row in rows:
                period_start = row['period_start']
                if period_start not in period_map:
                    period_map[period_start] = {
                        'sessions': set(),
                        'muscles': {},
                        'total_sets': 0,
                        'total_reps': 0,
                        'total_volume': 0.0
                    }

                # Track sessions
                if row['session_id']:
                    period_map[period_start]['sessions'].add(row['session_id'])

                # Track muscles
                if row['muscle_group']:
                    muscle = row['muscle_group']
                    if muscle not in period_map[period_start]['muscles']:
                        period_map[period_start]['muscles'][muscle] = {
                            'sets': 0,
                            'reps': 0,
                            'volume': 0.0
                        }

                    if row['reps'] is not None:
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
                entry = {
                    'sessions_count': len(data['sessions']),
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
        date = request.form.get('date')
        user_id = current_user.id
        
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
        
        # Get or create session
        cursor.execute(
            "SELECT id FROM workout_sessions "
            "WHERE user_id = %s AND date = %s",
            (user_id, date)
        )
        session = cursor.fetchone()
        
        if not session:
            cursor.execute(
                "INSERT INTO workout_sessions (user_id, date) "
                "VALUES (%s, %s) RETURNING id",
                (user_id, date)
            )
            session_id = cursor.fetchone()[0]
        else:
            session_id = session[0]
        
        # Add sets to session
        for ex in exercises:
            cursor.execute(
                "INSERT INTO workout_sets "
                "(session_id, exercise_id, reps, weight, rir, comments) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (session_id, ex[0], ex[1], ex[2], ex[3], ex[4])
            )
        
        conn.commit()
        return jsonify(success=True)
    except Exception as e:
        if conn:
            conn.rollback()
        app.logger.error(f"Error applying template: {str(e)}")
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
    # Add debug logging
    print(f"Copying workout from {source_date} to {target_date} for user {user_id}")
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)

    try:
        # Fetch source session
        cursor.execute(
            "SELECT * FROM workout_sessions WHERE user_id = %s AND date = %s",
            (user_id, source_date)
        )
        source_session = cursor.fetchone()
        if not source_session:
            return jsonify({"success": False, "error": "Source session not found"})

        # Use source muscle_group (or fallback)
        muscle_group = source_session["muscle_group"] or "All"

        # Insert new session for target date
        cursor.execute(
            "INSERT INTO workout_sessions (user_id, date, name, focus_type, muscle_group) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (user_id, target_date, source_session["name"], source_session["focus_type"], muscle_group)
        )
        new_session_id = cursor.fetchone()["id"]

        # Copy sets
        cursor.execute(
            "SELECT * FROM workout_sets WHERE session_id = %s",
            (source_session["id"],)
        )
        sets = cursor.fetchall()
        for s in sets:
            cursor.execute(
                "INSERT INTO workout_sets (session_id, exercise_id, reps, weight, rir, comments) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (new_session_id, s["exercise_id"], s["reps"], s["weight"], s["rir"], s["comments"])
            )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"success": True})

    except Exception as e:
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
    try:
        tdee = float(request.form.get('tdee', 0))
        weight = float(request.form.get('weight', 0))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET tdee = %s, weight = %s WHERE id = %s",
            (tdee, weight, current_user.id)
        )
        conn.commit()
        return jsonify(success=True, message="Metrics saved successfully!")
    except Exception as e:
        print(f"Error saving metrics: {e}")
        return jsonify(success=False, error=str(e)), 500
    finally:
        if conn:
            conn.close()
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

@app.route("/workout/save", methods=["POST"])
@login_required
def save_workout():
    data = request.get_json()
    focus_type = data.get("focus_type")
    date = data.get("date")
    exercises = data.get("exercises", [])
    name = data.get("name", "Unnamed Workout")

    if not focus_type or not date:
        return jsonify({"success": False, "error": "Focus vaihtoehto on valittava"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Save the workout session
        cursor.execute(
            "INSERT INTO workout_sessions (user_id, date, name, focus_type) VALUES (%s, %s, %s, %s) RETURNING id",
            (current_user.id, date, name, focus_type)
        )
        session_id = cursor.fetchone()[0]

        # Save sets for each exercise
        for ex in exercises:
            for s in ex["sets"]:
                cursor.execute(
                    "INSERT INTO workout_sets (session_id, exercise_id, reps, weight) VALUES (%s, %s, %s, %s)",
                    (session_id, ex["id"], s["reps"], s["weight"])
                )

        # Initialize tracking structures
        set_comparisons = []
        personal_records = []
        improvements = []
        total_sets = 0
        current_total_volume = 0

        for ex in exercises:
            # Previous session for same focus_type
            cursor.execute("""
                SELECT wset.reps, wset.weight, ws.date
                FROM workout_sessions ws
                JOIN workout_sets wset ON wset.session_id = ws.id
                WHERE ws.user_id = %s
                  AND ws.focus_type = %s
                  AND wset.exercise_id = %s
                  AND ws.id != %s
                ORDER BY ws.date DESC
                LIMIT 1
            """, (current_user.id, focus_type, ex["id"], session_id))
            last = cursor.fetchone()

            current_sets = ex["sets"]
            total_sets += len(current_sets)

            # Current session calculations
            heaviest_set = max(current_sets, key=lambda s: s["weight"])
            best_set = max(current_sets, key=lambda s: s["reps"] * s["weight"])
            total_volume_ex = sum(s["reps"] * s["weight"] for s in current_sets)
            current_total_volume += total_volume_ex

            if last:
                last_reps, last_weight, last_date = last
                last_volume = last_reps * last_weight

                # PR detection
                if best_set["reps"] * best_set["weight"] > last_volume:
                    personal_records.append({
                        "exercise": ex["name"],
                        "type": "bestSet",
                        "weight": best_set["weight"],
                        "reps": best_set["reps"],
                        "previousBest": {"weight": last_weight, "reps": last_reps}
                    })
                if heaviest_set["weight"] > last_weight:
                    personal_records.append({
                        "exercise": ex["name"],
                        "type": "heaviestWeight",
                        "weight": heaviest_set["weight"],
                        "reps": None,
                        "previousBest": {"weight": last_weight, "reps": last_reps}
                    })

                # Per-set comparisons
                for idx, s in enumerate(current_sets, start=1):
                    current_volume = s["reps"] * s["weight"]
                    volume_change = current_volume - last_volume
                    set_comparisons.append({
                        "setId": f"{ex['id']}-{idx}",
                        "exerciseId": ex["id"],
                        "currentReps": s["reps"],
                        "currentWeight": s["weight"],
                        "currentVolume": current_volume,
                        "previousReps": last_reps,
                        "previousWeight": last_weight,
                        "previousVolume": last_volume,
                        "volumeChange": volume_change,
                        "noPrevious": False,
                        "isNew": False
                    })

                # Track improvements per exercise
                if total_volume_ex > last_volume:
                    improvements.append({"exercise": ex["name"], "volumeChange": total_volume_ex - last_volume})

            else:
                # First session of this focus type
                for idx, s in enumerate(current_sets, start=1):
                    current_volume = s["reps"] * s["weight"]
                    set_comparisons.append({
                        "setId": f"{ex['id']}-{idx}",
                        "exerciseId": ex["id"],
                        "currentReps": s["reps"],
                        "currentWeight": s["weight"],
                        "currentVolume": current_volume,
                        "previousReps": 0,
                        "previousWeight": 0,
                        "previousVolume": 0,
                        "volumeChange": current_volume,
                        "noPrevious": True,
                        "isNew": True
                    })

                # First session PRs (best set & heaviest)
                personal_records.append({
                    "exercise": ex["name"],
                    "type": "bestSet",
                    "weight": best_set["weight"],
                    "reps": best_set["reps"],
                    "previousBest": {"weight": 0, "reps": 0}
                })
                personal_records.append({
                    "exercise": ex["name"],
                    "type": "heaviestWeight",
                    "weight": heaviest_set["weight"],
                    "reps": None,
                    "previousBest": {"weight": 0, "reps": 0}
                })

        # Previous session totals for volume & sets
        cursor.execute("""
            SELECT ws.id
            FROM workout_sessions ws
            WHERE ws.user_id = %s
              AND ws.focus_type = %s
              AND ws.id != %s
            ORDER BY ws.date DESC
            LIMIT 1
        """, (current_user.id, focus_type, session_id))
        last_session = cursor.fetchone()

        last_total_volume = 0
        last_total_sets = 0
        if last_session:
            last_session_id = last_session[0]
            cursor.execute("SELECT SUM(reps * weight) FROM workout_sets WHERE session_id = %s", (last_session_id,))
            last_total_volume = cursor.fetchone()[0] or 0
            cursor.execute("SELECT COUNT(*) FROM workout_sets WHERE session_id = %s", (last_session_id,))
            last_total_sets = cursor.fetchone()[0] or 0

        volume_change_percent = ((current_total_volume - last_total_volume) / last_total_volume * 100) if last_total_volume else 0
        sets_change = total_sets - last_total_sets

        conn.commit()

        return jsonify({
            "success": True,
            "comparisonData": {
                "setComparisons": set_comparisons,
                "totalSets": total_sets,
                "setsChange": sets_change,
                "totalVolume": current_total_volume,
                "volumeChange": volume_change_percent
            },
            "achievements": {
                "personalRecords": personal_records,
                "improvements": improvements
            }
        })

    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
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
            provider_user_id = userinfo['id']
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
            flash(f'{provider.capitalize()} Kyttäjätili yhdisttety onnistuneesti!', 'success')
            return redirect(url_for('index'))
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
        # Get image data
        image_data = None
        if 'file' in request.files and request.files['file'].filename != '':
            image_data = request.files['file'].read()
        elif 'image' in request.form:
            base64_data = request.form['image']
            if base64_data.startswith('data:'):
                base64_data = base64_data.split(',')[1]  # fix: take base64 after comma
            image_data = base64.b64decode(base64_data)

        if not image_data:
            return jsonify({'success': False, 'error': 'No image provided'}), 400

        # Lazy-load scanner
        scanner = get_scanner()

        # Scan with EasyOCR
        result = scanner.scan_nutrition_label(image_data)

        if result['success']:
            # Format for your form
            form_data = {}
            for field in ['calories', 'fats', 'saturated', 'carbs', 'fiber', 'proteins', 'salt', 'sugars']:
                if field in result['nutrition_data']:
                    form_data[field] = round(result['nutrition_data'][field], 1)

            return jsonify({
                'success': True,
                'form_data': form_data,
                'per_100g': result.get('per_100g', True),
                'message': f'EasyOCR found {len(form_data)} nutrition values'
            })
        else:
            return jsonify(result), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
if __name__ == '__main__':
    try:
        print("[INIT] Initializing main database...")
        init_db()  # must run first: creates users, foods, etc.
        print("[INIT] Main database initialized.")

        print("[INIT] Initializing workout database...")
        init_workout_db()  # now safe: users table exists
        print("[INIT] Workout database initialized.")

        print("[INIT] Updating food keys normalization...")
        update_food_keys_normalization()
        print("[INIT] Food keys updated.")



        print("[START] Running Flask app...")
        app.run(debug=True)

    except Exception as e:
        print(f"[ERROR] Initialization failed: {e}")
