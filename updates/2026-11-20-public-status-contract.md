# Machine-readable public status contract (2026-11-20)

**Scope:** `tools/write_public_status.py` (new),
`tests/test_write_public_status.py` (new), `.github/workflows/audit3-ledger.yml`.

## Why

Answering "is the book publishing, how fresh is it, is anything promoted, and why
not?" meant fetching a 45 KB ledger plus a page sidecar and re-deriving three
fields. Monitoring should be one small fetch with a stable schema.

## What

`tools/write_public_status.py` writes
`audit_dashboard/data/audit3_public_status.json`, deployed as
**`/audit3/status.json`**:

```json
{"schema":"audit3.public_status.v1","generated_at":"…","ledger_generated_at":"…",
 "age_hours":0.82,"stale":false,
 "coverage":{"mode":"canonical","scored":8769,"total":16341,"valid":8769,
             "valid_basis":"canonical_kept_rows"},
 "verdicts":{"proven":0,"candidate":0,"weak":59,"kill":8},
 "persistence":{"on":true,"churn_flipped":0,"churn_tracked":444},
 "denials":{"n":55,"by_class":{"CRYPTO":33,"COMMODITY":8}},
 "forward":{"rows":430,"enforced":true,"eligible_pods":0,
            "blocked":[{"hypothesis":"H-119","reason":"net PF CI-LB …"}]}}
```

`stale` is `true` past 12h or when `generated_at` is missing (never crashes).

## Verification

- `pytest tests/test_write_public_status.py -q` → **4 passed** (contract fields +
  freshness, stale threshold, missing timestamp, sidecar reason override).
- Live build against the 03:56Z ledger: `stale=False scored=8769
  forward_rows=430`, verdicts `0/0/59/8`.
- Workflow YAML validates (12 steps); the file deploys with `/audit3`.
