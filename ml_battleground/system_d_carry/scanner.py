# Research-backed: R001 (Hedge Fund Quant), R005 (Risk Mgmt), R026 (Cross-Exchange Arb)
"""
System D Scanner: "The Carry Trade"
Funding rate carry / contrarian strategy.

Pipeline:
  1. Load active picks, validate existing (TP/SL/trailing/expiry)
  2. Scan Binance perpetual funding rates for all PAIRS
  3. SHORT when funding > 0.03% (longs overleveraged) + top 20% of 30d range + RSI > 55
  4. LONG when funding < -0.01% (shorts overleveraged) + bottom 20% of 30d range + RSI < 45
  5. F&G extreme confluence: < 25 BUY boost, > 75 SELL boost (+10% confidence)
  6. ATR-based TP/SL on 4h (TP = 2.5x ATR, SL = 1.5x ATR), minimum R:R 1.5
  7. Apply all standard gates (risk, health, E[R], adaptive, strategy health, symbol lock)
  8. Save picks, send Discord notifications, write dashboard + funding heatmap

Run: python -m ml_battleground.system_d_carry.scanner
"""
import os
import sys
import json
import time
import requests
import numpy as np
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.data_fetcher import fetch_ohlcv, fetch_fear_greed, fetch_funding_rates, PAIRS
from shared.indicators import atr, rsi, ema
from shared.risk_manager import can_open_trade, calculate_drawdown, position_size, should_trade
from shared.cost_model import round_trip_cost
from shared.validator import validate_picks, save_picks, load_active, load_closed, passes_validation_gate
from shared.performance import compute_stats
from shared.discord_notify import send_system_status, send_pick_alert, send_pick_exit
from shared.market_health import check_market_health, apply_health_gate, MarketHealth, dynamic_sl_multiplier
from shared.trade_filters import adaptive_threshold, atr_percentile_filter, volume_confirmation
from shared.strategy_health import filter_signals_by_health
from shared.symbol_lock import filter_signals_by_lock
from shared.revision_marker import check_revision
from shared.meta_labeler import filter_signals_batch as meta_label_filter
from shared.external_signals import fetch_external_signals, apply_external_confluence_batch, log_external_signals_summary
from shared.feature_snapshot import snapshot_from_dict

VERSION = "1.0.0"
SYSTEM_NAME = "system_d_carry"
SYSTEM_LABEL = "The Carry Trade"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MIN_RR = 1.5
MIN_CONFIDENCE = 0.42  # lowered from 0.52 — System D never generated a single pick in 13 days
EST = timezone(timedelta(hours=-5))
SCAN_FREQUENCY = "Every 30 minutes"
SCAN_STATE_PATH = os.path.join(DATA_DIR, "last_scan_state.json")

# Funding rate thresholds (research-backed)
FUNDING_SHORT_THRESHOLD = 0.0003   # 0.03% — longs overleveraged, pay shorts
FUNDING_LONG_THRESHOLD = -0.0001   # -0.01% — shorts overleveraged, pay longs
FUNDING_PCTILE_HIGH = 80           # top 20% of 30d range for SHORT
FUNDING_PCTILE_LOW = 20            # bottom 20% of 30d range for LONG
RSI_SHORT_MIN = 55                 # RSI confluence for SHORT
RSI_LONG_MAX = 45                  # RSI confluence for LONG


# ---------------------------------------------------------------------------
# Funding Rate History (Binance Futures API)
# ---------------------------------------------------------------------------

_funding_cache: dict[str, tuple[float, list[float]]] = {}  # pair -> (timestamp, rates)
_FUNDING_CACHE_TTL = 3600  # 1 hour cache

