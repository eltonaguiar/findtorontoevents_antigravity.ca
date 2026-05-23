#!/usr/bin/env node
/**
 * Historical CSV backtest: apply passesHighConvictionPick + cost-adjusted PnL summary.
 *
 *   node tools/hc_csv_backtest.js path/to/picks.csv [--config config/cost_model.json]
 *
 * CSV: first row = headers. Expected columns (aliases):
 *   pnl_pct | pnl_pct_gross — closed PnL %% (required for metrics)
 *   trust_score, trust_tier, strat_fwd_wr, forward_wr, strat_fwd_trades, forward_trades,
 *   confidence, score, elite_score, regime, market_regime, direction,
 *   hf_conviction_tier, conviction_tier, symbol, strategy, asset_class,
 *   source_systems, agreeing_sources, source_system, wf_verdict
 *
 * Quoted fields with commas are not supported (use tab-separated or sanitize exports).
 */
'use strict';

const fs = require('fs');
const path = require('path');

function parseCsvLine(line) {
  const out = [];
  var cur = '';
  var i;
  for (i = 0; i < line.length; i++) {
    var c = line[i];
    if (c === ',') {
      out.push(cur.trim());
      cur = '';
    } else {
      cur += c;
    }
  }
  out.push(cur.trim());
  return out;
}

function loadJson(p) {
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

function netPnlPct(grossPct, cost) {
  var spread = Number(cost.spreadHalfPctEachLeg) || 0;
  var slip = Number(cost.slippagePct) || 0;
  var comm = Number(cost.commissionPctEachLeg) || 0;
  var fund = Number(cost.fundingPctEstimate) || 0;
  var roundTrip = 2 * spread + slip + 2 * comm + fund;
  return grossPct - roundTrip;
}

function main() {
  const csvPath = process.argv[2];
  if (!csvPath) {
    console.error('Usage: node tools/hc_csv_backtest.js <picks.csv> [--config config/cost_model.json]');
    process.exit(1);
  }
  var costPath = path.join(__dirname, '..', 'config', 'cost_model.json');
  var ai = process.argv.indexOf('--config');
  if (ai !== -1 && process.argv[ai + 1]) costPath = process.argv[ai + 1];

  const cost = loadJson(costPath);
  delete cost._doc;
  delete cost.comment;

  const lines = fs.readFileSync(csvPath, 'utf8').split(/\r?\n/).filter(function (l) {
    return l.trim().length > 0;
  });
  if (lines.length < 2) {
    console.error('CSV needs header + rows');
    process.exit(1);
  }
  const headers = parseCsvLine(lines[0]).map(function (h) {
    return h.replace(/^"|"$/g, '').trim();
  });

  const { passesHighConvictionPick } = require(path.join(__dirname, '..', 'audit_dashboard', 'hc_filter.js'));

  var n = 0;
  var nPass = 0;
  var winsGross = 0;
  var winsNet = 0;
  var sumGross = 0;
  var sumNet = 0;

  var li;
  for (li = 1; li < lines.length; li++) {
    const cells = parseCsvLine(lines[li]);
    if (cells.length < headers.length * 0.5) continue;
    const row = {};
    var hi;
    for (hi = 0; hi < headers.length; hi++) {
      row[headers[hi]] = cells[hi] != null ? cells[hi].replace(/^"|"$/g, '') : '';
    }
    n++;
    var g = parseFloat(row.pnl_pct != null && row.pnl_pct !== '' ? row.pnl_pct : row.pnl_pct_gross);
    if (!Number.isFinite(g)) g = 0;

    var pass = passesHighConvictionPick(row);
    if (pass) {
      nPass++;
      var net = netPnlPct(g, cost);
      sumGross += g;
      sumNet += net;
      if (g > 0) winsGross++;
      if (net > 0) winsNet++;
    }
  }

  var wrGross = nPass ? winsGross / nPass : null;
  var wrNet = nPass ? winsNet / nPass : null;
  var avgGross = nPass ? sumGross / nPass : null;
  var avgNet = nPass ? sumNet / nPass : null;

  console.log(
    JSON.stringify(
      {
        csv: csvPath,
        rows_total: n,
        rows_pass_filter: nPass,
        win_rate_gross_on_passed: wrGross != null ? Math.round(wrGross * 10000) / 10000 : null,
        win_rate_net_on_passed: wrNet != null ? Math.round(wrNet * 10000) / 10000 : null,
        mean_pnl_pct_gross_on_passed: avgGross != null ? Math.round(avgGross * 1e6) / 1e6 : null,
        mean_pnl_pct_net_on_passed: avgNet != null ? Math.round(avgNet * 1e6) / 1e6 : null,
        cost_model: cost,
      },
      null,
      2
    )
  );
}

main();
