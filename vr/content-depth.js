/**
 * VR Content Depth & Cross-Zone Intelligence — Set 14
 *
 * 10 content-depth and cross-zone features:
 *
 *  1. Quick Notes Scratchpad  — global floating sticky note (Ctrl+N)
 *  2. Events RSVP System      — attend/interested per event, RSVP count
 *  3. Movies Genre Filter     — filter by genre tags, multi-select
 *  4. Creator Comparison      — side-by-side stat comparison
 *  5. Stocks Sector Map       — visual sector breakdown canvas chart
 *  6. Weather Alerts          — severe weather notifications
 *  7. Wellness Breathing      — guided inhale/hold/exhale visualization
 *  8. Hub News Ticker         — scrolling updates banner
 *  9. Cross-Zone Timeline     — unified chronological content view
 * 10. Ambient Lighting Sync   — A-Frame light reacts to content
 *
 * Load via <script src="/vr/content-depth.js"></script>
 */
(function () {
  'use strict';

  function detectZone() {
    var p = location.pathname;
    if (p.indexOf('/vr/events') !== -1) return 'events';
    if (p.indexOf('/vr/movies') !== -1) return 'movies';
    if (p.indexOf('/vr/creators') !== -1) return 'creators';
    if (p.indexOf('/vr/stocks') !== -1) return 'stocks';
    if (p.indexOf('/vr/wellness') !== -1) return 'wellness';
    if (p.indexOf('/vr/weather') !== -1) return 'weather';
    if (p.indexOf('/vr/tutorial') !== -1) return 'tutorial';
    return 'hub';
  }
  var zone = detectZone();

  function store(k, v) { try { localStorage.setItem('vr14_' + k, JSON.stringify(v)); } catch (e) {} }
  function load(k, d) { try { var v = localStorage.getItem('vr14_' + k); return v ? JSON.parse(v) : d; } catch (e) { return d; } }
  function css(id, t) { if (document.getElementById(id)) return; var s = document.createElement('style'); s.id = id; s.textContent = t; document.head.appendChild(s); }
  function toast(m, c) {
    c = c || '#7dd3fc';
    var t = document.createElement('div');
    t.style.cssText = 'position:fixed;top:16px;left:50%;transform:translateX(-50%);z-index:9300;background:rgba(15,12,41,0.95);color:' + c + ';padding:10px 20px;border-radius:10px;font:600 13px/1.3 Inter,system-ui,sans-serif;border:1px solid ' + c + '33;backdrop-filter:blur(10px);pointer-events:none;animation:vr14t .3s ease-out';
    t.textContent = m; document.body.appendChild(t);
    setTimeout(function () { t.style.opacity = '0'; t.style.transition = 'opacity .3s'; }, 2500);
    setTimeout(function () { if (t.parentNode) t.remove(); }, 3000);
  }
  css('vr14-base', '@keyframes vr14t{from{opacity:0;transform:translateX(-50%) translateY(-10px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}');

  /* ═══════════════════════════════════════════════
     1. QUICK NOTES SCRATCHPAD (Ctrl+N)
     ═══════════════════════════════════════════════ */
  var scratchpad = (function () {
    var text = load('scratchpad', '');
    var visible = false;

    function toggle() {
      visible = !visible;
      var el = document.getElementById('vr14-scratch');
      if (visible && !el) { createPad(); return; }
      if (el) el.style.display = visible ? 'block' : 'none';
    }

    function createPad() {
      css('vr14-scratch-css',
        '#vr14-scratch{position:fixed;bottom:60px;left:10px;z-index:250;width:220px;background:rgba(255,248,220,0.97);border:1px solid rgba(200,180,100,0.4);border-radius:10px;padding:10px;font:12px/1.4 "Courier New",monospace;box-shadow:0 4px 20px rgba(0,0,0,0.3)}' +
        '#vr14-scratch textarea{width:100%;height:120px;border:none;background:transparent;color:#1a1a1a;font:12px/1.5 "Courier New",monospace;resize:vertical;outline:none}' +
        '#vr14-scratch-hdr{display:flex;justify-content:space-between;margin-bottom:6px;font:700 11px Inter,system-ui,sans-serif;color:#8b7355}'
      );
      var el = document.createElement('div');
      el.id = 'vr14-scratch';
      el.innerHTML = '<div id="vr14-scratch-hdr"><span>📝 Scratchpad</span><button onclick="VRContentDepth.scratchpad.toggle()" style="background:none;border:none;color:#8b7355;cursor:pointer;font-size:14px">&times;</button></div>' +
        '<textarea id="vr14-scratch-txt" placeholder="Quick notes...">' + text.replace(/</g, '&lt;') + '</textarea>';
      document.body.appendChild(el);
      var ta = document.getElementById('vr14-scratch-txt');
      ta.addEventListener('input', function () { text = ta.value; store('scratchpad', text); });
      visible = true;
    }

    document.addEventListener('keydown', function (e) {
      if (e.ctrlKey && e.key === 'n') { e.preventDefault(); toggle(); }
    });

    return { toggle: toggle, getText: function () { return text; }, setText: function (t) { text = t; store('scratchpad', t); var ta = document.getElementById('vr14-scratch-txt'); if (ta) ta.value = t; } };
  })();

  /* ═══════════════════════════════════════════════
     2. EVENTS RSVP SYSTEM
     ═══════════════════════════════════════════════ */
  var eventsRSVP = (function () {
    if (zone !== 'events') return null;
    var rsvps = load('rsvps', {});

    function setRSVP(eventId, status) {
      // status: 'attending', 'interested', or null to remove
      if (!status) { delete rsvps[eventId]; }
      else { rsvps[eventId] = { status: status, time: Date.now() }; }
      store('rsvps', rsvps);
      toast(status ? (status === 'attending' ? '✅ Attending!' : '⭐ Interested') : 'RSVP removed', status === 'attending' ? '#22c55e' : '#f59e0b');
    }

    function getRSVP(eventId) { return rsvps[eventId] || null; }

    function getCount(status) {
      return Object.values(rsvps).filter(function (r) { return r.status === status; }).length;
    }

    function createBadge() {
      css('vr14-rsvp-css',
        '#vr14-rsvp-badge{position:fixed;top:90px;left:10px;z-index:160;background:rgba(15,12,41,0.92);border:1px solid rgba(34,197,94,0.2);border-radius:12px;padding:8px 12px;color:#e2e8f0;font:11px/1.4 Inter,system-ui,sans-serif;backdrop-filter:blur(10px)}' +
        '#vr14-rsvp-badge h4{margin:0 0 4px;color:#22c55e;font-size:12px}'
      );
      var el = document.createElement('div');
      el.id = 'vr14-rsvp-badge';
      renderBadge(el);
      document.body.appendChild(el);
    }

    function renderBadge(container) {
      container = container || document.getElementById('vr14-rsvp-badge');
      if (!container) return;
      container.innerHTML = '<h4>📋 My RSVPs</h4>' +
        '<div>✅ Attending: <strong>' + getCount('attending') + '</strong></div>' +
        '<div>⭐ Interested: <strong>' + getCount('interested') + '</strong></div>';
    }

    function getButtonHTML(eventId) {
      var current = rsvps[eventId];
      return '<span class="vr14-rsvp-btns">' +
        '<button onclick="VRContentDepth.eventsRSVP.set(\'' + eventId + '\',\'attending\')" style="background:' + (current && current.status === 'attending' ? 'rgba(34,197,94,0.2)' : 'none') + ';border:1px solid rgba(34,197,94,0.3);color:#86efac;border-radius:4px;padding:2px 6px;cursor:pointer;font:600 10px Inter,sans-serif">✅ Going</button> ' +
        '<button onclick="VRContentDepth.eventsRSVP.set(\'' + eventId + '\',\'interested\')" style="background:' + (current && current.status === 'interested' ? 'rgba(245,158,11,0.2)' : 'none') + ';border:1px solid rgba(245,158,11,0.3);color:#fbbf24;border-radius:4px;padding:2px 6px;cursor:pointer;font:600 10px Inter,sans-serif">⭐ Maybe</button></span>';
    }

    setTimeout(createBadge, 1800);
    return { set: setRSVP, get: getRSVP, getCount: getCount, getButtonHTML: getButtonHTML, getAll: function () { return rsvps; } };
  })();

  /* ═══════════════════════════════════════════════
     3. MOVIES GENRE FILTER
     ═══════════════════════════════════════════════ */
  var moviesGenreFilter = (function () {
    if (zone !== 'movies') return null;
    var genres = ['Action', 'Comedy', 'Drama', 'Sci-Fi', 'Horror', 'Romance', 'Thriller', 'Animation', 'Documentary'];
    var selected = load('genre_filter', []);

    function createUI() {
      css('vr14-genre-css',
        '#vr14-genres{position:fixed;top:50px;right:10px;z-index:160;background:rgba(15,12,41,0.92);border:1px solid rgba(78,205,196,0.2);border-radius:12px;padding:8px 12px;width:180px;color:#e2e8f0;font:11px/1.4 Inter,system-ui,sans-serif;backdrop-filter:blur(10px)}' +
        '#vr14-genres h4{margin:0 0 6px;color:#4ecdc4;font-size:12px}' +
        '.vr14-genre-tag{display:inline-block;padding:3px 8px;margin:2px;border-radius:12px;border:1px solid rgba(78,205,196,0.2);background:transparent;color:#94a3b8;cursor:pointer;font:600 10px Inter,system-ui,sans-serif;transition:all .15s}' +
        '.vr14-genre-tag.active{background:rgba(78,205,196,0.15);border-color:rgba(78,205,196,0.4);color:#fff}'
      );
      var el = document.createElement('div');
      el.id = 'vr14-genres';
      renderGenres(el);
      document.body.appendChild(el);
    }

    function renderGenres(container) {
      container = container || document.getElementById('vr14-genres');
      if (!container) return;
      var html = '<h4>🎬 Genres</h4>';
      genres.forEach(function (g) {
        var isActive = selected.indexOf(g) !== -1;
        html += '<span class="vr14-genre-tag' + (isActive ? ' active' : '') + '" onclick="VRContentDepth.moviesGenreFilter.toggleGenre(\'' + g + '\')">' + g + '</span>';
      });
      if (selected.length > 0) html += '<div style="margin-top:4px;color:#64748b;font-size:9px">Filtering: ' + selected.join(', ') + '</div>';
      container.innerHTML = html;
    }

    function toggleGenre(g) {
      var idx = selected.indexOf(g);
      if (idx === -1) selected.push(g); else selected.splice(idx, 1);
      store('genre_filter', selected);
      renderGenres();
      toast('Genre: ' + (selected.length > 0 ? selected.join(', ') : 'All'), '#4ecdc4');
      window.dispatchEvent(new CustomEvent('vr-genre-filter', { detail: { genres: selected } }));
    }

    setTimeout(createUI, 1800);
    return { toggleGenre: toggleGenre, getSelected: function () { return selected.slice(); }, genres: genres };
  })();

  /* ═══════════════════════════════════════════════
     4. CREATOR COMPARISON
     ═══════════════════════════════════════════════ */
  var creatorComparison = (function () {
    if (zone !== 'creators') return null;
    var slots = [null, null];

    function setSlot(idx, creator) {
      // creator = { name, followers, views, platform }
      slots[idx] = creator;
    }

    function compare() {
      if (!slots[0] || !slots[1]) { toast('Select 2 creators to compare', '#ef4444'); return null; }
      return { a: slots[0], b: slots[1] };
    }

    function openPanel() {
      var existing = document.getElementById('vr14-compare');
      if (existing) { existing.remove(); return; }
      css('vr14-cmp-css',
        '#vr14-compare{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:600;background:rgba(15,12,41,0.97);border:1px solid rgba(168,85,247,0.25);border-radius:16px;padding:24px;width:min(420px,92vw);color:#e2e8f0;font:13px/1.5 Inter,system-ui,sans-serif;backdrop-filter:blur(16px)}' +
        '.vr14-cmp-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:12px 0}' +
        '.vr14-cmp-card{background:rgba(255,255,255,0.04);border-radius:10px;padding:12px;text-align:center}' +
        '.vr14-cmp-card h4{margin:0 0 8px;color:#c4b5fd;font-size:14px}' +
        '.vr14-cmp-stat{font-size:11px;padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.04)}'
      );
      var el = document.createElement('div');
      el.id = 'vr14-compare';
      el.setAttribute('role', 'dialog');
      var a = slots[0] || { name: 'Creator A', followers: '—', views: '—', platform: '—' };
      var b = slots[1] || { name: 'Creator B', followers: '—', views: '—', platform: '—' };
      el.innerHTML = '<h3 style="margin:0 0 10px;color:#a855f7;font-size:16px">⚖️ Creator Comparison</h3>' +
        '<div class="vr14-cmp-grid"><div class="vr14-cmp-card"><h4>' + a.name + '</h4><div class="vr14-cmp-stat">Followers: ' + a.followers + '</div><div class="vr14-cmp-stat">Views: ' + a.views + '</div><div class="vr14-cmp-stat">Platform: ' + a.platform + '</div></div>' +
        '<div class="vr14-cmp-card"><h4>' + b.name + '</h4><div class="vr14-cmp-stat">Followers: ' + b.followers + '</div><div class="vr14-cmp-stat">Views: ' + b.views + '</div><div class="vr14-cmp-stat">Platform: ' + b.platform + '</div></div></div>' +
        '<button onclick="document.getElementById(\'vr14-compare\').remove()" style="width:100%;padding:6px;background:rgba(168,85,247,0.1);color:#c4b5fd;border:1px solid rgba(168,85,247,0.2);border-radius:8px;cursor:pointer;font:600 12px Inter,system-ui,sans-serif">Close</button>';
      document.body.appendChild(el);
    }

    return { setSlot: setSlot, compare: compare, open: openPanel, getSlots: function () { return slots.slice(); } };
  })();

  /* ═══════════════════════════════════════════════
     5. STOCKS SECTOR MAP
     ═══════════════════════════════════════════════ */
  var stocksSectorMap = (function () {
    if (zone !== 'stocks') return null;
    var sectors = [
      { name: 'Technology', pct: 35, color: '#3b82f6' },
      { name: 'Healthcare', pct: 18, color: '#22c55e' },
      { name: 'Financials', pct: 15, color: '#f59e0b' },
      { name: 'Consumer', pct: 12, color: '#ef4444' },
      { name: 'Energy', pct: 10, color: '#06b6d4' },
      { name: 'Other', pct: 10, color: '#64748b' }
    ];

    function createChart() {
      css('vr14-sector-css',
        '#vr14-sectors{position:fixed;top:50px;right:10px;z-index:160;background:rgba(15,12,41,0.92);border:1px solid rgba(59,130,246,0.2);border-radius:12px;padding:10px;width:180px;color:#e2e8f0;font:11px/1.4 Inter,system-ui,sans-serif;backdrop-filter:blur(10px)}' +
        '#vr14-sectors h4{margin:0 0 8px;color:#60a5fa;font-size:12px}' +
        '.vr14-sector-bar{height:14px;border-radius:4px;margin-bottom:3px;display:flex;align-items:center;padding-left:6px;font:600 9px Inter,system-ui,sans-serif;color:#fff;transition:width .5s}'
      );
      var el = document.createElement('div');
      el.id = 'vr14-sectors';
      var html = '<h4>📊 Sectors</h4>';
      sectors.forEach(function (s) {
        html += '<div class="vr14-sector-bar" style="width:' + (s.pct * 1.5) + 'px;background:' + s.color + '">' + s.name + ' ' + s.pct + '%</div>';
      });
      el.innerHTML = html;
      document.body.appendChild(el);
    }

    setTimeout(createChart, 1800);
    return { getSectors: function () { return sectors; } };
  })();

  /* ═══════════════════════════════════════════════
     6. WEATHER ALERTS
     ═══════════════════════════════════════════════ */
  var weatherAlerts = (function () {
    if (zone !== 'weather') return null;
    var alerts = [];

    function checkAlerts() {
      fetch('https://api.open-meteo.com/v1/forecast?latitude=43.65&longitude=-79.38&current=weather_code,wind_speed_10m,temperature_2m&timezone=auto')
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d || !d.current) return;
          var c = d.current;
          alerts = [];
          if (c.wind_speed_10m > 50) alerts.push({ type: 'wind', msg: '⚠️ High winds: ' + c.wind_speed_10m + ' km/h', severity: 'warning' });
          if (c.temperature_2m < -20) alerts.push({ type: 'cold', msg: '🥶 Extreme cold: ' + c.temperature_2m + '°C', severity: 'danger' });
          if (c.temperature_2m > 35) alerts.push({ type: 'heat', msg: '🔥 Extreme heat: ' + c.temperature_2m + '°C', severity: 'danger' });
          if (c.weather_code >= 95) alerts.push({ type: 'storm', msg: '⛈️ Thunderstorm active', severity: 'danger' });
          if (c.weather_code >= 71 && c.weather_code <= 77) alerts.push({ type: 'snow', msg: '❄️ Snow warning', severity: 'warning' });
          renderAlerts();
        }).catch(function () {});
    }

    function renderAlerts() {
      var existing = document.getElementById('vr14-wx-alerts');
      if (existing) existing.remove();
      if (alerts.length === 0) return;
      css('vr14-alert-css',
        '#vr14-wx-alerts{position:fixed;top:90px;left:10px;z-index:160;background:rgba(15,12,41,0.92);border:1px solid rgba(239,68,68,0.3);border-radius:12px;padding:8px 12px;width:200px;color:#fca5a5;font:11px/1.4 Inter,system-ui,sans-serif;backdrop-filter:blur(10px)}' +
        '.vr14-alert-item{padding:3px 0;border-bottom:1px solid rgba(239,68,68,0.1)}'
      );
      var el = document.createElement('div');
      el.id = 'vr14-wx-alerts';
      var html = '<div style="font-weight:700;color:#ef4444;margin-bottom:4px;font-size:12px">⚠️ Weather Alerts</div>';
      alerts.forEach(function (a) { html += '<div class="vr14-alert-item">' + a.msg + '</div>'; });
      el.innerHTML = html;
      document.body.appendChild(el);
    }

    setTimeout(checkAlerts, 2500);
    return { check: checkAlerts, getAlerts: function () { return alerts; } };
  })();

  /* ═══════════════════════════════════════════════
     7. WELLNESS BREATHING EXERCISE
     ═══════════════════════════════════════════════ */
  var breathingExercise = (function () {
    if (zone !== 'wellness') return null;
    var running = false;
    var phase = 'idle';
    var timer = null;

    function createUI() {
      css('vr14-breathe-css',
        '#vr14-breathe{position:fixed;bottom:10px;left:10px;z-index:160;background:rgba(15,12,41,0.92);border:1px solid rgba(16,185,129,0.2);border-radius:14px;padding:12px 16px;width:180px;color:#e2e8f0;font:12px/1.4 Inter,system-ui,sans-serif;backdrop-filter:blur(10px);text-align:center}' +
        '#vr14-breathe h4{margin:0 0 6px;color:#10b981;font-size:13px}' +
        '#vr14-breathe-circle{width:80px;height:80px;border-radius:50%;border:3px solid #10b981;margin:8px auto;display:flex;align-items:center;justify-content:center;font:700 14px Inter,system-ui,sans-serif;color:#6ee7b7;transition:all 1s ease-in-out}' +
        '#vr14-breathe-circle.inhale{transform:scale(1.3);border-color:#22c55e;background:rgba(34,197,94,0.1)}' +
        '#vr14-breathe-circle.hold{transform:scale(1.3);border-color:#f59e0b;background:rgba(245,158,11,0.05)}' +
        '#vr14-breathe-circle.exhale{transform:scale(0.8);border-color:#06b6d4;background:rgba(6,182,212,0.05)}' +
        '.vr14-breathe-btn{padding:5px 14px;border-radius:8px;border:1px solid rgba(16,185,129,0.3);background:rgba(16,185,129,0.1);color:#6ee7b7;cursor:pointer;font:600 11px Inter,system-ui,sans-serif;margin-top:6px}'
      );
      var el = document.createElement('div');
      el.id = 'vr14-breathe';
      el.innerHTML = '<h4>🌬️ Breathe</h4><div id="vr14-breathe-circle">Ready</div><button class="vr14-breathe-btn" onclick="VRContentDepth.breathingExercise.toggle()">Start</button>';
      document.body.appendChild(el);
    }

    function toggle() {
      if (running) stop(); else start();
    }

    function start() {
      running = true;
      var circle = document.getElementById('vr14-breathe-circle');
      var btn = document.querySelector('.vr14-breathe-btn');
      if (btn) btn.textContent = 'Stop';
      var steps = [
        { phase: 'inhale', text: 'Inhale', dur: 4000 },
        { phase: 'hold',   text: 'Hold',   dur: 4000 },
        { phase: 'exhale', text: 'Exhale', dur: 6000 }
      ];
      var idx = 0;
      function nextPhase() {
        if (!running) return;
        var step = steps[idx % steps.length];
        phase = step.phase;
        if (circle) { circle.className = step.phase; circle.textContent = step.text; }
        idx++;
        timer = setTimeout(nextPhase, step.dur);
      }
      nextPhase();
    }

    function stop() {
      running = false;
      phase = 'idle';
      if (timer) { clearTimeout(timer); timer = null; }
      var circle = document.getElementById('vr14-breathe-circle');
      if (circle) { circle.className = ''; circle.textContent = 'Ready'; }
      var btn = document.querySelector('.vr14-breathe-btn');
      if (btn) btn.textContent = 'Start';
    }

    setTimeout(createUI, 1800);
    return { start: start, stop: stop, toggle: toggle, isRunning: function () { return running; }, getPhase: function () { return phase; } };
  })();

  /* ═══════════════════════════════════════════════
     8. HUB NEWS TICKER
     ═══════════════════════════════════════════════ */
  var newsTicker = (function () {
    if (zone !== 'hub') return null;
    var headlines = [
      '🎉 77 VR features now live across 8 zones!',
      '🎬 New movies added — check the Movies zone',
      '🎵 Explore wellness breathing exercises in the Wellness zone',
      '📊 Track your stocks portfolio in the Stocks zone',
      '🌦️ Real-time weather alerts now active in the Weather zone',
      '⭐ Follow your favorite creators in the Creators zone',
      '🏆 Daily challenges reset at midnight — complete yours today!',
      '🎨 Try the 5 new color themes via Ctrl+,',
      '📌 Pin anything to your cross-zone pinboard',
      '🗣️ Use voice commands (press V) for hands-free navigation'
    ];

    function createTicker() {
      css('vr14-ticker-css',
        '#vr14-ticker{position:fixed;bottom:45px;left:0;right:0;z-index:140;height:28px;background:rgba(10,10,26,0.85);border-top:1px solid rgba(0,212,255,0.1);overflow:hidden;backdrop-filter:blur(6px)}' +
        '#vr14-ticker-text{display:inline-block;white-space:nowrap;color:#94a3b8;font:600 12px Inter,system-ui,sans-serif;line-height:28px;padding-left:100%;animation:vr14scroll 40s linear infinite}' +
        '@keyframes vr14scroll{0%{transform:translateX(0)}100%{transform:translateX(-100%)}}'
      );
      var el = document.createElement('div');
      el.id = 'vr14-ticker';
      el.innerHTML = '<div id="vr14-ticker-text">' + headlines.join('  ●  ') + '  ●  ' + headlines.join('  ●  ') + '</div>';
      document.body.appendChild(el);
    }

    setTimeout(createTicker, 2000);
    return { getHeadlines: function () { return headlines; }, addHeadline: function (h) { headlines.push(h); } };
  })();

  /* ═══════════════════════════════════════════════
     9. CROSS-ZONE TIMELINE
     ═══════════════════════════════════════════════ */
  var crossTimeline = (function () {
    function gatherTimeline() {
      var items = [];
      // Gather from session replay
      try {
        var actions = JSON.parse(localStorage.getItem('vr12_sessions') || '[]');
        actions.forEach(function (s) {
          items.push({ type: 'session', zone: s.zone, time: s.start, text: 'Visited ' + s.zone + ' (' + s.duration + 's)' });
        });
      } catch (e) {}
      // Gather from bookmarks
      try {
        var bks = JSON.parse(localStorage.getItem('vr13_bookmarks') || '[]');
        bks.forEach(function (b) {
          items.push({ type: 'bookmark', zone: b.zone, time: b.time, text: 'Bookmarked: ' + b.title });
        });
      } catch (e) {}
      // Gather from RSVPs
      try {
        var rsvps = JSON.parse(localStorage.getItem('vr14_rsvps') || '{}');
        Object.keys(rsvps).forEach(function (k) {
          items.push({ type: 'rsvp', zone: 'events', time: rsvps[k].time, text: 'RSVP: ' + k + ' (' + rsvps[k].status + ')' });
        });
      } catch (e) {}
      // Gather from notifications
      try {
        var notifs = JSON.parse(localStorage.getItem('vr11_notifications') || '[]');
        notifs.slice(0, 10).forEach(function (n) {
          items.push({ type: 'notification', zone: 'all', time: n.time, text: n.text });
        });
      } catch (e) {}
      return items.sort(function (a, b) { return b.time - a.time; }).slice(0, 30);
    }

    function openTimeline() {
      var existing = document.getElementById('vr14-timeline');
      if (existing) { existing.remove(); return; }
      css('vr14-tl-css',
        '#vr14-timeline{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:600;background:rgba(15,12,41,0.97);border:1px solid rgba(0,212,255,0.25);border-radius:16px;padding:20px;width:min(400px,92vw);max-height:60vh;overflow-y:auto;color:#e2e8f0;font:12px/1.5 Inter,system-ui,sans-serif;backdrop-filter:blur(16px)}' +
        '.vr14-tl-item{display:flex;gap:10px;padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.04);font-size:11px}' +
        '.vr14-tl-type{min-width:16px;text-align:center}' +
        '.vr14-tl-time{color:#64748b;font-size:10px}'
      );
      var items = gatherTimeline();
      var el = document.createElement('div');
      el.id = 'vr14-timeline';
      el.setAttribute('role', 'dialog');
      var typeIcons = { session: '🔄', bookmark: '🔖', rsvp: '📋', notification: '🔔' };
      var html = '<h3 style="margin:0 0 10px;color:#7dd3fc;font-size:15px">🕐 Cross-Zone Timeline</h3>';
      if (items.length === 0) html += '<div style="color:#64748b">No activity yet. Explore zones to build your timeline!</div>';
      items.forEach(function (item) {
        var date = new Date(item.time);
        html += '<div class="vr14-tl-item"><span class="vr14-tl-type">' + (typeIcons[item.type] || '•') + '</span><div><div>' + item.text + '</div><span class="vr14-tl-time">' + date.toLocaleString() + ' · ' + item.zone + '</span></div></div>';
      });
      html += '<button onclick="document.getElementById(\'vr14-timeline\').remove()" style="margin-top:10px;width:100%;padding:6px;background:rgba(0,212,255,0.1);color:#7dd3fc;border:1px solid rgba(0,212,255,0.2);border-radius:8px;cursor:pointer;font:600 12px Inter,system-ui,sans-serif">Close</button>';
      el.innerHTML = html;
      document.body.appendChild(el);
    }

    return { open: openTimeline, gather: gatherTimeline };
  })();

  /* ═══════════════════════════════════════════════
     10. AMBIENT LIGHTING SYNC
     ═══════════════════════════════════════════════ */
  var ambientLighting = (function () {
    var zoneLighting = {
      hub:      { color: '#404080', intensity: 0.5 },
      events:   { color: '#ff6b6b', intensity: 0.4 },
      movies:   { color: '#1a1a2e', intensity: 0.2 },
      creators: { color: '#7c3aed', intensity: 0.4 },
      stocks:   { color: '#064e3b', intensity: 0.4 },
      wellness: { color: '#065f46', intensity: 0.5 },
      weather:  { color: '#164e63', intensity: 0.5 },
      tutorial: { color: '#3b82f6', intensity: 0.4 }
    };
    var enabled = load('ambient_lighting', true);

    function apply() {
      if (!enabled) return;
      var config = zoneLighting[zone] || zoneLighting.hub;
      // Apply to A-Frame scene if available
      try {
        var scene = document.querySelector('a-scene');
        if (scene) {
          var existingLight = document.getElementById('vr14-ambient-light');
          if (!existingLight) {
            var light = document.createElement('a-light');
            light.id = 'vr14-ambient-light';
            light.setAttribute('type', 'ambient');
            light.setAttribute('color', config.color);
            light.setAttribute('intensity', String(config.intensity));
            scene.appendChild(light);
          } else {
            existingLight.setAttribute('color', config.color);
            existingLight.setAttribute('intensity', String(config.intensity));
          }
        }
      } catch (e) {}
      // Also apply CSS overlay tint
      css('vr14-light-tint', '#vr14-light-overlay{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:1;background:' + config.color + ';opacity:0.03;mix-blend-mode:overlay}');
      if (!document.getElementById('vr14-light-overlay')) {
        var overlay = document.createElement('div');
        overlay.id = 'vr14-light-overlay';
        document.body.appendChild(overlay);
      }
    }

    function toggle() {
      enabled = !enabled;
      store('ambient_lighting', enabled);
      if (!enabled) {
        var light = document.getElementById('vr14-ambient-light');
        if (light) light.remove();
        var overlay = document.getElementById('vr14-light-overlay');
        if (overlay) overlay.remove();
      } else {
        apply();
      }
      toast('Ambient lighting ' + (enabled ? 'ON' : 'OFF'), '#a855f7');
    }

    // Apply on scene ready
    function onReady() {
      var scene = document.querySelector('a-scene');
      if (scene && scene.hasLoaded) { apply(); }
      else if (scene) { scene.addEventListener('loaded', apply); }
      else { setTimeout(apply, 3000); }
    }
    setTimeout(onReady, 2000);

    return { apply: apply, toggle: toggle, isEnabled: function () { return enabled; }, getConfig: function () { return zoneLighting[zone]; } };
  })();

  /* ═══════════════════════════════════════════════
     PUBLIC API
     ═══════════════════════════════════════════════ */
  window.VRContentDepth = {
    zone: zone,
    version: 14,
    scratchpad: scratchpad,
    eventsRSVP: eventsRSVP,
    moviesGenreFilter: moviesGenreFilter,
    creatorComparison: creatorComparison,
    stocksSectorMap: stocksSectorMap,
    weatherAlerts: weatherAlerts,
    breathingExercise: breathingExercise,
    newsTicker: newsTicker,
    crossTimeline: crossTimeline,
    ambientLighting: ambientLighting
  };

  console.log('[VR Content Depth] Set 14 loaded — ' + zone);
})();
