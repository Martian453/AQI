import sqlite3


try:
    conn = sqlite3.connect("aqi.db")
    cursor = conn.cursor()
    
    # Check table info to verify columns
    cursor.execute("PRAGMA table_info(aqi_data)")
    columns = [info[1] for info in cursor.fetchall()]
    print(f"Columns found: {columns}")
    
    if "water_level" not in columns:
        print("❌ CRITICAL: 'water_level' column is MISSING!")
    else:
        print("'water_level' column exists.")

    # Fetch last 5 rows
    cursor.execute("SELECT id, timestamp, ph, turbidity, water_level FROM aqi_data ORDER BY timestamp DESC LIMIT 5")
    rows = cursor.fetchall()
    
    print("\n--- LATEST 5 RECORDS (Water Data) ---")
    print(f"{'ID':<5} {'Timestamp':<25} {'pH':<10} {'Turbidity':<10} {'Level':<10}")
    print("-" * 65)
    for row in rows:
        print(f"{row[0]:<5} {row[1]:<25} {row[2]:<10} {row[3]:<10} {row[4]:<10}")

    conn.close()

except Exception as e:
    print(f"Error: {e}")
