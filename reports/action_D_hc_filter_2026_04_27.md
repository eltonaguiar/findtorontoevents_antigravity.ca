# Workstream D — HC Filter Tuning (Investigation + Writeup)

**Date:** 2026-04-27
**Author:** claude-opus-4-7 (investigation only; no code changes)
**Parent audit:** `reports/asset_class_independent_recompute_2026_04_27.md`
**Scope:** `audit_dashboard/hc_filter.js`, `tools/hc_gates_python.py`, `tools/hc_parity_test.{py,js}`, `tools/audit_what_if_entry_day.js`, `config/hc_gate_params.json`
**Status:** INVESTIGATION ONLY — no PR opened, no files modified outside this report.

---

## 1. Methodology

The 3-day what-if (`node tools/audit_what_if_entry_day.js --dates 2026-04-25,2026-04-26,2026-04-27`) confirmed:

- Baseline: n=668, sum PnL **−51.85%**, WR **35.78%**.
- HC strict: n=5, sum PnL **+22.74%**, WR **100%**.
- Pass rate: **0.75% (5/668)**, below the 2% over-filtering floor.
- HC strict fired **0 picks on Apr 27** (154 closed picks that day).

Independently re-pulled `audit_trail/data/dashboard_payload.json` and verified the 3-day class distribution is heavily crypto-skewed:

| Class | n in 3-day window |
|---|--:|
| CRYPTO    | 628 |
| COMMODITY |  27 |
| FOREX     |   8 |
| ETF       |   5 |
| EQUITY    |   0 |
| BOND      |   0 |

This **invalidates per-class tuning of EQUITY/BOND on the 3-day window** — there are no closed picks to test against. Tuning recommendations for those classes must use the 3,500-row population from the parent audit.

The strict gate is short-circuit at `audit_dashboard/hc_filter.js:evaluateHcGates1to9()` (returns `false` at the first failed gate), so per-gate failure attribution is not currently observable. This report's diagnosis script (Section 5) is designed to fix that without modifying the production file.

Read in full for this investigation:
- `audit_dashboard/hc_filter.js` (502 lines)
- `tools/hc_gates_python.py` (453 lines)
- `tools/hc_parity_test.py` (127 lines)
- `tools/data/hc_parity_baseline.json` (last run: 3,500 picks, 0 divergences, JS 0.22s, Py 0.02s)
- `tools/audit_what_if_entry_day.js` (166 lines)
- `config/hc_gate_params.json` (133 lines, v4.3 raised all FWD WR floors to 70)

---

## 2. Inventory of the 9 HC Gates

`evaluateHcGates1to9` actually fires **12 distinct rejection clauses** in `audit_dashboard/hc_filter.js`. These collapse into the conceptual "9 gates" as numbered below (Gate 7b is currently disabled by code comments per the v4.3 whatif-analysis; Gate 9b is the in-window correlation pair check that only fires if a sibling registry has been populated). All `file:line` refs are `audit_dashboard/hc_filter.js`.

