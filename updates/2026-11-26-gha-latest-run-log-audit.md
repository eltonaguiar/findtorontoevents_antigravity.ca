# Latest-run log audit — green is not clean (2026-11-26)

## What was asked

Validate every workflow *and its latest run*, checking logs for warnings, errors
and anything odd — not just the pass/fail conclusion.

## Tooling added

| Tool | Answers |
|---|---|
| `tools/gha_workflow_run_matrix.py` | has this workflow ever run, and did it work? (real run history, one checkbox per workflow) |
| `tools/gha_act_batch.py` | run it locally in a container; separates `FAIL` (ours) from `BLOCKED_ENV` (secret/DB/FTP we cannot supply) |
| `tools/gha_latest_run_log_audit.py` | **download the latest run's log and count errors / warnings / suspicious output** |

`gha_latest_run_log_audit.py --resume` reuses logs already saved under
`reports/latest_run_logs/`, so a rate-limited run can be continued without
re-fetching what it already has.

Two harness gotchas cost real time and are now documented in the code:

- `catthehacker/ubuntu:act-latest` is **amd64-only**. On this aarch64 host every
  container exits 255 the instant a step runs ("container … is not running"),
  even for `echo hi`. A native `gha-runner:arm64` image is required.
- that image must contain `nodejs`, or every `uses:` action dies with
  `exec: node: executable file not found in $PATH` (exitcode 127), and
  `PIP_BREAK_SYSTEM_PACKAGES=1`, or pip refuses to install (PEP 668).

## Findings so far (73 of 369 runs with a log audited)

| Verdict | Workflows |
|---|---|
| ERRORS in log | **26** |
| WARNINGS only | 20 |
| SUSPICIOUS only | 6 |
| CLEAN | 21 |

**The headline: 26 workflows whose run conclusion is `success` still contain
error lines in their logs.** A green tick does not mean the work happened.

### Error classes, by line count

| Count | Class |
|---|---|
| 56 | `HTTP Error 4xx` |
| 28 | `ERROR` line |
| 25 | missing file |
| 11 | `##[error]` annotation |
| 4 | python traceback |
| 2 | git fatal |
| 1 | missing python module |
| 1 | missing binary |

### Worst offenders (all `success`)

| Errors | Workflow | First error |
|---|---|---|
| 38 | `backfill-features.yml` | `[WARN] All Binance mirrors failed for RENDERUSDT: HTTP Error 4xx` |
| 20 | `cross-aggregator.yml` | `[WARN] Could not load /home/runner/work/...` (missing input file) |
| 10 | `asterdex-paper-trading.yml` | `[ERROR] Klines fetch failed for BTCUSDT` |
| 10 | `etf-bond-scanner.yml` | see masking bug below |
| 8 | `alpha-engine-daily-picks.yml` | `[ERROR] yfinance:` |
| 6 | `audit-impact-tracker.yml` | `[WARN] Could not load strategy_performanc…` |
| 4 | `baby-strat-forward-paper.yml` | python traceback + missing module |
| 3 | `ai-model-portfolios-daily.yml` | `Traceback (most recent call last)` |

### Two distinct root causes, not one

1. **Binance 451 geo-block** (matches HERMES' independent finding): the
   `HTTP Error 4xx` mass is an egress-IP block on `api.binance.com`, not a data
   or symbol defect. It inflates "failure" counts in every crypto workflow.
2. **Missing input files carried as warnings**: `cross-aggregator` and
   `audit-impact-tracker` cannot load the artefact they aggregate and continue
   anyway, so the run is green and the output is silently incomplete. That is
   the same class as the NaN payloads fixed earlier — a producer that fails
   quietly.

### A masking bug worth its own ticket

`etf-bond-scanner.yml` logs `2026***11***26 03:40:24` — the timestamp has been
mangled to `2026***11***26` by a masking rule that redacts digit runs. A masker
is eating ordinary numbers inside log lines, which is exactly the kind of thing
that makes a log worthless during an incident. It also explains the
`masking-policy-lint` failure a peer reported on `ci/2026-11-25-gha-digest`.

## Still open

- 296 workflows remain to be audited; the GitHub REST budget (5,000/h) ran out
  at 96 workflows because the matrix sweep itself spends 386 calls. Re-run
  `python3 tools/gha_latest_run_log_audit.py --resume` once the hourly budget
  resets, or after the matrix has been cached.
- 175 of 386 workflows have **never run at all**, so they have no log to audit;
  they are tracked in `reports/GHA_PER_WORKFLOW_RUN_TODOS.md`.
