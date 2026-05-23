/**
 * Tournament Leaderboard — Rise of the Claw v4
 * v4 institutional scoring: Sharpe 30% + WinRate 25% + MaxDD 20% + ProfitFactor 15% + Consistency 10%
 * League brackets: Champions | Premier | Challenger | Qualification | Danger Zone
 */

var tournamentLoaded = false;

var LEAGUE_CONFIG = {
    'Champions League':  { icon: '🏆', color: '#f59e0b', bg: 'rgba(245,158,11,0.08)' },
    'Premier League':    { icon: '⭐', color: '#22c55e', bg: 'rgba(34,197,94,0.06)' },
    'Challenger League': { icon: '⚔️', color: '#3b82f6', bg: 'rgba(59,130,246,0.05)' },
    'Qualification':     { icon: '🌱', color: '#8888aa', bg: '' },
    'Danger Zone':       { icon: '⚠️', color: '#ef4444', bg: 'rgba(239,68,68,0.04)' },
};

var STATUS_CONFIG = {
    'CHAMPION':  { icon: '🏆', color: '#f59e0b' },
    'RISING':    { icon: '📈', color: '#22c55e' },
    'SCANNING':  { icon: '🔍', color: '#3b82f6' },
    'QUALIFYING':{ icon: '🌱', color: '#8888aa' },
    'WARNING':   { icon: '⚠️', color: '#f59e0b' },
    'PROBATION': { icon: '🔴', color: '#ef4444' },
};

function tournamentBadge(status) {
    var cfg = STATUS_CONFIG[status] || { icon: '📊', color: '#8888aa' };
    return '<span style="color:' + cfg.color + ';font-weight:700;">' + cfg.icon + ' ' + status + '</span>';
}

function leagueBadge(league) {
    var cfg = LEAGUE_CONFIG[league] || { icon: '🌱', color: '#8888aa' };
    return '<span style="color:' + cfg.color + ';font-size:12px;font-weight:600;">' + cfg.icon + ' ' + league + '</span>';
}

function tierBadge(tier) {
    if (tier === 'TIER_1')
        return '<span style="background:rgba(59,130,246,0.2);color:#60a5fa;padding:2px 7px;border-radius:10px;font-size:11px;font-weight:600;">TIER 1</span>';
    return '<span style="background:rgba(136,136,170,0.2);color:#8888aa;padding:2px 7px;border-radius:10px;font-size:11px;font-weight:600;">SCOUT</span>';
}

function scorebar(score) {
    var pct = Math.min(Math.max(score, 0), 100);
    var color = score >= 75 ? '#f59e0b' : score >= 55 ? '#22c55e' : score >= 40 ? '#3b82f6' : score >= 25 ? '#8888aa' : '#ef4444';
    return '<div style="display:flex;align-items:center;gap:6px;">' +
        '<div style="flex:1;background:rgba(136,136,170,0.15);border-radius:4px;height:6px;overflow:hidden;">' +
            '<div style="width:' + pct + '%;height:100%;background:' + color + ';border-radius:4px;transition:width 0.4s;"></div>' +
        '</div>' +
        '<span style="color:' + color + ';font-weight:700;min-width:32px;text-align:right;">' + score + '</span>' +
    '</div>';
}

function fmt(val, decimals, prefix, suffix) {
    if (val === undefined || val === null) return '<span style="color:#8888aa;">—</span>';
    var n = parseFloat(val).toFixed(decimals || 2);
    return (prefix || '') + n + (suffix || '');
}

function leagueSummaryBar(leagues) {
    if (!leagues) return '';
    var parts = [];
    var order = ['Champions League','Premier League','Challenger League','Qualification','Danger Zone'];
    order.forEach(function(lg) {
        var cnt = leagues[lg] || 0;
        if (cnt > 0) {
            var cfg = LEAGUE_CONFIG[lg] || { icon: '', color: '#8888aa' };
            parts.push('<span style="color:' + cfg.color + ';font-size:12px;margin:0 6px;">' +
                cfg.icon + ' ' + lg + ': <strong>' + cnt + '</strong></span>');
        }
    });
    return parts.join('<span style="color:#333;margin:0 2px;">·</span>');
}

