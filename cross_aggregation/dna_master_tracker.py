#!/usr/bin/env python3
"""
DNA Master Picks Tracker — Forward-tracked elite consensus picks
================================================================
The "if forced to put money on the line" tier.

Features:
  - SQLite DB for all master picks with entry/exit timestamps (EST)
  - Auto-validates TP/SL against live Binance prices
  - Tracks WR, PF, avg hold time, cumulative PnL
  - Rich Discord embed with all required fields
  - Only accepts ELITE-classified picks from pick_classifier

Usage:
    python -m cross_aggregation.dna_master_tracker
"""

import json
import os
import pathlib
import sqlite3
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

import requests
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_repo_root_str = str(REPO_ROOT)
if _repo_root_str not in sys.path:
    sys.path.insert(0, _repo_root_str)
from utils.discord_format import format_confidence_breakdown
DB_PATH = REPO_ROOT / "data" / "dna_master_picks.db"
EST = timezone(timedelta(hours=-5))

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_DNA_MASTER", "")
WEBHOOK_SANDBOX = os.environ.get("DISCORD_WEBHOOK_SANDBOX", "")

# Embed colors
COLOR_GOLD = 0xFFD700
COLOR_GREEN = 0x22C55E
COLOR_RED = 0xEF4444
COLOR_PURPLE = 0x8B5CF6


def init_db():
    """Create master_picks table if not exists."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS master_picks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL NOT NULL,
            tp_price REAL NOT NULL,
            sl_price REAL NOT NULL,
            entry_time TEXT NOT NULL,
            exit_time TEXT,
            status TEXT DEFAULT 'ACTIVE',
            exit_price REAL,
            pnl_pct REAL,
            confidence REAL,
            agreement_count INTEGER,
            source_systems TEXT,
            classification TEXT DEFAULT 'ELITE',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS master_stats_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            total_picks INTEGER,
            active_picks INTEGER,
            wins INTEGER,
            losses INTEGER,
            win_rate REAL,
            profit_factor REAL,
            cumulative_pnl REAL,
            avg_hold_hours REAL
        )
    """)
    conn.commit()
    conn.close()


def migrate_add_tier():
    """Add tier column if it doesn't exist (backward-compatible migration)."""
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("ALTER TABLE master_picks ADD COLUMN tier TEXT DEFAULT 'ELITE'")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.close()


def register_elite_pick(pick: Dict) -> Optional[int]:
    """
    Register an ELITE pick for forward tracking.
    Returns the pick ID or None if duplicate.
    """
    init_db()
    conn = sqlite3.connect(str(DB_PATH))

    symbol = pick.get("symbol", "")
    direction = pick.get("direction", "")
    entry = float(pick.get("entry", 0))

    # Dedup: don't register same symbol+direction+similar entry if already active
    existing = conn.execute(
        "SELECT id FROM master_picks WHERE symbol=? AND direction=? AND status='ACTIVE' AND ABS(entry_price - ?) / entry_price < 0.005",
        (symbol, direction, entry)
    ).fetchone()
    if existing:
        conn.close()
        return None

    now_est = datetime.now(EST).strftime("%Y-%m-%d %I:%M %p EST")
    sources = json.dumps(pick.get("source_systems", []))

    cur = conn.execute(
        """INSERT INTO master_picks (symbol, direction, entry_price, tp_price, sl_price,
           entry_time, confidence, agreement_count, source_systems, classification)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (symbol, direction, entry,
         float(pick.get("tp", 0)), float(pick.get("sl", 0)),
         now_est, float(pick.get("confidence", 0)),
         int(pick.get("agreement_count", 0)), sources, "ELITE")
    )
    pick_id = cur.lastrowid
    conn.commit()
    conn.close()
    return pick_id


def register_factory_pick(pick: Dict, tier: str = "ELITE") -> Optional[int]:
    """
    Register a pick from the DNA Factory with tier classification.
    Routes to appropriate Discord channel based on tier.
    """
    migrate_add_tier()
    conn = sqlite3.connect(str(DB_PATH))

    symbol = pick.get("symbol", "")
    direction = pick.get("direction", "")
    entry = float(pick.get("entry", 0))

    # Dedup: skip if same symbol+direction+similar entry already active
    existing = conn.execute(
        "SELECT id FROM master_picks WHERE symbol=? AND direction=? AND status='ACTIVE' AND ABS(entry_price - ?) / NULLIF(entry_price, 0) < 0.005",
        (symbol, direction, entry)
    ).fetchone()
    if existing:
        conn.close()
        return None

    now_est = datetime.now(EST).strftime("%Y-%m-%d %I:%M %p EST")
    sources = json.dumps(pick.get("source_systems", []))

    cur = conn.execute(
        """INSERT INTO master_picks (symbol, direction, entry_price, tp_price, sl_price,
           entry_time, confidence, agreement_count, source_systems, classification, tier)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (symbol, direction, entry,
         float(pick.get("tp", 0)), float(pick.get("sl", 0)),
         now_est, float(pick.get("confidence", 0)),
         int(pick.get("agreement_count", 0)), sources, tier, tier)
    )
    pick_id = cur.lastrowid
    conn.commit()
    conn.close()
    return pick_id


