# 2026-10-22 Winner-Hunt Go-Live — Change Log & Verification

Date: 2026-10-22. Author: Zoo (directive G: "find the ultimate bugs … then point out
proven winning strategies … find a true set of winners per asset class … variety pack
mutual fund").

## What was broken

1. **Micro-hold / instant-synthetic-fill "ultimate bug"** — closed-pick rows with hold
   durations under 60 seconds (e.g. `STXUSDT` held 0.544 s) inflated P/L with phantom wins.
   Across 8 dashboard feeds: **956 rows < 60 s → +2200.9% phantom PnL, 584 phantom wins**,
   concentrated in the genome feed (`mega_mutation_*`, 955 rows).
2. **Timestamp-key gap** — `_pick_hold_duration_seconds` did not scan the `timestamp` key
   that genome rows use to stamp entry, so the gate initially accepted all genome micro-holds.

## What changed

- [`audit_trail/dashboard_generator.py`](../audit_trail/dashboard_generator.py):
  - added `_MIN_HOLD_SECONDS = 60`;
  - `_pick_hold_duration_seconds` now also reads `timestamp` and `created_at` as entry keys;
  - `_is_valid_resolved_pick` now rejects rows held below the floor.
- [`tests/test_dashboard_generator_micro_hold.py`](../tests/test_dashboard_generator_micro_hold.py):
  8 regression tests (incl. `test_genome_uses_timestamp_key_as_entry`).
- [`tools/per_asset_class_winners.py`](../tools/per_asset_class_winners.py) (new): per-class
  winners analyzer over the dashboard's own closed feeds (validity gate incl. micro-hold,
  classifier via `_coerce_asset_class`).
- Reports:
  - [`reports/2026-10-22-forward-data-quality-audit.md`](../reports/2026-10-22-forward-data-quality-audit.md)
    §3.5 documents the micro-hold finding/fix.
  - [`reports/2026-10-22-proven-winners-per-asset-class.md`](../reports/2026-10-22-proven-winners-per-asset-class.md)
    (new) + `.json` sidecar: the per-class proven-winner shortlist.
  - [`reports/2026-10-22-mutual-fund-multi-asset-audit.md`](../reports/2026-10-22-mutual-fund-multi-asset-audit.md)
    (new): audit of the existing variety-pack machinery.

## Verified

- Test suite: `test_dashboard_generator_placeholder_exit.py` + `test_dashboard_generator_micro_hold.py`
  → **26 passed** (no regressions).
- Runtime impact scan (post-fix): genome `ACCEPTED=98, REJECTED=987`, with **955 micro-hold
  rows rejected, +2200.9% phantom PnL excluded, 583 phantom wins excluded**.
- Per-class winners (4,351 validated rows): FOREX `forex_rsi2_mean_reversion`
  (n=37, WR 75.68%, PF 5.333); CRYPTO `mega_mutation_macd_rsi_m017` (n=15, WR 80%,
  PF 5.302); symbols `ENJUSDT` (n=10, WR 80%, PF 8.599), `ETCUSDT` (n=15, WR 60%,
  PF 2.88), `ONDOUSDT`, `WIFUSDT`, `JUPUSDT`, `CADJPY=X`, `AUDUSD=X`.
- Mutual-fund audit: multi-asset closed feeds have genuine holds (no micro-hold pollution)
  and no placeholder exits, but the non-crypto components are net-negative (FUTURES −9.52,
  EQUITY −8.77, ETF −3.60, PENNY_STOCK −21.35) and the active book (43 picks) is not yet
  forward-validated → not deployable as-is.

## Deployment status

- Feature branch `feat/audit-dashboard-go-live-20261022` → merged to `main` (`2b0a8440`).
- `audit-dashboard.yml` dispatch run `39870062310` was **cancelled** (known cancel-cascade
  on this workflow). The last successful deploy predates this merge. QA-5 (verify live
  `dashboard_data.json` / `index.html` against a deploy containing the fix) is pending a
  successful run of `main` head; the hourly cron (‑:10) and/or a fresh dispatch should pick
  it up. The fix is independently proven by the 26-test suite + runtime exclusion scan, so
  this is a deploy-verification step, not a correctness dependency.
