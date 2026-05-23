# PR-1: Fix COT 3-Day Publication Lag + CT=F Concentration Cap

| Field | Value |
|---|---|
| **Branch** | `fix/cot-lag-concentration-2026-0518` |
| **Target** | `main` |
| **Class** | COMMODITY |
| **M-Code** | M-095 (`passes_active_gate` COT positioning kill) |
| **Status** | NOT_READY → target MONEY_READY |
| **Author** | `quant-dev-1` |
| **Reviewers** | `risk-lead`, `data-pipeline-owner` |

---

## 1. Problem Statement

### 1.1 COT Look-Ahead Leakage (Critical)
The COMMODITY class `passes_active_gate` function (~L6006 in `quality_gates.py`) consumes CFTC Commitment of Traders (COT) positioning data without accounting for the **3-day publication lag**. The CFTC releases COT reports every Friday at 3:30 PM ET covering data as-of the prior Tuesday. Our pipeline was stamping COT data with "available timestamp" rather than "reference timestamp," causing the gate to evaluate Friday-executed picks using Tuesday COT data that was not yet public.

**Impact:**
- Headline win rate of **87%** on CT=F (WTI Crude Oil Futures) backtests collapsed to **30%** when the 3-day lag was correctly applied.
- The gate appeared to work in backtests but fails in live/paper trading because the signal is non-stationary with respect to information availability.

### 1.2 CT=F Single-Symbol Concentration (Critical)
`pf_registry.json` (2026-05-18T00:27:46Z) shows CT=F at **84.9% concentration** within the COMMODITY class. With only `n=160` resolved picks and a class WR of **45.0%**, the entire class PF is being driven by a single instrument whose true edge was inflated by look-ahead leakage.

**Live Data Snapshot:**
```json
{
  "class": "COMMODITY",
  "n_resolved": 160,
  "win_rate": 0.450,
  "profit_factor": 1.17,
  "status": "NOT_READY",
  "concentration": {
    "CT=F": 0.849,
    "next_highest": 0.031
  },
  "headline_vs_lag_corrected": {
    "CT=F_wr_headline": 0.87,
    "CT=F_wr_lag_corrected": 0.30
  }
}
```

### 1.3 Root Cause
- `data_pipeline/cot_ingestor.py` assigns `available_timestamp = download_timestamp` instead of `reference_timestamp = tuesday_close_timestamp + 3_days`.
- `position_sizer.py` has no per-symbol concentration ceiling for COMMODITY futures.

---

## 2. Solution

### 2.1 COT Lag Correction
1. **In `data_pipeline/cot_ingestor.py`:**
   - Change the COT record timestamp assignment from download-time to `reference_tuesday_close + 3 trading days`.
   - Add a new field `cot_publication_timestamp` that is explicitly set to Friday 15:30 ET.
   - Backfill all historical COT records in the `cot_positioning` table with corrected timestamps.

2. **In `quality_gates.py` (~L6006, `passes_active_gate`):**
   - The gate already reads `cot_positioning` via `get_cot_signal(symbol, as_of)`.
   - Ensure `as_of` is strictly compared against `cot_publication_timestamp`, not `cot_data_timestamp`.
   - Add assertion: `if pick_timestamp < cot_publication_timestamp: raise LookAheadLeakageError(...)`.

### 2.2 35% Concentration Cap
1. **In `position_sizer.py`:**
   - Add `MAX_SINGLE_SYMBOL_PCT = 0.35` to the COMMODITY class configuration.
   - In `compute_position_size()`: if the proposed notional for a single symbol exceeds 35% of total COMMODITY class allocated capital, scale the position down to the cap.
   - If the cap is hit, emit a `CONCENTRATION_CAP_HIT` telemetry event with symbol and scaled_notional.

2. **In `quality_gates.py`:**
   - Add a pre-flight gate `check_concentration_cap(symbol, class, proposed_notional)` that runs before `passes_active_gate`.
   - Hard-reject picks that would breach 35% even after scaling (i.e., if minimum_lot_size still exceeds cap, reject outright).

---

## 3. Files Changed

| File | Lines | Change |
|---|---|---|
| `data_pipeline/cot_ingestor.py` | +45 / -12 | Add `cot_publication_timestamp`, backfill logic, timestamp correction |
| `quality_gates.py` | +38 / -6 | Enforce `as_of >= cot_publication_timestamp`; add concentration pre-flight gate ~L6006 |
| `position_sizer.py` | +62 / -8 | Add `MAX_SINGLE_SYMBOL_PCT=0.35` for COMMODITY; scale-to-cap logic |
| `config/asset_class_limits.yaml` | +8 / -2 | Document 35% concentration cap for COMMODITY |
| `tests/unit/test_cot_lag.py` | +189 | New test suite: leakage detection, timestamp alignment, cap enforcement |
| `tests/integration/test_commodity_e2e.py` | +94 | Backtest-with-lag vs. live-simulation parity test |
| `alembic/versions/026_fix_cot_timestamps.py` | +67 | DB migration: add `cot_publication_timestamp` column, backfill |

