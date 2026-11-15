# GitHub Actions triage — four red workflows, all root-caused to config bugs

**Date:** 2026-11-15
**Scope:** scheduled workflows on `main` whose latest run is `failure` and which
touch market data / financial predictions.
**Method:** `gh run list` latest-per-workflow scan, then `gh run view --log-failed`
on each, then read the invoked code path before changing anything.

## What was broken

Four workflows had no successful run after their latest failure:

| Workflow | Run | Symptom in log |
|---|---|---|
| QA Market Validation | 43688541491 | `fetch_quote(<ticker>): ALL 7 sources failed` for every equity ticker, then `exit code 1` |
| rsi5070 Forward-Test Snapshot (Daily) | 43688176979 | `failed to push some refs` ×10 → `ERROR: All push attempts failed` |
| Operator Review — Manual Candidates daily snapshot | 43688791845 | `failed to push some refs` ×5 → `ERROR: Push failed after 5 attempts` |
| Sports endpoint smoke + Playwright | 43689346545 | `ERROR: Playwright does not support chromium on ubuntu26.04-x64` |

### Root causes

1. **QA Market Validation — no quote-chain credentials.**
   `alpha_engine/equity_price_failover.py` documents a 7-adapter chain
   (Stooq, Finnhub, Tiingo, Twelve Data, Alpha Vantage, FMP, yfinance). Adapters
   2–6 `return None` immediately when their env var is unset. The workflow passed
   only DB passwords, so in Actions the chain was really **Stooq + yfinance** —
   and the module's own docstring says the Stooq endpoint and yfinance are both
   unreliable from GitHub runners. `ALL 7 sources failed` is literally
   `len(_QUOTE_CHAIN)`, i.e. it tried seven adapters but only two had any chance.
   Net effect: the gate that is supposed to stop unvalidated PnL from reaching the
   dashboard failed on *infrastructure*, not on bad PnL — and failed every hour.

2. **rsi5070 + operator-review — retry loops that never rebase.**
   Both commit a small JSON and then loop `git push`. On a non-fast-forward
   rejection, every subsequent attempt sends the identical ref update, so it
   cannot ever succeed. The shared `dashboard-publish` concurrency group does not
   help: other publishers (audit-dashboard and push-triggered jobs) advance `main`
   outside the group. Result: the daily forward-test snapshot and the operator
   review silently stopped updating `main`, which is a *data freshness* failure,
   not a CI annoyance.

3. **Sports smoke — runner image drift.**
   `runs-on: ${{ vars.ACTIONS_RUNNER_LABEL || 'ubuntu-latest' }}`; `ubuntu-latest`
   now resolves to 26.04, where Playwright refuses to install chromium. The job
   died on the install step and never executed a single test, so the hourly
   production-drift guard has been dark.

## What changed

- `.github/workflows/qa-market-validation.yml` — pass
  `FINNHUB_API_KEY`/`FINNHUB`, `TIINGO_API_KEY`, `TWELVE_DATA_API_KEY`,
  `ALPHA_VANTAGE_API_KEY`, `FMP_API_KEY` into the `Run QA ledger` step so the
  documented failover chain actually has sources. **No assertion or exit-code
  behaviour was weakened** — the gate still fails on any CRITICAL flag.
- `.github/workflows/rsi5070-forward-snapshot.yml` — on a non-fast-forward
  rejection, `git fetch origin main && git rebase origin/main`, then retry
  immediately (with `rebase --abort` + timed-retry fallback if the rebase itself
  fails). Permanent rejections still abort on the first attempt.
- `.github/workflows/operator-review-today.yml` — same rebase-before-retry logic.
- `.github/workflows/sports-smoke-and-e2e.yml` — smoke job pinned to
  `ubuntu-24.04` (var override still honoured) so Playwright can install.
  `deploy-guard` left on `ubuntu-latest`; it only uses `curl` + `sha256sum`.

Rebase safety: both snapshot jobs stage exactly one/two JSON files, so a rebase
onto a moved `main` cannot conflict by construction.

## Verification

- YAML structure parsed with `yaml.safe_load` for all four files; every `run: |`
  script extracted and checked with `bash -n` (see the command in the commit).
- Confirmed the failure strings each new branch matches really are what git
  emitted in the failing runs (`non-fast-forward` / `fetch first` / `[rejected]`
  / `behind its remote`) versus the existing permanent-rejection patterns.
- Confirmed `_QUOTE_CHAIN` length is 7 and that adapters 2–6 gate on exactly the
  env var names now wired in.
