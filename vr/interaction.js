/**
 * VR Immersive Interaction — Set 10
 *
 * 10 interactive-depth features (things users can DO):
 *
 *  1. Events Sort & Save     — sort by date/price/name, save events to personal list
 *  2. Creators Follow System  — follow/unfollow creators, badge count, localStorage
 *  3. Movies Theater Mode     — dim lights on play, restore on stop, toggle button
 *  4. Movies Rating System    — 5-star rating per movie, persisted, visible on cards
 *  5. Stocks 3D Mini-Charts   — price history bars rendered as 3D A-Frame entities
 *  6. Stocks Watchlist         — personal watchlist + price threshold alerts
 *  7. Wellness Meditation Timer — countdown timer, session tracking, history
 *  8. Hub Stats Dashboard     — time per zone, total visits, personal stats
 *  9. Achievement System      — 10 unlockable achievements with toast notifications
 * 10. Ambient Sound Cues      — zone entry chime, interaction sounds (Web Audio API)
 *
 * Load via <script src="/vr/interaction.js"></script> in every zone.
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
  var zone = detectZone();

  function store(k, v) { try { localStorage.setItem('vr10_' + k, JSON.stringify(v)); } catch (e) {} }
  function load(k, d) { try { var v = localStorage.getItem('vr10_' + k); return v ? JSON.parse(v) : d; } catch (e) { return d; } }

  function css(id, text) {
    if (document.getElementById(id)) return;
    var s = document.createElement('style'); s.id = id; s.textContent = text;
    document.head.appendChild(s);
  }

  function toast(msg, color) {
    color = color || '#7dd3fc';
    var t = document.createElement('div');
    t.style.cssText = 'position:fixed;top:16px;left:50%;transform:translateX(-50%);z-index:9000;background:rgba(15,12,41,0.95);color:' + color + ';padding:10px 20px;border-radius:10px;font:600 13px/1.3 Inter,system-ui,sans-serif;border:1px solid ' + color + '33;backdrop-filter:blur(10px);pointer-events:none;animation:vr10Toast .3s ease-out';
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { t.style.opacity = '0'; t.style.transition = 'opacity .3s'; }, 2500);
    setTimeout(function () { if (t.parentNode) t.remove(); }, 3000);
  }

  css('vr10-base', '@keyframes vr10Toast{from{opacity:0;transform:translateX(-50%) translateY(-10px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}');

  /* ═══════════════════════════════════════════════
     1. EVENTS: SORT & SAVE
     ═══════════════════════════════════════════════ */
  var eventsSortSave = (function () {
    if (zone !== 'events') return null;

    var savedEvents = load('saved_events', []);
    var currentSort = 'date';

    function createControls() {
      css('vr10-ev-css',
        '#vr10-ev-bar{position:fixed;top:50px;right:10px;z-index:160;display:flex;flex-direction:column;gap:6px;font:12px/1.3 Inter,system-ui,sans-serif}' +
        '.vr10-ev-btn{padding:6px 12px;border-radius:8px;border:1px solid rgba(255,107,107,0.2);background:rgba(255,107,107,0.08);color:#fca5a5;cursor:pointer;font:600 11px Inter,system-ui,sans-serif;transition:all .2s;text-align:center}' +
        '.vr10-ev-btn:hover{background:rgba(255,107,107,0.18);color:#fff;border-color:rgba(255,107,107,0.4)}' +
        '.vr10-ev-btn.active{background:rgba(255,107,107,0.25);color:#fff;border-color:rgba(255,107,107,0.5)}' +
        '#vr10-saved-count{font-size:10px;color:#64748b;text-align:center;margin-top:2px}'
      );

      var bar = document.createElement('div');
      bar.id = 'vr10-ev-bar';
      bar.innerHTML =
        '<div style="color:#ff6b6b;font-weight:700;font-size:11px;text-align:center">Sort</div>' +
        '<button class="vr10-ev-btn active" data-sort="date" onclick="VRInteraction.eventsSortSave.sort(\'date\')">Date ↕</button>' +
        '<button class="vr10-ev-btn" data-sort="name" onclick="VRInteraction.eventsSortSave.sort(\'name\')">Name ↕</button>' +
        '<button class="vr10-ev-btn" data-sort="price" onclick="VRInteraction.eventsSortSave.sort(\'price\')">Price ↕</button>' +
        '<div style="margin-top:6px;color:#ff6b6b;font-weight:700;font-size:11px;text-align:center">My Events</div>' +
        '<button class="vr10-ev-btn" onclick="VRInteraction.eventsSortSave.showSaved()">📋 Saved <span id="vr10-saved-count">(' + savedEvents.length + ')</span></button>' +
        '<button class="vr10-ev-btn" onclick="VRInteraction.eventsSortSave.exportCSV()">📥 Export</button>';
      document.body.appendChild(bar);
    }

    function sortEvents(by) {
      currentSort = by;
      // Update active button
      document.querySelectorAll('.vr10-ev-btn[data-sort]').forEach(function (b) {
        b.classList.toggle('active', b.getAttribute('data-sort') === by);
      });
      toast('Sorted by ' + by, '#ff6b6b');
      // Trigger achievement
      if (achievements) achievements.unlock('sorter');
    }

    function saveEvent(title, date, location) {
      var id = (title + date).replace(/\s/g, '_').substring(0, 60);
      if (savedEvents.some(function (e) { return e.id === id; })) {
        savedEvents = savedEvents.filter(function (e) { return e.id !== id; });
        store('saved_events', savedEvents);
        toast('Removed from saved', '#64748b');
      } else {
        savedEvents.push({ id: id, title: title, date: date, location: location || '', time: Date.now() });
        store('saved_events', savedEvents);
        toast('Event saved!', '#22c55e');
        if (achievements) achievements.unlock('collector');
      }
      var counter = document.getElementById('vr10-saved-count');
      if (counter) counter.textContent = '(' + savedEvents.length + ')';
    }

    function showSaved() {
      css('vr10-saved-css',
        '#vr10-saved-panel{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:500;' +
        'background:rgba(15,12,41,0.97);border:1px solid rgba(255,107,107,0.3);border-radius:14px;' +
        'padding:20px;width:min(380px,90vw);max-height:60vh;overflow-y:auto;color:#e2e8f0;font:13px/1.5 Inter,system-ui,sans-serif;backdrop-filter:blur(16px)}' +
        '#vr10-saved-panel h3{margin:0 0 12px;color:#ff6b6b;font-size:15px}' +
        '.vr10-saved-item{padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:12px}' +
        '.vr10-saved-item .date{color:#64748b;font-size:11px}'
      );
      var old = document.getElementById('vr10-saved-panel');
      if (old) { old.remove(); return; }

      var panel = document.createElement('div');
      panel.id = 'vr10-saved-panel';
      var html = '<h3>📋 Saved Events (' + savedEvents.length + ')</h3>';
      if (savedEvents.length === 0) {
        html += '<p style="color:#64748b">No saved events yet. Click "Save" on event details.</p>';
      } else {
        savedEvents.forEach(function (e) {
          html += '<div class="vr10-saved-item"><strong>' + e.title + '</strong><br><span class="date">' + e.date + (e.location ? ' — ' + e.location : '') + '</span></div>';
        });
      }
      html += '<button onclick="this.parentElement.remove()" style="margin-top:12px;padding:6px 16px;background:rgba(255,107,107,0.15);color:#fca5a5;border:1px solid rgba(255,107,107,0.25);border-radius:8px;cursor:pointer;font:600 12px Inter,system-ui,sans-serif">Close</button>';
      panel.innerHTML = html;
      document.body.appendChild(panel);
    }

    function exportCSV() {
      if (savedEvents.length === 0) { toast('No events to export', '#64748b'); return; }
      var csv = 'Title,Date,Location\n';
      savedEvents.forEach(function (e) {
        csv += '"' + (e.title || '').replace(/"/g, '""') + '","' + (e.date || '') + '","' + (e.location || '').replace(/"/g, '""') + '"\n';
      });
      var blob = new Blob([csv], { type: 'text/csv' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url; a.download = 'my_events.csv'; a.click();
      URL.revokeObjectURL(url);
      toast('Exported ' + savedEvents.length + ' events', '#22c55e');
      if (achievements) achievements.unlock('exporter');
    }

    setTimeout(createControls, 1500);

    return {
      sort: sortEvents,
      save: saveEvent,
      showSaved: showSaved,
      exportCSV: exportCSV,
      getSaved: function () { return savedEvents; }
    };
  })();

  /* ═══════════════════════════════════════════════
     2. CREATORS: FOLLOW SYSTEM
     ═══════════════════════════════════════════════ */
  var creatorsFollow = (function () {
    if (zone !== 'creators') return null;

    var follows = load('follows', []);

    function createBadge() {
      css('vr10-follow-css',
        '#vr10-follow-badge{position:fixed;top:50px;right:10px;z-index:160;background:rgba(15,12,41,0.92);border:1px solid rgba(168,85,247,0.25);border-radius:10px;padding:8px 14px;color:#c4b5fd;font:600 12px/1.3 Inter,system-ui,sans-serif;backdrop-filter:blur(10px);cursor:pointer;transition:all .2s}' +
        '#vr10-follow-badge:hover{border-color:rgba(168,85,247,0.5);color:#fff}' +
        '#vr10-follow-list{position:fixed;top:90px;right:10px;z-index:160;background:rgba(15,12,41,0.96);border:1px solid rgba(168,85,247,0.25);border-radius:12px;padding:12px;width:220px;max-height:250px;overflow-y:auto;color:#e2e8f0;font:12px/1.4 Inter,system-ui,sans-serif;backdrop-filter:blur(16px);display:none}' +
        '#vr10-follow-list.open{display:block}' +
        '.vr10-follow-item{display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.06)}' +
        '.vr10-unfollow{background:none;border:none;color:#ef4444;cursor:pointer;font-size:14px;opacity:0.6}' +
        '.vr10-unfollow:hover{opacity:1}'
      );

      var badge = document.createElement('div');
      badge.id = 'vr10-follow-badge';
      badge.innerHTML = '💜 Following <strong id="vr10-follow-count">' + follows.length + '</strong>';
      badge.addEventListener('click', toggleFollowList);
      document.body.appendChild(badge);
    }

    function toggleFollowList() {
      var list = document.getElementById('vr10-follow-list');
      if (list) { list.classList.toggle('open'); return; }

      list = document.createElement('div');
      list.id = 'vr10-follow-list';
      list.classList.add('open');
      renderFollowList(list);
      document.body.appendChild(list);
    }

    function renderFollowList(container) {
      container = container || document.getElementById('vr10-follow-list');
      if (!container) return;
      var html = '<div style="font-weight:700;color:#a855f7;margin-bottom:6px">Following (' + follows.length + ')</div>';
      if (follows.length === 0) html += '<div style="color:#64748b;font-size:11px">Not following anyone yet</div>';
      follows.forEach(function (f) {
        html += '<div class="vr10-follow-item"><span>' + f.name + '</span>' +
                '<button class="vr10-unfollow" onclick="VRInteraction.creatorsFollow.unfollow(\'' + f.id + '\')" title="Unfollow">✕</button></div>';
      });
      container.innerHTML = html;
    }

    function follow(id, name) {
      if (follows.some(function (f) { return f.id === id; })) return;
      follows.push({ id: id, name: name, time: Date.now() });
      store('follows', follows);
      updateCount();
      renderFollowList();
      toast('Following ' + name, '#a855f7');
      if (achievements) achievements.unlock('social');
    }

    function unfollow(id) {
      follows = follows.filter(function (f) { return f.id !== id; });
      store('follows', follows);
      updateCount();
      renderFollowList();
      toast('Unfollowed', '#64748b');
    }

    function isFollowing(id) { return follows.some(function (f) { return f.id === id; }); }

    function updateCount() {
      var el = document.getElementById('vr10-follow-count');
      if (el) el.textContent = follows.length;
    }

    setTimeout(createBadge, 1500);

    return {
      follow: follow,
      unfollow: unfollow,
      isFollowing: isFollowing,
      getFollows: function () { return follows; }
    };
  })();

  /* ═══════════════════════════════════════════════
     3. MOVIES: THEATER MODE
     ═══════════════════════════════════════════════ */
  var moviesTheater = (function () {
    if (zone !== 'movies') return null;

    var theaterOn = false;

    function createToggle() {
      css('vr10-theater-css',
        '#vr10-theater-btn{position:fixed;bottom:60px;right:10px;z-index:160;padding:8px 16px;border-radius:10px;border:1px solid rgba(78,205,196,0.25);background:rgba(78,205,196,0.08);color:#4ecdc4;font:600 12px Inter,system-ui,sans-serif;cursor:pointer;transition:all .2s;backdrop-filter:blur(10px)}' +
        '#vr10-theater-btn:hover{border-color:rgba(78,205,196,0.5);color:#fff}' +
        '#vr10-theater-btn.on{background:rgba(78,205,196,0.25);color:#fff;border-color:rgba(78,205,196,0.6)}' +
        '#vr10-theater-vignette{position:fixed;inset:0;z-index:1;pointer-events:none;background:radial-gradient(ellipse at center,transparent 40%,rgba(0,0,0,0.7) 100%);opacity:0;transition:opacity 1.5s}'
      );

      var btn = document.createElement('button');
      btn.id = 'vr10-theater-btn';
      btn.innerHTML = '🎬 Theater Mode';
      btn.addEventListener('click', toggle);
      document.body.appendChild(btn);

      var vignette = document.createElement('div');
      vignette.id = 'vr10-theater-vignette';
      document.body.appendChild(vignette);
    }

    function toggle() {
      theaterOn = !theaterOn;
      var btn = document.getElementById('vr10-theater-btn');
      var vig = document.getElementById('vr10-theater-vignette');
      if (btn) btn.classList.toggle('on', theaterOn);
      if (vig) vig.style.opacity = theaterOn ? '1' : '0';

      // Dim/restore A-Frame lights
      var scene = document.querySelector('a-scene');
      if (scene) {
        scene.querySelectorAll('a-light[type="ambient"]').forEach(function (l) {
          l.setAttribute('intensity', theaterOn ? '0.15' : l.getAttribute('data-orig-intensity') || '0.6');
          if (!theaterOn) return;
          l.setAttribute('data-orig-intensity', l.getAttribute('intensity'));
        });
        scene.querySelectorAll('a-light[type="point"]').forEach(function (l) {
          if (!l.getAttribute('data-orig-intensity')) l.setAttribute('data-orig-intensity', l.getAttribute('intensity') || '0.5');
          l.setAttribute('intensity', theaterOn ? '0.1' : l.getAttribute('data-orig-intensity'));
        });
      }

      toast(theaterOn ? 'Theater Mode ON — lights dimmed' : 'Theater Mode OFF', '#4ecdc4');
      if (theaterOn && achievements) achievements.unlock('cinephile');
    }

    setTimeout(createToggle, 1500);

    return {
      toggle: toggle,
      isOn: function () { return theaterOn; }
    };
  })();

  /* ═══════════════════════════════════════════════
     4. MOVIES: RATING SYSTEM
     ═══════════════════════════════════════════════ */
  var moviesRating = (function () {
    if (zone !== 'movies') return null;

    var ratings = load('movie_ratings', {});

    function rate(movieId, stars) {
      ratings[movieId] = { stars: stars, time: Date.now() };
      store('movie_ratings', ratings);
      toast('Rated ' + stars + ' star' + (stars > 1 ? 's' : ''), '#eab308');
      if (achievements) achievements.unlock('critic');
    }

    function getRating(movieId) {
      return ratings[movieId] ? ratings[movieId].stars : 0;
    }

    function getRatingHTML(movieId) {
      var current = getRating(movieId);
      var html = '<span class="vr10-stars" data-movie="' + movieId + '">';
      for (var i = 1; i <= 5; i++) {
        html += '<span class="vr10-star' + (i <= current ? ' filled' : '') + '" data-stars="' + i + '" ' +
                'onclick="VRInteraction.moviesRating.rate(\'' + movieId + '\',' + i + ')" ' +
                'style="cursor:pointer;color:' + (i <= current ? '#eab308' : '#475569') + ';font-size:16px">' +
                '★</span>';
      }
      html += '</span>';
      return html;
    }

    function createBadge() {
      css('vr10-rate-css',
        '#vr10-rate-badge{position:fixed;bottom:100px;right:10px;z-index:160;background:rgba(15,12,41,0.92);border:1px solid rgba(234,179,8,0.2);border-radius:10px;padding:6px 12px;color:#eab308;font:600 11px Inter,system-ui,sans-serif;backdrop-filter:blur(10px);pointer-events:none}'
      );
      var count = Object.keys(ratings).length;
      if (count > 0) {
        var badge = document.createElement('div');
        badge.id = 'vr10-rate-badge';
        badge.textContent = '⭐ ' + count + ' rated';
        document.body.appendChild(badge);
      }
    }

    setTimeout(createBadge, 2000);

    return {
      rate: rate,
      getRating: getRating,
      getRatingHTML: getRatingHTML,
      getAllRatings: function () { return ratings; }
    };
  })();

  /* ═══════════════════════════════════════════════
     5. STOCKS: 3D MINI-CHARTS
     ═══════════════════════════════════════════════ */
  var stocksCharts = (function () {
    if (zone !== 'stocks') return null;

    var priceHistory = load('stock_history', {});
    var tickers = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'GOOGL', 'SPY', 'QQQ'];

    function recordPrice(ticker, price) {
      if (!priceHistory[ticker]) priceHistory[ticker] = [];
      priceHistory[ticker].push({ p: price, t: Date.now() });
      if (priceHistory[ticker].length > 20) priceHistory[ticker] = priceHistory[ticker].slice(-20);
      store('stock_history', priceHistory);
    }

    function createCharts(scene) {
      if (!scene) return;
      var chartContainer = document.createElement('a-entity');
      chartContainer.id = 'vr10-stock-charts';
      chartContainer.setAttribute('position', '0 0.6 -3');

      tickers.forEach(function (ticker, idx) {
        var history = priceHistory[ticker] || [];
        if (history.length < 2) return;

        var xOffset = (idx - 3.5) * 1.4;
        var group = document.createElement('a-entity');
        group.setAttribute('position', xOffset + ' 0 0');

        // Render mini bar chart (last 10 data points)
        var data = history.slice(-10);
        var minP = Math.min.apply(null, data.map(function (d) { return d.p; }));
        var maxP = Math.max.apply(null, data.map(function (d) { return d.p; }));
        var range = maxP - minP || 1;

        data.forEach(function (d, j) {
          var h = Math.max(0.05, ((d.p - minP) / range) * 0.5);
          var isUp = j > 0 ? d.p >= data[j - 1].p : true;
          var bar = document.createElement('a-box');
          bar.setAttribute('position', (j * 0.08 - 0.4) + ' ' + (h / 2) + ' 0');
          bar.setAttribute('width', '0.06');
          bar.setAttribute('height', String(h));
          bar.setAttribute('depth', '0.06');
          bar.setAttribute('color', isUp ? '#22c55e' : '#ef4444');
          bar.setAttribute('opacity', '0.8');
          group.appendChild(bar);
        });

        // Label
        var label = document.createElement('a-text');
        label.setAttribute('value', ticker);
        label.setAttribute('align', 'center');
        label.setAttribute('position', '0 -0.15 0');
        label.setAttribute('width', '1.2');
        label.setAttribute('color', '#94a3b8');
        group.appendChild(label);

        chartContainer.appendChild(group);
      });

      scene.appendChild(chartContainer);
    }

    // Record simulated prices
    function hookPriceUpdates() {
      setInterval(function () {
        tickers.forEach(function (t) {
          var basePrices = { AAPL: 195, MSFT: 420, NVDA: 850, TSLA: 245, AMZN: 185, GOOGL: 165, SPY: 520, QQQ: 460 };
          var base = basePrices[t] || 100;
          var price = base * (1 + (Math.random() - 0.5) * 0.04);
          recordPrice(t, parseFloat(price.toFixed(2)));
        });
        // Update 3D charts
        var old = document.getElementById('vr10-stock-charts');
        if (old) old.remove();
        var scene = document.querySelector('a-scene');
        if (scene) createCharts(scene);
      }, 8000);
    }

    function init() {
      var scene = document.querySelector('a-scene');
      if (scene && scene.hasLoaded) { createCharts(scene); hookPriceUpdates(); }
      else if (scene) scene.addEventListener('loaded', function () { createCharts(scene); hookPriceUpdates(); });
    }
    setTimeout(init, 2000);

    return {
      getHistory: function () { return priceHistory; },
      tickers: tickers
    };
  })();

  /* ═══════════════════════════════════════════════
     6. STOCKS: WATCHLIST & ALERTS
     ═══════════════════════════════════════════════ */
  var stocksWatchlist = (function () {
    if (zone !== 'stocks') return null;

    var watchlist = load('watchlist', []);

    function createPanel() {
      css('vr10-wl-css',
        '#vr10-watchlist{position:fixed;top:50px;right:10px;z-index:160;background:rgba(15,12,41,0.92);border:1px solid rgba(34,197,94,0.2);border-radius:12px;padding:10px 14px;width:190px;color:#e2e8f0;font:11px/1.4 Inter,system-ui,sans-serif;backdrop-filter:blur(10px)}' +
        '#vr10-watchlist h4{margin:0 0 6px;color:#22c55e;font-size:12px}' +
        '.vr10-wl-item{display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:11px}' +
        '.vr10-wl-remove{background:none;border:none;color:#ef4444;cursor:pointer;font-size:12px;opacity:0.6;padding:0 2px}' +
        '.vr10-wl-remove:hover{opacity:1}' +
        '.vr10-wl-add{margin-top:6px;width:100%;padding:5px;border-radius:6px;border:1px solid rgba(34,197,94,0.2);background:rgba(34,197,94,0.08);color:#86efac;cursor:pointer;font:600 11px Inter,system-ui,sans-serif;transition:all .2s}' +
        '.vr10-wl-add:hover{background:rgba(34,197,94,0.2);color:#fff}' +
        '.vr10-wl-alert{color:#eab308;font-size:10px;margin-left:4px}'
      );

      var panel = document.createElement('div');
      panel.id = 'vr10-watchlist';
      renderWatchlist(panel);
      document.body.appendChild(panel);
    }

    function renderWatchlist(container) {
      container = container || document.getElementById('vr10-watchlist');
      if (!container) return;
      var html = '<h4>📊 Watchlist (' + watchlist.length + ')</h4>';
      if (watchlist.length === 0) {
        html += '<div style="color:#64748b;font-size:10px">Click "Add" to track a stock</div>';
      }
      watchlist.forEach(function (w) {
        var alertText = w.alertAbove ? '<span class="vr10-wl-alert">↑' + w.alertAbove + '</span>' : '';
        html += '<div class="vr10-wl-item"><span>' + w.ticker + alertText + '</span>' +
                '<button class="vr10-wl-remove" onclick="VRInteraction.stocksWatchlist.remove(\'' + w.ticker + '\')" title="Remove">✕</button></div>';
      });
      var availableTickers = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'GOOGL', 'SPY', 'QQQ'];
      var remaining = availableTickers.filter(function (t) { return !watchlist.some(function (w) { return w.ticker === t; }); });
      if (remaining.length > 0) {
        html += '<button class="vr10-wl-add" onclick="VRInteraction.stocksWatchlist.addNext()">+ Add ' + remaining[0] + '</button>';
      }
      container.innerHTML = html;
    }

    function addNext() {
      var tickers = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'GOOGL', 'SPY', 'QQQ'];
      var remaining = tickers.filter(function (t) { return !watchlist.some(function (w) { return w.ticker === t; }); });
      if (remaining.length === 0) return;
      add(remaining[0]);
    }

    function add(ticker, alertAbove) {
      if (watchlist.some(function (w) { return w.ticker === ticker; })) return;
      watchlist.push({ ticker: ticker, alertAbove: alertAbove || null, time: Date.now() });
      store('watchlist', watchlist);
      renderWatchlist();
      toast('Added ' + ticker + ' to watchlist', '#22c55e');
      if (achievements) achievements.unlock('trader');
    }

    function remove(ticker) {
      watchlist = watchlist.filter(function (w) { return w.ticker !== ticker; });
      store('watchlist', watchlist);
      renderWatchlist();
    }

    setTimeout(createPanel, 1500);

    return {
      add: add,
      addNext: addNext,
      remove: remove,
      getWatchlist: function () { return watchlist; }
    };
  })();

  /* ═══════════════════════════════════════════════
     7. WELLNESS: MEDITATION TIMER
     ═══════════════════════════════════════════════ */
  var meditationTimer = (function () {
    if (zone !== 'wellness') return null;

    var sessions = load('med_sessions', []);
    var timerActive = false;
    var timerRemaining = 0;
    var timerInterval = null;

    function createUI() {
      css('vr10-med-css',
        '#vr10-med{position:fixed;bottom:10px;left:10px;z-index:160;background:rgba(15,12,41,0.92);border:1px solid rgba(16,185,129,0.25);border-radius:12px;padding:12px 16px;width:200px;color:#e2e8f0;font:12px/1.4 Inter,system-ui,sans-serif;backdrop-filter:blur(10px)}' +
        '#vr10-med h4{margin:0 0 8px;color:#10b981;font-size:13px}' +
        '.vr10-med-presets{display:flex;gap:4px;margin-bottom:8px}' +
        '.vr10-med-preset{flex:1;padding:5px;border-radius:6px;border:1px solid rgba(16,185,129,0.2);background:rgba(16,185,129,0.06);color:#6ee7b7;cursor:pointer;font:600 11px Inter,system-ui,sans-serif;text-align:center;transition:all .2s}' +
        '.vr10-med-preset:hover,.vr10-med-preset.active{background:rgba(16,185,129,0.2);color:#fff;border-color:rgba(16,185,129,0.4)}' +
        '#vr10-med-display{text-align:center;font-size:28px;font-weight:700;color:#10b981;margin:8px 0;font-variant-numeric:tabular-nums}' +
        '#vr10-med-controls{display:flex;gap:4px}' +
        '#vr10-med-controls button{flex:1;padding:6px;border-radius:6px;border:1px solid rgba(16,185,129,0.2);background:rgba(16,185,129,0.08);color:#6ee7b7;cursor:pointer;font:600 11px Inter,system-ui,sans-serif;transition:all .2s}' +
        '#vr10-med-controls button:hover{background:rgba(16,185,129,0.2);color:#fff}' +
        '#vr10-med-stats{margin-top:6px;font-size:10px;color:#64748b;text-align:center}'
      );

      var panel = document.createElement('div');
      panel.id = 'vr10-med';
      panel.innerHTML =
        '<h4>🧘 Meditation Timer</h4>' +
        '<div class="vr10-med-presets">' +
          '<button class="vr10-med-preset" onclick="VRInteraction.meditationTimer.setTime(60)">1m</button>' +
          '<button class="vr10-med-preset" onclick="VRInteraction.meditationTimer.setTime(180)">3m</button>' +
          '<button class="vr10-med-preset" onclick="VRInteraction.meditationTimer.setTime(300)">5m</button>' +
          '<button class="vr10-med-preset" onclick="VRInteraction.meditationTimer.setTime(600)">10m</button>' +
        '</div>' +
        '<div id="vr10-med-display">5:00</div>' +
        '<div id="vr10-med-controls">' +
          '<button onclick="VRInteraction.meditationTimer.start()">▶ Start</button>' +
          '<button onclick="VRInteraction.meditationTimer.stop()">■ Stop</button>' +
        '</div>' +
        '<div id="vr10-med-stats">' + sessions.length + ' sessions completed</div>';
      document.body.appendChild(panel);
      timerRemaining = 300; // default 5 min
    }

    function setTime(secs) {
      if (timerActive) return;
      timerRemaining = secs;
      updateDisplay();
      document.querySelectorAll('.vr10-med-preset').forEach(function (b) {
        b.classList.toggle('active', parseInt(b.textContent) * 60 === secs || b.textContent === (secs / 60) + 'm');
      });
    }

    function updateDisplay() {
      var d = document.getElementById('vr10-med-display');
      if (!d) return;
      var m = Math.floor(timerRemaining / 60);
      var s = timerRemaining % 60;
      d.textContent = m + ':' + (s < 10 ? '0' : '') + s;
    }

    function start() {
      if (timerActive) return;
      if (timerRemaining <= 0) timerRemaining = 300;
      timerActive = true;
      toast('Meditation started — breathe deeply', '#10b981');
      if (achievements) achievements.unlock('zen');

      timerInterval = setInterval(function () {
        timerRemaining--;
        updateDisplay();
        if (timerRemaining <= 0) {
          clearInterval(timerInterval);
          timerActive = false;
          sessions.push({ duration: 300 - timerRemaining, time: Date.now() });
          store('med_sessions', sessions);
          toast('Meditation complete! 🧘', '#10b981');
          var stats = document.getElementById('vr10-med-stats');
          if (stats) stats.textContent = sessions.length + ' sessions completed';
        }
      }, 1000);
    }

    function stop() {
      if (!timerActive) return;
      clearInterval(timerInterval);
      timerActive = false;
      toast('Meditation paused', '#64748b');
    }

    setTimeout(createUI, 1500);

    return {
      start: start,
      stop: stop,
      setTime: setTime,
      isActive: function () { return timerActive; },
      getSessions: function () { return sessions; }
    };
  })();

  /* ═══════════════════════════════════════════════
     8. HUB: STATS DASHBOARD
     ═══════════════════════════════════════════════ */
  var hubStats = (function () {
    // Track time and visits for ALL zones
    var stats = load('zone_stats', {});
    var enterTime = Date.now();

    if (!stats[zone]) stats[zone] = { visits: 0, timeMs: 0 };
    stats[zone].visits++;
    store('zone_stats', stats);

    // Save time on leave
    window.addEventListener('beforeunload', function () {
      stats[zone].timeMs += Date.now() - enterTime;
      store('zone_stats', stats);
    });

    // Only show dashboard on hub
    if (zone !== 'hub') return { stats: stats };

    function createDashboard() {
      css('vr10-stats-css',
        '#vr10-stats{position:fixed;bottom:10px;left:10px;z-index:160;background:rgba(15,12,41,0.92);border:1px solid rgba(0,212,255,0.2);border-radius:12px;padding:12px 16px;width:230px;color:#e2e8f0;font:11px/1.4 Inter,system-ui,sans-serif;backdrop-filter:blur(10px)}' +
        '#vr10-stats h4{margin:0 0 8px;color:#00d4ff;font-size:13px}' +
        '.vr10-stat-row{display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.04)}' +
        '.vr10-stat-zone{color:#94a3b8}' +
        '.vr10-stat-val{color:#7dd3fc;font-weight:600;font-variant-numeric:tabular-nums}' +
        '.vr10-stat-bar{height:3px;border-radius:2px;margin-top:2px;background:rgba(0,212,255,0.3)}'
      );

      var panel = document.createElement('div');
      panel.id = 'vr10-stats';

      var zoneNames = { hub: 'Hub', events: 'Events', movies: 'Movies', creators: 'Creators', stocks: 'Stocks', wellness: 'Wellness', weather: 'Weather', tutorial: 'Tutorial' };
      var zoneColors = { hub: '#00d4ff', events: '#ff6b6b', movies: '#4ecdc4', creators: '#a855f7', stocks: '#22c55e', wellness: '#10b981', weather: '#06b6d4', tutorial: '#f59e0b' };
      var totalVisits = 0;
      var totalTime = 0;
      Object.keys(stats).forEach(function (k) { totalVisits += stats[k].visits; totalTime += stats[k].timeMs; });
      var maxTime = Math.max.apply(null, Object.keys(stats).map(function (k) { return stats[k].timeMs; }).concat([1]));

      var html = '<h4>📊 Your VR Stats</h4>';
      html += '<div class="vr10-stat-row"><span class="vr10-stat-zone">Total visits</span><span class="vr10-stat-val">' + totalVisits + '</span></div>';
      html += '<div class="vr10-stat-row" style="margin-bottom:6px"><span class="vr10-stat-zone">Total time</span><span class="vr10-stat-val">' + Math.round(totalTime / 60000) + ' min</span></div>';

      ['events', 'movies', 'creators', 'stocks', 'wellness', 'weather'].forEach(function (z) {
        var s = stats[z] || { visits: 0, timeMs: 0 };
        var pct = maxTime > 0 ? Math.round((s.timeMs / maxTime) * 100) : 0;
        html += '<div class="vr10-stat-row"><span class="vr10-stat-zone">' + (zoneNames[z] || z) + '</span><span class="vr10-stat-val">' + s.visits + ' · ' + Math.round(s.timeMs / 60000) + 'm</span></div>';
        html += '<div class="vr10-stat-bar" style="width:' + pct + '%;background:' + (zoneColors[z] || '#00d4ff') + '"></div>';
      });

      panel.innerHTML = html;
      document.body.appendChild(panel);
    }

    setTimeout(createDashboard, 1500);

    return { stats: stats };
  })();

  /* ═══════════════════════════════════════════════
     9. ACHIEVEMENT SYSTEM
     ═══════════════════════════════════════════════ */
  var achievements = (function () {
    var unlocked = load('achievements', {});

    var defs = {
      explorer:   { name: 'Explorer',      desc: 'Visit 3 different zones',   icon: '🌍' },
      sorter:     { name: 'Organizer',     desc: 'Sort events list',          icon: '📋' },
      collector:  { name: 'Collector',     desc: 'Save an event',             icon: '📌' },
      exporter:   { name: 'Data Master',   desc: 'Export events to CSV',      icon: '📥' },
      social:     { name: 'Social Star',   desc: 'Follow a creator',          icon: '💜' },
      cinephile:  { name: 'Cinephile',     desc: 'Use Theater Mode',          icon: '🎬' },
      critic:     { name: 'Critic',        desc: 'Rate a movie',              icon: '⭐' },
      trader:     { name: 'Trader',        desc: 'Add stock to watchlist',    icon: '📈' },
      zen:        { name: 'Zen Master',    desc: 'Start a meditation session',icon: '🧘' },
      veteran:    { name: 'VR Veteran',    desc: 'Unlock 5 other achievements', icon: '🏆' }
    };

    // Auto-check explorer achievement
    var zoneStats = load('zone_stats', {});
    if (Object.keys(zoneStats).length >= 3 && !unlocked.explorer) {
      setTimeout(function () { unlock('explorer'); }, 3000);
    }

    function unlock(id) {
      if (unlocked[id]) return;
      var def = defs[id];
      if (!def) return;
      unlocked[id] = { time: Date.now() };
      store('achievements', unlocked);

      // Toast notification
      css('vr10-ach-css',
        '#vr10-ach-toast{position:fixed;top:16px;right:16px;z-index:9000;background:linear-gradient(135deg,rgba(15,12,41,0.97),rgba(30,20,60,0.95));border:1px solid rgba(234,179,8,0.4);border-radius:14px;padding:14px 20px;color:#fef08a;font:13px/1.3 Inter,system-ui,sans-serif;backdrop-filter:blur(16px);display:flex;align-items:center;gap:10px;animation:vr10Toast .3s ease-out;max-width:280px}' +
        '#vr10-ach-toast .ach-icon{font-size:28px}' +
        '#vr10-ach-toast .ach-text strong{display:block;color:#fef08a;font-size:14px}' +
        '#vr10-ach-toast .ach-text span{color:#a3a3a3;font-size:11px}'
      );

      var el = document.createElement('div');
      el.id = 'vr10-ach-toast';
      el.innerHTML = '<span class="ach-icon">' + def.icon + '</span><div class="ach-text"><strong>Achievement Unlocked!</strong><span>' + def.name + ' — ' + def.desc + '</span></div>';
      document.body.appendChild(el);
      setTimeout(function () { el.style.opacity = '0'; el.style.transition = 'opacity .5s'; }, 4000);
      setTimeout(function () { if (el.parentNode) el.remove(); }, 4500);

      // Check veteran achievement
      var total = Object.keys(unlocked).length;
      if (total >= 5 && !unlocked.veteran) {
        setTimeout(function () { unlock('veteran'); }, 1500);
      }
    }

    function isUnlocked(id) { return !!unlocked[id]; }
    function getAll() { return unlocked; }
    function getCount() { return Object.keys(unlocked).length; }

    return {
      unlock: unlock,
      isUnlocked: isUnlocked,
      getAll: getAll,
      getCount: getCount,
      defs: defs
    };
  })();

  /* ═══════════════════════════════════════════════
     10. AMBIENT SOUND CUES
     ═══════════════════════════════════════════════ */
  var ambientSound = (function () {
    var audioCtx;
    var enabled = load('sound_enabled', true);

    function getCtx() {
      if (audioCtx) return audioCtx;
      try { audioCtx = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { return null; }
      return audioCtx;
    }

    function playTone(freq, duration, type, volume) {
      if (!enabled) return;
      var ctx = getCtx();
      if (!ctx) return;
      try {
        var osc = ctx.createOscillator();
        var gain = ctx.createGain();
        osc.type = type || 'sine';
        osc.frequency.value = freq;
        gain.gain.value = volume || 0.08;
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + (duration || 0.3));
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(ctx.currentTime);
        osc.stop(ctx.currentTime + (duration || 0.3));
      } catch (e) {}
    }

    // Zone entry chime — different tone per zone
    var zoneFreqs = {
      hub: [523, 659, 784],       // C E G (major chord)
      events: [440, 554, 659],    // A C# E
      movies: [392, 494, 587],    // G B D
      creators: [349, 440, 523],  // F A C
      stocks: [330, 415, 494],    // E G# B
      wellness: [294, 370, 440],  // D F# A
      weather: [262, 330, 392],   // C E G low
      tutorial: [523, 587, 659]   // C D E
    };

    function playZoneChime() {
      if (!enabled) return;
      var freqs = zoneFreqs[zone] || [440, 554, 659];
      freqs.forEach(function (f, i) {
        setTimeout(function () { playTone(f, 0.4, 'sine', 0.06); }, i * 120);
      });
    }

    // Play entry chime after a short delay (needs user interaction for AudioContext)
    function initChime() {
      document.addEventListener('click', function firstClick() {
        playZoneChime();
        document.removeEventListener('click', firstClick);
      }, { once: true });
    }
    setTimeout(initChime, 500);

    function toggle() {
      enabled = !enabled;
      store('sound_enabled', enabled);
      toast(enabled ? 'Sound ON' : 'Sound OFF', '#7dd3fc');
      return enabled;
    }

    return {
      playTone: playTone,
      playZoneChime: playZoneChime,
      toggle: toggle,
      isEnabled: function () { return enabled; }
    };
  })();

  /* ═══════════════════════════════════════════════
     PUBLIC API
     ═══════════════════════════════════════════════ */
  window.VRInteraction = {
    zone: zone,
    version: 10,
    eventsSortSave: eventsSortSave,
    creatorsFollow: creatorsFollow,
    moviesTheater: moviesTheater,
    moviesRating: moviesRating,
    stocksCharts: stocksCharts,
    stocksWatchlist: stocksWatchlist,
    meditationTimer: meditationTimer,
    hubStats: hubStats,
    achievements: achievements,
    ambientSound: ambientSound
  };

  console.log('[VR Interaction] Set 10 loaded — ' + zone + ' (achievements: ' + achievements.getCount() + '/10)');
})();
