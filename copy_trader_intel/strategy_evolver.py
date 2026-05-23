#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Strategy Evolver - Mutation Engine for Copy Trader Strategies
==============================================================
Takes reverse-engineered trader DNA profiles and generates strategy mutations,
then paper-trades each mutation to find which variations outperform.

Mutation types:
  tight_scalp      - 1.5% TP, 1% SL, 4h max hold, only top 3 coins
  momentum_ride    - 3% TP, 1.5% SL, follow trend only
  contrarian_fade  - Same TP/SL but fade the trader on losing streaks
  consensus_only   - Only take picks when 2+ traders agree
  high_confidence  - Only take picks with confidence > 0.7
  volatility_filter- Skip trades during low-vol periods
  time_filtered    - Only trade during trader's peak hours
  size_scaled      - Scale position by trader's historical WR on that symbol

After 10+ closed trades: compute score boosts (WR * PnL_factor).
After 20+ trades: eliminate bottom 25% of mutations per trader.
"""

import sys
import io

# Windows UTF-8 fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import json
import math
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

STRATEGY_PROFILES_FILE = DATA_DIR / "strategy_profiles.json"
ACTIVE_PICKS_FILE = DATA_DIR / "active_picks.json"
MUTATION_FORWARD_TEST_FILE = DATA_DIR / "mutation_forward_test.json"
MUTATION_SCORES_FILE = DATA_DIR / "mutation_scores.json"

INITIAL_CAPITAL = 500.0

# ---------------------------------------------------------------------------
# Binance price API -- 3+ failover chain (per CLAUDE.md rules)
# ---------------------------------------------------------------------------
BINANCE_ENDPOINTS = [
    "https://data-api.binance.vision/api/v3/ticker/price?symbol={}",
    "https://api.binance.us/api/v3/ticker/price?symbol={}",
    "https://api.binance.com/api/v3/ticker/price?symbol={}",
]
COINGECKO_MAP = {
    "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
    "XRPUSDT": "ripple", "ADAUSDT": "cardano", "DOTUSDT": "polkadot",
    "LINKUSDT": "chainlink", "AVAXUSDT": "avalanche-2",
    "SUIUSDT": "sui", "TONUSDT": "the-open-network",
    "HYPEUSDT": "hyperliquid", "TAOUSDT": "bittensor",
    "WLDUSDT": "worldcoin-wld", "CRVUSDT": "curve-dao-token",
    "AAVEUSDT": "aave", "ZECUSDT": "zcash", "XMRUSDT": "monero",
    "DOGEUSDT": "dogecoin", "NEARUSDT": "near", "ARBUSDT": "arbitrum",
}
KUCOIN_TEMPLATE = "https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={}-USDT"
CRYPTOCOMPARE_TEMPLATE = "https://min-api.cryptocompare.com/data/price?fsym={}&tsyms=USD"


def _fetch_url(url, timeout=8):
    """Fetch JSON from URL with timeout."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "StratEvolver/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def get_price(symbol):
    """Get current price with 3+ failover chain: Binance mirrors -> CoinGecko -> KuCoin -> CryptoCompare."""
    sym = symbol.upper().replace("-", "").replace("/", "")
    if not sym.endswith("USDT") and not sym.endswith("USD"):
        sym = sym + "USDT"

    # 1. Binance mirrors
    for endpoint in BINANCE_ENDPOINTS:
        data = _fetch_url(endpoint.format(sym))
        if data and "price" in data:
            return float(data["price"])

    base = sym.replace("USDT", "").replace("USD", "")

    # 2. CoinGecko fallback
    cg_id = COINGECKO_MAP.get(sym)
    if cg_id:
        data = _fetch_url(
            "https://api.coingecko.com/api/v3/simple/price?ids={}&vs_currencies=usd".format(cg_id)
        )
        if data and cg_id in data:
            return float(data[cg_id]["usd"])

    # 3. KuCoin fallback
    data = _fetch_url(KUCOIN_TEMPLATE.format(base))
    if data and data.get("data") and data["data"].get("price"):
        return float(data["data"]["price"])

    # 4. CryptoCompare fallback
    data = _fetch_url(CRYPTOCOMPARE_TEMPLATE.format(base))
    if data and "USD" in data:
        return float(data["USD"])

    return None


