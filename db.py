import sqlite3
import os
import json
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), 'nutriquant.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Initialises the database tables and schemas, including migrations and seeding."""
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            gender TEXT,
            height_cm REAL,
            weight_kg REAL,
            age INTEGER,
            activity TEXT,
            goal TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Run column migration check for 'is_admin'
    cursor.execute("PRAGMA table_info(users)")
    columns = [row['name'] for row in cursor.fetchall()]
    if 'is_admin' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
        conn.commit()
        
    # Run column migration check for custom target overrides
    cursor.execute("PRAGMA table_info(users)")
    columns = [row['name'] for row in cursor.fetchall()]
    for col in ['custom_calories', 'custom_protein', 'custom_carbs', 'custom_fat']:
        if col not in columns:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} INTEGER")
            conn.commit()
            
    # Run column migration check for subscription_tier
    cursor.execute("PRAGMA table_info(users)")
    columns = [row['name'] for row in cursor.fetchall()]
    if 'subscription_tier' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN subscription_tier TEXT DEFAULT 'free'")
        conn.commit()

    # Run column migration check for onboarding and coach workflow fields
    cursor.execute("PRAGMA table_info(users)")
    columns = [row['name'] for row in cursor.fetchall()]
    profile_columns = {
        'dietary_style': "TEXT DEFAULT 'balanced'",
        'allergies': "TEXT DEFAULT '[]'",
        'meal_schedule': "TEXT DEFAULT 'standard'",
        'region_cuisine': "TEXT DEFAULT 'global'",
        'coaching_level': "TEXT DEFAULT 'self_guided'",
        'coach_id': "INTEGER",
        'client_tags': "TEXT DEFAULT '[]'",
        'onboarding_completed': "INTEGER DEFAULT 0",
        'full_name': "TEXT",
        'email': "TEXT"
    }
    for col, definition in profile_columns.items():
        if col not in columns:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
            conn.commit()
    
    # 2. Weight Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weight_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            weight_kg REAL NOT NULL,
            logged_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, logged_at)
        )
    ''')
    
    # 3. Daily Intake Table (Water, Calories, Macros, Habit Checklist)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_intake (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            logged_date TEXT NOT NULL,
            water_ml INTEGER DEFAULT 0,
            calories INTEGER DEFAULT 0,
            protein INTEGER DEFAULT 0,
            carbs INTEGER DEFAULT 0,
            fat INTEGER DEFAULT 0,
            checklist TEXT DEFAULT '[]',
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, logged_date)
        )
    ''')
    
    # 4. Coaching Notes / Messages Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coaching_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER, -- NULL means global announcement
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # 6. Admin Audit Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            target_info TEXT,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # 5. Predefined Foods Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            calories_per_100g REAL NOT NULL,
            protein_per_100g REAL NOT NULL,
            carbs_per_100g REAL NOT NULL,
            fat_per_100g REAL NOT NULL
        )
    ''')
    
    # Seed predefined foods if empty or less than 6000 items
    cursor.execute("SELECT COUNT(*) FROM foods")
    if cursor.fetchone()[0] < 6000:
        cursor.execute("DELETE FROM foods")
        standard_foods = [
            ("Chicken Breast", 165.0, 31.0, 0.0, 3.6),
            ("White Rice (cooked)", 130.0, 2.7, 28.0, 0.3),
            ("Whole Eggs", 143.0, 12.6, 0.7, 9.5),
            ("Whole Milk", 61.0, 3.2, 4.8, 3.25),
            ("Banana", 89.0, 1.1, 22.8, 0.3),
            ("Apple", 52.0, 0.3, 13.8, 0.2),
            ("Avocado", 160.0, 2.0, 8.5, 14.7),
            ("Salmon Fillet", 206.0, 22.0, 0.0, 12.0),
            ("Oatmeal (cooked)", 71.0, 2.5, 12.0, 1.4),
            ("Almonds", 579.0, 21.2, 21.6, 49.9),
            ("Broccoli", 34.0, 2.8, 7.0, 0.4),
            ("Greek Yogurt (Plain)", 59.0, 10.0, 3.6, 0.4),
            ("Sweet Potato (baked)", 90.0, 2.0, 21.0, 0.1),
            ("Peanut Butter", 588.0, 25.0, 20.0, 50.0),
            ("Olive Oil", 884.0, 0.0, 0.0, 100.0)
        ]
        
        seen_names = set()
        foods_to_insert = []
        for name, cal, pro, carb, fat in standard_foods:
            seen_names.add(name)
            foods_to_insert.append((name, cal, pro, carb, fat))
            
        base_foods = [
            # --- MEAT ---
            ("Chicken Breast", "meat", 120.0, 22.5, 0.0, 2.5),
            ("Chicken Thigh", "meat", 150.0, 19.0, 0.0, 8.0),
            ("Chicken Wing", "meat", 190.0, 18.0, 0.0, 13.0),
            ("Turkey Breast", "meat", 104.0, 22.0, 0.0, 1.5),
            ("Beef Sirloin", "meat", 200.0, 21.0, 0.0, 12.0),
            ("Beef Ribeye", "meat", 290.0, 17.0, 0.0, 24.0),
            ("Beef Tenderloin", "meat", 220.0, 20.0, 0.0, 15.0),
            ("Ground Beef", "meat", 250.0, 18.0, 0.0, 19.0),
            ("Pork Chop", "meat", 190.0, 20.0, 0.0, 12.0),
            ("Pork Tenderloin", "meat", 143.0, 21.0, 0.0, 6.0),
            ("Lamb Chop", "meat", 230.0, 18.0, 0.0, 17.0),
            ("Venison", "meat", 150.0, 22.0, 0.0, 6.0),
            ("Bison", "meat", 145.0, 21.0, 0.0, 6.0),
            ("Duck Breast", "meat", 240.0, 16.0, 0.0, 19.0),
            ("Goat Meat", "meat", 143.0, 20.6, 0.0, 6.0),
            ("Veal Cutlet", "meat", 170.0, 20.0, 0.0, 9.0),
            ("Bacon", "meat", 400.0, 12.0, 1.0, 38.0),
            ("Ham", "meat", 145.0, 17.0, 1.5, 7.5),
            ("Pork Sausage", "meat", 320.0, 12.0, 2.0, 28.0),
            ("Beef Sausage", "meat", 330.0, 13.0, 2.0, 29.0),
            ("Beef Patty", "meat", 240.0, 19.0, 0.0, 18.0),
            ("Pork Belly", "meat", 518.0, 9.0, 0.0, 53.0),
            ("Lamb Shank", "meat", 200.0, 18.5, 0.0, 14.0),
            ("Chicken Giblets", "meat", 124.0, 18.0, 0.9, 5.0),
            ("Turkey Drumstick", "meat", 140.0, 20.0, 0.0, 6.5),
            ("Beef Brisket", "meat", 300.0, 16.5, 0.0, 26.0),
            ("Beef Liver", "meat", 135.0, 20.4, 3.9, 3.6),
            ("Pork Ribs", "meat", 280.0, 16.0, 0.0, 24.0),
            ("Salami Slice", "meat", 380.0, 22.0, 1.0, 32.0),
            ("Chorizo", "meat", 455.0, 24.0, 2.0, 38.0),
            ("Pheasant", "meat", 133.0, 22.3, 0.0, 4.3),
            ("Quail", "meat", 134.0, 21.8, 0.0, 4.5),
            ("Rabbit Meat", "meat", 136.0, 20.0, 0.0, 5.5),
            ("Venison Roast", "meat", 148.0, 22.0, 0.0, 6.0),
            ("Veal Chop", "meat", 165.0, 19.5, 0.0, 8.5),
            ("Pork Belly Slice", "meat", 518.0, 9.0, 0.0, 53.0),
            ("Pork Loin Roast", "meat", 170.0, 21.0, 0.0, 8.8),
            ("Beef Ribs", "meat", 290.0, 16.5, 0.0, 24.5),
            ("Beef Brisket Slab", "meat", 300.0, 16.5, 0.0, 26.0),
            ("Beef Flank", "meat", 165.0, 22.0, 0.0, 8.0),
            ("Beef Skirt", "meat", 220.0, 20.0, 0.0, 15.0),
            ("Beef Chuck", "meat", 250.0, 18.0, 0.0, 19.0),
            ("Beef Round", "meat", 180.0, 21.5, 0.0, 9.5),
            ("Beef Shank", "meat", 200.0, 20.2, 0.0, 12.5),
            ("Duck Leg", "meat", 210.0, 17.0, 0.0, 15.0),
            ("Goose Breast", "meat", 220.0, 18.0, 0.0, 16.0),
            ("Turkey Thigh", "meat", 145.0, 19.0, 0.0, 7.2),
            ("Turkey Wing", "meat", 160.0, 18.5, 0.0, 9.0),
            ("Turkey Sausage", "meat", 196.0, 15.0, 1.5, 14.0),
            ("Chicken Tenderloin", "meat", 110.0, 23.0, 0.0, 1.5),
            ("Chicken Drumstick", "meat", 155.0, 18.5, 0.0, 8.5),
            ("Chicken Gizzard", "meat", 94.0, 17.5, 0.0, 2.1),
            ("Chicken Heart", "meat", 153.0, 15.5, 0.0, 9.3),
            ("Pepperoni Slice", "meat", 500.0, 20.0, 1.0, 46.0),
            ("Prosciutto Slice", "meat", 230.0, 25.0, 0.5, 14.0),
            ("Pancetta Cube", "meat", 380.0, 15.0, 0.0, 35.0),
            ("Bratwurst", "meat", 300.0, 13.0, 2.0, 26.0),
            ("Mortadella", "meat", 310.0, 16.0, 1.0, 27.0),
            ("Capicola", "meat", 270.0, 20.0, 1.0, 21.0),
            ("Beef Jerky", "meat", 410.0, 33.0, 11.0, 25.0),
            ("Pork Rind", "meat", 544.0, 61.0, 0.0, 31.0),
            ("Pastrami", "meat", 147.0, 22.0, 1.5, 5.8),
            ("Corned Beef", "meat", 250.0, 18.0, 0.5, 19.0),
            ("Flank Steak", "meat", 165.0, 22.0, 0.0, 8.0),
            ("Skirt Steak", "meat", 220.0, 20.0, 0.0, 15.0),

            # --- SEAFOOD ---
            ("Salmon Fillet", "seafood", 180.0, 20.0, 0.0, 11.0),
            ("Tuna Steak", "seafood", 130.0, 26.0, 0.0, 2.0),
            ("Cod Fillet", "seafood", 82.0, 18.0, 0.0, 0.7),
            ("Halibut", "seafood", 110.0, 21.0, 0.0, 2.3),
            ("Trout", "seafood", 140.0, 20.0, 0.0, 6.0),
            ("Mackerel", "seafood", 205.0, 19.0, 0.0, 14.0),
            ("Sardines", "seafood", 208.0, 25.0, 0.0, 11.0),
            ("Sea Bass", "seafood", 97.0, 18.4, 0.0, 2.0),
            ("Red Snapper", "seafood", 100.0, 20.5, 0.0, 1.3),
            ("Tilapia", "seafood", 96.0, 20.0, 0.0, 1.7),
            ("Shrimp", "seafood", 85.0, 20.0, 0.0, 0.5),
            ("Crab Meat", "seafood", 83.0, 18.0, 0.0, 0.9),
            ("Lobster", "seafood", 89.0, 19.0, 1.3, 0.9),
            ("Scallops", "seafood", 111.0, 20.5, 3.0, 0.8),
            ("Squid / Calamari", "seafood", 92.0, 15.6, 3.0, 1.4),
            ("Octopus", "seafood", 82.0, 14.9, 2.2, 1.0),
            ("Oysters", "seafood", 81.0, 9.0, 5.0, 2.3),
            ("Clams", "seafood", 74.0, 12.8, 2.6, 1.0),
            ("Mussels", "seafood", 86.0, 11.9, 3.7, 2.2),
            ("Anchovies", "seafood", 131.0, 20.0, 0.0, 4.8),
            ("Caviar", "seafood", 264.0, 24.6, 4.0, 17.9),
            ("Herring", "seafood", 158.0, 18.0, 0.0, 9.0),
            ("Swordfish", "seafood", 144.0, 20.0, 0.0, 6.7),
            ("Red Snapper Fillet", "seafood", 100.0, 20.5, 0.0, 1.3),
            ("Whitefish", "seafood", 134.0, 19.0, 0.0, 5.9),
            ("Shrimp Paste", "seafood", 120.0, 15.0, 5.0, 1.5),
            ("Fish Cake", "seafood", 140.0, 12.0, 15.0, 4.0),
            ("Prawns", "seafood", 85.0, 20.0, 0.0, 0.5),
            ("King Crab Leg", "seafood", 97.0, 19.0, 0.0, 1.5),
            ("Snow Crab", "seafood", 90.0, 18.5, 0.0, 1.2),
            ("Crayfish", "seafood", 77.0, 16.0, 0.0, 1.0),
            ("Sea Scallop", "seafood", 111.0, 20.5, 3.0, 0.8),
            ("Bay Scallop", "seafood", 88.0, 17.0, 2.5, 0.7),
            ("Calamari Ring", "seafood", 92.0, 15.6, 3.0, 1.4),
            ("Baby Squid", "seafood", 92.0, 15.6, 3.0, 1.4),
            ("Baby Octopus", "seafood", 82.0, 14.9, 2.2, 1.0),
            ("Rock Oyster", "seafood", 81.0, 9.0, 5.0, 2.3),
            ("Blue Mussel", "seafood", 86.0, 11.9, 3.7, 2.2),
            ("Hard Clam", "seafood", 74.0, 12.8, 2.6, 1.0),
            ("Soft Clam", "seafood", 74.0, 12.8, 2.6, 1.0),
            ("Perch Fillet", "seafood", 91.0, 18.6, 0.0, 1.2),
            ("Catfish Fillet", "seafood", 119.0, 15.0, 0.0, 6.0),
            ("Pollock Fillet", "seafood", 92.0, 19.0, 0.0, 1.0),
            ("Mahi Mahi Fillet", "seafood", 85.0, 18.5, 0.0, 0.7),
            ("Swordfish Steak", "seafood", 144.0, 20.0, 0.0, 6.7),
            ("Grouper Fillet", "seafood", 92.0, 19.0, 0.0, 1.0),
            ("Flounder Fillet", "seafood", 91.0, 18.8, 0.0, 1.2),
            ("Sole Fillet", "seafood", 91.0, 18.8, 0.0, 1.2),
            ("Haddock Fillet", "seafood", 90.0, 19.0, 0.0, 0.9),
            ("Snapper Fillet", "seafood", 100.0, 20.5, 0.0, 1.3),
            ("Mullet", "seafood", 117.0, 19.4, 0.0, 3.8),
            ("Turbot", "seafood", 95.0, 16.0, 0.0, 3.0),
            ("Black Cod", "seafood", 250.0, 15.0, 0.0, 20.0),
            ("Sea Bream", "seafood", 96.0, 19.0, 0.0, 1.9),
            ("John Dory", "seafood", 95.0, 20.0, 0.0, 1.0),
            ("Monkfish", "seafood", 76.0, 14.5, 0.0, 1.5),
            ("Octopus Arm", "seafood", 82.0, 14.9, 2.2, 1.0),
            ("Sea Urchin Roe", "seafood", 120.0, 16.0, 5.0, 4.0),
            ("Pike Fillet", "seafood", 88.0, 19.0, 0.0, 0.7),
            ("Carp Fillet", "seafood", 127.0, 18.0, 0.0, 5.6),

            # --- GRAIN ---
            ("White Rice", "grain", 360.0, 7.0, 79.0, 0.6),
            ("Brown Rice", "grain", 350.0, 8.0, 73.0, 2.5),
            ("Jasmine Rice", "grain", 356.0, 7.0, 78.0, 0.8),
            ("Basmati Rice", "grain", 355.0, 8.5, 77.0, 1.0),
            ("Quinoa", "grain", 368.0, 14.0, 64.0, 6.0),
            ("Rolled Oats", "grain", 389.0, 16.9, 66.0, 6.9),
            ("Barley", "grain", 354.0, 12.5, 73.0, 2.3),
            ("Millet", "grain", 378.0, 11.0, 73.0, 4.2),
            ("Couscous", "grain", 376.0, 12.8, 77.0, 0.6),
            ("Buckwheat", "grain", 343.0, 13.0, 72.0, 3.4),
            ("Semolina Pasta", "grain", 355.0, 12.5, 73.0, 1.5),
            ("Whole Wheat Pasta", "grain", 348.0, 14.6, 68.0, 2.5),
            ("Gnocchi", "grain", 186.0, 3.5, 41.0, 0.5),
            ("Polenta", "grain", 340.0, 8.0, 74.0, 1.0),
            ("Bulgur Wheat", "grain", 342.0, 12.3, 76.0, 1.3),
            ("Wild Rice", "grain", 357.0, 14.7, 75.0, 1.1),
            ("White Bread", "grain", 265.0, 9.0, 49.0, 3.2),
            ("Whole Wheat Bread", "grain", 247.0, 13.0, 41.0, 3.4),
            ("Rye Bread", "grain", 259.0, 8.5, 48.0, 3.3),
            ("Sourdough Bread", "grain", 290.0, 10.0, 56.0, 1.2),
            ("Pita Bread", "grain", 275.0, 9.0, 56.0, 1.2),
            ("Flour Tortilla", "grain", 310.0, 8.0, 50.0, 8.0),
            ("Corn Tortilla", "grain", 218.0, 5.7, 44.0, 2.8),
            ("Bagel", "grain", 270.0, 10.0, 53.0, 1.5),
            ("Arborio Rice", "grain", 355.0, 7.0, 80.0, 0.5),
            ("Red Rice", "grain", 355.0, 7.5, 75.0, 2.0),
            ("Black Rice", "grain", 340.0, 8.5, 72.0, 3.0),
            ("Carnaroli Rice", "grain", 355.0, 7.0, 80.0, 0.5),
            ("Glutinous Rice", "grain", 350.0, 6.5, 78.0, 0.5),
            ("Sushi Rice", "grain", 350.0, 6.5, 78.0, 0.5),
            ("Steel Cut Oats", "grain", 375.0, 12.5, 68.0, 6.0),
            ("Instant Oats", "grain", 370.0, 12.0, 66.0, 6.0),
            ("Oat Bran", "grain", 246.0, 17.0, 66.0, 7.0),
            ("Wheat Bran", "grain", 216.0, 15.0, 64.0, 4.2),
            ("Wheat Germ", "grain", 360.0, 23.0, 52.0, 10.0),
            ("Farro", "grain", 360.0, 12.0, 72.0, 2.0),
            ("Spelt", "grain", 338.0, 14.5, 70.0, 2.4),
            ("Teff", "grain", 367.0, 13.3, 73.0, 2.4),
            ("Amaranth", "grain", 371.0, 13.6, 65.0, 7.0),
            ("Sorghum", "grain", 339.0, 11.3, 75.0, 3.3),
            ("Kamut", "grain", 337.0, 14.5, 70.0, 2.0),
            ("Naan Bread", "grain", 310.0, 9.0, 52.0, 6.0),
            ("Brioche Bread", "grain", 360.0, 10.0, 48.0, 14.0),
            ("Focaccia Bread", "grain", 250.0, 8.0, 42.0, 8.0),
            ("Ciabatta Bread", "grain", 260.0, 9.0, 52.0, 2.0),
            ("Pumpernickel Bread", "grain", 250.0, 9.0, 48.0, 3.0),
            ("Challah Bread", "grain", 290.0, 9.0, 52.0, 6.0),
            ("Cornbread", "grain", 300.0, 7.0, 46.0, 10.0),
            ("English Muffin", "grain", 230.0, 8.0, 45.0, 1.5),
            ("Crumpet", "grain", 175.0, 6.0, 36.0, 1.0),
            ("Taco Shell", "grain", 470.0, 6.0, 60.0, 22.0),
            ("Udon Noodles", "grain", 130.0, 3.5, 28.0, 0.5),
            ("Soba Noodles", "grain", 340.0, 14.0, 70.0, 1.5),
            ("Ramen Noodles", "grain", 436.0, 10.0, 63.0, 16.0),
            ("Rice Vermicelli", "grain", 350.0, 6.0, 80.0, 0.5),
            ("Egg Noodles", "grain", 380.0, 14.0, 70.0, 4.5),
            ("Orzo", "grain", 355.0, 12.0, 73.0, 1.5),
            ("Pappardelle", "grain", 355.0, 12.0, 73.0, 1.5),
            ("Macaroni", "grain", 355.0, 12.0, 73.0, 1.5),
            ("Fettuccine", "grain", 355.0, 12.0, 73.0, 1.5),

            # --- VEGETABLE ---
            ("Broccoli", "vegetable", 34.0, 2.8, 6.6, 0.4),
            ("Cauliflower", "vegetable", 25.0, 1.9, 5.0, 0.3),
            ("Spinach", "vegetable", 23.0, 2.9, 3.6, 0.4),
            ("Kale", "vegetable", 49.0, 4.3, 8.8, 0.9),
            ("Brussels Sprouts", "vegetable", 43.0, 3.4, 9.0, 0.3),
            ("Asparagus", "vegetable", 20.0, 2.2, 3.9, 0.1),
            ("Green Beans", "vegetable", 31.0, 1.8, 7.0, 0.2),
            ("Green Peas", "vegetable", 81.0, 5.4, 14.4, 0.4),
            ("Sweet Corn", "vegetable", 86.0, 3.2, 19.0, 1.2),
            ("Carrot", "vegetable", 41.0, 0.9, 9.6, 0.2),
            ("Russet Potato", "vegetable", 79.0, 2.0, 18.0, 0.1),
            ("Sweet Potato", "vegetable", 86.0, 1.6, 20.0, 0.1),
            ("Zucchini", "vegetable", 17.0, 1.2, 3.1, 0.3),
            ("Eggplant", "vegetable", 25.0, 1.0, 6.0, 0.2),
            ("Bell Pepper", "vegetable", 20.0, 0.9, 4.6, 0.2),
            ("Tomato", "vegetable", 18.0, 0.9, 3.9, 0.2),
            ("Yellow Onion", "vegetable", 40.0, 1.1, 9.3, 0.1),
            ("White Mushroom", "vegetable", 22.0, 3.1, 3.3, 0.3),
            ("Celery", "vegetable", 16.0, 0.7, 3.0, 0.2),
            ("Cucumber", "vegetable", 15.0, 0.7, 3.6, 0.1),
            ("Cabbage", "vegetable", 25.0, 1.3, 5.8, 0.1),
            ("Radish", "vegetable", 16.0, 0.7, 3.4, 0.1),
            ("Beetroot", "vegetable", 43.0, 1.6, 9.6, 0.2),
            ("Butternut Squash", "vegetable", 45.0, 1.0, 11.7, 0.1),
            ("Artichoke", "vegetable", 47.0, 3.3, 10.5, 0.2),
            ("Leek", "vegetable", 61.0, 1.5, 14.2, 0.3),
            ("Okra", "vegetable", 33.0, 1.9, 7.5, 0.2),
            ("Parsnip", "vegetable", 75.0, 1.2, 18.0, 0.3),
            ("Turnip", "vegetable", 28.0, 0.9, 6.4, 0.1),
            ("Watercress", "vegetable", 11.0, 2.3, 1.3, 0.1),
            ("Bamboo Shoots", "vegetable", 27.0, 2.6, 5.2, 0.3),
            ("Bok Choy", "vegetable", 13.0, 1.5, 2.2, 0.2),
            ("Swiss Chard", "vegetable", 19.0, 1.8, 3.7, 0.2),
            ("Ginger Root", "vegetable", 80.0, 1.8, 17.8, 0.8),
            ("Garlic Clove", "vegetable", 149.0, 6.4, 33.0, 0.5),
            ("Shallot", "vegetable", 72.0, 2.5, 16.8, 0.1),
            ("Fennel Bulb", "vegetable", 31.0, 1.2, 7.3, 0.2),
            ("Endive Leaf", "vegetable", 17.0, 1.2, 3.4, 0.2),
            ("Escarole", "vegetable", 17.0, 1.2, 3.4, 0.2),
            ("Radicchio", "vegetable", 23.0, 1.4, 4.5, 0.2),
            ("Arugula", "vegetable", 25.0, 2.6, 3.7, 0.7),
            ("Water Chestnut", "vegetable", 97.0, 1.4, 23.9, 0.1),
            ("Hearts of Palm", "vegetable", 115.0, 2.7, 25.6, 0.2),
            ("Jicama", "vegetable", 38.0, 0.7, 8.8, 0.1),
            ("Kohlrabi", "vegetable", 27.0, 1.7, 6.2, 0.1),
            ("Rutabaga", "vegetable", 37.0, 1.1, 8.6, 0.2),
            ("Daikon Radish", "vegetable", 18.0, 0.6, 4.1, 0.1),
            ("Parsley", "vegetable", 36.0, 3.0, 6.3, 0.8),
            ("Cilantro", "vegetable", 23.0, 2.1, 3.7, 0.5),
            ("Basil Leaf", "vegetable", 23.0, 3.2, 2.7, 0.6),
            ("Mint Leaf", "vegetable", 44.0, 3.3, 8.4, 0.7),
            ("Dill", "vegetable", 43.0, 3.5, 7.0, 1.1),
            ("Rosemary", "vegetable", 131.0, 3.3, 20.7, 5.9),
            ("Thyme", "vegetable", 101.0, 5.6, 24.4, 1.7),
            ("Oregano", "vegetable", 265.0, 9.0, 68.9, 4.3),
            ("Sage", "vegetable", 315.0, 10.6, 60.7, 12.7),
            ("Chives", "vegetable", 30.0, 3.3, 4.3, 0.7),
            ("Green Onion", "vegetable", 32.0, 1.8, 7.3, 0.2),
            ("Leek Stalk", "vegetable", 61.0, 1.5, 14.2, 0.3),
            ("Bok Choy Cabbage", "vegetable", 13.0, 1.5, 2.2, 0.2),
            ("Red Cabbage", "vegetable", 31.0, 1.4, 7.4, 0.2),
            ("Napa Cabbage", "vegetable", 16.0, 1.2, 3.2, 0.25),
            ("Savoy Cabbage", "vegetable", 27.0, 2.0, 6.1, 0.1),
            ("Seaweed / Kelp", "vegetable", 43.0, 1.7, 9.6, 0.6),
            ("Portobello Mushroom", "vegetable", 22.0, 2.1, 3.9, 0.3),
            ("Shiitake Mushroom", "vegetable", 34.0, 2.2, 6.8, 0.5),
            ("Oyster Mushroom", "vegetable", 33.0, 3.3, 6.1, 0.4),
            ("Enoki Mushroom", "vegetable", 37.0, 2.7, 7.8, 0.3),
            ("Alfalfa Sprouts", "vegetable", 23.0, 4.0, 2.1, 0.7),
            ("Bean Sprouts", "vegetable", 30.0, 3.0, 6.0, 0.2),
            ("Yam", "vegetable", 118.0, 1.5, 27.9, 0.25),

            # --- FRUIT ---
            ("Banana", "fruit", 89.0, 1.1, 22.8, 0.3),
            ("Apple", "fruit", 52.0, 0.3, 13.8, 0.2),
            ("Pear", "fruit", 57.0, 0.4, 15.0, 0.1),
            ("Orange", "fruit", 47.0, 0.9, 11.8, 0.1),
            ("Grapefruit", "fruit", 42.0, 0.8, 10.7, 0.1),
            ("Strawberries", "fruit", 32.0, 0.7, 7.7, 0.3),
            ("Blueberries", "fruit", 57.0, 0.7, 14.5, 0.3),
            ("Raspberries", "fruit", 52.0, 1.2, 11.9, 0.7),
            ("Blackberries", "fruit", 43.0, 1.4, 9.6, 0.5),
            ("Red Grapes", "fruit", 69.0, 0.7, 18.1, 0.25),
            ("Peach", "fruit", 39.0, 0.9, 9.5, 0.3),
            ("Plum", "fruit", 46.0, 0.7, 11.4, 0.3),
            ("Cherry", "fruit", 50.0, 1.0, 12.0, 0.3),
            ("Mango", "fruit", 60.0, 0.8, 15.0, 0.4),
            ("Pineapple", "fruit", 50.0, 0.5, 13.1, 0.1),
            ("Kiwi", "fruit", 61.0, 1.1, 14.7, 0.5),
            ("Watermelon", "fruit", 30.0, 0.6, 7.6, 0.2),
            ("Cantaloupe", "fruit", 34.0, 0.8, 8.2, 0.2),
            ("Avocado", "fruit", 160.0, 2.0, 8.5, 14.7),
            ("Lemon", "fruit", 29.0, 1.1, 9.3, 0.3),
            ("Lime", "fruit", 30.0, 0.7, 10.5, 0.2),
            ("Pomegranate", "fruit", 83.0, 1.7, 18.7, 1.2),
            ("Fresh Fig", "fruit", 74.0, 0.8, 19.2, 0.3),
            ("Medjool Date", "fruit", 277.0, 1.8, 75.0, 0.2),
            ("Blackcurrant", "fruit", 63.0, 1.4, 15.4, 0.4),
            ("Elderberry", "fruit", 73.0, 0.7, 18.4, 0.5),
            ("Gooseberry", "fruit", 44.0, 0.9, 10.2, 0.6),
            ("Guava", "fruit", 68.0, 2.6, 14.3, 1.0),
            ("Lychee", "fruit", 66.0, 0.8, 16.5, 0.4),
            ("Passion Fruit", "fruit", 97.0, 2.2, 23.4, 0.7),
            ("Persimmon", "fruit", 70.0, 0.8, 18.6, 0.2),
            ("Quince", "fruit", 57.0, 0.4, 15.3, 0.1),
            ("Tamarind", "fruit", 239.0, 2.8, 62.5, 0.6),
            ("Starfruit", "fruit", 31.0, 1.0, 6.7, 0.3),
            ("Nectarine", "fruit", 44.0, 1.1, 10.6, 0.3),
            ("Apricot", "fruit", 48.0, 1.4, 11.1, 0.4),
            ("Mandarin Orange", "fruit", 53.0, 0.8, 13.3, 0.3),
            ("Clementine", "fruit", 47.0, 0.9, 12.0, 0.1),
            ("Satsuma", "fruit", 53.0, 0.8, 13.3, 0.3),
            ("Cranberries", "fruit", 46.0, 0.4, 12.2, 0.1),
            ("Red Currant", "fruit", 56.0, 1.4, 13.8, 0.2),
            ("White Currant", "fruit", 56.0, 1.4, 13.8, 0.2),
            ("Papaya", "fruit", 43.0, 0.5, 10.8, 0.3),
            ("Dragon Fruit", "fruit", 60.0, 1.2, 12.9, 1.5),
            ("Rambutan", "fruit", 82.0, 0.9, 20.9, 0.2),
            ("Mangosteen", "fruit", 73.0, 0.4, 18.0, 0.6),
            ("Coconut Meat", "fruit", 354.0, 3.3, 15.2, 33.5),
            ("Coconut Water Fruit", "fruit", 19.0, 0.7, 3.7, 0.2),
            ("Honeydew Melon", "fruit", 36.0, 0.5, 9.0, 0.1),
            ("Kano Melon", "fruit", 34.0, 0.8, 8.2, 0.2),
            ("Soursop", "fruit", 66.0, 1.0, 16.8, 0.3),
            ("Jackfruit", "fruit", 95.0, 1.7, 23.2, 0.6),
            ("Breadfruit", "fruit", 103.0, 1.1, 27.1, 0.2),
            ("Durian", "fruit", 147.0, 1.5, 27.1, 5.3),
            ("Loquat", "fruit", 47.0, 0.4, 12.1, 0.2),
            ("Kumquat", "fruit", 71.0, 1.9, 15.9, 0.9),
            ("Mulberry", "fruit", 43.0, 1.4, 9.8, 0.4),
            ("Boysenberry", "fruit", 50.0, 1.1, 12.2, 0.3),
            ("Honeydew Melon Slice", "fruit", 36.0, 0.5, 9.0, 0.1),
            ("Black Cherry", "fruit", 50.0, 1.0, 12.0, 0.3),
            ("White Grapes", "fruit", 69.0, 0.7, 18.1, 0.2),

            # --- DAIRY ---
            ("Whole Milk", "dairy", 61.0, 3.2, 4.8, 3.25),
            ("Semi-Skimmed Milk", "dairy", 50.0, 3.4, 4.8, 1.8),
            ("Skim Milk", "dairy", 35.0, 3.4, 5.0, 0.1),
            ("Greek Yogurt (Plain)", "dairy", 59.0, 10.0, 3.6, 0.4),
            ("Low-Fat Greek Yogurt", "dairy", 73.0, 10.0, 4.0, 2.0),
            ("Low-Fat Yogurt", "dairy", 63.0, 5.3, 7.0, 1.55),
            ("Cottage Cheese", "dairy", 98.0, 11.1, 3.4, 4.3),
            ("Cheddar Cheese", "dairy", 403.0, 25.0, 1.3, 33.0),
            ("Mozzarella Cheese", "dairy", 280.0, 22.0, 2.2, 20.0),
            ("Parmesan Cheese", "dairy", 431.0, 38.0, 4.1, 29.0),
            ("Feta Cheese", "dairy", 264.0, 14.0, 4.1, 21.0),
            ("Cream Cheese", "dairy", 342.0, 6.0, 4.1, 34.0),
            ("Swiss Cheese", "dairy", 380.0, 27.0, 1.5, 28.0),
            ("Provolone Cheese", "dairy", 351.0, 25.6, 2.1, 26.6),
            ("Butter", "dairy", 717.0, 0.9, 0.1, 81.0),
            ("Heavy Whipping Cream", "dairy", 340.0, 2.8, 2.7, 36.0),
            ("Sour Cream", "dairy", 198.0, 2.4, 4.6, 19.0),
            ("Soy Milk", "dairy", 43.0, 3.3, 4.0, 1.8),
            ("Almond Milk (Unsweetened)", "dairy", 15.0, 0.5, 0.3, 1.1),
            ("Oat Milk", "dairy", 50.0, 1.0, 7.0, 1.5),
            ("Blue Cheese", "dairy", 353.0, 21.0, 2.3, 29.0),
            ("Colby Cheese", "dairy", 394.0, 23.8, 2.6, 32.0),
            ("Gouda Cheese", "dairy", 356.0, 25.0, 2.2, 27.0),
            ("Havarti Cheese", "dairy", 371.0, 21.4, 2.9, 30.0),
            ("Mascarpone", "dairy", 429.0, 5.7, 4.3, 45.7),
            ("Ricotta Cheese", "dairy", 174.0, 11.0, 3.0, 13.0),
            ("Clotted Cream", "dairy", 586.0, 1.7, 2.4, 63.5),
            ("Cashew Milk", "dairy", 25.0, 1.0, 1.0, 2.0),
            ("Goat Milk", "dairy", 69.0, 3.6, 4.5, 4.1),
            ("Sheep Milk", "dairy", 108.0, 6.0, 5.4, 7.0),
            ("Buffalo Milk", "dairy", 97.0, 3.8, 5.2, 6.9),
            ("Camel Milk", "dairy", 50.0, 3.0, 4.0, 2.5),
            ("Skyr (Plain)", "dairy", 65.0, 11.0, 4.0, 0.2),
            ("Kefir (Plain)", "dairy", 60.0, 3.5, 4.0, 3.0),
            ("Buttermilk", "dairy", 40.0, 3.3, 4.8, 0.9),
            ("Ghee", "dairy", 900.0, 0.0, 0.0, 100.0),
            ("Clarified Butter", "dairy", 900.0, 0.0, 0.0, 100.0),
            ("Half and Half Cream", "dairy", 130.0, 3.0, 4.3, 11.5),
            ("Evaporated Milk Can", "dairy", 134.0, 6.8, 10.0, 7.6),
            ("Condensed Milk Can", "dairy", 321.0, 7.9, 54.0, 8.7),
            ("Powdered Milk", "dairy", 496.0, 26.3, 38.4, 26.7),
            ("Gorgonzola Cheese", "dairy", 353.0, 21.0, 2.3, 29.0),
            ("Brie Cheese", "dairy", 334.0, 20.7, 0.5, 27.7),
            ("Camembert Cheese", "dairy", 300.0, 19.8, 0.5, 24.3),
            ("Monterey Jack Cheese", "dairy", 373.0, 24.5, 0.7, 30.3),
            ("Pepper Jack Cheese", "dairy", 373.0, 24.5, 0.7, 30.3),
            ("Pecorino Romano Cheese", "dairy", 387.0, 25.0, 1.5, 31.8),
            ("Gruyere Cheese", "dairy", 413.0, 29.8, 0.4, 32.3),
            ("Paneer Cheese", "dairy", 265.0, 18.0, 3.0, 20.0),
            ("Halloumi Cheese", "dairy", 320.0, 21.0, 2.0, 26.0),
            ("Ricotta Salata", "dairy", 270.0, 16.0, 3.0, 21.0),
            ("Neufchatel Cheese", "dairy", 253.0, 9.0, 3.5, 23.0),
            ("Queso Fresco", "dairy", 290.0, 18.0, 3.0, 23.0),
            ("Gjetost Cheese", "dairy", 466.0, 10.0, 43.0, 29.0),
            ("Provolone Cheese Slice", "dairy", 351.0, 25.6, 2.1, 26.6),
            ("Swiss Cheese Slice", "dairy", 380.0, 27.0, 1.5, 28.0),
            ("Mozzarella Ball", "dairy", 280.0, 22.0, 2.2, 20.0),
            ("Parmesan Grated", "dairy", 431.0, 38.0, 4.1, 29.0),
            ("Feta Block", "dairy", 264.0, 14.0, 4.1, 21.0),
            ("Cottage Cheese 2%", "dairy", 81.0, 10.4, 4.7, 2.3),

            # --- NUT ---
            ("Almonds", "nut", 579.0, 21.2, 21.6, 49.9),
            ("Walnuts", "nut", 654.0, 15.2, 13.7, 65.2),
            ("Cashews", "nut", 553.0, 18.2, 30.2, 43.8),
            ("Pistachios", "nut", 562.0, 20.0, 27.5, 45.4),
            ("Pecans", "nut", 691.0, 9.2, 13.9, 72.0),
            ("Peanuts", "nut", 567.0, 25.8, 16.1, 49.2),
            ("Macadamia Nuts", "nut", 718.0, 7.9, 13.8, 75.8),
            ("Chia Seeds", "nut", 486.0, 16.5, 42.1, 30.7),
            ("Flax Seeds", "nut", 534.0, 18.3, 28.9, 42.2),
            ("Pumpkin Seeds", "nut", 559.0, 30.2, 10.7, 49.0),
            ("Sunflower Seeds", "nut", 584.0, 20.8, 20.0, 51.5),
            ("Sesame Seeds", "nut", 573.0, 17.7, 23.4, 49.7),
            ("Brazil Nuts", "nut", 656.0, 14.3, 12.3, 66.4),
            ("Hazelnut", "nut", 628.0, 15.0, 16.7, 60.8),
            ("Pine Nuts", "nut", 673.0, 13.7, 13.1, 68.4),
            ("Hemp Seeds", "nut", 553.0, 31.6, 8.7, 48.8),
            ("Poppy Seeds", "nut", 525.0, 18.0, 28.0, 41.5),
            ("Chestnuts", "nut", 131.0, 2.0, 28.0, 1.2),
            ("Butternuts", "nut", 612.0, 24.9, 12.0, 57.0),
            ("Acorn Squash Seeds", "nut", 559.0, 30.2, 10.7, 49.0),
            ("Watermelon Seeds", "nut", 557.0, 28.3, 15.3, 47.4),
            ("Cacao Nibs", "nut", 600.0, 12.0, 30.0, 50.0),
            ("Lotus Seeds", "nut", 332.0, 15.4, 64.0, 2.0),
            ("Ginkgo Nuts", "nut", 182.0, 4.3, 37.6, 1.7),
            ("Tiger Nuts", "nut", 400.0, 7.0, 60.0, 25.0),
            ("Sacha Inchi", "nut", 600.0, 30.0, 10.0, 50.0),
            ("Pili Nuts", "nut", 719.0, 10.8, 4.0, 79.8),
            ("Mongongo Nuts", "nut", 620.0, 24.0, 10.0, 57.0),
            ("Kola Nuts", "nut", 90.0, 2.0, 20.0, 0.5),
            ("Candlenuts", "nut", 650.0, 8.0, 18.0, 63.0),
            ("Beechnuts", "nut", 570.0, 19.0, 33.0, 50.0),
            ("Acorns", "nut", 387.0, 6.0, 41.0, 24.0),
            ("Hickory Nuts", "nut", 657.0, 12.7, 18.3, 64.3),
            ("Safflower Seeds", "nut", 517.0, 16.2, 34.3, 38.5),
            ("Squash Seeds", "nut", 559.0, 30.2, 10.7, 49.0),
            ("Apricot Kernels", "nut", 600.0, 25.0, 15.0, 50.0),
            ("Peach Kernels", "nut", 600.0, 25.0, 15.0, 50.0),
            ("Plum Kernels", "nut", 600.0, 25.0, 15.0, 50.0),
            ("Cherry Kernels", "nut", 600.0, 25.0, 15.0, 50.0),
            ("Melon Seeds", "nut", 557.0, 28.3, 15.3, 47.4),

            # --- SNACK ---
            ("Potato Chips", "snack", 536.0, 7.0, 53.0, 35.0),
            ("Tortilla Chips", "snack", 497.0, 7.0, 65.0, 24.0),
            ("Pretzels", "snack", 380.0, 10.0, 80.0, 3.0),
            ("Popcorn (Air-Popped)", "snack", 387.0, 12.9, 78.0, 4.5),
            ("Wheat Crackers", "snack", 450.0, 8.0, 68.0, 18.0),
            ("Chocolate Chip Cookie", "snack", 490.0, 5.0, 62.0, 25.0),
            ("Oatmeal Raisin Cookie", "snack", 435.0, 6.0, 69.0, 15.0),
            ("Chocolate Brownie", "snack", 466.0, 5.0, 60.0, 23.0),
            ("Milk Chocolate Bar", "snack", 535.0, 7.6, 59.4, 29.7),
            ("Dark Chocolate (70%)", "snack", 598.0, 7.8, 45.9, 42.6),
            ("Gummy Bears", "snack", 343.0, 6.9, 77.0, 0.1),
            ("Vanilla Ice Cream", "snack", 207.0, 3.5, 24.0, 11.0),
            ("Chocolate Ice Cream", "snack", 216.0, 3.8, 28.0, 11.0),
            ("Glazed Donut", "snack", 426.0, 4.9, 51.0, 22.0),
            ("Blueberry Muffin", "snack", 377.0, 5.3, 54.0, 16.0),
            ("Pancake", "snack", 227.0, 6.0, 28.0, 10.0),
            ("Waffle", "snack", 291.0, 7.9, 33.0, 14.0),
            ("Croissant", "snack", 406.0, 8.2, 46.0, 21.0),
            ("Pretzel Sticks", "snack", 380.0, 10.0, 80.0, 3.0),
            ("Graham Crackers", "snack", 429.0, 7.1, 78.6, 10.7),
            ("Vanilla Wafer", "snack", 467.0, 4.8, 73.8, 16.7),
            ("Fruit Roll-up", "snack", 375.0, 0.0, 87.5, 4.2),
            ("Rice Cakes", "snack", 387.0, 8.2, 81.3, 2.8),
            ("Granola Bar", "snack", 432.0, 8.0, 65.0, 15.0),
            ("Veggie Chips", "snack", 480.0, 5.0, 64.0, 22.0),
            ("Kale Chips", "snack", 420.0, 15.0, 30.0, 25.0),
            ("Pita Chips", "snack", 450.0, 9.0, 70.0, 13.0),
            ("Cheese Crackers", "snack", 500.0, 10.0, 56.0, 25.0),
            ("Animal Crackers", "snack", 440.0, 7.0, 78.0, 10.0),
            ("Shortbread Cookie", "snack", 500.0, 5.0, 60.0, 25.0),
            ("Gingerbread Cookie", "snack", 420.0, 5.0, 72.0, 12.0),
            ("Macaron", "snack", 450.0, 7.0, 70.0, 16.0),
            ("Eclair", "snack", 262.0, 4.8, 30.0, 13.8),
            ("Cream Puff", "snack", 262.0, 4.8, 30.0, 13.8),
            ("Fruit Tart", "snack", 280.0, 3.0, 42.0, 11.0),
            ("Apple Pie Slice", "snack", 237.0, 2.0, 38.0, 9.0),
            ("Pecan Pie Slice", "snack", 410.0, 4.8, 52.0, 21.0),
            ("Pumpkin Pie Slice", "snack", 243.0, 3.7, 32.0, 11.5),
            ("White Chocolate Bar", "snack", 539.0, 5.9, 59.0, 32.0),
            ("Sorbet", "snack", 120.0, 0.5, 30.0, 0.1),
            ("Gelato", "snack", 180.0, 4.0, 25.0, 7.0),
            ("Popsicle", "snack", 79.0, 0.0, 20.0, 0.0),
            ("Protein Bar", "snack", 400.0, 30.0, 40.0, 12.0),
            ("Fig Bar", "snack", 360.0, 4.0, 78.0, 4.5),
            ("Rice Crispy Treat", "snack", 426.0, 3.0, 80.0, 10.0),
            ("Marshmallow", "snack", 318.0, 1.8, 81.0, 0.2),
            ("Caramel Cube", "snack", 382.0, 1.6, 77.0, 8.1),
            ("Toffee Piece", "snack", 450.0, 1.0, 65.0, 21.0),
            ("Fudge Slice", "snack", 411.0, 2.3, 71.0, 13.0),
            ("Licorice Twist", "snack", 350.0, 3.0, 80.0, 1.0),
            ("Cheese Puffs", "snack", 536.0, 5.0, 56.0, 32.0),
            ("Pork Cracklings", "snack", 544.0, 61.0, 0.0, 31.0),
            ("Beef Sticks", "snack", 500.0, 25.0, 3.0, 43.0),
            ("Cashew Bar", "snack", 450.0, 10.0, 50.0, 25.0),
            ("Peanut Butter Cup", "snack", 513.0, 9.3, 57.0, 29.0),
            ("Rice Cakes Caramel", "snack", 387.0, 5.0, 85.0, 2.0),
            ("Oat Bar", "snack", 400.0, 6.0, 68.0, 12.0),
            ("Energy Gel", "snack", 280.0, 0.0, 70.0, 0.0),
            ("Dried Banana Chips", "snack", 519.0, 2.3, 58.0, 33.6),
            ("Potato Starch Crisps", "snack", 480.0, 5.0, 70.0, 20.0),
            ("Cheese Straws", "snack", 515.0, 12.0, 48.0, 31.0),
            ("Shortbread Crust", "snack", 500.0, 5.0, 60.0, 25.0),
            ("Fruit Leather", "snack", 350.0, 1.0, 83.0, 1.5),
            ("Popcorn Buttered", "snack", 450.0, 8.0, 56.0, 28.0),
            ("Tortilla Chips Lime", "snack", 497.0, 7.0, 65.0, 24.0),

            # --- BEVERAGE ---
            ("Black Coffee", "beverage", 1.0, 0.1, 0.0, 0.0),
            ("Espresso", "beverage", 9.0, 0.1, 1.7, 0.2),
            ("Black Tea", "beverage", 1.0, 0.0, 0.2, 0.0),
            ("Green Tea", "beverage", 1.0, 0.0, 0.0, 0.0),
            ("Orange Juice", "beverage", 45.0, 0.7, 10.4, 0.2),
            ("Apple Juice", "beverage", 46.0, 0.1, 11.3, 0.1),
            ("Cola Soda", "beverage", 38.0, 0.0, 10.0, 0.0),
            ("Diet Cola", "beverage", 0.0, 0.0, 0.1, 0.0),
            ("Energy Drink", "beverage", 45.0, 0.4, 11.0, 0.1),
            ("Sports Drink", "beverage", 25.0, 0.0, 6.0, 0.0),
            ("Coconut Water", "beverage", 19.0, 0.7, 3.7, 0.2),
            ("Tomato Juice", "beverage", 17.0, 0.8, 4.2, 0.1),
            ("Grape Juice", "beverage", 60.0, 0.6, 15.4, 0.1),
            ("Pineapple Juice", "beverage", 53.0, 0.4, 12.8, 0.1),
            ("Lemonade", "beverage", 40.0, 0.1, 10.2, 0.1),
            ("Iced Tea", "beverage", 35.0, 0.0, 8.8, 0.0),
            ("Hot Chocolate", "beverage", 77.0, 3.5, 10.5, 2.3),
            ("White Tea", "beverage", 1.0, 0.0, 0.2, 0.0),
            ("Olong Tea", "beverage", 1.0, 0.0, 0.2, 0.0),
            ("Herbal Chamomile Tea", "beverage", 1.0, 0.0, 0.2, 0.0),
            ("Herbal Peppermint Tea", "beverage", 1.0, 0.0, 0.2, 0.0),
            ("Rooibos Tea", "beverage", 1.0, 0.0, 0.2, 0.0),
            ("Cranberry Juice", "beverage", 46.0, 0.4, 12.2, 0.1),
            ("Pomegranate Juice", "beverage", 54.0, 0.2, 13.1, 0.3),
            ("Root Beer Soda", "beverage", 41.0, 0.0, 10.5, 0.0),
            ("Ginger Ale Soda", "beverage", 34.0, 0.0, 9.0, 0.0),
            ("Lemon-Lime Soda", "beverage", 38.0, 0.0, 10.0, 0.0),
            ("Kombucha Drink", "beverage", 30.0, 0.1, 7.0, 0.1),
            ("Milkshake Vanilla", "beverage", 112.0, 3.0, 15.0, 4.0),
            ("Milkshake Chocolate", "beverage", 116.0, 3.0, 16.0, 4.2),
            ("Strawberry Smoothie", "beverage", 60.0, 1.0, 14.0, 0.5),
            ("Green Smoothie", "beverage", 50.0, 1.5, 11.0, 0.5),
            ("Chai Latte", "beverage", 60.0, 2.0, 11.0, 1.5),
            ("Matcha Latte", "beverage", 60.0, 2.0, 11.0, 1.5),
            ("Café Latte", "beverage", 45.0, 2.5, 3.5, 2.0),
            ("Cappuccino", "beverage", 45.0, 2.5, 3.5, 2.0),
            ("Macchiato", "beverage", 45.0, 2.5, 3.5, 2.0),
            ("Club Soda", "beverage", 0.0, 0.0, 0.0, 0.0),
            ("Tonic Water", "beverage", 34.0, 0.0, 9.0, 0.0),
            ("Ginger Beer", "beverage", 48.0, 0.0, 12.0, 0.0),
            ("Protein Shake Chocolate", "beverage", 80.0, 15.0, 3.0, 1.0),
            ("Protein Shake Vanilla", "beverage", 80.0, 15.0, 3.0, 1.0),
            ("Almond Matcha Shake", "beverage", 70.0, 3.0, 8.0, 3.0),
            ("Soy Cacao Shake", "beverage", 80.0, 5.0, 10.0, 2.5),
            ("Oat Vanilla Shake", "beverage", 75.0, 4.0, 11.0, 2.0),
            ("Peach Iced Tea", "beverage", 32.0, 0.0, 8.0, 0.0),
            ("Mango Smoothie", "beverage", 70.0, 1.0, 16.0, 0.5),
            ("Cold Brew Coffee", "beverage", 1.0, 0.1, 0.0, 0.0),
            ("Hot Black Coffee", "beverage", 1.0, 0.1, 0.0, 0.0),
            ("Sparkling Water", "beverage", 0.0, 0.0, 0.0, 0.0),

            # --- SAUCE ---
            ("Ketchup", "sauce", 110.0, 1.0, 26.0, 0.1),
            ("Yellow Mustard", "sauce", 66.0, 4.0, 5.0, 4.0),
            ("Dijon Mustard", "sauce", 150.0, 6.0, 6.0, 11.0),
            ("Mayonnaise", "sauce", 680.0, 1.0, 1.0, 75.0),
            ("Barbecue Sauce", "sauce", 172.0, 1.0, 40.0, 0.6),
            ("Hot Sauce", "sauce", 15.0, 0.5, 3.0, 0.1),
            ("Sriracha", "sauce", 120.0, 2.0, 27.0, 1.0),
            ("Soy Sauce", "sauce", 53.0, 9.0, 5.0, 0.1),
            ("Teriyaki Sauce", "sauce", 89.0, 6.0, 16.0, 0.1),
            ("Sweet and Sour Sauce", "sauce", 150.0, 0.5, 36.0, 0.2),
            ("Marinara Sauce", "sauce", 50.0, 1.5, 8.0, 1.5),
            ("Pesto Sauce", "sauce", 529.0, 7.0, 6.0, 53.0),
            ("Alfredo Sauce", "sauce", 196.0, 3.5, 4.0, 19.0),
            ("Bolognese Sauce", "sauce", 120.0, 7.0, 6.0, 8.0),
            ("Hollandaise Sauce", "sauce", 535.0, 2.0, 2.0, 58.0),
            ("Tartar Sauce", "sauce", 210.0, 1.0, 8.0, 20.0),
            ("Horseradish Sauce", "sauce", 110.0, 1.5, 12.0, 6.0),
            ("Worcestershire Sauce", "sauce", 78.0, 0.0, 19.0, 0.0),
            ("Fish Sauce", "sauce", 35.0, 5.0, 4.0, 0.1),
            ("Oyster Sauce", "sauce", 51.0, 1.3, 11.3, 0.1),
            ("Hoisin Sauce", "sauce", 220.0, 2.0, 53.0, 1.5),
            ("Plum Sauce", "sauce", 240.0, 0.5, 59.0, 0.2),
            ("Tzatziki", "sauce", 90.0, 5.0, 4.0, 6.0),
            ("Hummus", "sauce", 166.0, 8.0, 14.0, 10.0),
            ("Guacamole", "sauce", 157.0, 2.0, 8.0, 14.0),
            ("Salsa", "sauce", 36.0, 1.5, 7.0, 0.2),
            ("Ranch Dressing", "sauce", 460.0, 1.5, 7.0, 48.0),
            ("Caesar Dressing", "sauce", 470.0, 2.0, 3.0, 50.0),
            ("Italian Dressing", "sauce", 290.0, 0.3, 8.0, 29.0),
            ("Balsamic Vinaigrette", "sauce", 350.0, 0.0, 18.0, 31.0),
            ("Blue Cheese Dressing", "sauce", 475.0, 2.5, 4.0, 50.0),
            ("Thousand Island Dressing", "sauce", 370.0, 1.0, 15.0, 35.0),
            ("Honey Mustard Dressing", "sauce", 460.0, 1.0, 22.0, 41.0),
            ("French Dressing", "sauce", 420.0, 0.5, 23.0, 36.0),
            ("Sweet Chili Sauce", "sauce", 180.0, 0.5, 45.0, 0.1),
            ("Buffalo Sauce", "sauce", 90.0, 1.0, 2.0, 9.0),
            ("Tartar Dip", "sauce", 210.0, 1.0, 8.0, 20.0),
            ("Cocktail Sauce", "sauce", 110.0, 1.5, 25.0, 0.2),
            ("Cranberry Sauce", "sauce", 150.0, 0.3, 38.0, 0.1),
            ("Apple Butter", "sauce", 120.0, 0.5, 30.0, 0.2),
            ("Peanut Sauce", "sauce", 350.0, 10.0, 15.0, 28.0),
            ("Tahini Sauce", "sauce", 590.0, 17.0, 16.0, 53.0),
            ("Chimichurri", "sauce", 400.0, 1.5, 4.0, 42.0),
            ("Pesto Dip", "sauce", 529.0, 7.0, 6.0, 53.0),
            ("Aioli Sauce", "sauce", 680.0, 1.0, 1.0, 75.0),

            # --- SOUP ---
            ("Chicken Noodle Soup", "soup", 36.0, 2.5, 4.5, 1.0),
            ("Tomato Soup", "soup", 45.0, 0.8, 8.0, 1.2),
            ("Vegetable Soup", "soup", 32.0, 1.0, 6.0, 0.5),
            ("Beef Stew", "soup", 95.0, 7.5, 7.0, 4.0),
            ("Chicken Stew", "soup", 85.0, 8.0, 6.0, 3.2),
            ("Clam Chowder", "soup", 82.0, 4.0, 9.0, 3.5),
            ("Potato Leek Soup", "soup", 60.0, 1.5, 9.0, 2.0),
            ("French Onion Soup", "soup", 38.0, 2.0, 5.0, 1.2),
            ("Minestrone Soup", "soup", 38.0, 1.8, 6.5, 0.6),
            ("Lentil Soup", "soup", 56.0, 3.8, 8.5, 0.8),
            ("Split Pea Soup", "soup", 70.0, 4.5, 12.0, 0.4),
            ("Butternut Squash Soup", "soup", 45.0, 1.0, 9.5, 0.8),
            ("Miso Soup", "soup", 22.0, 1.5, 2.5, 0.6),
            ("Wonton Soup", "soup", 30.0, 2.0, 4.0, 0.6),
            ("Egg Drop Soup", "soup", 27.0, 1.5, 2.2, 1.3),
            ("Tom Yum Soup", "soup", 38.0, 2.5, 4.0, 1.3),
            ("Gazpacho", "soup", 32.0, 0.8, 5.0, 1.2),
            ("Lobster Bisque", "soup", 98.0, 4.5, 5.0, 6.8),
            ("Crab Bisque", "soup", 92.0, 4.8, 5.2, 6.0),
            ("Corn Chowder", "soup", 78.0, 2.0, 12.5, 2.4),
            ("Black Bean Soup", "soup", 58.0, 3.5, 10.5, 0.4),
            ("Mulligatawny Soup", "soup", 65.0, 2.5, 9.5, 2.0),
            ("Beef Barley Soup", "soup", 62.0, 4.5, 7.5, 1.5),
            ("Chicken Tortilla Soup", "soup", 55.0, 4.0, 6.0, 1.8),
            ("Italian Wedding Soup", "soup", 45.0, 3.0, 4.5, 1.6),
            ("Matzo Ball Soup", "soup", 42.0, 1.8, 6.5, 1.0),
            ("Beef Noodle Soup", "soup", 58.0, 4.5, 7.5, 1.5),
            ("Pork Noodle Soup", "soup", 62.0, 4.5, 7.5, 2.0),
            ("Miso Ramen Soup", "soup", 80.0, 3.5, 12.0, 2.2),
            ("Hot and Sour Soup", "soup", 45.0, 2.5, 6.0, 1.5),
            ("Chicken Rice Soup", "soup", 38.0, 2.5, 5.0, 0.8),
            ("Turkey Rice Soup", "soup", 38.0, 2.5, 5.0, 0.8),
            ("Oxtail Soup", "soup", 85.0, 6.0, 4.0, 5.0),
            ("Gumbo Stew", "soup", 90.0, 6.5, 9.0, 3.5),
            ("Chili Con Carne", "soup", 110.0, 8.0, 11.0, 4.5)
        ]
        
        prep_styles = {
            "meat": [
                ("Raw", 1.0, 1.0, 1.0, 1.0),
                ("Grilled", 1.3, 1.2, 1.0, 1.2),
                ("Baked", 1.2, 1.15, 1.0, 1.1),
                ("Roasted", 1.25, 1.2, 1.0, 1.15),
                ("Fried", 1.8, 1.0, 1.2, 2.5),
                ("Steamed", 1.0, 1.0, 1.0, 0.95),
                ("Boiled", 0.95, 0.95, 1.0, 0.9),
                ("Sauteed", 1.4, 1.1, 1.0, 1.6),
                ("Pan-Seared", 1.35, 1.15, 1.0, 1.45),
                ("Smoked", 1.3, 1.25, 1.0, 1.2),
                ("Air-Fried", 1.2, 1.1, 1.0, 1.05),
                ("Slow-Cooked", 1.15, 1.1, 1.0, 1.1),
                ("Braised", 1.25, 1.15, 1.0, 1.2),
                ("Cured", 1.5, 1.3, 1.1, 1.4),
                ("Minced", 1.0, 1.0, 1.0, 1.0),
                ("Shredded", 1.0, 1.0, 1.0, 1.0),
                ("Glazed", 1.4, 0.9, 1.5, 1.1),
                ("Seasoned", 1.0, 1.0, 1.0, 1.0),
                ("Marinated", 1.1, 1.0, 1.05, 1.1),
                ("Battered & Fried", 2.2, 0.9, 1.8, 3.0),
                ("Charbroiled", 1.3, 1.2, 1.0, 1.25),
                ("Tenderized", 1.0, 1.0, 1.0, 1.0)
            ],
            "seafood": [
                ("Raw", 1.0, 1.0, 1.0, 1.0),
                ("Grilled", 1.25, 1.2, 1.0, 1.15),
                ("Baked", 1.15, 1.15, 1.0, 1.1),
                ("Fried", 1.7, 1.0, 1.3, 2.4),
                ("Steamed", 1.0, 1.0, 1.0, 0.95),
                ("Boiled", 0.95, 0.95, 1.0, 0.9),
                ("Pan-Seared", 1.3, 1.15, 1.0, 1.45),
                ("Smoked", 1.3, 1.2, 1.0, 1.2),
                ("Poached", 1.0, 1.0, 1.0, 0.95),
                ("Air-Fried", 1.2, 1.1, 1.1, 1.2),
                ("Blackened", 1.1, 1.1, 1.0, 1.1),
                ("Broiled", 1.15, 1.15, 1.0, 1.1),
                ("Cured", 1.3, 1.2, 1.1, 1.2),
                ("Salted", 1.1, 1.1, 1.0, 1.1),
                ("Beer-Battered", 2.0, 0.9, 1.7, 2.6),
                ("Marinated", 1.1, 1.0, 1.1, 1.1)
            ],
            "grain": [
                ("Raw (Dry)", 1.0, 1.0, 1.0, 1.0),
                ("Cooked", 0.35, 0.35, 0.35, 0.35),
                ("Steamed", 0.35, 0.35, 0.35, 0.35),
                ("Boiled", 0.33, 0.33, 0.33, 0.33),
                ("Fried", 0.65, 0.35, 0.45, 1.5),
                ("Toasted", 1.0, 1.0, 1.0, 1.0),
                ("Baked", 1.0, 1.0, 1.0, 1.0),
                ("Puffed", 1.0, 1.0, 1.0, 1.0),
                ("Sprouted", 1.05, 1.05, 1.05, 1.05),
                ("Whole-Grain", 1.0, 1.0, 1.0, 1.0),
                ("Enriched", 1.0, 1.0, 1.0, 1.0),
                ("Parboiled", 0.95, 0.95, 0.95, 0.95)
            ],
            "vegetable": [
                ("Raw", 1.0, 1.0, 1.0, 1.0),
                ("Steamed", 0.95, 0.95, 0.95, 0.95),
                ("Boiled", 0.9, 0.9, 0.9, 0.9),
                ("Roasted", 1.2, 1.1, 1.2, 1.1),
                ("Grilled", 1.15, 1.1, 1.1, 1.1),
                ("Sauteed", 1.5, 1.1, 1.1, 1.8),
                ("Air-Fried", 1.2, 1.0, 1.1, 1.3),
                ("Stir-Fried", 1.4, 1.0, 1.1, 1.6),
                ("Pickled", 0.8, 0.8, 1.1, 0.8),
                ("Mashed", 1.1, 1.0, 1.1, 1.1),
                ("Pureed", 0.95, 0.95, 0.95, 0.95),
                ("Chopped", 1.0, 1.0, 1.0, 1.0),
                ("Grated", 1.0, 1.0, 1.0, 1.0),
                ("Fermented", 0.9, 0.9, 1.0, 0.8)
            ],
            "fruit": [
                ("Raw", 1.0, 1.0, 1.0, 1.0),
                ("Dried", 4.0, 3.5, 4.0, 3.5),
                ("Cooked", 0.9, 0.9, 0.9, 0.9),
                ("Pureed", 1.0, 1.0, 1.0, 1.0),
                ("Frozen", 0.95, 0.95, 0.95, 0.95),
                ("Baked", 1.1, 1.0, 1.2, 1.1),
                ("Canned", 1.2, 0.9, 1.4, 0.9),
                ("Juiced", 0.8, 0.5, 1.2, 0.2),
                ("Freeze-Dried", 4.5, 3.8, 4.5, 3.8),
                ("Caramelized", 1.5, 0.8, 2.0, 1.0)
            ],
            "dairy": [
                ("Regular", 1.0, 1.0, 1.0, 1.0),
                ("Low-Fat", 0.7, 1.05, 1.0, 0.3),
                ("Fat-Free", 0.5, 1.1, 1.0, 0.05),
                ("Organic", 1.0, 1.0, 1.0, 1.0),
                ("Lactose-Free", 1.0, 1.0, 1.0, 1.0),
                ("Whipped", 1.0, 1.0, 1.0, 1.0),
                ("Salted", 1.0, 1.0, 1.0, 1.0),
                ("Unsalted", 1.0, 1.0, 1.0, 1.0),
                ("Cultured", 1.0, 1.0, 1.0, 1.0),
                ("Evaporated", 2.0, 2.0, 2.0, 2.0),
                ("Condensed", 3.0, 2.0, 5.0, 3.0),
                ("Powdered", 5.0, 5.0, 5.0, 5.0)
            ],
            "nut": [
                ("Raw", 1.0, 1.0, 1.0, 1.0),
                ("Roasted", 1.05, 1.05, 1.05, 1.05),
                ("Salted", 1.05, 1.05, 1.05, 1.05),
                ("Dry-Roasted", 1.02, 1.02, 1.02, 1.02),
                ("Honey-Roasted", 1.2, 1.0, 1.3, 1.1),
                ("Spiced", 1.05, 1.05, 1.05, 1.05),
                ("Ground", 1.0, 1.0, 1.0, 1.0),
                ("Blanched", 1.0, 1.0, 1.0, 1.0),
                ("Slivered", 1.0, 1.0, 1.0, 1.0),
                ("Chopped", 1.0, 1.0, 1.0, 1.0)
            ],
            "snack": [
                ("Regular", 1.0, 1.0, 1.0, 1.0),
                ("Low-Sodium", 1.0, 1.0, 1.0, 1.0),
                ("Gluten-Free", 1.0, 0.9, 1.05, 1.0),
                ("Organic", 1.0, 1.0, 1.0, 1.0),
                ("Baked", 0.9, 1.0, 1.0, 0.8),
                ("Keto-Friendly", 1.1, 1.2, 0.3, 1.4),
                ("Spiced", 1.0, 1.0, 1.0, 1.0),
                ("High-Protein", 1.1, 2.5, 0.8, 1.0),
                ("Low-Carb", 0.9, 1.2, 0.4, 1.2),
                ("Sugar-Free", 0.8, 1.0, 0.1, 1.0)
            ],
            "beverage": [
                ("Regular", 1.0, 1.0, 1.0, 1.0),
                ("Sugar-Free", 0.05, 1.0, 0.02, 0.0),
                ("With Milk", 1.5, 1.5, 1.2, 1.5),
                ("With Sugar", 1.8, 1.0, 2.0, 1.0),
                ("Iced", 1.0, 1.0, 1.0, 1.0),
                ("Hot", 1.0, 1.0, 1.0, 1.0),
                ("Decaf", 1.0, 1.0, 1.0, 1.0),
                ("Cold-Brewed", 1.0, 1.0, 1.0, 1.0),
                ("Concentrate", 3.0, 3.0, 3.0, 3.0),
                ("Infused", 1.0, 1.0, 1.0, 1.0)
            ],
            "sauce": [
                ("Regular", 1.0, 1.0, 1.0, 1.0),
                ("Low-Fat", 0.6, 0.9, 1.0, 0.4),
                ("Low-Sodium", 0.95, 1.0, 1.0, 1.0),
                ("Organic", 1.0, 1.0, 1.0, 1.0),
                ("Spicy", 1.0, 1.0, 1.0, 1.0),
                ("Sweet", 1.2, 0.9, 1.4, 0.9),
                ("Zesty", 1.0, 1.0, 1.0, 1.0),
                ("Creamy", 1.3, 1.0, 1.1, 1.8),
                ("Tangy", 1.0, 1.0, 1.0, 1.0),
                ("Glazed", 1.4, 0.8, 1.5, 1.1)
            ],
            "soup": [
                ("Regular", 1.0, 1.0, 1.0, 1.0),
                ("Low-Sodium", 0.95, 1.0, 1.0, 1.0),
                ("Condensed", 2.2, 2.0, 2.2, 2.0),
                ("Creamy", 1.5, 1.1, 1.2, 2.2),
                ("Clear Broth", 0.4, 0.5, 0.4, 0.3),
                ("Chunky", 1.1, 1.1, 1.1, 1.1),
                ("Spicy", 1.0, 1.0, 1.0, 1.0),
                ("Hearty", 1.3, 1.2, 1.2, 1.2)
            ]
        }
        
        for base_name, category, cal, pro, carb, fat in base_foods:
            styles = prep_styles.get(category, [("Regular", 1.0, 1.0, 1.0, 1.0)])
            for style_name, cal_m, pro_m, carb_m, fat_m in styles:
                if style_name == "Regular":
                    full_name = base_name
                else:
                    full_name = f"{style_name} {base_name}"
                if full_name not in seen_names:
                    seen_names.add(full_name)
                    new_cal = round(cal * cal_m, 1)
                    new_pro = round(pro * pro_m, 1)
                    new_carb = round(carb * carb_m, 1)
                    new_fat = round(fat * fat_m, 1)
                    foods_to_insert.append((full_name, new_cal, new_pro, new_carb, new_fat))
        cursor.executemany(
            "INSERT INTO foods (name, calories_per_100g, protein_per_100g, carbs_per_100g, fat_per_100g) VALUES (?, ?, ?, ?, ?)",
            foods_to_insert
        )
# 6. User Individual Food Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            food_name TEXT NOT NULL,
            amount_g REAL NOT NULL,
            calories INTEGER NOT NULL,
            protein INTEGER NOT NULL,
            carbs INTEGER NOT NULL,
            fat INTEGER NOT NULL,
            logged_date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # 7. Daily Exercise Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exercise_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            logged_date TEXT NOT NULL,
            activity_type TEXT NOT NULL,
            duration_min INTEGER NOT NULL,
            calories_burned INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # 8. Favorite Foods for faster logging
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorite_foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            food_id INTEGER,
            food_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (food_id) REFERENCES foods(id) ON DELETE SET NULL,
            UNIQUE(user_id, food_name)
        )
    ''')

    # 9. User food templates and recipes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS meal_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            entries_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            servings INTEGER DEFAULT 1,
            ingredients_json TEXT NOT NULL,
            calories INTEGER NOT NULL,
            protein INTEGER NOT NULL,
            carbs INTEGER NOT NULL,
            fat INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # 10. Generated weekly plans, coach check-ins, notes, and target history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS meal_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            week_start TEXT NOT NULL,
            plan_json TEXT NOT NULL,
            shopping_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, week_start)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            mood INTEGER,
            energy INTEGER,
            hunger INTEGER,
            compliance INTEGER,
            notes TEXT,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coach_threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS target_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            admin_id INTEGER,
            calories INTEGER,
            protein INTEGER,
            carbs INTEGER,
            fat INTEGER,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    
    # 5. Seed Default Admin User if not exists
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        admin_password = os.environ.get('NUTRIQUANT_ADMIN_PASSWORD', 'admin123')
        password_hash = generate_password_hash(admin_password, method='pbkdf2:sha256')
        cursor.execute(
            "INSERT INTO users (username, password_hash, is_admin) VALUES ('admin', ?, 1)",
            (password_hash,)
        )
        
    conn.commit()
    conn.close()

