import cv2
import pytesseract
import time
import sqlite3
import re
import numpy as np
import statistics

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
    # Left Column (PM2.5, CO, SO2) -> Shifted Right to match screen
    "PM2.5": (180, 240, 110, 60),
    "CO":    (320, 240, 110, 60),  # This seems to be PM10 in your screenshot, swapping columns
    
    # Wait, looking at screenshot:
    # Row 1: PM2.5 (Left), PM10 (Right)
    # Row 2: CO (Left), NO2 (Right)
    # Row 3: O3 (Left), SO2 (Right)
    
    # UPDATED MAPPING BASED ON IMAGE:
    "PM2.5": (200, 90, 50, 30),
    "PM10":  (400, 90, 50, 30),
    
    "CO":    (200, 200, 50, 30),
    "NO2":   (400, 200, 50, 30),
    
    "O3":    (200, 330, 50, 30),  # Assuming layout continues
    "SO2":   (400, 330, 50, 30)
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
    """Upscales and thresholds the image for maximum OCR accuracy."""
    # 1. Grayscale
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # 2. Invert if needed (for Dark Mode)
    if invert:
        gray = cv2.bitwise_not(gray)

    # 3. RESIZE (Critical for accuracy!) 
    # Upscale by 3x so Tesseract can see details clearly
    gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

    # 4. Blur & Threshold
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    
    # 5. Add Border/Padding (Tesseract likes whitespace around text)
    thresh = cv2.copyMakeBorder(thresh, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=255)
    
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
    
    # Check resolution
    ret, frame = cap.read()
    if ret:
        h, w = frame.shape[:2]
        print(f"📷 Camera Resolution: {w}x{h}")

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
            print("📸 BURST MODE: Capturing 5 frames...")
            # Show "Processing" on screen
            cv2.putText(display_frame, "PROCESSING BURST...", (200, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
            cv2.imshow("AQI Monitor - Alignment View", display_frame)
            cv2.waitKey(1)

            # Dictionary to store lists of readings: {'PM2.5': [50, 50, None, 52], ...}
            burst_data = {k: [] for k in ROIS.keys()}
            
            # BURST LOOP: Take 5 samples
            for i in range(5):
                # Capture fresh frame
                ret, frame = cap.read()
                if not ret: continue
                
                print(f"   [Frame {i+1}/5] Analyzing...")
                
                for label, (x, y, w, h) in ROIS.items():
                    # SAFETY CHECK: Ensure ROI is inside the frame
                    height, width = frame.shape[:2]
                    if y+h > height or x+w > width:
                        print(f"   ⚠️ SKIPPING {label}: Coordinate ({x},{y}) out of bounds (Frame size: {width}x{height})")
                        continue

                    roi = frame[y:y+h, x:x+w]
                    
                    # --- SMART OCR STRATEGY ---
                    val = None
                    # Use 'PSM 6' (Assume a single uniform block of text)
                    config = "--psm 6 -c tessedit_char_whitelist=0123456789."
                    
                    # Attempt 1: Standard
                    thresh_standard = preprocess_roi(roi, invert=False)
                    text = pytesseract.image_to_string(thresh_standard, config=config)
                    val = clean_text(text)
                    
                    # Attempt 2: Dark Mode
                    if val is None:
                        thresh_inverted = preprocess_roi(roi, invert=True)
                        text_inv = pytesseract.image_to_string(thresh_inverted, config=config)
                        val = clean_text(text_inv)
                    
                    # Append result (even None) to list
                    burst_data[label].append(val)
                
                # Small delay between shots
                time.sleep(0.2)

            # VOTE: Find the most common value (Mode)
            final_readings = {}
            for label, values in burst_data.items():
                # Filter out None values for voting
                valid_values = [v for v in values if v is not None]
                
                if not valid_values:
                    final_val = None
                    print(f"   ❌ {label}: No valid data.")
                else:
                    try:
                        final_val = statistics.mode(valid_values)
                        print(f"   ✅ {label}: {valid_values} -> Voted: {final_val}")
                    except statistics.StatisticsError:
                        # If tie (e.g. [50, 52]), take the first one
                        final_val = valid_values[0]
                        print(f"   ⚠️ {label}: Tie {valid_values} -> Took: {final_val}")
                
                final_readings[label] = final_val



            save_to_db(final_readings)
            last_save_time = time.time()

        # Key Controls
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # Ensure DB exists
    import database
    database.init_db()
    
    main()
