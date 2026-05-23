"""
Approach B: ML-Enhanced Breakout Scanner
S/R breakout detection + LightGBM confidence filter.
Target: 50-150 high-conviction trades/year on 4h timeframe.

Candidates are generated via Williams fractal + volume profile + round-number
S/R detection (same engine as Approach A), then each breakout event has 10
features extracted and scored by a heuristic model (bootstrap) that will
auto-upgrade to LightGBM once 50+ labeled outcomes accumulate.

Run: python -m breakout_arena.approach_b_ml_breakout.scanner [--dry-run]
"""
import os
import sys
import json
import time
import logging
import argparse
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from typing import Optional

# ---------------------------------------------------------------------------
# Path setup -- allow running from repo root
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from ml_battleground.shared.data_fetcher import (
    fetch_ohlcv, fetch_single, fetch_fear_greed, fetch_funding_rates,
)
from ml_battleground.shared.indicators import (
    atr, ema, sma, rsi, bollinger_bands,
)
from ml_battleground.shared.sr_engine import (
    SRLevel, detect_sr_levels, nearest_support, nearest_resistance,
    sr_based_tp_sl,
)
from ml_battleground.shared.risk_manager import (
    can_open_trade, calculate_drawdown, position_size,
)
from ml_battleground.shared.cost_model import round_trip_cost
from ml_battleground.shared.performance import compute_stats

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SYSTEM_NAME = "approach_b_ml_breakout"
VERSION = "1.0.0"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
EST = timezone(timedelta(hours=-5))

# Scan parameters
TIMEFRAME = "4h"
CANDLE_LIMIT = 500
PAIRS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
         "ADAUSDT", "DOTUSDT", "AVAXUSDT", "LINKUSDT"]

# Breakout filters (intentionally looser than Approach A -- ML decides)
VOLUME_MULT_THRESHOLD = 1.5       # 1.5x avg volume (A uses 2.0x)
FRESHNESS_BARS = 3                # breakout within last N bars

# ML threshold
ML_THRESHOLD = 0.65

# TP/SL
MIN_RR = 1.5
TP_ATR_MULT = 3.0
SL_ATR_MULT = 1.0
TRAILING_ACTIVATE_PCT = 0.02      # +2% to activate
TRAILING_DISTANCE_PCT = 0.03      # 3% from HWM
MAX_HOLD_HOURS = 72               # 3 days max hold — auto-expire stale picks

# Cost
BTC_COST = 0.0025                 # 0.25% round-trip

# Equity
INITIAL_EQUITY = 10000.0

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Approach-B] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _col(df: pd.DataFrame, name: str) -> pd.Series:
    """Case-insensitive column accessor."""
    if name in df.columns:
        return df[name]
    lower = name.lower()
    if lower in df.columns:
        return df[lower]
    raise KeyError(f"Column {name} not found in {list(df.columns)}")


# ---------------------------------------------------------------------------
# S/R + Breakout Detection  (mirrors Approach A, looser filters)
# ---------------------------------------------------------------------------

@dataclass
class BreakoutCandidate:
    symbol: str
    signal_type: str              # "BUY" or "SELL"
    entry_price: float
    broken_level: SRLevel
    bar_index: int                # index in df where breakout occurred
    timestamp: str


