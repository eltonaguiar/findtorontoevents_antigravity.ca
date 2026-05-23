"""
Multi-Tier Stop-Loss System
=============================
Three-tier exit framework replacing the current single-level SL.

Current problem: The backtest engine uses a single fixed stop-loss (price * (1 - sl_pct)).
This doesn't trail, doesn't protect profits, and uses a fixed 90-day max hold for all strategies.

This module implements:
- Tier 1: Hard Stop (catastrophic protection, never moves)
- Tier 2: ATR Trailing Stop (ratchets up, locks profits)  
- Tier 3: Time-Based Exit (prevents capital lock-up)

Author: Forensic Audit Implementation (PR #72)
Date: 2026-04-11
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ─── Asset-Class Stop Configurations ──────────────────────────────────────────
# Derived from Kelly-optimal analysis in Section 5.2 of the audit report.

STOP_CONFIGS = {
    "crypto_1h": {
        "hard_stop_pct": 0.08,       # 8% max loss per position
        "trail_atr_mult": 2.0,       # Trailing stop at 2x ATR
        "trail_activation_pct": 0.02, # Start trailing after 2% profit
        "max_hold_bars": 24,          # 24 hours max hold
        "tp_atr_mult": 2.5,          # Take profit at 2.5x ATR
    },
    "crypto_4h": {
        "hard_stop_pct": 0.10,
        "trail_atr_mult": 2.5,
        "trail_activation_pct": 0.03,
        "max_hold_bars": 20,          # 80 hours (20 x 4h bars)
        "tp_atr_mult": 3.5,
    },
    "crypto_daily": {
        "hard_stop_pct": 0.12,
        "trail_atr_mult": 3.0,
        "trail_activation_pct": 0.05,
        "max_hold_bars": 30,          # 30 days
        "tp_atr_mult": 4.0,
    },
    "equity_swing": {
        "hard_stop_pct": 0.05,
        "trail_atr_mult": 1.5,
        "trail_activation_pct": 0.02,
        "max_hold_bars": 63,          # ~3 months
        "tp_atr_mult": 2.0,
    },
    "equity_rsi2": {
        # RSI-2 mean reversion uses signal-based exit (RSI > 65), not ATR
        "hard_stop_pct": 0.05,
        "trail_atr_mult": 1.0,       # Tight trail for mean reversion
        "trail_activation_pct": 0.01,
        "max_hold_bars": 10,          # 10 trading days max (Connors spec)
        "tp_atr_mult": 1.0,
    },
    "forex_carry": {
        "hard_stop_pct": 0.03,
        "trail_atr_mult": 2.5,
        "trail_activation_pct": 0.01,
        "max_hold_bars": 504,         # ~2 years at daily (carry trades are long-duration)
        "tp_atr_mult": None,          # No TP — hold for carry income
    },
    "commodity_trend": {
        "hard_stop_pct": 0.08,
        "trail_atr_mult": 2.0,
        "trail_activation_pct": 0.03,
        "max_hold_bars": 40,          # 40 bars
        "tp_atr_mult": 4.0,
    },
    "futures_tsmom": {
        "hard_stop_pct": 0.10,
        "trail_atr_mult": 2.5,
        "trail_activation_pct": 0.03,
        "max_hold_bars": 60,          # ~3 months at daily
        "tp_atr_mult": None,          # TSMOM holds until signal reverses
    },
    "bonds": {
        "hard_stop_pct": 0.03,
        "trail_atr_mult": 1.5,
        "trail_activation_pct": 0.005,
        "max_hold_bars": 252,         # ~1 year at daily
        "tp_atr_mult": None,          # Duration-based, not ATR-based
    },
}

# Default fallback
DEFAULT_CONFIG = STOP_CONFIGS["crypto_4h"]


@dataclass
class StopState:
    """Current state of the multi-tier stop system for one position."""
    ticker: str
    entry_price: float
    entry_atr: float
    config_name: str
    
    # Tier 1: Hard stop (set at entry, never moves)
    hard_stop: float = 0.0
    
    # Tier 2: Trailing stop
    trail_stop: float = 0.0
    trail_active: bool = False  # Only activates after trail_activation_pct profit
    highest_price: float = 0.0  # High-water mark for trailing
    
    # Tier 3: Time-based
    bars_held: int = 0
    max_hold_bars: int = 24
    
    # Take profit
    take_profit: float = 0.0  # 0 = no TP (hold until trail/time exit)
    
    # Metadata
    last_update_price: float = 0.0
    last_update_atr: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "ticker": self.ticker,
            "entry_price": self.entry_price,
            "hard_stop": self.hard_stop,
            "trail_stop": self.trail_stop,
            "trail_active": self.trail_active,
            "take_profit": self.take_profit,
            "bars_held": self.bars_held,
            "max_hold_bars": self.max_hold_bars,
            "highest_price": self.highest_price,
            "config": self.config_name,
        }


class MultiTierStopLoss:
    """
    Three-tier stop-loss manager.
    
    Manages stop-loss state for multiple positions simultaneously.
    Call update() each bar, check_exits() to get exit signals.
    
    Example:
        stops = MultiTierStopLoss()
        
        # On entry:
        stops.register_position("BTCUSDT", entry_price=60000, atr=1500, 
                               config_name="crypto_4h")
        
        # Each bar:
        exits = stops.update_all(current_prices, current_atrs)
        for exit in exits:
            execute_exit(exit["ticker"], exit["reason"], exit["price"])
        
        # On exit:
        stops.remove_position("BTCUSDT")
    """
    
    def __init__(self):
        self._positions: Dict[str, StopState] = {}
    
    def register_position(
        self,
        ticker: str,
        entry_price: float,
        atr: float,
        config_name: str = "crypto_4h",
        direction: int = 1,  # 1 = long, -1 = short
    ) -> StopState:
        """
        Register a new position with the stop-loss system.
        
        Args:
            ticker: Symbol/ticker
            entry_price: Entry price
            atr: Current ATR at entry
            config_name: Key into STOP_CONFIGS
            direction: 1 for long, -1 for short
            
        Returns:
            The initial StopState
        """
        config = STOP_CONFIGS.get(config_name, DEFAULT_CONFIG)
        
        if direction == 1:  # Long
            hard_stop = entry_price * (1 - config["hard_stop_pct"])
            trail_stop = entry_price - config["trail_atr_mult"] * atr
            tp_mult = config.get("tp_atr_mult")
            take_profit = entry_price + tp_mult * atr if tp_mult else 0.0
        else:  # Short
            hard_stop = entry_price * (1 + config["hard_stop_pct"])
            trail_stop = entry_price + config["trail_atr_mult"] * atr
            tp_mult = config.get("tp_atr_mult")
            take_profit = entry_price - tp_mult * atr if tp_mult else 0.0
        
        state = StopState(
            ticker=ticker,
            entry_price=entry_price,
            entry_atr=atr,
            config_name=config_name,
            hard_stop=hard_stop,
            trail_stop=trail_stop,
            trail_active=False,
            highest_price=entry_price,
            bars_held=0,
            max_hold_bars=config["max_hold_bars"],
            take_profit=take_profit,
            last_update_price=entry_price,
            last_update_atr=atr,
        )
        
        self._positions[ticker] = state
        
        logger.debug(
            f"Registered {ticker}: entry={entry_price:.2f}, "
            f"hard_stop={hard_stop:.2f}, trail={trail_stop:.2f}, "
            f"tp={take_profit:.2f}, max_hold={config['max_hold_bars']} bars"
        )
        
        return state
    
    def update(
        self,
        ticker: str,
        current_price: float,
        current_atr: float,
        direction: int = 1,
    ) -> Optional[Dict]:
        """
        Update stop levels for one position and check for exit.
        
        Args:
            ticker: Symbol
            current_price: Current market price
            current_atr: Current ATR value
            direction: 1 for long, -1 for short
            
        Returns:
            None if no exit triggered, or exit dict with reason and price
        """
        if ticker not in self._positions:
            return None
        
        state = self._positions[ticker]
        config = STOP_CONFIGS.get(state.config_name, DEFAULT_CONFIG)
        
        state.bars_held += 1
        state.last_update_price = current_price
        state.last_update_atr = current_atr
        
        if direction == 1:  # Long position
            # Update high-water mark
            state.highest_price = max(state.highest_price, current_price)
            
            # Check if trailing stop should activate
            profit_pct = (current_price - state.entry_price) / state.entry_price
            if profit_pct >= config["trail_activation_pct"]:
                state.trail_active = True
            
            # Ratchet trailing stop up (never down)
            if state.trail_active:
                new_trail = current_price - config["trail_atr_mult"] * current_atr
                state.trail_stop = max(state.trail_stop, new_trail)
            
            # ── Check exit conditions (priority order) ──
            
            # Tier 1: Hard stop (catastrophic protection)
            if current_price <= state.hard_stop:
                return {
                    "ticker": ticker,
                    "reason": "hard_stop",
                    "price": current_price,
                    "bars_held": state.bars_held,
                    "pnl_pct": (current_price - state.entry_price) / state.entry_price,
                }
            
            # Take profit
            if state.take_profit > 0 and current_price >= state.take_profit:
                return {
                    "ticker": ticker,
                    "reason": "take_profit",
                    "price": current_price,
                    "bars_held": state.bars_held,
                    "pnl_pct": (current_price - state.entry_price) / state.entry_price,
                }
            
            # Tier 2: Trailing stop
            if state.trail_active and current_price <= state.trail_stop:
                return {
                    "ticker": ticker,
                    "reason": "trailing_stop",
                    "price": current_price,
                    "bars_held": state.bars_held,
                    "pnl_pct": (current_price - state.entry_price) / state.entry_price,
                }
            
            # Tier 3: Time-based exit
            if state.bars_held >= state.max_hold_bars:
                return {
                    "ticker": ticker,
                    "reason": "time_exit",
                    "price": current_price,
                    "bars_held": state.bars_held,
                    "pnl_pct": (current_price - state.entry_price) / state.entry_price,
                }
        
        else:  # Short position (mirror logic)
            state.highest_price = min(state.highest_price, current_price)  # Lowest for shorts
            
            profit_pct = (state.entry_price - current_price) / state.entry_price
            if profit_pct >= config["trail_activation_pct"]:
                state.trail_active = True
            
            if state.trail_active:
                new_trail = current_price + config["trail_atr_mult"] * current_atr
                state.trail_stop = min(state.trail_stop, new_trail)
            
            if current_price >= state.hard_stop:
                return {"ticker": ticker, "reason": "hard_stop", "price": current_price,
                        "bars_held": state.bars_held,
                        "pnl_pct": (state.entry_price - current_price) / state.entry_price}
            
            if state.take_profit > 0 and current_price <= state.take_profit:
                return {"ticker": ticker, "reason": "take_profit", "price": current_price,
                        "bars_held": state.bars_held,
                        "pnl_pct": (state.entry_price - current_price) / state.entry_price}
            
            if state.trail_active and current_price >= state.trail_stop:
                return {"ticker": ticker, "reason": "trailing_stop", "price": current_price,
                        "bars_held": state.bars_held,
                        "pnl_pct": (state.entry_price - current_price) / state.entry_price}
            
            if state.bars_held >= state.max_hold_bars:
                return {"ticker": ticker, "reason": "time_exit", "price": current_price,
                        "bars_held": state.bars_held,
                        "pnl_pct": (state.entry_price - current_price) / state.entry_price}
        
        return None
    
    def update_all(
        self,
        current_prices: Dict[str, float],
        current_atrs: Dict[str, float],
        directions: Optional[Dict[str, int]] = None,
    ) -> List[Dict]:
        """
        Update all positions and return list of triggered exits.
        
        Args:
            current_prices: {ticker: price}
            current_atrs: {ticker: atr}
            directions: {ticker: 1 or -1}, defaults to 1 (long)
        """
        exits = []
        if directions is None:
            directions = {}
        
        for ticker in list(self._positions.keys()):
            if ticker not in current_prices:
                continue
            
            direction = directions.get(ticker, 1)
            atr = current_atrs.get(ticker, self._positions[ticker].entry_atr)
            
            result = self.update(ticker, current_prices[ticker], atr, direction)
            if result is not None:
                exits.append(result)
        
        return exits
    
    def remove_position(self, ticker: str):
        """Remove a position after exit is executed."""
        self._positions.pop(ticker, None)
    
    def get_state(self, ticker: str) -> Optional[StopState]:
        """Get current stop state for a position."""
        return self._positions.get(ticker)
    
    def get_all_states(self) -> Dict[str, Dict]:
        """Get all position states as dicts."""
        return {k: v.to_dict() for k, v in self._positions.items()}
    
    def summary(self) -> str:
        """Human-readable summary of all positions and their stops."""
        if not self._positions:
            return "No active positions."
        
        lines = [f"Multi-Tier Stop Manager: {len(self._positions)} positions"]
        for ticker, state in self._positions.items():
            pnl = (state.last_update_price - state.entry_price) / state.entry_price * 100
            lines.append(
                f"  {ticker}: entry={state.entry_price:.2f} "
                f"current={state.last_update_price:.2f} ({pnl:+.1f}%) "
                f"hard={state.hard_stop:.2f} "
                f"trail={state.trail_stop:.2f}{'*' if state.trail_active else ''} "
                f"tp={state.take_profit:.2f} "
                f"bars={state.bars_held}/{state.max_hold_bars}"
            )
        return "\n".join(lines)
