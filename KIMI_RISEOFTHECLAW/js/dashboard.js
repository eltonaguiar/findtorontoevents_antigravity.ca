// Main dashboard logic
let currentData = null;
let refreshInterval = null;
let currentCategory = 'all';
let currentSort = 'return';

// Initialize dashboard
document.addEventListener('DOMContentLoaded', async () => {
    await loadDashboardData();
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

    // Handle empty algorithms array
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

    // Top performer - with initial value
    const topPerformer = algorithms.reduce((best, algo) =>
        algo.totalReturn > best.totalReturn ? algo : best,
        algorithms[0]
    );
    document.getElementById('topPerformer').textContent = topPerformer.name;
    document.getElementById('topPerformerReturn').textContent =
        `${topPerformer.totalReturn >= 0 ? '+' : ''}${topPerformer.totalReturn.toFixed(2)}%`;
    document.getElementById('topPerformerReturn').className =
        `perf-sub ${topPerformer.totalReturn >= 0 ? 'return-positive' : 'return-negative'}`;

    // Best win rate - with initial value
    const bestWinRate = algorithms.reduce((best, algo) =>
        algo.winRate > best.winRate ? algo : best,
        algorithms[0]
    );
    document.getElementById('bestWinRate').textContent = `${bestWinRate.winRate.toFixed(1)}%`;
    document.getElementById('bestWinRateAlgo').textContent = bestWinRate.name;

    // Most active - with initial value
    const mostActive = algorithms.reduce((most, algo) =>
        algo.activePicks > most.activePicks ? algo : most,
        algorithms[0]
    );
    document.getElementById('mostActive').textContent = mostActive.name;
    document.getElementById('mostActiveCount').textContent = `${mostActive.activePicks} picks`;

    // Best Sharpe - with initial value
    const bestSharpe = algorithms.reduce((best, algo) =>
        algo.sharpeRatio > best.sharpeRatio ? algo : best,
        algorithms[0]
    );
    document.getElementById('bestSharpe').textContent = bestSharpe.sharpeRatio.toFixed(2);
    document.getElementById('bestSharpeAlgo').textContent = bestSharpe.name;

    // Lowest drawdown - with initial value
    const lowestDrawdown = algorithms.reduce((best, algo) =>
        algo.maxDrawdown > best.maxDrawdown ? algo : best,
        algorithms[0]
    );
    document.getElementById('lowestDrawdown').textContent = `${lowestDrawdown.maxDrawdown.toFixed(1)}%`;
    document.getElementById('lowestDrawdownAlgo').textContent = lowestDrawdown.name;
}

// Render leaderboard
function renderLeaderboard(data) {
    let algorithms = [...data.algorithms];
    
    // Filter by category
    if (currentCategory !== 'all') {
        algorithms = algorithms.filter(a => a.category === currentCategory);
    }
    
    // Sort
    algorithms.sort((a, b) => {
        switch(currentSort) {
            case 'return': return b.totalReturn - a.totalReturn;
            case 'winRate': return b.winRate - a.winRate;
            case 'sharpe': return b.sharpeRatio - a.sharpeRatio;
            case 'value': return b.currentValue - a.currentValue;
            default: return b.totalReturn - a.totalReturn;
        }
    });
    
    const tbody = document.getElementById('leaderboardBody');
    
    if (algorithms.length === 0) {
        tbody.innerHTML = `<tr><td colspan="10" class="loading-cell">No algorithms found for this category.</td></tr>`;
        return;
    }
    
    var isLive = currentData && currentData.dataType === 'FORWARD_TEST';

    tbody.innerHTML = algorithms.map(function(algo, index) {
        var rank = index + 1;
        var rankClass = rank === 1 ? 'gold' : rank === 2 ? 'silver' : rank === 3 ? 'bronze' : '';
        var rowClass = rank <= 3 ? 'rank-' + rank : '';
        var returnClass = algo.totalReturn >= 0 ? 'return-positive' : 'return-negative';
        var hasTraded = algo.totalReturn !== 0 || (algo.activePicks || 0) > 0;

        // Status column: in live mode show scanning status when no trades
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

        return '<tr class="' + rowClass + '" onclick="showAlgorithmDetails(\'' + algo.id + '\')" style="cursor: pointer;">' +
            '<td><div class="rank-badge ' + rankClass + '">' + rank + '</div></td>' +
            '<td>' +
                '<div class="algo-name-cell">' +
                    '<div class="algo-avatar">' + (algo.avatar || '📊') + '</div>' +
                    '<div class="algo-info">' +
                        '<div class="algo-name">' + algo.name + '</div>' +
                        '<div class="algo-category">' + getCategoryName(algo.category) + '</div>' +
                    '</div>' +
                '</div>' +
            '</td>' +
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

// Render active picks - ONLY real trades (no fakes)
function renderActivePicks(data) {
    var tbody = document.getElementById('picksBody');
    var picks = (data.activePicks || []).slice();
    var isLive = data.dataType === 'FORWARD_TEST';
    var isBacktest = data.dataType === 'BACKTEST';

    // Apply category filter
    var categoryFilter = document.getElementById('pickCategoryFilter');
    var catVal = categoryFilter ? categoryFilter.value : 'all';
    if (catVal !== 'all') {
        picks = picks.filter(function(p) { return p.category === catVal; });
    }

    // Apply search filter
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
                    'All algorithms are actively scanning markets for trade signals. ' +
                    'Picks will appear here the moment an algorithm triggers an entry condition. ' +
                    'Crypto scans run 24/7; stock scans run during US market hours.' +
                '</div>' +
                '<div style="margin-top: 12px; font-size: 12px; color: #60a5fa;">' +
                    'Click the <strong>🔴 LIVE FORWARD TEST</strong> badge above for the full audit trail.' +
                '</div>' +
            '</div>';
        } else if (isBacktest) {
            msg = '<div style="padding: 20px; text-align: center; color: #8888aa;">' +
                'Backtest summary shown in the leaderboard above. ' +
                'Individual trade logs available in <a href="/kimi-claw/data/tier1_summary.json" target="_blank" style="color: #f59e0b;">tier1_summary.json</a>.' +
            '</div>';
        } else {
            msg = 'No active picks found.';
        }
        tbody.innerHTML = '<tr><td colspan="18" class="loading-cell">' + msg + '</td></tr>';
        return;
    }

    tbody.innerHTML = picks.map(function(pick) {
        var entry = pick.entryPrice || 0;
        var current = pick.currentPrice || entry;
        var plPct = entry > 0 ? ((current - entry) / entry) * 100 : 0;
        var plVal = pick.plValue || (pick.shares ? (current - entry) * pick.shares : 0);
        var plClass = plPct >= 0 ? 'return-positive' : 'return-negative';
        var signalClass = (pick.signal || '').toLowerCase() === 'buy' ? 'buy' : (pick.signal || '').toLowerCase() === 'sell' ? 'sell' : 'hold';
        var priceFormat = function(p) {
            if (typeof p !== 'number') return p || '--';
            if (p >= 1000) return '$' + p.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
            if (p >= 1) return '$' + p.toFixed(2);
            return '$' + p.toFixed(6);
        };

        // Safety badge
        var safetyCell = '--';
        if (typeof pick.safety_score === 'number' && pick.safety_score >= 0) {
            var sColor = pick.safety_score >= 70 ? '#22c55e' : pick.safety_score >= 30 ? '#f59e0b' : '#ef4444';
            var sIcon = pick.safety_score >= 70 ? '\u{1F6E1}' : pick.safety_score >= 30 ? '\u26A0' : '\u{1F6AB}';
            safetyCell = '<span style="color:' + sColor + '; font-weight:700; font-size:11px;">' + sIcon + ' ' + pick.safety_score + '</span>';
        }

        // Performance breakdown cells
        var pb = pick.performance_breakdown || {};
        var perfCell = function(period) {
            var d = pb[period];
            if (!d) return '<td style="color:#555; font-size:11px;">—</td>';
            var c = d.pct > 0.5 ? '#22c55e' : d.pct < -0.5 ? '#ef4444' : '#888';
            var s = d.pct >= 0 ? '+' : '';
            return '<td style="color:' + c + '; font-size:11px; font-weight:600; font-family:monospace;">' + s + d.pct.toFixed(1) + '%</td>';
        };
        var gradeColors = {'A+':'#22c55e','A':'#4ade80','B':'#3b82f6','C':'#f59e0b','D':'#ef4444','F':'#ef4444'};
        var tg = pick.trend_grade || '?';
        var tgColor = gradeColors[tg] || '#888';
        var gradeCell = '<span style="color:' + tgColor + '; font-weight:800; font-size:13px;">' + tg + '</span>';
        if (pick.super_bullish) gradeCell += ' <span style="font-size:9px; color:#22c55e; background:rgba(34,197,94,0.12); padding:1px 4px; border-radius:4px;">BULL</span>';

        // Double ignite flame emoji
        var flameTag = '';
        if (pick.double_ignite) {
            flameTag = '<span class="flame-icon" title="Double Ignite — convergence 2 scans in a row">\uD83D\uDD25</span> ';
        }

        // MTF trend mini-panel
        var mtfRow = '';
        if (pick.mtf_trend) {
            var mtf = pick.mtf_trend;
            var tfLabels = ['5m','15m','30m','1H','4H','1D','1W'];
            var mtfCells = tfLabels.map(function(tf) {
                var d = mtf[tf];
                if (!d || d.trend === 'N/A') return '<span class="mtf-cell mtf-na">—</span>';
                var cls = d.trend === 'Bullish' ? 'mtf-bull' : d.trend === 'Bearish' ? 'mtf-bear' : 'mtf-neutral';
                return '<span class="mtf-cell ' + cls + '" title="' + tf + ': ' + d.trend + ' (' + d.strength + ')">' + tf + '</span>';
            }).join('');
            mtfRow = '<div class="mtf-strip">' + mtfCells + '</div>';
        }

        return '<tr onclick="showAlgorithmDetails(\'' + (pick.algorithmId || '') + '\')" style="cursor:pointer;" title="Click for full audit">' +
            '<td><strong>' + flameTag + pick.symbol + '</strong>' + mtfRow + '</td>' +
            '<td>' + pick.algorithm + '</td>' +
            '<td><span class="category-badge ' + pick.category + '">' + getCategoryName(pick.category) + '</span></td>' +
            '<td>' + safetyCell + '</td>' +
            perfCell('1w') +
            perfCell('1m') +
            perfCell('3m') +
            perfCell('ytd') +
            perfCell('1y') +
            '<td>' + gradeCell + '</td>' +
            '<td style="font-size:12px; white-space:nowrap;">' + formatEST(pick.entryDate) + '</td>' +
            '<td>' + priceFormat(entry) + '</td>' +
            '<td>' + priceFormat(current) + '</td>' +
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
    const categories = ['stock', 'penny', 'crypto', 'meme', 'forex'];
    const grid = document.getElementById('breakdownGrid');
    
    grid.innerHTML = categories.map(cat => {
        const algos = data.algorithms.filter(a => a.category === cat);
        if (algos.length === 0) return '';
        
        const avgReturn = algos.reduce((sum, a) => sum + a.totalReturn, 0) / algos.length;
        const avgWinRate = algos.reduce((sum, a) => sum + a.winRate, 0) / algos.length;
        const totalPicks = algos.reduce((sum, a) => sum + a.activePicks, 0);
        const bestAlgo = algos.reduce((best, a) => a.totalReturn > best.totalReturn ? a : best, algos[0]);
        
        return `
            <div class="breakdown-card">
                <div class="breakdown-header">
                    <div class="breakdown-title">${getCategoryIcon(cat)} ${getCategoryName(cat)}</div>
                    <div class="breakdown-return ${avgReturn >= 0 ? 'return-positive' : 'return-negative'}">
                        ${avgReturn >= 0 ? '+' : ''}${avgReturn.toFixed(1)}%
                    </div>
                </div>
                <div class="breakdown-stats">
                    <div class="breakdown-stat">
                        <div class="breakdown-stat-value">${algos.length}</div>
                        <div class="breakdown-stat-label">Algorithms</div>
                    </div>
                    <div class="breakdown-stat">
                        <div class="breakdown-stat-value">${avgWinRate.toFixed(1)}%</div>
                        <div class="breakdown-stat-label">Avg Win Rate</div>
                    </div>
                    <div class="breakdown-stat">
                        <div class="breakdown-stat-value">${totalPicks}</div>
                        <div class="breakdown-stat-label">Active Picks</div>
                    </div>
                </div>
                <div style="margin-top: 12px; font-size: 12px; color: #8888aa;">
                    Top: <span style="color: #e0e0f0;">${bestAlgo.name}</span> 
                    (${bestAlgo.totalReturn >= 0 ? '+' : ''}${bestAlgo.totalReturn.toFixed(1)}%)
                </div>
            </div>
        `;
    }).join('');
}

// Filter by category
function filterCategory(category) {
    currentCategory = category;
    
    // Update button states
    document.querySelectorAll('.cat-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.category === category) {
            btn.classList.add('active');
        }
    });
    
    renderLeaderboard(currentData);
}

// Sort leaderboard
function sortLeaderboard() {
    currentSort = document.getElementById('sortBy').value;
    renderLeaderboard(currentData);
}

// Filter picks
function filterPicks() {
    renderActivePicks(currentData);
}

// Algorithm methodology definitions - full transparency for external vetting
var ALGO_METHODOLOGY = {
    'etf-masters-live': {
        description: 'Scans major ETFs for trend-following entries using moving average crossovers.',
        symbols: ['SPY', 'QQQ', 'VTI'],
        indicators: ['10-day SMA', '50-day SMA'],
        entryLogic: 'BUY when 10-day SMA crosses ABOVE 50-day SMA (bullish golden cross).',
        exitLogic: 'SELL when 10-day SMA crosses BELOW 50-day SMA (bearish death cross).',
        dataSource: 'Yahoo Finance (yfinance) - 3 months daily OHLCV',
        scanFrequency: 'Every 15 minutes during US market hours (9:30 AM - 4:30 PM EST, Mon-Fri)',
        riskManagement: '$2,000 allocation per position, max 3 concurrent positions.',
        knownLimitations: 'MA crossovers are lagging indicators. May miss fast reversals. Not suited for choppy/sideways markets.'
    },
    'crypto-winners-live': {
        description: 'Identifies strong crypto momentum using RSI oversold conditions and 5-day price momentum.',
        symbols: ['BTC-USD', 'ETH-USD', 'SOL-USD'],
        indicators: ['RSI(14)', '5-day momentum'],
        entryLogic: 'BUY when RSI(14) < 30 (oversold) OR 5-day price return > 2%.',
        exitLogic: 'SELL when RSI(14) > 70 (overbought) or position held > 14 days.',
        dataSource: 'Yahoo Finance (yfinance) - 3 months daily OHLCV',
        scanFrequency: 'Every 15 min during market hours + every 4 hours on weekends (crypto 24/7)',
        riskManagement: '$2,000 allocation per position, max 3 concurrent positions.',
        knownLimitations: 'Momentum strategies can buy into extended rallies near tops. RSI can stay oversold in strong downtrends.'
    },
    'meme-scanner-live': {
        description: 'Detects meme coin breakouts via momentum combined with volume spikes.',
        symbols: ['DOGE-USD', 'SHIB-USD'],
        indicators: ['5-day momentum', '20-day avg volume', 'Volume spike (1.5x)'],
        entryLogic: 'BUY when 5-day return > 2% AND current volume > 1.5x 20-day average.',
        exitLogic: 'SELL when momentum turns negative or volume drops below average.',
        dataSource: 'Yahoo Finance (yfinance) - 3 months daily OHLCV',
        scanFrequency: 'Every 15 min during market hours + every 4 hours on weekends',
        riskManagement: '$2,000 allocation per position, max 3 concurrent positions.',
        knownLimitations: 'Meme coins are extremely volatile. Volume spikes can be false signals (manipulation). High risk.'
    },
    'penny-tracker-live': {
        description: 'Identifies penny stock breakouts based on unusual volume activity.',
        symbols: ['GME', 'AMC', 'PLTR', 'SOFI', 'HOOD'],
        indicators: ['20-day avg volume', 'Volume spike (2x threshold)'],
        entryLogic: 'BUY when current volume > 2x 20-day average volume (institutional accumulation signal).',
        exitLogic: 'SELL when volume normalizes or position held > 7 days.',
        dataSource: 'Yahoo Finance (yfinance) - 3 months daily OHLCV',
        scanFrequency: 'Every 15 minutes during US market hours (Mon-Fri)',
        riskManagement: '$2,000 allocation per position, max 3 concurrent positions.',
        knownLimitations: 'Penny stocks have wide spreads and low liquidity. Volume spikes may not sustain. High risk.'
    },
    'forex-scanner-live': {
        description: 'Trades major forex pairs using moving average crossover trend following.',
        symbols: ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X'],
        indicators: ['10-day SMA', '50-day SMA'],
        entryLogic: 'BUY when 10-day SMA crosses ABOVE 50-day SMA on daily chart.',
        exitLogic: 'SELL when 10-day SMA crosses BELOW 50-day SMA.',
        dataSource: 'Yahoo Finance (yfinance) - 3 months daily OHLCV',
        scanFrequency: 'Every 15 minutes during US market hours (Mon-Fri)',
        riskManagement: '$2,000 allocation per position, max 3 concurrent positions.',
        knownLimitations: 'Forex MA crossovers generate many false signals in ranging markets. Daily timeframe misses intraday moves.'
    },
    'rsi-momentum-live': {
        description: 'Pure RSI mean-reversion strategy on crypto assets.',
        symbols: ['BTC-USD', 'ETH-USD', 'SOL-USD', 'DOGE-USD', 'XRP-USD'],
        indicators: ['RSI(14)'],
        entryLogic: 'BUY when RSI(14) < 30 (oversold condition).',
        exitLogic: 'SELL when RSI(14) > 70 (overbought) or held > 14 days.',
        dataSource: 'Yahoo Finance (yfinance) - 3 months daily OHLCV',
        scanFrequency: 'Every 15 min + every 4 hours on weekends',
        riskManagement: '$2,000 allocation per position, max 3 concurrent positions.',
        knownLimitations: 'RSI can remain oversold for extended periods in bear markets. Works best in range-bound conditions.'
    },
    'alpha-hunter-live': {
        description: 'Multi-indicator confluence strategy requiring 2+ simultaneous signals for high-conviction entries.',
        symbols: ['BTC-USD', 'ETH-USD', 'SOL-USD', 'NVDA', 'TSLA'],
        indicators: ['RSI(14)', 'Bollinger Bands(20,2)', '5-day momentum'],
        entryLogic: 'BUY when 2 or more conditions met simultaneously: RSI < 35, price at lower Bollinger Band, 5-day momentum > 2%.',
        exitLogic: 'SELL when 0 conditions remain active or held > 14 days.',
        dataSource: 'Yahoo Finance (yfinance) - 3 months daily OHLCV',
        scanFrequency: 'Every 15 min + every 4 hours on weekends',
        riskManagement: '$2,000 allocation per position, max 3 concurrent positions.',
        knownLimitations: 'Confluence requirement means fewer trades but potentially higher quality. May miss fast-moving opportunities.'
    },
    'pump-watch-live': {
        description: 'Detects potential pump activity in crypto via extreme volume spikes.',
        symbols: ['BTC-USD', 'ETH-USD', 'SOL-USD', 'DOGE-USD', 'SHIB-USD'],
        indicators: ['20-day avg volume', 'Volume spike (2x threshold)'],
        entryLogic: 'BUY when current volume > 2x 20-day average volume (whale accumulation signal).',
        exitLogic: 'SELL when volume normalizes below 20-day average.',
        dataSource: 'Yahoo Finance (yfinance) - 3 months daily OHLCV',
        scanFrequency: 'Every 15 min + every 4 hours on weekends',
        riskManagement: '$2,000 allocation per position, max 3 concurrent positions.',
        knownLimitations: 'Volume spikes can be sell-offs not accumulation. Pump signals may precede dumps. Very high risk.'
    },
    'blue-chip-live': {
        description: 'Identifies oversold blue chip stocks using RSI and momentum confirmation.',
        symbols: ['AAPL', 'MSFT', 'NVDA', 'META'],
        indicators: ['RSI(14)', '5-day momentum', '20-day avg volume'],
        entryLogic: 'BUY when RSI(14) < 30 (oversold) OR (5-day return > 2% AND volume above average).',
        exitLogic: 'SELL when RSI(14) > 70 or position held > 14 days.',
        dataSource: 'Yahoo Finance (yfinance) - 3 months daily OHLCV',
        scanFrequency: 'Every 15 minutes during US market hours (Mon-Fri)',
        riskManagement: '$2,000 allocation per position, max 3 concurrent positions.',
        knownLimitations: 'RSI oversold on blue chips is rare and may indicate fundamental issues. Momentum can reverse quickly.'
    },
    'technical-momentum-live': {
        description: 'Bollinger Band squeeze breakouts on high-volatility tech stocks.',
        symbols: ['AMD', 'TSLA', 'NVDA'],
        indicators: ['Bollinger Bands(20,2)', '5-day momentum'],
        entryLogic: 'BUY when price touches lower Bollinger Band OR 5-day return > 2% (momentum breakout).',
        exitLogic: 'SELL when price touches upper Bollinger Band or momentum reverses.',
        dataSource: 'Yahoo Finance (yfinance) - 3 months daily OHLCV',
        scanFrequency: 'Every 15 minutes during US market hours (Mon-Fri)',
        riskManagement: '$2,000 allocation per position, max 3 concurrent positions.',
        knownLimitations: 'Bollinger touches in strong downtrends are not reversals. Momentum can be a lagging signal on volatile stocks.'
    }
};

// Show algorithm details modal with full audit and methodology
function showAlgorithmDetails(algoId) {
    if (!algoId || !currentData) return;
    var algo = currentData.algorithms.find(function(a) { return a.id === algoId; });
    if (!algo) return;

    var isLive = currentData.dataType === 'FORWARD_TEST';
    var method = ALGO_METHODOLOGY[algoId] || null;
    var returnClass = (algo.totalReturn || 0) >= 0 ? 'return-positive' : 'return-negative';

    // Find this algorithm's active picks
    var algoPicks = (currentData.activePicks || []).filter(function(p) {
        return p.algorithmId === algoId || p.algorithm === algo.name;
    });

    document.getElementById('modalAlgoName').textContent = algo.name + ' — Full Audit';

    // Tab system
    var html = '' +
    '<div style="display:flex; gap:4px; margin-bottom:16px; border-bottom:2px solid rgba(136,136,170,0.2); padding-bottom:8px;">' +
        '<button onclick="switchAlgoTab(\'overview\')" id="tabBtn_overview" style="background:#3b82f6; color:#fff; border:none; padding:8px 16px; border-radius:6px 6px 0 0; cursor:pointer; font-weight:600; font-size:13px;">Overview</button>' +
        '<button onclick="switchAlgoTab(\'methodology\')" id="tabBtn_methodology" style="background:transparent; color:#8888aa; border:none; padding:8px 16px; border-radius:6px 6px 0 0; cursor:pointer; font-weight:600; font-size:13px;">Methodology</button>' +
        '<button onclick="switchAlgoTab(\'picks\')" id="tabBtn_picks" style="background:transparent; color:#8888aa; border:none; padding:8px 16px; border-radius:6px 6px 0 0; cursor:pointer; font-weight:600; font-size:13px;">Active Picks (' + algoPicks.length + ')</button>' +
        '<button onclick="switchAlgoTab(\'audit\')" id="tabBtn_audit" style="background:transparent; color:#8888aa; border:none; padding:8px 16px; border-radius:6px 6px 0 0; cursor:pointer; font-weight:600; font-size:13px;">Audit Trail</button>' +
    '</div>';

    // === OVERVIEW TAB ===
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
    html += '<div style="display:flex; align-items:center; gap:8px;"><span class="category-badge ' + algo.category + '">' + getCategoryName(algo.category) + '</span>';
    html += '<span style="font-size:12px; color:#8888aa;">' + (isLive ? '🔴 LIVE FORWARD TEST' : '📊 BACKTESTED') + '</span></div>';
    html += '</div>';

    // === METHODOLOGY TAB ===
    html += '<div id="algoTab_methodology" style="display:none;">';
    if (method) {
        html += '<div style="background:rgba(59,130,246,0.1); border-left:3px solid #3b82f6; padding:12px; border-radius:4px; margin-bottom:14px;">' +
            '<div style="font-size:14px; font-weight:600; color:#e0e0f0; margin-bottom:4px;">' + method.description + '</div>' +
        '</div>';

        html += '<table style="width:100%; border-collapse:collapse; font-size:13px;">';
        html += '<tr style="border-bottom:1px solid rgba(136,136,170,0.2);"><td style="padding:8px; color:#8888aa; width:140px; vertical-align:top;">Symbols Scanned</td><td style="padding:8px; color:#e0e0f0;"><code>' + method.symbols.join(', ') + '</code></td></tr>';
        html += '<tr style="border-bottom:1px solid rgba(136,136,170,0.2);"><td style="padding:8px; color:#8888aa; vertical-align:top;">Indicators</td><td style="padding:8px; color:#e0e0f0;">' + method.indicators.join(', ') + '</td></tr>';
        html += '<tr style="border-bottom:1px solid rgba(136,136,170,0.2); background:rgba(34,197,94,0.05);"><td style="padding:8px; color:#22c55e; vertical-align:top; font-weight:600;">Entry Logic</td><td style="padding:8px; color:#e0e0f0;">' + method.entryLogic + '</td></tr>';
        html += '<tr style="border-bottom:1px solid rgba(136,136,170,0.2); background:rgba(239,68,68,0.05);"><td style="padding:8px; color:#ef4444; vertical-align:top; font-weight:600;">Exit Logic</td><td style="padding:8px; color:#e0e0f0;">' + method.exitLogic + '</td></tr>';
        html += '<tr style="border-bottom:1px solid rgba(136,136,170,0.2);"><td style="padding:8px; color:#8888aa; vertical-align:top;">Data Source</td><td style="padding:8px; color:#e0e0f0;">' + method.dataSource + '</td></tr>';
        html += '<tr style="border-bottom:1px solid rgba(136,136,170,0.2);"><td style="padding:8px; color:#8888aa; vertical-align:top;">Scan Frequency</td><td style="padding:8px; color:#e0e0f0;">' + method.scanFrequency + '</td></tr>';
        html += '<tr style="border-bottom:1px solid rgba(136,136,170,0.2);"><td style="padding:8px; color:#8888aa; vertical-align:top;">Risk Management</td><td style="padding:8px; color:#e0e0f0;">' + method.riskManagement + '</td></tr>';
        html += '<tr style="background:rgba(245,158,11,0.08);"><td style="padding:8px; color:#f59e0b; vertical-align:top; font-weight:600;">Known Limitations</td><td style="padding:8px; color:#fde68a;">' + method.knownLimitations + '</td></tr>';
        html += '</table>';

        html += '<div style="margin-top:14px; background:rgba(18,18,42,0.5); padding:10px; border-radius:6px; font-size:12px; color:#8888aa;">' +
            '<strong>Source Code:</strong> <a href="https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/KIMI_RISEOFTHECLAW/live_scanner.py" target="_blank" style="color:#60a5fa;">live_scanner.py on GitHub</a> — fully open source, auditable.' +
        '</div>';
    } else {
        html += '<div style="padding:20px; text-align:center; color:#8888aa;">Methodology details not available for this algorithm.</div>';
    }
    html += '</div>';

    // === ACTIVE PICKS TAB ===
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
            html += '</table>';
            html += '</div>';
        });
    } else {
        html += '<div style="padding:30px; text-align:center;">';
        html += '<div style="font-size:32px; margin-bottom:8px;">🔍</div>';
        html += '<div style="font-size:15px; font-weight:600; margin-bottom:6px;">No Active Picks</div>';
        html += '<div style="font-size:13px; color:#8888aa; line-height:1.6;">';
        if (method) {
            html += 'This algorithm is scanning <code>' + method.symbols.join(', ') + '</code> for entry signals.<br>';
            html += 'Entry condition: <span style="color:#e0e0f0;">' + method.entryLogic + '</span><br>';
            html += 'No symbols currently meet the entry threshold. This is normal — the algorithm waits for high-probability setups.';
        } else {
            html += 'Algorithm is scanning for signals. No entry conditions met yet.';
        }
        html += '</div></div>';
    }
    html += '</div>';

    // === AUDIT TRAIL TAB ===
    html += '<div id="algoTab_audit" style="display:none;">';
    html += '<div style="background:rgba(59,130,246,0.1); border-left:3px solid #3b82f6; padding:12px; border-radius:4px; margin-bottom:14px; font-size:13px;">' +
        '<strong>Full Transparency:</strong> Every signal, scan, and trade is logged with timestamps. ' +
        'Raw data files are publicly accessible for independent verification.' +
    '</div>';

    // Build audit entries from picks
    var auditItems = [];
    algoPicks.forEach(function(p) {
        auditItems.push({
            time: p.entryDate,
            type: 'ENTRY',
            detail: p.signal.toUpperCase() + ' ' + p.symbol + ' @ $' + (p.entryPrice || 0).toLocaleString(undefined, {maximumFractionDigits: 2}) + ' — Reason: ' + (p.reason || 'N/A')
        });
    });
    // Add scan events
    auditItems.push({
        time: currentData.lastUpdated || new Date().toISOString(),
        type: 'SCAN',
        detail: 'Market scan completed. ' + algoPicks.length + ' active position(s). ' + (method ? method.symbols.length : '?') + ' symbols checked.'
    });

    auditItems.sort(function(a, b) { return new Date(b.time) - new Date(a.time); });

    html += '<div style="max-height:300px; overflow-y:auto;">';
    auditItems.forEach(function(item) {
        var typeColor = item.type === 'ENTRY' ? '#22c55e' : item.type === 'EXIT' ? '#ef4444' : '#3b82f6';
        html += '<div style="background:rgba(18,18,42,0.5); padding:10px 12px; border-radius:6px; margin-bottom:6px; font-size:13px; border-left:3px solid ' + typeColor + ';">';
        html += '<div style="display:flex; justify-content:space-between; margin-bottom:4px;">';
        html += '<span style="color:' + typeColor + '; font-weight:600;">' + item.type + '</span>';
        html += '<span style="color:#8888aa; font-size:11px;">' + formatEST(item.time) + '</span>';
        html += '</div>';
        html += '<div style="color:#e0e0f0;">' + item.detail + '</div>';
        html += '</div>';
    });
    html += '</div>';

    html += '<div style="margin-top:14px; background:rgba(18,18,42,0.5); padding:10px; border-radius:6px;">';
    html += '<div style="font-weight:600; margin-bottom:6px; font-size:13px;">Verify Raw Data</div>';
    html += '<div style="font-size:12px; color:#8888aa; line-height:1.8;">';
    html += '<a href="data/live_competition.json" target="_blank" style="color:#60a5fa;">live_competition.json</a> — All algorithm positions & trades<br>';
    html += '<a href="data/active_picks.json" target="_blank" style="color:#60a5fa;">active_picks.json</a> — Flat list of all active picks<br>';
    html += '<a href="data/audit_log.json" target="_blank" style="color:#60a5fa;">audit_log.json</a> — Append-only signal log<br>';
    html += '<a href="https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/KIMI_RISEOFTHECLAW/live_scanner.py" target="_blank" style="color:#60a5fa;">Source Code (GitHub)</a> — Open source scanner logic';
    html += '</div></div>';
    html += '</div>';

    document.getElementById('modalBody').innerHTML = html;
    document.getElementById('algoModal').classList.add('active');
}

