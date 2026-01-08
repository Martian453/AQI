import sqlite3
import csv
import os

# 1. Connect to the Database
db_path = "aqi.db"
if not os.path.exists(db_path):
    print(f"❌ Error: Database file '{db_path}' not found.")
    exit()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 2. Select All Data
# This will now automatically include the new columns (ph, turbidity, water_level)
query = "SELECT * FROM aqi_data ORDER BY timestamp DESC"
cursor.execute(query)
rows = cursor.fetchall()
headers = [description[0] for description in cursor.description]

# 3. Write to CSV
csv_file = "aqi_export.csv"
with open(csv_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(headers) # Write Column Names
    writer.writerows(rows)   # Write Data Rows

conn.close()

print(f"✅ Success! Data extracted to '{csv_file}'")
print(f"   Found {len(rows)} records.")
