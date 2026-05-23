# PR-3: Promote M-069 Slippage Model to Hard Gate (Post-Cost Expectancy)

| Field | Value |
|---|---|
| **Branch** | `feat/post-cost-expectancy-gate-2026-0518` |
| **Target** | `main` |
| **Class** | ALL (global gate) |
| **M-Code** | M-069 (`charter_slippage.deduct_slippage`) |
| **Status** | Global advisory → hard gate |
| **Author** | `quant-dev-3` |
| **Reviewers** | `risk-lead`, `execution-desk`, `strat-lead` |

---

## 1. Problem Statement

### 1.1 M-069 Is Advisory Only
The M-069 slippage model, implemented in `charter_slippage.py` via `deduct_slippage()`, currently computes **post-cost expectancy** for every pick but only logs it as a warning:

```python
# charter_slippage.py ~L284 (current)
post_cost_expectancy = gross_expectancy - total_slippage - commission - market_impact
if post_cost_expectancy <= 0:
    logger.warning(f"Pick {pick.id} has non-positive post-cost expectancy: {post_cost_expectancy}")
    # ADVISORY ONLY — pick still proceeds to execution
```

This means picks with **zero or negative true expectancy after all trading costs** are still being sent to the execution desk and counted in `pf_registry.json`. The system is trading at a known loss on a material subset of picks.

### 1.2 Impact by Class (from `pf_registry.json`, 2026-05-18T00:27:46Z)

| Class | Gross PF | Est. Post-Cost PF | Picks with Expectancy <= 0 | Annual Waste |
|---|---|---|---|---|
| CRYPTO | 1.28 | ~0.95 | ~22% | $340K |
| COMMODITY | 1.17 | ~0.88 | ~31% | $180K |
| ETF | ~1.2 | ~0.85 | ~28% | $95K |
| FOREX | 0.33 | ~0.22 | ~55% | $420K |
| BOND | 0.0 | -0.05 | ~40% | $25K |
| FUTURES | 0.96 | ~0.71 | ~35% | $110K |

**Aggregate:** ~$1.17M/year in post-cost negative-expectancy trades are currently flowing through the system.

### 1.3 Why This Was Advisory
The slippage model was kept advisory for 18 months because:
1. The slippage estimates were unvalidated (paper vs. live variance was > 40%).
2. Risk desk feared over-filtering during high-volatility opportunities.
3. No threshold calibration framework existed.

As of 2026-05, the M-069 model has been validated against 14 months of live execution data with < 8% variance. The model is now accurate enough to promote to a hard gate.

---

## 2. Solution

### 2.1 Promote to Hard Gate
1. **In `charter_slippage.py`:**
   - Change `deduct_slippage()` return type from `(float, WarningLevel)` to `GateResult`.
   - If `post_cost_expectancy <= 0.0`:
     - Return `GateResult.REJECT` with `filter_reason = "POST_COST_EXPECTANCY_REJECT"`.
     - Attach diagnostic dict: `{"gross_expectancy": ..., "slippage": ..., "commission": ..., "market_impact": ..., "post_cost": ...}`.
   - If `post_cost_expectancy > 0.0 but < 0.01 * notional`:
     - Return `GateResult.REJECT` with `filter_reason = "POST_COST_EXPECTANCY_TOO_LOW"` (minimum economic threshold).

2. **In `quality_gates.py`:**
   - Add `passes_post_cost_expectancy(pick)` to the **global** gate chain (runs after `passes_active_gate`, before `passes_ml_quarantine`).
   - Import `charter_slippage.deduct_slippage` and wrap it as a gate.
   - Add metric: `post_cost_expectancy_reject_total{class, reason}`.
   - Update `passes_all_gates()` to include the new gate in sequence.

3. **In `pick_lifecycle_log.py`:**
   - Ensure the diagnostic dict from slippage is serialized into `filter_metadata` when a pick is rejected.
   - Add `post_cost_expectancy` as a top-level column (float, nullable) for all picks.

### 2.2 Graduated Rollout (Config-Based)
- Add `post_cost_gate_mode` enum in `config/trading.yaml`: `["advisory", "shadow", "hard_reject"]`.
- Default to `"shadow"` for 2 weeks: gate runs but only logs rejections, does not block.
- After shadow period, switch to `"hard_reject"`.
- This allows the execution desk to validate rejection rates before going live.

### 2.3 Threshold Calibration
- Add `min_post_cost_expectancy_bps` in `config/asset_class_limits.yaml` per class.
- Defaults: 0 bps (i.e., > 0) for all classes except FOREX (5 bps, due to wider spreads).

---

## 3. Files Changed

| File | Lines | Change |
|---|---|---|
| `charter_slippage.py` | +89 / -34 | Refactor `deduct_slippage()` to return `GateResult`; add `POST_COST_EXPECTANCY_REJECT` / `TOO_LOW` reasons |
| `quality_gates.py` | +67 / -14 | Add `passes_post_cost_expectancy()` to global gate chain; metrics; shadow mode support |
| `pick_lifecycle_log.py` | +23 / -4 | Add `post_cost_expectancy` column; serialize slippage diagnostics in `filter_metadata` |
| `config/trading.yaml` | +12 / -2 | Add `post_cost_gate_mode: shadow` (initial rollout) |
| `config/asset_class_limits.yaml` | +14 / -2 | Add `min_post_cost_expectancy_bps` per class |
| `pick_evaluator.py` | +18 / -6 | Wire new gate into evaluation flow; respect `post_cost_gate_mode` config |
| `pf_registry.json` | +6 / -1 | Update global gate list annotation |
| `tests/unit/test_post_cost_gate.py` | +245 | New test suite: expectancy calc, reject logic, shadow mode, threshold config |
| `tests/integration/test_slippage_e2e.py` | +112 | Shadow mode e2e; verify rejections match live slippage logs |
| `alembic/versions/027_add_post_cost_column.py` | +29 | DB migration: add `post_cost_expectancy` to `pick_lifecycle_log` |

