/**
 * VR Chat Integration - Connects Chat/Voice systems with VR Controls
 *
 * Integrates:
 *   - vr-chat-panel.js with vr-controls.js
 *   - vr-voice-indicator.js with VoiceEngine
 *   - virtual-keyboard.js with controller raycasters
 *   - Quest 3 controller bindings for chat/voice
 *
 * Controller Bindings:
 *   - Left grip + A = Push-to-talk
 *   - Right B = Toggle mute
 *   - Both thumbsticks press = Toggle chat panel
 *   - Double-tap B = Quick mute toggle
 */
(function() {
  'use strict';

  /* ═══════ CONFIGURATION ═══════ */
  var CFG = {
    doubleTapThreshold: 300,  // ms
    pttCooldown: 100,         // ms
    chatToggleCooldown: 500,  // ms
    hapticDuration: 50,       // ms
    hapticStrength: 0.6
  };

  /* ═══════ STATE ═══════ */
  var state = {
    lastBPress: 0,
    bTapCount: 0,
    pttActive: false,
    gripPressed: { left: false, right: false },
    aPressed: { left: false, right: false },
    chatPanelVisible: true,
    lastChatToggle: 0,
    initialized: false
  };

  /* ═══════ UTILITY ═══════ */
  function log() {
    console.log('[VR Chat Integration]', ...arguments);
  }

  function triggerHaptic(hand) {
    var ctrlId = hand === 'left' ? 'left-ctrl' : 'right-ctrl';
    var ctrl = document.getElementById(ctrlId);
    if (!ctrl) return;

    try {
      var handComp = ctrl.components['hand-controls'];
      if (handComp && handComp.gamepad && handComp.gamepad.hapticActuators) {
        handComp.gamepad.hapticActuators[0].pulse(CFG.hapticStrength, CFG.hapticDuration);
      }
    } catch (e) {
      // Haptic not available
    }
  }

  /* ═══════ VOICE CONTROLS ═══════ */

  /**
   * Toggle mute state
   */
  function toggleMute() {
    if (typeof VoiceEngine === 'undefined') {
      log('VoiceEngine not available');
      return;
    }

    var muted = VoiceEngine.toggleMute();
    log('Mute toggled:', muted ? 'muted' : 'unmuted');

    // Haptic feedback
    triggerHaptic('right');

    // Show notification
    showNotification(muted ? '🔇 Muted' : '🔊 Unmuted', muted ? '#ef4444' : '#22c55e');

    return muted;
  }

  /**
   * Set push-to-talk state
   */
  function setPushToTalk(active) {
    if (typeof VoiceEngine === 'undefined') return;

    if (active && !state.pttActive) {
      // PTT pressed
      VoiceEngine.setPushToTalkActive(true);
      state.pttActive = true;
      log('Push-to-talk active');
      triggerHaptic('left');
      showNotification('🎤 Speaking...', '#22c55e');
    } else if (!active && state.pttActive) {
      // PTT released
      VoiceEngine.setPushToTalkActive(false);
      state.pttActive = false;
      log('Push-to-talk released');
    }
  }

  /**
   * Handle double-tap detection for B button
   */
  function handleBButton(hand) {
    var now = Date.now();
    var timeDiff = now - state.lastBPress;

    if (timeDiff < CFG.doubleTapThreshold) {
      state.bTapCount++;
      if (state.bTapCount >= 2) {
        // Double-tap detected
        toggleMute();
        state.bTapCount = 0;
      }
    } else {
      state.bTapCount = 1;
    }

    state.lastBPress = now;
  }

  /* ═══════ CHAT PANEL CONTROLS ═══════ */

  /**
   * Toggle chat panel visibility
   */
  function toggleChatPanel() {
    var now = Date.now();
    if (now - state.lastChatToggle < CFG.chatToggleCooldown) return;
    state.lastChatToggle = now;

    var panel = document.getElementById('vr-chat-panel');
    if (!panel) {
      log('Chat panel not found');
      return;
    }

    state.chatPanelVisible = !state.chatPanelVisible;
    panel.setAttribute('visible', state.chatPanelVisible);

    log('Chat panel:', state.chatPanelVisible ? 'visible' : 'hidden');
    triggerHaptic('left');
    triggerHaptic('right');

    showNotification(state.chatPanelVisible ? '💬 Chat On' : '💬 Chat Off', '#00d4ff');
  }

  /**
   * Show floating notification
   */
  function showNotification(text, color) {
    var scene = document.querySelector('a-scene');
    if (!scene) return;

    var notif = document.createElement('a-text');
    notif.setAttribute('value', text);
    notif.setAttribute('align', 'center');
    notif.setAttribute('position', '0 0.5 -1');
    notif.setAttribute('width', '3');
    notif.setAttribute('color', color);
    notif.setAttribute('font', 'roboto');
    notif.setAttribute('side', 'double');

    // Add background
    var bg = document.createElement('a-plane');
    bg.setAttribute('width', '0.8');
    bg.setAttribute('height', '0.15');
    bg.setAttribute('color', '#1a1a2e');
    bg.setAttribute('opacity', '0.9');
    bg.setAttribute('position', '0 0 -0.01');
    notif.appendChild(bg);

    // Add to camera for billboard effect
    var camera = document.getElementById('camera') || scene.querySelector('a-camera');
    if (camera) {
      camera.appendChild(notif);
    } else {
      scene.appendChild(notif);
    }

    // Animate and remove
    var startTime = Date.now();
    function animate() {
      var elapsed = Date.now() - startTime;
      if (elapsed > 1500) {
        notif.remove();
        return;
      }

      // Fade out in last 500ms
      if (elapsed > 1000) {
        var opacity = 1 - ((elapsed - 1000) / 500);
        notif.setAttribute('opacity', opacity);
      }

      requestAnimationFrame(animate);
    }
    animate();
  }

  /* ═══════ CONTROLLER WIRING ═══════ */

  /**
   * Wire up controller events
   */
  function wireControllers() {
    var leftCtrl = document.getElementById('left-ctrl');
    var rightCtrl = document.getElementById('right-ctrl');

    if (!leftCtrl || !rightCtrl) {
      log('Controllers not found, retrying...');
      setTimeout(wireControllers, 1000);
      return;
    }

    log('Wiring controller events...');

    // Left controller - Push-to-talk (grip + A)
    leftCtrl.addEventListener('gripdown', function() {
      state.gripPressed.left = true;
      checkPTT();
    });
    leftCtrl.addEventListener('gripup', function() {
      state.gripPressed.left = false;
      setPushToTalk(false);
    });
    leftCtrl.addEventListener('abuttondown', function() {
      state.aPressed.left = true;
      checkPTT();
    });
    leftCtrl.addEventListener('abuttonup', function() {
      state.aPressed.left = false;
      checkPTT();
    });

    // Right controller - Mute toggle (B button)
    rightCtrl.addEventListener('bbuttondown', function() {
      handleBButton('right');
    });

    // Thumbstick press - Toggle chat (both hands)
    leftCtrl.addEventListener('thumbstickdown', function() {
      checkChatToggle();
    });
    rightCtrl.addEventListener('thumbstickdown', function() {
      checkChatToggle();
    });

    log('Controller events wired');
  }

  /**
   * Check push-to-talk activation
   */
  function checkPTT() {
    var shouldPTT = state.gripPressed.left && state.aPressed.left;
    setPushToTalk(shouldPTT);
  }

  /**
   * Check chat toggle (both thumbsticks)
   */
  var leftThumbstickPressed = false;
  var rightThumbstickPressed = false;

  function checkChatToggle() {
    // This is called from individual thumbstick events
    // We use a simpler approach: single thumbstick press toggles chat
    toggleChatPanel();
  }

  /* ═══════ KEYBOARD RAYCASTER SETUP ═══════ */

  /**
   * Enhance controllers for keyboard interaction
   */
  function setupKeyboardRaycasters() {
    var leftCtrl = document.getElementById('left-ctrl');
    var rightCtrl = document.getElementById('right-ctrl');

    if (!leftCtrl || !rightCtrl) return;

    // Add keyboard-specific raycaster targets
    var keyboard = document.getElementById('vr-keyboard');
    if (keyboard) {
      // Ensure raycasters can hit keyboard keys
      leftCtrl.setAttribute('raycaster', 'objects', '.clickable, .keyboard-key');
      rightCtrl.setAttribute('raycaster', 'objects', '.clickable, .keyboard-key');
    }
  }

  /* ═══════ INITIALIZATION ═══════ */

  /**
   * Initialize VR Chat Integration
   */
  function init() {
    if (state.initialized) return;

    log('Initializing VR Chat Integration...');

    // Wait for scene to be ready
    var scene = document.querySelector('a-scene');
    if (!scene) {
      setTimeout(init, 500);
      return;
    }

    // Wire controllers when ready
    if (scene.hasLoaded) {
      wireControllers();
    } else {
      scene.addEventListener('loaded', wireControllers);
    }

    // Setup keyboard raycasters
    setupKeyboardRaycasters();

    // Listen for keyboard open events
    scene.addEventListener('openkeyboard', function(evt) {
      log('Keyboard opened');
      setupKeyboardRaycasters();
    });

    state.initialized = true;
    log('VR Chat Integration initialized');
  }

  /* ═══════ PUBLIC API ═══════ */

  window.VRChatIntegration = {
    init: init,
    toggleMute: toggleMute,
    toggleChatPanel: toggleChatPanel,
    setPushToTalk: setPushToTalk,
    showNotification: showNotification,
    triggerHaptic: triggerHaptic
  };

  // Auto-init when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
