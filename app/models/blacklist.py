from datetime import datetime
from app import db


class BlacklistEntry(db.Model):
    """Represents a single email entry in the global blacklist."""

    __tablename__ = "blacklist_entries"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    app_uuid = db.Column(db.String(36), nullable=False)
    blocked_reason = db.Column(db.String(255), nullable=True)
    request_ip = db.Column(db.String(45), nullable=False)          # IPv4 or IPv6
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<BlacklistEntry email={self.email} app_uuid={self.app_uuid}>"
