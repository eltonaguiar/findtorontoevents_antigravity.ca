/**
 * VR Area Guide System
 *
 * Provides contextual information about each VR zone via text overlay and
 * text-to-speech narration. Each zone registers its guide content, which
 * can include dynamic data (e.g., who is live, event counts).
 *
 * Integrated into the nav menu via a "Guide" button. Also provides the
 * Events Audio Announcements feature with today/tomorrow event reading.
 */
(function () {
  'use strict';

  /* ═══════════════════════════════════════════════
     ZONE GUIDE DEFINITIONS
     ═══════════════════════════════════════════════ */

  var ZONE_GUIDES = {
    hub: {
      title: 'Welcome to the VR Hub',
      intro: 'This is the central hub of the VR experience. From here you can visit 7 unique zones.',
      actions: [
        'Click any glowing portal to enter a zone',
        'Use WASD keys to walk around the hub',
        'Press M or Tab to open the navigation menu',
        'Look at the data badges below portals for live stats'
      ],
      dynamic: null
    },
    events: {
      title: 'Events Explorer',
      intro: 'Browse hundreds of Toronto events in immersive 3D. Filter by category, search by keyword, and preview event details.',
      actions: [
        'Click event cards to see full details',
        'Use the category pills at the top to filter',
        'Press / or F to search events by name',
        'Arrow keys navigate between pages',
        'Click "View Event" to open in your browser',
        'Click "Preview" to see the event page inline'
      ],
      dynamic: function () {
        if (typeof window.filteredEvents !== 'undefined') {
          var count = window.filteredEvents.length || 0;
          var todayCount = 0;
          var now = new Date();
          var todayStr = now.toISOString().split('T')[0];
          (window.filteredEvents || []).forEach(function (ev) {
            if (ev.date && ev.date.indexOf(todayStr) === 0) todayCount++;
          });
          return count + ' events loaded. ' + (todayCount > 0 ? todayCount + ' happening today.' : 'Check the filters for today\'s events.');
        }
        return 'Events are loading...';
      }
    },
    movies: {
      title: 'Movie Theater',
      intro: 'Welcome to the VR Movie Theater. Browse movie trailers, watch them on the big screen, and discover what\'s playing in Toronto.',
      actions: [
        'Click movie posters to see details and trailers',
        'Use arrow keys to browse the collection',
        'Press Enter or click Play to watch a trailer',
        'Use the category bar to filter by genre',
        'Press Escape to close the video player'
      ],
      dynamic: null
    },
    creators: {
      title: 'FavCreators Live Lounge',
      intro: 'See your favorite content creators\' live status. Watch streams, browse recent videos, and discover who\'s online.',
      actions: [
        'Login to see your personal creator list',
        'Click creator cards for details and stream links',
        'Use the Live Now menu at the top for quick access',
        'Press R to refresh live status',
        'Keys 1-5 filter by platform (All/TikTok/Twitch/Kick/YouTube)'
      ],
      dynamic: function () {
        if (typeof window.allCreators !== 'undefined') {
          var creators = window.allCreators || [];
          var liveCount = creators.filter(function (c) { return c._vrIsLive; }).length;
          var total = creators.length;
          var liveNames = creators.filter(function (c) { return c._vrIsLive; })
            .map(function (c) { return c.name; }).slice(0, 5);
          var msg = total + ' creators loaded. ';
          if (liveCount > 0) {
            msg += liveCount + ' live right now: ' + liveNames.join(', ');
            if (liveCount > 5) msg += ' and ' + (liveCount - 5) + ' more';
            msg += '.';
          } else {
            msg += 'No one is live right now. Auto-refreshes every 60 seconds.';
          }
          return msg;
        }
        return 'Loading creators...';
      }
    },
    stocks: {
      title: 'Stock Trading Floor',
      intro: 'Welcome to the Trading Floor. View real-time stock simulations, track gainers and losers, and monitor market trends.',
      actions: [
        'Press R to refresh stock data',
        'Arrow Up/Down cycles through tickers',
        'Watch the scrolling news ticker for market updates',
        'Gainer panel is on the left, loser panel on the right'
      ],
      dynamic: null
    },
    wellness: {
      title: 'Wellness Garden',
      intro: 'A peaceful retreat for relaxation. Practice breathing exercises, check in with yourself, and find moments of calm.',
      actions: [
        'Click the breathing sphere to start a guided exercise',
        'Visit the accountability zone for daily check-ins',
        'Motivational quotes rotate around the garden',
        'Press C for a quick check-in, Space to start breathing'
      ],
      dynamic: null
    },
    weather: {
      title: 'Weather Observatory',
      intro: 'Experience Toronto\'s weather in immersive VR. See real-time conditions with dynamic particle effects.',
      actions: [
        'Press 1-4 to switch weather modes (Clear/Rain/Snow/Thunder)',
        'Press P for passthrough AR mode (Quest 3)',
        'Press R to refresh weather data',
        'The 7-day forecast updates automatically'
      ],
      dynamic: function () {
        var tempEl = document.querySelector('[id*="temp"], .weather-temp, #current-temp');
        if (tempEl) return 'Current conditions: ' + tempEl.textContent;
        return 'Weather data loading...';
      }
    },
    tutorial: {
      title: 'VR Tutorial',
      intro: 'Learn the basics of navigating in VR. This guided walkthrough covers looking, clicking, walking, and menu usage.',
      actions: [
        'Press S to skip the current step',
        'Press B to go back one step',
        'Press R to restart the tutorial',
        'Follow the on-screen instructions for each step'
      ],
      dynamic: null
    }
  };

  /* ═══════════════════════════════════════════════
     TEXT-TO-SPEECH ENGINE
     ═══════════════════════════════════════════════ */

  var ttsSupported = 'speechSynthesis' in window;
  var ttsUtterance = null;
  var ttsPaused = false;
  var ttsSpeaking = false;

  function speak(text, onEnd) {
    if (!ttsSupported) { if (onEnd) onEnd(); return; }
    stopSpeaking();
    ttsUtterance = new SpeechSynthesisUtterance(text);
    ttsUtterance.rate = 0.95;
    ttsUtterance.pitch = 1.0;
    ttsUtterance.volume = 0.9;
    var voices = speechSynthesis.getVoices();
    var preferred = voices.find(function (v) {
      return v.lang.indexOf('en') === 0 && (v.name.indexOf('Google') !== -1 || v.name.indexOf('Natural') !== -1 || v.name.indexOf('Samantha') !== -1);
    }) || voices.find(function (v) { return v.lang.indexOf('en') === 0; });
    if (preferred) ttsUtterance.voice = preferred;

    ttsUtterance.onend = function () {
      ttsSpeaking = false;
      ttsPaused = false;
      updateTTSControls();
      if (onEnd) onEnd();
    };
    ttsSpeaking = true;
    ttsPaused = false;
    speechSynthesis.speak(ttsUtterance);
    updateTTSControls();
  }

  function pauseSpeaking() {
    if (ttsSupported && ttsSpeaking) {
      speechSynthesis.pause();
      ttsPaused = true;
      updateTTSControls();
    }
  }

  function resumeSpeaking() {
    if (ttsSupported && ttsPaused) {
      speechSynthesis.resume();
      ttsPaused = false;
      updateTTSControls();
    }
  }

  function stopSpeaking() {
    if (ttsSupported) {
      speechSynthesis.cancel();
      ttsSpeaking = false;
      ttsPaused = false;
      updateTTSControls();
    }
  }

  function updateTTSControls() {
    var statusEl = document.getElementById('vr-guide-tts-status');
    var pauseBtn = document.getElementById('vr-guide-tts-pause');
    if (!statusEl) return;

    if (ttsSpeaking && !ttsPaused) {
      statusEl.textContent = 'Speaking...';
      statusEl.style.color = '#22c55e';
      if (pauseBtn) pauseBtn.textContent = 'Pause';
    } else if (ttsPaused) {
      statusEl.textContent = 'Paused';
      statusEl.style.color = '#f59e0b';
      if (pauseBtn) pauseBtn.textContent = 'Resume';
    } else {
      statusEl.textContent = '';
      statusEl.style.color = '#64748b';
    }
  }

  /* ═══════════════════════════════════════════════
     GUIDE OVERLAY UI
     ═══════════════════════════════════════════════ */

  var guideOpen = false;

  function getGuideCSS() {
    return '\
#vr-area-guide{position:fixed;inset:0;z-index:100005;display:none;align-items:center;justify-content:center;background:rgba(6,4,16,0.9);backdrop-filter:blur(12px);font-family:Inter,system-ui,sans-serif}\
#vr-area-guide.open{display:flex}\
.guide-card{width:min(94vw,560px);max-height:88vh;overflow-y:auto;background:linear-gradient(135deg,rgba(15,12,41,0.98),rgba(8,20,40,0.98));border:1px solid rgba(0,212,255,0.3);border-radius:18px;padding:24px;box-shadow:0 24px 80px rgba(0,0,0,0.5);animation:guideFadeIn .25s ease}\
@keyframes guideFadeIn{from{opacity:0;transform:translateY(-10px)}to{opacity:1;transform:none}}\
.guide-card::-webkit-scrollbar{width:5px}.guide-card::-webkit-scrollbar-thumb{background:rgba(0,212,255,0.3);border-radius:3px}\
.guide-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px}\
.guide-title{font-size:1.4rem;font-weight:700;color:#7dd3fc;margin:0}\
.guide-close{background:none;border:none;color:#64748b;font-size:1.5rem;cursor:pointer;padding:0 4px;line-height:1}.guide-close:hover{color:#ef4444}\
.guide-intro{color:#94a3b8;font-size:0.95rem;line-height:1.5;margin-bottom:16px}\
.guide-dynamic{background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);border-radius:10px;padding:10px 14px;margin-bottom:14px;color:#4ade80;font-size:0.9rem;line-height:1.4}\
.guide-section-label{color:#475569;font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;display:flex;align-items:center;gap:8px}\
.guide-section-label::after{content:"";flex:1;height:1px;background:rgba(255,255,255,0.06)}\
.guide-actions{list-style:none;padding:0;margin:0 0 16px}\
.guide-actions li{display:flex;align-items:center;gap:8px;padding:6px 0;color:#cbd5e1;font-size:0.88rem}\
.guide-actions li::before{content:"\\25B8";color:#00d4ff;font-size:0.7rem}\
.guide-tts-controls{display:flex;align-items:center;gap:8px;padding:10px 0;border-top:1px solid rgba(255,255,255,0.06);margin-top:8px}\
.guide-tts-btn{padding:6px 14px;border-radius:8px;border:1px solid rgba(0,212,255,0.25);background:rgba(0,212,255,0.08);color:#7dd3fc;cursor:pointer;font-size:0.8rem;font-weight:600;transition:all .2s}\
.guide-tts-btn:hover{background:rgba(0,212,255,0.18)}\
.guide-tts-btn.stop{border-color:rgba(239,68,68,0.25);background:rgba(239,68,68,0.08);color:#fca5a5}\
.guide-tts-btn.stop:hover{background:rgba(239,68,68,0.18)}\
.guide-tts-status{font-size:0.75rem;font-weight:500;margin-left:auto}\
.guide-event-audio{margin-top:12px;padding:12px;background:rgba(255,107,107,0.06);border:1px solid rgba(255,107,107,0.15);border-radius:10px}\
.guide-event-audio-title{color:#ff6b6b;font-size:0.8rem;font-weight:600;margin-bottom:8px}\
.guide-event-btns{display:flex;gap:6px;flex-wrap:wrap}\
.guide-event-btn{padding:5px 12px;border-radius:8px;border:1px solid rgba(255,107,107,0.25);background:rgba(255,107,107,0.08);color:#fca5a5;cursor:pointer;font-size:0.78rem;font-weight:600;transition:all .2s}\
.guide-event-btn:hover{background:rgba(255,107,107,0.18)}\
.guide-event-btn.active{background:rgba(255,107,107,0.25);border-color:#ff6b6b}';
  }

  function createGuideOverlay() {
    if (document.getElementById('vr-area-guide')) return;
    var style = document.createElement('style');
    style.textContent = getGuideCSS();
    document.head.appendChild(style);

    var overlay = document.createElement('div');
    overlay.id = 'vr-area-guide';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-label', 'Area Guide');
    document.body.appendChild(overlay);
  }

  function showGuide(zoneId) {
    var guide = ZONE_GUIDES[zoneId];
    if (!guide) guide = ZONE_GUIDES.hub;

    var dynamicHTML = '';
    if (guide.dynamic) {
      var dynamicText = guide.dynamic();
      dynamicHTML = '<div class="guide-dynamic">' + dynamicText + '</div>';
    }

    var actionsHTML = guide.actions.map(function (a) {
      return '<li>' + a + '</li>';
    }).join('');

    // Events zone gets special audio controls
    var eventsAudioHTML = '';
    if (zoneId === 'events') {
      eventsAudioHTML =
        '<div class="guide-event-audio">' +
          '<div class="guide-event-audio-title">Event Announcements</div>' +
          '<div class="guide-event-btns">' +
            '<button class="guide-event-btn" onclick="VRAreaGuide.announceEvents(\'today\')">Today\'s Events</button>' +
            '<button class="guide-event-btn" onclick="VRAreaGuide.announceEvents(\'tomorrow\')">Tomorrow\'s Events</button>' +
            '<button class="guide-event-btn" onclick="VRAreaGuide.announceEvents(\'weekend\')">This Weekend</button>' +
          '</div>' +
        '</div>';
    }

    var overlay = document.getElementById('vr-area-guide');
    overlay.innerHTML =
      '<div class="guide-card">' +
        '<div class="guide-header">' +
          '<h2 class="guide-title">' + guide.title + '</h2>' +
          '<button class="guide-close" onclick="VRAreaGuide.hide()" aria-label="Close">&times;</button>' +
        '</div>' +
        '<div class="guide-intro">' + guide.intro + '</div>' +
        dynamicHTML +
        '<div class="guide-section-label">What You Can Do</div>' +
        '<ul class="guide-actions">' + actionsHTML + '</ul>' +
        eventsAudioHTML +
        '<div class="guide-tts-controls">' +
          '<button class="guide-tts-btn" onclick="VRAreaGuide.speakGuide()">Read Aloud</button>' +
          '<button class="guide-tts-btn" id="vr-guide-tts-pause" onclick="VRAreaGuide.togglePause()" style="display:none">Pause</button>' +
          '<button class="guide-tts-btn stop" id="vr-guide-tts-stop" onclick="VRAreaGuide.stopSpeaking()" style="display:none">Stop</button>' +
          '<span class="guide-tts-status" id="vr-guide-tts-status"></span>' +
        '</div>' +
      '</div>';

    overlay.classList.add('open');
    guideOpen = true;
  }

  function hideGuide() {
    var overlay = document.getElementById('vr-area-guide');
    if (overlay) overlay.classList.remove('open');
    guideOpen = false;
    stopSpeaking();
  }

  function speakCurrentGuide() {
    var zoneId = detectCurrentZone();
    var guide = ZONE_GUIDES[zoneId] || ZONE_GUIDES.hub;
    var text = guide.title + '. ' + guide.intro + '. ';
    if (guide.dynamic) text += guide.dynamic() + '. ';
    text += 'Here\'s what you can do: ' + guide.actions.join('. ') + '.';

    var pauseBtn = document.getElementById('vr-guide-tts-pause');
    var stopBtn = document.getElementById('vr-guide-tts-stop');
    if (pauseBtn) pauseBtn.style.display = 'inline-block';
    if (stopBtn) stopBtn.style.display = 'inline-block';

    speak(text, function () {
      if (pauseBtn) pauseBtn.style.display = 'none';
      if (stopBtn) stopBtn.style.display = 'none';
    });
  }

  function togglePauseSpeaking() {
    if (ttsPaused) resumeSpeaking();
    else pauseSpeaking();
  }

  /* ═══════════════════════════════════════════════
     EVENTS AUDIO ANNOUNCEMENTS
     ═══════════════════════════════════════════════ */

  var eventAnnouncementQueue = [];
  var eventAnnouncementIdx = 0;
  var eventAnnouncementActive = false;

  function announceEvents(timeframe) {
    if (!ttsSupported) { alert('Text-to-speech is not supported in this browser.'); return; }

    var events = [];
    var allEvts = window.filteredEvents || window._allEvents || window.allEvents || [];
    var now = new Date();

    if (timeframe === 'today') {
      var todayStr = now.toISOString().split('T')[0];
      events = allEvts.filter(function (e) { return e.date && e.date.indexOf(todayStr) !== -1; });
    } else if (timeframe === 'tomorrow') {
      var tom = new Date(now);
      tom.setDate(tom.getDate() + 1);
      var tomStr = tom.toISOString().split('T')[0];
      events = allEvts.filter(function (e) { return e.date && e.date.indexOf(tomStr) !== -1; });
    } else if (timeframe === 'weekend') {
      var day = now.getDay();
      var satOffset = day === 0 ? 6 : (6 - day);
      var sat = new Date(now); sat.setDate(sat.getDate() + satOffset);
      var sun = new Date(sat); sun.setDate(sun.getDate() + 1);
      var satStr = sat.toISOString().split('T')[0];
      var sunStr = sun.toISOString().split('T')[0];
      events = allEvts.filter(function (e) {
        return e.date && (e.date.indexOf(satStr) !== -1 || e.date.indexOf(sunStr) !== -1);
      });
    }

    if (events.length === 0) {
      speak('No events found for ' + timeframe + '. Try a different time period.');
      return;
    }

    var limit = Math.min(events.length, 15);
    var intro = '';
    if (timeframe === 'today') intro = 'Here are today\'s events. ' + events.length + ' events happening today. ';
    else if (timeframe === 'tomorrow') intro = 'Here are tomorrow\'s events. ' + events.length + ' events. ';
    else if (timeframe === 'weekend') intro = 'This weekend\'s events. ' + events.length + ' events. ';

    eventAnnouncementQueue = [intro];
    for (var i = 0; i < limit; i++) {
      var ev = events[i];
      var text = 'Event ' + (i + 1) + ': ' + (ev.title || 'Untitled') + '. ';
      if (ev.location) text += 'At ' + ev.location + '. ';
      if (ev.price) text += ev.price + '. ';
      else if (ev.isFree) text += 'Free admission. ';
      eventAnnouncementQueue.push(text);
    }

    if (events.length > limit) {
      eventAnnouncementQueue.push('And ' + (events.length - limit) + ' more events. Check the events wall for the full list.');
    }

    eventAnnouncementIdx = 0;
    eventAnnouncementActive = true;

    var pauseBtn = document.getElementById('vr-guide-tts-pause');
    var stopBtn = document.getElementById('vr-guide-tts-stop');
    if (pauseBtn) pauseBtn.style.display = 'inline-block';
    if (stopBtn) stopBtn.style.display = 'inline-block';

    speakNextEvent();
  }

  function speakNextEvent() {
    if (!eventAnnouncementActive || eventAnnouncementIdx >= eventAnnouncementQueue.length) {
      eventAnnouncementActive = false;
      var pauseBtn = document.getElementById('vr-guide-tts-pause');
      var stopBtn = document.getElementById('vr-guide-tts-stop');
      if (pauseBtn) pauseBtn.style.display = 'none';
      if (stopBtn) stopBtn.style.display = 'none';
      updateTTSControls();
      return;
    }
    speak(eventAnnouncementQueue[eventAnnouncementIdx], function () {
      eventAnnouncementIdx++;
      speakNextEvent();
    });
  }

  /* ═══════════════════════════════════════════════
     ZONE DETECTION
     ═══════════════════════════════════════════════ */

  function detectCurrentZone() {
    var path = window.location.pathname;
    if (path.indexOf('/vr/events') !== -1) return 'events';
    if (path.indexOf('/vr/movies') !== -1) return 'movies';
    if (path.indexOf('/vr/creators') !== -1) return 'creators';
    if (path.indexOf('/vr/stocks') !== -1) return 'stocks';
    if (path.indexOf('/vr/wellness') !== -1) return 'wellness';
    if (path.indexOf('/vr/weather') !== -1) return 'weather';
    if (path.indexOf('/vr/tutorial') !== -1) return 'tutorial';
    return 'hub';
  }

  /* ═══════════════════════════════════════════════
     KEYBOARD SHORTCUT: G for Guide
     ═══════════════════════════════════════════════ */

  document.addEventListener('keydown', function (e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (e.key === 'g' || e.key === 'G') {
      if (!e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        if (guideOpen) hideGuide();
        else showGuide(detectCurrentZone());
      }
    }
  });

  /* ═══════════════════════════════════════════════
     PUBLIC API
     ═══════════════════════════════════════════════ */

  window.VRAreaGuide = {
    show: function (zoneId) { showGuide(zoneId || detectCurrentZone()); },
    hide: hideGuide,
    toggle: function () {
      if (guideOpen) hideGuide();
      else showGuide(detectCurrentZone());
    },
    speakGuide: speakCurrentGuide,
    togglePause: togglePauseSpeaking,
    stopSpeaking: stopSpeaking,
    announceEvents: announceEvents,
    registerZone: function (id, guide) {
      ZONE_GUIDES[id] = guide;
    },
    isOpen: function () { return guideOpen; }
  };

  /* ═══════════════════════════════════════════════
     INIT
     ═══════════════════════════════════════════════ */

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createGuideOverlay);
  } else {
    createGuideOverlay();
  }

  if (ttsSupported && speechSynthesis.onvoiceschanged !== undefined) {
    speechSynthesis.onvoiceschanged = function () {};
  }
})();
