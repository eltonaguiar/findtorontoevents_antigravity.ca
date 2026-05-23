#!/usr/bin/env python3
"""
Symbol Consensus Lookup Tool
-----------------------------
Query any crypto/asset symbol across ALL trading systems to see the consensus view.

Usage:
    python tools/symbol_lookup.py BTCUSDT
    python tools/symbol_lookup.py BTC
    python tools/symbol_lookup.py --all
"""

import argparse
import io
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 output on Windows (cp1252 can't handle box-drawing chars)
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package required. Install with: pip install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent

SYMBOL_ALIASES = {
    "BTC": "BTCUSDT", "BITCOIN": "BTCUSDT", "BTC-USD": "BTCUSDT", "BTCUSD": "BTCUSDT",
    "ETH": "ETHUSDT", "ETHEREUM": "ETHUSDT", "ETH-USD": "ETHUSDT", "ETHUSD": "ETHUSDT",
    "SOL": "SOLUSDT", "SOLANA": "SOLUSDT", "SOL-USD": "SOLUSDT",
    "BNB": "BNBUSDT", "BNB-USD": "BNBUSDT",
    "XRP": "XRPUSDT", "XRP-USD": "XRPUSDT",
    "DOGE": "DOGEUSDT", "DOGE-USD": "DOGEUSDT", "DOGECOIN": "DOGEUSDT",
    "ADA": "ADAUSDT", "ADA-USD": "ADAUSDT", "CARDANO": "ADAUSDT",
    "AVAX": "AVAXUSDT", "AVAX-USD": "AVAXUSDT",
    "LINK": "LINKUSDT", "LINK-USD": "LINKUSDT",
    "DOT": "DOTUSDT", "DOT-USD": "DOTUSDT", "POLKADOT": "DOTUSDT",
    "SHIB": "SHIBUSDT", "SHIB-USD": "SHIBUSDT",
    "SUI": "SUIUSDT", "SUI-USD": "SUIUSDT",
    "ARB": "ARBUSDT", "ARB-USD": "ARBUSDT",
    "OP": "OPUSDT", "OP-USD": "OPUSDT",
    "INJ": "INJUSDT", "INJ-USD": "INJUSDT",
    "NEAR": "NEARUSDT", "NEAR-USD": "NEARUSDT",
    "RENDER": "RENDERUSDT", "RENDER-USD": "RENDERUSDT",
    "TAO": "TAOUSDT", "TAO-USD": "TAOUSDT",
    "FET": "FETUSDT", "FET-USD": "FETUSDT",
    "AAVE": "AAVEUSDT", "AAVE-USD": "AAVEUSDT",
    "TRX": "TRXUSDT", "TRX-USD": "TRXUSDT",
    "PEPE": "PEPEUSDT", "PEPE-USD": "PEPEUSDT",
    "WIF": "WIFUSDT", "MATIC": "MATICUSDT", "POL": "POLUSDT",
    "ATOM": "ATOMUSDT", "FIL": "FILUSDT", "APT": "APTUSDT",
    "LTC": "LTCUSDT", "UNI": "UNIUSDT", "HBAR": "HBARUSDT",
}

# Each entry: (system_name, active_picks_path, closed_picks_path)
SYSTEM_PATHS = [
    ("Mercury 2",        "mercury2/data/active_picks.json",                    "mercury2/data/closed_picks.json"),
    ("Alpha Engine",     "alpha_engine/data/active_picks.json",                "alpha_engine/data/closed_picks.json"),
    ("KIMI Claw",        "KIMI_RISEOFTHECLAW/data/active_picks.json",          "KIMI_RISEOFTHECLAW/data/closed_picks.json"),
    ("Crypto Signal",    "crypto_signal_engine/data/active_picks.json",        "crypto_signal_engine/data/closed_picks.json"),
    ("ML Edge",          "crypto_ml_edge/data/active_picks.json",              "crypto_ml_edge/data/closed_picks.json"),
    ("ML-A Filter",      "ml_battleground/system_a_filter/data/active_picks.json",  "ml_battleground/system_a_filter/data/closed_picks.json"),
    ("ML-B Regime",      "ml_battleground/system_b_regime/data/active_picks.json",  "ml_battleground/system_b_regime/data/closed_picks.json"),
    ("ML-D Carry",       "ml_battleground/system_d_carry/data/active_picks.json",   "ml_battleground/system_d_carry/data/closed_picks.json"),
    ("ML-E Momentum",    "ml_battleground/system_e_momentum/data/active_picks.json","ml_battleground/system_e_momentum/data/closed_picks.json"),
    ("Claude Gainer",    "claude_gainer_ml/tracker/claude_live_picks.json",    None),
    ("Cross Aggregator", "data/aggregated_picks.json",                         None),
    # Additional systems found on disk
    ("ML-C DeepLearn",   "ml_battleground/system_c_deeplearn/data/active_picks.json", "ml_battleground/system_c_deeplearn/data/closed_picks.json"),
    ("ML-F ClawsDoom",   "ml_battleground/system_f_clawsofdoom/data/active_picks.json", "ml_battleground/system_f_clawsofdoom/data/closed_picks.json"),
    ("Breakout SR",      "breakout_arena/approach_a_sr_breakout/data/active_picks.json", "breakout_arena/approach_a_sr_breakout/data/closed_picks.json"),
    ("Breakout ML",      "breakout_arena/approach_b_ml_breakout/data/active_picks.json", "breakout_arena/approach_b_ml_breakout/data/closed_picks.json"),
    ("Breakout Spike",   "breakout_arena/approach_c_spike_reverse/data/active_picks.json", "breakout_arena/approach_c_spike_reverse/data/closed_picks.json"),
]


# ---------------------------------------------------------------------------
# Symbol normalization
# ---------------------------------------------------------------------------

def normalize_symbol(raw: str) -> str:
    """Normalize any symbol variant to XXXUSDT format."""
    upper = raw.upper().strip()
    # Direct alias match
    if upper in SYMBOL_ALIASES:
        return SYMBOL_ALIASES[upper]
    # Already ends with USDT
    if upper.endswith("USDT"):
        return upper
    # Strip common suffixes and re-check
    for suffix in ["-USD", "-USDT", "USD"]:
        if upper.endswith(suffix):
            base = upper[: -len(suffix)]
            if base in SYMBOL_ALIASES:
                return SYMBOL_ALIASES[base]
            return base + "USDT"
    # Default: append USDT
    return upper + "USDT"


def symbol_matches(pick_symbol: str, target: str) -> bool:
    """Check if a pick's symbol matches our normalized target."""
    return normalize_symbol(pick_symbol) == target


# ---------------------------------------------------------------------------
# Data loaders (handle all known formats)
# ---------------------------------------------------------------------------

def load_json(path: Path):
    """Load a JSON file, return None on error."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def extract_picks_list(data, system_name: str):
    """
    Different systems store picks in different structures.
    Returns a flat list of pick dicts.
    """
    if data is None:
        return []
    # Plain list
    if isinstance(data, list):
        return data
    # KIMI format: {"activePicks": [...]} or {"closedPicks": [...]}
    if isinstance(data, dict):
        for key in ("activePicks", "picks", "closedPicks", "closed"):
            if key in data and isinstance(data[key], list):
                return data[key]
        # Maybe a single pick dict
        if "symbol" in data:
            return [data]
    return []


def extract_direction(pick: dict) -> str:
    """Normalize direction/signal to LONG or SHORT."""
    for key in ("direction", "signal", "signal_type"):
        val = str(pick.get(key, "")).upper()
        if val in ("LONG", "BUY"):
            return "LONG"
        if val in ("SHORT", "SELL"):
            return "SHORT"
    return "UNKNOWN"


def extract_entry(pick: dict) -> float | None:
    for key in ("entry_price", "entryPrice"):
        v = pick.get(key)
        if v is not None:
            try:
                return float(v)
            except (ValueError, TypeError):
                pass
    return None


def extract_tp(pick: dict) -> float | None:
    for key in ("take_profit", "targetPrice", "tp_price", "tp1_price"):
        v = pick.get(key)
        if v is not None:
            try:
                return float(v)
            except (ValueError, TypeError):
                pass
    return None


def extract_sl(pick: dict) -> float | None:
    for key in ("stop_loss", "stopPrice", "sl_price"):
        v = pick.get(key)
        if v is not None:
            try:
                return float(v)
            except (ValueError, TypeError):
                pass
    return None


def extract_confidence(pick: dict) -> float | None:
    for key in ("confidence", "confluence_score", "ml_score"):
        v = pick.get(key)
        if v is not None:
            try:
                val = float(v)
                # Some systems use 0-100, normalize to 0-1
                if val > 1.0:
                    val = val / 100.0
                return val
            except (ValueError, TypeError):
                pass
    return None


def extract_pnl(pick: dict) -> float | None:
    for key in ("realized_pnl_pct", "pnl_pct", "pnl"):
        v = pick.get(key)
        if v is not None:
            try:
                return float(v)
            except (ValueError, TypeError):
                pass
    return None


def extract_status(pick: dict) -> str:
    val = str(pick.get("status", "")).upper()
    if val in ("WIN", "TP", "WON"):
        return "WIN"
    if val in ("LOSS", "SL", "LOST", "STOPPED"):
        return "LOSS"
    if val in ("ACTIVE", "OPEN"):
        return "ACTIVE"
    if val in ("EXPIRED", "TIMEOUT", "TIME_EXIT"):
        return "EXPIRED"
    return val or "UNKNOWN"


# ---------------------------------------------------------------------------
# Market data
# ---------------------------------------------------------------------------

def fetch_binance_price(symbol: str) -> float | None:
    """Fetch live price from Binance public API."""
    try:
        resp = requests.get(
            f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}",
            timeout=5,
        )
        if resp.status_code == 200:
            return float(resp.json()["price"])
    except Exception:
        pass
    return None


def fetch_fear_greed() -> tuple:
    """Fetch Fear & Greed index. Returns (value, label) or (None, None)."""
    try:
        resp = requests.get(
            "https://api.alternative.me/fng/?limit=1", timeout=5
        )
        if resp.status_code == 200:
            d = resp.json()["data"][0]
            return int(d["value"]), d["value_classification"]
    except Exception:
        pass
    return None, None


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def fmt_price(price: float | None) -> str:
    if price is None:
        return "N/A"
    if price < 0.0001:
        return f"${price:.8f}"
    if price < 1:
        return f"${price:.6f}"
    if price < 100:
        return f"${price:,.4f}"
    return f"${price:,.2f}"


def fmt_pct(val: float | None) -> str:
    if val is None:
        return "N/A"
    if abs(val) < 0.005:
        return "0.00%"
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.2f}%"


def fmt_conf(val: float | None) -> str:
    if val is None:
        return "N/A"
    return f"{val:.2f}"


def make_bar(pct: float, width: int = 10) -> str:
    filled = max(0, min(width, round(pct / 100.0 * width)))
    return "\u2588" * filled + "\u2591" * (width - filled)


def pad(text: str, width: int) -> str:
    """Left-align text within width."""
    return text[:width].ljust(width)


def table_row(cols: list[tuple[str, int]], sep: str = "\u2502") -> str:
    parts = [f" {pad(text, w)} " for text, w in cols]
    return sep + sep.join(parts) + sep


def table_header(cols: list[tuple[str, int]]) -> tuple[str, str, str]:
    top = "\u250c" + "\u252c".join("\u2500" * (w + 2) for _, w in cols) + "\u2510"
    mid = "\u251c" + "\u253c".join("\u2500" * (w + 2) for _, w in cols) + "\u2524"
    bot = "\u2514" + "\u2534".join("\u2500" * (w + 2) for _, w in cols) + "\u2518"
    return top, mid, bot


# ---------------------------------------------------------------------------
# Core scanning
# ---------------------------------------------------------------------------

def scan_active_picks(target_symbol: str) -> list[dict]:
    """Scan all systems for active picks matching the symbol."""
    results = []
    for sys_name, active_path, _closed_path in SYSTEM_PATHS:
        full_path = REPO_ROOT / active_path
        data = load_json(full_path)
        picks = extract_picks_list(data, sys_name)
        for pick in picks:
            sym = pick.get("symbol") or pick.get("pair", "")
            if symbol_matches(sym, target_symbol):
                status = extract_status(pick)
                if status in ("ACTIVE", "OPEN", "UNKNOWN"):
                    results.append({
                        "system": sys_name,
                        "direction": extract_direction(pick),
                        "entry": extract_entry(pick),
                        "tp": extract_tp(pick),
                        "sl": extract_sl(pick),
                        "confidence": extract_confidence(pick),
                        "strategy": pick.get("strategy", pick.get("algorithm", "N/A")),
                        "timestamp": pick.get("timestamp", pick.get("entryDate", "")),
                        "unrealized_pnl": pick.get("unrealized_pnl_pct"),
                    })
    return results


def scan_closed_picks(target_symbol: str) -> list[dict]:
    """Scan all systems for closed/historical picks matching the symbol."""
    results = []
    for sys_name, _active_path, closed_path in SYSTEM_PATHS:
        if closed_path is None:
            continue
        full_path = REPO_ROOT / closed_path
        data = load_json(full_path)
        picks = extract_picks_list(data, sys_name)
        for pick in picks:
            sym = pick.get("symbol") or pick.get("pair", "")
            if symbol_matches(sym, target_symbol):
                results.append({
                    "system": sys_name,
                    "status": extract_status(pick),
                    "pnl": extract_pnl(pick),
                    "entry": extract_entry(pick),
                    "exit_price": pick.get("exit_price"),
                    "direction": extract_direction(pick),
                })
    return results


def compute_historical_stats(closed: list[dict]) -> dict[str, dict]:
    """Group closed picks by system and compute stats."""
    by_system = {}
    for pick in closed:
        sys = pick["system"]
        if sys not in by_system:
            by_system[sys] = []
        by_system[sys].append(pick)

    stats = {}
    for sys, picks in by_system.items():
        total = len(picks)
        wins = sum(1 for p in picks if p["status"] == "WIN")
        pnls = [p["pnl"] for p in picks if p["pnl"] is not None]
        avg_pnl = sum(pnls) / len(pnls) if pnls else None
        # Simple Sharpe approximation: mean / std of pnl
        sharpe = None
        if len(pnls) >= 2:
            mean_pnl = sum(pnls) / len(pnls)
            var = sum((x - mean_pnl) ** 2 for x in pnls) / (len(pnls) - 1)
            std = math.sqrt(var) if var > 0 else 0
            sharpe = round(mean_pnl / std, 2) if std > 0 else None
        stats[sys] = {
            "trades": total,
            "wins": wins,
            "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
            "avg_pnl": round(avg_pnl, 2) if avg_pnl is not None else None,
            "sharpe": sharpe,
        }
    return stats


def compute_consensus(active: list[dict]) -> tuple[str, float, str]:
    """Compute consensus label, strength %, and emoji."""
    longs = sum(1 for p in active if p["direction"] == "LONG")
    shorts = sum(1 for p in active if p["direction"] == "SHORT")
    total = longs + shorts

    if total == 0:
        return "NO ACTIVE PICKS", 0, "\u26aa"

    strength = max(longs, shorts) / total * 100

    if longs >= 3 and shorts == 0:
        return "STRONG BUY", strength, "\U0001f7e2"
    if longs >= 2 and shorts <= 1:
        return "BUY", strength, "\U0001f7e2"
    if shorts >= 3 and longs == 0:
        return "STRONG SELL", strength, "\U0001f534"
    if shorts >= 2 and longs <= 1:
        return "SELL", strength, "\U0001f534"
    return "NEUTRAL", 50, "\U0001f7e1"


# ---------------------------------------------------------------------------
# All-symbols mode
# ---------------------------------------------------------------------------

def scan_all_symbols() -> dict[str, list[dict]]:
    """Find every symbol with active picks across all systems."""
    symbol_map = {}
    for sys_name, active_path, _closed_path in SYSTEM_PATHS:
        full_path = REPO_ROOT / active_path
        data = load_json(full_path)
        picks = extract_picks_list(data, sys_name)
        for pick in picks:
            sym = pick.get("symbol") or pick.get("pair", "")
            if not sym:
                continue
            normalized = normalize_symbol(sym)
            status = extract_status(pick)
            if status not in ("ACTIVE", "OPEN", "UNKNOWN"):
                continue
            if normalized not in symbol_map:
                symbol_map[normalized] = []
            symbol_map[normalized].append({
                "system": sys_name,
                "direction": extract_direction(pick),
                "confidence": extract_confidence(pick),
            })
    return symbol_map


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_symbol_report(symbol: str, active: list[dict], closed: list[dict],
                        live_price: float | None, fng_val, fng_label: str):
    sep = "\u2550" * 59
    price_str = fmt_price(live_price) if live_price else "N/A"
    fng_str = f"{fng_val} ({fng_label})" if fng_val is not None else "N/A"

    print()
    print(f"  {sep}")
    print(f"    SYMBOL CONSENSUS REPORT: {symbol}")
    print(f"    Live Price: {price_str} | F&G: {fng_str}")
    print(f"  {sep}")
    print()

    # -- Active picks table --
    if active:
        cols = [("System", 17), ("Direction", 9), ("Entry", 12), ("TP", 12), ("SL", 12), ("Conf", 6)]
        top, mid, bot = table_header(cols)

        print(f"  ACTIVE PICKS (across all systems):")
        print(f"  {top}")
        print(f"  {table_row([(n, w) for n, w in cols])}")
        print(f"  {mid}")
        for pick in active:
            row = [
                (pick["system"], 17),
                (pick["direction"], 9),
                (fmt_price(pick["entry"]), 12),
                (fmt_price(pick["tp"]), 12),
                (fmt_price(pick["sl"]), 12),
                (fmt_conf(pick["confidence"]), 6),
            ]
            print(f"  {table_row(row)}")
        print(f"  {bot}")
        print()

        # Consensus
        label, strength, emoji = compute_consensus(active)
        longs = sum(1 for p in active if p["direction"] == "LONG")
        shorts = sum(1 for p in active if p["direction"] == "SHORT")
        bar = make_bar(strength)
        print(f"  CONSENSUS: {emoji} {label} ({longs} LONG, {shorts} SHORT across {len(active)} picks)")
        print(f"  Signal Strength: {bar} {strength:.0f}%")
        print()
    else:
        print("  No active picks found for this symbol across any system.")
        print()

    # -- Historical performance --
    hist_stats = compute_historical_stats(closed)
    if hist_stats:
        cols = [("System", 17), ("Trades", 6), ("Win Rate", 8), ("Avg PnL", 9), ("Sharpe", 6)]
        top, mid, bot = table_header(cols)

        print(f"  HISTORICAL PERFORMANCE (closed picks):")
        print(f"  {top}")
        print(f"  {table_row([(n, w) for n, w in cols])}")
        print(f"  {mid}")
        for sys_name, st in hist_stats.items():
            row = [
                (sys_name, 17),
                (str(st["trades"]), 6),
                (f"{st['win_rate']}%", 8),
                (fmt_pct(st["avg_pnl"]), 9),
                (str(st["sharpe"]) if st["sharpe"] is not None else "N/A", 6),
            ]
            print(f"  {table_row(row)}")
        print(f"  {bot}")
        print()
    else:
        print("  No closed/historical picks found for this symbol.")
        print()

    # -- Unrealized P&L --
    if active and live_price is not None:
        has_pnl = False
        for pick in active:
            entry = pick["entry"]
            if entry is None or entry == 0:
                continue
            if not has_pnl:
                print("  CURRENT UNREALIZED P&L:")
                has_pnl = True
            if pick["direction"] == "LONG":
                pnl = (live_price - entry) / entry * 100
            elif pick["direction"] == "SHORT":
                pnl = (entry - live_price) / entry * 100
            else:
                pnl = 0
            arrow = "\u2191" if pnl >= 0 else "\u2193"
            print(f"  {pick['system']}: {pick['direction']} @ {fmt_price(entry)} -> now {fmt_price(live_price)} ({fmt_pct(pnl)} {arrow})")
        if has_pnl:
            print()

    print(f"  {sep}")
    print()


def print_all_symbols_report(symbol_map: dict, fng_val, fng_label: str):
    sep = "\u2550" * 75
    fng_str = f"{fng_val} ({fng_label})" if fng_val is not None else "N/A"

    print()
    print(f"  {sep}")
    print(f"    ALL ACTIVE SYMBOLS ACROSS SYSTEMS | F&G: {fng_str}")
    print(f"  {sep}")
    print()

    cols = [("Symbol", 14), ("Systems", 7), ("LONG", 5), ("SHORT", 5), ("Consensus", 18), ("Strength", 8)]
    top, mid, bot = table_header(cols)
    print(f"  {top}")
    print(f"  {table_row([(n, w) for n, w in cols])}")
    print(f"  {mid}")

    # Sort by number of systems (most coverage first)
    for sym in sorted(symbol_map, key=lambda s: len(symbol_map[s]), reverse=True):
        picks = symbol_map[sym]
        longs = sum(1 for p in picks if p["direction"] == "LONG")
        shorts = sum(1 for p in picks if p["direction"] == "SHORT")
        label, strength, emoji = compute_consensus(picks)
        row = [
            (sym, 14),
            (str(len(picks)), 7),
            (str(longs), 5),
            (str(shorts), 5),
            (f"{emoji} {label}", 18),
            (f"{strength:.0f}%", 8),
        ]
        print(f"  {table_row(row)}")

    print(f"  {bot}")
    print()
    print(f"  Total: {len(symbol_map)} symbols with active picks across {sum(len(v) for v in symbol_map.values())} positions")
    print()


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------

def export_json(symbol: str, active: list[dict], closed: list[dict],
                live_price: float | None, fng_val, fng_label: str,
                hist_stats: dict):
    """Save structured JSON report for programmatic use."""
    label, strength, _ = compute_consensus(active)
    longs = sum(1 for p in active if p["direction"] == "LONG")
    shorts = sum(1 for p in active if p["direction"] == "SHORT")

    report = {
        "symbol": symbol,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "live_price": live_price,
        "fear_greed": {"value": fng_val, "label": fng_label},
        "consensus": {
            "label": label,
            "strength_pct": round(strength, 1),
            "longs": longs,
            "shorts": shorts,
            "total_active": len(active),
        },
        "active_picks": active,
        "historical_stats": hist_stats,
    }

    out_dir = REPO_ROOT / "portfolio_tracker" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"symbol_report_{symbol}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"  JSON report saved: {out_path}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Symbol Consensus Lookup - query any symbol across all trading systems"
    )
    parser.add_argument(
        "symbol",
        nargs="?",
        default=None,
        help="Symbol to look up (e.g., BTC, BTCUSDT, ETH-USD)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Show all symbols with active picks across all systems",
    )
    parser.add_argument(
        "--no-json",
        action="store_true",
        help="Skip JSON export",
    )

    args = parser.parse_args()

    if not args.symbol and not args.all:
        parser.print_help()
        sys.exit(1)

    # Fetch market data once
    fng_val, fng_label = fetch_fear_greed()

    if args.all:
        symbol_map = scan_all_symbols()
        if not symbol_map:
            print("\n  No active picks found in any system.\n")
            return
        print_all_symbols_report(symbol_map, fng_val, fng_label)
        return

    # Single symbol lookup
    target = normalize_symbol(args.symbol)
    live_price = fetch_binance_price(target)

    active = scan_active_picks(target)
    closed = scan_closed_picks(target)

    print_symbol_report(target, active, closed, live_price, fng_val, fng_label)

    hist_stats = compute_historical_stats(closed)
    if not args.no_json:
        export_json(target, active, closed, live_price, fng_val, fng_label, hist_stats)


if __name__ == "__main__":
    main()
