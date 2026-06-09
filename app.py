import math
import os
from flask import Flask, jsonify, request, render_template, session
from functools import wraps
import db

app = Flask(__name__)
app.secret_key = os.environ.get('NUTRIQUANT_SECRET_KEY', 'dev-only-change-me')
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('NUTRIQUANT_COOKIE_SECURE', '').lower() == 'true'
)

PLAN_FEATURES = {
    "free": {
        "label": "Free",
        "price": 0,
        "features": [
            "Nutrition calculator",
            "Daily calorie and macro targets",
            "Basic weight tracking"
        ],
        "limits": {
            "coach_messaging": False,
            "custom_targets": False,
            "team_console": False
        }
    },
    "premium": {
        "label": "Premium",
        "price": 29,
        "features": [
            "Daily food, water, and exercise logs",
            "Coach notes and custom target overrides",
            "Progress dashboards"
        ],
        "limits": {
            "coach_messaging": True,
            "custom_targets": True,
            "team_console": False
        }
    },
    "enterprise": {
        "label": "Enterprise",
        "price": 99,
        "features": [
            "Coach/admin client console",
            "Subscription and audit analytics",
            "Managed food database"
        ],
        "limits": {
            "coach_messaging": True,
            "custom_targets": True,
            "team_console": True
        }
    }
}

# Initialise database on startup
db.init_db()

# -------------------------------------------------------------
# Auth Access Decorators
# -------------------------------------------------------------
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        user = db.get_user_by_id(session['user_id'])
        if not user or not user.get('is_admin'):
            return jsonify({"error": "Forbidden: Admin access required."}), 403
        return f(*args, **kwargs)
    return decorated_function

def public_user_payload(user):
    """Return non-sensitive user data with plan metadata for the client UI."""
    payload = dict(user)
    payload.pop('password_hash', None)
    payload['is_admin'] = bool(payload.get('is_admin', 0))
    tier = (payload.get('subscription_tier') or 'free').lower()
    if tier not in PLAN_FEATURES:
        tier = 'free'
    payload['subscription_tier'] = tier
    payload['plan'] = PLAN_FEATURES[tier]
    return payload

