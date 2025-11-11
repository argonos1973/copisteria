/* ==========================================
   ALEPH70 - Main JavaScript
   ========================================== */

// DOM Elements
const loader = document.getElementById('loader');
const navbar = document.getElementById('navbar');
const navMenu = document.getElementById('navMenu');
const hamburger = document.getElementById('hamburger');
const registerModal = document.getElementById('registerModal');
const successModal = document.getElementById('successModal');
const registerForm = document.getElementById('registerForm');
const contactForm = document.getElementById('contactForm');

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    // Hide loader
    setTimeout(() => {
        loader.classList.add('hidden');
    }, 500);
    
    // Initialize animations
    initAnimations();
    
    // Initialize event listeners
    initEventListeners();
    
    // Initialize smooth scroll
    initSmoothScroll();
    
    // Initialize form validation
    initFormValidation();
});

// Event Listeners
function initEventListeners() {
    // Navbar scroll effect
    window.addEventListener('scroll', handleNavScroll);
    
    // Mobile menu toggle
    hamburger.addEventListener('click', toggleMobileMenu);
    
    // Close mobile menu on link click
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            navMenu.classList.remove('active');
            resetHamburger();
        });
    });
    
    // Register form submission
    registerForm.addEventListener('submit', handleRegistration);
    
    // Contact form submission
    contactForm.addEventListener('submit', handleContactForm);
    
    // Close modal on outside click
    window.addEventListener('click', (e) => {
        if (e.target === registerModal) {
            closeRegisterModal();
        }
        if (e.target === successModal) {
            closeSuccessModal();
        }
    });
}

// Navbar scroll handler
function handleNavScroll() {
    if (window.scrollY > 50) {
        navbar.classList.add('scrolled');
    } else {
        navbar.classList.remove('scrolled');
    }
}

// Mobile menu toggle
function toggleMobileMenu() {
    navMenu.classList.toggle('active');
    hamburger.classList.toggle('active');
    
    // Animate hamburger bars
    const bars = hamburger.querySelectorAll('.bar');
    if (hamburger.classList.contains('active')) {
        bars[0].style.transform = 'rotate(-45deg) translate(-5px, 6px)';
        bars[1].style.opacity = '0';
        bars[2].style.transform = 'rotate(45deg) translate(-5px, -6px)';
    } else {
        resetHamburger();
    }
}

function resetHamburger() {
    const bars = hamburger.querySelectorAll('.bar');
    bars[0].style.transform = '';
    bars[1].style.opacity = '1';
    bars[2].style.transform = '';
}

// Smooth scroll
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Modal functions
function openRegisterModal() {
    registerModal.classList.add('show');
    document.body.style.overflow = 'hidden';
}

function closeRegisterModal() {
    registerModal.classList.remove('show');
    document.body.style.overflow = '';
    registerForm.reset();
}

function openSuccessModal() {
    successModal.classList.add('show');
}

function closeSuccessModal() {
    successModal.classList.remove('show');
}

// Form validation
function initFormValidation() {
    // Add real-time validation
    const inputs = document.querySelectorAll('input[required]');
    inputs.forEach(input => {
        input.addEventListener('blur', validateField);
        input.addEventListener('input', () => {
            if (input.classList.contains('error')) {
                validateField.call(input);
            }
        });
    });
}

function validateField() {
    const field = this;
    const value = field.value.trim();
    
    // Remove previous error
    field.classList.remove('error');
    
    // Check if empty
    if (!value) {
        showError(field, 'Este campo es obligatorio');
        return false;
    }
    
    // Email validation
    if (field.type === 'email') {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
            showError(field, 'Email inválido');
            return false;
        }
    }
    
    // Phone validation
    if (field.type === 'tel') {
        const phoneRegex = /^[0-9+\-\s()]+$/;
        if (!phoneRegex.test(value)) {
            showError(field, 'Teléfono inválido');
            return false;
        }
    }
    
    // Password validation
    if (field.type === 'password') {
        if (value.length < 6) {
            showError(field, 'Mínimo 6 caracteres');
            return false;
        }
    }
    
    return true;
}

function showError(field, message) {
    field.classList.add('error');
    
    // Create or update error message
    let errorEl = field.parentElement.querySelector('.error-message');
    if (!errorEl) {
        errorEl = document.createElement('div');
        errorEl.className = 'error-message';
        field.parentElement.appendChild(errorEl);
    }
    errorEl.textContent = message;
}

