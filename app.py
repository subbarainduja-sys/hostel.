"""Hostel Attendance - QR / Face Capture. NOTE: face feature is face DETECTION only (OpenCV Haar),
not biometric identity recognition."""
import os, io, csv, base64, secrets, uuid
from datetime import datetime, timedelta, date
from functools import wraps
import cv2, numpy as np, qrcode
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from models import db, User, Attendance, QRToken, Room, Leave

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
os.makedirs(Config.FACE_DIR, exist_ok=True)
os.makedirs(os.path.join(Config.FACE_DIR, ".."), exist_ok=True)
FACE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

def seed():
    db.create_all()
    if not User.query.first():  # DEMO credentials - change before deployment!
        db.session.add(User(username="admin", name="Warden", role="ADMIN", password_hash=generate_password_hash("admin123")))
        for i, n in enumerate(["Arun Kumar", "Priya S", "Karthik R"], 1):
            db.session.add(User(username=f"STU00{i}", name=n, role="STUDENT", block="A" if i < 3 else "B",
                                room=f"10{i}", password_hash=generate_password_hash("student123")))
        db.session.commit()

def login_required(role):
    def deco(f):
        @wraps(f)
        def w(*a, **k):
            if "uid" not in session: return redirect(url_for("login"))
            if session["role"] != role:
                flash("Access denied", "danger"); return redirect(url_for("index"))
            return f(*a, **k)
        return w
    return deco

def me(): return db.session.get(User, session["uid"])

def mark(user, method, face=None, token=None):
    """Record attendance once per day. Returns (ok, message)."""
    today, now = date.today(), datetime.now()
    if Attendance.query.filter_by(user_id=user.id, date=today).first():
        return False, "Duplicate attendance: already marked today"
    db.session.add(Attendance(user_id=user.id, date=today, time=now.strftime("%H:%M:%S"),
                              method=method, status="PRESENT", face_image=face, qr_token=token))
    try: db.session.commit()
    except Exception: db.session.rollback(); return False, "Database error"
    return True, "Attendance Marked Successfully"

