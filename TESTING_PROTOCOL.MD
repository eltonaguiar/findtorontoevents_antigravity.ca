# TESTING_PROTOCOL

Date: 2026-04-01 (original) | **Audited: 2026-04-04**  
Scope: Crypto, Stocks, ETFs, Forex, Futures, Commodities  
Primary DB: `mysql.50webs.com` -> `ejaguiar1_stocks`

> **⚠️ AUDIT STATUS (2026-04-04):** Infrastructure audit against 1,000 closed picks revealed
> significant gaps between this protocol and reality. See Section 13 for data-driven calibration
> and Section 14 for priority implementation roadmap. Key issues: forward test pipeline broken
> (0 picks), walk-forward stale (21 days), promotion gate disconnected from live dashboard
> (0/5 strategies promoted but 50+ strategies live), MySQL tables not created, scarcity
> analysis never executed.
>
> **🔄 PHILOSOPHY CHANGE (2026-04-04):** Shifted from "kill underperformers" to
> **"rehabilitation-first pipeline."** Section 7 now defines a 6-stage rehabilitation process
> (cross-symbol → cross-asset → inverse → mutation grid → regime filter → crossover blend)
> before any strategy reaches the graveyard. Evidence: `winner_pattern_precursor` inverse =
> 81.2% WR, `claude_gainer_ml` inverse = 80% WR. Killing destroys signal value.
>
> **2026-04-08 — Tread lightly on new hard blocks:** Before adding systems to
> `BLOCKED_SOURCE_SYSTEMS`, follow **`docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`**
> (investigation ladder, DNA / inverse / cross-asset). Same strategy may lose in one asset
> class and work after mutation or transfer — do not "score your way out" of that process.
>
> **Three-axis autopsy:** Export closed picks CSV, run **`python tools/mutation_analysis.py`**, then
> **`docs/MUTATION_THREE_AXIS_PROTOCOL.md`** (symbol / direction / timeframe splits, mutation
> quality score, allowlist mutations before kill).

## 1) Objective

Standardize a multi-layer testing pipeline so strategy promotion is evidence-based:
- Backtest -> walk-forward -> statistical validation -> forward test -> test portfolios.
- Track top performers and low-pick scarcity.
- Run loser what-if remediation (SL/TP tweaks, inverse, DNA mutation).
- Detect cross-symbol / cross-asset "super strategies".
- **[NEW] Enforce data-driven gates (score floor, trust floor, toxic combo blocks) at every layer.**
- **[NEW] Rehabilitation-first pipeline: cross-symbol → cross-asset → inverse → mutation → regime → crossover → graveyard (last resort).**

---

## 2) Layered Testing Stack (Required)

### Layer 0: Data Integrity
- Use adjusted prices where relevant (splits/dividends for equities/ETFs).
- Normalize timestamps to UTC.
- Version source snapshots used per run.
- Include transaction cost + slippage model metadata in each run record.

### Layer 1: In-Sample Backtest
- Baseline universe per asset class.
- Fixed universe for IS period.
- Store full parameters, seed, and symbol list.

### Layer 2: Out-of-Sample (OOS)
- Required split target:
  - IS: first 70%
  - OOS validation: next 15%
  - final holdout/live-forward: last 15%
- Reject if OOS drift is too severe vs IS.

### Layer 2.5: Data-Driven Quality Gates *(NEW — 2026-04-04)*

> Empirical gates derived from 1,000 closed dashboard picks. Applied **before** forward test
> entry to prevent garbage picks from polluting test portfolios.

| Gate | Threshold | Evidence | Action |
|------|-----------|----------|--------|
| **Score Floor** | Score ≥ 40 | Score < 40 = 33.9% WR (372 picks) | Hard block — pick never enters forward test or dashboard |
| **Promotion Score Floor** | Score ≥ 60 | Score ≥ 60 = 75.2% WR | Required for PRODUCTION status |
| **Trust Floor (LONGs)** | Trust ≥ 4 for LONG picks | LONG + Trust 0-3 = 36.2% WR (506 picks) | Block LONG picks with Trust < 4 |
| **Toxic Combo Kill** | Block LONG + Conf ≥ 0.90 | 19.5% WR on 41 picks — worst combo | Hard block |
| **Dead Zone Flag** | Flag LONG + Conf 0.60-0.69 | 31.3% WR on 182 picks | Score penalty (-12), not hard block |
| **Overconfidence Penalty** | Conf ≥ 0.90 (any direction) | 22.9% WR system-wide | Score penalty (-20) |
| **SHORT Base Bonus** | SHORT direction | 56.7% WR vs LONG 48.7% (+8pp) | Score bonus (+5) |

**Recalibrate quarterly** as closed pick count grows past 2,000.

### Layer 3: Walk-Forward
- Rolling train window (example: 2 years) + forward test (example: 3 months).
- Re-estimation allowed only in train window.
- Mandatory for promotion.
- **[TWEAK] Mandate weekly refresh with minimum 200 picks per run** (currently 81, last run 2026-03-14 = 21 days stale).
- **[TWEAK] Staleness gate: if `walk_forward_report.json` > 7 days old, block all new promotions.**
- **[TWEAK] Walk-forward must cover ≥ 3 asset classes** (currently crypto-only).

### Layer 4: Statistical Significance
- Raw p-value + multiple-testing correction:
  - Benjamini-Hochberg (FDR)
  - Bonferroni
- Fisher combined p-value for strategy families.

### Layer 5: Robustness/Stress
- Bootstrap / Monte Carlo confidence intervals.
- Regime checks (bull/bear/sideways/high-vol).
- Shock scenarios (drawdown and recovery behavior).
- **[TWEAK] Add Fear & Greed Index (FGI) as a regime dimension.**
  - `st_fear_greed_contrarian` = 87.7% WR during extreme fear confirms FGI matters.
  - Required FGI regime buckets: Extreme Fear (0-20), Fear (20-40), Neutral (40-60), Greed (60-80), Extreme Greed (80-100).
  - Strategy must show positive edge in ≥ 2 FGI regimes to pass.
- **[TWEAK] Test hold time sensitivity.** EXPIRED exits = 94.9% WR → system may be closing winners too early. Test +50% and +100% hold time extensions for Score ≥ 60 picks.

### Layer 6: Forward Test + Test Portfolios
- Strategies passing Layers 1-5 must enter controlled test portfolios.
- Track live-like TP/SL execution and realized outcomes.
- **[CRITICAL FIX] Forward test pipeline is BROKEN — `live_forward_test_picks.json` has 0 picks.**
  - Root cause: likely a dependency failure in `alpha_engine/forward_test.py` or the GitHub Actions workflow.
  - **Health check required:** if `live_forward_test_picks.json` has 0 picks for > 24h, trigger alert.
- **[TWEAK] Forward test inherits Layer 2.5 gates:** Score ≥ 40, Trust ≥ 4 for LONGs, no LONG+Conf≥0.90.
- **[TWEAK] Forward test must track ≥ 8 strategies** (currently only `forward_test_state.json` tracks 8: GOLDEN_FILTER, MTF_GATED, ENSEMBLE_2OF3, SHORT_DOMINANT, ROCKET_PICKS, PROVEN_FOREX, COT_CARRY, QUALITY_STOCKS — but producing 0 picks).

### Layer 7: Promotion Gate
- Promote only if multi-layer pass persists in forward tracking.
- **[CRITICAL GAP] Promotion gate is disconnected from the live dashboard.** Current state: 0/5 strategies pass the promotion gate, yet 50+ strategies are live on the dashboard. The promotion gate must become the gatekeeper for dashboard inclusion.
- **[TWEAK] Auto-rehab trigger:** any strategy with ≥ 10 resolved picks and WR < 35% → auto-route to **Rehabilitation Pipeline** (Section 7). Pause original config pick generation, but do NOT kill — the signal may have value on other symbols, asset classes, or as an inverse.
  - Example: `claude_gainer_1h` (14.3% WR, 35 picks) should be auto-routed to rehabilitation, not killed. Its inverse (`claude_gainer_ml_inverse`) already has **80% WR**.
  - Example: `winner_pattern_precursor` was 0% WR but its inverse is **81.2% WR, PF 2.35** — killing would have destroyed massive value.
- **[TWEAK] Gini concentration threshold 0.40** is failing everything (current Gini = 0.71). Either lower threshold to 0.60 or exempt Gini from promotion gate until diversification improves.

---

## 3) Promotion Status Model

Every strategy must have one status:

**Forward path (promotion):**
- `CANDIDATE`
- `BACKTEST_PASS`
- `WF_PASS`
- `STATS_PASS`
- `FORWARD_PASS`
- **`DATA_VALIDATED`** *(NEW)* — passes Layer 2.5 data-driven gates (Score ≥ 60, Trust ≥ 4, no toxic combos)
- `PRODUCTION`