// Switch tabs within algorithm detail modal
function switchAlgoTab(tab) {
    var tabs = ['overview', 'methodology', 'picks', 'audit'];
    tabs.forEach(function(t) {
        var el = document.getElementById('algoTab_' + t);
        var btn = document.getElementById('tabBtn_' + t);
        if (el) el.style.display = (t === tab) ? 'block' : 'none';
        if (btn) {
            btn.style.background = (t === tab) ? '#3b82f6' : 'transparent';
            btn.style.color = (t === tab) ? '#ffffff' : '#8888aa';
        }
    });
}

// Close modal
function closeModal() {
    document.getElementById('algoModal').classList.remove('active');
}

// Close modal on outside click
document.addEventListener('click', (e) => {
    const modal = document.getElementById('algoModal');
    if (e.target === modal) {
        closeModal();
    }
});

// Auto refresh
function startAutoRefresh() {
    const interval = parseInt(document.getElementById('refreshInterval')?.value || '60');
    
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    
    if (interval > 0) {
        refreshInterval = setInterval(() => {
            loadDashboardData();
        }, interval * 1000);
    }
}

function setRefreshInterval() {
    startAutoRefresh();
}

function manualRefresh() {
    loadDashboardData();
}

// Update last updated timestamp (in EST)
function updateLastUpdated() {
    var ts = (currentData && currentData.lastUpdated) ? new Date(currentData.lastUpdated) : new Date();
    try {
        document.getElementById('lastUpdated').textContent =
            ts.toLocaleTimeString('en-US', { timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' EST';
    } catch (e) {
        document.getElementById('lastUpdated').textContent =
            ts.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
}

// Export data
function exportData() {
    if (!currentData) return;
    
    const exportObj = {
        timestamp: new Date().toISOString(),
        algorithms: currentData.algorithms,
        activePicks: currentData.activePicks
    };
    
    const blob = new Blob([JSON.stringify(exportObj, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `rise-of-the-claw-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
