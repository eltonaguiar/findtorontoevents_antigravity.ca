"""Discord reporter - posts trade events and portfolio summaries to #paper-trade."""
import logging
import os
import requests
import time
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("paper_trading")

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_PAPER_TRADE", "")
USERNAME = "Paper Trading Bot"

COLOR_GREEN = 0x22C55E
COLOR_RED = 0xEF4444
COLOR_BLUE = 0x3B82F6
COLOR_GOLD = 0xFFD700
COLOR_GRAY = 0x6B7280

EST = timezone(timedelta(hours=-5))


def _post_webhook(payload: dict, max_retries: int = 3):
    """Post to Discord webhook with retry/backoff."""
    if not WEBHOOK_URL:
        logger.warning("No DISCORD_WEBHOOK_PAPER_TRADE set, skipping Discord post")
        return
    for attempt in range(max_retries):
        try:
            r = requests.post(WEBHOOK_URL, json=payload, timeout=10)
            if r.status_code == 429:
                retry_after = int(r.headers.get("Retry-After", str(2 ** (attempt + 1))))
                logger.warning(f"Discord rate limited, waiting {retry_after}s")
                time.sleep(retry_after)
                continue
            if r.status_code == 204 or r.ok:
                return
            logger.warning(f"Discord webhook returned {r.status_code}: {r.text[:200]}")
        except Exception as e:
            logger.error(f"Discord webhook error: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    logger.error("Failed to post to Discord after retries")


def _progress_bar(value: float, total: float, length: int = 10) -> str:
    """Create a visual progress bar."""
    if total <= 0:
        return "\u2591" * length
    filled = int(length * min(value / total, 1.0))
    return "\u2588" * filled + "\u2591" * (length - filled)


def _get_strategy_track_record(strategy_name: str) -> str:
    """Query closed positions for this strategy and return a track-record string."""
    try:
        from paper_trading.db import get_conn
        conn = get_conn()
        rows = conn.execute(
            "SELECT pnl_pct FROM positions WHERE strategy_name=? AND status!='ACTIVE'",
            (strategy_name,)
        ).fetchall()
        conn.close()
        if not rows:
            return ""
        total = len(rows)
        wins = sum(1 for r in rows if (r["pnl_pct"] or 0) > 0)
        losses = total - wins
        wr = round(wins / total * 100, 1) if total else 0
        avg_pnl = round(sum(r["pnl_pct"] or 0 for r in rows) / total, 2) if total else 0
        win_pnl = sum(r["pnl_pct"] for r in rows if (r["pnl_pct"] or 0) > 0)
        loss_pnl = sum(abs(r["pnl_pct"]) for r in rows if (r["pnl_pct"] or 0) < 0)
        pf = round(win_pnl / loss_pnl, 2) if loss_pnl > 0 else "\u221e"
        return (f"**Track Record:** {total} trades | "
                f"{wins}W/{losses}L | WR: {wr}% | PF: {pf} | Avg: {avg_pnl:+.2f}%")
    except Exception:
        return ""


def send_entry_alert(event: dict):
    """Send a new entry notification."""
    symbol = event["symbol"]
    direction = event["direction"]
    color = COLOR_GREEN if direction == "LONG" else COLOR_RED

    conf_bar = _progress_bar(event.get("confidence", 0.5), 1.0, 10)
    rr = event.get("risk_reward", 0)

    fields = [
        {"name": "Portfolio", "value": f"`{event['portfolio']}` | `{event['tier']}`", "inline": True},
        {"name": "Strategy", "value": event.get("strategy", ""), "inline": True},
        {"name": "Position Size", "value": f"${event.get('position_usd', 0):,.2f}", "inline": True},
        {"name": "Entry", "value": f"${event['entry_price']:,.4f}", "inline": True},
        {"name": "TP", "value": f"${event['tp']:,.4f}", "inline": True},
        {"name": "SL", "value": f"${event['sl']:,.4f}", "inline": True},
        {"name": "Confidence", "value": f"{conf_bar} {event.get('confidence', 0.5)*100:.0f}%", "inline": True},
        {"name": "Risk:Reward", "value": f"{rr:.1f}:1", "inline": True},
        {"name": "Reason", "value": event.get("reason", "")[:200], "inline": False},
    ]
    track_record = _get_strategy_track_record(event.get("strategy", ""))
    if track_record:
        fields.append({"name": "\U0001f4c8 Strategy Performance", "value": track_record, "inline": False})

    embed = {
        "title": f"NEW ENTRY | {symbol} {direction}",
        "color": color,
        "fields": fields,
        "footer": {"text": f"Paper Trade Only | Not Financial Advice | {datetime.now(EST).strftime('%b %d %Y %I:%M %p EST')}"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    _post_webhook({"username": USERNAME, "embeds": [embed]})


def send_exit_alert(event: dict):
    """Send an exit (TP/SL/expiry) notification."""
    symbol = event["symbol"]
    status = event["status"]
    pnl_pct = event.get("pnl_pct", 0)
    pnl_usd = event.get("pnl_usd", 0)

    if status == "TP_HIT":
        color = COLOR_GREEN
    elif status == "SL_HIT":
        color = COLOR_RED
    else:
        color = COLOR_GRAY

    pnl_sign = "+" if pnl_pct >= 0 else ""

    embed = {
        "title": f"{status.replace('_', ' ')} | {symbol} {event['direction']}",
        "color": color,
        "fields": [
            {"name": "P&L", "value": f"**{pnl_sign}{pnl_pct:.2f}%** (${pnl_sign}{pnl_usd:.2f})", "inline": True},
            {"name": "Entry > Exit", "value": f"${event['entry_price']:,.4f} > ${event['exit_price']:,.4f}", "inline": True},
            {"name": "Hold Time", "value": f"{event.get('hold_days', 0)} days", "inline": True},
            {"name": "Portfolio", "value": f"`{event['portfolio']}`", "inline": True},
            {"name": "Strategy", "value": event.get("strategy", ""), "inline": True},
        ],
        "footer": {"text": f"Paper Trade Only | {datetime.now(EST).strftime('%b %d %Y %I:%M %p EST')}"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    _post_webhook({"username": USERNAME, "embeds": [embed]})


def send_portfolio_summary(summary: list):
    """Send the 4-hourly portfolio summary with tables."""
    now_est = datetime.now(EST).strftime("%b %d, %Y %I:%M %p EST")

    strategy_type = [p for p in summary if p["type"] == "strategy_type"]
    conviction_tier = [p for p in summary if p["type"] == "conviction_tier"]

    # Build strategy type table
    st_lines = ["```"]
    st_lines.append(f"{'Portfolio':<14} {'Value':>10} {'P&L%':>7} {'Trades':>7} {'WR%':>6} {'Active':>7}")
    st_lines.append("-" * 55)
    for p in strategy_type:
        pnl_str = f"{p['pnl_pct']:+.1f}%"
        st_lines.append(
            f"{p['name']:<14} ${p['equity']:>8,.0f} {pnl_str:>7} {p['total_trades']:>7} "
            f"{p['win_rate']:>5.0f}% {p['active_positions']:>7}"
        )
    st_lines.append("```")

    # Build conviction tier table
    ct_lines = ["```"]
    ct_lines.append(f"{'Portfolio':<18} {'Value':>10} {'P&L%':>7} {'Trades':>7} {'WR%':>6}")
    ct_lines.append("-" * 52)
    for p in conviction_tier:
        pnl_str = f"{p['pnl_pct']:+.1f}%"
        ct_lines.append(
            f"{p['name']:<18} ${p['equity']:>8,.0f} {pnl_str:>7} {p['total_trades']:>7} {p['win_rate']:>5.0f}%"
        )
    ct_lines.append("```")

    # Find best/worst
    all_pf = strategy_type + conviction_tier
    if all_pf:
        best = max(all_pf, key=lambda p: p["pnl_pct"])
        worst = min(all_pf, key=lambda p: p["pnl_pct"])
        footer_text = f"Best: {best['name']} ({best['pnl_pct']:+.1f}%) | Worst: {worst['name']} ({worst['pnl_pct']:+.1f}%)"
    else:
        footer_text = "No portfolio data yet"

    total_equity = sum(p["equity"] for p in all_pf)
    total_starting = len(all_pf) * 10000
    total_pnl = ((total_equity - total_starting) / total_starting) * 100 if total_starting else 0

    embeds = [
        {
            "title": f"PAPER PORTFOLIO REPORT | {now_est}",
            "description": f"**Total Equity:** ${total_equity:,.0f} / ${total_starting:,.0f} ({total_pnl:+.2f}%)\n**Portfolios:** {len(all_pf)} | **10 Strategies** | Free API Data Sources",
            "color": COLOR_BLUE,
            "fields": [
                {"name": "BY STRATEGY TYPE", "value": "\n".join(st_lines), "inline": False},
                {"name": "BY CONVICTION TIER", "value": "\n".join(ct_lines), "inline": False},
            ],
            "footer": {"text": footer_text},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    ]

    _post_webhook({"username": USERNAME, "embeds": embeds})


def send_events(events: dict, portfolio_summary: list = None):
    """Send all trade events and optionally a portfolio summary."""
    entries = events.get("entries", [])
    for entry in entries:
        send_entry_alert(entry)
        time.sleep(0.5)

    exits = events.get("exits", [])
    for exit_event in exits:
        send_exit_alert(exit_event)
        time.sleep(0.5)

    if portfolio_summary:
        send_portfolio_summary(portfolio_summary)
