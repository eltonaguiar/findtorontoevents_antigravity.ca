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
//   ANNOUNCER STINGER SFX
//   Dramatic impact effects that play alongside voice
// ═══════════════════════════════════════════════════════════

SFX.announcerName = function() {
    // Dramatic impact + arena reverb for character name call-outs
    tone(70, 'sine', 0.45, 0.22, 0.005, 0.45);          // low boom
    noiseBurst(0.1, 0.28, 1400, 2);                       // impact crack
    tone(350, 'square', 0.06, 0.08, 0.002, 0.06);         // bright accent
    setTimeout(function() {
        noiseBurst(0.4, 0.06, 600, 0.5);                  // crowd-like tail
    }, 60);
};

SFX.announcerFight = function() {
    // Huge impact for FIGHT!
    tone(55, 'sine', 0.6, 0.3, 0.005, 0.6);              // sub boom
    noiseBurst(0.18, 0.4, 900, 1.5);                      // heavy crack
    sweep(180, 700, 0.35, 'sawtooth', 0.1);               // rising energy
    tone(440, 'square', 0.1, 0.12, 0.002, 0.1);           // sharp accent
    setTimeout(function() {
        noiseBurst(0.5, 0.08, 500, 0.4);                  // arena reverb tail
    }, 100);
};

SFX.announcerKO = function() {
    // Devastating impact for K.O.
    tone(40, 'sine', 0.9, 0.35, 0.01, 0.9);              // deep sub
    noiseBurst(0.25, 0.45, 500, 1);                        // massive crack
    sweep(700, 80, 0.55, 'sawtooth', 0.12);               // descending weight
    setTimeout(function() {
        tone(60, 'sine', 0.5, 0.15, 0.01, 0.5);          // aftershock
    }, 250);
};

SFX.announcerWins = function() {
    // Triumphant chord
    tone(261, 'square', 0.35, 0.07, 0.005, 0.35);         // C4
    tone(329, 'square', 0.35, 0.07, 0.005, 0.35);         // E4
    tone(392, 'square', 0.35, 0.07, 0.005, 0.35);         // G4
    sweep(250, 1000, 0.45, 'sawtooth', 0.05);             // rising energy
    noiseBurst(0.12, 0.2, 1200, 2);                        // impact
};

SFX.announcerVersus = function() {
    // Tension-building whoosh
    sweep(100, 500, 0.3, 'sawtooth', 0.08);
    noiseBurst(0.15, 0.2, 800, 1);
    tone(100, 'sine', 0.3, 0.12, 0.005, 0.3);
};

SFX.announcerRound = function() {
    // Authoritative bell-like hit
    tone(300, 'sine', 0.25, 0.15, 0.002, 0.25);
    tone(600, 'sine', 0.2, 0.08, 0.002, 0.2);
    noiseBurst(0.08, 0.2, 2000, 3);
};


// ═══════════════════════════════════════════════════════════
//   VOCAL ANNOUNCER (Formant Synthesis)
//   Synthesized vocal "shout" layer for fighting game energy.
//   Plays as a stylized undertone alongside the speech voice.
// ═══════════════════════════════════════════════════════════

