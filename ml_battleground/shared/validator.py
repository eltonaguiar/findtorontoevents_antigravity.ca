"""
Forward validation for ML Battleground.
Checks active picks against live Binance prices.
Records TP/SL/trailing/expiry outcomes.
"""
import json
import os
import time
import requests
from datetime import datetime, timezone, timedelta
from typing import Optional

from . import cost_model


EST = timezone(timedelta(hours=-5))
TRAIL_ACTIVATE_PCT = 0.03   # activate trailing after +3% (was 1.5% — too aggressive, killed winners)
TRAIL_STOP_PCT = 0.03       # trail 3% from high-water mark (was 2% — crypto needs breathing room)
MAX_HOLD_HOURS = {
    "15m": 48,    # 2 days for scalp
    "1h": 168,    # 7 days for swing
    "4h": 120,    # 30 bars x 4h = 120h (5 days) for System C neural net
}


def validate_picks(
    active: list[dict],
    system_name: str,
    data_dir: str,
    fear_greed: Optional[int] = None,
) -> tuple[list[dict], list[dict]]:
    """
    Validate active picks against live prices.
    Returns (still_active, newly_closed).

    Args:
        fear_greed: Current Fear & Greed index. When provided and ≤ 15,
            SHORT positions losing > 1% are force-closed (bounce detector).
            Mercury 2 proves LONG is the edge in extreme fear — holding
            shorts is fighting the proven edge.
    """
    if not active:
        return [], []

    # Fetch current prices
    symbols = list(set(p["symbol"] for p in active))
    prices = _fetch_live_prices(symbols)

    still_active = []
    newly_closed = []
    now = datetime.now(timezone.utc)

    for pick in active:
        symbol = pick["symbol"]
        if symbol not in prices:
            still_active.append(pick)
            continue

        price_data = prices[symbol]
        current = price_data["price"]
        day_high = price_data["high"]
        day_low = price_data["low"]

        entry = pick["entry_price"]
        tp = pick["take_profit"]
        sl = pick["stop_loss"]
        signal = pick.get("signal_type", "BUY")
        timeframe = pick.get("timeframe", "1h")
        opened_at = datetime.fromisoformat(pick["timestamp"])

        # --- BOUNCE DETECTOR (Mercury feedback, Feb 25 2026) ---
        # When F&G ≤ 15 (extreme fear), SHORT positions are fighting the
        # proven contrarian-long edge. Force-close shorts losing > 1% to
        # stop the bleeding. Mercury 2 (94% WR) proves longs win here.
        if (fear_greed is not None and fear_greed <= 15
                and signal == "SELL"):
            unrealized_pct = (entry - current) / entry * 100 if entry > 0 else 0
            if unrealized_pct < -1.0:  # losing more than 1%
                pick["exit_price"] = current
                pick["exit_reason"] = "bounce_close"
                pick["closed_at"] = now.isoformat()
                pick["closed_at_est"] = now.astimezone(EST).strftime("%Y-%m-%d %I:%M %p EST")
                pick["bounce_detector"] = True
                pick["fear_greed_at_close"] = fear_greed
                _record_pnl(pick)
                newly_closed.append(pick)
                print(f"  [BOUNCE CLOSE] {symbol} SHORT: F&G={fear_greed}, "
                      f"unrealized={unrealized_pct:+.2f}% — force-closed")
                continue

        # Track high-water mark using CURRENT price (not 24h extremes)
        # Old bug: day_high/day_low includes wicks from before the trade opened
        if signal == "BUY":
            hwm = max(pick.get("hwm", entry), current)
        else:
            hwm = min(pick.get("hwm", entry), current)
        pick["hwm"] = hwm

        # Check expiry
        max_hold = MAX_HOLD_HOURS.get(timeframe, 168)
        hours_held = (now - opened_at).total_seconds() / 3600
        if hours_held > max_hold:
            pick["exit_price"] = current
            pick["exit_reason"] = "expiry"
            pick["closed_at"] = now.isoformat()
            pick["closed_at_est"] = now.astimezone(EST).strftime("%Y-%m-%d %I:%M %p EST")
            _record_pnl(pick)
            newly_closed.append(pick)
            continue

        # Trailing stop: ratchet SL up to lock in profits BEFORE checking SL
        # This ensures the SL check uses the updated (tighter) level
        if signal == "BUY":
            unrealized = (hwm - entry) / entry
            if unrealized > TRAIL_ACTIVATE_PCT:
                trail_level = hwm * (1 - TRAIL_STOP_PCT)
                if trail_level > sl:
                    sl = trail_level
                    pick["stop_loss"] = sl  # update the pick's SL
                    pick["trailing_active"] = True
        else:
            unrealized = (entry - hwm) / entry
            if unrealized > TRAIL_ACTIVATE_PCT:
                trail_level = hwm * (1 + TRAIL_STOP_PCT)
                if trail_level < sl:
                    sl = trail_level
                    pick["stop_loss"] = sl  # update the pick's SL
                    pick["trailing_active"] = True

        # Check SL using BOTH current price AND intra-candle high/low
        # Old bug: only checked current price, missing SL hits between validator runs
        SL_BUFFER = 0.003  # 0.3% tolerance
        if signal == "BUY":
            sl_hit = current <= sl * (1 + SL_BUFFER) or day_low <= sl
        else:
            sl_hit = current >= sl * (1 - SL_BUFFER) or day_high >= sl
        if sl_hit:
            # Use SL price as exit (not current which may have bounced back)
            pick["exit_price"] = sl if (current > sl if signal == "BUY" else current < sl) else current
            exit_reason = "trailing_stop" if pick.get("trailing_active") else "stop_loss"
            pick["exit_reason"] = exit_reason
            pick["closed_at"] = now.isoformat()
            pick["closed_at_est"] = now.astimezone(EST).strftime("%Y-%m-%d %I:%M %p EST")
            _record_pnl(pick)
            newly_closed.append(pick)
            continue

        # Check TP using BOTH current price AND intra-candle high/low
        if signal == "BUY":
            tp_hit = current >= tp * (1 - SL_BUFFER) or day_high >= tp
        else:
            tp_hit = current <= tp * (1 + SL_BUFFER) or day_low <= tp
        if tp_hit:
            # Use TP price as exit (not current which may have moved past)
            pick["exit_price"] = tp if (current < tp if signal == "BUY" else current > tp) else current
            pick["exit_reason"] = "take_profit"
            pick["closed_at"] = now.isoformat()
            pick["closed_at_est"] = now.astimezone(EST).strftime("%Y-%m-%d %I:%M %p EST")
            _record_pnl(pick)
            newly_closed.append(pick)
            continue

        # Update current price for dashboard
        pick["current_price"] = current
        pick["unrealized_pnl_pct"] = ((current - entry) / entry * 100) if signal == "BUY" else ((entry - current) / entry * 100)
        still_active.append(pick)

    return still_active, newly_closed


