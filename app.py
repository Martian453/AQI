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
    # Row format: (id, timestamp, pm25, pm10, co, so2, no2, o3)
    response = {
        "timestamps": [r[1] for r in rows],
        "pm25": [r[2] if r[2] is not None else 0 for r in rows],
        "pm10": [r[3] if r[3] is not None else 0 for r in rows],
        "co":   [r[4] if r[4] is not None else 0 for r in rows],
        "so2":  [r[5] if r[5] is not None else 0 for r in rows],
        "no2":  [r[6] if r[6] is not None else 0 for r in rows],
        "o3":   [r[7] if r[7] is not None else 0 for r in rows]
    }
    return jsonify(response)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
