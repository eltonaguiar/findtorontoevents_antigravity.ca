# Money Ready verdict now strict JSON — NaN blocker fixed (V2.1 P1)

**Date:** 2026-10-19
**Package:** V2.1 Priority-1 blocker (`planv2_Oct19_github.MD`)
**Files:** `alpha_engine/money_ready_verdict.py`, `tools/money_ready_snapshot.py`,
`tests/test_money_ready_verdict_strict_json.py` (new)

## What was broken

The live `https://findtorontoevents.ca/audit/data/money_ready_verdict.json`
returned **HTTP 200 but was not valid JSON**: bare `"dsr_score": NaN` tokens.
Python's `json.dump` emits `NaN`/`Infinity` by default; any browser
`JSON.parse()` (and any strict downstream consumer) rejects the document. The
dashboard therefore could not reliably read the verdict payload it was
supposed to render — a P1 publication blocker.

NaN arose whenever a gate had an empty/undefined return sample (DSR, PBO,
CI-LB on classes with too few closed picks) — the math produced `nan`, which
was serialized verbatim.

## What changed

1. **`alpha_engine/money_ready_verdict.py`** — all non-finite floats are
   sanitized at serialization time: `NaN`, `Infinity`, `-Infinity` become
   JSON `null` (with the gate's `pass`/`fail` state carried separately by the
   surrounding gate object, so no verdict logic depends on the float being
   present). Applied to the verdict payload construction, not just a global
   `allow_nan=False` crash — consumers get a valid document *and* an explicit
   null rather than a rejected one.
2. **`tools/money_ready_snapshot.py`** — the snapshot writer hardens output:
   writes via a strict encoder (`allow_nan=False` semantics after sanitizing)
   so any future non-finite value fails loudly at write time instead of
   shipping, and the emitted file is verified parseable before the atomic
   `os.replace`.
3. **`tests/test_money_ready_verdict_strict_json.py`** (new) — regression
   tests asserting:
   - `json.loads(..., parse_constant=...)` strict-parse of generated output
     raises on bare `NaN` (i.e. the test *would* catch a regression)
   - generated verdict/snapshot output strict-parses cleanly
   - no `NaN`/`Infinity` substrings in the serialized bytes

## Verification

- `python3 -m pytest tests/test_audit_cohort_units.py tests/test_money_ready_verdict_strict_json.py -q` → **13 passed**
- End-to-end: ran `tools/money_ready_snapshot.py --dry-run` and strict-parsed
  its stdout the way a browser would → **PASS, 9 asset classes, zero
  NaN/Infinity tokens**.
- RED-first: the strict tests were run against the pre-fix code and failed
  exactly as expected (3 failures), then went green after the fix.
- `python3 -m py_compile alpha_engine/money_ready_verdict.py tools/money_ready_snapshot.py` → clean

## Status

Fix + doc staged for commit on `fix/js-reference-accuracy-audit`; only files
created/modified by this work are included.
