import os
import logging
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_key_only_for_development")
    if not app.secret_key:
        logger.error("No Flask secret key set!")
        
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
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
    db.init_app(app)
    login_manager.init_app(app)
    
    # Initialize Flask-Mail with app context
    mail = Mail(app)
    app.mail = mail  # Make mail accessible via current_app
    
    # User loader function
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        logger.error(f"Page not found: {error}")
        return render_template('error.html', error=error), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Server error: {error}")
        db.session.rollback()
        return render_template('error.html', error=error), 500
        
    with app.app_context():
        try:
            import models
            db.create_all()
            logger.info("Database tables created successfully")
            
            # Register blueprints
            from routes import main
            from google_auth import google_auth
            app.register_blueprint(main)
            app.register_blueprint(google_auth)
            logger.info("Blueprints registered successfully")
            
        except Exception as e:
            logger.error(f"Error during app initialization: {str(e)}")
            raise
        
    return app
