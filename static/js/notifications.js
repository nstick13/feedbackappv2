document.addEventListener('DOMContentLoaded', function() {
    if (!io) {
        console.error('Socket.IO not loaded');
        return;
    }

    const socket = io();
    const userId = document.body.getAttribute('data-user-id');
    const notificationBadge = document.querySelector('.notification-badge');
    const notificationList = document.querySelector('.notification-list');
    const toastContainer = document.querySelector('.toast-container');
    
    let unreadCount = 0;

    socket.on('connect', () => {
        console.log('Connected to notification service');
    });

    // Listen for new feedback requests
    socket.on(`new_feedback_request_${userId}`, (data) => {
        showNotification('New Feedback Request', `New feedback request for: ${data.topic}`);
        updateNotificationCount();
    });

    // Listen for feedback submissions
    socket.on(`feedback_submitted_${userId}`, (data) => {
        showNotification('Feedback Received', `New feedback received for: ${data.topic}`);
        updateNotificationCount();
    });

    // Listen for analysis completion
    socket.on(`analysis_completed_${userId}`, (data) => {
        showNotification('Analysis Complete', `Feedback analysis completed for: ${data.topic}`);
        updateNotificationCount();
    });

    function showNotification(title, message) {
        // Create toast notification
        const toastElement = document.createElement('div');
        toastElement.className = 'toast';
        toastElement.setAttribute('role', 'alert');
        toastElement.innerHTML = `
            <div class="toast-header">
                <strong class="me-auto">${title}</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">${message}</div>
        `;
        
        toastContainer.appendChild(toastElement);
        const toast = new bootstrap.Toast(toastElement);
        toast.show();

        // Add to notification dropdown
        const notificationItem = document.createElement('a');
        notificationItem.className = 'dropdown-item';
        notificationItem.href = '#';
        notificationItem.textContent = `${title}: ${message}`;
        notificationList.insertBefore(notificationItem, notificationList.firstChild);
    }

    function updateNotificationCount() {
        unreadCount++;
        notificationBadge.textContent = unreadCount;
        notificationBadge.classList.remove('d-none');
    }
});
