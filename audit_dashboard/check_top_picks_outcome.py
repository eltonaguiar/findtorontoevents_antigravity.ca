#!/usr/bin/env python3
"""
Claude Top Picks — 24h Outcome Checker
Fetches live Binance prices, checks TP/SL hits, updates claude_top_picks.json.
Runs every scan cycle via GitHub Actions (momentum-scanner.yml).
Also checks genome/data/momentum_scalp_picks.json and tracked_live_picks.json.
"""
import json, os, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import urllib.request
except ImportError:
    print("ERROR: urllib not available")
    sys.exit(1)

# Dynamic import of alpha_engine failover (5-source chain)
_failover_price = None
try:
    import importlib, types
    _ae_path = Path(__file__).resolve().parent.parent / "alpha_engine" / "api_failover.py"
    if _ae_path.exists():
        spec = importlib.util.spec_from_file_location("api_failover", str(_ae_path))
        _mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_mod)
        _failover_price = getattr(_mod, "fetch_price", None)
        if _failover_price:
            print("INFO: api_failover loaded — using 5-source price chain")
except Exception as _e:
    print(f"WARNING: api_failover import failed ({_e}), falling back to Binance-only")

# Optional yfinance for forex symbols
_yf_download = None
try:
    import yfinance as _yf
    _yf_download = _yf.download
    print("INFO: yfinance available for forex fallback")
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
TOP_PICKS_PATH = Path(__file__).resolve().parent / "data" / "claude_top_picks.json"
MOMENTUM_PATH = ROOT / "genome" / "data" / "momentum_scalp_picks.json"
TRACKED_PATH = ROOT / "genome" / "data" / "tracked_live_picks.json"

_BINANCE_SPOT_BASES = [
    "https://api.binance.com",
    "https://api.binance.us",
    "https://data-api.binance.vision",
]


