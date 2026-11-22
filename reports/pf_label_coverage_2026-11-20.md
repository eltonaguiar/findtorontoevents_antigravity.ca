# PF label coverage

Date: 2026-11-20  |  author: freebuff (deepseek-v4-flash)

Rule adopted 2026-11-20: a class or system profit factor is quoted as
`PF <value> (n=<count>[, net <bp>bp])`. A PF without a denominator is not a
measurement -- CRYPTO was published at 1.31 / 0.83 / 0.26 from three
populations, all arithmetically correct.

**6/6 publishing surfaces carry the denominator.**

| surface | what it publishes | status | PF-ish lines scanned |
|---|---|---|---|
| `audit_trail/dashboard_generator.py` | asset_class_health `pf`/`profit_factor` | labelled | 67 |
| `alpha_engine/money_ready_verdict.py` | money_ready class PF + policy_clean_pf | labelled | 36 |
| `alpha_engine/audit3_tribunal.py` | audit3 ledger cell PF | labelled | 13 |
| `tools/anti_overfit_audit_sidecar.py` | per-strategy PF in anti_overfit_audit.json | labelled | 3 |
| `tools/crypto_pf_reconcile.py` | PF reconciliation table | labelled | 12 |
| `audit_dashboard/template.html` | PF rendered in class/system cards | labelled | 166 |

## Scope, stated

This list is the PF surfaces that reach a reader or another system. It is
deliberately **not** every `profit_factor` in the repo: ~60 backtest and
scraper scripts compute a PF for their own report and publish no class
figure, and labelling them would imply a class-level claim they do not make.
If a new surface starts publishing a class PF, add it here in the same PR.

Regenerate: `python tools/pf_label_audit.py`.
