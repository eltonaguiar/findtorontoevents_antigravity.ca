#!/usr/bin/env python3
"""
Discord Bot Command: !fc-baby

Baby Strategy Forward Test — Actionable Signals
Shows active picks from baby strategies with entry/TP/SL, current price,
Room to TP progress bars, and per-direction (Long/Short) historical performance.

Usage:
    python discord_baby_forward_test.py           # Preview in terminal
    python discord_baby_forward_test.py --send    # Send to Discord webhook
    python discord_baby_forward_test.py 5         # Show top 5 strategies
"""

import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    import requests
except ImportError:
    requests = None

# Paths — use absolute paths so bot can import from any CWD
REPO_ROOT = Path(__file__).resolve().parent
DB_PATH = REPO_ROOT / "incubator" / "forward_test.db"
TIERED_RESULTS = REPO_ROOT / "incubator" / "backtest_results" / "tiered_test_results.json"
BATTLEGROUND_DASHBOARD = REPO_ROOT / "battleground" / "data" / "baby_strats_dashboard.json"

EST = timezone(timedelta(hours=-5))
BINANCE_PRICE_URL = "https://api.binance.com/api/v3/ticker/price"

BAR_FILLED = "\u2588"  # █
BAR_EMPTY = "\u2591"   # ░

# Graduation criteria
GRAD_MIN_TRADES = 20
GRAD_MIN_DAYS = 30
GRAD_MIN_SHARPE = 0.8


COINGECKO_IDS = {
    "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
    "DOGEUSDT": "dogecoin", "ADAUSDT": "cardano", "DOTUSDT": "polkadot",
}


def fetch_live_prices(symbols: List[str]) -> Dict[str, float]:
    """Fetch current prices from Binance, fallback to CoinGecko."""
    if not requests or not symbols:
        return {}
    prices = {}

    # 1) Binance — individual symbol endpoint (more reliable than bulk)
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


def fmt_price(val: float) -> str:
    """Format price."""
    if val is None or val == 0:
        return "$0"
    val = float(val)
    if val >= 1000:
        return f"${val:,.2f}"
    elif val >= 1:
        return f"${val:.4f}"
    else:
        return f"${val:.6f}"


def progress_bar(pct: float, length: int = 14) -> str:
    """Build progress bar showing Room to TP."""
    pct = max(0, min(100, pct))
    filled = round(pct / 100 * length)
    empty = length - filled
    return f"{BAR_FILLED * filled}{BAR_EMPTY * empty} {pct:.1f}%"


def room_to_tp_pct(entry: float, tp: float, current: float, direction: str) -> float:
    """How much of TP move is still available (0-100%)."""
    if direction in ("BUY", "LONG"):
        total = tp - entry
        if total <= 0:
            return 0.0
        remaining = tp - current
    else:
        total = entry - tp
        if total <= 0:
            return 0.0
        remaining = current - tp
    return max(0, min(100, (remaining / total) * 100))


def current_pnl_pct(entry: float, current: float, direction: str) -> float:
    """Current unrealized P&L %."""
    if direction in ("BUY", "LONG"):
        return ((current - entry) / entry) * 100
    else:
        return ((entry - current) / entry) * 100


def format_timestamp(ts_str: str) -> str:
    """Convert timestamp to EST format."""
    if not ts_str:
        return "OPEN"
    try:
        ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        est = ts.astimezone(EST)
        return est.strftime("%m/%d %H:%M")
    except Exception:
        return str(ts_str)[:12]


def load_all_trades() -> List[Dict]:
    """Load all trades (open + closed) from forward_test.db."""
    if not DB_PATH.exists():
        return []
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='forward_signals'")
        if not cursor.fetchone():
            conn.close()
            return []
        cursor.execute("""
            SELECT id, strategy_name, symbol, direction, entry_price,
                   take_profit, stop_loss, confidence, reason, entry_time,
                   exit_time, exit_price, exit_reason, pnl_pct, status,
                   max_favorable, max_adverse
            FROM forward_signals
            ORDER BY entry_time DESC
        """)
        trades = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return trades
    except Exception:
        return []


