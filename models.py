from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)  # Student ID or 'admin'
    name = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(10), nullable=False)                   # ADMIN / STUDENT
    password_hash = db.Column(db.String(200), nullable=False)
    block = db.Column(db.String(20))
    room = db.Column(db.String(10))
    email = db.Column(db.String(80)); phone = db.Column(db.String(15)); department = db.Column(db.String(50))
    parent_name = db.Column(db.String(80)); parent_phone = db.Column(db.String(15))

class Attendance(db.Model):
    __table_args__ = (db.UniqueConstraint("user_id", "date"),)       # no duplicates per day
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(8))
    method = db.Column(db.String(10))                                 # QR / FACE / MANUAL
    status = db.Column(db.String(10), default="PRESENT")
    face_image = db.Column(db.String(100))
    qr_token = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User")

class QRToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True)
    expires_at = db.Column(db.DateTime)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(10), unique=True, nullable=False)
    block = db.Column(db.String(20)); floor = db.Column(db.Integer, default=0)
    capacity = db.Column(db.Integer, default=4)

class Leave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    leave_type = db.Column(db.String(20)); from_date = db.Column(db.Date); to_date = db.Column(db.Date)
    reason = db.Column(db.String(300)); status = db.Column(db.String(10), default="Pending"); remark = db.Column(db.String(200))
    user = db.relationship("User")
