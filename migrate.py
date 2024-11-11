from app import app
from extensions import db
from models import User, FeedbackRequest, FeedbackProvider, FeedbackSession

with app.app_context():
    db.create_all()