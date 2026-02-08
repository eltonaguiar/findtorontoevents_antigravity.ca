/* ============================================================
   SHADOW ARENA — Audio Engine
   Procedural sound effects using Web Audio API.
   No external audio files required — all sounds are synthesized.
   ============================================================ */
(function() {
'use strict';

var _ctx = null;         // AudioContext (lazy-init on first user gesture)
var _master = null;      // master gain
var _musicGain = null;   // music sub-bus
var _sfxGain = null;     // sfx sub-bus
var _musicOscs = [];     // current music oscillators
var _musicPlaying = false;
var _muted = false;
var _sfxVolume = 0.45;
var _musicVolume = 0.18;

// ── Lazy-init AudioContext (requires user gesture on many browsers) ──
function ctx() {
    if (_ctx) return _ctx;
    try {
        _ctx = new (window.AudioContext || window.webkitAudioContext)();
        _master = _ctx.createGain();
        _master.gain.value = 1;
        _master.connect(_ctx.destination);

        _sfxGain = _ctx.createGain();
        _sfxGain.gain.value = _sfxVolume;
        _sfxGain.connect(_master);

        _musicGain = _ctx.createGain();
        _musicGain.gain.value = _musicVolume;
        _musicGain.connect(_master);
    } catch (e) {
        _ctx = null;
    }
    return _ctx;
}

// Ensure context is resumed (call on first click/key)
function ensureResumed() {
    if (_ctx && _ctx.state === 'suspended') {
        _ctx.resume();
    }
}

// ── Utility: play a noise burst (used for impacts) ──
function noiseBurst(duration, volume, filterFreq, filterQ) {
    var c = ctx(); if (!c) return;
    var len = c.sampleRate * duration;
    var buf = c.createBuffer(1, len, c.sampleRate);
    var data = buf.getChannelData(0);
    for (var i = 0; i < len; i++) data[i] = (Math.random() * 2 - 1);

    var src = c.createBufferSource();
    src.buffer = buf;

    var filt = c.createBiquadFilter();
    filt.type = 'bandpass';
    filt.frequency.value = filterFreq || 800;
    filt.Q.value = filterQ || 1.5;

    var gain = c.createGain();
    gain.gain.setValueAtTime(volume || 0.3, c.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, c.currentTime + duration);

    src.connect(filt);
    filt.connect(gain);
    gain.connect(_sfxGain);
    src.start();
}

// ── Utility: play a tone ──
function tone(freq, type, duration, volume, attack, decay) {
    var c = ctx(); if (!c);
    if (!c) return;
    var osc = c.createOscillator();
    osc.type = type || 'sine';
    osc.frequency.value = freq;

    var gain = c.createGain();
    var t = c.currentTime;
    var atk = attack || 0.005;
    var dec = decay || duration;
    gain.gain.setValueAtTime(0.001, t);
    gain.gain.linearRampToValueAtTime(volume || 0.2, t + atk);
    gain.gain.exponentialRampToValueAtTime(0.001, t + dec);

    osc.connect(gain);
    gain.connect(_sfxGain);
    osc.start(t);
    osc.stop(t + dec + 0.05);
}

// ── Utility: pitch sweep ──
function sweep(startFreq, endFreq, duration, type, volume) {
    var c = ctx(); if (!c) return;
    var osc = c.createOscillator();
    osc.type = type || 'sawtooth';
    osc.frequency.setValueAtTime(startFreq, c.currentTime);
    osc.frequency.exponentialRampToValueAtTime(endFreq, c.currentTime + duration);

    var gain = c.createGain();
    gain.gain.setValueAtTime(volume || 0.15, c.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, c.currentTime + duration);

    osc.connect(gain);
    gain.connect(_sfxGain);
    osc.start();
    osc.stop(c.currentTime + duration + 0.02);
}


// ═══════════════════════════════════════════════════════════
//   SOUND EFFECTS
// ═══════════════════════════════════════════════════════════

var SFX = {};

// ── Hit / Impact sounds ──
SFX.lightHit = function() {
    noiseBurst(0.08, 0.35, 1200, 2);
    tone(300, 'sine', 0.06, 0.15, 0.002, 0.06);
};

SFX.heavyHit = function() {
    noiseBurst(0.15, 0.5, 600, 1.5);
    noiseBurst(0.08, 0.3, 2000, 2);
    tone(150, 'sine', 0.12, 0.2, 0.002, 0.12);
    tone(80, 'sine', 0.18, 0.15, 0.005, 0.18);
};

SFX.specialHit = function() {
    noiseBurst(0.2, 0.55, 500, 1.2);
    noiseBurst(0.12, 0.35, 2500, 3);
    sweep(800, 200, 0.25, 'sawtooth', 0.12);
    tone(120, 'sine', 0.2, 0.2, 0.005, 0.2);
};

SFX.grabHit = function() {
    noiseBurst(0.12, 0.4, 400, 1);
    tone(200, 'triangle', 0.1, 0.2, 0.002, 0.1);
    tone(100, 'sine', 0.15, 0.15, 0.01, 0.15);
};

// ── Attack whoosh (pre-hit) ──
SFX.lightAttack = function() {
    sweep(800, 2000, 0.08, 'sawtooth', 0.08);
    noiseBurst(0.06, 0.12, 3000, 3);
};

SFX.heavyAttack = function() {
    sweep(400, 1200, 0.14, 'sawtooth', 0.1);
    noiseBurst(0.1, 0.15, 2000, 2);
};

SFX.specialAttack = function() {
    sweep(200, 1500, 0.2, 'square', 0.08);
    tone(600, 'sine', 0.3, 0.08, 0.01, 0.3);
    tone(800, 'sine', 0.25, 0.06, 0.05, 0.25);
};

// ── Block ──
SFX.block = function() {
    noiseBurst(0.06, 0.3, 2500, 4);
    tone(500, 'square', 0.04, 0.1, 0.001, 0.04);
};

// ── Dash ──
SFX.dash = function() {
    sweep(1500, 400, 0.12, 'sawtooth', 0.06);
    noiseBurst(0.08, 0.1, 4000, 5);
};

// ── Jump ──
SFX.jump = function() {
    sweep(300, 800, 0.1, 'sine', 0.08);
};

// ── Land ──
SFX.land = function() {
    noiseBurst(0.05, 0.2, 300, 1);
};

// ── KO ──
SFX.ko = function() {
    noiseBurst(0.3, 0.6, 300, 0.8);
    tone(150, 'sawtooth', 0.4, 0.15, 0.005, 0.4);
    sweep(500, 80, 0.5, 'sawtooth', 0.1);
    // Dramatic low boom
    tone(50, 'sine', 0.6, 0.25, 0.01, 0.6);
};

// ── Round announcements ──
SFX.countdown = function(num) {
    // Higher pitch for FIGHT!
    var freq = num === 0 ? 800 : 400 + num * 80;
    tone(freq, 'square', 0.15, 0.12, 0.002, 0.15);
    tone(freq * 1.5, 'sine', 0.1, 0.06, 0.01, 0.1);
};

SFX.roundStart = function() {
    tone(600, 'square', 0.1, 0.1, 0.002, 0.1);
    tone(800, 'square', 0.1, 0.12, 0.002, 0.1);
    setTimeout(function() {
        tone(1000, 'square', 0.2, 0.15, 0.002, 0.2);
    }, 120);
};

SFX.roundEnd = function() {
    tone(800, 'sine', 0.2, 0.1, 0.01, 0.2);
    setTimeout(function() { tone(600, 'sine', 0.3, 0.12, 0.01, 0.3); }, 200);
    setTimeout(function() { tone(400, 'sine', 0.4, 0.1, 0.01, 0.4); }, 400);
};

SFX.matchEnd = function() {
    // Victory fanfare
    var notes = [523, 659, 784, 1047]; // C5 E5 G5 C6
    for (var i = 0; i < notes.length; i++) {
        (function(n, delay) {
            setTimeout(function() {
                tone(n, 'square', 0.25, 0.1, 0.005, 0.25);
                tone(n * 0.5, 'sine', 0.3, 0.08, 0.01, 0.3);
            }, delay);
        })(notes[i], i * 180);
    }
};

// ── Taunt ──
SFX.taunt = function() {
    sweep(300, 600, 0.15, 'triangle', 0.06);
    setTimeout(function() { sweep(600, 300, 0.15, 'triangle', 0.06); }, 160);
};

// ── Special meter full ──
SFX.meterFull = function() {
    tone(880, 'sine', 0.1, 0.08, 0.002, 0.1);
    setTimeout(function() { tone(1100, 'sine', 0.15, 0.1, 0.005, 0.15); }, 100);
};

// ── UI sounds ──
SFX.uiClick = function() {
    tone(800, 'sine', 0.04, 0.08, 0.001, 0.04);
};

SFX.uiConfirm = function() {
    tone(600, 'sine', 0.06, 0.1, 0.002, 0.06);
    setTimeout(function() { tone(900, 'sine', 0.08, 0.1, 0.002, 0.08); }, 70);
};

SFX.uiBack = function() {
    tone(500, 'sine', 0.05, 0.08, 0.002, 0.05);
    setTimeout(function() { tone(350, 'sine', 0.06, 0.08, 0.002, 0.06); }, 60);
};

SFX.uiSelect = function() {
    tone(700, 'sine', 0.03, 0.06, 0.001, 0.03);
};


// ═══════════════════════════════════════════════════════════
//   BACKGROUND MUSIC (simple procedural loop)
// ═══════════════════════════════════════════════════════════

var _loopTimer = null;

function startMusic(style) {
    var c = ctx(); if (!c) return;
    stopMusic();
    _musicPlaying = true;

    // Bass line pattern (note frequencies)
    var patterns = {
        menu: { notes: [110, 110, 130.81, 130.81, 146.83, 146.83, 130.81, 130.81], bpm: 110, vibe: 'dark' },
        fight: { notes: [82.41, 98, 110, 130.81, 110, 98, 82.41, 73.42], bpm: 140, vibe: 'intense' },
        victory: { notes: [130.81, 164.81, 196, 261.63, 196, 164.81, 130.81, 130.81], bpm: 120, vibe: 'bright' }
    };
    var pat = patterns[style] || patterns.fight;
    var beatMs = 60000 / pat.bpm;
    var step = 0;

    function playBeat() {
        if (!_musicPlaying) return;
        var c2 = ctx(); if (!c2) return;

        var note = pat.notes[step % pat.notes.length];
        var t = c2.currentTime;
        var dur = beatMs / 1000 * 0.85;

        // Bass
        var osc = c2.createOscillator();
        osc.type = 'sawtooth';
        osc.frequency.value = note;
        var g = c2.createGain();
        g.gain.setValueAtTime(0.15, t);
        g.gain.exponentialRampToValueAtTime(0.001, t + dur);
        var filt = c2.createBiquadFilter();
        filt.type = 'lowpass';
        filt.frequency.value = 250;
        osc.connect(filt);
        filt.connect(g);
        g.connect(_musicGain);
        osc.start(t);
        osc.stop(t + dur + 0.05);

        // Kick on beats 0, 2, 4, 6
        if (step % 2 === 0) {
            var kick = c2.createOscillator();
            kick.type = 'sine';
            kick.frequency.setValueAtTime(150, t);
            kick.frequency.exponentialRampToValueAtTime(40, t + 0.12);
            var kg = c2.createGain();
            kg.gain.setValueAtTime(0.3, t);
            kg.gain.exponentialRampToValueAtTime(0.001, t + 0.15);
            kick.connect(kg);
            kg.connect(_musicGain);
            kick.start(t);
            kick.stop(t + 0.2);
        }

        // Hi-hat on offbeats
        if (step % 2 === 1) {
            var hatLen = c2.sampleRate * 0.04;
            var hatBuf = c2.createBuffer(1, hatLen, c2.sampleRate);
            var hatData = hatBuf.getChannelData(0);
            for (var i = 0; i < hatLen; i++) hatData[i] = (Math.random() * 2 - 1);
            var hatSrc = c2.createBufferSource();
            hatSrc.buffer = hatBuf;
            var hatFilt = c2.createBiquadFilter();
            hatFilt.type = 'highpass';
            hatFilt.frequency.value = 8000;
            var hatG = c2.createGain();
            hatG.gain.setValueAtTime(0.08, t);
            hatG.gain.exponentialRampToValueAtTime(0.001, t + 0.04);
            hatSrc.connect(hatFilt);
            hatFilt.connect(hatG);
            hatG.connect(_musicGain);
            hatSrc.start(t);
        }

        // Snare on beat 4
        if (step % 8 === 4) {
            var snLen = c2.sampleRate * 0.1;
            var snBuf = c2.createBuffer(1, snLen, c2.sampleRate);
            var snData = snBuf.getChannelData(0);
            for (var j = 0; j < snLen; j++) snData[j] = (Math.random() * 2 - 1);
            var snSrc = c2.createBufferSource();
            snSrc.buffer = snBuf;
            var snFilt = c2.createBiquadFilter();
            snFilt.type = 'bandpass';
            snFilt.frequency.value = 1500;
            snFilt.Q.value = 1;
            var snG = c2.createGain();
            snG.gain.setValueAtTime(0.15, t);
            snG.gain.exponentialRampToValueAtTime(0.001, t + 0.1);
            snSrc.connect(snFilt);
            snFilt.connect(snG);
            snG.connect(_musicGain);
            snSrc.start(t);
        }

        step++;
        _loopTimer = setTimeout(playBeat, beatMs);
    }

    playBeat();
}

function stopMusic() {
    _musicPlaying = false;
    if (_loopTimer) { clearTimeout(_loopTimer); _loopTimer = null; }
}


// ═══════════════════════════════════════════════════════════
//   PUBLIC API
// ═══════════════════════════════════════════════════════════

window.GameAudio = {
    init: function() { ctx(); },
    ensureResumed: ensureResumed,
    sfx: SFX,
    startMusic: startMusic,
    stopMusic: stopMusic,
    mute: function() {
        _muted = true;
        if (_master) _master.gain.value = 0;
    },
    unmute: function() {
        _muted = false;
        if (_master) _master.gain.value = 1;
    },
    toggleMute: function() {
        if (_muted) this.unmute(); else this.mute();
        return _muted;
    },
    isMuted: function() { return _muted; },
    setSfxVolume: function(v) {
        _sfxVolume = v;
        if (_sfxGain) _sfxGain.gain.value = v;
    },
    setMusicVolume: function(v) {
        _musicVolume = v;
        if (_musicGain) _musicGain.gain.value = v;
    }
};

})();
