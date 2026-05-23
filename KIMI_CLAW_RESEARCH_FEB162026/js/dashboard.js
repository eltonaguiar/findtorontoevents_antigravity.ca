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
    
    // Top performer
    const topPerformer = algorithms.reduce((best, algo) => 
        algo.totalReturn > best.totalReturn ? algo : best
    );
    document.getElementById('topPerformer').textContent = topPerformer.name;
    document.getElementById('topPerformerReturn').textContent = 
        `${topPerformer.totalReturn >= 0 ? '+' : ''}${topPerformer.totalReturn.toFixed(2)}%`;
    document.getElementById('topPerformerReturn').className = 
        `perf-sub ${topPerformer.totalReturn >= 0 ? 'return-positive' : 'return-negative'}`;
    
    // Best win rate
    const bestWinRate = algorithms.reduce((best, algo) => 
        algo.winRate > best.winRate ? algo : best
    );
    document.getElementById('bestWinRate').textContent = `${bestWinRate.winRate.toFixed(1)}%`;
    document.getElementById('bestWinRateAlgo').textContent = bestWinRate.name;
    
    // Most active (by number of trades)
    const mostActive = algorithms.reduce((most, algo) =>
        (algo.activePicks || algo.numTrades || 0) > (most.activePicks || most.numTrades || 0) ? algo : most
    );
    document.getElementById('mostActive').textContent = mostActive.name;
    document.getElementById('mostActiveCount').textContent = `${mostActive.activePicks} picks`;
    
    // Best Sharpe
    const bestSharpe = algorithms.reduce((best, algo) => 
        algo.sharpeRatio > best.sharpeRatio ? algo : best
    );
    document.getElementById('bestSharpe').textContent = bestSharpe.sharpeRatio.toFixed(2);
    document.getElementById('bestSharpeAlgo').textContent = bestSharpe.name;
    
    // Lowest drawdown
    const lowestDrawdown = algorithms.reduce((best, algo) => 
        algo.maxDrawdown > best.maxDrawdown ? algo : best
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
    
    tbody.innerHTML = algorithms.map((algo, index) => {
        const rank = index + 1;
        const rankClass = rank === 1 ? 'gold' : rank === 2 ? 'silver' : rank === 3 ? 'bronze' : '';
        const rowClass = rank <= 3 ? `rank-${rank}` : '';
        const returnClass = algo.totalReturn >= 0 ? 'return-positive' : 'return-negative';
        
        // Get last 7 days for sparkline
        const sparklineData = algo.history.slice(-7).map(h => h.value);
        
        return `
            <tr class="${rowClass}" onclick="showAlgorithmDetails('${algo.id}')" style="cursor: pointer;">
                <td><div class="rank-badge ${rankClass}">${rank}</div></td>
                <td>
                    <div class="algo-name-cell">
                        <div class="algo-avatar">${algo.avatar}</div>
                        <div class="algo-info">
                            <div class="algo-name">${algo.name}</div>
                            <div class="algo-category">${getCategoryName(algo.category)}</div>
                        </div>
                    </div>
                </td>
                <td><span class="category-badge ${algo.category}">${getCategoryName(algo.category)}</span></td>
                <td>$${algo.currentValue.toLocaleString()}</td>
                <td class="${returnClass}">${algo.totalReturn >= 0 ? '+' : ''}${algo.totalReturn.toFixed(2)}%</td>
                <td>${algo.winRate.toFixed(1)}%</td>
                <td>${algo.activePicks}</td>
                <td>${algo.sharpeRatio.toFixed(2)}</td>
                <td style="color: ${algo.maxDrawdown < -15 ? '#ef4444' : '#8888aa'}">${algo.maxDrawdown.toFixed(1)}%</td>
                <td>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span class="${sparklineData[sparklineData.length-1] >= sparklineData[0] ? 'return-positive' : 'return-negative'}">
                            ${((sparklineData[sparklineData.length-1] - sparklineData[0]) / sparklineData[0] * 100).toFixed(1)}%
                        </span>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// Render active picks
function renderActivePicks(data) {
    const tbody = document.getElementById('picksBody');
    let picks = [...data.activePicks];
    
    // Apply category filter
    const categoryFilter = document.getElementById('pickCategoryFilter')?.value || 'all';
    if (categoryFilter !== 'all') {
        picks = picks.filter(p => p.category === categoryFilter);
    }
    
    // Apply search filter
    const searchTerm = document.getElementById('pickSearch')?.value?.toLowerCase() || '';
    if (searchTerm) {
        picks = picks.filter(p => 
            p.symbol.toLowerCase().includes(searchTerm) ||
            p.algorithm.toLowerCase().includes(searchTerm)
        );
    }
    
    if (picks.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="loading-cell">No active picks found.</td></tr>`;
        return;
    }
    
    tbody.innerHTML = picks.map(pick => {
        const plClass = pick.plPercent >= 0 ? 'return-positive' : 'return-negative';
        const signalClass = pick.signal === 'buy' ? 'buy' : pick.signal === 'sell' ? 'sell' : 'hold';
        
        return `
            <tr>
                <td><strong>${pick.symbol}</strong></td>
                <td>${pick.algorithm}</td>
                <td><span class="category-badge ${pick.category}">${getCategoryName(pick.category)}</span></td>
                <td>${typeof pick.entryPrice === 'number' && pick.entryPrice < 1 ? 
                    pick.entryPrice.toFixed(6) : pick.entryPrice}</td>
                <td>${typeof pick.currentPrice === 'number' && pick.currentPrice < 1 ? 
                    pick.currentPrice.toFixed(6) : pick.currentPrice}</td>
                <td class="${plClass}">${pick.plPercent >= 0 ? '+' : ''}${pick.plPercent.toFixed(2)}%</td>
                <td>${pick.daysHeld}d</td>
                <td><span class="signal-badge ${signalClass}">${pick.signal.toUpperCase()}</span></td>
            </tr>
        `;
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
        const bestAlgo = algos.reduce((best, a) => a.totalReturn > best.totalReturn ? a : best);
        
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

// Show algorithm details modal
function showAlgorithmDetails(algoId) {
    const algo = currentData.algorithms.find(a => a.id === algoId);
    if (!algo) return;
    
    document.getElementById('modalAlgoName').textContent = algo.name;
    
    const returnClass = algo.totalReturn >= 0 ? 'return-positive' : 'return-negative';
    
    var annReturn = algo.annualizedReturn ? algo.annualizedReturn.toFixed(2) : '--';
    var sortinoVal = algo.sortinoRatio ? algo.sortinoRatio.toFixed(2) : '--';
    var calmarVal = algo.calmarRatio ? algo.calmarRatio.toFixed(2) : '--';
    var pfVal = algo.profitFactor ? algo.profitFactor.toFixed(2) : '--';
    var volVal = algo.volatility ? algo.volatility.toFixed(1) : '--';
    var avgWinVal = algo.avgWin ? algo.avgWin.toFixed(2) : '--';
    var avgLossVal = algo.avgLoss ? algo.avgLoss.toFixed(2) : '--';

    document.getElementById('modalBody').innerHTML = `
        <p style="color: #8888aa; margin-bottom: 16px; font-size: 13px;">${algo.description || ''}</p>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 24px;">
            <div style="background: rgba(18, 18, 42, 0.5); padding: 16px; border-radius: 12px;">
                <div style="font-size: 12px; color: #8888aa; text-transform: uppercase;">Portfolio Value</div>
                <div style="font-size: 24px; font-weight: 700;">$${algo.currentValue.toLocaleString()}</div>
            </div>
            <div style="background: rgba(18, 18, 42, 0.5); padding: 16px; border-radius: 12px;">
                <div style="font-size: 12px; color: #8888aa; text-transform: uppercase;">Total Return</div>
                <div style="font-size: 24px; font-weight: 700;" class="${returnClass}">
                    ${algo.totalReturn >= 0 ? '+' : ''}${algo.totalReturn.toFixed(2)}%
                </div>
            </div>
            <div style="background: rgba(18, 18, 42, 0.5); padding: 16px; border-radius: 12px;">
                <div style="font-size: 12px; color: #8888aa; text-transform: uppercase;">Annualized Return</div>
                <div style="font-size: 24px; font-weight: 700;" class="${returnClass}">${annReturn}%</div>
            </div>
            <div style="background: rgba(18, 18, 42, 0.5); padding: 16px; border-radius: 12px;">
                <div style="font-size: 12px; color: #8888aa; text-transform: uppercase;">Win Rate</div>
                <div style="font-size: 24px; font-weight: 700;">${algo.winRate.toFixed(1)}%</div>
            </div>
        </div>

        <div style="margin-bottom: 16px;">
            <div style="font-size: 14px; font-weight: 600; margin-bottom: 12px;">Performance Metrics</div>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
                <div style="text-align: center; padding: 12px; background: rgba(18, 18, 42, 0.3); border-radius: 8px;">
                    <div style="font-size: 20px; font-weight: 700;">${algo.sharpeRatio.toFixed(2)}</div>
                    <div style="font-size: 11px; color: #8888aa;">Sharpe Ratio</div>
                </div>
                <div style="text-align: center; padding: 12px; background: rgba(18, 18, 42, 0.3); border-radius: 8px;">
                    <div style="font-size: 20px; font-weight: 700;">${sortinoVal}</div>
                    <div style="font-size: 11px; color: #8888aa;">Sortino Ratio</div>
                </div>
                <div style="text-align: center; padding: 12px; background: rgba(18, 18, 42, 0.3); border-radius: 8px;">
                    <div style="font-size: 20px; font-weight: 700;">${calmarVal}</div>
                    <div style="font-size: 11px; color: #8888aa;">Calmar Ratio</div>
                </div>
                <div style="text-align: center; padding: 12px; background: rgba(18, 18, 42, 0.3); border-radius: 8px;">
                    <div style="font-size: 20px; font-weight: 700; color: ${algo.maxDrawdown < -15 ? '#ef4444' : '#e0e0f0'};">${algo.maxDrawdown.toFixed(1)}%</div>
                    <div style="font-size: 11px; color: #8888aa;">Max Drawdown</div>
                </div>
                <div style="text-align: center; padding: 12px; background: rgba(18, 18, 42, 0.3); border-radius: 8px;">
                    <div style="font-size: 20px; font-weight: 700;">${pfVal}</div>
                    <div style="font-size: 11px; color: #8888aa;">Profit Factor</div>
                </div>
                <div style="text-align: center; padding: 12px; background: rgba(18, 18, 42, 0.3); border-radius: 8px;">
                    <div style="font-size: 20px; font-weight: 700;">${volVal}%</div>
                    <div style="font-size: 11px; color: #8888aa;">Volatility</div>
                </div>
                <div style="text-align: center; padding: 12px; background: rgba(18, 18, 42, 0.3); border-radius: 8px;">
                    <div style="font-size: 20px; font-weight: 700;">${algo.numTrades || algo.activePicks || 0}</div>
                    <div style="font-size: 11px; color: #8888aa;">Total Trades</div>
                </div>
                <div style="text-align: center; padding: 12px; background: rgba(18, 18, 42, 0.3); border-radius: 8px;">
                    <div style="font-size: 20px; font-weight: 700; color: #22c55e;">${avgWinVal}%</div>
                    <div style="font-size: 11px; color: #8888aa;">Avg Win</div>
                </div>
                <div style="text-align: center; padding: 12px; background: rgba(18, 18, 42, 0.3); border-radius: 8px;">
                    <div style="font-size: 20px; font-weight: 700; color: #ef4444;">${avgLossVal}%</div>
                    <div style="font-size: 11px; color: #8888aa;">Avg Loss</div>
                </div>
            </div>
        </div>

        <div style="font-size: 14px; font-weight: 600; margin-bottom: 12px;">Details</div>
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
            <span class="category-badge ${algo.category}">${getCategoryName(algo.category)}</span>
            <span style="color: #8888aa; font-size: 12px;">Asset: ${algo.asset || '--'}</span>
        </div>
        <div style="color: #8888aa; font-size: 12px; margin-top: 8px;">
            Starting capital: $${(algo.startingValue || 100000).toLocaleString()} |
            Status: <span style="color: ${algo.status === 'ACTIVE' ? '#22c55e' : '#f59e0b'};">${algo.status || 'ACTIVE'}</span>
        </div>
    `;
    
    document.getElementById('algoModal').classList.add('active');
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

// Update last updated timestamp - shows when backtest data was generated
async function updateLastUpdated() {
    var el = document.getElementById('lastUpdated');
    try {
        var runInfo = await fetchLastRunInfo();
        if (runInfo && runInfo.lastRun) {
            var d = new Date(runInfo.lastRun);
            el.textContent = 'Data: ' + d.toLocaleDateString('en-US', {
                month: 'short', day: 'numeric'
            }) + ' ' + d.toLocaleTimeString('en-US', {
                hour: '2-digit', minute: '2-digit'
            });
            return;
        }
    } catch (e) { /* fallback below */ }
    var now = new Date();
    el.textContent = now.toLocaleTimeString('en-US', {
        hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
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
