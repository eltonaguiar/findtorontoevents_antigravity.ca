// Chart.js configuration and portfolio chart
let portfolioChart = null;
let currentTimeRange = '7d';

const CHART_COLORS = [
    '#f59e0b', // Gold
    '#06b6d4', // Cyan
    '#a855f7', // Purple
    '#22c55e', // Green
    '#ef4444', // Red
    '#3b82f6', // Blue
    '#e879f9', // Pink
    '#f97316', // Orange
    '#14b8a6', // Teal
    '#8b5cf6', // Violet
    '#f43f5e', // Rose
    '#10b981', // Emerald
];

function initPortfolioChart(data) {
    const ctx = document.getElementById('portfolioChart').getContext('2d');
    
    if (portfolioChart) {
        portfolioChart.destroy();
    }
    
    const datasets = data.algorithms.map((algo, index) => ({
        label: algo.name,
        data: algo.history.map(h => ({
            x: new Date(h.date),
            y: h.value
        })),
        borderColor: CHART_COLORS[index % CHART_COLORS.length],
        backgroundColor: CHART_COLORS[index % CHART_COLORS.length] + '20',
        borderWidth: 2,
        fill: false,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 6,
        pointHoverBackgroundColor: CHART_COLORS[index % CHART_COLORS.length],
        pointHoverBorderColor: '#fff',
        pointHoverBorderWidth: 2,
    }));
    
    portfolioChart = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(18, 18, 42, 0.95)',
                    titleColor: '#e0e0f0',
                    bodyColor: '#e0e0f0',
                    borderColor: 'rgba(42, 42, 74, 0.6)',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true,
                    callbacks: {
                        title: function(context) {
                            const date = new Date(context[0].parsed.x);
                            return date.toLocaleDateString('en-US', { 
                                month: 'short', 
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                            });
                        },
                        label: function(context) {
                            const value = context.parsed.y;
                            const return_pct = ((value - 10000) / 10000 * 100).toFixed(2);
                            return `${context.dataset.label}: $${value.toLocaleString()} (${return_pct >= 0 ? '+' : ''}${return_pct}%)`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day',
                        displayFormats: {
                            day: 'MMM d'
                        }
                    },
                    grid: {
                        color: 'rgba(42, 42, 74, 0.3)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#8888aa',
                        font: { size: 11 }
                    }
                },
                y: {
                    beginAtZero: false,
                    grid: {
                        color: 'rgba(42, 42, 74, 0.3)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#8888aa',
                        font: { size: 11 },
                        callback: function(value) {
                            return '$' + (value / 1000).toFixed(1) + 'k';
                        }
                    }
                }
            }
        }
    });
    
    // Update custom legend
    updateChartLegend(data.algorithms);
}

function updateChartLegend(algorithms) {
    const legend = document.getElementById('chartLegend');
    if (!legend) return;
    
    legend.innerHTML = algorithms.map((algo, index) => `
        <div class="legend-item" onclick="toggleDataset(${index})" style="cursor: pointer; display: flex; align-items: center; gap: 6px;">
            <span style="width: 12px; height: 12px; border-radius: 2px; background: ${CHART_COLORS[index % CHART_COLORS.length]};"></span>
            <span style="color: #8888aa; font-size: 12px;">${algo.name}</span>
        </div>
    `).join('');
}

function toggleDataset(index) {
    if (!portfolioChart) return;
    
    const meta = portfolioChart.getDatasetMeta(index);
    meta.hidden = meta.hidden === null ? !portfolioChart.data.datasets[index].hidden : null;
    portfolioChart.update();
}

function setTimeRange(range) {
    currentTimeRange = range;
    
    // Update button states
    document.querySelectorAll('.time-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.textContent.toLowerCase().includes(range.toLowerCase())) {
            btn.classList.add('active');
        }
    });
    
    // Reload chart with filtered data
    loadDashboardData();
}

function filterDataByTimeRange(data, range) {
    const now = new Date();
    let cutoff = new Date();
    
    switch(range) {
        case '7d':
            cutoff.setDate(now.getDate() - 7);
            break;
        case '30d':
            cutoff.setDate(now.getDate() - 30);
            break;
        case '90d':
            cutoff.setDate(now.getDate() - 90);
            break;
        default:
            return data;
    }
    
    return {
        ...data,
        algorithms: data.algorithms.map(algo => ({
            ...algo,
            history: algo.history.filter(h => new Date(h.date) >= cutoff)
        }))
    };
}

// Sparkline chart for leaderboard
function createSparkline(canvasId, data) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map((_, i) => i),
            datasets: [{
                data: data,
                borderColor: data[data.length - 1] >= data[0] ? '#22c55e' : '#ef4444',
                backgroundColor: 'transparent',
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { display: false },
                y: { display: false }
            },
            layout: { padding: 0 }
        }
    });
}
