import sys
from pathlib import Path

path = Path('index.html')
content = path.read_text(encoding='utf-8')

import re

# Find the start and end of the corrupted block
# Start: function renderNonCryptoPanel()
# End: end of Wire drill-down buttons section followed by }
pattern = re.compile(r'function renderNonCryptoPanel\(\) \{.*?\}\s+// \?\? Non-Crypto Drill-Down Modal \?\?', re.DOTALL)

new_code = """function renderNonCryptoPanel() {
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
    cardsHtml += '</div>';

    if (catStats.resolved === 0 && catActive.length > 0) {
      cardsHtml += '<div class="nc-row"><span class="nc-lbl">Active Picks</span><span class="nc-val">' + catActive.length + '</span></div>';
      cardsHtml += '<div class="nc-nodata">No closed picks yet</div>';
    } else if (catStats.resolved > 0) {
       // Unrealized
       var unrealizedPnl = 0;
       catActive.forEach(function(p) { unrealizedPnl += Math.max(-100, Math.min(100, p.pnl_pct || 0)); });
       var overallPnl = totalPnl + unrealizedPnl;

       cardsHtml += '<div class="nc-row"><span class="nc-lbl">Active</span><span class="nc-val">' + catActive.length + '</span></div>';
       cardsHtml += '<div class="nc-row"><span class="nc-lbl">Closed</span><span class="nc-val">' + catClosed.length + '</span></div>';
       cardsHtml += '<div class="nc-row"><span class="nc-lbl">W / L / F</span><span class="nc-val">' + catStats.wins + ' / ' + catStats.losses + ' / ' + catStats.flat + '</span></div>';
       cardsHtml += '<div class="nc-row"><span class="nc-lbl">Realized PnL</span><span class="nc-val" style="color:' + pnlColor + '">' + pnlDisplay + '</span></div>';
       cardsHtml += '<div class="nc-row" style="border-top:1px solid rgba(255,255,255,0.1);padding-top:2px;margin-top:2px"><span class="nc-lbl" style="font-weight:700">Overall PnL</span><span class="nc-val" style="color:' + (overallPnl >= 0 ? 'var(--green)' : 'var(--red)') + ';font-weight:700">' + fmtPct(overallPnl) + '</span></div>';
    } else {
      cardsHtml += '<div class="nc-nodata">No data</div>';
    }
    cardsHtml += '</div>';
  }

  if (!hasAnyData) {
    container.innerHTML = '';
    return;
  }

  container.innerHTML = '<div class="nc-panel">' +
    '<h3 style="display:flex;align-items:center;flex-wrap:wrap">' +
    '<span style="color:var(--blue)">Non-Crypto Performance</span> ' +
    '<span style="font-size:11px;color:var(--text-dim);font-weight:400;margin-left:6px">Equities, Forex, Commodities, Futures, ETFs</span>' +
    '</h3>' +
    '<div class="nc-grid">' + cardsHtml + '</div>' +
    '</div>';

  container.querySelectorAll('.nc-drill-btn').forEach(function(btn) {
    btn.addEventListener('click', function(e) {
      e.stopPropagation();
      showNcDrillDown(btn.getAttribute('data-catkey'));
    });
  });
}

// ?? Non-Crypto Drill-Down Modal ??"""

if pattern.search(content):
    content = pattern.sub(new_code, content)
    print("Full Panel Refactor applied")
else:
    print("Pattern NOT found")

path.write_text(content, encoding='utf-8')
