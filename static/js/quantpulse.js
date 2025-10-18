/**
 * QuantPulse - Custom JavaScript Library
 * Utility functions and enhancements for the QuantPulse trading platform
 */

// Global QuantPulse namespace
window.QuantPulse = {
    version: '1.0.0',
    config: {
        apiBaseUrl: '/api/v1',
        toastTimeout: 3000,
        chartDefaultColors: [
            '#007bff', '#28a745', '#dc3545', '#ffc107', 
            '#17a2b8', '#6f42c1', '#e83e8c', '#fd7e14'
        ]
    },
    utils: {},
    charts: {},
    api: {},
    components: {}
};

/**
 * Utility Functions
 */
QuantPulse.utils = {
    /**
     * Format currency with proper symbols
     */
    formatCurrency: function(amount, currency = 'USD', locale = 'en-US') {
        if (amount === null || amount === undefined) return '$0.00';
        
        return new Intl.NumberFormat(locale, {
            style: 'currency',
            currency: currency,
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount);
    },

    /**
     * Format percentage with proper precision
     */
    formatPercentage: function(value, precision = 2) {
        if (value === null || value === undefined) return '0.00%';
        return (value * 100).toFixed(precision) + '%';
    },

    /**
     * Format large numbers with K, M, B suffixes
     */
    formatNumber: function(num) {
        if (num === null || num === undefined) return '0';
        
        const absNum = Math.abs(num);
        if (absNum >= 1e9) {
            return (num / 1e9).toFixed(1) + 'B';
        } else if (absNum >= 1e6) {
            return (num / 1e6).toFixed(1) + 'M';
        } else if (absNum >= 1e3) {
            return (num / 1e3).toFixed(1) + 'K';
        }
        
        return num.toFixed(0);
    },

    /**
     * Debounce function for search inputs
     */
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * Throttle function for scroll events
     */
    throttle: function(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    /**
     * Generate random ID
     */
    generateId: function(length = 8) {
        return Math.random().toString(36).substring(2, length + 2);
    },

    /**
     * Copy text to clipboard
     */
    copyToClipboard: function(text) {
        if (navigator.clipboard) {
            return navigator.clipboard.writeText(text);
        } else {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            try {
                document.execCommand('copy');
                return Promise.resolve();
            } catch (err) {
                return Promise.reject(err);
            } finally {
                document.body.removeChild(textArea);
            }
        }
    },

    /**
     * Validate email format
     */
    isValidEmail: function(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },

    /**
     * Get color based on value (green for positive, red for negative)
     */
    getValueColor: function(value) {
        if (value > 0) return 'var(--qp-success)';
        if (value < 0) return 'var(--qp-danger)';
        return 'var(--qp-secondary)';
    },

    /**
     * Calculate percentage change
     */
    calculatePercentageChange: function(current, previous) {
        if (!previous || previous === 0) return 0;
        return ((current - previous) / previous) * 100;
    }
};

/**
 * API Helper Functions
 */
QuantPulse.api = {
    /**
     * Generic API request function
     */
    request: function(endpoint, options = {}) {
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        };

        // Add CSRF token if available
        const csrfToken = document.querySelector('meta[name="csrf-token"]');
        if (csrfToken) {
            defaultOptions.headers['X-CSRFToken'] = csrfToken.getAttribute('content');
        }

        const config = { ...defaultOptions, ...options };
        const url = endpoint.startsWith('/') ? QuantPulse.config.apiBaseUrl + endpoint : endpoint;

        return fetch(url, config)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            });
    },

    /**
     * GET request
     */
    get: function(endpoint) {
        return this.request(endpoint);
    },

    /**
     * POST request
     */
    post: function(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    /**
     * PUT request
     */
    put: function(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    /**
     * DELETE request
     */
    delete: function(endpoint) {
        return this.request(endpoint, {
            method: 'DELETE'
        });
    }
};

/**
 * Toast Notification System
 */
QuantPulse.toast = {
    show: function(message, type = 'info', duration = null) {
        const toastContainer = this.getOrCreateContainer();
        const toast = this.createElement(message, type);
        
        toastContainer.appendChild(toast);
        
        // Trigger animation
        setTimeout(() => toast.classList.add('show'), 100);
        
        // Auto-remove toast
        const timeout = duration || QuantPulse.config.toastTimeout;
        setTimeout(() => {
            this.hide(toast);
        }, timeout);
        
        return toast;
    },

    success: function(message, duration) {
        return this.show(message, 'success', duration);
    },

    error: function(message, duration) {
        return this.show(message, 'error', duration);
    },

    warning: function(message, duration) {
        return this.show(message, 'warning', duration);
    },

    info: function(message, duration) {
        return this.show(message, 'info', duration);
    },

    hide: function(toast) {
        toast.classList.add('hiding');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    },

    createElement: function(message, type) {
        const toast = document.createElement('div');
        toast.className = `toast-notification toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <span class="toast-icon">${this.getIcon(type)}</span>
                <span class="toast-message">${message}</span>
                <button class="toast-close" onclick="QuantPulse.toast.hide(this.parentElement.parentElement)">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        return toast;
    },

    getIcon: function(type) {
        const icons = {
            success: '<i class="fas fa-check-circle"></i>',
            error: '<i class="fas fa-exclamation-circle"></i>',
            warning: '<i class="fas fa-exclamation-triangle"></i>',
            info: '<i class="fas fa-info-circle"></i>'
        };
        return icons[type] || icons.info;
    },

    getOrCreateContainer: function() {
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        return container;
    }
};

/**
 * Chart Utilities
 */
QuantPulse.charts = {
    /**
     * Create a line chart for performance data
     */
    createPerformanceChart: function(canvas, data, options = {}) {
        const defaultOptions = {
            type: 'line',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        ticks: {
                            callback: function(value) {
                                return QuantPulse.utils.formatCurrency(value);
                            }
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        };

        const config = this.mergeOptions(defaultOptions, options);
        return new Chart(canvas, config);
    },

    /**
     * Create a pie chart for portfolio allocation
     */
    createPieChart: function(canvas, data, options = {}) {
        const defaultOptions = {
            type: 'pie',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const percentage = ((value / context.dataset.data.reduce((a, b) => a + b, 0)) * 100).toFixed(1);
                                return `${label}: ${QuantPulse.utils.formatCurrency(value)} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        };

        const config = this.mergeOptions(defaultOptions, options);
        return new Chart(canvas, config);
    },

    /**
     * Merge chart options deeply
     */
    mergeOptions: function(defaults, custom) {
        return this.deepMerge(defaults, custom);
    },

    /**
     * Deep merge objects
     */
    deepMerge: function(target, source) {
        const result = { ...target };
        
        for (const key in source) {
            if (source.hasOwnProperty(key)) {
                if (typeof source[key] === 'object' && source[key] !== null && !Array.isArray(source[key])) {
                    result[key] = this.deepMerge(result[key] || {}, source[key]);
                } else {
                    result[key] = source[key];
                }
            }
        }
        
        return result;
    }
};

