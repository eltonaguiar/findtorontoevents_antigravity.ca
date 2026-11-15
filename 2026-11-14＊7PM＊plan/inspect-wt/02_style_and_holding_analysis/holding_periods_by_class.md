# Holding period × trading style analysis, per asset class

> The question: for each class, which style (long-term / short-term / swing / day trading /
> scalping) is structurally viable, and why. The organizing principle is **cost-to-horizon
> ratio**: a style works only when the expected move per holding period comfortably exceeds
> the round-trip cost of that period. Cost numbers below are order-of-magnitude retail
> benchmarks (measure your own before believing them — QA Gate: fill model per class).

## The cost-to-horizon table (the arithmetic that decides everything)

| Style | Holding period | Typical round-trip cost (retail) | Move needed to profit (≈ 2-3× cost) | Structurally viable only where cost ≈ 0 |
|---|---|---|---|---|
| Scalping | seconds–minutes | 0.05–0.20% (spread+fee) | 0.15–0.6% per trade | **Nowhere retail** (HFT/market-making owns this — SubQ evidence: mkmaking 4.57/5, capacity-tested) |
| Day trading | intraday, flat by close | 0.05–0.15% | 0.15–0.45% | Liquid futures/ETFs *if* edge is real; mostly cost-dominated |
| Swing | 1–10 days | same per trade | 0.15–0.45% per swing | **Equity/ETF/crypto** (the practical retail battlefield) |
| Short-term position | 1–6 weeks | same | per-trade move grows with horizon | Futures/forex trend, crypto trend |
| Long-term / monthly | weeks–months | 0.05–0.10% + fund ER 0.03–0.20% | horizon move 5–30% | **MF/ETF/bond allocation** — cost becomes noise |

Key insight: **mutual funds' NAV clock isn't a bug for long-term — it's free cost filtering.**
You cannot scalp a fund, so the class can only be evaluated on the horizon where costs
disappear into the return stream. That's why the user's MF conviction is *structurally*
compatible with the class's mechanics.

## Per-class verdicts (grounded in our own measured data + SubQ)

| Class | Viable style(s) | Dead styles (and why measured) | Notes |
|---|---|---|---|
| **CRYPTO** | position (1–5d), swing | scalping/day (funding+fee+slippage: measured stop-fill overshoot ate ~98.8% of class loss pre-fix); long-term = just hold BTC (benchmark objection) | SubQ style: longterm 0.49 / position 0.42 — split; our fill data says the *tradeable* horizon is days+ |
| **EQUITY** | swing (1–5d) | day (PDT rule + costs vs 0.10% edge), scalping | Cost margin measured at 3.23× — swing fits; RSI(2)-class trial in `equity.md` |
| **COMMODITY/FUTURES** | position (weeks–months) — CTA style | scalping (retail latency), day (competition with HFT) | Trend's win signature (few big winners) requires holding through weeks; SubQ: position 0.56 |
| **ETF** | swing + monthly allocation | scalping (spread eats the edge on thin sector ETFs) | daily NAV + deep books make swing clean |
| **BOND** | long-term / monthly | day/scalping/swing (bonds move in *basis points*; retail cost > daily range) | SubQ: longterm 0.77, conf 0.69 — strongest style agreement of any class |
| **FOREX** | position (days–weeks) *if* any edge survives costs | day/scalping (spread is per-pip: 1–2 pip spread on a 10–20 pip daily range = 5–15% tax on the move) | SubQ: position 0.53; our PF 0.27 history says even position fails today |
| **MUTUAL FUNDS** | **long-term / monthly only** (structurally enforced: NAV once daily, T+1/T+2, 30-day rule) | everything intraday — impossible, not just unprofitable | SubQ: longterm 0.86, conf 0.81 — highest-confidence style call in the set |

## The uncomfortable pattern (why day trading/scalping keeps failing here)
Every "elite PF 2.3–4" snapshot in this repo's history was measured at horizons where
**our own fill model didn't exist**. The moment fills were measured (crypto) the class
loss turned out to be ~fill overshoot. Day/scalping claims should be treated as
*unfalsifiable until the fill model exists for that class* — that is the honest order:
**fills → costs → horizon → edge**, never edge first.

## Recommendation (style allocation across the whole book)
1. **Core (capital):** monthly MF/ETF allocation sleeve — long-term style only.
2. **Alpha research:** swing (equity trial) + position (crypto/commodity trials) —
   exactly the two styles whose cost-to-horizon ratios are defensible at retail size.
3. **Explicitly banned until proven:** scalping everywhere; day trading in forex/MF/ETF.
   A ban written down now prevents the next agent from rediscovering it expensively.
