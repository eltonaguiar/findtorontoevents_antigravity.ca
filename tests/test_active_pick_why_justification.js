/**
 * Regression tests for the Active Picks "WHY" justification tooltip on
 * audit_dashboard/template.html.
 *
 * The operator requirement (2026-10-04): every active pick must expose a
 * tooltip that states a strong, statistics-or-fundamentals justification for
 * why it was chosen — and be honest when the evidence is thin.
 *
 * Run: node tests/test_active_pick_why_justification.js
 *
 * Strategy: brace-match and eval the REAL functions out of template.html
 * (same technique as tests/test_card_metrics.js) so the test exercises the
 * shipped code, not a copy. Only the descriptive helpers are stubbed.
 */

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const templatePath = path.join(__dirname, '..', 'audit_dashboard', 'template.html');
const templateSrc = fs.readFileSync(templatePath, 'utf8');

let passed = 0;
let failed = 0;
function test(name, fn) {
  try {
    fn();
    passed++;
    console.log('ok   —', name);
  } catch (e) {
    failed++;
    console.error('FAIL —', name);
    console.error('       ' + (e && e.message ? e.message : e));
  }
}

// ---------------------------------------------------------------------------
// Source extraction: slice a top-level function out of template.html up to the
// next top-level `function` declaration. Regex literals (e.g. /&"/g) make a
// naive brace-matcher unreliable, so anchor on declaration boundaries instead.
// ---------------------------------------------------------------------------
function extractByNext(src, header, nextHeader) {
  const start = src.indexOf(header);
  if (start === -1) throw new Error('missing `' + header + '` in template.html');
  const end = src.indexOf(nextHeader, start + header.length);
  if (end === -1) throw new Error('missing next marker `' + nextHeader + '` after ' + header);
  return src.slice(start, end);
}

const fnSrc = {
  _normFwdWrPct: extractByNext(templateSrc, 'function _normFwdWrPct(x) {', '\nfunction '),
  _parseExportNumber: extractByNext(templateSrc, 'function _parseExportNumber(value) {', '\nfunction '),
  _normalizeExportText: extractByNext(templateSrc, 'function _normalizeExportText(v) {', '\nfunction '),
  _pickEvidenceTier: extractByNext(templateSrc, 'function _pickEvidenceTier(p) {', 'function _buildPickJustification(p) {'),
  _buildPickJustification: extractByNext(templateSrc, 'function _buildPickJustification(p) {', '\nfunction _deriveForwardWR(p) {'),
};

for (const [name, src] of Object.entries(fnSrc)) {
  if (!/^function /.test(src.trim())) throw new Error('bad extraction for ' + name);
  // Syntax-only compile check (calls are resolved at invocation time).
  new Function(src);
}

const builder = new Function(
  '_normFwdWrPct', '_parseExportNumber', '_normalizeExportText',
  'getVerifiedTier', '_buildDirectionReason', '_lookupStrategyDescription',
  '_lookupSystemDescription', '_symDirIntrabarUseable',
  fnSrc._normFwdWrPct + '\n' + fnSrc._parseExportNumber + '\n' + fnSrc._normalizeExportText + '\n' +
  fnSrc._pickEvidenceTier + '\n' + fnSrc._buildPickJustification + '\n' +
  'return { _pickEvidenceTier, _buildPickJustification };'
);

function build(overrides) {
  const opts = overrides || {};
  return builder(
    fnSrc._normFwdWrPct,
    fnSrc._parseExportNumber,
    fnSrc._normalizeExportText,
    opts.getVerifiedTier || (() => ({ tier: null, combo_stats: null, strat_stats: null })),
    opts._buildDirectionReason || (() => 'SHORT - overbought RSI, momentum down'),
    opts._lookupStrategyDescription || (() => 'Mean-reversion strategy that fades overbought extremes'),
    opts._lookupSystemDescription || (() => 'Non-crypto multi-strategy consensus engine'),
    opts._symDirIntrabarUseable || (() => false)
  );
}

const mod = build();

