# realtime-challenge red runs (Binance HTTP 451) + superseded Actions-run cleanup

Date: 2026-11-26 · Owner: Buffy · Scope: `.github/workflows/realtime-challenge.yml`,
`tools/realtime_challenge.py`, Actions run history on `main` / `gh-pages`.

## 1. The run that was reported

[Run 45163680658](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/45163680658)
— workflow `realtime-challenge`, event `schedule`, branch `main`, created
2026-11-23T11:16Z, **conclusion: failure**. Job `cycle` (10 min timeout) failed on
step 4, "Mark open positions and open new slots"; step 5 ("Commit the ledger")
was skipped.

Job log, in order:

```
mark: no open positions
open: no market data (['market data unavailable: https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=5m&limit=200 (HTTP Error 451: )'])
##[error]Process completed with exit code 2.
```

So: `mark` did its job (no open positions), then `open` fetched all 8 symbols in
the universe, **every** request came back HTTP 451, `cmd_open()` printed
`open: no market data (...)` and returned **2**, and the step failed. The
workflow is green only when the venue answers.

**Cause.** HTTP 451 is `Unavailable For Legal Reasons`: Binance answers 451 to
cloud IP ranges it does not serve (this is the well-known GitHub-hosted-runner
block, not a credentials, symbol or code problem). It is also **intermittent by
runner**: the same workflow on the same commit has succeeded since — e.g. run
[45765709788](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/45765709788)
(schedule, 2026-11-26T06:04Z) and the dispatch at 09:16Z both succeeded — because
those jobs landed on a runner range Binance does serve. The strategy logic was
never wrong; the transport was.

## 2. Fix

`tools/realtime_challenge.py` — `klines()` now tries the primary API host first
and falls back to the venue's public market-data mirror, which publishes the
same klines for the same symbols and is not geo-restricted:

```python
API = "https://api.binance.com/api/v3"
API_MIRRORS = ("https://data-api.binance.vision/api/v3",)
_API_BASE = None   # first host that answered in this process
```

* Host order is `cached → api.binance.com → data-api.binance.vision`.
* The host that answered is cached, so the other 7 symbols do not re-pay a 451.
* When the mirror is used the log says so:
  `market data: https://data-api.binance.vision/api/v3 (primary https://api.binance.com/api/v3 unreachable)`.
* If **no** host answers, `RuntimeError("all market-data hosts failed: ...")` is
  raised and `cmd_open()` still returns 2, so a genuine outage is still red. The
  failure flag was not silenced, only the avoidable one was removed.
* **No pre-registered rule moved.** Universe, EMA/RSI filters, TP +0.60 %, SL
  −0.40 %, 60-minute time stop, 3 slots, 10 bp fee + 2 bp slippage are untouched —
  this is transport plumbing. A test asserts the frozen constants explicitly.

New tests: `tests/test_realtime_challenge_market_data.py` (4 tests) — 451 on the
primary falls through to the mirror and parses bars; the cached host is reused on
the next symbol; a total outage still raises; frozen constants unchanged.

## 3. Verification

| Check | Result |
|---|---|
| `python3 -m pytest tests/test_realtime_challenge_market_data.py -q` | `4 passed` |
| `python3 -c "py_compile ... tools/realtime_challenge.py"` | compiled |
| Live call through the real code (`klines`/`snapshot` on BTCUSDT) | 5 bars, last close 60948.01, `snapshot` fields populated, host `api.binance.com`, 0.2 s |

**Limit (stated, not hidden):** a 451 can only be reproduced from the blocked
runner range, so the fallback path itself is proven by the unit test, not by a
red-to-green replay on a hosted runner. The normal path is proven live above.

## 4. Queue cleanup — superseded failed runs deleted

Rule applied (operator's, and consistent with this repo's definition of a stale
failure): **delete a failed run only when the same workflow has a LATER
successful run on `main` or `gh-pages`.** Oldest-first, so the freshest failures
(the ones worth diagnosing) survive. Nothing queued or in-progress was touched;
no successful run was touched.

Inventory: every workflow (≈280) surveyed via the Actions API for its latest run
on `main`/`gh-pages`; failures older than a later success collected.

