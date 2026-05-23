const fs = require('fs');
const source = JSON.parse(fs.readFileSync('E:/findtorontoevents_antigravity.ca/audit_dashboard/data/claudes_test_state.json','utf8'));
const embedded = JSON.parse(fs.readFileSync('E:/findtorontoevents_antigravity.ca/tmp/embedded.json','utf8'));

console.log('=== SHARPE RATIO AUDIT ===');
// Sharpe = (mean return) / (stddev of returns) * sqrt(252) annualized
// But with only hours of data, the Sharpe values are likely computed from equity_history

Object.entries(source).forEach(([id, port]) => {
  const eh = port.equity_history || [];
  if (eh.length < 3) return;

  // Compute returns from equity history
  const returns = [];
  for (let i = 1; i < eh.length; i++) {
    returns.push((eh[i].equity - eh[i-1].equity) / eh[i-1].equity);
  }

  if (returns.length === 0) return;

  const mean = returns.reduce((a,r) => a + r, 0) / returns.length;
  const variance = returns.reduce((a,r) => a + (r - mean) ** 2, 0) / returns.length;
  const stddev = Math.sqrt(variance);

  // The embedded sharpe
  const emb = embedded.portfolios.find(p => p.id === id);
  const embSharpe = emb ? emb.stats.sharpe : '?';

  // Try annualized with sqrt(252*24/0.5) for 30-min intervals, or sqrt(252) for daily
  const rawSharpe = stddev > 0 ? mean / stddev : 0;
  const annualized252 = rawSharpe * Math.sqrt(252);
  const annualized30min = rawSharpe * Math.sqrt(252 * 48); // 48 30-min periods per day

  if (embSharpe !== 0 && Math.abs(embSharpe) > 10) {
    console.log(id, '| embedded sharpe:', embSharpe, '| raw:', rawSharpe.toFixed(4),
      '| ann(daily):', annualized252.toFixed(2), '| ann(30min):', annualized30min.toFixed(2),
      '| returns:', returns.length, '| mean:', (mean*100).toFixed(6)+'%', '| std:', (stddev*100).toFixed(6)+'%');
  }
});

console.log('');
console.log('=== PROFIT FACTOR DEEP AUDIT ===');
// PF should be gross_wins / gross_losses
Object.entries(source).forEach(([id, port]) => {
  const closed = port.closed || [];
  if (closed.length === 0) return;

  const emb = embedded.portfolios.find(p => p.id === id);
  const embPF = emb ? emb.stats.profit_factor : 0;

  const grossWin = closed.filter(c => (c.net_pnl_usd||0) > 0).reduce((a,c) => a + c.net_pnl_usd, 0);
  const grossLoss = Math.abs(closed.filter(c => (c.net_pnl_usd||0) < 0).reduce((a,c) => a + c.net_pnl_usd, 0));
  const calcPF = grossLoss > 0 ? grossWin / grossLoss : (grossWin > 0 ? 99 : 0);

  console.log(id, '| embedded PF:', embPF, '| calc PF:', calcPF.toFixed(2),
    '| grossWin:', grossWin.toFixed(2), '| grossLoss:', grossLoss.toFixed(2));
});

console.log('');
console.log('=== NET_PNL FORMULA INVESTIGATION ===');
// It seems net_pnl = pnl_usd - commission_entry - commission_exit (not just - commission_exit)
const port = source['score_leaders'];
const c = port.closed[0]; // BTCUSDT
console.log('Example: score_leaders BTCUSDT');
console.log('  pnl_usd:', c.pnl_usd);
console.log('  commission_entry:', c.commission_entry);
console.log('  slippage_entry:', c.slippage_entry);
console.log('  commission_exit:', c.commission_exit);
console.log('  net_pnl_usd:', c.net_pnl_usd);
console.log('  pnl - comm_exit:', (c.pnl_usd - c.commission_exit).toFixed(4));
console.log('  pnl - comm_entry - comm_exit:', (c.pnl_usd - c.commission_entry - c.commission_exit).toFixed(4));
console.log('  pnl - comm_exit - slippage:', (c.pnl_usd - c.commission_exit - c.slippage_entry).toFixed(4));
console.log('  pnl - comm_entry - comm_exit - slip:', (c.pnl_usd - c.commission_entry - c.commission_exit - c.slippage_entry).toFixed(4));

console.log('');
console.log('=== STALE DATA CHECK ===');
// Check how old the data is
const now = new Date('2026-03-10T18:00:00Z'); // approximate "now"
Object.entries(source).forEach(([id, port]) => {
  const lastUp = new Date(port.last_updated);
  const created = new Date(port.created_at);
  const ageHours = (now - lastUp) / 3600000;
  const lifeHours = (lastUp - created) / 3600000;
  if (lifeHours < 12) {
    // All portfolios are very new (< 1 day old)
  }
});
console.log('All portfolios created:', source.score_leaders.created_at);
console.log('Last updated:', source.score_leaders.last_updated);
console.log('Data age: < 1 day (all portfolios born same day 2026-03-10)');

// Check for suspicious patterns
console.log('');
console.log('=== PROP SWING ANOMALY ===');
const ps = source['prop_swing'];
console.log('prop_swing: initial=', ps.initial_capital, 'equity=', ps.equity, 'pnl%=', ((ps.equity-ps.initial_capital)/ps.initial_capital*100).toFixed(2)+'%');
console.log('  wins:', ps.wins, 'losses:', ps.losses, 'total closed:', ps.closed.length);
console.log('  embedded stats:', JSON.stringify(embedded.portfolios.find(p=>p.id==='prop_swing').stats));
// WR 0% but equity is UP $1255? That's suspicious
if (ps.wins === 0 && ps.equity > ps.initial_capital) {
  console.log('  ** ANOMALY: 0 wins but equity UP by $' + (ps.equity - ps.initial_capital).toFixed(2));
  console.log('  Closed trades:', JSON.stringify(ps.closed.map(c => ({sym: c.symbol, exit_reason: c.exit_reason, net_pnl: c.net_pnl_usd}))));
  console.log('  Open positions:', JSON.stringify(ps.positions.map(p => ({sym: p.symbol, pnl: p.pnl_usd, size: p.size_usd}))));
}