// Real live payload pick (SB=F, 2026-10-03) — no forward sample.
const SB_F = {
  symbol: 'SB=F', direction: 'SHORT', strategy: 'non_crypto_consensus',
  source_system: 'non_crypto_consensus', asset_class: 'COMMODITY',
  reason: '[Consensus 2v0] Strategies: futures_bb_mean_reversion, cot_positioning. Original: COT positioning SHORT: Weekly RSI=82 overbought. Sugar.',
  confidence: 0.7, score: 25, rr_ratio: 1.33,
  forward_wr: 0, forward_trades: 0, forward_validated: false,
  forward_status: 'NO_DATA: no closed picks found for this system/strategy',
  trust_score: 3, trust_label: 'LOW', trust_tier: 'WATCH',
  trust_breakdown: { freshness: 2, track_record: 0, edge: 0, regime_alignment: 1, rr_quality: 0 },
  wf_p_value: 0.452163, wf_final_score: 0.4008, wf_verdict: 'VIABLE', wf_oos_wr: 64.3,
  ml_score: 55.0, antigravity_score: 70.0,
  antigravity_tooltip: 'Safe Trading Protocol: Confirmed band 60-79 (Paper only)',
  concept_family: 'standard',
  _penalties: ['blocked_asset_class(FUTURES):-60'],
};

// ---------------------------------------------------------------------------
// Static wiring assertions
// ---------------------------------------------------------------------------
test('template defines _pickEvidenceTier and _buildPickJustification', () => {
  assert.ok(templateSrc.includes('function _pickEvidenceTier('), '_pickEvidenceTier missing');
  assert.ok(templateSrc.includes('function _buildPickJustification('), '_buildPickJustification missing');
});

test('WHY badge is wired into the Symbol cell render', () => {
  assert.ok(templateSrc.includes('\\u2139 WHY'), 'WHY badge label not found');
  assert.ok(
    /\$\{whyBadge\}/.test(templateSrc),
    'whyBadge is not interpolated into the symbol <td> — badge would never render'
  );
});

// ---------------------------------------------------------------------------
// Evidence-tier logic
// ---------------------------------------------------------------------------
test('real SB=F pick (no forward sample, non-significant WF) → THIN EVIDENCE', () => {
  const ev = mod._pickEvidenceTier(SB_F);
  assert.strictEqual(ev.tier, 'THIN');
  assert.strictEqual(ev.label, 'THIN EVIDENCE');
});

test('proven pick (n>=10, WR>=55) → PROVEN EDGE', () => {
  const p = Object.assign({}, SB_F, { strat_fwd_wr: 61.5, strat_fwd_trades: 240 });
  assert.strictEqual(mod._pickEvidenceTier(p).tier, 'PROVEN');
});

test('significant walk-forward (p<0.05, OOS WR>=55) → PROVEN EDGE', () => {
  const p = Object.assign({}, SB_F, { forward_wr: null, forward_trades: 0, wf_p_value: 0.011, wf_oos_wr: 58.0 });
  assert.strictEqual(mod._pickEvidenceTier(p).tier, 'PROVEN');
});

test('GOLDEN verified edge → PROVEN EDGE', () => {
  const m2 = build({ getVerifiedTier: () => ({ tier: 'GOLDEN', combo_stats: { wr: 66, pf: 2.1, n: 9 }, strat_stats: null }) });
  assert.strictEqual(m2._pickEvidenceTier(SB_F).tier, 'PROVEN');
});

test('VERIFIED verified edge → SUPPORTED', () => {
  const m2 = build({ getVerifiedTier: () => ({ tier: 'VERIFIED', combo_stats: null, strat_stats: { wr: 57, pf: 1.4, n: 40 } }) });
  assert.strictEqual(m2._pickEvidenceTier(SB_F).tier, 'SUPPORTED');
});

test('thin forward sample (n>=5, WR>=45) → SUPPORTED', () => {
  const p = Object.assign({}, SB_F, { strat_fwd_wr: 48.0, strat_fwd_trades: 12 });
  assert.strictEqual(mod._pickEvidenceTier(p).tier, 'SUPPORTED');
});

test('no evidence at all → UNPROVEN', () => {
  const p = { symbol: 'X', direction: 'LONG', strategy: 's', source_system: 's' };
  assert.strictEqual(mod._pickEvidenceTier(p).tier, 'UNPROVEN');
});