def fetch_funding_history(pair: str, limit: int = 90) -> list[float]:
    """Fetch last ~30 days of funding rates (3 per day x 30 = 90).

    Returns list of float funding rates, newest last.
    Uses cache + retry to handle Binance API timeouts during high load.
    """
    import time as _time

    # Check cache first
    if pair in _funding_cache:
        cached_ts, cached_rates = _funding_cache[pair]
        if _time.time() - cached_ts < _FUNDING_CACHE_TTL:
            return cached_rates

    # 5-source failover: OKX → Bybit → KuCoin → Binance → dYdX
    # OKX first (no geo-block), Binance last (451 on GitHub Actions)
    sources = [
        ("okx", "https://www.okx.com/api/v5/public/funding-rate-history"),
        ("bybit", "https://api.bybit.com/v5/market/funding/history"),
        ("kucoin", "https://api-futures.kucoin.com/api/v1/contract/funding-rates"),
        ("binance", "https://fapi.binance.com/fapi/v1/fundingRate"),
        ("dydx", "https://indexer.dydx.trade/v4/historicalFunding"),
    ]
    for source, url in sources:
        try:
            if source == "okx":
                inst_id = pair.replace("USDT", "-USDT-SWAP")
                resp = requests.get(url, params={"instId": inst_id, "limit": str(limit)}, timeout=15)
                resp.raise_for_status()
                data = resp.json().get("data", [])
                data.reverse()  # OKX returns newest first
                rates = [float(r["fundingRate"]) for r in data]
            elif source == "bybit":
                resp = requests.get(url, params={"category": "linear", "symbol": pair, "limit": str(limit)}, timeout=15)
                resp.raise_for_status()
                items = resp.json().get("result", {}).get("list", [])
                items.reverse()  # Bybit returns newest first
                rates = [float(r["fundingRate"]) for r in items]
            elif source == "kucoin":
                kucoin_sym = pair.replace("USDT", "USDTM")  # BTCUSDT → BTCUSDTM
                resp = requests.get(url + f"/{kucoin_sym}", params={"maxCount": str(limit)}, timeout=15)
                resp.raise_for_status()
                items = resp.json().get("data", {}).get("dataList", [])
                rates = [float(r["fundingRate"]) for r in reversed(items)]
            elif source == "binance":
                resp = requests.get(url, params={"symbol": pair, "limit": limit}, timeout=15)
                resp.raise_for_status()
                rates = [float(r["fundingRate"]) for r in resp.json()]
            elif source == "dydx":
                # dYdX v4 uses different symbol format: BTC-USD
                dydx_sym = pair.replace("USDT", "-USD")
                resp = requests.get(url + f"/{dydx_sym}", params={"limit": str(limit)}, timeout=15)
                resp.raise_for_status()
                items = resp.json().get("historicalFunding", [])
                rates = [float(r["rate"]) for r in reversed(items)]
            else:
                continue
            if rates:
                _funding_cache[pair] = (_time.time(), rates)
                return rates
        except Exception:
            continue
    # Return stale cache if available, else empty
    if pair in _funding_cache:
        return _funding_cache[pair][1]
    return []


def percentile_rank(value: float, history: list[float]) -> float:
    """Return percentile rank (0-100) of value within history.

    If history is empty, returns 50.0 (neutral).
    """
    if not history:
        return 50.0
    arr = np.array(history)
    return float(np.sum(arr <= value) / len(arr) * 100.0)


# ---------------------------------------------------------------------------
# Signal Generation
# ---------------------------------------------------------------------------

