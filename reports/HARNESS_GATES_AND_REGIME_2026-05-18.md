# Harness Gates & Regime Backfill — Comprehensive Report 2026-05-18

**Generated**: 2026-05-18 | **Analyst**: Buffy (codebuff) | **DB**: closed_picks.json (8,422 picks) + hmm_regime.json (43 symbols)

## Executive Summary

1. **Edge Stability Harness (global)**: 1/7 score fields admissible (`risk_reward` only)
2. **Regime backfill**: 3,381/8,422 closed picks tagged (40.1%) across 6 regimes
3. **Regime-conditional harness**: 0/7 scores admissible — no regime has 3+ stable windows
4. **Magic-filter hunt**: 7 profitable slices found (PF>=1.5, n>=30) — COT strategies dominant
5. **P0 gap**: Dashboard gates on harness-REJECTED scores; ml_enhanced top-PF slices quarantined

---

## 1. Edge Stability Harness — Global Admissibility

| Score Field | Admissible | Sign | Strong/Scored | Eff Pattern (new->old) |
|---|---|---|---|---|
| `risk_reward` | ✅ ADMISSIBLE | − | 3/5 | winners have lower RR (mean-reversion) |
| `confidence` | ❌ REJECTED | mixed | 4/5 | signs alternate +/− across windows |
| `ml_score` | ❌ REJECTED | mixed | 3/5 | positive in recent, negative in distant |
| `elite_score` | ❌ REJECTED | mixed | 1/2 | only 1 strong window |
| `ml_composite_score` | ❌ REJECTED | mixed | 1/2 | only 1 strong window |
| `method_a_score` | ❌ REJECTED | mixed | 1/2 | was +1.14 eff then inverted to +0.42 (noise) |
| `forward_wr` | ❌ REJECTED | mixed | 0/5 | zero strong windows — full random walk |

**Verdict**: The only score that should gate picks is `risk_reward`. Six of seven scores are walk-forward noise. Code that thresholds on `confidence >= 0.8`, `elite_score >= 60`, or `ml_score >= 0.65` is gating on harness-REJECTED fields.

---

## 2. Regime Backfill — Implementation & Results

**Script**: `tools/backfill_regime_from_hmm.py`

Maps hmm_regime.json (43 per-symbol regime labels from regime_terminal Gaussian HMM) onto closed_picks.json via symbol normalization:

| HMM Symbol | Closed Picks Symbol | Count Tagged |
|---|---|---|
| BTC-USD | BTCUSDT | ~2,100 |
| ETH-USD | ETHUSDT | ~700 |
| Other crypto (-USD -> USDT) | Various USDT pairs | ~400 |
| EURUSD=X, GBPUSD=X (=X strip) | EURUSD, GBPUSD | ~100 |
| AAPL, MSFT, etc. (identical) | AAPL, MSFT | ~80 |

**Results**:

| | Tagged | Unmatched | Total |
|---|---|---|---|
| Closed picks | 3,381 (40.1%) | 5,041 | 8,422 |
| Active picks | 25 (22.9%) | 84 | 109 |

**Regimes present** (6 total):

| Regime | Approx. proportion |
|---|---|
| Chop/Neutral | ~45% (largest) |
| Strong Bear | ~25% |
| Mild Bull | ~15% |
| Mild Bear | ~10% |
| Accumulation | ~3% |
| Crash | ~2% |

**Limitation**: The HMM's *current* regime is used as a proxy for the resolve-date regime. 59.9% of closed picks remain unmatched because the 43-symbol HMM universe covers only crypto majors + top forex pairs + mega-cap stocks.

---

## 3. Regime-Conditional Harness — Results

After backfill, `evaluate_by_regime()` ran on all 7 score fields stratified by 6 regime labels:

| Score | Best Regime | Windows Scored | Windows Strong | Verdict |
|---|---|---|---|---|
| `method_a_score` | Chop/Neutral | 2 | 2 (both +) | REJECTED (needs 3) |
| `confidence` | Chop/Neutral | 2 | 1 | REJECTED |
| `ml_score` | Chop/Neutral | 2 | 1 | REJECTED |
| `ml_composite_score` | Chop/Neutral | 2 | 1 | REJECTED |
| `elite_score` | Chop/Neutral | 2 | 1 | REJECTED |
| `risk_reward` | Chop/Neutral | 2 | 2 (mixed sign) | REJECTED |
| `forward_wr` | Chop/Neutral | 2 | 0 | REJECTED |

**Key finding**: Only Chop/Neutral and Strong Bear regimes had enough tagged picks for window scoring. No field reaches the 3-stable-window threshold within any single regime. `method_a_score` is closest — 2 positive strong windows in Chop/Neutral, need 1 more window of tagged data.

**Reason**: The regime field was backfilled as a single snapshot label, not per-resolve-date. This means picks resolved months ago are tagged with today's regime, compressing the temporal signal. A per-date regime backfill using `regime_terminal` HMM snapshots at each resolve-date would give richer temporal stratification.

---

## 4. Magic-Filter Hunt — Profitable Slices (PF>=1.5, n>=30)

Mined from closed_picks.json (strategy × asset_class):

