from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import io
import os

# Import the classifier framework
from classifier import VerteClassifier

app = Flask(__name__)

# Thorough CORS implementation to allow smooth API calls across Vercel and localhost
CORS(app, resources={r"/*": {
    "origins": "*",
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"]
}})

app.secret_key = "verte_secret_vine_key_change_in_production"

# Calculate pristine paths for the execution environment dynamically
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "mobilenetv2_waste.h5")
DB_PATH = os.path.join(BASE_DIR, "database.db")

# Fallback path resolutions for different project directory variants
if not os.path.exists(MODEL_PATH):
    MODEL_PATH = "../models/mobilenetv2_waste.h5"
    if not os.path.exists(MODEL_PATH):
        MODEL_PATH = "../../ai-model/models/mobilenetv2_waste.h5"

# Initialize AI classifier engine
ai_engine = VerteClassifier(model_path=MODEL_PATH)

# In-memory transient session storage for matching user guesses against true categories
ACTIVE_SCANS = {}

def init_db():
    """Validates and instantiates structural schema matrices safely upon initialization."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_scores (
                user_id INTEGER PRIMARY KEY,
                total_points INTEGER DEFAULT 0,
                streak_count INTEGER DEFAULT 0,
                last_upload_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
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

# Enforce database schema health check on launch
init_db()

def get_db_connection():
    """Generates an optimized key-value row contextual dictionary pipeline."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/", methods=["GET"])
def home_fallback():
    """Healthy endpoint heartbeat check."""
    return jsonify({
        "status": "online",
        "app": "Verte AI Engine Backend API",
        "version": "1.1.0"
    }), 200


@app.route('/api/register', methods=['POST'])
def register_user():
    """Registers users by accepting variations of frontend payload keys."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        print(f"📥 RAW FRONTEND DATA RECEIVED: {data}", flush=True)

        # Try extracting variations of "username" sent by the frontend
        username = data.get("username") or data.get("user") or data.get("email")
        # Try extracting variations of "password" sent by the frontend
        password = data.get("password") or data.get("pass")
    
        # Clean strings if they exist
        if username: username = str(username).strip()
        if password: password = str(password).strip()

        if not username or not password:
            return jsonify({
                "error": "Registration failed. Backend did not receive username or password values.",
                "received_keys": list(data.keys())
            }), 400

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed_password)
            )
            user_id = cursor.lastrowid
            
            cursor.execute(
                "INSERT INTO user_scores (user_id, total_points, streak_count) VALUES (?, 0, 0)",
                (user_id,)
            )
            conn.commit()
            
        except sqlite3.IntegrityError:
            return jsonify({"error": "That username is already taken."}), 400
        finally:
            conn.close()

        return jsonify({
            "success": True,
            "message": "Registration successful!",
            "user_id": user_id
        }), 201
        
    except Exception as e:
        return jsonify({"error": f"Internal database error: {str(e)}"}), 500


@app.route("/api/login", methods=["POST"])
def login_user():
    """Authenticates account matching signatures safely."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        if not username or not password:
            return jsonify({"error": "Missing validation requirements."}), 400

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user is None or not check_password_hash(user["password"], password):
            return jsonify({"error": "Invalid username or password configuration."}), 401

        return jsonify({
            "success": True,
            "message": f"Welcome back, {username}!",
            "user_id": user["id"]
        }), 200
    except Exception as e:
        return jsonify({"error": f"Server login pipeline issue: {str(e)}"}), 500


@app.route("/api/upload", methods=["POST"])
def upload_image():
    """Receives visual camera stream payloads and pushes matrix values to AI Engine."""
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
        
    user_id = int(request.form.get("user_id", 1))
    file = request.files['image']
    image_bytes = io.BytesIO(file.read())
    
    try:
        # Machine learning network inference processing
        ai_result = ai_engine.predict(image_bytes)
        
        ACTIVE_SCANS[user_id] = {
            "true_category": ai_result["category"],
            "raw_material": ai_result["raw_material"],
            "timestamp": datetime.utcnow()
        }
        
        return jsonify({
            "message": "Analysis processing complete. Make your selection!",
            "options": ["recyclable", "compostable", "landfill"]
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"AI Processing failed: {str(e)}"}), 500


@app.route("/api/verify-guess", methods=["POST"])
def verify_guess():
    """Validates selected option boxes against stored inferences to compute scores."""
    try:
        data = request.json or {}
        user_id = int(data.get("user_id", 1))
        user_guess = data.get("guess", "").lower().strip()
        
        scan_session = ACTIVE_SCANS.get(user_id)
        if not scan_session:
            return jsonify({"error": "No active scan transaction found."}), 400
            
        true_category = scan_session["true_category"]
        points_awarded = 0
        is_correct = (user_guess == true_category)
        now = datetime.utcnow()
        
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
            last_upload_at = now.strftime("%Y-%m-%d %H:%M:%S")
            status_message = "Correct! Your sustainability vine grows longer!"
        else:
            streak_count = 0 
            status_message = f"Not quite. The AI classified this element as {true_category}."
            
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
    except Exception as e:
        return jsonify({"error": f"Verification pipeline crash: {str(e)}"}), 500


@app.route("/api/user-stats/<int:user_id>", methods=["GET"])
def get_user_stats(user_id):
    """Retrieves score telemetry attributes for rendering UI profile updates."""
    try:
        conn = get_db_connection()
        row = conn.execute("SELECT total_points, streak_count FROM user_scores WHERE user_id = ?", (user_id,)).fetchone()
        conn.close()
        
        if not row:
            return jsonify({"total_points": 0, "streak_count": 0}), 200
            
        return jsonify({
            "total_points": row["total_points"],
            "streak_count": row["streak_count"]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)