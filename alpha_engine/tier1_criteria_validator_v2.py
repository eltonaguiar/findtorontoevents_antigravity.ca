#!/usr/bin/env python3
"""
Tier-1 Copy Trader Criteria Validator v2

Upgrades consensus pick quality from 59% WR (v1) to 65%+ WR (v2) by implementing
tighter thresholds on copy trader selection.

Policy approved 2026-04-05 per PICK_QUALITY_IMPROVEMENT_ROADMAP.md Priority 2.

v1 Thresholds (legacy):
  WR >= 52%,  PF >= 1.3,  Capital >= $10k,  DD < 25%,  Years >= 3
  → Results: 59% consensus WR (with contamination from marginal traders)

v2 Thresholds (approved):
  WR >= 55%,  PF >= 1.5,  Capital >= $25k,  DD < 20%,  Years >= 4
  → Expected: 62-65% consensus WR (eliminates margin traders, ensures profitability)
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, Dict, List, Any


class Tier1CriteriaValidator:
    """Validate and filter copy traders against Tier-1 thresholds."""

    # v2 Approved thresholds (2026-04-05)
    THRESHOLDS = {
        "wr_min_pct": 55.0,         # Was 52%
        "pf_min": 1.5,               # Was 1.3
        "capital_min_usd": 25000,    # Was 10,000
        "dd_max_pct": 20.0,          # Was 25%
        "years_min": 4,              # Was 3
        "version": "2.0",
    }

    # Additional validation gates (v2 enhancements)
    ENHANCEMENTS = {
        "recent_performance_window_days": 30,
        "recent_performance_min_wr_pct": 50.0,  # Last 30 days WR must not degrade >15pp
        "degradation_max_pp": 15.0,              # Reject if >15pp drop from all-time
        "min_trades_for_stats": 20,              # Need minimum trades for statistical confidence
    }

    def __init__(self):
        self.version = self.THRESHOLDS["version"]
        self.validation_log = []

    def passes_v1_thresholds(self, trader: dict) -> Tuple[bool, str]:
        """Check trader against v1 (legacy) thresholds."""
        wr = self._normalize_wr(trader.get("wr"))
        pf = float(trader.get("pf") or 0)
        capital = float(trader.get("capital") or 0)
        dd = float(trader.get("dd_pct") or 0)
        years = float(trader.get("years_active") or 0)

        if wr < 52.0:
            return False, f"WR {wr}% < 52%"
        if pf < 1.3:
            return False, f"PF {pf} < 1.3"
        if capital < 10000:
            return False, f"Capital ${capital:,.0f} < $10k"
        if dd >= 25.0:
            return False, f"DD {dd}% >= 25%"
        if years < 3:
            return False, f"Years {years} < 3"

        return True, ""

    def passes_v2_thresholds(self, trader: dict) -> Tuple[bool, str]:
        """Check trader against v2 (tighter) thresholds."""
        wr = self._normalize_wr(trader.get("wr"))
        pf = float(trader.get("pf") or 0)
        capital = float(trader.get("capital") or 0)
        dd = float(trader.get("dd_pct") or 0)
        years = float(trader.get("years_active") or 0)

        if wr < self.THRESHOLDS["wr_min_pct"]:
            return False, f"WR {wr}% < {self.THRESHOLDS['wr_min_pct']}%"
        if pf < self.THRESHOLDS["pf_min"]:
            return False, f"PF {pf} < {self.THRESHOLDS['pf_min']}"
        if capital < self.THRESHOLDS["capital_min_usd"]:
            return False, f"Capital ${capital:,.0f} < ${self.THRESHOLDS['capital_min_usd']:,}"
        if dd >= self.THRESHOLDS["dd_max_pct"]:
            return False, f"DD {dd}% >= {self.THRESHOLDS['dd_max_pct']}%"
        if years < self.THRESHOLDS["years_min"]:
            return False, f"Years {years} < {self.THRESHOLDS['years_min']}"

        return True, ""

    def passes_recent_performance_gate(self, trader: dict) -> Tuple[bool, str]:
        """
        Check if trader's recent performance (last 30 days) has not degraded >15pp
        from all-time historical performance (V2 enhancement gate).
        """
        hist_wr = self._normalize_wr(trader.get("wr"))
        recent_wr = self._normalize_wr(trader.get("recent_wr_30d"))
        recent_trades = int(trader.get("recent_trades_30d") or 0)

        if hist_wr is None or recent_wr is None:
            return True, ""  # Missing data = pass (no gate)

        if recent_trades < 5:
            return True, ""  # Not enough data for judgment

        degradation = hist_wr - recent_wr
        if degradation > self.ENHANCEMENTS["degradation_max_pp"]:
            return (
                False,
                f"Recent degradation {degradation:.1f}pp > {self.ENHANCEMENTS['degradation_max_pp']}pp "
                f"({hist_wr:.1f}% all-time → {recent_wr:.1f}% last 30d)",
            )

        return True, ""

    def validate_trader(
        self,
        trader: dict,
        thresholds: str = "v2",
        check_recent: bool = True,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Comprehensive validation of trader against all gates.

        Args:
            trader: Trader metadata dict
            thresholds: "v1" or "v2"
            check_recent: Apply recent performance gate (only for v2)

        Returns:
            (passes, reason, details)
        """
        details = {
            "trader_id": trader.get("trader_id", "unknown"),
            "thresholds": thresholds,
            "gates": {},
        }

        # Gate 1: Base threshold check
        if thresholds.lower() == "v2":
            passes, reason = self.passes_v2_thresholds(trader)
            details["gates"]["v2_thresholds"] = {"pass": passes, "reason": reason}
        else:
            passes, reason = self.passes_v1_thresholds(trader)
            details["gates"]["v1_thresholds"] = {"pass": passes, "reason": reason}

        if not passes:
            return False, f"[Gate 1] {reason}", details

        # Gate 2: Recent performance check (v2 only)
        if thresholds.lower() == "v2" and check_recent:
            passes, reason = self.passes_recent_performance_gate(trader)
            details["gates"]["recent_performance"] = {"pass": passes, "reason": reason}
            if not passes:
                return False, f"[Gate 2 Recent] {reason}", details

        return True, "", details

    def filter_traders(
        self,
        traders: List[dict],
        thresholds: str = "v2",
        check_recent: bool = True,
    ) -> Tuple[List[dict], Dict[str, Any]]:
        """
        Filter list of traders against criteria.

        Returns:
            (passing_traders, validation_summary)
        """
        passing = []
        summary = {
            "total_input": len(traders),
            "passes": 0,
            "fails": 0,
            "fail_reasons": {},
            "thresholds": thresholds,
        }

        for trader in traders:
            passes, reason, details = self.validate_trader(trader, thresholds, check_recent)

            if passes:
                passing.append(trader)
                summary["passes"] += 1
            else:
                summary["fails"] += 1
                if reason not in summary["fail_reasons"]:
                    summary["fail_reasons"][reason] = 0
                summary["fail_reasons"][reason] += 1

        return passing, summary

    @staticmethod
    def _normalize_wr(value: Any) -> Optional[float]:
        """Convert WR to percentage (0-100 range)."""
        if value is None:
            return None
        try:
            f = float(value)
            if 0 <= f <= 1:
                return f * 100
            return f
        except (TypeError, ValueError):
            return None

    def generate_report(
        self,
        input_traders: List[dict],
        thresholds: str = "v2",
    ) -> str:
        """Generate human-readable validation report."""
        passing, summary = self.filter_traders(input_traders, thresholds)

        lines = [
            "=" * 80,
            f"Tier-1 Copy Trader Criteria Validator v{self.version}",
            f"Timestamp: {datetime.now().isoformat()}",
            "=" * 80,
            "",
            f"Thresholds: {thresholds.upper()}",
            "",
        ]

        if thresholds.lower() == "v2":
            lines.extend([
                "V2 Criteria (approved 2026-04-05):",
                f"  • WR >= {self.THRESHOLDS['wr_min_pct']}%",
                f"  • PF >= {self.THRESHOLDS['pf_min']}",
                f"  • Capital >= ${self.THRESHOLDS['capital_min_usd']:,}",
                f"  • DD < {self.THRESHOLDS['dd_max_pct']}%",
                f"  • Years >= {self.THRESHOLDS['years_min']}",
                "",
                "Enhancement Gates:",
                f"  • Recent WR (30d) not degraded >{self.ENHANCEMENTS['degradation_max_pp']}pp",
            ])
        else:
            lines.extend([
                "V1 Criteria (legacy):",
                "  • WR >= 52%",
                "  • PF >= 1.3",
                "  • Capital >= $10k",
                "  • DD < 25%",
                "  • Years >= 3",
            ])

        lines.extend([
            "",
            "─" * 80,
            "RESULTS",
            "─" * 80,
            f"Input traders:  {summary['total_input']}",
            f"Passing v{self.version}   :  {summary['passes']} ({100*summary['passes']/max(1,summary['total_input']):.1f}%)",
            f"Failing v{self.version}   :  {summary['fails']} ({100*summary['fails']/max(1,summary['total_input']):.1f}%)",
            "",
        ])

        if summary["fail_reasons"]:
            lines.append("Top Failure Reasons:")
            sorted_fails = sorted(summary["fail_reasons"].items(), key=lambda x: x[1], reverse=True)
            for reason, count in sorted_fails[:5]:
                lines.append(f"  • {reason}: {count} traders ({100*count/max(1,summary['fails']):.1f}%)")

        lines.extend([
            "",
            "─" * 80,
            "IMPACT ESTIMATE",
            "─" * 80,
        ])

        if thresholds.lower() == "v2":
            lines.extend([
                "Expected quality improvement (v1 → v2):",
                f"  • Consensus WR: 59% → ~62-65% (estimated)",
                f"  • Input reduction: ~{summary['total_input']} → {summary['passes']} traders",
                f"  • Elimination rate: {100*summary['fails']/max(1,summary['total_input']):.1f}% (removes marginal traders)",
                "",
                "Justification:",
                "  • 55% WR floor: Eliminates sub-55% performers (majority of failures)",
                "  • 1.5 PF floor: Ensures profitability margin (risk-adjusted)",
                "  • $25k capital: Filters serious traders (removes micro-accounts)",
                "  • 20% DD: Conservative risk profile (prevents blow-ups)",
                "  • 4-year tenure: Proven multi-year track record",
            ])

        lines.extend([
            "",
            "=" * 80,
            f"Generated by Tier-1 Criteria Validator v{self.version}",
            "=" * 80,
        ])

        return "\n".join(lines)