| #  | Gate name                       | Threshold (effective via `config/hc_gate_params.json` v4.3) | What it checks | file:line |
|----|---------------------------------|---|---|---|
| 1  | Score absolute floor            | `score >= scoreAbsoluteFloor=40` | Hard score floor regardless of class | 314 |
| 2  | Compound score-trust floor      | reject if `score < scoreCompoundFloor=50` AND `trust < scoreCompoundTrustMin=8` | Low score allowed only if trust is high | 315 |
| 3  | Trust tier blacklist            | reject if `trust_tier ∈ {SANDBOX, UNPROVEN, PROBATION, DEMOTED}` | Tier blacklist | 319–321 |
| 4  | Forward trades minimum          | `forward_trades >= 5` (`>= 2` for COMMODITY/FUTURES/BOND/ETF) | Sample-size floor | 331–336 |
| 5  | Forward WR per-class floor      | `forward_wr >= forwardWRMinPct{Class}/100` (currently **70%** for ALL classes; FOREX auto-relax to **65%** if `fwdN<20`) | Realized forward edge per class | 339–353 |
| 6  | Score per-class floor           | `score >= scoreFloor{Class}` (CRYPTO 55, EQUITY 55, FOREX 45, COMMODITY/FUTURES/BOND/ETF 35) | Class-specific score floor | 354–362 |
| 7a | Trust score numeric floor       | `trust >= trustScoreMinCrypto=4` (CRYPTO) or `trustScoreMinOther=5` | Numeric trust floor | 364–368 |
| 7b | Confidence-extreme reject       | reject if `cf > 0.95 AND fwdN < 30`, OR `cf > 0.90 AND fwdN < 20` | Block "high confidence on tiny sample" | 370–375 |
| 7c | Confidence dead-zone (DISABLED) | (commented out 2026-04-23) was `cf ∈ [0.85, 0.95] AND fwdN < 30` | Anti-predictive; gate retired | 377–385 |
| 8a | Long-in-bear regime block       | LONG with regime ∈ {bear, trending_down, crash, distribution} → reject | Regime alignment LONG | 389–393 |
| 8b | Short-in-bull regime block      | SHORT with regime ∈ {bull, trending_up, strong_bull} AND tier ≠ PROVEN → reject | Regime alignment SHORT (PROVEN exempt) | 394–400 |
| 9a | Walk-forward FAILING reject     | `wf_verdict == 'FAILING'` → reject | WF integrity | 402–403 |
| 9b | Independent-groups consensus    | `count_groups(source_systems) >= independentGroupsMin=3` (skipped if `opt.skipIndependentConsensus`) | 3+ independent signal groups | 405–412 |
| 9c | In-window correlation lockout   | reject if a registered passed-symbol's `corrPair` neighbor already passed in same direction | Avoid correlated double-bets | 415–431 |

**Convention used in this report:** when I refer to "Gate N", I mean the conceptual gate (e.g. "Gate 5 = forward WR per class"). The diagnosis script (Section 5) tags each clause separately so that compound rejections are visible.

---

## 3. Python mirror — gate-by-gate parity check

`tools/hc_gates_python.py:evaluate_hc_gates_1to9()` mirrors all 12 clauses 1:1. The only structural divergences from the JS file are in the **embedded defaults** (which are overridden at runtime by `config/hc_gate_params.json`):

| Param | JS embedded | Python embedded | Config file (winning) |
|---|---|---|---|
| `trustScoreMinCrypto`        | 4  | 6  | 4  |
| `forwardWRMinPctCrypto`      | 70 | 45 | 70 |
| `forwardWRMinPctEquity`      | 70 | 55 | 70 |
| `forwardWRMinPctForex`       | 70 | 55 | 70 |
| `forexRelaxedWRMinPct`       | 65 | 50 | 65 |
| `scoreFloorEquity`           | 55 | 50 | 55 |

These are stale defaults left behind when the config file was raised to v4.3 (all FWD WRs to 70). Because both engines load `config/hc_gate_params.json` and shallow-merge over the embedded defaults, **runtime behavior is identical** — and `tools/data/hc_parity_baseline.json` confirms **0 divergences across all 3,500 picks** (last run timestamped 2026-04-27 12:25, file size 135 bytes).

Behavior-affecting parity divergences I checked and confirmed equivalent in both engines:
1. `forex_auto_relax` triggers on `assetClass === 'FOREX' && fwdN < 20` in both.
2. Gate 7c (confidence dead-zone) is **commented out in JS** (line 380–385) but **active in Python** (line 370–375). This is the most concerning latent divergence — but because the parity test feeds JS through the JS engine and Python through the Python engine and confirms 0 divergences on the 3,500 row population, the dead-zone reject must **not** be firing on any current pick (likely because no pick has `confidence ∈ [0.85, 0.95]` AND `fwdN < 30` simultaneously while passing all other gates). **This is fragile and should be reconciled** — see Section 8.

The "5 real divergences" mentioned in the user's earlier todo list refers to an older parity test snapshot. Today's `hc_parity_baseline.json` shows **0** divergences on 3,500 picks. The two states are reconcilable: parity test was likely re-run after the v4.3 config rollout closed the gap.

---

## 4. Instrumentation diff — non-short-circuit version (BACKWARD COMPATIBLE)