/**
 * Form Validation Utilities
 */
QuantPulse.validation = {
    /**
     * Validate form fields
     */
    validateForm: function(form) {
        const errors = [];
        const formData = new FormData(form);
        
        // Get all required fields
        const requiredFields = form.querySelectorAll('[required]');
        
        requiredFields.forEach(field => {
            const value = formData.get(field.name);
            
            if (!value || value.trim() === '') {
                errors.push(`${this.getFieldLabel(field)} is required`);
                this.markFieldAsError(field);
            } else {
                this.clearFieldError(field);
            }
        });
        
        // Validate specific field types
        const emailFields = form.querySelectorAll('input[type="email"]');
        emailFields.forEach(field => {
            const value = formData.get(field.name);
            if (value && !QuantPulse.utils.isValidEmail(value)) {
                errors.push(`${this.getFieldLabel(field)} must be a valid email address`);
                this.markFieldAsError(field);
            }
        });
        
        return {
            isValid: errors.length === 0,
            errors: errors
        };
    },

    getFieldLabel: function(field) {
        const label = field.closest('.form-group')?.querySelector('label');
        return label ? label.textContent.replace('*', '').trim() : field.name;
    },

    markFieldAsError: function(field) {
        field.classList.add('is-invalid');
    },

    clearFieldError: function(field) {
        field.classList.remove('is-invalid');
    },

    clearAllErrors: function(form) {
        const errorFields = form.querySelectorAll('.is-invalid');
        errorFields.forEach(field => field.classList.remove('is-invalid'));
    }
};

