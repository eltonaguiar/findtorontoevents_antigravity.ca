/**
 * VR Mobile-Friendly Handler
 * Shared module that enhances existing VR zone pages for mobile/touch devices.
 * Injects: virtual joystick, touch-friendly UI, responsive overlays, gyro look hints.
 *
 * Include in any zone: <script src="/vr/vr-mobile.js"></script>
 * Must be loaded AFTER the A-Frame scene is in the DOM.
 */
(function () {
  'use strict';

  // ===================== DETECTION =====================
  var _isMobile = null;
  function isMobile() {
    if (_isMobile !== null) return _isMobile;
    var ua = navigator.userAgent || '';
    var mobileRe = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini|Mobile|mobile|CriOS/i;
    var hasTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    var small = window.innerWidth < 1024;
    _isMobile = mobileRe.test(ua) || (hasTouch && small);
    return _isMobile;
  }

  function isQuest() {
    return /OculusBrowser|Quest/i.test(navigator.userAgent || '');
  }

  // Don't run on Quest headsets — they use controllers
  if (isQuest()) return;

  // ===================== RESPONSIVE CSS =====================
  function injectMobileCSS() {
    var style = document.createElement('style');
    style.id = 'vr-mobile-css';
    style.textContent = [
      '/* VR Mobile Responsive */',
      '@media (max-width: 1023px) {',
      '  .clickable { cursor: pointer; }',
      '  #stock-ui, #movie-hud, .back-btn, #instructions, #help-overlay,',
      '  #scroll-hint, #vr-video-controls { font-size: 12px !important; }',
      '  #stock-ui { max-width: 200px !important; padding: 8px !important; font-size: 11px !important; }',
      '  #stock-ui h3 { font-size: 13px !important; }',
      '  .stock-card { padding: 5px !important; margin: 4px 0 !important; }',
      '}',
      '@media (max-width: 767px) {',
      '  #stock-ui { display: none !important; }',
      '  #help-overlay #help-card { padding: 1rem !important; }',
      '  #help-overlay #help-card .columns { grid-template-columns: 1fr !important; }',
      '}',
      '',
      '/* Touch joystick */',
      '#vr-mobile-joystick {',
      '  position: fixed; bottom: 24px; left: 24px; z-index: 9995;',
      '  width: 110px; height: 110px; border-radius: 50%;',
      '  background: rgba(255,255,255,0.08); border: 2px solid rgba(0,212,255,0.4);',
      '  touch-action: none; display: none;',
      '  padding-bottom: env(safe-area-inset-bottom, 0px);',
      '}',
      '#vr-mobile-joystick .knob {',
      '  position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%);',
      '  width: 44px; height: 44px; border-radius: 50%;',
      '  background: linear-gradient(135deg, #00d4ff, #0ea5e9);',
      '  box-shadow: 0 0 14px rgba(0,212,255,0.5);',
      '}',
      '',
      '/* Mobile action bar */',
      '#vr-mobile-bar {',
      '  position: fixed; bottom: 24px; right: 16px; z-index: 9995;',
      '  display: none; flex-direction: column; gap: 12px; align-items: center;',
      '  padding-bottom: env(safe-area-inset-bottom, 0px);',
      '}',
      '#vr-mobile-bar button {',
      '  width: 52px; height: 52px; border-radius: 50%; border: 2px solid rgba(255,255,255,0.25);',
      '  background: rgba(10,10,30,0.8); color: #fff; font-size: 22px;',
      '  backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);',
      '  display: flex; align-items: center; justify-content: center;',
      '}',
      '#vr-mobile-bar button:active { transform: scale(0.9); }',
      '#vr-mobile-bar .primary { background: rgba(0,212,255,0.7); border-color: #00d4ff; }',
      '',
      '/* Mobile top bar */',
      '#vr-mobile-topbar {',
      '  position: fixed; top: 0; left: 0; right: 0; z-index: 9995;',
      '  height: 48px; display: none; align-items: center; justify-content: space-between;',
      '  padding: 0 12px; padding-top: env(safe-area-inset-top, 0px);',
      '  background: linear-gradient(180deg, rgba(10,10,30,0.92), transparent);',
      '  pointer-events: auto;',
      '}',
      '#vr-mobile-topbar a, #vr-mobile-topbar button {',
      '  min-width: 44px; min-height: 44px; display: flex; align-items: center;',
      '  justify-content: center; background: rgba(255,255,255,0.1);',
      '  border: 1px solid rgba(255,255,255,0.15); border-radius: 10px;',
      '  color: #fff; text-decoration: none; font-size: 18px;',
      '}',
      '#vr-mobile-topbar .zone-title {',
      '  font-size: 14px; font-weight: 700; color: #00d4ff;',
      '  pointer-events: none;',
      '}',
      '',
      '/* Orientation hint */',
      '#vr-mobile-orient {',
      '  position: fixed; inset: 0; z-index: 10002; background: #0a0a1f;',
      '  display: none; flex-direction: column; align-items: center; justify-content: center;',
      '  text-align: center; color: #fff; padding: 2rem;',
      '}',
      '#vr-mobile-orient .icon { font-size: 64px; animation: vr-mob-rotate 2s ease-in-out infinite; }',
      '@keyframes vr-mob-rotate { 0%,100%{transform:rotate(0)} 50%{transform:rotate(90deg)} }',
      '#vr-mobile-orient p { color: #888; margin-top: 12px; font-size: 14px; }',
      '',
      '/* Drag-to-look hint */',
      '#vr-mobile-look-hint {',
      '  position: fixed; top: 50%; left: 50%; transform: translate(-50%,-50%);',
      '  z-index: 9994; background: rgba(0,0,0,0.7); color: #888;',
      '  padding: 12px 22px; border-radius: 20px; font-size: 13px;',
      '  pointer-events: none; opacity: 0; transition: opacity 0.4s;',
      '}',
      '#vr-mobile-look-hint.show { opacity: 1; }'
    ].join('\n');
    document.head.appendChild(style);
  }

  // ===================== JOYSTICK =====================
  var joyEl, knobEl, joyActive = false, joyX = 0, joyY = 0, joyStartX, joyStartY;

  function createJoystick() {
    joyEl = document.createElement('div');
    joyEl.id = 'vr-mobile-joystick';
    joyEl.innerHTML = '<div class="knob"></div>';
    document.body.appendChild(joyEl);
    knobEl = joyEl.querySelector('.knob');

    joyEl.addEventListener('touchstart', function (e) {
      e.preventDefault();
      joyActive = true;
      var rect = joyEl.getBoundingClientRect();
      joyStartX = rect.left + rect.width / 2;
      joyStartY = rect.top + rect.height / 2;
    }, { passive: false });

    joyEl.addEventListener('touchmove', function (e) {
      e.preventDefault();
      if (!joyActive) return;
      var t = e.touches[0];
      var dx = t.clientX - joyStartX;
      var dy = t.clientY - joyStartY;
      var maxR = 32;
      var dist = Math.min(Math.sqrt(dx * dx + dy * dy), maxR);
      var angle = Math.atan2(dy, dx);
      var cx = Math.cos(angle) * dist;
      var cy = Math.sin(angle) * dist;
      knobEl.style.transform = 'translate(calc(-50% + ' + cx + 'px), calc(-50% + ' + cy + 'px))';
      joyX = cx / maxR;
      joyY = cy / maxR;
    }, { passive: false });

    function endJoy() {
      joyActive = false;
      joyX = 0; joyY = 0;
      if (knobEl) knobEl.style.transform = 'translate(-50%,-50%)';
    }
    joyEl.addEventListener('touchend', endJoy);
    joyEl.addEventListener('touchcancel', endJoy);
  }

  // Movement loop driven by joystick
  function startMoveLoop() {
    var rig = document.getElementById('rig') || document.getElementById('camera-rig');
    var cam = document.querySelector('a-camera');
    if (!rig) return;
    var speed = 0.055;

    function step() {
      if (joyActive && (Math.abs(joyX) > 0.08 || Math.abs(joyY) > 0.08)) {
        var yaw = cam && cam.object3D ? cam.object3D.rotation.y : 0;
        var dx = Math.sin(yaw) * -joyY + Math.cos(yaw) * joyX;
        var dz = Math.cos(yaw) * -joyY - Math.sin(yaw) * joyX;
        var pos = rig.getAttribute('position');
        rig.setAttribute('position', {
          x: pos.x + dx * speed,
          y: pos.y,
          z: pos.z + dz * speed
        });
      }
      requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  // ===================== ACTION BAR =====================
  function createActionBar() {
    var bar = document.createElement('div');
    bar.id = 'vr-mobile-bar';

    // Hub button
    var hubBtn = document.createElement('button');
    hubBtn.innerHTML = '&#x1F3E0;'; // house
    hubBtn.title = 'Back to Hub';
    hubBtn.addEventListener('click', function () { window.location.href = '/vr/'; });

    // Reset position
    var resetBtn = document.createElement('button');
    resetBtn.innerHTML = '&#x1F504;'; // arrows
    resetBtn.title = 'Reset Position';
    resetBtn.addEventListener('click', function () {
      var rig = document.getElementById('rig') || document.getElementById('camera-rig');
      if (rig) {
        rig.setAttribute('position', '0 1.6 0');
        rig.setAttribute('rotation', '0 0 0');
      }
    });

    // VR enter
    var vrBtn = document.createElement('button');
    vrBtn.className = 'primary';
    vrBtn.innerHTML = '&#x1F97D;'; // goggles
    vrBtn.title = 'Enter VR';
    vrBtn.addEventListener('click', function () {
      var scene = document.querySelector('a-scene');
      if (scene && scene.enterVR) scene.enterVR();
    });

    // Help
    var helpBtn = document.createElement('button');
    helpBtn.innerHTML = '?';
    helpBtn.title = 'Help';
    helpBtn.addEventListener('click', function () {
      // Try existing F1 help overlay first
      var helpOv = document.getElementById('vr-help-overlay');
      if (helpOv) {
        helpOv.style.display = helpOv.style.display === 'flex' ? 'none' : 'flex';
      }
    });

    bar.appendChild(helpBtn);
    bar.appendChild(vrBtn);
    bar.appendChild(resetBtn);
    bar.appendChild(hubBtn);
    document.body.appendChild(bar);
  }

  // ===================== TOP BAR =====================
  function createTopBar() {
    var topbar = document.createElement('div');
    topbar.id = 'vr-mobile-topbar';

    // Back link
    var back = document.createElement('a');
    back.href = '/vr/';
    back.textContent = '\u2190';
    back.title = 'Hub';

    // Zone title
    var title = document.createElement('span');
    title.className = 'zone-title';
    var pageName = document.title.replace(/\s*[-—|].*$/, '').trim();
    title.textContent = pageName || 'VR Zone';

    // Menu button (opens nav-menu if present)
    var menuBtn = document.createElement('button');
    menuBtn.textContent = '\u2630';
    menuBtn.title = 'Menu';
    menuBtn.addEventListener('click', function () {
      // Try existing nav menu
      var navMenu = document.getElementById('vr-nav-menu-2d');
      if (navMenu) {
        navMenu.classList.toggle('active');
        return;
      }
      // Fallback: go to hub
      window.location.href = '/vr/';
    });

    topbar.appendChild(back);
    topbar.appendChild(title);
    topbar.appendChild(menuBtn);
    document.body.appendChild(topbar);
  }

  // ===================== ORIENTATION HINT =====================
  function createOrientationHint() {
    var el = document.createElement('div');
    el.id = 'vr-mobile-orient';
    el.innerHTML = '<div class="icon">&#x1F4F1;</div><h3>Rotate for Best Experience</h3><p>Landscape mode recommended for VR zones</p><button style="margin-top:18px;padding:10px 28px;border-radius:20px;border:1px solid #00d4ff;background:rgba(0,212,255,0.15);color:#00d4ff;font-size:14px;" id="vr-orient-dismiss">Continue Anyway</button>';
    document.body.appendChild(el);

    function check() {
      // Only nag in portrait on phones (not tablets)
      if (window.innerWidth < 600 && window.innerHeight > window.innerWidth) {
        el.style.display = 'flex';
      } else {
        el.style.display = 'none';
      }
    }

    el.querySelector('#vr-orient-dismiss').addEventListener('click', function () {
      el.style.display = 'none';
      el.remove();
    });

    window.addEventListener('resize', check);
    // Only show once on load, don't nag repeatedly
    check();
  }

  // ===================== LOOK HINT =====================
  function showLookHint() {
    var hint = document.createElement('div');
    hint.id = 'vr-mobile-look-hint';
    hint.textContent = '\uD83D\uDC46 Drag to look around';
    document.body.appendChild(hint);
    setTimeout(function () { hint.classList.add('show'); }, 800);
    setTimeout(function () { hint.classList.remove('show'); }, 4000);
    setTimeout(function () { hint.remove(); }, 5000);
  }

  // ===================== ENLARGE CLICK TARGETS =====================
  function enlargeClickTargets() {
    var scene = document.querySelector('a-scene');
    if (!scene) return;

    // Wait for scene to load
    function doEnlarge() {
      var clickables = scene.querySelectorAll('.clickable');
      clickables.forEach(function (el) {
        // Add a larger invisible hit area for small elements
        var geom = el.getAttribute('geometry');
        var w = el.getAttribute('width');
        var h = el.getAttribute('height');
        // If element is small (text buttons, etc.), add padding via a transparent wrapper
        if (geom && geom.primitive === 'plane' && parseFloat(w) < 1.5) {
          el.setAttribute('geometry', 'primitive: plane; width: ' + Math.max(parseFloat(w) * 1.3, 1.5) + '; height: ' + Math.max(parseFloat(h) * 1.3, 0.6));
        }
      });
    }

    if (scene.hasLoaded) doEnlarge();
    else scene.addEventListener('loaded', doEnlarge);
  }

  // ===================== DOUBLE-TAP SELECT =====================
  function setupDoubleTapSelect() {
    var lastTap = 0;
    document.addEventListener('touchend', function (e) {
      var now = Date.now();
      if (now - lastTap < 300) {
        // Simulate a click at center of screen
        var scene = document.querySelector('a-scene');
        if (scene) {
          var cursor = scene.querySelector('[cursor]');
          if (cursor) cursor.emit('click');
        }
      }
      lastTap = now;
    });
  }

  // ===================== PREVENT ZOOM =====================
  function preventPinchZoom() {
    document.addEventListener('gesturestart', function (e) { e.preventDefault(); });
    document.addEventListener('gesturechange', function (e) { e.preventDefault(); });
    document.addEventListener('gestureend', function (e) { e.preventDefault(); });
    // Prevent double-tap zoom on iOS
    var lastTouch = 0;
    document.addEventListener('touchend', function (e) {
      var now = Date.now();
      if (now - lastTouch <= 300) {
        e.preventDefault();
      }
      lastTouch = now;
    }, { passive: false });
  }

  // ===================== SHOW / HIDE MOBILE UI =====================
  function showMobileUI() {
    var joy = document.getElementById('vr-mobile-joystick');
    var bar = document.getElementById('vr-mobile-bar');
    var top = document.getElementById('vr-mobile-topbar');
    if (joy) joy.style.display = 'block';
    if (bar) bar.style.display = 'flex';
    if (top) top.style.display = 'flex';
  }

  // ===================== INIT =====================
  function boot() {
    if (!isMobile()) return;

    injectMobileCSS();
    createJoystick();
    createActionBar();
    createTopBar();
    createOrientationHint();
    showLookHint();
    enlargeClickTargets();
    setupDoubleTapSelect();
    preventPinchZoom();

    // Show UI after scene loads
    var scene = document.querySelector('a-scene');
    if (scene) {
      var show = function () {
        showMobileUI();
        startMoveLoop();
      };
      if (scene.hasLoaded) show();
      else scene.addEventListener('loaded', show);
    }

    // Hide default A-Frame VR button on mobile (we have our own)
    var vrBtn = document.querySelector('.a-enter-vr');
    if (vrBtn) vrBtn.style.display = 'none';

    console.log('[VR-Mobile] Mobile UI activated');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  // Export
  window.VRMobile = {
    isMobile: isMobile,
    isQuest: isQuest
  };
})();
