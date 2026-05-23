// Main dashboard logic
let currentData = null;
let refreshInterval = null;
let currentCategory = 'all';
let currentSort = 'return';

// ── Live Price Refresh via CoinGecko ──
const SYMBOL_TO_COINGECKO = {
    'BTC-USD': 'bitcoin', 'ETH-USD': 'ethereum', 'SOL-USD': 'solana',
    'DOGE-USD': 'dogecoin', 'ADA-USD': 'cardano', 'XRP-USD': 'ripple',
    'DOT-USD': 'polkadot', 'AVAX-USD': 'avalanche-2', 'LINK-USD': 'chainlink',
    'ATOM-USD': 'cosmos', 'NEAR-USD': 'near', 'FIL-USD': 'filecoin',
    'SHIB-USD': 'shiba-inu', 'PEPE-USD': 'pepe', 'WIF-USD': 'dogwifcoin',
    'BONK-USD': 'bonk', 'MATIC-USD': 'matic-network', 'ARB-USD': 'arbitrum',
    'OP-USD': 'optimism', 'APT-USD': 'aptos', 'SUI-USD': 'sui',
    'INJ-USD': 'injective-protocol', 'TIA-USD': 'celestia',
    'RENDER-USD': 'render-token', 'FET-USD': 'fetch-ai',
    'RNDR-USD': 'render-token', 'COIN': 'bitcoin',
};

async function refreshLivePrices() {
    if (!currentData || !currentData.algorithms) return;
    // Collect all symbols from active picks
    const symbols = new Set();
    currentData.algorithms.forEach(function(algo) {
        (algo.activePicks || []).forEach(function(p) {
            const sym = (p.symbol || p.pair || '').toUpperCase();
            if (sym && SYMBOL_TO_COINGECKO[sym]) symbols.add(sym);
        });
    });
    if (symbols.size === 0) return;
    const cgIds = [...symbols].map(s => SYMBOL_TO_COINGECKO[s]).filter(Boolean);
    const unique = [...new Set(cgIds)];
    if (unique.length === 0) return;
    try {
        const resp = await fetch('https://api.coingecko.com/api/v3/simple/price?ids=' + unique.join(',') + '&vs_currencies=usd', {cache: 'no-store'});
        if (!resp.ok) return;
        const prices = await resp.json();
        // Build symbol → price map
        const priceMap = {};
        for (const sym of symbols) {
            const cgId = SYMBOL_TO_COINGECKO[sym];
            if (cgId && prices[cgId] && prices[cgId].usd) {
                priceMap[sym] = prices[cgId].usd;
            }
        }
        // Update active picks in-place
        let updated = 0;
        currentData.algorithms.forEach(function(algo) {
            (algo.activePicks || []).forEach(function(p) {
                const sym = (p.symbol || p.pair || '').toUpperCase();
                if (priceMap[sym]) {
                    p.currentPrice = priceMap[sym];
                    const entry = p.entryPrice || 0;
                    if (entry > 0) p.pnlPct = ((priceMap[sym] - entry) / entry * 100);
                    updated++;
                }
            });
        });
        if (updated > 0) {
            console.log('[PriceRefresh] Updated ' + updated + ' active pick prices');
            renderActivePicks(currentData);
        }
    } catch (e) {
        console.warn('[PriceRefresh] CoinGecko fetch failed:', e.message);
    }
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', async () => {
    await loadDashboardData();
    // Refresh live prices immediately, then every 2 minutes
    setTimeout(refreshLivePrices, 2000);
    setInterval(refreshLivePrices, 120000);
    startAutoRefresh();
    updateLastUpdated();
});

