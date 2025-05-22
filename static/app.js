// Job Portal - Main JavaScript File

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeComponents();
    setupEventListeners();
    setupFormValidation();
    setupAnimations();
});

// Initialize Bootstrap components and custom functionality
function initializeComponents() {
    // Initialize all tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize all popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
}

// Setup global event listeners
function setupEventListeners() {
    // File upload validation
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(function(input) {
        input.addEventListener('change', validateFileUpload);
    });

    // Form submission loading states
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', handleFormSubmission);
    });

    // Search input debouncing
    const searchInputs = document.querySelectorAll('input[type="search"], input[id*="search"]');
    searchInputs.forEach(function(input) {
        let timeoutId;
        input.addEventListener('input', function() {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(function() {
                handleSearch(input);
            }, 300);
        });
    });

    // Card hover effects
    const cards = document.querySelectorAll('.card');
    cards.forEach(function(card) {
        card.addEventListener('mouseenter', function() {
            this.classList.add('shadow-lg');
        });
        card.addEventListener('mouseleave', function() {
            this.classList.remove('shadow-lg');
        });
    });

    // Smooth scrolling for anchor links
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    anchorLinks.forEach(function(link) {
        link.addEventListener('click', handleSmoothScroll);
    });
}

// File upload validation
function validateFileUpload(event) {
    const file = event.target.files[0];
    const input = event.target;
    const maxSize = 16 * 1024 * 1024; // 16MB
    
    if (!file) return;

    // Check file size
    if (file.size > maxSize) {
        showAlert('File size must be less than 16MB', 'danger');
        input.value = '';
        return;
    }

    // Check file type based on input accept attribute
    const acceptedTypes = input.accept.split(',').map(type => type.trim().toLowerCase());
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
    const mimeType = file.type.toLowerCase();

    const isValidType = acceptedTypes.some(type => {
        if (type.startsWith('.')) {
            return fileExtension === type;
        } else {
            return mimeType.startsWith(type.replace('*', ''));
        }
    });

    if (!isValidType) {
        showAlert('Invalid file type. Please check the allowed file formats.', 'danger');
        input.value = '';
        return;
    }

    // Visual feedback for successful upload
    const inputGroup = input.closest('.input-group') || input.parentElement;
    const feedback = inputGroup.querySelector('.file-feedback');
    if (feedback) {
        feedback.textContent = `Selected: ${file.name}`;
        feedback.className = 'file-feedback text-success small';
    }
}

// Form submission with loading state
function handleFormSubmission(event) {
    const form = event.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    
    if (submitBtn) {
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
        
        // Re-enable button after 10 seconds as fallback
        setTimeout(function() {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }, 10000);
    }
}

// Setup form validation
function setupFormValidation() {
    // Custom validation for password confirmation
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    passwordInputs.forEach(function(input) {
        if (input.name === 'confirm_password') {
            input.addEventListener('input', validatePasswordConfirmation);
        }
    });

    // Email validation
    const emailInputs = document.querySelectorAll('input[type="email"]');
    emailInputs.forEach(function(input) {
        input.addEventListener('blur', validateEmail);
    });

    // Phone number formatting
    const phoneInputs = document.querySelectorAll('input[type="tel"]');
    phoneInputs.forEach(function(input) {
        input.addEventListener('input', formatPhoneNumber);
    });
}

// Password confirmation validation
function validatePasswordConfirmation(event) {
    const confirmInput = event.target;
    const passwordInput = document.querySelector('input[name="password"]');
    
    if (!passwordInput) return;

    if (confirmInput.value !== passwordInput.value) {
        confirmInput.setCustomValidity('Passwords do not match');
        confirmInput.classList.add('is-invalid');
    } else {
        confirmInput.setCustomValidity('');
        confirmInput.classList.remove('is-invalid');
        confirmInput.classList.add('is-valid');
    }
}

// Email validation
function validateEmail(event) {
    const input = event.target;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    if (input.value && !emailRegex.test(input.value)) {
        input.classList.add('is-invalid');
        showTooltip(input, 'Please enter a valid email address');
    } else {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
    }
}

// Phone number formatting
function formatPhoneNumber(event) {
    const input = event.target;
    let value = input.value.replace(/\D/g, '');
    
    if (value.length >= 6) {
        value = value.replace(/(\d{3})(\d{3})(\d{4})/, '($1) $2-$3');
    } else if (value.length >= 3) {
        value = value.replace(/(\d{3})(\d{3})/, '($1) $2');
    }
    
    input.value = value;
}

// Search functionality
function handleSearch(input) {
    const searchTerm = input.value.toLowerCase();
    const searchableElements = document.querySelectorAll('[data-search]');
    
    searchableElements.forEach(function(element) {
        const searchData = element.getAttribute('data-search').toLowerCase();
        const isVisible = searchData.includes(searchTerm);
        
        element.style.display = isVisible ? '' : 'none';
    });
}

