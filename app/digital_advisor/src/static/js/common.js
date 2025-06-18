// static/js/common.js

/**
 * Opens a modal specified by its ID.
 * @param {string} modalId The ID of the modal to open.
 */
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        document.visibilityState = 'hidden';
        modal.style.visibility = 'visible'; // Ensure modal is visible
    }
}

/**
 * Closes a modal specified by its ID.
 * @param {string} modalId The ID of the modal to close.
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
}

// Global event listener for clicking outside the modal content to close it
window.addEventListener('click', (event) => {
    if (event.target.classList.contains('modal-overlay')) {
        closeModal(event.target.id);
    }
});

// API utilities
const API_BASE_URL = ''; // Empty since we're on the same domain

/**
 * Makes an authenticated API request
 * @param {string} endpoint The API endpoint
 * @param {Object} options Fetch options
 * @returns {Promise<Response>}
 */
async function apiRequest(endpoint, options = {}) {
    const token = localStorage.getItem('access_token');
    
    const defaultHeaders = {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
    };

    const mergedOptions = {
        ...options,
        headers: {
            ...defaultHeaders,
            ...options.headers
        }
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, mergedOptions);
    
    // Handle token expiration
    if (response.status === 401) {
        console.log('Authentication failed (401), performing silent logout and redirecting.');
        alert('Your session has expired. Please log in again.');
        silentLogout(); // Redirects to login
        throw new Error('Authentication failed');
    }
    
    return response;
}

/**
 * Makes a GET request to the API
 * @param {string} endpoint The API endpoint
 * @returns {Promise<any>}
 */
async function apiGet(endpoint) {
    const response = await apiRequest(endpoint, { method: 'GET' });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({})); // Try to parse error body
        throw new Error(errorData.msg || `API Error: ${response.status} for ${endpoint}`);
    }
    return response.json();
}

/**
 * Makes a POST request to the API
 * @param {string} endpoint The API endpoint
 * @param {Object} data The data to send
 * @returns {Promise<any>}
 */
async function apiPost(endpoint, data) {
    const response = await apiRequest(endpoint, {
        method: 'POST',
        body: JSON.stringify(data)
    });
    
    const responseData = await response.json();
    
    if (!response.ok) {
        throw new Error(responseData.msg || `API Error: ${response.status} for ${endpoint}`);
    }
    
    return responseData;
}

/**
 * Makes a PUT request to the API
 * @param {string} endpoint The API endpoint
 * @param {Object} data The data to send
 * @returns {Promise<any>}
 */
async function apiPut(endpoint, data) {
    const response = await apiRequest(endpoint, {
        method: 'PUT',
        body: JSON.stringify(data)
    });
    
    const responseData = await response.json();
    
    if (!response.ok) {
        throw new Error(responseData.msg || `API Error: ${response.status} for ${endpoint}`);
    }
    
    return responseData;
}

/**
 * Makes a DELETE request to the API
 * @param {string} endpoint The API endpoint
 * @returns {Promise<any>}
 */
async function apiDelete(endpoint) {
    const response = await apiRequest(endpoint, { method: 'DELETE' });
    
    if (!response.ok) {
        const responseData = await response.json().catch(() => ({}));
        throw new Error(responseData.msg || `API Error: ${response.status} for ${endpoint}`);
    }
    
    return response.status === 204 ? null : response.json();
}

/**
 * Checks if user is authenticated by verifying token validity.
 * @returns {boolean}
 */
function isAuthenticated() {
    const token = localStorage.getItem('access_token');
    if (!token) return false;
    
    // Basic token expiration check
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const currentTime = Math.floor(Date.now() / 1000);
        
        if (payload.exp && payload.exp < currentTime) {
            console.log('Token expired, auto-logout');
            silentLogout();
            return false;
        }
        return true;
    } catch (error) {
        console.error('Error parsing token:', error);
        return false; // Treat invalid token as unauthenticated
    }
}

/**
 * Redirects to login if not authenticated
 */
