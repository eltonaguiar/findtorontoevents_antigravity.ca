# 08 — Evidence Index

**Date:** 2026-11-15 · Every claim in this package traces here.

---

## 1. Measured in this repo

| Artefact | What it establishes |
|---|---|
| `reports/asset_class_measurability.json` | 6,968 closed rows, 3,350 forged (48.1%), 3 of 7 classes measurable |
| `reports/pnl_zero_validation_live.json` | 37 fabricated flats verified against real closes, errors to −17.6% |
| `reports/risk_metrics_live.json` | CVaR95 −7.96%, Kelly −0.0538, MC ruin 44.4%, HHI 0.385 |
| Live payload `2026-11-14T22:34Z` | Asset classes present: CRYPTO 5584, EQUITY 933, ETF 616, FOREX 472, COMMODITY 54, BOND 47, FUTURES 15, SPORTS 2 — **no PREDICTION class** |

Reproduce: `python3 tools/asset_class_measurability.py --payload <live json>`

## 2. Prediction-market findings (this round)

| Claim | Evidence |
|---|---|
| No PREDICTION class in ledger | Row walk of live payload; 8 classes only |
| PM picks tagged CRYPTO | 32 pick-shaped rows from `pm_kalshi_signals` / `prediction_market_consensus` carry `asset_class=CRYPTO` |
| Kalshi fee formula | `ceil(M × 0.07 × C × P × (1−P))` — fee schedule effective 2026-07-07, kalshi.com/docs/kalshi-fee-schedule.pdf |
| Fee as % of stake | 6.3% at 10¢, 5.3% at 25¢, **3.5% at 50¢**, 1.8% at 75¢, 0.7% at 90¢ |
| Polymarket fees | `fee = C × θ × P × (1−P)`, θ 0.04–0.07 by category; Polymarket US θ 0.05 → 0.06 (Jul) → 0.0695 (Sep 2026); makers 0 + 15–25% rebate |
| Copy trading costs | Taker fee paid twice + fill after leader's price move (derivation in `02_prediction_markets/`) |

Sources: kalshi.com/fee-schedule, docs.polymarket.com/trading/fees, help.polymarket.com trading-fees,
chanceledger.com fee survey (verified 2026-10-18).

## 3. Mutual fund / benchmark evidence

| Claim | Evidence |
|---|---|
| 92.89% of large-cap active funds trailed S&P 500 over 20y | SPIVA U.S. Year-End 2025, Report 1a |
| 85.59% over 10y, 88.96% over 5y, 78.78% over 1y | same |
| 95.01% of all domestic funds trailed S&P Composite 1500 over 20y | same |
| Mid-Year 2026: 67% of large-cap funds trailed over 1y | SPIVA U.S. Mid-Year 2026 |
| 90.2% of SPY 10-year windows positive; CAGR 8.71%; maxDD −52.2% | Measured from SPY monthly history (407 months), prior session |
| Fee drag ≈10% of terminal value over 20y (0.60% vs 0.03% ER) | Arithmetic on the same series |

## 4. SubQ artefacts

| File | Contents |
|---|---|
| `07_subq/subq_questions.json` | 8 questions + prior/evidence states |
| `07_subq/subq_run_20261115T003430Z.json` | Both arms, request SHA-256, token usage |
| `07_subq/FACTCHECK.md` | Analysis incl. the FOREX-vs-EQUITY disagreement |

## 5. Not measured — do not cite as findings

| Claim | Status |
|---|---|
| Any excess return vs SPY / BTC / cash / AGG | **Never computed for any class** |
| Information ratio, down-capture, capture ratio | Not computed |
| Fees impact on this system's PnL | Fee model absent from the ledger |
| Mutual fund returns for specific funds | Not fetched; SPIVA is the population statistic |
| Prediction-market calibration / Brier score | No settlement data recorded |
| Whether maker-side PM is profitable | Open question; A5 is assigned to test it |
| Contest returns (Larry Williams etc.) | From organiser standings via completetradersedge.com; single contest years |

## 6. Known limitations

1. **Verified ≠ intrabar-validated** — 3,618 marks are marked, not replayed; replay historically
   reclassifies ~26% of TP_HIT to SL_HIT.
2. **Three CRYPTO PFs circulate** (0.258 / 0.74 / 1.02) on different cohorts.
3. **SubQ has no reasoning trace**, so only behavioural deltas are auditable.
4. **Costs are industry-typical assumptions**, not measured fills — the repo has no fill model.
5. **SPIVA is a population statistic** — it does not identify which 7% of funds win.
