# Don't publish a "share of valid" above 100% (2026-11-19)

**Scope:** `alpha_engine/audit3_tribunal.py` (`payload_coverage`),
`tests/test_audit3_coverage_alpha.py`.

## What was wrong

The live ledger reported:

```
scored_rows 8613 · valid_closed_picks 8175 · scored_share_of_valid_pct 105.26
```

Scored rows cannot exceed "valid" rows of the same book. The two numbers come
from different populations: `scored_rows` is the canonical resolved view, while
`valid_closed_picks` is the publishing payload's summary. The ratio is
meaningless when they disagree, and 105% invites a reader to conclude the ledger
double-counts.

## Change

`payload_coverage` now:

- publishes `scored_share_of_valid_pct` only when it is ≤ 100%;
- otherwise sets it to `null` and adds `scored_share_of_valid_note` explaining
  that the numerator and denominator come from different populations.

Normal ratios are unchanged (e.g. 500/800 → 62.5).

## Verification

`pytest tests/test_audit3_coverage_alpha.py tests/test_audit3_tribunal.py -q`
→ **44 passed**, including the new
`test_share_of_valid_is_nulled_when_it_exceeds_100`.
