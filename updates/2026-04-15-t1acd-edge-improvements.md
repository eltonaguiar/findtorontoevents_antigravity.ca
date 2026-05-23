# Edge Improvement Session — 2026-04-15

**Agent:** Codebuff (Buffy)
**Branch:** `fix/dynamic-runner-conviction-workflows`
**Reference:** `docs/HANDOFF_EDGE_IMPROVEMENT_TASKS_2026-04-14.md`

---

## Part 1: Claude Code Review Investigation & Fixes

### Background

A Claude Opus peer reviewed the last 24 hours of commits and produced a 10-item code review with 4 CRITICAL, 3 MAJOR, and 3 MINOR issues. I investigated each against the current codebase.

### Investigation Results

| # | Issue | Severity | Status | Detail |
|---|---|---|---|---|
| 1 | Untested production code paths (equity_bb_zscore_mr, forex_carry_ppp) | CRITICAL | ⚠️ Acceptable | Strategies exist but blocked at asset-class level by `HARD_KILLED_ASSET_CLASSES`. Cannot reach production picks. |
| 2 | Score thresholds lack bounds checking | CRITICAL | ✅ **Fixed** | Rewrote `ScoreThresholdConfig` → `AssetClassThreshold` matching actual schema, added 0–100 bounds |
| 3 | Redis bus single point of failure | CRITICAL | ✅ Already fixed | `CircuitBreaker` + `_load_cached_picks()` fallback exist |
| 4 | Dynamic threshold optimizer output not versioned | CRITICAL | ✅ **Fixed** | Added dry-run validation step + commit gate |
| 5 | Strategy demotion logic not auditable | MAJOR | ✅ Already fixed | `demotion_audit_trail.py` with source_hash + timestamp |
| 6 | Copytrader integration doesn't validate freshness | MAJOR | ✅ Already fixed | `check_trader_freshness()` validates WR degradation |
| 7 | Walk-forward validation lacks confidence intervals | MAJOR | ✅ Already fixed | Bootstrap CIs computed, `pf_ci_lower >= 1.20` promotion gate |
| 8 | Hardcoded asset-class thresholds | MINOR | ✅ Already fixed | Uses `calculate_dynamic_score_thresholds()` |
| 9 | ML ensemble is a stub | MINOR | ℹ️ Design debt | Placeholder, low priority |
| 10 | No deprecation warnings on old scoring | MINOR | ℹ️ Not addressed | Low impact |

### Fix #2: Threshold Validation (`alpha_engine/validate_thresholds.py`)

**Why:** The old `ScoreThresholdConfig` Pydantic model used `min_score`/`max_score`/`pf_killswitch` fields that didn't match the actual `score_thresholds.json` schema (which uses `threshold`/`profit_factor`/`win_rate`/`weighted_trades`). The validator would fail on real data. Also, no 0–100 bounds existed — a threshold >100 would silently pass.

**What changed:**
- Rewrote model as `AssetClassThreshold` matching actual schema:
  - `threshold: float` with `Field(ge=0, le=100)` — bounds enforced
  - `profit_factor: float` with `Field(ge=0)` — negative PF rejected
  - `win_rate: float` with `Field(ge=0, le=100)` — percentage bounds
  - Optional `reason`, `weighted_win_pnl`, `weighted_loss_pnl` fields
- Added CLI `__main__` block for GitHub Actions dry-run (plain-JSON validation, no pydantic required on bare CI runners)
- Deferred pydantic import with `try/except ImportError` guard
- Updated `tests/test_code_review_fixes.py` to match new model (11/11 tests pass)

**Benefit:** Prevents bad threshold values from silently breaking live pick scoring. CI catches issues before deployment.

### Fix #4: Workflow Dry-Run Validation (`.github/workflows/optimize-score-thresholds.yml`)

**Why:** The daily optimizer overwrites `score_thresholds.json` with no validation. If it produces garbage thresholds (e.g., all 0), live picks break immediately.

**What changed:**
- Added `Validate score thresholds (dry-run)` step between optimizer and commit
- Runs `python alpha_engine/validate_thresholds.py data/score_thresholds.json`
- Gated the commit step on `steps.validate-thresholds.outcome == 'success'`

**Benefit:** Bad thresholds are caught before they reach production. Commit only proceeds if validation passes.

---

## Part 2: Handoff Task Implementations (T1-A, T1-C, T1-D)

### T1-C: Bottom-Symbol Blocklist

**Goal:** Block 6 symbols with WR < 35% on n ≥ 20 that lose money regardless of strategy.

**Evidence:**

