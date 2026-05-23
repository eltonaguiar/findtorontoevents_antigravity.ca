"""
Portfolio Circuit Breaker - Global Drawdown Protection
======================================================
Automatically halts trading when portfolio-level risk thresholds are breached.

Based on feedback: "Portfolio-level circuit breaker: if equity drops > X% from peak"

Features:
- Global drawdown circuit breaker
- Per-sleeve drawdown limits
- Auto-flatten and cooldown
- Gradual re-entry

Usage:
    from portfolio_circuit_breaker import PortfolioCircuitBreaker
    
    breaker = PortfolioCircuitBreaker()
    
    # Update portfolio value
    breaker.update_equity(105000)
    
    # Check if trading allowed
    if breaker.can_trade():
        execute_signals()
    else:
        logger.warning(f"Circuit breaker active: {breaker.get_status()}")
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('CircuitBreaker')


class BreakerState(Enum):
    """Circuit breaker states"""
    NORMAL = "normal"
    WARNING = "warning"
    TRIGGERED = "triggered"
    COOLDOWN = "cooldown"


@dataclass
class BreakerConfig:
    """Circuit breaker configuration"""
    # Global limits
    global_max_dd_percent: float = 8.0  # 8% max DD
    global_warning_dd_percent: float = 5.0  # Warning at 5%
    
    # Per-sleeve limits
    sleeve_max_dd_percent: float = 6.0
    
    # Cooldown settings
    cooldown_minutes: int = 30
    gradual_reentry: bool = True
    reentry_percentages: List[float] = field(default_factory=lambda: [0.25, 0.5, 0.75, 1.0])
    
    # Auto-flatten
    auto_flatten_on_trigger: bool = True


@dataclass
class SleeveState:
    """State for a trading sleeve"""
    sleeve_id: str
    peak_equity: float
    current_equity: float
    max_dd_percent: float = 0.0
    state: BreakerState = BreakerState.NORMAL


class PortfolioCircuitBreaker:
    """
    Portfolio-level circuit breaker system
    
    Protects against catastrophic drawdowns by automatically
    halting trading when risk thresholds are breached.
    """
    
    def __init__(self, config: Optional[BreakerConfig] = None):
        self.config = config or BreakerConfig()
        
        # Portfolio state
        self.peak_equity: float = 0.0
        self.current_equity: float = 0.0
        self.global_state: BreakerState = BreakerState.NORMAL
        
        # Sleeve states
        self.sleeves: Dict[str, SleeveState] = {}
        
        # Breaker history
        self.trigger_history: List[Dict] = []
        self.last_trigger_time: Optional[datetime] = None
        self.cooldown_end: Optional[datetime] = None
        self.current_size_multiplier: float = 1.0
        
        # Load state
        self._load_state()
    
    def _load_state(self):
        """Load circuit breaker state"""
        try:
            with open('circuit_breaker_state.json', 'r') as f:
                data = json.load(f)
                self.peak_equity = data.get('peak_equity', 0)
                self.current_equity = data.get('current_equity', 0)
                self.trigger_history = data.get('history', [])
        except FileNotFoundError:
            pass
    
    def _save_state(self):
        """Save circuit breaker state"""
        data = {
            'peak_equity': self.peak_equity,
            'current_equity': self.current_equity,
            'global_state': self.global_state.value,
            'last_trigger': self.last_trigger_time.isoformat() if self.last_trigger_time else None,
            'cooldown_end': self.cooldown_end.isoformat() if self.cooldown_end else None,
            'size_multiplier': self.current_size_multiplier,
            'history': self.trigger_history[-100:]  # Keep last 100
        }
        with open('circuit_breaker_state.json', 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def update_equity(self, equity: float, timestamp: Optional[datetime] = None):
        """
        Update portfolio equity
        
        Args:
            equity: Current portfolio equity
            timestamp: Update timestamp
        """
        ts = timestamp or datetime.now()
        
        # Update peak
        if equity > self.peak_equity:
            self.peak_equity = equity
            # Reset state if we've recovered
            if self.global_state == BreakerState.WARNING:
                self.global_state = BreakerState.NORMAL
                logger.info("[CircuitBreaker] Recovered from warning state")
        
        self.current_equity = equity
        
        # Calculate drawdown
        if self.peak_equity > 0:
            dd_percent = (self.peak_equity - equity) / self.peak_equity * 100
        else:
            dd_percent = 0
        
        # Check thresholds
        self._check_thresholds(dd_percent, ts)
        
        self._save_state()
    
    def _check_thresholds(self, dd_percent: float, timestamp: datetime):
        """Check if any thresholds breached"""
        
        # Check cooldown expiration
        if self.global_state == BreakerState.COOLDOWN:
            if self.cooldown_end and timestamp > self.cooldown_end:
                self._exit_cooldown()
            return
        
        # Check global max DD
        if dd_percent >= self.config.global_max_dd_percent:
            self._trigger_breaker('global_max_dd', dd_percent, timestamp)
            return
        
        # Check warning level
        if dd_percent >= self.config.global_warning_dd_percent:
            if self.global_state != BreakerState.WARNING:
                self.global_state = BreakerState.WARNING
                logger.warning(f"[CircuitBreaker] WARNING: Drawdown {dd_percent:.2f}%")
    
    def _trigger_breaker(self, reason: str, dd_percent: float, timestamp: datetime):
        """Trigger the circuit breaker"""
        self.global_state = BreakerState.TRIGGERED
        self.last_trigger_time = timestamp
        self.cooldown_end = timestamp + timedelta(minutes=self.config.cooldown_minutes)
        self.current_size_multiplier = 0.0
        
        # Log trigger
        trigger_event = {
            'timestamp': timestamp.isoformat(),
            'reason': reason,
            'drawdown_percent': dd_percent,
            'peak_equity': self.peak_equity,
            'current_equity': self.current_equity,
            'cooldown_until': self.cooldown_end.isoformat()
        }
        self.trigger_history.append(trigger_event)
        
        logger.critical(
            f"[CircuitBreaker] TRIGGERED! Reason: {reason}, "
            f"DD: {dd_percent:.2f}%, Cooldown until: {self.cooldown_end}"
        )
        
        # Auto-flatten if enabled
        if self.config.auto_flatten_on_trigger:
            self._flatten_all_positions()
    
    def _flatten_all_positions(self):
        """Flatten all open positions"""
        logger.critical("[CircuitBreaker] AUTO-FLATTENING ALL POSITIONS")
        # In production, this would call your position manager
        # For now, just log
    
    def _exit_cooldown(self):
        """Exit cooldown and enter gradual reentry"""
        self.global_state = BreakerState.NORMAL
        
        if self.config.gradual_reentry:
            # Start with reduced size
            self.current_size_multiplier = self.config.reentry_percentages[0]
            logger.info(f"[CircuitBreaker] Cooldown ended. Reentry at {self.current_size_multiplier:.0%} size")
        else:
            self.current_size_multiplier = 1.0
            logger.info("[CircuitBreaker] Cooldown ended. Full size restored")
    
    def can_trade(self) -> Tuple[bool, str]:
        """
        Check if trading is currently allowed
        
        Returns: (allowed, reason)
        """
        if self.global_state == BreakerState.TRIGGERED:
            return False, "Circuit breaker triggered - auto-flattening"
        
        if self.global_state == BreakerState.COOLDOWN:
            remaining = (self.cooldown_end - datetime.now()).total_seconds() / 60
            if remaining > 0:
                return False, f"In cooldown: {remaining:.1f} minutes remaining"
        
        if self.global_state == BreakerState.WARNING:
            return True, "WARNING: Approaching drawdown limit"
        
        return True, "OK"
    
    def get_position_size_multiplier(self) -> float:
        """
        Get current position size multiplier
        
        Returns 0.0-1.0 based on breaker state
        """
        return self.current_size_multiplier
    
    def update_sleeve_equity(self, sleeve_id: str, equity: float):
        """Update equity for a specific sleeve"""
        if sleeve_id not in self.sleeves:
            self.sleeves[sleeve_id] = SleeveState(
                sleeve_id=sleeve_id,
                peak_equity=equity,
                current_equity=equity
            )
        
        sleeve = self.sleeves[sleeve_id]
        
        # Update peak
        if equity > sleeve.peak_equity:
            sleeve.peak_equity = equity
            sleeve.state = BreakerState.NORMAL
        
        sleeve.current_equity = equity
        
        # Check sleeve drawdown
        if sleeve.peak_equity > 0:
            dd = (sleeve.peak_equity - equity) / sleeve.peak_equity * 100
            sleeve.max_dd_percent = dd
            
            if dd >= self.config.sleeve_max_dd_percent:
                sleeve.state = BreakerState.TRIGGERED
                logger.warning(f"[CircuitBreaker] Sleeve {sleeve_id} max DD breached: {dd:.2f}%")
    
    def is_sleeve_allowed(self, sleeve_id: str) -> bool:
        """Check if a specific sleeve can trade"""
        if sleeve_id not in self.sleeves:
            return True
        return self.sleeves[sleeve_id].state != BreakerState.TRIGGERED
    
    def get_status(self) -> Dict[str, Any]:
        """Get full circuit breaker status"""
        dd_percent = 0
        if self.peak_equity > 0:
            dd_percent = (self.peak_equity - self.current_equity) / self.peak_equity * 100
        
        return {
            'timestamp': datetime.now().isoformat(),
            'state': self.global_state.value,
            'peak_equity': self.peak_equity,
            'current_equity': self.current_equity,
            'drawdown_percent': round(dd_percent, 2),
            'size_multiplier': self.current_size_multiplier,
            'can_trade': self.can_trade()[0],
            'cooldown_remaining_minutes': (
                (self.cooldown_end - datetime.now()).total_seconds() / 60
                if self.cooldown_end and self.global_state == BreakerState.COOLDOWN
                else 0
            ),
            'trigger_count_30d': len([
                t for t in self.trigger_history
                if datetime.fromisoformat(t['timestamp']) > datetime.now() - timedelta(days=30)
            ]),
            'sleeve_status': {
                sleeve_id: {
                    'state': s.state.value,
                    'max_dd': round(s.max_dd_percent, 2)
                }
                for sleeve_id, s in self.sleeves.items()
            }
        }
    
    def manual_reset(self, confirm: bool = False):
        """Manually reset circuit breaker (use with caution!)"""
        if not confirm:
            logger.error("[CircuitBreaker] Manual reset requires confirm=True")
            return
        
        self.global_state = BreakerState.NORMAL
        self.cooldown_end = None
        self.current_size_multiplier = 1.0
        self.peak_equity = self.current_equity  # Reset peak to current
        
        logger.critical("[CircuitBreaker] MANUAL RESET PERFORMED")
        self._save_state()


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("PORTFOLIO CIRCUIT BREAKER - Demo")
    print("=" * 80)
    
    breaker = PortfolioCircuitBreaker()
    
    # Simulate equity curve
    initial_equity = 100000
    breaker.update_equity(initial_equity)
    
    print(f"\nInitial Equity: ${initial_equity:,.2f}")
    print(f"State: {breaker.get_status()['state']}")
    print(f"Can Trade: {breaker.can_trade()[0]}")
    
    # Simulate growth
    for i in range(5):
        equity = initial_equity * (1 + (i + 1) * 0.02)
        breaker.update_equity(equity)
        print(f"Day {i+1}: ${equity:,.2f} | Peak: ${breaker.peak_equity:,.2f}")
    
    # Simulate drawdown
    print("\n[DRAWDOWN SIMULATION]")
    drawdowns = [0.02, 0.04, 0.06, 0.075, 0.085, 0.09, 0.05, 0.03]
    peak = breaker.peak_equity
    
    for i, dd in enumerate(drawdowns):
        equity = peak * (1 - dd)
        breaker.update_equity(equity)
        status = breaker.get_status()
        can_trade, reason = breaker.can_trade()
        
        print(f"Day {i+6}: ${equity:,.2f} | DD: {status['drawdown_percent']:.1f}% | "
              f"State: {status['state']} | Can Trade: {can_trade}")
        
        if status['state'] == 'triggered':
            print("  >>> CIRCUIT BREAKER TRIGGERED!")
        elif status['state'] == 'cooldown':
            print(f"  >>> COOLDOWN: {status['cooldown_remaining_minutes']:.1f} min remaining")
    
    print("\n" + "=" * 80)
    print("Final Status:")
    print(json.dumps(breaker.get_status(), indent=2))
    print("=" * 80)
