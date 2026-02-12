/**
 * stock-nav.js — Shared injectable navigation for all stock/trading pages.
 * Add <script src="/findstocks/portfolio2/stock-nav.js"></script> before </body>.
 */
(function() {
  var NAV_GROUPS = [
    {
      label: 'Portfolio',
      links: [
        { text: 'Hub', href: '/findstocks/portfolio2/hub.html' },
        { text: 'Picks', href: '/findstocks/portfolio2/picks.html' },
        { text: 'Consolidated', href: '/findstocks/portfolio2/consolidated.html' },
        { text: 'Leaderboard', href: '/findstocks/portfolio2/leaderboard.html' },
        { text: 'Dashboard', href: '/findstocks/portfolio2/dashboard.html' },
        { text: 'Horizon Picks', href: '/findstocks/portfolio2/horizon-picks.html' },
        { text: 'Dividends', href: '/findstocks/portfolio2/dividends.html' },
        { text: 'Penny Stocks', href: '/findstocks/portfolio2/penny-stocks.html' }
      ]
    },
    {
      label: 'Analysis',
      links: [
        { text: 'Algo Study', href: '/findstocks/portfolio2/algo-study.html' },
        { text: 'Stock Intel', href: '/findstocks/portfolio2/stock-intel.html' },
        { text: 'Learning Lab', href: '/findstocks/portfolio2/learning-lab.html' },
        { text: 'Learning Dash', href: '/findstocks/portfolio2/learning-dashboard.html' },
        { text: 'Smart Learning', href: '/findstocks/portfolio2/smart-learning.html' },
        { text: 'Stats', href: '/findstocks/portfolio2/stats/' }
      ]
    },
    {
      label: 'Live Trading',
      links: [
        { text: 'Live Monitor', href: '/live-monitor/live-monitor.html' },
        { text: 'Scanner', href: '/live-monitor/opportunity-scanner.html' },
        { text: 'Edge Dash', href: '/live-monitor/edge-dashboard.html' },
        { text: 'Patterns', href: '/live-monitor/winning-patterns.html' },
        { text: 'Hour Learn', href: '/live-monitor/hour-learning.html' },
        { text: 'DayTrader Sim', href: '/findstocks/portfolio2/daytrader-sim.html' },
        { text: 'L vs O', href: '/live-monitor/algo-performance.html' }
      ]
    },
    {
      label: 'Cross-Asset',
      links: [
        { text: 'Crypto', href: '/findcryptopairs/portfolio/' },
        { text: 'Forex', href: '/findforex2/portfolio/' },
        { text: 'Global Dash', href: '/findstocks2_global/' },
        { text: 'Stock Profile', href: '/findstocks/portfolio2/stock-profile.html' }
      ]
    },
    {
      label: 'Goldmines \u00b7 Claude',
      links: [
        { text: 'Goldmine Checker', href: '/live-monitor/goldmine-dashboard.html' },
        { text: 'Health Alerts', href: '/live-monitor/goldmine-alerts.html' },
        { text: 'Smart Money', href: '/live-monitor/smart-money.html' },
        { text: 'Capital Efficiency', href: '/live-monitor/capital-efficiency.html' },
        { text: 'Multi-Dim', href: '/live-monitor/multi-dimensional.html' }
      ]
    }
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
    '#stock-nav-toggle{display:none;background:none;border:1px solid #2a2a4a;color:#8888aa;padding:6px 10px;border-radius:6px;cursor:pointer;font-size:16px;margin-left:auto;line-height:1}',
    '#stock-nav-toggle:hover{color:#e0e0f0;border-color:#4a4a6a}',
    '#stock-nav-links{display:flex;align-items:center;flex-wrap:wrap;flex:1}',
    '@media(max-width:900px){',
    '  #stock-nav-toggle{display:block}',
    '  #stock-nav-links{display:none;width:100%;flex-direction:column;align-items:flex-start;padding:8px 0}',
    '  #stock-nav-links.open{display:flex}',
    '  .sn-group{flex-wrap:wrap;width:100%;margin:2px 0}',
    '  .sn-group-label{width:100%;padding:6px 7px 2px;font-size:10px}',
    '  .sn-sep{display:none}',
    '  .sn-link{padding:5px 10px;font-size:13px}',
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
  brand.href = '/findstocks/portfolio2/hub.html';
  brand.textContent = 'FTE Invest';
  inner.appendChild(brand);

  var toggle = document.createElement('button');
  toggle.id = 'stock-nav-toggle';
  toggle.innerHTML = '&#9776;';
  toggle.setAttribute('aria-label', 'Toggle navigation');
  inner.appendChild(toggle);

  var linksContainer = document.createElement('div');
  linksContainer.id = 'stock-nav-links';

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
      a.className = 'sn-link' + (isActive(links[i].href) ? ' active' : '');
      a.href = links[i].href;
      a.textContent = links[i].text;
      group.appendChild(a);
    }
    linksContainer.appendChild(group);
  }

  inner.appendChild(linksContainer);
  nav.appendChild(inner);

  // Insert at very top of body
  document.body.insertBefore(nav, document.body.firstChild);

  // Toggle handler
  toggle.addEventListener('click', function() {
    linksContainer.classList.toggle('open');
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