# ---------------------------------------------------------------------------
# Symbol normalization
# ---------------------------------------------------------------------------
def normalize_symbol(sym):
    """Convert raw symbol to Binance-compatible format."""
    s = sym.upper().replace("/", "").replace("-", "")
    # Skip non-crypto symbols
    if ":" in sym or s.startswith("@"):
        return None
    if not s.endswith("USDT") and not s.endswith("USD"):
        s += "USDT"
    # kPEPE -> PEPEUSDT
    if s.startswith("K") and len(s) > 5:
        s = s[1:]
    return s


# ---------------------------------------------------------------------------
# Mutation definitions
# ---------------------------------------------------------------------------
MUTATION_DEFS = {
    "tight_scalp": {
        "tp_pct": 1.5,
        "sl_pct": 1.0,
        "max_hold_hours": 4,
        "coin_filter": "top3",
        "description": "Tight Scalp: 1.5% TP, 1% SL, 4h max, top 3 coins only",
    },
    "momentum_ride": {
        "tp_pct": 3.0,
        "sl_pct": 1.5,
        "max_hold_hours": 12,
        "requires_trend": True,
        "description": "Momentum Ride: 3% TP, 1.5% SL, follow trend only",
    },
    "contrarian_fade": {
        "tp_pct": 3.0,
        "sl_pct": 1.5,
        "max_hold_hours": 12,
        "fade_on_streak": True,
        "description": "Contrarian Fade: invert direction when trader on losing streak",
    },
    "consensus_only": {
        "tp_pct": 2.5,
        "sl_pct": 1.5,
        "max_hold_hours": 12,
        "requires_consensus": True,
        "description": "Consensus Only: trade only when 2+ traders agree",
    },
    "high_confidence": {
        "tp_pct": 3.0,
        "sl_pct": 1.5,
        "max_hold_hours": 12,
        "min_confidence": 0.7,
        "description": "High Confidence: only picks with confidence > 0.7",
    },
    "volatility_filter": {
        "tp_pct": 3.0,
        "sl_pct": 1.5,
        "max_hold_hours": 12,
        "skip_low_vol": True,
        "description": "Volatility Filter: skip during low-vol periods",
    },
    "time_filtered": {
        "tp_pct": 3.0,
        "sl_pct": 1.5,
        "max_hold_hours": 12,
        "time_filtered": True,
        "description": "Time Filtered: only trade during trader's peak hours",
    },
    "size_scaled": {
        "tp_pct": 3.0,
        "sl_pct": 1.5,
        "max_hold_hours": 12,
        "scale_by_wr": True,
        "description": "Size Scaled: scale position by trader's WR on symbol",
    },
}


# ---------------------------------------------------------------------------
# JSON I/O helpers
# ---------------------------------------------------------------------------
def load_json(path):
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# Empty mutation portfolio
# ---------------------------------------------------------------------------
def _empty_mutation(mkey, mdef):
    return {
        "status": "ACTIVE",
        "description": mdef["description"],
        "capital": INITIAL_CAPITAL,
        "trades": 0,
        "wins": 0,
        "losses": 0,
        "wr": 0.0,
        "pnl_dollar": 0.0,
        "pnl_pct": 0.0,
        "profit_factor": 0.0,
        "max_drawdown_pct": 0.0,
        "sharpe_ratio": 0.0,
        "score_boost": 0.0,
        "open_positions": {},
        "closed_trades": [],
        "elimination_reason": None,
        "eliminated_at": None,
        "peak_capital": INITIAL_CAPITAL,
        "returns_list": [],
    }