def get_micronutrients(age, gender):
    """
    Returns exact FDA/NIH RDA values for essential vitamins and minerals based on age and gender.
    """
    if age <= 3:
        return {
            "Vitamin A": {"value": 300, "unit": "mcg RAE", "desc": "Supports healthy vision, immune system, and skin development.", "sources": "Carrots, sweet potatoes, spinach, squash"},
            "Vitamin C": {"value": 15, "unit": "mg", "desc": "Acts as an antioxidant, aids iron absorption, and builds collagen.", "sources": "Citrus fruits, strawberries, bell peppers, broccoli"},
            "Vitamin D": {"value": 15, "unit": "mcg (600 IU)", "desc": "Maintains strong bone structure and boosts immune defense.", "sources": "Fortified milk, salmon, egg yolks, direct sunlight"},
            "Vitamin B12": {"value": 0.9, "unit": "mcg", "desc": "Crucial for red blood cell synthesis and neurological functions.", "sources": "Beef, poultry, fish, eggs, fortified plant milk"},
            "Folate (B9)": {"value": 150, "unit": "mcg DFE", "desc": "Essential for cellular division and DNA synthesis.", "sources": "Leafy greens, lentils, chickpeas, asparagus"},
            "Calcium": {"value": 700, "unit": "mg", "desc": "Essential for developing dense, strong bones and teeth.", "sources": "Milk, cheese, yogurt, fortified juices, kale"},
            "Iron": {"value": 7, "unit": "mg", "desc": "Transports oxygen in blood via hemoglobin; prevents anemia.", "sources": "Red meat, beans, lentils, dark poultry, spinach"},
            "Magnesium": {"value": 80, "unit": "mg", "desc": "Regulates muscle contractions, nerve signals, and blood sugar.", "sources": "Almonds, pumpkin seeds, spinach, dark chocolate"},
            "Zinc": {"value": 3, "unit": "mg", "desc": "Supports immune health, wound recovery, and protein synthesis.", "sources": "Beef, chickpeas, lentils, pumpkin seeds, cashews"}
        }
    elif age <= 8:
        return {
            "Vitamin A": {"value": 400, "unit": "mcg RAE", "desc": "Supports healthy vision, immune system, and skin development.", "sources": "Carrots, sweet potatoes, spinach, squash"},
            "Vitamin C": {"value": 25, "unit": "mg", "desc": "Acts as an antioxidant, aids iron absorption, and builds collagen.", "sources": "Citrus fruits, strawberries, bell peppers, broccoli"},
            "Vitamin D": {"value": 15, "unit": "mcg (600 IU)", "desc": "Maintains strong bone structure and boosts immune defense.", "sources": "Fortified milk, salmon, egg yolks, direct sunlight"},
            "Vitamin B12": {"value": 1.2, "unit": "mcg", "desc": "Crucial for red blood cell synthesis and neurological functions.", "sources": "Beef, poultry, fish, eggs, fortified plant milk"},
            "Folate (B9)": {"value": 200, "unit": "mcg DFE", "desc": "Essential for cellular division and DNA synthesis.", "sources": "Leafy greens, lentils, chickpeas, asparagus"},
            "Calcium": {"value": 1000, "unit": "mg", "desc": "Essential for developing dense, strong bones and teeth.", "sources": "Milk, cheese, yogurt, fortified juices, kale"},
            "Iron": {"value": 10, "unit": "mg", "desc": "Transports oxygen in blood via hemoglobin; prevents anemia.", "sources": "Red meat, beans, lentils, dark poultry, spinach"},
            "Magnesium": {"value": 130, "unit": "mg", "desc": "Regulates muscle contractions, nerve signals, and blood sugar.", "sources": "Almonds, pumpkin seeds, spinach, dark chocolate"},
            "Zinc": {"value": 5, "unit": "mg", "desc": "Supports immune health, wound recovery, and protein synthesis.", "sources": "Beef, chickpeas, lentils, pumpkin seeds, cashews"}
        }
    elif age <= 13:
        return {
            "Vitamin A": {"value": 600, "unit": "mcg RAE", "desc": "Supports healthy vision, immune system, and skin development.", "sources": "Carrots, sweet potatoes, spinach, squash"},
            "Vitamin C": {"value": 45, "unit": "mg", "desc": "Acts as an antioxidant, aids iron absorption, and builds collagen.", "sources": "Citrus fruits, strawberries, bell peppers, broccoli"},
            "Vitamin D": {"value": 15, "unit": "mcg (600 IU)", "desc": "Maintains strong bone structure and boosts immune defense.", "sources": "Fortified milk, salmon, egg yolks, direct sunlight"},
            "Vitamin B12": {"value": 1.8, "unit": "mcg", "desc": "Crucial for red blood cell synthesis and neurological functions.", "sources": "Beef, poultry, fish, eggs, fortified plant milk"},
            "Folate (B9)": {"value": 300, "unit": "mcg DFE", "desc": "Essential for cellular division and DNA synthesis.", "sources": "Leafy greens, lentils, chickpeas, asparagus"},
            "Calcium": {"value": 1300, "unit": "mg", "desc": "Essential for developing dense, strong bones and teeth.", "sources": "Milk, cheese, yogurt, fortified juices, kale"},
            "Iron": {"value": 8, "unit": "mg", "desc": "Transports oxygen in blood via hemoglobin; prevents anemia.", "sources": "Red meat, beans, lentils, dark poultry, spinach"},
            "Magnesium": {"value": 240, "unit": "mg", "desc": "Regulates muscle contractions, nerve signals, and blood sugar.", "sources": "Almonds, pumpkin seeds, spinach, dark chocolate"},
            "Zinc": {"value": 8, "unit": "mg", "desc": "Supports immune health, wound recovery, and protein synthesis.", "sources": "Beef, chickpeas, lentils, pumpkin seeds, cashews"}
        }
    elif age <= 18:
        iron_val = 15 if gender == 'female' else 11
        mag_val = 360 if gender == 'female' else 410
        zinc_val = 9 if gender == 'female' else 11
        vit_a_val = 700 if gender == 'female' else 900
        vit_c_val = 65 if gender == 'female' else 75
        return {
            "Vitamin A": {"value": vit_a_val, "unit": "mcg RAE", "desc": "Supports healthy vision, immune system, and skin development.", "sources": "Carrots, sweet potatoes, spinach, squash"},
            "Vitamin C": {"value": vit_c_val, "unit": "mg", "desc": "Acts as an antioxidant, aids iron absorption, and builds collagen.", "sources": "Citrus fruits, strawberries, bell peppers, broccoli"},
            "Vitamin D": {"value": 15, "unit": "mcg (600 IU)", "desc": "Maintains strong bone structure and boosts immune defense.", "sources": "Fortified milk, salmon, egg yolks, direct sunlight"},
            "Vitamin B12": {"value": 2.4, "unit": "mcg", "desc": "Crucial for red blood cell synthesis and neurological functions.", "sources": "Beef, poultry, fish, eggs, fortified plant milk"},
            "Folate (B9)": {"value": 400, "unit": "mcg DFE", "desc": "Essential for cellular division and DNA synthesis.", "sources": "Leafy greens, lentils, chickpeas, asparagus"},
            "Calcium": {"value": 1300, "unit": "mg", "desc": "Essential for developing dense, strong bones and teeth.", "sources": "Milk, cheese, yogurt, fortified juices, kale"},
            "Iron": {"value": iron_val, "unit": "mg", "desc": "Transports oxygen in blood via hemoglobin; prevents anemia.", "sources": "Red meat, beans, lentils, dark poultry, spinach"},
            "Magnesium": {"value": mag_val, "unit": "mg", "desc": "Regulates muscle contractions, nerve signals, and blood sugar.", "sources": "Almonds, pumpkin seeds, spinach, dark chocolate"},
            "Zinc": {"value": zinc_val, "unit": "mg", "desc": "Supports immune health, wound recovery, and protein synthesis.", "sources": "Beef, chickpeas, lentils, pumpkin seeds, cashews"}
        }
    elif age <= 50:
        iron_val = 18 if gender == 'female' else 8
        mag_val = 310 if gender == 'female' else 400
        zinc_val = 8 if gender == 'female' else 11
        vit_a_val = 700 if gender == 'female' else 900
        vit_c_val = 75 if gender == 'female' else 90
        return {
            "Vitamin A": {"value": vit_a_val, "unit": "mcg RAE", "desc": "Supports healthy vision, immune system, and skin health.", "sources": "Carrots, sweet potatoes, spinach, squash"},
            "Vitamin C": {"value": vit_c_val, "unit": "mg", "desc": "Acts as an antioxidant, aids iron absorption, and builds collagen.", "sources": "Citrus fruits, strawberries, bell peppers, broccoli"},
            "Vitamin D": {"value": 15, "unit": "mcg (600 IU)", "desc": "Maintains strong bone structure and boosts immune defense.", "sources": "Fortified milk, salmon, egg yolks, direct sunlight"},
            "Vitamin B12": {"value": 2.4, "unit": "mcg", "desc": "Crucial for red blood cell synthesis and neurological functions.", "sources": "Beef, poultry, fish, eggs, fortified plant milk"},
            "Folate (B9)": {"value": 400, "unit": "mcg DFE", "desc": "Essential for cellular division and DNA synthesis.", "sources": "Leafy greens, lentils, chickpeas, asparagus"},
            "Calcium": {"value": 1000, "unit": "mg", "desc": "Essential for developing dense, strong bones and teeth.", "sources": "Milk, cheese, yogurt, fortified juices, kale"},
            "Iron": {"value": iron_val, "unit": "mg", "desc": "Transports oxygen in blood via hemoglobin; prevents anemia.", "sources": "Red meat, beans, lentils, dark poultry, spinach"},
            "Magnesium": {"value": mag_val, "unit": "mg", "desc": "Regulates muscle contractions, nerve signals, and blood sugar.", "sources": "Almonds, pumpkin seeds, spinach, dark chocolate"},
            "Zinc": {"value": zinc_val, "unit": "mg", "desc": "Supports immune health, wound recovery, and protein synthesis.", "sources": "Beef, chickpeas, lentils, pumpkin seeds, cashews"}
        }
    elif age <= 70:
        iron_val = 8
        mag_val = 320 if gender == 'female' else 420
        zinc_val = 8 if gender == 'female' else 11
        vit_a_val = 700 if gender == 'female' else 900
        vit_c_val = 75 if gender == 'female' else 90
        calcium_val = 1200 if gender == 'female' else 1000
        return {
            "Vitamin A": {"value": vit_a_val, "unit": "mcg RAE", "desc": "Supports healthy vision, immune system, and skin health.", "sources": "Carrots, sweet potatoes, spinach, squash"},
            "Vitamin C": {"value": vit_c_val, "unit": "mg", "desc": "Acts as an antioxidant, aids iron absorption, and builds collagen.", "sources": "Citrus fruits, strawberries, bell peppers, broccoli"},
            "Vitamin D": {"value": 15, "unit": "mcg (600 IU)", "desc": "Maintains strong bone structure and boosts immune defense.", "sources": "Fortified milk, salmon, egg yolks, direct sunlight"},
            "Vitamin B12": {"value": 2.4, "unit": "mcg", "desc": "Crucial for red blood cell synthesis and neurological functions.", "sources": "Beef, poultry, fish, eggs, fortified plant milk"},
            "Folate (B9)": {"value": 400, "unit": "mcg DFE", "desc": "Essential for cellular division and DNA synthesis.", "sources": "Leafy greens, lentils, chickpeas, asparagus"},
            "Calcium": {"value": calcium_val, "unit": "mg", "desc": "Essential for maintaining bone density and preventing osteoporosis.", "sources": "Milk, cheese, yogurt, fortified juices, kale"},
            "Iron": {"value": iron_val, "unit": "mg", "desc": "Transports oxygen in blood via hemoglobin; prevents anemia.", "sources": "Red meat, beans, lentils, dark poultry, spinach"},
            "Magnesium": {"value": mag_val, "unit": "mg", "desc": "Regulates muscle contractions, nerve signals, and blood sugar.", "sources": "Almonds, pumpkin seeds, spinach, dark chocolate"},
            "Zinc": {"value": zinc_val, "unit": "mg", "desc": "Supports immune health, wound recovery, and protein synthesis.", "sources": "Beef, chickpeas, lentils, pumpkin seeds, cashews"}
        }
    else:  # 70+
        iron_val = 8
        mag_val = 320 if gender == 'female' else 420
        zinc_val = 8 if gender == 'female' else 11
        vit_a_val = 700 if gender == 'female' else 900
        vit_c_val = 75 if gender == 'female' else 90
        return {
            "Vitamin A": {"value": vit_a_val, "unit": "mcg RAE", "desc": "Supports healthy vision, immune system, and skin health.", "sources": "Carrots, sweet potatoes, spinach, squash"},
            "Vitamin C": {"value": vit_c_val, "unit": "mg", "desc": "Acts as an antioxidant, aids iron absorption, and builds collagen.", "sources": "Citrus fruits, strawberries, bell peppers, broccoli"},
            "Vitamin D": {"value": 20, "unit": "mcg (800 IU)", "desc": "Promotes calcium absorption; increased dose protects aging bone structure.", "sources": "Fatty fish, fortified milk, egg yolks, direct sunlight"},
            "Vitamin B12": {"value": 2.4, "unit": "mcg", "desc": "Crucial for red blood cell synthesis and neurological functions.", "sources": "Beef, poultry, fish, eggs, fortified plant milk"},
            "Folate (B9)": {"value": 400, "unit": "mcg DFE", "desc": "Essential for cellular division and DNA synthesis.", "sources": "Leafy greens, lentils, chickpeas, asparagus"},
            "Calcium": {"value": 1200, "unit": "mg", "desc": "Essential for maintaining bone density and preventing osteoporosis.", "sources": "Milk, cheese, yogurt, fortified juices, kale"},
            "Iron": {"value": iron_val, "unit": "mg", "desc": "Transports oxygen in blood via hemoglobin; prevents anemia.", "sources": "Red meat, beans, lentils, dark poultry, spinach"},
            "Magnesium": {"value": mag_val, "unit": "mg", "desc": "Regulates muscle contractions, nerve signals, and blood sugar.", "sources": "Almonds, pumpkin seeds, spinach, dark chocolate"},
            "Zinc": {"value": zinc_val, "unit": "mg", "desc": "Supports immune health, wound recovery, and protein synthesis.", "sources": "Beef, chickpeas, lentils, pumpkin seeds, cashews"}
        }