function requireAuth() {
    const currentPath = window.location.pathname;
    if (currentPath === '/' || currentPath.includes('index')) {
        //no auth needed
        return;
        }
    if (!isAuthenticated()) {
        console.log('User not authenticated, redirecting to login');
        window.location.href = '/login';
    }
}

/**
 * Gets the current user data from session storage
 * @returns {Object|null}
 */
function getCurrentUser() {
    const userData = sessionStorage.getItem('loggedInUser');
    return userData ? JSON.parse(userData) : null;
}

/**
 * Updates current user data in session storage
 * @param {Object} userData
 */
function updateCurrentUser(userData) {
    sessionStorage.setItem('loggedInUser', JSON.stringify(userData));
}

/**
 * Display error message in a user-friendly way using a modal.
 * @param {string} message Error message to display.
 * @param {HTMLElement} [container] Optional container element to show error in.
 * If not provided, a global message modal is used.
 */
function displayError(message, container) {
    if (container) {
        container.innerHTML = `<p class="form-status-message error">${message}</p>`;
        container.classList.add('error-message'); // Add class for styling
    } else {
        // Fallback to a generic message modal if no container is provided
        const globalMessageContent = document.getElementById('globalMessageContent');
        if (globalMessageContent) {
            globalMessageContent.innerHTML = `<p class="text-red-600 text-lg font-semibold">${message}</p>`;
            openModal('global-message-modal');
        } else {
            console.error('Error: ' + message);
        }
    }
}

/**
 * Display success message in a user-friendly way using a modal.
 * @param {string} message Success message to display.
 * @param {HTMLElement} [container] Optional container element to show message in.
 * If not provided, a global message modal is used.
 */
function displaySuccess(message, container) {
    if (container) {
        container.innerHTML = `<p class="form-status-message success">${message}</p>`;
        container.classList.add('success-message'); // Add class for styling
    } else {
        const globalMessageContent = document.getElementById('globalMessageContent');
        if (globalMessageContent) {
            globalMessageContent.innerHTML = `<p class="text-green-600 text-lg font-semibold">${message}</p>`;
            openModal('global-message-modal');
        } else {
            console.log('Success: ' + message);
        }
    }
}

/**
 * Display loading message
 * @param {HTMLElement} container Container element to show loading in
 * @param {string} message Loading message
 */
function displayLoading(container, message = 'Loading...') {
    if (container) {
        container.innerHTML = `<p style="text-align: center; color: #6c757d;">${message}</p>`;
        container.classList.remove('error-message', 'success-message'); // Remove status classes
    }
}

/**
 * Load prices for tickers using the /prices API.
 * This function is now centralized in common.js.
 * @param {Array<string>} tickers - An array of stock ticker symbols.
 * @returns {Promise<Object>} A promise that resolves to an object mapping tickers to their prices.
 */
async function loadPricesForTickers(tickers) {
    if (!tickers || tickers.length === 0) return {};
    
    try {
        const tickerParam = tickers.join(',');
        console.log(`Loading prices for: ${tickerParam}`);
        
        const prices = await apiGet(`/prices?tickers=${tickerParam}`);
        console.log('Loaded prices:', prices);
        
        // Assuming priceCache is a global or passed variable in modules that use this
        // For now, if called from a page, it's expected to update the page's cache.
        // This function primarily fetches prices, not manages global cache directly in common.js.
        return prices;
    } catch (error) {
        console.error('Error loading prices:', error);
        // It's up to the calling function (e.g., dashboard.js or profile.js) to display an error to the user.
        return {};
    }
}

/**
 * Handle redirects based on auth status
 */
async function handleAuthRedirect() {
    const currentPath = window.location.pathname;
    console.log('Checking auth for path:', currentPath);
    
    if (isAuthenticated()) {
        // If on login/register pages, redirect to dashboard
        if (currentPath.includes('login') || currentPath.includes('register')) {
            console.log('Already logged in, redirecting to dashboard');
            window.location.href = '/dashboard';
            return;
        }
        
        // If on homepage, show logged-in options
        if (currentPath === '/' || currentPath.includes('index')) {
            showLoggedInOptions();
        }
    } else {
        // If trying to access dashboard, redirect to login
        if (currentPath.includes('dashboard') || currentPath.includes('profile')) {
            console.log('Not authenticated, redirecting to login');
            window.location.href = '/login';
            return;
        }
    }
}

