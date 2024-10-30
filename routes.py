import logging
from flask import Blueprint, render_template, jsonify, request, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import db, FeedbackRequest, FeedbackProvider, FeedbackSession, User
from chat_service import generate_feedback_prompts, analyze_feedback
from email_service import send_feedback_invitation, send_feedback_submitted_notification, send_analysis_completed_notification
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
        
        # Add providers and send email invitations
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
        
        db.session.commit()
        logger.info(f"Successfully created feedback request {feedback_request.id}")
        return jsonify({"status": "success", "request_id": feedback_request.id})
        
    except Exception as e:
        logger.error(f"Error creating feedback request: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@main.route('/feedback/session/<int:request_id>')
@login_required
def feedback_session(request_id):
    try:
        logger.debug(f"Accessing feedback session {request_id}")
        feedback_request = FeedbackRequest.query.get_or_404(request_id)
        provider = FeedbackProvider.query.filter_by(
            feedback_request_id=request_id,
            provider_id=current_user.id
        ).first()
        
        if not provider and feedback_request.requestor_id != current_user.id:
            logger.warning(f"Unauthorized access attempt to feedback session {request_id}")
            return render_template('error.html', error="Unauthorized access"), 403
            
        return render_template(
            'feedback_session.html',
            feedback_request=feedback_request,
            is_provider=bool(provider)
        )
    except Exception as e:
        logger.error(f"Error accessing feedback session: {str(e)}")
        return render_template('error.html', error=str(e)), 500

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
        
        # Get requestor's email
        requestor = User.query.get(feedback_request.requestor_id)
        feedback_url = url_for('main.feedback_session', request_id=request_id, _external=True)
        
        # Send email notifications
        send_feedback_submitted_notification(
            requestor.email,
            current_user.username,
            feedback_request.topic,
            feedback_url
        )
        
        send_analysis_completed_notification(
            requestor.email,
            feedback_request.topic,
            feedback_url
        )
        
        db.session.commit()
        logger.info(f"Successfully submitted feedback for request {request_id}")
        return jsonify({"status": "success"})
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
