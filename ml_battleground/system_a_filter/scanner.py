"""
System A Scanner: "The Filter"
Proven strategies -> ML filter -> S/R-based TP/SL
Run: python -m ml_battleground.system_a_filter.scanner
"""
import os
import sys
import json
import time
import numpy as np
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.data_fetcher import fetch_ohlcv, fetch_fear_greed, fetch_funding_rates, fetch_fear_greed_history, fear_greed_persistence, PAIRS
from shared.indicators import atr, rsi
from shared.sr_engine import detect_sr_levels, sr_based_tp_sl
from shared.risk_manager import can_open_trade, calculate_drawdown, position_size, should_trade
from shared.cost_model import round_trip_cost
from shared.validator import validate_picks, save_picks, load_active, load_closed
from shared.performance import compute_stats
from shared.discord_notify import send_system_status, send_pick_alert, send_pick_exit
from shared.validator import passes_validation_gate
from shared.market_health import check_market_health, apply_health_gate, MarketHealth, dynamic_sl_multiplier
from shared.trade_filters import adaptive_threshold, atr_percentile_filter, volume_confirmation, reversal_confirmation
from shared.strategy_health import filter_signals_by_health
from shared.symbol_lock import filter_signals_by_lock
from shared.revision_marker import check_revision
from shared.meta_labeler import filter_signals_batch as meta_label_filter
from shared.external_signals import fetch_external_signals, apply_external_confluence_batch, log_external_signals_summary
from system_a_filter.strategies import run_all_strategies
from system_a_filter.proven_aggressive_variants import run_all_aggressive_variants
from system_a_filter.ml_filter import compute_filter_features, predict

SYSTEM_NAME = "system_a_filter"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FILTER_THRESHOLD = 0.65  # minimum ML score to take a signal (raised from 0.55)
VERSION = "1.0.0"
EST = timezone(timedelta(hours=-5))
SCAN_FREQUENCY = "Every 30 minutes"
SCAN_STATE_PATH = os.path.join(DATA_DIR, "last_scan_state.json")


