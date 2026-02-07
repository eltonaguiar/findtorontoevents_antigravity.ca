/**
 * Meta Quest 3 Controller Support & Teleport Movement
 *
 * Included on ALL VR pages. Provides:
 *   - Quest 3 controller models (oculus-touch-controls)
 *   - Left thumbstick: smooth locomotion
 *   - Right thumbstick forward: parabolic teleport with arc + landing circle
 *   - Right thumbstick horizontal: snap turn
 *   - Laser pointer interaction from both hands
 *   - Hand tracking fallback
 *   - Desktop: WASD + mouse still works
 *   - Controller guide popup on VR entry
 *
 * Camera rig must use: <a-entity id="rig"><a-camera ...></a-camera></a-entity>
 */
(function () {
  'use strict';

  /* ── Config ── */
  var CONFIG = {
    teleport: {
      maxDistance: 20,
      arcSteps: 30,
      gravity: -9.8,
      initialSpeed: 8,
      validColor: '#00d4ff',
      invalidColor: '#ef4444',
      circleRadius: 0.3,
      dt: 0.06
    },
    movement: {
      speed: 3.0,
      deadzone: 0.15,
      snapAngle: 45,
      snapCooldownMs: 350
    }
  };

  /* ── State ── */
  var isVR = false;
  var teleportActive = false;
  var teleportValid = false;
  var teleportLandingPoint = null;
  var teleportIndicator = null;
  var teleportArcEl = null;
  var cameraRig = null;
  var scene = null;
  var lastSnapTime = 0;
  var hintEntity = null;
  var leftCtrl = null;
  var rightCtrl = null;

  /* ── Helpers ── */
  function v3(x, y, z) { return new THREE.Vector3(x, y, z); }

  /* ═══════════════════════════════════════════
     INITIALIZATION
     ═══════════════════════════════════════════ */
  function init() {
    var attempts = 0;
    var check = setInterval(function () {
      attempts++;
      scene = document.querySelector('a-scene');
      if (scene && scene.hasLoaded) {
        clearInterval(check);
        setupScene();
      } else if (scene) {
        scene.addEventListener('loaded', function () {
          clearInterval(check);
          setupScene();
        });
        clearInterval(check);
      }
      if (attempts > 100) clearInterval(check); // 10s
    }, 100);
  }

  function setupScene() {
    // Find the camera rig — pages use #rig or #camera-rig
    cameraRig = document.getElementById('rig')
             || document.getElementById('camera-rig')
             || findCameraParent();

    if (!cameraRig) {
      console.warn('[Controller Support] No camera rig found (#rig or #camera-rig). Creating wrapper.');
      createCameraRig();
    }

    scene.addEventListener('enter-vr', onEnterVR);
    scene.addEventListener('exit-vr', onExitVR);

    createTeleportVisuals();
    ensureControllers();
    startInputLoop();

    console.log('[Controller Support] Ready. Rig:', cameraRig.id || '(unnamed)');
  }

  // Fallback: find the parent of the <a-camera>
  function findCameraParent() {
    var cam = document.querySelector('a-camera');
    if (cam && cam.parentNode && cam.parentNode.tagName &&
        cam.parentNode.tagName.toLowerCase().indexOf('a-') === 0) {
      return cam.parentNode;
    }
    return null;
  }

  function createCameraRig() {
    var cam = document.querySelector('a-camera');
    if (!cam) return;
    var rig = document.createElement('a-entity');
    rig.id = 'rig';
    cam.parentNode.insertBefore(rig, cam);
    rig.appendChild(cam);
    cameraRig = rig;
  }

  /* ═══════════════════════════════════════════
     CONTROLLERS — ensure left + right hands exist
     ═══════════════════════════════════════════ */
  function ensureControllers() {
    if (!cameraRig) return;

    // ── Left hand ──
    leftCtrl = cameraRig.querySelector('#left-hand')
            || cameraRig.querySelector('#left-controller');
    if (!leftCtrl) {
      leftCtrl = document.createElement('a-entity');
      leftCtrl.id = 'left-hand';
      cameraRig.appendChild(leftCtrl);
    }
    // Ensure components
    if (!leftCtrl.hasAttribute('laser-controls')) {
      leftCtrl.setAttribute('laser-controls', 'hand: left');
    }
    if (!leftCtrl.hasAttribute('raycaster') ||
        leftCtrl.getAttribute('raycaster').toString().indexOf('.clickable') === -1) {
      leftCtrl.setAttribute('raycaster', 'objects: .clickable; far: 25; lineColor: #00d4ff; lineOpacity: 0.5');
    }
    if (!leftCtrl.hasAttribute('cursor')) {
      leftCtrl.setAttribute('cursor', 'rayOrigin: entity; fuse: false');
    }

    // ── Right hand ──
    rightCtrl = cameraRig.querySelector('#right-hand')
             || cameraRig.querySelector('#right-controller');
    if (!rightCtrl) {
      rightCtrl = document.createElement('a-entity');
      rightCtrl.id = 'right-hand';
      cameraRig.appendChild(rightCtrl);
    }
    if (!rightCtrl.hasAttribute('laser-controls')) {
      rightCtrl.setAttribute('laser-controls', 'hand: right');
    }
    if (!rightCtrl.hasAttribute('raycaster') ||
        rightCtrl.getAttribute('raycaster').toString().indexOf('.clickable') === -1) {
      rightCtrl.setAttribute('raycaster', 'objects: .clickable; far: 25; lineColor: #a855f7; lineOpacity: 0.5');
    }
    if (!rightCtrl.hasAttribute('cursor')) {
      rightCtrl.setAttribute('cursor', 'rayOrigin: entity; fuse: false');
    }

    // Log connected controllers
    leftCtrl.addEventListener('controllerconnected', function (e) {
      console.log('[Controller] Left connected:', e.detail.name);
    });
    rightCtrl.addEventListener('controllerconnected', function (e) {
      console.log('[Controller] Right connected:', e.detail.name);
    });
  }

  /* ═══════════════════════════════════════════
     TELEPORT VISUALS
     ═══════════════════════════════════════════ */
  function createTeleportVisuals() {
    // Reuse existing indicator if present (e.g. Hub has one)
    teleportIndicator = document.getElementById('vr-teleport-indicator')
                     || document.getElementById('teleport-indicator');
    if (!teleportIndicator) {
      teleportIndicator = document.createElement('a-entity');
      teleportIndicator.id = 'vr-teleport-indicator';
      teleportIndicator.setAttribute('visible', 'false');
      teleportIndicator.innerHTML =
        '<a-ring rotation="-90 0 0" radius-inner="0.22" radius-outer="0.35" color="#00d4ff" ' +
        '  opacity="0.8" material="shader: flat; transparent: true" position="0 0.02 0"' +
        '  animation="property: scale; from: 0.85 0.85 0.85; to: 1.15 1.15 1.15; dur: 700; loop: true; dir: alternate"></a-ring>' +
        '<a-ring rotation="-90 0 0" radius-inner="0.04" radius-outer="0.07" color="#ffffff" ' +
        '  opacity="0.9" material="shader: flat" position="0 0.025 0"></a-ring>' +
        '<a-cylinder radius="0.02" height="1.5" color="#00d4ff" opacity="0.3" position="0 0.75 0"></a-cylinder>';
      scene.appendChild(teleportIndicator);
    }

    teleportArcEl = document.getElementById('vr-teleport-arc');
    if (!teleportArcEl) {
      teleportArcEl = document.createElement('a-entity');
      teleportArcEl.id = 'vr-teleport-arc';
      teleportArcEl.setAttribute('visible', 'false');
      scene.appendChild(teleportArcEl);
    }
  }

  /* ═══════════════════════════════════════════
     INPUT LOOP (runs every frame in VR)
     ═══════════════════════════════════════════ */
  function startInputLoop() {
    var lastTime = 0;
    function loop(time) {
      var dt = lastTime ? (time - lastTime) : 16;
      lastTime = time;
      if (isVR) {
        processGamepads(dt);
      }
      requestAnimationFrame(loop);
    }
    requestAnimationFrame(loop);
  }

  function processGamepads(dt) {
    if (!navigator.getGamepads) return;
    var gamepads = navigator.getGamepads();
    var leftGP = null;
    var rightGP = null;

    for (var i = 0; i < gamepads.length; i++) {
      var gp = gamepads[i];
      if (!gp || !gp.connected) continue;

      // Identify hand
      if (gp.hand === 'left') {
        leftGP = gp;
      } else if (gp.hand === 'right') {
        rightGP = gp;
      } else if (gp.id) {
        var id = gp.id.toLowerCase();
        if (id.indexOf('left') !== -1) leftGP = gp;
        else if (id.indexOf('right') !== -1) rightGP = gp;
      }
    }

    if (leftGP) handleLeftStick(leftGP, dt);
    if (rightGP) handleRightStick(rightGP, dt);
  }

  /* ── Left thumbstick: smooth locomotion ── */
  function handleLeftStick(gp, dt) {
    if (!gp.axes || gp.axes.length < 4) return;
    if (!cameraRig) return;

    var x = gp.axes[2]; // thumbstick X
    var z = gp.axes[3]; // thumbstick Y (forward/back)
    var dz = CONFIG.movement.deadzone;
    if (Math.abs(x) < dz) x = 0;
    if (Math.abs(z) < dz) z = 0;
    if (x === 0 && z === 0) return;

    var cam = scene.camera;
    if (!cam) return;

    // Camera forward/right projected onto XZ plane
    var forward = v3(0, 0, 0);
    cam.getWorldDirection(forward);
    forward.y = 0;
    forward.normalize();

    var right = v3(0, 0, 0);
    right.crossVectors(forward, v3(0, 1, 0));
    right.normalize();

    var speed = CONFIG.movement.speed * (dt / 1000);
    var move = v3(0, 0, 0);
    move.addScaledVector(right, x * speed);
    move.addScaledVector(forward, -z * speed); // thumbstick Y inverted

    cameraRig.object3D.position.add(move);
  }

  /* ── Right thumbstick: teleport (forward push) + snap turn (left/right) ── */
  function handleRightStick(gp, dt) {
    if (!gp.axes || gp.axes.length < 4) return;

    var x = gp.axes[2];
    var y = gp.axes[3];
    var dz = CONFIG.movement.deadzone;

    // ── Snap turn (horizontal) ──
    if (Math.abs(x) > 0.7 && Math.abs(y) < 0.5) {
      var now = Date.now();
      if (now - lastSnapTime > CONFIG.movement.snapCooldownMs) {
        lastSnapTime = now;
        var dir = x > 0 ? -CONFIG.movement.snapAngle : CONFIG.movement.snapAngle;
        if (cameraRig) {
          var rot = cameraRig.getAttribute('rotation') || { x: 0, y: 0, z: 0 };
          cameraRig.setAttribute('rotation', { x: rot.x, y: rot.y + dir, z: rot.z });
        }
        pulseHaptics(rightCtrl, 0.15, 80);
      }
      return; // don't also teleport while snap turning
    }

    // ── Teleport (push forward) ──
    if (y < -0.4) {
      if (!teleportActive) {
        teleportActive = true;
        showTeleportVisuals(true);
        pulseHaptics(rightCtrl, 0.1, 60);
      }
      updateTeleportArc();
    } else {
      if (teleportActive) {
        // Release — execute teleport
        executeTeleport();
        teleportActive = false;
        showTeleportVisuals(false);
      }
    }

    // Cancel with B button (button index 5 on Quest)
    if (gp.buttons.length > 5 && gp.buttons[5] && gp.buttons[5].pressed) {
      cancelTeleport();
    }
  }

  /* ═══════════════════════════════════════════
     TELEPORT LOGIC
     ═══════════════════════════════════════════ */
  function showTeleportVisuals(show) {
    if (teleportIndicator) teleportIndicator.setAttribute('visible', show);
    if (teleportArcEl) teleportArcEl.setAttribute('visible', show);
  }

  function updateTeleportArc() {
    if (!rightCtrl || !rightCtrl.object3D) return;

    // Get controller world position + direction
    var startPos = v3(0, 0, 0);
    rightCtrl.object3D.getWorldPosition(startPos);

    var dir = v3(0, 0, -1);
    rightCtrl.object3D.getWorldDirection(dir);
    dir.multiplyScalar(CONFIG.teleport.initialSpeed);
    // Add slight upward arc
    dir.y = Math.max(dir.y, 2);

    // Calculate parabolic arc
    var points = [];
    var pos = startPos.clone();
    var vel = dir.clone();
    var grav = CONFIG.teleport.gravity;
    var dtt = CONFIG.teleport.dt;
    var valid = false;

    for (var i = 0; i < CONFIG.teleport.arcSteps; i++) {
      points.push(pos.clone());
      pos.x += vel.x * dtt;
      pos.y += vel.y * dtt;
      pos.z += vel.z * dtt;
      vel.y += grav * dtt;

      // Hit ground?
      if (pos.y <= 0.05) {
        pos.y = 0;
        points.push(pos.clone());
        valid = true;
        break;
      }
      // Too far?
      if (startPos.distanceTo(pos) > CONFIG.teleport.maxDistance) break;
    }

    teleportValid = valid;
    teleportLandingPoint = valid ? pos.clone() : null;

    // Draw arc with dots
    var html = '';
    for (var j = 0; j < points.length; j++) {
      var p = points[j];
      var opacity = 0.3 + (j / points.length) * 0.5;
      var col = valid ? CONFIG.teleport.validColor : CONFIG.teleport.invalidColor;
      html += '<a-sphere position="' + p.x.toFixed(2) + ' ' + p.y.toFixed(2) + ' ' + p.z.toFixed(2) +
              '" radius="0.02" color="' + col + '" opacity="' + opacity.toFixed(2) +
              '" material="shader: flat"></a-sphere>';
    }
    if (teleportArcEl) teleportArcEl.innerHTML = html;

    // Update indicator
    if (teleportIndicator && teleportLandingPoint) {
      teleportIndicator.object3D.position.set(
        teleportLandingPoint.x,
        teleportLandingPoint.y + 0.02,
        teleportLandingPoint.z
      );
      var ring = teleportIndicator.querySelector('a-ring');
      if (ring) ring.setAttribute('color', valid ? CONFIG.teleport.validColor : CONFIG.teleport.invalidColor);
    }
  }

  function executeTeleport() {
    if (!teleportValid || !teleportLandingPoint || !cameraRig) {
      cancelTeleport();
      return;
    }

    var lp = teleportLandingPoint;
    var rigPos = cameraRig.object3D.position;

    // Smooth blink teleport
    cameraRig.setAttribute('animation', {
      property: 'position',
      to: lp.x + ' ' + rigPos.y + ' ' + lp.z,
      dur: 180,
      easing: 'easeOutQuad'
    });

    pulseHaptics(rightCtrl, 0.35, 150);
    cancelTeleport();
  }

  function cancelTeleport() {
    teleportActive = false;
    teleportValid = false;
    teleportLandingPoint = null;
    showTeleportVisuals(false);
    if (teleportArcEl) teleportArcEl.innerHTML = '';
  }

  /* ═══════════════════════════════════════════
     HAPTICS
     ═══════════════════════════════════════════ */
  function pulseHaptics(ctrlEl, intensity, duration) {
    if (!ctrlEl) return;
    try {
      // Try A-Frame component API
      var comp = ctrlEl.components['oculus-touch-controls'] ||
                 ctrlEl.components['laser-controls'];
      if (comp && comp.controller && comp.controller.hapticActuators) {
        comp.controller.hapticActuators[0].pulse(intensity, duration);
        return;
      }
      // Try WebXR gamepad
      var gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
      for (var i = 0; i < gamepads.length; i++) {
        var gp = gamepads[i];
        if (gp && gp.hapticActuators && gp.hapticActuators.length > 0) {
          gp.hapticActuators[0].pulse(intensity, duration);
        }
      }
    } catch (e) { /* haptics optional */ }
  }

  /* ═══════════════════════════════════════════
     VR MODE HANDLERS
     ═══════════════════════════════════════════ */
  function onEnterVR() {
    console.log('[Controller Support] Entered VR');
    isVR = true;
    // Re-ensure controllers are properly attached
    setTimeout(function () {
      ensureControllers();
      showControllerGuide();
    }, 500);
  }

  function onExitVR() {
    console.log('[Controller Support] Exited VR');
    isVR = false;
    cancelTeleport();
    if (hintEntity && hintEntity.parentNode) hintEntity.parentNode.removeChild(hintEntity);
  }

  function showControllerGuide() {
    // Show a floating guide panel near the user for 12 seconds
    if (hintEntity && hintEntity.parentNode) hintEntity.parentNode.removeChild(hintEntity);

    hintEntity = document.createElement('a-entity');
    hintEntity.setAttribute('position', '0 1.8 -2');

    hintEntity.innerHTML =
      '<a-plane width="2.8" height="1.6" color="#0a0a1a" opacity="0.92" material="shader: flat"></a-plane>' +
      '<a-plane width="2.82" height="1.62" color="#00d4ff" opacity="0.3" position="0 0 -0.005" material="shader: flat; wireframe: true"></a-plane>' +
      '<a-text value="Quest Controls" position="0 0.55 0.01" align="center" width="5" color="#00d4ff"></a-text>' +
      '<a-text value="Left Stick .......... Move around" position="-1.2 0.25 0.01" align="left" width="3.2" color="#ffffff"></a-text>' +
      '<a-text value="Right Stick L/R ..... Snap turn" position="-1.2 0.0 0.01" align="left" width="3.2" color="#ffffff"></a-text>' +
      '<a-text value="Right Stick Fwd ..... Aim teleport" position="-1.2 -0.25 0.01" align="left" width="3.2" color="#ffffff"></a-text>' +
      '<a-text value="Trigger ............. Select / click" position="-1.2 -0.5 0.01" align="left" width="3.2" color="#ffffff"></a-text>' +
      '<a-text value="Menu button ......... Navigation" position="-1.2 -0.75 0.01" align="left" width="3.2" color="#94a3b8"></a-text>';

    // Add close button
    var closeBtn = document.createElement('a-entity');
    closeBtn.setAttribute('position', '1.2 0.6 0.01');
    closeBtn.classList.add('clickable');
    closeBtn.innerHTML = '<a-circle radius="0.12" color="#ef4444" opacity="0.8"></a-circle>' +
                         '<a-text value="X" position="0 0 0.01" align="center" width="3" color="#fff"></a-text>';
    closeBtn.addEventListener('click', function () {
      if (hintEntity && hintEntity.parentNode) hintEntity.parentNode.removeChild(hintEntity);
    });
    hintEntity.appendChild(closeBtn);

    scene.appendChild(hintEntity);

    // Auto-remove after 12 seconds
    setTimeout(function () {
      if (hintEntity && hintEntity.parentNode) hintEntity.parentNode.removeChild(hintEntity);
    }, 12000);
  }

  /* ═══════════════════════════════════════════
     ENH-009: HAND TRACKING SUPPORT
     ═══════════════════════════════════════════ */
  var leftHand = null;
  var rightHand = null;
  var handTrackingActive = false;
  var activeInputMethod = 'keyboard'; // 'keyboard' | 'controllers' | 'hands' | 'gaze'

  function ensureHandTracking() {
    if (!cameraRig) return;

    // Left hand tracking
    leftHand = cameraRig.querySelector('#left-hand-tracking');
    if (!leftHand) {
      leftHand = document.createElement('a-entity');
      leftHand.id = 'left-hand-tracking';
      leftHand.setAttribute('hand-tracking-controls', 'hand: left; modelColor: #00d4ff; modelOpacity: 0.6');
      leftHand.setAttribute('visible', 'false');
      cameraRig.appendChild(leftHand);
    }

    // Right hand tracking
    rightHand = cameraRig.querySelector('#right-hand-tracking');
    if (!rightHand) {
      rightHand = document.createElement('a-entity');
      rightHand.id = 'right-hand-tracking';
      rightHand.setAttribute('hand-tracking-controls', 'hand: right; modelColor: #a855f7; modelOpacity: 0.6');
      rightHand.setAttribute('visible', 'false');
      cameraRig.appendChild(rightHand);
    }

    // Listen for hand tracking events
    leftHand.addEventListener('hand-tracking-extras-ready', function () {
      console.log('[Hand Tracking] Left hand detected');
      handTrackingActive = true;
      setActiveInput('hands');
    });
    rightHand.addEventListener('hand-tracking-extras-ready', function () {
      console.log('[Hand Tracking] Right hand detected');
      handTrackingActive = true;
      setActiveInput('hands');
    });

    // Pinch = select
    leftHand.addEventListener('pinchstarted', function (e) { handlePinch(leftHand, e); });
    rightHand.addEventListener('pinchstarted', function (e) { handlePinch(rightHand, e); });
  }

  function handlePinch(handEl, e) {
    // Use raycaster from hand position to simulate a click
    var worldPos = v3(0, 0, 0);
    handEl.object3D.getWorldPosition(worldPos);
    console.log('[Hand Tracking] Pinch at', worldPos.x.toFixed(2), worldPos.y.toFixed(2), worldPos.z.toFixed(2));
  }

  /* ═══════════════════════════════════════════
     ENH-012: INPUT FAILOVER / AUTO-DETECTION
     ═══════════════════════════════════════════ */
  function setActiveInput(method) {
    if (activeInputMethod === method) return;
    activeInputMethod = method;
    console.log('[Input] Active method:', method);
    updateInputIndicator();

    // Show/hide hand models vs controller models
    if (method === 'hands') {
      if (leftHand) leftHand.setAttribute('visible', 'true');
      if (rightHand) rightHand.setAttribute('visible', 'true');
    } else {
      if (leftHand) leftHand.setAttribute('visible', 'false');
      if (rightHand) rightHand.setAttribute('visible', 'false');
    }
  }

  var inputIndicatorEl = null;

  function updateInputIndicator() {
    // Show a small indicator in the corner of 2D view
    if (!inputIndicatorEl) {
      inputIndicatorEl = document.createElement('div');
      inputIndicatorEl.id = 'vr-input-indicator';
      inputIndicatorEl.style.cssText =
        'position:fixed;bottom:60px;left:12px;z-index:99998;background:rgba(0,0,0,0.7);' +
        'color:#64748b;font-size:11px;padding:4px 10px;border-radius:6px;font-family:system-ui;' +
        'pointer-events:none;transition:all 0.3s;';
      document.body.appendChild(inputIndicatorEl);
    }

    var labels = {
      keyboard: 'Keyboard + Mouse',
      controllers: 'Quest Controllers',
      hands: 'Hand Tracking',
      gaze: 'Gaze (Eye Tracking)'
    };
    var colors = {
      keyboard: '#64748b',
      controllers: '#00d4ff',
      hands: '#a855f7',
      gaze: '#f59e0b'
    };
    inputIndicatorEl.textContent = 'Input: ' + (labels[activeInputMethod] || activeInputMethod);
    inputIndicatorEl.style.color = colors[activeInputMethod] || '#64748b';
  }

  /* Detect which input method is available and auto-switch */
  function detectInputMethod() {
    if (!isVR) {
      setActiveInput('keyboard');
      return;
    }

    // Check for controllers
    var hasControllers = false;
    if (navigator.getGamepads) {
      var gps = navigator.getGamepads();
      for (var i = 0; i < gps.length; i++) {
        if (gps[i] && gps[i].connected && gps[i].axes && gps[i].axes.length >= 2) {
          hasControllers = true;
          break;
        }
      }
    }

    if (hasControllers) {
      setActiveInput('controllers');
    } else if (handTrackingActive) {
      setActiveInput('hands');
    } else {
      // Fallback to gaze
      setActiveInput('gaze');
      ensureGazeFallback();
    }
  }

  function ensureGazeFallback() {
    // If no controllers and no hands, enable gaze cursor on camera
    var cam = document.querySelector('a-camera');
    if (!cam) return;
    var cursor = cam.querySelector('[cursor]');
    if (!cursor) {
      var gazeEl = document.createElement('a-entity');
      gazeEl.setAttribute('cursor', 'fuse: true; fuseTimeout: 2500');
      gazeEl.setAttribute('raycaster', 'objects: .clickable; far: 20');
      gazeEl.setAttribute('position', '0 0 -1');
      gazeEl.innerHTML = '<a-ring radius-inner="0.01" radius-outer="0.02" color="#f59e0b" opacity="0.8" material="shader: flat"></a-ring>';
      cam.appendChild(gazeEl);
      console.log('[Input] Gaze cursor fallback enabled');
    }
  }

  /* Run input detection periodically */
  var inputDetectInterval = null;
  function startInputDetection() {
    // Run once immediately then every 3 seconds
    detectInputMethod();
    if (inputDetectInterval) clearInterval(inputDetectInterval);
    inputDetectInterval = setInterval(detectInputMethod, 3000);
  }

  /* ═══════════════════════════════════════════
     PUBLIC API
     ═══════════════════════════════════════════ */
  window.VRControllerSupport = {
    isVR: function () { return isVR; },
    isTeleporting: function () { return teleportActive; },
    cancelTeleport: cancelTeleport,
    pulseHaptics: pulseHaptics,
    showGuide: showControllerGuide,
    getConfig: function () { return CONFIG; },
    getActiveInput: function () { return activeInputMethod; },
    isHandTracking: function () { return handTrackingActive; }
  };

  /* ── Patch setupScene to include hand tracking + input detection ── */
  var _origSetup = setupScene;
  setupScene = function () {
    _origSetup();
    ensureHandTracking();
    startInputDetection();
    updateInputIndicator();
  };

  /* ── Start ── */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
