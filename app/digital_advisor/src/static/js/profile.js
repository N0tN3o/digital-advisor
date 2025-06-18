// static/js/profile.js

// Global variables for profile page
let currentUser = {
    user_id: null,
    username: 'Guest',
    email: 'N/A',
    balance: 0.00,
    totalTrades: 0,
    portfolioValue: 0.00,
    totalGains: 0.00,
    totalGainsPercent: 0.00,
    activePredictions: 0,
    portfolio: [],
    isLoaded: false,
    lastUpdated: null
};

document.addEventListener('DOMContentLoaded', async () => {
    // checkAuthStatus is handled by common.js's DOMContentLoaded listener.
    // If we reach here, it means the user is authenticated.

    // Load profile data
    await loadProfileData();
    
    // Setup event listeners
    setupProfileEventListeners();
});

/**
 * Check authentication status for profile page
 * (This function is largely redundant now due to handleAuthRedirect in common.js,
 * but kept for explicit clarity within this file's context if needed for other checks).
 */
async function checkAuthStatus() {
    if (!isAuthenticated()) { // isAuthenticated from common.js
        console.log('Not authenticated, redirecting to login');
        window.location.href = '/login';
        return false;
    }
    return true;
}

/**
 * Load all profile data
 */
async function loadProfileData() {
    try {
        console.log('Loading profile data...');
        
        // Load user data from /auth/me
        await loadUserData();
        
        // Load portfolio data
        await loadPortfolioSummary();
        
        // Update all displays
        updateProfileDisplay();
        
        console.log('Profile data loaded successfully');
    } catch (error) {
        console.error('Error loading profile data:', error);
        displayError(error.message || 'Failed to load profile data.');
    }
}

/**
 * Load user data from /auth/me API
 */
async function loadUserData() {
    try {
        const userData = await apiGet('/auth/me'); // Using apiGet from common.js
        console.log('User data loaded:', userData);

        // Update currentUser with real data
        Object.assign(currentUser, {
            user_id: userData.user_id || userData.id,
            username: userData.username,
            email: userData.email,
            balance: Number(userData.balance) || 0,
            lastUpdated: new Date(),
            isLoaded: true
        });

        // Save to session storage
        sessionStorage.setItem('loggedInUser', JSON.stringify(currentUser));
        
    } catch (error) {
        console.error('Error loading user data:', error);
        displayError(error.message || 'Failed to load user account details.');
        // Fallback to session storage if API fails
        const storedUser = sessionStorage.getItem('loggedInUser');
        if (storedUser) {
            try {
                const parsedUser = JSON.parse(storedUser);
                Object.assign(currentUser, parsedUser);
            } catch (e) {
                console.error("Error parsing cached user data:", e);
            }
        }
    }
}

/**
 * Load portfolio summary data from /portfolio API
 */
async function loadPortfolioSummary() {
    try {
        const portfolioData = await apiGet('/portfolio'); // Using apiGet from common.js
        const portfolio = portfolioData.holdings || [];
        const cashBalance = portfolioData.cash_balance || 0;

        // Update portfolio stats
        currentUser.portfolio = portfolio;
        currentUser.balance = cashBalance; // Ensure balance is updated from portfolio endpoint if it's the most current source
        
        // Calculate portfolio value and P&L
        if (portfolio.length > 0) {
            let totalValue = 0;
            // For totalCost, we would need the average purchase price for each holding.
            // If API doesn't provide it, we'll use current price as a proxy for simplicity.
            let totalCostBasis = 0; 

            // Fetch current prices for all portfolio tickers to calculate real-time value
            const tickersInPortfolio = [...new Set(portfolio.map(item => item.ticker))];
            const currentPrices = await loadPricesForTickers(tickersInPortfolio); // Use loadPricesForTickers from dashboard.js/common.js

            portfolio.forEach(item => {
                const volume = item.volume || 0;
                const purchasePrice = item.purchase_price || item.price || 0; // Use actual purchase_price if available
                const currentPrice = currentPrices[item.ticker] || purchasePrice; // Fallback to purchase price if current not found
                
                totalValue += volume * currentPrice;
                totalCostBasis += volume * purchasePrice;
            });
            
            currentUser.portfolioValue = totalValue;
            currentUser.totalGains = totalValue - totalCostBasis;
            currentUser.totalGainsPercent = totalCostBasis > 0 ? ((totalValue - totalCostBasis) / totalCostBasis * 100) : 0;
        } else {
            currentUser.portfolioValue = 0.00;
            currentUser.totalGains = 0.00;
            currentUser.totalGainsPercent = 0.00;
        }
        // Update totalTrades and activePredictions if your /portfolio or /auth/me API returns them
        // For now, assuming they are tracked elsewhere or initialized to 0.
        
    } catch (error) {
        console.error('Error loading portfolio summary:', error);
        displayError(error.message || 'Failed to load portfolio summary.');
    }
}

