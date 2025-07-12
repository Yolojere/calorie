# app.py
from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

# Data paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FOOD_FILE = os.path.join(BASE_DIR, 'data', 'foods.json')
USAGE_FILE = os.path.join(BASE_DIR, 'data', 'food_usage.json')
SESSION_FILE = os.path.join(BASE_DIR, 'data', 'session_history.json')

# Initialize data files if they don't exist
def init_data_files():
    os.makedirs(os.path.dirname(FOOD_FILE), exist_ok=True)
    
    # Initialize foods.json with default foods if empty
    if not os.path.exists(FOOD_FILE):
        default_foods = {
            "chicken breast": {
                "name": "Chicken breast",
                "carbs": 0,
                "sugars": 0,
                "fiber": 0,
                "proteins": 31,
                "fats": 3.6,
                "saturated": 1.0,
                "salt": 0.1,
                "calories": 165.4,
                "grams": 100,
                "half": 150,
                "entire": 300,
                "serving": 100,
                "ean": None
            },
            "rice": {
                "name": "Rice",
                "carbs": 28,
                "sugars": 0.1,
                "fiber": 0.4,
                "proteins": 2.7,
                "fats": 0.3,
                "saturated": 0.1,
                "salt": 0.01,
                "calories": 130.4,
                "grams": 100,
                "half": 90,
                "entire": 180,
                "serving": 150,
                "ean": None
            },
            "broccoli": {
                "name": "Broccoli",
                "carbs": 7,
                "sugars": 1.5,
                "fiber": 2.6,
                "proteins": 2.8,
                "fats": 0.4,
                "saturated": 0.1,
                "salt": 0.03,
                "calories": 34,
                "grams": 100,
                "half": 150,
                "entire": 300,
                "serving": 85,
                "ean": None
            }
        }
        with open(FOOD_FILE, 'w') as f:
            json.dump(default_foods, f, indent=2)
    
    # Initialize other files
    if not os.path.exists(USAGE_FILE):
        with open(USAGE_FILE, 'w') as f:
            json.dump({}, f)
    
    if not os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, 'w') as f:
            json.dump({}, f)

init_data_files()

# Helper functions
def calculate_calories(carbs, proteins, fats):
    return carbs * 4 + proteins * 4 + fats * 9

def get_foods():
    with open(FOOD_FILE, 'r') as f:
        return json.load(f)

def save_foods(foods):
    with open(FOOD_FILE, 'w') as f:
        json.dump(foods, f, indent=2)

def get_food_usage():
    with open(USAGE_FILE, 'r') as f:
        return json.load(f)

def save_food_usage(food_usage):
    with open(USAGE_FILE, 'w') as f:
        json.dump(food_usage, f, indent=2)

def get_session_history():
    with open(SESSION_FILE, 'r') as f:
        return json.load(f)

def save_session_history(session_history):
    with open(SESSION_FILE, 'w') as f:
        json.dump(session_history, f, indent=2)

def increment_food_usage(food_name, food_usage):
    food_name_lower = food_name.lower()
    food_usage[food_name_lower] = food_usage.get(food_name_lower, 0) + 1
    save_food_usage(food_usage)

def get_current_session(day=None):
    session_history = get_session_history()
    if day is None:
        day = datetime.now().strftime("%A")
    
    return session_history.get(day, []), day

def save_current_session(eaten_items, day):
    session_history = get_session_history()
    session_history[day] = eaten_items
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
    total_carbs = sum(item['carbs'] for item in day_data)
    total_proteins = sum(item['proteins'] for item in day_data)
    total_fats = sum(item['fats'] for item in day_data)
    total_salt = sum(item.get('salt', 0.0) for item in day_data)
    total_calories = sum(item['calories'] for item in day_data)
    return total_calories, total_proteins, total_fats, total_carbs, total_salt

# Routes
@app.route('/')
def index():
    eaten_items, current_day = get_current_session()
    totals = calculate_totals(eaten_items)
    food_usage = get_food_usage()
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    group_breakdown = calculate_group_breakdown(eaten_items)
    
    return render_template('index.html', 
                           eaten_items=eaten_items,
                           totals=totals,
                           current_day=current_day,
                           days_of_week=days_of_week,
                           food_usage=food_usage,
                           group_breakdown=group_breakdown)

@app.route('/search_foods', methods=['POST'])
def search_foods():
    query = request.form.get('query', '').lower()
    foods = get_foods()
    food_usage = get_food_usage()
    
    # Search for EAN matches first
    ean_matches = []
    for key, food in foods.items():
        if food.get('ean') and str(food['ean']).strip().lower() == query:
            usage = food_usage.get(key, 0)
            ean_matches.append((food, usage))
    
    # Then name matches
    name_matches = []
    for key, food in foods.items():
        if query in food['name'].lower():
            usage = food_usage.get(key, 0)
            name_matches.append((food, usage))
    
    # Sort name matches by usage (descending) then name (ascending)
    name_matches.sort(key=lambda x: (-x[1], x[0]['name'].lower()))
    
    results = []
    for food, usage in ean_matches + name_matches:
        results.append({
            'id': food['name'].lower(),
            'name': food['name'],
            'calories': food['calories'],
            'has_serving': food.get('serving') is not None,
            'has_half': food.get('half') is not None,
            'has_entire': food.get('entire') is not None
        })
    
    return jsonify(results)

