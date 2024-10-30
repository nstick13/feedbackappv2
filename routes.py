import logging
import uuid
from datetime import datetime
from flask import Blueprint, render_template, jsonify, request, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import db, FeedbackRequest, FeedbackProvider, FeedbackSession, User
from chat_service import generate_feedback_prompts, analyze_feedback
from notification_service import (
    send_email,
    send_feedback_invitation,
    send_feedback_submitted_notification,
    send_analysis_completed_notification
)

logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)

@main.route('/')
def index():
    try:
        logger.debug("Rendering index page", extra={"request_id": "INDEX"})
        if current_user.is_authenticated:
            return redirect(url_for('main.dashboard'))
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index page: {str(e)}", extra={"request_id": "INDEX"})
        return render_template('error.html', error=str(e)), 500

@main.route('/dashboard')
@login_required
def dashboard():
    request_id = str(uuid.uuid4())
    try:
        logger.debug(f"Fetching dashboard data for user {current_user.id}", extra={"request_id": request_id})
        my_requests = FeedbackRequest.query.filter_by(requestor_id=current_user.id).all()
        pending_feedback = FeedbackProvider.query.filter_by(
            provider_id=current_user.id,
            status='invited'
        ).all()
        return render_template('dashboard.html', requests=my_requests, pending=pending_feedback)
    except Exception as e:
        logger.error(f"Error rendering dashboard: {str(e)}", extra={"request_id": request_id})
        return render_template('error.html', error=str(e)), 500

