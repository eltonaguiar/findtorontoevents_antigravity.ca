# Coverage denominator reconciliation (P0, 2026-11-20)

**Scope:** `alpha_engine/audit3_tribunal.py` (`payload_coverage`),
`tests/test_audit3_coverage_alpha.py`.

## The defect (peer-review P0)

The live ledger reported:

```
scored_rows 8,769 · valid_closed_picks 7,942 · scored_share_of_valid_pct 110.41
```

Two different populations were being divided: `scored` is the **canonical
resolved view**, `valid_closed_picks` is the **publishing payload's summary**.
A prior change stopped *publishing* the impossible ratio (it returned `null` with
a note), but the underlying mismatch was still there — a masked number is not a
reconciled one.

## Change

`payload_coverage` now reconciles before dividing:

- when the canonical view is authoritative and it supplied `kept_rows`, then
  `valid = max(payload_valid, canonical_kept_rows)`;
- the basis is published as **`valid_closed_picks_basis`**
  (`canonical_kept_rows` or `payload_summary`);
- the >100% guard stays as a last resort, but should no longer fire.

## Verification

Live payload rebuild:

```
mode canonical · scored 8735 · valid 8735
valid_closed_picks_basis  canonical_kept_rows
scored_share_of_valid_pct 100.0   status ok   note False
```

`pytest tests/test_audit3_coverage_alpha.py tests/test_audit3_tribunal.py tests/test_audit3_expectancy_gates.py -q`
→ **51 passed**, including a new test that a canonical payload with a smaller
`valid_closed_picks` reconciles to 100% rather than 110%.