def load_strategy_summaries() -> Dict[str, Dict]:
    """Load per-strategy summary stats."""
    summaries = {}
    if not DB_PATH.exists():
        return summaries
    try:
        conn = sqlite3.connect(str(DB_PATH))
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


def load_tiered_info() -> Dict[str, Dict]:
    """Load tiered test info (tier level, backtest stats)."""
    info = {}
    if not TIERED_RESULTS.exists():
        return info
    try:
        with open(TIERED_RESULTS, 'r') as f:
            data = json.load(f)
        tier2_full = set(data.get('tier2_full', []))
        tier2_partial = set(data.get('tier2_partial', []))
        tier1_pass = set(data.get('tier1_pass', []))
        details = data.get('details', {})

        for name in tier1_pass | tier2_full | tier2_partial:
            d = details.get(name, {})
            t1 = d.get('tier1', {})
            best = t1.get('best', {})
            if name in tier2_full:
                tier = 'TIER2_ROBUST'
            elif name in tier2_partial:
                tier = 'TIER2_PARTIAL'
            else:
                tier = 'TIER1'
            info[name] = {
                'tier': tier,
                'best_pair': t1.get('best_pair', '?'),
                'bt_sharpe': t1.get('best_sharpe', best.get('sharpe', 0)),
                'bt_wr': best.get('win_rate', 0) * 100 if best.get('win_rate', 0) <= 1 else best.get('win_rate', 0),
                'bt_max_dd': best.get('max_dd', 0),
            }
    except Exception:
        pass
    return info


def get_direction_stats(trades: List[Dict], strat_name: str) -> Dict[str, Dict]:
    """Get per-direction (LONG/SHORT) W/L record for a strategy."""
    strat_trades = [t for t in trades if t['strategy_name'] == strat_name]
    stats = {}
    for t in strat_trades:
        dir_label = "LONG" if t['direction'] in ("BUY", "LONG") else "SHORT"
        if dir_label not in stats:
            stats[dir_label] = {"wins": 0, "losses": 0, "open": 0, "pnl": 0}
        if t['status'] == 'CLOSED':
            if (t.get('pnl_pct') or 0) > 0:
                stats[dir_label]["wins"] += 1
            else:
                stats[dir_label]["losses"] += 1
            stats[dir_label]["pnl"] += (t.get('pnl_pct') or 0)
        else:
            stats[dir_label]["open"] += 1
    return stats


def _render_strat_block(name: str, picks: List[Dict], live_prices: Dict,
                        summaries: Dict, tiered_info: Dict,
                        all_trades: List[Dict]) -> str:
    """Render a single strategy block (header + picks) as plain text."""
    s = summaries.get(name, {})
    ti = tiered_info.get(name, {})
    dir_stats = get_direction_stats(all_trades, name)

    tier = ti.get('tier', 'TIER1')
    wins = s.get('wins', 0)
    losses = s.get('losses', 0)
    fw_closed = wins + losses

    if fw_closed >= GRAD_MIN_TRADES and s.get('sharpe', 0) >= GRAD_MIN_SHARPE:
        badge = "GRAD"
    elif tier == 'TIER2_ROBUST':
        badge = "T2"
    elif tier == 'TIER2_PARTIAL':
        badge = "T2p"
    else:
        badge = "T1"

    display_name = name
    for suffix in ("Strategy", "Strat"):
        if display_name.endswith(suffix):
            display_name = display_name[:-len(suffix)]

    dir_parts = []
    for dl in ("LONG", "SHORT"):
        ds = dir_stats.get(dl)
        if ds:
            dw, dloss = ds["wins"], ds["losses"]
            if dw + dloss > 0:
                dwr = dw / (dw + dloss) * 100
                dpnl = ds["pnl"]
                dir_parts.append(f"{dl}: {dw}W/{dloss}L {dwr:.0f}% ({dpnl:+.1f}%)")
            elif ds["open"] > 0:
                dir_parts.append(f"{dl}: {ds['open']} open")
    hist_str = " | ".join(dir_parts) if dir_parts else "New -- no closed trades"

    lines = []
    lines.append(f"[{badge}] {display_name} (BT Sharpe: {ti.get('bt_sharpe', 0):.1f})")
    lines.append(f"  Hist: {hist_str}")

    for t in picks:
        symbol = t['symbol']
        direction = t['direction']
        entry = t['entry_price']
        tp = t['take_profit']
        sl = t['stop_loss']
        confidence = t.get('confidence', 0)

        current = live_prices.get(symbol, entry)
        has_live = symbol in live_prices

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

        conf_str = f"{confidence * 100:.0f}%" if confidence <= 1 else f"{confidence:.0f}%"
        price_label = "Now" if has_live else "Last"

        dir_arrow = "\u25b2" if dir_label == "LONG" else "\u25bc"
        lines.append(f"  {dir_arrow} {sym_short} {dir_label} | Entry: {fmt_price(entry)} -> TP: {fmt_price(tp)} (+{tp_pct:.1f}%)")
        lines.append(f"    {price_label}: {fmt_price(current)} | Room to TP: {progress_bar(room)}")
        lines.append(f"    SL: {fmt_price(sl)} (-{sl_pct:.1f}%) | R:R {rr:.1f} | P/L: {pnl:+.2f}% | Conf: {conf_str}")

    return "\n".join(lines)


