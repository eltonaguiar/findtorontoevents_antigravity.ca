#!/usr/bin/env python3
"""
Discord #freshpicks — Baby Bundle Active Picks
================================================
Shows active picks from the top baby-bundle forward-tested strategies
with real-time price tracking, "Room to TP" progress bars (accounts for
notification delay), performance stats, and disclaimer.

Format mirrors the KIMI "Claws of Doom" style:
  BTC LONG — StrategyName (F) (1W/0L, 100% WR)
  Entry: $65,314.76 -> TP: $66,452.91 (+1.7%)
  Now: $65,610.00 | Room to TP: [####............] 94.2%
  SL: $64,461.15 (-1.3%) | R:R 1.3 | reason
  Showing all 8 picks | Feb 27, 2026 06:36 PM EST

Usage:
    python discord_freshpicks_baby.py             # Preview in terminal
    python discord_freshpicks_baby.py --send      # Send to #freshpicks webhook
    python discord_freshpicks_baby.py --bot       # For Discord.py bot integration
"""

import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None

# ── Paths ──────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent
FORWARD_DB = REPO_ROOT / "incubator" / "forward_test.db"
FORWARD_JSON = REPO_ROOT / "incubator" / "backtest_results" / "forward_signals.json"
TIERED_RESULTS = REPO_ROOT / "incubator" / "backtest_results" / "tiered_test_results.json"

# ── Discord ────────────────────────────────────────────────────────────────
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_FRESHPICKS", os.environ.get("DISCORD_WEBHOOK_URL", ""))

# ── Timezone ───────────────────────────────────────────────────────────────
EST = timezone(timedelta(hours=-5))

# ── Progress bar characters ────────────────────────────────────────────────
BAR_FILLED = "\u2588"   # █
BAR_EMPTY = "\u2591"    # ░

# ── Binance public API ─────────────────────────────────────────────────────
BINANCE_PRICE_URL = "https://api.binance.com/api/v3/ticker/price"


COINGECKO_IDS = {
    "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
    "DOGEUSDT": "dogecoin", "ADAUSDT": "cardano", "DOTUSDT": "polkadot",
}


def fetch_live_prices(symbols: List[str]) -> Dict[str, float]:
    """Fetch current prices from Binance, fallback to CoinGecko."""
    if not requests or not symbols:
        return {}
    prices = {}

    # 1) Binance — individual symbol endpoint
    for sym in symbols:
        try:
            resp = requests.get(f"{BINANCE_PRICE_URL}?symbol={sym}", timeout=8)
            if resp.status_code == 200:
                prices[sym] = float(resp.json()["price"])
        except Exception:
            pass

    # 2) Fallback: CoinGecko for any still missing
    missing = [s for s in symbols if s not in prices and s in COINGECKO_IDS]
    if missing:
        try:
            ids = ",".join(COINGECKO_IDS[s] for s in missing)
            resp = requests.get(
                f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd",
                timeout=8
            )
            if resp.status_code == 200:
                data = resp.json()
                for sym in missing:
                    cg_id = COINGECKO_IDS[sym]
                    if cg_id in data and "usd" in data[cg_id]:
                        prices[sym] = float(data[cg_id]["usd"])
        except Exception:
            pass

    return prices


def fmt_price(val: float, symbol: str = "") -> str:
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


def progress_bar(pct: float, length: int = 18) -> str:
    """Build a visual progress bar. pct is 0-100."""
    pct = max(0, min(100, pct))
    filled = round(pct / 100 * length)
    empty = length - filled
    bar = BAR_FILLED * filled + BAR_EMPTY * empty
    return f"{bar} {pct:.1f}%"


