/**
 * VR Personalization & Social — Set 11
 *
 * 10 personalization, social, and quality-of-life features:
 *
 *  1. Theme Customizer       — 5 selectable color themes (Ctrl+,)
 *  2. Movies Named Playlists — create/manage/switch named playlists
 *  3. Events Social Share    — per-event share buttons + copy link
 *  4. Events Personal Notes  — add/edit notes per event, persisted
 *  5. Weather Multi-City     — switch Toronto/Vancouver/Montreal/Calgary
 *  6. Creator View History   — track views, watch time, analytics
 *  7. Notification Center    — persistent panel with history
 *  8. Stocks Portfolio       — simulated buy/sell, track P&L
 *  9. Cross-Zone Pinboard    — pin items from any zone
 * 10. Hub Quick-Launch       — pinned zone shortcuts on hub
 *
 * Load via <script src="/vr/personalization.js"></script>
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

  function store(k, v) { try { localStorage.setItem('vr11_' + k, JSON.stringify(v)); } catch (e) {} }
  function load(k, d) { try { var v = localStorage.getItem('vr11_' + k); return v ? JSON.parse(v) : d; } catch (e) { return d; } }
  function css(id, t) { if (document.getElementById(id)) return; var s = document.createElement('style'); s.id = id; s.textContent = t; document.head.appendChild(s); }
  function toast(m, c) { c = c || '#7dd3fc'; var t = document.createElement('div'); t.style.cssText = 'position:fixed;top:16px;left:50%;transform:translateX(-50%);z-index:9000;background:rgba(15,12,41,0.95);color:' + c + ';padding:10px 20px;border-radius:10px;font:600 13px/1.3 Inter,system-ui,sans-serif;border:1px solid ' + c + '33;backdrop-filter:blur(10px);pointer-events:none;animation:vr11t .3s ease-out'; t.textContent = m; document.body.appendChild(t); setTimeout(function () { t.style.opacity = '0'; t.style.transition = 'opacity .3s'; }, 2500); setTimeout(function () { if (t.parentNode) t.remove(); }, 3000); }
  css('vr11-base', '@keyframes vr11t{from{opacity:0;transform:translateX(-50%) translateY(-10px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}');

  /* ═══════════════════════════════════════════════
     1. THEME CUSTOMIZER (Ctrl+,)
     ═══════════════════════════════════════════════ */
  var themeCustomizer = (function () {
    var themes = {
      neon:    { accent: '#00d4ff', bg: 'rgba(10,10,26,0.97)', border: 'rgba(0,212,255,0.25)', text: '#7dd3fc', name: 'Neon (default)' },
      ocean:   { accent: '#0ea5e9', bg: 'rgba(8,15,30,0.97)',  border: 'rgba(14,165,233,0.25)', text: '#7dd3fc', name: 'Ocean' },
      forest:  { accent: '#22c55e', bg: 'rgba(8,20,12,0.97)',  border: 'rgba(34,197,94,0.25)',  text: '#86efac', name: 'Forest' },
      sunset:  { accent: '#f97316', bg: 'rgba(25,12,8,0.97)',  border: 'rgba(249,115,22,0.25)', text: '#fdba74', name: 'Sunset' },
      midnight:{ accent: '#a855f7', bg: 'rgba(15,8,30,0.97)',  border: 'rgba(168,85,247,0.25)', text: '#c4b5fd', name: 'Midnight' }
    };
    var current = load('theme', 'neon');

    function apply(id) {
      var t = themes[id] || themes.neon;
      current = id;
      store('theme', id);
      document.body.setAttribute('data-vr-theme', id);
      css('vr11-theme-vars', ':root{--vr-accent:' + t.accent + ';--vr-bg:' + t.bg + ';--vr-border:' + t.border + ';--vr-text:' + t.text + '}');
      css('vr11-theme-apply',
        '[data-vr-theme] .vr-nav-overlay{background:var(--vr-bg)!important;border-color:var(--vr-border)!important}' +
        '[data-vr-theme] .vr-nav-link:hover{color:var(--vr-accent)!important}' +
        '[data-vr-theme] #vr-area-guide{background:var(--vr-bg)!important;border-color:var(--vr-border)!important}'
      );
    }
    apply(current);

    var panelOpen = false;
    function openPanel() {
      if (panelOpen) { closePanel(); return; }
      panelOpen = true;
      css('vr11-theme-css',
        '#vr11-theme{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:600;background:rgba(15,12,41,0.97);border:1px solid rgba(0,212,255,0.25);border-radius:16px;padding:24px;width:300px;color:#e2e8f0;font:13px/1.5 Inter,system-ui,sans-serif;backdrop-filter:blur(16px)}' +
        '#vr11-theme h3{margin:0 0 14px;color:#7dd3fc;font-size:16px}' +
        '.vr11-theme-opt{display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:8px;cursor:pointer;transition:all .2s;border:1px solid transparent;margin-bottom:4px}' +
        '.vr11-theme-opt:hover,.vr11-theme-opt.active{background:rgba(255,255,255,0.06);border-color:rgba(255,255,255,0.1)}' +
        '.vr11-theme-swatch{width:24px;height:24px;border-radius:6px}' +
        '.vr11-theme-close{position:absolute;top:12px;right:16px;background:none;border:none;color:#64748b;font-size:18px;cursor:pointer}'
      );
      var el = document.createElement('div');
      el.id = 'vr11-theme';
      el.setAttribute('role', 'dialog');
      var html = '<h3>🎨 Theme</h3><button class="vr11-theme-close" onclick="VRPersonalization.themeCustomizer.closePanel()">&times;</button>';
      Object.keys(themes).forEach(function (id) {
        var t = themes[id];
        html += '<div class="vr11-theme-opt' + (current === id ? ' active' : '') + '" onclick="VRPersonalization.themeCustomizer.apply(\'' + id + '\');VRPersonalization.themeCustomizer.closePanel()">' +
                '<div class="vr11-theme-swatch" style="background:' + t.accent + '"></div>' +
                '<span>' + t.name + '</span></div>';
      });
      el.innerHTML = html;
      document.body.appendChild(el);
    }
    function closePanel() { panelOpen = false; var p = document.getElementById('vr11-theme'); if (p) p.remove(); }

    document.addEventListener('keydown', function (e) {
      if (e.ctrlKey && e.key === ',') { e.preventDefault(); openPanel(); }
      if (e.key === 'Escape' && panelOpen) closePanel();
    });

    return { apply: apply, openPanel: openPanel, closePanel: closePanel, current: function () { return current; }, themes: themes };
  })();

  /* ═══════════════════════════════════════════════
     2. MOVIES NAMED PLAYLISTS
     ═══════════════════════════════════════════════ */
  var moviesPlaylists = (function () {
    if (zone !== 'movies') return null;
    var playlists = load('playlists', { Default: [] });
    var active = load('active_playlist', 'Default');

    function createUI() {
      css('vr11-pl-css',
        '#vr11-playlists{position:fixed;top:50px;left:10px;z-index:160;background:rgba(15,12,41,0.92);border:1px solid rgba(78,205,196,0.2);border-radius:12px;padding:10px 14px;width:200px;color:#e2e8f0;font:11px/1.4 Inter,system-ui,sans-serif;backdrop-filter:blur(10px)}' +
        '#vr11-playlists h4{margin:0 0 6px;color:#4ecdc4;font-size:12px}' +
        '.vr11-pl-item{display:flex;justify-content:space-between;align-items:center;padding:4px 6px;border-radius:6px;cursor:pointer;transition:all .15s;margin-bottom:2px;font-size:11px}' +
        '.vr11-pl-item:hover,.vr11-pl-item.active{background:rgba(78,205,196,0.1);color:#fff}' +
        '.vr11-pl-item.active{border-left:2px solid #4ecdc4}' +
        '.vr11-pl-count{color:#64748b;font-size:10px}' +
        '.vr11-pl-new{width:100%;margin-top:6px;padding:5px;border-radius:6px;border:1px solid rgba(78,205,196,0.2);background:rgba(78,205,196,0.06);color:#4ecdc4;cursor:pointer;font:600 11px Inter,system-ui,sans-serif}'
      );
      var el = document.createElement('div');
      el.id = 'vr11-playlists';
      render(el);
      document.body.appendChild(el);
    }

    function render(container) {
      container = container || document.getElementById('vr11-playlists');
      if (!container) return;
      var html = '<h4>🎵 Playlists</h4>';
      Object.keys(playlists).forEach(function (name) {
        var count = playlists[name].length;
        html += '<div class="vr11-pl-item' + (name === active ? ' active' : '') + '" onclick="VRPersonalization.moviesPlaylists.switchTo(\'' + name.replace(/'/g, "\\'") + '\')">' +
                '<span>' + name + '</span><span class="vr11-pl-count">' + count + '</span></div>';
      });
      html += '<button class="vr11-pl-new" onclick="VRPersonalization.moviesPlaylists.createNew()">+ New Playlist</button>';
      container.innerHTML = html;
    }

    function createNew() {
      var name = prompt('Playlist name:');
      if (!name || playlists[name]) return;
      playlists[name] = [];
      store('playlists', playlists);
      render();
      toast('Created playlist: ' + name, '#4ecdc4');
    }

    function switchTo(name) {
      if (!playlists[name]) return;
      active = name;
      store('active_playlist', active);
      render();
      toast('Switched to: ' + name, '#4ecdc4');
    }

    function addToPlaylist(title, videoId) {
      if (!playlists[active]) playlists[active] = [];
      if (playlists[active].some(function (i) { return i.videoId === videoId; })) return;
      playlists[active].push({ title: title, videoId: videoId, time: Date.now() });
      store('playlists', playlists);
      render();
      toast('Added to ' + active, '#4ecdc4');
    }

    setTimeout(createUI, 1500);
    return { createNew: createNew, switchTo: switchTo, add: addToPlaylist, getActive: function () { return active; }, getAll: function () { return playlists; } };
  })();

  /* ═══════════════════════════════════════════════
     3. EVENTS SOCIAL SHARE
     ═══════════════════════════════════════════════ */
  var eventsShare = (function () {
    if (zone !== 'events') return null;

    function shareEvent(title, date, url) {
      var text = title + ' — ' + date + '\n' + (url || location.href);
      if (navigator.share) {
        navigator.share({ title: title, text: text, url: url || location.href }).catch(function () {});
      } else {
        copyToClipboard(text);
      }
    }

    function copyToClipboard(text) {
      if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function () { toast('Copied to clipboard!', '#22c55e'); });
      } else {
        var ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove();
        toast('Copied to clipboard!', '#22c55e');
      }
    }

    function getShareHTML(title, date) {
      var encoded = encodeURIComponent(title + ' — ' + date);
      var url = encodeURIComponent(location.href);
      return '<span class="vr11-share-row">' +
        '<button onclick="VRPersonalization.eventsShare.share(\'' + title.replace(/'/g, "\\'") + '\',\'' + date + '\')" title="Share" style="background:none;border:none;color:#7dd3fc;cursor:pointer;font-size:14px">🔗</button>' +
        '<a href="https://twitter.com/intent/tweet?text=' + encoded + '&url=' + url + '" target="_blank" rel="noopener" style="color:#1d9bf0;font-size:14px;text-decoration:none" title="Tweet">𝕏</a>' +
        '</span>';
    }

    return { share: shareEvent, copy: copyToClipboard, getShareHTML: getShareHTML };
  })();

  /* ═══════════════════════════════════════════════
     4. EVENTS PERSONAL NOTES
     ═══════════════════════════════════════════════ */
  var eventsNotes = (function () {
    if (zone !== 'events') return null;
    var notes = load('event_notes', {});

    function createNotesUI() {
      css('vr11-notes-css',
        '#vr11-notes-badge{position:fixed;top:130px;right:10px;z-index:160;background:rgba(15,12,41,0.92);border:1px solid rgba(234,179,8,0.2);border-radius:10px;padding:6px 12px;color:#fbbf24;font:600 11px Inter,system-ui,sans-serif;backdrop-filter:blur(10px);cursor:pointer;transition:all .2s}' +
        '#vr11-notes-badge:hover{border-color:rgba(234,179,8,0.4);color:#fff}' +
        '#vr11-notes-panel{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:500;background:rgba(15,12,41,0.97);border:1px solid rgba(234,179,8,0.3);border-radius:14px;padding:20px;width:min(380px,90vw);max-height:60vh;overflow-y:auto;color:#e2e8f0;font:13px/1.5 Inter,system-ui,sans-serif;backdrop-filter:blur(16px);display:none}' +
        '#vr11-notes-panel.open{display:block}'
      );
      var badge = document.createElement('div');
      badge.id = 'vr11-notes-badge';
      var count = Object.keys(notes).length;
      badge.innerHTML = '📝 ' + count + ' note' + (count !== 1 ? 's' : '');
      badge.addEventListener('click', togglePanel);
      document.body.appendChild(badge);
    }

    function togglePanel() {
      var p = document.getElementById('vr11-notes-panel');
      if (p) { p.classList.toggle('open'); return; }
      p = document.createElement('div');
      p.id = 'vr11-notes-panel';
      p.classList.add('open');
      renderNotes(p);
      document.body.appendChild(p);
    }

    function renderNotes(container) {
      container = container || document.getElementById('vr11-notes-panel');
      if (!container) return;
      var keys = Object.keys(notes);
      var html = '<h3 style="margin:0 0 12px;color:#fbbf24;font-size:15px">📝 My Event Notes (' + keys.length + ')</h3>';
      if (keys.length === 0) html += '<p style="color:#64748b">No notes yet. Add notes from event details.</p>';
      keys.forEach(function (k) {
        var n = notes[k];
        html += '<div style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.06)"><strong style="color:#fbbf24">' + (n.title || k) + '</strong><br><span style="color:#94a3b8;font-size:12px">' + (n.text || '') + '</span></div>';
      });
      html += '<button onclick="this.parentElement.classList.remove(\'open\')" style="margin-top:10px;padding:6px 16px;background:rgba(234,179,8,0.1);color:#fbbf24;border:1px solid rgba(234,179,8,0.2);border-radius:8px;cursor:pointer;font:600 12px Inter,system-ui,sans-serif">Close</button>';
      container.innerHTML = html;
    }

    function setNote(eventId, title, text) {
      notes[eventId] = { title: title, text: text, time: Date.now() };
      store('event_notes', notes);
      var badge = document.getElementById('vr11-notes-badge');
      if (badge) badge.innerHTML = '📝 ' + Object.keys(notes).length + ' notes';
      toast('Note saved', '#fbbf24');
    }

    function getNote(eventId) { return notes[eventId] || null; }
    function removeNote(eventId) { delete notes[eventId]; store('event_notes', notes); }

    setTimeout(createNotesUI, 1500);
    return { set: setNote, get: getNote, remove: removeNote, getAll: function () { return notes; }, toggle: togglePanel };
  })();

  /* ═══════════════════════════════════════════════
     5. WEATHER MULTI-CITY
     ═══════════════════════════════════════════════ */
  var weatherMultiCity = (function () {
    if (zone !== 'weather') return null;
    var cities = {
      toronto:   { name: 'Toronto',   lat: 43.65, lon: -79.38 },
      vancouver: { name: 'Vancouver', lat: 49.28, lon: -123.12 },
      montreal:  { name: 'Montreal',  lat: 45.50, lon: -73.57 },
      calgary:   { name: 'Calgary',   lat: 51.05, lon: -114.07 }
    };
    var current = load('weather_city', 'toronto');

    function createSelector() {
      css('vr11-city-css',
        '#vr11-city-sel{position:fixed;top:50px;right:10px;z-index:160;background:rgba(15,12,41,0.92);border:1px solid rgba(6,182,212,0.25);border-radius:12px;padding:8px;display:flex;gap:4px;backdrop-filter:blur(10px)}' +
        '.vr11-city-btn{padding:5px 10px;border-radius:6px;border:1px solid rgba(6,182,212,0.15);background:transparent;color:#67e8f9;cursor:pointer;font:600 11px Inter,system-ui,sans-serif;transition:all .2s}' +
        '.vr11-city-btn:hover,.vr11-city-btn.active{background:rgba(6,182,212,0.15);border-color:rgba(6,182,212,0.4);color:#fff}'
      );
      var el = document.createElement('div');
      el.id = 'vr11-city-sel';
      Object.keys(cities).forEach(function (id) {
        el.innerHTML += '<button class="vr11-city-btn' + (id === current ? ' active' : '') + '" onclick="VRPersonalization.weatherMultiCity.switchCity(\'' + id + '\')">' + cities[id].name + '</button>';
      });
      document.body.appendChild(el);
    }

    function switchCity(id) {
      if (!cities[id]) return;
      current = id;
      store('weather_city', id);
      document.querySelectorAll('.vr11-city-btn').forEach(function (b) {
        b.classList.toggle('active', b.textContent === cities[id].name);
      });
      toast('Weather: ' + cities[id].name, '#06b6d4');
      // Dispatch event for weather zone to re-fetch
      window.dispatchEvent(new CustomEvent('vr-weather-city-change', { detail: cities[id] }));
    }

    setTimeout(createSelector, 1500);
    return { switchCity: switchCity, getCurrent: function () { return current; }, cities: cities };
  })();

  /* ═══════════════════════════════════════════════
     6. CREATOR VIEW HISTORY
     ═══════════════════════════════════════════════ */
  var creatorHistory = (function () {
    if (zone !== 'creators') return null;
    var history = load('creator_views', []);

    function recordView(creatorId, name) {
      var existing = history.find(function (h) { return h.id === creatorId; });
      if (existing) { existing.views++; existing.lastViewed = Date.now(); }
      else history.unshift({ id: creatorId, name: name, views: 1, lastViewed: Date.now(), totalTimeSec: 0 });
      if (history.length > 50) history = history.slice(0, 50);
      store('creator_views', history);
    }

    function createBadge() {
      css('vr11-cv-css',
        '#vr11-creator-history{position:fixed;bottom:10px;left:10px;z-index:160;background:rgba(15,12,41,0.92);border:1px solid rgba(168,85,247,0.2);border-radius:12px;padding:10px 14px;width:200px;color:#e2e8f0;font:11px/1.4 Inter,system-ui,sans-serif;backdrop-filter:blur(10px)}' +
        '#vr11-creator-history h4{margin:0 0 6px;color:#a855f7;font-size:12px}'
      );
      var el = document.createElement('div');
      el.id = 'vr11-creator-history';
      var html = '<h4>👁 Recently Viewed</h4>';
      if (history.length === 0) html += '<div style="color:#64748b;font-size:10px">No creators viewed yet</div>';
      history.slice(0, 5).forEach(function (h) {
        html += '<div style="padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.04);display:flex;justify-content:space-between"><span>' + h.name + '</span><span style="color:#64748b">' + h.views + 'x</span></div>';
      });
      el.innerHTML = html;
      document.body.appendChild(el);
    }

    setTimeout(createBadge, 1500);
    return { record: recordView, getHistory: function () { return history; } };
  })();

  /* ═══════════════════════════════════════════════
     7. NOTIFICATION CENTER
     ═══════════════════════════════════════════════ */
  var notifications = (function () {
    var items = load('notifications', []);
    var unread = items.filter(function (n) { return !n.read; }).length;

    function createBell() {
      css('vr11-notif-css',
        '#vr11-notif-bell{position:fixed;top:8px;left:60px;z-index:200;background:rgba(15,12,41,0.9);border:1px solid rgba(0,212,255,0.2);border-radius:10px;padding:5px 10px;color:#7dd3fc;font:600 12px Inter,system-ui,sans-serif;cursor:pointer;transition:all .2s;backdrop-filter:blur(10px)}' +
        '#vr11-notif-bell:hover{border-color:rgba(0,212,255,0.4);color:#fff}' +
        '#vr11-notif-bell .badge{background:#ef4444;color:#fff;border-radius:8px;padding:1px 5px;font-size:10px;margin-left:4px}' +
        '#vr11-notif-panel{position:fixed;top:42px;left:60px;z-index:200;background:rgba(15,12,41,0.97);border:1px solid rgba(0,212,255,0.25);border-radius:12px;padding:12px;width:260px;max-height:300px;overflow-y:auto;color:#e2e8f0;font:12px/1.4 Inter,system-ui,sans-serif;backdrop-filter:blur(16px);display:none}' +
        '#vr11-notif-panel.open{display:block}' +
        '.vr11-notif-item{padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:11px}' +
        '.vr11-notif-item.unread{border-left:2px solid #00d4ff;padding-left:8px}' +
        '.vr11-notif-item .time{color:#64748b;font-size:10px}'
      );

      var bell = document.createElement('div');
      bell.id = 'vr11-notif-bell';
      bell.innerHTML = '🔔' + (unread > 0 ? '<span class="badge">' + unread + '</span>' : '');
      bell.addEventListener('click', togglePanel);
      document.body.appendChild(bell);
    }

    function togglePanel() {
      var p = document.getElementById('vr11-notif-panel');
      if (p) { p.classList.toggle('open'); if (p.classList.contains('open')) markAllRead(); return; }
      p = document.createElement('div');
      p.id = 'vr11-notif-panel';
      p.classList.add('open');
      renderPanel(p);
      document.body.appendChild(p);
      markAllRead();
    }

    function renderPanel(container) {
      container = container || document.getElementById('vr11-notif-panel');
      if (!container) return;
      var html = '<div style="font-weight:700;color:#7dd3fc;margin-bottom:8px;font-size:13px">Notifications</div>';
      if (items.length === 0) html += '<div style="color:#64748b;font-size:11px">No notifications</div>';
      items.slice(0, 15).forEach(function (n) {
        var ago = Math.round((Date.now() - n.time) / 60000);
        var ts = ago < 60 ? ago + 'm ago' : Math.round(ago / 60) + 'h ago';
        html += '<div class="vr11-notif-item' + (!n.read ? ' unread' : '') + '">' + n.text + '<div class="time">' + ts + '</div></div>';
      });
      if (items.length > 0) html += '<button onclick="VRPersonalization.notifications.clear()" style="margin-top:6px;padding:4px 10px;background:rgba(239,68,68,0.1);color:#fca5a5;border:1px solid rgba(239,68,68,0.2);border-radius:6px;cursor:pointer;font:600 10px Inter,system-ui,sans-serif">Clear All</button>';
      container.innerHTML = html;
    }

    function add(text, type) {
      items.unshift({ text: text, type: type || 'info', time: Date.now(), read: false });
      if (items.length > 50) items = items.slice(0, 50);
      store('notifications', items);
      unread++;
      updateBell();
    }

    function markAllRead() {
      items.forEach(function (n) { n.read = true; });
      store('notifications', items);
      unread = 0;
      updateBell();
    }

    function updateBell() {
      var bell = document.getElementById('vr11-notif-bell');
      if (bell) bell.innerHTML = '🔔' + (unread > 0 ? '<span class="badge">' + unread + '</span>' : '');
    }

    function clear() {
      items = [];
      store('notifications', items);
      unread = 0;
      updateBell();
      renderPanel();
      toast('Notifications cleared', '#64748b');
    }

    // Auto-generate welcome notification
    if (items.length === 0) {
      add('Welcome to VR! Explore all zones to unlock achievements.', 'welcome');
    }

    setTimeout(createBell, 1000);
    return { add: add, clear: clear, toggle: togglePanel, getAll: function () { return items; }, unreadCount: function () { return unread; } };
  })();

  /* ═══════════════════════════════════════════════
     8. STOCKS PORTFOLIO
     ═══════════════════════════════════════════════ */
  var stocksPortfolio = (function () {
    if (zone !== 'stocks') return null;
    var portfolio = load('portfolio', []);
    var basePrices = { AAPL: 195, MSFT: 420, NVDA: 850, TSLA: 245, AMZN: 185, GOOGL: 165, SPY: 520, QQQ: 460 };

    function createUI() {
      css('vr11-port-css',
        '#vr11-portfolio{position:fixed;bottom:10px;left:10px;z-index:160;background:rgba(15,12,41,0.92);border:1px solid rgba(34,197,94,0.2);border-radius:12px;padding:10px 14px;width:220px;color:#e2e8f0;font:11px/1.4 Inter,system-ui,sans-serif;backdrop-filter:blur(10px)}' +
        '#vr11-portfolio h4{margin:0 0 6px;color:#22c55e;font-size:12px}' +
        '.vr11-port-item{display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.04);font-size:11px}' +
        '.vr11-port-pnl{font-weight:600}' +
        '.vr11-port-buy{margin-top:6px;width:100%;padding:5px;border-radius:6px;border:1px solid rgba(34,197,94,0.2);background:rgba(34,197,94,0.06);color:#86efac;cursor:pointer;font:600 11px Inter,system-ui,sans-serif}'
      );
      var el = document.createElement('div');
      el.id = 'vr11-portfolio';
      renderPortfolio(el);
      document.body.appendChild(el);
    }

    function renderPortfolio(container) {
      container = container || document.getElementById('vr11-portfolio');
      if (!container) return;
      var totalPnl = 0;
      var html = '<h4>💼 Portfolio</h4>';
      if (portfolio.length === 0) html += '<div style="color:#64748b;font-size:10px">No positions yet</div>';
      portfolio.forEach(function (p) {
        var current = basePrices[p.ticker] * (1 + (Math.random() - 0.48) * 0.05);
        var pnl = (current - p.buyPrice) * p.shares;
        totalPnl += pnl;
        var color = pnl >= 0 ? '#22c55e' : '#ef4444';
        var sign = pnl >= 0 ? '+' : '';
        html += '<div class="vr11-port-item"><span>' + p.ticker + ' ×' + p.shares + '</span><span class="vr11-port-pnl" style="color:' + color + '">' + sign + pnl.toFixed(2) + '</span></div>';
      });
      if (portfolio.length > 0) {
        var tColor = totalPnl >= 0 ? '#22c55e' : '#ef4444';
        html += '<div style="margin-top:4px;font-weight:700;text-align:right;color:' + tColor + '">Total: ' + (totalPnl >= 0 ? '+' : '') + totalPnl.toFixed(2) + '</div>';
      }
      html += '<button class="vr11-port-buy" onclick="VRPersonalization.stocksPortfolio.buyRandom()">📈 Buy Random Stock</button>';
      container.innerHTML = html;
    }

    function buy(ticker, shares) {
      var price = basePrices[ticker] || 100;
      portfolio.push({ ticker: ticker, shares: shares || 10, buyPrice: price, time: Date.now() });
      store('portfolio', portfolio);
      renderPortfolio();
      toast('Bought ' + shares + ' ' + ticker + ' @ $' + price, '#22c55e');
      if (notifications) notifications.add('Bought ' + shares + ' shares of ' + ticker, 'trade');
    }

    function buyRandom() {
      var tickers = Object.keys(basePrices);
      var t = tickers[Math.floor(Math.random() * tickers.length)];
      buy(t, Math.floor(Math.random() * 20) + 5);
    }

    // Refresh P&L every 8s
    setInterval(function () { renderPortfolio(); }, 8000);

    setTimeout(createUI, 1500);
    return { buy: buy, buyRandom: buyRandom, getPortfolio: function () { return portfolio; }, clear: function () { portfolio = []; store('portfolio', []); renderPortfolio(); } };
  })();

  /* ═══════════════════════════════════════════════
     9. CROSS-ZONE PINBOARD
     ═══════════════════════════════════════════════ */
  var pinboard = (function () {
    var pins = load('pinboard', []);

    function pin(item) {
      // item = { type, title, zone, data }
      var id = (item.type + '_' + item.title).replace(/\s/g, '_').substring(0, 80);
      if (pins.some(function (p) { return p.id === id; })) { toast('Already pinned', '#64748b'); return; }
      pins.push({ id: id, type: item.type || 'item', title: item.title, zone: item.zone || zone, data: item.data || {}, time: Date.now() });
      if (pins.length > 30) pins = pins.slice(0, 30);
      store('pinboard', pins);
      toast('Pinned: ' + item.title, '#f59e0b');
      updateBadge();
    }

    function unpin(id) {
      pins = pins.filter(function (p) { return p.id !== id; });
      store('pinboard', pins);
      updateBadge();
    }

    function createBadge() {
      css('vr11-pin-css',
        '#vr11-pin-badge{position:fixed;top:8px;left:120px;z-index:200;background:rgba(15,12,41,0.9);border:1px solid rgba(245,158,11,0.2);border-radius:10px;padding:5px 10px;color:#f59e0b;font:600 12px Inter,system-ui,sans-serif;cursor:pointer;transition:all .2s;backdrop-filter:blur(10px)}' +
        '#vr11-pin-badge:hover{border-color:rgba(245,158,11,0.4);color:#fff}' +
        '#vr11-pin-panel{position:fixed;top:42px;left:120px;z-index:200;background:rgba(15,12,41,0.97);border:1px solid rgba(245,158,11,0.25);border-radius:12px;padding:12px;width:250px;max-height:300px;overflow-y:auto;color:#e2e8f0;font:12px/1.4 Inter,system-ui,sans-serif;backdrop-filter:blur(16px);display:none}' +
        '#vr11-pin-panel.open{display:block}' +
        '.vr11-pin-item{display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:11px}' +
        '.vr11-pin-zone{color:#64748b;font-size:10px;text-transform:capitalize}'
      );
      var badge = document.createElement('div');
      badge.id = 'vr11-pin-badge';
      badge.innerHTML = '📌 ' + pins.length;
      badge.addEventListener('click', togglePanel);
      document.body.appendChild(badge);
    }

    function updateBadge() {
      var b = document.getElementById('vr11-pin-badge');
      if (b) b.innerHTML = '📌 ' + pins.length;
    }

    function togglePanel() {
      var p = document.getElementById('vr11-pin-panel');
      if (p) { p.classList.toggle('open'); return; }
      p = document.createElement('div');
      p.id = 'vr11-pin-panel';
      p.classList.add('open');
      renderPanel(p);
      document.body.appendChild(p);
    }

    function renderPanel(container) {
      container = container || document.getElementById('vr11-pin-panel');
      if (!container) return;
      var html = '<div style="font-weight:700;color:#f59e0b;margin-bottom:8px;font-size:13px">📌 Pinboard (' + pins.length + ')</div>';
      if (pins.length === 0) html += '<div style="color:#64748b;font-size:11px">Pin items from any zone</div>';
      pins.forEach(function (p) {
        html += '<div class="vr11-pin-item"><div><strong>' + p.title + '</strong><br><span class="vr11-pin-zone">' + p.zone + ' · ' + p.type + '</span></div>' +
                '<button onclick="VRPersonalization.pinboard.unpin(\'' + p.id + '\')" style="background:none;border:none;color:#ef4444;cursor:pointer;opacity:0.6;font-size:12px" title="Unpin">✕</button></div>';
      });
      container.innerHTML = html;
    }

    setTimeout(createBadge, 1000);
    return { pin: pin, unpin: unpin, getPins: function () { return pins; }, toggle: togglePanel };
  })();

  /* ═══════════════════════════════════════════════
     10. HUB QUICK-LAUNCH FAVORITES
     ═══════════════════════════════════════════════ */
  var hubQuickLaunch = (function () {
    if (zone !== 'hub') return null;
    var favorites = load('hub_favorites', ['events', 'movies', 'creators', 'games', 'fightgame']);
    var zoneUrls = { events: '/vr/events/', movies: '/vr/movies.html', creators: '/vr/creators.html', stocks: '/vr/stocks-zone.html', wellness: '/vr/wellness/', weather: '/vr/weather-zone.html', games: '/vr/game-arena/', tictactoe: '/vr/game-arena/tic-tac-toe.html', soccer: '/vr/game-arena/soccer-shootout.html', fightgame: '/FIGHTGAME/', '2xko': '/2xko/', antrush: '/vr/ant-rush/' };
    var zoneColors = { events: '#ff6b6b', movies: '#4ecdc4', creators: '#a855f7', stocks: '#22c55e', wellness: '#10b981', weather: '#06b6d4', games: '#8b5cf6', tictactoe: '#8b5cf6', soccer: '#34d399', fightgame: '#ef4444', '2xko': '#f97316', antrush: '#ff6b35' };

    function createBar() {
      css('vr11-ql-css',
        '#vr11-quick-launch{position:fixed;bottom:10px;left:50%;transform:translateX(-50%);z-index:160;display:flex;gap:6px;background:rgba(15,12,41,0.92);border:1px solid rgba(0,212,255,0.15);border-radius:14px;padding:8px 16px;backdrop-filter:blur(10px)}' +
        '.vr11-ql-btn{padding:6px 14px;border-radius:8px;border:1px solid rgba(255,255,255,0.08);background:rgba(255,255,255,0.04);color:#94a3b8;cursor:pointer;font:600 11px Inter,system-ui,sans-serif;transition:all .2s;text-transform:capitalize}' +
        '.vr11-ql-btn:hover{color:#fff;border-color:rgba(0,212,255,0.3);background:rgba(255,255,255,0.08)}'
      );
      var bar = document.createElement('div');
      bar.id = 'vr11-quick-launch';
      favorites.forEach(function (z) {
        var btn = document.createElement('button');
        btn.className = 'vr11-ql-btn';
        btn.textContent = z;
        btn.style.borderColor = (zoneColors[z] || '#00d4ff') + '33';
        btn.addEventListener('click', function () { location.href = zoneUrls[z] || '/vr/'; });
        btn.addEventListener('mouseenter', function () { btn.style.color = zoneColors[z] || '#fff'; });
        btn.addEventListener('mouseleave', function () { btn.style.color = '#94a3b8'; });
        bar.appendChild(btn);
      });
      document.body.appendChild(bar);
    }

    setTimeout(createBar, 1500);
    return { getFavorites: function () { return favorites; }, setFavorites: function (f) { favorites = f; store('hub_favorites', f); } };
  })();

  /* ═══════════════════════════════════════════════
     PUBLIC API
     ═══════════════════════════════════════════════ */
  window.VRPersonalization = {
    zone: zone,
    version: 11,
    themeCustomizer: themeCustomizer,
    moviesPlaylists: moviesPlaylists,
    eventsShare: eventsShare,
    eventsNotes: eventsNotes,
    weatherMultiCity: weatherMultiCity,
    creatorHistory: creatorHistory,
    notifications: notifications,
    stocksPortfolio: stocksPortfolio,
    pinboard: pinboard,
    hubQuickLaunch: hubQuickLaunch
  };

  console.log('[VR Personalization] Set 11 loaded — ' + zone + ' (theme: ' + themeCustomizer.current() + ')');
})();
