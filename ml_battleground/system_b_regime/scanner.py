# PRIMARY SYSTEM - Backtested 56.6% WR, Sharpe 9.91 on 90d 4h data
"""
System B Scanner: "The Regime"
Classify regime -> Route to strategies -> ATR TP/SL -> Validate -> Save

Pipeline:
  1. Load active picks, validate existing (TP/SL/trailing/expiry)
  2. Fetch OHLCV for 4h (primary) and 1h (secondary) timeframes
  3. For each pair: classify regime -> route to appropriate strategies
  4. Set regime-specific ATR TP/SL, enforce R:R >= 1.5
  5. Apply risk management (max 5 concurrent, 2% per trade, 10% DD breaker)
  6. Save picks, send Discord notifications, write dashboard data

Run: python -m ml_battleground.system_b_regime.scanner
"""
import os
import sys
import json
import time
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.data_fetcher import fetch_ohlcv, fetch_fear_greed, fetch_funding_rates, fetch_fear_greed_history, fear_greed_persistence, PAIRS
from shared import indicators as ind
from shared.risk_manager import can_open_trade, calculate_drawdown, position_size, should_trade
from shared.cost_model import round_trip_cost
from shared.validator import validate_picks, save_picks, load_active, load_closed, passes_validation_gate
from shared.performance import compute_stats
from shared.discord_notify import send_system_status, send_pick_alert, send_pick_exit
from shared.market_health import check_market_health, apply_health_gate, MarketHealth, dynamic_sl_multiplier
from shared.trade_filters import adaptive_threshold, atr_percentile_filter, volume_confirmation, reversal_confirmation
from shared.cost_model import round_trip_cost
from shared.strategy_health import filter_signals_by_health
from shared.symbol_lock import filter_signals_by_lock
from shared.revision_marker import check_revision
from shared.meta_labeler import filter_signals_batch as meta_label_filter
from shared.external_signals import fetch_external_signals, apply_external_confluence_batch, log_external_signals_summary

from system_b_regime.regime_classifier import classify
from system_b_regime.strategy_router import route, get_regime_config

