# D-008: per_class_trainer Shadow Mode — Training Data Volume Assessment

**Date:** 2026-05-18  
**Analyst:** Claude Sonnet 4.6  
**Decision:** PROCESS NOW (models trained; shadow validation required before wiring into gates)

---

## Training Data Volume (from `audit_dashboard/data/dashboard_data.json::picks.recent_closed`)

| Asset Class | n (closed) | Base WR | Min n Threshold | Trainable? |
|-------------|-----------|---------|-----------------|------------|
| CRYPTO      | 2,796     | 45.2%   | 50              | YES        |
| EQUITY      | 252       | 53.6%   | 50              | YES        |
| FOREX       | 142       | 45.1%   | 50              | YES (shadow only) |
| FUTURES     | 129       | 4.7%    | 50              | YES (degenerate — see §3) |
| ETF         | 113       | 53.1%   | 50              | YES        |
| COMMODITY   | 56        | 53.6%   | 50              | YES (marginal n) |
| BOND        | 12        | 50.0%   | 50              | NO (stub)  |

---

## Per-Class Model Results (`ml_gatekeeper/data/per_class_gates.json`)

| Asset Class | CV AUC | Threshold | Status |
|-------------|--------|-----------|--------|
| CRYPTO      | 0.5812 | 0.55      | trained |
| EQUITY      | 0.5634 | 0.65      | trained |
| COMMODITY   | 0.6299 | 0.45      | trained (best AUC) |
| ETF         | 0.5619 | 0.65      | trained |
| FOREX       | 0.5974 | 0.70      | trained (HARD_DISABLED — shadow only) |
| FUTURES     | nan    | 0.50      | trained (DEGENERATE) |
| BOND        | —      | —         | insufficient_data stub |

---

## Key Findings

### 1. CRYPTO training set is contaminated by blocked strategies

The `recent_closed` dataset includes all historical picks including those from blocked sources
(`quan_engine_scalp`, `rapid_fire`, etc.). This pulls CRYPTO base WR down to 45.2% vs
the production-filtered WR of 66.4% seen on the dashboard.

**Impact:** The CRYPTO model learns patterns from toxic picks (quantity bias), which may cause
it to assign high win-probability to picks that the production gates already block.

**Recommendation (future work):** Add a `--filter-passed-gates` flag to `per_class_trainer.py`
that pre-filters closed picks through `is_blocked_strategy()` / `is_blocked_pick()` before
training. This would give the model a cleaner training distribution that matches the production
pick population.

### 2. FUTURES model is degenerate

FUTURES closed_picks WR = 4.7% (6 wins / 123 losses). This is dominated by
`multi_asset_copytrader` (WR=3%, n=203, already known from 2026-05-17 P0 gates session).
AUC = nan because the model essentially predicts "loss" for all picks — there is not enough
positive-class signal to learn from.

**Recommendation:** Mark FUTURES per-class model as `degenerate_low_wr` in the gates
manifest. Do not wire this model into gates until the underlying FUTURES strategy mix is fixed.

### 3. COMMODITY AUC is best (0.630) but n=56 is marginal

Small n means CV estimates have high variance. AUC=0.630 could be ±0.10 in production.

### 4. BOND deferred (n=12 < MIN_TRAIN_N=50)

BOND picks started accumulating only 2026-05-17. MySQL sync 2026-05-24 is the unlock event.

---

## Decision: D-008 = PROCESS NOW

**Models trained:** 6/7 classes trained and saved to `ml_gatekeeper/models/per_class/`.
**Gates manifest:** `ml_gatekeeper/data/per_class_gates.json` committed.

**Shadow validation required before wiring into `passes_active_gate`:**
- Minimum 30-day calibration window to confirm model output correlates with live WR
- Priority order for wiring: EQUITY (cleanest signal) → ETF → CRYPTO (after contamination fix)
- FUTURES: do not wire until WR is above 20% (strategy mix improvement required)
- FOREX: do not wire (HARD_DISABLED)

**Regeneration command:**
```bash
python ml_gatekeeper/per_class_trainer.py                      # all classes
python ml_gatekeeper/per_class_trainer.py --class CRYPTO       # one class
ML_GATE_DROP_LEAKAGE=1 python ml_gatekeeper/per_class_trainer.py  # no leakage
```

---

## Files Changed

- `ml_gatekeeper/data/per_class_gates.json` — gates manifest (committed)
- `ml_gatekeeper/models/per_class/*.joblib` — model bundles (gitignored — regenerate with above command)
