# ITERATION-002 — Purity-filtered re-aggregation + significance (2026-11-14 18:20Z)

Applied the proof bar's purity gate to the **closed** ledger `dashboard_data.json::picks.recent_closed` (3,500 rows), then re-aggregated per strategy and tested significance with Bonferroni correction across the full 683-strategy universe.

## Purity result: the CLOSED ledger is largely clean (contamination lives in ACTIVE/summary)

- 3,500 rows → dropped **23** (12 `pnl=0` frozen, 11 UNKNOWN phantoms) → 3,488 clean.
- 0 placeholder "all-wins-exactly-3.0%" strategies in the closed ledger (that cohort is in the *summary* winners table + active_raw, not the resolved closed set).
- **Important correction to ITERATION-001:** the frozen-price/fabricated "edges" (87–97% WR) are in the ACTIVE + summary surfaces, NOT in `recent_closed`. The honest closed book is net-negative but not artifact-inflated.

## Re-aggregated honest result

- **Overall clean:** n=3,488, **sum PnL −469.51%, mean −0.1346%/trade** → still net-negative.
- 14 strategies have n≥50; **9 of 14 have PF < 1.0** (losing).
- Only one strategy clears PF>1.5: `rs-breakout-scout` (ETF, n=133, WR 53.4%, PF 1.652, tPnL +95.12).

## Significance test (one-sided mean>0, Bonferroni α = 0.05/683 = 7.3e-5)

| strategy | n | mean/trade | t | p (one-sided) | verdict |
|---|---|---|---|---|---|
| `rs-breakout-scout` | 133 | +0.715% | 2.37 | 0.0089 | **closest, but NOT significant** |
| `luxalgo_confluence` | 1,290 | +0.167% | 1.71 | 0.044 | not significant |
| `vol-contraction-scout` | 81 | +0.229% | 0.39 | 0.35 | not significant |
| `momentum-factor` | 105 | +0.101% | 0.23 | 0.41 | not significant |
| `intermarket-flow-scout` | 104 | +0.065% | 0.25 | 0.40 | not significant |

## Conclusion — honest, provable

**No strategy proves profitable on the closed ledger.** The best candidate `rs-breakout-scout` has t=2.37 (nominal p=0.009), which **fails Bonferroni** — and with 683 strategies, ~6 false discoveries at p<0.009 are expected by pure chance, so one such hit is exactly what noise predicts. The candidate seeds from ITERATION-001 (`forex_rsi2_mean_reversion` etc.) live in the MySQL/pf_registry ledger, not `recent_closed`, and are pending the same test.

## Forward path — the legitimate route to proof (ITERATION-003)

`rs-breakout-scout` is now a **single pre-registered hypothesis**. The correct confirmatory test is OUT-OF-SAMPLE: hold out a date cutoff, re-run on post-cutoff trades only, and require (a) PF>1.5, (b) nominal p<0.05 on the OOS mean — with NO 683-way penalty because only one hypothesis is tested OOS. If it clears, that is a defensible "profitable approach"; if not, the honest answer is "no edge exists and the system should be sized to zero / used for research only."

Tooling for 003: `alpha_engine/walkforward_validator.py` (OOS windows), `benchmark_closed_ledger.py` (bootstrap CI), MySQL `at_signal_outcomes.intrabar_pnl_pct` (purity source of truth).