def detect_breakouts(
    df: pd.DataFrame,
    symbol: str,
    sr_levels: list[SRLevel],
) -> list[BreakoutCandidate]:
    """
    Detect S/R breakout candidates with loose filters.
    1. Close crosses an S/R level (fresh break within FRESHNESS_BARS)
    2. Volume > VOLUME_MULT_THRESHOLD x SMA(20) volume
    No RSI filter -- ML decides conviction.
    """
    if len(df) < 50 or not sr_levels:
        return []

    close = _col(df, "Close").values
    volume = _col(df, "Volume").values
    high = _col(df, "High").values
    low = _col(df, "Low").values

    vol_sma = pd.Series(volume).rolling(20).mean().values

    candidates = []
    n = len(df)

    for level in sr_levels:
        lp = level.price
        # Check last FRESHNESS_BARS for a fresh cross
        for offset in range(FRESHNESS_BARS):
            i = n - 1 - offset
            if i < 1:
                continue

            prev_close = close[i - 1]
            curr_close = close[i]

            # Volume check
            if np.isnan(vol_sma[i]) or vol_sma[i] <= 0:
                continue
            vol_ratio = volume[i] / vol_sma[i]
            if vol_ratio < VOLUME_MULT_THRESHOLD:
                continue

            # Bullish breakout: close crosses above resistance
            if prev_close <= lp < curr_close and level.level_type == "resistance":
                ts = str(df.index[i]) if hasattr(df.index[i], "isoformat") else str(df.index[i])
                candidates.append(BreakoutCandidate(
                    symbol=symbol,
                    signal_type="BUY",
                    entry_price=float(curr_close),
                    broken_level=level,
                    bar_index=i,
                    timestamp=ts,
                ))
                break  # one breakout per level

            # Bearish breakout: close crosses below support
            if prev_close >= lp > curr_close and level.level_type == "support":
                ts = str(df.index[i]) if hasattr(df.index[i], "isoformat") else str(df.index[i])
                candidates.append(BreakoutCandidate(
                    symbol=symbol,
                    signal_type="SELL",
                    entry_price=float(curr_close),
                    broken_level=level,
                    bar_index=i,
                    timestamp=ts,
                ))
                break

    return candidates


# ---------------------------------------------------------------------------
# Feature Extraction  (10 features per breakout event)
# ---------------------------------------------------------------------------

def extract_features(
    df: pd.DataFrame,
    candidate: BreakoutCandidate,
    fear_greed: int = 50,
    funding_rate: float = 0.0,
) -> dict:
    """
    Extract 10 ML features for a breakout candidate.

    1. atr_rank         -- ATR(14) percentile over 90 bars (0-1)
    2. volume_spike     -- current volume / SMA(20) volume
    3. sr_strength      -- strength score of the broken level
    4. sr_touches       -- number of times level was tested before break
    5. trend_strength   -- EMA(9) - EMA(50), normalized by ATR
    6. breakout_bar_size -- (close - open) / ATR of the breakout bar
    7. prior_squeeze    -- BB width percentile over 50 bars (lower = more compressed)
    8. funding_rate     -- Binance futures funding rate (or 0)
    9. fear_greed_norm  -- Fear & Greed / 100
    10. distance_from_level -- (close - level) / ATR
    """
    close = _col(df, "Close")
    high = _col(df, "High")
    low = _col(df, "Low")
    volume = _col(df, "Volume")
    open_ = _col(df, "Open")

    i = candidate.bar_index
    atr_series = atr(high, low, close, period=14)
    atr_now = float(atr_series.iloc[i]) if not np.isnan(atr_series.iloc[i]) else float(close.iloc[i]) * 0.02

    # 1. ATR rank (percentile over 90 bars)
    lookback = min(90, i)
    if lookback > 1 and atr_now > 0:
        atr_window = atr_series.iloc[max(0, i - lookback):i + 1].dropna().values
        atr_rank = float(np.searchsorted(np.sort(atr_window), atr_now) / len(atr_window))
    else:
        atr_rank = 0.5

    # 2. Volume spike
    vol_sma_20 = float(volume.iloc[max(0, i - 19):i + 1].mean())
    volume_spike = float(volume.iloc[i]) / vol_sma_20 if vol_sma_20 > 0 else 1.0

    # 3. SR strength
    sr_strength = candidate.broken_level.strength

    # 4. SR touches
    sr_touches = candidate.broken_level.touches

    # 5. Trend strength: (EMA9 - EMA50) / ATR
    ema9 = ema(close, 9)
    ema50 = ema(close, 50)
    trend_diff = float(ema9.iloc[i] - ema50.iloc[i])
    trend_strength = trend_diff / atr_now if atr_now > 0 else 0.0

    # 6. Breakout bar size: (close - open) / ATR
    bar_body = float(close.iloc[i] - open_.iloc[i])
    breakout_bar_size = bar_body / atr_now if atr_now > 0 else 0.0

    # 7. Prior squeeze: BB width percentile over 50 bars
    _, _, _, bb_width, _ = bollinger_bands(close, period=20, std_mult=2.0)
    squeeze_lookback = min(50, i)
    if squeeze_lookback > 1:
        bb_window = bb_width.iloc[max(0, i - squeeze_lookback):i + 1].dropna().values
        bb_now = float(bb_width.iloc[i]) if not np.isnan(bb_width.iloc[i]) else 0.5
        prior_squeeze = float(np.searchsorted(np.sort(bb_window), bb_now) / len(bb_window))
    else:
        prior_squeeze = 0.5

    # 8. Funding rate
    funding_rate_val = funding_rate

    # 9. Fear & Greed normalized
    fear_greed_norm = fear_greed / 100.0

    # 10. Distance from level: (close - level) / ATR
    dist = float(close.iloc[i]) - candidate.broken_level.price
    if candidate.signal_type == "SELL":
        dist = -dist  # positive = favorable distance
    distance_from_level = dist / atr_now if atr_now > 0 else 0.0

    return {
        "atr_rank": round(atr_rank, 4),
        "volume_spike": round(volume_spike, 4),
        "sr_strength": round(sr_strength, 4),
        "sr_touches": sr_touches,
        "trend_strength": round(trend_strength, 4),
        "breakout_bar_size": round(breakout_bar_size, 4),
        "prior_squeeze": round(prior_squeeze, 4),
        "funding_rate": round(funding_rate_val, 6),
        "fear_greed_norm": round(fear_greed_norm, 4),
        "distance_from_level": round(distance_from_level, 4),
    }


