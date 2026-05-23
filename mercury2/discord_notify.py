# -*- coding: utf-8 -*-
"""Mercury 2 — Discord notification module.

Sends rich embeds for system status, new picks, and trade exits.
"""

import logging
import requests as _req
from typing import List, Dict, Optional

from .config import DISCORD_WEBHOOK, VERSION, SYSTEM_NAME

log = logging.getLogger("mercury2.discord")

DASHBOARD_URL = "https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/mercury2/"


def _fmt_price(val) -> str:
    """Format price without scientific notation."""
    if val is None or val == 0:
        return "$0"
    val = float(val)
    if val >= 1000:
        return f"${val:,.2f}"
    elif val >= 1:
        return f"${val:.4f}"
    elif val >= 0.001:
        return f"${val:.6f}"
    else:
        return f"${val:.10f}"
COLORS = {
    "status_green": 0x00ff88,
    "status_red": 0xff4444,
    "status_neutral": 0x6366f1,
    "new_pick": 0x22c55e,
    "exit_win": 0xfbbf24,
    "exit_loss": 0xef4444,
}


def _post(payload: dict) -> None:
    if not DISCORD_WEBHOOK:
        return
    import time as _time
    for attempt in range(3):
        try:
            resp = _req.post(DISCORD_WEBHOOK, json=payload, timeout=10)
            if resp.status_code in (200, 204):
                return
            if resp.status_code == 429:
                retry_after = resp.json().get("retry_after", 3)
                _time.sleep(retry_after)
                continue
            log.warning("Discord post failed: %d", resp.status_code)
            if attempt < 2:
                _time.sleep(2 * (attempt + 1))
                continue
            return
        except Exception as e:
            if attempt == 2:
                log.warning("Discord send failed after 3 attempts: %s", e)
            else:
                _time.sleep(2 * (attempt + 1))


def _fng_label(fng: int) -> str:
    if fng <= 15:
        return f"{fng} (EXTREME FEAR)"
    if fng <= 25:
        return f"{fng} (Fear)"
    if fng <= 45:
        return f"{fng} (Caution)"
    if fng <= 55:
        return f"{fng} (Neutral)"
    if fng <= 75:
        return f"{fng} (Greed)"
    return f"{fng} (EXTREME GREED)"


def send_status(
    active_picks: List[Dict],
    closed_count: int,
    win_rate: float,
    total_pnl: float,
    fng: int,
    btc_dom: float,
    new_picks: List[Dict],
    newly_closed: List[Dict],
    top_gainers: Optional[List[Dict]] = None,
    closed_picks: Optional[List[Dict]] = None,
) -> None:
    """Send system status embed every scan cycle."""
    wins = round(closed_count * win_rate / 100) if closed_count else 0

    # Determine embed color
    if win_rate >= 65:
        color = COLORS["status_green"]
    elif win_rate >= 45:
        color = COLORS["status_neutral"]
    else:
        color = COLORS["status_red"]

    # Header line
    title = f"Mercury 2 v{VERSION}"
    if new_picks or newly_closed:
        parts = []
        if new_picks:
            parts.append(f"{len(new_picks)} new")
        if newly_closed:
            parts.append(f"{len(newly_closed)} closed")
        title += f" — {', '.join(parts)}"

    # Direction breakdown from closed picks
    long_closed = [p for p in (closed_picks or []) if p.get("direction") == "LONG"]
    short_closed = [p for p in (closed_picks or []) if p.get("direction") == "SHORT"]
    long_wins = sum(1 for p in long_closed if p.get("status") == "WIN" or p.get("realized_pnl_pct", 0) > 0)
    short_wins = sum(1 for p in short_closed if p.get("status") == "WIN" or p.get("realized_pnl_pct", 0) > 0)
    long_wr = (long_wins / len(long_closed) * 100) if long_closed else 0
    short_wr = (short_wins / len(short_closed) * 100) if short_closed else 0
    long_pnl = sum(p.get("realized_pnl_pct", 0) for p in long_closed)
    short_pnl = sum(p.get("realized_pnl_pct", 0) for p in short_closed)
    long_active = sum(1 for p in active_picks if p.get("direction") == "LONG")
    short_active = sum(1 for p in active_picks if p.get("direction") == "SHORT")

    fields = [
        {"name": "Active Picks", "value": f"{len(active_picks)} ({long_active}L / {short_active}S)", "inline": True},
        {"name": "Closed", "value": f"{wins}W / {closed_count - wins}L ({closed_count} total)", "inline": True},
        {"name": "Win Rate", "value": f"**{win_rate:.1f}%**", "inline": True},
        {"name": "Total PnL", "value": f"**{total_pnl:+.2f}%**", "inline": True},
        {"name": "F&G", "value": _fng_label(fng), "inline": True},
        {"name": "BTC Dom", "value": f"{btc_dom:.1f}%", "inline": True},
    ]

    # Direction stats (only if we have closed trades in both directions)
    dir_parts = []
    if long_closed:
        dir_parts.append(f"LONG: {long_wr:.0f}% WR ({long_wins}/{len(long_closed)}) {long_pnl:+.1f}%")
    if short_closed:
        dir_parts.append(f"SHORT: {short_wr:.0f}% WR ({short_wins}/{len(short_closed)}) {short_pnl:+.1f}%")
    if dir_parts:
        fields.append({"name": "Direction Stats", "value": "\n".join(dir_parts), "inline": False})

    # Active picks detail
    if active_picks:
        lines = []
        for p in active_picks[:8]:
            pnl = p.get("unrealized_pnl_pct", 0)
            icon = "+" if pnl >= 0 else ""
            trail = " (trailing)" if p.get("trailing_active") else ""
            lines.append(
                f"`{p['symbol']:12s}` {p['direction']} "
                f"{icon}{pnl:.2f}%{trail}"
            )
        fields.append({"name": "Positions", "value": "\n".join(lines)})

    # Newly closed detail
    if newly_closed:
        lines = []
        for p in newly_closed[:5]:
            pnl = p.get("realized_pnl_pct", 0)
            status = p.get("status", "CLOSED")
            icon = "+" if pnl >= 0 else ""
            lines.append(f"`{p['symbol']:12s}` {status} {icon}{pnl:.2f}%")
        fields.append({"name": "Just Resolved", "value": "\n".join(lines)})

    # Top gainers — ML-predicted next-24h returns (informational, not traded)
    if top_gainers:
        tg_lines = [
            f"`{g['symbol']:12s}` {g['predicted_return_pct']:+.1f}%"
            for g in top_gainers[:5]
        ]
        tg_lines.append("_ML prediction only — not auto-traded_")
        fields.append({"name": "Top Gainers (24h ML Forecast)", "value": "\n".join(tg_lines)})

    embed = {
        "title": title,
        "color": color,
        "fields": fields,
        "footer": {"text": f"{SYSTEM_NAME} v{VERSION} | Top Performing System"},
    }

    _post({"embeds": [embed]})


