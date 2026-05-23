"""Discord notifier for #paper-trade channel."""
import logging
import os
import pathlib
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List

import requests

# Add repo root to path for shared utils
_repo_root = str(pathlib.Path(__file__).resolve().parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)
from utils.discord_format import format_strategy_stats, format_symbol_history
from utils.discord_heartbeat import send_no_picks_heartbeat

logger = logging.getLogger(__name__)

WEBHOOK_URL = os.environ.get(
    "DISCORD_WEBHOOK_PAPERTRADE",
    "https://discord.com/api/webhooks/1478588243459965008/9TZAjAtrgz5dTvWpV3TP7FO8Fo5JRDCz03PkPiTaSlef0EcIEdHEDUmz8Zi13sZrqgA3"
)
USERNAME = "Coinglass DNA Bundle"

COLOR_GREEN = 0x22C55E
COLOR_RED = 0xEF4444
COLOR_BLUE = 0x3B82F6
COLOR_GOLD = 0xFFD700
COLOR_PURPLE = 0x8B5CF6


def _post(embeds: list):
    if not WEBHOOK_URL:
        logger.warning("No DISCORD_WEBHOOK_PAPERTRADE set")
        return
    for i in range(0, len(embeds), 10):
        batch = embeds[i:i + 10]
        payload = {"username": USERNAME, "embeds": batch}
        for attempt in range(3):
            try:
                resp = requests.post(WEBHOOK_URL, json=payload, timeout=15)
                if resp.status_code in (200, 204):
                    break
                if resp.status_code == 429:
                    retry = resp.json().get("retry_after", 5)
                    time.sleep(retry)
                    continue
                logger.warning("Discord post failed: %d", resp.status_code)
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
                    continue
                break
            except Exception as exc:
                if attempt == 2:
                    logger.error("Discord error after 3 attempts: %s", exc)
                else:
                    time.sleep(2 * (attempt + 1))


def _get_strategy_track_record(strategy: str) -> str:
    """Build a short track record string for a strategy from closed positions."""
    try:
        from . import ratio_store
        stats = ratio_store.get_strategy_stats(strategy)
        if strategy not in stats or stats[strategy]["total"] == 0:
            return f"`{strategy}`: 0 trades \u2014 tracking started"
        return format_strategy_stats(strategy, stats[strategy])
    except Exception:
        return f"`{strategy}`: 0 trades \u2014 tracking started"


def send_signal_alerts(picks: List[Dict]):
    if not picks:
        return
    embeds = []
    for pick in picks:
        direction = pick.get("direction", "?")
        color = COLOR_GREEN if direction == "LONG" else COLOR_RED
        symbol = pick.get("symbol", "?")
        entry = pick.get("entry_price", 0)
        tp = pick.get("take_profit", 0)
        sl = pick.get("stop_loss", 0)
        conf = pick.get("confidence", 0)
        strategy = pick.get("strategy", "?")
        reason = pick.get("reason", "")
        filled = int(conf * 10)
        bar = "\u2588" * filled + "\u2591" * (10 - filled)
        rr = f"{abs(tp - entry) / abs(entry - sl):.1f}x" if abs(entry - sl) > 0 else "\u2014"
        fields = [
            {"name": "Strategy", "value": f"`{strategy}`", "inline": True},
            {"name": "Confidence", "value": f"{bar} {conf:.0%}", "inline": True},
            {"name": "Entry", "value": f"${entry:,.2f}", "inline": True},
            {"name": "Take Profit", "value": f"${tp:,.2f}", "inline": True},
            {"name": "Stop Loss", "value": f"${sl:,.2f}", "inline": True},
            {"name": "R:R", "value": rr, "inline": True},
            {"name": "Rationale", "value": reason[:200], "inline": False},
        ]
        # Always show strategy performance (even if 0 trades)
        track_record = _get_strategy_track_record(strategy)
        fields.append({"name": "\U0001f4c8 Strategy Performance", "value": track_record, "inline": False})

        # Add symbol-specific history (e.g., "SOLUSDT LONGs: 3W/1L (75%)")
        try:
            from . import ratio_store
            sym_stats = ratio_store.get_symbol_direction_stats(symbol, direction)
            if sym_stats and sym_stats.get("total", 0) > 0:
                sym_line = format_symbol_history(symbol, direction, sym_stats["wins"], sym_stats["losses"])
                if sym_line:
                    fields.append({"name": "\U0001f4ca Symbol History", "value": sym_line, "inline": True})
        except Exception:
            pass

        embed = {
            "title": f"{'🟢' if direction == 'LONG' else '🔴'} {direction} {symbol}",
            "color": color,
            "fields": fields,
            "footer": {"text": f"Coinglass DNA Bundle \u2022 {datetime.now(timezone.utc).strftime('%H:%M UTC')}"},
        }
        embeds.append(embed)
    _post(embeds)
    logger.info("Sent %d signal alerts to Discord", len(embeds))


