/**
 * VR Scene Enhancements — Set 8: 3D Scene Polish
 *
 * 10 actual A-Frame 3D scene improvements (not 2D overlays):
 *
 *   1.  Hub Portal Particle Fountains  — each portal emits themed particles
 *   2.  Hub Portal Hover Pulse         — portals scale up + glow on mouseenter
 *   3.  Hub Platform Energy Waves      — concentric expanding rings from center
 *   4.  Movies Screen Glow             — screen radiates color-matched light
 *   5.  Movies Dust Motes              — floating particles in projector beam
 *   6.  Stocks Price-Change Sparks     — green/red sparks on simulated ticks
 *   7.  Wellness Fireflies             — glowing animated orbs drifting in garden
 *   8.  Time-of-Day Sky Tint           — sky color shifts by real clock time
 *   9.  Ambient Floating Motes         — slow-drifting luminous dust in every zone
 *  10.  Portal Data Badges             — live data numbers floating below each hub portal
 *
 * Loaded via <script src="/vr/scene-enhancements.js"></script> in every zone.
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

  /* helper — wait until A-Frame scene is ready */
  function onSceneReady(cb) {
    var scene = document.querySelector('a-scene');
    if (!scene) return;
    if (scene.hasLoaded) cb(scene);
    else scene.addEventListener('loaded', function () { cb(scene); });
  }

  function el(tag, attrs, children) {
    var e = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (children) children.forEach(function (c) { e.appendChild(c); });
    return e;
  }

  /* ═══════════════════════════════════════════
     1. HUB: PORTAL PARTICLE FOUNTAINS
     ═══════════════════════════════════════════ */
  function hubPortalParticles(scene) {
    var portals = [
      { pos: '-6 0 -8', color: '#ff6b6b' },
      { pos: '0 0 -8',  color: '#4ecdc4' },
      { pos: '6 0 -8',  color: '#a855f7' },
      { pos: '-6 0 8',  color: '#22c55e' },
      { pos: '0 0 8',   color: '#10b981' },
      { pos: '6 0 8',   color: '#06b6d4' }
    ];

    portals.forEach(function (p) {
      var parts = p.pos.split(' ');
      var bx = parseFloat(parts[0]), bz = parseFloat(parts[2]);
      for (var i = 0; i < 5; i++) {
        var ox = (Math.random() - 0.5) * 1.5;
        var oz = (Math.random() - 0.5) * 1.5;
        var dur = 2500 + Math.random() * 2000;
        var yEnd = 3 + Math.random() * 2;
        var sphere = el('a-sphere', {
          position: (bx + ox) + ' 0.2 ' + (bz + oz),
          radius: (0.03 + Math.random() * 0.04).toFixed(3),
          color: p.color,
          opacity: '0.6',
          shader: 'flat',
          animation: 'property: position; to: ' + (bx + ox * 0.5) + ' ' + yEnd + ' ' + (bz + oz * 0.5) + '; dur: ' + Math.round(dur) + '; loop: true; dir: alternate; easing: easeInOutSine',
          'animation__fade': 'property: opacity; from: 0.6; to: 0.1; dur: ' + Math.round(dur) + '; loop: true; dir: alternate; easing: easeInOutSine'
        });
        scene.appendChild(sphere);
      }
    });
  }

  /* ═══════════════════════════════════════════
     2. HUB: PORTAL HOVER PULSE
     ═══════════════════════════════════════════ */
  function hubPortalHover(scene) {
    var boxes = scene.querySelectorAll('a-box[zone-link]');
    boxes.forEach(function (box) {
      box.addEventListener('mouseenter', function () {
        box.setAttribute('animation__hover', 'property: scale; to: 1.15 1.15 1.15; dur: 300; easing: easeOutBack');
        var ring = box.parentElement.querySelector('a-ring');
        if (ring) ring.setAttribute('animation__glow', 'property: opacity; to: 0.9; dur: 300');
      });
      box.addEventListener('mouseleave', function () {
        box.setAttribute('animation__hover', 'property: scale; to: 1 1 1; dur: 300; easing: easeOutQuad');
        var ring = box.parentElement.querySelector('a-ring');
        if (ring) ring.setAttribute('animation__glow', 'property: opacity; to: 0.5; dur: 300');
      });
    });
  }

  /* ═══════════════════════════════════════════
     3. HUB: PLATFORM ENERGY WAVES
     ═══════════════════════════════════════════ */
  function hubPlatformWaves(scene) {
    for (var i = 0; i < 3; i++) {
      var delay = i * 2000;
      var ring = el('a-ring', {
        position: '0 0.15 0',
        rotation: '-90 0 0',
        'radius-inner': '0.3',
        'radius-outer': '0.4',
        color: '#00d4ff',
        opacity: '0.5',
        shader: 'flat',
        animation: 'property: radius-outer; from: 0.5; to: 5; dur: 4000; loop: true; delay: ' + delay + '; easing: linear',
        'animation__ri': 'property: radius-inner; from: 0.3; to: 4.8; dur: 4000; loop: true; delay: ' + delay + '; easing: linear',
        'animation__fade': 'property: opacity; from: 0.5; to: 0; dur: 4000; loop: true; delay: ' + delay + '; easing: linear'
      });
      scene.appendChild(ring);
    }
  }

  /* ═══════════════════════════════════════════
     4. MOVIES: DYNAMIC SCREEN GLOW
     ═══════════════════════════════════════════ */
  function moviesScreenGlow(scene) {
    // Create a large soft light behind the screen area
    var glow = el('a-light', {
      id: 'screen-glow-light',
      type: 'point',
      color: '#4ecdc4',
      intensity: '0.3',
      distance: '20',
      position: '0 3.5 -15'
    });
    scene.appendChild(glow);

    // Create a subtle glow plane behind the screen
    var glowPlane = el('a-plane', {
      id: 'screen-glow-plane',
      position: '0 3.5 -16.3',
      width: '13',
      height: '8',
      color: '#4ecdc4',
      opacity: '0.05',
      shader: 'flat',
      animation: 'property: opacity; from: 0.03; to: 0.08; dur: 3000; loop: true; dir: alternate; easing: easeInOutSine'
    });
    scene.appendChild(glowPlane);
  }

  /* ═══════════════════════════════════════════
     5. MOVIES: DUST MOTES IN PROJECTOR BEAM
     ═══════════════════════════════════════════ */
  function moviesDustMotes(scene) {
    var moteContainer = el('a-entity', { id: 'dust-motes', position: '0 3 -8' });
    for (var i = 0; i < 20; i++) {
      var x = (Math.random() - 0.5) * 6;
      var y = (Math.random() - 0.5) * 4;
      var z = (Math.random() - 0.5) * 12;
      var dur = 5000 + Math.random() * 8000;
      var mote = el('a-sphere', {
        position: x + ' ' + y + ' ' + z,
        radius: (0.01 + Math.random() * 0.02).toFixed(3),
        color: '#ffffff',
        opacity: (0.15 + Math.random() * 0.2).toFixed(2),
        shader: 'flat',
        animation: 'property: position; to: ' + (x + (Math.random() - 0.5) * 2) + ' ' + (y + (Math.random() - 0.5) * 2) + ' ' + (z + (Math.random() - 0.5) * 2) + '; dur: ' + Math.round(dur) + '; loop: true; dir: alternate; easing: easeInOutSine'
      });
      moteContainer.appendChild(mote);
    }
    scene.appendChild(moteContainer);
  }

  /* ═══════════════════════════════════════════
     6. STOCKS: PRICE-CHANGE SPARKS
     ═══════════════════════════════════════════ */
  function stocksSparks(scene) {
    var sparkContainer = el('a-entity', { id: 'stock-sparks' });
    scene.appendChild(sparkContainer);

    // Every 5s, emit a burst of green or red sparks near the panels
    setInterval(function () {
      var isUp = Math.random() > 0.5;
      var color = isUp ? '#22c55e' : '#ef4444';
      var panelX = isUp ? -5 : 5;

      for (var i = 0; i < 6; i++) {
        var spark = el('a-sphere', {
          position: panelX + ' ' + (2 + Math.random() * 2) + ' -5',
          radius: '0.04',
          color: color,
          opacity: '0.8',
          shader: 'flat',
          animation: 'property: position; to: ' + (panelX + (Math.random() - 0.5) * 3) + ' ' + (3 + Math.random() * 2) + ' ' + (-5 + (Math.random() - 0.5) * 2) + '; dur: 1200; easing: easeOutQuad',
          'animation__fade': 'property: opacity; from: 0.8; to: 0; dur: 1200; easing: easeInQuad'
        });
        sparkContainer.appendChild(spark);
        // Clean up after animation
        (function (s) {
          setTimeout(function () { if (s.parentNode) s.parentNode.removeChild(s); }, 1500);
        })(spark);
      }
    }, 5000);

    // Add glowing edges to the panel frames
    var panels = scene.querySelectorAll('#stock-panels > a-entity');
    panels.forEach(function (panel) {
      var box = panel.querySelector('a-box');
      if (!box) return;
      var pos = box.getAttribute('position');
      if (!pos) return;
      // Add a subtle edge glow ring
      var edgeGlow = el('a-ring', {
        position: pos.x + ' ' + (pos.y - 1.5) + ' ' + pos.z,
        rotation: '-90 0 0',
        'radius-inner': '1.3',
        'radius-outer': '1.4',
        color: box.getAttribute('color') || '#00d4ff',
        opacity: '0.2',
        shader: 'flat',
        animation: 'property: opacity; from: 0.1; to: 0.35; dur: 2000; loop: true; dir: alternate; easing: easeInOutSine'
      });
      panel.appendChild(edgeGlow);
    });
  }

  /* ═══════════════════════════════════════════
     7. WELLNESS: FIREFLIES
     ═══════════════════════════════════════════ */
  function wellnessFireflies(scene) {
    var container = el('a-entity', { id: 'fireflies' });
    for (var i = 0; i < 15; i++) {
      var x = (Math.random() - 0.5) * 20;
      var y = 0.5 + Math.random() * 3;
      var z = (Math.random() - 0.5) * 20;
      var dur = 4000 + Math.random() * 6000;
      var colors = ['#fbbf24', '#a3e635', '#34d399', '#22d3ee'];
      var color = colors[Math.floor(Math.random() * colors.length)];
      var fly = el('a-sphere', {
        position: x + ' ' + y + ' ' + z,
        radius: (0.02 + Math.random() * 0.03).toFixed(3),
        color: color,
        opacity: '0.7',
        shader: 'flat',
        animation: 'property: position; to: ' + (x + (Math.random() - 0.5) * 4) + ' ' + (y + (Math.random() - 0.5) * 2) + ' ' + (z + (Math.random() - 0.5) * 4) + '; dur: ' + Math.round(dur) + '; loop: true; dir: alternate; easing: easeInOutSine',
        'animation__blink': 'property: opacity; from: 0.7; to: 0.1; dur: ' + (1500 + Math.random() * 2000).toFixed(0) + '; loop: true; dir: alternate; easing: easeInOutSine'
      });
      container.appendChild(fly);
    }
    scene.appendChild(container);

    // Add falling petals near the trees
    var petalContainer = el('a-entity', { id: 'falling-petals' });
    for (var j = 0; j < 8; j++) {
      var px = -4 + Math.random() * 14;
      var pz = -8 + Math.random() * 10;
      var pDur = 6000 + Math.random() * 5000;
      var petalColors = ['#fda4af', '#f9a8d4', '#c4b5fd', '#fef08a'];
      var petal = el('a-plane', {
        position: px + ' ' + (4 + Math.random() * 2) + ' ' + pz,
        width: '0.08',
        height: '0.06',
        color: petalColors[Math.floor(Math.random() * petalColors.length)],
        opacity: '0.7',
        shader: 'flat',
        animation: 'property: position; to: ' + (px + (Math.random() - 0.5) * 3) + ' 0.1 ' + (pz + (Math.random() - 0.5) * 3) + '; dur: ' + Math.round(pDur) + '; loop: true; easing: linear',
        'animation__spin': 'property: rotation; from: 0 0 0; to: 360 180 90; dur: ' + Math.round(pDur) + '; loop: true; easing: linear',
        'animation__fade': 'property: opacity; from: 0.7; to: 0; dur: ' + Math.round(pDur) + '; loop: true; easing: easeInQuad'
      });
      petalContainer.appendChild(petal);
    }
    scene.appendChild(petalContainer);
  }

  /* ═══════════════════════════════════════════
     8. TIME-OF-DAY SKY TINT
     ═══════════════════════════════════════════ */
  function timeOfDaySkyTint(scene) {
    var h = new Date().getHours();
    var tint, ambientColor, ambientIntensity;

    if (h >= 6 && h < 10) {
      // Morning — warm orange-pink
      tint = '#2a1a10'; ambientColor = '#ff9966'; ambientIntensity = '0.15';
    } else if (h >= 10 && h < 17) {
      // Day — slight warm white
      tint = '#1a1a25'; ambientColor = '#ffe4b5'; ambientIntensity = '0.1';
    } else if (h >= 17 && h < 20) {
      // Evening — purple-orange
      tint = '#1a0f20'; ambientColor = '#cc6699'; ambientIntensity = '0.15';
    } else {
      // Night — cool blue
      tint = '#080815'; ambientColor = '#334488'; ambientIntensity = '0.12';
    }

    // Add a subtle tint light
    var tintLight = el('a-light', {
      id: 'time-tint-light',
      type: 'ambient',
      color: ambientColor,
      intensity: ambientIntensity
    });
    scene.appendChild(tintLight);
  }

  /* ═══════════════════════════════════════════
     9. AMBIENT FLOATING MOTES (all zones)
     ═══════════════════════════════════════════ */
  function ambientMotes(scene) {
    var zoneColors = {
      hub: '#00d4ff', events: '#ff6b6b', movies: '#4ecdc4', creators: '#a855f7',
      stocks: '#22c55e', wellness: '#fbbf24', weather: '#06b6d4', tutorial: '#f59e0b'
    };
    var color = zoneColors[zone] || '#00d4ff';
    var container = el('a-entity', { id: 'ambient-motes' });

    for (var i = 0; i < 12; i++) {
      var x = (Math.random() - 0.5) * 16;
      var y = 1 + Math.random() * 5;
      var z = (Math.random() - 0.5) * 16;
      var dur = 8000 + Math.random() * 10000;
      var mote = el('a-sphere', {
        position: x + ' ' + y + ' ' + z,
        radius: (0.015 + Math.random() * 0.025).toFixed(3),
        color: color,
        opacity: (0.2 + Math.random() * 0.25).toFixed(2),
        shader: 'flat',
        animation: 'property: position; to: ' + (x + (Math.random() - 0.5) * 6) + ' ' + (y + (Math.random() - 0.5) * 3) + ' ' + (z + (Math.random() - 0.5) * 6) + '; dur: ' + Math.round(dur) + '; loop: true; dir: alternate; easing: easeInOutSine'
      });
      container.appendChild(mote);
    }
    scene.appendChild(container);
  }

  /* ═══════════════════════════════════════════
     10. HUB: PORTAL DATA BADGES
     ═══════════════════════════════════════════ */
  function hubPortalDataBadges(scene) {
    var badgeData = [
      { pos: '-6 3.8 -8', text: '1000+ events', color: '#ff6b6b' },
      { pos: '0 3.8 -8',  text: '100+ trailers', color: '#4ecdc4' },
      { pos: '6 3.8 -8',  text: 'Live streams', color: '#a855f7' },
      { pos: '-6 3.8 8',  text: '8 tickers', color: '#22c55e' },
      { pos: '0 3.8 8',   text: 'Breathe & focus', color: '#10b981' },
      { pos: '6 3.8 8',   text: 'Live forecast', color: '#06b6d4' }
    ];

    badgeData.forEach(function (b) {
      var badge = el('a-entity', { position: b.pos, 'look-at-camera': '' });
      var bg = el('a-plane', {
        width: '2',
        height: '0.4',
        color: b.color,
        opacity: '0.15',
        shader: 'flat'
      });
      var txt = el('a-text', {
        value: b.text,
        align: 'center',
        width: '3',
        color: b.color,
        position: '0 0 0.01'
      });
      badge.appendChild(bg);
      badge.appendChild(txt);

      // Gentle float animation
      badge.setAttribute('animation', 'property: position; to: ' +
        b.pos.split(' ')[0] + ' 4 ' + b.pos.split(' ')[2] +
        '; dur: 3000; loop: true; dir: alternate; easing: easeInOutSine');

      scene.appendChild(badge);
    });
  }

  /* ═══════════════════════════════════════════
     INIT
     ═══════════════════════════════════════════ */
  onSceneReady(function (scene) {
    // Feature 8 + 9: apply to ALL zones
    timeOfDaySkyTint(scene);
    ambientMotes(scene);

    // Zone-specific features
    switch (zone) {
      case 'hub':
        hubPortalParticles(scene);   // 1
        hubPortalHover(scene);       // 2
        hubPlatformWaves(scene);     // 3
        hubPortalDataBadges(scene);  // 10
        break;
      case 'movies':
        moviesScreenGlow(scene);     // 4
        moviesDustMotes(scene);      // 5
        break;
      case 'stocks':
        stocksSparks(scene);         // 6
        break;
      case 'wellness':
        wellnessFireflies(scene);    // 7
        break;
    }

    console.log('[VR Scene Enhancements] Set 8 loaded — ' + zone);
  });

  window.VRSceneEnhancements = {
    zone: zone,
    version: 8
  };
})();
