import os
import logging
from flask import Flask, render_template, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from extensions import db  # Import db from extensions.py
from flask_migrate import Migrate

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

app = Flask(__name__)  # Create the Flask application instance

# Configuration
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_key_only_for_development")
if not app.secret_key:
    logger.error("No Flask secret key set!")

# Determine the database URL
database_url = os.getenv("DATABASE_URL", "postgresql://localhost/natetgreat")

# Replace 'postgres://' with 'postgresql://'
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Initialize the database with the app
db.init_app(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

# SendGrid configuration
app.config['SENDGRID_API_KEY'] = os.environ.get('SENDGRID_API_KEY')
app.config['SENDGRID_FROM_EMAIL'] = os.environ.get('SENDGRID_FROM_EMAIL')

# OpenAI configuration
openai_api_key = os.environ.get("OPEN_AI_KEY")
if not openai_api_key:
    logger.error("No OpenAI API key set!")
else:
    logger.info(f"OpenAI API key is set: {openai_api_key[:5]}...")

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
mail = Mail(app)
app.mail = mail  # Make mail accessible via current_app

# Import the User model
from models import User  # Ensure you import your User model

# Define the user loader function
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# Register blueprints
from routes import main as main_blueprint
app.register_blueprint(main_blueprint)

from google_auth import google_auth_bp  # Import the google_auth blueprint
app.register_blueprint(google_auth_bp, url_prefix='/google_login')

def migrate_database():
    with current_app.app_context():
        # Check if columns exist
        inspector = db.inspect(db.engine)
        columns = {col['name'] for col in inspector.get_columns('feedback_provider')}
        
        if 'access_token' not in columns or 'token_expiry' not in columns:
            logger.info("Adding missing columns to feedback_provider table")
            # Add missing columns
            with db.engine.connect() as conn:
                if 'access_token' not in columns:
                    conn.execute(text('ALTER TABLE feedback_provider ADD COLUMN access_token VARCHAR(100)'))
                if 'token_expiry' not in columns:
                    conn.execute(text('ALTER TABLE feedback_provider ADD COLUMN token_expiry TIMESTAMP'))
                conn.commit()
            logger.info("Successfully added missing columns")

if __name__ == '__main__':
    app.run(debug=True)
