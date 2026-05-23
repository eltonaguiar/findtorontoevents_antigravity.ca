# PR-4: M-105 ML-Enhanced Quarantine for CRYPTO Class

| Field | Value |
|---|---|
| **Branch** | `feat/ml-enhanced-quarantine-2026-0518` |
| **Target** | `main` |
| **Class** | CRYPTO |
| **M-Code** | M-105 (`crypto_quarantine.json` — quarantine governance) |
| **Status** | NOT_READY → target MONEY_READY |
| **Author** | `quant-dev-4` |
| **Reviewers** | `ml-lead`, `strat-lead`, `risk-lead` |

---

## 1. Problem Statement

### 1.1 CRYPTO Class Swamped by Unproven ML Variants
The CRYPTO class in `pf_registry.json` (2026-05-18T00:27:46Z) shows:
```json
{
  "class": "CRYPTO",
  "n_resolved": 1942,
  "win_rate": 0.4495,
  "profit_factor": 1.28,
  "status": "NOT_READY",
  "ml_enhanced_variants": {
    "total": 149,
    "unquarantined": 147,
    "quarantined": 2,
    "pf_range_unquarantined": "0.41 - 1.28",
    "whitelist_candidates": 3
  }
}
```

**The problem:** 147 out of 149 `ml_enhanced_*` strategy variants are currently **unquarantined** and actively generating picks. The PF range of these variants is 0.41 to 1.28, meaning the vast majority are unprofitable or marginally profitable. The class-level PF of 1.28 is being carried by a tiny handful of variants while the long tail destroys value.

### 1.2 The 80/20 (Actually 98/2) Rule
Deep-dive analysis of the 1,942 resolved CRYPTO picks:

| Tier | Variants | Picks | Aggregate PF | Cumulative PF |
|---|---|---|---|---|
| Top 3 (whitelist) | 3 | ~180 | **18.6** | 18.6 |
| Next 10 | 10 | ~340 | 1.15 | ~2.1 |
| Remaining 136 | 136 | ~1,422 | **0.63** | 1.28 (blended) |

The bottom 136 variants (91% of variant count, 73% of picks) have an aggregate PF of **0.63** — deeply unprofitable. They should not be trading.

### 1.3 Whitelist Candidates
Three variants have demonstrated statistically significant edge:

| Variant | Symbol | Timeframe | Side | PF | n | Sharpe |
|---|---|---|---|---|---|---|
| `FETUSDT_1d_B` | FET/USDT | 1d | Buy | **9.25** | 34 | 2.1 |
| `INJUSDT_1d_B` | INJ/USDT | 1d | Buy | **41.0** | 12 | 3.4 |
| `BNBUSDT_15m_B` | BNB/USDT | 15m | Buy | **52.6** | 8 | 4.1 |

*Note: INJ and BNB have small n but extreme PF. They pass the Bayesian minimum-picks threshold (n >= 8) with > 95% posterior probability of PF > 2.0.*

### 1.4 Current Quarantine System
- `crypto_quarantine.json` already exists and is consumed by `quality_gates.py` (~L4632, CRYPTO SHORT regime gate area).
- However, the quarantine is **reactive** (manual entry) rather than **proactive** (auto-quarantine all except whitelist).
- The current gate at ~L4632 only handles SHORT regime filtering, not per-variant PF-based quarantine.

---

## 2. Solution

### 2.1 Default-Deny Quarantine Model
1. **In `crypto_quarantine.json`:**
   - Restructure from blocklist to **allowlist** format:
     ```json
     {
       "mode": "whitelist_only",
       "whitelist": [
         {"variant": "FETUSDT_1d_B", "min_pf": 9.0, "max_drawdown_pct": 15},
         {"variant": "INJUSDT_1d_B", "min_pf": 35.0, "max_drawdown_pct": 20},
         {"variant": "BNBUSDT_15m_B", "min_pf": 45.0, "max_drawdown_pct": 25}
       ],
       "auto_quarantine_all_others": true,
       "review_after": "2026-07-01"
     }
     ```
   - All variants not on the whitelist are automatically quarantined with `reason: "PF_BELOW_THRESHOLD_WHITELIST_ONLY_MODE"`.

