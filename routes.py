import logging
import uuid
from datetime import datetime
from flask import Blueprint, render_template, jsonify, request, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import db, FeedbackRequest, FeedbackProvider, FeedbackSession, User
from chat_service import generate_feedback_prompts, analyze_feedback, openai_client
from notification_service import (
    send_email,
    send_feedback_invitation,
    send_feedback_submitted_notification,
    send_analysis_completed_notification
)
import json

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
        
        prompts = generate_feedback_prompts(topic)
        
        feedback_request = FeedbackRequest(
            topic=topic,
            requestor_id=current_user.id,
            ai_context=prompts
        )
        db.session.add(feedback_request)
        db.session.flush()
        
        email_errors = []
        for email in provider_emails:
            logger.debug(f"Processing provider email: {email}", extra={"request_id": request_id})
            
            try:
                invitation_sent_time = datetime.utcnow()
                provider = FeedbackProvider(
                    feedback_request_id=feedback_request.id,
                    provider_email=email,
                    invitation_sent=invitation_sent_time
                )
                db.session.add(provider)
                
                feedback_url = url_for(
                    'main.feedback_session',
                    request_id=feedback_request.id,
                    _external=True
                )
                
                try:
                    send_feedback_invitation(
                        email,
                        current_user.username,
                        topic,
                        feedback_url,
                        request_id
                    )
                except Exception as email_error:
                    logger.error(
                        f"Failed to send invitation email to {email}\n"
                        f"Error: {str(email_error)}",
                        extra={"request_id": request_id},
                        exc_info=True
                    )
                    email_errors.append(email)
            except Exception as e:
                logger.error(
                    f"Error processing provider {email}: {str(e)}",
                    extra={"request_id": request_id},
                    exc_info=True
                )
                email_errors.append(email)
        
        db.session.commit()
        
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
        is_requestor = feedback_request.requestor_id == current_user.id
        
        # Check if user is a provider for this feedback request
        provider = FeedbackProvider.query.filter_by(
            feedback_request_id=request_id,
            provider_email=current_user.email
        ).first()
        
        # Ensure user has proper access
        if not (is_requestor or provider):
            logger.warning(
                f"Unauthorized access attempt to feedback session {request_id} by user {current_user.id}", 
                extra={"request_id": session_id}
            )
            return render_template('error.html', error="Unauthorized access"), 403
        
        # Only allow providers to use the chat interface
        if is_requestor:
            return render_template(
                'feedback_session.html',
                feedback_request=feedback_request,
                is_provider=False,
                chat_enabled=False
            )
        
        return render_template(
            'feedback_session.html',
            feedback_request=feedback_request,
            is_provider=True,
            chat_enabled=True
        )
    except Exception as e:
        logger.error(f"Error accessing feedback session: {str(e)}", 
                    extra={"request_id": session_id},
                    exc_info=True)
        return render_template('error.html', error=str(e)), 500

@main.route('/chat/message', methods=['POST'])
@login_required
def chat_message():
    request_id = str(uuid.uuid4())
    logger.debug(f"Received chat message request", extra={"request_id": request_id})
    
    try:
        data = request.get_json()
        user_message = data.get('message')
        feedback_request_id = data.get('request_id')
        
        if not user_message or not feedback_request_id:
            logger.error(f"Missing required parameters", extra={"request_id": request_id})
            return jsonify({
                "status": "error",
                "message": "Missing required parameters"
            }), 400
        
        feedback_request = FeedbackRequest.query.get_or_404(feedback_request_id)
        
        # Check if user is authorized to chat
        provider = FeedbackProvider.query.filter_by(
            feedback_request_id=feedback_request_id,
            provider_email=current_user.email
        ).first()
        
        # Only allow providers to use chat
        if not provider or feedback_request.requestor_id == current_user.id:
            logger.warning(
                f"Unauthorized chat attempt for feedback request {feedback_request_id} by user {current_user.id}",
                extra={"request_id": request_id}
            )
            return jsonify({
                "status": "error",
                "message": "Unauthorized access"
            }), 403
        
        context = {
            "topic": feedback_request.topic,
            "ai_context": feedback_request.ai_context,
            "user_role": "provider"
        }
        
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"You are an AI feedback assistant helping with a feedback session about: {context['topic']}. The user is the feedback provider."},
                    {"role": "user", "content": user_message}
                ]
            )
            
            ai_response = response.choices[0].message.content
            
            return jsonify({
                "status": "success",
                "response": ai_response
            })
            
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}", 
                        extra={"request_id": request_id},
                        exc_info=True)
            return jsonify({
                "status": "error",
                "message": "Failed to generate response"
            }), 500
            
    except Exception as e:
        logger.error(f"Error in chat message endpoint: {str(e)}", 
                    extra={"request_id": request_id},
                    exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