def save_picks(active: list[dict], closed: list[dict], data_dir: str):
    """Save active and closed picks to JSON files."""
    os.makedirs(data_dir, exist_ok=True)

    # Feed hygiene: strip resolved/zero-entry rows before persisting
    _CLOSED_STATUSES = frozenset({
        "CLOSED", "RESOLVED", "STALE", "WON", "LOST",
        "TP_HIT", "SL_HIT", "TIME_EXPIRY", "EXPIRED",
        "CANCELLED", "KILLED", "ELIMINATED",
    })
    def _is_valid_active(p):
        if not isinstance(p, dict): return False
        try:
            ep = float(p.get("entry_price") or 0)
        except (TypeError, ValueError):
            ep = 0.0
        if ep <= 0: return False
        if str(p.get("status", "")).upper().strip() in _CLOSED_STATUSES: return False
        try:
            ex = float(p.get("exit_price") or 0)
        except (TypeError, ValueError):
            ex = 0.0
        if ex > 0: return False
        if p.get("resolved_at") or p.get("closed_at") or p.get("exit_time"): return False
        if not p.get("symbol"): return False
        return True
    clean_active = [p for p in active if _is_valid_active(p)]
    removed = len(active) - len(clean_active)
    if removed:
        import logging; logging.getLogger(__name__).info(
            "[feed_hygiene] save_picks: removed %d invalid active picks", removed)
    active = clean_active

    with open(os.path.join(data_dir, "active_picks.json"), "w") as f:
        json.dump(active, f, indent=2, default=str)

    closed_path = os.path.join(data_dir, "closed_picks.json")
    existing_closed = []
    if os.path.exists(closed_path):
        with open(closed_path) as f:
            existing_closed = json.load(f)

    # Backfill pnl_pct for legacy closed picks that only have net_pnl_pct/gross_pnl_pct
    for pick in existing_closed:
        if "pnl_pct" not in pick:
            if "net_pnl_pct" in pick:
                pick["pnl_pct"] = pick["net_pnl_pct"]
            elif "gross_pnl_pct" in pick:
                pick["pnl_pct"] = pick["gross_pnl_pct"]
            elif pick.get("entry_price") and pick.get("exit_price"):
                entry = pick["entry_price"]
                exit_p = pick["exit_price"]
                sig = pick.get("signal_type", "BUY")
                if sig == "BUY":
                    pick["pnl_pct"] = round((exit_p - entry) / entry * 100, 4)
                else:
                    pick["pnl_pct"] = round((entry - exit_p) / entry * 100, 4)

    existing_closed.extend(closed)
    with open(closed_path, "w") as f:
        json.dump(existing_closed, f, indent=2, default=str)


