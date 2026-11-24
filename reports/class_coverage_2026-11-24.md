# Per-class coverage and effective source diversity (2026-11-24)

Provenance: [`docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json`](docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json) via [`tools/class_coverage.py`](tools/class_coverage.py), run 2026-11-24.

## Coverage against the 50% floor

```
class             n  coverage%  below 50%  ledger ok
CRYPTO         6926      24.17       True      False
EQUITY          956      76.46      False       True
ETF             590      91.36      False       True
FOREX           264       50.0      False       True
COMMODITY        50       80.0      False       True
BOND             37      94.59      False       True
FUTURES           4      100.0      False      False
```

CRYPTO is the only class below the floor, and it is 92% of the ledger (6,926 of
7,827 rows). The classes that look well covered are the small ones: BOND at
94.59% is 35 of 37 rows.

FUTURES shows the opposite failure. Its coverage is 100% (4 of 4) yet the ledger
flags it `ok: false`, because its `alpha_gate` has `alpha_ci_lo: null` and status
`unproven`. Coverage and evidence are separate properties, and a high coverage
number on a tiny sample means nothing.

## Effective source diversity

Using the top-source share, an upper bound on effective independent sources is
`1 / (p^2 + (1-p)^2)`:

| class | n | top_source_share | effective sources (approx) | single_source flag |
|---|---|---|---|---|
| FUTURES | 4 | 1.000 | 1.0 | true |
| ETF | 590 | 0.9644 | 1.1 | true |
| BOND | 37 | 0.8919 | 1.2 | false |
| EQUITY | 956 | 0.7939 | 1.5 | false |
| CRYPTO | 6926 | 0.5866 | 1.9 | false |
| FOREX | 264 | 0.4318 | 2.0 | false |
| COMMODITY | 50 | 0.540 | 2.0 | false |

No class has more than about two effective independent sources. Row counts
(EQUITY 956, CRYPTO 6,926) therefore overstate independent evidence by one to
two orders of magnitude. This is the same thin-effective-n problem that shows
up in the forward sample, where dropping three symbols out of 109 turns the mean
from +0.1348% to −0.0371%.

## What a CRYPTO backfill would need

The gap is 5,252 of 6,926 rows with no alpha measurement. Closing it needs, per
row, the return of the pick *and* the return of its benchmark over the same
window, so `alpha = pick - benchmark` can be computed. `hold_net_pct` (−0.1431)
and `alpha_ci` ((−0.9095, −0.208)) are already present, so the machinery works;
what is missing is benchmark returns for those rows.

It is probably not worth the effort to rescue the class: CRYPTO's measured alpha
CI is entirely below zero, so a complete sample would most likely confirm
`KILL` rather than overturn it. The honest use of a backfill is to *test* that,
not to hope for a different verdict.
