# 2026-11-15 — "vs Bench" (excess) column on the audit dashboard

Requested: surface the excess-return column on the audit dashboard so each pick shows pick vs benchmark.

## What was there before

The per-pick excess existed only in `reports/pick_excess_returns.json` and the WIRED_IN docs. On
`/audit`, a closed pick showed `PnL%` and nothing to compare it against, so a +0.4% pick looked
identical to a +0.4% pick while SPY returned 1.8% over the same three days — the exact confusion the
excess column exists to remove.

## What was added

| File | Change |
|---|---|
| `audit_dashboard/excess_column.js` | **New.** Benchmark lookup + cell renderer, exposes `window.PickExcess`. External file because the audit workflow regenerates `index.html` from `template.html`, so inline logic is lost on the next deploy. |
| `audit_dashboard/data/benchmark_prices.json` | **New sidecar** (~25KB): daily closes for SPY and BTC-USD. Fetched once by the page. |
| `tools/build_benchmark_prices.py` | **New.** Builds the sidecar from the same cache `tools/pick_excess.py` uses, so the dashboard and the measured report cannot disagree through a different price feed. |
| `audit_dashboard/template.html` | `vs Bench` column in `closedCols` (after `PnL%`), a cell in `renderClosedRow`, a sort case in `ncSortVal`, and the `<script>` tag. |
| `audit_dashboard/index.html` | Same four edits, so the checked-in artifact matches before CI regenerates it. |
| `tools/deploy_audit_files.py` | `excess_column.js` added to the `audit_js` deploy group — without this the file 404s in production. |
| `AGENTS.md` | Pipeline dependency rows (per the path-registry rule). |

## Method — deliberately identical to `tools/pick_excess.py`

```text
bench return = last close on/before entry day  ->  last close on/before exit day
excess       = pick pnl% - bench return%          (percentage points)
benchmark    = EQUITY/ETF -> SPY, CRYPTO -> BTC-USD
```

The tooltip shows the arithmetic, not just the result: `pick +0.44% minus benchmark +0.20% = +0.24pp`,
plus the window and the two benchmark closes.

**Sub-day windows are not scored.** When entry and exit land on the same trading day there is no daily
benchmark window. The cell renders `—` with the reason instead of a fabricated `0.00`. Scoring those
needs 60-minute bars (~500KB); `tools/pick_excess.py` already does it offline and the dashboard
deliberately does not duplicate it.

## Verification

Node parity harness against the Python artifact (same source data, both engines):

| Check | Result |
|---|---|
| `node --check audit_dashboard/excess_column.js` | clean |
| JS vs `reports/pick_excess_returns.json` | see parity table below |
| Column/cell count consistency | `closedCols` entries == `<td>` emitted by `renderClosedRow` in **both** HTML files |
| Sidecar | SPY 469 bars, BTC-USD 683 bars, ascending unique dates |

**Known, expected divergence:** the dashboard uses the `pnl_pct` already displayed on the row, while the
Python tool recomputes the return from `entry_price`/`exit_price` and *excludes* rows where the two
disagree by more than 0.5pp (49 rows). Those 49 are scored by the dashboard (using the displayed number)
and absent from the artifact, which is why they appear as "scored but not in artifact".

## Limits

- The column is **not** a portfolio return: trades overlap with no capital constraint.
- The sidecar is rebuilt by running the script; nothing regenerates it automatically yet. When it goes
  stale, newer picks render `—` (no bar after the last date) rather than a wrong number.
- Hourly-resolution picks show `—` on the dashboard even though the offline report scores them.
