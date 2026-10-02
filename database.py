from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Custom save location for transcripts, PDFs, notes
    local_save_path = db.Column(db.String(500), nullable=False)
    
    # Integrations
    telegram_bot_token = db.Column(db.String(255), nullable=True)
    telegram_chat_id = db.Column(db.String(255), nullable=True)
    notion_token = db.Column(db.String(255), nullable=True)
    notion_database_id = db.Column(db.String(255), nullable=True)
    notion_page_url = db.Column(db.String(500), nullable=True)
    
    # Chrome CDP Port for automated logins
    cdp_port = db.Column(db.String(10), default="9222")

    # Scraped Curriculum Courses (Stored as JSON string)
    courses_json = db.Column(db.Text, nullable=True)
    
    # Onboarding Status
    onboarding_completed = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "local_save_path": self.local_save_path,
            "telegram_bot_token": self.telegram_bot_token,
            "telegram_chat_id": self.telegram_chat_id,
            "notion_token": self.notion_token,
            "notion_database_id": self.notion_database_id,
            "notion_page_url": self.notion_page_url,
            "cdp_port": self.cdp_port,
            "courses_json": self.courses_json,
            "onboarding_completed": self.onboarding_completed
        }