def room_to_tp_pct(entry: float, tp: float, current: float, direction: str) -> float:
    """
    Calculate how much of the TP move is still available (0-100%).
    Accounts for notification delay — shows users how much profit remains.
    """
    if direction in ("BUY", "LONG"):
        total_move = tp - entry
        if total_move <= 0:
            return 0.0
        remaining = tp - current
        return max(0, min(100, (remaining / total_move) * 100))
    else:  # SELL / SHORT
        total_move = entry - tp
        if total_move <= 0:
            return 0.0
        remaining = current - tp
        return max(0, min(100, (remaining / total_move) * 100))


def current_pnl_pct(entry: float, current: float, direction: str) -> float:
    """Current unrealized P&L %."""
    if direction in ("BUY", "LONG"):
        return ((current - entry) / entry) * 100
    else:
        return ((entry - current) / entry) * 100


def load_open_trades() -> List[Dict]:
    """Load open trades from forward_test.db or forward_signals.json."""
    trades = []

    # Try SQLite first (most up-to-date)
    if FORWARD_DB.exists():
        try:
            conn = sqlite3.connect(str(FORWARD_DB))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='forward_signals'")
            if cursor.fetchone():
                cursor.execute("""
                    SELECT id, strategy_name, symbol, direction, entry_price,
                           take_profit, stop_loss, confidence, reason, entry_time,
                           max_favorable, max_adverse, bars_held
                    FROM forward_signals
                    WHERE status = 'OPEN'
                    ORDER BY entry_time DESC
                """)
                for row in cursor.fetchall():
                    trades.append(dict(row))
            conn.close()
        except Exception as e:
            print(f"  [FreshPicks] DB error: {e}")

    # Fallback to JSON
    if not trades and FORWARD_JSON.exists():
        try:
            with open(FORWARD_JSON, "r") as f:
                data = json.load(f)
            trades = [t for t in data.get("open_trades", []) if t.get("status") == "OPEN"]
        except Exception:
            pass

    return trades


def load_strategy_summaries() -> Dict[str, Dict]:
    """Load per-strategy summary stats from forward_test.db."""
    summaries = {}
    if not FORWARD_DB.exists():
        return summaries
    try:
        conn = sqlite3.connect(str(FORWARD_DB))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='forward_summary'")
        if cursor.fetchone():
            cursor.execute("SELECT * FROM forward_summary")
            for row in cursor.fetchall():
                summaries[row["strategy_name"]] = dict(row)
        conn.close()
    except Exception:
        pass
    return summaries


def load_closed_trades() -> List[Dict]:
    """Load recently closed trades."""
    trades = []
    if not FORWARD_DB.exists():
        return trades
    try:
        conn = sqlite3.connect(str(FORWARD_DB))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='forward_signals'")
        if cursor.fetchone():
            cursor.execute("""
                SELECT strategy_name, symbol, direction, entry_price, exit_price,
                       pnl_pct, exit_reason, entry_time, exit_time
                FROM forward_signals
                WHERE status = 'CLOSED'
                ORDER BY exit_time DESC
                LIMIT 10
            """)
            for row in cursor.fetchall():
                trades.append(dict(row))
        conn.close()
    except Exception:
        pass
    return trades


def load_tiered_sharpe() -> Dict[str, float]:
    """Load tier1 backtest Sharpe for each strategy."""
    sharpes = {}
    if TIERED_RESULTS.exists():
        try:
            with open(TIERED_RESULTS, "r") as f:
                data = json.load(f)
            for name, info in data.get("details", {}).items():
                t1 = info.get("tier1", {})
                sharpes[name] = t1.get("best_sharpe", t1.get("best", {}).get("sharpe", 0))
        except Exception:
            pass
    return sharpes


