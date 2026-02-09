"""
Transaction Cost Model

Realistic cost modeling including commissions, slippage, spread, borrow costs.
"Many 'edges' vanish here" — this is the reality check.
"""
from dataclasses import dataclass
from typing import Optional

import numpy as np


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
