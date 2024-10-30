import logging
import os
import time
import socket
from typing import List, Optional
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from flask import current_app
from queue import Queue
import threading
from datetime import datetime

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - [%(request_id)s] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class EmailMessage:
    subject: str
    recipients: List[str]
    html_content: str
    retry_count: int = 0
    request_id: str = None

class EmailNotificationService:
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    SMTP_TIMEOUT = 30  # seconds
    
    def __init__(self):
        self.email_queue: Queue[EmailMessage] = Queue()
        self.worker_thread = threading.Thread(target=self._process_email_queue, daemon=True)
        self.worker_thread.start()
        logger.info("Email notification service initialized", extra={"request_id": "INIT"})
        
        # Test SMTP connection on startup
        self._test_smtp_connection()

    def _test_smtp_connection(self) -> bool:
        """Test SMTP connection and configuration on startup"""
        try:
            logger.info("Testing SMTP connection...", extra={"request_id": "INIT"})
            with self._create_smtp_connection() as server:
                logger.info("SMTP connection test successful", extra={"request_id": "INIT"})
                return True
        except Exception as e:
            logger.error(f"SMTP connection test failed: {str(e)}", extra={"request_id": "INIT"})
            return False

    def _create_smtp_connection(self) -> smtplib.SMTP:
        """Create and configure SMTP connection with proper error handling"""
        try:
            # Create SMTP connection with timeout
            logger.debug("Initiating SMTP connection...", extra={"request_id": "CONN"})
            server = smtplib.SMTP(
                current_app.config['MAIL_SERVER'],
                current_app.config['MAIL_PORT'],
                timeout=self.SMTP_TIMEOUT
            )
            server.set_debuglevel(1)
            logger.debug(f"Connected to SMTP server: {current_app.config['MAIL_SERVER']}:{current_app.config['MAIL_PORT']}", 
                        extra={"request_id": "CONN"})

            # Configure TLS
            if current_app.config['MAIL_USE_TLS']:
                logger.debug("Initiating TLS connection", extra={"request_id": "CONN"})
                server.starttls()
                logger.debug("TLS connection established successfully", extra={"request_id": "CONN"})

            # Authenticate
            username = current_app.config['MAIL_USERNAME']
            password = current_app.config['MAIL_PASSWORD']
            
            if not username or not password:
                raise ValueError("SMTP credentials not configured")
            
            logger.debug(f"Attempting authentication for user: {username}", extra={"request_id": "CONN"})
            server.login(username, password)
            logger.debug("SMTP authentication successful", extra={"request_id": "CONN"})

            return server
            
        except socket.timeout as e:
            logger.error(f"SMTP connection timeout: {str(e)}", extra={"request_id": "CONN"})
            raise
        except smtplib.SMTPException as e:
            logger.error(f"SMTP connection error: {str(e)}", extra={"request_id": "CONN"})
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating SMTP connection: {str(e)}", extra={"request_id": "CONN"})
            raise

    def send_email(self, message: EmailMessage) -> bool:
        """Send email with proper error handling and logging"""
        try:
            logger.info(f"Preparing to send email: {message.subject} to {message.recipients}", 
                       extra={"request_id": message.request_id})
            
            logger.debug("Creating email message", extra={"request_id": message.request_id})
            with self._create_smtp_connection() as server:
                # Create message
                msg = MIMEMultipart('alternative')
                msg['Subject'] = message.subject
                msg['From'] = current_app.config['MAIL_USERNAME']
                msg['To'] = ', '.join(message.recipients)
                
                # Add HTML content with proper formatting
                html_part = MIMEText(
                    f"""
                    <!DOCTYPE html>
                    <html>
                        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                            {message.html_content}
                        </body>
                    </html>
                    """,
                    'html'
                )
                msg.attach(html_part)
                logger.debug("Email message prepared successfully", extra={"request_id": message.request_id})

                # Send email
                logger.debug("Attempting to send email", extra={"request_id": message.request_id})
                server.send_message(msg)
                logger.info(f"Email sent successfully: {message.subject} to {message.recipients}", 
                          extra={"request_id": message.request_id})
                return True

        except (smtplib.SMTPAuthenticationError, ValueError) as e:
            logger.error(f"Authentication error: {str(e)}", extra={"request_id": message.request_id})
            raise
        except socket.timeout as e:
            logger.error(f"Connection timeout: {str(e)}", extra={"request_id": message.request_id})
            return False
        except smtplib.SMTPServerDisconnected as e:
            logger.error(f"Server disconnected: {str(e)}", extra={"request_id": message.request_id})
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {str(e)}", extra={"request_id": message.request_id})
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", extra={"request_id": message.request_id})
            return False
        finally:
            logger.debug("Email sending operation completed", extra={"request_id": message.request_id})

    def queue_email(self, message: EmailMessage):
        """Add email to the queue for processing"""
        try:
            logger.info(f"Queueing email: {message.subject} for {message.recipients}", 
                       extra={"request_id": message.request_id})
            self.email_queue.put(message)
        except Exception as e:
            logger.error(f"Error queueing email: {str(e)}", extra={"request_id": message.request_id})

    def _process_email_queue(self):
        """Process emails in the queue with retry logic"""
        while True:
            try:
                if not self.email_queue.empty():
                    message = self.email_queue.get()
                    retry_count = 0
                    
                    while retry_count < self.MAX_RETRIES:
                        try:
                            logger.debug(f"Processing queued email (attempt {retry_count + 1}/{self.MAX_RETRIES})", 
                                       extra={"request_id": message.request_id})
                            if self.send_email(message):
                                break
                            
                            retry_count += 1
                            if retry_count < self.MAX_RETRIES:
                                logger.warning(
                                    f"Retrying email {message.subject} to {message.recipients}. "
                                    f"Attempt {retry_count + 1}/{self.MAX_RETRIES}",
                                    extra={"request_id": message.request_id}
                                )
                                time.sleep(self.RETRY_DELAY * (2 ** retry_count))  # Exponential backoff
                            else:
                                logger.error(
                                    f"Failed to send email {message.subject} to {message.recipients} "
                                    f"after {self.MAX_RETRIES} attempts",
                                    extra={"request_id": message.request_id}
                                )
                        except Exception as e:
                            logger.error(f"Error in send attempt {retry_count + 1}: {str(e)}", 
                                       extra={"request_id": message.request_id})
                            retry_count += 1
                            if retry_count < self.MAX_RETRIES:
                                time.sleep(self.RETRY_DELAY * (2 ** retry_count))
                    
                    self.email_queue.task_done()
                else:
                    time.sleep(1)  # Prevent busy-waiting
                    
            except Exception as e:
                logger.error(f"Error in email queue processing: {str(e)}", extra={"request_id": "QUEUE"})
                time.sleep(self.RETRY_DELAY)

