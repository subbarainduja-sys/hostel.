# Hostel Attendance - QR / Face Capture System
Flask + SQLite + OpenCV. Face feature is **face detection/capture only, not identity recognition**.

## Run on Windows
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000 (DB and demo data are created automatically).

**Demo credentials (change before deployment):** admin / admin123 - STU001 / student123

## How it works
- QR: admin generates a token valid 60 s; student scans in-app (jsQR); server checks token, expiry, duplicate.
- Face: browser camera -> JPEG -> Flask -> OpenCV Haar face detection -> saved in uploads/faces -> attendance FACE.

## Deploy (Render)
Push to GitHub, create a Web Service, build `pip install -r requirements.txt`, start `gunicorn app:app`,
set env `SECRET_KEY`. Render gives HTTPS, which browsers require for camera access (localhost is exempt).
Use PostgreSQL via `DATABASE_URL` for persistent data (Render's disk is ephemeral).

## Future work
Rooms, leave requests, student edit/profile, PDF export, real face recognition, liveness, SMS/email alerts, geofencing.
