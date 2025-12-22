import sqlite3

def init_db():
    conn = sqlite3.connect("aqi.db")
    cursor = conn.cursor()
    
    # Create table for 6 pollutants + timestamp
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS aqi_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        pm25 REAL,
        pm10 REAL,
        co REAL,
        so2 REAL,
        no2 REAL,
        o3 REAL
    )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Database 'aqi.db' initialized successfully.")

if __name__ == "__main__":
    init_db()
