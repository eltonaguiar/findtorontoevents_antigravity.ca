#!/usr/bin/env python3
"""
Shadow Exit Tracker — runs 4 exit models in parallel on every active pick
and logs what each would have done, WITHOUT affecting real positions.

Models:
  A (Current)    — Fixed TP/SL from the pick fields
  B (Trailing)   — Trailing stop: +1.5% activation, 1% trail distance, no fixed TP
  C (Time-decay) — TP reduces by 10% per 4h held; after 24h TP = 50% of original
  D (Partial)    — Exit 50% at 1R profit, trail remainder to 2R or SL
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SHADOW_LOG_PATH = os.path.join(DATA_DIR, "shadow_exit_log.json")
PORTFOLIO_PATH = os.path.join(DATA_DIR, "portfolio_1x.json")
MAX_LOG_ENTRIES = 500

# ── helpers ──────────────────────────────────────────────────────────────

def _now_utc():
    return datetime.now(timezone.utc)


def _hours_held(opened_at_str):
    """Return hours since position was opened."""
    try:
        opened = datetime.fromisoformat(opened_at_str)
        if opened.tzinfo is None:
            opened = opened.replace(tzinfo=timezone.utc)
        delta = _now_utc() - opened
        return max(delta.total_seconds() / 3600, 0)
    except Exception:
        return 0


def _pnl_pct(entry_price, current_price, direction="BUY"):
    """Signed PnL percentage."""
    if not entry_price:
        return 0.0
    if direction in ("BUY", "LONG"):
        return ((current_price - entry_price) / entry_price) * 100
    else:
        return ((entry_price - current_price) / entry_price) * 100


def _load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# ── shadow state (per-run, keyed by symbol) ──────────────────────────────

_shadow_state = {}  # populated from log on first call


def _get_state(symbol):
    """Get or create shadow state for a symbol across models."""
    if symbol not in _shadow_state:
        _shadow_state[symbol] = {
            "B_hwm": None,          # trailing model high-water mark price
            "B_trailing_stop": 0,   # trailing stop level
            "B_activated": False,   # whether +1.5% was reached
            "D_first_exit_done": False,  # partial model: first 50% exited?
            "D_remainder_hwm": None,
        }
    return _shadow_state[symbol]


# ── Model A: Fixed TP / SL ──────────────────────────────────────────────

def _check_model_a(pos, price):
    entry = pos["entry_price"]
    tp = pos.get("take_profit", 0)
    sl = pos.get("stop_loss", 0)
    direction = pos.get("direction", "BUY")
    pnl = _pnl_pct(entry, price, direction)

    is_long = direction in ("BUY", "LONG")

    if tp and ((is_long and price >= tp) or (not is_long and price <= tp)):
        return "EXIT", pnl, f"TP hit at {price:.6g} (target {tp:.6g})"
    if sl and ((is_long and price <= sl) or (not is_long and price >= sl)):
        return "EXIT", pnl, f"SL hit at {price:.6g} (stop {sl:.6g})"
    return "HOLD", pnl, ""


# ── Model B: Trailing Stop (+1.5% activation, 1% trail) ─────────────────

def _check_model_b(pos, price):
    entry = pos["entry_price"]
    direction = pos.get("direction", "BUY")
    symbol = pos.get("symbol", "?")
    pnl = _pnl_pct(entry, price, direction)
    state = _get_state(symbol)
    is_long = direction in ("BUY", "LONG")

    # update high-water mark
    if state["B_hwm"] is None:
        state["B_hwm"] = price
    if is_long:
        state["B_hwm"] = max(state["B_hwm"], price)
    else:
        state["B_hwm"] = min(state["B_hwm"], price)

    # activation check: +1.5% from entry
    activation_pnl = _pnl_pct(entry, state["B_hwm"], direction)
    if activation_pnl >= 1.5:
        state["B_activated"] = True
        # set trailing stop 1% below HWM (long) or 1% above HWM (short)
        if is_long:
            state["B_trailing_stop"] = state["B_hwm"] * 0.99
        else:
            state["B_trailing_stop"] = state["B_hwm"] * 1.01

    if state["B_activated"]:
        if is_long and price <= state["B_trailing_stop"]:
            return "EXIT", pnl, f"Trailing stop hit at {price:.6g} (trail {state['B_trailing_stop']:.6g})"
        if not is_long and price >= state["B_trailing_stop"]:
            return "EXIT", pnl, f"Trailing stop hit at {price:.6g} (trail {state['B_trailing_stop']:.6g})"

    # also check original SL as floor
    sl = pos.get("stop_loss", 0)
    if sl and ((is_long and price <= sl) or (not is_long and price >= sl)):
        return "EXIT", pnl, f"SL hit at {price:.6g} (stop {sl:.6g})"

    return "HOLD", pnl, ""


# ── Model C: Time-decay TP ──────────────────────────────────────────────

def _check_model_c(pos, price):
    entry = pos["entry_price"]
    tp_orig = pos.get("take_profit", 0)
    sl = pos.get("stop_loss", 0)
    direction = pos.get("direction", "BUY")
    is_long = direction in ("BUY", "LONG")
    pnl = _pnl_pct(entry, price, direction)

    opened_at = pos.get("opened_at", "")
    hours = _hours_held(opened_at)

    if tp_orig and entry:
        # TP distance decays 10% per 4h, floor at 50%
        decay_steps = int(hours / 4)
        decay_factor = max(0.5, 1.0 - 0.10 * decay_steps)
        tp_distance = abs(tp_orig - entry) * decay_factor
        if is_long:
            effective_tp = entry + tp_distance
        else:
            effective_tp = entry - tp_distance

        if (is_long and price >= effective_tp) or (not is_long and price <= effective_tp):
            return "EXIT", pnl, f"Decayed TP hit at {price:.6g} (eff_tp {effective_tp:.6g}, decay {decay_factor:.0%}, {hours:.1f}h held)"

    if sl and ((is_long and price <= sl) or (not is_long and price >= sl)):
        return "EXIT", pnl, f"SL hit at {price:.6g} (stop {sl:.6g})"

    return "HOLD", pnl, ""


# ── Model D: Partial exit (50% at 1R, trail rest to 2R or SL) ───────────

def _check_model_d(pos, price):
    entry = pos["entry_price"]
    tp = pos.get("take_profit", 0)
    sl = pos.get("stop_loss", 0)
    direction = pos.get("direction", "BUY")
    symbol = pos.get("symbol", "?")
    is_long = direction in ("BUY", "LONG")
    pnl = _pnl_pct(entry, price, direction)
    state = _get_state(symbol)

    # 1R = distance from entry to SL
    if sl and entry:
        risk = abs(entry - sl)
    elif tp and entry:
        risk = abs(tp - entry) / 2  # fallback: half of TP distance
    else:
        risk = abs(entry * 0.02)  # fallback: 2%

    one_r = risk
    two_r = risk * 2

    if is_long:
        one_r_price = entry + one_r
        two_r_price = entry + two_r
    else:
        one_r_price = entry - one_r
        two_r_price = entry - two_r

    # First exit: 50% at 1R
    if not state["D_first_exit_done"]:
        if (is_long and price >= one_r_price) or (not is_long and price <= one_r_price):
            state["D_first_exit_done"] = True
            state["D_remainder_hwm"] = price
            return "PARTIAL_EXIT", pnl, f"50% exit at 1R ({price:.6g}, 1R={one_r_price:.6g})"

        # SL before 1R
        if sl and ((is_long and price <= sl) or (not is_long and price >= sl)):
            return "EXIT", pnl, f"Full SL hit before 1R at {price:.6g}"
        return "HOLD", pnl, ""

    # Remainder: trail to 2R or back to SL
    if state["D_remainder_hwm"] is None:
        state["D_remainder_hwm"] = price
    if is_long:
        state["D_remainder_hwm"] = max(state["D_remainder_hwm"], price)
    else:
        state["D_remainder_hwm"] = min(state["D_remainder_hwm"], price)

    if (is_long and price >= two_r_price) or (not is_long and price <= two_r_price):
        return "EXIT", pnl, f"Remainder exit at 2R ({price:.6g}, 2R={two_r_price:.6g})"

    # trail remainder: stop at 1R (breakeven-ish) once past 1R
    if is_long:
        remainder_stop = one_r_price
        if price <= remainder_stop:
            return "EXIT", pnl, f"Remainder trailed back to 1R stop ({price:.6g})"
    else:
        remainder_stop = one_r_price
        if price >= remainder_stop:
            return "EXIT", pnl, f"Remainder trailed back to 1R stop ({price:.6g})"

    return "HOLD", pnl, ""


# ── Main API ─────────────────────────────────────────────────────────────

MODELS = {
    "A_fixed": _check_model_a,
    "B_trailing": _check_model_b,
    "C_timedecay": _check_model_c,
    "D_partial": _check_model_d,
}


def update_shadow_exits(positions, prices):
    """
    Run all 4 shadow exit models on each position.

    Args:
        positions: dict keyed by position_id -> position dict
                   (must have: symbol, entry_price, take_profit, stop_loss, direction, opened_at)
        prices: dict keyed by symbol -> float current price

    Returns:
        list of shadow event dicts
    """
    events = []
    ts = _now_utc().isoformat()

    for pos_id, pos in positions.items():
        symbol = pos.get("symbol", "")
        price = prices.get(symbol)
        if price is None:
            continue

        for model_name, model_fn in MODELS.items():
            action, pnl, reason = model_fn(pos, price)
            events.append({
                "timestamp": ts,
                "symbol": symbol,
                "model": model_name,
                "action": action,
                "exit_price": price if action != "HOLD" else None,
                "pnl_pct": round(pnl, 4),
                "reason": reason,
            })

    # persist
    history = _load_json(SHADOW_LOG_PATH)
    history.extend(events)
    history = history[-MAX_LOG_ENTRIES:]
    _save_json(SHADOW_LOG_PATH, history)

    return events


def get_shadow_summary(history_path=None):
    """
    Read shadow log and compute per-model statistics.

    Returns:
        dict keyed by model name -> {trades_closed, win_rate, avg_pnl, profit_factor}
    """
    path = history_path or SHADOW_LOG_PATH
    history = _load_json(path)

    stats = {}
    for model_name in MODELS:
        closed = [e for e in history if e["model"] == model_name and e["action"] in ("EXIT", "PARTIAL_EXIT")]
        wins = [e for e in closed if e["pnl_pct"] > 0]
        losses = [e for e in closed if e["pnl_pct"] <= 0]

        total_closed = len(closed)
        win_rate = len(wins) / total_closed if total_closed else 0
        avg_pnl = sum(e["pnl_pct"] for e in closed) / total_closed if total_closed else 0

        gross_profit = sum(e["pnl_pct"] for e in wins) if wins else 0
        gross_loss = abs(sum(e["pnl_pct"] for e in losses)) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (999 if gross_profit > 0 else 0)

        stats[model_name] = {
            "trades_closed": total_closed,
            "win_rate": round(win_rate, 4),
            "avg_pnl": round(avg_pnl, 4),
            "profit_factor": round(profit_factor, 4),
        }

    return stats


# ── Price fetching (Binance → CoinGecko → KuCoin fallback) ──────────────

def _fetch_binance_price(symbol):
    """Try Binance first."""
    clean = symbol.replace("-", "").replace("/", "").upper()
    # skip forex / equity symbols
    if "=" in symbol or "." in symbol:
        return None
    urls = [
        f"https://api.binance.com/api/v3/ticker/price?symbol={clean}",
        f"https://api1.binance.com/api/v3/ticker/price?symbol={clean}",
        f"https://api2.binance.com/api/v3/ticker/price?symbol={clean}",
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "shadow-exit-tracker/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                return float(data["price"])
        except Exception:
            continue
    return None


def _fetch_coingecko_price(symbol):
    """CoinGecko fallback."""
    clean = symbol.replace("USDT", "").replace("USD", "").replace("-", "").lower()
    id_map = {
        "btc": "bitcoin", "eth": "ethereum", "sol": "solana", "xrp": "ripple",
        "doge": "dogecoin", "ada": "cardano", "avax": "avalanche-2", "dot": "polkadot",
        "matic": "matic-network", "link": "chainlink", "atom": "cosmos", "uni": "uniswap",
        "kas": "kaspa", "hype": "hyperliquid", "sui": "sui", "xag": "silver",
    }
    cg_id = id_map.get(clean)
    if not cg_id:
        return None
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "shadow-exit-tracker/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return float(data[cg_id]["usd"])
    except Exception:
        return None


def fetch_live_prices(symbols):
    """Fetch prices for a list of symbols with fallback chain."""
    prices = {}
    for sym in symbols:
        price = _fetch_binance_price(sym)
        if price is None:
            price = _fetch_coingecko_price(sym)
        if price is not None:
            prices[sym] = price
    return prices


# ── CLI ──────────────────────────────────────────────────────────────────

def main():
    print("=== Shadow Exit Tracker ===")
    print(f"Time: {_now_utc().isoformat()}")
    print()

    # load portfolio
    if not os.path.exists(PORTFOLIO_PATH):
        print(f"ERROR: {PORTFOLIO_PATH} not found")
        sys.exit(1)

    portfolio = _load_json(PORTFOLIO_PATH)
    positions = portfolio.get("positions", {})
    if not positions:
        print("No open positions found.")
        sys.exit(0)

    print(f"Loaded {len(positions)} positions from portfolio_1x.json")

    # collect unique symbols and fetch prices
    symbols = list(set(p["symbol"] for p in positions.values()))
    print(f"Fetching prices for {len(symbols)} symbols...")
    prices = fetch_live_prices(symbols)
    print(f"Got prices for {len(prices)}/{len(symbols)} symbols")
    print()

    # run shadow models
    events = update_shadow_exits(positions, prices)

    # display results
    exits = [e for e in events if e["action"] != "HOLD"]
    holds = [e for e in events if e["action"] == "HOLD"]

    if exits:
        print(f"--- Shadow Exits ({len(exits)}) ---")
        for e in exits:
            print(f"  [{e['model']}] {e['symbol']}: {e['action']} pnl={e['pnl_pct']:+.2f}% — {e['reason']}")
    else:
        print("No shadow exits triggered this run.")

    print(f"\n{len(holds)} model/position combos still holding.")

    # summary
    print("\n--- Model Comparison ---")
    summary = get_shadow_summary()
    for model, stats in summary.items():
        print(f"  {model}: closed={stats['trades_closed']} WR={stats['win_rate']:.1%} "
              f"avg_pnl={stats['avg_pnl']:+.2f}% PF={stats['profit_factor']:.2f}")

    print(f"\nShadow log: {SHADOW_LOG_PATH}")


if __name__ == "__main__":
    main()
