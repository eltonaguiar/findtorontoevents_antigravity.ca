# Fix: Hardwire Promotion Gate + Populate CAGR/Sortino (2026-06-03)

**Commit:** `62479e3a0`  
**Tests:** 100/100 pass (test_promotion_path, test_p1_7_slippage_promotion_gate, test_portfolio_gates, test_portfolio_engine, test_portfolio_kills, test_sidecar_promotion, test_promotion_mysql)

---

## What was broken

### 1. Promotion gate soft-gated (production_scanner.py)

The `PROMOTION_GATE_ENFORCE` env var controlled whether non-admissible picks were rejected. Without it set, `is_admissible_for_production()` returned `False` but picks still passed through via `if _pg_ok or not _pg_enforce:`. With `PROMOTED_STRATEGIES` empty, the gate was effectively dead code.

### 2. CAGR + Sortino never written to DB (run_daily.py)

`compute_metrics()` returned `cagr` and `sortino_30d` in its dict, but the INSERT statement only wrote 7 columns — `sortino_30d` and `cagr` were always NULL in `PF_DAILY_METRICS`.

---

## What changed

### production_scanner.py (line 5615)

Removed `_pg_enforce` env-var check. Changed `if _pg_ok or not _pg_enforce:` → `if _pg_ok:`. Gate now always enforces deny-by-default admission.

### run_daily.py (lines 368-397, 543-549)

- **CAGR**: Uses `date.fromisoformat()` for calendar-day elapsed time. Formula: `((end/start)^(365.25/days)-1)*100`
- **Sortino**: Standard downside-deviation denominator (all returns, not just negative). Formula: `(mean_r / sqrt(mean(neg_r²))) * sqrt(252)`. Sentinel 999.0 when no losing days.
- **INSERT**: Now writes 9 columns including `sortino_30d` and `cagr`
