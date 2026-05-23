"""Shared formatting helpers for Discord pick embeds."""


def format_strategy_stats(name: str, stats: dict) -> str:
    """Format strategy stats as a compact one-liner for Discord embeds.

    Args:
        name: Strategy name (e.g., 'coinglass_leverage_squeeze')
        stats: Dict with keys: total, wins, losses, win_rate, avg_pnl, profit_factor
    """
    if not stats or stats.get("total", 0) == 0:
        return f"`{name}`: 0 trades — tracking started"
    wins = stats.get("wins", 0)
    losses = stats.get("losses", 0)
    wr = stats.get("win_rate", 0)
    pf = stats.get("profit_factor", "--")
    avg = stats.get("avg_pnl", 0)
    if isinstance(pf, (int, float)) and pf != float("inf"):
        pf_str = f"{pf:.2f}"
    else:
        pf_str = str(pf)
    return (
        f"`{name}`: {wins}W/{losses}L "
        f"({wr:.0f}% WR) | PF: {pf_str} | Avg: {avg:+.2f}%"
    )


def format_symbol_history(symbol: str, direction: str, wins: int, losses: int) -> str:
    """Format symbol+direction history as a compact string."""
    total = wins + losses
    if total == 0:
        return ""
    wr = wins / total * 100
    return f"{symbol} {direction}s: {wins}W/{losses}L ({wr:.0f}%)"


def format_confidence_breakdown(breakdown: dict) -> str:
    """Format confidence breakdown as a human-readable one-liner.

    Args:
        breakdown: Dict with keys: base, wr_boost, sharpe_boost, consensus, playbook, final
    """
    if not breakdown:
        return ""
    parts = [f"Base: {breakdown.get('base', 0):.0f}%"]
    if breakdown.get("consensus", 0) > 0:
        parts.append(f"+{breakdown['consensus']:.0f}% consensus")
    if breakdown.get("wr_boost", 0) > 0:
        parts.append(f"+{breakdown['wr_boost']:.0f}% WR")
    if breakdown.get("sharpe_boost", 0) > 0:
        parts.append(f"+{breakdown['sharpe_boost']:.0f}% Sharpe")
    if breakdown.get("playbook", 0) > 0:
        parts.append(f"+{breakdown['playbook']:.0f}% playbook")
    final = breakdown.get("final", 0)
    return " → ".join(parts) + f" = **{final:.0f}%**"


def format_per_system_stats(source_systems: list, source_strategies: dict,
                            system_wrs: dict, max_display: int = 5) -> str:
    """Format per-system strategy stats for Discord embed.

    Args:
        source_systems: List of system names that agree on this pick
        source_strategies: Dict mapping system_name -> strategy_name
        system_wrs: Dict mapping system_name -> rolling win rate (0-100)
        max_display: Max systems to show before truncating
    """
    lines = []
    unique = sorted(set(source_systems))
    for sys in unique[:max_display]:
        strat = source_strategies.get(sys, "unknown")
        wr = system_wrs.get(sys)
        wr_str = f"{wr:.0f}% WR" if wr is not None else "new"
        lines.append(f"`{sys}` \u2192 {strat} ({wr_str})")
    if len(unique) > max_display:
        lines.append(f"+ {len(unique) - max_display} more")
    return "\n".join(lines) if lines else "N/A"
