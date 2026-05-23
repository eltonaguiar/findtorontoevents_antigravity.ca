"""Incubator promotion system — evaluates incubator strategies for promotion to verified."""
import json
import logging
import pathlib
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List

logger = logging.getLogger("paper_trading")

DATA_DIR = pathlib.Path(__file__).parent / "data"

# Promotion thresholds
MIN_CLOSED_TRADES = 10
MIN_WIN_RATE = 0.55          # 55%
MIN_AVG_PNL = 0.0            # must be positive
MIN_PROFIT_FACTOR = 1.3      # gross wins / gross losses
MAX_WORST_TRADE = -8.0       # worst single trade P&L% floor


def _load_closed_picks() -> List[dict]:
    """Load closed picks from the data directory."""
    path = DATA_DIR / "closed_picks.json"
    if not path.exists():
        logger.warning("closed_picks.json not found at %s", path)
        return []
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load closed_picks.json: %s", e)
        return []


def _group_by_strategy(picks: List[dict]) -> Dict[str, List[dict]]:
    """Group closed picks by strategy name, keeping only incubator portfolio picks."""
    groups = defaultdict(list)
    for pick in picks:
        if pick.get("portfolio_type") == "incubator":
            groups[pick["strategy"]].append(pick)
    return dict(groups)


def _evaluate_strategy(strategy_name: str, trades: List[dict]) -> dict:
    """Evaluate a single incubator strategy against promotion criteria.

    Returns a dict with evaluation results:
        strategy, trade_count, win_rate, avg_pnl, profit_factor,
        worst_trade, meets_criteria, status, reasons
    """
    trade_count = len(trades)
    result = {
        "strategy": strategy_name,
        "trade_count": trade_count,
        "win_rate": 0.0,
        "avg_pnl": 0.0,
        "profit_factor": 0.0,
        "worst_trade": 0.0,
        "total_pnl_usd": 0.0,
        "meets_criteria": False,
        "status": "needs_data",
        "reasons": [],
    }

    if trade_count < MIN_CLOSED_TRADES:
        result["reasons"].append(
            f"Only {trade_count}/{MIN_CLOSED_TRADES} trades completed"
        )
        return result

    # Calculate metrics
    wins = [t for t in trades if t.get("pnl_pct", 0) > 0]
    losses = [t for t in trades if t.get("pnl_pct", 0) <= 0]
    pnl_values = [t.get("pnl_pct", 0) for t in trades]
    pnl_usd_values = [t.get("pnl_usd", 0) for t in trades]

    win_rate = len(wins) / trade_count
    avg_pnl = sum(pnl_values) / trade_count
    worst_trade = min(pnl_values)
    total_pnl_usd = sum(pnl_usd_values)

    gross_wins = sum(t.get("pnl_pct", 0) for t in wins) if wins else 0
    gross_losses = abs(sum(t.get("pnl_pct", 0) for t in losses)) if losses else 0
    profit_factor = (gross_wins / gross_losses) if gross_losses > 0 else float("inf")

    result.update({
        "win_rate": round(win_rate, 4),
        "avg_pnl": round(avg_pnl, 4),
        "profit_factor": round(profit_factor, 3),
        "worst_trade": round(worst_trade, 3),
        "total_pnl_usd": round(total_pnl_usd, 2),
    })

    # Check each criterion
    failures = []
    if win_rate < MIN_WIN_RATE:
        failures.append(f"Win rate {win_rate:.1%} < {MIN_WIN_RATE:.0%}")
    if avg_pnl <= MIN_AVG_PNL:
        failures.append(f"Avg P&L {avg_pnl:.3f}% <= {MIN_AVG_PNL}%")
    if profit_factor < MIN_PROFIT_FACTOR:
        failures.append(f"Profit factor {profit_factor:.2f} < {MIN_PROFIT_FACTOR}")
    if worst_trade < MAX_WORST_TRADE:
        failures.append(f"Worst trade {worst_trade:.2f}% < {MAX_WORST_TRADE}% floor")

    if failures:
        result["status"] = "underperforming"
        result["reasons"] = failures
    else:
        result["status"] = "promoted"
        result["meets_criteria"] = True
        result["reasons"] = ["All promotion criteria met"]

    return result


