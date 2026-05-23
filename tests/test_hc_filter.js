/**
 * Regression tests for passesHighConvictionPick v3 (audit_dashboard/hc_filter.js).
 * Run: node tests/test_hc_filter.js
 */
'use strict';

const assert = require('assert');
const path = require('path');
const hcPath = path.join(__dirname, '..', 'audit_dashboard', 'hc_filter.js');
const { passesHighConvictionPick, filterHighConvictionOrdered, resetHcGateParamsCache } = require(
  hcPath
);

/** v3: score drives gate 1 (not elite). Min score 50 or 40–49 with trust >= 8. */
function basePick(overrides) {
  return Object.assign(
    {
      symbol: 'BTCUSDT',
      asset_class: 'CRYPTO',
      strategy: 'keltner',
      trust_score: 6,
      strat_fwd_wr: 0.55,
      strat_fwd_trades: 10,
      elite_score: 0,
      trust_tier: 'PROVEN',
      direction: 'LONG',
      regime: 'neutral',
      confidence: 0.5,
      score: 55,
    },
    overrides || {}
  );
}

function test(name, fn) {
  try {
    fn();
    console.log('ok —', name);
  } catch (e) {
    console.error('FAIL —', name);
    throw e;
  }
}

test('v3 PROVEN pick passes all gates', () => {
  assert.strictEqual(
    passesHighConvictionPick(
      basePick({
        trust_tier: 'PROVEN',
      })
    ),
    true
  );
});

test('SANDBOX trust tier blocked', () => {
  assert.strictEqual(
    passesHighConvictionPick(
      basePick({
        trust_tier: 'SANDBOX',
      })
    ),
    false
  );
});

test('fwdTrades < 5 fails', () => {
  assert.strictEqual(
    passesHighConvictionPick(
      basePick({
        strat_fwd_trades: 3,
        trust_tier: 'PROVEN',
      })
    ),
    false
  );
});

test('score below absolute floor fails', () => {
  assert.strictEqual(
    passesHighConvictionPick(
      basePick({
        score: 35,
        trust_tier: 'PROVEN',
      })
    ),
    false
  );
});

test('crypto DOTUSDT fear_greed passes (no source_systems)', () => {
  assert.strictEqual(
    passesHighConvictionPick(
      basePick({
        symbol: 'DOTUSDT',
        strategy: 'st_fear_greed_contrarian_v1',
      })
    ),
    true
  );
});

test('EQUITY NVDA passes same v3 gates', () => {
  assert.strictEqual(
    passesHighConvictionPick(
      basePick({
        symbol: 'NVDA',
        asset_class: 'EQUITY',
        strategy: 'other',
      })
    ),
    true
  );
});

test('SHORT in bull without PROVEN fails', () => {
  assert.strictEqual(
    passesHighConvictionPick(
      basePick({
        direction: 'SHORT',
        regime: 'strong_bull',
        trust_tier: 'DEVELOPING',
      })
    ),
    false
  );
});

test('overconfidence high conf + low trades fails', () => {
  assert.strictEqual(
    passesHighConvictionPick(
      basePick({
        confidence: 0.95,
        strat_fwd_trades: 10,
        trust_tier: 'PROVEN',
      })
    ),
    false
  );
});

test('wf_verdict FAILING blocked', () => {
  assert.strictEqual(
    passesHighConvictionPick(
      basePick({
        wf_verdict: 'FAILING',
        trust_tier: 'PROVEN',
      })
    ),
    false
  );
});

test('independentGroupsMin=3 when source_systems present', () => {
  global.window = { __HC_GATE_PARAMS__: { independentGroupsMin: 3 } };
  resetHcGateParamsCache();
  assert.strictEqual(
    passesHighConvictionPick(
      basePick({
        source_systems: 'alpha_engine, luxalgo_filters, regime_terminal',
      })
    ),
    true
  );
  assert.strictEqual(
    passesHighConvictionPick(
      basePick({
        source_systems: 'alpha_engine, luxalgo_filters',
      })
    ),
    false
  );
  delete global.window;
  resetHcGateParamsCache();
});

