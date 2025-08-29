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

# Initialize extensions
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
csrf = CSRFProtect(app)
# Update the normalize_key function
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
            half REAL,
            entire REAL,
            serving REAL,
            ean TEXT UNIQUE
        )
    ''')

    # 3. Food usage
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_usage (
            food_key TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0,
            FOREIGN KEY (food_key) REFERENCES foods(key) ON DELETE CASCADE
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
            (key, name, carbs, sugars, fiber, proteins, fats, saturated, salt, calories, grams, half, entire, serving, ean)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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

    

# Migrate JSON data to database
def migrate_json_to_db():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    FOOD_FILE = os.path.join(BASE_DIR, 'data', 'foods.json')
    USAGE_FILE = os.path.join(BASE_DIR, 'data', 'food_usage.json')
    
    # Migrate foods
    foods = {}
    if os.path.exists(FOOD_FILE) and os.path.getsize(FOOD_FILE) > 0:
        try:
            with open(FOOD_FILE, 'r') as f:
                foods = json.load(f)
        except json.JSONDecodeError:
            print(f"Invalid JSON in {FOOD_FILE}, skipping migration")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for key, food in foods.items():
        normalized_key = normalize_key(key)
        # Handle EAN field - convert list to string if needed
        ean = food.get('ean')
        if isinstance(ean, list):
            ean = ', '.join(ean) if ean else None
        
        try:
            cursor.execute('''
                INSERT INTO foods 
                (key, name, carbs, sugars, fiber, proteins, fats, saturated, salt, calories, grams, half, entire, serving, ean)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    ean = EXCLUDED.ean
            ''', (
                key,
                food['name'],
                safe_float(food['carbs']),  # Use safe_float
                safe_float(food.get('sugars')),  # Use safe_float
                safe_float(food.get('fiber')),  # Use safe_float
                safe_float(food['proteins']),  # Use safe_float
                safe_float(food['fats']),  # Use safe_float
                safe_float(food.get('saturated')),  # Use safe_float
                safe_float(food.get('salt')),  # Use safe_float
                safe_float(food['calories']),  # Use safe_float
                safe_float(food['grams'], 100),  # Use safe_float with default 100
                safe_float(food.get('half'), None),  # Allow None for optional fields
                safe_float(food.get('entire'), None),  # Allow None for optional fields
                safe_float(food.get('serving'), None),  # Allow None for optional fields
                ean
            ))
        except Exception as e:
            print(f"Error inserting food {key}: {e}")
    
    conn.commit()
    
    # Backup if we successfully processed the file
    if os.path.exists(FOOD_FILE) and os.path.getsize(FOOD_FILE) > 0:
        os.rename(FOOD_FILE, FOOD_FILE + ".bak")
    
    # Migrate food_usage
    usage = {}
    if os.path.exists(USAGE_FILE) and os.path.getsize(USAGE_FILE) > 0:
        try:
            with open(USAGE_FILE, 'r') as f:
                usage = json.load(f)
        except json.JSONDecodeError:
            print(f"Invalid JSON in {USAGE_FILE}, skipping migration")
    
    for key, count in usage.items():
        try:
            cursor.execute('''
                INSERT INTO food_usage (food_key, count)
                VALUES (%s, %s)
                ON CONFLICT (food_key) DO UPDATE SET count = food_usage.count + %s
            ''', (key, count, count))
        except Exception as e:
            print(f"Error inserting usage for {key}: {e}")
            
        
    conn.commit()
    conn.close()
    
    # Backup if we successfully processed the file
    if os.path.exists(USAGE_FILE) and os.path.getsize(USAGE_FILE) > 0:
        os.rename(USAGE_FILE, USAGE_FILE + ".bak")

# Forms (unchanged)
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', 
                                    validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s', (username.data,))
        user = cursor.fetchone()
        conn.close()
        if user:
            raise ValidationError('Username already taken. Please choose a different one.')

    def validate_email(self, email):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = %s', (email.data,))
        user = cursor.fetchone()
        conn.close()
        if user:
            raise ValidationError('Email already registered. Please use a different email.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class UpdateProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    full_name = StringField('Full Name')
    avatar_choice = RadioField(
        "Choose Avatar",
        choices=[("avatar1.png", "Avatar 1"), ("avatar2.png", "Avatar 2"), ("avatar3.png", "Avatar 3")],
        default="avatar1.png")
    avatar_upload = FileField("Or Upload Avatar")
    submit = SubmitField('Update')

    def validate_username(self, username):
        if username.data != current_user.username:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = %s', (username.data,))
            user = cursor.fetchone()
            conn.close()
            if user:
                raise ValidationError('Username already taken. Please choose a different one.')

    def validate_email(self, email):
        if email.data != current_user.email:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE email = %s', (email.data,))
            user = cursor.fetchone()
            conn.close()
            if user:
                raise ValidationError('Email already registered. Please use a different email.')

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
        return User(id=user['id'], username=user['username'], email=user['email'], role=user['role'])
    return None

# Helper functions
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
            (key, name, carbs, sugars, fiber, proteins, fats, saturated, salt, calories, grams, half, entire, serving, ean)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            food_data.get('ean')
        ))
        conn.commit()
    finally:
        conn.close()

def get_food_usage():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute('SELECT food_key, count FROM food_usage')
    usage = cursor.fetchall()
    conn.close()
    return {row['food_key']: row['count'] for row in usage}

def increment_food_usage(food_key):
    normalized_key = normalize_key(food_key)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO food_usage (food_key, count)
            VALUES (%s, 1)
            ON CONFLICT (food_key) DO UPDATE SET count = food_usage.count + 1
        ''', (normalized_key,))
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
        return 0.0, 0.0, 0.0, 0.0, 0.0
        
    total_calories = sum(item['calories'] for item in day_data)
    total_proteins = sum(item['proteins'] for item in day_data)
    total_fats = sum(item['fats'] for item in day_data)
    total_carbs = sum(item['carbs'] for item in day_data)
    total_salt = sum(item.get('salt', 0.0) for item in day_data)
    return total_calories, total_proteins, total_fats, total_carbs, total_salt

