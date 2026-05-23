"""
Funding Rate Arbitrage & Basis Trading Strategies
=================================================
Exploits the premium between spot and perpetual futures markets.

Strategies:
1. Funding Rate Arbitrage - capture funding payments
2. Basis Trading - trade the spot-futures spread
3. Cash-and-Carry - risk-free arbitrage when basis is wide
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class FundingRateOpportunity:
    """Container for funding rate arbitrage opportunity."""
    symbol: str
    funding_rate: float  # 8-hour funding rate
    annualized_rate: float
    direction: str  # "LONG" (receive funding) or "SHORT" (pay funding)
    spot_price: float
    perp_price: float
    basis: float  # (perp - spot) / spot
    expected_profit: float  # Annualized
    risk_score: float  # 0-1, higher = riskier
    timestamp: datetime


@dataclass
class BasisTrade:
    """Container for basis trading signal."""
    symbol: str
    basis: float  # Current basis (annualized)
    historical_percentile: float  # Where current basis sits historically
    zscore: float
    direction: str  # "NARROW" (basis will shrink) or "WIDEN"
    confidence: float
    expected_return: float
    holding_period: int  # Expected days to hold


class FundingRateArbitrage:
    """
    Detect funding rate arbitrage opportunities.
    
    Strategy:
    - When funding rate is highly positive: SHORT perp + LONG spot
      (earn funding every 8 hours)
    - When funding rate is highly negative: LONG perp + SHORT spot
      (earn funding every 8 hours)
    
    Requirements:
    - Access to both spot and perpetual markets
    - Ability to short spot (or hold spot as hedge)
    - Monitor for basis risk (spread between spot and perp)
    """
    
    def __init__(
        self,
        min_funding_threshold: float = 0.0001,  # 0.01% per 8h = ~11% annualized
        max_basis_risk: float = 0.005,  # 0.5% max acceptable basis
        funding_intervals_per_day: float = 3.0  # 3x 8-hour periods
    ):
        self.min_funding_threshold = min_funding_threshold
        self.max_basis_risk = max_basis_risk
        self.funding_intervals_per_day = funding_intervals_per_day
    
    def calculate_annualized_rate(self, funding_rate_8h: float) -> float:
        """Convert 8-hour funding rate to annualized rate."""
        return funding_rate_8h * self.funding_intervals_per_day * 365
    
    def detect_opportunities(
        self,
        funding_rates: Dict[str, float],  # symbol -> 8h funding rate
        spot_prices: Dict[str, float],
        perp_prices: Dict[str, float],
        exclude_negative_carry: bool = True
    ) -> List[FundingRateOpportunity]:
        """
        Detect funding rate arbitrage opportunities.
        
        Args:
            funding_rates: Dict of symbol -> 8-hour funding rate
            spot_prices: Dict of symbol -> spot price
            perp_prices: Dict of symbol -> perpetual price
            exclude_negative_carry: If True, only return positive carry trades
        
        Returns:
            List of opportunities sorted by expected profit
        """
        opportunities = []
        
        for symbol, funding_rate in funding_rates.items():
            if symbol not in spot_prices or symbol not in perp_prices:
                continue
            
            spot = spot_prices[symbol]
            perp = perp_prices[symbol]
            
            if spot <= 0 or perp <= 0:
                continue
            
            # Calculate basis (spread)
            basis = (perp - spot) / spot
            
            # Annualized funding rate
            annualized = self.calculate_annualized_rate(funding_rate)
            
            # Determine direction
            # Positive funding = longs pay shorts -> we want to be SHORT perp
            # Negative funding = shorts pay longs -> we want to be LONG perp
            if funding_rate > self.min_funding_threshold:
                direction = "SHORT"  # Short perp, long spot
                expected_profit = annualized
            elif funding_rate < -self.min_funding_threshold:
                direction = "LONG"  # Long perp, short spot
                expected_profit = -annualized  # Absolute value
            else:
                continue  # Funding too small
            
            # Check basis risk
            if abs(basis) > self.max_basis_risk:
                risk_score = 0.8  # High basis risk
            else:
                risk_score = 0.3  # Low basis risk
            
            # Adjust expected profit for basis risk
            # If we need to pay the basis to enter, reduce expected profit
            if direction == "SHORT" and basis > 0:
                # Shorting perp above spot = negative entry cost
                expected_profit -= basis * 100  # Convert to annualized equivalent
            elif direction == "LONG" and basis < 0:
                # Longing perp below spot = positive entry cost
                expected_profit += abs(basis) * 100
            
            # Skip if negative carry and exclude_negative_carry is True
            if exclude_negative_carry and expected_profit <= 0:
                continue
            
            opportunities.append(FundingRateOpportunity(
                symbol=symbol,
                funding_rate=funding_rate,
                annualized_rate=annualized,
                direction=direction,
                spot_price=spot,
                perp_price=perp,
                basis=basis,
                expected_profit=expected_profit,
                risk_score=risk_score,
                timestamp=datetime.utcnow()
            ))
        
        # Sort by expected profit (descending)
        opportunities.sort(key=lambda x: x.expected_profit, reverse=True)
        
        return opportunities
    
    def get_top_opportunities(
        self,
        opportunities: List[FundingRateOpportunity],
        n: int = 5,
        max_risk_score: float = 0.5
    ) -> List[FundingRateOpportunity]:
        """Get top N opportunities with acceptable risk."""
        filtered = [o for o in opportunities if o.risk_score <= max_risk_score]
        return filtered[:n]


class BasisTradingStrategy:
    """
    Trade the convergence/divergence of spot-perpetual basis.
    
    Strategy:
    - When basis is historically wide: SHORT perp + LONG spot (bet on narrowing)
    - When basis is historically narrow: LONG perp + SHORT spot (bet on widening)
    
    This is a mean-reversion strategy on the basis.
    """
    
    def __init__(
        self,
        lookback_days: int = 30,
        entry_zscore: float = 2.0,
        exit_zscore: float = 0.5
    ):
        self.lookback_days = lookback_days
        self.entry_zscore = entry_zscore
        self.exit_zscore = exit_zscore
    
    def calculate_basis_zscore(
        self,
        current_basis: float,
        historical_basis: pd.Series
    ) -> Tuple[float, float]:
        """
        Calculate z-score and percentile of current basis.
        
        Returns:
            (zscore, percentile)
        """
        mean = historical_basis.mean()
        std = historical_basis.std()
        
        if std == 0:
            return 0, 0.5
        
        zscore = (current_basis - mean) / std
        percentile = (historical_basis < current_basis).mean()
        
        return zscore, percentile
    
    def generate_signals(
        self,
        basis_history: Dict[str, pd.Series]  # symbol -> historical basis series
    ) -> List[BasisTrade]:
        """
        Generate basis trading signals.
        
        Args:
            basis_history: Dict of symbol -> historical basis (daily)
        
        Returns:
            List of basis trade signals
        """
        signals = []
        
        for symbol, history in basis_history.items():
            if len(history) < self.lookback_days:
                continue
            
            current_basis = history.iloc[-1]
            hist_window = history.tail(self.lookback_days)
            
            zscore, percentile = self.calculate_basis_zscore(current_basis, hist_window)
            
            # Generate signal based on z-score
            if zscore > self.entry_zscore:
                # Basis is wide - expect it to narrow
                # SHORT perp (expensive) + LONG spot (cheap)
                direction = "NARROW"
                confidence = min(abs(zscore) / 3.0, 1.0)  # Scale confidence
                expected_return = abs(zscore) * hist_window.std() * 100  # Annualized estimate
                
                signals.append(BasisTrade(
                    symbol=symbol,
                    basis=current_basis,
                    historical_percentile=percentile,
                    zscore=zscore,
                    direction=direction,
                    confidence=confidence,
                    expected_return=expected_return,
                    holding_period=int(abs(zscore) * 5)  # Days to revert
                ))
                
            elif zscore < -self.entry_zscore:
                # Basis is narrow/negative - expect it to widen
                # LONG perp (cheap) + SHORT spot (expensive)
                direction = "WIDEN"
                confidence = min(abs(zscore) / 3.0, 1.0)
                expected_return = abs(zscore) * hist_window.std() * 100
                
                signals.append(BasisTrade(
                    symbol=symbol,
                    basis=current_basis,
                    historical_percentile=percentile,
                    zscore=zscore,
                    direction=direction,
                    confidence=confidence,
                    expected_return=expected_return,
                    holding_period=int(abs(zscore) * 5)
                ))
        
        # Sort by confidence
        signals.sort(key=lambda x: x.confidence, reverse=True)
        
        return signals


class CashAndCarryArbitrage:
    """
    Risk-free cash-and-carry arbitrage.
    
    When: Perpetual trades at significant premium to spot
    Trade: Buy spot, sell perpetual, earn funding
    
    This is "risk-free" because the positions hedge each other,
    but requires:
    - Capital for spot purchase
    - Ability to short perpetual
    - Monitoring of liquidation risk on perp short
    """
    
    def __init__(
        self,
        min_annualized_return: float = 0.10,  # 10% minimum
        max_holding_days: int = 30
    ):
        self.min_annualized_return = min_annualized_return
        self.max_holding_days = max_holding_days
    
    def calculate_carry_return(
        self,
        spot_price: float,
        perp_price: float,
        funding_rate_8h: float,
        days_to_hold: int = 30
    ) -> Dict:
        """
        Calculate cash-and-carry return.
        
        Returns:
            Dict with expected returns and risk metrics
        """
        # Initial basis (entry cost)
        basis = (perp_price - spot_price) / spot_price
        
        # Funding income over holding period
        funding_per_day = funding_rate_8h * 3  # 3 funding periods per day
        funding_income = funding_per_day * days_to_hold
        
        # Expected exit basis (assume it narrows to 0)
        exit_basis = 0
        basis_pnl = basis - exit_basis  # Profit from basis narrowing
        
        # Total return
        total_return = funding_income + basis_pnl
        annualized = total_return * (365 / days_to_hold)
        
        # Risk: Basis could widen further
        max_risk = abs(basis) + funding_income  # Worst case
        
        return {
            'spot_price': spot_price,
            'perp_price': perp_price,
            'entry_basis': basis,
            'funding_income': funding_income,
            'basis_pnl': basis_pnl,
            'total_return': total_return,
            'annualized_return': annualized,
            'max_risk': max_risk,
            'sharpe_approx': annualized / (max_risk + 0.001),
            'is_profitable': annualized >= self.min_annualized_return
        }


def fetch_binance_funding_rates() -> Dict[str, float]:
    """
    Fetch current funding rates from Binance.
    
    Returns:
        Dict of symbol -> 8-hour funding rate
    """
    import requests
    
    try:
        _fapi_bases = [
            "https://fapi.binance.com", "https://fapi1.binance.com",
            "https://fapi2.binance.com",
        ]
        data = None
        for _base in _fapi_bases:
            try:
                url = f"{_base}/fapi/v1/premiumIndex"
                response = requests.get(url, timeout=10)
                if response.status_code in (451, 403):
                    continue
                data = response.json()
                break
            except Exception:
                continue
        if not data:
            return {}
        
        funding_rates = {}
        for item in data:
            symbol = item.get('symbol', '')
            funding_rate = float(item.get('lastFundingRate', 0))
            funding_rates[symbol] = funding_rate
        
        return funding_rates
    except Exception as e:
        logger.error(f"Error fetching funding rates: {e}")
        return {}


def generate_funding_arbitrage_signals() -> List[Dict]:
    """
    Main entry point: Generate funding arbitrage signals.
    
    Returns:
        List of signal dictionaries for Discord/routing
    """
    # Fetch data
    funding_rates = fetch_binance_funding_rates()
    
    # Get spot and perp prices (placeholder - would need actual price fetcher)
    # In production, use existing price fetcher
    spot_prices = {}  # Populate from price fetcher
    perp_prices = {}  # Populate from price fetcher
    
    # Detect opportunities
    arb = FundingRateArbitrage()
    opportunities = arb.detect_opportunities(funding_rates, spot_prices, perp_prices)
    
    # Convert to signal format
    signals = []
    for opp in arb.get_top_opportunities(opportunities, n=5):
        signals.append({
            'symbol': opp.symbol,
            'direction': opp.direction,
            'confidence': 0.8 if opp.risk_score < 0.5 else 0.6,
            'strategy': 'funding_arbitrage',
            'entry_price': opp.spot_price,
            'expected_profit_annual': opp.expected_profit,
            'funding_rate_8h': opp.funding_rate,
            'basis': opp.basis,
            'risk_score': opp.risk_score,
            'timestamp': opp.timestamp.isoformat()
        })
    
    return signals


if __name__ == "__main__":
    print("Funding Rate Arbitrage & Basis Trading Module")
    print("\nExample usage:")
    print("  from alpha_engine.basis_strategies import FundingRateArbitrage")
    print("  arb = FundingRateArbitrage()")
    print("  opportunities = arb.detect_opportunities(funding_rates, spot, perp)")