def load_direction_stats() -> Dict[str, Dict[str, Dict]]:
    """Load per-strategy, per-direction (LONG/SHORT) win/loss stats from forward_signals."""
    stats = {}
    if not FORWARD_DB.exists():
        return stats
    try:
        conn = sqlite3.connect(str(FORWARD_DB))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='forward_signals'")
        if not cursor.fetchone():
            conn.close()
            return stats
        cursor.execute("""
            SELECT strategy_name, direction,
                   SUM(CASE WHEN status='CLOSED' AND pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN status='CLOSED' AND pnl_pct <= 0 THEN 1 ELSE 0 END) as losses,
                   SUM(CASE WHEN status='CLOSED' THEN pnl_pct ELSE 0 END) as total_pnl,
                   COUNT(CASE WHEN status='OPEN' THEN 1 END) as open_count
            FROM forward_signals
            GROUP BY strategy_name, direction
        """)
        for row in cursor.fetchall():
            name, direction, wins, losses, pnl, open_ct = row
            dir_label = "LONG" if direction in ("BUY", "LONG") else "SHORT"
            if name not in stats:
                stats[name] = {}
            stats[name][dir_label] = {
                "wins": wins or 0, "losses": losses or 0,
                "pnl": pnl or 0, "open": open_ct or 0
            }
        conn.close()
    except Exception:
        pass
    return stats


def short_strategy_name(name: str) -> str:
    """Shorten strategy names for display."""
    # Remove common suffixes
    for suffix in ("Strategy", "Strat"):
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    return name