# Initialize the notification service
email_service = EmailNotificationService()

def send_feedback_invitation(recipient_email: str, requestor_name: str, topic: str, feedback_url: str, request_id: str):
    """Send feedback invitation email with proper error handling"""
    try:
        logger.info(f"Preparing feedback invitation email for {recipient_email}", extra={"request_id": request_id})
        
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
        logger.debug("Email content prepared", extra={"request_id": request_id})
        
        message = EmailMessage(
            subject=f"Feedback Request from {requestor_name}",
            recipients=[recipient_email],
            html_content=html_content,
            request_id=request_id
        )
        
        email_service.queue_email(message)
        logger.info(f"Feedback invitation email queued for {recipient_email}", extra={"request_id": request_id})
        
    except Exception as e:
        logger.error(f"Error preparing feedback invitation email: {str(e)}", extra={"request_id": request_id})
        raise

def send_feedback_submitted_notification(recipient_email: str, provider_name: str, topic: str, feedback_url: str, request_id: str):
    """Send feedback submission notification email with proper error handling"""
    try:
        logger.info(f"Preparing feedback submission notification for {recipient_email}", extra={"request_id": request_id})
        
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
        logger.debug("Email content prepared", extra={"request_id": request_id})
        
        message = EmailMessage(
            subject=f"New Feedback Received from {provider_name}",
            recipients=[recipient_email],
            html_content=html_content,
            request_id=request_id
        )
        
        email_service.queue_email(message)
        logger.info(f"Feedback submission notification email queued for {recipient_email}", 
                   extra={"request_id": request_id})
        
    except Exception as e:
        logger.error(f"Error preparing feedback submission notification: {str(e)}", extra={"request_id": request_id})
        raise

def send_analysis_completed_notification(recipient_email: str, topic: str, feedback_url: str, request_id: str):
    """Send analysis completion notification email with proper error handling"""
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
        logger.debug("Email content prepared", extra={"request_id": request_id})
        
        message = EmailMessage(
            subject=f"Feedback Analysis Complete - {topic}",
            recipients=[recipient_email],
            html_content=html_content,
            request_id=request_id
        )
        
        email_service.queue_email(message)
        logger.info(f"Analysis completion notification email queued for {recipient_email}", 
                   extra={"request_id": request_id})
        
    except Exception as e:
        logger.error(f"Error preparing analysis completion notification: {str(e)}", 
                    extra={"request_id": request_id})
        raise
