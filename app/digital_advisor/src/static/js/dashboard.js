// static/js/dashboard.js

// Global variables for dashboard state
let currentUser = {
    username: 'Guest',
    balance: 10000.00,
    totalTrades: 0,
    portfolioValue: 0.00,
    totalGains: 0.00,
    activePredictions: 0,
    portfolio: [],
    email: 'N/A'
};

let currentMarketData = [];
let selectedStockForTrade = null;
let priceCache = {};
let pricesCacheTime = null;

document.addEventListener('DOMContentLoaded', async () => {
    // checkAuthStatus is handled by common.js's DOMContentLoaded listener
    // This listener will ensure redirection if not authenticated.
    // If we reach here, it means the user is authenticated.

    loadUserData();
    setupEventListeners();

    // Add this for AI predictions refresh button
    const refreshAIPredictionsBtn = document.getElementById('refreshAIPredictionsBtn');
    if (refreshAIPredictionsBtn) {
        refreshAIPredictionsBtn.addEventListener('click', () => {
            loadAIPredictions();
        });
    }

    // Load market data with REAL prices
    await loadLiveMarketData();
    
    loadPortfolio();
    loadAIPredictions();
    
    // Setup auto-refresh
    setupAutoRefresh();
});

/**
 * Load REAL user data from /auth/me API
 */
async function loadUserData() {
    try {
        console.log('Loading REAL user data from /auth/me API...');
        
        const userData = await apiGet('/auth/me'); // Using apiGet from common.js
        console.log('REAL user data from API:', userData);

        // Update currentUser with REAL data from your backend
        currentUser = {
            // Real data from /auth/me API
            user_id: userData.user_id || userData.id,
            username: userData.username,  // Real username
            email: userData.email,        // Real email
            balance: Number(userData.balance) || 0,  // Real balance
            
            // Keep calculated values or initialize if not present in backend
            totalTrades: currentUser.totalTrades || 0,
            portfolioValue: currentUser.portfolioValue || 0.00,
            totalGains: currentUser.totalGains || 0.00,
            activePredictions: currentUser.activePredictions || 0,
            portfolio: currentUser.portfolio || [],
            
            // Meta
            isLoaded: true,
            lastUpdated: new Date()
        };

        sessionStorage.setItem('loggedInUser', JSON.stringify(currentUser));
        
        console.log('Updated currentUser with REAL data:', currentUser);
        
        // Update UI with real data
        updateUserProfileDisplay();
        
    } catch (error) {
        console.error('Error loading real user data:', error);
        displayError(error.message || 'Failed to load user data.');
        updateUserProfileDisplay(); // Show cached data if API fails
    }
}

/**
 * Updates the user profile display on the header and profile modal (safely).
 * Only updates elements that exist on the current page.
 */
function updateUserProfileDisplay() {
    const displayBalance = typeof currentUser.balance === 'number' ? currentUser.balance : 0;
    const displayTotalTrades = typeof currentUser.totalTrades === 'number' ? currentUser.totalTrades : 0;
    const displayPortfolioValue = typeof currentUser.portfolioValue === 'number' ? currentUser.portfolioValue : 0;
    const displayTotalGains = typeof currentUser.totalGains === 'number' ? currentUser.totalGains : 0;
    const displayActivePredictions = typeof currentUser.activePredictions === 'number' ? currentUser.activePredictions : 0;

    // Helper function to safely update element text content
    function safeUpdateElement(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
        } else {
            // console.log(`Element '${elementId}' not found on this page, skipping update`);
        }
    }

    // Update elements that exist on dashboard page
    safeUpdateElement('currentUsername', `Welcome, ${currentUser.username || 'User'}!`);
    safeUpdateElement('currentBalance', displayBalance.toFixed(2));

    // Update profile modal fields (only if they exist - these are on profile page)
    safeUpdateElement('displayUsername', currentUser.username || 'N/A');
    safeUpdateElement('displayEmail', currentUser.email || 'N/A');
    safeUpdateElement('displayBalance', `$${displayBalance.toFixed(2)}`);
    safeUpdateElement('totalTradesCount', displayTotalTrades);
    safeUpdateElement('currentPortfolioValue', `$${displayPortfolioValue.toFixed(2)}`);
    safeUpdateElement('totalProfitLoss', `$${displayTotalGains.toFixed(2)}`);
    safeUpdateElement('activePredictionsCount', displayActivePredictions);
}