def register_user(username, password):
    """
    Registers a new user with a hashed password.
    Returns user_id on success, or None if the username already exists.
    """
    username = username.strip().lower()
    if not username or not password:
        return None
        
    password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 0)",
            (username, password_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return user_id
    except sqlite3.IntegrityError:
        return None  # Username already taken
    finally:
        conn.close()

def authenticate_user(username, password):
    """
    Authenticates username and password.
    Returns user row dictionary on success, or None on failure.
    """
    username = username.strip().lower()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user and check_password_hash(user['password_hash'], password):
        return dict(user)
    return None

def get_user_by_id(user_id):
    """Fetches user details by user ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def update_account_settings(user_id, full_name, email, password=None):
    """Updates the user's name, email, and password (if provided)."""
    conn = get_db()
    cursor = conn.cursor()
    if password:
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        cursor.execute('''
            UPDATE users
            SET full_name = ?, email = ?, password_hash = ?
            WHERE id = ?
        ''', (full_name, email, password_hash, user_id))
    else:
        cursor.execute('''
            UPDATE users
            SET full_name = ?, email = ?
            WHERE id = ?
        ''', (full_name, email, user_id))
    conn.commit()
    conn.close()
    return True

def save_onboarding(user_id, data):
    """Stores onboarding preferences used by meal planning and coaching workflows."""
    allergies = data.get('allergies', [])
    if isinstance(allergies, str):
        allergies = [a.strip() for a in allergies.split(',') if a.strip()]

    client_tags = data.get('client_tags', [])
    if isinstance(client_tags, str):
        client_tags = [t.strip() for t in client_tags.split(',') if t.strip()]

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users
        SET dietary_style = ?,
            allergies = ?,
            meal_schedule = ?,
            region_cuisine = ?,
            coaching_level = ?,
            client_tags = ?,
            onboarding_completed = 1
        WHERE id = ? AND is_admin = 0
    ''', (
        data.get('dietary_style', 'balanced'),
        json.dumps(allergies),
        data.get('meal_schedule', 'standard'),
        data.get('region_cuisine', 'global'),
        data.get('coaching_level', 'self_guided'),
        json.dumps(client_tags),
        user_id
    ))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success

def save_profile(user_id, age, height_cm, weight_kg, gender, activity, goal):
    """
    Saves/updates profile parameters in the users table, 
    and automatically updates/logs the weight for today.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Update profile in users table
    cursor.execute('''
        UPDATE users 
        SET age = ?, height_cm = ?, weight_kg = ?, gender = ?, activity = ?, goal = ?
        WHERE id = ?
    ''', (age, height_cm, weight_kg, gender, activity, goal, user_id))
    
    conn.commit()
    conn.close()
    
    # Auto-log weight for today
    today_str = datetime.now().strftime('%Y-%m-%d')
    log_weight(user_id, weight_kg, today_str)

def log_weight(user_id, weight_kg, date_str=None):
    """
    Logs weight for a user. If date_str is not provided, defaults to today.
    Uses UPSERT to prevent duplicate logs on the same date.
    """
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')
        
    conn = get_db()
    cursor = conn.cursor()
    try:
        # Upsert: Insert or replace weight if log for the date already exists
        cursor.execute('''
            INSERT INTO weight_logs (user_id, weight_kg, logged_at) 
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, logged_at) 
            DO UPDATE SET weight_kg = excluded.weight_kg
        ''', (user_id, float(weight_kg), date_str))
        
        # Also update the user's primary weight parameter in users table
        cursor.execute('UPDATE users SET weight_kg = ? WHERE id = ?', (float(weight_kg), user_id))
        
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def get_weight_history(user_id):
    """
    Returns weight logs sorted chronologically.
    Returns a list of dicts with logged_at and weight_kg keys.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT logged_at, weight_kg 
        FROM weight_logs 
        WHERE user_id = ? 
        ORDER BY logged_at ASC
    ''', (user_id,))
    logs = cursor.fetchall()
    conn.close()
    return [{"logged_at": log["logged_at"], "weight_kg": log["weight_kg"]} for log in logs]