# ---------------------------------------------------------------------------
# Metrics computation
# ---------------------------------------------------------------------------
def _compute_metrics(mut_data):
    """Recompute WR, PnL, profit factor, max drawdown, Sharpe from closed trades."""
    closed = mut_data.get("closed_trades", [])
    if not closed:
        return

    wins = sum(1 for t in closed if t.get("result") == "WIN")
    losses = sum(1 for t in closed if t.get("result") == "LOSS")
    total = wins + losses
    mut_data["trades"] = total
    mut_data["wins"] = wins
    mut_data["losses"] = losses
    mut_data["wr"] = round(wins / total, 4) if total else 0.0

    gross_profit = sum(t.get("pnl_dollar", 0) for t in closed if t.get("pnl_dollar", 0) > 0)
    gross_loss = abs(sum(t.get("pnl_dollar", 0) for t in closed if t.get("pnl_dollar", 0) < 0))
    mut_data["pnl_dollar"] = round(sum(t.get("pnl_dollar", 0) for t in closed), 4)
    mut_data["pnl_pct"] = round(mut_data["pnl_dollar"] / INITIAL_CAPITAL * 100, 2)
    mut_data["profit_factor"] = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 99.99

    # Max drawdown
    equity = INITIAL_CAPITAL
    peak = equity
    max_dd = 0.0
    for t in closed:
        equity += t.get("pnl_dollar", 0)
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
    mut_data["max_drawdown_pct"] = round(max_dd * 100, 2)
    mut_data["capital"] = round(INITIAL_CAPITAL + mut_data["pnl_dollar"], 2)

    # Sharpe ratio (annualized, ~6 trades/day assumption)
    returns = mut_data.get("returns_list", [])
    if len(returns) >= 5:
        mean_r = sum(returns) / len(returns)
        variance = sum((r - mean_r) ** 2 for r in returns) / len(returns)
        std_r = math.sqrt(variance) if variance > 0 else 0.001
        # Annualize: sqrt(252 * 6) ~ sqrt(1512) ~ 38.9
        mut_data["sharpe_ratio"] = round((mean_r / std_r) * 38.9, 2)
    else:
        mut_data["sharpe_ratio"] = 0.0


# ---------------------------------------------------------------------------
# Score boosting -- after 10+ closed trades
# ---------------------------------------------------------------------------
def _compute_score_boost(mut_data):
    """Compute performance multiplier: WR * PnL_factor.
    PnL_factor = (capital / INITIAL_CAPITAL) clamped to [0.5, 3.0].
    Returns a score_boost value where 1.0 = neutral, >1 = good, <1 = bad.
    """
    if mut_data.get("trades", 0) < 10:
        return 0.0  # Not enough data

    wr = mut_data.get("wr", 0)
    capital = mut_data.get("capital", INITIAL_CAPITAL)
    pnl_factor = max(0.5, min(3.0, capital / INITIAL_CAPITAL))

    # Score = WR * PnL_factor, normalized so 0.5 WR * 1.0 PnL = 0.5 (neutral)
    score = round(wr * pnl_factor, 4)
    mut_data["score_boost"] = score
    return score


# ---------------------------------------------------------------------------
# Trade entry/exit logic
# ---------------------------------------------------------------------------
def _get_top3_coins(profile):
    """Extract top 3 tradeable coin symbols from a strategy profile."""
    coins = []
    for cb in profile.get("coin_breakdown", [])[:5]:
        sym = normalize_symbol(cb.get("coin", ""))
        if sym:
            coins.append(sym)
        if len(coins) >= 3:
            break
    return coins


def _get_coin_wr(profile, symbol):
    """Get a trader's historical win rate on a specific coin."""
    base = symbol.upper().replace("USDT", "").replace("USD", "")
    for cb in profile.get("coin_breakdown", []):
        coin = cb.get("coin", "").upper().replace("USDT", "").replace("USD", "")
        if coin == base:
            return cb.get("win_rate", 0.5)
    return 0.5  # default


def _get_recent_streak(mut_data):
    """Count consecutive losses in recent closed trades. Positive = wins, negative = losses."""
    closed = mut_data.get("closed_trades", [])
    if not closed:
        return 0
    streak = 0
    for t in reversed(closed):
        if t.get("result") == "LOSS":
            streak -= 1
        elif t.get("result") == "WIN":
            if streak < 0:
                break  # streak ended
            streak += 1
        else:
            break
    return streak