def generate_funding_signals(
    pair: str,
    current_rate: float,
    historical_rates: list[float],
    rsi_val: float,
    fear_greed: int,
    df,  # pd.DataFrame with OHLCV
    vol_col: str = "Volume",
) -> dict | None:
    """Evaluate funding rate signal for a single pair.

    Returns a signal dict or None if no signal qualifies.
    """
    if not historical_rates or len(historical_rates) < 10:
        return None

    funding_pctile = percentile_rank(current_rate, historical_rates)

    signal_type = None
    strategy_reason = None

    # --- SHORT signal ---
    if (current_rate > FUNDING_SHORT_THRESHOLD
            and funding_pctile >= FUNDING_PCTILE_HIGH
            and rsi_val > RSI_SHORT_MIN):
        signal_type = "SELL"
        strategy_reason = (
            f"Funding {current_rate:.4%} > {FUNDING_SHORT_THRESHOLD:.4%} "
            f"(P{funding_pctile:.0f} of 30d), RSI {rsi_val:.1f} > {RSI_SHORT_MIN}"
        )

    # --- LONG signal ---
    elif (current_rate < FUNDING_LONG_THRESHOLD
          and funding_pctile <= FUNDING_PCTILE_LOW
          and rsi_val < RSI_LONG_MAX):
        signal_type = "BUY"
        strategy_reason = (
            f"Funding {current_rate:.4%} < {FUNDING_LONG_THRESHOLD:.4%} "
            f"(P{funding_pctile:.0f} of 30d), RSI {rsi_val:.1f} < {RSI_LONG_MAX}"
        )

    if signal_type is None:
        return None

    # --- Confidence calculation ---
    confidence = 0.55  # base

    # Funding rate strength: how extreme is the rate vs history
    if funding_pctile > 90 or funding_pctile < 10:
        confidence += 0.10  # extreme = high conviction
    elif funding_pctile > 80 or funding_pctile < 20:
        confidence += 0.05

    # RSI confluence
    if (signal_type == "SELL" and rsi_val > 65) or (signal_type == "BUY" and rsi_val < 35):
        confidence += 0.10

    # F&G extreme confluence
    if (signal_type == "BUY" and fear_greed <= 25) or (signal_type == "SELL" and fear_greed >= 75):
        confidence += 0.10

    # Volume confirmation
    vol_ok, vol_ratio = volume_confirmation(df[vol_col].values)
    if vol_ok and vol_ratio > 1.5:
        confidence += 0.05

    confidence = min(confidence, 0.95)  # cap at 95%

    if confidence < MIN_CONFIDENCE:
        return None

    # --- Entry price ---
    close_col = "close" if "close" in df.columns else "Close"
    entry_price = float(df[close_col].iloc[-1])

    return {
        "symbol": pair,
        "signal_type": signal_type,
        "strategy": "funding_rate_carry",
        "entry_price": entry_price,
        "confidence": round(confidence, 4),
        "reason": strategy_reason,
        "funding_rate": current_rate,
        "funding_percentile": round(funding_pctile, 1),
        "rsi": round(rsi_val, 2),
        "category": "crypto",
    }


# ---------------------------------------------------------------------------
# Main Scan
# ---------------------------------------------------------------------------

def _check_candle_gate(reference_df) -> bool:
    """Returns True if a new 1h candle has closed since last scan.

    Uses BTCUSDT 1h as the reference candle clock. If the latest candle
    close timestamp matches the stored one, skip the scan to avoid
    computing features on incomplete (mid-candle) data.
    """
    if reference_df is None or len(reference_df) == 0:
        return True  # No data = let it try
    latest_close = str(reference_df.index[-1])
    if os.path.exists(SCAN_STATE_PATH):
        try:
            with open(SCAN_STATE_PATH) as f:
                state = json.load(f)
            if state.get("last_candle_close") == latest_close:
                return False
        except (json.JSONDecodeError, OSError):
            pass
    # Update state
    os.makedirs(os.path.dirname(SCAN_STATE_PATH), exist_ok=True)
    with open(SCAN_STATE_PATH, 'w') as f:
        json.dump({"last_candle_close": latest_close}, f)
    return True