# -------------------------------------------------------------
# Admin Queries
# -------------------------------------------------------------
def get_all_users():
    """
    Fetches all registered users who are not administrators.
    Excludes password hashes.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, username, gender, height_cm, weight_kg, age, activity, goal, created_at,
               dietary_style, allergies, meal_schedule, region_cuisine,
               coaching_level, coach_id, client_tags, onboarding_completed
        FROM users 
        WHERE is_admin = 0 
        ORDER BY created_at DESC
    ''')
    users = cursor.fetchall()
    conn.close()
    return [dict(u) for u in users]

def get_admin_stats():
    """
    Computes aggregate metrics for registered non-admin clients.
    """
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Total count
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 0")
    total_users = cursor.fetchone()[0]
    
    # 2. Averages
    if total_users > 0:
        cursor.execute('''
            SELECT AVG(age), AVG(height_cm), AVG(weight_kg) 
            FROM users 
            WHERE is_admin = 0
        ''')
        avg_age, avg_height, avg_weight = cursor.fetchone()
    else:
        avg_age, avg_height, avg_weight = 0, 0, 0
        
    # 3. Predefined Foods count
    cursor.execute("SELECT COUNT(*) FROM foods")
    total_foods = cursor.fetchone()[0]
    
    # 4. Audit Logs count
    cursor.execute("SELECT COUNT(*) FROM admin_audit_logs")
    total_audit_logs = cursor.fetchone()[0]
    
    # 5. Operational coaching metrics
    cursor.execute('''
        SELECT COUNT(*) FROM users
        WHERE is_admin = 0 AND onboarding_completed = 1
    ''')
    onboarding_completed = cursor.fetchone()[0]

    cursor.execute('''
        SELECT COUNT(*) FROM users
        WHERE is_admin = 0 AND coach_id IS NOT NULL
    ''')
    assigned_clients = cursor.fetchone()[0]

    cursor.execute('''
        SELECT COUNT(DISTINCT user_id)
        FROM daily_intake
        WHERE logged_date >= date('now', '-7 day')
          AND (calories > 0 OR water_ml > 0 OR protein > 0 OR carbs > 0 OR fat > 0)
    ''')
    active_last_7_days = cursor.fetchone()[0]

    cursor.execute('''
        SELECT COUNT(*) FROM checkins
        WHERE checked_at >= datetime('now', '-7 day')
    ''')
    checkins_last_7_days = cursor.fetchone()[0]

    cursor.execute('''
        SELECT goal, COUNT(*) as count
        FROM users
        WHERE is_admin = 0 AND goal IS NOT NULL
        GROUP BY goal
    ''')
    goals = {row['goal']: row['count'] for row in cursor.fetchall()}

    cursor.execute('''
        SELECT activity, COUNT(*) as count
        FROM users
        WHERE is_admin = 0 AND activity IS NOT NULL
        GROUP BY activity
    ''')
    activities = {row['activity']: row['count'] for row in cursor.fetchall()}
        
    conn.close()
    return {
        "total_users": total_users,
        "avg_age": round(avg_age or 0, 1),
        "avg_height": round(avg_height or 0, 1),
        "avg_weight": round(avg_weight or 0, 1),
        "total_foods": total_foods,
        "total_audit_logs": total_audit_logs,
        "onboarding_completed": onboarding_completed,
        "assigned_clients": assigned_clients,
        "active_last_7_days": active_last_7_days,
        "checkins_last_7_days": checkins_last_7_days,
        "goals": goals,
        "activities": activities
    }

def delete_user(user_id):
    """
    Deletes a user by ID. 
    Foreign key constraints automatically cascade delete their weight logs.
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE id = ? AND is_admin = 0", (user_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        return False
    finally:
        conn.close()


