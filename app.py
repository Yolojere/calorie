from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import os
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

# Database path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'foods.db')
FOOD_FILE = os.path.join(BASE_DIR, 'data', 'foods.json')  # Kept for migration
USAGE_FILE = os.path.join(BASE_DIR, 'data', 'food_usage.json')  # Kept for migration
SESSION_FILE = os.path.join(BASE_DIR, 'data', 'session_history.json')

# Database connection
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database
def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create foods table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            carbs REAL NOT NULL,
            sugars REAL NOT NULL,
            fiber REAL NOT NULL,
            proteins REAL NOT NULL,
            fats REAL NOT NULL,
            saturated REAL NOT NULL,
            salt REAL NOT NULL,
            calories REAL NOT NULL,
            grams REAL NOT NULL,
            half REAL,
            entire REAL,
            serving REAL,
            ean TEXT
        )
    ''')
    
    # Create food_usage table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_usage (
            food_key TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0,
            FOREIGN KEY (food_key) REFERENCES foods(key)
        )
    ''')
    
    # Check if foods table is empty
    cursor.execute("SELECT COUNT(*) FROM foods")
    if cursor.fetchone()[0] == 0:
        # Insert default food
        cursor.execute('''
            INSERT INTO foods 
            (key, name, carbs, sugars, fiber, proteins, fats, saturated, salt, calories, grams, half, entire, serving, ean)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'broccoli',
            'Broccoli',
            7, 1.5, 2.6, 2.8, 0.4, 0.1, 0.03, 34, 100, 150, 300, 85, None
        ))
    
    conn.commit()
    conn.close()

# Migrate JSON data to database
def migrate_json_to_db():
    # Migrate foods
    if os.path.exists(FOOD_FILE):
        with open(FOOD_FILE, 'r') as f:
            foods = json.load(f)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for key, food in foods.items():
            # Handle EAN field - convert list to string if needed
            ean = food.get('ean')
            if isinstance(ean, list):
                ean = ', '.join(ean) if ean else None
            
            try:
                cursor.execute('''
                    INSERT INTO foods 
                    (key, name, carbs, sugars, fiber, proteins, fats, saturated, salt, calories, grams, half, entire, serving, ean)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    ean  # Use the processed EAN value
                ))
            except sqlite3.IntegrityError:
                pass  # Skip duplicates
        
        conn.commit()
        conn.close()
        if os.path.exists(FOOD_FILE):
            os.rename(FOOD_FILE, FOOD_FILE + ".bak")
    
    # Migrate food_usage
    if os.path.exists(USAGE_FILE):
        with open(USAGE_FILE, 'r') as f:
            usage = json.load(f)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for key, count in usage.items():
            try:
                cursor.execute('''
                    INSERT INTO food_usage (food_key, count)
                    VALUES (?, ?)
                    ON CONFLICT(food_key) DO UPDATE SET count = count + ?
                ''', (key, count, count))
            except sqlite3.IntegrityError:
                pass
        
        conn.commit()
        conn.close()
        if os.path.exists(USAGE_FILE):
            os.rename(USAGE_FILE, USAGE_FILE + ".bak")

    
    # Migrate food_usage
    if os.path.exists(USAGE_FILE):
        with open(USAGE_FILE, 'r') as f:
            usage = json.load(f)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for key, count in usage.items():
            try:
                cursor.execute('''
                    INSERT INTO food_usage (food_key, count)
                    VALUES (?, ?)
                    ON CONFLICT(food_key) DO UPDATE SET count = count + ?
                ''', (key, count, count))
            except sqlite3.IntegrityError:
                pass
        
        conn.commit()
        conn.close()
        os.rename(USAGE_FILE, USAGE_FILE + ".bak")

# Initialize database and migrate data
init_db()
migrate_json_to_db()

# Helper functions
def calculate_calories(carbs, proteins, fats):
    return carbs * 4 + proteins * 4 + fats * 9

def get_foods():
    conn = get_db_connection()
    foods = conn.execute('SELECT * FROM foods').fetchall()
    conn.close()
    return {food['key']: dict(food) for food in foods}

def get_food_by_key(key):
    conn = get_db_connection()
    food = conn.execute('SELECT * FROM foods WHERE key = ?', (key,)).fetchone()
    conn.close()
    return dict(food) if food else None

def save_food(food_data):
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT OR REPLACE INTO foods 
            (key, name, carbs, sugars, fiber, proteins, fats, saturated, salt, calories, grams, half, entire, serving, ean)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    usage = conn.execute('SELECT food_key, count FROM food_usage').fetchall()
    conn.close()
    return {row['food_key']: row['count'] for row in usage}

