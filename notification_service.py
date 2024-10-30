from flask_socketio import SocketIO, emit, disconnect
from flask import request
from flask_login import current_user
from functools import wraps
import logging

logger = logging.getLogger(__name__)
socketio = SocketIO()

def authenticated_only(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            disconnect()
        else:
            return f(*args, **kwargs)
    return wrapped

def init_socket(app):
    socketio.init_app(app, cors_allowed_origins="*")
    
    @socketio.on('connect')
    @authenticated_only
    def handle_connect(*args):
        logger.info(f"Client connected: {current_user.id}")
        emit('connection_response', {'status': 'connected'}, room=request.sid)

    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info("Client disconnected")

def notify_new_feedback_request(provider_id, request_data):
    """Notify a provider about a new feedback request"""
    try:
        logger.info(f"Sending new feedback request notification to user {provider_id}")
        socketio.emit(
            'new_feedback_request',
            {
                'message': f'You have received a new feedback request about: {request_data["topic"]}',
                'request_id': request_data['request_id']
            },
            room=f'user_{provider_id}'
        )
    except Exception as e:
        logger.error(f"Error sending new feedback request notification: {str(e)}")

def notify_feedback_submitted(requestor_id, feedback_data):
    """Notify the requestor about submitted feedback"""
    try:
        logger.info(f"Sending feedback submitted notification to user {requestor_id}")
        socketio.emit(
            'feedback_submitted',
            {
                'message': f'New feedback received for: {feedback_data["topic"]}',
                'request_id': feedback_data['request_id']
            },
            room=f'user_{requestor_id}'
        )
    except Exception as e:
        logger.error(f"Error sending feedback submitted notification: {str(e)}")

def notify_analysis_completed(requestor_id, analysis_data):
    """Notify the requestor about completed feedback analysis"""
    try:
        logger.info(f"Sending analysis completed notification to user {requestor_id}")
        socketio.emit(
            'analysis_completed',
            {
                'message': f'Feedback analysis completed for: {analysis_data["topic"]}',
                'request_id': analysis_data['request_id']
            },
            room=f'user_{requestor_id}'
        )
    except Exception as e:
        logger.error(f"Error sending analysis completed notification: {str(e)}")