---

## 4. Test Plan

### 4.1 Unit Tests (`tests/unit/test_cot_lag.py`)

| Test Case | Input | Expected |
|---|---|---|
| `test_cot_publication_timestamp_set_correctly` | Tuesday close COT data ingested on Friday | `cot_publication_timestamp` = Friday 15:30 ET |
| `test_gate_rejects_pre_publication_pick` | Pick timestamp = Friday 14:00 ET | `LookAheadLeakageError` raised |
| `test_gate_accepts_post_publication_pick` | Pick timestamp = Friday 16:00 ET | Gate evaluates normally |
| `test_concentration_cap_scales_position` | Proposed notional = 50% of class capital | Scaled to 35%; `CONCENTRATION_CAP_HIT` emitted |
| `test_concentration_cap_hard_reject` | Min lot size > 35% cap | Pick rejected with `CONCENTRATION_BREACH` |
| `test_ct=f_wr_post_fix` | 1000 simulated CT=F picks with lag-corrected COT | WR in [0.25, 0.35] (consistent with 30% corrected) |

### 4.2 Integration Tests (`tests/integration/test_commodity_e2e.py`)
- Run the full COMMODITY pipeline for 2025-01-01 to 2026-05-01 with both:
  - (A) Old codepath (leakage-present) — expect PF ~1.9, WR ~60%
  - (B) New codepath (lag-corrected) — expect PF ~1.05, WR ~30-35%
- Verify the delta is statistically significant (p < 0.001 via bootstrap).

### 4.3 Manual / QA
- [ ] Run `make backtest class=COMMODITY start=2025-01-01 end=2026-05-01` and confirm CT=F concentration drops from 84.9% to <35%.
- [ ] Verify `pf_registry.json` output shows `CT=F` capped.
- [ ] Check `pick_lifecycle_log` for `CONCENTRATION_CAP_HIT` events.

---

## 5. Acceptance Criteria

- [ ] `cot_publication_timestamp` is populated for 100% of COT records (migration backfill completes without error).
- [ ] `passes_active_gate` raises `LookAheadLeakageError` if any pick timestamp predates `cot_publication_timestamp`.
- [ ] CT=F concentration in COMMODITY class is capped at 35% — no single symbol exceeds this threshold in `pf_registry.json`.
- [ ] COMMODITY class PF drops to reflect true lag-corrected performance (expected range 0.95–1.10, not 1.17).
- [ ] All 189 new unit tests pass (`pytest tests/unit/test_cot_lag.py -v`).
- [ ] Integration backtest shows WR ~30% for CT=F (not 87%).
- [ ] No regression in other classes (CRYPTO, FOREX, ETF, BOND, FUTURES).
- [ ] DB migration `026_fix_cot_timestamps.py` is reversible (`alembic downgrade -1` succeeds).

---

## 6. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Backfill migration corrupts historical COT table | Low | Critical | Full table dump taken before migration; migration runs in transaction with rollback on failure. |
| Concentration cap overly restricts valid high-conviction CT=F picks | Medium | Medium | Cap is configurable via `asset_class_limits.yaml`; can be raised to 45% via hot config if needed. |
| Look-ahead leakage exists in other gates (CRYPTO, FOREX) | Medium | High | Audit ticket #4428 opened to inspect all `as_of` timestamp comparisons across `quality_gates.py`. |
| PF drop triggers risk-management circuit breaker | Low | High | Pre-notify risk desk; PF drop is *correct* (removing fake alpha), not a system failure. |

### Rollback
1. Revert commit: `git revert HEAD` (single merge commit).
2. Run `alembic downgrade -1` to restore old COT timestamps.
3. Restart pick evaluation service.
4. Estimated rollback time: **4 minutes**.

---

## 7. Merge Order

```
PR-1 (this PR) ──> PR-3 ──> PR-4 ──> PR-5
  │
  └─> PR-2 (independent)
```

| Dependency | Reason |
|---|---|
| **None (first in sequence)** | PR-1 is the foundation. It fixes the most severe data leakage in the system. |
| PR-1 → PR-3 | PR-3's slippage gate relies on accurate win-rate baselines; PR-1 corrects the inflated COMMODITY WR that feeds into global slippage estimates. |
| PR-1 → PR-4 | PR-4's CRYPTO quarantine references true PF baselines; COMMODITY leakage correction calibrates the cross-class risk model used by M-105. |
| PR-1 → PR-5 | PR-5's what-if query must show correct historical filtering reasons; PR-1 changes the `filter_reason` for many historical COMMODITY picks from `PASSED` to `COT_LAG_REJECTED`. |

**Merge this PR first.**
