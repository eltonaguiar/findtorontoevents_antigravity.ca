# PR #1: EQUITY Confidence Inversion Penalty

**Branch:** `fix/equity-confidence-inversion`  
**File:** `audit_trail/quality_gates.py`  
**Type:** Bug fix / calibration correction  
**Priority:** P0 — Edge Destroyer  
**Expected Impact:** WR lift from 54% → 57%+, pushing EQUITY from Tier 2 to Tier 1

---

## Problem

The confidence model for EQUITY is **systematically inverted**. Analysis of 252 closed EQUITY picks in `audit_dashboard/data/dashboard_data.json` (2026-05-16T03:55Z) shows:

| Confidence Bucket | n | Win Rate | Profit Factor | Total PnL% |
|-------------------|---|----------|---------------|------------|
| **LOW** | 84 | **70.2%** | **4.307** | **+290.41%** |
| MID | 84 | 53.6% | 1.334 | +45.60% |
| **HIGH** | 84 | **38.1%** | **1.041** | **+5.22%** |

**Every 10 points of confidence costs ~8 points of win rate.** The model is confidently wrong — it assigns high confidence to trades that are structurally more likely to lose.

### Root Cause Hypotheses
1. **Regime-dependent miscalibration:** The April bull regime broke the confidence→probability mapping
2. **Volatility conflation:** The model confuses expected move size (volatility) with probability of success

---

## Solution

Add a targeted score penalty in `_apply_score_penalties()` for EQUITY picks with confidence > 0.70:

```python
if _asset_class == "EQUITY" and os.environ.get("EQUITY_CONFIDENCE_INVERSION_PENALTY_DISABLED", "0") != "1":
    _eq_conf = _normalize_confidence(pick.get("confidence", 0))
    if _eq_conf > 0.70:
        score -= 15
        penalties.append(f"equity_overconfidence_penalty(conf={_eq_conf:.2f}):-15")
```

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Threshold: >0.70** | The inversion is sharpest above 0.70; MID bucket (0.40-0.70) performs normally |
| **Penalty: -15 points** | Large enough to push most high-confidence picks below SMART_PICKS_MIN_SCORE (60), but not so large that it destroys visibility entirely |
| **Env kill-switch** | `EQUITY_CONFIDENCE_INVERSION_PENALTY_DISABLED=1` allows instant rollback if the penalty causes unexpected side effects |
| **Placement in `_apply_score_penalties`** | Consistent with other asset-class-specific penalties (FOREX confidence guard, futures probation) |

---

## Verification Plan

1. **Shadow test (14 days):**
   - Monitor `picks.active` for EQUITY picks with `equity_overconfidence_penalty` tag
   - Track WR of penalized vs. non-penalized buckets
   - Expected: penalized bucket WR should rise as overconfident picks are filtered out

2. **Metrics to watch:**
   - EQUITY aggregate WR (target: >55% for Tier 1)
   - EQUITY aggregate PF (target: maintain >1.90)
   - Number of active EQUITY picks (should not drop >30%)
   - No increase in blocked-symbol leakage

3. **Rollback trigger:**
   - If EQUITY WR drops below 50% over 7 days → `EQUITY_CONFIDENCE_INVERSION_PENALTY_DISABLED=1`
   - If active EQUITY count drops below 20 → investigate, don't auto-rollback (quality > quantity)

---

## Related Files

- `updates/2026-05-16-EQUITY-validation.md` — Full EQUITY Phase 2.1–2.3 report
- `updates/2026-05-16-comprehensive-edge-analysis-and-recommendations.md` — Cross-asset analysis
- `audit_trail/quality_gates.py` — This PR's target file

---

## Sign-off

- [x] Data-driven (252-trade analysis)
- [x] Kill-switch included (`EQUITY_CONFIDENCE_INVERSION_PENALTY_DISABLED`)
- [x] Follows existing penalty pattern (FOREX confidence guard)
- [x] Shadow test plan defined
- [x] Documented in `updates/2026-05-16-PR-1-equity-confidence-inversion.md`
