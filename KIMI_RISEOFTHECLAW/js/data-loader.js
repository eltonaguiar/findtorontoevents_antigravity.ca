// Rise of the Claw - Data Loader
// NO FAKE DATA. Delegates to data-mode-switcher for LIVE vs BACKTEST.

/**
 * Main entry point - delegates to mode switcher if available
 */
async function fetchAlgorithmData() {
    // Use the mode switcher (loaded before this file)
    if (typeof fetchDataByMode === 'function') {
        return await fetchDataByMode();
    }

    // Fallback: try to load directly from JSON files
    console.warn('[DataLoader] Mode switcher not found, loading directly');
    try {
        var cacheBust = '?_=' + Date.now();
        var resp = await fetch('data/algorithms.json' + cacheBust);
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        var data = await resp.json();

        var algorithms = (data.algorithms || []).map(function(algo) {
            if (!algo.history || algo.history.length === 0) {
                algo.history = generateFlatHistory(algo.startingValue || 10000, 7);
            }
            if (typeof algo.winRate !== 'number') algo.winRate = 0;
            if (typeof algo.sharpeRatio !== 'number') algo.sharpeRatio = 0;
            if (typeof algo.maxDrawdown !== 'number') algo.maxDrawdown = 0;
            if (typeof algo.activePicks !== 'number') algo.activePicks = 0;
            return algo;
        });

        return {
            dataType: data.dataType || 'FORWARD_TEST',
            algorithms: algorithms,
            activePicks: [],
            auditTrail: []
        };
    } catch (err) {
        console.warn('[DataLoader] Direct load failed:', err.message);
        return { dataType: 'UNKNOWN', algorithms: [], activePicks: [], auditTrail: [] };
    }
}

// Flat history for algorithms with no trades yet
function generateFlatHistory(value, days) {
    var history = [];
    var now = new Date();
    for (var i = days; i >= 0; i--) {
        var d = new Date(now);
        d.setDate(d.getDate() - i);
        history.push({ date: d.toISOString(), value: value });
    }
    return history;
}

// Category utilities
function getCategoryName(category) {
    var names = { stock: 'Stocks', penny: 'Penny Stocks', crypto: 'Crypto', meme: 'Meme Coins', forex: 'Forex' };
    return names[category] || category;
}

function getCategoryIcon(category) {
    var icons = { stock: '📈', penny: '💎', crypto: '₿', meme: '🚀', forex: '💱' };
    return icons[category] || '📊';
}
