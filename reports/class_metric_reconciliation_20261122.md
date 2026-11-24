# Per-class metric reconciliation — 20261122

Ledger: `docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json`

No number here is edited from a source. A mismatch is reported, not patched.

## 1 Ledger internal consistency (B2)

| class | n | WR | net PF | alpha | alpha_n | verdict |
|---|---|---|---|---|---|---|
| CRYPTO | 6926.0 | 0.3939 | 0.7886 | -0.5549 | 1674.0 | KILL |
| EQUITY | 956.0 | 0.4477 | 1.0499 | -0.045 | 731.0 | WEAK |
| ETF | 590.0 | 0.4305 | 0.9947 | -0.1036 | 539.0 | WEAK |
| FOREX | 264.0 | 0.3636 | 0.8496 | -0.069 | 132.0 | WEAK |
| COMMODITY | 50.0 | 0.2 | 0.1505 | -3.5699 | 40.0 | KILL |
| BOND | 37.0 | 0.4324 | 0.806 | -0.0512 | 35.0 | WEAK |
| FUTURES | 4.0 | 0.5 | 1.8719 | 1.3353 | 4.0 | INSUFFICIENT_N |

### Findings (6)

| sev | class | check | detail |
|---|---|---|---|
| HIGH | CRYPTO | alpha covers the class sample | alpha_n 1674 of n 6926 = 24.2% (alpha -0.5549) is measured on a subset, not the class |
| HIGH | EQUITY | alpha covers the class sample | alpha_n 731 of n 956 = 76.5% (alpha -0.045) is measured on a subset, not the class |
| HIGH | ETF | pf consistent with gross expectancy | implied gross losses -4998.3 <= 0 (pf 0.9947, gross_exp 0.0449, n 590.0) |
| HIGH | FOREX | alpha covers the class sample | alpha_n 132 of n 264 = 50.0% (alpha -0.069) is measured on a subset, not the class |
| HIGH | COMMODITY | alpha covers the class sample | alpha_n 40 of n 50 = 80.0% (alpha -3.5699) is measured on a subset, not the class |
| MED | FUTURES | alpha == pick_net - hold_net | 1.2853 - 0.0 = 1.2853 vs alpha 1.3353 |

## 2 Gross to net bridge (B3)

Not run (no `--db`), or the database was unreachable.
### Bridge findings

- **BLOCKED** db: ModuleNotFoundError: No module named 'tools'

## Provenance

- cost constants: ledger `conventions.slippage_pct_by_class`; /audit `SLIPPAGE_BPS` in `alpha_engine/money_ready_verdict.py`
- DB population filter: `tools/per_class_scrutiny_engine.py:74-81`
- generated: 2026-11-22T07:00:56.025176+00:00
