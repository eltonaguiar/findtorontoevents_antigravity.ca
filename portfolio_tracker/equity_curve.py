"""
Portfolio Equity Curve Builder
Aggregates closed picks across all trading systems, builds cumulative PnL,
and computes portfolio-level and per-system risk metrics.
"""

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent

# All systems to aggregate, keyed by display name -> relative path to closed_picks.json
SYSTEM_SOURCES: dict[str, Path] = {
    "mercury2": Path("mercury2/data/closed_picks.json"),
    "alpha_engine": Path("alpha_engine/data/closed_picks.json"),
    "kimi_riseoftheclaw": Path("KIMI_RISEOFTHECLAW/data/closed_picks.json"),
    "crypto_signal_engine": Path("crypto_signal_engine/data/closed_picks.json"),
    "crypto_ml_edge": Path("crypto_ml_edge/data/closed_picks.json"),
    "system_a_filter": Path("ml_battleground/system_a_filter/data/closed_picks.json"),
    "system_b_regime": Path("ml_battleground/system_b_regime/data/closed_picks.json"),
    "system_d_carry": Path("ml_battleground/system_d_carry/data/closed_picks.json"),
    "system_e_momentum": Path("ml_battleground/system_e_momentum/data/closed_picks.json"),
    "claude_gainer_ml": Path("claude_gainer_ml/tracker/closed_picks.json"),
}

DATA_DIR = Path(__file__).resolve().parent / "data"


