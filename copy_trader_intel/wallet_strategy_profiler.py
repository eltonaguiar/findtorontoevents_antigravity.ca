"""
wallet_strategy_profiler.py - Wallet Strategy Reverse Engineering
=================================================================
Analyzes top-performing wallets from our Hyperliquid (89 wallets) and OKX
(294 traders) databases. For high-quality wallets, fetches recent fill
history from Hyperliquid API and computes strategy profiles:

  - Average hold time, preferred entry conditions
  - Typical TP/SL ratios, leverage preferences
  - Trading patterns: time of day, position sizing, coin preferences
  - Directional bias (long/short ratio)

Output: copy_trader_intel/data/wallet_strategy_profiles.json

Integration: Use profiles as entry filters in the Alpha Engine.
  e.g., "PensionFund trades BTC SHORT at 3x leverage → if BTC is trending
  down and leverage < 5x, boost confidence for SHORT picks"

Data Sources:
  - copy_trader_intel/data/hyperliquid_trader_database.json (89 wallets)
  - copy_trader_intel/data/okx_trader_database.json (294 traders)
  - Hyperliquid API: POST https://api.hyperliquid.xyz/info
    {"type":"userFills","user":"ADDRESS"} → recent fills
"""

from __future__ import annotations

import json
import logging
import ssl
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent / "data"
HL_DB_FILE = DATA_DIR / "hyperliquid_trader_database.json"
OKX_DB_FILE = DATA_DIR / "okx_trader_database.json"
OUTPUT_FILE = DATA_DIR / "wallet_strategy_profiles.json"

HL_API = "https://api.hyperliquid.xyz/info"

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

TIMEOUT = 10

# Minimum quality thresholds for profiling
MIN_WIN_RATE = 0.60
MIN_CLOSED_TRADES = 50
MIN_CLOSED_PNL = 1000  # USD


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _post_json(url: str, payload: dict) -> Optional[Any]:
    """POST JSON to URL and return parsed response."""
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "AlphaEngine/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=_SSL_CTX) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        logger.warning(f"HTTP {e.code} from {url}")
    except urllib.error.URLError as e:
        logger.warning(f"URL error {url}: {e.reason}")
    except Exception as e:
        logger.warning(f"Error posting to {url}: {e}")
    return None


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_hyperliquid_traders() -> List[Dict[str, Any]]:
    """Load Hyperliquid trader database and filter to quality traders."""
    if not HL_DB_FILE.exists():
        logger.warning(f"Hyperliquid DB not found: {HL_DB_FILE}")
        return []

    with open(HL_DB_FILE, encoding="utf-8") as f:
        data = json.load(f)

    traders = data.get("traders", [])
    quality = []
    for t in traders:
        wr = t.get("win_rate")
        trades = t.get("closed_trades_with_pnl", 0)
        pnl = t.get("total_closed_pnl_recent", 0)
        if wr is not None and wr >= MIN_WIN_RATE and trades >= MIN_CLOSED_TRADES and pnl >= MIN_CLOSED_PNL:
            quality.append(t)

    quality.sort(key=lambda x: x.get("total_closed_pnl_recent", 0), reverse=True)
    logger.info(f"Loaded {len(quality)}/{len(traders)} quality Hyperliquid traders")
    return quality


def load_okx_traders() -> List[Dict[str, Any]]:
    """Load OKX trader database and filter to quality traders."""
    if not OKX_DB_FILE.exists():
        logger.warning(f"OKX DB not found: {OKX_DB_FILE}")
        return []

    with open(OKX_DB_FILE, encoding="utf-8") as f:
        data = json.load(f)

    traders = data.get("quality_traders", [])
    quality = []
    for t in traders:
        try:
            wr = float(t.get("winRatio", 0))
        except (ValueError, TypeError):
            wr = 0
        try:
            pnl = float(t.get("pnl", 0))
        except (ValueError, TypeError):
            pnl = 0
        try:
            days = int(t.get("leadDays", 0))
        except (ValueError, TypeError):
            days = 0

        if wr >= 0.60 and days >= 60 and pnl >= 1000:
            quality.append(t)

    quality.sort(key=lambda x: float(x.get("pnl", 0)), reverse=True)
    logger.info(f"Loaded {len(quality)}/{len(traders)} quality OKX traders")
    return quality


# ---------------------------------------------------------------------------
# Hyperliquid fills fetcher
# ---------------------------------------------------------------------------

