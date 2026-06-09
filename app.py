import math
import os
import json
from datetime import datetime, timedelta
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
    """Return non-sensitive user data for the client UI."""
    payload = dict(user)
    payload.pop('password_hash', None)
    payload['is_admin'] = bool(payload.get('is_admin', 0))
    payload.pop('subscription_tier', None)
    for key in ['allergies', 'client_tags']:
        value = payload.get(key)
        if isinstance(value, str):
            try:
                payload[key] = json.loads(value)
            except json.JSONDecodeError:
                payload[key] = []
    return payload

def calculate_targets(age, height_cm, weight_kg, gender, activity, goal):
    """Standards-aware target engine using Mifflin-St Jeor plus DGA/DRI-style guardrails."""
    if gender == 'male':
        bmr = 10.0 * weight_kg + 6.25 * height_cm - 5.0 * age + 5.0
    else:
        bmr = 10.0 * weight_kg + 6.25 * height_cm - 5.0 * age - 161.0

    activity_multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9
    }
    multiplier = activity_multipliers.get(activity, 1.55)
    tdee = bmr * multiplier

    goal_adjustments = {
        "lose": -500,
        "lose_mild": -250,
        "maintain": 0,
        "gain_mild": 250,
        "gain": 500
    }
    target_calories = tdee + goal_adjustments.get(goal, 0)
    min_calories = 1500 if gender == 'male' else 1200
    target_calories = round(max(target_calories, min_calories))

    bmi = weight_kg / ((height_cm / 100.0) ** 2)
    ideal_weight_kg = round(22.0 * ((height_cm / 100.0) ** 2), 1)

    # DGA adult AMDR: protein 10-35%, carbohydrate 45-65%, fat 20-35%.
    protein_factor = 1.8 if goal.startswith('gain') else 1.6 if goal.startswith('lose') else 1.2
    protein_grams = weight_kg * protein_factor
    protein_calories = protein_grams * 4
    min_protein_cal = target_calories * 0.10
    max_protein_cal = target_calories * 0.35
    protein_calories = min(max(protein_calories, min_protein_cal), max_protein_cal)
    protein_grams = round(protein_calories / 4)

    fat_pct = 0.25
    if goal.startswith('lose'):
        fat_pct = 0.28
    elif goal.startswith('gain'):
        fat_pct = 0.25
    fat_calories = min(max(target_calories * fat_pct, target_calories * 0.20), target_calories * 0.35)
    fat_grams = round(fat_calories / 9)

    carb_calories = target_calories - protein_calories - fat_calories
    carb_min_calories = target_calories * 0.45
    carb_max_calories = target_calories * 0.65
    if carb_calories < carb_min_calories:
        carb_calories = carb_min_calories
        fat_calories = max(target_calories * 0.20, target_calories - protein_calories - carb_calories)
        fat_grams = round(fat_calories / 9)
    elif carb_calories > carb_max_calories:
        carb_calories = carb_max_calories
    carb_grams = max(0, round(carb_calories / 4))

    fiber_grams = round(max((target_calories / 1000.0) * 14.0, 38.0 if gender == 'male' else 25.0))
    water_ml = weight_kg * 35.0 + {
        "sedentary": 0,
        "light": 350,
        "moderate": 700,
        "active": 1000,
        "very_active": 1500
    }.get(activity, 700)

    standards = {
        "macro_reference": "AMDR: protein 10-35%, carbohydrate 45-65%, fat 20-35% of calories.",
        "fiber_reference": "Fiber target uses 14g per 1,000 kcal with adult minimum guardrails.",
        "added_sugar_limit_g": round((target_calories * 0.10) / 4),
        "saturated_fat_limit_g": round((target_calories * 0.10) / 9),
        "sodium_limit_mg": 2300,
        "who_notes": [
            "Prefer unsaturated fats over saturated fats.",
            "Limit free or added sugars and highly processed foods.",
            "Keep sodium near or below 2,300 mg/day for general adult guidance."
        ]
    }

    return {
        "bmr": round(bmr),
        "tdee": round(tdee),
        "target_calories": target_calories,
        "ideal_weight_kg": ideal_weight_kg,
        "bmi": round(bmi, 1),
        "bmi_category": get_bmi_category(bmi),
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
        "water_l": round(water_ml / 1000.0, 1),
        "micronutrients": get_micronutrients(age, gender),
        "standards": standards
    }

