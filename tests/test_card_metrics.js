/**
 * Regression tests for the tier / asset-class card math on
 * audit_dashboard/template.html.
 *
 * Locks in the 2026-05-22 stat-validation fix (reports/AUDIT_STAT_VALIDATION_2026-05-22.md):
 * the bold headline is now an honest equal-weight COMPOUNDED return computed by
 * `compoundEwCappedPct`, NOT a naive `totalPnl += capped` sum-of-percentages,
 * which overstated returns ~14x. This test guards against that bug coming back.
 *
 * Run: node tests/test_card_metrics.js
 */
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
// acorn is a devDependency used to validate the extracted function parses.
// If node_modules is not installed, fall back to `new Function` for the
// same syntax check so the test runs without an npm install.
let acorn = null;
try {
  acorn = require('acorn');
} catch (_) {
  acorn = null;
}

const templatePath = path.join(__dirname, '..', 'audit_dashboard', 'template.html');
const templateSrc = fs.readFileSync(templatePath, 'utf8');

// --- pass/fail counter -----------------------------------------------------
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
// 1. Extract the REAL `compoundEwCappedPct` function from template.html.
//    Strategy: find the `function compoundEwCappedPct` token, then walk the
//    source with acorn to find the smallest function declaration that parses
//    cleanly from that offset. Eval the exact source into test scope.
// ---------------------------------------------------------------------------
function extractFunction(src, fnName) {
  const marker = 'function ' + fnName;
  const start = src.indexOf(marker);
  if (start === -1) {
    throw new Error('could not find `' + marker + '` in template.html');
  }
  // Brace-match from the first `{` after the function header.
  const headerEnd = src.indexOf('{', start);
  if (headerEnd === -1) throw new Error('no opening brace for ' + fnName);
  let depth = 0;
  let end = -1;
  for (let i = headerEnd; i < src.length; i++) {
    const c = src[i];
    if (c === '{') depth++;
    else if (c === '}') {
      depth--;
      if (depth === 0) {
        end = i + 1;
        break;
      }
    }
  }
  if (end === -1) throw new Error('unbalanced braces for ' + fnName);
  const fnSrc = src.slice(start, end);
  // Verify it is syntactically valid JS before we eval it.
  if (acorn) {
    acorn.parse(fnSrc, { ecmaVersion: 2020 });
  } else {
    // Fallback when acorn is not installed: `new Function` throws on bad syntax.
    // eslint-disable-next-line no-new-func
    new Function('return (' + fnSrc + ')');
  }
  return fnSrc;
}

const compoundFnSrc = extractFunction(templateSrc, 'compoundEwCappedPct');
// Eval the extracted source so we test the production function verbatim.
// eslint-disable-next-line no-eval
const compoundEwCappedPct = (0, eval)('(' + compoundFnSrc + ')');

// Reference re-implementation — only used to assert the extracted version
// matches the documented algorithm.
function refCompound(picks, capAbs) {
  const cap = capAbs == null ? 500 : capAbs;
  if (!picks || !picks.length) return null;
  const ord = picks
    .slice()
    .sort(
      (a, b) =>
        String(a.timestamp || '').localeCompare(String(b.timestamp || '')) ||
        String(a.symbol || '').localeCompare(String(b.symbol || ''))
    );
  let prod = 1;
  for (let i = 0; i < ord.length; i++) {
    const r = Math.max(-cap, Math.min(cap, Number(ord[i].pnl_pct) || 0)) / 100;
    prod *= 1 + r;
  }
  return Math.round((prod - 1) * 10000) / 100;
}

// Naive (buggy) headline: arithmetic sum of capped per-trade %.
function naiveSum(picks) {
  let total = 0;
  for (const p of picks) {
    total += Math.max(-500, Math.min(500, Number(p.pnl_pct) || 0));
  }
  return total;
}

function picksOf(pcts) {
  return pcts.map((v, i) => ({ pnl_pct: v, timestamp: '2026-05-' + String(10 + i).padStart(2, '0'), symbol: 'S' + i }));
}

