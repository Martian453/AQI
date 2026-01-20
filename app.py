from flask import Flask, render_template, jsonify
import sqlite3
import requests
import csv
import io
from flask import Flask, render_template, jsonify, Response

app = Flask(__name__)

# CONSTANTS
DB_FILE = "aqi.db"
ESP_URL = "http://10.161.184.150/data" # ESP32 Proxy URL



def get_data():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Get last 50 readings for the chart
    cursor.execute("SELECT * FROM aqi_data ORDER BY timestamp DESC LIMIT 50")
    rows = cursor.fetchall()
    conn.close()
    # Reverse to show oldest first on the chart
    return rows[::-1]

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route('/water_data')
def water_data():
    try:
        # Fetch data from ESP32 with a short timeout (e.g. 2 seconds)
        response = requests.get(ESP_URL, timeout=2)
        if response.status_code == 200:
            return response.json()
        else:
            return jsonify({'error': 'ESP32 Error', 'ph': 0, 'turbidity': 0, 'level': 0})
    except Exception as e:
        # If ESP is offline, return zeros so dashboard doesn't break
        return jsonify({'error': str(e), 'ph': 0, 'turbidity': 0, 'level': 0})

@app.route("/data")
def data():
    rows = get_data()
    
    # Structure data for Chart.js
    # Filter function: Keep value if not None and < 2000, else 0
    def clean(val):
        if val is None: return 0
        if val > 2000: return 0 # Filter huge OCR errors
        return val

    # Row format: (id, timestamp, pm25, pm10, co, so2, no2, o3)
    response = {
        "timestamps": [r[1] for r in rows],
        "pm25": [clean(r[2]) for r in rows],
        "pm10": [clean(r[3]) for r in rows],
        "co":   [clean(r[4]) for r in rows],
        "so2":  [clean(r[5]) for r in rows],
        "no2":  [clean(r[6]) for r in rows],
        "o3":   [clean(r[7]) for r in rows]
    }
    return jsonify(response)

@app.route("/export_csv")
def export_csv():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM aqi_data ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    
    # Get column headers
    headers = [description[0] for description in cursor.description]
    conn.close()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=aqi_water_report.csv"}
    )

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