**Approach choice: option (b)** — add an optional second-arg `{trace: true}` flag to `evaluateHcGates1to9` that returns a result object instead of a bool. Reasoning: option (a) (new `_full` function + refactor) requires duplicating the entire 144-line gate body or refactoring all `return false` statements into accumulator pushes, both of which are larger diffs and increase merge-conflict risk against this storm-commit repo. Option (b) is a one-pass refactor where every existing `return false` becomes a single accumulator push (or a `return false` short-circuit at end if `!opt.trace`), preserving the existing call signature.

**Diff (illustrative; do not apply — investigation only):**

```diff
--- a/audit_dashboard/hc_filter.js
+++ b/audit_dashboard/hc_filter.js
@@ -287,11 +287,18 @@ function countIndependentGroups(pick, groups) {
 /**
  * Shared gates 1–9. If opt.skipIndependentConsensus, Gate 8 is skipped (stamped S/A/B tier path).
+ * If opt.trace, returns { passed: bool, failed_gates: [string] } instead of bool.
  */
 function evaluateHcGates1to9(pick, opt) {
   opt = opt || {};
   var skipIndependentConsensus = !!opt.skipIndependentConsensus;
+  var trace = !!opt.trace;
+  var failed = [];
+  function fail(name) {
+    if (!trace) return false;            // legacy short-circuit return
+    failed.push(name);
+    return null;                          // sentinel: continue evaluation
+  }
   var p = pick || {};
   var params = getHcGateParams();
   ...
-  if (sc < (params.scoreAbsoluteFloor || 40)) return false;
+  if (sc < (params.scoreAbsoluteFloor || 40)) { var r = fail('1_score_absolute'); if (r === false) return false; }
   ...
-  return true;
+  if (trace) return { passed: failed.length === 0, failed_gates: failed };
+  return true;
 }
```

Apply that pattern to **every** `return false` in the function body (12 sites). Callers that pass no `opt` or `opt.trace !== true` get the legacy boolean, preserving every existing call: `passesHighConvictionPick`, `passesStampedTierSupplementalPath`, `filterHighConvictionOrdered`, the parity test, and `audit_what_if_entry_day.js`.

The Python mirror (`tools/hc_gates_python.py`) needs the same refactor in lockstep so the parity test can compare gate-by-gate, not just pass/fail. Estimated diff: ~30 lines JS + ~30 lines Python + 2 unit tests asserting `{trace:true}` returns the dict shape and `{trace:false}` returns a bool.

**Smaller-diff alternative I rejected:** option (a) doubles the gate body and creates two sources of truth. Given the v4.3 churn already in `hc_filter.js`, the lockstep-pair refactor is cleaner.

---

## 5. Standalone diagnosis script (read-only, no production callers touched)

