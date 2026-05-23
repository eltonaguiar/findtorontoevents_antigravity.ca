# Per-Asset-Class Prediction Optimization Review

**Date:** 2026-05-14
**Source:** Audit of `findtorontoevents.ca/audit`, live `dashboard_data.json`
**Scope:** Score pipeline, consensus mechanisms, boosting infrastructure, regime protection — all asset classes

---

## Current State by Asset Class

| Class | PF | Status | Share | Boosters | Regime Protection | ML Model |
|-------|-----|--------|-------|----------|-------------------|----------|
| CRYPTO | 1.34 | stable | 93% | MTF+8, Ensemble+5, Liquidity, SHORT+3 | Yes (F&G, ADX, BTC dom) | ml_crypto_predictor |
| EQUITY | 1.55 | stable | <3% | None | No | No |
| COMMODITY | 4.03 | stable | <2% | None | No | No |
| FOREX | 0.81 | stressed | <2% | Penalties only | No | No |
| ETF | 1.41 | stable | <1% | None | No | No |
| BOND | 0.66 | thin_sample | <1% | None | No | No |
| FUTURES | None | insufficient | <1% | None | No | No |

---

## Top 10 Optimization Opportunities (ranked by impact × feasibility)

### P1 — Wire Per-Asset-Class IC Analysis Into Pipeline Feedback Loop

**Problem:** `tools/analyze_audit_scores_vs_pnl.py` already computes Spearman and Pearson correlations per asset class, per source system, and per quintile. The last analysis found crypto IC=0.11, non-crypto IC=0.33, but **none of these results feed back** to dynamically adjust boost/penalty weights in `score_booster.py` or `quality_gates.py`. Weights are hard-coded and manually adjusted based on human review of analytical reports.

**What to change:**
1. Add a `dynamic_weights.json` file written by `analyze_audit_scores_vs_pnl.py` containing per-asset-class ICs and quintile lift metrics
2. Have `score_booster.py` read this file on each run and apply proportional boosts: asset classes with higher IC get higher-confidence score projections, classes with flat IC get dampened
3. Auto-tune `ASSET_CLASS_SMART_THRESHOLDS` (quality_gates.py:370-378) based on actual per-class performance distributions

**Expected impact:** Adaptive scoring that self-tunes. Non-crypto IC advantage would be automatically exploited instead of manually patched every few weeks.

**Files:** `tools/analyze_audit_scores_vs_pnl.py`, `alpha_engine/score_booster.py`, `audit_trail/quality_gates.py`

---

### P2 — Build Non-Crypto Equivalents to Crypto's Signal Confirmation Gates

**Problem:** Crypto picks receive up to **+13 score bonus** from MTF multi-timeframe alignment (+8, score_booster.py:1015-1057) and Ensemble 2-of-3 signal confirmation (+5, score_booster.py:1059-1119). Non-crypto picks get **zero** signal confirmation boosting. This is the single biggest structural gap in per-asset prediction quality — non-crypto picks are simply scored less accurately because they lack independent signal verification.

**What to change:**
1. **For EQUITY/ETF:** Build a volume-profile + VWAP confirmation gate. Check if the pick's direction aligns with:
   - Volume-weighted average price (VWAP) position
   - On-balance volume (OBV) trend
   - SPY sector relative strength
   - Award +5/+8 score for 2+/3+ signals aligned
2. **For FOREX:** Build a session-liquidity + DXY correlation gate. Check:
   - DXY directional alignment for USD pairs
   - Session volume presence (London/NY overlap)
   - ATR expansion vs compression
3. **For COMMODITY:** Build a macro-correlation gate. Check:
   - DXY inverse correlation (gold, oil)
   - COT report positioning alignment
   - Inflation expectation trend (breakevens)

**Expected impact:** Non-crypto picks would get the same multi-signal verification that crypto enjoys. This is proven to add edge (MTF-aligned crypto picks have measurably higher WR).

**Files:** New module or extend `alpha_engine/score_booster.py`, `alpha_engine/ensemble_gate.py`

---

### P3 — Add Regime Protection for Non-Crypto Asset Classes

**Problem:** `cross_aggregation/regime_router.py:471-473` checks `is_crypto = sym.endswith("USDT")` and passes ALL non-crypto picks through unfiltered. This means:
- FOREX SHORTs fire during DXY panics with no protection
- EQUITY LONGs fire during VIX spikes with no gating
- COMMODITY picks ignore macro inventory/seasonal regimes