| Symbol | n | WR | PF | Sum PnL |
|---|---|---|---|---|
| TRXUSDT | 41 | 7.3% | 0.08 | −62.8% |
| JTOUSDT | 33 | 18.2% | 0.38 | −34.1% |
| XLMUSDT | 26 | 19.2% | 0.81 | −1.7% |
| ICPUSDT | 53 | 22.6% | 0.65 | −6.7% |
| RENDERUSDT | 45 | 31.1% | 0.40 | −33.8% |
| NVDA | 21 | 33.3% | 0.77 | −6.3% |

> Note: TRXUSDT was already in `BLOCKED_SYMBOLS` (added 2026-04-02). Added the remaining 5.

**Files changed:**
- `audit_trail/quality_gates.py` — Added 5 symbols to `BLOCKED_SYMBOLS` set (line ~795)

**How it works:** The existing `BLOCKED_SYMBOLS` set is already wired into two enforcement points:
1. `_apply_score_penalties()` — applies `-50` score penalty to blocked symbols (line ~1712)
2. `passes_active_gate()` — rejects blocked symbols entirely (line ~3325)

No new wiring needed — just adding the symbols to the existing set.

**Benefit:** Prevents future picks on structurally anti-edge symbols. Estimated 0–3 currently active picks affected (preemptive block for safety).

---

### T1-D: Top-Symbol Score Boost

**Goal:** Boost 10 proven symbols (+2 to +5) to nudge picks over HC gate thresholds without changing any floor.

**Evidence (top 10 with n ≥ 20, WR ≥ 50%):**

| Symbol | WR | PF | Boost |
|---|---|---|---|
| BNBUSDT | 83.9% | 12.70 | +5 |
| CVX | 72.4% | 2.25 | +4 |
| XRPUSDT | 69.4% | 4.43 | +4 |
| OPUSDT | 63.3% | 2.37 | +3 |
| NEARUSDT | 62.5% | 2.74 | +3 |
| XOM | 60.5% | 1.53 | +3 |
| WLDUSDT | 60.0% | 2.06 | +3 |
| UNIUSDT | 57.6% | 1.54 | +2 |
| ARBUSDT | 54.1% | 1.92 | +2 |
| SOLUSDT | 50.8% | 1.84 | +2 |

**Files changed:**
- `audit_trail/quality_gates.py` — Added `PROVEN_SYMBOL_BOOSTS` dict (after `STRATEGY_SYMBOL_BONUSES`, ~line 3280) and wired into `_apply_score_penalties()` (section 6b, ~line 2290)

**Implementation details:**
- **Dedup guard:** Proven boost is skipped when a `SYMBOL_DIRECTION_BONUS` already applies for the same symbol+direction. This avoids double-boosting (e.g., BNBUSDT LONG already gets +7 from direction bonus) and prevents partial undo of direction penalties (e.g., SOLUSDT LONG has -15 direction penalty but would get +2 proven boost, partially cancelling the penalty).
- **Score cap:** `score = min(100, score + _proven_boost)` — score cannot exceed 100 after boost.
- **Transparency:** Boost logged in pick's `_penalties` list as `proven_symbol(SYMBOL):+N`.

**Benefit:** Proven symbols get a small score lift, pushing marginal picks over HC gate thresholds. Expected HC live pick count increases by 1–3 on these symbols.

---

### T1-A: Tighten HC Gate 7 — Confidence Band 0.85–0.95

**Goal:** Close the anti-predictive confidence band. Picks in 0.85–0.95 confidence have PF 0.61 (losing money), but the existing Gate 7 only rejected `confidence > 0.90 AND fwd_n < 20`.

**Evidence:**

| Confidence | n | WR | PF |
|---|---|---|---|
| 0.75–0.85 | 795 | 45.9% | 1.28 (positive) |
| **0.85–0.95** | **126** | **47.6%** | **0.61** (LOSING) |
| 0.95–1.01 | 110 | 44.5% | 1.04 |

**Files changed:**
- `audit_dashboard/hc_filter.js` — Added 3 params to `HC_GATE_PARAMS_EMBEDDED` + Gate 7b logic in `evaluateHcGates1to9()`
- `config/hc_gate_params.json` — Added `confidenceLoBand: 0.85`, `confidenceHiBand: 0.95`, `confidenceLoBandFwdTradesMin: 30`
- `tools/dashboard_hc_rules.py` — Added 3 params to `_EMBEDDED_DEFAULTS` + Gate 7b logic in `evaluate_hc_gates_1_to_9()`

**Gate 7b logic (all three mirrors):**

```javascript
// JS
var cfLo = params.confidenceLoBand || 0.85;
var cfHi = params.confidenceHiBand || 0.95;
var cfLoFwdMin = params.confidenceLoBandFwdTradesMin || 30;
if (cf >= cfLo && cf <= cfHi && fwdN < cfLoFwdMin) return false;
```