def _is_forex_symbol(sym):
    """Check if symbol looks like forex (e.g. EURUSD=X, USDJPY, 6-letter pair)."""
    if "=X" in sym:
        return True
    forex_bases = {"EUR", "USD", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD", "SEK", "NOK", "DKK", "SGD", "HKD"}
    s = sym.replace("=X", "").replace("/", "")
    if len(s) == 6 and s[:3] in forex_bases and s[3:] in forex_bases:
        return True
    return False


def _fetch_forex_yfinance(sym):
    """Try fetching forex price via yfinance."""
    if _yf_download is None:
        return None
    try:
        ticker = sym if "=X" in sym else f"{sym[:3]}{sym[3:]}=X"
        import yfinance as _yf
        t = _yf.Ticker(ticker)
        info = t.info or {}
        price = info.get("regularMarketPrice") or info.get("previousClose")
        if price and float(price) > 0:
            print(f"  yfinance forex: {sym} -> {price}")
            return float(price)
    except Exception as e:
        print(f"  yfinance forex failed for {sym}: {e}")
    return None


def fetch_binance_prices(symbols):
    """Fetch current prices using api_failover (5-source) with Binance bulk fallback.

    For forex symbols, also tries yfinance as additional fallback.
    """
    prices = {}

    # --- Phase 1: Try api_failover per-symbol (5-source chain) ---
    if _failover_price:
        remaining = set()
        for sym in symbols:
            try:
                p = _failover_price(sym)
                if p and p > 0:
                    prices[sym] = p
                else:
                    remaining.add(sym)
            except Exception:
                remaining.add(sym)
    else:
        remaining = set(symbols)

    if not remaining:
        return prices

    # --- Phase 2: Binance bulk fetch for remaining symbols ---
    for base in _BINANCE_SPOT_BASES:
        if not remaining:
            break
        try:
            req = urllib.request.Request(
                f"{base}/api/v3/ticker/price",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                for t in data:
                    if t["symbol"] in remaining:
                        prices[t["symbol"]] = float(t["price"])
                        remaining.discard(t["symbol"])
            break  # success
        except Exception as e:
            print(f"WARNING: Binance price fetch from {base} failed: {e}")
            continue

    # --- Phase 3: Forex fallback via yfinance ---
    if remaining:
        for sym in list(remaining):
            if _is_forex_symbol(sym):
                p = _fetch_forex_yfinance(sym)
                if p:
                    prices[sym] = p
                    remaining.discard(sym)

    if remaining:
        print(f"WARNING: Could not fetch prices for: {remaining}")

    return prices


def check_pick(pick, live_price, now):
    """Check if a pick hit TP, SL, or expired. Returns updated pick."""
    if pick.get("outcome") not in ("PENDING", None):
        return pick  # Already resolved

    entry = pick.get("entry_price", 0)
    tp = pick.get("take_profit", 0)
    sl = pick.get("stop_loss", 0)
    direction = pick.get("direction", "LONG")

    if not entry or not tp or not sl or not live_price:
        return pick

    # Calculate unrealized P/L
    if direction == "LONG":
        pnl_pct = ((live_price - entry) / entry) * 100
        tp_hit = live_price >= tp
        sl_hit = live_price <= sl
    else:
        pnl_pct = ((entry - live_price) / entry) * 100
        tp_hit = live_price <= tp
        sl_hit = live_price >= sl

    pick["pnl_pct"] = round(pnl_pct, 4)
    pick["last_checked"] = now.isoformat()
    pick["last_price"] = live_price

    # Track peak/trough
    pick["peak_pnl_pct"] = max(pick.get("peak_pnl_pct", pnl_pct), pnl_pct)
    pick["trough_pnl_pct"] = min(pick.get("trough_pnl_pct", pnl_pct), pnl_pct)

    # Add to price history (max 48 entries = 24h at 30min intervals)
    history = pick.get("price_history", [])
    history.append({"t": now.isoformat(), "p": live_price, "pnl": round(pnl_pct, 2)})
    if len(history) > 48:
        history = history[-48:]
    pick["price_history"] = history

    # Check outcomes
    if tp_hit:
        pick["outcome"] = "TP_HIT"
        pick["status"] = "CLOSED"
        pick["closed_at"] = now.isoformat()
        pick["closed_price"] = live_price
        print(f"  TP HIT: {pick['symbol']} entry={entry} -> {live_price} ({pnl_pct:+.2f}%)")
    elif sl_hit:
        pick["outcome"] = "SL_HIT"
        pick["status"] = "CLOSED"
        pick["closed_at"] = now.isoformat()
        pick["closed_price"] = live_price
        print(f"  SL HIT: {pick['symbol']} entry={entry} -> {live_price} ({pnl_pct:+.2f}%)")
    else:
        # Check 24h expiry
        entry_time = pick.get("entry_time") or pick.get("timestamp")
        if entry_time:
            try:
                et = datetime.fromisoformat(entry_time.replace("Z", "+00:00"))
                elapsed_h = (now - et).total_seconds() / 3600
                pick["elapsed_h"] = round(elapsed_h, 1)
                if elapsed_h >= 24:
                    pick["outcome"] = "EXPIRED"
                    pick["status"] = "CLOSED"
                    pick["closed_at"] = now.isoformat()
                    pick["closed_price"] = live_price
                    print(f"  EXPIRED: {pick['symbol']} after {elapsed_h:.1f}h ({pnl_pct:+.2f}%)")
            except Exception:
                pass

    return pick


def update_top_picks():
    """Update claude_top_picks.json with live outcomes."""
    if not TOP_PICKS_PATH.exists():
        print("No claude_top_picks.json found, skipping")
        return

    with open(TOP_PICKS_PATH) as f:
        data = json.load(f)

    picks = data.get("picks", [])
    if not picks:
        print("No picks in claude_top_picks.json")
        return

    symbols = {p["symbol"] for p in picks}
    prices = fetch_binance_prices(symbols)
    now = datetime.now(timezone.utc)

    print(f"\n=== Claude Top Picks Outcome Check ({now.strftime('%Y-%m-%d %H:%M UTC')}) ===")
    for p in picks:
        live = prices.get(p["symbol"])
        if live:
            p = check_pick(p, live, now)
            entry = p.get("entry_price", 0)
            pnl = float(p.get("pnl_pct", 0) or 0)
            print(f"  {p['symbol']:16s} entry={entry} now={live} pnl={pnl:+.2f}% status={p.get('outcome','?')}")

    # Update historical round results
    rounds = data.get("historical_rounds", [])
    if rounds:
        current_round = rounds[-1]
        results = current_round.get("results", {})
        wins, losses, pending_count = 0, 0, 0
        total_pnl = 0
        for p in picks:
            sym = p["symbol"]
            results[sym] = {
                "outcome": p.get("outcome", "PENDING"),
                "pnl_pct": float(p.get("pnl_pct", 0) or 0),
                "peak_pnl_pct": p.get("peak_pnl_pct", 0),
                "trough_pnl_pct": p.get("trough_pnl_pct", 0)
            }
            total_pnl += float(p.get("pnl_pct", 0) or 0)
            if p.get("outcome") == "TP_HIT":
                wins += 1
            elif p.get("outcome") in ("SL_HIT", "EXPIRED"):
                losses += 1
            else:
                pending_count += 1

        current_round["results"] = results
        current_round["round_pnl_pct"] = round(total_pnl / len(picks), 2) if picks else 0
        if wins + losses > 0:
            current_round["round_wr"] = round(wins / (wins + losses) * 100, 1)
            if pending_count == 0:
                current_round["status"] = "WIN" if wins > losses else "LOSS" if losses > wins else "DRAW"

    # Update lifetime stats
    stats = data.get("lifetime_stats", {})
    all_resolved = [p for p in picks if p.get("outcome") not in ("PENDING", None)]
    wins_total = sum(1 for p in all_resolved if p.get("outcome") == "TP_HIT")
    losses_total = len(all_resolved) - wins_total
    stats["wins"] = wins_total
    stats["losses"] = losses_total
    stats["pending"] = len(picks) - len(all_resolved)
    stats["win_rate"] = round(wins_total / len(all_resolved) * 100, 1) if all_resolved else None
    stats["avg_pnl_pct"] = round(sum(float(p.get("pnl_pct", 0) or 0) for p in picks) / len(picks), 2) if picks else 0
    stats["cumulative_pnl_pct"] = round(sum(float(p.get("pnl_pct", 0) or 0) for p in picks), 2)

    best = max(picks, key=lambda p: float(p.get("pnl_pct", 0) or 0))
    worst = min(picks, key=lambda p: float(p.get("pnl_pct", 0) or 0))
    stats["best_pick"] = {"symbol": best["symbol"], "pnl_pct": best.get("pnl_pct", 0)}
    stats["worst_pick"] = {"symbol": worst["symbol"], "pnl_pct": worst.get("pnl_pct", 0)}

    data["lifetime_stats"] = stats
    data["last_checked"] = now.isoformat()

    with open(TOP_PICKS_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Updated {TOP_PICKS_PATH}")


def update_generic_picks(path, label):
    """Update momentum/tracked picks with live outcomes."""
    if not path.exists():
        print(f"No {path.name} found, skipping")
        return

    with open(path) as f:
        data = json.load(f)

    picks = data.get("picks", [])
    pending = [p for p in picks if p.get("outcome") in ("PENDING", None)]
    if not pending:
        print(f"{label}: no pending picks to check")
        return

    symbols = {p["symbol"] for p in pending}
    prices = fetch_binance_prices(symbols)
    now = datetime.now(timezone.utc)

    print(f"\n=== {label} Outcome Check ({now.strftime('%Y-%m-%d %H:%M UTC')}) ===")
    tp_hits, sl_hits, expired, still_pending = 0, 0, 0, 0
    for i, p in enumerate(picks):
        if p.get("outcome") not in ("PENDING", None):
            continue
        live = prices.get(p["symbol"])
        if live:
            picks[i] = check_pick(p, live, now)
            outcome = picks[i].get("outcome", "PENDING")
            if outcome == "TP_HIT":
                tp_hits += 1
            elif outcome == "SL_HIT":
                sl_hits += 1
            elif outcome == "EXPIRED":
                expired += 1
            else:
                still_pending += 1

    data["picks"] = picks
    data["last_checked"] = now.isoformat()

    # Summary stats
    all_resolved = [p for p in picks if p.get("outcome") not in ("PENDING", None)]
    if all_resolved:
        wins = sum(1 for p in all_resolved if p.get("outcome") == "TP_HIT")
        data["resolved_stats"] = {
            "total": len(all_resolved),
            "tp_hits": wins,
            "sl_hits": sum(1 for p in all_resolved if p.get("outcome") == "SL_HIT"),
            "expired": sum(1 for p in all_resolved if p.get("outcome") == "EXPIRED"),
            "win_rate": round(wins / len(all_resolved) * 100, 1),
            "avg_pnl_pct": round(sum(float(p.get("pnl_pct", 0) or 0) for p in all_resolved) / len(all_resolved), 2)
        }

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"  Results: TP={tp_hits} SL={sl_hits} Expired={expired} Pending={still_pending}")
    print(f"  Updated {path}")


if __name__ == "__main__":
    print("=" * 60)
    print("OUTCOME CHECKER — All Pick Sources")
    print("=" * 60)

    update_top_picks()
    update_generic_picks(MOMENTUM_PATH, "Momentum Scalp Picks")
    update_generic_picks(TRACKED_PATH, "Tracked Live Picks")

    print("\nDone.")