test('stamped tier A path bypasses Gate 8 independent consensus when contract matches', () => {
  global.window = { __HC_GATE_PARAMS__: { independentGroupsMin: 3, tierSABypassIndependentConsensus: true } };
  resetHcGateParamsCache();
  assert.strictEqual(
    passesHighConvictionPick(
      basePick({
        symbol: 'LINKUSDT',
        strategy: 'st_fear_greed_contrarian_v1',
        hf_conviction_tier: 'A',
        source_systems: 'alpha_engine',
      })
    ),
    true
  );
  delete global.window;
  resetHcGateParamsCache();
});

test('stamped tier B path still enforces Gate 8 independent consensus', () => {
  global.window = { __HC_GATE_PARAMS__: { independentGroupsMin: 3, tierSABypassIndependentConsensus: true } };
  resetHcGateParamsCache();
  assert.strictEqual(
    passesHighConvictionPick(
      basePick({
        symbol: 'BTCUSDT',
        hf_conviction_tier: 'B',
        source_systems: 'alpha_engine',
      })
    ),
    false
  );
  delete global.window;
  resetHcGateParamsCache();
});

test('stamped tier B bypass reason is accepted even when symbol is not in legacy contract list', () => {
  assert.strictEqual(
    passesHighConvictionPick(
      basePick({
        symbol: 'ARBUSDT',
        hf_conviction_tier: 'B',
        hf_conviction_reasons: ['bypass_tier_b_3of5_criteria_conf0.82'],
      })
    ),
    true
  );
});

test('GATE 9: second correlated LONG blocked after first passes (registry)', () => {
  globalThis._hcPassedSyms = {};
  const eth = basePick({ symbol: 'ETHUSDT', trust_tier: 'PROVEN' });
  const sol = basePick({ symbol: 'SOLUSDT', trust_tier: 'PROVEN' });
  assert.strictEqual(passesHighConvictionPick(eth), true);
  globalThis._hcPassedSyms.ETHUSDT = 'LONG';
  assert.strictEqual(passesHighConvictionPick(sol), false);
  delete globalThis._hcPassedSyms;
});

test('GATE 9: opposite direction on neighbor does not block', () => {
  globalThis._hcPassedSyms = {};
  const eth = basePick({ symbol: 'ETHUSDT', trust_tier: 'PROVEN' });
  const solShort = basePick({
    symbol: 'SOLUSDT',
    trust_tier: 'PROVEN',
    direction: 'SHORT',
    regime: 'neutral',
  });
  assert.strictEqual(passesHighConvictionPick(eth), true);
  globalThis._hcPassedSyms.ETHUSDT = 'LONG';
  assert.strictEqual(passesHighConvictionPick(solShort), true);
  delete globalThis._hcPassedSyms;
});

test('filterHighConvictionOrdered drops second correlated same-direction pick', () => {
  const out = filterHighConvictionOrdered([
    basePick({ symbol: 'ETHUSDT', trust_tier: 'PROVEN' }),
    basePick({ symbol: 'SOLUSDT', trust_tier: 'PROVEN' }),
  ]);
  assert.strictEqual(out.length, 1);
  assert.strictEqual(out[0].symbol, 'ETHUSDT');
});

// ---------------------------------------------------------------------------
// FOREX auto-relax + Gate 7b exception + per-asset-class threshold tests
// (2026-04-15: BUG FIX regression tests)
// ---------------------------------------------------------------------------

function forexBasePick(overrides) {
  return Object.assign(
    {
      symbol: 'EURUSD=X',
      asset_class: 'FOREX',
      strategy: 'forex_rsi2',
      trust_score: 5,
      strat_fwd_wr: 0.60,
      strat_fwd_trades: 25,
      elite_score: 0,
      trust_tier: 'PROVEN',
      direction: 'LONG',
      regime: 'neutral',
      confidence: 0.5,
      score: 55,
    },
    overrides || {}
  );
}

test('FOREX: fwdN >= 20 needs FWD WR >= 55%', () => {
  assert.strictEqual(
    passesHighConvictionPick(forexBasePick({ strat_fwd_wr: 0.55, strat_fwd_trades: 25 })),
    true
  );
  assert.strictEqual(
    passesHighConvictionPick(forexBasePick({ strat_fwd_wr: 0.54, strat_fwd_trades: 25 })),
    false
  );
});

