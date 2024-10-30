import secrets
import logging
from datetime import datetime, timedelta
from models import FeedbackProvider, db
from flask import current_app

logger = logging.getLogger(__name__)

def generate_feedback_token():
    """Generate a secure random token for feedback providers"""
    return secrets.token_urlsafe(32)

def create_feedback_token(provider_id):
    """Create and store a new access token for a feedback provider"""
    try:
        provider = FeedbackProvider.query.get(provider_id)
        if not provider:
            logger.error(f"Provider {provider_id} not found")
            return None

        token = generate_feedback_token()
        provider.access_token = token
        provider.token_expiry = datetime.utcnow() + timedelta(days=7)  # Token valid for 7 days
        
        db.session.commit()
        logger.info(f"Created access token for provider {provider_id}")
        return token
    
    except Exception as e:
        logger.error(f"Error creating feedback token: {str(e)}")
        db.session.rollback()
        return None

def verify_feedback_token(token):
    """Verify a feedback provider's access token"""
    try:
        if not token:
            return None
            
        provider = FeedbackProvider.query.filter_by(access_token=token).first()
        if not provider:
            logger.warning(f"Invalid token used: {token[:10]}...")
            return None
            
        if provider.token_expiry and provider.token_expiry < datetime.utcnow():
            logger.warning(f"Expired token used for provider {provider.id}")
            return None
            
        return provider
        
    except Exception as e:
        logger.error(f"Error verifying feedback token: {str(e)}")
        return None
