"""
Portfolio Constructor

Constructs portfolios from signals with risk controls:
- Max position caps
- Sector exposure limits
- Turnover constraints
- Volatility targeting
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class Position:
    """A single position in the portfolio."""
    ticker: str
    shares: int
    entry_price: float
    entry_date: pd.Timestamp
    current_price: float
    weight: float
    direction: int  # 1 = long, -1 = short
    stop_loss: float
    take_profit: float
    strategy: str
    category: str
    sector: str = "Unknown"


@dataclass
class PortfolioState:
    """Current state of the portfolio."""
    date: pd.Timestamp
    cash: float
    positions: Dict[str, Position] = field(default_factory=dict)
    total_value: float = 0
    realized_pnl: float = 0
    unrealized_pnl: float = 0
    total_costs: float = 0
    trades_today: int = 0

    @property
    def equity(self) -> float:
        return self.cash + sum(
            p.shares * p.current_price * p.direction
            for p in self.positions.values()
        )


class PortfolioConstructor:
    """
    Construct and manage portfolios with risk controls.
    
    Enforces:
    - Maximum single position size
    - Maximum sector exposure
    - Turnover limits
    - Drawdown-based stop
    - Volatility targeting
    """

    def __init__(
        self,
        initial_capital: float = 100000,
        max_position_pct: float = 0.05,
        max_sector_pct: float = 0.25,
        max_positions: int = 30,
        max_daily_turnover_pct: float = 0.20,
        max_drawdown_halt: float = 0.15,
    ):
        self.initial_capital = initial_capital
        self.max_position_pct = max_position_pct
        self.max_sector_pct = max_sector_pct
        self.max_positions = max_positions
        self.max_daily_turnover_pct = max_daily_turnover_pct
        self.max_drawdown_halt = max_drawdown_halt
        self.peak_equity = initial_capital

    def construct_portfolio(
        self,
        signals: List[Dict],
        current_state: PortfolioState,
        prices: Dict[str, float],
        sectors: Dict[str, str] = None,
        volatilities: Dict[str, float] = None,
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Construct target portfolio from signals with risk controls.
        
        Args:
            signals: List of signal dicts (ticker, score, direction, category, etc.)
            current_state: Current portfolio state
            prices: Current prices dict
            sectors: Sector map
            volatilities: Annualized vol for each ticker
            
        Returns:
            (orders_to_execute, positions_to_close)
        """
        if sectors is None:
            sectors = {}
        if volatilities is None:
            volatilities = {}

        # Check drawdown halt
        current_equity = current_state.equity
        drawdown = (self.peak_equity - current_equity) / self.peak_equity
        if drawdown > self.max_drawdown_halt:
            # Close all positions, halt trading
            return [], [{"ticker": t, "reason": "drawdown_halt"} for t in current_state.positions]

        self.peak_equity = max(self.peak_equity, current_equity)

        # Sort signals by score
        signals = sorted(signals, key=lambda s: s.get("score", 0), reverse=True)

        # Apply filters
        orders = []
        sector_exposure = self._compute_sector_exposure(current_state, sectors, prices)
        total_turnover = 0

        for signal in signals:
            ticker = signal["ticker"]
            price = prices.get(ticker)
            if price is None or price <= 0:
                continue

            # Check position count
            n_positions = len(current_state.positions) + len(orders)
            if n_positions >= self.max_positions:
                break

            # Skip if already in portfolio
            if ticker in current_state.positions:
                continue

            # Check sector exposure
            sector = sectors.get(ticker, "Unknown")
            if sector_exposure.get(sector, 0) >= self.max_sector_pct:
                continue

            # Compute position size
            target_weight = min(signal.get("confidence", 0.5) * self.max_position_pct, self.max_position_pct)
            target_value = current_equity * target_weight
            shares = int(target_value / price)

            if shares <= 0:
                continue

            # Check turnover limit
            order_value = shares * price
            total_turnover += order_value
            if total_turnover / current_equity > self.max_daily_turnover_pct:
                break

            orders.append({
                "ticker": ticker,
                "shares": shares,
                "price": price,
                "direction": signal.get("direction", 1),
                "weight": target_weight,
                "strategy": signal.get("strategy", "unknown"),
                "category": signal.get("category", "unknown"),
                "score": signal.get("score", 0),
                "stop_loss": price * (1 - signal.get("stop_loss_pct", 0.10)),
                "take_profit": price * (1 + signal.get("take_profit_pct", 0.50)),
                "sector": sector,
            })

            sector_exposure[sector] = sector_exposure.get(sector, 0) + target_weight

        # Check for positions to close (stop loss, take profit, expired)
        closes = []
        for ticker, pos in current_state.positions.items():
            current_price = prices.get(ticker, pos.current_price)

            # Stop loss
            if current_price <= pos.stop_loss:
                closes.append({"ticker": ticker, "reason": "stop_loss", "price": current_price})
            # Take profit
            elif current_price >= pos.take_profit:
                closes.append({"ticker": ticker, "reason": "take_profit", "price": current_price})

        return orders, closes

    def _compute_sector_exposure(
        self,
        state: PortfolioState,
        sectors: Dict[str, str],
        prices: Dict[str, float],
    ) -> Dict[str, float]:
        """Compute current sector exposure as % of equity."""
        exposure = {}
        equity = state.equity
        if equity <= 0:
            return exposure

        for ticker, pos in state.positions.items():
            sector = sectors.get(ticker, "Unknown")
            price = prices.get(ticker, pos.current_price)
            weight = (pos.shares * price) / equity
            exposure[sector] = exposure.get(sector, 0) + weight

        return exposure

    def compute_target_weights(
        self,
        signals: List[Dict],
        method: str = "risk_weighted",
        volatilities: Dict[str, float] = None,
    ) -> Dict[str, float]:
        """
        Compute target portfolio weights from signals.
        
        Methods:
        - equal_weight: 1/N across all signals
        - score_weighted: weight by signal score
        - risk_weighted: inverse volatility weighting
        - risk_parity: equalize risk contribution
        """
        if not signals:
            return {}

        tickers = [s["ticker"] for s in signals]
        n = len(tickers)

        if method == "equal_weight":
            weight = min(1.0 / n, self.max_position_pct)
            return {t: weight for t in tickers}

        elif method == "score_weighted":
            total_score = sum(s.get("score", 0.5) for s in signals)
            if total_score <= 0:
                return {t: 1.0 / n for t in tickers}
            weights = {}
            for s in signals:
                w = s.get("score", 0.5) / total_score
                weights[s["ticker"]] = min(w, self.max_position_pct)
            return weights

        elif method == "risk_weighted" and volatilities:
            inv_vols = {t: 1.0 / max(volatilities.get(t, 0.25), 0.05) for t in tickers}
            total_inv_vol = sum(inv_vols.values())
            weights = {}
            for t in tickers:
                w = inv_vols[t] / total_inv_vol
                weights[t] = min(w, self.max_position_pct)
            return weights

        else:
            # Default to equal weight
            weight = min(1.0 / n, self.max_position_pct)
            return {t: weight for t in tickers}
