import logging
import uuid
from datetime import datetime
from flask import Blueprint, render_template, jsonify, request, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import db, FeedbackRequest, FeedbackProvider, FeedbackSession, User
from chat_service import generate_feedback_prompts, analyze_feedback, openai_client, initiate_user_conversation
from notification_service import (
    send_feedback_request_email,
    send_feedback_invitation,
    send_feedback_submitted_notification,
    send_analysis_completed_notification
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

@main.route('/feedback/session/<int:request_id>')
def feedback_session(request_id):
    session_id = str(uuid.uuid4())
    try:
        logger.debug(f"Accessing feedback session {request_id}", extra={"request_id": session_id})
        feedback_request = FeedbackRequest.query.get_or_404(request_id)
        
        # Check authentication method
        token = request.args.get('token')
        if token:
            # Token-based authentication for feedback providers
            provider = verify_feedback_token(token)
            if not provider or provider.feedback_request_id != request_id:
                logger.warning(
                    f"Invalid token access attempt for session {request_id}",
                    extra={"request_id": session_id}
                )
                return render_template('error.html', error="Invalid or expired access token"), 403
            
            return render_template(
                'feedback_session.html',
                feedback_request=feedback_request,
                is_provider=True,
                chat_enabled=True
            )
        
        # Regular authentication check
        if not current_user.is_authenticated:
            return redirect(url_for('google_auth.login'))
            
        # Check if user is the requestor
        is_requestor = feedback_request.requestor_id == current_user.id
        
        # Check if user is a provider
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
        
        # Load providers and their feedback status for requestor view
        if is_requestor:
            providers = FeedbackProvider.query.filter_by(
                feedback_request_id=request_id
            ).all()
            
            # Load feedback sessions for completed feedback
            for p in providers:
                p.feedback_session = FeedbackSession.query.filter_by(
                    feedback_request_id=request_id,
                    provider_id=p.provider_id
                ).first()
            
            feedback_request.providers = providers
            
            return render_template(
                'feedback_session.html',
                feedback_request=feedback_request,
                is_provider=False,
                chat_enabled=False
            )
        
        # Provider view with chat interface
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

@main.route('/feedback/remind/<int:provider_id>', methods=['POST'])
@login_required
def send_reminder(provider_id):
    request_id = str(uuid.uuid4())
    try:
        provider = FeedbackProvider.query.get_or_404(provider_id)
        feedback_request = FeedbackRequest.query.get(provider.feedback_request_id)
        
        # Verify the current user is the requestor
        if feedback_request.requestor_id != current_user.id:
            logger.warning(
                f"Unauthorized reminder attempt for provider {provider_id}", 
                extra={"request_id": request_id}
            )
            return jsonify({
                "status": "error",
                "message": "Unauthorized access"
            }), 403
        
        # Generate new token for the provider
        token = create_feedback_token(provider.id)
        if not token:
            logger.error(f"Failed to create access token for provider {provider_id}", 
                        extra={"request_id": request_id})
            return jsonify({
                "status": "error",
                "message": "Failed to generate access token"
            }), 500
        
        # Send reminder email with token
        feedback_url = url_for(
            'main.feedback_session',
            request_id=feedback_request.id,
            token=token,
            _external=True
        )
        
        send_feedback_invitation(
            provider.provider_email,
            current_user.username,
            feedback_request.topic,
            feedback_url,
            request_id
        )
        
        provider.invitation_sent = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Reminder sent successfully"
        })
        
    except Exception as e:
        logger.error(f"Error sending reminder: {str(e)}", 
                    extra={"request_id": request_id},
                    exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@main.route('/chat/message', methods=['POST'])
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
        
        # Check authentication method
        token = request.args.get('token')
        if token:
            provider = verify_feedback_token(token)
            if not provider or provider.feedback_request_id != int(feedback_request_id):
                return jsonify({
                    "status": "error",
                    "message": "Invalid access token"
                }), 403
        else:
            if not current_user.is_authenticated:
                return jsonify({
                    "status": "error",
                    "message": "Authentication required"
                }), 401
                
            # Check if user is authorized to chat
            provider = FeedbackProvider.query.filter_by(
                feedback_request_id=feedback_request_id,
                provider_email=current_user.email
            ).first()
            
            # Only allow providers to use chat
            if not provider or feedback_request.requestor_id == current_user.id:
                logger.warning(
                    f"Unauthorized chat attempt for feedback request {feedback_request_id}",
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
        
        # Create a new feedback request
        feedback_request = FeedbackRequest(
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