test('losing symbol×strategy combo caps a strong forward sample to THIN', () => {
  const m2 = build({ getVerifiedTier: () => ({ tier: 'TRACK', combo_stats: { wr: 35.1, pf: 0.69, n: 97 }, strat_stats: null }) });
  const p = Object.assign({}, SB_F, { strat_fwd_wr: 64.0, strat_fwd_trades: 50 });
  const ev = m2._pickEvidenceTier(p);
  assert.strictEqual(ev.tier, 'THIN');
  assert.strictEqual(ev.comboBad, true);
  const out = m2._buildPickJustification(p);
  assert.ok(out.html.includes('Conflict:'), 'conflict note missing');
  assert.ok(out.html.includes('35.1%'), 'combine WR not surfaced');
});

test('a healthy combo does not trigger the conflict cap', () => {
  const m2 = build({ getVerifiedTier: () => ({ tier: 'TRACK', combo_stats: { wr: 62.0, pf: 1.9, n: 12 }, strat_stats: null }) });
  const p = Object.assign({}, SB_F, { strat_fwd_wr: 64.0, strat_fwd_trades: 50 });
  assert.strictEqual(m2._pickEvidenceTier(p).tier, 'PROVEN');
});

test('"Unknown" strategy/system descriptions are suppressed', () => {
  const m2 = build({
    _lookupStrategyDescription: () => 'Unknown',
    _lookupSystemDescription: () => 'Unknown',
  });
  const p = Object.assign({}, SB_F, { strategy: 'unknown', source_system: 'unknown' });
  const out = m2._buildPickJustification(p);
  assert.ok(!/Strategy:<\/b> Unknown/.test(out.html), 'Unknown strategy leaked');
  assert.ok(!/System:<\/b> Unknown/.test(out.html), 'Unknown system leaked');
});

// ---------------------------------------------------------------------------
// Tooltip content
// ---------------------------------------------------------------------------
test('justification contains signal, statistical + fundamental sections', () => {
  const out = mod._buildPickJustification(SB_F);
  assert.ok(out.html.includes('Why now:'), 'missing "Why now" head');
  assert.ok(out.html.includes('Statistical evidence'), 'missing statistical section');
  assert.ok(out.html.includes('Fundamental / structural basis'), 'missing fundamental section');
  assert.ok(out.html.includes('SB=F'), 'missing symbol');
  assert.ok(out.html.includes('SHORT'), 'missing direction');
  assert.ok(out.html.includes('THIN EVIDENCE'), 'missing tier label');
});

test('justification states weak evidence honestly', () => {
  const out = mod._buildPickJustification(SB_F);
  assert.ok(/hypothesis|not statistically significant|not yet significant|unproven/i.test(out.html),
    'honesty footer for a thin pick not present');
});

test('proven pick justification claims corroborated edge', () => {
  const p = Object.assign({}, SB_F, { strat_fwd_wr: 61.5, strat_fwd_trades: 240, forward_validated: true });
  const out = mod._buildPickJustification(p);
  assert.ok(out.html.includes('PROVEN EDGE'));
  assert.ok(/corroborated by a live forward sample/i.test(out.html));
  assert.ok(out.html.includes('n=240'), 'forward n not surfaced');
});

test('non-significant walk-forward is labelled as such', () => {
  const out = mod._buildPickJustification(SB_F);
  assert.ok(out.html.includes('p=0.452 (not significant)'), 'non-significant WF not labelled');
});

test('gate notes surface blocked-asset-class penalty', () => {
  const out = mod._buildPickJustification(SB_F);
  assert.ok(out.html.includes('Gate notes'), 'gate notes missing');
  assert.ok(out.html.includes('blocked_asset_class'), 'penalty text missing');
});

test('reason text is HTML-escaped (no XSS via pick.reason)', () => {
  const evil = Object.assign({}, SB_F, { reason: '<img src=x onerror=alert(1)>' });
  const out = mod._buildPickJustification(evil);
  assert.ok(!out.html.includes('<img src=x'), 'raw <img> was NOT escaped');
  assert.ok(out.html.includes('&lt;img src=x'), 'escaped <img> not found');
});

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------
console.log('\n' + passed + ' passed, ' + failed + ' failed.');
if (failed > 0) process.exit(1);
console.log('All active-pick WHY justification tests passed.');