/**
 * Update all profile displays
 */
function updateProfileDisplay() {
    try {
        // Header (assuming elements with these IDs exist in your common header or main layout)
        updateElement('currentUsername', `Welcome, ${currentUser.username}!`);
        updateElement('currentBalance', currentUser.balance.toFixed(2));
        
        // Profile header
        updateElement('profileDisplayUsername', currentUser.username);
        updateElement('profileDisplayEmail', currentUser.email);
        
        // Account information
        updateElement('displayUsername', currentUser.username);
        updateElement('displayEmail', currentUser.email);
        
        // Financial information
        updateElement('displayBalance', `$${currentUser.balance.toFixed(2)}`);
        updateElement('currentPortfolioValue', `$${currentUser.portfolioValue.toFixed(2)}`);
        
        // Update P&L with color coding
        const plElement = document.getElementById('totalProfitLoss');
        if (plElement) {
            const totalGains = currentUser.totalGains || 0;
            plElement.textContent = `${totalGains >= 0 ? '+' : ''}$${totalGains.toFixed(2)}`;
            plElement.className = `pl-amount ${totalGains >= 0 ? 'text-green-600' : 'text-red-600'} font-bold`; // Tailwind classes
        }
        
        const plPercentElement = document.getElementById('totalProfitLossPercent');
        if (plPercentElement) {
            const gainsPercent = currentUser.totalGainsPercent || 0;
            plPercentElement.textContent = `${gainsPercent >= 0 ? '+' : ''}${gainsPercent.toFixed(2)}%`;
            plPercentElement.className = `pl-amount ${gainsPercent >= 0 ? 'text-green-600' : 'text-red-600'} font-bold`; // Tailwind classes
        }
        
        // Trading statistics
        updateElement('totalTradesCount', currentUser.totalTrades || 0);
        updateElement('activePredictionsCount', currentUser.activePredictions || 0);
        updateElement('portfolioItemsCount', currentUser.portfolio.length || 0);
        updateElement('totalInvestmentCount', `$${currentUser.portfolioValue.toFixed(0)}`);
        
        // Last updated
        if (currentUser.lastUpdated) {
            updateElement('lastUpdatedTime', new Date(currentUser.lastUpdated).toLocaleString());
        }
        
        console.log('Profile display updated');
        
    } catch (error) {
        console.error('Error updating profile display:', error);
    }
}

/**
 * Helper function to safely update DOM elements
 */
function updateElement(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value;
    } else {
        // console.warn(`Element with ID '${elementId}' not found`);
    }
}

/**
 * Setup event listeners for profile page
 */
