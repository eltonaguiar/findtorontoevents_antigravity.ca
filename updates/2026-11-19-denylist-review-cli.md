# One-command denylist review (2026-11-19)

**Scope:** `alpha_engine/audit3_denylist_hits.py`,
`tests/test_audit3_denylist_hits.py`.

## Why

The weekly review previously needed an inline Python snippet. That is a
friction point for something meant to be run routinely, and the CLI also exits
non-zero when there is nothing recorded so a scheduled check cannot mistake
"no data" for "clean".

## What

```bash
python3 -m alpha_engine.audit3_denylist_hits            # text summary
python3 -m alpha_engine.audit3_denylist_hits --json     # machine-readable
python3 -m alpha_engine.audit3_denylist_hits --path reports/x.jsonl
```

Prints the denial count, first/last timestamp, and the top strategies, symbols
and asset classes. Defaults to `AUDIT3_DENYLIST_HIT_LOG` or
`alpha_engine/data/audit3_denylist_hits.jsonl` (the CI-persisted path).

Exit codes: `0` when denials exist, `1` when the log is empty or absent.

## Verification

`pytest tests/test_audit3_denylist_hits.py -q` → **8 passed**, including a CLI
test for the empty (exit 1) and populated (exit 0) cases.
