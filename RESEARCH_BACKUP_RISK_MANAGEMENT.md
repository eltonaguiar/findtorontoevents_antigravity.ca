# Comprehensive Risk Management & Capital Preservation Strategies

**Research Date:** February 15, 2026  
**Purpose:** Protect capital during system drawdowns and establish robust risk frameworks

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Position Sizing Methods](#1-position-sizing-methods)
3. [Drawdown Protection](#2-drawdown-protection)
4. [Portfolio-Level Risk](#3-portfolio-level-risk)
5. [Stop Loss Strategies](#4-stop-loss-strategies)
6. [Hedging Techniques](#5-hedging-techniques)
7. [Psychological Risk Management](#6-psychological-risk-management)
8. [Black Swan Protection](#7-black-swan-protection)
9. [Emergency Protocols](#8-emergency-protocols)
10. [Implementation Checklist](#9-implementation-checklist)

---

## Executive Summary

When a trading system experiences losses, the priority shifts from **return maximization** to **capital preservation**. The frameworks in this document provide multiple layers of defense:

| Layer | Purpose | Key Metric |
|-------|---------|------------|
| Position Sizing | Control per-trade risk | % of equity at risk |
| Stop Losses | Limit individual losses | Risk/Reward ratio |
| Drawdown Controls | System-level protection | Max drawdown threshold |
| Portfolio Risk | Prevent correlated losses | Correlation matrix |
| Hedging | Downside protection | Cost vs protection |
| Emergency | Survival protocol | Capital preservation |

**Golden Rule:** Never risk more than 1-2% of capital on any single trade.

---

## 1. Position Sizing Methods

### 1.1 Kelly Criterion (Fractional Kelly)

The Kelly Criterion determines optimal bet size based on win rate and payoff ratio.

**Formula:**
```
Kelly % = W - [(1 - W) / R]

Where:
W = Win probability (0-1)
R = Average win / Average loss (payoff ratio)
```

**Python Implementation:**

```python
import numpy as np
import pandas as pd
from typing import List, Tuple
from dataclasses import dataclass

@dataclass
class KellyResult:
    full_kelly: float
    half_kelly: float
    quarter_kelly: float
    recommended: float
    confidence: str

class PositionSizer:
    """Advanced position sizing with multiple methods"""
    
    def __init__(self, account_equity: float):
        self.equity = account_equity
        self.max_position_pct = 0.25  # Max 25% in single position
        self.min_position_pct = 0.01  # Min 1% to make trade worthwhile
    
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
            kelly_fraction: Use quarter Kelly (0.25) for safety
        """
        total_trades = wins + losses
        win_prob = wins / total_trades
        
        # Payoff ratio (R)
        payoff_ratio = avg_win / avg_loss if avg_loss > 0 else 1
        
        # Full Kelly
        kelly_pct = win_prob - ((1 - win_prob) / payoff_ratio)
        kelly_pct = max(0, min(kelly_pct, 1))  # Bound between 0-100%
        
        # Fractional Kelly (safer)
        half_kelly = kelly_pct * 0.5
        quarter_kelly = kelly_pct * 0.25
        
        # Determine confidence level
        if total_trades < 30:
            confidence = "LOW - Insufficient sample size"
            recommended = min(quarter_kelly, 0.05)  # Cap at 5%
        elif total_trades < 100:
            confidence = "MEDIUM - Use caution"
            recommended = quarter_kelly
        else:
            confidence = "HIGH - Reliable estimate"
            recommended = min(half_kelly, 0.10)  # Cap at 10%
        
        return KellyResult(
            full_kelly=kelly_pct,
            half_kelly=half_kelly,
            quarter_kelly=quarter_kelly,
            recommended=recommended,
            confidence=confidence
        )
    
    def calculate_kelly_from_trades(self, trades: List[float]) -> KellyResult:
        """
        Calculate Kelly from historical trade P&L list.
        
        Args:
            trades: List of trade returns (e.g., [0.05, -0.03, 0.02, ...])
        """
        wins = [t for t in trades if t > 0]
        losses = [t for t in trades if t <= 0]
        
        if len(losses) == 0 or len(wins) == 0:
            return KellyResult(0, 0, 0, 0, "INSUFFICIENT DATA")
        
        return self.kelly_criterion(
            wins=len(wins),
            losses=len(losses),
            avg_win=np.mean(wins),
            avg_loss=abs(np.mean(losses)),
            kelly_fraction=0.25
        )
```

**Usage Example:**
```python
# Example: System with 55% win rate, 2:1 payoff
sizer = PositionSizer(account_equity=100000)
kelly = sizer.kelly_criterion(
    wins=55, losses=45, 
    avg_win=0.10, avg_loss=0.05
)

print(f"Full Kelly: {kelly.full_kelly:.2%}")
print(f"Quarter Kelly (Recommended): {kelly.quarter_kelly:.2%}")
print(f"Position Size: ${100000 * kelly.recommended:,.2f}")
```

---

### 1.2 Fixed Fractional Sizing

Risk a fixed percentage of equity on each trade.

**Formula:**
```
Position Size = (Account Equity × Risk %) / (Entry Price - Stop Loss Price)
```

```python
    def fixed_fractional(self, 
                        entry_price: float,
                        stop_loss: float,
                        risk_pct: float = 0.01) -> dict:
        """
        Calculate position size based on fixed fractional risk.
        
        Args:
            entry_price: Entry price per share
            stop_loss: Stop loss price
            risk_pct: Percentage of equity to risk (default 1%)
        """
        risk_amount = self.equity * risk_pct
        risk_per_share = abs(entry_price - stop_loss)
        
        if risk_per_share == 0:
            raise ValueError("Risk per share cannot be zero")
        
        shares = int(risk_amount / risk_per_share)
        position_value = shares * entry_price
        position_pct = position_value / self.equity
        
        # Enforce maximum position size
        if position_pct > self.max_position_pct:
            max_shares = int((self.equity * self.max_position_pct) / entry_price)
            shares = min(shares, max_shares)
            position_value = shares * entry_price
            position_pct = position_value / self.equity
            capped = True
        else:
            capped = False
        
        return {
            'shares': shares,
            'position_value': position_value,
            'position_pct': position_pct,
            'risk_amount': risk_amount,
            'risk_per_share': risk_per_share,
            'capped': capped,
            'method': 'fixed_fractional'
        }
```

**Risk Level Guidelines:**

| Risk % | Use Case | Experience Level |
|--------|----------|------------------|
| 0.5% | Conservative / High volatility | Beginner |
| 1.0% | Standard / Normal conditions | Intermediate |
| 2.0% | Aggressive / High confidence | Advanced |
| 3.0%+ | Danger zone / Recovery mode | Expert only |

---

### 1.3 Fixed Ratio Sizing (Ryan Jones Method)

Increase position size only after achieving profit targets.

```python
    def fixed_ratio(self,
                   delta: float = 5000,
                   current_contracts: int = 1,
                   profit: float = 0) -> dict:
        """
        Fixed ratio position sizing.
        
        Args:
            delta: Profit required to increase position by 1 unit
            current_contracts: Current number of contracts/shares
            profit: Current profit level
        """
        # Calculate how many levels we can increase
        cumulative_required = 0
        new_contracts = 1
        
        for i in range(1, 100):  # Cap at 100
            cumulative_required += i * delta
            if profit >= cumulative_required:
                new_contracts = i + 1
            else:
                break
        
        next_level_profit = sum((i + 1) * delta for i in range(new_contracts))
        
        return {
            'current_contracts': current_contracts,
            'recommended_contracts': new_contracts,
            'delta': delta,
            'current_profit': profit,
            'profit_for_next_increase': next_level_profit,
            'profit_needed': next_level_profit - profit,
            'method': 'fixed_ratio'
        }
```

---

### 1.4 Optimal f (Ralph Vince)

Find the optimal fraction that maximizes geometric growth.

```python
    def optimal_f(self, trades: List[float]) -> dict:
        """
        Calculate Optimal f using Ralph Vince's method.
        
        Args:
            trades: Historical trade returns
        """
        if not trades or len(trades) < 10:
            return {'f': 0, 'twr': 0, 'warning': 'Insufficient data'}
        
        # Find worst loss
        worst_loss = min(trades)
        if worst_loss >= 0:
            return {'f': 0, 'twr': 0, 'warning': 'No losses in data'}
        
        # Test f values from 0.01 to 1.0
        best_f = 0
        best_twr = 0
        results = []
        
        for f in np.arange(0.01, 1.01, 0.01):
            twr = 1  # Terminal Wealth Relative
            for trade in trades:
                # HPR = 1 + f × (-trade / worst_loss)
                hpr = 1 + f * (-trade / worst_loss)
                twr *= hpr
            
            results.append({'f': f, 'twr': twr})
            
            if twr > best_twr:
                best_twr = twr
                best_f = f
        
        # Use half f for safety
        safe_f = best_f * 0.5
        
        return {
            'optimal_f': best_f,
            'safe_f': safe_f,
            'terminal_wealth_relative': best_twr,
            'geometric_mean': best_twr ** (1/len(trades)),
            'worst_loss': worst_loss,
            'safety_warning': 'Use half f or less in practice',
            'method': 'optimal_f'
        }
```

---

### 1.5 Risk-Parity Position Sizing

Allocate risk equally across positions based on volatility.

```python
    def risk_parity(self,
                   assets: List[dict],
                   target_volatility: float = 0.10) -> dict:
        """
        Risk-parity allocation based on inverse volatility.
        
        Args:
            assets: List of {'symbol': str, 'volatility': float, 'price': float}
            target_volatility: Target annualized volatility (default 10%)
        """
        n = len(assets)
        
        # Calculate inverse volatility weights
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
        
        return {
            'allocations': allocations,
            'target_volatility': target_volatility,
            'method': 'risk_parity'
        }
```

---

## 2. Drawdown Protection

### 2.1 Equity Curve Monitoring

Track the equity curve and adjust position sizing dynamically.

```python
class DrawdownProtection:
    """Comprehensive drawdown protection system"""
    
    def __init__(self, initial_equity: float):
        self.initial_equity = initial_equity
        self.peak_equity = initial_equity
        self.current_equity = initial_equity
        self.equity_history = [initial_equity]
        self.drawdown_thresholds = {
            'warning': 0.05,      # 5% - Reduce size by 25%
            'caution': 0.10,      # 10% - Reduce size by 50%
            'danger': 0.15,       # 15% - Reduce size by 75%
            'stop': 0.20          # 20% - STOP TRADING
        }
        self.consecutive_losses = 0
        self.max_consecutive_losses = 5
    
    def update_equity(self, new_equity: float):
        """Update equity and check drawdown levels"""
        self.current_equity = new_equity
        self.equity_history.append(new_equity)
        
        # Update peak
        if new_equity > self.peak_equity:
            self.peak_equity = new_equity
            self.consecutive_losses = 0  # Reset on new high
        else:
            self.consecutive_losses += 1
        
        return self.get_drawdown_status()
    
    def get_drawdown_status(self) -> dict:
        """Get current drawdown status and recommended actions"""
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
        
        # Determine level and action
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
                'action': 'Reduce to 25% position size, review system'
            })
        elif drawdown >= self.drawdown_thresholds['caution']:
            status.update({
                'level': 'CAUTION',
                'position_multiplier': 0.50,
                'action': 'Reduce to 50% position size, increase scrutiny'
            })
        elif drawdown >= self.drawdown_thresholds['warning']:
            status.update({
                'level': 'WARNING',
                'position_multiplier': 0.75,
                'action': 'Reduce to 75% position size, monitor closely'
            })
        
        # Check consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            status['action'] += f" | STOP: {self.consecutive_losses} consecutive losses"
            status['can_trade'] = False
        
        return status
```

---

### 2.2 Circuit Breakers

Automatic trading halt triggers.

```python
    def check_circuit_breakers(self, 
                              daily_pnl: float,
                              trades_today: int) -> dict:
        """
        Check if any circuit breakers should trigger.
        
        Returns dict with breaker status and actions.
        """
        daily_loss_pct = abs(daily_pnl) / self.current_equity if daily_pnl < 0 else 0
        
        breakers = {
            'daily_loss_limit': {
                'limit': 0.03,  # 3% daily loss
                'triggered': daily_loss_pct >= 0.03,
                'action': 'HALT TRADING FOR TODAY'
            },
            'weekly_loss_limit': {
                'limit': 0.07,  # 7% weekly loss
                'triggered': self._check_weekly_loss() >= 0.07,
                'action': 'HALT TRADING FOR WEEK'
            },
            'consecutive_losses': {
                'limit': self.max_consecutive_losses,
                'triggered': self.consecutive_losses >= self.max_consecutive_losses,
                'action': 'MANDATORY 24-HOUR BREAK'
            },
            'volatility_spike': {
                'limit': 2.0,  # 2x normal volatility
                'triggered': self._check_volatility_spike(),
                'action': 'REDUCE SIZE BY 50%'
            }
        }
        
        any_triggered = any(b['triggered'] for b in breakers.values())
        
        return {
            'breakers': breakers,
            'any_triggered': any_triggered,
            'halt_trading': any_triggered,
            'timestamp': pd.Timestamp.now()
        }
    
    def _check_weekly_loss(self) -> float:
        """Calculate weekly loss percentage"""
        if len(self.equity_history) < 5:
            return 0
        week_ago_equity = self.equity_history[-min(5, len(self.equity_history))]
        return (week_ago_equity - self.current_equity) / week_ago_equity
    
    def _check_volatility_spike(self) -> bool:
        """Check for abnormal volatility"""
        if len(self.equity_history) < 20:
            return False
        recent_returns = np.diff(self.equity_history[-20:]) / self.equity_history[-21:-1]
        current_vol = np.std(recent_returns[-5:])
        historical_vol = np.std(recent_returns)
        return current_vol > historical_vol * 2 if historical_vol > 0 else False
```

---

### 2.3 Volatility Targeting

Adjust position sizes based on market volatility.

```python
class VolatilityTargeting:
    """Dynamic position sizing based on volatility"""
    
    def __init__(self, target_volatility: float = 0.10):
        self.target_vol = target_volatility  # 10% annualized
        self.volatility_history = []
    
    def calculate_volatility_multiplier(self, 
                                       recent_returns: List[float]) -> float:
        """
        Calculate position size multiplier based on current vs target volatility.
        
        When volatility is high, reduce position size.
        When volatility is low, can increase position size.
        """
        if len(recent_returns) < 20:
            return 1.0
        
        # Calculate current annualized volatility
        current_vol = np.std(recent_returns) * np.sqrt(252)
        
        # Store for tracking
        self.volatility_history.append(current_vol)
        
        # Multiplier = target / current
        # If current vol is 20% and target is 10%, multiplier = 0.5 (half size)
        multiplier = self.target_vol / current_vol if current_vol > 0 else 1.0
        
        # Cap multiplier for safety
        return max(0.25, min(multiplier, 1.5))
    
    def get_position_adjustment(self, 
                               symbol: str, 
                               base_position: float,
                               atr_20: float,
                               price: float) -> dict:
        """
        Get volatility-adjusted position size.
        
        Args:
            symbol: Trading symbol
            base_position: Base position size in dollars
            atr_20: 20-day Average True Range
            price: Current price
        """
        # ATR as percentage of price
        atr_pct = atr_20 / price
        
        # Expected annual volatility from ATR
        expected_vol = atr_pct * np.sqrt(252)
        
        # Adjustment factor
        adjustment = self.target_vol / expected_vol if expected_vol > 0 else 1.0
        
        # Cap for safety
        adjustment = max(0.5, min(adjustment, 1.5))
        
        adjusted_position = base_position * adjustment
        
        return {
            'symbol': symbol,
            'base_position': base_position,
            'adjusted_position': adjusted_position,
            'adjustment_factor': adjustment,
            'atr_pct': atr_pct,
            'expected_vol': expected_vol,
            'target_vol': self.target_vol
        }
```

---

### 2.4 Maximum Adverse Excursion (MAE) Analysis

Use historical MAE to set realistic stops.

```python
class MAEAnalysis:
    """Maximum Adverse Excursion analysis for stop placement"""
    
    def __init__(self):
        self.trade_data = []
    
    def add_trade(self, 
                  entry_price: float,
                  exit_price: float,
                  lowest_price: float,
                  highest_price: float,
                  direction: str):
        """
        Record trade data for MAE analysis.
        
        Args:
            entry_price: Entry price
            exit_price: Exit price
            lowest_price: Lowest price during trade (for longs)
            highest_price: Highest price during trade (for longs)
            direction: 'long' or 'short'
        """
        if direction == 'long':
            mae = (entry_price - lowest_price) / entry_price
            mfe = (highest_price - entry_price) / entry_price
        else:
            mae = (highest_price - entry_price) / entry_price
            mfe = (entry_price - lowest_price) / entry_price
        
        trade_result = (exit_price - entry_price) / entry_price
        if direction == 'short':
            trade_result = -trade_result
        
        self.trade_data.append({
            'entry': entry_price,
            'exit': exit_price,
            'mae': mae,
            'mfe': mfe,
            'result': trade_result,
            'direction': direction,
            'winner': trade_result > 0
        })
    
    def analyze(self) -> dict:
        """Analyze MAE data and recommend stop levels"""
        if len(self.trade_data) < 10:
            return {'error': 'Insufficient trade data'}
        
        winners = [t for t in self.trade_data if t['winner']]
        losers = [t for t in self.trade_data if not t['winner']]
        
        # MAE statistics for winners
        winner_mae = [t['mae'] for t in winners]
        loser_mae = [t['mae'] for t in losers]
        
        analysis = {
            'total_trades': len(self.trade_data),
            'winners': len(winners),
            'losers': len(losers),
            'win_rate': len(winners) / len(self.trade_data),
            
            'winner_mae': {
                'mean': np.mean(winner_mae) if winner_mae else 0,
                'median': np.median(winner_mae) if winner_mae else 0,
                'max': max(winner_mae) if winner_mae else 0,
                'percentile_95': np.percentile(winner_mae, 95) if winner_mae else 0
            },
            
            'loser_mae': {
                'mean': np.mean(loser_mae) if loser_mae else 0,
                'median': np.median(loser_mae) if loser_mae else 0,
                'max': max(loser_mae) if loser_mae else 0,
                'percentile_50': np.percentile(loser_mae, 50) if loser_mae else 0
            },
            
            'recommendations': {}
        }
        
        # Recommend stop levels
        if winner_mae and loser_mae:
            # Conservative: Use 95th percentile of winner MAE
            conservative_stop = np.percentile(winner_mae, 95)
            # Aggressive: Use median loser MAE
            aggressive_stop = np.percentile(loser_mae, 50)
            # Moderate: Average of the two
            moderate_stop = (conservative_stop + aggressive_stop) / 2
            
            analysis['recommendations'] = {
                'conservative_stop_pct': conservative_stop,
                'moderate_stop_pct': moderate_stop,
                'aggressive_stop_pct': aggressive_stop,
                'rationale': 'Based on MAE analysis of historical trades'
            }
        
        return analysis
```

---

## 3. Portfolio-Level Risk

### 3.1 Correlation-Based Position Limits

Prevent concentration in correlated assets.

```python
class PortfolioRiskManager:
    """Portfolio-level risk management"""
    
    def __init__(self, total_equity: float):
        self.equity = total_equity
        self.positions = {}
        self.correlation_matrix = None
        self.sector_exposure = {}
        
        # Limits
        self.max_single_position = 0.15  # 15% max single position
        self.max_correlated_exposure = 0.25  # 25% max correlated group
        self.max_sector_exposure = 0.30  # 30% max sector
    
    def add_position(self, 
                    symbol: str, 
                    value: float, 
                    sector: str,
                    beta: float = 1.0):
        """Add or update position"""
        self.positions[symbol] = {
            'value': value,
            'sector': sector,
            'beta': beta,
            'pct_of_equity': value / self.equity
        }
        
        # Update sector exposure
        self._update_sector_exposure()
    
    def _update_sector_exposure(self):
        """Calculate sector concentrations"""
        self.sector_exposure = {}
        for pos in self.positions.values():
            sector = pos['sector']
            if sector not in self.sector_exposure:
                self.sector_exposure[sector] = 0
            self.sector_exposure[sector] += pos['pct_of_equity']
    
    def check_position_limits(self, new_symbol: str, new_value: float) -> dict:
        """
        Check if new position violates limits.
        
        Returns approval status and any warnings.
        """
        new_pct = new_value / self.equity
        warnings = []
        approved = True
        
        # Check single position limit
        if new_pct > self.max_single_position:
            warnings.append(f"Position {new_pct:.1%} exceeds max single position {self.max_single_position:.1%}")
            approved = False
        
        # Check total portfolio exposure
        current_exposure = sum(p['pct_of_equity'] for p in self.positions.values())
        if current_exposure + new_pct > 1.0:
            warnings.append(f"Total exposure would exceed 100%")
            approved = False
        
        return {
            'approved': approved,
            'warnings': warnings,
            'new_exposure': current_exposure + new_pct,
            'current_exposure': current_exposure
        }
    
    def calculate_portfolio_var(self, 
                               confidence: float = 0.95,
                               time_horizon: int = 1) -> dict:
        """
        Calculate portfolio Value at Risk.
        
        Args:
            confidence: Confidence level (e.g., 0.95 for 95%)
            time_horizon: Days (1 for daily VaR)
        """
        if not self.positions:
            return {'var': 0, 'cvar': 0}
        
        # Simplified parametric VaR calculation
        # In practice, use historical simulation or Monte Carlo
        
        portfolio_value = sum(p['value'] for p in self.positions.values())
        
        # Calculate weighted volatility
        # This is simplified - should use covariance matrix
        weighted_vol = 0
        for pos in self.positions.values():
            # Assume 20% annual volatility as default
            asset_vol = 0.20 * np.sqrt(time_horizon / 252)
            weighted_vol += (pos['pct_of_equity'] * asset_vol) ** 2
        
        portfolio_vol = np.sqrt(weighted_vol)
        
        # VaR = Z-score × volatility × portfolio value
        z_score = {0.90: 1.28, 0.95: 1.645, 0.99: 2.33}.get(confidence, 1.645)
        
        var = z_score * portfolio_vol * portfolio_value
        
        return {
            'var_amount': var,
            'var_pct': var / portfolio_value if portfolio_value > 0 else 0,
            'confidence': confidence,
            'time_horizon_days': time_horizon,
            'portfolio_value': portfolio_value,
            'portfolio_volatility': portfolio_vol
        }
```

---

### 3.2 Beta Neutrality

Maintain market-neutral exposure.

```python
    def calculate_portfolio_beta(self) -> dict:
        """Calculate overall portfolio beta"""
        if not self.positions:
            return {'portfolio_beta': 0, 'status': 'No positions'}
        
        total_value = sum(p['value'] for p in self.positions.values())
        weighted_beta = sum(
            p['value'] * p.get('beta', 1.0) for p in self.positions.values()
        ) / total_value
        
        # Determine status
        if abs(weighted_beta - 1.0) < 0.1:
            status = 'Market neutral'
        elif weighted_beta > 1.2:
            status = 'High beta - vulnerable to market drops'
        elif weighted_beta < 0.8:
            status = 'Low beta - conservative'
        else:
            status = 'Moderate beta'
        
        return {
            'portfolio_beta': weighted_beta,
            'status': status,
            'hedge_required': (1 - weighted_beta) * total_value,
            'total_long_exposure': total_value
        }
    
    def suggest_hedge(self, market_beta: float = 1.0) -> dict:
        """Suggest hedge position to achieve beta neutrality"""
        beta_info = self.calculate_portfolio_beta()
        portfolio_beta = beta_info['portfolio_beta']
        total_value = beta_info['total_long_exposure']
        
        # Required hedge
        beta_adjustment = 1.0 - portfolio_beta
        hedge_value = -beta_adjustment * total_value
        
        return {
            'current_beta': portfolio_beta,
            'target_beta': market_beta,
            'suggested_hedge_value': hedge_value,
            'hedge_direction': 'SHORT' if hedge_value < 0 else 'LONG',
            'hedge_instruments': ['SPY', 'QQQ', 'IWM', 'ES Futures'],
            'rationale': f'Reduce beta from {portfolio_beta:.2f} to {market_beta:.2f}'
        }
```

---

### 3.3 Sector Exposure Monitoring

```python
    def get_sector_exposure_report(self) -> dict:
        """Generate sector exposure report"""
        report = {
            'sectors': {},
            'over_exposed': [],
            'under_exposed': [],
            'recommendations': []
        }
        
        for sector, exposure in self.sector_exposure.items():
            status = 'OK'
            if exposure > self.max_sector_exposure:
                status = 'OVER LIMIT'
                report['over_exposed'].append(sector)
                report['recommendations'].append(
                    f"Reduce {sector} exposure from {exposure:.1%} to {self.max_sector_exposure:.1%}"
                )
            elif exposure < 0.05:
                status = 'MINIMAL'
                report['under_exposed'].append(sector)
            
            report['sectors'][sector] = {
                'exposure_pct': exposure,
                'value': exposure * self.equity,
                'status': status
            }
        
        return report
```

---

## 4. Stop Loss Strategies

### 4.1 ATR-Based Stops

```python
class StopLossManager:
    """Advanced stop loss calculations"""
    
    def __init__(self):
        self.atr_multiplier = {
            'tight': 1.5,
            'normal': 2.0,
            'wide': 3.0,
            'volatility_adjusted': 'dynamic'
        }
    
    def atr_stop(self, 
                 entry_price: float,
                 atr: float,
                 direction: str = 'long',
                 multiplier: float = 2.0) -> dict:
        """
        Calculate ATR-based stop loss.
        
        Args:
            entry_price: Entry price
            atr: Current ATR value
            direction: 'long' or 'short'
            multiplier: ATR multiplier (2.0 = 2x ATR)
        """
        stop_distance = atr * multiplier
        
        if direction == 'long':
            stop_price = entry_price - stop_distance
        else:
            stop_price = entry_price + stop_distance
        
        stop_pct = stop_distance / entry_price
        
        return {
            'entry_price': entry_price,
            'stop_price': stop_price,
            'stop_distance': stop_distance,
            'stop_pct': stop_pct,
            'atr': atr,
            'multiplier': multiplier,
            'direction': direction
        }
    
    def chandelier_exit(self,
                       high_prices: List[float],
                       low_prices: List[float],
                       close_prices: List[float],
                       period: int = 22,
                       atr_period: int = 22,
                       multiplier: float = 3.0) -> dict:
        """
        Chandelier Exit indicator for trailing stops.
        
        Based on highest high minus ATR multiple.
        """
        import pandas as pd
        
        df = pd.DataFrame({
            'high': high_prices,
            'low': low_prices,
            'close': close_prices
        })
        
        # Calculate ATR
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['close'].shift())
        df['tr3'] = abs(df['low'] - df['close'].shift())
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        df['atr'] = df['tr'].rolling(atr_period).mean()
        
        # Highest high and lowest low
        df['highest_high'] = df['high'].rolling(period).max()
        df['lowest_low'] = df['low'].rolling(period).min()
        
        # Chandelier exit
        df['chandelier_long'] = df['highest_high'] - df['atr'] * multiplier
        df['chandelier_short'] = df['lowest_low'] + df['atr'] * multiplier
        
        latest = df.iloc[-1]
        
        return {
            'long_stop': latest['chandelier_long'],
            'short_stop': latest['chandelier_short'],
            'highest_high': latest['highest_high'],
            'lowest_low': latest['lowest_low'],
            'atr': latest['atr'],
            'period': period,
            'multiplier': multiplier
        }
```

---

### 4.2 Trailing Stops

```python
    def trailing_stop(self,
                     entry_price: float,
                     current_price: float,
                     highest_price: float,
                     trail_pct: float = 0.10) -> dict:
        """
        Calculate trailing stop price.
        
        Args:
            entry_price: Initial entry price
            current_price: Current market price
            highest_price: Highest price since entry
            trail_pct: Trailing percentage (e.g., 0.10 = 10%)
        """
        # Calculate current profit
        current_profit_pct = (current_price - entry_price) / entry_price
        
        # Trailing stop moves up with price
        trail_distance = highest_price * trail_pct
        stop_price = highest_price - trail_distance
        
        # Ensure stop is above breakeven if in profit
        if stop_price < entry_price and current_profit_pct > 0:
            stop_price = max(stop_price, entry_price)
        
        return {
            'entry_price': entry_price,
            'current_price': current_price,
            'highest_price': highest_price,
            'stop_price': stop_price,
            'trail_pct': trail_pct,
            'current_profit_pct': current_profit_pct,
            'locked_profit_pct': (stop_price - entry_price) / entry_price if stop_price > entry_price else 0,
            'status': 'Trailing' if current_price > entry_price else 'Waiting for profit'
        }
    
    def parabolic_sar_stop(self,
                          high_prices: List[float],
                          low_prices: List[float],
                          af_start: float = 0.02,
                          af_increment: float = 0.02,
                          af_max: float = 0.20) -> dict:
        """
        Parabolic SAR for dynamic stop placement.
        
        Accelerating stop that moves closer to price as trend continues.
        """
        import pandas as pd
        import numpy as np
        
        df = pd.DataFrame({'high': high_prices, 'low': low_prices})
        
        # Initialize
        sar = [df['low'].iloc[0]]
        ep = df['high'].iloc[0]  # Extreme point
        af = af_start
        trend = 1  # 1 for uptrend, -1 for downtrend
        
        for i in range(1, len(df)):
            if trend == 1:  # Uptrend
                new_sar = sar[-1] + af * (ep - sar[-1])
                # Ensure SAR is below recent lows
                new_sar = min(new_sar, df['low'].iloc[max(0, i-2):i].min())
                
                if df['low'].iloc[i] < new_sar:  # Trend reversal
                    trend = -1
                    sar.append(ep)
                    ep = df['low'].iloc[i]
                    af = af_start
                else:
                    sar.append(new_sar)
                    if df['high'].iloc[i] > ep:
                        ep = df['high'].iloc[i]
                        af = min(af + af_increment, af_max)
            else:  # Downtrend
                new_sar = sar[-1] + af * (ep - sar[-1])
                new_sar = max(new_sar, df['high'].iloc[max(0, i-2):i].max())
                
                if df['high'].iloc[i] > new_sar:
                    trend = 1
                    sar.append(ep)
                    ep = df['high'].iloc[i]
                    af = af_start
                else:
                    sar.append(new_sar)
                    if df['low'].iloc[i] < ep:
                        ep = df['low'].iloc[i]
                        af = min(af + af_increment, af_max)
        
        return {
            'sar_values': sar,
            'current_sar': sar[-1],
            'current_af': af,
            'trend': 'UP' if trend == 1 else 'DOWN',
            'extreme_point': ep
        }
```

---

### 4.3 Time-Based Stops

```python
    def time_stop(self,
                 entry_date: str,
                 max_holding_days: int = 20,
                 profit_target: float = None) -> dict:
        """
        Time-based exit strategy.
        
        Exit if position held too long without hitting target.
        """
        from datetime import datetime, timedelta
        
        entry = datetime.strptime(entry_date, '%Y-%m-%d')
        exit_date = entry + timedelta(days=max_holding_days)
        days_held = (datetime.now() - entry).days
        
        return {
            'entry_date': entry_date,
            'max_exit_date': exit_date.strftime('%Y-%m-%d'),
            'days_held': days_held,
            'days_remaining': max(0, max_holding_days - days_held),
            'time_expired': days_held >= max_holding_days,
            'profit_target': profit_target,
            'rationale': 'Time stops prevent capital tie-up in stagnant positions'
        }
```

---

## 5. Hedging Techniques

### 5.1 Options Hedging Basics

```python
class OptionsHedge:
    """Basic options hedging calculations"""
    
    def protective_put(self,
                      stock_price: float,
                      shares: int,
                      strike_price: float,
                      put_premium: float,
                      days_to_expiry: int) -> dict:
        """
        Calculate protective put hedge.
        
        Buy puts to protect long stock positions.
        """
        position_value = stock_price * shares
        put_cost = put_premium * shares * 100  # 100 shares per contract
        
        # Breakeven
        breakeven = stock_price + put_premium
        
        # Max loss
        max_loss = (stock_price - strike_price) * shares + put_cost
        max_loss_pct = max_loss / position_value
        
        # Cost as percentage
        hedge_cost_pct = put_cost / position_value
        annualized_cost = hedge_cost_pct * (365 / days_to_expiry)
        
        return {
            'position_value': position_value,
            'shares': shares,
            'strike_price': strike_price,
            'put_premium': put_premium,
            'put_cost_total': put_cost,
            'hedge_cost_pct': hedge_cost_pct,
            'annualized_cost': annualized_cost,
            'breakeven': breakeven,
            'max_loss': max_loss,
            'max_loss_pct': max_loss_pct,
            'protection_level': (strike_price / stock_price - 1),
            'recommendation': 'Costly but effective for major events'
        }
    
    def collar_strategy(self,
                       stock_price: float,
                       shares: int,
                       put_strike: float,
                       put_premium: float,
                       call_strike: float,
                       call_premium: float) -> dict:
        """
        Collar strategy: Protective put + covered call.
        
        Limits both downside and upside.
        """
        position_value = stock_price * shares
        
        # Net premium
        net_premium = (put_premium - call_premium) * shares * 100
        
        # Protected range
        downside_protection = (stock_price - put_strike) / stock_price
        upside_cap = (call_strike - stock_price) / stock_price
        
        # Max loss and gain
        max_loss = (stock_price - put_strike) * shares + net_premium
        max_gain = (call_strike - stock_price) * shares - net_premium
        
        return {
            'position_value': position_value,
            'net_premium': net_premium,
            'downside_protection_pct': downside_protection,
            'upside_cap_pct': upside_cap,
            'max_loss': max_loss,
            'max_gain': max_gain,
            'protected_range': f'{put_strike:.2f} - {call_strike:.2f}',
            'zero_cost': abs(net_premium) < (position_value * 0.001)
        }
```

---

### 5.2 Inverse ETF Hedging

```python
class InverseETFHedge:
    """Hedge using inverse ETFs"""
    
    INVERSE_ETFS = {
        'SPY': 'SH',      # S&P 500 short
        'QQQ': 'PSQ',     # Nasdaq short
        'IWM': 'RWM',     # Russell 2000 short
        'DIA': 'DOG',     # Dow short
        'XLF': 'SEF',     # Financials short
        'XLE': 'DUG',     # Energy short (2x)
        'GLD': 'DGZ'      # Gold short
    }
    
    def calculate_hedge_size(self,
                            portfolio_value: float,
                            portfolio_beta: float = 1.0,
                            hedge_coverage: float = 0.50) -> dict:
        """
        Calculate inverse ETF hedge position.
        
        Args:
            portfolio_value: Total portfolio value
            portfolio_beta: Portfolio beta to market
            hedge_coverage: Percentage of exposure to hedge (0.5 = 50%)
        """
        hedge_value = portfolio_value * portfolio_beta * hedge_coverage
        
        return {
            'portfolio_value': portfolio_value,
            'portfolio_beta': portfolio_beta,
            'hedge_coverage': hedge_coverage,
            'hedge_value': hedge_value,
            'recommended_etfs': {
                'SPY': hedge_value * 0.6,  # 60% in S&P hedge
                'QQQ': hedge_value * 0.4   # 40% in Nasdaq hedge
            },
            'pros': ['Simple', 'No time decay', 'Liquid'],
            'cons': ['Daily reset decay', 'Limited after-hours', 'Tracking error']
        }
```

---

### 5.3 Pairs Trading for Risk Management

```python
class PairsHedge:
    """Use pairs trading to hedge sector exposure"""
    
    def calculate_hedge_ratio(self,
                             asset1_prices: List[float],
                             asset2_prices: List[float]) -> dict:
        """
        Calculate hedge ratio for pairs trading.
        
        Uses linear regression to find optimal ratio.
        """
        from scipy import stats
        
        # Linear regression: asset1 = alpha + beta * asset2
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            asset2_prices, asset1_prices
        )
        
        # Correlation
        correlation = r_value
        
        # Hedge ratio
        hedge_ratio = slope
        
        # Spread
        spread = [a1 - hedge_ratio * a2 for a1, a2 in zip(asset1_prices, asset2_prices)]
        spread_mean = np.mean(spread)
        spread_std = np.std(spread)
        z_score = (spread[-1] - spread_mean) / spread_std if spread_std > 0 else 0
        
        return {
            'hedge_ratio': hedge_ratio,
            'correlation': correlation,
            'r_squared': r_value ** 2,
            'current_spread': spread[-1],
            'spread_mean': spread_mean,
            'spread_std': spread_std,
            'z_score': z_score,
            'trade_signal': self._get_pairs_signal(z_score),
            'position_size_ratio': f'1:{hedge_ratio:.2f}'
        }
    
    def _get_pairs_signal(self, z_score: float) -> str:
        """Generate signal based on z-score"""
        if z_score > 2:
            return 'SHORT Asset1, LONG Asset2 (Spread will contract)'
        elif z_score < -2:
            return 'LONG Asset1, SHORT Asset2 (Spread will expand)'
        elif abs(z_score) < 0.5:
            return 'NO SIGNAL - Spread near mean'
        else:
            return 'WATCH - Building position'
```

---

## 6. Psychological Risk Management

### 6.1 Trading Rules to Prevent Emotional Decisions

```python
class PsychologicalRiskManager:
    """Manage psychological and emotional trading risks"""
    
    def __init__(self):
        self.daily_stats = {
            'trades': [],
            'pnl': 0,
            'wins': 0,
            'losses': 0
        }
        self.rules_violated = []
        self.emotional_state = 'neutral'
    
    TRADING_RULES = {
        'R001': {
            'name': 'No Revenge Trading',
            'description': 'After 3 consecutive losses, take 30-minute break',
            'check': lambda stats: stats['losses'] >= 3,
            'action': 'MANDATORY_BREAK'
        },
        'R002': {
            'name': 'Daily Loss Limit',
            'description': 'Stop trading after 3% daily loss',
            'check': lambda stats: stats['pnl'] < -0.03,
            'action': 'HALT_TRADING'
        },
        'R003': {
            'name': 'No Oversizing',
            'description': 'Position size must be pre-calculated, never increased mid-trade',
            'check': None,  # Manual check
            'action': 'WARNING'
        },
        'R004': {
            'name': 'Pre-Trade Checklist',
            'description': 'Complete checklist before every trade',
            'check': None,  # Manual check
            'action': 'BLOCK_TRADE'
        },
        'R005': {
            'name': 'No FOMO Entries',
            'description': 'Wait for pullback, never chase',
            'check': None,  # Manual check
            'action': 'WARNING'
        }
    }
    
    def check_rules(self, equity: float) -> dict:
        """Check all trading rules"""
        violations = []
        
        for rule_id, rule in self.TRADING_RULES.items():
            if rule['check'] and rule['check'](self.daily_stats):
                violations.append({
                    'rule_id': rule_id,
                    'rule_name': rule['name'],
                    'action': rule['action']
                })
        
        # Determine emotional state
        if len(violations) > 0:
            self.emotional_state = 'AT RISK'
        elif self.daily_stats['losses'] > self.daily_stats['wins']:
            self.emotional_state = 'cautious'
        else:
            self.emotional_state = 'neutral'
        
        return {
            'can_trade': len([v for v in violations if v['action'] == 'HALT_TRADING']) == 0,
            'violations': violations,
            'emotional_state': self.emotional_state,
            'daily_stats': self.daily_stats
        }
```

---

### 6.2 Daily/Weekly Loss Limits

```python
    def update_daily_pnl(self, trade_pnl: float):
        """Update daily P&L and check limits"""
        self.daily_stats['pnl'] += trade_pnl
        
        if trade_pnl > 0:
            self.daily_stats['wins'] += 1
        else:
            self.daily_stats['losses'] += 1
        
        self.daily_stats['trades'].append(trade_pnl)
    
    def get_loss_limit_status(self, 
                             daily_limit: float = 0.03,
                             weekly_limit: float = 0.07) -> dict:
        """
        Check loss limit status.
        
        Returns warnings if approaching limits.
        """
        daily_loss = abs(min(0, self.daily_stats['pnl']))
        weekly_loss = daily_loss * 1.5  # Simplified weekly estimate
        
        status = {
            'daily_loss_pct': daily_loss,
            'daily_limit_pct': daily_limit,
            'daily_remaining': daily_limit - daily_loss,
            'daily_breached': daily_loss >= daily_limit,
            
            'weekly_loss_pct': weekly_loss,
            'weekly_limit_pct': weekly_limit,
            'weekly_remaining': weekly_limit - weekly_loss,
            'weekly_breached': weekly_loss >= weekly_limit,
            
            'warnings': []
        }
        
        if daily_loss >= daily_limit * 0.8:
            status['warnings'].append(f"Approaching daily limit: {daily_loss:.1%}")
        
        if status['daily_breached']:
            status['warnings'].append("DAILY LOSS LIMIT BREACHED - STOP TRADING")
        
        return status
    
    def reset_daily_stats(self):
        """Reset at start of new trading day"""
        self.daily_stats = {
            'trades': [],
            'pnl': 0,
            'wins': 0,
            'losses': 0
        }
        self.rules_violated = []
```

---

### 6.3 Review Process Framework

```python
    def generate_daily_review(self) -> dict:
        """Generate end-of-day review"""
        trades = self.daily_stats['trades']
        
        if not trades:
            return {'message': 'No trades today'}
        
        review = {
            'date': pd.Timestamp.now().strftime('%Y-%m-%d'),
            'total_trades': len(trades),
            'win_rate': self.daily_stats['wins'] / len(trades),
            'total_pnl': sum(trades),
            'avg_win': np.mean([t for t in trades if t > 0]) if any(t > 0 for t in trades) else 0,
            'avg_loss': np.mean([t for t in trades if t < 0]) if any(t < 0 for t in trades) else 0,
            'largest_win': max(trades),
            'largest_loss': min(trades),
            'rules_followed': len(self.TRADING_RULES) - len(self.rules_violated),
            'rules_violated': self.rules_violated,
            'emotional_state': self.emotional_state,
            'lessons': [],
            'tomorrow_focus': []
        }
        
        # Generate lessons
        if review['win_rate'] < 0.4:
            review['lessons'].append('Low win rate - review entry criteria')
        
        if abs(review['avg_loss']) > review['avg_win'] * 1.5:
            review['lessons'].append('Losses larger than wins - tighten stops')
        
        if len(trades) > 10:
            review['lessons'].append('Overtrading detected - be more selective')
        
        return review
```

---

## 7. Black Swan Protection

### 7.1 Tail Risk Hedging

```python
class BlackSwanProtection:
    """Protection against extreme market events"""
    
    def __init__(self, portfolio_value: float):
        self.portfolio_value = portfolio_value
        self.tail_risk_budget = portfolio_value * 0.01  # 1% for hedging
    
    def calculate_vix_hedge(self, 
                           current_vix: float,
                           vix_historical_mean: float = 20) -> dict:
        """
        Calculate VIX-based hedge.
        
        Increase hedge when VIX is low (cheap insurance).
        """
        # VIX percentile calculation
        vix_percentile = current_vix / vix_historical_mean
        
        if current_vix < 15:  # Low volatility regime
            hedge_size = 0.05  # 5% in VIX calls
            urgency = 'HIGH'
        elif current_vix < 20:
            hedge_size = 0.03
            urgency = 'MEDIUM'
        elif current_vix < 25:
            hedge_size = 0.01
            urgency = 'LOW'
        else:
            hedge_size = 0  # Volatility already elevated
            urgency = 'NONE'
        
        hedge_value = self.portfolio_value * hedge_size
        
        return {
            'current_vix': current_vix,
            'vix_percentile': vix_percentile,
            'hedge_size_pct': hedge_size,
            'hedge_value': hedge_value,
            'urgency': urgency,
            'instruments': ['VIX Call Options', 'VIX Futures', 'VXX'],
            'strategy': f'Buy {urgency} urgency VIX protection'
        }
    
    def crash_protection_options(self,
                                spy_price: float,
                                portfolio_beta: float = 1.0) -> dict:
        """
        Calculate crash protection using deep OTM puts.
        """
        # 20% OTM puts
        otm_strike = spy_price * 0.80
        
        # Estimated cost (varies by volatility)
        estimated_cost_pct = 0.005  # 0.5% monthly
        monthly_cost = self.portfolio_value * estimated_cost_pct * portfolio_beta
        annual_cost = monthly_cost * 12
        
        return {
            'protection_level': '20% below current (80% strike)',
            'spy_strike': otm_strike,
            'monthly_cost': monthly_cost,
            'annual_cost': annual_cost,
            'annual_cost_pct': annual_cost / self.portfolio_value,
            'coverage': 'Black swan events (>20% drops)',
            'recommendation': 'Worth 2-5% annual cost for catastrophic protection'
        }
```

---

### 7.2 Liquidity Risk Management

```python
    def liquidity_check(self,
                       symbol: str,
                       position_size: float,
                       avg_daily_volume: int,
                       avg_spread_pct: float) -> dict:
        """
        Check if position can be exited without major slippage.
        """
        # Position as % of daily volume
        position_value = position_size
        volume_pct = position_value / (avg_daily_volume * 100)  # Assuming $100 avg price
        
        # Liquidity score
        if volume_pct < 0.01 and avg_spread_pct < 0.001:
            liquidity = 'EXCELLENT'
            exit_days = 1
        elif volume_pct < 0.05 and avg_spread_pct < 0.005:
            liquidity = 'GOOD'
            exit_days = 1
        elif volume_pct < 0.10 and avg_spread_pct < 0.01:
            liquidity = 'ACCEPTABLE'
            exit_days = 2
        elif volume_pct < 0.25:
            liquidity = 'POOR'
            exit_days = 3
        else:
            liquidity = 'DANGEROUS'
            exit_days = 5
        
        return {
            'symbol': symbol,
            'position_value': position_value,
            'avg_daily_volume': avg_daily_volume,
            'position_as_pct_of_volume': volume_pct,
            'avg_spread_pct': avg_spread_pct,
            'liquidity_rating': liquidity,
            'estimated_exit_days': exit_days,
            'recommendation': 'REDUCE SIZE' if liquidity in ['POOR', 'DANGEROUS'] else 'OK'
        }
    
    def stress_test(self,
                   positions: List[dict],
                   scenario: str = '2008_crash') -> dict:
        """
        Stress test portfolio against historical scenarios.
        
        Scenarios: 2008_crash, 2020_covid, 1987_black_monday
        """
        scenarios = {
            '2008_crash': {
                'spx_drop': -0.57,
                'vix_spike': 80,
                'correlation_spike': 0.90
            },
            '2020_covid': {
                'spx_drop': -0.34,
                'vix_spike': 85,
                'correlation_spike': 0.85
            },
            '1987_black_monday': {
                'spx_drop': -0.20,  # Single day
                'vix_spike': 150,
                'correlation_spike': 0.95
            }
        }
        
        s = scenarios.get(scenario, scenarios['2008_crash'])
        
        # Estimate portfolio loss
        portfolio_value = sum(p['value'] for p in positions)
        avg_beta = np.mean([p.get('beta', 1.0) for p in positions])
        
        estimated_loss = portfolio_value * s['spx_drop'] * avg_beta
        remaining_equity = portfolio_value + estimated_loss
        
        return {
            'scenario': scenario,
            'portfolio_value': portfolio_value,
            'estimated_loss': estimated_loss,
            'estimated_loss_pct': estimated_loss / portfolio_value,
            'remaining_equity': remaining_equity,
            'survivable': remaining_equity > (portfolio_value * 0.70),  # 30% max drawdown
            'recommendations': [
                'Increase cash position',
                'Add VIX calls',
                'Reduce beta exposure'
            ] if remaining_equity < (portfolio_value * 0.80) else []
        }
```

---

## 8. Emergency Protocols

### 8.1 Significant Drawdown Response

```python
class EmergencyProtocol:
    """Emergency response for significant drawdowns"""
    
    EMERGENCY_LEVELS = {
        'LEVEL_1': {
            'drawdown': 0.10,
            'action': 'REDUCE_SIZE',
            'description': 'Reduce position sizes by 50%'
        },
        'LEVEL_2': {
            'drawdown': 0.15,
            'action': 'DEFENSIVE',
            'description': 'Only defensive trades, increase cash to 50%'
        },
        'LEVEL_3': {
            'drawdown': 0.20,
            'action': 'HALT',
            'description': 'HALT ALL TRADING, emergency review required'
        },
        'LEVEL_4': {
            'drawdown': 0.30,
            'action': 'CAPITAL_PRESERVATION',
            'description': 'LIQUIDATE TO CASH, preserve remaining capital'
        }
    }
    
    def assess_emergency(self,
                        current_equity: float,
                        peak_equity: float) -> dict:
        """Assess current emergency level"""
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
            level = 'NORMAL'
        
        if level == 'NORMAL':
            return {'level': 'NORMAL', 'drawdown': drawdown, 'action': 'NONE'}
        
        emergency = self.EMERGENCY_LEVELS[level].copy()
        emergency['drawdown'] = drawdown
        emergency['level'] = level
        emergency['equity_lost'] = peak_equity - current_equity
        emergency['recovery_needed'] = (peak_equity / current_equity) - 1
        
        return emergency
    
    def execute_emergency_action(self, level: str, positions: List[dict]) -> dict:
        """Execute emergency action plan"""
        actions = {
            'LEVEL_1': {
                'close_positions': [],
                'reduce_positions_pct': 0.50,
                'pause_new_trades_hours': 24,
                'mandatory_review': True
            },
            'LEVEL_2': {
                'close_positions': ['speculative', 'high_beta'],
                'reduce_positions_pct': 0.75,
                'target_cash_pct': 0.50,
                'pause_new_trades_hours': 72,
                'mandatory_review': True
            },
            'LEVEL_3': {
                'close_positions': ['all_open'],
                'keep_positions': ['core_holdings'],
                'target_cash_pct': 0.70,
                'pause_new_trades_hours': 168,  # 1 week
                'mandatory_review': True,
                'system_audit_required': True
            },
            'LEVEL_4': {
                'close_positions': ['all'],
                'target_cash_pct': 0.95,
                'pause_new_trades_hours': 720,  # 1 month
                'mandatory_review': True,
                'external_consultation': True,
                'capital_preservation_mode': True
            }
        }
        
        return {
            'level': level,
            'action_plan': actions.get(level, {}),
            'timestamp': pd.Timestamp.now().isoformat(),
            'next_review': (pd.Timestamp.now() + pd.Timedelta(hours=actions.get(level, {}).get('pause_new_trades_hours', 0))).isoformat()
        }
```

---

### 8.2 Recovery Plan Template

```python
    def generate_recovery_plan(self,
                              current_equity: float,
                              peak_equity: float,
                              max_acceptable_risk: float = 0.01) -> dict:
        """
        Generate recovery plan after drawdown.
        
        Focus on capital preservation during recovery.
        """
        drawdown = (peak_equity - current_equity) / peak_equity
        recovery_needed = (peak_equity / current_equity) - 1
        
        # Recovery time estimates at different return rates
        monthly_returns = [0.02, 0.05, 0.10]
        recovery_estimates = {}
        
        for ret in monthly_returns:
            months = np.log(1 + recovery_needed) / np.log(1 + ret)
            recovery_estimates[f'{ret:.0%}_monthly'] = {
                'months': int(np.ceil(months)),
                'years': round(months / 12, 1)
            }
        
        plan = {
            'current_situation': {
                'current_equity': current_equity,
                'peak_equity': peak_equity,
                'drawdown': drawdown,
                'recovery_needed': recovery_needed
            },
            
            'phase_1_stabilize': {
                'duration': 'Week 1-2',
                'risk_per_trade': min(0.005, max_acceptable_risk),  # 0.5%
                'max_positions': 3,
                'focus': 'High-probability setups only',
                'cash_target': 0.50
            },
            
            'phase_2_recover': {
                'duration': 'Week 3-8',
                'risk_per_trade': min(0.01, max_acceptable_risk),  # 1%
                'max_positions': 5,
                'focus': 'Proven strategies only',
                'cash_target': 0.30
            },
            
            'phase_3_growth': {
                'duration': 'After new highs',
                'risk_per_trade': max_acceptable_risk,
                'max_positions': 10,
                'focus': 'Resume normal operations',
                'cash_target': 0.10
            },
            
            'recovery_estimates': recovery_estimates,
            
            'rules': [
                'No new strategies until fully recovered',
                'Daily journaling mandatory',
                'Weekly progress reviews',
                'Reduce size on any additional loss',
                'Focus on base hits, not home runs'
            ]
        }
        
        return plan
```

---

## 9. Implementation Checklist

### Pre-Trade Risk Checklist

```python
class PreTradeChecklist:
    """Mandatory checklist before executing any trade"""
    
    CHECKLIST_ITEMS = [
        {'id': 'R1', 'item': 'Position size calculated using 1% risk rule', 'critical': True},
        {'id': 'R2', 'item': 'Stop loss price determined and entered', 'critical': True},
        {'id': 'R3', 'item': 'Risk/Reward ratio at least 1:2', 'critical': True},
        {'id': 'R4', 'item': 'Daily loss limit not exceeded', 'critical': True},
        {'id': 'R5', 'item': 'Not in revenge trading mode', 'critical': True},
        {'id': 'R6', 'item': 'Market conditions suitable for strategy', 'critical': False},
        {'id': 'R7', 'item': 'Position within sector limits', 'critical': True},
        {'id': 'R8', 'item': 'Liquidity adequate for exit', 'critical': True},
        {'id': 'R9', 'item': 'Correlated positions under limit', 'critical': False},
        {'id': 'R10', 'item': 'Emotional state is neutral/positive', 'critical': True}
    ]
    
    def run_checklist(self, answers: dict) -> dict:
        """
        Run pre-trade checklist.
        
        Args:
            answers: Dict mapping item ID to True/False
        """
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
            'all_passed': critical_failures == 0 and all(answers.get(i['id'], False) for i in self.CHECKLIST_ITEMS),
            'critical_passed': critical_failures == 0,
            'critical_failures': critical_failures,
            'results': results,
            'can_trade': critical_failures == 0,
            'timestamp': pd.Timestamp.now().isoformat()
        }
```

---

### Risk Parameter Quick Reference

| Parameter | Conservative | Normal | Aggressive |
|-----------|--------------|--------|------------|
| Risk per trade | 0.5% | 1.0% | 2.0% |
| Max daily loss | 2% | 3% | 5% |
| Max weekly loss | 5% | 7% | 10% |
| Max drawdown (halt) | 10% | 15% | 20% |
| Max single position | 10% | 15% | 25% |
| Max sector exposure | 20% | 30% | 50% |
| Target volatility | 8% | 12% | 20% |
| Kelly fraction | 0.10 | 0.25 | 0.50 |

---

### Daily Risk Monitoring Dashboard

```python
class RiskDashboard:
    """Daily risk monitoring summary"""
    
    def generate_report(self,
                       equity: float,
                       peak_equity: float,
                       positions: List[dict],
                       daily_pnl: float) -> dict:
        """Generate comprehensive risk dashboard"""
        
        dd_protection = DrawdownProtection(peak_equity)
        dd_status = dd_protection.update_equity(equity)
        
        portfolio = PortfolioRiskManager(equity)
        for pos in positions:
            portfolio.add_position(
                pos['symbol'], 
                pos['value'], 
                pos.get('sector', 'unknown'),
                pos.get('beta', 1.0)
            )
        
        return {
            'summary': {
                'equity': equity,
                'peak_equity': peak_equity,
                'drawdown': dd_status['drawdown_pct'],
                'daily_pnl': daily_pnl,
                'daily_pnl_pct': daily_pnl / equity,
                'status': dd_status['level']
            },
            
            'drawdown': dd_status,
            
            'portfolio': {
                'beta': portfolio.calculate_portfolio_beta(),
                'sector_exposure': portfolio.get_sector_exposure_report(),
                'var_95': portfolio.calculate_portfolio_var(confidence=0.95)
            },
            
            'circuit_breakers': dd_protection.check_circuit_breakers(daily_pnl, len(positions)),
            
            'recommendations': self._generate_recommendations(dd_status, portfolio)
        }
    
    def _generate_recommendations(self, dd_status: dict, portfolio: PortfolioRiskManager) -> List[str]:
        """Generate risk-based recommendations"""
        recs = []
        
        if dd_status['level'] != 'normal':
            recs.append(f"Drawdown alert: {dd_status['action']}")
        
        if dd_status['consecutive_losses'] >= 3:
            recs.append(f"Stop trading: {dd_status['consecutive_losses']} consecutive losses")
        
        beta_info = portfolio.calculate_portfolio_beta()
        if beta_info['portfolio_beta'] > 1.2:
            recs.append("High beta exposure - consider hedging")
        
        return recs
```

---

## Summary

### Key Principles

1. **Capital Preservation > Profit Maximization**
   - When in doubt, reduce size
   - Live to trade another day

2. **Multiple Layers of Defense**
   - Position sizing (per-trade protection)
   - Stop losses (individual trade limits)
   - Drawdown controls (system-level protection)
   - Portfolio risk (correlation protection)
   - Emergency protocols (survival mode)

3. **Pre-Defined Rules**
   - Never override risk rules due to emotion
   - All decisions made before the trade
   - Checklists prevent impulsive mistakes

4. **Continuous Monitoring**
   - Daily risk dashboard
   - Real-time drawdown tracking
   - Weekly strategy review

### Immediate Actions for Current Situation

1. **Implement 1% risk per trade immediately**
2. **Set daily loss limit at 3% and weekly at 7%**
3. **Halt trading if drawdown reaches 15%**
4. **Review all open positions for proper stop placement**
5. **Reduce overall exposure until system recovers**

---

*Document Version: 1.0*  
*Last Updated: February 15, 2026*  
*Next Review: After system recovery*
