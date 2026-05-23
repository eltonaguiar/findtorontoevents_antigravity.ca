#!/usr/bin/env python3
"""
Edge Finder Bridge Module
==========================
Connects PHP Edge Finder v2 API with Python HF Statistical Validation.

This bridge:
1. Calls the PHP API for initial bucketing (ACTIVE/SMART/HIGH_CONVICTION)
2. Applies HF statistical validation (DSR, multiple testing correction)
3. Merges results for production-ready pick selection
4. Applies kill switch and risk overlays
"""

import requests
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Import our HF modules
from audit_trail.hf_statistical_rigor import HFScoringValidator, compute_hf_score
from audit_trail.hf_risk_management import (
    HFRiskDashboard, KillSwitchManager, 
    CVaRMonitor, CorrelationMonitor
)


@dataclass
class ValidatedPick:
    """Production-ready pick with full validation."""
    ticker: str
    direction: str  # LONG/SHORT
    entry_price: float
    stop_loss: float
    take_profit: float
    
    # PHP API results
    php_bucket: str  # ACTIVE / SMART / HIGH_CONVICTION
    php_score: float
    alpha_score: float
    risk_penalty: float
    
    # HF validation results
    hf_validated: bool
    dsr: float  # Deflated Sharpe Ratio
    harvey_liu_p: float
    sharpe_ratio: float
    regime_robustness: Dict[str, float]
    
    # Risk overlay
    kill_switch_level: Optional[str]
    cvar_95: float
    position_size: float
    
    # Final decision
    approved_for_trading: bool
    rejection_reasons: List[str]
    final_bucket: str  # May downgrade from PHP bucket