test('FOREX auto-relax: fwdN < 20 lowers FWD WR threshold from 55% to 50%', () => {
  // fwdN=15, FWD WR=52%: would fail at 55% but passes at relaxed 50%
  assert.strictEqual(
    passesHighConvictionPick(forexBasePick({ strat_fwd_wr: 0.52, strat_fwd_trades: 15 })),
    true
  );
  // fwdN=15, FWD WR=49%: fails even relaxed 50% threshold
  assert.strictEqual(
    passesHighConvictionPick(forexBasePick({ strat_fwd_wr: 0.49, strat_fwd_trades: 15 })),
    false
  );
  // fwdN=19 (boundary -1): still relaxed
  assert.strictEqual(
    passesHighConvictionPick(forexBasePick({ strat_fwd_wr: 0.51, strat_fwd_trades: 19 })),
    true
  );
  // fwdN=20 (boundary): normal threshold applies, 51% fails
  assert.strictEqual(
    passesHighConvictionPick(forexBasePick({ strat_fwd_wr: 0.51, strat_fwd_trades: 20 })),
    false
  );
});

test('FOREX auto-relax bypasses Gate 7b (confidence 0.85-0.95 + fwdN < 30)', () => {
  // fwdN=15, confidence=0.88: auto-relax active, Gate 7b skipped → PASS
  assert.strictEqual(
    passesHighConvictionPick(
      forexBasePick({ strat_fwd_trades: 15, confidence: 0.88, strat_fwd_wr: 0.55 })
    ),
    true
  );
  // Same but fwdN=25 (auto-relax NOT active): Gate 7b applies, 25 < 30 → FAIL
  assert.strictEqual(
    passesHighConvictionPick(
      forexBasePick({ strat_fwd_trades: 25, confidence: 0.88, strat_fwd_wr: 0.55 })
    ),
    false
  );
});

test('Gate 7b still applies to CRYPTO (no FOREX auto-relax)', () => {
  // Clear any leftover correlation registry from previous tests
  if (typeof globalThis !== 'undefined' && globalThis._hcPassedSyms) {
    delete globalThis._hcPassedSyms;
  }
  // CRYPTO: confidence=0.88, fwdN=15 → Gate 7b rejects
  assert.strictEqual(
    passesHighConvictionPick(
      basePick({ confidence: 0.88, strat_fwd_trades: 15, trust_tier: 'PROVEN' })
    ),
    false
  );
  // CRYPTO: confidence=0.88, fwdN=35 → Gate 7b passes
  assert.strictEqual(
    passesHighConvictionPick(
      basePick({ confidence: 0.88, strat_fwd_trades: 35, trust_tier: 'PROVEN' })
    ),
    true
  );
});

test('Per-asset-class score floors: CRYPTO >= 55, EQUITY >= 50, FOREX >= 40', () => {
  // CRYPTO score=54 fails
  assert.strictEqual(passesHighConvictionPick(basePick({ score: 54, trust_tier: 'PROVEN' })), false);
  // CRYPTO score=55 passes
  assert.strictEqual(passesHighConvictionPick(basePick({ score: 55, trust_tier: 'PROVEN' })), true);
  // EQUITY score=49 fails
  assert.strictEqual(
    passesHighConvictionPick(basePick({ asset_class: 'EQUITY', score: 49, trust_tier: 'PROVEN' })),
    false
  );
  // EQUITY score=50 passes
  assert.strictEqual(
    passesHighConvictionPick(basePick({ asset_class: 'EQUITY', score: 50, trust_tier: 'PROVEN' })),
    true
  );
  // FOREX score=39 fails
  assert.strictEqual(
    passesHighConvictionPick(forexBasePick({ score: 39, trust_tier: 'PROVEN' })),
    false
  );    // FOREX score=40 passes (needs trust_score >= 8 to bypass Gate 2: score < 50 + trust < 8)
  assert.strictEqual(
    passesHighConvictionPick(forexBasePick({ score: 40, strat_fwd_trades: 25, trust_score: 8, trust_tier: 'PROVEN' })),
    true
  );
});