def increment_food_usage(food_name):
    key = food_name.lower()
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO food_usage (food_key, count)
            VALUES (?, 1)
            ON CONFLICT(food_key) DO UPDATE SET count = count + 1
        ''', (key,))
        conn.commit()
    finally:
        conn.close()

def get_session_history():
    if not os.path.exists(SESSION_FILE):
        return {}
    
    with open(SESSION_FILE, 'r') as f:
        try:
            return json.load(f)
        except:
            return {}

def save_session_history(session_history):
    with open(SESSION_FILE, 'w') as f:
        json.dump(session_history, f, indent=2)

def get_current_session(date=None):
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    session_history = get_session_history()
    return session_history.get(date, []), date

def save_current_session(eaten_items, date):
    session_history = get_session_history()
    session_history[date] = eaten_items
    save_session_history(session_history)

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
                "salt": 0
            }
        
        groups[group]["items"].append(item)
        groups[group]["calories"] += item['calories']
        groups[group]["carbs"] += item['carbs']
        groups[group]["proteins"] += item['proteins']
        groups[group]["fats"] += item['fats']
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
    total_calories = sum(item['calories'] for item in day_data)
    total_proteins = sum(item['proteins'] for item in day_data)
    total_fats = sum(item['fats'] for item in day_data)
    total_carbs = sum(item['carbs'] for item in day_data)
    total_salt = sum(item.get('salt', 0.0) for item in day_data)
    return total_calories, total_proteins, total_fats, total_carbs, total_salt

def format_date(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return date_obj.strftime("%A (%d.%m.%Y)")

# Routes
@app.route('/')
def index():
    eaten_items, current_date = get_current_session()
    totals = calculate_totals(eaten_items)
    food_usage = get_food_usage()
    group_breakdown = calculate_group_breakdown(eaten_items)
    
    # Generate dates for selector
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

@app.route('/search_foods', methods=['POST'])
def search_foods():
    query = request.form.get('query', '').lower().strip()
    conn = get_db_connection()
    
    if not query:
        # Get top 10 foods by usage
        foods = conn.execute('''
            SELECT f.*, COALESCE(u.count, 0) as usage
            FROM foods f
            LEFT JOIN food_usage u ON f.key = u.food_key
            ORDER BY usage DESC, name ASC
            LIMIT 10
        ''').fetchall()
    else:
        # Search by name OR EAN (supports Code-128) - UPDATED FOR BETTER MATCHING
        foods = conn.execute('''
            SELECT f.*, COALESCE(u.count, 0) as usage
            FROM foods f
            LEFT JOIN food_usage u ON f.key = u.food_key
            WHERE LOWER(f.name) LIKE ? OR f.ean LIKE ? OR f.ean = ?
            ORDER BY usage DESC, name ASC
            LIMIT 10
        ''', (f'%{query}%', f'%{query}%', query)).fetchall()
    
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
def get_food_details():
    food_id = request.form.get('food_id')
    unit_type = request.form.get('unit_type')
    units = request.form.get('units')
    
    food = get_food_by_key(food_id)
    if not food:
        return jsonify({'error': 'Food not found'}), 404
    
    # Default to grams if no units provided
    if not units or float(units) <= 0:
        units = 100
        unit_type = 'grams'
    else:
        units = float(units)
    
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
    calories = food['calories'] * factor
    
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

@app.route('/log_food', methods=['POST'])
def log_food():
    food_id = request.form.get('food_id')
    unit_type = request.form.get('unit_type')
    units = float(request.form.get('units'))
    meal_group = request.form.get('meal_group')
    date = request.form.get('date', datetime.now().strftime("%Y-%m-%d"))
    
    food = get_food_by_key(food_id)
    if not food:
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
    eaten_items, current_date = get_current_session(date)
    eaten_items.append(item)
    save_current_session(eaten_items, date)
    
    # Update food usage
    increment_food_usage(food['name'])
    
    # Return updated session, totals and breakdown
    totals = calculate_totals(eaten_items)
    group_breakdown = calculate_group_breakdown(eaten_items)
    return jsonify({
        'session': eaten_items,
        'totals': totals,
        'breakdown': group_breakdown
    })

@app.route('/update_session', methods=['POST'])
def update_session():
    date = request.form.get('date', datetime.now().strftime("%Y-%m-%d"))
    eaten_items, current_date = get_current_session(date)
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
def delete_food():
    food_id = request.form.get('food_id').lower()
    conn = get_db_connection()
    try:
        # Delete from both tables
        conn.execute('DELETE FROM foods WHERE key = ?', (food_id,))
        conn.execute('DELETE FROM food_usage WHERE food_key = ?', (food_id,))
        conn.commit()
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500
    finally:
        conn.close()

@app.route('/delete_item', methods=['POST'])
def delete_item():
    item_index = int(request.form.get('item_index'))
    date = request.form.get('date', datetime.now().strftime("%Y-%m-%d"))
    
    eaten_items, current_date = get_current_session(date)
    if 0 <= item_index < len(eaten_items):
        del eaten_items[item_index]
        save_current_session(eaten_items, date)
    
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
def clear_session():
    date = request.form.get('date', datetime.now().strftime("%Y-%m-%d"))
    save_current_session([], date)
    group_breakdown = calculate_group_breakdown([])
    current_date_formatted = format_date(date)
    return jsonify({
        'session': [],
        'totals': calculate_totals([]),
        'current_date_formatted': current_date_formatted,
        'breakdown': group_breakdown
    })

@app.route('/move_to_date', methods=['POST'])
def move_to_date():
    source_date = request.form.get('source_date')
    target_date = request.form.get('target_date')
    
    session_history = get_session_history()
    if source_date in session_history:
        session_history[target_date] = session_history[source_date].copy()
        save_session_history(session_history)
    
    return jsonify({'success': True})

@app.route('/create_group', methods=['POST'])
def create_group():
    group_name = request.form.get('group_name')
    predefined = ["breakfast", "lunch", "dinner", "snack", "Ungrouped"]
    
    if not group_name:
        return jsonify({'error': 'Group name is required'}), 400
    
    if group_name in predefined:
        return jsonify({'error': 'This is a reserved group name'}), 400
    
    return jsonify({'success': True, 'group_name': group_name})

@app.route('/custom_food')
def custom_food():
    return render_template('custom_food.html')

@app.route('/save_food', methods=['POST'])
def save_food_route():
    # Extract form data
    name = request.form.get('name')
    carbs = float(request.form.get('carbs', 0))
    sugars = float(request.form.get('sugars', 0))
    fiber = float(request.form.get('fiber', 0))
    proteins = float(request.form.get('proteins', 0))
    fats = float(request.form.get('fats', 0))
    saturated = float(request.form.get('saturated', 0))
    salt = float(request.form.get('salt', 0))
    ean = request.form.get('ean') or None
    grams = float(request.form.get('grams', 100))
    serving = request.form.get('serving')
    half = request.form.get('half')
    entire = request.form.get('entire')
    
    # Process optional fields
    serving = float(serving) if serving else None
    half = float(half) if half else None
    entire = float(entire) if entire else None
    
    # Calculate calories
    calories = calculate_calories(carbs, proteins, fats)
    
    # Create food object
    food_data = {
        "key": name.lower(),
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
    save_food(food_data)
    
    # Initialize usage count
    increment_food_usage(name)
    
    return jsonify({'success': True})

def calculate_weekly_averages():
    session_history = get_session_history()
    weekly_data = {}
    
    # Group data by week
    for date_str, items in session_history.items():
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        year, week_num, _ = date_obj.isocalendar()
        week_key = f"{year}-W{week_num}"
        
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
def history():
    # Daily history (last 7 days)
    session_history = get_session_history()
    today = datetime.today()
    daily_dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    
    history_data = []
    for date in daily_dates:
        if date in session_history:
            calories, proteins, fats, carbs, salt = get_daily_totals(session_history[date])
            history_data.append({
                'date': format_date(date),
                'calories': calories,
                'proteins': proteins,
                'fats': fats,
                'carbs': carbs,
                'salt': salt
            })
        else:
            history_data.append({
                'date': format_date(date),
                'calories': 0,
                'proteins': 0,
                'fats': 0,
                'carbs': 0,
                'salt': 0
            })
    
    # Weekly history
    weekly_data = calculate_weekly_averages()
    
    return render_template('history.html', 
                           history_data=history_data,
                           weekly_data=weekly_data)

@app.route('/update_grams', methods=['POST'])
def update_grams():
    item_index = int(request.form.get('item_index'))
    new_grams = float(request.form.get('new_grams'))
    date = request.form.get('date', datetime.now().strftime("%Y-%m-%d"))
    
    eaten_items, current_date = get_current_session(date)
    
    if 0 <= item_index < len(eaten_items):
        item = eaten_items[item_index]
        
        # Get original food data
        food = get_food_by_key(item['name'].lower())
        if not food:
            return jsonify({'error': 'Food not found'}), 404
        
        # Update grams and recalculate nutrition
        item['grams'] = new_grams
        item['units'] = new_grams
        item['unit_type'] = 'grams'
        
        factor = new_grams / 100
        item['carbs'] = food['carbs'] * factor
        item['proteins'] = food['proteins'] * factor
        item['fats'] = food['fats'] * factor
        item['salt'] = food.get('salt', 0.0) * factor
        item['calories'] = food['calories'] * factor
        
        save_current_session(eaten_items, date)
    
    totals = calculate_totals(eaten_items)
    group_breakdown = calculate_group_breakdown(eaten_items)
    current_date_formatted = format_date(current_date)
    return jsonify({
        'session': eaten_items,
        'totals': totals,
        'current_date_formatted': current_date_formatted,
        'breakdown': group_breakdown
    })

@app.route('/move_items', methods=['POST'])
def move_items():
    date = request.form.get('date', datetime.now().strftime("%Y-%m-%d"))
    item_indices = json.loads(request.form.get('item_indices'))
    new_group = request.form.get('new_group')
    
    eaten_items, current_date = get_current_session(date)
    # Update the group for each selected item
    for idx in item_indices:
        if 0 <= idx < len(eaten_items):
            eaten_items[idx]['group'] = new_group
    
    save_current_session(eaten_items, date)
    
    # Return the updated session and breakdown
    group_breakdown = calculate_group_breakdown(eaten_items)
    totals = calculate_totals(eaten_items)
    current_date_formatted = format_date(current_date)
    return jsonify({
        'session': eaten_items,
        'totals': totals,
        'current_date_formatted': current_date_formatted,
        'breakdown': group_breakdown
    })

if __name__ == '__main__':
    app.run(debug=True)
