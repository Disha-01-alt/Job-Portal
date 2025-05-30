// Job Portal - Main JavaScript File

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeComponents();
    setupEventListeners();
    setupFormValidation();
    setupAnimations();
    initializeLazyLoading(); // Moved lazy loading init here as it depends on DOM
    // Initialize other specific components if needed, e.g., rating
    // if (document.getElementById('candidate-rating-stars')) {
    //     JobPortal.initializeRating('candidate-rating-stars');
    // }
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
            // Check if the alert element still exists and has bootstrap alert instance
            if (alert && bootstrap.Alert.getInstance(alert)) {
                const bsAlert = bootstrap.Alert.getInstance(alert);
                bsAlert.close();
            } else if (alert && !bootstrap.Alert.getInstance(alert)) {
                // If no instance, try creating one then closing
                try {
                    const bsAlert = new bootstrap.Alert(alert);
                    bsAlert.close();
                } catch (e) {
                    // If creating an instance fails (e.g., element removed by other means)
                    // console.warn("Could not close alert:", e);
                }
            }
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
    // Selecting all <a> tags whose href starts with #
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    anchorLinks.forEach(function(link) {
        link.addEventListener('click', handleSmoothScroll); // Using the updated handleSmoothScroll
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
        input.value = ''; // Clear the input
        return;
    }

    // Check file type based on input accept attribute
    const acceptedTypes = input.accept.split(',').map(type => type.trim().toLowerCase());
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
    const mimeType = file.type.toLowerCase();

    // If accept attribute is empty, skip type validation (or add specific logic)
    if (input.accept) {
        const isValidType = acceptedTypes.some(type => {
            if (type.startsWith('.')) { // e.g., .pdf
                return fileExtension === type;
            } else if (type.includes('/')) { // e.g., image/jpeg or application/pdf
                if (type.endsWith('/*')) { // e.g., image/*
                    return mimeType.startsWith(type.slice(0, -2));
                }
                return mimeType === type;
            }
            return false; // Skip other unknown formats in accept
        });

        if (!isValidType) {
            showAlert('Invalid file type. Please check the allowed file formats.', 'danger');
            input.value = ''; // Clear the input
            return;
        }
    }


    // Visual feedback for successful upload selection
    const inputGroup = input.closest('.input-group') || input.parentElement;
    if (inputGroup) {
        let feedback = inputGroup.querySelector('.file-feedback');
        if (!feedback) { // Create feedback element if it doesn't exist
            feedback = document.createElement('div');
            feedback.className = 'file-feedback small';
            // Insert after the input, or at the end of the input group
            if (input.nextSibling) {
                inputGroup.insertBefore(feedback, input.nextSibling);
            } else {
                inputGroup.appendChild(feedback);
            }
        }
        feedback.textContent = `Selected: ${file.name}`;
        feedback.className = 'file-feedback text-success small mt-1';
    }
}

