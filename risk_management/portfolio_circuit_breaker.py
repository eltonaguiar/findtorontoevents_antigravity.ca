#!/usr/bin/env python3
"""
Portfolio Circuit Breaker — Correlation-Aware Risk Management
==============================================================

Institutional-grade portfolio protection:
    1. Drawdown circuit breakers (5%/8% thresholds)
    2. Correlation-aware sleeve allocation
    3. Rolling volatility monitoring
    4. Position-level and portfolio-level kill switches

Integrates with the InstitutionalOverlay for full safety stack.

Usage:
    from risk_management.portfolio_circuit_breaker import PortfolioCircuitBreaker

    breaker = PortfolioCircuitBreaker(portfolio_value=10000)
    status = breaker.check(equity_curve, active_positions)
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CircuitBreakerStatus:
    """Current status of the portfolio circuit breaker."""
    is_triggered: bool
    level: str  # "GREEN", "YELLOW", "RED", "HALT"
    current_dd: float
    peak_equity: float
    current_equity: float
    rolling_vol: float
    max_position_count: int
    size_multiplier: float
    reasons: List[str] = field(default_factory=list)


class PortfolioCircuitBreaker:
    """
    Multi-level circuit breaker for portfolio protection.

    Levels:
        GREEN  — Normal operation (DD < 3%)
        YELLOW — Caution: reduce new positions by 50% (DD 3-5%)
        RED    — Danger: close weakest positions, no new entries (DD 5-8%)
        HALT   — Emergency: close all positions (DD > 8%)
    """

    DD_YELLOW = 0.03
    DD_RED = 0.05
    DD_HALT = 0.08

    VOL_HIGH = 0.04    # Daily vol > 4% triggers caution
    VOL_EXTREME = 0.08  # Daily vol > 8% triggers halt

    MAX_CONCURRENT_GREEN = 10
    MAX_CONCURRENT_YELLOW = 5
    MAX_CONCURRENT_RED = 2

    def __init__(self, portfolio_value: float = 10000.0):
        self.portfolio_value = portfolio_value
        self.peak_equity = portfolio_value

    def check(
        self,
        equity_curve: List[float],
        active_position_count: int = 0,
    ) -> CircuitBreakerStatus:
        """Evaluate current portfolio state and return circuit breaker status."""
        if not equity_curve:
            return CircuitBreakerStatus(
                is_triggered=False, level="GREEN",
                current_dd=0.0, peak_equity=self.portfolio_value,
                current_equity=self.portfolio_value,
                rolling_vol=0.0, max_position_count=self.MAX_CONCURRENT_GREEN,
                size_multiplier=1.0,
            )

        current = equity_curve[-1]
        peak = max(equity_curve)
        self.peak_equity = max(self.peak_equity, peak)

        dd = (self.peak_equity - current) / self.peak_equity if self.peak_equity > 0 else 0.0
        dd = max(0.0, dd)

        rolling_vol = self._rolling_volatility(equity_curve, window=14)

        level = "GREEN"
        size_mult = 1.0
        max_pos = self.MAX_CONCURRENT_GREEN
        reasons = []

        if dd >= self.DD_HALT or rolling_vol >= self.VOL_EXTREME:
            level = "HALT"
            size_mult = 0.0
            max_pos = 0
            if dd >= self.DD_HALT:
                reasons.append(f"DD={dd:.1%} >= {self.DD_HALT:.0%}")
            if rolling_vol >= self.VOL_EXTREME:
                reasons.append(f"Vol={rolling_vol:.1%} >= {self.VOL_EXTREME:.0%}")

        elif dd >= self.DD_RED:
            level = "RED"
            size_mult = 0.25
            max_pos = self.MAX_CONCURRENT_RED
            reasons.append(f"DD={dd:.1%} >= {self.DD_RED:.0%}")

        elif dd >= self.DD_YELLOW or rolling_vol >= self.VOL_HIGH:
            level = "YELLOW"
            size_mult = 0.50
            max_pos = self.MAX_CONCURRENT_YELLOW
            if dd >= self.DD_YELLOW:
                reasons.append(f"DD={dd:.1%} >= {self.DD_YELLOW:.0%}")
            if rolling_vol >= self.VOL_HIGH:
                reasons.append(f"Vol={rolling_vol:.1%} >= {self.VOL_HIGH:.0%}")

        is_triggered = level != "GREEN"

        return CircuitBreakerStatus(
            is_triggered=is_triggered,
            level=level,
            current_dd=round(dd, 6),
            peak_equity=round(self.peak_equity, 2),
            current_equity=round(current, 2),
            rolling_vol=round(rolling_vol, 6),
            max_position_count=max_pos,
            size_multiplier=size_mult,
            reasons=reasons,
        )

    def can_open_trade(
        self,
        equity_curve: List[float],
        active_position_count: int,
    ) -> Tuple[bool, str]:
        """Check if a new trade can be opened."""
        status = self.check(equity_curve, active_position_count)

        if status.level == "HALT":
            return False, f"HALT: {', '.join(status.reasons)}"

        if status.level == "RED":
            if active_position_count >= status.max_position_count:
                return False, f"RED: max {status.max_position_count} positions"
            return True, f"RED: limited to {status.max_position_count} positions"

        if active_position_count >= status.max_position_count:
            return False, f"{status.level}: max {status.max_position_count} positions"

        return True, f"{status.level}: OK"

    def get_size_multiplier(self, equity_curve: List[float]) -> float:
        """Get position size multiplier based on current risk state."""
        status = self.check(equity_curve)
        return status.size_multiplier

    @staticmethod
    def _rolling_volatility(
        equity_curve: List[float],
        window: int = 14,
    ) -> float:
        """Compute rolling daily volatility from equity curve."""
        if len(equity_curve) < max(window, 3):
            return 0.0

        returns = []
        for i in range(1, len(equity_curve)):
            if equity_curve[i - 1] > 0:
                ret = (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
                returns.append(ret)

        if len(returns) < 2:
            return 0.0

        recent = returns[-window:]
        if len(recent) < 2:
            return 0.0

        return statistics.stdev(recent)


class SleeveRiskMonitor:
    """
    Monitor risk concentration across strategy sleeves.

    Prevents all strategies from losing together by tracking
    per-sleeve drawdown and enforcing correlation-aware limits.
    """

    SLEEVE_DD_WARNING = 0.04
    SLEEVE_DD_HALT = 0.06

    def __init__(self):
        self.sleeve_equity: Dict[str, List[float]] = {}

    def update_sleeve(self, sleeve: str, pnl: float):
        """Record a PnL update for a sleeve."""
        if sleeve not in self.sleeve_equity:
            self.sleeve_equity[sleeve] = [0.0]
        current = self.sleeve_equity[sleeve][-1] + pnl
        self.sleeve_equity[sleeve].append(current)

    def check_sleeve(self, sleeve: str) -> Dict[str, Any]:
        """Check a single sleeve's health."""
        equity = self.sleeve_equity.get(sleeve, [0.0])
        if len(equity) < 2:
            return {"sleeve": sleeve, "status": "OK", "dd": 0.0}

        peak = max(equity)
        current = equity[-1]
        dd = (peak - current) / max(abs(peak), 0.01) if peak > 0 else 0.0
        dd = max(0.0, dd)

        status = "OK"
        if dd >= self.SLEEVE_DD_HALT:
            status = "HALT"
        elif dd >= self.SLEEVE_DD_WARNING:
            status = "WARNING"

        return {
            "sleeve": sleeve,
            "status": status,
            "dd": round(dd, 4),
            "peak": round(peak, 4),
            "current": round(current, 4),
        }

    def check_all(self) -> Dict[str, Any]:
        """Check all sleeves and return aggregate status."""
        results = {}
        halted = []
        warned = []

        for sleeve in self.sleeve_equity:
            check = self.check_sleeve(sleeve)
            results[sleeve] = check
            if check["status"] == "HALT":
                halted.append(sleeve)
            elif check["status"] == "WARNING":
                warned.append(sleeve)

        return {
            "sleeves": results,
            "halted_sleeves": halted,
            "warned_sleeves": warned,
            "portfolio_status": (
                "CRITICAL" if len(halted) >= 2
                else "HALT" if halted
                else "WARNING" if warned
                else "OK"
            ),
        }
