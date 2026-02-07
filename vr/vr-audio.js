/**
 * VR Spatial Audio Cues
 * Lightweight click/hover/enter sounds using Web Audio API oscillators.
 * No external audio files needed — generates tones procedurally.
 *
 * Include in any zone: <script src="/vr/vr-audio.js"></script>
 */
(function () {
  'use strict';

  var ctx = null;

  function getCtx() {
    if (!ctx) {
      try { ctx = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { return null; }
    }
    if (ctx.state === 'suspended') ctx.resume();
    return ctx;
  }

  function playTone(freq, dur, type, vol) {
    var c = getCtx();
    if (!c) return;
    var osc = c.createOscillator();
    var gain = c.createGain();
    osc.type = type || 'sine';
    osc.frequency.setValueAtTime(freq, c.currentTime);
    gain.gain.setValueAtTime(vol || 0.08, c.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, c.currentTime + dur);
    osc.connect(gain);
    gain.connect(c.destination);
    osc.start(c.currentTime);
    osc.stop(c.currentTime + dur);
  }

  // Hover: soft high ping
  function hoverSound() {
    playTone(880, 0.08, 'sine', 0.05);
  }

  // Click: satisfying double-tap
  function clickSound() {
    playTone(660, 0.06, 'triangle', 0.1);
    setTimeout(function () { playTone(880, 0.1, 'triangle', 0.08); }, 60);
  }

  // Zone enter: ascending chord
  function enterSound() {
    playTone(440, 0.15, 'sine', 0.07);
    setTimeout(function () { playTone(554, 0.15, 'sine', 0.06); }, 80);
    setTimeout(function () { playTone(660, 0.2, 'sine', 0.05); }, 160);
  }

  // Success: bright ding
  function successSound() {
    playTone(784, 0.12, 'sine', 0.08);
    setTimeout(function () { playTone(1047, 0.18, 'sine', 0.06); }, 100);
  }

  // Attach to all clickable elements in the scene
  function init() {
    var scene = document.querySelector('a-scene');
    if (!scene) return;

    // Use event delegation on the scene
    scene.addEventListener('mouseenter', function (e) {
      if (e.target && e.target.classList && e.target.classList.contains('clickable')) {
        hoverSound();
      }
    }, true);

    scene.addEventListener('click', function (e) {
      if (e.target && e.target.classList && e.target.classList.contains('clickable')) {
        clickSound();
      }
    }, true);

    // Zone enter sound on navigation
    var origGoToZone = window.goToZone;
    if (typeof origGoToZone === 'function') {
      window.goToZone = function () {
        enterSound();
        return origGoToZone.apply(this, arguments);
      };
    }
  }

  // Export for manual use
  window.VRAudio = {
    hover: hoverSound,
    click: clickSound,
    enter: enterSound,
    success: successSound
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