@app.route('/')
def index():
    user = None
    if 'user_id' in session:
        user = db.get_user_by_id(session['user_id'])
    return render_template('index.html', user=user)

# -------------------------------------------------------------
# User Authentication API
# -------------------------------------------------------------
@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.get_json() or {}
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({"error": "Username and password are required."}), 400
        if len(username) < 3 or len(password) < 6:
            return jsonify({"error": "Username must be at least 3 characters and password at least 6 characters."}), 400
            
        user_id = db.register_user(username, password)
        if not user_id:
            return jsonify({"error": "Username is already taken."}), 400
            
        session['user_id'] = user_id
        session['username'] = username
        return jsonify({"success": True, "user": {"id": user_id, "username": username, "is_admin": False}})
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json() or {}
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({"error": "Username and password are required."}), 400
            
        user = db.authenticate_user(username, password)
        if not user:
            return jsonify({"error": "Invalid username or password."}), 401
            
        session['user_id'] = user['id']
        session['username'] = user['username']
        return jsonify({"success": True, "user": {
            "id": user['id'], 
            "username": user['username'], 
            "is_admin": bool(user.get('is_admin', 0))
        }})
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True})

@app.route('/api/profile', methods=['GET'])
def get_profile():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user = db.get_user_by_id(session['user_id'])
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"user": public_user_payload(user)})

