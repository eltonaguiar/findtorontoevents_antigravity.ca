# IDEA-H Lead/Lag — Findings (NO leading-indicator edge)

**Date:** 2026-06-13 · **Author:** claude-fable · **Verdict: NO EDGE — do not wire PM odds as a leading signal.**

## TL;DR

Backfilled **~6 months of daily prediction-market Fed-rate odds** (Polymarket CLOB + Kalshi candlesticks) and ran the IDEA-H lead/lag analysis across **149 markets**. After Bonferroni correction over 298 tests:

- **20 markets show LEADING at the raw |r|≥0.30 threshold; 0 survive correction (α=1.7e-4).**
- The only correlations strong enough to survive Bonferroni are **COINCIDENT (lag 0) or REACTIVE (lag −1)** — PM odds move *with* or *after* TLT / EUR-USD, never reliably before.

Per IDEA-H's own rule ("if odds lag by 1–3 days, flag as reactive — discard for trading"), **there is no tradeable lead from prediction-market Fed odds into bonds/FX.** This is the answer to the highest-scored brainstorm idea's core question (does PM lead or lag the underlying?) — it lags/coincides.

## Method

| Param | Value |
|---|---|
| Source | Polymarket CLOB `prices-history` (fidelity=1440) + Kalshi `candlesticks` (period_interval=1440) |
| Markets | 152 fetched, **149 with ≥20 daily points** (75 Polymarket + 74 Kalshi) |
| Underlyings | TLT (long-duration bonds), EURUSD=X (USD leg) — what pm_macro_overlay trades |
| Stat | Pearson r of daily Δodds vs underlying daily return at lags −3..+3; best lag per (market, underlying) |
| Correction | Two-tailed t-test p-value (exact, incomplete-beta) + Bonferroni over 298 reported correlations |
| Seed cmd | `python3 prediction_market_agents/pm_odds_history.py --backfill` (idempotent) |

## Result

Verdict distribution (best lag per market×underlying): **233 NO_SIGNAL · 38 REACTIVE · 20 LEADING · 7 COINCIDENT.**

The 5 most-significant correlations (all that clear Bonferroni α=1.7e-4) are **lag ≤ 0**:

| p (uncorrected) | market | underlying | verdict | lag | r |
|---|---|---|---|---|---|
| 3e-5 | polymarket 254247 | EURUSD=X | COINCIDENT | 0 | 0.415 |
| 4e-5 | polymarket 254247 | TLT | REACTIVE | −1 | 0.414 |
| 5e-5 | polymarket 253299 | TLT | REACTIVE | −1 | 0.397 |
| 6e-5 | polymarket 255335 | TLT | REACTIVE | −1 | 0.339 |
| — | (every raw-LEADING result) | — | LEADING | ≥+1 | p ≫ α |

Read: when there IS a real (correction-surviving) relationship, the underlying moves first and the odds react. The 20 raw-LEADING verdicts are the best-of-7-lag selections across 149 markets — exactly the multiple-comparison shape that manufactures false positives, and none clear the corrected bar.

## Decision

- **Do NOT wire PM odds as a leading indicator** (closes IDEA-H milestone #6 as NO-EDGE, not "pending").
- The conservative design of `pm_macro_overlay.py` — emit only on **contemporaneous cross-platform consensus**, never on a lead — is **vindicated**: there is no lead to exploit, so consensus-at-time is the right (and only defensible) use of PM odds.
- Re-test only if a future structural reason emerges (e.g. a new high-liquidity per-meeting market with genuine information lead). The analyzer + backfill are now in place to re-run in one command.

## Artifacts

- `prediction_market_agents/data/pm_odds_history.jsonl` — 20,958 backfilled daily odds rows (rows tagged `"backfilled": true`).
- `prediction_market_agents/data/pm_leadlag_report.json` — full per-market correlation report incl. `best_p_uncorrected` + `bonferroni_significant`.
- Reproduce: `python3 prediction_market_agents/pm_odds_history.py --backfill && python3 prediction_market_agents/pm_lead_lag_analyzer.py`