function setupProfileEventListeners() {
    document.getElementById('refreshProfileButton')?.addEventListener('click', refreshUserProfile);
    document.getElementById('refreshAllDataButton')?.addEventListener('click', refreshAllData);
    document.getElementById('saveSettingsButton')?.addEventListener('click', saveSettings);
    document.getElementById('depositButton')?.addEventListener('click', handleDeposit);
    document.getElementById('withdrawButton')?.addEventListener('click', handleWithdraw);
    document.getElementById('openEditProfileModalButton')?.addEventListener('click', openEditProfileModal);
    document.getElementById('exportPortfolioButton')?.addEventListener('click', exportPortfolio);

    // Modal specific buttons
    document.getElementById('confirmDepositButton')?.addEventListener('click', handleDeposit);
    document.getElementById('confirmWithdrawButton')?.addEventListener('click', handleWithdraw);
    document.getElementById('saveProfileChangesButton')?.addEventListener('click', saveProfileChanges);

    // Modal close buttons
    document.querySelectorAll('.close-button').forEach(button => {
        button.addEventListener('click', (event) => {
            const modalId = event.target.closest('.modal-overlay').id;
            closeModal(modalId);
        });
    });
    console.log('Profile event listeners setup');
}

/**
 * Refresh user profile data
 */
async function refreshUserProfile() {
    console.log('Refreshing user profile...');
    await loadProfileData();
    displaySuccess('Profile data refreshed!'); // Using common.js displaySuccess
}

/**
 * Refresh all data (calls loadProfileData which in turn calls loadUserData and loadPortfolioSummary)
 */
async function refreshAllData() {
    console.log('Refreshing all profile data...');
    await loadProfileData();
    displaySuccess('All data refreshed successfully!'); // Using common.js displaySuccess
}

/**
 * Save settings (mock functionality for now)
 */
function saveSettings() {
    // Get setting values
    const emailNotifications = document.getElementById('emailNotifications')?.checked;
    const twoFactorAuth = document.getElementById('twoFactorAuth')?.checked;
    const tradingAlerts = document.getElementById('tradingAlerts')?.checked;
    
    console.log('Saving settings:', {
        emailNotifications,
        twoFactorAuth,
        tradingAlerts
    });
    
    // TODO: Implement actual API call to save settings
    displaySuccess('Settings saved! (Feature coming soon)'); // Using common.js displaySuccess
}

/**
 * Handle deposit using /balance/deposit API
 */
async function handleDeposit() {
    const amountInput = document.getElementById('depositAmount');
    const status = document.getElementById('depositStatus');
    
    const amount = parseFloat(amountInput.value);
    
    if (isNaN(amount) || amount <= 0) {
        displayError('Please enter a valid amount greater than 0', status);
        return;
    }
    
    displayLoading(status, 'Processing deposit...');
    
    try {
        const result = await apiPost('/balance/deposit', { amount: amount }); // Using apiPost
        
        displaySuccess(result.msg || `Successfully deposited $${amount.toFixed(2)}`, status);
        amountInput.value = '';
        
        // Refresh profile data to show updated balance
        await loadProfileData();
        
        setTimeout(() => {
            closeModal('deposit-modal');
            status.textContent = ''; // Clear status after closing
        }, 1500);
    } catch (error) {
        console.error('Deposit error:', error);
        displayError(error.message || 'An error occurred during deposit. Please try again.', status);
    }
}

/**
 * Handle withdrawal using /balance/withdraw API
 */
async function handleWithdraw() {
    const amountInput = document.getElementById('withdrawAmount');
    const status = document.getElementById('withdrawStatus');
    
    const amount = parseFloat(amountInput.value);
    
    if (isNaN(amount) || amount <= 0) {
        displayError('Please enter a valid amount greater than 0', status);
        return;
    }
    
    if (amount > currentUser.balance) {
        displayError('Insufficient balance', status);
        return;
    }
    
    displayLoading(status, 'Processing withdrawal...');
    
    try {
        const result = await apiPost('/balance/withdraw', { amount: amount }); // Using apiPost
        
        displaySuccess(result.msg || `Successfully withdrew $${amount.toFixed(2)}`, status);
        amountInput.value = '';
        
        // Refresh profile data to show updated balance
        await loadProfileData();
        
        setTimeout(() => {
            closeModal('withdraw-modal');
            status.textContent = ''; // Clear status after closing
        }, 1500);
    } catch (error) {
        console.error('Withdrawal error:', error);
        displayError(error.message || 'An error occurred during withdrawal. Please try again.', status);
    }
}