def _get_binance_price(symbol: str) -> Optional[float]:
    """Fetch current price from Binance API (with endpoint failover)."""
    _SPOT_BASES = [
        "https://api.binance.com", "https://api1.binance.com",
        "https://data-api.binance.vision", "https://api.binance.us",
    ]
    for _base in _SPOT_BASES:
        try:
            url = f"{_base}/api/v3/ticker/price?symbol={symbol}"
            req = urllib.request.Request(url, headers={"User-Agent": "DNATracker/1.0"})
            data = json.loads(urllib.request.urlopen(req, timeout=10).read())
            return float(data["price"])
        except Exception:
            continue
    return None


def check_exits():
    """Check all active picks against live prices for TP/SL hits."""
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    active = conn.execute(
        "SELECT id, symbol, direction, entry_price, tp_price, sl_price FROM master_picks WHERE status='ACTIVE'"
    ).fetchall()

    exits = []
    for row in active:
        pick_id, symbol, direction, entry, tp, sl = row
        price = _get_binance_price(symbol)
        if price is None:
            continue

        hit = None
        if direction == "LONG":
            if price >= tp:
                hit = "WON"
                pnl = (tp / entry - 1) * 100
            elif price <= sl:
                hit = "LOST"
                pnl = (sl / entry - 1) * 100
        else:  # SHORT
            if price <= tp:
                hit = "WON"
                pnl = (1 - tp / entry) * 100
            elif price >= sl:
                hit = "LOST"
                pnl = (1 - sl / entry) * 100

        if hit:
            now_est = datetime.now(EST).strftime("%Y-%m-%d %I:%M %p EST")
            conn.execute(
                "UPDATE master_picks SET status=?, exit_time=?, exit_price=?, pnl_pct=? WHERE id=?",
                (hit, now_est, price, round(pnl, 4), pick_id)
            )
            exits.append({
                "id": pick_id, "symbol": symbol, "direction": direction,
                "status": hit, "pnl_pct": pnl, "entry": entry, "exit_price": price
            })

    conn.commit()
    conn.close()
    return exits


def get_master_stats() -> Dict:
    """Get overall master picks performance stats."""
    init_db()
    conn = sqlite3.connect(str(DB_PATH))

    total = conn.execute("SELECT COUNT(*) FROM master_picks").fetchone()[0]
    active = conn.execute("SELECT COUNT(*) FROM master_picks WHERE status='ACTIVE'").fetchone()[0]
    wins = conn.execute("SELECT COUNT(*) FROM master_picks WHERE status='WON'").fetchone()[0]
    losses = conn.execute("SELECT COUNT(*) FROM master_picks WHERE status='LOST'").fetchone()[0]

    closed = wins + losses
    wr = (wins / closed * 100) if closed else 0

    # Profit factor
    win_pnl = conn.execute("SELECT COALESCE(SUM(pnl_pct), 0) FROM master_picks WHERE status='WON'").fetchone()[0]
    loss_pnl = conn.execute("SELECT COALESCE(SUM(ABS(pnl_pct)), 0) FROM master_picks WHERE status='LOST'").fetchone()[0]
    pf = (win_pnl / loss_pnl) if loss_pnl > 0 else (99.99 if win_pnl > 0 else 0)

    cum_pnl = conn.execute("SELECT COALESCE(SUM(pnl_pct), 0) FROM master_picks WHERE status IN ('WON','LOST')").fetchone()[0]

    # Recent picks for embed
    recent = conn.execute(
        "SELECT symbol, direction, status, pnl_pct, entry_time, exit_time FROM master_picks ORDER BY id DESC LIMIT 5"
    ).fetchall()

    conn.close()
    return {
        "total": total,
        "active": active,
        "wins": wins,
        "losses": losses,
        "closed": closed,
        "win_rate": round(wr, 1),
        "profit_factor": round(min(pf, 99.99), 2),
        "cumulative_pnl": round(cum_pnl, 2),
        "recent": [
            {"symbol": r[0], "direction": r[1], "status": r[2],
             "pnl_pct": r[3], "entry_time": r[4], "exit_time": r[5]}
            for r in recent
        ],
    }


