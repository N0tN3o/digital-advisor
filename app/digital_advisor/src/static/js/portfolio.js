// static/js/portfolio.js

// Global variables for portfolio page
let currentUser = {
    username: 'Guest',
    balance: 0,
    portfolio: []
};

let portfolioData = [];
let priceCache = {};
let selectedStock = null;
let portfolioChart = null;

// Initialize portfolio page
document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 Portfolio page initializing...');
    
    // Check authentication using common.js function
    if (!isAuthenticated()) {
        console.log('Not authenticated, redirecting to login');
        window.location.href = '/login';
        return;
    }
    
    // Initialize modal system
    initializeModalSystem();
    
    // Load user data and portfolio
    await loadUserData();
    await loadPortfolio();
    
    // Setup event listeners
    setupEventListeners();
    
    console.log('✅ Portfolio page initialized');
});

/**
 * Load user data for header display using common.js apiGet
 */
async function loadUserData() {
    try {
        const userData = await apiGet('/auth/me'); // Using apiGet from common.js
        currentUser = {
            username: userData.username,
            balance: userData.balance
        };
        
        // Update header display
        const usernameElement = document.getElementById('currentUsername');
        const balanceElement = document.getElementById('currentBalance');
        
        if (usernameElement) usernameElement.textContent = `Welcome, ${currentUser.username}!`;
        if (balanceElement) balanceElement.textContent = currentUser.balance.toFixed(2);
    } catch (error) {
        console.error('Error loading user data:', error);
    }
}

/**
 * Load prices for tickers using common.js function
 */
async function loadPricesForTickers(tickers) {
    if (!tickers || tickers.length === 0) return {};
    
    try {
        const tickerParam = tickers.join(',');
        console.log(`Loading prices for: ${tickerParam}`);
        
        const prices = await apiGet(`/prices?tickers=${tickerParam}`); // Using apiGet from common.js
        console.log('Loaded prices:', prices);
        
        // Store in global priceCache
        Object.assign(priceCache, prices);
        
        return prices;
    } catch (error) {
        console.error('Error loading prices:', error);
        return {};
    }
}

/**
 * Get price from cache
 */
function getPriceFromCache(ticker) {
    return priceCache[ticker.toUpperCase()] || null;
}

/**
 * Loads and displays the user's portfolio from Flask API.
 */
async function loadPortfolio() {
    const userPortfolioList = document.getElementById('userPortfolioList');
    const emptyPortfolio = document.getElementById('emptyPortfolio');
    
    if (!userPortfolioList) return;

    displayLoading(userPortfolioList, 'Loading portfolio...');

    try {
        console.log('Fetching portfolio from /portfolio API...');
        
        const portfolioApiData = await apiGet('/portfolio'); // Using apiGet from common.js
        
        // Extract the holdings array from the response
        const portfolio = portfolioApiData.holdings || [];
        const cashBalance = portfolioApiData.cash_balance || 0;
        
        console.log('=== PORTFOLIO DEBUG ===');
        console.log('Holdings array:', portfolio);
        console.log('Cash balance:', cashBalance);

        // Update user balance from API
        currentUser.balance = cashBalance;
        updateBalanceDisplay();

        if (portfolio.length === 0) {
            userPortfolioList.innerHTML = '';
            emptyPortfolio.style.display = 'block';
            updatePortfolioSummary([]);
            return;
        }

        emptyPortfolio.style.display = 'none';

        // Get prices for all tickers in the portfolio
        const tickers = [...new Set(portfolio.map(item => item.ticker))];
        await loadPricesForTickers(tickers);

        const enrichedPortfolio = portfolio.map((item) => {
            const currentPrice = getPriceFromCache(item.ticker);
            const volume = item.volume;
            const avgPrice = item.price || 0; // Purchase price
            const currentValue = volume * (currentPrice !== null ? currentPrice : 0);
            const totalCost = volume * avgPrice;
            const gainLoss = currentValue - totalCost;
            const gainLossPercent = totalCost > 0 ? (gainLoss / totalCost) * 100 : 0;
            
            return {
                ...item,
                current_price: currentPrice,
                current_value: currentValue,
                avg_price: avgPrice,
                gain_loss: gainLoss,
                gain_loss_percent: gainLossPercent
            };
        });

        portfolioData = enrichedPortfolio;
        currentUser.portfolio = enrichedPortfolio;
        
        renderPortfolio(enrichedPortfolio);
        renderDetailedTable(enrichedPortfolio);
        updatePortfolioSummary(enrichedPortfolio);
        renderPortfolioChart(enrichedPortfolio);
        
        console.log('Portfolio loaded successfully:', enrichedPortfolio);
        
    } catch (error) {
        console.error('Error loading portfolio:', error);
        displayError(error.message || 'Failed to load portfolio.', userPortfolioList);
    }
}