/**
 * Loading Indicator Utilities
 */
QuantPulse.loading = {
    show: function(element, text = 'Loading...') {
        element.classList.add('loading');
        const loader = document.createElement('div');
        loader.className = 'loading-overlay';
        loader.innerHTML = `
            <div class="loading-content">
                <div class="spinner-quantpulse"></div>
                <span class="loading-text">${text}</span>
            </div>
        `;
        element.appendChild(loader);
    },

    hide: function(element) {
        element.classList.remove('loading');
        const loader = element.querySelector('.loading-overlay');
        if (loader) {
            loader.remove();
        }
    }
};

/**
 * WebSocket Connection Manager
 */
QuantPulse.websocket = {
    connection: null,
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,
    reconnectInterval: 5000,

    connect: function(url) {
        if (this.connection && this.connection.readyState === WebSocket.OPEN) {
            return;
        }

        this.connection = new WebSocket(url);
        
        this.connection.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this.onConnect();
        };

        this.connection.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.onMessage(data);
            } catch (e) {
                console.error('Error parsing WebSocket message:', e);
            }
        };

        this.connection.onclose = () => {
            console.log('WebSocket disconnected');
            this.onDisconnect();
            this.attemptReconnect(url);
        };

        this.connection.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    },

    disconnect: function() {
        if (this.connection) {
            this.connection.close();
            this.connection = null;
        }
    },

    send: function(data) {
        if (this.connection && this.connection.readyState === WebSocket.OPEN) {
            this.connection.send(JSON.stringify(data));
        }
    },

    attemptReconnect: function(url) {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => {
                console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                this.connect(url);
            }, this.reconnectInterval);
        }
    },

    onConnect: function() {
        // Override in implementation
    },

    onMessage: function(data) {
        // Override in implementation
    },

    onDisconnect: function() {
        // Override in implementation
    }
};

/**
 * Local Storage Utilities
 */
QuantPulse.storage = {
    set: function(key, value, expiry = null) {
        const data = {
            value: value,
            expiry: expiry ? Date.now() + expiry : null
        };
        localStorage.setItem(`qp_${key}`, JSON.stringify(data));
    },

    get: function(key) {
        try {
            const data = JSON.parse(localStorage.getItem(`qp_${key}`));
            if (!data) return null;
            
            if (data.expiry && Date.now() > data.expiry) {
                this.remove(key);
                return null;
            }
            
            return data.value;
        } catch (e) {
            return null;
        }
    },

    remove: function(key) {
        localStorage.removeItem(`qp_${key}`);
    },

    clear: function() {
        const keys = Object.keys(localStorage);
        keys.forEach(key => {
            if (key.startsWith('qp_')) {
                localStorage.removeItem(key);
            }
        });
    }
};

/**
 * Initialize QuantPulse on DOM ready
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Add loading states to forms
    const forms = document.querySelectorAll('form[data-async="true"]');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.classList.add('loading');
                submitBtn.disabled = true;
                
                // Re-enable after 10 seconds as fallback
                setTimeout(() => {
                    submitBtn.classList.remove('loading');
                    submitBtn.disabled = false;
                }, 10000);
            }
        });
    });

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert[data-auto-dismiss="true"]');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.parentNode) {
                alert.style.opacity = '0';
                alert.style.transform = 'translateY(-20px)';
                setTimeout(() => {
                    if (alert.parentNode) {
                        alert.parentNode.removeChild(alert);
                    }
                }, 300);
            }
        }, 5000);
    });

    // Console welcome message
    console.log('%cQuantPulse Trading Platform', 'color: #007bff; font-size: 20px; font-weight: bold;');
    console.log('%cVersion: ' + QuantPulse.version, 'color: #6c757d; font-size: 12px;');
});

// Expose QuantPulse globally for backward compatibility
window.QP = QuantPulse;