/**
 * Sets up event listeners for search and modal interactions.
 */
function setupEventListeners() {
    const stockSearchField = document.getElementById('stockSearchField');
    if (stockSearchField) {
        stockSearchField.addEventListener('input', filterStocks);
    }

    const tradeSharesInput = document.getElementById('tradeSharesInput');
    if (tradeSharesInput) {
        tradeSharesInput.addEventListener('input', calculateTotalCost);
    }

    const tradeActionSelect = document.getElementById('tradeAction');
    if (tradeActionSelect) {
        tradeActionSelect.addEventListener('change', calculateTotalCost);
    }

    // Modal close button listeners
    document.querySelectorAll('.close-button').forEach(button => {
        button.addEventListener('click', (event) => {
            const modalId = event.target.closest('.modal-overlay').id;
            closeModal(modalId);
        });
    });

    // Specific button listeners
    document.getElementById('executeTradeButton')?.addEventListener('click', executeTrade);
    document.getElementById('tradeBasedOnPredictionButton')?.addEventListener('click', tradeBasedOnPrediction);
    document.getElementById('showTopStocksButton')?.addEventListener('click', showTopStocks);
    document.getElementById('exportPortfolioButton')?.addEventListener('click', exportPortfolio);
    document.getElementById('editUserProfileButton')?.addEventListener('click', editUserProfile); // This refers to the mock function
}

/**
 * Loads all initial dashboard data. (Consolidated as much as possible)
 */
async function loadDashboardData() {
    // loadUserData already called in DOMContentLoaded
    // await loadLiveMarketData() already called in DOMContentLoaded
    // loadPortfolio() already called in DOMContentLoaded
    // loadAIPredictions() already called in DOMContentLoaded
    console.log("Dashboard data initialization complete.");
}

/**
 * Get price from cache
 */
function getPriceFromCache(ticker) {
    return priceCache[ticker.toUpperCase()] || null;
}

/**
 * Load prices for tickers using the /prices API.
 */
async function loadPricesForTickers(tickers) {
    if (!tickers || tickers.length === 0) return {};
    
    try {
        const tickerParam = tickers.join(',');
        console.log(`Loading prices for: ${tickerParam}`);
        
        const prices = await apiGet(`/prices?tickers=${tickerParam}`);
        console.log('Loaded prices:', prices);
        
        // Store in global priceCache
        Object.assign(priceCache, prices);
        pricesCacheTime = Date.now();
        
        return prices;
    } catch (error) {
        console.error('Error loading prices:', error);
        displayError(error.message || 'Failed to load stock prices.');
        return {};
    }
}

/**
 * Loads live market data using real API calls.
 */
async function loadLiveMarketData() {
    const liveStockGrid = document.getElementById('liveStockGrid');
    if (!liveStockGrid) return;

    displayLoading(liveStockGrid, 'Loading live market data...');

    try {
        // Define stocks to display in market overview (Nasdaq 100 sample)
        const marketTickers = [
            "APP", "BKNG", "META", "NVDA", "PEP", "PLTR", "TSLA"
        ];

        console.log('Loading live market data for:', marketTickers);

        // Load REAL prices from your API
        const prices = await loadPricesForTickers(marketTickers);
        console.log('Loaded real market prices:', prices);

        if (Object.keys(prices).length === 0) {
            displayError('Failed to load market data. Please try again later.', liveStockGrid);
            return;
        }

        // Create market data with REAL prices, and calculate change/percentChange
        const marketData = marketTickers.map(ticker => {
            const currentPrice = prices[ticker];
            
            if (!currentPrice) {
                console.warn(`No price data for ${ticker}`);
                return null;
            }

            return {
                symbol: ticker,
                name: getCompanyName(ticker),
                price: currentPrice,  // REAL PRICE from API
            };
        }).filter(Boolean); // Remove null entries

        console.log('Market data with real prices:', marketData);

        // Store for other functions
        currentMarketData = marketData;

        // Render with real prices
        renderStocks(marketData);

    } catch (error) {
        console.error('Error loading live market data:', error);
        displayError(error.message || 'Failed to load market data. Please try again later.', liveStockGrid);
    }
}

