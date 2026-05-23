"""Three textbook bond strategies seeded into P3 for v1 end-to-end test.

Citations (verifiable via P1 swarm in next iteration):

1. **Curve momentum** — Cochrane & Piazzesi (2005) "Bond Risk Premia",
   American Economic Review 95(1). Tent-shaped forward-rate factor predicts
   bond excess returns. Simplified to 10y-2y slope momentum here.

2. **TIPS breakeven mean-reversion** — Fleckenstein, Longstaff, Lustig (2014)
   "The TIPS-Treasury Bond Puzzle", Journal of Finance 69(5). Breakeven
   inflation exhibits mean-reversion vs survey expectations; trade
   deviations from 5y rolling mean.

3. **IG credit carry vs vol** — Frazzini & Pedersen (2014) "Betting Against
   Beta", Journal of Financial Economics 111(1). Long low-vol IG, short
   high-vol IG, rebalanced monthly.

All three are EXPECTED to live in P3 first as proof the harness wires
end-to-end. The P1+P2 swarm will replace them with engine-proposed
candidates in subsequent runs.
"""

from __future__ import annotations

from .schemas import StrategySpec


def get_textbook_specs() -> list[StrategySpec]:
    return [
        StrategySpec(
            spec_id="bond_curve_momentum_v1",
            asset_class="BOND",
            entry=(
                "long when 12m change in (10y - 2y) slope > 0 AND "
                "12m realized term-premium positive"
            ),
            exit="reverse on slope sign flip OR 6m hold",
            sizing="risk-parity to 10% annualized vol",
            universe=["IEF", "TLT", "SHY", "IEI"],
            regime_filter="exclude QE/QT transition windows (Fed minutes flag)",
            source_refs=[
                "https://www.aeaweb.org/articles?id=10.1257/0002828053828581"
            ],
            proposed_by_engine="textbook_seed",
        ),
        StrategySpec(
            spec_id="bond_tips_breakeven_mr_v1",
            asset_class="BOND",
            entry=(
                "long TIP / short IEF when 10y breakeven inflation < "
                "5y rolling mean - 1σ"
            ),
            exit="exit when breakeven crosses 5y rolling mean OR 90d hold",
            sizing="duration-neutral pair, 5% portfolio risk",
            universe=["TIP", "IEF"],
            regime_filter="skip when MOVE index > 130 (high-vol regimes break mean reversion)",
            source_refs=[
                "https://doi.org/10.1111/jofi.12188"
            ],
            proposed_by_engine="textbook_seed",
        ),
        StrategySpec(
            spec_id="bond_ig_carry_low_vol_v1",
            asset_class="BOND",
            entry=(
                "long bottom-quartile 60d-vol IG bonds, short top-quartile, "
                "rebalanced monthly"
            ),
            exit="monthly rebalance OR vol-quartile flip",
            sizing="dollar-neutral, leverage to 8% portfolio vol",
            universe=["LQD", "VCIT", "VCSH", "HYG"],
            regime_filter="reduce leverage 50% when VIX > 25",
            source_refs=[
                "https://doi.org/10.1016/j.jfineco.2013.10.005"
            ],
            proposed_by_engine="textbook_seed",
        ),
    ]