# ---------- auth ----------
@app.route("/")
def index():
    if "uid" not in session: return redirect(url_for("login"))
    return redirect(url_for("admin_dashboard" if session["role"] == "ADMIN" else "student_dashboard"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(username=request.form.get("username", "").strip()).first()
        if u and check_password_hash(u.password_hash, request.form.get("password", "")):
            session.clear(); session.update(uid=u.id, role=u.role)
            return redirect(url_for("index"))
        flash("Invalid login", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("login"))

# ---------- admin ----------
@app.route("/admin/dashboard")
@login_required("ADMIN")
def admin_dashboard():
    total = User.query.filter_by(role="STUDENT").count()
    present = Attendance.query.filter_by(date=date.today()).count()
    recent = Attendance.query.order_by(Attendance.id.desc()).limit(8).all()
    return render_template("admin/dashboard.html", total=total, present=present, absent=total - present,
                           pct=round(present / total * 100, 1) if total else 0, recent=recent)

@app.route("/api/chart-data")
@login_required("ADMIN")
def chart_data():
    days = [date.today() - timedelta(days=i) for i in range(6, -1, -1)]
    weekly = [Attendance.query.filter_by(date=d).count() for d in days]
    total = User.query.filter_by(role="STUDENT").count()
    present = weekly[-1]
    blocks = {}
    for a in Attendance.query.filter_by(date=date.today()).all():
        blocks[a.user.block or "-"] = blocks.get(a.user.block or "-", 0) + 1
    return jsonify(labels=[d.strftime("%a") for d in days], weekly=weekly, present=present,
                   absent=total - present, blocks=blocks)

@app.route("/admin/students", methods=["GET", "POST"])
@login_required("ADMIN")
def admin_students():
    if request.method == "POST":
        f = request.form
        sid, name, pw = f.get("username", "").strip(), f.get("name", "").strip(), f.get("password", "")
        if not sid or not name or len(pw) < 6: flash("Fill all fields (password min 6 chars)", "danger")
        elif User.query.filter_by(username=sid).first(): flash("Student ID already exists", "danger")
        else:
            db.session.add(User(username=sid, name=name, role="STUDENT", block=f.get("block"), room=f.get("room"),
                                password_hash=generate_password_hash(pw)))
            db.session.commit(); flash("Student added", "success")
        return redirect(url_for("admin_students"))
    q = request.args.get("q", "")
    s = User.query.filter_by(role="STUDENT")
    if q: s = s.filter(User.name.ilike(f"%{q}%") | User.username.ilike(f"%{q}%"))
    return render_template("admin/students.html", students=s.all(), q=q)

@app.route("/admin/students/delete/<int:id>", methods=["POST"])
@login_required("ADMIN")
def delete_student(id):
    u = db.session.get(User, id)
    if u and u.role == "STUDENT":
        Attendance.query.filter_by(user_id=id).delete(); db.session.delete(u); db.session.commit()
        flash("Student deleted", "success")
    return redirect(url_for("admin_students"))

@app.route("/admin/qr-attendance")
@login_required("ADMIN")
def admin_qr(): return render_template("admin/qr_attendance.html")

@app.route("/api/generate-qr", methods=["POST"])
@login_required("ADMIN")
def generate_qr():
    QRToken.query.filter(QRToken.expires_at < datetime.utcnow()).delete()
    tok = secrets.token_urlsafe(24)
    db.session.add(QRToken(token=tok, expires_at=datetime.utcnow() + timedelta(seconds=Config.QR_TTL)))
    db.session.commit()
    url = request.host_url.rstrip("/") + "/attendance/qr/" + tok
    buf = io.BytesIO(); qrcode.make(url).save(buf, format="PNG")
    return jsonify(qr="data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(), ttl=Config.QR_TTL)

@app.route("/admin/reports")
@login_required("ADMIN")
def admin_reports():
    q = Attendance.query.join(User)
    d, m, st, name = (request.args.get(k, "") for k in ("date", "method", "status", "name"))
    if d: q = q.filter(Attendance.date == date.fromisoformat(d))
    if m: q = q.filter(Attendance.method == m)
    if st: q = q.filter(Attendance.status == st)
    if name: q = q.filter(User.name.ilike(f"%{name}%") | User.username.ilike(f"%{name}%"))
    rows = q.order_by(Attendance.date.desc(), Attendance.time.desc()).all()
    if request.args.get("export") == "csv":
        o = io.StringIO(); w = csv.writer(o)
        w.writerow(["Student ID", "Name", "Date", "Time", "Room", "Method", "Status"])
        for a in rows: w.writerow([a.user.username, a.user.name, a.date, a.time, a.user.room, a.method, a.status])
        return Response(o.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=report.csv"})
    return render_template("admin/reports.html", rows=rows)

# ---------- student ----------
@app.route("/student/dashboard")
@login_required("STUDENT")
def student_dashboard():
    u = me(); recs = Attendance.query.filter_by(user_id=u.id).order_by(Attendance.date.desc()).all()
    days = db.session.query(Attendance.date).distinct().count() or 1
    return render_template("student/dashboard.html", u=u, recs=recs[:5], present=len(recs), days=days,
                           pct=round(len(recs) / days * 100, 1), today=bool(recs and recs[0].date == date.today()))

@app.route("/student/qr-attendance")
@login_required("STUDENT")
def student_qr(): return render_template("student/qr_attendance.html")

@app.route("/student/face-attendance")
@login_required("STUDENT")
def student_face(): return render_template("student/face_attendance.html")

@app.route("/student/attendance-history")
@login_required("STUDENT")
def student_history():
    recs = Attendance.query.filter_by(user_id=session["uid"]).order_by(Attendance.date.desc()).all()
    days = db.session.query(Attendance.date).distinct().count() or 1
    return render_template("student/attendance_history.html", recs=recs, present=len(recs),
                           absent=max(days - len(recs), 0), pct=round(len(recs) / days * 100, 2))

def use_token(tok):
    t = QRToken.query.filter_by(token=tok).first()
    if not t: return False, "Invalid QR"
    if t.expires_at < datetime.utcnow(): return False, "Expired QR"
    return mark(me(), "QR", token=tok)

@app.route("/attendance/qr/<token>")  # opened if a phone's native camera scans the QR
@login_required("STUDENT")
def qr_link(token):
    ok, msg = use_token(token); flash(msg, "success" if ok else "danger")
    return redirect(url_for("student_dashboard"))

@app.route("/api/mark-qr-attendance", methods=["POST"])
@login_required("STUDENT")
def mark_qr():
    tok = (request.get_json(silent=True) or {}).get("token", "").strip().split("/")[-1]
    ok, msg = use_token(tok)
    return jsonify(ok=ok, message=msg, student=me().username, date=str(date.today()),
                   time=datetime.now().strftime("%H:%M:%S"), method="QR"), (200 if ok else 400)

@app.route("/api/mark-face-attendance", methods=["POST"])
@login_required("STUDENT")
def mark_face():
    img = (request.get_json(silent=True) or {}).get("image", "")
    try:
        raw = base64.b64decode(img.split(",")[-1])
        frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    except Exception:
        return jsonify(ok=False, message="Invalid image"), 400
    if len(FACE.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))) == 0:
        return jsonify(ok=False, message="No face detected. Please position your face clearly in front of the camera."), 400
    if Attendance.query.filter_by(user_id=session["uid"], date=date.today()).first():
        return jsonify(ok=False, message="Duplicate attendance: already marked today"), 400
    fn = f"{me().username}_{uuid.uuid4().hex[:10]}.jpg"
    cv2.imwrite(os.path.join(Config.FACE_DIR, fn), frame)
    ok, msg = mark(me(), "FACE", face=fn)
    return jsonify(ok=ok, message="Face Captured Successfully - Attendance Marked" if ok else msg,
                   date=str(date.today()), time=datetime.now().strftime("%H:%M:%S"), method="FACE"), (200 if ok else 400)

# ---------- rooms ----------
@app.route("/admin/rooms", methods=["GET", "POST"])
@login_required("ADMIN")
def admin_rooms():
    if request.method == "POST":
        f = request.form; n = f.get("number", "").strip()
        if not n: flash("Room number required", "danger")
        elif Room.query.filter_by(number=n).first(): flash("Room already exists", "danger")
        else:
            db.session.add(Room(number=n, block=f.get("block"), floor=int(f.get("floor") or 0), capacity=int(f.get("capacity") or 4)))
            db.session.commit(); flash("Room added", "success")
        return redirect(url_for("admin_rooms"))
    rooms = [(r, User.query.filter_by(room=r.number, role="STUDENT").count()) for r in Room.query.order_by(Room.number).all()]
    return render_template("admin/rooms.html", rooms=rooms)

@app.route("/admin/rooms/delete/<int:id>", methods=["POST"])
@login_required("ADMIN")
def delete_room(id):
    r = db.session.get(Room, id)
    if r: db.session.delete(r); db.session.commit(); flash("Room deleted", "success")
    return redirect(url_for("admin_rooms"))

# ---------- edit student ----------
@app.route("/admin/students/edit/<int:id>", methods=["GET", "POST"])
@login_required("ADMIN")
def edit_student(id):
    s = db.session.get(User, id)
    if not s or s.role != "STUDENT": return render_template("404.html"), 404
    if request.method == "POST":
        for k in ("name", "block", "room", "email", "phone", "department", "parent_name", "parent_phone"):
            setattr(s, k, request.form.get(k, "").strip())
        if request.form.get("password"):
            if len(request.form["password"]) < 6: flash("Password min 6 chars", "danger"); return redirect(request.url)
            s.password_hash = generate_password_hash(request.form["password"])
        db.session.commit(); flash("Student updated", "success"); return redirect(url_for("admin_students"))
    return render_template("admin/edit_student.html", s=s)

# ---------- leave ----------
@app.route("/student/leave", methods=["GET", "POST"])
@login_required("STUDENT")
def student_leave():
    if request.method == "POST":
        f = request.form
        try: a, b = date.fromisoformat(f["from_date"]), date.fromisoformat(f["to_date"])
        except Exception: a = b = None
        if not a or b < a or not f.get("reason", "").strip() or f.get("leave_type") not in ("Home Visit", "Medical", "Emergency", "Other"):
            flash("Invalid leave request", "danger")
        else:
            db.session.add(Leave(user_id=session["uid"], leave_type=f["leave_type"], from_date=a, to_date=b, reason=f["reason"][:300]))
            db.session.commit(); flash("Leave request submitted", "success")
        return redirect(url_for("student_leave"))
    return render_template("student/leave.html", leaves=Leave.query.filter_by(user_id=session["uid"]).order_by(Leave.id.desc()).all())

@app.route("/admin/leave-requests", methods=["GET", "POST"])
@login_required("ADMIN")
def admin_leaves():
    if request.method == "POST":
        l = db.session.get(Leave, int(request.form["id"]))
        if l and request.form.get("action") in ("Approved", "Rejected"):
            l.status = request.form["action"]; l.remark = request.form.get("remark", "")[:200]; db.session.commit()
            flash("Leave " + l.status.lower(), "success")
        return redirect(url_for("admin_leaves"))
    return render_template("admin/leave_requests.html", leaves=Leave.query.order_by(Leave.id.desc()).all())

# ---------- profile / settings ----------
def change_pw(u):
    f = request.form
    if not check_password_hash(u.password_hash, f.get("old", "")): flash("Current password incorrect", "danger")
    elif len(f.get("new", "")) < 6: flash("New password min 6 chars", "danger")
    else: u.password_hash = generate_password_hash(f["new"]); db.session.commit(); flash("Password changed", "success")

@app.route("/student/profile", methods=["GET", "POST"])
@login_required("STUDENT")
def student_profile():
    u = me()
    if request.method == "POST":
        if request.form.get("old"): change_pw(u)
        else:
            u.email, u.phone = request.form.get("email", "").strip(), request.form.get("phone", "").strip()
            db.session.commit(); flash("Profile updated", "success")
        return redirect(url_for("student_profile"))
    return render_template("student/profile.html", u=u)

@app.route("/admin/settings", methods=["GET", "POST"])
@login_required("ADMIN")
def admin_settings():
    if request.method == "POST": change_pw(me()); return redirect(url_for("admin_settings"))
    return render_template("admin/settings.html", ttl=Config.QR_TTL)

def seed_rooms():
    if not Room.query.first():
        for n, b in [("101", "A"), ("102", "A"), ("103", "B"), ("201", "B")]:
            db.session.add(Room(number=n, block=b, floor=int(n[0]), capacity=4))
        db.session.commit()

@app.errorhandler(404)
def e404(e): return render_template("404.html"), 404
@app.errorhandler(500)
def e500(e): return render_template("500.html"), 500

with app.app_context(): seed(); seed_rooms()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("DEBUG") == "1")