| | |
|---|---|
| Failed runs deleted | **2,664** |
| — on `main` | 2,631 |
| — on `gh-pages` (all `pages-build-deployment`) | 33 |
| Workflows touched | 163 |
| Deleted span | 2026-05-23T08:19Z … 2026-11-26T07:48Z |
| Delete API failures | 0 |

Largest clears: `Claude's Test - Portfolio Manager` 100, `ALPHA ENGINE - Dynamic
Runner` 100, `Feed Health Check` 100, `Market Beating System` 100, `Mercury 2
Signal Scanner` 100, `Mirror: findtorontoevents.ca ↔ torontoevent.net` 100,
`Outcome Resolver` 100, `realtime-challenge` 100, `robust-edge-miner` 100,
`Signal Tracking & Validation` 100. Full per-workflow counts:
`reports/gha_superseded_run_cleanup_2026-11-26.json`.

Verified after the sweep:

* `gh run list --branch gh-pages --status failure` → **empty** (was 33).
* `realtime-challenge` no longer appears in the `main` failure list; its latest
  run is a success.
* Residual `main` failures are all runs with **no later success** (see §5) — the
  rule was not violated to make the list look clean.

## 5. What is still red (not superseded — real backlog)

Latest run on `main` is a failure for these 8 workflows; each needs a real fix,
not a deletion:

| Workflow | Latest failure | Cause from the log |
|---|---|---|
| `Closed Picks Command` | 2026-11-26T08:24Z | `ERROR: Error: No module named 'signal_aggregator'` — broken import/module path |
| `Deploy Strategy Bundle` | 08:25Z | `AttributeError: 'list' object has no attribute 'values'` in the strategy validation script |
| `Edge stability refresh` | 08:25Z | `error: could not apply 5caf73f22b4... chore(edge-stability): daily refresh` → `push failed after 5 attempts` (rebase conflict on its own commit) |
| `Fast Stocks Competition` | 08:25Z | exit 2 from the scan step |
| `Clear Channel Command` | 08:26Z | exit 1 from the command step |
| `DB Sync: findtorontoevents.ca ↔ torontoevent.net` | 07:05Z | exit 1 in "Sync databases to torontoevent.net" |
| `Sign-Coherence Gate` | 04:38Z | **red by design**: `Sign-flip count regressed: 1 > 0 baseline` — the gate is reporting resolver corruption, not breaking |
| `Verification Tests` | 09:09Z | 5 Python test failures: `test_p1_gates_etf_tight_crypto_consensus` (3 × ETF gate env handling), `test_pf_registry_tournament_db::test_tournament_loader_transforms_db_rows` (`0 == 2`), `test_trust_tier_non_crypto_default_on::test_etf_banned_passes_by_default` |

Also noisy but not "failed": `realtime-challenge` and several other schedules
show long runs of `cancelled` (e.g. 12 in a row on 2026-11-26 morning); that is
the cancel cascade, not a data failure, and is out of scope here.

## 6. Stale test repaired while shepherding this PR

`CI Tests` on this PR failed one test unrelated to the change:

```
FAILED tests/test_pr_triage_2026_04_25_merge_success.py::Test391_CIStashFix::test_audit_dashboard_has_stash_before_retry_loop
AssertionError: expected 10-retry loop not found in audit-dashboard.yml
```

It fails on `main` too (reproduced locally on the branch base). Commit
`dfe299a66a70` deliberately cut the `audit-dashboard.yml` merge-retry loop from 10
to 3 attempts — "a merge that conflicts on attempt 1 conflicts identically on
attempt 10" — and left the test pinning the literal string
`for i in 1 2 3 4 5 6 7 8 9 10`.

The regression PR #391 actually guards is **order**: `git stash push` must be
parked before the merge-retry loop, or the pull trips over the working tree. The
test now asserts that order and matches the loop by pattern (any attempt count)
instead of a hard-coded 10, so a future retune cannot re-break it. No assertion
was dropped or relaxed: both the stash's presence and its ordering are still
checked.

`pytest tests/test_pr_triage_2026_04_25_merge_success.py -q` → **29 passed**.

## 7. Files

* `tools/realtime_challenge.py` — mirror fallback in `klines()`.
* `tests/test_realtime_challenge_market_data.py` — new regression tests.
* `reports/gha_superseded_run_cleanup_2026-11-26.json` — cleanup counts.
* this file.
