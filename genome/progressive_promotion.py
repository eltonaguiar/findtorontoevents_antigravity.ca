"""
Progressive Promotion Pipeline
===============================
Evaluates DNA Factory strategies on forward-trading performance and
promotes / demotes them through tiers:

    INCUBATOR -> SANDBOX -> FRESH_PICKS -> DNA_MASTER

Promotion rules (cumulative forward trades):
    INCUBATOR  -> SANDBOX      : 10+ trades
    SANDBOX    -> FRESH_PICKS  : 20+ trades, WR >= 50%, Sharpe >= 0.5
    FRESH_PICKS-> DNA_MASTER   : 30+ trades, WR >= 55%, Sharpe >= 1.5

Demotion rules (rolling 20-trade window):
    DNA_MASTER -> FRESH_PICKS  : WR < 50% or Sharpe < 1.0
    FRESH_PICKS-> SANDBOX      : WR < 45% or Sharpe < 0.3
    SANDBOX    -> INCUBATOR    : WR < 40%
"""

import sys
import os
import math
import json
import sqlite3
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from alpha_engine.asset_class import normalize_asset_class

# ---------------------------------------------------------------------------
# Paths & Constants
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
FACTORY_DB = REPO_ROOT / "battleground" / "data" / "dna_factory.db"
EST = timezone(timedelta(hours=-5))

TIERS = ["INCUBATOR", "SANDBOX", "FRESH_PICKS", "DNA_MASTER"]
TIER_EMOJI = {
    "INCUBATOR": "\U0001f331",    # seedling
    "SANDBOX": "\U0001f9ea",       # test tube
    "FRESH_PICKS": "\U0001f4ca",   # bar chart
    "DNA_MASTER": "\U0001f9ec",    # dna
}
# ASCII-safe fallbacks for Windows terminals that can't render emoji
TIER_LABEL = {
    "INCUBATOR": "[INCUB]",
    "SANDBOX": "[SBOX] ",
    "FRESH_PICKS": "[FRESH]",
    "DNA_MASTER": "[MASTER]",
}
COLOR_GOLD = 0xFFD700
COLOR_GREEN = 0x22C55E
COLOR_RED = 0xEF4444
COLOR_BLUE = 0x3B82F6

ROLLING_WINDOW = 20

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ProgressivePromotion")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tier_rank(tier: str) -> int:
    """Return numeric rank for a tier. INCUBATOR=0 ... DNA_MASTER=3."""
    mapping = {"INCUBATOR": 0, "SANDBOX": 1, "FRESH_PICKS": 2, "DNA_MASTER": 3}
    return mapping.get(tier, -1)


def _compute_sharpe(pnl_list: List[float]) -> float:
    """
    Annualised Sharpe ratio from a list of per-trade PnL percentages.
    Uses sqrt(252) annualisation factor (daily trading assumption).
    Returns 0.0 for edge cases (empty, single trade, zero variance).
    """
    if len(pnl_list) < 2:
        return 0.0
    mean = sum(pnl_list) / len(pnl_list)
    variance = sum((x - mean) ** 2 for x in pnl_list) / (len(pnl_list) - 1)
    if variance <= 0:
        return 0.0
    std = math.sqrt(variance)
    return (mean / std) * math.sqrt(252)


def log_outcome_to_mysql(conn, pick: dict, outcome: str, exit_price: float, pnl_pct: float):
    """Write a forward trade result to MySQL at_signal_outcomes."""
    from datetime import datetime as _dt
    sql = """
        INSERT INTO at_signal_outcomes
        (symbol, direction, entry_price, take_profit, stop_loss,
         exit_price, outcome, pnl_pct, source_system, strategy,
         asset_class, opened_at, closed_at, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
    """
    params = (
        pick["symbol"], pick["direction"], pick["entry_price"],
        pick.get("tp"), pick.get("sl"), exit_price, outcome,
        round(pnl_pct, 4), "dna_genome", pick.get("strategy_id", "unknown"),
        normalize_asset_class(pick).upper(), pick.get("opened_at"), _dt.now(timezone.utc),
    )
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()