def fetch_hl_fills(address: str) -> List[Dict[str, Any]]:
    """
    Fetch recent fills from Hyperliquid for a given address.
    Returns up to 2000 most recent fills.
    """
    payload = {"type": "userFills", "user": address}
    result = _post_json(HL_API, payload)
    if result and isinstance(result, list):
        logger.info(f"Fetched {len(result)} fills for {address[:12]}...")
        return result
    return []


# ---------------------------------------------------------------------------
# Fill analysis
# ---------------------------------------------------------------------------

def _parse_timestamp(ts: Any) -> Optional[datetime]:
    """Parse Hyperliquid timestamp (milliseconds since epoch)."""
    try:
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
        if isinstance(ts, str):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, OSError):
        pass
    return None


def analyze_hl_fills(fills: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze Hyperliquid fills to extract trading patterns.

    Each fill has: coin, px, sz, side, time, closedPnl, hash, oid,
                   crossed, fee, tid, dir, startPosition, liquidationMarkPx
    """
    if not fills:
        return {"error": "no_fills"}

    # Group fills by coin
    by_coin: Dict[str, List[Dict]] = defaultdict(list)
    for f in fills:
        coin = f.get("coin", "UNKNOWN")
        by_coin[coin].append(f)

    # Aggregate stats
    total_pnl = 0.0
    wins = 0
    losses = 0
    long_count = 0
    short_count = 0
    sizes_usd = []
    hours_utc = []
    leverages_seen = []
    coin_pnl: Dict[str, float] = defaultdict(float)
    hold_times: List[float] = []

    # Track open/close sequences per coin for hold time estimation
    trade_sequences: Dict[str, List[Dict]] = defaultdict(list)

    for f in fills:
        coin = f.get("coin", "UNKNOWN")
        side = f.get("side", "")
        try:
            px = float(f.get("px", 0))
            sz = float(f.get("sz", 0))
            closed_pnl = float(f.get("closedPnl", 0))
        except (ValueError, TypeError):
            continue

        size_usd = px * sz
        if size_usd > 0:
            sizes_usd.append(size_usd)

        # Direction
        dir_val = f.get("dir", "")
        if "Open Long" in str(dir_val) or side == "B":
            long_count += 1
        elif "Open Short" in str(dir_val) or side == "A":
            short_count += 1

        # PnL tracking
        if closed_pnl != 0:
            total_pnl += closed_pnl
            coin_pnl[coin] += closed_pnl
            if closed_pnl > 0:
                wins += 1
            else:
                losses += 1

        # Time analysis
        ts = _parse_timestamp(f.get("time"))
        if ts:
            hours_utc.append(ts.hour)
            trade_sequences[coin].append({"time": ts, "dir": dir_val, "pnl": closed_pnl})

    # Estimate hold times from close fills that have non-zero PnL
    # (close fills reference position close — we estimate by looking at
    # time gaps between consecutive fills on the same coin)
    for coin, seq in trade_sequences.items():
        seq.sort(key=lambda x: x["time"])
        open_time = None
        for s in seq:
            d = str(s.get("dir", ""))
            if "Open" in d:
                open_time = s["time"]
            elif "Close" in d and open_time:
                delta = (s["time"] - open_time).total_seconds()
                if 0 < delta < 86400 * 30:  # Cap at 30 days
                    hold_times.append(delta)
                open_time = None

    # Compute aggregates
    total_trades = wins + losses
    win_rate = wins / total_trades if total_trades > 0 else 0

    # Best coins by PnL
    best_coins = sorted(coin_pnl.items(), key=lambda x: x[1], reverse=True)[:10]
    worst_coins = sorted(coin_pnl.items(), key=lambda x: x[1])[:5]

    # Hour distribution — find preferred trading hours
    hour_counts = defaultdict(int)
    for h in hours_utc:
        hour_counts[h] += 1
    peak_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    # Hold time stats
    avg_hold_seconds = sum(hold_times) / len(hold_times) if hold_times else 0
    median_hold = sorted(hold_times)[len(hold_times) // 2] if hold_times else 0

    # Size stats
    avg_size_usd = sum(sizes_usd) / len(sizes_usd) if sizes_usd else 0
    max_size_usd = max(sizes_usd) if sizes_usd else 0

    # Long/short ratio
    total_dir = long_count + short_count
    long_ratio = long_count / total_dir if total_dir > 0 else 0.5

    return {
        "fill_count": len(fills),
        "total_pnl_usd": round(total_pnl, 2),
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 4),
        "long_count": long_count,
        "short_count": short_count,
        "long_ratio": round(long_ratio, 4),
        "directional_bias": "long" if long_ratio > 0.6 else ("short" if long_ratio < 0.4 else "balanced"),
        "avg_position_size_usd": round(avg_size_usd, 2),
        "max_position_size_usd": round(max_size_usd, 2),
        "avg_hold_time_hours": round(avg_hold_seconds / 3600, 2),
        "median_hold_time_hours": round(median_hold / 3600, 2),
        "hold_time_samples": len(hold_times),
        "peak_trading_hours_utc": [{"hour": h, "count": c} for h, c in peak_hours],
        "best_coins": [{"coin": c, "pnl_usd": round(p, 2)} for c, p in best_coins],
        "worst_coins": [{"coin": c, "pnl_usd": round(p, 2)} for c, p in worst_coins],
        "unique_coins_traded": len(by_coin),
    }


# ---------------------------------------------------------------------------
# OKX trader profiling (from database stats, no API fills)
# ---------------------------------------------------------------------------

def profile_okx_trader(trader: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a strategy profile for an OKX trader from their database entry.
    OKX provides stats but not individual fills via the public API.
    """
    try:
        wr = float(trader.get("winRatio", 0))
        pnl = float(trader.get("pnl", 0))
        pnl_ratio = float(trader.get("pnlRatio", 0))
        days = int(trader.get("leadDays", 0))
        followers = int(trader.get("copyTraderNum", 0))
        aum = float(trader.get("aum", 0))
    except (ValueError, TypeError):
        wr = pnl = pnl_ratio = 0
        days = followers = 0
        aum = 0

    instruments = trader.get("traderInsts", [])
    preferred_coins = []
    for inst in instruments[:20]:
        coin = inst.replace("-USDT", "").replace("-USD", "").replace("-PERP", "")
        if coin not in preferred_coins:
            preferred_coins.append(coin)

    # Estimate daily PnL
    daily_pnl = pnl / days if days > 0 else 0

    return {
        "source": "okx",
        "unique_code": trader.get("uniqueCode", ""),
        "nickname": trader.get("nickName", ""),
        "win_rate": round(wr, 4),
        "total_pnl_usd": round(pnl, 2),
        "pnl_ratio": round(pnl_ratio, 4),
        "lead_days": days,
        "followers": followers,
        "aum_usd": round(aum, 2),
        "estimated_daily_pnl": round(daily_pnl, 2),
        "preferred_coins": preferred_coins,
        "num_instruments": len(instruments),
        "profile_type": "stats_only",
        "trading_patterns": {
            "diversification": "high" if len(preferred_coins) > 10 else (
                "medium" if len(preferred_coins) > 5 else "concentrated"),
            "estimated_style": "swing" if days > 180 else "active",
            "follower_confidence": "high" if followers > 200 else (
                "medium" if followers > 50 else "low"),
        },
    }


# ---------------------------------------------------------------------------
# Main profiler
# ---------------------------------------------------------------------------

def build_wallet_profiles(max_hl_profiles: int = 20, max_okx_profiles: int = 30) -> Dict[str, Any]:
    """
    Build strategy profiles for top-performing wallets.

    For Hyperliquid wallets: fetches live fills from API.
    For OKX traders: uses database stats (no fill-level API available publicly).
    """
    logger.info("Building wallet strategy profiles...")

    # --- Hyperliquid Profiles ---
    hl_traders = load_hyperliquid_traders()
    hl_profiles = []

    for i, trader in enumerate(hl_traders[:max_hl_profiles]):
        address = trader.get("address", "")
        label = trader.get("label", "")
        logger.info(f"[{i+1}/{min(len(hl_traders), max_hl_profiles)}] Profiling HL: {label} ({address[:12]}...)")

        # Fetch fills from API
        fills = fetch_hl_fills(address)
        time.sleep(0.5)  # Rate limit

        if fills:
            fill_analysis = analyze_hl_fills(fills)
        else:
            fill_analysis = {"error": "no_fills_returned", "note": "Using database stats only"}

        # Combine database stats with fill analysis
        profile = {
            "source": "hyperliquid",
            "address": address,
            "label": label,
            "tier": trader.get("tier", ""),
            "account_value_usd": trader.get("account_value_usd", 0),
            "db_win_rate": trader.get("win_rate"),
            "db_closed_pnl": trader.get("total_closed_pnl_recent", 0),
            "db_closed_trades": trader.get("closed_trades_with_pnl", 0),
            "avg_leverage": trader.get("avg_leverage", 0),
            "coins_actively_trading": trader.get("coins_actively_trading", []),
            "num_open_positions": trader.get("num_open_positions", 0),
            "estimated_total_pnl": trader.get("estimated_total_pnl", ""),
            "fill_analysis": fill_analysis,
        }

        # Derive strategy insights
        coins = trader.get("coins_actively_trading", [])
        open_pos = trader.get("open_positions", [])

        # Position direction analysis from open positions
        long_pos = sum(1 for p in open_pos if p.get("direction") == "LONG")
        short_pos = sum(1 for p in open_pos if p.get("direction") == "SHORT")
        total_pos = long_pos + short_pos

        # Leverage distribution from open positions
        leverages = [p.get("leverage", 0) for p in open_pos if p.get("leverage")]

        profile["strategy_insights"] = {
            "diversification": "high" if len(coins) > 15 else (
                "medium" if len(coins) > 5 else "concentrated"),
            "current_directional_bias": (
                "long" if total_pos > 0 and long_pos / total_pos > 0.6 else
                ("short" if total_pos > 0 and short_pos / total_pos > 0.6 else "balanced")
            ),
            "current_long_ratio": round(long_pos / total_pos, 2) if total_pos > 0 else 0.5,
            "leverage_style": (
                "conservative" if trader.get("avg_leverage", 0) <= 5 else
                ("moderate" if trader.get("avg_leverage", 0) <= 15 else "aggressive")
            ),
            "avg_leverage": trader.get("avg_leverage", 0),
            "max_leverage": max(leverages) if leverages else 0,
            "min_leverage": min(leverages) if leverages else 0,
            "position_count": total_pos,
            "preferred_coins_top5": coins[:5],
        }

        # Entry filter recommendation
        lev = trader.get("avg_leverage", 0)
        if fill_analysis.get("directional_bias") == "long":
            profile["entry_filter"] = {
                "recommended_direction": "LONG",
                "max_leverage_match": min(lev * 1.5, 50) if lev > 0 else 10,
                "description": f"This wallet favors LONG positions at ~{lev}x leverage",
            }
        elif fill_analysis.get("directional_bias") == "short":
            profile["entry_filter"] = {
                "recommended_direction": "SHORT",
                "max_leverage_match": min(lev * 1.5, 50) if lev > 0 else 10,
                "description": f"This wallet favors SHORT positions at ~{lev}x leverage",
            }
        else:
            profile["entry_filter"] = {
                "recommended_direction": "BOTH",
                "max_leverage_match": min(lev * 1.5, 50) if lev > 0 else 10,
                "description": f"This wallet trades both directions at ~{lev}x leverage",
            }

        hl_profiles.append(profile)

    # --- OKX Profiles ---
    okx_traders = load_okx_traders()
    okx_profiles = []

    for trader in okx_traders[:max_okx_profiles]:
        profile = profile_okx_trader(trader)
        okx_profiles.append(profile)
        logger.info(f"Profiled OKX: {profile['nickname']} (WR={profile['win_rate']:.0%})")

    # --- Aggregate insights ---
    # Find consensus: what coins do the best traders agree on?
    coin_popularity: Dict[str, int] = defaultdict(int)
    for p in hl_profiles:
        for coin in p.get("coins_actively_trading", []):
            coin_popularity[coin] += 1
    for p in okx_profiles:
        for coin in p.get("preferred_coins", []):
            coin_popularity[coin] += 1

    top_consensus_coins = sorted(coin_popularity.items(), key=lambda x: x[1], reverse=True)[:20]

    # Directional consensus
    long_bias_count = sum(
        1 for p in hl_profiles
        if p.get("strategy_insights", {}).get("current_directional_bias") == "long"
    )
    short_bias_count = sum(
        1 for p in hl_profiles
        if p.get("strategy_insights", {}).get("current_directional_bias") == "short"
    )

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "hyperliquid": {
                "total_in_db": len(load_hyperliquid_traders.__wrapped__) if hasattr(load_hyperliquid_traders, '__wrapped__') else "see_metadata",
                "quality_filtered": len(hl_profiles),
                "filter_criteria": f"WR>={MIN_WIN_RATE:.0%}, trades>={MIN_CLOSED_TRADES}, PnL>=${MIN_CLOSED_PNL}",
            },
            "okx": {
                "quality_filtered": len(okx_profiles),
                "filter_criteria": "WR>=60%, days>=60, PnL>=$1000",
            },
        },
        "aggregate_insights": {
            "top_consensus_coins": [{"coin": c, "trader_count": n} for c, n in top_consensus_coins],
            "hl_directional_consensus": {
                "long_biased_wallets": long_bias_count,
                "short_biased_wallets": short_bias_count,
                "balanced_wallets": len(hl_profiles) - long_bias_count - short_bias_count,
                "overall_bias": (
                    "bullish" if long_bias_count > short_bias_count * 1.5 else
                    ("bearish" if short_bias_count > long_bias_count * 1.5 else "mixed")
                ),
            },
        },
        "hyperliquid_profiles": hl_profiles,
        "okx_profiles": okx_profiles,
    }

    # Fix sources metadata
    result["sources"]["hyperliquid"]["total_in_db"] = len(hl_traders) if hl_traders else 0

    # Save
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    logger.info(f"Wallet strategy profiles saved to {OUTPUT_FILE}")

    return result


