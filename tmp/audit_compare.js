const fs = require('fs');
const embedded = JSON.parse(fs.readFileSync('E:/findtorontoevents_antigravity.ca/tmp/embedded.json','utf8'));
const source = JSON.parse(fs.readFileSync('E:/findtorontoevents_antigravity.ca/audit_dashboard/data/claudes_test_state.json','utf8'));

const srcKeys = Object.keys(source);
const embPorts = embedded.portfolios || [];

console.log('=== STRUCTURE COMPARISON ===');
console.log('Source portfolios:', srcKeys.length);
console.log('Embedded portfolios:', embPorts.length);
console.log('Embedded regime:', embedded.regime);
console.log('Embedded ranking entries:', (embedded.ranking||[]).length);
console.log('');

// Check each source portfolio vs embedded
let mismatches = [];
srcKeys.forEach(key => {
  const src = source[key];
  const emb = embPorts.find(p => p.id === key);
  if (!emb) {
    console.log('MISSING in embedded:', key);
    return;
  }

  if (Math.abs(src.equity - emb.equity) > 0.01) {
    mismatches.push({port: key, field: 'equity', src: src.equity, emb: emb.equity});
  }
  if (src.initial_capital !== emb.initial_capital) {
    mismatches.push({port: key, field: 'initial_capital', src: src.initial_capital, emb: emb.initial_capital});
  }
  if ((src.positions||[]).length !== (emb.positions||[]).length) {
    mismatches.push({port: key, field: 'positions_count', src: (src.positions||[]).length, emb: (emb.positions||[]).length});
  }
  if ((src.closed||[]).length !== (emb.recent_closed||[]).length) {
    mismatches.push({port: key, field: 'closed_count', src: (src.closed||[]).length, emb: (emb.recent_closed||[]).length});
  }
});

console.log('=== DATA MISMATCHES (embedded vs source) ===');
if (mismatches.length === 0) console.log('None found');
else mismatches.forEach(m => console.log(JSON.stringify(m)));

// === CALCULATION AUDIT ===
console.log('');
console.log('=== CALCULATION AUDIT ===');
const issues = [];

Object.entries(source).forEach(([id, port]) => {
  const closed = port.closed || [];
  const positions = port.positions || [];

  // 1. Win/Loss count
  const tpHits = closed.filter(c => c.exit_reason === 'TP' || c.status === 'TP_HIT').length;
  const slHits = closed.filter(c => c.exit_reason === 'SL' || c.status === 'SL_HIT').length;

  if (tpHits !== (port.wins||0) && closed.length > 0) {
    issues.push({port: id, issue: 'wins_mismatch', tp_hits: tpHits, reported_wins: port.wins});
  }
  if (slHits !== (port.losses||0) && closed.length > 0) {
    issues.push({port: id, issue: 'losses_mismatch', sl_hits: slHits, reported_losses: port.losses});
  }

  // 2. PnL % for each closed trade
  closed.forEach(c => {
    if (c.entry_price && c.exit_price) {
      let expectedPnlPct;
      if (c.direction === 'LONG') {
        expectedPnlPct = ((c.exit_price - c.entry_price) / c.entry_price) * 100;
      } else {
        expectedPnlPct = ((c.entry_price - c.exit_price) / c.entry_price) * 100;
      }
      const diff = Math.abs(expectedPnlPct - (c.pnl_pct||0));
      if (diff > 0.5) {
        issues.push({port: id, trade: c.symbol+'_'+c.id.slice(0,6), issue: 'pnl_pct_off', expected: expectedPnlPct.toFixed(4), reported: (c.pnl_pct||0).toFixed(4), diff: diff.toFixed(4)});
      }
    }
  });

  // 3. net_pnl_usd = pnl_usd - commission_exit
  closed.forEach(c => {
    if (c.pnl_usd !== undefined && c.net_pnl_usd !== undefined) {
      const expectedNet = c.pnl_usd - (c.commission_exit||0);
      const diff = Math.abs(expectedNet - c.net_pnl_usd);
      if (diff > 0.1) {
        issues.push({port: id, trade: c.symbol, issue: 'net_pnl_calc', expected: expectedNet.toFixed(4), reported: c.net_pnl_usd.toFixed(4)});
      }
    }
  });

  // 4. TP/SL direction consistency
  closed.forEach(c => {
    if (c.exit_reason === 'TP' && c.direction === 'LONG' && c.exit_price < c.entry_price) {
      issues.push({port: id, trade: c.symbol, issue: 'TP_hit_but_exit_below_entry'});
    }
    if (c.exit_reason === 'SL' && c.direction === 'LONG' && c.exit_price > c.entry_price * 1.01) {
      issues.push({port: id, trade: c.symbol, issue: 'SL_hit_but_profitable'});
    }
    if (c.exit_reason === 'TP' && c.direction === 'SHORT' && c.exit_price > c.entry_price) {
      issues.push({port: id, trade: c.symbol, issue: 'TP_hit_SHORT_but_exit_above_entry'});
    }
  });
});

if (issues.length === 0) console.log('No issues found');
else issues.forEach(i => console.log(JSON.stringify(i)));

// === EMBEDDED STATS AUDIT ===
console.log('');
console.log('=== EMBEDDED STATS AUDIT ===');
const statsIssues = [];