// Registration handler
async function handleRegistration(e) {
    e.preventDefault();
    
    // Get form data
    const formData = {
        name: document.getElementById('regName').value,
        surname: document.getElementById('regSurname').value,
        company: document.getElementById('regCompany').value,
        email: document.getElementById('regEmail').value,
        phone: document.getElementById('regPhone').value,
        password: document.getElementById('regPassword').value,
        passwordConfirm: document.getElementById('regPasswordConfirm').value
    };
    
    // Validate passwords match
    if (formData.password !== formData.passwordConfirm) {
        showError(document.getElementById('regPasswordConfirm'), 'Las contraseñas no coinciden');
        return;
    }
    
    // Check terms
    if (!document.getElementById('regTerms').checked) {
        alert('Debes aceptar los términos y condiciones');
        return;
    }
    
    // Show loading state
    const submitBtn = registerForm.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creando cuenta...';
    submitBtn.disabled = true;
    
    try {
        // Send registration request
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            // Success
            closeRegisterModal();
            openSuccessModal();
        } else {
            // Error
            alert(result.error || 'Error al crear la cuenta');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error de conexión. Por favor, intenta de nuevo.');
    } finally {
        // Reset button
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
}

// Contact form handler
async function handleContactForm(e) {
    e.preventDefault();
    
    const formData = new FormData(contactForm);
    const submitBtn = contactForm.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    
    // Show loading state
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enviando...';
    submitBtn.disabled = true;
    
    try {
        const response = await fetch('/api/contact', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            alert('Mensaje enviado correctamente. Te contactaremos pronto.');
            contactForm.reset();
        } else {
            alert('Error al enviar el mensaje. Por favor, intenta de nuevo.');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error de conexión. Por favor, intenta de nuevo.');
    } finally {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
}

// Screenshot carousel
let currentScreenshot = 0;
const screenshots = document.querySelectorAll('.screenshot-item');

function changeScreenshot(direction) {
    screenshots[currentScreenshot].classList.remove('active');
    currentScreenshot = (currentScreenshot + direction + screenshots.length) % screenshots.length;
    screenshots[currentScreenshot].classList.add('active');
}

// Auto-rotate screenshots
setInterval(() => {
    changeScreenshot(1);
}, 5000);

// Plan selection
function selectPlan(plan) {
    // Store selected plan
    localStorage.setItem('selectedPlan', plan);
    
    // Open registration modal
    openRegisterModal();
    
    // Pre-select plan in form (if you add a plan selector)
    const planInput = document.getElementById('regPlan');
    if (planInput) {
        planInput.value = plan;
    }
}

// Animation initialization
function initAnimations() {
    // Reveal on scroll
    const reveals = document.querySelectorAll('.reveal');
    
    function revealOnScroll() {
        reveals.forEach(element => {
            const elementTop = element.getBoundingClientRect().top;
            const elementVisible = 150;
            
            if (elementTop < window.innerHeight - elementVisible) {
                element.classList.add('active');
            }
        });
    }
    
    window.addEventListener('scroll', revealOnScroll);
    revealOnScroll(); // Check on load
    
    // Parallax effect
    const parallaxElements = document.querySelectorAll('.parallax');
    
    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        
        parallaxElements.forEach(element => {
            const speed = element.dataset.speed || 0.5;
            const yPos = -(scrolled * speed);
            element.style.transform = `translateY(${yPos}px)`;
        });
    });
    
    // Number counter animation
    const counters = document.querySelectorAll('.stat-number');
    
    counters.forEach(counter => {
        const updateCount = () => {
            const target = parseInt(counter.innerText);
            let count = 0;
            const increment = target / 100;
            
            const timer = setInterval(() => {
                if (count < target) {
                    counter.innerText = Math.ceil(count + increment);
                    count += increment;
                } else {
                    counter.innerText = target + '+';
                    clearInterval(timer);
                }
            }, 20);
        };
        
        // Trigger on scroll
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    updateCount();
                    observer.unobserve(entry.target);
                }
            });
        });
        
        observer.observe(counter);
    });
}

// Add input error styles
const style = document.createElement('style');
style.textContent = `
    input.error {
        border-color: #e74c3c !important;
    }
    .error-message {
        color: #e74c3c;
        font-size: 0.875rem;
        margin-top: 0.25rem;
    }
`;
document.head.appendChild(style);

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Performance optimization
const debouncedScroll = debounce(() => {
    handleNavScroll();
}, 10);

window.addEventListener('scroll', debouncedScroll);
