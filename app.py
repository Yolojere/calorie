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
    try:
        with open(USAGE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_food_usage(food_usage):
    with open(USAGE_FILE, 'w') as f:
        json.dump(food_usage, f, indent=2)

def get_session_history():
    with open(SESSION_FILE, 'r') as f:
        try:
            return json.load(f)
        except:
            return {}

def save_session_history(session_history):
    with open(SESSION_FILE, 'w') as f:
        json.dump(session_history, f, indent=2)

def increment_food_usage(food_name, food_usage):
    food_name_lower = food_name.lower()
    food_usage[food_name_lower] = food_usage.get(food_name_lower, 0) + 1
    save_food_usage(food_usage)

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
    """Format date as 'Weekday (day.month.year)'"""
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return date_obj.strftime("%A (%d.%m.%Y)")

# Routes
@app.route('/')
def index():
    eaten_items, current_date = get_current_session()
    totals = calculate_totals(eaten_items)
    food_usage = get_food_usage()
    group_breakdown = calculate_group_breakdown(eaten_items)
    
    # Generate dates for the selector: 3 days before, today, and 3 days after
    dates = []
    today = datetime.now()
    for i in range(-3, 4):  # This gives [-3, -2, -1, 0, 1, 2, 3]
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
    foods = get_foods()
    food_usage = get_food_usage()
    
    # Get all foods sorted by usage (desc) then name (asc)
    all_foods = []
    for key, food in foods.items():
        usage = food_usage.get(key, 0)
        all_foods.append({
            'id': key,
            'name': food['name'],
            'calories': food['calories'],
            'serving_size': food.get('serving'),
            'half_size': food.get('half'),
            'entire_size': food.get('entire'),
            'usage': usage,
            'ean': food.get('ean'),
        })
    
    # Sort by usage (desc) then name (asc)
    all_foods.sort(key=lambda x: (-x['usage'], x['name'].lower()))
    
    # If query is empty, return top 10
    if not query:
        results = all_foods[:10]
        return jsonify(results)
    
    # Otherwise filter by query
    results = []
    for food in all_foods:
        if query in food['name'].lower() or (food['ean'] and query == str(food['ean']).strip()):
            results.append(food)
    
    return jsonify(results[:10])  # Return max 10 results

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
    date = request.form.get('date', datetime.now().strftime("%Y-%m-%d"))
    
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
    eaten_items, current_date = get_current_session(date)
    eaten_items.append(item)
    save_current_session(eaten_items, date)
    
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
    foods = get_foods()
    
    if food_id in foods:
        # Remove from foods
        del foods[food_id]
        save_foods(foods)
        
        # Remove from usage
        food_usage = get_food_usage()
        if food_id in food_usage:
            del food_usage[food_id]
            save_food_usage(food_usage)
        
        return jsonify(success=True)
    
    return jsonify(success=False, error='Food not found'), 404
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
        foods = get_foods()
        food = foods.get(item['name'].lower())
        
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