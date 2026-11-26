# GitHub Actions usage metrics → cost-weighted triage (2026-11-26)

## What was missing

The per-workflow audit (`reports/GHA_LATEST_RUN_LOG_AUDIT.md`) ranks 386 workflows by
**severity** — how many error lines its last log carried. It says nothing about **cost**.
That is the wrong order for deciding what to fix first:

- `audit-dashboard.yml` is the single most expensive workflow (28,689 billed minutes) *and*
  logs 40 errors per run — it deserves to be first on both axes.
- `discord-bot.yml` is billed 35,340 minutes across only 101 runs (≈350 min/run) and had **no
  audited log** — invisible in a severity-only list, because "no log" scores zero.
- 72 workflows log errors while **35 of them conclude `success`**. A severity list cannot
  distinguish "red because it crashed" from "green but printing errors" — the second group is
  the one that silently rots.

There was also no answer anywhere to "how many workflows are there to look into?" — the
inventory (381 files), the audit (386 entries, 82 with no log) and the usage export (380
billed workflows) disagreed, and nobody had reconciled them.

## What was added

`tools/gha_usage_triage.py` joins the two GitHub Actions **usage exports** (job-level and
workflow-level CSV) against three local sources and emits `reports/GHA_USAGE_TRIAGE.{md,json}`:

| Source | Used for |
|--------|----------|
| usage export, job-level | billed minutes per job → "top job" for each workflow |
| usage export, workflow-level | billed minutes + run counts per workflow |
| `.github/workflows/` | which workflow files actually exist today |
| `reports/GHA_PER_WORKFLOW_RUN_MATRIX.json` | `runs_seen`, latest conclusion, class |
| `reports/GHA_LATEST_RUN_LOG_AUDIT.json` | error/warning/suspicious counts from the last log |

Each workflow lands in exactly one bucket: `ERRORS`, `SUSPICIOUS`, `NEVER_RAN`,
`AUDIT_INCOMPLETE`, `DELETED`, `RENAMED`, `DISABLED`, `WARN_ONLY`, `UNAUDITED`, `CLEAN`,
`MANAGED`. Priority is severity-weight + billed minutes, so a broken expensive workflow
outranks a broken cheap one, and a clean expensive one never outranks a broken one.

Two classification traps are handled explicitly, because both inflate the work count:

- **`MANAGED`** — `pages-build-deployment` and `update-graph` are created by GitHub and have
  no file in the repo. They are billed, they are not ours, and they must not be counted as
  broken workflows.
- **`RENAMED`** — a billed name whose file was renamed keeps the same *leading token*
  (`daily-price-refresh` → `daily-prices-yf-refresh`, `cross-db-consistency` →
  `cross-db-audit`, `live_trading_canada_free` → `live_trading_canada`). A fuzzy match alone
  wrongly paired `mermaid-test-deploy` with `backtest-and-deploy` because both contain
  "deploy"; requiring the shared leading token correctly classifies it as `DELETED`.
  A `.disabled` successor is reported as `DISABLED`, not as missing.

`AUDIT_INCOMPLETE` exists because "no log to read" and "never ran" are different problems: the
first needs a re-audit (`python3 tools/gha_latest_run_log_audit.py --resume`), the second needs
a dispatch. The 58 workflows in it account for 219,558 billed minutes — the largest single
block of unmeasured spend.

## Numbers (export window as provided)

- 381 workflow files in the repo; 380 workflows billed; 560,627 billed minutes over 104,981 runs.
- **191 workflows need investigation**: 72 `ERRORS`, 56 `SUSPICIOUS`, 58 `AUDIT_INCOMPLETE`,
  4 `NEVER_RAN`, 1 `DELETED`. (The first pass said 259 — the difference was 58 workflows whose
  billed name had been renamed plus 2 GitHub-managed ones, i.e. false work.)
- Cost is concentrated: top 10 workflows = 41.8% of billed minutes, top 25 = 64.4%,
  top 50 = 79.5%.
- `ERRORS` holds 130,377 minutes and 21,359 runs; 35 of those 72 conclude `success`, so the
  job passes while printing errors every run.

## How it was verified

- `python3 -m pytest tests/test_gha_usage_triage.py -q` → **7 passed**. The tests pin the
  leading-token rename rule, the false-positive case, `MANAGED`/`DISABLED`/`DELETED`
  separation, the `AUDIT_INCOMPLETE` vs `UNAUDITED` split, and an end-to-end join asserting
  bucket totals, the 191-style investigation count, and byte-identical output on re-run.
- Output is deterministic: re-running on the same inputs produced identical file hashes
  (`md5 70faf2fc…` for the report before the rename-rule fix; the post-fix report was also
  hash-stable across two runs).
- The join was cross-checked against the known headline defects: `picks-now-refresh.yml`
  resolves to `ERRORS` with 1,427 error lines in 1,261 billed minutes, and
  `battleground-mass-backtest.yml` to `ERRORS` with 312 `No Strategy class found` lines over
  106 minutes — both match the audit report, so the join loses nothing.

Reproduce with:

```bash
python3 tools/gha_usage_triage.py \
  --jobs-csv <job-export>.csv --workflows-csv <workflow-export>.csv \
  --out-md reports/GHA_USAGE_TRIAGE.md --out-json reports/GHA_USAGE_TRIAGE.json
```

The CSVs are not committed (they are account billing exports); only the derived report is.