embPorts.forEach(port => {
  const s = port.stats;
  const closed = port.recent_closed || [];
  const positions = port.positions || [];

  // Verify stats.pnl_pct matches (equity - initial) / initial * 100
  const calcPnlPct = ((port.equity - port.initial_capital) / port.initial_capital) * 100;
  if (Math.abs(calcPnlPct - s.pnl_pct) > 0.02) {
    statsIssues.push({port: port.id, issue: 'pnl_pct_vs_equity', calc: calcPnlPct.toFixed(4), reported: s.pnl_pct});
  }

  // Verify stats.pnl_usd matches equity - initial
  const calcPnlUsd = port.equity - port.initial_capital;
  if (Math.abs(calcPnlUsd - s.pnl_usd) > 0.1) {
    statsIssues.push({port: port.id, issue: 'pnl_usd_vs_equity', calc: calcPnlUsd.toFixed(2), reported: s.pnl_usd});
  }

  // Check win_rate consistency
  if (s.total_trades > 0) {
    const tpCount = closed.filter(c => c.exit_reason === 'TP').length;
    const calcWR = (tpCount / s.total_trades) * 100;
    if (Math.abs(calcWR - s.win_rate) > 2) {
      statsIssues.push({port: port.id, issue: 'win_rate_mismatch', tp_count: tpCount, total: s.total_trades, calc: calcWR.toFixed(1), reported: s.win_rate});
    }
  }

  // Check profit_factor
  if (s.total_trades > 0 && closed.length > 0) {
    const wins = closed.filter(c => (c.net_pnl_usd||0) > 0);
    const losses = closed.filter(c => (c.net_pnl_usd||0) < 0);
    const grossWin = wins.reduce((a,c) => a + c.net_pnl_usd, 0);
    const grossLoss = Math.abs(losses.reduce((a,c) => a + c.net_pnl_usd, 0));
    const calcPF = grossLoss > 0 ? grossWin / grossLoss : (grossWin > 0 ? 99 : 0);
    if (Math.abs(calcPF - s.profit_factor) > 0.3 && s.profit_factor > 0) {
      statsIssues.push({port: port.id, issue: 'profit_factor_mismatch', calc: calcPF.toFixed(2), reported: s.profit_factor, grossWin: grossWin.toFixed(2), grossLoss: grossLoss.toFixed(2)});
    }
  }

  // Check open_positions count
  if (positions.length !== s.open_positions) {
    statsIssues.push({port: port.id, issue: 'open_positions_count', actual: positions.length, reported: s.open_positions});
  }

  // Sharpe ratio: sanity check (should be reasonable)
  if (Math.abs(s.sharpe) > 100 && s.total_trades > 0) {
    statsIssues.push({port: port.id, issue: 'sharpe_suspiciously_high', value: s.sharpe});
  }
  if (Math.abs(s.sharpe) > 50 && s.total_trades === 0) {
    statsIssues.push({port: port.id, issue: 'sharpe_nonzero_no_trades', value: s.sharpe});
  }

  // Win rate 100% but losing money
  if (s.win_rate === 100 && s.pnl_usd < 0) {
    statsIssues.push({port: port.id, issue: '100pct_WR_but_losing_money', pnl: s.pnl_usd, wr: s.win_rate});
  }

  // Profit factor 0 but has wins
  if (s.profit_factor === 0 && s.win_rate > 0 && s.total_trades > 0) {
    statsIssues.push({port: port.id, issue: 'PF_zero_despite_wins', wr: s.win_rate, pf: s.profit_factor});
  }
});

if (statsIssues.length === 0) console.log('No stats issues found');
else statsIssues.forEach(i => console.log(JSON.stringify(i)));

// === JS LOGIC AUDIT ===
console.log('');
console.log('=== JS LOGIC / DISPLAY AUDIT ===');

// The HTML says "22 Portfolio Challenge" in title but "26 Portfolio Challenge" in h1
console.log('Title says "22 Portfolio Challenge", h1 says "26 Portfolio Challenge"');
console.log('Stat card hardcodes "22 (4 DV + 3 HTF + 3 prop)" but there are', embPorts.length, 'portfolios');

// Check totalWins calculation bug
// Code: totalWins = allPorts.reduce((a,p) => a + (p.stats.total_trades > 0 ? Math.round(p.stats.win_rate/100*p.stats.total_trades) : 0), 0)
// This rounds per-portfolio which can accumulate rounding errors
let totalWinsJS = embPorts.reduce((a,p) => a + (p.stats.total_trades > 0 ? Math.round(p.stats.win_rate/100*p.stats.total_trades) : 0), 0);
let actualWins = 0;
embPorts.forEach(p => {
  (p.recent_closed||[]).filter(c => c.exit_reason === 'TP').forEach(() => actualWins++);
});
console.log('totalWins (JS calc):', totalWinsJS, '| actual TP count:', actualWins);

// Dormant portfolios
const dormant = embPorts.filter(p => p.stats.total_trades === 0 && (p.positions||[]).length === 0);
console.log('Dormant portfolios (no trades, no positions):', dormant.length, dormant.map(p=>p.id));

// Cash Available calculation in detail view: equity - totalHoldings - unrealizedPnl
// This is wrong. Cash should be port.cash or equity - sum(size_usd)
embPorts.filter(p => (p.positions||[]).length > 0).forEach(port => {
  const unrealizedPnl = (port.positions||[]).reduce((a,p) => a + (p.pnl_usd||0), 0);
  const totalHoldings = (port.positions||[]).reduce((a,p) => a + p.size_usd, 0);
  const cashCalc = port.equity - totalHoldings - unrealizedPnl;
  // Compare to source cash
  const src = source[port.id];
  if (src && src.cash !== undefined) {
    const diff = Math.abs(cashCalc - src.cash);
    if (diff > 5) {
      console.log('Cash mismatch for', port.id, '| JS calc:', cashCalc.toFixed(2), '| source cash:', src.cash.toFixed(2), '| diff:', diff.toFixed(2));
    }
  }
});
