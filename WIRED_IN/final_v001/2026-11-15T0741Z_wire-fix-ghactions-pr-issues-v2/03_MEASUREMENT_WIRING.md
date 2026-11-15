# 03 — Measurement Wiring: make the clock actually run

The forward ledger exists but is not invoked. This is the shortest path to a
trustworthy "vs Bench" panel on `findtorontoevents.ca/audit`. Do these in order;
each has a verifiable exit.

## Step 1 — Merge the three ready PRs (in order)

```bash
gh pr merge 713 --squash --delete-branch   # backup-verify: live fetch + issue dedup
gh pr merge 786 --squash --delete-branch   # QA keys + rebase + sports smoke pin
gh pr merge 785 --squash --delete-branch   # forward clock, excess column, pick_excess, benchmark prices
```
Exit: `Backup Restore Verification` green; QA green; `/audit` `template.html`
contains `excess_column.js` + `forward_clock.js`.

## Step 2 — Close the production 404 (PR 785 does NOT do this)

Add the two JS files to every FTP include list and to the Python deployer:

- `.github/workflows/audit-dashboard.yml` (three sites): the hard-coded JS lists
  around `:1167`, `:1303-1304`, `:1409-1410` — add
  `audit_dashboard/excess_column.js` and `audit_dashboard/forward_clock.js`.
- `tools/deploy_audit_files.py`: add the same two paths.
- Verify: `curl -fsS https://findtorontoevents.ca/audit/excess_column.js | head`
  returns JS (not 404) after deploy.

## Step 3 — Fix data integrity before trusting any number

1. **#748** resolver flat-close: in `audit_trail/universal_pick_resolver.py`,
   when `_priceless_close` applies, write the *last known* price and a
   `resolution_basis` field; never `exit_price = 0.0`.
2. Re-derive `recent_closed` / `dashboard_data.json` from clean bars.
3. Add `audit_dashboard/data/data_integrity_report.json` (Gate 0): counts of
   ghost rows, duplicates, flat closes, frozen cohorts. Fail the audit build if
   flat-close ratio > 0.5% or any cohort shows PF > 10 on n ≥ 20.

Exit: `GainerPredictor1hStrategy`-style PF 120 artifacts disappear from the
verdict payload.

## Step 4 — Fix the tracker TypeError (wrong file was patched)

`alpha_engine/data/forward_testing/forward_tracker.py:120-123` catches only
`ValueError`; mixed naive/aware timestamps raise `TypeError`. Either:

```python
except (ValueError, TypeError):
```
plus normalize with `_parse_ts` before subtraction (the pattern already used in
`tools/forward_tracker.py:210-224`). Add a regression test feeding one `Z` and
one naive timestamp.

## Step 5 — Populate the plan with real, pre-registered hypotheses

`state/forward_test/plan.json` on main has only 2 entries, so `load_plan()`
returns them verbatim and the registered scouts (`vwap-reversion-scout`,
`rs-breakout-scout`) never load. Add:

- `vwap-reversion-scout` (Gate 1 fields: entry/exit/universe/TF/params, trial
  count, benchmark, cost model, kill/promote rule);
- `rs-breakout-scout`;
- `etf-h103-dual-momentum` (ETF, benchmark SPY, monthly, 48-obs prior, forward
  target 152 windows).

Exit: `python -m tools.forward_tracker selftest` shows all intended strategies
loaded, not 2.

## Step 6 — Turn on the ledger sync (the missing cron)

Create `.github/workflows/forward-ledger-sync.yml` (the version on the closed
branch `wired-in/buffy-2026-11-15` is a good base):

- `schedule: cron '37 5 * * *'` (daily), `workflow_dispatch`.
- Steps: fetch benchmark prices → run `tools/build_benchmark_prices.py` →
  append resolved picks to `state/forward_test/ledger.jsonl` →
  `python -m tools.forward_tracker sync` → `build_forward_clock.py` →
  `pick_excess.py` (net-of-cost) → commit sidecars under a single
  `dashboard-publish` concurrency group.
- This is the **only** writer of the ledger; give it its own concurrency group
  so the 236 other pushers can't race it.

Exit: `state/forward_test/ledger.jsonl` grows daily; `forward_clock.json`
`ledger_rows > 0`.

## Step 7 — Make `pick_excess` net-of-cost

`spec/pick_excess.py` reports **gross** excess (`:313`, `:319`). Subtract the
per-class round-trip cost from `excess_pp` before writing
`reports/pick_excess_returns.json`, and record `gross_pp` and `net_pp`
separately. At 12 bps RT, +0.238pp → ≈+0.118pp and −0.795pp → ≈−0.915pp.

## Step 8 — Real trial accounting + DSR/PBO

- Add `state/forward_test/trial_count.json`; increment on every evaluated
  parameter set/symbol/TF (including abandoned sweeps).
- Compute DSR against that count. PBO currently prints `N/A` because
  `n_strategies=2 < 5` — that is a **Gate 3 fail**, not a pass. Add enough
  registered variants (≥ 5) that PBO is computable.

## Step 9 — Publish to `/audit`

See `06_AUDIT_PUBLISH_CONTRACT.md`. Minimum: the `template.html` columns
"Excess vs Bench", "Forward n", "Gate status", "CI(low,high)" bound to the
sidecars, plus the forward-clock panel.

## Verification checklist

```bash
git grep -n "excess_column.js\|forward_clock.js" origin/main -- audit_dashboard/template.html
git cat-file -e origin/main:audit_dashboard/data/benchmark_prices.json && echo OK
python -m tools.forward_tracker selftest        # all strategies load, 21/21
gh run list --workflow=forward-ledger-sync.yml --limit 3   # green, daily
curl -fsS https://findtorontoevents.ca/audit/forward_clock.js >/dev/null && echo LIVE
```