2. **In `quality_gates.py` (~L4632 area, `passes_ml_quarantine`):**
   - Refactor `passes_ml_quarantine(pick)` to read the new whitelist format.
   - Gate logic:
     - Extract `variant_id` from pick (symbol_timeframe_side format).
     - If variant is in whitelist → `PASS`.
     - If variant is not in whitelist → `REJECT` with `filter_reason = "ML_VARIANT_QUARANTINED"`.
     - If `mode != "whitelist_only"` → fall back to legacy blocklist behavior (backward compatibility).
   - Add metric: `ml_quarantine_reject_total{variant, reason}`.

3. **In `variant_registry.py`:**
   - Add `get_variant_pf(variant_id, lookback_days=90)` to dynamically compute PF from `pick_lifecycle_log`.
   - Add `promote_from_quarantine(variant_id)` for manual override (requires 2-person approval via `approval_queue`).
   - Add `demote_to_quarantine(variant_id)` for emergency risk-off.

### 2.2 CRYPTO SHORT Regime Integration
- The existing CRYPTO SHORT regime gate (~L4632) remains active.
- Gate execution order: `passes_active_gate` → `passes_post_cost_expectancy` (PR-3) → `passes_ml_quarantine` (this PR) → `passes_crypto_short_regime`.
- A pick must pass ALL gates. `passes_ml_quarantine` runs before the SHORT regime gate so that rejected variants don't waste SHORT-regime compute.

### 2.3 Graduated Exposure for Whitelist Variants
- Even whitelisted variants start with reduced position size:
  - `FETUSDT_1d_B`: 50% of normal position size for 20 picks, then 100%.
  - `INJUSDT_1d_B`: 50% for 10 picks, then 100%.
  - `BNBUSDT_15m_B`: 50% for 10 picks, then 100%.
- This is implemented in `position_sizer.py` via a new `ml_variant_ramp_table`.

---

## 3. Files Changed

| File | Lines | Change |
|---|---|---|
| `crypto_quarantine.json` | +28 / -45 | Restructure to whitelist-only mode; add 3 whitelist entries; auto-quarantine config |
| `quality_gates.py` | +94 / -31 | Refactor `passes_ml_quarantine()` for whitelist logic; metrics; mode switching |
| `variant_registry.py` | +156 / -12 | Add PF computation, promote/demote, approval queue integration |
| `position_sizer.py` | +67 / -8 | Add `ml_variant_ramp_table`; reduced sizing for new whitelist entries |
| `pick_evaluator.py` | +14 / -5 | Update gate chain order; wire `passes_ml_quarantine` |
| `config/asset_class_limits.yaml` | +10 / -2 | CRYPTO whitelist mode config; ramp parameters |
| `pf_registry.json` | +8 / -3 | Update CRYPTO variant counts; whitelist annotation |
| `tests/unit/test_ml_quarantine.py` | +312 | New test suite: whitelist pass, auto-quarantine, ramp sizing, mode fallback |
| `tests/integration/test_crypto_e2e.py` | +156 | End-to-end: verify only 3 variants trade; PF >= 5.0 expected |
| `approval_queue.py` | +45 | Manual promote/demote endpoints; 2-person approval logic |

---

## 4. Test Plan

### 4.1 Unit Tests (`tests/unit/test_ml_quarantine.py`)

| Test Case | Input | Expected |
|---|---|---|
| `test_whitelist_variant_passes` | Pick with variant `FETUSDT_1d_B` | `PASS` |
| `test_non_whitelist_variant_rejected` | Pick with variant `BTCUSDT_1h_B` (PF=0.8) | `REJECT`, reason `ML_VARIANT_QUARANTINED` |
| `test_whitelist_with_pf_degradation` | `FETUSDT_1d_B` pick but 30-day PF dropped to 5.0 | Still `PASS` (whitelist is static; dynamic review on 2026-07-01) |
| `test_ramp_sizing_fetusdt` | First 5 picks of `FETUSDT_1d_B` | Position size = 50% of normal |
| `test_ramp_sizing_after_threshold` | 25th pick of `FETUSDT_1d_B` | Position size = 100% of normal |
| `test_legacy_mode_fallback` | `mode: "blocklist"` in JSON | Falls back to old blocklist behavior |
| `test_bayesian_threshold_included` | `BNBUSDT_15m_B` with n=8 | Passes Bayesian PF > 2.0 test (posterior 97.3%) |
| `test_bayesian_threshold_excluded` | Hypothetical variant with n=7, PF=50 | Rejected (n < 8 minimum) |
| `test_promote_requires_approval` | `variant_registry.promote("NEWVARIANT")` | Queued in `approval_queue`; not active until approved |

