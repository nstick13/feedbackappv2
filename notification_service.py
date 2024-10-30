from flask_socketio import SocketIO
from flask import session

socketio = SocketIO()

@socketio.on('connect')
def handle_connect():
    print("Client connected")

def notify_new_feedback_request(user_id, data):
    """Notify user about new feedback request"""
    socketio.emit(f'new_feedback_request_{user_id}', data)

def notify_feedback_submitted(user_id, data):
    """Notify requestor when feedback is submitted"""
    socketio.emit(f'feedback_submitted_{user_id}', data)

def notify_analysis_completed(user_id, data):
    """Notify requestor when feedback analysis is complete"""
    socketio.emit(f'analysis_completed_{user_id}', data)