def load_active(data_dir: str) -> list[dict]:
    """Load active picks from JSON."""
    path = os.path.join(data_dir, "active_picks.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []


def load_closed(data_dir: str) -> list[dict]:
    """Load closed picks from JSON."""
    path = os.path.join(data_dir, "closed_picks.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []


def _record_pnl(pick: dict):
    """Calculate and record PnL on a closed pick."""
    entry = pick["entry_price"]
    exit_price = pick["exit_price"]
    signal = pick.get("signal_type", "BUY")
    pair = pick["symbol"]

    if signal == "BUY":
        gross_pnl = (exit_price - entry) / entry * 100
    else:
        gross_pnl = (entry - exit_price) / entry * 100

    cost = cost_model.round_trip_cost(pair) * 100
    pick["gross_pnl_pct"] = round(gross_pnl, 4)
    pick["net_pnl_pct"] = round(gross_pnl - cost, 4)
    pick["pnl_pct"] = round(gross_pnl - cost, 4)  # alias for consumers that read pnl_pct
    pick["cost_pct"] = round(cost, 4)


def _fetch_live_prices(symbols: list[str]) -> dict:
    """
    Fetch live prices with 3-tier fallback:
      1. Binance (best data, blocked on GitHub Actions)
      2. OKX (good fallback, individual symbol calls)
      3. CoinGecko (last resort, free tier, fewer pairs)
    """
    result = {}

    # --- Tier 1: Binance (single bulk call, works locally) ---
    try:
        resp = requests.get(
            "https://api.binance.com/api/v3/ticker/24hr",
            timeout=10,
        )
        resp.raise_for_status()
        for item in resp.json():
            sym = item["symbol"]
            if sym in symbols:
                result[sym] = {
                    "price": float(item["lastPrice"]),
                    "high": float(item["highPrice"]),
                    "low": float(item["lowPrice"]),
                }
    except Exception as e:
        print(f"  [validator] Binance failed: {e}")

    # --- Tier 2: OKX (per-symbol, works on CI) ---
    missing = [s for s in symbols if s not in result]
    if missing:
        print(f"  [validator] OKX fallback for {len(missing)} symbols")
        for sym in missing:
            try:
                okx_sym = sym.replace("USDT", "-USDT")
                resp = requests.get(
                    f"https://www.okx.com/api/v5/market/ticker?instId={okx_sym}",
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json().get("data", [])
                if data:
                    t = data[0]
                    result[sym] = {
                        "price": float(t["last"]),
                        "high": float(t["high24h"]),
                        "low": float(t["low24h"]),
                    }
                time.sleep(0.1)
            except Exception as e:
                print(f"  [validator] OKX failed for {sym}: {e}")

    # --- Tier 3: CoinGecko (last resort — price only, no 24h high/low) ---
    missing = [s for s in symbols if s not in result]
    if missing:
        print(f"  [validator] CoinGecko last-resort for {len(missing)} symbols")
        # Map BTCUSDT → bitcoin, ETHUSDT → ethereum, etc.
        _CG_IDS = {
            "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
            "BNBUSDT": "binancecoin", "XRPUSDT": "ripple", "ADAUSDT": "cardano",
            "DOGEUSDT": "dogecoin", "TAOUSDT": "bittensor", "AVAXUSDT": "avalanche-2",
            "LINKUSDT": "chainlink", "NEARUSDT": "near", "SUIUSDT": "sui",
            "APTUSDT": "aptos", "ARBUSDT": "arbitrum", "OPUSDT": "optimism",
            "INJUSDT": "injective-protocol", "FETUSDT": "fetch-ai",
            "TIAUSDT": "celestia", "SEIUSDT": "sei-network", "FILUSDT": "filecoin",
            "RENDERUSDT": "render-token", "ETCUSDT": "ethereum-classic",
            "ATOMUSDT": "cosmos", "HBARUSDT": "hedera-hashgraph", "TRXUSDT": "tron",
            "SHIBUSDT": "shiba-inu",
        }
        cg_ids = [_CG_IDS[s] for s in missing if s in _CG_IDS]
        if cg_ids:
            try:
                resp = requests.get(
                    "https://api.coingecko.com/api/v3/simple/price",
                    params={"ids": ",".join(cg_ids), "vs_currencies": "usd",
                            "include_24hr_high": "true", "include_24hr_low": "true"},
                    timeout=10,
                )
                resp.raise_for_status()
                cg_data = resp.json()
                # Reverse map: id → symbol
                id_to_sym = {v: k for k, v in _CG_IDS.items() if k in missing}
                for cg_id, info in cg_data.items():
                    sym = id_to_sym.get(cg_id)
                    if sym and "usd" in info:
                        price = float(info["usd"])
                        high = float(info.get("usd_24h_high", price))
                        low = float(info.get("usd_24h_low", price))
                        result[sym] = {"price": price, "high": high, "low": low}
            except Exception as e:
                print(f"  [validator] CoinGecko failed: {e}")

    found = len(result)
    total = len(symbols)
    if found < total:
        print(f"  [validator] WARNING: only got prices for {found}/{total} symbols")
    else:
        print(f"  [validator] Got live prices for all {total} symbols")

    return result


def passes_validation_gate(closed_picks: list) -> dict:
    """
    Institutional 8-check validation gate.
    Returns dict with status, checks_passed, and recommendation.

    Status levels:
    - COLLECTING: <30 trades, still gathering data
    - TESTING: 30+ trades but failing >5 checks
    - MARGINAL: Passing 3-4 checks
    - PROVEN: Passing 5-6 checks (WR>50%, Sharpe>1.0, DD<15%)
    - ELITE: Passing 7-8 checks (institutional quality)
    """
    from .performance import compute_institutional_metrics

    metrics = compute_institutional_metrics(closed_picks)

    result = {
        "status": metrics["status"],
        "checks_passed": metrics["checks_passed"],
        "total_checks": 8,
        "sample_size": metrics["sample_size"],
        "win_rate": metrics["win_rate"],
        "sharpe_ratio": metrics["sharpe_ratio"],
        "profit_factor": metrics["profit_factor"],
        "max_drawdown_pct": metrics["max_drawdown_pct"],
        "expectancy": metrics["expectancy"],
        "calmar_ratio": metrics["calmar_ratio"],
        "p_value": metrics["p_value"],
        "check_details": metrics["check_details"],
    }

    # Recommendation based on status
    if metrics["status"] == "ELITE":
        result["recommendation"] = "SCALE UP: Increase position size, reduce restrictions"
    elif metrics["status"] == "PROVEN":
        result["recommendation"] = "MAINTAIN: Continue current strategy, monitor for decay"
    elif metrics["status"] == "MARGINAL":
        result["recommendation"] = "OPTIMIZE: Review losing trades, tighten filters"
    elif metrics["status"] == "TESTING":
        result["recommendation"] = "REVIEW: Strategy may need fundamental changes"
    else:
        result["recommendation"] = "COLLECT: Need 15+ closed trades for evaluation"

    return result
