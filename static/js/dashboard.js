document.addEventListener('DOMContentLoaded', function() {
    const submitButton = document.getElementById('submitRequest');
    const feedbackForm = document.getElementById('feedbackRequestForm');
    const modal = document.getElementById('newFeedbackModal');
    const modalInstance = new bootstrap.Modal(modal);
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger d-none mb-3';
    feedbackForm.insertBefore(errorDiv, feedbackForm.firstChild);
    
    function showError(message) {
        console.error('Error:', message);
        errorDiv.textContent = message;
        errorDiv.classList.remove('d-none');
    }
    
    function hideError() {
        errorDiv.classList.add('d-none');
    }
    
    function setLoading(isLoading) {
        if (isLoading) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Submitting...';
        } else {
            submitButton.disabled = false;
            submitButton.textContent = 'Request Feedback';
        }
    }
    
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
    
    // Reset form and error state when modal is closed
    modal.addEventListener('hidden.bs.modal', function() {
        feedbackForm.reset();
        hideError();
        setLoading(false);
    });
});