# ---------------------------------------------------------------------------
# ML Model: Heuristic Bootstrap -> LightGBM
# ---------------------------------------------------------------------------

def load_ml_model():
    """Load trained LightGBM model if available."""
    model_path = os.path.join(DATA_DIR, "breakout_lgbm.joblib")
    if os.path.exists(model_path):
        try:
            import joblib
            return joblib.load(model_path)
        except Exception as e:
            log.warning(f"Failed to load LightGBM model: {e}")
    return None


def heuristic_ml_score(features: dict, signal_type: str) -> float:
    """
    Bootstrap heuristic until 50+ labeled breakouts accumulate.
    Mimics expected SHAP feature importance from research:
      ATR expansion > Volume spike > Squeeze > SR strength > Trend alignment.
    """
    score = 0.5

    # ATR expansion is the most important predictor (SHAP finding)
    if features["atr_rank"] > 0.7:
        score += 0.15
    elif features["atr_rank"] > 0.5:
        score += 0.05

    # Volume spike matters
    if features["volume_spike"] > 3.0:
        score += 0.10
    elif features["volume_spike"] > 2.0:
        score += 0.05

    # Strong levels break more decisively
    if features["sr_strength"] > 5.0:
        score += 0.05
    if features["sr_touches"] >= 3:
        score += 0.05

    # Trend alignment
    if features["trend_strength"] > 0 and signal_type == "BUY":
        score += 0.05
    elif features["trend_strength"] < 0 and signal_type == "SELL":
        score += 0.05

    # Squeeze breakout (compressed -> expansion)
    if features["prior_squeeze"] < 0.2:
        score += 0.10

    # Penalty for weak breakout (barely past level)
    if features["distance_from_level"] < 0.5:
        score -= 0.05

    # Fear/greed alignment
    if features["fear_greed_norm"] < 0.25 and signal_type == "SELL":
        score += 0.05
    elif features["fear_greed_norm"] > 0.60 and signal_type == "BUY":
        score += 0.05

    return max(0.0, min(1.0, score))


def predict_ml(features: dict, signal_type: str) -> tuple[float, str]:
    """
    Score a breakout candidate.
    Returns (score, method) where method is 'lightgbm' or 'heuristic'.
    """
    model = load_ml_model()
    if model is not None:
        try:
            feature_order = [
                "atr_rank", "volume_spike", "sr_strength", "sr_touches",
                "trend_strength", "breakout_bar_size", "prior_squeeze",
                "funding_rate", "fear_greed_norm", "distance_from_level",
            ]
            X = np.array([[features[f] for f in feature_order]])
            proba = model.predict_proba(X)[0][1]
            return float(proba), "lightgbm"
        except Exception as e:
            log.warning(f"LightGBM predict failed, falling back to heuristic: {e}")

    score = heuristic_ml_score(features, signal_type)
    return score, "heuristic"