# -------------------------------------------------------------
# User Dashboard & Logs Queries
# -------------------------------------------------------------
def get_daily_intake(user_id, date_str):
    """
    Fetches the daily log for a user on a given date.
    Creates a blank record if it does not exist.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT water_ml, calories, protein, carbs, fat, checklist 
        FROM daily_intake 
        WHERE user_id = ? AND logged_date = ?
    ''', (user_id, date_str))
    row = cursor.fetchone()
    
    if row:
        result = dict(row)
        conn.close()
        return result
        
    # Create default record
    try:
        cursor.execute('''
            INSERT INTO daily_intake (user_id, logged_date, water_ml, calories, protein, carbs, fat, checklist)
            VALUES (?, ?, 0, 0, 0, 0, 0, '[]')
        ''', (user_id, date_str))
        conn.commit()
        cursor.execute('''
            SELECT water_ml, calories, protein, carbs, fat, checklist 
            FROM daily_intake 
            WHERE user_id = ? AND logged_date = ?
        ''', (user_id, date_str))
        row = cursor.fetchone()
        result = dict(row) if row else {"water_ml": 0, "calories": 0, "protein": 0, "carbs": 0, "fat": 0, "checklist": "[]"}
    except sqlite3.IntegrityError:
        # Just in case of race conditions
        cursor.execute('SELECT water_ml, calories, protein, carbs, fat, checklist FROM daily_intake WHERE user_id = ? AND logged_date = ?', (user_id, date_str))
        row = cursor.fetchone()
        result = dict(row) if row else {"water_ml": 0, "calories": 0, "protein": 0, "carbs": 0, "fat": 0, "checklist": "[]"}
    finally:
        conn.close()
        
    return result

def update_water(user_id, date_str, amount_ml, set_absolute=False):
    """Increments or updates the water intake for a user on a given date."""
    # Ensure daily_intake record exists before opening connection (avoid DB connection nesting & locks)
    get_daily_intake(user_id, date_str)
    
    conn = get_db()
    cursor = conn.cursor()
    if set_absolute:
        cursor.execute('''
            UPDATE daily_intake 
            SET water_ml = MAX(0, ?) 
            WHERE user_id = ? AND logged_date = ?
        ''', (amount_ml, user_id, date_str))
    else:
        cursor.execute('''
            UPDATE daily_intake 
            SET water_ml = MAX(0, water_ml + ?) 
            WHERE user_id = ? AND logged_date = ?
        ''', (amount_ml, user_id, date_str))
    
    conn.commit()
    conn.close()
    return True

def add_food_entry(user_id, date_str, calories, protein, carbs, fat):
    """Adds a food log to the daily totals."""
    # Ensure daily_intake record exists before opening connection (avoid DB connection nesting & locks)
    get_daily_intake(user_id, date_str)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE daily_intake 
        SET calories = calories + ?,
            protein = protein + ?,
            carbs = carbs + ?,
            fat = fat + ?
        WHERE user_id = ? AND logged_date = ?
    ''', (int(calories), int(protein), int(carbs), int(fat), user_id, date_str))
    
    conn.commit()
    conn.close()
    return True

def update_checklist(user_id, date_str, items_json):
    """Saves the habit checklist state."""
    # Ensure daily_intake record exists before opening connection (avoid DB connection nesting & locks)
    get_daily_intake(user_id, date_str)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE daily_intake 
        SET checklist = ? 
        WHERE user_id = ? AND logged_date = ?
    ''', (items_json, user_id, date_str))
    
    conn.commit()
    conn.close()
    return True


# -------------------------------------------------------------
# Coaching Notes & Overrides Queries
# -------------------------------------------------------------
def get_coaching_notes(user_id):
    """
    Fetches coaching announcements and personal coaching feedback for a user.
    Returns notes ordered by newest first.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT n.message, n.created_at, u.username as sender_name 
        FROM coaching_notes n
        JOIN users u ON n.sender_id = u.id
        WHERE n.receiver_id IS NULL OR n.receiver_id = ?
        ORDER BY n.created_at DESC
        LIMIT 20
    ''', (user_id,))
    notes = cursor.fetchall()
    conn.close()
    
    return [dict(note) for note in notes]

def add_coaching_note(sender_id, receiver_id, message):
    """Adds a direct coach-client feedback note or a global announcement."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO coaching_notes (sender_id, receiver_id, message) 
            VALUES (?, ?, ?)
        ''', (sender_id, receiver_id, message))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def save_custom_override(user_id, cal, pro, carb, fat):
    """Updates a user's custom daily nutrition targets."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE users 
            SET custom_calories = ?, custom_protein = ?, custom_carbs = ?, custom_fat = ?
            WHERE id = ?
        ''', (cal, pro, carb, fat, user_id))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def clear_custom_override(user_id):
    """Clears coach targets override and returns to default calculations."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE users 
            SET custom_calories = NULL, custom_protein = NULL, custom_carbs = NULL, custom_fat = NULL
            WHERE id = ?
        ''', (user_id,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def get_dashboard_analytics():
    """Computes distribution statistics for the admin dashboard (goals, activity levels)."""
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Goal Distribution
    cursor.execute('''
        SELECT goal, COUNT(*) as count 
        FROM users 
        WHERE is_admin = 0 
        GROUP BY goal
    ''')
    goals = {row['goal'] or 'unknown': row['count'] for row in cursor.fetchall()}
    
    # 2. Activity Distribution
    cursor.execute('''
        SELECT activity, COUNT(*) as count 
        FROM users 
        WHERE is_admin = 0 
        GROUP BY activity
    ''')
    activities = {row['activity'] or 'unknown': row['count'] for row in cursor.fetchall()}
    
    # 3. Total weight logs
    cursor.execute("SELECT COUNT(*) FROM weight_logs")
    total_weight_logs = cursor.fetchone()[0]
    
    conn.close()
    return {
        "goals": goals,
        "activities": activities,
        "total_weight_logs": total_weight_logs
    }

def get_all_foods():
    """Fetches list of all predefined foods in the database."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM foods ORDER BY name ASC")
    foods = cursor.fetchall()
    conn.close()
    return [dict(f) for f in foods]

def add_food_log(user_id, date_str, food_name, amount_g, calories, protein, carbs, fat):
    """
    Logs an individual food entry into food_entries, 
    and increments the user's daily_intake totals for that date.
    """
    # 1. Ensure aggregate daily_intake record exists for today
    get_daily_intake(user_id, date_str)
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        # 2. Insert into individual food_entries
        cursor.execute('''
            INSERT INTO food_entries (user_id, food_name, amount_g, calories, protein, carbs, fat, logged_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, food_name, float(amount_g), int(calories), int(protein), int(carbs), int(fat), date_str))
        
        # 3. Update aggregate totals
        cursor.execute('''
            UPDATE daily_intake 
            SET calories = calories + ?,
                protein = protein + ?,
                carbs = carbs + ?,
                fat = fat + ?
            WHERE user_id = ? AND logged_date = ?
        ''', (int(calories), int(protein), int(carbs), int(fat), user_id, date_str))
        
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def delete_food_log(entry_id, user_id):
    """
    Deletes a specific food entry and subtracts its nutritional values 
    from the user's daily_intake totals for that date.
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        # 1. Fetch details of the entry to get the date and macros to subtract
        cursor.execute("SELECT * FROM food_entries WHERE id = ? AND user_id = ?", (entry_id, user_id))
        entry = cursor.fetchone()
        if not entry:
            return False
            
        calories = entry['calories']
        protein = entry['protein']
        carbs = entry['carbs']
        fat = entry['fat']
        date_str = entry['logged_date']
        
        # 2. Delete the individual entry
        cursor.execute("DELETE FROM food_entries WHERE id = ? AND user_id = ?", (entry_id, user_id))
        
        # 3. Update the daily_intake aggregates (don't go below 0)
        cursor.execute('''
            UPDATE daily_intake
            SET calories = MAX(0, calories - ?),
                protein = MAX(0, protein - ?),
                carbs = MAX(0, carbs - ?),
                fat = MAX(0, fat - ?)
            WHERE user_id = ? AND logged_date = ?
        ''', (int(calories), int(protein), int(carbs), int(fat), user_id, date_str))
        
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def get_food_logs_for_date(user_id, date_str):
    """Retrieves all individual food log entries for a user on a given date."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM food_entries 
        WHERE user_id = ? AND logged_date = ?
        ORDER BY id ASC
    ''', (user_id, date_str))
    logs = cursor.fetchall()
    conn.close()
    return [dict(l) for l in logs]


# -------------------------------------------------------------
# Predefined Food Database CRUD (Admin)
# -------------------------------------------------------------
def add_food(name, calories, protein, carbs, fat):
    """Inserts a new predefined food item into the foods table."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO foods (name, calories_per_100g, protein_per_100g, carbs_per_100g, fat_per_100g)
            VALUES (?, ?, ?, ?, ?)
        ''', (name.strip(), float(calories), float(protein), float(carbs), float(fat)))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None  # Food name already exists
    finally:
        conn.close()

