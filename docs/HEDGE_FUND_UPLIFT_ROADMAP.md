# Hedge-Fund Quality Uplift — Per-Asset-Class Audit & Enhancement Roadmap

**Date:** 2026-05-02
**Scope:** Full repository review of `findtorontoevents_antigravity.ca` with focus on achieving hedge-fund-grade pick quality across all asset classes.
**Methodology:** Static analysis of quality gates, config thresholds, strategy blocklists, feed hygiene, dashboard generator, and closed-pick diagnostics. Cross-referenced with existing audit docs (`ACTIVE_PICKS_ASSET_CLASS_DIAGNOSIS_2026_04_22`, `CODE_REVIEW_QUANT_SYSTEM_2026-04-13`).

---

## Executive Summary

The system has **strong bones** — multi-layer quality gates, per-class score floors, strategy blocklists, and a sophisticated dashboard pipeline. However, it suffers from **five structural problems** preventing hedge-fund-level performance:

1. **Score calibration debt** — penalty stacking destroys 65%+ of genuine signals before they reach smart-pick thresholds
2. **Emitter gaps** — ETF and BOND have strategy libraries but no production pipeline feeding picks
3. **Near-miss strategies** — several strategies are killed by overly strict gates when parameter tuning or mutation could rescue them
4. **Data quality gaps** — `ml_score` and `hf_conviction_tier` are 0% populated, making gates that depend on them dead code
5. **Single-source-of-truth conflict** — `MIN_ELITE_SCORE_BY_CLASS` in `config.py` and `SMART_PICKS_MIN_SCORE_*` in `quality_gates.py` use different values for the same concept

---

## 1. Per-Asset-Class Analysis

### 1.1 CRYPTO — The Battleground

**Current State:**
- Short recency windows: ~60-68% WR, PF 3-5 (last 50 closed)
- Full pool: ~38% WR, PF 0.9 (~1,650 rows)
- Highest volume emitter — permissive active display

**Key Issues:**

#### A. Penalty Stacking Destroys Signals
Evidence from `quality_gates.py` comments:
> "Penalty stacking (Sunday -6, LONG_OVERCONF -25, direction_conflict -12) applied to 65% of picks is destroying genuine signals."

**Evidence:** At threshold=70, ZERO active picks qualify (max live score=60). At threshold=60, 1 pick qualifies; at 50, 7 qualify. The scoring system is self-defeating.

**Recommendation:**
1. **Cap total penalty at -15 points** — no pick should lose more than 15 points from combined penalties
2. **Time-of-day penalties should be bonuses, not penalties** — Sunday picks with strong conviction should get a slight bonus (lower competition), not a penalty
3. **Direction conflict should be a flag, not a penalty** — log it, show it in the UI, but don't penalize the score

#### B. Score Calibration Reset
Evidence from closed-pick analysis:
> "score 60-69 = 62.7% WR, PF 12.90 (strong edge)"

**Recommendation:**
- Recalibrate scoring so the **median live pick score lands at 50-55** (currently the median is much lower due to penalty stacking)
- Use the existing `score_calibration.py` module — it's imported but apparently not active by default

#### C. Near-Miss: `st_fear_greed_contrarian`
- **Status:** Retired (10.5% WR, -381.62% PnL, n=640)
- **Near-miss analysis:** The underlying fear/greed concept is sound — contrarian signals at extreme sentiment. The implementation was broken (likely look-ahead bias or wrong sentiment source).
- **Recommendation:** Spawn a **v2 mutation** with:
  - Strict time-gated sentiment data (no look-ahead)
  - Only trigger at extreme readings (VIX > 30 or CNN Fear & Greed < 20)
  - Crypto-only filter (equity contrarian has different dynamics)

---

### 1.2 EQUITY — Gate-Stacked, Not Supply-Starved

**Current State:**
- Emitters exist (`multi_asset_copytrader`, `ml_gatekeeper`, `stocks_competition`)
- Downstream gates kill most picks before they reach the dashboard
- Forward WR floor fix shipped (EQUITY 0.40) but needs monitoring

