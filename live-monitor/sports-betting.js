/**
 * Sports Betting — Multi-Sport Intelligence Module
 * Fetches real team stats from all sport APIs and enriches pick cards.
 * Win streak tracking is handled by the main page via sports_picks.php?action=performance.
 *
 * Intelligence sources:
 *   - NBA: nba_stats.php (ESPN, BallDontLie, NBA.com CDN)
 *   - NHL: nhl_stats.php (ESPN NHL Standings)
 *   - NFL: nfl_stats.php (ESPN NFL Standings)
 *   - MLB: mlb_stats.php (ESPN MLB Standings)
 *   - Schedule: schedule_intel.php (ESPN Scoreboard — B2B, rest, road trips)
 *   - Injuries: injury_intel.php (ESPN team injuries)
 */
(function() {
    var BASE = (typeof API_BASE !== 'undefined' ? API_BASE : '/live-monitor/api/');

    // ── Sport config ──
    var SPORT_CONFIG = {
        'NBA': {
            api: BASE + 'nba_stats.php',
            schedule_key: 'basketball_nba',
            color: '#6366f1',
            label: 'NBA Intelligence',
            record: function(t) { return t.wins + '-' + t.losses; },
            extra: function(t, role) {
                var h = '';
                if (role === 'home' && t.home_record) h += ' | Home: ' + t.home_record;
                if (role === 'away' && t.away_record) h += ' | Away: ' + t.away_record;
                if (t.streak) h += ' | Streak: <span style="color:' + (String(t.streak).indexOf('W') === 0 ? '#22c55e' : '#ef4444') + '">' + t.streak + '</span>';
                if (t.last10) h += ' | L10: ' + t.last10;
                return h;
            },
            summary: function(ht, at) {
                if (!ht || !at || !ht.ppg || !at.ppg) return '';
                var total = parseFloat(ht.ppg) + parseFloat(at.ppg);
                var s = 'Combined PPG: <strong style="color:#eab308">' + total.toFixed(1) + '</strong>';
                if (ht.opp_ppg && at.opp_ppg) s += ' | Def avg: ' + ((parseFloat(ht.opp_ppg) + parseFloat(at.opp_ppg)) / 2).toFixed(1);
                return s;
            }
        },
        'NHL': {
            api: BASE + 'nhl_stats.php',
            schedule_key: 'icehockey_nhl',
            color: '#3b82f6',
            label: 'NHL Intelligence',
            record: function(t) { return t.wins + '-' + t.losses + '-' + (t.otl || 0) + ' (' + t.points + ' pts)'; },
            extra: function(t, role) {
                var h = '';
                if (role === 'home' && t.home_record) h += ' | Home: ' + t.home_record;
                if (role === 'away' && t.away_record) h += ' | Away: ' + t.away_record;
                if (t.streak) h += ' | Streak: <span style="color:' + (String(t.streak).indexOf('W') === 0 ? '#22c55e' : '#ef4444') + '">' + t.streak + '</span>';
                if (t.pp_pct) h += ' | PP%: ' + t.pp_pct;
                if (t.pk_pct) h += ' | PK%: ' + t.pk_pct;
                return h;
            },
            summary: function(ht, at) {
                if (!ht || !at) return '';
                var s = '';
                if (ht.goals_for && at.goals_for) s += 'GF: ' + ht.goals_for + ' vs ' + at.goals_for;
                if (ht.goals_against && at.goals_against) s += ' | GA: ' + ht.goals_against + ' vs ' + at.goals_against;
                return s;
            }
        },
        'NFL': {
            api: BASE + 'nfl_stats.php',
            schedule_key: 'americanfootball_nfl',
            color: '#10b981',
            label: 'NFL Intelligence',
            record: function(t) { return t.wins + '-' + t.losses + (t.ties > 0 ? '-' + t.ties : ''); },
            extra: function(t, role) {
                var h = '';
                if (role === 'home' && t.home_record) h += ' | Home: ' + t.home_record;
                if (role === 'away' && t.away_record) h += ' | Away: ' + t.away_record;
                if (t.turnover_diff !== '' && t.turnover_diff !== undefined) h += ' | TO Margin: <span style="color:' + (parseInt(t.turnover_diff) >= 0 ? '#22c55e' : '#ef4444') + '">' + (parseInt(t.turnover_diff) >= 0 ? '+' : '') + t.turnover_diff + '</span>';
                if (t.streak) h += ' | Streak: <span style="color:' + (String(t.streak).indexOf('W') === 0 ? '#22c55e' : '#ef4444') + '">' + t.streak + '</span>';
                return h;
            },
            summary: function(ht, at) {
                if (!ht || !at) return '';
                var s = '';
                if (ht.ppg && at.ppg) s += 'PPG: ' + ht.ppg + ' vs ' + at.ppg;
                if (ht.opp_ppg && at.opp_ppg) s += ' | Opp PPG: ' + ht.opp_ppg + ' vs ' + at.opp_ppg;
                return s;
            }
        },
        'MLB': {
            api: BASE + 'mlb_stats.php',
            schedule_key: 'baseball_mlb',
            color: '#f59e0b',
            label: 'MLB Intelligence',
            record: function(t) { return t.wins + '-' + t.losses; },
            extra: function(t, role) {
                var h = '';
                if (role === 'home' && t.home_record) h += ' | Home: ' + t.home_record;
                if (role === 'away' && t.away_record) h += ' | Away: ' + t.away_record;
                if (t.era) h += ' | ERA: <strong style="color:#e0e0f0">' + t.era + '</strong>';
                if (t.streak) h += ' | Streak: <span style="color:' + (String(t.streak).indexOf('W') === 0 ? '#22c55e' : '#ef4444') + '">' + t.streak + '</span>';
                if (t.last10) h += ' | L10: ' + t.last10;
                return h;
            },
            summary: function(ht, at) {
                if (!ht || !at) return '';
                var s = '';
                if (ht.rpg && at.rpg) s += 'RPG: ' + ht.rpg + ' vs ' + at.rpg;
                if (ht.run_diff && at.run_diff) s += ' | Run Diff: ' + ht.run_diff + ' vs ' + at.run_diff;
                return s;
            }
        }
    };

    // ── Map sport text from pick cards to our keys ──
    function detectSport(sportText) {
        var t = sportText.toUpperCase();
        if (t.indexOf('NBA') !== -1 || t.indexOf('BASKETBALL_NBA') !== -1) return 'NBA';
        if (t.indexOf('NHL') !== -1 || t.indexOf('ICEHOCKEY_NHL') !== -1) return 'NHL';
        if (t.indexOf('NFL') !== -1 || t.indexOf('AMERICANFOOTBALL_NFL') !== -1) return 'NFL';
        if (t.indexOf('MLB') !== -1 || t.indexOf('BASEBALL_MLB') !== -1) return 'MLB';
        return null;
    }

    // ── Fuzzy team name matching (reusable) ──
    function findTeam(teams, name) {
        name = name.toLowerCase().trim();
        for (var k in teams) {
            if (!teams.hasOwnProperty(k)) continue;
            var t = teams[k];
            var tName = (t.name || '').toLowerCase();
            var tShort = (t.short_name || '').toLowerCase();
            var tAbbr = (t.abbreviation || '').toLowerCase();
            if (tName === name || tShort === name || tAbbr === name) return t;
            if (tName.indexOf(name) !== -1 || name.indexOf(tName) !== -1) return t;
            if (tShort && (tShort.indexOf(name) !== -1 || name.indexOf(tShort) !== -1)) return t;
            var nameParts = name.split(' ');
            var lastWord = nameParts[nameParts.length - 1];
            if (lastWord.length > 3 && tName.indexOf(lastWord) !== -1) return t;
        }
        return null;
    }

    // ── Store loaded data globally ──
    window._sportTeamStats = window._sportTeamStats || {};
    window._sportScheduleIntel = window._sportScheduleIntel || {};
    window._sportInjuryIntel = window._sportInjuryIntel || {};

    // ── Fetch team stats for a sport ──
    function fetchSportStats(sportKey) {
        var cfg = SPORT_CONFIG[sportKey];
        if (!cfg) return;
        var xhr = new XMLHttpRequest();
        xhr.open('GET', cfg.api + '?action=team_stats', true);
        xhr.timeout = 10000;
        xhr.onload = function() {
            if (xhr.status !== 200) return;
            try {
                var d = JSON.parse(xhr.responseText);
                if (!d.ok || !d.teams) return;
                window._sportTeamStats[sportKey] = d.teams;
                enrichPickCards();
                if (sportKey === 'NBA') renderNbaInsightsPanel(d);
                if (sportKey === 'NHL') renderNhlInsightsPanel(d);
            } catch(e) {}
        };
        xhr.onerror = function() {};
        xhr.send();
    }

    // ── Fetch schedule intel for a sport ──
    function fetchScheduleIntel(sportKey) {
        var cfg = SPORT_CONFIG[sportKey];
        if (!cfg || !cfg.schedule_key) return;
        var xhr = new XMLHttpRequest();
        xhr.open('GET', BASE + 'schedule_intel.php?action=schedule&sport=' + cfg.schedule_key, true);
        xhr.timeout = 10000;
        xhr.onload = function() {
            if (xhr.status !== 200) return;
            try {
                var d = JSON.parse(xhr.responseText);
                if (!d.ok || !d.teams) return;
                window._sportScheduleIntel[sportKey] = d.teams;
                enrichPickCards();
            } catch(e) {}
        };
        xhr.onerror = function() {};
        xhr.send();
    }

    // ── Fetch injury intel for a sport ──
    function fetchInjuryIntel(sportKey) {
        var cfg = SPORT_CONFIG[sportKey];
        if (!cfg || !cfg.schedule_key) return;
        var xhr = new XMLHttpRequest();
        xhr.open('GET', BASE + 'injury_intel.php?action=injuries&sport=' + cfg.schedule_key, true);
        xhr.timeout = 10000;
        xhr.onload = function() {
            if (xhr.status !== 200) return;
            try {
                var d = JSON.parse(xhr.responseText);
                if (!d.ok || !d.teams) return;
                window._sportInjuryIntel[sportKey] = d.teams;
                enrichPickCards();
            } catch(e) {}
        };
        xhr.onerror = function() {};
        xhr.send();
    }

    // ── Enrich all pick cards with situation intel badges ──
    function enrichPickCards() {
        var cards = document.querySelectorAll('.pick-card-enhanced, .pick-card');
        for (var i = 0; i < cards.length; i++) {
            var card = cards[i];
            var sportEl = card.querySelector('.pick-sport');
            if (!sportEl) continue;
            var sportText = (sportEl.textContent || sportEl.innerText || '');
            var sportKey = detectSport(sportText);
            if (!sportKey) continue;

            var cfg = SPORT_CONFIG[sportKey];
            var teams = window._sportTeamStats[sportKey];
            if (!teams) continue;

            var teamsEl = card.querySelector('.pick-teams');
            if (!teamsEl) continue;
            var matchup = teamsEl.textContent || teamsEl.innerText || '';
            var parts = matchup.split('@');
            if (parts.length < 2) parts = matchup.split('vs');
            if (parts.length < 2) continue;

            var awayName = parts[0].trim();
            var homeName = parts[1].trim();
            var homeStats = findTeam(teams, homeName);
            var awayStats = findTeam(teams, awayName);

            if (!homeStats && !awayStats) continue;

            // Remove old badge
            var old = card.querySelector('.sport-intel-badge');
            if (old) old.parentNode.removeChild(old);

            var badge = document.createElement('div');
            badge.className = 'sport-intel-badge';
            badge.style.cssText = 'margin-top:0.5rem;padding:0.5rem;background:rgba(' + hexToRgb(cfg.color) + ',0.08);border:1px solid rgba(' + hexToRgb(cfg.color) + ',0.3);border-radius:8px;font-size:0.78rem;color:#b0b0d0;';

            var html = '<div style="font-weight:700;color:' + cfg.color + ';margin-bottom:0.3rem;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.5px">' + cfg.label + '</div>';

            if (homeStats) {
                html += '<div>' + homeStats.name + ' (HOME): <strong style="color:#e0e0f0">' + cfg.record(homeStats) + '</strong>';
                html += cfg.extra(homeStats, 'home') + '</div>';
            }
            if (awayStats) {
                html += '<div>' + awayStats.name + ' (AWAY): <strong style="color:#e0e0f0">' + cfg.record(awayStats) + '</strong>';
                html += cfg.extra(awayStats, 'away') + '</div>';
            }

            // Summary line
            var summaryHtml = cfg.summary(homeStats, awayStats);
            if (summaryHtml) {
                html += '<div style="margin-top:0.2rem;color:#8888aa">' + summaryHtml + '</div>';
            }

            // ── Schedule/fatigue badges ──
            var schedData = window._sportScheduleIntel[sportKey];
            if (schedData) {
                var homeSched = findTeam(schedData, homeName);
                var awaySched = findTeam(schedData, awayName);
                var schedBadges = [];

                if (homeSched && homeSched.is_back_to_back) schedBadges.push('<span style="background:#ef4444;color:#fff;padding:1px 6px;border-radius:4px;font-size:0.68rem;font-weight:700">HOME B2B</span>');
                if (awaySched && awaySched.is_back_to_back) schedBadges.push('<span style="background:#ef4444;color:#fff;padding:1px 6px;border-radius:4px;font-size:0.68rem;font-weight:700">AWAY B2B</span>');
                if (homeSched && awaySched) {
                    var restDiff = (parseInt(homeSched.rest_days) || 0) - (parseInt(awaySched.rest_days) || 0);
                    if (Math.abs(restDiff) >= 2) {
                        var rested = restDiff > 0 ? 'HOME' : 'AWAY';
                        schedBadges.push('<span style="background:#3b82f6;color:#fff;padding:1px 6px;border-radius:4px;font-size:0.68rem;font-weight:700">' + rested + ' +' + Math.abs(restDiff) + 'D REST</span>');
                    }
                }
                if (awaySched && awaySched.is_road_trip) schedBadges.push('<span style="background:#f59e0b;color:#000;padding:1px 6px;border-radius:4px;font-size:0.68rem;font-weight:700">AWAY ROAD TRIP</span>');

                if (schedBadges.length > 0) {
                    html += '<div style="margin-top:0.3rem;display:flex;gap:0.3rem;flex-wrap:wrap">' + schedBadges.join('') + '</div>';
                }
            }

            // ── Injury badges ──
            var injData = window._sportInjuryIntel[sportKey];
            if (injData) {
                var homeInj = findTeam(injData, homeName);
                var awayInj = findTeam(injData, awayName);
                var injBadges = [];

                if (homeInj && homeInj.out >= 2) injBadges.push('<span style="background:#dc2626;color:#fff;padding:1px 6px;border-radius:4px;font-size:0.68rem">HOME: ' + homeInj.out + ' OUT</span>');
                if (awayInj && awayInj.out >= 2) injBadges.push('<span style="background:#dc2626;color:#fff;padding:1px 6px;border-radius:4px;font-size:0.68rem">AWAY: ' + awayInj.out + ' OUT</span>');

                if (injBadges.length > 0) {
                    html += '<div style="margin-top:0.2rem;display:flex;gap:0.3rem;flex-wrap:wrap">' + injBadges.join('') + '</div>';
                }
            }

            badge.innerHTML = html;
            card.appendChild(badge);
        }
    }

    // ── Hex color to RGB ──
    function hexToRgb(hex) {
        hex = hex.replace('#', '');
        var r = parseInt(hex.substring(0, 2), 16);
        var g = parseInt(hex.substring(2, 4), 16);
        var b = parseInt(hex.substring(4, 6), 16);
        return r + ',' + g + ',' + b;
    }

    // ── Render NBA insights panel in performance tab ──
    function renderNbaInsightsPanel(data) {
        var perfTables = document.getElementById('perf-tables');
        if (!perfTables || !data.teams) return;

        var existingPanel = document.getElementById('nba-intel-panel');
        if (existingPanel) existingPanel.parentNode.removeChild(existingPanel);

        var teamArr = [];
        for (var k in data.teams) { if (data.teams.hasOwnProperty(k)) teamArr.push(data.teams[k]); }
        if (teamArr.length === 0) return;

        teamArr.sort(function(a, b) {
            return (b.wins / Math.max(1, b.wins + b.losses)) - (a.wins / Math.max(1, a.wins + a.losses));
        });

        var panel = document.createElement('div');
        panel.id = 'nba-intel-panel';
        var html = '<h3 class="section-title" style="margin-top:1.5rem">NBA Intelligence</h3>';
        html += '<p class="text-dim" style="font-size:0.85rem;margin-bottom:0.5rem">Live team stats powering our NBA predictions. Updated via ESPN + backup scrapers.</p>';
        html += '<div style="max-height:300px;overflow-y:auto"><table><tr><th>Team</th><th>W-L</th><th>Win%</th><th>Home</th><th>Away</th><th>Streak</th><th>L10</th><th>PPG</th><th>Opp PPG</th></tr>';
        for (var i = 0; i < Math.min(teamArr.length, 30); i++) {
            var t = teamArr[i];
            var winPct = ((t.wins / Math.max(1, t.wins + t.losses)) * 100).toFixed(1);
            var sColor = (t.streak || '').indexOf('W') === 0 ? 'var(--green)' : 'var(--red)';
            html += '<tr><td><strong>' + (t.short_name || t.name || '') + '</strong></td><td>' + t.wins + '-' + t.losses + '</td><td>' + winPct + '%</td><td>' + (t.home_record || '--') + '</td><td>' + (t.away_record || '--') + '</td><td style="color:' + sColor + '">' + (t.streak || '--') + '</td><td>' + (t.last10 || '--') + '</td><td>' + (t.ppg || '--') + '</td><td>' + (t.opp_ppg || '--') + '</td></tr>';
        }
        html += '</table></div>';
        if (data.updated_at) html += '<div style="font-size:0.72rem;color:var(--text-dim);margin-top:0.5rem;text-align:right">Updated: ' + data.updated_at + ' | Sources: ESPN, BallDontLie, NBA.com</div>';
        panel.innerHTML = html;
        perfTables.appendChild(panel);
    }

    // ── Render NHL insights panel in performance tab ──
    function renderNhlInsightsPanel(data) {
        var perfTables = document.getElementById('perf-tables');
        if (!perfTables || !data.teams) return;

        var existingPanel = document.getElementById('nhl-intel-panel');
        if (existingPanel) existingPanel.parentNode.removeChild(existingPanel);

        var teamArr = [];
        for (var k in data.teams) { if (data.teams.hasOwnProperty(k)) teamArr.push(data.teams[k]); }
        if (teamArr.length === 0) return;

        teamArr.sort(function(a, b) { return (b.pts_pct || 0) - (a.pts_pct || 0); });

        var panel = document.createElement('div');
        panel.id = 'nhl-intel-panel';
        var html = '<h3 class="section-title" style="margin-top:1.5rem">NHL Intelligence</h3>';
        html += '<p class="text-dim" style="font-size:0.85rem;margin-bottom:0.5rem">Live NHL standings powering our hockey predictions. Updated via ESPN.</p>';
        html += '<div style="max-height:300px;overflow-y:auto"><table><tr><th>Team</th><th>Record</th><th>Pts</th><th>Pts%</th><th>Home</th><th>Away</th><th>Streak</th><th>GF</th><th>GA</th></tr>';
        for (var i = 0; i < Math.min(teamArr.length, 32); i++) {
            var t = teamArr[i];
            var sColor = (t.streak || '').indexOf('W') === 0 ? 'var(--green)' : 'var(--red)';
            html += '<tr><td><strong>' + (t.short_name || t.name || '') + '</strong></td><td>' + t.wins + '-' + t.losses + '-' + (t.otl || 0) + '</td><td>' + (t.points || '--') + '</td><td>' + ((t.pts_pct || 0) * 100).toFixed(1) + '%</td><td>' + (t.home_record || '--') + '</td><td>' + (t.away_record || '--') + '</td><td style="color:' + sColor + '">' + (t.streak || '--') + '</td><td>' + (t.goals_for || '--') + '</td><td>' + (t.goals_against || '--') + '</td></tr>';
        }
        html += '</table></div>';
        if (data.updated_at) html += '<div style="font-size:0.72rem;color:var(--text-dim);margin-top:0.5rem;text-align:right">Updated: ' + data.updated_at + ' | Source: ESPN</div>';
        panel.innerHTML = html;
        perfTables.appendChild(panel);
    }

    // ── Main loader ──
    function loadAllIntelligence() {
        var sports = ['NBA', 'NHL', 'NFL', 'MLB'];
        for (var i = 0; i < sports.length; i++) {
            fetchSportStats(sports[i]);
            fetchScheduleIntel(sports[i]);
            fetchInjuryIntel(sports[i]);
        }
    }

    // Auto-load on DOMContentLoaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(loadAllIntelligence, 2000);
        });
    } else {
        setTimeout(loadAllIntelligence, 2000);
    }

    // Re-enrich when picks are refreshed
    var _origFP = window.fetchPicks;
    if (typeof _origFP === 'function') {
        window.fetchPicks = function() {
            _origFP.apply(this, arguments);
            setTimeout(enrichPickCards, 1500);
        };
    }

    // Export for manual refresh
    window.refreshSportsIntelligence = loadAllIntelligence;
    window.refreshNbaIntelligence = function() { fetchSportStats('NBA'); };
})();