def _parse_exit_time(pick: dict[str, Any]) -> datetime | None:
    """Extract exit timestamp from a closed pick, trying multiple field names."""
    for field in ("exit_time", "exit_time_est", "closed_at", "exit_date", "last_checked"):
        val = pick.get(field)
        if not val:
            continue
        if isinstance(val, (int, float)):
            try:
                return datetime.fromtimestamp(val, tz=timezone.utc)
            except (OSError, ValueError):
                continue
        if isinstance(val, str):
            # Try ISO format first, then common formats
            for fmt in (
                None,  # sentinel for fromisoformat
                "%Y-%m-%d %H:%M:%S %Z",
                "%Y-%m-%d %I:%M %p %Z",
                "%Y-%m-%d %H:%M:%S %z",
                "%Y-%m-%d",
            ):
                try:
                    if fmt is None:
                        dt = datetime.fromisoformat(val)
                    else:
                        dt = datetime.strptime(val, fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except (ValueError, TypeError):
                    continue
            # Handle "EST" suffix manually (Python strptime doesn't know EST)
            for suffix, offset_h in ((" EST", -5), (" EDT", -4), (" UTC", 0)):
                if val.endswith(suffix):
                    clean = val[: -len(suffix)]
                    for fmt2 in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %I:%M %p"):
                        try:
                            from datetime import timedelta
                            dt = datetime.strptime(clean, fmt2)
                            dt = dt.replace(tzinfo=timezone(timedelta(hours=offset_h)))
                            return dt
                        except ValueError:
                            continue
    return None


def _extract_pnl_pct(pick: dict[str, Any]) -> float | None:
    """Extract PnL percentage from a closed pick, trying multiple field names."""
    for field in ("net_pnl_pct", "pnl_pct", "realized_pnl_pct", "gross_pnl_pct"):
        val = pick.get(field)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                continue
    return None


def load_all_closed_picks() -> list[dict[str, Any]]:
    """Load and normalize closed picks from all systems."""
    all_trades: list[dict[str, Any]] = []

    for system_name, rel_path in SYSTEM_SOURCES.items():
        full_path = REPO_ROOT / rel_path
        if not full_path.exists():
            logger.warning("Skipping %s: file not found at %s", system_name, full_path)
            continue
        try:
            raw = json.loads(full_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Skipping %s: failed to read %s (%s)", system_name, full_path, exc)
            continue

        if not isinstance(raw, list):
            logger.warning("Skipping %s: expected list, got %s", system_name, type(raw).__name__)
            continue

        if not raw:
            logger.info("Skipping %s: empty closed picks", system_name)
            continue

        loaded = 0
        for pick in raw:
            pnl = _extract_pnl_pct(pick)
            exit_dt = _parse_exit_time(pick)
            if pnl is None or exit_dt is None:
                continue
            all_trades.append({
                "system": system_name,
                "symbol": pick.get("symbol", "UNKNOWN"),
                "pnl_pct": pnl,
                "exit_time": exit_dt,
            })
            loaded += 1

        logger.info("Loaded %d/%d closed trades from %s", loaded, len(raw), system_name)

    # Sort by exit time
    all_trades.sort(key=lambda t: t["exit_time"])
    return all_trades


def compute_sharpe(returns: np.ndarray, annualization: float = 365.0) -> float:
    """Annualized Sharpe ratio from an array of trade returns (as fractions, e.g. 0.05 = 5%)."""
    if len(returns) < 2:
        return 0.0
    mean_r = float(np.mean(returns))
    std_r = float(np.std(returns, ddof=1))
    if std_r < 1e-12:
        return 0.0
    # Annualize assuming ~1 trade per day on average; use sqrt(N) scaling
    return (mean_r / std_r) * math.sqrt(annualization)


def compute_max_drawdown(cumulative_pnl: np.ndarray) -> float:
    """Max drawdown as a positive percentage from peak-to-trough on cumulative PnL series."""
    if len(cumulative_pnl) == 0:
        return 0.0
    # Treat cumulative_pnl as an equity curve starting at 100
    equity = 100.0 + cumulative_pnl
    peak = np.maximum.accumulate(equity)
    drawdown = (peak - equity) / np.where(peak > 0, peak, 1.0) * 100.0
    return float(np.max(drawdown))


def compute_rolling_sharpe(returns: np.ndarray, window: int = 20) -> float:
    """Most recent rolling Sharpe over `window` trades."""
    if len(returns) < window:
        return compute_sharpe(returns)
    recent = returns[-window:]
    return compute_sharpe(recent)


def softmax_weights(sharpes: dict[str, float]) -> dict[str, float]:
    """Compute system weights as softmax(max(sharpe, 0) ** 2)."""
    scores = {k: max(v, 0.0) ** 2 for k, v in sharpes.items()}
    total = sum(scores.values())
    if total < 1e-12:
        # Equal weight if all systems have non-positive Sharpe
        n = len(sharpes)
        return {k: 1.0 / n for k in sharpes} if n > 0 else {}
    return {k: v / total for k, v in scores.items()}


def build_portfolio_metrics() -> dict[str, Any]:
    """Main computation: load all trades, compute metrics, return structured dict."""
    trades = load_all_closed_picks()

    if not trades:
        logger.warning("No closed trades found across any system.")
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "portfolio": {
                "sharpe": 0.0, "rolling_sharpe_20": 0.0, "max_dd_pct": 0.0,
                "calmar": 0.0, "total_trades": 0, "total_pnl_pct": 0.0,
            },
            "systems": {},
            "system_weights": {},
        }

    # Portfolio-level
    all_returns = np.array([t["pnl_pct"] / 100.0 for t in trades])
    cumulative_pnl = np.cumsum(np.array([t["pnl_pct"] for t in trades]))

    portfolio_sharpe = compute_sharpe(all_returns)
    rolling_sharpe = compute_rolling_sharpe(all_returns, 20)
    max_dd = compute_max_drawdown(cumulative_pnl)
    total_pnl = float(cumulative_pnl[-1]) if len(cumulative_pnl) > 0 else 0.0

    # Calmar: annualized return / max DD
    if len(trades) >= 2:
        first_exit = trades[0]["exit_time"]
        last_exit = trades[-1]["exit_time"]
        span_days = max((last_exit - first_exit).total_seconds() / 86400.0, 1.0)
        annualized_return = total_pnl * (365.0 / span_days)
    else:
        annualized_return = total_pnl
    calmar = annualized_return / max_dd if max_dd > 1e-6 else 0.0

    # Per-system metrics
    system_trades: dict[str, list[dict]] = {}
    for t in trades:
        system_trades.setdefault(t["system"], []).append(t)

    systems_metrics: dict[str, dict[str, Any]] = {}
    system_sharpes: dict[str, float] = {}

    for sys_name, sys_trades_list in system_trades.items():
        sys_returns = np.array([t["pnl_pct"] / 100.0 for t in sys_trades_list])
        sys_cum_pnl = np.cumsum(np.array([t["pnl_pct"] for t in sys_trades_list]))
        sys_sharpe = compute_sharpe(sys_returns)
        sys_max_dd = compute_max_drawdown(sys_cum_pnl)
        sys_total_pnl = float(sys_cum_pnl[-1])
        wins = sum(1 for t in sys_trades_list if t["pnl_pct"] > 0)
        win_rate = wins / len(sys_trades_list) if sys_trades_list else 0.0

        systems_metrics[sys_name] = {
            "sharpe": round(sys_sharpe, 4),
            "win_rate": round(win_rate, 4),
            "max_dd": round(sys_max_dd, 4),
            "total_pnl": round(sys_total_pnl, 4),
            "closed_trades": len(sys_trades_list),
        }
        system_sharpes[sys_name] = sys_sharpe

    # Correlation matrix between systems (using trade-by-trade returns per day)
    # Group returns by (system, date) and compute pairwise correlations
    # This is a simplified approach: bucket by date, compute daily return per system
    from collections import defaultdict
    daily_returns: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for t in trades:
        date_key = t["exit_time"].strftime("%Y-%m-%d")
        daily_returns[date_key][t["system"]] += t["pnl_pct"]

    sys_names_sorted = sorted(system_trades.keys())
    dates_sorted = sorted(daily_returns.keys())

    if len(dates_sorted) >= 5 and len(sys_names_sorted) >= 2:
        # Build matrix: rows=dates, cols=systems
        matrix = np.zeros((len(dates_sorted), len(sys_names_sorted)))
        for i, d in enumerate(dates_sorted):
            for j, s in enumerate(sys_names_sorted):
                matrix[i, j] = daily_returns[d].get(s, 0.0)
        # Compute correlation matrix
        corr = np.corrcoef(matrix.T)
        correlation_matrix = {
            s1: {s2: round(float(corr[i, j]), 4) for j, s2 in enumerate(sys_names_sorted)}
            for i, s1 in enumerate(sys_names_sorted)
        }
    else:
        correlation_matrix = {}

    weights = softmax_weights(system_sharpes)

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "portfolio": {
            "sharpe": round(portfolio_sharpe, 4),
            "rolling_sharpe_20": round(rolling_sharpe, 4),
            "max_dd_pct": round(max_dd, 4),
            "calmar": round(calmar, 4),
            "total_trades": len(trades),
            "total_pnl_pct": round(total_pnl, 4),
        },
        "systems": systems_metrics,
        "system_weights": {k: round(v, 4) for k, v in weights.items()},
    }

    if correlation_matrix:
        result["correlation_matrix"] = correlation_matrix

    return result


