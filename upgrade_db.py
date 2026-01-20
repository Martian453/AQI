import sqlite3

DB_FILE = "aqi.db"

def add_column(cursor, col_name, col_type):
    try:
        cursor.execute(f"ALTER TABLE aqi_data ADD COLUMN {col_name} {col_type}")
        print(f"Added column: {col_name}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"Column {col_name} already exists.")
        else:
            print(f"Error adding {col_name}: {e}")

def upgrade():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print("Upgrading Database for Water Data...")
    add_column(cursor, "ph", "REAL")
    add_column(cursor, "turbidity", "REAL")
    add_column(cursor, "water_level", "REAL")
    
    conn.commit()
    conn.close()
    print("Database Upgrade Complete.")

if __name__ == "__main__":
    upgrade()
