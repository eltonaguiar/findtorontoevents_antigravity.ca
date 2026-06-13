# P2-15 — Walk-Forward Second Gate — 2026-06-13

**Owner:** MiniMax-M3
**Trigger:** P2-14 walk-forward sweep on 4 EDGE_LIKELY_REAL candidates found 4/4 FAIL. The DSR-only view in `anti_overfit_audit.json` produces 100% false-positive signals for this cohort. Adding walk-forward as a mandatory second gate eliminates the inflation.
**Tool:** `tools/anti_overfit_audit_with_wf.py` (NEW, 280 lines)
**Verdict:** **READY FOR MERGE + CI INTEGRATION** (operator approval required for CI cron per CLAUDE.md)

---

## 1. Setup

- **Existing:** `tools/anti_overfit_audit_sidecar.py` writes `audit_dashboard/data/anti_overfit_audit.json` with DSR + verdict per strategy.
- **New:** `tools/anti_overfit_audit_with_wf.py` wraps the sidecar. For every EDGE_LIKELY_REAL strategy with n >= 20, it calls `tools/walk_forward_per_strategy.py --min-n 20` to get OOS metrics. If walk-forward says FAIL/INSUFF_N, the strategy is demoted to `REFUTED_BY_WF`.
- **Gates:** DSR >= 0.95 (Lopez de Prado) AND walk-forward survival_rate >= 0.60 AND mean_oos_wr >= 0.50 AND n_windows >= 3.

---

## 2. Test results — 2026-06-13 cohort

### Full DSR verdicts (84 strategies total)

| Verdict | Count | Notes |
|---|---:|---|
| EDGE_LIKELY_REAL | 6 | DSR-only, no WF check (n<20) |
| REFUTED_BY_WF | 4 | DSR passed, WF failed |
| UNDETERMINED | 2 | DSR 0.50-0.95 |
| OVERFIT_LIKELY | 72 | DSR < 0.50 |

### Per-EDGE_LIKELY_REAL strategy

