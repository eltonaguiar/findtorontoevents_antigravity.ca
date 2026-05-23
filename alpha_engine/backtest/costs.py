"""
Transaction Cost Model

Realistic cost modeling including commissions, slippage, spread, borrow costs.
"Many 'edges' vanish here" — this is the reality check.

Crypto model based on:
- Talos TMI (sigmoid-adjusted sqrt, 50k+ orders validated)
- Amberdata temporal liquidity (BTC/FDUSD Binance, 2024-2025)
- Binance fee schedules 2025-2026
- Almgren-Chriss optimal execution framework
"""
from dataclasses import dataclass
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Time-of-day slippage multipliers (Amberdata 2024-2025, BTC/FDUSD Binance)
# Peak liquidity 11 UTC ($3.86M within 10bps), trough 21 UTC ($2.71M)
# ---------------------------------------------------------------------------
_TOD_MULTIPLIER = {
    0: 1.08, 1: 1.08, 2: 1.08, 3: 1.10, 4: 1.10,
    5: 1.08, 6: 1.05, 7: 1.03, 8: 1.00, 9: 0.95,
    10: 0.93, 11: 0.90, 12: 0.93, 13: 0.95, 14: 0.98,
    15: 1.00, 16: 1.05, 17: 1.08, 18: 1.12, 19: 1.15,
    20: 1.20, 21: 1.42, 22: 1.35, 23: 1.20,
}


def time_of_day_slippage_multiplier(hour_utc: int) -> float:
    """Empirical liquidity multiplier by hour (Amberdata 2024).

    A trade costing 3 bps at 11:00 UTC costs ~5 bps at 21:00 UTC.
    Monday 21:00 is worst ($2.36M depth), Saturday 17:00 is best ($4.43M).
    """
    return _TOD_MULTIPLIER.get(hour_utc % 24, 1.10)


@dataclass
class CostModel:
    """
    Comprehensive transaction cost model.

    Includes:
    - Commission (per share or per trade)
    - Slippage (market impact)
    - Spread cost (bid-ask)
    - Borrow cost (for shorts)
    - Exchange fees
    """
    commission_per_share: float = 0.005    # $0.005/share (IB-style)
    min_commission: float = 1.00           # $1.00 minimum
    slippage_bps: float = 10               # 10 bps = 0.10%
    spread_bps: float = 5                  # 5 bps estimated half-spread
    borrow_cost_annual_bps: float = 50     # 50 bps/year for shorts
    exchange_fee_per_share: float = 0.003  # Exchange/ECN fees

    # Questrade-specific
    questrade_mode: bool = False
    forex_fee_pct: float = 0.0175          # 1.75% for USD trades (Questrade)
    ecn_fee: float = 0.0035               # ECN fee per share

    def compute_entry_cost(
        self,
        price: float,
        shares: int,
        is_short: bool = False,
    ) -> float:
        """
        Compute total cost for entering a position.
        
        Returns total dollar cost (always positive).
        """
        # Commission
        commission = max(shares * self.commission_per_share, self.min_commission)

        # Slippage (market impact)
        slippage = price * shares * (self.slippage_bps / 10000)

        # Half-spread cost
        spread = price * shares * (self.spread_bps / 10000)

        # Exchange fees
        exchange = shares * self.exchange_fee_per_share

        # Questrade forex fee
        forex = 0
        if self.questrade_mode:
            forex = price * shares * self.forex_fee_pct
            exchange = shares * self.ecn_fee

        total = commission + slippage + spread + exchange + forex
        return total

    def compute_exit_cost(
        self,
        price: float,
        shares: int,
        is_short: bool = False,
        holding_days: int = 0,
    ) -> float:
        """
        Compute total cost for exiting a position.
        Includes borrow cost for shorts.
        """
        # Same base costs as entry
        base_cost = self.compute_entry_cost(price, shares, is_short)

        # Add borrow cost for shorts
        borrow = 0
        if is_short and holding_days > 0:
            annual_borrow = price * shares * (self.borrow_cost_annual_bps / 10000)
            borrow = annual_borrow * (holding_days / 365)

        return base_cost + borrow

    def compute_round_trip_cost(
        self,
        entry_price: float,
        exit_price: float,
        shares: int,
        is_short: bool = False,
        holding_days: int = 0,
    ) -> float:
        """Compute total round-trip cost."""
        entry_cost = self.compute_entry_cost(entry_price, shares, is_short)
        exit_cost = self.compute_exit_cost(exit_price, shares, is_short, holding_days)
        return entry_cost + exit_cost

    def compute_cost_as_pct(
        self,
        price: float,
        shares: int,
        is_short: bool = False,
        holding_days: int = 0,
    ) -> float:
        """Compute round-trip cost as percentage of position value."""
        position_value = price * shares
        if position_value <= 0:
            return 0
        total_cost = self.compute_round_trip_cost(price, price, shares, is_short, holding_days)
        return total_cost / position_value

    def effective_entry_price(self, price: float, shares: int, is_long: bool = True) -> float:
        """Get effective entry price including slippage."""
        slip = price * (self.slippage_bps / 10000)
        spread = price * (self.spread_bps / 10000)
        if is_long:
            return price + slip + spread
        else:
            return price - slip - spread

    def effective_exit_price(self, price: float, shares: int, is_long: bool = True) -> float:
        """Get effective exit price including slippage."""
        slip = price * (self.slippage_bps / 10000)
        spread = price * (self.spread_bps / 10000)
        if is_long:
            return price - slip - spread
        else:
            return price + slip + spread

    @classmethod
    def zero_cost(cls) -> "CostModel":
        """Zero-cost model for idealized backtests."""
        return cls(commission_per_share=0, min_commission=0, slippage_bps=0,
                   spread_bps=0, borrow_cost_annual_bps=0, exchange_fee_per_share=0)

    @classmethod
    def questrade_canada(cls) -> "CostModel":
        """Questrade Canada cost model."""
        return cls(
            commission_per_share=0, min_commission=0,
            slippage_bps=10, spread_bps=5,
            questrade_mode=True, forex_fee_pct=0.0175, ecn_fee=0.0035,
        )

    @classmethod
    def interactive_brokers(cls) -> "CostModel":
        """Interactive Brokers cost model."""
        return cls(
            commission_per_share=0.005, min_commission=1.00,
            slippage_bps=5, spread_bps=3,
            exchange_fee_per_share=0.003,
        )


