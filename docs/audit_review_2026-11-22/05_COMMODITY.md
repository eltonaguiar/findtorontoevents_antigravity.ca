# 05 COMMODITY

Central question: is a tiny-n, low-PF class a real kill or a sample artifact, and why is a
flat slippage constant below measured here?

## 1 Identity
[SRC: alpha_engine/money_ready_verdict.py:255] COMMODITY is one of the canonical classes.
[SRC: _raw/audit3_audit3_ledger.json] The ledger has a COMMODITY class bucket and kills `futures_momentum` under it.

## 2 What the class is
Commodities have roll yield, storage cost, seasonality, and COT positioning.
[SRC: _raw/audit3_audit3_ledger.json] The repo runs COT and term-structure strategies (`commodity_term_cot`, `commodity_momentum`).

## 3 Measured state
[SRC: _raw/audit3_audit3_ledger.json] Ledger class bucket: n 50, WR 0.2 CI [0.1124, 0.3304], PF net 0.1505 at cost 0.15 pct, gross -2.8119 pct, net -2.9619 pct, net CI [-5.004, -1.3383], 2x-cost CI [-5.154, -1.4883], DSR 0.0, verdict KILL, required_n 24.
[SRC: _raw/audit3_audit3_ledger.json] Selection alpha: -3.5699 pct, CI [-5.5086, -2.0486].
[SRC: _raw/audit_data_dashboard_data.json] `/audit` readiness: gate_state BLOCKED.
[SRC: _raw/audit_data_money_ready_verdict.json] `money_ready_verdict` class verdict: NOT_READY with policy_frozen true.
The central question: by the ledger's own criterion the kill is not a sample artifact, because n 50 exceeds required_n 24 and the CI excludes zero. In absolute terms the sample is still small.

## 4 Contradictions
The plan said WATCH versus KILL.
[SRC: _raw/audit_data_dashboard_data.json] Today `/audit` shows BLOCKED, not WATCH.
[SRC: _raw/audit3_audit3_ledger.json] `/audit3` KILLs.
So the surfaces disagree less than the plan claimed, and the plan's WATCH label is not reproducible.

## 5 Data integrity
[SRC: _raw/audit3_audit3_ledger.json] Only 50 rows survive, and 64 COMMODITY picks were denylisted, so the surviving sample may be unrepresentative.
Adversarial review note [SRC: docs/audit_review_2026-11-22/_reviews/05_COMMODITY.review.md]: the H-101 COT publication-lag look-ahead is a known COMMODITY contamination, so this PF may be contaminated independently of n; the KILL does not rest on it (gross expectancy -2.8119 pct).

## 6 Cost reality
[SRC: _raw/audit3_audit3_ledger.json] Flat constant 0.15 pct. For contract-sized commodities that is likely optimistic rather than conservative, and measured slippage is UNMEASURED. Even at 2x the CI stays below zero, so the direction of the kill is robust.

## 7 What would change the verdict
[SRC: _raw/audit3_audit3_ledger.json] One experiment: reprice the 50 rows with contract-level tick and commission data. Gate: net CI lower bound above zero. Falsifier: if true-cost repricing moves the CI above zero the kill was a cost artifact, but a gross expectancy of -2.81 pct makes that unlikely.

## 8 Blunt answer
NO defensible edge: KILL on the ledger, CI entirely below zero, negative selection alpha.

Least survivable number: PF net 0.1505. With only 50 rows and many denylisted picks around them, one or two bad rows dominate the ratio [SRC: _raw/audit3_audit3_ledger.json]; the sign is robust but the magnitude is not.

## Provenance
- model: deepinfra/meta-llama/Meta-Llama-3.1-8B-Instruct (adversarial reviewer only; dossier drafted by the curator. Reviewer raised H-101 contamination in the data-integrity section. Drafter outage recorded in BLOCKERS.md B1.)
- prompt: the adversarial prompt file under /tmp (leakage-context block plus the class summaries)
- snapshot: `/audit3/audit3_ledger.json` 88606e1e… generated 2026-11-22T06:35:41Z
