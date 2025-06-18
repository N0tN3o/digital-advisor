// static/js/history.js

// Global variables for history page
let allTransactions = [];
let filteredTransactions = [];
let currentPage = 1;
let transactionsPerPage = 20;
let currentSort = { field: 'date', direction: 'desc' };
let currentUser = { username: 'Guest', balance: 0 };

// Initialize page
document.addEventListener('DOMContentLoaded', async () => {
    // Check authentication
    const isAuth = await checkAuthStatus();
    if (!isAuth) return;
    
    // Load user data and transaction history
    await loadUserData();
    await loadTransactionHistory();
    
    // Setup event listeners
    setupEventListeners();
    
    console.log('History page initialized');
});

/**
 * Check authentication status
 */
async function checkAuthStatus() {
    if (!isAuthenticated()) {
        console.log('Not authenticated, redirecting to login');
        window.location.href = '/login';
        return false;
    }
    return true;
}

/**
 * Get authorization headers for API calls
 */
function getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

/**
 * Load user data for header display
 */
async function loadUserData() {
    try {
        const response = await fetch('/auth/me', {
            method: 'GET',
            headers: getAuthHeaders()
        });

        if (response.ok) {
            const userData = await response.json();
            currentUser = {
                username: userData.username,
                balance: userData.balance
            };
            
            // Update header display
            const usernameElement = document.getElementById('currentUsername');
            const balanceElement = document.getElementById('currentBalance');
            
            if (usernameElement) usernameElement.textContent = `Welcome, ${currentUser.username}!`;
            if (balanceElement) balanceElement.textContent = currentUser.balance.toFixed(2);
        }
    } catch (error) {
        console.error('Error loading user data:', error);
    }
}

/**
 * Load transaction history from /history API
 */
