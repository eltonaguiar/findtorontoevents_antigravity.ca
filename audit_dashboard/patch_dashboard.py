import sys
from pathlib import Path

content = Path('index.html').read_text(encoding='utf-8')

# Chunk 1: Global metadata and renderNonCryptoPanel start
target1 = """function renderNonCryptoPanel() {
  var container = el('non-crypto-panel');
  if (!container) return;

  var activePicks = (D.picks && D.picks.active) || [];
  var closedPicks = (D.picks && D.picks.recent_closed) || [];

  // Filter out blocked systems
  activePicks = activePicks.filter(function(p) { return !isBlockedSystem(p.source_system); });
  closedPicks = closedPicks.filter(function(p) { return !isBlockedSystem(p.source_system); });

  // Define non-crypto asset categories (only categories with real data)
  var categories = [
    {key: 'EQUITY', label: 'Equities & Stocks', icon: '\\u{1F4C8}', color: 'var(--cyan)', borderColor: 'rgba(34,211,238,0.3)'},
    {key: 'FOREX', label: 'Forex', icon: '\\u{1F4B1}', color: 'var(--blue)', borderColor: 'rgba(96,165,250,0.3)'},
    {key: 'COMMODITY', label: 'Commodities', icon: '\\u{1F6E2}', color: 'var(--orange)', borderColor: 'rgba(251,146,60,0.3)'},
    {key: 'FUTURES', label: 'Futures', icon: '\\u{1F4CA}', color: 'var(--yellow)', borderColor: 'rgba(245,158,11,0.3)'},
    {key: 'ETF', label: 'ETFs', icon: '\\u{1F4E6}', color: 'var(--cyan)', borderColor: 'rgba(34,211,238,0.3)'}
  ];

  function matchCategory(pick, catKey) {
    var ac = ((pick.asset_class || '') + '').toUpperCase();
    var cat = ((pick.category || '') + '').toUpperCase();
    var sym = ((pick.symbol || '') + '').toUpperCase();
    if (catKey === 'FOREX') return ac === 'FOREX' || cat === 'FOREX' || sym.includes('=X');
    if (catKey === 'EQUITY') return ac === 'EQUITY' || ac === 'STOCK' || cat === 'EQUITY' || cat === 'STOCK' || cat === 'STOCKS';
    if (catKey === 'COMMODITY') return ac === 'COMMODITY' || cat === 'COMMODITY' || cat === 'COMMODITIES' || sym.startsWith('XAG') || sym.startsWith('XAU');
    if (catKey === 'FUTURES') return ac === 'FUTURES' || cat === 'FUTURES' || cat === 'FUTURE';
    if (catKey === 'ETF') return ac === 'ETF' || cat === 'ETF';
    return false;
  }

  function isAnyNonCrypto(pick) {
    for (var j = 0; j < categories.length; j++) {
      if (matchCategory(pick, categories[j].key)) return true;
    }
    return false;
  }"""