def format_date(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return date_obj.strftime("%A (%d.%m.%Y)")

# Email functions
def send_reset_email(user):
    token = user.get_reset_token()
    msg = MIMEText(f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request, please ignore this email.
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
migrate_json_to_db()
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
    user_id = current_user.id

    # Fetch latest weight & TDEE from DB
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT weight, tdee FROM users WHERE id = %s", (user_id,))
    user_metrics = cursor.fetchone()
    cursor.close()
    conn.close()

    current_weight = user_metrics[0] if user_metrics and user_metrics[0] else 0
    current_tdee = user_metrics[1] if user_metrics and user_metrics[1] else 0

    # Get session data
    eaten_items, current_date = get_current_session(user_id)
    totals = calculate_totals(eaten_items)
    food_usage = get_food_usage()
    group_breakdown = calculate_group_breakdown(eaten_items)
    
    # Generate dates for selector - 3 days past, today, 3 days future
    dates = []
    today = datetime.now()
    for i in range(-3, 4):
        date_str = (today + timedelta(days=i)).strftime("%Y-%m-%d")
        formatted_date = format_date(date_str)
        dates.append((date_str, formatted_date))

    current_date_formatted = format_date(current_date)
    for group, group_data in group_breakdown.items():
        for item in group_data['items']:
            # Ensure each item has a key property (as a dictionary key, not attribute)
            if 'key' not in item:
                item['key'] = item['id']  # Use dictionary access, not attribute access
    return render_template(
        'index.html',
        eaten_items=eaten_items,
        totals=totals,
        current_date=current_date,
        current_date_formatted=current_date_formatted,
        dates=dates,
        food_usage=food_usage,
        group_breakdown=group_breakdown,
        current_tdee=current_tdee,        # latest TDEE
        current_weight=current_weight     # latest weight
    )


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
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO users (username, email, password) VALUES (%s, %s, %s)',
                (form.username.data, form.email.data, hashed_password)
            )
            conn.commit()
            flash('Your account has been created! You can now log in', 'success')
            return redirect(url_for('login'))
        except psycopg2.IntegrityError as e:
            flash('Username or email already exists', 'danger')
            app.logger.error(f"Registration error: {e}")
        finally:
            conn.close()
    
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s', (form.email.data,))
        user = cursor.fetchone()
        conn.close()
        if user and bcrypt.check_password_hash(user['password'], form.password.data):
            user_obj = User(id=user['id'], username=user['username'], email=user['email'], role=user['role'])
            login_user(user_obj, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
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

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = UpdateProfileForm()
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    
    # Initialize variables with default values
    current_weight = None
    current_tdee = None
    current_avatar = 'default.png'

    # Define predefined avatars for the form choices
    predefined_avatars = ['default.png', 'avatar1.png', 'avatar2.png', 'avatar3.png', 'avatar4.png','avatar5.png','avatar6.png','avatar7.png']
    form.avatar_choice.choices = [(avatar, avatar.split('.')[0].capitalize()) for avatar in predefined_avatars]

    try:
        # Check if the new columns exist in the database
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name IN ('full_name')
        """)
        extra_columns_exist = bool(cursor.fetchall())
        
        # Build the SELECT query based on available columns
        select_query = 'SELECT username, email, weight, tdee, avatar'
        if extra_columns_exist:
            select_query += ', full_name, main_sport, fitness_goals'
        select_query += ' FROM users WHERE id = %s'
        
        # Get current user info
        cursor.execute(select_query, (current_user.id,))
        user_data = cursor.fetchone()
        
        if user_data:
            current_weight = user_data['weight']
            current_tdee = user_data['tdee']
            current_avatar = user_data['avatar'] if user_data['avatar'] else 'default.png'

        if form.validate_on_submit():
            avatar_filename = current_avatar  # default to current

            # Handle avatar upload
            if form.avatar_upload.data:
                file = form.avatar_upload.data
                if file and allowed_file(file.filename):
                    # Generate unique filename to avoid conflicts
                    timestamp = str(int(time.time()))
                    filename = secure_filename(file.filename)
                    name, ext = os.path.splitext(filename)
                    unique_filename = f"{name}_{timestamp}{ext}"
                    filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
                    
                    # Create uploads directory if it doesn't exist
                    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                    
                    file.save(filepath)

                    # Resize to 200x200
                    img = Image.open(filepath)
                    img.thumbnail((200, 200))
                    img.save(filepath)

                    avatar_filename = unique_filename
                else:
                    flash('Invalid file type. Please upload PNG, JPG, JPEG, or GIF.', 'danger')

            # Handle avatar choice (predefined avatars)
            elif form.avatar_choice.data:
                avatar_filename = form.avatar_choice.data

            # Build the UPDATE query based on available columns
            update_query = '''UPDATE users SET username = %s, email = %s, avatar = %s'''
            update_params = [form.username.data, form.email.data, avatar_filename]
            
            # Add extra fields if they exist
            if extra_columns_exist:
                update_query += ', full_name = %s, main_sport = %s, fitness_goals = %s'
                update_params.extend([
                    request.form.get('full_name', ''),
                    request.form.get('main_sport', ''),
                    request.form.get('fitness_goals', '')
                ])
            
            update_query += ' WHERE id = %s'
            update_params.append(current_user.id)
            
            # Update user information
            cursor.execute(update_query, tuple(update_params))
            conn.commit()
            flash('Your profile has been updated!', 'success')
            return redirect(url_for('profile'))

        # GET request: pre-fill form
        elif request.method == 'GET' and user_data:
            form.username.data = user_data['username']
            form.email.data = user_data['email']
            
            # Pre-fill extra fields if they exist
            if extra_columns_exist:
                form.full_name.data = user_data.get('full_name', '')
                form.main_sport.data = user_data.get('main_sport', '')
                form.fitness_goals.data = user_data.get('fitness_goals', '')
            
            # Set avatar choice - use default.png if none is set
            if user_data['avatar'] and user_data['avatar'] in predefined_avatars:
                form.avatar_choice.data = user_data['avatar']
            else:
                form.avatar_choice.data = 'default.png'

    except psycopg2.IntegrityError:
        flash('Username or email already taken', 'danger')
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'danger')
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
        role=current_user.role,
        extra_columns_exist=extra_columns_exist  # Pass this to template
    )


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RequestResetForm()
    if form.validate_on_submit():
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s', (form.email.data,))
        user = cursor.fetchone()
        conn.close()
        if user:
            user_obj = User(id=user['id'], username=user['username'], email=user['email'], role=user['role'])
            if send_reset_email(user_obj):
                flash('An email has been sent with instructions to reset your password.', 'info')
            else:
                flash('Could not send email. Please try again later.', 'danger')
        else:
            flash('No account found with that email.', 'warning')
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
    
    user_obj = User(id=user['id'], username=user['username'], email=user['email'], role=user['role'])
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
        flash('Your password has been updated! You can now log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)

@app.route('/search_foods', methods=['POST'])
@login_required
def search_foods():
    query = request.form.get('query', '').strip()
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    
    if not query:
        cursor.execute('''
            SELECT f.*, COALESCE(u.count, 0) as usage
            FROM foods f
            LEFT JOIN food_usage u ON f.key = u.food_key
            ORDER BY usage DESC, name ASC
            LIMIT 15
        ''')
    else:
        cursor.execute('''
            SELECT f.*, COALESCE(u.count, 0) as usage
            FROM foods f
            LEFT JOIN food_usage u ON f.key = u.food_key
            WHERE LOWER(f.name) LIKE %s OR f.ean = %s
            ORDER BY usage DESC, name ASC
            LIMIT 15
        ''', (f'%{query.lower()}%', query))
    
    foods = cursor.fetchall()
    conn.close()
    
    results = []
    for food in foods:
        results.append({
            'id': food['key'],
            'name': food['name'],
            'calories': food['calories'],
            'serving_size': food['serving'],
            'half_size': food['half'],
            'entire_size': food['entire'],
            'usage': food['usage'],
            'ean': food['ean']
        })
    
    return jsonify(results)

@app.route('/get_food_details', methods=['POST'])
@login_required
def get_food_details():
    try:
        food_id = request.form.get('food_id')
        unit_type = request.form.get('unit_type')
        units = request.form.get('units')
        
        # Use the standard normalize_key function
        normalized_key = normalize_key(food_id)
        
        print(f"\n=== /get_food_details REQUEST ===")
        print(f"Raw food_id: '{food_id}'")
        print(f"Normalized key: '{normalized_key}'")
        
        food = get_food_by_key(normalized_key)
        if not food:
            # Get all keys only when needed
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT key FROM foods')
            all_keys = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            print(f"❌ Food not found: '{normalized_key}'")
            return jsonify({
                'error': 'Food not found',
                'requested_key': food_id,
                'normalized_key': normalized_key,
                'all_keys_in_db': all_keys  # Fixed variable name
            }), 404 
        
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
        "entire_size": food.get("entire")
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
        else:
            grams = units
            unit_type = 'grams'
        
        factor = grams / 100
        carbs = food['carbs'] * factor
        proteins = food['proteins'] * factor
        fats = food['fats'] * factor
        salt = safe_float(food.get('salt')) * factor  # Use safe_float
        sugars = safe_float(food.get('sugars')) * factor  # Use safe_float
        fiber = safe_float(food.get('fiber')) * factor  # Use safe_float
        saturated = safe_float(food.get('saturated')) * factor  # Use safe_float
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
        increment_food_usage(food['key'])

        # Return updated session, totals and breakdown
        totals = calculate_totals(eaten_items)
        group_breakdown = calculate_group_breakdown(eaten_items)
        return jsonify({
            'session': eaten_items,
            'totals': totals,
            'breakdown': group_breakdown,
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
    return move_or_copy_items(remove_original=True)

@app.route('/copy_items', methods=['POST'])
@login_required
def copy_items():
    return move_or_copy_items(remove_original=False)

def move_or_copy_items(remove_original=True):
    try:
        user_id = current_user.id
        date = request.form.get('date', datetime.now().strftime("%Y-%m-%d"))
        
        new_group = request.form.get('new_group')
        target_date = request.form.get('target_date', date)
        item_ids = json.loads(request.form.get('item_ids', '[]'))
        
        # Get source session
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute(
            'SELECT data FROM user_sessions WHERE user_id = %s AND date = %s',
            (user_id, date)
        )
        session_data = cursor.fetchone()
        eaten_items = json.loads(session_data['data']) if session_data else []
        
        # Prepare items to transfer by matching IDs
        items_to_transfer = []
        for item in eaten_items:
            if item['id'] in item_ids:
                # Create a copy and update the group
                new_item = item.copy()
                new_item['group'] = new_group
                if not remove_original:  # Only for copies, not moves
                    new_item['id'] = str(uuid.uuid4())
                items_to_transfer.append(new_item)
        
        # If moving, remove original items by ID
        if remove_original:
            # Create a new list without the moved items
            eaten_items = [item for item in eaten_items if item['id'] not in item_ids]
        
        # Save source session
        save_current_session(user_id, eaten_items, date)
        
        # Get target session
        cursor.execute(
            'SELECT data FROM user_sessions WHERE user_id = %s AND date = %s',
            (user_id, target_date)
        )
        target_data = cursor.fetchone()
        target_items = json.loads(target_data['data']) if target_data else []
        
        # Add items to target session
        target_items.extend(items_to_transfer)
        save_current_session(user_id, target_items, target_date)
        
        # Return updated session
        totals = calculate_totals(eaten_items)
        group_breakdown = calculate_group_breakdown(eaten_items)
        current_date_formatted = format_date(date)
        
        return jsonify({
            'session': eaten_items,
            'totals': totals,
            'current_date': date,
            'current_date_formatted': current_date_formatted,
            'breakdown': group_breakdown
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500



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
        
        # Use the name to lookup food details
        food_key = item_found['key']  # Get the stored key
        food = get_food_by_key(food_key)  # Use key instead of name
        
        if not food:
            print(f"Food not found in database for key: '{food_key}'")
            return jsonify({'error': 'Food not found'}), 404
        
        # Convert units to grams
        factor = float(new_grams) / 100
        item_found['grams'] = float(new_grams)
        item_found['units'] = float(new_grams)
        item_found['unit_type'] = 'grams'
        item_found['carbs'] = food['carbs'] * factor
        item_found['proteins'] = food['proteins'] * factor
        item_found['fats'] = food['fats'] * factor
        item_found['salt'] = food.get('salt', 0.0) * factor
        item_found['calories'] = food['calories'] * factor
        
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
    except Exception as e:
        print(f"Error in update_grams: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/save_food', methods=['POST'])
@login_required
def save_food_route():
    conn = None
    try:
        # Extract form data
        name = request.form.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400
        
        # Get EAN and check if it's provided
        ean = request.form.get('ean') or None
        
        # Open connection early for EAN check
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check for duplicate EAN if provided
        if ean:
            cursor.execute('SELECT key FROM foods WHERE ean = %s', (ean,))
            existing_food = cursor.fetchone()
            if existing_food:
                return jsonify({
                    'success': False, 
                    'error': f'EAN {ean} already in use by food: {existing_food[0]}'
                }), 400

        # Rest of form data extraction
        carbs = safe_float(request.form.get('carbs', 0))
        sugars = safe_float(request.form.get('sugars', 0))
        fiber = safe_float(request.form.get('fiber', 0))
        proteins = safe_float(request.form.get('proteins', 0))
        fats = safe_float(request.form.get('fats', 0))
        saturated = safe_float(request.form.get('saturated', 0))
        salt = safe_float(request.form.get('salt', 0))
        
        # Handle optional portion fields
        serving_val = request.form.get('serving')
        half_val = request.form.get('half')
        entire_val = request.form.get('entire')
        
        serving = safe_float(serving_val, None) if serving_val else None
        half = safe_float(half_val, None) if half_val else None
        entire = safe_float(entire_val, None) if entire_val else None
        
        # Base grams handling
        grams_val = request.form.get('grams', '100')
        grams = safe_float(grams_val, 100, min_val=0.001)
        
        # Handle calories - use if provided, otherwise calculate
        calories_input = request.form.get('calories', '').strip()
        if calories_input:
            try:
                calories = float(calories_input)
                # Validate that the provided calories make sense
                calculated_calories = calculate_calories(carbs, proteins, fats)
                # If provided calories are significantly different from calculated, use calculated
                if abs(calories - calculated_calories) > calculated_calories * 0.5:  # 50% difference threshold
                    calories = calculated_calories
            except ValueError:
                calories = calculate_calories(carbs, proteins, fats)
        else:
            # Calculate calories if not provided
            calories = calculate_calories(carbs, proteins, fats)
        
        # Generate unique key
        base_key = re.sub(r'[^a-z0-9_]', '', name.lower().replace(' ', '_')) or "custom_food"
        key = base_key
        counter = 1
        while True:
            cursor.execute('SELECT 1 FROM foods WHERE key = %s', (key,))
            if not cursor.fetchone():
                break
            key = f"{base_key}_{counter}"
            counter += 1
            if counter > 100:  # Fallback for too many duplicates
                key = f"custom_{uuid.uuid4().hex[:8]}"
                break
            
        # Create food object
        food_data = {
            "key": key,
            "name": name,
            "carbs": carbs,
            "sugars": sugars,
            "fiber": fiber,
            "proteins": proteins,
            "fats": fats,
            "saturated": saturated,
            "salt": salt,
            "calories": calories,
            "grams": grams,
            "half": half,
            "entire": entire,
            "serving": serving,
            "ean": ean
        }
        
        # Save to database
        cursor.execute('''
            INSERT INTO foods 
            (key, name, carbs, sugars, fiber, proteins, fats, saturated, salt, calories, grams, half, entire, serving, ean)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            food_data.get('ean')
        ))
        
        # Initialize usage count
        cursor.execute('''
            INSERT INTO food_usage (food_key, count)
            VALUES (%s, 1)
            ON CONFLICT (food_key) DO UPDATE SET count = food_usage.count + 1
        ''', (key,))
        
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
    
    # Group data by week
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
                    "count": 0
                }
        
            calories, proteins, fats, carbs, salt = get_daily_totals(items)
            weekly_data[week_key]["days"].append(date_str)
            weekly_data[week_key]["calories"] += calories
            weekly_data[week_key]["proteins"] += proteins
            weekly_data[week_key]["fats"] += fats
            weekly_data[week_key]["carbs"] += carbs
            weekly_data[week_key]["salt"] += salt
            weekly_data[week_key]["count"] += 1
        except Exception as e:
            app.logger.error(f"Error processing date {date_str}: {e}")
            continue
    
    # Calculate averages
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
                "avg_salt": data["salt"] / count
            })
    
    # Sort by week (newest first)
    result.sort(key=lambda x: x["end_date"], reverse=True)
    return result

@app.route('/history')
@login_required
def history():
    user_id = current_user.id
    session_history = get_session_history(user_id)
    today = datetime.today()
    daily_dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(-3, 4)]
    
    history_data = []
    for date in daily_dates:
        day_data = session_history.get(date, [])
        calories, proteins, fats, carbs, salt = get_daily_totals(day_data)
        history_data.append({
            'date': format_date(date),
            'calories': calories,
            'proteins': proteins,
            'fats': fats,
            'carbs': carbs,
            'salt': salt
            })
        
    # Weekly history
    weekly_data = calculate_weekly_averages(session_history)
    
    return render_template('history.html', 
                           history_data=history_data,
                           weekly_data=weekly_data)
# food templates #
@app.route('/save_template_food', methods=['POST'])
@login_required
def save_template_food():
    try:
        name = request.form.get('name')
        items_json = request.form.get('items', '[]')
        items = json.loads(items_json)
        
        if not name or not items:
            return jsonify({'success': False, 'error': 'Invalid data'})
        
        # Check if template with this name already exists
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT id FROM food_templates WHERE user_id = %s AND name = %s',
            (current_user.id, name)
        )
        if cursor.fetchone():
            return jsonify({'success': False, 'error': 'Template with this name already exists'})
        
        # Save template to database
        cursor.execute(
            'INSERT INTO food_templates (user_id, name) VALUES (%s, %s) RETURNING id',
            (current_user.id, name)
        )
        template_id = cursor.fetchone()[0]
        
        # Save template items
        for item in items:
            # Use the food_key directly from the request
            food_key = item.get('food_key')
            grams = item.get('grams')
            
            if not food_key or not grams:
                print(f"Missing food_key or grams for item: {item}")
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
        
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error saving template: {str(e)}")
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
        print(f"Applying template {template_id} with meal group: {meal_group}")
        date_str = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
        user_id = current_user.id
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get template items
        cursor.execute('''
            SELECT f.key, f.name, f.carbs, f.proteins, f.fats, f.saturated, f.fiber, f.sugars, f.salt, f.calories, fti.grams
            FROM food_template_items fti
            JOIN foods f ON fti.food_key = f.key
            WHERE fti.template_id = %s
        ''', (template_id,))
        
        template_items = cursor.fetchall()
        
        if not template_items:
            return jsonify({'success': False, 'error': 'Template not found or empty'})
        
        # Get current session data
        session_data, _ = get_current_session(current_user.id, date_str)
        
        # Add each template item to the session
        for item in template_items:
            factor = item[9] / 100  # Convert from grams to factor
            
            session_data.append({
                'id': str(uuid.uuid4()),  # Generate a unique ID for the session
                'key': item[0],           # Store the food key
                'name': item[1],
                'carbs': item[2] * factor,
                'proteins': item[3] * factor,
                'fats': item[4] * factor,
                'saturated': item[5] * factor,
                'fiber': item[6] * factor,
                'sugars': item[7] * factor,
                'salt': item[8] * factor,
                'calories': item[9] * factor,
                'grams': item[10],
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

@app.route('/debug_food_key/<food_id>')
@login_required
def debug_food_key(food_id):
    """Endpoint to check if a food key exists in the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT key, name FROM foods WHERE key = %s',
            (food_id,)
        )
        food = cursor.fetchone()
        
        if food:
            return jsonify({
                'success': True,
                'food': {'key': food[0], 'name': food[1]}
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Food with key {food_id} not found'
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
    dates = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    current_date = today.strftime("%Y-%m-%d")
    return jsonify(dates=dates, current_date=current_date)

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

@app.route('/workout/get_exercises', methods=['GET'])
@login_required
def get_exercises():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute("SELECT id, name, muscle_group, description FROM exercises ORDER BY name")
    exercises = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(exercises=exercises)

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
        # Updated query to include new columns
        cursor.execute(
            "SELECT id, muscle_group, notes, is_saved, workout_type FROM workout_sessions "
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
        
        # Now includes all needed columns
        session = {
            "id": session_data['id'],
            "muscle_group": session_data['muscle_group'],
            "notes": session_data['notes'],
            "is_saved": session_data['is_saved'],
            "workout_type": session_data['workout_type']
        }

        session_id = session['id']
        
        # Get sets for this session and group by exercise - ADD NEW FIELDS
        cursor.execute(
            "SELECT s.id, e.id AS exercise_id, e.name AS exercise_name, "
            "e.muscle_group, s.reps, s.weight, s.volume, s.rir, s.comments "  # Added rir and comments
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
                'rir': row['rir'],  # NEW FIELD
                'comments': row['comments']  # NEW FIELD
            })
        
        conn.close()
    
        return jsonify({
            'success': True,
            'session': dict(session_data),
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
        return jsonify(success=False, error="Name and muscle group are required"), 400
    
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
        return jsonify(success=False, error="Exercise name already exists"), 400
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

@app.route('/workout/save_workout', methods=['POST'])
@login_required
def save_workout():
    user_id = current_user.id
    date = request.form.get('date')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE workout_sessions SET is_saved = TRUE "
            "WHERE user_id = %s AND date = %s",
            (user_id, date)
        )
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
            "FROM workout_sets WHERE session_id = ("
            "SELECT id FROM workout_sessions "
            "WHERE user_id = %s AND date = %s"
            ")",
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
        
        # Get template exercises
        cursor.execute('''
            SELECT e.id AS exercise_id, e.name, e.muscle_group,
                   t.reps, t.weight, t.rir, t.comments
            FROM workout_template_exercises t
            JOIN exercises e ON t.exercise_id = e.id
            WHERE t.template_id = %s
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

@app.route('/workout/copy_session', methods=['POST'])
@login_required
def copy_workout_session():
    conn = None
    try:
        source_date = request.form.get('source_date')
        target_date = request.form.get('target_date')
        user_id = current_user.id
        
        if not source_date or not target_date:
            return jsonify(success=False, error="Missing date parameters"), 400
            
        if source_date == target_date:
            return jsonify(success=False, error="Cannot copy to same date"), 400
            
        # Get database connection
        conn = get_db_connection()
        if not conn:
            return jsonify(success=False, error="Database connection failed"), 500
            
        cursor = conn.cursor()
        
        # Get source session
        cursor.execute(
            "SELECT id FROM workout_sessions "
            "WHERE user_id = %s AND date = %s",
            (user_id, source_date)
        )
        source_session = cursor.fetchone()
        
        if not source_session:
            return jsonify(success=False, error="No workout found for source date"), 404
            
        source_session_id = source_session[0]
        
        # Get target session (create if doesn't exist)
        cursor.execute(
            "SELECT id FROM workout_sessions "
            "WHERE user_id = %s AND date = %s",
            (user_id, target_date)
        )
        target_session = cursor.fetchone()
        
        if target_session:
            target_session_id = target_session[0]
        else:
            # Get muscle group from source session
            cursor.execute(
                "SELECT muscle_group FROM workout_sessions "
                "WHERE id = %s",
                (source_session_id,)
            )
            muscle_group = cursor.fetchone()[0] or 'General'
            
            cursor.execute(
                "INSERT INTO workout_sessions (user_id, date, muscle_group) "
                "VALUES (%s, %s, %s) RETURNING id",
                (user_id, target_date, muscle_group)
            )
            target_session_id = cursor.fetchone()[0]
        
        # Copy sets
        cursor.execute(
            "INSERT INTO workout_sets (session_id, exercise_id, reps, weight, rir, comments) "
            "SELECT %s, exercise_id, reps, weight, rir, comments "
            "FROM workout_sets "
            "WHERE session_id = %s",
            (target_session_id, source_session_id)
        )
        
        conn.commit()
        return jsonify(success=True)
        
    except Exception as e:
        if conn:
            conn.rollback()
        app.logger.error(f"Error copying workout session: {str(e)}")
        return jsonify(success=False, error=str(e)), 500
    finally:
        if conn:
            conn.close()

# Get all exercises endpoint
@app.route('/workout/exercises')
@login_required
def get_exercises_list():  # Changed function name
    user_id = current_user.id
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    
    try:
        # Simplified query to avoid complex subqueries
        cursor.execute('''
            SELECT 
                e.id,
                e.name,
                e.muscle_group,
                MAX(ws.weight) AS personal_best,
                MAX(s.date) AS last_performed,
                SUM(ws.volume) AS total_volume
            FROM workout_sets ws
            JOIN workout_sessions s ON ws.session_id = s.id
            JOIN exercises e ON ws.exercise_id = e.id
            WHERE s.user_id = %s
            GROUP BY e.id
            ORDER BY e.name
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
                # Volume trend will be calculated client-side
                'volume_trend': 0  
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
                MAX(ws.weight || 'x' || ws.reps || 'kg') AS best_set,
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
        best_set = f"{best_set_row['reps']}x{best_set_row['weight']}kg" if best_set_row else '-'
        
        return jsonify({
            'name': exercise['name'],
            'personal_best': personal_best,
            'monthly_volume': monthly_volume,
            'best_set': best_set,
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

def extract_nutrition_data(mindee_response):
    """
    Extract nutrition data from Mindee API response
    with support for Finnish nutrient names and kJ conversion.
    """
    nutrition_data = {}

    # Finnish → English mapping
    NUTRIENT_MAP = {
        "rasva": "fat",
        "tyydyttynyt rasva": "saturated fat",
        "hiilihydraatit": "carbohydrate",
        "sokerit": "sugars",
        "proteiini": "protein",
        "suola": "salt",
        "kuitu": "fiber",
        "energia": "energy"
    }

    try:
        predictions = mindee_response.get('document', {}).get('inference', {}).get('prediction', {})

        # Product name
        if 'product_name' in predictions:
            nutrition_data['product_name'] = predictions['product_name'].get('value')

        # Nutrients
        nutrients = predictions.get('nutrients', [])
        for nutrient in nutrients:
            nutrient_name = nutrient.get('name', '').lower()
            nutrient_value = nutrient.get('quantity')
            nutrient_unit = nutrient.get('unit', '').lower()

            if not nutrient_name or nutrient_value is None:
                continue

            # Map Finnish to English
            nutrient_name = NUTRIENT_MAP.get(nutrient_name, nutrient_name)

            # Energy: convert kJ → kcal if needed
            if nutrient_name in ["energy", "energy kcal"]:
                if nutrient_unit == "kj":
                    nutrition_data['calories'] = round(nutrient_value / 4.184, 2)
                else:
                    nutrition_data['calories'] = nutrient_value

            elif nutrient_name in ["fat", "total fat"]:
                nutrition_data['fats'] = nutrient_value
            elif nutrient_name == "saturated fat":
                nutrition_data['saturated_fat'] = nutrient_value
            elif nutrient_name in ["carbohydrate", "total carbohydrate"]:
                nutrition_data['carbohydrates'] = nutrient_value
            elif nutrient_name in ["sugars", "sugar"]:
                nutrition_data['sugars'] = nutrient_value
            elif nutrient_name in ["fiber", "dietary fiber"]:
                nutrition_data['fiber'] = nutrient_value
            elif nutrient_name == "protein":
                nutrition_data['proteins'] = nutrient_value
            elif nutrient_name in ["salt", "sodium"]:
                if nutrient_name == "sodium":
                    nutrition_data['salt'] = nutrient_value * 2.5  # Na → salt conversion
                else:
                    nutrition_data['salt'] = nutrient_value

        return nutrition_data

    except Exception as e:
        print(f"Error extracting nutrition data: {e}")
        return nutrition_data

@app.route('/process_nutrition_label', methods=['POST'])
@login_required
def process_nutrition_label():
    try:
        api_key = current_app.config.get('MINDEE_API_KEY')
        if not api_key:
            return jsonify({'success': False, 'error': 'Mindee API key not configured in .env'})

        # Choose endpoint based on sandbox flag
        if current_app.config.get('MINDEE_USE_SANDBOX'):
            api_url = "https://api.mindee.net/v1/products/mindee/nutrition_facts/v1/predict/sandbox"
        else:
            api_url = "https://api.mindee.net/v1/products/mindee/nutrition_facts/v1/predict"

        # Check if image was uploaded
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image uploaded'})

        image_file = request.files['image']
        image_data = image_file.read()
        encoded_image = base64.b64encode(image_data).decode('utf-8')

        headers = {
            'Authorization': f'Token {api_key}',
            'Content-Type': 'application/json',
        }
        data = {'document': encoded_image}

        response = requests.post(api_url, headers=headers, json=data)

        # Handle common errors
        if response.status_code == 401:
            return jsonify({'success': False, 'error': 'Unauthorized: Check your Mindee API key or endpoint (sandbox vs production)'})
        elif response.status_code != 201:
            return jsonify({'success': False, 'error': f'Mindee API error: {response.status_code} - {response.text}'})

        result = response.json()
        nutrition_data = extract_nutrition_data(result)

        return jsonify({'success': True, 'data': nutrition_data})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def extract_nutrition_data(mindee_response):
    """
    Extract nutrition data from Mindee API response
    """
    nutrition_data = {}

    try:
        predictions = mindee_response.get('document', {}).get('inference', {}).get('prediction', {})

        if 'product_name' in predictions:
            nutrition_data['product_name'] = predictions['product_name']['value']

        nutrients = predictions.get('nutrients', [])
        for nutrient in nutrients:
            name = nutrient.get('name', '').lower()
            value = nutrient.get('quantity')
            unit = nutrient.get('unit')

            if name and value is not None:
                if name in ['energy', 'energy kcal']:
                    nutrition_data['calories'] = value
                elif name in ['fat', 'total fat']:
                    nutrition_data['fats'] = value
                elif name == 'saturated fat':
                    nutrition_data['saturated_fat'] = value
                elif name in ['carbohydrate', 'total carbohydrate']:
                    nutrition_data['carbohydrates'] = value
                elif name in ['sugars', 'sugar']:
                    nutrition_data['sugars'] = value
                elif name in ['fiber', 'dietary fiber']:
                    nutrition_data['fiber'] = value
                elif name == 'protein':
                    nutrition_data['proteins'] = value
                elif name in ['salt', 'sodium']:
                    nutrition_data['salt'] = value if name == 'salt' else value * 2.5

        return nutrition_data

    except Exception as e:
        print(f"Error extracting nutrition data: {e}")
        return nutrition_data

    
@app.route('/foods')
def list_foods():
    cursor = get_cursor()
    cursor.execute("SELECT * FROM foods LIMIT 10;")
    foods = cursor.fetchall()
    cursor.close()
    return jsonify(foods)        
    
if __name__ == '__main__':
    try:
        print("[INIT] Initializing main database...")
        init_db()  # must run first: creates users, foods, etc.
        print("[INIT] Main database initialized.")

        print("[INIT] Initializing workout database...")
        init_workout_db()  # now safe: users table exists
        print("[INIT] Workout database initialized.")

        print("[INIT] Migrating JSON food data (if any)...")
        migrate_json_to_db()
        print("[INIT] JSON migration complete.")

        print("[INIT] Updating food keys normalization...")
        update_food_keys_normalization()
        print("[INIT] Food keys updated.")



        print("[START] Running Flask app...")
        app.run(debug=True)

    except Exception as e:
        print(f"[ERROR] Initialization failed: {e}")
