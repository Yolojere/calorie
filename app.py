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
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
from itsdangerous import URLSafeTimedSerializer as Serializer
import smtplib
from email.mime.text import MIMEText
from functools import wraps
from urllib.parse import urlparse
import os
from dotenv import load_dotenv
import traceback


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

# Update the normalize_key function
def normalize_key(key):
    """Normalize food key while preserving non-ASCII characters"""
    if key is None:
        return ""
    # Preserve all Unicode letters and numbers, plus allowed special characters
    normalized = re.sub(r'[^\w\s\-.,%+]', '', key, flags=re.UNICODE)
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
    DATABASE_URL = os.getenv('DATABASE_URL')
    print(f"Connecting to database: {DATABASE_URL.split('@')[-1]}")
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        conn.autocommit = True
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        raise
    result = urlparse(DATABASE_URL)
    conn = psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port,
        sslmode='require'
    )
    conn.autocommit = True
    return conn

# Initialize database
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Create users table first
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            role TEXT NOT NULL DEFAULT 'user',
            reset_token TEXT,
            reset_token_expiration TIMESTAMP
        )
    ''')
    
    # 2. Create foods table
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
            ean TEXT
        )
    ''')
    
    # 3. Create food_usage table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_usage (
            food_key TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0,
            FOREIGN KEY (food_key) REFERENCES foods(key)
        )
    ''')
    
    # 4. Create user_sessions table last (depends on users)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            data TEXT NOT NULL,
            PRIMARY KEY (user_id, date),
            FOREIGN KEY (user_id) REFERENCES users(id)
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
    conn.close()

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
                food['carbs'],
                food.get('sugars', 0),
                food.get('fiber', 0),
                food['proteins'],
                food['fats'],
                food.get('saturated', 0),
                food.get('salt', 0),
                food['calories'],
                food['grams'],
                food.get('half'),
                food.get('entire'),
                food.get('serving'),
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
    def __init__(self, id, username, email, role):
        self.id = id
        self.username = username
        self.email = email
        self.role = role

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return user_id
        

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
        # First try exact match with normalized key
        cursor.execute('SELECT * FROM foods WHERE key = %s', (normalized_key,))
        food = cursor.fetchone()
        
        if food:
            print(f"✔️ Found food by exact match: {food['name']}")
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
    
    return render_template('index.html', 
                           eaten_items=eaten_items,
                           totals=totals,
                           current_date=current_date,
                           current_date_formatted=current_date_formatted,
                           dates=dates,
                           food_usage=food_usage,
                           group_breakdown=group_breakdown)

@app.route('/custom_food')
@login_required
def custom_food():
    return render_template('custom_food.html')

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

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = UpdateProfileForm()
    if form.validate_on_submit():
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'UPDATE users SET username = %s, email = %s WHERE id = %s',
                (form.username.data, form.email.data, current_user.id)
            )
            conn.commit()
            flash('Your profile has been updated!', 'success')
            return redirect(url_for('profile'))
        except psycopg2.IntegrityError:
            flash('Username or email already taken', 'danger')
        finally:
            conn.close()
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    return render_template('profile.html', title='Profile', form=form)

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
            LIMIT 10
        ''')
    else:
        cursor.execute('''
            SELECT f.*, COALESCE(u.count, 0) as usage
            FROM foods f
            LEFT JOIN food_usage u ON f.key = u.food_key
            WHERE LOWER(f.name) LIKE %s OR f.ean = %s
            ORDER BY usage DESC, name ASC
            LIMIT 10
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
            'name': food['name'],
            'units': units,
            'unit_type': unit_type,
            'carbs': carbs,
            'proteins': proteins,
            'fats': fats,
            'salt': salt,
            'calories': calories,
            'serving_size': food.get('serving'),
            'half_size': food.get('half'),
            'entire_size': food.get('entire')
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

                # Print for debugging
        print(f"Logging food: original='{food_id}', normalized='{normalized_key}'")
              
        food = get_food_by_key(normalized_key)
        if not food:
            print(f"Food not found: '{normalized_key}'")
            return jsonify({'error': 'Food not found'}), 404

        # ... rest of your function code goes here ...
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
        salt = food.get('salt', 0.0) * factor
        sugars = food.get('sugars', 0.0) * factor
        fiber = food.get('fiber', 0.0) * factor
        saturated = food.get('saturated', 0.0) * factor
        calories = food['calories'] * factor
        
        item = {
            "name": food['name'],
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
            'breakdown': group_breakdown
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
    eaten_items, current_date = get_current_session(user_id, date)
    totals = calculate_totals(eaten_items)
    group_breakdown = calculate_group_breakdown(eaten_items)
    current_date_formatted = format_date(current_date)
    return jsonify({
        'session': eaten_items,
        'totals': totals,
        'current_date': current_date,
        'current_date_formatted': current_date_formatted,
        'breakdown': group_breakdown
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
    item_index = int(request.form.get('item_index'))
    date = request.form.get('date', datetime.now().strftime("%Y-%m-%d"))
    
    eaten_items, current_date = get_current_session(user_id, date)
    if 0 <= item_index < len(eaten_items):
        del eaten_items[item_index]
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


@app.route('/move_items', methods=['POST'])
@login_required
def move_items():
    user_id = current_user.id
    date = request.form.get('date', datetime.now().strftime("%Y-%m-%d"))
    item_indices = json.loads(request.form.get('item_indices'))
    new_group = request.form.get('new_group')
    target_date = request.form.get('target_date', date)
    
    # Get source session
    eaten_items, current_date = get_current_session(user_id, date)
    
    # Move items to target date and group
    moved_items = []
    for idx in sorted(item_indices, reverse=True):
        if 0 <= idx < len(eaten_items):
            item = eaten_items.pop(idx)
            item['group'] = new_group
            moved_items.append(item)
    
    # Save source session
    save_current_session(user_id, eaten_items, date)
    
    # Get target session and add moved items
    target_items, _ = get_current_session(user_id, target_date)
    target_items.extend(moved_items)
    save_current_session(user_id, target_items, target_date)
    
    # Calculate totals using current data (no need to refetch)
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



@app.route('/update_grams', methods=['POST'])
@login_required
def update_grams():
    try:
        print("Received update_grams request")
        user_id = current_user.id
        item_index = int(request.form.get('item_index'))
        new_grams = float(request.form.get('new_grams'))
        date = request.form.get('date', datetime.now().strftime("%Y-%m-%d"))
        
        print(f"Params: index={item_index}, grams={new_grams}, date={date}")
        
        eaten_items, current_date = get_current_session(user_id, date)
        print(f"Current session has {len(eaten_items)} items")
        
        if 0 <= item_index < len(eaten_items):
            item = eaten_items[item_index]
            print(f"Food name from session: {item['name']}")
            
            food = get_food_by_key(item['name'])
            if not food:
                print(f"Food not found in database!")
                return jsonify({'error': 'Food not found'}), 404
            
            # Recalculate nutrition
            factor = new_grams / 100
            item['grams'] = new_grams
            item['units'] = new_grams
            item['unit_type'] = 'grams'
            item['carbs'] = food['carbs'] * factor
            item['proteins'] = food['proteins'] * factor
            item['fats'] = food['fats'] * factor
            item['salt'] = food.get('salt', 0.0) * factor
            item['calories'] = food['calories'] * factor
            
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
    try:
        # Extract form data
        name = request.form.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400
        

        # Generate key from name - ensure it's never empty
        base_key = re.sub(r'[^a-z0-9_]', '', name.lower().replace(' ', '_'))
        if not base_key:  # Handle empty key case
            base_key = "custom_food"
              
        # Convert to floats with safe_float
        carbs = safe_float(request.form.get('carbs', 0))
        sugars = safe_float(request.form.get('sugars', 0))
        fiber = safe_float(request.form.get('fiber', 0))
        proteins = safe_float(request.form.get('proteins', 0))
        fats = safe_float(request.form.get('fats', 0))
        saturated = safe_float(request.form.get('saturated', 0))
        salt = safe_float(request.form.get('salt', 0))
        ean = request.form.get('ean') or None
        
        # Handle optional portion fields properly
        serving_val = request.form.get('serving')
        half_val = request.form.get('half')
        entire_val = request.form.get('entire')
        
        # Convert to float if provided, otherwise None
        serving = safe_float(serving_val, None) if serving_val else None
        half = safe_float(half_val, None) if half_val else None
        entire = safe_float(entire_val, None) if entire_val else None
        
        # Base grams handling
        grams_val = request.form.get('grams', '100')
        grams = safe_float(grams_val, 100, min_val=0.001)
        # Calculate calories
        calories = calculate_calories(carbs, proteins, fats)
        
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Generate unique key with fallback
            key = base_key
            counter = 1
            while True:
                cursor.execute('SELECT 1 FROM foods WHERE key = %s', (key,))
                existing = cursor.fetchone()
                if not existing:
                    break
                key = f"{base_key}_{counter}"
                counter += 1
                # Fallback if we have too many duplicates
                if counter > 100:
                    key = f"custom_{uuid.uuid4().hex[:8]}"
                    break
        
            # Ensure key is not empty
            if not key:
                key = f"food_{int(time.time())}"
                
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
            
            # Initialize usage count
            cursor.execute('''
                INSERT INTO food_usage (food_key, count)
                VALUES (%s, 1)
                ON CONFLICT (food_key) DO UPDATE SET count = food_usage.count + 1
            ''', (key,))
            conn.commit()
            
            return jsonify({'success': True})
        finally:
            conn.close()
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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

@app.route('/admin')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute('SELECT id, username, email, role, created_at FROM users')
    users = cursor.fetchall()
    conn.close()
    return render_template('admin.html', users=users)

if __name__ == '__main__':
        init_db()
        migrate_json_to_db()
        update_food_keys_normalization()
        app.run(debug=True)