test('Per-asset-class FWD WR floors: CRYPTO >= 45%, EQUITY >= 55%, FOREX >= 55%', () => {
  // CRYPTO FWD WR=44% fails
  assert.strictEqual(
    passesHighConvictionPick(basePick({ strat_fwd_wr: 0.44, trust_tier: 'PROVEN' })),
    false
  );
  // CRYPTO FWD WR=45% passes
  assert.strictEqual(
    passesHighConvictionPick(basePick({ strat_fwd_wr: 0.45, trust_tier: 'PROVEN' })),
    true
  );
  // EQUITY FWD WR=54% fails
  assert.strictEqual(
    passesHighConvictionPick(
      basePick({ asset_class: 'EQUITY', strat_fwd_wr: 0.54, trust_tier: 'PROVEN' })
    ),
    false
  );
  // EQUITY FWD WR=55% passes
  assert.strictEqual(
    passesHighConvictionPick(
      basePick({ asset_class: 'EQUITY', strat_fwd_wr: 0.55, trust_tier: 'PROVEN' })
    ),
    true
  );
});

test('FOREX auto-relax does NOT bypass Gate 7a (extreme confidence)', () => {
  // Gate 7a rejects when confidence > 0.95 AND fwdN < 30.
  // fwdN=15, confidence=0.96: auto-relax active but Gate 7a still rejects (0.96 > 0.95 AND 15 < 30)
  assert.strictEqual(
    passesHighConvictionPick(
      forexBasePick({ strat_fwd_trades: 15, confidence: 0.96, strat_fwd_wr: 0.55 })
    ),
    false
  );
  // fwdN=25, confidence=0.96: no auto-relax (25 >= 20), Gate 7a rejects (0.96 > 0.95 AND 25 < 30)
  assert.strictEqual(
    passesHighConvictionPick(
      forexBasePick({ strat_fwd_trades: 25, confidence: 0.96, strat_fwd_wr: 0.55 })
    ),
    false
  );
  // fwdN=35, confidence=0.96: Gate 7a does NOT reject (35 >= 30), passes
  assert.strictEqual(
    passesHighConvictionPick(
      forexBasePick({ strat_fwd_trades: 35, confidence: 0.96, strat_fwd_wr: 0.55 })
    ),
    true
  );
});

test('FOREX Gate 7b upper boundary: fwdN=30 passes, fwdN=29 fails', () => {
  // fwdN=30, confidence=0.88: meets Gate 7b threshold (30 >= 30) → PASS
  assert.strictEqual(
    passesHighConvictionPick(
      forexBasePick({ strat_fwd_trades: 30, confidence: 0.88, strat_fwd_wr: 0.55 })
    ),
    true
  );
  // fwdN=29, confidence=0.88: fails Gate 7b (29 < 30) and no auto-relax (29 >= 20)
  assert.strictEqual(
    passesHighConvictionPick(
      forexBasePick({ strat_fwd_trades: 29, confidence: 0.88, strat_fwd_wr: 0.55 })
    ),
    false
  );
});

test('Config override: forexRelaxedWRMinPct can be changed from default 50', () => {
  // Override forexRelaxedWRMinPct to 45% via global config
  global.window = { __HC_GATE_PARAMS__: { forexRelaxedWRMinPct: 45 } };
  resetHcGateParamsCache();
  // fwdN=15, FWD WR=46%: passes with relaxed 45% threshold
  assert.strictEqual(
    passesHighConvictionPick(
      forexBasePick({ strat_fwd_wr: 0.46, strat_fwd_trades: 15 })
    ),
    true
  );
  // fwdN=15, FWD WR=44%: fails even relaxed 45% threshold
  assert.strictEqual(
    passesHighConvictionPick(
      forexBasePick({ strat_fwd_wr: 0.44, strat_fwd_trades: 15 })
    ),
    false
  );
  delete global.window;
  resetHcGateParamsCache();
});

console.log('\nAll HC filter regression tests passed.');
