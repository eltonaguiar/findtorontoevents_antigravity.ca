/**
 * VR Advanced UX & Immersion — Set 12
 *
 * 10 advanced UX and immersion features:
 *
 *  1. Data Export/Import    — backup all VR user data as JSON, import/restore
 *  2. Mini-Map Radar        — small top-down zone map with position marker
 *  3. Dynamic Weather FX    — rain/snow/fog particles from actual forecast
 *  4. Photo Mode            — capture viewport with date/zone watermark
 *  5. Events Countdown      — live countdown to next upcoming event
 *  6. Movie Autoplay Queue  — auto-advance through active playlist
 *  7. Creator Spotlight     — rotating featured creator with highlight banner
 *  8. Voice Commands        — speech recognition for hands-free navigation
 *  9. Usage Analytics       — personal usage stats, session length graph
 * 10. Spatial Ambient Audio — zone-specific ambient soundscapes
 *
 * Load via <script src="/vr/advanced-ux.js"></script>
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

  function store(k, v) { try { localStorage.setItem('vr12_' + k, JSON.stringify(v)); } catch (e) {} }
  function load(k, d) { try { var v = localStorage.getItem('vr12_' + k); return v ? JSON.parse(v) : d; } catch (e) { return d; } }
  function css(id, t) { if (document.getElementById(id)) return; var s = document.createElement('style'); s.id = id; s.textContent = t; document.head.appendChild(s); }
  function toast(m, c) {
    c = c || '#7dd3fc';
    var t = document.createElement('div');
    t.className = 'vr12-toast';
    t.style.cssText = 'position:fixed;top:16px;left:50%;transform:translateX(-50%);z-index:9100;background:rgba(15,12,41,0.95);color:' + c + ';padding:10px 20px;border-radius:10px;font:600 13px/1.3 Inter,system-ui,sans-serif;border:1px solid ' + c + '33;backdrop-filter:blur(10px);pointer-events:none;animation:vr12t .3s ease-out';
    t.textContent = m; document.body.appendChild(t);
    setTimeout(function () { t.style.opacity = '0'; t.style.transition = 'opacity .3s'; }, 2500);
    setTimeout(function () { if (t.parentNode) t.remove(); }, 3000);
  }
  css('vr12-base', '@keyframes vr12t{from{opacity:0;transform:translateX(-50%) translateY(-10px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}');

  /* ═══════════════════════════════════════════════
     1. DATA EXPORT / IMPORT
     ═══════════════════════════════════════════════ */
  var dataExport = (function () {
    var VR_PREFIXES = ['vr_', 'vr5_', 'vr7_', 'vr8_', 'vr9_', 'vr10_', 'vr11_', 'vr12_', 'vrFav', 'vrSearch', 'vrRating', 'vrActivity', 'vrPreload', 'vrBreadcrumb', 'vrStats', 'vrShare'];

    function gatherAll() {
      var data = {};
      for (var i = 0; i < localStorage.length; i++) {
        var key = localStorage.key(i);
        if (VR_PREFIXES.some(function (p) { return key.indexOf(p) === 0; })) {
          try { data[key] = JSON.parse(localStorage.getItem(key)); } catch (e) { data[key] = localStorage.getItem(key); }
        }
      }
      return data;
    }

    function exportData() {
      var data = gatherAll();
      data._meta = { exported: new Date().toISOString(), version: 12, zone: zone, keys: Object.keys(data).length };
      var blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url; a.download = 'vr-backup-' + new Date().toISOString().slice(0, 10) + '.json';
      a.click(); URL.revokeObjectURL(url);
      toast('Data exported (' + Object.keys(data).length + ' keys)', '#22c55e');
    }

    function importData(jsonStr) {
      try {
        var data = typeof jsonStr === 'string' ? JSON.parse(jsonStr) : jsonStr;
        var count = 0;
        Object.keys(data).forEach(function (key) {
          if (key === '_meta') return;
          localStorage.setItem(key, typeof data[key] === 'string' ? data[key] : JSON.stringify(data[key]));
          count++;
        });
        toast('Imported ' + count + ' keys. Reload to apply.', '#22c55e');
        return count;
      } catch (e) { toast('Import failed: invalid JSON', '#ef4444'); return 0; }
    }

    function importFromFile() {
      var input = document.createElement('input');
      input.type = 'file'; input.accept = '.json';
      input.addEventListener('change', function () {
        if (!input.files || !input.files[0]) return;
        var reader = new FileReader();
        reader.onload = function () { importData(reader.result); };
        reader.readAsText(input.files[0]);
      });
      input.click();
    }

    return { export: exportData, import: importData, importFromFile: importFromFile, gather: gatherAll };
  })();

  /* ═══════════════════════════════════════════════
     2. MINI-MAP RADAR
     ═══════════════════════════════════════════════ */
  var miniMap = (function () {
    var zoneLayouts = {
      hub:     { w: 120, h: 120, areas: [{ x: 60, y: 20, r: 8, label: 'Events', c: '#ff6b6b' }, { x: 100, y: 60, r: 8, label: 'Movies', c: '#4ecdc4' }, { x: 60, y: 100, r: 8, label: 'Stocks', c: '#22c55e' }, { x: 20, y: 60, r: 8, label: 'Creators', c: '#a855f7' }] },
      events:  { w: 120, h: 80,  areas: [{ x: 30, y: 40, r: 6, label: 'Stage', c: '#ff6b6b' }, { x: 90, y: 40, r: 6, label: 'Cards', c: '#f97316' }] },
      movies:  { w: 120, h: 80,  areas: [{ x: 60, y: 30, r: 10, label: 'Screen', c: '#4ecdc4' }, { x: 60, y: 65, r: 6, label: 'Seats', c: '#64748b' }] },
      creators:{ w: 120, h: 80,  areas: [{ x: 40, y: 40, r: 6, label: 'Grid', c: '#a855f7' }, { x: 90, y: 40, r: 6, label: 'Live', c: '#ef4444' }] },
      stocks:  { w: 120, h: 80,  areas: [{ x: 40, y: 40, r: 8, label: 'Board', c: '#22c55e' }, { x: 90, y: 40, r: 6, label: 'Charts', c: '#06b6d4' }] },
      weather: { w: 120, h: 80,  areas: [{ x: 60, y: 40, r: 12, label: 'Globe', c: '#06b6d4' }] },
      wellness:{ w: 120, h: 80,  areas: [{ x: 40, y: 40, r: 8, label: 'Garden', c: '#10b981' }, { x: 90, y: 40, r: 6, label: 'Timer', c: '#f59e0b' }] },
      tutorial:{ w: 120, h: 80,  areas: [{ x: 60, y: 40, r: 10, label: 'Guide', c: '#7dd3fc' }] }
    };
    var layout = zoneLayouts[zone] || zoneLayouts.hub;
    var playerX = layout.w / 2, playerY = layout.h / 2;

    function createMiniMap() {
      css('vr12-mm-css',
        '#vr12-minimap{position:fixed;bottom:10px;right:10px;z-index:170;width:' + (layout.w + 16) + 'px;background:rgba(10,10,26,0.88);border:1px solid rgba(0,212,255,0.2);border-radius:12px;padding:8px;backdrop-filter:blur(8px)}' +
        '#vr12-minimap canvas{display:block;border-radius:6px}' +
        '#vr12-mm-label{color:#64748b;font:600 9px Inter,system-ui,sans-serif;text-align:center;margin-top:3px;text-transform:capitalize}'
      );
      var el = document.createElement('div');
      el.id = 'vr12-minimap';
      el.innerHTML = '<canvas id="vr12-mm-canvas" width="' + layout.w + '" height="' + layout.h + '"></canvas><div id="vr12-mm-label">' + zone + ' zone</div>';
      document.body.appendChild(el);
      drawMap();
      // Simulate player movement for demo
      setInterval(function () {
        playerX = Math.max(8, Math.min(layout.w - 8, playerX + (Math.random() - 0.5) * 4));
        playerY = Math.max(8, Math.min(layout.h - 8, playerY + (Math.random() - 0.5) * 4));
        drawMap();
      }, 2000);
    }

    function drawMap() {
      var canvas = document.getElementById('vr12-mm-canvas');
      if (!canvas) return;
      var ctx = canvas.getContext('2d');
      // Background
      ctx.fillStyle = 'rgba(15,12,41,0.9)';
      ctx.fillRect(0, 0, layout.w, layout.h);
      // Grid lines
      ctx.strokeStyle = 'rgba(255,255,255,0.04)';
      ctx.lineWidth = 0.5;
      for (var gx = 0; gx < layout.w; gx += 20) { ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, layout.h); ctx.stroke(); }
      for (var gy = 0; gy < layout.h; gy += 20) { ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(layout.w, gy); ctx.stroke(); }
      // Areas
      layout.areas.forEach(function (a) {
        ctx.beginPath(); ctx.arc(a.x, a.y, a.r, 0, Math.PI * 2);
        ctx.fillStyle = a.c + '33'; ctx.fill();
        ctx.strokeStyle = a.c + '66'; ctx.lineWidth = 1; ctx.stroke();
        ctx.fillStyle = a.c; ctx.font = '7px Inter,sans-serif'; ctx.textAlign = 'center';
        ctx.fillText(a.label, a.x, a.y + a.r + 9);
      });
      // Player dot
      ctx.beginPath(); ctx.arc(playerX, playerY, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#00d4ff'; ctx.fill();
      ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.5; ctx.stroke();
      // Pulse ring
      var pulse = (Date.now() % 2000) / 2000;
      ctx.beginPath(); ctx.arc(playerX, playerY, 4 + pulse * 8, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(0,212,255,' + (0.4 - pulse * 0.4) + ')'; ctx.lineWidth = 1; ctx.stroke();
    }

    setTimeout(createMiniMap, 2000);
    return { getPosition: function () { return { x: playerX, y: playerY }; }, zone: zone };
  })();

  /* ═══════════════════════════════════════════════
     3. DYNAMIC WEATHER EFFECTS
     ═══════════════════════════════════════════════ */
  var weatherEffects = (function () {
    if (zone !== 'weather') return null;
    var currentEffect = 'none';
    var particleContainer = null;
    var animFrame = null;

    function createContainer() {
      css('vr12-wx-css',
        '#vr12-weather-fx{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:50;overflow:hidden}' +
        '.vr12-rain{position:absolute;width:1px;background:linear-gradient(transparent,rgba(100,180,255,0.6));animation:vr12rain linear infinite}' +
        '.vr12-snow{position:absolute;width:4px;height:4px;background:rgba(255,255,255,0.8);border-radius:50%;animation:vr12snow linear infinite}' +
        '@keyframes vr12rain{from{transform:translateY(-20px)}to{transform:translateY(100vh)}}' +
        '@keyframes vr12snow{from{transform:translateY(-20px) rotate(0deg)}to{transform:translateY(100vh) rotate(360deg)}}'
      );
      particleContainer = document.createElement('div');
      particleContainer.id = 'vr12-weather-fx';
      document.body.appendChild(particleContainer);
    }

    function clearParticles() {
      if (particleContainer) particleContainer.innerHTML = '';
      if (animFrame) { cancelAnimationFrame(animFrame); animFrame = null; }
      currentEffect = 'none';
    }

    function spawnRain(intensity) {
      clearParticles();
      currentEffect = 'rain';
      var count = Math.min(intensity || 40, 80);
      for (var i = 0; i < count; i++) {
        var drop = document.createElement('div');
        drop.className = 'vr12-rain';
        var h = 15 + Math.random() * 25;
        drop.style.cssText = 'left:' + Math.random() * 100 + '%;height:' + h + 'px;animation-duration:' + (0.4 + Math.random() * 0.6) + 's;animation-delay:' + Math.random() * 2 + 's;opacity:' + (0.3 + Math.random() * 0.4);
        particleContainer.appendChild(drop);
      }
    }

    function spawnSnow(intensity) {
      clearParticles();
      currentEffect = 'snow';
      var count = Math.min(intensity || 30, 60);
      for (var i = 0; i < count; i++) {
        var flake = document.createElement('div');
        flake.className = 'vr12-snow';
        var size = 2 + Math.random() * 4;
        flake.style.cssText = 'left:' + Math.random() * 100 + '%;width:' + size + 'px;height:' + size + 'px;animation-duration:' + (3 + Math.random() * 5) + 's;animation-delay:' + Math.random() * 4 + 's;opacity:' + (0.4 + Math.random() * 0.4);
        particleContainer.appendChild(flake);
      }
    }

    function spawnFog() {
      clearParticles();
      currentEffect = 'fog';
      var overlay = document.createElement('div');
      overlay.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;background:rgba(180,190,200,0.15);animation:vr12fog 6s ease-in-out infinite alternate';
      css('vr12-fog-anim', '@keyframes vr12fog{from{opacity:0.1}to{opacity:0.25}}');
      particleContainer.appendChild(overlay);
    }

    function autoDetect() {
      // Use Open-Meteo WMO weather codes
      fetch('https://api.open-meteo.com/v1/forecast?latitude=43.65&longitude=-79.38&current=weather_code&timezone=auto')
        .then(function (r) { return r.json(); })
        .then(function (d) {
          var code = d && d.current && d.current.weather_code;
          if (!code && code !== 0) return;
          if (code >= 61 && code <= 67) spawnRain(50);        // Rain
          else if (code >= 71 && code <= 77) spawnSnow(40);   // Snow
          else if (code >= 80 && code <= 82) spawnRain(70);   // Showers
          else if (code >= 85 && code <= 86) spawnSnow(50);   // Snow showers
          else if (code >= 95) spawnRain(80);                 // Thunderstorm
          else if (code === 45 || code === 48) spawnFog();    // Fog
          // else clear (no effect)
        }).catch(function () {});
    }

    setTimeout(function () { createContainer(); autoDetect(); }, 2000);
    return { rain: spawnRain, snow: spawnSnow, fog: spawnFog, clear: clearParticles, getCurrent: function () { return currentEffect; }, autoDetect: autoDetect };
  })();

  /* ═══════════════════════════════════════════════
     4. PHOTO MODE
     ═══════════════════════════════════════════════ */
  var photoMode = (function () {
    var isActive = false;

    function capture() {
      var canvas = document.querySelector('canvas.a-canvas, canvas');
      if (!canvas) { toast('No canvas found', '#ef4444'); return null; }
      try {
        // Draw watermark
        var tempCanvas = document.createElement('canvas');
        tempCanvas.width = canvas.width; tempCanvas.height = canvas.height;
        var ctx = tempCanvas.getContext('2d');
        ctx.drawImage(canvas, 0, 0);
        // Watermark
        ctx.fillStyle = 'rgba(0,0,0,0.5)';
        ctx.fillRect(0, tempCanvas.height - 36, tempCanvas.width, 36);
        ctx.fillStyle = '#7dd3fc'; ctx.font = '14px Inter,sans-serif'; ctx.textBaseline = 'middle';
        ctx.fillText('VR Toronto Events — ' + zone.toUpperCase() + ' — ' + new Date().toLocaleString(), 10, tempCanvas.height - 18);
        var dataUrl = tempCanvas.toDataURL('image/png');
        // Save
        var a = document.createElement('a');
        a.href = dataUrl; a.download = 'vr-photo-' + zone + '-' + Date.now() + '.png';
        a.click();
        toast('Photo captured!', '#f59e0b');
        return dataUrl;
      } catch (e) { toast('Capture failed (CORS)', '#ef4444'); return null; }
    }

    function createButton() {
      css('vr12-photo-css',
        '#vr12-photo-btn{position:fixed;bottom:60px;right:10px;z-index:170;background:rgba(15,12,41,0.9);border:1px solid rgba(245,158,11,0.25);border-radius:10px;padding:6px 12px;color:#f59e0b;font:600 12px Inter,system-ui,sans-serif;cursor:pointer;transition:all .2s;backdrop-filter:blur(10px)}' +
        '#vr12-photo-btn:hover{border-color:rgba(245,158,11,0.5);color:#fff;transform:scale(1.05)}'
      );
      var btn = document.createElement('button');
      btn.id = 'vr12-photo-btn';
      btn.innerHTML = '📷 Photo';
      btn.title = 'Capture VR screenshot (P)';
      btn.addEventListener('click', capture);
      document.body.appendChild(btn);
    }

    document.addEventListener('keydown', function (e) {
      if (e.key === 'p' && !e.ctrlKey && !e.altKey && !e.metaKey && document.activeElement.tagName !== 'INPUT') capture();
    });

    setTimeout(createButton, 1500);
    return { capture: capture, isActive: function () { return isActive; } };
  })();

  /* ═══════════════════════════════════════════════
     5. EVENTS COUNTDOWN TIMER
     ═══════════════════════════════════════════════ */
  var eventsCountdown = (function () {
    if (zone !== 'events') return null;
    var timerEl = null;
    var targetEvent = null;
    var intervalId = null;

    function createUI() {
      css('vr12-cd-css',
        '#vr12-countdown{position:fixed;top:50px;left:10px;z-index:160;background:rgba(15,12,41,0.92);border:1px solid rgba(255,107,107,0.2);border-radius:12px;padding:10px 14px;min-width:180px;color:#e2e8f0;font:11px/1.4 Inter,system-ui,sans-serif;backdrop-filter:blur(10px)}' +
        '#vr12-countdown h4{margin:0 0 4px;color:#ff6b6b;font-size:12px}' +
        '#vr12-cd-time{font:700 20px Inter,system-ui,sans-serif;color:#ff6b6b;letter-spacing:1px}' +
        '#vr12-cd-name{color:#94a3b8;font-size:10px;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:160px}'
      );
      timerEl = document.createElement('div');
      timerEl.id = 'vr12-countdown';
      timerEl.innerHTML = '<h4>⏱ Next Event</h4><div id="vr12-cd-time">--:--:--</div><div id="vr12-cd-name">Loading...</div>';
      document.body.appendChild(timerEl);
      findNextEvent();
    }

    function findNextEvent() {
      // Try to find events from DOM or events.json
      var now = new Date();
      fetch('/events.json').then(function (r) { return r.json(); }).then(function (events) {
        if (!Array.isArray(events)) events = events.events || [];
        var future = events.filter(function (e) {
          var d = new Date(e.date || e.startDate || e.start);
          return d > now;
        }).sort(function (a, b) {
          return new Date(a.date || a.startDate || a.start) - new Date(b.date || b.startDate || b.start);
        });
        if (future.length > 0) {
          targetEvent = { name: future[0].name || future[0].title || 'Event', date: new Date(future[0].date || future[0].startDate || future[0].start) };
          startCountdown();
        } else {
          // Fallback: countdown to tomorrow
          var tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1); tomorrow.setHours(10, 0, 0, 0);
          targetEvent = { name: 'Tomorrow\'s events', date: tomorrow };
          startCountdown();
        }
      }).catch(function () {
        var tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1); tomorrow.setHours(10, 0, 0, 0);
        targetEvent = { name: 'Tomorrow\'s events', date: tomorrow };
        startCountdown();
      });
    }

    function startCountdown() {
      if (intervalId) clearInterval(intervalId);
      updateDisplay();
      intervalId = setInterval(updateDisplay, 1000);
    }

    function updateDisplay() {
      if (!targetEvent) return;
      var diff = targetEvent.date - Date.now();
      if (diff <= 0) { document.getElementById('vr12-cd-time').textContent = 'NOW!'; return; }
      var h = Math.floor(diff / 3600000);
      var m = Math.floor((diff % 3600000) / 60000);
      var s = Math.floor((diff % 60000) / 1000);
      var timeEl = document.getElementById('vr12-cd-time');
      var nameEl = document.getElementById('vr12-cd-name');
      if (timeEl) timeEl.textContent = (h > 0 ? h + 'h ' : '') + String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
      if (nameEl) nameEl.textContent = targetEvent.name;
    }

    setTimeout(createUI, 1500);
    return { getTarget: function () { return targetEvent; }, refresh: findNextEvent };
  })();

  /* ═══════════════════════════════════════════════
     6. MOVIE AUTOPLAY QUEUE
     ═══════════════════════════════════════════════ */
  var movieAutoplay = (function () {
    if (zone !== 'movies') return null;
    var queue = [];
    var currentIdx = -1;
    var autoAdvance = load('autoplay_enabled', false);

    function createUI() {
      css('vr12-aq-css',
        '#vr12-autoplay{position:fixed;top:130px;left:10px;z-index:160;background:rgba(15,12,41,0.92);border:1px solid rgba(78,205,196,0.2);border-radius:12px;padding:8px 12px;color:#e2e8f0;font:11px/1.4 Inter,system-ui,sans-serif;backdrop-filter:blur(10px);min-width:160px}' +
        '#vr12-autoplay h4{margin:0 0 6px;color:#4ecdc4;font-size:12px}' +
        '.vr12-aq-toggle{background:none;border:1px solid rgba(78,205,196,0.2);color:#4ecdc4;padding:3px 10px;border-radius:6px;cursor:pointer;font:600 10px Inter,system-ui,sans-serif;transition:all .15s}' +
        '.vr12-aq-toggle.on{background:rgba(78,205,196,0.15);border-color:rgba(78,205,196,0.4)}' +
        '.vr12-aq-info{color:#64748b;font-size:10px;margin-top:4px}'
      );
      var el = document.createElement('div');
      el.id = 'vr12-autoplay';
      render(el);
      document.body.appendChild(el);
    }

    function render(container) {
      container = container || document.getElementById('vr12-autoplay');
      if (!container) return;
      container.innerHTML = '<h4>▶ Autoplay</h4>' +
        '<button class="vr12-aq-toggle' + (autoAdvance ? ' on' : '') + '" onclick="VRAdvancedUX.movieAutoplay.toggleAuto()">' + (autoAdvance ? '✓ ON' : '○ OFF') + '</button>' +
        '<div class="vr12-aq-info">Queue: ' + queue.length + ' • Now: ' + (currentIdx >= 0 ? (currentIdx + 1) + '/' + queue.length : '—') + '</div>';
    }

    function addToQueue(title, videoId) {
      if (queue.some(function (q) { return q.videoId === videoId; })) return;
      queue.push({ title: title, videoId: videoId });
      render();
      toast('Queued: ' + title, '#4ecdc4');
    }

    function toggleAuto() {
      autoAdvance = !autoAdvance;
      store('autoplay_enabled', autoAdvance);
      render();
      toast('Autoplay ' + (autoAdvance ? 'ON' : 'OFF'), '#4ecdc4');
    }

    function next() {
      if (queue.length === 0) return null;
      currentIdx = (currentIdx + 1) % queue.length;
      return queue[currentIdx];
    }

    setTimeout(createUI, 1500);
    return { add: addToQueue, next: next, toggleAuto: toggleAuto, isAuto: function () { return autoAdvance; }, getQueue: function () { return queue; } };
  })();

  /* ═══════════════════════════════════════════════
     7. CREATOR SPOTLIGHT
     ═══════════════════════════════════════════════ */
  var creatorSpotlight = (function () {
    if (zone !== 'creators') return null;
    var spotlightCreators = ['pokimane', 'xQc', 'IShowSpeed', 'Kai Cenat', 'Valkyrae', 'HasanAbi', 'Mizkif', 'Ludwig'];
    var currentIdx = 0;

    function createBanner() {
      css('vr12-spot-css',
        '#vr12-spotlight{position:fixed;top:50px;left:50%;transform:translateX(-50%);z-index:160;background:linear-gradient(135deg,rgba(168,85,247,0.15),rgba(236,72,153,0.15));border:1px solid rgba(168,85,247,0.3);border-radius:14px;padding:10px 24px;color:#e2e8f0;font:12px/1.4 Inter,system-ui,sans-serif;backdrop-filter:blur(12px);text-align:center;max-width:300px;transition:all .5s}' +
        '#vr12-spotlight .star{color:#f59e0b;margin-right:6px}' +
        '#vr12-spotlight .name{font-weight:700;color:#c4b5fd;font-size:14px}' +
        '#vr12-spotlight .label{color:#a78bfa;font-size:10px;text-transform:uppercase;letter-spacing:1px}'
      );
      var el = document.createElement('div');
      el.id = 'vr12-spotlight';
      renderSpotlight(el);
      document.body.appendChild(el);
      // Rotate every 15s
      setInterval(function () {
        currentIdx = (currentIdx + 1) % spotlightCreators.length;
        renderSpotlight();
      }, 15000);
    }

    function renderSpotlight(container) {
      container = container || document.getElementById('vr12-spotlight');
      if (!container) return;
      container.innerHTML = '<div class="label">⭐ Creator Spotlight</div><div class="name"><span class="star">★</span>' + spotlightCreators[currentIdx] + '</div>';
      container.style.opacity = '0';
      setTimeout(function () { container.style.opacity = '1'; }, 50);
    }

    setTimeout(createBanner, 2000);
    return { getCurrent: function () { return spotlightCreators[currentIdx]; }, next: function () { currentIdx = (currentIdx + 1) % spotlightCreators.length; renderSpotlight(); } };
  })();

  /* ═══════════════════════════════════════════════
     8. VOICE COMMANDS
     ═══════════════════════════════════════════════ */
  var voiceCommands = (function () {
    var supported = typeof webkitSpeechRecognition !== 'undefined' || typeof SpeechRecognition !== 'undefined';
    var listening = false;
    var recognition = null;
    var commands = {
      'go to hub':      function () { location.href = '/vr/'; },
      'go to events':   function () { location.href = '/vr/events/'; },
      'go to movies':   function () { location.href = '/vr/movies.html'; },
      'go to creators':  function () { location.href = '/vr/creators.html'; },
      'go to stocks':   function () { location.href = '/vr/stocks-zone.html'; },
      'go to weather':  function () { location.href = '/vr/weather-zone.html'; },
      'go to wellness': function () { location.href = '/vr/wellness/'; },
      'open menu':      function () { if (window.openNavMenu) window.openNavMenu(); },
      'close menu':     function () { if (window.closeNavMenu) window.closeNavMenu(); },
      'take photo':     function () { if (photoMode) photoMode.capture(); },
      'export data':    function () { dataExport.export(); }
    };

    function createBadge() {
      css('vr12-voice-css',
        '#vr12-voice{position:fixed;bottom:100px;right:10px;z-index:170;background:rgba(15,12,41,0.9);border:1px solid rgba(239,68,68,0.2);border-radius:10px;padding:6px 12px;color:#fca5a5;font:600 12px Inter,system-ui,sans-serif;cursor:pointer;transition:all .2s;backdrop-filter:blur(10px)}' +
        '#vr12-voice:hover{border-color:rgba(239,68,68,0.4);color:#fff}' +
        '#vr12-voice.listening{border-color:rgba(239,68,68,0.6);color:#ef4444;animation:vr12pulse 1s infinite}'  +
        '@keyframes vr12pulse{0%,100%{box-shadow:0 0 0 0 rgba(239,68,68,0.3)}50%{box-shadow:0 0 0 8px rgba(239,68,68,0)}}'
      );
      var btn = document.createElement('button');
      btn.id = 'vr12-voice';
      btn.innerHTML = '🎤 Voice';
      btn.title = 'Voice commands (V)';
      btn.addEventListener('click', toggle);
      document.body.appendChild(btn);
    }

    function toggle() {
      if (!supported) { toast('Speech recognition not supported', '#ef4444'); return; }
      if (listening) { stop(); return; }
      start();
    }

    function start() {
      if (!supported || listening) return;
      var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognition = new SR();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';
      recognition.onresult = function (e) {
        var t = e.results[0][0].transcript.toLowerCase().trim();
        toast('Heard: "' + t + '"', '#fca5a5');
        var matched = false;
        Object.keys(commands).forEach(function (cmd) {
          if (t.indexOf(cmd) !== -1) { commands[cmd](); matched = true; }
        });
        if (!matched) toast('Unknown command', '#64748b');
      };
      recognition.onend = function () { listening = false; updateBadge(); };
      recognition.onerror = function () { listening = false; updateBadge(); };
      recognition.start();
      listening = true;
      updateBadge();
      toast('Listening...', '#ef4444');
    }

    function stop() {
      if (recognition) recognition.stop();
      listening = false;
      updateBadge();
    }

    function updateBadge() {
      var btn = document.getElementById('vr12-voice');
      if (btn) { btn.classList.toggle('listening', listening); btn.innerHTML = listening ? '🔴 Listening' : '🎤 Voice'; }
    }

    document.addEventListener('keydown', function (e) {
      if (e.key === 'v' && !e.ctrlKey && !e.altKey && !e.metaKey && document.activeElement.tagName !== 'INPUT') toggle();
    });

    setTimeout(createBadge, 1500);
    return { start: start, stop: stop, toggle: toggle, isListening: function () { return listening; }, isSupported: function () { return supported; }, commands: Object.keys(commands) };
  })();

  /* ═══════════════════════════════════════════════
     9. USAGE ANALYTICS DASHBOARD
     ═══════════════════════════════════════════════ */
  var analytics = (function () {
    var sessions = load('sessions', []);
    var sessionStart = Date.now();

    // Record this session
    function recordSession() {
      var duration = Math.round((Date.now() - sessionStart) / 1000);
      if (duration < 3) return; // Skip very short
      sessions.push({ zone: zone, start: sessionStart, duration: duration, date: new Date().toISOString().slice(0, 10) });
      if (sessions.length > 200) sessions = sessions.slice(-200);
      store('sessions', sessions);
    }
    window.addEventListener('beforeunload', recordSession);

    function getStats() {
      var totalTime = 0, zoneTime = {}, dayCounts = {};
      sessions.forEach(function (s) {
        totalTime += s.duration;
        zoneTime[s.zone] = (zoneTime[s.zone] || 0) + s.duration;
        dayCounts[s.date] = (dayCounts[s.date] || 0) + 1;
      });
      return { totalSessions: sessions.length, totalTimeSec: totalTime, zoneTime: zoneTime, dayCounts: dayCounts };
    }

    function openDashboard() {
      var existing = document.getElementById('vr12-analytics');
      if (existing) { existing.remove(); return; }
      var stats = getStats();
      css('vr12-an-css',
        '#vr12-analytics{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:600;background:rgba(15,12,41,0.97);border:1px solid rgba(0,212,255,0.25);border-radius:16px;padding:24px;width:min(400px,92vw);max-height:70vh;overflow-y:auto;color:#e2e8f0;font:13px/1.5 Inter,system-ui,sans-serif;backdrop-filter:blur(16px)}' +
        '#vr12-analytics h3{margin:0 0 12px;color:#7dd3fc;font-size:16px}' +
        '.vr12-an-stat{display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.05);font-size:12px}' +
        '.vr12-an-bar{height:8px;border-radius:4px;margin:2px 0}' +
        '.vr12-an-close{margin-top:12px;padding:6px 16px;background:rgba(0,212,255,0.1);color:#7dd3fc;border:1px solid rgba(0,212,255,0.2);border-radius:8px;cursor:pointer;font:600 12px Inter,system-ui,sans-serif}'
      );
      var el = document.createElement('div');
      el.id = 'vr12-analytics';
      el.setAttribute('role', 'dialog');
      var html = '<h3>📊 Usage Analytics</h3>';
      html += '<div class="vr12-an-stat"><span>Total Sessions</span><span>' + stats.totalSessions + '</span></div>';
      html += '<div class="vr12-an-stat"><span>Total Time</span><span>' + formatTime(stats.totalTimeSec) + '</span></div>';
      // Zone breakdown
      var maxZ = 1;
      Object.values(stats.zoneTime).forEach(function (t) { if (t > maxZ) maxZ = t; });
      var zoneColors = { hub: '#7dd3fc', events: '#ff6b6b', movies: '#4ecdc4', creators: '#a855f7', stocks: '#22c55e', wellness: '#10b981', weather: '#06b6d4', tutorial: '#f59e0b' };
      html += '<div style="margin-top:10px;font-weight:700;color:#94a3b8;font-size:11px">Time by Zone</div>';
      Object.keys(stats.zoneTime).forEach(function (z) {
        var pct = Math.round(stats.zoneTime[z] / maxZ * 100);
        html += '<div class="vr12-an-stat"><span style="text-transform:capitalize">' + z + '</span><span>' + formatTime(stats.zoneTime[z]) + '</span></div>';
        html += '<div class="vr12-an-bar" style="width:' + pct + '%;background:' + (zoneColors[z] || '#64748b') + '"></div>';
      });
      // Recent days
      var days = Object.keys(stats.dayCounts).sort().slice(-7);
      if (days.length > 0) {
        html += '<div style="margin-top:10px;font-weight:700;color:#94a3b8;font-size:11px">Last 7 Days</div>';
        days.forEach(function (d) {
          html += '<div class="vr12-an-stat"><span>' + d + '</span><span>' + stats.dayCounts[d] + ' sessions</span></div>';
        });
      }
      html += '<button class="vr12-an-close" onclick="document.getElementById(\'vr12-analytics\').remove()">Close</button>';
      el.innerHTML = html;
      document.body.appendChild(el);
    }

    function formatTime(sec) {
      if (sec < 60) return sec + 's';
      if (sec < 3600) return Math.round(sec / 60) + 'm';
      return Math.round(sec / 3600 * 10) / 10 + 'h';
    }

    return { getStats: getStats, open: openDashboard, getSessions: function () { return sessions; } };
  })();

  /* ═══════════════════════════════════════════════
     10. SPATIAL AMBIENT AUDIO
     ═══════════════════════════════════════════════ */
  var spatialAudio = (function () {
    var audioCtx = null;
    var playing = false;
    var sourceNode = null;
    var gainNode = null;
    var enabled = load('spatial_audio', true);

    var zoneScapes = {
      hub:     { type: 'sine',   freq: 120, vol: 0.03, mod: 0.2 },
      events:  { type: 'sine',   freq: 200, vol: 0.02, mod: 0.5 },
      movies:  { type: 'sine',   freq: 80,  vol: 0.025, mod: 0.1 },
      creators:{ type: 'square', freq: 180, vol: 0.01, mod: 0.3 },
      stocks:  { type: 'sawtooth', freq: 150, vol: 0.008, mod: 0.4 },
      wellness:{ type: 'sine',   freq: 260, vol: 0.02, mod: 0.15 },
      weather: { type: 'sine',   freq: 100, vol: 0.025, mod: 0.3 },
      tutorial:{ type: 'triangle', freq: 220, vol: 0.015, mod: 0.2 }
    };

    function startAmbient() {
      if (!enabled || playing) return;
      try {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        var scape = zoneScapes[zone] || zoneScapes.hub;
        // Base drone
        var osc = audioCtx.createOscillator();
        osc.type = scape.type;
        osc.frequency.setValueAtTime(scape.freq, audioCtx.currentTime);
        // LFO for modulation
        var lfo = audioCtx.createOscillator();
        lfo.frequency.setValueAtTime(scape.mod, audioCtx.currentTime);
        var lfoGain = audioCtx.createGain();
        lfoGain.gain.setValueAtTime(scape.freq * 0.05, audioCtx.currentTime);
        lfo.connect(lfoGain);
        lfoGain.connect(osc.frequency);
        lfo.start();
        // Output
        gainNode = audioCtx.createGain();
        gainNode.gain.setValueAtTime(scape.vol, audioCtx.currentTime);
        osc.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        osc.start();
        sourceNode = osc;
        playing = true;
      } catch (e) {}
    }

    function stopAmbient() {
      try {
        if (sourceNode) { sourceNode.stop(); sourceNode = null; }
        if (audioCtx) { audioCtx.close(); audioCtx = null; }
      } catch (e) {}
      playing = false;
    }

    function toggle() {
      enabled = !enabled;
      store('spatial_audio', enabled);
      if (enabled) startAmbient(); else stopAmbient();
      toast('Ambient audio ' + (enabled ? 'ON' : 'OFF'), '#06b6d4');
    }

    // Auto-start on first interaction
    document.addEventListener('click', function firstClick() {
      if (enabled && !playing) startAmbient();
      document.removeEventListener('click', firstClick);
    }, { once: true });

    window.addEventListener('beforeunload', stopAmbient);

    return { start: startAmbient, stop: stopAmbient, toggle: toggle, isPlaying: function () { return playing; }, isEnabled: function () { return enabled; } };
  })();

  /* ═══════════════════════════════════════════════
     PUBLIC API
     ═══════════════════════════════════════════════ */
  window.VRAdvancedUX = {
    zone: zone,
    version: 12,
    dataExport: dataExport,
    miniMap: miniMap,
    weatherEffects: weatherEffects,
    photoMode: photoMode,
    eventsCountdown: eventsCountdown,
    movieAutoplay: movieAutoplay,
    creatorSpotlight: creatorSpotlight,
    voiceCommands: voiceCommands,
    analytics: analytics,
    spatialAudio: spatialAudio
  };

  console.log('[VR Advanced UX] Set 12 loaded — ' + zone);
})();
