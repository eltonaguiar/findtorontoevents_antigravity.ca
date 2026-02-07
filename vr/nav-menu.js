/**
 * VR Zone — Global Navigation Menu + Ambient Music Player
 *
 * Features:
 *   - Current zone indicator + live clock
 *   - Navigate all 7 VR zones (current zone highlighted)
 *   - Context-aware section shortcuts per zone
 *   - Built-in ambient music player (SomaFM copyright-free streams)
 *   - Play/pause, skip station, volume, genre select
 *   - Works in 2D (overlay) and 3D (VR in-scene)
 *   - Toggle: M / Tab / Menu button on Quest controller
 */
(function () {
  'use strict';

  /* ── Zone definitions ── */
  var ZONES = [
    { id: 'hub',      name: 'VR Hub',               emoji: '\uD83C\uDFE0', url: '/vr/',                  color: '#00d4ff' },
    { id: 'events',   name: 'Events Explorer',       emoji: '\uD83D\uDCC5', url: '/vr/events/',           color: '#ff6b6b' },
    { id: 'movies',   name: 'Movie Theater',          emoji: '\uD83C\uDFAC', url: '/vr/movies.html',       color: '#4ecdc4' },
    { id: 'creators', name: 'Live Creators',          emoji: '\uD83D\uDCFA', url: '/vr/creators.html',     color: '#a855f7' },
    { id: 'stocks',   name: 'Trading Floor',          emoji: '\uD83D\uDCC8', url: '/vr/stocks-zone.html',  color: '#22c55e' },
    { id: 'wellness', name: 'Wellness Garden',        emoji: '\uD83C\uDF3F', url: '/vr/wellness/',         color: '#f59e0b' },
    { id: 'weather',  name: 'Weather Observatory',    emoji: '\u26C5',       url: '/vr/weather-zone.html', color: '#06b6d4' },
    { id: 'tutorial', name: 'Tutorial',               emoji: '\u2753',       url: '/vr/tutorial/',         color: '#f59e0b' }
  ];

  /* ── Music stations (SomaFM — copyright-free, listener-supported) ── */
  var STATIONS = [
    { id: 'groovesalad', name: 'Groove Salad',    genre: 'Ambient Chill',     url: 'https://ice1.somafm.com/groovesalad-128-mp3',   color: '#22c55e' },
    { id: 'spacestation', name: 'Space Station',   genre: 'Mid-tempo Space',   url: 'https://ice1.somafm.com/spacestation-128-mp3',  color: '#6366f1' },
    { id: 'dronezone',   name: 'Drone Zone',       genre: 'Dark Ambient',      url: 'https://ice1.somafm.com/dronezone-128-mp3',     color: '#475569' },
    { id: 'lush',        name: 'Lush',             genre: 'Downtempo Vocals',  url: 'https://ice1.somafm.com/lush-128-mp3',          color: '#ec4899' },
    { id: 'deepspace',   name: 'Deep Space One',   genre: 'Deep Ambient',      url: 'https://ice1.somafm.com/deepspaceone-128-mp3',  color: '#1e293b' },
    { id: 'vaporwaves',  name: 'Vaporwaves',       genre: 'Vaporwave',         url: 'https://ice1.somafm.com/vaporwaves-128-mp3',    color: '#f472b6' }
  ];

  /* ── Context-specific section actions per zone ── */
  var SECTION_ACTIONS = {
    hub:      [{ label: 'Reset Position',    action: 'resetPos' },   { label: 'Toggle Labels',   action: 'toggleLabels' }],
    events:   [{ label: 'Next Page',         action: 'nextPage' },   { label: 'Prev Page',       action: 'prevPage' },    { label: 'Filter',  action: 'filter' }],
    movies:   [{ label: 'Play Trailer',      action: 'playTrailer' },{ label: 'Next Movie',      action: 'nextMovie' },   { label: 'Categories', action: 'categories' }],
    creators: [{ label: 'Refresh Live',      action: 'refreshLive' },{ label: 'Filter Platform',  action: 'filterPlat' }, { label: 'Next Page',  action: 'nextPage' }],
    stocks:   [{ label: 'Refresh Prices',    action: 'refresh' }],
    wellness: [{ label: 'Breathing Exercise', action: 'breathe' },   { label: 'Ambient Sounds',  action: 'ambient' }],
    weather:  [{ label: 'Refresh Weather',   action: 'refresh' }],
    tutorial: [{ label: 'Restart Tutorial',  action: 'resetPos' }]
  };

  /* ── State ── */
  var menuOpen = false;
  var vrMenuEntity = null;
  var audio = null;
  var currentStationIdx = 0;
  var musicPlaying = false;
  var musicVolume = 0.4;
  var clockInterval = null;

  /* ── Session Timer (Quick-Win QW-002) ── */
  var SESSION_START_KEY = 'vr_session_start';
  if (!sessionStorage.getItem(SESSION_START_KEY)) {
    sessionStorage.setItem(SESSION_START_KEY, Date.now().toString());
  }
  function getSessionDuration() {
    var start = parseInt(sessionStorage.getItem(SESSION_START_KEY)) || Date.now();
    var elapsed = Math.floor((Date.now() - start) / 1000);
    var h = Math.floor(elapsed / 3600);
    var m = Math.floor((elapsed % 3600) / 60);
    var s = elapsed % 60;
    if (h > 0) return h + 'h ' + (m < 10 ? '0' : '') + m + 'm';
    if (m > 0) return m + 'm ' + (s < 10 ? '0' : '') + s + 's';
    return s + 's';
  }

  /* ── Zone Visit Tracking (Quick-Win QW-003) ── */
  var VISITED_KEY = 'vr_visited_zones';
  function markZoneVisited(zoneId) {
    try {
      var visited = JSON.parse(localStorage.getItem(VISITED_KEY)) || {};
      visited[zoneId] = Date.now();
      localStorage.setItem(VISITED_KEY, JSON.stringify(visited));
    } catch (e) { /* ignore */ }
  }

  /* ── Detect current zone ── */
  function getCurrentZone() {
    var path = window.location.pathname;
    for (var i = 0; i < ZONES.length; i++) {
      if (ZONES[i].id === 'hub' && (path === '/vr/' || path === '/vr/index.html')) return ZONES[i];
      if (ZONES[i].id !== 'hub' && path.indexOf(ZONES[i].url.replace(/\/$/, '')) !== -1) return ZONES[i];
    }
    return ZONES[0];
  }

  var currentZone = getCurrentZone();

  // Mark this zone as visited (QW-003)
  markZoneVisited(currentZone.id);

  /* ── Format time ── */
  function formatTime() {
    var d = new Date();
    var h = d.getHours();
    var m = d.getMinutes();
    var ampm = h >= 12 ? 'PM' : 'AM';
    h = h % 12 || 12;
    return h + ':' + (m < 10 ? '0' : '') + m + ' ' + ampm;
  }

  function formatDate() {
    var d = new Date();
    var days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
    var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return days[d.getDay()] + ', ' + months[d.getMonth()] + ' ' + d.getDate();
  }

  /* ═══════════════════════════════════════════
     MUSIC PLAYER
     ═══════════════════════════════════════════ */
  function initAudio() {
    if (audio) return;
    audio = new Audio();
    audio.crossOrigin = 'anonymous';
    audio.volume = musicVolume;
    audio.preload = 'none';
  }

  function playStation(idx) {
    initAudio();
    if (idx < 0) idx = STATIONS.length - 1;
    if (idx >= STATIONS.length) idx = 0;
    currentStationIdx = idx;
    audio.src = STATIONS[idx].url;
    audio.load();
    audio.play().then(function () {
      musicPlaying = true;
      updateMusicUI();
    }).catch(function (e) {
      console.warn('[Music] Playback blocked:', e.message);
      musicPlaying = false;
      updateMusicUI();
    });
  }

  function toggleMusic() {
    initAudio();
    if (musicPlaying) {
      audio.pause();
      musicPlaying = false;
    } else {
      if (!audio.src || audio.src === '') {
        playStation(currentStationIdx);
        return;
      }
      audio.play().then(function () { musicPlaying = true; updateMusicUI(); })
                   .catch(function () { musicPlaying = false; updateMusicUI(); });
    }
    updateMusicUI();
  }

  function nextStation() { playStation(currentStationIdx + 1); }
  function prevStation() { playStation(currentStationIdx - 1); }

  function setVolume(v) {
    musicVolume = Math.max(0, Math.min(1, v));
    if (audio) audio.volume = musicVolume;
    updateMusicUI();
  }

  /* ── Fire section action ── */
  function fireSectionAction(actionId) {
    closeNavMenu();
    switch (actionId) {
      case 'resetPos':
        var rig = document.getElementById('rig') || document.getElementById('camera-rig');
        if (rig) rig.setAttribute('position', '0 1.6 0');
        break;
      case 'nextPage':
        if (typeof window.nextPage === 'function') window.nextPage();
        break;
      case 'prevPage':
        if (typeof window.prevPage === 'function') window.prevPage();
        break;
      case 'refreshLive':
        if (typeof window.refreshLiveStatus === 'function') window.refreshLiveStatus();
        break;
      case 'filterPlat':
        var strip = document.getElementById('platform-strip');
        if (strip) strip.scrollIntoView({ behavior: 'smooth' });
        break;
      case 'playTrailer':
        if (typeof window.playSelectedTrailer === 'function') window.playSelectedTrailer();
        break;
      case 'nextMovie':
        if (typeof window.selectMovie === 'function') window.selectMovie((window._selectedIdx || 0) + 1);
        break;
      case 'categories':
        var catBar = document.getElementById('category-bar');
        if (catBar) catBar.scrollIntoView({ behavior: 'smooth' });
        break;
      case 'filter':
        var fBar = document.querySelector('.filter-bar, #filter-bar, .filters');
        if (fBar) fBar.scrollIntoView({ behavior: 'smooth' });
        break;
      case 'refresh':
        if (typeof window.refreshData === 'function') window.refreshData();
        else if (typeof window.refreshLiveStatus === 'function') window.refreshLiveStatus();
        break;
      case 'breathe':
        if (typeof window.startBreathing === 'function') window.startBreathing();
        break;
      case 'ambient':
        toggleMusic();
        break;
      case 'toggleLabels':
        document.querySelectorAll('a-text[value]').forEach(function (t) {
          t.setAttribute('visible', t.getAttribute('visible') === 'false' ? 'true' : 'false');
        });
        break;
    }
  }

  /* ═══════════════════════════════════════════
     2D MENU (Desktop / Mobile overlay)
     ═══════════════════════════════════════════ */
  function create2DMenu() {
    if (document.getElementById('vr-nav-menu-2d')) return;

    var zoneHTML = ZONES.map(function (z) {
      var isCurrent = z.id === currentZone.id;
      return '<a href="' + z.url + '" class="vr-nav-zone' + (isCurrent ? ' current' : '') +
             '" style="--zone-color:' + z.color + '">' +
             '<span class="vr-nav-emoji">' + z.emoji + '</span>' +
             '<span class="vr-nav-name">' + z.name + '</span>' +
             (isCurrent ? '<span class="vr-nav-here">HERE</span>' : '<span class="vr-nav-arrow">&rarr;</span>') +
             '</a>';
    }).join('');

    var sectionHTML = '';
    var actions = SECTION_ACTIONS[currentZone.id] || [];
    if (actions.length > 0) {
      sectionHTML = '<div class="vr-nav-section-label">' + currentZone.name + ' Actions</div>' +
        '<div class="vr-nav-section-btns">' +
        actions.map(function (a) {
          return '<button class="vr-nav-section-btn" onclick="window._vrMenuAction(\'' + a.action + '\')">' + a.label + '</button>';
        }).join('') + '</div>';
    }

    var stationsHTML = STATIONS.map(function (s, i) {
      return '<button class="vr-music-station' + (i === currentStationIdx ? ' active' : '') +
             '" data-idx="' + i + '" style="--st-color:' + s.color + '">' +
             '<span class="st-name">' + s.name + '</span>' +
             '<span class="st-genre">' + s.genre + '</span></button>';
    }).join('');

    var menu = document.createElement('div');
    menu.id = 'vr-nav-menu-2d';
    menu.innerHTML =
      '<div class="vr-nav-overlay" onclick="closeNavMenu()"></div>' +
      '<div class="vr-nav-panel">' +
        // Header: zone name + clock
        '<div class="vr-nav-header">' +
          '<div class="vr-nav-header-left">' +
            '<span class="vr-nav-current-dot" style="background:' + currentZone.color + '"></span>' +
            '<span class="vr-nav-current-zone">' + currentZone.emoji + ' ' + currentZone.name + '</span>' +
          '</div>' +
          '<div class="vr-nav-header-right">' +
            '<span class="vr-nav-session" id="vr-session" title="Session duration">' + getSessionDuration() + '</span>' +
            '<span class="vr-nav-clock" id="vr-clock">' + formatTime() + '</span>' +
            '<button class="vr-nav-close" onclick="closeNavMenu()">&#x2715;</button>' +
          '</div>' +
        '</div>' +
        '<div class="vr-nav-date" id="vr-date">' + formatDate() + '</div>' +

        // Section-specific actions
        sectionHTML +

        // Area Guide button
        '<div class="vr-nav-section-label">Area Guide</div>' +
        '<div class="vr-nav-guide-row">' +
          '<button class="vr-nav-guide-btn" onclick="closeNavMenu();if(window.VRAreaGuide)VRAreaGuide.show()" title="Learn about this zone">' +
            '<span class="guide-btn-icon">&#x1F4D6;</span> About This Zone' +
          '</button>' +
          '<button class="vr-nav-guide-btn vr-nav-guide-speak" onclick="closeNavMenu();if(window.VRAreaGuide)VRAreaGuide.speakGuide()" title="Hear zone description">' +
            '<span class="guide-btn-icon">&#x1F50A;</span> Read Aloud' +
          '</button>' +
        '</div>' +

        // Zone navigation
        '<div class="vr-nav-section-label">Navigate</div>' +
        '<div class="vr-nav-zones">' + zoneHTML + '</div>' +

        // Music player
        '<div class="vr-nav-section-label">Ambient Music</div>' +
        '<div class="vr-music-player">' +
          '<div class="vr-music-controls">' +
            '<button class="vr-music-btn" id="vr-music-prev" title="Previous">&laquo;</button>' +
            '<button class="vr-music-btn vr-music-play" id="vr-music-toggle" title="Play/Pause">&#9654;</button>' +
            '<button class="vr-music-btn" id="vr-music-next" title="Next">&raquo;</button>' +
            '<input type="range" class="vr-music-vol" id="vr-music-vol" min="0" max="100" value="' + Math.round(musicVolume * 100) + '" title="Volume">' +
          '</div>' +
          '<div class="vr-music-now" id="vr-music-now">Not playing</div>' +
          '<div class="vr-music-stations">' + stationsHTML + '</div>' +
          '<div class="vr-music-credit">Streams by <a href="https://somafm.com" target="_blank" rel="noopener">SomaFM</a> &mdash; copyright-free</div>' +
        '</div>' +

        // Footer
        '<div class="vr-nav-hint">' +
          'Press <kbd>M</kbd> or <kbd>Tab</kbd> to toggle &bull; <kbd>G</kbd> Area Guide &bull; <kbd>Esc</kbd> to close' +
        '</div>' +
      '</div>';

    // Inject styles
    var style = document.createElement('style');
    style.textContent = getMenuCSS();
    document.head.appendChild(style);
    document.body.appendChild(menu);

    // Bind music controls
    document.getElementById('vr-music-toggle').onclick = function () { toggleMusic(); };
    document.getElementById('vr-music-next').onclick = function () { nextStation(); };
    document.getElementById('vr-music-prev').onclick = function () { prevStation(); };
    document.getElementById('vr-music-vol').oninput = function () { setVolume(this.value / 100); };

    // Bind station buttons
    menu.querySelectorAll('.vr-music-station').forEach(function (btn) {
      btn.onclick = function () { playStation(parseInt(btn.getAttribute('data-idx'))); };
    });

    // Floating menu button
    var fab = document.createElement('button');
    fab.id = 'vr-nav-floating-btn';
    fab.innerHTML = '<span class="fab-icon">&#9776;</span>';
    fab.title = 'Menu (M)';
    fab.onclick = function () { toggleNavMenu(); };
    document.body.appendChild(fab);

    // Start clock + session timer update
    clockInterval = setInterval(function () {
      var el = document.getElementById('vr-clock');
      if (el) el.textContent = formatTime();
      var del = document.getElementById('vr-date');
      if (del) del.textContent = formatDate();
      var sel = document.getElementById('vr-session');
      if (sel) sel.textContent = getSessionDuration();
    }, 5000);
  }

  /* ── Update music UI state ── */
  function updateMusicUI() {
    var toggleBtn = document.getElementById('vr-music-toggle');
    if (toggleBtn) toggleBtn.innerHTML = musicPlaying ? '&#10074;&#10074;' : '&#9654;';

    var nowEl = document.getElementById('vr-music-now');
    if (nowEl) {
      if (musicPlaying) {
        var st = STATIONS[currentStationIdx];
        nowEl.innerHTML = '<span style="color:' + st.color + '">' + st.name + '</span> &mdash; ' + st.genre;
      } else {
        nowEl.textContent = 'Paused';
      }
    }

    // Highlight active station
    document.querySelectorAll('.vr-music-station').forEach(function (btn, i) {
      btn.classList.toggle('active', i === currentStationIdx);
    });
  }

  /* ── Public action bridge ── */
  window._vrMenuAction = function (actionId) { fireSectionAction(actionId); };

  /* ═══════════════════════════════════════════
     3D VR MENU (In-Scene)
     ═══════════════════════════════════════════ */
  function createVRMenu() {
    var scene = document.querySelector('a-scene');
    if (!scene || document.getElementById('vr-nav-menu-vr')) return;

    var ent = document.createElement('a-entity');
    ent.id = 'vr-nav-menu-vr';
    ent.setAttribute('position', '0 2 -3');
    ent.setAttribute('visible', 'false');

    var html = '';
    // Background panel
    html += '<a-plane width="4.2" height="6.5" color="#0a0a1a" opacity="0.95" material="shader: flat"></a-plane>';
    html += '<a-plane width="4.22" height="6.52" color="#00d4ff" opacity="0.4" position="0 0 -0.005" material="shader: flat; wireframe: true"></a-plane>';

    // Header: current zone + clock
    html += '<a-text value="' + currentZone.emoji + ' ' + currentZone.name.toUpperCase() + '" position="0 2.8 0.02" align="center" width="6" color="' + currentZone.color + '"></a-text>';
    html += '<a-text id="vr-menu-clock" value="' + formatTime() + '" position="1.6 2.8 0.02" align="right" width="3.5" color="#64748b"></a-text>';

    // Divider
    html += '<a-plane width="3.8" height="0.01" color="#334155" position="0 2.5 0.02" material="shader: flat"></a-plane>';

    // Section actions
    var actions = SECTION_ACTIONS[currentZone.id] || [];
    if (actions.length > 0) {
      html += '<a-text value="ACTIONS" position="-1.7 2.3 0.02" align="left" width="3" color="#475569"></a-text>';
      actions.forEach(function (a, i) {
        var y = 2.0 - i * 0.4;
        html += '<a-entity position="0 ' + y + ' 0.02" class="clickable"' +
                '  animation__hover="property: scale; to: 1.04 1.04 1.04; dur: 150; startEvents: mouseenter"' +
                '  animation__leave="property: scale; to: 1 1 1; dur: 150; startEvents: mouseleave"' +
                '  onclick="window._vrMenuAction(\'' + a.action + '\')">' +
                '<a-box width="3.6" height="0.32" depth="0.04" color="' + currentZone.color + '" opacity="0.15"></a-box>' +
                '<a-text value="' + a.label + '" position="0 0 0.03" align="center" width="4" color="#fff"></a-text></a-entity>';
      });
    }

    // Zone navigation
    var navStartY = actions.length > 0 ? (2.0 - actions.length * 0.4 - 0.3) : 2.2;
    html += '<a-text value="NAVIGATE" position="-1.7 ' + navStartY + ' 0.02" align="left" width="3" color="#475569"></a-text>';

    ZONES.forEach(function (z, i) {
      var y = navStartY - 0.3 - i * 0.4;
      var isCurrent = z.id === currentZone.id;
      html += '<a-entity position="0 ' + y + ' 0.02" class="clickable"' +
              '  onclick="window.location.href=\'' + z.url + '\'"' +
              '  animation__hover="property: scale; to: 1.04 1.04 1.04; dur: 150; startEvents: mouseenter"' +
              '  animation__leave="property: scale; to: 1 1 1; dur: 150; startEvents: mouseleave">' +
              '<a-box width="3.6" height="0.32" depth="0.04" color="' + z.color + '" opacity="' + (isCurrent ? '0.4' : '0.12') + '"></a-box>' +
              '<a-box width="0.08" height="0.32" depth="0.05" color="' + z.color + '" position="-1.76 0 0"></a-box>' +
              '<a-text value="' + z.name.toUpperCase() + '" position="0 0 0.03" align="center" width="3.8" color="' + (isCurrent ? '#fff' : '#94a3b8') + '"></a-text>' +
              (isCurrent ? '<a-text value="HERE" position="1.4 0 0.03" align="center" width="2" color="' + z.color + '"></a-text>' : '') +
              '</a-entity>';
    });

    // Music controls
    var musicY = navStartY - 0.3 - ZONES.length * 0.4 - 0.3;
    html += '<a-text value="MUSIC" position="-1.7 ' + musicY + ' 0.02" align="left" width="3" color="#475569"></a-text>';
    html += '<a-entity position="0 ' + (musicY - 0.35) + ' 0.02">';
    html += '  <a-entity position="-0.8 0 0" class="clickable" onclick="window._vrMusicPrev()">' +
            '    <a-box width="0.5" height="0.32" depth="0.04" color="#1e293b"></a-box>' +
            '    <a-text value="<<" position="0 0 0.03" align="center" width="3" color="#94a3b8"></a-text></a-entity>';
    html += '  <a-entity position="0 0 0" class="clickable" onclick="window._vrMusicToggle()">' +
            '    <a-box width="0.7" height="0.32" depth="0.04" color="#22c55e" opacity="0.3"></a-box>' +
            '    <a-text id="vr-music-label" value="PLAY" position="0 0 0.03" align="center" width="3" color="#22c55e"></a-text></a-entity>';
    html += '  <a-entity position="0.8 0 0" class="clickable" onclick="window._vrMusicNext()">' +
            '    <a-box width="0.5" height="0.32" depth="0.04" color="#1e293b"></a-box>' +
            '    <a-text value=">>" position="0 0 0.03" align="center" width="3" color="#94a3b8"></a-text></a-entity>';
    html += '</a-entity>';
    html += '<a-text id="vr-music-station-label" value="Groove Salad - Ambient Chill" position="0 ' + (musicY - 0.7) + ' 0.02" align="center" width="3.5" color="#64748b"></a-text>';

    // Close button
    html += '<a-entity position="1.8 2.85 0.02" class="clickable" onclick="closeNavMenu()">' +
            '<a-circle radius="0.14" color="#ef4444" opacity="0.8" material="shader: flat"></a-circle>' +
            '<a-text value="X" position="0 0 0.02" align="center" width="4" color="#fff"></a-text></a-entity>';

    // Footer hint
    html += '<a-text value="Menu button to toggle" position="0 -3.0 0.02" align="center" width="3" color="#475569"></a-text>';

    ent.innerHTML = html;
    scene.appendChild(ent);
    vrMenuEntity = ent;

    // VR music bridge functions
    window._vrMusicToggle = function () { toggleMusic(); updateVRMusicLabel(); };
    window._vrMusicNext = function () { nextStation(); updateVRMusicLabel(); };
    window._vrMusicPrev = function () { prevStation(); updateVRMusicLabel(); };

    // Floating menu sphere in VR (attached to camera)
    var cam = document.querySelector('a-camera');
    if (cam && !document.getElementById('vr-nav-button')) {
      var vrBtn = document.createElement('a-entity');
      vrBtn.id = 'vr-nav-button';
      vrBtn.setAttribute('position', '0.8 -0.5 -1.5');
      vrBtn.innerHTML =
        '<a-sphere radius="0.12" color="#00d4ff" opacity="0.85" class="clickable"' +
        '  animation="property: scale; to: 1.08 1.08 1.08; dur: 1200; loop: true; dir: alternate"' +
        '  onclick="toggleNavMenu()">' +
        '  <a-text value="M" position="0 0 0.1" align="center" width="3.5" color="#fff"></a-text>' +
        '</a-sphere>' +
        '<a-text value="Menu" position="0 -0.2 0" align="center" width="2.5" color="#00d4ff"></a-text>';
      cam.appendChild(vrBtn);
    }

    // Update VR clock every 30s
    setInterval(function () {
      var el = document.getElementById('vr-menu-clock');
      if (el) el.setAttribute('value', formatTime());
    }, 30000);
  }

  function updateVRMusicLabel() {
    var el = document.getElementById('vr-music-label');
    if (el) el.setAttribute('value', musicPlaying ? 'PAUSE' : 'PLAY');
    var stEl = document.getElementById('vr-music-station-label');
    if (stEl) {
      var st = STATIONS[currentStationIdx];
      stEl.setAttribute('value', musicPlaying ? st.name + ' - ' + st.genre : 'Not playing');
    }
  }

  /* ═══════════════════════════════════════════
     MENU TOGGLE
     ═══════════════════════════════════════════ */
  window.toggleNavMenu = function () {
    menuOpen = !menuOpen;
    var m = document.getElementById('vr-nav-menu-2d');
    if (m) m.classList.toggle('active', menuOpen);
    var f = document.getElementById('vr-nav-floating-btn');
    if (f) f.classList.toggle('active', menuOpen);
    if (vrMenuEntity) vrMenuEntity.setAttribute('visible', menuOpen);
  };

  window.closeNavMenu = function () {
    menuOpen = false;
    var m = document.getElementById('vr-nav-menu-2d');
    if (m) m.classList.remove('active');
    var f = document.getElementById('vr-nav-floating-btn');
    if (f) f.classList.remove('active');
    if (vrMenuEntity) vrMenuEntity.setAttribute('visible', false);
  };

  /* ── Keyboard ── */
  document.addEventListener('keydown', function (e) {
    if (e.key === 'm' || e.key === 'M' || e.key === 'Tab') {
      e.preventDefault();
      toggleNavMenu();
    }
    if (e.key === 'Escape') closeNavMenu();
  });

  /* ── Quest menu button polling ── */
  function setupGamepadMenuButton() {
    var scene = document.querySelector('a-scene');
    if (!scene) return;
    var lastPressed = false;
    scene.addEventListener('loaded', function () {
      if (!navigator.getGamepads) return;
      setInterval(function () {
        var gamepads = navigator.getGamepads();
        for (var i = 0; i < gamepads.length; i++) {
          var gp = gamepads[i];
          if (!gp) continue;
          // Quest Menu button: button index 2 or 3
          var btn = (gp.buttons[2] && gp.buttons[2].pressed) ||
                    (gp.buttons[3] && gp.buttons[3].pressed);
          if (btn && !lastPressed) {
            toggleNavMenu();
          }
          lastPressed = btn;
        }
      }, 200);
    });
  }

  /* ═══════════════════════════════════════════
     CSS
     ═══════════════════════════════════════════ */
  function getMenuCSS() {
    return '\
#vr-nav-menu-2d{position:fixed;top:0;left:0;width:100%;height:100%;z-index:100000;display:none;font-family:"Inter",system-ui,sans-serif}\
#vr-nav-menu-2d.active{display:block}\
.vr-nav-overlay{position:absolute;inset:0;background:rgba(0,0,0,0.7);backdrop-filter:blur(8px)}\
.vr-nav-panel{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);background:linear-gradient(135deg,#1a1a3e,#0f0f1f);border:1.5px solid rgba(0,212,255,0.4);border-radius:18px;padding:20px 22px;min-width:360px;max-width:92vw;max-height:90vh;overflow-y:auto;box-shadow:0 25px 80px rgba(0,212,255,0.2);animation:vr-nav-appear .3s ease}\
.vr-nav-panel::-webkit-scrollbar{width:5px}.vr-nav-panel::-webkit-scrollbar-thumb{background:rgba(0,212,255,0.3);border-radius:3px}\
@keyframes vr-nav-appear{from{opacity:0;transform:translate(-50%,-45%) scale(.95)}to{opacity:1;transform:translate(-50%,-50%) scale(1)}}\
.vr-nav-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;padding-bottom:10px;border-bottom:1px solid rgba(255,255,255,0.08)}\
.vr-nav-header-left{display:flex;align-items:center;gap:8px}\
.vr-nav-header-right{display:flex;align-items:center;gap:10px}\
.vr-nav-current-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}\
.vr-nav-current-zone{color:#fff;font-size:15px;font-weight:600}\
.vr-nav-session{color:#22c55e;font-size:11px;font-weight:600;background:rgba(34,197,94,0.1);padding:2px 8px;border-radius:6px;letter-spacing:0.5px;font-variant-numeric:tabular-nums}\
.vr-nav-clock{color:#64748b;font-size:13px;font-weight:500;font-variant-numeric:tabular-nums}\
.vr-nav-date{color:#475569;font-size:12px;text-align:right;margin-bottom:12px}\
.vr-nav-close{background:rgba(255,255,255,0.08);border:none;color:#aaa;width:30px;height:30px;border-radius:50%;cursor:pointer;font-size:14px;transition:all .2s;display:flex;align-items:center;justify-content:center}\
.vr-nav-close:hover{background:rgba(239,68,68,0.7);color:#fff}\
.vr-nav-section-label{color:#475569;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin:12px 0 6px;display:flex;align-items:center;gap:8px}\
.vr-nav-section-label::after{content:"";flex:1;height:1px;background:rgba(255,255,255,0.06)}\
.vr-nav-section-btns{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px}\
.vr-nav-section-btn{background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.08);color:#cbd5e1;padding:6px 14px;border-radius:8px;cursor:pointer;font-size:12px;font-weight:500;transition:all .2s}\
.vr-nav-section-btn:hover{background:rgba(255,255,255,0.12);color:#fff}\
.vr-nav-zones{display:flex;flex-direction:column;gap:5px}\
.vr-nav-zone{display:flex;align-items:center;gap:10px;padding:10px 12px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:10px;text-decoration:none;color:#94a3b8;transition:all .2s;font-size:14px}\
.vr-nav-zone:hover{background:rgba(255,255,255,0.08);border-color:var(--zone-color);color:#fff;transform:translateX(3px)}\
.vr-nav-zone.current{background:rgba(255,255,255,0.08);border-color:var(--zone-color);color:#fff}\
.vr-nav-emoji{font-size:18px;width:32px;height:32px;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.25);border-radius:8px}\
.vr-nav-name{flex:1;font-weight:500}\
.vr-nav-arrow{opacity:0;transition:all .2s;color:var(--zone-color);font-size:13px}\
.vr-nav-zone:hover .vr-nav-arrow{opacity:1;transform:translateX(3px)}\
.vr-nav-here{font-size:10px;font-weight:700;color:var(--zone-color);letter-spacing:1px;background:rgba(255,255,255,0.06);padding:2px 8px;border-radius:6px}\
.vr-music-player{background:rgba(0,0,0,0.2);border:1px solid rgba(255,255,255,0.05);border-radius:10px;padding:10px 12px;margin-bottom:6px}\
.vr-music-controls{display:flex;align-items:center;gap:6px;margin-bottom:6px}\
.vr-music-btn{width:32px;height:32px;border-radius:50%;border:1px solid rgba(255,255,255,0.1);background:rgba(255,255,255,0.05);color:#94a3b8;cursor:pointer;font-size:14px;display:flex;align-items:center;justify-content:center;transition:all .2s}\
.vr-music-btn:hover{background:rgba(255,255,255,0.12);color:#fff}\
.vr-music-play{width:38px;height:38px;border-color:rgba(34,197,94,0.3);color:#22c55e;font-size:16px}\
.vr-music-play:hover{background:rgba(34,197,94,0.15)}\
.vr-music-vol{flex:1;height:4px;-webkit-appearance:none;appearance:none;background:rgba(255,255,255,0.1);border-radius:2px;outline:none;cursor:pointer}\
.vr-music-vol::-webkit-slider-thumb{-webkit-appearance:none;width:14px;height:14px;border-radius:50%;background:#00d4ff;cursor:pointer}\
.vr-music-now{color:#64748b;font-size:12px;margin-bottom:6px;min-height:16px}\
.vr-music-stations{display:flex;gap:4px;flex-wrap:wrap}\
.vr-music-station{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.06);border-radius:6px;padding:4px 10px;cursor:pointer;transition:all .2s;text-align:left}\
.vr-music-station:hover{background:rgba(255,255,255,0.08);border-color:var(--st-color)}\
.vr-music-station.active{background:rgba(255,255,255,0.1);border-color:var(--st-color)}\
.st-name{display:block;color:#cbd5e1;font-size:11px;font-weight:600}\
.st-genre{display:block;color:#475569;font-size:10px}\
.vr-music-credit{color:#334155;font-size:10px;margin-top:6px;text-align:center}\
.vr-music-credit a{color:#475569;text-decoration:none}\
.vr-nav-guide-row{display:flex;gap:6px;margin-bottom:6px}\
.vr-nav-guide-btn{flex:1;display:flex;align-items:center;justify-content:center;gap:6px;padding:8px 12px;border-radius:10px;border:1px solid rgba(125,211,252,0.2);background:linear-gradient(135deg,rgba(0,212,255,0.06),rgba(168,85,247,0.06));color:#7dd3fc;cursor:pointer;font-size:12px;font-weight:600;transition:all .2s}\
.vr-nav-guide-btn:hover{background:linear-gradient(135deg,rgba(0,212,255,0.15),rgba(168,85,247,0.12));border-color:rgba(125,211,252,0.4);color:#fff}\
.vr-nav-guide-speak{border-color:rgba(34,197,94,0.2);background:rgba(34,197,94,0.06);color:#4ade80}\
.vr-nav-guide-speak:hover{background:rgba(34,197,94,0.15);border-color:rgba(34,197,94,0.4);color:#fff}\
.guide-btn-icon{font-size:15px}\
.vr-nav-hint{margin-top:10px;padding-top:10px;border-top:1px solid rgba(255,255,255,0.06);text-align:center;font-size:11px;color:#475569}\
.vr-nav-hint kbd{background:rgba(255,255,255,0.08);padding:2px 6px;border-radius:4px;font-family:monospace;color:#64748b;font-size:10px}\
#vr-nav-floating-btn{position:fixed;bottom:16px;right:16px;width:50px;height:50px;background:linear-gradient(135deg,#00d4ff,#a855f7);border:none;border-radius:14px;cursor:pointer;z-index:99999;display:flex;align-items:center;justify-content:center;box-shadow:0 8px 24px rgba(0,212,255,0.3);transition:all .3s;animation:vr-nav-float 3s ease-in-out infinite}\
@keyframes vr-nav-float{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}\
#vr-nav-floating-btn:hover{transform:scale(1.1)}\
#vr-nav-floating-btn.active{background:linear-gradient(135deg,#ef4444,#f97316);animation:none;border-radius:50%}\
.fab-icon{color:#fff;font-size:22px;line-height:1}\
.a-fullscreen #vr-nav-floating-btn{display:none}';
  }

  /* ═══════════════════════════════════════════
     SMOOTH ZONE TRANSITION (Quick-Win QW-004)
     ═══════════════════════════════════════════ */
  function addZoneTransition() {
    // Fade-in on page load
    var style = document.createElement('style');
    style.textContent =
      '@keyframes vr-zone-fadein{from{opacity:0}to{opacity:1}}' +
      'body.vr-entering{animation:vr-zone-fadein 0.5s ease forwards}' +
      'body.vr-leaving{transition:opacity 0.35s ease;opacity:0!important}';
    document.head.appendChild(style);
    document.body.classList.add('vr-entering');

    // Intercept link clicks for fade-out transition
    document.addEventListener('click', function (e) {
      var link = e.target.closest('a[href]');
      if (!link) return;
      var href = link.getAttribute('href');
      if (!href || href.charAt(0) === '#' || href.indexOf('://') !== -1) return;
      // Only intercept VR zone links
      if (href.indexOf('/vr/') !== 0 && href.indexOf('vr/') !== 0) return;
      e.preventDefault();
      document.body.classList.add('vr-leaving');
      setTimeout(function () { window.location.href = href; }, 350);
    });
  }

  /* ═══════════════════════════════════════════
     INIT
     ═══════════════════════════════════════════ */
  function init() {
    addZoneTransition();
    create2DMenu();
    var check = setInterval(function () {
      var scene = document.querySelector('a-scene');
      if (scene) {
        clearInterval(check);
        createVRMenu();
        setupGamepadMenuButton();
      }
    }, 500);
    setTimeout(function () { clearInterval(check); }, 10000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
