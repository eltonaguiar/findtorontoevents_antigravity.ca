# Smoke tests for the audit3 entry points (2026-11-20)

**Scope:** `tests/test_audit3_cli_smoke.py` (new).

## Why

The ledger went red three times on 2026-11-19 (23:45, 23:51, 23:49) for reasons no
behavioural test covered:

| Incident | Would have been caught by |
|---|---|
| duplicate `--history` flag (`argparse` conflict) | building the parser (`--help`) |
| `build_report()` missing `require_alpha` | calling it with that keyword |
| `ALPHA_PASSTHROUGH_KEYS` undefined | one attribute assertion |
| `denylist_hits` dropped from the report | not covered here (report-shape) |

## What

Four tests that exercise the real entry points rather than the internals:

1. `python -m alpha_engine.audit3_tribunal --help` exits 0 and lists every flag
   the workflows pass.
2. `build_report(..., require_alpha=True)` returns a valid report.
3. A require-alpha build never yields `PROVEN_T2` when no alpha sidecar exists (G8).
4. `ALPHA_PASSTHROUGH_KEYS` is a tuple containing `covered`.

## Verification

`pytest tests/test_audit3_cli_smoke.py -q` → **4 passed**; together with the
tribunal and coverage suites, 60+ pass. These run in the normal CI test job, so a
future partial merge fails fast instead of at the next scheduled ledger.