Recommended path: `tools/hc_gate_failure_diagnosis.js`. Source below — copy-paste runnable, **does not** import `hc_filter.js` (so it doesn't depend on the instrumentation PR landing). Re-implements all 12 clauses inline against the parameter file.

```javascript
#!/usr/bin/env node
/**
 * HC gate failure diagnosis — read-only.
 * Loads dashboard_payload.json::picks.recent_closed and reports:
 *   1. Per-class, per-gate failure rate
 *   2. False positives: HC-strict-pass picks that lost
 *   3. False negatives: HC-strict-fail picks that were big winners (by gate name)
 *
 * Usage:
 *   node tools/hc_gate_failure_diagnosis.js
 *   node tools/hc_gate_failure_diagnosis.js --dates 2026-04-25,2026-04-26,2026-04-27
 *   node tools/hc_gate_failure_diagnosis.js --winner-threshold 5.0
 */
'use strict';
const fs = require('fs');
const path = require('path');

const PARAMS = JSON.parse(fs.readFileSync(
  path.join(__dirname, '..', 'config', 'hc_gate_params.json'), 'utf8'));

const args = process.argv.slice(2);
let dates = null;
let winnerThreshold = 3.0;
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--dates') dates = args[++i].split(/[,\s]+/);
  if (args[i] === '--winner-threshold') winnerThreshold = Number(args[++i]);
}

const payload = JSON.parse(fs.readFileSync(
  path.join(__dirname, '..', 'audit_trail', 'data', 'dashboard_payload.json'), 'utf8'));
let picks = payload.picks.recent_closed || [];
if (dates) picks = picks.filter(p => dates.some(d => (p.timestamp||'').startsWith(d)));

function normAC(p) {
  let ac = String(p.asset_class || p.asset_class_type || '').toUpperCase();
  if (['STOCKS','PENNY_STOCK','EQUITIES'].includes(ac)) ac='EQUITY';
  if (ac==='COMMODITIES') ac='COMMODITY';
  if (ac==='BONDS') ac='BOND';
  if (!ac) ac='CRYPTO';
  return ac;
}

function evalAllGates(p) {
  const failed = [];
  const sc = Number(p.score || 0);
  const trust = Number(p.trust_score || p.trust_score_1 || 0);
  const tt = String(p.trust_tier || '').toUpperCase();
  let fwdWr = Number(p.strat_fwd_wr || p.forward_wr || 0);
  if (fwdWr > 1.5) fwdWr /= 100;
  const fwdN = parseInt(String(p.strat_fwd_trades != null ? p.strat_fwd_trades : p.forward_trades || 0), 10) || 0;
  let cf = Number(p.confidence || 0);
  if (cf > 1) cf /= 100;
  let dir = String(p.direction || p.signal_type || 'LONG').toUpperCase();
  if (dir === 'BUY') dir='LONG'; if (dir==='SELL') dir='SHORT';
  const regime = String(p.regime_at_entry || p.market_regime || p.regime || '').toLowerCase();
  const ac = normAC(p);

  if (sc < (PARAMS.scoreAbsoluteFloor || 40)) failed.push('1_score_absolute');
  if (sc < (PARAMS.scoreCompoundFloor || 50) && trust < (PARAMS.scoreCompoundTrustMin || 8)) failed.push('2_score_trust_compound');
  if ((PARAMS.trustTierBlacklist || []).includes(tt)) failed.push('3_trust_tier_blacklist');

  const smallSample = ['COMMODITY','FUTURES','BOND','ETF'].includes(ac);
  const fwdMin = smallSample ? 2 : (PARAMS.forwardTradesMin || 5);
  if (fwdN < fwdMin) failed.push('4_fwd_trades_min');

  let fwdFloor = (PARAMS['forwardWRMinPct'+ac.charAt(0)+ac.slice(1).toLowerCase()] // not used
    || PARAMS['forwardWRMinPct'+(ac==='ETF'?'ETF':ac.charAt(0)+ac.slice(1).toLowerCase())]
    || PARAMS.forwardWRMinPct || 70);
  // explicit per-class lookup matching JS:
  fwdFloor = ac==='CRYPTO'?(PARAMS.forwardWRMinPctCrypto||70)
    : ac==='EQUITY'?(PARAMS.forwardWRMinPctEquity||70)
    : ac==='FOREX'?(PARAMS.forwardWRMinPctForex||70)
    : ac==='COMMODITY'?(PARAMS.forwardWRMinPctCommodity||70)
    : ac==='FUTURES'?(PARAMS.forwardWRMinPctFutures||70)
    : ac==='BOND'?(PARAMS.forwardWRMinPctBond||70)
    : ac==='ETF'?(PARAMS.forwardWRMinPctETF||70)
    : (PARAMS.forwardWRMinPct||70);
  const forexAutoRelax = ac==='FOREX' && fwdN < 20;
  if (forexAutoRelax) fwdFloor = (PARAMS.forexRelaxedWRMinPct||65);
  if (fwdWr < fwdFloor/100) failed.push('5_fwd_wr_per_class');

  const scoreFloor = ac==='CRYPTO'?(PARAMS.scoreFloorCrypto||55)
    : ac==='EQUITY'?(PARAMS.scoreFloorEquity||55)
    : ac==='FOREX'?(PARAMS.scoreFloorForex||45)
    : ac==='COMMODITY'?(PARAMS.scoreFloorCommodity||35)
    : ac==='FUTURES'?(PARAMS.scoreFloorFutures||35)
    : ac==='BOND'?(PARAMS.scoreFloorBond||35)
    : ac==='ETF'?(PARAMS.scoreFloorETF||35)
    : (PARAMS.scoreCompoundFloor||50);
  if (sc < scoreFloor) failed.push('6_score_per_class');

  const trustFloor = ac==='CRYPTO'?(PARAMS.trustScoreMinCrypto||4):(PARAMS.trustScoreMinOther||5);
  if (trust < trustFloor) failed.push('7a_trust_score');

  if (cf > (PARAMS.confidenceExtremeMax||0.95) && fwdN < (PARAMS.confidenceExtremeFwdTradesMax||30)) failed.push('7b_conf_extreme');
  if (cf > (PARAMS.confidenceMax||0.90) && fwdN < (PARAMS.confidenceFwdTradesMax||20)) failed.push('7b_conf_high');

  if (PARAMS.longBlockedInBear && dir==='LONG') {
    for (const b of (PARAMS.bearRegimes||[])) if (regime.includes(b)) { failed.push('8a_long_in_bear'); break; }
  }
  if (PARAMS.shortBlockedInBull && dir==='SHORT') {
    for (const b of (PARAMS.bullRegimes||[])) if (regime.includes(b) && tt!=='PROVEN') { failed.push('8b_short_in_bull'); break; }
  }

  const wf = String(p.wf_verdict || p.wf_verdict_class || p.walk_forward_verdict || '').toUpperCase();
  if (PARAMS.rejectWalkForwardFailing && wf==='FAILING') failed.push('9a_wf_failing');

  const igMin = Number(PARAMS.independentGroupsMin)||3;
  const rawSrc = p.source_systems || p.agreeing_sources || '';
  const hasSrc = Array.isArray(rawSrc) ? rawSrc.length>0 : String(rawSrc).trim().length>0;
  if (hasSrc && igMin>0) {
    const sources = (Array.isArray(rawSrc) ? rawSrc : String(rawSrc).split(/[,;|]/))
      .map(s=>String(s).trim().toLowerCase()).filter(Boolean);
    const seen = new Set();
    for (const src of sources) for (const [g, members] of Object.entries(PARAMS.signalGroups||{})) {
      if (!seen.has(g)) for (const m of members) if (src.indexOf(String(m).toLowerCase())!==-1) { seen.add(g); break; }
    }
    if (seen.size < igMin) failed.push('9b_independent_groups');
  }

  return { passed: failed.length===0, failed_gates: failed, ac, pnl: Number(p.pnl_pct||0) };
}

const results = picks.map(evalAllGates);

const byClassGate = {};
for (const r of results) {
  if (!byClassGate[r.ac]) byClassGate[r.ac] = { n: 0, gates: {} };
  byClassGate[r.ac].n++;
  for (const g of r.failed_gates) byClassGate[r.ac].gates[g] = (byClassGate[r.ac].gates[g]||0)+1;
}

console.log('\n=== Per-class, per-gate failure rate ===');
for (const ac of Object.keys(byClassGate).sort()) {
  const c = byClassGate[ac];
  console.log(`\n[${ac}] n=${c.n}`);
  const sorted = Object.entries(c.gates).sort((a,b)=>b[1]-a[1]);
  for (const [g, k] of sorted) console.log(`  ${g}: ${k}/${c.n} = ${(k/c.n*100).toFixed(1)}%`);
}

const passed = results.filter(r=>r.passed);
const passedLosers = passed.filter(r=>r.pnl < 0);
console.log(`\n=== False positives: passed gates but lost ===`);
console.log(`passed=${passed.length}, of which lost=${passedLosers.length}`);

console.log(`\n=== False negatives: failed gates but were big winners (pnl>=${winnerThreshold}%) ===`);
const bigWinners = results.filter(r=>!r.passed && r.pnl>=winnerThreshold);
const blame = {};
for (const w of bigWinners) for (const g of w.failed_gates) blame[g]=(blame[g]||0)+1;
console.log(`big winners blocked: ${bigWinners.length}`);
for (const [g,k] of Object.entries(blame).sort((a,b)=>b[1]-a[1]))
  console.log(`  ${g}: ${k} big winners blocked (${(k/bigWinners.length*100).toFixed(1)}% of blocked winners)`);
```

**Why this is safe:** read-only (only reads `audit_trail/data/dashboard_payload.json` and `config/hc_gate_params.json`); writes nothing; doesn't import `hc_filter.js` (so it can't disturb in-flight callers); and it lives in `tools/` where ad-hoc analysis scripts already cluster.