// Load dashboard data
async function loadDashboardData() {
    try {
        currentData = await fetchAlgorithmData();
        
        // Filter by time range
        const filteredData = filterDataByTimeRange(currentData, currentTimeRange);
        
        // Update all sections
        updatePerformanceCards(filteredData);
        initPortfolioChart(filteredData);
        renderLeaderboard(filteredData);
        renderActivePicks(filteredData);
        renderCategoryBreakdown(filteredData);
        
        updateLastUpdated();
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

// Update performance cards
function updatePerformanceCards(data) {
    const algorithms = data.algorithms;

    if (!algorithms || algorithms.length === 0) {
        console.warn('No algorithms data available');
        document.getElementById('topPerformer').textContent = 'Waiting for data...';
        document.getElementById('topPerformerReturn').textContent = '0%';
        document.getElementById('bestWinRate').textContent = '0%';
        document.getElementById('bestWinRateAlgo').textContent = 'Waiting for data...';
        document.getElementById('mostActive').textContent = 'Waiting for data...';
        document.getElementById('mostActiveCount').textContent = '0 picks';
        document.getElementById('bestSharpe').textContent = '0.00';
        document.getElementById('bestSharpeAlgo').textContent = 'Waiting for data...';
        document.getElementById('lowestDrawdown').textContent = '0%';
        document.getElementById('lowestDrawdownAlgo').textContent = 'Waiting for data...';
        return;
    }

    const topPerformer = algorithms.reduce((best, algo) =>
        algo.totalReturn > best.totalReturn ? algo : best, algorithms[0]);
    document.getElementById('topPerformer').textContent = topPerformer.name;
    document.getElementById('topPerformerReturn').textContent =
        (topPerformer.totalReturn >= 0 ? '+' : '') + topPerformer.totalReturn.toFixed(2) + '%';
    document.getElementById('topPerformerReturn').className =
        'perf-sub ' + (topPerformer.totalReturn >= 0 ? 'return-positive' : 'return-negative');

    const bestWinRate = algorithms.reduce((best, algo) =>
        algo.winRate > best.winRate ? algo : best, algorithms[0]);
    document.getElementById('bestWinRate').textContent = bestWinRate.winRate.toFixed(1) + '%';
    document.getElementById('bestWinRateAlgo').textContent = bestWinRate.name;

    const mostActive = algorithms.reduce((most, algo) =>
        algo.activePicks > most.activePicks ? algo : most, algorithms[0]);
    document.getElementById('mostActive').textContent = mostActive.name;
    document.getElementById('mostActiveCount').textContent = mostActive.activePicks + ' picks';

    const bestSharpe = algorithms.reduce((best, algo) =>
        algo.sharpeRatio > best.sharpeRatio ? algo : best, algorithms[0]);
    document.getElementById('bestSharpe').textContent = bestSharpe.sharpeRatio.toFixed(2);
    document.getElementById('bestSharpeAlgo').textContent = bestSharpe.name;

    const lowestDrawdown = algorithms.reduce((best, algo) =>
        algo.maxDrawdown > best.maxDrawdown ? algo : best, algorithms[0]);
    document.getElementById('lowestDrawdown').textContent = lowestDrawdown.maxDrawdown.toFixed(1) + '%';
    document.getElementById('lowestDrawdownAlgo').textContent = lowestDrawdown.name;
}

// Render leaderboard
function renderLeaderboard(data) {
    var algorithms = data.algorithms.slice();
    
    if (currentCategory !== 'all') {
        algorithms = algorithms.filter(function(a) { return a.category === currentCategory; });
    }
    
    algorithms.sort(function(a, b) {
        switch(currentSort) {
            case 'return': return b.totalReturn - a.totalReturn;
            case 'winRate': return b.winRate - a.winRate;
            case 'sharpe': return b.sharpeRatio - a.sharpeRatio;
            case 'value': return b.currentValue - a.currentValue;
            default: return b.totalReturn - a.totalReturn;
        }
    });
    
    var tbody = document.getElementById('leaderboardBody');
    
    if (algorithms.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="loading-cell">No algorithms found for this category.</td></tr>';
        return;
    }
    
    var isLive = currentData && currentData.dataType === 'FORWARD_TEST';

    tbody.innerHTML = algorithms.map(function(algo, index) {
        var rank = index + 1;
        var rankClass = rank === 1 ? 'gold' : rank === 2 ? 'silver' : rank === 3 ? 'bronze' : '';
        var rowClass = rank <= 3 ? 'rank-' + rank : '';
        var returnClass = algo.totalReturn >= 0 ? 'return-positive' : 'return-negative';
        var hasTraded = algo.totalReturn !== 0 || (algo.activePicks || 0) > 0;

        var statusCol = '';
        if (isLive && !hasTraded) {
            statusCol = '<span style="color: #60a5fa; font-size: 11px;" title="' + (algo.nextAction || 'Scanning') + '">🔍 Scanning</span>';
        } else {
            var sparklineData = (algo.history || []).slice(-7).map(function(h) { return h.value; });
            if (sparklineData.length >= 2 && sparklineData[0] > 0) {
                var trend = ((sparklineData[sparklineData.length-1] - sparklineData[0]) / sparklineData[0] * 100);
                var trendClass = trend >= 0 ? 'return-positive' : 'return-negative';
                statusCol = '<span class="' + trendClass + '">' + (trend >= 0 ? '+' : '') + trend.toFixed(1) + '%</span>';
            } else {
                statusCol = '<span style="color: #8888aa;">--</span>';
            }
        }

        var tierLabel = algo.tier === 'TIER_1' ? '<span style="background:#2563eb;color:#fff;padding:1px 6px;border-radius:4px;font-size:10px;margin-left:4px;" title="Validated academic strategy">T1</span>' :
                       algo.tier === 'SCOUT' ? '<span style="background:#6b7280;color:#fff;padding:1px 6px;border-radius:4px;font-size:10px;margin-left:4px;" title="Simple supplementary signal">Scout</span>' : '';

        return '<tr class="' + rowClass + '" onclick="showAlgorithmDetails(\'' + algo.id + '\')" style="cursor: pointer;">' +
            '<td><div class="rank-badge ' + rankClass + '">' + rank + '</div></td>' +
            '<td><div class="algo-name-cell"><div class="algo-avatar">' + (algo.avatar || '📊') + '</div><div class="algo-info"><div class="algo-name">' + algo.name + tierLabel + '</div><div class="algo-category">' + getCategoryName(algo.category) + '</div></div></div></td>' +
            '<td><span class="category-badge ' + algo.category + '">' + getCategoryName(algo.category) + '</span></td>' +
            '<td>$' + (algo.currentValue || 0).toLocaleString() + '</td>' +
            '<td class="' + returnClass + '">' + (algo.totalReturn >= 0 ? '+' : '') + (algo.totalReturn || 0).toFixed(2) + '%</td>' +
            '<td>' + (algo.winRate || 0).toFixed(1) + '%</td>' +
            '<td>' + (algo.activePicks || 0) + '</td>' +
            '<td>' + (algo.sharpeRatio || 0).toFixed(2) + '</td>' +
            '<td style="color: ' + ((algo.maxDrawdown || 0) < -15 ? '#ef4444' : '#8888aa') + '">' + (algo.maxDrawdown || 0).toFixed(1) + '%</td>' +
            '<td>' + statusCol + '</td>' +
        '</tr>';
    }).join('');
}

// Format UTC date string to EST timezone for display
function formatEST(isoStr) {
    if (!isoStr) return '--';
    try {
        var d = new Date(isoStr);
        if (isNaN(d.getTime())) return isoStr;
        return d.toLocaleString('en-US', {
            timeZone: 'America/New_York',
            month: 'short', day: 'numeric', year: 'numeric',
            hour: 'numeric', minute: '2-digit', second: '2-digit',
            hour12: true
        }) + ' EST';
    } catch (e) { return isoStr; }
}

// Render active picks - ONLY real trades with full transparency
function renderActivePicks(data) {
    var tbody = document.getElementById('picksBody');
    var picks = (data.activePicks || []).slice();
    var isLive = data.dataType === 'FORWARD_TEST';
    var isBacktest = data.dataType === 'BACKTEST';

    var categoryFilter = document.getElementById('pickCategoryFilter');
    var catVal = categoryFilter ? categoryFilter.value : 'all';
    if (catVal !== 'all') {
        picks = picks.filter(function(p) { return p.category === catVal; });
    }

    var searchEl = document.getElementById('pickSearch');
    var searchTerm = searchEl ? searchEl.value.toLowerCase() : '';
    if (searchTerm) {
        picks = picks.filter(function(p) {
            return p.symbol.toLowerCase().indexOf(searchTerm) !== -1 ||
                   p.algorithm.toLowerCase().indexOf(searchTerm) !== -1;
        });
    }

    if (picks.length === 0) {
        var msg = '';
        if (isLive) {
            msg = '<div style="padding: 30px; text-align: center;">' +
                '<div style="font-size: 36px; margin-bottom: 12px;">🔍</div>' +
                '<div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">No Active Picks Yet</div>' +
                '<div style="font-size: 13px; color: #8888aa; max-width: 500px; margin: 0 auto; line-height: 1.6;">' +
                    'All algorithms are actively scanning. Picks appear when entry conditions are met.</div>' +
                '<div style="margin-top: 12px; font-size: 12px; color: #60a5fa;">' +
                    'Click the <strong>🔴 LIVE FORWARD TEST</strong> badge for the audit trail.</div></div>';
        } else if (isBacktest) {
            msg = '<div style="padding: 20px; text-align: center; color: #8888aa;">' +
                'Backtest summary in the leaderboard above. Trade logs: <a href="/kimi-claw/data/tier1_summary.json" target="_blank" style="color: #f59e0b;">tier1_summary.json</a>.</div>';
        } else {
            msg = 'No active picks found.';
        }
        tbody.innerHTML = '<tr><td colspan="11" class="loading-cell">' + msg + '</td></tr>';
        return;
    }

    tbody.innerHTML = picks.map(function(pick) {
        var entry = pick.entryPrice || 0;
        var current = pick.currentPrice || entry;
        var plPct = entry > 0 ? ((current - entry) / entry) * 100 : 0;
        var plVal = pick.plValue || (pick.shares ? (current - entry) * pick.shares : 0);
        var plClass = plPct >= 0 ? 'return-positive' : 'return-negative';
        var sig = (pick.signal || '').toLowerCase();
        var signalClass = sig === 'buy' ? 'buy' : sig === 'sell' ? 'sell' : 'hold';

        var fmtPrice = function(p) {
            if (typeof p !== 'number') return p || '--';
            if (p >= 1000) return '$' + p.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
            if (p >= 1) return '$' + p.toFixed(2);
            return '$' + p.toFixed(6);
        };

        return '<tr onclick="showAlgorithmDetails(\'' + (pick.algorithmId || '') + '\')" style="cursor:pointer;" title="Click for full audit">' +
            '<td><strong>' + pick.symbol + '</strong></td>' +
            '<td>' + pick.algorithm + '</td>' +
            '<td><span class="category-badge ' + pick.category + '">' + getCategoryName(pick.category) + '</span></td>' +
            '<td style="font-size:12px; white-space:nowrap;">' + formatEST(pick.entryDate) + '</td>' +
            '<td>' + fmtPrice(entry) + '</td>' +
            '<td>' + fmtPrice(current) + '</td>' +
            '<td class="' + plClass + '" style="font-weight:600;">' + (plPct >= 0 ? '+' : '') + plPct.toFixed(2) + '%</td>' +
            '<td class="' + plClass + '">' + (plVal >= 0 ? '+' : '') + '$' + Math.abs(plVal).toFixed(2) + '</td>' +
            '<td>' + (pick.daysHeld || 0) + 'd</td>' +
            '<td><span class="signal-badge ' + signalClass + '">' + (pick.signal || 'hold').toUpperCase() + '</span></td>' +
            '<td style="font-size:12px; color:#8888aa; max-width:200px;">' + (pick.reason || '--') + '</td>' +
        '</tr>';
    }).join('');
}

// Render category breakdown
function renderCategoryBreakdown(data) {
    var categories = ['stock', 'penny', 'crypto', 'meme', 'forex'];
    var grid = document.getElementById('breakdownGrid');
    
    grid.innerHTML = categories.map(function(cat) {
        var algos = data.algorithms.filter(function(a) { return a.category === cat; });
        if (algos.length === 0) return '';
        
        var avgReturn = algos.reduce(function(sum, a) { return sum + a.totalReturn; }, 0) / algos.length;
        var avgWinRate = algos.reduce(function(sum, a) { return sum + a.winRate; }, 0) / algos.length;
        var totalPicks = algos.reduce(function(sum, a) { return sum + a.activePicks; }, 0);
        var bestAlgo = algos.reduce(function(best, a) { return a.totalReturn > best.totalReturn ? a : best; }, algos[0]);
        
        return '<div class="breakdown-card">' +
            '<div class="breakdown-header">' +
                '<div class="breakdown-title">' + getCategoryIcon(cat) + ' ' + getCategoryName(cat) + '</div>' +
                '<div class="breakdown-return ' + (avgReturn >= 0 ? 'return-positive' : 'return-negative') + '">' +
                    (avgReturn >= 0 ? '+' : '') + avgReturn.toFixed(1) + '%</div>' +
            '</div>' +
            '<div class="breakdown-stats">' +
                '<div class="breakdown-stat"><div class="breakdown-stat-value">' + algos.length + '</div><div class="breakdown-stat-label">Algorithms</div></div>' +
                '<div class="breakdown-stat"><div class="breakdown-stat-value">' + avgWinRate.toFixed(1) + '%</div><div class="breakdown-stat-label">Avg Win Rate</div></div>' +
                '<div class="breakdown-stat"><div class="breakdown-stat-value">' + totalPicks + '</div><div class="breakdown-stat-label">Active Picks</div></div>' +
            '</div>' +
            '<div style="margin-top: 12px; font-size: 12px; color: #8888aa;">Top: <span style="color: #e0e0f0;">' + bestAlgo.name + '</span> (' + (bestAlgo.totalReturn >= 0 ? '+' : '') + bestAlgo.totalReturn.toFixed(1) + '%)</div>' +
        '</div>';
    }).join('');
}

// Filter by category
function filterCategory(category) {
    currentCategory = category;
    document.querySelectorAll('.cat-btn').forEach(function(btn) {
        btn.classList.remove('active');
        if (btn.dataset.category === category) btn.classList.add('active');
    });
    renderLeaderboard(currentData);
}

function sortLeaderboard() {
    currentSort = document.getElementById('sortBy').value;
    renderLeaderboard(currentData);
}

function filterPicks() {
    renderActivePicks(currentData);
}

// Algorithm methodology definitions - full transparency for external vetting
// Covers ALL algorithm IDs: v2 Tier 1, v2 Scout, v1 legacy, backtest, and algorithms.json originals
// NO algorithm should ever show "Methodology details not available"
var ALGO_METHODOLOGY = (function() {
    // ========== TIER 1: Academic strategies from strategies_tier1.py ==========
    var t1_funding = {
        tier: 'TIER 1',
        description: 'Crypto funding rate mean-reversion via VWMA basis z-score. When price is deeply below its volume-weighted fair value, it historically coincides with negative funding rates — going long earns the reversion premium.',
        academicBasis: 'Funding rate arbitrage is a well-documented crypto market inefficiency. Proxy via VWMA basis (Frazzini & Pedersen framework adapted for crypto).',
        symbols: ['BTC-USD', 'ETH-USD', 'SOL-USD'],
        indicators: ['20-day VWMA (Volume-Weighted Moving Average)', '60-day rolling z-score of basis'],
        entryLogic: 'BUY when VWMA basis z-score < -2.0 (price deeply below volume-weighted fair value).',
        exitLogic: 'SELL when basis z-score reverts above -0.5 (mean-reversion complete).',
        dataSource: 'Yahoo Finance (yfinance) - 6 months daily OHLCV',
        scanFrequency: 'Every 15 min during market hours + every 4 hours on weekends',
        riskManagement: '$2,000 allocation per position, max 3 concurrent positions.',
        knownLimitations: 'Spot-only proxy cannot directly observe funding rates. Requires extended negative basis which is rare. Trades infrequently (by design).',
        backtestResult: 'Backtest: +26.2% total return, Sharpe 0.50, 24 trades over 6 years.'
    };
    var t1_pairs = {
        tier: 'TIER 1',
        description: 'Pairs trading via cointegration z-score of the log-spread between correlated assets. Exploits temporary divergences between historically linked price series.',
        academicBasis: 'Cointegration-based pairs trading (Engle & Granger, 1987). Rolling OLS hedge ratio with z-score mean-reversion.',
        symbols: ['SPY (paired with QQQ)', 'BTC-USD (paired with ETH-USD)'],
        indicators: ['60-day rolling OLS hedge ratio', '60-day z-score of log-spread'],
        entryLogic: 'BUY when spread z-score < -2.0 (long the underperformer in the pair).',
        exitLogic: 'SELL when spread z-score reverts within +/-0.5 (mean-reverted).',
        dataSource: 'Yahoo Finance (yfinance) - 6 months daily OHLCV for both assets in each pair',
        scanFrequency: 'Every 15 min during market hours + every 4 hours on weekends',
        riskManagement: '$2,000 allocation per position, max 3 concurrent positions.',
        knownLimitations: 'Cointegration can break down (regime change). Requires both assets to be available. Needs 120+ bars of history.',
        backtestResult: 'Backtest: +7.9% total return, Sharpe 0.55, 10 trades over 6 years.'
    };
    var t1_bab = {
        tier: 'TIER 1',
        description: 'Betting Against Beta (BAB): low-beta stocks earn higher risk-adjusted returns because leverage-constrained investors overpay for high-beta "lottery ticket" names.',
        academicBasis: 'Frazzini & Pedersen (2014), "Betting Against Beta." One of the most robust anomalies in finance, documented across 20+ countries and 50+ years.',
        symbols: ['AAPL', 'MSFT', 'NVDA', 'META', 'VTI'],
        indicators: ['120-day rolling beta vs SPY', '200-day SMA (trend filter)'],
        entryLogic: 'BUY when rolling beta < 0.8 AND price > 200-day SMA (low-beta with uptrend confirmation).',
        exitLogic: 'SELL when beta > 1.2 OR price drops below 200-day SMA.',
        dataSource: 'Yahoo Finance (yfinance) - 6 months daily OHLCV + SPY as benchmark',
        scanFrequency: 'Every 15 minutes during US market hours (Mon-Fri)',
        riskManagement: '$2,000 allocation per position, max 3 concurrent positions.',
        knownLimitations: 'BAB premium is slow-moving. Requires 200+ bars of data. Underperforms in strong momentum markets. Currently showing -3.2% in backtest (honest).',
        backtestResult: 'Backtest: -3.2% total return, Sharpe -0.24 (LOSING — this is the honest result).'
    };
    var t1_flash = {
        tier: 'TIER 1',
        description: 'Buys extreme sell-offs for the snap-back. Detects rapid, outsized declines using drawdown depth, RSI extremes, and volume capitulation simultaneously.',
        academicBasis: 'Mean-reversion after extreme moves is documented in Jegadeesh (1990) and DeBondt & Thaler (1985). Volume spike = capitulation signal (Barber & Odean, 2008).',
        symbols: ['BTC-USD', 'ETH-USD', 'SOL-USD', 'SPY', 'QQQ'],
        indicators: ['20-day rolling high / drawdown', 'RSI(6) short period for crash sensitivity', 'Volume ratio vs 20-day average'],
        entryLogic: 'BUY when ALL THREE conditions met simultaneously: drawdown > 5% from 20-day high, RSI(6) < 25, AND volume > 2x 20-day average.',
        exitLogic: 'SELL when price recovers 50% of the drawdown, OR time-stop after 10 bars.',
        dataSource: 'Yahoo Finance (yfinance) - 6 months daily OHLCV',
        scanFrequency: 'Every 15 min + every 4 hours on weekends',
        riskManagement: '$2,000 allocation per position, max 3 concurrent positions.',
        knownLimitations: 'Regime-specific: trades very rarely but with high expectancy. Triple-filter requirement means many crashes are missed. Catching a falling knife is inherently risky.',
        backtestResult: 'Backtest: +15.7% total return, Sharpe 0.49, 11 trades over 6 years. Excellent expectancy per trade.'
    };
    var t1_qmj = {
        tier: 'TIER 1',
        description: 'Quality Minus Junk: high-quality stocks (stable, consistent trend, shallow drawdowns, strong Sharpe) outperform junk. Uses price-derived quality proxies since fundamental data is not in OHLCV.',
        academicBasis: 'Novy-Marx (2013), Asness et al. (2019) "Quality Minus Junk." Persistent factor premium across markets and time periods.',
        symbols: ['AAPL', 'MSFT', 'NVDA', 'META', 'SPY', 'QQQ'],
        indicators: ['20-day return stability (inverse volatility)', '60-day trend R-squared (price-time regression)', '60-day drawdown resilience', '60-day momentum Sharpe', '200-day SMA (trend filter)'],
        entryLogic: 'BUY when composite quality z-score > 0.5 AND price > 200-day SMA.',
        exitLogic: 'SELL when quality z-score < -0.5 OR price drops below 200-day SMA.',
        dataSource: 'Yahoo Finance (yfinance) - 6 months daily OHLCV',
        scanFrequency: 'Every 15 minutes during US market hours (Mon-Fri)',
        riskManagement: '$2,000 allocation per position, max 3 concurrent positions.',
        knownLimitations: 'Price-derived quality proxies are less reliable than fundamental data (ROE, D/E). Requires 200+ bars. Quality factor can underperform in speculative rallies.',
        backtestResult: 'Backtest: +18.7% total return, Sharpe 0.89, 6 trades over 6 years.'
    };

    // ========== SCOUT: Simple supplementary signals ==========
    var scout_meme = {
        tier: 'SCOUT',
        description: '[SCOUT] Detects meme coin momentum breakouts via 5-day return + volume spike. Simple TA, no academic edge.',
        symbols: ['DOGE-USD', 'SHIB-USD'],
        indicators: ['5-day momentum', '20-day avg volume', 'Volume spike (1.5x)'],
        entryLogic: 'BUY when 5-day return > 2% AND volume > 1.5x 20-day average.',
        exitLogic: 'SELL when momentum turns negative or volume normalizes.',
        dataSource: 'Yahoo Finance (yfinance) - 6 months daily OHLCV',
        scanFrequency: 'Every 15 min + every 4 hours on weekends',
        riskManagement: '$2,000 per position, max 3.',
        knownLimitations: 'Simple momentum + volume. Meme coins are extremely volatile and prone to manipulation. HIGH RISK.'
    };
    var scout_penny = {
        tier: 'SCOUT',
        description: '[SCOUT] Volume breakout detection on penny stocks. Simple TA, no academic edge.',
        symbols: ['GME', 'AMC', 'PLTR', 'SOFI', 'HOOD'],
        indicators: ['20-day avg volume', 'Volume spike (2x)'],
        entryLogic: 'BUY when volume > 2x 20-day average.',
        exitLogic: 'SELL when volume normalizes.',
        dataSource: 'Yahoo Finance (yfinance) - 6 months daily OHLCV',
        scanFrequency: 'Every 15 min during US market hours',
        riskManagement: '$2,000 per position, max 3.',
        knownLimitations: 'Volume breakouts have no proven edge. Penny stocks have wide spreads. HIGH RISK.'
    };
    var scout_forex = {
        tier: 'SCOUT',
        description: '[SCOUT] MA crossover on major forex pairs. Simple TA, no academic edge.',
        symbols: ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X'],
        indicators: ['10-day SMA', '50-day SMA'],
        entryLogic: 'BUY when 10-day SMA crosses above 50-day SMA.',
        exitLogic: 'SELL when 10-day SMA crosses below 50-day SMA.',
        dataSource: 'Yahoo Finance (yfinance) - 6 months daily OHLCV',
        scanFrequency: 'Every 15 min during US market hours',
        riskManagement: '$2,000 per position, max 3.',
        knownLimitations: 'MA crossovers are lagging indicators with no proven edge in forex. Many false signals in ranging markets.'
    };
    var scout_rsi = {
        tier: 'SCOUT',
        description: '[SCOUT] RSI oversold detection on crypto. Simple TA, no academic edge.',
        symbols: ['BTC-USD', 'ETH-USD', 'SOL-USD', 'DOGE-USD', 'XRP-USD', 'BNB-USD'],
        indicators: ['RSI(14)'],
        entryLogic: 'BUY when RSI(14) < 30.',
        exitLogic: 'SELL when RSI(14) > 70 or held > 14 days.',
        dataSource: 'Yahoo Finance (yfinance) - 6 months daily OHLCV',
        scanFrequency: 'Every 15 min + every 4 hours on weekends',
        riskManagement: '$2,000 per position, max 3.',
        knownLimitations: 'RSI alone has no proven edge. Can stay oversold in bear markets. Textbook indicator.'
    };
    var scout_volume = {
        tier: 'SCOUT',
        description: '[SCOUT] Volume spike detection on crypto. Simple TA, no academic edge.',
        symbols: ['BTC-USD', 'ETH-USD', 'SOL-USD', 'DOGE-USD', 'SHIB-USD'],
        indicators: ['20-day avg volume', 'Volume spike (2x)'],
        entryLogic: 'BUY when volume > 2x 20-day average.',
        exitLogic: 'SELL when volume normalizes.',
        dataSource: 'Yahoo Finance (yfinance) - 6 months daily OHLCV',
        scanFrequency: 'Every 15 min + every 4 hours on weekends',
        riskManagement: '$2,000 per position, max 3.',
        knownLimitations: 'Volume spikes can be sell-offs, not accumulation. No academic backing. HIGH RISK.'
    };
    var scout_etf = {
        tier: 'SCOUT',
        description: '[SCOUT] MA crossover trend-following on ETFs. Simple TA.',
        symbols: ['SPY', 'QQQ', 'VTI'],
        indicators: ['10-day SMA', '50-day SMA'],
        entryLogic: 'BUY when 10-day SMA crosses ABOVE 50-day SMA (bullish golden cross).',
        exitLogic: 'SELL when 10-day SMA crosses BELOW 50-day SMA.',
        dataSource: 'Yahoo Finance (yfinance) - 6 months daily OHLCV',
        scanFrequency: 'Every 15 min during US market hours',
        riskManagement: '$2,000 per position, max 3.',
        knownLimitations: 'MA crossovers are lagging indicators. May miss fast reversals. Not suited for sideways markets.'
    };
    var scout_bluechip = {
        tier: 'SCOUT',
        description: '[SCOUT] RSI + momentum on blue chip stocks. Simple TA.',
        symbols: ['AAPL', 'MSFT', 'NVDA', 'META'],
        indicators: ['RSI(14)', '5-day momentum', '20-day avg volume'],
        entryLogic: 'BUY when RSI(14) < 30 (oversold) OR (5-day return > 2% AND volume above average).',
        exitLogic: 'SELL when RSI(14) > 70 or position held > 14 days.',
        dataSource: 'Yahoo Finance (yfinance) - 6 months daily OHLCV',
        scanFrequency: 'Every 15 min during US market hours',
        riskManagement: '$2,000 per position, max 3.',
        knownLimitations: 'RSI oversold on blue chips is rare. Momentum can buy near tops.'
    };
    var scout_techmo = {
        tier: 'SCOUT',
        description: '[SCOUT] Bollinger Band + momentum on volatile tech stocks. Simple TA.',
        symbols: ['AMD', 'TSLA', 'NVDA'],
        indicators: ['Bollinger Bands(20,2)', '5-day momentum'],
        entryLogic: 'BUY when price touches lower Bollinger Band OR 5-day return > 2%.',
        exitLogic: 'SELL when price touches upper Bollinger Band or momentum reverses.',
        dataSource: 'Yahoo Finance (yfinance) - 6 months daily OHLCV',
        scanFrequency: 'Every 15 min during US market hours',
        riskManagement: '$2,000 per position, max 3.',
        knownLimitations: 'Bollinger touches in strong downtrends are not reversals.'
    };
    var scout_crypto_generic = {
        tier: 'SCOUT',
        description: '[SCOUT] RSI + momentum crypto scanning. Simple TA.',
        symbols: ['BTC-USD', 'ETH-USD', 'SOL-USD'],
        indicators: ['RSI(14)', '5-day momentum'],
        entryLogic: 'BUY when RSI(14) < 30 (oversold) OR 5-day return > 2%.',
        exitLogic: 'SELL when RSI(14) > 70 or held > 14 days.',
        dataSource: 'Yahoo Finance (yfinance) - 6 months daily OHLCV',
        scanFrequency: 'Every 15 min + every 4 hours on weekends',
        riskManagement: '$2,000 per position, max 3.',
        knownLimitations: 'Momentum can buy near tops. RSI can stay oversold in bear markets.'
    };
    var scout_alpha = {
        tier: 'SCOUT',
        description: '[SCOUT] Multi-indicator confluence: RSI + Bollinger + momentum. Requires 2+ simultaneous signals.',
        symbols: ['BTC-USD', 'ETH-USD', 'SOL-USD', 'NVDA', 'TSLA'],
        indicators: ['RSI(14)', 'Bollinger Bands(20,2)', '5-day momentum'],
        entryLogic: 'BUY when 2 or more: RSI < 35, price at lower Bollinger Band, 5-day momentum > 1%.',
        exitLogic: 'SELL when 0 conditions remain active or held > 14 days.',
        dataSource: 'Yahoo Finance (yfinance) - 6 months daily OHLCV',
        scanFrequency: 'Every 15 min + every 4 hours on weekends',
        riskManagement: '$2,000 per position, max 3.',
        knownLimitations: 'Confluence requirement means fewer trades. May miss fast moves.'
    };
    var scout_pump = {
        tier: 'SCOUT',
        description: '[SCOUT] Extreme volume spike detection on crypto. Simple TA.',
        symbols: ['BTC-USD', 'ETH-USD', 'SOL-USD', 'DOGE-USD', 'SHIB-USD'],
        indicators: ['20-day avg volume', 'Volume spike (2x)'],
        entryLogic: 'BUY when volume > 2x 20-day average.',
        exitLogic: 'SELL when volume normalizes.',
        dataSource: 'Yahoo Finance (yfinance) - 6 months daily OHLCV',
        scanFrequency: 'Every 15 min + every 4 hours on weekends',
        riskManagement: '$2,000 per position, max 3.',
        knownLimitations: 'Volume spikes can be sell-offs not accumulation. Very high risk.'
    };
    var scout_generic = {
        tier: 'SCOUT',
        description: '[SCOUT] General technical analysis scanner using standard indicators.',
        symbols: ['Various'],
        indicators: ['RSI', 'SMA', 'Volume'],
        entryLogic: 'BUY on standard TA signal (RSI oversold, MA crossover, or volume spike).',
        exitLogic: 'SELL on signal reversal or time-stop.',
        dataSource: 'Yahoo Finance (yfinance) - 6 months daily OHLCV',
        scanFrequency: 'Every 15 min during market hours',
        riskManagement: '$2,000 per position, max 3.',
        knownLimitations: 'Standard TA indicators have no proven persistent edge. Widely used and likely arbitraged.'
    };

    // Build the map with ALL known IDs pointing to the right methodology
    var m = {};

    // v2 Tier 1 IDs (live_scanner.py v2)
    m['funding-rate-arb'] = t1_funding;
    m['pairs-trading'] = t1_pairs;
    m['betting-against-beta'] = t1_bab;
    m['flash-crash-reversal'] = t1_flash;
    m['quality-minus-junk'] = t1_qmj;

    // Backtest IDs (dashboard_data.json from generate_dashboard_data.py)
    m['funding_rate_arb'] = t1_funding;
    m['pairs_trading'] = t1_pairs;
    m['bab'] = t1_bab;
    m['flash_crash'] = t1_flash;
    m['qmj'] = t1_qmj;

    // v2 Scout IDs
    m['meme-scanner-live'] = scout_meme;
    m['penny-tracker-live'] = scout_penny;
    m['forex-scanner-live'] = scout_forex;
    m['crypto-momentum-scout'] = scout_rsi;
    m['volume-spike-scout'] = scout_volume;

    // v1 Live scanner IDs (legacy — user may still see these from cached data)
    m['etf-masters-live'] = scout_etf;
    m['blue-chip-live'] = scout_bluechip;
    m['technical-momentum-live'] = scout_techmo;
    m['crypto-winners-live'] = scout_crypto_generic;
    m['rsi-momentum-live'] = scout_rsi;
    m['alpha-hunter-live'] = scout_alpha;
    m['pump-watch-live'] = scout_pump;

    // Original algorithms.json IDs (oldest version)
    m['etf-masters'] = scout_etf;
    m['blue-chip-growth'] = scout_bluechip;
    m['technical-momentum'] = scout_techmo;
    m['crypto-winners'] = scout_crypto_generic;
    m['meme-scanner'] = scout_meme;
    m['penny-tracker'] = scout_penny;
    m['forex-scanner'] = scout_forex;
    m['rsi-mean-reversion'] = scout_rsi;
    m['alpha-predator'] = scout_alpha;
    m['sector-rotation'] = scout_generic;
    m['can-slim'] = scout_generic;
    m['composite-rating'] = scout_generic;
    m['macd-crossover'] = scout_generic;
    m['bollinger-squeeze'] = scout_generic;
    m['triple-ema'] = scout_generic;
    m['ichimoku-cloud'] = scout_generic;
    m['momentum-btc'] = scout_crypto_generic;
    m['stochrsi-volume'] = scout_rsi;
    m['funding-contrarian'] = t1_funding;
    m['whale-accumulation'] = scout_pump;
    m['ml-meme'] = scout_meme;

    return m;
})();

// Show algorithm details modal with full audit and methodology
function showAlgorithmDetails(algoId) {
    if (!algoId || !currentData) return;
    var algo = currentData.algorithms.find(function(a) { return a.id === algoId; });
    if (!algo) return;

    var isLive = currentData.dataType === 'FORWARD_TEST';
    var method = ALGO_METHODOLOGY[algoId] || {
        tier: algo.tier === 'TIER_1' ? 'TIER 1' : algo.tier || 'UNKNOWN',
        description: 'Algorithm: ' + algo.name + '. Category: ' + getCategoryName(algo.category) + '.',
        symbols: [algo.asset || algo.id],
        indicators: ['Technical analysis indicators'],
        entryLogic: algo.nextAction || 'Scan for entry signals based on configured rules.',
        exitLogic: 'Exit on signal reversal or time-based stop.',
        dataSource: 'Yahoo Finance (yfinance) - daily OHLCV data',
        scanFrequency: 'Automated via GitHub Actions',
        riskManagement: '$2,000 per position, max 3 concurrent.',
        knownLimitations: 'Detailed methodology for this algorithm ID ("' + algoId + '") is being documented. Check source code on GitHub for full logic.'
    };
    var returnClass = (algo.totalReturn || 0) >= 0 ? 'return-positive' : 'return-negative';

    var algoPicks = (currentData.activePicks || []).filter(function(p) {
        return p.algorithmId === algoId || p.algorithm === algo.name;
    });

    document.getElementById('modalAlgoName').textContent = algo.name + ' — Full Audit';

    var html = '';

    // Tab buttons
    html += '<div style="display:flex; gap:4px; margin-bottom:16px; border-bottom:2px solid rgba(136,136,170,0.2); padding-bottom:8px;">' +
        '<button onclick="switchAlgoTab(\'overview\')" id="tabBtn_overview" style="background:#3b82f6; color:#fff; border:none; padding:8px 16px; border-radius:6px 6px 0 0; cursor:pointer; font-weight:600; font-size:13px;">Overview</button>' +
        '<button onclick="switchAlgoTab(\'methodology\')" id="tabBtn_methodology" style="background:transparent; color:#8888aa; border:none; padding:8px 16px; border-radius:6px 6px 0 0; cursor:pointer; font-weight:600; font-size:13px;">Methodology</button>' +
        '<button onclick="switchAlgoTab(\'picks\')" id="tabBtn_picks" style="background:transparent; color:#8888aa; border:none; padding:8px 16px; border-radius:6px 6px 0 0; cursor:pointer; font-weight:600; font-size:13px;">Active Picks (' + algoPicks.length + ')</button>' +
        '<button onclick="switchAlgoTab(\'audit\')" id="tabBtn_audit" style="background:transparent; color:#8888aa; border:none; padding:8px 16px; border-radius:6px 6px 0 0; cursor:pointer; font-weight:600; font-size:13px;">Audit Trail</button>' +
    '</div>';

    // OVERVIEW TAB
    html += '<div id="algoTab_overview">';
    html += '<div style="display:grid; grid-template-columns:repeat(2,1fr); gap:12px; margin-bottom:16px;">';
    html += '<div style="background:rgba(18,18,42,0.5); padding:14px; border-radius:10px;"><div style="font-size:11px; color:#8888aa; text-transform:uppercase;">Portfolio Value</div><div style="font-size:22px; font-weight:700;">$' + (algo.currentValue || 0).toLocaleString() + '</div></div>';
    html += '<div style="background:rgba(18,18,42,0.5); padding:14px; border-radius:10px;"><div style="font-size:11px; color:#8888aa; text-transform:uppercase;">Total Return</div><div style="font-size:22px; font-weight:700;" class="' + returnClass + '">' + ((algo.totalReturn || 0) >= 0 ? '+' : '') + (algo.totalReturn || 0).toFixed(2) + '%</div></div>';
    html += '<div style="background:rgba(18,18,42,0.5); padding:14px; border-radius:10px;"><div style="font-size:11px; color:#8888aa; text-transform:uppercase;">Win Rate</div><div style="font-size:22px; font-weight:700;">' + (algo.winRate || 0).toFixed(1) + '%</div></div>';
    html += '<div style="background:rgba(18,18,42,0.5); padding:14px; border-radius:10px;"><div style="font-size:11px; color:#8888aa; text-transform:uppercase;">Sharpe Ratio</div><div style="font-size:22px; font-weight:700;">' + (algo.sharpeRatio || 0).toFixed(2) + '</div></div>';
    html += '</div>';
    html += '<div style="display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-bottom:16px;">';
    html += '<div style="text-align:center; padding:10px; background:rgba(18,18,42,0.3); border-radius:8px;"><div style="font-size:18px; font-weight:700;">' + (algo.activePicks || 0) + '</div><div style="font-size:10px; color:#8888aa;">Active Picks</div></div>';
    html += '<div style="text-align:center; padding:10px; background:rgba(18,18,42,0.3); border-radius:8px;"><div style="font-size:18px; font-weight:700;">' + (algo.maxDrawdown || 0).toFixed(1) + '%</div><div style="font-size:10px; color:#8888aa;">Max Drawdown</div></div>';
    html += '<div style="text-align:center; padding:10px; background:rgba(18,18,42,0.3); border-radius:8px;"><div style="font-size:18px; font-weight:700;">$' + (algo.startingValue || 10000).toLocaleString() + '</div><div style="font-size:10px; color:#8888aa;">Starting Value</div></div>';
    html += '</div>';
    var overviewTierBadge = algo.tier === 'TIER_1' ? '<span style="background:#2563eb;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;">TIER 1</span>' :
                            algo.tier === 'SCOUT' ? '<span style="background:#6b7280;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;">SCOUT</span>' : '';
    html += '<div style="display:flex; align-items:center; gap:8px;">' + overviewTierBadge + '<span class="category-badge ' + algo.category + '">' + getCategoryName(algo.category) + '</span>';
    html += '<span style="font-size:12px; color:#8888aa;">' + (isLive ? '🔴 LIVE FORWARD TEST' : '📊 BACKTESTED') + '</span></div>';
    html += '</div>';

    // METHODOLOGY TAB
    html += '<div id="algoTab_methodology" style="display:none;">';
    if (method) {
        var tierBadge = method.tier === 'TIER 1' ?
            '<span style="background:#2563eb;color:#fff;padding:3px 10px;border-radius:6px;font-size:12px;font-weight:700;">TIER 1 — Academic Strategy</span>' :
            '<span style="background:#6b7280;color:#fff;padding:3px 10px;border-radius:6px;font-size:12px;font-weight:700;">SCOUT — Simple TA</span>';
        html += '<div style="margin-bottom:12px;">' + tierBadge + '</div>';
        html += '<div style="background:rgba(59,130,246,0.1); border-left:3px solid #3b82f6; padding:12px; border-radius:4px; margin-bottom:14px;"><div style="font-size:14px; font-weight:600; color:#e0e0f0;">' + method.description + '</div></div>';
        if (method.academicBasis) {
            html += '<div style="background:rgba(139,92,246,0.1); border-left:3px solid #8b5cf6; padding:10px; border-radius:4px; margin-bottom:14px; font-size:13px;"><strong style="color:#a78bfa;">Academic Basis:</strong> <span style="color:#e0e0f0;">' + method.academicBasis + '</span></div>';
        }
        if (method.backtestResult) {
            var btColor = method.backtestResult.indexOf('LOSING') >= 0 ? '#ef4444' : '#22c55e';
            html += '<div style="background:rgba(245,158,11,0.1); border-left:3px solid ' + btColor + '; padding:10px; border-radius:4px; margin-bottom:14px; font-size:13px;"><strong style="color:' + btColor + ';">Backtest Result:</strong> <span style="color:#e0e0f0;">' + method.backtestResult + '</span></div>';
        }
        html += '<table style="width:100%; border-collapse:collapse; font-size:13px;">';
        html += '<tr style="border-bottom:1px solid rgba(136,136,170,0.2);"><td style="padding:8px; color:#8888aa; width:140px;">Symbols Scanned</td><td style="padding:8px; color:#e0e0f0;"><code>' + method.symbols.join(', ') + '</code></td></tr>';
        html += '<tr style="border-bottom:1px solid rgba(136,136,170,0.2);"><td style="padding:8px; color:#8888aa;">Indicators</td><td style="padding:8px; color:#e0e0f0;">' + method.indicators.join(', ') + '</td></tr>';
        html += '<tr style="border-bottom:1px solid rgba(136,136,170,0.2); background:rgba(34,197,94,0.05);"><td style="padding:8px; color:#22c55e; font-weight:600;">Entry Logic</td><td style="padding:8px; color:#e0e0f0;">' + method.entryLogic + '</td></tr>';
        html += '<tr style="border-bottom:1px solid rgba(136,136,170,0.2); background:rgba(239,68,68,0.05);"><td style="padding:8px; color:#ef4444; font-weight:600;">Exit Logic</td><td style="padding:8px; color:#e0e0f0;">' + method.exitLogic + '</td></tr>';
        html += '<tr style="border-bottom:1px solid rgba(136,136,170,0.2);"><td style="padding:8px; color:#8888aa;">Data Source</td><td style="padding:8px; color:#e0e0f0;">' + method.dataSource + '</td></tr>';
        html += '<tr style="border-bottom:1px solid rgba(136,136,170,0.2);"><td style="padding:8px; color:#8888aa;">Scan Frequency</td><td style="padding:8px; color:#e0e0f0;">' + method.scanFrequency + '</td></tr>';
        html += '<tr style="border-bottom:1px solid rgba(136,136,170,0.2);"><td style="padding:8px; color:#8888aa;">Risk Mgmt</td><td style="padding:8px; color:#e0e0f0;">' + method.riskManagement + '</td></tr>';
        html += '<tr style="background:rgba(245,158,11,0.08);"><td style="padding:8px; color:#f59e0b; font-weight:600;">Limitations</td><td style="padding:8px; color:#fde68a;">' + method.knownLimitations + '</td></tr>';
        html += '</table>';
        html += '<div style="margin-top:14px; background:rgba(18,18,42,0.5); padding:10px; border-radius:6px; font-size:12px; color:#8888aa;"><strong>Source Code:</strong> <a href="https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/KIMI_RISEOFTHECLAW/live_scanner.py" target="_blank" style="color:#60a5fa;">live_scanner.py on GitHub</a> — fully open source, auditable. Strategy definitions: <a href="https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/KIMI_CLAW_RESEARCH_FEB162026/strategies_tier1.py" target="_blank" style="color:#60a5fa;">strategies_tier1.py</a></div>';
    } else {
        html += '<div style="padding:20px; text-align:center; color:#8888aa;">Methodology details not available for this algorithm.</div>';
    }
    html += '</div>';

    // ACTIVE PICKS TAB
    html += '<div id="algoTab_picks" style="display:none;">';
    if (algoPicks.length > 0) {
        html += '<div style="margin-bottom:10px; font-size:12px; color:#8888aa;">All timestamps in Eastern Standard Time (EST). Entry prices are the actual market price at time of signal.</div>';
        algoPicks.forEach(function(pick) {
            var entry = pick.entryPrice || 0;
            var current = pick.currentPrice || entry;
            var plPct = entry > 0 ? ((current - entry) / entry) * 100 : 0;
            var plVal = pick.shares ? (current - entry) * pick.shares : 0;
            var plClass = plPct >= 0 ? 'return-positive' : 'return-negative';

            html += '<div style="background:rgba(18,18,42,0.5); padding:14px; border-radius:8px; margin-bottom:8px; border-left:3px solid ' + (plPct >= 0 ? '#22c55e' : '#ef4444') + ';">';
            html += '<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">';
            html += '<div><strong style="font-size:16px;">' + pick.symbol + '</strong> <span class="signal-badge ' + ((pick.signal || '').toLowerCase() === 'buy' ? 'buy' : 'sell') + '" style="font-size:10px;">' + (pick.signal || '').toUpperCase() + '</span></div>';
            html += '<div class="' + plClass + '" style="font-size:18px; font-weight:700;">' + (plPct >= 0 ? '+' : '') + plPct.toFixed(3) + '%</div>';
            html += '</div>';
            html += '<table style="width:100%; font-size:12px; border-collapse:collapse;">';
            html += '<tr><td style="padding:3px 0; color:#8888aa; width:120px;">Entry Date (EST)</td><td style="padding:3px 0; color:#e0e0f0; font-weight:600;">' + formatEST(pick.entryDate) + '</td></tr>';
            html += '<tr><td style="padding:3px 0; color:#8888aa;">Entry Price</td><td style="padding:3px 0; color:#e0e0f0;">$' + entry.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 6}) + '</td></tr>';
            html += '<tr><td style="padding:3px 0; color:#8888aa;">Current Price</td><td style="padding:3px 0; color:#e0e0f0;">$' + current.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 6}) + '</td></tr>';
            html += '<tr><td style="padding:3px 0; color:#8888aa;">P&L ($)</td><td style="padding:3px 0;" class="' + plClass + '">$' + plVal.toFixed(2) + '</td></tr>';
            html += '<tr><td style="padding:3px 0; color:#8888aa;">Shares / Units</td><td style="padding:3px 0; color:#e0e0f0;">' + (pick.shares || 0).toFixed(6) + '</td></tr>';
            html += '<tr><td style="padding:3px 0; color:#8888aa;">Allocation</td><td style="padding:3px 0; color:#e0e0f0;">$' + (pick.allocation || 0).toLocaleString() + '</td></tr>';
            html += '<tr><td style="padding:3px 0; color:#8888aa;">Signal Reason</td><td style="padding:3px 0; color:#f59e0b; font-weight:600;">' + (pick.reason || '--') + '</td></tr>';
            html += '<tr><td style="padding:3px 0; color:#8888aa;">Days Held</td><td style="padding:3px 0; color:#e0e0f0;">' + (pick.daysHeld || 0) + ' days</td></tr>';
            html += '<tr><td style="padding:3px 0; color:#8888aa;">Data Source</td><td style="padding:3px 0; color:#60a5fa;">' + (pick.auditSource || 'live_competition.json') + '</td></tr>';
            html += '</table></div>';
        });
    } else {
        html += '<div style="padding:30px; text-align:center;"><div style="font-size:32px; margin-bottom:8px;">🔍</div>';
        html += '<div style="font-size:15px; font-weight:600; margin-bottom:6px;">No Active Picks</div>';
        html += '<div style="font-size:13px; color:#8888aa; line-height:1.6;">';
        if (method) {
            html += 'Scanning <code>' + method.symbols.join(', ') + '</code>.<br>Entry: <span style="color:#e0e0f0;">' + method.entryLogic + '</span><br>No symbols currently meet the entry threshold.';
        } else { html += 'Scanning for signals. No entry conditions met yet.'; }
        html += '</div></div>';
    }
    html += '</div>';

    // AUDIT TRAIL TAB
    html += '<div id="algoTab_audit" style="display:none;">';
    html += '<div style="background:rgba(59,130,246,0.1); border-left:3px solid #3b82f6; padding:12px; border-radius:4px; margin-bottom:14px; font-size:13px;"><strong>Full Transparency:</strong> Every signal and trade is logged. Raw data files are publicly accessible.</div>';

    var auditItems = [];
    algoPicks.forEach(function(p) {
        auditItems.push({ time: p.entryDate, type: 'ENTRY', detail: (p.signal || 'BUY').toUpperCase() + ' ' + p.symbol + ' @ $' + (p.entryPrice || 0).toLocaleString(undefined, {maximumFractionDigits: 2}) + ' — ' + (p.reason || 'N/A') });
    });
    auditItems.push({ time: currentData.lastUpdated || new Date().toISOString(), type: 'SCAN', detail: 'Market scan completed. ' + algoPicks.length + ' active position(s). ' + (method ? method.symbols.length : '?') + ' symbols checked.' });
    auditItems.sort(function(a, b) { return new Date(b.time) - new Date(a.time); });

    html += '<div style="max-height:300px; overflow-y:auto;">';
    auditItems.forEach(function(item) {
        var typeColor = item.type === 'ENTRY' ? '#22c55e' : item.type === 'EXIT' ? '#ef4444' : '#3b82f6';
        html += '<div style="background:rgba(18,18,42,0.5); padding:10px 12px; border-radius:6px; margin-bottom:6px; font-size:13px; border-left:3px solid ' + typeColor + ';">';
        html += '<div style="display:flex; justify-content:space-between; margin-bottom:4px;"><span style="color:' + typeColor + '; font-weight:600;">' + item.type + '</span><span style="color:#8888aa; font-size:11px;">' + formatEST(item.time) + '</span></div>';
        html += '<div style="color:#e0e0f0;">' + item.detail + '</div></div>';
    });
    html += '</div>';

    html += '<div style="margin-top:14px; background:rgba(18,18,42,0.5); padding:10px; border-radius:6px;"><div style="font-weight:600; margin-bottom:6px; font-size:13px;">Verify Raw Data</div>';
    html += '<div style="font-size:12px; color:#8888aa; line-height:1.8;">';
    html += '<a href="data/live_competition.json" target="_blank" style="color:#60a5fa;">live_competition.json</a> — All positions<br>';
    html += '<a href="data/active_picks.json" target="_blank" style="color:#60a5fa;">active_picks.json</a> — Flat pick list<br>';
    html += '<a href="data/audit_log.json" target="_blank" style="color:#60a5fa;">audit_log.json</a> — Append-only signal log<br>';
    html += '<a href="https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/KIMI_RISEOFTHECLAW/live_scanner.py" target="_blank" style="color:#60a5fa;">Source Code (GitHub)</a></div></div>';
    html += '</div>';

    document.getElementById('modalBody').innerHTML = html;
    document.getElementById('algoModal').classList.add('active');
}

