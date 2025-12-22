import cv2
import pytesseract
import time
import sqlite3
import re
import numpy as np

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------
# PATH TO TESSERACT - UPDATE THIS IF NEEDED
# Common paths:
# Windows: r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# Linux/Mac: "/usr/bin/tesseract" (usually auto-detected)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# DATABASE FILE
DB_FILE = "aqi.db"

# REGIONS OF INTEREST (ROI)
# Format: 'Label': (x, y, width, height)
# ⚠️ YOU MUST ADJUST THESE TO MATCH YOUR SCREEN / CAMERA POSITION
# Use the "Calibration Mode" window to find the right coordinates.
ROIS = {
    "PM2.5": (50, 100, 100, 100),
    "PM10":  (250, 100, 100, 100),
    "CO":    (50, 250, 100, 100),
    "NO2":   (250, 250, 100, 100),
    "SO2":   (50, 400, 100, 100),
    "O3":    (250, 400, 100, 100)
}

# ---------------------------------------------------------
# UTILITY FUNCTIONS
# ---------------------------------------------------------
def clean_text(text):
    """Extracts the first valid floassting point number from text."""
    # Allow digits and dots, remove everything else
    clean = re.sub(r'[^0-9.]', '', text)
    try:
        val = float(clean)
        return val
    except ValueError:
        return None

def save_to_db(data):
    """Saves a dictionary of pollutants to the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO aqi_data (pm25, pm10, co, so2, no2, o3)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data.get("PM2.5"),
        data.get("PM10"),
        data.get("CO"),
        data.get("SO2"),
        data.get("NO2"),
        data.get("O3")
    ))
    conn.commit()
    conn.close()
    print(f"💾 Saved to DB: {data}")

def preprocess_roi(roi, invert=False):
    """Applies grayscale and thresholding. Optionally inverts for Dark Mode."""
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    
    if invert:
        gray = cv2.bitwise_not(gray)
        
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    return thresh

# ---------------------------------------------------------
# MAIN LOOPS
# ---------------------------------------------------------
def main():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) # CAP_DSHOW for faster startup on Windows
    
    if not cap.isOpened():
        print("❌ Error: Could not open camera.")
        return

    print("✅ Camera started.")
    print("PRESS 's' TO SAVE DATA MANUALLY")
    print("PRESS 'q' TO QUIT")
    
    last_save_time = time.time()
    SAVE_INTERVAL = 300  # 5 minutes in seconds

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Error: Failed to capture frame.")
            break

        # Display frame with rectangles
        display_frame = frame.copy()
        
        # Draw rectangles for alignment
        for label, (x, y, w, h) in ROIS.items():
            cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(display_frame, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Show status
        time_left = int(SAVE_INTERVAL - (time.time() - last_save_time))
        status_msg = f"Next Auto-Capture: {time_left}s | Press 's' to Save Now"
        cv2.putText(display_frame, status_msg, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        cv2.imshow("AQI Monitor - Alignment View", display_frame)

        # TRIGGER OCR ON TIMER OR KEYPRESS
        key = cv2.waitKey(1) & 0xFF
        should_save = False
        
        if time.time() - last_save_time > SAVE_INTERVAL:
            print("⏰ Timer triggered.")
            should_save = True
        elif key == ord('s'):
            print("👇 Manual trigger.")
            should_save = True
            
        if should_save:
            print("📸 Capturing and processing... (This may take a moment)")
            # Show "Processing" on screen
            cv2.putText(display_frame, "PROCESSING...", (200, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            cv2.imshow("AQI Monitor - Alignment View", display_frame)
            cv2.waitKey(1) # Force update UI

            current_readings = {}
            for label, (x, y, w, h) in ROIS.items():
                roi = frame[y:y+h, x:x+w]
                
                # --- SMART OCR STRATEGY ---
                # Attempt 1: Standard (Expects Black Text on White Background)
                thresh_standard = preprocess_roi(roi, invert=False)
                config = "--psm 7 -c tessedit_char_whitelist=0123456789."
                text = pytesseract.image_to_string(thresh_standard, config=config)
                val = clean_text(text)
                
                # Attempt 2: Dark Mode (Expects White Text on Dark Background)
                if val is None:
                    thresh_inverted = preprocess_roi(roi, invert=True)
                    text_inv = pytesseract.image_to_string(thresh_inverted, config=config)
                    val = clean_text(text_inv)
                    if val is not None:
                        print(f"   🌑 Dark Mode detected for {label}")

                print(f"   🔍 Read '{label}': {val}")
                current_readings[label] = val
            
            save_to_db(current_readings)
            last_save_time = time.time()

        if key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # Ensure DB exists
    import database
    database.init_db()
    
    main()
