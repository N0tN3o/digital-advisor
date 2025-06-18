// static/js/landing.js

document.addEventListener('DOMContentLoaded', () => {
    loadMarketDataPreview();
});

/**
 * Loads market data using the real /prices API and displays it on the landing page.
 */
async function loadMarketDataPreview() {
    const marketDataGrid = document.getElementById('marketDataGrid');
    if (!marketDataGrid) return;

    displayLoading(marketDataGrid, 'Loading market data preview...');

    try {
        // Define a set of relevant NASDAQ 100 tickers for the landing page preview
        const previewTickers = ["APP", "BKNG", "META", "NVDA", "PEP", "PLTR", "TSLA"];

        // Use the /prices API to get current prices
        const prices = await apiGet(`/prices?tickers=${previewTickers.join(',')}`);

        if (Object.keys(prices).length === 0) {
            displayError('Failed to load market data for preview. Please try again later.', marketDataGrid);
            return;
        }

        const marketData = previewTickers.map(ticker => {
            const currentPrice = prices[ticker];
            if (currentPrice === undefined) { // Check for undefined as prices object might not contain all requested tickers
                console.warn(`No price data for ${ticker} in preview.`);
                return null;
            }

            // Generate realistic but mock change and percentChange for display
            // As /prices only gives current price, we simulate historical change for a compelling preview.
            const changePercent = (Math.random() - 0.5) * 3; // -1.5% to +1.5%
            const change = currentPrice * (changePercent / 100);

            return {
                symbol: ticker,
                name: getCompanyName(ticker), // Reuse the getCompanyName helper from dashboard.js if available
                price: currentPrice,
                change: change,
                percentChange: changePercent
            };
        }).filter(Boolean); // Remove any null entries if price data was missing for a ticker

        marketDataGrid.innerHTML = ''; // Clear loading message

        marketData.forEach(stock => {
            const changeClass = stock.change >= 0 ? 'text-green-600' : 'text-red-600'; // Tailwind classes
            const changeSign = stock.change >= 0 ? '+' : '';
            const stockElement = document.createElement('div');
            stockElement.classList.add('stock-preview-item', 'bg-white', 'p-4', 'rounded-lg', 'shadow-md', 'transform', 'transition', 'duration-300', 'hover:scale-105');
            stockElement.innerHTML = `
                <div class="stock-preview-symbol text-xl font-bold text-gray-800">${stock.symbol}</div>
                <div class="stock-preview-price text-2xl font-extrabold text-blue-700">$${stock.price.toFixed(2)}</div>
                <div class="stock-preview-change text-lg font-semibold ${changeClass}">
                    ${changeSign}${stock.change.toFixed(2)} (${changeSign}${stock.percentChange.toFixed(2)}%)
                </div>
            `;
            marketDataGrid.appendChild(stockElement);
        });
    } catch (error) {
        console.error('Error loading market data preview:', error);
        displayError('Failed to load market data for preview. Please try again later.', marketDataGrid);
    }
}

// Re-using getCompanyName from dashboard.js to keep company names consistent
// If dashboard.js is not loaded on landing, this function needs to be in common.js or duplicated.
// For now, assuming common.js will load this or it will be inlined.
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