def format_discord_embed(pick: Dict, stats: Dict) -> Dict:
    """Format a DNA Master Pick as a rich Discord embed."""
    symbol = pick.get("symbol", "???")
    direction = pick.get("direction", "LONG")
    entry = pick.get("entry", 0)
    tp = pick.get("tp", 0)
    sl = pick.get("sl", 0)
    confidence = pick.get("confidence", 0)
    agreement = pick.get("agreement_count", 0)
    sources = pick.get("source_systems", [])

    tp_pct = ((tp / entry - 1) * 100) if entry and tp else 0
    sl_pct = ((1 - sl / entry) * 100) if entry and sl else 0
    rr = (tp_pct / sl_pct) if sl_pct else 0

    dir_emoji = "\U0001f7e2" if direction == "LONG" else "\U0001f534"
    conf_display = f"{confidence * 100:.0f}%" if confidence <= 1 else f"{confidence:.0f}%"
    now_est = datetime.now(EST).strftime("%Y-%m-%d %I:%M %p EST")

    # Performance stats block
    wr = stats.get("win_rate", 0)
    pf = stats.get("profit_factor", 0)
    cum_pnl = stats.get("cumulative_pnl", 0)
    closed = stats.get("closed", 0)
    active_count = stats.get("active", 0)

    if closed == 0:
        perf_line = "First DNA Master Pick! Forward tracking starts now."
    else:
        perf_line = f"**WR: {wr:.0f}%** | **PF: {pf:.1f}** | Cum PnL: {cum_pnl:+.1f}% | {closed} closed, {active_count} active"

    # Recent trades
    recent_lines = []
    for r in stats.get("recent", [])[:3]:
        icon = "\u2705" if r["status"] == "WON" else "\u274c" if r["status"] == "LOST" else "\u23f3"
        pnl = r.get("pnl_pct")
        pnl_str = f" ({pnl:+.2f}%)" if pnl else ""
        recent_lines.append(f"{icon} `{r['symbol']:12s}` {r['direction']}{pnl_str}")

    fields = [
        {"name": "Entry", "value": f"${entry:,.2f}" if entry >= 1 else f"${entry:.6f}", "inline": True},
        {"name": f"Target (+{tp_pct:.1f}%)", "value": f"${tp:,.2f}" if tp >= 1 else f"${tp:.6f}", "inline": True},
        {"name": f"Stop (-{sl_pct:.1f}%)", "value": f"${sl:,.2f}" if sl >= 1 else f"${sl:.6f}", "inline": True},
        {"name": "Confidence", "value": conf_display, "inline": True},
        {"name": "R:R Ratio", "value": f"{rr:.1f}:1", "inline": True},
        {"name": "Agreement", "value": f"{agreement} systems", "inline": True},
        {"name": "Sources", "value": ", ".join(sources[:5]) or "N/A", "inline": False},
        {"name": "\U0001f3c6 DNA Master Performance", "value": perf_line, "inline": False},
    ]

    if recent_lines:
        fields.append({"name": "Recent Master Picks", "value": "\n".join(recent_lines), "inline": False})

    # Contributing strategies (per-system breakdown)
    source_strats = pick.get("source_strategies", {})
    if source_strats:
        strat_lines = [f"`{s}` \u2192 {st}" for s, st in list(source_strats.items())[:5]]
        fields.append({
            "name": "\U0001f9ec Contributing Strategies",
            "value": "\n".join(strat_lines),
            "inline": False,
        })

    # Confidence breakdown (explains what the % means)
    cb = pick.get("confidence_breakdown")
    if cb:
        breakdown_text = format_confidence_breakdown(cb)
        if breakdown_text:
            fields.append({
                "name": "\U0001f50d Confidence Breakdown",
                "value": breakdown_text,
                "inline": False,
            })

    lead_strat = pick.get("strategy", "multi-system consensus")
    embed = {
        "title": f"\U0001f9ec DNA MASTER PICK: {dir_emoji} {direction} {symbol}",
        "color": COLOR_GOLD,
        "fields": fields,
        "description": (
            f"**Elite consensus** \u2014 {agreement} systems agree with {conf_display} confidence.\n"
            f"Lead strategy: `{lead_strat}`\n"
            f"Forward-tracked with live TP/SL validation."
        ),
        "footer": {"text": f"DNA Master Picks | {now_est} | Not financial advice"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return embed


def send_master_pick_alert(pick: Dict) -> bool:
    """Send DNA Master Pick to Discord."""
    if not WEBHOOK_URL:
        print("  [DNA Master] No DISCORD_WEBHOOK_DNA_MASTER set, skipping")
        return False

    stats = get_master_stats()
    embed = format_discord_embed(pick, stats)

    import time as _time
    for attempt in range(3):
        try:
            r = requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=10)
            if r.status_code in (200, 204):
                print(f"  [DNA Master] Sent ({r.status_code}): {pick.get('symbol')} {pick.get('direction')}")
                return True
            if r.status_code == 429:
                _time.sleep(r.json().get("retry_after", 3))
                continue
            if attempt < 2:
                _time.sleep(2 * (attempt + 1))
                continue
            print(f"  [DNA Master] Failed: {r.status_code}")
            return False
        except Exception as e:
            if attempt == 2:
                print(f"  [DNA Master] Failed after 3 attempts: {e}")
                return False
            _time.sleep(2 * (attempt + 1))
    return False


def send_exit_alert(exit_info: Dict) -> bool:
    """Send TP/SL hit alert for a master pick."""
    webhook = WEBHOOK_URL or WEBHOOK_SANDBOX
    if not webhook:
        return False

    is_win = exit_info["status"] == "WON"
    pnl = exit_info.get("pnl_pct", 0)
    emoji = "\U0001f389" if is_win else "\U0001f6a8"
    color = COLOR_GREEN if is_win else COLOR_RED

    embed = {
        "title": f"{emoji} DNA Master Pick {'TP HIT' if is_win else 'SL HIT'}: {exit_info['symbol']}",
        "color": color,
        "description": f"**{exit_info['direction']}** closed at ${exit_info.get('exit_price', 0):,.2f}\n"
                       f"Entry: ${exit_info.get('entry', 0):,.2f} → PnL: **{pnl:+.2f}%**",
        "footer": {"text": f"DNA Master Picks | {datetime.now(EST).strftime('%Y-%m-%d %I:%M %p EST')}"},
    }

    # Add updated stats
    stats = get_master_stats()
    embed["fields"] = [{
        "name": "\U0001f3c6 Updated Master Stats",
        "value": f"WR: **{stats['win_rate']:.0f}%** | PF: **{stats['profit_factor']:.1f}** | "
                 f"Cum PnL: **{stats['cumulative_pnl']:+.1f}%** | {stats['closed']} closed",
        "inline": False,
    }]

    import time as _time
    for attempt in range(3):
        try:
            r = requests.post(webhook, json={"embeds": [embed]}, timeout=10)
            if r.status_code in (200, 204):
                return True
            if r.status_code == 429:
                _time.sleep(r.json().get("retry_after", 3))
                continue
            if attempt < 2:
                _time.sleep(2 * (attempt + 1))
                continue
            return False
        except Exception:
            if attempt == 2:
                return False
            _time.sleep(2 * (attempt + 1))
    return False


if __name__ == "__main__":
    # Check exits and report
    init_db()
    exits = check_exits()
    if exits:
        for ex in exits:
            print(f"  EXIT: {ex['symbol']} {ex['direction']} → {ex['status']} ({ex['pnl_pct']:+.2f}%)")
            send_exit_alert(ex)
    else:
        print("  No exits triggered")

    stats = get_master_stats()
    print(f"\n  DNA Master Stats: {stats['closed']} closed | WR: {stats['win_rate']:.0f}% | PF: {stats['profit_factor']:.1f} | PnL: {stats['cumulative_pnl']:+.1f}%")
    print(f"  Active: {stats['active']} picks")