**Rehabilitation path (underperformers):**
- `PROBATION` — early warning, still generating picks
- **`REHAB_CANDIDATE`** *(NEW)* — auto-triggered when WR < 35% on ≥ 10 picks. Original config paused.
- **`REHAB_STAGE_1`** *(NEW)* — cross-symbol backtest in progress
- **`REHAB_STAGE_2`** *(NEW)* — cross-asset class backtest in progress
- **`REHAB_STAGE_3`** *(NEW)* — inverse variant test in progress
- **`REHAB_STAGE_4`** *(NEW)* — parameter mutation grid in progress
- **`REHAB_STAGE_5`** *(NEW)* — regime-filtered variant test in progress
- **`REHAB_STAGE_6`** *(NEW)* — crossover blending with proven winners in progress
- **`REHABILITATED`** *(NEW)* — a working variant was found and deployed (with suffix like `_inverse`, `_xasset`, `_mut_tight`)
- **`EXHAUSTED`** *(NEW, replaces BANNED)* — ALL 6 rehabilitation stages tried and failed. Strategy archived in graveyard. **Annual review required** — market regimes change.

> **⚠️ PHILOSOPHY:** A strategy is NEVER "killed" or "banned" outright. Every underperformer
> enters the rehabilitation pipeline first. Evidence: `winner_pattern_precursor` was 0% WR
> but its inverse is 81.2% WR (PF 2.35). `claude_gainer_ml_inverse` is 80% WR (PF 19.56).
> Killing a strategy destroys the signal — inverting or relocating it extracts value.

> **⚠️ IMPLEMENTATION GAP:** No `strategy_registry.json` exists. The status model is defined
> but not enforced. Create a lightweight JSON registry that the dashboard generator reads.
> Each strategy entering the dashboard must have a registry entry with a valid status.
> **Add `strategy_rehabilitation_tracker.json`** to track each strategy's progress through
> the 6-stage pipeline with results at each stage.

---

## 4) Current Live Test Systems

### A) Real-money simulation tracker
- File: `alpha_engine/real_money_tracker.py`
- Purpose: strict picks from proven strategies and quality gates.
- **Status (2026-04-04):** 10 active positions, 6 closed. Running.

### B-E) Theory portfolios
- File: `alpha_engine/portfolio_theories.py`
- B: News sentiment contrarian
- C: Technical confluence
- D: Funding contrarian
- E: Multi-asset proven

### Institutional validation
- File: `alpha_engine/validation/institutional_backtest_suite.py`
- Output:
  - `alpha_engine/data/institutional_backtest_report.json`
  - `alpha_engine/data/institutional_backtest_report_round2.json`

### Forward test (8 strategies tracked)
- File: `alpha_engine/forward_test.py`
- State: `alpha_engine/data/forward_test_state.json` (8 strategies: GOLDEN_FILTER, MTF_GATED, ENSEMBLE_2OF3, SHORT_DOMINANT, ROCKET_PICKS, PROVEN_FOREX, COT_CARRY, QUALITY_STOCKS)
- **⚠️ Status (2026-04-04):** Producing 0 picks. Pipeline needs repair.

### DNA Mutation Engine
- File: `alpha_engine/auto_dna_mutator.py`, `alpha_engine/dna_mutation_engine.py`
- Output: `alpha_engine/data/dna_mutation_report.json`
- **Status (2026-04-04):** Identified 5 super losers, 6 super winners. Mutations generated but NOT connected to live banning pipeline.

### GitHub Actions Workflows (Testing-Related)
| Workflow | Schedule | Status |
|----------|----------|--------|
| `forward_test.yml` | Every 4h | ⚠️ Running but 0 picks output |
| `forward-test-daily.yml` | Weekdays 14:30 UTC + every 6h | Running |
| `forward-test-new-strategies.yml` | Every 6h | Running |
| `walk-forward-backtest.yml` | Sundays 08:00 UTC | ⚠️ Last run March 14 (stale) |
| `statistical_validation.yml` | Daily midnight UTC | Running |
| `battle_test.yml` | Hourly | Running |
| `alpha-weekly-validation.yml` | Mondays 06:00 UTC | Running |

---

## 5) Round-2 Test Evidence (Executed)

Commands run:
- `python -m alpha_engine.validation.institutional_backtest_suite --strategy-results alpha_engine/data/walk_forward_results.json --pair-results backtest_results/walk_forward_results.json --output alpha_engine/data/institutional_backtest_report_round2.json --bootstrap-sims 10000`
- `python alpha_engine/real_money_tracker.py`
- `python alpha_engine/portfolio_theories.py`

Observed highlights:
- Multiple-testing significant (BH + Bonferroni): `ema_crossover`, `bollinger_bounce`
- Robust-edge candidates after strict gates: none
- Portfolio risk remains elevated for several pairs (example: high SL-hit frequencies on `SOL/USDT`, `DOGE/USDT`, `ARB/USDT`)
- Test portfolios are active and producing fresh tracked positions.

> **⚠️ STALE DATA (2026-04-04):** Round-2 evidence is from April 2. Walk-forward report is from
> March 14 (21 days stale). Promotion gate report shows 0/5 production candidates. Gini
> concentration 0.71 (above 0.40 threshold) indicates over-concentration. The promotion gate
> strategies (ema_crossover, bollinger_bounce, rsi_reversal, funding_rate_contrarian,
> volume_breakout) are not representative of the 50+ strategies actually live on the dashboard.

### Further QA (local, 2026-04-02)

- Regenerated `institutional_backtest_report_round2.json` with `--bootstrap-sims 10000`; refreshed `promotion_gate_report.json` from that file (`production_candidates: 0`).
- `tools/validate_production_pnl.py` — re-scan production JSON for zero / extreme PnL anomalies (see `alpha_engine/data/pnl_validation_report.json`).
- `pytest tests/test_validation_gate.py tests/test_quality_gates.py` — **15 passed** after aligning `passes_active_gate` / `passes_smart_gate` with tests: non-crypto raw score floor + blocked asset×strategy pairs, `history_wr_bayes` in edge ratio for consensus picks, concentration exclusion for Smart Picks on non-verified rows; test fixtures use **fresh UTC timestamps** so staleness rules stay stable.

---

## 6) Scarcity Analysis (Top Strategies With Too Few Picks)

> **⚠️ NEVER EXECUTED (2026-04-04):** No `scarcity_analysis.json` exists. This section is
> purely aspirational. First execution is **Priority 7** on the implementation roadmap.

### Goal
Identify strong strategies that under-fire and test controlled entry loosening.

### Rule
Scarcity candidate if:
- win_rate >= 0.58
- profit_factor >= 1.5
- trades < percentile_30 by asset class OR trades < fixed minimum (ex: <25)

### Current Scarce Winners (from 1,000 closed pick analysis)

| Strategy | WR | Picks | PnL | Status |
|----------|----|-------|-----|--------|
| `copy_trader_highscore` | 92.3% | 13 | +13.8% | Scarce — needs more picks |
| `super_signals` | 84.6% | 13 | +17.1% | Scarce — needs more picks |
| `signal_validation` | 100% | 6 | +18.0% | ⚠️ In BLOCKED list (prior 0% WR data) — if recent 6-pick WR holds, remove from BLOCKED |
| `st_fear_greed_contrarian` | 87.7% | 138 | +129.5% | Not scarce — but could generate more |

### SHORT Direction Scarcity
- SHORT = 240/1000 picks (24%) but 56.7% WR vs LONG 48.7%.
- **[NEW] Test generating more SHORT signals** from existing strategies. SHORT is under-represented but outperforms.

### What-if loosening plan
For each scarce strategy, test variants:
- Entry threshold loosen +5%, +10%, +15%
- Volume filter loosen (ex: 1.5x -> 1.3x)
- RSI bands relaxed by 2-5 points

Accept loosened variant only if:
- pick_count increases >= 30%
- win_rate drop <= 5 percentage points
- PF remains >= 1.5

---

## 7) Rehabilitation-First Pipeline *(OVERHAULED — 2026-04-04)*

> **CORE PHILOSOPHY: Rehabilitate, don't kill.** Every underperforming strategy contains
> a signal — it may just be applied to the wrong symbol, wrong asset class, wrong direction,
> or wrong parameters. Evidence:
> - `winner_pattern_precursor`: 0% WR LONG → inverse = **81.2% WR, PF 2.35** (48 trades)
> - `claude_gainer_ml`: low WR → inverse = **80.0% WR, PF 19.56** (10 trades)
> - `st_multi_day_momentum`: 0% WR → inverse = profitable after validation
>
> **Killing these strategies would have destroyed massive value.**

### Trigger: Auto-Detection

A strategy enters the rehabilitation pipeline when ANY of these fire:
- WR < 35% on ≥ 10 resolved trades
- PnL < -15% cumulative
- 5+ consecutive losses
- DNA mutation engine flags as "super loser"