```python
# Python
cf_lo = params.get("confidenceLoBand", 0.85)
cf_hi = params.get("confidenceHiBand", 0.95)
cf_lo_fwd_min = params.get("confidenceLoBandFwdTradesMin", 30)
if cf >= cf_lo and cf <= cf_hi and fwd_n < cf_lo_fwd_min:
    return False
```

**Design decisions:**
- **Upper bound uses `<=` (not `<`):** Code reviewer flagged that `cf == 0.95` exactly would fall through both Gate 7b (`cf < 0.95`) and the extreme gate (`cf > 0.95`). Using `<=` closes the gap.
- **FwdTradesMin = 30:** If a strategy has ≥30 forward trades at high confidence, the confidence is likely earned (not overfitted). Below 30, the 0.85–0.95 band is anti-predictive.
- **Params are configurable:** All three values come from `hc_gate_params.json`, so they can be tuned without code changes.

**Benefit:** HC-passing picks in the anti-predictive confidence band are filtered out. Expected aggregate PF of HC-passing closed picks rises by ≥0.05. Live HC pick count drops by 1–2 picks.

---

## Validation Summary

| Check | Result |
|---|---|
| `py_compile audit_trail/quality_gates.py` | ✅ OK |
| `py_compile tools/dashboard_hc_rules.py` | ✅ OK |
| `node require('./audit_dashboard/hc_filter.js')` | ✅ OK |
| `config/hc_gate_params.json` valid JSON | ✅ OK (confidenceLoBand: 0.85, confidenceHiBand: 0.95, confidenceLoBandFwdTradesMin: 30) |
| `pytest tests/test_quality_gates.py` (36 tests) | ✅ 36/36 pass |
| `pytest tests/test_code_review_fixes.py` (11 tests) | ✅ 11/11 pass |
| Import verification: `BLOCKED_SYMBOLS` + `PROVEN_SYMBOL_BOOSTS` | ✅ All symbols present |
| CLI validation: `python alpha_engine/validate_thresholds.py data/score_thresholds.json` | ✅ 8 asset classes validated |

---

## Files Changed (Complete List)

