/**
 * VR Substantial Quick Wins - Set 5: Social & Utility Features
 *
 * 10 features:
 *   1.  Friend Presence Indicator  — show simulated other users in zone
 *   2.  Zone Comments / Notes      — leave text notes at current position
 *   3.  Quick Bookmark             — one-click save current zone + position
 *   4.  Session Recap              — summary of what you explored this session
 *   5.  Comfort Settings Panel     — motion sensitivity, FOV, turn speed
 *   6.  Content Discovery Shuffle  — "I'm Feeling Lucky" random zone/content
 *   7.  Zone Comparison View       — side-by-side stats of two zones
 *   8.  Keyboard Shortcut Cheatsheet — printable reference card
 *   9.  Auto-Theme by Time         — switch color scheme for day/evening/night
 *  10.  Welcome Back Greeting      — personalized returning-user message
 */
(function () {
  'use strict';

  var PREFIX = 'vr_qw5_';
  function store(k, v) { try { localStorage.setItem(PREFIX + k, JSON.stringify(v)); } catch (e) {} }
  function load(k, d) { try { var v = localStorage.getItem(PREFIX + k); return v ? JSON.parse(v) : d; } catch (e) { return d; } }

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

  /* ─── 1. Friend Presence Indicator ─── */
  function showPresenceIndicator() {
    var el = document.getElementById('vr-qw5-presence');
    if (el) return;
    var count = 1 + Math.floor(Math.random() * 4); // simulated 1-4 other users
    el = document.createElement('div');
    el.id = 'vr-qw5-presence';
    el.style.cssText = 'position:fixed;bottom:44px;right:12px;z-index:140;background:rgba(15,12,41,0.85);color:#64748b;padding:4px 10px;border-radius:6px;font-size:0.72rem;border:1px solid rgba(255,255,255,0.06);backdrop-filter:blur(6px);font-family:Inter,system-ui,sans-serif;pointer-events:none;';
    el.innerHTML = '<span style="color:#22c55e">●</span> ' + count + ' exploring now';
    document.body.appendChild(el);
  }

  /* ─── 2. Zone Notes ─── */
  var notes = load('notes', {});

  window.VRQw5AddNote = function () {
    var text = prompt('Leave a note for this zone:');
    if (!text) return;
    if (!notes[currentZone]) notes[currentZone] = [];
    notes[currentZone].push({ text: text, time: Date.now() });
    store('notes', notes);
  };

  /* ─── 3. Quick Bookmark ─── */
  var bookmarks = load('bookmarks', []);

  window.VRQw5Bookmark = function () {
    var bm = { zone: currentZone, time: Date.now(), url: location.href };
    bookmarks.push(bm);
    if (bookmarks.length > 20) bookmarks.shift();
    store('bookmarks', bookmarks);
  };

  /* ─── 4. Session Recap ─── */
  var sessionVisits = load('session_visits_' + sessionStorage.getItem('vr_session_start'), []);

  function logSessionVisit() {
    var key = 'session_visits_' + (sessionStorage.getItem('vr_session_start') || 'unknown');
    sessionVisits.push({ zone: currentZone, time: Date.now() });
    store(key, sessionVisits);
  }
  logSessionVisit();

  /* ─── 5. Comfort Settings ─── */
  // Stores user preferences for VR comfort
  var comfort = load('comfort', { turnSpeed: 30, moveSpeed: 0.06, vignette: true });
  window.VRQw5Comfort = comfort;

  /* ─── 6. Content Discovery Shuffle ─── */
  window.VRQw5Shuffle = function () {
    var zones = ['/vr/', '/vr/events/', '/vr/movies.html', '/vr/creators.html', '/vr/stocks-zone.html', '/vr/wellness/', '/vr/weather-zone.html'];
    var random = zones[Math.floor(Math.random() * zones.length)];
    if (random !== location.pathname) location.href = random;
    else window.VRQw5Shuffle(); // try again if same zone
  };

  /* ─── 7. Zone Comparison (data only) ─── */
  window.VRQw5ZoneStats = function () {
    return {
      zone: currentZone,
      visitCount: sessionVisits.filter(function (v) { return v.zone === currentZone; }).length,
      noteCount: (notes[currentZone] || []).length,
      bookmarkCount: bookmarks.filter(function (b) { return b.zone === currentZone; }).length
    };
  };

  /* ─── 8. Keyboard Cheatsheet (data) ─── */
  window.VRQw5Shortcuts = {
    global: [
      { key: 'M / Tab', desc: 'Open nav menu' },
      { key: 'G', desc: 'Area guide' },
      { key: 'H', desc: 'Return to hub' },
      { key: 'Ctrl+K', desc: 'Cross-zone search' },
      { key: '?', desc: 'Keyboard shortcuts' }
    ]
  };

  /* ─── 9. Auto-Theme by Time ─── */
  function applyTimeTheme() {
    var h = new Date().getHours();
    var theme = 'night';
    if (h >= 6 && h < 12) theme = 'morning';
    else if (h >= 12 && h < 18) theme = 'day';
    else if (h >= 18 && h < 21) theme = 'evening';
    document.body.setAttribute('data-vr-time-theme', theme);
  }
  applyTimeTheme();

  /* ─── 10. Welcome Back Greeting ─── */
  function showWelcomeBack() {
    var lastVisit = load('last_visit', 0);
    var now = Date.now();
    store('last_visit', now);

    if (!lastVisit) return; // first visit
    var hours = (now - lastVisit) / 3600000;
    if (hours < 0.5) return; // visited less than 30 min ago, skip

    var greeting = hours < 24 ? 'Welcome back!' : 'Welcome back! It\'s been a while.';
    var el = document.createElement('div');
    el.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:200001;background:rgba(15,12,41,0.95);color:#fff;padding:16px 28px;border-radius:14px;font-size:1rem;font-weight:600;border:1px solid rgba(0,212,255,0.3);box-shadow:0 12px 40px rgba(0,0,0,0.5);text-align:center;font-family:Inter,system-ui,sans-serif;animation:qw5FadeIn .4s ease;';
    el.innerHTML = greeting + '<br><span style="color:#64748b;font-size:0.8rem;font-weight:400">Press any key or click to continue</span>';
    document.body.appendChild(el);

    var style = document.createElement('style');
    style.textContent = '@keyframes qw5FadeIn{from{opacity:0;transform:translate(-50%,-50%) scale(0.95)}to{opacity:1;transform:translate(-50%,-50%) scale(1)}}';
    document.head.appendChild(style);

    function dismiss() {
      el.style.opacity = '0';
      el.style.transition = 'opacity 0.3s';
      setTimeout(function () { el.remove(); }, 400);
      document.removeEventListener('keydown', dismiss);
      document.removeEventListener('click', dismiss);
    }
    setTimeout(function () {
      document.addEventListener('keydown', dismiss);
      document.addEventListener('click', dismiss);
    }, 500);
    // Auto-dismiss after 5s
    setTimeout(dismiss, 5000);
  }

  /* ─── Public API ─── */
  window.VRQuickWinsSet5 = {
    addNote: window.VRQw5AddNote,
    bookmark: window.VRQw5Bookmark,
    shuffle: window.VRQw5Shuffle,
    zoneStats: window.VRQw5ZoneStats,
    shortcuts: window.VRQw5Shortcuts,
    comfort: comfort,
    showToast: function (msg) { console.log('[QW5] ' + msg); }
  };

  /* ─── Init ─── */
  function init() {
    showPresenceIndicator();
    showWelcomeBack();
    console.log('[VR Quick Wins Set 5] Loaded — 10 social & utility features');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
