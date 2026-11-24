# Excluded-summary checker + pre-wiring baseline (Block 61)

**Date:** 2026-11-24
**Branch:** `blk61-excluded-summary-checker`
**Scope:** read-only operator tool, one appended doc section, one added assertion.

## Why the checker exists

`coverage.excluded_summary` in the audit3 ledger is built from the
`_excluded_cohort_rows` block the dashboard generator publishes in
`dashboard_data.json` (Blocks 58/59). Two different failures look identical
from the outside:

| State | Payload | Ledger | Looks like |
|---|---|---|---|
| Wiring missing | no `_excluded_cohort_rows` key | `excluded_summary: null` or zeros | `total: 0` |
| Measurement not fed | key present, empty cohorts | `total: 0`, `by_class: {}` | `total: 0` |

`total: 0` is therefore **indistinguishable from the un-wired default** and must
never be read as "no excluded rows exist". Before this tool, telling the two
apart meant hand-reading the payload and the ledger; Block 60 spent a whole
recon round on exactly that.

## How to run it

```sh
# against the live payload (gitignored, FTP-deployed) and the tracked ledger
python3 tools/check_excluded_summary.py \
    --payload https://findtorontoevents.ca/audit/data/dashboard_data.json \
    --ledger audit_dashboard/data/audit3_ledger.json

# against a downloaded copy, with a stricter threshold
python3 tools/check_excluded_summary.py \
    --payload /tmp/dashboard_data.json --expect-min 100
```

Interface:

- `--payload <path-or-url>` (required) — dashboard payload; an `http(s)://`
  value is fetched with a 30s timeout and a `User-Agent`, otherwise read as a
  local file.
- `--ledger <path-or-url>` (optional) — audit3 ledger; adds
  `coverage.excluded_summary.total`, `by_class`, `by_reason`.
- `--expect-min <int>` (default `1`) — minimum `total` considered fed.

Exit semantics: **0 only if** the payload carries `_excluded_cohort_rows`,
`total >= --expect-min`, and `by_class` is non-empty. Otherwise **1**, with a
one-line reason on stderr. Expected conditions (missing file, HTTP error,
malformed JSON, absent key) print a message, never a traceback.

This is a manual operator tool. **It is deliberately not wired into any
workflow** — a CI gate would fail every hour until the next dashboard build
lands.

## The pre-wiring baseline (2026-11-24T01:29Z)

- `coverage.excluded_summary` = `total: 0`, `by_class: {}`, all `by_reason`
  zero, `overlap: false`.
- Deployed payload `metadata.repo_sha = 325a7d8f`, **no**
  `_excluded_cohort_rows` key.
- `git merge-base --is-ancestor 188759ab 325a7d8f` = **false** → the run was
  pre-wiring.
- The same ledger's `coverage.excluded_cohorts` already reports **6,025
  integrity-excluded + 9,274 auto-expired** rows (overlapping, not a
  partition). Those are the counts `excluded_summary` will eventually break
  down by class and reason.

## What flips the label

A run whose payload has a `repo_sha` **descending from `188759ab`**, carries
`_excluded_cohort_rows`, and yields `total > 0` with a non-empty real-class
`by_class`.

## The gitignored / FTP finding (do not re-derive)

`audit_dashboard/data/dashboard_data.json` is **gitignored**
([`.gitignore:222`](../.gitignore:222), the 2026-05-22 repo-bloat fix) and
**FTP-deployed**. A payload refresh therefore never appears as a git commit, so
"has the build landed?" can never be answered with `git log`. The only tracked
observation surfaces are:

1. the audit3 ledger (`audit_dashboard/data/audit3_ledger.json`), and
2. sibling `audit_dashboard/data/*.json` sidecars.

The deployed payload itself must be read from the live URL
(`https://findtorontoevents.ca/audit/data/dashboard_data.json`) or a downloaded
copy.

## Verification

- `tests/test_check_excluded_summary.py`: 9 tests, proven RED (all 9 fail with
  the tool absent) then GREEN (9 passed).
- `tests/test_coverage_limits_doc.py`: new
  `test_observation_log_records_the_zero_total_trap`, proven RED against the
  `origin/main` doc then GREEN (8 passed).
- `COVERAGE_LIMITS.md` change is append-only: `git diff --numstat` = 29
  added, 0 removed.