/**
 * Render portfolio holdings list
 */
function renderPortfolio(portfolio) {
    const userPortfolioList = document.getElementById('userPortfolioList');
    
    if (portfolio.length === 0) {
        userPortfolioList.innerHTML = '<div class="empty-state"><p>Your portfolio is empty.</p></div>';
        return;
    }
    
    const portfolioHTML = `
        <div class="portfolio-holdings-list">
            ${portfolio.map(item => {
                const changeClass = item.gain_loss >= 0 ? 'positive' : 'negative';
                const changeSign = item.gain_loss >= 0 ? '+' : '';
                
                return `
                    <div class="portfolio-item" onclick="openStockDetail('${item.ticker}')">
                        <div class="portfolio-item-header">
                            <span class="portfolio-stock-symbol">${item.ticker}</span>
                            <span class="portfolio-current-price">${item.current_price !== null ? item.current_price.toFixed(2) : 'N/A'}</span>
                        </div>
                        <div class="portfolio-item-details">
                            <div class="portfolio-detail">
                                <div class="portfolio-detail-label">Shares</div>
                                <div class="portfolio-detail-value">${item.volume.toLocaleString()}</div>
                            </div>
                            <div class="portfolio-detail">
                                <div class="portfolio-detail-label">Market Value</div>
                                <div class="portfolio-detail-value">$${item.current_value.toFixed(2)}</div>
                            </div>
                            <div class="portfolio-detail">
                                <div class="portfolio-detail-label">Gain/Loss</div>
                                <div class="portfolio-detail-value ${changeClass}">
                                    ${changeSign}$${Math.abs(item.gain_loss).toFixed(2)} (${changeSign}${item.gain_loss_percent.toFixed(2)}%)
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('')}
        </div>
    `;
    
    userPortfolioList.innerHTML = portfolioHTML;
}

/**
 * Render detailed holdings table
 */
function renderDetailedTable(portfolio) {
    const tableBody = document.getElementById('holdingsTableBody');
    
    if (portfolio.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="8" class="loading-row">No holdings to display</td></tr>';
        return;
    }
    
    tableBody.innerHTML = portfolio.map(item => {
        const gainLossClass = item.gain_loss >= 0 ? 'positive' : 'negative';
        const gainLossSign = item.gain_loss >= 0 ? '+' : '';
        
        return `
            <tr onclick="openStockDetail('${item.ticker}')" style="cursor: pointer;">
                <td class="stock-symbol-cell">${item.ticker}</td>
                <td>${item.volume.toLocaleString()}</td>
                <td class="price-cell">$${item.avg_price.toFixed(2)}</td>
                <td class="price-cell">$${(item.current_price || 0).toFixed(2)}</td>
                <td class="value-cell">$${item.current_value.toFixed(2)}</td>
                <td class="gain-loss-cell ${gainLossClass}">
                    ${gainLossSign}$${Math.abs(item.gain_loss).toFixed(2)}
                </td>
                <td class="percentage-cell ${gainLossClass}">
                    ${gainLossSign}${item.gain_loss_percent.toFixed(2)}%
                </td>
                <td class="actions-cell">
                    <button class="action-btn buy" onclick="event.stopPropagation(); openTradeModal('${item.ticker}', ${item.current_price || 0}, 'buy')">Buy</button>
                    <button class="action-btn sell" onclick="event.stopPropagation(); openTradeModal('${item.ticker}', ${item.current_price || 0}, 'sell')">Sell</button>
                    <button class="action-btn view" onclick="event.stopPropagation(); openStockDetail('${item.ticker}')">View</button>
                </td>
            </tr>
        `;
    }).join('');
}

/**
 * Update portfolio summary cards
 */
function updatePortfolioSummary(portfolio) {
    const totalValue = portfolio.reduce((sum, item) => sum + item.current_value, 0);
    const totalGainLoss = portfolio.reduce((sum, item) => sum + item.gain_loss, 0);
    const totalCost = portfolio.reduce((sum, item) => sum + (item.volume * item.avg_price), 0);
    const totalGainLossPercent = totalCost > 0 ? (totalGainLoss / totalCost) * 100 : 0;
    
    // Update summary cards
    updateElement('totalPortfolioValue', `$${totalValue.toFixed(2)}`);
    updateElement('cashBalance', `$${currentUser.balance.toFixed(2)}`);
    updateElement('holdingsCount', portfolio.length);
    updateElement('holdingsValue', `${portfolio.length} different stock${portfolio.length !== 1 ? 's' : ''}`);
    
    // Update total portfolio change
    const changeElement = document.getElementById('totalPortfolioChange');
    if (changeElement) {
        const changeSign = totalGainLoss >= 0 ? '+' : '';
        const changeClass = totalGainLoss >= 0 ? 'positive' : 'negative';
        changeElement.textContent = `${changeSign}$${Math.abs(totalGainLoss).toFixed(2)} (${changeSign}${totalGainLossPercent.toFixed(2)}%)`;
        changeElement.className = `summary-change ${changeClass}`;
    }
    
    // Update daily change (mock for now - would need historical data)
    const dailyChangeElement = document.getElementById('dailyChange');
    const dailyChangePercentElement = document.getElementById('dailyChangePercent');
    if (dailyChangeElement && dailyChangePercentElement) {
        const mockDailyChange = totalValue * (Math.random() - 0.5) * 0.02; // Mock ±1% daily change
        const mockDailyChangePercent = totalValue > 0 ? (mockDailyChange / totalValue) * 100 : 0;
        
        const dailySign = mockDailyChange >= 0 ? '+' : '';
        const dailyClass = mockDailyChange >= 0 ? 'positive' : 'negative';
        
        dailyChangeElement.textContent = `${dailySign}$${Math.abs(mockDailyChange).toFixed(2)}`;
        dailyChangeElement.className = `summary-value ${dailyClass}`;
        dailyChangePercentElement.textContent = `${dailySign}${mockDailyChangePercent.toFixed(2)}%`;
        dailyChangePercentElement.className = `summary-change ${dailyClass}`;
    }
}

/**
 * Render portfolio composition chart (simple implementation)
 */
function renderPortfolioChart(portfolio) {
    const chartContainer = document.querySelector('.chart-container');
    
    if (!chartContainer) return;
    
    if (portfolio.length === 0) {
        chartContainer.innerHTML = '<p style="color: #6b7280;">No data to display</p>';
        return;
    }
    
    // Simple pie chart representation
    const totalValue = portfolio.reduce((sum, item) => sum + item.current_value, 0);
    
    let chartHTML = '<div style="display: flex; flex-direction: column; gap: 1rem;">';
    
    // Add a simple legend
    chartHTML += '<div style="display: flex; flex-wrap: wrap; gap: 1rem; justify-content: center;">';
    
    portfolio.forEach((item, index) => {
        const percentage = (item.current_value / totalValue) * 100;
        const colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#14b8a6'];
        const color = colors[index % colors.length];
        
        chartHTML += `
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <div style="width: 16px; height: 16px; background: ${color}; border-radius: 50%;"></div>
                <span style="font-size: 0.9rem; color: #374151;">${item.ticker} (${percentage.toFixed(1)}%)</span>
            </div>
        `;
    });
    
    chartHTML += '</div>';
    
    // Add value breakdown
    chartHTML += '<div style="text-align: center; margin-top: 1rem;">';
    chartHTML += `<h4 style="margin: 0; color: #1f2937;">Total Portfolio: $${totalValue.toFixed(2)}</h4>`;
    chartHTML += '</div>';
    
    chartHTML += '</div>';
    
    chartContainer.innerHTML = chartHTML;
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Refresh button
    const refreshBtn = document.getElementById('refreshPortfolioBtn');
    if (refreshBtn) refreshBtn.addEventListener('click', refreshPortfolio);
    
    // Export button
    const exportBtn = document.getElementById('exportHoldingsBtn');
    if (exportBtn) exportBtn.addEventListener('click', exportHoldings);
    
    // Sort dropdown
    const sortSelect = document.getElementById('sortBy');
    if (sortSelect) sortSelect.addEventListener('change', handleSort);
    
    // Chart toggle buttons
    const pieChartBtn = document.getElementById('pieChartBtn');
    const performanceChartBtn = document.getElementById('performanceChartBtn');
    if (pieChartBtn) pieChartBtn.addEventListener('click', () => switchChart('pie'));
    if (performanceChartBtn) performanceChartBtn.addEventListener('click', () => switchChart('performance'));
    
    // Table sorting
    document.querySelectorAll('.sortable').forEach(header => {
        header.addEventListener('click', () => {
            const sortField = header.dataset.sort;
            handleTableSort(sortField);
        });
    });
}

/**
 * Refresh portfolio data
 */
async function refreshPortfolio() {
    const refreshBtn = document.getElementById('refreshPortfolioBtn');
    if (!refreshBtn) return;
    
    const originalText = refreshBtn.textContent;
    
    refreshBtn.textContent = '🔄 Refreshing...';
    refreshBtn.disabled = true;
    
    try {
        // Clear price cache to get fresh data
        priceCache = {};
        await loadPortfolio();
        console.log('Portfolio refreshed successfully');
    } finally {
        refreshBtn.textContent = originalText;
        refreshBtn.disabled = false;
    }
}

/**
 * Export holdings to CSV
 */
function exportHoldings() {
    if (portfolioData.length === 0) {
        alert('No holdings to export');
        return;
    }
    
    const headers = ['Symbol', 'Shares', 'Avg Price', 'Current Price', 'Market Value', 'Gain/Loss', '% Change'];
    const csvContent = [
        headers.join(','),
        ...portfolioData.map(item => [
            item.ticker,
            item.volume,
            item.avg_price.toFixed(2),
            (item.current_price || 0).toFixed(2),
            item.current_value.toFixed(2),
            item.gain_loss.toFixed(2),
            item.gain_loss_percent.toFixed(2) + '%'
        ].join(','))
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', `portfolio_holdings_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    console.log('Portfolio holdings exported to CSV');
}

