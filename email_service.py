from flask_mail import Message
from app import mail
from flask import render_template_string

def send_feedback_invitation(recipient_email: str, requestor_name: str, topic: str, feedback_url: str):
    subject = f"Feedback Request from {requestor_name}"
    
    html_content = """
    <h2>Feedback Request</h2>
    <p>Hello,</p>
    <p>{{ requestor_name }} has requested your feedback regarding: {{ topic }}</p>
    <p>Please click the link below to provide your feedback:</p>
    <a href="{{ feedback_url }}">Provide Feedback</a>
    <p>Thank you for your time!</p>
    """
    
    html = render_template_string(
        html_content,
        requestor_name=requestor_name,
        topic=topic,
        feedback_url=feedback_url
    )
    
    msg = Message(
        subject=subject,
        recipients=[recipient_email],
        html=html,
        sender="noreply@feedbackplatform.com"
    )
    
    mail.send(msg)