def _get_strategy_forward_stats(
    conn: sqlite3.Connection,
    strategy_id: str,
    rolling_window: int = 0,
) -> Dict:
    """
    Compute forward-trading statistics for a strategy from factory_trades.

    Parameters
    ----------
    conn : sqlite3 connection
    strategy_id : strategy to evaluate
    rolling_window : if > 0, only use the most recent N closed trades

    Returns
    -------
    dict with keys: trades, wins, losses, wr, sharpe, pnl, pnl_list
    """
    cur = conn.cursor()
    if rolling_window > 0:
        cur.execute(
            """
            SELECT status, pnl_pct FROM factory_trades
            WHERE strategy_id = ? AND status IN ('WON', 'LOST')
            ORDER BY id DESC LIMIT ?
            """,
            (strategy_id, rolling_window),
        )
    else:
        cur.execute(
            """
            SELECT status, pnl_pct FROM factory_trades
            WHERE strategy_id = ? AND status IN ('WON', 'LOST')
            ORDER BY id ASC
            """,
            (strategy_id,),
        )

    rows = cur.fetchall()
    trades = len(rows)
    wins = sum(1 for r in rows if r[0] == "WON")
    losses = trades - wins
    pnl_list = [r[1] for r in rows if r[1] is not None]
    total_pnl = sum(pnl_list)
    wr = (wins / trades * 100) if trades > 0 else 0.0
    sharpe = _compute_sharpe(pnl_list)

    return {
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "wr": round(wr, 2),
        "sharpe": round(sharpe, 4),
        "pnl": round(total_pnl, 4),
        "pnl_list": pnl_list,
    }


# ---------------------------------------------------------------------------
# Promotion / Demotion Logic
# ---------------------------------------------------------------------------

def _check_promotion(tier: str, stats: Dict) -> Optional[str]:
    """Check if strategy qualifies for promotion (one tier up)."""
    t = stats["trades"]
    wr = stats["wr"]
    sharpe = stats["sharpe"]

    if tier == "INCUBATOR" and t >= 10:
        return "SANDBOX"
    if tier == "SANDBOX" and t >= 20 and wr >= 50.0 and sharpe >= 0.5:
        return "FRESH_PICKS"
    if tier == "FRESH_PICKS" and t >= 30 and wr >= 55.0 and sharpe >= 1.5:
        return "DNA_MASTER"
    return None


def _check_demotion(tier: str, rolling_stats: Dict) -> Optional[str]:
    """Check if strategy should be demoted based on rolling window stats."""
    wr = rolling_stats["wr"]
    sharpe = rolling_stats["sharpe"]
    trades = rolling_stats["trades"]

    # Need at least some trades in rolling window to demote
    if trades < 5:
        return None

    if tier == "DNA_MASTER" and (wr < 50.0 or sharpe < 1.0):
        return "FRESH_PICKS"
    if tier == "FRESH_PICKS" and (wr < 45.0 or sharpe < 0.3):
        return "SANDBOX"
    if tier == "SANDBOX" and wr < 40.0:
        return "INCUBATOR"
    return None


# ---------------------------------------------------------------------------
# Main Evaluation
# ---------------------------------------------------------------------------

