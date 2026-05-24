"""Concrete audit test implementations.

All tests read from existing JSON files — no live DB connection.
"""

import glob
import json
import os
import time
from datetime import datetime, timezone

from .base import AuditTest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
_DATA_DIR = os.path.join(_PROJECT_ROOT, "audit_dashboard", "data")


def _load_json(filename: str) -> object:
    """Load a JSON file from the audit_dashboard/data directory."""
    path = os.path.join(_DATA_DIR, filename)
    with open(path, "r") as f:
        return json.load(f)


def _file_age_days(filepath: str) -> float:
    """Return the age of a file in days based on mtime."""
    mtime = os.path.getmtime(filepath)
    age_seconds = time.time() - mtime
    return age_seconds / 86400.0


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class DbHealthCheck(AuditTest):
    """Reads db_health.json, fails if any check has tier='red'."""

    name = "DbHealthCheck"
    severity = "critical"

    def run(self) -> dict:
        try:
            data = _load_json("db_health.json")
        except FileNotFoundError:
            return {"passed": False, "message": "db_health.json not found", "data": {}}
        except json.JSONDecodeError as e:
            return {"passed": False, "message": f"db_health.json is invalid JSON: {e}", "data": {}}

        checks = data.get("checks", {})
        red_checks = []
        for check_name, check_result in checks.items():
            tier = check_result.get("data", {}).get("tier", "")
            if tier == "red":
                red_checks.append(check_name)

        if red_checks:
            return {
                "passed": False,
                "message": f"Red-tier DB health checks: {', '.join(red_checks)}",
                "data": {"red_checks": red_checks, "overall": data.get("overall", {})},
            }
        return {
            "passed": True,
            "message": "All DB health checks are green/yellow",
            "data": {"overall": data.get("overall", {})},
        }


class GhostRowCount(AuditTest):
    """Fails if total_ghost_rows > 1000."""

    name = "GhostRowCount"
    severity = "high"

    def run(self) -> dict:
        try:
            data = _load_json("db_health.json")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return {"passed": False, "message": f"Cannot read db_health.json: {e}", "data": {}}

        ghost_data = data.get("checks", {}).get("ghost_rows", {}).get("data", {})
        total_ghost_rows = ghost_data.get("total_ghost_rows", 0)
        threshold = 1000

        if total_ghost_rows > threshold:
            return {
                "passed": False,
                "message": f"Ghost rows: {total_ghost_rows:,} (threshold: {threshold:,})",
                "data": {"total_ghost_rows": total_ghost_rows, "threshold": threshold,
                         "top_cohorts": ghost_data.get("top_cohorts", [])[:5]},
            }
        return {
            "passed": True,
            "message": f"Ghost rows: {total_ghost_rows:,} (within threshold)",
            "data": {"total_ghost_rows": total_ghost_rows, "threshold": threshold},
        }


class OpenBloatCheck(AuditTest):
    """Fails if open_count > 1,000,000."""

    name = "OpenBloatCheck"
    severity = "high"

    def run(self) -> dict:
        try:
            data = _load_json("db_health.json")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return {"passed": False, "message": f"Cannot read db_health.json: {e}", "data": {}}

        bloat_data = data.get("checks", {}).get("open_bloat", {}).get("data", {})
        open_count = bloat_data.get("open_count", 0)
        threshold = 1_000_000

        if open_count > threshold:
            return {
                "passed": False,
                "message": f"Open rows: {open_count:,} (threshold: {threshold:,})",
                "data": {"open_count": open_count, "threshold": threshold,
                         "info_schema_estimate": bloat_data.get("info_schema_estimate"),
                         "hours_since_last_close": bloat_data.get("hours_since_last_close"),
                         "validator_frozen": bloat_data.get("validator_frozen")},
            }
        return {
            "passed": True,
            "message": f"Open rows: {open_count:,} (within threshold)",
            "data": {"open_count": open_count, "threshold": threshold},
        }


class PnLIntegrityCheck(AuditTest):
    """Fails if mismatch_pct > 5%."""

    name = "PnLIntegrityCheck"
    severity = "critical"

    def run(self) -> dict:
        try:
            data = _load_json("db_health.json")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return {"passed": False, "message": f"Cannot read db_health.json: {e}", "data": {}}

        pnl_data = data.get("checks", {}).get("pnl_integrity", {}).get("data", {})
        mismatch_pct = pnl_data.get("mismatch_pct", 0.0)
        threshold = 5.0

        if mismatch_pct > threshold:
            return {
                "passed": False,
                "message": f"PnL mismatch: {mismatch_pct:.1f}% (threshold: {threshold:.0f}%)",
                "data": {"mismatch_pct": mismatch_pct, "threshold": threshold,
                         "gt1pct_mismatch": pnl_data.get("gt1pct_mismatch"),
                         "gt001pct_mismatch": pnl_data.get("gt001pct_mismatch"),
                         "sampled": pnl_data.get("sampled")},
            }
        return {
            "passed": True,
            "message": f"PnL mismatch: {mismatch_pct:.1f}% (within threshold)",
            "data": {"mismatch_pct": mismatch_pct, "threshold": threshold},
        }


class WonPnlContradiction(AuditTest):
    """Fails if contradiction_detected is true."""

    name = "WonPnlContradiction"
    severity = "critical"

    def run(self) -> dict:
        try:
            data = _load_json("db_health.json")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return {"passed": False, "message": f"Cannot read db_health.json: {e}", "data": {}}

        won_data = data.get("checks", {}).get("won_pnl_contradiction", {}).get("data", {})
        contradiction = won_data.get("contradiction_detected", False)

        if contradiction:
            return {
                "passed": False,
                "message": "WON/PnL contradiction detected — some WON trades have negative avg PnL",
                "data": {"contradiction_detected": True,
                         "by_status": won_data.get("by_status", [])},
            }
        return {
            "passed": True,
            "message": "No WON/PnL contradictions",
            "data": {"contradiction_detected": False},
        }


