# 09 PENNY_STOCK

Central question: are the tiny-n catastrophic cells evidence or noise, and does the literature
bound it?

## 1 Identity
[SRC: alpha_engine/money_ready_verdict.py:255] Not one of the canonical classes, but the dashboard and money_ready_verdict emit it as its own class.
[SRC: _raw/audit_data_money_ready_verdict.json] It has no bucket in the `/audit3` ledger, so the only measurements are on `/audit`.
Inclusion is justified because the repo emits and scores it.

## 2 What the class is
Sub-dollar equities: wide spreads, dilution risk, pump-and-dump regimes, thin liquidity. The structural feature that dominates is cost, not edge; the candidate edge is event-driven momentum around filings and squeezes.

## 3 Measured state
[SRC: _raw/audit_data_dashboard_data.json] `/audit` readiness: n 4, WR 50.0 pct, PF 0.18, gate_state MONITORING, sample_tier BELOW_T2.
[SRC: _raw/audit_data_money_ready_verdict.json] `money_ready_verdict`: n 4, PF 0.1779, INSUFFICIENT_DATA, intrabar_truth null, and DSR skipped because there is no n_trials baseline for the class.

## 4 Contradictions
[SRC: _raw/audit_data_dashboard_data.json] `/audit` shows WR 50 pct with PF 0.18, which is consistent only if the wins are tiny and the losses large, the classic penny-stock payoff shape. No surface disagrees; there is simply nothing there.

## 5 Data integrity
[SRC: _raw/audit_data_money_ready_verdict.json] n 4, no intrabar truth, legacy fallback for sizing.
[SRC: _raw/audit3_audit3_ledger.json] A 4-trade sample cannot distinguish a strategy from a coin flip: the ledger's own n 4 FUTURES WR CI is [0.15, 0.85].

## 6 Cost reality
[SRC: _raw/audit3_audit3_ledger.json] The conventions assign PENNY_STOCK the highest round-trip constant, 0.3 pct. That is the right order for sub-dollar names and probably still optimistic, since measured slippage is UNMEASURED.

## 7 What would change the verdict
[SRC: _raw/audit_data_money_ready_verdict.json] One experiment: collect at least 100 penny-stock closed picks with intrabar resolution. Gate: net PF CI lower bound above 1.0 at the 0.3 pct cost. Falsifier: PF stays below 0.5.

## 8 Blunt answer
UNMEASURED: four trades, no intrabar truth, no DSR baseline. The PF 0.18 is noise, not evidence.

Least survivable number: PF 0.1779. It is computed on four trades [SRC: _raw/audit_data_money_ready_verdict.json], so one trade flips it.

## 9 Cross-check against /audit and the database
[SRC: _raw/audit_data_money_ready_verdict.json] `/audit` reports PF 0.1779 on n 4 with no intrabar measurement, so the number rests on four trades and has no honest-resolution counterpart.
[SRC: reports/class_metric_reconciliation_20261122.md] The live `trading_picks` table has no PENNY_STOCK category rows, and `/audit3` has no PENNY_STOCK class bucket, so three surfaces cannot corroborate the four-row figure.
[SRC: _raw/audit3_audit3_ledger.json] PENNY_STOCK is charged the highest cost in the system at 0.3 pct, ten times EQUITY, which on a four-row sample can flip the sign of PF by itself.

## Provenance
- model: none (drafter fan-out blocked, see BLOCKERS.md B1; written by the curator from frozen evidence)
- prompt: none
- snapshot: `/audit/data/money_ready_verdict.json` b5387de5… and `/audit/data/dashboard_data.json` 888591a6…