def _check_momentum(symbol, price_cache):
    """Simple momentum check: fetch 24h price change from Binance.
    Returns True if 24h change > 0 (uptrend for longs), or the change pct.
    """
    sym = symbol.upper().replace("-", "").replace("/", "")
    if not sym.endswith("USDT"):
        sym += "USDT"

    url = "https://api.binance.com/api/v3/ticker/24hr?symbol={}".format(sym)
    data = _fetch_url(url, timeout=5)
    if data and "priceChangePercent" in data:
        return float(data["priceChangePercent"])

    # Fallback: try binance.us
    url2 = "https://api.binance.us/api/v3/ticker/24hr?symbol={}".format(sym)
    data2 = _fetch_url(url2, timeout=5)
    if data2 and "priceChangePercent" in data2:
        return float(data2["priceChangePercent"])

    return 0.0  # Unknown, allow trade


def _check_volatility(symbol, price_cache):
    """Check if current volatility is above threshold.
    Uses 24h price range as a proxy.
    Returns True if volatility is sufficient (trade allowed).
    """
    sym = symbol.upper().replace("-", "").replace("/", "")
    if not sym.endswith("USDT"):
        sym += "USDT"

    url = "https://api.binance.com/api/v3/ticker/24hr?symbol={}".format(sym)
    data = _fetch_url(url, timeout=5)
    if data and "highPrice" in data and "lowPrice" in data:
        high = float(data["highPrice"])
        low = float(data["lowPrice"])
        if low > 0:
            vol_pct = ((high - low) / low) * 100
            return vol_pct >= 1.5  # Need at least 1.5% daily range

    return True  # Unknown vol, allow trade


def _should_enter_mutation(mkey, mdef, pick, profile, all_picks, mut_data, price_cache):
    """Decide whether a mutation should enter a given pick."""

    symbol = pick.get("symbol", "")
    direction = pick.get("direction", "LONG").upper()

    # -- coin filter --
    if mdef.get("coin_filter") == "top3" and profile:
        top3 = _get_top3_coins(profile)
        norm = normalize_symbol(symbol)
        if norm and norm not in top3:
            return False, direction

    # -- consensus filter --
    if mdef.get("requires_consensus"):
        matching = sum(
            1 for p in all_picks
            if p.get("symbol") == symbol
            and p.get("direction", "").upper() == direction
            and p.get("id") != pick.get("id")
        )
        if matching < 1:
            return False, direction

    # -- high confidence filter --
    if mdef.get("min_confidence"):
        conf = pick.get("confidence", 0)
        if conf < mdef["min_confidence"]:
            return False, direction

    # -- time filter --
    if mdef.get("time_filtered") and profile:
        peak_hours = profile.get("timing", {}).get("peak_entry_hours_utc", [])
        if peak_hours:
            now_hour = datetime.now(timezone.utc).hour
            if now_hour not in peak_hours:
                return False, direction

    # -- momentum filter --
    if mdef.get("requires_trend"):
        change_pct = _check_momentum(symbol, price_cache)
        # Only enter if momentum aligns with direction
        if direction == "LONG" and change_pct < 0.5:
            return False, direction
        if direction == "SHORT" and change_pct > -0.5:
            return False, direction

    # -- volatility filter --
    if mdef.get("skip_low_vol"):
        if not _check_volatility(symbol, price_cache):
            return False, direction

    # -- contrarian fade: invert direction on losing streak --
    if mdef.get("fade_on_streak"):
        streak = _get_recent_streak(mut_data)
        if streak <= -3:
            # Trader on 3+ loss streak, fade direction
            direction = "SHORT" if direction == "LONG" else "LONG"

    return True, direction


def _calc_tp_sl(entry_price, direction, mdef):
    """Calculate TP and SL prices."""
    tp_pct = mdef["tp_pct"] / 100.0
    sl_pct = mdef["sl_pct"] / 100.0

    if direction == "LONG":
        tp = entry_price * (1 + tp_pct)
        sl = entry_price * (1 - sl_pct)
    else:
        tp = entry_price * (1 - tp_pct)
        sl = entry_price * (1 + sl_pct)

    return round(tp, 8), round(sl, 8)