def save_metrics(metrics: dict[str, Any]) -> Path:
    """Write metrics to portfolio_tracker/data/portfolio_metrics.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / "portfolio_metrics.json"
    out_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    logger.info("Saved portfolio metrics to %s", out_path)
    return out_path


def print_report(metrics: dict[str, Any]) -> None:
    """Print a formatted portfolio report to stdout."""
    p = metrics["portfolio"]
    print("=" * 70)
    print("  PORTFOLIO EQUITY CURVE REPORT")
    print("=" * 70)
    print(f"  Timestamp:         {metrics['timestamp']}")
    print(f"  Total Trades:      {p['total_trades']}")
    print(f"  Total PnL:         {p['total_pnl_pct']:+.2f}%")
    print(f"  Sharpe Ratio:      {p['sharpe']:.4f}")
    print(f"  Rolling Sharpe(20):{p['rolling_sharpe_20']:.4f}")
    print(f"  Max Drawdown:      {p['max_dd_pct']:.2f}%")
    print(f"  Calmar Ratio:      {p['calmar']:.4f}")
    print()

    systems = metrics.get("systems", {})
    weights = metrics.get("system_weights", {})
    if systems:
        print("  PER-SYSTEM BREAKDOWN")
        print("  " + "-" * 66)
        header = f"  {'System':<22} {'Sharpe':>8} {'WR':>7} {'MaxDD':>8} {'PnL%':>9} {'Trades':>7} {'Wt':>6}"
        print(header)
        print("  " + "-" * 66)
        for name in sorted(systems.keys()):
            s = systems[name]
            w = weights.get(name, 0.0)
            print(
                f"  {name:<22} {s['sharpe']:>8.3f} {s['win_rate']*100:>6.1f}% "
                f"{s['max_dd']:>7.2f}% {s['total_pnl']:>+8.2f}% {s['closed_trades']:>6d} {w:>5.1%}"
            )
        print("  " + "-" * 66)

    corr = metrics.get("correlation_matrix")
    if corr:
        print()
        print("  CORRELATION MATRIX")
        sys_list = sorted(corr.keys())
        # Header
        short = {s: s[:10] for s in sys_list}
        print("  " + " " * 14 + "  ".join(f"{short[s]:>10}" for s in sys_list))
        for s1 in sys_list:
            row = "  ".join(f"{corr[s1].get(s2, 0.0):>10.3f}" for s2 in sys_list)
            print(f"  {short[s1]:<14}{row}")

    print()
    print("=" * 70)


def main() -> None:
    """Run standalone: build metrics, save, and print report."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    metrics = build_portfolio_metrics()
    save_metrics(metrics)
    print_report(metrics)


if __name__ == "__main__":
    main()