# ---------------------------------------------------------------------------
# Integration helper
# ---------------------------------------------------------------------------

def get_wallet_consensus(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Get wallet consensus signal for a symbol.

    Returns dict with:
      - direction: "bullish" | "bearish" | "neutral"
      - confidence_boost: float in [-0.05, +0.05]
      - wallets_trading: number of profiled wallets trading this coin
      - top_wallet: label of the highest-PnL wallet trading this coin
    """
    sym = symbol.upper().replace("USDT", "").replace("-USD", "").replace("USD", "").replace("-PERP", "")

    try:
        if not OUTPUT_FILE.exists():
            return None

        with open(OUTPUT_FILE, encoding="utf-8") as f:
            data = json.load(f)

        hl_profiles = data.get("hyperliquid_profiles", [])
        okx_profiles = data.get("okx_profiles", [])

        wallets_long = 0
        wallets_short = 0
        wallets_trading = 0
        top_wallet = None
        top_pnl = 0

        for p in hl_profiles:
            coins = p.get("coins_actively_trading", [])
            if sym in coins:
                wallets_trading += 1
                # Check direction from open positions
                bias = p.get("strategy_insights", {}).get("current_directional_bias", "balanced")
                if bias == "long":
                    wallets_long += 1
                elif bias == "short":
                    wallets_short += 1

                pnl = p.get("db_closed_pnl", 0)
                if pnl > top_pnl:
                    top_pnl = pnl
                    top_wallet = p.get("label", p.get("address", "")[:12])

        for p in okx_profiles:
            coins = p.get("preferred_coins", [])
            if sym in coins:
                wallets_trading += 1

        if wallets_trading == 0:
            return None

        # Direction from consensus
        total_dir = wallets_long + wallets_short
        if total_dir > 0:
            net = (wallets_long - wallets_short) / total_dir
        else:
            net = 0

        if net > 0.2:
            direction = "bullish"
        elif net < -0.2:
            direction = "bearish"
        else:
            direction = "neutral"

        # Confidence boost: scale by number of wallets (more = stronger signal)
        boost = net * min(wallets_trading / 10, 1.0) * 0.05
        boost = max(-0.05, min(0.05, boost))

        return {
            "direction": direction,
            "confidence_boost": round(boost, 4),
            "wallets_trading": wallets_trading,
            "wallets_long": wallets_long,
            "wallets_short": wallets_short,
            "top_wallet": top_wallet,
            "top_wallet_pnl": round(top_pnl, 2),
            "source": "wallet_profiles",
        }
    except Exception as e:
        logger.debug(f"Wallet consensus lookup failed: {e}")
    return None


# ---------------------------------------------------------------------------
# Standalone
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = build_wallet_profiles(max_hl_profiles=20, max_okx_profiles=30)

    print(f"\nWallet Strategy Profiling Complete:")
    print(f"  Hyperliquid profiles: {len(result['hyperliquid_profiles'])}")
    print(f"  OKX profiles: {len(result['okx_profiles'])}")

    insights = result.get("aggregate_insights", {})
    print(f"\n  Directional consensus: {insights.get('hl_directional_consensus', {}).get('overall_bias', 'N/A')}")
    print(f"  Top consensus coins:")
    for c in insights.get("top_consensus_coins", [])[:10]:
        print(f"    {c['coin']}: {c['trader_count']} wallets")

    # Show top HL profiles
    print(f"\n  Top Hyperliquid wallet profiles:")
    for p in result["hyperliquid_profiles"][:5]:
        fa = p.get("fill_analysis", {})
        print(f"    {p['label']:30s} WR={p['db_win_rate']:.0%} "
              f"PnL=${p['db_closed_pnl']:,.0f} "
              f"bias={p.get('strategy_insights', {}).get('current_directional_bias', 'N/A')} "
              f"lev={p['avg_leverage']}x "
              f"hold={fa.get('avg_hold_time_hours', 'N/A')}h")
