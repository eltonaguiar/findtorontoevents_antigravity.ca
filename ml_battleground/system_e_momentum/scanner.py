"""
System E Scanner: "The Momentum"
Cross-sectional momentum: rank all pairs by 7d/30d return, buy top 3, sell bottom 3.
Research: Liu et al. 2022 JFE, documented Sharpe ~2.1 for crypto cross-sectional momentum.
Run: python -m ml_battleground.system_e_momentum.scanner
"""
import os
import sys
import json
import time
import numpy as np
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.data_fetcher import fetch_ohlcv, fetch_fear_greed, fetch_funding_rates, PAIRS
from shared.indicators import atr, rsi, ema, sma, rate_of_change
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
SYSTEM_NAME = "system_e_momentum"
SYSTEM_LABEL = "The Momentum"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MIN_RR = 1.5
MIN_CONFIDENCE = 0.42  # lowered from 0.52 — System E never generated a single pick in 13 days
SCAN_FREQUENCY = "Every 30 minutes"
TOP_N = 3   # buy top 3
BOTTOM_N = 3  # sell bottom 3
EST = timezone(timedelta(hours=-5))
SCAN_STATE_PATH = os.path.join(DATA_DIR, "last_scan_state.json")


def rank_momentum(data: dict) -> list[dict]:
    """Rank all pairs by 7d and 30d momentum. Returns sorted list."""
    rankings = []
    for pair, df in data.items():
        if len(df) < 180:  # need ~30 days of 4h data (180 bars)
            continue
        close = df["Close"]
        # 7-day return (42 bars of 4h data)
        ret_7d = (float(close.iloc[-1]) / float(close.iloc[-42]) - 1) * 100 if len(close) >= 42 else 0
        # 30-day return (180 bars of 4h data)
        ret_30d = (float(close.iloc[-1]) / float(close.iloc[-180]) - 1) * 100 if len(close) >= 180 else 0
        rankings.append({
            "pair": pair,
            "ret_7d": round(ret_7d, 2),
            "ret_30d": round(ret_30d, 2),
            "last_close": float(close.iloc[-1]),
        })
    # Sort by 7d return (primary), 30d return (tiebreak)
    rankings.sort(key=lambda x: (x["ret_7d"], x["ret_30d"]), reverse=True)
    return rankings


def _compute_confidence(ret_7d: float, ret_30d: float, signal_type: str,
                        ema20_val: float, ema50_val: float, vol_ratio: float) -> float:
    """Calculate signal confidence based on momentum factors."""
    confidence = 0.50  # base

    # Momentum strength
    abs_ret = abs(ret_7d)
    if abs_ret > 10:
        confidence += 0.15
    elif abs_ret > 5:
        confidence += 0.10
    elif abs_ret > 3:
        confidence += 0.05

    # 30d trend alignment
    if (signal_type == "BUY" and ret_30d > 5) or (signal_type == "SELL" and ret_30d < -5):
        confidence += 0.10

    # EMA alignment (EMA20 vs EMA50)
    if (signal_type == "BUY" and ema20_val > ema50_val) or (signal_type == "SELL" and ema20_val < ema50_val):
        confidence += 0.05

    # Volume surge bonus
    if vol_ratio > 1.5:
        confidence += 0.05

    return round(min(confidence, 0.99), 4)


