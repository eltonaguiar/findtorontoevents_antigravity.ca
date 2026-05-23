#!/usr/bin/env python3
"""
Pick Classifier — Routes picks to correct Discord channel tier
================================================================
Every pick gets classified before notification:

  ELITE    → #dna-master-picks + #fresh-picks  (3+ systems, all WR>=55%, historical edge>=60%)
  PROVEN   → #fresh-picks only                 (2+ systems, at least 1 WR>=55% with 5+ trades)
  EXPERIMENTAL → #sandbox                      (systems with <5 trades or WR<50%)
  INFORMATIONAL → #notifications               (status updates, summaries)

Usage:
    from cross_aggregation.pick_classifier import classify_pick, get_system_trust_badge
"""

import json
import pathlib
from typing import Dict, Optional, Tuple

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Closed picks paths per system (forward-tracked only)
CLOSED_PICKS_PATHS = {
    "mercury2":       "mercury2/data/closed_picks.json",
    "alpha_engine":   "alpha_engine/data/closed_picks.json",
    "claws_of_doom":  "ml_battleground/system_f_clawsofdoom/data/closed_picks.json",
    "ml_bg_a":        "ml_battleground/system_a_filter/data/closed_picks.json",
    "ml_bg_b":        "ml_battleground/system_b_regime/data/closed_picks.json",
    "ml_bg_d":        "ml_battleground/system_d_carry/data/closed_picks.json",
    "ml_bg_e":        "ml_battleground/system_e_momentum/data/closed_picks.json",
    "kimi":           "KIMI_RISEOFTHECLAW/data/closed_picks.json",
    "signal_engine":  "crypto_signal_engine/data/closed_picks.json",
}


def _load_system_forward_stats() -> Dict[str, Dict]:
    """Load forward performance stats for all systems from closed_picks files."""
    stats = {}
    for sys_name, rel_path in CLOSED_PICKS_PATHS.items():
        path = REPO_ROOT / rel_path
        if not path.exists():
            stats[sys_name] = {"trades": 0, "wins": 0, "losses": 0, "wr": 0, "pf": 0, "pnl": 0}
            continue
        try:
            closed = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(closed, list):
                closed = closed.get("picks", closed.get("closed", []))
            wins = 0
            losses = 0
            total_win_pnl = 0.0
            total_loss_pnl = 0.0
            for c in closed:
                status = str(c.get("status", "")).upper()
                exit_reason = str(c.get("exit_reason", "")).lower()
                pnl = c.get("pnl_pct", c.get("realized_pnl_pct", c.get("net_pnl_pct", 0)))
                if isinstance(pnl, (int, float)) and abs(pnl) < 1 and abs(pnl) > 0:
                    pnl = pnl * 100  # normalize to percent
                is_win = (status in ("WON", "WIN", "CLOSED_TP")
                          or exit_reason in ("take_profit", "tp_hit")
                          or (status not in ("LOST", "LOSS", "CLOSED_SL") and exit_reason not in ("stop_loss", "sl_hit") and pnl > 0))
                is_loss = (status in ("LOST", "LOSS", "CLOSED_SL")
                           or exit_reason in ("stop_loss", "sl_hit")
                           or (not is_win and pnl <= 0))
                if is_win:
                    wins += 1
                    total_win_pnl += abs(pnl)
                elif is_loss:
                    losses += 1
                    total_loss_pnl += abs(pnl)
            total = wins + losses
            wr = (wins / total * 100) if total else 0
            pf = (total_win_pnl / total_loss_pnl) if total_loss_pnl > 0 else (99.99 if total_win_pnl > 0 else 0)
            stats[sys_name] = {
                "trades": total,
                "wins": wins,
                "losses": losses,
                "wr": round(wr, 1),
                "pf": round(min(pf, 99.99), 2),
                "pnl": round(total_win_pnl - total_loss_pnl, 2),
            }
        except Exception:
            stats[sys_name] = {"trades": 0, "wins": 0, "losses": 0, "wr": 0, "pf": 0, "pnl": 0}
    return stats


# Cache system stats per run
_cached_stats: Optional[Dict] = None


def get_all_system_stats() -> Dict[str, Dict]:
    """Get forward performance stats for all systems (cached per process)."""
    global _cached_stats
    if _cached_stats is None:
        _cached_stats = _load_system_forward_stats()
    return _cached_stats


