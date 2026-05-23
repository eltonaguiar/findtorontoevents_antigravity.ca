#!/usr/bin/env python3
"""
Proven Winners Test Portfolio — tracks active picks from strategies
that have verified live profitability.

Runs hourly, snapshots the portfolio, tracks PnL over time.
Results flow into smart_picks.json via the existing pipeline.

Output: alpha_engine/data/proven_portfolio.json
"""
import json, time, urllib.request, logging
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger("proven_portfolio")

_DIR = Path(__file__).resolve().parent
_DATA = _DIR / "data"
_PORTFOLIO_PATH = _DATA / "proven_portfolio.json"
_ACTIVE_PATH = _DATA / "active_picks.json"
_CLOSED_PATH = _DATA / "closed_picks.json"

# Import the proven winners from smart_picks_engine
try:
    from alpha_engine.smart_picks_engine import PROVEN_WINNERS, PROVEN_PREFIXES, BANNED_SYSTEMS
except ImportError:
    try:
        from smart_picks_engine import PROVEN_WINNERS, PROVEN_PREFIXES, BANNED_SYSTEMS
    except ImportError:
        PROVEN_WINNERS = {}
        PROVEN_PREFIXES = {}
        BANNED_SYSTEMS = set()

BINANCE_URLS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
]
_HDR = {"User-Agent": "AlphaEngine/1.0"}


def _http_json(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers=_HDR)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None


def fetch_prices(symbols):
    """Bulk fetch prices from Binance."""
    prices = {}
    sym_set = set(symbols)
    for mirror in BINANCE_URLS:
        data = _http_json(f"{mirror}/api/v3/ticker/price")
        if isinstance(data, list):
            for t in data:
                if t["symbol"] in sym_set:
                    prices[t["symbol"]] = float(t["price"])
            break
    return prices


def is_proven_strategy(strategy_name):
    """Check if strategy is in the proven winners list."""
    if strategy_name in PROVEN_WINNERS:
        return True
    for prefix in PROVEN_PREFIXES:
        if strategy_name.startswith(prefix):
            return True
    return False


def load_portfolio():
    """Load existing portfolio state."""
    if _PORTFOLIO_PATH.exists():
        try:
            return json.loads(_PORTFOLIO_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "description": "Test portfolio tracking only proven-winner strategies",
        "criteria": {
            "strategies": list(PROVEN_WINNERS.keys()),
            "prefixes": list(PROVEN_PREFIXES.keys()),
            "direction_filter": "LONG only for crypto (shorts have 15.3% WR)",
            "confidence_floor": 0.70,
        },
        "active_positions": [],
        "closed_positions": [],
        "snapshots": [],
        "stats": {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "total_pnl_pct": 0.0,
        },
    }


