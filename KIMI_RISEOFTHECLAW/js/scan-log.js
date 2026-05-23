/**
 * Rise of the Claw — Scan Log Panel (v10.3)
 * Reads data/scan_log.json and renders:
 *   - Last-checked timestamp per asset class (category)
 *   - Last-checked + active picks per algorithm ID
 *   - Mini sparkline of scan history (signals found per run)
 */

(function() {
    'use strict';

    var CATEGORY_COLORS = {
        crypto: '#f59e0b',
        stock:  '#3b82f6',
        meme:   '#ec4899',
        penny:  '#10b981',
        forex:  '#8b5cf6',
    };

    var CATEGORY_LABELS = {
        crypto: 'Crypto',
        stock:  'Stocks',
        meme:   'Meme',
        penny:  'Penny',
        forex:  'Forex',
    };

    function timeAgo(isoStr) {
        if (!isoStr) return 'never';
        var d = new Date(isoStr);
        var diff = Math.floor((Date.now() - d.getTime()) / 1000);
        if (diff < 60)   return diff + 's ago';
        if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
        if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
        return Math.floor(diff / 86400) + 'd ago';
    }

    function fmtReturn(v) {
        var n = parseFloat(v) || 0;
        var color = n > 0 ? '#22c55e' : n < 0 ? '#ef4444' : '#8888aa';
        var sign = n >= 0 ? '+' : '';
        return '<span style="color:' + color + '">' + sign + n.toFixed(2) + '%</span>';
    }

    function renderCategoryRow(cat, stats) {
        var color = CATEGORY_COLORS[cat] || '#8888aa';
        var label = CATEGORY_LABELS[cat] || cat;
        var ago = timeAgo(stats.lastScanned);
        var algosStr = (stats.algosWithPicks || 0) + '/' + (stats.algosTotal || 0) + ' algos active';
        var activeStr = stats.activePicks > 0
            ? '<span style="color:#22c55e">' + stats.activePicks + ' open</span>'
            : '<span style="color:#555">0 open</span>';
        var closedStr = stats.closedPicks > 0
            ? '<span style="color:#8888aa">' + stats.closedPicks + ' closed</span>'
            : '<span style="color:#333">0 closed</span>';
        var retStr = fmtReturn(stats.totalReturn);

        return '<tr>' +
            '<td><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:' + color + ';margin-right:6px;"></span>' +
            '<strong style="color:#e0e0f0">' + label + '</strong></td>' +
            '<td style="color:#8888aa">' + ago + '</td>' +
            '<td>' + activeStr + ' · ' + closedStr + '</td>' +
            '<td style="color:#8888aa;font-size:11px">' + algosStr + '</td>' +
            '<td>' + retStr + '</td>' +
            '</tr>';
    }

    function renderAlgoTable(byAlgo) {
        var cats = ['crypto', 'stock', 'meme', 'penny', 'forex'];
        var html = '';

        cats.forEach(function(cat) {
            var algos = Object.values(byAlgo).filter(function(a) { return a.category === cat; });
            if (!algos.length) return;

            var color = CATEGORY_COLORS[cat] || '#8888aa';
            var label = CATEGORY_LABELS[cat] || cat;

            html += '<tr><td colspan="6" style="padding:8px 6px 3px;font-size:10px;text-transform:uppercase;' +
                'letter-spacing:1px;color:' + color + ';border-top:1px solid #1a1a2e">' + label + '</td></tr>';

            algos.sort(function(a, b) { return b.activePicks - a.activePicks || a.name.localeCompare(b.name); });

            algos.forEach(function(a) {
                var ago = timeAgo(a.lastScanned);
                var tierColor = a.tier === 'TIER_1' ? '#f59e0b' : '#6366f1';
                var tierShort = a.tier === 'TIER_1' ? 'T1' : 'SC';
                var activeStr = a.activePicks > 0
                    ? '<span style="color:#22c55e;font-weight:600">' + a.activePicks + '</span>'
                    : '<span style="color:#555">0</span>';
                var closedStr = a.closedPicks > 0
                    ? '<span style="color:#8888aa">' + a.closedPicks + '</span>'
                    : '<span style="color:#333">0</span>';
                var drought = a.droughtScans || 0;
                var droughtStr = drought > 5
                    ? '<span style="color:#ef4444">' + drought + '</span>'
                    : '<span style="color:#555">' + drought + '</span>';

                html += '<tr style="font-size:12px">' +
                    '<td><span style="color:' + tierColor + ';font-size:10px;margin-right:4px">' + tierShort + '</span>' +
                    '<span style="color:#c0c0d8">' + (a.name || a.id) + '</span></td>' +
                    '<td style="color:#666;font-size:11px">' + ago + '</td>' +
                    '<td>' + activeStr + ' open</td>' +
                    '<td>' + closedStr + ' closed</td>' +
                    '<td>' + droughtStr + ' drought</td>' +
                    '<td>' + fmtReturn(a.totalReturn) + '</td>' +
                    '</tr>';
            });
        });

        return html;
    }

    function renderSparkline(history) {
        if (!history || history.length < 2) return '';
        var recent = history.slice(-40);
        var vals = recent.map(function(h) { return h.signalsFound || 0; });
        var max = Math.max.apply(null, vals) || 1;
        var W = 300, H = 40;
        var step = W / (vals.length - 1);
        var points = vals.map(function(v, i) {
            return (i * step).toFixed(1) + ',' + (H - (v / max) * (H - 4)).toFixed(1);
        }).join(' ');

        // New picks dots
        var dots = recent.map(function(h, i) {
            if (!h.newPicks) return '';
            var x = (i * step).toFixed(1);
            var y = (H - ((h.signalsFound || 0) / max) * (H - 4) - 6).toFixed(1);
            return '<circle cx="' + x + '" cy="' + y + '" r="3" fill="#22c55e" />';
        }).join('');

        return '<svg width="' + W + '" height="' + H + '" style="margin-top:8px;display:block">' +
            '<polyline points="' + points + '" fill="none" stroke="#3b82f6" stroke-width="1.5" opacity="0.7"/>' +
            dots +
            '</svg>';
    }

    async function loadScanLog() {
        var container = document.getElementById('scanLogPanel');
        if (!container) return;

        try {
            var cacheBust = '?_=' + Date.now();
            var resp = await fetch('data/scan_log.json' + cacheBust);
            if (!resp.ok) throw new Error('HTTP ' + resp.status);
            var log = await resp.json();

            var byCategory = log.byCategory || {};
            var byAlgo     = log.byAlgo     || {};
            var history    = log.scanHistory || [];
            var lastUpdated = log.lastUpdated || '';

            // ---- Category summary ----
            var catOrder = ['crypto', 'stock', 'meme', 'penny', 'forex'];
            var catRows = catOrder.map(function(c) {
                return byCategory[c] ? renderCategoryRow(c, byCategory[c]) : '';
            }).join('');

            // ---- Totals ----
            var totalActive = Object.values(byCategory).reduce(function(s, c) { return s + (c.activePicks || 0); }, 0);
            var totalClosed = Object.values(byCategory).reduce(function(s, c) { return s + (c.closedPicks || 0); }, 0);

            // ---- History sparkline ----
            var spark = renderSparkline(history);
            var lastRun = history.length ? history[history.length - 1] : null;
            var lastRunStr = lastRun
                ? 'Last run: ' + timeAgo(lastRun.timestamp) + ' · ' + (lastRun.signalsFound || 0) + ' signals · ' + (lastRun.newPicks || 0) + ' new picks'
                : 'No runs yet';

            container.innerHTML =
                '<div style="display:flex;gap:24px;flex-wrap:wrap;align-items:flex-start">' +

                // Left: category table
                '<div style="flex:1;min-width:300px">' +
                '<div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#555;margin-bottom:8px">By Asset Class</div>' +
                '<table style="width:100%;border-collapse:collapse;font-size:12px">' +
                '<thead><tr style="color:#555;font-size:10px;border-bottom:1px solid #1a1a2e">' +
                '<th style="text-align:left;padding:3px 6px">Class</th>' +
                '<th style="text-align:left;padding:3px 6px">Last Check</th>' +
                '<th style="text-align:left;padding:3px 6px">Picks</th>' +
                '<th style="text-align:left;padding:3px 6px">Algos</th>' +
                '<th style="text-align:left;padding:3px 6px">Return</th>' +
                '</tr></thead>' +
                '<tbody>' + catRows + '</tbody>' +
                '</table>' +
                '<div style="margin-top:10px;font-size:11px;color:#555">' +
                'Total: <span style="color:#22c55e">' + totalActive + ' open</span> · ' +
                '<span style="color:#8888aa">' + totalClosed + ' closed</span> · ' +
                '<span style="color:#666">' + Object.keys(byAlgo).length + ' algos tracked</span>' +
                '</div>' +
                '</div>' +

                // Right: sparkline + last run
                '<div style="min-width:300px">' +
                '<div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#555;margin-bottom:4px">' +
                'Signal Activity (' + history.length + ' runs)</div>' +
                '<div style="font-size:10px;color:#3b82f6;margin-bottom:2px">Signals found per run</div>' +
                spark +
                '<div style="font-size:10px;color:#555;margin-top:4px">' + lastRunStr + '</div>' +
                '<div style="font-size:10px;color:#22c55e;margin-top:2px">Green dots = runs that generated new picks</div>' +
                '</div>' +

                '</div>' +

                // Algo table (collapsed by default, expand on click)
                '<div style="margin-top:16px">' +
                '<button onclick="toggleAlgoLog(this)" style="background:none;border:1px solid #2a2a3e;color:#8888aa;' +
                'padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">Show per-algo log ▾</button>' +
                '<div id="algoLogTable" style="display:none;margin-top:8px">' +
                '<table style="width:100%;border-collapse:collapse;font-size:12px">' +
                '<thead><tr style="color:#555;font-size:10px;border-bottom:1px solid #1a1a2e">' +
                '<th style="text-align:left;padding:3px 6px">Algorithm</th>' +
                '<th style="text-align:left;padding:3px 6px">Last Check</th>' +
                '<th style="text-align:left;padding:3px 6px">Open</th>' +
                '<th style="text-align:left;padding:3px 6px">Closed</th>' +
                '<th style="text-align:left;padding:3px 6px">Drought</th>' +
                '<th style="text-align:left;padding:3px 6px">Return</th>' +
                '</tr></thead>' +
                '<tbody>' + renderAlgoTable(byAlgo) + '</tbody>' +
                '</table></div></div>';

        } catch (err) {
            container.innerHTML = '<div style="color:#555;font-size:12px;padding:8px">Scan log not yet available — runs after next scanner cycle. (' + err.message + ')</div>';
        }
    }

    window.toggleAlgoLog = function(btn) {
        var tbl = document.getElementById('algoLogTable');
        if (!tbl) return;
        if (tbl.style.display === 'none') {
            tbl.style.display = 'block';
            btn.textContent = 'Hide per-algo log ▴';
        } else {
            tbl.style.display = 'none';
            btn.textContent = 'Show per-algo log ▾';
        }
    };

    // Load on page ready; auto-refresh every 5 min
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            loadScanLog();
            setInterval(loadScanLog, 5 * 60 * 1000);
        });
    } else {
        loadScanLog();
        setInterval(loadScanLog, 5 * 60 * 1000);
    }

})();
