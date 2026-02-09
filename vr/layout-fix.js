/**
 * VR Layout Fix — Resolves overlapping fixed-position UI widgets
 *
 * Problem: 25+ scripts each inject fixed-position panels at the same locations
 * (top:50px right:10px, bottom:50px right:10px, bottom:10px left:10px, etc.),
 * causing massive visual overlap on every VR page.
 *
 * Solution:
 *   1. CSS overrides with high specificity to hide non-essential widgets
 *   2. JavaScript enforcement to catch widgets created via setTimeout
 *   3. MutationObserver to handle dynamically injected elements
 *   4. Dark body background to prevent white flash
 *   5. Drawer toggle to optionally show hidden widgets
 *   6. Protect A-Frame WebXR "Enter VR" button from being covered
 *
 * Runs AFTER all quick-wins scripts (loaded at bottom of <body>).
 */
(function () {
  'use strict';

  /* ── Elements to forcefully hide (IDs) ── */
  var HIDDEN_IDS = [
    'vr15-pomo',              // Pomodoro timer
    'vr17-feed',              // Activity feed
    'vr17-habits',            // Daily habits
    'vr13-recs',              // "You might like" recommendations
    'vr-grab-indicator',      // Grab indicator (desktop not useful)
    'vr-quality-indicator',   // Quality: low/high indicator
    'vr-presence-indicator',  // "1 user(s) in zone" (from set2)
    'vr-presence-badge',      // Presence badge (from presence.js)
    'vr16-stock-news',        // Stock news
    'vr12-minimap',           // Minimap
    'vr12-photo-btn',         // Photo button
    'vr13-particles',         // Particle density slider
    'vr17-ratings',           // Ratings
    'vr10-theater-btn',       // Theater button
    'vr10-rate-badge',        // Rate badge
    'vr9-calendar',           // Calendar
    'vr9-watch-badge',        // Watch badge
    'vr-snapturn-toggle',     // Snap turn toggle
    'vr-stats-btn',           // Stats button
    'vr-minimap-toggle',      // Minimap toggle
    'vr-weather-btn',         // Weather effects button
    'vr-voice-toggle',        // Voice chat toggle
    'vr-voicechat-btn',       // Voice chat button
    'vr-voice-indicator',     // Voice indicator
    'vr-pwa-install-btn',     // PWA install
    'vr11-pin-badge',         // Pinboard badge
    'vr11-pin-panel',         // Pinboard panel
    'vr-session-time-display',// Session time (old ID)
    'vr-session-timer',       // Session timer (actual ID from quick-wins-substantial)
    'vr-pomodoro-indicator',  // Pomodoro small indicator
    'vr16-outfit',            // Outfit suggestion
    'vr16-world-map',         // World map
    'vr14-scratch',           // Scratchpad
    'vr14-breathe',           // Breathing exercise
    'vr10-med',               // Meditation widget
    'vr10-stats',             // Stats widget
    'vr9-weather-timeline',   // Weather timeline
    'vr-emergency-exit',      // Exit VR button (only needed in VR headset)
    'vr9-fps',                // FPS counter
    'vr-input-indicator',     // Input indicator (keyboard/mouse)
    'vr-quick-settings-btn',  // Settings gear button (Ctrl+, available)
    'vr-quick-settings',      // Settings panel
    'vr12-countdown',         // Countdown timer
    'vr12-autoplay',          // Autoplay widget
    'vr12-spotlight',         // Spotlight widget
    'vr12-voice',             // Voice indicator
    'vr12-analytics',         // Analytics panel
    'vr-boundary-indicator',  // Boundary indicator
    'vr-tutorial-overlay',    // Tutorial overlay
    'vr9-onboard',            // Onboarding tips
    'vr-time-indicator',      // "Afternoon" / time-of-day label
    'vr14-genres',            // Genres panel (movies page)
    'vr-world-clock',         // World clock widget
    'vr-world-clock-btn',     // World clock button

    // Set 11 buttons
    'vr-notifications-center-btn',
    'vr-voice-nav-btn',
    'vr-lod-btn',
    'vr-shortcuts-overlay-btn',
    'vr-autowalk-btn',
    'vr-shadowplay-btn',
    'vr-haptic-designer-btn',
    'vr-spatial-bookmarks-btn',
    'vr-taskmanager-btn',
    'vr-reading-btn',

    // Set 12 buttons & panels (clipboard overlaps AI robot icon)
    'vr-clipboard-btn',
    'vr-clipboard-panel',
    'vr-gestures-btn',
    'vr-gestures-panel',
    'vr-audio-viz-btn',
    'vr-audio-canvas',
    'vr-magnifier-btn',
    'vr-magnifier-lens',
    'vr-inventory-btn',
    'vr-inventory-panel',
    'vr-search-btn',
    'vr-search-overlay',
    'vr-calc-btn',
    'vr-calc-panel',
    'vr-colorpicker-btn',
    'vr-profiler-btn',
    'vr-profiler-panel',
    'vr-notes-btn',

    // Set 13 widgets
    'vr-virtual-pet',
    'vr-weather-widget',

    // Set 14 buttons
    'vr-timemachine-btn',
    'vr-timemachine-panel',
    'vr-gesturedraw-btn',
    'vr-gesture-canvas',
    'vr-voiceavatar-btn',
    'vr-voice-viz',
    'vr-hapticmed-btn',
    'vr-photosphere-btn',
    'vr-photosphere-viewer',
    'vr-keyboard-btn',
    'vr-shadowpuppet-btn',
    'vr-ambient-btn',
    'vr-ambient-panel',
    'vr-fireworks-btn',
    'vr-proximity-indicator',

    // Set 15 buttons
    'vr-sequencer-btn',
    'vr-sequencer-panel',
    'vr-handcalib-btn',
    'vr-calib-panel',
    'vr-mirror-btn',
    'vr-haptic-type-btn',
    'vr-photoframe-btn',
    'vr-voicememo-btn',
    'vr-socialdist-btn',
    'vr-sketch-btn',
    'vr-sketch-pad',
    'vr-lightsaber-btn',
    'vr-celebrate-btn',

    // Set 16 buttons
    'vr-spawner-btn',
    'vr-spawner-panel',
    'vr-gesture-shortcuts-btn',
    'vr-pomodoro-btn',
    'vr-pomodoro-panel',
    'vr-bookmarks-v2-btn',
    'vr-bookmarks-v2-panel',
    'vr-heartbeat-btn',
    'vr-dice-btn',
    'vr-nightvision-btn',
    'vr-volume-indicator',
    'vr-coin-btn',
    'vr-immersive-clock'
  ];

  /* ── Elements to forcefully hide (CSS classes) ── */
  var HIDDEN_CLASSES = [
    'vr13-lang-btn',
    'vr-genres-panel',
    'vr-playlists-panel',
    'vr-weather-widget',
    'vr-clock-widget'
  ];

  /* ── CSS Overrides ── */
  function injectLayoutCSS() {
    var css = document.createElement('style');
    css.id = 'vr-layout-fix-css';

    // Build hide rules for all IDs with high specificity
    var hideRules = HIDDEN_IDS.map(function (id) {
      return 'html body #' + id + '{display:none!important}';
    });

    // Build hide rules for classes
    var classHideRules = HIDDEN_CLASSES.map(function (cls) {
      return 'html body .' + cls + '{display:none!important}';
    });

    css.textContent = [
      '/* === VR Layout Fix v3: Prevent overlapping + protect A-Frame === */',

      /* ── Body background — prevent white flash ── */
      'body{background:#0a0a1a!important}',

      /* ── A-Frame scene & canvas — protect visibility only, let A-Frame handle positioning ── */
      'a-scene{display:block!important;visibility:visible!important;opacity:1!important}',
      'a-scene .a-canvas{display:block!important;visibility:visible!important;opacity:1!important}',

      /* ── A-Frame WebXR "Enter VR" button — must stay accessible ── */
      '.a-enter-vr{z-index:99999!important;bottom:16px!important;right:16px!important}',

      /* ── VR Mode Toggle — move to left side to avoid Enter VR button ── */
      '#vr-mode-toggle{bottom:16px!important;left:16px!important;right:auto!important;transform:none!important;z-index:200!important;width:40px!important;height:40px!important}',
      '#vr-mode-indicator{bottom:62px!important;left:16px!important;right:auto!important;transform:none!important;z-index:199!important}',
      '#vr-mode-selector{z-index:100000!important}',

      /* ── RIGHT COLUMN BOTTOM: stacked vertically ── */
      '#vr-nav-floating-btn{bottom:16px!important;right:70px!important;z-index:300!important}',
      '#vr-hud-toggle-btn{bottom:16px!important;right:120px!important;z-index:300!important}',

      /* Events sort bar — keep but compact */
      '#vr10-ev-bar{top:50px!important;right:10px!important;max-width:100px!important}',

      /* Login button — keep but reposition to not overlap drawer toggle */
      '#vr-login-btn{top:8px!important;right:60px!important}',

      /* ── LEFT COLUMN ── */
      '#vr16-trivia-btn{display:none!important}',
      '.qw7-stats-badge{display:none!important}',

      /* ── BOTTOM: clean stacking ── */
      /* Layer 1 (bottom): Keyboard hints bar */
      'html body #vr-hint-bar{bottom:0!important;left:0!important;right:0!important;z-index:150!important;padding:4px 16px 6px!important;font-size:11px!important;opacity:0.6!important}',
      /* Layer 2: Quick-launch zone bar */
      'html body #vr11-quick-launch{bottom:28px!important;z-index:160!important}',
      /* Layer 3: Ticker */
      'html body #vr14-ticker{bottom:64px!important;height:22px!important;z-index:140!important}',
      '#vr14-ticker-text{line-height:22px!important;font-size:11px!important}',
      /* Hide zen badge and continue badge to declutter */
      '#vr13-zen-badge{display:none!important}',
      '#vr9-continue{display:none!important}',

      /* ── TOP: fix Exit VR + Back + timer overlap ── */
      /* Exit VR button — force hidden on desktop (shown via JS on enter-vr) */
      'html body #vr-emergency-exit{display:none!important}',
      /* Back button on hub — hide (no parent to go back to) */
      'html body #back-btn{top:12px!important;left:12px!important;z-index:150!important}',
      /* Breadcrumb — reposition to not overlap with top-left buttons */
      '#vr-qw7-breadcrumb{top:12px!important;left:auto!important;right:auto!important}',

      /* ── Touch panel fix — move away from Enter VR area ── */
      '#touch-zone-panel{bottom:120px!important;right:76px!important;z-index:160!important}',
      '#touch-panel-toggle{bottom:72px!important;right:76px!important;z-index:161!important}',

      /* ── Mobile bar — reposition to avoid Enter VR button ── */
      '#vr-mobile-bar{bottom:80px!important;right:16px!important}',

      /* ── AI Agent button — reposition to avoid overlap ── */
      'html body #vr-agent-btn{bottom:16px!important;right:16px!important;width:44px!important;height:44px!important;font-size:20px!important;z-index:301!important}',
      /* Agent login button — keep in top-right but below drawer toggle */
      'html body #vr-agent-login-btn{top:12px!important;right:52px!important;z-index:500!important}',

      /* ── LEFT SIDE: clean up Hub/Reset/Settings overlap ── */
      /* Hub button — hide on hub page (you are already there) */
      'html body #vr-hub-btn{bottom:100px!important;left:12px!important;padding:6px 12px!important;font-size:12px!important;z-index:200!important}',
      /* Reset position — compact and position above hub button */
      'html body #vr-reset-btn{bottom:140px!important;left:12px!important;padding:6px 12px!important;font-size:12px!important;z-index:200!important}',

      /* ── BULK: hide all vr-*-btn buttons except essential ones ── */
      /* This catches set 11-16 buttons and any future additions */
      'html body button[id^="vr-"][id$="-btn"]:not(#vr-hub-btn):not(#vr-reset-btn):not(#vr-hud-toggle-btn):not(#vr-nav-floating-btn):not(#vr-agent-btn):not(#vr-mode-toggle){display:none!important}',
      /* Hide pet widget */
      'html body #vr-virtual-pet{display:none!important}',
      /* Hide all toast notifications from widget sets */
      'html body [id^="vr-toast-set"]{display:none!important}',

      /* ── TOP-LEFT: declutter ── */
      /* Hide achievement star badges that pile up */
      'html body .vr-achievement-badge{display:none!important}',
      'html body #vr-qw7-breadcrumb{display:none!important}',

      /* ── Drawer toggle for hidden widgets ── */
      '#vr-layout-drawer-toggle{',
      'position:fixed;top:10px;right:10px;z-index:99998;',
      'width:36px;height:36px;border-radius:10px;',
      'background:rgba(10,10,26,0.85);border:1px solid rgba(0,212,255,0.2);',
      'color:#64748b;font-size:16px;cursor:pointer;',
      'display:flex;align-items:center;justify-content:center;',
      'backdrop-filter:blur(8px);transition:all .25s;',
      'font-family:Inter,system-ui,sans-serif',
      '}',
      '#vr-layout-drawer-toggle:hover{border-color:rgba(0,212,255,0.5);color:#00d4ff}',
      '#vr-layout-drawer-toggle.active{background:rgba(0,212,255,0.15);color:#00d4ff}',

      /* When drawer is open, show hidden widgets in organized positions */
      'body.vr-drawer-open #vr15-pomo{display:block!important;position:fixed!important;top:50px!important;right:10px!important;z-index:155!important}',
      'body.vr-drawer-open #vr17-feed{display:block!important;position:fixed!important;top:240px!important;right:10px!important;max-height:160px!important;z-index:155!important}',
      'body.vr-drawer-open #vr17-habits{display:block!important;position:fixed!important;top:420px!important;right:10px!important;z-index:155!important}',
      'body.vr-drawer-open #vr13-recs{display:block!important;position:fixed!important;top:50px!important;right:220px!important;z-index:155!important}',
      'body.vr-drawer-open #vr16-stock-news{display:block!important;position:fixed!important;top:240px!important;right:220px!important;z-index:155!important}',
      'body.vr-drawer-open #vr17-ratings{display:block!important;position:fixed!important;top:420px!important;right:220px!important;z-index:155!important}',
      'body.vr-drawer-open #vr12-photo-btn{display:block!important;bottom:340px!important;right:10px!important}',
      'body.vr-drawer-open #vr13-particles{display:flex!important;bottom:380px!important;right:10px!important}',
      'body.vr-drawer-open #vr10-theater-btn{display:block!important;bottom:340px!important;right:200px!important}',
      'body.vr-drawer-open #vr-grab-indicator{display:block!important;bottom:300px!important;left:10px!important}',
      'body.vr-drawer-open #vr12-minimap{display:block!important;bottom:160px!important;right:10px!important}',
      'body.vr-drawer-open #vr-voicechat-btn{display:block!important}',
      'body.vr-drawer-open #vr16-outfit{display:block!important;bottom:80px!important;left:10px!important}',
      'body.vr-drawer-open #vr16-world-map{display:block!important;bottom:160px!important;left:10px!important}',
      'body.vr-drawer-open #vr14-scratch{display:block!important;bottom:280px!important;left:10px!important}',
      'body.vr-drawer-open #vr14-breathe{display:block!important;bottom:80px!important;left:240px!important}',
      'body.vr-drawer-open #vr10-med{display:block!important;bottom:160px!important;left:240px!important}',
      'body.vr-drawer-open #vr9-weather-timeline{display:block!important;bottom:80px!important}',

      /* ── Safety-net: force-hide loading overlays once layout is ready ── */
      'body.vr-layout-ready #loading{opacity:0!important;pointer-events:none!important}',
      'body.vr-layout-ready #loading-overlay{opacity:0!important;pointer-events:none!important}',

      /* Hide layout widgets in VR fullscreen */
      '.a-fullscreen #vr-layout-drawer-toggle{display:none}',
      '.a-fullscreen #vr-mode-toggle{display:none}',
      '.a-fullscreen #vr-mode-indicator{display:none}',
      '.a-fullscreen #touch-zone-panel{display:none}',
      '.a-fullscreen #touch-panel-toggle{display:none}',
      '.a-fullscreen #vr-mobile-bar{display:none}'
    ].concat(hideRules).concat(classHideRules).join('\n');

    document.head.appendChild(css);
  }

  /* ── JavaScript enforcement: directly hide elements via inline style ── */
  function enforceHiddenElements() {
    // Skip enforcement if drawer is open
    if (document.body.classList.contains('vr-drawer-open')) return;

    HIDDEN_IDS.forEach(function (id) {
      var el = document.getElementById(id);
      if (el && el.style.display !== 'none') {
        el.style.setProperty('display', 'none', 'important');
      }
    });

    HIDDEN_CLASSES.forEach(function (cls) {
      var els = document.querySelectorAll('.' + cls);
      for (var i = 0; i < els.length; i++) {
        if (els[i].style.display !== 'none') {
          els[i].style.setProperty('display', 'none', 'important');
        }
      }
    });
  }

  /* ── MutationObserver: catch elements as they are added to the DOM ── */
  /* NOTE: subtree is FALSE to avoid interfering with A-Frame's internal
     DOM operations. All widget scripts append directly to document.body,
     so childList on body alone is sufficient. */
  function observeDOM() {
    if (typeof MutationObserver === 'undefined') return;

    var hiddenSet = {};
    HIDDEN_IDS.forEach(function (id) { hiddenSet[id] = true; });

    var observer = new MutationObserver(function (mutations) {
      if (document.body.classList.contains('vr-drawer-open')) return;
      for (var i = 0; i < mutations.length; i++) {
        var added = mutations[i].addedNodes;
        for (var j = 0; j < added.length; j++) {
          var node = added[j];
          if (node.nodeType !== 1) continue; // skip text nodes
          // Skip A-Frame elements entirely
          if (node.tagName && node.tagName.indexOf('A-') === 0) continue;
          if (node.id && hiddenSet[node.id]) {
            node.style.setProperty('display', 'none', 'important');
          }
          // Also check direct children (in case a wrapper div is added)
          if (node.querySelectorAll) {
            var children = node.children;
            for (var k = 0; k < children.length; k++) {
              if (children[k].id && hiddenSet[children[k].id]) {
                children[k].style.setProperty('display', 'none', 'important');
              }
            }
          }
        }
      }
    });

    observer.observe(document.body, { childList: true, subtree: false });
  }

  /* ── Drawer toggle button ── */
  function createDrawerToggle() {
    if (document.getElementById('vr-layout-drawer-toggle')) return;
    var btn = document.createElement('button');
    btn.id = 'vr-layout-drawer-toggle';
    btn.innerHTML = '&#x2630;'; // hamburger icon
    btn.title = 'Show/hide extra widgets';
    btn.dataset.vrMode = 'simple';
    var open = false;
    btn.addEventListener('click', function () {
      open = !open;
      document.body.classList.toggle('vr-drawer-open', open);
      btn.classList.toggle('active', open);
      btn.innerHTML = open ? '&#x2715;' : '&#x2630;';
      btn.title = open ? 'Hide extra widgets' : 'Show extra widgets';

      if (!open) {
        // Re-hide all widgets when drawer closes
        enforceHiddenElements();
      }
    });
    document.body.appendChild(btn);
  }

  /* ── Dedup: remove duplicate clock/session widgets ── */
  function deduplicateWidgets() {
    var duplicateSelectors = [
      '#vr-pomodoro-indicator',
      '#vr-session-time-display'
    ];
    duplicateSelectors.forEach(function (sel) {
      var els = document.querySelectorAll(sel);
      for (var i = 1; i < els.length; i++) {
        els[i].style.setProperty('display', 'none', 'important');
      }
    });
  }

  /* ── Gaze Cursor: completely off on desktop, enabled only in VR headset ── */
  function fixGazeCursor() {
    var scene = document.querySelector('a-scene');
    if (!scene) return;

    /**
     * Gather all gaze cursor elements:
     *  - .vr-gaze-ring  (new convention: ring with data-vr-cursor / data-vr-raycaster)
     *  - [cursor*="fuse"] EXCLUDING a-scene (legacy pages)
     *  - a-cursor[fuse="true"] (legacy)
     */
    function getAllGazeCursors() {
      var cursors = [];
      var seen = {};

      // New convention: rings with class .vr-gaze-ring
      var gazeRings = document.querySelectorAll('.vr-gaze-ring');
      for (var g = 0; g < gazeRings.length; g++) {
        cursors.push(gazeRings[g]);
        seen[gazeRings[g]] = true;
      }

      // Legacy: [cursor*="fuse"], excluding a-scene
      var rings = document.querySelectorAll('[cursor*="fuse"]');
      for (var i = 0; i < rings.length; i++) {
        var tag = rings[i].tagName.toLowerCase();
        if (tag === 'a-scene') continue; // never hide or modify the scene element
        if (!seen[rings[i]]) cursors.push(rings[i]);
      }

      var acursors = document.querySelectorAll('a-cursor[fuse="true"]');
      for (var j = 0; j < acursors.length; j++) {
        if (!seen[acursors[j]]) cursors.push(acursors[j]);
      }
      return cursors;
    }

    /**
     * Desktop mode: completely remove cursor + raycaster from gaze rings
     * so they cannot intercept mouse clicks. Only the scene-level mouse cursor
     * (on a-scene) should handle click events on desktop.
     */
    function disableGazeCursors() {
      var cursors = getAllGazeCursors();
      for (var k = 0; k < cursors.length; k++) {
        var c = cursors[k];
        // Remove cursor component entirely (prevents click interception)
        if (c.hasAttribute('cursor')) {
          c.removeAttribute('cursor');
        }
        // Remove raycaster component (prevents intersection detection)
        if (c.hasAttribute('raycaster')) {
          c.removeAttribute('raycaster');
        }
        // Legacy a-cursor elements: just disable fuse
        if (c.tagName && c.tagName.toLowerCase() === 'a-cursor') {
          c.setAttribute('fuse', 'false');
        }
        c.setAttribute('visible', false);
      }
    }

    /**
     * VR mode: add cursor + raycaster to gaze rings for gaze-based interaction.
     * Reads config from data-vr-cursor / data-vr-raycaster attributes, or uses defaults.
     */
    function enableGazeCursors() {
      var cursors = getAllGazeCursors();
      for (var k = 0; k < cursors.length; k++) {
        var c = cursors[k];
        // Determine cursor config
        var cursorConf = c.dataset.vrCursor || 'fuse: true; fuseTimeout: 1500';
        var raycasterConf = c.dataset.vrRaycaster || 'objects: .clickable; far: 30';

        c.setAttribute('cursor', cursorConf);
        c.setAttribute('raycaster', raycasterConf);

        // Legacy a-cursor
        if (c.tagName && c.tagName.toLowerCase() === 'a-cursor') {
          c.setAttribute('fuse', 'true');
        }
        c.setAttribute('visible', true);
      }
    }

    // Disable immediately and again after scene loads (belt + suspenders)
    disableGazeCursors();
    if (scene.hasLoaded) { disableGazeCursors(); }
    else { scene.addEventListener('loaded', disableGazeCursors); }

    scene.addEventListener('enter-vr', enableGazeCursors);
    scene.addEventListener('exit-vr', disableGazeCursors);
  }

  /* ── Verify A-Frame scene is rendering properly ── */
  function verifyAFrameScene() {
    var scene = document.querySelector('a-scene');
    if (!scene) {
      console.warn('[VR Layout Fix] No a-scene found');
      return;
    }

    // Force-hide any lingering loading overlays (hub uses #loading, movies uses #loading-overlay)
    var loadingIds = ['loading', 'loading-overlay'];
    loadingIds.forEach(function (lid) {
      var loading = document.getElementById(lid);
      if (loading && !loading.classList.contains('hidden')) {
        loading.style.setProperty('opacity', '0');
        loading.style.setProperty('pointer-events', 'none');
        setTimeout(function () { loading.classList.add('hidden'); }, 500);
        console.log('[VR Layout Fix] Force-hid lingering overlay #' + lid);
      }
    });

    // Diagnostics (non-invasive — read-only checks)
    var boxes = scene.querySelectorAll('a-box[zone-link]');
    console.log('[VR Layout Fix] Zone portals found:', boxes.length);

    var cam = scene.querySelector('a-camera');
    if (cam) {
      console.log('[VR Layout Fix] Camera position:', cam.getAttribute('position'));
    }

    if (scene.renderer) {
      try {
        var size = scene.renderer.getSize(new THREE.Vector2());
        console.log('[VR Layout Fix] Renderer size:', size.x + 'x' + size.y);
        // Check if scene has 3D children
        if (scene.object3D) {
          console.log('[VR Layout Fix] Scene children:', scene.object3D.children.length);
        }
      } catch (e) {
        console.warn('[VR Layout Fix] Renderer check error:', e.message);
      }
    }
  }

  /* ── Init ── */
  function init() {
    injectLayoutCSS();
    createDrawerToggle();
    fixGazeCursor();
    observeDOM();

    // Enforce hidden state multiple times to catch late-created widgets
    // (some scripts use setTimeout up to 2500ms)
    enforceHiddenElements();
    setTimeout(enforceHiddenElements, 500);
    setTimeout(enforceHiddenElements, 1500);
    setTimeout(enforceHiddenElements, 3000);
    setTimeout(enforceHiddenElements, 5000);

    // Dedup after scripts finish creating elements
    setTimeout(deduplicateWidgets, 3000);

    // Verify A-Frame scene is rendering
    setTimeout(verifyAFrameScene, 2000);
    setTimeout(verifyAFrameScene, 5000);

    // Safety-net: mark body as layout-ready after 5s to force-hide lingering loading overlays via CSS
    setTimeout(function () {
      document.body.classList.add('vr-layout-ready');
    }, 5000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  console.log('[VR Layout Fix] Loaded — overlapping widgets will be auto-stacked');
})();