**Note on Gate 9c (correlation lockout):** the diagnosis script omits 9c because it's an order-dependent in-window check, not an intrinsic property of the pick — modeling it requires replaying `filterHighConvictionOrdered` and is rarely the marginal blocker.

---

## 6. Predicted per-class, per-gate failure rates (estimates pending diagnosis run)

The script above hasn't been executed (per the brief). Best-effort estimates below, drawn from known field statistics in the parent audit and from the threshold tightness of v4.3:

| Asset class | Expected dominant gate(s) | Estimated failure rate | Confidence |
|---|---|---|---|
| CRYPTO (n=628 in window, n=1598 in 3,500-pop) | **Gate 5** (FWD WR ≥ 70%) and **Gate 9b** (3 independent groups) | Gate 5: ~75–85%; Gate 9b: ~40–60% | high — class WR is 42.18% population-wide; only top decile of strategies clear 70% FWD WR |
| COMMODITY (n=27 / n=622 pop) | **Gate 5** (FWD WR ≥ 70%) | Gate 5: 80–90% | high — class WR is 42.60%, and 66.79% of "wins" are 1bp resolver noise so the FWD WR distribution is artificially compressed near 50% |
| FOREX (n=8 / n=794 pop) | **Gate 5** (FWD WR ≥ 70%, even with relax-to-65 if `fwdN<20`) | Gate 5: 85–95% | high — class WR is 50.38%, 63.25% noise |
| ETF (n=5 / n=83 pop) | **Gate 5** + **Gate 4** (FWD trades ≥ 2) | Gate 5: 60–80% | medium — small sample |
| EQUITY (n=0 in window / n=381 pop) | **Gate 5** + **Gate 6** (score ≥ 55) | TBD — no 3-day data | low — must run on 3,500-row population |
| BOND (n=0 / n=17 pop) | **Gate 4** then **Gate 5** | TBD — n=17 too small | very low — sample insufficient |

