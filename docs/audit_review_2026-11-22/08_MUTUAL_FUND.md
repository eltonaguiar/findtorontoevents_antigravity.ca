# 08 MUTUAL_FUND

Central question: is this a tracked class or a placeholder (`intrabar_truth: null`) that should be
retired from the headline?

## 1 Identity
[SRC: alpha_engine/money_ready_verdict.py:255] MUTUAL_FUND is one of the canonical classes.
[SRC: alpha_engine/money_ready_verdict.py:253] It is required to appear even at n 0 so downstream consumers never assume a class is absent.

## 2 What the class is
Mutual funds price once daily at NAV. Momentum, factor exposure, and expense drag are the candidates.

## 3 Measured state
[SRC: _raw/audit_data_dashboard_data.json] `/audit` readiness: n 0, PF null, WR 0.0, gate_state MONITORING, sizing_allowed false.
[SRC: _raw/audit_data_money_ready_verdict.json] `money_ready_verdict` class: n 0, INSUFFICIENT_DATA, PF 0.0, intrabar_truth null.
[SRC: _raw/audit3_audit3_ledger.json] `/audit3` has no MUTUAL_FUND class bucket.
The central question is answered: it is a placeholder with zero rows on every surface, kept only because the canonical list requires it.

## 4 Contradictions
No surface disagrees, since all say zero.
[SRC: _raw/audit_data_dashboard_data.json] But gate_state MONITORING on zero observations reads as "being watched" when nothing exists to watch.

## 5 Data integrity
[SRC: _raw/audit_data_money_ready_verdict.json] n 0: no symbols, no sources, no dates.

## 6 Cost reality
UNMEASURED, since there are no trades.
[SRC: _raw/audit3_audit3_ledger.json] A flat constant 0.08 pct exists in the ledger conventions, but it is never exercised.

## 7 What would change the verdict
[SRC: _raw/audit_data_money_ready_verdict.json] One experiment: ingest any priced mutual-fund picks. Gate: n at least 30 before any verdict word other than INSUFFICIENT_DATA. Falsifier: n stays 0, in which case retire it from the headline and show it only in an appendix.

## 8 Blunt answer
UNMEASURED: a required placeholder with zero rows; it should not appear as a tracked class.

Least survivable number: n 0. It is the only number and the first ingested fund pick falsifies it [SRC: _raw/audit_data_money_ready_verdict.json].

## 9 Cross-check against /audit and the database
[SRC: _raw/audit_data_money_ready_verdict.json] `/audit` reports n 0 with PF 0.0 for MUTUAL_FUND, so there is nothing measured and the 0.0 must never be read as a performance figure.
[SRC: reports/class_metric_reconciliation_20261122.md] The live `trading_picks` table has no MUTUAL_FUND category rows at all, and `/audit3` has no MUTUAL_FUND class bucket, so the class is absent from every measured surface rather than performing badly.
[SRC: _raw/audit3_audit3_ledger.json] MUTUAL_FUND appears only in `slippage_pct_by_class` at 0.08, i.e. it is configured but never populated.

## Provenance
- model: none (drafter fan-out blocked, see BLOCKERS.md B1; written by the curator from frozen evidence)
- prompt: none
- snapshot: `/audit/data/money_ready_verdict.json` b5387de5… generated 2026-11-22T03:58:43Z