def check_promotions() -> Dict[str, list]:
    """Evaluate all incubator strategies and return promotion results.

    Returns:
        {
            "promoted": [eval_dict, ...],
            "needs_data": [eval_dict, ...],
            "underperforming": [eval_dict, ...],
            "evaluated_at": ISO timestamp,
        }
    """
    picks = _load_closed_picks()
    groups = _group_by_strategy(picks)

    results = {"promoted": [], "needs_data": [], "underperforming": [],
               "evaluated_at": datetime.now(timezone.utc).isoformat()}

    if not groups:
        logger.info("No incubator strategy trades found in closed_picks.json")
        return results

    for strategy_name, trades in sorted(groups.items()):
        evaluation = _evaluate_strategy(strategy_name, trades)
        bucket = evaluation["status"]  # "promoted", "needs_data", or "underperforming"
        results[bucket].append(evaluation)

        # Log the result
        if bucket == "promoted":
            logger.info(
                "PROMOTED: %s — %d trades, WR %.1f%%, PF %.2f, avg P&L %.3f%%",
                strategy_name, evaluation["trade_count"],
                evaluation["win_rate"] * 100, evaluation["profit_factor"],
                evaluation["avg_pnl"],
            )
        elif bucket == "needs_data":
            logger.info(
                "NEEDS DATA: %s — %d/%d trades completed",
                strategy_name, evaluation["trade_count"], MIN_CLOSED_TRADES,
            )
        else:
            logger.info(
                "UNDERPERFORMING: %s — %s",
                strategy_name, "; ".join(evaluation["reasons"]),
            )

    promoted_count = len(results["promoted"])
    total = sum(len(v) for k, v in results.items() if k != "evaluated_at")
    logger.info(
        "Incubator promotion check complete: %d/%d strategies promoted, "
        "%d need data, %d underperforming",
        promoted_count, total,
        len(results["needs_data"]), len(results["underperforming"]),
    )

    return results


def get_incubator_report() -> dict:
    """Return a summary dict suitable for Discord reporting.

    Returns:
        {
            "title": str,
            "promoted": [{"name": str, "trades": int, "win_rate": str, ...}],
            "in_progress": [{"name": str, "trades": int, "needed": int}],
            "failing": [{"name": str, "trades": int, "issues": str}],
            "summary": str,
            "evaluated_at": str,
        }
    """
    results = check_promotions()

    report = {
        "title": "Incubator Promotion Report",
        "promoted": [],
        "in_progress": [],
        "failing": [],
        "summary": "",
        "evaluated_at": results["evaluated_at"],
    }

    for ev in results["promoted"]:
        report["promoted"].append({
            "name": ev["strategy"],
            "trades": ev["trade_count"],
            "win_rate": f"{ev['win_rate']:.1%}",
            "profit_factor": f"{ev['profit_factor']:.2f}",
            "avg_pnl": f"{ev['avg_pnl']:.3f}%",
            "total_pnl_usd": f"${ev['total_pnl_usd']:.2f}",
        })

    for ev in results["needs_data"]:
        report["in_progress"].append({
            "name": ev["strategy"],
            "trades": ev["trade_count"],
            "needed": MIN_CLOSED_TRADES - ev["trade_count"],
        })

    for ev in results["underperforming"]:
        report["failing"].append({
            "name": ev["strategy"],
            "trades": ev["trade_count"],
            "win_rate": f"{ev['win_rate']:.1%}",
            "profit_factor": f"{ev['profit_factor']:.2f}",
            "issues": "; ".join(ev["reasons"]),
        })

    total = len(report["promoted"]) + len(report["in_progress"]) + len(report["failing"])
    report["summary"] = (
        f"{len(report['promoted'])}/{total} strategies promoted | "
        f"{len(report['in_progress'])} gathering data | "
        f"{len(report['failing'])} underperforming"
    )

    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    results = check_promotions()
    print(json.dumps(results, indent=2))