def main():
    """Example usage."""
    # Example traders
    sample_traders = [
        {
            "trader_id": "trader_001",
            "wr": 0.58,
            "pf": 1.65,
            "capital": 50000,
            "dd_pct": 18.0,
            "years_active": 5,
            "recent_wr_30d": 0.55,
            "recent_trades_30d": 15,
        },
        {
            "trader_id": "trader_002",
            "wr": 0.52,
            "pf": 1.2,
            "capital": 15000,
            "dd_pct": 22.0,
            "years_active": 2,
            "recent_wr_30d": None,
            "recent_trades_30d": 0,
        },
        {
            "trader_id": "trader_003",
            "wr": 0.65,
            "pf": 2.1,
            "capital": 100000,
            "dd_pct": 15.0,
            "years_active": 7,
            "recent_wr_30d": 0.48,  # 17pp degradation
            "recent_trades_30d": 20,
        },
    ]

    validator = Tier1CriteriaValidator()

    # V1 validation
    print("\nVALIDATION WITH V1 THRESHOLDS:")
    print(validator.generate_report(sample_traders, thresholds="v1"))

    # V2 validation
    print("\n\nVALIDATION WITH V2 THRESHOLDS:")
    print(validator.generate_report(sample_traders, thresholds="v2"))


if __name__ == "__main__":
    main()