**Action:** Status → `REHAB_CANDIDATE`. Pause pick generation for the **original config only**
(not the whole strategy family). Still generates picks if a working variant is found later.

**Existing code:** `alpha_engine/strategy_killer.py` `KILL_CRITERIA` → repurpose as `REHAB_CRITERIA`

### Stage 1: Cross-Symbol Backtest *(1-3 days)*

Test the **same strategy logic** on every symbol in its asset class. A strategy that fails on
BTC might work beautifully on ETH, SOL, or BNB.

| Asset Class | Test Universe |
|-------------|---------------|
| Crypto | ~30 symbols: BTC, ETH, SOL, BNB, XRP, ADA, DOGE, AVAX, DOT, LINK, UNI, AAVE, etc. |
| Equities | Sector ETFs (XLK, XLF, XLE, etc.) + top 20 stocks (AAPL, MSFT, NVDA, etc.) |
| Forex | 8 major pairs: EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CHF, NZD/USD, USD/CAD, EUR/GBP |
| Commodities | GC (gold), SI (silver), CL (oil), NG (nat gas), HG (copper) |

**Use:** `alpha_engine/backtest/engine.py` + `alpha_engine/cross_sectional.py`

**Pass criteria:** WR ≥ 50% AND PF ≥ 1.2 on ≥ 2 new symbols with ≥ 5 trades each

**If PASS:** Deploy on winning symbols with `_[symbol]` suffix. Mark original symbol as
"strategy-symbol mismatch." **The strategy LIVES — it just needed different symbols.**

**If FAIL:** → Stage 2

### Stage 2: Cross-Asset Class Backtest *(1-3 days)*

Test on **completely different asset classes**. A crypto strategy might work on forex,
a forex strategy might work on commodities. Market microstructure patterns often transfer.

| Original Class | Test Against |
|---------------|---------------|
| Crypto | Equities, Forex, Commodities, ETFs |
| Equities | Crypto, Forex, Commodities |
| Forex | Crypto, Equities, Commodities |
| Commodities | Crypto, Equities, Forex |

**Use:** `incubator/backtest_team/failed_strategy_robustness_probe.py`
(already supports multi-pair, direction mode, TP/SL scale, timeframe)

**Pass criteria:** WR ≥ 50% on ≥ 1 new asset class with ≥ 5 trades

**If PASS:** Deploy on winning asset class with `_xasset_[class]` suffix.
**Strategy LIVES in a new home.**

**If FAIL:** → Stage 3

### Stage 3: Inverse Strategy Test *(1-2 days)*

Flip direction on ALL symbols (original + cross-symbol universe).
LONG → SHORT, SHORT → LONG, swap TP/SL.

**Use:** `alpha_engine/dna_mutation_engine.py::inverse_mutation()` +
`alpha_engine/inverse_strategies.py` + `alpha_engine/auto_dna_mutator.py` `LOSER_MUTATIONS`
(inverse, inverse_tight, inverse_wide)

**Proven precedent (already in our codebase):**
- `winner_pattern_precursor_inverse`: 81.2% WR, PF 2.35, 48 trades → PASS
- `claude_gainer_ml_inverse`: 80.0% WR, PF 19.56, 10 trades → PASS
- `st_multi_day_momentum` inverse: profitable after validation

**Pass criteria:** WR ≥ 50% on ≥ 1 symbol with ≥ 5 trades

**If PASS:** Deploy inverse variant with `_inverse` suffix.
**The strategy's SIGNAL was correct, just the DIRECTION was wrong.**

**If FAIL:** → Stage 4

### Stage 4: Parameter Mutation Grid *(2-5 days)*

Systematic grid search of parameter variants:

| Dimension | Variants | Count |
|-----------|----------|-------|
| TP scale | 0.5×, 0.7×, 1.0×, 1.5×, 2.0× | 5 |
| SL scale | 0.5×, 0.7×, 1.0×, 1.3×, 1.5× | 5 |
| Direction mode | long-only, short-only, both | 3 |
| Timeframe | 15m, 1h, 4h, 1d | 4 |
| Hold time | 0.5×, 1.0×, 2.0× | 3 |

Total: up to 900 variants (pruned by early stopping — skip combos where
first 3 trades all lose).

**Use:** `incubator/backtest_team/failed_strategy_robustness_probe.py`
(already supports direction mode, TP/SL scale, timeframe) +
`alpha_engine/auto_dna_mutator.py` mutation definitions

**Pass criteria:** ANY variant with WR ≥ 50% AND PF ≥ 1.2 on ≥ 5 trades

**If PASS:** Deploy best variant with `_mut_[variant_name]` suffix. Track lineage.

**If FAIL:** → Stage 5

**Hold time extension sub-test:** EXPIRED exits = 94.9% WR → system may be closing
winners too early. Always include +50% and +100% hold time extensions in the grid.
Also test widening TP from 3% to 4% for Score ≥ 60 picks.

### Stage 5: Regime-Filtered Variant *(1-2 days)*

Maybe the strategy only works in specific market conditions. Test with regime gates:

| Regime Type | Buckets |
|-------------|--------|
| Trend | Bull (SMA50 > SMA200), Bear (SMA50 < SMA200), Sideways (ADX < 20) |
| Volatility | High vol (ATR > 2× avg), Low vol (ATR < 0.5× avg), Normal |
| Sentiment (FGI) | Extreme Fear (0-20), Fear (20-40), Neutral (40-60), Greed (60-80), Extreme Greed (80-100) |
| Volume | High volume (> 2× MA20), Low volume (< 0.5× MA20), Normal |

**Use:** `alpha_engine/dna_mutation_engine.py` `regime_gate` mutation

**Pass criteria:** WR ≥ 55% in ≥ 1 regime bucket with ≥ 5 trades

**If PASS:** Deploy regime-gated variant with `_regime_[condition]` suffix.
**Strategy LIVES but only fires in its sweet spot.**

**If FAIL:** → Stage 6

### Stage 6: Crossover Blending *(1-2 days)*

Blend the failing strategy's signal detection with proven winners' risk management:

- Take **entry SIGNALS** from the loser (its timing may have value)
- Take **TP/SL PARAMETERS** from a proven winner
- Or: take **INVERSE direction** from loser + **parameters** from winner

Blend with top 3 proven strategies:
- `st_fear_greed_contrarian` (87.7% WR, 138 trades)
- `copy_trader_highscore` (92.3% WR, 13 trades)
- `super_signals` (84.6% WR, 13 trades)

**Use:** `alpha_engine/dna_mutation_engine.py::crossover_mutation()` (already exists)

**Pass criteria:** WR ≥ 50% AND PF ≥ 1.2

**If PASS:** Deploy crossover variant with `_xover_[donor]` suffix.

**If FAIL:** → Stage 7 (Graveyard)

### Stage 7: Graveyard (Last Resort ONLY)

> **A strategy reaches this stage ONLY after ALL 6 rehabilitation stages have been
> exhausted and documented.** This is NOT "killing" — it's archiving with full records.

**Requirements before graveyard:**
1. ✅ Full rehabilitation report exists (what was tried, results at each stage)
2. ✅ Cross-symbol tested (≥ 10 symbols)
3. ✅ Cross-asset tested (≥ 2 other asset classes)
4. ✅ Inverse tested (on all symbols)
5. ✅ Parameter grid tested (≥ 50 variants)
6. ✅ Regime gates tested (≥ 3 regime types)
7. ✅ Crossover with ≥ 2 proven winners tested

**Graveyard rules:**
- Strategy preserved for reference, **NEVER deleted**
- Code, research, and backtest data remain available
- Used as negative training data for ML classifiers
- **Annual review REQUIRED** — market regimes change. A strategy that failed in Q1 bull
  might work in Q3 bear. The graveyard feeds into `baby_strategies/STRATEGY_GRAVEYARD.md`.
- Can be pulled from graveyard if new data/conditions emerge

### Rehabilitation Tracker Schema

File: `alpha_engine/data/strategy_rehabilitation_tracker.json`

```json
{
  "strategy_id": "claude_gainer_1h",
  "original_metrics": {"wr": 0.143, "trades": 35, "pnl_pct": -168.7},
  "entered_rehab": "2026-04-04T00:00:00Z",
  "current_stage": 1,
  "stages": {
    "stage_1_cross_symbol": {
      "status": "COMPLETED",
      "symbols_tested": 28,
      "results": [
        {"symbol": "BNBUSDT", "wr": 0.52, "pf": 1.3, "trades": 8},
        {"symbol": "SOLUSDT", "wr": 0.48, "pf": 0.9, "trades": 6}
      ],
      "best_result": {"symbol": "BNBUSDT", "wr": 0.52, "pf": 1.3, "trades": 8},
      "passed": true,
      "completed_at": "2026-04-06T12:00:00Z"
    },
    "stage_2_cross_asset": {"status": "SKIPPED", "reason": "Passed stage 1"},
    "stage_3_inverse": {"status": "NOT_STARTED"},
    "stage_4_mutation_grid": {"status": "NOT_STARTED"},
    "stage_5_regime_filtered": {"status": "NOT_STARTED"},
    "stage_6_crossover": {"status": "NOT_STARTED"}
  },
  "verdict": "REHABILITATED",
  "deployed_variant": "claude_gainer_1h_bnb",
  "deployed_at": "2026-04-06T12:00:00Z"
}
```

