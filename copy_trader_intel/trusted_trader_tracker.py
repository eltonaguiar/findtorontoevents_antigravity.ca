#!/usr/bin/env python3
"""
Trusted Trader Performance Tracker v1.0
========================================
Tracks per-trader performance for copy trader picks.
Maintains trust scores, per-symbol breakdowns, direction bias,
and generates tags/insights for the audit dashboard.

Outputs:
  data/trusted_traders.json   - Trust registry with performance history
  data/trusted_tags.json      - Dashboard tags per strategy prefix
  data/trader_insights.json   - Brain icon insights for audit dashboard
"""

import json
import sys
import os
import time
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Fix Windows charmap encoding
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

TRUSTED_FILE = DATA_DIR / "trusted_traders.json"
TAGS_FILE = DATA_DIR / "trusted_tags.json"
INSIGHTS_FILE = DATA_DIR / "trader_insights.json"
ACTIVE_PICKS_FILE = DATA_DIR / "active_picks.json"

# Alpha Engine carries the verified closed-trade history. Include it so trust
# scores reflect audited outcomes instead of just the current open book.
ALPHA_ACTIVE_PICKS_FILE = Path(__file__).parent.parent / "alpha_engine" / "data" / "active_picks.json"
ALPHA_CLOSED_PICKS_FILE = Path(__file__).parent.parent / "alpha_engine" / "data" / "closed_picks.json"

# ---------- Auto-blacklist thresholds ----------
BLACKLIST_PNL_THRESHOLD = -20.0    # % total PnL
BLACKLIST_WR_THRESHOLD = 0.25      # 25% WR
BLACKLIST_MIN_PICKS = 5            # Need at least N picks before blacklisting
PROBATION_WR_THRESHOLD = 0.40      # Below 40% WR = probation
TRUST_SCORE_BLACKLIST = 15         # Score below this = auto-blacklist

# ---------- Trust score weights ----------
WR_WEIGHT = 0.40
PNL_CONSISTENCY_WEIGHT = 0.30
DRAWDOWN_WEIGHT = 0.20
PICK_COUNT_WEIGHT = 0.10


# ==================== Price Fetcher (Binance + failover) ====================

