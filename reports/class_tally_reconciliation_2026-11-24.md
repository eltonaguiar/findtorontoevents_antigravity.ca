# Class tally reconciliation (2026-11-24)

Provenance: [`docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json`](docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json), read on 2026-11-24.

## Two different scopes

Measured row counts in the committed ledger:

```
classes = 7
segments = 6
cells = 374
```

Class names: `CRYPTO, EQUITY, ETF, FOREX, COMMODITY, BOND, FUTURES`.
Segment classes: `EQUITY, ETF, FOREX, BOND, CRYPTO, COMMODITY` (namespace `discovery`).

The settled programme tally is `0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN (14 rows)`.

## Does 14 reconcile?

| Arithmetic | Result |
|---|---|
| `len(classes)` | 7 |
| `len(segments)` | 6 |
| `classes + segments` | 13 |
| `len(set(classes) ∪ set(segments))` | 7 |
| `len(cells)` | 374 |
| **any of these equal to 14?** | **no** |

### Second pass: do segments or cells reproduce `0 / 11 / 3`?

`segments` and `cells` were each evaluated against the exact tally shape
(INVESTABLE = count of `INVESTABLE`, NOT_INVESTABLE = `KILL` + `WEAK`,
UNKNOWN = `INSUFFICIENT_N`):

```
segments: total=6   INVESTABLE=0 NOT_INVESTABLE=6  UNKNOWN=0    (WEAK 4, KILL 2)
cells   : total=374 INVESTABLE=0 NOT_INVESTABLE=67 UNKNOWN=307  (WEAK 57, KILL 10, INSUFFICIENT_N 307)
target  : total=14  INVESTABLE=0 NOT_INVESTABLE=11 UNKNOWN=3
```

Neither matches. `segments` has 14-shape numerator but only 6 rows; `cells` has
374 rows and 307 unknowns. **No scope in this ledger produces 14 rows with the
`0 / 11 / 3` split.** This is recorded as a confirmed dead end: the tally comes
from an artifact or a filter not present in this checkout.

**Conclusion: the 14-row tally is not derivable from this ledger's `classes`, `segments`, or `cells` scopes.** 7 + 6 = 13, one short of 14, and the union is only 7 because all 6 segment classes are already class rows. I could force 14 by counting FUTURES in classes and then double-counting something, but that would be constructing a number to match a claim rather than measuring it.

The tally therefore comes from a different artifact than this ledger, or from a version of it that included one more row. **I cannot verify it from what is committed here, and I am not changing it.**

## Measured per-class verdicts (stored in the ledger)

```
OK    CRYPTO      n=6926   stored=KILL          rederived=KILL
OK    EQUITY      n=956    stored=WEAK          rederived=WEAK
OK    ETF         n=590    stored=WEAK          rederived=WEAK
OK    FOREX       n=264    stored=WEAK          rederived=WEAK
DRIFT COMMODITY   n=50     stored=KILL          rederived=INSUFFICIENT_N
DRIFT BOND        n=37     stored=WEAK          rederived=INSUFFICIENT_N
OK    FUTURES     n=4      stored=INSUFFICIENT_N rederived=INSUFFICIENT_N
```

Counter: `WEAK 4, KILL 2, INSUFFICIENT_N 1`.

## Two defects this measurement exposed

1. **Verdict drift (2 of 7).** COMMODITY (n=50) and BOND (n=37) are stored as `KILL` and `WEAK`, but both have fewer than 100 rows. The documented ladder puts `n < 100` at `INSUFFICIENT_N` before any PF or CI test, so neither stored verdict follows from its own sample size. These are exactly the classes the settled tally counts as UNKNOWN, so the tally's UNKNOWN bucket is more consistent with the ladder than the ledger's own `verdict` field is.

2. **`split_half` is `null` for at least one class.** The ladder treats a missing split as unstable, which caps that class at `CANDIDATE_CAP_HALVES`. That is safe, but it means "the halves were stable" can never be established for a class with too few rows to split.

## Mapping used

| Ladder verdict | Programme token |
|---|---|
| `KILL`, `WEAK` | NOT_INVESTABLE |
| `INSUFFICIENT_N` | UNKNOWN |
| `CANDIDATE*` | candidate only; never INVESTABLE |
| (nothing) | INVESTABLE — no ladder output grants it |

Under this mapping the 7 measured classes give `0 INVESTABLE / 6 NOT_INVESTABLE / 1 UNKNOWN`. If the two drifted rows are corrected to `INSUFFICIENT_N`, it becomes `0 / 4 / 3`.

## What cannot be claimed

- That the settled 14-row tally is right or wrong. It is unverifiable from this ledger.
- That any class is INVESTABLE. No ladder output can produce it; only forward evidence can, and none is present.

## What would settle it

Locate the artifact the 14-row tally was actually computed from, and reconcile that. Until then the discrepancy is recorded, not resolved, and the tally stands unchanged.
