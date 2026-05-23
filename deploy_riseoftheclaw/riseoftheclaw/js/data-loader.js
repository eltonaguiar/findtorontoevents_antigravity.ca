// Data loader for fetching algorithm data
const API_ENDPOINTS = {
    stocks: '/findstocks/portfolio2/api/picks.php',
    crypto: '/findcryptopairs/api/winners.php',
    meme: '/findcryptopairs/api/meme_scanner.php',
    forex: '/findforex2/api/signals.php',
    penny: '/findstocks/portfolio2/api/penny_stock_picks.php'
};

// Sample data for initial load (will be replaced with real API calls)
const SAMPLE_DATA = {
    algorithms: [
        {
            id: 'etf-masters',
            name: 'ETF Masters',
            category: 'stock',
            avatar: '📊',
            startingValue: 10000,
            currentValue: 11850,
            totalReturn: 18.50,
            winRate: 82.35,
            activePicks: 5,
            sharpeRatio: 1.32,
            maxDrawdown: -8.2,
            history: generateHistory(10000, 11850, 30)
        },
        {
            id: 'blue-chip-growth',
            name: 'Blue Chip Growth',
            category: 'stock',
            avatar: '💎',
            startingValue: 10000,
            currentValue: 11240,
            totalReturn: 12.40,
            winRate: 80.00,
            activePicks: 8,
            sharpeRatio: 0.98,
            maxDrawdown: -5.5,
            history: generateHistory(10000, 11240, 30)
        },
        {
            id: 'sector-rotation',
            name: 'Sector Rotation',
            category: 'stock',
            avatar: '🔄',
            startingValue: 10000,
            currentValue: 10980,
            totalReturn: 9.80,
            winRate: 72.73,
            activePicks: 4,
            sharpeRatio: 0.70,
            maxDrawdown: -12.3,
            history: generateHistory(10000, 10980, 30)
        },
        {
            id: 'can-slim',
            name: 'CAN SLIM',
            category: 'stock',
            avatar: '📈',
            startingValue: 10000,
            currentValue: 9850,
            totalReturn: -1.50,
            winRate: 38.39,
            activePicks: 6,
            sharpeRatio: -0.07,
            maxDrawdown: -18.5,
            history: generateHistory(10000, 9850, 30)
        },
        {
            id: 'composite-rating',
            name: 'Composite Rating',
            category: 'stock',
            avatar: '⭐',
            startingValue: 10000,
            currentValue: 10350,
            totalReturn: 3.50,
            winRate: 52.75,
            activePicks: 3,
            sharpeRatio: 17.91,
            maxDrawdown: -3.2,
            history: generateHistory(10000, 10350, 30)
        },
        {
            id: 'technical-momentum',
            name: 'Technical Momentum',
            category: 'stock',
            avatar: '🚀',
            startingValue: 10000,
            currentValue: 10720,
            totalReturn: 7.20,
            winRate: 65.00,
            activePicks: 7,
            sharpeRatio: 0.85,
            maxDrawdown: -9.8,
            history: generateHistory(10000, 10720, 30)
        },
        {
            id: 'alpha-predator',
            name: 'Alpha Predator',
            category: 'stock',
            avatar: '🦁',
            startingValue: 10000,
            currentValue: 9450,
            totalReturn: -5.50,
            winRate: 22.11,
            activePicks: 12,
            sharpeRatio: -0.09,
            maxDrawdown: -25.4,
            history: generateHistory(10000, 9450, 30)
        },
        {
            id: 'penny-tracker',
            name: 'Penny Stock Tracker',
            category: 'penny',
            avatar: '💰',
            startingValue: 10000,
            currentValue: 12500,
            totalReturn: 25.00,
            winRate: 68.50,
            activePicks: 15,
            sharpeRatio: 1.45,
            maxDrawdown: -15.2,
            history: generateHistory(10000, 12500, 30)
        },
        {
            id: 'crypto-winners',
            name: 'Crypto Winners Scanner',
            category: 'crypto',
            avatar: '₿',
            startingValue: 10000,
            currentValue: 13200,
            totalReturn: 32.00,
            winRate: 71.20,
            activePicks: 8,
            sharpeRatio: 1.68,
            maxDrawdown: -22.5,
            history: generateHistory(10000, 13200, 30)
        },
        {
            id: 'rsi-mean-reversion',
            name: 'RSI Mean Reversion',
            category: 'crypto',
            avatar: '📉',
            startingValue: 10000,
            currentValue: 10850,
            totalReturn: 8.50,
            winRate: 58.30,
            activePicks: 6,
            sharpeRatio: 0.72,
            maxDrawdown: -14.8,
            history: generateHistory(10000, 10850, 30)
        },
        {
            id: 'macd-crossover',
            name: 'MACD Crossover',
            category: 'crypto',
            avatar: '📊',
            startingValue: 10000,
            currentValue: 11100,
            totalReturn: 11.00,
            winRate: 61.50,
            activePicks: 5,
            sharpeRatio: 0.88,
            maxDrawdown: -11.2,
            history: generateHistory(10000, 11100, 30)
        },
        {
            id: 'bollinger-squeeze',
            name: 'Bollinger Band Squeeze',
            category: 'crypto',
            avatar: '🎯',
            startingValue: 10000,
            currentValue: 10600,
            totalReturn: 6.00,
            winRate: 55.80,
            activePicks: 4,
            sharpeRatio: 0.65,
            maxDrawdown: -13.5,
            history: generateHistory(10000, 10600, 30)
        },
        {
            id: 'triple-ema',
            name: 'Triple EMA Crossover',
            category: 'crypto',
            avatar: '📈',
            startingValue: 10000,
            currentValue: 11400,
            totalReturn: 14.00,
            winRate: 64.20,
            activePicks: 7,
            sharpeRatio: 1.05,
            maxDrawdown: -10.8,
            history: generateHistory(10000, 11400, 30)
        },
        {
            id: 'ichimoku-cloud',
            name: 'Ichimoku Cloud',
            category: 'crypto',
            avatar: '☁️',
            startingValue: 10000,
            currentValue: 10900,
            totalReturn: 9.00,
            winRate: 59.40,
            activePicks: 5,
            sharpeRatio: 0.78,
            maxDrawdown: -12.0,
            history: generateHistory(10000, 10900, 30)
        },
        {
            id: 'momentum-btc',
            name: 'Momentum + BTC Regime',
            category: 'crypto',
            avatar: '🌊',
            startingValue: 10000,
            currentValue: 12100,
            totalReturn: 21.00,
            winRate: 67.80,
            activePicks: 6,
            sharpeRatio: 1.25,
            maxDrawdown: -16.5,
            history: generateHistory(10000, 12100, 30)
        },
        {
            id: 'stochrsi-volume',
            name: 'StochRSI + Volume',
            category: 'crypto',
            avatar: '📊',
            startingValue: 10000,
            currentValue: 10750,
            totalReturn: 7.50,
            winRate: 56.90,
            activePicks: 8,
            sharpeRatio: 0.68,
            maxDrawdown: -14.2,
            history: generateHistory(10000, 10750, 30)
        },
        {
            id: 'funding-contrarian',
            name: 'Funding Rate Contrarian',
            category: 'crypto',
            avatar: '🔄',
            startingValue: 10000,
            currentValue: 11300,
            totalReturn: 13.00,
            winRate: 62.10,
            activePicks: 4,
            sharpeRatio: 0.92,
            maxDrawdown: -11.8,
            history: generateHistory(10000, 11300, 30)
        },
        {
            id: 'whale-accumulation',
            name: 'Whale Accumulation',
            category: 'crypto',
            avatar: '🐋',
            startingValue: 10000,
            currentValue: 11600,
            totalReturn: 16.00,
            winRate: 65.50,
            activePicks: 5,
            sharpeRatio: 1.12,
            maxDrawdown: -13.0,
            history: generateHistory(10000, 11600, 30)
        },
        {
            id: 'meme-scanner',
            name: 'Meme Coin Scanner',
            category: 'meme',
            avatar: '🚀',
            startingValue: 10000,
            currentValue: 15800,
            totalReturn: 58.00,
            winRate: 45.20,
            activePicks: 20,
            sharpeRatio: 1.85,
            maxDrawdown: -35.5,
            history: generateHistory(10000, 15800, 30)
        },
        {
            id: 'ml-meme',
            name: 'ML-Enhanced Meme Signals',
            category: 'meme',
            avatar: '🤖',
            startingValue: 10000,
            currentValue: 14200,
            totalReturn: 42.00,
            winRate: 52.80,
            activePicks: 12,
            sharpeRatio: 1.62,
            maxDrawdown: -28.3,
            history: generateHistory(10000, 14200, 30)
        },
        {
            id: 'forex-scanner',
            name: 'Forex Scanner',
            category: 'forex',
            avatar: '💱',
            startingValue: 10000,
            currentValue: 10500,
            totalReturn: 5.00,
            winRate: 54.30,
            activePicks: 6,
            sharpeRatio: 0.58,
            maxDrawdown: -8.5,
            history: generateHistory(10000, 10500, 30)
        }
    ],
    activePicks: [
        { symbol: 'AAPL', algorithm: 'ETF Masters', category: 'stock', entryPrice: 185.50, currentPrice: 192.30, plPercent: 3.67, daysHeld: 12, signal: 'buy' },
        { symbol: 'MSFT', algorithm: 'Blue Chip Growth', category: 'stock', entryPrice: 380.20, currentPrice: 395.80, plPercent: 4.10, daysHeld: 15, signal: 'buy' },
        { symbol: 'NVDA', algorithm: 'Technical Momentum', category: 'stock', entryPrice: 485.00, currentPrice: 520.40, plPercent: 7.30, daysHeld: 8, signal: 'buy' },
        { symbol: 'BTC', algorithm: 'Crypto Winners Scanner', category: 'crypto', entryPrice: 42500, currentPrice: 48200, plPercent: 13.41, daysHeld: 20, signal: 'buy' },
        { symbol: 'ETH', algorithm: 'Triple EMA Crossover', category: 'crypto', entryPrice: 2550, currentPrice: 2780, plPercent: 9.02, daysHeld: 14, signal: 'buy' },
        { symbol: 'DOGE', algorithm: 'Meme Coin Scanner', category: 'meme', entryPrice: 0.078, currentPrice: 0.095, plPercent: 21.79, daysHeld: 5, signal: 'buy' },
        { symbol: 'SHIB', algorithm: 'ML-Enhanced Meme Signals', category: 'meme', entryPrice: 0.0000085, currentPrice: 0.0000112, plPercent: 31.76, daysHeld: 7, signal: 'buy' },
        { symbol: 'PEPE', algorithm: 'Meme Coin Scanner', category: 'meme', entryPrice: 0.0000012, currentPrice: 0.0000015, plPercent: 25.00, daysHeld: 3, signal: 'buy' },
        { symbol: 'EURUSD', algorithm: 'Forex Scanner', category: 'forex', entryPrice: 1.0850, currentPrice: 1.0920, plPercent: 0.65, daysHeld: 10, signal: 'buy' },
        { symbol: 'GBPUSD', algorithm: 'Forex Scanner', category: 'forex', entryPrice: 1.2650, currentPrice: 1.2580, plPercent: -0.55, daysHeld: 8, signal: 'sell' },
        { symbol: 'SOL', algorithm: 'Whale Accumulation', category: 'crypto', entryPrice: 98.50, currentPrice: 112.30, plPercent: 14.01, daysHeld: 11, signal: 'buy' },
        { symbol: 'XRP', algorithm: 'Funding Rate Contrarian', category: 'crypto', entryPrice: 0.58, currentPrice: 0.62, plPercent: 6.90, daysHeld: 16, signal: 'buy' },
        { symbol: 'PEPE2', algorithm: 'Meme Coin Scanner', category: 'meme', entryPrice: 0.00000085, currentPrice: 0.00000105, plPercent: 23.53, daysHeld: 4, signal: 'buy' },
        { symbol: 'FLOKI', algorithm: 'ML-Enhanced Meme Signals', category: 'meme', entryPrice: 0.000035, currentPrice: 0.000042, plPercent: 20.00, daysHeld: 6, signal: 'buy' },
        { symbol: 'BONK', algorithm: 'Meme Coin Scanner', category: 'meme', entryPrice: 0.000012, currentPrice: 0.000015, plPercent: 25.00, daysHeld: 5, signal: 'buy' }
    ]
};

