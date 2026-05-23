"""Track Record Generator -- creates honest, transparent performance reports.

Outputs JSON with: overall P/L (no cherry-picking), per-strategy breakdown
with p-values, win/loss streaks, drawdown history, monthly returns.
"""
import json
import math
from datetime import datetime
from collections import defaultdict


def generate_track_record(closed_picks_path: str, performance_path: str) -> dict:
    """Generate transparent track record from closed picks data."""
    with open(closed_picks_path) as f:
        closed = json.load(f)
    with open(performance_path) as f:
        perf = json.load(f)

    if not closed:
        return {"error": "No closed trades", "generated_at": datetime.utcnow().isoformat()}

    total_trades = len(closed)
    wins = sum(1 for p in closed if float(p.get("pnl_pct", 0) or 0) > 0)
    losses = total_trades - wins
    total_pnl_pct = sum(float(p.get("pnl_pct", 0) or 0) for p in closed)
    total_pnl_dollar = sum(float(p.get("pnl_dollar", 0) or 0) for p in closed)

    pnls = [float(p.get("pnl_pct", 0) or 0) for p in closed]
    avg_win = sum(p for p in pnls if p > 0) / max(wins, 1)
    avg_loss = sum(p for p in pnls if p <= 0) / max(losses, 1)

    p_value = _binomial_p_value(wins, total_trades)

    # Drawdown
    equity_curve = [0.0]
    for pnl in pnls:
        equity_curve.append(equity_curve[-1] + pnl)
    peak = equity_curve[0]
    max_dd = 0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = (val - peak) / max(abs(peak), 0.01)
        if dd < max_dd:
            max_dd = dd

    # Monthly returns
    monthly = defaultdict(lambda: {"trades": 0, "pnl_pct": 0, "wins": 0})
    for p in closed:
        exit_time = p.get("exit_time") or p.get("closed_at", "")
        if exit_time:
            month_key = exit_time[:7]
            monthly[month_key]["trades"] += 1
            monthly[month_key]["pnl_pct"] += float(p.get("pnl_pct", 0) or 0)
            if float(p.get("pnl_pct", 0) or 0) > 0:
                monthly[month_key]["wins"] += 1

    # Strategy breakdown
    strategy_summary = []
    for strat_name, data in sorted(perf.items(), key=lambda x: x[1].get("total_pnl_dollar", 0), reverse=True):
        if data.get("closed_picks", 0) == 0:
            continue
        s_wins = data.get("wins", 0)
        s_total = data.get("closed_picks", 0)
        strategy_summary.append({
            "strategy": strat_name,
            "trades": s_total,
            "win_rate": data.get("win_rate", 0),
            "pnl_dollar": data.get("total_pnl_dollar", 0),
            "sharpe": data.get("sharpe", 0),
            "p_value": _binomial_p_value(s_wins, s_total),
            "status": "PROVEN" if _binomial_p_value(s_wins, s_total) < 0.05 and s_total >= 10 else
                      "PROMISING" if data.get("total_pnl_dollar", 0) > 0 else
                      "LOSING",
        })

    # Win/loss streaks
    current_streak = 0
    max_win_streak = 0
    max_loss_streak = 0
    for pnl in pnls:
        if pnl > 0:
            current_streak = current_streak + 1 if current_streak > 0 else 1
            max_win_streak = max(max_win_streak, current_streak)
        else:
            current_streak = current_streak - 1 if current_streak < 0 else -1
            max_loss_streak = max(max_loss_streak, abs(current_streak))

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "disclaimer": "Past performance does not guarantee future results. All numbers are from live forward testing, not backtests.",
        "overall": {
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / total_trades, 4) if total_trades else 0,
            "win_rate_p_value": round(p_value, 4),
            "statistically_significant": p_value < 0.05,
            "total_pnl_pct": round(total_pnl_pct, 4),
            "total_pnl_dollar": round(total_pnl_dollar, 2),
            "avg_win_pct": round(avg_win, 4),
            "avg_loss_pct": round(avg_loss, 4),
            "profit_factor": round(abs(avg_win * wins) / abs(avg_loss * losses), 2) if losses and avg_loss else 0,
            "max_drawdown_pct": round(max_dd, 4),
            "max_win_streak": max_win_streak,
            "max_loss_streak": max_loss_streak,
        },
        "monthly_returns": dict(sorted(monthly.items())),
        "strategies": strategy_summary,
        "proven_count": sum(1 for s in strategy_summary if s["status"] == "PROVEN"),
        "losing_count": sum(1 for s in strategy_summary if s["status"] == "LOSING"),
    }


def _binomial_p_value(wins: int, total: int, null: float = 0.5) -> float:
    if total < 5:
        return 1.0
    rate = wins / total
    if rate <= null:
        return 1.0
    se = math.sqrt(null * (1 - null) / total)
    if se == 0:
        return 1.0
    z = (rate - null) / se
    return 0.5 * math.erfc(z / math.sqrt(2))


if __name__ == "__main__":
    import os
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    result = generate_track_record(
        os.path.join(data_dir, "closed_picks.json"),
        os.path.join(data_dir, "strategy_performance.json"),
    )
    output_path = os.path.join(data_dir, "track_record.json")
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Track record generated: {output_path}")
    print(f"Total trades: {result['overall']['total_trades']}")
    print(f"Win rate: {result['overall']['win_rate']*100:.1f}% (p={result['overall']['win_rate_p_value']:.4f})")
    print(f"Total P/L: ${result['overall']['total_pnl_dollar']:+,.2f}")
    print(f"Proven strategies: {result['proven_count']}")
    print(f"Losing strategies: {result['losing_count']}")