---

## 4. Test Plan

### 4.1 Unit Tests (`tests/unit/test_post_cost_gate.py`)

| Test Case | Input | Expected |
|---|---|---|
| `test_reject_when_expectancy_zero` | `gross=0.5`, `slippage+commission+impact=0.5` | `REJECT`, reason `POST_COST_EXPECTANCY_REJECT` |
| `test_reject_when_expectancy_negative` | `gross=0.3`, `costs=0.5` | `REJECT` |
| `test_pass_when_expectancy_positive` | `gross=1.0`, `costs=0.3` | `PASS` |
| `test_reject_when_expectancy_too_low` | `gross=0.1005`, `costs=0.10`, `notional=10000` | `REJECT`, reason `POST_COST_EXPECTANCY_TOO_LOW` (< 1 bps) |
| `test_shadow_mode_logs_but_does_not_reject` | `post_cost_gate_mode="shadow"`, negative expectancy | Logs `SHADOW_REJECT`; pick proceeds |
| `test_advisory_mode_no_effect` | `post_cost_gate_mode="advisory"` | Same as old behavior (warning only) |
| `test_forex_threshold_5bps` | FOREX pick, post-cost = 4 bps | `REJECT` (below 5 bps floor) |
| `test_crypto_threshold_0bps` | CRYPTO pick, post-cost = 0.5 bps | `PASS` (0 bps floor) |
| `test_diagnostic_dict_attached` | Rejected pick | `filter_metadata` contains full slippage breakdown |

### 4.2 Integration Tests (`tests/integration/test_slippage_e2e.py`)
- Replay 500 historical picks with live slippage data.
- In shadow mode: compare gate rejections against actual P&L of those picks.
- Assert > 85% of shadow-rejected picks would have been losers (validating model accuracy).
- After switching to hard_reject: assert those picks are blocked.

### 4.3 Manual / QA
- [ ] Set `post_cost_gate_mode="shadow"` in paper-trading environment for 5 trading days.
- [ ] Compare `post_cost_expectancy_reject_total` metric against actual execution P&L.
- [ ] Confirm shadow-rejected picks have live PF < 0.5.
- [ ] Switch to `hard_reject`; verify pick count drops by expected ~22-55% per class.

---

## 5. Acceptance Criteria

- [ ] `deduct_slippage()` returns `GateResult.REJECT` when `post_cost_expectancy <= 0`.
- [ ] `passes_post_cost_expectancy()` is in the global gate chain for all asset classes.
- [ ] Shadow mode is available and functional: logs rejections without blocking.
- [ ] `post_cost_expectancy` column is populated for 100% of picks in `pick_lifecycle_log`.
- [ ] Rejected picks include full slippage diagnostic in `filter_metadata`.
- [ ] `POST_COST_EXPECTANCY_REJECT` appears as a top-3 filter reason in `pf_registry.json` for all classes.
- [ ] All 245 new unit tests pass.
- [ ] Integration test validates > 85% shadow-rejected picks would have been losers.
- [ ] Rollback to `advisory` mode is a one-line config change.
- [ ] No picks with negative post-cost expectancy reach the execution desk in `hard_reject` mode.

---

## 6. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Slippage model underestimates costs in volatile regimes, letting bad picks through | Medium | High | Shadow mode validates for 2 weeks before hard reject; model has 14-month live validation. |
| Over-filtering removes marginally positive picks that aggregate to meaningful P&L | Medium | Medium | `min_post_cost_expectancy_bps` is configurable per-class; can be set negative (allow small losers) if needed. |
| Execution desk objects to reduced flow volume | High | Low | Volume reduction is *correct* (removing negative expectancy trades); risk desk pre-briefed. |
| Migration adds nullable column that breaks downstream ETL | Low | High | Migration is additive only; `pick_lifecycle_log` is append-only; ETL reads columns by name. |

### Rollback
1. **Config rollback (instant):** Set `post_cost_gate_mode: "advisory"` in `config/trading.yaml`. Hot reload.
2. **Code rollback:** `git revert HEAD`. Restart pick evaluator.
3. **Estimated time:** 15 seconds (config) / 3 minutes (code).

---

## 7. Merge Order

```
PR-1 ──> PR-2 ──> PR-3 (this PR) ──> PR-4 ──> PR-5
              ^
              │
        PR-3 depends on PR-1 and PR-2
        for correct PF baselines
```

| Dependency | Reason |
|---|---|
| **PR-1 → PR-3** | PR-1 corrects COMMODITY's inflated PF (from 1.17 to ~1.05). PR-3's post-cost expectancy threshold for COMMODITY must use the true PF baseline to avoid miscalibrating slippage tolerance. |
| **PR-2 → PR-3** | PR-2 establishes ETF's true VIX-gated PF (~2.05). PR-3's slippage model uses ETF's gross expectancy as input; it must reflect the filtered regime, not the blended regime. |
| **PR-3 → PR-4** | PR-4's CRYPTO quarantine whitelist uses post-cost PF to determine which variants are truly profitable. PR-3 must be active to compute accurate post-cost PF for the whitelist. |
| **PR-3 → PR-5** | PR-5's what-if query must show correct `POST_COST_EXPECTANCY_REJECT` as a filter reason in historical data. |

**Merge this PR third, after PR-1 and PR-2 have stabilized.**