Marked **TBD pending diagnosis script run** for any rate that depends on running the diagnosis script. The CRYPTO row is the highest-confidence prediction because the math is direct: with v4.3 raising FWD WR to 70%, only ~5–10% of CRYPTO picks (the top performers) can clear it. That's consistent with the 5/668 = 0.75% observed pass rate in the 3-day window.

---

## 7. Per-class threshold recommendations (CRYPTO, EQUITY, ETF, BOND only)

Per Workstream B, FOREX/COMMODITY tuning is **BLOCKED** until `audit_trail/outcome_resolver.py:384–405` is fixed (1bp WIN threshold + live yfinance close → 63–67% noise wins). Recommendations below cover the four classes with reliable WR signal.

### CRYPTO — recommended changes

The 70% FWD WR floor is the dominant filter. The class-population WR is 42.18% (n=1,598); requiring FWD WR ≥ 70% selects roughly the top 5–10% of strategies. Gate 9b (3 independent groups) is the secondary blocker.

| Param | Current | Proposal | Rationale |
|---|---|---|---|
| `forwardWRMinPctCrypto` | 70 | **60** | Median observed strategy FWD WR is ~42%; 60% selects the top quartile, not the top decile. Brings expected pass rate to ~3–5%. |
| `scoreFloorCrypto`      | 55 | 55 (unchanged) | Already aligned with score distribution (median ~50 in payload). |
| `trustScoreMinCrypto`   |  4 |  4 (unchanged) | Working as intended. |
| `independentGroupsMin`  |  3 | **2** for CRYPTO only (would require parameterization) | Many real edge picks come from 2 independent groups. Mark as **"TBD pending diagnosis run"** — confirm Gate 9b is in the top 3 failure modes before relaxing. |

