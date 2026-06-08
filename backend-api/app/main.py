from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import sqlite3
import io
import os

from werkzeug.security import generate_password_hash, check_password_hash
# Import the classifier built in the previous step
from classifier import VerteClassifier

app = Flask(__name__)
CORS(app, resources={r"/*": {
    "origins": "*",
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"]
}})
app.secret_key = "verte_secret_vine_key_change_in_production"

# Handle paths smoothly whether running from app/ or project root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "mobilenetv2_waste.h5")
DB_PATH = os.path.join(BASE_DIR, "database.db")

if not os.path.exists(MODEL_PATH):
    # Fallback to check relative workspace paths if directory layout differs
    MODEL_PATH = "../models/mobilenetv2_waste.h5"
    if not os.path.exists(MODEL_PATH):
        MODEL_PATH = "../../ai-model/models/mobilenetv2_waste.h5"

# Initialize our AI Engine with the calculated model path location
ai_engine = VerteClassifier(model_path=MODEL_PATH)

# Active scans tracking (Temporary storage for matching user guesses to photos)
ACTIVE_SCANS = {}

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        # Create user_scores table needed for streaks/points
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_scores (
                user_id INTEGER PRIMARY KEY,
                total_points INTEGER DEFAULT 0,
                streak_count INTEGER DEFAULT 0,
                last_upload_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        # Create scan_history table needed for logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                predicted_category TEXT,
                user_guess TEXT,
                is_correct INTEGER,
                points_awarded INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        conn.commit()
    print("🗄️ SQLite Database schema checks passed cleanly!")

init_db()

def get_db_connection():
    # ✅ FIX: All routes now use the exact same DB_PATH file location
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Allows reading rows as key-value dictionaries
    return conn


@app.route("/api/upload", methods=["POST"])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
        
    user_id = int(request.form.get("user_id", 1)) # Defaulting to user 1 for development
    file = request.files['image']
    image_bytes = io.BytesIO(file.read())
    
    try:
        # Run inference using the MobileNetV2 pipeline
        ai_result = ai_engine.predict(image_bytes)
        
        # Save the true classification result temporarily in memory linked to user
        ACTIVE_SCANS[user_id] = {
            "true_category": ai_result["category"],
            "raw_material": ai_result["raw_material"],
            "timestamp": datetime.utcnow()
        }
        
        return jsonify({
            "message": "Image analyzed successfully. Time to guess!",
            "options": ["recyclable", "compostable", "landfill"]
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"AI Processing failed: {str(e)}"}), 500


@app.route("/api/verify-guess", methods=["POST"])
def verify_guess():
    data = request.json or {}
    user_id = int(data.get("user_id", 1))
    user_guess = data.get("guess", "").lower()
    
    scan_session = ACTIVE_SCANS.get(user_id)
    if not scan_session:
        return jsonify({"error": "No active upload session found for this user."}), 400
        
    true_category = scan_session["true_category"]
    
    points_awarded = 0
    is_correct = (user_guess == true_category)
    now = datetime.utcnow()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("INSERT OR IGNORE INTO user_scores (user_id, total_points, streak_count) VALUES (?, 0, 0)", (user_id,))
    
    user_profile = cursor.execute("SELECT * FROM user_scores WHERE user_id = ?", (user_id,)).fetchone()
    total_points = user_profile["total_points"]
    streak_count = user_profile["streak_count"]
    last_upload_at = user_profile["last_upload_at"]
    
    if is_correct:
        points_awarded = 10
        total_points += points_awarded
        
        if last_upload_at is None:
            streak_count = 1
        else:
            last_scan = datetime.strptime(last_upload_at, "%Y-%m-%d %H:%M:%S")
            if (now - last_scan) <= timedelta(hours=24):
                streak_count += 1
            else:
                streak_count = 1
                
        last_upload_at = now_str
        status_message = "Connect! Correct category guessed. Your vine grows!"
    else:
        streak_count = 0 
        status_message = f"Not quite! The AI classified this item as {true_category}."
        
    cursor.execute("""
        UPDATE user_scores 
        SET total_points = ?, streak_count = ?, last_upload_at = ? 
        WHERE user_id = ?
    """, (total_points, streak_count, last_upload_at, user_id))
    
    cursor.execute("""
        INSERT INTO scan_history (user_id, predicted_category, user_guess, is_correct, points_awarded)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, true_category, user_guess, int(is_correct), points_awarded))
    
    conn.commit()
    conn.close()
    
    if user_id in ACTIVE_SCANS:
        del ACTIVE_SCANS[user_id]
    
    return jsonify({
        "correct": is_correct,
        "message": status_message,
        "true_category": true_category,
        "points_awarded": points_awarded,
        "updated_stats": {
            "total_points": total_points,
            "streak_count": streak_count
        }
    }), 200


@app.route('/api/register', methods=['POST'])
def register_user():
    """
    ✅ FIX: Fully implemented registration query pipeline with password hashing.
    """
    try:
        data = request.json or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        if not username or not password:
            return jsonify({"error": "Username and password are required."}), 400

        # Generate standard cryptographically secure password hash
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed_password)
            )
            conn.commit()
            
            # Fetch the newly created user's ID
            user_id = cursor.lastrowid
            
            # Initialize their score tracking row immediately
            cursor.execute(
                "INSERT INTO user_scores (user_id, total_points, streak_count) VALUES (?, 0, 0)",
                (user_id,)
            )
            conn.commit()
            
        except sqlite3.IntegrityError:
            return jsonify({"error": "Username already exists. Please choose another."}), 400
        finally:
            conn.close()

        return jsonify({
            "success": True,
            "message": "User registered successfully!",
            "user_id": user_id
        }), 201
        
    except Exception as e:
        return jsonify({"error": f"Database write failure: {str(e)}"}), 500


@app.route("/api/login", methods=["POST"])
def login_user():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "Please provide both username and password."}), 400

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()

    # ✅ FIX: Pointed verify sequence to user["password"] to match table schema
    if user is None or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid username or password combination."}), 401

    return jsonify({
        "success": True,
        "message": f"Welcome back, {username}!",
        "user_id": user["id"]
    }), 200


@app.route("/", methods=["GET"])
def home_fallback():
    return jsonify({
        "status": "online",
        "app": "Verte AI Engine Backend API",
        "version": "1.0.0",
        "endpoints": ["/api/upload", "/api/verify-guess", "/api/register", "/api/login", "/api/user-stats/<id>"]
    }), 200


@app.route("/api/user-stats/<int:user_id>", methods=["GET"])
def get_user_stats(user_id):
    conn = get_db_connection()
    row = conn.execute("SELECT total_points, streak_count FROM user_scores WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    
    if not row:
        return jsonify({"total_points": 0, "streak_count": 0}), 200
        
    return jsonify({
        "total_points": row["total_points"],
        "streak_count": row["streak_count"]
    }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)