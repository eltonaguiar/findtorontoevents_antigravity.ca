/**
 * Blog Events Engine v1.0
 * Shared event fetching, filtering, rendering, and mega menu for blog100-149
 * Self-initializing — just include this script and call BlogEngine.init(config)
 */
(function() {
  'use strict';

  var EVENT_SOURCES = [
    '/next/events.json',
    '/events.json',
    '/data/events.json',
    'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents.ca/main/next/events.json'
  ];

  var allEvents = [];
  var filteredEvents = [];
  var currentCategory = 'all';
  var searchQuery = '';
  var currentPage = 0;
  var EVENTS_PER_PAGE = 12;

  /* ═══════════════════════════════════════════
     EVENT FETCHING
     ═══════════════════════════════════════════ */
  function fetchEvents(sourceIndex) {
    sourceIndex = sourceIndex || 0;
    if (sourceIndex >= EVENT_SOURCES.length) {
      renderNoEvents('Could not load events. Please try again later.');
      return;
    }
    var url = EVENT_SOURCES[sourceIndex];
    fetch(url)
      .then(function(r) {
        if (!r.ok) throw new Error('Status ' + r.status);
        return r.json();
      })
      .then(function(data) {
        var events = data.events || data;
        if (!Array.isArray(events) || events.length === 0) {
          throw new Error('No events');
        }
        allEvents = events;
        filterAndRender();
      })
      .catch(function() {
        fetchEvents(sourceIndex + 1);
      });
  }

  /* ═══════════════════════════════════════════
     FILTERING
     ═══════════════════════════════════════════ */
  function filterAndRender() {
    var now = new Date();
    now.setHours(0, 0, 0, 0);

    filteredEvents = allEvents.filter(function(ev) {
      // Date filter — only show today and future
      var evDate = new Date(ev.date || ev.startDate || ev.start_date);
      if (isNaN(evDate.getTime())) return true;
      var endDate = ev.end_date || ev.endDate;
      if (endDate) {
        var ed = new Date(endDate);
        if (!isNaN(ed.getTime()) && ed < now) return false;
      } else if (evDate < now) {
        return false;
      }

      // Category filter
      if (currentCategory !== 'all') {
        var cat = (ev.category || ev.type || '').toLowerCase();
        var title = (ev.title || ev.name || '').toLowerCase();
        var desc = (ev.description || '').toLowerCase();
        var combined = cat + ' ' + title + ' ' + desc;
        if (combined.indexOf(currentCategory.toLowerCase()) === -1) return false;
      }

      // Search filter
      if (searchQuery) {
        var q = searchQuery.toLowerCase();
        var haystack = ((ev.title || ev.name || '') + ' ' + (ev.description || '') + ' ' + (ev.location || ev.venue || '') + ' ' + (ev.category || '')).toLowerCase();
        if (haystack.indexOf(q) === -1) return false;
      }

      return true;
    });

    // Sort by date
    filteredEvents.sort(function(a, b) {
      var da = new Date(a.date || a.startDate || a.start_date || 0);
      var db = new Date(b.date || b.startDate || b.start_date || 0);
      return da - db;
    });

    currentPage = 0;
    renderEvents();
    renderPagination();
    updateEventCount();
  }

  /* ═══════════════════════════════════════════
     RENDERING
     ═══════════════════════════════════════════ */
  function renderEvents() {
    var container = document.getElementById('events-grid');
    if (!container) return;

    var start = currentPage * EVENTS_PER_PAGE;
    var pageEvents = filteredEvents.slice(start, start + EVENTS_PER_PAGE);

    if (pageEvents.length === 0) {
      renderNoEvents(searchQuery ? 'No events match "' + searchQuery + '"' : 'No upcoming events found');
      return;
    }

    var html = '';
    pageEvents.forEach(function(ev) {
      var title = ev.title || ev.name || 'Untitled Event';
      var date = formatDate(ev.date || ev.startDate || ev.start_date);
      var time = ev.time || ev.startTime || '';
      var location = ev.location || ev.venue || 'Toronto';
      var category = ev.category || ev.type || 'Event';
      var desc = ev.description || '';
      if (desc.length > 120) desc = desc.substring(0, 120) + '...';
      var link = ev.url || ev.link || '#';
      var imgUrl = ev.image || ev.imageUrl || ev.thumbnail || '';

      html += '<div class="event-card" data-category="' + escapeAttr(category) + '">';
      if (imgUrl) {
        html += '<div class="event-card-img"><img src="' + escapeAttr(imgUrl) + '" alt="' + escapeAttr(title) + '" loading="lazy" onerror="this.parentElement.style.display=\'none\'"></div>';
      }
      html += '<div class="event-card-body">';
      html += '<span class="event-card-tag">' + escapeHtml(category) + '</span>';
      html += '<h3 class="event-card-title">' + escapeHtml(title) + '</h3>';
      html += '<div class="event-card-meta">';
      html += '<span class="event-card-date">' + escapeHtml(date) + (time ? ' &middot; ' + escapeHtml(time) : '') + '</span>';
      html += '<span class="event-card-location">' + escapeHtml(location) + '</span>';
      html += '</div>';
      if (desc) html += '<p class="event-card-desc">' + escapeHtml(desc) + '</p>';
      if (link && link !== '#') html += '<a href="' + escapeAttr(link) + '" target="_blank" rel="noopener" class="event-card-link">View Details</a>';
      html += '</div></div>';
    });

    container.innerHTML = html;
  }

  function renderNoEvents(msg) {
    var container = document.getElementById('events-grid');
    if (!container) return;
    container.innerHTML = '<div class="no-events"><div class="no-events-icon">&#128197;</div><p>' + escapeHtml(msg) + '</p></div>';
  }

  function renderPagination() {
    var container = document.getElementById('events-pagination');
    if (!container) return;
    var totalPages = Math.ceil(filteredEvents.length / EVENTS_PER_PAGE);
    if (totalPages <= 1) { container.innerHTML = ''; return; }

    var html = '<div class="pagination">';
    if (currentPage > 0) html += '<button class="page-btn" data-page="' + (currentPage - 1) + '">&laquo; Prev</button>';

    for (var i = 0; i < totalPages; i++) {
      if (totalPages > 7 && Math.abs(i - currentPage) > 2 && i !== 0 && i !== totalPages - 1) {
        if (i === 1 || i === totalPages - 2) html += '<span class="page-dots">...</span>';
        continue;
      }
      html += '<button class="page-btn' + (i === currentPage ? ' active' : '') + '" data-page="' + i + '">' + (i + 1) + '</button>';
    }

    if (currentPage < totalPages - 1) html += '<button class="page-btn" data-page="' + (currentPage + 1) + '">Next &raquo;</button>';
    html += '</div>';
    container.innerHTML = html;

    container.querySelectorAll('.page-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        currentPage = parseInt(this.getAttribute('data-page'));
        renderEvents();
        renderPagination();
        document.getElementById('events-grid').scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });
  }

  function updateEventCount() {
    var el = document.getElementById('event-count');
    if (el) el.textContent = filteredEvents.length + ' event' + (filteredEvents.length !== 1 ? 's' : '') + ' found';
  }

  /* ═══════════════════════════════════════════
     CATEGORIES
     ═══════════════════════════════════════════ */
  function extractCategories() {
    var cats = {};
    allEvents.forEach(function(ev) {
      var c = ev.category || ev.type || 'Other';
      cats[c] = (cats[c] || 0) + 1;
    });
    return Object.keys(cats).sort();
  }

  function renderCategories() {
    var container = document.getElementById('category-filters');
    if (!container) return;
    var cats = extractCategories();

    var html = '<button class="cat-btn active" data-cat="all">All</button>';
    cats.forEach(function(c) {
      html += '<button class="cat-btn" data-cat="' + escapeAttr(c) + '">' + escapeHtml(c) + '</button>';
    });
    container.innerHTML = html;

    container.querySelectorAll('.cat-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        container.querySelectorAll('.cat-btn').forEach(function(b) { b.classList.remove('active'); });
        this.classList.add('active');
        currentCategory = this.getAttribute('data-cat');
        filterAndRender();
      });
    });
  }

  /* ═══════════════════════════════════════════
     SEARCH
     ═══════════════════════════════════════════ */
  function initSearch() {
    var input = document.getElementById('event-search');
    if (!input) return;
    var debounceTimer;
    input.addEventListener('input', function() {
      clearTimeout(debounceTimer);
      var val = this.value;
      debounceTimer = setTimeout(function() {
        searchQuery = val;
        filterAndRender();
      }, 300);
    });
  }

  /* ═══════════════════════════════════════════
     OTHER STUFF MEGA MENU
     ═══════════════════════════════════════════ */
  function createOtherStuffMenu() {
    // Overlay
    var overlay = document.createElement('div');
    overlay.className = 'os-overlay';
    overlay.id = 'os-overlay';
    document.body.appendChild(overlay);

    // Popup
    var popup = document.createElement('div');
    popup.className = 'os-popup';
    popup.id = 'os-popup';
    popup.innerHTML = '<div class="os-header"><h3>Other Stuff</h3><button class="os-close" id="os-close-btn">&times;</button></div>'
      + '<div class="os-body">'
      + osLink('/weather/', 'Toronto Weather', 'Real-time conditions & what to wear', '#00d4ff', true)
      + osLink('/affiliates/', 'Recommended Gear & Links', 'Products we trust & stand behind', '#fbbf24')
      + osLink('/updates/', 'Latest Updates', 'New features & improvements', '#34d399')
      + osLink('/news/', 'News Aggregator', 'Toronto & world news from 20+ sources', '#f87171')
      + osLink('/deals/', 'Deals & Freebies', '78 birthday freebies & Canadian deals', '#fbbf24')
      + '<div class="os-divider"></div>'
      + '<div class="os-section-title">Apps & Tools</div>'
      + osLink('/investments/', 'Investment Hub', 'Portfolios, analytics & tools', '#22c55e')
      + osLink('/findstocks/', 'Stock Ideas', 'AI picks, updated daily', '#f59e0b')
      + osLink('/findstocks/portfolio2/dashboard.html', 'Portfolio Dashboard', 'Track your positions & equity curve', '#6366f1')
      + osLink('/findstocks/portfolio2/dividends.html', 'Dividends & Earnings', 'Dividend calendar & earnings tracker', '#22c55e')
      + osLink('/findcryptopairs/', 'Crypto Scanner', 'Crypto pairs analysis', '#f59e0b')
      + osLink('/findforex2/', 'Forex Scanner', 'Currency pairs analysis', '#06b6d4')
      + osLink('/live-monitor/goldmine-dashboard.html', 'Goldmine Dashboard', 'Multi-dimensional scoring', '#6366f1')
      + osLink('/live-monitor/sports-betting.html', 'Sports Bet Finder', 'NHL, NBA, NFL odds & picks', '#4ade80')
      + '<div class="os-divider"></div>'
      + '<div class="os-section-title">Entertainment</div>'
      + osLink('/MOVIESHOWS/', 'Now Showing', 'Cineplex showtimes & ratings', '#f59e0b')
      + osLink('/movieshows2/', 'The Film Vault', '4,000+ titles & playlists', '#fbbf24')
      + osLink('/MOVIESHOWS3/', 'Binge Mode', 'TikTok-style auto-scroll trailers', '#fb923c')
      + osLink('/fc/#/guest', 'Fav Creators', 'Track streamers across platforms', '#ec4899')
      + '<div class="os-divider"></div>'
      + '<div class="os-section-title">More</div>'
      + osLink('/MENTALHEALTHRESOURCES/', 'Mental Health', 'Wellness tools & crisis support', '#10b981')
      + osLink('/WINDOWSFIXER/', 'Windows Boot Fixer', 'Fix BSOD & boot issues', '#667eea')
      + osLink('/vr/', 'VR Experience', 'VR worlds for desktop & Quest', '#a855f7')
      + osLink('/vr/game-arena/', 'Game Arena', 'Browser-based game prototypes', '#a855f7')
      + osLink('/gotjob/', 'GotJob', 'Your job finding hub', '#06b6d4')
      + osLink('/blog/', 'Blog', 'Toronto event articles & guides', '#818cf8')
      + '</div>'
      + '<div class="os-footer"><a href="/" class="os-back-btn">&larr; Back to Events</a></div>';
    document.body.appendChild(popup);

    // Toggle
    overlay.addEventListener('click', closeMenu);
    document.getElementById('os-close-btn').addEventListener('click', closeMenu);

    // Trigger button
    var triggerBtn = document.getElementById('other-stuff-btn');
    if (triggerBtn) {
      triggerBtn.addEventListener('click', function(e) {
        e.preventDefault();
        openMenu();
      });
    }
  }

  function osLink(href, title, desc, color, highlight) {
    return '<a href="' + href + '" class="os-link' + (highlight ? ' os-highlight' : '') + '" target="_blank">'
      + '<span class="os-link-title" style="color:' + color + '">' + title + '</span>'
      + '<span class="os-link-desc">' + desc + '</span>'
      + '<span class="os-link-arrow">&rsaquo;</span></a>';
  }

  function openMenu() {
    document.getElementById('os-overlay').classList.add('open');
    document.getElementById('os-popup').classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function closeMenu() {
    document.getElementById('os-overlay').classList.remove('open');
    document.getElementById('os-popup').classList.remove('open');
    document.body.style.overflow = '';
  }

  /* ═══════════════════════════════════════════
     NAVIGATION ARROWS (between blog pages)
     ═══════════════════════════════════════════ */
  function createNavArrows(pageNum) {
    var nav = document.createElement('div');
    nav.className = 'blog-nav-arrows';
    var prevNum = pageNum - 1;
    var nextNum = pageNum + 1;

    var html = '';
    if (prevNum >= 100) {
      html += '<a href="blog' + prevNum + '.html" class="blog-nav-arrow prev" title="Previous Theme">&larr; Theme ' + prevNum + '</a>';
    }
    html += '<span class="blog-nav-current">Theme ' + pageNum + ' of 149</span>';
    if (nextNum <= 149) {
      html += '<a href="blog' + nextNum + '.html" class="blog-nav-arrow next" title="Next Theme">Theme ' + nextNum + ' &rarr;</a>';
    }
    nav.innerHTML = html;
    document.body.appendChild(nav);
  }

  /* ═══════════════════════════════════════════
     UTILITIES
     ═══════════════════════════════════════════ */
  function formatDate(dateStr) {
    if (!dateStr) return '';
    var d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    var days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    return days[d.getDay()] + ', ' + months[d.getMonth()] + ' ' + d.getDate() + ', ' + d.getFullYear();
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function escapeAttr(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;');
  }

  /* ═══════════════════════════════════════════
     INIT
     ═══════════════════════════════════════════ */
  window.BlogEngine = {
    init: function(config) {
      config = config || {};
      EVENTS_PER_PAGE = config.eventsPerPage || 12;

      // Wait for DOM
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() { bootstrap(config); });
      } else {
        bootstrap(config);
      }
    }
  };

  function bootstrap(config) {
    fetchEvents(0);
    initSearch();
    createOtherStuffMenu();
    if (config.pageNum) createNavArrows(config.pageNum);

    // Re-render categories once events load
    var checkCats = setInterval(function() {
      if (allEvents.length > 0) {
        renderCategories();
        clearInterval(checkCats);
      }
    }, 500);
  }

})();
