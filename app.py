from flask import Flask, render_template, jsonify
import sqlite3

app = Flask(__name__)

DB_FILE = "aqi.db"

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

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