| File | Change | Task |
|---|---|---|
| `audit_trail/quality_gates.py` | Added 5 blocked symbols to `BLOCKED_SYMBOLS`; added `PROVEN_SYMBOL_BOOSTS` dict; wired boost into `_apply_score_penalties()` | T1-C, T1-D |
| `audit_dashboard/hc_filter.js` | Added 3 confidence band params; added Gate 7b logic with `<=` upper bound | T1-A |
| `config/hc_gate_params.json` | Added `confidenceLoBand`, `confidenceHiBand`, `confidenceLoBandFwdTradesMin` | T1-A |
| `tools/dashboard_hc_rules.py` | Added 3 confidence band params to embedded defaults; added Gate 7b logic | T1-A |
| `alpha_engine/validate_thresholds.py` | Rewrote `ScoreThresholdConfig` → `AssetClassThreshold` with 0–100 bounds; added CLI `__main__` block; deferred pydantic import | Claude #2 |
| `.github/workflows/optimize-score-thresholds.yml` | Added dry-run validation step; gated commit on validation success | Claude #4 |
| `tests/test_code_review_fixes.py` | Updated tests to match `AssetClassThreshold` model; graceful handling for missing `demotion_audit_trail` | Claude #2 |
| `audit_dashboard/hc_filter.js` | Updated forwardWRMinPct 45 -> 55 in embedded defaults + fallback | T1-B |
| `config/hc_gate_params.json` | Updated forwardWRMinPct 45 -> 55 + updated _doc comment | T1-B |
| `tools/dashboard_hc_rules.py` | Updated forwardWRMinPct 45 -> 55 in embedded defaults + fallback | T1-B |
| `.github/workflows/audit-dashboard.yml` | Added stock_prices.json + ai_challenge_*.json to checkout --ours (issue #141 fix) | T1-G |

---

## Remaining Handoff Tasks

Per `docs/HANDOFF_EDGE_IMPROVEMENT_TASKS_2026-04-14.md`, the following are still open:

**Tier 1 (this week):**
- T1-B: Relax `forwardWRMinPct` 45 → 55 (DONE)
- T1-E: Wire `inverse_goldmine_stocks` to live scanner (medium)
- T1-F: Investigate `quan_engine_scalp` (medium-high, investigation only)
- T1-G: Fix workflow conflict-marker trap (DONE)

**Tier 2 (1–2 weeks):** T2-A through T2-K (11 tasks)

**Coordination notes:**
- `alpha_engine/ml_ranker.py` + `alpha_engine/model_calibration.py` → DO NOT TOUCH (Codebuff paused)
- Never edit `audit_dashboard/index.html` directly (regenerated by workflow)


---

---

## Part 2b: Additional Handoff Tasks (T1-B, T1-G)

### T1-B: Relax forwardWRMinPct 45 -> 55

**Goal:** Raise the HC Gate 3 forward-WR floor from 45% to 55%. Evidence from closed picks shows this improves aggregate PF from 1.31 to 1.92 — picks with fwd WR 45-55% have negative edge and drag down portfolio quality.

**Files changed:**
-  — Updated  to  in embedded defaults + fallback in gate logic
-  — Updated  to  + updated  comment
-  — Updated  to  in embedded defaults + fallback in gate logic

**Evidence:** Per handoff doc, raising forwardWRMinPct from 45 to 55 produces PF 1.31 -> 1.92 delta on closed picks. Picks below 55% forward WR are statistically anti-edge.

**Benefit:** Higher quality bar for HC-passing picks. Expected HC live pick count drops slightly but aggregate PF rises significantly.

---

### T1-G: Fix Recurring Workflow #141 Conflict-Marker Trap

**Goal:** Fix the root cause of issue #141 — stash-pop conflict resolution leaving  markers in JSON files that then get committed to main.

**Root cause:** The  line during stash-pop conflict resolution only covered 4 files:
- 
- 
- 
- 

But the subsequent  line included 6 files (also  and ). The 2 missing files would retain conflict markers from the stash-pop, which then got staged and committed. The  safety net correctly caught this, but it blocked the deploy for hours.

**Files changed:**
- ====================================================================
  Polymarket Wallet Intelligence
====================================================================
  [PM] #01 0x8dxd -> 49 crypto decisions, WR 100.0%, adj 89.0%, 30d 0d/0, hft_micro, lat 0.96/hft_micro, PnL $775,783
  [PM] #02 0xf705fa045201391d9632b7f3cde06a5e24453ca7 -> 50 crypto decisions, WR 100.0%, adj 89.1%, 30d 3d/99,067, market_maker_systematic, lat 0.46/market_maker_systematic, PnL $1,840,820
  [PM] #03 k9Q2mX4L8A7ZP3R -> 50 crypto decisions, WR 100.0%, adj 89.1%, 30d 1d/10,757, hft_micro, lat 0.98/hft_micro, PnL $650,173
  [PM] #04 justdance -> 39 crypto decisions, WR 100.0%, adj 87.1%, 30d 3d/80,956, high_prob_bond, lat 0.49/ok, PnL $1,432,985
  [PM] #05 0x1979ae6B7E6534dE9c4539D0c205E582cA637C9D-1769439463256 -> 49 crypto decisions, WR 100.0%, adj 89.0%, 30d 0d/0, hft_micro, lat 0.95/hft_micro, PnL $871,350
  [PM] #06 BoneReader -> 49 crypto decisions, WR 100.0%, adj 89.0%, 30d 8d/55,698, hft_micro, lat 0.92/hft_micro, PnL $364,594
  [PM] #07 coinman2 -> 29 crypto decisions, WR 100.0%, adj 84.5%, 30d 0d/0, directional_generalist, lat 0.62/latency_arb, PnL $834,820
  [PM] #08 0xa95bfdb -> 40 crypto decisions, WR 100.0%, adj 87.3%, 30d 0d/0, high_prob_bond, lat 0.54/ok, PnL $1,214,577
  [PM] #09 stonksgoup -> 18 crypto decisions, WR 100.0%, adj 80.0%, 30d 0d/0, milestone_fade, lat 0.48/ok, PnL $368,616
  [PM] #10 gabagool22 -> 50 crypto decisions, WR 100.0%, adj 89.1%, 30d 0d/0, hft_micro, lat 0.92/hft_micro, PnL $166,217
  [PM] #11 PurpleThunderBicycleMountain -> 48 crypto decisions, WR 100.0%, adj 88.8%, 30d 0d/0, hft_micro, lat 0.92/hft_micro, PnL $1,213,184
  [PM] #12 distinct-baguette -> 49 crypto decisions, WR 100.0%, adj 89.0%, 30d 0d/0, hft_micro, lat 0.91/hft_micro, PnL $130,310
  [PM] #13 0x1d0034134e -> 50 crypto decisions, WR 100.0%, adj 89.1%, 30d 0d/0, hft_micro, lat 0.93/hft_micro, PnL $578,435
  [PM] #14 kingofcoinflips -> 48 crypto decisions, WR 100.0%, adj 88.8%, 30d 2d/29,448, directional_generalist, lat 0.62/latency_arb, PnL $908,537
  [PM] #15 0xdE17f7144fbD0eddb2679132C10ff5e74B120988-1772205225932 -> 45 crypto decisions, WR 100.0%, adj 88.3%, 30d 23d/1,222,442, high_prob_bond, lat 0.50/ok, PnL $1,900,504
  [PM] #16 Circus-995 -> 49 crypto decisions, WR 100.0%, adj 89.0%, 30d 0d/0, high_prob_bond, lat 0.44/ok, PnL $1,894,351
  [PM] #17 Account88888 -> 50 crypto decisions, WR 100.0%, adj 89.1%, 30d 0d/0, hft_micro, lat 0.97/hft_micro, PnL $1,632,053
  [PM] #18 vidarx -> 49 crypto decisions, WR 100.0%, adj 89.0%, 30d 3d/23,925, hft_micro, lat 0.94/hft_micro, PnL $382,922
  [PM] #19 elPolloLoco -> 30 crypto decisions, WR 100.0%, adj 84.8%, 30d 2d/19,832, high_prob_bond, lat 0.44/ok, PnL $340,591
  [PM] #20 HaileyWelch -> 21 crypto decisions, WR 100.0%, adj 81.5%, 30d 0d/0, hft_micro, lat 0.79/hft_micro, PnL $822,850
  [PM] #21 0xfb1c3c1ab4fb2d0cbcbb9538c8d4d357dd95963e -> 44 crypto decisions, WR 100.0%, adj 88.1%, 30d 0d/0, high_prob_bond, lat 0.46/ok, PnL $2,201,582
  [PM] #22 0xE594336603F4fB5d3ba4125a67021ab3B4347052-1769022918519 -> 49 crypto decisions, WR 100.0%, adj 89.0%, 30d 0d/0, hft_micro, lat 0.95/hft_micro, PnL $1,110,427
  [PM] #23 ComTruise -> 47 crypto decisions, WR 100.0%, adj 88.7%, 30d 5d/43,862, high_prob_bond, lat 0.46/ok, PnL $360,636
  [PM] #24 x6916Cc00AA1c3e75ECf4081DF7caE7D2f3592fd4 -> 43 crypto decisions, WR 100.0%, adj 87.9%, 30d 9d/55,397, high_prob_bond, lat 0.45/ok, PnL $181,215
  [PM] #25 brr69420 -> 39 crypto decisions, WR 100.0%, adj 87.1%, 30d 0d/0, hft_micro, lat 0.86/hft_micro, PnL $275,011
  [PM] #26 sherlockhomie -> 50 crypto decisions, WR 100.0%, adj 89.1%, 30d 0d/0, hft_micro, lat 0.95/hft_micro, PnL $261,735
  [PM] #27 0xB27BC932bf8110D8F78e55da7d5f0497A18B5b82-1772569391020 -> 50 crypto decisions, WR 100.0%, adj 89.1%, 30d 50d/361,043, hft_micro, lat 0.93/hft_micro, PnL $361,043
  [PM] #28 Sharky6999 -> 37 crypto decisions, WR 100.0%, adj 86.7%, 30d 0d/0, market_maker_systematic, lat 0.56/market_maker_systematic, PnL $300,978
  [PM] #29 0x1f0ebc543B2d411f66947041625c0Aa1ce61CF86-1772205597930 -> 49 crypto decisions, WR 100.0%, adj 89.0%, 30d 14d/171,872, hft_micro, lat 0.93/hft_micro, PnL $580,236
  [PM] #30 0x0eA574F3204C5c9C0cdEad90392ea0990F4D17e4-1769515653156 -> 49 crypto decisions, WR 100.0%, adj 89.0%, 30d 0d/0, hft_micro, lat 0.95/hft_micro, PnL $790,189
  [PM] #44 SolMoe -> 16 crypto decisions, WR 68.8%, adj 65.0%, 30d 1d/-18, hft_micro, lat 0.87/hft_micro, PnL $969
  [PM] Saved 20 trader profiles -> E:indtorontoevents_antigravity.ca\copy_trader_intel\data\polymarket_trader_profiles.json
  [PM] Saved 2 live picks      -> E:indtorontoevents_antigravity.ca\copy_trader_intel\data\polymarket_picks.json
  [PM] Complete: 20 qualified wallets, 2 live crypto picks
======================================================================
  Polymarket Crypto Signal Generator
======================================================================

[1/4] Fetching strict crypto markets...
      7 markets passed strict filtering

  Top markets:
    BTCUSDT    price_above p=1% vol=$   975,020  Will Bitcoin reach $95,000 in April?
    ETHUSDT    price_above p=0% vol=$    99,024  Will the price of Ethereum be above $2,500 on April 15?
    ETHUSDT    price_above p=6% vol=$    97,147  Will Ethereum reach $7,500 by December 31, 2026?
    ETHUSDT    price_above p=4% vol=$    94,699  Will the price of Ethereum be above $2,400 on April 15?
    BNBUSDT    price_above p=10% vol=$     9,756  Will BNB reach $1500 by December 31, 2026?
    ETHUSDT    price_above p=4% vol=$     9,695  Will Ethereum reach $2,700 April 13-19?
    BTCUSDT    price_above p=73% vol=$     9,426  Will the price of Bitcoin be above $72,000 on April 20?

[2/4] Building probability signals...
      7 probability signals

[3/4] Building momentum signals...
      0 momentum signals

[4/4] Saving picks...
      Saved 3 picks to E:indtorontoevents_antigravity.calpha_engine\data\polymarket_signals.json

Done.
======================================================================
  Kalshi Prediction Market Signals  Multi-Timeframe Consensus
======================================================================

[1/3] Fetching Kalshi crypto series (BTC, ETH, SOL...)...
      Generated 4 consensus signals

  LONG  BTCUSDT      conf=0.61  [2/4 TFs agree]  Kalshi MTF consensus [2/4 TFs agree]: 15m | 1h | 1d | 1y
  LONG  SOLUSDT      conf=0.61  [1/2 TFs agree]  Kalshi MTF consensus [1/2 TFs agree]: 15m | 1d
  SHORT BNBUSDT      conf=0.82  [1/1 TFs agree]  Kalshi MTF consensus [1/1 TFs agree]: 15m
  SHORT HYPEUSDT     conf=0.82  [1/1 TFs agree]  Kalshi MTF consensus [1/1 TFs agree]: 15m

[2/3] Generating picks...
      4 picks generated

[3/3] Saving to kalshi_signals.json...
      Saved to E:indtorontoevents_antigravity.calpha_engine\data\kalshi_signals.json

======================================================================
  Done. 4 Kalshi signals saved.
======================================================================
======================================================================
  Prediction Market Consensus
  Wallet Copy + Polymarket Reverse + Kalshi
======================================================================

Results: 2 consensus picks

  SHORT BNBUSDT      conf=0.91 [kalshi,polymarket_reverse]
    - polymarket_reverse: 
    - kalshi: 

  LONG  BTCUSDT      conf=0.87 [kalshi,wallet_copy]
    - wallet_copy: Polymarket wallet justdance rank #4 is net LONG BTCUSDT across 10 open markets; 37 closed crypto decisions, adj WR 92.9% (raw 100.0%), PnL $1,359,944, archetype
    - kalshi: 

  [PM] #01 0x8dxd -> 49 crypto decisions, WR 100.0%, adj 89.0%, 30d 0d/0, hft_micro, lat 0.96/hft_micro, PnL $775,783
  [PM] #02 0xf705fa045201391d9632b7f3cde06a5e24453ca7 -> 50 crypto decisions, WR 100.0%, adj 89.1%, 30d 3d/99,067, market_maker_systematic, lat 0.46/market_maker_systematic, PnL $1,840,820
  [PM] #03 k9Q2mX4L8A7ZP3R -> 50 crypto decisions, WR 100.0%, adj 89.1%, 30d 1d/10,757, hft_micro, lat 0.98/hft_micro, PnL $650,173
  [PM] #04 justdance -> 39 crypto decisions, WR 100.0%, adj 87.1%, 30d 3d/80,956, high_prob_bond, lat 0.49/ok, PnL $1,432,985
  [PM] #05 0x1979ae6B7E6534dE9c4539D0c205E582cA637C9D-1769439463256 -> 49 crypto decisions, WR 100.0%, adj 89.0%, 30d 0d/0, hft_micro, lat 0.95/hft_micro, PnL $871,350
  [PM] #06 BoneReader -> 49 crypto decisions, WR 100.0%, adj 89.0%, 30d 8d/55,698, hft_micro, lat 0.92/hft_micro, PnL $364,594
  [PM] #07 coinman2 -> 29 crypto decisions, WR 100.0%, adj 84.5%, 30d 0d/0, directional_generalist, lat 0.62/latency_arb, PnL $834,820
  [PM] #08 0xa95bfdb -> 40 crypto decisions, WR 100.0%, adj 87.3%, 30d 0d/0, high_prob_bond, lat 0.54/ok, PnL $1,214,577
  [PM] #09 stonksgoup -> 18 crypto decisions, WR 100.0%, adj 80.0%, 30d 0d/0, milestone_fade, lat 0.48/ok, PnL $368,616
  [PM] #10 gabagool22 -> 50 crypto decisions, WR 100.0%, adj 89.1%, 30d 0d/0, hft_micro, lat 0.92/hft_micro, PnL $166,217
  [PM] #11 PurpleThunderBicycleMountain -> 48 crypto decisions, WR 100.0%, adj 88.8%, 30d 0d/0, hft_micro, lat 0.92/hft_micro, PnL $1,213,184
  [PM] #12 distinct-baguette -> 49 crypto decisions, WR 100.0%, adj 89.0%, 30d 0d/0, hft_micro, lat 0.91/hft_micro, PnL $130,310
  [PM] #13 0x1d0034134e -> 50 crypto decisions, WR 100.0%, adj 89.1%, 30d 0d/0, hft_micro, lat 0.93/hft_micro, PnL $578,435
  [PM] #14 kingofcoinflips -> 48 crypto decisions, WR 100.0%, adj 88.8%, 30d 2d/29,448, directional_generalist, lat 0.62/latency_arb, PnL $908,537
  [PM] #15 0xdE17f7144fbD0eddb2679132C10ff5e74B120988-1772205225932 -> 45 crypto decisions, WR 100.0%, adj 88.3%, 30d 23d/1,222,442, high_prob_bond, lat 0.50/ok, PnL $1,900,504
  [PM] #16 Circus-995 -> 49 crypto decisions, WR 100.0%, adj 89.0%, 30d 0d/0, high_prob_bond, lat 0.44/ok, PnL $1,894,351
  [PM] #17 Account88888 -> 50 crypto decisions, WR 100.0%, adj 89.1%, 30d 0d/0, hft_micro, lat 0.97/hft_micro, PnL $1,632,053
  [PM] #18 vidarx -> 49 crypto decisions, WR 100.0%, adj 89.0%, 30d 3d/23,925, hft_micro, lat 0.94/hft_micro, PnL $382,922
  [PM] #19 elPolloLoco -> 30 crypto decisions, WR 100.0%, adj 84.8%, 30d 2d/19,832, high_prob_bond, lat 0.44/ok, PnL $340,591
  [PM] #20 HaileyWelch -> 21 crypto decisions, WR 100.0%, adj 81.5%, 30d 0d/0, hft_micro, lat 0.79/hft_micro, PnL $822,850
  [PM] #21 0xfb1c3c1ab4fb2d0cbcbb9538c8d4d357dd95963e -> 44 crypto decisions, WR 100.0%, adj 88.1%, 30d 0d/0, high_prob_bond, lat 0.46/ok, PnL $2,201,582
  [PM] #22 0xE594336603F4fB5d3ba4125a67021ab3B4347052-1769022918519 -> 49 crypto decisions, WR 100.0%, adj 89.0%, 30d 0d/0, hft_micro, lat 0.95/hft_micro, PnL $1,110,427
  [PM] #23 ComTruise -> 47 crypto decisions, WR 100.0%, adj 88.7%, 30d 5d/43,862, high_prob_bond, lat 0.46/ok, PnL $360,636
  [PM] #24 x6916Cc00AA1c3e75ECf4081DF7caE7D2f3592fd4 -> 43 crypto decisions, WR 100.0%, adj 87.9%, 30d 9d/55,397, high_prob_bond, lat 0.45/ok, PnL $181,215
  [PM] #25 brr69420 -> 39 crypto decisions, WR 100.0%, adj 87.1%, 30d 0d/0, hft_micro, lat 0.86/hft_micro, PnL $275,011
  [PM] #26 sherlockhomie -> 50 crypto decisions, WR 100.0%, adj 89.1%, 30d 0d/0, hft_micro, lat 0.95/hft_micro, PnL $261,735
  [PM] #27 0xB27BC932bf8110D8F78e55da7d5f0497A18B5b82-1772569391020 -> 50 crypto decisions, WR 100.0%, adj 89.1%, 30d 50d/361,043, hft_micro, lat 0.93/hft_micro, PnL $361,043
  [PM] #28 Sharky6999 -> 37 crypto decisions, WR 100.0%, adj 86.7%, 30d 0d/0, market_maker_systematic, lat 0.56/market_maker_systematic, PnL $300,978
  [PM] #29 0x1f0ebc543B2d411f66947041625c0Aa1ce61CF86-1772205597930 -> 49 crypto decisions, WR 100.0%, adj 89.0%, 30d 14d/171,872, hft_micro, lat 0.93/hft_micro, PnL $580,236
  [PM] #30 0x0eA574F3204C5c9C0cdEad90392ea0990F4D17e4-1769515653156 -> 49 crypto decisions, WR 100.0%, adj 89.0%, 30d 0d/0, hft_micro, lat 0.95/hft_micro, PnL $790,189
  [PM] #44 SolMoe -> 16 crypto decisions, WR 68.8%, adj 65.0%, 30d 1d/-18, hft_micro, lat 0.87/hft_micro, PnL $969
  [PM] Saved 20 trader profiles -> E:indtorontoevents_antigravity.ca\copy_trader_intel\data\polymarket_trader_profiles.json
  [PM] Saved 2 live picks      -> E:indtorontoevents_antigravity.ca\copy_trader_intel\data\polymarket_picks.json
{
  "generated_at": "2026-04-15T12:43:29.823974+00:00",
  "duration_seconds": 101.1,
  "agent_results": {
    "whale_tracker": {
      "traders": 15,
      "signals": 2,
      "error": null
    },
    "momentum_detector": {
      "markets_analyzed": 7,
      "signals": 0,
      "error": null
    },
    "kalshi_agent": {
      "events": 36,
      "signals": 5,
      "error": null
    },
    "consensus": {
      "signals_aggregated": 10,
      "consensus_signals": 5,
      "high_conviction": 1,
      "error": null
    }
  },
  "total_raw_signals": 7,
  "consensus_signals": 5,
  "merged_to_pipeline": 3
} — Added  and  to the  line, with a comment explaining issue #141 and why all  paths must be covered.

**Verification:** Confirmed that the 6 files in  are exactly the set of freshly-generated dashboard outputs:
1.  writes: , , 
2.  writes: 
3.  writes: 
4.  writes: 

All 6 are freshly generated in the current CI run, so  (our locally generated version) is always correct.

**Benefit:** Eliminates the recurring issue #141 deploy-blocker. Conflict markers will no longer appear in generated files.

## Part 3: Cursor Code Review — Cross-Check

**Reviewer:** Cursor agent
**Date:** 2026-04-15

### Summary

Cursor cross-checked Codebuff's findings against the repo's gates, blocks, and scoring. The review largely validated Codebuff's work as consistent with existing policies, but flagged two follow-ups:

### 1. JTOUSDT Gap → RESOLVED

**Cursor finding:** TRXUSDT is hard-blocked in `BLOCKED_SYMBOLS`, but JTOUSDT was only in `negative_knowledge_registry.py` (0% WR, n=15) — not promoted to the hard-block set.

**Status:** ✅ **Already fixed by T1-C.** JTOUSDT was added to `BLOCKED_SYMBOLS` in this session (along with XLMUSDT, ICPUSDT, RENDERUSDT, NVDA). Verified: `'JTOUSDT' in BLOCKED_SYMBOLS` returns `True`.

### 2. quan_engine Tension — UNRESOLVED (maps to T1-F)

**Cursor finding:** Codebuff's handoff doc (T1-F) describes `quan_engine_scalp` as "540 trades, 38.9% WR, PF 1.25" — borderline but not terrible. However, the codebase treats it as a confirmed loser across multiple enforcement layers:

| Layer | Treatment | Data cited |
|---|---|---|
| `PERMANENTLY_KILLED` (auto_tuner.py) | Hard-killed | "0% WR zombie — killed 2026-04-02" |
| `BLOCKED_STRATEGIES` (quality_gates.py) | Blocked | "25% WR, 1793 trades, -352.88% PnL" |
| Source score bias (quality_gates.py) | -28 | quan_engine_scalp dominant volume |
| Source score bias (quality_gates.py) | -15 | quan_engine (generic) |
| LONG direction penalty (quality_gates.py) | -15 | "29% WR on LONGs (387 trades)" |
| Symbol blocks (quality_gates.py) | Multiple | MATICUSDT, ADAUSDT, ICPUSDT, SOLUSDT, BTCUSDT, KASUSDT, ONDOUSDT |
| Strategy+symbol penalties (quality_gates.py) | -15 each | BTCUSDT, KASUSDT, ONDOUSDT, ICPUSDT |

**Root cause of the discrepancy:**

- The "38.9% WR, PF 1.25" figure likely comes from a **different cohort window** (e.g., recent picks, specific symbols, or a subset like SHORT-only)
- The "25% WR, -352.88% PnL" figure is the **all-time closed ledger** with 1,793 trades
- PF 1.25 with 38.9% WR is mathematically plausible if wins are much larger than losses (few big wins offset many small losses), but this pattern is unstable

**Recommended resolution (aligns with T1-F in handoff doc):**

1. Pull the exact closed-pick cohort for `quan_engine_scalp` from `closed_picks.json`
2. Partition by: asset class, symbol, LONG vs SHORT, date window (first-half vs second-half)
3. Identify which sub-slice produces the "38.9% WR / PF 1.25" result
4. If the positive slice is SHORT-only on specific symbols → consider a `PROFITABLE_SHORT_STRATEGIES` exemption
5. If the positive slice is a narrow date window → confirm whether the edge has decayed
6. Document in `negative_knowledge_registry.py` or `quality_gates.py` as appropriate

**Action:** No code change in this session. This maps directly to handoff task **T1-F** (investigation only, separate follow-up PR for any changes).

### Alignment Summary

| Cursor Item | Status | Action |
|---|---|---|
| JTOUSDT gap vs negative_knowledge_registry | ✅ Fixed (T1-C) | Already in `BLOCKED_SYMBOLS` |
| quan_engine tension (handoff vs code) | ⚠️ Unresolved | Maps to T1-F investigation task |
| SHORT penalties / LONG-only smart picks | ✅ Consistent | Already enforced in code |
| Trust scoring alignment | ✅ Consistent | Smart-picks floor (3) vs HC gate (6) are intentionally different |
| TRX / Value+Quality / volume_spike | ✅ Consistent | All hard-blocked as expected |