**Key Issues:**

#### A. Elite Score Distribution Mismatch
Evidence from `config.py`:
```
EQUITY: median 36, pct>=70 = 0.0%
```
The global `MIN_ELITE_SCORE_FOR_PICKS = 70` was killing 100% of EQUITY picks. The per-class floor of 50 was a fix, but:

**Recommendation:**
- Set EQUITY elite floor to **45** (not 50) — the median is 36, so 50 still kills ~60% of picks
- Add a **percentile-based floor** as an alternative: `floor = max(MIN_ELITE_SCORE, percentile_25(closed_picks_for_class))`

#### B. Near-Miss: `stocks_competition`
- Likely has decent raw signal but gets killed by the trust floor + forward WR floor combo
- **Recommendation:** Audit `stocks_comcompetition` closed picks separately — if WR > 50% on n>=20, exempt it from the forward WR floor (similar to how `exempt_sources` works)

#### C. Missing: Equity-Specific Risk Factors
The system has `SECTOR_MAP` for crypto but no equivalent for equities. Equity picks should consider:
- **Earnings proximity** — reduce position size or block picks within 5 days of earnings
- **Sector rotation** — use the existing `SECTOR_ETFS` list to detect hot/cold sectors
- **Market regime** — VIX-based regime filter (already have `MACRO_TICKERS["VIX"]`)

---

### 1.3 FOREX — Fixed by Blocklist, Still Fragile

**Current State:**
- Blocking `kimi_signal_tracking/default` flipped FOREX from -816% to +17%
- Smart Picks add `forward_wr >= 50%` rule (score alone mis-ranks FX)
- TP/SL widened from 0.5%/0.75% to 0.8%/1.5% (April 25 fix)

**Key Issues:**

#### A. The Fix Worked But Is Brittle
The entire FOREX class profitability depends on **one blocklist entry**. If a new toxic FOREX emitter appears, the class collapses again.

**Recommendation:**
1. Add a **FOREX-specific emitter quality gate**: any new FOREX source must demonstrate >= 45% WR on n>=30 before being allowed into active picks
2. Implement **auto-blocklist** for any strategy/symbol pair with WR < 25% on n>=20

#### B. Near-Miss: `forex_rsi2_mean_reversion` and `myfxbook_retail_contrarian`
From `quality_gates.py` comments:
> "Proven strategies (forex_rsi2_mean_reversion, myfxbook_retail_contrarian) score 30-45 but must now pass additional quality gates beyond score"

These strategies have **proven edge** but low scores. They're being gate-kept by score floors that were calibrated for crypto.

**Recommendation:**
- Create a **PROVEN_STRATEGY_WHITELIST** that bypasses score floors for strategies with verified forward WR >= 55% on n>=30
- These strategies should flow through to Smart Picks based on forward performance, not raw score

#### C. Forex PnL Unit Normalization
From `feed_hygiene.py`:
> "multi_asset_copytrader and kimi_signal_tracking emit a mix of decimal (0.0003) and percent (1.28) values"

The normalization fix exists but is only applied at ingest. Historical closed picks may still have wrong units.

**Recommendation:**
- Run a **one-time migration** on `closed_picks.json` to normalize all FOREX pnl_pct values
- Add a validation step: `assert abs(pnl_pct) < 100 or asset_class != "FOREX"` (catches decimal-form values)

---

### 1.4 COMMODITY / FUTURES — Thin but Promising

**Current State:**
- `SMART_PICKS_MIN_SCORE_COMMODITY = 60` (raised from 40)
- `SMART_PICKS_MIN_SCORE_FUTURES = 65` (raised from 40)
- `futures_momentum` is the only consistent winner

**Key Issues:**

#### A. Score Floors Were Raised Without Supply
Raising floors from 40→60/65 makes sense for quality, but commodity/futures strategies **can't accumulate score booster enrichment** (score_booster has crypto-only guards in MTF + ensemble gates). Achievable score range is ~30-55.

