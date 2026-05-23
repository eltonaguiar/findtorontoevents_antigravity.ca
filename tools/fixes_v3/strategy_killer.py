"""
Strategy Killer — Auto-Disable Failed Strategies
==================================================
Based on live strategy_performance.json data:

KILL (proven negative edge):
  - quan_engine_scalp: 3,119 picks, 28.2% WR, Sharpe -6.25, PF 0.38, -$554K
  - quan_engine_position: 18 picks, 0% WR, Sharpe -203.6
  - volume_spike_breakout: 36 picks, 11.1% WR, Sharpe -17.27, PF 0.14
  - stochrsi_macd_combo: 10 picks, 0% WR, all SL hits
  - rsi_bounce: 10 picks, 40% WR but PF=1.0 (breakeven, no edge)

KEEP (positive or promising):
  - macd_crossover: 16 picks, 68.8% WR, Sharpe 11.34, PF 4.09 ✅
  - quan_engine_swing: 90 picks, 33.3% WR, Sharpe 1.59, PF 1.25 ✅
  - rsi_overbought: 5 picks, 60% WR (too few but promising)

REQUIRE MIN TRADES (no track record):
  - Any strategy with 0 forward trades should NOT generate live picks

Usage:
    from tools.fixes_v3.strategy_killer import StrategyKiller
    killer = StrategyKiller()
    if killer.is_allowed("volume_spike_breakout"):
        # Won't reach here — it's killed
        pass

Author: Enhancement PR based on audit feedback
Date: 2026-04-11
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# Strategies with proven negative edge — KILL immediately
KILLED_STRATEGIES = {
    "quan_engine_scalp": {
        "reason": "3,119 picks, 28.2% WR, Sharpe -6.25, PF 0.38. Lost $554K equivalent.",
        "killed_date": "2026-04-11",
        "picks": 3119,
        "wr": 0.282,
        "sharpe": -6.25,
    },
    "quan_engine_position": {
        "reason": "18 picks, 0% WR, 100% SL hits. TAOUSDT only. Sharpe -203.6.",
        "killed_date": "2026-04-11",
        "picks": 18,
        "wr": 0.0,
        "sharpe": -203.6,
    },
    "volume_spike_breakout": {
        "reason": "36 picks, 11.1% WR, 89% SL hits, Sharpe -17.27, PF 0.14.",
        "killed_date": "2026-04-11",
        "picks": 36,
        "wr": 0.111,
        "sharpe": -17.27,
    },
    "stochrsi_macd_combo": {
        "reason": "10 picks, 0% WR, 100% SL hits. Infinite negative Sharpe.",
        "killed_date": "2026-04-11",
        "picks": 10,
        "wr": 0.0,
        "sharpe": -9e16,
    },
}

# Strategies on probation — need more data before trusting
PROBATION_STRATEGIES = {
    "rsi_bounce": {
        "reason": "10 picks, 40% WR but PF=1.0 (exact breakeven). Need 30+ trades.",
        "min_trades_required": 30,
    },
    "macd_rsi_confluence": {
        "reason": "17 picks, 35.3% WR, PF 0.73. Below breakeven. Need improvement.",
        "min_trades_required": 30,
    },
    "futures_momentum": {
        "reason": "9 picks, 0% WR. All PRICE_RESOLVED or FORCE_CLOSED_TOXIC.",
        "min_trades_required": 20,
    },
}

# Strategies with positive evidence — ALLOW
ALLOWED_STRATEGIES = {
    "macd_crossover": {
        "reason": "16 picks, 68.8% WR, Sharpe 11.34, PF 4.09. Best in system.",
        "picks": 16,
        "wr": 0.688,
        "sharpe": 11.34,
    },
    "quan_engine_swing": {
        "reason": "90 picks, 33.3% WR, Sharpe 1.59, PF 1.25. Positive edge.",
        "picks": 90,
        "wr": 0.333,
        "sharpe": 1.59,
    },
    "rsi_overbought": {
        "reason": "5 picks, 60% WR, PF 2.25. Small sample but promising.",
        "picks": 5,
        "wr": 0.60,
        "sharpe": 6.48,
    },
}

# Minimum forward trades before a strategy can generate live picks
MIN_FORWARD_TRADES = 10


class StrategyKiller:
    """
    Gate strategies based on proven live performance.
    
    Problem being fixed:
    The current system has strategies with 0% WR and -203 Sharpe
    still generating live picks. There's no mechanism to auto-kill
    strategies that have been proven to lose money.
    
    This module provides that mechanism.
    """
    
    def __init__(
        self,
        performance_data: Optional[Dict] = None,
        min_forward_trades: int = MIN_FORWARD_TRADES,
    ):
        self.killed = set(KILLED_STRATEGIES.keys())
        self.probation = set(PROBATION_STRATEGIES.keys())
        self.allowed = set(ALLOWED_STRATEGIES.keys())
        self.min_forward_trades = min_forward_trades
        self._performance = performance_data or {}
    
    def load_performance(self, path: str = "alpha_engine/data/strategy_performance.json"):
        """Load latest strategy performance data."""
        try:
            with open(path) as f:
                self._performance = json.load(f)
            logger.info(f"Loaded performance for {len(self._performance)} strategies")
        except FileNotFoundError:
            logger.warning(f"Performance file not found: {path}")
    
    def is_allowed(self, strategy_name: str) -> bool:
        """Check if a strategy is allowed to generate picks."""
        decision = self.evaluate(strategy_name)
        return decision["allowed"]
    
    def evaluate(self, strategy_name: str) -> Dict[str, Any]:
        """
        Full evaluation of a strategy.
        
        Returns:
            Dict with: allowed, reason, status, metrics
        """
        # Check kill list first
        if strategy_name in self.killed:
            info = KILLED_STRATEGIES.get(strategy_name, {})
            return {
                "allowed": False,
                "status": "KILLED",
                "reason": info.get("reason", "Strategy is on kill list"),
                "strategy": strategy_name,
            }
        
        # Check probation
        if strategy_name in self.probation:
            info = PROBATION_STRATEGIES[strategy_name]
            perf = self._performance.get(strategy_name, {})
            current_trades = perf.get("closed_picks", 0)
            min_req = info["min_trades_required"]
            
            if current_trades < min_req:
                return {
                    "allowed": False,
                    "status": "PROBATION",
                    "reason": f"{info['reason']} Has {current_trades}/{min_req} trades.",
                    "strategy": strategy_name,
                }
        
        # Check if strategy has minimum forward trades
        perf = self._performance.get(strategy_name, {})
        forward_trades = perf.get("closed_picks", 0)
        
        if forward_trades < self.min_forward_trades:
            return {
                "allowed": False,
                "status": "NO_TRACK_RECORD",
                "reason": (
                    f"Strategy '{strategy_name}' has only {forward_trades} forward trades "
                    f"(minimum {self.min_forward_trades} required). "
                    f"Cannot assess edge without sufficient data."
                ),
                "strategy": strategy_name,
            }
        
        # Check live performance thresholds
        wr = perf.get("win_rate", 0)
        pf = perf.get("profit_factor", 0)
        sharpe = perf.get("sharpe", 0)
        
        if wr < 0.20 and forward_trades >= 20:
            return {
                "allowed": False,
                "status": "AUTO_KILLED",
                "reason": f"WR {wr:.1%} < 20% on {forward_trades} trades. Auto-killed.",
                "strategy": strategy_name,
            }
        
        if pf < 0.50 and forward_trades >= 30:
            return {
                "allowed": False,
                "status": "AUTO_KILLED",
                "reason": f"PF {pf:.2f} < 0.50 on {forward_trades} trades. Auto-killed.",
                "strategy": strategy_name,
            }
        
        # Passed all checks
        return {
            "allowed": True,
            "status": "ALLOWED",
            "reason": f"Strategy has {forward_trades} trades, WR={wr:.1%}, PF={pf:.2f}",
            "strategy": strategy_name,
            "metrics": {
                "trades": forward_trades,
                "win_rate": wr,
                "profit_factor": pf,
                "sharpe": sharpe,
            },
        }
    
    def get_kill_report(self) -> str:
        """Human-readable kill report."""
        lines = ["Strategy Kill Report", "=" * 60]
        
        lines.append("\n🔴 KILLED (proven negative edge):")
        for name, info in KILLED_STRATEGIES.items():
            lines.append(f"  {name}: {info['reason']}")
        
        lines.append("\n🟡 PROBATION (insufficient evidence):")
        for name, info in PROBATION_STRATEGIES.items():
            lines.append(f"  {name}: {info['reason']}")
        
        lines.append("\n✅ ALLOWED (positive evidence):")
        for name, info in ALLOWED_STRATEGIES.items():
            lines.append(f"  {name}: {info['reason']}")
        
        return "\n".join(lines)
    
    def filter_picks(self, picks: List[Dict]) -> List[Dict]:
        """Filter a list of picks, removing those from killed strategies."""
        allowed = []
        blocked = 0
        
        for pick in picks:
            strategy = pick.get("strategy", "unknown")
            decision = self.evaluate(strategy)
            
            if decision["allowed"]:
                allowed.append(pick)
            else:
                blocked += 1
                logger.info(
                    f"Killed pick from {strategy}: {decision['reason']}"
                )
        
        if blocked > 0:
            logger.info(f"StrategyKiller: blocked {blocked}/{len(picks)} picks")
        
        return allowed