// Form submission with loading state
function handleFormSubmission(event) {
    const form = event.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    
    if (submitBtn && !submitBtn.classList.contains('no-loading')) { // Add 'no-loading' class to buttons to skip this
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
        
        // Re-enable button after 10 seconds as fallback
        // This is a general fallback; for AJAX forms, you'd re-enable on success/error
        setTimeout(function() {
            if (submitBtn.disabled) { // Only re-enable if still disabled
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }
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
            // Also validate on password input change
            const passwordField = document.querySelector('input[name="password"]');
            if (passwordField) {
                passwordField.addEventListener('input', () => validatePasswordConfirmation({target: input}));
            }
        }
    });

    // Email validation
    const emailInputs = document.querySelectorAll('input[type="email"]');
    emailInputs.forEach(function(input) {
        input.addEventListener('blur', validateEmail); // Validate on blur
        input.addEventListener('input', validateEmail); // Validate on input for immediate feedback if previously invalid
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
    // Ensure we get the password input relative to the current form, if possible
    const form = confirmInput.closest('form');
    const passwordInput = form ? form.querySelector('input[name="password"]') : document.querySelector('input[name="password"]');
    
    if (!passwordInput) return;

    if (passwordInput.value && confirmInput.value !== passwordInput.value) { // Only validate if password has a value
        confirmInput.setCustomValidity('Passwords do not match');
        confirmInput.classList.add('is-invalid');
        confirmInput.classList.remove('is-valid');
    } else {
        confirmInput.setCustomValidity('');
        confirmInput.classList.remove('is-invalid');
        if (confirmInput.value) { // Only add is-valid if there's content
             confirmInput.classList.add('is-valid');
        }
    }
}

// Email validation
function validateEmail(event) {
    const input = event.target;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    if (input.value && !emailRegex.test(input.value)) {
        input.classList.add('is-invalid');
        input.classList.remove('is-valid');
        // showTooltip(input, 'Please enter a valid email address'); // Tooltip might be annoying on input
    } else if (input.value) { // Only mark as valid if there's content and it's valid
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
    } else { // If empty, remove validation classes
        input.classList.remove('is-invalid');
        input.classList.remove('is-valid');
    }
}

// Phone number formatting
function formatPhoneNumber(event) {
    const input = event.target;
    let value = input.value.replace(/\D/g, ''); // Remove all non-digits
    
    // Simple US-style formatting (XXX) XXX-XXXX
    // You might want a more sophisticated library for international numbers
    if (value.length > 10) {
        value = value.substring(0, 10); // Max 10 digits
    }

    let formattedValue = "";
    if (value.length > 6) {
        formattedValue = `(${value.substring(0, 3)}) ${value.substring(3, 6)}-${value.substring(6)}`;
    } else if (value.length > 3) {
        formattedValue = `(${value.substring(0, 3)}) ${value.substring(3)}`;
    } else if (value.length > 0) {
        formattedValue = `(${value}`;
    }
    
    input.value = formattedValue;
}

// Search functionality
function handleSearch(input) {
    const searchTerm = input.value.toLowerCase().trim();
    // Assume searchable elements are siblings or within a common container that needs to be identified
    // This is a very generic search; you might need more specific logic
    const searchableContainer = input.closest('[data-search-container]') || document.body;
    const searchableElements = searchableContainer.querySelectorAll('[data-search-text]');
    
    searchableElements.forEach(function(element) {
        const searchData = element.getAttribute('data-search-text').toLowerCase();
        const isVisible = searchData.includes(searchTerm);
        
        // Find a common ancestor to hide (e.g., if element is a title inside a card, hide the card)
        const itemToToggle = element.closest('.searchable-item') || element; // Add 'searchable-item' class to the parent you want to hide/show
        itemToToggle.style.display = isVisible ? '' : 'none';
    });
}

// --- START OF UPDATED SMOOTH SCROLL FUNCTION ---
// Smooth scrolling
function handleSmoothScroll(event) {
    // 'this' refers to the clicked anchor element (<a>)
    const hrefAttribute = this.getAttribute('href');

    // 1. Check if the hrefAttribute is valid for smooth scrolling
    if (hrefAttribute && hrefAttribute.startsWith('#') && hrefAttribute.length > 1) {
        try {
            // 2. Try to find the target element
            const targetElement = document.querySelector(hrefAttribute);

            if (targetElement) {
                // 3. If target found, prevent default link behavior and scroll smoothly
                event.preventDefault();
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start' // Default block alignment
                });
            } else {
                // 4. Optional: Log a warning if the target element for a valid-looking selector wasn't found
                console.warn(`Smooth scroll: Target element not found for selector: ${hrefAttribute}`);
                // For non-existent targets, you might want to allow default behavior or still prevent it.
                // If you allow default, comment out the next line if you want the browser to try to jump.
                // event.preventDefault(); // Prevents jump if target not found (optional)
            }
        } catch (e) {
            // 5. Catch errors if querySelector fails (e.g., selector has invalid characters)
            console.error(`Smooth scroll: Invalid selector "${hrefAttribute}".`, e);
            event.preventDefault(); // Prevent default action for invalid selectors
        }
    } else if (hrefAttribute === '#') {
        // 6. Specifically handle href="#"
        event.preventDefault(); // Prevent the default jump-to-top behavior
        console.log("Smooth scroll: Clicked on href='#' link. Default action prevented.");
        // Optionally, smooth scroll to the top:
        // window.scrollTo({
        //     top: 0,
        //     behavior: 'smooth'
        // });
    }
    // If hrefAttribute is null, or doesn't start with '#', or is not handled above,
    // the click will just follow the link normally (default browser behavior) as event.preventDefault() was not called.
}
// --- END OF UPDATED SMOOTH SCROLL FUNCTION ---

