# 07 FUTURES

Central question: same cost-constant question as COMMODITY, plus whether class labels are contaminated.

## 1 Identity
[SRC: alpha_engine/money_ready_verdict.py:255] FUTURES is one of the canonical classes.
[SRC: _raw/audit3_audit3_ledger.json] The ledger class bucket has n 4.

## 2 What the class is
Futures have roll, margin, and contract multipliers. Structural candidates are trend, carry, and basis.

## 3 Measured state
[SRC: _raw/audit3_audit3_ledger.json] Ledger class bucket: n 4, WR 0.5 CI [0.15, 0.85], PF net 1.8719 at cost 0.15 pct, net 1.2853 pct, net CI [-2.9483, 5.519], DSR null, split-half null, verdict INSUFFICIENT_N, top_source_share 1.0.
[SRC: _raw/audit_data_dashboard_data.json] `/audit` readiness: n 17, PF 1.27, WR 35.3 pct, gate_state BLOCKED.
[SRC: _raw/audit_data_money_ready_verdict.json] `money_ready_verdict` class: n 17, INSUFFICIENT_DATA, policy_frozen true.
The cost part of the central question: the ledger uses the same 0.15 pct flat constant as COMMODITY [SRC: _raw/audit3_audit3_ledger.json], measured slippage is UNMEASURED, and with n 4 nothing can be said about it.

## 4 Contradictions
[SRC: _raw/audit_data_dashboard_data.json] `/audit` shows PF 1.27 at n 17.
[SRC: _raw/audit3_audit3_ledger.json] `/audit3` shows PF 1.87 at n 4, a four-trade number on the do-not-trust list.

## 5 Data integrity
[SRC: _raw/audit3_audit3_ledger.json] Labels are contaminated: `futures_momentum` is filed under COMMODITY in the kill tribunal while FUTURES has its own bucket, so the same word maps to two classes. INDEX is also often a futures alias. The exact contamination rate is UNMEASURED.

## 6 Cost reality
[SRC: _raw/audit3_audit3_ledger.json] Flat 0.15 pct, likely optimistic for index futures once commissions and roll are counted, and not measured.

## 7 What would change the verdict
[SRC: _raw/audit3_audit3_ledger.json] One experiment: resolve at least 100 FUTURES rows under one unambiguous class label. Gate: net CI lower bound above zero. Falsifier: if the relabelled bucket drops below 30 rows the class is not measurable and should merge into COMMODITY.

## 8 Blunt answer
UNMEASURED: n 4 on the ledger, no DSR, one source. The PF 1.87 is noise.

Least survivable number: PF net 1.8719. It is four trades with a CI spanning -2.95 to 5.52 [SRC: _raw/audit3_audit3_ledger.json]; it will not survive a single extra row.

## 9 Cross-check against /audit and the database
[SRC: _raw/audit3_audit3_ledger.json] `/audit3` reports the only positive selection alpha anywhere in the system, +1.3353 with PF 1.8719, on n 4. It is correctly labelled INSUFFICIENT_N, but the positive alpha is a four-row artifact and will be quoted out of context.
[SRC: reports/class_metric_reconciliation_20261122.md] The live `trading_picks` table has n 66 for FUTURES with gross PF 0.956 and net PF 0.841, so the 4-row cell is 6% of the available sample and disagrees with it in sign.
[SRC: _raw/audit_data_money_ready_verdict.json] `/audit` gives daily PF 1.2706 (n 17) versus intrabar 0.8929 (n 63), and FUTURES is `policy_frozen: true`.
[SRC: _raw/audit3_audit3_ledger.json] The ledger charges FUTURES a cost of 0.15 pct, which is the COMMODITY constant, because `class_cost_pct` has no FUTURES key even though `slippage_pct_by_class` lists FUTURES at 0.1.

## Provenance
- model: none (drafter fan-out blocked, see BLOCKERS.md B1; written by the curator from frozen evidence)
- prompt: none
- snapshot: `/audit3/audit3_ledger.json` 88606e1e… generated 2026-11-22T06:35:41Z