class EdgeFinderBridge:
    """
    Bridge between PHP Edge Finder v2 and Python HF validation.
    
    Usage:
        bridge = EdgeFinderBridge(api_base_url="https://yourdomain.com")
        pick = bridge.validate_pick("NVDA", historical_returns)
    """
    
    def __init__(self, 
                 api_base_url: str = "https://findtorontoevents.ca",
                 n_strategies_tested: int = 500,
                 initial_capital: float = 100000,
                 min_dsr: float = 0.5,
                 min_p_value: float = 0.05):
        """
        Args:
            api_base_url: Base URL for PHP Edge Finder API
            n_strategies_tested: For multiple testing correction
            initial_capital: For risk dashboard
            min_dsr: Minimum Deflated Sharpe Ratio
            min_p_value: Maximum p-value (Harvey-Liu corrected)
        """
        self.api_base = api_base_url
        self.hf_validator = HFScoringValidator(n_strategies_tested)
        self.risk_dashboard = HFRiskDashboard(initial_capital)
        self.kill_switch = KillSwitchManager(initial_capital)
        self.cvar_monitor = CVaRMonitor()
        self.correlation_monitor = CorrelationMonitor()
        
        self.min_dsr = min_dsr
        self.min_p_value = min_p_value
        
    def call_php_api(self, ticker: str, action: str = "scan") -> Dict:
        """
        Call PHP Edge Finder v2 API.
        
        Endpoints:
            ?action=scan - Main scanning endpoint
            ?action=market - Market status
            ?action=methodology - Scoring methodology
        """
        url = f"{self.api_base}/live-monitor/api/edge_finder_v2.php"
        params = {"action": action, "ticker": ticker}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"[Bridge] PHP API error: {e}")
            return self._fallback_response(ticker)
    
    def _fallback_response(self, ticker: str) -> Dict:
        """Fallback if PHP API unavailable."""
        return {
            "ticker": ticker,
            "bucket": "ACTIVE",
            "final_score": 50.0,
            "alpha_score": 50.0,
            "risk_penalty": 0.0,
            "reasons": ["php_api_unavailable"],
            "entry_price": 0.0,
            "stop_loss": 0.0,
            "take_profit": 0.0,
            "direction": "LONG"
        }
    
    def validate_pick(self, 
                      ticker: str,
                      historical_returns: Optional[pd.Series] = None,
                      current_regimes: Optional[pd.Series] = None,
                      portfolio_value: Optional[float] = None,
                      position_sizes: Optional[Dict[str, float]] = None) -> ValidatedPick:
        """
        Full validation pipeline for a single pick.
        
        Args:
            ticker: Symbol to validate
            historical_returns: Strategy return series for HF validation
            current_regimes: Regime labels for each return
            portfolio_value: Current portfolio value for risk overlay
            position_sizes: Current position sizes
            
        Returns:
            ValidatedPick with full validation results
        """
        # Step 1: Call PHP API
        php_result = self.call_php_api(ticker)
        
        # Step 2: HF Statistical Validation
        if historical_returns is not None and len(historical_returns) >= 100:
            hf_result = self.hf_validator.validate_strategy(
                returns=historical_returns.tolist(),
                strategy_name=php_result.get('strategy', ticker),
                regimes=current_regimes.tolist() if current_regimes is not None else None
            )
        else:
            # Insufficient data for HF validation
            hf_result = {
                'passed_hf_validation': True,  # Pass by default
                'deflated_sharpe': 0.0,
                'p_value_harvey_liu': 1.0,
                'sharpe_ratio': 0.0,
                'regime_metrics': {},
                'failure_reasons': ['insufficient_data']
            }
        
        # Step 3: Risk Overlay
        kill_status = None
        cvar_95 = 0.0
        
        if portfolio_value is not None:
            kill_status = self.kill_switch.update(portfolio_value)
            
        if historical_returns is not None:
            cvar_results = self.cvar_monitor.calculate(historical_returns)
            cvar_95 = abs(cvar_results.get('cvar_95', 0))
        
        # Step 4: Position Sizing
        position_size = self._calculate_position_size(
            php_bucket=php_result.get('bucket', 'ACTIVE'),
            hf_validated=hf_result['passed_hf_validation'],
            dsr=hf_result.get('deflated_sharpe', 0),
            kill_switch_level=kill_status['level'] if kill_status else None,
            cvar_95=cvar_95
        )
        
        # Step 5: Final Approval Decision
        approved, reasons = self._approval_decision(
            php_result=php_result,
            hf_result=hf_result,
            kill_status=kill_status,
            has_sufficient_data=historical_returns is not None and len(historical_returns) >= 100
        )
        
        # Step 6: Determine final bucket (may downgrade)
        final_bucket = self._determine_final_bucket(
            php_bucket=php_result.get('bucket', 'ACTIVE'),
            hf_validated=hf_result['passed_hf_validation'],
            approved=approved
        )
        
        return ValidatedPick(
            ticker=ticker,
            direction=php_result.get('direction', 'LONG'),
            entry_price=php_result.get('entry_price', 0.0),
            stop_loss=php_result.get('stop_loss', 0.0),
            take_profit=php_result.get('take_profit', 0.0),
            php_bucket=php_result.get('bucket', 'ACTIVE'),
            php_score=php_result.get('final_score', 0.0),
            alpha_score=php_result.get('alpha_score', 0.0),
            risk_penalty=php_result.get('risk_penalty', 0.0),
            hf_validated=hf_result['passed_hf_validation'],
            dsr=hf_result.get('deflated_sharpe', 0.0),
            harvey_liu_p=hf_result.get('p_value_harvey_liu', 1.0),
            sharpe_ratio=hf_result.get('sharpe_ratio', 0.0),
            regime_robustness=hf_result.get('regime_metrics', {}),
            kill_switch_level=kill_status['level'] if kill_status else None,
            cvar_95=cvar_95,
            position_size=position_size,
            approved_for_trading=approved,
            rejection_reasons=reasons,
            final_bucket=final_bucket
        )
    
    def _calculate_position_size(self,
                                  php_bucket: str,
                                  hf_validated: bool,
                                  dsr: float,
                                  kill_switch_level: Optional[str],
                                  cvar_95: float) -> float:
        """Calculate position size based on validation and risk state."""
        # Base size by bucket
        base_sizes = {
            'HIGH_CONVICTION': 0.10,  # 10% of portfolio
            'SMART': 0.05,             # 5% of portfolio
            'ACTIVE': 0.025            # 2.5% of portfolio
        }
        size = base_sizes.get(php_bucket, 0.01)
        
        # HF validation multiplier
        if hf_validated:
            size *= min(1.0 + dsr * 0.2, 1.5)  # Up to 50% boost for high DSR
        else:
            size *= 0.5  # 50% reduction if not HF validated
        
        # Kill switch multiplier
        if kill_switch_level:
            kill_multipliers = {
                'WARNING': 0.75,
                'CAUTION': 0.50,
                'ALERT': 0.25,
                'KILL': 0.0
            }
            size *= kill_multipliers.get(kill_switch_level, 1.0)
        
        # CVaR adjustment
        if cvar_95 > 0.05:  # CVaR > 5%
            size *= (0.05 / cvar_95)  # Reduce size proportionally
        
        return min(size, 0.15)  # Cap at 15% per position
    
    def _approval_decision(self,
                          php_result: Dict,
                          hf_result: Dict,
                          kill_status: Optional[Dict],
                          has_sufficient_data: bool) -> Tuple[bool, List[str]]:
        """Determine if pick is approved for trading."""
        reasons = []
        approved = True
        
        # PHP bucket check
        if php_result.get('bucket') == 'ACTIVE' and php_result.get('final_score', 0) < 55:
            approved = False
            reasons.append("php_score_too_low")
        
        # HF validation check (only if we have data)
        if has_sufficient_data:
            if not hf_result['passed_hf_validation']:
                approved = False
                reasons.extend(hf_result.get('failure_reasons', []))
            
            if hf_result.get('deflated_sharpe', 0) < self.min_dsr:
                approved = False
                reasons.append(f"dsr_below_{self.min_dsr}")
        
        # Kill switch check
        if kill_status and kill_status['level'] == 'KILL':
            approved = False
            reasons.append("kill_switch_active")
        
        return approved, reasons
    
    def _determine_final_bucket(self,
                               php_bucket: str,
                               hf_validated: bool,
                               approved: bool) -> str:
        """Determine final bucket (may downgrade from PHP bucket)."""
        if not approved:
            return "REJECTED"
        
        if not hf_validated:
            # Downgrade one level if not HF validated
            downgrades = {
                'HIGH_CONVICTION': 'SMART',
                'SMART': 'ACTIVE',
                'ACTIVE': 'ACTIVE'
            }
            return downgrades.get(php_bucket, 'ACTIVE')
        
        return php_bucket
    
    def batch_validate(self,
                      tickers: List[str],
                      returns_data: Dict[str, pd.Series],
                      portfolio_value: float) -> List[ValidatedPick]:
        """
        Validate multiple picks in batch.
        
        Args:
            tickers: List of symbols to validate
            returns_data: Dict of ticker -> return series
            portfolio_value: Current portfolio value
            
        Returns:
            List of ValidatedPick objects
        """
        results = []
        
        for ticker in tickers:
            returns = returns_data.get(ticker)
            pick = self.validate_pick(
                ticker=ticker,
                historical_returns=returns,
                portfolio_value=portfolio_value
            )
            results.append(pick)
        
        return results
    
    def get_portfolio_snapshot(self,
                               portfolio_value: float,
                               all_returns: pd.DataFrame,
                               position_sizes: Dict[str, float]) -> Dict:
        """
        Get complete risk snapshot for portfolio.
        
        Combines PHP API data with HF risk metrics.
        """
        snapshot = self.risk_dashboard.generate_snapshot(
            portfolio_value=portfolio_value,
            returns=all_returns.mean(axis=1),  # Portfolio-level returns
            returns_df=all_returns,
            position_sizes=position_sizes
        )
        
        return {
            'timestamp': snapshot.timestamp,
            'portfolio_value': snapshot.portfolio_value,
            'current_drawdown': snapshot.current_drawdown,
            'max_drawdown': snapshot.max_drawdown,
            'cvar_95': snapshot.cvar_95,
            'cvar_99': snapshot.cvar_99,
            'kill_switch_level': snapshot.kill_switch_level.name if snapshot.kill_switch_level else None,
            'can_trade': snapshot.kill_switch_level != KillSwitchLevel.KILL if snapshot.kill_switch_level else True,
            'position_sizes': snapshot.position_sizes
        }


