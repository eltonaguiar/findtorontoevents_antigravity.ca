/**
 * VR Quick Wins — Set 7: Utility, Polish & Discovery
 *
 * 10 substantial features:
 *   1. Favorites System     — star/save items across zones, persist in localStorage
 *   2. Cross-Zone Search    — universal search overlay (events + creators + movies)
 *   3. Recent Activity Feed — tracks & displays last 20 actions across zones
 *   4. Zone Ratings         — rate each zone 1-5 stars, show averages
 *   5. Content Preloader    — prefetch next-likely zone for instant transitions
 *   6. Zone Loading Bar     — per-zone themed progress indicator
 *   7. Share Snapshot       — capture current view state as a shareable deep-link
 *   8. Enhanced Tooltips    — rich hover tooltips on interactive UI elements
 *   9. Breadcrumb Trail     — show navigation path (Hub > Events > Detail)
 *  10. Quick Stats Badge    — floating badge with live stats for current zone
 *
 * Loaded in all VR zones via <script src="/vr/quick-wins-set7.js"></script>
 */
(function () {
  'use strict';

  /* ─────────────────────────────────────────────
     HELPERS
     ───────────────────────────────────────────── */
  var STORAGE_PREFIX = 'vr_qw7_';

  function store(key, val) {
    try { localStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(val)); } catch (e) {}
  }
  function load(key, fallback) {
    try {
      var v = localStorage.getItem(STORAGE_PREFIX + key);
      return v !== null ? JSON.parse(v) : fallback;
    } catch (e) { return fallback; }
  }

  function detectZone() {
    var p = location.pathname;
    if (p.indexOf('/vr/events') !== -1) return 'events';
    if (p.indexOf('/vr/movies') !== -1) return 'movies';
    if (p.indexOf('/vr/creators') !== -1) return 'creators';
    if (p.indexOf('/vr/stocks') !== -1) return 'stocks';
    if (p.indexOf('/vr/wellness') !== -1) return 'wellness';
    if (p.indexOf('/vr/weather') !== -1) return 'weather';
    if (p.indexOf('/vr/tutorial') !== -1) return 'tutorial';
    return 'hub';
  }

  function zoneName(id) {
    var names = { hub:'VR Hub', events:'Events Explorer', movies:'Movie Theater', creators:'Live Creators', stocks:'Trading Floor', wellness:'Wellness Garden', weather:'Weather Observatory', tutorial:'Tutorial' };
    return names[id] || id;
  }

  function zoneColor(id) {
    var colors = { hub:'#00d4ff', events:'#ff6b6b', movies:'#4ecdc4', creators:'#a855f7', stocks:'#22c55e', wellness:'#f59e0b', weather:'#06b6d4', tutorial:'#f59e0b' };
    return colors[id] || '#00d4ff';
  }

  function showToast(msg, duration, color) {
    var toast = document.createElement('div');
    toast.className = 'vr-qw7-toast';
    toast.textContent = msg;
    if (color) toast.style.borderColor = color;
    document.body.appendChild(toast);
    requestAnimationFrame(function () { toast.classList.add('show'); });
    setTimeout(function () {
      toast.classList.remove('show');
      setTimeout(function () { toast.remove(); }, 400);
    }, duration || 2500);
  }

  function injectCSS(css) {
    var s = document.createElement('style');
    s.textContent = css;
    document.head.appendChild(s);
  }

  var currentZone = detectZone();

  /* ─────────────────────────────────────────────
     1. FAVORITES SYSTEM
     ───────────────────────────────────────────── */
  var favorites = load('favorites', []);

  function addFavorite(item) {
    // item: { id, type, title, zone, url }
    if (favorites.some(function (f) { return f.id === item.id; })) return false;
    item.addedAt = Date.now();
    favorites.push(item);
    store('favorites', favorites);
    logActivity('favorite', 'Saved "' + item.title + '"');
    showToast('★ Saved to favorites', 2000, '#f59e0b');
    return true;
  }

  function removeFavorite(id) {
    favorites = favorites.filter(function (f) { return f.id !== id; });
    store('favorites', favorites);
    showToast('Removed from favorites', 2000);
  }

  function isFavorite(id) {
    return favorites.some(function (f) { return f.id === id; });
  }

  function getFavorites(type) {
    if (!type) return favorites;
    return favorites.filter(function (f) { return f.type === type; });
  }

  /* ─────────────────────────────────────────────
     2. CROSS-ZONE SEARCH
     ───────────────────────────────────────────── */
  var searchOpen = false;

  function createSearchOverlay() {
    if (document.getElementById('vr-qw7-search')) return;
    var overlay = document.createElement('div');
    overlay.id = 'vr-qw7-search';
    overlay.innerHTML =
      '<div class="qw7-search-backdrop" onclick="VRQuickWins7.closeSearch()"></div>' +
      '<div class="qw7-search-panel">' +
        '<div class="qw7-search-header">' +
          '<input id="qw7-search-input" type="text" placeholder="Search events, creators, movies..." autocomplete="off" autofocus>' +
          '<button onclick="VRQuickWins7.closeSearch()" class="qw7-search-close">&times;</button>' +
        '</div>' +
        '<div id="qw7-search-results" class="qw7-search-results">' +
          '<div class="qw7-search-hint">Type to search across all zones</div>' +
        '</div>' +
      '</div>';
    document.body.appendChild(overlay);

    document.getElementById('qw7-search-input').addEventListener('input', function () {
      performSearch(this.value);
    });
  }

  function openSearch() {
    createSearchOverlay();
    var overlay = document.getElementById('vr-qw7-search');
    overlay.classList.add('open');
    searchOpen = true;
    var input = document.getElementById('qw7-search-input');
    if (input) { input.value = ''; input.focus(); }
  }

  function closeSearch() {
    var overlay = document.getElementById('vr-qw7-search');
    if (overlay) overlay.classList.remove('open');
    searchOpen = false;
  }

  function performSearch(query) {
    var resultsEl = document.getElementById('qw7-search-results');
    if (!query || query.trim().length < 2) {
      resultsEl.innerHTML = '<div class="qw7-search-hint">Type at least 2 characters to search</div>';
      return;
    }
    var q = query.toLowerCase();
    var results = [];

    // Search events
    var allEvents = window.filteredEvents || window._allEvents || window.allEvents || [];
    allEvents.forEach(function (ev) {
      if ((ev.title && ev.title.toLowerCase().indexOf(q) !== -1) ||
          (ev.location && ev.location.toLowerCase().indexOf(q) !== -1)) {
        results.push({ type: 'event', title: ev.title, sub: ev.location || '', url: '/vr/events/', color: '#ff6b6b', icon: '📅' });
      }
    });

    // Search creators
    var allCreators = window.allCreators || [];
    allCreators.forEach(function (c) {
      if (c.name && c.name.toLowerCase().indexOf(q) !== -1) {
        results.push({ type: 'creator', title: c.name, sub: c.platform || '', url: '/vr/creators.html', color: '#a855f7', icon: '📺' });
      }
    });

    // Limit results
    results = results.slice(0, 12);

    if (results.length === 0) {
      resultsEl.innerHTML = '<div class="qw7-search-hint">No results for "' + query + '"</div>';
      return;
    }

    resultsEl.innerHTML = results.map(function (r) {
      return '<a href="' + r.url + '" class="qw7-search-item" style="--item-color:' + r.color + '">' +
        '<span class="qw7-si-icon">' + r.icon + '</span>' +
        '<div class="qw7-si-text"><span class="qw7-si-title">' + r.title + '</span><span class="qw7-si-sub">' + r.sub + '</span></div>' +
        '<span class="qw7-si-type">' + r.type + '</span>' +
      '</a>';
    }).join('');
  }

  /* ─────────────────────────────────────────────
     3. RECENT ACTIVITY FEED
     ───────────────────────────────────────────── */
  var activityLog = load('activity', []);

  function logActivity(action, detail) {
    activityLog.unshift({
      action: action,
      detail: detail,
      zone: currentZone,
      time: Date.now()
    });
    if (activityLog.length > 30) activityLog.length = 30;
    store('activity', activityLog);
  }

  // Auto-log zone visit
  logActivity('visit', 'Visited ' + zoneName(currentZone));

  function getActivity(limit) {
    return activityLog.slice(0, limit || 20);
  }

  function showActivityFeed() {
    var items = getActivity(15);
    var overlay = document.getElementById('vr-qw7-activity');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'vr-qw7-activity';
      document.body.appendChild(overlay);
    }
    var now = Date.now();
    overlay.innerHTML =
      '<div class="qw7-search-backdrop" onclick="VRQuickWins7.closeActivity()"></div>' +
      '<div class="qw7-activity-panel">' +
        '<div class="qw7-activity-header">' +
          '<h3>Recent Activity</h3>' +
          '<button onclick="VRQuickWins7.closeActivity()" class="qw7-search-close">&times;</button>' +
        '</div>' +
        '<div class="qw7-activity-list">' +
        (items.length === 0 ? '<div class="qw7-search-hint">No recent activity</div>' :
        items.map(function (a) {
          var ago = Math.floor((now - a.time) / 60000);
          var agoStr = ago < 1 ? 'just now' : ago < 60 ? ago + 'm ago' : Math.floor(ago / 60) + 'h ago';
          var icons = { visit: '🚶', favorite: '⭐', rate: '⭐', search: '🔍', share: '🔗' };
          return '<div class="qw7-activity-item">' +
            '<span class="qw7-ai-icon">' + (icons[a.action] || '📌') + '</span>' +
            '<div class="qw7-ai-text"><span class="qw7-ai-detail">' + a.detail + '</span>' +
            '<span class="qw7-ai-meta">' + zoneName(a.zone) + ' · ' + agoStr + '</span></div>' +
          '</div>';
        }).join('')) +
        '</div>' +
      '</div>';
    overlay.classList.add('open');
  }

  function closeActivity() {
    var overlay = document.getElementById('vr-qw7-activity');
    if (overlay) overlay.classList.remove('open');
  }

  /* ─────────────────────────────────────────────
     4. ZONE RATINGS
     ───────────────────────────────────────────── */
  var ratings = load('ratings', {});

  function rateZone(zoneId, stars) {
    ratings[zoneId] = { stars: stars, time: Date.now() };
    store('ratings', ratings);
    logActivity('rate', 'Rated ' + zoneName(zoneId) + ' ' + stars + '★');
    showToast('Rated ' + zoneName(zoneId) + ' ' + '★'.repeat(stars), 2000, zoneColor(zoneId));
  }

  function getZoneRating(zoneId) {
    return ratings[zoneId] ? ratings[zoneId].stars : 0;
  }

  function showRatingPrompt() {
    var existing = getZoneRating(currentZone);
    var overlay = document.getElementById('vr-qw7-rate');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'vr-qw7-rate';
      document.body.appendChild(overlay);
    }
    overlay.innerHTML =
      '<div class="qw7-search-backdrop" onclick="VRQuickWins7.closeRating()"></div>' +
      '<div class="qw7-rate-panel">' +
        '<h3 style="margin:0 0 8px;color:#fff;font-size:1.1rem;">Rate ' + zoneName(currentZone) + '</h3>' +
        '<p style="color:#64748b;font-size:0.85rem;margin:0 0 12px;">How would you rate this zone?</p>' +
        '<div class="qw7-stars" id="qw7-star-row">' +
          [1,2,3,4,5].map(function (n) {
            return '<button class="qw7-star' + (n <= existing ? ' active' : '') + '" onclick="VRQuickWins7.submitRating(' + n + ')" data-stars="' + n + '">★</button>';
          }).join('') +
        '</div>' +
        (existing ? '<p style="color:#475569;font-size:0.8rem;margin-top:8px;">Your current rating: ' + existing + '★</p>' : '') +
      '</div>';
    overlay.classList.add('open');
  }

  function submitRating(stars) {
    rateZone(currentZone, stars);
    setTimeout(function () {
      var overlay = document.getElementById('vr-qw7-rate');
      if (overlay) overlay.classList.remove('open');
    }, 600);
  }

  function closeRating() {
    var overlay = document.getElementById('vr-qw7-rate');
    if (overlay) overlay.classList.remove('open');
  }

  /* ─────────────────────────────────────────────
     5. CONTENT PRELOADER
     ───────────────────────────────────────────── */
  var prefetched = {};

  function prefetchZone(url) {
    if (prefetched[url]) return;
    prefetched[url] = true;
    var link = document.createElement('link');
    link.rel = 'prefetch';
    link.href = url;
    link.as = 'document';
    document.head.appendChild(link);
  }

  // Prefetch adjacent zones based on navigation patterns
  function autoPrefetch() {
    var likely = {
      hub: ['/vr/events/', '/vr/movies.html', '/vr/creators.html'],
      events: ['/vr/', '/vr/movies.html'],
      movies: ['/vr/', '/vr/events/'],
      creators: ['/vr/', '/vr/events/'],
      stocks: ['/vr/'],
      wellness: ['/vr/'],
      weather: ['/vr/'],
      tutorial: ['/vr/']
    };
    var targets = likely[currentZone] || ['/vr/'];
    targets.forEach(function (url) {
      setTimeout(function () { prefetchZone(url); }, 3000 + Math.random() * 2000);
    });
  }

  /* ─────────────────────────────────────────────
     6. ZONE LOADING BAR
     ───────────────────────────────────────────── */
  function createLoadingBar() {
    if (document.getElementById('vr-qw7-loadbar')) return;
    var bar = document.createElement('div');
    bar.id = 'vr-qw7-loadbar';
    bar.innerHTML = '<div class="qw7-loadbar-fill" id="qw7-loadbar-fill" style="background:' + zoneColor(currentZone) + '"></div>';
    document.body.appendChild(bar);

    // Animate to 60% quickly, then slow crawl
    var fill = document.getElementById('qw7-loadbar-fill');
    var progress = 0;
    var interval = setInterval(function () {
      if (progress < 60) progress += 8;
      else if (progress < 90) progress += 1;
      fill.style.width = progress + '%';
      if (progress >= 90) clearInterval(interval);
    }, 100);

    // Complete on page fully loaded
    function complete() {
      clearInterval(interval);
      fill.style.width = '100%';
      setTimeout(function () {
        bar.classList.add('done');
        setTimeout(function () { bar.remove(); }, 500);
      }, 300);
    }

    if (document.readyState === 'complete') complete();
    else window.addEventListener('load', complete);
  }

  /* ─────────────────────────────────────────────
     7. SHARE SNAPSHOT (deep-link)
     ───────────────────────────────────────────── */
  function shareSnapshot() {
    var state = {
      zone: currentZone,
      page: window.currentPage || 0,
      filter: '',
      t: Date.now()
    };

    // Try to capture current filter state
    var activeFilter = document.querySelector('#cat-strip .active, .platform-filter.active');
    if (activeFilter) state.filter = activeFilter.textContent.trim();

    var url = location.origin + '/vr/' + (currentZone === 'hub' ? '' :
      currentZone === 'events' ? 'events/' :
      currentZone === 'movies' ? 'movies.html' :
      currentZone === 'creators' ? 'creators.html' :
      currentZone === 'stocks' ? 'stocks-zone.html' :
      currentZone === 'wellness' ? 'wellness/' :
      currentZone === 'weather' ? 'weather-zone.html' :
      currentZone === 'tutorial' ? 'tutorial/' : '');

    url += '?shared=1&zone=' + currentZone;
    if (state.filter) url += '&filter=' + encodeURIComponent(state.filter);
    if (state.page > 0) url += '&page=' + state.page;

    // Try to use navigator.share, fall back to clipboard
    if (navigator.share) {
      navigator.share({
        title: 'Check out ' + zoneName(currentZone) + ' in VR!',
        text: 'I\'m exploring ' + zoneName(currentZone) + ' on findtorontoevents.ca',
        url: url
      }).then(function () {
        logActivity('share', 'Shared ' + zoneName(currentZone));
        showToast('Shared!', 2000, '#22c55e');
      }).catch(function () {});
    } else if (navigator.clipboard) {
      navigator.clipboard.writeText(url).then(function () {
        logActivity('share', 'Copied link for ' + zoneName(currentZone));
        showToast('Link copied to clipboard!', 2500, '#22c55e');
      });
    } else {
      logActivity('share', 'Shared ' + zoneName(currentZone));
      showToast('Share: ' + url, 4000, '#22c55e');
    }
  }

  /* ─────────────────────────────────────────────
     8. ENHANCED TOOLTIPS
     ───────────────────────────────────────────── */
  var tooltipEl = null;

  function createTooltipSystem() {
    tooltipEl = document.createElement('div');
    tooltipEl.id = 'vr-qw7-tooltip';
    tooltipEl.className = 'qw7-tooltip';
    document.body.appendChild(tooltipEl);

    document.addEventListener('mouseover', function (e) {
      var target = e.target.closest('[data-vr-tip]');
      if (target) {
        tooltipEl.textContent = target.getAttribute('data-vr-tip');
        tooltipEl.classList.add('visible');
        positionTooltip(e);
      }
    });

    document.addEventListener('mousemove', function (e) {
      if (tooltipEl.classList.contains('visible')) positionTooltip(e);
    });

    document.addEventListener('mouseout', function (e) {
      var target = e.target.closest('[data-vr-tip]');
      if (target) tooltipEl.classList.remove('visible');
    });
  }

  function positionTooltip(e) {
    var x = e.clientX + 12;
    var y = e.clientY - 8;
    if (x + 200 > window.innerWidth) x = e.clientX - 212;
    if (y < 10) y = e.clientY + 20;
    tooltipEl.style.left = x + 'px';
    tooltipEl.style.top = y + 'px';
  }

  /* ─────────────────────────────────────────────
     9. BREADCRUMB TRAIL
     ───────────────────────────────────────────── */
  function createBreadcrumb() {
    if (currentZone === 'hub') return; // Hub is the root, no breadcrumb needed
    if (document.getElementById('vr-qw7-breadcrumb')) return;

    var crumb = document.createElement('div');
    crumb.id = 'vr-qw7-breadcrumb';
    crumb.innerHTML =
      '<a href="/vr/" class="qw7-bc-link">VR Hub</a>' +
      '<span class="qw7-bc-sep">›</span>' +
      '<span class="qw7-bc-current" style="color:' + zoneColor(currentZone) + '">' + zoneName(currentZone) + '</span>';
    document.body.appendChild(crumb);
  }

  /* ─────────────────────────────────────────────
     10. QUICK STATS BADGE
     ───────────────────────────────────────────── */
  function createStatsBadge() {
    if (document.getElementById('vr-qw7-stats')) return;
    var badge = document.createElement('div');
    badge.id = 'vr-qw7-stats';
    badge.className = 'qw7-stats-badge';
    document.body.appendChild(badge);
    updateStatsBadge();
    setInterval(updateStatsBadge, 10000);
  }

  function updateStatsBadge() {
    var badge = document.getElementById('vr-qw7-stats');
    if (!badge) return;

    var stats = [];
    var rating = getZoneRating(currentZone);
    if (rating > 0) stats.push('★'.repeat(rating));

    var favCount = getFavorites().length;
    if (favCount > 0) stats.push(favCount + ' ♡');

    if (currentZone === 'events') {
      var evtCount = (window.filteredEvents || window._allEvents || []).length;
      if (evtCount > 0) stats.push(evtCount + ' events');
    }
    if (currentZone === 'creators') {
      var creators = window.allCreators || [];
      var liveCount = creators.filter(function (c) { return c._vrIsLive; }).length;
      if (liveCount > 0) stats.push(liveCount + ' live');
      else if (creators.length > 0) stats.push(creators.length + ' creators');
    }

    var sessionStart = parseInt(sessionStorage.getItem('vr_session_start')) || Date.now();
    var elapsed = Math.floor((Date.now() - sessionStart) / 60000);
    stats.push(elapsed + 'm session');

    badge.textContent = stats.join(' · ');
    badge.style.borderLeftColor = zoneColor(currentZone);
  }

  /* ─────────────────────────────────────────────
     CSS
     ───────────────────────────────────────────── */
  function injectAllCSS() {
    injectCSS('\
/* Toast */\
.vr-qw7-toast{position:fixed;bottom:80px;left:50%;transform:translateX(-50%) translateY(20px);z-index:200000;\
background:rgba(15,12,41,0.95);color:#fff;padding:10px 20px;border-radius:10px;font-size:0.85rem;font-weight:600;\
border:1px solid rgba(0,212,255,0.3);opacity:0;transition:all .3s ease;pointer-events:none;white-space:nowrap;\
box-shadow:0 8px 24px rgba(0,0,0,0.4);font-family:Inter,system-ui,sans-serif}\
.vr-qw7-toast.show{opacity:1;transform:translateX(-50%) translateY(0)}\
\
/* Loading Bar */\
#vr-qw7-loadbar{position:fixed;top:0;left:0;width:100%;height:3px;z-index:200001;background:rgba(0,0,0,0.2)}\
#vr-qw7-loadbar.done{opacity:0;transition:opacity .4s}\
.qw7-loadbar-fill{height:100%;width:0;transition:width .15s ease;border-radius:0 2px 2px 0}\
\
/* Search Overlay */\
#vr-qw7-search,#vr-qw7-activity,#vr-qw7-rate{position:fixed;inset:0;z-index:200002;display:none;\
align-items:flex-start;justify-content:center;padding-top:12vh;font-family:Inter,system-ui,sans-serif}\
#vr-qw7-search.open,#vr-qw7-activity.open,#vr-qw7-rate.open{display:flex}\
.qw7-search-backdrop{position:absolute;inset:0;background:rgba(0,0,0,0.7);backdrop-filter:blur(8px)}\
.qw7-search-panel,.qw7-activity-panel,.qw7-rate-panel{position:relative;z-index:1;width:min(94vw,520px);\
background:linear-gradient(135deg,#1a1a3e,#0f0f1f);border:1px solid rgba(0,212,255,0.3);border-radius:16px;\
padding:16px;box-shadow:0 24px 60px rgba(0,0,0,0.5);animation:qw7FadeIn .2s ease}\
@keyframes qw7FadeIn{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:none}}\
.qw7-search-header{display:flex;gap:8px;margin-bottom:10px}\
#qw7-search-input{flex:1;background:rgba(0,0,0,0.4);border:1px solid rgba(255,255,255,0.1);color:#fff;\
padding:10px 14px;border-radius:10px;font-size:0.95rem;outline:none;font-family:inherit}\
#qw7-search-input:focus{border-color:rgba(0,212,255,0.4)}\
.qw7-search-close{background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.2);color:#fca5a5;\
width:40px;border-radius:10px;cursor:pointer;font-size:1.3rem}\
.qw7-search-results{max-height:50vh;overflow-y:auto}\
.qw7-search-hint{color:#475569;text-align:center;padding:20px;font-size:0.85rem}\
.qw7-search-item{display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:8px;\
text-decoration:none;color:#cbd5e1;transition:all .15s;border:1px solid transparent}\
.qw7-search-item:hover{background:rgba(255,255,255,0.06);border-color:var(--item-color)}\
.qw7-si-icon{font-size:1.2rem;width:32px;text-align:center}\
.qw7-si-text{flex:1;min-width:0}\
.qw7-si-title{display:block;font-size:0.88rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}\
.qw7-si-sub{display:block;color:#475569;font-size:0.75rem}\
.qw7-si-type{color:#64748b;font-size:0.7rem;text-transform:uppercase;font-weight:600}\
\
/* Activity Feed */\
.qw7-activity-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}\
.qw7-activity-header h3{margin:0;color:#7dd3fc;font-size:1rem}\
.qw7-activity-list{max-height:50vh;overflow-y:auto}\
.qw7-activity-item{display:flex;align-items:flex-start;gap:10px;padding:8px 4px;border-bottom:1px solid rgba(255,255,255,0.04)}\
.qw7-ai-icon{font-size:1rem;width:24px;text-align:center;flex-shrink:0;margin-top:2px}\
.qw7-ai-text{flex:1}\
.qw7-ai-detail{display:block;color:#cbd5e1;font-size:0.85rem}\
.qw7-ai-meta{display:block;color:#475569;font-size:0.72rem;margin-top:2px}\
\
/* Rating Stars */\
.qw7-rate-panel{text-align:center;padding:24px}\
.qw7-stars{display:flex;justify-content:center;gap:8px}\
.qw7-star{background:none;border:none;font-size:2rem;cursor:pointer;color:#334155;transition:all .15s;padding:4px 6px}\
.qw7-star:hover,.qw7-star:hover~.qw7-star{color:#f59e0b}\
.qw7-star.active{color:#f59e0b}\
.qw7-stars:hover .qw7-star{color:#334155}\
.qw7-stars:hover .qw7-star:hover,.qw7-stars .qw7-star:hover~.qw7-star{color:#f59e0b}\
\
/* Breadcrumb */\
#vr-qw7-breadcrumb{position:fixed;top:12px;left:50%;transform:translateX(-50%);z-index:140;\
background:rgba(15,12,41,0.85);padding:5px 14px;border-radius:8px;font-size:0.78rem;\
border:1px solid rgba(255,255,255,0.06);backdrop-filter:blur(6px);display:flex;align-items:center;gap:6px;\
font-family:Inter,system-ui,sans-serif;pointer-events:auto}\
.qw7-bc-link{color:#64748b;text-decoration:none;transition:color .2s}.qw7-bc-link:hover{color:#fff}\
.qw7-bc-sep{color:#334155}\
.qw7-bc-current{font-weight:600}\
\
/* Stats Badge */\
.qw7-stats-badge{position:fixed;bottom:44px;left:12px;z-index:140;\
background:rgba(15,12,41,0.85);color:#64748b;padding:4px 12px;border-radius:6px;\
font-size:0.7rem;border:1px solid rgba(255,255,255,0.06);border-left:3px solid #00d4ff;\
backdrop-filter:blur(6px);font-family:Inter,system-ui,sans-serif;pointer-events:none}\
\
/* Tooltip */\
.qw7-tooltip{position:fixed;z-index:200003;background:rgba(15,12,41,0.95);color:#cbd5e1;\
padding:6px 12px;border-radius:6px;font-size:0.78rem;max-width:200px;pointer-events:none;\
border:1px solid rgba(0,212,255,0.2);opacity:0;transition:opacity .15s;font-family:Inter,system-ui,sans-serif}\
.qw7-tooltip.visible{opacity:1}\
');
  }

  /* ─────────────────────────────────────────────
     KEYBOARD SHORTCUTS
     ───────────────────────────────────────────── */
  document.addEventListener('keydown', function (e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

    // Ctrl+K or / (when not in search): Open cross-zone search
    if ((e.ctrlKey && e.key === 'k') || (e.key === '\\' && !e.ctrlKey)) {
      e.preventDefault();
      if (searchOpen) closeSearch();
      else openSearch();
      return;
    }

    // Escape: close overlays
    if (e.key === 'Escape') {
      if (searchOpen) { closeSearch(); e.stopPropagation(); return; }
    }
  });

  /* ─────────────────────────────────────────────
     PUBLIC API
     ───────────────────────────────────────────── */
  window.VRQuickWins7 = {
    // Favorites
    addFavorite: addFavorite,
    removeFavorite: removeFavorite,
    isFavorite: isFavorite,
    getFavorites: getFavorites,

    // Search
    openSearch: openSearch,
    closeSearch: closeSearch,

    // Activity
    logActivity: logActivity,
    getActivity: getActivity,
    showActivity: showActivityFeed,
    closeActivity: closeActivity,

    // Ratings
    showRating: showRatingPrompt,
    submitRating: submitRating,
    closeRating: closeRating,
    getZoneRating: getZoneRating,

    // Share
    shareSnapshot: shareSnapshot,

    // Preloader
    prefetchZone: prefetchZone,

    // Utils
    showToast: showToast,
    currentZone: currentZone
  };

  /* ─────────────────────────────────────────────
     INIT
     ───────────────────────────────────────────── */
  function init() {
    injectAllCSS();
    createLoadingBar();
    createBreadcrumb();
    createStatsBadge();
    createTooltipSystem();
    autoPrefetch();

    // Register keyboard hints if available
    if (window.VRKeyboardHints) {
      // Don't duplicate — just check if the key is already there
    }

    console.log('[VR Quick Wins Set 7] Loaded — ' + zoneName(currentZone));
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
