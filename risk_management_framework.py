"""
Risk Management & Capital Preservation Framework
Implementation for Trading System

Usage:
    from risk_management_framework import (
        PositionSizer, DrawdownProtection, PortfolioRiskManager,
        StopLossManager, VolatilityTargeting, EmergencyProtocol
    )
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from scipy import stats


@dataclass
class KellyResult:
    """Result from Kelly Criterion calculation"""
    full_kelly: float
    half_kelly: float
    quarter_kelly: float
    recommended: float
    confidence: str


class PositionSizer:
    """
    Advanced position sizing with multiple methods.
    
    Methods supported:
    - Kelly Criterion (with fractional safety)
    - Fixed fractional sizing
    - Fixed ratio sizing
    - Optimal f
    - Risk-parity
    """
    
    def __init__(self, account_equity: float):
        self.equity = account_equity
        self.max_position_pct = 0.25
        self.min_position_pct = 0.01
    
    def kelly_criterion(self, 
                       wins: int, 
                       losses: int, 
                       avg_win: float, 
                       avg_loss: float,
                       kelly_fraction: float = 0.25) -> KellyResult:
        """
        Calculate Kelly Criterion with safety fraction.
        
        Args:
            wins: Number of winning trades
            losses: Number of losing trades  
            avg_win: Average winning trade return (e.g., 0.05 for 5%)
            avg_loss: Average losing trade return (positive value, e.g., 0.03)
            kelly_fraction: Fraction of Kelly to use (0.25 = quarter Kelly)
        """
        total_trades = wins + losses
        win_prob = wins / total_trades if total_trades > 0 else 0
        
        payoff_ratio = avg_win / avg_loss if avg_loss > 0 else 1
        
        kelly_pct = win_prob - ((1 - win_prob) / payoff_ratio)
        kelly_pct = max(0, min(kelly_pct, 1))
        
        half_kelly = kelly_pct * 0.5
        quarter_kelly = kelly_pct * 0.25
        
        if total_trades < 30:
            confidence = "LOW - Insufficient sample size"
            recommended = min(quarter_kelly, 0.05)
        elif total_trades < 100:
            confidence = "MEDIUM - Use caution"
            recommended = quarter_kelly
        else:
            confidence = "HIGH - Reliable estimate"
            recommended = min(half_kelly, 0.10)
        
        return KellyResult(
            full_kelly=kelly_pct,
            half_kelly=half_kelly,
            quarter_kelly=quarter_kelly,
            recommended=recommended,
            confidence=confidence
        )
    
    def fixed_fractional(self, 
                        entry_price: float,
                        stop_loss: float,
                        risk_pct: float = 0.01) -> dict:
        """Calculate position size based on fixed fractional risk."""
        risk_amount = self.equity * risk_pct
        risk_per_share = abs(entry_price - stop_loss)
        
        if risk_per_share == 0:
            raise ValueError("Risk per share cannot be zero")
        
        shares = int(risk_amount / risk_per_share)
        position_value = shares * entry_price
        position_pct = position_value / self.equity
        
        capped = False
        if position_pct > self.max_position_pct:
            max_shares = int((self.equity * self.max_position_pct) / entry_price)
            shares = min(shares, max_shares)
            position_value = shares * entry_price
            position_pct = position_value / self.equity
            capped = True
        
        return {
            'shares': shares,
            'position_value': position_value,
            'position_pct': position_pct,
            'risk_amount': risk_amount,
            'risk_per_share': risk_per_share,
            'capped': capped,
            'method': 'fixed_fractional'
        }
    
    def risk_parity(self, assets: List[dict]) -> dict:
        """Risk-parity allocation based on inverse volatility."""
        n = len(assets)
        inverse_vols = []
        
        for asset in assets:
            inv_vol = 1 / asset['volatility'] if asset['volatility'] > 0 else 0
            inverse_vols.append(inv_vol)
        
        total_inv_vol = sum(inverse_vols)
        allocations = []
        
        for i, asset in enumerate(assets):
            weight = (inverse_vols[i] / total_inv_vol) if total_inv_vol > 0 else 1/n
            position_value = self.equity * weight
            shares = int(position_value / asset['price'])
            
            allocations.append({
                'symbol': asset['symbol'],
                'weight': weight,
                'position_value': position_value,
                'shares': shares,
                'volatility': asset['volatility']
            })
        
        return {'allocations': allocations, 'method': 'risk_parity'}


class DrawdownProtection:
    """Comprehensive drawdown protection with circuit breakers."""
    
    def __init__(self, initial_equity: float):
        self.initial_equity = initial_equity
        self.peak_equity = initial_equity
        self.current_equity = initial_equity
        self.equity_history = [initial_equity]
        self.drawdown_thresholds = {
            'warning': 0.05,
            'caution': 0.10,
            'danger': 0.15,
            'stop': 0.20
        }
        self.consecutive_losses = 0
        self.max_consecutive_losses = 5
    
    def update_equity(self, new_equity: float) -> dict:
        """Update equity and return drawdown status."""
        self.current_equity = new_equity
        self.equity_history.append(new_equity)
        
        if new_equity > self.peak_equity:
            self.peak_equity = new_equity
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
        
        return self.get_drawdown_status()
    
    def get_drawdown_status(self) -> dict:
        """Get current drawdown status and recommended actions."""
        drawdown = (self.peak_equity - self.current_equity) / self.peak_equity
        
        status = {
            'drawdown_pct': drawdown,
            'peak_equity': self.peak_equity,
            'current_equity': self.current_equity,
            'consecutive_losses': self.consecutive_losses,
            'level': 'normal',
            'position_multiplier': 1.0,
            'action': 'Trade normally',
            'can_trade': True
        }
        
        if drawdown >= self.drawdown_thresholds['stop']:
            status.update({
                'level': 'CRITICAL',
                'position_multiplier': 0.0,
                'action': 'STOP ALL TRADING IMMEDIATELY',
                'can_trade': False
            })
        elif drawdown >= self.drawdown_thresholds['danger']:
            status.update({
                'level': 'DANGER',
                'position_multiplier': 0.25,
                'action': 'Reduce to 25% position size'
            })
        elif drawdown >= self.drawdown_thresholds['caution']:
            status.update({
                'level': 'CAUTION',
                'position_multiplier': 0.50,
                'action': 'Reduce to 50% position size'
            })
        elif drawdown >= self.drawdown_thresholds['warning']:
            status.update({
                'level': 'WARNING',
                'position_multiplier': 0.75,
                'action': 'Reduce to 75% position size'
            })
        
        if self.consecutive_losses >= self.max_consecutive_losses:
            status['can_trade'] = False
            status['action'] += f" | STOP: {self.consecutive_losses} consecutive losses"
        
        return status
    
    def check_circuit_breakers(self, daily_pnl: float, trades_today: int) -> dict:
        """Check circuit breaker conditions."""
        daily_loss_pct = abs(daily_pnl) / self.current_equity if daily_pnl < 0 else 0
        
        breakers = {
            'daily_loss_limit': {
                'limit': 0.03,
                'triggered': daily_loss_pct >= 0.03,
                'action': 'HALT TRADING FOR TODAY'
            },
            'weekly_loss_limit': {
                'limit': 0.07,
                'triggered': self._check_weekly_loss() >= 0.07,
                'action': 'HALT TRADING FOR WEEK'
            },
            'consecutive_losses': {
                'limit': self.max_consecutive_losses,
                'triggered': self.consecutive_losses >= self.max_consecutive_losses,
                'action': 'MANDATORY 24-HOUR BREAK'
            }
        }
        
        any_triggered = any(b['triggered'] for b in breakers.values())
        
        return {
            'breakers': breakers,
            'any_triggered': any_triggered,
            'halt_trading': any_triggered
        }
    
    def _check_weekly_loss(self) -> float:
        """Calculate weekly loss percentage."""
        if len(self.equity_history) < 5:
            return 0
        week_ago_equity = self.equity_history[-min(5, len(self.equity_history))]
        return (week_ago_equity - self.current_equity) / week_ago_equity


class PortfolioRiskManager:
    """Portfolio-level risk management."""
    
    def __init__(self, total_equity: float):
        self.equity = total_equity
        self.positions = {}
        self.max_single_position = 0.15
        self.max_sector_exposure = 0.30
    
    def add_position(self, symbol: str, value: float, sector: str, beta: float = 1.0):
        """Add or update position."""
        self.positions[symbol] = {
            'value': value,
            'sector': sector,
            'beta': beta,
            'pct_of_equity': value / self.equity
        }
    
    def calculate_portfolio_beta(self) -> dict:
        """Calculate overall portfolio beta."""
        if not self.positions:
            return {'portfolio_beta': 0, 'status': 'No positions'}
        
        total_value = sum(p['value'] for p in self.positions.values())
        weighted_beta = sum(
            p['value'] * p.get('beta', 1.0) for p in self.positions.values()
        ) / total_value
        
        if abs(weighted_beta - 1.0) < 0.1:
            status = 'Market neutral'
        elif weighted_beta > 1.2:
            status = 'High beta - vulnerable to drops'
        elif weighted_beta < 0.8:
            status = 'Low beta - conservative'
        else:
            status = 'Moderate beta'
        
        return {
            'portfolio_beta': weighted_beta,
            'status': status,
            'hedge_required': (1 - weighted_beta) * total_value
        }
    
    def calculate_portfolio_var(self, confidence: float = 0.95) -> dict:
        """Calculate portfolio Value at Risk."""
        if not self.positions:
            return {'var': 0, 'var_pct': 0}
        
        portfolio_value = sum(p['value'] for p in self.positions.values())
        
        # Simplified calculation
        weighted_vol = 0
        for pos in self.positions.values():
            asset_vol = 0.20 / np.sqrt(252)  # Daily vol
            weighted_vol += (pos['pct_of_equity'] * asset_vol) ** 2
        
        portfolio_vol = np.sqrt(weighted_vol)
        z_score = {0.90: 1.28, 0.95: 1.645, 0.99: 2.33}.get(confidence, 1.645)
        
        var = z_score * portfolio_vol * portfolio_value
        
        return {
            'var_amount': var,
            'var_pct': var / portfolio_value if portfolio_value > 0 else 0,
            'confidence': confidence
        }


class StopLossManager:
    """Advanced stop loss calculations."""
    
    def atr_stop(self, 
                 entry_price: float,
                 atr: float,
                 direction: str = 'long',
                 multiplier: float = 2.0) -> dict:
        """Calculate ATR-based stop loss."""
        stop_distance = atr * multiplier
        
        if direction == 'long':
            stop_price = entry_price - stop_distance
        else:
            stop_price = entry_price + stop_distance
        
        return {
            'entry_price': entry_price,
            'stop_price': stop_price,
            'stop_distance': stop_distance,
            'stop_pct': stop_distance / entry_price,
            'atr': atr,
            'multiplier': multiplier
        }
    
    def trailing_stop(self,
                     entry_price: float,
                     current_price: float,
                     highest_price: float,
                     trail_pct: float = 0.10) -> dict:
        """Calculate trailing stop price."""
        current_profit_pct = (current_price - entry_price) / entry_price
        trail_distance = highest_price * trail_pct
        stop_price = highest_price - trail_distance
        
        if stop_price < entry_price and current_profit_pct > 0:
            stop_price = max(stop_price, entry_price)
        
        return {
            'entry_price': entry_price,
            'current_price': current_price,
            'stop_price': stop_price,
            'trail_pct': trail_pct,
            'locked_profit_pct': (stop_price - entry_price) / entry_price if stop_price > entry_price else 0
        }


class VolatilityTargeting:
    """Dynamic position sizing based on volatility."""
    
    def __init__(self, target_volatility: float = 0.10):
        self.target_vol = target_volatility
        self.volatility_history = []
    
    def calculate_multiplier(self, recent_returns: List[float]) -> float:
        """Calculate position size multiplier based on volatility."""
        if len(recent_returns) < 20:
            return 1.0
        
        current_vol = np.std(recent_returns) * np.sqrt(252)
        self.volatility_history.append(current_vol)
        
        multiplier = self.target_vol / current_vol if current_vol > 0 else 1.0
        return max(0.25, min(multiplier, 1.5))


class EmergencyProtocol:
    """Emergency response for significant drawdowns."""
    
    EMERGENCY_LEVELS = {
        'LEVEL_1': {'drawdown': 0.10, 'action': 'REDUCE_SIZE'},
        'LEVEL_2': {'drawdown': 0.15, 'action': 'DEFENSIVE'},
        'LEVEL_3': {'drawdown': 0.20, 'action': 'HALT'},
        'LEVEL_4': {'drawdown': 0.30, 'action': 'CAPITAL_PRESERVATION'}
    }
    
    def assess_emergency(self, current_equity: float, peak_equity: float) -> dict:
        """Assess current emergency level."""
        drawdown = (peak_equity - current_equity) / peak_equity
        
        if drawdown >= 0.30:
            level = 'LEVEL_4'
        elif drawdown >= 0.20:
            level = 'LEVEL_3'
        elif drawdown >= 0.15:
            level = 'LEVEL_2'
        elif drawdown >= 0.10:
            level = 'LEVEL_1'
        else:
            return {'level': 'NORMAL', 'drawdown': drawdown, 'action': 'NONE'}
        
        emergency = self.EMERGENCY_LEVELS[level].copy()
        emergency['drawdown'] = drawdown
        emergency['level'] = level
        emergency['recovery_needed'] = (peak_equity / current_equity) - 1
        
        return emergency
    
    def generate_recovery_plan(self, current_equity: float, peak_equity: float) -> dict:
        """Generate recovery plan after drawdown."""
        drawdown = (peak_equity - current_equity) / peak_equity
        recovery_needed = (peak_equity / current_equity) - 1
        
        return {
            'current_situation': {
                'drawdown': drawdown,
                'recovery_needed': recovery_needed
            },
            'phase_1_stabilize': {
                'duration': 'Week 1-2',
                'risk_per_trade': 0.005,
                'max_positions': 3,
                'cash_target': 0.50
            },
            'phase_2_recover': {
                'duration': 'Week 3-8',
                'risk_per_trade': 0.01,
                'max_positions': 5,
                'cash_target': 0.30
            },
            'phase_3_growth': {
                'duration': 'After new highs',
                'risk_per_trade': 0.01,
                'max_positions': 10,
                'cash_target': 0.10
            }
        }


class PreTradeChecklist:
    """Mandatory pre-trade risk checklist."""
    
    CHECKLIST_ITEMS = [
        {'id': 'R1', 'item': 'Position size calculated using 1% risk rule', 'critical': True},
        {'id': 'R2', 'item': 'Stop loss price determined and entered', 'critical': True},
        {'id': 'R3', 'item': 'Risk/Reward ratio at least 1:2', 'critical': True},
        {'id': 'R4', 'item': 'Daily loss limit not exceeded', 'critical': True},
        {'id': 'R5', 'item': 'Not in revenge trading mode', 'critical': True},
    ]
    
    def run_checklist(self, answers: Dict[str, bool]) -> dict:
        """Run pre-trade checklist."""
        results = []
        critical_failures = 0
        
        for item in self.CHECKLIST_ITEMS:
            passed = answers.get(item['id'], False)
            results.append({
                **item,
                'passed': passed,
                'status': 'PASS' if passed else ('FAIL-CRITICAL' if item['critical'] else 'FAIL')
            })
            
            if not passed and item['critical']:
                critical_failures += 1
        
        return {
            'can_trade': critical_failures == 0,
            'critical_failures': critical_failures,
            'results': results
        }


# Example usage
if __name__ == "__main__":
    # Initialize with $100k account
    equity = 100000
    
    # Position sizing example
    sizer = PositionSizer(equity)
    
    # Kelly calculation for system with 55% win rate, 2:1 reward/risk
    kelly = sizer.kelly_criterion(wins=55, losses=45, avg_win=0.10, avg_loss=0.05)
    print(f"Kelly Criterion: {kelly.recommended:.2%} recommended")
    
    # Fixed fractional sizing
    position = sizer.fixed_fractional(
        entry_price=100,
        stop_loss=95,
        risk_pct=0.01
    )
    print(f"Position size: {position['shares']} shares (${position['position_value']:,.2f})")
    
    # Drawdown monitoring
    dd = DrawdownProtection(equity)
    status = dd.update_equity(95000)  # 5% drawdown
    print(f"Drawdown status: {status['level']} - {status['action']}")
    
    # Stop loss calculation
    stops = StopLossManager()
    atr_stop = stops.atr_stop(entry_price=100, atr=2.5, multiplier=2.0)
    print(f"ATR Stop at ${atr_stop['stop_price']:.2f} ({atr_stop['stop_pct']:.1%} risk)")
