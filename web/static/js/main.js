/**
 * SmartForm Main JavaScript
 * Handles common functionality for the web interface
 */

// Global variables
let currentProcessingId = null;
let processingCheckInterval = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeComponents();
    setupEventListeners();
});

/**
 * Initialize all components
 */
function initializeComponents() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Add fade-in animation to cards
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
        card.classList.add('fade-in');
    });
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // File upload drag and drop
    setupFileUpload();
    
    // Processing status updates
    setupProcessingStatus();
    
    // Form validation
    setupFormValidation();
    
    // Auto-refresh dashboard
    setupAutoRefresh();
}

/**
 * Setup file upload with drag and drop
 */
function setupFileUpload() {
    const uploadArea = document.querySelector('.file-upload-area');
    const fileInput = document.querySelector('input[type="file"]');
    
    if (!uploadArea || !fileInput) return;
    
    // Drag and drop events
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            updateFileInfo(files[0]);
        }
    });
    
    // Click to upload
    uploadArea.addEventListener('click', function() {
        fileInput.click();
    });
    
    // File input change
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            updateFileInfo(this.files[0]);
        }
    });
}

/**
 * Update file information display
 */
function updateFileInfo(file) {
    const fileInfo = document.querySelector('.file-info');
    if (!fileInfo) return;
    
    const fileSize = formatFileSize(file.size);
    const fileType = file.type || 'Unknown';
    
    fileInfo.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas fa-file-alt me-3 text-primary" style="font-size: 2rem;"></i>
            <div>
                <h6 class="mb-1">${file.name}</h6>
                <small class="text-muted">${fileSize} • ${fileType}</small>
            </div>
        </div>
    `;
    
    // Show file info
    fileInfo.style.display = 'block';
}

/**
 * Format file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Setup processing status updates
 */
function setupProcessingStatus() {
    const processingId = document.querySelector('[data-processing-id]');
    if (processingId) {
        currentProcessingId = processingId.dataset.processingId;
        startProcessingCheck();
    }
}

/**
 * Start checking processing status
 */
function startProcessingCheck() {
    if (!currentProcessingId) return;
    
    processingCheckInterval = setInterval(function() {
        checkProcessingStatus(currentProcessingId);
    }, 2000); // Check every 2 seconds
}

/**
 * Check processing status via API
 */
function checkProcessingStatus(processingId) {
    fetch(`/api/processing/${processingId}`)
        .then(response => response.json())
        .then(data => {
            updateProcessingStatus(data);
            
            // Stop checking if completed or failed
            if (data.status === 'completed' || data.status === 'failed') {
                stopProcessingCheck();
                
                // Redirect to results page if completed
                if (data.status === 'completed') {
                    setTimeout(() => {
                        window.location.href = `/processing/${processingId}`;
                    }, 1000);
                }
            }
        })
        .catch(error => {
            console.error('Error checking processing status:', error);
        });
}

/**
 * Update processing status display
 */
function updateProcessingStatus(data) {
    const statusElement = document.querySelector('.processing-status');
    const progressElement = document.querySelector('.processing-progress');
    
    if (statusElement) {
        statusElement.textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1);
        statusElement.className = `status-badge status-${data.status}`;
    }
    
    if (progressElement) {
        progressElement.style.width = `${data.progress}%`;
        progressElement.setAttribute('aria-valuenow', data.progress);
    }
}

/**
 * Stop processing status check
 */
function stopProcessingCheck() {
    if (processingCheckInterval) {
        clearInterval(processingCheckInterval);
        processingCheckInterval = null;
    }
}

/**
 * Setup form validation
 */
function setupFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        });
    });
}

/**
 * Setup auto-refresh for dashboard
 */
function setupAutoRefresh() {
    const dashboard = document.querySelector('.dashboard');
    if (!dashboard) return;
    
    // Auto-refresh dashboard every 30 seconds
    setInterval(function() {
        refreshDashboard();
    }, 30000);
}

/**
 * Refresh dashboard data
 */
function refreshDashboard() {
    fetch('/api/dashboard')
        .then(response => response.json())
        .then(data => {
            updateDashboardStats(data);
        })
        .catch(error => {
            console.error('Error refreshing dashboard:', error);
        });
}

/**
 * Update dashboard statistics
 */
function updateDashboardStats(data) {
    // Update stats cards
    const totalProcessings = document.querySelector('.total-processings');
    const completedProcessings = document.querySelector('.completed-processings');
    
    if (totalProcessings) {
        totalProcessings.textContent = data.total_processings;
    }
    
    if (completedProcessings) {
        completedProcessings.textContent = data.completed_processings;
    }
}

/**
 * Show loading spinner
 */
function showLoading(element) {
    if (!element) return;
    
    element.innerHTML = `
        <div class="d-flex justify-content-center align-items-center">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
    `;
}

/**
 * Hide loading spinner
 */
function hideLoading(element, content) {
    if (!element) return;
    
    element.innerHTML = content;
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

/**
 * Confirm action
 */
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

/**
 * Download file
 */
function downloadFile(url, filename) {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * Copy to clipboard
 */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showNotification('Copied to clipboard!', 'success');
    }).catch(function(err) {
        console.error('Could not copy text: ', err);
        showNotification('Failed to copy to clipboard', 'danger');
    });
}

/**
 * Format date
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

/**
 * Format confidence score
 */
function formatConfidence(confidence) {
    if (confidence >= 0.8) {
        return `<span class="confidence-high">${(confidence * 100).toFixed(1)}%</span>`;
    } else if (confidence >= 0.6) {
        return `<span class="confidence-medium">${(confidence * 100).toFixed(1)}%</span>`;
    } else {
        return `<span class="confidence-low">${(confidence * 100).toFixed(1)}%</span>`;
    }
}

/**
 * Search functionality
 */
function setupSearch() {
    const searchInput = document.querySelector('.search-input');
    if (!searchInput) return;
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        const items = document.querySelectorAll('.searchable-item');
        
        items.forEach(item => {
            const text = item.textContent.toLowerCase();
            if (text.includes(searchTerm)) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    });
}

/**
 * Filter functionality
 */
function setupFilters() {
    const filterSelects = document.querySelectorAll('.filter-select');
    
    filterSelects.forEach(select => {
        select.addEventListener('change', function() {
            const filterValue = this.value;
            const filterType = this.dataset.filterType;
            const items = document.querySelectorAll(`[data-${filterType}]`);
            
            items.forEach(item => {
                const itemValue = item.dataset[filterType];
                if (filterValue === 'all' || itemValue === filterValue) {
                    item.style.display = '';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    });
}

// Export functions for use in other scripts
window.SmartForm = {
    showLoading,
    hideLoading,
    showNotification,
    confirmAction,
    downloadFile,
    copyToClipboard,
    formatDate,
    formatConfidence,
    setupSearch,
    setupFilters
};
