# The ledger carries the denylist enforcement summary (2026-11-19)

**Scope:** `alpha_engine/audit3_tribunal.py`, `tests/test_audit3_tribunal.py`.

## Why

`/audit3` and the ledger are the artifact of record for what the system believes.
The denylist gates emission, but its activity lived only in a separate JSONL that
the page never read — so a reader could not tell whether the gate was armed,
idle, or blocking half the book.

## What

`build_report` now attaches `denylist_hits`:

```json
{"available": true, "n": 27, "first_ts": "...", "last_ts": "...",
 "by_class": {"CRYPTO": 23, "COMMODITY": 4},
 "top_strategies": {"atr_percentile_gate_scanner": 9, ...},
 "path": "alpha_engine/data/audit3_denylist_hits.jsonl"}
```

Best-effort: a missing/unreadable log yields `{"available": false, "n": 0}` and
never fails the build.

## Verification

`pytest tests/test_audit3_tribunal.py tests/test_audit3_denylist_hits.py -q`
→ **62 passed**, including a test that a two-row temp log produces
`n=2`, `by_class={"CRYPTO": 2}`, and the top strategy.