**What to change:**
1. **FOREX regime gate:** Track DXY trend + volatility. Block FOREX BUYs when DXY is crashing (>1% daily down), block SHORTs when DXY is surging. Add ADX-based chop detection (ADX<15 = only mean-reversion, no trend-following).
2. **EQUITY/ETF regime gate:** Track VIX levels. VIX>30 = -20 confidence on LONGs, +10 on SHORTs. VIX<15 = +10 on LONGs. Add SPY 200-SMA position gate (below 200SMA = no LONGs).
3. **COMMODITY regime gate:** Track DXY inverse, COT net positioning, backwardation/contango. Block COMMODITY BUYs when DXY surging +2%. Boost during backwardation.

**Expected impact:** FOREX PF 0.81 would improve by filtering out regime-contradictory picks. EQUITY picks would stop firing into VIX spikes.

**Files:** `cross_aggregation/regime_router.py`, `alpha_engine/scanner.py` (non-crypto quality gate section, lines 2440-2506)

---

### P4 — Normalize Scores Per Asset Class

**Problem:** The "score" field is computed identically for ALL asset classes using the same formula in `_apply_score_penalties()` (quality_gates.py:2653-3452). A score of 60 means completely different edge quality in CRYPTO (crowded, 93% of trades) vs COMMODITY (sparse, highest PF). The per-class elite score floors (`config.py:234-242`) are admissions floors, not normalizers — they just reject low scores, they don't make scores comparable across classes.

**Specific data:**
- CRYPTO elite floor: 70, PF=1.34
- COMMODITY elite floor: 65, PF=4.03 (highest PF but nearly same floor!)
- FOREX elite floor: 70, PF=0.81 (highest floor for worst class — correct for admission but misleading for comparison)

**What to change:**
1. Add `_normalize_score_by_class()` to score_booster.py that applies within-class z-score normalization using the per-class closed-pick distribution
2. Store per-class score distributions in `dynamic_weights.json` (mean, stdev, quintile breaks) updated on each run
3. Display both raw and normalized scores in dashboard, with normalized as the sort key
4. Update `MIN_ELITE_SCORE_BY_CLASS` dynamically based on rolling class performance

**Expected impact:** Picks across asset classes become comparable. COMMODITY picks with raw score 55 (rejected by 65 floor) would show normalized score 80+ relative to their class, making their edge visible.

**Files:** `alpha_engine/score_booster.py`, `audit_trail/quality_gates.py`, `alpha_engine/config.py`

---

### P5 — Build Per-Asset-Class Ranking Models

**Problem:** Only CRYPTO has a dedicated ML model (`ml_crypto_predictor`). All other asset classes use the same pool-wide score formula that was calibrated on crypto data. Non-crypto IC=0.33 suggests there IS predictable edge in non-crypto picks, but the model doesn't specialize for it.

**What to change:**
1. Train lightweight per-class logistic regression or gradient-boosted models using historical closed picks (strategy, symbol, WR, confidence, technical indicators, regime context → pnl_pct outcome)
2. Add `ml_equity_score`, `ml_forex_score`, `ml_commodity_score`, `ml_etf_score` fields
3. Blend class-specific ML score with the existing pool-wide score (weighted by per-class IC confidence)
4. **Commodity first** (PF=4.03, clearest signal) then equity (PF=1.55, moderate signal), then forex (needs regime feature engineering first)

**Expected impact:** Per-class ML would compound the already-observed IC=0.33 for non-crypto by using class-specific features (e.g., VIX for equity, DXY for forex, COT for commodity).

**Files:** New `ml_consensus/per_class_ranker.py`, `alpha_engine/score_booster.py`

---

### P6 — Fix Liquidity Penalty for Non-Crypto Symbols

**Problem:** `score_booster.py:989-1013` penalizes symbols NOT in `TOP50_SYMBOLS` (a Binance crypto-only list) with -5 score. ALL non-crypto symbols get this automatic -5 penalty because they aren't USDT pairs. This is a systemic under-scoring of non-crypto.

```python
# score_booster.py line 1002-1003
if sym not in TOP50_SYMBOLS:
    pick["score"] = max(0, old_score - 5)  # All non-crypto gets -5
```

