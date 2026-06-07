-- backend-api/app/database/schema.sql

-- 1. Main Core Users Profile Table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Scores, Levels, and Streaks
CREATE TABLE IF NOT EXISTS user_scores (
    user_id INTEGER PRIMARY KEY,
    total_points INTEGER DEFAULT 0,
    streak_count INTEGER DEFAULT 0,
    last_upload_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. Historical Logs Analytics Tracker 
CREATE TABLE IF NOT EXISTS scan_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    predicted_category TEXT,
    user_guess TEXT,
    is_correct INTEGER,
    points_awarded INTEGER,
    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);