@main.route('/feedback/request', methods=['POST'])
@login_required
def create_feedback_request():
    request_id = str(uuid.uuid4())
    try:
        data = request.get_json()
        topic = data.get('topic')
        provider_emails = data.get('providers', [])
        
        if not topic:
            raise ValueError("Topic is required")
        
        logger.debug(f"Creating feedback request for topic: {topic}", extra={"request_id": request_id})
        logger.debug(
            f"SMTP Configuration Details:\n"
            f"Server: {current_app.config['MAIL_SERVER']}\n"
            f"Port: {current_app.config['MAIL_PORT']}\n"
            f"TLS: {current_app.config['MAIL_USE_TLS']}\n"
            f"Username: {current_app.config['MAIL_USERNAME']}", 
            extra={"request_id": request_id}
        )
        
        # Generate AI prompts
        prompts = generate_feedback_prompts(topic)
        
        # Create feedback request
        feedback_request = FeedbackRequest(
            topic=topic,
            requestor_id=current_user.id,
            ai_context=prompts
        )
        db.session.add(feedback_request)
        db.session.flush()
        
        # Add providers and send email invitations
        email_errors = []
        for email in provider_emails:
            logger.debug(f"Processing provider email: {email}", extra={"request_id": request_id})
            
            try:
                # Create provider entry with email
                invitation_sent_time = datetime.utcnow()
                provider = FeedbackProvider(
                    feedback_request_id=feedback_request.id,
                    provider_email=email,
                    invitation_sent=invitation_sent_time
                )
                db.session.add(provider)
                logger.debug(f"Created provider entry for {email} at {invitation_sent_time}", 
                           extra={"request_id": request_id})
                
                # Generate feedback URL
                feedback_url = url_for(
                    'main.feedback_session',
                    request_id=feedback_request.id,
                    _external=True
                )
                logger.debug(f"Generated feedback URL for {email}: {feedback_url}", 
                            extra={"request_id": request_id})
                
                # Prepare email invitation
                logger.info(f"Preparing to send feedback invitation to {email}", extra={"request_id": request_id})
                logger.debug(
                    f"Email Context Details:\n"
                    f"From: {current_app.config['MAIL_USERNAME']}\n"
                    f"To: {email}\n"
                    f"Subject: Feedback Request from {current_user.username}\n"
                    f"Topic: {topic}\n"
                    f"Feedback URL: {feedback_url}\n"
                    f"Request ID: {request_id}",
                    extra={"request_id": request_id}
                )
                
                # Monitor SMTP connection
                logger.debug("Initiating SMTP connection for sending invitation", extra={"request_id": request_id})
                
                try:
                    send_feedback_invitation(
                        email,
                        current_user.username,
                        topic,
                        feedback_url,
                        request_id
                    )
                    logger.info(
                        f"Successfully sent invitation email to {email}\n"
                        f"Time: {datetime.utcnow()}\n"
                        f"SMTP Status: Success", 
                        extra={"request_id": request_id}
                    )
                except Exception as email_error:
                    logger.error(
                        f"Failed to send invitation email to {email}\n"
                        f"Error Type: {type(email_error).__name__}\n"
                        f"Error Message: {str(email_error)}\n"
                        f"Stack Trace: {email_error.__traceback__}",
                        extra={"request_id": request_id},
                        exc_info=True
                    )
                    email_errors.append(email)
            except Exception as e:
                logger.error(
                    f"Error preparing email for {email}\n"
                    f"Error Type: {type(e).__name__}\n"
                    f"Error Message: {str(e)}\n"
                    f"Stack Trace: {e.__traceback__}",
                    extra={"request_id": request_id},
                    exc_info=True
                )
                email_errors.append(email)
        
        db.session.commit()
        logger.info(f"Successfully created feedback request {feedback_request.id}", 
                   extra={"request_id": request_id})
        
        if email_errors:
            return jsonify({
                "status": "partial_success",
                "request_id": feedback_request.id,
                "message": f"Request created but failed to send emails to: {', '.join(email_errors)}"
            })
            
        return jsonify({"status": "success", "request_id": feedback_request.id})
        
    except Exception as e:
        logger.error(f"Error creating feedback request: {str(e)}", 
                    extra={"request_id": request_id},
                    exc_info=True)
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@main.route('/feedback/session/<int:request_id>')
@login_required
def feedback_session(request_id):
    session_id = str(uuid.uuid4())
    try:
        logger.debug(f"Accessing feedback session {request_id}", extra={"request_id": session_id})
        feedback_request = FeedbackRequest.query.get_or_404(request_id)
        
        # Check if user is the requestor
        if feedback_request.requestor_id == current_user.id:
            return render_template(
                'feedback_session.html',
                feedback_request=feedback_request,
                is_provider=False
            )
        
        # Check if user is a provider by email
        provider = FeedbackProvider.query.filter_by(
            feedback_request_id=request_id,
            provider_email=current_user.email
        ).first()
        
        if not provider:
            logger.warning(f"Unauthorized access attempt to feedback session {request_id} by user {current_user.id}", 
                         extra={"request_id": session_id})
            return render_template('error.html', error="Unauthorized access"), 403
            
        return render_template(
            'feedback_session.html',
            feedback_request=feedback_request,
            is_provider=True
        )
    except Exception as e:
        logger.error(f"Error accessing feedback session: {str(e)}", 
                    extra={"request_id": session_id},
                    exc_info=True)
        return render_template('error.html', error=str(e)), 500

@main.route('/test/email')
@login_required
def test_email():
    """Test route to verify email functionality"""
    try:
        test_id = str(uuid.uuid4())
        logger.info("Testing email functionality", extra={"request_id": test_id})
        
        result = send_email(
            subject="Test Email",
            recipients=[current_user.email],
            html_content="""
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2>Email System Test</h2>
                <p>This is a test email to verify the email notification system.</p>
                <p>If you received this email, the system is working correctly.</p>
                <p>Time sent: {}</p>
            </div>
            """.format(datetime.utcnow()),
            request_id=test_id
        )
        
        if result:
            logger.info("Test email sent successfully", extra={"request_id": test_id})
            return jsonify({"status": "success", "message": "Test email sent successfully"})
        else:
            logger.error("Failed to send test email", extra={"request_id": test_id})
            return jsonify({"status": "error", "message": "Failed to send test email"}), 500
            
    except Exception as e:
        logger.error(f"Error in test email route: {str(e)}", extra={"request_id": test_id}, exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