def generate_message() -> str:
    """Generate the full #freshpicks Discord message with progress bars."""
    now_est = datetime.now(EST)
    timestamp = now_est.strftime("%b %d, %Y %I:%M %p EST")

    open_trades = load_open_trades()
    summaries = load_strategy_summaries()
    closed_trades = load_closed_trades()
    tiered_sharpes = load_tiered_sharpe()

    # Get unique symbols for price fetch
    symbols = list(set(t["symbol"] for t in open_trades))

    # Fetch live prices
    live_prices = fetch_live_prices(symbols) if symbols else {}

    # Calculate overall stats
    total_wins = sum(s.get("wins", 0) for s in summaries.values())
    total_losses = sum(s.get("losses", 0) for s in summaries.values())
    total_closed = total_wins + total_losses
    overall_wr = (total_wins / total_closed * 100) if total_closed > 0 else 0
    total_pnl = sum(s.get("total_pnl_pct", 0) for s in summaries.values())
    active_strategies = sum(1 for s in summaries.values() if s.get("open_trades", 0) > 0)

    # ── Header ─────────────────────────────────────────────────────────
    lines = []
    lines.append("```ansi")
    lines.append("\u001b[1;36m\u2554\u2550\u2550 BABY BUNDLE \u2014 #freshpicks \u2550\u2550\u2557\u001b[0m")
    lines.append(f"\u001b[0;33m  Forward-Tested Baby Strategies | Live Picks\u001b[0m")
    lines.append(f"\u001b[0;90m  {active_strategies} active strategies | {len(open_trades)} open picks\u001b[0m")
    if total_closed > 0:
        lines.append(f"\u001b[0;90m  Overall: {total_wins}W/{total_losses}L ({overall_wr:.1f}% WR) | P/L: {total_pnl:+.2f}%\u001b[0m")
    lines.append("")

    if not open_trades:
        lines.append("\u001b[0;33m  No active picks right now. Strategies scanning...\u001b[0m")
        lines.append("```")
        lines.append(f"*{timestamp}*")
        lines.append(_disclaimer())
        return "\n".join(lines)

    # ── Each pick ──────────────────────────────────────────────────────
    for trade in open_trades:
        symbol = trade["symbol"]
        direction = trade["direction"]
        strat_name = trade["strategy_name"]
        entry = trade["entry_price"]
        tp = trade["take_profit"]
        sl = trade["stop_loss"]
        confidence = trade.get("confidence", 0)
        reason = trade.get("reason", "")
        entry_time = trade.get("entry_time", "")

        # Live price
        current = live_prices.get(symbol, entry)
        has_live = symbol in live_prices

        # Strategy record
        summary = summaries.get(strat_name, {})
        wins = summary.get("wins", 0)
        losses = summary.get("losses", 0)
        strat_wr = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        bt_sharpe = tiered_sharpes.get(strat_name, summary.get("tier1_sharpe", 0))

        # Direction display
        sym_short = symbol.replace("USDT", "")
        dir_emoji = "\U0001f4c8" if direction in ("BUY", "LONG") else "\U0001f4c9"
        dir_label = "LONG" if direction in ("BUY", "LONG") else "SHORT"

        # TP/SL percentages
        if direction in ("BUY", "LONG"):
            tp_pct = ((tp / entry) - 1) * 100
            sl_pct = (1 - (sl / entry)) * 100
        else:
            tp_pct = (1 - (tp / entry)) * 100
            sl_pct = ((sl / entry) - 1) * 100

        # R:R ratio
        reward = abs(tp - entry)
        risk = abs(entry - sl)
        rr = reward / risk if risk > 0 else 0

        # Room to TP
        room = room_to_tp_pct(entry, tp, current, direction)
        pnl = current_pnl_pct(entry, current, direction)

        # Confidence display
        conf_display = f"{confidence * 100:.0f}%" if confidence <= 1 else f"{confidence:.0f}%"

        # Strategy record display
        record = f"({wins}W/{losses}L, {strat_wr:.0f}% WR)" if (wins + losses) > 0 else "(F)"

        # Short reason
        short_reason = reason[:50] if reason else strat_name

        # Color codes for ANSI in Discord
        if pnl > 0:
            pnl_color = "\u001b[0;32m"  # green
        elif pnl < 0:
            pnl_color = "\u001b[0;31m"  # red
        else:
            pnl_color = "\u001b[0;33m"  # yellow

        room_color = "\u001b[0;32m" if room >= 70 else "\u001b[0;33m" if room >= 30 else "\u001b[0;31m"
        dir_color = "\u001b[1;32m" if dir_label == "LONG" else "\u001b[1;31m"

        # Build pick block
        display_name = short_strategy_name(strat_name)
        lines.append(f"{dir_color}{sym_short} {dir_label}\u001b[0m \u2014 {display_name} {record}")
        lines.append(f"  Entry: {fmt_price(entry, symbol)} \u2192 TP: {fmt_price(tp, symbol)} (+{tp_pct:.1f}%)")

        # Current price + Room to TP bar
        price_label = "Now" if has_live else "Last"
        lines.append(f"  {price_label}: {fmt_price(current, symbol)} | Room to TP: {room_color}{progress_bar(room)}\u001b[0m")

        # SL + R:R + P&L + reason
        lines.append(f"  SL: {fmt_price(sl, symbol)} (-{sl_pct:.1f}%) | R:R {rr:.1f} | {pnl_color}P/L: {pnl:+.2f}%\u001b[0m")
        lines.append(f"\u001b[0;90m  {short_reason} | Conf: {conf_display} | BT Sharpe: {bt_sharpe:.1f}\u001b[0m")
        lines.append("")

    # ── Recently closed ────────────────────────────────────────────────
    if closed_trades:
        lines.append("\u001b[1;35m\u2500\u2500 Recently Closed \u2500\u2500\u001b[0m")
        for ct in closed_trades[:5]:
            sym = ct["symbol"].replace("USDT", "")
            pnl_val = ct.get("pnl_pct", 0)
            reason_label = ct.get("exit_reason", "")
            icon = "\u2705" if pnl_val > 0 else "\u274c"
            color = "\u001b[0;32m" if pnl_val > 0 else "\u001b[0;31m"
            lines.append(f"  {icon} {sym} {ct['direction'][:4]} {color}{pnl_val:+.2f}%\u001b[0m ({reason_label}) \u2014 {short_strategy_name(ct['strategy_name'])}")
        lines.append("")

    # ── Footer ─────────────────────────────────────────────────────────
    lines.append(f"\u001b[0;90mShowing all {len(open_trades)} picks | {timestamp}\u001b[0m")
    lines.append(f"\u001b[0;90mRoom to TP = % of profit target still available (accounts for delay)\u001b[0m")
    lines.append("```")

    # ── Disclaimer (outside code block) ────────────────────────────────
    lines.append(_disclaimer())

    return "\n".join(lines)


