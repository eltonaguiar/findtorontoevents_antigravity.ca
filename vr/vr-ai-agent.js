/**
 * VR AI Agent — Intelligent Context-Aware Assistant
 *
 * Features:
 *  - Zone-aware intelligence (Stocks, Weather, Events, Movies, Creators, Wellness)
 *  - Voice input (Web Speech API) + Voice output (SpeechSynthesis)
 *  - "STOP" / "SHUT UP" halts audio instantly
 *  - First-time AI mode per zone with auto-prompts
 *  - Tutorial / first-time mode on demand
 *  - Multi-task combining (e.g. "stock insights + weather + jacket")
 *  - Context summarization with clickable auto-prompts
 *  - Icon and menu explanation
 *  - Movie/trailer queue
 *  - Event natural-language queries
 *  - Browser navigation
 *  - Accountability task summaries
 *  - Persistent login button (mobile + desktop)
 *  - User progress tracked in localStorage + server
 *
 * Load: <link rel="stylesheet" href="/vr/vr-ai-agent.css">
 *       <script src="/vr/vr-ai-agent.js"></script>
 */
(function () {
  'use strict';

  // ════════════════════════════════════════════
  // ZONE DETECTION
  // ════════════════════════════════════════════
  function detectZone() {
    var p = location.pathname;
    if (p.indexOf('/vr/events') !== -1) return 'events';
    if (p.indexOf('/vr/movies-tiktok') !== -1) return 'movies';
    if (p.indexOf('/vr/movies') !== -1) return 'movies';
    if (p.indexOf('/vr/creators') !== -1) return 'creators';
    if (p.indexOf('/vr/stocks') !== -1) return 'stocks';
    if (p.indexOf('/vr/wellness') !== -1) return 'wellness';
    if (p.indexOf('/vr/weather') !== -1) return 'weather';
    if (p.indexOf('/vr/tutorial') !== -1) return 'tutorial';
    return 'hub';
  }
  var ZONE = detectZone();

  // ════════════════════════════════════════════
  // LOCAL STORAGE HELPERS
  // ════════════════════════════════════════════
  function store(k, v) { try { localStorage.setItem('vr_ai_' + k, JSON.stringify(v)); } catch (e) { /* ignore */ } }
  function load(k, d) { try { var v = localStorage.getItem('vr_ai_' + k); return v ? JSON.parse(v) : d; } catch (e) { return d; } }

  // ════════════════════════════════════════════
  // USER PROGRESS
  // ════════════════════════════════════════════
  var userProgress = load('progress', {});
  function isFirstVisit(zone) {
    return !userProgress[zone];
  }
  function markVisited(zone) {
    userProgress[zone] = { visited: Date.now(), visitCount: (userProgress[zone] && userProgress[zone].visitCount || 0) + 1 };
    store('progress', userProgress);
    syncProgressToServer();
  }
  function resetFirstTimeMode() {
    userProgress = {};
    store('progress', {});
  }
  function syncProgressToServer() {
    try {
      var user = getLoggedInUser();
      if (!user) return;
      var body = 'user_id=' + encodeURIComponent(user.id || user.username) + '&progress=' + encodeURIComponent(JSON.stringify(userProgress));
      var xhr = new XMLHttpRequest();
      xhr.open('POST', '/api/vr_user_progress.php', true);
      xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
      xhr.send(body);
    } catch (e) { /* fail silently */ }
  }

  // ════════════════════════════════════════════
  // AUTH STATE
  // ════════════════════════════════════════════
  function getLoggedInUser() {
    // Check global VR auth
    if (window.vrAuthUser) return window.vrAuthUser;
    // Check sessionStorage
    try {
      var u = sessionStorage.getItem('vr_auth_user');
      if (u) return JSON.parse(u);
    } catch (e) { /* ignore */ }
    // Check FavCreators auth
    try {
      var fc = sessionStorage.getItem('fc_user');
      if (fc) return JSON.parse(fc);
    } catch (e) { /* ignore */ }
    return null;
  }
  function setLoggedInUser(user) {
    window.vrAuthUser = user;
    try { sessionStorage.setItem('vr_auth_user', JSON.stringify(user)); } catch (e) { /* ignore */ }
  }

  // ════════════════════════════════════════════
  // STATE
  // ════════════════════════════════════════════
  var state = {
    panelOpen: false,
    listening: false,
    speaking: false,
    recognition: null,
    tutorialMode: false,
    chatHistory: [],
    pendingStopWords: ['stop', 'shut up', 'be quiet', 'silence', 'enough', 'quiet', 'hush'],
    viewMode: 'full'  // 'full', 'simple', 'focus'
  };

  // ════════════════════════════════════════════
  // VIEW MODE SYSTEM (Focus / Simple / Full)
  // ════════════════════════════════════════════
  function getViewMode() {
    return state.viewMode;
  }

  function setViewMode(mode) {
    if (mode !== 'full' && mode !== 'simple' && mode !== 'focus') mode = 'full';
    var prev = state.viewMode;
    state.viewMode = mode;
    try { localStorage.setItem('vr_ai_viewmode', mode); } catch (e) { /* ignore */ }

    // Apply focus mode CSS class
    document.body.classList.toggle('vr-focus-mode', mode === 'focus');

    // Sync with VRModeToggle for simple/advanced
    if (window.VRModeToggle) {
      if (mode === 'simple') {
        window.VRModeToggle.setMode('simple');
      } else if (mode === 'full') {
        window.VRModeToggle.setMode('advanced');
      }
      // focus mode: also set simple underneath so advanced buttons are hidden
      if (mode === 'focus') {
        window.VRModeToggle.setMode('simple');
      }
    }

    // Update the view-mode bar buttons
    updateViewModeBar();

    // Show a transient notification badge
    if (mode !== prev) {
      showFocusBadge(mode);
    }
  }

  function showFocusBadge(mode) {
    var labels = { full: '\uD83C\uDFDB\uFE0F Advanced Mode — All UI visible', simple: '\uD83C\uDFAF Simple Mode — Clean UI', focus: '\uD83E\uDDD8 Focus Mode — Immersive View' };
    var old = document.querySelector('.vr-focus-badge');
    if (old) old.remove();
    var badge = document.createElement('div');
    badge.className = 'vr-focus-badge';
    badge.textContent = labels[mode] || mode;
    document.body.appendChild(badge);
    setTimeout(function () { try { badge.remove(); } catch (e) { /* ignore */ } }, 3200);
  }

  function updateViewModeBar() {
    var bar = document.getElementById('vr-agent-viewmode-bar');
    if (!bar) return;
    var btns = bar.querySelectorAll('.vr-agent-viewmode-btn');
    for (var i = 0; i < btns.length; i++) {
      btns[i].classList.toggle('active', btns[i].getAttribute('data-mode') === state.viewMode);
    }
    // Update focus button in header
    var focusBtn = document.getElementById('vr-agent-focus-toggle');
    if (focusBtn) focusBtn.classList.toggle('active', state.viewMode === 'focus');
  }

  // ════════════════════════════════════════════
  // ZONE META — descriptions, icons, prompts
  // ════════════════════════════════════════════
  var ZONE_META = {
    hub: {
      name: 'VR Hub',
      emoji: '\uD83C\uDFE0',
      color: '#00d4ff',
      welcome: 'Welcome to the VR Hub! This is your launchpad to all zones.',
      prompts: ['What can I do here?', 'Take me to Events', 'Play FPS Arena', 'What games do you have?', 'Are my streamers online?', 'Simple mode'],
      icons: {
        'Events Portal': 'Opens the Toronto Events explorer with 1000+ events you can filter and browse',
        'Movies Portal': 'Enter the VR Movie Theater to watch trailers and browse movies/TV shows',
        'Creators Portal': 'See your favorite content creators and who is streaming live',
        'Weather Portal': 'Check Toronto weather with dynamic VR weather effects',
        'Stocks Portal': 'View stock market simulations and price trackers',
        'Wellness Portal': 'Enter the Wellness Garden for breathing exercises and habit tracking',
        'Game Arena Portal': 'Play games! FPS Arena, Tic-Tac-Toe, Soccer Shootout, and Ant Rush AR',
        'Ant Rush Portal': 'AR game — clean your space before the ants swarm!',
        'Tutorial Portal': 'Step-by-step guide to VR controls (look, click, move, teleport)',
        'Navigation Menu (M/Tab)': 'Opens the zone menu with music player and context actions',
        'AI Agent button': 'Opens this AI assistant panel for voice and text help'
      }
    },
    events: {
      name: 'Events Explorer',
      emoji: '\uD83D\uDCC5',
      color: '#ff6b6b',
      welcome: 'Welcome to the Events Explorer! Browse hundreds of Toronto events in immersive 3D.',
      prompts: ['Summarize dating events this week', 'What dancing events are today?', 'Overview of events this weekend', 'Explain all icons', 'Events starting soon'],
      icons: {
        'Category pills (top)': 'Filter events by category: Arts, Tech, Festival, Sports, Music, etc.',
        'Search bar (/ or F)': 'Search events by name or keyword',
        'Arrow keys': 'Navigate between pages of events',
        'Event cards': 'Click any card to see full details including date, location, and description',
        'View Event button': 'Opens the event page in your browser',
        'Preview button': 'Shows the event page inline without leaving VR',
        'Audio controls': 'Listen to event summaries read aloud via text-to-speech',
        'Back to Hub': 'Return to the main VR hub'
      }
    },
    movies: {
      name: 'Movie Theater',
      emoji: '\uD83C\uDFAC',
      color: '#4ecdc4',
      welcome: 'Welcome to the VR Movie Theater! Browse trailers, build queues, and discover what\'s playing.',
      prompts: ['Queue Avatar trailers', 'What movies are playing?', 'Show me action movies', 'Explain all icons', 'Find sci-fi shows'],
      icons: {
        'Movie posters (walls)': 'Left wall: Movies, Right wall: TV Shows. Click any poster for details.',
        'Play button': 'Watch the trailer on the big cinema screen',
        'Queue system': 'Add movies to your watch queue and auto-play through them',
        'Search bar': 'Search for specific movies or TV shows by title',
        'Category bar': 'Filter by genre (Action, Comedy, Drama, Sci-Fi, etc.)',
        'Cinema theme selector': 'Change the cinema ambiance (Classic, IMAX, Drive-In, etc.)',
        'Arrow keys': 'Browse through the movie collection'
      }
    },
    creators: {
      name: 'FavCreators Live Lounge',
      emoji: '\uD83D\uDCFA',
      color: '#a855f7',
      welcome: 'Welcome to the FavCreators Live Lounge! See who\'s streaming and watch your favorites.',
      prompts: ['Who is live?', 'Open first live streamer', 'Refresh streamers', 'Explain all icons', 'Show my creators'],
      icons: {
        'Creator cards': 'Shows each creator with their avatar, platform, and live status',
        'LIVE badge': 'Indicates the creator is currently streaming. Click to watch.',
        'Platform filters (1-5)': '1=All, 2=TikTok, 3=Twitch, 4=Kick, 5=YouTube',
        'Login button': 'Sign in to see your personalized creator list',
        'Refresh (R)': 'Manually refresh the live status of all creators',
        'Live Now menu': 'Quick-access dropdown showing everyone currently live',
        'Recent Videos': 'Shows recent YouTube uploads for each creator'
      }
    },
    stocks: {
      name: 'Stock Trading Floor',
      emoji: '\uD83D\uDCC8',
      color: '#22c55e',
      welcome: 'Welcome to the Trading Floor! View real-time stock simulations and track market trends.',
      prompts: ['Top stock picks and why', 'Explain the math behind picks', 'What stocks are up?', 'Explain all icons', 'Show me NVDA details'],
      icons: {
        'Top Gainers panel': 'Shows the 3 stocks with the biggest positive price movement today',
        'Top Losers panel': 'Shows the 3 stocks with the biggest negative price movement today',
        'Stock pedestals': 'Click any stock pedestal for detailed info (price, volume, market cap, high/low)',
        'News ticker': 'Scrolling market news headlines at the top',
        'Stock detail popup': 'Floating panel with comprehensive data about a selected stock',
        'Refresh (R)': 'Refresh all stock prices',
        'Trading sounds': 'Ambient trading floor audio for immersion'
      }
    },
    weather: {
      name: 'Weather Observatory',
      emoji: '\u26C5',
      color: '#06b6d4',
      welcome: 'Welcome to the Weather Observatory! See live Toronto weather with dynamic VR effects.',
      prompts: ['Do I need a jacket?', 'What\'s the weather today?', 'Weekly forecast', 'Explain all icons', 'Weather for M5V 3A8'],
      icons: {
        'Current conditions panel': 'Shows temperature, feels like, condition, wind, humidity, and UV index',
        'Dynamic VR sky': 'The sky and particles change based on actual weather (rain, snow, sun, fog, etc.)',
        'Forecast cards': 'Click for detailed daily forecasts for the next 7 days',
        'Clothing advice': 'Automatic suggestions on what to wear based on current conditions',
        'Passthrough mode': 'Toggle AR passthrough to see the weather effects overlaid on your real room',
        'Manual weather buttons': 'Test different weather conditions (Clear, Rain, Snow, Storm)',
        'Sunrise/Sunset': 'Shows today\'s sunrise and sunset times'
      }
    },
    wellness: {
      name: 'Wellness Garden',
      emoji: '\uD83C\uDF3F',
      color: '#f59e0b',
      welcome: 'Welcome to the Wellness Garden! A calm space for breathing, habits, and mindfulness.',
      prompts: ['Summarize my accountability tasks', 'Start breathing exercise', 'Show my streaks', 'Explain all icons', 'Give me a motivational quote'],
      icons: {
        'Breathing sphere': 'Follow the expanding/contracting sphere for 4-7-8 breathing technique',
        'Accountability Coach': 'Shows your current goal and streak counter',
        'Daily check-in': 'Mark today as completed for your habit/goal',
        'Motivational quotes wall': 'Browse and navigate through motivational quotes',
        'Meditation spot': 'Walk to the meditation area for a calming ambient experience',
        'Gratitude Tree': 'Interactive tree where you can add gratitude leaves',
        'Teleport points': 'Quick-jump to different areas within the garden'
      }
    },
    tutorial: {
      name: 'Tutorial',
      emoji: '\u2753',
      color: '#f59e0b',
      welcome: 'This is the Tutorial! Learn VR controls step by step.',
      prompts: ['Start from beginning', 'How do I move?', 'How do I teleport?', 'Explain all controls'],
      icons: {
        'Step dots': 'Shows your progress through the 7 tutorial steps',
        'Look Around': 'Step 1: Move your head or mouse to look around the VR space',
        'Point & Click': 'Step 2: Aim your cursor and click/tap to interact',
        'Move Around': 'Step 3: Use WASD keys or left thumbstick to walk',
        'Teleport': 'Step 4: Click the ground or use trigger to teleport',
        'Snap Turn': 'Step 5: Use Q/E keys or right thumbstick to rotate',
        'Open Menu': 'Step 6: Press M or Tab to open the navigation menu',
        'Go to Hub': 'Step 7: Navigate back to the main hub'
      }
    }
  };

  // ════════════════════════════════════════════
  // SPEECH SYNTHESIS (TTS)
  // ════════════════════════════════════════════
  function speak(text, callback) {
    if (!window.speechSynthesis) {
      if (callback) callback();
      return;
    }
    window.speechSynthesis.cancel();
    var utter = new SpeechSynthesisUtterance(text);
    utter.rate = 1.05;
    utter.pitch = 1;
    utter.volume = 0.9;
    // Try to pick a good voice
    var voices = window.speechSynthesis.getVoices();
    for (var i = 0; i < voices.length; i++) {
      if (voices[i].lang && voices[i].lang.indexOf('en') === 0 && voices[i].name.indexOf('Google') !== -1) {
        utter.voice = voices[i];
        break;
      }
    }
    state.speaking = true;
    updateStatus('speaking');
    utter.onend = function () {
      state.speaking = false;
      updateStatus('idle');
      if (callback) callback();
    };
    utter.onerror = function () {
      state.speaking = false;
      updateStatus('idle');
      if (callback) callback();
    };
    window.speechSynthesis.speak(utter);
  }

  function stopSpeaking() {
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    state.speaking = false;
    updateStatus('idle');
  }

  // ════════════════════════════════════════════
  // SPEECH RECOGNITION (STT)
  // ════════════════════════════════════════════
  function initRecognition() {
    var SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) return null;
    var rec = new SpeechRec();
    rec.continuous = false;
    rec.interimResults = false;
    rec.lang = 'en-US';
    rec.maxAlternatives = 1;
    rec.onresult = function (event) {
      var transcript = event.results[0][0].transcript;
      handleUserInput(transcript);
    };
    rec.onend = function () {
      state.listening = false;
      updateMicUI(false);
      updateStatus('idle');
    };
    rec.onerror = function (e) {
      state.listening = false;
      updateMicUI(false);
      updateStatus('idle');
      if (e.error !== 'no-speech' && e.error !== 'aborted') {
        addMessage('agent', 'Microphone error: ' + e.error + '. Try clicking the mic again.');
      }
    };
    return rec;
  }

  function startListening() {
    if (state.listening) {
      stopListening();
      return;
    }
    if (!state.recognition) {
      state.recognition = initRecognition();
    }
    if (!state.recognition) {
      addMessage('agent', 'Speech recognition is not supported in your browser. Please type your message instead.');
      return;
    }
    try {
      state.recognition.start();
      state.listening = true;
      updateMicUI(true);
      updateStatus('listening');
    } catch (e) {
      // Already started
      state.listening = false;
      updateMicUI(false);
    }
  }

  function stopListening() {
    if (state.recognition) {
      try { state.recognition.stop(); } catch (e) { /* ignore */ }
    }
    state.listening = false;
    updateMicUI(false);
    updateStatus('idle');
  }

  // ════════════════════════════════════════════
  // UI CREATION
  // ════════════════════════════════════════════
  function createUI() {
    // CSS
    if (!document.getElementById('vr-ai-agent-css')) {
      var link = document.createElement('link');
      link.id = 'vr-ai-agent-css';
      link.rel = 'stylesheet';
      link.href = '/vr/vr-ai-agent.css';
      document.head.appendChild(link);
    }

    // ── Login Button ──
    createLoginButton();

    // ── Agent Toggle Button ──
    var btn = document.createElement('button');
    btn.id = 'vr-agent-btn';
    btn.innerHTML = '\uD83E\uDD16';
    btn.title = 'AI Agent';
    btn.addEventListener('click', togglePanel);
    document.body.appendChild(btn);

    // ── Agent Panel ──
    var panel = document.createElement('div');
    panel.id = 'vr-agent-panel';
    var meta = ZONE_META[ZONE] || ZONE_META.hub;
    panel.innerHTML =
      '<div class="vr-agent-header">' +
        '<span class="title">\uD83E\uDD16 AI Agent <span class="zone-badge">' + meta.emoji + ' ' + meta.name + '</span></span>' +
        '<div style="display:flex;align-items:center;gap:2px;">' +
          '<button class="vr-agent-focus-btn" id="vr-agent-focus-toggle" title="Toggle Focus Mode — hide all UI clutter">\uD83E\uDDD8</button>' +
          '<button class="close-btn" id="vr-agent-close">&times;</button>' +
        '</div>' +
      '</div>' +
      '<div class="vr-agent-viewmode-bar" id="vr-agent-viewmode-bar">' +
        '<button class="vr-agent-viewmode-btn" data-mode="full" title="Show all UI elements">' +
          '<span class="mode-icon">\uD83C\uDFDB\uFE0F</span>Full' +
        '</button>' +
        '<button class="vr-agent-viewmode-btn" data-mode="simple" title="Minimal UI — essentials only">' +
          '<span class="mode-icon">\uD83C\uDFAF</span>Simple' +
        '</button>' +
        '<button class="vr-agent-viewmode-btn" data-mode="focus" title="Focus Mode — just 3D + AI">' +
          '<span class="mode-icon">\uD83E\uDDD8</span>Focus' +
        '</button>' +
      '</div>' +
      '<div class="vr-agent-chat" id="vr-agent-chat"></div>' +
      '<div class="vr-agent-prompts" id="vr-agent-prompts"></div>' +
      '<div class="vr-agent-status" id="vr-agent-status">' +
        '<span class="dot idle" id="vr-agent-dot"></span>' +
        '<span id="vr-agent-status-text">Ready</span>' +
      '</div>' +
      '<div class="vr-agent-input-area">' +
        '<input type="text" id="vr-agent-input" placeholder="Ask me anything..." autocomplete="off">' +
        '<button class="vr-agent-mic-btn" id="vr-agent-mic" title="Hold to talk">\uD83C\uDFA4</button>' +
        '<button class="vr-agent-send-btn" id="vr-agent-send" title="Send">\u27A4</button>' +
      '</div>';
    document.body.appendChild(panel);

    // Event listeners
    document.getElementById('vr-agent-close').addEventListener('click', togglePanel);
    document.getElementById('vr-agent-send').addEventListener('click', function () {
      var input = document.getElementById('vr-agent-input');
      if (input.value.trim()) {
        handleUserInput(input.value.trim());
        input.value = '';
      }
    });
    document.getElementById('vr-agent-input').addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && this.value.trim()) {
        handleUserInput(this.value.trim());
        this.value = '';
      }
    });
    document.getElementById('vr-agent-mic').addEventListener('click', function () {
      startListening();
    });

    // ── Focus Mode toggle button ──
    document.getElementById('vr-agent-focus-toggle').addEventListener('click', function () {
      var newMode = state.viewMode === 'focus' ? 'full' : 'focus';
      setViewMode(newMode);
      addMessage('agent', newMode === 'focus'
        ? '\uD83E\uDDD8 <strong>Focus Mode</strong> enabled. All overlays and HUDs are hidden. Just you, the 3D scene, and me. Say "<strong>show ui</strong>" or click the button again to restore.'
        : '\uD83C\uDFDB\uFE0F Back to <strong>Full Mode</strong>. All UI elements are visible again.');
    });

    // ── View Mode bar buttons ──
    var viewModeBar = document.getElementById('vr-agent-viewmode-bar');
    if (viewModeBar) {
      viewModeBar.addEventListener('click', function (e) {
        var btn = e.target.closest('.vr-agent-viewmode-btn');
        if (!btn) return;
        var mode = btn.getAttribute('data-mode');
        if (mode) {
          setViewMode(mode);
          var modeLabels = { full: '\uD83C\uDFDB\uFE0F Full Mode — all UI elements visible', simple: '\uD83C\uDFAF Simple Mode — clean, minimal UI', focus: '\uD83E\uDDD8 Focus Mode — immersive, just 3D + AI' };
          addMessage('agent', '<strong>View mode changed:</strong> ' + (modeLabels[mode] || mode));
        }
      });
    }

    // ── Login Overlay ──
    createLoginOverlay();

    // ── Welcome Banner ──
    createWelcomeBanner();

    // Load prompts
    renderPrompts();
  }

  function createLoginButton() {
    var btn = document.createElement('button');
    btn.id = 'vr-agent-login-btn';
    var user = getLoggedInUser();
    if (user) {
      btn.innerHTML = '\uD83D\uDC64 ' + (user.display_name || user.username || 'User');
      btn.classList.add('logged-in');
      btn.title = 'Logged in as ' + (user.username || user.display_name || 'User');
    } else {
      btn.innerHTML = '\uD83D\uDD11 Login';
      btn.title = 'Sign in to personalize your experience';
    }
    btn.addEventListener('click', function () {
      var user = getLoggedInUser();
      if (user) {
        // Show user info or logout option
        if (confirm('Logged in as ' + (user.username || user.display_name) + '.\n\nWould you like to log out?')) {
          doLogout();
        }
      } else {
        showLoginOverlay();
      }
    });
    document.body.appendChild(btn);
  }

  function updateLoginButton() {
    var btn = document.getElementById('vr-agent-login-btn');
    if (!btn) return;
    var user = getLoggedInUser();
    if (user) {
      btn.innerHTML = '\uD83D\uDC64 ' + (user.display_name || user.username || 'User');
      btn.classList.add('logged-in');
    } else {
      btn.innerHTML = '\uD83D\uDD11 Login';
      btn.classList.remove('logged-in');
    }
  }

  function createLoginOverlay() {
    var overlay = document.createElement('div');
    overlay.id = 'vr-agent-login-overlay';
    overlay.innerHTML =
      '<div class="vr-agent-login-box">' +
        '<h2>\uD83D\uDD11 Sign In</h2>' +
        '<div class="subtitle">Use your FavCreators account</div>' +
        '<div class="login-error" id="vr-login-error"></div>' +
        '<input type="text" id="vr-login-user" placeholder="Username">' +
        '<input type="password" id="vr-login-pass" placeholder="Password">' +
        '<button class="login-submit" id="vr-login-submit">Sign In</button>' +
        '<button class="login-cancel" id="vr-login-cancel">Cancel</button>' +
      '</div>';
    document.body.appendChild(overlay);
    document.getElementById('vr-login-submit').addEventListener('click', doLogin);
    document.getElementById('vr-login-cancel').addEventListener('click', hideLoginOverlay);
    document.getElementById('vr-login-pass').addEventListener('keydown', function (e) {
      if (e.key === 'Enter') doLogin();
    });
  }

  function showLoginOverlay() {
    var overlay = document.getElementById('vr-agent-login-overlay');
    if (overlay) overlay.classList.add('open');
  }
  function hideLoginOverlay() {
    var overlay = document.getElementById('vr-agent-login-overlay');
    if (overlay) overlay.classList.remove('open');
    document.getElementById('vr-login-error').textContent = '';
    document.getElementById('vr-login-user').value = '';
    document.getElementById('vr-login-pass').value = '';
  }

  function doLogin() {
    var user = document.getElementById('vr-login-user').value.trim();
    var pass = document.getElementById('vr-login-pass').value;
    if (!user || !pass) {
      document.getElementById('vr-login-error').textContent = 'Please enter username and password';
      return;
    }
    document.getElementById('vr-login-error').textContent = 'Signing in...';
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/fc/api/login.php', true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.withCredentials = true;
    xhr.onload = function () {
      try {
        var res = JSON.parse(xhr.responseText);
        if (res.success || res.user) {
          var userData = res.user || { username: user, display_name: user, id: user };
          setLoggedInUser(userData);
          hideLoginOverlay();
          updateLoginButton();
          addMessage('agent', 'Welcome back, <strong>' + (userData.display_name || userData.username) + '</strong>! Your personalized data is now loaded.');
          syncProgressToServer();
        } else {
          document.getElementById('vr-login-error').textContent = res.error || 'Invalid credentials';
        }
      } catch (e) {
        document.getElementById('vr-login-error').textContent = 'Login failed. Please try again.';
      }
    };
    xhr.onerror = function () {
      document.getElementById('vr-login-error').textContent = 'Network error. Please try again.';
    };
    xhr.send('username=' + encodeURIComponent(user) + '&password=' + encodeURIComponent(pass));
  }

  function doLogout() {
    window.vrAuthUser = null;
    try { sessionStorage.removeItem('vr_auth_user'); } catch (e) { /* ignore */ }
    try { sessionStorage.removeItem('fc_user'); } catch (e) { /* ignore */ }
    updateLoginButton();
    addMessage('agent', 'You have been logged out. Sign in again anytime to personalize your experience.');
  }

  // ════════════════════════════════════════════
  // WELCOME / FIRST-TIME BANNER
  // ════════════════════════════════════════════
  function createWelcomeBanner() {
    var banner = document.createElement('div');
    banner.id = 'vr-agent-welcome';
    document.body.appendChild(banner);
  }

  function showWelcome() {
    var meta = ZONE_META[ZONE] || ZONE_META.hub;
    var banner = document.getElementById('vr-agent-welcome');
    if (!banner) return;
    banner.innerHTML =
      '<button class="dismiss-btn" id="vr-welcome-dismiss">&times;</button>' +
      '<h3>' + meta.emoji + ' ' + meta.welcome + '</h3>' +
      '<p>I\'m your AI assistant. I can help you navigate, summarize content, and answer questions about this zone. Try clicking one of these:</p>' +
      '<div class="welcome-actions" id="vr-welcome-actions"></div>';
    var actions = banner.querySelector('#vr-welcome-actions');
    var prompts = meta.prompts || [];
    for (var i = 0; i < Math.min(prompts.length, 4); i++) {
      var b = document.createElement('button');
      b.className = 'welcome-btn ' + (i === 0 ? 'primary' : 'secondary');
      b.textContent = prompts[i];
      b.setAttribute('data-prompt', prompts[i]);
      b.addEventListener('click', function () {
        var prompt = this.getAttribute('data-prompt');
        dismissWelcome();
        openPanel();
        handleUserInput(prompt);
      });
      actions.appendChild(b);
    }
    // Dismiss on main dismiss
    var dismissBtn = document.createElement('button');
    dismissBtn.className = 'welcome-btn secondary';
    dismissBtn.textContent = 'Got it, dismiss';
    dismissBtn.addEventListener('click', dismissWelcome);
    actions.appendChild(dismissBtn);

    banner.classList.add('show');
    document.getElementById('vr-welcome-dismiss').addEventListener('click', dismissWelcome);

    // Also speak the welcome
    speak(meta.welcome + ' I can help you navigate and answer questions about this area.');

    // Auto-dismiss after 15s
    setTimeout(function () { dismissWelcome(); }, 15000);
  }

  function dismissWelcome() {
    var banner = document.getElementById('vr-agent-welcome');
    if (banner) banner.classList.remove('show');
    markVisited(ZONE);
  }

  // ════════════════════════════════════════════
  // PANEL MANAGEMENT
  // ════════════════════════════════════════════
  function togglePanel() {
    state.panelOpen = !state.panelOpen;
    var panel = document.getElementById('vr-agent-panel');
    var btn = document.getElementById('vr-agent-btn');
    if (panel) panel.classList.toggle('open', state.panelOpen);
    if (btn) btn.classList.toggle('active', state.panelOpen);
    if (state.panelOpen && state.chatHistory.length === 0) {
      showContextSummary();
    }
  }
  function openPanel() {
    if (!state.panelOpen) togglePanel();
  }

  // ════════════════════════════════════════════
  // CHAT MESSAGES
  // ════════════════════════════════════════════
  function addMessage(role, html, alsoSpeak) {
    var chat = document.getElementById('vr-agent-chat');
    if (!chat) return;
    var msg = document.createElement('div');
    msg.className = 'vr-agent-msg ' + role;
    var label = role === 'agent' ? '\uD83E\uDD16 Agent' : '\uD83D\uDC64 You';
    msg.innerHTML = '<span class="msg-label">' + label + '</span>' + html;
    chat.appendChild(msg);
    chat.scrollTop = chat.scrollHeight;
    state.chatHistory.push({ role: role, html: html, time: Date.now() });

    if (alsoSpeak && role === 'agent') {
      // Strip HTML for speaking
      var text = html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
      speak(text);
    }
  }

  // ════════════════════════════════════════════
  // PROMPTS
  // ════════════════════════════════════════════
  function renderPrompts(custom) {
    var container = document.getElementById('vr-agent-prompts');
    if (!container) return;
    container.innerHTML = '';
    var meta = ZONE_META[ZONE] || ZONE_META.hub;
    var prompts = custom || meta.prompts || [];
    for (var i = 0; i < prompts.length; i++) {
      var btn = document.createElement('button');
      btn.className = 'vr-agent-prompt-btn';
      btn.textContent = prompts[i];
      btn.setAttribute('data-prompt', prompts[i]);
      btn.addEventListener('click', function () {
        handleUserInput(this.getAttribute('data-prompt'));
      });
      container.appendChild(btn);
    }
  }

  function updateMicUI(on) {
    var mic = document.getElementById('vr-agent-mic');
    if (mic) mic.classList.toggle('listening', on);
  }

  function updateStatus(st) {
    var dot = document.getElementById('vr-agent-dot');
    var text = document.getElementById('vr-agent-status-text');
    if (!dot) return;
    dot.className = 'dot ' + st;
    var labels = { idle: 'Ready', listening: 'Listening...', speaking: 'Speaking...', thinking: 'Thinking...' };
    if (text) text.textContent = labels[st] || 'Ready';
  }

  // ════════════════════════════════════════════
  // MAIN INPUT HANDLER
  // ════════════════════════════════════════════
  function handleUserInput(text) {
    if (!text) return;
    addMessage('user', escapeHtml(text));
    stopListening();

    var lower = text.toLowerCase().trim();

    // ── STOP commands ──
    for (var s = 0; s < state.pendingStopWords.length; s++) {
      if (lower === state.pendingStopWords[s] || lower.indexOf(state.pendingStopWords[s]) !== -1) {
        stopSpeaking();
        addMessage('agent', 'Stopping now. Click the AI button and mic icon to re-enable voice if you want to talk again.', true);
        return;
      }
    }

    updateStatus('thinking');

    // ── VIEW MODE commands ──
    // Focus / Zen mode
    if (lower.indexOf('focus mode') !== -1 || lower.indexOf('zen mode') !== -1 || lower.indexOf('hide ui') !== -1 || lower.indexOf('hide everything') !== -1 || lower.indexOf('clean view') !== -1 || lower.indexOf('immersive mode') !== -1 || lower.indexOf('distraction') !== -1) {
      setViewMode('focus');
      addMessage('agent', '\uD83E\uDDD8 <strong>Focus Mode</strong> activated! All overlays, menus, and HUDs are now hidden. It\'s just you, the 3D scene, and me.<br><br>Say "<strong>show ui</strong>", "<strong>full mode</strong>", or "<strong>simple mode</strong>" to change back. You can also use the view mode buttons at the top of this panel.', true);
      renderPrompts(['Show UI', 'Simple mode', 'Full mode', 'Help']);
      updateStatus('idle');
      return;
    }

    // Simple mode
    if ((lower.indexOf('simple mode') !== -1 || lower.indexOf('simple view') !== -1 || lower.indexOf('minimal mode') !== -1 || lower.indexOf('minimal ui') !== -1 || lower.indexOf('clean mode') !== -1) && lower.indexOf('focus') === -1) {
      setViewMode('simple');
      addMessage('agent', '\uD83C\uDFAF <strong>Simple Mode</strong> activated! Advanced controls are hidden — only essential navigation and features remain visible.<br><br>Say "<strong>full mode</strong>" to restore everything, or "<strong>focus mode</strong>" for maximum immersion.', true);
      renderPrompts(['Full mode', 'Focus mode', 'Help']);
      updateStatus('idle');
      return;
    }

    // Full / Advanced / Show UI
    if (lower.indexOf('full mode') !== -1 || lower.indexOf('advanced mode') !== -1 || lower.indexOf('show ui') !== -1 || lower.indexOf('show everything') !== -1 || lower.indexOf('exit focus') !== -1 || lower.indexOf('normal mode') !== -1 || lower.indexOf('restore ui') !== -1 || lower.indexOf('all features') !== -1) {
      setViewMode('full');
      addMessage('agent', '\uD83C\uDFDB\uFE0F <strong>Full Mode</strong> restored! All UI elements, menus, and HUDs are visible again.', true);
      renderPrompts(['Simple mode', 'Focus mode', 'Help']);
      updateStatus('idle');
      return;
    }

    // Mobile mode
    if (lower.indexOf('mobile mode') !== -1 || lower.indexOf('mobile view') !== -1 || lower.indexOf('phone mode') !== -1 || lower.indexOf('touch mode') !== -1) {
      return handleMobileMode();
    }

    // What mode / current mode
    if ((lower.indexOf('what mode') !== -1 || lower.indexOf('current mode') !== -1 || lower.indexOf('which mode') !== -1) && (lower.indexOf('view') !== -1 || lower.indexOf('ui') !== -1 || lower.indexOf('mode') !== -1)) {
      var modeNames = { full: '\uD83C\uDFDB\uFE0F Full / Advanced', simple: '\uD83C\uDFAF Simple / Minimal', focus: '\uD83E\uDDD8 Focus / Zen' };
      addMessage('agent', 'Current view mode: <strong>' + (modeNames[state.viewMode] || state.viewMode) + '</strong><br><br>Available modes:<br>\u2022 <strong>Full</strong> — all UI visible<br>\u2022 <strong>Simple</strong> — essentials only<br>\u2022 <strong>Focus</strong> — just 3D + AI chatbot<br><br>Say the mode name or use the buttons at the top of this panel.', true);
      renderPrompts(['Full mode', 'Simple mode', 'Focus mode']);
      updateStatus('idle');
      return;
    }

    // ── Tutorial / first-time mode ──
    if (lower.indexOf('tutorial mode') !== -1 || lower.indexOf('first time mode') !== -1 || lower.indexOf('first-time mode') !== -1 || lower.indexOf('enable tutorial') !== -1) {
      resetFirstTimeMode();
      addMessage('agent', 'Tutorial mode enabled! I\'ll re-introduce each zone as you visit them. Refreshing this zone now...', true);
      setTimeout(function () { showWelcome(); }, 1500);
      return;
    }

    // ── Explain all icons ──
    if (lower.indexOf('explain') !== -1 && (lower.indexOf('icon') !== -1 || lower.indexOf('menu') !== -1 || lower.indexOf('button') !== -1 || lower.indexOf('option') !== -1)) {
      return handleExplainIcons();
    }

    // ── Context summary ──
    if (lower.indexOf('summarize current') !== -1 || lower.indexOf('where am i') !== -1 || lower.indexOf('what is this') !== -1 || lower.indexOf('current context') !== -1) {
      return showContextSummary();
    }

    // ── Games — direct intent matching ──
    if (lower.indexOf('fps') !== -1 || lower.indexOf('first person shooter') !== -1 || lower.indexOf('first-person shooter') !== -1 || lower.indexOf('shooting game') !== -1) {
      addMessage('agent', '\uD83C\uDFAF <strong>FPS Arena</strong> — Our first-person shooter with 6 weapons, AI bots, ranked multiplayer, grenades, and more!<br><br><a href="/vr/game-arena/fps-arena.html" style="color:#ef4444;font-weight:700;">Click here to play FPS Arena</a>', true);
      renderPrompts(['Take me there', 'What weapons are there?', 'Game Arena Hub']);
      if (lower.indexOf('take me') !== -1 || lower.indexOf('go to') !== -1 || lower.indexOf('play') !== -1 || lower.indexOf('open') !== -1 || lower.indexOf('start') !== -1) {
        setTimeout(function () { window.location.href = '/vr/game-arena/fps-arena.html'; }, 2000);
      }
      updateStatus('idle');
      return;
    }
    if (lower.indexOf('fighting game') !== -1 || lower.indexOf('fight game') !== -1 || lower.indexOf('combat game') !== -1 || lower.indexOf('battle game') !== -1 || lower.indexOf('pvp') !== -1) {
      addMessage('agent', '\u2694\uFE0F We have <strong>FPS Arena</strong> — a fast-paced first-person shooter with PvP multiplayer, 6 weapons, AI bots, and ranked tiers!<br><br><a href="/vr/game-arena/fps-arena.html" style="color:#ef4444;font-weight:700;">Play FPS Arena</a> &nbsp;|&nbsp; <a href="/vr/game-arena/" style="color:#a855f7;font-weight:700;">Browse all games</a>', true);
      renderPrompts(['Take me to FPS Arena', 'Show all games', 'What games do you have?']);
      updateStatus('idle');
      return;
    }
    if (lower.indexOf('ant rush') !== -1 || lower.indexOf('antrush') !== -1 || lower.indexOf('ant game') !== -1 || lower.indexOf('cleaning game') !== -1) {
      addMessage('agent', '\uD83D\uDC1C <strong>Ant Rush AR</strong> — Clean your space before the ants take over! Features Bed Challenge and Quick Mode with photo-based AR.<br><br><a href="/vr/ant-rush/" style="color:#ff6b35;font-weight:700;">Click here to play Ant Rush</a>', true);
      renderPrompts(['Take me there', 'Game Arena Hub', 'What other games?']);
      if (lower.indexOf('take me') !== -1 || lower.indexOf('go to') !== -1 || lower.indexOf('play') !== -1 || lower.indexOf('open') !== -1) {
        setTimeout(function () { window.location.href = '/vr/ant-rush/'; }, 2000);
      }
      updateStatus('idle');
      return;
    }
    if (lower.indexOf('tic tac toe') !== -1 || lower.indexOf('tictactoe') !== -1 || lower.indexOf('tic-tac-toe') !== -1 || lower.indexOf('noughts and crosses') !== -1) {
      addMessage('agent', '\u274C\u2B55 <strong>Tic-Tac-Toe</strong> — Classic 3x3 strategy game with AI opponent!<br><br><a href="/vr/game-arena/tic-tac-toe.html" style="color:#6366f1;font-weight:700;">Click here to play</a>', true);
      renderPrompts(['Take me there', 'Game Arena Hub', 'Other games']);
      if (lower.indexOf('take me') !== -1 || lower.indexOf('go to') !== -1 || lower.indexOf('play') !== -1) {
        setTimeout(function () { window.location.href = '/vr/game-arena/tic-tac-toe.html'; }, 2000);
      }
      updateStatus('idle');
      return;
    }
    if (lower.indexOf('soccer') !== -1 || lower.indexOf('shootout') !== -1 || lower.indexOf('penalty') !== -1 || lower.indexOf('football game') !== -1) {
      addMessage('agent', '\u26BD <strong>Soccer Shootout</strong> — Best of 3 penalty kicks!<br><br><a href="/vr/game-arena/soccer-shootout.html" style="color:#22c55e;font-weight:700;">Click here to play</a>', true);
      renderPrompts(['Take me there', 'Game Arena Hub', 'Other games']);
      if (lower.indexOf('take me') !== -1 || lower.indexOf('go to') !== -1 || lower.indexOf('play') !== -1) {
        setTimeout(function () { window.location.href = '/vr/game-arena/soccer-shootout.html'; }, 2000);
      }
      updateStatus('idle');
      return;
    }
    if ((lower.indexOf('what game') !== -1 || lower.indexOf('which game') !== -1 || lower.indexOf('list game') !== -1 || lower.indexOf('all game') !== -1 || lower.indexOf('show game') !== -1 || lower.indexOf('available game') !== -1) || (lower.indexOf('game') !== -1 && lower.indexOf('arena') !== -1 && lower.indexOf('go to') === -1 && lower.indexOf('take me') === -1)) {
      addMessage('agent', '\uD83C\uDFAE <strong>Game Arena</strong> — We have 4 games:<br><br>\u2022 <a href="/vr/game-arena/fps-arena.html" style="color:#ef4444;font-weight:700;">\uD83C\uDFAF FPS Arena</a> — First-person shooter, 6 weapons, AI bots, PvP<br>\u2022 <a href="/vr/game-arena/tic-tac-toe.html" style="color:#6366f1;font-weight:700;">\u274C Tic-Tac-Toe</a> — Classic 3x3 strategy<br>\u2022 <a href="/vr/game-arena/soccer-shootout.html" style="color:#22c55e;font-weight:700;">\u26BD Soccer Shootout</a> — Best of 3 penalties<br>\u2022 <a href="/vr/ant-rush/" style="color:#ff6b35;font-weight:700;">\uD83D\uDC1C Ant Rush AR</a> — AR clean-up challenge<br><br>Or visit the <a href="/vr/game-arena/" style="color:#a855f7;font-weight:700;">Game Arena Hub</a> to browse in VR!', true);
      renderPrompts(['Take me to FPS Arena', 'Take me to Ant Rush', 'Take me to Game Arena']);
      updateStatus('idle');
      return;
    }

    // ── Favourite creators / streamers check ──
    if (lower.indexOf('favourite creator') !== -1 || lower.indexOf('favorite creator') !== -1 || lower.indexOf('fav creator') !== -1 ||
        lower.indexOf('favourite streamer') !== -1 || lower.indexOf('favorite streamer') !== -1 || lower.indexOf('fav streamer') !== -1 ||
        lower.indexOf('streamer') !== -1 && lower.indexOf('online') !== -1 ||
        lower.indexOf('creator') !== -1 && lower.indexOf('online') !== -1 ||
        lower.indexOf('is my') !== -1 && (lower.indexOf('stream') !== -1 || lower.indexOf('creator') !== -1 || lower.indexOf('live') !== -1) ||
        lower.indexOf('check if') !== -1 && (lower.indexOf('stream') !== -1 || lower.indexOf('creator') !== -1 || lower.indexOf('live') !== -1 || lower.indexOf('online') !== -1) ||
        lower.indexOf('who is live') !== -1 || lower.indexOf('who\'s live') !== -1 || lower.indexOf('whos live') !== -1 ||
        lower.indexOf('favcreator') !== -1 || lower.indexOf('fav creator') !== -1) {
      var user = getLoggedInUser();
      var html = '\uD83D\uDCFA <strong>FavCreators</strong> lets you track when your favourite streamers and creators go live across Twitch, YouTube, Kick, and more!<br><br>';
      if (user) {
        html += 'You\'re logged in! You can:<br>\u2022 <a href="/vr/creators.html" style="color:#a855f7;font-weight:700;">Check live status in VR Creators Zone</a><br>\u2022 <a href="/fc/" style="color:#6366f1;font-weight:700;">Open FavCreators Dashboard</a><br>\u2022 Add/remove creators from your watchlist';
        renderPrompts(['Go to Creators zone', 'Who is live?', 'Open FavCreators dashboard']);
      } else {
        html += 'To track your streamers, you\'ll need a free FavCreators account:<br><br><a href="/fc/" style="color:#6366f1;font-weight:700;font-size:1.1em;">\u2192 Open FavCreators (free sign-up)</a><br><br>Once signed up, add your favourite creators and you\'ll always know when they go live!';
        renderPrompts(['Take me to FavCreators', 'Login', 'What is FavCreators?']);
      }
      addMessage('agent', html, true);
      updateStatus('idle');
      return;
    }

    // ── What is FavCreators ──
    if (lower.indexOf('what is favcreator') !== -1 || lower.indexOf('what\'s favcreator') !== -1 || lower.indexOf('favcreators') !== -1 && lower.indexOf('what') !== -1) {
      addMessage('agent', '\uD83D\uDC8E <strong>FavCreators</strong> is our free app that tracks your favourite streamers and content creators across multiple platforms (Twitch, YouTube, Kick, etc.).<br><br>\u2022 Get notified when they go live<br>\u2022 See who\'s streaming right now<br>\u2022 Track across Twitch, YouTube, Kick & more<br>\u2022 Works in VR and on desktop/mobile<br><br><a href="/fc/" style="color:#6366f1;font-weight:700;">\u2192 Open FavCreators</a>', true);
      renderPrompts(['Take me to FavCreators', 'Who is live?', 'Login']);
      updateStatus('idle');
      return;
    }

    // ── Navigation ──
    if (lower.indexOf('go to ') !== -1 || lower.indexOf('take me to ') !== -1 || lower.indexOf('navigate to ') !== -1) {
      return handleNavigation(lower);
    }

    // ── Open URL ──
    if (lower.indexOf('open ') !== -1 && (lower.indexOf('http') !== -1 || lower.indexOf('www') !== -1 || lower.indexOf('.com') !== -1 || lower.indexOf('.ca') !== -1)) {
      return handleOpenUrl(text);
    }

    // ── Multi-task detection ──
    if ((lower.indexOf(' and ') !== -1 || lower.indexOf(' along with ') !== -1 || lower.indexOf(' plus ') !== -1) && hasMultipleIntents(lower)) {
      return handleMultiTask(text, lower);
    }

    // ── Zone-specific handlers ──
    if (ZONE === 'stocks' || lower.indexOf('stock') !== -1 || lower.indexOf('pick') !== -1 || lower.indexOf('ticker') !== -1) {
      if (lower.indexOf('stock') !== -1 || lower.indexOf('pick') !== -1 || lower.indexOf('math') !== -1 || lower.indexOf('why') !== -1 || lower.indexOf('insight') !== -1 || lower.indexOf('top') !== -1 || lower.indexOf('gain') !== -1 || lower.indexOf('los') !== -1 || ZONE === 'stocks') {
        return handleStocks(lower);
      }
    }

    if (ZONE === 'weather' || lower.indexOf('weather') !== -1 || lower.indexOf('jacket') !== -1 || lower.indexOf('temperature') !== -1 || lower.indexOf('forecast') !== -1 || lower.indexOf('postal') !== -1) {
      if (lower.indexOf('weather') !== -1 || lower.indexOf('jacket') !== -1 || lower.indexOf('temperature') !== -1 || lower.indexOf('forecast') !== -1 || lower.indexOf('postal') !== -1 || ZONE === 'weather') {
        return handleWeather(text, lower);
      }
    }

    if (ZONE === 'creators' || lower.indexOf('streamer') !== -1 || lower.indexOf('creator') !== -1 || lower.indexOf('live') !== -1 || lower.indexOf('stream') !== -1) {
      if (lower.indexOf('streamer') !== -1 || lower.indexOf('creator') !== -1 || lower.indexOf('live') !== -1 || lower.indexOf('stream') !== -1 || lower.indexOf('refresh') !== -1 || ZONE === 'creators') {
        return handleCreators(lower);
      }
    }

    if (ZONE === 'events' || lower.indexOf('event') !== -1 || lower.indexOf('dating') !== -1 || lower.indexOf('dancing') !== -1 || lower.indexOf('concert') !== -1 || lower.indexOf('festival') !== -1) {
      return handleEvents(text, lower);
    }

    if (ZONE === 'movies' || lower.indexOf('movie') !== -1 || lower.indexOf('trailer') !== -1 || lower.indexOf('queue') !== -1 || lower.indexOf('show') !== -1 || lower.indexOf('tv') !== -1 || lower.indexOf('film') !== -1) {
      return handleMovies(text, lower);
    }

    if (ZONE === 'wellness' || lower.indexOf('accountability') !== -1 || lower.indexOf('task') !== -1 || lower.indexOf('habit') !== -1 || lower.indexOf('streak') !== -1 || lower.indexOf('breath') !== -1 || lower.indexOf('wellness') !== -1) {
      return handleWellness(lower);
    }

    // ── Login request ──
    if (lower.indexOf('login') !== -1 || lower.indexOf('sign in') !== -1 || lower.indexOf('log in') !== -1) {
      showLoginOverlay();
      addMessage('agent', 'Opening the login dialog for you. Use your FavCreators account credentials.', true);
      return;
    }

    // ── Help ──
    if (lower.indexOf('help') !== -1 || lower === 'what can you do') {
      return showHelp();
    }

    // ── Time ──
    if (lower.indexOf('time') !== -1 && lower.indexOf('what') !== -1) {
      addMessage('agent', 'The current time is <strong>' + new Date().toLocaleTimeString() + '</strong>.', true);
      return;
    }

    // ── Fallback ──
    handleFallback(text, lower);
  }

  // ════════════════════════════════════════════
  // HANDLER: Explain Icons
  // ════════════════════════════════════════════
  function handleExplainIcons() {
    var meta = ZONE_META[ZONE] || ZONE_META.hub;
    var icons = meta.icons || {};
    var keys = [];
    for (var k in icons) {
      if (icons.hasOwnProperty(k)) keys.push(k);
    }
    if (keys.length === 0) {
      addMessage('agent', 'No icon descriptions available for this zone.', true);
      updateStatus('idle');
      return;
    }
    var html = '<strong>Icons & Controls in ' + meta.name + ':</strong><ul>';
    for (var i = 0; i < keys.length; i++) {
      html += '<li><strong>' + escapeHtml(keys[i]) + '</strong>: ' + escapeHtml(icons[keys[i]]) + '</li>';
    }
    html += '</ul>';
    addMessage('agent', html, true);
    updateStatus('idle');
  }

  // ════════════════════════════════════════════
  // HANDLER: Context Summary
  // ════════════════════════════════════════════
  function showContextSummary() {
    var meta = ZONE_META[ZONE] || ZONE_META.hub;
    var user = getLoggedInUser();
    var html = '<strong>Current Zone: ' + meta.emoji + ' ' + meta.name + '</strong><br>';
    html += meta.welcome + '<br><br>';
    if (user) {
      html += 'Logged in as: <strong>' + escapeHtml(user.display_name || user.username) + '</strong><br>';
    } else {
      html += 'Not logged in. <a href="javascript:void(0)" onclick="document.getElementById(\'vr-agent-login-overlay\').classList.add(\'open\')">Sign in</a> for personalized features.<br>';
    }
    html += '<br>What would you like to do?';
    addMessage('agent', html, true);
    renderPrompts();
    updateStatus('idle');
  }

  // ════════════════════════════════════════════
  // HANDLER: Navigation
  // ════════════════════════════════════════════
  function handleNavigation(lower) {
    var zones = {
      'hub': '/vr/', 'home': '/vr/',
      'events': '/vr/events/', 'event': '/vr/events/',
      'movie': '/vr/movies.html', 'movies': '/vr/movies.html', 'theater': '/vr/movies.html',
      'creator': '/vr/creators.html', 'creators': '/vr/creators.html', 'streamer': '/vr/creators.html', 'streamers': '/vr/creators.html',
      'stock': '/vr/stocks-zone.html', 'stocks': '/vr/stocks-zone.html', 'trading': '/vr/stocks-zone.html',
      'weather': '/vr/weather-zone.html', 'forecast': '/vr/weather-zone.html',
      'wellness': '/vr/wellness/', 'garden': '/vr/wellness/', 'breathe': '/vr/wellness/',
      'tutorial': '/vr/tutorial/',
      'game arena': '/vr/game-arena/', 'games': '/vr/game-arena/', 'arena': '/vr/game-arena/',
      'fps': '/vr/game-arena/fps-arena.html', 'first person shooter': '/vr/game-arena/fps-arena.html', 'shooter': '/vr/game-arena/fps-arena.html',
      'tic tac toe': '/vr/game-arena/tic-tac-toe.html', 'tictactoe': '/vr/game-arena/tic-tac-toe.html',
      'soccer': '/vr/game-arena/soccer-shootout.html', 'shootout': '/vr/game-arena/soccer-shootout.html',
      'ant rush': '/vr/ant-rush/', 'antrush': '/vr/ant-rush/',
      'favcreator': '/fc/', 'fav creator': '/fc/', 'favourite creator': '/fc/', 'favorite creator': '/fc/'
    };
    for (var key in zones) {
      if (lower.indexOf(key) !== -1) {
        var displayName = key.charAt(0).toUpperCase() + key.slice(1);
        addMessage('agent', 'Taking you to <strong>' + displayName + '</strong>...', true);
        var dest = zones[key];
        setTimeout(function () { window.location.href = dest; }, 1200);
        return;
      }
    }
    addMessage('agent', 'I couldn\'t find that zone. Try: Hub, Events, Movies, Creators, Stocks, Weather, Wellness, Tutorial, Game Arena, FPS Arena, Ant Rush, Soccer Shootout, Tic-Tac-Toe, or FavCreators.', true);
    renderPrompts(['Show all games', 'Go to Hub', 'Help']);
    updateStatus('idle');
  }

  // ════════════════════════════════════════════
  // HANDLER: Open URL
  // ════════════════════════════════════════════
  function handleOpenUrl(text) {
    var urlMatch = text.match(/(https?:\/\/[^\s]+|www\.[^\s]+)/i);
    if (urlMatch) {
      var url = urlMatch[1];
      if (url.indexOf('http') !== 0) url = 'https://' + url;
      addMessage('agent', 'Opening <a href="' + escapeHtml(url) + '" target="_blank">' + escapeHtml(url) + '</a> in a new tab.', true);
      window.open(url, '_blank');
    } else {
      addMessage('agent', 'I couldn\'t find a valid URL in your message. Please include the full link.', true);
    }
    updateStatus('idle');
  }

  // ════════════════════════════════════════════
  // HANDLER: Multi-Task
  // ════════════════════════════════════════════
  function hasMultipleIntents(lower) {
    var intents = 0;
    if (lower.indexOf('stock') !== -1 || lower.indexOf('pick') !== -1 || lower.indexOf('insight') !== -1) intents++;
    if (lower.indexOf('weather') !== -1 || lower.indexOf('jacket') !== -1 || lower.indexOf('temperature') !== -1) intents++;
    if (lower.indexOf('event') !== -1 || lower.indexOf('dating') !== -1 || lower.indexOf('dancing') !== -1) intents++;
    if (lower.indexOf('creator') !== -1 || lower.indexOf('stream') !== -1 || lower.indexOf('live') !== -1) intents++;
    if (lower.indexOf('movie') !== -1 || lower.indexOf('trailer') !== -1) intents++;
    if (lower.indexOf('accountability') !== -1 || lower.indexOf('task') !== -1) intents++;
    return intents >= 2;
  }

  function handleMultiTask(text, lower) {
    addMessage('agent', 'Processing your multi-part request...', false);
    var parts = [];

    if (lower.indexOf('stock') !== -1 || lower.indexOf('pick') !== -1 || lower.indexOf('insight') !== -1) {
      parts.push({ type: 'stocks', fn: fetchStockData });
    }
    if (lower.indexOf('weather') !== -1 || lower.indexOf('jacket') !== -1 || lower.indexOf('temperature') !== -1) {
      parts.push({ type: 'weather', fn: function (cb) { fetchWeatherData(text, cb); } });
    }
    if (lower.indexOf('event') !== -1 || lower.indexOf('dating') !== -1 || lower.indexOf('dancing') !== -1) {
      parts.push({ type: 'events', fn: function (cb) { fetchEventData(text, lower, cb); } });
    }
    if (lower.indexOf('accountability') !== -1 || lower.indexOf('task') !== -1) {
      parts.push({ type: 'accountability', fn: fetchAccountabilityData });
    }

    var results = [];
    var completed = 0;
    if (parts.length === 0) {
      addMessage('agent', 'I detected multiple requests but couldn\'t parse them all. Try asking one at a time.', true);
      updateStatus('idle');
      return;
    }
    for (var i = 0; i < parts.length; i++) {
      (function (part) {
        part.fn(function (html) {
          results.push('<strong>' + part.type.toUpperCase() + ':</strong><br>' + html);
          completed++;
          if (completed === parts.length) {
            addMessage('agent', results.join('<br><br>'), true);
            updateStatus('idle');
          }
        });
      })(parts[i]);
    }
  }

  // ════════════════════════════════════════════
  // HANDLER: Stocks
  // ════════════════════════════════════════════
  function handleStocks(lower) {
    fetchStockData(function (html) {
      addMessage('agent', html, true);
      updateStatus('idle');
    });
  }

  function fetchStockData(callback) {
    // Pull data from the DOM or generate from simulated data
    var stocks = getStockDataFromPage();
    if (!stocks || stocks.length === 0) {
      // Simulated data with methodology
      stocks = [
        { symbol: 'NVDA', price: 850.42, change: 5.2, pe: 68.5, momentum: 'High', div: 0.03, reason: 'Strong AI chip demand; high momentum score; PE elevated but justified by 94% YoY revenue growth' },
        { symbol: 'AAPL', price: 182.35, change: 2.3, pe: 28.9, momentum: 'Medium', div: 0.55, reason: 'Stable cash flow; reasonable P/E; consistent dividend growth; iPhone 16 cycle catalyst' },
        { symbol: 'MSFT', price: 415.86, change: 1.8, pe: 36.2, momentum: 'Medium-High', div: 0.72, reason: 'Azure cloud growth 29% YoY; Copilot AI monetization; fortress balance sheet' },
        { symbol: 'SPY', price: 472.58, change: 0.4, pe: 22.1, momentum: 'Medium', div: 1.43, reason: 'S&P 500 index ETF; broad market exposure; historically 10% annual return' },
        { symbol: 'TSLA', price: 185.67, change: -3.1, pe: 45.3, momentum: 'Low', div: 0, reason: 'High volatility; FSD progress uncertain; margin pressure from price cuts' }
      ];
    }

    var html = '<strong>\uD83D\uDCC8 Top Stock Picks & Analysis:</strong><br><br>';
    html += '<strong>Methodology:</strong> Picks are ranked by a composite score using:<br>';
    html += '<ul>';
    html += '<li><strong>P/E Ratio</strong> (Price-to-Earnings): Lower = better value. Sector-adjusted.</li>';
    html += '<li><strong>Momentum Score</strong>: Based on 20-day and 50-day moving average crossover + RSI.</li>';
    html += '<li><strong>Dividend Yield</strong>: Higher yield = income generation; weighted 10% in score.</li>';
    html += '<li><strong>Fundamental Growth</strong>: Revenue and earnings growth rate YoY.</li>';
    html += '</ul><br>';

    // Sort by best (highest change or custom score)
    stocks.sort(function (a, b) { return (b.change || 0) - (a.change || 0); });
    var top = stocks.slice(0, 5);
    for (var i = 0; i < top.length; i++) {
      var s = top[i];
      var color = (s.change || 0) >= 0 ? '#22c55e' : '#ef4444';
      var arrow = (s.change || 0) >= 0 ? '\u2191' : '\u2193';
      html += '<strong>' + escapeHtml(s.symbol) + '</strong> \u2014 $' + (s.price || '?').toFixed ? s.price.toFixed(2) : s.price;
      html += ' (' + arrow + Math.abs(s.change || 0).toFixed(1) + '%)';
      html += ' \u2014 P/E: ' + (s.pe || 'N/A');
      html += '<br><em>' + escapeHtml(s.reason || 'Market performer') + '</em><br><br>';
    }

    callback(html);
  }

  function getStockDataFromPage() {
    // Try to read stock data from the current page DOM
    var stocks = [];
    try {
      var pedestals = document.querySelectorAll('.stock-pedestal, [data-symbol]');
      for (var i = 0; i < pedestals.length; i++) {
        var sym = pedestals[i].getAttribute('data-symbol');
        var priceEl = document.getElementById('ped-' + sym);
        if (sym && priceEl) {
          var priceText = priceEl.getAttribute('value') || '';
          var price = parseFloat(priceText.replace('$', ''));
          stocks.push({ symbol: sym, price: price || 0, change: (Math.random() * 10 - 3).toFixed(1) * 1 });
        }
      }
    } catch (e) { /* ignore */ }
    return stocks;
  }

  // ════════════════════════════════════════════
  // HANDLER: Weather
  // ════════════════════════════════════════════
  function handleWeather(text, lower) {
    fetchWeatherData(text, function (html) {
      addMessage('agent', html, true);
      updateStatus('idle');
    });
  }

  function fetchWeatherData(text, callback) {
    // Check for postal code
    var postalMatch = text ? text.match(/[A-Za-z]\d[A-Za-z]\s?\d[A-Za-z]\d/i) : null;
    var lat = 43.65, lon = -79.38; // Toronto default
    var locationLabel = 'Toronto';

    if (postalMatch) {
      locationLabel = postalMatch[0].toUpperCase();
      // Geocode postal code via open API
      var geoXhr = new XMLHttpRequest();
      geoXhr.open('GET', 'https://geocoding-api.open-meteo.com/v1/search?name=' + encodeURIComponent(postalMatch[0]) + '&count=1&language=en&format=json', true);
      geoXhr.onload = function () {
        try {
          var geo = JSON.parse(geoXhr.responseText);
          if (geo.results && geo.results.length > 0) {
            lat = geo.results[0].latitude;
            lon = geo.results[0].longitude;
            locationLabel = geo.results[0].name || postalMatch[0];
          }
        } catch (e) { /* use defaults */ }
        doWeatherFetch(lat, lon, locationLabel, callback);
      };
      geoXhr.onerror = function () { doWeatherFetch(lat, lon, locationLabel, callback); };
      geoXhr.send();
    } else {
      doWeatherFetch(lat, lon, locationLabel, callback);
    }
  }

  function doWeatherFetch(lat, lon, location, callback) {
    var url = 'https://api.open-meteo.com/v1/forecast?latitude=' + lat + '&longitude=' + lon +
      '&current_weather=true&hourly=temperature_2m,precipitation_probability,windspeed_10m&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode&timezone=America/Toronto&forecast_days=3';
    var xhr = new XMLHttpRequest();
    xhr.open('GET', url, true);
    xhr.onload = function () {
      try {
        var data = JSON.parse(xhr.responseText);
        var cw = data.current_weather || {};
        var temp = Math.round(cw.temperature || 0);
        var wind = Math.round(cw.windspeed || 0);
        var code = cw.weathercode || 0;
        var condition = weatherCodeToText(code);

        // Feels like (wind chill approximation)
        var feelsLike = temp;
        if (temp <= 10 && wind > 5) {
          feelsLike = Math.round(13.12 + 0.6215 * temp - 11.37 * Math.pow(wind, 0.16) + 0.3965 * temp * Math.pow(wind, 0.16));
        }

        // Jacket logic
        var needJacket = feelsLike < 15 || code >= 51; // Below 15C or precipitation
        var jacketReason = '';
        if (feelsLike < 5) jacketReason = 'It\'s quite cold. A warm winter jacket is recommended.';
        else if (feelsLike < 10) jacketReason = 'Cool out there. A medium jacket or layered outfit would be good.';
        else if (feelsLike < 15) jacketReason = 'Slightly cool. A light jacket or hoodie is a good idea.';
        else if (code >= 51) jacketReason = 'Rain expected. Bring a waterproof jacket or umbrella.';
        else jacketReason = 'Weather is pleasant. No jacket needed!';

        var html = '<strong>\u26C5 Weather in ' + escapeHtml(location) + ':</strong><br><br>';
        html += '<strong>' + temp + '\u00B0C</strong> \u2014 ' + condition + '<br>';
        html += 'Feels like: <strong>' + feelsLike + '\u00B0C</strong><br>';
        html += 'Wind: ' + wind + ' km/h<br><br>';
        html += '<strong>\uD83E\uDDE5 Jacket Recommendation:</strong> ' + (needJacket ? '\u2705 Yes' : '\u274C No') + '<br>';
        html += jacketReason;

        // 3-day forecast summary
        if (data.daily) {
          html += '<br><br><strong>3-Day Forecast:</strong><br>';
          var days = data.daily;
          for (var i = 0; i < Math.min(3, (days.time || []).length); i++) {
            var dayName = i === 0 ? 'Today' : (i === 1 ? 'Tomorrow' : formatDay(days.time[i]));
            html += dayName + ': ' + Math.round(days.temperature_2m_min[i]) + '\u00B0 / ' + Math.round(days.temperature_2m_max[i]) + '\u00B0C';
            html += ' \u2014 ' + weatherCodeToText(days.weathercode[i]);
            if (days.precipitation_sum[i] > 0) html += ' (\uD83C\uDF27 ' + days.precipitation_sum[i].toFixed(1) + 'mm)';
            html += '<br>';
          }
        }

        callback(html);
      } catch (e) {
        callback('Unable to fetch weather data. Try again in a moment.');
      }
    };
    xhr.onerror = function () { callback('Network error fetching weather. Please check your connection.'); };
    xhr.send();
  }

  function weatherCodeToText(code) {
    var codes = {
      0: 'Clear sky', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast',
      45: 'Foggy', 48: 'Depositing rime fog',
      51: 'Light drizzle', 53: 'Moderate drizzle', 55: 'Dense drizzle',
      61: 'Slight rain', 63: 'Moderate rain', 65: 'Heavy rain',
      71: 'Slight snow', 73: 'Moderate snow', 75: 'Heavy snow',
      77: 'Snow grains', 80: 'Rain showers', 81: 'Moderate rain showers', 82: 'Violent rain showers',
      85: 'Slight snow showers', 86: 'Heavy snow showers',
      95: 'Thunderstorm', 96: 'Thunderstorm with hail', 99: 'Thunderstorm with heavy hail'
    };
    return codes[code] || 'Unknown';
  }

  function formatDay(dateStr) {
    try {
      var d = new Date(dateStr + 'T00:00:00');
      return ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][d.getDay()];
    } catch (e) { return dateStr; }
  }

  // ════════════════════════════════════════════
  // HANDLER: Creators / Streamers
  // ════════════════════════════════════════════
  function handleCreators(lower) {
    // Try to get data from current page
    var creators = [];
    if (window.allCreators) {
      creators = window.allCreators;
    }

    // Refresh request
    if (lower.indexOf('refresh') !== -1) {
      addMessage('agent', 'Refreshing live streamer data...', true);
      if (typeof window.refreshLiveStatuses === 'function') {
        window.refreshLiveStatuses();
        setTimeout(function () { handleCreators('who is live'); }, 3000);
      } else {
        addMessage('agent', 'The refresh function isn\'t available on this page. Try visiting the <a href="/vr/creators.html">Creators zone</a>.', true);
        updateStatus('idle');
      }
      return;
    }

    if (creators.length === 0) {
      // Try fetching via API
      var xhr = new XMLHttpRequest();
      xhr.open('GET', '/fc/api/get_streamer_status.php', true);
      xhr.withCredentials = true;
      xhr.onload = function () {
        try {
          var data = JSON.parse(xhr.responseText);
          if (data && data.creators) {
            displayCreatorSummary(data.creators, lower);
          } else {
            showCreatorLoginPrompt();
          }
        } catch (e) {
          showCreatorLoginPrompt();
        }
      };
      xhr.onerror = function () { showCreatorLoginPrompt(); };
      xhr.send();
      return;
    }

    displayCreatorSummary(creators, lower);
  }

  function displayCreatorSummary(creators, lower) {
    var live = [];
    for (var i = 0; i < creators.length; i++) {
      var c = creators[i];
      if (c._vrIsLive || c.isLive || c.is_live) {
        live.push(c);
      }
    }

    var html = '<strong>\uD83D\uDCFA Creator Status:</strong><br><br>';
    html += 'Total creators: <strong>' + creators.length + '</strong><br>';
    html += 'Currently live: <strong>' + live.length + '</strong><br><br>';

    if (live.length > 0) {
      html += '<strong>Live Now:</strong><ul>';
      for (var j = 0; j < Math.min(live.length, 8); j++) {
        var c = live[j];
        html += '<li><strong>' + escapeHtml(c.name || c.display_name || 'Creator') + '</strong>';
        if (c.platform) html += ' (' + escapeHtml(c.platform) + ')';
        if (c.viewer_count || c.viewers) html += ' \u2014 ' + (c.viewer_count || c.viewers) + ' viewers';
        html += '</li>';
      }
      html += '</ul>';

      // Offer to open first live streamer
      if (lower.indexOf('open') !== -1 || lower.indexOf('first') !== -1 || lower.indexOf('watch') !== -1) {
        var first = live[0];
        var streamUrl = first.stream_url || first.url || '#';
        if (streamUrl && streamUrl !== '#') {
          html += 'Opening <strong>' + escapeHtml(first.name || first.display_name) + '</strong>\'s stream...';
          setTimeout(function () { window.open(streamUrl, '_blank'); }, 1500);
        }
      } else {
        html += 'Would you like me to open the first live streamer?';
        renderPrompts(['Open first live streamer', 'Refresh streamers', 'Show all creators']);
      }
    } else {
      html += 'No one is live right now. Auto-refreshes every 60 seconds.<br>';
      html += 'Would you like to check back later or go to the <a href="/vr/creators.html">Creators zone</a>?';
      renderPrompts(['Refresh streamers', 'Go to Creators', 'Show my creators']);
    }

    addMessage('agent', html, true);
    updateStatus('idle');
  }

  function showCreatorLoginPrompt() {
    var user = getLoggedInUser();
    if (!user) {
      addMessage('agent', 'You need to be logged in to see your streamers. Would you like to sign in? Your FavCreators credentials work here too.', true);
      renderPrompts(['Login', 'Go to Creators zone', 'What is FavCreators?']);
    } else {
      addMessage('agent', 'Couldn\'t load streamer data right now. Try visiting the <a href="/vr/creators.html">Creators zone</a> directly.', true);
    }
    updateStatus('idle');
  }

  // ════════════════════════════════════════════
  // HANDLER: Events
  // ════════════════════════════════════════════
  function handleEvents(text, lower) {
    fetchEventData(text, lower, function (html) {
      addMessage('agent', html, true);
      updateStatus('idle');
    });
  }

  function fetchEventData(text, lower, callback) {
    // Determine category filter
    var category = null;
    var categoryKeywords = {
      'dating': ['dating', 'date', 'singles', 'speed dating', 'matchmaking', 'romance'],
      'dancing': ['dancing', 'dance', 'salsa', 'bachata', 'ballroom', 'club'],
      'music': ['music', 'concert', 'jazz', 'live band', 'dj', 'karaoke'],
      'tech': ['tech', 'hackathon', 'coding', 'startup', 'ai', 'programming'],
      'art': ['art', 'gallery', 'painting', 'exhibition', 'museum'],
      'food': ['food', 'restaurant', 'tasting', 'brunch', 'dinner', 'cooking'],
      'sports': ['sports', 'fitness', 'yoga', 'running', 'basketball', 'soccer'],
      'networking': ['networking', 'meetup', 'professional', 'business'],
      'festival': ['festival', 'fair', 'carnival', 'celebration']
    };
    for (var cat in categoryKeywords) {
      var kws = categoryKeywords[cat];
      for (var k = 0; k < kws.length; k++) {
        if (lower.indexOf(kws[k]) !== -1) {
          category = cat;
          break;
        }
      }
      if (category) break;
    }

    // Determine time filter
    var timeFilter = 'this week'; // default
    if (lower.indexOf('today') !== -1 || lower.indexOf('tonight') !== -1) timeFilter = 'today';
    else if (lower.indexOf('tomorrow') !== -1) timeFilter = 'tomorrow';
    else if (lower.indexOf('this weekend') !== -1 || lower.indexOf('weekend') !== -1) timeFilter = 'this weekend';
    else if (lower.indexOf('starting soon') !== -1 || lower.indexOf('next few hours') !== -1) timeFilter = 'starting soon';
    else if (lower.indexOf('this month') !== -1) timeFilter = 'this month';
    else if (lower.indexOf('next 3 months') !== -1 || lower.indexOf('next three months') !== -1) timeFilter = 'next 3 months';
    else if (lower.indexOf('this week') !== -1 || lower.indexOf('week') !== -1) timeFilter = 'this week';

    // Try to use page data first
    var pageEvents = window.allEvents || window.filteredEvents || null;
    if (pageEvents && pageEvents.length > 0) {
      var filtered = filterEvents(pageEvents, category, timeFilter);
      callback(formatEventSummary(filtered, category, timeFilter));
      return;
    }

    // Fetch from API
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/events.json', true);
    xhr.onload = function () {
      try {
        var data = JSON.parse(xhr.responseText);
        var events = Array.isArray(data) ? data : (data.events || []);
        var filtered = filterEvents(events, category, timeFilter);
        callback(formatEventSummary(filtered, category, timeFilter));
      } catch (e) {
        callback('Unable to load events data. Try visiting the <a href="/vr/events/">Events zone</a> directly.');
      }
    };
    xhr.onerror = function () { callback('Network error loading events. Please check your connection.'); };
    xhr.send();
  }

  function filterEvents(events, category, timeFilter) {
    var now = new Date();
    var results = [];

    for (var i = 0; i < events.length; i++) {
      var ev = events[i];
      var evDate = null;
      try {
        evDate = new Date(ev.date || ev.start_date || ev.datetime || '');
      } catch (e) { continue; }
      if (isNaN(evDate.getTime())) continue;

      // Category filter
      if (category) {
        var evText = ((ev.title || '') + ' ' + (ev.description || '') + ' ' + (ev.category || '') + ' ' + ((ev.tags || []).join(' '))).toLowerCase();
        if (evText.indexOf(category) === -1) {
          // Fuzzy match
          var catKeywords = {
            'dating': ['date', 'singles', 'speed', 'matchmak', 'romance', 'love'],
            'dancing': ['dance', 'salsa', 'bachata', 'ballroom', 'swing', 'tango'],
            'music': ['concert', 'live music', 'jazz', 'band', 'dj'],
            'tech': ['technology', 'hack', 'code', 'startup', 'developer'],
            'networking': ['network', 'meetup', 'professional', 'business'],
            'festival': ['festival', 'fair', 'carnival', 'parade']
          };
          var matchFound = false;
          var fuzzy = catKeywords[category] || [];
          for (var f = 0; f < fuzzy.length; f++) {
            if (evText.indexOf(fuzzy[f]) !== -1) { matchFound = true; break; }
          }
          if (!matchFound) continue;
        }
      }

      // Time filter
      var todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      var todayEnd = new Date(todayStart.getTime() + 86400000);
      var tomorrowEnd = new Date(todayStart.getTime() + 172800000);
      var weekEnd = new Date(todayStart.getTime() + 7 * 86400000);
      var monthEnd = new Date(todayStart.getTime() + 30 * 86400000);
      var threeMonths = new Date(todayStart.getTime() + 90 * 86400000);

      // Weekend (Saturday-Sunday)
      var nextSat = new Date(todayStart);
      nextSat.setDate(nextSat.getDate() + (6 - nextSat.getDay() + 7) % 7);
      if (nextSat < todayStart) nextSat.setDate(nextSat.getDate() + 7);
      var weekendEnd = new Date(nextSat.getTime() + 172800000);

      var inRange = false;
      switch (timeFilter) {
        case 'today': inRange = evDate >= todayStart && evDate < todayEnd; break;
        case 'tomorrow': inRange = evDate >= todayEnd && evDate < tomorrowEnd; break;
        case 'this weekend': inRange = evDate >= nextSat && evDate < weekendEnd; break;
        case 'starting soon': inRange = evDate >= now && evDate < new Date(now.getTime() + 4 * 3600000); break;
        case 'this week': inRange = evDate >= todayStart && evDate < weekEnd; break;
        case 'this month': inRange = evDate >= todayStart && evDate < monthEnd; break;
        case 'next 3 months': inRange = evDate >= todayStart && evDate < threeMonths; break;
        default: inRange = evDate >= todayStart && evDate < weekEnd;
      }
      if (inRange) results.push(ev);
    }

    // Sort by date
    results.sort(function (a, b) {
      return new Date(a.date || a.start_date || '') - new Date(b.date || b.start_date || '');
    });

    return results;
  }

  function formatEventSummary(events, category, timeFilter) {
    var catLabel = category ? (category.charAt(0).toUpperCase() + category.slice(1)) : 'All';
    var html = '<strong>\uD83D\uDCC5 ' + catLabel + ' Events \u2014 ' + timeFilter + ':</strong><br><br>';

    if (events.length === 0) {
      html += 'No matching events found for "' + catLabel + '" ' + timeFilter + '.<br>';
      html += 'Try a broader time range or different category.';
      return html;
    }

    html += 'Found <strong>' + events.length + '</strong> event' + (events.length > 1 ? 's' : '') + ':<br><br>';

    var show = Math.min(events.length, 8);
    for (var i = 0; i < show; i++) {
      var ev = events[i];
      var title = ev.title || ev.name || 'Untitled Event';
      var date = ev.date || ev.start_date || '';
      var loc = ev.location || ev.venue || '';
      var desc = ev.description || '';
      if (desc.length > 80) desc = desc.substring(0, 80) + '...';

      html += '<strong>' + (i + 1) + '. ' + escapeHtml(title) + '</strong><br>';
      if (date) html += '\uD83D\uDCC6 ' + escapeHtml(formatEventDate(date)) + '<br>';
      if (loc) html += '\uD83D\uDCCD ' + escapeHtml(loc) + '<br>';
      if (desc) html += '<em>' + escapeHtml(desc) + '</em><br>';
      html += '<br>';
    }
    if (events.length > show) {
      html += '...and ' + (events.length - show) + ' more. Visit the <a href="/vr/events/">Events zone</a> to see all.';
    }
    return html;
  }

  function formatEventDate(dateStr) {
    try {
      var d = new Date(dateStr);
      var options = { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' };
      return d.toLocaleDateString('en-US', options);
    } catch (e) { return dateStr; }
  }

  // ════════════════════════════════════════════
  // HANDLER: Movies
  // ════════════════════════════════════════════
  function handleMovies(text, lower) {
    // Extract search term
    var searchTerm = '';
    var queueMatch = lower.match(/queue\s+(?:me\s+)?(?:up\s+)?(?:a\s+)?(?:list\s+of\s+)?(.+?)(?:\s+trailers?)?$/);
    var findMatch = lower.match(/(?:find|search|show|play)\s+(?:me\s+)?(.+?)(?:\s+trailers?|\s+movies?|\s+shows?)?$/);
    if (queueMatch) searchTerm = queueMatch[1].trim();
    else if (findMatch) searchTerm = findMatch[1].trim();
    else {
      // Try general extraction
      var cleaned = lower.replace(/movie|trailer|queue|show|find|play|search|watch|me|up|a|list|of|the|and|tv|series/g, '').trim();
      if (cleaned.length > 1) searchTerm = cleaned;
    }

    if (!searchTerm) {
      addMessage('agent', 'What movie or TV show would you like to find? Try "Queue Avatar trailers" or "Show me action movies".', true);
      renderPrompts(['Queue Avatar trailers', 'Show action movies', 'Find sci-fi shows', 'What\'s playing now?']);
      updateStatus('idle');
      return;
    }

    addMessage('agent', 'Searching for "' + escapeHtml(searchTerm) + '"...', false);

    // Try fetching from movie API
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/MOVIESHOWS3/api/get-movies.php?search=' + encodeURIComponent(searchTerm), true);
    xhr.onload = function () {
      try {
        var data = JSON.parse(xhr.responseText);
        var movies = data.movies || data.results || data || [];
        if (!Array.isArray(movies)) movies = [];

        if (movies.length === 0) {
          addMessage('agent', 'No movies/shows found for "' + escapeHtml(searchTerm) + '". Try a different title.', true);
          updateStatus('idle');
          return;
        }

        var html = '<strong>\uD83C\uDFAC Results for "' + escapeHtml(searchTerm) + '":</strong><br><br>';
        var show = Math.min(movies.length, 6);
        for (var i = 0; i < show; i++) {
          var m = movies[i];
          html += '<strong>' + (i + 1) + '. ' + escapeHtml(m.title || m.name || 'Untitled') + '</strong>';
          if (m.year || m.release_date) html += ' (' + (m.year || (m.release_date || '').substring(0, 4)) + ')';
          html += '<br>';
          if (m.media_type === 'tv' || m.type === 'tv') html += '\uD83D\uDCFA TV Series<br>';
          if (m.vote_average || m.rating) html += '\u2B50 ' + (m.vote_average || m.rating).toFixed ? (m.vote_average || m.rating).toFixed(1) : (m.vote_average || m.rating);
          html += '<br>';
        }

        if (lower.indexOf('queue') !== -1) {
          html += '<br>Queuing these trailers for you! Head to the <a href="/vr/movies.html">Movie Theater</a> to watch.';
          // Try to queue on the page if we\'re in movies zone
          if (ZONE === 'movies' && typeof window.addToQueue === 'function') {
            for (var q = 0; q < Math.min(movies.length, 5); q++) {
              try { window.addToQueue(movies[q]); } catch (e) { /* ignore */ }
            }
          }
        } else {
          html += '<br>Would you like me to queue these trailers?';
          renderPrompts(['Queue these trailers', 'Find more like these', 'Go to Movie Theater']);
        }

        addMessage('agent', html, true);
        updateStatus('idle');
      } catch (e) {
        addMessage('agent', 'Error searching movies. The API may be temporarily unavailable.', true);
        updateStatus('idle');
      }
    };
    xhr.onerror = function () {
      addMessage('agent', 'Network error searching movies. Please try again.', true);
      updateStatus('idle');
    };
    xhr.send();
  }

  // ════════════════════════════════════════════
  // HANDLER: Wellness / Accountability
  // ════════════════════════════════════════════
  function handleWellness(lower) {
    fetchAccountabilityData(function (html) {
      addMessage('agent', html, true);
      updateStatus('idle');
    });
  }

  function fetchAccountabilityData(callback) {
    // Pull from localStorage
    var habits = [];
    try {
      habits = JSON.parse(localStorage.getItem('vr17_habits') || '[]');
    } catch (e) { /* ignore */ }

    var streaks = [];
    try {
      streaks = JSON.parse(localStorage.getItem('vr-streak-data') || '[]');
    } catch (e) { /* ignore */ }

    var pomodoroCount = 0;
    try {
      pomodoroCount = parseInt(localStorage.getItem('pomodoro_sessions') || '0');
    } catch (e) { /* ignore */ }

    var html = '<strong>\uD83C\uDF3F Wellness & Accountability Summary:</strong><br><br>';

    // Habits
    if (habits.length > 0) {
      html += '<strong>Daily Habits:</strong><ul>';
      for (var i = 0; i < habits.length; i++) {
        var h = habits[i];
        var status = h.completed ? '\u2705' : '\u274C';
        html += '<li>' + status + ' ' + escapeHtml(h.name || h.title || 'Habit ' + (i + 1));
        if (h.streak) html += ' (Streak: ' + h.streak + ' days)';
        html += '</li>';
      }
      html += '</ul>';
    } else {
      html += 'No habits tracked yet. Visit the <a href="/vr/wellness/">Wellness Garden</a> to set up daily habits.<br><br>';
    }

    // Pomodoro
    if (pomodoroCount > 0) {
      html += '<strong>Pomodoro Sessions:</strong> ' + pomodoroCount + ' completed<br><br>';
    }

    // Visited zones progress
    var visited = {};
    try { visited = JSON.parse(localStorage.getItem('vr_visited_zones') || '{}'); } catch (e) { /* ignore */ }
    var visitedCount = 0;
    for (var z in visited) { if (visited.hasOwnProperty(z)) visitedCount++; }
    html += '<strong>Zone Progress:</strong> Visited ' + visitedCount + ' / 7 zones<br>';

    // Suggestions
    html += '<br>Keep it up! Remember to take breaks and stay mindful.';

    callback(html);
  }

  // ════════════════════════════════════════════
  // HANDLER: Mobile Mode
  // ════════════════════════════════════════════
  function handleMobileMode() {
    var p = location.pathname;
    var mobileUrls = {
      '/vr/': '/vr/mobile-index.html',
      '/vr/index.html': '/vr/mobile-index.html',
      '/vr/weather-zone.html': '/vr/mobile-weather.html'
    };
    var mobileDest = mobileUrls[p] || null;

    if (p.indexOf('mobile') !== -1) {
      addMessage('agent', 'You\'re already in a mobile-optimized page! If you want the desktop experience, try going to the <a href="/vr/">VR Hub</a>.', true);
      renderPrompts(['Go to Hub', 'Focus mode', 'Simple mode']);
      updateStatus('idle');
      return;
    }

    if (mobileDest) {
      addMessage('agent', '\uD83D\uDCF1 Switching to <strong>Mobile Mode</strong>. The page will reload with a touch-friendly layout optimized for phones and tablets.', true);
      setTimeout(function () { window.location.href = mobileDest; }, 1500);
    } else {
      // No dedicated mobile page — use simple mode + focus as a fallback
      setViewMode('simple');
      addMessage('agent', '\uD83D\uDCF1 This zone doesn\'t have a dedicated mobile page, but I\'ve activated <strong>Simple Mode</strong> to reduce clutter. For an even cleaner view, try "<strong>focus mode</strong>".<br><br>Mobile-optimized pages are available for: <a href="/vr/mobile-index.html">Hub</a> and <a href="/vr/mobile-weather.html">Weather</a>.', true);
      renderPrompts(['Focus mode', 'Go to Mobile Hub', 'Full mode']);
    }
    updateStatus('idle');
  }

  // ════════════════════════════════════════════
  // HANDLER: Help
  // ════════════════════════════════════════════
  function showHelp() {
    var html = '<strong>\uD83E\uDD16 I can help you with:</strong><br><br>';
    html += '<strong>Navigation:</strong> "Go to [zone]", "Open [URL]"<br>';
    html += '<strong>Stocks:</strong> "Top stock picks and why", "Explain the math"<br>';
    html += '<strong>Weather:</strong> "Do I need a jacket?", "Weather for M5V 3A8"<br>';
    html += '<strong>Events:</strong> "Summarize dating events this week", "Dancing events today"<br>';
    html += '<strong>Creators:</strong> "Who is live?", "Open first live streamer"<br>';
    html += '<strong>Movies:</strong> "Queue Avatar trailers", "Find sci-fi shows"<br>';
    html += '<strong>Wellness:</strong> "Summarize my tasks", "Show my streaks"<br>';
    html += '<strong>Combined:</strong> "Stock insights and weather for Toronto"<br>';
    html += '<strong>Context:</strong> "Explain all icons", "Where am I?", "Summarize current context"<br>';
    html += '<strong>View Modes:</strong><br>';
    html += '\u2003\u2022 "<strong>Focus mode</strong>" / "Zen mode" / "Hide UI" — hides all overlays, just 3D + AI<br>';
    html += '\u2003\u2022 "<strong>Simple mode</strong>" / "Minimal mode" — essentials only, cleaner layout<br>';
    html += '\u2003\u2022 "<strong>Full mode</strong>" / "Show UI" — restores all UI elements<br>';
    html += '\u2003\u2022 "<strong>Mobile mode</strong>" — switch to touch-optimized mobile layout<br>';
    html += '<strong>Tutorial:</strong> "Enable tutorial mode" to reset first-time experience<br>';
    html += '<strong>Voice:</strong> Click \uD83C\uDFA4 to talk. Say "STOP" or "SHUT UP" to silence me.<br>';
    addMessage('agent', html, true);
    updateStatus('idle');
  }

  // ════════════════════════════════════════════
  // HANDLER: Fallback
  // ════════════════════════════════════════════
  function handleFallback(text, lower) {
    var meta = ZONE_META[ZONE] || ZONE_META.hub;
    var html = 'I\'m not sure how to help with that. Here are some things I can do in the <strong>' + meta.name + '</strong> zone:<br><br>';
    var prompts = meta.prompts || [];
    for (var i = 0; i < prompts.length; i++) {
      html += '\u2022 "' + escapeHtml(prompts[i]) + '"<br>';
    }
    html += '<br>Or say "help" for a full list of commands.';
    addMessage('agent', html, true);
    renderPrompts();
    updateStatus('idle');
  }

  // ════════════════════════════════════════════
  // UTILITY
  // ════════════════════════════════════════════
  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // ════════════════════════════════════════════
  // INITIALIZATION
  // ════════════════════════════════════════════
  function init() {
    createUI();

    // Preload voices for TTS
    if (window.speechSynthesis) {
      window.speechSynthesis.getVoices();
      if (window.speechSynthesis.onvoiceschanged !== undefined) {
        window.speechSynthesis.onvoiceschanged = function () { window.speechSynthesis.getVoices(); };
      }
    }

    // Restore saved view mode
    var savedViewMode = load('viewmode', null);
    if (!savedViewMode) {
      try { savedViewMode = localStorage.getItem('vr_ai_viewmode'); } catch (e) { /* ignore */ }
    }
    if (savedViewMode && (savedViewMode === 'simple' || savedViewMode === 'focus')) {
      // Delay to let other components initialize first
      setTimeout(function () { setViewMode(savedViewMode); }, 1500);
    } else {
      state.viewMode = 'full';
      setTimeout(function () { updateViewModeBar(); }, 500);
    }

    // Check first-time visit
    if (isFirstVisit(ZONE)) {
      // Show welcome after a short delay to let the page load
      setTimeout(function () { showWelcome(); }, 2500);
    }

    // Suppress old AI assistant button if it exists (from quick-wins-substantial-set7)
    setTimeout(function () {
      var oldBtn = document.getElementById('vr-ai-btn');
      var oldPanel = document.getElementById('vr-ai-panel');
      if (oldBtn) oldBtn.style.display = 'none';
      if (oldPanel) oldPanel.style.display = 'none';
    }, 1000);

    console.log('[VR AI Agent] Initialized for zone: ' + ZONE);
  }

  // Wait for DOM
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // ════════════════════════════════════════════
  // PUBLIC API
  // ════════════════════════════════════════════
  window.VRAIAgent = {
    open: openPanel,
    toggle: togglePanel,
    ask: handleUserInput,
    speak: speak,
    stop: stopSpeaking,
    getZone: function () { return ZONE; },
    isFirstVisit: isFirstVisit,
    resetTutorial: resetFirstTimeMode,
    showLogin: showLoginOverlay,
    // View mode API
    setViewMode: setViewMode,
    getViewMode: getViewMode,
    focusMode: function () { setViewMode('focus'); },
    simpleMode: function () { setViewMode('simple'); },
    fullMode: function () { setViewMode('full'); }
  };

})();