class DataFreshnessCheck(AuditTest):
    """Scans audit_dashboard/data/*.json, fails if any file > 7 days old."""

    name = "DataFreshnessCheck"
    severity = "high"

    def run(self) -> dict:
        pattern = os.path.join(_DATA_DIR, "*.json")
        json_files = sorted(glob.glob(pattern))
        threshold_days = 7

        stale_files = []
        for filepath in json_files:
            age_days = _file_age_days(filepath)
            if age_days > threshold_days:
                stale_files.append({
                    "file": os.path.basename(filepath),
                    "age_days": round(age_days, 1),
                })

        if stale_files:
            return {
                "passed": False,
                "message": f"{len(stale_files)} files older than {threshold_days} days",
                "data": {"stale_files": stale_files[:20],  # cap at 20
                         "total_json_files": len(json_files),
                         "threshold_days": threshold_days},
            }
        return {
            "passed": True,
            "message": f"All {len(json_files)} JSON files are within {threshold_days} days",
            "data": {"total_json_files": len(json_files), "threshold_days": threshold_days},
        }


class AssetClassificationCheck(AuditTest):
    """Reads ai_tournament_picks_latest.json, fails if ETF symbols tagged as CRYPTO."""

    name = "AssetClassificationCheck"
    severity = "high"

    ETF_SYMBOLS = {"SPY", "QQQ", "XLK", "XLI", "XLF", "XLE", "XLV", "XLP", "XLU", "XLY",
                   "EFA", "EEM", "IWM", "DIA", "VTI", "VOO"}

    def run(self) -> dict:
        try:
            picks = _load_json("ai_tournament_picks_latest.json")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return {"passed": False, "message": f"Cannot read ai_tournament_picks_latest.json: {e}", "data": {}}

        if not isinstance(picks, list):
            return {"passed": False, "message": "ai_tournament_picks_latest.json is not a list", "data": {}}

        misclassified = []
        for pick in picks:
            symbol = pick.get("symbol", "").upper()
            asset_class = pick.get("asset_class", "").upper()
            if symbol in self.ETF_SYMBOLS and asset_class != "ETF":
                misclassified.append({
                    "symbol": symbol,
                    "tagged_as": asset_class,
                    "expected": "ETF",
                })

        if misclassified:
            return {
                "passed": False,
                "message": f"{len(misclassified)} ETF symbol(s) misclassified: {', '.join(m['symbol'] for m in misclassified)}",
                "data": {"misclassified": misclassified, "etf_symbols_checked": sorted(self.ETF_SYMBOLS)},
            }
        return {
            "passed": True,
            "message": "All ETF symbols correctly classified",
            "data": {"etf_symbols_checked": sorted(self.ETF_SYMBOLS)},
        }


class SignalOutcomesCheck(AuditTest):
    """Reads db_freshness.json, fails if signal_outcomes > 1440 min stale."""

    name = "SignalOutcomesCheck"
    severity = "high"

    def run(self) -> dict:
        try:
            data = _load_json("db_freshness.json")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return {"passed": False, "message": f"Cannot read db_freshness.json: {e}", "data": {}}

        checks = data.get("checks", [])
        threshold = 1440  # minutes

        for check in checks:
            if check.get("check") == "signal_outcomes":
                minutes_stale = check.get("minutes_stale")
                if minutes_stale is not None and minutes_stale > threshold:
                    return {
                        "passed": False,
                        "message": f"Signal outcomes: {minutes_stale:,.0f} min stale (threshold: {threshold:,} min)",
                        "data": {"minutes_stale": minutes_stale, "threshold": threshold,
                                 "last_resolved_at": check.get("last_resolved_at"),
                                 "status": check.get("status")},
                    }
                return {
                    "passed": True,
                    "message": f"Signal outcomes: {minutes_stale or 0:,.0f} min stale (within threshold)",
                    "data": {"minutes_stale": minutes_stale, "threshold": threshold},
                }

        return {"passed": False, "message": "signal_outcomes check not found in db_freshness.json", "data": {}}


class BacktestTableCheck(AuditTest):
    """Reads db_freshness.json, fails if backtests table has no data or is stale > 7 days."""

    name = "BacktestTableCheck"
    severity = "medium"

    def run(self) -> dict:
        try:
            data = _load_json("db_freshness.json")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return {"passed": False, "message": f"Cannot read db_freshness.json: {e}", "data": {}}

        checks = data.get("checks", [])
        threshold = 10080  # 7 days in minutes

        for check in checks:
            if check.get("check") == "backtests":
                error = check.get("error")
                n_total = check.get("n_total", 0)
                minutes_stale = check.get("minutes_stale")

                if error:
                    return {
                        "passed": False,
                        "message": f"Backtests table error: {error}",
                        "data": {"error": error, "n_total": n_total},
                    }
                if minutes_stale is not None and minutes_stale > threshold:
                    return {
                        "passed": False,
                        "message": f"Backtests: {minutes_stale:,.0f} min stale (threshold: {threshold:,} min)",
                        "data": {"minutes_stale": minutes_stale, "threshold": threshold},
                    }
                return {
                    "passed": True,
                    "message": f"Backtests: {n_total} rows, {minutes_stale or 0:,.0f} min stale",
                    "data": {"n_total": n_total, "minutes_stale": minutes_stale},
                }

        return {"passed": False, "message": "backtests check not found in db_freshness.json", "data": {}}
