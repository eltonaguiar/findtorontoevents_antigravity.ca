// ============================================================
// DASHBOARD FRESHNESS ENGINE — Per-section EST timestamps &
// color-coded data-age badges for every major JSON data source.
//
// Loaded by template.html via <script src="dashboard_freshness.js">
// after dashboard_enhancements.js. Uses window._fmtEST if available
// (defined in template.html ~line 5275), otherwise provides its own.
//
// Freshness thresholds:
//   GREEN  = < 24 hours old
//   YELLOW = 24–72 hours old
//   RED    = > 72 hours old (STALE — banner-level warning)
//
// Data sources tracked:
//   1. dashboard_data.json   → generated_at
//   2. edge_stability_index.json → as_of
//   3. money_ready_verdict.json → generated_at
//   4. swarm_picks.json      → [0].created_at (first pick timestamp)
//   5. Walk-forward data     → DASHBOARD_DATA.walkforward.generated_at
//   6. AI leaderboard        → ai_leaderboard_index.json → generated_at
// ============================================================
(function () {
  'use strict';

  // ── EST formatter (matches edge_stability.html toEST helper) ────
  function toEST(utcStr) {
    if (!utcStr) return '—';
    try {
      return new Date(utcStr).toLocaleString('en-US', {
        timeZone: 'America/New_York',
        month: 'short', day: 'numeric', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
      });
    } catch (e) { return String(utcStr).slice(0, 16).replace('T', ' '); }
  }

  // Use the shared _fmtEST if the main script already defined it
  var fmtEST = window._fmtEST || toEST;

  // ── Freshness classification ──────────────────────────────────
  var HOUR = 3600000;
  var DAY  = 86400000;

  function freshnessLevel(isoStr) {
    if (!isoStr) return { level: 'unknown', ageMs: Infinity, label: 'NO DATA', color: '#6b7280', bg: 'rgba(107,114,128,0.12)' };
    var ms = Date.now() - new Date(isoStr).getTime();
    if (ms < 0) ms = 0;
    if (ms < 24 * HOUR)  return { level: 'green',  ageMs: ms, label: 'FRESH',   color: '#22c55e', bg: 'rgba(34,197,94,0.12)' };
    if (ms < 72 * HOUR)  return { level: 'yellow', ageMs: ms, label: 'AGING',   color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' };
    return                           { level: 'red',    ageMs: ms, label: 'STALE',   color: '#ef4444', bg: 'rgba(239,68,68,0.12)' };
  }

  function ageText(ms) {
    if (!isFinite(ms) || ms < 0) return 'unknown';
    var mins = Math.floor(ms / 60000);
    if (mins < 1)   return 'just now';
    if (mins < 60)  return mins + 'm ago';
    var hrs = Math.floor(mins / 60);
    if (hrs < 24)   return hrs + 'h ' + (mins % 60) + 'm ago';
    var days = Math.floor(hrs / 24);
    return days + 'd ' + (hrs % 24) + 'h ago';
  }

  // ── XSS-safe HTML escape ──────────────────────────────────────
  function esc(v) {
    if (v == null) return '';
    return String(v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // ── Badge HTML builder ────────────────────────────────────────
  function badge(isoStr, extraLabel) {
    var f = freshnessLevel(isoStr);
    var est = isoStr ? fmtEST(isoStr) : 'no data';
    var age = ageText(f.ageMs);
    var label = extraLabel ? extraLabel + ' · ' : '';
    return '<span style="display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700;background:' +
      f.bg + ';color:' + f.color + ';border:1px solid ' + f.color + '40;white-space:nowrap" title="' +
      esc(label + 'Generated: ' + est + ' EST — ' + age) + '">' +
      '<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:' + f.color + '"></span>' +
      esc(f.label) + ' <span style="font-weight:400;opacity:0.8">' + esc(age) + '</span></span>';
  }

  // ── Fetch with timeout & error handling ───────────────────────
  function fetchJSON(url, timeoutMs) {
    timeoutMs = timeoutMs || 8000;
    var ctrl = new AbortController();
    var timer = setTimeout(function() { ctrl.abort(); }, timeoutMs);
    return fetch(url + '?_=' + Date.now(), { cache: 'no-store', signal: ctrl.signal })
      .then(function(r) { clearTimeout(timer); if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .catch(function(e) { clearTimeout(timer); return null; });
  }

  // ── Data sources registry ─────────────────────────────────────
  var sources = [
    {
      id: 'dashboard-data',
      label: 'Dashboard Data',
      description: 'Main picks, portfolios & system metrics',
      url: 'data/dashboard_data.json',
      extract: function(json) { return json && (json.generated_at || (json.metadata && json.metadata.generated_at)); }
    },
    {
      id: 'edge-stability',
      label: 'Edge Stability',
      description: 'Per-asset-class edge consistency (7d/30d/90d/all-time)',
      url: 'data/edge_stability/edge_stability_index.json',
      extract: function(json) { return json && json.as_of; }
    },
    {
      id: 'money-ready',
      label: 'Money Ready Verdict',
      description: 'DSR-verified Tier-1 deploy readiness',
      url: 'data/money_ready_verdict.json',
      extract: function(json) { return json && (json.generated_at || json.generated_date); }
    },
    
    {
      id: 'ai-leaderboard',
      label: 'AI Leaderboard',
      description: 'Per-AI pick attribution & performance',
      url: 'data/ai_leaderboard/ai_leaderboard_index.json',
      extract: function(json) { return json && (json.generated_at || json.as_of); }
    },
    {
      id: 'theory-tracker',
      label: 'Theory / Hypothesis Tracker',
      description: 'Theory portfolios & h0XX hypothesis harness rows',
      url: 'data/theory_tracker.json',
      extract: function(json) { return json && json.generated_at; }
    }
  ];

  // ── Per-section inline timestamp targets ──────────────────────
  // Maps data source ID → array of DOM element IDs that should get
  // an inline freshness badge injected.
  var sectionTimestamps = {
    'dashboard-data':   ['last-updated', 'summary-cards-freshness'],
    'edge-stability':   ['edge-stability-freshness'],
    'money-ready':      ['money-ready-freshness'],
    'ai-leaderboard':   ['ai-leaderboard-freshness']
  };

  // ── Build the top-level freshness panel ───────────────────────
  function buildFreshnessPanel(results) {
    // Find the anchor: insert after the header div
    var header = document.querySelector('.header');
    if (!header) return;

    // Check if panel already exists (idempotent)
    if (document.getElementById('data-freshness-panel')) return;

    var panel = document.createElement('div');
    panel.id = 'data-freshness-panel';
    panel.style.cssText = 'max-width:1180px;margin:0 auto 12px;padding:12px 18px;background:linear-gradient(135deg,rgba(15,23,42,0.95),rgba(30,41,59,0.9));border:1px solid #334155;border-radius:10px;color:#e2e8f0;font-size:13px';

    // 2026-11-16: a source that failed to load (HTTP error, or a body the
    // browser's JSON.parse rejects) carries no timestamp and used to be skipped
    // by this verdict entirely — so the panel printed "ALL SOURCES CURRENT"
    // directly above a tile reading "No data available" (seen live on
    // money_ready_verdict.json while it shipped bare NaN tokens). Missing is
    // not current: count it as a problem, and name it as a loading failure.
    var hasMissing = results.some(function(r) { return !r.timestamp; });
    var hasStale = results.some(function(r) { return r.freshness && r.freshness.level === 'red'; });
    var hasProblem = hasStale || hasMissing;
    var headerIcon = hasProblem ? '&#x26A0;' : '&#x2705;';
    var headerColor = hasStale ? '#ef4444' : (hasMissing ? '#f59e0b' : '#22c55e');
    var headerText = hasStale ? 'DATA FRESHNESS — STALE SOURCES DETECTED'
                   : (hasMissing ? 'DATA FRESHNESS — SOURCE NOT LOADING'
                   : 'DATA FRESHNESS — ALL SOURCES CURRENT');

    var html = '<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap">' +
      '<span style="font-size:15px;font-weight:700;color:' + headerColor + '">' + headerIcon + ' ' + esc(headerText) + '</span>' +
      '<span style="margin-left:auto;font-size:11px;color:#94a3b8">Auto-checks on page load · Times in EST/EDT</span>' +
      '</div>';

    html += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:8px">';

    results.forEach(function(r) {
      var f = r.freshness || freshnessLevel(null);
      var est = r.timestamp ? fmtEST(r.timestamp) : 'no data';
      var age = ageText(f.ageMs);
      var isStale = f.level === 'red';
      var isMissing = !r.timestamp;

      html += '<div style="background:rgba(0,0,0,0.3);border:1px solid ' + f.color + '30;border-radius:8px;padding:10px 12px;position:relative' +
        ((isStale || isMissing) ? ';border-left:3px solid ' + f.color : '') + '">' +
        '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px">' +
        '<span style="font-size:12px;font-weight:700;color:' + f.color + '">' + esc(r.label) + '</span>' +
        '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:' + f.color +
        ';box-shadow:0 0 6px ' + f.color + '60"></span></div>' +
        '<div style="font-size:10px;color:#94a3b8;margin-bottom:4px">' + esc(r.description) + '</div>' +
        '<div style="font-size:11px;color:' + f.color + ';font-weight:600">' +
        (r.timestamp ? esc(est) + ' EST' : 'No data available') + '</div>' +
        '<div style="font-size:10px;color:#64748b;margin-top:2px">' + esc(age) + '</div>' +
        (isStale ? '<div style="font-size:9px;color:#fca5a5;margin-top:4px;padding:3px 6px;background:rgba(239,68,68,0.1);border-radius:4px">&#x26A0; Data is over 3 days old — may not reflect current state</div>' : '') +
        (isMissing ? '<div style="font-size:9px;color:#fcd34d;margin-top:4px;padding:3px 6px;background:rgba(245,158,11,0.12);border-radius:4px">&#x26A0; No timestamp — file missing, unreachable, or not valid JSON. Treated as unverified, not current.</div>' : '') +
        '</div>';
    });

    html += '</div>';
    panel.innerHTML = html;

    // Insert after header, before any banners
    var firstBanner = header.nextElementSibling;
    if (firstBanner) {
      header.parentNode.insertBefore(panel, firstBanner);
    } else {
      header.parentNode.appendChild(panel);
    }
  }

  // ── Inject per-section inline badges ──────────────────────────
  function injectSectionBadges(sourceId, timestamp) {
    var targets = sectionTimestamps[sourceId];
    if (!targets) return;
    // 2026-06-09: label each inline badge with its section so co-located badges
    // don't read as a meaningless "FRESH FRESH FRESH" cluster (operator feedback).
    var srcLabel = '';
    for (var si = 0; si < sources.length; si++) {
      if (sources[si].id === sourceId) { srcLabel = sources[si].label; break; }
    }
    targets.forEach(function(targetId) {
      var el = document.getElementById(targetId);
      if (!el) return;
      // Don't overwrite if already has a freshness badge
      if (el.querySelector('[data-freshness-badge]')) return;
      var f = freshnessLevel(timestamp);
      var est = timestamp ? fmtEST(timestamp) : 'no data';
      var age = ageText(f.ageMs);
      var span = document.createElement('span');
      span.setAttribute('data-freshness-badge', sourceId);
      span.style.cssText = 'display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:600;background:' +
        f.bg + ';color:' + f.color + ';border:1px solid ' + f.color + '40;margin-left:8px;white-space:nowrap';
      span.innerHTML = '<span style="width:5px;height:5px;border-radius:50%;background:' + f.color + '"></span>' +
        (srcLabel ? esc(srcLabel) + ' · ' : '') + esc(f.label) + ' · ' + esc(age);
      span.title = (srcLabel ? srcLabel + ' — ' : '') + 'Generated: ' + esc(est) + ' EST';
      el.appendChild(span);
    });
  }

  // ── Inject freshness indicator into section headers ───────────
  function injectSectionHeaderBadges() {
    // Walk-forward by-class card
    var wfMeta = document.getElementById('walkforward-by-class-meta');
    if (wfMeta && window.DASHBOARD_DATA && window.DASHBOARD_DATA.walkforward && window.DASHBOARD_DATA.walkforward.generated_at) {
      var wfTs = window.DASHBOARD_DATA.walkforward.generated_at;
      var wfF = freshnessLevel(wfTs);
      var wfBadge = document.createElement('span');
      wfBadge.setAttribute('data-freshness-badge', 'walkforward');
      wfBadge.style.cssText = 'display:inline-flex;align-items:center;gap:3px;padding:2px 6px;border-radius:8px;font-size:9px;font-weight:600;background:' +
        wfF.bg + ';color:' + wfF.color + ';border:1px solid ' + wfF.color + '40;margin-left:6px';
      wfBadge.innerHTML = '<span style="width:4px;height:4px;border-radius:50%;background:' + wfF.color + '"></span>' + esc(wfF.label);
      wfBadge.title = 'Walk-forward generated: ' + fmtEST(wfTs) + ' EST';
      wfMeta.appendChild(wfBadge);
    }

    // IC Analysis card
    var icMeta = document.getElementById('ic-analysis-meta');
    if (icMeta && window.DASHBOARD_DATA && window.DASHBOARD_DATA.ic_analysis && window.DASHBOARD_DATA.ic_analysis.generated_at) {
      var icTs = window.DASHBOARD_DATA.ic_analysis.generated_at;
      var icF = freshnessLevel(icTs);
      var icBadge = document.createElement('span');
      icBadge.setAttribute('data-freshness-badge', 'ic-analysis');
      icBadge.style.cssText = 'display:inline-flex;align-items:center;gap:3px;padding:2px 6px;border-radius:8px;font-size:9px;font-weight:600;background:' +
        icF.bg + ';color:' + icF.color + ';border:1px solid ' + icF.color + '40;margin-left:6px';
      icBadge.innerHTML = '<span style="width:4px;height:4px;border-radius:50%;background:' + icF.color + '"></span>' + esc(icF.label);
      icBadge.title = 'IC analysis generated: ' + fmtEST(icTs) + ' EST';
      icMeta.appendChild(icBadge);
    }

    // Major goal banner asof
    var goalAsOf = document.getElementById('major-goal-asof');
    if (goalAsOf && window.DASHBOARD_DATA) {
      var goalTs = window.DASHBOARD_DATA.generated_at || (window.DASHBOARD_DATA.metadata && window.DASHBOARD_DATA.metadata.generated_at);
      if (goalTs) {
        var goalF = freshnessLevel(goalTs);
        var goalBadge = document.createElement('span');
        goalBadge.setAttribute('data-freshness-badge', 'major-goal');
        goalBadge.style.cssText = 'display:inline-flex;align-items:center;gap:3px;padding:2px 6px;border-radius:8px;font-size:9px;font-weight:600;background:' +
          goalF.bg + ';color:' + goalF.color + ';border:1px solid ' + goalF.color + '40;margin-left:6px';
        goalBadge.innerHTML = '<span style="width:4px;height:4px;border-radius:50%;background:' + goalF.color + '"></span>' + esc(goalF.label);
        goalAsOf.appendChild(goalBadge);
      }
    }

    // TA Baseline section
    var taMeta = document.getElementById('ta-baseline-meta');
    if (taMeta && window.DASHBOARD_DATA && window.DASHBOARD_DATA.ta_baseline && window.DASHBOARD_DATA.ta_baseline.generated_at) {
      var taTs = window.DASHBOARD_DATA.ta_baseline.generated_at;
      var taF = freshnessLevel(taTs);
      var taBadge = document.createElement('span');
      taBadge.setAttribute('data-freshness-badge', 'ta-baseline');
      taBadge.style.cssText = 'display:inline-flex;align-items:center;gap:3px;padding:2px 6px;border-radius:8px;font-size:9px;font-weight:600;background:' +
        taF.bg + ';color:' + taF.color + ';border:1px solid ' + taF.color + '40;margin-left:6px';
      taBadge.innerHTML = '<span style="width:4px;height:4px;border-radius:50%;background:' + taF.color + '"></span>' + esc(taF.label);
      taBadge.title = 'TA baseline generated: ' + fmtEST(taTs) + ' EST';
      taMeta.appendChild(taBadge);
    }

    // Tier-2 hero section
    var t2Meta = document.getElementById('tier2-hero-meta');
    if (t2Meta && window.DASHBOARD_DATA && window.DASHBOARD_DATA.tier2_proven_strategies && window.DASHBOARD_DATA.tier2_proven_strategies.generated_at) {
      var t2Ts = window.DASHBOARD_DATA.tier2_proven_strategies.generated_at;
      var t2F = freshnessLevel(t2Ts);
      var t2Badge = document.createElement('span');
      t2Badge.setAttribute('data-freshness-badge', 'tier2-hero');
      t2Badge.style.cssText = 'display:inline-flex;align-items:center;gap:3px;padding:2px 6px;border-radius:8px;font-size:9px;font-weight:600;background:' +
        t2F.bg + ';color:' + t2F.color + ';border:1px solid ' + t2F.color + '40;margin-left:6px';
      t2Badge.innerHTML = '<span style="width:4px;height:4px;border-radius:50%;background:' + t2F.color + '"></span>' + esc(t2F.label);
      t2Badge.title = 'Tier-2 hero data generated: ' + fmtEST(t2Ts) + ' EST';
      t2Meta.appendChild(t2Badge);
    }

    // Swarm panel headline
    var swarmHeadline = document.getElementById('swarm-panel-headline');
    if (swarmHeadline && window.DASHBOARD_DATA && window.DASHBOARD_DATA.swarm_picks_data) {
      var swarmData = window.DASHBOARD_DATA.swarm_picks_data;
      var swarmTs = swarmData.generated_at || (swarmData.picks && swarmData.picks.length > 0 ? swarmData.picks[0].created_at : null);
      if (swarmTs) {
        var swarmF = freshnessLevel(swarmTs);
        var swarmBadge = document.createElement('span');
        swarmBadge.setAttribute('data-freshness-badge', 'swarm');
        swarmBadge.style.cssText = 'display:inline-flex;align-items:center;gap:3px;padding:2px 6px;border-radius:8px;font-size:9px;font-weight:600;background:' +
          swarmF.bg + ';color:' + swarmF.color + ';border:1px solid ' + swarmF.color + '40;margin-left:8px';
        swarmBadge.innerHTML = '<span style="width:4px;height:4px;border-radius:50%;background:' + swarmF.color + '"></span>' + esc(swarmF.label) + ' · ' + esc(ageText(swarmF.ageMs));
        swarmBadge.title = 'Swarm data: ' + fmtEST(swarmTs) + ' EST';
        swarmHeadline.parentNode.insertBefore(swarmBadge, swarmHeadline.nextSibling);
      }
    }

    // Performance analytics header
    var perfHeader = document.getElementById('perf-section-header');
    if (perfHeader && window.DASHBOARD_DATA) {
      var perfTs = window.DASHBOARD_DATA.generated_at || (window.DASHBOARD_DATA.metadata && window.DASHBOARD_DATA.metadata.generated_at);
      if (perfTs) {
        var perfF = freshnessLevel(perfTs);
        var perfBadge = document.createElement('span');
        perfBadge.setAttribute('data-freshness-badge', 'perf');
        perfBadge.style.cssText = 'display:inline-flex;align-items:center;gap:3px;padding:2px 6px;border-radius:8px;font-size:9px;font-weight:600;background:' +
          perfF.bg + ';color:' + perfF.color + ';border:1px solid ' + perfF.color + '40;margin-left:6px';
        perfBadge.innerHTML = '<span style="width:4px;height:4px;border-radius:50%;background:' + perfF.color + '"></span>' + esc(perfF.label);
        perfBadge.title = 'Performance data generated: ' + fmtEST(perfTs) + ' EST';
        perfHeader.appendChild(perfBadge);
      }
    }
  }

  // ── Per-TAB staleness tags (2026-10-04) ───────────────────────
  // Tags a TAB whose backing payload section is RED (>72h) directly on the tab
  // button, so staleness is visible where the data would be read and can be
  // actioned later (by an operator or an AI agent).
  //
  // HONESTY NOTE: a tab can only be aged if its payload section actually carries
  // a timestamp. Sections with no timestamp resolve to 'unknown' and are
  // deliberately NOT tagged — tagging them would be a guess. The map below is
  // derived from each tab's render function (which keys it reads from
  // window.DASHBOARD_DATA), not guessed from section names.
  //
  // Follow-up that would let the remaining tabs be aged: emit a per-section
  // generated_at from audit_trail/dashboard_generator.py.
  // NOTE: only tabs that actually exist as a `.tab-btn[data-tab=...]` in
  // template.html are listed — a mapping for a tab with no button would never
  // render. The tab bar currently exposes: active, closed, overview,
  // performance, mlhealth, leaderboard, dashboards, permutations, scoretracker,
  // smartpicks, ueps, verifiedalpha, links. Tabs whose payload keys we cannot
  // prove are deliberately omitted rather than guessed.
  var TAB_SOURCES = {
    active:       ['picks', 'systems'],
    closed:       ['picks', 'systems'],
    overview:     ['performance', 'picks', 'summary', 'systems'],
    performance:  ['picks', 'walkforward'],
    mlhealth:     ['ml_health'],
    leaderboard:  ['leaderboard'],
    dashboards:   ['audit_events', 'filter_events'],
    permutations: ['cross_strategy_permutations', 'cross_system_permutations']
  };

  // Deep-resolve a dotted path against the payload.
  function resolvePath(obj, path) {
    var cur = obj;
    var parts = String(path).split('.');
    for (var i = 0; i < parts.length; i++) {
      if (cur == null) return null;
      cur = cur[parts[i]];
    }
    return cur;
  }

  // Newest ISO-ish timestamp anywhere inside a value (bounded walk).
  function newestTimestamp(o, depth) {
    if (depth > 4) return null;
    var best = null, i;
    if (typeof o === 'string') {
      return (/^\d{4}-\d{2}-\d{2}/.test(o) && o.length >= 10) ? o : null;
    }
    if (Array.isArray(o)) {
      for (i = 0; i < Math.min(o.length, 500); i++) {
        var r = newestTimestamp(o[i], (depth || 0) + 1);
        if (r && (best === null || r > best)) best = r;
      }
      return best;
    }
    if (o && typeof o === 'object') {
      for (var k in o) {
        if (!Object.prototype.hasOwnProperty.call(o, k)) continue;
        var rr = newestTimestamp(o[k], (depth || 0) + 1);
        if (rr && (best === null || rr > best)) best = rr;
      }
      return best;
    }
    return null;
  }

  function tabFreshness(D, keys) {
    var best = null;
    for (var i = 0; i < keys.length; i++) {
      var ts = newestTimestamp(resolvePath(D, keys[i]), 0);
      if (ts && (best === null || ts > best)) best = ts;
    }
    return best ? freshnessLevel(best) : { level: 'unknown', ageMs: Infinity, label: 'NO DATA', color: '#6b7280', bg: 'rgba(107,114,128,0.12)' };
  }

  function injectTabStaleBadges() {
    var D = window.DASHBOARD_DATA;
    if (!D) return;
    Object.keys(TAB_SOURCES).forEach(function(tab) {
      var btn = document.querySelector('.tab-btn[data-tab="' + tab + '"]');
      if (!btn) return;
      if (btn.querySelector('[data-stale-tag]')) return;
      var f = tabFreshness(D, TAB_SOURCES[tab]);
      if (f.level !== 'red') return;
      var tag = document.createElement('span');
      tag.setAttribute('data-stale-tag', tab);
      tag.style.cssText = 'display:inline-flex;align-items:center;gap:4px;padding:1px 7px;border-radius:9px;font-size:9px;font-weight:800;letter-spacing:0.4px;background:rgba(239,68,68,0.18);color:#f87171;border:1px solid rgba(239,68,68,0.5);margin-left:6px;white-space:nowrap';
      tag.innerHTML = '&#x26A0; STALE ' + esc(ageText(f.ageMs));
      tag.title = 'STALE DATA: this tab is backed by ' + TAB_SOURCES[tab].join(', ') +
        ', whose newest timestamp is ' + esc(ageText(f.ageMs)) + ' old. Not a display bug — the upstream source has stopped updating. Actionable: re-run/repair the producer for ' +
        TAB_SOURCES[tab].join(', ') + '.';
      btn.appendChild(tag);
    });
  }

  // ── Per-asset-class staleness panel (2026-10-04) ─────────────
  // "Is every asset class still producing picks?" — computed from the payload's
  // own pick timestamps, so it needs no extra fetch and cannot disagree with
  // what the tables above actually show.
  var CLASS_KEYS = ['closed_at', 'signal_timestamp', 'recorded_at', 'entry_time', 'timestamp', 'created_at'];

  function pickTimestamp(p) {
    for (var i = 0; i < CLASS_KEYS.length; i++) {
      var v = p[CLASS_KEYS[i]];
      if (typeof v === 'string' && v.length >= 10) return v;
    }
    return null;
  }

  // ── Market-hours staleness (2026-11-15) ───────────────────────
  // ETF/BOND/EQUITY/COMMODITY/FUTURES are fed by weekday-only crons
  // (etf-bond-scanner.yml runs 13:35 and 14:00 UTC Mon-Fri). Judged in raw
  // wall-clock time every one of them manufactures a false "STALE — check that
  // class's scanner" alarm each weekend: Friday 14:00 UTC + 72h lands exactly on
  // Monday 14:00 UTC, so the alarm fires before the next run is even due. For
  // these classes the age excludes Sat/Sun, so the 72h budget measures trading
  // silence. CRYPTO (and anything unlisted) trades 24/7 and keeps wall-clock age.
  // Whole weekend days are subtracted rather than exact hours, which slightly
  // over-credits a partially-elapsed weekend — deliberately, because the failure
  // this guards against is a false alarm, not a missed one.
  var MARKET_CLASSES = { ETF: 1, BOND: 1, EQUITY: 1, COMMODITY: 1, FUTURES: 1,
                         INDEX_STOCK: 1, STOCKS: 1, PENNY_STOCK: 1 };

  function marketAgeMs(isoStr, assetClass) {
    var start = new Date(isoStr).getTime();
    if (!isFinite(start)) return Infinity;
    var ms = Date.now() - start;
    if (ms < 0) ms = 0;
    if (!MARKET_CLASSES[String(assetClass || '').toUpperCase()]) return ms;
    var DAY = 86400000;
    var excluded = 0;
    var t = new Date(start);
    t.setHours(0, 0, 0, 0);
    // Cap the walk: beyond ~3 months the pick is stale under any calendar.
    while (t.getTime() < Date.now() && excluded < 90 * DAY) {
      var dow = t.getDay();
      if (dow === 0 || dow === 6) excluded += DAY;
      t = new Date(t.getTime() + DAY);
    }
    return Math.max(0, ms - excluded);
  }

  function marketFreshness(isoStr, assetClass) {
    var f = freshnessLevel(isoStr);
    if (!isoStr || !MARKET_CLASSES[String(assetClass || '').toUpperCase()]) return f;
    var age = marketAgeMs(isoStr, assetClass);
    var lvl = age < 24 * HOUR ? 'green' : (age < 72 * HOUR ? 'yellow' : 'red');
    if (lvl === f.level) return f;
    var map = {
      green:  { label: 'FRESH', color: '#22c55e', bg: 'rgba(34,197,94,0.12)' },
      yellow: { label: 'AGING', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' },
      red:    { label: 'STALE', color: '#ef4444', bg: 'rgba(239,68,68,0.12)' }
    };
    var m = map[lvl];
    return { level: lvl, ageMs: age, label: m.label, color: m.color, bg: m.bg };
  }

  function assetClassStaleness(D) {
    var groups = [['active', (D.picks && D.picks.active) || []],
                  ['active_raw', (D.picks && D.picks.active_raw) || []],
                  ['recent_closed', (D.picks && D.picks.recent_closed) || []]];
    var out = [];
    groups.forEach(function(g) {
      var byClass = {};
      g[1].forEach(function(p) {
        if (!p || typeof p !== 'object') return;
        var ac = p.asset_class || 'UNKNOWN';
        var ts = pickTimestamp(p);
        if (!ts) return;
        if (!byClass[ac] || ts > byClass[ac].ts) byClass[ac] = { ts: ts, n: (byClass[ac] ? byClass[ac].n : 0) + 1 };
      });
      Object.keys(byClass).forEach(function(ac) {
        out.push({ group: g[0], assetClass: ac, ts: byClass[ac].ts, n: byClass[ac].n });
      });
    });
    return out;
  }

  function injectAssetClassStaleness() {
    var D = window.DASHBOARD_DATA;
    if (!D || !D.picks) return;
    var host = document.getElementById('asset-class-staleness');
    if (!host) {
      host = document.createElement('div');
      host.id = 'asset-class-staleness';
      host.style.cssText = 'max-width:1180px;margin:8px auto;padding:10px 14px;background:rgba(15,23,42,0.6);border:1px solid rgba(100,116,139,0.4);border-radius:10px';
      var anchor = document.getElementById('tab-bar');
      if (anchor && anchor.parentNode) anchor.parentNode.insertBefore(host, anchor);
      else document.body.insertBefore(host, document.body.firstChild);
    }
    var rows = assetClassStaleness(D);
    if (!rows.length) { host.innerHTML = '<div style="font-size:11px;color:#94a3b8">Asset-class staleness: no timestamped picks in payload.</div>'; return; }
    var stale = rows.filter(function(r) { return marketFreshness(r.ts, r.assetClass).level === 'red'; });
    var head = stale.length
      ? '<strong style="color:#f87171">&#x26A0; ' + stale.length + ' stale asset-class row(s)</strong>'
      : '<strong style="color:#22c55e">&#x2713; All asset-class rows fresh (&lt;72h)</strong>';
    var body = '<div style="font-size:11px;color:#94a3b8;margin:4px 0 6px">' + head +
      ' &middot; newest timestamped pick per class &middot; over 72h of *open-market* silence is tagged STALE ' +
      '(market-hours classes exclude Sat/Sun; CRYPTO ages in wall-clock time)</div>';
    body += '<div style="display:flex;flex-wrap:wrap;gap:6px">';
    rows.sort(function(a, b) { return (b.ts || '').localeCompare(a.ts || ''); });
    rows.forEach(function(r) {
      var f = marketFreshness(r.ts, r.assetClass);
      var isStale = f.level === 'red';
      var txt = esc(r.assetClass) + ' <span style="opacity:0.7">' + esc(r.group) + '</span> n=' + r.n + ' &middot; ' + esc(ageText(f.ageMs));
      body += '<span title="' + esc(r.assetClass + ' / ' + r.group + ' — newest ' + fmtEST(r.ts) + ' EST, n=' + r.n) + '" style="display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:10px;font-size:10px;font-weight:700;background:' +
        f.bg + ';color:' + f.color + ';border:1px solid ' + f.color + '40">' +
        (isStale ? '&#x26A0; STALE &middot; ' : '') + txt + '</span>';
    });
    body += '</div>';
    if (stale.length) {
      body += '<div style="font-size:10px;color:#fca5a5;margin-top:6px">Stale: ' +
        esc(stale.map(function(s) { return s.assetClass + '/' + s.group; }).join(', ')) +
        ' — no new picks in >72h of trading time. Actionable: check that class\'s scanner/emitter is still running.</div>';
    }
    host.innerHTML = body;
  }

  // ── Main: fetch all sources and render ────────────────────────
  function init() {
    var results = [];
    var pending = sources.length;

    sources.forEach(function(src) {
      fetchJSON(src.url).then(function(json) {
        var ts = src.extract(json);
        var f = freshnessLevel(ts);
        results.push({ id: src.id, label: src.label, description: src.description, timestamp: ts, freshness: f });
        // Inject per-section badges immediately
        injectSectionBadges(src.id, ts);
      }).catch(function() {
        results.push({ id: src.id, label: src.label, description: src.description, timestamp: null, freshness: freshnessLevel(null) });
      }).then(function() {
        pending--;
        if (pending <= 0) render();
      });
    });

    function render() {
      // Sort by staleness (red first)
      results.sort(function(a, b) {
        var order = { red: 0, yellow: 1, green: 2, unknown: 3 };
        return (order[a.freshness.level] || 9) - (order[b.freshness.level] || 9);
      });
      buildFreshnessPanel(results);

      // Also try to inject section-header badges (some may depend on DASHBOARD_DATA being loaded)
      injectSectionHeaderBadges();
      injectTabStaleBadges();
      injectAssetClassStaleness();

      // Listen for late data loads
      document.addEventListener('dashboard-data-loaded', function() {
        setTimeout(injectSectionHeaderBadges, 200);
        setTimeout(injectTabStaleBadges, 250);
        setTimeout(injectAssetClassStaleness, 250);
      });
    }
  }

  // ── Stale data banner ─────────────────────────────────────────
  // If any core source is >72h old, show a prominent banner at the very top.
  function checkStaleBanner() {
    // Wait for DASHBOARD_DATA to be available
    function tryBanner() {
      var D = window.DASHBOARD_DATA;
      if (!D || !D.generated_at) {
        setTimeout(tryBanner, 1000);
        return;
      }
      var dashboardFresh = freshnessLevel(D.generated_at);
      if (dashboardFresh.level !== 'red') return;

      // Check if banner already exists
      if (document.getElementById('stale-data-banner')) return;

      var banner = document.createElement('div');
      banner.id = 'stale-data-banner';
      banner.style.cssText = 'max-width:1180px;margin:0 auto 8px;padding:10px 16px;background:linear-gradient(135deg,rgba(239,68,68,0.15),rgba(239,68,68,0.08));border:1px solid rgba(239,68,68,0.5);border-radius:10px;color:#fecaca;font-size:13px;display:flex;align-items:center;gap:10px;flex-wrap:wrap';
      banner.innerHTML = '<span style="font-size:18px">&#x26A0;</span>' +
        '<div><strong style="color:#ef4444">STALE DATA WARNING</strong> — Dashboard data is ' +
        esc(ageText(dashboardFresh.ageMs)) + ' old (' + esc(fmtEST(D.generated_at)) + ' EST). ' +
        'The information shown may not reflect current market conditions. ' +
        '<a href="#" onclick="location.reload();return false" style="color:#fbbf24;text-decoration:underline;font-weight:600">Reload page</a> or check ' +
        '<a href="https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions" target="_blank" style="color:#fbbf24;text-decoration:underline;font-weight:600">workflow status</a>.</div>';

      var header = document.querySelector('.header');
      if (header && header.nextSibling) {
        header.parentNode.insertBefore(banner, header.nextSibling);
      }
    }
    tryBanner();
  }

  // ── Bootstrap ─────────────────────────────────────────────────
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { init(); checkStaleBanner(); });
  } else {
    init();
    checkStaleBanner();
  }

  // Re-inject section badges after main render completes
  window.addEventListener('load', function() {
    setTimeout(injectSectionHeaderBadges, 2000);
    setTimeout(injectTabStaleBadges, 2200);
    setTimeout(injectAssetClassStaleness, 2200);
  });

  // Expose for debugging
  window._freshnessEngine = {
    toEST: toEST,
    freshnessLevel: freshnessLevel,
    ageText: ageText,
    badge: badge,
    refresh: function() { init(); }
  };
})();