### Current Rehabilitation Queue (from 1,000 closed pick analysis)

> **These strategies were previously flagged as "kill candidates." Under the rehabilitation-first
> philosophy, they are now rehabilitation candidates — each must go through all 6 stages
> before any graveyard decision.**

| Strategy | WR | Picks | PnL | Rehab Priority | Notes |
|----------|----|-------|-----|---------------|-------|
| `claude_gainer_1h` | 14.3% | 35 | -168.7% | **P1 — HIGH** | `claude_gainer_ml_inverse` already 80% WR! Test Stage 3 inverse first |
| `enhanced_ml_A_xgboost` | 32.7% | 49 | -18.0% | **P1 — HIGH** | 49 trades = large sample. Test cross-symbol (Stage 1) + inverse (Stage 3) |
| `widened_tp_momentum_carry` | 22.2% | 9 | -24.1% | P2 | Low sample. Test parameter grid (Stage 4) — TP is already "widened" |
| `Extreme Fear Contrarian Buy` | 20.0% | 5 | -3.5% | P2 | Try as SHORT (inverse). Fear contrarian SHORT might work |
| `crypto_adx_pullback_trendresume_v1` | 14.3% | 7 | -2.9% | P2 | Test on other timeframes (Stage 4) + equities (Stage 2) |

### Existing Rehabilitation Infrastructure (Already Built)

| Tool | File | Capability | Status |
|------|------|-----------|--------|
| DNA Mutation Engine | `alpha_engine/dna_mutation_engine.py` | Inverse, tighter_stops, wider_stops, regime_gate, crossover | ✅ Working |
| Auto DNA Mutator | `alpha_engine/auto_dna_mutator.py` | "Mutate before kill" — inverse/tight/wide mutations | ✅ Working (but 0 mutations generated — needs connection fix) |
| Inverse Strategies | `alpha_engine/inverse_strategies.py` | Validated inverse picks from mutation backtest | ✅ Working — 2 proven inverses |
| Robustness Probe | `incubator/backtest_team/failed_strategy_robustness_probe.py` | Direction mode, TP/SL scale, timeframe testing | ✅ Working |
| Cross-Sectional | `alpha_engine/cross_sectional.py` | Momentum rank, relative strength across symbols | ✅ Working |
| Backtest Engine | `alpha_engine/backtest/engine.py` | Full event-driven backtest on any symbol | ✅ Working |
| Strategy Graveyard | `baby_strategies/STRATEGY_GRAVEYARD.md` | DNA-integrated archive for exhausted strategies | ✅ Documented |

**Key gap:** These tools exist but are not connected into a unified pipeline.
The rehabilitation router (replacing `strategy_killer.py`) needs to orchestrate
Stages 1-6 automatically using these existing tools.

### Promotion Rule for Rehabilitated Variants
- Must re-pass Layers 1-6 of the testing stack
- Must outperform parent on OOS and forward test
- Lineage tracked: parent strategy, rehabilitation stage, variant parameters
- If rehabilitated variant later underperforms → re-enters pipeline at Stage 1
  (strategies can go through rehabilitation multiple times as market regimes change)

---

## 8) Super-Strategy Detection

A strategy is `SUPER_CANDIDATE` if:
- Passes significance after correction
- Positive OOS performance across >=3 symbols
- Works in >=2 asset classes
- Regime pass in bull + bear + high-vol buckets
- No single-symbol concentration > 60% of total edge

Upgrade to `SUPER_STRATEGY` only after forward portfolio confirmation.

### Current Super-Strategy Candidates (from 1,000 closed pick analysis)

> **⚠️ NOT SYSTEMATICALLY IMPLEMENTED.** The criteria above exist on paper but no
> `super_strategy_candidates` tracking exists. Bootstrap from these data-validated candidates:

| Strategy | WR | Picks | PnL | Cross-Symbol? | Evidence |
|----------|----|-------|-----|---------------|----------|
| `st_fear_greed_contrarian` | 87.7% | 138 | +129.5% | Yes (BTC/ETH/SOL/BNB+) | Best system-wide strategy |
| `claude_gainer_st` (source) | 85.5% | 166 | +155.1% | Yes (multiple crypto) | Best volume source |
| `copy_trader_highscore` | 92.3% | 13 | +13.8% | TBD — needs more picks | Highest WR |

---

## 9) MySQL Tracking Schema

> **⚠️ TABLES NOT CREATED (2026-04-04).** The SQL schema below was defined but never
> deployed to `ejaguiar1_stocks`. MySQL connection code exists in `alpha_engine/audit_sync.py`
> and `alpha_engine/incubator/incubator_db.py` but uses different tables (`algorithms`, etc.).
>
> **Recommendation:** Either create these tables and connect, or implement a simpler
> JSON-based registry (`alpha_engine/data/strategy_registry.json` +
> `alpha_engine/data/strategy_test_runs.json`) that matches the current JSON-file architecture.
> A working JSON registry is better than an aspirational MySQL schema.

Run these tables in `ejaguiar1_stocks` and sync from pipeline jobs.

```sql
CREATE TABLE IF NOT EXISTS strategy_registry (
  strategy_id VARCHAR(128) PRIMARY KEY,
  asset_class VARCHAR(32) NOT NULL,
  status VARCHAR(32) NOT NULL,
  parent_strategy_id VARCHAR(128) NULL,
  mutation_type VARCHAR(32) NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS strategy_test_runs (
  run_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  strategy_id VARCHAR(128) NOT NULL,
  test_layer VARCHAR(32) NOT NULL,
  symbol VARCHAR(64) NULL,
  asset_class VARCHAR(32) NULL,
  period_start DATETIME NULL,
  period_end DATETIME NULL,
  trades INT DEFAULT 0,
  win_rate DECIMAL(8,4) NULL,
  profit_factor DECIMAL(10,4) NULL,
  sharpe DECIMAL(10,4) NULL,
  max_drawdown DECIMAL(10,4) NULL,
  p_value DECIMAL(12,8) NULL,
  q_value_bh DECIMAL(12,8) NULL,
  p_value_bonf DECIMAL(12,8) NULL,
  pass_flag TINYINT(1) DEFAULT 0,
  metadata_json TEXT NULL,
  created_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS strategy_symbol_coverage (
  strategy_id VARCHAR(128) NOT NULL,
  symbol VARCHAR(64) NOT NULL,
  asset_class VARCHAR(32) NOT NULL,
  tested_backtest TINYINT(1) DEFAULT 0,
  tested_walkforward TINYINT(1) DEFAULT 0,
  tested_forward TINYINT(1) DEFAULT 0,
  last_result_at DATETIME NULL,
  PRIMARY KEY (strategy_id, symbol)
);

CREATE TABLE IF NOT EXISTS strategy_whatif_results (
  whatif_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  strategy_id VARCHAR(128) NOT NULL,
  variant_name VARCHAR(128) NOT NULL,
  variant_type VARCHAR(32) NOT NULL,
  params_json TEXT NOT NULL,
  baseline_win_rate DECIMAL(8,4) NULL,
  baseline_pf DECIMAL(10,4) NULL,
  baseline_trades INT NULL,
  variant_win_rate DECIMAL(8,4) NULL,
  variant_pf DECIMAL(10,4) NULL,
  variant_trades INT NULL,
  delta_win_rate DECIMAL(8,4) NULL,
  delta_pf DECIMAL(10,4) NULL,
  delta_trades INT NULL,
  accepted TINYINT(1) DEFAULT 0,
  created_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS test_portfolio_positions (
  portfolio_name VARCHAR(64) NOT NULL,
  position_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  strategy_id VARCHAR(128) NOT NULL,
  symbol VARCHAR(64) NOT NULL,
  direction VARCHAR(8) NOT NULL,
  entry_price DECIMAL(18,8) NOT NULL,
  take_profit DECIMAL(18,8) NOT NULL,
  stop_loss DECIMAL(18,8) NOT NULL,
  status VARCHAR(16) NOT NULL,
  opened_at DATETIME NOT NULL,
  closed_at DATETIME NULL,
  pnl_pct DECIMAL(10,4) NULL,
  metadata_json TEXT NULL
);

CREATE TABLE IF NOT EXISTS super_strategy_candidates (
  strategy_id VARCHAR(128) PRIMARY KEY,
  symbols_passed INT DEFAULT 0,
  asset_classes_passed INT DEFAULT 0,
  regimes_passed INT DEFAULT 0,
  concentration_ratio DECIMAL(10,4) NULL,
  fisher_p DECIMAL(12,8) NULL,
  status VARCHAR(32) NOT NULL,
  notes TEXT NULL,
  updated_at DATETIME NOT NULL
);
```

