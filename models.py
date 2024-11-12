from datetime import datetime
from extensions import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id_string = db.Column(db.String(100), primary_key=True)
    name = db.Column(db.String(100))
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_id(self):
        return self.id_string

class FeedbackRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(36), unique=True, nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    requestor_id = db.Column(db.String(100), db.ForeignKey('user.id_string'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ai_context = db.Column(db.JSON, default={})

class FeedbackProvider(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Add other fields as necessary

class FeedbackSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    feedback_request_id = db.Column(db.Integer, db.ForeignKey('feedback_request.id'))
    provider_id = db.Column(db.String(100), db.ForeignKey('user.id_string'))
    content = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