// ---------------------------------------------------------------------------
// 2. Function behaviour assertions
// ---------------------------------------------------------------------------

test('extracted function matches the reference algorithm on a mixed set', () => {
  const set = picksOf([1.5, -2.3, 4.1, -0.7, 12.0, -8.8]);
  assert.strictEqual(compoundEwCappedPct(set, 500), refCompound(set, 500));
});

test('core regression: 100 trades of +1% → sum=100% but compound≈170.5%', () => {
  const set = picksOf(Array(100).fill(1));
  const sum = naiveSum(set);
  const comp = compoundEwCappedPct(set, 500);
  assert.strictEqual(Math.round(sum), 100, 'naive sum should be 100%');
  // (1.01^100 - 1)*100 = 170.481...  → rounded to 2dp = 170.48
  assert.strictEqual(comp, 170.48, 'compound should be ~170.5%, got ' + comp);
  assert.notStrictEqual(comp, sum, 'compound MUST differ from naive sum');
  assert.ok(comp > sum, 'for gains, compound > sum');
});

test('compound != naive-sum for any multi-trade set with non-zero returns', () => {
  const sets = [
    picksOf([5, 5, 5]),
    picksOf([10, -3, 7, 2]),
    picksOf([0.25, 0.25, 0.25, 0.25, 0.25]),
    picksOf([-1, -1, -1, -1]),
  ];
  for (const s of sets) {
    assert.notStrictEqual(
      compoundEwCappedPct(s, 500),
      naiveSum(s),
      'compound must not equal naive sum for ' + JSON.stringify(s.map((p) => p.pnl_pct))
    );
  }
});

test('for losses, compound is smaller in magnitude than the naive sum', () => {
  const set = picksOf(Array(50).fill(-2)); // sum = -100%
  const sum = naiveSum(set);
  const comp = compoundEwCappedPct(set, 500);
  assert.ok(sum < 0 && comp < 0, 'both negative');
  // 0.98^50 - 1 = -0.6358 → -63.58%, less severe than -100%
  assert.ok(Math.abs(comp) < Math.abs(sum), 'compound loss magnitude < sum: ' + comp + ' vs ' + sum);
  assert.strictEqual(comp, -63.58);
});

test('single trade: compound == that trade pnl_pct', () => {
  assert.strictEqual(compoundEwCappedPct(picksOf([3.7]), 500), 3.7);
  assert.strictEqual(compoundEwCappedPct(picksOf([-4.25]), 500), -4.25);
  assert.strictEqual(compoundEwCappedPct(picksOf([0]), 500), 0);
});

test('empty / null list → null', () => {
  assert.strictEqual(compoundEwCappedPct([], 500), null);
  assert.strictEqual(compoundEwCappedPct(null, 500), null);
  assert.strictEqual(compoundEwCappedPct(undefined, 500), null);
});

test('±cap clamp: a +99999% pnl_pct is clamped to +cap before compounding', () => {
  const clampedHigh = compoundEwCappedPct([{ pnl_pct: 99999, timestamp: 't1' }], 500);
  const atCap = compoundEwCappedPct([{ pnl_pct: 500, timestamp: 't1' }], 500);
  assert.strictEqual(clampedHigh, atCap, 'huge gain clamps to +500% → 500');
  assert.strictEqual(clampedHigh, 500);

  const clampedLow = compoundEwCappedPct([{ pnl_pct: -99999, timestamp: 't1' }], 500);
  const atCapLow = compoundEwCappedPct([{ pnl_pct: -500, timestamp: 't1' }], 500);
  assert.strictEqual(clampedLow, atCapLow, 'huge loss clamps to -500%');

  // custom cap honoured
  const c50 = compoundEwCappedPct([{ pnl_pct: 12345, timestamp: 't1' }], 50);
  assert.strictEqual(c50, 50, 'cap=50 → result 50');
});

test('product is order-independent (multiplication commutes)', () => {
  const a = compoundEwCappedPct(picksOf([3, -2, 7, -1, 5]), 500);
  const b = compoundEwCappedPct(picksOf([5, -1, 7, -2, 3]), 500);
  assert.strictEqual(a, b, 'same trades, any order → same compound');
});