def _render_pick(trade: Dict, live_prices: Dict, summaries: Dict,
                  tiered_sharpes: Dict, dir_stats: Dict) -> str:
    """Render a single pick as a plain-text block (no ``` wrapping)."""
    symbol = trade["symbol"]
    direction = trade["direction"]
    strat_name = trade["strategy_name"]
    entry = trade["entry_price"]
    tp = trade["take_profit"]
    sl = trade["stop_loss"]
    confidence = trade.get("confidence", 0)
    reason = trade.get("reason", "")

    current = live_prices.get(symbol, entry)
    has_live = symbol in live_prices

    summary = summaries.get(strat_name, {})
    wins = summary.get("wins", 0)
    losses = summary.get("losses", 0)
    strat_wr = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    bt_sharpe = tiered_sharpes.get(strat_name, summary.get("tier1_sharpe", 0))

    sym_short = symbol.replace("USDT", "")
    dir_label = "LONG" if direction in ("BUY", "LONG") else "SHORT"

    if direction in ("BUY", "LONG"):
        tp_pct = ((tp / entry) - 1) * 100
        sl_pct = (1 - (sl / entry)) * 100
    else:
        tp_pct = (1 - (tp / entry)) * 100
        sl_pct = ((sl / entry) - 1) * 100

    reward = abs(tp - entry)
    risk = abs(entry - sl)
    rr = reward / risk if risk > 0 else 0

    room = room_to_tp_pct(entry, tp, current, direction)
    pnl = current_pnl_pct(entry, current, direction)

    conf_display = f"{confidence * 100:.0f}%" if confidence <= 1 else f"{confidence:.0f}%"
    record = f"({wins}W/{losses}L, {strat_wr:.0f}% WR)" if (wins + losses) > 0 else "(F)"

    # Per-direction historical performance
    strat_dirs = dir_stats.get(strat_name, {})
    dir_parts = []
    for dl in ("LONG", "SHORT"):
        ds = strat_dirs.get(dl)
        if ds and (ds["wins"] + ds["losses"] > 0):
            dw, dloss = ds["wins"], ds["losses"]
            dwr = dw / (dw + dloss) * 100
            dir_parts.append(f"{dl}: {dw}W/{dloss}L {dwr:.0f}%")
        elif ds and ds["open"] > 0:
            dir_parts.append(f"{dl}: {ds['open']} open")
    hist_line = " | ".join(dir_parts) if dir_parts else "No closed trades yet"

    display_name = short_strategy_name(strat_name)
    dir_icon = "\U0001f4c8" if dir_label == "LONG" else "\U0001f4c9"

    lines = []
    lines.append(f"{dir_icon} {sym_short} {dir_label} -- {display_name} {record}")
    lines.append(f"Entry: {fmt_price(entry, symbol)} -> TP: {fmt_price(tp, symbol)} (+{tp_pct:.1f}%)")

    price_label = "Now" if has_live else "Last"
    lines.append(f"{price_label}: {fmt_price(current, symbol)} | Room to TP: {progress_bar(room)}")
    lines.append(f"SL: {fmt_price(sl, symbol)} (-{sl_pct:.1f}%) | R:R {rr:.1f} | P/L: {pnl:+.2f}%")
    lines.append(f"  Hist: {hist_line}")
    lines.append(f"  {reason[:50]} | Conf: {conf_display} | BT Sharpe: {bt_sharpe:.1f}")
    return "\n".join(lines)