// Setup animations
function setupAnimations() {
    // Intersection Observer for fade-in animations
    if ('IntersectionObserver' in window) {
        const observerOptions = {
            threshold: 0.1, // Trigger when 10% of the element is visible
            rootMargin: '0px 0px -50px 0px' // Trigger a bit before it's fully in viewport
        };

        const observer = new IntersectionObserver(function(entries, PIntersectionObserver) { // Renamed observer to PIntersectionObserver to avoid conflict
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in-visible'); // Use a class that makes it visible
                    PIntersectionObserver.unobserve(entry.target); // Stop observing once animated
                }
            });
        }, observerOptions);

        // Observe elements with animation class
        const animatedElements = document.querySelectorAll('.animate-on-scroll');
        animatedElements.forEach(function(element) {
            // Initially hide elements that will be animated
            element.classList.add('fade-in-hidden'); // Add a class to initially hide them
            observer.observe(element);
        });
    }
}

// Utility functions
function showAlert(message, type = 'info', duration = 5000) {
    const alertContainer = document.querySelector('#alert-container-main') || document.body; // Prefer a dedicated container
    const alertId = 'custom-alert-' + Date.now();
    
    const alertHTML = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert" style="position: fixed; top: 20px; right: 20px; z-index: 1055;">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    // Remove any existing alerts of the same type to avoid stacking too many
    // const existingAlert = alertContainer.querySelector(`.alert-${type}`);
    // if(existingAlert) new bootstrap.Alert(existingAlert).close();

    alertContainer.insertAdjacentHTML('beforeend', alertHTML); // Use beforend for fixed position alerts
    
    const alertElement = document.getElementById(alertId);
    if (!alertElement) return;

    // Auto-remove after specified duration
    if (duration > 0) {
        setTimeout(function() {
            if (document.getElementById(alertId)) { // Check if it still exists
                 const bsAlert = bootstrap.Alert.getInstance(alertElement) || new bootstrap.Alert(alertElement);
                 bsAlert.close();
            }
        }, duration);
    }
}

function showTooltip(element, message, duration = 3000) {
    const existingTooltip = bootstrap.Tooltip.getInstance(element);
    if (existingTooltip) {
        existingTooltip.dispose(); // Dispose existing to avoid conflicts
    }

    const tooltip = new bootstrap.Tooltip(element, {
        title: message,
        trigger: 'manual', // Important for programmatic show/hide
        placement: 'top'
    });
    
    tooltip.show();
    
    if (duration > 0) {
        setTimeout(function() {
            if (bootstrap.Tooltip.getInstance(element)) {
                bootstrap.Tooltip.getInstance(element).hide();
                // Dispose after hiding to clean up
                setTimeout(() => {
                     if (bootstrap.Tooltip.getInstance(element)) bootstrap.Tooltip.getInstance(element).dispose();
                }, 150); // Delay dispose slightly to allow hide animation
            }
        }, duration);
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    if (isNaN(parseFloat(bytes)) || !isFinite(bytes)) return 'N/A';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']; // Added TB
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) { // Clipboard API works in secure contexts (HTTPS)
        navigator.clipboard.writeText(text).then(function() {
            showAlert('Copied to clipboard!', 'success');
        }).catch(function(err) {
            console.error('Failed to copy text: ', err);
            showAlert('Failed to copy. Please try again.', 'danger');
        });
    } else {
        // Fallback for HTTP or older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed'; // Prevent scrolling to bottom of page
        textArea.style.left = '-9999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        try {
            const successful = document.execCommand('copy');
            if (successful) {
                showAlert('Copied to clipboard! (fallback)', 'success');
            } else {
                showAlert('Failed to copy using fallback.', 'danger');
            }
        } catch (err) {
            console.error('Fallback copy failed: ', err);
            showAlert('Failed to copy.', 'danger');
        }
        document.body.removeChild(textArea);
    }
}

// Rating system for candidate evaluation
function initializeRating(containerIdOrElement) {
    const container = (typeof containerIdOrElement === 'string') ? document.getElementById(containerIdOrElement) : containerIdOrElement;
    if (!container) {
        console.warn("Rating container not found:", containerIdOrElement);
        return;
    }

    const stars = container.querySelectorAll('.rating-star');
    const input = container.querySelector('input[type="hidden"][name="rating"], input[type="number"][name="rating"]'); // More specific input selector
    
    if (!input) {
        console.warn("Rating input not found in container:", containerIdOrElement);
        return;
    }
    if (stars.length === 0) {
        console.warn("No rating stars found in container:", containerIdOrElement);
        return;
    }

    function updateStars(ratingValue) {
        stars.forEach(function(s, i) {
            if (i < ratingValue) {
                s.classList.add('active');
                s.innerHTML = '<i class="fas fa-star"></i>'; // Solid star
            } else {
                s.classList.remove('active');
                s.innerHTML = '<i class="far fa-star"></i>'; // Outline star
            }
            s.style.color = (i < ratingValue) ? '#ffc107' : '#6c757d'; // Ensure color is set
        });
    }

    stars.forEach(function(star, index) {
        star.addEventListener('click', function() {
            const rating = index + 1;
            input.value = rating;
            updateStars(rating);
            // Dispatch a change event on the input for other listeners (e.g., form validation)
            input.dispatchEvent(new Event('change', { bubbles: true }));
        });
        
        star.addEventListener('mouseenter', function() {
            const hoverRating = index + 1;
            stars.forEach(function(s, i) {
                s.style.color = (i < hoverRating) ? '#ffc107' : '#e0e0e0'; // Lighter grey for unhovered
            });
        });
    });
    
    container.addEventListener('mouseleave', function() {
        const currentRating = parseInt(input.value) || 0;
        updateStars(currentRating); // Revert to actual selected rating
    });

    // Initialize stars based on current input value (e.g., if form is pre-filled)
    const initialRating = parseInt(input.value) || 0;
    updateStars(initialRating);
}

