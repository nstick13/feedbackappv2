document.addEventListener('DOMContentLoaded', function() {
    const submitButton = document.getElementById('submitFeedback');
    
    if (submitButton) {
        submitButton.addEventListener('click', async function() {
            const responses = Array.from(document.querySelectorAll('.feedback-response'))
                .map(textarea => textarea.value);
            
            const questions = Array.from(document.querySelectorAll('.form-label'))
                .map(label => label.textContent);
            
            const feedback = questions.map((question, index) => {
                return `${question}\n${responses[index]}`;
            }).join('\n\n');
            
            const requestId = window.location.pathname.split('/').pop();
            
            try {
                const response = await fetch(`/feedback/submit/${requestId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        feedback: feedback
                    })
                });
                
                const data = await response.json();
                
                if (data.status === 'success') {
                    window.location.href = '/dashboard';
                } else {
                    alert('Error submitting feedback');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error submitting feedback');
            }
        });
    }
});
