"""
Sharpe-based Capital Allocator
Reads portfolio_metrics.json and outputs risk-parity inspired system allocations
with minimum/maximum weight constraints.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "data"
METRICS_PATH = DATA_DIR / "portfolio_metrics.json"
ALLOCATIONS_PATH = DATA_DIR / "system_allocations.json"

MIN_WEIGHT = 0.05
MAX_WEIGHT = 0.50


def load_metrics() -> dict[str, Any]:
    """Load portfolio_metrics.json."""
    if not METRICS_PATH.exists():
        raise FileNotFoundError(
            f"Portfolio metrics not found at {METRICS_PATH}. "
            "Run equity_curve.py first to generate metrics."
        )
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))


def compute_allocations(metrics: dict[str, Any]) -> dict[str, Any]:
    """
    Compute capital allocations using Sharpe-squared risk-parity weights.

    Formula: weight_i = max(sharpe_i, 0) ** 2 / sum(max(sharpe_j, 0) ** 2)
    Then clamp to [MIN_WEIGHT, MAX_WEIGHT] and renormalize.
    """
    systems = metrics.get("systems", {})
    if not systems:
        return {"allocations": {}, "timestamp": metrics.get("timestamp", "")}

    # Extract Sharpe ratios for active systems (those with closed trades)
    active_systems = {
        name: data["sharpe"]
        for name, data in systems.items()
        if data.get("closed_trades", 0) > 0
    }

    if not active_systems:
        return {"allocations": {}, "timestamp": metrics.get("timestamp", "")}

    # Compute raw scores: max(sharpe, 0) ** 2
    scores = {name: max(sharpe, 0.0) ** 2 for name, sharpe in active_systems.items()}
    total_score = sum(scores.values())

    if total_score < 1e-12:
        # All systems have non-positive Sharpe -- equal weight
        n = len(active_systems)
        raw_weights = {name: 1.0 / n for name in active_systems}
    else:
        raw_weights = {name: score / total_score for name, score in scores.items()}

    # Clamp and renormalize iteratively until stable
    weights = dict(raw_weights)
    for _ in range(20):  # convergence loop
        clamped = {
            name: max(MIN_WEIGHT, min(MAX_WEIGHT, w))
            for name, w in weights.items()
        }
        total = sum(clamped.values())
        if total < 1e-12:
            break
        weights = {name: w / total for name, w in clamped.items()}

        # Check if all within bounds
        all_ok = all(
            MIN_WEIGHT - 1e-6 <= w <= MAX_WEIGHT + 1e-6
            for w in weights.values()
        )
        if all_ok:
            break

    # Round for readability
    allocations = {name: round(w, 4) for name, w in sorted(weights.items())}

    return {
        "timestamp": metrics.get("timestamp", ""),
        "min_weight": MIN_WEIGHT,
        "max_weight": MAX_WEIGHT,
        "method": "sharpe_squared_risk_parity",
        "allocations": allocations,
        "raw_scores": {name: round(s, 6) for name, s in sorted(scores.items())},
        "active_systems": len(active_systems),
    }


def save_allocations(alloc: dict[str, Any]) -> Path:
    """Write allocations to portfolio_tracker/data/system_allocations.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ALLOCATIONS_PATH.write_text(json.dumps(alloc, indent=2), encoding="utf-8")
    logger.info("Saved system allocations to %s", ALLOCATIONS_PATH)
    return ALLOCATIONS_PATH


def get_system_weight(system_name: str) -> float:
    """
    Get the current allocation weight for a system.
    Returns the weight from the latest allocations file, or 0.0 if not found.
    Other modules can import and call this function.
    """
    if not ALLOCATIONS_PATH.exists():
        logger.warning("Allocations file not found. Run sharpe_allocator.py first.")
        return 0.0
    try:
        data = json.loads(ALLOCATIONS_PATH.read_text(encoding="utf-8"))
        return float(data.get("allocations", {}).get(system_name, 0.0))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read allocations: %s", exc)
        return 0.0


def print_allocations(alloc: dict[str, Any]) -> None:
    """Print a formatted allocation report."""
    print("=" * 50)
    print("  CAPITAL ALLOCATION (Sharpe-Squared Risk Parity)")
    print("=" * 50)
    print(f"  Method:          {alloc.get('method', 'N/A')}")
    print(f"  Active Systems:  {alloc.get('active_systems', 0)}")
    print(f"  Weight Bounds:   [{alloc.get('min_weight', MIN_WEIGHT):.0%}, {alloc.get('max_weight', MAX_WEIGHT):.0%}]")
    print()

    allocations = alloc.get("allocations", {})
    raw_scores = alloc.get("raw_scores", {})
    if allocations:
        print(f"  {'System':<22} {'Weight':>8} {'Raw Score':>12}")
        print("  " + "-" * 44)
        for name in sorted(allocations.keys()):
            w = allocations[name]
            s = raw_scores.get(name, 0.0)
            print(f"  {name:<22} {w:>7.1%} {s:>12.6f}")
        print("  " + "-" * 44)
        total = sum(allocations.values())
        print(f"  {'TOTAL':<22} {total:>7.1%}")
    else:
        print("  No active systems with positive Sharpe ratios.")

    print("=" * 50)


def main() -> None:
    """Run standalone: load metrics, compute allocations, save, print."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    metrics = load_metrics()
    alloc = compute_allocations(metrics)
    save_allocations(alloc)
    print_allocations(alloc)


if __name__ == "__main__":
    main()