def scan():
    """Main scan cycle for System D — The Carry Trade."""
    now = datetime.now(timezone.utc)
    print(f"[System D - The Carry Trade] Scan started at {now.isoformat()}")
    print(f"  Version: {VERSION}")

    # Ensure data directory exists before any file operations
    os.makedirs(DATA_DIR, exist_ok=True)

    # Check for revision reset (archives pre-revision data, resets tracking)
    from pathlib import Path
    check_revision(SYSTEM_NAME, Path(DATA_DIR))

    # -------------------------------------------------------------------------
    # 1. Load existing state and validate active picks
    # -------------------------------------------------------------------------
    active = load_active(DATA_DIR)
    closed = load_closed(DATA_DIR)

    print(f"  Loaded: {len(active)} active, {len(closed)} closed")

    active, newly_closed = validate_picks(active, SYSTEM_NAME, DATA_DIR)

    if newly_closed:
        closed_symbols = [p["symbol"] for p in newly_closed]
        print(f"  Closed {len(newly_closed)} picks: {closed_symbols}")

        # Send Discord exit notifications
        for pick in newly_closed:
            try:
                send_pick_exit(SYSTEM_LABEL, pick)
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # 2. Compute stats and check risk budget
    # -------------------------------------------------------------------------
    stats = compute_stats(closed)
    equity_curve = stats.get("equity_curve", [10000.0])
    dd = calculate_drawdown(equity_curve)
    can_trade, reason = can_open_trade(len(active), dd)

    if not can_trade:
        print(f"  Cannot open new trades: {reason}")
        save_picks(active, newly_closed, DATA_DIR)
        _write_dashboard_data(active, closed, stats, {})
        print(f"[System D] Scan complete (risk limit).")
        return

    # Drawdown halt gate (8% DD = stop trading until recovery)
    ok_to_trade, halt_reason = should_trade(equity_curve)
    if not ok_to_trade:
        print(f"  {halt_reason}")
        save_picks(active, newly_closed, DATA_DIR)
        _write_dashboard_data(active, closed, stats, {})
        print(f"[System D] Scan complete (drawdown halt).")
        return

    # -------------------------------------------------------------------------
    # 3. Fetch market context
    # -------------------------------------------------------------------------
    fear_greed = fetch_fear_greed()
    funding_rates = fetch_funding_rates()
    print(f"  Fear & Greed: {fear_greed}")

    # --- Market Health Gate ---
    btc_health_data = fetch_ohlcv(["BTCUSDT"], "1h", 300)
    btc_df_health = btc_health_data.get("BTCUSDT")

    # --- Candle-Close Gate: skip scan if no new 1h candle has closed ---
    if not _check_candle_gate(btc_df_health):
        print(f"  Skipping scan: no new 1h candle closed since last scan")
        save_picks(active, newly_closed, DATA_DIR)
        _write_dashboard_data(active, closed, stats, {})
        print(f"[System D] Scan complete (no new candle).")
        return

    health, health_details = check_market_health(fear_greed, btc_df_health, funding_rates)
    print(f"  Market Health: {health.value} | F&G={fear_greed}, BTC trend={health_details.get('btc_trend', '?')}, "
          f"BTC 24h={health_details.get('btc_24h_change', '?')}%, volatility={health_details.get('volatility', '?')}")

    if health == MarketHealth.PANIC:
        print(f"  *** PANIC MODE: scanning for SELL-only opportunities ***")

    # --- F&G Contrarian Bias (research-backed) ---
    fg_direction = None
    if fear_greed <= 15:
        fg_direction = "BUY"
        print(f"  F&G CONTRARIAN bias: BUY only (F&G={fear_greed} <= 15, extreme fear = buy opportunity)")
    elif fear_greed > 80:
        fg_direction = "SELL"
        print(f"  F&G CONTRARIAN bias: SELL only (F&G={fear_greed} > 80, extreme greed = sell opportunity)")
    else:
        print(f"  F&G: {fear_greed} (no directional filter)")

    # --- External Signal Confluence (Deribit + Binance Contrarian) ---
    ext_signals = fetch_external_signals()
    log_external_signals_summary(ext_signals)

    # -------------------------------------------------------------------------
    # 4. Fetch OHLCV (4h primary) + funding rate history, generate signals
    # -------------------------------------------------------------------------
    new_signals = []
    active_symbols = {p["symbol"] for p in active}
    funding_heatmap = {}

    # Fetch 4h OHLCV for all pairs (primary timeframe for carry trade)
    data_4h = fetch_ohlcv(PAIRS, "4h", 500)

    # If shared fetcher returned nothing, log it (common in GitHub Actions)
    if not funding_rates:
        print(f"  [WARN] Shared fetch_funding_rates returned empty — will use per-pair history fallback")

    for pair in PAIRS:
        # --- Fetch funding rate history (graceful skip on failure) ---
        current_rate = funding_rates.get(pair, None)
        historical_rates = fetch_funding_history(pair, limit=90)

        # Fallback chain: shared API -> historical API -> skip
        if current_rate is None and historical_rates:
            current_rate = historical_rates[-1]
            print(f"  [fallback] {pair}: using last historical rate {current_rate:.6f}")
        elif current_rate is None:
            # Last resort: try fetching current rate from OKX → Bybit → Binance
            for _src, _url, _parser in [
                ("OKX", "https://www.okx.com/api/v5/public/funding-rate",
                 lambda r, p: float(r.json()["data"][0]["fundingRate"]) if r.json().get("data") else None),
                ("Bybit", "https://api.bybit.com/v5/market/tickers",
                 lambda r, p: float(r.json()["result"]["list"][0]["fundingRate"])
                 if r.json().get("result", {}).get("list") else None),
                ("Binance", "https://fapi.binance.com/fapi/v1/premiumIndex",
                 lambda r, p: float(r.json()["lastFundingRate"]) if isinstance(r.json(), dict)
                 else float(r.json()[0]["lastFundingRate"]) if r.json() else None),
            ]:
                try:
                    if _src == "OKX":
                        inst_id = pair.replace("USDT", "-USDT-SWAP")
                        resp = requests.get(_url, params={"instId": inst_id}, timeout=10)
                    elif _src == "Bybit":
                        resp = requests.get(_url, params={"category": "linear", "symbol": pair}, timeout=10)
                    else:
                        resp = requests.get(_url, params={"symbol": pair}, timeout=10)
                    if resp.ok:
                        current_rate = _parser(resp, pair)
                        if current_rate is not None:
                            print(f"  [direct-fetch/{_src}] {pair}: got rate {current_rate:.6f}")
                            break
                except Exception:
                    continue
            if current_rate is None:
                print(f"  [skip] {pair}: no funding rate data after all fallbacks")
                funding_heatmap[pair] = {"rate": None, "percentile": None, "signal": None}
                continue

        if current_rate is None:
            print(f"  [skip] {pair}: no funding rate data after all fallbacks")
            funding_heatmap[pair] = {"rate": None, "percentile": None, "signal": None}
            continue

        funding_pctile = percentile_rank(current_rate, historical_rates) if historical_rates else 50.0

        # Determine heatmap signal direction
        heatmap_signal = None
        if current_rate > FUNDING_SHORT_THRESHOLD and funding_pctile >= FUNDING_PCTILE_HIGH:
            heatmap_signal = "SHORT"
        elif current_rate < FUNDING_LONG_THRESHOLD and funding_pctile <= FUNDING_PCTILE_LOW:
            heatmap_signal = "LONG"
        funding_heatmap[pair] = {
            "rate": round(current_rate, 6),
            "percentile": round(funding_pctile, 1),
            "signal": heatmap_signal,
        }

        # Skip if already active
        if pair in active_symbols:
            print(f"  [skip] {pair}: already active")
            continue

        # Check OHLCV data availability
        df = data_4h.get(pair)
        if df is None or len(df) < 50:
            print(f"  [skip] {pair}: insufficient 4h OHLCV data ({len(df) if df is not None else 0} bars)")
            continue

        # --- Compute RSI ---
        close_col = "close" if "close" in df.columns else "Close"
        high_col = "high" if "high" in df.columns else "High"
        low_col = "low" if "low" in df.columns else "Low"
        vol_col = "volume" if "volume" in df.columns else "Volume"

        rsi_series = rsi(df[close_col], 14)
        if len(rsi_series) < 1 or np.isnan(rsi_series.iloc[-1]):
            print(f"  [skip] {pair}: RSI not available")
            continue
        rsi_val = float(rsi_series.iloc[-1])

        # --- Generate funding rate signal ---
        sig = generate_funding_signals(
            pair=pair,
            current_rate=current_rate,
            historical_rates=historical_rates,
            rsi_val=rsi_val,
            fear_greed=fear_greed,
            df=df,
            vol_col=vol_col,
        )

        if sig is None:
            continue

        print(f"  {pair}: funding={current_rate:.4%} P{funding_pctile:.0f} RSI={rsi_val:.1f} -> {sig['signal_type']} (conf={sig['confidence']:.2f})")

        # --- F&G directional filter ---
        if fg_direction and sig["signal_type"] != fg_direction:
            print(f"    [filtered] {pair}: {sig['signal_type']} blocked (F&G={fear_greed} -> {fg_direction} only)")
            continue

        # --- Research-backed pre-trade filters ---

        # ATR percentile filter (Wilder 1978)
        atr_vals = atr(df[high_col], df[low_col], df[close_col], 14)
        if len(atr_vals) >= 50 and not atr_percentile_filter(atr_vals.values):
            print(f"    [filtered] {pair}: ATR outside 40-95th percentile")
            continue

        # Volume confirmation gate
        vol_ok, vol_ratio = volume_confirmation(df[vol_col].values)
        if not vol_ok:
            print(f"    [filtered] {pair}: volume ratio {vol_ratio:.2f} < 0.7")
            continue

        # --- ATR-based TP/SL (4h timeframe) ---
        atr_now = float(atr_vals.iloc[-1]) if len(atr_vals) > 0 else sig["entry_price"] * 0.02
        entry = sig["entry_price"]

        if sig["signal_type"] == "BUY":
            tp = entry + 2.5 * atr_now
            sl = entry - 1.5 * atr_now
        else:  # SELL
            tp = entry - 2.5 * atr_now
            sl = entry + 1.5 * atr_now

        # Calculate R:R
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        rr = reward / risk if risk > 0 else 0

        if rr < MIN_RR:
            print(f"    [filtered] {pair}: R:R {rr:.2f} < {MIN_RR}")
            continue

        # --- Dynamic SL widening during volatility spikes ---
        if len(df) >= 60:
            ranges = (df[high_col] - df[low_col]).values[-60:]
            current_range = float(ranges[-1])
            median_range = float(np.median(ranges[:-1]))
            if median_range > 0 and current_range / median_range > 2.0:
                old_sl = sl
                sl_dist = abs(entry - sl)
                if sig["signal_type"] == "BUY":
                    sl = entry - sl_dist * 1.5
                else:
                    sl = entry + sl_dist * 1.5
                # Recalculate R:R with widened SL
                risk = abs(entry - sl)
                reward = abs(tp - entry)
                rr = round(reward / risk, 2) if risk > 0 else 0
                print(f"    [volatility] Widening SL for {pair}: {old_sl:.4g} -> {sl:.4g}")

        # Dynamic SL widening based on market health
        health_sl_mult = dynamic_sl_multiplier(health, base_mult=1.0)
        if health_sl_mult > 1.0:
            old_sl = sl
            sl_dist = abs(entry - sl)
            if sig["signal_type"] == "BUY":
                sl = entry - sl_dist * health_sl_mult
            else:
                sl = entry + sl_dist * health_sl_mult
            risk = abs(entry - sl)
            reward = abs(tp - entry)
            rr = round(reward / risk, 2) if risk > 0 else 0
            print(f"    [health={health.value}] Widening SL for {pair}: {old_sl:.4g} -> {sl:.4g} ({health_sl_mult:.1f}x)")

        # --- Expected return pre-filter (Kimi/Lopez de Prado) ---
        cost = round_trip_cost(pair)
        tp_dist_pct = abs(tp - entry) / entry if entry > 0 else 0
        sl_dist_pct = abs(entry - sl) / entry if entry > 0 else 0
        conf = sig["confidence"]
        expected_return = conf * tp_dist_pct - (1 - conf) * sl_dist_pct - cost
        # 3x cost rule: E[R] must exceed 3 * round_trip_cost (min 30 bps)
        min_er = max(cost * 3, 0.003)
        if expected_return < min_er:
            print(f"    [filtered] {pair}: E[R]={expected_return:.4f} < min {min_er:.4f} "
                  f"(3x cost rule, prob={conf:.3f}, TP%={tp_dist_pct:.4f}, SL%={sl_dist_pct:.4f}, cost={cost:.4f})")
            continue

        # Adaptive threshold: cost-aware breakeven (Kissell 2020)
        min_conf = adaptive_threshold(tp_dist_pct, sl_dist_pct, cost)
        effective_min = max(min_conf, MIN_CONFIDENCE)
        if conf < effective_min:
            print(f"    [filtered] {pair}: confidence {conf:.3f} < threshold {effective_min:.3f}")
            continue

        # --- Attach full signal metadata ---
        current_price = float(df[close_col].iloc[-1])

        # Capture feature snapshot at entry time (Design 3E)
        _entry_features = {
            "close": float(df[close_col].iloc[-1]),
            "high": float(df[high_col].iloc[-1]),
            "low": float(df[low_col].iloc[-1]),
            "volume": float(df[vol_col].iloc[-1]),
            "atr_14": float(atr_vals.iloc[-1]) if len(atr_vals) > 0 else 0.0,
            "rsi_14": rsi_val,
            "funding_rate": current_rate,
            "funding_percentile": funding_pctile,
            "fear_greed": fear_greed,
            "confidence": sig["confidence"],
        }

        sig.update({
            "take_profit": round(tp, 8),
            "stop_loss": round(sl, 8),
            "risk_reward": round(rr, 2),
            "features": snapshot_from_dict(_entry_features),
            "tp_sl_method": "atr_4h_2.5x_1.5x",
            "timeframe": "4h",
            "market_health": health.value,
            "system": SYSTEM_NAME,
            "version": VERSION,
            "timestamp": now.isoformat(),
            "fear_greed": fear_greed,
            "timestamp_est": now.astimezone(EST).strftime("%Y-%m-%d %I:%M %p EST"),
            "current_price": current_price,
            "pick_reason": (
                f"funding_rate_carry signal on 4h "
                f"| {sig.get('reason', '')} "
                f"| Confidence {conf:.2f} | R:R {rr:.1f} "
                f"| TP/SL via ATR 2.5x/1.5x "
                f"| F&G={fear_greed} | Funding={current_rate:.4%}"
            ),
        })

        # Unrealized P&L
        if sig["signal_type"] == "BUY":
            sig["unrealized_pnl_pct"] = round((current_price - entry) / entry * 100, 4)
        else:
            sig["unrealized_pnl_pct"] = round((entry - current_price) / entry * 100, 4)

        new_signals.append(sig)
        # Rate-limit Binance API calls
        time.sleep(0.15)

    # -------------------------------------------------------------------------
    # 5. Meta-Labeler Quality Gate, then health gate, rank and select
    # -------------------------------------------------------------------------
    if new_signals:
        new_signals = meta_label_filter(new_signals, closed, SYSTEM_NAME)

    # --- External Signal Confluence (Deribit + Binance Contrarian) ---
    if new_signals:
        new_signals = apply_external_confluence_batch(new_signals, ext_signals)

    raw_count = len(new_signals)
    new_signals = apply_health_gate(health, new_signals)
    if raw_count > 0 and len(new_signals) < raw_count:
        print(f"  Health gate ({health.value}): {raw_count} -> {len(new_signals)} signals")

    # --- Strategy Health Gate: disable consistently losing strategies ---
    new_signals = filter_signals_by_health(new_signals, closed)

    # --- Cross-System Symbol Lock: prevent conflicting positions ---
    new_signals = filter_signals_by_lock(new_signals, SYSTEM_NAME)

    # Sort by confidence * R:R (best signals first)
    new_signals.sort(
        key=lambda s: s.get("confidence", 0) * s.get("risk_reward", 1.0),
        reverse=True,
    )

    # Deduplicate by symbol (keep best signal per pair)
    seen_symbols = set(active_symbols)
    deduped = []
    for sig in new_signals:
        if sig["symbol"] not in seen_symbols:
            deduped.append(sig)
            seen_symbols.add(sig["symbol"])
    if len(deduped) < len(new_signals):
        print(f"  Dedup: {len(new_signals)} -> {len(deduped)} signals (removed duplicate symbols)")
    new_signals = deduped

    added = 0
    for sig in new_signals:
        can, reason = can_open_trade(len(active), dd)
        if not can:
            break
        active.append(sig)
        added += 1
        print(
            f"  NEW: {sig['symbol']} {sig['signal_type']} via {sig['strategy']} "
            f"| funding={sig.get('funding_rate', 0):.4%} P{sig.get('funding_percentile', 50):.0f} "
            f"| conf={sig.get('confidence', 0):.2f} | R:R={sig.get('risk_reward', 0):.1f} "
            f"| TP={sig.get('take_profit', 0):.6g} SL={sig.get('stop_loss', 0):.6g}"
        )

        # Send Discord alert for qualifying picks
        if sig.get("confidence", 0) >= 0.60:
            try:
                send_pick_alert(SYSTEM_LABEL, sig)
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # 6. Save and report
    # -------------------------------------------------------------------------
    save_picks(active, newly_closed, DATA_DIR)
    _write_dashboard_data(active, closed, stats, funding_heatmap)

    # System D is rule-based (no ML model), so DSR validation is N/A
    # Mark as False until forward-test returns accumulate enough data
    _dsr_validated = False

    # Write scan summary for debugging
    scan_summary = {
        "timestamp": now.isoformat(),
        "market_health": health.value,
        "fear_greed": fear_greed,
        "active_count": len(active),
        "closed_count": len(closed),
        "new_picks": added,
        "newly_closed": len(newly_closed),
        "win_rate": stats.get("win_rate", 0),
        "sharpe": stats.get("sharpe", 0),
        "drawdown": round(dd, 4),
        "funding_heatmap": funding_heatmap,
        "dsr_validated": _dsr_validated,
    }
    with open(os.path.join(DATA_DIR, "scan_summary.json"), "w") as f:
        json.dump(scan_summary, f, indent=2)

    print(f"\n  Active: {len(active)} | Closed: {len(closed)} | New: {added}")
    print(f"  Stats: WR={stats.get('win_rate', 0):.1%} Sharpe={stats.get('sharpe', 0):.2f} DD={dd:.1%}")
    print(f"  Funding heatmap: {sum(1 for v in funding_heatmap.values() if v.get('signal'))} pairs with signals")

    # Send Discord status
    _send_status(active, closed, stats)

    print(f"[System D - The Carry Trade] Scan complete.")