def generate_plain_messages() -> List[str]:
    """Generate a list of Discord messages (each <=2000 chars) showing ALL picks."""
    now_est = datetime.now(EST)
    timestamp = now_est.strftime("%b %d, %Y %I:%M %p EST")

    open_trades = load_open_trades()
    summaries = load_strategy_summaries()
    closed_trades = load_closed_trades()
    tiered_sharpes = load_tiered_sharpe()
    dir_stats = load_direction_stats()

    symbols = list(set(t["symbol"] for t in open_trades))
    live_prices = fetch_live_prices(symbols) if symbols else {}

    total_wins = sum(s.get("wins", 0) for s in summaries.values())
    total_losses = sum(s.get("losses", 0) for s in summaries.values())
    total_closed = total_wins + total_losses
    overall_wr = (total_wins / total_closed * 100) if total_closed > 0 else 0
    total_pnl = sum(s.get("total_pnl_pct", 0) for s in summaries.values())
    active_strategies = sum(1 for s in summaries.values() if s.get("open_trades", 0) > 0)

    # ── No picks case ────────────────────────────────────────────────
    if not open_trades:
        msg = "```\n== BABY BUNDLE -- #freshpicks ==\n"
        msg += f"Forward-Tested Baby Strategies | Live Picks\n"
        msg += f"{active_strategies} active strategies | 0 open picks\n"
        if total_closed > 0:
            msg += f"Overall: {total_wins}W/{total_losses}L ({overall_wr:.1f}% WR) | P/L: {total_pnl:+.2f}%\n"
        msg += "No active picks right now. Strategies scanning...\n```\n"
        msg += f"*{timestamp}*\n"
        msg += _disclaimer()
        return [msg]

    # ── Render each pick ─────────────────────────────────────────────
    pick_blocks = []
    for trade in open_trades:
        pick_blocks.append(_render_pick(trade, live_prices, summaries,
                                        tiered_sharpes, dir_stats))

    # ── Render closed trades block ───────────────────────────────────
    closed_block = ""
    if closed_trades:
        cl_lines = ["-- Recently Closed --"]
        for ct in closed_trades[:5]:
            sym = ct["symbol"].replace("USDT", "")
            pnl_val = ct.get("pnl_pct", 0)
            reason_label = ct.get("exit_reason", "")
            icon = "+" if pnl_val > 0 else "x"
            cl_lines.append(f"  [{icon}] {sym} {ct['direction'][:4]} {pnl_val:+.2f}% ({reason_label}) -- {short_strategy_name(ct['strategy_name'])}")
        closed_block = "\n".join(cl_lines)

    # ── Build messages that fit within Discord's 2000 char limit ─────
    LIMIT = 1900  # leave room for ``` wrapping and padding
    messages = []
    total_picks = len(pick_blocks)

    # Header for the first message
    header_lines = [
        "== BABY BUNDLE -- #freshpicks ==",
        f"Forward-Tested Baby Strategies | Live Picks",
        f"{active_strategies} active strategies | {total_picks} open picks",
    ]
    if total_closed > 0:
        header_lines.append(f"Overall: {total_wins}W/{total_losses}L ({overall_wr:.1f}% WR) | P/L: {total_pnl:+.2f}%")
    header_lines.append("-" * 50)
    header = "\n".join(header_lines)

    current_body = header
    picks_in_msg = 0
    msg_num = 1

    for i, pick in enumerate(pick_blocks):
        candidate = current_body + "\n\n" + pick if current_body else pick

        if len("```\n" + candidate + "\n```") > LIMIT and picks_in_msg > 0:
            # Flush current message
            messages.append(f"```\n{current_body}\n```")
            # Start new message with continuation header
            msg_num += 1
            cont_header = f"== #freshpicks (cont. {msg_num}) =="
            current_body = cont_header + "\n\n" + pick
            picks_in_msg = 1
        else:
            current_body = candidate
            picks_in_msg += 1

    # ── Append closed trades + footer to last message (or new msg) ──
    footer_lines = []
    if closed_block:
        footer_lines.append(closed_block)
    footer_lines.append(f"Showing all {total_picks} picks | {timestamp}")
    footer_lines.append("Room to TP = % of profit target still available")
    footer = "\n\n" + "\n".join(footer_lines)

    if len("```\n" + current_body + footer + "\n```") <= LIMIT:
        current_body += footer
        messages.append(f"```\n{current_body}\n```")
    else:
        # Flush picks, put footer in new message
        messages.append(f"```\n{current_body}\n```")
        messages.append(f"```\n{chr(10).join(footer_lines)}\n```")

    # ── Disclaimer always on the last message ────────────────────────
    messages[-1] += "\n" + _disclaimer()

    return messages