# ---------------------------------------------------------------------------
# Auto-Training Stub
# ---------------------------------------------------------------------------

def maybe_train_model() -> Optional[str]:
    """
    Auto-train LightGBM when 50+ closed picks with features are available.
    Returns model path if trained, None otherwise.
    """
    closed_path = os.path.join(DATA_DIR, "closed_picks.json")
    if not os.path.exists(closed_path):
        return None

    try:
        with open(closed_path) as f:
            closed = json.load(f)
    except Exception:
        return None

    # Need 50+ labeled entries with features
    labeled = [p for p in closed if "features" in p and "outcome" in p]
    if len(labeled) < 50:
        log.info(f"Auto-train: {len(labeled)}/50 labeled picks -- not enough yet")
        return None

    try:
        import lightgbm as lgb
        from sklearn.model_selection import cross_val_score
        import joblib
    except ImportError:
        log.warning("LightGBM/sklearn/joblib not installed -- cannot auto-train")
        return None

    feature_order = [
        "atr_rank", "volume_spike", "sr_strength", "sr_touches",
        "trend_strength", "breakout_bar_size", "prior_squeeze",
        "funding_rate", "fear_greed_norm", "distance_from_level",
    ]

    X = np.array([[p["features"].get(f, 0) for f in feature_order] for p in labeled])
    y = np.array([1 if p["outcome"] == "win" else 0 for p in labeled])

    model = lgb.LGBMClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.05,
        min_child_samples=5,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbose=-1,
    )

    # 3-fold cross-validation
    scores = cross_val_score(model, X, y, cv=3, scoring="accuracy")
    log.info(f"Auto-train CV accuracy: {scores.mean():.3f} +/- {scores.std():.3f}")

    # Train on full data and save
    model.fit(X, y)
    model_path = os.path.join(DATA_DIR, "breakout_lgbm.joblib")
    joblib.dump(model, model_path)
    log.info(f"LightGBM model saved to {model_path} (trained on {len(labeled)} samples)")

    return model_path


# ---------------------------------------------------------------------------
# TP/SL + Trailing Stop
# ---------------------------------------------------------------------------

def compute_tp_sl(
    entry: float,
    signal_type: str,
    sr_levels: list[SRLevel],
    atr_val: float,
) -> tuple[float, float, float, str]:
    """
    Compute take-profit and stop-loss using S/R levels with ATR fallback.
    Returns (tp, sl, rr, method).
    """
    tp, sl, method = sr_based_tp_sl(
        entry_price=entry,
        levels=sr_levels,
        atr_value=atr_val,
        signal_type=signal_type,
        min_rr=MIN_RR,
        tp_atr_fallback=TP_ATR_MULT,
        sl_atr_fallback=SL_ATR_MULT,
    )

    # Calculate R:R
    if signal_type == "BUY":
        risk = entry - sl
        reward = tp - entry
    else:
        risk = sl - entry
        reward = entry - tp

    rr = reward / risk if risk > 0 else 0.0
    return round(tp, 8), round(sl, 8), round(rr, 2), method


def apply_trailing_stop(pick: dict, current_price: float) -> dict:
    """
    Apply trailing stop logic.
    Activate at +TRAILING_ACTIVATE_PCT, trail TRAILING_DISTANCE_PCT from HWM.
    """
    entry = pick["entry_price"]
    signal_type = pick.get("signal_type", "BUY")

    if signal_type == "BUY":
        pnl_pct = (current_price - entry) / entry
    else:
        pnl_pct = (entry - current_price) / entry

    hwm = pick.get("hwm", current_price)

    if signal_type == "BUY":
        hwm = max(hwm, current_price)
    else:
        hwm = min(hwm, current_price)
    pick["hwm"] = hwm

    # Activate trailing stop once we hit threshold
    if pnl_pct >= TRAILING_ACTIVATE_PCT:
        pick["trailing_active"] = True
        if signal_type == "BUY":
            trailing_sl = hwm * (1 - TRAILING_DISTANCE_PCT)
            pick["stop_loss"] = max(pick["stop_loss"], round(trailing_sl, 8))
        else:
            trailing_sl = hwm * (1 + TRAILING_DISTANCE_PCT)
            pick["stop_loss"] = min(pick["stop_loss"], round(trailing_sl, 8))

    return pick