def evaluate_promotions() -> List[Dict]:
    """
    Evaluate all factory strategies for promotion/demotion.

    Returns list of tier changes:
        [{strategy_id, name, old_tier, new_tier, stats, direction}, ...]
    """
    if not FACTORY_DB.exists():
        logger.error("Factory DB not found: %s", FACTORY_DB)
        return []

    conn = sqlite3.connect(str(FACTORY_DB))
    conn.row_factory = sqlite3.Row
    changes: List[Dict] = []
    now_str = datetime.now(EST).strftime("%Y-%m-%d %H:%M:%S")

    try:
        cur = conn.cursor()
        cur.execute("SELECT strategy_id, name, tier FROM factory_strategies")
        strategies = cur.fetchall()
        logger.info("Evaluating %d strategies ...", len(strategies))

        for row in strategies:
            sid = row["strategy_id"]
            name = row["name"]
            old_tier = row["tier"]

            # Full forward stats (all trades)
            full_stats = _get_strategy_forward_stats(conn, sid)

            # Update forward_* columns
            cur.execute(
                """
                UPDATE factory_strategies SET
                    forward_trades = ?,
                    forward_wins = ?,
                    forward_losses = ?,
                    forward_wr = ?,
                    forward_sharpe = ?,
                    forward_pnl = ?,
                    last_evaluated = ?
                WHERE strategy_id = ?
                """,
                (
                    full_stats["trades"],
                    full_stats["wins"],
                    full_stats["losses"],
                    full_stats["wr"],
                    full_stats["sharpe"],
                    full_stats["pnl"],
                    now_str,
                    sid,
                ),
            )

            new_tier = old_tier

            # Check promotion first (using full stats)
            promoted_to = _check_promotion(old_tier, full_stats)
            if promoted_to:
                new_tier = promoted_to

            # Check demotion (using rolling window) -- only if not already promoted
            if new_tier == old_tier:
                rolling_stats = _get_strategy_forward_stats(conn, sid, ROLLING_WINDOW)
                demoted_to = _check_demotion(old_tier, rolling_stats)
                if demoted_to:
                    new_tier = demoted_to

            if new_tier != old_tier:
                direction = "PROMOTED" if _tier_rank(new_tier) > _tier_rank(old_tier) else "DEMOTED"
                cur.execute(
                    """
                    UPDATE factory_strategies SET tier = ?, last_promoted = ?
                    WHERE strategy_id = ?
                    """,
                    (new_tier, now_str, sid),
                )
                changes.append({
                    "strategy_id": sid,
                    "name": name,
                    "old_tier": old_tier,
                    "new_tier": new_tier,
                    "stats": full_stats,
                    "direction": direction,
                })
                logger.info(
                    "%s %s: %s -> %s (trades=%d, WR=%.1f%%, Sharpe=%.2f)",
                    direction, name, old_tier, new_tier,
                    full_stats["trades"], full_stats["wr"], full_stats["sharpe"],
                )

        conn.commit()

        if not changes:
            logger.info("No tier changes.")
        else:
            logger.info("%d tier change(s) applied.", len(changes))

    finally:
        conn.close()

    return changes


# ---------------------------------------------------------------------------
# Discord Notifications
# ---------------------------------------------------------------------------

def send_tier_change_notifications(changes: List[Dict]) -> int:
    """
    Send Discord webhook embeds for tier changes.

    Webhook routing:
        DNA_MASTER changes  -> WEBHOOK_DNA_MASTER / DISCORD_WEBHOOK_DNA_MASTER
        FRESH_PICKS changes -> WEBHOOK_URL / DISCORD_WEBHOOK_URL
        SANDBOX changes     -> WEBHOOK_SANDBOX / DISCORD_WEBHOOK_SANDBOX
        INCUBATOR demotions -> no notification

    Returns count of successfully sent notifications.
    """
    try:
        import requests
    except ImportError:
        logger.warning("requests not installed -- skipping Discord notifications")
        return 0

    webhook_map = {
        "DNA_MASTER": os.environ.get("WEBHOOK_DNA_MASTER") or os.environ.get("DISCORD_WEBHOOK_DNA_MASTER", ""),
        "FRESH_PICKS": os.environ.get("WEBHOOK_URL") or os.environ.get("DISCORD_WEBHOOK_URL", ""),
        "SANDBOX": os.environ.get("WEBHOOK_SANDBOX") or os.environ.get("DISCORD_WEBHOOK_SANDBOX", ""),
    }

    sent = 0
    for change in changes:
        # Route based on new tier (promotion) or old tier (demotion)
        target_tier = change["new_tier"] if change["direction"] == "PROMOTED" else change["old_tier"]

        # Skip INCUBATOR notifications
        if target_tier == "INCUBATOR":
            continue

        webhook_url = webhook_map.get(target_tier, "")
        if not webhook_url:
            logger.debug("No webhook configured for tier %s", target_tier)
            continue

        stats = change["stats"]
        arrow = "\u2b06\ufe0f" if change["direction"] == "PROMOTED" else "\u2b07\ufe0f"
        old_emoji = TIER_EMOJI.get(change["old_tier"], "")
        new_emoji = TIER_EMOJI.get(change["new_tier"], "")
        color = COLOR_GREEN if change["direction"] == "PROMOTED" else COLOR_RED

        embed = {
            "title": f"{arrow} {change['direction']}: {change['name']}",
            "description": (
                f"{old_emoji} **{change['old_tier']}** -> {new_emoji} **{change['new_tier']}**"
            ),
            "color": color,
            "fields": [
                {"name": "Win Rate", "value": f"{stats['wr']:.1f}%", "inline": True},
                {"name": "Sharpe", "value": f"{stats['sharpe']:.2f}", "inline": True},
                {"name": "Total PnL", "value": f"{stats['pnl']:+.2f}%", "inline": True},
                {"name": "Record", "value": f"{stats['wins']}W / {stats['losses']}L ({stats['trades']} trades)", "inline": True},
            ],
            "footer": {"text": f"DNA Progressive Promotion | {datetime.now(EST).strftime('%Y-%m-%d %H:%M EST')}"},
        }

        payload = {"embeds": [embed]}
        import time as _time
        for _attempt in range(3):
            try:
                resp = requests.post(webhook_url, json=payload, timeout=10)
                if resp.status_code in (200, 204):
                    sent += 1
                    logger.info("Notification sent for %s -> %s", change["name"], change["new_tier"])
                    break
                if resp.status_code == 429:
                    _time.sleep(resp.json().get("retry_after", 3))
                    continue
                logger.warning("Discord returned %d for %s", resp.status_code, change["name"])
                if _attempt < 2:
                    _time.sleep(2 * (_attempt + 1))
                    continue
                break
            except Exception as exc:
                if _attempt == 2:
                    logger.warning("Failed to notify for %s after 3 attempts: %s", change["name"], exc)
                else:
                    _time.sleep(2 * (_attempt + 1))

    logger.info("Sent %d / %d notifications.", sent, len(changes))
    return sent