/**
 * Company names for display (expanded for Nasdaq 100)
 */
function getCompanyName(ticker) {
    const companyNames = {
        'APP': 'AppLovin Corp.',
        'BKNG': 'Booking Holdings Inc.',
        'META': 'Meta Platforms Inc.',
        'NVDA': 'NVIDIA Corporation',
        'PEP': 'PepsiCo Inc.',
        'PLTR': 'Palantir Technologies Inc.',
        'TSLA': 'Tesla Inc.'
    };
    return companyNames[ticker] || `${ticker} Corp.`;
}

/**
 * Refresh market data manually
 */
async function refreshMarketData() {
    console.log('Refreshing market data...');
    
    // Clear price cache to get fresh data
    priceCache = {};
    pricesCacheTime = null;
    
    // Reload market data
    await loadLiveMarketData();
    
    console.log('Market data refreshed with real prices!');
}

/**
 * Auto-refresh every 5 minutes
 */
function setupAutoRefresh() {
    setInterval(refreshMarketData, 5 * 60 * 1000);
    console.log('Auto-refresh enabled for market data');
}

/**
 * Renders stock items in the live stock grid.
 */
function renderStocks(stocks) {
    const liveStockGrid = document.getElementById('liveStockGrid');
    liveStockGrid.innerHTML = '';

    if (stocks.length === 0) {
        displayError('No stocks found matching your criteria.', liveStockGrid);
        return;
    }

    stocks.forEach(stock => {

        const stockCard = document.createElement('div');
        stockCard.classList.add('stock-item-card');
        stockCard.innerHTML = `
            <div class="stock-info mb-2">
                <div class="stock-symbol">${stock.symbol}</div>
                <div class="stock-company-name">${stock.name}</div>
            </div>
            <div class="stock-price-data">
                <div class="current-price">$${stock.price.toFixed(2)}</div>
            </div>
            <div class="trade-predict-buttons">
                <button class="btn btn-primary" onclick="openTradeModal('${stock.symbol}', ${stock.price})">Trade</button>
            </div>
        `;
        liveStockGrid.appendChild(stockCard);
    });
}

/**
 * Filters stocks based on search input.
 */
function filterStocks() {
    const searchTerm = document.getElementById('stockSearchField').value.toLowerCase();
    const filteredStocks = currentMarketData.filter(stock =>
        stock.symbol.toLowerCase().includes(searchTerm) ||
        stock.name.toLowerCase().includes(searchTerm)
    );
    renderStocks(filteredStocks);
}


/**
 * Loads and displays the user's portfolio from Flask API.
 */
async function loadPortfolio() {
    const userPortfolioList = document.getElementById('userPortfolioList');
    if (!userPortfolioList) return;

    displayLoading(userPortfolioList, 'Loading portfolio...');

    try {
        const portfolioData = await apiGet('/portfolio'); // Using apiGet from common.js
        
        // Extract the holdings array from the response
        const portfolio = portfolioData.holdings || [];
        const cashBalance = portfolioData.cash_balance || 0;
        
        console.log('=== PORTFOLIO DEBUG ===');
        console.log('Holdings array:', portfolio);
        console.log('Cash balance:', cashBalance);

        // Update user balance from API
        currentUser.balance = cashBalance;
        updateUserProfileDisplay();

        if (portfolio.length === 0) {
            userPortfolioList.innerHTML = '<p class="text-center text-gray-600">Your portfolio is empty.</p>';
            currentUser.portfolio = [];
            calculatePortfolioValue(); // Update values even if empty
            return;
        }

        // Get prices for all tickers in the portfolio
        const tickers = [...new Set(portfolio.map(item => item.ticker))];
        await loadPricesForTickers(tickers);

        const enrichedPortfolio = portfolio.map((item) => {
            const currentPrice = getPriceFromCache(item.ticker);
            const volume = item.volume;
            // Ensure currentPrice is a number before calculation
            const currentValue = volume * (currentPrice !== null ? currentPrice : 0); 
            
            return {
                ...item,
                current_price: currentPrice,
                current_value: currentValue
            };
        });

        currentUser.portfolio = enrichedPortfolio;
        renderPortfolio(enrichedPortfolio);
        calculatePortfolioValue();
        
    } catch (error) {
        console.error('Error loading portfolio:', error);
        displayError(error.message || 'Failed to load portfolio.', userPortfolioList);
    }
}