# ---------------------------------------------------------------------------
# Position Tracking (active_picks / closed_picks / equity)
# ---------------------------------------------------------------------------

def load_active() -> list[dict]:
    path = os.path.join(DATA_DIR, "active_picks.json")
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def load_closed() -> list[dict]:
    path = os.path.join(DATA_DIR, "closed_picks.json")
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_active(picks: list[dict]):
    try:
        from alpha_engine.feed_hygiene import sanitize_active_picks
    except ImportError:
        sanitize_active_picks = lambda p, label="": p
    picks = sanitize_active_picks(picks, "breakout_arena_b")
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "active_picks.json"), "w") as f:
        json.dump(picks, f, indent=2, default=str)


def save_closed(picks: list[dict]):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "closed_picks.json"), "w") as f:
        json.dump(picks, f, indent=2, default=str)


def get_equity(closed: list[dict]) -> float:
    """Calculate current equity from closed picks."""
    equity = INITIAL_EQUITY
    for pick in closed:
        pnl_pct = pick.get("pnl_pct", 0)
        cost = pick.get("cost", BTC_COST)
        net = pnl_pct / 100.0 - cost
        # Risk 2% of equity per trade
        equity *= (1 + net * 0.02)
    return equity


def build_equity_curve(closed: list[dict]) -> list[float]:
    """Build equity curve from closed picks."""
    curve = [INITIAL_EQUITY]
    equity = INITIAL_EQUITY
    for pick in closed:
        pnl_pct = pick.get("pnl_pct", 0)
        cost = pick.get("cost", BTC_COST)
        net = pnl_pct / 100.0 - cost
        equity *= (1 + net * 0.02)
        curve.append(round(equity, 2))
    return curve


# ---------------------------------------------------------------------------
# Validate existing picks (check TP/SL hits)
# ---------------------------------------------------------------------------

