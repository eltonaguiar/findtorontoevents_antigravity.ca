# GHA validation ledger — who checked what, and how

**Question:** has every workflow on the repo been validated and its log checked?
**Answer: no single agent has done every workflow's raw log.** Four different lenses
exist, each covering a different slice, and they agree on the important finding:
*a `success` conclusion does not mean the run was clean.*

Last updated 2026-11-26 ~05:15Z.

## Lenses, by owner and method

| Owner | Method | Coverage | Findings |
|---|---|---|---|
| freebuff-deepseek-v4-flash (this ledger) | **raw latest run log** downloaded and scanned for errors / warnings / suspicious output (`tools/gha_latest_run_log_audit.py --resume`) | **304 of 386** workflows | 72 with errors, 76 warnings-only, 24 suspicious, 132 clean; **54 concluded `success` while the log contains errors** |
| copilot-cli-deepseek-flash | **check-run annotations** for every job of every run in a 1.2 h window (`/check-runs/{job_id}/annotations`) | 200 runs / 228 jobs / 123 annotations | warning 88 / failure 28 / notice 7; `success` + `failure` annotation on the same job is routine |
| copilot-cli-deepseek-flash | annotations, latest completed run per workflow | 123 workflows | 10 failure-annotations, 17 warnings, 5 notices, 98 clean |
| kilo-deepseek-flash | Actions **UI state query** (`is:failure`, `is:cancelled`, …) over Chrome DevTools — no API quota | all workflows, by state | 4 states clean; 20 `queued` are uncancellable zombies from 2026-11-11; `cancelled` was a real 10-minute timeout defect (fixed) |
| kilo-deepseek-flash | **static integrity**: YAML parse + actionlint + `act -l`/`act -n` | 383 files parse; 295 active, 5 disabled | 4 real `concurrency: queue` errors (dead config, removed); 2 timeout defects (realtime-challenge, DNA pipeline) |
| freebuff (earlier pass) | **local execution in `act`** with a native arm64 image | 26 of 175 never-run workflows | 5 PASS, 18 BLOCKED_ENV (act's setup-python has no `ssl`), 3 real FAIL |

## What is still not validated

| Gap | Count | Why |
|---|---|---|
| latest run still **in progress** at audit time | 65 | huge dispatch wave; `--resume` closes these |
| **never executed at all** | 15 | nothing to audit — the highest-risk group |
| log expired / gone (`HTTP 410`) | 2 | cannot be recovered from the API |

304 + 65 + 15 + 2 = 386.

## Where the lenses agree (high confidence)

1. **`success` ≠ clean.** Confirmed independently: mine (54 workflows with error
   lines under a green conclusion), copilot (DB Freshness Guardian exits 2 and
   renders green via `continue-on-error`; Outcome Resolver green while resolving
   0 picks).
2. **Silent commit failure.** I found 14 workflows with `git push` 403, 9 still
   green. Kilo independently found pushes hanging mid-push because the repo takes
   commits every 1-2 minutes, and moved its own fixes to the contents API.
3. **Timeouts misread as cancellations.** Kilo found `realtime-challenge` and
   `dna_strategy_pipeline` killed at their caps; copilot found `portfolio-tracker`
   3/3 cancelled at a 10-minute cap.

## Where the lenses disagree / need care

- **Binance 451 is not a symbol bug.** Mine and HERMES' findings agree: it is an
  egress geo-block. Any count that calls these "symbol failures" is mislabelling.
- **A failure on an older commit is not open work.** `gh run rerun` reuses the
  original commit, so a red run whose `head_sha` is behind main cannot be fixed by
  rerunning it.
- **Annotation counts and log-line counts are not comparable.** One `::warning::`
  annotation can correspond to hundreds of log lines, and most log lines are not
  annotated at all. Do not add them together.

## Defects fixed from this body of work

| Defect | Fix |
|---|---|
| `$SQ`/`$ADA`/`$BTC` and 6 dead tickers requested every run — 1,427 error lines in one green run | `#1175` (94cf1ae1): strip `$`, `KNOWN_DELISTED`, `CRYPTO_BASES`, silence the yfinance logger, 7 unit tests |
| `concurrency: queue` dead config in 4 workflows | kilo (removed) |
| `realtime-challenge` and `dna_strategy_pipeline` killed at their timeout cap | kilo (caps raised) |
| `mirror-site` burning 50 min on a quarantine tree | `#1169` + `#1171` (excludes) |
| 4 push-triggered workflows failing on every merge | `#1162`, `#1164`, `#1166` |
