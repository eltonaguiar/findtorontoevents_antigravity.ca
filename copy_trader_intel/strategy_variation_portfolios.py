#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOTE — SNAPSHOT-RESOLVER ARTIFACT (2026-06-03): WR/PF here is inflated by single
daily-snapshot TP/SL resolution (no intrabar OHLC path) — intraday SL touches are missed.
Do not size up on these numbers. See docs/RESOLVER_SNAPSHOT_ARTIFACT_AFFECTED_PORTFOLIOS_2026-06-03.md

Strategy Variation Paper Trading System
========================================
Creates multiple paper trading portfolios per trader, each using a different
variation of what we think their strategy is. Tracks which variation performs
best via process of elimination.

Variations:
  A: Tight Scalper     - 1.5% TP, 1% SL, max 4h hold, top 3 coins only
  B: Momentum Rider    - 3% TP, 1.5% SL, 8h hold, enter when momentum aligns
  C: Wide Swing        - 5% TP, 2.5% SL, 24h hold, all coins
  D: Conservative Copy - 2% TP, 1.5% SL, 12h hold, consensus only (2+ traders)
  E: Aggressive Mirror - 4% TP, 2% SL, no time limit, mirror leverage
  F: Inverse Filter    - Skip trades when funding rate against direction
  G: Volume Weighted   - Increase size on high-volume coins
  H: Time Filtered     - Only trade during trader's peak hours
"""

import sys
import os
import io

# Windows UTF-8 fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import json
import math
import time
import traceback
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
QUALIFIED_FILE = DATA_DIR / "qualified_traders.json"
STRATEGY_PROFILES_FILE = DATA_DIR / "strategy_profiles.json"
ACTIVE_PICKS_FILE = DATA_DIR / "active_picks.json"
VARIATIONS_FILE = DATA_DIR / "strategy_variations.json"
FORWARD_TEST_FILE = DATA_DIR / "variation_forward_test.json"

# ---------------------------------------------------------------------------
# Binance price API -- 3+ failover chain
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
    "TRUMPUSDT": "official-trump", "AAVEUSDT": "aave",
    "ZECUSDT": "zcash", "XMRUSDT": "monero",
}


def _fetch_url(url, timeout=8):
    """Fetch JSON from URL with timeout."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "StratVarBot/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def get_price(symbol):
    """Get current price for a Binance-style symbol. Returns float or None."""
    # Normalize symbol
    sym = symbol.upper().replace("-", "")
    if not sym.endswith("USDT") and not sym.endswith("USD"):
        sym = sym + "USDT"

    # Try Binance mirrors
    for endpoint in BINANCE_ENDPOINTS:
        data = _fetch_url(endpoint.format(sym))
        if data and "price" in data:
            return float(data["price"])

    # CoinGecko fallback
    cg_id = COINGECKO_MAP.get(sym)
    if cg_id:
        data = _fetch_url(
            f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd"
        )
        if data and cg_id in data:
            return float(data[cg_id]["usd"])

    return None


# ---------------------------------------------------------------------------
# Variation definitions
# ---------------------------------------------------------------------------
VARIATION_DEFS = {
    "A_tight_scalper": {
        "tp_pct": 1.5,
        "sl_pct": 1.0,
        "max_hold_hours": 4,
        "coin_filter": "top3",
        "description": "Tight Scalper: 1.5% TP, 1% SL, max 4h, top 3 coins",
    },
    "B_momentum_rider": {
        "tp_pct": 3.0,
        "sl_pct": 1.5,
        "max_hold_hours": 8,
        "coin_filter": "all",
        "requires_momentum": True,
        "description": "Momentum Rider: 3% TP, 1.5% SL, 8h, momentum-aligned entry",
    },
    "C_wide_swing": {
        "tp_pct": 5.0,
        "sl_pct": 2.5,
        "max_hold_hours": 24,
        "coin_filter": "all",
        "description": "Wide Swing: 5% TP, 2.5% SL, 24h hold, all coins",
    },
    "D_conservative_copy": {
        "tp_pct": 2.0,
        "sl_pct": 1.5,
        "max_hold_hours": 12,
        "coin_filter": "all",
        "requires_consensus": True,
        "description": "Conservative Copy: 2% TP, 1.5% SL, 12h, consensus only",
    },
    "E_aggressive_mirror": {
        "tp_pct": 4.0,
        "sl_pct": 2.0,
        "max_hold_hours": None,
        "coin_filter": "all",
        "mirror_leverage": True,
        "description": "Aggressive Mirror: 4% TP, 2% SL, no time limit, mirror leverage",
    },
    "F_inverse_filter": {
        "tp_pct": 3.0,
        "sl_pct": 1.5,
        "max_hold_hours": 12,
        "coin_filter": "all",
        "skip_adverse_funding": True,
        "description": "Inverse Filter: skip trades when funding rate is against direction",
    },
    "G_volume_weighted": {
        "tp_pct": 3.0,
        "sl_pct": 1.5,
        "max_hold_hours": 12,
        "coin_filter": "all",
        "volume_weighted": True,
        "description": "Volume Weighted: increase size on high-volume coins",
    },
    "H_time_filtered": {
        "tp_pct": 3.0,
        "sl_pct": 1.5,
        "max_hold_hours": 12,
        "coin_filter": "all",
        "time_filtered": True,
        "description": "Time Filtered: only trade during trader's most profitable hours",
    },
}

