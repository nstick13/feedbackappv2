document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chatMessages');
    const chatForm = document.getElementById('chatForm');
    const messageInput = document.getElementById('messageInput');
    const toggleChat = document.getElementById('toggleChat');
    const errorContainer = document.createElement('div');
    
    // Set up error container
    errorContainer.className = 'alert alert-danger d-none mb-3';
    chatMessages.parentElement.insertBefore(errorContainer, chatMessages);
    
    // Initialize with a welcome message
    appendMessage('ai', 'Hello! I\'m your AI feedback assistant. How can I help you with the feedback process?');
    
    // Toggle chat visibility
    toggleChat.addEventListener('click', function() {
        const cardBody = this.closest('.card').querySelector('.card-body');
        const icon = this.querySelector('i');
        
        if (cardBody.style.display === 'none') {
            cardBody.style.display = 'block';
            icon.classList.remove('bi-chevron-down');
            icon.classList.add('bi-chevron-up');
        } else {
            cardBody.style.display = 'none';
            icon.classList.remove('bi-chevron-up');
            icon.classList.add('bi-chevron-down');
        }
    });
    
    // Handle message submission
    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const message = messageInput.value.trim();
        if (!message) return;
        
        // Display user message
        appendMessage('user', message);
        messageInput.value = '';
        hideError();
        
        try {
            const response = await fetch('/chat/message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    request_id: getRequestId()
                })
            });
            
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                appendMessage('ai', data.response);
            } else {
                showError(data.message || 'Failed to get response from AI assistant');
                appendMessage('ai', 'I apologize, but I encountered an error. Please try again.');
            }
        } catch (error) {
            console.error('Error:', error);
            showError('Network error occurred. Please try again.');
            appendMessage('ai', 'Sorry, I encountered a network error. Please try again.');
        }
    });
    
    // Helper function to append messages
    function appendMessage(type, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${type}`;
        messageDiv.textContent = content;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Helper function to show error
    function showError(message) {
        errorContainer.textContent = message;
        errorContainer.classList.remove('d-none');
    }
    
    // Helper function to hide error
    function hideError() {
        errorContainer.classList.add('d-none');
    }
    
    // Helper function to get request ID from URL
    function getRequestId() {
        return window.location.pathname.split('/').pop();
    }
});
