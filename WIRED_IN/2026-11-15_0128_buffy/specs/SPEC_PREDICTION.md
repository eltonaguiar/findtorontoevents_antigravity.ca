# Algorithm Specification — PREDICTION MARKETS

**Agent:** buffy (Codebuff) · **Date:** 2026-11-15
**Status:** `NOT MEASURED — AND NOT MEASURABLE IN THE CURRENT LEDGER` (see §1)

---

## 1. The structural problem, first

There is **no `PREDICTION` asset class in the live ledger.** Rows from `pm_kalshi_signals` and
`prediction_market_consensus` are filed as **CRYPTO** (32 rows). Two consequences:

1. Prediction-market outcomes are aggregated into CRYPTO's profit factor, where they are invisible.
2. The system has **never computed a win rate** for prediction markets. It cannot learn from them.

Full reasoning in `2026-11-15_1233AM_winning-strategies/buffy/02_prediction_markets/WHY_NO_WINNERS.md`.
Nothing in this file changes that: it specifies the rule that *could* be measured once the class exists.

---

## 2. Why the continuous-instrument rule set does not transfer

A prediction contract settles at **$1 or $0**. The repo's resolver models entry / TP / SL / TIME_EXIT on
a continuous price. Forced onto a binary, it produces the pathology already in the ledger: closed rows
with `exit_price == entry_price` — flat closes that carry no information.

The spec therefore must be **settlement-native**: the outcome is `{0, 1}`, and P&L is
`(settlement − entry) × contracts − fees`.

---

## 3. Fee arithmetic (published schedules, not my measurement)

This is the part that decides the class, and it is arithmetic rather than a backtest result:

```text
Kalshi:     fee = ceil( M × 0.07 × C × P × (1 − P) )
Polymarket: fee = C × θ × P × (1 − P),  θ ≈ 0.04–0.07 by category
```

| Contract price | Fee per 100 contracts | **Fee as % of stake** |
|---|---:|---:|
| 10¢ | $0.63 | **6.3%** |
| 25¢ | $1.32 | **5.3%** |
| 50¢ | $1.75 | **3.5%** |
| 75¢ | $1.32 | **1.8%** |
| 90¢ | $0.63 | **0.7%** |

`P × (1 − P)` peaks at a coin flip, so the taker fee is **largest exactly where a forecaster believes
they have the most edge**, and it is symmetric: being right at 30¢ costs the same as being right at 70¢.

**Breakeven as a taker at 50¢ requires >3.5% of stake of edge on a single binary event.** A genuine
2-point calibration edge on a 50¢ contract is *below the fee*. This single line explains most of the
"no winners" result, and no signal design can be evaluated without it.

---

## 4. The rule that is worth specifying

```text
Pre-registered hypothesis:
    For contracts priced 0.85 <= P <= 0.95 in category C,
    the empirical settlement frequency exceeds P by >= 3 percentage points
    after fees, measured on >= 200 resolved contracts.

Entry:   MAKER order only (fee = 0, plus 15-25% rebate on Polymarket; 0 multiplier on Kalshi)
Size:    fixed fraction of bankroll; no averaging into a losing position (no stop exists)
Exit:    none. Contracts settle. The only exits are (a) sell before resolution to a maker, or (b) hold to $0/$1.
Resolve: settlement price, not TP/SL.
Gate:    calibration slope > 1 and Brier score better than the market's implied probability.
```

**Makers only.** Every structurally profitable prediction-market operation is a market-making operation,
not a forecasting one — Polymarket charges makers zero and rebates 15–25%; Kalshi's maker multiplier
defaults to 0. A taker strategy pays 3.5–6.3% of stake per position, which is a dozen times a liquid
equity round trip.

---

## 5. What was measured

**Nothing.** No settlement data exists in a form that permits a calibration curve, because the class
does not exist (Reason 1) and binary settlement is not representable (Reason 2).

I am flagging this as the single most valuable measurement the repo could add: recording
`(price_at_entry, settled_outcome, timestamp)` per contract would let a Brier score and a calibration
curve be computed for the first time. That is a data-capture task, not a strategy task, and it is the
precondition for everything else in this file.

---

## 6. Elimination (for now)

Eliminated as a **trading venue** while retained as a **data source**: with taker fees at 3.5–6.3% of
stake, a forecasting edge must be unusually large to survive, and the infrastructure required to be a
maker on these venues does not exist here. Prediction markets are a probability oracle before they are a
trading venue.

Recorded in `ELIMINATION_LOG.md` §3 with the exact re-admission condition.
