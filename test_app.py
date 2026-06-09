import os
import unittest
import json
import sqlite3

# Dynamically override DB_PATH before db is used
import db
TEST_DB_PATH = os.path.join(os.path.dirname(__file__), 'test_nutriquant.db')
db.DB_PATH = TEST_DB_PATH

# Delete test database if it exists from a previous crash
if os.path.exists(TEST_DB_PATH):
    try:
        os.remove(TEST_DB_PATH)
    except OSError:
        pass

from app import app

class NutriQuantTestCase(unittest.TestCase):
    def setUp(self):
        # Re-initialize the test database to ensure a clean slate
        db.init_db()
        self.client = app.test_client()
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test_secret_key'

    def tearDown(self):
        # Clean up database after each test
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except OSError:
                pass

    def register_user(self, username, password):
        return self.client.post('/api/auth/register', json={
            'username': username,
            'password': password
        })

    def login_user(self, username, password):
        return self.client.post('/api/auth/login', json={
            'username': username,
            'password': password
        })

    def get_user_by_username(self, username):
        conn = db.get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username.strip().lower(),))
        user = cursor.fetchone()
        conn.close()
        return dict(user) if user else None

    def test_user_registration_and_login(self):
        # Test registering a user
        res = self.register_user('client1', 'pass123')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])

        # Test logging in
        res = self.login_user('client1', 'pass123')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['username'], 'client1')

    def test_absolute_water_logging(self):
        # Register and login
        self.register_user('water_user', 'pass123')
        self.login_user('water_user', 'pass123')

        # Log water absolutely to 1000ml
        res = self.client.post('/api/user/water', json={
            'date_str': '2026-06-09',
            'amount_ml': 1000,
            'set_absolute': True
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['water_ml'], 1000)

        # Log water absolutely to 500ml (decrease)
        res = self.client.post('/api/user/water', json={
            'date_str': '2026-06-09',
            'amount_ml': 500,
            'set_absolute': True
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['water_ml'], 500)

        # Log water relatively (increase by 250ml)
        res = self.client.post('/api/user/water', json={
            'date_str': '2026-06-09',
            'amount_ml': 250,
            'set_absolute': False
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['water_ml'], 750)

    def test_food_database_size(self):
        # Predefined food seeding should ensure at least 6000 foods
        foods = db.get_all_foods()
        self.assertGreaterEqual(len(foods), 6000)

    def test_subscription_system_removed_from_public_api(self):
        self.register_user('client_without_subscription', 'pass123')
        self.login_user('client_without_subscription', 'pass123')

        res = self.client.get('/api/profile')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertNotIn('subscription_tier', data['user'])
        self.assertNotIn('plan', data['user'])

        res = self.client.post('/api/user/subscription', json={'subscription_tier': 'premium'})
        self.assertEqual(res.status_code, 404)

    def test_admin_stats_access_control(self):
        # Log in as normal client
        self.register_user('normal_user', 'pass123')
        self.login_user('normal_user', 'pass123')

        # Verify normal client is blocked from admin stats
        res = self.client.get('/api/admin/stats')
        self.assertEqual(res.status_code, 403)

        # Log in as admin
        self.login_user('admin', 'admin123')

        # Verify admin has access
        res = self.client.get('/api/admin/stats')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertIn('total_users', data['stats'])

    def test_admin_stats_expose_coaching_operations(self):
        self.register_user('client_for_ops', 'pass123')
        user = self.get_user_by_username('client_for_ops')
        db.save_onboarding(user['id'], {
            'dietary_style': 'balanced',
            'allergies': [],
            'meal_schedule': 'standard',
            'region_cuisine': 'global',
            'coaching_level': 'weekly_coaching'
        })
        db.add_checkin(user['id'], 4, 4, 3, 5, 'Solid week')

        self.login_user('admin', 'admin123')

        res = self.client.get('/api/admin/stats')
        self.assertEqual(res.status_code, 200)
        stats = json.loads(res.data)['stats']
        self.assertIn('onboarding_completed', stats)
        self.assertIn('assigned_clients', stats)
        self.assertIn('active_last_7_days', stats)
        self.assertIn('checkins_last_7_days', stats)
        self.assertNotIn('tiers', stats)
        self.assertNotIn('estimated_mrr', stats)

    def test_predefined_food_crud(self):
        # Log in as admin
        self.login_user('admin', 'admin123')

        # Create food item
        res = self.client.post('/api/admin/foods', json={
            'name': 'Test Chicken Breast',
            'calories': 150,
            'protein': 30,
            'carbs': 0,
            'fat': 3
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        food_id = data['food_id']

        # Edit food item
        res = self.client.put(f'/api/admin/foods/{food_id}', json={
            'name': 'Test Chicken Breast (Grilled)',
            'calories': 160,
            'protein': 32,
            'carbs': 0,
            'fat': 4
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])

        # Verify edits persisted
        foods = db.get_all_foods()
        test_food = next((f for f in foods if f['id'] == food_id), None)
        self.assertIsNotNone(test_food)
        self.assertEqual(test_food['name'], 'Test Chicken Breast (Grilled)')
        self.assertEqual(test_food['calories_per_100g'], 160)

        # Delete food item
        res = self.client.delete(f'/api/admin/foods/{food_id}')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])

        # Verify delete persisted
        foods = db.get_all_foods()
        test_food = next((f for f in foods if f['id'] == food_id), None)
        self.assertIsNone(test_food)

    def test_admin_coaching_overrides_announcements(self):
        # Register user
        self.register_user('client_to_coach', 'pass123')
        user = self.get_user_by_username('client_to_coach')
        user_id = user['id']

        # Log in as admin
        self.login_user('admin', 'admin123')

        # Post global announcement
        res = self.client.post('/api/admin/announcement', json={
            'message': 'Maintenance scheduled at 2 AM.'
        })
        self.assertEqual(res.status_code, 200)

        # Send coaching advice note
        res = self.client.post('/api/admin/message', json={
            'receiver_id': user_id,
            'message': 'Keep eating more protein!'
        })
        self.assertEqual(res.status_code, 200)

        # Set custom macro overrides
        res = self.client.post('/api/admin/override', json={
            'user_id': user_id,
            'calories': 2500,
            'protein': 180,
            'carbs': 250,
            'fat': 80
        })
        self.assertEqual(res.status_code, 200)

        # Check user profile to ensure overrides are present
        coached_user = db.get_user_by_id(user_id)
        self.assertEqual(coached_user['custom_calories'], 2500)
        self.assertEqual(coached_user['custom_protein'], 180)

        # Clear custom macro overrides
        res = self.client.delete(f'/api/admin/override/{user_id}')
        self.assertEqual(res.status_code, 200)

        # Check profile to ensure overrides cleared
        coached_user = db.get_user_by_id(user_id)
        self.assertIsNone(coached_user['custom_calories'])

    def test_admin_audit_logs(self):
        # Log in as admin and perform an action
        self.login_user('admin', 'admin123')
        
        # Post announcement to generate audit log
        self.client.post('/api/admin/announcement', json={
            'message': 'Audit test announcement.'
        })

        # Fetch audit logs
        res = self.client.get('/api/admin/audit-logs')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertGreater(len(data['logs']), 0)
        
        # Verify first log contains announcement details
        first_log = data['logs'][0]
        self.assertEqual(first_log['action_type'], 'post_announcement')

    def test_exercise_logging(self):
        # Register and login a client
        self.register_user('exercise_user', 'pass123')
        self.login_user('exercise_user', 'pass123')
        user = self.get_user_by_username('exercise_user')
        user_id = user['id']

        # Update weight to 80.0 kg for calorie calculation testing
        conn = db.get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET weight_kg = 80.0, age = 30, height_cm = 180, gender = 'male' WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()

        # Log exercise with auto-estimation (Running METs = 8.0)
        # Calories = 8.0 * 3.5 * 80.0 / 200.0 * 30 mins = 336 kcal
        res = self.client.post('/api/user/exercise', json={
            'date_str': '2026-06-09',
            'activity_type': 'Running',
            'duration_min': 30
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['total_exercise_calories'], 336)
        self.assertEqual(len(data['logs']), 1)
        log_id = data['log_id']

        # Log custom exercise with manually specified calories (e.g. 150 kcal)
        res = self.client.post('/api/user/exercise', json={
            'date_str': '2026-06-09',
            'activity_type': 'Weight Lifting',
            'duration_min': 45,
            'calories_burned': 150
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['total_exercise_calories'], 486) # 336 + 150
        self.assertEqual(len(data['logs']), 2)

        # Check dashboard API to ensure exercises are included
        res = self.client.get('/api/user/dashboard?date=2026-06-09')
        self.assertEqual(res.status_code, 200)
        dash_data = json.loads(res.data)
        self.assertEqual(dash_data['total_exercise_calories'], 486)
        self.assertEqual(len(dash_data['exercise_logs']), 2)

        # Delete the first exercise log
        res = self.client.delete(f'/api/user/exercise/{log_id}')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['total_exercise_calories'], 150)
        self.assertEqual(len(data['logs']), 1)

    def test_onboarding_meal_plan_and_progress_intelligence(self):
        self.register_user('product_user', 'pass123')
        self.login_user('product_user', 'pass123')

        res = self.client.post('/api/onboarding', json={
            'dietary_style': 'high_protein',
            'allergies': ['shellfish'],
            'meal_schedule': 'standard',
            'region_cuisine': 'mediterranean',
            'coaching_level': 'weekly_coaching'
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['user']['onboarding_completed'])
        self.assertEqual(data['user']['allergies'], ['shellfish'])

        res = self.client.post('/api/calculate', json={
            'age': 34,
            'height_cm': 178,
            'weight_kg': 84,
            'gender': 'male',
            'activity': 'moderate',
            'goal': 'lose_mild'
        })
        self.assertEqual(res.status_code, 200)
        calc = json.loads(res.data)
        self.assertIn('standards', calc)
        self.assertIn('bmi_category', calc)
        self.assertGreaterEqual(calc['macros']['carbs']['percentage'], 45)

        res = self.client.post('/api/user/meal-plan', json={})
        self.assertEqual(res.status_code, 200)
        plan = json.loads(res.data)['meal_plan']
        self.assertEqual(len(plan['plan']['days']), 7)
        self.assertGreater(len(plan['shopping']), 0)

        res = self.client.get('/api/user/progress')
        self.assertEqual(res.status_code, 200)
        progress = json.loads(res.data)['progress']
        self.assertIn('adherence_score', progress)
        self.assertIn('why_weight_changed', progress)

    def test_food_logging_shortcuts_and_favorites(self):
        self.register_user('shortcut_user', 'pass123')
        self.login_user('shortcut_user', 'pass123')

        res = self.client.post('/api/user/food', json={
            'date_str': '2026-06-09',
            'food_name': 'Branded Protein Yogurt',
            'amount_g': 150,
            'calories': 160,
            'protein': 20,
            'carbs': 12,
            'fat': 3,
            'favorite': True
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertGreaterEqual(len(data['favorite_foods']), 1)

        res = self.client.get('/api/user/logging/shortcuts')
        self.assertEqual(res.status_code, 200)
        shortcuts = json.loads(res.data)
        self.assertGreaterEqual(len(shortcuts['recent_foods']), 1)
        self.assertIn('serving_units', shortcuts)

    def test_coach_assignment_thread_and_weekly_report(self):
        self.register_user('coached_client', 'pass123')
        user = self.get_user_by_username('coached_client')
        user_id = user['id']

        self.login_user('admin', 'admin123')
        res = self.client.post(f'/api/admin/users/{user_id}/coach', json={
            'coach_id': 1,
            'client_tags': ['weekly', 'fat-loss']
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['user']['client_tags'], ['weekly', 'fat-loss'])

        res = self.client.post(f'/api/admin/users/{user_id}/thread', json={
            'message': 'Please send your Sunday check-in.'
        })
        self.assertEqual(res.status_code, 200)

        res = self.client.get(f'/api/admin/users/{user_id}/weekly-report')
        self.assertEqual(res.status_code, 200)
        report = json.loads(res.data)['report']
        self.assertEqual(report['client']['username'], 'coached_client')
        self.assertIn('target_history', report)

    def test_profile_update(self):
        self.register_user('profile_updater', 'pass123')
        self.login_user('profile_updater', 'pass123')

        res = self.client.post('/api/profile', json={
            'full_name': 'John Doe',
            'email': 'john@example.com',
            'password': ''
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['user']['full_name'], 'John Doe')
        self.assertEqual(data['user']['email'], 'john@example.com')

        res = self.client.post('/api/profile', json={
            'full_name': 'John Doe',
            'email': 'john@example.com',
            'password': 'newpassword123'
        })
        self.assertEqual(res.status_code, 200)

        self.client.post('/api/auth/logout')
        res = self.client.post('/api/auth/login', json={
            'username': 'profile_updater',
            'password': 'newpassword123'
        })
        self.assertEqual(res.status_code, 200)

if __name__ == '__main__':
    unittest.main()
