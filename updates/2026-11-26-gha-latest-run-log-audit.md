# Latest-run log audit — 303 workflows, 47 green-but-erroring (2026-11-26)

## Answer to "validate every workflow and its latest run"

Done for **303 of 386** registered workflows. The remaining 83 break down as:

| Why not audited | Count |
|---|---|
| latest run still **in progress** when the audit ran (peer dispatch wave) | 68 |
| no run on record (never executed) | 15 |
| log expired / gone (`HTTP 410`) | 2 |

Re-run `python3 tools/gha_latest_run_log_audit.py --resume` to pick up the in-progress ones once they finish — `--resume` reuses `reports/latest_run_logs/` and never refetches what it already has.

## Results

| Verdict | Workflows |
|---|---|
| **ERRORS in log** | **63** |
| WARNINGS only | 74 |
| SUSPICIOUS only | 23 |
| CLEAN | 143 |

**47 of those runs concluded `success` while their log contains error lines.**
8 concluded `success` while emitting `##[error]` annotations. Only 6 concluded `failure`.

A green tick is not evidence the work happened.

### Error classes across all audited runs

| Lines | Class |
|---|---|
| 1,859 | `ERROR` line |
| 284 | `HTTP Error 4xx` |
| 30 | `git fatal` |
| 27 | missing file |
| 24 | `##[error]` annotation |
| 8 | python traceback |

## Four distinct defects, not one

### 1. Symbols that do not exist are requested every run — and reported as success
`picks-now-refresh.yml` logs **1,427 errors** in a single successful run:

```
[ERROR] HTTP Error 404: {"quoteSummary":{"result":null,"error":{"code":"Not Found"...
[ERROR] $ADA: No data found, symbol may be delisted
```

`$ADA` is not a Yahoo symbol (it needs `ADA-USD`). This is the literal
"symbol not found" class: the equity/crypto universe contains invalid tickers and
the workflow treats every miss as a warning, so the run stays green and the picks
are silently thinner than reported. `battleground-mass-backtest.yml` is the same
shape — **312 × `ERROR: No Strategy class found`** across 869 directories, run still
green.

### 2. `git push` fails with 403 and the workflow still reports success
**14 workflows** hit `fatal: unable to access '…': The requested URL returned
error: 403`. Nine of them still conclude `success`, so the data they generated is
**never committed** — silent data loss:

`alpha-engine-etf`, `alpha-equity-breakout`, `claude-gainer-ml-live`,
`gha-queue-audit`, `macd-rsi-m048-shadow-daily`, `ml-battleground-retrain`,
`peer-claim-verification`, `quan-engine-live`, `rsi5070-forward-snapshot`,
`self_optimizing_trading`, `verified-pilot-daily`, `weekly-strategy-scorecard`,
`cross-aggregator`, `baby-strat-forward-paper`.

Not a missing-permission bug in most cases: `quan-engine-live.yml` declares
`permissions: contents: write` and still gets 403. Only 7 of the 236 pushing
workflows lack `contents: write`. The common factor is **236 workflows pushing to
`main`** — GitHub's git-push abuse detection answers 403 under that concurrency,
and `safe_push.sh` exhausts its retries ("ERROR: All 5 push attempts failed") and
the step swallows it. This is the same contended-main problem behind the
`weekly-scorecard` and `pod-h201` failures fixed earlier, but at fleet scale.

Fixing it properly means fewer pushes: batch writers, or one collector job that
commits for everyone.

### 3. Errors that are deliberately swallowed
`continue-on-error: true` appears in **71 workflows**, `|| echo` / `|| true` in
**245**. That is why a broken step produces a green run. Some are legitimate
(best-effort side channels); the ones above are not.

### 4. A masking rule is redacting digits in ordinary log lines
`etf-bond-scanner.yml` logs `2026***11***26 03:40:24` — the date has been mangled
by a masking rule that redacts digit runs. During an incident that log is
unusable, and it is the same policy that a peer flagged via `masking-policy-lint`.

## What is *not* a defect

- **Binance 451**: `HTTP Error 451` on `api.binance.com` is a geo-block of the
  runner's egress IP, confirmed independently by HERMES. It inflates error counts
  in `portfolio-tracker`, `conviction-picks`, `asterdex-paper-trading` and the
  `backfill-features` Binance mirrors. Do not "fix" the code for this.
- **NKLA**: genuinely delisted from Yahoo; the universe should drop it, but it is
  a data-curation issue, not a lookup bug.

## Tooling

| Tool | Purpose |
|---|---|
| `tools/gha_workflow_run_matrix.py` | has each workflow ever run? (real run history, one checkbox per workflow) |
| `tools/gha_latest_run_log_audit.py` | download each latest log, count errors / warnings / suspicious output, keep samples, `--resume` across rate limits |
| `tools/gha_act_batch.py` | execute workflows locally in a container, separating `FAIL` from `BLOCKED_ENV` |

Harness notes that cost hours and are now encoded in the tools:

- `catthehacker/ubuntu:act-latest` is amd64-only; on an aarch64 host every
  container exits 255 the moment a step runs. Needs a native image
  (`gha-runner:arm64`).
- that image needs `nodejs` (else every `uses:` action dies with
  `exec: node: not found`) and `PIP_BREAK_SYSTEM_PACKAGES=1` (PEP 668).
- act's `actions/setup-python` ships an interpreter without `ssl`, so pip cannot
  reach PyPI inside act. That is a harness limit, not a workflow defect — it is
  why 18 of 26 local runs land in `BLOCKED_ENV` rather than `FAIL`.
- `GITHUB_REPOSITORY` must be passed to act or `actions/checkout` fails with
  "Invalid repository '/local/path'".