/**
 * Handle sorting
 */
function handleSort(event) {
    const sortBy = event.target.value;
    const sortedPortfolio = [...portfolioData];
    
    sortedPortfolio.sort((a, b) => {
        switch (sortBy) {
            case 'value':
                return b.current_value - a.current_value;
            case 'ticker':
                return a.ticker.localeCompare(b.ticker);
            case 'change':
                return b.gain_loss - a.gain_loss;
            case 'volume':
                return b.volume - a.volume;
            default:
                return 0;
        }
    });
    
    renderPortfolio(sortedPortfolio);
    renderDetailedTable(sortedPortfolio);
}

/**
 * Handle table sorting
 */
function handleTableSort(field) {
    const sortedPortfolio = [...portfolioData];
    
    sortedPortfolio.sort((a, b) => {
        let aValue = a[field] || a[field.replace(/([A-Z])/g, '_$1').toLowerCase()];
        let bValue = b[field] || b[field.replace(/([A-Z])/g, '_$1').toLowerCase()];
        
        if (typeof aValue === 'string') {
            return aValue.localeCompare(bValue);
        }
        return bValue - aValue; // Descending order for numbers
    });
    
    renderDetailedTable(sortedPortfolio);
}

/**
 * Switch chart type
 */
function switchChart(type) {
    document.querySelectorAll('.chart-btn').forEach(btn => btn.classList.remove('active'));
    
    if (type === 'pie') {
        const pieBtn = document.getElementById('pieChartBtn');
        if (pieBtn) pieBtn.classList.add('active');
        renderPortfolioChart(portfolioData);
    } else {
        const perfBtn = document.getElementById('performanceChartBtn');
        if (perfBtn) perfBtn.classList.add('active');
        // Performance chart would be implemented here
        const chartContainer = document.querySelector('.chart-container');
        if (chartContainer) {
            chartContainer.innerHTML = '<p style="color: #6b7280;">Performance chart coming soon</p>';
        }
    }
}

