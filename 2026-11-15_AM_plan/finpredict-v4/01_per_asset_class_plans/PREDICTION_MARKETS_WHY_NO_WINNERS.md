# Prediction Markets — Why Copy Trading Keeps Failing (Kalshi/Polymarket)

**Date:** 2026-11-15 (AM)

---

## The structural reasons (not just "bad implementation")

1. **Zero-sum + fees.** Prediction markets are net-negative-sum for traders once fees/spread are charged. A strategy must beat the *fee drag* before it profits. Copying a winner does not escape this.

2. **Bot / adverse-selection dominance.** The most active participants are fast, informed bots. A retail copy-trader is the *liquidity provider* — systematically on the wrong side. You are not copying "edge"; you are providing the edge to the bots.

3. **Size mismatch.** The trader you copy may size in a way that moves the market or exploits micro-latency. Your copy executes slower and at a different price — the copied edge does not transfer.

4. **Contrarian / crowd bias.** Prediction-market prices already reflect a crowd consensus. Unless you have a *different, grounded* information source, you are betting against the consensus with no edge.

5. **No price-discovery edge in retail.** The edge in these markets belongs to those with superior information or speed. A retail system that just mirrors signals has neither.

---

## The fix (if pursued)

- Treat prediction markets as a **separate, zero-sum research problem** — not a copy-trading feed.
- Require a grounded information edge (e.g., event-specific data, a real model) that other participants lack.
- Price in fees + spread + slippage; compare to buy-and-hold (which in these markets is ~nothing — so the bar is genuinely high).
- Pre-register a hypothesis and run a 90-day paper track like any other class.

---

## Verdict

**Prediction-market copy trading is structurally unlikely to produce winners.** It fails for the same reason most day-trading fails: you are the un-advantaged counterparty. Do not allocate capital here until a genuine, grounded, pre-registered edge is demonstrated.
