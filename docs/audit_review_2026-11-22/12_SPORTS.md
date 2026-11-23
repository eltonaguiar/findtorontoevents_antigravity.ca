# 12 SPORTS

Central question: is this in scope for a financial audit, and if so what is its settlement and
resolution contract?

## 1 Identity
[SRC: alpha_engine/money_ready_verdict.py:255] Not one of the canonical classes.
[SRC: _raw/audit_data_dashboard_data.json] Absent from `/audit` this pass.
[SRC: _raw/audit3_audit3_ledger.json] Absent from the ledger's class, symbol and cell buckets.
[SRC: _raw/audit3_audit3_ledger.json] Sports exposure, if any, would come through prediction markets: the source families include `prediction_market`, and 112 denylist hits came from `prediction_market_consensus`.

## 2 What the class is
A sports outcome is a binary settlement: one event resolves YES or NO at a fixed time. It is a prediction-market contract, not a price series; its edge candidates are information timing and line-shopping, and its risk is settlement ambiguity (push, void, postponement).

## 3 Measured state
[SRC: _raw/audit_data_dashboard_data.json] `/audit` class verdict: absent.
[SRC: _raw/audit2_audit2.js:154] `/audit2` class verdict: absent (inherits the ledger).
[SRC: _raw/audit3_audit3_ledger.json] `/audit3`: zero SPORTS cells, verdict UNMEASURED. Prediction-market picks are scored inside existing buckets, not as SPORTS.

## 4 Contradictions
The program treats SPORTS as a class, but the pipeline files sports-like bets under prediction markets with no asset class of their own. There is no SPORTS number to contradict.

## 5 Data integrity
[SRC: _raw/audit3_audit3_ledger.json] Zero named rows, and the ledger's win definition is price-based (net pnl above zero), which a binary settlement does not fit cleanly.

## 6 Cost reality
UNMEASURED.
[SRC: _raw/audit3_audit3_ledger.json] Prediction-market fees and vig are not in the per-class slippage table.

## 7 What would change the verdict
[SRC: _raw/audit3_audit3_ledger.json] One experiment: define a settlement contract (resolved_yes/resolved_no/void with timestamps) and score prediction-market rows against it. Gate: at least 100 settled contracts. Falsifier: if rows cannot be settled deterministically, SPORTS stays out of the financial audit.

## 8 Blunt answer
UNMEASURED, and out of scope until a settlement contract exists; it is a prediction-market concern, not an asset class.

Least survivable number: there is no SPORTS number [SRC: _raw/audit3_audit3_ledger.json]. The least survivable claim is that SPORTS belongs in the financial taxonomy: nothing on any surface files a pick under it.

## Provenance
- model: none (drafter fan-out blocked, see BLOCKERS.md B1; written by the curator from frozen evidence)
- prompt: none
- snapshot: `/audit3/audit3_ledger.json` 88606e1e… generated 2026-11-22T06:35:41Z