def send_portfolio_summary(summary: Dict, ratio_snapshot: Dict = None):
    equity = summary.get("equity", 0)
    pnl_pct = summary.get("pnl_pct", 0)
    color = COLOR_GREEN if pnl_pct >= 0 else COLOR_RED
    positions_text = ""
    for pos in summary.get("positions", [])[:5]:
        sym = pos.get("symbol", "?")
        d = pos.get("direction", "?")
        entry = pos.get("entry_price", 0)
        positions_text += f"{'🟢' if d == 'LONG' else '🔴'} {sym} {d} @ ${entry:,.2f}\n"
    if not positions_text:
        positions_text = "No open positions"
    embed = {
        "title": "\U0001f4ca Coinglass DNA \u2014 Portfolio Summary",
        "color": color,
        "fields": [
            {"name": "Equity", "value": f"${equity:,.2f}", "inline": True},
            {"name": "P&L", "value": f"{'+'if pnl_pct >= 0 else ''}{pnl_pct:.2f}%", "inline": True},
            {"name": "Total P&L", "value": f"${summary.get('total_pnl', 0):,.2f}", "inline": True},
            {"name": "Trades", "value": f"{summary.get('total_trades', 0)} ({summary.get('wins', 0)}W / {summary.get('losses', 0)}L)", "inline": True},
            {"name": "Win Rate", "value": f"{summary.get('win_rate', 0):.1f}%", "inline": True},
            {"name": "Open Positions", "value": f"{summary.get('open_positions', 0)}/5", "inline": True},
            {"name": "Positions", "value": positions_text, "inline": False},
        ],
        "footer": {"text": f"Starting capital: ${summary.get('starting_capital', 10000):,.0f} \u2022 Updated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"},
    }
    if ratio_snapshot:
        ratio_text = ""
        for sym, data in ratio_snapshot.items():
            g = data.get("global", "\u2014")
            t = data.get("taker", "\u2014")
            ratio_text += f"**{sym}**: G={g:.3f} T={t:.3f}\n" if isinstance(g, float) else f"**{sym}**: no data\n"
        if ratio_text:
            embed["fields"].append({"name": "Current Ratios", "value": ratio_text[:1024], "inline": False})
    _post([embed])
    logger.info("Sent portfolio summary to Discord")


def send_close_alert(position: Dict, exit_reason: str, exit_price: float):
    direction = position.get("direction", "?")
    symbol = position.get("symbol", "?")
    entry = position.get("entry_price", 0)
    pnl_pct = position.get("pnl_pct", 0)
    is_win = exit_reason == "TP_HIT"
    color = COLOR_GOLD if is_win else COLOR_PURPLE
    embed = {
        "title": f"{'✅' if is_win else '❌'} CLOSED {symbol} {direction}",
        "color": color,
        "fields": [
            {"name": "Entry", "value": f"${entry:,.2f}", "inline": True},
            {"name": "Exit", "value": f"${exit_price:,.2f}", "inline": True},
            {"name": "P&L", "value": f"{'+'if pnl_pct >= 0 else ''}{pnl_pct:.2f}%", "inline": True},
            {"name": "Reason", "value": exit_reason, "inline": True},
        ],
        "footer": {"text": f"Coinglass DNA Bundle \u2022 {datetime.now(timezone.utc).strftime('%H:%M UTC')}"},
    }
    _post([embed])


def send_no_picks_alert(symbols_scanned: int, active_positions: int = 0):
    """Send heartbeat when scan completes with no qualifying picks."""
    send_no_picks_heartbeat(
        webhook_url=WEBHOOK_URL,
        channel_name="Coinglass DNA Bundle",
        scan_info={
            "symbols_scanned": symbols_scanned,
            "filter_reason": "No signals met confidence/ratio thresholds this cycle",
            "active_positions": active_positions,
        },
    )