def _generate_signals(rankings: list[dict], data: dict, active_symbols: set,
                       fear_greed: int, funding_rates: dict, fg_direction: str | None,
                       health: MarketHealth) -> list[dict]:
    """Generate BUY signals from top momentum, SELL from bottom momentum."""
    now = datetime.now(timezone.utc)
    signals = []

    # Top N for BUY — in bear markets (F&G<25), lower thresholds significantly
    # Cross-sectional momentum profits from RELATIVE performance, not absolute
    if fear_greed < 25:
        buy_candidates = [r for r in rankings if r["ret_7d"] > 0][:TOP_N * 3]
        sell_candidates = [r for r in reversed(rankings) if r["ret_7d"] < -3][:BOTTOM_N * 3]
    else:
        buy_candidates = [r for r in rankings if r["ret_7d"] > 3 and r["ret_30d"] > 0][:TOP_N * 3]
        sell_candidates = [r for r in reversed(rankings) if r["ret_7d"] < -3 and r["ret_30d"] < 0][:BOTTOM_N * 3]

    candidates = [(c, "BUY") for c in buy_candidates] + [(c, "SELL") for c in sell_candidates]

    buy_count = 0
    sell_count = 0

    for rank_entry, signal_type in candidates:
        pair = rank_entry["pair"]

        # Limit to TOP_N buys and BOTTOM_N sells
        if signal_type == "BUY" and buy_count >= TOP_N:
            continue
        if signal_type == "SELL" and sell_count >= BOTTOM_N:
            continue

        if pair in active_symbols:
            continue

        df = data.get(pair)
        if df is None or len(df) < 180:
            continue

        ret_7d = rank_entry["ret_7d"]
        ret_30d = rank_entry["ret_30d"]
        close = df["Close"]
        entry_price = float(close.iloc[-1])

        # RSI filter: widen bands in extreme fear to allow more signals through
        rsi_vals = rsi(close)
        rsi_now = float(rsi_vals.iloc[-1]) if len(rsi_vals) > 0 and not np.isnan(rsi_vals.iloc[-1]) else 50.0
        if fear_greed < 25:
            # Bear market: wider RSI bands (oversold readings are normal, not disqualifying)
            buy_rsi_range = (25, 75)
            sell_rsi_range = (15, 65)
        else:
            buy_rsi_range = (40, 75)
            sell_rsi_range = (25, 60)
        if signal_type == "BUY" and not (buy_rsi_range[0] <= rsi_now <= buy_rsi_range[1]):
            print(f"    [filtered] {pair}: RSI {rsi_now:.1f} outside BUY range {buy_rsi_range}")
            continue
        if signal_type == "SELL" and not (sell_rsi_range[0] <= rsi_now <= sell_rsi_range[1]):
            print(f"    [filtered] {pair}: RSI {rsi_now:.1f} outside SELL range {sell_rsi_range}")
            continue

        # Volume filter: > 0.8x average
        vol_col = "Volume" if "Volume" in df.columns else "volume"
        volumes = df[vol_col].values
        avg_vol = float(np.mean(volumes[-42:])) if len(volumes) >= 42 else float(np.mean(volumes))
        current_vol = float(volumes[-1])
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 0
        if vol_ratio < 0.3:  # lowered from 0.8 — weekend/low-activity was filtering everything
            print(f"    [filtered] {pair}: volume ratio {vol_ratio:.2f} < 0.3")
            continue

        # EMA trend filter: BUY needs EMA20 > EMA50, SELL needs EMA20 < EMA50
        ema20_series = ema(close, 20)
        ema50_series = ema(close, 50)
        ema20_val = float(ema20_series.iloc[-1]) if len(ema20_series) > 0 else entry_price
        ema50_val = float(ema50_series.iloc[-1]) if len(ema50_series) > 0 else entry_price
        if signal_type == "BUY" and ema20_val < ema50_val:
            print(f"    [filtered] {pair}: EMA20 < EMA50 (downtrend, need uptrend for BUY)")
            continue
        if signal_type == "SELL" and ema20_val > ema50_val:
            print(f"    [filtered] {pair}: EMA20 > EMA50 (uptrend, need downtrend for SELL)")
            continue

        # F&G directional filter — SKIP for cross-sectional momentum
        # Cross-sectional momentum is market-neutral (long winners + short losers)
        # so both directions are valid regardless of F&G sentiment
        # Only apply F&G filter for directional systems (not this one)

        # PANIC mode: respect F&G contrarian direction (Feb 26 2026 fix)
        # OLD CODE blocked ALL BUYs in PANIC — contradicted F&G contrarian logic
        # that says "BUY in extreme fear". Now: if F&G says BUY, allow it in PANIC.
        # Only block BUYs in PANIC when F&G is NOT in extreme fear zone.
        if health == MarketHealth.PANIC and signal_type == "BUY":
            if fg_direction != "BUY":
                print(f"    [filtered] {pair}: BUY blocked in PANIC mode (F&G not extreme fear)")
                continue
            else:
                print(f"    [pass] {pair}: BUY allowed in PANIC (extreme fear contrarian)")

        # ATR-based TP/SL: TP = 3x ATR, SL = 1.5x ATR (momentum needs wider TP)
        atr_vals = atr(df["High"], df["Low"], df["Close"])
        atr_now = float(atr_vals.iloc[-1]) if len(atr_vals) > 0 and not np.isnan(atr_vals.iloc[-1]) else entry_price * 0.02

        # ATR percentile filter (Wilder 1978)
        if not atr_percentile_filter(atr_vals.values):
            print(f"    [filtered] {pair}: ATR outside 40-95th percentile")
            continue

        # Volume confirmation gate (microstructure)
        vol_ok, vol_ratio_check = volume_confirmation(df[vol_col].values)
        if not vol_ok:
            print(f"    [filtered] {pair}: volume confirmation failed (ratio {vol_ratio_check:.2f})")
            continue

        if signal_type == "BUY":
            tp = entry_price + 3.0 * atr_now
            sl = entry_price - 1.5 * atr_now
        else:
            tp = entry_price - 3.0 * atr_now
            sl = entry_price + 1.5 * atr_now

        # R:R calculation
        risk = abs(entry_price - sl)
        reward = abs(tp - entry_price)
        rr = reward / risk if risk > 0 else 0

        if rr < MIN_RR:
            print(f"    [filtered] {pair}: R:R {rr:.2f} < {MIN_RR}")
            continue

        # --- Dynamic SL widening during volatility spikes ---
        if len(df) >= 60:
            high_col = "High" if "High" in df.columns else "high"
            low_col = "Low" if "Low" in df.columns else "low"
            ranges = (df[high_col] - df[low_col]).values[-60:]
            current_range = float(ranges[-1])
            median_range = float(np.median(ranges[:-1]))
            if median_range > 0 and current_range / median_range > 2.0:
                old_sl = sl
                sl_dist = abs(entry_price - sl)
                if signal_type == "BUY":
                    sl = entry_price - sl_dist * 1.5
                else:
                    sl = entry_price + sl_dist * 1.5
                # Recalculate R:R with widened SL
                risk = abs(entry_price - sl)
                reward = abs(tp - entry_price)
                rr = round(reward / risk, 2) if risk > 0 else 0
                print(f"    [volatility] Widening SL for {pair}: {old_sl:.4g} -> {sl:.4g}")

        # Dynamic SL widening based on market health
        health_sl_mult = dynamic_sl_multiplier(health, base_mult=1.0)
        if health_sl_mult > 1.0:
            old_sl = sl
            sl_dist = abs(entry_price - sl)
            if signal_type == "BUY":
                sl = entry_price - sl_dist * health_sl_mult
            else:
                sl = entry_price + sl_dist * health_sl_mult
            risk = abs(entry_price - sl)
            reward = abs(tp - entry_price)
            rr = round(reward / risk, 2) if risk > 0 else 0
            print(f"    [health={health.value}] Widening SL for {pair}: {old_sl:.4g} -> {sl:.4g} ({health_sl_mult:.1f}x)")

        # Confidence calculation
        confidence = _compute_confidence(ret_7d, ret_30d, signal_type, ema20_val, ema50_val, vol_ratio)
        if confidence < MIN_CONFIDENCE:
            print(f"    [filtered] {pair}: confidence {confidence:.3f} < {MIN_CONFIDENCE}")
            continue

        # --- Expected return pre-filter (Kimi/Lopez de Prado) ---
        cost = round_trip_cost(pair)
        tp_dist = abs(tp - entry_price) / entry_price
        sl_dist_pct = abs(entry_price - sl) / entry_price
        expected_return = confidence * tp_dist - (1 - confidence) * sl_dist_pct - cost
        min_expected = max(cost * 3, 0.003)
        if expected_return < min_expected:
            print(f"    [filtered] {pair}: E[R]={expected_return:.4f} < min {min_expected:.4f} "
                  f"(3x cost rule, conf={confidence:.3f}, TP%={tp_dist:.4f}, SL%={sl_dist_pct:.4f}, cost={cost:.4f})")
            continue

        # Adaptive threshold: cost-aware breakeven (Kissell 2020)
        min_conf = adaptive_threshold(tp_dist, sl_dist_pct, cost)
        if confidence < max(min_conf, MIN_CONFIDENCE):
            print(f"    [filtered] {pair}: confidence {confidence:.3f} < threshold {max(min_conf, MIN_CONFIDENCE):.3f}")
            continue

        # Calculate unrealized P&L
        current_price = entry_price
        if signal_type == "BUY":
            unrealized_pnl = round((current_price - entry_price) / entry_price * 100, 4)
        else:
            unrealized_pnl = round((entry_price - current_price) / entry_price * 100, 4)

        # Momentum rank position
        rank_pos = next((i for i, r in enumerate(rankings) if r["pair"] == pair), -1) + 1

        # Capture feature snapshot at entry time (Design 3E)
        _entry_features = {
            "close": entry_price,
            "ret_7d": ret_7d,
            "ret_30d": ret_30d,
            "rsi_14": rsi_now,
            "ema20": ema20_val,
            "ema50": ema50_val,
            "vol_ratio": vol_ratio,
            "atr_14": float(atr_vals.iloc[-1]) if len(atr_vals) > 0 else 0.0,
            "momentum_rank": rank_pos,
            "fear_greed": fear_greed,
            "funding_rate": funding_rates.get(pair, 0.0),
            "confidence": confidence,
        }

        sig = {
            "symbol": pair,
            "signal_type": signal_type,
            "strategy": "cross_sectional_momentum",
            "entry_price": round(entry_price, 8),
            "take_profit": round(tp, 8),
            "stop_loss": round(sl, 8),
            "risk_reward": round(rr, 2),
            "confidence": confidence,
            "features": snapshot_from_dict(_entry_features),
            "market_health": health.value,
            "timestamp": now.isoformat(),
            "system": SYSTEM_NAME,
            "version": VERSION,
            "timeframe": "4h",
            "fear_greed": fear_greed,
            "funding_rate": funding_rates.get(pair, 0.0),
            "timestamp_est": now.astimezone(EST).strftime("%Y-%m-%d %I:%M %p EST"),
            "current_price": current_price,
            "unrealized_pnl_pct": unrealized_pnl,
            "momentum_rank": rank_pos,
            "ret_7d": ret_7d,
            "ret_30d": ret_30d,
            "rsi": round(rsi_now, 2),
            "vol_ratio": round(vol_ratio, 2),
            "ema20": round(ema20_val, 8),
            "ema50": round(ema50_val, 8),
            "pick_reason": (
                f"Cross-sectional momentum ({signal_type}) on 4h "
                f"| 7d return {ret_7d:+.1f}%, 30d return {ret_30d:+.1f}% "
                f"| Rank #{rank_pos}/{len(rankings)} "
                f"| RSI {rsi_now:.1f} | Vol {vol_ratio:.1f}x "
                f"| R:R {rr:.1f} | TP/SL via ATR "
                f"| F&G={fear_greed} | Funding={funding_rates.get(pair, 0.0):.4f}"
            ),
        }

        signals.append(sig)
        active_symbols.add(pair)

        if signal_type == "BUY":
            buy_count += 1
        else:
            sell_count += 1

    return signals


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
    """Main scan cycle."""
    now = datetime.now(timezone.utc)
    print(f"[System E] Scan started at {now.isoformat()}")

    # Ensure data directory exists before any file operations
    os.makedirs(DATA_DIR, exist_ok=True)

    # Check for revision reset (archives pre-revision data, resets tracking)
    from pathlib import Path
    check_revision(SYSTEM_NAME, Path(DATA_DIR))

    # Load existing state
    active = load_active(DATA_DIR)
    closed = load_closed(DATA_DIR)

    # Validate existing picks first
    active, newly_closed = validate_picks(active, SYSTEM_NAME, DATA_DIR)
    closed.extend(newly_closed)
    if newly_closed:
        print(f"  Closed {len(newly_closed)} picks: {[p['symbol'] for p in newly_closed]}")

    # Check if we can open new trades
    stats = compute_stats(closed)
    equity_curve = stats.get("equity_curve", [10000.0])
    dd = calculate_drawdown(equity_curve)
    can_trade, reason = can_open_trade(len(active), dd)

    if not can_trade:
        print(f"  Cannot open new trades: {reason}")
        save_picks(active, newly_closed, DATA_DIR)
        _write_dashboard_data(active, closed, stats, [])
        return

    # Drawdown halt gate (8% DD = stop trading until recovery)
    ok_to_trade, halt_reason = should_trade(equity_curve)
    if not ok_to_trade:
        print(f"  {halt_reason}")
        save_picks(active, newly_closed, DATA_DIR)
        _write_dashboard_data(active, closed, stats, [])
        return

    # Fetch market context
    fear_greed = fetch_fear_greed()
    funding_rates_data = fetch_funding_rates()

    # --- Market Health Gate ---
    btc_health_data = fetch_ohlcv(["BTCUSDT"], "1h", 300)
    btc_df_health = btc_health_data.get("BTCUSDT")

    # --- Candle-Close Gate: skip scan if no new 1h candle has closed ---
    if not _check_candle_gate(btc_df_health):
        print(f"  Skipping scan: no new 1h candle closed since last scan")
        save_picks(active, newly_closed, DATA_DIR)
        _write_dashboard_data(active, closed, stats, [])
        print(f"[System E] Scan complete (no new candle).")
        return

    health, health_details = check_market_health(fear_greed, btc_df_health, funding_rates_data)
    print(f"  Market Health: {health.value} | F&G={fear_greed}, BTC trend={health_details.get('btc_trend', '?')}, "
          f"BTC 24h={health_details.get('btc_24h_change', '?')}%, volatility={health_details.get('volatility', '?')}")

    # BTC trend context (for logging/awareness)
    if btc_df_health is not None and len(btc_df_health) >= 200:
        btc_close = btc_df_health["Close"].values
        btc_sma50 = float(np.mean(btc_close[-50:]))
        btc_sma200 = float(np.mean(btc_close[-200:]))
        btc_now = float(btc_close[-1])
        if btc_now > btc_sma50 and btc_now > btc_sma200:
            btc_trend = "BULLISH"
        elif btc_now < btc_sma200:
            btc_trend = "BEARISH"
        else:
            btc_trend = "NEUTRAL"
        print(f"  BTC trend: {btc_trend} (${btc_now:.0f} | SMA50=${btc_sma50:.0f} | SMA200=${btc_sma200:.0f})")

    # PANIC mode: still scan for SELL signals (profit from crash) but skip BUYs
    if health == MarketHealth.PANIC:
        print(f"  *** PANIC MODE: scanning for SELL-only opportunities ***")

    # --- Fear & Greed Contrarian Bias (research-backed) ---
    fg_direction = None
    if fear_greed <= 15:
        fg_direction = "BUY"
        print(f"  Fear & Greed CONTRARIAN bias: BUY only (F&G={fear_greed} <= 15, extreme fear = buy opportunity)")
    elif fear_greed > 80:
        fg_direction = "SELL"
        print(f"  Fear & Greed CONTRARIAN bias: SELL only (F&G={fear_greed} > 80, extreme greed = sell opportunity)")
    else:
        print(f"  Fear & Greed: {fear_greed} (no directional filter)")

    # --- External Signal Confluence (Deribit + Binance Contrarian) ---
    ext_signals = fetch_external_signals()
    log_external_signals_summary(ext_signals)

    # --- Fetch 4h OHLCV for all pairs (need 180+ bars for 30d momentum) ---
    data = fetch_ohlcv(PAIRS, "4h", 500)
    print(f"  [4h] Fetched data for {len(data)} pairs")
    for p, d in data.items():
        print(f"    {p}: {len(d)} bars")

    # --- Rank all pairs by momentum ---
    rankings = rank_momentum(data)
    print(f"  Momentum rankings ({len(rankings)} pairs):")
    for i, r in enumerate(rankings):
        tag = ""
        if i < TOP_N:
            tag = " [TOP]"
        elif i >= len(rankings) - BOTTOM_N:
            tag = " [BOTTOM]"
        print(f"    #{i+1} {r['pair']}: 7d={r['ret_7d']:+.1f}%, 30d={r['ret_30d']:+.1f}%{tag}")

    # --- Generate signals from top/bottom momentum ---
    active_symbols = {p["symbol"] for p in active}
    new_signals = _generate_signals(
        rankings, data, active_symbols,
        fear_greed, funding_rates_data, fg_direction, health,
    )

    # --- Meta-Labeler Quality Gate (Lopez de Prado M2) ---
    if new_signals:
        new_signals = meta_label_filter(new_signals, closed, SYSTEM_NAME)

    # --- External Signal Confluence (Deribit + Binance Contrarian) ---
    if new_signals:
        new_signals = apply_external_confluence_batch(new_signals, ext_signals)

    # Apply market health gate to filter/adjust signals
    raw_count = len(new_signals)
    new_signals = apply_health_gate(health, new_signals)
    if raw_count > 0 and len(new_signals) < raw_count:
        print(f"  Health gate ({health.value}): {raw_count} -> {len(new_signals)} signals")

    # Deduplicate: keep best signal per symbol
    new_signals.sort(key=lambda s: s.get("confidence", 0), reverse=True)
    seen_syms = set(active_symbols)
    deduped = []
    for sig in new_signals:
        if sig["symbol"] not in seen_syms:
            deduped.append(sig)
            seen_syms.add(sig["symbol"])
    if len(deduped) < len(new_signals):
        print(f"  Dedup: {len(new_signals)} -> {len(deduped)} signals (removed duplicate symbols)")
    new_signals = deduped

    # --- Strategy Health Gate: disable consistently losing strategies ---
    new_signals = filter_signals_by_health(new_signals, closed)

    # --- Cross-System Symbol Lock: prevent conflicting positions ---
    new_signals = filter_signals_by_lock(new_signals, SYSTEM_NAME)

    added = 0
    for sig in new_signals:
        can, reason = can_open_trade(len(active), dd)
        if not can:
            break
        active.append(sig)
        added += 1
        print(f"  NEW: {sig['symbol']} {sig['signal_type']} "
              f"(rank #{sig['momentum_rank']}, 7d={sig['ret_7d']:+.1f}%, "
              f"conf:{sig['confidence']:.2f}, R:R:{sig['risk_reward']:.1f})")

    print(f"  Active: {len(active)} | Closed: {len(closed)} | New: {added}")
    print(f"  Stats: WR={stats.get('win_rate', 0):.1%} Sharpe={stats.get('sharpe', 0):.2f} DD={dd:.1%}")

    # Save everything
    save_picks(active, newly_closed, DATA_DIR)
    _write_dashboard_data(active, closed, stats, rankings)

    # System E is rule-based (no ML model), so DSR validation is N/A
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
        "momentum_rankings": rankings,
        "dsr_validated": _dsr_validated,
    }
    with open(os.path.join(DATA_DIR, "scan_summary.json"), "w") as f:
        json.dump(scan_summary, f, indent=2)

    # Send Discord notifications
    gate = passes_validation_gate(closed)

    # Notify exits
    for closed_pick in newly_closed:
        send_pick_exit(SYSTEM_LABEL, closed_pick)

    # Notify new picks
    for sig in active[-added:] if added > 0 else []:
        if sig.get("confidence", 0) >= 0.65:
            send_pick_alert(SYSTEM_LABEL, sig)

    # Hourly status
    send_system_status(
        system_name=SYSTEM_NAME,
        system_label=SYSTEM_LABEL,
        version=VERSION,
        active_picks=active,
        closed_picks=closed,
        stats=stats,
        validation_gate=gate,
    )

    print(f"[System E] Scan complete.")


