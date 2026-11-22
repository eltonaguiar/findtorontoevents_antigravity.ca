# 02 EQUITY

Central question: is a high WR at PF below one exit geometry rather than skill, and is the
breakout family the only positive-OOS cell?

## 1 Identity
[SRC: alpha_engine/money_ready_verdict.py:255] EQUITY is one of the canonical classes.
[SRC: _raw/audit3_audit3_ledger.json] The ledger symbol bucket carries EQUITY symbols such as UBER, so membership is by symbol string.

## 2 What the class is
Equities have session hours, an auction, and market beta. Structural candidates are the momentum premium, the low-volatility premium, and earnings drift.
[SRC: _raw/audit3_audit3_ledger.json] The repo pre-registered a breakout pod `POD-EQUITY-BREAKOUT` on hypothesis `H-BABY-EQUITY-VT-PATTERN-SWEEP-001`.

## 3 Measured state
[SRC: _raw/audit3_audit3_ledger.json] Ledger class bucket: n 956, WR 0.4477 CI [0.4164, 0.4794], PF net 1.0499 at cost 0.0515 pct, gross 0.1573 pct, net 0.1058 pct, net CI [-0.4803, 0.6925], 2x-cost CI [-0.5317, 0.641] with stress_2x_ok false, DSR 0.0052, q 1.0, split-half unstable (first 0.7663, second -0.5546), verdict WEAK, required_n 22569.
[SRC: _raw/audit3_audit3_ledger.json] Selection alpha: -0.045 pct, CI [-0.417, 0.3279], which is no evidence either way.
[SRC: _raw/audit_data_dashboard_data.json] `/audit` readiness: gate_state MONITORING.
[SRC: _raw/audit_data_money_ready_verdict.json] `money_ready_verdict` class verdict: NOT_READY.
The central question's first half: the measured WR is 0.4477, not the 59 to 60 pct the plan recalled [SRC: _raw/audit3_audit3_ledger.json]. The breakout-is-the-only-positive-OOS-cell claim is UNVERIFIED: `POD-EQUITY-BREAKOUT` has n_forward 0 and is not eligible [SRC: _raw/audit3_audit3_ledger.json].

## 4 Contradictions
[SRC: _raw/audit_data_dashboard_data.json] `/audit` readiness shows PF 0.61 on n 218 with WR 38.5 pct.
[SRC: _raw/audit_data_money_ready_verdict.json] `money_ready_verdict` shows PF 1.08 on n 121.
[SRC: _raw/audit3_audit3_ledger.json] `/audit3` shows PF 1.0499 on n 956.
Three PFs on three populations. Only the ledger's has a CI, and it straddles zero.

## 5 Data integrity
[SRC: _raw/audit3_audit3_ledger.json] The dashboard counts a fraction of the ledger's 956 EQUITY rows, so most EQUITY rows priced by the ledger are not in the dashboard headline. Which filter causes the gap is UNMEASURED this pass.

## 6 Cost reality
[SRC: _raw/audit3_audit3_ledger.json] Flat constant 0.05 pct. Equities have spreads and borrow costs, so measured slippage is UNMEASURED. At 2x cost the CI is wider and still straddles zero, so the verdict does not hinge on the constant.

## 7 What would change the verdict
[SRC: _raw/audit3_audit3_ledger.json] One experiment: resolve the 956 EQUITY rows intrabar-honestly and re-run the bootstrap. Gate: net CI lower bound above 0.0 with the 2x-cost CI also above 0.0. Falsifier: if the CI still straddles zero at 2x, the class has no demonstrated edge.

## 8 Blunt answer
NOT PROVEN: PF above one on the ledger, but the CI straddles zero and the split halves disagree.

Least survivable number: PF net 1.0499. It rests on 956 rows whose first half is positive and second half negative [SRC: _raw/audit3_audit3_ledger.json], so a mix change moves it across one easily.

## 9 Cross-check against /audit and the database
[SRC: _raw/audit_data_money_ready_verdict.json] `/audit` gives PF 1.08 (n 121) daily versus 0.9796 intrabar (n 258), and `wr_inflation_pp` is -25.8, meaning the intrabar WR is HIGHER than the daily one, the opposite of the usual direction.
[SRC: reports/class_metric_reconciliation_20261122.md] The live `trading_picks` table gives gross PF 1.016 and net PF 0.959 over n 1210, so of four surfaces only `/audit3` (1.0499) is above 1.0 and the database says the class is below it after cost.
[SRC: _raw/audit3_audit3_ledger.json] The ledger requires n 22569 for EQUITY and has 956, so the one positive number is measured on about 4% of the sample needed to detect it. Any claim that EQUITY is the best class is a claim about the least-powered number on the page.
[SRC: reports/forward_observations.jsonl] There are zero non-CRYPTO forward rows, so EQUITY cannot accumulate forward observations and cannot clear the forward gate regardless of its backtest.

## Provenance
- model: none (drafter fan-out blocked, see BLOCKERS.md B1; written by the curator from frozen evidence)
- prompt: none
- snapshot: `/audit3/audit3_ledger.json` 88606e1e… generated 2026-11-22T06:35:41Z
