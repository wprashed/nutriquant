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
        # Predefined food seeding should ensure at least 1000 foods
        foods = db.get_all_foods()
        self.assertGreaterEqual(len(foods), 1000)

    def test_subscription_tier_updates(self):
        # Register and login a normal client
        self.register_user('sub_user', 'pass123')
        self.login_user('sub_user', 'pass123')

        # Verify initial subscription tier is 'free'
        res = self.client.get('/api/profile')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['user']['subscription_tier'], 'free')

        # Update own subscription tier to premium
        res = self.client.post('/api/user/subscription', json={
            'subscription_tier': 'premium'
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['subscription_tier'], 'premium')

        # Check profile again to verify persistence
        res = self.client.get('/api/profile')
        data = json.loads(res.data)
        self.assertEqual(data['user']['subscription_tier'], 'premium')

        # Verify invalid tier validation
        res = self.client.post('/api/user/subscription', json={
            'subscription_tier': 'unlimited'
        })
        self.assertEqual(res.status_code, 400)

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

    def test_admin_update_subscription(self):
        # Register user
        self.register_user('client_to_upgrade', 'pass123')
        user = self.get_user_by_username('client_to_upgrade')
        user_id = user['id']

        # Log in as admin
        self.login_user('admin', 'admin123')

        # Upgrade user subscription tier
        res = self.client.post(f'/api/admin/users/{user_id}/tier', json={
            'subscription_tier': 'enterprise'
        })
        self.assertEqual(res.status_code, 200)

        # Verify subscription was persisted
        client_user = db.get_user_by_id(user_id)
        self.assertEqual(client_user['subscription_tier'], 'enterprise')

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

if __name__ == '__main__':
    unittest.main()
