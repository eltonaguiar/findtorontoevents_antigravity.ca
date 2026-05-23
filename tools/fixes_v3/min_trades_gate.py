"""
Minimum Trades Gate
====================
Current problem: 2 of 3 current live smart picks come from strategies with
ZERO forward trades (tsmom_volscaled and cg_whale_divergence). These have
no track record whatsoever — putting them live is pure gambling.

The audit dashboard's Smart Score formula gives up to 40 points for
"Forward WR + Track Record" but doesn't HARD GATE on minimum trades.
A strategy with 0 trades can still score 84/100 via other components.

This module adds a hard gate: no live picks from strategies with
fewer than N forward trades. No exceptions.

From the audit data:
- "Strategy Momentum" shows: after WIN = 65.6% WR, after LOSS = 24.1% WR
  This proves track record IS predictive — but only if there IS a track record.

Usage:
    from tools.fixes_v3.min_trades_gate import MinTradesGate
    
    gate = MinTradesGate(min_trades=10)
    gate.load_performance("alpha_engine/data/strategy_performance.json")
    
    if not gate.has_track_record("tsmom_volscaled"):
        block_pick()

Author: Enhancement PR based on audit feedback
Date: 2026-04-11
"""
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MinTradesGate:
    """
    Hard gate: strategies must have minimum forward trades before going live.
    
    Thresholds by confidence tier:
    - Default: 10 forward trades minimum
    - "WATCH" trust tier: 20 trades minimum
    - New/unvalidated strategies: 30 trades minimum
    - Proven strategies (WR > 50%, PF > 1.5): 5 trades minimum (fast-track)
    """
    
    DEFAULT_MIN = 10
    WATCH_MIN = 20
    NEW_MIN = 30
    PROVEN_MIN = 5
    
    def __init__(
        self,
        min_trades: int = 10,
        performance_data: Optional[Dict] = None,
    ):
        self.min_trades = min_trades
        self._performance = performance_data or {}
    
    def load_performance(self, path: str = "alpha_engine/data/strategy_performance.json"):
        """Load strategy performance data."""
        try:
            with open(path) as f:
                self._performance = json.load(f)
        except FileNotFoundError:
            logger.warning(f"Performance file not found: {path}")
    
    def set_performance(self, data: Dict):
        """Set performance data directly (for testing)."""
        self._performance = data
    
    def has_track_record(self, strategy_name: str) -> bool:
        """Quick check: does this strategy have enough forward trades?"""
        return self.evaluate(strategy_name)["passed"]
    
    def evaluate(self, strategy_name: str) -> Dict[str, Any]:
        """
        Full evaluation of a strategy's track record.
        
        Returns:
            Dict with: passed, trades, min_required, reason, tier
        """
        perf = self._performance.get(strategy_name, {})
        trades = perf.get("closed_picks", 0)
        wr = perf.get("win_rate", 0)
        pf = perf.get("profit_factor", 0)
        
        # Determine minimum based on quality
        if trades >= 20 and wr > 0.50 and pf > 1.5:
            min_required = self.PROVEN_MIN
            tier = "PROVEN"
        elif trades >= 10 and wr > 0.40:
            min_required = self.DEFAULT_MIN
            tier = "ESTABLISHED"
        elif trades > 0:
            min_required = self.WATCH_MIN
            tier = "WATCH"
        else:
            min_required = self.NEW_MIN
            tier = "NEW"
        
        passed = trades >= min_required
        
        if not passed:
            reason = (
                f"Strategy '{strategy_name}' has {trades}/{min_required} forward trades "
                f"(tier: {tier}). Cannot go live without track record. "
                f"Paper-trade until {min_required} trades complete."
            )
        else:
            reason = f"OK: {trades} trades (tier: {tier}, min: {min_required})"
        
        return {
            "passed": passed,
            "strategy": strategy_name,
            "trades": trades,
            "min_required": min_required,
            "tier": tier,
            "reason": reason,
            "win_rate": wr,
            "profit_factor": pf,
        }
    
    def filter_picks(self, picks: List[Dict]) -> List[Dict]:
        """Filter picks, removing those from strategies without track record."""
        allowed = []
        blocked_count = 0
        
        for pick in picks:
            strategy = pick.get("strategy", "unknown")
            result = self.evaluate(strategy)
            
            if result["passed"]:
                pick["_track_record"] = result
                allowed.append(pick)
            else:
                blocked_count += 1
                logger.warning(
                    f"BLOCKED {pick.get('symbol', '?')} from {strategy}: "
                    f"{result['reason']}"
                )
        
        if blocked_count:
            logger.info(
                f"MinTradesGate: {blocked_count}/{len(picks)} picks blocked "
                f"(no track record)"
            )
        
        return allowed
    
    def audit_current_picks(self, smart_picks: List[Dict]) -> Dict:
        """
        Audit current smart picks and flag those without track record.
        Returns a report dict.
        """
        results = []
        for pick in smart_picks:
            strategy = pick.get("strategy", "unknown")
            evaluation = self.evaluate(strategy)
            results.append({
                "symbol": pick.get("symbol", "?"),
                "direction": pick.get("direction", "?"),
                "score": pick.get("smart_score", 0),
                "strategy": strategy,
                **evaluation,
            })
        
        blocked = [r for r in results if not r["passed"]]
        
        return {
            "total_picks": len(results),
            "passed": len(results) - len(blocked),
            "blocked": len(blocked),
            "blocked_details": blocked,
            "all_results": results,
        }