/**
 * Open stock detail modal
 */
function openStockDetail(ticker) {
    const stock = portfolioData.find(item => item.ticker === ticker);
    if (!stock) return;
    
    selectedStock = stock;
    
    updateElement('stockDetailTitle', `${ticker} - Stock Details`);
    updateElement('detailCurrentPrice', `$${(stock.current_price || 0).toFixed(2)}`);
    updateElement('detailShares', stock.volume.toLocaleString());
    updateElement('detailMarketValue', `$${stock.current_value.toFixed(2)}`);
    
    const gainLossElement = document.getElementById('detailGainLoss');
    if (gainLossElement) {
        const gainLossSign = stock.gain_loss >= 0 ? '+' : '';
        const gainLossClass = stock.gain_loss >= 0 ? 'positive' : 'negative';
        gainLossElement.textContent = `${gainLossSign}$${Math.abs(stock.gain_loss).toFixed(2)} (${gainLossSign}${stock.gain_loss_percent.toFixed(2)}%)`;
        gainLossElement.className = gainLossClass;
    }
    
    // Initialize TradingView widget if function exists
    if (typeof initializeTradingViewWidget === 'function') {
        initializeTradingViewWidget(ticker);
    }
    
    openModal('stock-detail-modal');
}

/**
 * Initialize TradingView widget
 */