/**
 * Open withdraw modal and update balance display
 */
function openWithdrawModal() {
    document.getElementById('withdrawAmount').value = '';
    document.getElementById('withdrawStatus').textContent = '';
    // Ensure currentUser balance is up-to-date before displaying in modal
    updateElement('currentBalanceInWithdraw', currentUser.balance.toFixed(2));
    openModal('withdraw-modal');
}

/**
 * Open deposit modal
 */
function openDepositModal() {
    document.getElementById('depositAmount').value = '';
    document.getElementById('depositStatus').textContent = '';
    openModal('deposit-modal');
}

/**
 * Save profile changes (mock for now, API call needed)
 */
async function saveProfileChanges() {
    const usernameInput = document.getElementById('editUsername');
    const status = document.getElementById('editProfileStatus');
    
    const username = usernameInput.value;


    if (!username) {
        displayError('Please fill in all fields', status);
        return;
    }
    
    displayLoading(status, 'Saving changes...');
    
    // TODO: Implement API call (e.g., PUT /auth/me or a dedicated profile update endpoint)
    // For now, just update locally
    try {
        // Assuming a PUT /auth/me endpoint for profile updates:
        // const updatedUser = await apiPut('/auth/me', { username, email });
        // Object.assign(currentUser, updatedUser);

        currentUser.username = username;
        sessionStorage.setItem('loggedInUser', JSON.stringify(currentUser));
        
        updateProfileDisplay(); // Re-render UI with new data
        
        displaySuccess('Profile updated successfully! (Mock)', status);
        
        setTimeout(() => {
            closeModal('edit-profile-modal');
            status.textContent = '';
        }, 1500);
        
    } catch (error) {
        console.error('Profile update error:', error);
        displayError(error.message || 'Failed to update profile', status);
    }
}

/**
 * Open edit profile modal with current data
 */
function openEditProfileModal() {
    document.getElementById('editUsername').value = currentUser.username;
    document.getElementById('editProfileStatus').textContent = '';
    openModal('edit-profile-modal');
}

/**
 * Export portfolio data (client-side generation, no API call needed)
 */
function exportPortfolio() {
    try {
        const portfolioData = {
            user: currentUser.username,
            balance: currentUser.balance,
            portfolioValue: currentUser.portfolioValue,
            totalGains: currentUser.totalGains,
            portfolio: currentUser.portfolio,
            exportDate: new Date().toISOString()
        };
        
        const dataStr = JSON.stringify(portfolioData, null, 2);
        const blob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = `portfolio_${currentUser.username}_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        
        console.log('Portfolio exported successfully');
        displaySuccess('Portfolio exported successfully!'); // Using common.js displaySuccess
        
    } catch (error) {
        console.error('Export error:', error);
        displayError('Failed to export portfolio'); // Using common.js displayError
    }
}

// Helper to load prices, assuming it's available globally or imported if this is a separate module.
// This is copied from dashboard.js to make profile.js standalone for portfolio calculation.
// Ideally, this would be in common.js if used by both.
async function loadPricesForTickers(tickers) {
    if (!tickers || tickers.length === 0) return {};
    
    try {
        const tickerParam = tickers.join(',');
        console.log(`Profile page loading prices for: ${tickerParam}`);
        
        const prices = await apiGet(`/prices?tickers=${tickerParam}`);
        console.log('Profile page loaded prices:', prices);
        return prices;
    } catch (error) {
        console.error('Profile page error loading prices:', error);
        return {};
    }
}