def _position_size(mdef, pick, capital, profile, symbol):
    """Determine allocation for a trade."""
    base_alloc = min(capital * 0.1, 50.0)  # 10% of capital or $50 max

    # Size-scaled: adjust by trader's WR on this symbol
    if mdef.get("scale_by_wr") and profile:
        wr = _get_coin_wr(profile, symbol)
        # Scale: 0.5 WR = 0.5x, 0.7 WR = 1.4x, 0.9 WR = 1.8x
        scale = max(0.3, min(2.0, wr * 2.0))
        base_alloc = min(base_alloc * scale, capital * 0.2)

    return round(max(base_alloc, 5.0), 2)  # Minimum $5


def _check_tp_sl_hit(trade, current_price):
    """Check if TP or SL was hit. Returns 'WIN', 'LOSS', or None."""
    direction = trade.get("direction", "LONG")
    tp = trade.get("take_profit")
    sl = trade.get("stop_loss")

    if direction == "LONG":
        if current_price >= tp:
            return "WIN"
        if current_price <= sl:
            return "LOSS"
    else:
        if current_price <= tp:
            return "WIN"
        if current_price >= sl:
            return "LOSS"
    return None


def _check_time_expiry(trade, max_hold_hours):
    """Check if trade exceeded max hold time."""
    if max_hold_hours is None:
        return False
    opened = trade.get("opened_at", "")
    if not opened:
        return False
    try:
        opened_dt = datetime.fromisoformat(opened.replace("Z", "+00:00"))
        elapsed = (datetime.now(timezone.utc) - opened_dt).total_seconds() / 3600.0
        return elapsed >= max_hold_hours
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Elimination engine -- after 20+ trades, kill bottom 25%
# ---------------------------------------------------------------------------
def run_elimination(trader_mutations):
    """After 20+ closed trades per mutation, rank by Sharpe.
    Kill bottom 25% of mutations for this trader.
    """
    active = {
        k: v for k, v in trader_mutations.items()
        if v.get("status") == "ACTIVE"
    }

    # Need at least 4 active mutations with 20+ trades to eliminate
    eligible = {
        k: v for k, v in active.items()
        if v.get("trades", 0) >= 20
    }

    if len(eligible) < 4:
        return 0

    # Rank by Sharpe ratio
    ranked = sorted(eligible.items(), key=lambda x: x[1].get("sharpe_ratio", 0))

    # Kill bottom 25%
    kill_count = max(1, len(ranked) // 4)
    eliminated = 0

    for k, v in ranked[:kill_count]:
        if trader_mutations[k]["status"] == "ACTIVE":
            trader_mutations[k]["status"] = "ELIMINATED"
            trader_mutations[k]["elimination_reason"] = (
                "Bottom 25% Sharpe ({:.2f}) after {} trades".format(
                    v.get("sharpe_ratio", 0), v.get("trades", 0)
                )
            )
            trader_mutations[k]["eliminated_at"] = datetime.now(timezone.utc).isoformat()
            trader_mutations[k]["open_positions"] = {}
            eliminated += 1

    return eliminated


# ---------------------------------------------------------------------------
# Main run
# ---------------------------------------------------------------------------
def run():
    """
    Main entry point for strategy evolution:
    1. Load trader DNA profiles and active picks
    2. For each trader profile, maintain 8 mutation portfolios
    3. Check existing open positions for TP/SL/time expiry
    4. Open new mutation trades for fresh picks
    5. Compute metrics and score boosts
    6. Run elimination on mutations with 20+ trades
    7. Save mutation_forward_test.json and mutation_scores.json
    """
    print("=" * 70)
    print("  STRATEGY EVOLVER - Mutation Engine")
    print("  {}".format(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")))
    print("=" * 70)
    now_str = datetime.now(timezone.utc).isoformat()

    # Load data
    profiles_data = load_json(STRATEGY_PROFILES_FILE)
    active_picks_data = load_json(ACTIVE_PICKS_FILE)

    if not profiles_data or not profiles_data.get("profiles"):
        print("[ERROR] No strategy_profiles.json found or empty. Run strategy_reverse_engineer.py first.")
        return None

    profiles = profiles_data.get("profiles", [])
    print("  Loaded {} trader DNA profiles".format(len(profiles)))

    if not active_picks_data:
        print("[WARN] No active_picks.json found. Checking existing positions only.")
        all_picks = []
    else:
        if isinstance(active_picks_data, dict):
            all_picks = active_picks_data.get("picks", [])
        elif isinstance(active_picks_data, list):
            all_picks = active_picks_data
        else:
            all_picks = []
    print("  Loaded {} active picks".format(len(all_picks)))

    # Load existing state
    state = load_json(MUTATION_FORWARD_TEST_FILE) or {}
    if "traders" not in state:
        state = {"updated_at": now_str, "traders": {}, "all_closed": []}

    # Price cache
    price_cache = {}

    def cached_price(symbol):
        if symbol not in price_cache:
            p = get_price(symbol)
            if p is not None:
                price_cache[symbol] = p
        return price_cache.get(symbol)

    # Build profile lookup by address
    profile_map = {}
    for p in profiles:
        addr = p.get("address", "")
        if addr:
            profile_map[addr] = p

    # Group picks by trader address
    picks_by_trader = {}
    for pick in all_picks:
        addr = pick.get("trader_address", "")
        if addr:
            picks_by_trader.setdefault(addr, []).append(pick)

    # ---------- Process each trader profile ----------
    total_new = 0
    total_closed = 0
    total_eliminated = 0

    for profile in profiles:
        addr = profile.get("address", "")
        label = profile.get("label", addr[:10] if addr else "unknown")
        tkey = "evolve_{}".format(label)

        # Initialize trader in state if needed
        if tkey not in state["traders"]:
            state["traders"][tkey] = {
                "address": addr,
                "label": label,
                "mutations": {},
            }
        tmuts = state["traders"][tkey]["mutations"]

        # Ensure all mutations exist
        for mkey, mdef in MUTATION_DEFS.items():
            if mkey not in tmuts:
                tmuts[mkey] = _empty_mutation(mkey, mdef)

        # Get this trader's current picks
        trader_picks = picks_by_trader.get(addr, [])

        # ---------- Step 1: Check existing open positions ----------
        for mkey, mdata in tmuts.items():
            if mdata.get("status") != "ACTIVE":
                continue

            mdef = MUTATION_DEFS.get(mkey, {})
            positions_to_close = []

            for pos_id, pos in list(mdata.get("open_positions", {}).items()):
                symbol = pos.get("symbol", "")
                price = cached_price(symbol)
                if price is None:
                    continue

                # Check TP/SL
                result = _check_tp_sl_hit(pos, price)

                # Check time expiry
                if result is None and _check_time_expiry(pos, mdef.get("max_hold_hours")):
                    direction = pos.get("direction", "LONG")
                    entry = pos.get("entry_price", 0)
                    if direction == "LONG":
                        pnl_pct = ((price - entry) / entry) * 100 if entry else 0
                    else:
                        pnl_pct = ((entry - price) / entry) * 100 if entry else 0
                    result = "WIN" if pnl_pct > 0 else "LOSS"

                if result:
                    entry = pos.get("entry_price", 0)
                    alloc = pos.get("allocation", 50)
                    direction = pos.get("direction", "LONG")

                    if direction == "LONG":
                        pnl_pct = ((price - entry) / entry) * 100 if entry else 0
                    else:
                        pnl_pct = ((entry - price) / entry) * 100 if entry else 0

                    # Cap PnL at TP/SL levels
                    if result == "WIN":
                        tp_pct_max = mdef.get("tp_pct", 3.0)
                        pnl_pct = min(abs(pnl_pct), tp_pct_max)
                    elif result == "LOSS":
                        sl_pct_max = mdef.get("sl_pct", 1.5)
                        pnl_pct = -min(abs(pnl_pct), sl_pct_max)

                    pnl_dollar = round(alloc * (pnl_pct / 100), 4)

                    closed_trade = {
                        "id": pos_id,
                        "symbol": symbol,
                        "direction": direction,
                        "entry_price": entry,
                        "exit_price": price,
                        "take_profit": pos.get("take_profit"),
                        "stop_loss": pos.get("stop_loss"),
                        "opened_at": pos.get("opened_at"),
                        "closed_at": now_str,
                        "result": result,
                        "pnl_pct": round(pnl_pct, 4),
                        "pnl_dollar": pnl_dollar,
                        "allocation": alloc,
                        "mutation": mkey,
                        "trader": tkey,
                    }
                    mdata["closed_trades"].append(closed_trade)
                    mdata["returns_list"].append(pnl_pct / 100)
                    state.setdefault("all_closed", []).append(closed_trade)
                    positions_to_close.append(pos_id)
                    total_closed += 1

            for pid in positions_to_close:
                mdata["open_positions"].pop(pid, None)

        # ---------- Step 2: Open new trades for fresh picks ----------
        for pick in trader_picks:
            symbol = pick.get("symbol", "")
            pick_id = pick.get("id", "")

            # Skip non-crypto
            norm = normalize_symbol(symbol.replace("USDT", "").replace("USD", ""))
            if norm is None and ":" in symbol:
                continue

            entry_price = pick.get("entry_price")
            if not entry_price:
                price = cached_price(symbol)
                if price is None:
                    continue
                entry_price = price

            for mkey, mdef in MUTATION_DEFS.items():
                mdata = tmuts[mkey]
                if mdata.get("status") != "ACTIVE":
                    continue

                # Already have this position?
                pos_key = "{}::{}".format(mkey, pick_id)
                if pos_key in mdata.get("open_positions", {}):
                    continue

                # Max 5 open positions per mutation
                if len(mdata.get("open_positions", {})) >= 5:
                    continue

                # Check if mutation should enter
                should_enter, trade_direction = _should_enter_mutation(
                    mkey, mdef, pick, profile, all_picks, mdata, price_cache
                )
                if not should_enter:
                    continue

                # Capital check
                capital = mdata.get("capital", INITIAL_CAPITAL)
                alloc = _position_size(mdef, pick, capital, profile, symbol)
                if alloc <= 0 or alloc > capital:
                    continue

                tp, sl = _calc_tp_sl(entry_price, trade_direction, mdef)

                new_pos = {
                    "symbol": symbol,
                    "direction": trade_direction,
                    "entry_price": entry_price,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "allocation": alloc,
                    "opened_at": now_str,
                    "source_pick_id": pick_id,
                }
                mdata["open_positions"][pos_key] = new_pos
                total_new += 1

        # ---------- Step 3: Recompute metrics, score boosts, elimination ----------
        for mkey in tmuts:
            _compute_metrics(tmuts[mkey])
            _compute_score_boost(tmuts[mkey])

        eliminated = run_elimination(tmuts)
        total_eliminated += eliminated

    # ---------- Build mutation_scores.json ----------
    scores = {}
    for tkey, tdata in state.get("traders", {}).items():
        for mkey, mdata in tdata.get("mutations", {}).items():
            if mdata.get("trades", 0) >= 10:
                full_key = "{}_{}".format(tkey, mkey)
                scores[full_key] = {
                    "score_boost": mdata.get("score_boost", 0),
                    "wr": mdata.get("wr", 0),
                    "pnl_pct": mdata.get("pnl_pct", 0),
                    "sharpe": mdata.get("sharpe_ratio", 0),
                    "trades": mdata.get("trades", 0),
                    "status": mdata.get("status", "ACTIVE"),
                    "trader": tkey,
                    "mutation": mkey,
                }

    # ---------- Save state ----------
    state["updated_at"] = now_str

    # Build clean save state (strip returns_list, limit closed_trades)
    save_state = json.loads(json.dumps(state, default=str))
    for tkey in save_state.get("traders", {}):
        for mkey in save_state["traders"][tkey].get("mutations", {}):
            save_state["traders"][tkey]["mutations"][mkey].pop("returns_list", None)
            ct = save_state["traders"][tkey]["mutations"][mkey].get("closed_trades", [])
            if len(ct) > 200:
                save_state["traders"][tkey]["mutations"][mkey]["closed_trades"] = ct[-200:]

    # Limit all_closed global log
    all_closed = save_state.get("all_closed", [])
    if len(all_closed) > 5000:
        save_state["all_closed"] = all_closed[-5000:]

    save_json(MUTATION_FORWARD_TEST_FILE, save_state)

    scores_output = {
        "updated_at": now_str,
        "description": "Score boosts per mutation (WR * PnL_factor). >0.5 = good, <0.3 = bad.",
        "scores": scores,
    }
    save_json(MUTATION_SCORES_FILE, scores_output)

    # ---------- Print summary ----------
    print("\nRun completed: {}".format(now_str))
    print("New positions opened: {}".format(total_new))
    print("Trades closed: {}".format(total_closed))
    print("Mutations eliminated: {}".format(total_eliminated))
    print("Trader profiles: {}".format(len(state.get("traders", {}))))
    print("Prices fetched: {}".format(len(price_cache)))
    print("Score boosts computed: {}".format(len(scores)))

    print("\n" + "-" * 105)
    print("{:<25} {:<20} {:<10} {:>6} {:>6} {:>8} {:>7} {:>7} {:>6} {:>5}".format(
        "Trader", "Mutation", "Status", "Trades", "WR", "PnL$", "PnL%", "Sharpe", "Score", "Open"
    ))
    print("-" * 105)

    for tkey in sorted(state.get("traders", {}).keys()):
        tmuts = state["traders"][tkey].get("mutations", {})
        first = True
        for mkey in sorted(tmuts.keys()):
            m = tmuts[mkey]
            status = m.get("status", "?")
            trades = m.get("trades", 0)
            wr = m.get("wr", 0)
            pnl = m.get("pnl_dollar", 0)
            pnl_pct = m.get("pnl_pct", 0)
            sharpe = m.get("sharpe_ratio", 0)
            score = m.get("score_boost", 0)
            open_ct = len(m.get("open_positions", {}))

            label = tkey[:23] if first else ""
            first = False

            print("{:<25} {:<20} {:<10} {:>6} {:>5.1%} {:>8.2f} {:>6.1f}% {:>7.2f} {:>6.3f} {:>5}".format(
                label, mkey[:18], status[:8], trades, wr, pnl, pnl_pct, sharpe, score, open_ct
            ))

    print("-" * 105)

    # Top mutations by score boost
    all_scored = []
    for tkey, tdata in state.get("traders", {}).items():
        for mkey, mdata in tdata.get("mutations", {}).items():
            if mdata.get("trades", 0) >= 5 and mdata.get("status") == "ACTIVE":
                all_scored.append((tkey, mkey, mdata))

    if all_scored:
        all_scored.sort(key=lambda x: x[2].get("score_boost", 0), reverse=True)
        print("\n** TOP MUTATIONS BY SCORE BOOST (5+ trades, active) **")
        for tkey, mkey, mdata in all_scored[:10]:
            print("  {:<22} {:<20} Score={:.3f} WR={:.1%} PnL=${:.2f} Sharpe={:.2f}".format(
                tkey[:20], mkey[:18],
                mdata.get("score_boost", 0),
                mdata.get("wr", 0),
                mdata.get("pnl_dollar", 0),
                mdata.get("sharpe_ratio", 0),
            ))

    # Eliminated mutations
    elim_list = []
    for tkey, tdata in state.get("traders", {}).items():
        for mkey, mdata in tdata.get("mutations", {}).items():
            if mdata.get("status") == "ELIMINATED":
                elim_list.append((tkey, mkey, mdata))

    if elim_list:
        print("\n** ELIMINATED MUTATIONS **")
        for tkey, mkey, mdata in elim_list:
            print("  {:<22} {:<20} Reason: {}".format(
                tkey[:20], mkey[:18],
                mdata.get("elimination_reason", "unknown")
            ))

    print("\nDone.")
    return state


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run()
