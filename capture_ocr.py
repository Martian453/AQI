import requests
import cv2
import pytesseract
import time
import sqlite3
import re
import numpy as np
import statistics
from datetime import datetime
from collections import deque

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------
# PATH TO TESSERACT
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# DATABASE FILE
DB_FILE = "aqi.db"
ESP_URL = "http://10.161.184.150/data"

# ---------------------------------------------------------
# UTILITY FUNCTIONS
# ---------------------------------------------------------
def get_water_data():
    try:
        r = requests.get(ESP_URL, timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        # print(f"⚠️ Water Usage Error: {e}") # Reduce spam
        pass
    return {'ph': 0, 'turbidity': 0, 'level': 0}

def save_to_db(data):
    """Saves the voted AQI data AND Water Data to the database."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # fetch water data
    w = get_water_data()
    
    timestamp = datetime.now()
    
    c.execute('''INSERT INTO aqi_data 
                 (timestamp, pm25, pm10, co, so2, no2, o3, ph, turbidity, water_level)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (timestamp, 
               data.get('PM2.5', 0), 
               data.get('PM10', 0), 
               data.get('CO', 0), 
               data.get('SO2', 0), 
               data.get('NO2', 0), 
               data.get('O3', 0),
               w.get('ph', 0),
               w.get('turbidity', 0),
               w.get('level', 0)
              ))
    conn.commit()
    conn.close()
    print(f"💾 Saved to DB: AQI + Water (pH:{w.get('ph')} Turb:{w.get('turbidity')})")

def preprocess_frame(frame):
    """
    Full-frame preprocessing to make text pop out against background.
    """
    # 1. Convert to Grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # 2. CLAHE (Contrast Limited Adaptive Histogram Equalization)
    #    Helps if lighting is uneven
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)
    
    # 3. Resize / Upscale
    #    Upscaling helps Tesseract read small text
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    
    # 4. Blur to reduce noise
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # 5. Thresholding (Adaptive or Otsu)
    #    Otsu is often good for black text on light bg or vice versa
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    return thresh

def extract_value(text, label_patterns):
    """
    Scans the OCR text for a number appearing after any of the label patterns.
    Returns the first valid float found, or None.
    """
    for pattern in label_patterns:
        # Regex explanation:
        # pattern: the label (e.g., "PM2\.5")
        # [:\-\s]*: optional separator (colon, dash, space)
        # ([0-9]+\.?[0-9]*): the number group
        regex = rf"{pattern}[:\-\s]*([0-9]+\.?[0-9]*)"
        match = re.search(regex, text, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1))
                return val
            except ValueError:
                continue
    return None

# ---------------------------------------------------------
# OCR & LOGIC
# ---------------------------------------------------------
def main():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280) # Try HD if available
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    if not cap.isOpened():
        print("❌ Error: Could not open camera.")
        return

    print("✅ Camera started (Full-Screen Mode).")
    print("PRESS 's' TO SAVE DATA MANUALLY")
    print("PRESS 'q' TO QUIT")
    
    last_save_time = time.time()
    SAVE_INTERVAL = 300  # 5 minutes
    
    # regex patterns for each pollutant (list allows aliases)
    LABELS = {
        "PM2.5": [r"PM\s*2\.?5", r"PM25"],
        "PM10":  [r"PM\s*10", r"PM1O"],
        "CO":    [r"CO", r"C0"],
        "NO2":   [r"NO\s*2", r"N02"],
        "O3":    [r"O\s*3", r"03"],
        "SO2":   [r"SO\s*2", r"S02"]
    }

    while True:
        try:
            ret, frame = cap.read()
            if not ret:
                time.sleep(1)
                continue

            # Display Feed
            display_frame = frame.copy()
            
            # Show status info
            time_left = int(SAVE_INTERVAL - (time.time() - last_save_time))
            status_text = f"Auto-Save: {time_left}s | 's' to Save"
            cv2.putText(display_frame, status_text, (20, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            cv2.imshow("AQI Monitor - Full Screen", display_frame)

            # Check Triggers
            key = cv2.waitKey(1) & 0xFF
            should_save = False
            
            if time.time() - last_save_time > SAVE_INTERVAL:
                print("⏰ Timer triggered.")
                should_save = True
            elif key == ord('s'):
                print("👇 Manual trigger.")
                should_save = True
            elif key == ord('q'):
                break

            # BURST CAPTURE LOGIC
            if should_save:
                print("📸 PROCESSING BURST (Full Screen)...")
                cv2.putText(display_frame, "ANALYZING...", (200, 360), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
                cv2.imshow("AQI Monitor - Full Screen", display_frame)
                cv2.waitKey(1) # Force UI update

                # Buffer for burst readings
                burst_readings = {k: [] for k in LABELS.keys()}
                
                # Take 10 frames for stability (increased from 5 for better chance)
                for i in range(10): 
                    ret, fr = cap.read()
                    if not ret: continue
                    
                    # Preprocess
                    processed = preprocess_frame(fr)
                    
                    # OCR Full Frame
                    # EXPANDED WHITELIST: Include lowercase a-z so 'g' isn't read as '9'
                    # Also include / and ³ (if possible, though standard chars often suffice)
                    config = r"--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789.ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz%:-/"
                    text = pytesseract.image_to_string(processed, config=config)
                    
                    # Extract values
                    for label_key, patterns in LABELS.items():
                        # REGEX UPDATE:
                        # Look for Label -> Separator -> Number
                        # Stop at space or unit start (like u, g, p) to avoid merging '63g' -> '639'
                        # Use word boundary \b or explicit space handling
                        for pat in patterns:
                            # Match: Label + optional sep + (GROUP: number) + optional space + unit or end
                            # We don't strictly match unit, just ensuring we don't grab it as part of number
                            regex = rf"{pat}[:\-\s]+([0-9]+\.?[0-9]*)"
                            match = re.search(regex, text, re.IGNORECASE)
                            if match:
                                try:
                                    val_str = match.group(1)
                                    # Double check: if it ends with '9' and text had 'g' next to it?
                                    # Hard to know in regex alone, but the whitelist fix should solve 80%
                                    val = float(val_str)
                                    
                                    # Sanity Bounds Check (Heuristic)
                                    # PM2.5 > 500 is rare, detected 639 is suspicious if previous was 63
                                    if label_key == "PM2.5" and val > 600: continue 
                                    
                                    burst_readings[label_key].append(val)
                                    break # Found a match for this label, stop checking logic patterns
                                except ValueError:
                                    continue
                    
                    print(f"   [Frame {i+1}/10] Scanned.")
                    # Optional: time.sleep(0.1)

                # Aggregate Results (Median/Mode)
                final_data = {}
                for k, vals in burst_readings.items():
                    if not vals:
                        print(f"   ⚠️ {k}: No valid data found in burst.")
                        final_data[k] = 0.0 # Default fallback
                    else:
                        # Median is safer for removing outliers than mean
                        final_val = statistics.median(vals)
                        final_data[k] = final_val
                        print(f"   ✅ {k}: {vals} -> Voted: {final_val}")

                # Save
                save_to_db(final_data)
                last_save_time = time.time()

        except Exception as e:
            print(f"⚠️ Error loop: {e}")
            time.sleep(1)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # Ensure DB exists
    import database
    database.init_db()
    main()