**What to change:**
1. Add per-class liquidity/volume rankings: S&P 500 top 100 by volume for EQUITY, major forex pairs for FOREX, top 10 by open interest for COMMODITY/FUTURES, top 20 by AUM for ETF
2. Gate the -5 penalty per asset class: crypto-only for Binance volume, equity gets different volume thresholds, forex only penalizes exotics
3. Or simply bypass the liquidity penalty for non-crypto classes where Binance volume is irrelevant

**Expected impact:** +5 score boost for ALL non-crypto picks, correcting systemic bias.

**Files:** `alpha_engine/score_booster.py:989-1013`

---

### P7 — Differentiate Consensus Voting Thresholds by Asset Class

**Problem:** Non-crypto consensus (`copy_trader_intel/non_crypto_consensus.py:29-33`) requires >=2 agreeing strategies — same as crypto. But crypto has 20+ strategies voting while forex has ~3, commodity has ~5. A forex pick needs 67% of all forex strategies to agree (2/3) while crypto only needs 10% (2/20).

**What to change:**
1. Set `MIN_AGREEING_STRATEGIES` per asset class:
   - CRYPTO: 3 (higher due to more noise)
   - EQUITY: 2 (same, adequate for 8-10 strategies)
   - FOREX: 1 (only 3-4 strategies exist, any signal is rare)
   - COMMODITY: 2 (5-6 strategies, same proportion as equity)
   - ETF/BOND: 1 (fewest strategies, any agreement is meaningful)
2. Weight consensus score by total available strategies: `consensus_ratio = n_agreeing / n_available_strategies`

**Expected impact:** More forex/commodity/ETF picks promoted through consensus, better signal extraction from sparse strategy ecosystems.

**Files:** `copy_trader_intel/non_crypto_consensus.py:29-33`, `alpha_engine/contrarian_consensus.py:252-340`

---

### P8 — Add Signal Boosters for COMMODITY (PF=4.03)

**Problem:** COMMODITY has PF=4.03 — the highest of any asset class — but has **zero** dedicated boosting infrastructure. It gets the same penalty-only non-crypto treatment as FOREX (PF=0.81). This is the most mispriced asset class in the system.

**What to change:**
1. Add COMMODITY-specific booster in `score_booster.py`:
   - **DXY correlation check:** +8 when commodity direction aligns with DXY inverse (gold, silver, oil are DXY-inverse)
   - **COT positioning alignment:** +6 when COT net long/short aligns with pick direction
   - **Roll yield bonus:** +4 for backwardation in LONGs, +4 for contango in SHORTs
2. Lower COMMODITY elite score floor from 65 to 55 to admit more picks (high PF justifies lower admission threshold)
3. Increase COMMODITY capital allocation in config from 1.5x to 2.5x

**Expected impact:** More commodity picks promoted, higher capital allocation, better exploitation of the existing 4.03 PF edge.

**Files:** `alpha_engine/score_booster.py`, `alpha_engine/config.py:234-242`, `alpha_engine/config.py:159`

---

### P9 — Fix FOREX Negative-Expectancy Systemic Issues

**Problem:** FOREX PF=0.81, stressed status. Current mitigations are purely defensive:
- Elite score floor raised to 70 (config.py:239)
- "Non-crypto catastrophe" penalty -15 for WR<30% (score_booster.py:791)
- Widened SL to 0.8% (config.py:177-184)

These are all **penalties that reduce volume** but don't **improve selection quality**.

**What to change:**
1. Add DXY regime awareness to forex signal generation (see P3)
2. Add session-liquidity filter: only trade forex picks during London/NY overlap (8am-12pm EST)
3. Add carry-trade alignment bonus: +5 when interest rate differential supports direction
4. Add forward-validation escalation: forex strategies need 50+ fwd trades before promotion (currently 20 for all non-crypto)
5. Symbol blacklist: block JPY-cross BUYs (chronic losers per prior analysis)

**Expected impact:** PF should improve from 0.81 toward 1.0+ by filtering out regime-contradictory and low-liquidity picks rather than just penalizing everything.

**Files:** `alpha_engine/scanner.py:2440-2506`, `cross_aggregation/regime_router.py`, `audit_trail/quality_gates.py:1190-1211`

---

