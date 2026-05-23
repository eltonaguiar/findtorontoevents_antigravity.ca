"""
Signal Validator - Pre-Trade Validation System

Validates trading signals before they are executed to ensure
they meet all criteria for safe trading.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ValidationStatus(Enum):
    """Validation status codes"""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PENDING = "PENDING"
    WARNING = "WARNING"


@dataclass
class ValidationResult:
    """Complete validation result"""
    approved: bool
    status: str
    checks: Dict[str, bool]
    warnings: List[str]
    failures: List[str]
    timestamp: str
    cooldown_remaining: Optional[int] = None
    daily_limit_remaining: Optional[int] = None


class SignalValidator:
    """
    Validates trading signals before execution.
    
    Performs comprehensive checks:
    - Sufficient backtest data coverage
    - Signal uniqueness (no recent duplicates)
    - Market hours availability
    - Liquidity sufficiency
    - Portfolio correlation limits
    - Daily loss limits
    """
    
    # Validation thresholds
    MIN_BACKTEST_DAYS = 180  # Minimum 6 months backtest
    MIN_BACKTEST_TRADES = 30  # Minimum trades for significance
    SIGNAL_COOLDOWN_MINUTES = 240  # 4 hours between similar signals
    MAX_DAILY_LOSS_PCT = 5.0  # Max 5% daily loss
    MAX_POSITION_CORRELATION = 0.7  # Max correlation with existing positions
    MIN_LIQUIDITY_USD = 10_000_000  # Minimum $10M daily volume
    MAX_SPREAD_PCT = 0.01  # Maximum 1% spread
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the signal validator.
        
        Args:
            config: Optional configuration overrides
        """
        self.config = config or {}
        self.min_backtest_days = self.config.get('min_backtest_days', self.MIN_BACKTEST_DAYS)
        self.min_backtest_trades = self.config.get('min_backtest_trades', self.MIN_BACKTEST_TRADES)
        self.signal_cooldown = self.config.get('signal_cooldown_minutes', self.SIGNAL_COOLDOWN_MINUTES)
        self.max_daily_loss = self.config.get('max_daily_loss_pct', self.MAX_DAILY_LOSS_PCT)
        self.max_correlation = self.config.get('max_correlation', self.MAX_POSITION_CORRELATION)
        self.min_liquidity = self.config.get('min_liquidity_usd', self.MIN_LIQUIDITY_USD)
        self.max_spread = self.config.get('max_spread_pct', self.MAX_SPREAD_PCT)
        
        # Signal history for uniqueness checks
        self.recent_signals: Dict[str, float] = {}
        
        # Daily tracking
        self.daily_stats = {
            'date': datetime.utcnow().date(),
            'signals_generated': 0,
            'signals_approved': 0,
            'daily_pnl': 0.0,
            'daily_loss': 0.0
        }
    
    def validate(self, signal: Dict, portfolio_state: Optional[Dict] = None) -> ValidationResult:
        """
        Validate a trading signal.
        
        Args:
            signal: Trading signal to validate
            portfolio_state: Current portfolio state for correlation checks
            
        Returns:
            ValidationResult with approval status and details
        """
        checks = {}
        warnings = []
        failures = []
        
        # 1. Check backtest coverage
        backtest_ok = self._check_backtest_coverage(signal)
        checks['sufficient_backtest_data'] = backtest_ok
        if not backtest_ok:
            failures.append('sufficient_backtest_data')
        
        # 2. Check signal uniqueness
        unique_ok, cooldown_remaining = self._check_signal_uniqueness(signal)
        checks['no_recent_similar_signal'] = unique_ok
        if not unique_ok:
            failures.append('no_recent_similar_signal')
        
        # 3. Check market hours
        market_ok = self._check_market_hours(signal)
        checks['market_hours_ok'] = market_ok
        if not market_ok:
            warnings.append('market_hours_ok')  # Warning, not failure
        
        # 4. Check liquidity
        liquidity_ok = self._check_liquidity(signal)
        checks['liquidity_sufficient'] = liquidity_ok
        if not liquidity_ok:
            failures.append('liquidity_sufficient')
        
        # 5. Check portfolio correlation
        correlation_ok = self._check_portfolio_correlation(signal, portfolio_state)
        checks['correlation_within_limits'] = correlation_ok
        if not correlation_ok:
            warnings.append('correlation_within_limits')
        
        # 6. Check daily limits
        limits_ok, limit_remaining = self._check_daily_limits(signal)
        checks['daily_loss_limit_ok'] = limits_ok
        if not limits_ok:
            failures.append('daily_loss_limit_ok')
        
        # 7. Additional checks
        checks['spread_acceptable'] = self._check_spread(signal)
        if not checks['spread_acceptable']:
            warnings.append('spread_acceptable')
        
        checks['volatility_normal'] = self._check_volatility(signal)
        if not checks['volatility_normal']:
            warnings.append('volatility_normal')
        
        checks['not_blacklisted'] = self._check_blacklist(signal)
        if not checks['not_blacklisted']:
            failures.append('not_blacklisted')
        
        # Determine final status
        critical_failures = [f for f in failures if f not in ['market_hours_ok']]
        approved = len(critical_failures) == 0 and backtest_ok and liquidity_ok and limits_ok
        
        status = ValidationStatus.APPROVED if approved else ValidationStatus.REJECTED
        if warnings and approved:
            status = ValidationStatus.WARNING
        
        # Update signal history
        if approved:
            self._record_signal(signal)
        
        return ValidationResult(
            approved=approved,
            status=status.value,
            checks=checks,
            warnings=warnings,
            failures=failures,
            timestamp=datetime.utcnow().isoformat() + 'Z',
            cooldown_remaining=cooldown_remaining if not unique_ok else None,
            daily_limit_remaining=limit_remaining if not limits_ok else None
        )
    
    def _check_backtest_coverage(self, signal: Dict) -> bool:
        """Check if signal has sufficient backtest data."""
        backtest = signal.get('backtest_metrics', {})
        
        # Check number of trades
        trades = backtest.get('total_trades', 0)
        if trades < self.min_backtest_trades:
            return False
        
        # Check backtest duration if available
        duration_days = backtest.get('backtest_days', 365)
        if duration_days < self.min_backtest_days:
            return False
        
        # Check for minimum win rate
        win_rate = backtest.get('win_rate', 0)
        if win_rate < 0.45:  # Below 45% win rate is concerning
            return False
        
        return True
    
    def _check_signal_uniqueness(self, signal: Dict) -> Tuple[bool, Optional[int]]:
        """Check if similar signal was recently generated."""
        symbol = signal.get('symbol', '')
        direction = signal.get('direction', '')
        strategy = signal.get('strategy_dna', '')
        
        # Create signal key
        signal_key = f"{symbol}_{direction}_{strategy}"
        
        # Check if in recent signals
        if signal_key in self.recent_signals:
            last_time = self.recent_signals[signal_key]
            elapsed = time.time() - last_time
            cooldown_seconds = self.signal_cooldown * 60
            
            if elapsed < cooldown_seconds:
                remaining = int((cooldown_seconds - elapsed) / 60)
                return False, remaining
        
        return True, None
    
    def _check_market_hours(self, signal: Dict) -> bool:
        """Check if market is open and trading."""
        # Crypto markets are 24/7, but check for maintenance windows
        market_data = signal.get('market_structure', {})
        
        # Check if exchange is in maintenance
        if market_data.get('exchange_maintenance', False):
            return False
        
        # Check if trading is enabled
        if not market_data.get('trading_enabled', True):
            return False
        
        return True
    
    def _check_liquidity(self, signal: Dict) -> bool:
        """Check if market has sufficient liquidity."""
        market_data = signal.get('market_structure', {})
        
        daily_volume = market_data.get('daily_volume_usd', 0)
        if daily_volume < self.min_liquidity:
            return False
        
        # Check order book depth
        bid_depth = market_data.get('bid_depth_usd', 0)
        ask_depth = market_data.get('ask_depth_usd', 0)
        
        min_depth = self.min_liquidity * 0.1  # 10% of daily volume
        if bid_depth < min_depth or ask_depth < min_depth:
            return False
        
        return True
    
    def _check_spread(self, signal: Dict) -> bool:
        """Check if spread is acceptable."""
        market_data = signal.get('market_structure', {})
        spread_pct = market_data.get('spread_pct', 0.01)
        
        return spread_pct <= self.max_spread
    
    def _check_portfolio_correlation(self, signal: Dict, portfolio_state: Optional[Dict]) -> bool:
        """Check correlation with existing portfolio positions."""
        if not portfolio_state:
            return True
        
        positions = portfolio_state.get('positions', [])
        if not positions:
            return True
        
        symbol = signal.get('symbol', '')
        
        # Get correlations
        correlations = portfolio_state.get('correlations', {})
        
        for position in positions:
            pos_symbol = position.get('symbol', '')
            pair_key = f"{symbol}_{pos_symbol}"
            
            correlation = correlations.get(pair_key, 0)
            if abs(correlation) > self.max_correlation:
                return False
        
        return True
    
    def _check_daily_limits(self, signal: Dict) -> Tuple[bool, Optional[float]]:
        """Check if daily loss limit would be exceeded."""
        self._reset_daily_stats_if_needed()
        
        # Check daily loss
        if self.daily_stats['daily_loss'] >= self.max_daily_loss:
            return False, 0.0
        
        remaining = self.max_daily_loss - self.daily_stats['daily_loss']
        return True, remaining
    
    def _check_volatility(self, signal: Dict) -> bool:
        """Check if volatility is within normal range."""
        market_data = signal.get('market_structure', {})
        volatility = market_data.get('volatility_24h', 0.05)
        
        # Flag if volatility is extremely high (>15% daily)
        if volatility > 0.15:
            return False
        
        return True
    
    def _check_blacklist(self, signal: Dict) -> bool:
        """Check if symbol is blacklisted."""
        # Blacklist of problematic tokens
        blacklist = {
            'SUS', 'HOT', 'BTT', 'WIN', 'DENT',  # Low quality/high risk
            'SHIB', 'DOGE',  # Meme coins (optional - adjust as needed)
        }
        
        symbol = signal.get('symbol', '')
        base = symbol.replace('USDT', '').replace('USD', '').replace('PERP', '')
        
        return base not in blacklist
    
    def _record_signal(self, signal: Dict):
        """Record signal in history for uniqueness checks."""
        symbol = signal.get('symbol', '')
        direction = signal.get('direction', '')
        strategy = signal.get('strategy_dna', '')
        
        signal_key = f"{symbol}_{direction}_{strategy}"
        self.recent_signals[signal_key] = time.time()
        
        # Cleanup old signals
        self._cleanup_old_signals()
    
    def _cleanup_old_signals(self):
        """Remove signals older than cooldown period."""
        cutoff = time.time() - (self.signal_cooldown * 60 * 2)  # 2x cooldown
        self.recent_signals = {
            k: v for k, v in self.recent_signals.items()
            if v > cutoff
        }
    
    def _reset_daily_stats_if_needed(self):
        """Reset daily stats if it's a new day."""
        today = datetime.utcnow().date()
        if today != self.daily_stats['date']:
            self.daily_stats = {
                'date': today,
                'signals_generated': 0,
                'signals_approved': 0,
                'daily_pnl': 0.0,
                'daily_loss': 0.0
            }
    
    def update_daily_pnl(self, pnl: float):
        """Update daily P&L tracking."""
        self._reset_daily_stats_if_needed()
        
        self.daily_stats['daily_pnl'] += pnl
        if pnl < 0:
            self.daily_stats['daily_loss'] += abs(pnl)
    
    def get_validation_summary(self) -> Dict:
        """Get summary of validation statistics."""
        self._reset_daily_stats_if_needed()
        
        return {
            'daily_stats': self.daily_stats,
            'recent_signals_count': len(self.recent_signals),
            'config': {
                'min_backtest_days': self.min_backtest_days,
                'min_backtest_trades': self.min_backtest_trades,
                'signal_cooldown_minutes': self.signal_cooldown,
                'max_daily_loss_pct': self.max_daily_loss,
                'max_correlation': self.max_correlation
            }
        }


