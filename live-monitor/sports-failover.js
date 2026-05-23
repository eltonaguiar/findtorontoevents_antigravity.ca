/**
 * Sports Failover — Client-Side Multi-Source Data Fetcher
 *
 * Wraps all sport data fetches with automatic failover:
 *   1. Try the PHP proxy (server-side cascade)
 *   2. Try direct free APIs (client-side fallback)
 *   3. Try cached data from sessionStorage
 *
 * Also provides a health-check panel for the System Analysis tab.
 */
(function() {
    'use strict';

    var BASE = (typeof API_BASE !== 'undefined' ? API_BASE : '/live-monitor/api/');

    // ── Direct API endpoints (client-side fallback) ──────────────
    var DIRECT_APIS = {
        NBA: {
            scoreboard: [
                'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard',
                'https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json'
            ],
            standings: [
                'https://site.api.espn.com/apis/v2/sports/basketball/nba/standings'
            ]
        },
        NHL: {
            scoreboard: [
                'https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard'
            ],
            standings: [
                'https://site.api.espn.com/apis/v2/sports/hockey/nhl/standings',
                'https://api-web.nhle.com/v1/standings/now'
            ]
        },
        NFL: {
            scoreboard: [
                'https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard'
            ],
            standings: [
                'https://site.api.espn.com/apis/v2/sports/football/nfl/standings'
            ]
        },
        MLB: {
            scoreboard: [
                'https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard'
            ],
            standings: [
                'https://site.api.espn.com/apis/v2/sports/baseball/mlb/standings',
                'https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=' + new Date().getFullYear()
            ]
        }
    };

    // ── Failover fetch with timeout ──────────────────────────────
    function fetchWithTimeout(url, timeout) {
        return new Promise(function(resolve, reject) {
            var xhr = new XMLHttpRequest();
            xhr.open('GET', url, true);
            xhr.timeout = timeout || 8000;
            xhr.onload = function() {
                if (xhr.status >= 200 && xhr.status < 400) {
                    try {
                        resolve({ ok: true, data: JSON.parse(xhr.responseText), source: url });
                    } catch(e) {
                        reject({ ok: false, error: 'JSON parse error', source: url });
                    }
                } else {
                    reject({ ok: false, error: 'HTTP ' + xhr.status, source: url });
                }
            };
            xhr.onerror = function() { reject({ ok: false, error: 'Network error', source: url }); };
            xhr.ontimeout = function() { reject({ ok: false, error: 'Timeout', source: url }); };
            xhr.send();
        });
    }

    // ── Cache helpers ────────────────────────────────────────────
    var CACHE_PREFIX = 'sfo_';
    var CACHE_TTL = 300000; // 5 minutes

    function cacheKey(sport, type) { return CACHE_PREFIX + sport + '_' + type; }

    function cacheGet(sport, type) {
        try {
            var raw = sessionStorage.getItem(cacheKey(sport, type));
            if (!raw) return null;
            var entry = JSON.parse(raw);
            if (Date.now() - entry.ts > CACHE_TTL) return null;
            entry.data._fromCache = true;
            return entry.data;
        } catch(e) { return null; }
    }

    function cacheSet(sport, type, data) {
        try {
            sessionStorage.setItem(cacheKey(sport, type), JSON.stringify({ ts: Date.now(), data: data }));
        } catch(e) { /* storage full — ignore */ }
    }

    // ── Main failover fetch ─────────────────────────────────────
    /**
     * Fetch sport data with full failover chain:
     *   1. PHP proxy (server-side cascade)
     *   2. Direct API calls (client-side)
     *   3. SessionStorage cache (stale fallback)
     *
     * @param {string} sport - NBA, NHL, NFL, MLB
     * @param {string} type  - standings, scoreboard, injuries
     * @param {function} callback - function(result) where result has .ok, .data, .source, .failover_log
     */
    function failoverFetch(sport, type, callback) {
        sport = sport.toUpperCase();
        var log = [];
        var startTime = Date.now();

        // Step 1: Try PHP proxy
        var proxyUrl = BASE + 'sports_failover_proxy.php?sport=' + sport + '&type=' + type;
        fetchWithTimeout(proxyUrl, 12000)
            .then(function(result) {
                // Proxy can return 200 + JSON { ok: false, ... } (e.g. 50webs stub) — must fall through to direct APIs
                if (result.data && result.data.ok === false) {
                    return Promise.reject({ ok: false, error: (result.data.error || 'proxy ok:false'), source: proxyUrl });
                }
                log.push({ step: 'proxy', ok: true, source: result.data.source || 'proxy', ms: Date.now() - startTime });
                cacheSet(sport, type, result.data);
                callback({ ok: true, data: result.data, source: result.data.source || 'proxy', failover_log: log });
            })
            .catch(function(err) {
                log.push({ step: 'proxy', ok: false, error: err.error, ms: Date.now() - startTime });

                // Step 2: Try direct APIs
                var directUrls = (DIRECT_APIS[sport] && DIRECT_APIS[sport][type]) || [];
                tryDirectApis(directUrls, 0, sport, type, log, startTime, function(directResult) {
                    if (directResult) {
                        cacheSet(sport, type, directResult.data);
                        callback({ ok: true, data: directResult.data, source: directResult.source, failover_log: log });
                    } else {
                        // Step 3: Try cache
                        var cached = cacheGet(sport, type);
                        if (cached) {
                            log.push({ step: 'cache', ok: true, source: 'sessionStorage', ms: Date.now() - startTime });
                            callback({ ok: true, data: cached, source: 'cache (stale)', failover_log: log });
                        } else {
                            log.push({ step: 'cache', ok: false, error: 'No cache', ms: Date.now() - startTime });
                            callback({ ok: false, error: 'All sources failed', failover_log: log });
                        }
                    }
                });
            });
    }

    function tryDirectApis(urls, idx, sport, type, log, startTime, callback) {
        if (idx >= urls.length) { callback(null); return; }

        fetchWithTimeout(urls[idx], 8000)
            .then(function(result) {
                log.push({ step: 'direct_' + idx, ok: true, source: urls[idx].split('/')[2], ms: Date.now() - startTime });
                callback({ data: result.data, source: urls[idx].split('/')[2] });
            })
            .catch(function(err) {
                log.push({ step: 'direct_' + idx, ok: false, error: err.error, source: urls[idx].split('/')[2], ms: Date.now() - startTime });
                tryDirectApis(urls, idx + 1, sport, type, log, startTime, callback);
            });
    }

    // ── Health Check Panel ──────────────────────────────────────
    /**
     * Render a health check panel showing failover source status.
     * Appends to the #scraper-status-content element if present.
     */
    function renderFailoverHealthPanel() {
        var container = document.getElementById('failover-health-panel');
        if (!container) {
            // Create panel after scraper status
            var scraperEl = document.getElementById('scraper-status-content');
            if (!scraperEl) return;
            container = document.createElement('div');
            container.id = 'failover-health-panel';
            container.style.cssText = 'margin-top:1rem;padding:0.8rem;background:var(--bg-card);border:1px solid rgba(20,184,166,0.3);border-radius:12px;';
            scraperEl.parentNode.insertBefore(container, scraperEl.nextSibling);
        }

        container.innerHTML = '<div style="font-weight:700;color:#14b8a6;margin-bottom:0.5rem;font-size:0.85rem">🔄 Failover API Health Check</div><div style="font-size:0.78rem;color:#889;">Checking sources...</div>';

        fetchWithTimeout(BASE + 'sports_failover_proxy.php?action=health', 15000)
            .then(function(result) {
                var d = result.data;
                if (!d.ok) {
                    container.innerHTML += '<div style="color:#ef4444;font-size:0.78rem;">Health check failed</div>';
                    return;
                }
                var html = '<div style="display:flex;gap:0.5rem;align-items:center;margin-bottom:0.6rem;">';
                html += '<span style="font-weight:700;color:#14b8a6;font-size:0.85rem;">🔄 Failover API Health</span>';
                html += '<span class="badge ' + (d.healthy === d.total ? 'badge-green' : d.healthy > 0 ? 'badge-yellow' : 'badge-red') + '">'
                     + d.healthy + '/' + d.total + ' healthy</span>';
                html += '</div>';

                // Group by sport
                var bySport = {};
                for (var i = 0; i < d.results.length; i++) {
                    var r = d.results[i];
                    if (!bySport[r.sport]) bySport[r.sport] = [];
                    bySport[r.sport].push(r);
                }

                html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:0.6rem;">';
                for (var sp in bySport) {
                    var sources = bySport[sp];
                    var sportOk = sources.filter(function(s) { return s.ok; }).length;
                    html += '<div style="background:rgba(20,184,166,0.06);border:1px solid rgba(20,184,166,0.15);border-radius:8px;padding:0.6rem;">';
                    html += '<div style="font-weight:600;color:#14b8a6;font-size:0.82rem;margin-bottom:0.3rem;">' + sp + ' <span style="font-size:0.7rem;color:#889;">(' + sportOk + '/' + sources.length + ')</span></div>';
                    for (var j = 0; j < sources.length; j++) {
                        var s = sources[j];
                        var dot = s.ok ? '🟢' : '🔴';
                        html += '<div style="font-size:0.72rem;color:#889;padding:0.1rem 0;">' + dot + ' ' + s.source + ' <span style="color:#667;">(' + s.data_type + ') ' + s.latency_ms + 'ms</span></div>';
                    }
                    html += '</div>';
                }
                html += '</div>';
                html += '<div style="font-size:0.65rem;color:#667;margin-top:0.4rem;text-align:right;">Checked: ' + d.timestamp + ' UTC</div>';

                container.innerHTML = html;
            })
            .catch(function() {
                container.innerHTML = '<div style="font-weight:700;color:#14b8a6;margin-bottom:0.3rem;font-size:0.85rem">🔄 Failover API Health</div><div style="font-size:0.78rem;color:#ef4444;">Could not reach failover proxy — PHP endpoint may need deployment.</div>';
            });
    }

    // ── Failover-aware sport stats fetch (drop-in replacement) ──
    /**
     * Drop-in replacement for direct ESPN fetches in sports-betting.js.
     * Usage:  SportsFailover.fetchTeamStats('NBA', function(teams) { ... });
     */
    function fetchTeamStatsWithFailover(sport, callback) {
        failoverFetch(sport, 'standings', function(result) {
            if (result.ok && result.data) {
                var teams = result.data.data ? result.data.data.teams : (result.data.teams || []);
                var teamMap = {};
                for (var i = 0; i < teams.length; i++) {
                    var t = teams[i];
                    var key = t.abbreviation || t.short_name || t.name;
                    if (key) teamMap[key] = t;
                }
                callback(teamMap, result.source);
            } else {
                callback(null, 'failed');
            }
        });
    }

    // ── Hook into System Analysis tab ────────────────────────────
    var origFetchScraperStatus = window.fetchScraperStatus;
    if (typeof origFetchScraperStatus === 'function') {
        window.fetchScraperStatus = function() {
            origFetchScraperStatus();
            setTimeout(renderFailoverHealthPanel, 1500);
        };
    }

    // ── Public API ──────────────────────────────────────────────
    window.SportsFailover = {
        fetch:              failoverFetch,
        fetchTeamStats:     fetchTeamStatsWithFailover,
        renderHealthPanel:  renderFailoverHealthPanel,
        DIRECT_APIS:        DIRECT_APIS,
        VERSION:            '1.0.0',
    };

})();