### P10 — Consolidate Three Parallel Asset Classification Systems

**Problem:** Three different asset classification functions exist with different priorities and symbol sets:
1. `_derive_asset_class()` — dashboard_generator.py:3288-3487 (canonical, used by main pipeline)
2. `detect_asset_class()` — config.py:773-820 (used by polymarket/kalshi/non-crypto consensus)
3. `AssetClassifier.classify()` — asset_classification.py:263-366 (newer, partially adopted)

Classification mismatches cause picks to shift categories mid-pipeline, leading to incorrect performance bucketing and gate application.

**What to change:**
1. Make `AssetClassifier.classify()` the single source of truth
2. Route all callers through it: replace `_derive_asset_class()` and `detect_asset_class()` with wrappers
3. Unify the symbol universes: merge the 3 different EQUITY_SYMBOLS sets, FOREX_PREFIXES, and COMMODITY detection rules
4. Add classification audit logging: when a pick's `asset_class` changes mid-pipeline, log a warning

**Expected impact:** Consistent classification means performance stats per class are accurate. Currently some EQUITY/ETF misclassifications cause false performance signals.

**Files:** `audit_trail/dashboard_generator.py`, `alpha_engine/config.py`, `audit_trail/asset_classification.py`

---

## Quick Wins (Low Effort, Immediate Impact)

| # | Change | File | Line(s) | Impact |
|---|--------|------|---------|--------|
| Q1 | Bypass crypto liquidity penalty for non-crypto | score_booster.py | 1000-1003 | +5 score for all non-crypto |
| Q2 | Lower COMMODITY elite floor 65→55 | config.py | 240 | +10% commodity picks admitted |
| Q3 | Add non-crypto to SHORT edge bonus (currently crypto only) | score_booster.py | 1128-1143 | +3 score for non-crypto SHORTs |
| Q4 | Fix trust-tier model bypass log (non-crypto gets no trust gate but logs are silent) | quality_gates.py | 890-892 | Better observability |
| Q5 | Add FOREX JPY-cross BUY blocklist | quality_gates.py | 3122-3129 | Block chronic losers |
| Q6 | Lower forex consensus threshold 2→1 | non_crypto_consensus.py | 134 | More forex signals promoted |

---

## Implementation Priority

**Immediate (this week, ~4h):**
- Q1-Q6 quick wins (all under 15 minutes each)
- P6: Fix liquidity penalty (30 min)

**Short-term (next 2 weeks, ~20h):**
- P4: Score normalization per class (4h)
- P7: Per-class consensus thresholds (2h)
- P8: COMMODITY boosters (4h)
- P10: Classification consolidation (6h)
- P3: Regime protection for non-crypto (4h)

**Medium-term (next month, ~40h):**
- P2: Non-crypto signal confirmation gates (12h)
- P1: Wire IC feedback loop (8h)
- P9: FOREX systemic fix (12h)
- P5: Per-class ranking models (8h)

---

## Verification

After each phase:
1. Run `python tools/analyze_audit_scores_vs_pnl.py` to measure per-class IC changes
2. Check `dashboard_data.json` per-asset health for status improvements
3. Monitor smart_picks feed length per asset class (should increase for under-represented classes)
4. Verify no regression in CRYPTO metrics (primary volume, must not degrade)

---

## Files Touched by This Review

| File | Issue |
|------|-------|
| `alpha_engine/score_booster.py` | Liquidity penalty (P6), SHORT bonus (Q3), COMMODITY boosters (P8), MTF/Ensemble crypto-only (P2) |
| `alpha_engine/config.py` | Elite score floors (P4, Q2), per-class risk params |
| `cross_aggregation/regime_router.py` | Non-crypto regime bypass (P3) |
| `audit_trail/quality_gates.py` | Score normalization (P4), trust-tier bypass (Q4), FOREX gates (P9) |
| `copy_trader_intel/non_crypto_consensus.py` | Consensus thresholds (P7) |
| `audit_trail/dashboard_generator.py` | Classification fragmentation (P10) |
| `tools/analyze_audit_scores_vs_pnl.py` | IC feedback loop (P1) |
| `alpha_engine/scanner.py` | Non-crypto quality gate (P9), per-class confidence floors |
| `alpha_engine/antigravity_strategies.py` | Duplicated crypto symbol checks |
