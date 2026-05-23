#!/usr/bin/env python3
"""Sandbox Reporter — sends incubator strategy performance to Discord #sandbox.

Posts incubator proving-ground reports, backtest results, and strategy
comparisons to the #sandbox channel via bot token or webhook.

Environment:
    DISCORD_SANDBOX_WEBHOOK  — webhook URL for #sandbox (primary)
    DISCORD_BOT_TOKEN        — bot token fallback
"""

import json
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("sandbox_reporter")

DATA_DIR = Path(__file__).parent / "data"
SANDBOX_WEBHOOK = os.environ.get("DISCORD_SANDBOX_WEBHOOK", "")
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
SANDBOX_CHANNEL_ID = "1477929365550530600"
EST = timezone(timedelta(hours=-5))

# Colours
GREEN = 0x22C55E
YELLOW = 0xFACC15
RED = 0xEF4444
BLUE = 0x3B82F6
GOLD = 0xFFD700
GRAY = 0x6B7280

# Promotion thresholds (mirror incubator_promotion.py)
MIN_CLOSED_TRADES = 10
MIN_WIN_RATE = 0.55
MIN_PROFIT_FACTOR = 1.3


def _post_to_discord(payload: dict, max_retries: int = 3) -> bool:
    """Post to Discord via webhook or bot token fallback.

    Priority: DISCORD_SANDBOX_WEBHOOK > bot token + channel ID
    """
    # Try webhook first
    if SANDBOX_WEBHOOK:
        for attempt in range(max_retries):
            try:
                r = requests.post(SANDBOX_WEBHOOK, json=payload, timeout=10)
                if r.status_code == 429:
                    wait = int(r.headers.get("Retry-After", str(2 ** (attempt + 1))))
                    time.sleep(wait)
                    continue
                if r.status_code == 204 or r.ok:
                    logger.info("Sent to #sandbox via webhook")
                    return True
                logger.warning(f"Webhook returned {r.status_code}: {r.text[:200]}")
            except Exception as e:
                logger.error(f"Webhook error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

    # Fallback: send via bot token to #sandbox channel
    if BOT_TOKEN and SANDBOX_CHANNEL_ID:
        logger.info("Webhook unavailable, sending via bot token to #sandbox")
        headers = {"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}
        bot_payload = {"embeds": payload.get("embeds", [])}
        if payload.get("content"):
            bot_payload["content"] = payload["content"]
        for attempt in range(max_retries):
            try:
                r = requests.post(
                    f"https://discord.com/api/v10/channels/{SANDBOX_CHANNEL_ID}/messages",
                    headers=headers, json=bot_payload, timeout=15,
                )
                if r.status_code == 429:
                    wait = int(r.headers.get("Retry-After", str(2 ** (attempt + 1))))
                    time.sleep(wait)
                    continue
                if r.ok:
                    logger.info(f"Sent via bot to #sandbox (msg: {r.json().get('id', '?')})")
                    return True
                logger.warning(f"Bot send failed: {r.status_code} {r.text[:200]}")
            except Exception as e:
                logger.error(f"Bot send error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

    logger.error("No webhook or bot token available — cannot send to Discord")
    return False


def _load_active_picks() -> list:
    path = DATA_DIR / "active_picks.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except Exception as e:
        logger.error(f"Failed to load active_picks.json: {e}")
        return []


def _load_closed_picks() -> list:
    path = DATA_DIR / "closed_picks.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except Exception as e:
        logger.error(f"Failed to load closed_picks.json: {e}")
        return []


def _progress_bar(value: float, total: float, length: int = 10) -> str:
    filled = int(length * min(max(value / total, 0), 1.0)) if total > 0 else 0
    return "\u2588" * filled + "\u2591" * (length - filled)


def _status_color(status: str) -> int:
    """Return embed colour based on strategy status."""
    if status == "promoted":
        return GREEN
    elif status == "needs_data":
        return YELLOW
    else:
        return RED


def _wr_color(win_rate: float) -> int:
    """Return embed colour based on win rate percentage."""
    if win_rate >= 60:
        return GREEN
    elif win_rate >= 50:
        return YELLOW
    else:
        return RED


def _compute_strategy_stats(trades: list) -> dict:
    """Compute stats for a list of closed trades."""
    total = len(trades)
    if total == 0:
        return {
            "trades": 0, "wins": 0, "losses": 0,
            "win_rate": 0.0, "avg_pnl": 0.0, "profit_factor": 0.0,
            "worst_trade": 0.0, "best_trade": 0.0, "total_pnl": 0.0,
        }

    pnl_values = [t.get("pnl_pct", 0) or 0 for t in trades]
    wins = [p for p in pnl_values if p > 0]
    losses = [p for p in pnl_values if p <= 0]
    gross_wins = sum(wins) if wins else 0
    gross_losses = abs(sum(losses)) if losses else 0

    return {
        "trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / total * 100, 1),
        "avg_pnl": round(sum(pnl_values) / total, 3),
        "profit_factor": round(gross_wins / gross_losses, 2) if gross_losses > 0 else float("inf"),
        "worst_trade": round(min(pnl_values), 3),
        "best_trade": round(max(pnl_values), 3),
        "total_pnl": round(sum(pnl_values), 3),
    }


def send_incubator_report():
    """Main function: build and post incubator strategy report to #sandbox.

    Loads active_picks.json and closed_picks.json, groups by strategy,
    separates incubator from verified, and posts per-strategy cards with
    promotion progress to Discord.
    """
    logger.info("=" * 50)
    logger.info("Sandbox Reporter — Incubator Lab Report")
    logger.info("=" * 50)

    active = _load_active_picks()
    closed = _load_closed_picks()
    logger.info(f"Loaded {len(active)} active, {len(closed)} closed picks")

    # Group by strategy, separating incubator from verified
    incubator_closed = defaultdict(list)
    verified_closed = defaultdict(list)
    for pick in closed:
        strat = pick.get("strategy", "unknown")
        if pick.get("portfolio_type") == "incubator":
            incubator_closed[strat].append(pick)
        else:
            verified_closed[strat].append(pick)

    incubator_active = defaultdict(list)
    verified_active = defaultdict(list)
    for pick in active:
        strat = pick.get("strategy", "unknown")
        if pick.get("portfolio_type") == "incubator":
            incubator_active[strat].append(pick)
        else:
            verified_active[strat].append(pick)

    # All incubator strategy names
    all_incubator = sorted(set(list(incubator_closed.keys()) + list(incubator_active.keys())))

    now_est = datetime.now(EST).strftime("%b %d, %Y %I:%M %p EST")
    embeds = []

    # Header embed
    total_strategies = len(all_incubator)
    promoted_count = 0
    needs_data_count = 0
    underperforming_count = 0

    # Pre-compute statuses for summary
    strategy_results = {}
    for strat in all_incubator:
        stats = _compute_strategy_stats(incubator_closed.get(strat, []))
        if stats["trades"] < MIN_CLOSED_TRADES:
            status = "needs_data"
            needs_data_count += 1
        elif stats["win_rate"] >= MIN_WIN_RATE * 100 and stats["profit_factor"] >= MIN_PROFIT_FACTOR:
            status = "promoted"
            promoted_count += 1
        else:
            status = "underperforming"
            underperforming_count += 1
        strategy_results[strat] = {"stats": stats, "status": status}

    header = {
        "title": "INCUBATOR LAB | Strategy Proving Ground",
        "description": (
            f"**{total_strategies}** strategies in incubator\n"
            f"Promoted: **{promoted_count}** | "
            f"Gathering data: **{needs_data_count}** | "
            f"Underperforming: **{underperforming_count}**\n"
            f"__{now_est}__"
        ),
        "color": GREEN if promoted_count > 0 else (YELLOW if needs_data_count > 0 else GRAY),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    embeds.append(header)

    if not all_incubator:
        header["description"] += "\n\nNo incubator strategies found. Strategies enter here before earning verified status."
        _post_to_discord({"username": "Incubator Lab", "embeds": embeds})
        logger.info("No incubator strategies — sent empty report")
        return

    # Per-strategy embeds (limit to 9 to stay within Discord 10-embed limit)
    for strat in all_incubator[:9]:
        result = strategy_results[strat]
        stats = result["stats"]
        status = result["status"]
        active_positions = incubator_active.get(strat, [])
        color = _status_color(status)

        # Display name
        display_name = strat.replace("_", " ").title()

        # Status label
        if status == "promoted":
            status_label = "PROMOTED"
        elif status == "needs_data":
            status_label = "GATHERING DATA"
        else:
            status_label = "NEEDS IMPROVEMENT"

        # Build fields
        fields = [
            {"name": "Status", "value": f"**{status_label}**", "inline": True},
            {"name": "Closed Trades", "value": str(stats["trades"]), "inline": True},
            {"name": "Active Positions", "value": str(len(active_positions)), "inline": True},
        ]

        if stats["trades"] > 0:
            fields.extend([
                {"name": "W/L", "value": f"{stats['wins']}W / {stats['losses']}L", "inline": True},
                {"name": "Win Rate", "value": f"{stats['win_rate']:.1f}%", "inline": True},
                {"name": "Avg P&L", "value": f"{stats['avg_pnl']:+.3f}%", "inline": True},
                {"name": "Profit Factor", "value": f"{stats['profit_factor']:.2f}" if stats["profit_factor"] != float("inf") else "INF", "inline": True},
                {"name": "Best / Worst", "value": f"{stats['best_trade']:+.3f}% / {stats['worst_trade']:+.3f}%", "inline": True},
                {"name": "Total P&L", "value": f"{stats['total_pnl']:+.3f}%", "inline": True},
            ])

        # Progress bar toward promotion
        trade_progress = min(stats["trades"] / MIN_CLOSED_TRADES, 1.0)
        wr_progress = min((stats["win_rate"] / 100) / MIN_WIN_RATE, 1.0) if stats["trades"] > 0 else 0
        pf_progress = min(stats["profit_factor"] / MIN_PROFIT_FACTOR, 1.0) if stats["trades"] > 0 and stats["profit_factor"] != float("inf") else (1.0 if stats["profit_factor"] == float("inf") and stats["trades"] >= MIN_CLOSED_TRADES else 0)

        progress_text = (
            f"Trades: {_progress_bar(stats['trades'], MIN_CLOSED_TRADES)} {stats['trades']}/{MIN_CLOSED_TRADES}\n"
            f"WR:     {_progress_bar(stats['win_rate'], MIN_WIN_RATE * 100)} {stats['win_rate']:.1f}%/{MIN_WIN_RATE * 100:.0f}%\n"
            f"PF:     {_progress_bar(stats['profit_factor'] if stats['profit_factor'] != float('inf') else MIN_PROFIT_FACTOR, MIN_PROFIT_FACTOR)} "
            f"{stats['profit_factor']:.2f}/{MIN_PROFIT_FACTOR:.1f}" if stats["profit_factor"] != float("inf") else
            f"Trades: {_progress_bar(stats['trades'], MIN_CLOSED_TRADES)} {stats['trades']}/{MIN_CLOSED_TRADES}\n"
            f"WR:     {_progress_bar(stats['win_rate'], MIN_WIN_RATE * 100)} {stats['win_rate']:.1f}%/{MIN_WIN_RATE * 100:.0f}%\n"
            f"PF:     {_progress_bar(MIN_PROFIT_FACTOR, MIN_PROFIT_FACTOR)} INF/{MIN_PROFIT_FACTOR:.1f}"
        )
        fields.append({"name": "Promotion Progress", "value": f"```\n{progress_text}\n```", "inline": False})

        # Active positions summary
        if active_positions:
            pos_lines = []
            for pos in active_positions[:5]:
                symbol = pos.get("symbol", "?")
                direction = pos.get("direction", "?")
                entry = pos.get("entry_price", 0)
                pos_lines.append(f"{symbol} {direction} @ ${entry:,.6g}")
            if len(active_positions) > 5:
                pos_lines.append(f"... +{len(active_positions) - 5} more")
            fields.append({"name": "Open Positions", "value": "\n".join(pos_lines), "inline": False})

        embed = {
            "title": f"{display_name}",
            "color": color,
            "fields": fields,
            "footer": {"text": f"Incubator Lab | {status_label}"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        embeds.append(embed)

    # Send (max 10 embeds per message)
    logger.info(f"Sending {len(embeds)} embeds to #sandbox")
    success = _post_to_discord({"username": "Incubator Lab", "embeds": embeds[:10]})

    # If more than 9 strategies, send overflow in a second message
    if len(all_incubator) > 9:
        overflow_embeds = []
        for strat in all_incubator[9:18]:
            result = strategy_results[strat]
            stats = result["stats"]
            status = result["status"]
            display_name = strat.replace("_", " ").title()
            status_label = "PROMOTED" if status == "promoted" else ("GATHERING DATA" if status == "needs_data" else "NEEDS IMPROVEMENT")

            summary = (
                f"**{status_label}** | "
                f"{stats['trades']} trades | "
                f"{stats['wins']}W/{stats['losses']}L | "
                f"WR: {stats['win_rate']:.1f}% | "
                f"Avg: {stats['avg_pnl']:+.3f}%"
            )
            overflow_embeds.append({
                "title": display_name,
                "description": summary,
                "color": _status_color(status),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        if overflow_embeds:
            _post_to_discord({"username": "Incubator Lab", "embeds": overflow_embeds[:10]})

    if success:
        logger.info("Incubator report sent to #sandbox")
    else:
        logger.warning("Failed to send incubator report")


def send_backtest_results(results: dict):
    """Post formatted backtest results to #sandbox.

    Args:
        results: dict mapping strategy name to backtest metrics, e.g.:
            {
                "rsi_mean_reversion": {
                    "trades": 150, "win_rate": 62.5, "sharpe": 1.8,
                    "profit_factor": 1.65, "max_drawdown": -12.3,
                    "best_trade": 8.5, "worst_trade": -4.2,
                    "total_return": 45.6,
                },
                ...
            }
    """
    logger.info(f"Sending backtest results for {len(results)} strategies")

    now_est = datetime.now(EST).strftime("%b %d, %Y %I:%M %p EST")
    embeds = []

    # Header
    embeds.append({
        "title": "INCUBATOR LAB | Backtest Results",
        "description": f"**{len(results)}** strategies backtested\n__{now_est}__",
        "color": BLUE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    for strat_name, metrics in list(results.items())[:9]:
        wr = metrics.get("win_rate", 0)
        color = _wr_color(wr)
        display_name = strat_name.replace("_", " ").title()

        fields = [
            {"name": "Trades", "value": str(metrics.get("trades", 0)), "inline": True},
            {"name": "Win Rate", "value": f"{wr:.1f}%", "inline": True},
            {"name": "Sharpe Ratio", "value": f"{metrics.get('sharpe', 0):.2f}", "inline": True},
            {"name": "Profit Factor", "value": f"{metrics.get('profit_factor', 0):.2f}", "inline": True},
            {"name": "Max Drawdown", "value": f"{metrics.get('max_drawdown', 0):.1f}%", "inline": True},
            {"name": "Total Return", "value": f"{metrics.get('total_return', 0):+.1f}%", "inline": True},
            {"name": "Best Trade", "value": f"{metrics.get('best_trade', 0):+.2f}%", "inline": True},
            {"name": "Worst Trade", "value": f"{metrics.get('worst_trade', 0):+.2f}%", "inline": True},
        ]

        # Quality assessment
        if wr >= 60 and metrics.get("sharpe", 0) >= 1.5:
            quality = "HIGH QUALITY — promotion candidate"
        elif wr >= 50 and metrics.get("sharpe", 0) >= 1.0:
            quality = "ACCEPTABLE — continue monitoring"
        else:
            quality = "LOW QUALITY — review strategy logic"

        fields.append({"name": "Assessment", "value": quality, "inline": False})

        embeds.append({
            "title": display_name,
            "color": color,
            "fields": fields,
            "footer": {"text": "Backtest | Paper Trading Lab"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # Send (max 10 embeds per message)
    success = _post_to_discord({"username": "Incubator Lab | Backtest", "embeds": embeds[:10]})

    # Overflow for >9 strategies
    remaining = list(results.items())[9:]
    while remaining:
        batch = remaining[:10]
        remaining = remaining[10:]
        overflow = []
        for strat_name, metrics in batch:
            wr = metrics.get("win_rate", 0)
            display_name = strat_name.replace("_", " ").title()
            overflow.append({
                "title": display_name,
                "description": (
                    f"Trades: {metrics.get('trades', 0)} | "
                    f"WR: {wr:.1f}% | "
                    f"Sharpe: {metrics.get('sharpe', 0):.2f} | "
                    f"PF: {metrics.get('profit_factor', 0):.2f} | "
                    f"DD: {metrics.get('max_drawdown', 0):.1f}%"
                ),
                "color": _wr_color(wr),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        _post_to_discord({"username": "Incubator Lab | Backtest", "embeds": overflow})

    if success:
        logger.info("Backtest results sent to #sandbox")
    else:
        logger.warning("Failed to send backtest results")


def send_strategy_comparison(results: dict):
    """Post a comparison table showing all strategies ranked by Sharpe ratio.

    Args:
        results: dict mapping strategy name to metrics (same format as send_backtest_results).
    """
    logger.info(f"Sending strategy comparison for {len(results)} strategies")

    # Sort by Sharpe ratio descending
    ranked = sorted(results.items(), key=lambda x: x[1].get("sharpe", 0), reverse=True)

    now_est = datetime.now(EST).strftime("%b %d, %Y %I:%M %p EST")

    # Build table as code block
    header_line = f"{'#':<3} {'Strategy':<28} {'Sharpe':>7} {'WR%':>6} {'PF':>6} {'Trades':>7} {'Return':>8}"
    separator = "-" * len(header_line)
    rows = [header_line, separator]

    for i, (strat_name, metrics) in enumerate(ranked, 1):
        display = strat_name.replace("_", " ").title()
        if len(display) > 27:
            display = display[:24] + "..."
        sharpe = metrics.get("sharpe", 0)
        wr = metrics.get("win_rate", 0)
        pf = metrics.get("profit_factor", 0)
        trades = metrics.get("trades", 0)
        ret = metrics.get("total_return", 0)
        rows.append(f"{i:<3} {display:<28} {sharpe:>7.2f} {wr:>5.1f}% {pf:>6.2f} {trades:>7} {ret:>+7.1f}%")

    table_text = "\n".join(rows)

    # Split into chunks if the table is too long for a single code block (2000 char limit)
    chunks = []
    current_chunk = [header_line, separator]
    current_len = len(header_line) + len(separator) + 2

    for row in rows[2:]:  # skip header+separator already added
        if current_len + len(row) + 1 > 1800:
            chunks.append("\n".join(current_chunk))
            current_chunk = [header_line, separator, row]
            current_len = len(header_line) + len(separator) + len(row) + 3
        else:
            current_chunk.append(row)
            current_len += len(row) + 1

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    # Determine top strategy
    top_name = ranked[0][0].replace("_", " ").title() if ranked else "N/A"
    top_sharpe = ranked[0][1].get("sharpe", 0) if ranked else 0

    embeds = [{
        "title": "INCUBATOR LAB | Strategy Comparison (by Sharpe)",
        "description": (
            f"**{len(ranked)}** strategies ranked by risk-adjusted return\n"
            f"Top performer: **{top_name}** (Sharpe {top_sharpe:.2f})\n"
            f"__{now_est}__"
        ),
        "color": GOLD,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }]

    for i, chunk in enumerate(chunks[:9]):
        embeds.append({
            "title": f"Rankings{f' (cont. {i+1})' if i > 0 else ''}",
            "description": f"```\n{chunk}\n```",
            "color": BLUE,
        })

    success = _post_to_discord({"username": "Incubator Lab | Comparison", "embeds": embeds[:10]})

    if success:
        logger.info("Strategy comparison sent to #sandbox")
    else:
        logger.warning("Failed to send strategy comparison")


if __name__ == "__main__":
    send_incubator_report()
