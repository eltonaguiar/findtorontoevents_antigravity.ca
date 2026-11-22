# 06 BOND

Central question: is there any measurement at all beyond INSUFFICIENT_DATA?

## 1 Identity
[SRC: alpha_engine/money_ready_verdict.py:255] BOND is one of the canonical classes.
[SRC: _raw/audit_data_money_ready_verdict.json] Top symbol is TLT and the top source is `bond_duration_rotation`.

## 2 What the class is
Bonds carry duration risk, credit spread, and rate momentum. Candidate edges are the term premium and duration rotation.

## 3 Measured state
[SRC: _raw/audit_data_dashboard_data.json] `/audit` readiness: n 2, WR 100.0 pct, PF null, gate_state BLOCKED, sizing_allowed false.
[SRC: _raw/audit_data_money_ready_verdict.json] `money_ready_verdict` class: n 2, INSUFFICIENT_DATA, policy_frozen true.
[SRC: _raw/audit3_audit3_ledger.json] `/audit3` ledger class bucket: n 37, WR 0.4324, PF net 0.806, net -0.0978 pct, CI [-0.3388, 0.1688], verdict WEAK.
[SRC: _raw/audit3_audit3_ledger.json] Selection alpha: n 35, alpha -0.0512 pct, CI [-0.3999, 0.305].
The central question is answered yes: the ledger has 37 rows with a real CI, though it straddles zero. `/audit` shows only 2 rows, which is why it reports INSUFFICIENT_DATA.

## 4 Contradictions
[SRC: _raw/audit_data_dashboard_data.json] `/audit` says n 2 and WR 100 pct, a two-trade artifact that must not be quoted.
[SRC: _raw/audit3_audit3_ledger.json] `/audit3` says n 37 and WR 43.24 pct.
[SRC: _raw/audit_data_money_ready_verdict.json] The intrabar view shows WR 0.0769 on n 26 versus a daily WR of 1.0 on n 2, a 92.3 pp inflation. That is the most important BOND number: the daily view overstates the win rate by 92 points.

## 5 Data integrity
[SRC: _raw/audit_data_money_ready_verdict.json] The class is policy-frozen (operator-imposed, not data-thin), TLT is 100 pct of the symbol sample, and one source holds 50 pct.

## 6 Cost reality
[SRC: _raw/audit3_audit3_ledger.json] Flat constant 0.05 pct and measured slippage is UNMEASURED. TLT spreads are small, so 5 bp is plausible.

## 7 What would change the verdict
[SRC: _raw/audit3_audit3_ledger.json] One experiment: accumulate more than 100 BOND rows with intrabar-honest resolution. Gate: net CI lower bound above zero. Falsifier: if intrabar-honest WR stays near 8 pct the class is harmful.

## 8 Blunt answer
UNMEASURED at the dashboard surface and WEAK-but-unproven at the ledger; no edge demonstrated.

Least survivable number: WR 43.24 pct at n 37. The same class shows a 7.69 pct intrabar WR on 26 trades [SRC: _raw/audit_data_money_ready_verdict.json]; the two disagree by 35 points on overlapping populations, so one will not survive.

## 9 Cross-check against /audit and the database
[SRC: _raw/audit_data_money_ready_verdict.json] `/audit` publishes a daily WR of 1.0 on n 2 (PF null) while the intrabar path gives WR 0.0769 on n 26 (PF 0.3915), a 92.3 percentage point gap. n 2 is not a measurement, but the published number is the n 2 one.
[SRC: reports/class_metric_reconciliation_20261122.md] The live `trading_picks` table gives gross PF 0.658 and net PF 0.564 over n 75, while `/audit3` gives 0.806 on n 37. All three are below 1.0.
[SRC: _raw/audit_data_money_ready_verdict.json] BOND is `policy_frozen: true`, so any BOND verdict today reflects an operator block as much as the data.

## Provenance
- model: none (drafter fan-out blocked, see BLOCKERS.md B1; written by the curator from frozen evidence)
- prompt: none
- snapshot: `/audit3/audit3_ledger.json` 88606e1e… and `/audit/data/money_ready_verdict.json` b5387de5…