def get_bmi_category(bmi):
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Healthy range"
    if bmi < 30:
        return "Overweight"
    return "Obesity range"

def build_progress_intelligence(user, daily_log, weight_history, exercise_calories, calc):
    target = calc['target_calories']
    consumed = daily_log.get('calories', 0) if daily_log else 0
    protein = daily_log.get('protein', 0) if daily_log else 0
    carbs = daily_log.get('carbs', 0) if daily_log else 0
    fat = daily_log.get('fat', 0) if daily_log else 0
    water = daily_log.get('water_ml', 0) if daily_log else 0

    calorie_score = 100 if consumed and consumed <= target else max(0, 100 - min(100, abs(consumed - target) / max(target, 1) * 100))
    protein_score = min(100, (protein / max(calc['macros']['protein']['grams'], 1)) * 100)
    water_score = min(100, (water / max(calc['water_l'] * 1000, 1)) * 100)
    adherence_score = round((calorie_score * 0.45) + (protein_score * 0.3) + (water_score * 0.25))

    weekly_logs = []
    for i in range(6, -1, -1):
        day = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        log = db.get_daily_intake(user['id'], day)
        weekly_logs.append(log)
    consistency_days = sum(1 for log in weekly_logs if log and log.get('calories', 0) > 0)
    macro_consistency = round(sum(
        1 for log in weekly_logs
        if log and log.get('protein', 0) >= calc['macros']['protein']['grams'] * 0.8
    ) / 7 * 100)

    streak = 0
    for i in range(0, 30):
        day = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        log = db.get_daily_intake(user['id'], day)
        if log and (log.get('calories', 0) > 0 or log.get('water_ml', 0) > 0):
            streak += 1
        else:
            break

    projection = {"status": "insufficient_data", "eta_date": None, "days": None}
    why = "Log at least two weights for trend analysis."
    if len(weight_history) >= 2:
        first = weight_history[0]
        last = weight_history[-1]
        days = max(1, (datetime.fromisoformat(last['logged_at']) - datetime.fromisoformat(first['logged_at'])).days)
        change = last['weight_kg'] - first['weight_kg']
        weekly_rate = change / days * 7
        target_weight = calc['ideal_weight_kg']
        remaining = target_weight - last['weight_kg']
        if abs(weekly_rate) >= 0.05 and ((remaining > 0 and weekly_rate > 0) or (remaining < 0 and weekly_rate < 0)):
            weeks = abs(remaining / weekly_rate)
            eta = datetime.now() + timedelta(days=round(weeks * 7))
            projection = {"status": "on_track", "eta_date": eta.strftime('%Y-%m-%d'), "days": round(weeks * 7)}
        else:
            projection = {"status": "off_track", "eta_date": None, "days": None}

        balance = consumed - exercise_calories - target
        if abs(balance) < target * 0.08:
            why = "Weight changes are likely driven by normal fluid shifts because calorie balance is close to target."
        elif balance > 0:
            why = "Recent intake is above target after exercise, which can slow loss or drive gain."
        else:
            why = "Recent intake is below target after exercise, which can drive weight loss if sustained."

    return {
        "adherence_score": adherence_score,
        "streak_days": streak,
        "macro_consistency_pct": macro_consistency,
        "tracked_days_this_week": consistency_days,
        "goal_eta": projection,
        "why_weight_changed": why,
        "remaining_macros": {
            "calories": max(0, target - consumed + exercise_calories),
            "protein": max(0, calc['macros']['protein']['grams'] - protein),
            "carbs": max(0, calc['macros']['carbs']['grams'] - carbs),
            "fat": max(0, calc['macros']['fat']['grams'] - fat)
        }
    }