def fetch_prices(symbols: list) -> dict:
    """Fetch current prices for symbols. Binance -> CoinGecko -> KuCoin -> CryptoCompare failover."""
    import urllib.request

    prices = {}
    remaining = list(set(symbols))

    # --- Binance (primary) ---
    binance_mirrors = [
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://api2.binance.com",
        "https://api3.binance.com",
    ]
    for mirror in binance_mirrors:
        if not remaining:
            break
        try:
            url = f"{mirror}/api/v3/ticker/price"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
            price_map = {item["symbol"]: float(item["price"]) for item in data}
            for sym in list(remaining):
                clean = sym.replace("-", "").replace("/", "").upper()
                if clean in price_map:
                    prices[sym] = price_map[clean]
                    remaining.remove(sym)
            break  # success on this mirror
        except Exception:
            continue

    # --- CoinGecko (fallback 1) ---
    if remaining:
        try:
            cg_ids = {
                "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
                "XRPUSDT": "ripple", "DOGEUSDT": "dogecoin", "BNBUSDT": "binancecoin",
                "ADAUSDT": "cardano", "AVAXUSDT": "avalanche-2", "DOTUSDT": "polkadot",
                "LINKUSDT": "chainlink", "MATICUSDT": "matic-network", "TONUSDT": "the-open-network",
                "NEARUSDT": "near", "SUIUSDT": "sui", "APTUSDT": "aptos",
                "WLDUSDT": "worldcoin-wld", "TRXUSDT": "tron", "ARBUSDT": "arbitrum",
                "OPUSDT": "optimism", "FILUSDT": "filecoin", "SEIUSDT": "sei-network",
                "TIAUSDT": "celestia", "INJUSDT": "injective-protocol", "JUPUSDT": "jupiter-exchange-solana",
                "WUSDT": "wormhole", "STXUSDT": "blockstack",
            }
            ids_needed = []
            sym_to_cg = {}
            for sym in remaining:
                clean = sym.replace("-", "").replace("/", "").upper()
                if clean in cg_ids:
                    ids_needed.append(cg_ids[clean])
                    sym_to_cg[sym] = cg_ids[clean]
            if ids_needed:
                ids_str = ",".join(ids_needed[:50])
                url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_str}&vs_currencies=usd"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                for sym, cg_id in sym_to_cg.items():
                    if cg_id in data and "usd" in data[cg_id]:
                        prices[sym] = float(data[cg_id]["usd"])
                        if sym in remaining:
                            remaining.remove(sym)
        except Exception:
            pass

    # --- KuCoin (fallback 2) ---
    if remaining:
        try:
            url = "https://api.kucoin.com/api/v1/market/allTickers"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
            tickers = data.get("data", {}).get("ticker", [])
            kucoin_map = {}
            for t in tickers:
                s = t.get("symbol", "").replace("-", "")
                kucoin_map[s] = float(t.get("last", 0))
            for sym in list(remaining):
                clean = sym.replace("-", "").replace("/", "").upper()
                if clean in kucoin_map and kucoin_map[clean] > 0:
                    prices[sym] = kucoin_map[clean]
                    remaining.remove(sym)
        except Exception:
            pass

    # --- CryptoCompare (fallback 3) ---
    if remaining:
        try:
            for sym in list(remaining):
                base = sym.replace("USDT", "").replace("USD", "").replace("PERP", "")
                url = f"https://min-api.cryptocompare.com/data/price?fsym={base}&tsyms=USD"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode())
                if "USD" in data and data["USD"] > 0:
                    prices[sym] = float(data["USD"])
                    remaining.remove(sym)
        except Exception:
            pass

    return prices


# ==================== Trust Score Calculator ====================

def calculate_trust_score(stats: dict) -> int:
    """
    Calculate trust score (0-100) based on:
      WR (40%), PnL consistency (30%), drawdown (20%), pick count (10%)
    """
    total_picks = stats.get("total_picks", 0)
    wins = stats.get("wins", 0)
    losses = stats.get("losses", 0)
    total_pnl = stats.get("total_pnl_pct", 0.0)
    max_drawdown = stats.get("max_single_loss_pct", 0.0)

    # WR component (0-100)
    if total_picks > 0:
        wr = wins / total_picks
    else:
        wr = 0.5  # neutral if no data
    wr_score = min(100, wr * 120)  # 83% WR = 100 score

    # PnL consistency component (0-100)
    # Positive PnL = good, scale linearly
    if total_pnl > 0:
        pnl_score = min(100, total_pnl * 5)  # +20% = 100
    elif total_pnl > -5:
        pnl_score = max(0, 50 + total_pnl * 10)  # -5% = 0
    else:
        pnl_score = 0

    # Drawdown component (0-100, lower drawdown = higher score)
    if max_drawdown >= 0:
        dd_score = 100  # no drawdown
    else:
        dd_score = max(0, 100 + max_drawdown * 2)  # -50% = 0

    # Pick count component (0-100, more picks = more reliable)
    count_score = min(100, total_picks * 5)  # 20 picks = 100

    # Weighted total
    score = (
        wr_score * WR_WEIGHT +
        pnl_score * PNL_CONSISTENCY_WEIGHT +
        dd_score * DRAWDOWN_WEIGHT +
        count_score * PICK_COUNT_WEIGHT
    )

    return max(0, min(100, int(round(score))))


# ==================== Performance Analyzer ====================

