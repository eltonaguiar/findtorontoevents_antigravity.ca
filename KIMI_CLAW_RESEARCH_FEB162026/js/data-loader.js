// Data loader for fetching algorithm data from auto-generated backtest results
// Data is produced by generate_dashboard_data.py running in GitHub Actions daily

const DASHBOARD_DATA_URL = 'data/dashboard_data.json';
const LAST_RUN_URL = 'data/last_run.json';

let _cachedData = null;

// Fetch the auto-generated dashboard data from the JSON file
async function fetchAlgorithmData() {
    try {
        const cacheBuster = '?_=' + Date.now();
        const resp = await fetch(DASHBOARD_DATA_URL + cacheBuster);
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        const payload = await resp.json();

        // Validate the payload has the expected shape
        if (!payload || !payload.algorithms || !Array.isArray(payload.algorithms)) {
            throw new Error('Invalid dashboard data format');
        }

        // Ensure each algorithm has a history array (generate if missing)
        payload.algorithms.forEach(function(algo) {
            if (!algo.history || algo.history.length === 0) {
                algo.history = generateHistory(algo.startingValue, algo.currentValue, 30);
            }
            // Backtest strategies use numTrades as the "picks" count
            if (typeof algo.activePicks === 'undefined') {
                algo.activePicks = algo.numTrades || 0;
            }
        });

        // Build activePicks array from algorithm data for the picks table
        if (!payload.activePicks || payload.activePicks.length === 0) {
            payload.activePicks = buildPicksFromAlgorithms(payload.algorithms);
        }

        _cachedData = payload;
        console.log('[DataLoader] Loaded ' + payload.algorithms.length +
            ' algorithms from dashboard_data.json (generated: ' + (payload.generatedAt || 'unknown') + ')');
        return payload;
    } catch (error) {
        console.warn('[DataLoader] Could not load dashboard_data.json: ' + error.message + '. Using fallback.');
        return getFallbackData();
    }
}

// Build a picks-style table from algorithm backtest results
function buildPicksFromAlgorithms(algorithms) {
    var picks = [];
    algorithms.forEach(function(algo) {
        var startVal = algo.startingValue || 100000;
        var curVal = algo.currentValue || startVal;
        var pnl = ((curVal - startVal) / startVal * 100);
        picks.push({
            symbol: algo.asset || algo.id.toUpperCase(),
            algorithm: algo.name,
            category: algo.category,
            entryPrice: startVal,
            currentPrice: Math.round(curVal),
            plPercent: Math.round(pnl * 100) / 100,
            daysHeld: algo.history ? algo.history.length : 30,
            signal: pnl >= 0 ? 'buy' : 'hold'
        });
    });
    return picks;
}

// Check when data was last refreshed
async function fetchLastRunInfo() {
    try {
        var resp = await fetch(LAST_RUN_URL + '?_=' + Date.now());
        if (!resp.ok) return null;
        return await resp.json();
    } catch (e) {
        return null;
    }
}

// Generate realistic price history for chart display
function generateHistory(startValue, endValue, days) {
    var history = [];
    var now = new Date();
    var currentValue = startValue;
    var dailyReturn = Math.pow(endValue / startValue, 1 / days) - 1;

    for (var i = days; i >= 0; i--) {
        var date = new Date(now);
        date.setDate(date.getDate() - i);

        var randomFactor = 0.02;
        var randomReturn = (Math.random() - 0.5) * 2 * randomFactor;
        var trendReturn = dailyReturn + randomReturn;
        currentValue = currentValue * (1 + trendReturn);

        history.push({
            date: date.toISOString(),
            value: Math.round(currentValue * 100) / 100
        });
    }

    history[history.length - 1].value = endValue;
    return history;
}

// Minimal fallback data shown while waiting for first backtest run
function getFallbackData() {
    return {
        algorithms: [
            {
                id: 'loading',
                name: 'Awaiting First Backtest Run',
                category: 'stock',
                avatar: '⏳',
                asset: '--',
                description: 'Backtest data will appear after the next GitHub Actions run.',
                startingValue: 100000,
                currentValue: 100000,
                totalReturn: 0,
                annualizedReturn: 0,
                winRate: 0,
                sharpeRatio: 0,
                sortinoRatio: 0,
                maxDrawdown: 0,
                calmarRatio: 0,
                profitFactor: 0,
                numTrades: 0,
                avgTradeReturn: 0,
                volatility: 0,
                activePicks: 0,
                status: 'PENDING',
                history: generateHistory(100000, 100000, 30)
            }
        ],
        activePicks: [],
        summary: {
            totalAlgorithms: 0,
            averageReturn: 0,
            lastUpdated: new Date().toISOString(),
            dataSource: 'Awaiting first run...'
        }
    };
}

// Get category display name
function getCategoryName(category) {
    var names = {
        stock: 'Stocks',
        penny: 'Penny Stocks',
        crypto: 'Crypto',
        meme: 'Meme Coins',
        forex: 'Forex'
    };
    return names[category] || category;
}

// Get category icon
function getCategoryIcon(category) {
    var icons = {
        stock: '📈',
        penny: '💎',
        crypto: '₿',
        meme: '🚀',
        forex: '💱'
    };
    return icons[category] || '📊';
}