# Example usage
if __name__ == '__main__':
    validator = SignalValidator()
    
    # Test valid signal
    test_signal = {
        'symbol': 'BTCUSDT',
        'direction': 'LONG',
        'strategy_dna': 'combo_ema_rsi',
        'backtest_metrics': {
            'total_trades': 156,
            'backtest_days': 365,
            'win_rate': 0.68
        },
        'market_structure': {
            'daily_volume_usd': 35_000_000_000,
            'spread_pct': 0.0005,
            'volatility_24h': 0.045,
            'trading_enabled': True
        }
    }
    
    result = validator.validate(test_signal)
    
    print("=" * 60)
    print("SIGNAL VALIDATION RESULT")
    print("=" * 60)
    print(f"Approved: {result.approved}")
    print(f"Status: {result.status}")
    print(f"\nChecks:")
    for check, passed in result.checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
    
    if result.warnings:
        print(f"\nWarnings: {result.warnings}")
    if result.failures:
        print(f"Failures: {result.failures}")
    print("=" * 60)
    
    # Test invalid signal (low liquidity)
    bad_signal = {
        'symbol': 'LOWVOL',
        'direction': 'LONG',
        'strategy_dna': 'test',
        'backtest_metrics': {
            'total_trades': 156,
            'win_rate': 0.68
        },
        'market_structure': {
            'daily_volume_usd': 1_000_000,  # Too low
            'spread_pct': 0.05,  # Too wide
            'trading_enabled': True
        }
    }
    
    result2 = validator.validate(bad_signal)
    print("\n" + "=" * 60)
    print("INVALID SIGNAL VALIDATION")
    print("=" * 60)
    print(f"Approved: {result2.approved}")
    print(f"Status: {result2.status}")
    print(f"Failures: {result2.failures}")
    print("=" * 60)