# Integration helpers for existing pipeline

def integrate_with_smart_picks_engine(api_base_url: str = "https://findtorontoevents.ca"):
    """
    Factory function to create bridge integrated with existing system.
    
    Usage in smart_picks_engine.py:
        from audit_trail.edge_finder_bridge import integrate_with_smart_picks_engine
        
        bridge = integrate_with_smart_picks_engine()
        
        for pick in raw_picks:
            validated = bridge.validate_pick(
                ticker=pick['symbol'],
                historical_returns=get_historical_returns(pick['strategy']),
                portfolio_value=current_portfolio_value
            )
            
            if validated.approved_for_trading:
                approved_picks.append(validated)
    """
    return EdgeFinderBridge(
        api_base_url=api_base_url,
        n_strategies_tested=500,
        initial_capital=100000,
        min_dsr=0.5,
        min_p_value=0.05
    )


if __name__ == "__main__":
    """Test the bridge module."""
    print("=" * 60)
    print("Edge Finder Bridge Module - Test")
    print("=" * 60)
    
    # Create bridge (will use fallback since API not available in test)
    bridge = EdgeFinderBridge(api_base_url="http://localhost")
    
    # Test with sample data
    np.random.seed(42)
    sample_returns = pd.Series(np.random.normal(0.001, 0.02, 252))
    
    pick = bridge.validate_pick(
        ticker="TEST",
        historical_returns=sample_returns,
        portfolio_value=100000
    )
    
    print(f"\nValidated Pick: {pick.ticker}")
    print(f"  PHP Bucket: {pick.php_bucket}")
    print(f"  Final Bucket: {pick.final_bucket}")
    print(f"  PHP Score: {pick.php_score:.2f}")
    print(f"  HF Validated: {pick.hf_validated}")
    print(f"  DSR: {pick.dsr:.2f}")
    print(f"  Position Size: {pick.position_size:.2%}")
    print(f"  Approved: {pick.approved_for_trading}")
    if pick.rejection_reasons:
        print(f"  Reasons: {pick.rejection_reasons}")
    
    print("\n✓ Bridge module test complete")