def validate_active_picks(active: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Check active picks against current prices for TP/SL hits.
    Returns (still_active, newly_closed).
    """
    still_active = []
    newly_closed = []

    for pick in active:
        symbol = pick["symbol"]
        df = fetch_single(symbol, TIMEFRAME, limit=5)
        if df is None or len(df) < 1:
            # Even without a live price, enforce max-hold expiry on stale picks
            opened_at = pick.get("timestamp")
            if opened_at:
                try:
                    age_hours = (datetime.now(timezone.utc) - datetime.fromisoformat(opened_at)).total_seconds() / 3600
                    if age_hours > MAX_HOLD_HOURS:
                        pick.update({
                            "exit_price": pick["entry_price"],  # unknown exit, use entry as fallback
                            "pnl_pct": 0.0,
                            "cost": round_trip_cost(symbol),
                            "net_pnl_pct": round(-round_trip_cost(symbol) * 100, 4),
                            "outcome": "loss",
                            "exit_reason": f"expired_{int(age_hours)}h_no_price_data",
                            "exit_time": datetime.now(timezone.utc).isoformat(),
                            "current_price": pick["entry_price"],
                        })
                        newly_closed.append(pick)
                        log.warning(f"FORCE-EXPIRED {symbol} {pick.get('signal_type','?')} "
                                    f"after {int(age_hours)}h (no price data available)")
                        continue
                except (ValueError, TypeError):
                    pass
            still_active.append(pick)
            continue

        current_price = float(_col(df, "Close").iloc[-1])
        current_high = float(_col(df, "High").iloc[-1])
        current_low = float(_col(df, "Low").iloc[-1])

        # Apply trailing stop
        pick = apply_trailing_stop(pick, current_price)

        tp = pick["take_profit"]
        sl = pick["stop_loss"]
        entry = pick["entry_price"]
        signal_type = pick.get("signal_type", "BUY")

        # Max-hold expiry — auto-close stale picks
        opened_at = pick.get("timestamp")
        if opened_at:
            try:
                age_hours = (datetime.now(timezone.utc) - datetime.fromisoformat(opened_at)).total_seconds() / 3600
                if age_hours > MAX_HOLD_HOURS:
                    if signal_type == "BUY":
                        pnl_pct = (current_price - entry) / entry * 100
                    else:
                        pnl_pct = (entry - current_price) / entry * 100
                    cost = round_trip_cost(symbol)
                    pick.update({
                        "exit_price": round(current_price, 8),
                        "pnl_pct": round(pnl_pct, 4),
                        "cost": cost,
                        "net_pnl_pct": round(pnl_pct - cost * 100, 4),
                        "outcome": "win" if pnl_pct > 0 else "loss",
                        "exit_reason": f"expired_{int(age_hours)}h",
                        "exit_time": datetime.now(timezone.utc).isoformat(),
                        "current_price": current_price,
                    })
                    newly_closed.append(pick)
                    log.info(f"EXPIRED {symbol} {signal_type} after {int(age_hours)}h: "
                             f"PnL={pnl_pct:+.2f}% (net {pick['net_pnl_pct']:+.2f}%)")
                    continue
            except (ValueError, TypeError):
                pass

        hit_tp = False
        hit_sl = False

        if signal_type == "BUY":
            hit_tp = current_high >= tp
            hit_sl = current_low <= sl
        else:
            hit_tp = current_low <= tp
            hit_sl = current_high >= sl

        if hit_tp or hit_sl:
            exit_price = tp if hit_tp else sl
            if signal_type == "BUY":
                pnl_pct = (exit_price - entry) / entry * 100
            else:
                pnl_pct = (entry - exit_price) / entry * 100

            cost = round_trip_cost(symbol)
            pick.update({
                "exit_price": round(exit_price, 8),
                "pnl_pct": round(pnl_pct, 4),
                "cost": cost,
                "net_pnl_pct": round(pnl_pct - cost * 100, 4),
                "outcome": "win" if pnl_pct > 0 else "loss",
                "exit_reason": "tp_hit" if hit_tp else "sl_hit",
                "exit_time": datetime.now(timezone.utc).isoformat(),
                "current_price": current_price,
            })
            newly_closed.append(pick)
            log.info(f"CLOSED {symbol} {signal_type}: {pick['exit_reason']} "
                     f"PnL={pnl_pct:+.2f}% (net {pick['net_pnl_pct']:+.2f}%)")
        else:
            # Update unrealized P&L
            if signal_type == "BUY":
                unrealized = (current_price - entry) / entry * 100
            else:
                unrealized = (entry - current_price) / entry * 100
            pick["current_price"] = current_price
            pick["unrealized_pnl_pct"] = round(unrealized, 4)
            still_active.append(pick)

    return still_active, newly_closed


# ---------------------------------------------------------------------------
# Dashboard Output
# ---------------------------------------------------------------------------

def write_dashboard(active: list[dict], closed: list[dict], model_status: str):
    """Write dashboard.json for UI consumption."""
    equity_curve = build_equity_curve(closed)
    equity = equity_curve[-1] if equity_curve else INITIAL_EQUITY

    wins = [p for p in closed if p.get("outcome") == "win"]
    losses = [p for p in closed if p.get("outcome") == "loss"]
    win_rate = len(wins) / len(closed) if closed else 0
    avg_win = np.mean([p["pnl_pct"] for p in wins]) if wins else 0
    avg_loss = np.mean([abs(p["pnl_pct"]) for p in losses]) if losses else 0
    total_losses = sum(abs(p["pnl_pct"]) for p in losses)
    profit_factor = (sum(p["pnl_pct"] for p in wins) / total_losses) if total_losses > 0 else (float("inf") if wins else 0)

    # Sharpe (annualized from 4h bars)
    if len(closed) >= 5:
        returns = [p.get("net_pnl_pct", 0) / 100 for p in closed]
        sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(365 * 6) if np.std(returns) > 0 else 0
    else:
        sharpe = 0.0

    dashboard = {
        "system": "ML-Enhanced Breakout (Approach B)",
        "version": VERSION,
        "timeframe": TIMEFRAME,
        "ml_threshold": ML_THRESHOLD,
        "model_status": model_status,
        "updated": datetime.now(timezone.utc).isoformat(),
        "updated_est": datetime.now(EST).strftime("%Y-%m-%d %I:%M %p EST"),
        "active_picks": active,
        "stats": {
            "total_closed": len(closed),
            "win_rate": round(win_rate, 4),
            "avg_win_pct": round(avg_win, 2),
            "avg_loss_pct": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2),
            "sharpe": round(sharpe, 2),
            "equity": round(equity, 2),
            "max_drawdown": round(calculate_drawdown(equity_curve), 4),
        },
        "equity_curve": equity_curve,
        "recent_closed": closed[-20:] if closed else [],
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "dashboard.json"), "w") as f:
        json.dump(dashboard, f, indent=2, default=str)

    log.info(f"Dashboard written: {len(active)} active, {len(closed)} closed, "
             f"equity=${equity:.2f}, WR={win_rate:.1%}")


# ---------------------------------------------------------------------------
# Main Scan
# ---------------------------------------------------------------------------

def scan(dry_run: bool = False):
    """
    Main scan cycle:
    1. Validate existing active picks (TP/SL/trailing)
    2. Fetch 4h candles for all pairs
    3. Detect S/R levels + breakout candidates
    4. Extract 10 features per candidate
    5. Score with ML model (heuristic or LightGBM)
    6. Open trades where score > ML_THRESHOLD and R:R > MIN_RR
    7. Write dashboard, attempt auto-training
    """
    now = datetime.now(timezone.utc)
    log.info(f"=== Scan started at {now.isoformat()} (dry_run={dry_run}) ===")

    # Load state
    active = load_active()
    closed = load_closed()

    # Validate existing picks
    active, newly_closed = validate_active_picks(active)
    closed.extend(newly_closed)
    if newly_closed:
        log.info(f"Closed {len(newly_closed)} picks this cycle")

    # Check drawdown circuit breaker
    equity_curve = build_equity_curve(closed)
    dd = calculate_drawdown(equity_curve)
    can_trade, reason = can_open_trade(len(active), dd)

    if not can_trade:
        log.info(f"Cannot open new trades: {reason}")
        if not dry_run:
            save_active(active)
            save_closed(closed)
            write_dashboard(active, closed, _model_status())
        return

    # Fetch market context
    fear_greed = fetch_fear_greed()
    funding_rates = fetch_funding_rates(PAIRS)
    log.info(f"Market context: F&G={fear_greed}, funding rates for {len(funding_rates)} pairs")

    # Fetch OHLCV for all pairs on 4h
    data = fetch_ohlcv(PAIRS, TIMEFRAME, CANDLE_LIMIT)
    log.info(f"Fetched {TIMEFRAME} data for {len(data)}/{len(PAIRS)} pairs")

    # Also fetch ETHUSDT for correlation context (if not already in PAIRS)
    eth_df = data.get("ETHUSDT")

    # Track active symbols to avoid duplicates
    active_symbols = {p["symbol"] for p in active}
    new_signals = []

    for symbol, df in data.items():
        if symbol in active_symbols:
            log.info(f"  [skip] {symbol}: already active")
            continue
        if len(df) < 100:
            log.info(f"  [skip] {symbol}: only {len(df)} bars (need 100)")
            continue

        # Detect S/R levels
        sr_levels = detect_sr_levels(df)
        if not sr_levels:
            continue

        # Detect breakout candidates (loose filters)
        candidates = detect_breakouts(df, symbol, sr_levels)
        if not candidates:
            continue

        log.info(f"  {symbol}: {len(candidates)} breakout candidates, {len(sr_levels)} S/R levels")

        for candidate in candidates:
            # Extract 10 features
            features = extract_features(
                df, candidate,
                fear_greed=fear_greed,
                funding_rate=funding_rates.get(symbol, 0.0),
            )

            # ML score
            ml_score, ml_method = predict_ml(features, candidate.signal_type)
            log.info(f"    {symbol} {candidate.signal_type} @ {candidate.entry_price:.2f} "
                     f"-> ML={ml_score:.3f} ({ml_method})")

            if ml_score < ML_THRESHOLD:
                log.info(f"    [filtered] ML score {ml_score:.3f} < {ML_THRESHOLD}")
                continue

            # Compute TP/SL
            atr_series = atr(_col(df, "High"), _col(df, "Low"), _col(df, "Close"))
            atr_now = float(atr_series.iloc[-1]) if len(atr_series) > 0 else candidate.entry_price * 0.02
            tp, sl, rr, tp_sl_method = compute_tp_sl(
                candidate.entry_price, candidate.signal_type, sr_levels, atr_now,
            )

            if rr < MIN_RR:
                log.info(f"    [filtered] R:R {rr:.2f} < {MIN_RR}")
                continue

            # Build pick
            cost = round_trip_cost(symbol)
            pick = {
                "symbol": symbol,
                "signal_type": candidate.signal_type,
                "entry_price": candidate.entry_price,
                "take_profit": tp,
                "stop_loss": sl,
                "risk_reward": rr,
                "tp_sl_method": tp_sl_method,
                "ml_score": round(ml_score, 4),
                "ml_method": ml_method,
                "features": features,
                "broken_level_price": candidate.broken_level.price,
                "broken_level_strength": candidate.broken_level.strength,
                "broken_level_touches": candidate.broken_level.touches,
                "broken_level_source": candidate.broken_level.source,
                "cost": cost,
                "fear_greed": fear_greed,
                "funding_rate": funding_rates.get(symbol, 0.0),
                "timestamp": now.isoformat(),
                "timestamp_est": now.astimezone(EST).strftime("%Y-%m-%d %I:%M %p EST"),
                "system": SYSTEM_NAME,
                "version": VERSION,
                "timeframe": TIMEFRAME,
                "hwm": candidate.entry_price,
                "trailing_active": False,
                "current_price": candidate.entry_price,
                "unrealized_pnl_pct": 0.0,
                "pick_reason": (
                    f"S/R breakout on {TIMEFRAME} | ML score {ml_score:.2f} ({ml_method}) "
                    f"| Level {candidate.broken_level.price:.2f} "
                    f"(str={candidate.broken_level.strength:.1f}, "
                    f"touches={candidate.broken_level.touches}) "
                    f"| R:R {rr:.1f} | TP/SL via {tp_sl_method} "
                    f"| F&G={fear_greed} | ATR_rank={features['atr_rank']:.2f} "
                    f"| Vol_spike={features['volume_spike']:.1f}x"
                ),
            }

            new_signals.append(pick)
            active_symbols.add(symbol)
            break  # one signal per symbol per scan

    # Sort by ML score, take what fits risk budget
    new_signals.sort(key=lambda s: s["ml_score"], reverse=True)

    added = 0
    for sig in new_signals:
        can, reason = can_open_trade(len(active), dd)
        if not can:
            log.info(f"  Risk budget exhausted: {reason}")
            break
        if not dry_run:
            active.append(sig)
        added += 1
        log.info(f"  {'[DRY-RUN] ' if dry_run else ''}NEW: {sig['symbol']} "
                 f"{sig['signal_type']} @ {sig['entry_price']:.2f} "
                 f"(ML:{sig['ml_score']:.2f}, R:R:{sig['risk_reward']:.1f}, "
                 f"method:{sig['ml_method']})")

    # Summary
    equity = get_equity(closed)
    log.info(f"  Active: {len(active)} | Closed: {len(closed)} | New: {added} | "
             f"Equity: ${equity:.2f} | Drawdown: {dd:.1%}")

    if not dry_run:
        save_active(active)
        save_closed(closed)

        # Attempt auto-training
        model_path = maybe_train_model()
        if model_path:
            log.info(f"Auto-trained model saved: {model_path}")

        # Write dashboard
        write_dashboard(active, closed, _model_status())

    log.info(f"=== Scan complete ===")


def _model_status() -> str:
    """Check current model status."""
    model_path = os.path.join(DATA_DIR, "breakout_lgbm.joblib")
    if os.path.exists(model_path):
        return "trained"
    return "heuristic_bootstrap"


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Approach B: ML-Enhanced Breakout Scanner"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run scan without saving picks or writing dashboard",
    )
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)
    scan(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
