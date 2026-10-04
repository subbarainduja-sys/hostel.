import os
from dotenv import load_dotenv
load_dotenv()
B = os.path.abspath(os.path.dirname(__file__))
class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///" + os.path.join(B, "database", "hostel.db"))
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024   # max image upload 5 MB
    FACE_DIR = os.path.join(B, "uploads", "faces")
    QR_TTL = 60                            # QR token lifetime (seconds)
    SESSION_COOKIE_HTTPONLY = True