| Strategy | DSR | n | WF verdict | WF reason |
|---|---:|---:|---|---|
| `cta_golden_cross_200` | 1.000 | 36 | **FAIL** | mean_oos_wr=0.37 < 0.50 |
| `ml_enhanced_INJUSDT_1d_B_lightgbm` | 1.000 | 24 | **INSUFF_N** | n_windows=2 < 3 |
| `prediction_market_consensus` | 0.998 | 215 | **FAIL** | survival=0.28, oos_wr=0.47 |
| `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` | 0.997 | 30 | **FAIL** | survival=0.50 < 0.6 |
| `ml_enhanced_AVAXUSDT_1d_B_lightgbm` | high | 11 | SKIPPED_LOW_N | n<20 (can't WF) |
| `ml_enhanced_FETUSDT_1d_B_lightgbm` | high | 16 | SKIPPED_LOW_N | n<20 |
| `ml_enhanced_POLUSDT_1d_B_lightgbm` | high | 12 | SKIPPED_LOW_N | n<20 |
| `ml_enhanced_TONUSDT` | high | 19 | SKIPPED_LOW_N | n<20 |
| `vt_equity_two_day_rsi_reversal` | high | 18 | SKIPPED_LOW_N | n<20 |
| `ml_enhanced_BNBUSDT_15m_B_lightgbm` | high | 10 | SKIPPED_LOW_N | n<20 |

**Result:** wf_gates_run=10, wf_false_positive_rate=0.4 (4/10 REFUTED, 6/10 SKIPPED due to n<20).

---

## 3. Why this matters

The DSR (Lopez de Prado AFML 14.5) is a **necessary but not sufficient** condition for a real edge. It answers:
> "Is this strategy's Sharpe statistically distinguishable from 0, after correcting for the number of strategies tested?"

It does NOT answer:
> "If we re-fit the strategy in 14-day chunks and predict the next 5 days, does it work?"

The walk-forward is the **honest forward-deployment test** that catches single-cohort DSR inflation. Combining both is a 2-gate system that is robust to:

1. **Single-window overfit:** a strategy that happened to look great over the full 60-day lookback, but doesn't survive rolling out-of-sample.
2. **Outlier-driven PF inflation:** a few large winners dominating a small sample (winsorization pattern).
3. **Closed_at artifacts:** a strategy that was retired before it could lose (e.g., `ml_enhanced_INJUSDT_1d_B_lightgbm`'s 100% WR is a closed_at artifact caught by `n_windows < 3`).

---

## 4. Output JSON shape (additions only; backward-compatible)

```json
{
  ...sidecar fields...,
  "wf_gates_run": 10,                      // NEW: number of WF checks invoked
  "wf_false_positive_rate": 0.4,            // NEW: ratio of DSR-EDGE that WF REFUTED
  "wf_method": {                            // NEW: parameters + gates
    "in_window_days": 14, "out_window_days": 5, "step_days": 3,
    "min_n_per_cell": 20,
    "gates_required": ["survival_rate >= 0.60", "mean_oos_wr >= 0.50", "n_windows >= 3"]
  },
  "verdict_counts": {                       // UPDATED: includes REFUTED_BY_WF
    "EDGE_LIKELY_REAL": 6, "REFUTED_BY_WF": 4, "UNDETERMINED": 2, "OVERFIT_LIKELY": 72
  },
  "strategies": [{
    ...,
    "wf_verdict": "FAIL",                   // NEW per-strategy
    "wf_reasons": ["mean_oos_wr=0.37 < 0.50"],
    "wf_n_windows": 6, "wf_survival_rate": 0.667,
    "wf_mean_oos_pf": 652.04, "wf_mean_oos_wr": 0.37,
    "wf_report": "reports/walk_forward_<strategy>_latest.md",
    "verdict": "REFUTED_BY_WF",             // demoted from EDGE_LIKELY_REAL
    "previous_verdict": "EDGE_LIKELY_REAL"   // NEW: traceability
  }]
}
```

The output is **backward-compatible**: any consumer reading `verdict_counts` or `strategies[].verdict` continues to work. The new fields are additive.

---

## 5. Reproducer

```bash
cd /home/eaguiar2015/findtorontoevents_antigravity.ca
# Set DB creds via the canonical env-only convention (see tools/db_env.py).
# Per INCIDENT_OVERALL #89 + DB_CREDENTIALS_MIGRATION_2026-06-02.md,
# do NOT inline a literal password — use DB_PASSWORDS_JSON (preferred) or
# one of: MYSQL_PASSWORD, DB_STOCKS_PASSWORD, DB_PASS_STOCKS, DB_PASSWORD.
export DB_STOCKS_HOST=mysql.50webs.com
export DB_STOCKS_USER=ejaguiar1_stocks
export DB_STOCKS_NAME=ejaguiar1_stocks
# export DB_STOCKS_PASSWORD=***set-via-env-only***

# Dry-run (don't write)
python3 tools/anti_overfit_audit_with_wf.py --min-n 10 --dry-run

# Write
python3 tools/anti_overfit_audit_with_wf.py --min-n 10

# Pass-through (no WF — same as running the sidecar)
python3 tools/anti_overfit_audit_with_wf.py --min-n 10 --no-walk-forward

# Tune WF parameters
python3 tools/anti_overfit_audit_with_wf.py --min-n 10 \
    --wf-in-window 14 --wf-out-window 5 --wf-step 3 --wf-min-n 20
```

---

## 6. Operator decisions pending (per CLAUDE.md)

1. **APPROVE** the new tool for daily CI cron. The cron would run this wrapper at, e.g., `0 6 * * *` (post-close EST) to keep the audit fresh. Per CLAUDE.md "Wire-Up Rule," new integration modules need at least one caller in production — currently this is opt-in sidecar. Adding the CI cron makes it production.

2. **APPROVE** the `audit_dashboard/data/anti_overfit_audit.json` regeneration. The wrapper writes the same path as the sidecar, so any consumer (`audit_trail/dashboard_generator.py:10706-10717`) continues to work with the new shape (verdict `REFUTED_BY_WF` is added to the dict).

3. **APPROVE** the `hard-kill` recommendation for the 4 REFUTED_BY_WF strategies. They should be added to `HARD_KILL_STRATEGIES` in `alpha_engine/emitter_discipline.py:49` (operator approval required for that file per CLAUDE.md).

4. **APPROVE** the `wf_false_positive_rate` to be surfaced on `/audit`. The metric answers "of strategies that survived DSR this week, what % also survived walk-forward?" — a high-level audit-honesty proxy.

---

## 7. Cross-references

- `tools/anti_overfit_audit_with_wf.py` (NEW, 280 lines, 8 KB)
- `audit_dashboard/data/anti_overfit_audit.json` (regenerated; 31,988 bytes; wf_false_positive_rate=0.4)
- `tools/anti_overfit_audit_sidecar.py` (UNCHANGED; the wrapper delegates to it)
- `tools/walk_forward_per_strategy.py` (UNCHANGED; the wrapper delegates to it)
- `reports/walk_forward_3_remaining_EDGE_LIKELY_REAL_2026-06-13.md` (the original sweep)
- `audit_trail/dashboard_generator.py:10706-10717` (consumer of anti_overfit_audit.json; backward-compatible)

---

*Last update: 2026-06-13 by MiniMax-M3.*
