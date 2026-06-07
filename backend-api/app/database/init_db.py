# init_db.py
import sqlite3
import os

db_path = "verte.db"
schema_path = "schema.sql"  # Points to your schema file

print("🗄️ Initializing SQLite Database...")

# Open connection and read your schema queries
with sqlite3.connect(db_path) as conn:
    if os.path.exists(schema_path):
        with open(schema_path, "r") as f:
            schema_sql = f.read()
        
        # Execute the SQL tables initialization
        conn.executescript(schema_sql)
        print("✅ Database tables created successfully inside 'verte.db'!")
    else:
        print("❌ Error: Could not find your 'schema' file.")