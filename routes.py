import logging
import uuid
from datetime import datetime
from flask import Blueprint, render_template, jsonify, request, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import db, FeedbackRequest, FeedbackProvider, FeedbackSession, User
from chat_service import generate_feedback_prompts, analyze_feedback, openai_client, initiate_user_conversation
from notification_service import (
    send_feedback_request_email,
)
from auth_utils import create_feedback_token, verify_feedback_token
import json

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
        
        # Create a new feedback request with the UUID
        feedback_request = FeedbackRequest(
            request_id=request_id,
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

@main.route('/feedback_session/<request_id>', methods=['GET', 'POST'])
def feedback_session(request_id):
    feedback_request = FeedbackRequest.query.filter_by(request_id=request_id).first()
    if not feedback_request:
        return "Invalid request ID", 404
    # Continue with your logic

@main.route('/send_reminder/<request_id>', methods=['POST'])
@login_required
def send_reminder(request_id):
    try:
        feedback_request = FeedbackRequest.query.filter_by(request_id=request_id).first()
        if not feedback_request:
            return jsonify({"error": "Invalid request ID"}), 404
        
        # Your existing code for sending reminder
        # Example: send_reminder_email(feedback_request)
        
        return jsonify({"message": "Reminder sent successfully"}), 200
    except Exception as e:
        logger.error(f"Failed to send reminder: {str(e)}", extra={"request_id": request_id})
        return jsonify({"error": "Failed to send reminder"}), 500