def update_food(food_id, name, calories, protein, carbs, fat):
    """Updates an existing predefined food item in the database."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE foods 
            SET name = ?, calories_per_100g = ?, protein_per_100g = ?, carbs_per_100g = ?, fat_per_100g = ?
            WHERE id = ?
        ''', (name.strip(), float(calories), float(protein), float(carbs), float(fat), food_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_food(food_id):
    """Deletes a predefined food item from the database."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM foods WHERE id = ?", (food_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        return False
    finally:
        conn.close()


# -------------------------------------------------------------
# Admin Audit Logging
# -------------------------------------------------------------
def log_admin_action(admin_id, action_type, target_info, details):
    """Inserts a record into the admin_audit_logs table."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO admin_audit_logs (admin_id, action_type, target_info, details)
            VALUES (?, ?, ?, ?)
        ''', (admin_id, action_type, target_info, details))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def get_admin_audit_logs(limit=50):
    """Fetches recent admin actions sorted by time."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.*, u.username as admin_username 
        FROM admin_audit_logs a
        JOIN users u ON a.admin_id = u.id
        ORDER BY a.created_at DESC
        LIMIT ?
    ''', (limit,))
    logs = cursor.fetchall()
    conn.close()
    return [dict(l) for l in logs]

# -------------------------------------------------------------
# Exercise Logging (B2C)
# -------------------------------------------------------------
def add_exercise_log(user_id, date_str, activity_type, duration_min, calories_burned):
    """Inserts a new exercise log entry into the database."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO exercise_logs (user_id, logged_date, activity_type, duration_min, calories_burned)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, date_str.strip(), activity_type.strip(), int(duration_min), int(calories_burned)))
        conn.commit()
        return cursor.lastrowid
    except Exception:
        return None
    finally:
        conn.close()

def get_exercise_logs(user_id, date_str):
    """Fetches all exercise logs for a user on a given date."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM exercise_logs 
        WHERE user_id = ? AND logged_date = ?
        ORDER BY id ASC
    ''', (user_id, date_str.strip()))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_exercise_log(log_id, user_id):
    """Deletes an exercise log entry if it belongs to the user."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            DELETE FROM exercise_logs
            WHERE id = ? AND user_id = ?
        ''', (log_id, user_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        return False
    finally:
        conn.close()

def get_total_exercise_calories(user_id, date_str):
    """Returns the total calories burned from exercise for a user on a date."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT SUM(calories_burned) FROM exercise_logs
        WHERE user_id = ? AND logged_date = ?
    ''', (user_id, date_str.strip()))
    result = cursor.fetchone()[0]
    conn.close()
    return int(result) if result else 0


# -------------------------------------------------------------
# Product Workflow Helpers
# -------------------------------------------------------------
def get_recent_foods(user_id, limit=8):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT food_name, amount_g, calories, protein, carbs, fat, MAX(logged_date) as last_logged
        FROM food_entries
        WHERE user_id = ?
        GROUP BY food_name, amount_g, calories, protein, carbs, fat
        ORDER BY last_logged DESC
        LIMIT ?
    ''', (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_favorite_food(user_id, food_name, food_id=None):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO favorite_foods (user_id, food_id, food_name)
            VALUES (?, ?, ?)
        ''', (user_id, food_id, food_name.strip()))
        conn.commit()
        return True
    finally:
        conn.close()

def get_favorite_foods(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ff.*, f.calories_per_100g, f.protein_per_100g, f.carbs_per_100g, f.fat_per_100g
        FROM favorite_foods ff
        LEFT JOIN foods f ON ff.food_id = f.id
        WHERE ff.user_id = ?
        ORDER BY ff.created_at DESC
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_meal_template(user_id, name, entries):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO meal_templates (user_id, name, entries_json)
        VALUES (?, ?, ?)
    ''', (user_id, name.strip(), json.dumps(entries)))
    conn.commit()
    template_id = cursor.lastrowid
    conn.close()
    return template_id