function renderPortfolio(portfolio) {
    const userPortfolioList = document.getElementById('userPortfolioList');
    
    userPortfolioList.innerHTML = '';
    const ul = document.createElement('ul');
    ul.classList.add('space-y-3'); // Tailwind class for spacing

    portfolio.forEach((item) => {
        const li = document.createElement('li');
        li.classList.add('portfolio-item', 'bg-gray-50', 'p-3', 'rounded-md', 'shadow-sm', 'flex', 'items-center', 'justify-between');
        li.innerHTML = `
            <div class="flex-grow">
                <span class="portfolio-stock-symbol font-semibold text-lg text-gray-800">${item.ticker}</span>
                <span class="portfolio-holdings text-gray-600 ml-2">${item.volume} shares @ $${item.current_price !== null ? item.current_price.toFixed(2) : 'N/A'}</span>
            </div>
            <span class="portfolio-value font-bold text-blue-700">Value: $${item.current_value !== null ? item.current_value.toFixed(2) : 'N/A'}</span>
        `;
        ul.appendChild(li);
    });
    
    userPortfolioList.appendChild(ul);
}

/**
 * Calculates and updates the total portfolio value and P&L.
 */
function calculatePortfolioValue() {
    let totalValue = 0;
    let totalPL = 0; // Profit/Loss

    currentUser.portfolio.forEach(item => {
        const currentPrice = getPriceFromCache(item.ticker);
        if (currentPrice !== null) {
            totalValue += item.volume * currentPrice;
            // Assuming 'item.price' is the average purchase price
            totalPL += (currentPrice - item.price) * item.volume; 
        }
    });

    currentUser.portfolioValue = totalValue;
    currentUser.totalGains = totalPL; // Assign calculated P&L
    updateUserProfileDisplay();
}

/**
 * Loads AI predictions using real API with MAE-based confidence.
 */