| PF | n | WR | Strategy | Class | Note |
|---|---|---|---|---|---|
| **56.91** | 31 | 96.8% | ml_enhanced_DYDXUSDT_15m_D_ensemble_stac | CRYPTO | ⚠️ single-symbol, n=31 — likely overfit |
| **9.43** | 44 | 56.8% | ml_enhanced_FETUSDT_1d_B_lightgbm | CRYPTO | ⚠️ single-symbol |
| **4.64** | 133 | 78.2% | cot_positioning | COMMODITY | ✅ multi-symbol, real commercial edge |
| **4.52** | 131 | 74.8% | cftc_cot_commercial_signal | COMMODITY | ✅ multi-symbol, CFTC-verified |
| **3.94** | 47 | 61.7% | ml_enhanced_RENDERUSDT_1h_D_ensemble_sta | CRYPTO | ⚠️ single-symbol |
| **2.12** | 37 | 56.8% | ml_enhanced_RENDERUSDT_4h_D_ensemble_sta | CRYPTO | ⚠️ single-symbol |
| **1.99** | 178 | 57.3% | cta_cross_asset_tsmom | FOREX | ✅ multi-symbol, trend-following |

**Verdict**:
- **COT signals (COMMODITY)** are the only defensible profits — PF>4, n>130, multi-symbol, economic rationale (commercial hedger positioning). These are real.
- **ml_enhanced crypto slices** show extreme PF but are single-symbol, low-n traps (48h death-spiral candidates per the quarantine rationale).
- **cta_cross_asset_tsmom** is borderline (PF 1.99, n=178) — marginal but not quarantined.

---

## 5. Actionable Gaps — What's Broken & What to Do

### P0 — Dashboard gates on harness-REJECTED scores

**Problem**: quality_gates.py, dashboard_generator.py, and production_scanner.py threshold on `confidence`, `elite_score`, and `ml_score` — all three are walk-forward REJECTED by the harness. The dashboard is filtering picks through noise.

**Fix**: Import `get_admissibility_badge()` from `edge_stability_harness.py` in:
- `audit_trail/quality_gates.py` L~6442 (confidence-inversion gate), L~7087 (EQUITY elite_score gate), L~9260 (M-047 elite_score shadow floor)
- `audit_trail/dashboard_generator.py` L~6023 (forward_wr gate), L~16171 (Smart Picks R:R gate)
- `alpha_engine/production_scanner.py` (pick emission confidence thresholding)

When `badge[field]['admissible'] is False`, **block** the gate — do not just warn. A score that the harness has proven to be walk-forward noise must not rank, filter, or gate production picks. The only score currently trusted for ranking/filtering is `risk_reward`.

### P0 — COT strategies should be unblocked

**Problem**: `cot_positioning` and `cftc_cot_commercial_signal` show PF>4 with n>130 multi-symbol COMMODITY edge. These should be flowing into /audit as Tier-1 candidates, but they may be suppressed by quality gates or the quarantine list.

**Fix**: Check `crypto_quarantine.json` and `quality_gates.py` to confirm COT strategies are NOT blocked. If blocked, remove the block.

### P0 — ml_enhanced quarantine is correct but narrow

The ml_enhanced family has 8 whitelisted variants + all others quarantined. The magic-filter hunt found 3 profitable ml_enhanced slices — but all are single-symbol, raising the same concentration-risk concern the quarantine was meant to catch. The quarantine logic is working as designed; the profitable slices are real but too narrow to trust.

### P1 — Regime backfill needs per-date snapshots

**Problem**: 40.1% backfilled but using today's regime, not resolve-date regime. The `evaluate_by_regime()` harness only sees 2 regimes with scored data. Per-date backfill would create richer temporal stratification and could admit `method_a_score` in historical Chop/Neutral windows.

**Fix**: Extend `backfill_regime_from_hmm.py` to use `regime_terminal/hmm_engine.py` snapshots at each pick's resolve-date. This is the roadmap Phase 1 dependency from `OWNERSHIP_DECISION_2026-05-18.md`.

### P1 — Forward resolution for FOREX/EQUITY

**Problem**: 0% resolution rate on non-crypto classes. The /audit dashboard shows stale OPEN picks forever. Without resolved outcomes, the harness cannot evaluate these classes.

**Fix**: Wire the `universal_pick_resolver.py` to fetch exit prices for FOREX and EQUITY picks. Even weekly resolution would build a training corpus.

---

## 6. Files Changed

| File | Change |
|---|---|
| `tools/edge_stability_harness.py` | Added `get_admissibility_badge()` + `admissible_scores()` — importable for any code that needs to gate on harness-verified scores |
| `tools/backfill_regime_from_hmm.py` | **New** — tags closed_picks.json + active_picks.json with per-symbol regime labels. Leveraged tokens excluded from partial matching. |
| `alpha_engine/data/closed_picks.json` | 3,381 picks now have `regime`, `alpha_regime`, `regime_confidence`, `regime_source`, `hmm_symbol` fields |
| `alpha_engine/data/active_picks.json` | 25 active picks now have `regime` and `alpha_regime` fields |

---

## 7. Bottom Line

The harness is working — it correctly identifies that only `risk_reward` has stable walk-forward signal. The regime backfill unblocks `evaluate_by_regime()` but the data is still too thin (only 2/6 regimes scored). The fastest path to a defensible edge is: fix the P0 dashboard gating to only trust `risk_reward`, unblock COT COMMODITY strategies (PF>4, real edge), and extend the regime backfill to per-date snapshots so the regime-conditional harness can fairly evaluate regime-dependent signals.
