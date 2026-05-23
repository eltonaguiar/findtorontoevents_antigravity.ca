You are an institutional quant strategist. We run a multi-asset systematic trading
system. Below is our current realized closed-trade performance per asset class
(post-noise-filter, verdict-grade numbers from asset_class_health):

- EQUITY:    PF 1.41 / WR 52.7% / n=421   (Tier-2 candidate)
- COMMODITY: PF 1.78 / WR 46.9% / n=750   (meets Tier-2 PF, low WR)
- BOND:      PF 1.72 / WR 55.6% / n=18    (meets Tier-2 PF+WR, n far below floor)
- CRYPTO:    PF 1.25 / WR 44.6% / n=8067  (sub-Tier-2 aggregate; elite sub-strategies
             PF 2.34-3.97 dragged by quan_engine 18% vol @ PF 0.70 and an unknown
             source 7% vol @ PF 0.35)
- ETF:       PF 1.24 / WR 55.2% / n=87    (borderline Tier-2)
- FOREX:     PF 0.27 / WR 46.4% / n=1169  (genuinely sub-floor)

Tier-2 minimum: PF > 1.5, WR > 50%, MDD < 20%. Tier-1 target: PF > 2, WR > 55%, MDD < 10%.

For EACH asset class (EQUITY, COMMODITY, BOND, CRYPTO, ETF, FOREX), recommend the
1-2 highest-edge institutional-grade strategy archetypes. For each archetype give:
1. Why it has a structural/behavioral edge.
2. Concrete signal construction: features, lookback, universe, rebalance cadence,
   position sizing.
3. The main failure mode and how institutions guard against it.
4. A realistic post-cost Sharpe / PF expectation.

Then give a consolidated capital-allocation recommendation: which classes to scale,
maintain, shrink, or kill, and why. Be quant-credible and concrete - no fluff.