test('function sorts picks by timestamp (chronological)', () => {
  // Out-of-order timestamps; for a pure product order does not matter, so
  // verify the SORT explicitly: assert the extracted source sorts by timestamp,
  // and that a shuffled-timestamp input yields the same result as sorted input.
  assert.ok(
    /\.sort\(/.test(compoundFnSrc) && /timestamp/.test(compoundFnSrc),
    'function source must sort by timestamp'
  );
  const sorted = picksOf([2, 4, 6, 8]);
  const shuffled = [sorted[2], sorted[0], sorted[3], sorted[1]];
  assert.strictEqual(
    compoundEwCappedPct(shuffled, 500),
    compoundEwCappedPct(sorted, 500),
    'pre-shuffled input must compound to the chronologically-sorted result'
  );
});

test('losing everything: one -100% trade → compound == -100, never below', () => {
  const total = compoundEwCappedPct([{ pnl_pct: -100, timestamp: 't1' }], 500);
  assert.strictEqual(total, -100, 'a -100% trade wipes the book to exactly -100%');

  // A -100% trade followed by gains stays at -100% (prod is already 0).
  const withAfter = compoundEwCappedPct(
    [
      { pnl_pct: -100, timestamp: 't1' },
      { pnl_pct: 50, timestamp: 't2' },
      { pnl_pct: 200, timestamp: 't3' },
    ],
    500
  );
  assert.strictEqual(withAfter, -100, 'once wiped to zero equity, result stays -100%');

  // No clamp at -cap can push it below -100% in normal pnl ranges.
  const manyLosses = compoundEwCappedPct(picksOf(Array(20).fill(-50)), 500);
  assert.ok(manyLosses >= -100, 'compound return never goes below -100%: got ' + manyLosses);
});

// ---------------------------------------------------------------------------
// 3. GUARD: template.html still wires the honest metric.
// ---------------------------------------------------------------------------

test('template.html contains the honest "Compound Return (EW)" label', () => {
  assert.ok(
    templateSrc.includes('Compound Return (EW)'),
    'template.html must show the "Compound Return (EW)" headline'
  );
});

test('compoundEwCappedPct is CALLED in the crypto card render path (not just defined)', () => {
  // The crypto/tier card loop computes `var compoundPnl = compoundEwCappedPct(catClosed, 500);`
  assert.ok(
    /compoundPnl\s*=\s*compoundEwCappedPct\(\s*catClosed/.test(templateSrc),
    'crypto card must call compoundEwCappedPct(catClosed, ...)'
  );
  // Count call sites: definition + non-crypto card + crypto card = at least 2 calls.
  const calls = (templateSrc.match(/compoundEwCappedPct\(/g) || []).length;
  assert.ok(calls >= 3, 'expected the function definition plus >=2 call sites, found ' + calls);
});

test('old bug pattern gone: bold headline is NOT `totalPnl + unrealizedPnl`', () => {
  // The pre-fix bug folded unrealized mark-to-market into the "realized" headline
  // via `overallPnl = totalPnl + unrealizedPnl`. That assignment must be gone.
  assert.ok(
    !/totalPnl\s*\+\s*unrealizedPnl/.test(templateSrc),
    'template.html must not add unrealizedPnl into the realized headline'
  );
  assert.ok(
    !/\boverallPnl\b/.test(templateSrc),
    'the buggy `overallPnl` headline variable must be removed'
  );
});

test('the raw sum is relabeled "Σ Trade % (sum)", no longer the bold headline', () => {
  // &Sigma; is the HTML entity used in the template for the Σ symbol.
  assert.ok(
    templateSrc.includes('&Sigma; Trade % (sum)') || templateSrc.includes('Σ Trade % (sum)'),
    'the naive sum row must be labeled "Σ Trade % (sum)"'
  );
});

// ---------------------------------------------------------------------------
console.log('\n' + passed + ' passed, ' + failed + ' failed.');
if (failed > 0) {
  process.exit(1);
}
console.log('All card-metrics regression tests passed.');
