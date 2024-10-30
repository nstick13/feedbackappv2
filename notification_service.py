import logging
from typing import List
from flask import current_app
from flask_mail import Message
from datetime import datetime

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - [%(request_id)s] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def send_email(subject: str, recipients: List[str], html_content: str, request_id: str) -> bool:
    """Send email using Flask-Mail with detailed logging"""
    try:
        logger.info(f"Preparing to send email: {subject} to {recipients}", 
                   extra={"request_id": request_id})
        
        # Log email configuration
        logger.debug(
            f"Email Configuration:\n"
            f"- MAIL_SERVER: {current_app.config['MAIL_SERVER']}\n"
            f"- MAIL_PORT: {current_app.config['MAIL_PORT']}\n"
            f"- MAIL_USE_TLS: {current_app.config['MAIL_USE_TLS']}\n"
            f"- MAIL_USERNAME: {current_app.config['MAIL_USERNAME']}",
            extra={"request_id": request_id}
        )

        # Create email message
        msg = Message(
            subject=subject,
            sender=current_app.config['MAIL_USERNAME'],
            recipients=recipients
        )

        # Add HTML content with proper formatting
        msg.html = f"""
        <!DOCTYPE html>
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                {html_content}
            </body>
        </html>
        """

        logger.debug(f"Email content preview (first 200 chars): {msg.html[:200]}...", 
                    extra={"request_id": request_id})

        # Send email using Flask-Mail
        current_app.mail.send(msg)
        
        logger.info(f"Email sent successfully at {datetime.utcnow()}", 
                   extra={"request_id": request_id})
        return True

    except Exception as e:
        logger.error(
            f"Failed to send email: {str(e)}\n"
            f"Subject: {subject}\n"
            f"Recipients: {recipients}",
            extra={"request_id": request_id},
            exc_info=True
        )
        return False

def send_feedback_invitation(recipient_email: str, requestor_name: str, topic: str, feedback_url: str, request_id: str):
    """Send feedback invitation email"""
    try:
        logger.info(f"Preparing feedback invitation email for {recipient_email}", 
                   extra={"request_id": request_id})
        
        html_content = f"""
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #333;">Feedback Request</h2>
            <p>Hello,</p>
            <p>{requestor_name} has requested your feedback regarding: <strong>{topic}</strong></p>
            <p>Please click the button below to provide your feedback:</p>
            <p style="text-align: center;">
                <a href="{feedback_url}" 
                   style="display: inline-block; padding: 10px 20px; 
                          background-color: #007bff; color: white; 
                          text-decoration: none; border-radius: 5px;">
                    Provide Feedback
                </a>
            </p>
            <p>Thank you for your time!</p>
        </div>
        """
        
        logger.debug(f"Generated feedback URL: {feedback_url}", extra={"request_id": request_id})
        
        return send_email(
            subject=f"Feedback Request from {requestor_name}",
            recipients=[recipient_email],
            html_content=html_content,
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(f"Error preparing feedback invitation email: {str(e)}", 
                    extra={"request_id": request_id},
                    exc_info=True)
        raise

def send_feedback_submitted_notification(recipient_email: str, provider_name: str, topic: str, feedback_url: str, request_id: str):
    """Send feedback submission notification email"""
    try:
        logger.info(f"Preparing feedback submission notification for {recipient_email}", 
                   extra={"request_id": request_id})
        
        html_content = f"""
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #333;">New Feedback Received</h2>
            <p>Hello,</p>
            <p>{provider_name} has submitted feedback for your request: <strong>{topic}</strong></p>
            <p>Click the button below to view the feedback:</p>
            <p style="text-align: center;">
                <a href="{feedback_url}" 
                   style="display: inline-block; padding: 10px 20px; 
                          background-color: #007bff; color: white; 
                          text-decoration: none; border-radius: 5px;">
                    View Feedback
                </a>
            </p>
        </div>
        """
        
        logger.debug(f"Generated feedback URL: {feedback_url}", extra={"request_id": request_id})
        
        return send_email(
            subject=f"New Feedback Received from {provider_name}",
            recipients=[recipient_email],
            html_content=html_content,
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(f"Error preparing feedback submission notification: {str(e)}", 
                    extra={"request_id": request_id},
                    exc_info=True)
        raise

def send_analysis_completed_notification(recipient_email: str, topic: str, feedback_url: str, request_id: str):
    """Send analysis completion notification email"""
    try:
        logger.info(f"Preparing analysis completion notification for {recipient_email}", 
                   extra={"request_id": request_id})
        
        html_content = f"""
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #333;">Feedback Analysis Complete</h2>
            <p>Hello,</p>
            <p>The AI analysis of your feedback request for "<strong>{topic}</strong>" is now complete.</p>
            <p>Click the button below to view the analysis:</p>
            <p style="text-align: center;">
                <a href="{feedback_url}" 
                   style="display: inline-block; padding: 10px 20px; 
                          background-color: #007bff; color: white; 
                          text-decoration: none; border-radius: 5px;">
                    View Analysis
                </a>
            </p>
        </div>
        """
        
        logger.debug(f"Generated feedback URL: {feedback_url}", extra={"request_id": request_id})
        
        return send_email(
            subject=f"Feedback Analysis Complete - {topic}",
            recipients=[recipient_email],
            html_content=html_content,
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(f"Error preparing analysis completion notification: {str(e)}", 
                    extra={"request_id": request_id},
                    exc_info=True)
        raise
