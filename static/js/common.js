// Common JavaScript functions
document.addEventListener('DOMContentLoaded', function() {
    // Add CSRF token to all fetch requests if needed
    const token = document.querySelector('meta[name="csrf-token"]');
    if (token) {
        window.csrfToken = token.content;
    }

    // Handle flash messages
    const flashMessage = document.querySelector('.alert');
    if (flashMessage) {
        setTimeout(() => {
            flashMessage.style.opacity = '0';
            setTimeout(() => flashMessage.remove(), 300);
        }, 3000);
    }
});

// Global error handler for fetch requests
function handleFetchError(error) {
    console.error('Error:', error);
    alert('An error occurred. Please try again.');
}