// Smooth scrolling
function handleSmoothScroll(event) {
    event.preventDefault();
    const targetId = this.getAttribute('href');
    const targetElement = document.querySelector(targetId);
    
    if (targetElement) {
        targetElement.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }
}

// Setup animations
function setupAnimations() {
    // Intersection Observer for fade-in animations
    if ('IntersectionObserver' in window) {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in');
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        // Observe elements with animation class
        const animatedElements = document.querySelectorAll('.animate-on-scroll');
        animatedElements.forEach(function(element) {
            observer.observe(element);
        });
    }
}

// Utility functions
function showAlert(message, type = 'info') {
    const alertContainer = document.querySelector('.alert-container') || document.body;
    const alertId = 'alert-' + Date.now();
    
    const alertHTML = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    alertContainer.insertAdjacentHTML('afterbegin', alertHTML);
    
    // Auto-remove after 5 seconds
    setTimeout(function() {
        const alertElement = document.getElementById(alertId);
        if (alertElement) {
            const bsAlert = new bootstrap.Alert(alertElement);
            bsAlert.close();
        }
    }, 5000);
}

function showTooltip(element, message) {
    const tooltip = new bootstrap.Tooltip(element, {
        title: message,
        trigger: 'manual'
    });
    
    tooltip.show();
    
    setTimeout(function() {
        tooltip.hide();
        tooltip.dispose();
    }, 3000);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function() {
            showAlert('Copied to clipboard!', 'success');
        });
    } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showAlert('Copied to clipboard!', 'success');
    }
}

// Rating system for candidate evaluation
function initializeRating(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const stars = container.querySelectorAll('.rating-star');
    const input = container.querySelector('input[type="hidden"]');
    
    stars.forEach(function(star, index) {
        star.addEventListener('click', function() {
            const rating = index + 1;
            input.value = rating;
            
            stars.forEach(function(s, i) {
                if (i < rating) {
                    s.classList.add('active');
                    s.innerHTML = '<i class="fas fa-star"></i>';
                } else {
                    s.classList.remove('active');
                    s.innerHTML = '<i class="far fa-star"></i>';
                }
            });
        });
        
        star.addEventListener('mouseenter', function() {
            const rating = index + 1;
            
            stars.forEach(function(s, i) {
                if (i < rating) {
                    s.style.color = '#ffc107';
                } else {
                    s.style.color = '#6c757d';
                }
            });
        });
    });
    
    container.addEventListener('mouseleave', function() {
        const currentRating = parseInt(input.value) || 0;
        
        stars.forEach(function(star, i) {
            if (i < currentRating) {
                star.style.color = '#ffc107';
            } else {
                star.style.color = '#6c757d';
            }
        });
    });
}

// Progress tracking for profile completion
function updateProfileProgress(completedFields, totalFields) {
    const percentage = Math.round((completedFields / totalFields) * 100);
    const progressBar = document.querySelector('.profile-progress .progress-bar');
    const progressText = document.querySelector('.profile-progress-text');
    
    if (progressBar) {
        progressBar.style.width = percentage + '%';
        progressBar.setAttribute('aria-valuenow', percentage);
    }
    
    if (progressText) {
        progressText.textContent = percentage + '%';
    }
}

// Lazy loading for images
function initializeLazyLoading() {
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver(function(entries, observer) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });

        const images = document.querySelectorAll('img[data-src]');
        images.forEach(function(img) {
            imageObserver.observe(img);
        });
    }
}

// Export functions for global access
window.JobPortal = {
    showAlert,
    showTooltip,
    formatFileSize,
    copyToClipboard,
    initializeRating,
    updateProfileProgress,
    initializeLazyLoading
};

// Handle page visibility changes
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        // Page is hidden - pause any timers or animations
        console.log('Page hidden');
    } else {
        // Page is visible - resume timers or animations
        console.log('Page visible');
    }
});

// Error handling for uncaught errors
window.addEventListener('error', function(event) {
    console.error('Uncaught error:', event.error);
    // Optionally show user-friendly error message
    showAlert('An unexpected error occurred. Please refresh the page.', 'danger');
});

// Performance monitoring
if ('performance' in window) {
    window.addEventListener('load', function() {
        setTimeout(function() {
            const perfData = window.performance.timing;
            const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
            console.log('Page load time:', pageLoadTime + 'ms');
        }, 0);
    });
}

// Service Worker registration for offline support (optional)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        // Uncomment to enable service worker
        // navigator.serviceWorker.register('/sw.js')
        //     .then(function(registration) {
        //         console.log('SW registered: ', registration);
        //     })
        //     .catch(function(registrationError) {
        //         console.log('SW registration failed: ', registrationError);
        //     });
    });
}