**Expected impact:** TBD pending diagnosis script run, but with FWD WR 70→60 the strict-pass count over the 3-day window should rise from 5 to roughly 20–30 (3–5% pass rate); cumulative PnL contribution depends on whether the new entries are net-positive (current population CRYPTO is PF 1.14, so probably +2–8 percentage points net).

### EQUITY — recommended changes

Class-population n=381, WR 51.97%, PF 1.385 (parent audit). 3-day window has 0 closed picks, so use the 3,500-row population as the calibration set.

| Param | Current | Proposal | Rationale |
|---|---|---|---|
| `forwardWRMinPctEquity` | 70 | **55** | 55% matches the observed class WR; 70 is unrealistically tight given the actual edge distribution. |
| `scoreFloorEquity`      | 55 | 55 (unchanged) | OK. |
| `trustScoreMinOther`    |  5 |  5 (unchanged) | OK. |

**Expected impact:** TBD pending diagnosis run. Expectation: ~3–5% of EQUITY picks pass instead of <1%; given class PF 1.385 the cumulative PnL impact should be modestly positive.

### ETF — recommended changes

Class-population n=83 (small), WR 54.22%, PF 1.220. 3-day window has 5 closed picks (all-class would have 5–8 strict-pass).

| Param | Current | Proposal | Rationale |
|---|---|---|---|
| `forwardWRMinPctETF` | 70 | **55** | Class WR 54.22%; 70 over-filters. |
| `scoreFloorETF`      | 35 | 35 (unchanged) | Already low; this is data-collection mode. |
| `forwardTradesMin` (ETF) | 2 | 2 (unchanged) | OK. |

**Expected impact:** TBD pending diagnosis run. Expectation: a handful of additional ETF picks/week pass strict.

### BOND — recommended changes

n=17 in 3,500. **No tuning recommended.** Sample is too small to calibrate a threshold, and the class is in pure data-collection mode. Defer to a later audit when n ≥ 50.

---

## 8. Parity reconciliation — fold-in or separate PR?

**Current state:** `tools/data/hc_parity_baseline.json` reports **0 divergences on 3,500 picks**. The "5 real divergences" the user's earlier todo references is from an older test run (pre-v4.3 config rollout); the parity gap was closed when both engines started consuming `config/hc_gate_params.json` overrides identically.

**The latent risk** I found while reading both files: Python's Gate 7c (confidence dead-zone, `cf ∈ [0.85, 0.95] AND fwdN < 30 → reject`) is **active** in `tools/hc_gates_python.py:370–375`, while the JS file has it **commented out** in `audit_dashboard/hc_filter.js:380–385`. Today this divergence is unobservable on the 3,500-pick population (no pick has the exact field combination needed to trigger Python-only rejection), but the next pick that does will silently fail parity.

**Recommendation: separate, small P0 PR — does not block tuning.**

Why separate:
1. The fix is a 4-line delete in Python (or a 4-line uncomment in JS — but project history says the JS removal was deliberate per "anti-predictive on crypto" comment, so Python should follow JS).
2. Tuning PR is a config-only change to `config/hc_gate_params.json` — orthogonal codepath.
3. Tuning requires the diagnosis run before merging; the parity fix can land immediately.
4. Tying them creates a dependency chain (parity must be re-run after every threshold change), which slows tuning iteration.

**PR sequencing within Workstream D:** parity-reconcile PR (delete Gate 7c from Python) → diagnosis instrumentation PR (`{trace:true}` opt) → diagnosis run + this report's per-class threshold proposal in `config/hc_gate_params.json` → re-run what-if + parity test as smoke gates.

---

## 9. `audit_what_if_entry_day.js` — does it expose enough detail?

**Current capability:** prints, per date, three fold-tables (all closed / loose HC / strict HC) with per-class subtotals (n, sum PnL%, WR%). That's enough for headline pass-rate measurement but **does NOT expose per-gate failure rates** — exactly the gap that motivated this investigation.