def _send_status(
    active: list[dict],
    closed: list[dict],
    stats: dict,
):
    """Send Discord system status notification."""
    try:
        gate = passes_validation_gate(closed)
        send_system_status(
            system_name=SYSTEM_NAME,
            system_label=SYSTEM_LABEL,
            version=VERSION,
            active_picks=active,
            closed_picks=closed,
            stats=stats,
            validation_gate=gate,
        )
    except Exception as e:
        print(f"  [WARN] Discord notification failed: {e}")


def _write_dashboard_data(
    active: list[dict],
    closed: list[dict],
    stats: dict,
    funding_heatmap: dict,
):
    """Write JSON data for dashboard consumption."""
    os.makedirs(DATA_DIR, exist_ok=True)

    # Strategy inception registry
    STRATEGY_INCEPTION = {
        "funding_rate_carry": {
            "inception": "2026-02-24T23:00:00Z",
            "last_code_update": "2026-02-24T23:00:00Z",
        },
    }

    # Per-strategy stats
    strategy_stats = {}
    if closed:
        for pick in closed:
            strat = pick.get("strategy", "unknown")
            if strat not in strategy_stats:
                meta = STRATEGY_INCEPTION.get(strat, {})
                strategy_stats[strat] = {
                    "trades": 0,
                    "wins": 0,
                    "total_pnl": 0.0,
                    "inception": meta.get("inception"),
                    "last_code_update": meta.get("last_code_update"),
                }
            strategy_stats[strat]["trades"] += 1
            pnl = pick.get("net_pnl_pct", 0)
            strategy_stats[strat]["total_pnl"] += pnl
            if pnl > 0:
                strategy_stats[strat]["wins"] += 1
        for s in strategy_stats.values():
            s["win_rate"] = round(s["wins"] / s["trades"] * 100, 1) if s["trades"] else 0
            s["total_pnl"] = round(s["total_pnl"], 4)

    # Enrich closed trades with strategy inception metadata
    for trade in closed:
        strat = trade.get("strategy", "")
        if strat in STRATEGY_INCEPTION:
            trade["strategy_inception"] = STRATEGY_INCEPTION[strat]["inception"]
            trade["strategy_last_code_update"] = STRATEGY_INCEPTION[strat]["last_code_update"]

    dashboard_data = {
        "system": SYSTEM_LABEL,
        "system_name": SYSTEM_NAME,
        "version": VERSION,
        "scan_frequency": SCAN_FREQUENCY,
        "inception_date": "2026-02-24T23:00:00Z",
        "last_code_update": "2026-02-24T23:00:00Z",
        "updated": datetime.now(timezone.utc).isoformat(),
        "updated_est": datetime.now(EST).strftime("%Y-%m-%d %I:%M %p EST"),
        "active_picks": active,
        "stats": {k: v for k, v in stats.items() if k != "equity_curve"},
        "equity_curve": stats.get("equity_curve", []),
        "total_closed": len(closed),
        "recent_closed": closed[-20:] if closed else [],
        "strategy_stats": strategy_stats,
        "funding_heatmap": funding_heatmap,
    }

    dashboard_path = os.path.join(DATA_DIR, "dashboard.json")
    with open(dashboard_path, "w") as f:
        json.dump(dashboard_data, f, indent=2, default=str)


if __name__ == "__main__":
    scan()
