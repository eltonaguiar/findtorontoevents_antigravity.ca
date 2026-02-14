#!/usr/bin/env python3
"""
================================================================================
CIRCUIT BREAKER SYSTEM
================================================================================
Automatic trading halt triggers to prevent catastrophic losses
================================================================================
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class CircuitStatus(Enum):
    GREEN = "green"      # Normal operation
    YELLOW = "yellow"    # Caution - reduced sizing
    RED = "red"          # Halt trading
    BLACK = "black"      # Emergency - liquidate all


@dataclass
class CircuitBreaker:
    """Trading circuit breaker configuration"""
    
    # Daily limits
    max_daily_loss_pct: float = 5.0
    max_consecutive_losses: int = 3
    
    # Weekly limits
    max_weekly_loss_pct: float = 10.0
    min_weekly_win_rate: float = 30.0
    
    # Monthly limits
    max_monthly_drawdown_pct: float = 20.0
    min_monthly_sharpe: float = 0.5
    
    # Market conditions
    max_btc_daily_drop_pct: float = 10.0
    max_vix: float = 40.0
    
    def check_circuits(self, portfolio: Dict) -> Tuple[CircuitStatus, List[str]]:
        """
        Check all circuit breakers
        
        Returns:
            (status, list of triggered rules)
        """
        triggered = []
        
        # Check daily loss
        daily_pnl = portfolio.get('daily_pnl_pct', 0)
        if daily_pnl <= -self.max_daily_loss_pct:
            triggered.append(f"Daily loss {daily_pnl:.1f}% exceeds {self.max_daily_loss_pct}% limit")
        
        # Check consecutive losses
        consecutive = portfolio.get('consecutive_losses', 0)
        if consecutive >= self.max_consecutive_losses:
            triggered.append(f"{consecutive} consecutive losses")
        
        # Check weekly loss
        weekly_pnl = portfolio.get('weekly_pnl_pct', 0)
        if weekly_pnl <= -self.max_weekly_loss_pct:
            triggered.append(f"Weekly loss {weekly_pnl:.1f}% exceeds {self.max_weekly_loss_pct}% limit")
        
        # Check win rate
        win_rate = portfolio.get('win_rate', 50)
        if win_rate < self.min_weekly_win_rate:
            triggered.append(f"Win rate {win_rate:.1f}% below {self.min_weekly_win_rate}% minimum")
        
        # Check drawdown
        drawdown = portfolio.get('max_drawdown_pct', 0)
        if drawdown >= self.max_monthly_drawdown_pct:
            triggered.append(f"Drawdown {drawdown:.1f}% exceeds {self.max_monthly_drawdown_pct}% limit")
        
        # Determine status
        if len(triggered) >= 3:
            return CircuitStatus.BLACK, triggered
        elif len(triggered) >= 2:
            return CircuitStatus.RED, triggered
        elif len(triggered) >= 1:
            return CircuitStatus.YELLOW, triggered
        else:
            return CircuitStatus.GREEN, []
    
    def get_position_size_modifier(self, status: CircuitStatus) -> float:
        """Get position size modifier based on circuit status"""
        modifiers = {
            CircuitStatus.GREEN: 1.0,    # Full size
            CircuitStatus.YELLOW: 0.5,   # Half size
            CircuitStatus.RED: 0.0,      # No new positions
            CircuitStatus.BLACK: 0.0     # Emergency halt
        }
        return modifiers.get(status, 0.0)


class BackupModeManager:
    """
    Manages switching between trading modes based on performance
    """
    
    MODES = {
        'active': {
            'description': 'Full predictive trading',
            'position_size': 1.0,
            'systems_active': 'all',
            'max_risk_per_trade': 0.10
        },
        'reduced': {
            'description': 'Top 3 systems only',
            'position_size': 0.5,
            'systems_active': 3,
            'max_risk_per_trade': 0.05
        },
        'minimal': {
            'description': 'Best 1 system only',
            'position_size': 0.25,
            'systems_active': 1,
            'max_risk_per_trade': 0.05
        },
        'passive': {
            'description': 'Buy and hold BTC/ETH only',
            'position_size': 0.0,
            'systems_active': 0,
            'max_risk_per_trade': 0.0
        },
        'halt': {
            'description': 'All trading stopped',
            'position_size': 0.0,
            'systems_active': 0,
            'max_risk_per_trade': 0.0
        }
    }
    
    def __init__(self, db_connection=None):
        self.db = db_connection
        self.current_mode = 'active'
        self.mode_history = []
    
    def evaluate_mode_switch(self, metrics: Dict) -> str:
        """
        Evaluate if we should switch modes based on performance
        
        Returns:
            recommended_mode
        """
        win_rate = metrics.get('win_rate', 50)
        sharpe = metrics.get('sharpe', 1.0)
        drawdown = metrics.get('max_drawdown', 0)
        total_return = metrics.get('total_return', 0)
        
        # Mode switching logic
        if win_rate < 30 or drawdown > 25 or total_return < -20:
            return 'halt'
        elif win_rate < 35 or sharpe < 0.5 or drawdown > 20:
            return 'passive'
        elif win_rate < 40 or sharpe < 0.8 or drawdown > 15:
            return 'minimal'
        elif win_rate < 45 or sharpe < 1.0 or drawdown > 10:
            return 'reduced'
        else:
            return 'active'
    
    def switch_mode(self, new_mode: str, reason: str):
        """Switch to new trading mode"""
        if new_mode not in self.MODES:
            raise ValueError(f"Unknown mode: {new_mode}")
        
        old_mode = self.current_mode
        self.current_mode = new_mode
        
        # Log the switch
        switch_record = {
            'timestamp': datetime.now().isoformat(),
            'from_mode': old_mode,
            'to_mode': new_mode,
            'reason': reason,
            'config': self.MODES[new_mode]
        }
        
        self.mode_history.append(switch_record)
        
        # Alert
        print(f"\n{'='*60}")
        print(f"MODE SWITCH: {old_mode.upper()} → {new_mode.upper()}")
        print(f"Reason: {reason}")
        print(f"Config: {self.MODES[new_mode]}")
        print(f"{'='*60}\n")
        
        return switch_record
    
    def get_current_config(self) -> Dict:
        """Get current mode configuration"""
        return self.MODES.get(self.current_mode, self.MODES['halt'])


class CapitalPreservation:
    """
    Capital preservation rules and emergency protocols
    """
    
    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        self.emergency_triggered = False
    
    def update_capital(self, new_value: float):
        """Update current capital and check preservation rules"""
        self.current_capital = new_value
        
        # Update peak
        if new_value > self.peak_capital:
            self.peak_capital = new_value
        
        # Check rules
        alerts = []
        
        # 50% capital preservation rule
        if self.current_capital < self.initial_capital * 0.50:
            alerts.append("CRITICAL: Capital below 50% of initial")
            self.emergency_triggered = True
        
        # 30% drawdown rule
        drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
        if drawdown > 0.30:
            alerts.append(f"CRITICAL: Drawdown {drawdown*100:.1f}% exceeds 30%")
            self.emergency_triggered = True
        
        # 20% warning
        if drawdown > 0.20:
            alerts.append(f"WARNING: Drawdown {drawdown*100:.1f}% exceeds 20%")
        
        return alerts
    
    def should_halt(self) -> bool:
        """Check if trading should be halted"""
        return self.emergency_triggered
    
    def get_allocation(self) -> Dict[str, float]:
        """
        Get capital allocation based on preservation status
        
        Returns:
            Dictionary of asset -> percentage
        """
        if self.emergency_triggered:
            # Emergency: 80% cash, 20% BTC
            return {
                'USDT': 0.80,
                'BTC': 0.15,
                'ETH': 0.05
            }
        else:
            # Normal: 50% trading, 30% core, 20% reserve
            return {
                'trading_capital': 0.50,
                'core_holdings': 0.30,
                'emergency_reserve': 0.20
            }


def check_all_systems_health(systems_performance: List[Dict]) -> Dict:
    """
    Check health of all 11 systems and recommend actions
    
    Returns:
        Health report with recommendations
    """
    report = {
        'timestamp': datetime.now().isoformat(),
        'systems_checked': len(systems_performance),
        'healthy_systems': 0,
        'warning_systems': 0,
        'failing_systems': 0,
        'recommendations': []
    }
    
    for system in systems_performance:
        win_rate = system.get('win_rate', 0)
        sharpe = system.get('sharpe', 0)
        
        if win_rate > 50 and sharpe > 1.0:
            report['healthy_systems'] += 1
        elif win_rate > 40 and sharpe > 0.5:
            report['warning_systems'] += 1
        else:
            report['failing_systems'] += 1
            report['recommendations'].append(f"DISABLE: {system['name']} (win rate {win_rate:.1f}%)")
    
    # Overall recommendation
    if report['failing_systems'] >= len(systems_performance) * 0.7:
        report['overall_action'] = "SWITCH_TO_BACKUP_MODE"
        report['urgency'] = "HIGH"
    elif report['failing_systems'] >= len(systems_performance) * 0.5:
        report['overall_action'] = "REDUCE_RISK"
        report['urgency'] = "MEDIUM"
    else:
        report['overall_action'] = "CONTINUE"
        report['urgency'] = "LOW"
    
    return report


if __name__ == '__main__':
    # Demo
    print("=" * 70)
    print("CIRCUIT BREAKER & BACKUP MODE SYSTEM")
    print("=" * 70)
    
    # Example portfolio metrics
    portfolio = {
        'daily_pnl_pct': -6.0,
        'consecutive_losses': 3,
        'weekly_pnl_pct': -12.0,
        'win_rate': 25,
        'max_drawdown_pct': 22
    }
    
    breaker = CircuitBreaker()
    status, triggered = breaker.check_circuits(portfolio)
    
    print(f"\nPortfolio Status: {status.value.upper()}")
    print(f"Position Size Modifier: {breaker.get_position_size_modifier(status)}")
    print("\nTriggered Rules:")
    for rule in triggered:
        print(f"  - {rule}")
    
    # Mode manager demo
    manager = BackupModeManager()
    
    metrics = {
        'win_rate': 35,
        'sharpe': 0.4,
        'max_drawdown': 18,
        'total_return': -5
    }
    
    recommended = manager.evaluate_mode_switch(metrics)
    print(f"\nRecommended Mode: {recommended}")
    print(f"Current Config: {manager.MODES[recommended]}")