### 4.2 Integration Tests (`tests/integration/test_crypto_e2e.py`)
- Replay all 1,942 historical CRYPTO picks with the whitelist gate active.
- Expected: only ~180 picks from the 3 whitelist variants pass.
- Assert PF of passing picks >= 5.0 (blended across 3 variants with ramp sizing).
- Assert 0 picks from non-whitelist variants pass.
- Assert `ml_quarantine_reject_total` metric count = ~1,762.

### 4.3 Manual / QA
- [ ] Deploy to paper-trading; verify only FET, INJ, BNB picks are generated.
- [ ] Confirm `ML_VARIANT_QUARANTINED` is top filter reason in Grafana.
- [ ] Test manual promote workflow: submit `NEWVARIANT` for approval, have second user approve, verify it trades.
- [ ] Test emergency demote: demote `FETUSDT_1d_B`, confirm no FET picks within 1 minute.

---

## 5. Acceptance Criteria

- [ ] `crypto_quarantine.json` uses `mode: "whitelist_only"` with 3 variants explicitly listed.
- [ ] All 146 non-whitelist variants are auto-quarantined (reject rate ~99.3% of variants).
- [ ] Only `FETUSDT_1d_B`, `INJUSDT_1d_B`, and `BNBUSDT_15m_B` generate live picks.
- [ ] Ramp sizing applies: 50% position for first 10-20 picks, then 100%.
- [ ] CRYPTO class PF improves from 1.28 to >= 3.0 within 30 days of deployment (paper trading).
- [ ] `ML_VARIANT_QUARANTINED` is the #1 filter reason for CRYPTO class.
- [ ] Legacy `blocklist` mode is available via config change (backward compatibility).
- [ ] Manual promote/demote requires 2-person approval.
- [ ] All 312 new unit tests pass.
- [ ] Integration test shows PF >= 5.0 on whitelist-only pick subset.
- [ ] No regression in other asset classes.

---

## 6. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Whitelist is too restrictive; misses profitable new variants | Medium | High | Review date set for 2026-07-01; manual promote workflow exists; shadow mode can run new variants in parallel. |
| INJ/BNB small sample size (n=8-12) means PF is unstable | Medium | High | Bayesian threshold requires 95% posterior confidence; ramp sizing limits exposure; max drawdown caps in whitelist. |
| FETUSDT PF degrades below 9.0 | Medium | Medium | Whitelist is static until review date, but `passes_post_cost_expectancy` (PR-3) will filter picks if true edge disappears. |
| Crypto market regime shift invalidates all 3 variants | Low | Critical | This is inherent crypto risk; position sizing and risk limits still apply; max drawdown caps trigger emergency demotion. |
| Approval queue exploit: unauthorized variant promotion | Low | Critical | 2-person approval required; audit log immutable; only `risk-lead` and `strat-lead` roles can approve. |

### Rollback
1. Change `mode` in `crypto_quarantine.json` from `"whitelist_only"` to `"blocklist"`.
2. Restart pick evaluator (config reload).
3. All previously quarantined variants resume trading immediately.
4. **Estimated time: 30 seconds.**

---

## 7. Merge Order

```
PR-1 ──> PR-2 ──> PR-3 ──> PR-4 (this PR) ──> PR-5
                                    ^
                                    │
                              PR-4 depends on PR-3
                              for post-cost expectancy
                              calibration of whitelist PF
```

| Dependency | Reason |
|---|---|
| **PR-3 → PR-4** | PR-4's whitelist PF values (9.25, 41.0, 52.6) are **gross** PF. PR-3's post-cost expectancy gate must be active to ensure these remain positive after slippage. Without PR-3, the whitelist variants could have post-cost PF < 1.0, invalidating the whitelist. |
| PR-4 → PR-5 | PR-5's what-if query must include `ML_VARIANT_QUARANTINED` as a filter reason and allow users to query "what if this CRYPTO variant was not quarantined?" |
| PR-1 (soft) | PR-1's COT fix calibrates the global risk model that sets `max_drawdown_pct` caps for CRYPTO whitelist variants. |

**Merge this PR fourth, after PR-3 is live and post-cost baselines are stable.**