- Post-merge check (must be done by a human or the next cron):
  `gh run list --workflow=qa-market-validation.yml --limit 3` should show a green
  run, and `git log origin/main --oneline -3` should show new
  `chore(rsi5070-snapshot)` / `chore(operator-review)` commits.

## Known limitations / follow-ups

- **Measured secret audit** (`gh secret list`, 2026-11-15): the repo has
  `FINNHUB_API_KEY`, `FINNHUB`, `ALPHA_VANTAGE_API_KEY`, `FMP_API_KEY`.
  It does **not** have `TIINGO_API_KEY` or `TWELVE_DATA_API_KEY`, so adapters 3
  and 4 still no-op. Before this fix the effective chain was 2 of 7
  (Stooq + yfinance); after it, 5 of 7 (Stooq, Finnhub, Alpha Vantage, FMP,
  yfinance). Adding the two missing secrets raises it to 7 of 7.
  If the remaining sources are unavailable the gate still fails honestly — the
  fix is to add the secret, never to relax the gate.
- Stooq's anonymous endpoint and yfinance remain the only keyless paths; a
  runner-IP block on both is still possible. Monitor the first green run.
- `Verified pilot daily` and `Backup Restore Verification` appeared in the
  operator's failure list but have no runs in the last 200 on `main` — they are
  likely dispatch-only or on another branch. Not diagnosed here.
- `Feed Health Check` was queried but has no failed step output; it is not in the
  latest-run failure set.

## Post-fix dispatch result (proof the QA fix works)

Dispatched `QA Market Validation` on the fix branch, run **43690513115**:

- The step log confirms the keys reached the process — `ALPHA_VANTAGE_API_KEY: ***`,
  `FMP_API_KEY: ***`, while `TIINGO_API_KEY:` and `TWELVE_DATA_API_KEY:` were empty,
  matching the secret audit above.
- Result changed from *infrastructure failure* to *real validation*: **185 picks,
  `unpriced=0` in all six classes** (BOND 54, COMMODITY 3, EQUITY 31, ETF 74,
  FOREX 23, plus crypto). Before the fix every equity ticker logged
  `ALL 7 sources failed`.
- It still exits 1 — correctly — on 5 flags / **4 critical**:
  `FOREX mismatch=3`, `COMMODITY mismatch=1`, `EQUITY blank_tp/sl=1`.

That is the gate working as designed; it does **not** mean the CI fix failed.

### Honest note on naming those picks

An offline replay (`python3 tools/qa_ledger.py`) **cannot complete locally**: it
performs up to `_MAX_EXT_CHECKS=250` live cross-checks, each with a 5s-per-adapter
chain, and `timeout 180` killed it (`exit 124`, zero output).

An earlier attempt appeared to name symbols (`AUDJPY=X` repeated with a constant
0.63pp diff; `BLANK_TP_SL` on GOOGL/TTWO/PLTR/MU/NFLX). Those came from the
**pre-existing** `audit_dashboard/data/qa_market_validation.json` (generated
02:03:59, **4390** picks, 500 flags) — a different generation than the CI run's
185 picks — because the replay wrote nothing and the stale file was parsed. They
must not be attributed to run 43690513115, and that payload is not the current one.

If that older report is representative, the FOREX pattern matters: an identical
0.63pp gap on every AUDJPY=X row, despite different published values, is the
signature of a **time lag** between the published PnL snapshot and the live
external quote — not corrupt PnL. With `TOL_PP["FOREX"]=0.5`, a 0.63pp intraday
move trips the gate by itself. That is a gate-calibration question (tolerance vs.
payload refresh cadence), **NOT MEASURED** on the current payload.

## Unrelated blocker found while triaging

`branch-large-file-dup-guard` (`.github/workflows/branch-large-file-dup-guard.yml`)
runs on every non-main branch push with
`concurrency: group: branch-large-file-dup-guard, cancel-in-progress: true`.
Concurrent branches therefore cancel each other: on the #785 run the *Checkout*
step itself was `cancelled`, so steps 3–5 (fetch, scan, alert) were `skipped`
while step 6 "Enforce fail-on-findings policy" still returned `success`. A
cancelled guard is not a valid signal on either PR. Not fixed here — it is a
repo-bloat guard, not a data-pipeline job.

## Branch-rewrite note

While this work was in progress another process merged `main` into the fix branch
and rewrote it ("resolve merge conflicts in workflows for PR 786"). Verified after
the rewrite that all four fixes are still present in the remote tree
(`FINNHUB_API_KEY` x2, `TIINGO_API_KEY`, both rebase blocks, `ubuntu-24.04`), but
this documentation was reverted to its pre-appendix state. This appendix was
re-applied on top of the current remote head, without touching the working tree,
because other agents were editing files concurrently.