def generate_meal_plan(user, calc, foods, week_start=None, remaining=None):
    allergies = user.get('allergies') or []
    if isinstance(allergies, str):
        try:
            allergies = json.loads(allergies)
        except json.JSONDecodeError:
            allergies = []
    allergy_terms = [a.lower() for a in allergies]
    dietary_style = (user.get('dietary_style') or 'balanced').lower()
    cuisine = (user.get('region_cuisine') or 'global').lower()
    schedule = user.get('meal_schedule') or 'standard'
    meal_names = ["Breakfast", "Lunch", "Dinner"] if schedule != 'small_frequent' else ["Breakfast", "Snack", "Lunch", "Dinner"]

    candidates = [f for f in foods if not any(term and term in f['name'].lower() for term in allergy_terms)]
    if dietary_style in ['vegetarian', 'vegan']:
        avoid = ['chicken', 'beef', 'pork', 'turkey', 'salmon', 'tuna', 'cod', 'shrimp', 'lamb', 'fish']
        candidates = [f for f in candidates if not any(term in f['name'].lower() for term in avoid)]
    if dietary_style == 'low_carb':
        candidates = sorted(candidates, key=lambda f: (f['carbs_per_100g'], -f['protein_per_100g']))
    else:
        candidates = sorted(candidates, key=lambda f: (-f['protein_per_100g'], abs(f['calories_per_100g'] - 160)))

    if not candidates:
        candidates = foods[:]

    daily_target = remaining.get('calories') if remaining else calc['target_calories']
    meal_target = max(250, round(daily_target / len(meal_names)))
    start = week_start or datetime.now().strftime('%Y-%m-%d')
    plan = {"week_start": start, "dietary_style": dietary_style, "region_cuisine": cuisine, "days": []}
    shopping = {}

    for day_idx in range(7):
        day_date = (datetime.fromisoformat(start) + timedelta(days=day_idx)).strftime('%Y-%m-%d')
        day = {"date": day_date, "meals": []}
        for meal_idx, meal_name in enumerate(meal_names):
            food = candidates[(day_idx * len(meal_names) + meal_idx) % len(candidates)]
            amount = max(60, min(350, round((meal_target / max(food['calories_per_100g'], 1)) * 100)))
            factor = amount / 100.0
            meal = {
                "name": meal_name,
                "food": food['name'],
                "amount_g": amount,
                "calories": round(food['calories_per_100g'] * factor),
                "protein": round(food['protein_per_100g'] * factor),
                "carbs": round(food['carbs_per_100g'] * factor),
                "fat": round(food['fat_per_100g'] * factor),
                "swap_hint": "Swap with a similar calorie food from favorites or database."
            }
            day["meals"].append(meal)
            shopping[food['name']] = shopping.get(food['name'], 0) + amount
        plan["days"].append(day)

    shopping_list = [{"item": name, "amount_g": amount} for name, amount in sorted(shopping.items())]
    return plan, shopping_list

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
        user = db.get_user_by_id(user_id)
        return jsonify({"success": True, "user": public_user_payload(user)})
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
        return jsonify({"success": True, "user": public_user_payload(user)})
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True})