function showLoggedInOptions() {
    // Check if banner already exists on the page
    if (document.getElementById('logged-in-banner')) {
        return;
    }

    // Check if the banner has already been shown in this session
    if (sessionStorage.getItem('loggedInBannerDismissed')) {
        return;
    }
    
    // Get user info for personalized message
    let userName = 'User';
    try {
        const userData = sessionStorage.getItem('loggedInUser');
        if (userData) {
            const user = JSON.parse(userData);
            userName = user.username || 'User';
        }
    } catch (error) {
        console.log('Could not get username for banner');
    }
    
    const banner = document.createElement('div');
    banner.id = 'logged-in-banner';
    // Use your custom CSS for this class
    banner.className = 'logged-in-banner'; 
    banner.innerHTML = `
        <div class="banner-content">
            <p>Welcome back, ${userName}! You're already logged in.</p>
            <div class="banner-actions">
                <a href="/dashboard" class="btn btn-primary">Go to Dashboard</a>
                <button onclick="logoutUser()" class="btn btn-outline">Logout</button>
                <button id="dismissLoggedInBanner" class="btn btn-secondary">Dismiss</button>
            </div>
        </div>
    `;
    
    const main = document.querySelector('main') || document.body;
    main.insertBefore(banner, main.firstChild);

    // Add event listener for the dismiss button
    document.getElementById('dismissLoggedInBanner')?.addEventListener('click', () => {
        banner.style.display = 'none';
        sessionStorage.setItem('loggedInBannerDismissed', 'true'); // Mark as dismissed for this session
    });
}

// Run auth check on every page load
document.addEventListener('DOMContentLoaded', handleAuthRedirect);

/**
 * Global logout function - works on all pages
 */
function logoutUser() {
    try {
        console.log('Logging out user...');
        
        // Clear all authentication data
        localStorage.removeItem('access_token');
        sessionStorage.removeItem('loggedInUser');
        
        // Clear any cached data
        // priceCache is global to dashboard.js, so access it via window if needed
        if (typeof window.priceCache !== 'undefined') {
            window.priceCache = {};
        }

        // Clear the session dismissal flag for the banner so it shows on next login
        sessionStorage.removeItem('loggedInBannerDismissed');
        
        // Show confirmation message using the modal and then redirect
        const globalMessageContent = document.getElementById('globalMessageContent');
        if (globalMessageContent) {
            globalMessageContent.innerHTML = '<p class="text-green-600 text-lg font-semibold">You have been logged out.</p>';
            openModal('global-message-modal');
            setTimeout(() => {
                closeModal('global-message-modal');
                window.location.href = '/login';
            }, 1500); // Give user time to read message
        } else {
            window.location.href = '/login'; // Fallback redirect
        }
        
    } catch (error) {
        console.error('Error during logout:', error);
        // Force clear and redirect anyway
        localStorage.clear();
        sessionStorage.clear();
        window.location.href = '/login';
    }
}

/**
 * Silent logout (no alert) - useful for expired tokens
 */
function silentLogout() {
    console.log('Silent logout - clearing auth data and redirecting to login.');
    localStorage.removeItem('access_token');
    sessionStorage.removeItem('loggedInUser');
    sessionStorage.removeItem('loggedInBannerDismissed'); // Clear dismissal flag on silent logout too
    window.location.href = '/login';
}

// Global Message Modal structure (to be added to your HTML layout)
/*
<div id="global-message-modal" class="modal-overlay hidden fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="modal-content bg-white p-8 rounded-lg shadow-xl max-w-sm w-full mx-4 text-center">
        <div id="globalMessageContent" class="mb-4"></div>
        <button onclick="closeModal('global-message-modal')" class="btn bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded-lg">OK</button>
    </div>
</div>
*/