async function loadAIPredictions() {
    const aiPredictionsList = document.getElementById('aiPredictionsList');
    if (!aiPredictionsList) return;

    displayLoading(aiPredictionsList, 'Loading AI predictions...');

    const modelMAE = {
        'APP': 24.175, 'PEP': 1.678, 'TSLA': 1.041, 'NVDA': 1.690, 'BKNG': 28.569, 'META': 4.389, 'PLTR': 0.935
    };

    try {
        const predictionTickers = [
            "APP", "BKNG", "META", "NVDA", "PEP", "PLTR", "TSLA"
        ];
        const predictions = [];
        const currentPrices = await loadPricesForTickers(predictionTickers);

        for (const ticker of predictionTickers) {
            const currentPrice = currentPrices[ticker];
            if (!currentPrice) {
                console.warn(`Skipping prediction for ${ticker}: current price not available.`);
                continue;
            }
            try {
                const predictionResponse = await apiGet(`/predict?ticker=${ticker}`);
                let predictedPrice;
                if (typeof predictionResponse === 'number') {
                    predictedPrice = predictionResponse;
                } else if ('predicted_close_value' in predictionResponse) {
                    predictedPrice = predictionResponse.predicted_close_value;
                } else if ('price' in predictionResponse) {
                    predictedPrice = predictionResponse.price;
                } else {
                    console.warn(`Prediction for ${ticker} is not a number. Skipping.`);
                    continue;
                }

                const mae = modelMAE[ticker] || 5.0;
                const priceChange = predictedPrice - currentPrice;
                const percentChange = (priceChange / currentPrice) * 100;
                const direction = priceChange >= 0 ? 'Up' : 'Down';
                const maePercentage = (mae / currentPrice) * 100;
                let confidence;
                if (maePercentage <= 2) {
                    confidence = 'Very High';
                } else if (maePercentage <= 4) {
                    confidence = 'High';
                } else if (maePercentage <= 8) {
                    confidence = 'Medium';
                } else if (maePercentage <= 15) {
                    confidence = 'Low';
                } else {
                    confidence = 'Very Low';
                }

                predictions.push({
                    symbol: ticker,
                    company: getCompanyName(ticker),
                    direction: direction,
                    confidence: confidence,
                    timeframe: '1 week',
                    predictedPrice: predictedPrice,
                    currentPrice: currentPrice,
                    priceChange: priceChange,
                    percentChange: percentChange,
                    mae: mae,
                    maePercentage: maePercentage
                });
            } catch (error) {
                console.error(`Error getting prediction for ${ticker}:`, error);
            }
        }

        predictions.sort((a, b) => {
            const confidenceOrder = {'Very High': 5, 'High': 4, 'Medium': 3, 'Low': 2, 'Very Low': 1};
            const aScore = confidenceOrder[a.confidence] * 10 + Math.abs(a.percentChange);
            const bScore = confidenceOrder[b.confidence] * 10 + Math.abs(b.percentChange);
            return bScore - aScore;
        });

        currentUser.activePredictions = predictions.length;
        updateUserProfileDisplay();

        if (predictions.length === 0) {
            aiPredictionsList.innerHTML = '<p style="text-align:center; color: #666;">No AI predictions available.</p>';
            return;
        }

        aiPredictionsList.innerHTML = '';
        const ul = document.createElement('ul');
        ul.style.listStyle = 'none';
        ul.style.padding = '0';
        ul.style.margin = '0';

        predictions.forEach(item => {
            const confidenceColors = {
                'Very High': 'background: #d1fae5; color: #065f46;',
                'High': 'background: #bbf7d0; color: #166534;',
                'Medium': 'background: #fef9c3; color: #92400e;',
                'Low': 'background: #fee2e2; color: #991b1b;',
                'Very Low': 'background: #f3f4f6; color: #374151;'
            };
            const changeColor = item.direction === 'Up' ? 'color: #16a34a;' : 'color: #dc2626;';
            const changeSign = item.priceChange >= 0 ? '+' : '';

            const li = document.createElement('li');
            li.style.cssText = `
                background: #fff;
                padding: 0;
                border-radius: 8px;
                box-shadow: 0 1px 4px rgba(0,0,0,0.06);
                margin-bottom: 12px;
                overflow: hidden;
            `;

            // Summary row (always visible)
            const summaryDiv = document.createElement('div');
            summaryDiv.style.cssText = `
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 16px;
                cursor: pointer;
                transition: background 0.2s;
            `;
            summaryDiv.onmouseover = () => summaryDiv.style.background = "#f3f4f6";
            summaryDiv.onmouseout = () => summaryDiv.style.background = "#fff";

            summaryDiv.innerHTML = `
                <div style="flex-grow:1;">
                    <span style="font-weight:600; font-size:1.1rem; color:#1f2937;">${item.company}</span>
                    <span style="margin-left:10px;">
                        <span style="${changeColor} font-weight:700;">
                            ${item.direction} ${changeSign}${item.percentChange.toFixed(1)}%
                        </span>
                        <span style="margin-left:10px; font-weight:500; color:#374151;">
                            Predicted: $${item.predictedPrice.toFixed(2)}
                        </span>
                    </span>
                    <div style="font-size:0.95em; color:#6b7280; margin-top:2px;">
                        Real: $${item.currentPrice.toFixed(2)} | Δ: ${changeSign}$${Math.abs(item.priceChange).toFixed(2)}
                    </div>
                    <div style="font-size:0.9em; color:#6b7280;">
                        MAE: ${item.mae.toFixed(2)} (${item.maePercentage.toFixed(2)}%)
                    </div>
                </div>
                <span style="padding: 6px 16px; border-radius: 999px; font-size:0.95em; font-weight:600; ${confidenceColors[item.confidence] || ''}"
                    title="Model MAE: ${item.mae.toFixed(2)} (${item.maePercentage.toFixed(2)}% of real price)">
                    ${item.confidence}
                </span>
                <span class="expand-arrow" style="margin-left:16px; font-size:1.2em; color:#888;">&#9654;</span>
            `;

            // Details row (hidden by default)
            const detailsDiv = document.createElement('div');
            detailsDiv.style.display = 'none';
            detailsDiv.style.padding = '0 16px 16px 16px';
            detailsDiv.innerHTML = `
                <div id="tradingview-chart-${item.symbol}" style="height:300px;"></div>
            `;

            // Expand/collapse logic
            summaryDiv.addEventListener('click', () => {
                const arrow = summaryDiv.querySelector('.expand-arrow');
                if (detailsDiv.style.display === 'none') {
                    detailsDiv.style.display = 'block';
                    arrow.innerHTML = '&#9660;';
                    // Only load chart once
                    if (!detailsDiv.dataset.chartLoaded) {
                        loadTradingViewWidget(item.symbol, `tradingview-chart-${item.symbol}`);
                        detailsDiv.dataset.chartLoaded = 'true';
                    }
                } else {
                    detailsDiv.style.display = 'none';
                    arrow.innerHTML = '&#9654;';
                }
            });

            li.appendChild(summaryDiv);
            li.appendChild(detailsDiv);
            ul.appendChild(li);
        });
        aiPredictionsList.appendChild(ul);

    } catch (error) {
        console.error('Error loading AI predictions:', error);
        displayError(error.message || 'Failed to load predictions.', aiPredictionsList);
    }
}


