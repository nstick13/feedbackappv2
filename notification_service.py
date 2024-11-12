import logging
from typing import List, Dict
from flask import current_app, Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import uuid

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - [%(request_id)s] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@main.route('/initiate_conversation', methods=['POST'])
@login_required
def initiate_conversation():
    request_id = str(uuid.uuid4())
    try:
        logger.debug(f"Initiating conversation for user {current_user.id_string}", extra={"request_id": request_id})
        # Your existing code for initiating conversation
    except Exception as e:
        logger.error(f"Failed to initiate conversation: {str(e)}", extra={"request_id": request_id})
        return jsonify({"error": "Failed to initiate conversation"}), 500

@main.route('/request_feedback', methods=['POST'])
@login_required
def request_feedback():
    request_id = str(uuid.uuid4())
    try:
        logger.debug(f"Requesting feedback for user {current_user.id_string}", extra={"request_id": request_id})
        
        data = request.get_json()
        topic = data.get('topic')
        recipient_email = data.get('recipient_email')
        
        if not topic or not recipient_email:
            logger.error("Topic and recipient email are required", extra={"request_id": request_id})
            return jsonify({"error": "Topic and recipient email are required"}), 400
        
        # Create a new feedback request
        feedback_request = FeedbackRequest(
            topic=topic,
            requestor_id=current_user.id_string
        )
        db.session.add(feedback_request)
        db.session.commit()

        # Generate feedback URL
        feedback_url = url_for('main.feedback_session', request_id=request_id, _external=True)

        # Send feedback request email
        send_feedback_request_email(
            recipient_email=recipient_email,
            requestor_name=current_user.username,
            feedback_url=feedback_url,
            request_id=request_id
        )

        return jsonify({"message": "Feedback request sent successfully"}), 200
    except Exception as e:
        logger.error(f"Failed to request feedback: {str(e)}", extra={"request_id": request_id})
        return jsonify({"error": "Failed to request feedback"}), 500

def send_email_with_template(template_id: str, recipients: List[str], dynamic_data: Dict[str, str], request_id: str) -> bool:
    """Send email using SendGrid template with detailed logging"""
    try:
        logger.info(f"Preparing to send email to {recipients}", extra={"request_id": request_id})
        
        # Log email configuration
        logger.debug(
            f"Email Configuration:\n"
            f"- SENDGRID_API_KEY: {current_app.config['SENDGRID_API_KEY'][:5]}... (hidden)\n"
            f"- SENDGRID_FROM_EMAIL: {current_app.config['SENDGRID_FROM_EMAIL']}",
            extra={"request_id": request_id}
        )

        # Create email message with dynamic template data
        message = Mail(
            from_email=current_app.config['SENDGRID_FROM_EMAIL'],
            to_emails=recipients,
        )
        message.dynamic_template_data = dynamic_data
        message.template_id = template_id

        # Send email using SendGrid
        sg = SendGridAPIClient(api_key=current_app.config['SENDGRID_API_KEY'])
        response = sg.send(message)

        # Log SendGrid response
        logger.info(f"Email sent: {response.status_code}", extra={"request_id": request_id})
        logger.debug(f"SendGrid response body: {response.body}", extra={"request_id": request_id})
        logger.debug(f"SendGrid response headers: {response.headers}", extra={"request_id": request_id})
        
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}", extra={"request_id": request_id})
        return False

def send_feedback_request_email(recipient_email: str, requestor_name: str, feedback_url: str, request_id: str):
    """Send feedback request email using SendGrid template"""
    template_id = current_app.config['SENDGRID_FEEDBACK_REQUEST_TEMPLATE']
    dynamic_data = {
        "requestor_name": requestor_name,
        "feedback_link": feedback_url
    }
    return send_email_with_template(template_id, [recipient_email], dynamic_data, request_id)

def send_feedback_reminder_email(recipient_email: str, requestor_name: str, feedback_url: str, request_id: str):
    """Send feedback reminder email using SendGrid template"""
    template_id = current_app.config['SENDGRID_FEEDBACK_REMINDER_TEMPLATE']
    dynamic_data = {
        "requestor_name": requestor_name,
        "feedback_link": feedback_url
    }
    return send_email_with_template(template_id, [recipient_email], dynamic_data, request_id)

def send_feedback_provided_email(recipient_email: str, provider_name: str, feedback_url: str, request_id: str):
    """Send feedback provided email using SendGrid template"""
    template_id = current_app.config['SENDGRID_FEEDBACK_PROVIDED_TEMPLATE']
    dynamic_data = {
        "provider_name": provider_name,
        "feedback_link": feedback_url
    }
    return send_email_with_template(template_id, [recipient_email], dynamic_data, request_id)

def send_verify_email(recipient_email: str, verification_link: str, request_id: str):
    """Send verify email address email using SendGrid template"""
    template_id = current_app.config['SENDGRID_VERIFY_EMAIL_TEMPLATE']
    dynamic_data = {
        "verification_link": verification_link
    }
    return send_email_with_template(template_id, [recipient_email], dynamic_data, request_id)

def send_password_reset_email(recipient_email: str, reset_link: str, request_id: str):
    """Send password reset email using SendGrid template"""
    template_id = current_app.config['SENDGRID_PASSWORD_RESET_TEMPLATE']
    dynamic_data = {
        "reset_link": reset_link
    }
    return send_email_with_template(template_id, [recipient_email], dynamic_data, request_id)