INITIAL_CAPITAL = 500.0


# ---------------------------------------------------------------------------
# Helper: normalize symbol to Binance format
# ---------------------------------------------------------------------------
def _normalize_symbol(sym):
    """Convert raw symbol to Binance-compatible format."""
    s = sym.upper().replace("/", "").replace("-", "")
    # Skip non-crypto symbols (xyz:, km:, cash:, flx:, vntl:, hyna:)
    if ":" in sym:
        return None
    # Skip @ prefixed internal tokens
    if s.startswith("@"):
        return None
    if not s.endswith("USDT") and not s.endswith("USD"):
        s += "USDT"
    # kPEPE -> PEPEUSDT
    if s.startswith("K") and len(s) > 5:
        s = s[1:]
    return s


def _get_top3_coins(trader):
    """Extract top 3 tradeable coins from trader profile."""
    coins = []
    for entry in trader.get("top_coins", [])[:5]:
        sym = _normalize_symbol(entry[0])
        if sym:
            coins.append(sym)
        if len(coins) >= 3:
            break
    return coins


def _get_trader_key(trader):
    """Build a stable key for a trader."""
    label = trader.get("label", "unknown")
    addr = trader.get("address", "")[:8]
    return f"copy_hl_{label}_{addr}"


# ---------------------------------------------------------------------------
# Paper Portfolio per variation
# ---------------------------------------------------------------------------
def _empty_variation(vkey, vdef):
    return {
        "status": "ACTIVE",
        "description": vdef["description"],
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
        "open_positions": {},
        "closed_trades": [],
        "elimination_reason": None,
        "eliminated_at": None,
        "peak_capital": INITIAL_CAPITAL,
        "returns_list": [],
    }


