/**
 * stock-nav.js — Shared injectable navigation for all stock/trading pages.
 * Add <script src="/findstocks/portfolio2/stock-nav.js"></script> before </body>.
 *
 * Groups: Top Tools | Stocks | Multi-Asset | More (collapsed on desktop)
 */
(function() {
  var NAV_GROUPS = [
    {
      label: 'Top Tools',
      links: [
        { text: 'Consolidated', href: '/findstocks/portfolio2/consolidated.html', glow: true },
        { text: 'Smart Money', href: '/live-monitor/smart-money.html', glow: true },
        { text: 'Goldmine', href: '/live-monitor/goldmine-dashboard.html', glow: true },
        { text: 'L vs O', href: '/live-monitor/algo-performance.html', gold: true },
        { text: 'Live Monitor', href: '/live-monitor/live-monitor.html' }
      ]
    },
    {
      label: 'Stocks',
      links: [
        { text: 'Picks', href: '/findstocks/portfolio2/picks.html' },
        { text: 'Leaderboard', href: '/findstocks/portfolio2/leaderboard.html' },
        { text: 'Stock Intel', href: '/findstocks/portfolio2/stock-intel.html' },
        { text: 'Dividends', href: '/findstocks/portfolio2/dividends.html' }
      ]
    },
    {
      label: 'Multi-Asset',
      links: [
        { text: 'Crypto', href: '/findcryptopairs/winners.html' },
        { text: 'Forex', href: '/findforex2/portfolio/' },
        { text: 'Mutual Funds', href: '/findmutualfunds2/portfolio2/' },
        { text: 'Sports', href: '/live-monitor/sports-betting.html' }
      ]
    }
  ];

  var MORE_LINKS = [
    { text: 'Hub', href: '/findstocks/portfolio2/hub.html' },
    { text: 'Dashboard', href: '/findstocks/portfolio2/dashboard.html' },
    { text: 'Horizon Picks', href: '/findstocks/portfolio2/horizon-picks.html' },
    { text: 'Penny Stocks', href: '/findstocks/portfolio2/penny-stocks.html' },
    { text: 'Stock Profile', href: '/findstocks/portfolio2/stock-profile.html' },
    { text: 'DayTrader Sim', href: '/findstocks/portfolio2/daytrader-sim.html' },
    { text: 'Learning Lab', href: '/findstocks/portfolio2/learning-lab.html' },
    { text: 'Scanner', href: '/live-monitor/opportunity-scanner.html' },
    { text: 'Edge Dash', href: '/live-monitor/edge-dashboard.html' },
    { text: 'Patterns', href: '/live-monitor/winning-patterns.html' },
    { text: 'Health Alerts', href: '/live-monitor/goldmine-alerts.html' },
    { text: 'Multi-Dim', href: '/live-monitor/multi-dimensional.html' },
    { text: 'Capital Eff', href: '/live-monitor/capital-efficiency.html' },
    { text: 'Backtests', href: '/findstocks/portfolio2/backtest-results.html' },
    { text: 'All Tools', href: '/findstocks/tools.html' }
  ];

  // Detect active page
  var path = window.location.pathname;
  function isActive(href) {
    if (path === href) return true;
    // Match index pages (e.g. /findstocks/portfolio2/stats/ matches /findstocks/portfolio2/stats/index.html)
    if (href.charAt(href.length - 1) === '/' && (path === href + 'index.html' || path === href.slice(0, -1))) return true;
    if (path.charAt(path.length - 1) === '/' && path + 'index.html' === href) return true;
    return false;
  }

  // Check if any More link is active (to auto-expand on that page)
  var moreHasActive = false;
  for (var m = 0; m < MORE_LINKS.length; m++) {
    if (isActive(MORE_LINKS[m].href)) { moreHasActive = true; break; }
  }

  // Build CSS
  var style = document.createElement('style');
  style.textContent = [
    '#stock-nav-bar{position:sticky;top:0;z-index:9999;background:#0d0d20;border-bottom:1px solid #2a2a4a;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;font-size:13px;user-select:none}',
    '#stock-nav-inner{max-width:1400px;margin:0 auto;display:flex;align-items:center;padding:0 12px;min-height:40px;flex-wrap:wrap}',
    '#stock-nav-brand{color:#6366f1;font-weight:700;font-size:14px;margin-right:16px;white-space:nowrap;text-decoration:none}',
    '#stock-nav-brand:hover{color:#818cf8;text-decoration:none}',
    '.sn-group{display:flex;align-items:center;margin-right:6px}',
    '.sn-group-label{color:#555578;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;margin-right:4px;padding:6px 0}',
    '.sn-sep{width:1px;height:20px;background:#2a2a4a;margin:0 8px}',
    '.sn-link{color:#8888aa;padding:6px 7px;border-radius:6px;text-decoration:none;white-space:nowrap;transition:color 0.15s,background 0.15s}',
    '.sn-link:hover{color:#e0e0f0;background:rgba(99,102,241,0.12);text-decoration:none}',
    '.sn-link.active{color:#6366f1;background:rgba(99,102,241,0.15);font-weight:600}',
    '.sn-link.sn-glow{color:#22d3ee;text-shadow:0 0 6px rgba(34,211,238,0.4);font-weight:600;animation:sn-glow-pulse 3s ease-in-out infinite}',
    '.sn-link.sn-glow:hover{color:#fff;background:rgba(34,211,238,0.15);text-shadow:0 0 10px rgba(34,211,238,0.6)}',
    '.sn-link.sn-glow::after{content:"LIVE";font-size:7px;font-weight:800;letter-spacing:0.5px;background:#22d3ee;color:#0a0e1a;padding:1px 3px;border-radius:3px;margin-left:3px;vertical-align:super;line-height:1}',
    '@keyframes sn-glow-pulse{0%,100%{text-shadow:0 0 6px rgba(34,211,238,0.4)}50%{text-shadow:0 0 12px rgba(34,211,238,0.7),0 0 20px rgba(34,211,238,0.3)}}',
    '.sn-link.sn-gold{color:#ffd700;text-shadow:0 0 8px rgba(255,215,0,0.5);font-weight:700;border:1px solid rgba(255,215,0,0.4);background:rgba(255,215,0,0.08);animation:sn-gold-pulse 2.5s ease-in-out infinite}',
    '.sn-link.sn-gold:hover{color:#fff;background:rgba(255,215,0,0.18);text-shadow:0 0 14px rgba(255,215,0,0.7);border-color:rgba(255,215,0,0.6)}',
    '.sn-link.sn-gold::after{content:"#1";font-size:7px;font-weight:800;letter-spacing:0.5px;background:linear-gradient(135deg,#ffd700,#f59e0b);color:#0a0e1a;padding:1px 4px;border-radius:3px;margin-left:3px;vertical-align:super;line-height:1}',
    '@keyframes sn-gold-pulse{0%,100%{text-shadow:0 0 8px rgba(255,215,0,0.5);border-color:rgba(255,215,0,0.4)}50%{text-shadow:0 0 16px rgba(255,215,0,0.8),0 0 24px rgba(255,215,0,0.3);border-color:rgba(255,215,0,0.7)}}',
    '#stock-nav-toggle{display:none;background:none;border:1px solid #2a2a4a;color:#8888aa;padding:6px 10px;border-radius:6px;cursor:pointer;font-size:16px;margin-left:auto;line-height:1}',
    '#stock-nav-toggle:hover{color:#e0e0f0;border-color:#4a4a6a}',
    '#stock-nav-links{display:flex;align-items:center;flex-wrap:wrap;flex:1}',
    /* More toggle button */
    '.sn-more-toggle{color:#8888aa;padding:6px 7px;border-radius:6px;white-space:nowrap;cursor:pointer;transition:color 0.15s,background 0.15s;background:none;border:none;font-family:inherit;font-size:11px;text-transform:uppercase;letter-spacing:0.5px}',
    '.sn-more-toggle:hover{color:#e0e0f0;background:rgba(99,102,241,0.12)}',
    '.sn-more-toggle.sn-more-open{color:#6366f1}',
    /* More links container — collapsed by default on desktop */
    '.sn-more-links{display:none;width:100%;padding:4px 0 2px;flex-wrap:wrap;align-items:center;border-top:1px solid #1a1a3a;margin-top:4px}',
    '.sn-more-links.sn-more-visible{display:flex}',
    '@media(max-width:900px){',
    '  #stock-nav-toggle{display:block}',
    '  #stock-nav-links{display:none;width:100%;flex-direction:column;align-items:flex-start;padding:8px 0}',
    '  #stock-nav-links.open{display:flex}',
    '  .sn-group{flex-wrap:wrap;width:100%;margin:2px 0}',
    '  .sn-group-label{width:100%;padding:6px 7px 2px;font-size:10px}',
    '  .sn-sep{display:none}',
    '  .sn-link{padding:5px 10px;font-size:13px}',
    '  .sn-more-toggle{display:none}',
    '  .sn-more-links{display:flex;border-top:none;margin-top:0}',
    '}'
  ].join('\n');
  document.head.appendChild(style);

  // Build nav HTML
  var nav = document.createElement('nav');
  nav.id = 'stock-nav-bar';

  var inner = document.createElement('div');
  inner.id = 'stock-nav-inner';

  var brand = document.createElement('a');
  brand.id = 'stock-nav-brand';
  brand.href = '/findstocks/';
  brand.textContent = 'FTE Invest';
  inner.appendChild(brand);

  var toggle = document.createElement('button');
  toggle.id = 'stock-nav-toggle';
  toggle.innerHTML = '&#9776;';
  toggle.setAttribute('aria-label', 'Toggle navigation');
  inner.appendChild(toggle);

  var linksContainer = document.createElement('div');
  linksContainer.id = 'stock-nav-links';

  // Render the 3 main groups
  for (var g = 0; g < NAV_GROUPS.length; g++) {
    if (g > 0) {
      var sep = document.createElement('span');
      sep.className = 'sn-sep';
      linksContainer.appendChild(sep);
    }
    var group = document.createElement('span');
    group.className = 'sn-group';

    var glabel = document.createElement('span');
    glabel.className = 'sn-group-label';
    glabel.textContent = NAV_GROUPS[g].label;
    group.appendChild(glabel);

    var links = NAV_GROUPS[g].links;
    for (var i = 0; i < links.length; i++) {
      var a = document.createElement('a');
      a.className = 'sn-link' + (isActive(links[i].href) ? ' active' : '') + (links[i].gold ? ' sn-gold' : (links[i].glow ? ' sn-glow' : ''));
      a.href = links[i].href;
      a.textContent = links[i].text;
      if (links[i].gold) a.title = '#1 Pick — Only system with positive forward-facing returns (63.6% WR, +11.92% P\u0026L)';
      else if (links[i].glow) a.title = 'Real forward-looking performance data (not backtested)';
      group.appendChild(a);
    }
    linksContainer.appendChild(group);
  }

  // More toggle button (separator + button, inline with main groups)
  var moreSep = document.createElement('span');
  moreSep.className = 'sn-sep';
  linksContainer.appendChild(moreSep);

  var moreBtn = document.createElement('button');
  moreBtn.className = 'sn-more-toggle';
  moreBtn.textContent = moreHasActive ? 'More \u25C2' : 'More \u25B8';
  if (moreHasActive) moreBtn.classList.add('sn-more-open');
  linksContainer.appendChild(moreBtn);

  // More links container (full-width row beneath main groups)
  var moreContainer = document.createElement('div');
  moreContainer.className = 'sn-more-links' + (moreHasActive ? ' sn-more-visible' : '');

  var moreGroup = document.createElement('span');
  moreGroup.className = 'sn-group';
  moreGroup.style.cssText = 'flex-wrap:wrap';

  var moreLabel = document.createElement('span');
  moreLabel.className = 'sn-group-label';
  moreLabel.textContent = 'More';
  moreGroup.appendChild(moreLabel);

  for (var j = 0; j < MORE_LINKS.length; j++) {
    var ma = document.createElement('a');
    ma.className = 'sn-link' + (isActive(MORE_LINKS[j].href) ? ' active' : '');
    ma.href = MORE_LINKS[j].href;
    ma.textContent = MORE_LINKS[j].text;
    moreGroup.appendChild(ma);
  }
  moreContainer.appendChild(moreGroup);
  linksContainer.appendChild(moreContainer);

  inner.appendChild(linksContainer);
  nav.appendChild(inner);

  // Insert at very top of body
  document.body.insertBefore(nav, document.body.firstChild);

  // Toggle handler — mobile hamburger
  toggle.addEventListener('click', function() {
    linksContainer.classList.toggle('open');
  });

  // Toggle handler — More section (desktop only)
  moreBtn.addEventListener('click', function() {
    var isOpen = moreContainer.classList.toggle('sn-more-visible');
    moreBtn.classList.toggle('sn-more-open', isOpen);
    moreBtn.textContent = isOpen ? 'More \u25C2' : 'More \u25B8';
  });

  // Close mobile menu on link click
  linksContainer.addEventListener('click', function(e) {
    if (e.target.tagName === 'A') {
      linksContainer.classList.remove('open');
    }
  });

  // Goldmine failure alert banner — inject if active alerts exist
  setTimeout(function() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/live-monitor/api/goldmine_tracker.php?action=alerts');
    xhr.timeout = 5000;
    xhr.onload = function() {
      if (xhr.status === 200) {
        try {
          var data = JSON.parse(xhr.responseText);
          if (data.ok && data.active_count > 0) {
            var critical = 0;
            for (var i = 0; i < data.alerts.length; i++) {
              if (data.alerts[i].severity === 'critical') critical++;
            }
            var banner = document.createElement('div');
            banner.style.cssText = 'background:linear-gradient(90deg,#dc2626,#b91c1c);color:white;text-align:center;padding:8px 16px;font-weight:600;font-size:13px;font-family:system-ui,sans-serif;cursor:pointer;animation:gm-pulse 2s infinite';
            var label = critical > 0 ? 'CRITICAL' : 'WARNING';
            banner.innerHTML = '\u26a0\ufe0f ACTION REQUIRED: ' + data.active_count + ' system(s) underperforming (' + label + '). <a href="/live-monitor/goldmine-alerts.html" style="color:#fde68a;text-decoration:underline;margin-left:8px">View Details \u2192</a>';
            banner.onclick = function() { window.location.href = '/live-monitor/goldmine-alerts.html'; };
            var pulseStyle = document.createElement('style');
            pulseStyle.textContent = '@keyframes gm-pulse{0%,100%{opacity:1}50%{opacity:0.85}}';
            document.head.appendChild(pulseStyle);
            nav.parentNode.insertBefore(banner, nav.nextSibling);
          }
        } catch(e) {}
      }
    };
    xhr.onerror = function() {};
    xhr.send();
  }, 1500);
})();
