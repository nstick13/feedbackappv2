from datetime import datetime
from app import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class FeedbackRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(200), nullable=False)
    requestor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ai_context = db.Column(db.JSON, default={})
    
class FeedbackProvider(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    feedback_request_id = db.Column(db.Integer, db.ForeignKey('feedback_request.id'))
    provider_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    provider_email = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), default='invited')
    invitation_sent = db.Column(db.DateTime)
    access_token = db.Column(db.String(100), unique=True)
    token_expiry = db.Column(db.DateTime)

class FeedbackSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    feedback_request_id = db.Column(db.Integer, db.ForeignKey('feedback_request.id'))
    provider_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