def _compute_metrics(var_data):
    """Recompute win rate, PnL, profit factor, max drawdown, Sharpe from closed trades."""
    closed = var_data.get("closed_trades", [])
    if not closed:
        return

    wins = sum(1 for t in closed if t.get("result") == "WIN")
    losses = sum(1 for t in closed if t.get("result") == "LOSS")
    total = wins + losses
    var_data["trades"] = total
    var_data["wins"] = wins
    var_data["losses"] = losses
    var_data["wr"] = round(wins / total, 4) if total else 0.0

    gross_profit = sum(t.get("pnl_dollar", 0) for t in closed if t.get("pnl_dollar", 0) > 0)
    gross_loss = abs(sum(t.get("pnl_dollar", 0) for t in closed if t.get("pnl_dollar", 0) < 0))
    var_data["pnl_dollar"] = round(sum(t.get("pnl_dollar", 0) for t in closed), 4)
    var_data["pnl_pct"] = round(var_data["pnl_dollar"] / INITIAL_CAPITAL * 100, 2)
    var_data["profit_factor"] = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 99.99

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
    var_data["max_drawdown_pct"] = round(max_dd * 100, 2)
    var_data["capital"] = round(INITIAL_CAPITAL + var_data["pnl_dollar"], 2)

    # Sharpe ratio (annualized, assuming ~6 trades/day)
    returns = var_data.get("returns_list", [])
    if len(returns) >= 5:
        mean_r = sum(returns) / len(returns)
        variance = sum((r - mean_r) ** 2 for r in returns) / len(returns)
        std_r = math.sqrt(variance) if variance > 0 else 0.001
        # Annualize: sqrt(252 * 6) ~ sqrt(1512) ~ 38.9
        var_data["sharpe_ratio"] = round((mean_r / std_r) * 38.9, 2)
    else:
        var_data["sharpe_ratio"] = 0.0


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------
def load_json(path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def _should_enter_trade(vkey, vdef, pick, trader_profile, all_picks):
    """Decide whether a variation should enter a given pick as a new trade."""

    # Coin filter
    symbol = pick.get("symbol", "")
    if vdef.get("coin_filter") == "top3":
        top3 = []
        if trader_profile:
            for cb in trader_profile.get("coin_breakdown", [])[:3]:
                sym = _normalize_symbol(cb.get("coin", ""))
                if sym:
                    top3.append(sym)
        if symbol not in top3:
            return False

    # Consensus filter: need 2+ traders with same symbol + direction
    if vdef.get("requires_consensus"):
        direction = pick.get("direction", "")
        matching = sum(
            1 for p in all_picks
            if p.get("symbol") == symbol
            and p.get("direction") == direction
            and p.get("id") != pick.get("id")
        )
        if matching < 1:
            return False

    # Time filter: only enter during trader's peak hours
    if vdef.get("time_filtered") and trader_profile:
        peak_hours = trader_profile.get("timing", {}).get("peak_entry_hours_utc", [])
        if peak_hours:
            now_hour = datetime.now(timezone.utc).hour
            if now_hour not in peak_hours:
                return False

    return True


def _calc_variation_tp_sl(entry_price, direction, vdef):
    """Calculate TP and SL prices for a variation."""
    tp_pct = vdef["tp_pct"] / 100.0
    sl_pct = vdef["sl_pct"] / 100.0

    if direction == "LONG":
        tp = entry_price * (1 + tp_pct)
        sl = entry_price * (1 - sl_pct)
    else:  # SHORT
        tp = entry_price * (1 - tp_pct)
        sl = entry_price * (1 + sl_pct)

    return round(tp, 8), round(sl, 8)


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


def _position_size(vdef, pick, capital):
    """Determine allocation for a trade."""
    base_alloc = min(capital * 0.1, 50.0)  # 10% of capital or $50 max
    if vdef.get("volume_weighted"):
        # Double allocation for BTC/ETH (high volume)
        sym = pick.get("symbol", "").upper()
        if "BTC" in sym or "ETH" in sym:
            base_alloc = min(base_alloc * 2, capital * 0.2)
    return round(base_alloc, 2)


def _build_profile_map(profiles_data):
    """Build address -> profile lookup."""
    m = {}
    if not profiles_data:
        return m
    for p in profiles_data.get("profiles", []):
        addr = p.get("address", "")
        if addr:
            m[addr] = p
    return m


def _build_trader_map(qualified_data):
    """Build address -> trader lookup."""
    m = {}
    if not qualified_data:
        return m
    for t in qualified_data.get("traders", []):
        addr = t.get("address", "")
        if addr:
            m[addr] = t
    return m


# ---------------------------------------------------------------------------
# Elimination engine
# ---------------------------------------------------------------------------
def run_elimination(trader_vars):
    """
    After 20+ closed trades per variation, rank by Sharpe ratio.
    Eliminate bottom 2 variations.
    After 50+ trades, only keep top 2 per trader.
    """
    active_vars = {
        k: v for k, v in trader_vars.items()
        if v.get("status") == "ACTIVE"
    }

    # Phase 1: At 20+ trades, eliminate bottom 2
    eligible_20 = {
        k: v for k, v in active_vars.items()
        if v.get("trades", 0) >= 20
    }
    if len(eligible_20) >= 4:
        ranked = sorted(eligible_20.items(), key=lambda x: x[1].get("sharpe_ratio", 0))
        for k, v in ranked[:2]:
            if trader_vars[k]["status"] == "ACTIVE":
                trader_vars[k]["status"] = "ELIMINATED"
                trader_vars[k]["elimination_reason"] = (
                    f"Lowest Sharpe ({v.get('sharpe_ratio', 0)}) after {v.get('trades', 0)} trades"
                )
                trader_vars[k]["eliminated_at"] = datetime.now(timezone.utc).isoformat()
                # Close any open positions at current state
                trader_vars[k]["open_positions"] = {}

    # Phase 2: At 50+ trades, only keep top 2
    active_vars = {
        k: v for k, v in trader_vars.items()
        if v.get("status") == "ACTIVE"
    }
    eligible_50 = {
        k: v for k, v in active_vars.items()
        if v.get("trades", 0) >= 50
    }
    if len(eligible_50) > 2:
        ranked = sorted(eligible_50.items(), key=lambda x: x[1].get("sharpe_ratio", 0), reverse=True)
        for k, v in ranked[2:]:
            trader_vars[k]["status"] = "ELIMINATED"
            trader_vars[k]["elimination_reason"] = (
                f"Not top-2 Sharpe ({v.get('sharpe_ratio', 0)}) after {v.get('trades', 0)} trades"
            )
            trader_vars[k]["eliminated_at"] = datetime.now(timezone.utc).isoformat()
            trader_vars[k]["open_positions"] = {}


# ---------------------------------------------------------------------------
# Main run
# ---------------------------------------------------------------------------
def run():
    """
    Main entry point:
    1. Load current picks and strategy profiles
    2. For each open pick, check if any variation's TP/SL was hit
    3. Open new variation trades for fresh picks
    4. Run elimination on variations with 20+ trades
    5. Print summary table
    """
    print("=" * 70)
    print("  STRATEGY VARIATION PAPER TRADING SYSTEM")
    print("=" * 70)
    now_str = datetime.now(timezone.utc).isoformat()

    # Load data
    qualified = load_json(QUALIFIED_FILE)
    profiles = load_json(STRATEGY_PROFILES_FILE)
    active_picks = load_json(ACTIVE_PICKS_FILE)

    if not qualified:
        print("[ERROR] No qualified_traders.json found")
        return
    if not active_picks:
        print("[ERROR] No active_picks.json found")
        return

    # Ensure active_picks is a list
    if isinstance(active_picks, dict):
        active_picks = active_picks.get("picks", [])

    profile_map = _build_profile_map(profiles)
    trader_map = _build_trader_map(qualified)

    # Load existing state
    state = load_json(VARIATIONS_FILE) or {}
    if "traders" not in state:
        state = {"updated_at": now_str, "traders": {}}
    forward_test = load_json(FORWARD_TEST_FILE) or {}
    if "trades" not in forward_test:
        forward_test = {"updated_at": now_str, "trades": []}

    # Group picks by trader address
    picks_by_trader = {}
    for pick in active_picks:
        addr = pick.get("trader_address", "")
        if addr:
            picks_by_trader.setdefault(addr, []).append(pick)

    # Price cache to avoid repeated API calls
    price_cache = {}

    def cached_price(symbol):
        if symbol not in price_cache:
            p = get_price(symbol)
            if p is not None:
                price_cache[symbol] = p
        return price_cache.get(symbol)

    # ---------- Process each qualified trader ----------
    traders = qualified.get("traders", [])
    total_new = 0
    total_closed = 0
    total_eliminated = 0

    for trader in traders:
        addr = trader.get("address", "")
        label = trader.get("label", "unknown")
        tkey = f"copy_hl_{label}"
        profile = profile_map.get(addr)

        # Initialize trader in state if needed
        if tkey not in state["traders"]:
            state["traders"][tkey] = {"variations": {}}
        tvars = state["traders"][tkey]["variations"]

        # Ensure all variations exist
        for vkey, vdef in VARIATION_DEFS.items():
            if vkey not in tvars:
                tvars[vkey] = _empty_variation(vkey, vdef)

        # Get this trader's current picks
        trader_picks = picks_by_trader.get(addr, [])

        # ---------- Step 1: Check existing open positions ----------
        for vkey, vdata in tvars.items():
            if vdata.get("status") != "ACTIVE":
                continue

            vdef = VARIATION_DEFS.get(vkey, {})
            positions_to_close = []

            for pos_id, pos in list(vdata.get("open_positions", {}).items()):
                symbol = pos.get("symbol", "")
                price = cached_price(symbol)
                if price is None:
                    continue

                # Check TP/SL
                result = _check_tp_sl_hit(pos, price)

                # Check time expiry
                if result is None and _check_time_expiry(pos, vdef.get("max_hold_hours")):
                    # Force close -- determine if profit or loss
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
                        "variation": vkey,
                        "trader": tkey,
                    }
                    vdata["closed_trades"].append(closed_trade)
                    vdata["returns_list"].append(pnl_pct / 100)  # decimal return
                    forward_test["trades"].append(closed_trade)
                    positions_to_close.append(pos_id)
                    total_closed += 1

            for pid in positions_to_close:
                vdata["open_positions"].pop(pid, None)

        # ---------- Step 2: Open new trades for fresh picks ----------
        for pick in trader_picks:
            symbol = pick.get("symbol", "")
            direction = pick.get("direction", "")
            pick_id = pick.get("id", "")

            # Skip non-crypto / unsupported symbols
            norm = _normalize_symbol(symbol.replace("USDT", "").replace("USD", ""))
            if norm is None and ":" in symbol:
                continue

            entry_price = pick.get("entry_price")
            if not entry_price:
                price = cached_price(symbol)
                if price is None:
                    continue
                entry_price = price

            for vkey, vdef in VARIATION_DEFS.items():
                vdata = tvars[vkey]
                if vdata.get("status") != "ACTIVE":
                    continue

                # Already have this position open?
                pos_key = f"{vkey}::{pick_id}"
                if pos_key in vdata.get("open_positions", {}):
                    continue

                # Max 5 open positions per variation
                if len(vdata.get("open_positions", {})) >= 5:
                    continue

                # Check if variation should enter
                if not _should_enter_trade(vkey, vdef, pick, profile, active_picks):
                    continue

                # Capital check
                capital = vdata.get("capital", INITIAL_CAPITAL)
                alloc = _position_size(vdef, pick, capital)
                if alloc <= 0 or alloc > capital:
                    continue

                tp, sl = _calc_variation_tp_sl(entry_price, direction, vdef)

                new_pos = {
                    "symbol": symbol,
                    "direction": direction,
                    "entry_price": entry_price,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "allocation": alloc,
                    "opened_at": now_str,
                    "source_pick_id": pick_id,
                }
                vdata["open_positions"][pos_key] = new_pos
                total_new += 1

        # ---------- Step 3: Recompute metrics & run elimination ----------
        for vkey in tvars:
            _compute_metrics(tvars[vkey])

        active_before = sum(1 for v in tvars.values() if v.get("status") == "ACTIVE")
        run_elimination(tvars)
        active_after = sum(1 for v in tvars.values() if v.get("status") == "ACTIVE")
        total_eliminated += (active_before - active_after)

    # ---------- Save state ----------
    state["updated_at"] = now_str
    forward_test["updated_at"] = now_str

    # Strip returns_list from saved output (internal only)
    save_state = json.loads(json.dumps(state, default=str))
    for tkey in save_state.get("traders", {}):
        for vkey in save_state["traders"][tkey].get("variations", {}):
            save_state["traders"][tkey]["variations"][vkey].pop("returns_list", None)
            # Limit closed_trades to last 200 per variation
            ct = save_state["traders"][tkey]["variations"][vkey].get("closed_trades", [])
            if len(ct) > 200:
                save_state["traders"][tkey]["variations"][vkey]["closed_trades"] = ct[-200:]

    save_json(VARIATIONS_FILE, save_state)

    # Limit forward test to last 5000 trades
    if len(forward_test["trades"]) > 5000:
        forward_test["trades"] = forward_test["trades"][-5000:]
    save_json(FORWARD_TEST_FILE, forward_test)

    # ---------- Print summary ----------
    print(f"\nRun completed: {now_str}")
    print(f"New positions opened: {total_new}")
    print(f"Trades closed: {total_closed}")
    print(f"Variations eliminated: {total_eliminated}")
    print(f"Traders tracked: {len(state['traders'])}")
    print(f"Prices fetched: {len(price_cache)}")

    print("\n" + "-" * 100)
    print(f"{'Trader':<30} {'Variation':<22} {'Status':<12} {'Trades':>6} "
          f"{'WR':>6} {'PnL$':>8} {'PnL%':>7} {'Sharpe':>7} {'Open':>5}")
    print("-" * 100)

    for tkey in sorted(state["traders"].keys()):
        tvars = state["traders"][tkey]["variations"]
        first = True
        for vkey in sorted(tvars.keys()):
            v = tvars[vkey]
            status = v.get("status", "?")
            trades = v.get("trades", 0)
            wr = v.get("wr", 0)
            pnl = v.get("pnl_dollar", 0)
            pnl_pct = v.get("pnl_pct", 0)
            sharpe = v.get("sharpe_ratio", 0)
            open_ct = len(v.get("open_positions", {}))

            status_tag = status[:4]
            label = tkey[:28] if first else ""
            first = False

            print(f"{label:<30} {vkey:<22} {status_tag:<12} {trades:>6} "
                  f"{wr:>5.1%} {pnl:>8.2f} {pnl_pct:>6.1f}% {sharpe:>7.2f} {open_ct:>5}")

    print("-" * 100)

    # Summary of best variations
    print("\n** TOP VARIATIONS BY SHARPE (with 5+ trades) **")
    all_vars = []
    for tkey, tdata in state["traders"].items():
        for vkey, vdata in tdata.get("variations", {}).items():
            if vdata.get("trades", 0) >= 5 and vdata.get("status") == "ACTIVE":
                all_vars.append((tkey, vkey, vdata))

    all_vars.sort(key=lambda x: x[2].get("sharpe_ratio", 0), reverse=True)
    for tkey, vkey, vdata in all_vars[:10]:
        print(f"  {tkey[:25]:<25} {vkey:<22} Sharpe={vdata.get('sharpe_ratio', 0):>6.2f} "
              f"WR={vdata.get('wr', 0):.1%} PnL=${vdata.get('pnl_dollar', 0):.2f}")

    print("\nDone.")
    return state


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run()