// Function to load TradingView widget
function loadTradingViewWidget(symbol, containerId) {
    new TradingView.widget(
        {
            "width": "100%",
            "height": 300,
            "symbol": symbol, // Use the stock symbol here
            "interval": "D",
            "timezone": "Europe/Amsterdam", // Set your desired timezone
            "theme": "dark", // or "light"
            "style": "1",
            "locale": "en",
            "toolbar_bg": "#f1f3f6",
            "enable_publishing": false,
            "allow_symbol_change": true,
            "container_id": containerId,
            "show_popup_button": true,
            "popup_width": "1000",
            "popup_height": "650",
            "studies": [
                // Example: Add RSI indicator
            ]
        }
    );
}

// After injecting the HTML for each list item:
// Assuming 'li' is the list item element you just created and populated.

const summaryDiv = li.querySelector('.stock-summary');
const chartContainer = li.querySelector('.chart-container');
const chartId = `tradingview-chart-${item.symbol}`; // Get the specific ID for this chart

summaryDiv.addEventListener('click', () => {
    if (chartContainer.style.display === 'none') {
        chartContainer.style.display = 'block';
        // Check if the chart has already been loaded for this container
        if (!chartContainer.dataset.chartLoaded) {
            loadTradingViewWidget(item.symbol, chartId);
            chartContainer.dataset.chartLoaded = 'true'; // Mark as loaded
        }
    } else {
        chartContainer.style.display = 'none';
    }
});

/**
 * Opens the trading modal for a selected stock.
 */
function openTradeModal(symbol, price) {
    selectedStockForTrade = { symbol, price };
    const tradingTitle = document.getElementById('tradingTitle');
    const sharesInput = document.getElementById('tradeSharesInput');
    const statusMessage = document.getElementById('tradeStatusMessage');
    
    if (tradingTitle) tradingTitle.textContent = `Trade ${symbol}`;
    if (sharesInput) sharesInput.value = 1;
    if (statusMessage) statusMessage.textContent = '';
    
    calculateTotalCost();
    openModal('trade-stock-modal');
}

