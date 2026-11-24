# Canonical hypothesis statuses, without rewriting the registry (2026-11-19)

**Scope:** `alpha_engine/hypothesis_status.py` (new),
`tests/test_hypothesis_status.py` (new).

## Why

`reports/hypothesis_registry.json` uses **28 different spellings** for status
across 105 entries (`PRE-REGISTERED`, `forward-shadow`, `KILLED`,
`TESTED_KILL`, `REJECTED - only 0 scored windows (need 3)`, `NULL`, `CLOSED`, …).
Any status count is therefore unreliable, and two dashboards can disagree while
reading the same file.

The file is an **append-only pre-registration artifact**. Rewriting it would
destroy the audit trail, so this module normalises **on read** instead.

## What

Seven canonical states: `PRE_REGISTERED`, `UNTESTED`, `BLOCKED_DATA`, `FORWARD`,
`SUPPORTED`, `WEAK`, `REFUTED`.

- `normalize_status(raw)` handles case, separators, free-text prefixes
  (`REJECTED - …`), and data-gap notes.
- Unmapped spellings return `UNKNOWN` — deliberately **not** guessed — and are
  reported in `summarize()` so a human can decide.
- `summarize(registry)` walks the whole document recursively and returns counts
  plus `unmapped_spellings`.

## Current result on the real registry

```
{ "PRE_REGISTERED": 26, "UNTESTED": 16, "BLOCKED_DATA": 7, "FORWARD": 37,
  "SUPPORTED": 3, "WEAK": 2, "REFUTED": 50, "unknown": 2 }
unmapped: NEAR_ADMISSIBLE (1), IMPLEMENTED (1)
```

Those two are intentionally left for review: "near-admissible" could be WEAK or
FORWARD, and "implemented" does not imply tested.

## Verification

`python3 -m pytest tests/test_hypothesis_status.py -q` -> **7 passed**.
CLI: `python3 -m alpha_engine.hypothesis_status --registry reports/hypothesis_registry.json`
(exits 1 if any unmapped spelling exists, so drift is visible).

No registry file is modified.
