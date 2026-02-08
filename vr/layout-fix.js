/**
 * VR Layout Fix — Resolves overlapping fixed-position UI widgets
 *
 * Problem: 25+ scripts each inject fixed-position panels at the same locations
 * (top:50px right:10px, bottom:50px right:10px, bottom:10px left:10px, etc.),
 * causing massive visual overlap on every VR page.
 *
 * Solution:
 *   1. Identify all fixed-position sidebar widgets
 *   2. Auto-stack the RIGHT column from top, with gaps
 *   3. Auto-stack the LEFT column from bottom-up, above the ticker
 *   4. Fix bottom bar layering (ticker → quick-launch → nav button)
 *   5. Collapse non-essential widgets into a slide-out drawer
 *   6. Protect A-Frame WebXR "Enter VR" button from being covered
 *   7. Re-position VR mode toggle to avoid conflicts
 *
 * Runs AFTER all quick-wins scripts (loaded at bottom of <body>).
 */
(function () {
  'use strict';

  /* ── CSS Overrides ── */
  function injectLayoutCSS() {
    var css = document.createElement('style');
    css.id = 'vr-layout-fix-css';
    css.textContent = [
      '/* === VR Layout Fix: Prevent overlapping fixed widgets === */',

      /* ── A-Frame WebXR "Enter VR" button — must stay accessible ── */
      '.a-enter-vr{z-index:99999!important;bottom:16px!important;right:16px!important}',

      /* ── VR Mode Toggle — move to left side to avoid Enter VR button ── */
      '#vr-mode-toggle{bottom:16px!important;left:16px!important;right:auto!important;transform:none!important;z-index:200!important;width:40px!important;height:40px!important}',
      '#vr-mode-indicator{bottom:62px!important;left:16px!important;right:auto!important;transform:none!important;z-index:199!important}',
      '#vr-mode-selector{z-index:100000!important}',

      /* ── RIGHT COLUMN BOTTOM: stacked vertically above Enter VR ── */

      /* Nav menu floating button — above Enter VR */
      '#vr-nav-floating-btn{bottom:72px!important;right:16px!important;z-index:300!important}',

      /* HUD toggle — next to nav button */
      '#vr-hud-toggle-btn{bottom:72px!important;right:72px!important;z-index:300!important}',

      /* Presence badge — above nav button */
      '#vr-presence-badge{bottom:120px!important;right:16px!important;max-width:160px!important;font-size:11px!important}',

      /* Minimap — above presence badge */
      '#vr12-minimap{bottom:160px!important;right:10px!important}',

      /* Photo button — hidden by default */
      '#vr12-photo-btn{display:none!important}',

      /* Particle density slider — hidden by default */
      '#vr13-particles{display:none!important}',

      /* Ratings — hidden by default */
      '#vr17-ratings{display:none!important}',

      /* Recommendations — above minimap */
      '#vr13-recs{bottom:300px!important;right:10px!important}',

      /* Theater button — hidden by default (zone-specific) */
      '#vr10-theater-btn{display:none!important}',

      /* Rate badge — hidden by default */
      '#vr10-rate-badge{display:none!important}',

      /* Calendar — hidden to avoid bottom-right clash */
      '#vr9-calendar{display:none!important}',

      /* Watch badge — hidden to avoid bottom-right clash */
      '#vr9-watch-badge{display:none!important}',

      /* ── RIGHT COLUMN TOP: zone-specific panels ── */

      /* Events sort bar */
      '#vr10-ev-bar{top:50px!important;right:10px!important;max-width:100px!important}',

      /* Daily habits */
      '#vr17-habits{top:50px!important;right:10px!important}',

      /* Activity feed — below habits */
      '#vr17-feed{top:260px!important;right:10px!important;max-height:160px!important}',

      /* Stock news — same slot as feed (zone-specific) */
      '#vr16-stock-news{top:260px!important;right:10px!important;max-height:180px!important}',

      /* ── VR MOVIES PAGE: Fix overlapping right-side widgets ── */

      /* Genres Panel — top right, below header */
      '.vr-genres-panel{top:60px!important;right:10px!important;max-width:200px!important;max-height:300px!important;overflow-y:auto!important;z-index:90!important}',

      /* Pomodoro Timer — below genres panel */
      '.vr15-pomo-container{top:370px!important;right:10px!important;z-index:90!important}',
      '#vr15-pomo-btn{top:370px!important;right:10px!important;z-index:90!important}',

      /* Weather Widget — below pomodoro */
      '.vr-weather-widget{top:450px!important;right:10px!important;z-index:90!important}',

      /* Clock Widget — below weather */
      '.vr-clock-widget{top:520px!important;right:10px!important;z-index:90!important}',

      /* Snap Turn Toggle — top right corner, small and compact */
      '#vr-snapturn-toggle{top:10px!important;right:220px!important;z-index:95!important}',

      /* Stats Button — stacked vertically on far right */
      '#vr-stats-btn{top:120px!important;right:10px!important;z-index:90!important}',

      /* Minimap Toggle — below stats */
      '#vr-minimap-toggle{top:170px!important;right:10px!important;z-index:90!important}',

      /* Weather Effects Button — below minimap */
      '#vr-weather-btn{top:220px!important;right:10px!important;z-index:90!important}',

      /* Language Button */
      '.vr13-lang-btn{top:270px!important;right:10px!important;z-index:90!important}',

      /* Playlists Panel — left side to avoid right-side congestion */
      '.vr-playlists-panel{top:60px!important;left:10px!important;right:auto!important;max-width:180px!important;max-height:400px!important;overflow-y:auto!important;z-index:90!important}',

      /* ── LEFT COLUMN: stacked bottom-up, above ticker ── */

      /* Input indicator — above ticker */
      '#vr-input-indicator{bottom:80px!important;left:12px!important}',

      /* Outfit suggestion — hidden by default */
      '#vr16-outfit{display:none!important}',

      /* World map — hidden by default */
      '#vr16-world-map{display:none!important}',

      /* Trivia button — above input indicator */
      '#vr16-trivia-btn{bottom:110px!important;left:10px!important}',

      /* Scratchpad — hidden by default */
      '#vr14-scratch{display:none!important}',

      /* Breathing exercise — hidden by default */
      '#vr14-breathe{display:none!important}',

      /* Stats badge — above ticker */
      '.qw7-stats-badge{bottom:80px!important;left:12px!important}',

      /* Meditation widget — hidden */
      '#vr10-med{display:none!important}',

      /* Stats widget — hidden */
      '#vr10-stats{display:none!important}',

      /* ── BOTTOM CENTER: proper layering ── */

      /* Ticker — full width, above quick-launch */
      '#vr14-ticker{bottom:52px!important;height:24px!important}',
      '#vr14-ticker-text{line-height:24px!important;font-size:11px!important}',

      /* Quick-launch bar — bottom center */
      '#vr11-quick-launch{bottom:8px!important;z-index:170!important}',

      /* Zen badge — left of center, above ticker */
      '#vr13-zen-badge{bottom:54px!important;left:12px!important;transform:none!important}',

      /* Continue badge — above quick-launch */
      '#vr9-continue{bottom:55px!important}',

      /* Weather timeline — hidden to prevent full-width bottom overlap */
      '#vr9-weather-timeline{display:none!important}',

      /* ── Touch panel fix — move away from Enter VR area ── */
      '#touch-zone-panel{bottom:120px!important;right:76px!important;z-index:160!important}',
      '#touch-panel-toggle{bottom:72px!important;right:76px!important;z-index:161!important}',

      /* ── Mobile bar — reposition to avoid Enter VR button ── */
      '#vr-mobile-bar{bottom:80px!important;right:16px!important}',

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

      /* When drawer is open, show hidden widgets */
      'body.vr-drawer-open #vr12-photo-btn{display:block!important;bottom:340px!important;right:10px!important}',
      'body.vr-drawer-open #vr13-particles{display:flex!important;bottom:380px!important;right:10px!important}',
      'body.vr-drawer-open #vr17-ratings{display:block!important;bottom:420px!important;right:10px!important}',
      'body.vr-drawer-open #vr10-theater-btn{display:block!important;bottom:340px!important;right:200px!important}',
      'body.vr-drawer-open #vr16-outfit{display:block!important;bottom:80px!important;left:10px!important}',
      'body.vr-drawer-open #vr16-world-map{display:block!important;bottom:160px!important;left:10px!important}',
      'body.vr-drawer-open #vr14-scratch{display:block!important;bottom:280px!important;left:10px!important}',
      'body.vr-drawer-open #vr14-breathe{display:block!important;bottom:80px!important;left:240px!important}',
      'body.vr-drawer-open #vr10-med{display:block!important;bottom:160px!important;left:240px!important}',
      'body.vr-drawer-open #vr9-weather-timeline{display:block!important;bottom:80px!important}',

      /* Hide layout widgets in VR fullscreen — only keep essential 3D elements */
      '.a-fullscreen #vr-layout-drawer-toggle{display:none}',
      '.a-fullscreen #vr-mode-toggle{display:none}',
      '.a-fullscreen #vr-mode-indicator{display:none}',
      '.a-fullscreen #touch-zone-panel{display:none}',
      '.a-fullscreen #touch-panel-toggle{display:none}',
      '.a-fullscreen #vr-mobile-bar{display:none}'
    ].join('\n');
    document.head.appendChild(css);
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
      btn.innerHTML = open ? '&#x2715;' : '&#x2630;'; // X vs hamburger
      btn.title = open ? 'Hide extra widgets' : 'Show extra widgets';
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
        els[i].style.display = 'none';
      }
    });
  }

  /* ── Gaze Cursor: fuse only in VR headset mode ── */
  // On desktop, the gaze fuse auto-fires after a timeout and "forces" users
  // into zones they were just looking at. Disable fuse until actual VR mode.
  function fixGazeCursor() {
    var scene = document.querySelector('a-scene');
    if (!scene) return;

    // Find ALL fuse cursors (various pages use different patterns)
    function getAllGazeCursors() {
      var cursors = [];
      // a-ring / a-entity with cursor component containing fuse
      var rings = document.querySelectorAll('[cursor*="fuse"]');
      for (var i = 0; i < rings.length; i++) cursors.push(rings[i]);
      // a-cursor elements with fuse attribute
      var acursors = document.querySelectorAll('a-cursor[fuse="true"]');
      for (var j = 0; j < acursors.length; j++) cursors.push(acursors[j]);
      return cursors;
    }

    // Disable fuse on all gaze cursors (desktop mode)
    function disableFuse() {
      var cursors = getAllGazeCursors();
      for (var k = 0; k < cursors.length; k++) {
        var c = cursors[k];
        if (c.tagName && c.tagName.toLowerCase() === 'a-cursor') {
          c.setAttribute('fuse', 'false');
        } else {
          c.setAttribute('cursor', 'fuse', false);
        }
        c.setAttribute('visible', false);
      }
    }

    // Enable fuse on all gaze cursors (VR headset mode)
    function enableFuse() {
      var cursors = getAllGazeCursors();
      for (var k = 0; k < cursors.length; k++) {
        var c = cursors[k];
        if (c.tagName && c.tagName.toLowerCase() === 'a-cursor') {
          c.setAttribute('fuse', 'true');
        } else {
          c.setAttribute('cursor', 'fuse', true);
        }
        c.setAttribute('visible', true);
      }
    }

    // Start with fuse disabled (desktop default)
    if (scene.hasLoaded) {
      disableFuse();
    } else {
      scene.addEventListener('loaded', disableFuse);
    }

    scene.addEventListener('enter-vr', enableFuse);
    scene.addEventListener('exit-vr', disableFuse);
  }

  /* ── Init ── */
  function init() {
    injectLayoutCSS();
    createDrawerToggle();
    fixGazeCursor();
    // Dedup after a short delay to let scripts finish creating elements
    setTimeout(deduplicateWidgets, 3000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  console.log('[VR Layout Fix] Loaded — overlapping widgets will be auto-stacked');
})();