/**
 * Calculates and updates the total cost/value in the trading modal.
 */
function calculateTotalCost() {
    if (!selectedStockForTrade) return;

    const sharesInput = document.getElementById('tradeSharesInput');
    const totalDisplay = document.getElementById('tradeTotalCostDisplay');
    
    if (!sharesInput || !totalDisplay) return;

    const shares = parseInt(sharesInput.value);
    const price = selectedStockForTrade.price;
    let total = 0;

    if (!isNaN(shares) && shares > 0) {
        total = shares * price;
    }

    totalDisplay.textContent = total.toFixed(2);
}

/**
 * Executes a trade using Flask API.
 */
async function executeTrade() {
    const statusMessage = document.getElementById('tradeStatusMessage');
    const sharesInput = document.getElementById('tradeSharesInput');
    const actionSelect = document.getElementById('tradeAction');
    
    if (!statusMessage || !sharesInput || !actionSelect) {
        console.error('Required trade modal elements not found');
        return;
    }

    displayLoading(statusMessage, 'Executing trade...');

    if (!selectedStockForTrade) {
        displayError('No stock selected for trade. Please select a stock first.', statusMessage);
        return;
    }

    const shares = parseInt(sharesInput.value);
    const action = actionSelect.value;
    const symbol = selectedStockForTrade.symbol;

    if (isNaN(shares) || shares <= 0) {
        displayError('Please enter a valid number of shares.', statusMessage);
        return;
    }

    try {
        const endpoint = action === 'buy' ? '/portfolio/buy' : '/portfolio/sell';
        const data = await apiPost(endpoint, { // Using apiPost from common.js
            ticker: symbol,
            volume: shares
        });

        displaySuccess(data.msg || `${action.toUpperCase()} of ${shares} shares of ${symbol} successful!`, statusMessage);

        // Update local data
        currentUser.totalTrades++;
        sessionStorage.setItem('loggedInUser', JSON.stringify(currentUser));
        
        // Reload portfolio and user data
        await loadUserData(); // Refresh user balance and other info
        loadPortfolio(); // Refresh portfolio list

        setTimeout(() => closeModal('trade-stock-modal'), 1500);
    } catch (error) {
        console.error('Trade error:', error);
        displayError(error.message || 'An error occurred during trade. Please try again.', statusMessage);
    }
}

/**
 * Helper to get color for confidence level.
 */
function getConfidenceColor(confidence) {
    switch (confidence.toLowerCase()) {
        case 'very high': return '#10B981'; // Green
        case 'high': return '#34D399'; // Lighter Green
        case 'medium': return '#F59E0B'; // Amber
        case 'low': return '#EF4444'; // Red
        case 'very low': return '#DC2626'; // Darker Red
        default: return '#6B7280'; // Gray
    }
}

/**
 * Logs out the current user. (Uses global common.js function)
 */
function logoutUser() {
    console.log('Logging out user...');
    localStorage.removeItem('access_token'); // Clear token
    sessionStorage.removeItem('loggedInUser'); // Clear user data
    window.location.href = '/login'; // Redirect to login page
    console.log('User logged out and redirected to login.');
    alert('You have been logged out successfully.'); // Alert user (can be replaced with displaySuccess)

}

/**
 * Placeholder functions (now using display messages instead of alerts)
 */
function showCustomMessage(message) {
    displaySuccess(message); // Using the global success modal
}

function showTopStocks() {
    showCustomMessage('Showing top performing stocks! (Feature coming soon)');
}


function exportPortfolio() {
    showCustomMessage('Exporting portfolio data! (Feature coming soon)');
    // If you want to keep the file export, you can copy the logic from profile.js's exportPortfolio function
}

function editUserProfile() {
    showCustomMessage('Edit profile functionality coming soon! (Mock feature)');
    closeModal('user-profile-modal'); // Assuming this modal exists for profile edits
}