def get_meal_templates(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM meal_templates
        WHERE user_id = ?
        ORDER BY created_at DESC
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    templates = []
    for row in rows:
        item = dict(row)
        item['entries'] = json.loads(item.pop('entries_json') or '[]')
        templates.append(item)
    return templates

def save_recipe(user_id, name, servings, ingredients, totals):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO recipes (user_id, name, servings, ingredients_json, calories, protein, carbs, fat)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        name.strip(),
        int(servings or 1),
        json.dumps(ingredients),
        int(totals.get('calories', 0)),
        int(totals.get('protein', 0)),
        int(totals.get('carbs', 0)),
        int(totals.get('fat', 0))
    ))
    conn.commit()
    recipe_id = cursor.lastrowid
    conn.close()
    return recipe_id

def get_recipes(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM recipes
        WHERE user_id = ?
        ORDER BY created_at DESC
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    recipes = []
    for row in rows:
        item = dict(row)
        item['ingredients'] = json.loads(item.pop('ingredients_json') or '[]')
        recipes.append(item)
    return recipes

def save_meal_plan(user_id, week_start, plan, shopping):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO meal_plans (user_id, week_start, plan_json, shopping_json)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, week_start)
        DO UPDATE SET plan_json = excluded.plan_json,
                      shopping_json = excluded.shopping_json,
                      created_at = CURRENT_TIMESTAMP
    ''', (user_id, week_start, json.dumps(plan), json.dumps(shopping)))
    conn.commit()
    conn.close()
    return True

def get_latest_meal_plan(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM meal_plans
        WHERE user_id = ?
        ORDER BY week_start DESC, created_at DESC
        LIMIT 1
    ''', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    plan = dict(row)
    plan['plan'] = json.loads(plan.pop('plan_json') or '{}')
    plan['shopping'] = json.loads(plan.pop('shopping_json') or '[]')
    return plan

