# 04 FOREX

Central question: is the class unmeasurable because `fx_prices` ends 2026-02-09 and symbols do
not join?

## 1 Identity
[SRC: alpha_engine/money_ready_verdict.py:255] FOREX is one of the canonical classes.
[SRC: _raw/audit3_audit3_ledger.json] The ledger has FOREX rows, so the class is not empty.

## 2 What the class is
FX has carry (interest differential), momentum, and mean-reversion, and session structure matters more than for equities.

## 3 Measured state
[SRC: _raw/audit3_audit3_ledger.json] Ledger class bucket: n 264, WR 0.3636 CI [0.3079, 0.4232], PF net 0.8496 at cost 0.021 pct, gross -0.0237 pct, net -0.0447 pct, net CI [-0.1686, 0.0779], 2x-cost CI [-0.1893, 0.0576], DSR 0.0, verdict WEAK.
[SRC: _raw/audit3_audit3_ledger.json] Selection alpha: -0.069 pct, CI [-0.1496, 0.0121].
[SRC: _raw/audit3_audit3_ledger.json] Kill tribunal kills FOREX `Breakout Momentum` (n 37, PF 0.3959) and `MeanReversionBB` (n 29, PF 0.0).
[SRC: _raw/audit_data_dashboard_data.json] `/audit` readiness: gate_state BLOCKED.
[SRC: _raw/audit_data_money_ready_verdict.json] `money_ready_verdict` class verdict: NOT_READY with policy_frozen true.

## 4 Contradictions
[SRC: _raw/audit_data_dashboard_data.json] `/audit` readiness shows PF 0.18 on n 468.
[SRC: _raw/audit_data_money_ready_verdict.json] `money_ready_verdict` also shows PF 0.1751 on n 468.
[SRC: _raw/audit3_audit3_ledger.json] `/audit3` shows PF 0.8496 on n 264.
The dashboard's 468 rows almost double the ledger's 264, so the ledger excludes or cannot price roughly 204 FOREX rows.

## 5 Data integrity
The premise that `fx_prices` ends 2026-02-09 is a repo-data claim and is UNMEASURED this pass (no `fx_prices` read).
[SRC: _raw/audit3_audit3_ledger.json] That the symbol join is imperfect is supported: the ledger scores 264 rows where the dashboard counts 468.
[SRC: _raw/audit_data_money_ready_verdict.json] The class is policy_frozen, so its gate cannot lift on data alone.

## 6 Cost reality
[SRC: _raw/audit3_audit3_ledger.json] Flat constant 0.02 pct, the lowest of any class. Retail FX spreads can exceed 2 bp, and measured slippage is UNMEASURED. The verdict is WEAK on a CI that straddles zero, so cost is not what decides it.

## 7 What would change the verdict
[SRC: _raw/audit3_audit3_ledger.json] One experiment: verify `fx_prices` coverage end date and join the unmatched FOREX rows. Gate: at least 400 priced rows and a net CI lower bound above zero. Falsifier: if the extra rows come in at PF below one, the class gets worse, not better.

## 8 Blunt answer
UNMEASURED on the central question (price-data coverage not checked), and NOT PROVEN on the edge.

Least survivable number: PF net 0.8496. It is computed on 264 of 468 rows [SRC: _raw/audit3_audit3_ledger.json], so pricing the unjoined rows can move it.

## 9 Cross-check against /audit and the database
[SRC: reports/class_metric_reconciliation_20261122.md] FOREX is the largest DB population at n 8014 with gross PF 1.5335 and net PF 1.081 at the ledger's own cost, yet `/audit3` publishes 0.8496 on only n 264 and `/audit` publishes 0.1751 on n 468. The database has roughly 30x the ledger's sample for this class.
[SRC: _raw/audit_data_money_ready_verdict.json] `/audit` daily PF 0.1751 versus intrabar PF 0.6351 (n 641), `pf_inflation_x` 0.28, and FOREX is `policy_frozen: true`, so its verdict is an operator freeze as much as a measurement.
[SRC: _raw/audit_data_denominator.json] Either the canonical 264-row cohort is an unrepresentative slice of the 8014 available rows, or the DB filter admits rows the canonical pipeline rejects (`invalid_row` is the largest exclusion at 11782). This is the strongest single case for cohort forensics.

## Provenance
- model: none (drafter fan-out blocked, see BLOCKERS.md B1; written by the curator from frozen evidence)
- prompt: none
- snapshot: `/audit3/audit3_ledger.json` 88606e1e… generated 2026-11-22T06:35:41Z