@app.route('/api/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_id = session['user_id']
    if request.method == 'GET':
        user = db.get_user_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify({"user": public_user_payload(user)})
        
    try:
        data = request.get_json() or {}
        full_name = data.get('full_name', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if email and ('@' not in email or '.' not in email):
            return jsonify({"error": "Please provide a valid email address."}), 400
        if password and len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters long."}), 400
            
        db.update_account_settings(user_id, full_name, email, password if password else None)
        
        user = db.get_user_by_id(user_id)
        return jsonify({"success": True, "user": public_user_payload(user)})
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
        date_str = request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
        
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
        calc = None
        progress = None
        if user.get('age') and user.get('height_cm') and user.get('weight_kg'):
            calc = calculate_targets(
                int(user['age']),
                float(user['height_cm']),
                float(user['weight_kg']),
                user.get('gender') or 'male',
                user.get('activity') or 'moderate',
                user.get('goal') or 'maintain'
            )
            if user.get('custom_calories') is not None:
                calc['target_calories'] = user['custom_calories']
                calc['macros']['protein']['grams'] = user['custom_protein'] or 0
                calc['macros']['carbs']['grams'] = user['custom_carbs'] or 0
                calc['macros']['fat']['grams'] = user['custom_fat'] or 0
            progress = build_progress_intelligence(user, daily_log, weight_history, total_exercise_calories, calc)
        
        # Check if weight is logged for this date
        weight_logged_today = False
        for log in weight_history:
            if log['logged_at'] == date_str:
                weight_logged_today = True
                break
        
        return jsonify({
            "success": True,
            "user": public_user_payload(user),
            "daily_log": daily_log,
            "coaching_notes": notes,
            "weight_history": weight_history,
            "food_logs": food_logs,
            "weight_logged_today": weight_logged_today,
            "exercise_logs": exercise_logs,
            "total_exercise_calories": total_exercise_calories,
            "calculation": calc,
            "progress": progress,
            "recent_foods": db.get_recent_foods(user_id),
            "favorite_foods": db.get_favorite_foods(user_id),
            "meal_templates": db.get_meal_templates(user_id),
            "recipes": db.get_recipes(user_id),
            "meal_plan": db.get_latest_meal_plan(user_id),
            "checkins": db.get_checkins(user_id),
            "thread_messages": db.get_thread_messages(user_id, user.get('coach_id'), limit=20) if user.get('coach_id') else []
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
        serving_unit = data.get('serving_unit')
        serving_multiplier = float(data.get('serving_multiplier', 1) or 1)
        unit_grams = {
            "g": 1,
            "cup": 240,
            "tbsp": 15,
            "oz": 28.35,
            "piece": 100
        }.get(serving_unit, None)
        if unit_grams:
            amount_g = unit_grams * serving_multiplier
        calories = int(data.get('calories', 0))
        protein = int(data.get('protein', 0))
        carbs = int(data.get('carbs', 0))
        fat = int(data.get('fat', 0))
        
        if not date_str:
            return jsonify({"error": "Date is required."}), 400
            
        db.add_food_log(session['user_id'], date_str, food_name, amount_g, calories, protein, carbs, fat)
        if data.get('favorite'):
            db.add_favorite_food(session['user_id'], food_name, data.get('food_id'))
        daily_log = db.get_daily_intake(session['user_id'], date_str)
        food_logs = db.get_food_logs_for_date(session['user_id'], date_str)
        return jsonify({
            "success": True,
            "daily_log": daily_log,
            "food_logs": food_logs,
            "recent_foods": db.get_recent_foods(session['user_id']),
            "favorite_foods": db.get_favorite_foods(session['user_id'])
        })
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

@app.route('/api/onboarding', methods=['GET', 'POST'])
def onboarding():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user = db.get_user_by_id(session['user_id'])
    if not user:
        return jsonify({"error": "User not found"}), 404
    if request.method == 'GET':
        return jsonify({"success": True, "user": public_user_payload(user)})
    try:
        data = request.get_json() or {}
        success = db.save_onboarding(session['user_id'], data)
        if not success:
            return jsonify({"error": "Failed to save onboarding details."}), 400
        return jsonify({"success": True, "user": public_user_payload(db.get_user_by_id(session['user_id']))})
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/user/logging/shortcuts', methods=['GET'])
def food_logging_shortcuts():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({
        "success": True,
        "recent_foods": db.get_recent_foods(session['user_id']),
        "favorite_foods": db.get_favorite_foods(session['user_id']),
        "meal_templates": db.get_meal_templates(session['user_id']),
        "recipes": db.get_recipes(session['user_id']),
        "serving_units": [
            {"label": "grams", "value": "g", "grams": 1},
            {"label": "cup", "value": "cup", "grams": 240},
            {"label": "tablespoon", "value": "tbsp", "grams": 15},
            {"label": "ounce", "value": "oz", "grams": 28.35},
            {"label": "piece", "value": "piece", "grams": 100}
        ],
        "barcode_note": "Barcode lookup is ready for integration with a branded food database provider.",
        "photo_ocr_note": "Photo/OCR estimates can be reviewed as custom entries before logging."
    })

@app.route('/api/user/favorites', methods=['POST'])
def add_favorite():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    food_name = data.get('food_name', '').strip()
    if not food_name:
        return jsonify({"error": "Food name is required."}), 400
    db.add_favorite_food(session['user_id'], food_name, data.get('food_id'))
    return jsonify({"success": True, "favorite_foods": db.get_favorite_foods(session['user_id'])})

@app.route('/api/user/meal-templates', methods=['POST'])
def create_template():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    entries = data.get('entries', [])
    if not name or not isinstance(entries, list):
        return jsonify({"error": "Template name and entries are required."}), 400
    template_id = db.create_meal_template(session['user_id'], name, entries)
    return jsonify({"success": True, "template_id": template_id, "meal_templates": db.get_meal_templates(session['user_id'])})

@app.route('/api/user/recipes', methods=['POST'])
def create_recipe():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    ingredients = data.get('ingredients', [])
    if not name or not isinstance(ingredients, list):
        return jsonify({"error": "Recipe name and ingredients are required."}), 400
    totals = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
    for item in ingredients:
        amount = float(item.get('amount_g', 100) or 100)
        food = item.get('food') or {}
        factor = amount / 100.0
        totals["calories"] += round(float(food.get('calories_per_100g', item.get('calories', 0))) * factor)
        totals["protein"] += round(float(food.get('protein_per_100g', item.get('protein', 0))) * factor)
        totals["carbs"] += round(float(food.get('carbs_per_100g', item.get('carbs', 0))) * factor)
        totals["fat"] += round(float(food.get('fat_per_100g', item.get('fat', 0))) * factor)
    recipe_id = db.save_recipe(session['user_id'], name, data.get('servings', 1), ingredients, totals)
    return jsonify({"success": True, "recipe_id": recipe_id, "totals": totals, "recipes": db.get_recipes(session['user_id'])})

@app.route('/api/user/meal-plan', methods=['GET', 'POST'])
def user_meal_plan():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user = db.get_user_by_id(session['user_id'])
    if not user or not user.get('age'):
        return jsonify({"error": "Complete onboarding and body metrics before generating a meal plan."}), 400
    if request.method == 'GET':
        return jsonify({"success": True, "meal_plan": db.get_latest_meal_plan(session['user_id'])})
    try:
        data = request.get_json() or {}
        calc = calculate_targets(int(user['age']), float(user['height_cm']), float(user['weight_kg']), user.get('gender') or 'male', user.get('activity') or 'moderate', user.get('goal') or 'maintain')
        if user.get('custom_calories') is not None:
            calc['target_calories'] = user['custom_calories']
            calc['macros']['protein']['grams'] = user['custom_protein'] or 0
            calc['macros']['carbs']['grams'] = user['custom_carbs'] or 0
            calc['macros']['fat']['grams'] = user['custom_fat'] or 0
        foods = db.get_all_foods()
        week_start = data.get('week_start') or datetime.now().strftime('%Y-%m-%d')
        plan, shopping = generate_meal_plan(user, calc, foods, week_start, data.get('remaining_macros'))
        db.save_meal_plan(session['user_id'], week_start, plan, shopping)
        return jsonify({"success": True, "meal_plan": {"week_start": week_start, "plan": plan, "shopping": shopping}})
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/user/checkins', methods=['POST'])
def create_checkin():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    checkin_id = db.add_checkin(
        session['user_id'],
        int(data.get('mood', 3) or 3),
        int(data.get('energy', 3) or 3),
        int(data.get('hunger', 3) or 3),
        int(data.get('compliance', 3) or 3),
        data.get('notes', '').strip()
    )
    return jsonify({"success": True, "checkin_id": checkin_id, "checkins": db.get_checkins(session['user_id'])})

@app.route('/api/user/thread', methods=['GET', 'POST'])
def user_thread():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user = db.get_user_by_id(session['user_id'])
    coach_id = user.get('coach_id') if user else None
    if not coach_id:
        return jsonify({"success": True, "messages": [], "notice": "No coach is assigned yet."})
    if request.method == 'POST':
        data = request.get_json() or {}
        message = data.get('message', '').strip()
        if not message:
            return jsonify({"error": "Message is required."}), 400
        db.add_thread_message(session['user_id'], coach_id, message)
    return jsonify({"success": True, "messages": db.get_thread_messages(session['user_id'], coach_id, limit=50)})

@app.route('/api/user/progress', methods=['GET'])
def user_progress():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    date_str = request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
    user = db.get_user_by_id(session['user_id'])
    if not user or not user.get('age'):
        return jsonify({"error": "Complete your profile before viewing progress intelligence."}), 400
    calc = calculate_targets(int(user['age']), float(user['height_cm']), float(user['weight_kg']), user.get('gender') or 'male', user.get('activity') or 'moderate', user.get('goal') or 'maintain')
    daily_log = db.get_daily_intake(session['user_id'], date_str)
    history = db.get_weight_history(session['user_id'])
    exercise = db.get_total_exercise_calories(session['user_id'], date_str)
    return jsonify({"success": True, "progress": build_progress_intelligence(user, daily_log, history, exercise, calc)})

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
        users = [public_user_payload(user) for user in users]
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
            db.add_target_history(int(user_id), session['user_id'], int(calories), int(protein), int(carbs), int(fat), data.get('reason', 'Coach override'))
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

@app.route('/api/admin/users/<int:user_id>/coach', methods=['POST'])
@admin_required
def admin_assign_coach(user_id):
    try:
        data = request.get_json() or {}
        coach_id = int(data.get('coach_id') or session['user_id'])
        tags = data.get('client_tags', data.get('tags', []))
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',') if t.strip()]
        success = db.assign_client_coach(user_id, coach_id, tags)
        if success:
            user = db.get_user_by_id(user_id)
            username = user['username'] if user else f"User ID {user_id}"
            db.log_admin_action(session['user_id'], 'assign_coach', username, f"Assigned coach {coach_id} with tags: {', '.join(tags)}")
            return jsonify({"success": True, "user": public_user_payload(db.get_user_by_id(user_id))})
        return jsonify({"error": "Failed to assign coach."}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/admin/users/<int:user_id>/thread', methods=['GET', 'POST'])
@admin_required
def admin_thread(user_id):
    try:
        if request.method == 'POST':
            data = request.get_json() or {}
            message = data.get('message', '').strip()
            if not message:
                return jsonify({"error": "Message is required."}), 400
            db.add_thread_message(session['user_id'], user_id, message)
            user = db.get_user_by_id(user_id)
            db.log_admin_action(session['user_id'], 'private_thread_message', user['username'] if user else user_id, "Sent private thread message")
        return jsonify({"success": True, "messages": db.get_thread_messages(session['user_id'], user_id, limit=50)})
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/admin/users/<int:user_id>/weekly-report', methods=['GET'])
@admin_required
def admin_weekly_report(user_id):
    try:
        user = db.get_user_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        end = datetime.now()
        start = end - timedelta(days=6)
        logs = []
        for i in range(7):
            day = (start + timedelta(days=i)).strftime('%Y-%m-%d')
            logs.append({"date": day, "intake": db.get_daily_intake(user_id, day), "exercise": db.get_total_exercise_calories(user_id, day)})
        calc = None
        progress = None
        if user.get('age') and user.get('height_cm') and user.get('weight_kg'):
            calc = calculate_targets(int(user['age']), float(user['height_cm']), float(user['weight_kg']), user.get('gender') or 'male', user.get('activity') or 'moderate', user.get('goal') or 'maintain')
            progress = build_progress_intelligence(user, db.get_daily_intake(user_id, end.strftime('%Y-%m-%d')), db.get_weight_history(user_id), db.get_total_exercise_calories(user_id, end.strftime('%Y-%m-%d')), calc)
        report = {
            "client": public_user_payload(user),
            "period": {"start": start.strftime('%Y-%m-%d'), "end": end.strftime('%Y-%m-%d')},
            "daily_logs": logs,
            "weight_history": db.get_weight_history(user_id),
            "checkins": db.get_checkins(user_id),
            "target_history": db.get_target_history(user_id),
            "calculation": calc,
            "progress": progress,
            "export_note": "This JSON payload is ready for PDF rendering or download."
        }
        return jsonify({"success": True, "report": report})
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

        result = calculate_targets(age, height_cm, weight_kg, gender, activity, goal)

        # Automatically save user profile if logged in as standard user
        if 'user_id' in session:
            user = db.get_user_by_id(session['user_id'])
            if user and not user.get('is_admin'):
                db.save_profile(session['user_id'], age, height_cm, weight_kg, gender, activity, goal)
                # Check for custom target overrides and apply them
                user = db.get_user_by_id(session['user_id'])
                if user.get('custom_calories') is not None:
                    result['target_calories'] = user['custom_calories']
                    result['macros']['protein']['grams'] = user['custom_protein'] or 0
                    result['macros']['carbs']['grams'] = user['custom_carbs'] or 0
                    result['macros']['fat']['grams'] = user['custom_fat'] or 0
                    for key, calories_per_gram in [('protein', 4), ('carbs', 4), ('fat', 9)]:
                        grams = result['macros'][key]['grams']
                        result['macros'][key]['calories'] = round(grams * calories_per_gram)
                        result['macros'][key]['percentage'] = round((grams * calories_per_gram / result['target_calories']) * 100) if result['target_calories'] > 0 else 0
                    result['coach_override_active'] = True

        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5006)
