// Text-to-Speech module for ServiceNow Module Guides
// Uses the Web Speech API (speechSynthesis) — free, no external service required.
// Features: play/pause/stop, voice selection, speed control, click-to-jump, abort.

(function () {
  'use strict';

  var CONTENT_SELECTOR = '#content';
  var TTS_PANEL_ID = 'tts-panel';
  var TTS_TOGGLE_ID = 'tts-toggle';
  var STORAGE_PREFIX = 'sg-tts-';

  // Defaults
  var DEFAULTS = {
    enabled: false,
    rate: 1.0,
    voiceIndex: 0,
    volume: 1.0
  };

  // State
  var state = {
    enabled: false,
    rate: DEFAULTS.rate,
    voiceIndex: DEFAULTS.voiceIndex,
    volume: DEFAULTS.volume,
    utterances: [],
    currentIndex: -1,
    isPlaying: false,
    isPaused: false,
    synth: null,
    activeUtterance: null,
    blocks: [],        // DOM elements that are speakable
    blockTexts: [],    // extracted text per block
    sections: [],      // {blockIndex, text, level} for page headings
  };

  // DOM refs
  var panel, toggleBtn, playBtn, stopBtn, voiceSelect, rateSlider, rateVal, volumeSlider, volumeVal, sectionSelect;

  // ------------------------------------------------------------------
  // Initialization
  // ------------------------------------------------------------------
  function init() {
    loadState();
    var synth = window.speechSynthesis;
    if (!synth) {
      // Browser doesn't support TTS — silently skip.
      return;
    }
    state.synth = synth;

    buildToggleButton();
    buildPanel();
    renderControls();

    // Rebuild voices when they load (async in some browsers)
    synth.onvoiceschanged = function () {
      populateVoices();
      renderControls();
    };
    populateVoices();

    // Fallback: retry voice loading (Chrome loads voices async)
    var voiceRetry = 0;
    function retryVoices() {
        var voices = synth.getVoices ? synth.getVoices() : [];
        if (voices.length === 0 && voiceRetry < 10) {
            voiceRetry += 1;
            setTimeout(retryVoices, 500);
        } else if (voices.length > 0) {
            populateVoices();
            renderControls();
        }
    }
    setTimeout(retryVoices, 500);

    // Make content text clickable for jump-to
    makeContentClickable();
    // Build section list (headings) for quick nav
    buildSections();

    // Highlight sync
  }

  function loadState() {
    try {
      // TTS always starts OFF — user must explicitly turn it on.
      // Do not persist the enabled state across visits.
      var rate = localStorage.getItem(STORAGE_PREFIX + 'rate');
      var voiceIndex = localStorage.getItem(STORAGE_PREFIX + 'voiceIndex');
      var volume = localStorage.getItem(STORAGE_PREFIX + 'volume');

      state.enabled = DEFAULTS.enabled;
      state.rate = rate !== null ? parseFloat(rate) : DEFAULTS.rate;
      state.voiceIndex = voiceIndex !== null ? parseInt(voiceIndex, 10) : DEFAULTS.voiceIndex;
      state.volume = volume !== null ? parseFloat(volume) : DEFAULTS.volume;
    } catch (e) {
      // ignore storage errors
    }
  }

  function saveState() {
    try {
      // Do not persist 'enabled' — TTS always starts OFF per visit.
      localStorage.setItem(STORAGE_PREFIX + 'rate', String(state.rate));
      localStorage.setItem(STORAGE_PREFIX + 'voiceIndex', String(state.voiceIndex));
      localStorage.setItem(STORAGE_PREFIX + 'volume', String(state.volume));
    } catch (e) {
      // ignore
    }
  }

  // ------------------------------------------------------------------
  // UI: toggle button + panel
  // ------------------------------------------------------------------
  function buildToggleButton() {
    var btn = document.createElement('button');
    btn.id = TTS_TOGGLE_ID;
    btn.type = 'button';
    btn.className = 'icon-btn tts-toggle';
    btn.setAttribute('aria-label', state.enabled ? 'Turn off read-aloud' : 'Turn on read-aloud');
    btn.setAttribute('aria-pressed', String(state.enabled));
    btn.title = state.enabled ? 'Read-aloud: ON' : 'Read-aloud: OFF';
    btn.textContent = state.enabled ? '🔊 Off' : '🔊 Read';

    // Insert into topbar controls
    var topbar = document.querySelector('.topbar-controls');
    if (topbar) {
      topbar.appendChild(btn);
    }
    toggleBtn = btn;

    btn.addEventListener('click', function (e) {
      e.preventDefault();
      toggleEnabled();
    });
  }

  function toggleEnabled() {
    state.enabled = !state.enabled;
    saveState();
    renderToggle();
    if (state.enabled) {
      panel.classList.remove('hidden');
      stop();
    } else {
      panel.classList.add('hidden');
      stop();
    }
  }

  function renderToggle() {
    if (!toggleBtn) return;
    toggleBtn.setAttribute('aria-pressed', String(state.enabled));
    toggleBtn.setAttribute('title', state.enabled ? 'Read-aloud: ON' : 'Read-aloud: OFF');
    toggleBtn.textContent = state.enabled ? '🔊 Off' : '🔊 Read';
    toggleBtn.classList.toggle('tts-active', state.enabled);
  }

  function buildPanel() {
    var p = document.createElement('div');
    p.id = TTS_PANEL_ID;
    p.className = 'tts-panel ' + (state.enabled ? '' : 'hidden');
    p.innerHTML =
      '<div class="tts-panel-head">' +
      '<span class="tts-title">Read Aloud</span>' +
      '<button type="button" class="tts-close" id="tts-close" aria-label="Close read-aloud">✕</button>' +
      '</div>' +
      '<div class="tts-controls">' +
      '<div class="tts-control-row">' +
      '<button type="button" class="tts-btn tts-btn-play" id="tts-play" aria-label="Play / Pause">▶ Play</button>' +
      '<button type="button" class="tts-btn tts-btn-stop" id="tts-stop" aria-label="Stop">■ Stop</button>' +
      '</div>' +
      '<div class="tts-control-row">' +
      '<label for="tts-voice">Voice:</label>' +
      '<select id="tts-voice" class="tts-select"></select>' +
      '<button type="button" class="tts-btn tts-btn-small" id="tts-refresh-voices" aria-label="Refresh voices">↻</button>' +
      '</div>' +
      '<div class="tts-control-row">' +
      '<label for="tts-section">Section:</label>' +
      '<select id="tts-section" class="tts-select"></select>' +
      '</div>' +
      '<div class="tts-control-row">' +
      '<label for="tts-rate">Speed: <span id="tts-rate-val">1.0×</span></label>' +
      '<input type="range" id="tts-rate" min="0.5" max="2.0" step="0.1" value="1.0">' +
      '</div>' +
      '<div class="tts-control-row">' +
      '<label for="tts-volume">Volume: <span id="tts-volume-val">100%</span></label>' +
      '<input type="range" id="tts-volume" min="0" max="100" step="5" value="100">' +
      '</div>' +
      '<div class="tts-control-row tts-hint">' +
      '<span>💡 Click any paragraph to jump there. <button type="button" class="tts-btn tts-btn-small" id="tts-abort">Abort</button></span>' +
      '</div>' +
      '</div>' +
      '</div>';

    // Insert after header, before nav
    var header = document.querySelector('header');
    if (header) {
      header.insertAdjacentElement('afterend', p);
    }
    panel = p;

    // Wire controls
    document.getElementById('tts-close').addEventListener('click', function (e) {
      e.preventDefault();
      panel.classList.add('hidden');
      stop();
    });
    document.getElementById('tts-play').addEventListener('click', togglePlay);
    document.getElementById('tts-stop').addEventListener('click', stop);
    document.getElementById('tts-abort').addEventListener('click', function (e) {
      e.preventDefault();
      abort();
    });
    voiceSelect = document.getElementById('tts-voice');
    voiceSelect.addEventListener('change', function () {
      state.voiceIndex = voiceSelect.selectedIndex;
      saveState();
    });
    document.getElementById('tts-refresh-voices').addEventListener('click', function (e) {
      e.preventDefault();
      populateVoices();
      renderControls();
    });
    document.getElementById('tts-refresh-voices').addEventListener('click', function (e) {
      e.preventDefault();
      populateVoices();
      renderControls();
    });
    sectionSelect = document.getElementById('tts-section');
    sectionSelect.addEventListener('change', function () {
      var selIdx = sectionSelect.selectedIndex;
      if (selIdx > 0) {
        var sec = state.sections[selIdx - 1];
        if (sec) jumpToSection(sec.blockIndex);
        sectionSelect.selectedIndex = 0;
      }
    });
    rateSlider = document.getElementById('tts-rate');
    rateVal = document.getElementById('tts-rate-val');
    rateSlider.addEventListener('input', function () {
      state.rate = parseFloat(rateSlider.value);
      rateVal.textContent = state.rate.toFixed(1) + '×';
      saveState();
      if (state.activeUtterance) {
        state.activeUtterance.rate = state.rate;
      }
    });
    volumeSlider = document.getElementById('tts-volume');
    volumeVal = document.getElementById('tts-volume-val');
    volumeSlider.addEventListener('input', function () {
      state.volume = parseInt(volumeSlider.value, 10) / 100;
      volumeVal.textContent = volumeSlider.value + '%';
      saveState();
      if (state.activeUtterance) {
        state.activeUtterance.volume = state.volume;
      }
    });

    panel = p;
  }

  function renderControls() {
    if (!voiceSelect || !rateSlider || !rateVal || !volumeSlider || !volumeVal) return;

    var synth = state.synth;
    var voices = synth.getVoices ? synth.getVoices() : [];
    voiceSelect.innerHTML = '';
    voices.forEach(function (v, i) {
      var opt = document.createElement('option');
      opt.value = i;
      opt.textContent = v.name + (v.lang ? ' (' + v.lang + ')' : '');
      if (i === state.voiceIndex) opt.selected = true;
      voiceSelect.appendChild(opt);
    });

    rateSlider.value = state.rate;
    rateVal.textContent = state.rate.toFixed(1) + '×';
    volumeSlider.value = Math.round(state.volume * 100);
    volumeVal.textContent = Math.round(state.volume * 100) + '%';
  }

  function populateVoices() {
    renderControls();
  }

  // ------------------------------------------------------------------
  // Section extraction (headings) for quick nav
  // ------------------------------------------------------------------
  function buildSections() {
    var content = document.querySelector(CONTENT_SELECTOR);
    if (!content) return;
    var headings = content.querySelectorAll('h1, h2, h3, h4, h5, h6');
    state.sections = [];
    Array.prototype.forEach.call(headings, function (h) {
      var text = h.textContent.trim();
      if (!text) return;
      // Find which speakable block index this heading corresponds to
      var blockIndex = -1;
      state.blocks.forEach(function (b, i) {
        if (b === h || h.contains(b) || b.contains(h)) blockIndex = i;
      });
      if (blockIndex < 0) {
        // Try nearest block by position
        var rect = h.getBoundingClientRect();
        var minDist = Infinity;
        state.blocks.forEach(function (b, i) {
          var br = b.getBoundingClientRect();
          var d = Math.abs(br.top - rect.top);
          if (d < minDist) { minDist = d; blockIndex = i; }
        });
      }
      state.sections.push({ blockIndex: blockIndex, text: text, level: parseInt(h.tagName.charAt(1), 10) || 2 });
    });
    renderSectionSelect();
  }

  function renderSectionSelect() {
    if (!sectionSelect) return;
    sectionSelect.innerHTML = '<option value="">Jump to section…</option>';
    state.sections.forEach(function (s, i) {
      var indent = '';
      for (var k = 2; k < (s.level || 2); k++) indent += '  ';
      var opt = document.createElement('option');
      opt.value = i + 1;
      opt.textContent = indent + s.text;
      sectionSelect.appendChild(opt);
    });
  }

  function jumpToSection(blockIndex) {
    jumpTo(blockIndex);
  }

  // ------------------------------------------------------------------
  // Content walking: extract speakable blocks + make clickable
  // ------------------------------------------------------------------
  function makeContentClickable() {
    var content = document.querySelector(CONTENT_SELECTOR);
    if (!content) return;

    // Find block-level elements that contain readable text
    var selectors = 'h1, h2, h3, h4, h5, h6, p, li, pre, blockquote, td, th';
    var blocks = content.querySelectorAll(selectors);
    state.blocks = Array.prototype.filter.call(blocks, function (el) {
      var text = el.textContent.trim();
      return text.length > 0;
    });

    state.blockTexts = state.blocks.map(function (el) {
      return el.textContent.trim();
    });

    // Add clickable attribute + cursor styling via data attribute
    state.blocks.forEach(function (el, i) {
      el.setAttribute('data-tts-index', i);
      el.setAttribute('data-tts-clickable', 'true');
      el.classList.add('tts-clickable');
      el.addEventListener('click', function (e) {
        // Only jump if not clicking a link/button inside
        if (e.target.closest('a, button, input, select, textarea')) return;
        e.preventDefault();
        jumpTo(i);
      });
    });
  }

  function jumpTo(index) {
    if (index < 0 || index >= state.blocks.length) return;
    state.currentIndex = index;
    // Stop any ongoing TTS so it doesn't scroll back to where it was speaking
    stop();
    // Clicking a paragraph only scrolls to that section.
    state.blocks[index].scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  // ------------------------------------------------------------------
  // Playback
  // ------------------------------------------------------------------
  function togglePlay() {
    if (state.synth.paused && state.utterances.length > 0 && state.currentIndex >= 0) {
      // Resume
      state.synth.resume();
      state.isPaused = false;
      state.isPlaying = true;
      updatePlayBtn();
      return;
    }
    if (state.isPlaying && !state.synth.paused) {
      // Pause
      state.synth.pause();
      state.isPaused = true;
      state.isPlaying = false;
      updatePlayBtn();
      return;
    }
    // Start fresh (or restart from current)
    if (state.currentIndex < 0) state.currentIndex = 0;
    speakFrom(state.currentIndex);
  }

  function speakFrom(startIndex) {
    stop(); // clear any existing

    var synth = state.synth;
    var voices = synth.getVoices ? synth.getVoices() : [];
    var voice = voices[state.voiceIndex] || null;

    state.utterances = [];
    state.isPlaying = true;
    state.isPaused = false;
    updatePlayBtn();

    for (var i = startIndex; i < state.blocks.length; i++) {
      (function (idx) {
        var u = new SpeechSynthesisUtterance(state.blockTexts[idx]);
        u.voice = voice;
        u.rate = state.rate;
        u.volume = state.volume;
        u.lang = voice ? voice.lang : 'en-US';

        u.onstart = function () {
          state.currentIndex = idx;
          state.activeUtterance = u;
          highlight(idx);
          scrollTo(idx);
        };

        u.onend = function () {
          if (state.activeUtterance === u) {
            state.activeUtterance = null;
            unhighlight(idx);
          }
          // Auto-advance: if not paused/stopped, next utterance starts automatically
          // (speechSynthesis queues them, but we want per-block control)
          if (state.isPlaying && !state.synth.paused && !state.isPaused) {
            var next = state.utterances.indexOf(u) + 1;
            if (next < state.utterances.length) {
              // The browser will play the next queued utterance; we just track index
              state.currentIndex = next;
              highlight(next);
              scrollTo(next);
            } else {
              // Finished all
              state.isPlaying = false;
              state.isPaused = false;
              updatePlayBtn();
              unhighlight(idx);
            }
          }
        };

        u.onerror = function (e) {
          console.warn('TTS error on block ' + idx, e);
          if (state.activeUtterance === u) state.activeUtterance = null;
          unhighlight(idx);
        };

        state.utterances.push(u);
        synth.speak(u);
      })(i);
    }
  }

  function stop() {
    if (!state.synth) return;
    state.synth.cancel();
    state.isPlaying = false;
    state.isPaused = false;
    state.activeUtterance = null;
    state.utterances = [];
    updatePlayBtn();
    unhighlightAll();
  }

  function abort() {
    stop();
    // Also hide panel
    if (panel) panel.classList.add('hidden');
  }

  function updatePlayBtn() {
    var btn = document.getElementById('tts-play');
    if (!btn) return;
    if (state.isPlaying && !state.isPaused) {
      btn.textContent = '⏸ Pause';
      btn.setAttribute('aria-label', 'Pause read-aloud');
    } else {
      btn.textContent = '▶ Play';
      btn.setAttribute('aria-label', 'Play / Resume read-aloud');
    }
  }

  // ------------------------------------------------------------------
  // Highlighting
  // ------------------------------------------------------------------
  function highlight(index) {
    unhighlightAll();
    var el = state.blocks[index];
    if (el) {
      el.classList.add('tts-speaking');
      el.setAttribute('aria-live', 'polite');
    }
  }

  function unhighlight(index) {
    var el = state.blocks[index];
    if (el) el.classList.remove('tts-speaking');
  }

  function unhighlightAll() {
    state.blocks.forEach(function (el) {
      el.classList.remove('tts-speaking');
    });
  }

  function scrollTo(index) {
    var el = state.blocks[index];
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }

  // ------------------------------------------------------------------
  // Auto-init when DOM ready
  // ------------------------------------------------------------------
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
