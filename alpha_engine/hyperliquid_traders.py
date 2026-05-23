"""
Hyperliquid Top Trader Scraper
==============================
Fetches the Hyperliquid on-chain leaderboard, analyzes top traders'
positions and fills, and generates consensus picks when 2+ top traders
hold the same coin in the same direction.

Hyperliquid API: 100% on-chain, free, no auth required.
All endpoints use POST to https://api.hyperliquid.xyz/info.
"""

import json
import os
import ssl
import urllib.request
from datetime import datetime, timezone
from collections import defaultdict

API_URL = "https://api.hyperliquid.xyz/info"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "hyperliquid_traders.json")
TOP_N = 10
REQUEST_TIMEOUT = 20

# Known high-performance wallets (verified via research 2026-03-19)
# Always include these even if they don't appear on leaderboard.
#
# "GRINDER" = A trader who:
#   - Has 60%+ win rate over 100+ trades (statistically beyond luck)
#   - Trades frequently (daily or multiple times per day)
#   - Uses consistent position sizing and risk management
#   - Has been active for 30+ days (not a one-hit wonder)
#   - Max drawdown < 30% (disciplined, not a gambler)
#   - Opposite of a "whale gambler" who bets big and gets lucky
#   - Their edge comes from SKILL and CONSISTENCY, not variance
#
# vs "WHALE" = Large account, high variance, often 50/50 WR with big bets
# vs "MARKET MAKER" = ~50% WR, profits from spread, not direction
KNOWN_GRINDER_WALLETS = [
    # 97.6% WR, $537K in 2 weeks, 1215 trades/week -- ETH/SOL/BTC scalper
    "0xd260b2216B735277da6771564A01c04856E78321",
    # 100% WR on 20 consecutive trades, $31M total PnL (may be dormant)
    "0x9263c1bd29aa87a118242f3fbba4517037f8cc7a",
    # $32M account, 86 simultaneous positions -- market maker (use for flow signals)
    "0xecb63caa47c7c4e77f60f1ce858cf28dc2b82b00",
]

# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _post(payload: dict) -> dict:
    """POST JSON to Hyperliquid API, return parsed response."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, context=ctx, timeout=REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_float(val, default=0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# 1. Fetch leaderboard
# ---------------------------------------------------------------------------

def fetch_leaderboard(window: str = "month") -> list:
    """Return leaderboard entries sorted by PnL descending.

    Uses stats-data.hyperliquid.xyz (GET) which is the WORKING endpoint.
    The POST /info leaderboard endpoint returns 422.
    """
    # Primary: stats-data endpoint (confirmed working 2026-03-19)
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        url = "https://stats-data.hyperliquid.xyz/Mainnet/leaderboard"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT, context=ctx)
        raw = json.loads(resp.read().decode())
        print(f"[hyperliquid] Leaderboard fetched from stats-data endpoint")
    except Exception as e:
        print(f"[hyperliquid] stats-data failed ({e}), trying POST API...")
        try:
            raw = _post({"type": "leaderboard", "window": window})
        except Exception as e2:
            print(f"[hyperliquid] leaderboard fetch failed: {e2}")
            return []

    # API may return dict with a key or a plain list
    entries = []
    if isinstance(raw, list):
        entries = raw
    elif isinstance(raw, dict):
        # Try common keys
        for key in ("leaderboard", "rows", "data", "result"):
            if key in raw and isinstance(raw[key], list):
                entries = raw[key]
                break
        if not entries:
            # Might be nested: {"leaderboardRows": [...]}
            for key, val in raw.items():
                if isinstance(val, list) and len(val) > 0:
                    entries = val
                    break

    if not entries:
        print("[hyperliquid] leaderboard returned no entries")
        return []

    # Normalise & sort by PnL
    normalised = []
    for e in entries:
        addr = e.get("ethAddress") or e.get("address") or e.get("trader") or ""
        acct_val = _safe_float(e.get("accountValue") or e.get("equity") or 0)
        display = e.get("displayName") or e.get("name") or addr[:10]

        # Extract PnL from windowPerformances if present (stats-data format)
        pnl = 0
        roi = 0
        perfs = e.get("windowPerformances", [])
        if perfs:
            perf_dict = {p[0]: p[1] for p in perfs if isinstance(p, list) and len(p) >= 2}
            month_perf = perf_dict.get("month", perf_dict.get("allTime", {}))
            if isinstance(month_perf, dict):
                pnl = _safe_float(month_perf.get("pnl", 0))
                roi = _safe_float(month_perf.get("roi", 0))
        if pnl == 0:
            pnl = _safe_float(e.get("pnl") or e.get("profit") or 0)
        if roi == 0:
            roi = _safe_float(e.get("roi") or e.get("return") or 0)
        if addr:
            normalised.append({
                "address": addr,
                "display_name": display,
                "pnl": pnl,
                "roi": roi,
                "account_value": acct_val,
            })
    normalised.sort(key=lambda x: x["pnl"], reverse=True)
    return normalised[:TOP_N]


# ---------------------------------------------------------------------------
# 2. Fetch positions for a trader
# ---------------------------------------------------------------------------

def fetch_positions(wallet: str) -> list:
    """Return open positions for a wallet address."""
    try:
        raw = _post({"type": "clearinghouseState", "user": wallet})
    except Exception as e:
        print(f"[hyperliquid] positions fetch failed for {wallet[:10]}: {e}")
        return []

    positions = []
    asset_positions = []

    if isinstance(raw, dict):
        asset_positions = raw.get("assetPositions", [])
        if not asset_positions:
            # Fallback: maybe positions are at top level
            asset_positions = raw.get("positions", [])

    for ap in asset_positions:
        pos = ap.get("position", ap) if isinstance(ap, dict) else {}
        coin = pos.get("coin", "")
        szi = _safe_float(pos.get("szi", 0))
        entry_px = _safe_float(pos.get("entryPx", 0))
        unrealized_pnl = _safe_float(pos.get("unrealizedPnl", 0))
        leverage_info = pos.get("leverage", {})
        if isinstance(leverage_info, dict):
            leverage = _safe_float(leverage_info.get("value", 0))
        else:
            leverage = _safe_float(leverage_info)
        liq_px = _safe_float(pos.get("liquidationPx", 0))
        position_value = _safe_float(pos.get("positionValue", 0))

        if coin and szi != 0:
            direction = "LONG" if szi > 0 else "SHORT"
            positions.append({
                "coin": coin,
                "size": abs(szi),
                "direction": direction,
                "entry_price": entry_px,
                "unrealized_pnl": unrealized_pnl,
                "leverage": leverage,
                "liquidation_price": liq_px,
                "position_value": position_value,
            })
    return positions


# ---------------------------------------------------------------------------
# 3. Fetch recent fills/trades
# ---------------------------------------------------------------------------

def fetch_fills(wallet: str, limit: int = 200) -> list:
    """Return recent fills for a wallet."""
    try:
        raw = _post({"type": "userFills", "user": wallet})
    except Exception as e:
        print(f"[hyperliquid] fills fetch failed for {wallet[:10]}: {e}")
        return []

    fills = raw if isinstance(raw, list) else []
    # Take most recent `limit` fills
    fills = fills[:limit]

    parsed = []
    for f in fills:
        parsed.append({
            "coin": f.get("coin", ""),
            "price": _safe_float(f.get("px", 0)),
            "size": _safe_float(f.get("sz", 0)),
            "side": f.get("side", ""),
            "time_ms": int(_safe_float(f.get("time", 0))),
            "fee": _safe_float(f.get("fee", 0)),
            "closed_pnl": _safe_float(f.get("closedPnl", 0)),
            "direction": f.get("dir", ""),
            "hash": f.get("hash", ""),
        })
    return parsed


# ---------------------------------------------------------------------------
# 4. Analyze a trader
# ---------------------------------------------------------------------------

def analyze_trader(fills: list, positions: list) -> dict:
    """Compute stats from fills and positions."""
    stats = {
        "total_trades": len(fills),
        "wins": 0,
        "losses": 0,
        "win_rate": 0.0,
        "total_pnl": 0.0,
        "avg_hold_hours": 0.0,
        "most_traded_coins": [],
        "avg_leverage": 0.0,
        "long_count": 0,
        "short_count": 0,
        "long_ratio": 0.5,
        "trade_frequency_per_day": 0.0,
        "open_positions": len(positions),
    }

    if not fills:
        return stats

    # Win/loss from closedPnl
    closing_fills = [f for f in fills if f["closed_pnl"] != 0]
    stats["wins"] = sum(1 for f in closing_fills if f["closed_pnl"] > 0)
    stats["losses"] = sum(1 for f in closing_fills if f["closed_pnl"] < 0)
    total_closed = stats["wins"] + stats["losses"]
    stats["win_rate"] = round(stats["wins"] / total_closed, 3) if total_closed > 0 else 0.0
    stats["total_pnl"] = round(sum(f["closed_pnl"] for f in closing_fills), 2)

    # Most traded coins
    coin_counts = defaultdict(int)
    for f in fills:
        if f["coin"]:
            coin_counts[f["coin"]] += 1
    sorted_coins = sorted(coin_counts.items(), key=lambda x: x[1], reverse=True)
    stats["most_traded_coins"] = [c[0] for c in sorted_coins[:5]]

    # Long vs short ratio
    for f in fills:
        side = (f.get("side") or "").upper()
        if side in ("B", "BUY", "LONG"):
            stats["long_count"] += 1
        elif side in ("A", "SELL", "SHORT"):
            stats["short_count"] += 1
    total_sides = stats["long_count"] + stats["short_count"]
    stats["long_ratio"] = round(stats["long_count"] / total_sides, 3) if total_sides > 0 else 0.5

    # Average hold time estimate from fill timestamps
    # Group fills by coin, find pairs of open/close
    if len(fills) >= 2:
        times = [f["time_ms"] for f in fills if f["time_ms"] > 0]
        if len(times) >= 2:
            time_span_hours = (max(times) - min(times)) / (1000 * 3600)
            # Rough estimate: span / number of round-trip trades
            num_roundtrips = max(total_closed, 1)
            stats["avg_hold_hours"] = round(time_span_hours / num_roundtrips, 1)

    # Trade frequency
    if len(fills) >= 2:
        times = sorted([f["time_ms"] for f in fills if f["time_ms"] > 0])
        if len(times) >= 2:
            span_days = (times[-1] - times[0]) / (1000 * 86400)
            if span_days > 0:
                stats["trade_frequency_per_day"] = round(len(fills) / span_days, 1)

    # Average leverage from open positions
    if positions:
        levs = [p["leverage"] for p in positions if p["leverage"] > 0]
        stats["avg_leverage"] = round(sum(levs) / len(levs), 1) if levs else 0.0

    return stats


# ---------------------------------------------------------------------------
# 5. Generate consensus picks
# ---------------------------------------------------------------------------

def build_consensus(traders_data: list) -> list:
    """
    If 2+ top traders have open positions in the same coin+direction,
    produce a high-conviction consensus pick.
    """
    # Aggregate: (coin, direction) -> list of trader info
    buckets = defaultdict(list)
    for td in traders_data:
        for pos in td.get("positions", []):
            key = (pos["coin"], pos["direction"])
            buckets[key].append({
                "address": td["address"],
                "display_name": td.get("display_name", ""),
                "entry_price": pos["entry_price"],
                "leverage": pos["leverage"],
                "size": pos["size"],
                "unrealized_pnl": pos["unrealized_pnl"],
                "win_rate": td.get("stats", {}).get("win_rate", 0),
            })

    consensus = []
    for (coin, direction), holders in buckets.items():
        if len(holders) < 2:
            continue

        # Weighted average entry price
        total_size = sum(h["size"] for h in holders)
        if total_size == 0:
            continue
        avg_entry = sum(h["entry_price"] * h["size"] for h in holders) / total_size
        avg_leverage = sum(h["leverage"] for h in holders) / len(holders)
        avg_wr = sum(h["win_rate"] for h in holders) / len(holders)
        total_upnl = sum(h["unrealized_pnl"] for h in holders)

        # Confidence: base 0.55, +0.05 per extra trader, +0.10 if avg WR > 60%
        conf = 0.55 + 0.05 * (len(holders) - 2)
        if avg_wr > 0.60:
            conf += 0.10
        if avg_wr > 0.70:
            conf += 0.05
        conf = round(min(conf, 0.90), 3)

        # TP/SL based on direction
        if direction == "LONG":
            signal_type = "BUY"
            tp = round(avg_entry * 1.05, 6)   # 5% target
            sl = round(avg_entry * 0.97, 6)   # 3% stop
            rr = round(5.0 / 3.0, 2)
        else:
            signal_type = "SELL"
            tp = round(avg_entry * 0.95, 6)
            sl = round(avg_entry * 1.03, 6)
            rr = round(5.0 / 3.0, 2)

        consensus.append({
            "coin": coin,
            "direction": direction,
            "signal_type": signal_type,
            "num_traders": len(holders),
            "avg_entry_price": round(avg_entry, 6),
            "avg_leverage": round(avg_leverage, 1),
            "avg_win_rate": round(avg_wr, 3),
            "total_unrealized_pnl": round(total_upnl, 2),
            "confidence": conf,
            "take_profit": tp,
            "stop_loss": sl,
            "risk_reward": rr,
            "traders": [
                {"address": h["address"][:10] + "...", "display_name": h["display_name"]}
                for h in holders
            ],
        })

    # Sort by number of traders then confidence
    consensus.sort(key=lambda x: (x["num_traders"], x["confidence"]), reverse=True)
    return consensus


# ---------------------------------------------------------------------------
# 6. Full pipeline -- save to JSON
# ---------------------------------------------------------------------------

def run_full_scan() -> dict:
    """Run the full pipeline: leaderboard -> positions -> fills -> analysis -> consensus."""
    print("[hyperliquid] Fetching leaderboard...")
    leaders = fetch_leaderboard("month")
    if not leaders:
        print("[hyperliquid] No leaderboard data, trying 'week' window...")
        leaders = fetch_leaderboard("week")
    if not leaders:
        print("[hyperliquid] No leaderboard data available")
        return {"fetched_at": _now_iso(), "top_traders": [], "consensus_positions": [], "patterns": {}}

    # Always include known grinder wallets even if not on leaderboard
    leader_addrs = {l["address"].lower() for l in leaders}
    for wallet in KNOWN_GRINDER_WALLETS:
        if wallet.lower() not in leader_addrs:
            leaders.append({
                "address": wallet,
                "display_name": wallet[:10] + "...(known)",
                "pnl": 0,
                "roi": 0,
                "account_value": 0,
            })

    print(f"[hyperliquid] Got {len(leaders)} traders (incl. known grinders), fetching details...")

    traders_data = []
    all_hold_hours = []
    all_coins = defaultdict(int)
    all_long = 0
    all_short = 0

    for i, leader in enumerate(leaders):
        addr = leader["address"]
        print(f"[hyperliquid]   ({i+1}/{len(leaders)}) {leader['display_name']} -- PnL: ${leader['pnl']:,.0f}")

        positions = fetch_positions(addr)
        fills = fetch_fills(addr)
        stats = analyze_trader(fills, positions)

        trader_record = {
            "address": addr,
            "display_name": leader["display_name"],
            "pnl": leader["pnl"],
            "roi": leader["roi"],
            "account_value": leader["account_value"],
            "positions": positions,
            "stats": stats,
        }
        traders_data.append(trader_record)

        # Aggregate for global patterns
        if stats["avg_hold_hours"] > 0:
            all_hold_hours.append(stats["avg_hold_hours"])
        for coin in stats["most_traded_coins"]:
            all_coins[coin] += 1
        all_long += stats["long_count"]
        all_short += stats["short_count"]

    # Build consensus
    print("[hyperliquid] Building consensus picks...")
    consensus = build_consensus(traders_data)
    print(f"[hyperliquid] Found {len(consensus)} consensus positions")

    # Global patterns
    total_sides = all_long + all_short
    patterns = {
        "avg_hold_hours": round(sum(all_hold_hours) / len(all_hold_hours), 1) if all_hold_hours else 0,
        "top_coins": [c[0] for c in sorted(all_coins.items(), key=lambda x: x[1], reverse=True)[:10]],
        "long_ratio": round(all_long / total_sides, 3) if total_sides > 0 else 0.5,
        "num_traders_analyzed": len(traders_data),
    }

    # Prepare output (strip fills from saved data to keep file small)
    output_traders = []
    for td in traders_data:
        output_traders.append({
            "address": td["address"][:10] + "..." + td["address"][-4:],
            "display_name": td["display_name"],
            "pnl": td["pnl"],
            "roi": td["roi"],
            "account_value": td["account_value"],
            "positions": td["positions"],
            "stats": td["stats"],
        })

    result = {
        "fetched_at": _now_iso(),
        "top_traders": output_traders,
        "consensus_positions": consensus,
        "patterns": patterns,
    }

    # Save
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f, indent=2)
    print(f"[hyperliquid] Saved to {OUTPUT_FILE}")

    return result


# ---------------------------------------------------------------------------
# 7. Alpha-engine-compatible pick generator
# ---------------------------------------------------------------------------

def get_hyperliquid_consensus() -> list:
    """
    Return list of pick dicts compatible with active_picks.json schema.
    Runs the full scan if no recent data exists, otherwise loads cached data.
    """
    # Try to load cached data first (< 1 hour old)
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r") as f:
                cached = json.load(f)
            fetched = cached.get("fetched_at", "")
            if fetched:
                fetched_dt = datetime.strptime(fetched, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                age_minutes = (datetime.now(timezone.utc) - fetched_dt).total_seconds() / 60
                if age_minutes < 60:
                    print(f"[hyperliquid] Using cached data ({age_minutes:.0f}m old)")
                    return _consensus_to_picks(cached.get("consensus_positions", []))
        except Exception:
            pass

    # Run fresh scan
    result = run_full_scan()
    return _consensus_to_picks(result.get("consensus_positions", []))


def _consensus_to_picks(consensus: list) -> list:
    """Convert consensus positions to alpha engine pick format."""
    picks = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ts = _now_iso()

    for cp in consensus:
        coin = cp["coin"]
        # Map to standard symbol format (e.g. BTC -> BTC-USD)
        symbol = f"{coin}-USD" if not any(c in coin for c in ["-", "/", "="]) else coin

        pick = {
            "id": f"hl_consensus::{symbol}::{today}",
            "strategy": "hyperliquid_top_trader_consensus",
            "symbol": symbol,
            "category": "crypto",
            "signal_type": cp["signal_type"],
            "entry_price": cp["avg_entry_price"],
            "take_profit": cp["take_profit"],
            "stop_loss": cp["stop_loss"],
            "confidence": cp["confidence"],
            "risk_reward": cp["risk_reward"],
            "reason": (
                f"Hyperliquid consensus: {cp['num_traders']} top traders "
                f"are {cp['direction']} {coin} "
                f"(avg leverage {cp['avg_leverage']:.1f}x, "
                f"avg WR {cp['avg_win_rate']:.0%}). "
                f"Unrealized PnL: ${cp['total_unrealized_pnl']:,.0f}"
            ),
            "timeframe": "1-7d",
            "extra": {
                "source": "hyperliquid_onchain",
                "num_traders": cp["num_traders"],
                "avg_leverage": cp["avg_leverage"],
                "avg_win_rate": cp["avg_win_rate"],
                "total_unrealized_pnl": cp["total_unrealized_pnl"],
                "traders": cp["traders"],
            },
            "timestamp": ts,
        }
        picks.append(pick)

    return picks


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    result = run_full_scan()
    picks = _consensus_to_picks(result.get("consensus_positions", []))
    print(f"\n[hyperliquid] Generated {len(picks)} consensus picks:")
    for p in picks:
        print(f"  {p['signal_type']} {p['symbol']} @ {p['entry_price']} "
              f"(conf={p['confidence']}, traders={p['extra']['num_traders']})")
