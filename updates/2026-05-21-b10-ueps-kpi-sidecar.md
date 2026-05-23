# B10 Path B — UEPS KPI Sidecar Panel

**Date:** 2026-05-21
**PR:** feat/b10-ueps-kpi-sidecar-2026-04-30
**Queue item:** B10 (UEPS KPI Panel) from `reports/REMAINING_ACTION_ITEMS_2026_04_30.md`
**Path chosen:** Path B — sidecar unrealized PnL (no operator gate-lift required)

## What shipped

### `audit_trail/dashboard_generator.py`
- New function `_build_ueps_kpi_sidecar(active_raw_picks)` that extracts UEPS picks
  from `picks.active_raw` (source_system == "ueps") and builds a KPI dict:
  open_positions, strategies, tickers, aggregate (avg score, confidence, TP%, SL%, RR,
  unrealized PnL, n_closed=0, closed_wr=None, closed_pf=None).
- Wired into payload at `payload["picks"]["ueps_kpi"]` immediately after
  `active_raw` is fully assembled (post-gate, post-shadow-promotion).

### `audit_dashboard/template.html`
- Added `<div id="ueps-kpi-panel">` between the UEPS intro card and the subtabs.
- Added IIFE `renderUepsKpiPanel()` that reads `D.picks.ueps_kpi` after
  `dashboard-data-loaded` event (supports both embedded + external fetch paths).
- Panel shows: open positions count, avg confidence, avg score, TP%/SL%/RR targets,
  WR/PF as "n/a (accruing)" until UEPS picks exit through the resolver.
- Header n-count badge updated from `n=0` to `n=<open>` (e.g. `n=22 open`).

### `tests/test_dashboard_generator.py`
- 4 new tests: empty input, non-ueps exclusion, full aggregate checks (TP/SL/RR/conf/score), message text.
- All 23 tests pass (0 regressions).

## Why Path B (not A or C)

| Path | Notes |
|------|-------|
| A: Wire UEPS into outcome_resolver | Correct long-term fix; requires significant resolver surgery. Out of scope for one-hour loop run. |
| B: Sidecar unrealized PnL | **Implemented.** Shows live open-position metrics immediately. WR/PF gracefully shows "accruing" — no false data. |
| C: Operator gate-lift | Was recommended in status docs but requires a human reply. Path B is implementable autonomously. |

## Current data (2026-05-21T10:30Z)

- 22 UEPS picks open (QCOM, META, MA, PYPL, COST, GOOGL, JNJ, PEP, LIN, TXN, V, PFE,
  NFLX, T, IBM, MDT, ADBE, HD, XOM, BMY, BA, TSLA)
- Strategy: magic_formula_x_piotroski_x_acquirers
- Avg TP: +8%, Avg SL: -5%, Avg RR: 1.60
- Avg confidence: ~72%, Avg score: 28.6
- 0 closed picks (sidecar path; resolver not wired yet)

## Wire-Up Rule

`_build_ueps_kpi_sidecar` is called from `generate_payload()` in the main
dashboard generation path — it is wired. Production caller:
`audit_trail/dashboard_generator.py::generate_payload()` line ~16978.
