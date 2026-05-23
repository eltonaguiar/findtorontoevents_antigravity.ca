/**
 * Audit Trail - Full transparency about data sources
 *
 * - Clearly shows what is LIVE forward-facing vs BACKTESTED
 * - In LIVE mode with zero trades: explains why and when to expect trades
 * - Shows full audit log of every trade entry/exit with timestamps
 * - Links to raw data files for independent verification
 */

document.addEventListener('DOMContentLoaded', function() {
    var badge = document.getElementById('dataSourceBadge');
    if (badge) badge.addEventListener('click', showDataAuditTrail);
    setupEmptyStateMonitor();
});

function showDataAuditTrail() {
    var isLive = (typeof currentDataMode !== 'undefined') && currentDataMode === 'live';
    var modal = document.createElement('div');
    modal.className = 'modal active';
    modal.style.zIndex = '10000';

    var auditEntries = '';
    if (typeof currentData !== 'undefined' && currentData && currentData.auditTrail && currentData.auditTrail.length > 0) {
        auditEntries = currentData.auditTrail.map(function(entry) {
            return '<div style="background: rgba(18,18,42,0.5); padding: 10px; border-radius: 6px; margin-bottom: 6px; font-size: 13px;">' +
                '<span style="color: #8888aa;">' + (entry.timestamp || '--') + '</span> ' +
                '<span style="color: ' + (entry.action === 'OPEN' ? '#22c55e' : entry.action === 'CLOSE' ? '#ef4444' : '#3b82f6') + '; font-weight: 600;">' + (entry.action || '') + '</span> ' +
                (entry.symbol ? '<strong>' + entry.symbol + '</strong> ' : '') +
                (entry.algorithm ? '(' + entry.algorithm + ') ' : '') +
                (entry.price ? 'at $' + entry.price : '') +
                '<div style="color: #666; font-size: 11px; margin-top: 2px;">Source: ' + (entry.source || 'N/A') + '</div>' +
            '</div>';
        }).join('');
    } else {
        auditEntries = '<div style="text-align: center; padding: 20px; color: #8888aa;">' +
            (isLive ? 'No trades recorded yet. All algorithms are in SCANNING mode.' : 'Backtest run data shown above.') +
        '</div>';
    }

    var liveContent = '' +
        '<div style="background: #1e3a5f; padding: 16px; border-radius: 8px; margin-bottom: 16px; border-left: 4px solid #3b82f6;">' +
            '<div style="font-size: 18px; font-weight: 700; margin-bottom: 4px;">🔴 LIVE Forward-Facing Paper Trading</div>' +
            '<div style="color: #bfdbfe; font-size: 13px;">' +
                'Competition launched <strong>February 16, 2026</strong>. ' +
                'Each algorithm started with <strong>$10,000</strong>. ' +
                'Only real, timestamped trades appear on this dashboard.' +
            '</div>' +
        '</div>' +

        '<div style="background: rgba(59,130,246,0.1); border-left: 3px solid #60a5fa; padding: 14px; border-radius: 4px; margin-bottom: 16px;">' +
            '<div style="font-weight: 600; color: #60a5fa; margin-bottom: 6px;">Why no trades yet?</div>' +
            '<div style="font-size: 13px; color: #e0e0f0; line-height: 1.6;">' +
                'All 10 algorithms are actively scanning markets for entry conditions. ' +
                'Trade signals trigger when specific criteria are met (RSI thresholds, momentum breakouts, ' +
                'volume spikes, etc.). The algorithms will not force trades &mdash; they wait for high-probability setups.' +
            '</div>' +
            '<div style="font-size: 13px; color: #8888aa; margin-top: 8px;">' +
                '<strong>Crypto algorithms</strong> scan 24/7 &mdash; expect signals within 1-3 days.<br>' +
                '<strong>Stock algorithms</strong> scan during US market hours (9:30 AM - 4:00 PM EST).<br>' +
                '<strong>Forex algorithms</strong> scan during London/NY overlap (8 AM - 12 PM EST).' +
            '</div>' +
        '</div>' +

        '<div style="margin-bottom: 16px;">' +
            '<h4 style="margin-bottom: 8px; color: #e0e0f0;">Trade Audit Log</h4>' +
            '<div style="max-height: 200px; overflow-y: auto;">' + auditEntries + '</div>' +
        '</div>' +

        '<div style="background: rgba(18,18,42,0.5); padding: 12px; border-radius: 6px; margin-bottom: 12px;">' +
            '<div style="font-weight: 600; margin-bottom: 4px;">Verify Data</div>' +
            '<div style="font-size: 12px; color: #8888aa;">' +
                'Raw data: <a href="data/live_competition.json" target="_blank" style="color: #60a5fa;">live_competition.json</a> | ' +
                '<a href="data/active_picks.json" target="_blank" style="color: #60a5fa;">active_picks.json</a>' +
            '</div>' +
        '</div>';

    var backtestContent = '' +
        '<div style="background: #3d2e0f; padding: 16px; border-radius: 8px; margin-bottom: 16px; border-left: 4px solid #f59e0b;">' +
            '<div style="font-size: 18px; font-weight: 700; margin-bottom: 4px;">📊 BACKTESTED Historical Data</div>' +
            '<div style="color: #fde68a; font-size: 13px;">' +
                'Results from running 5 Tier 1 strategies against <strong>real Yahoo Finance market data</strong> (2020 to present). ' +
                'Generated daily by GitHub Actions.' +
            '</div>' +
        '</div>' +

        '<div style="background: rgba(245,158,11,0.1); border-left: 3px solid #f59e0b; padding: 14px; border-radius: 4px; margin-bottom: 16px;">' +
            '<div style="font-weight: 600; color: #f59e0b; margin-bottom: 6px;">Important Disclaimer</div>' +
            '<div style="font-size: 13px; color: #e0e0f0; line-height: 1.6;">' +
                'Past performance does NOT guarantee future results. ' +
                'Backtests are run against historical data and suffer from look-ahead bias, survivorship bias, and other limitations. ' +
                'These results show how strategies WOULD HAVE performed, not how they WILL perform.' +
            '</div>' +
        '</div>' +

        '<div style="background: rgba(18,18,42,0.5); padding: 12px; border-radius: 6px; margin-bottom: 12px;">' +
            '<div style="font-weight: 600; margin-bottom: 6px;">Data Sources</div>' +
            '<div style="font-size: 13px; color: #8888aa; line-height: 1.8;">' +
                'Market data: Yahoo Finance (SPY, QQQ, BTC-USD)<br>' +
                'Backtest period: 2020-01-01 to present<br>' +
                'Engine: Python backtest_framework.py<br>' +
                'Schedule: Re-run daily at 6 AM UTC via GitHub Actions<br>' +
                (typeof currentData !== 'undefined' && currentData && currentData.generatedAt ?
                    'Last run: ' + new Date(currentData.generatedAt).toLocaleString() : '') +
            '</div>' +
        '</div>' +

        '<div style="margin-bottom: 16px;">' +
            '<h4 style="margin-bottom: 8px; color: #e0e0f0;">Backtest Run Log</h4>' +
            '<div style="max-height: 200px; overflow-y: auto;">' + auditEntries + '</div>' +
        '</div>' +

        '<div style="background: rgba(18,18,42,0.5); padding: 12px; border-radius: 6px;">' +
            '<div style="font-weight: 600; margin-bottom: 4px;">Verify Data</div>' +
            '<div style="font-size: 12px; color: #8888aa;">' +
                'Raw results: <a href="/kimi-claw/data/dashboard_data.json" target="_blank" style="color: #f59e0b;">dashboard_data.json</a> | ' +
                '<a href="/kimi-claw/data/tier1_summary.json" target="_blank" style="color: #f59e0b;">tier1_summary.json</a><br>' +
                'GitHub: <a href="https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/workflows/backtest-and-deploy.yml" target="_blank" style="color: #f59e0b;">Workflow runs</a>' +
            '</div>' +
        '</div>';

    modal.innerHTML = '' +
        '<div class="modal-content" style="max-width: 650px;">' +
            '<div class="modal-header">' +
                '<h3>📋 Data Audit Trail</h3>' +
                '<button class="modal-close" onclick="this.closest(\'.modal\').remove()">&times;</button>' +
            '</div>' +
            '<div class="modal-body">' +
                (isLive ? liveContent : backtestContent) +
                '<div style="margin-top: 16px; padding-top: 12px; border-top: 1px solid rgba(136,136,170,0.2); font-size: 11px; color: #666;">' +
                    'Audit trail generated: ' + new Date().toLocaleString() +
                '</div>' +
            '</div>' +
        '</div>';

    document.body.appendChild(modal);
    modal.addEventListener('click', function(e) {
        if (e.target === modal) modal.remove();
    });
}

