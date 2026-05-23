/**
 * Jobs Log - shows recent scanner runs so you can tell if the system is alive or stale
 * Reads from data/scan_runs.json (written by live_scanner.py after every run)
 */

var jobsLogLoaded = false;

function timeAgo(isoStr) {
    if (!isoStr) return '—';
    var d = new Date(isoStr);
    var now = new Date();
    var diffMs = now - d;
    var diffSec = Math.floor(diffMs / 1000);
    if (diffSec < 60) return diffSec + 's ago';
    var diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return diffMin + 'm ago';
    var diffH = Math.floor(diffMin / 60);
    if (diffH < 24) return diffH + 'h ago';
    return Math.floor(diffH / 24) + 'd ago';
}

function fmtTimestamp(isoStr) {
    if (!isoStr) return '—';
    try {
        return new Date(isoStr).toLocaleString('en-CA', {
            month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit', second: '2-digit',
            hour12: false, timeZone: 'UTC'
        }) + ' UTC';
    } catch (e) { return isoStr; }
}

async function loadJobsLog() {
    var container = document.getElementById('jobsLogBody');
    var headerEl = document.getElementById('jobsLogLastRun');
    if (!container) return;

    try {
        var cacheBust = '?_=' + Date.now();
        var basePath = (typeof getBasePath === 'function') ? getBasePath() : '/riseoftheclaw/';
        var resp = await fetch(basePath + 'data/scan_runs.json' + cacheBust);

        if (!resp.ok) {
            container.innerHTML = '<tr><td colspan="6" class="loading-cell" style="color:#f59e0b;">⚠ scan_runs.json not found yet — will appear after next scanner run</td></tr>';
            if (headerEl) headerEl.textContent = 'No data yet';
            return;
        }

        var runs = await resp.json();
        if (!Array.isArray(runs) || runs.length === 0) {
            container.innerHTML = '<tr><td colspan="6" class="loading-cell">No scan runs recorded yet.</td></tr>';
            if (headerEl) headerEl.textContent = 'No runs yet';
            return;
        }

        // Newest first
        var sorted = runs.slice().reverse();
        var latest = sorted[0];

        // Update header pill
        if (headerEl) {
            var ago = timeAgo(latest.timestamp);
            var staleMins = Math.floor((new Date() - new Date(latest.timestamp)) / 60000);
            var staleClass = staleMins <= 20 ? 'jl-fresh' : staleMins <= 60 ? 'jl-warn' : 'jl-stale';
            headerEl.innerHTML = '<span class="jl-pill ' + staleClass + '">Last scan: ' + ago + '</span>';
        }

        var rows = sorted.slice(0, 30).map(function(run) {
            var statusIcon = run.status === 'FAILED' ? '🔴' : run.new_picks > 0 ? '🟢' : run.signals_found > 0 ? '🟡' : '🔵';
            var statusLabel = run.status === 'FAILED' ? '<span style="color:#ef4444">FAILED</span>'
                : run.new_picks > 0 ? '<span style="color:#22c55e">NEW PICKS (' + run.new_picks + ')</span>'
                : run.signals_found > 0 ? '<span style="color:#f59e0b">SIGNAL (held)</span>'
                : '<span style="color:#8888aa">no signal</span>';

            var signalTxt = '';
            if (run.signal_details && run.signal_details.length > 0) {
                signalTxt = run.signal_details.map(function(s) {
                    return (s.new ? '🆕 ' : '') + s.symbol + ' via ' + (s.algorithmName || s.algorithm);
                }).join('; ');
            }

            return '<tr>' +
                '<td>' + statusIcon + '</td>' +
                '<td><span title="' + run.timestamp + '">' + fmtTimestamp(run.timestamp) + '</span><br><small style="color:#8888aa">' + timeAgo(run.timestamp) + '</small></td>' +
                '<td>' + statusLabel + '</td>' +
                '<td style="text-align:center">' + (run.signals_found || 0) + '</td>' +
                '<td style="text-align:center">' + (run.total_active_picks || 0) + '</td>' +
                '<td style="color:#aaa;font-size:12px">' + (signalTxt || (run.status === 'FAILED' ? 'fetch failed' : '—')) + '</td>' +
            '</tr>';
        }).join('');

        container.innerHTML = rows;
        jobsLogLoaded = true;

    } catch (err) {
        container.innerHTML = '<tr><td colspan="6" class="loading-cell" style="color:#ef4444;">Error loading scan_runs.json: ' + err.message + '</td></tr>';
        if (headerEl) headerEl.textContent = 'Load error';
    }
}

document.addEventListener('DOMContentLoaded', function() {
    loadJobsLog();
    // Refresh log every 2 minutes
    setInterval(loadJobsLog, 120000);
});
