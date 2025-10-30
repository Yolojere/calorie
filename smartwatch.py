# smartwatch.py - Garmin/Smartwatch Integration Routes
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from psycopg2.extras import DictCursor
import json
import logging

# Create Blueprint
smartwatch_bp = Blueprint('smartwatch_bp', __name__, url_prefix='/garmin')

# Import from your main app (these need to be accessible)
# You'll need to pass these as dependencies or import from a shared module
def get_db_connection():
    """Import this from your main app or create shared db module"""
    from app import get_db_connection as _get_db
    return _get_db()

# Garmin client storage (shared with main app)
garmin_clients = {}

# Garmin activity type mapping
GARMIN_TO_CARDIO_MAP = {
    'running': 'Juoksu (Data)',
    'trail_running': 'Juoksu (Data)',
    'indoor_cycling': 'Sisäpyöräily (Data)',
    'cycling': 'Pyöräily (Data)',
    'walking': 'Kävely (Data)',
    'swimming': 'Uinti (Data)',
    'strength_training': None,  # Don't import strength as cardio
    'hiking': 'Vaellus (Data)',
    'elliptical': 'Crosstrainer (Data)',
    'rowing': 'Soutu (Data)',
    'yoga': None,  # Skip yoga
    'treadmill_running': 'Juoksu (Data)',
    'cardio': 'Muu Cardio',
    'indoor_cardio': 'Muu Cardio',
    'other': 'Muu Cardio'
}

# ==============================================================================
# GARMIN CONNECTION ROUTES
# ==============================================================================

