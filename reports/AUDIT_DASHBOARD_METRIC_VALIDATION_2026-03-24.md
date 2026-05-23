# Audit Dashboard Metric Validation

Date: 2026-03-24

## Scope

Validated `findtorontoevents.ca/audit` from a rendered-metrics perspective, then patched the local dashboard source and added a Playwright regression to validate:

- summary cards vs visible tab counts
- asset-class drill-down counts vs rendered tables
- summary metrics across asset/filter combinations

Files changed locally in this pass:

- `audit_dashboard/index.html`
- `audit_dashboard/template.html`
- `playwright.config.ts`
- `tests/audit_metric_matrix_validation.spec.ts`

## Live-Site Findings

Live page checked: `https://findtorontoevents.ca/audit/`

The live site is materially inconsistent today.

### 1. Summary active count does not match the Active tab

After `Clear All` on the live page:

- Summary `Active Picks`: `385`
- Active tab heading: `239`

This is not a rounding issue. The summary was counting picks that the Active tab hides.

### 2. Summary closed count does not match the Closed tab

After `Clear All` on the live page:

- Summary `Closed Picks`: `11329`
- Closed tab heading: `1990`

This is a methodology mismatch: the summary card is full-history, while the table is recent loaded closed picks only.

### 3. Overview drill-down counts do not reconcile with what opens

Asset-class drill links on the live page currently overstate what the user sees after click-through:

| Asset | Overview Active Link | Active Tab After Click | Overview Closed Link | Closed Tab After Click |
|---|---:|---:|---:|---:|
| CRYPTO | 232 | 158 | 10512 | 1850 |
| EQUITY | 100 | 73 | 665 | 93 |
| FOREX | 31 | 6 | 175 | 24 |
| COMMODITY | 21 | 2 | 22 | 10 |
| FUTURES | 13 | 0 | 33 | 13 |

### 4. Drill links do not reset filters or rerender the summary

On the live page, overview drill links were only calling `renderPicks()`. They were not:

- clearing existing score/filter state
- rerendering summary cards

That made drill-through especially misleading when the page already had `Score=≥ 50` selected by default.

## Root Cause

Two main implementation problems caused the visible mismatch:

### A. `renderSummary()` and `renderPicks()` used different active-pick baselines

`renderSummary()` was filtering:

- invalid entries
- blocked systems
- stale low-impact picks

But it was **not** filtering:

- resolved `TP_HIT` / `SL_HIT` picks hidden from the Active tab
- low-score `rapid_fire` noise hidden from the Active tab

So the summary card could not match the table.

### B. Overview drill links used backend totals, not drillable visible counts

The overview active/closed link counts were based on backend aggregate stats, while the target tabs show:

- visible active picks after client-side hiding rules
- recent loaded closed picks, not full closed history

That made the counts non-drillable in practice.

## Local Fixes Applied

Implemented locally in both `index.html` and `template.html`:

1. Added shared helper logic for the visible active-pick baseline:
   - recompute live age from timestamp
   - remove blocked systems
   - remove stale low-impact picks
   - remove garbage entries
   - remove hidden resolved picks
   - remove hidden low-score `rapid_fire` noise

2. Updated `renderSummary()` to use that same active baseline as the Active tab.

3. Added `resetPickFilters()` and `applyDrillFilter()` so overview drill-down:
   - clears prior filter state
   - switches tab
   - rerenders both summary and picks

4. Rebased overview drill-link counts onto drillable local counts:
   - active counts now use the visible active dataset
   - closed counts now use the loaded recent-closed dataset

## Playwright Validation

Added regression:

- `tests/audit_metric_matrix_validation.spec.ts`

Run:

```bash
npx playwright test tests/audit_metric_matrix_validation.spec.ts --project="Desktop Chrome"
```

Result on local patched dashboard:

- `3 passed`

Validated areas:

1. Summary active card matches the Active tab after `Clear All`
2. Overview drill links reconcile to the destination tabs
3. Summary metrics match recomputed filtered data across 25 matrix cases:
   - `CRYPTO`, `EQUITY`, `FOREX`, `COMMODITY`, `FUTURES`
   - asset only
   - asset + `LONG`
   - asset + profitable only
   - asset + `conf >= 0.65`
   - asset + `age <= 48h`

Metrics checked per case:

- Active Picks
- Closed Picks
- Win Rate
- Total PnL
- Profit Factor
- Expectancy
- W / L
- Systems

## Residual Notes

- The local server still logs a missing `audit_dashboard/data/stock_prices.json` request. That did not break the metric regression, but it is still a fetch hole worth cleaning up.
- The live site remains unfixed until these local dashboard changes are deployed.

## Bottom Line

The live `/audit` page currently has real count/metric reconciliation bugs.

The local patch fixes the main client-side accuracy issues and the new Playwright regression now proves the rendered summary/drill-down/filter matrix is internally consistent on the patched dashboard.