# ============================================================================
# Crypto-specific cost model
# ============================================================================

@dataclass
class CryptoCostModel:
    """
    Realistic crypto transaction cost model.

    Slippage model based on Talos TMI (sigmoid-adjusted square root),
    validated on 50,000+ parent orders. Fee schedules from Binance 2025.

    Empirical slippage by order size (BTC/USDT, Binance, normal vol):
        $1k   -> <1 bps
        $10k  -> 1-2 bps
        $100k -> 3-8 bps
        $1M   -> 10-25 bps

    Ignoring slippage inflates backtest Sharpe by 25-50% for medium-frequency
    strategies and can make high-frequency Sharpe go from 3.0 to negative.
    """

    # Fee tier (Binance regular with BNB discount by default)
    maker_fee_pct: float = 0.075     # 7.5 bps (10 bps - 25% BNB discount)
    taker_fee_pct: float = 0.075     # 7.5 bps
    use_bnb_discount: bool = True

    # Funding (for perpetual futures)
    funding_rate_8h_pct: float = 0.01   # 0.01% per 8h = 1 bps
    funding_intervals_per_day: int = 3

    # Slippage model parameters
    slippage_model: str = "sqrt"   # "fixed", "linear", "sqrt"
    fixed_slippage_bps: float = 5.0
    base_volatility: float = 0.02  # 2% daily vol baseline for normalization

    # Spread
    half_spread_bps: float = 2.0   # ~2 bps half-spread for BTC/USDT on Binance

    def compute_slippage_bps(
        self,
        order_size_usd: float,
        daily_volume_usd: float,
        daily_volatility: float = 0.03,
        hour_utc: int = 12,
    ) -> float:
        """
        Estimate slippage in basis points using sigmoid-adjusted sqrt model.

        Based on Talos TMI and Almgren-Chriss:
            Impact = sigma * sqrt(Q / V) * adjustment_factor

        Parameters
        ----------
        order_size_usd : float
            Dollar value of the order.
        daily_volume_usd : float
            Average daily trading volume for the pair.
        daily_volatility : float
            Daily price volatility (e.g. 0.03 = 3%).
        hour_utc : int
            Hour of execution (0-23 UTC) for time-of-day adjustment.
        """
        if self.slippage_model == "fixed":
            return self.fixed_slippage_bps

        if daily_volume_usd <= 0:
            return 100.0  # Illiquid asset, assume 1% slippage

        participation = order_size_usd / daily_volume_usd

        if self.slippage_model == "linear":
            return participation * 10000 * 0.1  # 10% of participation rate

        # ---- Square root model (default) ----
        # Base: Almgren-Chriss sqrt law
        base_impact_bps = daily_volatility * np.sqrt(participation) * 10000

        # Sigmoid adjustment for low participation rates (Talos TMI finding:
        # pure sqrt underestimates by ~4 bps at participation < 0.5%)
        log_part = np.log10(max(participation, 1e-12))
        sigmoid_adj = 1.0 + 0.5 / (1.0 + np.exp(-(log_part + 5)))

        # Time-of-day adjustment (Amberdata empirical)
        tod_mult = time_of_day_slippage_multiplier(hour_utc)

        # Volatility regime scaling (high vol = more slippage)
        vol_mult = max(1.0, daily_volatility / self.base_volatility)

        impact_bps = base_impact_bps * sigmoid_adj * tod_mult * vol_mult

        # Add half-spread
        total = impact_bps + self.half_spread_bps

        # Floor at 0.5 bps (even tiny orders cross some spread)
        return max(total, 0.5)

    def compute_fee_bps(self, is_maker: bool = False) -> float:
        """Trading fee in basis points for one side."""
        fee_pct = self.maker_fee_pct if is_maker else self.taker_fee_pct
        return fee_pct * 100  # Convert percent to bps

    def compute_funding_bps(self, holding_days: float) -> float:
        """Cumulative funding cost in bps for perpetual futures."""
        return (self.funding_rate_8h_pct
                * self.funding_intervals_per_day
                * holding_days
                * 100)  # Convert % to bps

    def total_round_trip_bps(
        self,
        order_size_usd: float,
        daily_volume_usd: float,
        is_maker: bool = False,
        holding_days: float = 0,
        daily_volatility: float = 0.03,
        hour_utc: int = 12,
    ) -> float:
        """
        Total round-trip cost in basis points.

        Components: 2x fee + 2x slippage + funding.

        Three-tier benchmarks (HyperQuant Research):
            Conservative: ~50 bps round trip
            Moderate:     ~30 bps round trip
            Optimistic:   ~15 bps round trip
        """
        fee_bps = self.compute_fee_bps(is_maker)
        slip_bps = self.compute_slippage_bps(
            order_size_usd, daily_volume_usd, daily_volatility, hour_utc)
        funding_bps = self.compute_funding_bps(holding_days)

        return 2 * fee_bps + 2 * slip_bps + funding_bps

    def total_round_trip_pct(self, **kwargs) -> float:
        """Total round-trip cost as a percentage."""
        return self.total_round_trip_bps(**kwargs) / 10000

    def net_return(
        self,
        gross_return_pct: float,
        order_size_usd: float,
        daily_volume_usd: float,
        **kwargs,
    ) -> float:
        """Compute net return after all costs."""
        cost_pct = self.total_round_trip_pct(
            order_size_usd=order_size_usd,
            daily_volume_usd=daily_volume_usd,
            **kwargs,
        )
        return gross_return_pct - cost_pct * 100  # Both in %

    def sharpe_haircut_factor(self, trades_per_day: float) -> float:
        """
        Estimated Sharpe ratio degradation factor from costs.

        Empirical benchmarks:
            100+ trades/day  -> Sharpe * 0.0 to 0.3
            1-10 trades/day  -> Sharpe * 0.5 to 0.7
            1-5 trades/week  -> Sharpe * 0.8 to 0.93
            1-2 trades/month -> Sharpe * 0.85 to 0.95
        """
        if trades_per_day >= 100:
            return 0.15
        elif trades_per_day >= 10:
            return 0.40
        elif trades_per_day >= 1:
            return 0.60
        elif trades_per_day >= 0.2:  # ~1/week
            return 0.80
        else:
            return 0.90

    # ---- Factory methods ----

    @classmethod
    def binance_spot_regular(cls) -> "CryptoCostModel":
        """Binance spot, regular tier, BNB discount."""
        return cls(maker_fee_pct=0.075, taker_fee_pct=0.075)

    @classmethod
    def binance_spot_vip3(cls) -> "CryptoCostModel":
        """Binance spot VIP 3 ($20M+ 30d volume)."""
        return cls(maker_fee_pct=0.042, taker_fee_pct=0.060)

    @classmethod
    def binance_futures_regular(cls) -> "CryptoCostModel":
        """Binance USD-M futures, regular tier."""
        return cls(maker_fee_pct=0.020, taker_fee_pct=0.050)

    @classmethod
    def conservative(cls) -> "CryptoCostModel":
        """Conservative cost assumptions (worst case). ~50 bps RT."""
        return cls(
            maker_fee_pct=0.10, taker_fee_pct=0.10,
            use_bnb_discount=False,
            fixed_slippage_bps=10.0, slippage_model="fixed",
            funding_rate_8h_pct=0.02,
        )

    @classmethod
    def optimistic(cls) -> "CryptoCostModel":
        """Optimistic cost assumptions (best case). ~15 bps RT."""
        return cls(
            maker_fee_pct=0.02, taker_fee_pct=0.04,
            fixed_slippage_bps=2.0, slippage_model="fixed",
            funding_rate_8h_pct=0.005,
        )
