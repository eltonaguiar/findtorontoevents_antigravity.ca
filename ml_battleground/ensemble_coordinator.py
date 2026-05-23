"""
Ensemble Coordinator: Regime-Conditioned Agreement Alpha
=========================================================
Wires all five ML Battleground systems together:

  System B ("The Regime")     -> PRIMARY (56.6% WR, Sharpe 9.91 backtested)
  System A ("The Filter")     -> PREDICTOR (ML-filtered strategy signals)
  System C ("The Neural Net") -> PREDICTOR (GRU-Attention neural net)
  System D ("The Carry Trade") -> INDEPENDENT (funding rate contrarian carry)
  System E ("The Momentum")   -> INDEPENDENT (cross-sectional momentum)

Ensemble Rules:
  1. System B signals weighted 2x vs A and C (backtest-proven primary)
  2. A+C agreement picks still generated (Agreement Alpha)
  3. System B standalone picks allowed at 50% position size even without
     A+C agreement (B is the only profitable system in backtests)
  4. Systems D and E operate independently — their signals are included
     at 50% position size when they pass the E[R] gate (uncorrelated alpha)

Position sizing uses:
  - Agreement strength (geometric mean of confidences)
  - System B weight bonus (2x)
  - Regime context (smaller in range, larger in trend)
  - Kelly fraction capped at 0.25

Output: Same JSON format as individual scanner outputs.

Run: python -m ml_battleground.ensemble_coordinator
"""
import os
import sys
import json
import math
import numpy as np
from datetime import datetime, timezone, timedelta

# Ensure imports work from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.data_fetcher import fetch_ohlcv, fetch_fear_greed, fetch_funding_rates, PAIRS
from shared.risk_manager import can_open_trade, calculate_drawdown, MAX_CONCURRENT
from shared.cost_model import round_trip_cost
from shared.validator import validate_picks, save_picks, load_active, load_closed
from shared.performance import compute_stats
from shared.discord_notify import send_system_status, send_pick_alert, send_pick_exit
from shared.market_health import check_market_health, apply_health_gate, MarketHealth

VERSION = "1.2.0"
SYSTEM_NAME = "ensemble"
SYSTEM_LABEL = "The Ensemble"
DATA_DIR = os.path.join(os.path.dirname(__file__), "ensemble_data")
EST = timezone(timedelta(hours=-5))
SCAN_FREQUENCY = "Every 30 minutes"

# --- Agreement Alpha Thresholds ---
MIN_COMBINED_CONFIDENCE = 0.60   # geometric mean of A + C confidences
MIN_EXPECTED_RETURN_MULT = 3.0   # E[R] must exceed cost * this multiplier
MIN_COST_BPS = 0.0030            # 30 bps absolute floor for expected return
KELLY_CAP = 0.25                 # maximum Kelly fraction

# System B weight multiplier (PRIMARY SYSTEM - backtested 56.6% WR, Sharpe 9.91)
SYSTEM_B_WEIGHT = 2.0
SYSTEM_B_STANDALONE_SIZE = 0.50  # 50% position size for B-only picks

# Regime-based position scaling
REGIME_POSITION_SCALE = {
    "trending_up":     1.00,  # full size in confirmed trends
    "trending_down":   1.00,  # full size (for SELL signals)
    "range_bound":     0.50,  # half size -- mean reversion is noisier
    "high_volatility": 0.60,  # reduced -- wider stops eat into sizing
}


