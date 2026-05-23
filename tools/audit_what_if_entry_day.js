#!/usr/bin/env node
/**
 * "What if" by calendar entry day for picks shown on the Antigravity **audit** dashboard
 * (https://findtorontoevents.ca/audit).
 *
 * Data source: audit_trail/data/dashboard_payload.json — same JSON shape the /audit
 * page is generated from (see audit_trail/dashboard_generator.py). Uses
 * audit_dashboard/hc_filter.js for HIGH CONVICTION gates; duplicates the
 * filterHcStrict / passesValidatedEdgePerClass logic from audit_dashboard/template.html
 * (strict mode matches the default HIGH CONVICTION hero button, which sets _hcEdgeStrict).
 *
 * Usage:
 *   node tools/audit_what_if_entry_day.js
 *   node tools/audit_what_if_entry_day.js --dates 2026-04-22,2026-04-23
 *   node tools/audit_what_if_entry_day.js --payload path/to/dashboard_payload.json
 */
'use strict';

const fs = require('fs');
const path = require('path');
const hc = require(path.join(__dirname, '..', 'audit_dashboard', 'hc_filter.js'));

function parseArgs() {
  const args = process.argv.slice(2);
  const o = { dates: null, payload: null };
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--dates' && args[i + 1]) {
      o.dates = args[++i].split(/[\s,]+/).map((d) => d.trim()).filter(Boolean);
    } else if (args[i] === '--payload' && args[i + 1]) {
      o.payload = args[++i];
    }
  }
  return o;
}

/** Same as filterHcStrict in audit_dashboard/template.html (HIGH CONVICTION + strict edge). */
function passesValidatedEdgePerClass(p) {
  if (!p) return false;
  var ac = String(p.asset_class || p.asset_class_type || '').toUpperCase();
  if (ac === 'STOCKS' || ac === 'PENNY_STOCK' || ac === 'EQUITIES') ac = 'EQUITY';
  if (ac === 'COMMODITIES') ac = 'COMMODITY';
  if (ac === 'BONDS') ac = 'BOND';
  if (!ac) ac = 'CRYPTO';
  var score = Number(p.score || 0);
  var trust = Number(p.trust_score || p.trust_score_1 || 0);
  var fwdWr = Number(p.strat_fwd_wr || p.forward_wr || 0);
  if (fwdWr > 1.5) fwdWr = fwdWr / 100;
  var _hcP = hc.getHcGateParams();
  var cryptoFwdWr = (Number(_hcP.forwardWRMinPctCrypto) || 45) / 100;
  var cryptoScore = Number(_hcP.scoreFloorCrypto) || 55;
  var eqFwdWr = (Number(_hcP.forwardWRMinPctEquity) || 55) / 100;
  var eqScore = Number(_hcP.scoreFloorEquity) || 50;
  var fxScore = Number(_hcP.scoreFloorForex) || 40;
  var trustFloor =
    ac === 'CRYPTO' ? (Number(_hcP.trustScoreMinCrypto) || 6) : (Number(_hcP.trustScoreMinOther) || 5);
  if (ac === 'CRYPTO') {
    return fwdWr >= cryptoFwdWr && score >= cryptoScore && trust >= trustFloor;
  }
  if (ac === 'EQUITY') {
    return fwdWr >= eqFwdWr && score >= eqScore && trust >= trustFloor;
  }
  if (ac === 'FOREX') {
    var fwdN = parseInt(
      String(p.strat_fwd_trades != null ? p.strat_fwd_trades : p.forward_trades || 0),
      10
    ) || 0;
    var forexNormalWR = (Number(_hcP.forwardWRMinPctForex) || 55) / 100;
    var forexRelaxedWR = (Number(_hcP.forexRelaxedWRMinPct) || 50) / 100;
    var forexWRFloor = fwdN < 20 ? forexRelaxedWR : forexNormalWR;
    return fwdWr >= forexWRFloor && score >= fxScore && trust >= trustFloor;
  }
  return false;
}

function filterHcStrict(picks) {
  const base = hc.filterHighConvictionOrdered(picks);
  return base.filter(passesValidatedEdgePerClass);
}

function normalizeAc(p) {
  let ac = String(p.asset_class || p.asset_class_type || '').toUpperCase();
  if (!ac) return 'CRYPTO';
  if (ac === 'STOCKS' || ac === 'PENNY_STOCK' || ac === 'EQUITIES') return 'EQUITY';
  if (ac === 'COMMODITIES') return 'COMMODITY';
  if (ac === 'BONDS') return 'BOND';
  return ac;
}

function fold(rows) {
  const by = {};
  let sum = 0;
  let w = 0;
  for (const p of rows) {
    const ac = normalizeAc(p);
    if (!by[ac]) {
      by[ac] = { n: 0, wins: 0, pnl: 0 };
    }
    const pnl = Number(p.pnl_pct || 0);
    by[ac].n++;
    by[ac].pnl += pnl;
    if (pnl > 0) {
      by[ac].wins++;
      w++;
    }
    sum += pnl;
  }
  return { by, n: rows.length, sumPnl: sum, wins: w, wr: rows.length ? (w / rows.length) * 100 : 0 };
}

function byDay(closed, dayPrefix) {
  return closed.filter((p) => (p.timestamp || '').startsWith(dayPrefix));
}

function printTable(title, stat) {
  console.log('\n' + title);
  console.log('  picks:', stat.n, ' sum pnl%:', round4(stat.sumPnl), ' win rate%:', round2(stat.wr));
  const keys = Object.keys(stat.by).sort();
  for (const k of keys) {
    const b = stat.by[k];
    const wr = b.n ? (b.wins / b.n) * 100 : 0;
    console.log('  ', k, ' n=', b.n, ' pnl%=', round4(b.pnl), ' wr%=', round2(wr));
  }
}

function round2(x) {
  return Math.round(x * 100) / 100;
}
function round4(x) {
  return Math.round(x * 10000) / 10000;
}

function main() {
  const args = parseArgs();
  const payloadPath = path.join(
    __dirname,
    '..',
    'audit_trail',
    'data',
    'dashboard_payload.json'
  );
  const fp = args.payload || payloadPath;
  const raw = fs.readFileSync(fp, 'utf8');
  const data = JSON.parse(raw);
  const closed = (data.picks && data.picks.recent_closed) || [];
  const generated = (data.metadata && data.metadata.generated_at) || (data.summary && data.generated_at) || '';
  console.log('=== Audit dashboard what-if (findtorontoevents.ca/audit) ===');
  console.log('Payload:', fp);
  console.log('Payload generated_at:', generated);
  console.log('recent_closed rows:', closed.length, '(capped; see MAX_CLOSED_PICKS in dashboard_generator.py)');

  const defaultDates = ['2026-04-22', '2026-04-23'];
  const dates = args.dates && args.dates.length ? args.dates : defaultDates;

  for (const day of dates) {
    const bucket = byDay(closed, day);
    printTable(day + ' — all closed in payload (by entry date prefix)', fold(bucket));
    printTable(day + ' — HIGH CONVICTION (hc_filter.js only, like loose HC)', fold(hc.filterHighConvictionOrdered(bucket)));
    printTable(
      day + ' — HIGH CONVICTION + validated edge (strict, matches _hcEdgeStrict / hero button)',
      fold(filterHcStrict(bucket))
    );
  }
}

main();