/**
 * Monitor for empty states and add informative messages
 */
function setupEmptyStateMonitor() {
    var observer = new MutationObserver(function() { checkEmptyStates(); });
    observer.observe(document.body, { childList: true, subtree: true });
    setTimeout(checkEmptyStates, 1000);
}

function checkEmptyStates() {
    var isLive = (typeof currentDataMode !== 'undefined') && currentDataMode === 'live';

    // Active picks empty state
    var picksBody = document.getElementById('picksBody');
    if (picksBody) {
        var rows = picksBody.querySelectorAll('tr');
        if (rows.length === 1) {
            var cell = rows[0].querySelector('td');
            if (cell && cell.colSpan > 1 && cell.textContent.indexOf('No active picks') !== -1) {
                if (!cell.querySelector('.audit-note') && isLive) {
                    var note = document.createElement('div');
                    note.className = 'audit-note';
                    note.style.cssText = 'margin-top: 8px; font-size: 12px; color: #60a5fa; font-style: italic;';
                    note.textContent = 'All algorithms are scanning for entry signals. Trades will appear here when conditions are met.';
                    cell.appendChild(note);
                }
            }
        }
    }

    // Category breakdown empty state
    var breakdownGrid = document.getElementById('breakdownGrid');
    if (breakdownGrid && breakdownGrid.children.length === 0) {
        if (!breakdownGrid.querySelector('.empty-message')) {
            breakdownGrid.innerHTML = '' +
                '<div class="empty-message" style="grid-column: 1 / -1; text-align: center; padding: 40px; background: rgba(18,18,42,0.5); border-radius: 12px;">' +
                    '<div style="font-size: 48px; margin-bottom: 16px;">📊</div>' +
                    '<div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">' +
                        (isLive ? 'Waiting for First Trades' : 'No Backtest Data Available') +
                    '</div>' +
                    '<div style="font-size: 14px; color: #8888aa;">' +
                        (isLive ?
                            'Category performance will populate as algorithms execute trades.<br>Crypto scans run 24/7; stock scans run during US market hours.' :
                            'Backtest data will appear after the next GitHub Actions run.') +
                    '</div>' +
                '</div>';
        }
    }
}