async function loadTournament() {
    var container = document.getElementById('tournamentBody');
    var headerEl  = document.getElementById('tournamentPhase');
    var leagueEl  = document.getElementById('leagueSummary');
    if (!container) return;

    try {
        var cacheBust = '?_=' + Date.now();
        var basePath = (typeof getBasePath === 'function') ? getBasePath() : '/riseoftheclaw/';
        var resp = await fetch(basePath + 'data/tournament.json' + cacheBust);

        if (!resp.ok) {
            container.innerHTML = '<tr><td colspan="9" class="loading-cell" style="color:#f59e0b;">⚠ tournament.json not yet available — will appear after next scanner run</td></tr>';
            return;
        }

        var t = await resp.json();
        if (!t || !t.rankings || t.rankings.length === 0) {
            container.innerHTML = '<tr><td colspan="9" class="loading-cell">No tournament data yet.</td></tr>';
            return;
        }

        if (headerEl) {
            var regimeStr = '';
            if (t.marketRegime) {
                var sr = (t.marketRegime.stock || 'neutral').toUpperCase();
                var cr = (t.marketRegime.crypto || 'neutral').toUpperCase();
                var srColor = sr === 'BULL' ? '#22c55e' : sr === 'BEAR' ? '#ef4444' : '#f59e0b';
                var crColor = cr === 'BULL' ? '#22c55e' : cr === 'BEAR' ? '#ef4444' : '#f59e0b';
                var vixVal = t.marketRegime.vix;
                var vixStr = '';
                if (vixVal !== undefined && vixVal !== null) {
                    var vixColor = vixVal > 35 ? '#ef4444' : vixVal > 25 ? '#f97316' : vixVal < 15 ? '#f59e0b' : '#22c55e';
                    vixStr = ' · VIX:<span style="color:' + vixColor + ';font-weight:700;"> ' + vixVal.toFixed(1) + '</span>';
                }
                regimeStr = ' &nbsp;|&nbsp;<span style="font-size:11px;color:#8888aa;"> Stocks:<span style="color:' + srColor + ';font-weight:700;"> ' + sr + '</span> · Crypto:<span style="color:' + crColor + ';font-weight:700;"> ' + cr + '</span>' + vixStr + '</span>';
            }
            headerEl.innerHTML =
                '<span style="background:rgba(245,158,11,0.15);color:#f59e0b;border:1px solid rgba(245,158,11,0.3);' +
                'padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600;">' +
                t.phase + ' · Day ' + (t.daysInCompetition || 1) + ' · ' + (t.totalAlgorithms || 0) + ' algos</span>' + regimeStr;
        }

        if (leagueEl && t.leagues) {
            var leagueHtml = leagueSummaryBar(t.leagues);
            if (t.signalConvergence && t.signalConvergence.length > 0) {
                leagueHtml += '&nbsp;&nbsp;<span style="background:rgba(245,158,11,0.12);color:#f59e0b;padding:2px 8px;border-radius:8px;font-size:11px;font-weight:600;">🔥 Convergence: ' +
                    t.signalConvergence.slice(0,3).map(function(c){return c.symbol+'×'+c.strategies;}).join(', ') + '</span>';
            }
            // Crypto Fear & Greed Index
            if (t.fearGreedIndex && t.fearGreedIndex.value !== undefined) {
                var fng = t.fearGreedIndex;
                var fngVal = fng.value;
                var fngColor = fngVal <= 24 ? '#ef4444' : fngVal <= 49 ? '#f97316' : fngVal >= 75 ? '#22c55e' : '#f59e0b';
                var fngIcon = fngVal <= 24 ? '😱' : fngVal <= 49 ? '😰' : fngVal >= 75 ? '🤑' : '😐';
                leagueHtml += '&nbsp;&nbsp;<span style="font-size:11px;color:' + fngColor + ';">' +
                    fngIcon + ' Crypto F&G: <strong>' + fngVal + '</strong>/100 (' + fng.classification + ')</span>';
            }
            // VIX Term Structure (v6.2)
            if (t.vixTermStructure && t.vixTermStructure.term_signal) {
                var vts = t.vixTermStructure;
                var vtsColors = { contango: '#22c55e', flat: '#f59e0b', backwardation: '#ef4444' };
                var vtsIcons  = { contango: '📈', flat: '➡️', backwardation: '🔴' };
                var vtsColor = vtsColors[vts.term_signal] || '#8888aa';
                var vtsIcon  = vtsIcons[vts.term_signal]  || '❓';
                leagueHtml += '&nbsp;&nbsp;<span style="font-size:11px;color:' + vtsColor + ';">' +
                    vtsIcon + ' VIX Term: <strong>' + vts.term_signal.toUpperCase() + '</strong>' +
                    ' (' + (vts.vix_spot || '—') + '/' + (vts.vix3m || '—') + ')' +
                    '</span>';
            }
            // Portfolio heat map
            if (t.portfolioHeat) {
                var heatParts = Object.entries(t.portfolioHeat).filter(function(e){ return e[1].picks > 0; }).map(function(e) {
                    var isHot = t.heatWarnings && t.heatWarnings.indexOf(e[0]) >= 0;
                    return '<span style="color:' + (isHot ? '#ef4444' : '#8888aa') + ';font-size:11px;">' +
                        (isHot ? '🔴 ' : '') + e[0] + ': ' + e[1].picks + ' (' + e[1].pct + '%)</span>';
                });
                if (heatParts.length > 0) {
                    leagueHtml += '&nbsp;&nbsp;|&nbsp;&nbsp;' + heatParts.join(' · ');
                }
            }
            leagueEl.innerHTML = leagueHtml;
        }

        var rows = t.rankings.map(function(r) {
            var league = r.league || 'Qualification';
            var lcfg   = LEAGUE_CONFIG[league] || { bg: '' };
            var wrColor = r.winRate >= 55 ? '#22c55e' : r.winRate >= 40 ? '#f59e0b' : '#ef4444';
            var shColor = (r.sharpe || 0) >= 1.0 ? '#22c55e' : (r.sharpe || 0) >= 0.3 ? '#f59e0b' : '#8888aa';
            var pfColor = (r.profitFactor || 1) >= 1.5 ? '#22c55e' : (r.profitFactor || 1) >= 1.0 ? '#f59e0b' : '#ef4444';
            var rankEl  = r.rank === 1 ? '<span style="color:#f59e0b;font-weight:900;">🥇 1</span>'
                        : r.rank === 2 ? '<span style="color:#aaa;font-weight:900;">🥈 2</span>'
                        : r.rank === 3 ? '<span style="color:#cd7f32;font-weight:900;">🥉 3</span>'
                        : '<span style="color:#8888aa;">' + r.rank + '</span>';

            // Regime bonus indicator
            var rb = r.regimeBonus || 0;
            var rbEl = rb !== 0
                ? '<div style="font-size:10px;margin-top:2px;color:' + (rb > 0 ? '#22c55e' : '#ef4444') + ';">' +
                  (rb > 0 ? '▲ +' : '▼ ') + rb.toFixed(1) + ' regime</div>'
                : '';

            // Kelly fraction indicator
            var kf = r.kellyFraction || 0;
            var kfEl = kf > 0
                ? '<div style="color:#8b5cf6;font-size:11px;margin-top:2px;">K¼: ' + (kf * 100).toFixed(1) + '%</div>'
                : '';

            // Walk-forward decay / consistency indicator (v5.5)
            var wfDecay = r.wfDecayPenalty || 0;
            var wfBonus = r.wfBonus || 0;
            var wfEl = '';
            if (wfDecay <= -5) {
                wfEl = '<div style="font-size:10px;margin-top:2px;color:#ef4444;">⚠ WF decay: ' + wfDecay.toFixed(1) + '</div>';
            } else if (wfDecay < -2) {
                wfEl = '<div style="font-size:10px;margin-top:2px;color:#f97316;">↓ WF ' + wfDecay.toFixed(1) + '</div>';
            } else if (wfBonus >= 5) {
                wfEl = '<div style="font-size:10px;margin-top:2px;color:#22c55e;">✓ WF consistent</div>';
            }

            return '<tr style="' + (lcfg.bg ? 'background:' + lcfg.bg + ';' : '') + '">' +
                '<td style="text-align:center">' + rankEl + '</td>' +
                '<td>' +
                    '<div style="font-weight:600;">' + r.name + '</div>' +
                    '<div style="margin-top:3px;">' + tierBadge(r.tier) + '</div>' +
                '</td>' +
                '<td>' + tournamentBadge(r.status) + '</td>' +
                '<td style="min-width:120px">' + scorebar(r.score) + rbEl + wfEl + '</td>' +
                '<td style="color:' + wrColor + ';text-align:center;">' +
                    r.winRate + '<small style="color:#8888aa;font-size:11px;">% (' + r.wins + 'W/' + r.losses + 'L)</small>' +
                '</td>' +
                '<td style="color:' + shColor + ';text-align:center;font-weight:700;">' +
                    (r.sharpe !== undefined ? r.sharpe.toFixed(3) : '—') +
                    (r.sortino !== undefined ? '<div style="font-size:10px;color:#8b5cf6;margin-top:1px;">S: ' + r.sortino.toFixed(2) + '</div>' : '') +
                '</td>' +
                '<td style="color:' + pfColor + ';text-align:center;">' +
                    (r.profitFactor !== undefined ? r.profitFactor.toFixed(2) + 'x' : '—') +
                '</td>' +
                '<td style="text-align:center;">' + leagueBadge(league) + '</td>' +
                '<td style="text-align:center;color:#8888aa;font-size:12px;">' + (r.activePicks || 0) + ' active' + kfEl + '</td>' +
            '</tr>';
        }).join('');

        container.innerHTML = rows;
        tournamentLoaded = true;

    } catch (err) {
        container.innerHTML = '<tr><td colspan="9" class="loading-cell" style="color:#ef4444;">Error loading tournament.json: ' + err.message + '</td></tr>';
    }
}

document.addEventListener('DOMContentLoaded', function() {
    loadTournament();
    setInterval(loadTournament, 300000); // refresh every 5 minutes
});
