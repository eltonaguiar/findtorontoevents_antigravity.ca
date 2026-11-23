# 03 ETF

[SRC: _raw/audit3_audit3_ledger.json] Central question: does measured slippage consume more than 100 pct of per-trade PnL, leaving only monthly cadence viable?

## 1 Identity
[SRC: alpha_engine/money_ready_verdict.py:255] ETF is one of the canonical classes.
[SRC: _raw/audit3_audit3_ledger.json] Broad-index products (SPY, QQQ, IWM and sector ETFs) are filed under ETF in the ledger symbol bucket.

## 2 What the class is
ETFs trade like equities but carry tracking error, expense drag, and usually tighter spreads. Structural candidates are sector rotation, factor tilts, and mean-reversion around NAV.

## 3 Measured state
[SRC: _raw/audit3_audit3_ledger.json] Ledger class bucket: n 590, WR 0.4305 CI [0.3911, 0.4708], PF net 0.9947 at cost 0.0511 pct, gross 0.0449 pct, net -0.0062 pct, net CI [-0.4368, 0.433], 2x-cost CI [-0.4876, 0.3815] with stress_2x_ok false, DSR 0.0007, q 1.0, split-half unstable, verdict WEAK, required_n 1730370.
[SRC: _raw/audit_data_dashboard_data.json] `/audit` readiness: PF 1.89 on n 33, gate_state MONITORING.
[SRC: _raw/audit_data_money_ready_verdict.json] `money_ready_verdict` class verdict: INSUFFICIENT_DATA.
[SRC: _raw/audit3_audit3_ledger.json] Selection alpha: -0.1036 pct, CI [-0.3079, 0.0989].
The central question: gross expectancy 0.0449 pct against a cost of 0.0511 pct means the flat constant consumes 114 pct of gross per-trade PnL [SRC: _raw/audit3_audit3_ledger.json]. So the premise holds at the flat constant, but that constant is the same one used for EQUITY and measured ETF slippage is UNMEASURED. "Monthly cadence viable" is a hypothesis, not a measurement.

## 4 Contradictions
[SRC: _raw/audit_data_dashboard_data.json] `/audit` says PF 1.89 on n 33.
[SRC: _raw/audit3_audit3_ledger.json] `/audit3` says PF 0.9947 on n 590, and also kills symbol IWM (n 65, PF 0.5411).
The dashboard's 33 rows are a subset, so its PF is a small-n artifact rather than a class statistic.

## 5 Data integrity
[SRC: _raw/audit3_audit3_ledger.json] 590 ledger rows versus 33 dashboard rows is a 94 pct gap. The cause is UNMEASURED.

## 6 Cost reality
[SRC: _raw/audit3_audit3_ledger.json] Flat constant 0.05 pct, which exceeds gross per-trade PnL. If ETFs really trade tighter than equities the constant is conservative, but the point estimate is -0.0062 pct, so even a large cost cut leaves it near zero.
[SRC: reports/equity_cost_measurement/equity_cost_20261122.json] **ETF/equity cost is now MEASURED as an upper bound** (M1, 2026-11-22, 1-minute bars 2026-11-16..20): round-trip spread bound **12.07 bp** median over the breakout universe (SPY 8.31 bp, QQQ 12.07 bp, XLF 6.11 bp), Corwin-Schultz **1.50 bp**, per-side **6.04 bp**. The constant 0.05 pct (50 bp RT) is therefore ~4x the measured upper bound. This confirms the doc's own guess ("if ETFs really trade tighter ... the constant is conservative") but changes nothing: at 6.04 bp the class point estimate is still ≈ 0, so the answer to the central question is that cost does **not** explain the WEAK verdict, the absence of edge does.
[SRC: reports/equity_cost_measurement/class_cost_20261122.json] **M3 (2026-11-22) measured the ETF universe directly**: 14 names, yfinance 1-min bars 2026-11-16..20. Median round-trip upper bound **6.71 bp** (min SHY 0.61, p25 5.32, p75 8.31, p90 12.07, max SOXX 22.90) — a **37×** spread between the tightest and widest ETF, which is exactly why an average is not quoted. The 50 bp flat constant is ~7.5× this upper bound. Live NBBO was `BLOCKED_NO_LIVE_NBBO` (Tiingo IEX HTTP 429, Sunday) and commission is `COMMISSION_UNKNOWN`.

## 7 What would change the verdict
[SRC: _raw/audit3_audit3_ledger.json] One experiment: measure realised ETF slippage from fills for the 590 rows and recompute. Gate: net expectancy CI lower bound above zero. Falsifier: if the CI straddles zero even at measured cost, cadence changes cannot rescue it.

## 8 Blunt answer
[SRC: _raw/audit3_audit3_ledger.json] NOT PROVEN: PF 0.9947, net expectancy indistinguishable from zero, cost eats the gross edge.

[SRC: _raw/audit3_audit3_ledger.json] Least survivable number: PF net 0.9947. Near-zero net expectancy pins it to one, so any cost or mix change flips it either side.

## 9 Cross-check against /audit and the database
[SRC: _raw/audit_data_money_ready_verdict.json] This is the worst inversion in the system: `/audit` publishes daily PF 1.8752 (n 32) but the intrabar PF is 0.0187 (n 56), a `pf_inflation_x` of 100.28 and 58.9 percentage points of WR that do not survive honest first-touch resolution. The daily ETF number is an artifact.
[SRC: reports/class_metric_reconciliation_20261122.md] The live `trading_picks` table agrees with the intrabar column, not the daily one: gross PF 0.940 and net PF 0.889 over n 74. `/audit3` gives 0.9947 on n 590.
[SRC: _raw/audit_data_money_ready_verdict.json] `/audit` labels the class INSUFFICIENT_DATA on n 32 while also publishing a PF of 1.8752, so the label and the number disagree about whether the class is measurable.
[SRC: reports/forward_observations.jsonl] Zero non-CRYPTO forward rows exist, so ETF has no forward observation path.

## Provenance
- model: none (drafter fan-out blocked, see BLOCKERS.md B1; written by the curator from frozen evidence)
- prompt: none
- snapshot: `/audit3/audit3_ledger.json` 88606e1e… generated 2026-11-22T06:35:41Z
