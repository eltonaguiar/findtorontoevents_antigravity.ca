/**
 * scope_labels.js -- Injectable asset class scope banner
 *
 * Adds a thin (28px) color-coded banner below the navigation bar on every
 * dashboard page, showing which asset class(es) the current page covers.
 *
 * Usage:
 *   <script src="/live-monitor/api/scope_labels.js"></script>
 *   (load AFTER stock-nav.js so #stock-nav-bar exists in the DOM)
 *
 * Design:
 *   - IIFE, zero dependencies, broad browser compat (var-only)
 *   - Exact path match first, then trailing-slash normalization,
 *     then prefix match for directory-based pages
 *   - If the current page is not in the scope map, nothing renders
 */
(function() {
  'use strict';

  // ----------------------------------------------------------------
  // Scope map: pathname -> { scope, label, color, icon }
  // ----------------------------------------------------------------
  var SCOPE_MAP = {

    // --- ALL ASSET CLASSES (purple #a855f7) -----------------------
    '/live-monitor/command-center.html':     { scope: 'ALL ASSET CLASSES', label: 'Stocks, Crypto, Forex, Meme Coins, Penny Stocks, Sports Betting', color: '#a855f7', icon: '\uD83C\uDFAF' },
    '/live-monitor/goldmine-dashboard.html': { scope: 'ALL ASSET CLASSES', label: 'Stocks, Crypto, Forex, Meme Coins, Penny Stocks, Sports Betting', color: '#a855f7', icon: '\uD83C\uDFAF' },
    '/live-monitor/live-monitor.html':       { scope: 'ALL ASSET CLASSES', label: 'Stocks, Crypto, Forex',                                            color: '#a855f7', icon: '\uD83C\uDFAF' },
    '/live-monitor/edge-dashboard.html':     { scope: 'ALL ASSET CLASSES', label: 'Stocks, Crypto, Forex',                                            color: '#a855f7', icon: '\uD83C\uDFAF' },
    '/live-monitor/opportunity-scanner.html': { scope: 'ALL ASSET CLASSES', label: 'Stocks, Crypto, Forex',                                           color: '#a855f7', icon: '\uD83C\uDFAF' },
    '/live-monitor/algo-performance.html':   { scope: 'ALL ASSET CLASSES', label: 'Stocks, Crypto, Forex',                                            color: '#a855f7', icon: '\uD83C\uDFAF' },
    '/live-monitor/winning-patterns.html':   { scope: 'ALL ASSET CLASSES', label: 'Stocks, Crypto, Forex',                                            color: '#a855f7', icon: '\uD83C\uDFAF' },
    '/live-monitor/multi-dimensional.html':  { scope: 'ALL ASSET CLASSES', label: 'Stocks, Crypto, Forex',                                            color: '#a855f7', icon: '\uD83C\uDFAF' },
    '/live-monitor/capital-efficiency.html': { scope: 'ALL ASSET CLASSES', label: 'Stocks, Crypto, Forex',                                            color: '#a855f7', icon: '\uD83C\uDFAF' },
    '/findstocks/portfolio2/picks.html':     { scope: 'ALL ASSET CLASSES', label: 'Stocks, Crypto, Forex',                                            color: '#a855f7', icon: '\uD83C\uDFAF' },
    '/findstocks/portfolio2/leaderboard.html': { scope: 'ALL ASSET CLASSES', label: 'Stocks, Crypto, Forex',                                          color: '#a855f7', icon: '\uD83C\uDFAF' },
    '/findstocks/portfolio2/algorithm-intelligence.html': { scope: 'ALL ASSET CLASSES', label: 'Stocks, Crypto, Forex',                                color: '#a855f7', icon: '\uD83C\uDFAF' },

    // --- STOCKS ONLY (blue #3b82f6) -------------------------------
    '/findstocks/portfolio2/consolidated.html':  { scope: 'STOCKS ONLY', label: 'US & Canadian Stocks',     color: '#3b82f6', icon: '\uD83D\uDCC8' },
    '/findstocks/portfolio2/dashboard.html':     { scope: 'STOCKS ONLY', label: 'US & Canadian Stocks',     color: '#3b82f6', icon: '\uD83D\uDCC8' },
    '/findstocks/portfolio2/dividends.html':     { scope: 'STOCKS ONLY', label: 'Dividend-Paying Stocks',   color: '#3b82f6', icon: '\uD83D\uDCC8' },
    '/findstocks/portfolio2/horizon-picks.html': { scope: 'STOCKS ONLY', label: 'Multi-Horizon Stock Picks', color: '#3b82f6', icon: '\uD83D\uDCC8' },
    '/findstocks/portfolio2/stock-intel.html':   { scope: 'STOCKS ONLY', label: 'Stock Intelligence',       color: '#3b82f6', icon: '\uD83D\uDCC8' },
    '/findstocks/portfolio2/daytrader-sim.html': { scope: 'STOCKS ONLY', label: 'Day Trading Simulator',    color: '#3b82f6', icon: '\uD83D\uDCC8' },
    '/findstocks/portfolio2/stock-profile.html': { scope: 'STOCKS ONLY', label: 'Individual Stock Profiles', color: '#3b82f6', icon: '\uD83D\uDCC8' },
    '/findstocks/portfolio2/backtest-results.html': { scope: 'STOCKS ONLY', label: 'Stock Backtests',       color: '#3b82f6', icon: '\uD83D\uDCC8' },
    '/findstocks/portfolio2/hub.html':           { scope: 'STOCKS ONLY', label: 'Stock Tools Hub',          color: '#3b82f6', icon: '\uD83D\uDCC8' },
    '/findstocks/portfolio2/learning-lab.html':  { scope: 'STOCKS ONLY', label: 'Algorithm Learning',       color: '#3b82f6', icon: '\uD83D\uDCC8' },
    '/live-monitor/smart-money.html':            { scope: 'STOCKS ONLY', label: 'Smart Money Intelligence', color: '#3b82f6', icon: '\uD83D\uDCC8' },

    // --- PENNY STOCKS ONLY (amber #f59e0b) ------------------------
    '/findstocks/portfolio2/penny-stocks.html': { scope: 'PENNY STOCKS ONLY', label: 'Low-Cap Stocks Under $5', color: '#f59e0b', icon: '\uD83E\uDE99' },

    // --- CRYPTO ONLY (orange #f97316) -----------------------------
    '/findcryptopairs/winners.html': { scope: 'CRYPTO ONLY', label: 'Major Cryptocurrencies',      color: '#f97316', icon: '\u20BF' },
    '/findcryptopairs/index.html':   { scope: 'CRYPTO ONLY', label: 'Cryptocurrency Dashboard',    color: '#f97316', icon: '\u20BF' },

    // --- MEME COINS ONLY (pink #ec4899) ---------------------------
    '/findcryptopairs/meme.html': { scope: 'MEME COINS ONLY', label: 'DOGE, SHIB, PEPE, FLOKI & More', color: '#ec4899', icon: '\uD83D\uDC36' },

    // --- SPORTS BETTING ONLY (green #22c55e) ----------------------
    '/live-monitor/sports-betting.html': { scope: 'SPORTS BETTING ONLY', label: 'NHL, NBA, NFL, MLB', color: '#22c55e', icon: '\uD83C\uDFC8' },

    // --- FOREX ONLY (cyan #06b6d4) --------------------------------
    '/findforex2/portfolio/':           { scope: 'FOREX ONLY', label: 'Major Currency Pairs', color: '#06b6d4', icon: '\uD83D\uDCB1' },
    '/findforex2/portfolio/index.html': { scope: 'FOREX ONLY', label: 'Major Currency Pairs', color: '#06b6d4', icon: '\uD83D\uDCB1' },

    // --- MUTUAL FUNDS ONLY (teal #14b8a6) -------------------------
    '/findmutualfunds2/portfolio2/':           { scope: 'MUTUAL FUNDS ONLY', label: 'Canadian & US Mutual Funds', color: '#14b8a6', icon: '\uD83C\uDFE6' },
    '/findmutualfunds2/portfolio2/index.html': { scope: 'MUTUAL FUNDS ONLY', label: 'Canadian & US Mutual Funds', color: '#14b8a6', icon: '\uD83C\uDFE6' }
  };

  // ----------------------------------------------------------------
  // Resolve the current page to a scope entry
  // ----------------------------------------------------------------
  var path = window.location.pathname;
  var info = SCOPE_MAP[path];

  if (!info) {
    // Try without trailing slash
    var stripped = path.replace(/\/$/, '');
    info = SCOPE_MAP[stripped] || SCOPE_MAP[stripped + '/'];
  }

  if (!info) {
    // Prefix match for directory-based pages (e.g. /findforex2/portfolio/)
    for (var key in SCOPE_MAP) {
      if (SCOPE_MAP.hasOwnProperty(key) && key.charAt(key.length - 1) === '/' && path.indexOf(key) === 0) {
        info = SCOPE_MAP[key];
        break;
      }
    }
  }

  // Unknown page -- nothing to render
  if (!info) return;

  // ----------------------------------------------------------------
  // Build the banner DOM
  // ----------------------------------------------------------------
  var banner = document.createElement('div');
  banner.id = 'scope-label-banner';
  banner.style.cssText = [
    'background:rgba(' + hexToRgb(info.color) + ',0.08)',
    'border-bottom:1px solid #2a2a4a',
    'text-align:center',
    'padding:5px 12px',
    'font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif',
    'line-height:1',
    'display:flex',
    'align-items:center',
    'justify-content:center',
    'gap:8px'
  ].join(';') + ';';

  // Scope badge (colored pill)
  var badgeHtml = '<span style="' +
    'background:' + info.color + ';' +
    'color:#0a0a1a;' +
    'padding:3px 10px;' +
    'border-radius:4px;' +
    'font-weight:800;' +
    'font-size:10px;' +
    'letter-spacing:0.8px;' +
    'text-transform:uppercase;' +
    'white-space:nowrap' +
    '">' + info.icon + ' ' + info.scope + '</span>';

  // Descriptive label
  var labelHtml = '<span style="' +
    'color:#8888aa;' +
    'font-size:11px;' +
    'letter-spacing:0.3px' +
    '">Showing: ' + info.label + '</span>';

  banner.innerHTML = badgeHtml + labelHtml;

  // ----------------------------------------------------------------
  // Insert into the DOM: after #stock-nav-bar, or top of <body>
  // ----------------------------------------------------------------
  var nav = document.getElementById('stock-nav-bar');

  if (nav && nav.nextSibling) {
    nav.parentNode.insertBefore(banner, nav.nextSibling);
  } else if (nav) {
    nav.parentNode.appendChild(banner);
  } else {
    // Nav bar not present -- fall back to top of body
    document.body.insertBefore(banner, document.body.firstChild);
  }

  // ----------------------------------------------------------------
  // Utility: convert a hex color string to "r,g,b" for rgba()
  // ----------------------------------------------------------------
  function hexToRgb(hex) {
    var r = parseInt(hex.slice(1, 3), 16);
    var g = parseInt(hex.slice(3, 5), 16);
    var b = parseInt(hex.slice(5, 7), 16);
    return r + ',' + g + ',' + b;
  }

})();