def generate_plain_message() -> str:
    """Legacy single-string output (joins all messages with separator)."""
    return "\n\n".join(generate_plain_messages())


def _disclaimer() -> str:
    """Standard disclaimer for all freshpicks messages."""
    return (
        "\n> :warning: **DISCLAIMER:** These are experimental baby strategies in "
        "forward-testing. NOT financial advice. Signals are generated by AI/algorithmic "
        "systems under evaluation. Past performance does not guarantee future results. "
        "**Do your own research (DYOR).** Paper trade only. Never risk money you can't "
        "afford to lose.\n"
        "> *Prices shown may have a delay of up to 30 min from signal generation. "
        "\"Room to TP\" shows how much of the profit target remains at current prices.*"
    )


def send_discord(webhook_url: str = None, msg: str = None) -> bool:
    """Send to Discord webhook. Uses pre-chunked messages that respect formatting."""
    if not requests:
        print("[ERROR] requests module not installed")
        return False

    webhook_url = webhook_url or WEBHOOK_URL
    if not webhook_url:
        print("[ERROR] No webhook URL. Set DISCORD_WEBHOOK_FRESHPICKS or DISCORD_WEBHOOK_URL")
        return False

    # Use properly-chunked messages (each already <=2000 chars with valid ``` blocks)
    if msg:
        chunks = [msg]  # legacy single-message path
    else:
        chunks = generate_plain_messages()

    success = True
    for i, chunk in enumerate(chunks):
        sent = False
        for _attempt in range(3):
            try:
                resp = requests.post(webhook_url, json={"content": chunk}, timeout=10)
                if resp.status_code in (200, 204):
                    sent = True
                    break
                if resp.status_code == 429:
                    time.sleep(resp.json().get("retry_after", 3))
                    continue
                if _attempt < 2:
                    time.sleep(2 * (_attempt + 1))
                    continue
                print(f"  [FreshPicks] Discord error {resp.status_code}: {resp.text[:200]}")
                break
            except Exception as e:
                if _attempt == 2:
                    print(f"  [FreshPicks] Send error after 3 attempts: {e}")
                else:
                    time.sleep(2 * (_attempt + 1))
        if not sent:
            success = False
        if i < len(chunks) - 1:
            time.sleep(0.5)  # rate limit safety

    print(f"  [FreshPicks] Sent {len(chunks)} message(s)")
    return success


# ── Discord.py bot integration ─────────────────────────────────────────────
async def fc_fresh_command(ctx):
    """Discord command handler for !fc-fresh."""
    loading = await ctx.send(":mag: Loading freshpicks...")

    messages = generate_plain_messages()
    await loading.delete()

    for msg in messages:
        await ctx.send(msg)


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--send" in args:
        print("Sending to #freshpicks...")
        if send_discord():
            print("[SUCCESS] Sent!")
        else:
            print("[FAILED] Check webhook URL")
    elif "--help" in args:
        print(__doc__)
    elif "--plain" in args:
        print(generate_plain_message())
    else:
        # Default: show plain message (ANSI may not render in all terminals)
        print(generate_plain_message())
        print("\n" + "=" * 50)
        print("Commands:")
        print("  python discord_freshpicks_baby.py --send   # Send to Discord")
        print("  python discord_freshpicks_baby.py --plain  # Plain text preview")