VERSION = "1.0.0"
SYSTEM_NAME = "system_b_regime"
SYSTEM_LABEL = "The Regime"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MIN_RR = 1.5
MIN_CONFIDENCE = 0.55  # raised from 0.40 — stop accepting garbage picks
EST = timezone(timedelta(hours=-5))
SCAN_FREQUENCY = "Every 30 minutes"
SCAN_STATE_PATH = os.path.join(DATA_DIR, "last_scan_state.json")


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
    """Main scan cycle for System B."""
    now = datetime.now(timezone.utc)
    print(f"[System B - The Regime] Scan started at {now.isoformat()}")
    print(f"  Version: {VERSION}")

    # Check for revision reset (archives pre-revision data, resets tracking)
    from pathlib import Path
    check_revision(SYSTEM_NAME, Path(DATA_DIR))

    # -------------------------------------------------------------------------
    # 1. Fetch market context early — needed for bounce detector in validator
    # -------------------------------------------------------------------------
    fear_greed = fetch_fear_greed()
    funding_rates = fetch_funding_rates()
    print(f"  Fear & Greed: {fear_greed}")

    # -------------------------------------------------------------------------
    # 2. Load existing state and validate active picks
    # -------------------------------------------------------------------------
    active = load_active(DATA_DIR)
    closed = load_closed(DATA_DIR)

    print(f"  Loaded: {len(active)} active, {len(closed)} closed")

    active, newly_closed = validate_picks(active, SYSTEM_NAME, DATA_DIR,
                                          fear_greed=fear_greed)

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
    # 3. Compute stats and check risk budget
    # -------------------------------------------------------------------------
    stats = compute_stats(closed)
    equity_curve = stats.get("equity_curve", [10000.0])
    dd = calculate_drawdown(equity_curve)
    can_trade, reason = can_open_trade(len(active), dd)

    if not can_trade:
        print(f"  Cannot open new trades: {reason}")
        save_picks(active, newly_closed, DATA_DIR)
        _write_dashboard_data(active, closed, stats, "range_bound", 0.0)
        _send_status(active, closed, stats, "range_bound", 0.0)
        print(f"[System B] Scan complete (risk limit).")
        return

    # Drawdown halt gate (8% DD = stop trading until recovery)
    ok_to_trade, halt_reason = should_trade(equity_curve)
    if not ok_to_trade:
        print(f"  {halt_reason}")
        save_picks(active, newly_closed, DATA_DIR)
        _write_dashboard_data(active, closed, stats, "range_bound", 0.0)
        _send_status(active, closed, stats, "range_bound", 0.0)
        print(f"[System B] Scan complete (drawdown halt).")
        return

    # --- Market Health Gate ---
    btc_health_data = fetch_ohlcv(["BTCUSDT"], "1h", 300)
    btc_df_health = btc_health_data.get("BTCUSDT")

    # --- Candle-Close Gate: skip scan if no new 1h candle has closed ---
    if not _check_candle_gate(btc_df_health):
        print(f"  Skipping scan: no new 1h candle closed since last scan")
        save_picks(active, newly_closed, DATA_DIR)
        _write_dashboard_data(active, closed, stats, "range_bound", 0.0)
        _send_status(active, closed, stats, "range_bound", 0.0)
        print(f"[System B] Scan complete (no new candle).")
        return

    health, health_details = check_market_health(fear_greed, btc_df_health, funding_rates)
    print(f"  Market Health: {health.value} | F&G={fear_greed}, BTC trend={health_details.get('btc_trend','?')}, "
          f"BTC 24h={health_details.get('btc_24h_change','?')}%, volatility={health_details.get('volatility','?')}")

    if health == MarketHealth.PANIC:
        print(f"  *** PANIC MODE: scanning for SELL-only opportunities ***")

    # --- F&G 3-Day Persistence (R008: Wong, Sharpe 1.3) ---
    fg_history = fetch_fear_greed_history(7)
    fg_persist = fear_greed_persistence(fg_history)
    if fg_persist["persistent"]:
        print(f"  F&G PERSISTENT: {fg_persist['direction']} ({fg_persist['fear_days']}d fear, {fg_persist['greed_days']}d greed)")

    # --- F&G Directional Filter (HARD BLOCK — same logic as System A) ---
    # Extreme fear = SELL only (market crashing), extreme greed = BUY only
    fg_direction = None
    fg_confidence_boost = 0.0
    if fear_greed < 15:
        # P0 BOUNCE DETECTOR: F&G < 15 = capitulation bottom 70-80% of historical cases
        fg_direction = None
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

    # --- External Signal Confluence (Deribit + Binance Contrarian) ---
    ext_signals = fetch_external_signals()
    log_external_signals_summary(ext_signals)

    # -------------------------------------------------------------------------
    # 4. Fetch OHLCV and run regime-based strategy routing
    # -------------------------------------------------------------------------
    new_signals = []
    active_symbols = {p["symbol"] for p in active}
    regime_summary = {}  # track per-pair regime for dashboard

    # Primary: 4h (best signal-to-noise), Secondary: 1h
    # 15m removed — too noisy for crypto, destroys profitability via transaction costs
    for interval in ["4h", "1h"]:
        limit = 500
        data = fetch_ohlcv(PAIRS, interval, limit)

        for pair, df in data.items():
            if pair in active_symbols:
                continue
            if len(df) < 100:
                continue

            # Classify regime using 1h data preferentially
            # (for 15m, we still classify but use 1h regime if available)
            try:
                regime, regime_confidence, regime_duration = classify(df, fear_greed=float(fear_greed))
                print(f"  {pair}: regime={regime} conf={regime_confidence:.2f} duration={regime_duration} bars")
            except Exception as e:
                print(f"  [WARN] Regime classification failed for {pair}: {e}")
                regime, regime_confidence, regime_duration = "range_bound", 0.40, 0

            # Track regime for dashboard
            if pair not in regime_summary or interval == "1h":
                regime_summary[pair] = {
                    "regime": regime,
                    "confidence": regime_confidence,
                    "regime_duration": regime_duration,
                    "timeframe": interval,
                }

            # --- Research-backed pre-trade filters ---
            # ATR percentile filter (Wilder 1978)
            # Exception: SELL signals during panic — high vol is where shorts thrive
            atr_vals = ind.atr(df["High"], df["Low"], df["Close"], 14)
            if len(atr_vals) >= 50 and not atr_percentile_filter(atr_vals.values):
                if fg_direction == "SELL" and fear_greed < 25:
                    print(f"    [exempt] {pair}: ATR filter bypassed for SELL in PANIC (F&G={fear_greed})")
                else:
                    print(f"    [filtered] {pair}: ATR outside 40-95th percentile")
                    continue

            # Volume confirmation gate
            # Exception: during panic, low volume is normal (sell-off already happened)
            vol_col = "volume" if "volume" in df.columns else "Volume"
            vol_ok, vol_ratio = volume_confirmation(df[vol_col].values)
            if not vol_ok:
                if fg_direction == "SELL" and fear_greed < 25:
                    print(f"    [exempt] {pair}: volume filter bypassed for SELL in PANIC (ratio={vol_ratio:.2f})")
                else:
                    print(f"    [filtered] {pair}: volume ratio {vol_ratio:.2f} < 0.7")
                    continue

            # Reversal confirmation: require price action to confirm direction (Elder 1993)
            # For System B, check both BUY and SELL directions — filter applied per-signal below
            close_col = "close" if "close" in df.columns else "Close"
            high_col = "high" if "high" in df.columns else "High"
            low_col = "low" if "low" in df.columns else "Low"
            _rev_closes = df[close_col].values
            _rev_highs = df[high_col].values
            _rev_lows = df[low_col].values

            # Route to regime-appropriate strategies
            signals = route(
                regime=regime,
                regime_confidence=regime_confidence,
                df=df,
                pair=pair,
                interval=interval,
                min_rr=MIN_RR,
                fear_greed=fear_greed,
            )

            for sig in signals:
                # Skip low-confidence signals
                if sig.get("confidence", 0) < MIN_CONFIDENCE:
                    continue

                # --- Regime Directional Filter (CRITICAL FIX) ---
                # Don't BUY in confirmed downtrends or SELL in confirmed uptrends.
                # The regime classifier correctly identifies direction but route()
                # still returns counter-trend signals. Block them here.
                sig_dir = sig.get("signal_type", "BUY")
                if regime == "trending_down" and regime_confidence >= 0.85 and sig_dir == "BUY":
                    print(f"    [filtered] {pair}: BUY blocked (regime=trending_down, conf={regime_confidence:.0%})")
                    continue
                if regime == "trending_up" and regime_confidence >= 0.70 and sig_dir == "SELL":
                    print(f"    [filtered] {pair}: SELL blocked (regime=trending_up, conf={regime_confidence:.0%})")
                    continue

                # Reversal confirmation: price action must confirm signal direction
                # Bypass for SELL in PANIC: trend is strongly down, green candles = dead cat bounce
                sig_dir = sig.get("signal_type", "BUY")
                if sig_dir == "SELL" and fear_greed < 25:
                    rev_ok, rev_reason = True, "bypassed_sell_panic"
                else:
                    rev_ok, rev_reason = reversal_confirmation(
                        _rev_closes, _rev_highs, _rev_lows,
                        signal_type=sig_dir,
                    )
                if not rev_ok:
                    print(f"    [filtered] {pair}: reversal not confirmed ({rev_reason})")
                    continue

                # F&G directional filter
                if fg_direction and sig.get("signal_type", "BUY") != fg_direction:
                    continue

                # Dynamic SL widening based on market health
                # Skip for SELL in PANIC: shorts benefit from volatility expanding downward
                health_sl_mult = dynamic_sl_multiplier(health, base_mult=1.0)
                if health_sl_mult > 1.0 and "stop_loss" in sig and "entry_price" in sig and not (sig_dir == "SELL" and fear_greed < 25):
                    entry = sig["entry_price"]
                    sl = sig["stop_loss"]
                    tp = sig["take_profit"]
                    sl_dist = abs(entry - sl)
                    if sig.get("signal_type", "BUY") == "BUY":
                        sl = entry - sl_dist * health_sl_mult
                    else:
                        sl = entry + sl_dist * health_sl_mult
                    sig["stop_loss"] = round(sl, 8)
                    # Recalculate R:R
                    risk = abs(entry - sl)
                    reward = abs(tp - entry)
                    sig["risk_reward"] = round(reward / risk, 2) if risk > 0 else 0
                    print(f"  [health={health.value}] Widening SL for {pair}: {health_sl_mult:.1f}x")

                # --- Minimum SL floor: never closer than 1.5% ---
                entry = sig["entry_price"]
                sl = sig["stop_loss"]
                tp = sig["take_profit"]
                sl_dist_abs = abs(entry - sl)
                if entry > 0 and sl_dist_abs / entry < 0.015:
                    if sig.get("signal_type", "BUY") == "BUY":
                        sl = entry * (1 - 0.015)
                    else:
                        sl = entry * (1 + 0.015)
                    sig["stop_loss"] = round(sl, 8)
                    risk = abs(entry - sl)
                    reward = abs(tp - entry)
                    sig["risk_reward"] = round(reward / risk, 2) if risk > 0 else 0
                    print(f"  [SL floor] {pair}: SL widened to 1.5% minimum")

                # --- Expected return pre-filter (Kimi/Lopez de Prado) ---
                cost = round_trip_cost(pair)
                tp_dist_pct = abs(sig["take_profit"] - entry) / entry if entry > 0 else 0
                sl_dist_pct = abs(sig["stop_loss"] - entry) / entry if entry > 0 else 0
                conf = sig.get("confidence", 0.5)
                # For SELL in PANIC: use max of ML and strategy confidence
                if sig_dir == "SELL" and fear_greed < 25:
                    ml_sc = sig.get("ml_score", 0)
                    conf = max(conf, ml_sc, 0.55)  # Floor at 0.55 for untrained ML
                expected_return = conf * tp_dist_pct - (1 - conf) * sl_dist_pct - cost
                # 3x cost rule: E[R] must exceed 3 * round_trip_cost (min 30 bps)
                # Relaxed for SELL in PANIC: 1.5x cost (shorts profit from momentum)
                if sig_dir == "SELL" and fear_greed < 25:
                    min_er = max(cost * 1.5, 0.001)  # 10 bps minimum for panic shorts
                else:
                    min_er = max(cost * 3, 0.003)  # at least 30 bps
                if expected_return < min_er:
                    print(f"    [filtered] {pair}: E[R]={expected_return:.4f} < min {min_er:.4f} (3x cost rule)")
                    continue

                # Adaptive threshold: cost-aware breakeven (Kissell 2020)
                min_conf = adaptive_threshold(tp_dist_pct, sl_dist_pct, cost, regime=regime)
                # Hard confidence floor: never open below MIN_CONFIDENCE
                effective_min = max(min_conf, MIN_CONFIDENCE)
                if conf < effective_min:
                    print(f"    [filtered] {pair}: confidence {conf:.3f} < threshold {effective_min:.3f}")
                    continue

                # Attach system metadata
                sig.update({
                    "system": SYSTEM_NAME,
                    "market_health": health.value,
                    "version": VERSION,
                    "timestamp": now.isoformat(),
                    "fear_greed": fear_greed,
                    "funding_rate": funding_rates.get(pair, 0.0),
                    "regime_duration": regime_duration,
                    "category": "crypto",
                    "timestamp_est": now.astimezone(EST).strftime("%Y-%m-%d %I:%M %p EST"),
                    "pick_reason": (
                        f"{sig.get('strategy', '?')} signal on {sig.get('timeframe', interval)} "
                        f"| Regime: {sig.get('regime', regime)} ({sig.get('regime_confidence', regime_confidence):.0%} conf) "
                        f"| Confidence {sig.get('confidence', 0):.2f} | R:R {sig.get('risk_reward', 0):.1f} "
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

    # -------------------------------------------------------------------------
    # 5. Meta-Labeler Quality Gate, then health gate, rank and select
    # -------------------------------------------------------------------------
    # Meta-Labeler (Lopez de Prado M2): filters low-quality signals using
    # heuristic rules (<50 trades) or trained RF (>=50 trades).
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

    # Sort by combined score: confidence * regime_confidence * R:R
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

    added = 0
    for sig in deduped:
        can, reason = can_open_trade(len(active), dd)
        if not can:
            break
        active.append(sig)
        added += 1
        print(
            f"  NEW: {sig['symbol']} {sig['signal_type']} via {sig['strategy']} "
            f"| regime={sig.get('regime', '?')} ({sig.get('regime_confidence', 0):.0%}) "
            f"| conf={sig.get('confidence', 0):.2f} | R:R={sig.get('risk_reward', 0):.1f} "
            f"| TP={sig.get('take_profit', 0):.6g} SL={sig.get('stop_loss', 0):.6g}"
        )

        # Send Discord alert for high-confidence picks
        if sig.get("confidence", 0) >= 0.55:
            try:
                send_pick_alert(SYSTEM_LABEL, sig)
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # 6. Determine dominant regime (most common across scanned pairs)
    # -------------------------------------------------------------------------
    if regime_summary:
        regime_counts = {}
        for info in regime_summary.values():
            r = info["regime"]
            regime_counts[r] = regime_counts.get(r, 0) + 1
        dominant_regime = max(regime_counts, key=regime_counts.get)
        dominant_conf = np.mean([
            info["confidence"]
            for info in regime_summary.values()
            if info["regime"] == dominant_regime
        ])
    else:
        dominant_regime = "range_bound"
        dominant_conf = 0.50

    # -------------------------------------------------------------------------
    # 7. Save and report
    # -------------------------------------------------------------------------
    save_picks(active, newly_closed, DATA_DIR)
    _write_dashboard_data(active, closed, stats, dominant_regime, dominant_conf, regime_summary)

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
    scan_summary = {
        "timestamp": now.isoformat(),
        "market_health": health.value,
        "fear_greed": fear_greed,
        "dominant_regime": dominant_regime,
        "active_count": len(active),
        "closed_count": len(closed),
        "new_picks": added,
        "newly_closed": len(newly_closed),
        "win_rate": stats.get("win_rate", 0),
        "sharpe": stats.get("sharpe", 0),
        "drawdown": round(dd, 4),
        "dsr_validated": _dsr_validated,
    }
    with open(os.path.join(DATA_DIR, "scan_summary.json"), "w") as f:
        json.dump(scan_summary, f, indent=2)

    print(f"\n  Active: {len(active)} | Closed: {len(closed)} | New: {added}")
    print(f"  Dominant regime: {dominant_regime} ({dominant_conf:.0%})")
    print(f"  Stats: WR={stats.get('win_rate', 0):.1%} Sharpe={stats.get('sharpe', 0):.2f} DD={dd:.1%}")

    # Send Discord status
    _send_status(active, closed, stats, dominant_regime, dominant_conf)

    print(f"[System B - The Regime] Scan complete.")


def _send_status(
    active: list[dict],
    closed: list[dict],
    stats: dict,
    regime: str,
    regime_confidence: float,
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
            regime=regime,
            regime_confidence=regime_confidence,
        )
    except Exception as e:
        print(f"  [WARN] Discord notification failed: {e}")


def _write_dashboard_data(
    active: list[dict],
    closed: list[dict],
    stats: dict,
    dominant_regime: str,
    dominant_conf: float,
    regime_summary: dict = None,
):
    """Write JSON data for dashboard consumption."""
    os.makedirs(DATA_DIR, exist_ok=True)

    # Per-regime stats
    regime_stats = {}
    if closed:
        for regime_name in ["trending_up", "trending_down", "range_bound", "high_volatility"]:
            regime_picks = [p for p in closed if p.get("regime") == regime_name]
            if regime_picks:
                pnls = [p.get("net_pnl_pct", 0) for p in regime_picks]
                wins = [p for p in pnls if p > 0]
                regime_stats[regime_name] = {
                    "trades": len(regime_picks),
                    "win_rate": len(wins) / len(regime_picks) if regime_picks else 0,
                    "avg_pnl": float(np.mean(pnls)) if pnls else 0,
                    "total_pnl": sum(pnls),
                }

    # Per-strategy stats
    strategy_stats = {}
    if closed:
        for pick in closed:
            strat = pick.get("strategy", "unknown")
            if strat not in strategy_stats:
                strategy_stats[strat] = {"trades": 0, "wins": 0, "total_pnl": 0}
            strategy_stats[strat]["trades"] += 1
            pnl = pick.get("net_pnl_pct", 0)
            strategy_stats[strat]["total_pnl"] += pnl
            if pnl > 0:
                strategy_stats[strat]["wins"] += 1
        for strat, s in strategy_stats.items():
            s["win_rate"] = s["wins"] / s["trades"] if s["trades"] > 0 else 0

    # Regime timeline (for pairs being tracked)
    regime_timeline = {}
    if regime_summary:
        for pair, info in regime_summary.items():
            regime_timeline[pair] = {
                "regime": info["regime"],
                "confidence": round(info["confidence"], 4),
            }

    # Strategy inception registry — when each strategy was first added to System B
    STRATEGY_INCEPTION = {
        "supertrend_follow":          {"inception": "2026-02-23T01:00:00Z", "last_code_update": "2026-02-23T01:00:00Z"},
        "connors_rsi2":               {"inception": "2026-02-23T01:00:00Z", "last_code_update": "2026-02-23T01:00:00Z"},
        "bollinger_keltner_squeeze":  {"inception": "2026-02-23T01:00:00Z", "last_code_update": "2026-02-23T01:00:00Z"},
        "rsi_macd_confluence":        {"inception": "2026-02-23T01:00:00Z", "last_code_update": "2026-02-23T01:00:00Z"},
        "ema_stack":                  {"inception": "2026-02-23T01:00:00Z", "last_code_update": "2026-02-23T01:00:00Z"},
        "volume_climax_reversal":     {"inception": "2026-02-23T01:00:00Z", "last_code_update": "2026-02-24T05:00:00Z"},
        "swing_failure_pattern":      {"inception": "2026-02-23T01:00:00Z", "last_code_update": "2026-02-23T01:00:00Z"},
        "ornstein_uhlenbeck":         {"inception": "2026-02-23T01:00:00Z", "last_code_update": "2026-02-23T01:00:00Z"},
        "narrative_sniper":           {"inception": "2026-02-23T01:00:00Z", "last_code_update": "2026-02-23T01:00:00Z"},
        "rsi_bb_macd_confluence":     {"inception": "2026-02-24T12:00:00Z", "last_code_update": "2026-02-24T12:00:00Z"},
        "supertrend_volume_confirmed":{"inception": "2026-02-24T12:00:00Z", "last_code_update": "2026-02-24T12:00:00Z"},
        "funding_rate_extreme":       {"inception": "2026-02-24T12:00:00Z", "last_code_update": "2026-02-24T12:00:00Z"},
    }

    # Enrich strategy_stats with inception metadata
    for strat_name, strat_data in strategy_stats.items():
        meta = STRATEGY_INCEPTION.get(strat_name, {})
        strat_data["inception"] = meta.get("inception")
        strat_data["last_code_update"] = meta.get("last_code_update")

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
        "inception_date": "2026-02-23T01:00:00Z",
        "last_code_update": "2026-02-24T20:00:00Z",
        "updated": datetime.now(timezone.utc).isoformat(),
        "updated_est": datetime.now(EST).strftime("%Y-%m-%d %I:%M %p EST"),
        "dominant_regime": dominant_regime,
        "dominant_regime_confidence": round(dominant_conf, 4),
        "active_picks": active,
        "stats": {k: v for k, v in stats.items() if k != "equity_curve"},
        "equity_curve": stats.get("equity_curve", []),
        "total_closed": len(closed),
        "recent_closed": closed[-20:] if closed else [],
        "regime_stats": regime_stats,
        "strategy_stats": strategy_stats,
        "regime_timeline": regime_timeline,
    }

    dashboard_path = os.path.join(DATA_DIR, "dashboard.json")
    with open(dashboard_path, "w") as f:
        json.dump(dashboard_data, f, indent=2, default=str)


# numpy needed for mean calculation in scan()
import numpy as np


if __name__ == "__main__":
    scan()
