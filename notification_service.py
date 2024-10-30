import logging
import os
import time
from typing import List, Optional
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from flask import current_app
from queue import Queue
import threading
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EmailMessage:
    subject: str
    recipients: List[str]
    html_content: str
    sender: str = "noreply@feedbackplatform.com"
    retry_count: int = 0

class EmailNotificationService:
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    
    def __init__(self):
        self.email_queue: Queue[EmailMessage] = Queue()
        self.worker_thread = threading.Thread(target=self._process_email_queue, daemon=True)
        self.worker_thread.start()
        logger.info("Email notification service initialized")

    def send_email(self, message: EmailMessage) -> bool:
        try:
            logger.info(f"Preparing to send email: {message.subject} to {message.recipients}")
            
            with smtplib.SMTP(current_app.config['MAIL_SERVER'], 
                            current_app.config['MAIL_PORT']) as server:
                
                # Log connection attempt
                logger.debug("Attempting SMTP connection")
                
                if current_app.config['MAIL_USE_TLS']:
                    server.starttls()
                    logger.debug("TLS connection established")

                # Authenticate
                username = current_app.config['MAIL_USERNAME']
                password = current_app.config['MAIL_PASSWORD']
                
                if not username or not password:
                    raise ValueError("SMTP credentials not configured")
                
                server.login(username, password)
                logger.debug("SMTP authentication successful")

                # Create message
                msg = MIMEMultipart('alternative')
                msg['Subject'] = message.subject
                msg['From'] = message.sender
                msg['To'] = ', '.join(message.recipients)
                
                html_part = MIMEText(message.html_content, 'html')
                msg.attach(html_part)

                # Send email
                server.send_message(msg)
                
                logger.info(f"Email sent successfully: {message.subject} to {message.recipients}")
                return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication failed: {str(e)}")
            raise
        except smtplib.SMTPServerDisconnected as e:
            logger.error(f"SMTP Server disconnected: {str(e)}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error occurred: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email: {str(e)}")
            return False

    def queue_email(self, message: EmailMessage):
        """Add email to the queue for processing"""
        try:
            logger.info(f"Queueing email: {message.subject} for {message.recipients}")
            self.email_queue.put(message)
        except Exception as e:
            logger.error(f"Error queueing email: {str(e)}")

    def _process_email_queue(self):
        """Process emails in the queue with retry logic"""
        while True:
            try:
                if not self.email_queue.empty():
                    message = self.email_queue.get()
                    
                    # Attempt to send email with retries
                    while message.retry_count < self.MAX_RETRIES:
                        if self.send_email(message):
                            break
                        
                        message.retry_count += 1
                        if message.retry_count < self.MAX_RETRIES:
                            logger.warning(
                                f"Retrying email {message.subject} to {message.recipients}. "
                                f"Attempt {message.retry_count + 1}/{self.MAX_RETRIES}"
                            )
                            time.sleep(self.RETRY_DELAY)
                        else:
                            logger.error(
                                f"Failed to send email {message.subject} to {message.recipients} "
                                f"after {self.MAX_RETRIES} attempts"
                            )
                    
                    self.email_queue.task_done()
                else:
                    time.sleep(1)  # Prevent busy-waiting
                    
            except Exception as e:
                logger.error(f"Error in email queue processing: {str(e)}")
                time.sleep(self.RETRY_DELAY)

# Initialize the notification service
email_service = EmailNotificationService()

def send_feedback_invitation(recipient_email: str, requestor_name: str, topic: str, feedback_url: str):
    """Send feedback invitation email with proper error handling"""
    try:
        logger.info(f"Preparing feedback invitation email for {recipient_email}")
        
        html_content = f"""
        <h2>Feedback Request</h2>
        <p>Hello,</p>
        <p>{requestor_name} has requested your feedback regarding: {topic}</p>
        <p>Please click the link below to provide your feedback:</p>
        <a href="{feedback_url}">Provide Feedback</a>
        <p>Thank you for your time!</p>
        """
        
        message = EmailMessage(
            subject=f"Feedback Request from {requestor_name}",
            recipients=[recipient_email],
            html_content=html_content
        )
        
        email_service.queue_email(message)
        logger.info(f"Feedback invitation email queued for {recipient_email}")
        
    except Exception as e:
        logger.error(f"Error preparing feedback invitation email: {str(e)}")
        raise

def send_feedback_submitted_notification(recipient_email: str, provider_name: str, topic: str, feedback_url: str):
    """Send feedback submission notification email with proper error handling"""
    try:
        logger.info(f"Preparing feedback submission notification for {recipient_email}")
        
        html_content = f"""
        <h2>New Feedback Received</h2>
        <p>Hello,</p>
        <p>{provider_name} has submitted feedback for your request: {topic}</p>
        <p>Click the link below to view the feedback:</p>
        <a href="{feedback_url}">View Feedback</a>
        """
        
        message = EmailMessage(
            subject=f"New Feedback Received from {provider_name}",
            recipients=[recipient_email],
            html_content=html_content
        )
        
        email_service.queue_email(message)
        logger.info(f"Feedback submission notification email queued for {recipient_email}")
        
    except Exception as e:
        logger.error(f"Error preparing feedback submission notification: {str(e)}")
        raise

def send_analysis_completed_notification(recipient_email: str, topic: str, feedback_url: str):
    """Send analysis completion notification email with proper error handling"""
    try:
        logger.info(f"Preparing analysis completion notification for {recipient_email}")
        
        html_content = f"""
        <h2>Feedback Analysis Complete</h2>
        <p>Hello,</p>
        <p>The AI analysis of your feedback request for "{topic}" is now complete.</p>
        <p>Click the link below to view the analysis:</p>
        <a href="{feedback_url}">View Analysis</a>
        """
        
        message = EmailMessage(
            subject=f"Feedback Analysis Complete - {topic}",
            recipients=[recipient_email],
            html_content=html_content
        )
        
        email_service.queue_email(message)
        logger.info(f"Analysis completion notification email queued for {recipient_email}")
        
    except Exception as e:
        logger.error(f"Error preparing analysis completion notification: {str(e)}")
        raise