def _write_dashboard_data(active: list, closed: list, stats: dict, rankings: list):
    """Write JSON data for dashboard consumption."""
    # Strategy inception registry
    STRATEGY_INCEPTION = {
        "cross_sectional_momentum": {
            "inception": "2026-02-24T23:00:00Z",
            "last_code_update": "2026-02-24T23:00:00Z",
        },
    }

    # Enrich closed trades with strategy inception metadata
    for trade in closed:
        strat = trade.get("strategy", "")
        if strat in STRATEGY_INCEPTION:
            trade["strategy_inception"] = STRATEGY_INCEPTION[strat]["inception"]
            trade["strategy_last_code_update"] = STRATEGY_INCEPTION[strat]["last_code_update"]

    # Build strategy breakdown with inception dates
    strategy_breakdown = {}
    for trade in closed:
        strat = trade.get("strategy", "unknown")
        if strat not in strategy_breakdown:
            meta = STRATEGY_INCEPTION.get(strat, {})
            strategy_breakdown[strat] = {
                "trades": 0, "wins": 0, "total_pnl": 0.0,
                "inception": meta.get("inception"),
                "last_code_update": meta.get("last_code_update"),
            }
        entry = strategy_breakdown[strat]
        entry["trades"] += 1
        pnl = trade.get("net_pnl_pct", 0)
        entry["total_pnl"] += pnl
        if pnl > 0:
            entry["wins"] += 1
    for s in strategy_breakdown.values():
        s["win_rate"] = round(s["wins"] / s["trades"] * 100, 1) if s["trades"] else 0
        s["total_pnl"] = round(s["total_pnl"], 4)

    dashboard_data = {
        "system": SYSTEM_LABEL,
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
        "strategy_breakdown": strategy_breakdown,
        "momentum_rankings": rankings,
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "dashboard.json"), "w") as f:
        json.dump(dashboard_data, f, indent=2, default=str)


if __name__ == "__main__":
    scan()
