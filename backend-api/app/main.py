# backend-api/app/main.py

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
MODEL_PATH = "./models/mobilenetv2_waste.h5"
if not os.path.exists(MODEL_PATH):
    # Fallback to check relative workspace paths if directory layout differs
    MODEL_PATH = "../models/mobilenetv2_waste.h5"
    if not os.path.exists(MODEL_PATH):
        MODEL_PATH = "../../ai-model/models/mobilenetv2_waste.h5"

# Initialize our AI Engine with the calculated model path location
ai_engine = VerteClassifier(model_path=MODEL_PATH)

# Active scans tracking (Temporary storage for matching user guesses to photos)
ACTIVE_SCANS = {}

def get_db_connection():
    # Looks for your newly initialized database file inside the database directory
    db_location = "./database/verte.db"
    if not os.path.exists(db_location):
        db_location = "verte.db"
        
    conn = sqlite3.connect(db_location)
    conn.row_factory = sqlite3.Row  # Allows reading rows as key-value dictionaries
    return conn

@app.route("/api/upload", methods=["POST"])
def upload_image():
    """
    Step 1: User uploads an image via the camera component.
    The AI processes it in secret and returns the three '?' options to the user.
    """
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
        
        # Return success but DO NOT give away the answer yet! 
        # This populates the three '?' options on your sketch screen.
        return jsonify({
            "message": "Image analyzed successfully. Time to guess!",
            "options": ["recyclable", "compostable", "landfill"]
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"AI Processing failed: {str(e)}"}), 500


@app.route("/api/verify-guess", methods=["POST"])
def verify_guess():
    """
    Step 2: User selects one of the 3 '?' boxes.
    Evaluates their choice against the AI's result and updates points/streaks persistently.
    """
    data = request.json or {}
    user_id = int(data.get("user_id", 1))
    user_guess = data.get("guess", "").lower()
    
    # Check if there is an active scan awaiting confirmation
    scan_session = ACTIVE_SCANS.get(user_id)
    if not scan_session:
        return jsonify({"error": "No active upload session found for this user."}), 400
        
    true_category = scan_session["true_category"]
    
    # Base configuration values for our vine mechanics
    points_awarded = 0
    is_correct = (user_guess == true_category)
    now = datetime.utcnow()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Ensure profile metrics placeholder defaults are established for this profile ID
    cursor.execute("INSERT OR IGNORE INTO user_scores (user_id, total_points, streak_count) VALUES (?, 0, 0)", (user_id,))
    
    # Grab current metrics stats out of the SQLite tables
    user_profile = cursor.execute("SELECT * FROM user_scores WHERE user_id = ?", (user_id,)).fetchone()
    total_points = user_profile["total_points"]
    streak_count = user_profile["streak_count"]
    last_upload_at = user_profile["last_upload_at"]
    
    if is_correct:
        points_awarded = 10
        total_points += points_awarded
        
        # Streak mechanics: check if last scan was within 24 hours to grow vine
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
        
    # Write updated levels metadata properties back to database
    cursor.execute("""
        UPDATE user_scores 
        SET total_points = ?, streak_count = ?, last_upload_at = ? 
        WHERE user_id = ?
    """, (total_points, streak_count, last_upload_at, user_id))
    
    # Maintain a chronological analytics trace file history block log
    cursor.execute("""
        INSERT INTO scan_history (user_id, predicted_category, user_guess, is_correct, points_awarded)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, true_category, user_guess, int(is_correct), points_awarded))
    
    conn.commit()
    conn.close()
    
    # Clean up the processed session scan
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

@app.route("/api/register", methods=["POST",'OPTIONS'])
def register_user():
    """
    Registers a new unique user profile and initiates their starting dashboard metrics.
    """
    if request.method == 'OPTIONS':
        return jsonify({"message": "Preflight check successful."}), 200
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "Username and password are required fields."}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long."}), 400

    # Scramble the password using secure cryptographic hashing
    hashed_password = generate_password_hash(password)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. Insert row into core users table
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, hashed_password)
        )
        new_user_id = cursor.lastrowid

        # 2. Automatically provision an empty matching baseline stats sheet
        cursor.execute(
            "INSERT INTO user_scores (user_id, total_points, streak_count) VALUES (?, 0, 0)",
            (new_user_id,)
        )
        
        conn.commit()
        return jsonify({
            "success": True,
            "message": "Account created successfully!",
            "user_id": new_user_id
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({"error": "Username is already taken. Try another name!"}), 400
    finally:
        conn.close()


@app.route("/api/login", methods=["POST"])
def login_user():
    """
    Authenticates a user's credentials against the secure database hash.
    """
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "Please provide both username and password."}), 400

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()

    # Verify matching hash matrices
    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid username or password combination."}), 401

    return jsonify({
        "success": True,
        "message": f"Welcome back, {username}!",
        "user_id": user["id"]
    }), 200

# Add these endpoints right above the if __name__ == "__main__": block in main.py

@app.route("/", methods=["GET"])
def home_fallback():
    """
    Prevents confusing 404 errors if a developer or user visits the bare API URL.
    """
    return jsonify({
        "status": "online",
        "app": "Verte AI Engine Backend API",
        "version": "1.0.0",
        "endpoints": ["/api/upload", "/api/verify-guess", "/api/register", "/api/login", "/api/user-stats/<id>"]
    }), 200


@app.route("/api/user-stats/<int:user_id>", methods=["GET"])
def get_user_stats(user_id):
    """
    Fetches historical points matrix properties to display on the profile dashboard header.
    """
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
    # Read port from cloud environment variable, fallback to 5000 locally
    port = int(os.environ.get("PORT", 5000))
    # Host must be 0.0.0.0 in production so it binds to the cloud network interface
    app.run(host="0.0.0.0", port=port, debug=False)