@app.route('/get_food_details', methods=['POST'])
def get_food_details():
    food_id = request.form.get('food_id')
    unit_type = request.form.get('unit_type')
    units = request.form.get('units')
    
    foods = get_foods()
    food = foods.get(food_id)
    
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
    day = request.form.get('day', datetime.now().strftime("%A"))
    
    foods = get_foods()
    food = foods.get(food_id)
    
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
    eaten_items, current_day = get_current_session(day)
    eaten_items.append(item)
    save_current_session(eaten_items, day)
    
    # Update food usage
    food_usage = get_food_usage()
    increment_food_usage(food['name'], food_usage)
    
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
    day = request.form.get('day', datetime.now().strftime("%A"))
    eaten_items, current_day = get_current_session(day)
    totals = calculate_totals(eaten_items)
    group_breakdown = calculate_group_breakdown(eaten_items)
    return jsonify({
        'session': eaten_items,
        'totals': totals,
        'current_day': day,
        'breakdown': group_breakdown
    })

@app.route('/delete_item', methods=['POST'])
def delete_item():
    item_index = int(request.form.get('item_index'))
    day = request.form.get('day', datetime.now().strftime("%A"))
    
    eaten_items, current_day = get_current_session(day)
    if 0 <= item_index < len(eaten_items):
        del eaten_items[item_index]
        save_current_session(eaten_items, day)
    
    totals = calculate_totals(eaten_items)
    group_breakdown = calculate_group_breakdown(eaten_items)
    return jsonify({
        'session': eaten_items,
        'totals': totals,
        'breakdown': group_breakdown
    })

@app.route('/clear_session', methods=['POST'])
def clear_session():
    day = request.form.get('day', datetime.now().strftime("%A"))
    save_current_session([], day)
    group_breakdown = calculate_group_breakdown([])
    return jsonify({
        'session': [],
        'totals': calculate_totals([]),
        'breakdown': group_breakdown
    })

@app.route('/move_to_day', methods=['POST'])
def move_to_day():
    source_day = request.form.get('source_day')
    target_day = request.form.get('target_day')
    
    session_history = get_session_history()
    if source_day in session_history:
        session_history[target_day] = session_history[source_day].copy()
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
    
    # In a real app, you'd store custom groups in a file/database
    return jsonify({'success': True, 'group_name': group_name})

@app.route('/custom_food')
def custom_food():
    return render_template('custom_food.html')

@app.route('/save_food', methods=['POST'])
def save_food():
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
    food = {
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
    foods = get_foods()
    foods[name.lower()] = food
    save_foods(foods)
    
    # Initialize usage count
    food_usage = get_food_usage()
    if name.lower() not in food_usage:
        food_usage[name.lower()] = 0
        save_food_usage(food_usage)
    
    return jsonify({'success': True})

@app.route('/history')
def history():
    session_history = get_session_history()
    
    # Get dates for the last 7 days
    today = datetime.today()
    dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    
    # Prepare history data
    history_data = []
    for date in dates:
        if date in session_history:
            calories, proteins, fats, carbs, salt = get_daily_totals(session_history[date])
            history_data.append({
                'date': datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y"),
                'calories': calories,
                'proteins': proteins,
                'fats': fats,
                'carbs': carbs,
                'salt': salt
            })
    
    return render_template('history.html', history_data=history_data)

@app.route('/update_item', methods=['POST'])
def update_item():
    item_index = int(request.form.get('item_index'))
    units = float(request.form.get('units'))
    unit_type = request.form.get('unit_type')
    day = request.form.get('day', datetime.now().strftime("%A"))
    
    eaten_items, current_day = get_current_session(day)
    
    if 0 <= item_index < len(eaten_items):
        item = eaten_items[item_index]
        
        # Get original food data
        foods = get_foods()
        food = foods.get(item['name'].lower())
        
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
        item['grams'] = grams
        item['units'] = units
        item['unit_type'] = unit_type
        item['carbs'] = food['carbs'] * factor
        item['proteins'] = food['proteins'] * factor
        item['fats'] = food['fats'] * factor
        item['salt'] = food.get('salt', 0.0) * factor
        item['calories'] = food['calories'] * factor
        
        save_current_session(eaten_items, day)
    
    totals = calculate_totals(eaten_items)
    return jsonify({
        'session': eaten_items,
        'totals': totals
    })

if __name__ == '__main__':
    app.run(debug=True)