// Progress tracking for profile completion
function updateProfileProgress(completedFields, totalFields) {
    if (totalFields <= 0) return; // Avoid division by zero

    const percentage = Math.max(0, Math.min(100, Math.round((completedFields / totalFields) * 100)));
    const progressBar = document.querySelector('.profile-progress .progress-bar');
    const progressText = document.querySelector('.profile-progress-text');
    
    if (progressBar) {
        progressBar.style.width = percentage + '%';
        progressBar.setAttribute('aria-valuenow', percentage);
        progressBar.textContent = percentage + '%'; // Show percentage on bar if desired
    }
    
    if (progressText) {
        progressText.textContent = `Profile ${percentage}% complete`;
    }
}

// Lazy loading for images
function initializeLazyLoading() {
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver(function(entries, PIntersectionObserver) { // Renamed observer
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src'); // Remove data-src after loading
                        img.classList.add('loaded'); // Add class to indicate loaded
                    }
                    img.classList.remove('lazy'); // Original class if any
                    PIntersectionObserver.unobserve(img);
                }
            });
        }, { threshold: 0.01, rootMargin: "0px 0px 100px 0px" }); // Load a bit before visible

        const images = document.querySelectorAll('img[data-src]');
        images.forEach(function(img) {
            imageObserver.observe(img);
        });
    } else {
        // Fallback for browsers without IntersectionObserver (load all images)
        const images = document.querySelectorAll('img[data-src]');
        images.forEach(function(img) {
            if (img.dataset.src) {
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
                img.classList.add('loaded');
            }
            img.classList.remove('lazy');
        });
    }
}

// Export functions for global access if needed (consider modular approach for larger apps)
window.JobPortal = {
    showAlert,
    showTooltip,
    formatFileSize,
    copyToClipboard,
    initializeRating,
    updateProfileProgress
    // initializeLazyLoading is called internally, no need to export usually
};

// Handle page visibility changes
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        // Page is hidden - pause any timers or animations
        console.log('Page hidden - application might pause background tasks.');
    } else {
        // Page is visible - resume timers or animations
        console.log('Page visible - application resuming.');
    }
});

// Global error handling for uncaught errors
window.addEventListener('error', function(event) {
    console.error('Uncaught JavaScript error:', event.error, 'at', event.filename, event.lineno + ':' + event.colno);
    // Optionally show user-friendly error message
    // Avoid showing alerts for every minor JS error unless critical
    // showAlert('An unexpected error occurred. Please try refreshing the page or contact support if the issue persists.', 'danger', 0); // 0 for permanent
});

window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    // showAlert('An asynchronous operation failed. Please check your connection or try again.', 'warning');
});


// Performance monitoring (simple example)
if ('performance' in window && window.performance.timing) {
    window.addEventListener('load', function() {
        setTimeout(function() { // Use timeout to ensure all load events are fired
            const perfData = window.performance.timing;
            const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
            if (pageLoadTime > 0) {
                console.log('Page fully loaded in:', pageLoadTime + 'ms');
            }
            // You can send this data to an analytics service
        }, 0);
    });
}

// Service Worker registration for offline support (optional)
// Ensure sw.js is in the root of your web app
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        // Uncomment to enable service worker
        /*
        navigator.serviceWorker.register('/sw.js') // Path relative to origin
            .then(function(registration) {
                console.log('ServiceWorker registration successful with scope: ', registration.scope);
            })
            .catch(function(registrationError) {
                console.log('ServiceWorker registration failed: ', registrationError);
            });
        */
    });
}
