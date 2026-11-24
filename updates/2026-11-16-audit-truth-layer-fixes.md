# 2026-11-16 audit truth-layer fixes

## What was broken

Peer plans under `ACTIONPLAN_AUDITPAGE/` agreed the /audit page overstated data quality. Rechecked against `origin/main` before editing:

- `tools/db_health_check.py` marked 22,947 ghost rows as a pass (`threshold_pass` was `< 100000`, tier yellow). The health strip stayed green.
- The deployed `audit_dashboard/index.html` still said "Ghost rows: 0 (was 22,947)".
- The sign-consistency tile was labelled "PnL Integrity 99.5%" and hid the 27.05% magnitude mismatch (6,535 / 24,158) already stored in `db_health.json`.
- Embedded age banner went red at 60 minutes. The publish job is hourly and can run 30–115 minutes, so a healthy page looked stale.
- Zero-loss profit factor and open W/L rendered as `∞`, which reads as edge.
- The major-goal line still cited June sleeves (`futures_momentum` PF 2.6, `forex_rsi2` PF 2.4). Those numbers are not in current JSON.

## What changed

- `ghost_row_verdict()`: 0 = green pass; 1–999 = yellow fail; ≥1000 = red fail. `check_ghost_rows()` uses it, so `banner_should_show` trips while ghosts remain. The check `ok` flag stays true so the tile still renders.
- Dashboard tile title is now "Sign consistency (sampled)" and prints both sign and magnitude counts.
- Template and deployed index drop the "Ghost rows: 0" claim, render `n/a` instead of `∞`, and raise the stale banner to 150 minutes.
- Stale PF 2.6 / PF 2.4 forward-track sentence removed from the template banner.

## What this does not fix

- Ghost rows are still in `bt_backtest_trades`. No `--execute` cleanup was run.
- Prediction-market path split and missing `kalshi_signals.json` are unchanged. Markets stay shadow.
- No sizing change. 0 classes are money-ready.

## How it was verified

`python3 -m unittest tests.test_ghost_row_verdict -v`

Live-page checks are in `ACTIONPLAN_AUDITPAGE/2026-11-16T0635Z_kilo_auditpage/TESTING_PLAN.md`.
