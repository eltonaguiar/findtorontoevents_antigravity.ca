/**
 * FPSV4 Audio — Procedural Web Audio system
 */
var FPSV4 = window.FPSV4 || {};

FPSV4.Audio = (function () {
  'use strict';

  var ctx = null;
  var masterGain = null;
  var initialized = false;

  function init() {
    if (initialized) return;
    try {
      ctx = new (window.AudioContext || window.webkitAudioContext)();
      masterGain = ctx.createGain();
      masterGain.gain.value = 0.5;
      masterGain.connect(ctx.destination);
      initialized = true;
      playAmbient();
    } catch (e) { console.warn('[Audio] Not available:', e); }
  }

  function resume() {
    if (ctx && ctx.state === 'suspended') ctx.resume();
  }

  function noiseBuffer(duration) {
    var sr = ctx.sampleRate;
    var len = Math.floor(sr * duration);
    var buf = ctx.createBuffer(1, len, sr);
    var data = buf.getChannelData(0);
    for (var i = 0; i < len; i++) data[i] = Math.random() * 2 - 1;
    return buf;
  }

  // ─── Weapon Sounds ───
  function playGunshot(weaponId) {
    if (!initialized) return;
    resume();
    var now = ctx.currentTime;
    var gain = ctx.createGain();
    gain.connect(masterGain);

    if (weaponId === 'pistol' || weaponId === 'm1911') {
      var osc = ctx.createOscillator();
      osc.type = 'sawtooth'; osc.frequency.setValueAtTime(420, now);
      osc.frequency.exponentialRampToValueAtTime(80, now + 0.08);
      var g2 = ctx.createGain();
      g2.gain.setValueAtTime(0.5, now); g2.gain.exponentialRampToValueAtTime(0.001, now + 0.12);
      osc.connect(g2); g2.connect(gain);
      osc.start(now); osc.stop(now + 0.12);
      var ns = ctx.createBufferSource(); ns.buffer = noiseBuffer(0.06);
      var nf = ctx.createBiquadFilter(); nf.type = 'highpass'; nf.frequency.value = 2000;
      var ng = ctx.createGain(); ng.gain.setValueAtTime(0.4, now); ng.gain.exponentialRampToValueAtTime(0.001, now + 0.06);
      ns.connect(nf); nf.connect(ng); ng.connect(gain);
      ns.start(now); ns.stop(now + 0.06);
      gain.gain.setValueAtTime(0.65, now);
    } else if (weaponId === 'shotgun') {
      var ns2 = ctx.createBufferSource(); ns2.buffer = noiseBuffer(0.15);
      var nf2 = ctx.createBiquadFilter(); nf2.type = 'lowpass'; nf2.frequency.value = 3000;
      var ng2 = ctx.createGain(); ng2.gain.setValueAtTime(0.8, now); ng2.gain.exponentialRampToValueAtTime(0.001, now + 0.15);
      ns2.connect(nf2); nf2.connect(ng2); ng2.connect(gain);
      ns2.start(now); ns2.stop(now + 0.15);
      gain.gain.setValueAtTime(0.8, now);
    } else if (weaponId === 'smg') {
      var osc3 = ctx.createOscillator();
      osc3.type = 'square'; osc3.frequency.setValueAtTime(600, now);
      osc3.frequency.exponentialRampToValueAtTime(100, now + 0.04);
      var og3 = ctx.createGain(); og3.gain.setValueAtTime(0.35, now); og3.gain.exponentialRampToValueAtTime(0.001, now + 0.05);
      osc3.connect(og3); og3.connect(gain);
      osc3.start(now); osc3.stop(now + 0.05);
      gain.gain.setValueAtTime(0.5, now);
    } else if (weaponId === 'assault') {
      var osc4 = ctx.createOscillator();
      osc4.type = 'sawtooth'; osc4.frequency.setValueAtTime(500, now);
      osc4.frequency.exponentialRampToValueAtTime(60, now + 0.07);
      var og4 = ctx.createGain(); og4.gain.setValueAtTime(0.45, now); og4.gain.exponentialRampToValueAtTime(0.001, now + 0.08);
      osc4.connect(og4); og4.connect(gain);
      osc4.start(now); osc4.stop(now + 0.08);
      gain.gain.setValueAtTime(0.6, now);
    } else if (weaponId === 'sniper') {
      var osc5 = ctx.createOscillator();
      osc5.type = 'sawtooth'; osc5.frequency.setValueAtTime(300, now);
      osc5.frequency.exponentialRampToValueAtTime(30, now + 0.2);
      var og5 = ctx.createGain(); og5.gain.setValueAtTime(0.6, now); og5.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
      osc5.connect(og5); og5.connect(gain);
      osc5.start(now); osc5.stop(now + 0.25);
      gain.gain.setValueAtTime(0.8, now);
    } else if (weaponId === 'rocket') {
      var osc6 = ctx.createOscillator();
      osc6.type = 'sawtooth'; osc6.frequency.setValueAtTime(150, now);
      osc6.frequency.linearRampToValueAtTime(800, now + 0.15);
      osc6.frequency.linearRampToValueAtTime(100, now + 0.3);
      var og6 = ctx.createGain(); og6.gain.setValueAtTime(0.5, now); og6.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
      osc6.connect(og6); og6.connect(gain);
      osc6.start(now); osc6.stop(now + 0.35);
      gain.gain.setValueAtTime(0.7, now);
    }
  }

  function playReload() {
    if (!initialized) return;
    resume();
    var now = ctx.currentTime;
    var gain = ctx.createGain(); gain.connect(masterGain); gain.gain.setValueAtTime(0.3, now);
    var o1 = ctx.createOscillator(); o1.type = 'square';
    o1.frequency.setValueAtTime(400, now); o1.frequency.exponentialRampToValueAtTime(200, now + 0.1);
    var g1 = ctx.createGain(); g1.gain.setValueAtTime(0.15, now); g1.gain.exponentialRampToValueAtTime(0.001, now + 0.1);
    o1.connect(g1); g1.connect(gain); o1.start(now); o1.stop(now + 0.1);
    var o2 = ctx.createOscillator(); o2.type = 'square';
    o2.frequency.setValueAtTime(600, now + 0.8); o2.frequency.exponentialRampToValueAtTime(300, now + 0.9);
    var g2 = ctx.createGain(); g2.gain.setValueAtTime(0, now);
    g2.gain.setValueAtTime(0.2, now + 0.8); g2.gain.exponentialRampToValueAtTime(0.001, now + 0.95);
    o2.connect(g2); g2.connect(gain); o2.start(now + 0.8); o2.stop(now + 0.95);
  }

  function playHit() {
    if (!initialized) return;
    resume();
    var now = ctx.currentTime;
    var gain = ctx.createGain(); gain.connect(masterGain); gain.gain.setValueAtTime(0.3, now);
    var osc = ctx.createOscillator();
    osc.type = 'sine'; osc.frequency.setValueAtTime(1200, now);
    osc.frequency.exponentialRampToValueAtTime(800, now + 0.06);
    var g1 = ctx.createGain(); g1.gain.setValueAtTime(0.3, now); g1.gain.exponentialRampToValueAtTime(0.001, now + 0.08);
    osc.connect(g1); g1.connect(gain); osc.start(now); osc.stop(now + 0.08);
  }

  function playHeadshot() {
    if (!initialized) return;
    resume();
    var now = ctx.currentTime;
    var gain = ctx.createGain(); gain.connect(masterGain); gain.gain.setValueAtTime(0.4, now);
    var osc = ctx.createOscillator(); osc.type = 'sine'; osc.frequency.setValueAtTime(2000, now);
    var g1 = ctx.createGain(); g1.gain.setValueAtTime(0.4, now); g1.gain.exponentialRampToValueAtTime(0.001, now + 0.15);
    osc.connect(g1); g1.connect(gain); osc.start(now); osc.stop(now + 0.15);
    var osc2 = ctx.createOscillator(); osc2.type = 'sine'; osc2.frequency.setValueAtTime(3000, now);
    var g2 = ctx.createGain(); g2.gain.setValueAtTime(0.2, now); g2.gain.exponentialRampToValueAtTime(0.001, now + 0.1);
    osc2.connect(g2); g2.connect(gain); osc2.start(now); osc2.stop(now + 0.1);
  }

  function playKill() {
    if (!initialized) return;
    resume();
    var now = ctx.currentTime;
    var gain = ctx.createGain(); gain.connect(masterGain); gain.gain.setValueAtTime(0.35, now);
    [800, 1000, 1200].forEach(function (freq, i) {
      var osc = ctx.createOscillator(); osc.type = 'sine'; osc.frequency.value = freq;
      var g = ctx.createGain();
      g.gain.setValueAtTime(0, now + i * 0.05);
      g.gain.linearRampToValueAtTime(0.3, now + i * 0.05 + 0.02);
      g.gain.exponentialRampToValueAtTime(0.001, now + i * 0.05 + 0.2);
      osc.connect(g); g.connect(gain);
      osc.start(now + i * 0.05); osc.stop(now + i * 0.05 + 0.2);
    });
  }

  function playDamage() {
    if (!initialized) return;
    resume();
    var now = ctx.currentTime;
    var gain = ctx.createGain(); gain.connect(masterGain); gain.gain.setValueAtTime(0.3, now);
    var ns = ctx.createBufferSource(); ns.buffer = noiseBuffer(0.08);
    var nf = ctx.createBiquadFilter(); nf.type = 'lowpass'; nf.frequency.value = 1500;
    var ng = ctx.createGain(); ng.gain.setValueAtTime(0.3, now); ng.gain.exponentialRampToValueAtTime(0.001, now + 0.08);
    ns.connect(nf); nf.connect(ng); ng.connect(gain); ns.start(now); ns.stop(now + 0.08);
  }

  function playFootstep(sprinting) {
    if (!initialized) return;
    resume();
    var now = ctx.currentTime;
    var gain = ctx.createGain(); gain.connect(masterGain);
    gain.gain.setValueAtTime(sprinting ? 0.1 : 0.06, now);
    var ns = ctx.createBufferSource(); ns.buffer = noiseBuffer(0.04);
    var nf = ctx.createBiquadFilter(); nf.type = 'lowpass'; nf.frequency.value = sprinting ? 800 : 500;
    var ng = ctx.createGain(); ng.gain.setValueAtTime(0.12, now); ng.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
    ns.connect(nf); nf.connect(ng); ng.connect(gain); ns.start(now); ns.stop(now + 0.04);
  }

  function playExplosion() {
    if (!initialized) return;
    resume();
    var now = ctx.currentTime;
    var gain = ctx.createGain(); gain.connect(masterGain); gain.gain.setValueAtTime(0.7, now);
    var osc = ctx.createOscillator(); osc.type = 'sine';
    osc.frequency.setValueAtTime(80, now); osc.frequency.exponentialRampToValueAtTime(20, now + 0.5);
    var g1 = ctx.createGain(); g1.gain.setValueAtTime(0.8, now); g1.gain.exponentialRampToValueAtTime(0.001, now + 0.5);
    osc.connect(g1); g1.connect(gain); osc.start(now); osc.stop(now + 0.5);
    var ns = ctx.createBufferSource(); ns.buffer = noiseBuffer(0.3);
    var nf = ctx.createBiquadFilter(); nf.type = 'lowpass';
    nf.frequency.setValueAtTime(3000, now); nf.frequency.exponentialRampToValueAtTime(200, now + 0.3);
    var ng = ctx.createGain(); ng.gain.setValueAtTime(0.6, now); ng.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
    ns.connect(nf); nf.connect(ng); ng.connect(gain); ns.start(now); ns.stop(now + 0.3);
  }

  // ─── Zombie Sounds ───
  function playZombieGroan() {
    if (!initialized) return;
    resume();
    var now = ctx.currentTime;
    var gain = ctx.createGain(); gain.connect(masterGain); gain.gain.setValueAtTime(0.15, now);
    // Low rumbling groan
    var osc = ctx.createOscillator(); osc.type = 'sawtooth';
    var baseFreq = 60 + Math.random() * 40;
    osc.frequency.setValueAtTime(baseFreq, now);
    osc.frequency.linearRampToValueAtTime(baseFreq * 0.7, now + 0.6);
    osc.frequency.linearRampToValueAtTime(baseFreq * 1.1, now + 1.0);
    var g1 = ctx.createGain();
    g1.gain.setValueAtTime(0, now);
    g1.gain.linearRampToValueAtTime(0.15, now + 0.1);
    g1.gain.linearRampToValueAtTime(0.1, now + 0.6);
    g1.gain.exponentialRampToValueAtTime(0.001, now + 1.2);
    var filter = ctx.createBiquadFilter(); filter.type = 'lowpass'; filter.frequency.value = 400;
    osc.connect(filter); filter.connect(g1); g1.connect(gain);
    osc.start(now); osc.stop(now + 1.2);
  }

  function playZombieDeath() {
    if (!initialized) return;
    resume();
    var now = ctx.currentTime;
    var gain = ctx.createGain(); gain.connect(masterGain); gain.gain.setValueAtTime(0.25, now);
    // Death screech
    var osc = ctx.createOscillator(); osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(200, now);
    osc.frequency.exponentialRampToValueAtTime(50, now + 0.4);
    var g1 = ctx.createGain(); g1.gain.setValueAtTime(0.25, now); g1.gain.exponentialRampToValueAtTime(0.001, now + 0.4);
    var filter = ctx.createBiquadFilter(); filter.type = 'lowpass'; filter.frequency.value = 600;
    osc.connect(filter); filter.connect(g1); g1.connect(gain);
    osc.start(now); osc.stop(now + 0.4);
    // Thud
    var ns = ctx.createBufferSource(); ns.buffer = noiseBuffer(0.08);
    var nf = ctx.createBiquadFilter(); nf.type = 'lowpass'; nf.frequency.value = 300;
    var ng = ctx.createGain(); ng.gain.setValueAtTime(0, now);
    ng.gain.setValueAtTime(0.2, now + 0.3); ng.gain.exponentialRampToValueAtTime(0.001, now + 0.4);
    ns.connect(nf); nf.connect(ng); ng.connect(gain); ns.start(now + 0.3); ns.stop(now + 0.4);
  }

  function playZombieAttack() {
    if (!initialized) return;
    resume();
    var now = ctx.currentTime;
    var gain = ctx.createGain(); gain.connect(masterGain); gain.gain.setValueAtTime(0.2, now);
    var osc = ctx.createOscillator(); osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(150, now);
    osc.frequency.linearRampToValueAtTime(250, now + 0.05);
    osc.frequency.exponentialRampToValueAtTime(60, now + 0.2);
    var g1 = ctx.createGain(); g1.gain.setValueAtTime(0.2, now); g1.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
    var filter = ctx.createBiquadFilter(); filter.type = 'bandpass'; filter.frequency.value = 300; filter.Q.value = 3;
    osc.connect(filter); filter.connect(g1); g1.connect(gain);
    osc.start(now); osc.stop(now + 0.25);
  }

  // ─── Round Sounds ───
  function playRoundStart() {
    if (!initialized) return;
    resume();
    var now = ctx.currentTime;
    var gain = ctx.createGain(); gain.connect(masterGain); gain.gain.setValueAtTime(0.3, now);
    // Rising tone
    [400, 500, 600, 800].forEach(function (freq, i) {
      var osc = ctx.createOscillator(); osc.type = 'sine'; osc.frequency.value = freq;
      var g = ctx.createGain();
      g.gain.setValueAtTime(0, now + i * 0.12);
      g.gain.linearRampToValueAtTime(0.2, now + i * 0.12 + 0.05);
      g.gain.exponentialRampToValueAtTime(0.001, now + i * 0.12 + 0.25);
      osc.connect(g); g.connect(gain);
      osc.start(now + i * 0.12); osc.stop(now + i * 0.12 + 0.25);
    });
  }

  function playRoundEnd() {
    if (!initialized) return;
    resume();
    var now = ctx.currentTime;
    var gain = ctx.createGain(); gain.connect(masterGain); gain.gain.setValueAtTime(0.25, now);
    // Descending ding
    [1000, 800, 600].forEach(function (freq, i) {
      var osc = ctx.createOscillator(); osc.type = 'sine'; osc.frequency.value = freq;
      var g = ctx.createGain();
      g.gain.setValueAtTime(0, now + i * 0.15);
      g.gain.linearRampToValueAtTime(0.25, now + i * 0.15 + 0.04);
      g.gain.exponentialRampToValueAtTime(0.001, now + i * 0.15 + 0.3);
      osc.connect(g); g.connect(gain);
      osc.start(now + i * 0.15); osc.stop(now + i * 0.15 + 0.3);
    });
  }

  function playKnifeSwing() {
    if (!initialized) return;
    resume();
    var now = ctx.currentTime;
    var gain = ctx.createGain(); gain.connect(masterGain); gain.gain.setValueAtTime(0.2, now);
    var ns = ctx.createBufferSource(); ns.buffer = noiseBuffer(0.1);
    var nf = ctx.createBiquadFilter(); nf.type = 'highpass'; nf.frequency.value = 3000;
    var ng = ctx.createGain(); ng.gain.setValueAtTime(0.2, now); ng.gain.exponentialRampToValueAtTime(0.001, now + 0.1);
    ns.connect(nf); nf.connect(ng); ng.connect(gain); ns.start(now); ns.stop(now + 0.1);
  }

  // ─── Ambient ───
  function playAmbient() {
    if (!initialized) return;
    resume();
    var now = ctx.currentTime;
    // Low ominous drone
    var osc = ctx.createOscillator(); osc.type = 'sine'; osc.frequency.value = 45;
    var lfo = ctx.createOscillator(); lfo.type = 'sine'; lfo.frequency.value = 0.08;
    var lfoGain = ctx.createGain(); lfoGain.gain.value = 4;
    lfo.connect(lfoGain); lfoGain.connect(osc.frequency);
    var gain = ctx.createGain(); gain.connect(masterGain); gain.gain.value = 0.04;
    osc.connect(gain); osc.start(now); lfo.start(now);
    // Wind-like noise
    var windNs = ctx.createBufferSource(); windNs.buffer = noiseBuffer(30); windNs.loop = true;
    var windF = ctx.createBiquadFilter(); windF.type = 'bandpass'; windF.frequency.value = 200; windF.Q.value = 0.5;
    var windG = ctx.createGain(); windG.gain.value = 0.02;
    windNs.connect(windF); windF.connect(windG); windG.connect(masterGain);
    windNs.start(now);
  }

  function setVolume(vol) {
    if (masterGain) masterGain.gain.value = vol;
  }

  return {
    init: init,
    setVolume: setVolume,
    playGunshot: playGunshot,
    playReload: playReload,
    playHit: playHit,
    playHeadshot: playHeadshot,
    playKill: playKill,
    playDamage: playDamage,
    playFootstep: playFootstep,
    playExplosion: playExplosion,
    playKnifeSwing: playKnifeSwing,
    playZombieGroan: playZombieGroan,
    playZombieDeath: playZombieDeath,
    playZombieAttack: playZombieAttack,
    playRoundStart: playRoundStart,
    playRoundEnd: playRoundEnd
  };
})();