def analyze_trader_picks(picks: list, strategy_prefix: str) -> dict:
    """Analyze all picks for a given strategy prefix and return performance stats."""
    trader_picks = [p for p in picks if isinstance(p, dict)
                    and p.get("strategy", "") == strategy_prefix]

    if not trader_picks:
        return {}

    stats = {
        "total_picks": 0,
        "open_picks": 0,
        "closed_picks": 0,
        "wins": 0,
        "losses": 0,
        "win_rate": 0.0,
        "total_pnl_pct": 0.0,
        "total_pnl_dollar": 0.0,
        "best_trade": None,
        "worst_trade": None,
        "max_single_loss_pct": 0.0,
        "per_symbol": {},
        "direction_stats": {"LONG": {"count": 0, "wins": 0, "pnl": 0.0},
                            "SHORT": {"count": 0, "wins": 0, "pnl": 0.0}},
        "hold_times": [],
        "rolling_7d": {"picks": 0, "wins": 0, "pnl": 0.0},
        "symbols_traded": [],
    }

    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    for pick in trader_picks:
        stats["total_picks"] += 1
        status = pick.get("status", "OPEN")
        symbol = pick.get("symbol", "UNKNOWN")
        direction = pick.get("direction", pick.get("signal_type", "LONG")).upper()
        if direction in ("SELL",):
            direction = "SHORT"
        elif direction in ("BUY",):
            direction = "LONG"

        pnl_pct = pick.get("pnl_pct")
        pnl_dollar = pick.get("pnl_dollar")
        entry_price = pick.get("entry_price", 0)
        exit_price = pick.get("exit_price")
        hold_days = pick.get("hold_days")

        # Track per-symbol
        if symbol not in stats["per_symbol"]:
            stats["per_symbol"][symbol] = {
                "picks": 0, "wins": 0, "losses": 0,
                "total_pnl_pct": 0.0, "directions": []
            }
        stats["per_symbol"][symbol]["picks"] += 1
        stats["per_symbol"][symbol]["directions"].append(direction)

        # Track direction
        if direction in stats["direction_stats"]:
            stats["direction_stats"][direction]["count"] += 1

        if status == "OPEN":
            stats["open_picks"] += 1
            continue

        # Closed trade analysis
        stats["closed_picks"] += 1

        if pnl_pct is not None:
            pnl_val = float(pnl_pct)
            stats["total_pnl_pct"] += pnl_val

            if pnl_val > 0:
                stats["wins"] += 1
                stats["per_symbol"][symbol]["wins"] += 1
                if direction in stats["direction_stats"]:
                    stats["direction_stats"][direction]["wins"] += 1
            else:
                stats["losses"] += 1
                stats["per_symbol"][symbol]["losses"] += 1

            if direction in stats["direction_stats"]:
                stats["direction_stats"][direction]["pnl"] += pnl_val

            stats["per_symbol"][symbol]["total_pnl_pct"] += pnl_val

            # Track max loss
            if pnl_val < stats["max_single_loss_pct"]:
                stats["max_single_loss_pct"] = pnl_val

            # Best/worst trade
            trade_info = {"symbol": symbol, "direction": direction,
                          "pnl_pct": pnl_val, "entry": entry_price, "exit": exit_price}
            if stats["best_trade"] is None or pnl_val > stats["best_trade"]["pnl_pct"]:
                stats["best_trade"] = trade_info
            if stats["worst_trade"] is None or pnl_val < stats["worst_trade"]["pnl_pct"]:
                stats["worst_trade"] = trade_info

        if pnl_dollar is not None:
            stats["total_pnl_dollar"] += float(pnl_dollar)

        if hold_days is not None:
            stats["hold_times"].append(float(hold_days))

        # Rolling 7-day
        detected = pick.get("detected_at", pick.get("entry_date", ""))
        try:
            if "T" in str(detected):
                dt = datetime.fromisoformat(str(detected).replace("Z", "+00:00"))
            else:
                dt = datetime.strptime(str(detected)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if dt >= seven_days_ago:
                stats["rolling_7d"]["picks"] += 1
                if pnl_pct is not None and float(pnl_pct) > 0:
                    stats["rolling_7d"]["wins"] += 1
                if pnl_pct is not None:
                    stats["rolling_7d"]["pnl"] += float(pnl_pct)
        except Exception:
            pass

    # Calculate WR
    closed = stats["closed_picks"]
    if closed > 0:
        stats["win_rate"] = round(stats["wins"] / closed, 4)
    else:
        stats["win_rate"] = 0.0

    # Direction WR
    for d in ["LONG", "SHORT"]:
        ds = stats["direction_stats"][d]
        if ds["count"] > 0:
            ds["wr"] = round(ds["wins"] / ds["count"], 4)
            ds["pct_of_total"] = round(ds["count"] / max(1, stats["total_picks"]) * 100, 1)
        else:
            ds["wr"] = 0.0
            ds["pct_of_total"] = 0.0

    # Symbol list
    stats["symbols_traded"] = sorted(stats["per_symbol"].keys())

    # Best symbols (sorted by PnL)
    symbol_ranking = sorted(
        stats["per_symbol"].items(),
        key=lambda x: x[1]["total_pnl_pct"],
        reverse=True
    )
    stats["best_symbols"] = [s[0] for s in symbol_ranking[:5] if s[1]["total_pnl_pct"] > 0]
    stats["worst_symbols"] = [s[0] for s in symbol_ranking[-3:] if s[1]["total_pnl_pct"] < 0]

    # Average hold time
    if stats["hold_times"]:
        stats["avg_hold_days"] = round(sum(stats["hold_times"]) / len(stats["hold_times"]), 2)
    else:
        stats["avg_hold_days"] = None

    # Round PnL
    stats["total_pnl_pct"] = round(stats["total_pnl_pct"], 2)
    stats["total_pnl_dollar"] = round(stats["total_pnl_dollar"], 2)

    return stats


def compute_unrealized_pnl(picks: list, strategy_prefix: str, prices: dict) -> list:
    """Compute unrealized PnL for open positions given current prices."""
    open_picks = [p for p in picks if isinstance(p, dict)
                  and p.get("strategy", "") == strategy_prefix
                  and p.get("status", "OPEN") == "OPEN"]

    results = []
    for pick in open_picks:
        symbol = pick.get("symbol", "")
        entry = pick.get("entry_price", 0)
        direction = pick.get("direction", "LONG").upper()
        if direction in ("SELL",):
            direction = "SHORT"

        current = prices.get(symbol, 0)
        if entry > 0 and current > 0:
            if direction == "LONG":
                pnl_pct = (current - entry) / entry * 100
            else:
                pnl_pct = (entry - current) / entry * 100
            results.append({
                "symbol": symbol, "direction": direction,
                "entry": entry, "current": current,
                "unrealized_pnl_pct": round(pnl_pct, 2)
            })

    return results


# ==================== Trust Registry ====================

def load_trust_registry() -> dict:
    """Load existing trust registry or create new one."""
    if TRUSTED_FILE.exists():
        try:
            with open(TRUSTED_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"generated_at": None, "traders": {}}


def save_trust_registry(registry: dict):
    """Save trust registry to disk."""
    registry["generated_at"] = datetime.now(timezone.utc).isoformat()
    with open(TRUSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, default=str)


# ==================== Initial Trader Definitions ====================

KNOWN_TRADERS = {
    "copy_hl_NMTD_25M": {
        "label": "NMTD_25M",
        "description": "Short-biased scalper, +8.9% PnL",
        "initial_trust": "TRUSTED",
    },
    "copy_hl_whale_123M_87roi": {
        "label": "whale_123M_87roi",
        "description": "Balanced direction, 67% WR",
        "initial_trust": "TRUSTED",
    },
    "copy_hl_whale_24.5M": {
        "label": "whale_24.5M",
        "description": "Most diversified, 61% WR, 44 picks",
        "initial_trust": "TRUSTED",
    },
    "copy_hl_whale_58M_287roi": {
        "label": "whale_58M_287roi",
        "description": "Was best performer before closing positions",
        "initial_trust": "TRUSTED",
    },
    "copy_hl_PensionFund_24M": {
        "label": "PensionFund_24M",
        "description": "0% WR, always losing",
        "initial_trust": "BLACKLISTED",
    },
    "copy_hl_whale_7.7M_acct": {
        "label": "whale_7.7M_acct",
        "description": "25% WR",
        "initial_trust": "UNTRUSTED",
    },
    "copy_hl_lb_jeff lover": {
        "label": "lb_jeff lover",
        "description": "Catastrophic -44% loss",
        "initial_trust": "BLACKLISTED",
    },
}


# ==================== Insight Generator ====================

def generate_insights(registry: dict, all_picks: list) -> list:
    """Generate brain-icon insights from trader performance data."""
    insights = []

    for prefix, trader in registry.get("traders", {}).items():
        label = trader.get("label", prefix)
        trust = trader.get("trust_status", "UNKNOWN")
        stats = trader.get("performance", {})
        wr = stats.get("win_rate", 0)
        total_pnl = stats.get("total_pnl_pct", 0)
        best_symbols = stats.get("best_symbols", [])
        worst_symbols = stats.get("worst_symbols", [])
        per_symbol = stats.get("per_symbol", {})
        dir_stats = stats.get("direction_stats", {})

        # Trust-level insight
        if trust == "BLACKLISTED":
            reason = trader.get("blacklist_reason", f"{wr:.0%} WR, {total_pnl:+.1f}% PnL")
            insights.append({
                "type": "AVOID",
                "trader": label,
                "prefix": prefix,
                "text": f"{label} has been BLACKLISTED. {reason}.",
                "severity": "critical"
            })
            continue

        if trust == "PROBATION":
            insights.append({
                "type": "WARN",
                "trader": label,
                "prefix": prefix,
                "text": f"{label} is on PROBATION -- WR={wr:.0%}, PnL={total_pnl:+.1f}%. Monitor closely.",
                "severity": "warning"
            })

        # Direction bias insight
        long_stats = dir_stats.get("LONG", {})
        short_stats = dir_stats.get("SHORT", {})
        long_pct = long_stats.get("pct_of_total", 50)
        short_pct = short_stats.get("pct_of_total", 50)
        long_wr = long_stats.get("wr", 0)
        short_wr = short_stats.get("wr", 0)

        if short_pct > 60:
            insights.append({
                "type": "INFO",
                "trader": label,
                "prefix": prefix,
                "text": f"{label} is short-biased ({short_pct:.0f}% shorts). "
                        f"Short WR: {short_wr:.0%}, Long WR: {long_wr:.0%}.",
                "severity": "info"
            })
        elif long_pct > 70:
            insights.append({
                "type": "INFO",
                "trader": label,
                "prefix": prefix,
                "text": f"{label} is heavily long-biased ({long_pct:.0f}% longs). "
                        f"Long WR: {long_wr:.0%}.",
                "severity": "info"
            })

        # Best symbol insights
        if best_symbols:
            sym_details = []
            for sym in best_symbols[:3]:
                sym_data = per_symbol.get(sym, {})
                sym_pnl = sym_data.get("total_pnl_pct", 0)
                sym_details.append(f"{sym} {sym_pnl:+.1f}%")
            if sym_details:
                insights.append({
                    "type": "TRUST",
                    "trader": label,
                    "prefix": prefix,
                    "text": f"{label} excels at: {', '.join(sym_details)}.",
                    "severity": "positive"
                })

        # Worst symbol warnings
        for sym in worst_symbols:
            sym_data = per_symbol.get(sym, {})
            sym_pnl = sym_data.get("total_pnl_pct", 0)
            if sym_pnl < -10:
                # Determine dominant direction for this symbol
                dirs = sym_data.get("directions", [])
                dom_dir = max(set(dirs), key=dirs.count) if dirs else "UNKNOWN"
                insights.append({
                    "type": "AVOID",
                    "trader": label,
                    "prefix": prefix,
                    "text": f"{label} has catastrophic {sym} {dom_dir} ({sym_pnl:+.1f}%) -- avoid {sym} {dom_dir.lower()}s from this trader.",
                    "severity": "warning"
                })

    # Cross-trader symbol consensus
    symbol_directions = {}
    for pick in all_picks:
        if not isinstance(pick, dict):
            continue
        strategy = pick.get("strategy", "")
        if not strategy.startswith("copy_hl_"):
            continue
        # Only count trusted traders
        trader_entry = registry.get("traders", {}).get(strategy, {})
        if trader_entry.get("trust_status") not in ("TRUSTED", "PROBATION"):
            continue
        symbol = pick.get("symbol", "")
        direction = pick.get("direction", "LONG").upper()
        if direction in ("SELL",):
            direction = "SHORT"
        elif direction in ("BUY",):
            direction = "LONG"
        if symbol:
            symbol_directions.setdefault(symbol, []).append({
                "trader": trader_entry.get("label", strategy),
                "direction": direction
            })

    for symbol, entries in symbol_directions.items():
        if len(entries) < 2:
            continue
        long_traders = [e["trader"] for e in entries if e["direction"] == "LONG"]
        short_traders = [e["trader"] for e in entries if e["direction"] == "SHORT"]
        if long_traders and short_traders:
            insights.append({
                "type": "WARN",
                "trader": "CONSENSUS",
                "prefix": symbol,
                "text": f"{symbol}: mixed signals -- {len(short_traders)} trader(s) short ({', '.join(short_traders[:3])}), "
                        f"{len(long_traders)} trader(s) long ({', '.join(long_traders[:3])}).",
                "severity": "warning"
            })
        elif len(long_traders) >= 2:
            insights.append({
                "type": "TRUST",
                "trader": "CONSENSUS",
                "prefix": symbol,
                "text": f"{symbol}: {len(long_traders)} trusted traders agree LONG ({', '.join(long_traders[:3])}).",
                "severity": "positive"
            })
        elif len(short_traders) >= 2:
            insights.append({
                "type": "TRUST",
                "trader": "CONSENSUS",
                "prefix": symbol,
                "text": f"{symbol}: {len(short_traders)} trusted traders agree SHORT ({', '.join(short_traders[:3])}).",
                "severity": "positive"
            })

    return insights


# ==================== Tag Generator ====================

def generate_tags(registry: dict) -> dict:
    """Generate trusted_tags.json for audit dashboard consumption."""
    tags = {}

    for prefix, trader in registry.get("traders", {}).items():
        stats = trader.get("performance", {})
        trust = trader.get("trust_status", "UNKNOWN")
        score = trader.get("trust_score", 0)
        wr = stats.get("win_rate", 0)
        total_pnl = stats.get("total_pnl_pct", 0)
        best_symbols = stats.get("best_symbols", [])

        tag = {
            "trust": trust,
            "score": score,
            "wr": round(wr * 100, 1) if wr <= 1 else round(wr, 1),
            "pnl": f"{total_pnl:+.1f}%",
            "total_picks": stats.get("total_picks", 0),
            "closed_picks": stats.get("closed_picks", 0),
            "wins": stats.get("wins", 0),
            "losses": stats.get("losses", 0),
            "best_symbols": best_symbols[:5],
        }

        if trust == "BLACKLISTED":
            tag["reason"] = trader.get("blacklist_reason", "Auto-blacklisted")

        if trust == "PROBATION":
            tag["reason"] = trader.get("probation_reason", "Low performance")

        tags[prefix] = tag

    return tags


# ==================== Main Run ====================

def run():
    """
    Main entry point.
    Loads picks, updates trust registry, generates tags and insights.
    """
    print("\n" + "=" * 60)
    print("  TRUSTED TRADER TRACKER v1.0")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    # Load all picks (copy_trader_intel live + alpha_engine active + alpha_engine closed)
    all_picks = []
    for picks_file in [ACTIVE_PICKS_FILE, ALPHA_ACTIVE_PICKS_FILE, ALPHA_CLOSED_PICKS_FILE]:
        if picks_file.exists():
            try:
                with open(picks_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    all_picks.extend(data)
                    print(f"  [OK] Loaded {len(data)} picks from {picks_file.name}")
            except Exception as e:
                print(f"  [WARN] Failed to load {picks_file}: {e}")

    if not all_picks:
        print("  [WARN] No picks found. Nothing to track.")
        return

    # Deduplicate by ID
    seen_ids = set()
    unique_picks = []
    for p in all_picks:
        if not isinstance(p, dict):
            continue
        pid = p.get("id", "")
        if pid and pid in seen_ids:
            continue
        if pid:
            seen_ids.add(pid)
        unique_picks.append(p)
    all_picks = unique_picks
    print(f"  [OK] {len(all_picks)} unique picks after dedup")

    # Discover all copy_hl_ strategies
    hl_strategies = set()
    for p in all_picks:
        strat = p.get("strategy", "")
        if strat.startswith("copy_hl_"):
            hl_strategies.add(strat)

    print(f"  [OK] Found {len(hl_strategies)} Hyperliquid copy trader strategies")

    # Fetch live prices for unrealized PnL
    symbols = list(set(p.get("symbol", "") for p in all_picks if p.get("status") == "OPEN"))
    symbols = [s for s in symbols if s]
    prices = {}
    if symbols:
        print(f"  Fetching prices for {len(symbols)} symbols...")
        try:
            prices = fetch_prices(symbols)
            print(f"  [OK] Got prices for {len(prices)}/{len(symbols)} symbols")
        except Exception as e:
            print(f"  [WARN] Price fetch failed: {e}")

    # Load existing registry
    registry = load_trust_registry()
    if "traders" not in registry:
        registry["traders"] = {}

    # Process each strategy
    for prefix in sorted(hl_strategies):
        # Get or create trader entry
        if prefix not in registry["traders"]:
            known = KNOWN_TRADERS.get(prefix, {})
            registry["traders"][prefix] = {
                "label": known.get("label", prefix.replace("copy_hl_", "")),
                "strategy_prefix": prefix,
                "trust_status": known.get("initial_trust", "UNKNOWN"),
                "description": known.get("description", ""),
                "trust_score": 50,
                "first_seen": datetime.now(timezone.utc).isoformat(),
                "status_history": [],
                "performance": {},
            }

        trader = registry["traders"][prefix]

        # Analyze performance
        stats = analyze_trader_picks(all_picks, prefix)
        if stats:
            trader["performance"] = stats
            trader["last_updated"] = datetime.now(timezone.utc).isoformat()

            # Compute unrealized PnL for open positions
            unrealized = compute_unrealized_pnl(all_picks, prefix, prices)
            if unrealized:
                total_unreal = sum(u["unrealized_pnl_pct"] for u in unrealized)
                trader["performance"]["unrealized_positions"] = unrealized
                trader["performance"]["total_unrealized_pnl_pct"] = round(total_unreal, 2)

            # Calculate trust score
            score = calculate_trust_score(stats)
            old_score = trader.get("trust_score", 50)
            trader["trust_score"] = score

            # Auto-trust management
            old_status = trader.get("trust_status", "UNKNOWN")
            new_status = old_status

            closed = stats.get("closed_picks", 0)
            wr = stats.get("win_rate", 0)
            pnl = stats.get("total_pnl_pct", 0)

            # Auto-blacklist rules
            if closed >= BLACKLIST_MIN_PICKS:
                if pnl < BLACKLIST_PNL_THRESHOLD:
                    new_status = "BLACKLISTED"
                    trader["blacklist_reason"] = f"PnL {pnl:+.1f}% below {BLACKLIST_PNL_THRESHOLD}% threshold"
                elif wr < BLACKLIST_WR_THRESHOLD:
                    new_status = "BLACKLISTED"
                    trader["blacklist_reason"] = f"WR {wr:.0%} below {BLACKLIST_WR_THRESHOLD:.0%} threshold after {closed} picks"
                elif score < TRUST_SCORE_BLACKLIST:
                    new_status = "BLACKLISTED"
                    trader["blacklist_reason"] = f"Trust score {score} below {TRUST_SCORE_BLACKLIST}"
                elif wr < PROBATION_WR_THRESHOLD and old_status != "BLACKLISTED":
                    new_status = "PROBATION"
                    trader["probation_reason"] = f"WR {wr:.0%} below {PROBATION_WR_THRESHOLD:.0%}"

            # Record status change
            if new_status != old_status:
                trader["trust_status"] = new_status
                trader["status_history"].append({
                    "from": old_status,
                    "to": new_status,
                    "at": datetime.now(timezone.utc).isoformat(),
                    "reason": trader.get("blacklist_reason", trader.get("probation_reason", "auto")),
                    "score_at_change": score,
                })
                print(f"  [STATUS] {trader['label']}: {old_status} -> {new_status} (score={score})")

    # Save registry
    save_trust_registry(registry)
    print(f"\n  [OK] Saved trust registry ({len(registry['traders'])} traders)")

    # Generate tags
    tags = generate_tags(registry)
    with open(TAGS_FILE, "w", encoding="utf-8") as f:
        json.dump(tags, f, indent=2, default=str)
    print(f"  [OK] Saved trusted tags to {TAGS_FILE.name}")

    # Generate insights
    insights = generate_insights(registry, all_picks)
    with open(INSIGHTS_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_insights": len(insights),
            "insights": insights
        }, f, indent=2, default=str)
    print(f"  [OK] Saved {len(insights)} insights to {INSIGHTS_FILE.name}")

    # Print summary table
    print(f"\n{'=' * 80}")
    print(f"  {'Trader':<25} {'Trust':<12} {'Score':>5} {'Picks':>6} {'WR':>6} {'PnL':>8} {'Best Symbols'}")
    print(f"  {'-'*25} {'-'*12} {'-'*5} {'-'*6} {'-'*6} {'-'*8} {'-'*20}")

    for prefix in sorted(registry["traders"].keys()):
        t = registry["traders"][prefix]
        s = t.get("performance", {})
        label = t.get("label", "?")[:24]
        trust = t.get("trust_status", "?")
        score = t.get("trust_score", 0)
        total = s.get("total_picks", 0)
        wr = s.get("win_rate", 0)
        pnl = s.get("total_pnl_pct", 0)
        best = s.get("best_symbols", [])[:3]
        best_str = ",".join(best) if best else "-"

        trust_marker = ""
        if trust == "TRUSTED":
            trust_marker = "[TRUST]"
        elif trust == "BLACKLISTED":
            trust_marker = "[AVOID]"
        elif trust == "PROBATION":
            trust_marker = "[WARN]"
        else:
            trust_marker = "[----]"

        print(f"  {label:<25} {trust_marker:<12} {score:>5} {total:>6} {wr:>5.0%} {pnl:>+7.1f}% {best_str}")

    print(f"{'=' * 80}")

    # Print key insights
    critical = [i for i in insights if i.get("severity") in ("critical", "warning")]
    if critical:
        print(f"\n  Key Insights:")
        for ins in critical[:10]:
            marker = f"  [{ins['type']}]"
            print(f"  {marker} {ins['text']}")

    print()
    return registry


if __name__ == "__main__":
    run()
