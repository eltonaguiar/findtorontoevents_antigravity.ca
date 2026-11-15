# 02 — Open Pull Requests

37 open PRs as of 2026-11-15. `mergeStateStatus` values below were fetched live
(`gh api .../pulls/<n>`); `UNKNOWN` in `gh pr list` is just the list endpoint not
computing mergeability — the API returns the real value.

## Priority A — merge now (green or trivially fixable, unblock red CI)

| PR | Title | State | Recommendation |
|----|-------|-------|----------------|
| **#713** | `fix(ci): backup-verify false failures + issue spam; speed up dup-guard` | **MERGEABLE / CLEAN** (+192/−24) | **MERGE FIRST.** This is the exact fix for the 43-issue flood: fetches `dashboard_data.json` from the live site instead of a gitignored path, skips the proxy when absent, removes it from `critical_files`, and makes issue creation idempotent (comments on an existing open issue). Has been open since **2026-10-04**. Merging it single-handedly stops the flood. |
| **#786** | `fix(ci): restore QA price validation, snapshot pushes, and sports smoke` | MERGEABLE / unstable (1 pending check: large-blob guard) | **MERGE.** Adds the 5 equity quote-chain secrets to QA, fetch+rebase before push-retry in the two snapshot jobs, and pins the sports smoke `smoke` job to `ubuntu-24.04`. Checks `smoke`, Gitleaks, masking-lint, secret-scan all pass. |

## Priority B — merge after a quick review (profitability measurement infra)

| PR | Title | State | Notes |
|----|-------|-------|-------|
| #785 | Restore audit page script tags + tracker horizon fix | MERGEABLE / unstable, 48 files | Brings `excess_column.js` / `forward_clock.js` script tags into `template.html`, fixes the naive/aware timestamp `TypeError` that left 3,500 forward rows NOT MEASURED (3,392 now measured), plus `tools/pick_excess.py`, `build_benchmark_prices.py`, `build_forward_clock.py`. This is the measurement layer the profitability verdict depends on. Review the WIRED_IN bundle but the code is wanted. |
| #760 | Fund walk-forward review fixes (FXAIX same-window CI) | MERGEABLE / CLEAN, 11 files | Corrects a claimed +0.5%/yr fund edge to "+0.066%/yr = the fee gap" and fixes the `cagr3` window bug that made momentum pairs identical for 19 years. Honest-research value; merge. |
| #759 | 95-fund durability audit / genuine zero-expense ETFs | research | Review; likely archive rather than merge unless the data files are wanted. |

## Priority C — security, but stale (verify before merge)

| PR | Title | State | Notes |
|----|-------|-------|-------|
| #761 | Rotated FTP credentials, no embedded password defaults, verified FTPS | MERGEABLE / unstable, 16 files | Good hardening, but open since **2026-10-23**. Secrets may have rotated again since. Re-verify the FTPS check passes against current creds before merging; do not merge blind (it touches all deploy entrypoints). |

## Priority D — docs / non-trading (close or fold into a docs PR)

These add job-search notes, weather content, or skills docs. They do not touch
the trading system and are 2+ weeks stale. Close or batch into one docs commit.

- #766 — ServiceNow/Salesforce jobs scan (Nov 2)
- #765 — kilo additional skills docs (Nov 2)
- #763 — sci-fi TV watchlist on `/weather/` (Nov 1)
- #762 — Huggle job scan (Oct 30)

## Priority E — conflicts / needs rebase

- **#758** `fix(ci): BTC evaluator daily drawdown` — **DIRTY** (merge conflict in
  `tools/crypto_published_strategies.py`, `audit_dashboard/data/published_strategy_gates.json`,
  tests). Rebase or close; do not merge as-is.

## Priority F — research / opt-in, backlog triage

Open 3–5 months, mostly research or opt-in sidecars. Decide explicitly:
archive, or close with a pointer, so they stop obscuring the real queue.

- #757 grok scorecard evidence cards · #756 DSR>1 + resolver batch-close ·
  #751 GHA health monitor (useful — consider extracting just the monitor) ·
  #750 Nemotron bond slope · #749 batch-close root cause · #747 opencode
  crypto money-ready (0 passes) · #746 KPI page spec (spec only) · #745 audit
  empty-state v2 · #744 blacklist enforcement in `save_active_picks` ·
  #736 FC/weather UI · #735 audit cache/live stats · #711 stale-tag defects ·
  #701 pick rationale through normalizers · #700 LLM/Discord loud-failure ·
  #696 Discord secret rotation · #667 forward-track cell selector ·
  #666 B1 backfill price guard · #665 stalled-producer detector ·
  #657 contract-test gate · #600/595 edge-hunt (0 regime-controlled edges) ·
  #581 model_portfolios page · #564/562 audit edge-hunt docs.

## Duplicate-work warning

Several PRs re-implement fixes already present elsewhere or already on main:
- #713 vs the manual backup-verify fix proposed in this folder — **merge #713,
  do not hand-roll a second fix.**
- #760 and #756 both touch resolver/DSR/batch-close logic. Reconcile before
  merging both.