// Generate realistic price history
function generateHistory(startValue, endValue, days) {
    const history = [];
    const now = new Date();
    let currentValue = startValue;
    const dailyReturn = Math.pow(endValue / startValue, 1 / days) - 1;
    
    for (let i = days; i >= 0; i--) {
        const date = new Date(now);
        date.setDate(date.getDate() - i);
        
        // Add some randomness to the trend
        const randomFactor = 0.02; // 2% daily volatility
        const randomReturn = (Math.random() - 0.5) * 2 * randomFactor;
        const trendReturn = dailyReturn + randomReturn;
        
        currentValue = currentValue * (1 + trendReturn);
        
        history.push({
            date: date.toISOString(),
            value: Math.round(currentValue * 100) / 100
        });
    }
    
    // Ensure final value matches
    history[history.length - 1].value = endValue;
    
    return history;
}

// Fetch data from APIs
async function fetchAlgorithmData() {
    try {
        // Load from local JSON files
        const [algoResponse, picksResponse] = await Promise.all([
            fetch('data/algorithms.json'),
            fetch('data/active_picks.json')
        ]);

        if (!algoResponse.ok || !picksResponse.ok) {
            console.warn('Failed to load data files, using sample data');
            return SAMPLE_DATA;
        }

        const algoData = await algoResponse.json();
        const picksData = await picksResponse.json();

        // Generate history for each algorithm
        const algorithmsWithHistory = algoData.algorithms.map(algo => ({
            ...algo,
            history: generateHistory(algo.startingValue, algo.currentValue, 30)
        }));

        return {
            algorithms: algorithmsWithHistory,
            activePicks: picksData.activePicks || []
        };
    } catch (error) {
        console.error('Error fetching algorithm data:', error);
        return SAMPLE_DATA;
    }
}

// Get category display name
function getCategoryName(category) {
    const names = {
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
    const icons = {
        stock: '📈',
        penny: '💎',
        crypto: '₿',
        meme: '🚀',
        forex: '💱'
    };
    return icons[category] || '📊';
}