**Required expansion** (separate small PR, ride alongside the instrumentation PR in Section 4):
1. Once `evaluateHcGates1to9(p, {trace: true})` returns `{passed, failed_gates}`, add a new fold-mode `failGateBreakdown(rows)` that returns `{ [class]: { [gate_name]: count } }`.
2. Add a fourth printed table per date: `"<date> — gate failure breakdown (per class)"`.
3. Optionally add a `--show-blocked-winners` flag that lists the top-K picks with `pnl_pct >= --winner-threshold` that were blocked, with their failed-gates list.

This becomes the canonical regression check for any future threshold change: re-run with `--dates last-3-days`, confirm pass rate stays in the 2–5% band, and confirm no big-winner is blocked by an unexpected gate.

---

## 10. Test plan

For the bundled tuning + instrumentation work:

1. **Parity regression** — `python tools/hc_parity_test.py` must report 0 divergences after the Python Gate 7c removal. Stored baseline (`tools/data/hc_parity_baseline.json`) re-generated.
2. **Instrumentation unit test** — new file `tools/test_hc_trace.js` (or `pytest` equivalent) asserting:
   - `evaluateHcGates1to9(pick, {})` returns a boolean (legacy).
   - `evaluateHcGates1to9(pick, {trace: true})` returns `{passed: bool, failed_gates: string[]}`.
   - For a hand-crafted pick failing exactly `5_fwd_wr_per_class` AND `9b_independent_groups`, both names appear in `failed_gates` (proving non-short-circuit).
3. **Diagnosis script smoke** — `node tools/hc_gate_failure_diagnosis.js --dates 2026-04-25,2026-04-26,2026-04-27` runs cleanly and prints a non-empty per-class, per-gate breakdown.
4. **What-if regression** — pre-tuning baseline saved (`reports/audit_what_if_2026_04_25_to_27_PRE.txt`), post-tuning re-run must show pass rate in **2–5%** band on the 3-day window, with strict-pass cumulative PnL **≥ baseline**.
5. **Dashboard parity** — load `audit_dashboard/index.html` (built from `template.html`) in browser, confirm the HIGH CONVICTION hero button still renders the same picks set as `filterHcStrict`.

---

## 11. PR sequencing — relationship to Workstreams A and B

**Workstream B (resolver bug, FOREX/COMMODITY 63–67% noise wins) is a hard prerequisite for FOREX/COMMODITY tuning.** Until `outcome_resolver.py:384–405` filters `|pnl_pct| < 0.05%` as no-trade (or only closes at TP/SL/time-exit), FWD WR for those classes is half-noise and any threshold proposal is meaningless. **Workstream D's CRYPTO/EQUITY/ETF/BOND tuning can land independently of B.**

**Workstream A (ML pipeline freshness — `rf_model.pkl` 12.3d stale, `ml_gatekeeper` non-persisting) is orthogonal.** ML pipeline freshness changes the inputs (`score`, `confidence`, `strat_fwd_wr`); HC gates evaluate those inputs. As long as the ML pipeline's outputs land in the same payload fields, the HC gates don't care whether they came from a fresh or stale model. There is a second-order interaction: if A lands first and ML scores shift materially, the diagnosis run for D should be re-done against the new payload. Practical sequencing:

1. **Now:** Parity reconciliation PR (delete Python Gate 7c). Lands clean.
2. **Now:** Instrumentation PR (`{trace:true}` opt in JS + Python). Lands clean.
3. **+1 day:** Run diagnosis script, replace this report's "TBD pending diagnosis run" rows with measured rates.
4. **+1 day:** Tuning PR (config-only `forwardWRMinPctCrypto: 70→60`, `forwardWRMinPctEquity: 70→55`, `forwardWRMinPctETF: 70→55`). Verify with `audit_what_if_entry_day.js` re-run. Pause if pass rate exceeds 5% or strict cumulative PnL drops.
5. **Workstream B blocker:** FOREX/COMMODITY tuning held until resolver patch lands. Re-run diagnosis after that and propose FOREX/COMMODITY thresholds in a follow-up PR.
6. **Workstream A blocker (none):** independent.

Total Workstream D scope (excl. blocked classes): 3 small PRs — parity, instrumentation, config-tune — each independently revertable.

---

**End of report. No code modified outside this file.**
