from flask import Blueprint, render_template, jsonify, request, redirect, url_for
from flask_login import login_required, current_user
from models import db, FeedbackRequest, FeedbackProvider, FeedbackSession, User
from chat_service import generate_feedback_prompts, analyze_feedback
from email_service import send_feedback_invitation
from datetime import datetime

main = Blueprint('main', __name__)

@main.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main.route('/dashboard')
@login_required
def dashboard():
    my_requests = FeedbackRequest.query.filter_by(requestor_id=current_user.id).all()
    pending_feedback = FeedbackProvider.query.filter_by(
        provider_id=current_user.id,
        status='invited'
    ).all()
    return render_template('dashboard.html', requests=my_requests, pending=pending_feedback)

@main.route('/feedback/request', methods=['POST'])
@login_required
def create_feedback_request():
    data = request.get_json()
    topic = data.get('topic')
    provider_emails = data.get('providers', [])
    
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
    
    # Add providers
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
    return jsonify({"status": "success", "request_id": feedback_request.id})

@main.route('/feedback/session/<int:request_id>')
@login_required
def feedback_session(request_id):
    feedback_request = FeedbackRequest.query.get_or_404(request_id)
    provider = FeedbackProvider.query.filter_by(
        feedback_request_id=request_id,
        provider_id=current_user.id
    ).first()
    
    if not provider and feedback_request.requestor_id != current_user.id:
        return "Unauthorized", 403
        
    return render_template(
        'feedback_session.html',
        feedback_request=feedback_request,
        is_provider=bool(provider)
    )

@main.route('/feedback/submit/<int:request_id>', methods=['POST'])
@login_required
def submit_feedback(request_id):
    data = request.get_json()
    feedback_content = data.get('feedback')
    
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
    
    db.session.commit()
    return jsonify({"status": "success"})
