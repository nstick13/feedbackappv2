from flask_socketio import SocketIO, emit
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
    def handle_connect():
        logger.info(f"Client connected: {current_user.id}")
        socketio.emit('connection_response', {'status': 'connected'}, room=request.sid)

    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info("Client disconnected")

def notify_new_feedback_request(provider_id, request_data):
    """Notify a provider about a new feedback request"""
    socketio.emit(
        'new_feedback_request',
        {
            'message': f'You have received a new feedback request about: {request_data["topic"]}',
            'request_id': request_data['request_id']
        },
        room=f'user_{provider_id}'
    )

def notify_feedback_submitted(requestor_id, feedback_data):
    """Notify the requestor about submitted feedback"""
    socketio.emit(
        'feedback_submitted',
        {
            'message': f'New feedback received for: {feedback_data["topic"]}',
            'request_id': feedback_data['request_id']
        },
        room=f'user_{requestor_id}'
    )

def notify_analysis_completed(requestor_id, analysis_data):
    """Notify the requestor about completed feedback analysis"""
    socketio.emit(
        'analysis_completed',
        {
            'message': f'Feedback analysis completed for: {analysis_data["topic"]}',
            'request_id': analysis_data['request_id']
        },
        room=f'user_{requestor_id}'
    )