@smartwatch_bp.route('/connect', methods=['POST'])
@login_required
def connect_garmin():
    """Authenticate user with Garmin and store session"""
    from garminconnect import Garmin
    
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'success': False, 'error': 'Sähköposti ja salasana vaadittu.'}), 400
    
    try:
        # Create Garmin client
        client = Garmin(email, password)
        client.login()
        
        # Get session data (tokens) for storage
        session_data = {
            'oauth1_token': getattr(client, 'oauth1_token', None),
            'oauth2_token': getattr(client, 'oauth2_token', None),
        }
        
        # Store in database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO garmin_connections (user_id, garmin_email, garmin_session_data, is_active)
            VALUES (%s, %s, %s, TRUE)
            ON CONFLICT (user_id) 
            DO UPDATE SET 
                garmin_email = EXCLUDED.garmin_email,
                garmin_session_data = EXCLUDED.garmin_session_data,
                is_active = TRUE,
                last_sync = CURRENT_TIMESTAMP
        ''', (current_user.id, email, json.dumps(session_data)))
        
        conn.commit()
        conn.close()
        
        # Store client in memory for this session
        garmin_clients[current_user.id] = client
        
        # Perform initial sync
        sync_result = sync_garmin_data_internal(client, current_user.id, days=7)
        
        return jsonify({
            'success': True, 
            'message': 'Yhdistetty garminiin onnistuneesti!',
            'synced_days': sync_result.get('synced_days', 0)
        })
        
    except Exception as e:
        print(f"Garmin connection error: {e}")
        return jsonify({'success': False, 'error': f'Failed to connect: {str(e)}'}), 401


@smartwatch_bp.route('/disconnect', methods=['POST'])
@login_required
def disconnect_garmin():
    """Disconnect Garmin account"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Mark as inactive instead of deleting (keep historical data)
        cursor.execute('''
            UPDATE garmin_connections 
            SET is_active = FALSE 
            WHERE user_id = %s
        ''', (current_user.id,))
        
        conn.commit()
        conn.close()
        
        # Remove from memory
        if current_user.id in garmin_clients:
            del garmin_clients[current_user.id]
        
        return jsonify({'success': True, 'message': 'Garmin disconnected'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@smartwatch_bp.route('/status', methods=['GET'])
@login_required
def garmin_status():
    """Check if user has Garmin connected"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        cursor.execute('''
            SELECT garmin_email, last_sync, is_active 
            FROM garmin_connections 
            WHERE user_id = %s
        ''', (current_user.id,))
        
        connection = cursor.fetchone()
        conn.close()
        
        if connection and connection['is_active']:
            return jsonify({
                'connected': True,
                'email': connection['garmin_email'],
                'last_sync': connection['last_sync'].isoformat() if connection['last_sync'] else None
            })
        else:
            return jsonify({'connected': False})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==============================================================================
# GARMIN SYNC ROUTES
# ==============================================================================

@smartwatch_bp.route('/sync', methods=['POST'])
@login_required
def sync_garmin_data():
    """Manually trigger Garmin data sync with optional auto-import"""
    try:
        days = int(request.form.get('days', 7))
        
        # Get or create client
        client = get_or_create_garmin_client(current_user.id)
        
        if not client:
            return jsonify({
                'success': False, 
                'error': 'Garmin yhteys vanhentunut. Ole hyvä ja yhdistä uudelleen.',
                'needs_reconnect': True
            }), 401
        
        # Perform sync
        result = sync_garmin_data_internal(client, current_user.id, days)
        
        if result['success']:
            # Check if auto-import is enabled
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            try:
                cursor.execute('''
                    SELECT auto_import_garmin_cardio 
                    FROM users 
                    WHERE id = %s
                ''', (current_user.id,))
                
                user_settings = cursor.fetchone()
                auto_import = user_settings.get('auto_import_garmin_cardio', False) if user_settings else False
                
                if auto_import:
                    # Get recently synced activities that haven't been imported
                    cursor.execute('''
                        SELECT * FROM garmin_activities 
                        WHERE user_id = %s 
                        AND synced_at > NOW() - INTERVAL '5 minutes'
                        ORDER BY date DESC
                    ''', (current_user.id,))
                    
                    recent_activities = cursor.fetchall()
                    
                    # Import each activity
                    imported_count = 0
                    for activity in recent_activities:
                        import_result = import_garmin_activity_as_cardio(dict(activity), current_user.id)
                        if import_result['success']:
                            imported_count += 1
                    
                    result['auto_imported'] = imported_count
                else:
                    result['auto_imported'] = 0
                    
            finally:
                conn.close()
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Sync error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': 'Synkronointi epäonnistui. Yritä uudelleen myöhemmin.',
            'needs_reconnect': True
        }), 500


@smartwatch_bp.route('/activities', methods=['GET'])
@login_required
def get_garmin_activities():
    """Get Garmin activities for date range"""
    start_date = request.args.get('start_date', 
                                  (date.today() - timedelta(days=7)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', date.today().strftime('%Y-%m-%d'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        cursor.execute('''
            SELECT * FROM garmin_activities 
            WHERE user_id = %s AND date BETWEEN %s AND %s
            ORDER BY start_time DESC
        ''', (current_user.id, start_date, end_date))
        
        activities = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'activities': [dict(a) for a in activities]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==============================================================================
# GARMIN IMPORT ROUTES
# ==============================================================================

@smartwatch_bp.route('/importable-activities', methods=['GET'])
@login_required
def get_importable_activities():
    """Get Garmin activities that can be imported as cardio"""
    try:
        start_date = request.args.get('start_date', (date.today() - timedelta(days=7)).strftime('%Y-%m-%d'))
        end_date = request.args.get('end_date', date.today().strftime('%Y-%m-%d'))
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        # Get Garmin activities
        cursor.execute("""
            SELECT ga.activity_id, ga.activity_name, ga.activity_type, 
                   ga.date, ga.duration_seconds, ga.distance_meters, 
                   ga.calories, ga.avg_hr, ga.start_time
            FROM garmin_activities ga
            WHERE ga.user_id = %s 
            AND ga.date BETWEEN %s AND %s
            ORDER BY ga.date DESC, ga.start_time DESC
        """, (current_user.id, start_date, end_date))
        
        activities = cursor.fetchall()
        
        importable = []
        for activity_dict in activities:
            # Check if activity type is importable
            if activity_dict['activity_type'] not in GARMIN_TO_CARDIO_MAP:
                continue
            
            cardio_name = GARMIN_TO_CARDIO_MAP[activity_dict['activity_type']]
            if cardio_name is None:
                continue
            
            # Check if already imported
            cursor.execute("""
                SELECT cs.id 
                FROM cardio_sessions cs
                JOIN workout_sessions ws ON cs.session_id = ws.id
                WHERE ws.user_id = %s 
                AND cs.garmin_activity_id = %s
            """, (current_user.id, str(activity_dict['activity_id'])))
            
            already_imported_by_id = cursor.fetchone() is not None
            
            # Method 2: By notes (fallback for old imports)
            cursor.execute("""
                SELECT cs.id 
                FROM cardio_sessions cs
                JOIN workout_sessions ws ON cs.session_id = ws.id
                WHERE ws.user_id = %s 
                AND ws.date = %s 
                AND cs.notes LIKE %s
            """, (current_user.id, activity_dict['date'], 
                  f'%Garmin Activity ID: {activity_dict["activity_id"]}%'))
            
            already_imported_by_notes = cursor.fetchone() is not None
            
            already_imported = already_imported_by_id or already_imported_by_notes
            
            importable.append({
                'activity_id': activity_dict['activity_id'],
                'activity_name': activity_dict['activity_name'],
                'activity_type': activity_dict['activity_type'],
                'date': activity_dict['date'].strftime('%Y-%m-%d'),
                'duration_minutes': round(activity_dict['duration_seconds'] / 60.0, 1),
                'distance_km': round(activity_dict['distance_meters'] / 1000.0, 2) if activity_dict['distance_meters'] else None,
                'calories': activity_dict['calories'],
                'avg_hr': activity_dict['avg_hr'],
                'mapped_cardio_name': cardio_name,
                'already_imported': already_imported
            })
        
        conn.close()
        return jsonify({'success': True, 'activities': importable})
        
    except Exception as e:
        print(f'Error getting importable activities: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@smartwatch_bp.route('/import-activity', methods=['POST'])
@login_required
def import_single_activity():
    """Import a specific Garmin activity as cardio"""
    try:
        activity_id = request.form.get('activity_id')
        
        if not activity_id:
            return jsonify({'success': False, 'error': 'Activity ID required'}), 400
        
        # Get activity from database
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        cursor.execute('''
            SELECT * FROM garmin_activities 
            WHERE user_id = %s AND activity_id = %s
        ''', (current_user.id, activity_id))
        
        activity = cursor.fetchone()
        conn.close()
        
        if not activity:
            return jsonify({'success': False, 'error': 'Activity not found'}), 404
        
        # Import the activity
        result = import_garmin_activity_as_cardio(dict(activity), current_user.id)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error importing activity: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@smartwatch_bp.route('/import-activities-bulk', methods=['POST'])
@login_required
def import_activities_bulk():
    """Import multiple Garmin activities to workout log as cardio sessions"""
    try:
        data = request.get_json()
        activity_ids = data.get('activity_ids', [])
        
        if not activity_ids:
            return jsonify({'success': False, 'error': 'No activity IDs provided'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        imported_count = 0
        failed_count = 0
        failed_activities = []
        
        for activity_id in activity_ids:
            try:
                # Get activity from garmin_activities table
                cursor.execute('''
                    SELECT * FROM garmin_activities 
                    WHERE user_id = %s AND activity_id = %s
                ''', (current_user.id, activity_id))
                
                garmin_activity = cursor.fetchone()
                
                if not garmin_activity:
                    failed_count += 1
                    failed_activities.append({
                        'activity_id': activity_id,
                        'error': 'Activity not found'
                    })
                    continue
                
                # Use the fixed import function
                import_result = import_garmin_activity_as_cardio(dict(garmin_activity), current_user.id)
                
                if import_result['success']:
                    imported_count += 1
                else:
                    failed_count += 1
                    failed_activities.append({
                        'activity_id': activity_id,
                        'error': import_result.get('reason', 'Unknown error')
                    })
                    
            except Exception as e:
                conn.rollback()
                failed_count += 1
                failed_activities.append({
                    'activity_id': activity_id,
                    'error': str(e)
                })
                print(f"Error importing activity {activity_id}: {e}")
                continue
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'imported_count': imported_count,
            'failed_count': failed_count,
            'failed_activities': failed_activities
        })
        
    except Exception as e:
        print(f"Error in bulk import: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@smartwatch_bp.route('/toggle-auto-import', methods=['POST'])
@login_required
def toggle_auto_import():
    """Toggle automatic import of cardio sessions during Garmin sync"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', True)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET auto_import_garmin_cardio = %s 
            WHERE id = %s
        ''', (enabled, current_user.id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'enabled': enabled,
            'message': 'Auto-import asetukset päivitetty'
        })
        
    except Exception as e:
        print(f"Error toggling auto-import: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@smartwatch_bp.route('/auto-import-status', methods=['GET'])
@login_required
def get_auto_import_status():
    """Get current auto-import preference"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        cursor.execute('''
            SELECT auto_import_garmin_cardio 
            FROM users 
            WHERE id = %s
        ''', (current_user.id,))
        
        user = cursor.fetchone()
        conn.close()
        
        enabled = user.get('auto_import_garmin_cardio', True) if user else True
        
        return jsonify({
            'success': True,
            'enabled': enabled
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def get_or_create_garmin_client(user_id):
    """Get existing client or create new one from stored session"""
    from garminconnect import Garmin
    
    # Check memory cache first
    if user_id in garmin_clients:
        try:
            client = garmin_clients[user_id]
            # Quick validation - try to get today's stats
            client.get_stats(date.today().strftime('%Y-%m-%d'))
            return client
        except Exception as e:
            logging.warning(f"Cached Garmin client expired for user {user_id}: {e}")
            # Remove expired client
            del garmin_clients[user_id]
    
    # Try to restore from database session data
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        cursor.execute('''
            SELECT garmin_email, garmin_session_data
            FROM garmin_connections
            WHERE user_id = %s AND is_active = TRUE
        ''', (user_id,))
        
        connection = cursor.fetchone()
        conn.close()
        
        if not connection:
            return None
        
        # Note: garminconnect library doesn't support session restoration
        # Users will need to re-authenticate when sessions expire
        logging.info(f"No valid session for user {user_id} - re-authentication required")
        return None
        
    except Exception as e:
        logging.error(f"Error restoring Garmin session for user {user_id}: {e}")
        return None


def sync_garmin_data_internal(client, user_id, days=7):
    """Internal function to sync Garmin data to database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    synced_days = 0
    synced_activities = 0
    
    try:
        print(f"\n=== STARTING SYNC FOR USER {user_id} - {days} DAYS ===")
        
        for i in range(days):
            date_obj = date.today() - timedelta(days=i)
            date_str = date_obj.strftime('%Y-%m-%d')
            
            try:
                print(f"\n--- Syncing date: {date_str} ---")
                
                # Get daily stats
                stats = client.get_stats(date_str)
                
                # Try to get heart rate
                try:
                    heart_rate = client.get_heart_rates(date_str)
                    resting_hr = heart_rate.get('restingHeartRate')
                    max_hr = heart_rate.get('maxHeartRate')
                    avg_hr = heart_rate.get('averageHeartRate')
                except Exception:
                    resting_hr = None
                    max_hr = None
                    avg_hr = None
                
                # Extract values from stats
                steps = stats.get('totalSteps', 0)
                total_cals = stats.get('totalKilocalories', 0)
                active_cals = stats.get('activeKilocalories', 0)
                distance = stats.get('totalDistanceMeters', 0)
                floors = stats.get('floorsAscended', 0)
                
                # Get heart rate from stats if not from get_heart_rates
                if resting_hr is None:
                    resting_hr = stats.get('restingHeartRate')
                if max_hr is None:
                    max_hr = stats.get('maxHeartRate')
                
                # Insert/update daily data
                cursor.execute("""
                    INSERT INTO garmin_daily_data 
                    (user_id, date, steps, calories_total, calories_active, 
                     distance_meters, floors_climbed, resting_hr, max_hr, avg_hr)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, date) 
                    DO UPDATE SET 
                        steps = EXCLUDED.steps,
                        calories_total = EXCLUDED.calories_total,
                        calories_active = EXCLUDED.calories_active,
                        distance_meters = EXCLUDED.distance_meters,
                        floors_climbed = EXCLUDED.floors_climbed,
                        resting_hr = EXCLUDED.resting_hr,
                        max_hr = EXCLUDED.max_hr,
                        avg_hr = EXCLUDED.avg_hr,
                        synced_at = CURRENT_TIMESTAMP
                """, (
                    user_id, 
                    date_str,
                    steps,
                    total_cals,
                    active_cals,
                    distance,
                    floors,
                    resting_hr,
                    max_hr,
                    avg_hr
                ))
                
                synced_days += 1
                
            except Exception as e:
                print(f"✗ Error syncing date {date_str}: {e}")
                continue
        
        # Sync recent activities
        try:
            activities = client.get_activities(0, 20)  # Last 20 activities
            
            for activity in activities:
                try:
                    # Parse start time
                    start_time_str = activity.get('startTimeLocal', '')
                    if start_time_str:
                        if 'Z' in start_time_str or '+' in start_time_str:
                            activity_date = datetime.fromisoformat(
                                start_time_str.replace('Z', '+00:00')
                            ).date()
                        else:
                            activity_date = datetime.strptime(
                                start_time_str.split('.')[0], '%Y-%m-%d %H:%M:%S'
                            ).date()
                    else:
                        activity_date = date.today()
                    
                    # Handle activityType
                    activity_type_raw = activity.get('activityType')
                    if isinstance(activity_type_raw, dict):
                        activity_type = activity_type_raw.get('typeKey')
                    else:
                        activity_type = activity_type_raw
                    
                    cursor.execute("""
                        INSERT INTO garmin_activities 
                        (user_id, activity_id, activity_name, activity_type, start_time,
                         duration_seconds, distance_meters, calories, avg_hr, max_hr, date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_id, activity_id) 
                        DO UPDATE SET
                            activity_name = EXCLUDED.activity_name,
                            duration_seconds = EXCLUDED.duration_seconds,
                            calories = EXCLUDED.calories,
                            synced_at = CURRENT_TIMESTAMP
                    """, (
                        user_id,
                        activity.get('activityId'),
                        activity.get('activityName'),
                        activity_type,
                        start_time_str if start_time_str else None,
                        activity.get('duration'),
                        activity.get('distance'),
                        activity.get('calories'),
                        activity.get('averageHR'),
                        activity.get('maxHeartRate'),
                        activity_date
                    ))
                    
                    synced_activities += 1
                    
                except Exception as e:
                    print(f"Error syncing activity: {e}")
                    continue
                
        except Exception as e:
            print(f"✗ Error fetching activities: {e}")
        
        # Update last sync time
        cursor.execute('''
            UPDATE garmin_connections 
            SET last_sync = CURRENT_TIMESTAMP 
            WHERE user_id = %s
        ''', (user_id,))
        
        conn.commit()
        
        return {
            'success': True,
            'synced_days': synced_days,
            'synced_activities': synced_activities
        }
        
    except Exception as e:
        conn.rollback()
        print(f"✗ MAJOR SYNC ERROR: {e}")
        return {'success': False, 'error': str(e)}
        
    finally:
        cursor.close()
        conn.close()


def get_cardio_exercise_by_name(name):
    """Get cardio exercise from database by name"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute("SELECT * FROM cardio_exercises WHERE name = %s", (name,))
    exercise = cursor.fetchone()
    conn.close()
    return dict(exercise) if exercise else None


def import_garmin_activity_as_cardio(activity, user_id):
    """
    Import a Garmin activity as a cardio session
    Uses the same unsaved session logic as manual cardio additions
    """
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    
    try:
        activity_id = activity['activity_id']
        activity_name = activity['activity_name']
        activity_type = activity['activity_type']
        
        # Check if activity type should be imported
        cardio_name = GARMIN_TO_CARDIO_MAP.get(activity_type)
        if cardio_name is None:
            return {
                'success': False, 
                'reason': f'Activity type {activity_type} not configured for import'
            }
        
        # Get corresponding cardio exercise
        cardio_exercise = get_cardio_exercise_by_name(cardio_name)
        if not cardio_exercise:
            return {'success': False, 'reason': f'Cardio exercise {cardio_name} not found'}
        
        cardio_exercise_id = cardio_exercise['id']
        
        # Extract activity data
        duration_minutes = round(activity['duration_seconds'] / 60.0, 1) if activity.get('duration_seconds') else 0
        distance_km = round(activity['distance_meters'] / 1000.0, 2) if activity.get('distance_meters') else None
        avg_hr = activity.get('avg_hr')
        max_hr = activity.get('max_hr')
        calories_burned = activity.get('calories', 0)
        
        # Calculate pace if distance available
        avg_pace_min_per_km = None
        if distance_km and distance_km > 0 and duration_minutes > 0:
            avg_pace_min_per_km = round(duration_minutes / distance_km, 2)
        
        # Get activity date
        activity_date = activity['date']
        if isinstance(activity_date, str):
            activity_date = datetime.strptime(activity_date, '%Y-%m-%d').date()
        
        # Find or create unsaved workout session for this date
        cursor.execute("""
            SELECT id FROM workout_sessions 
            WHERE user_id = %s AND date = %s AND is_saved = false
            ORDER BY id DESC LIMIT 1
        """, (user_id, activity_date))
        
        session_result = cursor.fetchone()
        
        if session_result:
            session_id = session_result['id']
        else:
            # Create new unsaved session
            cursor.execute("""
                INSERT INTO workout_sessions (user_id, date, muscle_group, is_saved, workout_type)
                VALUES (%s, %s, 'cardio', false, 'cardio')
                RETURNING id
            """, (user_id, activity_date))
            session_id = cursor.fetchone()['id']
        
        # Create notes with Garmin activity ID
        notes = f"Imported from Garmin: {activity_name} (ID: {activity_id})"
        
        # Insert cardio session
        cursor.execute("""
            INSERT INTO cardio_sessions 
            (session_id, cardio_exercise_id, duration_minutes, distance_km, 
             avg_pace_min_per_km, avg_heart_rate, max_heart_rate, calories_burned, 
             notes, garmin_activity_id, is_saved, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, NOW())
            RETURNING id
        """, (
            session_id,
            cardio_exercise_id,
            duration_minutes,
            distance_km,
            avg_pace_min_per_km,
            avg_hr,
            max_hr,
            calories_burned,
            notes,
            activity_id
        ))
        
        cardio_session_id = cursor.fetchone()['id']
        conn.commit()
        
        return {
            'success': True,
            'cardio_session_id': cardio_session_id,
            'session_id': session_id,
            'activity_name': activity_name,
            'calories_burned': round(calories_burned, 1),
            'duration_minutes': round(duration_minutes, 1),
            'activity_id': activity_id,
            'date': activity_date.strftime('%Y-%m-%d')
        }
        
    except Exception as e:
        conn.rollback()
        print(f"Error importing Garmin activity: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'reason': str(e)}
        
    finally:
        cursor.close()
        conn.close()


def auto_sync_all_garmin_users():
    """
    Background job that automatically syncs Garmin data for all connected users
    AND auto-imports cardio activities to workout log
    """
    logging.info("Starting automatic Garmin sync for all users...")
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)
    
    try:
        # Get all active Garmin connections with auto-import preference
        cursor.execute("""
            SELECT gc.user_id, gc.garmin_email, u.username, gc.last_sync,
                   u.garmin_sync_interval, u.auto_import_garmin_cardio
            FROM garmin_connections gc
            JOIN users u ON gc.user_id = u.id
            WHERE gc.is_active = TRUE
        """)
        
        active_connections = cursor.fetchall()
        
        if not active_connections:
            logging.info("No active Garmin connections found.")
            return
        
        logging.info(f"Found {len(active_connections)} active Garmin connections")
        
        synced_count = 0
        failed_count = 0
        total_imported = 0
        
        for connection in active_connections:
            user_id = connection['user_id']
            username = connection['username']
            last_sync = connection['last_sync']
            sync_interval = connection.get('garmin_sync_interval', 60)  # Default 60 minutes
            auto_import_enabled = connection.get('auto_import_garmin_cardio', True)
            
            # Get or create Garmin client
            client = get_or_create_garmin_client(user_id)
            
            if not client:
                logging.warning(f"No valid Garmin session for {username} - attempting to reconnect")
                client = reconnect_garmin_user(user_id)
                
                if not client:
                    logging.error(f"Failed to reconnect {username} - user needs to re-authenticate")
                    failed_count += 1
                    continue
            
            # Sync data
            result = sync_garmin_data_internal(client, user_id, days=2)
            
            if result['success']:
                synced_count += 1
                logging.info(f"✓ Synced {username}: {result['synced_days']} days, {result['synced_activities']} activities")
                
                # Auto-import if enabled
                if auto_import_enabled:
                    try:
                        cursor.execute("""
                            SELECT * FROM garmin_activities 
                            WHERE user_id = %s 
                            AND synced_at > NOW() - INTERVAL '2 days'
                            ORDER BY date DESC
                        """, (user_id,))
                        
                        recent_activities = cursor.fetchall()
                        
                        imported_count = 0
                        for activity in recent_activities:
                            try:
                                import_result = import_garmin_activity_as_cardio(dict(activity), user_id)
                                if import_result['success']:
                                    imported_count += 1
                                    logging.info(f"  ✓ Imported {import_result['activity_name']} ({import_result['calories_burned']} cal)")
                                else:
                                    logging.debug(f"  ⊘ Skipped: {import_result.get('reason', 'Unknown')}")
                            except Exception as e:
                                logging.error(f"  ✗ Error importing activity: {e}")
                                continue
                        
                        total_imported += imported_count
                        logging.info(f"  Auto-imported {imported_count} activities for {username}")
                        
                    except Exception as e:
                        logging.error(f"Error during auto-import for {username}: {e}")
            else:
                logging.error(f"Sync failed for {username}: {result.get('error', 'Unknown error')}")
                failed_count += 1
                
        logging.info(f"Auto-sync complete: {synced_count} successful, {failed_count} failed, {total_imported} activities imported")
        
    except Exception as e:
        logging.error(f"Critical error in auto_sync_all_garmin_users: {e}")
        import traceback
        traceback.printexc()
        
    finally:
        cursor.close()
        conn.close()


def reconnect_garmin_user(user_id):
    """
    Attempt to reconnect a user whose Garmin session has expired
    Note: This will only work if you're storing encrypted credentials
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        cursor.execute('''
            SELECT garmin_email, garmin_session_data 
            FROM garmin_connections 
            WHERE user_id = %s AND is_active = TRUE
        ''', (user_id,))
        
        connection = cursor.fetchone()
        conn.close()
        
        if not connection:
            return None
        
        # Try to restore session using tokens (may not work)
        logging.warning("Session restoration not fully implemented - user may need to re-authenticate")
        return None
        
    except Exception as e:
        logging.error(f"Error reconnecting user {user_id}: {e}")
        return None
