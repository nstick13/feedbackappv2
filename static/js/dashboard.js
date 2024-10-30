document.addEventListener('DOMContentLoaded', function() {
    const submitButton = document.getElementById('submitRequest');
    const feedbackForm = document.getElementById('feedbackRequestForm');
    const modal = document.getElementById('newFeedbackModal');
    const modalInstance = modal ? new bootstrap.Modal(modal) : null;
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger d-none mb-3';
    
    if (feedbackForm) {
        feedbackForm.insertBefore(errorDiv, feedbackForm.firstChild);
    }
    
    function showError(message, isWarning = false) {
        console.error('Error:', message);
        errorDiv.textContent = message;
        errorDiv.className = `alert ${isWarning ? 'alert-warning' : 'alert-danger'} mb-3`;
        errorDiv.classList.remove('d-none');
    }
    
    function hideError() {
        errorDiv.classList.add('d-none');
    }
    
    function setLoading(isLoading) {
        if (submitButton) {
            if (isLoading) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Submitting...';
            } else {
                submitButton.disabled = false;
                submitButton.textContent = 'Request Feedback';
            }
        }
    }
    
    // Handle feedback request submission
    if (submitButton) {
        submitButton.addEventListener('click', async function() {
            hideError();
            const topic = document.getElementById('topic').value;
            const providersText = document.getElementById('providers').value;
            const providers = providersText.split('\n').map(email => email.trim()).filter(email => email);
            
            // Validation
            if (!topic) {
                showError('Please enter a topic for feedback');
                return;
            }
            if (providers.length === 0) {
                showError('Please enter at least one provider email');
                return;
            }

            // Email validation
            const invalidEmails = providers.filter(email => !email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/));
            if (invalidEmails.length > 0) {
                showError(`Invalid email format: ${invalidEmails.join(', ')}`);
                return;
            }
            
            console.log('Submitting feedback request:', { topic, providers });
            setLoading(true);
            
            try {
                const response = await fetch('/feedback/request', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        topic: topic,
                        providers: providers
                    })
                });
                
                const data = await response.json();
                console.log('Server response:', data);
                
                if (data.status === 'success') {
                    console.log('Feedback request created successfully');
                    modalInstance.hide();
                    window.location.reload();
                } else if (data.status === 'partial_success') {
                    showError(data.message, true);
                    setTimeout(() => {
                        modalInstance.hide();
                        window.location.reload();
                    }, 3000);
                } else {
                    showError(data.message || 'Error creating feedback request');
                    setLoading(false);
                }
            } catch (error) {
                console.error('Request error:', error);
                showError('Failed to submit feedback request. Please try again.');
                setLoading(false);
            }
        });
    }
    
    // Handle reminder sending
    async function sendReminder(providerId) {
        try {
            const button = document.querySelector(`[data-provider-id="${providerId}"]`);
            if (button) {
                button.disabled = true;
                button.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
            }
            
            const response = await fetch(`/feedback/remind/${providerId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                if (button) {
                    button.innerHTML = 'Reminder Sent';
                    button.classList.remove('btn-outline-primary');
                    button.classList.add('btn-success');
                }
            } else {
                if (button) {
                    button.disabled = false;
                    button.innerHTML = 'Send Reminder';
                }
                alert(data.message || 'Failed to send reminder');
            }
        } catch (error) {
            console.error('Error sending reminder:', error);
            alert('Failed to send reminder. Please try again.');
            if (button) {
                button.disabled = false;
                button.innerHTML = 'Send Reminder';
            }
        }
    }
    
    // Add event listeners for reminder buttons
    document.querySelectorAll('.send-reminder').forEach(button => {
        button.addEventListener('click', function() {
            const providerId = this.dataset.providerId;
            sendReminder(providerId);
        });
    });
    
    // Reset form and error state when modal is closed
    if (modal) {
        modal.addEventListener('hidden.bs.modal', function() {
            feedbackForm.reset();
            hideError();
            setLoading(false);
        });
    }
});