---

## 10) Operational Queries

### A) Top performers with scarcity
```sql
SELECT strategy_id, asset_class,
       AVG(win_rate) AS avg_wr,
       AVG(profit_factor) AS avg_pf,
       SUM(trades) AS total_trades
FROM strategy_test_runs
WHERE test_layer IN ('walk_forward','forward_test')
GROUP BY strategy_id, asset_class
HAVING AVG(win_rate) >= 0.58
   AND AVG(profit_factor) >= 1.5
   AND SUM(trades) < 25
ORDER BY avg_pf DESC, avg_wr DESC;
```

### B) Losers for remediation queue
```sql
SELECT strategy_id, asset_class,
       AVG(win_rate) AS avg_wr,
       AVG(profit_factor) AS avg_pf,
       AVG(max_drawdown) AS avg_dd
FROM strategy_test_runs
WHERE test_layer IN ('walk_forward','forward_test')
GROUP BY strategy_id, asset_class
HAVING AVG(win_rate) < 0.45
    OR AVG(profit_factor) < 1.0
ORDER BY avg_pf ASC, avg_wr ASC;
```

### C) Super-strategy candidates
```sql
SELECT strategy_id,
       COUNT(DISTINCT symbol) AS symbols_ok,
       COUNT(DISTINCT asset_class) AS classes_ok
FROM strategy_test_runs
WHERE pass_flag = 1
GROUP BY strategy_id
HAVING COUNT(DISTINCT symbol) >= 3
   AND COUNT(DISTINCT asset_class) >= 2
ORDER BY classes_ok DESC, symbols_ok DESC;
```

---

## 11) Cadence

> **⚠️ CADENCE NOT BEING FOLLOWED (2026-04-04).** Reality check below.

- Hourly:
  - Update test portfolios (`real_money_tracker`, `portfolio_theories`) ✅ Running
  - Sync open/closed positions to MySQL ❌ MySQL tables not created
  - **[NEW] Run `testing_health_check.py`** (see Section 14)
- Daily:
  - Run institutional suite + scarcity and rehabilitation queues ❌ Scarcity never run, rehab pipeline not connected
  - Execute what-if batch ❌ Never executed
  - **[NEW] Run auto-rehab detection sweep** — route strategies with WR < 35% (≥ 10 picks) to rehabilitation pipeline
  - **[NEW] Advance active rehabilitation candidates** through next pipeline stage
  - **[NEW] Verify forward test pipeline health** (alert if 0 picks)
- Weekly:
  - Walk-forward full run ⚠️ Last run 21 days ago (should be every Sunday)
  - Promotion/probation/rehabilitation decisions ❌ No strategy_registry to track decisions
  - **[NEW] Refresh walk-forward with ≥ 200 picks**
  - **[NEW] Run scarcity analysis on closed picks**
  - **[NEW] Process 5-10 strategies through rehabilitation pipeline** (batch processing)
- Monthly *(NEW)*:
  - **Recalibrate Layer 2.5 gates** from latest closed pick data
  - **Review super-strategy candidates** for promotion
  - **Audit rehabilitation pipeline results** — promote successful variants, advance stalled candidates
  - **Annual graveyard review** — re-evaluate exhausted strategies against new market conditions

---

## 12) Definition of Done (Per Strategy)

A strategy is production-eligible only when all are true:
- Walk-forward pass
- Multiple-testing corrected significance
- Bootstrap CI not implying fragile edge
- Forward test positive expectancy in portfolio tracking
- Symbol coverage logged in DB
- Scarcity/loser what-if checks completed and recorded
- **[NEW] Passes Layer 2.5 data-driven gates (Score ≥ 60, Trust ≥ 4 for LONGs, no toxic combos)**
- **[NEW] Strategy registry entry exists with `DATA_VALIDATED` or `PRODUCTION` status**
- **[NEW] Not in active rehabilitation (status `REHAB_STAGE_*`) or exhausted**

---

## 13) Data-Driven Calibration Tables *(NEW — 2026-04-04)*

> Empirical calibration from 1,000 closed dashboard picks. These tables define the thresholds
> used in Layer 2.5 gates and should be refreshed quarterly.

### Score Buckets
| Bucket | Picks | WR | Action |
|--------|-------|----|--------|
| < 40 | 372 | 33.9% | **Hard block** — never enters forward test or dashboard |
| 40–59 | 178 | 57.3% | Allow — moderate edge |
| 60–79 | 285 | 73.5% | Preferred — strong edge |
| 80–99 | 165 | 85.7% | Elite tier |

### Trust Score Buckets
| Bucket | Picks | WR | Action |
|--------|-------|----|--------|
| 0–3 | 610 | 38.0% | ⚠️ Penalty for LONGs (-15), block LONG if Trust < 4 |
| 4–5 | 134 | 57.6% | Good |
| 6–7 | 256 | 77.0% | **Strongest single predictor** — bonus +15 |

### Confidence Buckets
| Bucket | Picks | WR | Action |
|--------|-------|----|--------|
| < 0.55 | 287 | 48.7% | Neutral |
| 0.55–0.59 | 187 | 42.2% | Mild penalty |
| 0.60–0.64 | 139 | 28.8% | 🔴 **Dead zone** — penalty -10 |
| 0.65–0.69 | 82 | 46.7% | Mild penalty -5 |
| 0.70–0.74 | 69 | 49.3% | Neutral |
| 0.75–0.79 | 119 | **86.5%** | ✅ **Sweet spot** — bonus +18 |
| 0.80–0.84 | 15 | 60.0% | Neutral |
| 0.85–0.89 | 8 | 37.5% | ⚠️ Small sample |
| 0.90+ | 48 | **22.9%** | 🔴 **Overconfident** — penalty -20 |

### Direction Bias
| Direction | Picks | WR | PnL |
|-----------|-------|----|-----|
| LONG | 760 | 48.7% | +121.13% |
| SHORT | 240 | **56.7%** | +111.24% |

SHORT outperforms LONG by 8pp. SHORT is under-represented (24% of volume).

### Toxic Combos (BLOCK)
| Combo | Picks | WR | Action |
|-------|-------|----|--------|
| LONG + Conf ≥ 0.90 | 41 | **19.5%** | ☠️ Hard block |
| LONG + Trust 0–3 | 506 | **36.2%** | 🔴 Block or heavy penalty |
| LONG + Conf 0.60–0.69 | 182 | **31.3%** | 🔴 Penalty -12 |

### Elite Combos (PROTECT)
| Combo | Picks | WR | Action |
|-------|-------|----|--------|
| Conf 0.75–0.79 (any dir) | 119 | **86.5%** | ✅ Bonus +18 |
| Trust 6–7 (any dir) | 256 | **77.0%** | ✅ Bonus +15 |
| LONG + Trust 6–7 | 200 | **80.0%** | ✅ Elite LONG zone |
| Score ≥ 80 | 165 | **85.7%** | ✅ Maximum trust |

### Exit Reason Analysis
| Exit Reason | WR | Insight |
|-------------|----|---------|
| EXPIRED | **94.9%** | System closes winners too early — extend hold times |
| TP_HIT | ~65% | Working as intended |
| SL_HIT | ~5% | Stop losses are doing their job |

### Source System Rankings (min 10 resolved)
| Source | Picks | WR | PnL | Verdict |
|--------|-------|----|-----|---------|
| `claude_gainer_st` | 166 | 85.5% | +155.1% | 🏆 Elite — protect |
| `copy_trader_intel` | 11 | 63.6% | +107.0% | ✅ Strong PnL |
| `battleground` | 128 | 53.1% | +33.0% | ✅ Volume + profit |
| `alpha_engine` | 277 | 39.4% | +38.1% | ⚠️ Below 50% but net positive |
| `alpha_engine_fast` | 38 | 39.5% | -20.1% | 🔴 Losing — review |
| `claude_gainer` | 35 | 14.3% | -168.7% | 🔄 **Rehabilitation candidate** — inverse already 80% WR |
| `aggregated_picks` | 12 | 16.7% | -8.3% | 🔄 **Rehabilitation candidate** — test cross-symbol + inverse |

### Symbol Performance (min 5 resolved)
**Best:** HBARUSDT (100%, 5 picks), DOGEUSDT (92%, 13 picks), LTCUSDT (91%, 11 picks)  
**Worst:** XMR (0%, 23 picks, -115% PnL), KASUSDT (12%, 25 picks), ENAUSDT (12.5%, 8 picks), IMXUSDT (0%, 7 picks)

---

## 14) Priority Implementation Roadmap *(NEW — 2026-04-04)*