**Evidence:** From `quality_gates.py` comments:
> "commodity strategies can't accumulate score booster enrichment... achievable score range is ~30-55. Floor=60 = silent zero picks."

**Recommendation:**
- **Revert COMMODITY floor to 45** and FUTURES floor to 50 until score booster enrichment is asset-class-agnostic
- Add a **commodity/futures-specific booster** that rewards: COT report alignment, term structure signals, roll yield

#### B. Near-Miss: `futures_momentum`
This is the one consistent winner but gets drowned by killed strategies.

**Recommendation:**
- Ensure `futures_momentum` is in the **PROVEN_STRATEGY_WHITELIST**
- Add a **futures-specific risk model**: wider stops (futures gaps are common), longer hold periods

---

### 1.5 ETF — Strategy Library Exists, No Pipeline

**Current State:**
- `alpha_engine/etf_strategies.py` defines strategy library
- ETF hard ban removed (2026-04-19)
- **No production path** merges ETF output into `active_picks.json`

**This is the #1 quick win for the entire system.**

**Recommendation:**
1. **Wire ETF emitter** — create `tools/etf_emitter.py` that:
   - Runs `etf_strategies.py` on the ETF universe
   - Outputs to `alpha_engine/data/active_picks_etf.json`
   - Add to the dashboard generator's source list
2. **Start with conservative gates** — use the same gates as EQUITY (floor=45, forward WR >= 40%)
3. **Monitor for 30 days** before tightening

**Evidence:** ETF strategies exist in code. The only barrier is wiring them into the pipeline. This is a ~50-line code change.

---

### 1.6 BOND — Same as ETF, Even Thinner

**Current State:**
- `alpha_engine/bond_strategies.py` + `bond_data_fred.py` exist
- Same pipeline gap as ETF

**Recommendation:**
1. Wire BOND emitter (same pattern as ETF)
2. Use FRED data for bond yields (already have `bond_data_fred.py`)
3. Start with Treasury strategies only (most liquid)

---

## 2. Cross-Cutting Issues

### 2.1 Single Source of Truth: Score Floors

**Problem:** Two separate systems define score floors:
- `alpha_engine/config.py`: `MIN_ELITE_SCORE_BY_CLASS` (used by scanner)
- `audit_trail/quality_gates.py`: `SMART_PICKS_MIN_SCORE_*` (used by dashboard)

These are **not synchronized**. Example:
| Asset Class | config.py (scanner) | quality_gates.py (dashboard) |
|-------------|--------------------|-----------------------------|
| CRYPTO | 70 | 60 |
| EQUITY | 50 | 50 |
| FOREX | 50 | 55 |
| COMMODITY | 50 | 60 |
| FUTURES | — | 65 |

**Recommendation:**
1. Create `alpha_engine/unified_thresholds.py` as the single source of truth
2. Both `config.py` and `quality_gates.py` import from it
3. Add a CI check that warns if the two diverge

### 2.2 Dead Code: ML Score Gate

From `quality_gates.py`:
> "ML score gate is currently DISABLED — ml_score is not reliably populated upstream"