def send_pick_alert(pick: Dict, fng: int) -> None:
    """Send alert when a new high-confidence pick is opened."""
    sym = pick["symbol"]
    direction = pick.get("direction", "LONG")
    entry = pick.get("entry_price", 0)
    tp = pick.get("take_profit", 0)
    sl = pick.get("stop_loss", 0)
    conf = pick.get("confidence", 0)
    rr = pick.get("risk_reward", 0)

    embed = {
        "title": f"Mercury 2 — New {direction}: {sym}",
        "color": COLORS["new_pick"],
        "fields": [
            {"name": "Entry", "value": _fmt_price(entry), "inline": True},
            {"name": "Take Profit", "value": _fmt_price(tp), "inline": True},
            {"name": "Stop Loss", "value": _fmt_price(sl), "inline": True},
            {"name": "Confidence", "value": f"{conf*100:.1f}%" if conf <= 1 else f"{conf:.1f}%", "inline": True},
            {"name": "R:R", "value": f"{rr:.2f}", "inline": True},
            {"name": "F&G", "value": _fng_label(fng), "inline": True},
        ],
        "footer": {"text": f"{SYSTEM_NAME} v{VERSION}"},
    }
    _post({"embeds": [embed]})


def send_pick_exit(pick: Dict) -> None:
    """Send alert when a pick is resolved (WIN/LOSS/TIME_EXIT)."""
    sym = pick["symbol"]
    status = pick.get("status", "CLOSED")
    pnl = pick.get("realized_pnl_pct", 0)
    is_win = status == "WIN" or pnl > 0

    embed = {
        "title": f"Mercury 2 — {'WIN' if is_win else 'LOSS'}: {sym} ({pnl:+.2f}%)",
        "color": COLORS["exit_win"] if is_win else COLORS["exit_loss"],
        "fields": [
            {"name": "Entry", "value": _fmt_price(pick.get('entry_price', 0)), "inline": True},
            {"name": "Exit", "value": _fmt_price(pick.get('exit_price', pick.get('current_price', 0))), "inline": True},
            {"name": "PnL", "value": f"**{pnl:+.2f}%**", "inline": True},
            {"name": "Hold Time", "value": pick.get("hold_time", "N/A"), "inline": True},
            {"name": "Status", "value": status, "inline": True},
        ],
        "footer": {"text": f"{SYSTEM_NAME} v{VERSION}"},
    }
    _post({"embeds": [embed]})