| # | Task | Impact | Effort | Status |
|---|------|--------|--------|--------|
| 1 | **Fix forward test pipeline** (0 picks) | Critical — Layer 6 broken | Medium | ✅ FIXED (2026-04-04) |
| 2 | **Add Score Floor ≥ 40 as hard gate** in quality_gates.py | High — eliminates 37% of losing volume | Low | ❌ Not started |
| 3 | **Build rehabilitation pipeline router** — connect `strategy_killer.py` → `auto_dna_mutator.py` → `failed_strategy_robustness_probe.py` into unified 6-stage pipeline | High — extracts value from underperformers instead of destroying them | Medium | ❌ Not started |
| 4 | **Refresh walk-forward** (21 days stale) | Medium — Layer 3 stale | Medium | ❌ Not started |
| 5 | **Create `strategy_registry.json`** to track statuses | Medium — enables status model | Low | ✅ DONE (2026-04-04) |
| 6 | **Add `testing_health_check.py`** daily script | Medium — prevents future staleness | Medium | ❌ Not started |
| 7 | **Run first scarcity analysis** | Medium — unlocks scarce winners | Low | ❌ Not started |
| 8 | **Add hold time extension test** (EXPIRED = 94.9% WR) | Medium — could improve PnL significantly | Medium | ❌ Not started |
| 9 | **Deploy MySQL tables** or implement JSON registry alternative | Low — tracking infrastructure | Medium | ❌ Not started |
| 10 | **Implement auto-rehab triggers** in dashboard generator — route underperformers to rehabilitation pipeline instead of killing | Medium — closes status model loop | Medium | ❌ Not started |

### `testing_health_check.py` Specification

Daily script that reports:
1. Walk-forward staleness (days since last run, alert if > 7)
2. Forward test pick count (alert if 0 for > 24h)
3. Promotion gate coverage (% of active strategies evaluated)
4. Strategies live on dashboard but not in registry
5. Strategies below rehabilitation threshold (WR < 35%, ≥ 10 resolved) not yet in pipeline
6. Layer 2.5 gate calibration age (alert if > 90 days)
7. **Rehabilitation pipeline status** — strategies in each stage, stalled candidates (> 7 days in same stage)
8. **Exhausted strategies due for annual review** (graveyard entries > 90 days old)

**Deployment:** Add as a new GitHub Actions workflow (`testing-health-check.yml`) running daily at 06:00 UTC, or integrate into the existing `statistical_validation.yml` workflow as an additional step.

### Rehabilitation Pipeline Implementation Plan

**Week 1:** Create `strategy_rehabilitation_tracker.json` schema + repurpose `strategy_killer.py` as `strategy_rehab_router.py`

**Week 2:** Wire the router to existing tools:
- Stage 1 (cross-symbol) → `backtest/engine.py` with multi-symbol loop
- Stage 3 (inverse) → `auto_dna_mutator.py` + `inverse_strategies.py`
- Stage 4 (mutations) → `failed_strategy_robustness_probe.py`

**Week 3:** Begin batch rehabilitation of highest-priority candidates:
- `claude_gainer_1h` → Stage 3 first (inverse already proven for `claude_gainer_ml`)
- `enhanced_ml_A_xgboost` → Stage 1 first (49 trades = good sample for cross-symbol)
- 5 DNA-identified super losers → Stages 1-3 in parallel

**Week 4+:** Process 5-10 strategies/week through the pipeline.

### Audit of Existing 69 "Killed" Strategies

> **CRITICAL:** Most of the 69 strategies in `PERMANENTLY_KILLED_STRATEGIES` were killed
> WITHOUT trying cross-symbol, cross-asset, inverse, or parameter mutations. They should
> be audited and the highest-value candidates re-entered into the rehabilitation pipeline.

**Priority for rehabilitation audit:**
1. Strategies with > 50 trades (large sample → reliable signal for inverse/cross-symbol)
2. Strategies from proven source families (e.g., `claude_gainer_*` — the family has winners)
3. Strategies already proven as inverses (e.g., `winner_pattern_precursor`, `claude_gainer_ml`)
4. Strategies with 0% WR (perfect anti-predictors → inverse should be ~100% directionally correct)
5. Strategy families with many variants killed (e.g., `crypto_soc_*` — 24 killed, but maybe
   they work on equities or with regime filtering)

**Rename goal:** Over time, rename `PERMANENTLY_KILLED_STRATEGIES` to `EXHAUSTED_REHABILITATION`
and require proof that all 6 stages were attempted before any strategy enters the set.

---

## 15) Codebuff Infrastructure Audit Findings *(2026-04-04)*

> Deep audit of actual system state, data files, and runtime behavior.
> These findings go beyond the protocol recommendations — they document **bugs, leaks,
> disconnections, and dead pipelines** discovered during live inspection.

### Finding 1: 🚨 33 Active Picks from KILLED Strategies Are Leaking Through

**Severity: CRITICAL**

Despite 69 strategies in `PERMANENTLY_KILLED_STRATEGIES`, **33 active picks** from killed
strategies are currently live on the dashboard:

| Killed Strategy | Active Picks Leaking | Root Cause |
|----------------|---------------------|------------|
| `enhanced_ml_A_xgboost` | **24** | Case-sensitivity: picks arrive as `enhanced_ml_a_xgboost` (lowercase) but kill list has `enhanced_ml_A_xgboost` (mixed case) |
| `quan_engine_position` | **5** | Picks ingested before kill was added; no retroactive purge |
| `flash-crash-reversal` | **4** | Same — no retroactive close on existing active picks |

**Root cause:** The kill check at `quality_gates.py` line 650 uses exact `strategy in PERMANENTLY_KILLED_STRATEGIES`
which is **case-sensitive**. Many picks arrive with lowercase strategy names but the kill list
uses mixed case.

**Fix required:**
1. Normalize strategy names to lowercase before checking the kill list (or store kill list in lowercase)
2. Add a retroactive purge step: when a strategy is killed, force-close all its active picks
3. Add a daily health check for leaking killed picks

### Finding 2: 🚨 Promotion Gate Covers Only 4.4% of Strategies

**Severity: CRITICAL**

| Metric | Value |
|--------|-------|
| Unique strategies on dashboard (active + closed) | **113** |
| Unique strategies in active picks | 51 |
| Unique strategies in closed picks | 74 |
| Strategies evaluated by promotion gate | **5 (4.4%)** |
| Production candidates | **0** |

The 5 strategies in the promotion gate (`bollinger_bounce`, `ema_crossover`, `rsi_reversal`,
`funding_rate_contrarian`, `macd_divergence`) are **not representative** of the 113 strategies
actually running. The gate is completely disconnected from reality.

**Promotion gate decisions (all REJECTED):**

| Strategy | Status | WR | PF | Sharpe | Gates Passed | Failed Checks |
|----------|--------|----|----|--------|-------------|---------------|
| `bollinger_bounce` | REJECT | 63.6% | 0.49 | 0.87 | 3/7 | deflated_sharpe, correlation, gini, basic_quality |
| `ema_crossover` | REJECT | 28.4% | 0.07 | -7.06 | 3/7 | posterior_prob, deflated_sharpe, gini, basic_quality |
| `rsi_reversal` | REJECT | 53.9% | 0.15 | 42.01 | 2/7 | min_trades, significance, deflated_sharpe, gini, basic_quality |
| `funding_rate_contrarian` | REJECT | 52.0% | 0.39 | 8.80 | 2/7 | min_trades, significance, deflated_sharpe, gini, basic_quality |
| `macd_divergence` | REJECT | 43.8% | 2.40 | 1.09 | 2/7 | significance, deflated_sharpe, correlation, gini, basic_quality |

**Key observation:** `gini_concentration_gate` and `basic_quality` fail for ALL 5 strategies.
Gini = 0.71 (threshold 0.40) means the gate is structurally impossible to pass with current
strategy concentration. Either lower the Gini threshold or the promotion gate will remain permanently locked.

### Finding 3: ⚠️ DNA Mutation Engine Generated 0 Mutations

**Severity: HIGH**

The DNA mutation report (generated 2026-04-03) identifies losers and winners but **produced
0 actual mutations** and merged 0 into active strategies.

**Super Losers Identified (not acted on — should enter Rehabilitation Pipeline Stage 3+):**
- `st_rsi_momentum_confluence` → try inverse, cross-symbol
- `claude_gainer_1h` → inverse already proven (80% WR for `claude_gainer_ml_inverse`)
- `st_obv_support_divergence` → try regime-filtered variant (may work in high-vol only)
- `quan_engine_scalp` → try on different timeframes (Stage 4)
- `macd_crossover` → try on equities (Stage 2) — MACD is proven on stocks

**Super Winners Identified (not amplified — should get tighter/wider/aggressive mutations):**
- `copy_hl_whale_24.5M`
- `gainer_compression_relaxed_mut`
- `st_fear_greed_contrarian`
- `hs_lb_None`
- `crypto_rsi_whaleconfirmed_v1`
- `clone_hl_copy_lb_None`