def get_system_trust_badge(system_name: str) -> Tuple[str, str]:
    """
    Returns (badge_emoji, badge_text) for a system based on forward WR.

    Returns:
        ("WINNER", "LOSER", "UNDETERMINED") with appropriate emoji
    """
    stats = get_all_system_stats()
    s = stats.get(system_name, {})
    trades = s.get("trades", 0)
    wr = s.get("wr", 0)
    pf = s.get("pf", 0)

    if trades < 5:
        return "\u2754", "UNDETERMINED"  # ❔
    elif wr >= 55 and pf >= 1.2:
        return "\u2705", "WINNER"  # ✅
    elif wr >= 50:
        return "\U0001f7e1", "MODERATE"  # 🟡
    else:
        return "\u274c", "LOSER"  # ❌


def get_system_stats_line(system_name: str) -> str:
    """One-line summary for embedding in Discord."""
    stats = get_all_system_stats()
    s = stats.get(system_name, {})
    trades = s.get("trades", 0)
    wr = s.get("wr", 0)
    pf = s.get("pf", 0)
    pnl = s.get("pnl", 0)
    emoji, badge = get_system_trust_badge(system_name)
    if trades == 0:
        return f"{emoji} **{badge}** | No forward trades"
    return f"{emoji} **{badge}** | WR: {wr:.0f}% | PF: {pf:.1f} | {trades} fwd trades | PnL: {pnl:+.1f}%"


def classify_pick(pick: Dict, system_stats: Optional[Dict] = None) -> str:
    """
    Classify a consensus pick into a tier for routing.

    Phase 1 update (Mar 16 2026): "PROVEN" now requires WR >= 55% AND 30+
    forward-validated trades (was 5+). "ELITE" requires 2+ systems meeting
    this stricter bar. This eliminates lucky small-sample systems from the
    proven tier.

    Args:
        pick: Aggregated consensus pick with source_systems, agreement_count, etc.
        system_stats: Optional pre-loaded system stats (otherwise loads from files)

    Returns:
        "ELITE" | "PROVEN" | "EXPERIMENTAL"
    """
    if system_stats is None:
        system_stats = get_all_system_stats()

    agreement = pick.get("agreement_count", 0)
    source_systems = pick.get("source_systems", [])
    confidence = pick.get("confidence", 0)

    # Get stats for all source systems
    source_stats = [system_stats.get(s, {}) for s in source_systems]
    source_wrs = [s.get("wr", 0) for s in source_stats]
    source_trades = [s.get("trades", 0) for s in source_stats]

    # Phase 1: Stricter "proven edge" definition — WR >= 55% AND 30+ forward trades
    # This ensures statistical significance, not just a lucky streak on 5 trades
    systems_with_proven_edge = sum(
        1 for s in source_stats
        if s.get("wr", 0) >= 55 and s.get("trades", 0) >= 30
    )
    # Softer "edge" for PROVEN tier — WR >= 55% AND 10+ trades (was 5+)
    systems_with_edge = sum(
        1 for s in source_stats
        if s.get("wr", 0) >= 55 and s.get("trades", 0) >= 10
    )
    # Check for systems that are actively losing (should push toward EXPERIMENTAL)
    systems_losing = sum(
        1 for s in source_stats
        if s.get("trades", 0) >= 10 and s.get("wr", 0) < 50
    )

    # ELITE: 3+ systems agree, 2+ with proven edge (30+ trades, WR>=55%), high confidence
    if (agreement >= 3
            and systems_with_proven_edge >= 2
            and confidence >= 0.60
            and systems_losing == 0
            and all(wr >= 55 or trades < 10 for wr, trades in zip(source_wrs, source_trades))):
        return "ELITE"

    # PROVEN: 2+ systems agree, at least 1 has validated forward edge (10+ trades, WR>=55%)
    # AND no actively losing systems in the mix
    if agreement >= 2 and systems_with_edge >= 1 and systems_losing == 0:
        return "PROVEN"

    # Everything else is experimental (includes picks backed by losing systems)
    return "EXPERIMENTAL"


def classify_system(system_name: str) -> str:
    """Classify a single system (not a consensus pick) for routing its solo picks."""
    stats = get_all_system_stats()
    s = stats.get(system_name, {})
    trades = s.get("trades", 0)
    wr = s.get("wr", 0)
    pf = s.get("pf", 0)

    if trades >= 5 and wr >= 55 and pf >= 1.2:
        return "PROVEN"
    elif trades < 5:
        return "EXPERIMENTAL"
    elif wr < 50:
        return "EXPERIMENTAL"
    else:
        return "PROVEN"
