#!/usr/bin/env node
/**
 * Backtest passesHighConvictionPick on a closed-picks JSON array.
 *
 *   node tools/hc_filter_backtest.js [path/to/closed_picks.json]
 *
 * Uses audit_dashboard/hc_filter.js (same as the dashboard). Reports how many
 * rows pass; if n_pass is 0, check forward trade counts / elite_score in your export.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { passesHighConvictionPick } = require(path.join(__dirname, '..', 'audit_dashboard', 'hc_filter.js'));

const closedPath = process.argv[2] || path.join(__dirname, '..', 'alpha_engine', 'data', 'closed_picks.json');
const raw = fs.readFileSync(closedPath, 'utf8');
const picks = JSON.parse(raw);
if (!Array.isArray(picks)) {
  console.error('Expected JSON array');
  process.exit(1);
}

let nHc = 0;
let wins = 0;
let pnlSum = 0;
const hcPnls = [];

for (let i = 0; i < picks.length; i++) {
  const p = picks[i];
  if (!p || typeof p !== 'object') continue;
  if (!passesHighConvictionPick(p)) continue;
  nHc++;
  const pnl = Number(p.pnl_pct);
  const pnlN = Number.isFinite(pnl) ? pnl : 0;
  pnlSum += pnlN;
  hcPnls.push(pnlN);
  if (pnlN > 0) wins++;
}

const wr = nHc ? wins / nHc : null;
const exp = nHc ? pnlSum / nHc : null;

const out = {
  closed_path: closedPath,
  n_total: picks.length,
  n_high_conviction: nHc,
  win_rate: wr != null ? Math.round(wr * 10000) / 10000 : null,
  mean_pnl_pct: exp != null ? Math.round(exp * 1e6) / 1e6 : null,
  sum_pnl_pct: Math.round(pnlSum * 1e6) / 1e6,
};

if (nHc === 0) {
  out.warning =
    'No rows passed — common causes: strat_fwd_trades/forward_trades < 5 in export, elite_score < 50, trust_score < 6.';
}

console.log(JSON.stringify(out, null, 2));
