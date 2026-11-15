# Why prediction-market & signal copy-trading still loses (Kalshi / Polymarket / crypto)

**Question the user asked:** "We had prediction markets like Kalshi/Polymarket… and yet
despite copy-trading attempts we STILL don't have winners… why!!"

Short answer: **copy-trading copies the *published* result, not the *edge*.** The published
result is a sample that was selected, delayed, and cost-loaded between the winner's
decision and your fill. Below is the structural breakdown, each reason labeled as
provable arithmetic vs probabilistic argument. (SubQ consultation + fact-check in `../subq/`.)

---

## The seven structural reasons

### 1. Adverse selection of *who publishes* — probabilistic, near-certain in aggregate
The traders visible enough to be copied are selected by **recent wins** (survivorship +
recency). Copying = buying the tail of a hot streak. Base rate: most short-horizon winners
are variance, not skill; with thousands of traders, a leader with a 10-trade win streak has
~zero probability under a fair coin but many candidates by construction (multiple testing
across the leaderboard itself). You copy rank #1 *because* of the streak, which is precisely
the property that regresses.

### 2. Latency & slippage between their fill and yours — provable arithmetic
Prediction markets: their order sits at the ask; when the copy signal lands, the book has
moved — you buy **after** the price move that made the trade look good. Crypto signals:
same, worse at news times. If the edge per trade is e.g. 1–2¢ on a 30¢ contract and you
pay +1–2¢ delay slippage, **most or all of the edge is gone before trade #1**. This is
directly measurable: log their fill timestamp vs yours; we have seen exactly this pattern
in this repo's own copy-trader (entries recorded after the candle that produced the signal).

### 3. Spread, fees, and resolution friction — provable arithmetic
Kalshi charges per-contract fees; Polymarket has spread + (on some markets) gas/relay
costs; crypto copy has taker fees + spread. Round-trip cost on a $0.50 contract at 1¢ fee
+ 1¢ spread = **4% of notional per round trip** — vs ~0.1–0.3% for an equity ETF trade.
Any copied edge must first clear a 10–100× higher cost bar than equity strategies.

### 4. Quote-vs-resolution mismatch — probabilistic (measurable)
You often cannot exit at the winner's exit: they may hold to resolution (getting paid by
the long-shot payoff structure) while you panic-sell at 0.42 into a scare. **Different
payoff function = different strategy**, even with identical entries. Our own audit lesson
applies: `exit_reason` vs `exit_price` mismatch (B4) showed rows whose recorded exit never
traded — copy-trading multiplies that problem because the copier's exit is reconstructed,
not executed.

### 5. Small-n resolution randomness — probabilistic (quantifiable)
Prediction markets resolve binary events; a 60% win-rate strategy on $1 contracts has
per-trade σ of $0.49. n=30 trades → σ of win rate ≈ 8.9pp — **the 95% CI on a 60% hit rate
after 30 trades is roughly ±17pp**. You cannot distinguish a 60% winner from a 50% coin at
that n. Leaders after 20–50 trades are statistically indistinguishable from luck; you would
need n≥200+ to confirm (and the leader will have stopped/been banned by then — see #6).

### 6. Winner non-stationarity — probabilistic, structurally guaranteed
The copied account **changes or disappears** precisely when it would be most valuable:
- edge decays once volume follows it (self-defeating: see #7);
- winners scale, get bored, or stop publishing;
- market-makers adapt to visible flow;
- accounts get limited/banned (prediction markets restrict winners; Kalshi/Polymarket
  resolve and delist markets continuously);
- regime change: the hot streak was one regime (e.g., 2021 trending crypto, 2024
  election books); your copy begins after it ends.
So the track record you copied is, by construction, a *backward* sample of a process that
no longer exists.

### 7. Self-defeating volume — probabilistic (game-theoretic)
If copying worked, AUM follows the leader, the leader's edge shrinks (their entry price is
now *your* entry price), and the leaderboard rotates. Any "proven" public copy service that
scales is a service whose returns must decay — the only stable copy edges are ones too small
or too capacity-constrained to publish.

---

## What would make copy-trading viable (if you still want to try it)

1. **Copy at decision time, not result time**: API-level order mirroring with <1s latency,
   paper first. Log their-fill-vs-your-fill basis for 100 trades; require basis < 20% of
   claimed edge.
2. **Cost-in-the-loop**: recompute every copied trade with YOUR fees/spread. Gate: net PF ≥ 1.3.
3. **n≥100 with Wilson CI** on the leader before following, and require their edge is
   measured vs *their* benchmark, not vs 0.
4. **Regime-robustness**: leader must be profitable across at least 2 distinct regimes.
5. **Exit parity**: you must be able to exit when they exit (or don't copy).
6. **Prediction markets specifically**: trade your OWN pre-registered models on a small set
   of markets you understand deeply (that's a forecasting edge), rather than mirroring
   strangers — the honest edge in prediction markets is research depth on a narrow domain,
   not leaderboard copying.

## The uncomfortable generalization (why this repo also fails at "copy")

This repo's copy-trader paths failed for the same reasons: entry-after-the-move (basis),
costs not in the PnL (0% fill convention), and selection on past winners (copy-trading
`elite PF 2.3–4` historical strategies). **Copy-trading is a strategy like any other —
it must clear the same gates: pre-registered, cost-adjusted, forward paper-traded,
benchmark-relative.** It has not.

---
*Fact-check status: reasons 1–7 are standard market-microstructure/multiple-testing
arguments; SubQ's independent take and my grounding verdicts are in `../subq/factcheck.md`.
Specific numeric CI examples above are computed, not quoted (Wilson/normal approx shown).*