function initializeTradingViewWidget(symbol) {
    const container = document.getElementById('tradingview_chart');
    if (!container || typeof TradingView === 'undefined') return;
    
    container.innerHTML = ''; // Clear previous chart
    
    try {
        new TradingView.widget({
            width: '100%',
            height: 400,
            symbol: `NASDAQ:${symbol}`,
            interval: 'D',
            timezone: 'Etc/UTC',
            theme: 'light',
            style: '1',
            locale: 'en',
            toolbar_bg: '#f1f3f6',
            enable_publishing: false,
            hide_side_toolbar: false,
            allow_symbol_change: false,
            container_id: 'tradingview_chart'
        });
    } catch (error) {
        console.error('Error initializing TradingView widget:', error);
        container.innerHTML = '<p style="color: #6b7280;">Chart unavailable</p>';
    }
}

/**
 * Open trade modal from detail view
 */
function openTradeModalFromDetail(action) {
    if (!selectedStock) return;
    
    closeModal('stock-detail-modal');
    
    // This would open the trade modal - assuming it exists in your system
    if (typeof openTradeModal === 'function') {
        openTradeModal(selectedStock.ticker, selectedStock.current_price || 0, action);
    }
}

/**
 * Update balance display
 */
function updateBalanceDisplay() {
    const balanceElement = document.getElementById('currentBalance');
    if (balanceElement) {
        balanceElement.textContent = currentUser.balance.toFixed(2);
    }
}

/**
 * Helper function to safely update DOM elements
 */
function updateElement(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value;
    }
}

/**
 * Utility functions
 */
function displayLoading(container, message = 'Loading...') {
    if (!container) return;
    container.innerHTML = `
        <div class="loading-state">
            <div class="loading-spinner"></div>
            <p>${message}</p>
        </div>
    `;
}

function displayError(message, container) {
    if (!container) return;
    container.innerHTML = `
        <div class="loading-state">
            <p style="color: #dc2626;">❌ ${message}</p>
            <button onclick="loadPortfolio()" class="btn btn-primary">Try Again</button>
        </div>
    `;
}

// Initialize modal system (basic implementation)
function initializeModalSystem() {
    const modals = document.querySelectorAll('.modal-overlay');
    modals.forEach(modal => {
        modal.style.display = 'none';
    });
}

function openRebalanceModal() {
    alert('Rebalance modal is not implemented yet.');
}

// Debug helpers
window.portfolioDebug = {
    portfolioData,
    refreshPortfolio,
    loadPortfolio,
    currentUser
};