The engine is **detection-only** — it identifies but doesn't act. The mutation generation
pipeline is broken or was never connected. **This is the single biggest missed opportunity:**
the tools for rehabilitation exist, they just aren't wired together.

### Finding 4: Real Money Portfolio Snapshot

| Metric | Value |
|--------|-------|
| Virtual Capital | $10,000.00 |
| Current Equity | $10,038.40 |
| Cash | $10,000.00 |
| Total Trades | 6 closed |
| Win Rate | 50.0% (3W / 3L) |
| Total Profit | +$11.65 (+0.12%) |
| Peak Equity | $10,053.59 |
| Max Drawdown | 0.25% |
| Active Positions | 10 |

**Active positions (10):**
- 4× SHORT via `rsi_overbought`: DOGEUSDT, BTCUSDT, ASTERUSDT, ADAUSDT
- 4× LONG via `st_fear_greed_contrarian`: SOLUSDT, UNIUSDT, BNBUSDT, APTUSDT
- 1× LONG via `st_fear_greed_contrarian`: APTUSDT (**⚠️ DUPLICATE — same symbol, same direction**)
- 1× SHORT via `crypto_keltner_compression_expansion_v1`: BTCUSDT

**Issues found:**
1. **Duplicate APTUSDT LONG** — two positions on the same symbol in the same direction (entries $0.8543 and $0.857). Position dedup check missing.
2. **Only 3 strategies used** out of 113 available — the "strict picks" filter may be too strict, or the forward test pipeline (which feeds it) being broken means no new strategies are entering.
3. **BTCUSDT has duplicate SHORT exposure** — two separate SHORT positions (rsi_overbought + keltner) on the same symbol. Meanwhile the broader dashboard has LONG BTC picks from other strategies, showing no portfolio-level coordination between the real_money_tracker and dashboard picks.

### Finding 5: What-If Analysis Exists but Is Unused

File `audit_dashboard/data/whatif_analysis.json` contains:
- 26 total portfolios analyzed (16 active)
- 33 position slots across 14 unique positions
- Data exists but is **not connected to any decision pipeline**
- No what-if batch has ever been executed as specified in Section 11 cadence

### Finding 6: Non-Crypto Dashboard Display Was Broken

**Fixed during this audit session.**

The v101 payload optimization (2000→1000 closed picks cap) crowded out non-crypto closed
picks, causing a cascading failure:
1. NC quality gate used capped `payload["picks"]["recent_closed"]` instead of full `resolved_closed`
2. Gate saw 0 non-crypto history → applied 0.35× penalty to all non-crypto active picks
3. Frontend `renderNonCryptoPanel` recomputed stats from capped arrays instead of using
   server-computed `D.summary.non_crypto_performance`
4. Result: panel showed ~5 picks when reality was **103 active, 351 closed, 42.5% WR, +24.68% PnL**

**Files fixed:**
- `audit_trail/dashboard_generator.py` — NC quality gate now uses `resolved_closed` (full list)
- `audit_dashboard/template.html` — frontend now uses server-computed aggregate stats

### Finding 7: GitHub Actions Workflow Conflicts

16+ testing-related workflows run on overlapping schedules, creating git push contention:
- 3 workflows at `:00` every 4-6 hours (forward_test, forward-test-daily, forward-test-new-strategies)
- `battle_test.yml` runs hourly at `:00` alongside `pick-monitor-30min.yml` at `:00` every 2h
- Recent commits show repeated `Merge branch 'main'` entries — sign of push contention
- Staggering was attempted (`fix: stagger cron schedules`) but many workflows still cluster

### Finding 8: 113 Strategies, No Registry, No Status Tracking

The system has 113 unique strategies producing picks, but:
- No `strategy_registry.json` exists
- No strategy has a formal status (CANDIDATE/PRODUCTION/BANNED etc.)
- The only status enforcement is `PERMANENTLY_KILLED_STRATEGIES` (69 entries, case-sensitive, leaking)
- Strategies enter the dashboard through multiple ingestion paths with no central gating

### Finding 9: 🚨 Score < 40 Gate Would Block 69.3% of Current Active Picks

**Severity: CRITICAL (implementation impact)**

Live audit of 137 active dashboard picks against the proposed Layer 2.5 Score Floor gate:

| Score Bucket | Active Picks | % of Total |
|--------------|-------------|------------|
| **< 20** | **91** | **66.4%** |
| 20–39 | 4 | 2.9% |
| 40–59 | 11 | 8.0% |
| 60–79 | 4 | 2.9% |
| 80+ | 27 | 19.7% |

- **85 of 137 active picks (62%) have score = 0 or missing** — they were never scored.
- **95 picks (69.3%) would be blocked** by the Score ≥ 40 gate.
- Only **42 picks (30.7%)** would survive the gate.

**Implication:** Cannot deploy Score Floor as a hard block without first ensuring all picks are
scored before entering the dashboard. The scoring pipeline has a gap — many picks bypass
`_apply_score_penalties()` entirely. **Must fix scoring coverage before enabling the gate.**

**Recommended phased rollout:**
1. **Phase 1 (immediate):** Audit why 62% of picks have no score — fix ingestion paths that skip scoring
2. **Phase 2 (after scoring fix):** Apply Score < 40 as a soft flag (tag picks, track WR separately)
3. **Phase 3 (after 2 weeks data):** Convert to hard block once scoring coverage > 95%

### Finding 10: 🚨 36 Duplicate Symbol+Direction Combos in Active Picks (105 picks)

**Severity: CRITICAL — direct capital waste**

The dashboard has **36 unique symbol+direction combos** where multiple active picks overlap,
involving **105 of 137 picks (76.6%)**. This means 3 out of every 4 active picks are redundant.

| Worst Duplicates | Picks | Impact |
|-----------------|-------|--------|
| SOLUSDT_LONG | **7** | 7 different strategies all LONG SOL at the same time |
| BNBUSDT_LONG | **6** | 6 overlapping LONG positions |
| XRPUSDT_SHORT | **5** | 5 identical SHORT bets |
| BTCUSDT_LONG | **5** | 5 overlapping LONG positions |
| ETHUSDT_LONG | **4** | 4 overlapping LONG positions |
| ETHUSDT_SHORT | **4** | 4 overlapping SHORT positions |

**Root cause:** No position-level deduplication. Each ingestion source (alpha_engine, battleground,
copy_trader, etc.) independently generates picks without checking what's already active.

**Fix required:**
1. Add a **position dedup gate** in `dashboard_generator.py`: when a new pick arrives for a
   symbol+direction already active, either (a) keep the higher-scored pick and close the lower,
   or (b) block the new pick entirely.
2. Exempt picks from different source systems that intentionally run independent portfolios.
3. Add a dashboard metric: "effective unique positions" vs "total active picks".

### Finding 11: ⚠️ 8 Symbols Have Conflicting Directions (LONG + SHORT Simultaneously)

**Severity: HIGH — net exposure is unpredictable**

The following symbols have **both LONG and SHORT** active picks at the same time:

| Symbol | Both Directions? | Implication |
|--------|-----------------|-------------|
| ADAUSDT | LONG + SHORT | Conflicting exposure |
| BNBUSDT | LONG + SHORT | 6 LONGs vs SHORTs — heavy LONG bias |
| BTCUSDT | LONG + SHORT | 5 LONGs vs SHORTs — heavy LONG bias |
| DOGEUSDT | LONG + SHORT | Conflicting exposure |
| ETHUSDT | LONG + SHORT | 4 LONGs vs 4 SHORTs — near zero net exposure |
| SOLUSDT | LONG + SHORT | 7 LONGs vs SHORTs — heaviest LONG bias |
| WLDUSDT | LONG + SHORT | Conflicting exposure |
| XRPUSDT | LONG + SHORT | LONGs vs 5 SHORTs — heavy SHORT bias |

If a user followed all active picks, they would have **hedged-to-zero exposure** on some symbols
(e.g., ETHUSDT with 4 LONG vs 4 SHORT = effectively flat). This is pure capital waste.

**Fix required:**
1. Add a **direction conflict detection** step to the dashboard generator.
2. When LONG + SHORT exist for the same symbol, flag in the UI with a ⚠️ icon.
3. Consider a **net exposure view** on the dashboard: aggregate all active picks into net
   directional exposure per symbol.
4. Add a quality gate: if net direction conflict exists, penalize the lower-scored direction's picks.

### Finding 12: ⚠️ `alpha_engine.forward_test` Module Does Not Exist

**Severity: HIGH — explains why forward test produces 0 picks**

Module import test results:

| Module | Status |
|--------|--------|
| `alpha_engine.forward_test` | ❌ **ModuleNotFoundError** — file does not exist |
| `alpha_engine.real_money_tracker` | ✅ OK |
| `alpha_engine.auto_dna_mutator` | ✅ OK |
| `alpha_engine.portfolio_theories` | ⚠️ Untested (script crashed after 3rd import due to stderr close) |
| `alpha_engine.validation.*` | ⚠️ Untested |