async function loadTransactionHistory() {
    const tableBody = document.getElementById('transactionTableBody');
    const transactionCount = document.getElementById('transactionCount');
    
    // Show loading state
    tableBody.innerHTML = `
        <tr>
            <td colspan="7" class="loading-row">
                <div class="loading-spinner"></div>
                Loading transaction history...
            </td>
        </tr>
    `;
    
    transactionCount.textContent = 'Loading...';

    try {
        console.log('Fetching transaction history from /history API...');
        
        const response = await fetch('/transactions', {
            method: 'GET',
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            if (response.status === 401) {
                handleApiError(response);
                return;
            }
            throw new Error(`History API failed: ${response.status}`);
        }

        const historyData = await response.json();
        console.log('Transaction history loaded:', historyData);

        // Parse the transaction data based on API response format
        allTransactions = parseTransactionData(historyData);
        
        // Apply filters and display
        applyFilters();
        updateSummaryStats();
        renderTransactionTable();
        setupPagination();
        
        console.log(`Loaded ${allTransactions.length} transactions`);

    } catch (error) {
        console.error('Error loading transaction history:', error);
        
        // Show error state
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="loading-row">
                    <span style="color: #dc2626;">
                        ❌ Failed to load transaction history. 
                        <button onclick="loadTransactionHistory()" style="background: none; border: none; color: #3b82f6; cursor: pointer; text-decoration: underline;">
                            Try again
                        </button>
                    </span>
                </td>
            </tr>
        `;
        
        transactionCount.textContent = 'Error loading transactions';
    }
}

/**
 * Parse transaction data from API response
 */
function parseTransactionData(data) {
    // Handle different possible API response formats
    let transactions = [];
    
    if (Array.isArray(data)) {
        transactions = data;
    } else if (data.transactions && Array.isArray(data.transactions)) {
        transactions = data.transactions;
    } else if (data.history && Array.isArray(data.history)) {
        transactions = data.history;
    } else {
        console.warn('Unexpected API response format:', data);
        return [];
    }

    // Normalize transaction data
    return transactions.map((transaction, index) => {
        return {
            id: transaction.id || index,
            date: transaction.date || transaction.timestamp || transaction.created_at || new Date().toISOString(),
            type: transaction.transaction_type || 'unknown',
            ticker: transaction.ticker || transaction.symbol || transaction.stock || 'N/A',
            volume: transaction.volume || transaction.shares || transaction.quantity || 0,
            price: transaction.price_per_unit || 0,
            total: transaction.total_amount || (transaction.volume * transaction.price) || 0,
            status: transaction.status || 'completed'
        };
    });
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Filter controls
    document.getElementById('transactionTypeFilter').addEventListener('change', applyFilters);
    document.getElementById('tickerFilter').addEventListener('input', debounce(applyFilters, 300));
    document.getElementById('dateRangeFilter').addEventListener('change', applyFilters);
    
    // Action buttons
    document.getElementById('refreshHistoryBtn').addEventListener('click', refreshHistory);
    document.getElementById('exportHistoryBtn').addEventListener('click', exportToCSV);
    
    // Table sorting
    document.querySelectorAll('.sortable').forEach(header => {
        header.addEventListener('click', () => {
            const sortField = header.dataset.sort;
            handleSort(sortField);
        });
    });
    
    // Pagination
    document.getElementById('prevPageBtn').addEventListener('click', () => changePage(currentPage - 1));
    document.getElementById('nextPageBtn').addEventListener('click', () => changePage(currentPage + 1));
}

/**
 * Apply filters to transaction data
 */
function applyFilters() {
    const typeFilter = document.getElementById('transactionTypeFilter').value;
    const tickerFilter = document.getElementById('tickerFilter').value.toLowerCase().trim();
    const dateFilter = document.getElementById('dateRangeFilter').value;
    
    filteredTransactions = allTransactions.filter(transaction => {
        // Type filter
        if (typeFilter !== 'all' && transaction.type !== typeFilter) {
            return false;
        }
        
        // Ticker filter
        if (tickerFilter && !transaction.ticker.toLowerCase().includes(tickerFilter)) {
            return false;
        }
        
        // Date filter
        if (dateFilter !== 'all') {
            const transactionDate = new Date(transaction.date);
            const now = new Date();
            
            switch (dateFilter) {
                case 'today':
                    if (transactionDate.toDateString() !== now.toDateString()) return false;
                    break;
                case 'week':
                    const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                    if (transactionDate < weekAgo) return false;
                    break;
                case 'month':
                    const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
                    if (transactionDate < monthAgo) return false;
                    break;
                case 'year':
                    const yearAgo = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000);
                    if (transactionDate < yearAgo) return false;
                    break;
            }
        }
        
        return true;
    });
    
    // Reset to first page and re-render
    currentPage = 1;
    updateSummaryStats();
    renderTransactionTable();
    setupPagination();
}

/**
 * Handle table sorting
 */
function handleSort(field) {
    if (currentSort.field === field) {
        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.field = field;
        currentSort.direction = 'desc';
    }
    
    filteredTransactions.sort((a, b) => {
        let aValue = a[field];
        let bValue = b[field];
        
        // Handle different data types
        if (field === 'date') {
            aValue = new Date(aValue);
            bValue = new Date(bValue);
        } else if (field === 'volume' || field === 'price' || field === 'total') {
            aValue = Number(aValue);
            bValue = Number(bValue);
        } else {
            aValue = String(aValue).toLowerCase();
            bValue = String(bValue).toLowerCase();
        }
        
        if (aValue < bValue) return currentSort.direction === 'asc' ? -1 : 1;
        if (aValue > bValue) return currentSort.direction === 'asc' ? 1 : -1;
        return 0;
    });
    
    // Update sort indicators
    updateSortIndicators();
    renderTransactionTable();
}

/**
 * Update sort indicators in table headers
 */
function updateSortIndicators() {
    document.querySelectorAll('.sortable').forEach(header => {
        const field = header.dataset.sort;
        const indicator = field === currentSort.field ? 
            (currentSort.direction === 'asc' ? ' ↑' : ' ↓') : ' ↕';
        
        header.textContent = header.textContent.replace(/ [↑↓↕]$/, '') + indicator;
    });
}

/**
 * Render transaction table
 */
function renderTransactionTable() {
    const tableBody = document.getElementById('transactionTableBody');
    const transactionCount = document.getElementById('transactionCount');
    const emptyState = document.getElementById('emptyState');
    
    // Calculate pagination
    const startIndex = (currentPage - 1) * transactionsPerPage;
    const endIndex = startIndex + transactionsPerPage;
    const pageTransactions = filteredTransactions.slice(startIndex, endIndex);
    
    // Update transaction count
    const totalCount = filteredTransactions.length;
    transactionCount.textContent = `${totalCount} transaction${totalCount !== 1 ? 's' : ''} found`;
    
    // Show empty state if no transactions
    if (totalCount === 0) {
        tableBody.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }
    
    emptyState.style.display = 'none';
    
    // Render transactions
    tableBody.innerHTML = pageTransactions.map(transaction => {
        const date = new Date(transaction.date);
        const formattedDate = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        
        return `
            <tr>
                <td>${formattedDate}</td>
                <td><span class="transaction-type ${transaction.type}">${transaction.type.toUpperCase()}</span></td>
                <td><span class="stock-symbol">${transaction.ticker}</span></td>
                <td>${transaction.volume.toLocaleString()}</td>
                <td class="price-value">$${Number(transaction.price).toFixed(2)}</td>
                <td class="total-value">${Number(transaction.total).toFixed(2)}</td>
                <td><span class="transaction-status ${transaction.status}">${transaction.status.toUpperCase()}</span></td>
            </tr>
        `;
    }).join('');
}

/**
 * Setup pagination controls
 */
function setupPagination() {
    const totalPages = Math.ceil(filteredTransactions.length / transactionsPerPage);
    const paginationInfo = document.getElementById('paginationInfo');
    const pageNumbers = document.getElementById('pageNumbers');
    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');
    
    // Update pagination info
    const startItem = (currentPage - 1) * transactionsPerPage + 1;
    const endItem = Math.min(currentPage * transactionsPerPage, filteredTransactions.length);
    const totalItems = filteredTransactions.length;
    
    paginationInfo.textContent = totalItems > 0 ? 
        `Showing ${startItem}-${endItem} of ${totalItems} transactions` : 
        'No transactions to display';
    
    // Update navigation buttons
    prevBtn.disabled = currentPage <= 1;
    nextBtn.disabled = currentPage >= totalPages;
    
    // Generate page numbers
    pageNumbers.innerHTML = '';
    if (totalPages > 1) {
        const maxVisiblePages = 5;
        let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
        let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
        
        // Adjust start page if we're near the end
        if (endPage - startPage < maxVisiblePages - 1) {
            startPage = Math.max(1, endPage - maxVisiblePages + 1);
        }
        
        for (let i = startPage; i <= endPage; i++) {
            const pageBtn = document.createElement('button');
            pageBtn.className = `page-number ${i === currentPage ? 'active' : ''}`;
            pageBtn.textContent = i;
            pageBtn.addEventListener('click', () => changePage(i));
            pageNumbers.appendChild(pageBtn);
        }
    }
}

/**
 * Change to specific page
 */
function changePage(page) {
    const totalPages = Math.ceil(filteredTransactions.length / transactionsPerPage);
    
    if (page >= 1 && page <= totalPages) {
        currentPage = page;
        renderTransactionTable();
        setupPagination();
        
        // Scroll to top of table
        document.querySelector('.history-table-container').scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });
    }
}

/**
 * Update summary statistics
 */
function updateSummaryStats() {
    const totalTransactions = filteredTransactions.length;
    const buyOrders = filteredTransactions.filter(t => t.type === 'buy').length;
    const sellOrders = filteredTransactions.filter(t => t.type === 'sell').length;
    const totalVolume = filteredTransactions.reduce((sum, t) => sum + Number(t.total), 0);
    
    document.getElementById('totalTransactions').textContent = totalTransactions.toLocaleString();
    document.getElementById('totalVolume').textContent = totalVolume.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
    document.getElementById('buyOrders').textContent = buyOrders.toLocaleString();
    document.getElementById('sellOrders').textContent = sellOrders.toLocaleString();
}

/**
 * Refresh transaction history
 */
async function refreshHistory() {
    const refreshBtn = document.getElementById('refreshHistoryBtn');
    const originalText = refreshBtn.textContent;
    
    refreshBtn.textContent = '🔄 Refreshing...';
    refreshBtn.disabled = true;
    
    try {
        await loadTransactionHistory();
    } finally {
        refreshBtn.textContent = originalText;
        refreshBtn.disabled = false;
    }
}

/**
 * Export transactions to CSV
 */
function exportToCSV() {
    if (filteredTransactions.length === 0) {
        alert('No transactions to export');
        return;
    }
    
    // Create CSV content
    const headers = ['Date', 'Type', 'Symbol', 'Shares', 'Price', 'Total', 'Status'];
    const csvContent = [
        headers.join(','),
        ...filteredTransactions.map(transaction => {
            const date = new Date(transaction.date).toISOString();
            return [
                date,
                transaction.type,
                transaction.ticker,
                transaction.volume,
                transaction.price,
                transaction.total,
                transaction.status
            ].join(',');
        })
    ].join('\n');
    
    // Create and download file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', `transaction_history_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    console.log('Transaction history exported to CSV');
}

/**
 * Handle API errors (including token expiration)
 */
function handleApiError(response) {
    if (response.status === 401) {
        localStorage.removeItem('access_token');
        sessionStorage.removeItem('loggedInUser');
        window.location.href = '/login';
        return;
    }
    throw new Error(`API Error: ${response.status}`);
}

/**
 * Debounce function for search input
 */
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

/**
 * Utility function to safely check authentication (from common.js)
 */
function isAuthenticated() {
    const token = localStorage.getItem('access_token');
    if (!token) return false;
    
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const currentTime = Math.floor(Date.now() / 1000);
        
        if (payload.exp && payload.exp < currentTime) {
            console.log('Token expired');
            localStorage.removeItem('access_token');
            sessionStorage.removeItem('loggedInUser');
            return false;
        }
        return true;
    } catch (error) {
        return !!token;
    }
}

// Expose functions for debugging
window.historyPageDebug = {
    allTransactions,
    filteredTransactions,
    currentSort,
    refreshHistory,
    loadTransactionHistory
};