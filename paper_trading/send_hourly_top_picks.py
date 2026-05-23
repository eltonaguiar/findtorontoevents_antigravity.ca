#!/usr/bin/env python3
"""Hourly Top Picks — sends paper trading's best active positions to #master-picks.

Reads active_picks.json (enriched with strategy metadata), checks live prices
via Binance, computes real-time P&L, and sends the top performing picks to
Discord #master-picks with full tracked performance.

Only sends picks that are:
  1. Still active (not expired/closed)
  2. Moving in the predicted direction (unrealised P&L >= 0)
  3. Still valid for entry (price between entry and TP, not past SL)

Environment:
    DISCORD_MASTER_PICKS  — webhook for #master-picks channel
    DISCORD_FRESHPICKS    — webhook for #fresh-picks channel (overflow)
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("hourly_top_picks")

DATA_DIR = Path(__file__).parent / "data"
MASTER_WEBHOOK = os.environ.get("DISCORD_MASTER_PICKS", "")
FRESH_WEBHOOK = os.environ.get("DISCORD_FRESHPICKS", "")
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
MASTER_CHANNEL_ID = "1477931341772230808"  # #master-picks channel
EST = timezone(timedelta(hours=-5))

# Colours
GREEN = 0x22C55E
RED = 0xEF4444
BLUE = 0x3B82F6
GOLD = 0xFFD700
GRAY = 0x6B7280


def _fetch_live_price(symbol: str) -> float | None:
    """Fetch current price with multi-source fallback (Binance -> CryptoCompare -> CoinGecko)."""
    try:
        from paper_trading.multi_source import fetch_price
        result = fetch_price(symbol)
        price = float(result.get("price", 0))
        if price > 0:
            return price
    except Exception:
        pass
    # Last-resort direct Binance call (in case multi_source fails to import)
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/price",
            params={"symbol": symbol}, timeout=8,
        )
        if r.ok:
            return float(r.json()["price"])
    except Exception:
        pass
    return None


def _load_active_picks() -> list[dict]:
    """Load active picks from paper trading data."""
    path = DATA_DIR / "active_picks.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except Exception as e:
        logger.error(f"Failed to load active picks: {e}")
        return []


def _load_closed_picks() -> list[dict]:
    """Load closed picks for track record calculation."""
    path = DATA_DIR / "closed_picks.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except Exception:
        return []


def _strategy_track_record(strategy_name: str, closed: list[dict]) -> dict:
    """Compute win rate and average P&L for a strategy from closed picks."""
    trades = [p for p in closed if p.get("strategy") == strategy_name]
    if not trades:
        return {}
    total = len(trades)
    wins = sum(1 for t in trades if (t.get("pnl_pct") or 0) > 0)
    avg_pnl = sum(t.get("pnl_pct", 0) or 0 for t in trades) / total
    return {
        "total_trades": total,
        "wins": wins,
        "losses": total - wins,
        "win_rate": round(wins / total * 100, 1),
        "avg_pnl": round(avg_pnl, 2),
    }


def _progress_bar(value: float, total: float, length: int = 10) -> str:
    filled = int(length * min(max(value / total, 0), 1.0)) if total > 0 else 0
    return "\u2588" * filled + "\u2591" * (length - filled)


def _pick_is_valid_for_entry(pick: dict, live_price: float) -> bool:
    """Check if pick is still valid for entry (price hasn't blown past TP or SL)."""
    entry = pick.get("entry_price", 0)
    tp = pick.get("tp", 0)
    sl = pick.get("sl", 0)
    direction = pick.get("direction", "LONG")

    if direction == "LONG":
        # Valid if price hasn't hit TP or SL
        return sl < live_price < tp
    else:
        return tp < live_price < sl


def _pick_going_our_way(pick: dict, live_price: float) -> bool:
    """Check if the pick is moving in the predicted direction."""
    entry = pick.get("entry_price", 0)
    direction = pick.get("direction", "LONG")
    if direction == "LONG":
        return live_price >= entry
    else:
        return live_price <= entry


def _compute_live_pnl(pick: dict, live_price: float) -> float:
    """Compute unrealised P&L percentage."""
    entry = pick.get("entry_price", 0)
    if entry <= 0:
        return 0.0
    if pick.get("direction") == "LONG":
        return round((live_price - entry) / entry * 100, 3)
    else:
        return round((entry - live_price) / entry * 100, 3)


def _tp_distance_pct(pick: dict, live_price: float) -> float:
    """How far (%) from TP."""
    tp = pick.get("tp", 0)
    if live_price <= 0:
        return 0.0
    if pick.get("direction") == "LONG":
        return round((tp - live_price) / live_price * 100, 2)
    else:
        return round((live_price - tp) / live_price * 100, 2)


def _sl_distance_pct(pick: dict, live_price: float) -> float:
    """How far (%) from SL."""
    sl = pick.get("sl", 0)
    if live_price <= 0:
        return 0.0
    if pick.get("direction") == "LONG":
        return round((live_price - sl) / live_price * 100, 2)
    else:
        return round((sl - live_price) / live_price * 100, 2)


def build_top_picks_embeds(picks: list[dict], closed: list[dict]) -> list[dict]:
    """Build Discord embeds for top performing valid picks."""
    enriched = []
    seen = set()  # dedup by symbol+direction — portfolio manager creates dupes across portfolio types

    for pick in picks:
        symbol = pick.get("symbol", "")
        direction = pick.get("direction", "")
        dedup_key = f"{symbol}_{direction}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        live_price = _fetch_live_price(symbol)
        if live_price is None:
            continue
        time.sleep(0.1)  # rate limit

        if not _pick_is_valid_for_entry(pick, live_price):
            continue

        pnl = _compute_live_pnl(pick, live_price)
        going_our_way = _pick_going_our_way(pick, live_price)

        enriched.append({
            **pick,
            "live_price": live_price,
            "live_pnl_pct": pnl,
            "going_our_way": going_our_way,
            "tp_dist": _tp_distance_pct(pick, live_price),
            "sl_dist": _sl_distance_pct(pick, live_price),
        })

    # Sort: picks going our way first, then by P&L descending
    enriched.sort(key=lambda p: (not p["going_our_way"], -p["live_pnl_pct"]))

    # Only include picks going our way for master-picks
    valid = [p for p in enriched if p["going_our_way"]][:5]

    if not valid:
        return []

    embeds = []
    now_est = datetime.now(EST).strftime("%b %d, %Y %I:%M %p EST")

    # Header embed
    total_pnl = sum(p["live_pnl_pct"] for p in valid)
    direction_counts = {"LONG": 0, "SHORT": 0}
    for p in valid:
        direction_counts[p.get("direction", "LONG")] += 1

    header = {
        "title": f"HOURLY TOP PICKS | Paper Trading | {now_est}",
        "description": (
            f"**{len(valid)} valid picks** moving in predicted direction\n"
            f"Avg unrealised P&L: **{total_pnl / len(valid):+.2f}%** | "
            f"LONG: {direction_counts['LONG']} | SHORT: {direction_counts['SHORT']}"
        ),
        "color": GREEN if total_pnl > 0 else RED,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    embeds.append(header)

    # Per-pick embeds
    for i, pick in enumerate(valid, 1):
        direction = pick.get("direction", "LONG")
        color = GREEN if pick["live_pnl_pct"] >= 0 else RED
        conf = pick.get("confidence", 0.5)
        conf_bar = _progress_bar(conf, 1.0)

        strategy = pick.get("strategy", "")
        display_name = pick.get("display_name") or pick.get("strategy_name", strategy)
        system_name = pick.get("system_name", "Paper Trading")
        dashboard_url = pick.get("dashboard_url", "")
        rr = pick.get("risk_reward", 0)
        if not rr:
            # Compute from TP/SL
            entry = pick.get("entry_price", 0)
            tp = pick.get("tp", 0)
            sl = pick.get("sl", 0)
            dist_tp = abs(tp - entry)
            dist_sl = abs(entry - sl)
            rr = round(dist_tp / dist_sl, 2) if dist_sl > 0 else 0

        # Track record
        tr = _strategy_track_record(strategy, closed)
        tr_text = ""
        if tr:
            tr_text = (
                f"{tr['total_trades']} trades | "
                f"{tr['wins']}W/{tr['losses']}L | "
                f"WR: {tr['win_rate']}% | "
                f"Avg: {tr['avg_pnl']:+.2f}%"
            )

        # Entry time
        entry_date = pick.get("entry_date", "")
        if entry_date:
            try:
                entered = datetime.fromisoformat(entry_date)
                hold_mins = int((datetime.now(timezone.utc) - entered).total_seconds() / 60)
                if hold_mins < 60:
                    hold_str = f"{hold_mins}m"
                elif hold_mins < 1440:
                    hold_str = f"{hold_mins // 60}h {hold_mins % 60}m"
                else:
                    hold_str = f"{hold_mins // 1440}d {(hold_mins % 1440) // 60}h"
            except Exception:
                hold_str = "?"
        else:
            hold_str = "?"

        fields = [
            {"name": "Direction", "value": f"**{direction}**", "inline": True},
            {"name": "Live P&L", "value": f"**{pick['live_pnl_pct']:+.2f}%**", "inline": True},
            {"name": "Confidence", "value": f"{conf_bar} {conf*100:.0f}%", "inline": True},
            {"name": "Entry", "value": f"${pick.get('entry_price', 0):,.6g}", "inline": True},
            {"name": "Live Price", "value": f"${pick['live_price']:,.6g}", "inline": True},
            {"name": "R:R", "value": f"{rr:.1f}:1", "inline": True},
            {"name": "TP Distance", "value": f"{pick['tp_dist']:+.2f}% (${pick.get('tp', 0):,.6g})", "inline": True},
            {"name": "SL Distance", "value": f"{pick['sl_dist']:.2f}% (${pick.get('sl', 0):,.6g})", "inline": True},
            {"name": "Hold Time", "value": hold_str, "inline": True},
            {"name": "Strategy", "value": f"**{display_name}**", "inline": True},
            {"name": "System", "value": system_name, "inline": True},
            {"name": "Reason", "value": (pick.get("reason") or "")[:150], "inline": False},
        ]
        if tr_text:
            fields.append({"name": "Track Record", "value": tr_text, "inline": False})
        if dashboard_url:
            fields.append({"name": "Dashboard", "value": f"[View Live]({dashboard_url})", "inline": True})

        embed = {
            "title": f"#{i} | {pick['symbol']} {direction}",
            "color": color,
            "fields": fields,
            "footer": {"text": f"Paper Trade Only | Not Financial Advice | {display_name}"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        embeds.append(embed)

    return embeds


def _post_to_discord(payload: dict, webhook: str = "", max_retries: int = 3):
    """Post to Discord via webhook or bot token fallback.

    Priority: webhook URL > bot token + channel ID
    """
    # Try webhook first
    if webhook:
        for attempt in range(max_retries):
            try:
                r = requests.post(webhook, json=payload, timeout=10)
                if r.status_code == 429:
                    wait = int(r.headers.get("Retry-After", str(2 ** (attempt + 1))))
                    time.sleep(wait)
                    continue
                if r.status_code == 204 or r.ok:
                    return True
                logger.warning(f"Webhook returned {r.status_code}: {r.text[:200]}")
            except Exception as e:
                logger.error(f"Webhook error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

    # Fallback: send via bot token to #master-picks channel
    if BOT_TOKEN and MASTER_CHANNEL_ID:
        logger.info("Webhook unavailable, sending via bot token to #master-picks")
        headers = {"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}
        bot_payload = {"embeds": payload.get("embeds", [])}
        for attempt in range(max_retries):
            try:
                r = requests.post(
                    f"https://discord.com/api/v10/channels/{MASTER_CHANNEL_ID}/messages",
                    headers=headers, json=bot_payload, timeout=15,
                )
                if r.status_code == 429:
                    wait = int(r.headers.get("Retry-After", str(2 ** (attempt + 1))))
                    time.sleep(wait)
                    continue
                if r.ok:
                    logger.info(f"Sent via bot to #master-picks (msg: {r.json().get('id', '?')})")
                    return True
                logger.warning(f"Bot send failed: {r.status_code} {r.text[:200]}")
            except Exception as e:
                logger.error(f"Bot send error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

    logger.error("No webhook or bot token available — cannot send to Discord")
    return False


def _log_to_mysql(picks: list[dict]):
    """Log sent picks to MySQL audit trail."""
    try:
        from audit_trail.mysql_client import log_discord_send
        for pick in picks:
            log_discord_send(
                pick_data={
                    "symbol": pick.get("symbol"),
                    "direction": pick.get("direction"),
                    "entry_price": pick.get("entry_price"),
                    "tp": pick.get("tp"),
                    "sl": pick.get("sl"),
                    "confidence": pick.get("confidence"),
                    "strategy": pick.get("display_name") or pick.get("strategy_name"),
                    "system_name": pick.get("system_name", "Paper Trading"),
                    "live_pnl_pct": pick.get("live_pnl_pct"),
                    "live_price": pick.get("live_price"),
                },
                channel="master_picks",
                event_type="HOURLY_TOP_PICK",
                webhook_name="paper_trading_hourly",
            )
    except Exception as e:
        logger.warning(f"MySQL audit logging failed (non-fatal): {e}")


def send_hourly_top_picks():
    """Main entry point: load picks, enrich with live prices, send to Discord."""
    logger.info("=" * 50)
    logger.info("Paper Trading — Hourly Top Picks")
    logger.info("=" * 50)

    active = _load_active_picks()
    if not active:
        logger.info("No active picks found")
        if MASTER_WEBHOOK or BOT_TOKEN:
            now_str = datetime.now(EST).strftime("%b %d, %Y %I:%M %p EST")
            _post_to_discord({
                "embeds": [{
                    "title": f"Paper Trading Hourly | {now_str}",
                    "description": "No active paper trading positions at this time.",
                    "color": GRAY,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }]
            })
        return

    closed = _load_closed_picks()
    logger.info(f"Loaded {len(active)} active, {len(closed)} closed picks")

    embeds = build_top_picks_embeds(active, closed)
    if not embeds:
        logger.info("No valid picks moving in predicted direction")
        if MASTER_WEBHOOK or BOT_TOKEN:
            now_str = datetime.now(EST).strftime("%b %d, %Y %I:%M %p EST")
            _post_to_discord({
                "embeds": [{
                    "title": f"Paper Trading Hourly | {now_str}",
                    "description": (
                        f"{len(active)} active positions but none currently moving in predicted direction. "
                        "Waiting for price confirmation before recommending entry."
                    ),
                    "color": GRAY,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }]
            })
        return

    # Send to #master-picks (max 10 embeds per message)
    logger.info(f"Sending {len(embeds)} embeds to #master-picks")
    success = _post_to_discord({
        "username": "Paper Trading | Hourly Top Picks",
        "embeds": embeds[:10],
    }, webhook=MASTER_WEBHOOK)
    if success:
        logger.info("Successfully sent to #master-picks")
    else:
        logger.warning("Failed to send to #master-picks")

    # Log to MySQL
    valid_picks = [e for e in embeds if "fields" in e]  # skip header
    _log_to_mysql(active[:5])

    # Sync to MySQL
    try:
        from paper_trading.mysql_sync import sync_to_mysql
        synced = sync_to_mysql()
        logger.info(f"MySQL sync: {synced} positions")
    except Exception as e:
        logger.warning(f"MySQL sync failed: {e}")

    logger.info("Done")


if __name__ == "__main__":
    send_hourly_top_picks()
