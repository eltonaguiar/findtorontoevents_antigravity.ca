# Prediction Markets — Why There Are Still No Winners

**Date:** 2026-11-15 · **Author:** Buffy · **For:** `2026-11-15_1233AM_winning-strategies/buffy/`

You have Polymarket and Kalshi ingestion and copy-trading attempts, and zero winners. This is not bad
luck. There are **six distinct reasons**, and the first is a structural bug in this repo rather than a
market problem.

---

## Reason 1 — There is no prediction-market class, so nothing is ever verdicted

The live ledger contains exactly these asset classes:

```
CRYPTO 5584 · EQUITY 933 · ETF 616 · FOREX 472 · COMMODITY 54 · BOND 47 · FUTURES 15 · SPORTS 2
```

**No `PREDICTION` class. None.** When I trace pick-shaped rows that come from `pm_kalshi_signals` or
`prediction_market_consensus`, they are tagged **CRYPTO** — 32 of them. A BTC price-range contract gets
filed as a crypto directional pick.

Consequence: PM outcomes are aggregated into CRYPTO's PF, where they are invisible, and **the system has
never once computed a win rate for prediction markets.** It cannot learn. You cannot find winners in a
class you do not record.

*Fix:* a `PREDICTION` asset class with its own resolver path (`settle_at_0_or_1`, not TP/SL), or an
explicit `pm_*` category excluded from CRYPTO aggregates.

---

## Reason 2 — Binary contracts have no TP/SL, so the existing resolver cannot represent them

A prediction contract settles at **$1 or $0**. There is no "take profit at 1.5 ATR". The resolver's
entire model — entry, TP, SL, TIME_EXIT, pnl_pct — maps onto a continuous instrument. Forced onto a
binary it produces exactly the pathology already in the ledger: a "closed" row with `exit_price ==
entry_price`.

That is very likely why PM rows show up as zero-pnl closes and vanish from any verdict. **Reason 2 is a
direct consequence of Reason 1.**

---

## Reason 3 — The fee is highest exactly where the edge is claimed

Kalshi's published formula (fee schedule effective 7 July 2026):

```
fee = ceil( M × 0.07 × C × P × (1 − P) )
```

Polymarket uses the same shape: `fee = C × θ × P × (1 − P)`, with θ ≈ 0.04–0.07 by category, and
Polymarket US raising θ from 0.05 → 0.06 → 0.0695 during 2026.

What that means per contract, as a share of what you stake:

| Price | Fee per 100 contracts | **Fee as % of stake** |
|---|---|---|
| 10¢ | $0.63 | **6.3%** |
| 25¢ | $1.32 | **5.3%** |
| 50¢ | $1.75 | **3.5%** |
| 75¢ | $1.32 | **1.8%** |
| 90¢ | $0.63 | **0.7%** |

**P × (1 − P) peaks at a coin flip.** So the taker fee is *largest* precisely where a forecaster believes
they have the most edge, and it is symmetric — being right at 30¢ pays the same fee as being right at 70¢.

To break even as a taker at 50¢ you need **>3.5% of stake** in edge on a single binary event. A genuine
forecasting edge of 2 percentage points on a 50¢ contract is *below the fee*. This one line explains
most of the "no winners" result.

---

## Reason 4 — Copy trading pays the taker fee twice and arrives late

Mirroring a wallet means:
1. The leader takes liquidity → **they** pay the taker fee (or they were a maker and you can't).
2. You take liquidity to mirror → **you** pay the taker fee again.
3. Your fill is at the *post-leader* price. If the leader's trade was informative, the price already moved
   against you by a fraction of their edge.
4. Because fees peak at 50¢, a leader trading near-even markets is trading in the most expensive zone.

So copying is: **−2 fees − slippage + a fraction of someone else's edge.** It is structurally negative
unless the leader's edge is large and slow-moving — and large, slow-moving edges in prediction markets
are exactly the ones that get arbitraged first.

**Makers are the exception:** Polymarket charges makers **zero** and pays 15–25% rebates; Kalshi's maker
multiplier defaults to 0. Every profitable PM operation is a market-making operation, not a forecasting
one.

---

## Reason 5 — Leaderboards rank PnL, not skill, and are survivorship-biased

Polymarket's leaderboard sorts by raw PnL. In a binary market the top of that list is routinely one
person who held a long-shot to resolution. That is a lottery outcome with a 6.3%-of-stake fee attached,
not a repeatable method.

To rank skill you need the things the leaderboard does not show: number of resolved positions, average
edge per position, max drawdown, and whether the PnL came from one event. Copy-trading a leaderboard
entry is copying a **selection**, not a **strategy**.

---

## Reason 6 — No settlement data means no calibration measurement

The one thing that *does* work in prediction markets is **calibration**: do events priced at 70¢ happen
70% of the time? That requires recording `(price_at_entry, settled_outcome, timestamp)` per contract.

This repo has `prediction_quality_tracker.py` and `verify_predictions.py`, but because PM rows never
reach a PREDICTION class (Reason 1), there is no calibration curve, no Brier score, and no way to know
whether the models are informative at all.

---

## What would actually make prediction markets viable here

| # | Action | Why |
|---|---|---|
| 1 | Add `PREDICTION` asset class + binary settlement resolver | Without it nothing is measured (Reasons 1–2) |
| 2 | Record Brier score + calibration curve per model | This is the only real edge metric for forecasters |
| 3 | **Trade as a maker**, never a taker | Maker fee = 0 + rebate; taker fee = 3.5–6.3% of stake |
| 4 | Restrict to 85–95¢ favourites *as a maker* | Fee 0.7% of stake, but only if you can earn the spread |
| 5 | Stop copying wallets; copy **methodologies** | Reason 5 |
| 6 | Pre-register: "a 3pp calibration edge at ≥100 contracts beats fees" | Forces the fee math into the hypothesis |

**The honest expectation:** with taker fees of 3.5–6.3% of stake, a forecasting edge must be *unusually
large* to survive. Market making is the only structurally sound path, and it requires infrastructure this
repo does not have. **Prediction markets are a data source (a probability oracle) before they are a
trading venue.**

---

## Answers to "why still no winners" in one paragraph

Because there is no prediction-market class in the ledger, so outcomes are filed as CRYPTO and never
verdicted; because binary settlement has no TP/SL so the resolver writes flat closes; because the taker
fee is 3.5% of stake at 50¢ and 6.3% at 10¢, peaking exactly where edge is claimed; because copying pays
that fee twice and arrives after the leader's fill; because leaderboards rank one lucky long-shot as
skill; and because without settlement data there is no calibration curve to tell you whether any of the
models are informative. **No verdict, no calibration, and a fee curve that eats small edges — that is
the whole story.**