replacement1 = """// Asset class metadata (icons, colors, display labels)
var NON_CRYPTO_METADATA = {
  EQUITY:    { label: 'Equities & Stocks', icon: '\\u{1F4C8}', color: 'var(--cyan)',   borderColor: 'rgba(34,211,238,0.3)' },
  STOCK:     { label: 'Equities & Stocks', icon: '\\u{1F4C8}', color: 'var(--cyan)',   borderColor: 'rgba(34,211,238,0.3)' },
  FOREX:     { label: 'Forex Markets',     icon: '\\u{1F4B1}', color: 'var(--blue)',   borderColor: 'rgba(96,165,250,0.3)' },
  COMMODITY: { label: 'Commodities',       icon: '\\u{1F6E2}', color: 'var(--orange)', borderColor: 'rgba(251,146,60,0.3)' },
  FUTURES:   { label: 'Futures Markets',   icon: '\\u{1F4CA}', color: 'var(--yellow)', borderColor: 'rgba(245,158,11,0.3)' },
  ETF:       { label: 'ETFs & Index',      icon: '\\u{1F4E6}', color: 'var(--cyan)',   borderColor: 'rgba(34,211,238,0.3)' },
  BOND:      { label: 'Fixed Income',      icon: '\\u{1F4D6}', color: 'var(--blue)',   borderColor: 'rgba(96,165,250,0.3)' }
};

function matchCategory(pick, catKey) {
  if (!pick) return false;
  var ac = ((pick.asset_class || '') + '').toUpperCase();
  var cat = ((pick.category || '') + '').toUpperCase();
  var sym = ((pick.symbol || '') + '').toUpperCase();
  
  if (catKey === 'FOREX') return ac === 'FOREX' || cat === 'FOREX' || sym.endsWith('=X');
  if (catKey === 'EQUITY' || catKey === 'STOCK') {
    return ac === 'EQUITY' || ac === 'STOCK' || cat === 'EQUITY' || cat === 'STOCK' || cat === 'STOCKS';
  }
  if (catKey === 'COMMODITY') return ac === 'COMMODITY' || cat === 'COMMODITY' || cat === 'COMMODITIES' || sym.startsWith('XAG') || sym.startsWith('XAU');
  if (catKey === 'FUTURES') return ac === 'FUTURES' || cat === 'FUTURES' || cat === 'FUTURE';
  if (catKey === 'ETF') return ac === 'ETF' || cat === 'ETF';
  return false;
}

function renderNonCryptoPanel() {
  var container = el('non-crypto-panel');
  if (!container) return;

  var activePicks = (D.picks && D.picks.active) || [];
  var closedPicks = (D.picks && D.picks.recent_closed) || [];

  // Filter out blocked systems
  activePicks = activePicks.filter(function(p) { return !isBlockedSystem(p.source_system); });
  closedPicks = closedPicks.filter(function(p) { return !isBlockedSystem(p.source_system); });

  // Use categories from data if available, fallback to defaults
  var dataCategories = (D.summary && D.summary.non_crypto_performance && D.summary.non_crypto_performance.categories) || {};
  var sortedKeys = Object.keys(dataCategories).sort();
  
  // If no summary data, fall back to hardcoded keys
  if (sortedKeys.length === 0) {
    sortedKeys = ['EQUITY', 'FOREX', 'COMMODITY', 'FUTURES', 'ETF'];
  }

  var hasAnyData = false;
  var cardsHtml = '';

  for (var k = 0; k < sortedKeys.length; k++) {
    var catKey = sortedKeys[k];
    var meta = NON_CRYPTO_METADATA[catKey] || { label: catKey, icon: '\\u{1F4C1}', color: 'var(--text)', borderColor: 'rgba(255,255,255,0.2)' };
    
    var catActive = activePicks.filter(function(p) { return matchCategory(p, catKey); });
    var catClosed = closedPicks.filter(function(p) { return matchCategory(p, catKey); });
    
    // Skip if no data for this category
    if (catActive.length === 0 && catClosed.length === 0) continue;
    hasAnyData = true;

    var catStats = computeOutcomeStats(catClosed, {
      capPnl: function(v) { return Math.max(-100, Math.min(200, v || 0)); },
      getPnl: getResolvedTradePnl
    });
    
    var wr = catStats.winRate;
    var totalPnl = catStats.totalPnl;
    var wrColor = wr === null ? 'var(--text-dim)' : wr > 50 ? 'var(--green)' : wr >= 40 ? 'var(--yellow)' : 'var(--red)';
    var wrDisplay = wr !== null ? fmt(wr, 1) + '%' : 'N/A';
    var pnlDisplay = catClosed.length > 0 ? fmtPct(totalPnl) : 'N/A';
    var pnlColor = totalPnl >= 0 ? 'var(--green)' : 'var(--red)';

    cardsHtml += '<div class="nc-card" style="border-color:' + meta.borderColor + '">';
    cardsHtml += '<div class="nc-header">';
    cardsHtml += '<span class="nc-title" style="color:' + meta.color + '">' + meta.icon + ' ' + meta.label + '</span>';
    cardsHtml += '<span style="display:flex;align-items:center;gap:8px">';
    if (catStats.resolved > 0) {
      cardsHtml += '<span class="nc-wr" style="color:' + wrColor + '">' + wrDisplay + '</span>';
    }
    cardsHtml += '<button class="nc-drill-btn" data-catkey="' + catKey + '" title="Drill down into ' + meta.label + ' trades" style="background:none;border:1px solid ' + meta.borderColor + ';color:' + meta.color + ';cursor:pointer;border-radius:5px;padding:2px 6px;font-size:14px;line-height:1;display:flex;align-items:center;justify-content:center;transition:all 0.2s">&#128269;</button>';
    cardsHtml += '</span>';
    cardsHtml += '</div>';"""

# Chunk 2: showNcDrillDown category metadata removal
target2 = """  var categories = {
    EQUITY: { label: 'Equities & Stocks', icon: '\\u{1F4C8}', color: 'var(--cyan)' },
    FOREX: { label: 'Forex', icon: '\\u{1F4B1}', color: 'var(--blue)' },
    COMMODITY: { label: 'Commodities', icon: '\\u{1F6E2}', color: 'var(--orange)' },
    FUTURES: { label: 'Futures', icon: '\\u{1F4CA}', color: 'var(--yellow)' },
    ETF: { label: 'ETFs', icon: '\\u{1F4E6}', color: 'var(--cyan)' }
  };
  var catMeta = categories[catKey] || { label: catKey, icon: '', color: 'var(--text)' };

  // Reuse matchCategory from renderNonCryptoPanel
  function matchCat(pick) {
    var ac = ((pick.asset_class || '') + '').toUpperCase();
    var cat = ((pick.category || '') + '').toUpperCase();
    var sym = ((pick.symbol || '') + '').toUpperCase();
    if (catKey === 'FOREX') return ac === 'FOREX' || cat === 'FOREX' || sym.includes('=X');
    if (catKey === 'EQUITY') return ac === 'EQUITY' || ac === 'STOCK' || cat === 'EQUITY' || cat === 'STOCK' || cat === 'STOCKS';
    if (catKey === 'COMMODITY') return ac === 'COMMODITY' || cat === 'COMMODITY' || cat === 'COMMODITIES' || sym.startsWith('XAG') || sym.startsWith('XAU');
    if (catKey === 'FUTURES') return ac === 'FUTURES' || cat === 'FUTURES' || cat === 'FUTURE';
    if (catKey === 'ETF') return ac === 'ETF' || cat === 'ETF';
    return false;
  }"""

replacement2 = """  var meta = NON_CRYPTO_METADATA[catKey] || { label: catKey, icon: '', color: 'var(--text)' };

  function matchCat(pick) {
    return matchCategory(pick, catKey);
  }"""

if target1 in content:
    content = content.replace(target1, replacement1)
    print("Patch 1 applied")
else:
    print("Patch 1 NOT found")

if target2 in content:
    content = content.replace(target2, replacement2)
    print("Patch 2 applied")
else:
    print("Patch 2 NOT found")

Path('index.html').write_text(content, encoding='utf-8')