var VocalAnnouncer = (function() {

    // Formant frequencies: [F1, F2, F3]
    var VOWELS = {
        'ah': [800, 1200, 2500],   // /ɑ/ "father"
        'ee': [270, 2300, 3000],   // /i/ "see"
        'ih': [400, 2000, 2600],   // /ɪ/ "sit"
        'eh': [530, 1850, 2500],   // /ɛ/ "bed"
        'oo': [300, 870, 2250],    // /u/ "boot"
        'uh': [640, 1200, 2400],   // /ʌ/ "but"
        'oh': [500, 700, 2500],    // /ɔ/ "go"
        'ay': [500, 1800, 2600],   // /eɪ/ start
        'ow': [600, 900, 2500]     // /aʊ/ "now"
    };

    // Phoneme sequences for each character name & phrase
    // type: 'v' = vowel, 'd' = diphthong, 'p' = plosive, 'f' = fricative, 'r' = resonant
    var PHRASES = {
        'Kai': [
            { t: 'p', hz: 3000, dur: 0.04 },
            { t: 'd', from: 'ah', to: 'ee', dur: 0.38 }
        ],
        'Rook': [
            { t: 'r', hz: 200, dur: 0.06 },
            { t: 'v', s: 'oo', dur: 0.28 },
            { t: 'p', hz: 2500, dur: 0.04 }
        ],
        'Zara': [
            { t: 'f', hz: 6000, dur: 0.07 },
            { t: 'v', s: 'ah', dur: 0.2 },
            { t: 'r', hz: 200, dur: 0.04 },
            { t: 'v', s: 'ah', dur: 0.28 }
        ],
        'Vex': [
            { t: 'f', hz: 3500, dur: 0.06 },
            { t: 'v', s: 'eh', dur: 0.28 },
            { t: 'f', hz: 5000, dur: 0.1 }
        ],
        'Freya': [
            { t: 'f', hz: 5000, dur: 0.05 },
            { t: 'r', hz: 200, dur: 0.03 },
            { t: 'd', from: 'ay', to: 'ah', dur: 0.38 }
        ],
        'Drake': [
            { t: 'p', hz: 2000, dur: 0.04 },
            { t: 'r', hz: 200, dur: 0.04 },
            { t: 'd', from: 'ay', to: 'ee', dur: 0.32 },
            { t: 'p', hz: 3000, dur: 0.04 }
        ],
        'Fight': [
            { t: 'f', hz: 5000, dur: 0.06 },
            { t: 'd', from: 'ah', to: 'ee', dur: 0.38 },
            { t: 'p', hz: 4000, dur: 0.04 }
        ],
        'KO': [
            { t: 'p', hz: 3000, dur: 0.05 },
            { t: 'd', from: 'ay', to: 'oh', dur: 0.5 }
        ],
        'Wins': [
            { t: 'r', hz: 250, dur: 0.05 },
            { t: 'v', s: 'ih', dur: 0.22 },
            { t: 'r', hz: 300, dur: 0.06 },
            { t: 'f', hz: 6000, dur: 0.08 }
        ],
        'Versus': [
            { t: 'f', hz: 3500, dur: 0.05 },
            { t: 'v', s: 'uh', dur: 0.15 },
            { t: 'f', hz: 5000, dur: 0.06 },
            { t: 'v', s: 'uh', dur: 0.14 },
            { t: 'f', hz: 5000, dur: 0.06 }
        ],
        'Round': [
            { t: 'r', hz: 200, dur: 0.05 },
            { t: 'd', from: 'ow', to: 'oo', dur: 0.28 },
            { t: 'r', hz: 300, dur: 0.06 },
            { t: 'p', hz: 2000, dur: 0.03 }
        ]
    };

    var BASE_PITCH = 95;  // deep male fundamental Hz

    /**
     * Synthesize a formant-based vocal shout.
     * @param {string} phrase  Key in PHRASES (e.g. 'Kai', 'Fight')
     * @param {object} opts    { pitch, volume }
     */
    function shout(phrase, opts) {
        var c = ctx(); if (!c) return;
        var segs = PHRASES[phrase];
        if (!segs) return;
        opts = opts || {};
        var pitch  = opts.pitch  || BASE_PITCH;
        var vol    = opts.volume || 0.45;

        // Total duration
        var totalDur = 0;
        for (var i = 0; i < segs.length; i++) totalDur += segs[i].dur;

        var t = c.currentTime + 0.01;

        // ── Voiced excitation: two slightly-detuned sawtooths ──
        var osc1 = c.createOscillator();
        osc1.type = 'sawtooth';
        osc1.frequency.setValueAtTime(pitch, t);
        osc1.frequency.linearRampToValueAtTime(pitch * 1.18, t + totalDur * 0.65);
        osc1.frequency.linearRampToValueAtTime(pitch * 0.88, t + totalDur);

        var osc2 = c.createOscillator();
        osc2.type = 'sawtooth';
        osc2.frequency.setValueAtTime(pitch * 1.004, t);
        osc2.frequency.linearRampToValueAtTime(pitch * 1.18 * 1.004, t + totalDur * 0.65);
        osc2.frequency.linearRampToValueAtTime(pitch * 0.88 * 1.004, t + totalDur);

        // Sub oscillator for chest resonance
        var oscSub = c.createOscillator();
        oscSub.type = 'sine';
        oscSub.frequency.setValueAtTime(pitch * 0.5, t);
        oscSub.frequency.linearRampToValueAtTime(pitch * 0.5 * 1.1, t + totalDur * 0.6);
        oscSub.frequency.linearRampToValueAtTime(pitch * 0.5 * 0.9, t + totalDur);

        var voiceMix = c.createGain();
        voiceMix.gain.value = 0.45;
        osc1.connect(voiceMix);
        osc2.connect(voiceMix);
        var subGain = c.createGain();
        subGain.gain.value = 0.2;
        oscSub.connect(subGain);
        subGain.connect(voiceMix);

        // ── Formant filter bank (3 parallel bandpass) ──
        var fmts = [];
        var fGains = [];
        var qVals = [5, 8, 10];
        var ampVals = [1.0, 0.65, 0.25];
        for (var fi = 0; fi < 3; fi++) {
            var bp = c.createBiquadFilter();
            bp.type = 'bandpass';
            bp.Q.value = qVals[fi];
            fmts.push(bp);
            var fg = c.createGain();
            fg.gain.value = ampVals[fi];
            fGains.push(fg);
            voiceMix.connect(bp);
            bp.connect(fg);
        }

        // ── Master vocal envelope ──
        var masterEnv = c.createGain();
        masterEnv.gain.setValueAtTime(0.001, t);
        masterEnv.gain.linearRampToValueAtTime(vol, t + 0.025);
        // Sustain at peak then decay
        masterEnv.gain.setValueAtTime(vol, t + totalDur * 0.8);
        masterEnv.gain.exponentialRampToValueAtTime(0.001, t + totalDur + 0.12);

        for (var gi = 0; gi < fGains.length; gi++) {
            fGains[gi].connect(masterEnv);
        }

        // ── Soft-clip distortion for vocal grit ──
        var shaper = c.createWaveShaper();
        var curve = new Float32Array(256);
        for (var ci = 0; ci < 256; ci++) {
            var x = (ci / 128) - 1;
            curve[ci] = (Math.PI + 2.5) * x / (Math.PI + 2.5 * Math.abs(x));
        }
        shaper.curve = curve;
        shaper.oversample = '2x';
        masterEnv.connect(shaper);

        // ── Arena echo (two taps) ──
        var d1 = c.createDelay(0.5);
        d1.delayTime.value = 0.09;
        var d1g = c.createGain();
        d1g.gain.value = 0.25;
        var d2 = c.createDelay(0.5);
        d2.delayTime.value = 0.18;
        var d2g = c.createGain();
        d2g.gain.value = 0.12;

        shaper.connect(_sfxGain);
        shaper.connect(d1);  d1.connect(d1g);  d1g.connect(_sfxGain);
        shaper.connect(d2);  d2.connect(d2g);  d2g.connect(_sfxGain);

        // ── Animate formants through phoneme sequence ──
        var segT = t;
        for (var si = 0; si < segs.length; si++) {
            var seg = segs[si];
            if (seg.t === 'v') {
                // Vowel — snap formants to target
                var vf = VOWELS[seg.s];
                for (var vk = 0; vk < 3; vk++) {
                    fmts[vk].frequency.linearRampToValueAtTime(vf[vk], segT + 0.012);
                }
            } else if (seg.t === 'd') {
                // Diphthong — glide between two vowels
                var vFrom = VOWELS[seg.from];
                var vTo   = VOWELS[seg.to];
                for (var dk = 0; dk < 3; dk++) {
                    fmts[dk].frequency.setValueAtTime(vFrom[dk], segT);
                    fmts[dk].frequency.linearRampToValueAtTime(vTo[dk], segT + seg.dur);
                }
            } else if (seg.t === 'p') {
                noiseBurst(seg.dur, vol * 0.45, seg.hz, 3);
            } else if (seg.t === 'f') {
                noiseBurst(seg.dur * 1.4, vol * 0.3, seg.hz, 5);
            } else if (seg.t === 'r') {
                tone(seg.hz, 'sine', seg.dur, vol * 0.28, 0.005, seg.dur);
            }
            segT += seg.dur;
        }

        // Start & stop oscillators
        osc1.start(t);  osc1.stop(t + totalDur + 0.2);
        osc2.start(t);  osc2.stop(t + totalDur + 0.2);
        oscSub.start(t); oscSub.stop(t + totalDur + 0.2);
    }

    return { shout: shout };
})();


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
    announcer: VocalAnnouncer,
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
