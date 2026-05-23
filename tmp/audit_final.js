const fs = require('fs');
const source = JSON.parse(fs.readFileSync('E:/findtorontoevents_antigravity.ca/audit_dashboard/data/claudes_test_state.json','utf8'));
const embedded = JSON.parse(fs.readFileSync('E:/findtorontoevents_antigravity.ca/tmp/embedded.json','utf8'));

// Investigate win_rate mismatches more carefully
console.log('=== WIN RATE DEEP DIVE ===');

['contrarian', 'anti_meme', 'prop_aggressive', 'forex_carry', 'multi_asset_diversified'].forEach(id => {
  const src = source[id];
  const emb = embedded.portfolios.find(p => p.id === id);
  const closed = src.closed || [];
  console.log('\n' + id + ':');
  console.log('  Source wins/losses:', src.wins, '/', src.losses);
  console.log('  Embedded win_rate:', emb.stats.win_rate);
  console.log('  Closed trades:');
  closed.forEach(c => {
    console.log('    ', c.symbol, c.direction, 'exit_reason:', c.exit_reason, 'status:', c.status, 'net_pnl:', c.net_pnl_usd?.toFixed(2));
  });
  // Wins field in source counts wins, but the embedded stats.win_rate is pre-computed
  // Check: is source.wins counting something different from TP hits?
  const pnlPositive = closed.filter(c => (c.net_pnl_usd || 0) > 0).length;
  console.log('  TP exits:', closed.filter(c => c.exit_reason === 'TP').length);
  console.log('  Net PnL positive trades:', pnlPositive);
  console.log('  Source wins field:', src.wins);
});

// Check the JS render code's totalWins calc vs display
console.log('\n=== TITLE / LABEL INCONSISTENCIES ===');
console.log('HTML <title>: "22 Portfolio Challenge"');
console.log('HTML <h1>: "26 Portfolio Challenge"');
console.log('Stat card Portfolios value hardcoded: "22 (4 DV + 3 HTF + 3 prop)"');
console.log('Actual portfolio count:', embedded.portfolios.length);

// Check ranking vs top3
console.log('\n=== RANKING AUDIT ===');
const ranking = embedded.ranking || [];
ranking.forEach((r, i) => {
  const port = embedded.portfolios.find(p => p.id === r.id);
  if (port) {
    const calcPnlPct = ((port.equity - port.initial_capital) / port.initial_capital) * 100;
    if (Math.abs(calcPnlPct - r.pnl_pct) > 0.02) {
      console.log('Ranking pnl_pct mismatch for', r.name, '| ranking:', r.pnl_pct, '| calc:', calcPnlPct.toFixed(4));
    }
    if (Math.abs(port.stats.win_rate - r.win_rate) > 0.5) {
      console.log('Ranking win_rate mismatch for', r.name, '| ranking:', r.win_rate, '| stats:', port.stats.win_rate);
    }
  }
});
console.log('(No output above = ranking matches portfolio stats)');

// Check for duplicate position IDs across portfolios (same signal in multiple portfolios)
console.log('\n=== DUPLICATE POSITION IDS ===');
const allPosIds = {};
embedded.portfolios.forEach(p => {
  (p.positions || []).forEach(pos => {
    if (!allPosIds[pos.id]) allPosIds[pos.id] = [];
    allPosIds[pos.id].push(p.id);
  });
});
Object.entries(allPosIds).filter(([,ports]) => ports.length > 1).forEach(([id, ports]) => {
  console.log('  Position', id, 'shared across:', ports.join(', '));
});

// Check equity_history consistency
console.log('\n=== EQUITY HISTORY ISSUES ===');
Object.entries(source).forEach(([id, port]) => {
  const eh = port.equity_history || [];
  if (eh.length < 2) return;
  // Last equity_history entry should match port.equity
  const lastEH = eh[eh.length - 1].equity;
  if (Math.abs(lastEH - port.equity) > 0.01) {
    console.log(id, '| last EH:', lastEH, '| port.equity:', port.equity, '| diff:', Math.abs(lastEH - port.equity).toFixed(2));
  }
  // First should be initial_capital
  if (Math.abs(eh[0].equity - port.initial_capital) > 0.01) {
    console.log(id, '| first EH:', eh[0].equity, '| initial:', port.initial_capital);
  }
  // High water mark should be max of equity_history
  const maxEH = Math.max(...eh.map(e => e.equity));
  if (Math.abs(maxEH - port.high_water_mark) > 0.01) {
    console.log(id, '| max EH:', maxEH, '| HWM:', port.high_water_mark, '| diff:', Math.abs(maxEH - port.high_water_mark).toFixed(2));
  }
});
console.log('(No output above = equity history is consistent)');
