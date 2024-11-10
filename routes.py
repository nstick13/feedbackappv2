import logging
import uuid
from datetime import datetime
from flask import Blueprint, render_template, jsonify, request, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import db, FeedbackRequest, FeedbackProvider, FeedbackSession, User
from chat_service import generate_feedback_prompts, analyze_feedback, openai_client, initiate_user_conversation
from notification_service import (
    send_email,
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
            provider_email=current_user.email,
            status='invited'
        ).all()
        return render_template('dashboard.html', requests=my_requests, pending=pending_feedback)
    except Exception as e:
        logger.error(f"Error rendering dashboard: {str(e)}", extra={"request_id": request_id})
        return render_template('error.html', error=str(e)), 500

@main.route('/initiate_conversation', methods=['POST'])
@login_required
def initiate_conversation():
    request_id = str(uuid.uuid4())
    try:
        logger.debug(f"Initiating conversation for user {current_user.id}", extra={"request_id": request_id})
        
        data = request.get_json()
        user_input = data.get('user_input')
        
        if not user_input:
            logger.error("User input is required", extra={"request_id": request_id})
            return jsonify({"status": "error", "message": "User input is required"}), 400
        
        # Initiate conversation with OpenAI
        summary = initiate_user_conversation(user_input)
        
        # Create a new FeedbackRequest with the summary
        feedback_request = FeedbackRequest(
            topic=user_input,
            requestor_id=current_user.id,
            ai_context=summary
        )
        db.session.add(feedback_request)
        db.session.commit()
        
        return jsonify({"status": "success", "message": "Conversation initiated", "summary": summary}), 200
        
    except Exception as e:
        logger.error(f"Error initiating conversation: {str(e)}", extra={"request_id": request_id}, exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

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