def generate_messages() -> List[str]:
    """Generate list of Discord messages (each <=2000 chars) showing ALL picks."""
    now_est = datetime.now(EST)
    timestamp = now_est.strftime("%b %d, %Y %I:%M %p EST")

    all_trades = load_all_trades()
    summaries = load_strategy_summaries()
    tiered_info = load_tiered_info()

    open_trades = [t for t in all_trades if t['status'] == 'OPEN']
    closed_trades = [t for t in all_trades if t['status'] == 'CLOSED']
    symbols = list(set(t['symbol'] for t in open_trades))
    live_prices = fetch_live_prices(symbols) if symbols else {}

    total_wins = len([t for t in closed_trades if (t.get('pnl_pct') or 0) > 0])
    total_losses = len(closed_trades) - total_wins
    total_closed = len(closed_trades)
    overall_wr = (total_wins / total_closed * 100) if total_closed > 0 else 0
    total_pnl = sum(t.get('pnl_pct', 0) or 0 for t in closed_trades)

    # Group open trades by strategy
    strats_with_picks = {}
    for t in open_trades:
        name = t['strategy_name']
        if name not in strats_with_picks:
            strats_with_picks[name] = []
        strats_with_picks[name].append(t)

    strat_order = []
    for name in strats_with_picks:
        s = summaries.get(name, {})
        ti = tiered_info.get(name, {})
        strat_order.append((name, s.get('total_signals', 0), ti.get('bt_sharpe', 0)))
    strat_order.sort(key=lambda x: (-x[1], -x[2]))

    if not strat_order and not closed_trades:
        msg = f"```\n[BABY STRAT] Forward Test\n{timestamp}\n\n"
        msg += f"No active picks or closed trades yet.\n"
        msg += f"Forward scanner runs every 30 min.\n"
        msg += f"Tracking {len(summaries)} strategies across BTC/ETH/SOL.\n```\n"
        msg += "> :warning: *Not financial advice -- DYOR*"
        return [msg]

    # ── Render all strategy blocks ───────────────────────────────────
    strat_blocks = []
    for name, sig_count, bt_sharpe in strat_order:
        picks = strats_with_picks[name]
        block = _render_strat_block(name, picks, live_prices, summaries,
                                    tiered_info, all_trades)
        strat_blocks.append(block)

    # ── Render closed trades block ───────────────────────────────────
    closed_block = ""
    if closed_trades:
        cl_lines = ["-" * 50, "RECENTLY CLOSED:"]
        for ct in closed_trades[:5]:
            sym = ct['symbol'].replace("USDT", "")
            direction = ct['direction']
            dir_label = "LONG" if direction in ("BUY", "LONG") else "SHORT"
            pnl_val = ct.get('pnl_pct', 0) or 0
            reason_label = ct.get('exit_reason', '')
            entry_p = fmt_price(ct['entry_price'])
            exit_p = fmt_price(ct.get('exit_price', 0))
            icon = "+" if pnl_val > 0 else "x"
            strat_short = ct['strategy_name']
            for suffix in ("Strategy", "Strat"):
                if strat_short.endswith(suffix):
                    strat_short = strat_short[:-len(suffix)]
            cl_lines.append(f"  [{icon}] {sym} {dir_label} {entry_p}->{exit_p} {pnl_val:+.2f}% ({reason_label}) {strat_short}")
        closed_block = "\n".join(cl_lines)

    # ── Build messages within Discord's 2000 char limit ──────────────
    LIMIT = 1900
    messages = []
    total_picks = len(open_trades)
    total_strats = len(strat_blocks)

    header_lines = [
        f"[BABY STRAT] Forward Test -- Active Picks",
        f"{timestamp}",
        f"{total_picks} open picks | {total_closed} closed | {total_strats} active strategies",
    ]
    if total_closed > 0:
        header_lines.append(f"Overall: {total_wins}W/{total_losses}L ({overall_wr:.0f}% WR) | Net P/L: {total_pnl:+.2f}%")
    header_lines.append("-" * 50)
    header = "\n".join(header_lines)

    current_body = header
    strats_in_msg = 0
    msg_num = 1

    for block in strat_blocks:
        candidate = current_body + "\n\n" + block

        if len("```\n" + candidate + "\n```") > LIMIT and strats_in_msg > 0:
            messages.append(f"```\n{current_body}\n```")
            msg_num += 1
            cont_header = f"[BABY STRAT] (cont. {msg_num})"
            current_body = cont_header + "\n\n" + block
            strats_in_msg = 1
        else:
            current_body = candidate
            strats_in_msg += 1

    # ── Append closed + footer ───────────────────────────────────────
    footer_lines = []
    if closed_block:
        footer_lines.append(closed_block)
    footer_lines.append(f"\nShowing all {total_strats} strategies, {total_picks} picks | {timestamp}")
    footer_lines.append("Room to TP = % of profit still available")
    footer = "\n\n" + "\n".join(footer_lines) if footer_lines else ""

    if len("```\n" + current_body + footer + "\n```") <= LIMIT:
        current_body += footer
        messages.append(f"```\n{current_body}\n```")
    else:
        messages.append(f"```\n{current_body}\n```")
        messages.append(f"```\n{chr(10).join(footer_lines)}\n```")

    # Disclaimer on last message
    disclaimer = ("\n> :warning: **DISCLAIMER:** Experimental AI strategies in forward-testing. "
                  "NOT financial advice. DYOR. Paper trade only.")
    messages[-1] += disclaimer

    return messages


