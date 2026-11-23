# Audit-surface review, 2026-11-22

Three audit surfaces (`/audit`, `/audit2`, `/audit3`) reviewed against frozen evidence, with one
dossier per asset class. Every number here is measured from the snapshot in `_MANIFEST.json`, or
written as `UNMEASURED`.

- `00_SURFACE_BASELINE.md` - page-to-fetch map, contradiction register, metric glossary, do-not-trust list
- `01_CRYPTO.md` … `12_SPORTS.md` - twelve class dossiers, one fixed template each
- `GHA_QA_FRAMEWORK.md`, `GHA_QA_RULE_CATALOG.md` - the GitHub Actions quality framework (Phase 3)
- `BLOCKERS.md` - steps that could not run, and why
- `REJECTED.md` - drafts that failed the lint or the adversarial pass, and why

## Cross-class verdict table

Verdict vocabulary, per surface:
- `/audit3` ledger: `KILL`, `WEAK`, `INSUFFICIENT_N` (cell and class gate).
- `/audit` readiness: `gate_state` = `BLOCKED`, `MONITORING`, plus `tier_vs_charter`.
- `/audit` money_ready_verdict: `NOT_READY`, `INSUFFICIENT_DATA`.

| # | Class | /audit3 ledger (verdict, n, PF) | /audit readiness (gate, n, PF) | /audit money_ready (verdict, n) | Blunt answer |
|---|---|---|---|---|---|
| 01 | CRYPTO | KILL [SRC: _raw/audit3_audit3_ledger.json] | MONITORING [SRC: _raw/audit_data_dashboard_data.json] | NOT_READY [SRC: _raw/audit_data_money_ready_verdict.json] | NO edge |
| 02 | EQUITY | WEAK [SRC: _raw/audit3_audit3_ledger.json] | MONITORING [SRC: _raw/audit_data_dashboard_data.json] | NOT_READY [SRC: _raw/audit_data_money_ready_verdict.json] | NOT PROVEN |
| 03 | ETF | WEAK [SRC: _raw/audit3_audit3_ledger.json] | MONITORING [SRC: _raw/audit_data_dashboard_data.json] | INSUFFICIENT_DATA [SRC: _raw/audit_data_money_ready_verdict.json] | NOT PROVEN |
| 04 | FOREX | WEAK [SRC: _raw/audit3_audit3_ledger.json] | BLOCKED [SRC: _raw/audit_data_dashboard_data.json] | NOT_READY [SRC: _raw/audit_data_money_ready_verdict.json] | UNMEASURED (coverage) |
| 05 | COMMODITY | KILL [SRC: _raw/audit3_audit3_ledger.json] | BLOCKED [SRC: _raw/audit_data_dashboard_data.json] | NOT_READY [SRC: _raw/audit_data_money_ready_verdict.json] | NO edge |
| 06 | BOND | WEAK [SRC: _raw/audit3_audit3_ledger.json] | BLOCKED [SRC: _raw/audit_data_dashboard_data.json] | INSUFFICIENT_DATA [SRC: _raw/audit_data_money_ready_verdict.json] | UNMEASURED |
| 07 | FUTURES | INSUFFICIENT_N [SRC: _raw/audit3_audit3_ledger.json] | BLOCKED [SRC: _raw/audit_data_dashboard_data.json] | INSUFFICIENT_DATA [SRC: _raw/audit_data_money_ready_verdict.json] | UNMEASURED |
| 08 | MUTUAL_FUND | absent [SRC: _raw/audit3_audit3_ledger.json] | MONITORING [SRC: _raw/audit_data_dashboard_data.json] | INSUFFICIENT_DATA [SRC: _raw/audit_data_money_ready_verdict.json] | placeholder |
| 09 | PENNY_STOCK | absent [SRC: _raw/audit3_audit3_ledger.json] | MONITORING [SRC: _raw/audit_data_dashboard_data.json] | INSUFFICIENT_DATA [SRC: _raw/audit_data_money_ready_verdict.json] | UNMEASURED |
| 10 | MEMECOIN | absent [SRC: _raw/audit3_audit3_ledger.json] | MONITORING [SRC: _raw/audit_data_dashboard_data.json] | INSUFFICIENT_DATA [SRC: _raw/audit_data_money_ready_verdict.json] | NO, leaning |
| 11 | INDEX | absent [SRC: _raw/audit3_audit3_ledger.json] | absent [SRC: _raw/audit_data_dashboard_data.json] | absent [SRC: _raw/audit_data_money_ready_verdict.json] | alias, not a class |
| 12 | SPORTS | absent [SRC: _raw/audit3_audit3_ledger.json] | absent [SRC: _raw/audit_data_dashboard_data.json] | absent [SRC: _raw/audit_data_money_ready_verdict.json] | out of scope |

Full n and PF per class are in each dossier's section 3 and in `_MANIFEST.json`. `/audit2` is not a
separate verdict column because it re-serves the ledger [SRC: _raw/audit2_audit2.js:154].

## The three P0s

1. **P0-1, selection alpha is negative and significant.** Picking lost to buy-and-hold by 0.3696 pct per trade overall, CI [-0.5673, -0.1674] [SRC: _raw/audit3_audit3_ledger.json]. The class table cannot see this; only the alpha table can.
2. **P0-2, stale and broken data paths.** `/audit/data/audit2_forward.json` is 22 hours stale [SRC: manifest:consistency_checks], and `/audit2` and `/audit3` reference payloads that return 404 [SRC: _raw/audit2_page.html]. A page can show fresh numbers next to day-old ones.
3. **P0-3, verdict labels without measurement.** `PROMOTED` sidecars at n 0 [SRC: audit_trail/dashboard_generator.py:12256], BOND WR 100 pct at n 2 [SRC: _raw/audit_data_dashboard_data.json], and FUTURES PF 1.87 at n 4 [SRC: _raw/audit3_audit3_ledger.json]. Labels outrun the data.

## How to regenerate

`python3 docs/audit_review_2026-11-22/scripts/build_manifest.py` rebuilds `_MANIFEST.json` from
`_raw/` with computed hashes. `python3 tools/doc_source_lint.py docs/audit_review_2026-11-22/`
re-checks the dossiers.

*Not investment advice.*
