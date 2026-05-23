"""
Strict asset-class filter generator for /audit real-money readiness.

Reads verdict-grade dashboard data and emits machine-readable filters with:
  - n / WR / PF / expectancy gate failures
  - concentration and readiness blocks
  - walk-forward worst-fold sanity check
  - quarter-Kelly size from alpha_engine.kelly_position_sizer
  - PERFORMANCE_CHARTER swing cap of 1% per trade

Usage:
    python tools/filter_generator.py
    python tools/filter_generator.py --asset-class EQUITY
    python tools/filter_generator.py --output reports/strict_filters.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpha_engine.kelly_position_sizer import compute_position_size  # noqa: E402


DEFAULT_DASHBOARD_PATH = ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
DEFAULT_CLASSES = ("EQUITY", "COMMODITY", "ETF", "CRYPTO", "FOREX", "BOND", "FUTURES")

MIN_RESOLVED_N = 100
MIN_WIN_RATE = 50.0
MIN_PROFIT_FACTOR = 1.5
MIN_WORST_FOLD_WR = 40.0
SWING_POSITION_CAP_PCT = 1.0


def _parse_dashboard_timestamp(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _dashboard_age_hours(generated_at: str | None) -> float | None:
    parsed = _parse_dashboard_timestamp(generated_at)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - parsed).total_seconds() / 3600.0


def _kelly_size_usd(
    asset_class: str,
    class_metrics: dict[str, Any],
    performance_metrics: dict[str, Any],
    portfolio_value: float,
) -> tuple[float, dict[str, Any]]:
    win_rate = float(class_metrics.get("win_rate") or 0.0) / 100.0
    stats = {
        "win_rate": win_rate,
        "avg_win_pct": float(performance_metrics.get("avg_win") or 0.0),
        "avg_loss_pct": float(performance_metrics.get("avg_loss") or 0.0),
    }
    pick = {
        "symbol": asset_class,
        "asset_class": asset_class,
        "extra": {"rolling_dd_30d": 0.0},
    }
    size_usd = compute_position_size(
        pick,
        stats,
        portfolio_value=portfolio_value,
        fraction=0.25,
    )
    details = {
        key: pick.get(key)
        for key in ("kelly_f", "kelly_size_pct", "kelly_size_usdc", "kelly_edge", "kelly_method")
        if key in pick
    }
    return float(size_usd or 0.0), details


def evaluate_asset_class(
    asset_class: str,
    dashboard: dict[str, Any],
    portfolio_value: float = 10_000.0,
) -> dict[str, Any]:
    performance = dashboard.get("performance") or {}
    health = (performance.get("asset_class_health") or {}).get(asset_class) or {}
    by_class = (performance.get("by_asset_class") or {}).get(asset_class) or {}
    concentration = (performance.get("asset_class_concentration") or {}).get(asset_class) or {}
    walkforward = ((dashboard.get("walkforward") or {}).get("by_class") or {}).get(asset_class) or {}
    readiness = ((dashboard.get("readiness") or {}).get("by_class") or {}).get(asset_class) or {}

    resolved_n = int(health.get("resolved_n") or health.get("n") or 0)
    win_rate = health.get("win_rate")
    profit_factor = health.get("profit_factor")
    expectancy = by_class.get("expectancy")
    concentration_tier = concentration.get("tier")
    readiness_sizing_allowed = readiness.get("sizing_allowed")
    worst_fold_wr = walkforward.get("worst_fold_wr")

    failures: list[str] = []
    if resolved_n < MIN_RESOLVED_N:
        failures.append("n<100")
    if profit_factor is None or float(profit_factor) < MIN_PROFIT_FACTOR:
        failures.append("PF<1.5")
    if win_rate is None or float(win_rate) < MIN_WIN_RATE:
        failures.append("WR<50")
    if expectancy is None or float(expectancy) <= 0.0:
        failures.append("expectancy<=0")
    if concentration_tier in ("WARN", "BLOCK"):
        failures.append(f"concentration_{concentration_tier}")
    if readiness_sizing_allowed is False:
        failures.append("readiness_sizing_blocked")
    if worst_fold_wr is not None and float(worst_fold_wr) < MIN_WORST_FOLD_WR:
        failures.append("bad_worst_fold")

    kelly_usd, kelly_details = _kelly_size_usd(asset_class, health, by_class, portfolio_value)
    charter_cap_usd = portfolio_value * SWING_POSITION_CAP_PCT / 100.0
    operational_usd = 0.0 if failures else min(kelly_usd, charter_cap_usd)

    return {
        "asset_class": asset_class,
        "verdict": "FILTER_READY_SMALL_SIZE" if not failures else "RESEARCH_ONLY",
        "failures": failures,
        "filter": {
            "asset_class": asset_class,
            "status": "OPEN",
            "preferred_strategy": concentration.get("top_strategy") if not failures else None,
            "max_position_pct": round((operational_usd / portfolio_value) * 100.0, 4),
            "max_position_usd": round(operational_usd, 2),
        },
        "metrics": {
            "resolved_n": resolved_n,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "total_pnl_pct": health.get("total_pnl_pct"),
            "avg_win": by_class.get("avg_win"),
            "avg_loss": by_class.get("avg_loss"),
        },
        "kelly": {
            "portfolio_value": portfolio_value,
            "quarter_kelly_usd": round(kelly_usd, 2),
            "quarter_kelly_pct": round((kelly_usd / portfolio_value) * 100.0, 4),
            "charter_cap_pct": SWING_POSITION_CAP_PCT,
            "operational_usd": round(operational_usd, 2),
            "details": kelly_details,
        },
        "readiness": {
            "gate_state": readiness.get("gate_state"),
            "tier_vs_charter": readiness.get("tier_vs_charter"),
            "sizing_allowed": readiness_sizing_allowed,
        },
        "concentration": {
            "tier": concentration_tier,
            "top_strategy": concentration.get("top_strategy"),
            "top_symbol": concentration.get("top_symbol"),
            "top_share_pct": concentration.get("top_share_pct"),
            "honest_label": concentration.get("honest_label"),
        },
        "walkforward": {
            "oos_wr": walkforward.get("oos_wr"),
            "oos_sharpe": walkforward.get("oos_sharpe"),
            "worst_fold_wr": worst_fold_wr,
            "folds": walkforward.get("folds"),
        },
    }


def generate_filters(
    dashboard_path: Path = DEFAULT_DASHBOARD_PATH,
    asset_class: str | None = None,
    portfolio_value: float = 10_000.0,
) -> dict[str, Any]:
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    generated_at = dashboard.get("generated_at")
    classes = [asset_class.upper()] if asset_class else list(DEFAULT_CLASSES)

    filters = [
        evaluate_asset_class(cls, dashboard, portfolio_value=portfolio_value)
        for cls in classes
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": str(dashboard_path.relative_to(ROOT) if dashboard_path.is_relative_to(ROOT) else dashboard_path),
        "source_generated_at": generated_at,
        "source_age_hours": _dashboard_age_hours(generated_at),
        "portfolio_value": portfolio_value,
        "gates": {
            "min_resolved_n": MIN_RESOLVED_N,
            "min_win_rate": MIN_WIN_RATE,
            "min_profit_factor": MIN_PROFIT_FACTOR,
            "min_worst_fold_wr": MIN_WORST_FOLD_WR,
            "swing_position_cap_pct": SWING_POSITION_CAP_PCT,
        },
        "filters": filters,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dashboard", default=str(DEFAULT_DASHBOARD_PATH), help="Path to dashboard_data.json")
    parser.add_argument("--asset-class", help="Limit output to one asset class, e.g. EQUITY")
    parser.add_argument("--portfolio-value", type=float, default=10_000.0, help="Account value for Kelly sizing")
    parser.add_argument("--output", help="Optional output JSON path")
    args = parser.parse_args(argv)

    payload = generate_filters(
        dashboard_path=Path(args.dashboard),
        asset_class=args.asset_class,
        portfolio_value=args.portfolio_value,
    )

    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
        print(f"Wrote {output_path}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