def _adx_regime_fallback() -> str:
    """Simple ADX-based regime detection as fallback when System B is untrusted.

    Uses BTC 4h data with ADX(14):
      - ADX > 25 + DI+ > DI-  -> trending_up
      - ADX > 25 + DI- > DI+  -> trending_down
      - ADX <= 25              -> range_bound

    Returns regime string compatible with System B's format.
    """
    try:
        from shared.data_fetcher import fetch_single
        df = fetch_single("BTCUSDT", "4h", 100)
        if df is None or len(df) < 30:
            return "range_bound"

        high = df["High"].values
        low = df["Low"].values
        close = df["Close"].values
        n = len(df)

        # Calculate ADX(14) manually
        period = 14
        tr_arr = np.zeros(n)
        plus_dm = np.zeros(n)
        minus_dm = np.zeros(n)

        for i in range(1, n):
            h_diff = high[i] - high[i - 1]
            l_diff = low[i - 1] - low[i]
            tr_arr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
            plus_dm[i] = h_diff if h_diff > l_diff and h_diff > 0 else 0
            minus_dm[i] = l_diff if l_diff > h_diff and l_diff > 0 else 0

        # Smoothed averages (Wilder's smoothing)
        atr_val = np.mean(tr_arr[1:period + 1])
        plus_di_sum = np.mean(plus_dm[1:period + 1])
        minus_di_sum = np.mean(minus_dm[1:period + 1])

        for i in range(period + 1, n):
            atr_val = (atr_val * (period - 1) + tr_arr[i]) / period
            plus_di_sum = (plus_di_sum * (period - 1) + plus_dm[i]) / period
            minus_di_sum = (minus_di_sum * (period - 1) + minus_dm[i]) / period

        plus_di = 100 * plus_di_sum / atr_val if atr_val > 0 else 0
        minus_di = 100 * minus_di_sum / atr_val if atr_val > 0 else 0
        dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) > 0 else 0
        # Use dx as proxy for ADX (single-pass approximation)
        adx = dx

        if adx > 25:
            return "trending_up" if plus_di > minus_di else "trending_down"
        return "range_bound"
    except Exception:
        return "range_bound"


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
    print(f"[System A] Scan started at {now.isoformat()}")

    # Check for revision reset (archives pre-revision data, resets tracking)
    from pathlib import Path
    check_revision(SYSTEM_NAME, Path(DATA_DIR))

    # Fetch market context early — needed for bounce detector in validator
    fear_greed = fetch_fear_greed()
    funding_rates = fetch_funding_rates()

    # Load existing state
    active = load_active(DATA_DIR)
    closed = load_closed(DATA_DIR)

    # Validate existing picks (with F&G for bounce-close of bleeding shorts)
    active, newly_closed = validate_picks(active, SYSTEM_NAME, DATA_DIR,
                                          fear_greed=fear_greed)
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
        _write_dashboard_data(active, closed, stats)
        return

    # Drawdown halt gate (8% DD = stop trading until recovery)
    ok_to_trade, halt_reason = should_trade(equity_curve)
    if not ok_to_trade:
        print(f"  {halt_reason}")
        save_picks(active, newly_closed, DATA_DIR)
        _write_dashboard_data(active, closed, stats)
        return

    # --- Market Health Gate ---
    btc_health_data = fetch_ohlcv(["BTCUSDT"], "1h", 300)
    btc_df_health = btc_health_data.get("BTCUSDT")

    # --- Candle-Close Gate: skip scan if no new 1h candle has closed ---
    if not _check_candle_gate(btc_df_health):
        print(f"  Skipping scan: no new 1h candle closed since last scan")
        save_picks(active, newly_closed, DATA_DIR)
        _write_dashboard_data(active, closed, stats)
        return

    health, health_details = check_market_health(fear_greed, btc_df_health, funding_rates)
    print(f"  Market Health: {health.value} | F&G={fear_greed}, BTC trend={health_details.get('btc_trend','?')}, "
          f"BTC 24h={health_details.get('btc_24h_change','?')}%, volatility={health_details.get('volatility','?')}")

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
    # apply_health_gate() handles the filtering — only high-confidence SELLs pass
    if health == MarketHealth.PANIC:
        print(f"  *** PANIC MODE: scanning for SELL-only opportunities ***")

    # --- F&G 3-Day Persistence (R008: Wong, Sharpe 1.3) ---
    fg_history = fetch_fear_greed_history(7)
    fg_persist = fear_greed_persistence(fg_history)
    if fg_persist["persistent"]:
        print(f"  F&G PERSISTENT: {fg_persist['direction']} ({fg_persist['fear_days']}d fear, {fg_persist['greed_days']}d greed)")

    # --- Fear & Greed Directional Filter (HARD BLOCK) ---
    # CRITICAL FIX: Old contrarian logic said "extreme fear = BUY opportunity" but
    # that lost money on 8/8 BUY trades during F&G=8. In practice, extreme fear means
    # the market is crashing and BUYs get stopped out immediately.
    #
    # New logic:
    #   F&G < 15:  SELL ONLY (market is crashing, don't catch falling knives)
    #   F&G 15-25: Allow both but with caution
    #   F&G 25-75: No filter (normal conditions)
    #   F&G 75-85: Allow both but with caution
    #   F&G > 85:  BUY ONLY (extreme greed = momentum, don't short parabolic moves)
    #
    # The contrarian "buy fear, sell greed" thesis is valid for MULTI-WEEK DCA,
    # not for intraday/4h swing trades with tight stops.
    fg_direction = None
    fg_confidence_boost = 0.0
    if fear_greed < 15:
        # P0 BOUNCE DETECTOR: F&G < 15 = capitulation bottom 70-80% of historical cases
        # Mercury 2 went 8/8 buying here. Don't force SELL at bottoms.
        fg_direction = None  # Allow both directions — let bounce detector in health gate decide
        print(f"  F&G BOUNCE ZONE: F&G={fear_greed} < 15, extreme capitulation — bounce detector active (no forced SELL)")
    elif fear_greed < 25:
        fg_direction = "SELL"
        print(f"  F&G HARD BLOCK: SELL only (F&G={fear_greed} < 25, extreme fear — no BUYs)")
    elif fear_greed > 85:
        fg_direction = "BUY"
        print(f"  F&G HARD BLOCK: BUY only (F&G={fear_greed} > 85, parabolic greed — no SHORTs)")
    elif fg_persist["persistent"] and fg_persist["direction"] == "SELL" and fear_greed <= 35:
        fg_direction = "SELL"
        fg_confidence_boost = 0.10
        print(f"  F&G PERSISTENT FEAR: SELL only ({fg_persist['fear_days']}d consecutive fear, F&G={fear_greed})")
    elif fg_persist["persistent"] and fg_persist["direction"] == "BUY" and fear_greed >= 75:
        fg_direction = "BUY"
        fg_confidence_boost = 0.10
        print(f"  F&G PERSISTENT GREED: BUY only ({fg_persist['greed_days']}d consecutive greed, F&G={fear_greed})")
    else:
        print(f"  F&G: {fear_greed} (no directional filter)")

    # --- Regime Filter from System B (with confidence gate) ---
    # Only take BUY signals when regime != trending_down
    # Only take SELL signals when regime != trending_up
    # BUT: if System B WR < 40% on last 20 trades, ignore its regime calls
    # and fall back to ADX-based regime detection instead.
    system_b_regime = None
    system_b_summary_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "system_b_regime", "data", "scan_summary.json"
    )
    system_b_closed_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "system_b_regime", "data", "closed_picks.json"
    )
    system_b_trusted = True  # assume trusted until proven otherwise
    try:
        # Check System B's recent WR to decide if we trust its regime calls
        if os.path.exists(system_b_closed_path):
            with open(system_b_closed_path) as f:
                b_closed = json.load(f)
            if len(b_closed) >= 10:
                recent_b = b_closed[-20:] if len(b_closed) >= 20 else b_closed
                b_wins = sum(1 for t in recent_b if t.get("net_pnl_pct", 0) > 0)
                b_wr = b_wins / len(recent_b)
                if b_wr < 0.40:
                    system_b_trusted = False
                    print(f"  System B regime IGNORED: WR={b_wr:.1%} on last {len(recent_b)} trades (<40% gate)")

        if system_b_trusted and os.path.exists(system_b_summary_path):
            with open(system_b_summary_path) as f:
                b_summary = json.load(f)
            system_b_regime = b_summary.get("dominant_regime")
            print(f"  System B regime filter: {system_b_regime}")
        elif not system_b_trusted:
            # Fallback: simple ADX-based regime detection from BTC data
            system_b_regime = _adx_regime_fallback()
            print(f"  ADX fallback regime: {system_b_regime}")
    except Exception as e:
        print(f"  [WARN] Could not load System B regime: {e}")

    # --- External Signal Confluence (Deribit + Binance Contrarian) ---
    # Fetch once per scan cycle; used later to boost/penalize pick confidence
    ext_signals = fetch_external_signals()
    log_external_signals_summary(ext_signals)

    # Fetch OHLCV — Primary: 4h (best signal-to-noise), Secondary: 1h
    # 15m removed — too noisy for crypto, destroys profitability via transaction costs
    new_signals = []
    active_symbols = {p["symbol"] for p in active}

    for interval in ["4h", "1h"]:
        limit = 500
        data = fetch_ohlcv(PAIRS, interval, limit)

        print(f"  [{interval}] Fetched data for {len(data)} pairs")
        for p, d in data.items():
            print(f"    {p}: {len(d)} bars")

        for pair, df in data.items():
            if pair in active_symbols:
                print(f"  [skip] {pair}: already active")
                continue
            if len(df) < 50:
                print(f"  [skip] {pair}: only {len(df)} bars (need 50)")
                continue

            # Run 12 strategies + 6 aggressive variants from proven winners
            signals = run_all_strategies(df, pair, interval=interval, funding_rate=funding_rates.get(pair, 0.0))
            agg_signals = run_all_aggressive_variants(df, pair, interval=interval)
            if agg_signals:
                print(f"    [AGG] {pair} ({interval}): {len(agg_signals)} aggressive variant signal(s)")
            signals.extend(agg_signals)
            if not signals:
                continue

            # Compute S/R levels
            sr_levels = detect_sr_levels(df)

            # ML filter each signal
            for sig in signals:
                sig["timeframe"] = interval
                features = compute_filter_features(
                    sig, sr_levels, df,
                    fear_greed=fear_greed,
                    funding_rate=funding_rates.get(pair, 0.0),
                )
                ml_score, method = predict(features)

                # --- Dynamic ML Threshold ---
                # During PANIC/WARNING, raise filter to block low-quality BUY signals.
                # But SELL signals use lower threshold — the ML model hasn't been
                # trained on SHORT patterns yet, so we rely more on strategy logic.
                # PANIC BUY: 0.85 (only highest-conviction), SELL: 0.55 (trust strategy)
                # WARNING: BUY 0.75, SELL 0.60
                # CAUTION/SAFE: normal 0.65
                sig_type_for_filter = sig.get("signal_type", "BUY")
                dynamic_filter = FILTER_THRESHOLD
                if health == MarketHealth.PANIC:
                    dynamic_filter = 0.55 if sig_type_for_filter == "SELL" else 0.70
                elif health == MarketHealth.WARNING:
                    dynamic_filter = 0.60 if sig_type_for_filter == "SELL" else 0.75
                print(f"    ML filter: {pair} {sig.get('strategy','?')} -> score={ml_score:.3f} ({method}), threshold={dynamic_filter} (health={health.value})")

                # F&G directional filter: skip signals against market direction
                # Exception: fear_capitulation_dca is DESIGNED for extreme fear — let it through
                # with reduced position size (tiered DCA, not all-in)
                strat_name = sig.get("strategy", "")
                if fg_direction and sig.get("signal_type", "BUY") != fg_direction:
                    if strat_name == "fear_capitulation_dca" and fg_direction == "SELL":
                        # Allow fear DCA through but mark as small tiered position
                        sig["position_scale"] = 0.25  # Only 25% position during extreme fear
                        sig["reason"] = sig.get("reason", "") + " [TIERED DCA: 25% position, F&G extreme]"
                        print(f"    [exempt] {pair} fear_capitulation_dca: BUY allowed through F&G filter (tiered 25%)")
                    else:
                        print(f"    [filtered] {pair} {strat_name}: {sig.get('signal_type','BUY')} blocked (F&G={fear_greed} -> {fg_direction} only)")
                        continue

                # Regime directional filter (from System B backtest results)
                sig_dir = sig.get("signal_type", "BUY")
                if system_b_regime == "trending_down" and sig_dir == "BUY":
                    print(f"    [filtered] {pair} {sig.get('strategy','?')}: BUY blocked (System B regime=trending_down)")
                    continue
                if system_b_regime == "trending_up" and sig_dir == "SELL":
                    print(f"    [filtered] {pair} {sig.get('strategy','?')}: SELL blocked (System B regime=trending_up)")
                    continue

                if ml_score < dynamic_filter:
                    print(f"    [filtered] {pair} {sig.get('strategy','?')}: ML score {ml_score:.3f} < {dynamic_filter}")
                    continue

                # --- Research-backed pre-trade filters ---
                atr_val = atr(df["High"], df["Low"], df["Close"])
                atr_now = float(atr_val.iloc[-1]) if len(atr_val) > 0 else sig["entry_price"] * 0.02

                # ATR percentile filter: only trade in goldilocks vol zone (Wilder 1978)
                # Exception: SELL signals during panic benefit from HIGH volatility
                # — shorts thrive in volatile downtrends, skip upper bound for SELL
                sig_dir = sig.get("signal_type", "BUY")
                if not atr_percentile_filter(atr_val.values):
                    if sig_dir == "SELL" and health == MarketHealth.PANIC:
                        print(f"    [exempt] {pair} {strat_name}: ATR filter bypassed for SELL in PANIC")
                    else:
                        print(f"    [filtered] {pair}: ATR outside 40-95th percentile")
                        continue

                # Volume confirmation gate (microstructure)
                # Exception: SELL during panic — low volume is normal post-selloff
                vol_col = "volume" if "volume" in df.columns else "Volume"
                vol_ok, vol_ratio = volume_confirmation(df[vol_col].values)
                if not vol_ok:
                    if sig_dir == "SELL" and health == MarketHealth.PANIC:
                        pass  # Allow SELL through low volume during panic
                    else:
                        print(f"    [filtered] {pair}: volume ratio {vol_ratio:.2f} < 0.7")
                        continue

                # Reversal confirmation: require price action to confirm direction (Elder 1993)
                # Bypass for SELL in PANIC: trend is strongly down, green candles = dead cat bounce
                sig_dir = sig.get("signal_type", "BUY")
                close_col = "close" if "close" in df.columns else "Close"
                high_col = "high" if "high" in df.columns else "High"
                low_col = "low" if "low" in df.columns else "Low"
                if sig_dir == "SELL" and health == MarketHealth.PANIC:
                    rev_ok, rev_reason = True, "bypassed_sell_panic"
                else:
                    rev_ok, rev_reason = reversal_confirmation(
                        df[close_col].values, df[high_col].values, df[low_col].values,
                        signal_type=sig_dir,
                    )
                if not rev_ok:
                    print(f"    [filtered] {pair}: reversal not confirmed ({rev_reason})")
                    continue

                # Set S/R-based TP/SL
                tp, sl, tp_sl_method = sr_based_tp_sl(
                    sig["entry_price"], sr_levels, atr_now,
                    signal_type=sig.get("signal_type", "BUY"),
                )

                # Calculate R:R
                entry = sig["entry_price"]
                if sig.get("signal_type", "BUY") == "BUY":
                    risk = entry - sl
                    reward = tp - entry
                else:
                    risk = sl - entry
                    reward = entry - tp

                rr = reward / risk if risk > 0 else 0

                # --- Dynamic SL widening during volatility spikes ---
                # Skip SL widening for SELL signals — shorts thrive on volatility
                if len(df) >= 60 and sig_dir != "SELL":
                    close_col = "close" if "close" in df.columns else "Close"
                    high_col = "high" if "high" in df.columns else "High"
                    low_col = "low" if "low" in df.columns else "Low"
                    ranges = (df[high_col] - df[low_col]).values[-60:]
                    current_range = float(ranges[-1])
                    median_range = float(np.median(ranges[:-1]))
                    if median_range > 0 and current_range / median_range > 2.0:
                        old_sl = sl
                        sl_dist = abs(entry - sl)
                        if sig.get("signal_type", "BUY") == "BUY":
                            sl = entry - sl_dist * 1.5
                        else:
                            sl = entry + sl_dist * 1.5
                        # Recalculate R:R with widened SL
                        tp_dist_new = abs(tp - entry)
                        new_sl_dist = abs(entry - sl)
                        rr = round(tp_dist_new / new_sl_dist, 2) if new_sl_dist > 0 else 0
                        print(f"  [volatility] Widening SL for {pair}: {old_sl:.4g} -> {sl:.4g}")

                # Dynamic SL widening based on market health
                # EXCEPTION: SELL signals during PANIC should NOT have widened SL
                # — shorts benefit from volatility expanding downward, tight SL is OK
                health_sl_mult = dynamic_sl_multiplier(health, base_mult=1.0)
                if health_sl_mult > 1.0 and not (sig_dir == "SELL" and health == MarketHealth.PANIC):
                    old_sl = sl
                    sl_dist = abs(entry - sl)
                    if sig.get("signal_type", "BUY") == "BUY":
                        sl = entry - sl_dist * health_sl_mult
                    else:
                        sl = entry + sl_dist * health_sl_mult
                    tp_dist_new = abs(tp - entry)
                    new_sl_dist = abs(entry - sl)
                    rr = round(tp_dist_new / new_sl_dist, 2) if new_sl_dist > 0 else 0
                    print(f"  [health={health.value}] Widening SL for {pair}: {old_sl:.4g} -> {sl:.4g} ({health_sl_mult:.1f}x)")

                # --- Minimum SL floor: never closer than 1.5% ---
                # Crypto noise on 4h is ~0.5-1.0%, so SL < 1.5% gets hit by random walks
                min_sl_pct = 0.015  # 1.5% minimum distance
                sl_dist_abs = abs(entry - sl)
                if sl_dist_abs / entry < min_sl_pct:
                    if sig.get("signal_type", "BUY") == "BUY":
                        sl = entry * (1 - min_sl_pct)
                    else:
                        sl = entry * (1 + min_sl_pct)
                    # Recalculate R:R with floor SL
                    tp_dist_new = abs(tp - entry)
                    new_sl_dist = abs(entry - sl)
                    rr = round(tp_dist_new / new_sl_dist, 2) if new_sl_dist > 0 else 0
                    print(f"  [SL floor] {pair}: SL widened to {min_sl_pct*100:.1f}% minimum")

                # --- RR Gate: Mercury data shows RR>=1.5 lifts WR 39%->68% ---
                MIN_RR_GATE = 1.5
                if rr < MIN_RR_GATE:
                    print(f"    [RR GATE] {pair} {strat_name}: R:R={rr:.2f} < {MIN_RR_GATE} -- skipped")
                    continue

                # --- Expected return pre-filter (Kimi/Lopez de Prado) ---
                # E[R] = prob × TP_dist - (1-prob) × SL_dist - costs
                # Only trade when E[R] > cost × 2 (minimum edge requirement)
                # For SELL signals in PANIC: use strategy confidence instead of
                # untrained ML score (ML model doesn't know SHORT patterns yet)
                cost = round_trip_cost(pair)
                tp_dist = abs(tp - entry) / entry
                sl_dist_pct = abs(entry - sl) / entry
                er_prob = ml_score
                if sig_dir == "SELL" and health == MarketHealth.PANIC:
                    er_prob = max(ml_score, sig.get("confidence", 0.5))
                expected_return = er_prob * tp_dist - (1 - er_prob) * sl_dist_pct - cost
                # 3x cost rule: E[R] must exceed 3 * round_trip_cost (min 30 bps)
                min_expected = max(cost * 3, 0.003)
                if expected_return < min_expected:
                    print(f"    [filtered] {pair}: E[R]={expected_return:.4f} < min {min_expected:.4f} (3x cost rule, prob={er_prob:.3f}, TP%={tp_dist:.4f}, SL%={sl_dist_pct:.4f}, cost={cost:.4f})")
                    continue

                # Adaptive threshold: cost-aware breakeven (Kissell 2020)
                min_conf = adaptive_threshold(tp_dist, sl_dist_pct, cost)
                # Use ML score as confidence — use dynamic_filter (health-aware) not static FILTER_THRESHOLD
                effective_threshold = max(min_conf, dynamic_filter)
                if ml_score < effective_threshold:
                    print(f"    [filtered] {pair}: ML score {ml_score:.3f} < threshold {effective_threshold:.3f}")
                    continue

                # Store ML filter features for future retraining
                filter_features_list = features.tolist() if hasattr(features, 'tolist') else list(features) if features is not None else None

                sig.update({
                    "take_profit": round(tp, 8),
                    "stop_loss": round(sl, 8),
                    "risk_reward": round(rr, 2),
                    "ml_score": round(ml_score, 4),
                    "ml_method": method,
                    "tp_sl_method": tp_sl_method,
                    "confidence": round(ml_score, 4),
                    "market_health": health.value,
                    "timestamp": now.isoformat(),
                    "system": SYSTEM_NAME,
                    "version": VERSION,
                    "fear_greed": fear_greed,
                    "funding_rate": funding_rates.get(pair, 0.0),
                    "filter_features": filter_features_list,
                    "timestamp_est": now.astimezone(EST).strftime("%Y-%m-%d %I:%M %p EST"),
                    "pick_reason": (
                        f"{sig.get('strategy', '?')} signal on {sig.get('timeframe', '1h')} "
                        f"| {sig.get('reason', '')} "
                        f"| ML filter score {ml_score:.2f} (threshold {FILTER_THRESHOLD}) "
                        f"| R:R {rr:.1f} | TP/SL via {tp_sl_method} "
                        f"| F&G={fear_greed} | Funding={funding_rates.get(pair, 0.0):.4f}"
                    ),
                })

                # Calculate initial unrealized P&L from latest close
                current_price = float(df["close"].iloc[-1]) if "close" in df.columns else float(df["Close"].iloc[-1])
                sig["current_price"] = current_price
                if sig.get("signal_type", "BUY") == "BUY":
                    sig["unrealized_pnl_pct"] = round((current_price - sig["entry_price"]) / sig["entry_price"] * 100, 4)
                else:
                    sig["unrealized_pnl_pct"] = round((sig["entry_price"] - current_price) / sig["entry_price"] * 100, 4)

                new_signals.append(sig)
                active_symbols.add(pair)
                break  # one signal per symbol per scan

    # --- Meta-Labeler Quality Gate (Lopez de Prado M2) ---
    # Filters low-quality signals using heuristic rules (<50 trades) or
    # trained RandomForest (>=50 trades) based on closed pick outcomes.
    if new_signals:
        new_signals = meta_label_filter(new_signals, closed, SYSTEM_NAME)

    # --- External Signal Confluence (Deribit + Binance Contrarian) ---
    # Boost confidence when external signals agree, penalize when they disagree.
    # Picks whose confidence drops below 0.45 after penalty are removed.
    if new_signals:
        new_signals = apply_external_confluence_batch(new_signals, ext_signals)

    # Apply market health gate to filter/adjust signals
    raw_count = len(new_signals)
    new_signals = apply_health_gate(health, new_signals)
    if raw_count > 0 and len(new_signals) < raw_count:
        print(f"  Health gate ({health.value}): {raw_count} -> {len(new_signals)} signals")

    # Deduplicate: keep best signal per symbol (prevents BUY+SELL on same pair)
    # Only check against EXISTING active picks, not newly generated signals
    new_signals.sort(key=lambda s: s.get("confidence", 0), reverse=True)
    existing_syms = {p["symbol"] for p in active}  # Only pre-existing active picks
    seen_new = set()
    deduped = []
    for sig in new_signals:
        sym = sig["symbol"]
        if sym not in existing_syms and sym not in seen_new:
            deduped.append(sig)
            seen_new.add(sym)
    if len(deduped) < len(new_signals):
        print(f"  Dedup: {len(new_signals)} -> {len(deduped)} signals (removed {len(new_signals) - len(deduped)} duplicate/active symbols)")
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
        print(f"  NEW: {sig['symbol']} {sig['signal_type']} via {sig['strategy']} "
              f"(ML:{sig['ml_score']:.2f}, R:R:{sig['risk_reward']:.1f}, TP/SL:{sig['tp_sl_method']})")

    print(f"  Active: {len(active)} | Closed: {len(closed)} | New: {added}")
    print(f"  Stats: WR={stats.get('win_rate', 0):.1%} Sharpe={stats.get('sharpe', 0):.2f} DD={dd:.1%}")

    # Save everything
    save_picks(active, newly_closed, DATA_DIR)
    _write_dashboard_data(active, closed, stats)

    # Check DSR validation status
    _dsr_validated = False
    try:
        _vr_path = os.path.join(os.path.dirname(__file__), "models", "validation_report.json")
        if os.path.exists(_vr_path):
            with open(_vr_path) as _vf:
                _dsr_validated = bool(json.load(_vf).get("passed", False))
    except Exception:
        pass

    # Write scan summary for debugging
    ext_summary = {}
    if ext_signals:
        deribit = ext_signals.get("deribit")
        if deribit:
            ext_summary["deribit_composite"] = deribit.get("signals", {}).get("composite_signal", "NEUTRAL")
            ext_summary["deribit_strength"] = deribit.get("signals", {}).get("composite_strength", 0)
        binance = ext_signals.get("binance")
        if binance:
            ext_summary["binance_composites"] = {
                sym: data.get("signals", {}).get("composite", {}).get("signal", "?")
                for sym, data in binance.items()
            }
        ext_summary["ext_errors"] = ext_signals.get("errors", [])
        regime = ext_signals.get("regime")
        if regime:
            ext_summary["regime_signals"] = {
                name: sig.get("signal", "?")
                for name, sig in regime.items()
            }

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
        "dsr_validated": _dsr_validated,
        "external_signals": ext_summary,
    }
    with open(os.path.join(DATA_DIR, "scan_summary.json"), "w") as f:
        json.dump(scan_summary, f, indent=2)

    # Send Discord notifications
    gate = passes_validation_gate(closed)

    # Notify exits
    for closed_pick in newly_closed:
        send_pick_exit("The Filter", closed_pick)

    # Notify new picks
    for sig in active[-added:] if added > 0 else []:
        if sig.get("confidence", 0) >= 0.65:
            send_pick_alert("The Filter", sig)

    # Hourly status
    send_system_status(
        system_name=SYSTEM_NAME,
        system_label="The Filter",
        version=VERSION,
        active_picks=active,
        closed_picks=closed,
        stats=stats,
        validation_gate=gate,
        ml_filter_acceptance_rate=added / max(1, len(new_signals)) if new_signals else None,
    )

    print(f"[System A] Scan complete.")


