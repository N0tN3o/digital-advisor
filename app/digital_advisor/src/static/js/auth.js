// static/js/auth.js

document.addEventListener('DOMContentLoaded', () => {
    // Redirect if already logged in
    if (isAuthenticated()) {
        console.log('Already logged in, redirecting to dashboard');
        window.location.href = '/dashboard';
        return;
    }
    
    // Setup forms only if not logged in
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');

    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }

    if (registerForm) {
        registerForm.addEventListener('submit', handleRegistration);
    }
});

/**
 * Handles user login.
 * @param {Event} event The form submission event.
 */
async function handleLogin(event) {
    event.preventDefault();
    const email = document.getElementById('userName').value;
    const password = document.getElementById('userPassword').value;
    const authStatus = document.getElementById('authStatus');

    displayLoading(authStatus, 'Logging in...');

    try {
        const data = await apiPost('/auth/login', {
            username: email, // Backend expects username field
            password: password
        });

        displaySuccess(data.msg || 'Login successful!', authStatus);
        
        // Store the JWT token
        localStorage.setItem('access_token', data.access_token);
        
        // Get user profile data
        await fetchUserProfile();
        
        // Redirect to dashboard after a short delay
        setTimeout(() => {
            window.location.href = '/dashboard';
        }, 1000);
    } catch (error) {
        console.error('Login error:', error);
        displayError(error.message || 'An error occurred during login. Please try again.', authStatus);
    }
}

/**
 * Handles user registration.
 * @param {Event} event The form submission event.
 */
async function handleRegistration(event) {
    event.preventDefault();
    const username = document.getElementById('username').value;
    const email = document.getElementById('userEmail').value;
    const password = document.getElementById('userPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const agreeTerms = document.getElementById('agreeTerms').checked;
    const authStatus = document.getElementById('authStatus');

    displayLoading(authStatus, 'Registering...');

    if (password !== confirmPassword) {
        displayError('Passwords do not match.', authStatus);
        return;
    }
    if (!agreeTerms) {
        displayError('You must agree to the Terms of Service and Privacy Policy.', authStatus);
        return;
    }

    try {
        const data = await apiPost('/auth/register', {
            username: username,
            email: email,
            password: password
        });

        displaySuccess(data.msg || 'Registration successful! Redirecting to login...', authStatus);
        // Redirect to login page after a short delay
        setTimeout(() => {
            window.location.href = '/login';
        }, 1500);
    } catch (error) {
        console.error('Registration error:', error);
        let errorMessage = error.message || 'An error occurred during registration. Please try again.';
        if (error.errors) {
            // Display validation errors
            const errorMessages = Object.values(error.errors).flat();
            errorMessage += ' ' + errorMessages.join(' ');
        }
        displayError(errorMessage, authStatus);
    }
}

/**
 * Fetches user profile data after login
 */
async function fetchUserProfile() {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    try {
        const userData = await apiGet('/auth/me'); // Using the common apiGet utility
        const userForStorage = {
            user_id: userData.user_id || userData.id,
            username: userData.username,
            email: userData.email,
            balance: userData.balance || 10000.00,
            totalTrades: 0,
            portfolioValue: 0.00,
            totalGains: 0.00,
            activePredictions: 0,
            portfolio: []
        };
        sessionStorage.setItem('loggedInUser', JSON.stringify(userForStorage));
    } catch (error) {
        console.error('Error fetching user profile:', error);
        // Error handling for fetchUserProfile is handled by apiGet,
        // which will redirect to login if 401. Other errors are logged.
    }
}
