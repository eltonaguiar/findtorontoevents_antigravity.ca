#!/usr/bin/env python3
"""
Concentration Checker — HF P1 #5

Enforces portfolio concentration limits per config/risk_policy.json (approved 2026-04-04):
  - max_equity_pct_per_symbol: 10% (block if one symbol > 10% of total equity)
  - max_equity_pct_per_direction: 20% (block if LONG or SHORT side > 20%)
  - max_portfolios_same_symbol_direction: 2 (block if >2 portfolios hold same symbol+direction)
  - per_trade_cap_pct: 5% (single trade max size)

Usage:
    from alpha_engine.concentration_checker import (
        check_portfolio_concentration,
        check_pick_against_portfolio,
        ConcentrationViolation,
    )

    # Check existing portfolio state
    violations = check_portfolio_concentration(active_positions, total_equity)

    # Check if new pick would violate limits
    can_add, reason = check_pick_against_portfolio(new_pick, active_positions, total_equity)

Policy source: docs/HEDGE_FUND_QUALITY_NEXT_STEPS.md (Threshold B)
Incident reference: ALGO 30%-equity concentration (bus 2026-04-04)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict

from alpha_engine.risk_policy_loader import load_risk_policy


@dataclass
class ConcentrationViolation:
    """A single concentration limit violation."""
    violation_type: str  # SYMBOL_CONCENTRATION, DIRECTION_CONCENTRATION, PORTFOLIO_OVERLAP
    severity: str        # BLOCK, WARN
    symbol: Optional[str]
    direction: Optional[str]
    current_pct: float
    limit_pct: float
    message: str


class ConcentrationChecker:
    """
    Enforce concentration limits on portfolio positions.

    Thresholds loaded from config/risk_policy.json with fallback defaults.
    """

    def __init__(self, asset_class: str = "crypto"):
        self.policy = load_risk_policy()
        self.asset_class = asset_class

        # Load thresholds for this asset class
        ac_policy = self.policy.get(asset_class, self.policy.get("crypto", {}))
        self.max_symbol_pct = float(ac_policy.get("max_equity_pct_per_symbol", 10))
        self.max_direction_pct = float(ac_policy.get("max_equity_pct_per_direction", 20))
        self.max_portfolio_overlap = int(ac_policy.get("max_portfolios_same_symbol_direction", 2))
        self.per_trade_cap_pct = float(ac_policy.get("per_trade_cap_pct", 5))

    def check_portfolio(
        self,
        positions: List[Dict[str, Any]],
        total_equity: float,
    ) -> List[ConcentrationViolation]:
        """
        Check all active positions for concentration violations.

        Args:
            positions: List of position dicts with keys:
                - symbol: str (e.g., "BTCUSDT")
                - direction: str ("LONG" or "SHORT")
                - notional: float (position value in USD)
                - portfolio: str (optional, portfolio ID)

            total_equity: Total portfolio equity in USD

        Returns:
            List of ConcentrationViolation objects (empty if compliant)
        """
        if total_equity <= 0:
            return []

        violations = []

        # 1. Symbol concentration check
        symbol_notional: Dict[str, float] = defaultdict(float)
        for pos in positions:
            sym = pos.get("symbol", "UNKNOWN")
            notional = float(pos.get("notional", 0))
            symbol_notional[sym] += notional

        for sym, notional in symbol_notional.items():
            pct = (notional / total_equity) * 100
            if pct > self.max_symbol_pct:
                violations.append(ConcentrationViolation(
                    violation_type="SYMBOL_CONCENTRATION",
                    severity="BLOCK",
                    symbol=sym,
                    direction=None,
                    current_pct=round(pct, 1),
                    limit_pct=self.max_symbol_pct,
                    message=f"Symbol {sym} at {pct:.1f}% exceeds {self.max_symbol_pct}% limit",
                ))

        # 2. Direction concentration check
        direction_notional: Dict[str, float] = defaultdict(float)
        for pos in positions:
            direction = pos.get("direction", "UNKNOWN").upper()
            if direction in ("BUY", "LONG"):
                direction = "LONG"
            elif direction in ("SELL", "SHORT"):
                direction = "SHORT"
            notional = float(pos.get("notional", 0))
            direction_notional[direction] += notional

        for direction, notional in direction_notional.items():
            pct = (notional / total_equity) * 100
            if pct > self.max_direction_pct:
                violations.append(ConcentrationViolation(
                    violation_type="DIRECTION_CONCENTRATION",
                    severity="BLOCK",
                    symbol=None,
                    direction=direction,
                    current_pct=round(pct, 1),
                    limit_pct=self.max_direction_pct,
                    message=f"Direction {direction} at {pct:.1f}% exceeds {self.max_direction_pct}% limit",
                ))

        # 3. Portfolio overlap check (same symbol+direction across portfolios)
        sym_dir_portfolios: Dict[str, set] = defaultdict(set)
        for pos in positions:
            sym = pos.get("symbol", "UNKNOWN")
            direction = pos.get("direction", "UNKNOWN").upper()
            if direction in ("BUY", "LONG"):
                direction = "LONG"
            elif direction in ("SELL", "SHORT"):
                direction = "SHORT"
            portfolio = pos.get("portfolio", "default")
            key = f"{sym}:{direction}"
            sym_dir_portfolios[key].add(portfolio)

        for key, portfolios in sym_dir_portfolios.items():
            if len(portfolios) > self.max_portfolio_overlap:
                sym, direction = key.split(":")
                violations.append(ConcentrationViolation(
                    violation_type="PORTFOLIO_OVERLAP",
                    severity="WARN",
                    symbol=sym,
                    direction=direction,
                    current_pct=len(portfolios),
                    limit_pct=self.max_portfolio_overlap,
                    message=f"{sym} {direction} held in {len(portfolios)} portfolios (max {self.max_portfolio_overlap})",
                ))

        return violations

    def can_add_pick(
        self,
        pick: Dict[str, Any],
        positions: List[Dict[str, Any]],
        total_equity: float,
        proposed_notional: Optional[float] = None,
    ) -> Tuple[bool, str, Optional[ConcentrationViolation]]:
        """
        Check if adding a new pick would violate concentration limits.

        Args:
            pick: New pick dict with symbol, direction
            positions: Current active positions
            total_equity: Total portfolio equity
            proposed_notional: Proposed position size (default: per_trade_cap_pct of equity)

        Returns:
            (can_add, reason, violation)
            - can_add: True if pick is allowed
            - reason: Human-readable explanation
            - violation: ConcentrationViolation if blocked, None otherwise
        """
        if total_equity <= 0:
            return True, "No equity limit to check", None

        sym = pick.get("symbol", "UNKNOWN")
        direction = pick.get("direction", "UNKNOWN").upper()
        if direction in ("BUY", "LONG"):
            direction = "LONG"
        elif direction in ("SELL", "SHORT"):
            direction = "SHORT"

        # Default proposed size
        if proposed_notional is None:
            proposed_notional = total_equity * (self.per_trade_cap_pct / 100)

        # Calculate post-add concentrations
        # 1. Symbol concentration
        current_symbol_notional = sum(
            float(p.get("notional", 0))
            for p in positions
            if p.get("symbol") == sym
        )
        new_symbol_pct = ((current_symbol_notional + proposed_notional) / total_equity) * 100

        if new_symbol_pct > self.max_symbol_pct:
            violation = ConcentrationViolation(
                violation_type="SYMBOL_CONCENTRATION",
                severity="BLOCK",
                symbol=sym,
                direction=direction,
                current_pct=round(new_symbol_pct, 1),
                limit_pct=self.max_symbol_pct,
                message=f"Adding {sym} would raise concentration to {new_symbol_pct:.1f}% (limit {self.max_symbol_pct}%)",
            )
            return False, violation.message, violation

        # 2. Direction concentration
        current_direction_notional = sum(
            float(p.get("notional", 0))
            for p in positions
            if self._normalize_direction(p.get("direction", "")) == direction
        )
        new_direction_pct = ((current_direction_notional + proposed_notional) / total_equity) * 100

        if new_direction_pct > self.max_direction_pct:
            violation = ConcentrationViolation(
                violation_type="DIRECTION_CONCENTRATION",
                severity="BLOCK",
                symbol=sym,
                direction=direction,
                current_pct=round(new_direction_pct, 1),
                limit_pct=self.max_direction_pct,
                message=f"Adding {sym} {direction} would raise {direction} exposure to {new_direction_pct:.1f}% (limit {self.max_direction_pct}%)",
            )
            return False, violation.message, violation

        # 3. Portfolio overlap (check if this portfolio would be a 3rd holder)
        portfolio = pick.get("portfolio", "default")
        key = f"{sym}:{direction}"
        existing_portfolios = set(
            p.get("portfolio", "default")
            for p in positions
            if p.get("symbol") == sym and self._normalize_direction(p.get("direction", "")) == direction
        )

        if portfolio not in existing_portfolios and len(existing_portfolios) >= self.max_portfolio_overlap:
            violation = ConcentrationViolation(
                violation_type="PORTFOLIO_OVERLAP",
                severity="WARN",
                symbol=sym,
                direction=direction,
                current_pct=len(existing_portfolios) + 1,
                limit_pct=self.max_portfolio_overlap,
                message=f"Adding {sym} {direction} to {portfolio} would be {len(existing_portfolios) + 1}th portfolio (max {self.max_portfolio_overlap})",
            )
            # WARN doesn't block, but returns the violation
            return True, f"WARNING: {violation.message}", violation

        return True, f"OK: {sym} {direction} passes concentration checks", None

    @staticmethod
    def _normalize_direction(direction: str) -> str:
        """Normalize direction to LONG or SHORT."""
        d = (direction or "").upper()
        if d in ("BUY", "LONG"):
            return "LONG"
        if d in ("SELL", "SHORT"):
            return "SHORT"
        return d

    def generate_report(
        self,
        positions: List[Dict[str, Any]],
        total_equity: float,
    ) -> str:
        """Generate human-readable concentration report."""
        violations = self.check_portfolio(positions, total_equity)

        lines = [
            "=" * 80,
            "CONCENTRATION CHECK REPORT",
            "=" * 80,
            f"Asset Class: {self.asset_class.upper()}",
            f"Total Equity: ${total_equity:,.2f}",
            f"Active Positions: {len(positions)}",
            "",
            "Policy Limits:",
            f"  - Max per symbol: {self.max_symbol_pct}%",
            f"  - Max per direction: {self.max_direction_pct}%",
            f"  - Max portfolios same symbol-direction: {self.max_portfolio_overlap}",
            f"  - Per-trade cap: {self.per_trade_cap_pct}%",
            "",
        ]

        if not violations:
            lines.append("✅ No concentration violations detected")
        else:
            lines.append(f"⚠️ {len(violations)} VIOLATIONS DETECTED:")
            lines.append("")
            for v in violations:
                emoji = "🚫" if v.severity == "BLOCK" else "⚠️"
                lines.append(f"  {emoji} [{v.violation_type}] {v.message}")

        # Symbol breakdown
        lines.extend([
            "",
            "-" * 80,
            "SYMBOL BREAKDOWN",
            "-" * 80,
        ])

        symbol_notional: Dict[str, float] = defaultdict(float)
        for pos in positions:
            sym = pos.get("symbol", "UNKNOWN")
            notional = float(pos.get("notional", 0))
            symbol_notional[sym] += notional

        sorted_symbols = sorted(symbol_notional.items(), key=lambda x: x[1], reverse=True)
        for sym, notional in sorted_symbols[:10]:
            pct = (notional / total_equity) * 100 if total_equity > 0 else 0
            flag = "🚫" if pct > self.max_symbol_pct else "  "
            lines.append(f"  {flag} {sym:15} ${notional:>12,.2f} ({pct:5.1f}%)")

        # Direction breakdown
        lines.extend([
            "",
            "-" * 80,
            "DIRECTION BREAKDOWN",
            "-" * 80,
        ])

        direction_notional: Dict[str, float] = defaultdict(float)
        for pos in positions:
            d = self._normalize_direction(pos.get("direction", ""))
            notional = float(pos.get("notional", 0))
            direction_notional[d] += notional

        for direction in ["LONG", "SHORT"]:
            notional = direction_notional.get(direction, 0)
            pct = (notional / total_equity) * 100 if total_equity > 0 else 0
            flag = "🚫" if pct > self.max_direction_pct else "  "
            lines.append(f"  {flag} {direction:10} ${notional:>12,.2f} ({pct:5.1f}%)")

        lines.extend([
            "",
            "=" * 80,
            f"Generated by ConcentrationChecker (policy v{self.policy.get('version', 1)})",
            "=" * 80,
        ])

        return "\n".join(lines)


# Module-level convenience functions
def check_portfolio_concentration(
    positions: List[Dict[str, Any]],
    total_equity: float,
    asset_class: str = "crypto",
) -> List[ConcentrationViolation]:
    """Check portfolio for concentration violations."""
    checker = ConcentrationChecker(asset_class)
    return checker.check_portfolio(positions, total_equity)


def check_pick_against_portfolio(
    pick: Dict[str, Any],
    positions: List[Dict[str, Any]],
    total_equity: float,
    proposed_notional: Optional[float] = None,
    asset_class: str = "crypto",
) -> Tuple[bool, str, Optional[ConcentrationViolation]]:
    """Check if adding a pick would violate concentration limits."""
    checker = ConcentrationChecker(asset_class)
    return checker.can_add_pick(pick, positions, total_equity, proposed_notional)


def main():
    """Example usage."""
    # Sample positions
    positions = [
        {"symbol": "BTCUSDT", "direction": "LONG", "notional": 5000, "portfolio": "SCALPER"},
        {"symbol": "BTCUSDT", "direction": "LONG", "notional": 3000, "portfolio": "TESTER"},
        {"symbol": "ETHUSDT", "direction": "LONG", "notional": 4000, "portfolio": "SCALPER"},
        {"symbol": "SOLUSDT", "direction": "SHORT", "notional": 2000, "portfolio": "TESTER"},
        {"symbol": "ALGOUSDT", "direction": "LONG", "notional": 8000, "portfolio": "TRUSTOURSCORE"},  # Over limit
    ]

    total_equity = 50000

    checker = ConcentrationChecker("crypto")
    print(checker.generate_report(positions, total_equity))

    # Test adding a new pick
    new_pick = {"symbol": "ALGOUSDT", "direction": "LONG", "portfolio": "BROKIE"}
    can_add, reason, violation = checker.can_add_pick(new_pick, positions, total_equity, 3000)
    print(f"\nCan add ALGOUSDT LONG to BROKIE? {can_add}")
    print(f"Reason: {reason}")


if __name__ == "__main__":
    main()