@app.route('/api/user/subscription', methods=['GET', 'POST'])
def get_my_subscription():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        user = db.get_user_by_id(session['user_id'])
        if not user:
            return jsonify({"error": "User not found"}), 404

        payload = public_user_payload(user)
        if request.method == 'POST':
            return jsonify({
                "error": "Subscription upgrades are managed by an administrator or billing integration.",
                "subscription_tier": payload['subscription_tier'],
                "plan": payload['plan']
            }), 403

        return jsonify({
            "success": True,
            "subscription_tier": payload['subscription_tier'],
            "plan": payload['plan']
        })
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

# -------------------------------------------------------------
# Weight Logging API
# -------------------------------------------------------------
@app.route('/api/weight/log', methods=['POST'])
def log_weight():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    try:
        data = request.get_json() or {}
        weight_kg = data.get('weight_kg')
        date_str = data.get('date_str')
        
        if weight_kg is None:
            return jsonify({"error": "Weight is required."}), 400
            
        weight_kg = float(weight_kg)
        if weight_kg <= 2 or weight_kg > 500:
            return jsonify({"error": "Please provide a valid weight between 2 kg and 500 kg."}), 400
            
        success = db.log_weight(session['user_id'], weight_kg, date_str)
        if not success:
            return jsonify({"error": "Failed to log weight."}), 400
            
        history = db.get_weight_history(session['user_id'])
        return jsonify({"success": True, "history": history})
    except ValueError:
        return jsonify({"error": "Invalid weight numeric value."}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/weight/history', methods=['GET'])
def get_weight_history():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        history = db.get_weight_history(session['user_id'])
        return jsonify({"history": history})
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

# -------------------------------------------------------------
# User Dashboard & Logs API
# -------------------------------------------------------------
@app.route('/api/user/dashboard', methods=['GET'])
def get_user_dashboard():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    try:
        user_id = session['user_id']
        date_str = request.args.get('date')
        
        # Get standard user details
        user = db.get_user_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        # Get daily progress logs
        daily_log = db.get_daily_intake(user_id, date_str)
        
        # Get coaching notes
        notes = db.get_coaching_notes(user_id)
        
        # Get weight history
        weight_history = db.get_weight_history(user_id)
        
        # Get individual food logs
        food_logs = db.get_food_logs_for_date(user_id, date_str)
        
        # Get individual exercise logs and total burned
        exercise_logs = db.get_exercise_logs(user_id, date_str)
        total_exercise_calories = db.get_total_exercise_calories(user_id, date_str)
        
        # Check if weight is logged for this date
        weight_logged_today = False
        for log in weight_history:
            if log['logged_at'] == date_str:
                weight_logged_today = True
                break
        
        return jsonify({
            "success": True,
            "user": {
                "id": user['id'],
                "username": user['username'],
                "is_admin": bool(user['is_admin']),
                "age": user['age'],
                "height_cm": user['height_cm'],
                "weight_kg": user['weight_kg'],
                "gender": user['gender'],
                "activity": user['activity'],
                "goal": user['goal'],
                "custom_calories": user['custom_calories'],
                "custom_protein": user['custom_protein'],
                "custom_carbs": user['custom_carbs'],
                "custom_fat": user['custom_fat']
            },
            "daily_log": daily_log,
            "coaching_notes": notes,
            "weight_history": weight_history,
            "food_logs": food_logs,
            "weight_logged_today": weight_logged_today,
            "exercise_logs": exercise_logs,
            "total_exercise_calories": total_exercise_calories
        })
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

# -------------------------------------------------------------
# Exercise Logging API
# -------------------------------------------------------------
@app.route('/api/user/exercise', methods=['POST'])
def log_exercise():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        data = request.get_json() or {}
        date_str = data.get('date_str')
        activity_type = data.get('activity_type', '').strip()
        duration_min = data.get('duration_min')
        calories_burned = data.get('calories_burned')

        if not date_str or not activity_type or duration_min is None:
            return jsonify({"error": "Date, activity type, and duration are required."}), 400

        try:
            duration_min = int(duration_min)
            if duration_min <= 0:
                raise ValueError()
        except ValueError:
            return jsonify({"error": "Duration must be a positive integer."}), 400

        # Auto estimate calories if not provided
        if calories_burned is None or str(calories_burned).strip() == '':
            # Fetch user weight for calculation
            user = db.get_user_by_id(session['user_id'])
            weight_kg = user.get('weight_kg', 70.0) if user else 70.0
            if not weight_kg or weight_kg <= 0:
                weight_kg = 70.0

            # METs estimation
            mets_map = {
                'running': 8.0,
                'cycling': 6.0,
                'swimming': 7.0,
                'walking': 3.5,
                'weightlifting': 3.0,
                'yoga': 2.5
            }
            activity_key = activity_type.lower().replace(" ", "")
            met = mets_map.get(activity_key, 3.0) # default MET

            # Formula: Calories = MET * 3.5 * weight_kg / 200 * duration_min
            calories_burned = int(met * 3.5 * weight_kg / 200.0 * duration_min)
        else:
            try:
                calories_burned = int(calories_burned)
                if calories_burned < 0:
                    raise ValueError()
            except ValueError:
                return jsonify({"error": "Calories burned must be a non-negative integer."}), 400

        log_id = db.add_exercise_log(session['user_id'], date_str, activity_type, duration_min, calories_burned)
        if log_id:
            total_burned = db.get_total_exercise_calories(session['user_id'], date_str)
            logs = db.get_exercise_logs(session['user_id'], date_str)
            return jsonify({"success": True, "log_id": log_id, "total_exercise_calories": total_burned, "logs": logs})
        return jsonify({"error": "Failed to log exercise."}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/user/exercise/<int:log_id>', methods=['DELETE'])
def delete_exercise(log_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        conn = db.get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT logged_date FROM exercise_logs WHERE id = ? AND user_id = ?", (log_id, session['user_id']))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({"error": "Exercise log not found."}), 404
            
        date_str = row['logged_date']
        success = db.delete_exercise_log(log_id, session['user_id'])
        if success:
            total_burned = db.get_total_exercise_calories(session['user_id'], date_str)
            logs = db.get_exercise_logs(session['user_id'], date_str)
            return jsonify({"success": True, "total_exercise_calories": total_burned, "logs": logs})
        return jsonify({"error": "Failed to delete exercise log."}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/user/water', methods=['POST'])
def log_water():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    try:
        data = request.get_json() or {}
        date_str = data.get('date_str')
        amount_ml = data.get('amount_ml', 250)
        set_absolute = data.get('set_absolute', False)
        
        if not date_str:
            return jsonify({"error": "Date is required."}), 400
            
        db.update_water(session['user_id'], date_str, int(amount_ml), set_absolute)
        daily_log = db.get_daily_intake(session['user_id'], date_str)
        return jsonify({"success": True, "water_ml": daily_log['water_ml']})
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/foods', methods=['GET'])
def get_foods():
    try:
        foods = db.get_all_foods()
        return jsonify({"success": True, "foods": foods})
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/user/food', methods=['POST'])
def log_food():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    try:
        data = request.get_json() or {}
        date_str = data.get('date_str')
        food_name = data.get('food_name', 'Custom Entry').strip() or 'Custom Entry'
        amount_g = float(data.get('amount_g', 100))
        calories = int(data.get('calories', 0))
        protein = int(data.get('protein', 0))
        carbs = int(data.get('carbs', 0))
        fat = int(data.get('fat', 0))
        
        if not date_str:
            return jsonify({"error": "Date is required."}), 400
            
        db.add_food_log(session['user_id'], date_str, food_name, amount_g, calories, protein, carbs, fat)
        daily_log = db.get_daily_intake(session['user_id'], date_str)
        food_logs = db.get_food_logs_for_date(session['user_id'], date_str)
        return jsonify({"success": True, "daily_log": daily_log, "food_logs": food_logs})
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/user/food/<int:entry_id>', methods=['DELETE'])
def delete_logged_food(entry_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        success = db.delete_food_log(entry_id, session['user_id'])
        if success:
            return jsonify({"success": True})
        return jsonify({"error": "Failed to delete food log or entry not found."}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route('/api/user/checklist', methods=['POST'])
def log_checklist():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    try:
        data = request.get_json() or {}
        date_str = data.get('date_str')
        checklist_data = data.get('checklist', '[]')
        
        if not date_str:
            return jsonify({"error": "Date is required."}), 400
            
        db.update_checklist(session['user_id'], date_str, checklist_data)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

# -------------------------------------------------------------
# B2B Admin Console REST API
# -------------------------------------------------------------
@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats():
    try:
        stats = db.get_admin_stats()
        analytics = db.get_dashboard_analytics()
        stats.update(analytics)
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_users():
    try:
        users = db.get_all_users()
        return jsonify({"success": True, "users": users})
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/admin/users/<int:user_id>/history', methods=['GET'])
@admin_required
def admin_user_history(user_id):
    try:
        history = db.get_weight_history(user_id)
        return jsonify({"success": True, "history": history})
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def admin_delete_user(user_id):
    try:
        user = db.get_user_by_id(user_id)
        username = user['username'] if user else f"User ID {user_id}"
        success = db.delete_user(user_id)
        if success:
            db.log_admin_action(session['user_id'], 'delete_user', username, f"Deleted user profile '{username}' (ID: {user_id})")
            return jsonify({"success": True})
        return jsonify({"error": "Failed to delete user or user is an admin."}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/admin/announcement', methods=['POST'])
@admin_required
def admin_post_announcement():
    try:
        data = request.get_json() or {}
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({"error": "Announcement message is required."}), 400
            
        success = db.add_coaching_note(session['user_id'], None, message)
        if success:
            preview = message[:30] + "..." if len(message) > 30 else message
            db.log_admin_action(session['user_id'], 'post_announcement', 'all', f"Posted global announcement: '{preview}'")
            return jsonify({"success": True})
        return jsonify({"error": "Failed to post announcement."}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/admin/message', methods=['POST'])
@admin_required
def admin_send_message():
    try:
        data = request.get_json() or {}
        receiver_id = data.get('receiver_id')
        message = data.get('message', '').strip()
        
        if not receiver_id or not message:
            return jsonify({"error": "Client ID and message are required."}), 400
            
        success = db.add_coaching_note(session['user_id'], int(receiver_id), message)
        if success:
            user = db.get_user_by_id(receiver_id)
            username = user['username'] if user else f"User ID {receiver_id}"
            preview = message[:30] + "..." if len(message) > 30 else message
            db.log_admin_action(session['user_id'], 'send_coaching_note', username, f"Sent note to {username}: '{preview}'")
            return jsonify({"success": True})
        return jsonify({"error": "Failed to send message."}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/admin/override', methods=['POST'])
@admin_required
def admin_set_override():
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        calories = data.get('calories')
        protein = data.get('protein')
        carbs = data.get('carbs')
        fat = data.get('fat')
        
        if not user_id or calories is None or protein is None or carbs is None or fat is None:
            return jsonify({"error": "All target values are required."}), 400
            
        success = db.save_custom_override(int(user_id), int(calories), int(protein), int(carbs), int(fat))
        if success:
            user = db.get_user_by_id(user_id)
            username = user['username'] if user else f"User ID {user_id}"
            db.log_admin_action(session['user_id'], 'override_targets', username, f"Set target overrides: {calories} kcal, {protein}g P, {carbs}g C, {fat}g F")
            return jsonify({"success": True})
        return jsonify({"error": "Failed to set target overrides."}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/admin/override/<int:user_id>', methods=['DELETE'])
@admin_required
def admin_clear_override(user_id):
    try:
        user = db.get_user_by_id(user_id)
        username = user['username'] if user else f"User ID {user_id}"
        success = db.clear_custom_override(user_id)
        if success:
            db.log_admin_action(session['user_id'], 'clear_override', username, f"Cleared target overrides for {username}")
            return jsonify({"success": True})
        return jsonify({"error": "Failed to clear target overrides."}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/admin/audit-logs', methods=['GET'])
@admin_required
def admin_audit_logs():
    try:
        logs = db.get_admin_audit_logs(limit=50)
        return jsonify({"success": True, "logs": logs})
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/admin/users/<int:user_id>/tier', methods=['POST'])
@admin_required
def admin_update_subscription(user_id):
    try:
        data = request.get_json() or {}
        tier = data.get('subscription_tier', data.get('tier', 'free')).strip().lower()
        if tier not in ['free', 'premium', 'enterprise']:
            return jsonify({"error": "Invalid subscription tier."}), 400
            
        success = db.update_user_subscription(user_id, tier)
        if success:
            user = db.get_user_by_id(user_id)
            username = user['username'] if user else f"User ID {user_id}"
            db.log_admin_action(session['user_id'], 'update_subscription', username, f"Changed subscription plan for {username} to {tier.capitalize()}")
            return jsonify({"success": True})
        return jsonify({"error": "Failed to update user subscription plan."}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/admin/foods', methods=['POST'])
@admin_required
def admin_add_food():
    try:
        data = request.get_json() or {}
        name = data.get('name', '').strip()
        calories = data.get('calories')
        protein = data.get('protein')
        carbs = data.get('carbs')
        fat = data.get('fat')
        
        if not name or calories is None or protein is None or carbs is None or fat is None:
            return jsonify({"error": "All food details are required."}), 400
            
        food_id = db.add_food(name, calories, protein, carbs, fat)
        if food_id:
            db.log_admin_action(session['user_id'], 'add_food', name, f"Added predefined food '{name}' ({calories} kcal per 100g)")
            return jsonify({"success": True, "food_id": food_id})
        return jsonify({"error": "Food name already exists in database."}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/admin/foods/<int:food_id>', methods=['PUT'])
@admin_required
def admin_edit_food(food_id):
    try:
        data = request.get_json() or {}
        name = data.get('name', '').strip()
        calories = data.get('calories')
        protein = data.get('protein')
        carbs = data.get('carbs')
        fat = data.get('fat')
        
        if not name or calories is None or protein is None or carbs is None or fat is None:
            return jsonify({"error": "All food details are required."}), 400
            
        success = db.update_food(food_id, name, calories, protein, carbs, fat)
        if success:
            db.log_admin_action(session['user_id'], 'edit_food', name, f"Updated predefined food '{name}' (ID: {food_id})")
            return jsonify({"success": True})
        return jsonify({"error": "Failed to edit food or name already exists."}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/admin/foods/<int:food_id>', methods=['DELETE'])
@admin_required
def admin_delete_food(food_id):
    try:
        # Get food name first for logging
        conn = db.get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM foods WHERE id = ?", (food_id,))
        row = cursor.fetchone()
        food_name = row['name'] if row else f"Food ID {food_id}"
        conn.close()
        
        success = db.delete_food(food_id)
        if success:
            db.log_admin_action(session['user_id'], 'delete_food', food_name, f"Deleted predefined food '{food_name}' (ID: {food_id})")
            return jsonify({"success": True})
        return jsonify({"error": "Failed to delete food item."}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

# -------------------------------------------------------------
# Calculation Engine API
# -------------------------------------------------------------
@app.route('/api/calculate', methods=['POST'])
def calculate():
    try:
        data = request.get_json() or {}
        
        # Inputs
        age = int(data.get('age', 25))
        height_cm = float(data.get('height_cm', 170.0))
        weight_kg = float(data.get('weight_kg', 70.0))
        gender = str(data.get('gender', 'male')).lower()
        activity = str(data.get('activity', 'moderate')).lower()
        goal = str(data.get('goal', 'maintain')).lower()
        
        # Validations
        if age <= 0 or age > 120:
            return jsonify({"error": "Please provide a valid age between 1 and 120."}), 400
        if height_cm <= 30 or height_cm > 300:
            return jsonify({"error": "Please provide a valid height between 30 cm and 300 cm."}), 400
        if weight_kg <= 2 or weight_kg > 500:
            return jsonify({"error": "Please provide a valid weight between 2 kg and 500 kg."}), 400
        if gender not in ['male', 'female']:
            gender = 'male'

        # 1. BMR Calculation (Mifflin-St Jeor)
        if gender == 'male':
            bmr = 10.0 * weight_kg + 6.25 * height_cm - 5.0 * age + 5.0
        else:
            bmr = 10.0 * weight_kg + 6.25 * height_cm - 5.0 * age - 161.0
            
        # 2. TDEE Calculation (Activity Factor)
        activity_multipliers = {
            "sedentary": 1.2,
            "light": 1.375,
            "moderate": 1.55,
            "active": 1.725,
            "very_active": 1.9
        }
        multiplier = activity_multipliers.get(activity, 1.55)
        tdee = bmr * multiplier
        
        # 3. Goal Calorie Adjustment
        goal_adjustments = {
            "lose": -500,
            "lose_mild": -250,
            "maintain": 0,
            "gain_mild": 250,
            "gain": 500
        }
        target_calories = tdee + goal_adjustments.get(goal, 0)
        
        # Health safety floors
        min_calories = 1500 if gender == 'male' else 1200
        if target_calories < min_calories:
            target_calories = min_calories
            
        target_calories = round(target_calories)
        
        # 4. Macronutrient Partitioning
        # Protein: 2.0g per kg of body weight
        protein_grams = weight_kg * 2.0
        protein_calories = protein_grams * 4
        
        max_protein_cal = target_calories * 0.35
        min_protein_cal = target_calories * 0.15
        
        if protein_calories > max_protein_cal:
            protein_grams = max_protein_cal / 4
            protein_calories = max_protein_cal
        elif protein_calories < min_protein_cal:
            protein_grams = min_protein_cal / 4
            protein_calories = min_protein_cal
            
        protein_grams = round(protein_grams)
        
        # Fat: 25% of total calories
        fat_calories = target_calories * 0.25
        fat_grams = round(fat_calories / 9)
        
        # Carbs: Remainder of calories
        carb_calories = target_calories - protein_calories - fat_calories
        carb_grams = round(carb_calories / 4)
        if carb_grams < 0:
            carb_grams = 0
            
        # Fiber: 14g per 1000 kcal
        base_fiber = (target_calories / 1000.0) * 14.0
        gender_min_fiber = 38.0 if gender == 'male' else 25.0
        fiber_grams = round(max(base_fiber, gender_min_fiber))
        
        # Water: 35ml per kg of weight + activity adjustment
        water_ml = weight_kg * 35.0
        activity_water_additions = {
            "sedentary": 0,
            "light": 350,
            "moderate": 700,
            "active": 1000,
            "very_active": 1500
        }
        water_ml += activity_water_additions.get(activity, 700)
        water_liters = round(water_ml / 1000.0, 1)
        
        # 5. Micronutrients
        micronutrients = get_micronutrients(age, gender)
        
        # Ideal weight estimation based on healthy BMI (22.0)
        ideal_weight_kg = round(22.0 * ((height_cm / 100.0) ** 2), 1)

        # Automatically save user profile if logged in as standard user
        if 'user_id' in session:
            user = db.get_user_by_id(session['user_id'])
            if user and not user.get('is_admin'):
                db.save_profile(session['user_id'], age, height_cm, weight_kg, gender, activity, goal)
                # Check for custom target overrides and apply them
                user = db.get_user_by_id(session['user_id'])
                if user.get('custom_calories') is not None:
                    target_calories = user['custom_calories']
                    protein_grams = user['custom_protein'] or 0
                    carb_grams = user['custom_carbs'] or 0
                    fat_grams = user['custom_fat'] or 0

        return jsonify({
            "bmr": round(bmr),
            "tdee": round(tdee),
            "target_calories": target_calories,
            "ideal_weight_kg": ideal_weight_kg,
            "macros": {
                "protein": {
                    "grams": protein_grams,
                    "calories": round(protein_grams * 4),
                    "percentage": round((protein_grams * 4 / target_calories) * 100) if target_calories > 0 else 0
                },
                "carbs": {
                    "grams": carb_grams,
                    "calories": round(carb_grams * 4),
                    "percentage": round((carb_grams * 4 / target_calories) * 100) if target_calories > 0 else 0
                },
                "fat": {
                    "grams": fat_grams,
                    "calories": round(fat_grams * 9),
                    "percentage": round((fat_grams * 9 / target_calories) * 100) if target_calories > 0 else 0
                }
            },
            "fiber_g": fiber_grams,
            "water_l": water_liters,
            "micronutrients": micronutrients
        })
        
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5006)