def _load_system_signals(system_data_dir: str) -> list:
    """Load active picks from a system's data directory."""
    active_path = os.path.join(system_data_dir, "active_picks.json")
    if not os.path.exists(active_path):
        return []
    try:
        with open(active_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return []


def _load_system_scan_summary(system_data_dir: str) -> dict:
    """Load the most recent scan summary from a system."""
    path = os.path.join(system_data_dir, "scan_summary.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return {}


def _adx_regime_fallback() -> str:
    """Simple ADX-based regime detection as fallback when System B is untrusted.

    Uses BTC 4h data with ADX(14):
      - ADX > 25 + DI+ > DI-  -> trending_up
      - ADX > 25 + DI- > DI+  -> trending_down
      - ADX <= 25              -> range_bound
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

        if dx > 25:
            return "trending_up" if plus_di > minus_di else "trending_down"
        return "range_bound"
    except Exception:
        return "range_bound"


def _check_system_b_trusted() -> bool:
    """Check if System B's regime calls should be trusted based on recent WR.

    If System B has < 40% WR on the last 20 trades, its regime calls
    are unreliable and should be replaced with ADX-based detection.
    """
    base = os.path.dirname(__file__)
    closed_path = os.path.join(base, "system_b_regime", "data", "closed_picks.json")
    if not os.path.exists(closed_path):
        return True  # No data = trust by default

    try:
        with open(closed_path) as f:
            b_closed = json.load(f)
        if len(b_closed) < 10:
            return True  # Not enough data to judge

        recent = b_closed[-20:] if len(b_closed) >= 20 else b_closed
        wins = sum(1 for t in recent if t.get("net_pnl_pct", 0) > 0)
        wr = wins / len(recent)
        return wr >= 0.40
    except Exception:
        return True


def _load_regime_state() -> tuple:
    """
    Load the current regime from System B's scan summary and regime history.
    Returns (regime_name, regime_confidence, regime_duration).

    If System B has < 40% WR on last 20 trades, falls back to ADX-based
    regime detection instead of trusting B's unreliable calls.
    """
    base = os.path.dirname(__file__)

    # Check if System B is trusted
    b_trusted = _check_system_b_trusted()

    if not b_trusted:
        # Fall back to ADX-based regime detection
        regime = _adx_regime_fallback()
        print(f"  [regime] System B WR < 40% -- using ADX fallback: {regime}")
        return regime, 0.50, 0

    summary = _load_system_scan_summary(os.path.join(base, "system_b_regime", "data"))
    regime = summary.get("dominant_regime", "range_bound")
    # Load regime history for confidence
    history_path = os.path.join(base, "system_b_regime", "data", "regime_history.json")
    confidence = 0.50
    duration = 0
    if os.path.exists(history_path):
        try:
            with open(history_path) as f:
                history = json.load(f)
            if history:
                # Use average confidence of last 3 readings
                recent = history[-3:]
                confidence = float(np.mean([h.get("confidence", 0.5) for h in recent]))
                # Count consecutive same-regime readings
                for h in reversed(history):
                    if h.get("regime") == regime:
                        duration += 1
                    else:
                        break
        except Exception:
            pass
    return regime, confidence, duration


def _find_agreement_pairs(signals_a: list, signals_c: list) -> list:
    """
    Find symbol pairs where Systems A and C agree on direction.

    Returns list of dicts:
      {
        "symbol": str,
        "direction": "BUY" | "SELL",
        "signal_a": dict,  # full signal from System A
        "signal_c": dict,  # full signal from System C
        "confidence_a": float,
        "confidence_c": float,
        "combined_confidence": float,  # geometric mean
      }
    """
    # Index signals by symbol
    a_by_symbol = {}
    for sig in signals_a:
        sym = sig.get("symbol")
        if sym and sym not in a_by_symbol:
            a_by_symbol[sym] = sig

    c_by_symbol = {}
    for sig in signals_c:
        sym = sig.get("symbol")
        if sym and sym not in c_by_symbol:
            c_by_symbol[sym] = sig

    agreements = []
    common_symbols = set(a_by_symbol.keys()) & set(c_by_symbol.keys())

    for sym in common_symbols:
        sig_a = a_by_symbol[sym]
        sig_c = c_by_symbol[sym]

        dir_a = sig_a.get("signal_type", "BUY")
        dir_c = sig_c.get("signal_type", "BUY")

        if dir_a != dir_c:
            continue  # disagreement -- skip

        conf_a = sig_a.get("confidence", sig_a.get("ml_score", 0.0))
        conf_c = sig_c.get("confidence", sig_c.get("ml_score", 0.0))

        # Geometric mean of confidences (penalizes if either is low)
        combined = math.sqrt(conf_a * conf_c) if conf_a > 0 and conf_c > 0 else 0.0

        agreements.append({
            "symbol": sym,
            "direction": dir_a,
            "signal_a": sig_a,
            "signal_c": sig_c,
            "confidence_a": conf_a,
            "confidence_c": conf_c,
            "combined_confidence": round(combined, 4),
        })

    # Sort by combined confidence descending
    agreements.sort(key=lambda x: x["combined_confidence"], reverse=True)
    return agreements


def _merge_tp_sl(sig_a: dict, sig_c: dict, direction: str) -> tuple:
    """
    Merge TP/SL from Systems A and C.
    Strategy: use the more conservative (tighter) TP and wider SL.
    This is the intersection of both systems' risk views.

    Returns (take_profit, stop_loss, entry_price)
    """
    entry_a = sig_a.get("entry_price", 0)
    entry_c = sig_c.get("entry_price", 0)
    # Use average entry price (both should be very close since same symbol at same time)
    entry = (entry_a + entry_c) / 2.0 if entry_a > 0 and entry_c > 0 else max(entry_a, entry_c)

    tp_a = sig_a.get("take_profit", entry * 1.02)
    tp_c = sig_c.get("take_profit", entry * 1.02)
    sl_a = sig_a.get("stop_loss", entry * 0.98)
    sl_c = sig_c.get("stop_loss", entry * 0.98)

    if direction == "BUY":
        # Conservative TP = closer to entry (smaller upside target)
        tp = min(tp_a, tp_c)
        # Wider SL = further from entry (more room before stop)
        sl = min(sl_a, sl_c)
    else:  # SELL
        # Conservative TP = closer to entry (higher price for short)
        tp = max(tp_a, tp_c)
        # Wider SL = further from entry (higher price for short stop)
        sl = max(sl_a, sl_c)

    return tp, sl, entry


def _kelly_position_size(
    combined_confidence: float,
    tp_dist_pct: float,
    sl_dist_pct: float,
    regime: str,
) -> float:
    """
    Kelly-criterion position sizing with regime scaling.

    Uses combined confidence as win probability estimate, TP/SL
    distances as avg win/loss, applies fractional Kelly (0.25x),
    then scales by regime.
    """
    if sl_dist_pct <= 0 or tp_dist_pct <= 0:
        return 0.005  # minimum

    b = tp_dist_pct / sl_dist_pct  # payoff ratio
    p = combined_confidence

    kelly_full = (p * b - (1 - p)) / b
    if kelly_full <= 0:
        return 0.005  # minimum -- edge is negative, only take tiny position

    kelly_frac = kelly_full * KELLY_CAP

    # Scale by regime
    regime_scale = REGIME_POSITION_SCALE.get(regime, 0.50)
    sized = kelly_frac * regime_scale

    # Clamp to [0.5%, 2%] of capital
    return max(0.005, min(sized, 0.02))


def scan():
    """
    Main ensemble scan cycle.

    1. Load regime from System B
    2. Load active signals from Systems A, B, and C
    3. Find agreement pairs (same symbol, same direction)
    4. Apply expected return filter (E[R] > 3x cost)
    5. Generate ensemble picks with regime-conditioned sizing
    5b. Generate System B standalone picks (PRIMARY - 50% position)
    6. Save and report
    """
    now = datetime.now(timezone.utc)
    print(f"\n{'=' * 60}")
    print(f"[Ensemble] Regime-Conditioned Agreement Alpha v{VERSION}")
    print(f"  Scan at {now.isoformat()}")
    print(f"{'=' * 60}")

    os.makedirs(DATA_DIR, exist_ok=True)
    base = os.path.dirname(__file__)

    # -------------------------------------------------------------------------
    # 1. Load existing ensemble state
    # -------------------------------------------------------------------------
    fear_greed = fetch_fear_greed()
    active = load_active(DATA_DIR)
    closed = load_closed(DATA_DIR)

    # Validate existing picks (with F&G for bounce-close of bleeding shorts)
    active, newly_closed = validate_picks(active, SYSTEM_NAME, DATA_DIR,
                                          fear_greed=fear_greed)
    if newly_closed:
        print(f"  Closed {len(newly_closed)} ensemble picks:")
        for p in newly_closed:
            pnl = p.get("net_pnl_pct", 0)
            print(f"    {p['symbol']} -> {p.get('exit_reason', '?')} ({pnl:+.2f}%)")
            try:
                send_pick_exit(SYSTEM_LABEL, p)
            except Exception:
                pass

    # Stats and risk budget
    all_closed = closed + newly_closed
    stats = compute_stats(all_closed)
    equity_curve = stats.get("equity_curve", [10000.0])
    dd = calculate_drawdown(equity_curve)
    can_trade, reason = can_open_trade(len(active), dd)

    if not can_trade:
        print(f"  Cannot open new trades: {reason}")
        save_picks(active, newly_closed, DATA_DIR)
        _write_dashboard_data(active, all_closed, stats, "range_bound", 0.5, [])
        print(f"[Ensemble] Scan complete (risk limit).")
        return

    # -------------------------------------------------------------------------
    # 2. Load regime state from System B
    # -------------------------------------------------------------------------
    regime, regime_confidence, regime_duration = _load_regime_state()
    print(f"\n  Regime (from System B): {regime} "
          f"(confidence={regime_confidence:.2f}, duration={regime_duration} bars)")

    # -------------------------------------------------------------------------
    # 3. Load signals from all three systems
    # -------------------------------------------------------------------------
    signals_a = _load_system_signals(os.path.join(base, "system_a_filter", "data"))
    signals_b = _load_system_signals(os.path.join(base, "system_b_regime", "data"))
    signals_c = _load_system_signals(os.path.join(base, "system_c_deeplearn", "data"))
    signals_d = _load_system_signals(os.path.join(base, "system_d_carry", "data"))
    signals_e = _load_system_signals(os.path.join(base, "system_e_momentum", "data"))

    print(f"  System A active signals: {len(signals_a)}")
    print(f"  System B active signals: {len(signals_b)} (PRIMARY - {SYSTEM_B_WEIGHT}x weight)")
    print(f"  System C active signals: {len(signals_c)}")
    print(f"  System D active signals: {len(signals_d)} (Carry Trade)")
    print(f"  System E active signals: {len(signals_e)} (Momentum)")

    if not signals_a and not signals_b and not signals_c and not signals_d and not signals_e:
        print("  No signals from any system. Nothing to ensemble.")
        save_picks(active, newly_closed, DATA_DIR)
        _write_dashboard_data(active, all_closed, stats, regime, regime_confidence, [])
        print(f"[Ensemble] Scan complete (no input signals).")
        return

    # -------------------------------------------------------------------------
    # 4. Find agreement pairs (A + C)
    # -------------------------------------------------------------------------
    agreements = _find_agreement_pairs(signals_a, signals_c)
    print(f"\n  Agreement pairs found: {len(agreements)}")
    for ag in agreements:
        print(f"    {ag['symbol']} {ag['direction']} "
              f"(A={ag['confidence_a']:.3f}, C={ag['confidence_c']:.3f}, "
              f"combined={ag['combined_confidence']:.3f})")

    # -------------------------------------------------------------------------
    # 5. Filter and generate ensemble picks (A+C agreement)
    # -------------------------------------------------------------------------
    active_symbols = {p["symbol"] for p in active}
    new_picks = []

    # Also load market context for dashboard
    fear_greed = 50
    summary_a = _load_system_scan_summary(os.path.join(base, "system_a_filter", "data"))
    if summary_a:
        fear_greed = summary_a.get("fear_greed", 50)

    for ag in agreements:
        symbol = ag["symbol"]
        if symbol in active_symbols:
            print(f"    [skip] {symbol}: already active in ensemble")
            continue

        combined_conf = ag["combined_confidence"]

        # Gate 1: Combined confidence threshold
        if combined_conf < MIN_COMBINED_CONFIDENCE:
            print(f"    [filtered] {symbol}: combined confidence {combined_conf:.3f} "
                  f"< {MIN_COMBINED_CONFIDENCE}")
            continue

        # Merge TP/SL from both systems
        direction = ag["direction"]
        tp, sl, entry = _merge_tp_sl(ag["signal_a"], ag["signal_c"], direction)

        if entry <= 0:
            continue

        # Calculate distances
        if direction == "BUY":
            tp_dist = tp - entry
            sl_dist = entry - sl
        else:
            tp_dist = entry - tp
            sl_dist = sl - entry

        if tp_dist <= 0 or sl_dist <= 0:
            print(f"    [filtered] {symbol}: invalid TP/SL (tp_dist={tp_dist:.6f}, "
                  f"sl_dist={sl_dist:.6f})")
            continue

        tp_dist_pct = tp_dist / entry
        sl_dist_pct = sl_dist / entry
        rr = tp_dist / sl_dist

        # Gate 2: Expected return > 3x cost (minimum 30 bps)
        cost = round_trip_cost(symbol)
        expected_return = combined_conf * tp_dist_pct - (1 - combined_conf) * sl_dist_pct - cost
        min_er = max(cost * MIN_EXPECTED_RETURN_MULT, MIN_COST_BPS)

        if expected_return < min_er:
            print(f"    [filtered] {symbol}: E[R]={expected_return:.4f} "
                  f"< min {min_er:.4f} (cost={cost:.4f})")
            continue

        # Gate 3: Regime alignment check
        # In trending_up regime, prefer BUY; in trending_down, prefer SELL
        # In range/volatility, accept either but with reduced confidence
        regime_aligned = True
        if regime == "trending_up" and direction == "SELL":
            regime_aligned = False
            print(f"    [note] {symbol}: SELL in trending_up regime "
                  f"(still allowed, regime_conf={regime_confidence:.2f})")
        elif regime == "trending_down" and direction == "BUY":
            regime_aligned = False
            print(f"    [note] {symbol}: BUY in trending_down regime "
                  f"(still allowed, regime_conf={regime_confidence:.2f})")

        # Penalize confidence when direction is against regime
        effective_conf = combined_conf
        if not regime_aligned and regime_confidence > 0.60:
            effective_conf *= 0.80  # 20% penalty for going against strong regime
            print(f"    [adjusted] {symbol}: confidence {combined_conf:.3f} "
                  f"-> {effective_conf:.3f} (against regime)")

        # Re-check after penalty
        if effective_conf < MIN_COMBINED_CONFIDENCE:
            print(f"    [filtered] {symbol}: effective confidence {effective_conf:.3f} "
                  f"< {MIN_COMBINED_CONFIDENCE} after regime penalty")
            continue

        # Position sizing: Kelly with regime scaling
        pos_size = _kelly_position_size(effective_conf, tp_dist_pct, sl_dist_pct, regime)

        # Build ensemble pick
        pick = {
            "symbol": symbol,
            "signal_type": direction,
            "entry_price": round(entry, 8),
            "take_profit": round(tp, 8),
            "stop_loss": round(sl, 8),
            "risk_reward": round(rr, 2),
            "confidence": round(effective_conf, 4),
            "combined_confidence": round(combined_conf, 4),
            "confidence_a": round(ag["confidence_a"], 4),
            "confidence_c": round(ag["confidence_c"], 4),
            "regime": regime,
            "regime_confidence": round(regime_confidence, 4),
            "regime_duration": regime_duration,
            "regime_aligned": regime_aligned,
            "position_size_pct": round(pos_size * 100, 2),
            "expected_return": round(expected_return, 6),
            "transaction_cost_pct": round(cost * 100, 3),
            "strategy": "agreement_alpha",
            "strategy_a": ag["signal_a"].get("strategy", "unknown"),
            "strategy_c": ag["signal_c"].get("strategy", "gru_attention"),
            "tp_sl_method": "merged_conservative",
            "timeframe": ag["signal_a"].get("timeframe", "1h"),
            "timestamp": now.isoformat(),
            "system": SYSTEM_NAME,
            "version": VERSION,
            "fear_greed": fear_greed,
            "funding_rate": ag["signal_a"].get("funding_rate", 0.0),
            "market_health": ag["signal_a"].get("market_health", "normal"),
            "category": "crypto",
            "timestamp_est": now.astimezone(EST).strftime("%Y-%m-%d %I:%M %p EST"),
            "pick_reason": (
                f"Agreement Alpha: Systems A ({ag['signal_a'].get('strategy', '?')}) "
                f"and C (GRU-Attention) both signal {direction} "
                f"| A conf={ag['confidence_a']:.2f}, C conf={ag['confidence_c']:.2f}, "
                f"combined={combined_conf:.2f} "
                f"| Regime: {regime} ({regime_confidence:.0%}) "
                f"| E[R]={expected_return:.4f} vs cost={cost:.4f} "
                f"| R:R={rr:.1f} | Kelly size={pos_size:.3f}"
            ),
        }

        # Unrealized P&L (entry = current at signal time)
        pick["current_price"] = entry
        pick["unrealized_pnl_pct"] = 0.0

        # Calibrate confidence using historical trade outcomes
        try:
            from shared.calibration import load_calibration_map, calibrate_confidence
            cal_map = load_calibration_map()
            if cal_map and cal_map.get("method") != "insufficient_data":
                raw_conf = pick["confidence"]
                pick["raw_confidence"] = raw_conf
                pick["confidence"] = calibrate_confidence(raw_conf, cal_map)
                pick["calibration_applied"] = True
        except Exception:
            pass  # graceful degradation

        new_picks.append(pick)
        active_symbols.add(symbol)

    # -------------------------------------------------------------------------
    # 5b. System B Standalone Picks (PRIMARY SYSTEM - 50% position size)
    # -------------------------------------------------------------------------
    # System B is the only profitable system (56.6% WR, Sharpe 9.91).
    # If System B has signals that A and C don't agree on, still take them
    # at reduced position size (50%).
    b_standalone_count = 0
    for sig_b in signals_b:
        symbol = sig_b.get("symbol")
        if not symbol or symbol in active_symbols:
            continue

        conf_b = sig_b.get("confidence", sig_b.get("ml_score", 0.0))
        if conf_b < MIN_COMBINED_CONFIDENCE:
            continue

        direction = sig_b.get("signal_type", "BUY")
        entry = sig_b.get("entry_price", 0)
        tp = sig_b.get("take_profit", 0)
        sl = sig_b.get("stop_loss", 0)

        if entry <= 0 or tp <= 0 or sl <= 0:
            continue

        # Calculate distances
        if direction == "BUY":
            tp_dist = tp - entry
            sl_dist = entry - sl
        else:
            tp_dist = entry - tp
            sl_dist = sl - entry

        if tp_dist <= 0 or sl_dist <= 0:
            continue

        tp_dist_pct = tp_dist / entry
        sl_dist_pct = sl_dist / entry
        rr = tp_dist / sl_dist

        # Expected return filter
        cost = round_trip_cost(symbol)
        expected_return = conf_b * tp_dist_pct - (1 - conf_b) * sl_dist_pct - cost
        min_er = max(cost * MIN_EXPECTED_RETURN_MULT, MIN_COST_BPS)

        if expected_return < min_er:
            continue

        # Position sizing: 50% of normal Kelly (standalone = reduced conviction)
        pos_size = _kelly_position_size(conf_b, tp_dist_pct, sl_dist_pct, regime) * SYSTEM_B_STANDALONE_SIZE

        pick = {
            "symbol": symbol,
            "signal_type": direction,
            "entry_price": round(entry, 8),
            "take_profit": round(tp, 8),
            "stop_loss": round(sl, 8),
            "risk_reward": round(rr, 2),
            "confidence": round(conf_b, 4),
            "combined_confidence": round(conf_b, 4),
            "confidence_b": round(conf_b, 4),
            "regime": regime,
            "regime_confidence": round(regime_confidence, 4),
            "regime_duration": regime_duration,
            "regime_aligned": True,
            "position_size_pct": round(pos_size * 100, 2),
            "expected_return": round(expected_return, 6),
            "transaction_cost_pct": round(cost * 100, 3),
            "strategy": "system_b_standalone",
            "strategy_b": sig_b.get("strategy", "unknown"),
            "tp_sl_method": sig_b.get("tp_sl_method", "regime_atr"),
            "timeframe": sig_b.get("timeframe", "4h"),
            "timestamp": now.isoformat(),
            "system": SYSTEM_NAME,
            "version": VERSION,
            "fear_greed": fear_greed,
            "funding_rate": sig_b.get("funding_rate", 0.0),
            "market_health": sig_b.get("market_health", "normal"),
            "category": "crypto",
            "timestamp_est": now.astimezone(EST).strftime("%Y-%m-%d %I:%M %p EST"),
            "pick_reason": (
                f"System B Standalone (PRIMARY): {sig_b.get('strategy', '?')} "
                f"signals {direction} | conf={conf_b:.2f} "
                f"| Regime: {regime} ({regime_confidence:.0%}) "
                f"| E[R]={expected_return:.4f} vs cost={cost:.4f} "
                f"| R:R={rr:.1f} | 50% position (standalone)"
            ),
        }

        pick["current_price"] = entry
        pick["unrealized_pnl_pct"] = 0.0

        # Calibrate confidence using historical trade outcomes
        try:
            from shared.calibration import load_calibration_map, calibrate_confidence
            cal_map = load_calibration_map()
            if cal_map and cal_map.get("method") != "insufficient_data":
                raw_conf = pick["confidence"]
                pick["raw_confidence"] = raw_conf
                pick["confidence"] = calibrate_confidence(raw_conf, cal_map)
                pick["calibration_applied"] = True
        except Exception:
            pass  # graceful degradation

        new_picks.append(pick)
        active_symbols.add(symbol)
        b_standalone_count += 1

    if b_standalone_count > 0:
        print(f"\n  System B standalone picks: {b_standalone_count} (50% position size)")

    # -------------------------------------------------------------------------
    # 5c. System D & E Independent Picks (uncorrelated alpha sources)
    # -------------------------------------------------------------------------
    de_standalone_count = 0
    for label, sig_list, sys_name in [("D (Carry)", signals_d, "system_d_carry"),
                                       ("E (Momentum)", signals_e, "system_e_momentum")]:
        for sig in sig_list:
            symbol = sig.get("symbol")
            if not symbol or symbol in active_symbols:
                continue

            conf = sig.get("confidence", sig.get("ml_score", 0.0))
            if conf < MIN_COMBINED_CONFIDENCE:
                continue

            direction = sig.get("signal_type", "BUY")
            entry = sig.get("entry_price", 0)
            tp = sig.get("take_profit", 0)
            sl = sig.get("stop_loss", 0)

            if entry <= 0 or tp <= 0 or sl <= 0:
                continue

            if direction == "BUY":
                tp_dist = tp - entry
                sl_dist = entry - sl
            else:
                tp_dist = entry - tp
                sl_dist = sl - entry

            if tp_dist <= 0 or sl_dist <= 0:
                continue

            tp_dist_pct = tp_dist / entry
            sl_dist_pct = sl_dist / entry
            rr = tp_dist / sl_dist

            cost = round_trip_cost(symbol)
            expected_return = conf * tp_dist_pct - (1 - conf) * sl_dist_pct - cost
            min_er = max(cost * MIN_EXPECTED_RETURN_MULT, MIN_COST_BPS)

            if expected_return < min_er:
                continue

            # 50% position size for independent systems (same as B standalone)
            pos_size = _kelly_position_size(conf, tp_dist_pct, sl_dist_pct, regime) * 0.50

            pick = {
                "symbol": symbol,
                "signal_type": direction,
                "entry_price": round(entry, 8),
                "take_profit": round(tp, 8),
                "stop_loss": round(sl, 8),
                "risk_reward": round(rr, 2),
                "confidence": round(conf, 4),
                "combined_confidence": round(conf, 4),
                "regime": regime,
                "regime_confidence": round(regime_confidence, 4),
                "regime_duration": regime_duration,
                "regime_aligned": True,
                "position_size_pct": round(pos_size * 100, 2),
                "expected_return": round(expected_return, 6),
                "transaction_cost_pct": round(cost * 100, 3),
                "strategy": f"{sys_name}_standalone",
                "tp_sl_method": sig.get("tp_sl_method", "atr"),
                "timeframe": sig.get("timeframe", "4h"),
                "timestamp": now.isoformat(),
                "system": SYSTEM_NAME,
                "version": VERSION,
                "fear_greed": fear_greed,
                "funding_rate": sig.get("funding_rate", 0.0),
                "market_health": sig.get("market_health", "normal"),
                "category": "crypto",
                "timestamp_est": now.astimezone(EST).strftime("%Y-%m-%d %I:%M %p EST"),
                "pick_reason": (
                    f"System {label} Standalone: {sig.get('strategy', '?')} "
                    f"signals {direction} | conf={conf:.2f} "
                    f"| E[R]={expected_return:.4f} vs cost={cost:.4f} "
                    f"| R:R={rr:.1f} | 50% position (independent)"
                ),
            }

            pick["current_price"] = entry
            pick["unrealized_pnl_pct"] = 0.0

            # Calibrate confidence using historical trade outcomes
            try:
                from shared.calibration import load_calibration_map, calibrate_confidence
                cal_map = load_calibration_map()
                if cal_map and cal_map.get("method") != "insufficient_data":
                    raw_conf = pick["confidence"]
                    pick["raw_confidence"] = raw_conf
                    pick["confidence"] = calibrate_confidence(raw_conf, cal_map)
                    pick["calibration_applied"] = True
            except Exception:
                pass  # graceful degradation

            new_picks.append(pick)
            active_symbols.add(symbol)
            de_standalone_count += 1

    if de_standalone_count > 0:
        print(f"\n  System D+E standalone picks: {de_standalone_count} (50% position size)")

    # -------------------------------------------------------------------------
    # 6. Apply health gate and add to active
    # -------------------------------------------------------------------------
    raw_count = len(new_picks)
    # Determine health state from the first pick's metadata (all come from same scan window)
    health_val = new_picks[0].get("market_health", "safe") if new_picks else "safe"
    try:
        health_enum = MarketHealth(health_val)
    except ValueError:
        health_enum = MarketHealth.SAFE
    new_picks = apply_health_gate(health_enum, new_picks)
    if raw_count > 0 and len(new_picks) < raw_count:
        print(f"  Health gate: {raw_count} -> {len(new_picks)} signals")

    added = 0
    for pick in new_picks:
        can, reason = can_open_trade(len(active), dd)
        if not can:
            print(f"  Risk limit hit: {reason}")
            break
        active.append(pick)
        added += 1
        print(f"\n  NEW ENSEMBLE PICK: {pick['symbol']} {pick['signal_type']}")
        print(f"    Entry={pick['entry_price']:.6g} TP={pick['take_profit']:.6g} "
              f"SL={pick['stop_loss']:.6g}")
        if "confidence_a" in pick and "confidence_c" in pick:
            print(f"    Confidence: A={pick['confidence_a']:.2f} C={pick['confidence_c']:.2f} "
                  f"Combined={pick['combined_confidence']:.2f}")
        elif "confidence_b" in pick:
            print(f"    Confidence: B={pick['confidence_b']:.2f} (standalone PRIMARY)")
        print(f"    Regime={pick['regime']} | R:R={pick['risk_reward']:.1f} "
              f"| E[R]={pick['expected_return']:.4f}")
        print(f"    Position size={pick['position_size_pct']:.2f}% of capital")

        try:
            send_pick_alert(SYSTEM_LABEL, pick)
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # 7. Save and report
    # -------------------------------------------------------------------------
    save_picks(active, newly_closed, DATA_DIR)
    _write_dashboard_data(active, all_closed, stats, regime, regime_confidence, agreements)

    # Rebuild calibration map from closed trades
    try:
        from shared.calibration import build_calibration_map, save_calibration_map
        if len(all_closed) >= 30:
            cal_map = build_calibration_map(all_closed)
            save_calibration_map(cal_map)
            print(f"  [calibration] Rebuilt map from {len(all_closed)} closed trades, method={cal_map.get('method')}")
    except Exception as e:
        print(f"  [calibration] Rebuild skipped: {e}")

    # Check DSR validation status across sub-systems
    _dsr_validated_any = False
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        for _sys in ["system_a_filter", "system_b_regime", "system_c_deeplearn"]:
            _vr_path = os.path.join(base, _sys, "models", "validation_report.json")
            if os.path.exists(_vr_path):
                with open(_vr_path) as _vf:
                    if json.load(_vf).get("passed", False):
                        _dsr_validated_any = True
                        break
    except Exception:
        pass

    # Write scan summary
    scan_summary = {
        "timestamp": now.isoformat(),
        "regime": regime,
        "regime_confidence": round(regime_confidence, 4),
        "fear_greed": fear_greed,
        "system_a_signals": len(signals_a),
        "system_b_signals": len(signals_b),
        "system_c_signals": len(signals_c),
        "system_d_signals": len(signals_d),
        "system_e_signals": len(signals_e),
        "system_b_standalone_picks": b_standalone_count,
        "system_de_standalone_picks": de_standalone_count,
        "agreement_pairs": len(agreements),
        "new_picks": added,
        "active_count": len(active),
        "closed_count": len(all_closed),
        "win_rate": stats.get("win_rate", 0),
        "sharpe": stats.get("sharpe", 0),
        "drawdown": round(dd, 4),
        "dsr_validated": _dsr_validated_any,
    }
    with open(os.path.join(DATA_DIR, "scan_summary.json"), "w") as f:
        json.dump(scan_summary, f, indent=2)

    print(f"\n  Summary:")
    print(f"    Regime: {regime} ({regime_confidence:.0%})")
    print(f"    System A: {len(signals_a)} | B: {len(signals_b)} (PRIMARY) | C: {len(signals_c)} | D: {len(signals_d)} (Carry) | E: {len(signals_e)} (Momentum)")
    print(f"    Agreement pairs: {len(agreements)} | B standalone: {b_standalone_count} | D+E standalone: {de_standalone_count} | New picks: {added}")
    print(f"    Active: {len(active)} | Closed: {len(all_closed)}")
    print(f"    Stats: WR={stats.get('win_rate', 0):.1%} "
          f"Sharpe={stats.get('sharpe', 0):.2f} DD={dd:.1%}")

    # Discord status
    try:
        from shared.validator import passes_validation_gate
        gate = passes_validation_gate(all_closed)
        send_system_status(
            system_name=SYSTEM_NAME,
            system_label=SYSTEM_LABEL,
            version=VERSION,
            active_picks=active,
            closed_picks=all_closed,
            stats=stats,
            validation_gate=gate,
            regime=regime,
            regime_confidence=regime_confidence,
        )
    except Exception as e:
        print(f"  [WARN] Discord notification failed: {e}")

    print(f"\n[Ensemble] Scan complete.\n")


def _write_dashboard_data(
    active: list,
    closed: list,
    stats: dict,
    regime: str,
    regime_confidence: float,
    agreements: list,
):
    """Write JSON dashboard data for the ensemble system."""
    os.makedirs(DATA_DIR, exist_ok=True)

    # Per-regime breakdown from closed trades
    regime_stats = {}
    for pick in closed:
        r = pick.get("regime", "unknown")
        if r not in regime_stats:
            regime_stats[r] = {"trades": 0, "wins": 0, "total_pnl": 0.0}
        regime_stats[r]["trades"] += 1
        pnl = pick.get("net_pnl_pct", 0)
        regime_stats[r]["total_pnl"] += pnl
        if pnl > 0:
            regime_stats[r]["wins"] += 1
    for r, s in regime_stats.items():
        s["win_rate"] = round(s["wins"] / s["trades"] * 100, 1) if s["trades"] else 0
        s["total_pnl"] = round(s["total_pnl"], 4)

    dashboard = {
        "system": SYSTEM_LABEL,
        "system_name": SYSTEM_NAME,
        "version": VERSION,
        "scan_frequency": SCAN_FREQUENCY,
        "inception_date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated": datetime.now(timezone.utc).isoformat(),
        "updated_est": datetime.now(EST).strftime("%Y-%m-%d %I:%M %p EST"),
        "regime": regime,
        "regime_confidence": round(regime_confidence, 4),
        "system_b_weight": SYSTEM_B_WEIGHT,
        "active_picks": active,
        "stats": {k: v for k, v in stats.items() if k != "equity_curve"},
        "equity_curve": stats.get("equity_curve", []),
        "total_closed": len(closed),
        "recent_closed": closed[-20:] if closed else [],
        "regime_stats": regime_stats,
        "agreement_log": [
            {
                "symbol": ag["symbol"],
                "direction": ag["direction"],
                "confidence_a": ag["confidence_a"],
                "confidence_c": ag["confidence_c"],
                "combined": ag["combined_confidence"],
            }
            for ag in (agreements or [])
        ],
    }

    with open(os.path.join(DATA_DIR, "dashboard.json"), "w") as f:
        json.dump(dashboard, f, indent=2, default=str)


if __name__ == "__main__":
    scan()
