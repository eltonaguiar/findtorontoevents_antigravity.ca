#!/usr/bin/env node
/**
 * HC evaluator parity CLI (Phase 3).
 * Reads JSON array of picks from stdin, emits JSON array of
 * {pick_id, hc_tier, gates_failed} to stdout.
 *
 * Reuses audit_dashboard/hc_filter.js exports. No DOM / no fetch.
 * Minimal browser stubs kept at top in case hc_filter.js sniffs them.
 */
'use strict';

// --- Browser-global stubs (hc_filter.js is tolerant but be explicit) ---
// hc_filter.js checks `typeof window !== 'undefined'` — leaving it undefined
// is the correct Node path, so we do NOT define window/document/fetch here.

const path = require('path');
const hc = require(path.join(__dirname, '..', 'audit_dashboard', 'hc_filter.js'));

function readStdin() {
  return new Promise((resolve, reject) => {
    let buf = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (c) => { buf += c; });
    process.stdin.on('end', () => resolve(buf));
    process.stdin.on('error', reject);
  });
}

function pickId(pick, idx) {
  return (
    pick.pick_id || pick.id || pick.uuid || pick.signal_id ||
    `${pick.symbol || 'SYM'}|${pick.strategy || 'STRAT'}|${pick.timestamp || pick.entry_time || idx}|${idx}`
  );
}

/**
 * Re-run each gate block individually to identify first failing gate.
 * Mirrors evaluateHcGates1to9 structure but labelled. We don't import private
 * internals — instead we run the public evaluator, then on failure bisect
 * with a light-weight reimplementation to categorise. For parity the only
 * load-bearing output is the pass/fail — `gates_failed` is diagnostic only.
 */
function classifyFailure(pick) {
  // Light categorisation via public params + same helpers used in hc_filter.js
  const params = hc.getHcGateParams();
  const p = pick || {};
  const sc = Number(p.score || 0);
  const trust = Number(p.trust_score || p.trust_score_1 || 0);
  const trustTier = String(p.trust_tier || '').toUpperCase();
  let fwdWr = Number(p.strat_fwd_wr || p.forward_wr || 0);
  if (fwdWr > 1.5) fwdWr = fwdWr / 100;
  const fwdN = parseInt(String(p.strat_fwd_trades != null ? p.strat_fwd_trades : p.forward_trades || 0), 10) || 0;
  let cf = Number(p.confidence || 0);
  if (cf > 1) cf = cf / 100;
  const ac = String(p.asset_class || p.asset_class_type || 'CRYPTO').toUpperCase();
  const failed = [];
  if (sc < (params.scoreAbsoluteFloor || 40)) failed.push('score_absolute_floor');
  if (sc < (params.scoreCompoundFloor || 50) && trust < (params.scoreCompoundTrustMin || 8)) failed.push('score_compound');
  if ((params.trustTierBlacklist || []).map(s => String(s).toUpperCase()).includes(trustTier)) failed.push('trust_tier_blacklist');
  const smallSample = ['COMMODITY', 'FUTURES', 'BOND', 'ETF', 'COMMODITIES'].includes(ac);
  const fwdMin = smallSample ? 2 : (params.forwardTradesMin || 5);
  if (fwdN < fwdMin) failed.push('forward_trades_min');
  if (fwdWr < 0.40) failed.push('fwd_wr_low');
  if (cf > 0.90 && fwdN < 20) failed.push('confidence_max');
  return failed;
}

async function main() {
  const raw = await readStdin();
  let picks;
  try {
    picks = JSON.parse(raw);
  } catch (e) {
    process.stderr.write(`parity-js: bad json: ${e.message}\n`);
    process.exit(2);
  }
  if (!Array.isArray(picks)) {
    process.stderr.write('parity-js: input must be array\n');
    process.exit(2);
  }

  // Process in order — mirrors filterHighConvictionOrdered correlation behaviour.
  if (typeof globalThis !== 'undefined') globalThis._hcPassedSyms = {};
  const out = new Array(picks.length);
  for (let i = 0; i < picks.length; i++) {
    const pick = picks[i] || {};
    const pid = pickId(pick, i);
    const pass = hc.passesHighConvictionPick(pick);
    let hcTier = null;
    let gatesFailed = [];
    if (pass) {
      // Tier reflects hf_conviction_tier (S/A/B). Approximate grade-a/grade-b mapping:
      const t = String(pick.hf_conviction_tier || '').toUpperCase();
      hcTier = (t === 'S' || t === 'A') ? 'grade-a' : (t === 'B' ? 'grade-b' : 'grade-a');
      // Update correlation registry same as filterHighConvictionOrdered.
      const sym = String(pick.symbol || '').toUpperCase();
      const dir = String(pick.direction || pick.signal_type || 'LONG').toUpperCase();
      if (sym && globalThis._hcPassedSyms) globalThis._hcPassedSyms[sym] = dir;
    } else {
      gatesFailed = classifyFailure(pick);
    }
    out[i] = { pick_id: pid, hc_tier: hcTier, gates_failed: gatesFailed };
  }
  process.stdout.write(JSON.stringify(out));
}

main().catch((e) => {
  process.stderr.write(`parity-js: ${e.stack || e.message}\n`);
  process.exit(1);
});
