import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def verify_smtp_config():
    """Verify SMTP configuration and connection"""
    required_configs = {
        'MAIL_USERNAME': os.environ.get('MAIL_USERNAME'),
        'MAIL_PASSWORD': os.environ.get('MAIL_PASSWORD')
    }
    
    # Check for missing configurations
    missing_configs = [key for key, value in required_configs.items() if not value]
    if missing_configs:
        logger.error(f"Missing required configurations: {', '.join(missing_configs)}")
        return False
        
    try:
        logger.info("Testing SMTP connection...")
        
        # Create SMTP connection
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=30)
        server.set_debuglevel(1)
        
        # Start TLS
        logger.info("Initiating TLS connection...")
        server.starttls()
        
        # Authenticate
        logger.info("Attempting authentication...")
        server.login(required_configs['MAIL_USERNAME'], required_configs['MAIL_PASSWORD'])
        
        # Send test email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"SMTP Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        msg['From'] = required_configs['MAIL_USERNAME']
        msg['To'] = required_configs['MAIL_USERNAME']  # Send to self
        
        html_content = """
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2>SMTP Configuration Test</h2>
            <p>This is a test email to verify SMTP configuration.</p>
            <p>If you received this email, the SMTP configuration is working correctly.</p>
        </div>
        """
        
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        logger.info("Sending test email...")
        server.send_message(msg)
        
        # Close connection
        server.quit()
        logger.info("SMTP configuration test completed successfully!")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"Authentication failed: {str(e)}")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error occurred: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    verify_smtp_config()