# ---------------------------------------------------------------------------
# Tier Summary
# ---------------------------------------------------------------------------

def print_tier_summary():
    """Print a summary table of strategies grouped by tier."""
    if not FACTORY_DB.exists():
        logger.error("Factory DB not found: %s", FACTORY_DB)
        return

    conn = sqlite3.connect(str(FACTORY_DB))
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            tier,
            COUNT(*) as cnt,
            COALESCE(AVG(forward_wr), 0) as avg_wr,
            COALESCE(AVG(forward_sharpe), 0) as avg_sharpe,
            COALESCE(SUM(forward_trades), 0) as total_trades
        FROM factory_strategies
        GROUP BY tier
        ORDER BY
            CASE tier
                WHEN 'DNA_MASTER' THEN 0
                WHEN 'FRESH_PICKS' THEN 1
                WHEN 'SANDBOX' THEN 2
                WHEN 'INCUBATOR' THEN 3
            END
        """
    )
    rows = cur.fetchall()
    conn.close()

    print("\n" + "=" * 65)
    print("  DNA FACTORY -- TIER SUMMARY")
    print("=" * 65)
    print(f"  {'Tier':<16} {'Count':>6} {'Avg WR':>8} {'Avg Sharpe':>12} {'Trades':>8}")
    print("-" * 65)

    total_strats = 0
    total_trades = 0
    for tier, cnt, avg_wr, avg_sharpe, trades in rows:
        label = TIER_LABEL.get(tier, tier[:7])
        try:
            emoji = TIER_EMOJI.get(tier, "")
            line = f"  {emoji} {tier:<13} {cnt:>6} {avg_wr:>7.1f}% {avg_sharpe:>11.2f} {trades:>8}"
            print(line)
        except UnicodeEncodeError:
            print(f"  {label} {tier:<13} {cnt:>6} {avg_wr:>7.1f}% {avg_sharpe:>11.2f} {trades:>8}")
        total_strats += cnt
        total_trades += trades

    print("-" * 65)
    print(f"  {'TOTAL':<16} {total_strats:>6} {'':>8} {'':>12} {total_trades:>8}")
    print("=" * 65 + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="DNA Progressive Promotion Pipeline")
    parser.add_argument("--evaluate", action="store_true", help="Run promotion/demotion evaluation")
    parser.add_argument("--notify", action="store_true", help="Send Discord notifications (use with --evaluate)")
    parser.add_argument("--summary", action="store_true", help="Print tier summary")
    parser.add_argument("--check", action="store_true",
                        help="Standalone promotion check: evaluate + notify + summary")
    args = parser.parse_args()

    # --check is a convenience shortcut for evaluate + notify + summary
    if args.check:
        args.evaluate = True
        args.notify = True
        args.summary = True

    # Default: evaluate + summary
    if not args.evaluate and not args.summary and not args.notify:
        args.evaluate = True
        args.summary = True

    changes = []
    if args.evaluate:
        changes = evaluate_promotions()

    if args.notify and changes:
        send_tier_change_notifications(changes)

    if args.summary:
        print_tier_summary()


if __name__ == "__main__":
    main()