The GitHub Actions workflow `forward_test.yml` likely references `alpha_engine.forward_test`
which doesn't exist, causing silent failure. The `forward_test_state.json` tracks 8 strategies
but the module that should populate `live_forward_test_picks.json` is **missing**.

**This directly explains the Layer 6 broken pipeline** documented in Section 2 and the
⚠️ status in Section 4's Forward test entry — the forward test produces 0 picks because
the module itself doesn't exist. It was either deleted, renamed, or never created.

**Fix required:**
1. Check `forward_test.yml` workflow to see what module it actually invokes.
2. Either restore the module or update the workflow to point to the correct file.
3. Validate `forward_test_state.json` is being populated after the fix.

### Finding 13: ⚠️ Test Suite Has 1 Failing Test (193 pass, 1 fail)

**Severity: MEDIUM**

```
FAILED: tests/test_dashboard_generator.py::test_pre_score_active_candidate_keeps_valid_zero_score_pick_alive
193 passed, 1 failed, 640 warnings (3.84s)
```

The failing test `test_pre_score_active_candidate_keeps_valid_zero_score_pick_alive` validates
that a pick with score=0 should still be kept alive if it's a valid candidate. This likely
broke due to the recent scoring/quality gate changes.

**Additionally:** 640 `DeprecationWarning` messages for `datetime.utcnow()` usage — should migrate
to `datetime.now(timezone.utc)` across the codebase.

**Fix required:**
1. Investigate whether the test expectation is still correct after scoring tweaks.
2. If the test is valid, fix `dashboard_generator.py` to preserve zero-score valid candidates.
3. If the test is outdated (zero-score picks should now be penalized), update the test.

### Finding 14: ✅ Data Pipeline Is Healthy (346 fresh files, 0 stale)

**Severity: POSITIVE**

All 346 JSON files in `alpha_engine/data/` have been updated within the last 7 days.
The data ingestion pipeline is running correctly — the problem is not data freshness
but **processing and gating** of that data.

Additionally, **0 active picks are stale** (> 7 days old), confirming the staleness
expiry mechanism is working correctly.

---

### Summary: Audit Severity Matrix

| # | Finding | Severity | Losing Money? | Fix Effort |
|---|---------|----------|---------------|------------|
| 1 | Killed strategies leaking (33 active picks) | 🔴 CRITICAL | Yes — 24 xgboost picks at 32.7% WR | Low (case-insensitive match) |
| 2 | Promotion gate covers 4.4% | 🔴 CRITICAL | Indirectly — no gating | High (expand gate scope) |
| 3 | DNA mutation engine 0 output (rehabilitation tools exist but disconnected) | 🟡 HIGH | No — but missing massive opportunity (proven inverses at 80%+ WR) | Medium |
| 4 | Real money portfolio dupes | 🟡 HIGH | Small — $10K virtual | Low (add dedup check) |
| 5 | What-if analysis unused | 🟡 MEDIUM | No | Low (connect to pipeline) |
| 6 | Non-crypto display broken | ✅ FIXED | Was hiding 351 closed picks | Done |
| 7 | Workflow push contention | 🟡 MEDIUM | No — but causes failed runs | Medium (stagger schedules) |
| 8 | No strategy registry | 🔴 CRITICAL | Indirectly — no governance | Medium (create JSON registry) |
| 9 | Score gate would block 69.3% of active picks | 🔴 CRITICAL | Not yet — gate not deployed | High (fix scoring coverage first) |
| 10 | 36 duplicate symbol+direction combos (105 picks) | 🔴 CRITICAL | Yes — 76.6% of picks are redundant | Medium (add dedup gate) |
| 11 | 8 symbols with conflicting LONG+SHORT | 🟡 HIGH | Yes — hedged-to-zero on some | Medium (add conflict detection) |
| 12 | `forward_test` module doesn't exist | 🟡 HIGH | Indirectly — Layer 6 dead | Low (restore/reconnect module) |
| 13 | 1 failing test in test suite | 🟡 MEDIUM | No | Low (fix test or code) |
| 14 | Data pipeline healthy (346 fresh files) | ✅ POSITIVE | N/A | N/A |

---

## 16) Hedge-Fund Upgrade Addendum *(NEW — 2026-04-05)*

> This addendum converts the audit findings plus Redis-bus peer feedback into concrete
> testing and signal-quality upgrades. Goal: fewer but higher-conviction picks, with
> honest forward performance and less dashboard noise.

### A. Backtesting realism must tighten before any new "world-class" claims

**Required execution assumptions (all asset classes):**
- **Next-bar-open fills only** for signal backtests. No same-bar close entries.
- **Asset-specific friction models** must be stored with each run:
  - Crypto: maker/taker fee + slippage by liquidity bucket
  - Equities/ETFs: commissions (if any), spread slippage, split-adjusted prices
  - Forex: spread + overnight carry
  - Futures/commodities: spread, roll cost, contract normalization, tick value
- **No promotion without live-close parity audit**: sampled closed trades must reconcile
  to independent market data within a tight tolerance (target: sign correct and <= 1.0pp
  drift for standard liquid assets).

**New mandatory test modes:**
- **Purged walk-forward with embargo** so adjacent windows do not leak information.
- **Regime-stratified validation** across trend, volatility, and Fear & Greed buckets.
- **Cross-asset holdout** for any strategy promoted as "multi-asset."
- **Capacity test**: reject strategies that only work at tiny notional or unrealistic fill quality.

### B. Confluence must mean independent agreement, not duplicate noise

The audit shows 36 duplicate symbol+direction combos and 8 symbols with simultaneous LONG
and SHORT exposure. Treat that as **false diversification** until proven otherwise.

**Confluence rules (promotion and Smart Picks):**
- Require **independent family agreement**, not just multiple variants of the same engine.
  Minimum default for tier-1 display: **2 independent systems** or an equivalent trust-weighted score.
- Apply a **clone penalty** when multiple picks share the same symbol, direction, and
  source family. The second/third clone should not count as fresh evidence.
- Add a **direction-conflict penalty**: when LONG and SHORT are both active on a symbol,
  only the stronger side remains tier-1 eligible unless the view is explicitly marked hedged.
- Add a **portfolio-level uniqueness metric**:
  - total active picks
  - unique symbol-direction positions
  - conflicting symbol count

### C. New hard filters for better live pick quality

**Do not hard-enable score-based blocking until scoring coverage is fixed.**
The audit found 62% of active picks had score `0` or missing, so enforcement must be phased:
1. Fix scoring coverage to **>= 95%** of active picks.
2. Run score floor as a shadow metric for 2 weeks.
3. Then hard-block `score < 40`.

**Additional live gates recommended now:**
- **No source, no publish**: reject picks with null `source`, `system`, or `strategy`.
- **Entry sanity gate for active and closed picks**:
  - reject decimal-scale corruption
  - enforce per-symbol or per-asset-class range checks
  - especially for futures / commodity contracts (e.g. GC=F)
- **Age gate for Smart Picks**: newly opened picks with `pnl_pct = 0` should not appear in
  Smart Picks until a minimum seasoning window passes.
- **Concentration cap**: any single symbol contributing >= 70% of a system's absolute PnL
  is flagged as toxic concentration and cannot be marketed as diversified alpha.

### D. Strategy families that deserve explicit emphasis

**Peer-confirmed strengths to expand:**
- **SHORT bias during bearish regime**: several peers found crypto SHORT frameworks materially
  outperforming LONGs when BTC is below trend / risk sentiment is weak.
- **Technical confluence with real independence**: RSI + EMA trend + volume + VWAP / market-structure
  agreement is a better promotion candidate than single-signal variants.
- **Leveraged ETF decay shorts**: JDST / LABD / SOXS / DRIP style structures backtested
  materially better than generic non-crypto longs, but must remain clearly isolated from
  commodity/futures systems.
- **Symbol-locked rehabilitations**: some "loser" families recover strongly once restricted
  to the right symbols or inverted. Keep rehabilitation-first policy, but promote only the
  repaired variant, never the original losing template.

**Families that remain on probation:**
- **Futures**: do not claim edge while price normalization and contract resolution remain suspect.
- **Any strategy with forward/backtest decay > 15 percentage points** after >= 20 closes.
- **Any strategy family with unresolved source tagging or score coverage gaps.**

### E. New protocol-level acceptance criteria

A strategy can be called **trusted / hedge-fund-grade** only if all are true:
- Backtest uses next-bar-open execution and asset-specific cost model.
- Walk-forward is refreshed within 7 days and covers the asset class actually traded.
- Forward sample has at least 20 resolved trades with acceptable decay vs backtest.
- Picks are fully attributable (`source`, `system`, `strategy`, audit cohort).
- No unresolved entry-price corruption, no toxic single-symbol concentration, and no uncontrolled
  duplicate/conflicting exposure in the published book.
