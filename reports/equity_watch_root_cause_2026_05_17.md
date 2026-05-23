# EQUITY WATCH Root Cause Analysis — 2026-05-17

**Generated:** 2026-05-17  
**Trigger:** EQUITY verdict = WATCH despite wr_ok=True, pf_ok=True, n_ok=True.

---

## Summary

EQUITY is WATCH because DSR/PBO/SPA statistical tests cannot run. The local `closed_picks.json` has only 44 EQUITY picks (37 from one strategy), while the dashboard reports n=240 from a larger historical dataset (MySQL). Until the MySQL ghost-row purge (2026-05-24) and data sync, local statistical tests remain null.

---

## Data Discrepancy

| Source | n | WR | Note |
|---|---|---|---|
| `closed_picks.json` (local) | 44 | ~35% | Only picks resolved via local resolver |
| `dashboard_data.json` (fallback) | 240 | 53.3% | Aggregated from full MySQL dataset |

The n=240 figure that `money_ready_verdict()` uses for basic checks comes from `dashboard_data.json` fallback. But DSR/SPA computation requires the actual pick-level return data from `closed_picks.json`, where EQUITY has only 44 picks.

---

## Local EQUITY Strategy Breakdown

| Strategy | n | WR |
|---|---|---|
| stocks_rsi2_pullback | 37 | 37.8% (14W/23L) |
| smart_money_accumulation | 4 | 0% (already KILLED) |
| stocks_rsi2_pullback_tight | 1 | 0% |
| stocks_rsi2_pullback_wide | 1 | 100% |
| futures_connors_rsi2 | 1 | 100% |

**Key insight:** `stocks_rsi2_pullback` shows WR=37.8% locally vs 53.3% in dashboard aggregate. This gap (15.5pp) likely reflects:
1. Picks resolved locally vs MySQL-side (different data subsets)
2. Or the strategy's genuine edge appears at n=100+ level but not in n=37 local subset

---

## DSR/SPA Blocker

- `dsr_ok = null`: "n=7 too small for DSR" — refers to n_strategies passed to DSR computation; actual reason is only 1 EQUITY strategy (stocks_rsi2_pullback) has n≥20, but DSR needs per-pick return series.
- `pbo_ok = null`: "need ≥2 strategies with n≥20, got 0" — locally 0 strategies qualify because local picks lack strategy-level tracking for SPA.
- `spa_ok = null`: "no strategies with n≥20" — same root cause.

---

## Verdict Blocker Chain

```
money_ready_verdict(EQUITY)
  → data_source = "dashboard_fallback"  (n=240, WR=53.3% from dashboard_data.json)
  → DSR computation: reads closed_picks.json → 44 EQUITY picks found
      → by strategy: stocks_rsi2_pullback n=37 — only 1 strategy, but system needs...
      → dsr module gets n_strategies=1 "too small" → dsr_ok=null
  → verdict = WATCH (statistical tests inconclusive)
```

---

## Recommendation

**Do NOT force MONEY_READY.** The verdict is correctly WATCH given statistical uncertainty.

**Path to EQUITY MONEY_READY:**

1. **Short-term (2026-05-24):** MySQL ghost-row purge + sync. Expect local closed_picks.json to have n≥100 EQUITY picks from `stocks_rsi2_pullback`. At n≥100, DSR/SPA become computable.

2. **Code gate:** `money_ready_verdict()` should check if n_local < 20% of n_dashboard and emit a `"data_sync_needed"` warning flag (not currently implemented). This would make the WATCH reason explicit.

3. **Second strategy needed for PBO:** `pbo_ok` requires ≥2 strategies with n≥20. After MySQL sync, check if `stocks_rsi2_pullback_tight` or `stocks_rsi2_pullback_wide` can accumulate n≥20.

**Estimated MONEY_READY timeline:** 2026-05-24 (after MySQL purge) if `stocks_rsi2_pullback` continues at WR≥52% and n reaches 100+.

---

## Files Referenced

- `alpha_engine/data/closed_picks.json` — local picks (n=44 EQUITY)
- `audit_dashboard/data/dashboard_data.json::performance.asset_class_health.EQUITY` — n=240 WR=53.3%
- `alpha_engine/money_ready_verdict.py` — dashboard fallback logic, DSR/SPA computation
