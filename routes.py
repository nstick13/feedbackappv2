import logging
from flask import Blueprint, render_template, jsonify, request, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import db, FeedbackRequest, FeedbackProvider, FeedbackSession, User
from chat_service import generate_feedback_prompts, analyze_feedback
from email_service import send_feedback_invitation, send_feedback_submitted_notification, send_analysis_completed_notification
from notification_service import notify_new_feedback_request, notify_feedback_submitted, notify_analysis_completed
from datetime import datetime

logger = logging.getLogger(__name__)
main = Blueprint('main', __name__)

@main.route('/')
def index():
    try:
        logger.debug("Rendering index page")
        if current_user.is_authenticated:
            return redirect(url_for('main.dashboard'))
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index page: {str(e)}")
        return render_template('error.html', error=str(e)), 500

@main.route('/dashboard')
@login_required
def dashboard():
    try:
        logger.debug(f"Fetching dashboard data for user {current_user.id}")
        my_requests = FeedbackRequest.query.filter_by(requestor_id=current_user.id).all()
        pending_feedback = FeedbackProvider.query.filter_by(
            provider_id=current_user.id,
            status='invited'
        ).all()
        return render_template('dashboard.html', requests=my_requests, pending=pending_feedback)
    except Exception as e:
        logger.error(f"Error rendering dashboard: {str(e)}")
        return render_template('error.html', error=str(e)), 500

@main.route('/feedback/request', methods=['POST'])
@login_required
def create_feedback_request():
    try:
        data = request.get_json()
        topic = data.get('topic')
        provider_emails = data.get('providers', [])
        
        if not topic:
            raise ValueError("Topic is required")
            
        logger.debug(f"Creating feedback request for topic: {topic}")
        
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
        
        # Add providers and send notifications
        for email in provider_emails:
            provider = User.query.filter_by(email=email).first()
            if provider:
                provider_entry = FeedbackProvider(
                    feedback_request_id=feedback_request.id,
                    provider_id=provider.id,
                    invitation_sent=datetime.utcnow()
                )
                db.session.add(provider_entry)
                
                # Send email invitation
                feedback_url = url_for(
                    'main.feedback_session',
                    request_id=feedback_request.id,
                    _external=True
                )
                send_feedback_invitation(
                    email,
                    current_user.username,
                    topic,
                    feedback_url
                )
                
                # Send real-time notification
                notify_new_feedback_request(provider.id, {
                    'topic': topic,
                    'request_id': feedback_request.id
                })
        
        db.session.commit()
        logger.info(f"Successfully created feedback request {feedback_request.id}")
        return jsonify({"status": "success", "request_id": feedback_request.id})
        
    except Exception as e:
        logger.error(f"Error creating feedback request: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@main.route('/feedback/submit/<int:request_id>', methods=['POST'])
@login_required
def submit_feedback(request_id):
    try:
        data = request.get_json()
        feedback_content = data.get('feedback')
        
        if not feedback_content:
            raise ValueError("Feedback content is required")
            
        logger.debug(f"Submitting feedback for request {request_id}")
        
        feedback_request = FeedbackRequest.query.get(request_id)
        if not feedback_request:
            raise ValueError("Feedback request not found")
        
        # Analyze feedback with AI
        analysis = analyze_feedback(feedback_content)
        
        session = FeedbackSession(
            feedback_request_id=request_id,
            provider_id=current_user.id,
            content={
                "feedback": feedback_content,
                "analysis": analysis
            },
            completed_at=datetime.utcnow()
        )
        
        db.session.add(session)
        
        # Update provider status
        provider = FeedbackProvider.query.filter_by(
            feedback_request_id=request_id,
            provider_id=current_user.id
        ).first()
        if provider:
            provider.status = 'completed'
        
        # Send notifications
        notify_feedback_submitted(feedback_request.requestor_id, {
            'topic': feedback_request.topic,
            'request_id': request_id
        })
        
        notify_analysis_completed(feedback_request.requestor_id, {
            'topic': feedback_request.topic,
            'request_id': request_id
        })
        
        db.session.commit()
        logger.info(f"Successfully submitted feedback for request {request_id}")
        return jsonify({"status": "success"})
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