def _write_dashboard_data(active: list, closed: list, stats: dict):
    """Write JSON data for dashboard consumption."""
    # Strategy inception registry — when each strategy was first added to System A
    STRATEGY_INCEPTION = {
        "supertrend_follow":          {"inception": "2026-02-23T01:00:00Z", "last_code_update": "2026-02-23T01:00:00Z"},
        "connors_rsi2":               {"inception": "2026-02-23T01:00:00Z", "last_code_update": "2026-02-23T01:00:00Z"},
        "bollinger_keltner_squeeze":  {"inception": "2026-02-23T01:00:00Z", "last_code_update": "2026-02-23T01:00:00Z"},
        "rsi_macd_confluence":        {"inception": "2026-02-23T01:00:00Z", "last_code_update": "2026-02-23T01:00:00Z"},
        "ema_stack":                  {"inception": "2026-02-23T01:00:00Z", "last_code_update": "2026-02-23T01:00:00Z"},
        "volume_climax_reversal":     {"inception": "2026-02-23T01:00:00Z", "last_code_update": "2026-02-23T01:00:00Z"},
        "swing_failure_pattern":      {"inception": "2026-02-23T01:00:00Z", "last_code_update": "2026-02-23T01:00:00Z"},
        "ornstein_uhlenbeck":         {"inception": "2026-02-23T01:00:00Z", "last_code_update": "2026-02-23T01:00:00Z"},
        "narrative_sniper":           {"inception": "2026-02-23T01:00:00Z", "last_code_update": "2026-02-23T01:00:00Z"},
        "rsi_bb_macd_confluence":     {"inception": "2026-02-24T12:00:00Z", "last_code_update": "2026-02-24T12:00:00Z"},
        "supertrend_volume_confirmed":{"inception": "2026-02-24T12:00:00Z", "last_code_update": "2026-02-24T12:00:00Z"},
        "funding_rate_extreme":       {"inception": "2026-02-24T12:00:00Z", "last_code_update": "2026-02-24T12:00:00Z"},
        "fear_capitulation_dca":      {"inception": "2026-02-24T22:00:00Z", "last_code_update": "2026-02-24T22:00:00Z"},
        "bb_mean_reversion":          {"inception": "2026-02-24T22:00:00Z", "last_code_update": "2026-02-24T22:00:00Z"},
        "keltner_channel_breakout":   {"inception": "2026-02-24T22:00:00Z", "last_code_update": "2026-02-24T22:00:00Z"},
        "rsi_divergence":             {"inception": "2026-02-24T23:00:00Z", "last_code_update": "2026-02-24T23:00:00Z"},
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
        "system": "The Filter",
        "version": VERSION,
        "scan_frequency": SCAN_FREQUENCY,
        "inception_date": "2026-02-23T01:00:00Z",
        "last_code_update": "2026-02-24T20:00:00Z",
        "updated": datetime.now(timezone.utc).isoformat(),
        "updated_est": datetime.now(EST).strftime("%Y-%m-%d %I:%M %p EST"),
        "active_picks": active,
        "stats": {k: v for k, v in stats.items() if k != "equity_curve"},
        "equity_curve": stats.get("equity_curve", []),
        "total_closed": len(closed),
        "recent_closed": closed[-20:] if closed else [],
        "strategy_breakdown": strategy_breakdown,
    }
    with open(os.path.join(DATA_DIR, "dashboard.json"), "w") as f:
        json.dump(dashboard_data, f, indent=2, default=str)


if __name__ == "__main__":
    scan()
