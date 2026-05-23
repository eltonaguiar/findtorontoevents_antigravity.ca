/**
 * Backtest Rankings — Rise of the Claw v3
 * Loads data/backtest_rankings.json and renders 5-year historical results.
 * Updated weekly by the vectorized backtest engine.
 */

var backtestLoaded = false;

function btRankBadge(rankLabel) {
    if (rankLabel === 'promoted')
        return '<span style="background:rgba(34,197,94,0.2);color:#22c55e;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;">PROMOTED</span>';
    if (rankLabel === 'eliminated')
        return '<span style="background:rgba(239,68,68,0.2);color:#ef4444;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;">ELIMINATED</span>';
    if (rankLabel === 'testing_ok')
        return '<span style="background:rgba(59,130,246,0.2);color:#60a5fa;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;">TESTING OK</span>';
    return '<span style="background:rgba(136,136,170,0.2);color:#8888aa;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;">TESTING</span>';
}

function btTierBadge(tier) {
    if (tier === 'TIER_1')
        return '<span style="background:rgba(59,130,246,0.2);color:#60a5fa;padding:2px 6px;border-radius:8px;font-size:10px;font-weight:600;">TIER 1</span>';
    return '<span style="background:rgba(136,136,170,0.15);color:#8888aa;padding:2px 6px;border-radius:8px;font-size:10px;font-weight:600;">SCOUT</span>';
}

function btScorebar(score) {
    var pct = Math.min(Math.max(score, 0), 100);
    var color = score >= 70 ? '#22c55e' : score >= 50 ? '#f59e0b' : score >= 35 ? '#3b82f6' : '#ef4444';
    return '<div style="display:flex;align-items:center;gap:6px;">' +
        '<div style="flex:1;background:rgba(136,136,170,0.15);border-radius:4px;height:6px;overflow:hidden;">' +
            '<div style="width:' + pct + '%;height:100%;background:' + color + ';border-radius:4px;"></div>' +
        '</div>' +
        '<span style="color:' + color + ';font-weight:700;min-width:32px;text-align:right;">' + score + '</span>' +
    '</div>';
}

async function loadBacktest() {
    var container = document.getElementById('backtestBody');
    var metaEl    = document.getElementById('backtestMeta');
    if (!container) return;

    try {
        var cacheBust = '?_=' + Date.now();
        var basePath = (typeof getBasePath === 'function') ? getBasePath() : '/riseoftheclaw/';
        var resp = await fetch(basePath + 'data/backtest_rankings.json' + cacheBust);

        if (!resp.ok) {
            container.innerHTML = '<tr><td colspan="9" class="loading-cell" style="color:#f59e0b;">Backtest data not yet generated — runs every Sunday 03:00 UTC</td></tr>';
            return;
        }

        var d = await resp.json();
        if (!d || !d.rankings || d.rankings.length === 0) {
            container.innerHTML = '<tr><td colspan="9" class="loading-cell">No backtest data.</td></tr>';
            return;
        }

        if (metaEl) {
            var promoted  = d.rankings.filter(function(r) { return r.rank_label === 'promoted'; }).length;
            var elim      = d.rankings.filter(function(r) { return r.rank_label === 'eliminated'; }).length;
            var upd = d.lastUpdated ? d.lastUpdated.substring(0, 10) : '';
            metaEl.innerHTML =
                '<span style="background:rgba(245,158,11,0.15);color:#f59e0b;border:1px solid rgba(245,158,11,0.3);' +
                'padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600;">' +
                d.period + ' · ' + d.totalStrategies + ' strategies · ' + upd + '</span>' +
                '&nbsp;<span style="color:#22c55e;font-size:12px;">' + promoted + ' promoted</span>' +
                '&nbsp;<span style="color:#ef4444;font-size:12px;">' + elim + ' eliminated</span>';
        }

        var rows = d.rankings.map(function(r) {
            var rankEl = r.rank === 1 ? '<span style="color:#f59e0b;font-weight:900;">🥇 1</span>'
                       : r.rank === 2 ? '<span style="color:#aaa;font-weight:900;">🥈 2</span>'
                       : r.rank === 3 ? '<span style="color:#cd7f32;font-weight:900;">🥉 3</span>'
                       : '<span style="color:#8888aa;">' + r.rank + '</span>';
            var pnlColor  = r.totalPnl >= 0 ? '#22c55e' : '#ef4444';
            var wrColor   = r.winRate >= 55 ? '#22c55e' : r.winRate >= 45 ? '#f59e0b' : '#ef4444';
            var shColor   = r.sharpe >= 1.0 ? '#22c55e' : r.sharpe >= 0.5 ? '#f59e0b' : '#ef4444';
            var rowStyle  = r.rank_label === 'eliminated' ? 'opacity:0.55;' :
                            r.rank_label === 'promoted'   ? 'background:rgba(34,197,94,0.04);' : '';
            return '<tr style="' + rowStyle + '">' +
                '<td style="text-align:center">' + rankEl + '</td>' +
                '<td><div style="font-weight:600;">' + r.name + '</div></td>' +
                '<td style="text-align:center">' + btTierBadge(r.tier) + '</td>' +
                '<td style="min-width:100px">' + btScorebar(r.score) + '</td>' +
                '<td style="text-align:center;color:#aaa;">' + r.trades + '</td>' +
                '<td style="text-align:center;color:' + wrColor + ';font-weight:700;">' + r.winRate.toFixed(1) + '%</td>' +
                '<td style="text-align:center;color:' + pnlColor + ';font-weight:700;">' +
                    (r.totalPnl >= 0 ? '+' : '') + '$' + r.totalPnl.toFixed(2) + '</td>' +
                '<td style="text-align:center;color:' + shColor + ';">' + r.sharpe.toFixed(3) + '</td>' +
                '<td style="text-align:center">' + btRankBadge(r.rank_label) + '</td>' +
            '</tr>';
        }).join('');

        container.innerHTML = rows;
        backtestLoaded = true;

    } catch (err) {
        container.innerHTML = '<tr><td colspan="9" class="loading-cell" style="color:#ef4444;">Error loading backtest data: ' + err.message + '</td></tr>';
    }
}

document.addEventListener('DOMContentLoaded', function() {
    loadBacktest();
    // Refresh once per hour (backtest runs weekly, so hourly is more than enough)
    setInterval(loadBacktest, 3600000);
});