def run():
    """Run portfolio update cycle."""
    now = datetime.now(timezone.utc)
    portfolio = load_portfolio()

    # Load active picks
    active = []
    if _ACTIVE_PATH.exists():
        try:
            active = json.loads(_ACTIVE_PATH.read_text(encoding="utf-8"))
        except Exception:
            active = []

    # Filter for proven winners only
    proven_picks = []
    for p in active:
        if not isinstance(p, dict):
            continue
        strat = p.get("strategy", "")
        if strat in BANNED_SYSTEMS:
            continue
        if not is_proven_strategy(strat):
            continue
        direction = (p.get("direction", "") or p.get("signal_type", "")).upper()
        # Block crypto shorts
        sym = p.get("symbol", "")
        if sym.endswith("USDT") and direction in ("SHORT", "SELL"):
            continue
        # Confidence floor
        conf = float(p.get("confidence", 0) or 0)
        if 0 < conf < 0.70:
            continue
        proven_picks.append(p)

    log.info(f"Found {len(proven_picks)} active picks from proven strategies (out of {len(active)} total)")

    # Fetch prices
    symbols = [p.get("symbol", "") for p in proven_picks if p.get("symbol")]
    prices = fetch_prices(symbols) if symbols else {}
    log.info(f"Got prices for {len(prices)}/{len(symbols)} symbols")

    # Build positions
    positions = []
    for p in proven_picks:
        sym = p.get("symbol", "")
        entry = float(p.get("entry_price", 0) or 0)
        tp = float(p.get("take_profit", 0) or 0)
        sl = float(p.get("stop_loss", 0) or 0)
        live = prices.get(sym, 0)
        direction = (p.get("direction", "") or p.get("signal_type", "")).upper()
        if direction in ("BUY", "LONG"):
            direction = "LONG"
        else:
            direction = "SHORT"

        if entry > 0 and live > 0:
            if direction == "LONG":
                pnl = (live - entry) / entry * 100
            else:
                pnl = (entry - live) / entry * 100
        else:
            pnl = 0

        # Determine status
        status = "OPEN"
        if tp > 0 and sl > 0:
            if direction == "LONG":
                if live >= tp:
                    status = "TP_HIT"
                elif live <= sl:
                    status = "SL_HIT"
            else:
                if live <= tp:
                    status = "TP_HIT"
                elif live >= sl:
                    status = "SL_HIT"

        boost = PROVEN_WINNERS.get(p.get("strategy", ""), {}).get("boost", 0)
        live_wr = PROVEN_WINNERS.get(p.get("strategy", ""), {}).get("wr", 0)

        positions.append({
            "symbol": sym,
            "direction": direction,
            "strategy": p.get("strategy", ""),
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "live_price": live,
            "pnl_pct": round(pnl, 4),
            "status": status,
            "confidence": float(p.get("confidence", 0) or 0),
            "elite_score": float(p.get("elite_score", p.get("score", 0)) or 0),
            "proven_boost": boost,
            "proven_live_wr": live_wr,
            "open_time": p.get("open_time", p.get("timestamp", "")),
        })

    # Check for closed positions (TP/SL hit)
    for pos in positions:
        if pos["status"] in ("TP_HIT", "SL_HIT"):
            pos["closed_at"] = now.isoformat()
            portfolio["closed_positions"].append(pos)
            if pos["pnl_pct"] > 0:
                portfolio["stats"]["wins"] += 1
            else:
                portfolio["stats"]["losses"] += 1
            portfolio["stats"]["total_trades"] += 1
            portfolio["stats"]["total_pnl_pct"] += pos["pnl_pct"]

    active_positions = [p for p in positions if p["status"] == "OPEN"]

    # Portfolio metrics
    total_pnl = sum(p["pnl_pct"] for p in active_positions) if active_positions else 0
    positive = sum(1 for p in active_positions if p["pnl_pct"] > 0)
    negative = sum(1 for p in active_positions if p["pnl_pct"] < 0)

    # Snapshot
    snapshot = {
        "timestamp": now.isoformat(),
        "active_count": len(active_positions),
        "total_unrealized_pnl": round(total_pnl, 4),
        "avg_pnl": round(total_pnl / len(active_positions), 4) if active_positions else 0,
        "positive": positive,
        "negative": negative,
        "strategies": list(set(p["strategy"] for p in active_positions)),
    }

    # Keep last 500 snapshots
    portfolio["snapshots"] = (portfolio.get("snapshots", []) + [snapshot])[-500:]
    portfolio["active_positions"] = active_positions
    portfolio["last_updated"] = now.isoformat()
    portfolio["summary"] = {
        "active_positions": len(active_positions),
        "unrealized_pnl": round(total_pnl, 4),
        "positive": positive,
        "negative": negative,
        "closed_trades": portfolio["stats"]["total_trades"],
        "closed_wins": portfolio["stats"]["wins"],
        "closed_losses": portfolio["stats"]["losses"],
        "closed_wr": round(portfolio["stats"]["wins"] / max(portfolio["stats"]["total_trades"], 1) * 100, 1),
        "total_realized_pnl": round(portfolio["stats"]["total_pnl_pct"], 4),
    }

    _PORTFOLIO_PATH.write_text(json.dumps(portfolio, indent=2), encoding="utf-8")

    # Print summary
    print(f"\n{'='*70}")
    print(f"PROVEN WINNERS TEST PORTFOLIO")
    print(f"{'='*70}")
    print(f"Active positions: {len(active_positions)}")
    print(f"Unrealized PnL:   {total_pnl:+.4f}%")
    print(f"In profit:        {positive}/{len(active_positions)}")
    print(f"Closed trades:    {portfolio['stats']['total_trades']} ({portfolio['stats']['wins']}W/{portfolio['stats']['losses']}L)")
    print(f"Realized PnL:     {portfolio['stats']['total_pnl_pct']:+.4f}%")
    print(f"{'='*70}")
    for p in sorted(active_positions, key=lambda x: -x["pnl_pct"]):
        boost_tag = f"[+{p['proven_boost']}]" if p['proven_boost'] else ""
        print(f"  {p['symbol']:15s} {p['direction']:5s} PnL={p['pnl_pct']:+.3f}% "
              f"strat={p['strategy'][:30]} {boost_tag}")

    return portfolio


if __name__ == "__main__":
    run()
