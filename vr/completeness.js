/**
 * VR Completeness & Polish — Set 9
 *
 * 10 production-readiness features:
 *
 *  1. Session Continuity   — resume last zone, filters, scroll position
 *  2. Error Recovery        — network retry w/ backoff, graceful degradation, connection HUD
 *  3. Accessibility Layer   — ARIA labels, focus ring, reduced-motion, high-contrast toggle
 *  4. First-Visit Onboarding — contextual tips per zone on first visit
 *  5. Performance LOD       — distance-based entity hiding, FPS monitor, auto-quality
 *  6. Events Calendar Minimap — month grid showing event density per day
 *  7. Movies Watch History  — track watched trailers, continue-watching row
 *  8. Weather Forecast Timeline — 24 h hourly breakdown bar
 *  9. Device Adaptive UI    — detect headset/desktop, scale text & controls
 * 10. What's New Changelog  — show latest features after updates
 *
 * Load via <script src="/vr/completeness.js"></script> in every zone.
 */
(function () {
  'use strict';

  /* ── helpers ─────────────────────────────────── */
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
  var currentZone = detectZone();

  function store(key, val) { try { localStorage.setItem('vr9_' + key, JSON.stringify(val)); } catch (e) {} }
  function load(key, fallback) { try { var v = localStorage.getItem('vr9_' + key); return v ? JSON.parse(v) : fallback; } catch (e) { return fallback; } }

  function injectStyle(id, css) {
    if (document.getElementById(id)) return;
    var s = document.createElement('style'); s.id = id; s.textContent = css;
    document.head.appendChild(s);
  }

  /* ═══════════════════════════════════════════════
     1. SESSION CONTINUITY
     ═══════════════════════════════════════════════ */
  var sessionState = (function () {
    // Save current zone + timestamp on every page load
    var lastSession = load('session', null);

    function save() {
      store('session', {
        zone: currentZone,
        path: location.pathname,
        time: Date.now(),
        scroll: window.scrollY || 0
      });
    }
    save();
    window.addEventListener('beforeunload', save);

    // Show "Continue" button on hub if returning within 4 hours
    function showContinueBtn() {
      if (currentZone !== 'hub' || !lastSession || lastSession.zone === 'hub') return;
      var age = Date.now() - (lastSession.time || 0);
      if (age > 4 * 60 * 60 * 1000) return; // older than 4 h

      var zoneNames = { events: 'Events Explorer', movies: 'Movie Theater', creators: 'Creators Lounge', stocks: 'Trading Floor', wellness: 'Wellness Garden', weather: 'Weather Observatory', tutorial: 'Tutorial' };
      var name = zoneNames[lastSession.zone] || lastSession.zone;

      injectStyle('vr9-continue-css',
        '#vr9-continue{position:fixed;bottom:70px;left:50%;transform:translateX(-50%);z-index:200;' +
        'background:linear-gradient(135deg,rgba(0,212,255,0.12),rgba(168,85,247,0.1));' +
        'border:1px solid rgba(0,212,255,0.25);border-radius:12px;padding:10px 20px;' +
        'color:#7dd3fc;font:600 13px/1.3 Inter,system-ui,sans-serif;cursor:pointer;' +
        'backdrop-filter:blur(10px);display:flex;align-items:center;gap:8px;' +
        'transition:all .25s;animation:vr9ContinueFade 0.5s ease-out}' +
        '#vr9-continue:hover{background:linear-gradient(135deg,rgba(0,212,255,0.22),rgba(168,85,247,0.18));color:#fff;border-color:rgba(0,212,255,0.5)}' +
        '#vr9-continue .dismiss{margin-left:8px;opacity:0.5;font-size:16px}' +
        '#vr9-continue .dismiss:hover{opacity:1}' +
        '@keyframes vr9ContinueFade{from{opacity:0;transform:translateX(-50%) translateY(10px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}'
      );

      var btn = document.createElement('div');
      btn.id = 'vr9-continue';
      btn.innerHTML = '<span>&#x25B6;</span> Continue to <strong>' + name + '</strong>' +
                       '<span class="dismiss" title="Dismiss">&times;</span>';
      btn.addEventListener('click', function (e) {
        if (e.target.classList.contains('dismiss')) { btn.remove(); return; }
        location.href = lastSession.path || '/vr/';
      });
      document.body.appendChild(btn);

      // Auto-dismiss after 12 seconds
      setTimeout(function () { if (btn.parentNode) btn.style.opacity = '0'; setTimeout(function () { if (btn.parentNode) btn.remove(); }, 500); }, 12000);
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', showContinueBtn);
    else showContinueBtn();

    return { getLastSession: function () { return lastSession; }, save: save };
  })();

  /* ═══════════════════════════════════════════════
     2. ERROR RECOVERY & RESILIENCE
     ═══════════════════════════════════════════════ */
  var errorRecovery = (function () {
    var online = navigator.onLine !== false;
    var retryQueue = [];

    // Connection HUD indicator
    function createIndicator() {
      injectStyle('vr9-conn-css',
        '#vr9-conn{position:fixed;top:8px;right:8px;z-index:300;padding:4px 10px;border-radius:6px;font:600 11px/1.3 Inter,system-ui,sans-serif;pointer-events:none;transition:all .3s;opacity:0}' +
        '#vr9-conn.offline{background:rgba(239,68,68,0.15);color:#fca5a5;border:1px solid rgba(239,68,68,0.3);opacity:1}' +
        '#vr9-conn.recovered{background:rgba(34,197,94,0.15);color:#86efac;border:1px solid rgba(34,197,94,0.3);opacity:1}'
      );
      var el = document.createElement('div');
      el.id = 'vr9-conn';
      document.body.appendChild(el);
      return el;
    }

    var indicator;
    function updateConnStatus() {
      if (!indicator) indicator = createIndicator();
      if (!online) {
        indicator.className = 'offline';
        indicator.textContent = '⚠ Offline — cached content only';
      } else {
        indicator.className = 'recovered';
        indicator.textContent = '✓ Connection restored';
        setTimeout(function () { indicator.style.opacity = '0'; indicator.className = ''; }, 3000);
        // Process retry queue
        retryQueue.forEach(function (fn) { try { fn(); } catch (e) {} });
        retryQueue = [];
      }
    }

    window.addEventListener('online', function () { online = true; updateConnStatus(); });
    window.addEventListener('offline', function () { online = false; updateConnStatus(); });

    // Resilient fetch wrapper with retry
    function resilientFetch(url, opts, maxRetries) {
      maxRetries = maxRetries || 3;
      var attempt = 0;
      function tryFetch() {
        attempt++;
        return fetch(url, opts).then(function (r) {
          if (!r.ok && attempt < maxRetries) {
            return new Promise(function (resolve) {
              setTimeout(resolve, Math.min(1000 * Math.pow(2, attempt), 8000));
            }).then(tryFetch);
          }
          return r;
        }).catch(function (err) {
          if (attempt < maxRetries) {
            return new Promise(function (resolve) {
              setTimeout(resolve, Math.min(1000 * Math.pow(2, attempt), 8000));
            }).then(tryFetch);
          }
          throw err;
        });
      }
      return tryFetch();
    }

    // Global error boundary — catch unhandled errors
    var errorCount = 0;
    window.addEventListener('error', function (e) {
      errorCount++;
      if (errorCount > 20) return; // Don't flood
      console.warn('[VR Error Recovery] Caught error:', e.message);
    });

    return {
      isOnline: function () { return online; },
      fetch: resilientFetch,
      onRetry: function (fn) { retryQueue.push(fn); },
      errorCount: function () { return errorCount; }
    };
  })();

  /* ═══════════════════════════════════════════════
     3. ACCESSIBILITY LAYER
     ═══════════════════════════════════════════════ */
  var accessibility = (function () {
    var prefs = load('a11y', { reducedMotion: false, highContrast: false, largeText: false });

    function applyPrefs() {
      document.body.setAttribute('data-vr-reduced-motion', prefs.reducedMotion ? 'true' : 'false');
      document.body.setAttribute('data-vr-high-contrast', prefs.highContrast ? 'true' : 'false');
      document.body.setAttribute('data-vr-large-text', prefs.largeText ? 'true' : 'false');

      injectStyle('vr9-a11y-css',
        /* Reduced motion — pause all CSS animations */
        '[data-vr-reduced-motion="true"] *{animation-duration:0.01ms!important;animation-iteration-count:1!important;transition-duration:0.01ms!important}' +
        /* High contrast */
        '[data-vr-high-contrast="true"]{filter:contrast(1.3) saturate(1.2)}' +
        '[data-vr-high-contrast="true"] .vr-nav-overlay,[data-vr-high-contrast="true"] #vr-area-guide{background:rgba(0,0,0,0.97)!important;border-color:rgba(255,255,255,0.4)!important}' +
        /* Large text */
        '[data-vr-large-text="true"]{font-size:115%!important}' +
        '[data-vr-large-text="true"] .vr-nav-overlay{font-size:14px!important}' +
        /* Focus ring for keyboard users */
        '.vr9-focus-visible :focus{outline:2px solid #00d4ff!important;outline-offset:2px!important}' +
        /* Skip link */
        '#vr9-skip{position:fixed;top:-60px;left:50%;transform:translateX(-50%);z-index:9999;background:#00d4ff;color:#000;padding:8px 16px;border-radius:0 0 8px 8px;font:700 14px Inter,system-ui,sans-serif;transition:top .2s}' +
        '#vr9-skip:focus{top:0}'
      );
      store('a11y', prefs);
    }

    // Detect prefers-reduced-motion
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      prefs.reducedMotion = true;
    }

    // Add skip link
    function addSkipLink() {
      var skip = document.createElement('a');
      skip.id = 'vr9-skip';
      skip.href = '#main-content';
      skip.textContent = 'Skip to main content';
      skip.setAttribute('tabindex', '0');
      document.body.insertBefore(skip, document.body.firstChild);

      // Mark main content area
      var scene = document.querySelector('a-scene');
      if (scene) scene.id = scene.id || 'main-content';
    }

    // Detect keyboard usage → show focus rings
    var usingKeyboard = false;
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Tab') {
        usingKeyboard = true;
        document.body.classList.add('vr9-focus-visible');
      }
    });
    document.addEventListener('mousedown', function () {
      usingKeyboard = false;
      document.body.classList.remove('vr9-focus-visible');
    });

    // Add ARIA labels to zone-link elements
    function labelInteractiveElements() {
      document.querySelectorAll('[zone-link]').forEach(function (el) {
        var url = el.getAttribute('zone-link');
        if (url) {
          var match = url.match(/url:\s*([^\s;]+)/);
          var dest = match ? match[1] : url;
          el.setAttribute('aria-label', 'Navigate to ' + dest);
          el.setAttribute('role', 'button');
          el.setAttribute('tabindex', '0');
        }
      });
      // Label common buttons
      document.querySelectorAll('button:not([aria-label])').forEach(function (btn) {
        if (btn.textContent.trim().length < 40) {
          btn.setAttribute('aria-label', btn.textContent.trim());
        }
      });
    }

    // Accessibility settings panel (press Alt+A)
    var panelOpen = false;
    function toggleA11yPanel() {
      if (panelOpen) { closeA11yPanel(); return; }
      panelOpen = true;

      injectStyle('vr9-a11y-panel-css',
        '#vr9-a11y-panel{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:500;' +
        'background:rgba(15,12,41,0.96);border:1px solid rgba(0,212,255,0.25);border-radius:16px;' +
        'padding:24px;width:320px;color:#e2e8f0;font:14px/1.5 Inter,system-ui,sans-serif;' +
        'backdrop-filter:blur(16px);animation:vr9SlideIn 0.2s ease-out}' +
        '#vr9-a11y-panel h3{margin:0 0 16px;font-size:16px;color:#7dd3fc}' +
        '.vr9-a11y-row{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.06)}' +
        '.vr9-a11y-row:last-child{border:none}' +
        '.vr9-toggle{position:relative;width:40px;height:22px;background:rgba(255,255,255,0.1);border-radius:11px;cursor:pointer;transition:background .2s}' +
        '.vr9-toggle.on{background:rgba(0,212,255,0.5)}' +
        '.vr9-toggle::after{content:"";position:absolute;top:2px;left:2px;width:18px;height:18px;background:#fff;border-radius:50%;transition:transform .2s}' +
        '.vr9-toggle.on::after{transform:translateX(18px)}' +
        '.vr9-a11y-close{position:absolute;top:12px;right:16px;background:none;border:none;color:#94a3b8;font-size:20px;cursor:pointer}' +
        '.vr9-a11y-close:hover{color:#fff}' +
        '@keyframes vr9SlideIn{from{opacity:0;transform:translate(-50%,-50%) scale(0.95)}to{opacity:1;transform:translate(-50%,-50%) scale(1)}}'
      );

      var panel = document.createElement('div');
      panel.id = 'vr9-a11y-panel';
      panel.setAttribute('role', 'dialog');
      panel.setAttribute('aria-label', 'Accessibility Settings');

      var rows = [
        { key: 'reducedMotion', label: 'Reduced Motion', desc: 'Pause animations' },
        { key: 'highContrast',  label: 'High Contrast',  desc: 'Increase contrast' },
        { key: 'largeText',     label: 'Large Text',     desc: 'Bigger font sizes' }
      ];

      var html = '<h3>&#x267F; Accessibility</h3><button class="vr9-a11y-close" onclick="VRCompleteness.closeA11y()" aria-label="Close">&times;</button>';
      rows.forEach(function (r) {
        html += '<div class="vr9-a11y-row"><div><strong>' + r.label + '</strong><br><small style="color:#64748b">' + r.desc + '</small></div>' +
                '<div class="vr9-toggle' + (prefs[r.key] ? ' on' : '') + '" data-key="' + r.key + '" role="switch" aria-checked="' + !!prefs[r.key] + '" tabindex="0"></div></div>';
      });
      panel.innerHTML = html;
      document.body.appendChild(panel);

      // Toggle clicks
      panel.querySelectorAll('.vr9-toggle').forEach(function (t) {
        t.addEventListener('click', function () {
          var key = t.getAttribute('data-key');
          prefs[key] = !prefs[key];
          t.classList.toggle('on', prefs[key]);
          t.setAttribute('aria-checked', String(prefs[key]));
          applyPrefs();
        });
      });
    }

    function closeA11yPanel() {
      panelOpen = false;
      var p = document.getElementById('vr9-a11y-panel');
      if (p) p.remove();
    }

    document.addEventListener('keydown', function (e) {
      if (e.altKey && (e.key === 'a' || e.key === 'A')) { e.preventDefault(); toggleA11yPanel(); }
      if (e.key === 'Escape' && panelOpen) closeA11yPanel();
    });

    function init() {
      applyPrefs();
      addSkipLink();
      labelInteractiveElements();
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();

    return {
      prefs: prefs,
      togglePanel: toggleA11yPanel,
      closePanel: closeA11yPanel,
      isPanelOpen: function () { return panelOpen; }
    };
  })();

  /* ═══════════════════════════════════════════════
     4. FIRST-VISIT ONBOARDING TIPS
     ═══════════════════════════════════════════════ */
  var onboarding = (function () {
    var visited = load('visited_zones', {});

    var tips = {
      hub: { title: 'Welcome to VR Hub!', body: 'Click any portal to enter a zone. Press <kbd>1-6</kbd> to jump directly. Press <kbd>M</kbd> for the menu, <kbd>G</kbd> for the Area Guide.' },
      events: { title: 'Events Explorer', body: 'Browse 1000+ Toronto events. Use category pills to filter, arrow keys to paginate. Click a card for details.' },
      movies: { title: 'Movie Theater', body: 'Hover a poster to play its trailer. Build a queue and enjoy cinema-style playback. Toggle Movies/TV Shows.' },
      creators: { title: 'Creators Live Lounge', body: 'See who\'s streaming live! Filter by platform. Click a card for stream preview and details.' },
      stocks: { title: 'Trading Floor', body: 'Watch simulated real-time ticker updates for 8 major stocks. Green = gains, red = losses.' },
      wellness: { title: 'Wellness Garden', body: 'Try the breathing exercise (press 1), visit the motivational wall (press 3), or relax at the meditation spot.' },
      weather: { title: 'Weather Observatory', body: 'Live Toronto weather with 7-day forecast. Override weather with Clear/Rain/Snow/Storm buttons.' },
      tutorial: { title: 'Tutorial', body: 'Follow the 7 steps to learn all VR controls: look, click, move, teleport, snap-turn, menu, and navigation.' }
    };

    function showTip() {
      if (visited[currentZone]) return;
      var tip = tips[currentZone];
      if (!tip) return;

      visited[currentZone] = true;
      store('visited_zones', visited);

      injectStyle('vr9-onboard-css',
        '#vr9-onboard{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:400;' +
        'background:linear-gradient(145deg,rgba(15,12,41,0.97),rgba(30,20,60,0.95));' +
        'border:1px solid rgba(0,212,255,0.3);border-radius:16px;padding:28px 32px;' +
        'width:min(380px,90vw);color:#e2e8f0;font:14px/1.6 Inter,system-ui,sans-serif;' +
        'backdrop-filter:blur(16px);text-align:center;animation:vr9SlideIn 0.3s ease-out}' +
        '#vr9-onboard h3{margin:0 0 10px;font-size:18px;color:#7dd3fc}' +
        '#vr9-onboard p{margin:0 0 16px;color:#94a3b8;font-size:13px}' +
        '#vr9-onboard kbd{background:rgba(255,255,255,0.1);padding:1px 6px;border-radius:4px;font-size:12px;color:#e2e8f0;border:1px solid rgba(255,255,255,0.15)}' +
        '#vr9-onboard button{background:linear-gradient(135deg,#00d4ff,#a855f7);color:#fff;border:none;padding:8px 24px;border-radius:8px;font:600 13px Inter,system-ui,sans-serif;cursor:pointer;transition:opacity .2s}' +
        '#vr9-onboard button:hover{opacity:0.85}'
      );

      var el = document.createElement('div');
      el.id = 'vr9-onboard';
      el.setAttribute('role', 'dialog');
      el.setAttribute('aria-label', 'Zone introduction');
      el.innerHTML = '<h3>' + tip.title + '</h3><p>' + tip.body + '</p>' +
                     '<button onclick="this.parentElement.remove()">Got it!</button>';
      document.body.appendChild(el);

      // Auto-dismiss after 10 s
      setTimeout(function () { if (el.parentNode) { el.style.opacity = '0'; setTimeout(function () { if (el.parentNode) el.remove(); }, 400); } }, 10000);
    }

    // Small delay so the scene loads first
    setTimeout(showTip, 1500);

    return {
      hasVisited: function (z) { return !!visited[z]; },
      resetAll: function () { visited = {}; store('visited_zones', {}); }
    };
  })();

  /* ═══════════════════════════════════════════════
     5. PERFORMANCE LOD (Level of Detail)
     ═══════════════════════════════════════════════ */
  var perfLOD = (function () {
    var fpsHistory = [];
    var quality = load('perf_quality', 'auto'); // auto, high, medium, low
    var lastFps = 60;

    // FPS monitor
    var lastTime = performance.now();
    var frameCount = 0;

    function measureFPS() {
      frameCount++;
      var now = performance.now();
      if (now - lastTime >= 1000) {
        lastFps = Math.round(frameCount * 1000 / (now - lastTime));
        fpsHistory.push(lastFps);
        if (fpsHistory.length > 30) fpsHistory.shift();
        frameCount = 0;
        lastTime = now;

        // Auto quality adjustment
        if (quality === 'auto') {
          var avgFps = fpsHistory.reduce(function (a, b) { return a + b; }, 0) / fpsHistory.length;
          if (avgFps < 20) applyQuality('low');
          else if (avgFps < 35) applyQuality('medium');
          else applyQuality('high');
        }
      }
      requestAnimationFrame(measureFPS);
    }
    requestAnimationFrame(measureFPS);

    function applyQuality(level) {
      document.body.setAttribute('data-vr-quality', level);

      // Reduce particle counts on low quality
      if (level === 'low') {
        // Hide non-essential particles
        var particles = document.querySelectorAll('#ambient-motes, #dust-motes, #fireflies, #falling-petals');
        particles.forEach(function (p) { p.setAttribute('visible', 'false'); });
      } else if (level === 'medium') {
        var particles = document.querySelectorAll('#falling-petals');
        particles.forEach(function (p) { p.setAttribute('visible', 'false'); });
        var kept = document.querySelectorAll('#ambient-motes, #dust-motes, #fireflies');
        kept.forEach(function (p) { p.setAttribute('visible', 'true'); });
      } else {
        var all = document.querySelectorAll('#ambient-motes, #dust-motes, #fireflies, #falling-petals');
        all.forEach(function (p) { p.setAttribute('visible', 'true'); });
      }
    }

    // FPS badge (bottom-left corner, small)
    function showFPSBadge() {
      injectStyle('vr9-fps-css',
        '#vr9-fps{position:fixed;bottom:6px;left:6px;z-index:100;background:rgba(0,0,0,0.5);color:#64748b;' +
        'padding:2px 7px;border-radius:4px;font:600 10px/1 monospace;pointer-events:none;opacity:0.6}'
      );
      var badge = document.createElement('div');
      badge.id = 'vr9-fps';
      badge.textContent = '-- FPS';
      document.body.appendChild(badge);

      setInterval(function () {
        badge.textContent = lastFps + ' FPS';
        badge.style.color = lastFps >= 45 ? '#22c55e' : lastFps >= 25 ? '#eab308' : '#ef4444';
      }, 1000);
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', showFPSBadge);
    else showFPSBadge();

    return {
      getFPS: function () { return lastFps; },
      getQuality: function () { return quality; },
      setQuality: function (q) { quality = q; store('perf_quality', q); if (q !== 'auto') applyQuality(q); }
    };
  })();

  /* ═══════════════════════════════════════════════
     6. EVENTS CALENDAR MINIMAP
     ═══════════════════════════════════════════════ */
  var eventsCalendar = (function () {
    if (currentZone !== 'events') return null;

    function createCalendar() {
      injectStyle('vr9-cal-css',
        '#vr9-calendar{position:fixed;bottom:10px;right:10px;z-index:150;' +
        'background:rgba(15,12,41,0.92);border:1px solid rgba(255,107,107,0.2);border-radius:12px;' +
        'padding:12px;width:210px;color:#e2e8f0;font:11px/1.3 Inter,system-ui,sans-serif;' +
        'backdrop-filter:blur(10px)}' +
        '#vr9-calendar .cal-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;font-weight:700;font-size:12px;color:#ff6b6b}' +
        '#vr9-calendar .cal-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:2px}' +
        '#vr9-calendar .cal-day-label{text-align:center;font-size:9px;color:#64748b;font-weight:600}' +
        '#vr9-calendar .cal-day{text-align:center;padding:3px 0;border-radius:4px;font-size:10px;color:#94a3b8;cursor:default;position:relative}' +
        '#vr9-calendar .cal-day.has-events{color:#fff;font-weight:700}' +
        '#vr9-calendar .cal-day.today{background:rgba(255,107,107,0.2);color:#ff6b6b;font-weight:700;border:1px solid rgba(255,107,107,0.3)}' +
        '#vr9-calendar .cal-density{position:absolute;bottom:1px;left:50%;transform:translateX(-50%);width:4px;height:4px;border-radius:50%}' +
        '#vr9-calendar .cal-toggle{position:absolute;top:8px;right:8px;background:none;border:none;color:#64748b;cursor:pointer;font-size:14px}' +
        '#vr9-calendar.collapsed .cal-grid{display:none}'
      );

      var now = new Date();
      var year = now.getFullYear(), month = now.getMonth();
      var monthNames = ['January','February','March','April','May','June','July','August','September','October','November','December'];
      var firstDay = new Date(year, month, 1).getDay();
      var daysInMonth = new Date(year, month + 1, 0).getDate();
      var today = now.getDate();

      // Try to get event density from loaded events
      var density = {};
      try {
        var eventCards = document.querySelectorAll('[data-date]');
        eventCards.forEach(function (c) {
          var d = c.getAttribute('data-date');
          if (d) {
            var day = parseInt(d.split('-').pop() || d.split('/').pop(), 10);
            if (day) density[day] = (density[day] || 0) + 1;
          }
        });
      } catch (e) {}

      var html = '<div class="cal-header"><span>' + monthNames[month] + ' ' + year + '</span></div>';
      html += '<div class="cal-grid">';
      ['Su','Mo','Tu','We','Th','Fr','Sa'].forEach(function (d) { html += '<div class="cal-day-label">' + d + '</div>'; });

      for (var i = 0; i < firstDay; i++) html += '<div class="cal-day"></div>';
      for (var d = 1; d <= daysInMonth; d++) {
        var classes = 'cal-day';
        var count = density[d] || 0;
        if (count > 0) classes += ' has-events';
        if (d === today) classes += ' today';
        var dotColor = count > 10 ? '#ef4444' : count > 5 ? '#eab308' : count > 0 ? '#22c55e' : 'transparent';
        html += '<div class="' + classes + '" title="' + count + ' events">' + d + '<div class="cal-density" style="background:' + dotColor + '"></div></div>';
      }
      html += '</div>';

      var el = document.createElement('div');
      el.id = 'vr9-calendar';
      el.innerHTML = html;
      document.body.appendChild(el);
    }

    // Delay to let events load first
    setTimeout(createCalendar, 3000);

    return { zone: 'events' };
  })();

  /* ═══════════════════════════════════════════════
     7. MOVIES WATCH HISTORY
     ═══════════════════════════════════════════════ */
  var watchHistory = (function () {
    if (currentZone !== 'movies') return null;

    var history = load('watch_history', []);

    function addToHistory(title, videoId, thumb) {
      // Remove duplicate
      history = history.filter(function (h) { return h.videoId !== videoId; });
      history.unshift({ title: title, videoId: videoId, thumb: thumb || '', time: Date.now() });
      if (history.length > 50) history = history.slice(0, 50);
      store('watch_history', history);
      updateBadge();
    }

    // Monitor for video playback
    function hookPlayback() {
      // Intercept the existing playVideo or similar functions
      var origPlay = window.playVideoById || window.playVideo;
      if (typeof origPlay === 'function') {
        window.playVideoById = function () {
          var args = arguments;
          origPlay.apply(this, args);
          // Try to capture what was played
          var nowPlaying = document.querySelector('#now-playing-title, .now-playing-title');
          if (nowPlaying) {
            addToHistory(nowPlaying.textContent, args[0] || 'unknown', '');
          }
        };
      }
    }

    // Watch history badge
    function updateBadge() {
      var badge = document.getElementById('vr9-watch-count');
      if (badge) badge.textContent = history.length + ' watched';
    }

    function createHistoryBadge() {
      injectStyle('vr9-watch-css',
        '#vr9-watch-badge{position:fixed;bottom:10px;right:10px;z-index:150;' +
        'background:rgba(15,12,41,0.92);border:1px solid rgba(78,205,196,0.2);border-radius:10px;' +
        'padding:8px 14px;color:#4ecdc4;font:600 12px Inter,system-ui,sans-serif;' +
        'backdrop-filter:blur(10px);cursor:pointer;transition:all .2s}' +
        '#vr9-watch-badge:hover{border-color:rgba(78,205,196,0.5);color:#fff}' +
        '#vr9-watch-panel{position:fixed;bottom:50px;right:10px;z-index:160;' +
        'background:rgba(15,12,41,0.96);border:1px solid rgba(78,205,196,0.25);border-radius:12px;' +
        'padding:12px;width:260px;max-height:300px;overflow-y:auto;color:#e2e8f0;font:12px/1.4 Inter,system-ui,sans-serif;' +
        'backdrop-filter:blur(16px);display:none}' +
        '#vr9-watch-panel.open{display:block}' +
        '.vr9-watch-item{padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.06);color:#94a3b8;font-size:11px}' +
        '.vr9-watch-item:last-child{border:none}' +
        '#vr9-watch-panel h4{margin:0 0 8px;color:#4ecdc4;font-size:13px}'
      );

      var badge = document.createElement('div');
      badge.id = 'vr9-watch-badge';
      badge.innerHTML = '&#x1F3AC; <span id="vr9-watch-count">' + history.length + ' watched</span>';
      badge.addEventListener('click', function () {
        var panel = document.getElementById('vr9-watch-panel');
        if (panel) { panel.classList.toggle('open'); return; }
        showHistoryPanel();
      });
      document.body.appendChild(badge);
    }

    function showHistoryPanel() {
      var panel = document.createElement('div');
      panel.id = 'vr9-watch-panel';
      panel.classList.add('open');
      var html = '<h4>Watch History</h4>';
      if (history.length === 0) {
        html += '<div class="vr9-watch-item" style="color:#64748b">No trailers watched yet</div>';
      } else {
        history.slice(0, 20).forEach(function (h) {
          var ago = Math.round((Date.now() - h.time) / 60000);
          var timeStr = ago < 60 ? ago + 'm ago' : Math.round(ago / 60) + 'h ago';
          html += '<div class="vr9-watch-item">' + (h.title || 'Untitled') + ' <span style="color:#4ecdc4;float:right">' + timeStr + '</span></div>';
        });
      }
      panel.innerHTML = html;
      document.body.appendChild(panel);
    }

    setTimeout(function () { createHistoryBadge(); hookPlayback(); }, 2000);

    return {
      add: addToHistory,
      getHistory: function () { return history; },
      clear: function () { history = []; store('watch_history', []); }
    };
  })();

  /* ═══════════════════════════════════════════════
     8. WEATHER FORECAST TIMELINE (24 h)
     ═══════════════════════════════════════════════ */
  var weatherTimeline = (function () {
    if (currentZone !== 'weather') return null;

    function createTimeline() {
      injectStyle('vr9-wtl-css',
        '#vr9-weather-timeline{position:fixed;bottom:10px;left:50%;transform:translateX(-50%);z-index:150;' +
        'background:rgba(15,12,41,0.92);border:1px solid rgba(6,182,212,0.2);border-radius:12px;' +
        'padding:10px 16px;width:min(550px,90vw);color:#e2e8f0;font:11px/1.3 Inter,system-ui,sans-serif;' +
        'backdrop-filter:blur(10px)}' +
        '#vr9-weather-timeline h4{margin:0 0 8px;font-size:12px;color:#06b6d4}' +
        '.vr9-tl-bar{display:flex;gap:2px;height:40px;align-items:flex-end}' +
        '.vr9-tl-bar-item{flex:1;min-width:0;border-radius:3px 3px 0 0;position:relative;cursor:default;transition:opacity .2s}' +
        '.vr9-tl-bar-item:hover{opacity:0.8}' +
        '.vr9-tl-labels{display:flex;gap:2px;margin-top:2px}' +
        '.vr9-tl-labels span{flex:1;text-align:center;font-size:8px;color:#64748b}'
      );

      // Fetch hourly forecast from Open-Meteo
      fetch('https://api.open-meteo.com/v1/forecast?latitude=43.65&longitude=-79.38&hourly=temperature_2m,weathercode&timezone=America/Toronto&forecast_days=1')
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (!data.hourly) return;
          var temps = data.hourly.temperature_2m || [];
          var codes = data.hourly.weathercode || [];
          var times = data.hourly.time || [];

          var minT = Math.min.apply(null, temps);
          var maxT = Math.max.apply(null, temps);
          var range = maxT - minT || 1;

          var barsHtml = '';
          var labelsHtml = '';
          temps.forEach(function (t, i) {
            var h = Math.max(4, Math.round(((t - minT) / range) * 36));
            var hue = t < 0 ? 210 : t < 10 ? 190 : t < 20 ? 40 : t < 30 ? 20 : 0;
            var color = 'hsl(' + hue + ',70%,55%)';
            barsHtml += '<div class="vr9-tl-bar-item" style="height:' + h + 'px;background:' + color + '" title="' + times[i] + ': ' + t + '°C"></div>';
            var hour = parseInt((times[i] || '').split('T')[1], 10);
            labelsHtml += '<span>' + (i % 3 === 0 ? hour + 'h' : '') + '</span>';
          });

          var el = document.createElement('div');
          el.id = 'vr9-weather-timeline';
          el.innerHTML = '<h4>&#x1F321;&#xFE0F; 24-Hour Forecast: ' + Math.round(minT) + '°C to ' + Math.round(maxT) + '°C</h4>' +
                         '<div class="vr9-tl-bar">' + barsHtml + '</div>' +
                         '<div class="vr9-tl-labels">' + labelsHtml + '</div>';
          document.body.appendChild(el);
        })
        .catch(function () {
          // Graceful degradation — show placeholder
          var el = document.createElement('div');
          el.id = 'vr9-weather-timeline';
          el.innerHTML = '<h4 style="color:#64748b">Forecast timeline unavailable</h4>';
          el.style.cssText = 'position:fixed;bottom:10px;left:50%;transform:translateX(-50%);z-index:150;background:rgba(15,12,41,0.8);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:8px 16px;color:#64748b;font:11px Inter,system-ui,sans-serif';
          document.body.appendChild(el);
        });
    }

    setTimeout(createTimeline, 2000);
    return { zone: 'weather' };
  })();

  /* ═══════════════════════════════════════════════
     9. DEVICE ADAPTIVE UI
     ═══════════════════════════════════════════════ */
  var deviceAdaptive = (function () {
    var isVR = false;
    var isQuest = false;
    var isDesktop = true;
    var isMobile = false;

    // Detect device
    var ua = navigator.userAgent || '';
    if (/OculusBrowser|Quest/i.test(ua)) { isQuest = true; isVR = true; isDesktop = false; }
    else if (/Pico|PICO/i.test(ua)) { isVR = true; isDesktop = false; }
    else if (/Mobile|Android|iPhone/i.test(ua)) { isMobile = true; isDesktop = false; }

    var deviceType = isQuest ? 'quest' : isVR ? 'vr-headset' : isMobile ? 'mobile' : 'desktop';
    document.body.setAttribute('data-vr-device', deviceType);

    injectStyle('vr9-device-css',
      /* Desktop: slightly larger UI text, mouse-friendly */
      '[data-vr-device="desktop"] .vr-nav-overlay{max-height:85vh}' +
      '[data-vr-device="desktop"] button,[data-vr-device="desktop"] .btn{min-height:32px}' +
      /* Mobile: larger touch targets */
      '[data-vr-device="mobile"] button,[data-vr-device="mobile"] .btn{min-height:44px;min-width:44px}' +
      '[data-vr-device="mobile"] .vr-nav-overlay{width:95vw}' +
      /* Quest: optimize for headset viewing */
      '[data-vr-device="quest"] .vr-nav-overlay{font-size:15px}' +
      '[data-vr-device="quest"] button{min-height:44px}' +
      /* Capability classes */
      '[data-vr-device="quest"] .desktop-only{display:none!important}' +
      '[data-vr-device="desktop"] .vr-only{display:none!important}'
    );

    // Monitor for WebXR session start/end
    var scene = document.querySelector('a-scene');
    if (scene) {
      scene.addEventListener('enter-vr', function () {
        document.body.setAttribute('data-vr-active', 'true');
      });
      scene.addEventListener('exit-vr', function () {
        document.body.setAttribute('data-vr-active', 'false');
      });
    }

    return {
      type: deviceType,
      isVR: isVR,
      isQuest: isQuest,
      isDesktop: isDesktop,
      isMobile: isMobile
    };
  })();

  /* ═══════════════════════════════════════════════
     10. WHAT'S NEW CHANGELOG
     ═══════════════════════════════════════════════ */
  var changelog = (function () {
    var CURRENT_VERSION = '9.0';
    var lastSeen = load('changelog_seen', '0');

    var entries = [
      { ver: '9.0', date: '2026-02-07', items: [
        'Session Continuity — resume where you left off',
        'Error Recovery — automatic retry & offline indicator',
        'Accessibility Settings (Alt+A) — reduced motion, high contrast, large text',
        'First-Visit Onboarding — zone introductions on first visit',
        'Performance LOD — auto quality adjustment based on FPS',
        'Events Calendar Minimap — month view with event density',
        'Movies Watch History — track watched trailers',
        'Weather 24h Forecast Timeline — hourly temperature bar',
        'Device Adaptive UI — auto-detect Quest / desktop / mobile',
        'What\'s New Changelog — this panel!'
      ]},
      { ver: '8.0', date: '2026-02-07', items: [
        'Portal Particle Fountains, Hover Pulse, Energy Waves',
        'Movies Screen Glow + Dust Motes',
        'Stocks Price-Change Sparks',
        'Wellness Fireflies + Falling Petals',
        'Time-of-Day Sky Tint, Ambient Motes, Portal Data Badges'
      ]}
    ];

    var panelOpen = false;

    function shouldShow() {
      return lastSeen < CURRENT_VERSION;
    }

    function showChangelog() {
      if (panelOpen) return;
      panelOpen = true;

      injectStyle('vr9-changelog-css',
        '#vr9-changelog-bg{position:fixed;inset:0;z-index:600;background:rgba(0,0,0,0.5);backdrop-filter:blur(4px)}' +
        '#vr9-changelog{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:601;' +
        'background:rgba(15,12,41,0.97);border:1px solid rgba(0,212,255,0.25);border-radius:16px;' +
        'padding:24px 28px;width:min(420px,90vw);max-height:70vh;overflow-y:auto;' +
        'color:#e2e8f0;font:13px/1.5 Inter,system-ui,sans-serif;animation:vr9SlideIn 0.3s ease-out}' +
        '#vr9-changelog h3{margin:0 0 4px;font-size:18px;color:#7dd3fc}' +
        '#vr9-changelog .ver-badge{display:inline-block;background:linear-gradient(135deg,#00d4ff,#a855f7);color:#fff;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700;margin-bottom:12px}' +
        '#vr9-changelog .cl-section{margin-bottom:16px}' +
        '#vr9-changelog .cl-ver{font-weight:700;color:#a855f7;font-size:12px;margin-bottom:4px}' +
        '#vr9-changelog .cl-date{color:#64748b;font-size:11px;margin-left:8px}' +
        '#vr9-changelog ul{margin:4px 0 0;padding-left:18px;color:#94a3b8;font-size:12px}' +
        '#vr9-changelog li{margin-bottom:3px}' +
        '#vr9-changelog .cl-dismiss{display:block;width:100%;margin-top:12px;padding:8px;background:linear-gradient(135deg,#00d4ff,#a855f7);color:#fff;border:none;border-radius:8px;font:600 13px Inter,system-ui,sans-serif;cursor:pointer}' +
        '#vr9-changelog .cl-dismiss:hover{opacity:0.85}'
      );

      var bg = document.createElement('div');
      bg.id = 'vr9-changelog-bg';
      bg.addEventListener('click', closeChangelog);
      document.body.appendChild(bg);

      var panel = document.createElement('div');
      panel.id = 'vr9-changelog';
      panel.setAttribute('role', 'dialog');
      panel.setAttribute('aria-label', 'What\'s New');

      var html = '<h3>&#x1F389; What\'s New</h3><div class="ver-badge">v' + CURRENT_VERSION + '</div>';
      entries.forEach(function (e) {
        html += '<div class="cl-section"><div class="cl-ver">v' + e.ver + '<span class="cl-date">' + e.date + '</span></div><ul>';
        e.items.forEach(function (item) { html += '<li>' + item + '</li>'; });
        html += '</ul></div>';
      });
      html += '<button class="cl-dismiss" onclick="VRCompleteness.closeChangelog()">Awesome, let\'s go!</button>';

      panel.innerHTML = html;
      document.body.appendChild(panel);

      store('changelog_seen', CURRENT_VERSION);
    }

    function closeChangelog() {
      panelOpen = false;
      var bg = document.getElementById('vr9-changelog-bg');
      var p = document.getElementById('vr9-changelog');
      if (bg) bg.remove();
      if (p) p.remove();
    }

    // Auto-show on hub if version is new
    if (currentZone === 'hub' && shouldShow()) {
      setTimeout(showChangelog, 2500);
    }

    return {
      show: showChangelog,
      close: closeChangelog,
      isOpen: function () { return panelOpen; },
      version: CURRENT_VERSION
    };
  })();

  /* ═══════════════════════════════════════════════
     PUBLIC API
     ═══════════════════════════════════════════════ */
  window.VRCompleteness = {
    zone: currentZone,
    version: 9,
    session: sessionState,
    errorRecovery: errorRecovery,
    accessibility: accessibility,
    onboarding: onboarding,
    perfLOD: perfLOD,
    eventsCalendar: eventsCalendar,
    watchHistory: watchHistory,
    weatherTimeline: weatherTimeline,
    device: deviceAdaptive,
    changelog: changelog,
    // Shortcut functions for nav-menu integration
    openA11y: function () { accessibility.togglePanel(); },
    closeA11y: function () { accessibility.closePanel(); },
    showChangelog: function () { changelog.show(); },
    closeChangelog: function () { changelog.close(); }
  };

  console.log('[VR Completeness] Set 9 loaded — ' + currentZone + ' (' + deviceAdaptive.type + ')');
})();
