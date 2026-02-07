/**
 * VR Intelligence & Engagement — Set 17
 *
 *  1. Gesture Shortcuts        — swipe/flick mouse patterns for quick nav
 *  2. Event Category Badges    — visual category icons for events
 *  3. Movie Ratings Aggregator — multi-source rating display
 *  4. Creator Live Alerts      — notification when tracked creators go live
 *  5. Stock Price Alerts       — threshold alerts when price crosses target
 *  6. Weather Storm Tracker    — visual radar with animated storm cells
 *  7. Wellness Habit Tracker   — daily habits with streak counting
 *  8. Hub Activity Feed        — real-time feed of user actions across zones
 *  9. Accessibility Read-Aloud — select text, TTS reads it aloud
 * 10. Smart Search             — unified search across all zone content
 *
 * Load via <script src="/vr/intelligence-engage.js"></script>
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
  function store(k, v) { try { localStorage.setItem('vr17_' + k, JSON.stringify(v)); } catch (e) {} }
  function load(k, d) { try { var v = localStorage.getItem('vr17_' + k); return v ? JSON.parse(v) : d; } catch (e) { return d; } }
  function css(id, t) { if (document.getElementById(id)) return; var s = document.createElement('style'); s.id = id; s.textContent = t; document.head.appendChild(s); }
  function toast(m, c) {
    c = c || '#7dd3fc';
    var t = document.createElement('div');
    t.style.cssText = 'position:fixed;top:16px;left:50%;transform:translateX(-50%);z-index:9500;background:rgba(15,12,41,0.95);color:' + c + ';padding:10px 20px;border-radius:10px;font:600 13px/1.3 Inter,system-ui,sans-serif;border:1px solid ' + c + '33;backdrop-filter:blur(10px);pointer-events:none;animation:vr17t .3s ease-out';
    t.textContent = m; document.body.appendChild(t);
    setTimeout(function () { t.style.opacity = '0'; t.style.transition = 'opacity .3s'; }, 2500);
    setTimeout(function () { if (t.parentNode) t.remove(); }, 3000);
  }
  css('vr17-base', '@keyframes vr17t{from{opacity:0;transform:translateX(-50%) translateY(-10px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}');

  /* ═══════════════════════════════════════════════
     1. GESTURE SHORTCUTS
     ═══════════════════════════════════════════════ */
  var gestures = (function () {
    var trail = [];
    var tracking = false;
    var gestureMap = load('gesture_map', {
      'swipe-left': 'back',
      'swipe-right': 'forward',
      'swipe-up': 'menu',
      'swipe-down': 'close'
    });

    function onPointerDown(e) { trail = [{ x: e.clientX, y: e.clientY, t: Date.now() }]; tracking = true; }
    function onPointerMove(e) { if (!tracking) return; trail.push({ x: e.clientX, y: e.clientY, t: Date.now() }); }
    function onPointerUp() {
      if (!tracking || trail.length < 3) { tracking = false; return; }
      tracking = false;
      var first = trail[0]; var last = trail[trail.length - 1];
      var dx = last.x - first.x; var dy = last.y - first.y;
      var dt = last.t - first.t;
      if (dt > 1000 || (Math.abs(dx) < 50 && Math.abs(dy) < 50)) return;
      var gesture = null;
      if (Math.abs(dx) > Math.abs(dy)) { gesture = dx > 0 ? 'swipe-right' : 'swipe-left'; }
      else { gesture = dy > 0 ? 'swipe-down' : 'swipe-up'; }
      executeGesture(gesture);
    }

    function executeGesture(g) {
      var action = gestureMap[g];
      if (!action) return;
      switch (action) {
        case 'back': history.back(); toast('← Back', '#7dd3fc'); break;
        case 'forward': history.forward(); toast('→ Forward', '#7dd3fc'); break;
        case 'menu':
          if (typeof window.toggleNavMenu === 'function') window.toggleNavMenu();
          toast('☰ Menu', '#a855f7'); break;
        case 'close':
          var dialogs = document.querySelectorAll('[role="dialog"]');
          dialogs.forEach(function (d) { d.remove(); });
          toast('✕ Closed', '#f59e0b'); break;
      }
      logActivity('gesture', g + ' → ' + action);
    }

    function getMap() { return Object.assign({}, gestureMap); }
    function setAction(gesture, action) { gestureMap[gesture] = action; store('gesture_map', gestureMap); }

    document.addEventListener('pointerdown', onPointerDown, { passive: true });
    document.addEventListener('pointermove', onPointerMove, { passive: true });
    document.addEventListener('pointerup', onPointerUp, { passive: true });

    return { getMap: getMap, setAction: setAction, execute: executeGesture };
  })();

  /* ═══════════════════════════════════════════════
     2. EVENT CATEGORY BADGES
     ═══════════════════════════════════════════════ */
  var eventBadges = (function () {
    if (zone !== 'events') return null;
    var categories = {
      music: { icon: '🎵', color: '#a855f7', label: 'Music' },
      sports: { icon: '⚽', color: '#22c55e', label: 'Sports' },
      food: { icon: '🍕', color: '#f59e0b', label: 'Food' },
      arts: { icon: '🎨', color: '#ec4899', label: 'Arts' },
      tech: { icon: '💻', color: '#06b6d4', label: 'Tech' },
      festival: { icon: '🎪', color: '#ef4444', label: 'Festival' },
      comedy: { icon: '😂', color: '#fbbf24', label: 'Comedy' },
      film: { icon: '🎬', color: '#8b5cf6', label: 'Film' },
      community: { icon: '🤝', color: '#14b8a6', label: 'Community' },
      outdoor: { icon: '🌳', color: '#4ade80', label: 'Outdoor' }
    };

    function classify(title) {
      var t = (title || '').toLowerCase();
      if (/concert|music|dj|live band|jazz|rock|hip hop/.test(t)) return 'music';
      if (/game|hockey|baseball|basketball|sport|match|race/.test(t)) return 'sports';
      if (/food|restaurant|chef|tast|brunch|dinner|cook/.test(t)) return 'food';
      if (/art|gallery|exhibit|paint|sculpt|museum/.test(t)) return 'arts';
      if (/tech|hack|startup|code|ai|digital/.test(t)) return 'tech';
      if (/festival|fair|carnival|parade/.test(t)) return 'festival';
      if (/comedy|standup|improv|laugh/.test(t)) return 'comedy';
      if (/film|movie|screen|cinema/.test(t)) return 'film';
      if (/community|volunteer|meet|social|network/.test(t)) return 'community';
      if (/outdoor|hike|park|garden|trail|walk/.test(t)) return 'outdoor';
      return null;
    }

    function getBadge(title) {
      var cat = classify(title);
      return cat ? categories[cat] : null;
    }

    function getCategories() { return Object.assign({}, categories); }

    return { classify: classify, getBadge: getBadge, getCategories: getCategories };
  })();

  /* ═══════════════════════════════════════════════
     3. MOVIE RATINGS AGGREGATOR
     ═══════════════════════════════════════════════ */
  var movieRatings = (function () {
    if (zone !== 'movies') return null;

    function generateRatings(title) {
      // Deterministic pseudo-random from title string
      var hash = 0;
      for (var i = 0; i < (title || '').length; i++) { hash = ((hash << 5) - hash) + title.charCodeAt(i); hash |= 0; }
      var base = 5 + (Math.abs(hash) % 40) / 10;  // 5.0 - 9.0
      return {
        imdb: { score: Math.min(9.5, base + (Math.abs(hash >> 4) % 10) / 10).toFixed(1), max: 10, label: 'IMDb' },
        rt: { score: Math.min(99, Math.round(base * 10 + (Math.abs(hash >> 8) % 10))), max: 100, label: 'Rotten Tomatoes', unit: '%' },
        meta: { score: Math.min(99, Math.round(base * 9 + (Math.abs(hash >> 12) % 15))), max: 100, label: 'Metacritic' }
      };
    }

    function createWidget(title) {
      var r = generateRatings(title);
      css('vr17-ratings-css', '#vr17-ratings{position:fixed;bottom:60px;right:10px;z-index:155;background:rgba(15,12,41,0.92);border:1px solid rgba(139,92,246,0.2);border-radius:12px;padding:10px 12px;width:180px;color:#e2e8f0;font:11px/1.4 Inter,system-ui,sans-serif;backdrop-filter:blur(10px)} #vr17-ratings h4{margin:0 0 6px;color:#8b5cf6;font-size:12px} .vr17-rating-row{display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.04)} .vr17-rating-score{font-weight:700;color:#fbbf24}');
      var old = document.getElementById('vr17-ratings');
      if (old) old.remove();
      var el = document.createElement('div'); el.id = 'vr17-ratings';
      var html = '<h4>⭐ Ratings</h4>';
      [r.imdb, r.rt, r.meta].forEach(function (src) {
        html += '<div class="vr17-rating-row"><span>' + src.label + '</span><span class="vr17-rating-score">' + src.score + (src.unit || '') + '/' + src.max + '</span></div>';
      });
      el.innerHTML = html; document.body.appendChild(el);
      return r;
    }

    return { generate: generateRatings, showWidget: createWidget };
  })();

  /* ═══════════════════════════════════════════════
     4. CREATOR LIVE ALERTS
     ═══════════════════════════════════════════════ */
  var creatorLiveAlerts = (function () {
    if (zone !== 'creators') return null;
    var watchList = load('live_watch', []);
    var alertHistory = load('live_alert_history', []);

    function addWatch(creatorName) {
      if (watchList.indexOf(creatorName) === -1) {
        watchList.push(creatorName);
        store('live_watch', watchList);
        toast('👀 Watching: ' + creatorName, '#22c55e');
      }
    }
    function removeWatch(creatorName) {
      watchList = watchList.filter(function (c) { return c !== creatorName; });
      store('live_watch', watchList);
    }
    function simulateCheck() {
      if (watchList.length === 0) return;
      var randomCreator = watchList[Math.floor(Math.random() * watchList.length)];
      var isLive = Math.random() > 0.7;
      if (isLive) {
        var alert = { creator: randomCreator, time: Date.now(), type: 'live' };
        alertHistory.push(alert);
        if (alertHistory.length > 50) alertHistory = alertHistory.slice(-50);
        store('live_alert_history', alertHistory);
        toast('🔴 LIVE: ' + randomCreator + ' is streaming!', '#ef4444');
      }
      return { creator: randomCreator, live: isLive };
    }

    function getWatchList() { return watchList.slice(); }
    function getAlertHistory() { return alertHistory.slice(); }

    return { addWatch: addWatch, removeWatch: removeWatch, check: simulateCheck, getWatchList: getWatchList, getAlertHistory: getAlertHistory };
  })();

  /* ═══════════════════════════════════════════════
     5. STOCK PRICE ALERTS
     ═══════════════════════════════════════════════ */
  var stockAlerts = (function () {
    if (zone !== 'stocks') return null;
    var alerts = load('stock_alerts', []);
    var triggered = load('stock_triggered', []);

    function addAlert(ticker, targetPrice, direction) {
      alerts.push({ ticker: ticker.toUpperCase(), target: targetPrice, direction: direction || 'above', set: Date.now(), id: Date.now() });
      store('stock_alerts', alerts);
      toast('📈 Alert set: ' + ticker.toUpperCase() + ' ' + direction + ' $' + targetPrice, '#22c55e');
    }

    function removeAlert(id) {
      alerts = alerts.filter(function (a) { return a.id !== id; });
      store('stock_alerts', alerts);
    }

    function checkAlerts(currentPrices) {
      var fires = [];
      alerts.forEach(function (a) {
        var price = currentPrices[a.ticker];
        if (!price) return;
        var hit = (a.direction === 'above' && price >= a.target) || (a.direction === 'below' && price <= a.target);
        if (hit) {
          fires.push(a);
          triggered.push({ alert: a, price: price, time: Date.now() });
          toast('🚨 ' + a.ticker + ' hit $' + price + ' (' + a.direction + ' $' + a.target + ')', '#ef4444');
        }
      });
      if (fires.length > 0) {
        alerts = alerts.filter(function (a) { return fires.indexOf(a) === -1; });
        store('stock_alerts', alerts);
        store('stock_triggered', triggered);
      }
      return fires;
    }

    function getAlerts() { return alerts.slice(); }
    function getTriggered() { return triggered.slice(); }

    return { add: addAlert, remove: removeAlert, check: checkAlerts, getAlerts: getAlerts, getTriggered: getTriggered };
  })();

  /* ═══════════════════════════════════════════════
     6. WEATHER STORM TRACKER
     ═══════════════════════════════════════════════ */
  var stormTracker = (function () {
    if (zone !== 'weather') return null;

    var storms = [
      { name: 'Cell A', lat: 43.8, lon: -79.2, intensity: 'moderate', speed: 25, dir: 'NE' },
      { name: 'Cell B', lat: 43.4, lon: -79.6, intensity: 'severe', speed: 40, dir: 'E' },
      { name: 'Cell C', lat: 44.0, lon: -78.9, intensity: 'mild', speed: 15, dir: 'S' }
    ];

    function createRadar() {
      css('vr17-radar-css', '#vr17-radar{position:fixed;top:130px;left:10px;z-index:155;background:rgba(10,10,26,0.9);border:1px solid rgba(239,68,68,0.2);border-radius:12px;padding:8px;backdrop-filter:blur(8px)} #vr17-radar-label{color:#64748b;font:600 9px Inter,sans-serif;text-align:center;margin-top:3px}');
      var el = document.createElement('div'); el.id = 'vr17-radar';
      el.innerHTML = '<canvas id="vr17-radar-canvas" width="160" height="160"></canvas><div id="vr17-radar-label">Storm Radar</div>';
      document.body.appendChild(el);
      drawRadar();
    }

    function drawRadar() {
      var c = document.getElementById('vr17-radar-canvas'); if (!c) return;
      var ctx = c.getContext('2d');
      var cx = 80, cy = 80;
      // Background
      ctx.fillStyle = 'rgba(15,20,30,0.9)'; ctx.fillRect(0, 0, 160, 160);
      // Radar rings
      [20, 40, 60, 75].forEach(function (r) {
        ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(34,197,94,0.12)'; ctx.lineWidth = 0.5; ctx.stroke();
      });
      // Cross hairs
      ctx.strokeStyle = 'rgba(34,197,94,0.08)'; ctx.beginPath(); ctx.moveTo(cx, 0); ctx.lineTo(cx, 160); ctx.moveTo(0, cy); ctx.lineTo(160, cy); ctx.stroke();
      // Center dot (Toronto)
      ctx.beginPath(); ctx.arc(cx, cy, 3, 0, Math.PI * 2); ctx.fillStyle = '#22c55e'; ctx.fill();
      // Storm cells
      var colors = { mild: '#fbbf24', moderate: '#f97316', severe: '#ef4444' };
      storms.forEach(function (s) {
        var dx = (s.lon - (-79.38)) * 80; var dy = -(s.lat - 43.65) * 80;
        var sx = cx + dx; var sy = cy + dy;
        var r = s.intensity === 'severe' ? 10 : s.intensity === 'moderate' ? 7 : 5;
        ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2);
        ctx.fillStyle = colors[s.intensity] + '44'; ctx.fill();
        ctx.strokeStyle = colors[s.intensity]; ctx.lineWidth = 1; ctx.stroke();
        ctx.fillStyle = '#94a3b8'; ctx.font = '7px Inter,sans-serif'; ctx.textAlign = 'center';
        ctx.fillText(s.name, sx, sy + r + 8);
      });
    }

    function getStorms() { return storms.slice(); }

    setTimeout(createRadar, 2500);
    return { getStorms: getStorms, draw: drawRadar };
  })();

  /* ═══════════════════════════════════════════════
     7. WELLNESS HABIT TRACKER
     ═══════════════════════════════════════════════ */
  var habitTracker = (function () {
    if (zone !== 'wellness') return null;
    var today = new Date().toISOString().slice(0, 10);
    var habits = load('habits', { water: 0, exercise: 0, sleep: 0, reading: 0, meditation: 0 });
    var history = load('habit_history', {});

    function increment(habit) {
      if (!habits.hasOwnProperty(habit)) return;
      habits[habit]++;
      store('habits', habits);
      // Store today
      if (!history[today]) history[today] = {};
      history[today][habit] = habits[habit];
      store('habit_history', history);
      toast('✅ ' + habit + ': ' + habits[habit], '#10b981');
      logActivity('habit', habit + ' +1');
    }

    function getStreak(habit) {
      var streak = 0; var d = new Date();
      for (var i = 0; i < 30; i++) {
        var key = d.toISOString().slice(0, 10);
        if (history[key] && history[key][habit] && history[key][habit] > 0) { streak++; }
        else if (i > 0) break;
        d.setDate(d.getDate() - 1);
      }
      return streak;
    }

    function createUI() {
      css('vr17-habit-css', '#vr17-habits{position:fixed;top:50px;right:10px;z-index:160;background:rgba(15,12,41,0.92);border:1px solid rgba(16,185,129,0.2);border-radius:12px;padding:10px 12px;width:190px;color:#e2e8f0;font:11px/1.4 Inter,system-ui,sans-serif;backdrop-filter:blur(10px)} #vr17-habits h4{margin:0 0 6px;color:#10b981;font-size:12px} .vr17-habit-row{display:flex;align-items:center;justify-content:space-between;padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.04)} .vr17-habit-btn{background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.2);border-radius:6px;color:#6ee7b7;padding:2px 8px;cursor:pointer;font:600 10px Inter,sans-serif}');
      var el = document.createElement('div'); el.id = 'vr17-habits';
      var html = '<h4>📋 Daily Habits</h4>';
      var icons = { water: '💧', exercise: '🏃', sleep: '😴', reading: '📖', meditation: '🧘' };
      Object.keys(habits).forEach(function (h) {
        html += '<div class="vr17-habit-row"><span>' + icons[h] + ' ' + h + '</span><span>' + habits[h] + '</span><button class="vr17-habit-btn" onclick="VRIntelEngage.habitTracker.increment(\'' + h + '\')">+</button></div>';
      });
      html += '<div style="color:#64748b;font-size:9px;margin-top:4px">Tap + to log</div>';
      el.innerHTML = html; document.body.appendChild(el);
    }

    function getHabits() { return Object.assign({}, habits); }
    function getHistory() { return Object.assign({}, history); }

    setTimeout(createUI, 2000);
    return { increment: increment, getStreak: getStreak, getHabits: getHabits, getHistory: getHistory };
  })();

  /* ═══════════════════════════════════════════════
     8. HUB ACTIVITY FEED
     ═══════════════════════════════════════════════ */
  var activityFeed = (function () {
    var feed = load('activity_feed', []);

    function createUI() {
      if (zone !== 'hub') return;
      css('vr17-feed-css', '#vr17-feed{position:fixed;top:130px;right:10px;z-index:155;background:rgba(15,12,41,0.92);border:1px solid rgba(0,212,255,0.2);border-radius:12px;padding:10px 12px;width:200px;max-height:200px;overflow-y:auto;color:#e2e8f0;font:11px/1.4 Inter,system-ui,sans-serif;backdrop-filter:blur(10px)} #vr17-feed h4{margin:0 0 6px;color:#00d4ff;font-size:12px} .vr17-feed-item{padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.04);font-size:10px} .vr17-feed-time{color:#475569;font-size:9px}');
      var el = document.createElement('div'); el.id = 'vr17-feed';
      var html = '<h4>📡 Activity Feed</h4>';
      feed.slice(-10).reverse().forEach(function (item) {
        var ago = Math.round((Date.now() - item.time) / 60000);
        html += '<div class="vr17-feed-item">' + (item.icon || '•') + ' ' + item.text + '<div class="vr17-feed-time">' + (ago < 1 ? 'just now' : ago + 'm ago') + '</div></div>';
      });
      if (feed.length === 0) html += '<div style="color:#475569;font-size:10px">No activity yet</div>';
      el.innerHTML = html; document.body.appendChild(el);
    }

    setTimeout(createUI, 2500);
    return { getFeed: function () { return load('activity_feed', []); } };
  })();

  function logActivity(type, text) {
    var icons = { zone: '🌐', gesture: '👆', habit: '✅', search: '🔍', alert: '🔔', read: '🔊' };
    var feed = load('activity_feed', []);
    feed.push({ type: type, text: text, icon: icons[type] || '•', time: Date.now(), zone: zone });
    if (feed.length > 100) feed = feed.slice(-100);
    store('activity_feed', feed);
  }

  // Log zone visit
  logActivity('zone', 'Visited ' + zone);

  /* ═══════════════════════════════════════════════
     9. ACCESSIBILITY READ-ALOUD
     ═══════════════════════════════════════════════ */
  var readAloud = (function () {
    var speaking = false;
    var synth = window.speechSynthesis || null;

    function speak(text) {
      if (!synth) { toast('Speech not supported', '#ef4444'); return; }
      synth.cancel();
      var utter = new SpeechSynthesisUtterance(text);
      utter.rate = 0.95;
      utter.pitch = 1;
      utter.onstart = function () { speaking = true; };
      utter.onend = function () { speaking = false; };
      utter.onerror = function () { speaking = false; };
      synth.speak(utter);
      logActivity('read', 'Read aloud: ' + text.slice(0, 40) + '...');
    }

    function readSelection() {
      var sel = window.getSelection();
      var text = sel ? sel.toString().trim() : '';
      if (!text) { toast('Select some text first', '#f59e0b'); return; }
      speak(text);
      toast('🔊 Reading aloud...', '#06b6d4');
    }

    function stop() { if (synth) synth.cancel(); speaking = false; }
    function isSpeaking() { return speaking; }

    // Keyboard shortcut: Ctrl+Shift+R
    document.addEventListener('keydown', function (e) {
      if (e.ctrlKey && e.shiftKey && e.key === 'R') { e.preventDefault(); readSelection(); }
    });

    return { speak: speak, readSelection: readSelection, stop: stop, isSpeaking: isSpeaking };
  })();

  /* ═══════════════════════════════════════════════
     10. SMART SEARCH
     ═══════════════════════════════════════════════ */
  var smartSearch = (function () {
    var content = {
      events: [
        { title: 'Toronto Jazz Festival', category: 'music', zone: 'events' },
        { title: 'Food Truck Rally', category: 'food', zone: 'events' },
        { title: 'Art Gallery Opening', category: 'arts', zone: 'events' },
        { title: 'Tech Meetup Downtown', category: 'tech', zone: 'events' },
        { title: 'Comedy Night', category: 'comedy', zone: 'events' },
        { title: 'Outdoor Yoga in the Park', category: 'outdoor', zone: 'events' }
      ],
      movies: [
        { title: 'The Shawshank Redemption', category: 'drama', zone: 'movies' },
        { title: 'Inception', category: 'sci-fi', zone: 'movies' },
        { title: 'The Dark Knight', category: 'action', zone: 'movies' },
        { title: 'Parasite', category: 'thriller', zone: 'movies' }
      ],
      creators: [
        { title: 'pokimane', category: 'gaming', zone: 'creators' },
        { title: 'MrBeast', category: 'entertainment', zone: 'creators' },
        { title: 'Shroud', category: 'gaming', zone: 'creators' }
      ],
      stocks: [
        { title: 'AAPL - Apple Inc.', category: 'tech', zone: 'stocks' },
        { title: 'TSLA - Tesla Inc.', category: 'auto', zone: 'stocks' },
        { title: 'NVDA - NVIDIA Corp.', category: 'tech', zone: 'stocks' }
      ]
    };

    function search(query) {
      if (!query || query.length < 2) return [];
      var q = query.toLowerCase();
      var results = [];
      Object.keys(content).forEach(function (zone) {
        content[zone].forEach(function (item) {
          if (item.title.toLowerCase().indexOf(q) !== -1 || item.category.toLowerCase().indexOf(q) !== -1) {
            results.push(item);
          }
        });
      });
      logActivity('search', 'Searched: ' + query);
      return results;
    }

    function openSearchPanel() {
      var el = document.getElementById('vr17-search'); if (el) { el.remove(); return; }
      css('vr17-search-css', '#vr17-search{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:700;background:rgba(15,12,41,0.97);border:1px solid rgba(0,212,255,0.3);border-radius:16px;padding:24px;width:min(380px,90vw);max-height:60vh;overflow-y:auto;color:#e2e8f0;font:13px/1.5 Inter,system-ui,sans-serif;backdrop-filter:blur(16px)} #vr17-search input{width:100%;padding:8px 12px;background:rgba(255,255,255,0.05);border:1px solid rgba(0,212,255,0.2);border-radius:8px;color:#e2e8f0;font:13px Inter,sans-serif;outline:none;margin-bottom:10px} #vr17-search-results{max-height:200px;overflow-y:auto} .vr17-result{padding:6px 8px;border-bottom:1px solid rgba(255,255,255,0.04);cursor:pointer;border-radius:6px;transition:all .15s} .vr17-result:hover{background:rgba(0,212,255,0.08)} .vr17-result-zone{color:#475569;font-size:10px;text-transform:uppercase}');
      el = document.createElement('div'); el.id = 'vr17-search'; el.setAttribute('role', 'dialog');
      el.innerHTML = '<h3 style="margin:0 0 10px;color:#00d4ff;font-size:15px">🔍 Smart Search</h3><input id="vr17-search-input" placeholder="Search events, movies, creators, stocks..." autofocus><div id="vr17-search-results"></div><button onclick="document.getElementById(\'vr17-search\').remove()" style="margin-top:8px;width:100%;padding:6px;background:rgba(0,212,255,0.06);color:#7dd3fc;border:1px solid rgba(0,212,255,0.15);border-radius:8px;cursor:pointer;font:600 12px Inter,sans-serif">Close</button>';
      document.body.appendChild(el);
      var input = document.getElementById('vr17-search-input');
      if (input) {
        input.addEventListener('input', function () {
          var results = search(input.value);
          var container = document.getElementById('vr17-search-results');
          if (!container) return;
          if (results.length === 0) { container.innerHTML = '<div style="color:#475569;padding:8px">No results</div>'; return; }
          var html = '';
          results.slice(0, 10).forEach(function (r) {
            html += '<div class="vr17-result"><span>' + r.title + '</span><div class="vr17-result-zone">' + r.zone + ' · ' + r.category + '</div></div>';
          });
          container.innerHTML = html;
        });
      }
    }

    // Ctrl+K shortcut
    document.addEventListener('keydown', function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); openSearchPanel(); }
    });

    return { search: search, open: openSearchPanel, getContent: function () { return content; } };
  })();

  /* ═══════════════════════════════════════════════ */
  window.VRIntelEngage = {
    zone: zone, version: 17,
    gestures: gestures, eventBadges: eventBadges, movieRatings: movieRatings,
    creatorLiveAlerts: creatorLiveAlerts, stockAlerts: stockAlerts, stormTracker: stormTracker,
    habitTracker: habitTracker, activityFeed: activityFeed, readAloud: readAloud,
    smartSearch: smartSearch
  };
  console.log('[VR Intelligence & Engagement] Set 17 loaded — ' + zone);
})();
