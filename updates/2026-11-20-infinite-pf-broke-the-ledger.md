# Infinite profit factor broke the ledger build (2026-11-20)

**Scope:** `alpha_engine/forward_observations.py`,
`tests/test_forward_pf_json_safe.py` (new).

## What happened

The 05:07 ledger build failed:

```
ValueError: Out of range float values are not JSON compliant: inf
when serializing dict item 'net_pf'
when serializing dict item 'POD-FABER-TAA'
```

The ingest had just produced the **first forward rows for POD-FABER-TAA** — and
they were all winners. Profit factor divides gross wins by gross losses, so with
no losses it is `inf`, and the tribunal serialises with
`json.dumps(..., allow_nan=False)`.

A *good* record broke publishing.

## Change

`_finite_pf(v, ceiling=99.0)`:

| input | output |
|---|---|
| `inf` | `99.0` (a perfect record is excellent, but must be finite) |
| `-inf` | `0.0` |
| `nan` / `None` / non-numeric | `None` |
| finite | unchanged |

Applied to `net_pf` and `pf_ci_lb` in `promotion()`.

## Verification

- `pytest tests/test_forward_pf_json_safe.py tests/test_forward_observations.py tests/test_audit3_tribunal.py -q`
  → **60 passed**, including an all-winner pod that now serialises.
- Live context: forward ledger grew **430 → 443** rows
  (`H-119` 430, `H-2026-11-19-03` 12, `H-2026-11-19-06` 1) — the first accrual for
  any pod other than H-119.