def assign_client_coach(user_id, coach_id, tags=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users
        SET coach_id = ?, client_tags = ?
        WHERE id = ? AND is_admin = 0
    ''', (coach_id, json.dumps(tags or []), user_id))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success

def add_checkin(user_id, mood, energy, hunger, compliance, notes):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO checkins (user_id, mood, energy, hunger, compliance, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, mood, energy, hunger, compliance, notes))
    conn.commit()
    checkin_id = cursor.lastrowid
    conn.close()
    return checkin_id

def get_checkins(user_id, limit=8):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM checkins
        WHERE user_id = ?
        ORDER BY checked_at DESC
        LIMIT ?
    ''', (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_thread_message(sender_id, receiver_id, message):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO coach_threads (sender_id, receiver_id, message)
        VALUES (?, ?, ?)
    ''', (sender_id, receiver_id, message.strip()))
    conn.commit()
    message_id = cursor.lastrowid
    conn.close()
    return message_id

def get_thread_messages(user_id, other_user_id=None, limit=50):
    conn = get_db()
    cursor = conn.cursor()
    params = [user_id, user_id]
    clause = "(sender_id = ? OR receiver_id = ?)"
    if other_user_id:
        clause = "((sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?))"
        params = [user_id, other_user_id, other_user_id, user_id]
    cursor.execute(f'''
        SELECT ct.*, s.username as sender_username, r.username as receiver_username
        FROM coach_threads ct
        JOIN users s ON ct.sender_id = s.id
        JOIN users r ON ct.receiver_id = r.id
        WHERE {clause}
        ORDER BY ct.created_at DESC
        LIMIT ?
    ''', (*params, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_target_history(user_id, admin_id, calories, protein, carbs, fat, reason):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO target_history (user_id, admin_id, calories, protein, carbs, fat, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, admin_id, calories, protein, carbs, fat, reason))
    conn.commit()
    conn.close()
    return True

def get_target_history(user_id, limit=10):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT th.*, u.username as admin_username
        FROM target_history th
        LEFT JOIN users u ON th.admin_id = u.id
        WHERE th.user_id = ?
        ORDER BY th.created_at DESC
        LIMIT ?
    ''', (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
