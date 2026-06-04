#!/usr/bin/env python3
"""
Circuit Breaker System - Risk Management
Addresses: No automatic risk controls, correlation monitoring
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np


class CircuitBreakerSystem:
    """
    Automatic risk controls to protect trading capital.
    """
    
    def __init__(self, 
                 daily_loss_limit: float = 0.05,      # 5% daily loss halt
                 max_drawdown_limit: float = 0.20,     # 20% max drawdown
                 consecutive_loss_limit: int = 5,      # Reduce size after 5 losses
                 volatility_spike_threshold: float = 3.0,  # 3x ATR spike
                 correlation_threshold: float = 0.7):   # Alert at 0.7 correlation
        
        self.limits = {
            'daily_loss': daily_loss_limit,
            'max_drawdown': max_drawdown_limit,
            'consecutive_losses': consecutive_loss_limit,
            'volatility_spike': volatility_spike_threshold,
            'correlation': correlation_threshold
        }
        
        self.state = {
            'trading_enabled': True,
            'position_size_multiplier': 1.0,
            'daily_pnl': 0.0,
            'consecutive_losses': 0,
            'peak_equity': 0.0,
            'current_drawdown': 0.0,
            'alerts': []
        }
    
    def check_all(self, portfolio: Dict) -> Dict:
        """Run all circuit breaker checks."""
        alerts = []
        
        # Check 1: Daily loss limit
        daily_pnl = portfolio.get('daily_pnl_pct', 0)
        if daily_pnl < -self.limits['daily_loss']:
            self.state['trading_enabled'] = False
            alerts.append({
                'level': 'CRITICAL',
                'type': 'DAILY_LOSS_HALT',
                'message': f"Daily loss {daily_pnl:.2%} exceeds limit {self.limits['daily_loss']:.2%}",
                'action': 'HALT_TRADING'
            })
        
        # Check 2: Max drawdown
        current_equity = portfolio.get('equity', 0)
        self.state['peak_equity'] = max(self.state['peak_equity'], current_equity)
        if self.state['peak_equity'] > 0:
            drawdown = (self.state['peak_equity'] - current_equity) / self.state['peak_equity']
            if drawdown > self.limits['max_drawdown']:
                self.state['trading_enabled'] = False
                alerts.append({
                    'level': 'CRITICAL',
                    'type': 'MAX_DRAWDOWN_HALT',
                    'message': f"Drawdown {drawdown:.2%} exceeds limit {self.limits['max_drawdown']:.2%}",
                    'action': 'HALT_TRADING'
                })
        
        # Check 3: Consecutive losses
        recent_trades = portfolio.get('recent_trades', [])
        losses = sum(1 for t in recent_trades[-10:] if (t.get('pnl') or 0) < 0)
        if losses >= self.limits['consecutive_losses']:
            self.state['position_size_multiplier'] = 0.5  # Reduce size
            alerts.append({
                'level': 'WARNING',
                'type': 'CONSECUTIVE_LOSSES',
                'message': f"{losses} consecutive losses - reducing position size 50%",
                'action': 'REDUCE_SIZE'
            })
        
        # Check 4: Volatility spike
        current_atr = portfolio.get('current_atr', 0)
        avg_atr = portfolio.get('avg_atr', current_atr)
        if avg_atr > 0 and current_atr > self.limits['volatility_spike'] * avg_atr:
            self.state['position_size_multiplier'] *= 0.7  # Reduce 30%
            alerts.append({
                'level': 'WARNING',
                'type': 'VOLATILITY_SPIKE',
                'message': f"ATR {current_atr:.2f} is {current_atr/avg_atr:.1f}x average",
                'action': 'REDUCE_SIZE'
            })
        
        # Check 5: Correlation spike
        correlations = portfolio.get('correlations', [])
        if correlations:
            avg_corr = np.mean([abs(c) for c in correlations])
            if avg_corr > self.limits['correlation']:
                alerts.append({
                    'level': 'WARNING',
                    'type': 'CORRELATION_SPIKE',
                    'message': f"Average correlation {avg_corr:.2f} exceeds {self.limits['correlation']}",
                    'action': 'DIVERSIFY_ALERT'
                })
        
        self.state['alerts'] = alerts
        return {
            'trading_enabled': self.state['trading_enabled'],
            'position_size_multiplier': self.state['position_size_multiplier'],
            'alerts': alerts
        }
    
    def reset_daily(self):
        """Reset daily counters."""
        self.state['daily_pnl'] = 0.0
        self.state['trading_enabled'] = True
        self.state['alerts'] = []
