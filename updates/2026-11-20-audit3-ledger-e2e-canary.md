# End-to-end ledger canary (2026-11-20)

**Scope:** `tests/test_audit3_ledger_e2e.py` (new).

## Why

The 2026-11-19 outage (23:45–00:09) was three separate partial-merge defects, and
each one would have been caught by running the ledger **once** with the real CLI
flags. Unit tests exercised helpers; nothing exercised the command the workflow
runs.

## What

The test writes a 150-row synthetic `pipeline_data.json`, then runs:

```
python -m alpha_engine.audit3_tribunal \
  --picks <payload> --out <ledger> \
  --history <hist> --history-write --persistence-runs 2 \
  --prev-ledger <prev> --max-churn 0.30
```

and asserts:

- exit code 0 (catches argparse conflicts such as a duplicated `--history`);
- the report contract: `schema`, `coverage`, `classes`, `cells`,
  `verdict_churn`, `persistence`, `denylist_hits`, `selection_alpha`, `summary`;
- `coverage.scored_rows == summary.n_rows` (the denominator invariant);
- the persistence sidecar is written with schema `audit3.verdict_history.v1`.

The assertions are on the **contract**, not an exact row count, because the ledger
legitimately dedupes mirror/duplicate rows.

## Verification

`pytest tests/test_audit3_ledger_e2e.py -q` → **1 passed**. Runs in the normal CI
test job, so a merge that breaks the scheduled invocation fails at PR time.