def generate_message(top_n: int = 999) -> str:
    """Legacy single-string output (joins all messages)."""
    return "\n\n".join(generate_messages())


def send_discord(webhook_url: str = None, msg: str = None) -> bool:
    """Send to Discord webhook using pre-chunked messages."""
    if not requests:
        return False
    webhook_url = webhook_url or os.getenv('DISCORD_BABY_WEBHOOK') or os.getenv('DISCORD_WEBHOOK_URL')

    if not webhook_url:
        print("[ERROR] No webhook URL. Set DISCORD_BABY_WEBHOOK")
        print("\n" + generate_message())
        return False

    chunks = [msg] if msg else generate_messages()

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
                print(f"Discord error: {resp.status_code}")
                break
            except Exception as e:
                if _attempt == 2:
                    print(f"Send error after 3 attempts: {e}")
                else:
                    time.sleep(2 * (_attempt + 1))
        if not sent:
            success = False
        if i < len(chunks) - 1:
            time.sleep(0.5)

    print(f"  [fc-baby] Sent {len(chunks)} message(s)")
    return success


# Discord.py integration
async def fc_baby_command(ctx, n: str = "all"):
    """Discord command handler for !fc-baby."""
    loading = await ctx.send(":mag: Loading baby strat data...")

    messages = generate_messages()
    await loading.delete()

    for msg in messages:
        await ctx.send(msg)


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--send" in args:
        print("Sending to Discord...")
        if send_discord():
            print("[SUCCESS] Sent!")
        else:
            print("[FAILED]")
    elif "--help" in args:
        print(__doc__)
    elif args and args[0].isdigit():
        print(generate_message(int(args[0])))
    else:
        print(generate_message())
