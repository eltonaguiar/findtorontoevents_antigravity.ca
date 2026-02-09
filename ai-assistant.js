/**
 * AI Assistant for findtorontoevents.ca
 * 
 * Free, client-side assistant using browser Web Speech APIs.
 * No API keys required. Pattern-matching intelligence with
 * live data fetching from existing endpoints.
 * 
 * Features:
 * - Voice input (SpeechRecognition) and output (speechSynthesis)
 * - Context-aware per page section
 * - Guided conversational flow (context → category → timeframe → results)
 * - Event summarization with time/type/location filters
 * - Location-aware events (postal code, area name, "near me" geolocation)
 * - Weather + jacket recommendation (Open-Meteo, free)
 * - Specific weather queries (rain, snow, precipitation, long-term forecast)
 * - Postal code weather lookup via Nominatim geocoding
 * - Stock insights summary
 * - Streamer/creator live status with refresh + loading bar
 * - Creator new content/posts/videos with time filters
 * - Accountability task summary
 * - Movie/show trailer queuing
 * - Tutorial / first-time mode
 * - Multi-task combining
 * - "STOP" / "SHUT UP" halts audio
 * - Auto-prompt suggestion chips
 * - Icon & menu explanation
 * - Navigation commands
 */
(function () {
  'use strict';

  // ═══════════════════════════════════════════════════════════
  // CONFIG
  // ═══════════════════════════════════════════════════════════
  var CONFIG = {
    eventsJsonPaths: ['/next/events.json', '/events.json', '/data/events.json'],
    weatherApi: 'https://api.open-meteo.com/v1/forecast',
    weatherLat: 43.6532,
    weatherLon: -79.3832,
    fcApi: 'https://findtorontoevents.ca/fc/api',
    aiPrefsApi: 'https://findtorontoevents.ca/fc/api/ai_preferences.php',
    stocksPage: '/findstocks/',
    moviesApi: '/MOVIESHOWS3/api/get-movies.php',
    nearMeApi: 'https://findtorontoevents.ca/fc/api/nearme.php',
    nowPlayingApi: 'https://findtorontoevents.ca/fc/api/now_playing.php',
    cineplexShowtimesApi: 'https://findtorontoevents.ca/fc/api/cineplex_showtimes.php',
    responseDelay: 300,
    firstTimeKey: 'fte_ai_first_visit',
    visitedSectionsKey: 'fte_ai_visited_sections',
    tutorialModeKey: 'fte_ai_tutorial_mode',
    hideBtnKey: 'fte_ai_hide_btn',
    muteTTSKey: 'fte_ai_mute_tts',
    aiEnabledKey: 'fte_ai_enabled',
    defaultTheaterKey: 'fte_default_theater',
    guestUsageApi: 'https://findtorontoevents.ca/fc/api/guest_usage.php',
    guestAiUsedKey: 'fte_ai_guest_used',
    verifyBusinessApi: 'https://findtorontoevents.ca/fc/api/verify_business.php'
  };

  // ═══════════════════════════════════════════════════════════
  // MOTIVATIONAL TIPS BANK (sourced from motivation.html research)
  // ═══════════════════════════════════════════════════════════
  var MOTIVATION_TIPS = [
    { icon: '\u{1F4CD}', title: 'Implementation Intentions', tip: 'Don\'t just say "I\'ll work out more." Say <b>"I will go to the gym at 7:00 AM at [PLACE]."</b> People who use this formula are 2-3x more likely to follow through. (Gollwitzer, 1999)', source: 'Peter Gollwitzer, NYU' },
    { icon: '\u23F1\uFE0F', title: 'The 2-Minute Rule', tip: 'The biggest barrier isn\'t the workout \u2014 it\'s <b>starting</b>. Scale it down: "Go to the gym" becomes "Put on your gym shoes." Consistency precedes intensity. (BJ Fogg, Stanford)', source: 'BJ Fogg, Stanford' },
    { icon: '\u{1FA9E}', title: 'Identity-Based Habits', tip: 'Stop saying "I want to go to the gym." Start saying <b>"I am someone who works out."</b> Each check-in is a vote for the person you\'re becoming. Identity shift > willpower. (James Clear)', source: 'James Clear, Atomic Habits' },
    { icon: '\u{1F3A7}', title: 'Temptation Bundling', tip: 'Save your favorite podcast or show for <b>gym-only</b>. In Milkman\'s Wharton study, gym visits <b>increased 51%</b> when people could only listen to addictive audiobooks at the gym.', source: 'Katy Milkman, Wharton' },
    { icon: '\u{1F3E0}', title: 'Environment Design', tip: 'People with "good self-control" don\'t have more willpower \u2014 they <b>structure their environment</b>. Sleep in gym clothes. Pack your bag the night before. Put keys on top of your gym bag. (Wendy Wood)', source: 'Wendy Wood, USC' },
    { icon: '\u{1F5D3}\uFE0F', title: 'The Fresh Start Effect', tip: 'Missed a day? Treat <b>right now</b> as a fresh start. Temporal landmarks (Monday, new month, even "today") create a psychological reset. Use "never miss twice" as your rule. One miss is human; two is a pattern.', source: 'Dai, Milkman, Riis (Wharton)' },
    { icon: '\u{1F525}', title: 'Loss Aversion & Streaks', tip: 'The pain of losing is <b>~2x stronger</b> than the pleasure of gaining. Your streak isn\'t just a number \u2014 it\'s something you\'ve invested in. Breaking it <i>hurts</i>. That\'s by design. (Kahneman & Tversky)', source: 'Kahneman & Tversky, Prospect Theory' },
    { icon: '\u{1F9E0}', title: 'Self-Determination Theory', tip: 'Intrinsic motivation needs 3 things: <b>Autonomy</b> (choose YOUR workout), <b>Competence</b> (track progress, celebrate PRs), <b>Relatedness</b> (accountability partner or community). If your routine feels like punishment, check which need is missing.', source: 'Deci & Ryan' },
    { icon: '\u{1F465}', title: 'Social Accountability', tip: 'Having a <b>specific accountability appointment</b> with someone raises your probability of completing a goal to <b>95%</b> \u2014 up from 65% with just a commitment. Tell someone your plan. (ASTD study)', source: 'JAMA Internal Medicine' },
    { icon: '\u{1F9E9}', title: 'The Zeigarnik Effect', tip: 'Your brain <b>can\'t stop thinking about incomplete tasks</b>. Leave tomorrow\'s workout plan open \u2014 write down the exercises tonight. The unfinished plan nags at you until you do it. Use this to your advantage.', source: 'Bluma Zeigarnik, 1927' },
    { icon: '\u{1F3CB}\uFE0F', title: 'Shrink the Commitment', tip: 'On your worst days, commit to <b>just 10 minutes</b>. A British Journal of Sports Medicine study found even brief bouts under 10 min provide significant health benefits. Your only job is to not break the chain.', source: 'BJSM, 2019' },
    { icon: '\u{1F614}', title: 'Don\'t Trust Pre-Workout Dread', tip: 'Multiple studies confirm <b>mood improves AFTER exercise begins</b>, not before. Your pre-workout dread is a terrible predictor of post-workout satisfaction. Exercise improves mood within 5 minutes of starting. Go anyway.', source: 'Health Psychology Review, 2018' },
    { icon: '\u{1F305}', title: 'Morning Exercisers Win', tip: 'Morning exercisers show <b>significantly higher consistency rates</b>. Not because mornings are magical, but because there are fewer competing demands, decisions, and excuses early in the day. Decision fatigue is real.', source: 'Health Psychology, 2019' },
    { icon: '\u{1F60A}', title: 'Enjoyment > Results', tip: '<b>Exercise enjoyment</b> is the single strongest predictor of long-term adherence \u2014 stronger than fitness goals or body changes. If you hate your routine, change it. The best workout is one you\'ll actually do.', source: 'Int. J. Behavioral Nutrition' },
    { icon: '\u{1F4CA}', title: 'Track Everything (Hawthorne Effect)', tip: 'Simply <b>tracking your workouts makes you more likely to do them</b>. Known as the Hawthorne Effect since 1958 \u2014 you change your behavior by observing it. That\'s why check-ins work. You\'re not just logging data.', source: 'Hawthorne Effect, 1958' }
  ];

  // ═══════════════════════════════════════════════════════════
  // STATE
  // ═══════════════════════════════════════════════════════════
  var state = {
    open: false,
    listening: false,
    speaking: false,
    processing: false,
    cancelled: false,
    eventsData: null,
    eventsLoaded: false,
    weatherCache: null,
    weatherCacheTime: 0,
    recognition: null,
    currentSection: 'events',
    chatHistory: [],
    tutorialMode: false,
    hiddenOnMovies: load(CONFIG.hideBtnKey, false),
    muteTTS: load(CONFIG.muteTTSKey, false),
    // Guided conversation flow
    flow: null,       // null | 'awaiting_context_choice' | 'awaiting_category' | 'awaiting_timeframe'
    flowData: {},     // temp data for guided flow { category, ... }
    userLocation: null, // { lat, lon, area } cached geolocation
    lastOfferedCreator: null, // { name, url, platform } — tracks the creator we offered to open
    aiEnabled: load(CONFIG.aiEnabledKey, true), // master on/off — persisted for logged-in users
    dbPrefsSynced: false, // whether we've fetched DB prefs for this session
    guestAiCheckDone: false, // whether we've verified guest AI usage with server
    guestAiAllowed: true    // cached result of guest AI check
  };

  // ═══════════════════════════════════════════════════════════
  // HELPERS
  // ═══════════════════════════════════════════════════════════
  function store(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { } }
  function load(k, d) { try { var v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } }

  function detectSection() {
    var path = window.location.pathname.toLowerCase();
    var hash = window.location.hash.toLowerCase();
    if (path.indexOf('/findstocks') !== -1) return 'stocks';
    // MovieShows — detect V1/V2/V3
    if (path.indexOf('/movieshows3') !== -1) return 'movies_v3';
    if (path.indexOf('/movieshows2') !== -1) return 'movies_v2';
    if (path.indexOf('/movieshows') !== -1 || path.indexOf('/movies') !== -1) return 'movies';
    if (path.indexOf('/fc/') !== -1 || path.indexOf('/favcreators') !== -1) {
      if (hash.indexOf('accountability') !== -1) return 'accountability';
      return 'streamers';
    }
    if (path.indexOf('/vr/') !== -1) {
      if (path.indexOf('weather') !== -1) return 'weather';
      if (path.indexOf('stock') !== -1) return 'stocks';
      if (path.indexOf('movie') !== -1) return 'movies';
      if (path.indexOf('creator') !== -1) return 'streamers';
      return 'vr';
    }
    if (path.indexOf('/mentalhealthresources') !== -1) return 'wellness';
    if (path.indexOf('/stats') !== -1) return 'stats';
    if (path.indexOf('/windowsfixer') !== -1) return 'windowsfixer';
    return 'events';
  }

  function formatDate(d) {
    var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    var days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    return days[d.getDay()] + ' ' + months[d.getMonth()] + ' ' + d.getDate();
  }

  function formatTime(d) {
    var h = d.getHours();
    var m = d.getMinutes();
    var ampm = h >= 12 ? 'PM' : 'AM';
    h = h % 12 || 12;
    return h + ':' + (m < 10 ? '0' : '') + m + ' ' + ampm;
  }

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.appendChild(document.createTextNode(s));
    return d.innerHTML;
  }

  // ── STREAM URL BUILDER ──
  function buildStreamUrl(platform, username) {
    if (!username) return null;
    var p = (platform || '').toLowerCase();
    if (p === 'twitch') return 'https://twitch.tv/' + encodeURIComponent(username);
    if (p === 'kick') return 'https://kick.com/' + encodeURIComponent(username);
    if (p === 'tiktok') return 'https://tiktok.com/@' + encodeURIComponent(username) + '/live';
    if (p === 'youtube') return 'https://youtube.com/@' + encodeURIComponent(username) + '/live';
    if (p === 'instagram') return 'https://instagram.com/' + encodeURIComponent(username) + '/live';
    return null;
  }

  // Build best stream URL for a live creator from cached/live data
  function getBestStreamInfo(creator) {
    var name = creator.name || creator.display_name || 'Unknown';
    // Try platforms array (from cached live data)
    if (creator.platforms && creator.platforms.length > 0) {
      for (var i = 0; i < creator.platforms.length; i++) {
        if (creator.platforms[i].isLive) {
          var url = buildStreamUrl(creator.platforms[i].platform, creator.platforms[i].username);
          if (url) return { name: name, platform: creator.platforms[i].platform, url: url };
        }
      }
      // Fallback: first platform with a username
      var fp = creator.platforms[0];
      var url2 = buildStreamUrl(fp.platform, fp.username);
      if (url2) return { name: name, platform: fp.platform, url: url2 };
    }
    // Try accounts array (from creator list data)
    if (creator.accounts && creator.accounts.length > 0) {
      for (var j = 0; j < creator.accounts.length; j++) {
        var acc = creator.accounts[j];
        if (acc.isLive || acc.is_live) {
          var url3 = acc.url || buildStreamUrl(acc.platform, acc.username);
          if (url3) return { name: name, platform: acc.platform, url: url3 };
        }
      }
      // Fallback: first account with a URL
      var fa = creator.accounts[0];
      var url4 = fa.url || buildStreamUrl(fa.platform, fa.username);
      if (url4) return { name: name, platform: fa.platform, url: url4 };
    }
    // Try direct fields
    if (creator.url || creator.stream_url || creator.channel_url) {
      return { name: name, platform: creator.platform || 'stream', url: creator.url || creator.stream_url || creator.channel_url };
    }
    return null;
  }

  // ── ACCOUNTABILITY HELPERS ──
  function getAccountabilityAuth() {
    // Try standalone accountability discord ID first
    var discordId = null;
    var appUserId = null;
    try { discordId = localStorage.getItem('accountability_discord_id'); } catch(_){}
    // Try FC logged-in user for app_user_id
    var user = window.__fc_logged_in_user__;
    if (!user || !user.id) {
      try { var c = localStorage.getItem('fav_creators_auth_user'); if (c) { var p = JSON.parse(c); if (p && p.id) user = p; } } catch(_){}
    }
    if (user && user.id) appUserId = user.id;
    return { discordId: discordId, appUserId: appUserId, hasAuth: !!(discordId || appUserId) };
  }

  async function fetchAccountabilityDashboard() {
    var auth = getAccountabilityAuth();
    if (!auth.hasAuth) return null;
    try {
      var url = CONFIG.fcApi + '/accountability/dashboard.php?';
      if (auth.appUserId) url += 'app_user_id=' + auth.appUserId;
      if (auth.discordId) url += (auth.appUserId ? '&' : '') + 'discord_id=' + auth.discordId;
      var resp = await fetch(url);
      if (!resp.ok) return null;
      var result = await resp.json();
      if (result.error) return null;
      return result;
    } catch (e) {
      return null;
    }
  }

  function getRandomMotivationTip() {
    return MOTIVATION_TIPS[Math.floor(Math.random() * MOTIVATION_TIPS.length)];
  }

  function daysBetween(dateStr1, dateStr2) {
    var d1 = new Date(dateStr1);
    var d2 = new Date(dateStr2 || new Date().toISOString().split('T')[0]);
    var diff = Math.abs(d2 - d1);
    return Math.floor(diff / (1000 * 60 * 60 * 24));
  }

  function formatMotivationTipHtml(tip) {
    return '<div style="margin-top:10px;padding:10px 12px;background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.2);border-radius:10px;">' +
      '<div style="font-size:0.9rem;font-weight:600;margin-bottom:4px;">' + tip.icon + ' ' + tip.title + '</div>' +
      '<div style="font-size:0.82rem;color:#cbd5e1;line-height:1.5;">' + tip.tip + '</div>' +
      '<div style="font-size:0.7rem;color:#64748b;margin-top:4px;">\u2014 ' + tip.source + '</div>' +
      '</div>';
  }

  function isToday(d) {
    var now = new Date();
    return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
  }

  function isTomorrow(d) {
    var tom = new Date();
    tom.setDate(tom.getDate() + 1);
    return d.getFullYear() === tom.getFullYear() && d.getMonth() === tom.getMonth() && d.getDate() === tom.getDate();
  }

  function isThisWeek(d) {
    var now = new Date();
    var start = new Date(now); start.setDate(now.getDate() - now.getDay());
    start.setHours(0, 0, 0, 0);
    var end = new Date(start); end.setDate(start.getDate() + 7);
    return d >= start && d < end;
  }

  function isThisWeekend(d) {
    var day = d.getDay();
    var now = new Date();
    var thisFri = new Date(now);
    thisFri.setDate(now.getDate() + (5 - now.getDay() + 7) % 7);
    thisFri.setHours(17, 0, 0, 0);
    var thisSun = new Date(thisFri);
    thisSun.setDate(thisFri.getDate() + 2);
    thisSun.setHours(23, 59, 59, 999);
    if (now.getDay() === 5 && now.getHours() >= 17) {
      thisFri = new Date(now);
      thisFri.setHours(17, 0, 0, 0);
    }
    if (now.getDay() === 6 || now.getDay() === 0) {
      thisFri = new Date(now);
      thisFri.setDate(now.getDate() - (now.getDay() === 6 ? 1 : 2));
      thisFri.setHours(17, 0, 0, 0);
      thisSun = new Date(thisFri);
      thisSun.setDate(thisFri.getDate() + 2);
      thisSun.setHours(23, 59, 59, 999);
    }
    return d >= thisFri && d <= thisSun;
  }

  function isThisMonth(d) {
    var now = new Date();
    return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth();
  }

  function isNext3Months(d) {
    var now = new Date();
    var end = new Date(now);
    end.setMonth(end.getMonth() + 3);
    return d >= now && d <= end;
  }

  function isStartingSoon(d) {
    var now = new Date();
    var soon = new Date(now);
    soon.setHours(soon.getHours() + 3);
    return d >= now && d <= soon;
  }

  function isFutureOrToday(d) {
    var now = new Date();
    now.setHours(0, 0, 0, 0);
    return d >= now;
  }

  // ── LOCATION HELPERS ──
  var TORONTO_AREAS = {
    'downtown': { lat: 43.6510, lon: -79.3470, label: 'Downtown Toronto' },
    'midtown': { lat: 43.6870, lon: -79.3960, label: 'Midtown Toronto' },
    'north york': { lat: 43.7615, lon: -79.4111, label: 'North York' },
    'scarborough': { lat: 43.7731, lon: -79.2577, label: 'Scarborough' },
    'etobicoke': { lat: 43.6205, lon: -79.5132, label: 'Etobicoke' },
    'east york': { lat: 43.6910, lon: -79.3280, label: 'East York' },
    'liberty village': { lat: 43.6375, lon: -79.4195, label: 'Liberty Village' },
    'distillery': { lat: 43.6503, lon: -79.3596, label: 'Distillery District' },
    'kensington': { lat: 43.6545, lon: -79.4005, label: 'Kensington Market' },
    'queen west': { lat: 43.6467, lon: -79.4057, label: 'Queen West' },
    'king west': { lat: 43.6440, lon: -79.4010, label: 'King West' },
    'the annex': { lat: 43.6710, lon: -79.4060, label: 'The Annex' },
    'beaches': { lat: 43.6710, lon: -79.2960, label: 'The Beaches' },
    'the beach': { lat: 43.6710, lon: -79.2960, label: 'The Beaches' },
    'leslieville': { lat: 43.6630, lon: -79.3310, label: 'Leslieville' },
    'parkdale': { lat: 43.6390, lon: -79.4450, label: 'Parkdale' },
    'junction': { lat: 43.6640, lon: -79.4680, label: 'The Junction' },
    'harbourfront': { lat: 43.6390, lon: -79.3810, label: 'Harbourfront' },
    'yorkville': { lat: 43.6710, lon: -79.3930, label: 'Yorkville' },
    'entertainment district': { lat: 43.6460, lon: -79.3880, label: 'Entertainment District' },
    'financial district': { lat: 43.6480, lon: -79.3810, label: 'Financial District' },
    'chinatown': { lat: 43.6530, lon: -79.3980, label: 'Chinatown' },
    'little italy': { lat: 43.6550, lon: -79.4200, label: 'Little Italy' },
    'greektown': { lat: 43.6790, lon: -79.3510, label: 'Greektown' },
    'danforth': { lat: 43.6790, lon: -79.3510, label: 'The Danforth' },
    'koreatown': { lat: 43.6640, lon: -79.4150, label: 'Koreatown' },
    'st lawrence': { lat: 43.6500, lon: -79.3720, label: 'St. Lawrence Market' },
    'ossington': { lat: 43.6530, lon: -79.4230, label: 'Ossington' },
    'bloor west': { lat: 43.6490, lon: -79.4780, label: 'Bloor West Village' },
    'high park': { lat: 43.6465, lon: -79.4637, label: 'High Park' },
    'roncesvalles': { lat: 43.6480, lon: -79.4520, label: 'Roncesvalles' },
    'cabbagetown': { lat: 43.6680, lon: -79.3630, label: 'Cabbagetown' },
    'corso italia': { lat: 43.6720, lon: -79.4440, label: 'Corso Italia' },
    'trinity bellwoods': { lat: 43.6470, lon: -79.4140, label: 'Trinity Bellwoods' },
    'roncy': { lat: 43.6480, lon: -79.4520, label: 'Roncesvalles' },
    'regent park': { lat: 43.6590, lon: -79.3630, label: 'Regent Park' },
    'moss park': { lat: 43.6550, lon: -79.3680, label: 'Moss Park' },
    'church wellesley': { lat: 43.6660, lon: -79.3810, label: 'Church-Wellesley Village' },
    'the village': { lat: 43.6660, lon: -79.3810, label: 'Church-Wellesley Village' }
  };

  function parsePostalCode(text) {
    var m = text.match(/([a-z]\d[a-z])\s?(\d[a-z]\d)/i);
    return m ? (m[1] + ' ' + m[2]).toUpperCase() : null;
  }

  function parseAreaName(lower) {
    for (var area in TORONTO_AREAS) {
      if (lower.indexOf(area) !== -1) return TORONTO_AREAS[area];
    }
    return null;
  }

  // Geocode Canadian postal code via Nominatim (free, no key)
  async function geocodePostalCode(postal) {
    try {
      var resp = await fetch('https://nominatim.openstreetmap.org/search?postalcode=' + encodeURIComponent(postal.replace(/\s/g, '')) + '&country=ca&format=json&limit=1', {
        headers: { 'User-Agent': 'FindTorontoEvents/1.0' }
      });
      var data = await resp.json();
      if (data && data.length > 0) {
        return { lat: parseFloat(data[0].lat), lon: parseFloat(data[0].lon), label: postal + ' area' };
      }
    } catch (e) { /* silent */ }
    return null;
  }

  function getUserLocation() {
    return new Promise(function (resolve) {
      if (state.userLocation) { resolve(state.userLocation); return; }
      if (!navigator.geolocation) { resolve(null); return; }
      navigator.geolocation.getCurrentPosition(
        function (pos) {
          state.userLocation = { lat: pos.coords.latitude, lon: pos.coords.longitude, label: 'your location' };
          resolve(state.userLocation);
        },
        function () { resolve(null); },
        { timeout: 8000, maximumAge: 300000 }
      );
    });
  }

  // Haversine distance in km
  function haversineKm(lat1, lon1, lat2, lon2) {
    var R = 6371;
    var dLat = (lat2 - lat1) * Math.PI / 180;
    var dLon = (lon2 - lon1) * Math.PI / 180;
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  // Filter events whose location text mentions a neighbourhood
  function filterEventsByLocation(events, areaLabel) {
    if (!areaLabel) return events;
    var areaLow = areaLabel.toLowerCase();
    // Also build keyword list from the label
    var keywords = areaLow.replace(/[^a-z ]/g, '').split(' ').filter(function (w) { return w.length > 2; });
    return events.filter(function (ev) {
      var loc = ((ev.location || '') + ' ' + (ev.description || '') + ' ' + (ev.title || '')).toLowerCase();
      if (loc.indexOf(areaLow) !== -1) return true;
      for (var i = 0; i < keywords.length; i++) {
        if (loc.indexOf(keywords[i]) !== -1) return true;
      }
      return false;
    });
  }

  // ── LOADING BAR HELPERS ──
  function showLoadingBar(label) {
    removeLoadingBar();
    var container = document.getElementById('fte-ai-messages');
    if (!container) return;
    var bar = document.createElement('div');
    bar.id = 'fte-ai-loading-bar';
    bar.className = 'fte-ai-msg ai';
    bar.innerHTML = '<div style="font-size:12px;color:#a5b4fc;margin-bottom:6px;">' + escapeHtml(label || 'Loading...') + '</div>' +
      '<div style="width:100%;height:6px;background:rgba(255,255,255,0.06);border-radius:3px;overflow:hidden;">' +
      '<div id="fte-ai-progress" style="height:100%;width:0%;background:linear-gradient(90deg,#6366f1,#8b5cf6);border-radius:3px;transition:width .3s ease;"></div>' +
      '</div>';
    container.appendChild(bar);
    container.scrollTop = container.scrollHeight;
  }

  function updateLoadingBar(pct) {
    var el = document.getElementById('fte-ai-progress');
    if (el) el.style.width = Math.min(100, Math.max(0, pct)) + '%';
  }

  function removeLoadingBar() {
    var el = document.getElementById('fte-ai-loading-bar');
    if (el) el.remove();
  }

  // ── DATABASE PREFERENCE SYNC ──
  // For logged-in users, persist AI on/off and mute preferences to the server
  function syncPrefsFromDB() {
    var user = window.__fc_logged_in_user__;
    if (!user || !user.id || state.dbPrefsSynced) return;
    state.dbPrefsSynced = true;
    try {
      fetch(CONFIG.aiPrefsApi + '?user_id=' + user.id)
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data && data.preferences) {
            if (typeof data.preferences.ai_enabled === 'boolean') {
              state.aiEnabled = data.preferences.ai_enabled;
              store(CONFIG.aiEnabledKey, state.aiEnabled);
              if (!state.aiEnabled) hideAssistantCompletely();
            }
            if (typeof data.preferences.ai_mute_tts === 'boolean') {
              state.muteTTS = data.preferences.ai_mute_tts;
              store(CONFIG.muteTTSKey, state.muteTTS);
            }
          }
        })
        .catch(function () { /* silent */ });
    } catch (e) { /* silent */ }
  }

  function savePrefToDB(key, value) {
    var user = window.__fc_logged_in_user__;
    if (!user || !user.id) return;
    try {
      var body = { user_id: user.id };
      body[key] = value;
      fetch(CONFIG.aiPrefsApi, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      }).catch(function () { /* silent */ });
    } catch (e) { /* silent */ }
  }

  // ── GUEST RATE-LIMIT HELPERS ──
  function isUserLoggedIn() {
    var user = window.__fc_logged_in_user__;
    if (user && user.id) return true;
    try {
      var c = localStorage.getItem('fav_creators_auth_user');
      if (c) { var p = JSON.parse(c); if (p && p.id) return true; }
    } catch (_) {}
    return false;
  }

  function checkGuestAiAllowed(callback) {
    if (isUserLoggedIn()) { callback(true); return; }
    // Quick client-side check
    if (load(CONFIG.guestAiUsedKey, false) && state.guestAiCheckDone) {
      callback(false);
      return;
    }
    // Server-side check by IP
    try {
      fetch(CONFIG.guestUsageApi + '?action=check_ai')
        .then(function (r) { return r.json(); })
        .then(function (data) {
          state.guestAiCheckDone = true;
          if (data && data.ok) {
            state.guestAiAllowed = data.allowed;
            if (!data.allowed) store(CONFIG.guestAiUsedKey, true);
            callback(data.allowed);
          } else {
            callback(true); // fail open
          }
        })
        .catch(function () { callback(true); }); // fail open
    } catch (e) { callback(true); }
  }

  function recordGuestAiUsage() {
    if (isUserLoggedIn()) return;
    try {
      fetch(CONFIG.guestUsageApi, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'record_ai' })
      }).then(function (r) { return r.json(); })
        .then(function (data) {
          if (data && !data.allowed) {
            store(CONFIG.guestAiUsedKey, true);
            state.guestAiAllowed = false;
          }
        }).catch(function () { /* silent */ });
    } catch (e) { /* silent */ }
  }

  function showGuestAiLimitMessage() {
    addMessage('ai',
      '<div class="fte-ai-summary">' +
      '<b>Sign in to keep chatting!</b><br><br>' +
      'You\'ve used your free message as a guest. ' +
      'Sign in to get <b>unlimited</b> access to the AI assistant, plus:<br><br>' +
      '\u2022 Track your favorite creators across platforms<br>' +
      '\u2022 Save events and build your calendar<br>' +
      '\u2022 Get personalized recommendations<br><br>' +
      '<a href="/fc/#login" style="display:inline-block;padding:10px 24px;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;border-radius:10px;text-decoration:none;font-weight:600;font-size:14px;">Sign In / Create Account</a>' +
      '<br><br><span style="color:#64748b;font-size:0.8rem;">It\'s free and takes under 30 seconds.</span>' +
      '</div>',
      false);
    setStatus('Sign in required', '#f59e0b');
  }

  function hideAssistantCompletely() {
    var btn = document.getElementById('fte-ai-btn');
    var panel = document.getElementById('fte-ai-panel');
    if (btn) btn.style.display = 'none';
    if (panel) { panel.classList.remove('open'); panel.style.display = 'none'; }
    state.open = false;
  }

  function showAssistantAgain() {
    var btn = document.getElementById('fte-ai-btn');
    var panel = document.getElementById('fte-ai-panel');
    if (btn) btn.style.display = '';
    if (panel) panel.style.display = '';
  }

  // ═══════════════════════════════════════════════════════════
  // CSS INJECTION
  // ═══════════════════════════════════════════════════════════
  function injectCSS() {
    if (document.getElementById('fte-ai-css')) return;
    var style = document.createElement('style');
    style.id = 'fte-ai-css';
    var sec = detectSection();
    var isMovies = sec === 'movies' || sec === 'movies_v2' || sec === 'movies_v3';
    style.textContent = [
      '@keyframes fteAiPulse { 0%,100%{box-shadow:0 0 0 0 rgba(99,102,241,0.6)} 50%{box-shadow:0 0 0 14px rgba(99,102,241,0)} }',
      '@keyframes fteAiSlideUp { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }',
      '@keyframes fteAiFadeIn { from{opacity:0} to{opacity:1} }',
      '@keyframes fteAiDots { 0%,20%{content:"."} 40%{content:".."} 60%,100%{content:"..."} }',
      '@keyframes fteAiGlow { 0%,100%{box-shadow:0 4px 24px rgba(99,102,241,0.5)} 50%{box-shadow:0 4px 32px rgba(139,92,246,0.7)} }',
      '#fte-ai-btn { position:fixed !important; bottom:100px !important; right:24px !important; height:48px !important; min-width:48px !important; border-radius:24px !important; background:linear-gradient(135deg,#6366f1,#8b5cf6) !important; border:2px solid rgba(255,255,255,0.25) !important; color:#fff !important; font-size:15px !important; cursor:pointer !important; z-index:100000 !important; display:flex !important; align-items:center !important; justify-content:center !important; gap:8px !important; padding:0 16px !important; box-shadow:0 4px 24px rgba(99,102,241,0.5) !important; transition:all .3s ease !important; animation:fteAiGlow 3s ease-in-out infinite !important; font-family:Inter,system-ui,-apple-system,sans-serif !important; font-weight:700 !important; letter-spacing:0.02em !important; white-space:nowrap !important; line-height:1 !important; visibility:visible !important; opacity:1 !important; }',
      '#fte-ai-btn:hover { transform:scale(1.05) !important; box-shadow:0 8px 40px rgba(99,102,241,0.7) !important; }',
      '#fte-ai-btn.listening { animation:fteAiPulse 1.5s infinite !important; background:linear-gradient(135deg,#22c55e,#16a34a) !important; }',
      '#fte-ai-btn.speaking { background:linear-gradient(135deg,#f59e0b,#d97706) !important; animation:none !important; }',
      '#fte-ai-btn .fte-ai-label { font-size:12px !important; font-weight:700 !important; text-transform:uppercase !important; letter-spacing:0.06em !important; }',
      (isMovies ? '#fte-ai-btn { bottom:60px !important; right:16px !important; left:auto !important; top:auto !important; }' : ''),
      (isMovies ? '#fte-ai-panel { bottom:120px !important; right:16px !important; left:auto !important; top:auto !important; max-height:calc(100vh - 140px) !important; }' : ''),
      '#fte-ai-panel { position:fixed !important; bottom:160px !important; right:24px !important; width:380px !important; max-width:calc(100vw - 32px) !important; max-height:calc(100vh - 180px) !important; background:rgba(10,10,25,0.97) !important; border:1px solid rgba(99,102,241,0.3) !important; border-radius:20px !important; z-index:100001 !important; display:none !important; flex-direction:column !important; backdrop-filter:blur(20px) !important; box-shadow:0 25px 80px rgba(0,0,0,0.6) !important; animation:fteAiSlideUp .3s ease-out !important; font-family:Inter,system-ui,-apple-system,sans-serif !important; overflow:hidden !important; }',
      '#fte-ai-panel.open { display:flex !important; }',
      '#fte-ai-header { padding:12px 16px 10px !important; border-bottom:1px solid rgba(255,255,255,0.06) !important; display:flex !important; align-items:center !important; justify-content:space-between !important; flex-shrink:0 !important; }',
      '#fte-ai-header h3 { margin:0 !important; font-size:14px !important; font-weight:700 !important; color:#e2e8f0 !important; display:flex !important; align-items:center !important; gap:8px !important; }',
      '#fte-ai-header .fte-ai-status { font-size:11px; color:#64748b; font-weight:500; }',
      '#fte-ai-header .fte-ai-close { background:none !important; border:none !important; color:#64748b !important; cursor:pointer !important; font-size:18px !important; padding:4px !important; border-radius:8px !important; transition:all .2s !important; }',
      '#fte-ai-header .fte-ai-close:hover { color:#e2e8f0 !important; background:rgba(255,255,255,0.05) !important; }',
      '#fte-ai-stop-btn { background:rgba(239,68,68,0.15) !important; border:1px solid rgba(239,68,68,0.3) !important; color:#f87171 !important; font-size:11px !important; font-weight:700 !important; padding:4px 12px !important; border-radius:10px !important; cursor:pointer !important; display:none !important; align-items:center !important; gap:4px !important; font-family:inherit !important; transition:all .2s !important; }',
      '#fte-ai-stop-btn:hover { background:rgba(239,68,68,0.3) !important; color:#fca5a5 !important; }',
      '#fte-ai-stop-btn.visible { display:inline-flex !important; }',
      '#fte-ai-messages { flex:1 !important; overflow-y:auto !important; padding:14px 16px !important; display:flex !important; flex-direction:column !important; gap:10px !important; min-height:200px !important; max-height:400px !important; scrollbar-width:thin; scrollbar-color:rgba(99,102,241,0.3) transparent; }',
      '#fte-ai-messages::-webkit-scrollbar { width:5px; }',
      '#fte-ai-messages::-webkit-scrollbar-thumb { background:rgba(99,102,241,0.3); border-radius:5px; }',
      '.fte-ai-msg { padding:10px 14px !important; border-radius:14px !important; font-size:13px !important; line-height:1.5 !important; max-width:90% !important; animation:fteAiFadeIn .3s ease !important; word-wrap:break-word !important; }',
      '.fte-ai-msg.user { background:rgba(99,102,241,0.15) !important; color:#c7d2fe !important; align-self:flex-end !important; border-bottom-right-radius:4px !important; }',
      '.fte-ai-msg.ai { background:rgba(255,255,255,0.04) !important; color:#cbd5e1 !important; align-self:flex-start !important; border-bottom-left-radius:4px !important; border:1px solid rgba(255,255,255,0.04) !important; }',
      '.fte-ai-msg.ai strong { color:#a5b4fc !important; }',
      '.fte-ai-msg.system { background:rgba(234,179,8,0.1) !important; color:#fbbf24 !important; align-self:center !important; text-align:center !important; font-size:12px !important; border:1px solid rgba(234,179,8,0.15) !important; }',
      '#fte-ai-prompts { padding:8px 14px !important; display:flex !important; flex-wrap:wrap !important; gap:6px !important; border-top:1px solid rgba(255,255,255,0.04) !important; flex-shrink:0 !important; max-height:100px !important; overflow-y:auto !important; }',
      '.fte-ai-chip { padding:6px 12px !important; border-radius:20px !important; border:1px solid rgba(99,102,241,0.25) !important; background:rgba(99,102,241,0.08) !important; color:#a5b4fc !important; font-size:11px !important; cursor:pointer !important; transition:all .2s !important; white-space:nowrap !important; font-family:inherit !important; }',
      '.fte-ai-chip:hover { background:rgba(99,102,241,0.2) !important; border-color:rgba(99,102,241,0.5) !important; color:#c7d2fe !important; }',
      '#fte-ai-input-area { padding:12px 14px !important; border-top:1px solid rgba(255,255,255,0.06) !important; display:flex !important; gap:8px !important; align-items:center !important; flex-shrink:0 !important; }',
      '#fte-ai-input { flex:1 !important; padding:10px 14px !important; border-radius:12px !important; background:rgba(255,255,255,0.05) !important; border:1px solid rgba(255,255,255,0.08) !important; color:#e2e8f0 !important; font-size:13px !important; font-family:inherit !important; outline:none !important; transition:border-color .2s !important; }',
      '#fte-ai-input:focus { border-color:rgba(99,102,241,0.5) !important; }',
      '#fte-ai-input::placeholder { color:#475569 !important; }',
      '.fte-ai-icon-btn { width:38px !important; height:38px !important; border-radius:12px !important; border:1px solid rgba(255,255,255,0.08) !important; background:rgba(255,255,255,0.04) !important; color:#94a3b8 !important; cursor:pointer !important; display:flex !important; align-items:center !important; justify-content:center !important; font-size:16px !important; transition:all .2s !important; flex-shrink:0 !important; }',
      '.fte-ai-icon-btn:hover { background:rgba(99,102,241,0.15) !important; color:#c7d2fe !important; border-color:rgba(99,102,241,0.3) !important; }',
      '.fte-ai-icon-btn.active { background:rgba(34,197,94,0.2) !important; color:#22c55e !important; border-color:rgba(34,197,94,0.4) !important; }',
      '.fte-ai-icon-btn.send { background:rgba(99,102,241,0.2) !important; color:#a5b4fc !important; border-color:rgba(99,102,241,0.3) !important; }',
      '.fte-ai-icon-btn.send:hover { background:rgba(99,102,241,0.35) !important; }',
      '@media(max-width:480px) { #fte-ai-panel { width:calc(100vw - 16px) !important; right:8px !important; bottom:160px !important; max-height:calc(100vh - 180px) !important; } #fte-ai-btn { bottom:100px !important; right:12px !important; } }',
      '#fte-ai-btn.hidden-mode { display:none !important; }',
      '.fte-ai-summary { font-size:12px; line-height:1.6; }',
      '.fte-ai-summary b { color:#a5b4fc; }',
      '.fte-ai-summary .event-item { padding:6px 0; border-bottom:1px solid rgba(255,255,255,0.03); }',
      '.fte-ai-summary .event-item:last-child { border-bottom:none; }',
      '.fte-ai-summary a { color:#818cf8; text-decoration:underline; cursor:pointer; }',
      '.fte-ai-summary a:hover { color:#c7d2fe; }',
      '.fte-ai-typing::after { content:""; animation:fteAiDots 1.2s infinite; }'
    ].join('\n');
    document.head.appendChild(style);
  }

  // ═══════════════════════════════════════════════════════════
  // UI CREATION
  // ═══════════════════════════════════════════════════════════
  function createUI() {
    var section = detectSection();
    var isMovies = section === 'movies' || section === 'movies_v2' || section === 'movies_v3';

    var btn = document.createElement('button');
    btn.id = 'fte-ai-btn';
    btn.innerHTML = '<span style="pointer-events:none;font-size:20px">\u{1F916}</span><span class="fte-ai-label" style="pointer-events:none">AI</span>';
    btn.title = 'AI Assistant \u2014 Ask me anything';
    btn.setAttribute('aria-label', 'Open AI Assistant');
    btn.addEventListener('click', togglePanel);
    if (isMovies && state.hiddenOnMovies) btn.classList.add('hidden-mode');
    document.body.appendChild(btn);

    var panel = document.createElement('div');
    panel.id = 'fte-ai-panel';
    panel.innerHTML = [
      '<div id="fte-ai-header">',
      '  <h3><span>\u{1F916}</span> AI Assistant <span class="fte-ai-status" id="fte-ai-status">Ready</span></h3>',
      '  <div style="display:flex;align-items:center;gap:6px;">',
      '    <button id="fte-ai-stop-btn" title="Stop / Pause response">\u23F9 Stop</button>',
      '    <button class="fte-ai-close" id="fte-ai-close" title="Close">&times;</button>',
      '  </div>',
      '</div>',
      '<div id="fte-ai-messages"></div>',
      '<div id="fte-ai-prompts"></div>',
      '<div id="fte-ai-input-area">',
      '  <button class="fte-ai-icon-btn" id="fte-ai-mic" title="Click to talk"><span style="pointer-events:none">\u{1F3A4}</span></button>',
      '  <input type="text" id="fte-ai-input" placeholder="Ask me anything..." autocomplete="off" />',
      '  <button class="fte-ai-icon-btn send" id="fte-ai-send" title="Send"><span style="pointer-events:none">\u27A4</span></button>',
      '</div>'
    ].join('\n');
    document.body.appendChild(panel);

    document.getElementById('fte-ai-close').addEventListener('click', togglePanel);
    document.getElementById('fte-ai-mic').addEventListener('click', toggleMic);
    document.getElementById('fte-ai-send').addEventListener('click', sendFromInput);
    document.getElementById('fte-ai-stop-btn').addEventListener('click', cancelCurrentResponse);
    document.getElementById('fte-ai-input').addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); sendFromInput(); }
    });
  }

  function togglePanel() {
    state.open = !state.open;
    var panel = document.getElementById('fte-ai-panel');
    if (panel) {
      if (state.open) {
        panel.classList.add('open');
        // If user logged in since guest limit was hit, clear the gate
        if (isUserLoggedIn() && load(CONFIG.guestAiUsedKey, false)) {
          store(CONFIG.guestAiUsedKey, false);
          state.guestAiAllowed = true;
        }
        checkFirstVisit();
        setTimeout(function () {
          var inp = document.getElementById('fte-ai-input');
          if (inp) inp.focus();
        }, 100);
      } else {
        panel.classList.remove('open');
        stopSpeaking();
      }
    }
  }

  function setStatus(text, color) {
    var el = document.getElementById('fte-ai-status');
    if (el) {
      el.textContent = text;
      el.style.color = color || '#64748b';
    }
  }

  // ═══════════════════════════════════════════════════════════
  // MESSAGES
  // ═══════════════════════════════════════════════════════════
  function addMessage(type, html, speak) {
    if (state.cancelled && type !== 'user') return;
    var container = document.getElementById('fte-ai-messages');
    if (!container) return;
    var msg = document.createElement('div');
    msg.className = 'fte-ai-msg ' + type;
    msg.innerHTML = html;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
    state.chatHistory.push({ type: type, text: html, time: Date.now() });

    if (type === 'ai') {
      state.processing = false;
      showStopBtn(false);
    }

    if (speak !== false && type === 'ai' && !state.muteTTS && 'speechSynthesis' in window) {
      var tmp = document.createElement('div');
      tmp.innerHTML = html;
      var text = tmp.textContent || tmp.innerText || '';
      if (text.length > 0 && text.length < 500) {
        speakText(text);
      }
    }
    return msg;
  }

  function addTypingIndicator() {
    var container = document.getElementById('fte-ai-messages');
    if (!container) return null;
    var msg = document.createElement('div');
    msg.className = 'fte-ai-msg ai';
    msg.id = 'fte-ai-typing';
    msg.innerHTML = '<span class="fte-ai-typing">Thinking</span>';
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
    return msg;
  }

  function removeTypingIndicator() {
    var el = document.getElementById('fte-ai-typing');
    if (el) el.remove();
  }

  // ═══════════════════════════════════════════════════════════
  // SPEECH SYNTHESIS (TTS)
  // ═══════════════════════════════════════════════════════════
  function speakText(text) {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    state.speaking = true;
    updateBtnState();
    showStopBtn(true);
    var utter = new SpeechSynthesisUtterance(text);
    utter.rate = 1.05;
    utter.pitch = 1;
    utter.lang = 'en-US';
    utter.onend = function () { state.speaking = false; updateBtnState(); showStopBtn(false); };
    utter.onerror = function () { state.speaking = false; updateBtnState(); showStopBtn(false); };
    window.speechSynthesis.speak(utter);
  }

  function stopSpeaking() {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    state.speaking = false;
    updateBtnState();
  }

  // ═══════════════════════════════════════════════════════════
  // SPEECH RECOGNITION (STT)
  // ═══════════════════════════════════════════════════════════
  function setupRecognition() {
    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.log('[AI Assistant] Speech recognition not supported');
      return;
    }
    state.recognition = new SpeechRecognition();
    state.recognition.continuous = false;
    state.recognition.interimResults = false;
    state.recognition.lang = 'en-US';

    state.recognition.onresult = function (e) {
      var transcript = e.results[0][0].transcript;
      state.listening = false;
      updateBtnState();
      setStatus('Processing...', '#f59e0b');
      processUserInput(transcript);
    };

    state.recognition.onerror = function (e) {
      state.listening = false;
      updateBtnState();
      setStatus('Ready', '#64748b');
      if (e.error === 'not-allowed') {
        addMessage('system', 'Microphone access denied. Please allow microphone access in your browser settings.');
      } else if (e.error === 'no-speech') {
        addMessage('system', 'No speech detected. Click the mic and try again.');
      }
    };

    state.recognition.onend = function () {
      state.listening = false;
      updateBtnState();
      setStatus('Ready', '#64748b');
    };
  }

  function toggleMic() {
    if (state.listening) {
      state.listening = false;
      if (state.recognition) {
        try { state.recognition.stop(); } catch (e) { }
      }
      updateBtnState();
      setStatus('Ready', '#64748b');
    } else {
      stopSpeaking();
      state.listening = true;
      updateBtnState();
      setStatus('Listening...', '#22c55e');
      if (state.recognition) {
        try { state.recognition.start(); } catch (e) {
          state.listening = false;
          updateBtnState();
          addMessage('system', 'Could not start voice recognition. Try again.');
        }
      } else {
        state.listening = false;
        updateBtnState();
        addMessage('system', 'Voice input is not supported in your browser. Please type your message instead.');
      }
    }
  }

  function updateBtnState() {
    var btn = document.getElementById('fte-ai-btn');
    var micBtn = document.getElementById('fte-ai-mic');
    if (btn) {
      btn.classList.toggle('listening', state.listening);
      btn.classList.toggle('speaking', state.speaking && !state.listening);
    }
    if (micBtn) {
      micBtn.classList.toggle('active', state.listening);
      micBtn.innerHTML = state.listening ? '<span style="pointer-events:none">\u{1F534}</span>' : '<span style="pointer-events:none">\u{1F3A4}</span>';
    }
  }

  // ═══════════════════════════════════════════════════════════
  // INPUT HANDLING
  // ═══════════════════════════════════════════════════════════
  function cancelCurrentResponse() {
    state.cancelled = true;
    state.processing = false;
    state.flow = null;
    state.flowData = {};
    stopSpeaking();
    removeTypingIndicator();
    removeLoadingBar();
    showStopBtn(false);
    addMessage('system', 'Response stopped. You can ask something else.', false);
    setStatus('Ready', '#64748b');
  }

  function showStopBtn(visible) {
    var btn = document.getElementById('fte-ai-stop-btn');
    if (btn) {
      if (visible) btn.classList.add('visible');
      else btn.classList.remove('visible');
    }
  }

  function sendFromInput() {
    var input = document.getElementById('fte-ai-input');
    if (!input || !input.value.trim()) return;
    processUserInput(input.value.trim());
    input.value = '';
  }

  function processUserInput(rawInput) {
    var input = rawInput.trim();
    if (!input) return;

    // Cancel any in-progress response first
    if (state.processing) {
      state.cancelled = true;
      state.processing = false;
      stopSpeaking();
      removeTypingIndicator();
      removeLoadingBar();
      showStopBtn(false);
    }
    state.cancelled = false;

    addMessage('user', escapeHtml(input), false);

    var lower = input.toLowerCase();

    // ── STOP / SHUT UP / PAUSE ── (always allowed, even for guests)
    if (lower === 'stop' || lower === 'shut up' || lower.indexOf('shut up') !== -1 || lower === 'be quiet' || lower === 'silence' || lower === 'pause') {
      stopSpeaking();
      state.processing = false;
      state.flow = null;
      state.flowData = {};
      showStopBtn(false);
      removeTypingIndicator();
      addMessage('ai', "Stopping now. Click the AI button and the mic icon to re-enable voice if you want to talk again.", false);
      setStatus('Stopped', '#ef4444');
      setTimeout(function () { setStatus('Ready', '#64748b'); }, 2000);
      return;
    }

    // ── GUEST AI RATE-LIMIT GATE ──
    // Logged-in users skip this entirely. Guests get 1 free message, tracked by IP.
    if (!isUserLoggedIn()) {
      // Quick client-side check first (avoids API call if already used)
      if (load(CONFIG.guestAiUsedKey, false)) {
        showGuestAiLimitMessage();
        return;
      }
      // Async server-side check by IP
      addTypingIndicator();
      setStatus('Checking...', '#a5b4fc');
      checkGuestAiAllowed(function (allowed) {
        removeTypingIndicator();
        if (!allowed) {
          showGuestAiLimitMessage();
          return;
        }
        // Record usage, then process the message
        recordGuestAiUsage();
        _processUserInputInner(lower, input);
      });
      return;
    }

    // Logged-in users: process immediately
    _processUserInputInner(lower, input);
  }

  function _processUserInputInner(lower, input) {
    // ── HIDE / SHOW AI BUTTON ──
    if (/hide (ai|assistant|bot) (button|icon)/i.test(lower) || /hide the (ai|assistant)/i.test(lower)) {
      state.hiddenOnMovies = true;
      store(CONFIG.hideBtnKey, true);
      var btn = document.getElementById('fte-ai-btn');
      if (btn) btn.classList.add('hidden-mode');
      addMessage('ai', 'AI button hidden. You can bring it back by typing "show AI button" in the URL bar or clearing site data.', false);
      setStatus('Ready', '#64748b');
      return;
    }
    if (/show (ai|assistant|bot) (button|icon)/i.test(lower) || /show the (ai|assistant)/i.test(lower)) {
      state.hiddenOnMovies = false;
      store(CONFIG.hideBtnKey, false);
      var btn2 = document.getElementById('fte-ai-btn');
      if (btn2) btn2.classList.remove('hidden-mode');
      addMessage('ai', 'AI button is now visible again.', false);
      setStatus('Ready', '#64748b');
      return;
    }

    // ── TURN OFF / DISABLE AI ASSISTANT (persists to DB for logged-in users) ──
    if (/turn off (the )?(ai|assistant)|disable (the )?(ai|assistant)|deactivate (the )?(ai|assistant)/i.test(lower)) {
      state.aiEnabled = false;
      store(CONFIG.aiEnabledKey, false);
      savePrefToDB('ai_enabled', false);
      addMessage('ai', 'AI Assistant turned off. It won\'t appear on any page until you re-enable it.' +
        (window.__fc_logged_in_user__ ? '<br><span style="color:#64748b;font-size:11px;">This preference is saved to your account.</span>' : '') +
        '<br><br>To re-enable, type <b>window.FTEAssistant.enable()</b> in the browser console, or clear site data.', false);
      setTimeout(function () { hideAssistantCompletely(); }, 2000);
      setStatus('Off', '#ef4444');
      return;
    }

    // ── TURN ON / ENABLE AI ASSISTANT ──
    if (/turn on (the )?(ai|assistant)|enable (the )?(ai|assistant)|activate (the )?(ai|assistant)/i.test(lower)) {
      state.aiEnabled = true;
      store(CONFIG.aiEnabledKey, true);
      savePrefToDB('ai_enabled', true);
      addMessage('ai', 'AI Assistant is now enabled on all pages!' +
        (window.__fc_logged_in_user__ ? '<br><span style="color:#64748b;font-size:11px;">Saved to your account.</span>' : ''), false);
      setStatus('Ready', '#64748b');
      return;
    }

    // ── MUTE / UNMUTE AI VOICE ──
    if (/mute (ai|voice|tts|speech|assistant)|turn off (voice|tts|speech|sound)/i.test(lower)) {
      state.muteTTS = true;
      store(CONFIG.muteTTSKey, true);
      savePrefToDB('ai_mute_tts', true);
      stopSpeaking();
      addMessage('ai', 'Voice responses muted. I\'ll only reply in text now. Say "unmute AI" to re-enable voice.', false);
      setStatus('Ready', '#64748b');
      return;
    }
    if (/unmute (ai|voice|tts|speech|assistant)|turn on (voice|tts|speech|sound)/i.test(lower)) {
      state.muteTTS = false;
      store(CONFIG.muteTTSKey, false);
      savePrefToDB('ai_mute_tts', false);
      addMessage('ai', 'Voice responses enabled! I\'ll speak my replies again.');
      setStatus('Ready', '#64748b');
      return;
    }

    // ── GUIDED FLOW INPUT ──
    if (state.flow) {
      state.processing = true;
      showStopBtn(true);
      addTypingIndicator();
      setStatus('Thinking...', '#a5b4fc');
      setTimeout(function () {
        if (state.cancelled) { state.cancelled = false; return; }
        removeTypingIndicator();
        handleFlowInput(lower, input);
      }, CONFIG.responseDelay);
      return;
    }

    // Show stop button + typing indicator
    state.processing = true;
    showStopBtn(true);
    addTypingIndicator();
    setStatus('Thinking...', '#a5b4fc');

    // ── MULTI-TASK DETECTION ──
    var tasks = splitMultiTask(lower, input);
    if (tasks.length > 1) {
      removeTypingIndicator();
      handleMultiTask(tasks);
      return;
    }

    // ── SINGLE TASK ROUTING ──
    setTimeout(function () {
      if (state.cancelled) { state.cancelled = false; return; }
      removeTypingIndicator();
      routeCommand(lower, input);
    }, CONFIG.responseDelay);
  }

  function splitMultiTask(lower, raw) {
    var delimiters = [' and also ', ' along with ', ', also ', ', plus ', ' as well as ', ' and then ', ', then '];
    for (var i = 0; i < delimiters.length; i++) {
      if (lower.indexOf(delimiters[i]) !== -1) {
        return raw.split(new RegExp(delimiters[i].trim(), 'i')).map(function (s) { return s.trim(); }).filter(Boolean);
      }
    }
    return [raw];
  }

  async function handleMultiTask(tasks) {
    addMessage('ai', 'I\'ll handle ' + tasks.length + ' requests for you. One moment...');
    for (var i = 0; i < tasks.length; i++) {
      if (state.cancelled) { state.cancelled = false; showStopBtn(false); return; }
      addMessage('system', 'Task ' + (i + 1) + '/' + tasks.length + ': ' + escapeHtml(tasks[i]));
      await routeCommandAsync(tasks[i].toLowerCase(), tasks[i]);
    }
    if (!state.cancelled) {
      addMessage('ai', 'All done! Anything else I can help with?');
    }
    state.processing = false;
    showStopBtn(false);
    setStatus('Ready', '#64748b');
  }

  // ═══════════════════════════════════════════════════════════
  // GUIDED CONVERSATION FLOW
  // ═══════════════════════════════════════════════════════════
  function handleFlowInput(lower, raw) {
    switch (state.flow) {

      // ── User chose what to do after "summarize current page" ──
      case 'awaiting_context_choice':
        if (/how (to|do i|does) (use|it|this)|overview|explain.*page|tutorial|walk me through/i.test(lower)) {
          state.flow = null;
          showPageOverview();
        } else if (state.flowData.section === 'stocks' && (/stock.*pick|today.*pick|give me.*pick|top.*pick/i.test(lower) ||
          /algorithm/i.test(lower) || /can.*slim/i.test(lower) || /momentum/i.test(lower) ||
          /risk/i.test(lower) || /up to date/i.test(lower))) {
          // Stock-specific flow routing
          state.flow = null;
          state.flowData = {};
          handleStocks(lower);
        } else if (/detail|feed|info|event|specific|give me|show me|what.*on|summar/i.test(lower)) {
          state.flow = null;
          startCategoryPicker();
        } else {
          // Exit flow, route normally
          state.flow = null;
          state.flowData = {};
          routeCommand(lower, raw);
        }
        break;

      // ── User picked an event category ──
      case 'awaiting_category':
        var category = parseEventType(lower);
        if (/all|everything|any|all events|show all|all types/i.test(lower)) {
          category = null; // all categories
        }
        if (category !== undefined) {
          state.flowData.category = category;
          state.flow = 'awaiting_timeframe';
          var catLabel = category ? category : 'all';
          addMessage('ai', '<b>' + capitalize(catLabel) + ' events</b> \u2014 what timeframe would you like?', false);
          setPrompts(['Today', 'This weekend', 'This week', 'This month', 'Next 3 months', 'Starting soon']);
          setStatus('Ready', '#64748b');
        } else {
          // Not a recognized category, exit flow and route normally
          state.flow = null;
          state.flowData = {};
          routeCommand(lower, raw);
        }
        break;

      // ── User picked a timeframe ──
      case 'awaiting_timeframe':
        var tf = parseTimeFilter(lower);
        if (/all|everything|any|upcoming/i.test(lower)) tf = null;
        state.flow = null;
        var flowCat = state.flowData.category;
        state.flowData = {};
        executeGuidedEventSearch(flowCat, tf);
        break;

      default:
        state.flow = null;
        state.flowData = {};
        routeCommand(lower, raw);
    }
  }

  function capitalize(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : 'All'; }

  function startCategoryPicker() {
    state.flow = 'awaiting_category';
    state.flowData = {};
    addMessage('ai', 'What category of events are you interested in? Pick one below, or type your own:', false);
    setPrompts(['Dating', 'Dancing', 'Music', 'Comedy', 'Networking', 'Food', 'Arts', 'Sports', 'Tech', 'Outdoor', 'Free events', 'All events']);
    setStatus('Ready', '#64748b');
  }

  function showPageOverview() {
    var section = detectSection();
    var html = '<div class="fte-ai-summary">';
    switch (section) {
      case 'events':
        html += '<b>\u{1F4CD} How to use the Events page</b><br><br>';
        html += '<b>Browse events:</b> Scroll through the feed to see Toronto events updated daily. Each card shows the event title, date, location, and a link to details/tickets.<br><br>';
        html += '<b>Filter & Search:</b> Use the category tabs at the top to filter by type (Dating, Music, Comedy, etc.). Adjust date ranges and price filters in Settings (\u2699\uFE0F).<br><br>';
        html += '<b>Save events:</b> Click the \u2764\uFE0F heart icon on any event card to save it to "My Collection".<br><br>';
        html += '<b>Export:</b> Use the Data Management section in Quick Nav (\u2630) to export as JSON, CSV, or Calendar (ICS) for Google/Apple Calendar.<br><br>';
        html += '<b>Quick Nav (\u2630):</b> Top-left hamburger menu \u2014 access all other sections (Stocks, Movies, Creators, VR, Accountability, etc.).<br><br>';
        html += '<b>AI Assistant:</b> That\'s me! Ask me anything \u2014 "dating events this weekend", "weather today", "top stock picks", etc.<br><br>';
        html += 'Want me to find specific events for you?';
        break;
      case 'stocks':
        html += '<b>\u{1F4CD} How to use Find Stocks</b><br><br>';
        html += 'View daily AI-validated stock picks from 11+ open-source algorithms. Picks are refreshed each trading day.<br><br>';
        html += '\u2022 Each pick shows: ticker, price, rating, risk level, and the algorithm that found it.<br>';
        html += '\u2022 Methodology includes CAN SLIM, Technical Momentum, Alpha Predator, and more.<br>';
        html += '\u2022 All picks are slippage-tested with realistic execution simulation.<br><br>';
        html += '<span style="color:#64748b;font-size:10px;">Not financial advice. Educational purposes only.</span>';
        break;
      case 'movies':
        html += '<b>\u{1F4CD} How to use Movies & TV</b><br><br>';
        html += 'Swipe through trailers TikTok-style. We have 3 versions:<br><br>';
        html += '\u2022 <b>V1</b> \u2014 Toronto theater info, IMDb + RT ratings, emoji reactions<br>';
        html += '\u2022 <b>V2</b> \u2014 TMDB integration, genre filters, playlist export<br>';
        html += '\u2022 <b>V3</b> \u2014 Full browse & search, user accounts, likes, queue<br><br>';
        html += 'Use the search bar in V3 to find specific movies or shows. Click any trailer to watch it.';
        break;
      case 'streamers':
        html += '<b>\u{1F4CD} How to use FavCreators</b><br><br>';
        html += 'Track your favorite content creators across TikTok, Twitch, Kick & YouTube.<br><br>';
        html += '\u2022 <b>Add creators</b> \u2014 Paste any creator URL or search by name<br>';
        html += '\u2022 <b>\u{1F534} Live status</b> \u2014 See who\'s streaming right now<br>';
        html += '\u2022 <b>Recent posts</b> \u2014 Latest content in one unified feed<br>';
        html += '\u2022 <b>Notifications</b> \u2014 Get alerted when favorites go live<br><br>';
        html += 'Sign in to save your creator list across devices.';
        break;
      case 'movies_v2':
        html += '<b>\u{1F4CD} How to use Movies & TV V2</b><br><br>';
        html += 'Browse movie and TV trailers with enhanced filtering.<br><br>';
        html += '\u2022 <b>Genre filters</b> \u2014 Filter by Action, Comedy, Drama, Horror, etc.<br>';
        html += '\u2022 <b>Playlist export/import</b> \u2014 Save your favorites and share them<br>';
        html += '\u2022 <b>TMDB integration</b> \u2014 Rich metadata from The Movie Database<br>';
        html += '\u2022 <b>Shareable links</b> \u2014 Send movie links to friends<br><br>';
        html += 'Swipe through trailers and click any to watch. Use V3 for full search.';
        break;
      case 'movies_v3':
        html += '<b>\u{1F4CD} How to use Movies & TV V3</b><br><br>';
        html += 'The full-featured movie and TV browsing experience.<br><br>';
        html += '\u2022 <b>Search</b> \u2014 Search any movie or TV show by name<br>';
        html += '\u2022 <b>User accounts</b> \u2014 Sign in to save likes and build a queue<br>';
        html += '\u2022 <b>Auto-scroll</b> \u2014 Trailers auto-play as you scroll<br>';
        html += '\u2022 <b>Personal queue</b> \u2014 Build a watch-later list<br>';
        html += '\u2022 <b>Likes</b> \u2014 Heart your favorites<br><br>';
        html += 'Use the search bar at the top to find specific titles.';
        break;
      case 'accountability':
        html += '<b>\u{1F4CD} How to use the Accountability Dashboard</b><br><br>';
        html += 'This is your personal system for building consistent habits \u2014 backed by behavioral science research.<br><br>';
        html += '<b>Getting Started:</b><br>';
        html += '\u2022 <b>Add a task</b> \u2014 Click "Add Task" and pick a type (Gym, Reading, Meditation, Custom)<br>';
        html += '\u2022 <b>Set your frequency</b> \u2014 How many times per week/month? (e.g., "4x per week")<br>';
        html += '\u2022 <b>Define success criteria</b> \u2014 What counts as a check-in? Be specific.<br>';
        html += '\u2022 <b>Add a punishment</b> \u2014 What happens if you miss? Loss aversion makes you 2x more likely to follow through.<br><br>';
        html += '<b>Daily Use:</b><br>';
        html += '\u2022 <b>\u2705 Check in</b> \u2014 Tap the check-in button when you complete your task<br>';
        html += '\u2022 <b>\u{1F525} Streaks</b> \u2014 Build consecutive days and earn streak tiers<br>';
        html += '\u2022 <b>\u{1F6E1}\uFE0F Shields</b> \u2014 Protect your streak on off days<br>';
        html += '\u2022 <b>\u23E9 Skip</b> \u2014 Log a skip with a reason (extends deadline by 1 day)<br><br>';
        html += '<b>Ask me:</b> "Am I behind?", "Give me a motivational push", "What\'s due today?", "My streaks"<br><br>';
        html += '<a href="/fc/motivation.html" target="_blank" style="color:#818cf8;">Read the science behind habit-building \u2192</a>';
        break;
      case 'wellness':
        html += '<b>\u{1F4CD} How to use Mental Health Resources</b><br><br>';
        html += 'Free tools for stress, anxiety, and crisis support.<br><br>';
        html += '\u2022 <b>Wellness games</b> \u2014 Breathing exercises, grounding techniques, guided meditation<br>';
        html += '\u2022 <b>Crisis support</b> \u2014 24/7 hotlines by country (Canada: 1-833-456-4566, Text HOME to 741741)<br>';
        html += '\u2022 <b>Global resources</b> \u2014 LGBTQ+, youth, veterans, and more<br>';
        html += '\u2022 <b>Self-care tools</b> \u2014 Journaling prompts, mood tracking, coping strategies<br><br>';
        html += '<b>If you\'re in crisis, please call 1-833-456-4566 or text HOME to 741741 now.</b>';
        break;
      case 'windowsfixer':
        html += '<b>\u{1F4CD} How to use Windows Boot Fixer</b><br><br>';
        html += 'A comprehensive recovery toolkit for Windows boot issues.<br><br>';
        html += '\u2022 <b>BSOD Fix</b> \u2014 Resolve INACCESSIBLE_BOOT_DEVICE and other blue screens<br>';
        html += '\u2022 <b>Boot Repair</b> \u2014 Fix corrupted bootloaders & MBR<br>';
        html += '\u2022 <b>Recovery</b> \u2014 Restore Windows when it won\'t start<br>';
        html += '\u2022 <b>Safe mode</b> \u2014 No data loss, works offline<br><br>';
        html += 'Free download. Works with Windows 10/11. Follow the step-by-step guides.';
        break;
      case 'stats':
        html += '<b>\u{1F4CD} How to use the Statistics Dashboard</b><br><br>';
        html += 'Monitor the health of event data sources and site metrics.<br><br>';
        html += '\u2022 <b>Source health</b> \u2014 See which event sources are active and responding<br>';
        html += '\u2022 <b>Event counts</b> \u2014 Total events by source and category<br>';
        html += '\u2022 <b>System status</b> \u2014 API health, database stats, and sync logs<br><br>';
        html += 'This dashboard is mainly for site administrators.';
        break;
      case 'vr':
        html += '<b>\u{1F4CD} How to use the VR Experience</b><br><br>';
        html += 'Explore Toronto events and apps in immersive WebXR.<br><br>';
        html += '\u2022 <b>Desktop</b> \u2014 Use WASD keys + mouse to look around<br>';
        html += '\u2022 <b>Quest 3</b> \u2014 Use controllers or hand tracking<br>';
        html += '\u2022 <b>Mobile</b> \u2014 Touch controls with streamlined UI<br>';
        html += '\u2022 <b>Zones</b> \u2014 Events Explorer, Movie Theater, Creators Lounge, Stocks Floor, Weather Observatory<br><br>';
        html += 'Works in any WebXR-capable browser. No app download needed.';
        break;
      default:
        html += '<b>\u{1F4CD} Page Overview</b><br><br>';
        html += 'This page is part of the findtorontoevents.ca network. Use the Quick Nav (\u2630) to explore Events, Stocks, Movies, Creators, VR, and more.';
    }
    html += '</div>';
    addMessage('ai', html, false);

    // Follow up with category picker on events page
    if (section === 'events') {
      speakText('Here\'s how the events page works. You can browse, filter, save, and export events. Want me to find specific events for you? Pick a category.');
      startCategoryPicker();
    } else {
      speakText('Here\'s an overview of this page. Let me know if you want more details or have a specific question.');
      setStatus('Ready', '#64748b');
    }
  }

  async function executeGuidedEventSearch(category, timeFilter) {
    // Reuse the main event handler logic
    var events = await loadEvents();
    if (!events || events.length === 0) {
      addMessage('ai', 'I couldn\'t load the events data. Please try refreshing the page.');
      setStatus('Ready', '#64748b');
      return;
    }
    var filtered = events;
    if (timeFilter) filtered = filterEventsByTime(filtered, timeFilter);
    else filtered = filterEventsByTime(filtered, null);
    if (category) filtered = filterEventsByType(filtered, category);
    filtered.sort(function (a, b) { return new Date(a.date) - new Date(b.date); });

    var timeLabel = getTimeLabel(timeFilter);
    var typeLabel = category ? category : 'all';
    renderEventResults(filtered, typeLabel, timeLabel);
  }

  // ═══════════════════════════════════════════════════════════
  // COMMAND ROUTER
  // ═══════════════════════════════════════════════════════════
  function routeCommand(lower, raw) {
    routeCommandAsync(lower, raw);
  }

  async function routeCommandAsync(lower, raw) {
    try {
      if (state.cancelled) { state.cancelled = false; showStopBtn(false); return; }

      // ── OPEN OFFERED CREATOR STREAM (affirmative responses) ──
      if (state.lastOfferedCreator && /^(yes[,.]?\s*(open it|please|do it)?|yeah|yep|sure|ok|okay|open( it)?|do it|go ahead|please|ye|ya|yea|absolutely|definitely|let'?s go|go for it)\s*!*\.?$/i.test(lower.trim())) {
        var offered = state.lastOfferedCreator;
        state.lastOfferedCreator = null;
        addMessage('ai', 'Opening <b>' + escapeHtml(offered.name) + '</b>\'s stream on ' + escapeHtml(offered.platform) + '...');
        speakText('Opening ' + offered.name + '\'s stream.');
        setTimeout(function () { window.open(offered.url, '_blank'); }, 600);
        setStatus('Ready', '#64748b');
        state.processing = false;
        showStopBtn(false);
        return;
      }
      // Clear offered creator if user says something else
      if (state.lastOfferedCreator && /^(no|nah|nope|not now|never mind|cancel|skip|no thanks|no thank)/i.test(lower.trim())) {
        state.lastOfferedCreator = null;
        addMessage('ai', 'No problem! Let me know if you need anything else.');
        setStatus('Ready', '#64748b');
        state.processing = false;
        showStopBtn(false);
        return;
      }
      state.lastOfferedCreator = null;

      // ── TUTORIAL / FIRST-TIME ──
      if (/enable (tutorial|first[- ]?time) mode/i.test(lower) || lower === 'tutorial' || lower === 'tutorial mode') {
        enableTutorialMode();
        return;
      }
      if (/disable (tutorial|first[- ]?time) mode/i.test(lower)) {
        disableTutorialMode();
        return;
      }

      // ── HELP ──
      if (lower === 'help' || lower === 'what can you do' || lower === 'commands' || lower.indexOf('what can you') !== -1) {
        showHelp();
        return;
      }

      // ── CONTEXT / SUMMARIZE CURRENT PAGE (conversational) ──
      if (/summarize (current|this) (context|page|section|view|feed)/i.test(lower) || lower === 'where am i' || lower === 'what page is this' || /summarize context/i.test(lower) || /what is this page/i.test(lower) || /describe this page/i.test(lower)) {
        summarizeContext();
        return;
      }

      // ── HOW TO USE (direct, no flow needed) ──
      if (/^how (to|do i) use (this|it|the page|this page)/i.test(lower) || /^how does (this|it) work/i.test(lower)) {
        showPageOverview();
        return;
      }

      // ── GIVE ME DETAILS / SUMMARIZE FEED (direct entry to category picker) ──
      if (/summarize (the )?(page )?feed/i.test(lower) || /give me (the )?details/i.test(lower) || /what('s| is) on (this|the) page/i.test(lower) || /show me what('s| is) (on|here)/i.test(lower)) {
        startCategoryPicker();
        return;
      }

      // ── EXPLAIN ICONS / MENU ──
      if (/explain (all )?(icons?|menu|buttons?|options?|navigation)/i.test(lower) || /what (are|do) (the|all) (icons?|buttons?|menu)/i.test(lower)) {
        explainIcons();
        return;
      }

      // ── PLACES SLASH COMMANDS (/places, /food, /find, /nearby, /open, /directions, /type:, /restrict:, etc.) ──
      if (_isPlacesSlashCommand(lower)) {
        await handlePlacesSlashCommand(lower, raw);
        return;
      }

      // ── DIRECTIONS (check before navigation to catch "how to get to X from Y", etc.) ──
      if (_isDirectionsQuery(lower)) {
        await handleDirections(lower);
        return;
      }

      // ── NAVIGATION ──
      if (/^(go to|open|take me to|navigate to|show me) /i.test(lower)) {
        handleNavigation(lower, raw);
        return;
      }

      // ── WEATHER (comprehensive patterns) ──
      if (/weather/i.test(lower) || /jacket/i.test(lower) || /temperature/i.test(lower) ||
        /umbrella/i.test(lower) || /forecast/i.test(lower) ||
        /will it (rain|snow|storm|hail|freeze|be (cold|warm|hot|nice|sunny|cloudy))/i.test(lower) ||
        /is it (rain|snow|cold|warm|hot|nice|sunny|cloudy|windy|humid|freezing)/i.test(lower) ||
        /any (rain|snow|precipitation|storm|wind)/i.test(lower) || /rain today/i.test(lower) || /snow today/i.test(lower) ||
        /precipitation/i.test(lower) || /do i need (a |an )?(jacket|umbrella|coat|sweater|hoodie|scarf|gloves|hat|sunscreen)/i.test(lower) ||
        /how (cold|warm|hot) is it/i.test(lower) || /what('s| is) it like outside/i.test(lower) ||
        /should i (bring|wear|take|pack)/i.test(lower) || /is it nice outside/i.test(lower) ||
        /chance of (rain|snow|storm)/i.test(lower) || /humidity/i.test(lower) || /wind/i.test(lower) ||
        /feels like/i.test(lower) || /weather (tomorrow|tonight|this (weekend|week))/i.test(lower) ||
        /^(high|low) today/i.test(lower) || /what should i wear/i.test(lower) ||
        /dress for (today|tomorrow|the weather)/i.test(lower) || /outdoor.*weather/i.test(lower)) {
        await handleWeather(lower);
        return;
      }

      // ── SET DEFAULT SEARCH PROVIDER ──
      var searchProvMatch = lower.match(/(?:make|set|change)\s+(?:my\s+)?(?:default\s+)?(?:search\s+)?(?:protocol|provider|engine)\s+(?:to\s+)?(google|foursquare|osm|openstreetmap)/i);
      if (!searchProvMatch) searchProvMatch = lower.match(/(?:default\s+search|search\s+default|search\s+provider|search\s+protocol)\s+(?:to\s+)?(google|foursquare|osm|openstreetmap)/i);
      if (!searchProvMatch) searchProvMatch = lower.match(/(?:use|switch\s+to)\s+(google|foursquare|osm|openstreetmap)\s+(?:by\s+default|as\s+default|for\s+search)/i);
      if (searchProvMatch) {
        var newProv = searchProvMatch[1].toLowerCase();
        if (newProv === 'osm' || newProv === 'openstreetmap') newProv = 'google';
        try { localStorage.setItem('fte_default_search_provider', newProv); } catch(e) {}
        var provLabel = newProv === 'google' ? 'Google (OpenStreetMap data + Google Maps links)' : 'Foursquare';
        addMessage('ai', '<div class="fte-ai-summary"><b>Default search provider updated!</b><br><br>' +
          'Your searches will now use <b>' + provLabel + '</b> by default.<br>' +
          'You can override per-search by saying "using google" or "using foursquare" in your query.<br><br>' +
          '<span style="color:#94a3b8;">Example: "coffee shops near me using foursquare"</span></div>');
        speakText('Default search provider set to ' + newProv + '.');
        setStatus('Ready', '#64748b');
        state.processing = false;
        showStopBtn(false);
        return;
      }

      // ── SET DEFAULT THEATER ──
      var theaterSetMatch = lower.match(/(?:make|set|change)\s+(?:my\s+)?(?:default\s+)?(?:theat(?:re|er)|cinema)\s+(?:to\s+)(.+)/i);
      if (!theaterSetMatch) theaterSetMatch = lower.match(/(?:default\s+theat(?:re|er)|my\s+theat(?:re|er))\s+(?:is|to)\s+(.+)/i);
      if (theaterSetMatch) {
        var newTheater = theaterSetMatch[1].trim().replace(/^["']/, '').replace(/["']$/, '');
        _setDefaultTheater(newTheater);
        addMessage('ai', '<div class="fte-ai-summary"><b>Default theater updated!</b><br><br>' +
          'Your default theater is now <b>' + escapeHtml(newTheater) + '</b>.<br>' +
          'Movie showtime queries will show times at this theater first.<br><br>' +
          '<a href="' + escapeHtml(_getTheaterShowtimeUrl(newTheater)) + '" target="_blank" style="color:#60a5fa;text-decoration:none;font-weight:600;">\uD83C\uDFAC View showtimes at ' + escapeHtml(newTheater) + '</a></div>');
        speakText('Default theater set to ' + newTheater + '.');
        setStatus('Ready', '#64748b');
        state.processing = false;
        showStopBtn(false);
        return;
      }

      // ── SET/CHANGE DEFAULT THEATER (bare, no theater name given) ──
      if (/(?:set|change|pick|choose|select)\s+(?:my\s+)?(?:default\s+)?(?:theat(?:re|er)|cinema)$/i.test(lower) ||
          /(?:set|change|pick|choose|select)\s+(?:(?:a|my)\s+)?(?:default|fav(?:ou?rite)?)\s+(?:theat(?:re|er)|cinema)$/i.test(lower)) {
        state.processing = true;
        showStopBtn(true);
        setStatus('Finding nearby theaters...', '#f59e0b');
        addMessage('ai', '<div id="fte-theater-picker-loading" class="fte-ai-summary"><b>Finding theaters near you...</b></div>', false);
        var pickLoc = await _getNearMeLocation();
        var pickLocParams = '';
        if (pickLoc && pickLoc.lat) pickLocParams = '&lat=' + pickLoc.lat + '&lng=' + pickLoc.lng;
        var pickData = { ok: false, results: [] };
        try {
          var pickResp = await fetch(CONFIG.nearMeApi + '?query=cinema&limit=6&provider=google' + pickLocParams);
          pickData = await pickResp.json();
        } catch(e) {}
        var pickEl = document.getElementById('fte-theater-picker-loading');
        var pickHtml = '<div class="fte-ai-summary">';
        var currentDefault = _getDefaultTheater();
        if (currentDefault) {
          pickHtml += '<div style="margin-bottom:8px;font-size:0.85rem;color:#94a3b8;">Current default: <b style="color:#fbbf24;">' + escapeHtml(currentDefault) + '</b></div>';
        }
        pickHtml += '<b>Pick your default theater:</b><br><br>';
        if (pickData.ok && pickData.results && pickData.results.length > 0) {
          for (var pi = 0; pi < pickData.results.length; pi++) {
            var pt = pickData.results[pi];
            var safePt = pt.name.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
            var isCurrentDefault = currentDefault && pt.name.toLowerCase() === currentDefault.toLowerCase();
            pickHtml += '<div style="margin-bottom:8px;padding:8px 10px;background:rgba(100,116,139,0.08);border-radius:8px;cursor:pointer;border-left:2px solid ' + (isCurrentDefault ? '#fbbf24' : '#64748b') + ';" onclick="__fteSetDefaultTheater(\'' + safePt + '\');this.parentElement.querySelectorAll(\'div[style]\').forEach(function(d){d.style.borderLeftColor=\'#64748b\'});this.style.borderLeftColor=\'#fbbf24\';this.querySelector(\'.fte-pick-status\').textContent=\'\u2605 Default\';this.querySelector(\'.fte-pick-status\').style.color=\'#fbbf24\'">';
            pickHtml += '<div style="display:flex;justify-content:space-between;align-items:center;">';
            pickHtml += '<b style="font-size:0.95rem;">' + escapeHtml(pt.name) + '</b>';
            pickHtml += '<span style="color:#a78bfa;font-size:0.8rem;margin-left:8px;">' + _formatDistance(pt.distance_m) + '</span>';
            pickHtml += '</div>';
            if (pt.address) pickHtml += '<div style="font-size:0.82rem;color:#94a3b8;">' + escapeHtml(pt.address) + '</div>';
            pickHtml += '<span class="fte-pick-status" style="font-size:0.8rem;color:' + (isCurrentDefault ? '#fbbf24' : '#6366f1') + ';">' + (isCurrentDefault ? '\u2605 Default' : 'Tap to select') + '</span>';
            pickHtml += '</div>';
          }
        } else {
          pickHtml += '<span style="color:#94a3b8;">Could not find theaters near you. Try saying "set my default theater to [theater name]".</span>';
        }
        pickHtml += '<div style="margin-top:8px;font-size:0.82rem;color:#94a3b8;">Or type: <b>"set my default theater to [name]"</b></div>';
        pickHtml += '</div>';
        if (pickEl) { pickEl.outerHTML = pickHtml; } else { addMessage('ai', pickHtml, false); }
        speakText(currentDefault ? 'Your current default is ' + currentDefault + '. Tap a theater to change it.' : 'Tap a theater to set it as your default.');
        setStatus('Ready', '#64748b');
        state.processing = false;
        showStopBtn(false);
        return;
      }

      // ── WHAT IS MY DEFAULT THEATER ──
      if (/(?:what|show|which)\s+(?:is\s+)?(?:my\s+)?(?:default\s+)?theat(?:re|er)/i.test(lower) && !/near|playing|showtime|movie/i.test(lower)) {
        var dt = _getDefaultTheater();
        if (dt) {
          addMessage('ai', '<div class="fte-ai-summary"><b>Your default theater:</b> ' + escapeHtml(dt) + '<br><br>' +
            '<a href="' + escapeHtml(_getTheaterShowtimeUrl(dt)) + '" target="_blank" style="color:#60a5fa;text-decoration:none;font-weight:600;">\uD83C\uDFAC View showtimes</a>' +
            ' <span style="margin-left:10px;color:#94a3b8;font-size:0.85rem;cursor:pointer;text-decoration:underline;" onclick="__fteSetDefaultTheater(\'\');this.parentElement.innerHTML=\'Default theater cleared. Next showtime search will use your nearest theater.\'">Clear default</span></div>');
        } else {
          addMessage('ai', '<div class="fte-ai-summary">You haven\'t set a default theater yet.<br><br>' +
            'Say <b>"set my default theater to Cineplex Yonge-Dundas"</b> or ask about movie showtimes \u2014 you can set a default from the results.</div>');
        }
        speakText(dt ? 'Your default theater is ' + dt + '.' : 'You haven\'t set a default theater yet.');
        setStatus('Ready', '#64748b');
        state.processing = false;
        showStopBtn(false);
        return;
      }

      // ── WORLD EVENTS / WHAT'S HAPPENING IN THE WORLD ──
      if (_isWorldEventsQuery(lower)) {
        await handleWorldEvents(lower);
        return;
      }

      // ── MOVIES NEAR ME / NOW PLAYING ──
      if (_isMovieShowtimesQuery(lower)) {
        await handleNowPlayingNearMe(lower, raw);
        return;
      }

      // ── BUSINESS VERIFY (is X still open?) ──
      if (_isBusinessVerifyQuery(lower)) {
        await handleBusinessVerify(lower);
        return;
      }

      // ── NEAR ME / PLACES / LOCATION FINDER ──
      if (_isNearMeQuery(lower)) {
        await handlePlaces(lower);
        return;
      }

      // ── EVENTS (comprehensive conversational patterns) ──
      if (/event/i.test(lower) || /dating/i.test(lower) || /dancing/i.test(lower) || /concert/i.test(lower) ||
        /festival/i.test(lower) || /comedy/i.test(lower) || /networking/i.test(lower) ||
        /things to do/i.test(lower) || /happenings/i.test(lower) || /activities/i.test(lower) ||
        /starting soon/i.test(lower) ||
        /what.*happening/i.test(lower) || /what.*going on/i.test(lower) || /near me/i.test(lower) ||
        /around here/i.test(lower) || /in (my |the )?area/i.test(lower) ||
        /what('s|s| is) on tonight/i.test(lower) || /tonight/i.test(lower) ||
        /anything fun/i.test(lower) || /something fun/i.test(lower) || /something to do/i.test(lower) ||
        /fun stuff/i.test(lower) || /fun things/i.test(lower) ||
        /good date idea/i.test(lower) || /date night/i.test(lower) || /romantic/i.test(lower) ||
        /singles/i.test(lower) || /mixer/i.test(lower) || /speed dat/i.test(lower) ||
        /brunch/i.test(lower) || /food event/i.test(lower) || /restaurant event/i.test(lower) ||
        /music event/i.test(lower) || /art (event|show|exhibit)/i.test(lower) ||
        /kid.*(friendly|event|activit)/i.test(lower) || /family.*(friendly|event|activit|fun)/i.test(lower) ||
        /free (event|thing|activit|stuff)/i.test(lower) || /cheap (event|thing|activit)/i.test(lower) ||
        /outdoor (event|activit|thing)/i.test(lower) || /hike|hiking/i.test(lower) ||
        /yoga|fitness|run|marathon/i.test(lower) || /tech (event|meetup)/i.test(lower) ||
        /startup|hackathon/i.test(lower) || /volunteer/i.test(lower) ||
        /open mic/i.test(lower) || /karaoke/i.test(lower) || /trivia/i.test(lower) ||
        /salsa|bachata|swing|ballroom/i.test(lower) ||
        /^what('s| is) (happening|on|up) /i.test(lower) ||
        /tomorrow/i.test(lower) || /next (weekend|week|friday|saturday|sunday)/i.test(lower) ||
        /this (weekend|week|friday|saturday|sunday|month)/i.test(lower) ||
        /upcoming/i.test(lower) || /what can i do/i.test(lower) ||
        /entertain/i.test(lower) || /nightlife/i.test(lower) || /bars?( |$)/i.test(lower) || /clubs?( |$)/i.test(lower) ||
        /party|parties/i.test(lower) || /rave/i.test(lower) || /dj set/i.test(lower) ||
        /museum|gallery|exhibit/i.test(lower) || /theatre|theater|musical/i.test(lower) || /\bplay\b.*\b(event|show|ticket|theatre|theater|perform)/i.test(lower) ||
        /sport|hockey|raptors|leafs|jays|tfc|argos/i.test(lower) ||
        /market|bazaar|fair/i.test(lower) || /christmas|holiday|halloween|valentine/i.test(lower) ||
        /pride|caribana|nuit blanche|tiff|luminato|cne/i.test(lower) ||
        /workshop|class|course|lesson|seminar/i.test(lower) ||
        /meditation|mindful|wellness.*event/i.test(lower) ||
        /book (club|reading|launch|signing)/i.test(lower) || /poetry/i.test(lower) ||
        /stand.?up|improv|comedy (show|night|club)/i.test(lower) ||
        /jazz|blues|rock|hip hop|edm|classical|orchestra|symphony/i.test(lower) ||
        /wine|beer|cocktail|tasting/i.test(lower) ||
        /pop.?up|food truck/i.test(lower) || /farmers.?market/i.test(lower) ||
        parsePostalCode(lower) !== null || parseAreaName(lower) !== null) {
        await handleEvents(lower);
        return;
      }

      // ── STOCKS (expanded) ──
      if (/stock/i.test(lower) || /pick/i.test(lower) || /trading/i.test(lower) || /investment/i.test(lower) ||
        /market/i.test(lower) || /portfolio/i.test(lower) || /ticker/i.test(lower) ||
        /dividend/i.test(lower) || /earning/i.test(lower) || /bull|bear/i.test(lower) ||
        /how.*market.*doing/i.test(lower) || /top.*gain/i.test(lower) ||
        /best.*buy/i.test(lower) || /stock.*tip/i.test(lower) || /stock.*recommend/i.test(lower) ||
        /what.*invest/i.test(lower) || /should i (buy|sell)/i.test(lower) ||
        /penny stock/i.test(lower) || /growth stock/i.test(lower) || /value stock/i.test(lower) ||
        /s&p|nasdaq|dow jones|tsx/i.test(lower) || /etf/i.test(lower) || /crypto/i.test(lower) ||
        /algo.*pick|algorithm.*pick/i.test(lower) || /can.*slim/i.test(lower) ||
        /momentum/i.test(lower) || /alpha predator/i.test(lower) ||
        /explain.*algorithm/i.test(lower) || /algorithm.*explain/i.test(lower) || /algorithm.*mean/i.test(lower) ||
        /what.*algorithm/i.test(lower) || /describe.*algorithm/i.test(lower) ||
        /what is (can slim|technical momentum|alpha predator|penny sniper|composite rating|ml ensemble|statistical arbitrage)/i.test(lower) ||
        /explain.*(can slim|technical momentum|alpha predator|penny sniper|composite rating|ml ensemble|statistical arbitrage)/i.test(lower) ||
        /risk level/i.test(lower) || /explain.*risk/i.test(lower) ||
        /up to date/i.test(lower) || /how old.*pick/i.test(lower) || /when.*pick.*update/i.test(lower) ||
        /penny sniper/i.test(lower) || /composite rating/i.test(lower) || /ml ensemble/i.test(lower) ||
        /statistical arbitrage/i.test(lower) || /slippage/i.test(lower)) {
        handleStocks(lower);
        return;
      }

      // ── STREAMERS / CREATORS (comprehensive) ──
      if (/stream/i.test(lower) || /creator/i.test(lower) || /twitch/i.test(lower) ||
        /kick\.com/i.test(lower) || /tiktok/i.test(lower) ||
        /refresh (my )?(fav|creator|streamer|live)/i.test(lower) ||
        /who('s| is) (live|streaming|on)/i.test(lower) || /anyone (live|streaming|on(line)?)/i.test(lower) ||
        /is anyone (live|streaming|on)/i.test(lower) || /anybody (live|streaming)/i.test(lower) ||
        /check (my )?(fav|creator|streamer|live)/i.test(lower) ||
        /new (content|post|video|song|upload)/i.test(lower) ||
        /any.*(content|post|video|song|upload).*creator/i.test(lower) ||
        /creator.*(content|post|video|song)/i.test(lower) ||
        /fav.*creator/i.test(lower) || /my creator/i.test(lower) ||
        /show.*creator/i.test(lower) || /list.*creator/i.test(lower) ||
        /who.*streaming/i.test(lower) || /who.*went live/i.test(lower) ||
        /recently live/i.test(lower) || /was.*(live|streaming)/i.test(lower) ||
        /latest.*(post|video|content|upload|song)/i.test(lower) ||
        /what.*creator.*post/i.test(lower) || /what.*creator.*upload/i.test(lower) ||
        /creator.*(update|news|activit)/i.test(lower) ||
        /scan.*(creator|live|stream)/i.test(lower) ||
        /live (status|check)/i.test(lower)) {
        await handleStreamers(lower);
        return;
      }

      // ── "live" on its own or "who is live" — route to streamers, but avoid matching "live music" etc ──
      if (/^(who'?s? live|check live|live now|live status)$/i.test(lower)) {
        await handleStreamers(lower);
        return;
      }

      // ── MOTIVATIONAL PUSH (before accountability so specific trigger matches first) ──
      if (/motivat|give me.*(push|boost|pep|tip)|inspire me|pep talk|random.*(tip|motiv)|i need.*(push|motivation|encouragement)/i.test(lower) ||
        /^(push|boost|motivate|inspire)$/i.test(lower)) {
        await handleAccountability(lower);
        return;
      }

      // ── ACCOUNTABILITY (expanded) ──
      if (/accountability/i.test(lower) || /my task/i.test(lower) || /my goal/i.test(lower) ||
        /my habit/i.test(lower) || /my progress/i.test(lower) ||
        /todo|to.?do list/i.test(lower) || /daily check/i.test(lower) ||
        /streak/i.test(lower) || /milestone/i.test(lower) ||
        /what.*i.*working on/i.test(lower) || /what.*i.*need to do/i.test(lower) ||
        /am i on track/i.test(lower) || /how.*i.*doing/i.test(lower) ||
        /show.*task/i.test(lower) || /accountability (dash|summar|report)/i.test(lower) ||
        /my deadline/i.test(lower) || /overdue/i.test(lower) || /due (today|soon|this week)/i.test(lower) ||
        /behind/i.test(lower) || /catch up/i.test(lower) || /how.*gym/i.test(lower) ||
        /haven'?t been/i.test(lower) || /haven'?t checked/i.test(lower) || /set up.*task/i.test(lower) ||
        /how.*(set up|create|add).*(task|goal)/i.test(lower)) {
        await handleAccountability(lower);
        return;
      }

      // ── MOVIES (expanded) ──
      // "play" and "watch" commands on movies pages should route here
      var _isOnMoviesPage = (function () { var s = detectSection(); return s === 'movies' || s === 'movies_v2' || s === 'movies_v3'; })();
      if (/movie/i.test(lower) || /trailer/i.test(lower) || /series/i.test(lower) ||
        /queue/i.test(lower) || /film/i.test(lower) || /cinema/i.test(lower) ||
        /what.*watch/i.test(lower) || /recommend.*(movie|show|film|series)/i.test(lower) ||
        /new (movie|release|film)/i.test(lower) || /popular (movie|show|film|series)/i.test(lower) ||
        /trending (movie|show|film|series)/i.test(lower) || /best (movie|show|film|series)/i.test(lower) ||
        /top (movie|show|film|series)/i.test(lower) || /movies? like/i.test(lower) ||
        /similar (to|movies|shows)/i.test(lower) || /showtime/i.test(lower) ||
        /where.*(watch|stream)/i.test(lower) || /watch.*(later|list|next)/i.test(lower) ||
        /binge/i.test(lower) || /netflix|disney|hulu|amazon prime|crave/i.test(lower) ||
        /documentary/i.test(lower) || /anime/i.test(lower) ||
        /horror (movie|film|show)/i.test(lower) || /action (movie|film|show)/i.test(lower) ||
        /romantic (movie|film|comedy)/i.test(lower) || /rom.?com/i.test(lower) ||
        /sci.?fi/i.test(lower) || /thriller/i.test(lower) || /drama/i.test(lower) ||
        (_isOnMoviesPage && /^(play|watch|find|search|look for|show me)\s+/i.test(lower))) {
        await handleMovies(lower, raw);
        return;
      }

      // ── "show" ambiguity: only match if it's about TV/movies, not "show me [something]" ──
      if (/^(tv )?show/i.test(lower) && !/show me|show (my|all|the )/i.test(lower)) {
        await handleMovies(lower, raw);
        return;
      }

      // ── TIME ──
      if (/what time/i.test(lower) || /current time/i.test(lower) || /what('s| is) the (date|day)/i.test(lower)) {
        var now = new Date();
        var dayName = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'][now.getDay()];
        addMessage('ai', 'It\'s <b>' + dayName + ', ' + formatDate(now) + '</b> at <b>' + formatTime(now) + '</b>.');
        setStatus('Ready', '#64748b');
        return;
      }

      // ── GREETINGS (expanded) ──
      if (/^(hi|hello|hey|good (morning|afternoon|evening|night)|sup|yo|howdy|what'?s up|hiya|heya|g'?day|bonjour|hola)$/i.test(lower) ||
        /^(hi|hello|hey|yo|howdy|hiya) (there|buddy|friend|pal|ai|assistant|bot)/i.test(lower)) {
        var hour = new Date().getHours();
        var greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
        var tips = [
          '"What\'s happening this weekend?"',
          '"Will it rain today?"',
          '"Refresh my creators"',
          '"Top stock picks"',
          '"Events near me tonight"',
          '"Good date ideas this weekend"',
          '"Anyone streaming right now?"'
        ];
        var tip = tips[Math.floor(Math.random() * tips.length)];
        addMessage('ai', greeting + '! I\'m your AI assistant for Toronto events, weather, creators, stocks, movies, and more.<br><br>Try: <b>' + tip + '</b>');
        setStatus('Ready', '#64748b');
        return;
      }

      // ── THANKS (expanded) ──
      if (/thank/i.test(lower) || /thanks/i.test(lower) || /^(ty|thx|cheers|appreciate|awesome|great job|nice|perfect|wonderful|excellent)/i.test(lower)) {
        var thankResponses = [
          'You\'re welcome! Let me know if you need anything else.',
          'Glad I could help! What else can I do for you?',
          'Anytime! Just ask if you need more info.',
          'Happy to help! Anything else on your mind?',
          'No problem! I\'m here whenever you need me.'
        ];
        addMessage('ai', thankResponses[Math.floor(Math.random() * thankResponses.length)]);
        setStatus('Ready', '#64748b');
        return;
      }

      // ── BYE (expanded) ──
      if (/^(bye|goodbye|see you|later|cya|peace|take care|gotta go|ttyl|g2g|brb|night|good night|nite)/i.test(lower)) {
        addMessage('ai', 'See you later! Enjoy exploring Toronto. I\'ll be here whenever you need me.');
        setStatus('Ready', '#64748b');
        return;
      }

      // ── WHO ARE YOU / ABOUT ──
      if (/who are you/i.test(lower) || /what are you/i.test(lower) || /tell me about yourself/i.test(lower) ||
        /about (this|the) (ai|assistant|bot)/i.test(lower) || /^about$/i.test(lower)) {
        addMessage('ai', '<div class="fte-ai-summary"><b>About the AI Assistant</b><br><br>' +
          'I\'m a free, client-side AI assistant built into findtorontoevents.ca. I run entirely in your browser \u2014 no API keys, no cloud AI, no data sent to third parties.<br><br>' +
          'I use pattern matching and your site\'s real data to help with:<br>' +
          '\u2022 Toronto events (search, filter, location-based)<br>' +
          '\u2022 <b>Restaurants & places</b> (dietary restrictions, open late, near you)<br>' +
          '\u2022 Weather forecasts and jacket recommendations<br>' +
          '\u2022 Creator live status and new content<br>' +
          '\u2022 Stock picks and methodology<br>' +
          '\u2022 Movie/TV browsing and trailer queuing<br>' +
          '\u2022 Accountability tasks and goal tracking<br>' +
          '\u2022 Site navigation and page explanations<br><br>' +
          'I can talk to you via text or voice. Click the mic button to speak, or type below.</div>');
        setStatus('Ready', '#64748b');
        return;
      }

      // ── WHAT'S NEW / TRENDING ──
      if (/what'?s new/i.test(lower) || /what'?s trending/i.test(lower) || /what'?s popular/i.test(lower) ||
        /^trending$/i.test(lower) || /^popular$/i.test(lower) || /^new$/i.test(lower)) {
        addMessage('ai', 'Here\'s what I can check for you right now:' +
          '<div style="margin-top:8px;font-size:12px;">' +
          '\u2022 <b>"Events this weekend"</b> \u2014 what\'s happening in Toronto<br>' +
          '\u2022 <b>"Who is live?"</b> \u2014 check if your creators are streaming<br>' +
          '\u2022 <b>"New content from creators"</b> \u2014 recent posts and videos<br>' +
          '\u2022 <b>"Top stock picks"</b> \u2014 today\'s algorithmic picks<br>' +
          '\u2022 <b>"Trending movies"</b> \u2014 popular trailers</div>');
        setPrompts(['Events this weekend', 'Restaurants near me', 'Who is live?', 'Top stock picks', 'Late night food']);
        setStatus('Ready', '#64748b');
        return;
      }

      // ── RECOMMENDATIONS / SUGGESTIONS ──
      if (/recommend/i.test(lower) || /suggest/i.test(lower) || /^ideas$/i.test(lower) ||
        /what should i/i.test(lower) || /help me find/i.test(lower) || /i('m| am) bored/i.test(lower) ||
        /give me something/i.test(lower)) {
        var section = detectSection();
        var recHtml = 'Based on where you are, here are some ideas:<br><br>';
        if (section === 'events' || section === 'default') {
          recHtml += '\u2022 <b>"Fun things to do this weekend"</b><br>';
          recHtml += '\u2022 <b>"Good date ideas tonight"</b><br>';
          recHtml += '\u2022 <b>"Free events this week"</b><br>';
          recHtml += '\u2022 <b>"Live music tonight"</b><br>';
        } else if (section === 'streamers') {
          recHtml += '\u2022 <b>"Refresh my creators"</b> \u2014 check who\'s live<br>';
          recHtml += '\u2022 <b>"New content past 48 hours"</b><br>';
        } else if (section === 'stocks') {
          recHtml += '\u2022 <b>"Give me today\'s stock picks"</b><br>';
          recHtml += '\u2022 <b>"Explain what the algorithms each mean"</b><br>';
          recHtml += '\u2022 <b>"Are these picks up to date?"</b><br>';
          recHtml += '\u2022 <b>"What is CAN SLIM?"</b><br>';
        }
        recHtml += '\u2022 <b>"Weather today"</b> \u2014 always useful!<br>';
        recHtml += '\u2022 <b>"Summarize current page"</b> \u2014 I\'ll walk you through it';
        addMessage('ai', recHtml);
        setStatus('Ready', '#64748b');
        return;
      }

      // ── DEFAULT (enriched) ──
      addMessage('ai', 'I\'m not sure how to help with that, but I can assist with a lot! Here are some ideas:' +
        '<div style="margin-top:8px;font-size:12px;">' +
        '\u2022 <b>Events</b>: "What\'s happening this weekend?" / "Good date ideas tonight"<br>' +
        '\u2022 <b>Near you</b>: "Events near me today" / "Events at M5G 2H5"<br>' +
        '\u2022 <b>Restaurants</b>: "Vegan near me" / "Halal near Yonge and Dundas" / "Late night food"<br>' +
        '\u2022 <b>Weather</b>: "Will it rain today?" / "Do I need a jacket?" / "7-day forecast"<br>' +
        '\u2022 <b>Creators</b>: "Refresh my creators" / "Who is live?" / "New content this week"<br>' +
        '\u2022 <b>Stocks</b>: "Top stock picks" / "How are picks chosen?"<br>' +
        '\u2022 <b>Movies</b>: "Queue Avatar trailers" / "Trending movies"<br>' +
        '\u2022 <b>Tasks</b>: "Show my accountability tasks"<br>' +
        '\u2022 <b>Navigate</b>: "Go to VR" / "Open FavCreators"<br>' +
        '\u2022 <b>Page info</b>: "Summarize current page" / "How to use this"<br>' +
        '\u2022 Say <b>"help"</b> for the complete command list</div>');
      setStatus('Ready', '#64748b');

    } catch (err) {
      console.error('[AI Assistant] Error:', err);
      addMessage('ai', 'Sorry, something went wrong. Please try again.');
      setStatus('Ready', '#64748b');
    }
  }

  // ═══════════════════════════════════════════════════════════
  // HANDLERS: EVENTS (with location awareness)
  // ═══════════════════════════════════════════════════════════
  async function loadEvents() {
    if (state.eventsLoaded && state.eventsData) return state.eventsData;
    if (window.__RAW_EVENTS__ && window.__RAW_EVENTS__.length > 0) {
      state.eventsData = window.__RAW_EVENTS__;
      state.eventsLoaded = true;
      return state.eventsData;
    }
    for (var i = 0; i < CONFIG.eventsJsonPaths.length; i++) {
      try {
        var resp = await fetch(CONFIG.eventsJsonPaths[i]);
        if (resp.ok) {
          var data = await resp.json();
          state.eventsData = data.events || data;
          state.eventsLoaded = true;
          return state.eventsData;
        }
      } catch (e) { /* try next */ }
    }
    return [];
  }

  function classifyEventType(event) {
    var text = ((event.title || '') + ' ' + (event.description || '') + ' ' + ((event.categories || []).join(' ')) + ' ' + ((event.tags || []).join(' '))).toLowerCase();
    if (/dating|singles|speed dat|mingle|mixer|matchmak|love|romantic|couples|relationship/.test(text)) return 'dating';
    if (/danc|salsa|bachata|kizomba|swing|ballroom|hip hop dance|dance class|dance party|dance night/.test(text)) return 'dancing';
    if (/concert|music|dj|live band|jazz|rock|hip hop|rap|edm|karaoke|open mic|sing/.test(text)) return 'music';
    if (/comedy|standup|stand-up|improv|laugh|comic|funny/.test(text)) return 'comedy';
    if (/network|professional|business|entrepreneur|startup|career|job fair/.test(text)) return 'networking';
    if (/food|restaurant|chef|tast|brunch|dinner|cook|culinary|wine|beer|cocktail/.test(text)) return 'food';
    if (/art|gallery|exhibit|paint|sculpt|museum|theatre|theater|play|performance|opera|ballet/.test(text)) return 'arts';
    if (/sport|hockey|baseball|basketball|soccer|football|run|marathon|fitness|gym|yoga/.test(text)) return 'sports';
    if (/tech|hack|startup|code|ai|digital|gaming|game|esport/.test(text)) return 'tech';
    if (/festival|fair|carnival|parade|market|bazaar/.test(text)) return 'festival';
    if (/outdoor|hike|park|garden|trail|walk|bike|cycling|nature/.test(text)) return 'outdoor';
    if (/wellness|mental health|meditation|mindful|self-care|therapy|support group/.test(text)) return 'wellness';
    if (/family|kids|children|youth|teen/.test(text)) return 'family';
    if (/film|movie|screen|cinema|documentary/.test(text)) return 'film';
    if (/free|no cost|complimentary/.test(text) || event.isFree) return 'free';
    return 'general';
  }

  function parseTimeFilter(lower) {
    if (/starting soon|happening soon|next (few )?hours?|right now|happening now/.test(lower)) return 'soon';
    if (/today|tonight|this evening|this morning|this afternoon/.test(lower)) return 'today';
    if (/this weekend|on the weekend|saturday|sunday/.test(lower)) return 'weekend';
    if (/this week|next 7 days/.test(lower)) return 'week';
    if (/this month|next 30 days/.test(lower)) return 'month';
    if (/next 3 months|next three months|coming months|upcoming months/.test(lower)) return '3months';
    if (/tomorrow/.test(lower)) return 'tomorrow';
    return null;
  }

  function parseEventType(lower) {
    if (/dating|singles|mingle|mixer/.test(lower)) return 'dating';
    if (/danc/.test(lower)) return 'dancing';
    if (/concert|music|live band|dj/.test(lower)) return 'music';
    if (/comedy|standup|improv/.test(lower)) return 'comedy';
    if (/network|professional|business/.test(lower)) return 'networking';
    if (/food|restaurant|brunch|dinner/.test(lower)) return 'food';
    if (/art|gallery|exhibit|theatre|theater/.test(lower)) return 'arts';
    if (/sport|hockey|basketball|soccer|football/.test(lower)) return 'sports';
    if (/tech|hack|gaming|game/.test(lower)) return 'tech';
    if (/festival|fair|market/.test(lower)) return 'festival';
    if (/outdoor|hike|park|nature/.test(lower)) return 'outdoor';
    if (/wellness|mental health|meditation/.test(lower)) return 'wellness';
    if (/family|kids|children/.test(lower)) return 'family';
    if (/free/.test(lower)) return 'free';
    if (/film|movie|cinema/.test(lower)) return 'film';
    return null;
  }

  function filterEventsByTime(events, filter) {
    var now = new Date();
    return events.filter(function (ev) {
      var d = new Date(ev.date);
      if (isNaN(d.getTime())) return false;
      switch (filter) {
        case 'soon': return isStartingSoon(d);
        case 'today': return isToday(d);
        case 'tomorrow': return isTomorrow(d);
        case 'weekend': return isThisWeekend(d) && isFutureOrToday(d);
        case 'week': return isThisWeek(d) && isFutureOrToday(d);
        case 'month': return isThisMonth(d) && isFutureOrToday(d);
        case '3months': return isNext3Months(d);
        default: return isFutureOrToday(d);
      }
    });
  }

  function filterEventsByType(events, type) {
    if (!type) return events;
    return events.filter(function (ev) {
      return classifyEventType(ev) === type;
    });
  }

  function getTimeLabel(tf) {
    return tf === 'soon' ? 'starting soon' :
      tf === 'today' ? 'today' :
        tf === 'tomorrow' ? 'tomorrow' :
          tf === 'weekend' ? 'this weekend' :
            tf === 'week' ? 'this week' :
              tf === 'month' ? 'this month' :
                tf === '3months' ? 'in the next 3 months' : 'upcoming';
  }

  function renderEventResults(filtered, typeLabel, timeLabel, locationLabel) {
    if (filtered.length === 0) {
      var msg = 'I found <b>0 ' + typeLabel + ' events ' + timeLabel + '</b>';
      if (locationLabel) msg += ' near <b>' + escapeHtml(locationLabel) + '</b>';
      msg += '. Try broadening your search \u2014 for example, "Show me all events this week".';
      addMessage('ai', msg);
      setStatus('Ready', '#64748b');
      return;
    }

    var maxShow = 8;
    var showing = filtered.slice(0, maxShow);
    var html = '<div class="fte-ai-summary">';
    html += '<b>' + filtered.length + ' ' + typeLabel + ' event' + (filtered.length !== 1 ? 's' : '') + ' ' + timeLabel;
    if (locationLabel) html += ' near ' + escapeHtml(locationLabel);
    html += ':</b><br><br>';

    for (var i = 0; i < showing.length; i++) {
      var ev = showing[i];
      var d = new Date(ev.date);
      var dateStr = isNaN(d.getTime()) ? '' : formatDate(d) + ' ' + formatTime(d);
      html += '<div class="event-item">';
      html += '<b>' + escapeHtml(ev.title) + '</b><br>';
      html += '<span style="color:#94a3b8;font-size:11px;">' + dateStr;
      if (ev.location) html += ' \u2022 ' + escapeHtml(ev.location);
      if (ev.price && ev.price !== 'See Article' && ev.price !== 'See Tickets') html += ' \u2022 ' + escapeHtml(ev.price);
      if (ev.isFree) html += ' \u2022 <span style="color:#22c55e;">FREE</span>';
      html += '</span>';
      if (ev.url) html += '<br><a href="' + escapeHtml(ev.url) + '" target="_blank" rel="noopener">Details \u2192</a>';
      html += '</div>';
    }

    if (filtered.length > maxShow) {
      html += '<br><span style="color:#64748b;font-size:11px;">Showing ' + maxShow + ' of ' + filtered.length + ' events. Browse the full list on the events page.</span>';
    }

    // Add "find food nearby" suggestion
    html += '<div style="margin-top:8px;padding:6px 8px;background:rgba(139,92,246,0.08);border:1px solid rgba(139,92,246,0.15);border-radius:6px;font-size:0.75rem;color:#a5b4fc;">';
    html += '\u{1F37D}\uFE0F Need food before or after? Try: <b>"restaurants near me"</b>';
    if (locationLabel) html += ' or <b>"food near ' + escapeHtml(locationLabel) + '"</b>';
    html += '</div>';

    html += '</div>';

    addMessage('ai', html, false);
    var speechText = 'I found ' + filtered.length + ' ' + typeLabel + ' events ' + timeLabel + '. ';
    if (locationLabel) speechText += 'near ' + locationLabel + '. ';
    if (showing.length > 0) {
      speechText += 'Here are the top ones: ';
      for (var j = 0; j < Math.min(3, showing.length); j++) {
        speechText += showing[j].title + '. ';
      }
    }
    speakText(speechText);
    setStatus('Ready', '#64748b');
  }

  async function handleEvents(lower) {
    var events = await loadEvents();
    if (!events || events.length === 0) {
      addMessage('ai', 'I couldn\'t load the events data. Please try refreshing the page.');
      setStatus('Ready', '#64748b');
      return;
    }

    var timeFilter = parseTimeFilter(lower);
    var eventType = parseEventType(lower);
    var locationLabel = null;

    // ── LOCATION: "near me" ──
    if (/near me|around here|close to me|in my area|nearby/i.test(lower)) {
      addMessage('ai', '\u{1F4CD} Getting your location...', false);
      var loc = await getUserLocation();
      if (!loc) {
        addMessage('ai', '<div class="fte-ai-summary">' +
          '<b>\u{1F4CD} Location not available</b><br><br>' +
          'I couldn\'t get your location. To enable it:<br><br>' +
          '<b>Chrome:</b> Click the lock/info icon in the address bar \u2192 Site settings \u2192 Location \u2192 Allow<br>' +
          '<b>Firefox:</b> Click the lock icon \u2192 Permissions \u2192 Access Your Location \u2192 Allow<br>' +
          '<b>Safari:</b> Preferences \u2192 Websites \u2192 Location \u2192 Allow<br>' +
          '<b>Mobile:</b> Make sure Location Services are on in your phone settings<br><br>' +
          'Or try: "events in <b>downtown</b>" or "events at <b>M5G 2H5</b>" instead.</div>', false);
        setStatus('Ready', '#64748b');
        return;
      }
      // Find closest known area
      var closestArea = null;
      var closestDist = Infinity;
      for (var areaName in TORONTO_AREAS) {
        var a = TORONTO_AREAS[areaName];
        var dist = haversineKm(loc.lat, loc.lon, a.lat, a.lon);
        if (dist < closestDist) { closestDist = dist; closestArea = a; }
      }
      if (closestArea) locationLabel = closestArea.label;
      else locationLabel = 'your area';
    }

    // ── LOCATION: postal code ──
    if (!locationLabel) {
      var postal = parsePostalCode(lower);
      if (postal) {
        addMessage('ai', '\u{1F4CD} Looking up postal code <b>' + escapeHtml(postal) + '</b>...', false);
        var geoResult = await geocodePostalCode(postal);
        if (geoResult) {
          // Find closest known area to the postal code
          var closestArea2 = null;
          var closestDist2 = Infinity;
          for (var areaName2 in TORONTO_AREAS) {
            var a2 = TORONTO_AREAS[areaName2];
            var dist2 = haversineKm(geoResult.lat, geoResult.lon, a2.lat, a2.lon);
            if (dist2 < closestDist2) { closestDist2 = dist2; closestArea2 = a2; }
          }
          locationLabel = closestArea2 ? closestArea2.label + ' (' + postal + ')' : postal + ' area';
        } else {
          locationLabel = postal + ' area';
        }
      }
    }

    // ── LOCATION: area name ──
    if (!locationLabel) {
      var area = parseAreaName(lower);
      if (area) locationLabel = area.label;
    }

    // Apply filters
    var filtered = events;
    if (timeFilter) filtered = filterEventsByTime(filtered, timeFilter);
    else filtered = filterEventsByTime(filtered, null);
    if (eventType) filtered = filterEventsByType(filtered, eventType);

    // Apply location filter
    if (locationLabel) {
      var locationFiltered = filterEventsByLocation(filtered, locationLabel);
      if (locationFiltered.length > 0) {
        filtered = locationFiltered;
      } else {
        // No exact match, show all events but mention location
        addMessage('ai', '<span style="color:#fbbf24;font-size:11px;">\u26A0 No events specifically mention "' + escapeHtml(locationLabel) + '" \u2014 showing all Toronto events instead.</span>', false);
      }
    }

    filtered.sort(function (a, b) { return new Date(a.date) - new Date(b.date); });
    var timeLabel = getTimeLabel(timeFilter);
    var typeLabel = eventType ? eventType : 'all';
    renderEventResults(filtered, typeLabel, timeLabel, locationLabel);
  }

  // ═══════════════════════════════════════════════════════════
  // HANDLERS: PLACES / RESTAURANTS (Foursquare)
  // ═══════════════════════════════════════════════════════════
  async function handlePlaces(lower) {
    state.processing = true;
    showStopBtn(true);
    setStatus('Searching nearby places...', '#f59e0b');

    try {
      // ── Parse location from query ──
      var ll = '';
      var near = '';
      var locationLabel = 'downtown Toronto';

      // Check for postal code
      var postal = parsePostalCode(lower);
      if (postal) {
        var geo = await geocodePostalCode(postal);
        if (geo) {
          ll = geo.lat + ',' + geo.lon;
          locationLabel = postal.toUpperCase();
        }
      }

      // Check for "near me" / geolocation
      if (!ll && /near me|around here|close to me|nearby|in my area/i.test(lower)) {
        var userLoc = await getUserLocation();
        if (userLoc) {
          ll = userLoc.lat + ',' + userLoc.lon;
          locationLabel = 'your location';
        }
      }

      // Check for intersection / landmark ("near Yonge and Dundas", "at King and Bathurst")
      if (!ll) {
        var intersectionMatch = lower.match(/(?:near|at|around|by|close to|in)\s+([a-z]+(?:\s+(?:and|&|st|street|ave|avenue|rd|road|blvd|boulevard))?(?:\s+(?:and|&)\s+[a-z]+(?:\s+(?:st|street|ave|avenue|rd|road|blvd|boulevard))?)?)/i);
        if (intersectionMatch) {
          var placeName = intersectionMatch[1].trim();
          // Check known areas first
          var areaKey = placeName.replace(/\s+/g, ' ').toLowerCase();
          if (TORONTO_AREAS[areaKey]) {
            ll = TORONTO_AREAS[areaKey].lat + ',' + TORONTO_AREAS[areaKey].lon;
            locationLabel = TORONTO_AREAS[areaKey].label;
          } else {
            // Use it as a "near" query for Foursquare
            near = placeName + ', Toronto';
            locationLabel = placeName;
          }
        }
      }

      // Check for known area names in the query
      if (!ll && !near) {
        var area = parseAreaName(lower);
        if (area && TORONTO_AREAS[area]) {
          ll = TORONTO_AREAS[area].lat + ',' + TORONTO_AREAS[area].lon;
          locationLabel = TORONTO_AREAS[area].label;
        }
      }

      // Default to downtown Toronto
      if (!ll && !near) {
        ll = '43.6532,-79.3832';
      }

      // ── Parse food type / dietary restriction from query ──
      var query = '';
      var dietaryNote = '';

      // Dietary restrictions
      if (/vegan/i.test(lower)) { query = 'vegan'; dietaryNote = 'vegan'; }
      else if (/vegetarian/i.test(lower)) { query = 'vegetarian'; dietaryNote = 'vegetarian'; }
      else if (/halal/i.test(lower)) { query = 'halal'; dietaryNote = 'halal'; }
      else if (/kosher/i.test(lower)) { query = 'kosher'; dietaryNote = 'kosher'; }
      else if (/gluten.?free/i.test(lower)) { query = 'gluten free'; dietaryNote = 'gluten-free'; }
      else if (/dairy.?free/i.test(lower)) { query = 'dairy free'; dietaryNote = 'dairy-free'; }
      else if (/keto/i.test(lower)) { query = 'keto'; dietaryNote = 'keto-friendly'; }
      // Cuisine types
      else if (/pizza/i.test(lower)) query = 'pizza';
      else if (/sushi/i.test(lower)) query = 'sushi';
      else if (/ramen/i.test(lower)) query = 'ramen';
      else if (/pho/i.test(lower)) query = 'pho';
      else if (/burger/i.test(lower)) query = 'burgers';
      else if (/taco/i.test(lower)) query = 'tacos';
      else if (/thai/i.test(lower)) query = 'thai';
      else if (/indian/i.test(lower)) query = 'indian';
      else if (/chinese/i.test(lower)) query = 'chinese';
      else if (/korean/i.test(lower)) query = 'korean';
      else if (/japanese/i.test(lower)) query = 'japanese';
      else if (/italian/i.test(lower)) query = 'italian';
      else if (/greek/i.test(lower)) query = 'greek';
      else if (/mexican/i.test(lower)) query = 'mexican';
      else if (/vietnamese/i.test(lower)) query = 'vietnamese';
      else if (/ethiopian/i.test(lower)) query = 'ethiopian';
      else if (/caribbean/i.test(lower)) query = 'caribbean';
      else if (/middle eastern|shawarma|falafel/i.test(lower)) query = 'middle eastern';
      else if (/mediterranean/i.test(lower)) query = 'mediterranean';
      else if (/persian/i.test(lower)) query = 'persian';
      else if (/turkish/i.test(lower)) query = 'turkish';
      else if (/lebanese/i.test(lower)) query = 'lebanese';
      else if (/wings|fried chicken/i.test(lower)) query = 'fried chicken';
      else if (/bbq|barbecue/i.test(lower)) query = 'bbq';
      else if (/steak/i.test(lower)) query = 'steakhouse';
      else if (/seafood/i.test(lower)) query = 'seafood';
      else if (/breakfast/i.test(lower)) query = 'breakfast';
      else if (/brunch/i.test(lower)) query = 'brunch';
      else if (/dessert|ice cream|bakery/i.test(lower)) query = 'dessert';
      else if (/bubble tea|boba/i.test(lower)) query = 'bubble tea';
      else if (/coffee|cafe/i.test(lower)) query = 'coffee';
      else if (/bar|pub/i.test(lower)) query = 'bar';
      else if (/fine dining/i.test(lower)) query = 'fine dining';
      else if (/cheap eat|affordable/i.test(lower)) query = 'cheap eats';
      else if (/patio/i.test(lower)) query = 'patio restaurant';
      else if (/diner/i.test(lower)) query = 'diner';
      else if (/late.?night|after.?hours|24.?hour|open (late|all night|24)/i.test(lower)) query = 'late night food';
      else query = 'restaurant';

      // ── Build API URL ──
      var openNow = '';
      if (/open now/i.test(lower) || /open late/i.test(lower) || /open right now/i.test(lower)) {
        openNow = '1';
      }

      var apiUrl = CONFIG.nearMeApi + '?query=' + encodeURIComponent(query) + '&limit=10';
      if (ll) {
        var llParts = ll.split(',');
        apiUrl += '&lat=' + llParts[0] + '&lng=' + llParts[1];
      }
      if (near) apiUrl += '&location=' + encodeURIComponent(near);
      if (openNow) apiUrl += '&open_now=true';
      if (dietaryNote) apiUrl += '&dietary=' + encodeURIComponent(dietaryNote);

      showLoadingBar('Searching for ' + query + '...');
      updateLoadingBar(30);

      var resp = await fetch(apiUrl);
      var data = await resp.json();

      updateLoadingBar(90);

      var results = (data && data.results) ? data.results : [];
      if (!data || !data.ok || results.length === 0) {
        removeLoadingBar();
        addMessage('ai', '<div class="fte-ai-summary"><b>\u{1F37D}\uFE0F No results</b><br><br>' +
          'I couldn\'t find any <b>' + escapeHtml(query) + '</b> places near <b>' + escapeHtml(locationLabel) + '</b>.<br><br>' +
          'Try a different cuisine, location, or broader search like <b>"restaurants near me"</b>.</div>');
        setStatus('Ready', '#64748b');
        state.processing = false;
        showStopBtn(false);
        return;
      }

      removeLoadingBar();

      // ── Build results HTML ──
      var title = query.charAt(0).toUpperCase() + query.slice(1);
      if (dietaryNote) title = dietaryNote.charAt(0).toUpperCase() + dietaryNote.slice(1) + ' options';

      var html = '<div class="fte-ai-summary">';
      html += '<b>\u{1F37D}\uFE0F ' + escapeHtml(title) + ' near ' + escapeHtml(locationLabel) + '</b>';
      html += ' <span style="color:#64748b;font-size:0.75rem;">(' + results.length + ' found)</span><br><br>';

      for (var i = 0; i < results.length; i++) {
        var v = results[i];
        var distText = '';
        if (v.distance_m !== null && v.distance_m !== undefined) {
          if (v.distance_m < 1000) {
            distText = v.distance_m + 'm';
          } else {
            distText = (v.distance_m / 1000).toFixed(1) + 'km';
          }
        }
        var catText = v.category || '';

        html += '<div style="padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.06);">';
        html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;">';
        html += '<b style="color:#f8fafc;">' + (i + 1) + '. ' + escapeHtml(v.name) + '</b>';
        if (distText) {
          html += '<span style="color:#64748b;font-size:0.75rem;white-space:nowrap;margin-left:8px;">\u{1F4CD} ' + distText + '</span>';
        }
        html += '</div>';
        if (catText) {
          html += '<div style="font-size:0.75rem;color:#8b5cf6;">' + escapeHtml(catText) + '</div>';
        }
        if (v.open_now === true) {
          html += '<span style="color:#86efac;font-size:0.75rem;">\u2714 Open now</span> ';
        } else if (v.open_now === false) {
          html += '<span style="color:#f87171;font-size:0.75rem;">Closed</span> ';
        }
        if (v.rating && v.rating > 0) {
          html += '<span style="color:#fbbf24;font-size:0.75rem;">\u2605 ' + (v.rating / 1).toFixed(1) + '/10</span> ';
        }
        if (v.address) {
          html += '<div style="font-size:0.75rem;color:#94a3b8;">\u{1F4CD} ' + escapeHtml(v.address) + '</div>';
        }
        if (v.phone) {
          html += '<div style="font-size:0.75rem;color:#94a3b8;">\u260E ' + escapeHtml(v.phone) + '</div>';
        }
        // Google Maps link
        if (v.maps_url) {
          html += '<a href="' + escapeHtml(v.maps_url) + '" target="_blank" style="font-size:0.7rem;color:#818cf8;text-decoration:none;">Open in Google Maps \u2197</a>';
        }
        html += '</div>';
      }

      html += '<div style="margin-top:10px;font-size:0.72rem;color:#475569;">';
      html += 'Powered by Foursquare \u2022 Try: <b>"vegan near me"</b>, <b>"halal near M5B 2H1"</b>, <b>"late night food near Yonge and Dundas"</b>';
      html += '</div>';
      html += '</div>';

      addMessage('ai', html, false);

      var speakCount = Math.min(results.length, 3);
      var speakNames = [];
      for (var si = 0; si < speakCount; si++) {
        speakNames.push(results[si].name);
      }
      speakText('I found ' + results.length + ' ' + query + ' places near ' + locationLabel + '. Top picks: ' + speakNames.join(', ') + '.');

      setPrompts(['Vegan near me', 'Late night food', 'Halal near Yonge and Dundas', 'Coffee near M5V 2H1', 'Best pizza downtown']);

    } catch (err) {
      removeLoadingBar();
      addMessage('ai', '<div class="fte-ai-summary"><b>\u{1F37D}\uFE0F Places Search</b><br><br>' +
        'Sorry, I had trouble searching for places. Please try again in a moment.<br><br>' +
        '<span style="font-size:0.75rem;color:#64748b;">Error: ' + escapeHtml(String(err.message || err)) + '</span></div>');
    }

    setStatus('Ready', '#64748b');
    state.processing = false;
    showStopBtn(false);
  }

  // ═══════════════════════════════════════════════════════════
  // HANDLERS: WEATHER (enhanced with specific queries)
  // ═══════════════════════════════════════════════════════════
  async function handleWeather(lower) {
    var postalMatch = parsePostalCode(lower);
    var lat = CONFIG.weatherLat;
    var lon = CONFIG.weatherLon;
    var locationName = 'Toronto';

    // Parse specific question type
    var questionType = 'general'; // general | rain | snow | precipitation | jacket | umbrella | longterm
    if (/will it rain|is it rain|any rain|rain today|going to rain|chance of rain/i.test(lower)) questionType = 'rain';
    else if (/will it snow|is it snow|any snow|snow today|going to snow|chance of snow/i.test(lower)) questionType = 'snow';
    else if (/precipitation|any precip/i.test(lower)) questionType = 'precipitation';
    else if (/jacket|coat|sweater|hoodie|warm enough|how (cold|warm|hot)/i.test(lower) || /do i need/i.test(lower) || /should i (bring|wear|take)/i.test(lower)) questionType = 'jacket';
    else if (/umbrella/i.test(lower)) questionType = 'umbrella';
    else if (/long[- ]?term|7[- ]?day|14[- ]?day|weekly|next week|extended|week ahead/i.test(lower)) questionType = 'longterm';

    // Determine forecast days based on query
    var forecastDays = questionType === 'longterm' ? 7 : 3;

    // ── Postal code geocoding ──
    if (postalMatch) {
      addMessage('ai', '\u{1F4CD} Looking up weather for <b>' + escapeHtml(postalMatch) + '</b>...', false);
      var geo = await geocodePostalCode(postalMatch);
      if (geo) {
        lat = geo.lat;
        lon = geo.lon;
        locationName = postalMatch;
      }
    }

    // ── Area name ──
    if (!postalMatch) {
      var area = parseAreaName(lower);
      if (area) {
        lat = area.lat;
        lon = area.lon;
        locationName = area.label;
      }
    }

    // Cache check (10 min) — only for default Toronto, non-longterm, non-location queries
    var now = Date.now();
    if (state.weatherCache && (now - state.weatherCacheTime) < 600000 && !postalMatch && questionType !== 'longterm' && locationName === 'Toronto') {
      renderWeather(state.weatherCache, locationName, lower, questionType);
      return;
    }

    try {
      var url = CONFIG.weatherApi + '?latitude=' + lat + '&longitude=' + lon +
        '&current=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,weather_code,apparent_temperature' +
        '&hourly=temperature_2m,precipitation_probability,weather_code,precipitation' +
        '&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,weather_code' +
        '&timezone=America/Toronto&forecast_days=' + forecastDays;

      var resp = await fetch(url);
      if (!resp.ok) throw new Error('Weather API error');
      var data = await resp.json();

      if (!postalMatch && locationName === 'Toronto') {
        state.weatherCache = data;
        state.weatherCacheTime = now;
      }
      renderWeather(data, locationName, lower, questionType);
    } catch (err) {
      addMessage('ai', 'Sorry, I couldn\'t fetch weather data right now. Please try again in a moment.');
      setStatus('Ready', '#64748b');
    }
  }

  function getWeatherDescription(code) {
    var descriptions = {
      0: 'Clear sky', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast',
      45: 'Fog', 48: 'Rime fog', 51: 'Light drizzle', 53: 'Moderate drizzle',
      55: 'Dense drizzle', 56: 'Freezing drizzle', 57: 'Dense freezing drizzle',
      61: 'Slight rain', 63: 'Moderate rain', 65: 'Heavy rain',
      66: 'Light freezing rain', 67: 'Heavy freezing rain',
      71: 'Slight snow', 73: 'Moderate snow', 75: 'Heavy snow',
      77: 'Snow grains', 80: 'Slight showers', 81: 'Moderate showers',
      82: 'Violent showers', 85: 'Slight snow showers', 86: 'Heavy snow showers',
      95: 'Thunderstorm', 96: 'Thunderstorm with hail', 99: 'Thunderstorm with heavy hail'
    };
    return descriptions[code] || 'Unknown';
  }

  function getWeatherEmoji(code) {
    if (code === 0) return '\u2600\uFE0F';
    if (code <= 3) return '\u26C5';
    if (code <= 48) return '\u{1F32B}\uFE0F';
    if (code <= 57) return '\u{1F327}\uFE0F';
    if (code <= 67) return '\u{1F327}\uFE0F';
    if (code <= 77) return '\u2744\uFE0F';
    if (code <= 82) return '\u{1F326}\uFE0F';
    if (code <= 86) return '\u{1F328}\uFE0F';
    return '\u26C8\uFE0F';
  }

  function isRainCode(code) { return (code >= 51 && code <= 67) || (code >= 80 && code <= 82) || code >= 95; }
  function isSnowCode(code) { return (code >= 71 && code <= 77) || (code >= 85 && code <= 86); }

  function renderWeather(data, location, lower, questionType) {
    var c = data.current;
    var temp = Math.round(c.temperature_2m);
    var feelsLike = Math.round(c.apparent_temperature);
    var wind = Math.round(c.wind_speed_10m);
    var humidity = c.relative_humidity_2m;
    var precip = c.precipitation;
    var code = c.weather_code;
    var desc = getWeatherDescription(code);
    var emoji = getWeatherEmoji(code);

    // Analyze hourly data for today's rain/snow probability
    var todayHours = [];
    var maxRainProb = 0;
    var maxSnowProb = 0;
    var totalPrecipToday = 0;
    if (data.hourly) {
      var nowHour = new Date().getHours();
      for (var h = 0; h < Math.min(24, data.hourly.time.length); h++) {
        var hourTime = new Date(data.hourly.time[h]);
        if (isToday(hourTime) && hourTime.getHours() >= nowHour) {
          todayHours.push({
            hour: hourTime.getHours(),
            precipProb: data.hourly.precipitation_probability[h] || 0,
            weatherCode: data.hourly.weather_code[h],
            precip: data.hourly.precipitation ? data.hourly.precipitation[h] : 0
          });
          if (data.hourly.precipitation_probability[h] > maxRainProb && isRainCode(data.hourly.weather_code[h])) {
            maxRainProb = data.hourly.precipitation_probability[h];
          }
          if (data.hourly.precipitation_probability[h] > maxSnowProb && isSnowCode(data.hourly.weather_code[h])) {
            maxSnowProb = data.hourly.precipitation_probability[h];
          }
          totalPrecipToday += data.hourly.precipitation ? data.hourly.precipitation[h] : 0;
        }
      }
    }

    // Jacket recommendation
    var needJacket = feelsLike < 10 || precip > 0 || code >= 51;
    var jacketReason = '';
    if (feelsLike < 0) jacketReason = 'It\'s freezing \u2014 definitely wear a warm coat, hat, and gloves.';
    else if (feelsLike < 5) jacketReason = 'It\'s quite cold \u2014 a warm jacket is essential.';
    else if (feelsLike < 10) jacketReason = 'It\'s cool out \u2014 bring a jacket.';
    else if (precip > 0 || code >= 51) jacketReason = 'There\'s precipitation \u2014 bring a waterproof jacket or umbrella.';
    else if (feelsLike < 15) jacketReason = 'It\'s mild \u2014 a light layer would be good.';
    else jacketReason = 'It\'s warm enough \u2014 no jacket needed!';

    var html = '<div class="fte-ai-summary">';

    // ── SPECIFIC QUESTION: RAIN ──
    if (questionType === 'rain') {
      var willRain = isRainCode(code) || maxRainProb > 30;
      html += '<b>\u{1F327}\uFE0F Will it rain in ' + escapeHtml(location) + ' today?</b><br><br>';
      if (isRainCode(code)) {
        html += '<b style="color:#60a5fa;">Yes, it\'s raining right now.</b> ' + desc + '.<br>';
      } else if (maxRainProb > 60) {
        html += '<b style="color:#f59e0b;">Very likely.</b> Up to <b>' + maxRainProb + '%</b> chance of rain later today.<br>';
      } else if (maxRainProb > 30) {
        html += '<b style="color:#fbbf24;">Possible.</b> Up to <b>' + maxRainProb + '%</b> chance of rain.<br>';
      } else {
        html += '<b style="color:#22c55e;">Unlikely.</b> Rain probability is low (max ' + maxRainProb + '%).<br>';
      }
      html += '<br>\u{1F321}\uFE0F Currently: <b>' + temp + '\u00B0C</b> (feels like ' + feelsLike + '\u00B0C) \u2022 ' + desc;
      if (willRain) html += '<br><br>\u2602\uFE0F <b>Bring an umbrella!</b>';
      html += '</div>';
      addMessage('ai', html, false);
      speakText(isRainCode(code) ? 'Yes, it\'s raining right now in ' + location + '. Bring an umbrella.' :
        maxRainProb > 60 ? 'Very likely rain in ' + location + ' today, up to ' + maxRainProb + ' percent chance. Bring an umbrella.' :
          maxRainProb > 30 ? 'There\'s a ' + maxRainProb + ' percent chance of rain in ' + location + ' today. You might want an umbrella.' :
            'Rain is unlikely in ' + location + ' today. Only ' + maxRainProb + ' percent chance.');
      setStatus('Ready', '#64748b');
      return;
    }

    // ── SPECIFIC QUESTION: SNOW ──
    if (questionType === 'snow') {
      var willSnow = isSnowCode(code) || maxSnowProb > 30;
      html += '<b>\u2744\uFE0F Will it snow in ' + escapeHtml(location) + ' today?</b><br><br>';
      if (isSnowCode(code)) {
        html += '<b style="color:#60a5fa;">Yes, it\'s snowing right now.</b> ' + desc + '.<br>';
      } else if (maxSnowProb > 60) {
        html += '<b style="color:#f59e0b;">Very likely.</b> Snow probability up to <b>' + maxSnowProb + '%</b>.<br>';
      } else if (maxSnowProb > 30) {
        html += '<b style="color:#fbbf24;">Possible.</b> Snow probability up to <b>' + maxSnowProb + '%</b>.<br>';
      } else if (temp < 2 && maxRainProb > 30) {
        html += '<b style="color:#fbbf24;">Temperature is near freezing</b> (' + temp + '\u00B0C) with precipitation possible \u2014 could turn to snow.<br>';
      } else {
        html += '<b style="color:#22c55e;">Unlikely.</b> No significant snow expected.<br>';
      }
      html += '<br>\u{1F321}\uFE0F Currently: <b>' + temp + '\u00B0C</b> (feels like ' + feelsLike + '\u00B0C) \u2022 ' + desc;
      if (willSnow) html += '<br><br>\u{1F9E5} <b>Dress warmly!</b>';
      html += '</div>';
      addMessage('ai', html, false);
      speakText(isSnowCode(code) ? 'Yes, it\'s snowing in ' + location + ' right now. Dress warmly!' :
        maxSnowProb > 30 ? 'There\'s a ' + maxSnowProb + ' percent chance of snow in ' + location + ' today.' :
          'Snow is unlikely in ' + location + ' today. Current temperature is ' + temp + ' degrees.');
      setStatus('Ready', '#64748b');
      return;
    }

    // ── SPECIFIC QUESTION: PRECIPITATION ──
    if (questionType === 'precipitation') {
      var anyPrecip = precip > 0 || maxRainProb > 20 || maxSnowProb > 20;
      html += '<b>\u{1F4A7} Precipitation in ' + escapeHtml(location) + ' today</b><br><br>';
      if (precip > 0) {
        html += '<b>Currently:</b> ' + precip + ' mm of precipitation \u2022 ' + desc + '<br>';
      }
      html += '<b>Rain chance:</b> up to <b>' + maxRainProb + '%</b><br>';
      html += '<b>Snow chance:</b> up to <b>' + maxSnowProb + '%</b><br>';
      html += '<b>Total expected:</b> ~' + totalPrecipToday.toFixed(1) + ' mm remaining today<br>';
      if (anyPrecip) {
        html += '<br>\u2602\uFE0F Bring an umbrella or waterproof jacket.';
      } else {
        html += '<br>\u2600\uFE0F Looks dry today!';
      }
      html += '</div>';
      addMessage('ai', html, false);
      speakText(anyPrecip ? 'There is precipitation expected in ' + location + ' today. Rain chance up to ' + maxRainProb + ' percent, snow chance up to ' + maxSnowProb + ' percent.' :
        'No significant precipitation expected in ' + location + ' today.');
      setStatus('Ready', '#64748b');
      return;
    }

    // ── SPECIFIC QUESTION: JACKET / UMBRELLA ──
    if (questionType === 'jacket' || questionType === 'umbrella') {
      html += '<b>\u{1F9E5} ' + (questionType === 'umbrella' ? 'Umbrella' : 'Jacket') + ' check for ' + escapeHtml(location) + '</b><br><br>';
      html += emoji + ' Currently: <b>' + temp + '\u00B0C</b> (feels like ' + feelsLike + '\u00B0C)<br>';
      html += '\u{1F4A8} Wind: <b>' + wind + ' km/h</b> \u2022 ' + desc + '<br><br>';
      if (questionType === 'umbrella') {
        var needUmbrella = isRainCode(code) || maxRainProb > 30;
        html += '<b>\u2602\uFE0F Umbrella?</b> ' + (needUmbrella ? '<span style="color:#f59e0b;">Yes</span>' : '<span style="color:#22c55e;">No</span>') + '<br>';
        html += needUmbrella ? 'Rain probability up to ' + maxRainProb + '% today. Better safe than sorry!' : 'Low rain chance today (' + maxRainProb + '%). You should be fine without one.';
      } else {
        html += '<b>\u{1F9E5} Jacket?</b> ' + (needJacket ? '<span style="color:#f59e0b;">Yes</span>' : '<span style="color:#22c55e;">No</span>') + ' \u2014 ' + jacketReason;
      }
      html += '</div>';
      addMessage('ai', html, false);
      speakText(questionType === 'umbrella' ?
        (maxRainProb > 30 ? 'Yes, bring an umbrella. Rain chance is ' + maxRainProb + ' percent.' : 'No umbrella needed today. Rain chance is only ' + maxRainProb + ' percent.') :
        jacketReason);
      setStatus('Ready', '#64748b');
      return;
    }

    // ── LONG-TERM FORECAST ──
    if (questionType === 'longterm') {
      html += '<b>' + emoji + ' Extended Forecast for ' + escapeHtml(location) + '</b><br><br>';
      html += '\u{1F321}\uFE0F Currently: <b>' + temp + '\u00B0C</b> (feels like ' + feelsLike + '\u00B0C) \u2022 ' + desc + '<br><br>';
      if (data.daily) {
        html += '<b>' + data.daily.time.length + '-Day Forecast:</b><br>';
        for (var i = 0; i < data.daily.time.length; i++) {
          var dayDate = new Date(data.daily.time[i] + 'T12:00:00');
          var dayEmoji = getWeatherEmoji(data.daily.weather_code[i]);
          var dayDesc = getWeatherDescription(data.daily.weather_code[i]);
          html += dayEmoji + ' <b>' + formatDate(dayDate) + '</b>: ' +
            Math.round(data.daily.temperature_2m_min[i]) + '\u00B0/' +
            Math.round(data.daily.temperature_2m_max[i]) + '\u00B0C \u2022 ' + dayDesc;
          if (data.daily.precipitation_sum[i] > 0) html += ' \u2022 \u{1F327}\uFE0F ' + data.daily.precipitation_sum[i] + 'mm';
          if (data.daily.precipitation_probability_max && data.daily.precipitation_probability_max[i] > 20) {
            html += ' \u2022 ' + data.daily.precipitation_probability_max[i] + '% precip';
          }
          html += '<br>';
        }
      }
      html += '</div>';
      addMessage('ai', html, false);
      speakText('Here\'s the extended forecast for ' + location + '. Currently ' + temp + ' degrees, ' + desc + '. Check the details in the chat.');
      setStatus('Ready', '#64748b');
      return;
    }

    // ── GENERAL WEATHER ──
    html += '<b>' + emoji + ' Weather in ' + escapeHtml(location) + '</b><br><br>';
    html += '\u{1F321}\uFE0F Temperature: <b>' + temp + '\u00B0C</b> (feels like ' + feelsLike + '\u00B0C)<br>';
    html += '\u{1F4A8} Wind: <b>' + wind + ' km/h</b><br>';
    html += '\u{1F4A7} Humidity: <b>' + humidity + '%</b><br>';
    html += '\u{1F324}\uFE0F Conditions: <b>' + desc + '</b><br>';
    if (precip > 0) html += '\u{1F327}\uFE0F Precipitation: <b>' + precip + ' mm</b><br>';
    html += '<br><b>\u{1F9E5} Jacket?</b> ' + (needJacket ? 'Yes' : 'No') + ' \u2014 ' + jacketReason;

    // Today's precipitation outlook
    if (maxRainProb > 20 || maxSnowProb > 20) {
      html += '<br><br><b>Today\'s precipitation outlook:</b><br>';
      if (maxRainProb > 20) html += '\u{1F327}\uFE0F Rain: up to <b>' + maxRainProb + '%</b> chance<br>';
      if (maxSnowProb > 20) html += '\u2744\uFE0F Snow: up to <b>' + maxSnowProb + '%</b> chance<br>';
    }

    // 3-day forecast
    if (data.daily) {
      html += '<br><b>' + data.daily.time.length + '-Day Forecast:</b><br>';
      for (var d = 0; d < data.daily.time.length; d++) {
        var dayDate2 = new Date(data.daily.time[d] + 'T12:00:00');
        var dayEmoji2 = getWeatherEmoji(data.daily.weather_code[d]);
        html += dayEmoji2 + ' ' + formatDate(dayDate2) + ': ' +
          Math.round(data.daily.temperature_2m_min[d]) + '\u00B0/' +
          Math.round(data.daily.temperature_2m_max[d]) + '\u00B0C';
        if (data.daily.precipitation_sum[d] > 0) html += ' \u{1F327}\uFE0F' + data.daily.precipitation_sum[d] + 'mm';
        html += '<br>';
      }
    }
    html += '</div>';

    addMessage('ai', html, false);
    var speech = 'Currently in ' + location + ', it\'s ' + temp + ' degrees, feels like ' + feelsLike + '. ' + desc + '. ' + jacketReason;
    speakText(speech);
    setStatus('Ready', '#64748b');
  }

  // ═══════════════════════════════════════════════════════════
  // HANDLERS: STOCKS
  // ═══════════════════════════════════════════════════════════

  // Helper: read the "Data last updated" <time> element from the stocks page
  function getStockUpdateDate() {
    try {
      var timeEl = document.querySelector('time[dateTime]') || document.querySelector('time[datetime]');
      if (timeEl) {
        var iso = timeEl.getAttribute('dateTime') || timeEl.getAttribute('datetime');
        var display = timeEl.textContent.trim();
        if (iso) return { date: new Date(iso), display: display, iso: iso };
      }
      // Fallback: look for "Data last updated:" text
      var ps = document.querySelectorAll('p');
      for (var i = 0; i < ps.length; i++) {
        var t = ps[i].textContent;
        if (/Data last updated/i.test(t)) {
          var m = t.match(/(\d{4}-\d{2}-\d{2})/);
          if (m) return { date: new Date(m[1] + 'T12:00:00'), display: m[1], iso: m[1] };
        }
      }
    } catch (e) { }
    return null;
  }

  // Helper: read stock data from page scripts
  function getStocksFromPage() {
    try {
      var scripts = document.querySelectorAll('script');
      for (var i = 0; i < scripts.length; i++) {
        var text = scripts[i].textContent || '';
        if (text.indexOf('initialStocks') !== -1) {
          var match = text.match(/"initialStocks":\[(.+?)\](?:,\[|}\])/);
          var stocks = null;
          if (match) {
            try { stocks = JSON.parse('[' + match[1] + ']'); } catch (e) { }
          }
          if (!stocks) {
            var jsonStart = text.indexOf('"initialStocks":[');
            if (jsonStart !== -1) {
              var arrStart = text.indexOf('[', jsonStart);
              var depth = 0;
              var arrEnd = arrStart;
              for (var j = arrStart; j < text.length; j++) {
                if (text[j] === '[') depth++;
                else if (text[j] === ']') { depth--; if (depth === 0) { arrEnd = j; break; } }
              }
              try { stocks = JSON.parse(text.substring(arrStart, arrEnd + 1)); } catch (e) { }
            }
          }
          if (stocks) return stocks;
        }
      }
    } catch (e) { }
    return null;
  }

  // Algorithm definitions — used by multiple stock sub-handlers
  var ALGO_DEFINITIONS = {
    'CAN SLIM': {
      short: 'William O\'Neil\'s growth stock selection',
      full: '<b>CAN SLIM Growth</b> \u2014 A long-term growth screener based on William O\'Neil\'s methodology. ' +
        'It looks for stocks with strong <b>Relative Strength (RS) Rating \u2265 90</b>, confirmed <b>Stage-2 Uptrend</b> ' +
        '(Mark Minervini criteria), price near the <b>52-week high</b>, and favorable RSI. ' +
        'The name stands for: <b>C</b>urrent earnings, <b>A</b>nnual earnings, <b>N</b>ew products/management, ' +
        '<b>S</b>upply & demand, <b>L</b>eader or laggard, <b>I</b>nstitutional sponsorship, <b>M</b>arket direction.<br>' +
        '<b>Best for:</b> 3\u201312 month holds. <b>Risk:</b> Medium.',
      bestFor: '3\u201312 month holds'
    },
    'Technical Momentum': {
      short: 'RSI, volume Z-score, price breakout',
      full: '<b>Technical Momentum</b> \u2014 A short-term momentum strategy that analyzes multiple timeframes (24h, 3d, 7d). ' +
        'It detects <b>volume surges</b> vs the 10-day average, <b>RSI extremes/momentum</b>, ' +
        '<b>20-day breakouts</b>, and <b>Bollinger Band squeezes</b>. ' +
        'Stocks get scored higher when multiple signals align across timeframes.<br>' +
        '<b>Best for:</b> 24h\u20131 week trades. <b>Risk:</b> High (short-term volatility).',
      bestFor: '24h\u20131 week trades'
    },
    'Alpha Predator': {
      short: 'ADX trend strength + Awesome Oscillator',
      full: '<b>Alpha Predator</b> \u2014 An aggressive trend-following strategy. ' +
        'It uses the <b>ADX (Average Directional Index)</b> to confirm trend strength and the ' +
        '<b>Awesome Oscillator</b> to time entries when momentum is shifting. ' +
        'Only triggers when ADX > 25 (strong trend) and AO crosses above zero.<br>' +
        '<b>Best for:</b> 3d\u20142 week swing trades. <b>Risk:</b> Medium-High.',
      bestFor: '3d\u20142 week swings'
    },
    'Penny Sniper': {
      short: 'Sub-$20 stocks with volume surge',
      full: '<b>Penny Sniper</b> \u2014 Targets lower-priced stocks (under $20) experiencing abnormal <b>volume surges</b>. ' +
        'It screens for sudden institutional or retail interest based on volume spikes ' +
        'relative to the 10-day moving average, combined with price momentum and RSI filters. ' +
        'Higher risk due to lower liquidity and wider spreads.<br>' +
        '<b>Best for:</b> 24h\u20143d trades. <b>Risk:</b> Very High.',
      bestFor: '24h\u20143d trades'
    },
    'Composite Rating': {
      short: 'Multi-factor composite scoring',
      full: '<b>Composite Rating</b> \u2014 A multi-factor scoring system that blends: ' +
        '<b>technicals</b> (price vs SMAs, RSI), <b>volume dynamics</b>, ' +
        '<b>fundamentals</b> (PE ratio, market cap), and <b>regime detection</b> (normal/low-vol/high-vol). ' +
        'Default weights are 40% technical / 20% volume / 20% fundamental / 20% regime. ' +
        'Gives an overall attractiveness score for swing/watchlist building.<br>' +
        '<b>Best for:</b> 1\u20143 month swings. <b>Risk:</b> Medium.',
      bestFor: '1\u20143 month swings'
    },
    'ML Ensemble': {
      short: 'Tree-based ML models for short-horizon returns',
      full: '<b>ML Ensemble</b> \u2014 Uses machine learning models (XGBoost, Gradient Boosting, etc.) to predict ' +
        'next-day or short-horizon returns from technical and microstructure features. ' +
        'Models are evaluated on MSE, R\u00B2, and MAE. Walk-forward validation helps prevent overfitting. ' +
        'Works best on liquid large/mid-cap stocks where training data is abundant.<br>' +
        '<b>Best for:</b> Liquid large/mid caps, 1\u20143 day horizon. <b>Risk:</b> Medium.',
      bestFor: 'liquid large/mid caps, 1\u20143 day horizon'
    },
    'Statistical Arbitrage': {
      short: 'Pairs mean reversion, z-score spread',
      full: '<b>Statistical Arbitrage</b> \u2014 A market-neutral strategy that finds <b>correlated stock pairs</b> ' +
        'and trades the spread when it deviates from the mean. Uses <b>z-score</b> for entry/exit signals ' +
        'and tracks <b>Sharpe ratio</b> and total return. Works by going long one stock and short the other ' +
        'when the spread is abnormally wide, then closing when it reverts.<br>' +
        '<b>Best for:</b> Sector pairs, mean reversion. <b>Risk:</b> Medium (hedged).',
      bestFor: 'sector pairs, mean reversion'
    }
  };

  function handleStocks(lower) {
    var stocks = getStocksFromPage();
    var dateInfo = getStockUpdateDate();

    // ── "explain algorithms" / "what algorithms are used" ──
    if (/explain.*algorithm|what.*algorithm|algorithm.*explain|algorithm.*mean|describe.*algorithm|all.*algorithm|how.*algorithm/i.test(lower)) {
      showAlgorithmOverview();
      return;
    }

    // ── "what is [specific algorithm]" / "explain [algorithm]" ──
    var algoMatch = lower.match(/(?:what is|what's|explain|describe|tell me about|how does)\s+(can\s*slim|technical\s*momentum|alpha\s*predator|penny\s*sniper|composite\s*rating|ml\s*ensemble|statistical\s*arbitrage)/i);
    if (algoMatch) {
      showSingleAlgorithm(algoMatch[1]);
      return;
    }

    // ── "are picks up to date" / "when were picks updated" / "how old" ──
    if (/up to date|how old|when.*update|fresh|stale|latest|current|outdated/i.test(lower)) {
      showDataFreshness(dateInfo);
      return;
    }

    // ── "risk levels" / "explain risk" ──
    if (/risk.*level|explain.*risk|what.*risk/i.test(lower)) {
      showRiskExplanation();
      return;
    }

    // ── Default: show today's picks (with date freshness) ──
    showStockPicks(stocks, dateInfo, lower);
  }

  function showAlgorithmOverview() {
    var html = '<div class="fte-ai-summary">';
    html += '<b>\u{1F9EA} Stock Algorithms Explained</b><br><br>';
    html += 'We use <b>11+ open-source algorithms</b> to generate picks. Here are the main ones:<br><br>';

    var keys = Object.keys(ALGO_DEFINITIONS);
    for (var i = 0; i < keys.length; i++) {
      var algo = ALGO_DEFINITIONS[keys[i]];
      html += '<div style="margin-bottom:10px;padding:8px;border-left:3px solid #6366f1;background:rgba(99,102,241,0.08);border-radius:4px;">';
      html += algo.full;
      html += '</div>';
    }

    html += '<br>Additionally, there are variant algorithms (CAN SLIM +1/+2/+3, Technical Momentum +1/+2, Penny Sniper +2) that apply ';
    html += 'stricter or alternative filters to the base strategy.<br><br>';
    html += 'All picks are <b>slippage-tested</b> with realistic execution simulation, and the V2 engine includes ';
    html += '<b>regime awareness</b> (shuts down in bearish markets) and an <b>immutable audit trail</b>.<br><br>';
    html += '<span style="color:#64748b;font-size:10px;">Not financial advice. For educational purposes only.</span>';
    html += '</div>';
    addMessage('ai', html, false);
    speakText('We use 11 plus algorithms including CAN SLIM for growth, Technical Momentum for short-term trades, Alpha Predator for trends, and more. Ask about any specific one for details. Not financial advice.');
    setPrompts(['What is CAN SLIM?', 'What is Technical Momentum?', 'What is Alpha Predator?', 'Give me today\'s stock picks', 'What is Composite Rating?', 'What is Penny Sniper?']);
    setStatus('Ready', '#64748b');
  }

  function showSingleAlgorithm(name) {
    var normalized = name.toLowerCase().replace(/\s+/g, ' ').trim();
    var key = null;
    var keys = Object.keys(ALGO_DEFINITIONS);
    for (var i = 0; i < keys.length; i++) {
      if (keys[i].toLowerCase() === normalized) { key = keys[i]; break; }
    }
    if (!key) {
      // fuzzy match
      for (var j = 0; j < keys.length; j++) {
        if (keys[j].toLowerCase().indexOf(normalized.split(' ')[0]) !== -1) { key = keys[j]; break; }
      }
    }
    if (!key) {
      addMessage('ai', 'I don\'t recognize that algorithm name. Try asking about: CAN SLIM, Technical Momentum, Alpha Predator, Penny Sniper, Composite Rating, ML Ensemble, or Statistical Arbitrage.');
      setStatus('Ready', '#64748b');
      return;
    }
    var algo = ALGO_DEFINITIONS[key];
    var html = '<div class="fte-ai-summary">';
    html += '<b>\u{1F9EA} Algorithm: ' + key + '</b><br><br>';
    html += '<div style="padding:10px;border-left:3px solid #6366f1;background:rgba(99,102,241,0.08);border-radius:4px;">';
    html += algo.full;
    html += '</div>';

    // Show picks from this algorithm if on stocks page
    var stocks = getStocksFromPage();
    if (stocks && stocks.length > 0) {
      var filtered = stocks.filter(function (s) {
        return (s.algorithm || '').toLowerCase().indexOf(key.toLowerCase().split(' ')[0]) !== -1;
      });
      if (filtered.length > 0) {
        var top5 = filtered.slice(0, 5);
        html += '<br><b>Current picks using ' + key + ' (' + filtered.length + ' total):</b><br>';
        for (var k = 0; k < top5.length; k++) {
          var s = top5[k];
          html += '\u2022 <b>' + escapeHtml(s.symbol) + '</b> \u2014 $' + (s.price || 0) + ', Score: ' + (s.score || 'N/A') + '/100, ' + (s.rating || 'N/A') + '<br>';
        }
        if (filtered.length > 5) html += '<span style="color:#64748b;font-size:10px;">...and ' + (filtered.length - 5) + ' more.</span><br>';
      }
    }

    html += '<br><span style="color:#64748b;font-size:10px;">Not financial advice. For educational purposes only.</span>';
    html += '</div>';
    addMessage('ai', html, false);
    speakText(key + '. ' + algo.short + '. Best for ' + algo.bestFor + '. Not financial advice.');

    // Smart follow-up prompts
    var otherAlgos = Object.keys(ALGO_DEFINITIONS).filter(function (k) { return k !== key; });
    var followUps = ['Give me today\'s stock picks', 'Explain what the algorithms each mean'];
    followUps.push('What is ' + otherAlgos[0] + '?');
    followUps.push('What is ' + otherAlgos[1] + '?');
    setPrompts(followUps);
    setStatus('Ready', '#64748b');
  }

  function showDataFreshness(dateInfo) {
    var html = '<div class="fte-ai-summary">';
    html += '<b>\u{1F4C5} Data Freshness Check</b><br><br>';
    if (dateInfo) {
      var now = new Date();
      var daysDiff = Math.floor((now - dateInfo.date) / 86400000);
      var dayOfWeek = dateInfo.date.getDay(); // 0=Sun, 6=Sat

      html += 'Picks were last updated: <b>' + dateInfo.display + '</b><br><br>';

      if (daysDiff === 0) {
        html += '\u2705 <b>These are today\'s picks!</b> The data is current and fresh.';
      } else if (daysDiff === 1) {
        if (now.getDay() === 0 || now.getDay() === 6) {
          html += '\u2705 <b>Picks are from the last trading day</b> (yesterday). This is expected on weekends \u2014 markets are closed.';
        } else {
          html += '\u{1F7E1} <b>Picks are from yesterday.</b> Today\'s picks may not have run yet. ' +
            'Check back later \u2014 the pipeline usually updates by market open.';
        }
      } else if (daysDiff <= 3) {
        var isWeekendGap = (dayOfWeek === 5 && daysDiff <= 3); // Friday data viewed on weekend/Monday
        if (isWeekendGap || now.getDay() === 1) {
          html += '\u{1F7E0} <b>Picks are from ' + daysDiff + ' day(s) ago.</b> This is likely the weekend gap \u2014 ' +
            'last trading day was Friday. New picks should appear after Monday\'s market open.';
        } else {
          html += '\u{1F7E0} <b>Picks are ' + daysDiff + ' days old.</b> The data pipeline may have missed a run. ' +
            'Consider checking if it\'s a holiday or if there was a technical issue.';
        }
      } else {
        html += '\u{1F534} <b>Picks are ' + daysDiff + ' days old!</b> This data is likely stale. ' +
          'The daily stock fetching pipeline may not have run recently. ' +
          'Picks on the page are still valid for reference, but may not reflect current market conditions.';
      }
      html += '<br><br>Picks are generated once per trading day (Mon\u2013Fri) using the GitHub Actions pipeline.';
    } else {
      html += '\u26A0\uFE0F Could not determine when picks were last updated. ' +
        'If you\'re not on the Stock Ideas page, navigate there first. ' +
        'Otherwise, the date element may not be available.';
    }
    html += '<br><br><span style="color:#64748b;font-size:10px;">Not financial advice. For educational purposes only.</span>';
    html += '</div>';
    addMessage('ai', html, false);

    if (dateInfo) {
      var daysDiff2 = Math.floor((new Date() - dateInfo.date) / 86400000);
      speakText('Picks were last updated ' + dateInfo.display + ', ' + (daysDiff2 === 0 ? 'today. Data is current.' : daysDiff2 + ' days ago.'));
    } else {
      speakText('I couldn\'t determine when picks were last updated.');
    }
    setPrompts(['Give me today\'s stock picks', 'Explain what the algorithms each mean', 'What is CAN SLIM?', 'Something else']);
    setStatus('Ready', '#64748b');
  }

  function showRiskExplanation() {
    var html = '<div class="fte-ai-summary">';
    html += '<b>\u26A0\uFE0F Risk Levels Explained</b><br><br>';
    html += 'Each stock pick is assigned a risk level based on volatility, liquidity, price, and algorithm type:<br><br>';
    html += '<div style="padding:8px;border-left:3px solid #22c55e;background:rgba(34,197,94,0.08);border-radius:4px;margin-bottom:6px;">';
    html += '\u{1F7E2} <b>Medium Risk</b> \u2014 Established stocks with solid fundamentals, lower volatility. Typical for CAN SLIM, Composite Rating picks. Examples: large-cap tech, ETFs.';
    html += '</div>';
    html += '<div style="padding:8px;border-left:3px solid #f59e0b;background:rgba(245,158,11,0.08);border-radius:4px;margin-bottom:6px;">';
    html += '\u{1F7E1} <b>High Risk</b> \u2014 More volatile stocks, shorter timeframes, momentum-driven. Typical for Technical Momentum picks. Higher potential returns but also higher potential losses.';
    html += '</div>';
    html += '<div style="padding:8px;border-left:3px solid #ef4444;background:rgba(239,68,68,0.08);border-radius:4px;margin-bottom:6px;">';
    html += '\u{1F534} <b>Very High Risk</b> \u2014 Low-priced or penny stocks, high volume volatility, wide bid/ask spreads. Typical for Penny Sniper picks. Only trade with capital you can afford to lose entirely.';
    html += '</div><br>';
    html += 'The V2 engine also applies <b>slippage torture tests</b> (3\u20135x standard liquidity spread) to filter out picks that wouldn\'t survive realistic execution costs.<br><br>';
    html += '<span style="color:#64748b;font-size:10px;">Not financial advice. For educational purposes only.</span>';
    html += '</div>';
    addMessage('ai', html, false);
    speakText('Risk levels range from Medium for established stocks, to High for momentum plays, to Very High for penny stocks. All picks are slippage tested. Not financial advice.');
    setPrompts(['Give me today\'s stock picks', 'Explain what the algorithms each mean', 'What is Penny Sniper?', 'Something else']);
    setStatus('Ready', '#64748b');
  }

  function showStockPicks(stocks, dateInfo, lower) {
    var html = '<div class="fte-ai-summary">';
    html += '<b>\u{1F4C8} Stock Ideas</b>';

    // Show data freshness at the top
    if (dateInfo) {
      var daysDiff = Math.floor((new Date() - dateInfo.date) / 86400000);
      if (daysDiff === 0) {
        html += ' <span style="color:#22c55e;font-size:11px;">\u2705 Updated today</span>';
      } else if (daysDiff === 1) {
        var isWeekend = new Date().getDay() === 0 || new Date().getDay() === 6;
        html += ' <span style="color:#eab308;font-size:11px;">\u{1F7E1} Updated yesterday' + (isWeekend ? ' (weekend)' : '') + '</span>';
      } else if (daysDiff <= 3) {
        html += ' <span style="color:#f97316;font-size:11px;">\u{1F7E0} ' + daysDiff + ' days ago</span>';
      } else {
        html += ' <span style="color:#ef4444;font-size:11px;">\u{1F534} ' + daysDiff + ' days old \u2014 may be stale</span>';
      }
      html += '<br><span style="font-size:10px;color:#64748b;">Last updated: ' + dateInfo.display + '</span>';
    }
    html += '<br><br>';

    if (stocks && stocks.length > 0) {
      // Check if user asked for specific type
      var filterAlgo = null;
      if (/growth|can.?slim/i.test(lower)) filterAlgo = 'CAN SLIM';
      else if (/momentum/i.test(lower)) filterAlgo = 'Technical Momentum';
      else if (/alpha/i.test(lower)) filterAlgo = 'Alpha Predator';
      else if (/penny/i.test(lower)) filterAlgo = 'Penny Sniper';
      else if (/composite/i.test(lower)) filterAlgo = 'Composite Rating';

      var displayStocks = stocks;
      if (filterAlgo) {
        displayStocks = stocks.filter(function (s) {
          return (s.algorithm || '').toLowerCase().indexOf(filterAlgo.toLowerCase().split(' ')[0]) !== -1;
        });
        html += '<b>Filtered by: ' + filterAlgo + '</b> (' + displayStocks.length + ' picks)<br><br>';
      }

      var topPicks = displayStocks.slice(0, 8);
      if (!filterAlgo) html += '<b>Top ' + topPicks.length + ' picks (of ' + stocks.length + ' total):</b><br><br>';

      for (var k = 0; k < topPicks.length; k++) {
        var s = topPicks[k];
        // Color-code by rating
        var ratingColor = '#22c55e';
        if ((s.rating || '').indexOf('HOLD') !== -1) ratingColor = '#eab308';
        else if ((s.rating || '').indexOf('SELL') !== -1) ratingColor = '#ef4444';

        html += '<div class="event-item">';
        html += '<b>' + escapeHtml(s.symbol) + '</b> \u2014 ' + escapeHtml(s.name) + '<br>';
        html += '<span style="font-size:11px;color:#94a3b8;">';
        html += 'Rating: <span style="color:' + ratingColor + ';">' + (s.rating || 'N/A') + '</span>';
        html += ' \u2022 Score: ' + (s.score || 'N/A') + '/100';
        html += ' \u2022 Price: $' + (s.price || 0);
        html += ' \u2022 Risk: ' + (s.risk || 'N/A');
        html += ' \u2022 Timeframe: ' + (s.timeframe || 'N/A');
        html += '</span><br>';
        html += '<span style="font-size:10px;color:#64748b;">';
        html += 'Algorithm: ' + (s.algorithm || 'N/A');
        // Explain WHY this stock was picked
        html += ' \u2014 <i>';
        if ((s.algorithm || '').indexOf('CAN SLIM') !== -1) {
          html += 'Strong RS rating';
          if (s.indicators && s.indicators.stage2) html += ', Stage 2 uptrend';
          if (s.indicators && s.indicators.rsRating) html += ' (RS:' + s.indicators.rsRating + ')';
        } else if ((s.algorithm || '').indexOf('Technical Momentum') !== -1) {
          html += 'Momentum signal';
          if (s.indicators && s.indicators.rsi) html += ', RSI:' + Math.round(s.indicators.rsi);
          if (s.indicators && s.indicators.breakout) html += ', breakout detected';
        } else if ((s.algorithm || '').indexOf('Alpha Predator') !== -1) {
          html += 'Strong trend (ADX)';
        } else if ((s.algorithm || '').indexOf('Penny Sniper') !== -1) {
          html += 'Volume surge on low-price stock';
        } else if ((s.algorithm || '').indexOf('Composite') !== -1) {
          html += 'Multi-factor composite score';
        } else {
          html += 'algorithmic signal';
        }
        html += '</i>';
        html += '</span>';
        html += '</div>';
      }
      if (displayStocks.length > 8) {
        html += '<span style="color:#64748b;font-size:10px;">Showing 8 of ' + displayStocks.length + '. Scroll the page for all picks.</span><br>';
      }
      html += '<br><b>Algorithms used in these picks:</b><br>';
      var algoSet = {};
      displayStocks.forEach(function (s) { if (s.algorithm) algoSet[s.algorithm.split(' +')[0].split('+')[0].trim()] = true; });
      var algoKeys = Object.keys(algoSet);
      for (var a = 0; a < algoKeys.length; a++) {
        var def = ALGO_DEFINITIONS[algoKeys[a]];
        html += '\u2022 <b>' + algoKeys[a] + '</b> \u2014 ' + (def ? def.short : 'proprietary scoring') + '<br>';
      }
      html += '<br>All picks are <b>slippage-tested</b> with realistic execution simulation.';
    } else {
      html += 'Our stock analysis uses <b>11+ open-source algorithms</b> including:<br>';
      html += '\u2022 <b>CAN SLIM</b> \u2014 growth stock selection<br>';
      html += '\u2022 <b>Technical Momentum</b> \u2014 RSI, volume Z-score, breakout<br>';
      html += '\u2022 <b>Alpha Predator</b> \u2014 ADX trend strength + Awesome Oscillator<br>';
      html += '\u2022 <b>Penny Sniper</b> \u2014 Sub-$20 volume surge detection<br>';
      html += '\u2022 <b>Regime Detection</b> \u2014 bull/bear market classification<br>';
      html += '\u2022 <b>Slippage Testing</b> \u2014 realistic execution simulation<br>';
      html += '<br>Picks are refreshed daily each trading day.<br>';
    }
    html += '<br><a href="/findstocks/" target="_blank">Open Stock Ideas App \u2192</a>';
    html += '<br><br><span style="color:#64748b;font-size:10px;">Not financial advice. For educational purposes only.</span>';
    html += '</div>';
    addMessage('ai', html, false);

    if (stocks && stocks.length > 0) {
      var top3 = stocks.slice(0, 3).map(function (s) { return s.symbol + ' at $' + s.price + ', rated ' + s.rating; }).join('. ');
      speakText('Here are the top stock picks. ' + top3 + '. The picks use algorithms like CAN SLIM and Technical Momentum with slippage testing. Not financial advice.');
    } else {
      speakText('Our stock analysis uses 11 plus open-source algorithms. Open the Stock Ideas app for today\'s picks. Not financial advice.');
    }
    setPrompts(['Explain what the algorithms each mean', 'What is CAN SLIM?', 'Are these picks up to date?', 'Explain the risk levels', 'Best growth stocks', 'Momentum picks today']);
    setStatus('Ready', '#64748b');
  }

  // ═══════════════════════════════════════════════════════════
  // HANDLERS: STREAMERS / CREATORS (enhanced)
  // ═══════════════════════════════════════════════════════════
  function parseCreatorTimeFilter(lower) {
    if (/past (24|twenty[- ]?four) hours|last (24|twenty[- ]?four) hours|today/i.test(lower)) return 24;
    if (/past (48|forty[- ]?eight) hours|last (48|forty[- ]?eight) hours|2 days|two days/i.test(lower)) return 48;
    if (/past (72|seventy[- ]?two) hours|last (72|seventy[- ]?two) hours|3 days|three days/i.test(lower)) return 72;
    if (/past week|last week|this week|7 days|seven days/i.test(lower)) return 168;
    if (/past (2|two) weeks|last (2|two) weeks|14 days|fourteen days/i.test(lower)) return 336;
    if (/past month|last month|30 days|this month/i.test(lower)) return 720;
    return null;
  }

  // ── Helper: update loading bar label text ──
  function updateLoadingLabel(text) {
    var bar = document.getElementById('fte-ai-loading-bar');
    if (!bar) return;
    var labelEl = bar.querySelector('div');
    if (labelEl) labelEl.textContent = text;
  }

  // ── Collect all checkLive accounts from a creator list ──
  function collectRefreshableAccounts(creators) {
    var accounts = [];
    for (var i = 0; i < creators.length; i++) {
      var cr = creators[i];
      var accts = cr.accounts || cr.social_accounts || [];
      for (var j = 0; j < accts.length; j++) {
        var a = accts[j];
        // Only include accounts that have checkLive enabled, OR any account on a streaming platform
        var platform = (a.platform || '').toLowerCase();
        var isStreamPlatform = /twitch|kick|youtube|tiktok/.test(platform);
        if (a.checkLive || isStreamPlatform || cr.isLiveStreamer) {
          accounts.push({
            platform: platform,
            username: a.username || a.handle || '',
            creator_id: cr.id || cr._id || '',
            creator_name: cr.name || cr.display_name || 'Unknown',
            account_url: a.url || ''
          });
        }
      }
    }
    return accounts;
  }

  async function handleStreamers(lower) {
    var user = window.__fc_logged_in_user__;
    // Fallback: check localStorage if window global not yet set (React may still be loading)
    if (!user || !user.id) {
      try {
        var cached = localStorage.getItem('fav_creators_auth_user');
        if (cached) {
          var parsed = JSON.parse(cached);
          if (parsed && parsed.id) user = parsed;
        }
      } catch (_) { /* ignore */ }
    }

    // ── "Who went live today?" — check live history first ──
    var isLiveHistoryQuery = /who (went|got|came|was) live|went live today|live history|live log|recently.*(went|got) live/i.test(lower);
    if (isLiveHistoryQuery && _liveHistory.length > 0) {
      var todayStr = new Date().toDateString();
      var todayEntries = _liveHistory.filter(function(h) {
        return new Date(h.time).toDateString() === todayStr;
      });
      if (todayEntries.length > 0) {
        var histHtml = '<div class="fte-ai-summary"><b>\u{1F4CB} Live History Today</b><br><br>';
        histHtml += '<div style="max-height:250px;overflow-y:auto;font-size:0.82rem;">';
        for (var hi = 0; hi < todayEntries.length; hi++) {
          var he = todayEntries[hi];
          histHtml += '<div style="padding:3px 0;">\u{1F534} <b>' + he.name + '</b> went live on <b>' + he.platform + '</b> <span style="color:#64748b;">at ' + formatTime(he.time) + '</span></div>';
        }
        histHtml += '</div>';
        histHtml += '<div style="margin-top:8px;font-size:0.75rem;color:#64748b;">' + todayEntries.length + ' creator(s) detected live during this session.</div>';
        histHtml += '</div>';
        addMessage('ai', histHtml, false);
        speakText(todayEntries.length + ' creators went live today. Check the chat for the full list.');
        setStatus('Ready', '#64748b');
        return;
      }
    }

    // ── Detect query intent ──
    var isNewContentQuery = /new (content|post|video|song|upload|media)|recent (content|post|video|song|upload)|any.*(content|post|video|song|upload).*creator|creator.*(content|post|video|song)|latest.*(post|video|content|upload)|what.*creator.*post/i.test(lower);
    var isRefreshQuery = /refresh|reload|check again|update.*(live|list|status)|fetch.*(live|list)|recheck|re-check|scan.*(creator|live)/i.test(lower);
    // "who is live based on latest check" = fast cached path; "who is live" = full refresh
    var isLatestCheckQuery = /latest check|last check|based on.*(latest|last|recent)|cached|quick check|already.*loaded|without refresh/i.test(lower);
    var isWhoIsLive = /who.*(is |'s )?live|anyone (live|streaming|on)|is anyone (live|on|streaming)|check.*(live|stream)|live (right )?now|streaming (right )?now/i.test(lower);
    var isListQuery = /list.*(my |all )?creator|my creator|show.*(my |all )?creator|all.*(my )?creator/i.test(lower);
    // If user asks for latest check + who is live, skip the full refresh and use cached data
    if (isLatestCheckQuery && isWhoIsLive) { isWhoIsLive = false; isRefreshQuery = false; }

    if (!user || !user.id) {
      addMessage('ai', '<div class="fte-ai-summary">' +
        '<b>Creators</b><br><br>' +
        'You\'re not logged in yet. To track your favorite creators and see who\'s live, you need to sign in.<br><br>' +
        '<a href="/fc/#/guest" target="_blank" style="color:#818cf8;">Open FavCreators</a> to sign in or create an account.<br><br>' +
        'Once logged in, I can:<br>' +
        '\u2022 Refresh your creators\' live status in real-time<br>' +
        '\u2022 Show you who\'s streaming right now<br>' +
        '\u2022 Check for new posts, videos, and content<br>' +
        '\u2022 Open a stream for you instantly</div>');
      setStatus('Ready', '#64748b');
      return;
    }

    try {
      // ═══ STEP 1: Fetch creator list ═══
      showLoadingBar('Step 1/3: Loading your creator list...');
      updateLoadingBar(5);
      setStatus('Loading creators...', '#a5b4fc');

      var resp = await fetch(CONFIG.fcApi + '/get_my_creators.php?user_id=' + user.id + '&t=' + Date.now(), { credentials: 'include' });
      var data = await resp.json();
      var creators = data.creators || data || [];
      updateLoadingBar(15);

      if (!creators.length) {
        removeLoadingBar();
        addMessage('ai', '<div class="fte-ai-summary"><b>Creators</b><br><br>' +
          'You haven\'t added any creators yet.<br><br>' +
          '<a href="/fc/" target="_blank" style="color:#818cf8;">Open FavCreators</a> to add your favorite streamers from Twitch, TikTok, Kick, and YouTube.<br><br>' +
          'Once you\'ve added some, say <b>"refresh my creators"</b> and I\'ll check who\'s live for you!</div>');
        setStatus('Ready', '#64748b');
        return;
      }

      // ═══ STEP 2: NEW CONTENT QUERY — use real cached updates + status_updates API ═══
      if (isNewContentQuery) {
        var hoursBack = parseCreatorTimeFilter(lower) || 48;
        var cutoff = new Date(Date.now() - hoursBack * 3600000);
        var timeLabel = hoursBack <= 24 ? 'past 24 hours' :
          hoursBack <= 48 ? 'past 48 hours' :
            hoursBack <= 72 ? 'past 3 days' :
              hoursBack <= 168 ? 'past week' :
                hoursBack <= 336 ? 'past 2 weeks' : 'past month';

        updateLoadingLabel('Step 2/3: Fetching latest content from platforms...');
        updateLoadingBar(25);
        setStatus('Checking platforms...', '#a5b4fc');

        // First try get_cached_updates for this user — it fetches from the real DB
        var updatesArr = [];
        try {
          var updResp = await fetch(CONFIG.fcApi + '/get_cached_updates.php?user_id=' + user.id, { credentials: 'include' });
          var updData = await updResp.json();
          if (updData.ok && updData.updates) {
            updatesArr = updData.updates;
          }
        } catch (e) { /* fall back to status_updates */ }

        updateLoadingBar(45);

        // Also check status_updates with time filter for broader results
        try {
          var suResp = await fetch(CONFIG.fcApi + '/status_updates.php?since_hours=' + hoursBack + '&limit=100');
          var suData = await suResp.json();
          if (suData.ok && suData.updates) {
            // Merge — deduplicate by content_id
            var existingIds = {};
            for (var ei = 0; ei < updatesArr.length; ei++) {
              if (updatesArr[ei].content_id) existingIds[updatesArr[ei].content_id] = true;
            }
            for (var si = 0; si < suData.updates.length; si++) {
              var su = suData.updates[si];
              if (su.content_id && !existingIds[su.content_id]) {
                updatesArr.push(su);
                existingIds[su.content_id] = true;
              }
            }
          }
        } catch (e) { /* ok */ }

        updateLoadingBar(65);
        updateLoadingLabel('Step 3/3: Analyzing results...');

        // Also check cached live status for currently-live creators
        var liveNow = [];
        try {
          var liveResp = await fetch(CONFIG.fcApi + '/get_live_cached.php?since_minutes=' + Math.ceil(hoursBack * 60));
          var liveData = await liveResp.json();
          if (liveData.ok && liveData.liveNow) liveNow = liveData.liveNow;
        } catch (e) { /* ok */ }

        updateLoadingBar(80);

        // Build a map of my creator IDs for filtering
        var myCreatorIds = {};
        for (var mi = 0; mi < creators.length; mi++) {
          var cid = creators[mi].id || creators[mi]._id;
          if (cid) myCreatorIds[String(cid)] = creators[mi];
        }

        // Filter updates to my creators only
        var myUpdates = [];
        for (var ui = 0; ui < updatesArr.length; ui++) {
          var upd = updatesArr[ui];
          if (upd.creator_id && myCreatorIds[String(upd.creator_id)]) {
            // Check time cutoff
            var pubDate = new Date(upd.content_published_at || upd.last_checked || upd.last_updated);
            if (pubDate >= cutoff || upd.is_live) {
              myUpdates.push(upd);
            }
          }
        }

        // Group by creator
        var byCreator = {};
        for (var gi = 0; gi < myUpdates.length; gi++) {
          var u = myUpdates[gi];
          var key = u.creator_id || u.creator_name;
          if (!byCreator[key]) byCreator[key] = { name: u.creator_name || 'Unknown', items: [], isLive: false };
          byCreator[key].items.push(u);
          if (u.is_live) byCreator[key].isLive = true;
        }

        // Also add live-now creators from the live cache
        for (var li = 0; li < liveNow.length; li++) {
          var lnc = liveNow[li];
          if (lnc.id && myCreatorIds[String(lnc.id)]) {
            var lKey = String(lnc.id);
            if (!byCreator[lKey]) byCreator[lKey] = { name: lnc.name || 'Unknown', items: [], isLive: true };
            else byCreator[lKey].isLive = true;
          }
        }

        updateLoadingBar(100);
        setTimeout(removeLoadingBar, 400);

        var creatorKeys = Object.keys(byCreator);
        var html = '<div class="fte-ai-summary">';
        html += '<b>New content from your creators (' + timeLabel + ')</b><br><br>';

        if (creatorKeys.length > 0) {
          html += '<b>' + creatorKeys.length + ' creator' + (creatorKeys.length !== 1 ? 's' : '') + ' with recent activity:</b><br><br>';
          for (var ck = 0; ck < creatorKeys.length; ck++) {
            var cData = byCreator[creatorKeys[ck]];
            html += '<b>' + escapeHtml(cData.name) + '</b>';
            if (cData.isLive) html += ' <span style="color:#ef4444;font-weight:bold;">LIVE NOW</span>';
            html += '<br>';
            // Show up to 3 recent items per creator
            var shown = 0;
            for (var ci = 0; ci < cData.items.length && shown < 3; ci++) {
              var item = cData.items[ci];
              var typeIcon = item.update_type === 'stream' ? '\u{1F534}' :
                item.update_type === 'video' || item.update_type === 'vod' ? '\u{1F3AC}' :
                  item.update_type === 'post' || item.update_type === 'tweet' ? '\u{1F4DD}' : '\u{1F4E2}';
              html += '  ' + typeIcon + ' ';
              if (item.content_url) {
                html += '<a href="' + escapeHtml(item.content_url) + '" target="_blank" style="color:#818cf8;">';
                html += escapeHtml(item.content_title || item.update_type || 'Link');
                html += '</a>';
              } else {
                html += escapeHtml(item.content_title || item.update_type || 'Activity');
              }
              if (item.platform) html += ' <span style="color:#64748b;font-size:10px;">(' + escapeHtml(item.platform) + ')</span>';
              html += '<br>';
              shown++;
            }
            if (cData.items.length > 3) {
              html += '  <span style="color:#64748b;font-size:11px;">...+' + (cData.items.length - 3) + ' more</span><br>';
            }
            html += '<br>';
          }
        } else {
          // Fall back to checking creator-level data
          var creatorsWithActivity = [];
          for (var fc = 0; fc < creators.length; fc++) {
            var cr = creators[fc];
            var hasRecent = false;
            if (cr.latest_post_date || cr.last_post_date || cr.recent_post_time) {
              var postDate = new Date(cr.latest_post_date || cr.last_post_date || cr.recent_post_time);
              if (postDate >= cutoff) hasRecent = true;
            }
            if (cr.is_live || cr.isLive) hasRecent = true;
            if (hasRecent) creatorsWithActivity.push(cr);
          }
          if (creatorsWithActivity.length > 0) {
            html += '<b>' + creatorsWithActivity.length + ' creator' + (creatorsWithActivity.length !== 1 ? 's' : '') + ' with recent activity:</b><br><br>';
            for (var fa = 0; fa < creatorsWithActivity.length; fa++) {
              var fcr = creatorsWithActivity[fa];
              html += '\u2022 <b>' + escapeHtml(fcr.name || fcr.display_name || 'Unknown') + '</b>';
              if (fcr.is_live || fcr.isLive) html += ' \u2014 <span style="color:#ef4444;">LIVE NOW</span>';
              var cUrl = fcr.url || fcr.stream_url || fcr.channel_url;
              if (cUrl) html += ' \u2014 <a href="' + escapeHtml(cUrl) + '" target="_blank" style="color:#818cf8;">Visit</a>';
              html += '<br>';
            }
          } else {
            html += 'No new content detected from your ' + creators.length + ' tracked creators in the ' + timeLabel + '.<br><br>';
            html += 'Try expanding the time range: <b>"new content past week"</b> or <b>"new content past month"</b><br><br>';
            html += '<a href="/fc/" target="_blank" style="color:#818cf8;">Open FavCreators</a> for the full feed.';
          }
        }
        html += '</div>';
        addMessage('ai', html, false);
        speakText(creatorKeys.length > 0 ?
          creatorKeys.length + ' of your creators have new activity in the ' + timeLabel + '. Check the details in the chat.' :
          'No new content from your creators in the ' + timeLabel + '. Try expanding the time range or check back later.');
        setStatus('Ready', '#64748b');
        return;
      }

      // ═══ STEP 2 (REFRESH / WHO IS LIVE): Real platform-by-platform live check ═══
      if (isRefreshQuery || isWhoIsLive) {
        var accounts = collectRefreshableAccounts(creators);

        if (accounts.length === 0) {
          // No checkable accounts — fall back to cached live status
          updateLoadingLabel('Step 2/3: Checking cached live status...');
          updateLoadingBar(40);

          var cachedLive = [];
          try {
            var clResp = await fetch(CONFIG.fcApi + '/get_live_cached.php?since_minutes=60');
            var clData = await clResp.json();
            if (clData.ok && clData.liveNow) cachedLive = clData.liveNow;
          } catch (e) { /* ok */ }
          updateLoadingBar(100);
          setTimeout(removeLoadingBar, 400);

          // Filter to only my creators
          var myCreatorMap = {};
          for (var mc = 0; mc < creators.length; mc++) {
            var mcId = creators[mc].id || creators[mc]._id;
            if (mcId) myCreatorMap[String(mcId)] = creators[mc];
          }
          var myLive = cachedLive.filter(function (c) { return c.id && myCreatorMap[String(c.id)]; });

          var html3 = '<div class="fte-ai-summary">';
          html3 += '<b>Your Creators (' + creators.length + ' tracked)</b><br><br>';
          if (myLive.length > 0) {
            html3 += '<span style="color:#22c55e;font-weight:bold;">' + myLive.length + ' LIVE right now:</span><br><br>';
            for (var ml = 0; ml < myLive.length; ml++) {
              var mlc = myLive[ml];
              html3 += '<b>' + escapeHtml(mlc.name || 'Unknown') + '</b>';
              if (mlc.platforms && mlc.platforms.length > 0) {
                for (var mpl = 0; mpl < mlc.platforms.length; mpl++) {
                  var mp = mlc.platforms[mpl];
                  if (mp.isLive) {
                    html3 += ' on ' + escapeHtml(mp.platform);
                    if (mp.streamTitle) html3 += ': "' + escapeHtml(mp.streamTitle) + '"';
                    if (mp.viewerCount) html3 += ' (' + mp.viewerCount + ' viewers)';
                  }
                }
              }
              html3 += '<br>';
            }
          } else {
            html3 += 'None of your creators are live right now.<br>';
          }
          html3 += '<br><span style="color:#64748b;font-size:11px;">Note: Your creators don\'t have live-check accounts configured. Open <a href="/fc/" target="_blank" style="color:#818cf8;">FavCreators</a> to enable live checking on their Twitch/Kick/YouTube accounts.</span>';
          html3 += '</div>';
          addMessage('ai', html3, false);
          speakText(myLive.length > 0 ?
            myLive.length + ' of your creators are live right now. Check the chat for details.' :
            'None of your creators are live right now. I\'ll check again if you ask later.');
          setStatus('Ready', '#64748b');
          return;
        }

        // We have accounts to check — do the REAL server-side refresh
        var totalAccounts = accounts.length;
        updateLoadingLabel('Step 2/3: Refreshing live status for ' + totalAccounts + ' account' + (totalAccounts !== 1 ? 's' : '') + '...');
        updateLoadingBar(20);
        setStatus('Checking ' + totalAccounts + ' accounts...', '#a5b4fc');

        addMessage('ai', '<div style="font-size:12px;color:#a5b4fc;">Checking <b>' + totalAccounts + '</b> account' + (totalAccounts !== 1 ? 's' : '') + ' across ' + creators.length + ' creators. This may take a moment...</div>', false);

        // Batch the accounts in groups of 5 to avoid overwhelming the server
        var batchSize = 5;
        var allResults = [];
        var checkedSoFar = 0;
        var errors = 0;

        for (var bStart = 0; bStart < accounts.length; bStart += batchSize) {
          if (state.cancelled) {
            removeLoadingBar();
            addMessage('ai', 'Refresh cancelled. Here\'s what I found so far:');
            break;
          }

          var batch = accounts.slice(bStart, Math.min(bStart + batchSize, accounts.length));
          var batchLabel = 'Checking ' + (bStart + 1) + '-' + Math.min(bStart + batchSize, accounts.length) + ' of ' + totalAccounts + '...';
          updateLoadingLabel(batchLabel);

          try {
            var batchResp = await fetch(CONFIG.fcApi + '/refresh_updates.php', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ accounts: batch })
            });
            var batchData = await batchResp.json();
            if (batchData.ok && batchData.results) {
              for (var br = 0; br < batchData.results.length; br++) {
                allResults.push(batchData.results[br]);
              }
              errors += (batchData.errors || 0);
            }
          } catch (e) {
            errors += batch.length;
          }

          checkedSoFar += batch.length;
          var pct = 20 + Math.round((checkedSoFar / totalAccounts) * 60);
          updateLoadingBar(pct);
        }

        updateLoadingLabel('Step 3/3: Building your results...');
        updateLoadingBar(90);

        // Also sync live status to the cache for future quick lookups
        var liveResults = allResults.filter(function (r) { return r.ok && r.is_live; });
        if (liveResults.length > 0) {
          try {
            // Build sync payload from live results
            var syncPayload = [];
            for (var sr = 0; sr < liveResults.length; sr++) {
              var lr = liveResults[sr];
              syncPayload.push({
                id: lr.creator_id,
                name: lr.creator_name || lr.username,
                accounts: [{
                  platform: lr.platform,
                  username: lr.username,
                  isLive: true,
                  streamTitle: (lr.updates && lr.updates.length > 0 && lr.updates[0].content_title) || '',
                  viewerCount: (lr.updates && lr.updates.length > 0 && lr.updates[0].viewer_count) || 0,
                  checkMethod: 'ai_assistant_refresh'
                }]
              });
            }
            await fetch(CONFIG.fcApi + '/sync_live_status.php', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ creators: syncPayload })
            });
          } catch (e) { /* non-critical */ }
        }

        updateLoadingBar(100);
        setTimeout(removeLoadingBar, 500);

        // ── Build the results display ──
        var liveCreatorsList = [];
        var offlineCreatorsList = [];
        var contentFound = [];
        var resultByCreator = {};

        for (var ri = 0; ri < allResults.length; ri++) {
          var res = allResults[ri];
          var cKey = res.creator_id || res.username;
          if (!resultByCreator[cKey]) {
            resultByCreator[cKey] = {
              name: res.creator_name || res.username || 'Unknown',
              creator_id: res.creator_id,
              platforms: [],
              isLive: false,
              updates: []
            };
          }
          resultByCreator[cKey].platforms.push(res.platform);
          if (res.is_live) resultByCreator[cKey].isLive = true;
          if (res.updates_count > 0 && res.updates) {
            for (var rui = 0; rui < res.updates.length; rui++) {
              resultByCreator[cKey].updates.push(res.updates[rui]);
            }
          }
        }

        var rKeys = Object.keys(resultByCreator);
        for (var rk = 0; rk < rKeys.length; rk++) {
          var rData = resultByCreator[rKeys[rk]];
          if (rData.isLive) liveCreatorsList.push(rData);
          else offlineCreatorsList.push(rData);
          if (rData.updates.length > 0) contentFound.push(rData);
        }

        var html2 = '<div class="fte-ai-summary">';
        html2 += '<b>Creator Refresh Complete</b> ';
        html2 += '<span style="color:#22c55e;font-size:11px;">\u2713 ' + checkedSoFar + ' account' + (checkedSoFar !== 1 ? 's' : '') + ' checked</span>';
        if (errors > 0) html2 += ' <span style="color:#f59e0b;font-size:11px;">(' + errors + ' failed)</span>';
        html2 += '<br><br>';

        if (liveCreatorsList.length > 0) {
          html2 += '<span style="color:#22c55e;font-weight:bold;">' + liveCreatorsList.length + ' LIVE RIGHT NOW:</span><br>';
          for (var lci = 0; lci < liveCreatorsList.length; lci++) {
            var live = liveCreatorsList[lci];
            html2 += '\u{1F534} <b>' + escapeHtml(live.name) + '</b>';
            html2 += ' (' + escapeHtml(live.platforms.join(', ')) + ')';
            // Show stream title if available
            var streamUpdate = null;
            for (var sui = 0; sui < live.updates.length; sui++) {
              if (live.updates[sui].is_live) { streamUpdate = live.updates[sui]; break; }
            }
            if (streamUpdate) {
              if (streamUpdate.content_title) html2 += '<br>  \u{1F3AC} "' + escapeHtml(streamUpdate.content_title) + '"';
              if (streamUpdate.viewer_count) html2 += ' \u2014 ' + streamUpdate.viewer_count + ' viewers';
              if (streamUpdate.content_url) html2 += '<br>  <a href="' + escapeHtml(streamUpdate.content_url) + '" target="_blank" style="color:#818cf8;">Watch now \u2192</a>';
            }
            html2 += '<br><br>';
          }
        } else {
          html2 += 'None of your creators are live right now.<br><br>';
        }

        // Show recent content found during refresh
        if (contentFound.length > 0) {
          var totalContent = 0;
          for (var tci = 0; tci < contentFound.length; tci++) totalContent += contentFound[tci].updates.length;
          html2 += '<b>Recent content found (' + totalContent + ' items):</b><br>';
          for (var cfi = 0; cfi < Math.min(5, contentFound.length); cfi++) {
            var cf = contentFound[cfi];
            html2 += '\u2022 <b>' + escapeHtml(cf.name) + '</b>: ';
            var firstUpdate = cf.updates[0];
            if (firstUpdate.content_url) {
              html2 += '<a href="' + escapeHtml(firstUpdate.content_url) + '" target="_blank" style="color:#818cf8;">';
              html2 += escapeHtml(firstUpdate.content_title || firstUpdate.update_type || 'New content');
              html2 += '</a>';
            } else {
              html2 += escapeHtml(firstUpdate.content_title || firstUpdate.update_type || 'New content');
            }
            if (cf.updates.length > 1) html2 += ' (+' + (cf.updates.length - 1) + ' more)';
            html2 += '<br>';
          }
          if (contentFound.length > 5) html2 += '<span style="color:#64748b;font-size:11px;">...and ' + (contentFound.length - 5) + ' more creators with content</span><br>';
          html2 += '<br>';
        }

        // Show offline creators summary
        if (offlineCreatorsList.length > 0 && liveCreatorsList.length > 0) {
          html2 += '<span style="color:#64748b;font-size:11px;">' + offlineCreatorsList.length + ' offline: ';
          var offlineNames = [];
          for (var oi = 0; oi < Math.min(8, offlineCreatorsList.length); oi++) {
            offlineNames.push(offlineCreatorsList[oi].name);
          }
          html2 += escapeHtml(offlineNames.join(', '));
          if (offlineCreatorsList.length > 8) html2 += ', +' + (offlineCreatorsList.length - 8) + ' more';
          html2 += '</span><br>';
        }

        // Offer to open the first live stream
        if (liveCreatorsList.length > 0) {
          var firstLive = liveCreatorsList[0];
          // Find stream URL: look up creator from original list to get account URLs
          var streamInfo = null;
          for (var fli = 0; fli < creators.length; fli++) {
            var flc = creators[fli];
            if ((flc.id && flc.id === firstLive.creator_id) || (flc.name && flc.name === firstLive.name)) {
              streamInfo = getBestStreamInfo(flc);
              break;
            }
          }
          if (!streamInfo && firstLive.platforms && firstLive.platforms.length > 0) {
            // Fallback: build URL from platform + name
            var flPlatform = firstLive.platforms[0];
            var flUsername = (firstLive.name || '').toLowerCase().replace(/[^a-z0-9_.]/g, '');
            var flUrl = buildStreamUrl(flPlatform, flUsername);
            if (flUrl) streamInfo = { name: firstLive.name, platform: flPlatform, url: flUrl };
          }
          html2 += '<br>Want me to open <b>' + escapeHtml(firstLive.name) + '</b>\'s stream?';
          if (streamInfo) state.lastOfferedCreator = streamInfo;
        }

        html2 += '</div>';
        addMessage('ai', html2, false);

        if (liveCreatorsList.length > 0) {
          setPrompts(['Yes, open it', 'No thanks', 'Refresh my creators']);
          speakText(liveCreatorsList.length + ' of your creators are live right now! ' +
            liveCreatorsList[0].name + ' is streaming. Would you like me to open their stream?');
        } else {
          speakText('Refresh complete. ' + checkedSoFar + ' accounts checked across ' + creators.length + ' creators. Nobody is live right now, but check back later!');
        }
        setStatus('Ready', '#64748b');
        return;
      }

      // ═══ DEFAULT: Simple creator list with cached live status ═══
      removeLoadingBar();

      // Quick check cached live data
      var quickLive = [];
      try {
        var qlResp = await fetch(CONFIG.fcApi + '/get_live_cached.php?since_minutes=60');
        var qlData = await qlResp.json();
        if (qlData.ok && qlData.liveNow) quickLive = qlData.liveNow;
      } catch (e) { /* ok */ }

      var myIds = {};
      for (var mi2 = 0; mi2 < creators.length; mi2++) {
        var cid2 = creators[mi2].id || creators[mi2]._id;
        if (cid2) myIds[String(cid2)] = creators[mi2];
      }
      var myLiveNow = quickLive.filter(function (c) { return c.id && myIds[String(c.id)]; });

      // Also check creator-level flags
      var creatorLevelLive = creators.filter(function (c) { return c.is_live || c.isLive; });
      // Merge
      var liveMap = {};
      for (var mln = 0; mln < myLiveNow.length; mln++) liveMap[String(myLiveNow[mln].id)] = myLiveNow[mln];
      for (var cll = 0; cll < creatorLevelLive.length; cll++) {
        var clId = String(creatorLevelLive[cll].id || creatorLevelLive[cll]._id);
        if (!liveMap[clId]) liveMap[clId] = creatorLevelLive[cll];
      }
      var allLive = [];
      var liveMapKeys = Object.keys(liveMap);
      for (var lmk = 0; lmk < liveMapKeys.length; lmk++) allLive.push(liveMap[liveMapKeys[lmk]]);

      var htmlDef = '<div class="fte-ai-summary">';
      htmlDef += '<b>Your Creators (' + creators.length + ' tracked)</b><br><br>';

      if (allLive.length > 0) {
        htmlDef += '<span style="color:#22c55e;font-weight:bold;">' + allLive.length + ' LIVE right now:</span><br>';
        for (var ali = 0; ali < allLive.length; ali++) {
          var al = allLive[ali];
          htmlDef += '\u{1F534} <b>' + escapeHtml(al.name || al.display_name || 'Unknown') + '</b>';
          if (al.platforms && al.platforms.length > 0) {
            for (var alp = 0; alp < al.platforms.length; alp++) {
              if (al.platforms[alp].isLive) htmlDef += ' on ' + escapeHtml(al.platforms[alp].platform);
            }
          } else if (al.platform) {
            htmlDef += ' (' + escapeHtml(al.platform) + ')';
          }
          htmlDef += '<br>';
        }
        var defStreamInfo = getBestStreamInfo(allLive[0]);
        htmlDef += '<br>Want me to open <b>' + escapeHtml(allLive[0].name || allLive[0].display_name || 'the first stream') + '</b>\'s stream?<br>';
        if (defStreamInfo) state.lastOfferedCreator = defStreamInfo;
      } else {
        htmlDef += 'None of your creators are live right now.<br>';
      }

      htmlDef += '<br><span style="color:#64748b;font-size:11px;">Tracked: ';
      var trackedNames = [];
      for (var tn = 0; tn < Math.min(10, creators.length); tn++) {
        trackedNames.push(creators[tn].name || creators[tn].display_name || 'Unknown');
      }
      htmlDef += escapeHtml(trackedNames.join(', '));
      if (creators.length > 10) htmlDef += ', +' + (creators.length - 10) + ' more';
      htmlDef += '</span>';

      htmlDef += '<br><br>Say <b>"refresh my creators"</b> for a real-time live check across all platforms.';
      htmlDef += '</div>';
      addMessage('ai', htmlDef, false);

      if (allLive.length > 0) {
        setPrompts(['Yes, open it', 'No thanks', 'Refresh my creators']);
        speakText(allLive.length + ' of your creators are live right now. ' + (allLive[0].name || allLive[0].display_name) + ' is streaming. Would you like me to open their stream?');
      } else {
        speakText('You have ' + creators.length + ' tracked creators. None are live right now. Say refresh my creators for a real-time check across all platforms.');
      }
      setStatus('Ready', '#64748b');
    } catch (err) {
      removeLoadingBar();
      addMessage('ai', 'I couldn\'t fetch your creator data. Please try again or visit <a href="/fc/" target="_blank" style="color:#818cf8;">FavCreators</a> directly.');
      setStatus('Ready', '#64748b');
    }
  }

  // ═══════════════════════════════════════════════════════════
  // HANDLERS: ACCOUNTABILITY (smart, context-aware)
  // ═══════════════════════════════════════════════════════════

  // ── Smart greeting shown when opening AI on accountability page ──
  async function showAccountabilityGreeting() {
    var auth = getAccountabilityAuth();
    if (!auth.hasAuth) {
      addMessage('ai', '<div class="fte-ai-summary">' +
        '<b>\u{1F3AF} Get Started with Accountability</b><br><br>' +
        'You\'re not signed in yet. To start tracking goals and building streaks:<br><br>' +
        '\u2022 <b>Sign in</b> with your FavCreators account, or<br>' +
        '\u2022 <b>Link your Discord</b> if you use the Accountability Bot<br><br>' +
        'Once linked, I\'ll track your tasks, remind you about deadlines, and help you stay consistent.' +
        '<br><br><a href="/fc/#/accountability" target="_blank" style="color:#818cf8;">Set up now \u2192</a></div>', false);
      return;
    }
    var data = await fetchAccountabilityDashboard();
    if (!data) return; // fetch failed silently

    var tasks = data.tasks || [];
    var stats = data.stats || {};
    var checkins = data.recent_checkins || [];
    var now = new Date();
    var todayStr = now.toISOString().split('T')[0];

    // ── No tasks at all ──
    if (tasks.length === 0) {
      var tip = getRandomMotivationTip();
      addMessage('ai', '<div class="fte-ai-summary">' +
        '<b>\u{1F6A8} You haven\'t set up any tasks yet!</b><br><br>' +
        'The accountability system works best when you have at least one trackable goal. Here\'s how to get started:<br><br>' +
        '\u2022 Click <b>"Add Task"</b> on the dashboard above<br>' +
        '\u2022 Pick a task type (Gym, Reading, Meditation, Custom...)<br>' +
        '\u2022 Set your <b>frequency</b> (e.g., 4x per week)<br>' +
        '\u2022 Define <b>success criteria</b> \u2014 what counts as a check-in?<br>' +
        '\u2022 Add a <b>punishment</b> for missed goals (loss aversion works!)<br><br>' +
        'Start small \u2014 the 2-Minute Rule says just <i>showing up</i> is what matters.' +
        formatMotivationTipHtml(tip) +
        '</div>', false);
      speakText('You haven\'t set up any tasks yet. Click Add Task on the dashboard to create your first goal. Start small!');
      return;
    }

    // ── Has tasks: analyze state ──
    var html = '<div class="fte-ai-summary">';
    var behindTasks = [];
    var dueSoonTasks = [];
    var onTrackTasks = [];
    var completedTasks = [];
    var pausedTasks = [];

    for (var i = 0; i < tasks.length; i++) {
      var t = tasks[i];
      if (t.is_paused) { pausedTasks.push(t); continue; }
      var remaining = Math.max(0, t.target_per_period - t.completions_this_period);
      var endDate = t.extended_deadline && t.extended_deadline > t.period_end ? t.extended_deadline : t.period_end;
      var daysLeft = daysBetween(todayStr, endDate);
      if (new Date(endDate) < now) daysLeft = -daysBetween(endDate, todayStr);

      if (remaining <= 0) {
        completedTasks.push(t);
      } else if (daysLeft < 0) {
        behindTasks.push({ task: t, remaining: remaining, daysLeft: daysLeft, endDate: endDate });
      } else if (remaining > daysLeft) {
        // Behind: need more check-ins than days left
        behindTasks.push({ task: t, remaining: remaining, daysLeft: daysLeft, endDate: endDate });
      } else if (daysLeft <= 2) {
        dueSoonTasks.push({ task: t, remaining: remaining, daysLeft: daysLeft, endDate: endDate });
      } else {
        onTrackTasks.push(t);
      }
    }

    // ── Check-in status ──
    var totalCheckins = stats.total_checkins || 0;
    if (totalCheckins === 0) {
      html += '<b>\u{1F6A8} You haven\'t completed a single check-in yet!</b><br><br>';
      html += 'You have <b>' + tasks.length + ' task' + (tasks.length !== 1 ? 's' : '') + '</b> set up \u2014 great start! ' +
        'But the real magic happens when you start <b>checking in</b>. Each check-in is a vote for the person you\'re becoming.<br><br>';
      html += '\u{1F449} Tap the <b>"\u2705 Check In"</b> button on any task to log your first one.<br>';
    } else {
      // ── Behind on tasks ──
      if (behindTasks.length > 0) {
        html += '<b>\u26A0\uFE0F Heads up \u2014 you\'re behind on ' + behindTasks.length + ' task' + (behindTasks.length !== 1 ? 's' : '') + ':</b><br><br>';
        for (var b = 0; b < behindTasks.length; b++) {
          var bt = behindTasks[b];
          var tName = bt.task.custom_name || bt.task.task_type || 'Task';
          var canCatchUp = bt.daysLeft >= 0 && bt.remaining <= (bt.daysLeft + 1) * 2; // could do 2x per day
          html += '\u{1F534} <b>' + escapeHtml(tName) + '</b> \u2014 ';
          if (bt.daysLeft < 0) {
            html += '<span style="color:#ef4444;">Period ended ' + Math.abs(bt.daysLeft) + ' day' + (Math.abs(bt.daysLeft) !== 1 ? 's' : '') + ' ago</span>';
            html += ' with <b>' + bt.remaining + '</b> check-in' + (bt.remaining !== 1 ? 's' : '') + ' still needed. ';
            html += '<span style="color:#f59e0b;">This period is missed, but a new one starts fresh. Never miss twice!</span>';
          } else {
            html += '<b>' + bt.remaining + '</b> check-in' + (bt.remaining !== 1 ? 's' : '') + ' needed, <b>' + bt.daysLeft + '</b> day' + (bt.daysLeft !== 1 ? 's' : '') + ' left. ';
            if (canCatchUp) {
              html += '<span style="color:#22c55e;">You can still catch up! Show up ' + (bt.daysLeft > 0 ? Math.ceil(bt.remaining / bt.daysLeft) + 'x per day' : bt.remaining + ' times today') + ' to meet your goal.</span>';
            } else {
              html += '<span style="color:#f59e0b;">It\'ll be tough to catch up, but show up anyway \u2014 every check-in counts. Do your best!</span>';
            }
          }
          html += '<br>';
        }
        html += '<br>';
      }

      // ── Due soon ──
      if (dueSoonTasks.length > 0) {
        html += '<b>\u23F0 Coming due soon:</b><br>';
        for (var d = 0; d < dueSoonTasks.length; d++) {
          var dt = dueSoonTasks[d];
          var dtName = dt.task.custom_name || dt.task.task_type || 'Task';
          html += '\u{1F7E1} <b>' + escapeHtml(dtName) + '</b> \u2014 ' + dt.remaining + ' check-in' + (dt.remaining !== 1 ? 's' : '') + ' left, due ' + (dt.daysLeft === 0 ? '<b>today</b>' : 'in <b>' + dt.daysLeft + ' day' + (dt.daysLeft !== 1 ? 's' : '') + '</b>') + '<br>';
        }
        html += '<br>';
      }

      // ── Last check-in timing ──
      if (checkins.length > 0) {
        var lastCheckin = checkins[0]; // most recent
        var lastDate = lastCheckin.checkin_time ? lastCheckin.checkin_time.split(' ')[0] : null;
        if (lastDate) {
          var daysSince = daysBetween(lastDate, todayStr);
          if (daysSince >= 3) {
            html += '\u{1F4AD} <b>It\'s been ' + daysSince + ' days since your last check-in</b>';
            if (lastCheckin.task_name) html += ' (' + escapeHtml(lastCheckin.task_name) + ')';
            html += '. ';
            if (daysSince >= 7) {
              html += 'That\'s over a week \u2014 but remember, <b>right now IS a fresh start</b>. Don\'t let a gap become a quit.';
            } else {
              html += 'Time to get back on track! The hardest part is just showing up.';
            }
            html += '<br><br>';
          }
        }
      }

      // ── On-track summary ──
      if (onTrackTasks.length > 0) {
        html += '\u2705 <b>' + onTrackTasks.length + ' task' + (onTrackTasks.length !== 1 ? 's' : '') + ' on track</b>';
        if (completedTasks.length > 0) html += ', <b>' + completedTasks.length + '</b> completed this period';
        html += '.<br>';
      }

      // ── Streaks ──
      var highestStreak = stats.highest_streak || 0;
      if (highestStreak > 0) {
        html += '\u{1F525} Best streak: <b>' + highestStreak + ' days</b>. ';
        var activeStreaks = tasks.filter(function(t) { return t.current_streak > 0; });
        if (activeStreaks.length > 0) {
          html += 'Active: ' + activeStreaks.map(function(t) { return '<b>' + (t.custom_name || t.task_type) + '</b> (' + t.current_streak + 'd)'; }).join(', ') + '.';
        }
        html += '<br>';
      }
    }

    // ── Random motivational tip ──
    var tip = getRandomMotivationTip();
    html += formatMotivationTipHtml(tip);
    html += '<div style="margin-top:8px;text-align:center;"><a href="/fc/motivation.html" target="_blank" style="color:#818cf8;font-size:0.75rem;">Read all 10 research-backed techniques \u2192</a></div>';
    html += '</div>';
    addMessage('ai', html, false);

    // Speak a quick summary
    var spokenSummary = '';
    if (behindTasks.length > 0) spokenSummary += 'You\'re behind on ' + behindTasks.length + ' task' + (behindTasks.length !== 1 ? 's' : '') + '. ';
    if (dueSoonTasks.length > 0) spokenSummary += dueSoonTasks.length + ' task' + (dueSoonTasks.length !== 1 ? 's are' : ' is') + ' coming due soon. ';
    if (totalCheckins === 0) spokenSummary += 'You haven\'t checked in yet — tap check in on any task to start! ';
    spokenSummary += tip.title + ': ' + tip.tip.replace(/<[^>]*>/g, '');
    speakText(spokenSummary);
  }

  // ── Main accountability handler (for explicit commands) ──
  async function handleAccountability(lower) {
    var auth = getAccountabilityAuth();
    if (!auth.hasAuth) {
      addMessage('ai', '<div class="fte-ai-summary"><b>\u{1F3AF} Accountability</b><br><br>' +
        'You need to be signed in to use accountability features.<br><br>' +
        '\u2022 <b>Sign in</b> to FavCreators, or<br>' +
        '\u2022 <b>Link your Discord ID</b> on the dashboard<br><br>' +
        '<a href="/fc/#/accountability" target="_blank" style="color:#818cf8;">Open the Accountability Dashboard \u2192</a></div>');
      setStatus('Ready', '#64748b');
      return;
    }

    // ── Motivational push ──
    if (/motiv|push|inspire|pep talk|random tip|give me.*(push|boost|tip)/i.test(lower)) {
      var tip = getRandomMotivationTip();
      var html = '<div class="fte-ai-summary"><b>\u{1F4AA} Motivational Push</b><br>';
      html += formatMotivationTipHtml(tip);
      html += '<br><a href="/fc/motivation.html" target="_blank" style="color:#818cf8;font-size:0.8rem;">Read all 10 research-backed techniques \u2192</a>';
      html += '</div>';
      addMessage('ai', html, false);
      speakText(tip.title + '. ' + tip.tip.replace(/<[^>]*>/g, ''));
      setStatus('Ready', '#64748b');
      return;
    }

    setStatus('Checking tasks...', '#a5b4fc');
    var data = await fetchAccountabilityDashboard();

    if (!data) {
      addMessage('ai', 'I couldn\'t fetch your accountability data right now. <a href="/fc/#/accountability" target="_blank" style="color:#818cf8;">Open the dashboard directly</a>.');
      setStatus('Ready', '#64748b');
      return;
    }

    var tasks = data.tasks || [];
    var stats = data.stats || {};
    var checkins = data.recent_checkins || [];
    var now = new Date();
    var todayStr = now.toISOString().split('T')[0];

    // ── No tasks ──
    if (tasks.length === 0) {
      var setupTip = getRandomMotivationTip();
      addMessage('ai', '<div class="fte-ai-summary">' +
        '<b>\u{1F3AF} You haven\'t set up any tasks yet!</b><br><br>' +
        'Here\'s how to get started in 30 seconds:<br><br>' +
        '<b>1.</b> Click <b>"Add Task"</b> on the dashboard above<br>' +
        '<b>2.</b> Pick a task type (Gym, Reading, Meditation, Custom...)<br>' +
        '<b>3.</b> Set your target frequency (e.g., 4x per week)<br>' +
        '<b>4.</b> Define what counts as a check-in ("Did I go to the gym?")<br>' +
        '<b>5.</b> Add a punishment for missed goals \u2014 loss aversion makes you <b>2x more likely</b> to follow through<br><br>' +
        'Pro tip: Start with just <b>one task</b>. Nail it consistently before adding more.' +
        formatMotivationTipHtml(setupTip) +
        '</div>', false);
      speakText('You haven\'t set up any tasks yet. Click Add Task on the dashboard to create your first goal.');
      setStatus('Ready', '#64748b');
      return;
    }

    // ── Overdue / behind analysis ──
    if (/behind|overdue|late|miss|catch up|falling behind|off track|how.*doing/i.test(lower)) {
      var behindItems = [];
      var dueItems = [];
      for (var i = 0; i < tasks.length; i++) {
        var t = tasks[i];
        if (t.is_paused) continue;
        var rem = Math.max(0, t.target_per_period - t.completions_this_period);
        if (rem <= 0) continue;
        var endDate = t.extended_deadline && t.extended_deadline > t.period_end ? t.extended_deadline : t.period_end;
        var dLeft = daysBetween(todayStr, endDate);
        if (new Date(endDate) < now) dLeft = -daysBetween(endDate, todayStr);
        if (dLeft < 0 || rem > dLeft) {
          behindItems.push({ task: t, remaining: rem, daysLeft: dLeft, endDate: endDate });
        } else if (dLeft <= 3) {
          dueItems.push({ task: t, remaining: rem, daysLeft: dLeft });
        }
      }

      var bhtml = '<div class="fte-ai-summary">';
      if (behindItems.length === 0 && dueItems.length === 0) {
        bhtml += '<b>\u2705 You\'re on track!</b><br><br>All your tasks are looking good. Keep it up \u2014 consistency is what builds character.<br>';
        var activeStreaks = tasks.filter(function(t) { return t.current_streak > 0 && !t.is_paused; });
        if (activeStreaks.length > 0) {
          bhtml += '<br>\u{1F525} Active streaks: ' + activeStreaks.map(function(t) { return '<b>' + escapeHtml(t.custom_name || t.task_type) + '</b> (' + t.current_streak + ' days)'; }).join(', ') + '<br>';
        }
      } else {
        if (behindItems.length > 0) {
          bhtml += '<b>\u26A0\uFE0F Behind on ' + behindItems.length + ' task' + (behindItems.length !== 1 ? 's' : '') + ':</b><br><br>';
          for (var bi = 0; bi < behindItems.length; bi++) {
            var bit = behindItems[bi];
            var bitName = bit.task.custom_name || bit.task.task_type || 'Task';
            bhtml += '\u{1F534} <b>' + escapeHtml(bitName) + '</b><br>';
            bhtml += '&nbsp;&nbsp;Progress: <b>' + bit.task.completions_this_period + '/' + bit.task.target_per_period + '</b> check-ins<br>';
            if (bit.daysLeft < 0) {
              bhtml += '&nbsp;&nbsp;<span style="color:#ef4444;">Period ended ' + Math.abs(bit.daysLeft) + ' day' + (Math.abs(bit.daysLeft) !== 1 ? 's' : '') + ' ago.</span> This goal is missed for this period.<br>';
              bhtml += '&nbsp;&nbsp;\u{1F4A1} But a <b>fresh start</b> is coming with the new period. The Fresh Start Effect says: treat it as a clean slate!<br>';
            } else {
              var canDoDouble = bit.remaining <= (bit.daysLeft + 1) * 2;
              bhtml += '&nbsp;&nbsp;<b>' + bit.remaining + '</b> needed in <b>' + bit.daysLeft + '</b> day' + (bit.daysLeft !== 1 ? 's' : '') + '. ';
              if (canDoDouble) {
                var perDay = bit.daysLeft > 0 ? Math.ceil(bit.remaining / (bit.daysLeft + 1)) : bit.remaining;
                bhtml += '<span style="color:#22c55e;">You CAN catch up by checking in <b>' + perDay + 'x per day</b>!</span>';
                if (perDay >= 2) bhtml += ' Show up twice if you need to \u2014 doubled sessions count.';
              } else {
                bhtml += '<span style="color:#f59e0b;">Catching up will be tough, but <b>every check-in still matters</b>. Do what you can.</span>';
              }
              bhtml += '<br>';
            }
            bhtml += '<br>';
          }
        }
        if (dueItems.length > 0) {
          bhtml += '<b>\u23F0 Due soon:</b><br>';
          for (var di = 0; di < dueItems.length; di++) {
            var dit = dueItems[di];
            var ditName = dit.task.custom_name || dit.task.task_type || 'Task';
            bhtml += '\u{1F7E1} <b>' + escapeHtml(ditName) + '</b> \u2014 ' + dit.remaining + ' left, ' + (dit.daysLeft === 0 ? 'due <b>today</b>' : dit.daysLeft + ' day' + (dit.daysLeft !== 1 ? 's' : '') + ' left') + '<br>';
          }
        }
      }
      bhtml += formatMotivationTipHtml(getRandomMotivationTip());
      bhtml += '</div>';
      addMessage('ai', bhtml, false);
      setStatus('Ready', '#64748b');
      return;
    }

    // ── How to set up a task ──
    if (/set up|create|add|how.*(task|goal)|get started|new task/i.test(lower)) {
      var setupHtml = '<div class="fte-ai-summary"><b>\u{1F3AF} How to Set Up a Task</b><br><br>';
      setupHtml += 'Setting up the right task is half the battle. Here\'s the formula for success:<br><br>';
      setupHtml += '<b>Step 1: Click "Add Task"</b> on the dashboard<br>';
      setupHtml += '<b>Step 2: Pick a type</b> \u2014 Gym, Reading, Meditation, Coding, or Custom<br>';
      setupHtml += '<b>Step 3: Set frequency</b> \u2014 e.g., "4x per week"<br>';
      setupHtml += '<b>Step 4: Define success criteria</b> \u2014 Be specific!<br>';
      setupHtml += '&nbsp;&nbsp;\u2022 Bad: "Work out" \u2014 too vague<br>';
      setupHtml += '&nbsp;&nbsp;\u2022 Good: "Did I complete at least 30 min at the gym?"<br>';
      setupHtml += '<b>Step 5: Add a punishment</b> \u2014 "No takeout this week" or "Donate $20 to charity"<br>';
      setupHtml += '&nbsp;&nbsp;Research shows loss aversion makes you <b>2x more likely</b> to follow through!<br>';
      setupHtml += '<b>Step 6: Write your benefits</b> \u2014 Why does this matter to you?<br><br>';
      setupHtml += '<b>Pro tips from behavioral science:</b><br>';
      setupHtml += '\u2022 Start with <b>just 1 task</b> \u2014 nail it before adding more<br>';
      setupHtml += '\u2022 Use an <b>Implementation Intention</b>: "I will [TASK] at [TIME] in [PLACE]"<br>';
      setupHtml += '\u2022 Make it <b>identity-based</b>: "I am someone who works out" > "I want to go to the gym"<br>';
      setupHtml += '</div>';
      addMessage('ai', setupHtml, false);
      speakText('To set up a task, click Add Task on the dashboard. Pick a type, set your frequency, define what counts as success, and add a punishment for missed goals.');
      setStatus('Ready', '#64748b');
      return;
    }

    // ── Streak query ──
    if (/streak/i.test(lower)) {
      var shtml = '<div class="fte-ai-summary"><b>\u{1F525} Your Streaks</b><br><br>';
      var hasStreaks = false;
      for (var si = 0; si < tasks.length; si++) {
        var st = tasks[si];
        var stName = st.custom_name || st.task_type || 'Task';
        shtml += '\u2022 <b>' + escapeHtml(stName) + '</b>: ';
        shtml += 'Current: <b>' + (st.current_streak || 0) + ' days</b> | Best: <b>' + (st.longest_streak || 0) + ' days</b>';
        if (st.streak_tier && st.streak_tier !== 'none') shtml += ' | Tier: <b>' + st.streak_tier + '</b>';
        shtml += '<br>';
        if (st.current_streak > 0) hasStreaks = true;
      }
      if (!hasStreaks) {
        shtml += '<br>No active streaks yet. Start checking in daily to build one!<br>';
        shtml += '<span style="color:#64748b;font-size:0.8rem;">Remember: the pain of breaking a streak is 2x stronger than the joy of building one. That\'s loss aversion working for you.</span>';
      }
      shtml += '</div>';
      addMessage('ai', shtml, false);
      setStatus('Ready', '#64748b');
      return;
    }

    // ── Due today / what's due ──
    if (/due|today|what.*need|what.*do/i.test(lower)) {
      var dhtml = '<div class="fte-ai-summary"><b>\u{1F4CB} Your Tasks Today</b><br><br>';
      var hasDue = false;
      for (var di2 = 0; di2 < tasks.length; di2++) {
        var dt2 = tasks[di2];
        if (dt2.is_paused) continue;
        var rem2 = Math.max(0, dt2.target_per_period - dt2.completions_this_period);
        var dName = dt2.custom_name || dt2.task_type || 'Task';
        var endD = dt2.extended_deadline && dt2.extended_deadline > dt2.period_end ? dt2.extended_deadline : dt2.period_end;
        var dL = daysBetween(todayStr, endD);
        if (new Date(endD) < now) dL = -1;

        var emoji = rem2 <= 0 ? '\u2705' : (dL <= 1 ? '\u{1F534}' : (dL <= 3 ? '\u{1F7E1}' : '\u{1F7E2}'));
        dhtml += emoji + ' <b>' + escapeHtml(dName) + '</b> \u2014 ';
        if (rem2 <= 0) {
          dhtml += '<span style="color:#22c55e;">Completed for this period!</span>';
        } else {
          dhtml += rem2 + ' check-in' + (rem2 !== 1 ? 's' : '') + ' remaining';
          if (dL < 0) {
            dhtml += ' <span style="color:#ef4444;">(overdue)</span>';
          } else if (dL === 0) {
            dhtml += ' <span style="color:#ef4444;">(due today!)</span>';
          } else {
            dhtml += ' <span style="color:#94a3b8;">(' + dL + ' day' + (dL !== 1 ? 's' : '') + ' left)</span>';
          }
        }
        dhtml += '<br>';
        hasDue = true;
      }
      if (!hasDue) {
        dhtml += 'No active tasks. <a href="/fc/#/accountability" target="_blank" style="color:#818cf8;">Add a task to get started!</a>';
      }
      dhtml += '</div>';
      addMessage('ai', dhtml, false);
      setStatus('Ready', '#64748b');
      return;
    }

    // ── Default: full task summary (enhanced) ──
    var html = '<div class="fte-ai-summary">';
    html += '<b>\u{1F3AF} Your Accountability Dashboard</b><br><br>';
    html += '<b>' + tasks.length + ' task' + (tasks.length !== 1 ? 's' : '') + '</b>';
    if (stats.on_track) html += ' | \u2705 ' + stats.on_track + ' on track';
    if (stats.behind) html += ' | \u26A0\uFE0F ' + stats.behind + ' behind';
    html += '<br><br>';

    for (var ti = 0; ti < Math.min(8, tasks.length); ti++) {
      var task = tasks[ti];
      var taskName = task.custom_name || task.task_type || 'Untitled';
      var taskRem = Math.max(0, task.target_per_period - task.completions_this_period);
      var taskDone = task.completions_this_period >= task.target_per_period;
      var taskEmoji = taskDone ? '\u2705' : (taskRem > 0 ? '\u2B1C' : '\u2705');
      html += taskEmoji + ' <b>' + escapeHtml(taskName) + '</b>';
      html += ' \u2014 ' + task.completions_this_period + '/' + task.target_per_period;
      if (task.current_streak > 0) html += ' \u{1F525}' + task.current_streak + 'd';
      if (task.period_end) html += ' <span style="color:#64748b;">(ends ' + task.period_end + ')</span>';
      html += '<br>';
    }
    if (tasks.length > 8) html += '<br>...and ' + (tasks.length - 8) + ' more.';

    // Check-in summary
    if ((stats.total_checkins || 0) === 0) {
      html += '<br><b>\u{1F6A8} You haven\'t completed a single check-in!</b> Tap \u2705 Check In on any task to start building your streak.';
    }

    html += '<br><br><a href="/fc/#/accountability" target="_blank" style="color:#818cf8;">Open Full Dashboard \u2192</a>';
    html += '</div>';
    addMessage('ai', html, false);
    speakText('You have ' + tasks.length + ' accountability tasks. ' + (stats.behind > 0 ? 'You\'re behind on ' + stats.behind + '. ' : '') + 'Check the dashboard for details.');
    setStatus('Ready', '#64748b');
  }

  // ═══════════════════════════════════════════════════════════
  // HANDLERS: MOVIES
  // ═══════════════════════════════════════════════════════════

  // Helper: find a movie card on the current page by title search
  function findMovieOnPage(searchTerm) {
    var searchLower = searchTerm.toLowerCase();
    var cards = document.querySelectorAll('[data-index]');
    if (!cards.length) return null;

    var bestMatch = null;
    var bestScore = 0;

    for (var i = 0; i < cards.length; i++) {
      var card = cards[i];
      // Get title from h2 or alt text
      var h2 = card.querySelector('h2');
      var title = h2 ? (h2.textContent || h2.innerText || '').trim() : '';
      if (!title) {
        var img = card.querySelector('img[alt]');
        if (img) title = img.getAttribute('alt') || '';
      }
      var titleLower = title.toLowerCase();

      // Exact match
      if (titleLower === searchLower) return { card: card, title: title, index: i, score: 100 };

      // Contains match
      if (titleLower.indexOf(searchLower) !== -1) {
        var score = 80 + (searchLower.length / titleLower.length) * 20;
        if (score > bestScore) { bestScore = score; bestMatch = { card: card, title: title, index: i, score: score }; }
      }

      // Partial word match (e.g. "spider" matches "Spider-Man: Across the Spider-Verse")
      var searchWords = searchLower.split(/[\s\-:]+/);
      var matchedWords = 0;
      for (var w = 0; w < searchWords.length; w++) {
        if (searchWords[w].length > 2 && titleLower.indexOf(searchWords[w]) !== -1) matchedWords++;
      }
      if (searchWords.length > 0 && matchedWords > 0) {
        var wordScore = (matchedWords / searchWords.length) * 70;
        if (wordScore > bestScore) { bestScore = wordScore; bestMatch = { card: card, title: title, index: i, score: wordScore }; }
      }
    }
    return bestMatch && bestMatch.score >= 30 ? bestMatch : null;
  }

  // Helper: scroll to a movie card on V1/V2 pages (snap-scroll)
  function scrollToMovieCard(card) {
    // Find the snap-scroll container
    var container = card.closest('.overflow-y-scroll') || card.parentElement;
    if (container && container.scrollTo) {
      card.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
      card.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  // Helper: trigger search on V3 page
  function triggerV3Search(term) {
    var searchInput = document.getElementById('browseSearchInput');
    if (searchInput) {
      searchInput.value = term;
      searchInput.dispatchEvent(new Event('input', { bubbles: true }));
      // Also try calling the filter function directly
      if (typeof window.applyBrowseFilters === 'function') {
        window.applyBrowseFilters();
      }
      return true;
    }
    return false;
  }

  // Helper: get all movie titles from the current page
  function getAllMovieTitles() {
    var titles = [];
    var cards = document.querySelectorAll('[data-index]');
    for (var i = 0; i < cards.length; i++) {
      var h2 = cards[i].querySelector('h2');
      var title = h2 ? (h2.textContent || h2.innerText || '').trim() : '';
      if (!title) {
        var img = cards[i].querySelector('img[alt]');
        if (img) title = img.getAttribute('alt') || '';
      }
      if (title) titles.push({ title: title, index: i });
    }
    return titles;
  }

  // ═══════════════════════════════════════════════════════════
  // WORLD EVENTS — "What's happening in the world?"
  // ═══════════════════════════════════════════════════════════

  /** Detect if user query is asking about world/global events */
  function _isWorldEventsQuery(lower) {
    // "world events", "global events", "world news", "what's happening in the world"
    if (/world\s*(event|news|happening)/i.test(lower)) return true;
    if (/global\s*(event|news|happening)/i.test(lower)) return true;
    if (/what'?s?\s+(happening|going on)\s+(in|around)\s+the\s+world/i.test(lower)) return true;
    if (/major\s*(event|news|headline)/i.test(lower)) return true;
    if (/big\s*(event|news|headline)/i.test(lower)) return true;
    if (/today'?s?\s*(headline|news|big\s*event)/i.test(lower)) return true;
    if (/headline/i.test(lower) && !/toronto/i.test(lower)) return true;
    if (/top\s*(news|stories|headline)/i.test(lower)) return true;
    if (/breaking\s*news/i.test(lower)) return true;
    if (/^world$/i.test(lower.trim())) return true;
    if (/^news$/i.test(lower.trim())) return true;
    if (/super\s*bowl/i.test(lower)) return true;
    if (/oscar|grammy|emmy|golden\s*globe/i.test(lower)) return true;
    if (/world\s*cup/i.test(lower) && !/toronto/i.test(lower)) return true;
    if (/olympic/i.test(lower)) return true;
    if (/what.*big.*today/i.test(lower)) return true;
    if (/anything.*big.*happening/i.test(lower)) return true;
    if (/what.*everyone.*talking/i.test(lower)) return true;
    return false;
  }

  /** Handle world events query */
  async function handleWorldEvents(lower) {
    // Determine range from query
    var range = 'today';
    if (/this\s*week/i.test(lower) || /week/i.test(lower)) range = 'week';
    if (/upcoming|next\s*few\s*days/i.test(lower)) range = '3days';

    // Show loading
    addMessage('ai', '<div id="fte-world-events-loading" class="fte-ai-summary" style="padding:12px;">' +
      '<div style="display:flex;align-items:center;gap:8px;">' +
      '<div class="fte-loading-dots" style="display:flex;gap:4px;">' +
      '<span style="width:8px;height:8px;border-radius:50%;background:#60a5fa;animation:fte-dot-pulse 1.2s ease-in-out infinite;"></span>' +
      '<span style="width:8px;height:8px;border-radius:50%;background:#60a5fa;animation:fte-dot-pulse 1.2s ease-in-out 0.2s infinite;"></span>' +
      '<span style="width:8px;height:8px;border-radius:50%;background:#60a5fa;animation:fte-dot-pulse 1.2s ease-in-out 0.4s infinite;"></span>' +
      '</div>' +
      '<span>Checking world events...</span>' +
      '</div></div>');
    setStatus('Fetching world events...', '#60a5fa');

    try {
      var apiUrl = 'https://findtorontoevents.ca/fc/api/world_events.php?range=' + encodeURIComponent(range) + '&limit=20';
      var resp = await fetch(apiUrl);
      var data = await resp.json();

      if (!data || !data.ok || !data.events || data.events.length === 0) {
        _replaceWorldEventsLoading('<div class="fte-ai-summary"><b>No world events found for today.</b><br>Try asking "world events this week" for a broader view.</div>');
        setStatus('Ready', '#64748b');
        state.processing = false;
        showStopBtn(false);
        return;
      }

      _renderWorldEvents(data, range);
    } catch (err) {
      _replaceWorldEventsLoading('<div class="fte-ai-summary"><b>Could not load world events.</b><br>Please try again later.</div>');
      setStatus('Ready', '#64748b');
      state.processing = false;
      showStopBtn(false);
    }
  }

  /** Replace the loading indicator for world events */
  function _replaceWorldEventsLoading(html) {
    var el = document.getElementById('fte-world-events-loading');
    if (el) {
      el.outerHTML = html;
    } else {
      addMessage('ai', html);
    }
  }

  /** Render world events results */
  function _renderWorldEvents(data, range) {
    var html = '<div class="fte-ai-summary">';

    // Header
    var rangeLabel = range === 'week' ? 'This Week' : (range === '3days' ? 'Next Few Days' : 'Today');
    html += '<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">';
    html += '<span style="font-size:1.4rem;">\uD83C\uDF0D</span>';
    html += '<b style="font-size:1.1rem;">World Events \u2014 ' + rangeLabel + '</b>';
    html += '<span style="font-size:0.78rem;color:#94a3b8;margin-left:auto;">' + escapeHtml(data.date) + '</span>';
    html += '</div>';

    // Category icons
    var catIcons = {
      sports: '\uD83C\uDFC6',
      entertainment: '\uD83C\uDFAC',
      holiday: '\uD83C\uDF89',
      culture: '\uD83C\uDF0E',
      tech: '\uD83D\uDCBB',
      world_news: '\uD83D\uDCF0',
      world: '\uD83C\uDF10',
      armed_conflicts: '\u26A0\uFE0F',
      disasters: '\uD83C\uDF0A',
      international_relations: '\uD83E\uDD1D',
      politics_elections: '\uD83D\uDDF3\uFE0F',
      law_crime: '\u2696\uFE0F',
      science_technology: '\uD83D\uDD2C',
      health: '\uD83C\uDFE5',
      business_economy: '\uD83D\uDCC8',
      streaming: '\uD83D\uDCF1',
      esports: '\uD83C\uDFAE',
      gaming: '\uD83D\uDD79\uFE0F',
      tv_movies: '\uD83C\uDFA5'
    };

    // Importance colors
    var impColors = {
      high: '#ef4444',
      medium: '#f59e0b',
      normal: '#94a3b8'
    };

    // Group by importance
    var highEvents = [];
    var medEvents = [];
    var normalEvents = [];
    for (var i = 0; i < data.events.length; i++) {
      var evt = data.events[i];
      if (evt.importance === 'high') highEvents.push(evt);
      else if (evt.importance === 'medium') medEvents.push(evt);
      else normalEvents.push(evt);
    }

    // Render high-importance events (featured cards)
    if (highEvents.length > 0) {
      for (var h = 0; h < highEvents.length; h++) {
        var he = highEvents[h];
        var icon = catIcons[he.category] || '\uD83C\uDF10';
        html += '<div style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.2);border-radius:8px;padding:10px 12px;margin-bottom:8px;">';
        html += '<div style="display:flex;align-items:center;gap:6px;">';
        html += '<span style="font-size:1.2rem;">' + icon + '</span>';
        html += '<b>' + escapeHtml(he.title) + '</b>';
        html += '<span style="background:#ef4444;color:#fff;font-size:0.65rem;padding:1px 5px;border-radius:3px;margin-left:auto;">' + escapeHtml(he.category).toUpperCase() + '</span>';
        html += '</div>';
        if (he.description && he.description !== he.title) {
          var desc = he.description.length > 180 ? he.description.substring(0, 180) + '...' : he.description;
          html += '<div style="font-size:0.85rem;color:#cbd5e1;margin-top:4px;">' + escapeHtml(desc) + '</div>';
        }
        if (he.url) {
          html += '<a href="' + escapeHtml(he.url) + '" target="_blank" style="font-size:0.78rem;color:#60a5fa;text-decoration:none;margin-top:4px;display:inline-block;">Learn more \u2192</a>';
        }
        if (he.date && he.date !== data.date) {
          html += '<span style="font-size:0.72rem;color:#64748b;margin-left:8px;">' + escapeHtml(he.date) + '</span>';
        }
        html += '</div>';
      }
    }

    // Render medium-importance events
    if (medEvents.length > 0) {
      html += '<div style="margin-top:6px;margin-bottom:4px;font-size:0.82rem;color:#f59e0b;font-weight:600;">Top Headlines</div>';
      for (var m = 0; m < Math.min(medEvents.length, 5); m++) {
        var me = medEvents[m];
        var mIcon = catIcons[me.category] || '\uD83D\uDCF0';
        html += '<div style="padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.05);font-size:0.88rem;">';
        html += '<span>' + mIcon + '</span> ';
        if (me.url) {
          html += '<a href="' + escapeHtml(me.url) + '" target="_blank" style="color:#e2e8f0;text-decoration:none;">' + escapeHtml(me.title) + '</a>';
        } else {
          html += escapeHtml(me.title);
        }
        html += ' <span style="font-size:0.7rem;color:#64748b;">(' + escapeHtml(me.source === 'bbc_news' ? 'BBC' : me.source) + ')</span>';
        html += '</div>';
      }
    }

    // Render normal events (compact list) — initially show first few, hide rest behind "Show more"
    if (normalEvents.length > 0) {
      var initialShow = Math.min(normalEvents.length, 5);
      var hasMore = normalEvents.length > initialShow;
      html += '<div style="margin-top:8px;margin-bottom:4px;font-size:0.82rem;color:#94a3b8;font-weight:600;">Also Today</div>';
      for (var n = 0; n < initialShow; n++) {
        var ne = normalEvents[n];
        var nIcon = catIcons[ne.category] || '\uD83C\uDF10';
        var nTitle = ne.title.length > 90 ? ne.title.substring(0, 90) + '...' : ne.title;
        html += '<div style="padding:2px 0;font-size:0.82rem;color:#94a3b8;">';
        html += '<span>' + nIcon + '</span> ';
        if (ne.url) {
          html += '<a href="' + escapeHtml(ne.url) + '" target="_blank" style="color:#94a3b8;text-decoration:none;">' + escapeHtml(nTitle) + '</a>';
        } else {
          html += escapeHtml(nTitle);
        }
        html += '</div>';
      }
      // Hidden extra events + "Show more" button
      if (hasMore) {
        var moreCount = normalEvents.length - initialShow;
        html += '<div id="fte-world-events-more" style="display:none;">';
        for (var nm = initialShow; nm < normalEvents.length; nm++) {
          var nme = normalEvents[nm];
          var nmIcon = catIcons[nme.category] || '\uD83C\uDF10';
          var nmTitle = nme.title.length > 90 ? nme.title.substring(0, 90) + '...' : nme.title;
          html += '<div style="padding:2px 0;font-size:0.82rem;color:#94a3b8;">';
          html += '<span>' + nmIcon + '</span> ';
          if (nme.url) {
            html += '<a href="' + escapeHtml(nme.url) + '" target="_blank" style="color:#94a3b8;text-decoration:none;">' + escapeHtml(nmTitle) + '</a>';
          } else {
            html += escapeHtml(nmTitle);
          }
          html += '</div>';
        }
        html += '</div>';
        html += '<a href="#" id="fte-world-events-show-more" onclick="var el=document.getElementById(\'fte-world-events-more\');if(el){el.style.display=\'block\';this.style.display=\'none\';var cont=document.getElementById(\'fte-ai-messages\');if(cont)cont.scrollTop=cont.scrollHeight;}return false;" ' +
          'style="display:inline-flex;align-items:center;gap:4px;margin-top:6px;padding:5px 12px;font-size:0.8rem;color:#60a5fa;background:rgba(96,165,250,0.1);border:1px solid rgba(96,165,250,0.25);border-radius:6px;text-decoration:none;cursor:pointer;transition:background 0.2s;"' +
          ' onmouseover="this.style.background=\'rgba(96,165,250,0.2)\'" onmouseout="this.style.background=\'rgba(96,165,250,0.1)\'">' +
          '\u25BC Show ' + moreCount + ' more event' + (moreCount > 1 ? 's' : '') + '</a>';
      }
    }

    // Action buttons: Summarize + Stop
    html += '<div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap;">';
    html += '<a href="#" id="fte-world-summarize-btn" onclick="window.FTEAssistant && window.FTEAssistant._summarizeWorldEvents();return false;" ' +
      'style="display:inline-flex;align-items:center;gap:5px;padding:7px 14px;font-size:0.82rem;color:#fff;background:linear-gradient(135deg,#6366f1,#818cf8);border:none;border-radius:8px;text-decoration:none;cursor:pointer;font-weight:600;transition:opacity 0.2s;box-shadow:0 2px 8px rgba(99,102,241,0.3);"' +
      ' onmouseover="this.style.opacity=\'0.85\'" onmouseout="this.style.opacity=\'1\'">' +
      '\uD83E\uDDE0 Summarize for me</a>';
    html += '<a href="#" id="fte-world-stop-btn" style="display:none;align-items:center;gap:5px;padding:7px 14px;font-size:0.82rem;color:#f87171;background:rgba(248,113,113,0.1);border:1px solid rgba(248,113,113,0.3);border-radius:8px;text-decoration:none;cursor:pointer;font-weight:600;transition:background 0.2s;"' +
      ' onclick="window.FTEAssistant && window.FTEAssistant._stopWorldSummary();return false;"' +
      ' onmouseover="this.style.background=\'rgba(248,113,113,0.2)\'" onmouseout="this.style.background=\'rgba(248,113,113,0.1)\'">' +
      '\u25A0 Stop</a>';
    html += '</div>';

    // Footer
    html += '<div style="margin-top:10px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.1);font-size:0.78rem;color:#64748b;">';
    html += 'Sources: Wikipedia Current Events, BBC World News, Dexerto, Curated Calendar';
    if (range === 'today') {
      html += '<br>Try: "world events this week" for upcoming events';
    }
    html += '</div>';

    html += '</div>';

    // Store events data for summarization
    state._worldEventsCache = data.events;

    _replaceWorldEventsLoading(html);

    // Speak a brief intro (not the full summary)
    var spoken = '';
    if (highEvents.length > 0) {
      spoken = 'Today\'s top event: ' + highEvents[0].title + '. ';
    }
    spoken += 'I found ' + data.events.length + ' events. Tap Summarize for a full rundown.';
    speakText(spoken);
    showStopBtn(true);
    setStatus('Ready', '#64748b');
    state.processing = false;
  }

  /** Summarize world events — AI explains what's happening */
  var _worldSummaryStopped = false;

  function _summarizeWorldEvents() {
    var events = state._worldEventsCache;
    if (!events || events.length === 0) {
      addMessage('ai', 'No world events loaded to summarize. Try asking "world events" first.');
      return;
    }
    _worldSummaryStopped = false;

    // Show stop button, hide summarize button
    var sumBtn = document.getElementById('fte-world-summarize-btn');
    var stopBtn = document.getElementById('fte-world-stop-btn');
    if (sumBtn) sumBtn.style.display = 'none';
    if (stopBtn) stopBtn.style.display = 'inline-flex';
    showStopBtn(true);

    // Build a natural-language summary from the events data
    var highEvts = [];
    var medEvts = [];
    var otherEvts = [];
    for (var i = 0; i < events.length; i++) {
      if (events[i].importance === 'high') highEvts.push(events[i]);
      else if (events[i].importance === 'medium') medEvts.push(events[i]);
      else otherEvts.push(events[i]);
    }

    var summaryParts = [];
    summaryParts.push("Here\u2019s what\u2019s happening in the world right now:");
    summaryParts.push('');

    if (highEvts.length > 0) {
      summaryParts.push('\uD83D\uDD34 <b>Top Stories</b>');
      for (var h = 0; h < highEvts.length; h++) {
        var he = highEvts[h];
        var hDesc = he.description && he.description !== he.title ? ' \u2014 ' + he.description : '';
        if (hDesc.length > 200) hDesc = hDesc.substring(0, 200) + '...';
        summaryParts.push('\u2022 <b>' + escapeHtml(he.title) + '</b>' + escapeHtml(hDesc));
      }
      summaryParts.push('');
    }

    if (medEvts.length > 0) {
      summaryParts.push('\uD83D\uDFE0 <b>Major Headlines</b>');
      for (var m = 0; m < medEvts.length; m++) {
        var me = medEvts[m];
        var mDesc = me.description && me.description !== me.title ? ' \u2014 ' + me.description : '';
        if (mDesc.length > 150) mDesc = mDesc.substring(0, 150) + '...';
        summaryParts.push('\u2022 ' + escapeHtml(me.title) + escapeHtml(mDesc));
      }
      summaryParts.push('');
    }

    if (otherEvts.length > 0) {
      summaryParts.push('\uD83D\uDD35 <b>Other Notable Events</b>');
      var showOther = Math.min(otherEvts.length, 6);
      for (var o = 0; o < showOther; o++) {
        summaryParts.push('\u2022 ' + escapeHtml(otherEvts[o].title));
      }
      if (otherEvts.length > showOther) {
        summaryParts.push('...and ' + (otherEvts.length - showOther) + ' more.');
      }
      summaryParts.push('');
    }

    summaryParts.push('<span style="color:#94a3b8;font-size:0.82rem;">That\u2019s the world at a glance. Ask me about any specific event for more details.</span>');

    var fullHTML = summaryParts.join('<br>');
    var fullText = summaryParts.join('\n').replace(/<[^>]+>/g, '');

    // Typewriter effect — reveal the summary word by word
    var msgEl = addMessage('ai', '<div id="fte-world-summary-text" class="fte-ai-summary" style="padding:12px;line-height:1.6;"></div>', false);
    var targetEl = document.getElementById('fte-world-summary-text');
    if (!targetEl) return;

    // Split into tokens for typewriter
    var tokens = fullHTML.split(/(?=<)|(?<=>)|\s+/);
    var displayed = '';
    var tokenIdx = 0;
    var insideTag = false;

    // Start TTS simultaneously
    state.speaking = true;
    updateBtnState();
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      var utter = new SpeechSynthesisUtterance(fullText);
      utter.rate = 1.0;
      utter.pitch = 1;
      utter.lang = 'en-US';
      utter.onend = function () {
        state.speaking = false;
        updateBtnState();
        _worldSummaryFinished();
      };
      utter.onerror = function () {
        state.speaking = false;
        updateBtnState();
        _worldSummaryFinished();
      };
      window.speechSynthesis.speak(utter);
    }

    // Typewriter interval
    var typeInterval = setInterval(function () {
      if (_worldSummaryStopped) {
        clearInterval(typeInterval);
        return;
      }
      if (tokenIdx >= tokens.length) {
        clearInterval(typeInterval);
        targetEl.innerHTML = fullHTML;
        if (!('speechSynthesis' in window)) _worldSummaryFinished();
        return;
      }
      // Add a few tokens per tick for speed
      var chunk = '';
      for (var t = 0; t < 3 && tokenIdx < tokens.length; t++, tokenIdx++) {
        chunk += tokens[tokenIdx] + ' ';
      }
      displayed += chunk;
      targetEl.innerHTML = displayed;
      var cont = document.getElementById('fte-ai-messages');
      if (cont) cont.scrollTop = cont.scrollHeight;
    }, 50);
  }

  function _worldSummaryFinished() {
    var sumBtn = document.getElementById('fte-world-summarize-btn');
    var stopBtn = document.getElementById('fte-world-stop-btn');
    if (stopBtn) stopBtn.style.display = 'none';
    if (sumBtn) {
      sumBtn.style.display = 'inline-flex';
      sumBtn.textContent = '\u2705 Summary complete';
      sumBtn.style.background = 'rgba(34,197,94,0.15)';
      sumBtn.style.color = '#4ade80';
      sumBtn.style.cursor = 'default';
      sumBtn.onclick = function () { return false; };
    }
    showStopBtn(false);
  }

  function _stopWorldSummary() {
    _worldSummaryStopped = true;
    stopSpeaking();
    var stopBtn = document.getElementById('fte-world-stop-btn');
    if (stopBtn) stopBtn.style.display = 'none';
    var sumBtn = document.getElementById('fte-world-summarize-btn');
    if (sumBtn) {
      sumBtn.style.display = 'inline-flex';
      sumBtn.textContent = '\uD83E\uDDE0 Summarize for me';
      sumBtn.style.background = 'linear-gradient(135deg,#6366f1,#818cf8)';
      sumBtn.style.color = '#fff';
      sumBtn.style.cursor = 'pointer';
      sumBtn.onclick = function () { window.FTEAssistant._summarizeWorldEvents(); return false; };
    }
    showStopBtn(false);
    // Show the stopped text as-is
    var textEl = document.getElementById('fte-world-summary-text');
    if (textEl) {
      textEl.innerHTML += '<br><span style="color:#f87171;font-size:0.8rem;">(Summary stopped)</span>';
    }
  }

  // ═══════════════════════════════════════════════════════════
  // MOVIES NOW PLAYING / SHOWTIMES DETECTION
  // ═══════════════════════════════════════════════════════════

  /** Detect if user query is asking about movies currently playing in theaters / showtimes */
  function _isMovieShowtimesQuery(lower) {
    // "what movies are playing near me", "which movies are showing"
    if (/(?:what|which)\s+movies?\s+(?:are\s+)?(?:playing|showing|screening|on|in\s+theaters?)/i.test(lower)) return true;
    // "movies playing near me", "movies showing nearby"
    if (/movies?\s+(?:playing|showing|screening)\s+(?:near|around|close|in\s+theaters?)/i.test(lower)) return true;
    // "movies near me" (bare — shows movies + theaters, more useful than just theater POIs)
    if (/^movies?\s+near\s+(?:me|here|by)$/i.test(lower)) return true;
    // "now playing" / "now showing" / "in theaters now"
    if (/(?:now\s+playing|now\s+showing|in\s+theaters?\s+(?:now|today|this\s+week))/i.test(lower)) return true;
    // "showtimes near me" / "movie showtimes" (with optional time qualifiers)
    if (/showtime/i.test(lower)) return true;
    // "what's on at the movies/cinema", "whats playing at the cinema"
    if (/what(?:'?s|\s+is)\s+(?:on|playing)\s+at\s+(?:the\s+)?(?:movie|cinema)/i.test(lower)) return true;
    // "movies starting soon / starting now / starting in X minutes / starting at Xpm / starting between"
    if (/movies?\s+starting/i.test(lower)) return true;
    // "what can i watch in theaters"
    if (/what\s+(?:can\s+i|to)\s+watch\s+(?:in|at)\s+(?:the\s+)?(?:theater|theatre|cinema)/i.test(lower)) return true;
    // "movie times" / "film times"
    if (/(?:movie|film)\s+times?\s/i.test(lower)) return true;
    return false;
  }

  /**
   * Parse time filter from a movie showtime query.
   * Returns object: { type, label, googleQuery }
   *   type: 'now' | 'soon' | 'in_minutes' | 'at_time' | 'between' | 'today' | 'tonight' | null
   *   label: human-readable string e.g. "starting in 20 minutes", "between 4pm and 6pm"
   *   googleQuery: fragment for Google Maps URL e.g. "showtimes+4pm"
   */
  function _parseMovieTimeFilter(lower) {
    var result = { type: null, label: '', googleQuery: 'showtimes' };

    // "starting now" / "right now"
    if (/starting\s+(?:right\s+)?now/i.test(lower) || /right\s+now/i.test(lower)) {
      result.type = 'now';
      result.label = 'starting now';
      result.googleQuery = 'showtimes+now';
      return result;
    }

    // "starting soon"
    if (/starting\s+soon/i.test(lower)) {
      result.type = 'soon';
      result.label = 'starting soon';
      result.googleQuery = 'showtimes+today';
      return result;
    }

    // "starting in X minutes/hours"
    var inMinMatch = lower.match(/starting\s+in\s+(\d+)\s*(min(?:ute)?s?|hrs?|hours?)/i);
    if (inMinMatch) {
      var amount = parseInt(inMinMatch[1], 10);
      var unit = inMinMatch[2].toLowerCase();
      var isHours = /^h/.test(unit);
      var minutes = isHours ? amount * 60 : amount;
      var now = new Date();
      var target = new Date(now.getTime() + minutes * 60000);
      var h = target.getHours();
      var ampm = h >= 12 ? 'pm' : 'am';
      var h12 = h % 12;
      if (h12 === 0) h12 = 12;
      var minStr = target.getMinutes() > 0 ? ':' + (target.getMinutes() < 10 ? '0' : '') + target.getMinutes() : '';
      result.type = 'in_minutes';
      result.label = 'starting around ' + h12 + minStr + ampm + ' (in ' + (isHours ? amount + (amount === 1 ? ' hour' : ' hours') : amount + ' min') + ')';
      result.googleQuery = 'showtimes+' + h12 + ampm;
      result.targetTime = target;
      return result;
    }

    // "starting between Xpm and Ypm" / "between X and Y"
    var betweenMatch = lower.match(/between\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s+and\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?/i);
    if (betweenMatch) {
      var h1 = parseInt(betweenMatch[1], 10);
      var m1 = betweenMatch[2] ? parseInt(betweenMatch[2], 10) : 0;
      var ap1 = (betweenMatch[3] || betweenMatch[6] || 'pm').toLowerCase();
      var h2 = parseInt(betweenMatch[4], 10);
      var m2 = betweenMatch[5] ? parseInt(betweenMatch[5], 10) : 0;
      var ap2 = (betweenMatch[6] || ap1).toLowerCase();
      result.type = 'between';
      result.label = 'between ' + h1 + (m1 ? ':' + (m1 < 10 ? '0' : '') + m1 : '') + ap1 + ' and ' + h2 + (m2 ? ':' + (m2 < 10 ? '0' : '') + m2 : '') + ap2;
      result.googleQuery = 'showtimes+' + h1 + ap1;
      return result;
    }

    // "starting at Xpm" / "at X:XX pm" / "around Xpm"
    var atTimeMatch = lower.match(/(?:starting\s+)?(?:at|around)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)/i);
    if (atTimeMatch) {
      var ht = parseInt(atTimeMatch[1], 10);
      var mt = atTimeMatch[2] ? parseInt(atTimeMatch[2], 10) : 0;
      var apt = atTimeMatch[3].toLowerCase();
      result.type = 'at_time';
      result.label = 'around ' + ht + (mt ? ':' + (mt < 10 ? '0' : '') + mt : '') + apt;
      result.googleQuery = 'showtimes+' + ht + apt;
      var atDate = new Date();
      var atH24 = ht;
      if (apt === 'pm' && ht < 12) atH24 = ht + 12;
      if (apt === 'am' && ht === 12) atH24 = 0;
      atDate.setHours(atH24, mt, 0, 0);
      result.targetTime = atDate;
      return result;
    }

    // "tonight" / "this evening"
    if (/tonight|this\s+evening/i.test(lower)) {
      result.type = 'tonight';
      result.label = 'tonight';
      result.googleQuery = 'showtimes+tonight';
      return result;
    }

    // "today"
    if (/today/i.test(lower)) {
      result.type = 'today';
      result.label = 'today';
      result.googleQuery = 'showtimes+today';
      return result;
    }

    // "tomorrow"
    if (/tomorrow/i.test(lower)) {
      result.type = 'tomorrow';
      result.label = 'tomorrow';
      result.googleQuery = 'showtimes+tomorrow';
      return result;
    }

    return result;
  }

  // ── DEFAULT THEATER HELPERS ──

  function _getDefaultTheater() {
    try { return localStorage.getItem(CONFIG.defaultTheaterKey) || ''; } catch(e) { return ''; }
  }

  function _setDefaultTheater(name) {
    try { localStorage.setItem(CONFIG.defaultTheaterKey, name); } catch(e) {}
  }

  function _getTheaterShowtimeUrl(theaterName, timeFilter) {
    timeFilter = timeFilter || { googleQuery: 'showtimes' };
    return 'https://www.google.com/search?q=' + encodeURIComponent(theaterName + ' ' + timeFilter.googleQuery);
  }

  // Global function for "set as default" onclick in rendered HTML
  window.__fteSetDefaultTheater = function(name) {
    _setDefaultTheater(name);
    var links = document.querySelectorAll('.fte-theater-default-link');
    for (var i = 0; i < links.length; i++) {
      var linkName = links[i].getAttribute('data-theater');
      if (linkName === name) {
        links[i].innerHTML = '\u2605 Default theater';
        links[i].style.color = '#fbbf24';
        links[i].style.cursor = 'default';
        links[i].onclick = null;
      } else {
        links[i].innerHTML = '\u2606 Set as default';
        links[i].style.color = '#64748b';
        links[i].style.cursor = 'pointer';
      }
    }
    // Update primary theater banner if present
    var banner = document.getElementById('fte-primary-theater-banner');
    if (banner) {
      var bannerName = banner.querySelector('.fte-primary-theater-name');
      if (bannerName) bannerName.textContent = name;
      var bannerLabel = banner.querySelector('.fte-primary-theater-label');
      if (bannerLabel) bannerLabel.textContent = '\u2605 Your Theater';
      banner.style.background = 'rgba(251,191,36,0.08)';
      banner.style.borderColor = 'rgba(251,191,36,0.2)';
    }
  };

  // ═══════════════════════════════════════════════════════════
  // BUSINESS VERIFICATION (is X still open?)
  // ═══════════════════════════════════════════════════════════

  /** Detect if user query is asking about a specific business being open/closed */
  function _isBusinessVerifyQuery(lower) {
    // "is [business] still open" / "is [business] closed"
    if (/\bis\s+.{2,40}\s+(still\s+)?(open|closed|shut\s*down|operating|running)\b/i.test(lower)) return true;
    // "check if [business] is open/closed"
    if (/\bcheck\s+(if|whether)\s+.{2,40}\s+(is|has)\s+(open|closed|shut|still)/i.test(lower)) return true;
    // "did [business] close" / "has [business] closed"
    if (/\b(did|has)\s+.{2,40}\s+(close[d]?|shut\s*down|gone)\b/i.test(lower)) return true;
    // "verify [business]" / "verify if [business]"
    if (/\bverify\s+(if\s+)?.{2,40}\s+(is\s+)?(open|closed|still)/i.test(lower)) return true;
    // "[business] still open?" / "[business] closed?"
    if (/\b.{3,40}\s+still\s+open\s*\??$/i.test(lower)) return true;
    return false;
  }

  /** Parse a business verify query to extract name and optional address */
  function _parseBusinessVerifyQuery(lower) {
    var name = '';
    var address = '';

    // Pattern: "is [business] (on/at [address]) still open/closed"
    var m = lower.match(/\bis\s+(.+?)\s+(?:on|at)\s+(.+?)\s+(?:still\s+)?(?:open|closed|shut|operating|running)/i);
    if (m) {
      name = m[1];
      address = m[2];
    }

    // Pattern: "is [business] still open/closed" (no address)
    if (!name) {
      m = lower.match(/\bis\s+(.+?)\s+(?:still\s+)?(?:open|closed|shut\s*down|operating|running)/i);
      if (m) name = m[1];
    }

    // Pattern: "check if [business] (on/at [address]) is open/closed"
    if (!name) {
      m = lower.match(/\bcheck\s+(?:if|whether)\s+(.+?)\s+(?:on|at)\s+(.+?)\s+(?:is|has)\s+(?:still\s+)?(?:open|closed)/i);
      if (m) { name = m[1]; address = m[2]; }
    }
    if (!name) {
      m = lower.match(/\bcheck\s+(?:if|whether)\s+(.+?)\s+(?:is|has)\s+(?:still\s+)?(?:open|closed)/i);
      if (m) name = m[1];
    }

    // Pattern: "did [business] close" / "has [business] closed"
    if (!name) {
      m = lower.match(/\b(?:did|has)\s+(.+?)\s+(?:close[d]?|shut\s*down|gone)/i);
      if (m) name = m[1];
    }

    // Pattern: "[business] still open?"
    if (!name) {
      m = lower.match(/^(.+?)\s+still\s+open\s*\??$/i);
      if (m) name = m[1];
    }

    // Extract address from name if it contains "on/at [street]"
    if (name && !address) {
      m = name.match(/^(.+?)\s+(?:on|at)\s+(.+)$/i);
      if (m) { name = m[1]; address = m[2]; }
    }

    // Clean up: remove leading "the"
    name = name.replace(/^the\s+/i, '').trim();

    return { name: name, address: address };
  }

  /** Handle a business verification query */
  async function handleBusinessVerify(lower) {
    var parsed = _parseBusinessVerifyQuery(lower);

    if (!parsed.name) {
      addMessage('ai', '<div class="fte-ai-summary"><b>Business Verification</b><br><br>' +
        'I can check if a business is still open or has closed. Try asking like:<br>' +
        '\u2022 "Is 241 Pizza on Queen Street still open?"<br>' +
        '\u2022 "Check if Blockbuster Video is closed"<br>' +
        '\u2022 "Did the cafe on Dundas close?"</div>');
      setStatus('Ready', '#64748b');
      return;
    }

    // Show loading
    addMessage('ai', '<div id="fte-ai-verify-loading" class="fte-ai-summary">' +
      '<b>\uD83D\uDD0D Checking: ' + escapeHtml(parsed.name) + '</b>' +
      (parsed.address ? '<br><span style="color:#94a3b8;">Near: ' + escapeHtml(parsed.address) + '</span>' : '') +
      '<br><span style="color:#a78bfa;">Cross-referencing Foursquare + OpenStreetMap...</span></div>');

    // Build API URL
    var params = 'name=' + encodeURIComponent(parsed.name);
    if (parsed.address) params += '&address=' + encodeURIComponent(parsed.address);
    var url = CONFIG.verifyBusinessApi + '?' + params;

    try {
      var resp = await fetch(url);
      var data = await resp.json();

      if (!data.ok) {
        _replaceVerifyLoading('<div class="fte-ai-summary"><b>Verification Error</b><br><br>' +
          escapeHtml(data.error || 'Unknown error') + '</div>');
        setStatus('Ready', '#64748b');
        return;
      }

      _renderBusinessVerifyResult(data, parsed);
    } catch (err) {
      _replaceVerifyLoading('<div class="fte-ai-summary"><b>Connection Error</b><br><br>' +
        'Could not reach the verification service. Please try again later.<br>' +
        '<span style="color:#94a3b8;">' + escapeHtml(err.message || 'Network error') + '</span></div>');
      setStatus('Ready', '#64748b');
    }
  }

  function _replaceVerifyLoading(html) {
    var el = document.getElementById('fte-ai-verify-loading');
    if (el) {
      el.outerHTML = html;
    } else {
      addMessage('ai', html);
    }
  }

  /** Render the business verification result card */
  function _renderBusinessVerifyResult(data, parsed) {
    // Verdict styling
    var verdictColors = {
      'likely_closed': { bg: 'rgba(239,68,68,0.1)', border: '#ef4444', icon: '\u274C', label: 'Likely Closed' },
      'possibly_closed': { bg: 'rgba(245,158,11,0.1)', border: '#f59e0b', icon: '\u26A0\uFE0F', label: 'Possibly Closed' },
      'temporarily_closed': { bg: 'rgba(245,158,11,0.1)', border: '#f59e0b', icon: '\u23F8\uFE0F', label: 'Temporarily Closed' },
      'likely_open': { bg: 'rgba(34,197,94,0.1)', border: '#22c55e', icon: '\u2705', label: 'Likely Open' },
      'possibly_open': { bg: 'rgba(34,197,94,0.08)', border: '#86efac', icon: '\uD83D\uDFE2', label: 'Possibly Open' },
      'unverified': { bg: 'rgba(148,163,184,0.1)', border: '#a78bfa', icon: '\uD83D\uDD0D', label: 'Unverified' },
      'unknown': { bg: 'rgba(148,163,184,0.1)', border: '#94a3b8', icon: '\u2753', label: 'Unknown' }
    };

    var v = verdictColors[data.verdict] || verdictColors['unknown'];

    var html = '<div class="fte-ai-summary" style="border-left:3px solid ' + v.border + ';">';

    // Header
    html += '<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">';
    html += '<span style="font-size:1.5em;">' + v.icon + '</span>';
    html += '<div><b style="font-size:1.1em;">' + escapeHtml(data.business_name) + '</b>';
    html += '<br><span style="color:' + v.border + ';font-weight:600;font-size:0.95em;">' + v.label + '</span>';
    html += ' <span style="color:#64748b;font-size:0.8em;">(' + escapeHtml(data.confidence) + ' confidence)</span>';
    html += '</div></div>';

    // Summary
    if (data.summary) {
      html += '<p style="color:#cbd5e1;margin:0 0 12px;line-height:1.5;">' + escapeHtml(data.summary) + '</p>';
    }

    // Sources
    if (data.sources && data.sources.length > 0) {
      html += '<div style="border-top:1px solid rgba(148,163,184,0.2);padding-top:10px;margin-top:8px;">';
      html += '<b style="font-size:0.85em;color:#94a3b8;">Sources:</b>';

      for (var i = 0; i < data.sources.length; i++) {
        var src = data.sources[i];
        var srcIcon = '\uD83C\uDF10';
        var srcLabel = src.provider || 'Unknown';
        if (src.provider === 'foursquare') { srcIcon = '\uD83D\uDCCD'; srcLabel = 'Foursquare'; }
        else if (src.provider === 'osm') { srcIcon = '\uD83C\uDF10'; srcLabel = 'OpenStreetMap'; }
        else if (src.provider === 'google_places') { srcIcon = '\uD83D\uDDFA\uFE0F'; srcLabel = 'Google Places'; }

        html += '<div style="margin-top:6px;padding:6px 8px;background:rgba(30,30,60,0.4);border-radius:6px;font-size:0.9em;">';
        html += '<span>' + srcIcon + ' <b>' + srcLabel + '</b></span>';

        if (src.status === 'closed' || src.status === 'disused') {
          html += ' \u2014 <span style="color:#f87171;">Closed</span>';
        } else if (src.status === 'temporarily_closed') {
          html += ' \u2014 <span style="color:#fbbf24;">Temporarily Closed</span>';
        } else if (src.status === 'open' || src.status === 'active') {
          html += ' \u2014 <span style="color:#86efac;">Open</span>';
        } else if (src.status === 'found') {
          html += ' \u2014 <span style="color:#a78bfa;">Listed</span>';
        } else if (src.status === 'unsure') {
          html += ' \u2014 <span style="color:#fbbf24;">Unsure</span>';
        } else if (src.status === 'not_found') {
          html += ' \u2014 <span style="color:#94a3b8;">Not found</span>';
        } else if (src.status === 'error' || src.status === 'unavailable') {
          html += ' \u2014 <span style="color:#94a3b8;">' + escapeHtml(src.note || 'Unavailable') + '</span>';
        }

        if (src.name) {
          html += '<br><span style="color:#94a3b8;">Match: ' + escapeHtml(src.name) + '</span>';
        }
        if (src.address) {
          html += '<br><span style="color:#94a3b8;">' + escapeHtml(src.address) + '</span>';
        }
        if (src.category) {
          html += '<br><span style="color:#94a3b8;font-size:0.85em;">Category: ' + escapeHtml(src.category) + '</span>';
        }
        if (src.business_status) {
          html += '<br><span style="color:#94a3b8;font-size:0.85em;">Google status: ' + escapeHtml(src.business_status) + '</span>';
        }

        html += '</div>';
      }
      html += '</div>';
    }

    // Google Maps link
    var mapsQuery = data.business_name;
    if (data.query_address) mapsQuery += ' ' + data.query_address;
    if (data.query_city) mapsQuery += ' ' + data.query_city;
    html += '<div style="margin-top:10px;">';
    html += '<a href="https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(mapsQuery) + '" target="_blank" rel="noopener" ' +
      'style="color:#a78bfa;text-decoration:none;font-size:0.9em;">\uD83D\uDDFA\uFE0F View on Google Maps</a>';
    html += '</div>';

    html += '</div>';

    _replaceVerifyLoading(html);
    speakText(data.business_name + ' is ' + (data.verdict || 'unknown status') + '. ' + (data.summary || ''));
    setStatus('Ready', '#64748b');
  }


  // ═══════════════════════════════════════════════════════════
  // NEAR ME / LOCATION FINDER
  // ═══════════════════════════════════════════════════════════

  /** Detect if user query is a "near me" / location-finder request */
  function _isNearMeQuery(lower) {
    // Exclude movie-showtime queries (they have their own handler)
    if (_isMovieShowtimesQuery(lower)) return false;
    // Exclude event-like queries so they route to handleEvents() instead
    if (/what.*happening/i.test(lower)) return false;
    if (/what.*going\s+on/i.test(lower)) return false;
    if (/things\s+to\s+do/i.test(lower)) return false;
    if (/something\s+to\s+do/i.test(lower)) return false;
    if (/fun\s+(stuff|things)/i.test(lower)) return false;
    if (/anything\s+fun/i.test(lower)) return false;
    if (/something\s+fun/i.test(lower)) return false;
    if (/\b(events?|concerts?|festivals?|shows?|comedy|part(y|ies)|nightlife|dancing|dating)\s*(near|around|close|tonight|today|tomorrow|this|next)/i.test(lower)) return false;
    if (/\b(happening|activities|happenings)\s*(near|around|tonight|today|this)/i.test(lower)) return false;
    // Explicit "near me" / "nearby" / "around here"
    if (/near\s?(me|by|here)/i.test(lower)) return true;
    if (/around\s?(here|me)/i.test(lower)) return true;
    // "where is the nearest X", "where can I find X"
    if (/where\s+(is|are|can i find)\s+(the\s+)?(nearest|closest)/i.test(lower)) return true;
    if (/where\s+(can i|to|do i)\s+(find|get|buy)/i.test(lower)) return true;
    // "find X near", "X close to me"
    if (/find\s+.+\s+near/i.test(lower)) return true;
    if (/close\s+to\s+(me|here)/i.test(lower)) return true;
    // Dietary + food/restaurant/near
    if (/(?:halal|kosher|vegan|vegetarian|gluten.?free|dairy.?free|keto)\s+.*(food|restaurant|near|place|option|pizza|burger|shop)/i.test(lower)) return true;
    // Food/restaurant explicit queries
    if (/(?:restaurants?|coffee\s*shops?|cafes?|pizza\s*(places?|shops?)?|burger\s*(joints?|places?)?|sushi|ramen|pho|shawarma|falafel|tacos?|hot\s*dogs?|delis?|baker(y|ies)|donuts?|ice\s*cream|bubble\s*tea|boba)\s*(near|open|close|around)/i.test(lower)) return true;
    if (/where\s+(can i|to|should i)\s+eat/i.test(lower)) return true;
    if (/food\s+near/i.test(lower) || /places\s+to\s+eat/i.test(lower)) return true;
    // Time-based: "open now/late/24/7/at midnight/till 3am" with a place term
    if (/open\s+(late|now|24|all\s+night|at\s+\d|till\s+\d|until\s+\d)/i.test(lower) &&
        /(?:restaurant|coffee|cafe|pizza|food|shop|store|bar|pub|pharmacy|gas|station|grocery|mall)/i.test(lower)) return true;
    if (/late\s*night\s*(food|eat|restaurant|place|munch|snack)/i.test(lower)) return true;
    if (/24\s*hour\s*(food|restaurant|place|store|pharmacy|coffee|gas|shop)/i.test(lower)) return true;
    // Cravings / hunger
    if (/(?:hungry|starving|craving|want\s+to\s+eat)/i.test(lower)) return true;
    // Non-food: services, facilities, healthcare, etc.
    if (/(?:washroom|restroom|bathroom|toilet|atm|parking|gas\s*station|pharmacy|drug\s*store|bank|post\s*office|laundromat|laundry|car\s*wash|hair\s*salon|barber|dry\s*clean|mechanic|locksmith|nail\s*salon|spa|massage)/i.test(lower)) return true;
    // Accommodation
    if (/(?:hotel|hostel|motel|airbnb|lodging|bed\s+and\s+breakfast)\s*(near|around|close|in\s+|$)/i.test(lower)) return true;
    // Entertainment
    if (/(?:movie\s*theat|cinema|bowling|arcade|escape\s*room|pool\s*hall|billiard|comedy\s*club|karaoke|skating\s*rink|gym|fitness|yoga|swimming\s*pool|mini\s*golf)\s*(near|around|close|$)/i.test(lower)) return true;
    // Shopping
    if (/(?:grocery|supermarket|convenience\s*store|corner\s*store|bookstore|thrift|electronics|computer\s*parts|hardware\s*store|dollar\s*store|liquor\s*store|lcbo|beer\s*store|cannabis|dispensary|pet\s*store|walmart|costco|canadian\s*tire|dollarama)\s*(near|around|$)/i.test(lower)) return true;
    // Healthcare
    if (/(?:hospital|walk.?in\s*clinic|clinic|doctor|dentist|vet|veterinar|urgent\s*care|optometrist|physiother|chiropract|eye\s*doctor)\s*(near|around|close|$)/i.test(lower)) return true;
    // Transit
    if (/(?:car\s*rental|taxi|bike\s*share|ev\s*charg|subway\s*station|train\s*station|bus\s*stop|go\s*station|ttc)\s*(near|around|close|$)/i.test(lower)) return true;
    // Community / Crisis
    if (/(?:library|libraries|church|mosque|temple|synagogue|gurdwara|police\s*station|fire\s*station|community\s*cent|food\s*bank|shelter|homeless|warming\s*cent|drop.?in)/i.test(lower)) return true;
    // Delivery queries
    if (/(?:uber\s*eats|doordash|skip\s*the\s*dishes|instacart)\s+.*(near|deliver)/i.test(lower)) return true;
    if (/delivery.*(food|pizza|burger|grocery|pharmacy|restaurant)/i.test(lower)) return true;
    // Generic "find/search [thing] near [place]"
    if (/(?:find|search|locate|look\s+for|where\s+is)\s+.+\s+near\s+/i.test(lower)) return true;
    // Product search near a landmark
    if (/(?:hand\s*warmer|charger|umbrella|phone\s*case|battery|snack|water|drink)\s*(near|at|in|around)/i.test(lower)) return true;
    // "best X near" / "recommend X near" / "suggest X near"
    if (/(?:best|recommend|suggest)\s+.+\s+near/i.test(lower)) return true;
    if (/(?:best|top\s*rated|highest\s*rated)\s+(?:restaurant|coffee|cafe|pizza|food|bar|pub|sushi|ramen|burger)/i.test(lower)) return true;
    // "cheap eats" / "affordable"
    if (/cheap\s+eat/i.test(lower) || /affordable\s*(food|restaurant)/i.test(lower)) return true;
    if (/fine\s+dining/i.test(lower)) return true;
    if (/patio\s*(restaurant|bar|food)/i.test(lower)) return true;
    // "where is [specific place name]" — catches "where is Almadina Bistro", "where is Eaton Centre"
    // Excludes: "where am i", "where is my X", "where is the event", "where is this"
    if (/^where\s+(?:is|are)\s+(?!my\s|the\s+event|this\s|that\s|i\b).{3,}/i.test(lower)) return true;

    // ── CUISINE-SPECIFIC (without requiring "near me") ──
    if (/\b(?:italian|chinese|japanese|indian|korean|thai|mexican|vietnamese|ethiopian|caribbean|greek|filipino|persian|turkish|lebanese|moroccan|french|spanish|german|brazilian|peruvian|colombian|cuban|jamaican|portuguese|polish|ukrainian|russian|afghan|pakistani|bangladeshi|sri\s*lankan|nepalese|tibetan|burmese|malaysian|indonesian|singaporean)\s*(?:food|restaurant|cuisine|place|kitchen|eatery|joint|spot|dining)/i.test(lower)) return true;

    // ── SPECIFIC FOOD ITEMS (people often just type the food) ──
    if (/\b(?:shawarma|falafel|pho|ramen|sushi|dim\s*sum|dumplings|noodles|pad\s*thai|bibimbap|jerk\s*chicken|empanadas|pupusas|tamales|banh\s*mi|gyoza|tempura|udon|soba|laksa|satay|butter\s*chicken|biryani|samosa|naan|tandoori|tikka\s*masala|kebab|hummus|baba\s*ghanoush|gyros|souvlaki|poutine|pierogi|schnitzel|currywurst|paella|tapas|ceviche|churrasco|acai|poke\s*bowl)\s*(?:near|around|place|shop|restaurant|open|$)/i.test(lower)) return true;

    // ── MEAL TIME queries ──
    if (/\b(?:brunch|breakfast|lunch|dinner|supper)\s*(?:spot|place|restaurant|near|around|idea|suggestion|option|$)/i.test(lower)) return true;
    if (/(?:place|somewhere|restaurant)\s+(?:for|to\s+(?:have|get|grab))\s+(?:brunch|breakfast|lunch|dinner)/i.test(lower)) return true;

    // ── VIBE / OCCASION queries ──
    if (/\b(?:date\s*night|romantic)\s*(?:restaurant|dinner|spot|place|idea)/i.test(lower)) return true;
    if (/\b(?:family\s*friendly|kid\s*friendly)\s*(?:restaurant|place|spot)/i.test(lower)) return true;
    if (/\b(?:group\s*dinner|birthday\s*dinner|work\s*lunch|business\s*lunch|team\s*dinner)/i.test(lower)) return true;
    if (/\b(?:quiet|cozy|chill|trendy|hipster|instagrammable|aesthetic)\s*(?:cafe|restaurant|spot|place|bar)/i.test(lower)) return true;
    if (/\b(?:dog\s*friendly|pet\s*friendly)\s*(?:patio|restaurant|cafe|bar|place)/i.test(lower)) return true;
    if (/\b(?:rooftop|waterfront|lakeside)\s*(?:bar|restaurant|patio|dining)/i.test(lower)) return true;
    if (/\b(?:sports\s*bar|dive\s*bar|cocktail\s*bar|lounge|speakeasy|hookah|shisha)/i.test(lower)) return true;

    // ── SERVICE QUERIES people ask naturally ──
    if (/where\s+can\s+i\s+(?:print|photocopy|fax|scan|notarize)/i.test(lower)) return true;
    if (/where\s+can\s+i\s+(?:get|buy|find)\s+(?:a\s+)?(?:passport\s*photo|key\s*cut|key\s*cop|shoe\s*repair|phone\s*repair|screen\s*repair|phone\s*case|charger|umbrella|hand\s*warmer|battery)/i.test(lower)) return true;
    if (/where\s+can\s+i\s+(?:study|work\s+from|sit\s+and\s+work|charge\s+my\s+phone|use\s+wifi|get\s+wifi)/i.test(lower)) return true;
    if (/where\s+can\s+i\s+(?:park|do\s+laundry|get\s+a\s+haircut|get\s+my\s+(?:car|bike|phone|shoes?)\s+(?:fixed|repaired))/i.test(lower)) return true;

    // ── "I need / I want / I'm looking for" patterns ──
    if (/\b(?:i\s+need|i\s+want|i(?:'m|\s+am)\s+looking\s+for|i(?:'m|\s+am)\s+searching\s+for|looking\s+for)\s+(?:a\s+|an\s+|some\s+|the\s+)?(?:restaurant|cafe|coffee|food|pizza|bar|pub|store|shop|pharmacy|clinic|dentist|doctor|gym|salon|barber|bank|atm|gas|station|hotel|hostel|laundry|mechanic|vet|washroom|restroom|bathroom|library)/i.test(lower)) return true;

    // ── "[anything] near [street address / postal code]" — catches "pizza places near 21 mccaul street" ──
    if (/\b.+\s+near\s+\d+\s+[a-z]/i.test(lower)) return true;
    if (/\b.+\s+near\s+[a-z]\d[a-z]\s*\d[a-z]\d/i.test(lower)) return true;

    // ── "Show me" + place type ──
    if (/show\s+me\s+(?:all\s+)?(?:the\s+)?(?:restaurants?|cafes?|coffee|food|pizza|bars?|stores?|shops?|pharmacy|clinic|gym|hotel|bank|gas\s+station|washroom|library|park)/i.test(lower)) return true;

    // ── "Is there a [place] near/around here" ──
    if (/is\s+there\s+(?:a|an)\s+.+\s+(?:near|around|close|nearby)/i.test(lower)) return true;

    // ── "What's around here / what's nearby" ──
    if (/what(?:'s|\s+is)\s+(?:around\s+here|nearby|close\s+by|in\s+this\s+area)/i.test(lower)) return true;
    if (/anything\s+(?:good|interesting|open|fun)\s+(?:near|around|close|nearby)/i.test(lower)) return true;

    // ── "Open right now" / "What's open" queries ──
    if (/what(?:'s|\s+is)\s+open\s+(?:right\s+)?now/i.test(lower)) return true;
    if (/anything\s+open\s+(?:right\s+)?now/i.test(lower)) return true;
    if (/what(?:'s|\s+is)\s+open\s+(?:late|at\s+\d|after\s+\d|past\s+\d)/i.test(lower)) return true;

    // ── "What time does [place] close/open" ──
    if (/what\s+time\s+(?:does|do|is)\s+.+\s+(?:close|open|shut)/i.test(lower)) return true;
    if (/is\s+.+\s+(?:open|closed)\s+(?:right\s+)?(?:now|today|tonight)/i.test(lower)) return true;

    // ── SPECIFIC CHAIN lookups ──
    if (/\b(?:starbucks|tim\s*hortons?|mcdonalds?|mcdonald's|subway|wendys?|wendy's|burger\s*king|popeyes?|kfc|pizza\s*pizza|pizza\s*hut|dominos?|domino's|shoppers?\s*drug\s*mart|no\s*frills|loblaws?|metro|freshco|food\s*basics|dollarama|winners|homesense|value\s*village|goodwill)\s*(?:near|around|open|close|$)/i.test(lower)) return true;

    // ── "Good [place type]" / "nice [place type]" without "near" ──
    if (/(?:good|nice|great|decent|solid|reliable)\s+(?:restaurant|cafe|coffee|pizza|barber|mechanic|dentist|doctor|gym|salon|hotel|sushi|ramen|thai|indian|chinese|italian)/i.test(lower)) return true;

    // ── Plural lookups ──
    if (/\b(?:restaurants|cafes|coffee\s*shops|bars|pubs|clubs|stores|shops|malls|hotels|hostels|clinics|hospitals|pharmacies|libraries|gyms|salons|barbershops|parks|beaches|pools|rinks|arenas|theaters|theatres|cinemas|museums|galleries)\s*(?:near|around|in\s+|$)/i.test(lower)) return true;

    // ── Drive-through / takeout ──
    if (/\b(?:drive\s*(?:thru|through)|takeout|take\s*out|take\s*away|pick\s*up)\s*(?:food|restaurant|coffee|burger|pizza|near|$)/i.test(lower)) return true;

    // ── "Feed me" / conversational hunger ──
    if (/\b(?:feed\s+me|i(?:'m|\s+am)\s+starving|i(?:'m|\s+am)\s+so\s+hungry|need\s+food|need\s+to\s+eat|grab\s+(?:a\s+)?(?:bite|food|coffee|drink|snack))\b/i.test(lower)) return true;

    // ── "Recommend" / "suggest" without "near" ──
    if (/(?:recommend|suggest)\s+(?:a\s+|an\s+|some\s+)?(?:restaurant|cafe|coffee|food|pizza|bar|place\s+to\s+eat|brunch|dinner|lunch|breakfast)/i.test(lower)) return true;

    return false;
  }

  /**
   * Parse a near-me query into structured data.
   * Returns { searchTerm, dietary, location, openNow, openAt, open247, radius, sort, wantDelivery }
   */
  function _parseNearMeQuery(text) {
    var lower = text.toLowerCase();
    var result = {
      searchTerm: '',
      dietary: '',
      location: '',
      openNow: false,
      openAt: '',
      open247: false,
      radius: null,
      sort: '',
      wantDelivery: false,
      provider: ''
    };

    // Extract search provider: "using google", "using foursquare", "with google", etc.
    var providerMatch = lower.match(/\b(?:using|with|via|on|through)\s+(google|foursquare|osm|openstreetmap)\b/i);
    if (providerMatch) {
      var prov = providerMatch[1].toLowerCase();
      if (prov === 'osm' || prov === 'openstreetmap') prov = 'google';
      result.provider = prov;
      lower = lower.replace(providerMatch[0], '').trim();
    }

    // Extract dietary
    var dietaryList = ['halal', 'kosher', 'vegan', 'vegetarian', 'gluten-free', 'gluten free', 'dairy-free', 'dairy free', 'keto', 'organic', 'paleo', 'nut-free', 'nut free'];
    for (var i = 0; i < dietaryList.length; i++) {
      if (lower.indexOf(dietaryList[i]) !== -1) {
        result.dietary = dietaryList[i].replace(/[- ]/g, function(m) { return m === ' ' ? '-' : m; });
        lower = lower.replace(new RegExp(dietaryList[i].replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi'), '').trim();
        break;
      }
    }

    // Extract delivery intent
    if (/uber\s*eats|doordash|skip\s*the\s*dishes|instacart|delivery/i.test(lower)) {
      result.wantDelivery = true;
      lower = lower.replace(/(?:on\s+)?(?:uber\s*eats|doordash|skip\s*the\s*dishes|instacart)/gi, '').replace(/\bdelivery\b/gi, '').trim();
    }

    // Extract time filters
    if (/open\s+24\s*\/?\s*7|24\s*hours?|all\s*night/i.test(lower)) {
      result.open247 = true;
      result.openNow = true;
      lower = lower.replace(/open\s+24\s*\/?\s*7|24\s*hours?|all\s*night/gi, '').trim();
    } else if (/open\s+now|currently\s+open/i.test(lower)) {
      result.openNow = true;
      lower = lower.replace(/open\s+now|currently\s+open/gi, '').trim();
    } else if (/open\s+(?:at\s+)?midnight/i.test(lower)) {
      result.openAt = '00:00';
      result.openNow = true;
      lower = lower.replace(/open\s+(?:at\s+)?midnight/gi, '').trim();
    } else if (/open\s+late/i.test(lower)) {
      result.openAt = '23:00';
      result.openNow = true;
      lower = lower.replace(/open\s+late/gi, '').trim();
    } else {
      var timeMatch = lower.match(/open\s+(?:(?:till|until|at)\s+)?(\d{1,2})\s*(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)/i);
      if (timeMatch) {
        var hr = parseInt(timeMatch[1], 10);
        var min = timeMatch[2] ? parseInt(timeMatch[2], 10) : 0;
        var ampm = timeMatch[3].replace(/\./g, '').toLowerCase();
        if (ampm === 'pm' && hr < 12) hr += 12;
        if (ampm === 'am' && hr === 12) hr = 0;
        result.openAt = (hr < 10 ? '0' : '') + hr + ':' + (min < 10 ? '0' : '') + min;
        result.openNow = true;
        lower = lower.replace(timeMatch[0], '').trim();
      }
    }

    // Extract radius
    var radiusMatch = lower.match(/(?:within|in|radius)\s+(\d+)\s*(km|kilometer|mi|mile|m|meter|block)/i);
    if (radiusMatch) {
      var val = parseInt(radiusMatch[1], 10);
      var unit = radiusMatch[2].toLowerCase();
      if (unit === 'km' || unit === 'kilometer') result.radius = val * 1000;
      else if (unit === 'mi' || unit === 'mile') result.radius = Math.round(val * 1609);
      else if (unit === 'm' || unit === 'meter') result.radius = val;
      else if (unit === 'block') result.radius = val * 100;
      lower = lower.replace(radiusMatch[0], '').trim();
    }

    // Extract sort
    if (/(?:top|highest|best)\s*rated/i.test(lower) || lower.indexOf('best') !== -1) {
      result.sort = 'RATING';
      lower = lower.replace(/(?:top|highest|best)\s*rated/gi, '').trim();
    } else if (/most\s+popular/i.test(lower)) {
      result.sort = 'POPULARITY';
      lower = lower.replace(/most\s+popular/gi, '').trim();
    }

    // Extract location — handle multi-part: "in [city] near [landmark]"
    var cityPlaceMatch = lower.match(/\bin\s+([a-z][a-z\s]{1,30}?)\s+near\s+(.+?)(?:\s+(?:open|that|which|with|within|\d).*)?$/i);
    if (cityPlaceMatch) {
      var cityPart = cityPlaceMatch[1].trim();
      var placePart = cityPlaceMatch[2].trim();
      // Don't treat "me/here" as a place
      if (!/^(me|here|my\s+location)$/i.test(placePart) && placePart.length > 1) {
        result.location = placePart + ', ' + cityPart;
        lower = lower.replace(cityPlaceMatch[0], '').trim();
      }
    }

    // Also check "near [place] in [city]" pattern
    if (!result.location) {
      var placeCityMatch = lower.match(/\bnear\s+(.+?)\s+in\s+([a-z][a-z\s]{1,30}?)(?:\s+(?:open|that|which|with|within|\d).*)?$/i);
      if (placeCityMatch) {
        var plc = placeCityMatch[1].trim();
        var cty = placeCityMatch[2].trim();
        if (!/^(me|here|my\s+location)$/i.test(plc) && plc.length > 1) {
          result.location = plc + ', ' + cty;
          lower = lower.replace(placeCityMatch[0], '').trim();
        }
      }
    }

    // Standard single location: "near [location]", "at [location]", "in [location]", "around [location]"
    if (!result.location) {
      var locMatch = lower.match(/(?:near|at|in|around|close\s+to|by)\s+(?:the\s+)?(.+?)(?:\s+(?:open|that|which|with|within|\d).*)?$/i);
      if (locMatch) {
        var locCandidate = locMatch[1].trim();
        // Don't treat "me" / "here" as a location string
        if (!/^(me|here|my\s+location)$/i.test(locCandidate) && locCandidate.length > 1) {
          result.location = locCandidate;
          lower = lower.replace(locMatch[0], '').trim();
        } else {
          lower = lower.replace(/near\s+(me|here|by|my\s+location)/gi, '').trim();
        }
      }
    }

    // Clean up question-form patterns: "what X are playing/showing" → "X"
    lower = lower.replace(/^what\s+/i, '').replace(/\s+(?:are|is)\s+(?:playing|showing|available|on|screening|running|out)(?:\s+(?:right\s+)?now)?$/i, '').trim();
    // Clean up common filler words
    lower = lower.replace(/\b(find|search|locate|look\s+for|where\s+(?:is|are|can\s+i\s+find)|the\s+nearest|the\s+closest|show\s+me|get\s+me|i\s+(?:need|want)|nearby|close|around\s+here|please|can\s+you)\b/gi, '').trim();
    lower = lower.replace(/\s{2,}/g, ' ').trim();

    result.searchTerm = lower || text.toLowerCase().replace(/near\s+me|nearby/gi, '').trim();
    // Fallback: if searchTerm is empty after all parsing, use the original
    if (!result.searchTerm) result.searchTerm = text;

    return result;
  }

  /** Get user geolocation (returns promise) */
  function _getNearMeLocation() {
    return new Promise(function(resolve) {
      // Check cached location first
      if (state.userLocation && state.userLocation.lat && state.userLocation.lng) {
        resolve({ lat: state.userLocation.lat, lng: state.userLocation.lng, source: 'cached' });
        return;
      }

      if (!navigator.geolocation) {
        resolve(null);
        return;
      }

      navigator.geolocation.getCurrentPosition(
        function(pos) {
          var loc = { lat: pos.coords.latitude, lng: pos.coords.longitude, source: 'gps' };
          state.userLocation = loc;
          resolve(loc);
        },
        function() {
          // Geolocation denied or failed
          resolve(null);
        },
        { timeout: 8000, enableHighAccuracy: false, maximumAge: 300000 }
      );
    });
  }

  /** Format distance for display */
  function _formatDistance(meters) {
    if (meters < 1000) return meters + 'm';
    return (meters / 1000).toFixed(1) + 'km';
  }

  /** Format rating for display */
  function _formatRating(rating) {
    if (!rating || rating <= 0) return '';
    var stars = Math.round(rating / 2); // Foursquare 0-10 -> 0-5 stars
    var out = '';
    for (var s = 0; s < 5; s++) {
      out += s < stars ? '\u2605' : '\u2606';
    }
    return out + ' ' + (rating / 10 * 10).toFixed(1) + '/10';
  }

  /** Main handler for near-me / places queries */
  async function handlePlaces(lower) {
    var parsed = _parseNearMeQuery(lower);

    // Resolve provider: query override > default from localStorage > 'google'
    var provider = parsed.provider || '';
    if (!provider) {
      try { provider = localStorage.getItem('fte_default_search_provider') || ''; } catch(e) {}
    }
    if (provider !== 'foursquare') provider = 'google';
    var providerLabel = provider === 'google' ? 'Google/OSM' : 'Foursquare';

    addMessage('ai', '<div id="fte-ai-nearme-loading" class="fte-ai-summary"><b>Searching for ' + escapeHtml(parsed.searchTerm) + '...</b><br>' +
      (parsed.dietary ? '<span style="color:#a78bfa;">Filter: ' + escapeHtml(parsed.dietary) + '</span><br>' : '') +
      (parsed.openNow ? '<span style="color:#86efac;">Open now</span>' + (parsed.openAt ? ' (until ' + escapeHtml(parsed.openAt) + ')' : '') + '<br>' : '') +
      '<span style="color:#94a3b8;">Searching via ' + providerLabel + '...</span></div>');

    // Get location
    var userLoc = null;
    if (parsed.location) {
      // User specified a location string - backend will geocode it
      userLoc = { lat: 0, lng: 0, source: 'text', locationStr: parsed.location };
    } else {
      userLoc = await _getNearMeLocation();
    }

    // If no location and no location string, ask user
    if (!userLoc && !parsed.location) {
      var el = document.getElementById('fte-ai-nearme-loading');
      if (el) {
        el.innerHTML = '<b>I need your location to search nearby.</b><br><br>' +
          'Please allow location access when prompted, or tell me a location like:<br>' +
          '\u2022 "coffee shops near Yonge and Dundas"<br>' +
          '\u2022 "pizza near Eaton Centre"<br>' +
          '\u2022 "washrooms near M5V 3A8"<br><br>' +
          '<span style="color:#94a3b8;">Tip: Try again with a specific location or enable location services in your browser.</span>';
      }
      speakText('I need your location to search nearby. Please share your location or tell me an intersection or postal code.');
      setStatus('Ready', '#64748b');
      return;
    }

    // Build API URL for nearme.php backend
    var params = 'query=' + encodeURIComponent(parsed.searchTerm);
    if (userLoc && userLoc.lat && userLoc.lng && userLoc.lat !== 0) {
      params += '&lat=' + userLoc.lat + '&lng=' + userLoc.lng;
    }
    if (userLoc && userLoc.locationStr) {
      params += '&location=' + encodeURIComponent(userLoc.locationStr);
    }
    if (parsed.openNow) params += '&open_now=true';
    if (parsed.openAt) params += '&open_at=' + encodeURIComponent(parsed.openAt);
    if (parsed.dietary) params += '&dietary=' + encodeURIComponent(parsed.dietary);
    if (parsed.radius) params += '&radius=' + parsed.radius;
    if (parsed.sort) params += '&sort=' + parsed.sort;
    params += '&limit=10';
    params += '&provider=' + encodeURIComponent(provider);

    var url = CONFIG.nearMeApi + '?' + params;

    // Update loading message
    var loadEl = document.getElementById('fte-ai-nearme-loading');
    if (loadEl) {
      loadEl.querySelector('span:last-child') && (loadEl.innerHTML = loadEl.innerHTML.replace('Getting your location...', 'Searching nearby places...'));
    }

    try {
      var resp = await fetch(url);
      var data = await resp.json();

      if (!data.ok) {
        var errHtml = '<div class="fte-ai-summary"><b>Search Error</b><br><br>';
        if (data.error && data.error.indexOf('API key') !== -1) {
          errHtml += 'The Near Me feature needs a Foursquare API key to be configured.<br>';
          errHtml += '<span style="color:#94a3b8;">The site admin needs to add FOURSQUARE_API_KEY to the server configuration.</span>';
        } else {
          errHtml += escapeHtml(data.error || 'Unknown error');
        }
        errHtml += '</div>';
        _replaceNearMeLoading(errHtml);
        setStatus('Ready', '#64748b');
        return;
      }

      // Handle crisis response
      if (data.is_crisis) {
        _renderCrisisResponse(data, parsed);
        return;
      }

      // Render normal results (nearme.php returns data in the format _renderNearMeResults expects)
      _renderNearMeResults(data, parsed);

    } catch (err) {
      _replaceNearMeLoading('<div class="fte-ai-summary"><b>Connection Error</b><br><br>' +
        'Could not reach the places search service. Please try again later.<br>' +
        '<span style="color:#94a3b8;">' + escapeHtml(err.message || 'Network error') + '</span></div>');
      setStatus('Ready', '#64748b');
    }
  }

  function _replaceNearMeLoading(html) {
    var el = document.getElementById('fte-ai-nearme-loading');
    if (el) {
      el.outerHTML = html;
    } else {
      addMessage('ai', html);
    }
  }

  /** Render crisis resources (shelters, hotlines, etc.) */
  function _renderCrisisResponse(data, parsed) {
    var html = '<div class="fte-ai-summary" style="border-left:3px solid #f87171;">';
    html += '<b style="color:#f87171;">24/7 Resources Available Now</b><br><br>';

    if (data.crisis_resources && data.crisis_resources.length > 0) {
      for (var i = 0; i < data.crisis_resources.length; i++) {
        var r = data.crisis_resources[i];
        html += '<div style="margin-bottom:8px;padding:6px 8px;background:rgba(248,113,113,0.08);border-radius:6px;">';
        html += '<b>' + escapeHtml(r.name) + '</b>';
        if (r.phone) {
          html += ' &mdash; <a href="tel:' + escapeHtml(r.phone.replace(/[^0-9+]/g, '')) + '" style="color:#60a5fa;font-weight:600;">' + escapeHtml(r.phone) + '</a>';
        }
        html += '<br>';
        if (r.hours) html += '<span style="color:#86efac;font-size:0.85rem;">' + escapeHtml(r.hours) + '</span> ';
        if (r.type) html += '<span style="color:#94a3b8;font-size:0.85rem;">&middot; ' + escapeHtml(r.type) + '</span>';
        if (r.address) {
          html += '<br><span style="font-size:0.85rem;">' + escapeHtml(r.address) + '</span>';
          if (r.maps_url) html += ' <a href="' + escapeHtml(r.maps_url) + '" target="_blank" style="color:#60a5fa;font-size:0.8rem;">[Map]</a>';
        }
        html += '</div>';
      }
    }

    // Also show Foursquare results if any
    if (data.results && data.results.length > 0) {
      html += '<br><b>Also found nearby:</b><br>';
      html += _buildResultsList(data.results, 5);
    }

    html += '</div>';
    _replaceNearMeLoading(html);

    speakText('Here are emergency and crisis resources that can help. I\'ve listed phone numbers and addresses for 24/7 services.');
    setStatus('Ready', '#64748b');
  }

  /** Render normal near-me results */
  function _renderNearMeResults(data, parsed) {
    var html = '<div class="fte-ai-summary">';

    if (data.results.length === 0) {
      html += '<b>No results found</b> for "' + escapeHtml(parsed.searchTerm) + '"';
      if (data.location && data.location.resolved_from) {
        html += ' near ' + escapeHtml(data.location.resolved_from);
      }
      html += '.<br><br>';
      html += '<b>Next steps:</b><br>';
      html += '\u2022 Search <a href="https://www.google.com/maps/search/' + encodeURIComponent(parsed.searchTerm) + '" target="_blank" style="color:#60a5fa;">Google Maps</a> for "' + escapeHtml(parsed.searchTerm) + '"<br>';
      html += '\u2022 Try a broader search term or increase the radius<br>';
      if (parsed.dietary) html += '\u2022 Try without the dietary filter first<br>';
      html += '\u2022 Call <b>311</b> for Toronto city services<br>';
      if (parsed.wantDelivery || data.delivery_tip) {
        html += '\u2022 Check Uber Eats, DoorDash, or SkipTheDishes apps<br>';
      }
      html += '</div>';
      _replaceNearMeLoading(html);
      speakText('I couldn\'t find any results for ' + parsed.searchTerm + ' near you. Try a broader search or check Google Maps.');
      setStatus('Ready', '#64748b');
      return;
    }

    // Header
    var provBadge = '';
    if (data.provider === 'google') {
      provBadge = ' <span style="display:inline-block;background:#34a853;color:#fff;font-size:0.7rem;padding:1px 6px;border-radius:3px;vertical-align:middle;">OpenStreetMap</span>';
    } else if (data.provider === 'foursquare') {
      provBadge = ' <span style="display:inline-block;background:#3333ff;color:#fff;font-size:0.7rem;padding:1px 6px;border-radius:3px;vertical-align:middle;">Foursquare</span>';
    }
    html += '<b>Found ' + data.total + ' result' + (data.total !== 1 ? 's' : '') + '</b>';
    html += ' for <b>' + escapeHtml(parsed.searchTerm) + '</b>';
    if (data.location && data.location.resolved_from && data.location.resolved_from !== 'coordinates' && data.location.resolved_from !== 'default (downtown Toronto)') {
      html += ' near <b>' + escapeHtml(data.location.resolved_from) + '</b>';
    }
    if (parsed.dietary) html += ' <span style="color:#a78bfa;">(' + escapeHtml(parsed.dietary) + ')</span>';
    html += provBadge;
    html += '<br><br>';

    // Results list
    html += _buildResultsList(data.results, 10);

    // Delivery tip
    if (data.delivery_tip || parsed.wantDelivery) {
      html += '<div style="margin-top:10px;padding:6px 10px;background:rgba(96,165,250,0.1);border-radius:6px;font-size:0.85rem;">';
      html += '\uD83D\uDE9A <b>Delivery:</b> ';
      html += data.delivery_tip ? escapeHtml(data.delivery_tip) : 'Check Uber Eats, DoorDash, or SkipTheDishes for delivery options.';
      html += '</div>';
    }

    // Dietary note
    if (data.dietary_note) {
      html += '<div style="margin-top:6px;padding:6px 10px;background:rgba(167,139,250,0.1);border-radius:6px;font-size:0.85rem;">';
      html += '\uD83C\uDF3F <b>Dietary:</b> ' + escapeHtml(data.dietary_note);
      html += '</div>';
    }

    // Pro tip
    if (data.pro_tip) {
      html += '<div style="margin-top:6px;padding:6px 10px;background:rgba(250,204,21,0.1);border-radius:6px;font-size:0.85rem;">';
      html += '\uD83D\uDCA1 <b>Pro Tip:</b> ' + escapeHtml(data.pro_tip);
      html += '</div>';
    }

    // Google Maps link (always shown for cross-reference)
    if (data.google_maps_url) {
      html += '<div style="margin-top:8px;padding:6px 10px;background:rgba(52,168,83,0.1);border-radius:6px;font-size:0.85rem;">';
      html += '\uD83D\uDDFA\uFE0F <a href="' + escapeHtml(data.google_maps_url) + '" target="_blank" style="color:#34a853;font-weight:600;text-decoration:none;">See these results on Google Maps</a>';
      html += '</div>';
    }

    // Suggest nearby intersection if user searched by postal code
    if (data.nearby_intersection && data.nearby_intersection.length > 0) {
      html += '<div style="margin-top:6px;padding:6px 10px;background:rgba(99,102,241,0.08);border-radius:6px;font-size:0.82rem;color:#6366f1;">';
      html += '<b>Tip:</b> Searching by intersection is more accurate than postal code. Try: ';
      html += '"<a href="#" onclick="document.getElementById(\'fte-ai-input\').value=\'' +
        escapeHtml(parsed.searchTerm) + ' near ' + escapeHtml(data.nearby_intersection) +
        '\';document.getElementById(\'fte-ai-send\').click();return false;" ' +
        'style="color:#4f46e5;text-decoration:underline;">' +
        escapeHtml(parsed.searchTerm) + ' near ' + escapeHtml(data.nearby_intersection) + '</a>"';
      html += '</div>';
    }

    // Suggest trying the other provider
    var otherProvider = (data.provider === 'google') ? 'foursquare' : 'google';
    var otherLabel = (otherProvider === 'google') ? 'Google/OSM' : 'Foursquare';
    html += '<div style="margin-top:4px;font-size:0.78rem;color:#64748b;">';
    html += 'Try: "' + escapeHtml(parsed.searchTerm) + ' using ' + otherLabel + '" for different results';
    html += '</div>';

    html += '</div>';
    _replaceNearMeLoading(html);

    // Speak summary
    var spoken = 'Found ' + data.total + ' ' + parsed.searchTerm + ' results. ';
    if (data.results.length > 0) {
      spoken += 'The closest is ' + data.results[0].name + ', ' + _formatDistance(data.results[0].distance_m) + ' away.';
      if (data.results[0].open_now === true) spoken += ' It\'s open now.';
      else if (data.results[0].open_now === false) spoken += ' It appears to be closed.';
    }
    speakText(spoken);
    setStatus('Ready', '#64748b');
  }

  /** Build HTML list of place results */
  function _buildResultsList(results, maxShow) {
    var html = '';
    var count = Math.min(results.length, maxShow);
    for (var i = 0; i < count; i++) {
      var r = results[i];
      html += '<div style="margin-bottom:10px;padding:8px 10px;background:rgba(100,116,139,0.08);border-radius:8px;border-left:2px solid ' + (r.open_now === true ? '#86efac' : r.open_now === false ? '#f87171' : '#64748b') + ';">';
      html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;">';
      html += '<b style="font-size:0.95rem;">' + (i + 1) + '. ' + escapeHtml(r.name) + '</b>';
      html += '<span style="color:#a78bfa;font-size:0.8rem;white-space:nowrap;margin-left:8px;">' + _formatDistance(r.distance_m) + '</span>';
      html += '</div>';

      // Category + open status
      html += '<div style="font-size:0.85rem;margin-top:2px;">';
      if (r.category) html += '<span style="color:#94a3b8;">' + escapeHtml(r.category) + '</span> ';
      if (r.open_now === true) {
        html += '<span style="color:#86efac;font-weight:600;">\u2022 Open now</span>';
        if (r.hours_detail) html += ' <span style="color:#94a3b8;">(' + escapeHtml(r.hours_detail) + ')</span>';
      } else if (r.open_now === false) {
        html += '<span style="color:#f87171;">\u2022 Closed</span>';
        if (r.hours_detail) html += ' <span style="color:#94a3b8;">(' + escapeHtml(r.hours_detail) + ')</span>';
      } else {
        if (r.hours) html += '<span style="color:#94a3b8;">' + escapeHtml(r.hours) + '</span>';
      }
      html += '</div>';

      // Address
      if (r.address) {
        html += '<div style="font-size:0.83rem;color:#94a3b8;margin-top:2px;">' + escapeHtml(r.address) + '</div>';
      }

      // Rating + price
      if (r.rating > 0 || r.price) {
        html += '<div style="font-size:0.83rem;margin-top:2px;">';
        if (r.rating > 0) html += '<span style="color:#fbbf24;">' + _formatRating(r.rating) + '</span> ';
        if (r.price) html += '<span style="color:#86efac;">' + escapeHtml(r.price) + '</span>';
        html += '</div>';
      }

      // Dietary notes
      if (r.dietary_notes) {
        html += '<div style="font-size:0.8rem;color:#a78bfa;margin-top:2px;">\uD83C\uDF3F ' + escapeHtml(r.dietary_notes) + '</div>';
      }

      // Action links
      html += '<div style="font-size:0.8rem;margin-top:4px;">';
      if (r.maps_url) {
        html += '<a href="' + escapeHtml(r.maps_url) + '" target="_blank" style="color:#60a5fa;text-decoration:none;margin-right:10px;">\uD83D\uDDFA\uFE0F Directions</a>';
      }
      if (r.phone) {
        html += '<a href="tel:' + escapeHtml(r.phone.replace(/[^0-9+]/g, '')) + '" style="color:#60a5fa;text-decoration:none;margin-right:10px;">\uD83D\uDCDE ' + escapeHtml(r.phone) + '</a>';
      }
      if (r.website) {
        html += '<a href="' + escapeHtml(r.website) + '" target="_blank" style="color:#60a5fa;text-decoration:none;">\uD83C\uDF10 Website</a>';
      }
      html += '</div>';
      html += '</div>';
    }
    return html;
  }


  // ═══════════════════════════════════════════════════════════
  // PLACES SLASH COMMANDS & HELP
  // ═══════════════════════════════════════════════════════════

  /** Detect if query is a /places slash command */
  function _isPlacesSlashCommand(lower) {
    if (/^\/(places|food|eat|find|nearby|open|directions|locate|search\s*place)(\s|$)/i.test(lower)) return true;
    // Inline filter syntax: /type:food, /cuisine:italian, /restrict:halal
    if (/^\/(?:type|cuisine|restrict|diet|near|radius|sort|open):/i.test(lower)) return true;
    return false;
  }

  /** Handle /places slash commands */
  async function handlePlacesSlashCommand(lower, raw) {
    // /places (no args) or /places help
    if (/^\/(places)\s*$/i.test(lower) || /^\/(places)\s+help/i.test(lower)) {
      showPlacesHelp();
      return;
    }

    // /directions [dest] [from origin]
    if (/^\/directions?\s+/i.test(lower)) {
      var dirText = lower.replace(/^\/directions?\s+/i, '').trim();
      await handleDirections(dirText);
      return;
    }

    // /open [type] → search open now
    if (/^\/open\s*/i.test(lower)) {
      var openType = lower.replace(/^\/open\s*/i, '').trim() || 'food';
      await handlePlaces(openType + ' open now near me');
      return;
    }

    // /food [query], /eat [query]
    if (/^\/(food|eat)\s*/i.test(lower)) {
      var foodQ = lower.replace(/^\/(food|eat)\s*/i, '').trim() || 'restaurants';
      await handlePlaces(foodQ + ' near me');
      return;
    }

    // /find [query], /nearby [query], /locate [query], /search place [query]
    if (/^\/(find|nearby|locate|search\s*place)\s*/i.test(lower)) {
      var findQ = lower.replace(/^\/(find|nearby|locate|search\s*place)\s*/i, '').trim() || 'interesting places';
      await handlePlaces(findQ + ' near me');
      return;
    }

    // /places [category] — search that category
    if (/^\/places\s+/i.test(lower)) {
      var catQ = lower.replace(/^\/places\s+/i, '').trim();
      // Check if it's a help subcategory
      var helpCats = ['food', 'drinks', 'coffee', 'shopping', 'health', 'services', 'transit', 'entertainment', 'fitness', 'emergency', 'accommodation', 'examples', 'filters', 'commands'];
      var isHelpCat = false;
      for (var hc = 0; hc < helpCats.length; hc++) {
        if (catQ === helpCats[hc]) { isHelpCat = true; break; }
      }
      if (isHelpCat) {
        showPlacesHelpCategory(catQ);
        return;
      }
      await handlePlaces(catQ + ' near me');
      return;
    }

    // Inline filter syntax: /type:food /restrict:halal pizza near dundas
    var filterResult = _parseInlineFilters(raw);
    if (filterResult.query) {
      await handlePlaces(filterResult.query);
      return;
    }

    // Fallback
    showPlacesHelp();
  }

  /** Parse inline filter syntax like /type:food /restrict:halal /near:dundas /open:now pizza */
  function _parseInlineFilters(text) {
    var remaining = text;
    var type = '';
    var restrict = '';
    var near = '';
    var openFilter = '';
    var sort = '';
    var radius = '';
    var cuisine = '';

    // Extract /key:value pairs
    var filterRegex = /\/(type|cuisine|restrict|diet|near|radius|sort|open):(\S+)/gi;
    var match;
    while ((match = filterRegex.exec(text)) !== null) {
      var key = match[1].toLowerCase();
      var val = match[2].replace(/_/g, ' ');
      if (key === 'type') type = val;
      else if (key === 'cuisine') cuisine = val;
      else if (key === 'restrict' || key === 'diet') restrict = val;
      else if (key === 'near') near = val;
      else if (key === 'sort') sort = val;
      else if (key === 'radius') radius = val;
      else if (key === 'open') openFilter = val;
      remaining = remaining.replace(match[0], '');
    }
    remaining = remaining.replace(/\s{2,}/g, ' ').trim();

    // Build a natural language query from the filters
    var parts = [];
    if (restrict) parts.push(restrict);
    if (cuisine) parts.push(cuisine);
    if (type) parts.push(type);
    if (remaining) parts.push(remaining);
    if (parts.length === 0 && !type) return { query: '' };
    if (parts.length === 0) parts.push(type);

    var query = parts.join(' ');
    if (openFilter === 'now' || openFilter === 'yes' || openFilter === 'true') query += ' open now';
    else if (openFilter === 'late') query += ' open late';
    else if (openFilter === '24h' || openFilter === '24/7') query += ' open 24 hours';
    else if (openFilter) query += ' open at ' + openFilter;
    if (near) query += ' near ' + near;
    else query += ' near me';
    if (sort === 'rating' || sort === 'best') query += ' top rated';
    if (radius) query += ' within ' + radius;

    return { query: query };
  }

  /** Show the comprehensive /places help */
  function showPlacesHelp() {
    var html = '<div class="fte-ai-summary" style="max-height:70vh;overflow-y:auto;">';
    html += '<b style="font-size:1.05rem;">Find Places \u2014 Complete Guide</b><br>';
    html += '<span style="color:#94a3b8;">Ask in plain English or use slash commands. I search real-time via Foursquare.</span><br><br>';

    // Quick commands
    html += '<div style="background:rgba(59,130,246,0.1);padding:8px 10px;border-radius:8px;margin-bottom:10px;">';
    html += '<b>\u26A1 Quick Commands</b><br>';
    html += '<span style="font-size:0.85rem;">';
    html += _helpCmd('/food') + ' \u2014 Food & restaurants near you<br>';
    html += _helpCmd('/food halal pizza') + ' \u2014 Specific food search<br>';
    html += _helpCmd('/open') + ' \u2014 What\'s open right now<br>';
    html += _helpCmd('/open coffee') + ' \u2014 Coffee shops open now<br>';
    html += _helpCmd('/find pharmacy') + ' \u2014 Find any type of place<br>';
    html += _helpCmd('/nearby') + ' \u2014 What\'s around me<br>';
    html += _helpCmd('/directions CN Tower') + ' \u2014 Get directions<br>';
    html += _helpCmd('/places') + ' \u2014 This help page<br>';
    html += '</span></div>';

    // Filter syntax
    html += '<div style="background:rgba(167,139,250,0.1);padding:8px 10px;border-radius:8px;margin-bottom:10px;">';
    html += '<b>\uD83C\uDFA8 Advanced Filters</b> <span style="color:#94a3b8;font-size:0.8rem;">combine any of these</span><br>';
    html += '<span style="font-size:0.85rem;">';
    html += _helpCmd('/type:food') + ' \u2014 Category (food, coffee, shopping, health...)<br>';
    html += _helpCmd('/cuisine:italian') + ' \u2014 Cuisine type<br>';
    html += _helpCmd('/restrict:halal') + ' \u2014 Dietary (halal, vegan, kosher, gluten-free...)<br>';
    html += _helpCmd('/near:eaton_centre') + ' \u2014 Location (use _ for spaces)<br>';
    html += _helpCmd('/open:now') + ' \u2014 Open filter (now, late, 24h, 2am)<br>';
    html += _helpCmd('/sort:rating') + ' \u2014 Sort by (rating, distance)<br>';
    html += _helpCmd('/radius:5km') + ' \u2014 Search radius<br>';
    html += '<br><b>Example combo:</b> ' + _helpCmd('/restrict:halal /open:late pizza near dundas') + '<br>';
    html += '<b>Example combo:</b> ' + _helpCmd('/cuisine:japanese /sort:rating /near:midtown') + '<br>';
    html += '</span></div>';

    // Categories grid
    html += '<b>Or just ask in English \u2014 tap any example to try it:</b><br><br>';

    // FOOD & DRINK
    html += _helpSection('\uD83C\uDF55 Food & Restaurants', [
      'halal pizza near me', 'vegan restaurants open now', 'best sushi downtown',
      'late night food near Dundas', 'cheap eats near me', 'brunch spots near me',
      'patio restaurants', 'fine dining near me', 'food trucks near me',
      'breakfast near me', 'lunch spots near King St', 'dinner near me open late',
      'shawarma near me', 'ramen near me', 'tacos near me',
      'Indian food near me', 'Ethiopian restaurants', 'Korean BBQ near me',
      'Thai food near me', 'Caribbean food near me', 'dim sum near me',
      'burgers near me', 'wings near me', 'steak near me'
    ]);

    html += _helpSection('\u2615 Coffee & Drinks', [
      'coffee near me', 'cafe with wifi near me', 'bubble tea near me',
      'bars near me', 'rooftop bars', 'craft beer near me',
      'cocktail bars near me', 'juice bar near me', 'smoothies near me',
      'pub near me', 'wine bar', 'late night bars open now'
    ]);

    html += _helpSection('\uD83C\uDF70 Bakeries & Dessert', [
      'bakery near me', 'donuts near me', 'ice cream near me',
      'cupcakes near me', 'dessert near me', 'pastries near me'
    ]);

    // SHOPPING
    html += _helpSection('\uD83D\uDED2 Shopping & Essentials', [
      'grocery store near me', 'convenience store open now', 'LCBO near me',
      'pharmacy near me', 'dollar store near me', 'mall near me',
      'thrift store near me', 'bookstore near me', 'pet store near me',
      'electronics store', 'hardware store near me', 'Canadian Tire near me',
      'Walmart near me', 'Costco near me', 'cannabis dispensary near me'
    ]);

    // HEALTH
    html += _helpSection('\uD83C\uDFE5 Health & Medical', [
      'walk-in clinic near me', 'hospital near me', 'pharmacy open now',
      'dentist near me', 'eye doctor near me', 'vet near me',
      'urgent care near me', 'physiotherapy near me', 'chiropractor near me',
      'mental health services', 'COVID testing near me'
    ]);

    // SERVICES
    html += _helpSection('\uD83D\uDD27 Services', [
      'ATM near me', 'bank near me', 'post office near me',
      'laundromat near me', 'dry cleaner near me', 'barber near me',
      'hair salon near me', 'nail salon near me', 'spa near me',
      'mechanic near me', 'car wash near me', 'locksmith near me',
      'phone repair near me', 'tailor near me', 'shoe repair near me',
      'key cutting near me', 'notary public near me', 'passport photos near me',
      'printing near me'
    ]);

    // TRANSIT
    html += _helpSection('\uD83D\uDE87 Transit & Getting Around', [
      'TTC station near me', 'GO station near me', 'bus stop near me',
      'parking near me', 'gas station near me', 'EV charging near me',
      'car rental near me', 'bike share near me', 'taxi near me',
      'how to get to Union Station', 'directions to Eaton Centre',
      'walk to CN Tower from here', 'transit from Dundas to Scarborough'
    ]);

    // ENTERTAINMENT
    html += _helpSection('\uD83C\uDFAD Entertainment', [
      'movie theater near me', 'bowling near me', 'arcade near me',
      'escape room near me', 'comedy club near me', 'karaoke near me',
      'museum near me', 'art gallery near me', 'pool hall near me',
      'mini golf near me', 'skating rink near me', 'live music near me',
      'nightclub near me', 'things to do tonight'
    ]);

    // FITNESS
    html += _helpSection('\uD83D\uDCAA Fitness & Recreation', [
      'gym near me', 'yoga near me', 'swimming pool near me',
      'basketball court near me', 'tennis court near me', 'dog park near me',
      'park near me', 'hiking trails near me', 'beach near me',
      'rock climbing near me', 'dance studio near me'
    ]);

    // ACCOMMODATION
    html += _helpSection('\uD83C\uDFE8 Accommodation', [
      'hotel near me', 'hostel near me', 'motel near me',
      'Airbnb near me', 'cheap hotel downtown', 'hotel near the airport'
    ]);

    // UTILITIES
    html += _helpSection('\uD83D\uDD0C Utilities & Essentials', [
      'washroom near me', 'public restroom', 'free wifi near me',
      'water fountain near me', 'phone charging near me',
      'where can I print something', 'where can I study'
    ]);

    // EMERGENCY
    html += _helpSection('\uD83C\uDD98 Emergency & Community', [
      'police station near me', 'fire station near me', 'shelter near me',
      'food bank near me', 'warming centre near me', 'community centre near me',
      'library near me', 'mosque near me', 'church near me', 'temple near me'
    ]);

    // SPECIFIC PLACE LOOKUP
    html += _helpSection('\uD83D\uDDFA\uFE0F Specific Place Lookup', [
      'where is Eaton Centre', 'where is Union Station',
      'where is Almadina Bistro', 'where is the nearest Starbucks',
      'is Shoppers Drug Mart open right now', 'what time does Tim Hortons close'
    ]);

    // DIRECTIONS
    html += _helpSection('\uD83E\uDDED Directions', [
      'how to get to Eaton Centre', 'directions to CN Tower',
      'how to get to Almadina Bistro from University and Dundas',
      'walk to Union Station from here', 'transit to Scarborough Town Centre',
      'how far is the ROM from here'
    ]);

    // Dietary filters
    html += '<div style="margin-top:8px;padding:6px 10px;background:rgba(134,239,172,0.1);border-radius:6px;">';
    html += '<b>\uD83C\uDF3F Dietary Filters</b> \u2014 add to any food search:<br>';
    html += '<span style="font-size:0.85rem;">halal \u2022 vegan \u2022 vegetarian \u2022 kosher \u2022 gluten-free \u2022 dairy-free \u2022 keto \u2022 organic \u2022 paleo \u2022 nut-free</span>';
    html += '</div>';

    // Time filters
    html += '<div style="margin-top:6px;padding:6px 10px;background:rgba(250,204,21,0.1);border-radius:6px;">';
    html += '<b>\u23F0 Time Filters</b> \u2014 add to any search:<br>';
    html += '<span style="font-size:0.85rem;">open now \u2022 open late \u2022 open 24/7 \u2022 open at midnight \u2022 open till 3am \u2022 open at 2am</span>';
    html += '</div>';

    html += '</div>';
    addMessage('ai', html, false);
    speakText('Here are all the ways you can find places. Tap any example to try it, or just describe what you need in your own words.');
    setStatus('Ready', '#64748b');
  }

  /** Show help for a specific category */
  function showPlacesHelpCategory(cat) {
    // For now, redirect to the main help (could be expanded later)
    showPlacesHelp();
  }

  /** Helper: format a clickable command for help display */
  function _helpCmd(cmd) {
    return '<a href="#" onclick="window.FTEAssistant && window.FTEAssistant.ask(\'' + cmd.replace(/'/g, "\\'") + '\');return false;" style="color:#818cf8;font-family:monospace;background:rgba(129,140,248,0.1);padding:1px 5px;border-radius:3px;text-decoration:none;">' + escapeHtml(cmd) + '</a>';
  }

  /** Helper: build a help section with clickable examples */
  function _helpSection(title, examples) {
    var html = '<div style="margin-bottom:8px;">';
    html += '<b>' + title + '</b><br>';
    html += '<span style="font-size:0.85rem;">';
    for (var i = 0; i < examples.length; i++) {
      if (i > 0) html += ' \u2022 ';
      html += '<a href="#" onclick="window.FTEAssistant && window.FTEAssistant.ask(\'' + examples[i].replace(/'/g, "\\'") + '\');return false;" style="color:#60a5fa;text-decoration:none;">' + escapeHtml(examples[i]) + '</a>';
    }
    html += '</span></div>';
    return html;
  }


  // ═══════════════════════════════════════════════════════════
  // DIRECTIONS / NAVIGATION TO PLACES
  // ═══════════════════════════════════════════════════════════

  /** Detect if query is asking for directions / how to get somewhere */
  function _isDirectionsQuery(lower) {
    if (/how\s+(?:to|do\s+i|can\s+i|would\s+i)\s+get\s+to/i.test(lower)) return true;
    if (/directions?\s+(?:to|from)/i.test(lower)) return true;
    if (/route\s+(?:to|from)/i.test(lower)) return true;
    if (/(?:walk|walking|drive|driving|transit|bus|subway|ttc)\s+(?:to|from)\s+.{3,}/i.test(lower)) return true;
    if (/(?:get|go)\s+from\s+.+\s+to\s+/i.test(lower)) return true;
    if (/how\s+(?:far|long)\s+(?:is\s+(?:it\s+)?)?(?:to|from)\s+/i.test(lower)) return true;
    return false;
  }

  /**
   * Parse a directions query into { destination, origin, mode }.
   * Handles:
   *   "how to get to Almadina Bistro from University and Dundas"
   *   "directions to Eaton Centre"
   *   "directions from Union Station to CN Tower"
   *   "walk to Almadina Bistro from here"
   *   "how far is Almadina Bistro from Dundas station"
   */
  function _parseDirectionsQuery(text) {
    var lower = text.toLowerCase();
    var result = { destination: '', origin: '', mode: '' };

    // Detect travel mode
    if (/\b(?:walk|walking|on\s+foot)\b/i.test(lower)) result.mode = 'walking';
    else if (/\b(?:driv|car|taxi|uber|lyft)\b/i.test(lower)) result.mode = 'driving';
    else if (/\b(?:transit|bus|subway|ttc|streetcar|go\s+train)\b/i.test(lower)) result.mode = 'transit';
    else if (/\bbik(?:e|ing|cycle)\b/i.test(lower)) result.mode = 'bicycling';

    // Pattern: "from [A] to [B]"
    var fromTo = lower.match(/from\s+(.+?)\s+to\s+(.+?)(?:\s+by\s+.+)?$/i);
    if (fromTo) {
      result.origin = fromTo[1].trim();
      result.destination = fromTo[2].trim();
    }

    // Pattern: "to [B] from [A]"
    if (!result.destination) {
      var toFrom = lower.match(/(?:get\s+to|to|towards)\s+(.+?)\s+from\s+(.+?)(?:\s+by\s+.+)?$/i);
      if (toFrom) {
        result.destination = toFrom[1].trim();
        result.origin = toFrom[2].trim();
      }
    }

    // Pattern: "how to get to [B]" / "directions to [B]" (no origin)
    if (!result.destination) {
      var getTo = lower.match(/(?:get\s+to|directions?\s+to|route\s+to|walk\s+to|drive\s+to|transit\s+to)\s+(.+?)(?:\s+by\s+.+)?$/i);
      if (getTo) {
        result.destination = getTo[1].trim();
      }
    }

    // Pattern: "how far is [B] from [A]"
    if (!result.destination) {
      var howFar = lower.match(/how\s+(?:far|long)\s+(?:is\s+(?:it\s+)?)?(?:to\s+)?(.+?)\s+from\s+(.+?)$/i);
      if (howFar) {
        result.destination = howFar[1].trim();
        result.origin = howFar[2].trim();
      }
    }

    // Clean up filler words from destination and origin
    var fillers = /^(?:the\s+|a\s+|an\s+)/i;
    if (result.destination) result.destination = result.destination.replace(fillers, '').replace(/[?.!]+$/, '').trim();
    if (result.origin) result.origin = result.origin.replace(fillers, '').replace(/[?.!]+$/, '').trim();
    // Remove "here"/"my location" from origin (we'll use GPS instead)
    if (/^(?:here|my\s+location|my\s+place|current\s+location)$/i.test(result.origin)) {
      result.origin = '';
    }

    return result;
  }

  /** Main handler for directions queries */
  async function handleDirections(lower) {
    var parsed = _parseDirectionsQuery(lower);

    if (!parsed.destination) {
      addMessage('ai', '<div class="fte-ai-summary"><b>Directions</b><br><br>' +
        'I can help you get directions! Try asking like:<br>' +
        '\u2022 "How to get to Eaton Centre from Union Station"<br>' +
        '\u2022 "Directions to Almadina Bistro"<br>' +
        '\u2022 "Walk to CN Tower from here"<br>' +
        '\u2022 "Transit from Dundas Station to Scarborough Town Centre"</div>');
      speakText('Tell me where you want to go. For example, how to get to Eaton Centre from Union Station.');
      setStatus('Ready', '#64748b');
      return;
    }

    addMessage('ai', '<div id="fte-ai-directions-loading" class="fte-ai-summary"><b>Getting directions to ' + escapeHtml(parsed.destination) + '...</b><br>' +
      (parsed.origin ? '<span style="color:#94a3b8;">From: ' + escapeHtml(parsed.origin) + '</span><br>' : '') +
      (parsed.mode ? '<span style="color:#a78bfa;">Mode: ' + escapeHtml(parsed.mode) + '</span><br>' : '') +
      '<span style="color:#94a3b8;">Looking up the destination...</span></div>');

    // Search for the destination via nearme.php to get coordinates/address
    var searchUrl = CONFIG.nearMeApi + '?query=' + encodeURIComponent(parsed.destination) + '&limit=1';

    // If origin is specified, use it as location context for the search
    if (parsed.origin) {
      searchUrl += '&location=' + encodeURIComponent(parsed.origin);
    } else {
      // Try to get user GPS for better search results
      var userLoc = await _getNearMeLocation();
      if (userLoc && userLoc.lat && userLoc.lng) {
        searchUrl += '&lat=' + userLoc.lat + '&lng=' + userLoc.lng;
      }
    }

    try {
      var resp = await fetch(searchUrl);
      var data = await resp.json();

      var destName = parsed.destination;
      var destAddress = '';
      var destLat = 0;
      var destLng = 0;
      var destInfo = null;

      if (data.ok && data.results && data.results.length > 0) {
        destInfo = data.results[0];
        destName = destInfo.name;
        destAddress = destInfo.address || '';
        if (destInfo.maps_url) {
          // Extract lat/lng from maps_url if present
          var coordMatch = destInfo.maps_url.match(/query=([0-9.-]+),([0-9.-]+)/);
          if (coordMatch) {
            destLat = parseFloat(coordMatch[1]);
            destLng = parseFloat(coordMatch[2]);
          }
        }
      }

      // Build Google Maps directions URL
      var mapsUrl = 'https://www.google.com/maps/dir/';

      // Origin
      if (parsed.origin) {
        mapsUrl += encodeURIComponent(parsed.origin + ', Toronto, ON') + '/';
      } else {
        mapsUrl += '/'; // empty origin = Google uses user's current location
      }

      // Destination
      if (destLat !== 0 && destLng !== 0) {
        mapsUrl += destLat + ',' + destLng;
      } else if (destAddress) {
        mapsUrl += encodeURIComponent(destAddress);
      } else {
        mapsUrl += encodeURIComponent(destName + ', Toronto, ON');
      }

      // Travel mode
      if (parsed.mode) {
        var modeMap = { walking: 'walking', driving: 'driving', transit: 'transit', bicycling: 'bicycling' };
        if (modeMap[parsed.mode]) {
          mapsUrl += '?travelmode=' + modeMap[parsed.mode];
        }
      }

      // Build response HTML
      var html = '<div class="fte-ai-summary" style="border-left:3px solid #60a5fa;">';
      html += '<b style="font-size:1rem;">\uD83D\uDDFA\uFE0F Directions to ' + escapeHtml(destName) + '</b><br><br>';

      if (parsed.origin) {
        html += '<b>From:</b> ' + escapeHtml(parsed.origin) + '<br>';
      } else {
        html += '<b>From:</b> Your current location<br>';
      }
      html += '<b>To:</b> ' + escapeHtml(destName) + '<br>';
      if (destAddress) {
        html += '<span style="color:#94a3b8;font-size:0.85rem;">' + escapeHtml(destAddress) + '</span><br>';
      }
      if (parsed.mode) {
        html += '<b>Mode:</b> ' + escapeHtml(parsed.mode.charAt(0).toUpperCase() + parsed.mode.slice(1)) + '<br>';
      }

      // Distance if available
      if (destInfo && destInfo.distance_m > 0) {
        html += '<b>Distance:</b> ' + _formatDistance(destInfo.distance_m) + ' (straight line)<br>';
      }

      html += '<br>';

      // Big directions button
      html += '<div style="text-align:center;margin:8px 0;">';
      html += '<a href="' + escapeHtml(mapsUrl) + '" target="_blank" style="display:inline-block;padding:10px 24px;background:#3b82f6;color:white;text-decoration:none;border-radius:8px;font-weight:600;font-size:0.95rem;">';
      html += '\uD83D\uDDFA\uFE0F Open in Google Maps</a>';
      html += '</div>';

      // Travel mode shortcuts
      html += '<div style="text-align:center;margin:6px 0;font-size:0.85rem;">';
      var baseDirUrl = 'https://www.google.com/maps/dir/';
      var originPart = parsed.origin ? encodeURIComponent(parsed.origin + ', Toronto, ON') : '';
      var destPart = (destLat !== 0 && destLng !== 0) ? (destLat + ',' + destLng) : encodeURIComponent(destAddress || destName + ', Toronto, ON');
      html += '<a href="' + baseDirUrl + originPart + '/' + destPart + '?travelmode=transit" target="_blank" style="color:#60a5fa;text-decoration:none;margin:0 6px;">\uD83D\uDE8C Transit</a>';
      html += '<a href="' + baseDirUrl + originPart + '/' + destPart + '?travelmode=walking" target="_blank" style="color:#60a5fa;text-decoration:none;margin:0 6px;">\uD83D\uDEB6 Walk</a>';
      html += '<a href="' + baseDirUrl + originPart + '/' + destPart + '?travelmode=driving" target="_blank" style="color:#60a5fa;text-decoration:none;margin:0 6px;">\uD83D\uDE97 Drive</a>';
      html += '<a href="' + baseDirUrl + originPart + '/' + destPart + '?travelmode=bicycling" target="_blank" style="color:#60a5fa;text-decoration:none;margin:0 6px;">\uD83D\uDEB2 Bike</a>';
      html += '</div>';

      // Destination details if found
      if (destInfo) {
        html += '<div style="margin-top:10px;padding:8px 10px;background:rgba(100,116,139,0.08);border-radius:8px;">';
        html += '<b>' + escapeHtml(destInfo.name) + '</b>';
        if (destInfo.category) html += ' <span style="color:#94a3b8;">(' + escapeHtml(destInfo.category) + ')</span>';
        html += '<br>';
        if (destInfo.open_now === true) html += '<span style="color:#86efac;font-weight:600;">\u2022 Open now</span> ';
        else if (destInfo.open_now === false) html += '<span style="color:#f87171;">\u2022 Closed</span> ';
        if (destInfo.phone) html += '<br><a href="tel:' + escapeHtml(destInfo.phone.replace(/[^0-9+]/g, '')) + '" style="color:#60a5fa;font-size:0.85rem;">\uD83D\uDCDE ' + escapeHtml(destInfo.phone) + '</a>';
        if (destInfo.website) html += ' <a href="' + escapeHtml(destInfo.website) + '" target="_blank" style="color:#60a5fa;font-size:0.85rem;">\uD83C\uDF10 Website</a>';
        html += '</div>';
      }

      html += '</div>';

      // Replace loading message
      var loadEl = document.getElementById('fte-ai-directions-loading');
      if (loadEl) {
        loadEl.outerHTML = html;
      } else {
        addMessage('ai', html);
      }

      // Speak
      var spoken = 'Here are directions to ' + destName + '.';
      if (parsed.origin) spoken += ' From ' + parsed.origin + '.';
      if (destInfo && destInfo.distance_m > 0) spoken += ' It\'s about ' + _formatDistance(destInfo.distance_m) + ' away.';
      spoken += ' Tap Open in Google Maps for step by step directions.';
      speakText(spoken);
      setStatus('Ready', '#64748b');

    } catch (err) {
      // Fallback: even if API fails, still generate a directions URL
      var fallbackUrl = 'https://www.google.com/maps/dir/';
      if (parsed.origin) {
        fallbackUrl += encodeURIComponent(parsed.origin + ', Toronto, ON') + '/';
      } else {
        fallbackUrl += '/';
      }
      fallbackUrl += encodeURIComponent(parsed.destination + ', Toronto, ON');
      if (parsed.mode) fallbackUrl += '?travelmode=' + parsed.mode;

      var fallbackHtml = '<div class="fte-ai-summary" style="border-left:3px solid #60a5fa;">';
      fallbackHtml += '<b>\uD83D\uDDFA\uFE0F Directions to ' + escapeHtml(parsed.destination) + '</b><br><br>';
      fallbackHtml += 'I couldn\'t look up the exact location, but you can get directions on Google Maps:<br><br>';
      fallbackHtml += '<div style="text-align:center;"><a href="' + escapeHtml(fallbackUrl) + '" target="_blank" style="display:inline-block;padding:10px 24px;background:#3b82f6;color:white;text-decoration:none;border-radius:8px;font-weight:600;">';
      fallbackHtml += '\uD83D\uDDFA\uFE0F Open in Google Maps</a></div>';
      fallbackHtml += '</div>';

      var loadEl2 = document.getElementById('fte-ai-directions-loading');
      if (loadEl2) {
        loadEl2.outerHTML = fallbackHtml;
      } else {
        addMessage('ai', fallbackHtml);
      }
      speakText('Here are directions to ' + parsed.destination + '. Tap to open in Google Maps.');
      setStatus('Ready', '#64748b');
    }
  }


  // ═══════════════════════════════════════════════════════════
  // HANDLERS: MOVIES
  // ═══════════════════════════════════════════════════════════

  async function handleMovies(lower, raw) {
    var section = detectSection();
    var isOnMoviesPage = section === 'movies' || section === 'movies_v2' || section === 'movies_v3';

    // Extract search term from various patterns
    var searchTerm = null;
    var playMatch = raw.match(/(?:play|watch|show me|find|search|look for|queue)\s+(?:me\s+)?(?:up\s+)?(?:a\s+)?(?:list\s+of\s+)?(?:the\s+)?(.+?)(?:\s+trailers?|\s+movie|\s+film)?$/i);
    if (playMatch) {
      searchTerm = playMatch[1].trim();
      // Clean up common suffixes
      searchTerm = searchTerm.replace(/\s+(trailer|movie|film|show|series|tv show)s?$/i, '').trim();
    }
    // Also try simpler patterns
    if (!searchTerm) {
      var simpleMatch = raw.match(/(?:play|watch|queue|find)\s+(.+)/i);
      if (simpleMatch) searchTerm = simpleMatch[1].replace(/\s+(trailer|movie|film)s?$/i, '').trim();
    }

    var html = '<div class="fte-ai-summary">';
    html += '<b>Movies & TV Shows</b><br><br>';

    // ── If user is ON a movies page, try to interact directly ──
    if (isOnMoviesPage && searchTerm) {

      // V3 has a built-in search bar
      if (section === 'movies_v3') {
        var searched = triggerV3Search(searchTerm);
        if (searched) {
          html += 'Searching for <b>"' + escapeHtml(searchTerm) + '"</b> on this page...<br><br>';
          html += 'The search results should appear above. Scroll through to find your trailer!';
          html += '</div>';
          addMessage('ai', html, false);
          speakText('I\'ve searched for ' + searchTerm + ' on this page. Check the results above.');
          setStatus('Ready', '#64748b');
          return;
        }
      }

      // V1 or V2: try to find and scroll to the matching card
      var match = findMovieOnPage(searchTerm);
      if (match) {
        scrollToMovieCard(match.card);
        html += 'Found <b>"' + escapeHtml(match.title) + '"</b>!<br><br>';
        html += 'I\'ve scrolled to it \u2014 the trailer should be playing now.<br>';
        html += '<span style="color:#64748b;font-size:11px;">Card #' + (match.index + 1) + ' \u2022 Match confidence: ' + Math.round(match.score) + '%</span>';
        html += '</div>';
        addMessage('ai', html, false);
        speakText('Found ' + match.title + '! I\'ve scrolled to it. The trailer should be playing now.');
        setStatus('Ready', '#64748b');
        return;
      }

      // Not found on current page — offer alternatives
      var allTitles = getAllMovieTitles();
      html += 'I couldn\'t find <b>"' + escapeHtml(searchTerm) + '"</b> on this page.<br><br>';

      if (allTitles.length > 0) {
        // Show some available titles that might be similar
        var suggestions = [];
        for (var ti = 0; ti < allTitles.length && suggestions.length < 6; ti++) {
          suggestions.push(allTitles[ti].title);
        }
        html += '<b>Available on this page:</b><br>';
        for (var si = 0; si < suggestions.length; si++) {
          html += '\u2022 <a href="#" onclick="window.FTEAssistant.ask(\'play ' + escapeHtml(suggestions[si]) + '\');return false;" style="color:#818cf8;">' + escapeHtml(suggestions[si]) + '</a><br>';
        }
        if (allTitles.length > 6) html += '<span style="color:#64748b;font-size:11px;">...and ' + (allTitles.length - 6) + ' more. Scroll down to browse all.</span><br>';
      }

      html += '<br>Or search on V3 which has all titles:<br>';
      html += '<a href="/MOVIESHOWS3/?search=' + encodeURIComponent(searchTerm) + '" target="_blank" style="color:#818cf8;">Search "' + escapeHtml(searchTerm) + '" in V3</a>';
      html += '</div>';
      addMessage('ai', html, false);
      speakText('I couldn\'t find ' + searchTerm + ' on this page, but I\'ve listed some available titles you can click to play. Or try V3 for the full catalog.');
      setStatus('Ready', '#64748b');
      return;
    }

    // ── On a movies page without a search term ──
    if (isOnMoviesPage && !searchTerm) {
      var titles = getAllMovieTitles();
      if (titles.length > 0) {
        html += 'You\'re browsing ' + titles.length + ' movies & TV shows. Swipe up/down to browse trailers.<br><br>';
        html += '<b>What can I do here?</b><br>';
        html += '\u2022 <b>"Play [title]"</b> \u2014 I\'ll scroll to that trailer<br>';
        html += '\u2022 <b>"Play Spider-Man"</b> \u2014 fuzzy search, I\'ll find the closest match<br>';
        html += '\u2022 <b>"Queue Avatar trailers"</b> \u2014 I\'ll search for it<br><br>';
        html += '<b>Some titles on this page:</b><br>';
        for (var tj = 0; tj < Math.min(8, titles.length); tj++) {
          html += '\u2022 <a href="#" onclick="window.FTEAssistant.ask(\'play ' + escapeHtml(titles[tj].title) + '\');return false;" style="color:#818cf8;">' + escapeHtml(titles[tj].title) + '</a><br>';
        }
        if (titles.length > 8) html += '<span style="color:#64748b;font-size:11px;">...and ' + (titles.length - 8) + ' more</span>';
        html += '</div>';
        addMessage('ai', html, false);
        speakText('You\'re browsing ' + titles.length + ' titles. Tell me what you want to watch and I\'ll scroll right to it. For example, say play Avatar or play Shrek 5.');
        setStatus('Ready', '#64748b');
        return;
      }
    }

    // ── Not on a movies page, or generic movie query ──
    if (searchTerm) {
      html += 'Looking for <b>"' + escapeHtml(searchTerm) + '"</b> trailers...<br><br>';
      html += 'I can play it for you! Go to one of our movie pages and ask again:<br><br>';
      html += '\u2022 <a href="/MOVIESHOWS/" target="_blank" style="color:#818cf8;">V1 \u2014 Theater Info + Ratings</a> (say "play ' + escapeHtml(searchTerm) + '" there)<br>';
      html += '\u2022 <a href="/movieshows2/" target="_blank" style="color:#818cf8;">V2 \u2014 Genre Filters + Playlists</a><br>';
      html += '\u2022 <a href="/MOVIESHOWS3/?search=' + encodeURIComponent(searchTerm) + '" target="_blank" style="color:#818cf8;">V3 \u2014 Search "' + escapeHtml(searchTerm) + '" directly</a>';
    } else {
      html += 'Swipe through trailers \u2014 your next binge awaits!<br><br>';
      html += 'We have 3 versions of the Movies & TV experience:<br>';
      html += '\u2022 <a href="/MOVIESHOWS/" target="_blank" style="color:#818cf8;">V1 \u2014 Theater Info + Ratings</a><br>';
      html += '\u2022 <a href="/movieshows2/" target="_blank" style="color:#818cf8;">V2 \u2014 Genre Filters + Playlists</a><br>';
      html += '\u2022 <a href="/MOVIESHOWS3/" target="_blank" style="color:#818cf8;">V3 \u2014 Full Browse & Search</a>';
    }
    html += '</div>';
    addMessage('ai', html, false);
    if (searchTerm) {
      speakText('To play ' + searchTerm + ', head to one of our movie pages. I\'ve included a direct search link for V3 which has the full catalog.');
    } else {
      speakText('We have 3 versions of the movie experience. V1 has theater info, V2 has genre filters, and V3 has full search and queuing.');
    }
    setStatus('Ready', '#64748b');
  }

  // ═══════════════════════════════════════════════════════════
  // HANDLERS: NOW PLAYING / MOVIE SHOWTIMES
  // ═══════════════════════════════════════════════════════════

  /** Get film events from the cached events data */
  function _getFilmEventsFromCache() {
    if (!state.eventsData || !Array.isArray(state.eventsData)) return [];
    var now = new Date();
    var weekFromNow = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
    var filmEvents = [];
    for (var i = 0; i < state.eventsData.length; i++) {
      var ev = state.eventsData[i];
      var text = ((ev.title || '') + ' ' + (ev.description || '')).toLowerCase();
      if (/film|movie|cinema|screening|indoor movie|movie night/i.test(text)) {
        var evDate = new Date(ev.date);
        if (evDate >= now && evDate <= weekFromNow) {
          filmEvents.push(ev);
        }
      }
    }
    filmEvents.sort(function(a, b) { return new Date(a.date) - new Date(b.date); });
    return filmEvents.slice(0, 5);
  }

  /** Format a date for display (e.g., "Sat Feb 8, 7:00 PM") */
  function _formatEventDate(dateStr) {
    try {
      var d = new Date(dateStr);
      var days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      var h = d.getHours();
      var m = d.getMinutes();
      var ampm = h >= 12 ? 'PM' : 'AM';
      h = h % 12;
      if (h === 0) h = 12;
      var minStr = m < 10 ? '0' + m : '' + m;
      return days[d.getDay()] + ' ' + months[d.getMonth()] + ' ' + d.getDate() + ', ' + h + ':' + minStr + ' ' + ampm;
    } catch (e) {
      return dateStr;
    }
  }

  /** Render the combined "now playing + theaters + events" card */
  function _renderNowPlayingCard(nowPlayingData, theaterData, filmEvents, userLoc, timeFilter, showtimesData) {
    timeFilter = timeFilter || { type: null, label: '', googleQuery: 'showtimes' };
    showtimesData = showtimesData || { ok: false };
    var defaultTheater = _getDefaultTheater();
    var html = '<div class="fte-ai-summary">';

    // Determine primary theater (default > closest)
    var primaryTheater = '';
    if (defaultTheater) {
      primaryTheater = defaultTheater;
    } else if (theaterData && theaterData.ok && theaterData.results && theaterData.results.length > 0) {
      primaryTheater = theaterData.results[0].name;
    }
    var primaryTheaterUrl = primaryTheater ? _getTheaterShowtimeUrl(primaryTheater, timeFilter) : '';

    // ── Time filter banner (if user specified a time) ──
    if (timeFilter.label) {
      html += '<div style="margin-bottom:10px;padding:8px 12px;background:rgba(251,191,36,0.12);border:1px solid rgba(251,191,36,0.25);border-radius:8px;font-size:0.9rem;">';
      html += '<span style="color:#fbbf24;font-weight:600;">\u23F0 Showtimes ' + escapeHtml(timeFilter.label) + '</span>';
      if (primaryTheater) {
        html += ' at <b>' + escapeHtml(primaryTheater) + '</b>';
      }
      html += '<br><a href="' + escapeHtml(primaryTheaterUrl || '#') + '" target="_blank" style="color:#60a5fa;font-size:0.85rem;text-decoration:none;">View exact showtimes \u2192</a>';
      html += '</div>';
    }

    // ── "Set a favorite theater" prompt (when no default is set) ──
    if (!defaultTheater && theaterData && theaterData.ok && theaterData.results && theaterData.results.length > 0) {
      html += '<div style="margin-bottom:12px;padding:10px 14px;background:rgba(251,191,36,0.06);border:1px solid rgba(251,191,36,0.15);border-radius:10px;">';
      html += '<div style="font-size:0.9rem;color:#fbbf24;font-weight:600;margin-bottom:4px;">\u2606 Pick your favorite theater</div>';
      html += '<div style="font-size:0.82rem;color:#94a3b8;margin-bottom:8px;">Set a default to quickly see showtimes with one tap next time.</div>';
      html += '<div style="display:flex;flex-wrap:wrap;gap:6px;">';
      var theaterPickCount = Math.min(theaterData.results.length, 4);
      for (var tp = 0; tp < theaterPickCount; tp++) {
        var tpName = theaterData.results[tp].name;
        var tpDist = _formatDistance(theaterData.results[tp].distance_m);
        var safeTp = tpName.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
        html += '<button onclick="__fteSetDefaultTheater(\'' + safeTp + '\')" style="padding:5px 12px;border-radius:16px;border:1px solid rgba(99,102,241,0.25);background:rgba(99,102,241,0.08);color:#a5b4fc;font-size:0.8rem;cursor:pointer;transition:all .2s;" onmouseover="this.style.background=\'rgba(99,102,241,0.2)\'" onmouseout="this.style.background=\'rgba(99,102,241,0.08)\'">';
        html += escapeHtml(tpName) + ' <span style="color:#94a3b8;">(' + tpDist + ')</span>';
        html += '</button>';
      }
      html += '</div>';
      html += '</div>';
    }

    // ── Primary theater showtime banner ──
    if (primaryTheater) {
      var bannerBg = defaultTheater ? 'rgba(251,191,36,0.08)' : 'rgba(96,165,250,0.08)';
      var bannerBorder = defaultTheater ? 'rgba(251,191,36,0.2)' : 'rgba(96,165,250,0.2)';
      html += '<div id="fte-primary-theater-banner" style="margin-bottom:12px;padding:10px 14px;background:' + bannerBg + ';border:1px solid ' + bannerBorder + ';border-radius:10px;">';
      html += '<div class="fte-primary-theater-label" style="font-size:0.82rem;color:#94a3b8;margin-bottom:2px;">' + (defaultTheater ? '\u2605 Your Theater' : '\uD83D\uDCCD Nearest Theater') + '</div>';
      html += '<b class="fte-primary-theater-name" style="font-size:1.05rem;">' + escapeHtml(primaryTheater) + '</b>';
      html += '<div style="margin-top:6px;">';
      html += '<a href="' + escapeHtml(primaryTheaterUrl) + '" target="_blank" style="display:inline-block;padding:6px 16px;background:#6366f1;color:#fff;border-radius:6px;text-decoration:none;font-size:0.9rem;font-weight:600;">View Showtimes</a>';
      if (!defaultTheater) {
        var safePrimary = primaryTheater.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
        html += ' <span class="fte-theater-default-link" data-theater="' + escapeHtml(primaryTheater) + '" style="color:#64748b;font-size:0.8rem;cursor:pointer;margin-left:8px;" onclick="__fteSetDefaultTheater(\'' + safePrimary + '\')">\u2606 Set as default</span>';
      }
      html += '</div>';
      html += '</div>';
    }

    // ── Section 0: REAL SHOWTIMES (from Cineplex API) ──
    if (showtimesData.ok && showtimesData.showtimes && showtimesData.showtimes.length > 0) {
      var stTheater = showtimesData.theatre || primaryTheater;
      html += '<b style="font-size:1.05rem;">Showtimes at ' + escapeHtml(stTheater) + '</b>';
      if (timeFilter.label) {
        html += ' <span style="color:#fbbf24;font-size:0.85rem;">' + escapeHtml(timeFilter.label) + '</span>';
      }
      html += '<br>';
      if (showtimesData.date) {
        html += '<span style="font-size:0.78rem;color:#64748b;">' + escapeHtml(showtimesData.date) + '</span>';
        if (showtimesData.cached && showtimesData.cache_age_minutes > 0) {
          html += '<span style="font-size:0.78rem;color:#64748b;"> \u00b7 Updated ' + showtimesData.cache_age_minutes + ' min ago</span>';
        }
      }
      html += '<br><br>';

      // Time filter helper: check if a session time matches the filter
      var nowMs = Date.now();
      function _sessMatchesFilter(sess, tf) {
        if (!tf || !tf.type) return true; // no filter = show all
        var raw = sess.time_raw || '';
        var sortT = sess.time_sort || '';
        var sessMs = raw ? new Date(raw).getTime() : 0;
        // Parse HH:MM from time_sort
        var sortParts = sortT.split(':');
        var sessH = sortParts.length >= 2 ? parseInt(sortParts[0], 10) : -1;
        var sessM = sortParts.length >= 2 ? parseInt(sortParts[1], 10) : 0;

        if (tf.type === 'now') {
          // Starting within next 45 minutes
          return sessMs > 0 && sessMs >= nowMs && sessMs <= nowMs + 45 * 60000;
        } else if (tf.type === 'soon') {
          // Starting within next 90 minutes
          return sessMs > 0 && sessMs >= nowMs && sessMs <= nowMs + 90 * 60000;
        } else if (tf.type === 'tonight') {
          // 6pm onwards
          return sessH >= 18;
        } else if (tf.type === 'at_time' && tf.targetTime) {
          // Within ±45 minutes of target
          var tgt = tf.targetTime.getTime();
          return sessMs > 0 && sessMs >= tgt - 45 * 60000 && sessMs <= tgt + 45 * 60000;
        } else if (tf.type === 'in_minutes' && tf.targetTime) {
          // Within ±30 minutes of target
          var tgt2 = tf.targetTime.getTime();
          return sessMs > 0 && sessMs >= tgt2 - 30 * 60000 && sessMs <= tgt2 + 30 * 60000;
        }
        return true; // 'today', 'tomorrow', unknown → show all
      }

      // Filter movies to only those with matching sessions, and count
      var stMovies = showtimesData.showtimes;
      var filteredMovies = [];
      for (var fi = 0; fi < stMovies.length; fi++) {
        var fm = stMovies[fi];
        var fSessions = fm.sessions || [];
        var matchedSessions = [];
        for (var fj = 0; fj < fSessions.length; fj++) {
          var fs = fSessions[fj];
          if (fs.is_past) continue;
          if (_sessMatchesFilter(fs, timeFilter)) matchedSessions.push(fs);
        }
        if (matchedSessions.length > 0) {
          filteredMovies.push({ movie: fm.movie, poster_url: fm.poster_url, runtime: fm.runtime, film_url: fm.film_url, sessions: matchedSessions });
        }
      }

      // If time filter produced zero results, fall back to all non-past sessions
      if (filteredMovies.length === 0 && timeFilter.type) {
        html += '<div style="font-size:0.85rem;color:#fbbf24;margin-bottom:8px;">No movies match "' + escapeHtml(timeFilter.label) + '" — showing all upcoming showtimes instead.</div>';
        for (var fi2 = 0; fi2 < stMovies.length; fi2++) {
          var fm2 = stMovies[fi2];
          var fSessions2 = fm2.sessions || [];
          var matchedSessions2 = [];
          for (var fj2 = 0; fj2 < fSessions2.length; fj2++) {
            if (!fSessions2[fj2].is_past) matchedSessions2.push(fSessions2[fj2]);
          }
          if (matchedSessions2.length > 0) {
            filteredMovies.push({ movie: fm2.movie, poster_url: fm2.poster_url, runtime: fm2.runtime, film_url: fm2.film_url, sessions: matchedSessions2 });
          }
        }
      }

      var stCount = Math.min(filteredMovies.length, 10);
      for (var si = 0; si < stCount; si++) {
        var stm = filteredMovies[si];
        html += '<div style="margin-bottom:8px;padding:6px 8px;background:rgba(100,116,139,0.06);border-radius:8px;">';
        html += '<div style="display:flex;align-items:center;gap:8px;">';
        if (stm.poster_url) {
          html += '<img src="' + escapeHtml(stm.poster_url) + '" style="width:32px;height:48px;border-radius:4px;object-fit:cover;" loading="lazy" onerror="this.style.display=\'none\'">';
        }
        html += '<div style="flex:1;min-width:0;">';
        html += '<b style="font-size:0.9rem;">' + escapeHtml(stm.movie) + '</b>';
        if (stm.runtime > 0) {
          html += ' <span style="color:#64748b;font-size:0.75rem;">' + stm.runtime + 'min</span>';
        }
        html += '<div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:3px;">';
        var stSessions = stm.sessions || [];
        for (var sj = 0; sj < stSessions.length; sj++) {
          var sess = stSessions[sj];
          var sessStyle = 'display:inline-block;padding:3px 8px;border-radius:4px;font-size:0.78rem;font-weight:600;text-decoration:none;';
          if (sess.is_sold_out) {
            sessStyle += 'background:rgba(248,113,113,0.15);color:#f87171;';
          } else if (sess.just_started) {
            sessStyle += 'background:rgba(251,191,36,0.15);color:#fbbf24;';
          } else if (sess.ticket_url) {
            sessStyle += 'background:rgba(99,102,241,0.12);color:#a5b4fc;';
          } else {
            sessStyle += 'background:rgba(100,116,139,0.12);color:#94a3b8;';
          }
          var sessLabel = sess.time;
          if (sess.experience && sess.experience !== 'Regular') {
            sessLabel += ' ' + sess.experience;
          }
          if (sess.is_sold_out) {
            sessLabel += ' SOLD OUT';
          } else if (sess.just_started && sess.minutes_ago > 0) {
            sessLabel += ' (started ' + sess.minutes_ago + 'min ago)';
          }
          if (sess.ticket_url && !sess.is_sold_out) {
            html += '<a href="' + escapeHtml(sess.ticket_url) + '" target="_blank" style="' + sessStyle + '">' + escapeHtml(sessLabel) + '</a>';
          } else {
            html += '<span style="' + sessStyle + '">' + escapeHtml(sessLabel) + '</span>';
          }
        }
        html += '</div>';
        html += '</div>';
        html += '</div>';
        html += '</div>';
      }
      if (filteredMovies.length > stCount) {
        html += '<div style="font-size:0.8rem;color:#94a3b8;">...and ' + (filteredMovies.length - stCount) + ' more movies showing today.</div>';
      }
      // Disclaimer with link to official source
      var cineplexLink = showtimesData.cineplex_url || 'https://www.cineplex.com/Showtimes';
      html += '<div style="margin-top:6px;font-size:0.75rem;color:#64748b;">';
      html += 'Showtimes are approximate and may change. ';
      html += '<a href="' + escapeHtml(cineplexLink) + '" target="_blank" style="color:#60a5fa;">Verify at cineplex.com</a>';
      html += '</div>';
      html += '<br>';
    }

    // ── Section 1: Now Playing in Theaters ──
    html += '<b style="font-size:1.05rem;">Now Playing in Theaters</b>';
    if (primaryTheater) {
      html += '<span style="font-size:0.82rem;color:#94a3b8;margin-left:6px;">(tap poster for showtimes)</span>';
    }
    html += '<br><br>';

    if (nowPlayingData.ok && nowPlayingData.movies && nowPlayingData.movies.length > 0) {
      // Horizontal scrolling poster row
      html += '<div style="display:flex;gap:10px;overflow-x:auto;padding-bottom:8px;-webkit-overflow-scrolling:touch;">';
      var movies = nowPlayingData.movies;
      var showCount = Math.min(movies.length, 12);
      for (var i = 0; i < showCount; i++) {
        var m = movies[i];
        var posterSrc = m.poster_url || '';
        // Link to showtimes at primary theater, or generic search
        var movieLink;
        if (primaryTheater) {
          movieLink = 'https://www.google.com/search?q=' + encodeURIComponent(m.title + ' showtimes ' + primaryTheater);
        } else {
          movieLink = 'https://www.google.com/maps/search/' + encodeURIComponent(m.title + ' ' + timeFilter.googleQuery);
        }
        html += '<div style="flex:0 0 120px;text-align:center;">';
        html += '<a href="' + escapeHtml(movieLink) + '" target="_blank" style="text-decoration:none;">';
        if (posterSrc) {
          html += '<img src="' + escapeHtml(posterSrc) + '" alt="' + escapeHtml(m.title) + '" '
            + 'style="width:120px;height:180px;border-radius:8px;object-fit:cover;box-shadow:0 2px 8px rgba(0,0,0,0.3);" '
            + 'loading="lazy" onerror="this.style.display=\'none\'">';
        } else {
          html += '<div style="width:120px;height:180px;border-radius:8px;background:#1a1a2e;display:flex;align-items:center;justify-content:center;color:#94a3b8;font-size:0.75rem;padding:8px;">'
            + escapeHtml(m.title) + '</div>';
        }
        html += '</a>';
        html += '<div style="margin-top:4px;font-size:0.78rem;font-weight:600;color:#e2e8f0;line-height:1.2;max-height:2.4em;overflow:hidden;">' + escapeHtml(m.title) + '</div>';
        // Rating stars
        if (m.rating > 0) {
          var starCount = Math.round(m.rating / 2);
          var stars = '';
          for (var s = 0; s < 5; s++) stars += (s < starCount) ? '\u2605' : '\u2606';
          html += '<div style="font-size:0.72rem;color:#fbbf24;">' + stars + ' ' + m.rating + '</div>';
        }
        // Genre
        if (m.genre_names) {
          html += '<div style="font-size:0.68rem;color:#94a3b8;max-height:1.4em;overflow:hidden;">' + escapeHtml(m.genre_names) + '</div>';
        }
        html += '</div>';
      }
      html += '</div>';

      // TMDB attribution
      html += '<div style="font-size:0.7rem;color:#64748b;margin-top:4px;">Data by TMDB';
      if (nowPlayingData.cached && nowPlayingData.cache_age_minutes > 0) {
        html += ' \u00b7 Updated ' + nowPlayingData.cache_age_minutes + ' min ago';
      }
      html += '</div>';
    } else {
      html += '<span style="color:#94a3b8;">Could not load now-playing data. Try again later.</span><br>';
    }

    // ── Section 2: Theaters Near You ──
    html += '<br><b style="font-size:1.05rem;">Theaters Near You</b><br><br>';

    if (theaterData.ok && theaterData.results && theaterData.results.length > 0) {
      var theaters = theaterData.results;
      var theaterCount = Math.min(theaters.length, 5);
      for (var ti = 0; ti < theaterCount; ti++) {
        var t = theaters[ti];
        var isDefault = defaultTheater && t.name.toLowerCase() === defaultTheater.toLowerCase();
        var tShowtimeUrl = _getTheaterShowtimeUrl(t.name, timeFilter);
        var borderColor = isDefault ? '#fbbf24' : (t.open_now === true ? '#86efac' : t.open_now === false ? '#f87171' : '#64748b');

        html += '<div style="margin-bottom:10px;padding:8px 10px;background:rgba(100,116,139,0.08);border-radius:8px;border-left:2px solid ' + borderColor + ';">';
        html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;">';
        html += '<b style="font-size:0.95rem;">' + (isDefault ? '\u2605 ' : (ti + 1) + '. ') + escapeHtml(t.name) + '</b>';
        html += '<span style="color:#a78bfa;font-size:0.8rem;white-space:nowrap;margin-left:8px;">' + _formatDistance(t.distance_m) + '</span>';
        html += '</div>';

        if (t.address) {
          html += '<div style="font-size:0.83rem;color:#94a3b8;margin-top:2px;">' + escapeHtml(t.address) + '</div>';
        }

        // Action links with showtimes
        html += '<div style="font-size:0.8rem;margin-top:4px;display:flex;flex-wrap:wrap;gap:8px;align-items:center;">';
        html += '<a href="' + escapeHtml(tShowtimeUrl) + '" target="_blank" style="color:#6366f1;text-decoration:none;font-weight:600;">\uD83C\uDFAC Showtimes</a>';
        if (t.maps_url) {
          html += '<a href="' + escapeHtml(t.maps_url) + '" target="_blank" style="color:#60a5fa;text-decoration:none;">\uD83D\uDDFA\uFE0F Directions</a>';
        }
        var safeT = t.name.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
        if (!isDefault) {
          html += '<span class="fte-theater-default-link" data-theater="' + escapeHtml(t.name) + '" style="color:#64748b;cursor:pointer;" onclick="__fteSetDefaultTheater(\'' + safeT + '\')">\u2606 Set as default</span>';
        } else {
          html += '<span class="fte-theater-default-link" data-theater="' + escapeHtml(t.name) + '" style="color:#fbbf24;">\u2605 Default theater</span>';
        }
        html += '</div>';
        html += '</div>';
      }
    } else if (!userLoc) {
      html += '<span style="color:#94a3b8;">Enable location access to find theaters near you, or search "movie theatre near [your area]".</span><br>';
    } else {
      html += '<span style="color:#94a3b8;">No theaters found nearby. Try expanding your search area.</span><br>';
    }

    // ── Section 3: Film Events This Week (conditional) ──
    if (filmEvents.length > 0) {
      html += '<br><b style="font-size:1.05rem;">Film Events This Week</b><br><br>';
      for (var j = 0; j < filmEvents.length; j++) {
        var ev = filmEvents[j];
        html += '<div style="margin-bottom:6px;padding:5px 8px;background:rgba(129,140,248,0.08);border-radius:6px;">';
        html += '<b style="font-size:0.88rem;">' + escapeHtml(ev.title) + '</b>';
        if (ev.date) {
          html += ' &mdash; <span style="color:#a78bfa;font-size:0.82rem;">' + _formatEventDate(ev.date) + '</span>';
        }
        if (ev.url) {
          html += ' <a href="' + escapeHtml(ev.url) + '" target="_blank" style="color:#60a5fa;font-size:0.8rem;">[Details]</a>';
        }
        html += '</div>';
      }
    }

    // ── Footer: Primary theater showtimes link ──
    var footerUrl = primaryTheaterUrl || ('https://www.google.com/maps/search/movie+' + timeFilter.googleQuery.replace(/\s+/g, '+') + '+near+me');
    if (!primaryTheater && userLoc && userLoc.lat) {
      footerUrl = 'https://www.google.com/maps/search/movie+' + timeFilter.googleQuery.replace(/\s+/g, '+') + '/@' + userLoc.lat + ',' + userLoc.lng + ',14z';
    }
    var footerLabel = primaryTheater
      ? 'All showtimes at ' + primaryTheater
      : (timeFilter.label ? 'See showtimes ' + timeFilter.label + ' on Google' : 'See all showtimes on Google');
    html += '<div style="margin-top:10px;padding:8px 10px;background:rgba(52,168,83,0.1);border-radius:6px;">';
    html += '<a href="' + escapeHtml(footerUrl) + '" target="_blank" style="color:#34a853;font-weight:600;text-decoration:none;font-size:0.9rem;">';
    html += '\uD83C\uDFAC ' + escapeHtml(footerLabel) + '</a>';
    html += '</div>';

    // ── Footer: Browse trailers ──
    html += '<div style="margin-top:6px;padding:6px 10px;background:rgba(129,140,248,0.08);border-radius:6px;font-size:0.85rem;">';
    html += '\uD83C\uDFAC <a href="/MOVIESHOWS3/" target="_blank" style="color:#818cf8;text-decoration:none;font-weight:600;">Browse trailers on MovieShows</a>';
    html += '</div>';

    html += '</div>';
    return html;
  }

  /** Main handler: "what movies are playing near me" */
  async function handleNowPlayingNearMe(lower, raw) {
    state.processing = true;
    showStopBtn(true);

    // Parse time filter from query
    var timeFilter = _parseMovieTimeFilter(lower);
    var statusMsg = timeFilter.label ? 'Finding movies ' + timeFilter.label + '...' : 'Finding movies near you...';
    setStatus(statusMsg, '#f59e0b');

    var loadingText = timeFilter.label
      ? 'Finding movies <b>' + escapeHtml(timeFilter.label) + '</b> near you...'
      : 'Finding movies playing near you...';
    addMessage('ai', '<div id="fte-ai-nowplaying-loading" class="fte-ai-summary">' +
      '<b>' + loadingText + '</b><br>' +
      '<span style="color:#94a3b8;">Checking theaters and now-playing listings...</span></div>', false);

    // Get user location for theater search
    var userLoc = await _getNearMeLocation();
    var locParams = '';
    if (userLoc && userLoc.lat) {
      locParams = '&lat=' + userLoc.lat + '&lng=' + userLoc.lng;
    }

    // Fire all requests in parallel
    var nowPlayingPromise = fetch(CONFIG.nowPlayingApi + '?region=CA')
      .then(function(r) { return r.json(); })
      .catch(function() { return { ok: false }; });

    var theatersPromise = fetch(CONFIG.nearMeApi + '?query=cinema&limit=5&provider=google' + locParams)
      .then(function(r) { return r.json(); })
      .catch(function() { return { ok: false, results: [] }; });

    // Fetch Cineplex showtimes for the primary theater
    var defaultT = _getDefaultTheater();
    var showtimesPromise = Promise.resolve({ ok: false });
    var stDateParam = '';
    if (timeFilter.type === 'tomorrow') {
      var tmrw = new Date();
      tmrw.setDate(tmrw.getDate() + 1);
      stDateParam = '&date=' + tmrw.getFullYear() + '-' + String(tmrw.getMonth() + 1).padStart(2, '0') + '-' + String(tmrw.getDate()).padStart(2, '0');
    }
    if (defaultT) {
      showtimesPromise = fetch(CONFIG.cineplexShowtimesApi + '?theatre=' + encodeURIComponent(defaultT) + stDateParam)
        .then(function(r) { return r.json(); })
        .catch(function() { return { ok: false }; });
    }

    var results = await Promise.all([nowPlayingPromise, theatersPromise, showtimesPromise]);
    var nowPlayingData = results[0];
    var theaterData = results[1];
    var showtimesData = results[2];

    // If no default theater but we have nearby theaters, try fetching showtimes for the nearest
    if (!showtimesData.ok && theaterData.ok && theaterData.results && theaterData.results.length > 0) {
      var nearestName = theaterData.results[0].name;
      try {
        var stResp = await fetch(CONFIG.cineplexShowtimesApi + '?theatre=' + encodeURIComponent(nearestName) + stDateParam);
        showtimesData = await stResp.json();
      } catch(e) { showtimesData = { ok: false }; }
    }

    // Film events from cached events data
    var filmEvents = _getFilmEventsFromCache();

    // Render the combined card
    var html = _renderNowPlayingCard(nowPlayingData, theaterData, filmEvents, userLoc, timeFilter, showtimesData);

    // Replace loading message
    var el = document.getElementById('fte-ai-nowplaying-loading');
    if (el) {
      el.outerHTML = html;
    } else {
      addMessage('ai', html, false);
    }

    // Speak summary
    var defaultT = _getDefaultTheater();
    var primaryT = defaultT || (theaterData.ok && theaterData.results && theaterData.results.length > 0 ? theaterData.results[0].name : '');
    var spoken = '';
    if (nowPlayingData.ok && nowPlayingData.movies && nowPlayingData.movies.length > 0) {
      spoken = 'There are ' + nowPlayingData.movies.length + ' movies now playing. ';
      spoken += 'Top picks include ' + nowPlayingData.movies[0].title;
      if (nowPlayingData.movies.length > 1) spoken += ' and ' + nowPlayingData.movies[1].title;
      spoken += '. ';
    }
    if (primaryT) {
      spoken += 'Tap any movie poster to see showtimes at ' + primaryT + '. ';
    }
    if (timeFilter.label) {
      spoken += 'Click View Showtimes for exact times ' + timeFilter.label + '.';
    } else {
      spoken += 'Click View Showtimes to see what\'s playing now.';
    }
    speakText(spoken);

    // Set follow-up suggestion chips
    var followUps = [];
    if (!timeFilter.type) {
      followUps.push('Showtimes starting now');
      followUps.push('Showtimes tonight');
    } else if (timeFilter.type === 'now' || timeFilter.type === 'soon') {
      followUps.push('Showtimes tonight');
      followUps.push('Showtimes tomorrow');
    } else {
      followUps.push('Showtimes starting now');
    }
    if (!defaultT) {
      followUps.push('Set my default theater');
    } else {
      followUps.push('Change my default theater');
    }
    followUps.push('What else is happening tonight?');
    setPrompts(followUps);

    setStatus('Ready', '#64748b');
    state.processing = false;
    showStopBtn(false);
  }

  // ═══════════════════════════════════════════════════════════
  // HANDLERS: NAVIGATION
  // ═══════════════════════════════════════════════════════════
  function handleNavigation(lower, raw) {
    var destinations = {
      'events': '/',
      'home': '/',
      'main': '/',
      'stocks': '/findstocks/',
      'stock': '/findstocks/',
      'find stocks': '/findstocks/',
      'movies': '/MOVIESHOWS3/',
      'movie': '/MOVIESHOWS3/',
      'tv': '/MOVIESHOWS3/',
      'trailers': '/MOVIESHOWS3/',
      'creators': '/fc/#/guest',
      'streamers': '/fc/#/guest',
      'favcreators': '/fc/#/guest',
      'favorite creators': '/fc/#/guest',
      'fav creators': '/fc/#/guest',
      'vr': '/vr/',
      'vr experience': '/vr/',
      'virtual reality': '/vr/',
      'vr mobile': '/vr/mobile-index.html',
      'mobile vr': '/vr/mobile-index.html',
      'weather': '/vr/weather-zone.html',
      'mental health': '/MENTALHEALTHRESOURCES/',
      'wellness': '/MENTALHEALTHRESOURCES/',
      'accountability': '/fc/#/accountability',
      'dashboard': '/fc/#/accountability',
      'windows fixer': '/WINDOWSFIXER/',
      'boot fixer': '/WINDOWSFIXER/',
      'stats': '/stats/',
      'statistics': '/stats/',
      'movies v1': '/MOVIESHOWS/',
      'movies v2': '/movieshows2/',
      'movies v3': '/MOVIESHOWS3/',
      'tutorial': '/vr/tutorial/',
    };

    var urlMatch = raw.match(/(https?:\/\/[^\s]+)/i);
    if (urlMatch) {
      addMessage('ai', 'Opening <b>' + escapeHtml(urlMatch[1]) + '</b>...');
      setTimeout(function () { window.open(urlMatch[1], '_blank'); }, 500);
      setStatus('Ready', '#64748b');
      return;
    }

    var target = lower.replace(/^(go to|open|take me to|navigate to|show me)\s+/i, '').trim();
    for (var key in destinations) {
      if (target.indexOf(key) !== -1 || key.indexOf(target) !== -1) {
        addMessage('ai', 'Taking you to <b>' + escapeHtml(key) + '</b>...');
        setTimeout(function () { window.location.href = destinations[key]; }, 800);
        setStatus('Ready', '#64748b');
        return;
      }
    }

    addMessage('ai', 'I\'m not sure where to navigate. Try one of these:<br>' +
      '<div style="margin-top:6px;font-size:12px;">' +
      '\u2022 "Go to events" \u2014 Main events page<br>' +
      '\u2022 "Go to stocks" \u2014 Stock Ideas<br>' +
      '\u2022 "Go to movies" \u2014 Movies & TV<br>' +
      '\u2022 "Go to creators" \u2014 FavCreators<br>' +
      '\u2022 "Go to VR" \u2014 VR Experience<br>' +
      '\u2022 "Go to accountability" \u2014 Dashboard<br>' +
      '\u2022 "Go to wellness" \u2014 Mental Health<br>' +
      '\u2022 "Open https://..." \u2014 Any URL</div>');
    setStatus('Ready', '#64748b');
  }

  // ═══════════════════════════════════════════════════════════
  // HANDLERS: CONTEXT / TUTORIAL (conversational)
  // ═══════════════════════════════════════════════════════════
  function summarizeContext() {
    var section = detectSection();
    var sectionNames = {
      events: 'the Events page',
      stocks: 'the Stock Ideas app',
      movies: 'Movies & TV Shows V1',
      movies_v2: 'Movies & TV Shows V2',
      movies_v3: 'Movies & TV Shows V3',
      streamers: 'the FavCreators app',
      accountability: 'the Accountability Dashboard',
      weather: 'the Weather zone',
      wellness: 'the Mental Health Resources',
      vr: 'the VR Experience hub',
      stats: 'the Statistics dashboard',
      windowsfixer: 'the Windows Boot Fixer'
    };

    var name = sectionNames[section] || 'the main page';

    // Conversational: ask what they want
    var html = '<div class="fte-ai-summary">';
    html += '<b>\u{1F4CD} You are on ' + name + '</b>';
    switch (section) {
      case 'events':
        html += ' \u2014 Toronto\'s daily feed of things to do, dating events, concerts, festivals, and more.';
        break;
      case 'stocks':
        html += ' \u2014 daily AI-validated stock picks from 11+ algorithms.';
        // Check data freshness
        var stockDateInfo = getStockUpdateDate();
        if (stockDateInfo) {
          var daysDiff = Math.floor((new Date() - stockDateInfo.date) / 86400000);
          if (daysDiff === 0) {
            html += '<br><br>\u2705 <b>Picks are up to date</b> \u2014 last updated today (' + stockDateInfo.display + ').';
          } else if (daysDiff === 1) {
            html += '<br><br>\u{1F7E1} Picks were updated <b>yesterday</b> (' + stockDateInfo.display + '). Markets may have closed since.';
          } else if (daysDiff <= 3) {
            html += '<br><br>\u{1F7E0} Picks are <b>' + daysDiff + ' days old</b> (' + stockDateInfo.display + '). This may be normal over a weekend.';
          } else {
            html += '<br><br>\u{1F534} Picks are <b>' + daysDiff + ' days old</b> (' + stockDateInfo.display + '). Data may be stale \u2014 check if the pipeline ran.';
          }
        }
        break;
      case 'movies':
        html += ' \u2014 V1 with Toronto theater info, IMDb + Rotten Tomatoes ratings, and emoji reactions.';
        break;
      case 'movies_v2':
        html += ' \u2014 V2 with TMDB integration, genre filtering, and playlist export/import.';
        break;
      case 'movies_v3':
        html += ' \u2014 V3 with full browse & search, user accounts, likes, auto-scroll, and personal queue.';
        break;
      case 'streamers':
        html += ' \u2014 track your favorite creators across Twitch, TikTok, Kick & YouTube.';
        // Check login status for streamers section
        var stUser = window.__fc_logged_in_user__;
        if (!stUser) { try { var c = localStorage.getItem('fav_creators_auth_user'); if (c) { var p = JSON.parse(c); if (p && p.id) stUser = p; } } catch(_){} }
        if (stUser && stUser.id) {
          html += '<br><br>You\'re signed in as <b>' + (stUser.display_name || stUser.email || 'User') + '</b>. Live checks start automatically \u2014 I\'ll show you the progress here.';
        }
        break;
      case 'accountability':
        html += ' \u2014 set goals, track progress, and build consistent habits.';
        html += '<br><br>What would you like to do?';
        html += '</div>';
        addMessage('ai', html, false);
        // Now fetch real data and show a smart context-aware follow-up
        showAccountabilityGreeting();
        setPrompts(['Show my tasks', 'Give me a motivational push', 'Am I behind on anything?',
          'How do I set up a task?', 'My streaks', 'What\'s due today?']);
        setStatus('Ready', '#64748b');
        return; // early return — we handled prompts + message ourselves
      case 'wellness':
        html += ' \u2014 free wellness games, breathing exercises, grounding techniques, and 24/7 crisis support lines by country.';
        break;
      case 'windowsfixer':
        html += ' \u2014 comprehensive Windows recovery toolkit for BSOD, boot repair, and system restoration.';
        break;
      case 'stats':
        html += ' \u2014 statistics dashboard showing event source health and data metrics.';
        break;
      case 'vr':
        html += ' \u2014 immersive WebXR experience with Events Explorer, Movie Theater, Creators Lounge, Stocks Floor, and Weather Observatory.';
        break;
      default:
        html += '.';
    }
    html += '<br><br>What would you like to do?';
    html += '</div>';
    addMessage('ai', html, false);
    speakText('You are on ' + name + '. Would you like to know how to use it, or get specific information?');

    // Set flow + show choice prompts (section-aware)
    state.flow = 'awaiting_context_choice';
    state.flowData = { section: section };
    if (section === 'stocks') {
      setPrompts(['Give me today\'s stock picks', 'Explain what the algorithms each mean', 'How to use it', 'Something else']);
    } else {
      setPrompts(['How to use it', 'Give me event details', 'Explain all icons', 'Something else']);
    }
    setStatus('Ready', '#64748b');
  }

  function explainIcons() {
    var section = detectSection();
    var html = '<div class="fte-ai-summary">';
    html += '<b>\u{1F50D} Icon & Menu Guide</b><br><br>';

    html += '<b>Navigation Bar (\u2630 Quick Nav):</b><br>';
    html += '\u2022 \u{1F310} <b>Global Feed</b> \u2014 Main events page with all Toronto events<br>';
    html += '\u2022 \u2764\uFE0F <b>My Collection</b> \u2014 Your saved/hearted events<br>';
    html += '\u2022 \u{1F4E7} <b>Contact Support</b> \u2014 Email support<br>';
    html += '<br><b>NETWORK section:</b><br>';
    html += '\u2022 \u{1F6E0}\uFE0F <b>Windows Boot Fixer</b> \u2014 PC recovery toolkit<br>';
    html += '\u2022 \u{1F31F} <b>Mental Health</b> \u2014 Wellness games & crisis resources<br>';
    html += '\u2022 \u{1F4C8} <b>Find Stocks</b> \u2014 AI-validated stock picks<br>';
    html += '\u2022 \u{1F3AC} <b>Movies & TV</b> \u2014 Trailer browser (3 versions)<br>';
    html += '\u2022 \u2B50 <b>Favorite Creators</b> \u2014 Track streamers<br>';
    html += '\u2022 \u{1F48E} <b>FAVCREATORS</b> \u2014 Full creator dashboard<br>';
    html += '\u2022 \u{1F534} <b>Live status</b> \u2014 See who\'s streaming now<br>';
    html += '\u2022 \u{1F97D} <b>VR Experience</b> \u2014 Immersive WebXR (Desktop & Mobile)<br>';
    html += '\u2022 \u{1F3AF} <b>Accountability</b> \u2014 Goal & habit tracking<br>';
    html += '<br><b>Top bar:</b><br>';
    html += '\u2022 \u{1F512} <b>Sign In</b> \u2014 Login to save events and track creators<br>';
    html += '\u2022 \u2699\uFE0F <b>Settings</b> \u2014 Theme, layout, and filter options<br>';
    html += '\u2022 \u{1F916} <b>AI Assistant</b> \u2014 That\'s me!<br>';

    if (section === 'events') {
      html += '<br><b>Event Cards:</b><br>';
      html += '\u2022 \u2764\uFE0F <b>Heart</b> \u2014 Save event to your collection<br>';
      html += '\u2022 \u{1F4C5} <b>Date badge</b> \u2014 Event date and time<br>';
      html += '\u2022 \u{1F517} <b>Link</b> \u2014 Open event details/tickets<br>';
      html += '\u2022 \u{1F3F7}\uFE0F <b>Category tags</b> \u2014 Event categories<br>';
      html += '<br><b>Data Management:</b><br>';
      html += '\u2022 \u{1F4E6} <b>JSON</b> \u2014 Export events as JSON<br>';
      html += '\u2022 \u{1F4CA} <b>CSV</b> \u2014 Export as spreadsheet<br>';
      html += '\u2022 \u{1F4C5} <b>Calendar (ICS)</b> \u2014 Import to Google/Apple Calendar<br>';
      html += '\u2022 \u{1F4E5} <b>Import Collection</b> \u2014 Import saved events<br>';
    }

    html += '</div>';
    addMessage('ai', html, false);
    speakText('I\'ve listed all the icons and menu options. The navigation menu has sections for events, stocks, movies, creators, VR, and more.');
    setStatus('Ready', '#64748b');
  }

  function showHelp() {
    var html = '<div class="fte-ai-summary">';
    html += '<b>AI Assistant \u2014 Complete Command Guide</b><br><br>';

    html += '<b>Events & Activities:</b><br>';
    html += '\u2022 "What\'s happening this weekend?" / "Events tonight"<br>';
    html += '\u2022 "Good date ideas this weekend" / "Date night ideas"<br>';
    html += '\u2022 "Free events this week" / "Cheap things to do"<br>';
    html += '\u2022 "Live music tonight" / "Comedy shows this week"<br>';
    html += '\u2022 "Events near me today" / "Events at M5G 2H5"<br>';
    html += '\u2022 "Events in downtown" / "Events in the annex"<br>';
    html += '\u2022 "Family-friendly activities" / "Outdoor events"<br>';
    html += '\u2022 "Salsa dancing tonight" / "Yoga this weekend"<br>';
    html += '\u2022 "TIFF events" / "Nuit Blanche" / "Pride events"<br>';
    html += '\u2022 "Networking events this week" / "Tech meetups"<br>';

    html += '<br><b>Weather & Clothing:</b><br>';
    html += '\u2022 "Will it rain today?" / "Will it snow?"<br>';
    html += '\u2022 "Do I need a jacket?" / "What should I wear?"<br>';
    html += '\u2022 "Chance of rain this weekend" / "Any precipitation?"<br>';
    html += '\u2022 "7-day forecast" / "Weather tomorrow"<br>';
    html += '\u2022 "Is it nice outside?" / "How cold is it?"<br>';
    html += '\u2022 "Weather at M5G 2H5" / "Weather in Yorkville"<br>';
    html += '\u2022 "Should I bring an umbrella?" / "Do I need sunscreen?"<br>';

    html += '<br><b>Creators & Streamers:</b><br>';
    html += '\u2022 <b>"Refresh my creators"</b> \u2014 real-time live check across all platforms (may take 30-60s)<br>';
    html += '\u2022 "Who is live?" / "Anyone streaming right now?"<br>';
    html += '\u2022 "New content from creators" / "Latest posts this week"<br>';
    html += '\u2022 "New videos past 48 hours" / "Content past month"<br>';
    html += '\u2022 "Show my creator list" / "Who went live recently?"<br>';
    html += '\u2022 "Creator updates" / "Latest from my creators"<br>';

    html += '<br><b>Stocks & Investing:</b><br>';
    html += '\u2022 "Give me today\'s stock picks" / "Best growth stocks"<br>';
    html += '\u2022 "Explain what the algorithms each mean" / "What is CAN SLIM?"<br>';
    html += '\u2022 "Are these picks up to date?" / "Explain the risk levels"<br>';
    html += '\u2022 "Momentum picks today" / "Alpha Predator picks"<br>';

    html += '<br><b>Near Me / Find Places:</b> <span style="color:#94a3b8;font-size:0.85rem;">(type <b>/places</b> for the full guide!)</span><br>';
    html += '\u2022 "Coffee near me" / "Pizza near me open now" / "ATM near Eaton Centre"<br>';
    html += '\u2022 "Where is Almadina Bistro?" / "Is Tim Hortons open?"<br>';
    html += '\u2022 "Halal pizza open at midnight near Dundas" / "Vegan brunch spots"<br>';
    html += '\u2022 "I\'m hungry" / "I need a pharmacy" / "Where can I print something?"<br>';
    html += '\u2022 Quick: <b>/food</b> \u2022 <b>/open</b> \u2022 <b>/find</b> \u2022 <b>/nearby</b><br>';
    html += '\u2022 Filters: <b>/restrict:halal</b> \u2022 <b>/cuisine:italian</b> \u2022 <b>/open:late</b><br>';
    html += '\u2022 <b>/places</b> \u2014 full searchable guide with 100+ examples<br>';

    html += '<br><b>Movies & TV:</b><br>';
    html += '\u2022 "Queue Avatar trailers" / "Search a movie"<br>';
    html += '\u2022 "What should I watch?" / "Trending movies"<br>';
    html += '\u2022 "Horror movies" / "Romantic comedies"<br>';
    html += '\u2022 "New releases" / "Popular this week"<br>';

    html += '<br><b>Accountability & Tasks:</b><br>';
    html += '\u2022 "Show my tasks" / "Am I on track?"<br>';
    html += '\u2022 "What\'s due today?" / "Overdue tasks"<br>';
    html += '\u2022 "My streaks" / "Goal progress"<br>';

    html += '<br><b>Directions:</b><br>';
    html += '\u2022 "How to get to Eaton Centre from Union Station"<br>';
    html += '\u2022 "Directions to CN Tower" / "Walk to Kensington Market"<br>';
    html += '\u2022 "Transit from Dundas to Scarborough" / "How far is the ROM?"<br>';
    html += '\u2022 Quick: <b>/directions Eaton Centre</b><br>';

    html += '<br><b>Navigation:</b><br>';
    html += '\u2022 "Go to stocks" / "Open VR" / "Take me to movies"<br>';
    html += '\u2022 "Open FavCreators" / "Go to accountability"<br>';
    html += '\u2022 "Open https://..." \u2014 any URL<br>';

    html += '<br><b>Page Info & Guided Help:</b><br>';
    html += '\u2022 "Summarize current page" \u2014 guided walkthrough with choices<br>';
    html += '\u2022 "How to use this page" / "How does this work?"<br>';
    html += '\u2022 "Explain all icons" / "What are the menu options?"<br>';
    html += '\u2022 "Where am I?" / "What is this page?"<br>';
    html += '\u2022 "Who are you?" / "What can you do?"<br>';

    html += '<br><b>Tutorial Mode:</b><br>';
    html += '\u2022 "Enable tutorial mode" \u2014 guided intro on every section<br>';
    html += '\u2022 "Disable tutorial mode"<br>';

    html += '<br><b>Combine Requests:</b><br>';
    html += '\u2022 "Stock insights and also weather today"<br>';
    html += '\u2022 "Dating events this weekend along with weather forecast"<br>';
    html += '\u2022 "Who is live, also events tonight"<br>';

    html += '<br><b>Settings:</b><br>';
    html += '\u2022 "Turn off AI" / "Turn on AI" \u2014 persists for logged-in users<br>';
    html += '\u2022 "Mute AI" / "Unmute AI" \u2014 toggle voice responses<br>';
    html += '\u2022 "Hide AI button" / "Show AI button"<br>';

    html += '<br><b>Voice Control:</b><br>';
    html += '\u2022 Click the microphone button to talk<br>';
    html += '\u2022 Say <b>"STOP"</b> or <b>"SHUT UP"</b> to silence me<br>';
    html += '\u2022 I\'ll stop and let you know how to re-enable<br>';

    html += '<br><b>Quick Tips:</b><br>';
    html += '\u2022 "I\'m bored" / "Give me suggestions" \u2014 I\'ll recommend things<br>';
    html += '\u2022 "What\'s new?" / "What\'s trending?" \u2014 latest across all sections<br>';
    html += '\u2022 "What time is it?" / "What day is it?"<br>';
    html += '</div>';
    addMessage('ai', html, false);
    speakText('I can help with events, weather, creator live checks, stocks, movies, accountability tasks, navigation, and much more. Ask me anything, or tap one of the suggestions below!');
    setStatus('Ready', '#64748b');
  }

  // ═══════════════════════════════════════════════════════════
  // TUTORIAL / FIRST-TIME MODE
  // ═══════════════════════════════════════════════════════════
  function checkFirstVisit() {
    var section = detectSection();
    state.currentSection = section;
    var visited = load(CONFIG.visitedSectionsKey, {});
    var tutorialMode = load(CONFIG.tutorialModeKey, false);
    var isFirstEver = !load(CONFIG.firstTimeKey, false);

    if (isFirstEver) {
      store(CONFIG.firstTimeKey, true);
      addMessage('ai', '<b>Welcome to the AI Assistant!</b><br><br>' +
        'I\'m your free, voice-enabled assistant for everything on findtorontoevents.ca. Here\'s a taste of what I can do:<br><br>' +
        '\u2022 <b>"What\'s happening this weekend?"</b> \u2014 events by type, date, or location<br>' +
        '\u2022 <b>"Good date ideas tonight"</b> \u2014 creative event suggestions<br>' +
        '\u2022 <b>"Will it rain today?"</b> \u2014 weather + jacket recommendations<br>' +
        '\u2022 <b>"Refresh my creators"</b> \u2014 live check across Twitch, Kick, YouTube, TikTok<br>' +
        '\u2022 <b>"Top stock picks"</b> \u2014 AI-validated stock analysis<br>' +
        '\u2022 <b>"What should I watch?"</b> \u2014 movie and TV trailers<br>' +
        '\u2022 <b>"Show my tasks"</b> \u2014 accountability dashboard<br><br>' +
        'Click the mic button to talk, or type below. Say <b>"help"</b> for the full command list.');
      speakText('Welcome to the AI Assistant! I can help with events, weather, live creators, stocks, movies, and more. Ask me anything or say help for all commands.');
      visited[section] = true;
      store(CONFIG.visitedSectionsKey, visited);
      updatePrompts(section);
      return;
    }

    if (tutorialMode || !visited[section]) {
      visited[section] = true;
      store(CONFIG.visitedSectionsKey, visited);
      summarizeContext();
      return;
    }

    updatePrompts(section);
    if (state.chatHistory.length === 0) {
      addMessage('ai', 'Hey! \u{1F44B} How can I help you today?', false);
    }
  }

  function enableTutorialMode() {
    store(CONFIG.tutorialModeKey, true);
    store(CONFIG.visitedSectionsKey, {});
    state.tutorialMode = true;
    addMessage('ai', '<b>Tutorial mode enabled!</b> \u{1F4DA}<br><br>I\'ll give you a guided introduction each time you visit a new section. Navigate to any page and I\'ll explain everything!');
    setStatus('Tutorial ON', '#22c55e');
  }

  function disableTutorialMode() {
    store(CONFIG.tutorialModeKey, false);
    state.tutorialMode = false;
    addMessage('ai', 'Tutorial mode disabled. I\'ll still be here if you need help \u2014 just ask!');
    setStatus('Ready', '#64748b');
  }

  // ═══════════════════════════════════════════════════════════
  // AUTO-PROMPTS / CHIPS (enhanced)
  // ═══════════════════════════════════════════════════════════
  function setPrompts(promptsArr) {
    var container = document.getElementById('fte-ai-prompts');
    if (!container) return;
    container.innerHTML = '';
    for (var i = 0; i < promptsArr.length; i++) {
      var chip = document.createElement('button');
      chip.className = 'fte-ai-chip';
      chip.textContent = promptsArr[i];
      chip.setAttribute('data-prompt', promptsArr[i]);
      chip.addEventListener('click', function () {
        processUserInput(this.getAttribute('data-prompt'));
      });
      container.appendChild(chip);
    }
  }

  function updatePrompts(section) {
    var prompts = [];
    switch (section) {
      case 'events':
        prompts = [
          'What\'s happening tonight?', 'Events this weekend', 'Events near me',
          'Good date ideas this weekend', 'Free events this week', 'Live music tonight',
          'Comedy shows this week', 'Outdoor activities this weekend',
          'Will it rain today?', 'Refresh my creators', 'Summarize current page'
        ];
        break;
      case 'stocks':
        prompts = [
          'Give me today\'s stock picks', 'Explain what the algorithms each mean',
          'What is CAN SLIM?', 'What is Technical Momentum?',
          'What is Alpha Predator?', 'Best growth stocks',
          'Are these picks up to date?', 'Explain the risk levels',
          'Momentum picks today'
        ];
        break;
      case 'movies':
        prompts = [
          'Play Avatar trailer', 'Play Shrek 5', 'What movies are here?',
          'Search a movie', 'What should I watch?',
          'Go to V3 (full search)', 'Events this weekend', 'Turn off AI'
        ];
        break;
      case 'movies_v2':
        prompts = [
          'Play a trailer', 'Search a movie', 'What movies are here?',
          'What should I watch?', 'Go to V3 (full search)',
          'Events this weekend', 'Weather today', 'Turn off AI'
        ];
        break;
      case 'movies_v3':
        prompts = [
          'Search a movie', 'Find Avatar', 'Trending movies',
          'What should I watch?', 'My queue',
          'Go to events', 'Weather today', 'Turn off AI'
        ];
        break;
      case 'streamers':
        prompts = [
          'Refresh my creators', 'Who is live?', 'Who is live based on latest check?',
          'New content this week', 'New posts past 48 hours', 'Latest videos from creators',
          'Show my creator list', 'Events this weekend', 'Weather today'
        ];
        break;
      case 'accountability':
        prompts = [
          'Am I behind on anything?', 'What\'s due today?', 'Give me a motivational push',
          'Show my tasks', 'My streaks', 'How do I set up a task?',
          'Can I still catch up?', 'How to use it', 'Events this weekend'
        ];
        break;
      case 'wellness':
        prompts = [
          'What resources are here?', 'Crisis support lines', 'Breathing exercises',
          'Grounding techniques', '5-4-3-2-1 technique', 'Guided meditation',
          'Events this weekend', 'Weather today', 'Who is live?'
        ];
        break;
      case 'windowsfixer':
        prompts = [
          'How does this work?', 'Fix BSOD', 'Boot repair steps',
          'Recovery options', 'Safe mode guide', 'Windows won\'t start',
          'Events this weekend', 'Weather today', 'Go to events'
        ];
        break;
      case 'stats':
        prompts = [
          'What stats are tracked?', 'Event sources health', 'How many events total?',
          'System status', 'API health check', 'Events this weekend',
          'Weather today', 'Who is live?'
        ];
        break;
      case 'vr':
        prompts = [
          'How do I use VR?', 'Desktop controls', 'Quest 3 setup',
          'What zones are there?', 'Mobile VR controls',
          'Events this weekend', 'Weather today', 'Who is live?'
        ];
        break;
      case 'weather':
        prompts = [
          'Will it rain today?', 'Will it snow?', '7-day forecast',
          'Do I need a jacket?', 'What should I wear?', 'Chance of rain this weekend',
          'Events this weekend', 'Who is live?'
        ];
        break;
      default:
        prompts = [
          'What\'s happening this weekend?', 'Events near me tonight',
          'Will it rain today?', 'Top stock picks', 'Who is live?',
          'Refresh my creators', 'What should I watch?', 'Summarize current page'
        ];
    }
    setPrompts(prompts);
  }

  // ═══════════════════════════════════════════════════════════
  // INITIALIZATION — resilient to React hydration
  // ═══════════════════════════════════════════════════════════
  var _initDone = false;

  function ensureUI() {
    if (!document.getElementById('fte-ai-css')) {
      injectCSS();
    }
    if (!document.getElementById('fte-ai-btn')) {
      var section = detectSection();
      var isMovies = section === 'movies' || section === 'movies_v2' || section === 'movies_v3';
      var btn = document.createElement('button');
      btn.id = 'fte-ai-btn';
      btn.innerHTML = '<span style="pointer-events:none;font-size:20px">\u{1F916}</span><span class="fte-ai-label" style="pointer-events:none">AI</span>';
      btn.title = 'AI Assistant \u2014 Ask me anything';
      btn.setAttribute('aria-label', 'Open AI Assistant');
      btn.addEventListener('click', togglePanel);
      if (isMovies && state.hiddenOnMovies) btn.classList.add('hidden-mode');
      if (state.listening) btn.classList.add('listening');
      if (state.speaking) btn.classList.add('speaking');
      document.body.appendChild(btn);
    }
    if (!document.getElementById('fte-ai-panel')) {
      var panel = document.createElement('div');
      panel.id = 'fte-ai-panel';
      if (state.open) panel.classList.add('open');
      panel.innerHTML = [
        '<div id="fte-ai-header">',
        '  <h3><span>\u{1F916}</span> AI Assistant <span class="fte-ai-status" id="fte-ai-status">Ready</span></h3>',
        '  <div style="display:flex;align-items:center;gap:6px;">',
        '    <button id="fte-ai-stop-btn" title="Stop / Pause response">\u23F9 Stop</button>',
        '    <button class="fte-ai-close" id="fte-ai-close" title="Close">&times;</button>',
        '  </div>',
        '</div>',
        '<div id="fte-ai-messages"></div>',
        '<div id="fte-ai-prompts"></div>',
        '<div id="fte-ai-input-area">',
        '  <button class="fte-ai-icon-btn" id="fte-ai-mic" title="Click to talk"><span style="pointer-events:none">\u{1F3A4}</span></button>',
        '  <input type="text" id="fte-ai-input" placeholder="Ask me anything..." autocomplete="off" />',
        '  <button class="fte-ai-icon-btn send" id="fte-ai-send" title="Send"><span style="pointer-events:none">\u27A4</span></button>',
        '</div>'
      ].join('\n');
      document.body.appendChild(panel);
      var closeBtn = document.getElementById('fte-ai-close');
      var micBtn = document.getElementById('fte-ai-mic');
      var sendBtn = document.getElementById('fte-ai-send');
      var stopBtn = document.getElementById('fte-ai-stop-btn');
      var inputEl = document.getElementById('fte-ai-input');
      if (closeBtn) closeBtn.addEventListener('click', togglePanel);
      if (micBtn) micBtn.addEventListener('click', toggleMic);
      if (sendBtn) sendBtn.addEventListener('click', sendFromInput);
      if (stopBtn) stopBtn.addEventListener('click', cancelCurrentResponse);
      if (inputEl) inputEl.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') { e.preventDefault(); sendFromInput(); }
      });
      var msgContainer = document.getElementById('fte-ai-messages');
      if (msgContainer && state.chatHistory.length > 0) {
        for (var i = 0; i < state.chatHistory.length; i++) {
          var entry = state.chatHistory[i];
          var msg = document.createElement('div');
          msg.className = 'fte-ai-msg ' + entry.type;
          msg.innerHTML = entry.text;
          msgContainer.appendChild(msg);
        }
        msgContainer.scrollTop = msgContainer.scrollHeight;
      }
      updatePrompts(state.currentSection);
    }
  }

  function init() {
    // Check if AI is disabled (respect user preference)
    if (!state.aiEnabled) {
      console.log('[AI Assistant] Disabled by user preference. Use window.FTEAssistant.enable() to re-enable.');
      _initDone = true;
      // Still expose enable function
      window.FTEAssistant = {
        enable: function () {
          state.aiEnabled = true;
          store(CONFIG.aiEnabledKey, true);
          savePrefToDB('ai_enabled', true);
          injectCSS();
          createUI();
          setupRecognition();
          state.currentSection = detectSection();
          updatePrompts(state.currentSection);
          setInterval(ensureUI, 2000);
          showAssistantAgain();
          console.log('[AI Assistant] Re-enabled!');
        },
        open: function () { },
        close: function () { },
        ask: function () { },
        speak: function () { },
        stop: function () { }
      };
      return;
    }

    injectCSS();
    createUI();
    setupRecognition();
    state.currentSection = detectSection();
    updatePrompts(state.currentSection);
    _initDone = true;

    setInterval(ensureUI, 2000);
    setTimeout(ensureUI, 500);
    setTimeout(ensureUI, 1500);
    setTimeout(ensureUI, 3000);
    setTimeout(ensureUI, 5000);
    setTimeout(ensureUI, 8000);

    setTimeout(function () { loadEvents(); }, 2000);

    // Sync DB preferences for logged-in users (after a short delay to let FC auth populate)
    setTimeout(syncPrefsFromDB, 3000);
    setTimeout(syncPrefsFromDB, 8000);

    // ── LIVE CHECK PROGRESS TRACKING (FavCreators integration) ──
    // Listen for live check events from the React app and show progress in AI chat
    var _liveCheckMsgId = null;
    var _liveCheckLiveFound = [];
    var _liveCheckChecked = [];

    // ── Live history: track who went live across sessions (persists in sessionStorage) ──
    var _liveHistory = [];
    try {
      var stored = sessionStorage.getItem('fc_ai_live_history');
      if (stored) _liveHistory = JSON.parse(stored);
    } catch (e) { /* ignore */ }

    function addToLiveHistory(name, platform, timestamp) {
      _liveHistory.push({ name: name, platform: platform, time: timestamp || new Date().toISOString() });
      // Keep last 100 entries
      if (_liveHistory.length > 100) _liveHistory = _liveHistory.slice(-100);
      try { sessionStorage.setItem('fc_ai_live_history', JSON.stringify(_liveHistory)); } catch (e) { /* ignore */ }
    }

    function formatTime(isoStr) {
      try {
        var d = new Date(isoStr);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      } catch (e) { return ''; }
    }

    // ── Auto-check timer state ──
    var _autoCheckInterval = null;
    var _autoCheckLastTotal = 0;
    var _autoCheckPaused = false;

    function updateLiveCheckMsg(current, total, currentCreator, percent) {
      var el = document.getElementById('fte-ai-live-progress');
      if (!el) return;
      var pct = percent || Math.round((current / total) * 100);
      var liveHtml = '';
      if (_liveCheckLiveFound.length > 0) {
        liveHtml = '<div style="margin-top:6px;padding:6px 8px;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.2);border-radius:6px;font-size:0.8rem;">' +
          '<b style="color:#f87171;">\u{1F534} Live Now (' + _liveCheckLiveFound.length + '):</b> ' +
          _liveCheckLiveFound.map(function(l) {
            var ts = l.time ? ' <span style="color:#64748b;font-size:0.7rem;">' + formatTime(l.time) + '</span>' : '';
            return '<b>' + l.name + '</b> <span style="color:var(--text-muted);">(' + l.platform + ')</span>' + ts;
          }).join(', ') +
          '</div>';
      }
      var viewBtnHtml = '';
      if (_liveCheckChecked.length > 0 && current < total) {
        viewBtnHtml = '<div style="margin-top:6px;text-align:center;">' +
          '<button id="fte-ai-show-checked-btn" style="background:rgba(99,102,241,0.15);border:1px solid rgba(99,102,241,0.3);border-radius:6px;color:#a5b4fc;cursor:pointer;padding:4px 12px;font-size:0.75rem;">View ' + _liveCheckChecked.length + ' checked creators</button>' +
          '</div>';
      }
      el.innerHTML = '<div style="margin-bottom:4px;font-size:0.85rem;">' +
        '<b>Checking:</b> ' + currentCreator + '  <span style="color:var(--text-muted);">' + current + ' / ' + total + ' (' + pct + '%)</span>' +
        '</div>' +
        '<div style="height:6px;background:rgba(255,255,255,0.1);border-radius:3px;overflow:hidden;">' +
        '<div style="height:100%;width:' + pct + '%;background:linear-gradient(90deg,#6366f1,#818cf8);border-radius:3px;transition:width 0.3s ease;"></div>' +
        '</div>' +
        liveHtml + viewBtnHtml;
      // Bind show-checked button
      var showBtn = document.getElementById('fte-ai-show-checked-btn');
      if (showBtn) {
        showBtn.onclick = function() {
          showCheckedCreatorsList();
        };
      }
    }

    function showCheckedCreatorsList() {
      if (_liveCheckChecked.length === 0) return;
      var html = '<div class="fte-ai-summary"><b>Checked Creators (' + _liveCheckChecked.length + ')</b><br><br>';
      html += '<div style="max-height:200px;overflow-y:auto;font-size:0.82rem;">';
      for (var i = 0; i < _liveCheckChecked.length; i++) {
        var c = _liveCheckChecked[i];
        var color = c.isLive ? '#f87171' : 'var(--text-muted)';
        var badge = c.isLive ? ' <span style="color:#f87171;font-weight:600;">\u{1F534} LIVE</span>' : ' <span style="color:#64748b;">offline</span>';
        html += '<div style="padding:2px 0;color:' + color + ';">' + (i + 1) + '. <b>' + c.name + '</b>' + badge + '</div>';
      }
      html += '</div></div>';
      addMessage('ai', html, false);
    }

    window.addEventListener('fc-live-check-start', function(e) {
      if (detectSection() !== 'streamers') return;
      _liveCheckLiveFound = [];
      _liveCheckChecked = [];
      var total = e.detail && e.detail.total ? e.detail.total : '?';
      // Only add progress message if chat is open or we haven't shown one yet
      var existing = document.getElementById('fte-ai-live-progress');
      if (!existing) {
        var progressHtml = '<div class="fte-ai-summary">' +
          '<b>\u{1F4E1} Checking for live creators...</b><br>' +
          '<div id="fte-ai-live-progress" style="margin-top:8px;">' +
          '<div style="font-size:0.85rem;color:var(--text-muted);">Starting check for ' + total + ' creators...</div>' +
          '<div style="height:6px;background:rgba(255,255,255,0.1);border-radius:3px;overflow:hidden;margin-top:4px;">' +
          '<div style="height:100%;width:0%;background:linear-gradient(90deg,#6366f1,#818cf8);border-radius:3px;transition:width 0.3s ease;"></div>' +
          '</div>' +
          '<div style="margin-top:6px;font-size:0.75rem;color:#64748b;">This may take a while depending on how many creators you follow. Check back soon!</div>' +
          '</div></div>';
        addMessage('ai', progressHtml, false);
      }
    });

    window.addEventListener('fc-live-check-progress', function(e) {
      if (detectSection() !== 'streamers') return;
      var d = e.detail || {};
      // Track checked creator
      if (d.currentCreator && !_liveCheckChecked.some(function(c) { return c.name === d.currentCreator; })) {
        _liveCheckChecked.push({ name: d.currentCreator, isLive: false });
      }
      updateLiveCheckMsg(d.current, d.total, d.currentCreator, d.percent);
    });

    window.addEventListener('fc-live-found', function(e) {
      if (detectSection() !== 'streamers') return;
      var d = e.detail || {};
      var now = new Date().toISOString();
      var timeStr = formatTime(now);
      _liveCheckLiveFound.push({ name: d.name, platform: d.platform, time: now });

      // Record in live history (only newly-live creators)
      if (d.isNewlyLive !== false) {
        addToLiveHistory(d.name, d.platform, now);
      }

      // Also mark as live in checked list
      for (var i = 0; i < _liveCheckChecked.length; i++) {
        if (_liveCheckChecked[i].name === d.name) {
          _liveCheckChecked[i].isLive = true;
          break;
        }
      }
    });

    window.addEventListener('fc-live-check-complete', function(e) {
      if (detectSection() !== 'streamers') return;
      var d = e.detail || {};
      var completedAt = new Date();
      var timeStr = completedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      var el = document.getElementById('fte-ai-live-progress');
      if (el) {
        var liveHtml = '';
        if (d.liveCreators && d.liveCreators.length > 0) {
          liveHtml = '<div style="margin-top:8px;padding:8px 10px;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.2);border-radius:8px;">' +
            '<b style="color:#f87171;">\u{1F534} Live Now (' + d.liveCreators.length + '):</b><br>';
          for (var i = 0; i < d.liveCreators.length; i++) {
            var lc = d.liveCreators[i];
            // Find timestamp from _liveCheckLiveFound
            var foundTime = '';
            for (var j = 0; j < _liveCheckLiveFound.length; j++) {
              if (_liveCheckLiveFound[j].name === lc.name && _liveCheckLiveFound[j].time) {
                foundTime = ' <span style="color:#64748b;font-size:0.75rem;">detected ' + formatTime(_liveCheckLiveFound[j].time) + '</span>';
                break;
              }
            }
            liveHtml += '<div style="margin-top:4px;">\u2022 <b>' + lc.name + '</b> <span style="color:var(--text-muted);">(' + lc.platforms.join(', ') + ')</span>' + foundTime + '</div>';
          }
          liveHtml += '</div>';
        } else {
          liveHtml = '<div style="margin-top:6px;color:var(--text-muted);font-size:0.85rem;">No creators are live right now.</div>';
        }
        el.innerHTML = '<div style="font-size:0.85rem;color:#86efac;font-weight:600;">\u2705 Finished at ' + timeStr + '! Checked ' + d.total + ' creators.</div>' + liveHtml;
      }
      _liveCheckMsgId = null;

      // ── AUTO-CHECK: Start 5-min timer if < 200 creators ──
      _autoCheckLastTotal = d.total || 0;
      if (_autoCheckLastTotal > 0 && _autoCheckLastTotal < 200) {
        startAutoCheckTimer();
      }
    });

    // ── Auto-check timer functions ──
    function startAutoCheckTimer() {
      // Clear any existing timer
      if (_autoCheckInterval) clearInterval(_autoCheckInterval);
      _autoCheckPaused = false;

      _autoCheckInterval = setInterval(function() {
        // Pause when tab is hidden
        if (document.hidden) {
          _autoCheckPaused = true;
          return;
        }
        // If we were paused and tab is now visible, skip this tick (will fire next interval)
        if (_autoCheckPaused) {
          _autoCheckPaused = false;
          return;
        }
        // Only auto-check on the streamers section
        if (detectSection() !== 'streamers') return;

        console.log('[AI Assistant] Auto-check: requesting live status refresh');
        try {
          window.dispatchEvent(new CustomEvent('fc-auto-check-request'));
        } catch (err) {
          console.warn('[AI Assistant] Auto-check dispatch failed:', err);
        }
      }, 5 * 60 * 1000); // 5 minutes
    }

    function stopAutoCheckTimer() {
      if (_autoCheckInterval) {
        clearInterval(_autoCheckInterval);
        _autoCheckInterval = null;
      }
    }

    console.log('[AI Assistant] Initialized for section:', state.currentSection);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  window.addEventListener('load', function () {
    if (_initDone) ensureUI();
  });

  window.FTEAssistant = {
    open: function () { if (!state.open) togglePanel(); },
    close: function () { if (state.open) togglePanel(); },
    ask: processUserInput,
    speak: speakText,
    stop: stopSpeaking,
    _summarizeWorldEvents: _summarizeWorldEvents,
    _stopWorldSummary: _stopWorldSummary
  };

})();