function switchAlgoTab(tab) {
    var tabs = ['overview', 'methodology', 'picks', 'audit'];
    tabs.forEach(function(t) {
        var el = document.getElementById('algoTab_' + t);
        var btn = document.getElementById('tabBtn_' + t);
        if (el) el.style.display = (t === tab) ? 'block' : 'none';
        if (btn) { btn.style.background = (t === tab) ? '#3b82f6' : 'transparent'; btn.style.color = (t === tab) ? '#ffffff' : '#8888aa'; }
    });
}

// Close modal
function closeModal() {
    document.getElementById('algoModal').classList.remove('active');
}

document.addEventListener('click', function(e) {
    var modal = document.getElementById('algoModal');
    if (e.target === modal) closeModal();
});

// Auto refresh
function startAutoRefresh() {
    var interval = parseInt((document.getElementById('refreshInterval') || {}).value || '60');
    if (refreshInterval) clearInterval(refreshInterval);
    if (interval > 0) {
        refreshInterval = setInterval(function() { loadDashboardData(); }, interval * 1000);
    }
}

function setRefreshInterval() { startAutoRefresh(); }
function manualRefresh() { loadDashboardData(); }

// Update last updated timestamp (in EST)
function updateLastUpdated() {
    var ts = (currentData && currentData.lastUpdated) ? new Date(currentData.lastUpdated) : new Date();
    try {
        document.getElementById('lastUpdated').textContent =
            ts.toLocaleTimeString('en-US', { timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' EST';
    } catch (e) {
        document.getElementById('lastUpdated').textContent = ts.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
}

// Export data
function exportData() {
    if (!currentData) return;
    var exportObj = { timestamp: new Date().toISOString(), algorithms: currentData.algorithms, activePicks: currentData.activePicks };
    var blob = new Blob([JSON.stringify(exportObj, null, 2)], { type: 'application/json' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'rise-of-the-claw-' + new Date().toISOString().split('T')[0] + '.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
