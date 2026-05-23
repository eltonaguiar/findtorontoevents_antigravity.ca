# Antigravity Enhancements — Remaining Gaps (Post-Copilot Audit)

## Status: Most Work Already Done ✅

GitHub Copilot + Kilo Code + Cursor have already implemented:
- ✅ `audit_trail/adaptive_stops.py` (250 lines, asset-class ATR multipliers)
- ✅ `audit_dashboard/ml_pick_scorer.py` (Empirical Bayes wired in, tested)
- ✅ `alpha_engine/strategies/earnings_drift.py` (PEAD strategy, registered in generator)
- ✅ `audit_trail/forward_test_gates.py` (270 lines, quality gates)
- ✅ `audit_trail/non_crypto_smart_score.py` (VIX regime + earnings gate)
- ✅ `.github/workflows/stocks-daily-stocksunify.yml` (cron with API keys)
- ✅ `audit_trail/hf_pick_validator.py` (hedge-fund quality validator)

## What's STILL Missing 🔴

### 1. Missing Data Backfill (CRITICAL — 08-missing-data-backfill/)

**The root problem:** 70-90% of active picks are missing critical fields.

| Field | Missing % | Impact |
|-------|-----------|--------|
| `elite_score` | 90% | Best IC predictor can't fire |
| `ml_score` | 87% | Kill zone gate useless |
| `risk_reward` | 73% | RR filter dead |
| `strategy` | 70% | Can't track by strategy |
| `conviction_tier` | ~100% | "High Conviction" button empty |

**The fix:** `missing_field_backfiller.py` computes proxy values from available fields so the quality gates and scoring can actually function.

**Installation:**
```bash
cp 08-missing-data-backfill/missing_field_backfiller.py audit_trail/
```

**Integration point:** Call `backfill_picks()` in `dashboard_generator.py` BEFORE quality gate evaluation.

### 2. HF Validator Recalibration Needed

Copilot built the HF validator but calibrated it wrong based on assumptions. Actual closed data reveals:

| Assumption | Reality | Fix |
|-----------|---------|-----|
| RR >= 2.0 needed | RR 1.0-1.5 = 56% WR; RR > 2.0 = 25% WR | Lower to RR >= 1.2 |
| Elite score matters | 90% missing, anti-predictive in 20-40 range | Drop from validator until backfilled |
| Confidence is noise | Confidence 0.8+ = **77% WR** (+13% avg PnL) | Make confidence 0.8+ the primary gate |

### 3. Conviction Tier Not Persisted

The "High Conviction" button checks `hf_conviction_tier` but it's computed in-memory by `dashboard_generator.py` and never saved to data files. Fix: persist tier assignments after classification.

### 4. quan_engine_scalp is a Capital Destroyer

21% WR, -17.7% avg PnL across 2,340 picks with `strategy=None`. The 10 "high PnL" outliers at low scores are cherry-picked from an extreme tail. **Needs hard block** or `-25 score penalty` as LEARNINGS already recommended.

## Installation

Copy the single remaining file into your repo:

```bash
cp 08-missing-data-backfill/missing_field_backfiller.py audit_trail/
```

Then in `audit_dashboard/dashboard_generator.py`, add before quality gate evaluation:

```python
from audit_trail.missing_field_backfiller import backfill_picks

# Before gates run:
active_picks, backfill_stats = backfill_picks(active_picks)
```

## Priority

| # | Action | Status | Effort |
|---|--------|--------|--------|
| 1 | Asset-class ATR stops | ✅ Done by Copilot | — |
| 2 | Empirical Bayes scorer | ✅ Done by Copilot | — |
| 3 | PEAD strategy | ✅ Done by Copilot | — |
| 4 | Stocks cron | ✅ Done by Copilot | — |
| 5 | Non-crypto Smart Score | ✅ Done by Copilot | — |
| 6 | Forward test gates | ✅ Done by Copilot | — |
| 7 | **Missing data backfill** | 🔴 **NEW — this file** | 2h |
| 8 | HF validator recalibration | ⚠️ Needs threshold fixes | 1h |
| 9 | Conviction tier persistence | ⚠️ Needs wiring | 1h |
| 10 | quan_engine_scalp block | ⚠️ Needs config change | 15min |