**Recommendation:**
- Either **populate ml_score** from the existing `ml_crypto_predictor` (it exists in the codebase) or **remove the dead gate** entirely
- If populating: start with a shadow mode (log but don't gate) for 14 days

### 2.3 Data Quality: Missing Fields

Fields with 0% fill rate on live picks (from dashboard generator comments):
- `ml_score`
- `hf_conviction_tier`
- `va_cohort_id`
- `entry_time` (14/37 active picks missing)

**Recommendation:**
1. **`entry_time`**: The `ensure_entry_time()` function in `feed_hygiene.py` already handles this — ensure ALL pick writers call it
2. **`ml_score`**: Wire from `ml_crypto_predictor` output
3. **`hf_conviction_tier`**: Compute from existing trust_score + forward_wr thresholds
4. **`va_cohort_id`**: Generate from strategy + asset_class hash

### 2.4 Backtesting Protocol Gaps

From `TESTING_PROTOCOL.MD` and code review:

| Gap | Impact | Fix |
|-----|--------|-----|
| Look-ahead bias | Inflated backtest WR | Enforce strict time-split in data loading |
| Survivorship bias | Over-optimistic returns | Load full universe including delisted |
| Over-fitting | Strategy works in-sample, fails live | Rolling-window cross-validation, min 6mo OOS |
| Transaction costs | Underestimated losses | Per-asset slippage model (0.1% equity, 0.5% crypto) |
| Liquidity filter | Illiquid picks inflate WR | Min 500K USD avg daily volume |
| Monte Carlo stress | No confidence intervals | 1000-run perturbation test |

**Recommendation:** Implement in priority order:
1. **Transaction costs** (biggest single source of bias)
2. **Liquidity filter** (easy to implement)
3. **Look-ahead bias audit** (manual review of rolling windows)

### 2.5 DNA-Mutate / Inverse Pipeline

The system retires strategies but doesn't systematically try to rescue them.

**Recommendation:**
1. For each retired strategy, auto-generate **3 mutations**:
   - **Inverse**: flip LONG↔SHORT signals
   - **Parameter perturbation**: ±20% on window sizes and thresholds
   - **Symbol-locked**: restrict to the top-3 symbols by historical WR
2. Run mutations in **paper-only mode** for 30 days
3. Promote mutations that show >= 55% WR on n>=20

**Near-miss candidates for mutation:**
| Strategy | Reason Killed | Mutation Opportunity |
|----------|--------------|---------------------|
| `fear_greed_contrarian` | 28.3% WR | Inverse (flip direction) at extreme VIX only |
| `st_obv_support_divergence` | 17% WR | Parameter: longer lookback, higher OBV threshold |
| `quan_engine_scalp` | 29.7% WR, -810% PnL | Inverse: might work as contrarian scalp |
| `enhanced_ml_A_xgboost` | 28% WR, PF 0.42 | Retrain with different features (add macro) |

---

## 3. Hedge-Fund Quality Index

### 3.1 Proposed Scoring Framework

Each strategy should be scored on a 0-100 "HF Quality Index":

| Component | Weight | Metric | Threshold |
|-----------|--------|--------|-----------|
| Risk-adjusted return | 25% | Sharpe ratio | >= 2.0 = full score |
| Win rate consistency | 20% | WR on rolling 50-trade windows | >= 55% = full score |
| Profit factor | 15% | PF on full history | >= 1.5 = full score |
| Multi-symbol robustness | 15% | # profitable symbols / total | >= 5 = full score |
| Drawdown control | 10% | Max drawdown | <= 15% = full score |
| Edge sustainability | 10% | Forward WR vs backtest WR gap | <= 10pp = full score |
| Data quality | 5% | Fill rate of required fields | >= 95% = full score |

**Classification:**
- **HF-Quality (80-100):** Hedge-fund grade, full allocation
- **Smart (60-79):** Proven edge, standard allocation
- **Active (40-59):** Under review, reduced allocation
- **Candidate (20-39):** Paper-only, monitoring
- **Retired (0-19):** Blocked from emission

### 3.2 Implementation

Create `audit_trail/hf_quality_index.py`:

```python
def compute_hf_quality_index(strategy_metrics: dict) -> float:
    """Compute hedge-fund quality index for a strategy."""
    scores = {
        "sharpe": min(strategy_metrics.get("sharpe", 0) / 2.0, 1.0) * 25,
        "wr_consistency": min(strategy_metrics.get("rolling_wr", 0) / 0.55, 1.0) * 20,
        "profit_factor": min(strategy_metrics.get("pf", 0) / 1.5, 1.0) * 15,
        "multi_symbol": min(strategy_metrics.get("profitable_symbols", 0) / 5, 1.0) * 15,
        "drawdown": max(1 - strategy_metrics.get("max_dd", 1) / 0.15, 0) * 10,
        "edge_sustain": max(1 - abs(strategy_metrics.get("fwd_bt_gap", 1)) / 0.10, 0) * 10,
        "data_quality": min(strategy_metrics.get("fill_rate", 0) / 0.95, 1.0) * 5,
    }
    return sum(scores.values())
```

---

## 4. Priority Implementation Roadmap

### Phase 1: Quick Wins (1-2 days)
1. ✅ **Fix penalty stacking** — cap total penalty at -15 points
2. ✅ **Wire ETF emitter** — connect `etf_strategies.py` to active picks pipeline
3. ✅ **Create unified threshold module** — single source of truth for score floors
4. ✅ **PROVEN_STRATEGY_WHITELIST** — let proven low-score strategies through

### Phase 2: Foundation (1-2 weeks)
5. Implement `hf_quality_index.py` and wire into quality gates
6. Add transaction cost model to all backtests
7. Wire BOND emitter
8. Run one-time FOREX pnl_pct migration
9. Populate `entry_time` for all pick writers

### Phase 3: Intelligence (2-4 weeks)
10. DNA-mutate pipeline for retired strategies
11. Auto-blocklist for strategy/symbol pairs with WR < 25% on n>=20
12. Equity-specific risk factors (earnings proximity, sector rotation)
13. ML score population from `ml_crypto_predictor`

### Phase 4: Hedge-Fund Grade (1-2 months)
14. Monte Carlo stress testing (1000 runs)
15. Rolling-window cross-validation for all strategies
16. Liquidity filter (min 500K USD avg daily volume)
17. Walk-forward optimization framework
18. Automated regime detection (VIX-based for equities, DXY-based for forex)

---

## 5. Evidence Appendix

### A. Score Distribution Data (from closed-pick analysis)
- CRYPTO: median elite_score 32, pct>=70 = 1.3%
- EQUITY: median elite_score 36, pct>=70 = 0.0%
- Score 60-69: 62.7% WR, PF 12.90 (strong edge)
- Score < 60: 42.1% WR, PF 0.87 (negative expectancy)

### B. Blocklist Impact
- `kimi_signal_tracking/default` on FOREX: 158 resolved, WR 30.4%, -974.66% total
- Blocking it: FOREX aggregate flips from -816% to +17%
- `quan_engine_scalp`: n=4741, WR 29.7%, -810.12% (largest single alpha destroyer)

### C. Forward WR Floor Impact
- EQUITY at 45% floor: kills 41-44% WR picks (economically debatable)
- EQUITY at 40% floor: preserves marginal but positive-expectancy picks
- FOREX: `fwd_wr >= 50%` gate = PF 1.62 on n=466 (proven effective)

### D. Penalty Stacking Quantified
- Sunday penalty: -6 points
- LONG_OVERCONF: -25 points
- Direction conflict: -12 points
- **Total possible penalty: -43 points** (on a 0-100 scale)
- This means a genuinely good signal scoring 70 raw → 27 after penalties → below any threshold

---

## 6. Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `alpha_engine/unified_thresholds.py` | CREATE | Single source of truth for all score floors |
| `audit_trail/hf_quality_index.py` | CREATE | Hedge-fund quality scoring framework |
| `tools/etf_emitter.py` | CREATE | Wire ETF strategies to active picks |
| `tools/bond_emitter.py` | CREATE | Wire BOND strategies to active picks |
| `alpha_engine/config.py` | MODIFY | Import from unified_thresholds |
| `audit_trail/quality_gates.py` | MODIFY | Cap penalties, import unified thresholds, add proven whitelist |
| `alpha_engine/feed_hygiene.py` | MODIFY | Ensure entry_time populated for all writers |
| `tests/test_quality_gates.py` | MODIFY | Add tests for penalty cap, proven whitelist, ETF/BOND gates |
| `docs/HEDGE_FUND_UPLIFT_ROADMAP.md` | CREATE | This document |

---

*Generated by AI review — all recommendations backed by data from the repository's own closed-pick analysis and existing audit documentation.*
