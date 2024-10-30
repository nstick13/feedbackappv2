document.addEventListener('DOMContentLoaded', function() {
    const submitButton = document.getElementById('submitRequest');
    
    submitButton.addEventListener('click', async function() {
        const topic = document.getElementById('topic').value;
        const providersText = document.getElementById('providers').value;
        const providers = providersText.split('\n').map(email => email.trim()).filter(email => email);
        
        if (!topic || providers.length === 0) {
            alert('Please fill in all required fields');
            return;
        }
        
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
            
            if (data.status === 'success') {
                window.location.reload();
            } else {
                alert('Error creating feedback request');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error creating feedback request');
        }
    });
});
