# 🌍 Vision-Based AQI Monitoring System

A complete start-to-end solution for monitoring Air Quality Index (AQI) by capturing a mobile screen using a laptop camera, extracting data via OCR, and visualizing it on a live dashboard.
    
### ✨ Key Features
*   **Smart OCR**: Automatically handles both Light and Dark mode apps.
*   **Burst Mode**: Captures 5 frames instantly and uses "Voting Logic" to ensure 100% accuracy, eliminating camera shake/blur.
*   **Premium Dashboard**: Real-time dark mode UI with live safety color indicators and trend analysis.
*   **Database**: Automatic logging to SQLite for historical data analysis.

## 📂 Project Structure

```
AQI_VISION_SYSTEM/
│
├── app.py                 # Flask Backend (serves dashboard & API)
├── capture_ocr.py         # Capture & OCR Script (The "Eyes" of the system)
├── database.py            # Database Setup Script
├── aqi.db                 # SQLite Database (Auto-created)
│
├── templates/
│   └── dashboard.html     # Frontend Dashboard (The "Face" of the system)
│
└── README.md              # This file
```

---

## 🚀 Installation & Setup

### 1. Install Python Dependencies
Open your terminal/command prompt and run:
```bash
pip install flask opencv-python pytesseract
```

### 2. Install Tesseract OCR (Crucial Step!)
Tesseract is the engine that reads text from images. You must install it separately.
*   **Download**: [Tesseract via UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) (download the 64-bit .exe).
*   **Install**: Run the installer. **Note the installation path** (usually `C:\Program Files\Tesseract-OCR`).
*   **Verify Path**: Ensure line 14 in `capture_ocr.py` matches your installation path:
    ```python
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    ```

### 3. Initialize Database
Run the setup script once to create the empty database:
```bash
python database.py
```
*You should see: "✅ Database 'aqi.db' initialized successfully."*

---

## 🏃‍♂️ How to Run

You need to run **two separate terminals** (one for the website, one for the camera).

### Terminal 1: Start the Dashboard
```bash
python app.py
```
*   Go to **http://127.0.0.1:5000** in your browser.
*   The chart will be empty initially.

### Terminal 2: Start the Camera & OCR
```bash
python capture_ocr.py
```
1.  A window named "Alignment View" will appear.
2.  **Align your phone**: Hold your phone in front of the camera so the AQI numbers fall inside the **green boxes**.
3.  **Adjust ROIs**: If the boxes don't match, open `capture_ocr.py` and adjust the `ROIS` dictionary coordinates (x, y, width, height).
4.  The system captures data every **5 minutes** automatically.
5.  **Manual Save**: Press **'s'** to force an immediate capture/save for testing.

---

## 🧠 Viva-Ready Explanation

**Q: How does the system work?**
**A:** "The system uses Computer Vision. The laptop camera acts as a sensor, capturing the phone screen. We use **OpenCV** to process the image (converting to grayscale and thresholding) to make text clear. Then, **Tesseract OCR** reads the text from specific regions (ROIs). This data is cleaned using Python and stored in an **SQLite** database. Finally, a **Flask** web server sends this data to the frontend, where **Chart.js** updates the graph in real-time."

**Q: Why use SQLite?**
**A:** "It's lightweight, serverless (doesn't require a separate process like MySQL), and perfect for embedded or standalone monitoring systems like this."

**Q: How do you handle different phone screens?**
**A:** "We use a Region of Interest (ROI) based approach. In a real-world scenario, we would implement dynamic text detection, but for this prototype, we define fixed coordinates that can be calibrated to the specific device position."
