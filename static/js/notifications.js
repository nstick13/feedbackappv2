document.addEventListener('DOMContentLoaded', function() {
    if (!document.querySelector('.notification-icon')) {
        return; // Not logged in, don't initialize notifications
    }

    const socket = io();
    const notificationList = document.querySelector('.notification-list');
    const notificationBadge = document.querySelector('.notification-badge');
    const toastContainer = document.querySelector('.toast-container');
    
    let unreadCount = 0;
    
    function updateNotificationBadge() {
        if (unreadCount > 0) {
            notificationBadge.textContent = unreadCount;
            notificationBadge.classList.remove('d-none');
        } else {
            notificationBadge.classList.add('d-none');
        }
    }
    
    function showToast(title, message, link = null) {
        const toastId = `toast-${Date.now()}`;
        const toastHtml = `
            <div class="toast" role="alert" id="${toastId}">
                <div class="toast-header">
                    <strong class="me-auto">${title}</strong>
                    <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
                </div>
                <div class="toast-body">
                    ${message}
                    ${link ? `<br><a href="${link}" class="btn btn-primary btn-sm mt-2">View</a>` : ''}
                </div>
            </div>
        `;
        
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement);
        toast.show();
        
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }
    
    function addNotification(title, message, link = null) {
        const notificationHtml = `
            <a class="dropdown-item" href="${link || '#'}">
                <h6 class="mb-0">${title}</h6>
                <small class="text-muted">${message}</small>
            </a>
        `;
        
        notificationList.insertAdjacentHTML('afterbegin', notificationHtml);
        unreadCount++;
        updateNotificationBadge();
    }
    
    // Socket event handlers
    socket.on('connect', () => {
        console.log('Connected to notification service');
    });
    
    socket.on('new_feedback_request', (data) => {
        const title = 'New Feedback Request';
        const link = `/feedback/session/${data.request_id}`;
        addNotification(title, data.message, link);
        showToast(title, data.message, link);
    });
    
    socket.on('feedback_submitted', (data) => {
        const title = 'Feedback Received';
        const link = `/feedback/session/${data.request_id}`;
        addNotification(title, data.message, link);
        showToast(title, data.message, link);
    });
    
    socket.on('analysis_completed', (data) => {
        const title = 'Analysis Completed';
        const link = `/feedback/session/${data.request_id}`;
        addNotification(title, data.message, link);
        showToast(title, data.message, link);
    });
    
    // Clear notifications when dropdown is opened
    document.querySelector('#notificationsDropdown').addEventListener('shown.bs.dropdown', () => {
        unreadCount = 0;
        updateNotificationBadge();
    });
});
