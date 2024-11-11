import os
import logging
from flask import Flask, render_template, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

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

# Get the database URL from Heroku's environment variable
database_url = os.getenv("DATABASE_URL")

# Replace 'postgres://' with 'postgresql://'
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Set the modified URL to your Flask configuration
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

# Initialize extensions
db = SQLAlchemy(model_class=Base)
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
mail = Mail(app)
app.mail = mail  # Make mail accessible via current_app

# Register blueprints
from routes import main as main_blueprint
app.register_blueprint(main_blueprint)

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
