"""
ALPHA_ENGINE -- Incubator Graduate Strategies
=============================================

Forward-deploys two Tier 1 backtest champions from `incubator/` to
`alpha_engine/` for live paper-trading evaluation.

Backtest provenance (`incubator/backtest_results/tiered_test_results.json`,
2026-05-08):

  * volume_weighted_candle_sequence  -- SOLUSDT WR 48.94%, Sharpe 1.67,
    max_dd 2.38%, total_return 197.4%, n=94002 trades. Tier 2 status:
    FULLY ROBUST across 1h / 4h / 1d. Best params: tp_atr_mult=1.5,
    sl_atr_mult=1.0. (See `reports/strategy_backtest_forward_ranking_2026-05-08.md`.)

  * market_structure_volume          -- All-TF Champion. Detects CHoCH /
    BOS structure shifts confirmed by volume expansion. Source impl
    `baby_strategies/market_structure_volume.py` (single-symbol class API);
    this module ports it to the multi-symbol dict API expected by the
    alpha_engine signal pipeline.

Wiring Plan (per CLAUDE.md Wire-Up Rule -- opt-in sidecar)
----------------------------------------------------------
This module is **opt-in** and not yet referenced by the production
pick-generation path. Forward-validation must show ≥4-week parity with
the backtest WR/PF before promotion.

Target callers (planned):
  * `alpha_engine/scanner.py` -- crypto branch, alongside
    `incubator_strategies` callers (e.g. `triple_supertrend`,
    `adx_momentum`). Add to the per-symbol fan-out loop after fetching
    OHLCV via the 5-mirror Binance failover chain.
  * `alpha_engine/equity_strategies.py` -- equity branch, called from
    the scoring pipeline once 4-week paper-trading validation passes.

Promotion criteria (before adding to JSON_PICK_SOURCES):
  1. ≥100 closed picks per strategy in `audit_dashboard/data/`
  2. WR within 10pp of backtest (48.9% target ± 10)
  3. PF ≥ 1.3 system-wide
  4. No commodity / FOREX leakage (CRYPTO + EQUITY only initially)

Rollback envs:
  * VWCANDLE_DISABLED=1  -- silences volume_weighted_candle_sequence
  * MSV_DISABLED=1       -- silences market_structure_volume

Schema
------
Both functions return a list of signal dicts with keys:

    symbol, direction (LONG/SHORT), strategy, asset_class (CRYPTO/EQUITY),
    category, timeframe, entry_price, stop_loss, take_profit, confidence
    (0.5 - 0.95), generated_at (ISO8601 UTC), source_system, reason,
    risk_reward.

Pure numpy / pandas. No network IO. Caller fetches OHLCV.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------- #
#  Constants & helpers
# --------------------------------------------------------------------------- #

_REQUIRED_COLS = ("open", "high", "low", "close", "volume")
_MIN_BARS = 60  # minimum bars before we attempt to fire any signal

# Heuristic: anything ending USDT / USDC / USD / BTC / ETH is crypto.
# Anything else with len <= 5 alphabetic is treated as an equity ticker.
_CRYPTO_QUOTE_SUFFIXES = ("USDT", "USDC", "USD", "BTC", "ETH", "BUSD")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _infer_asset_class(symbol: str) -> str:
    s = (symbol or "").upper()
    if any(s.endswith(suf) for suf in _CRYPTO_QUOTE_SUFFIXES):
        return "CRYPTO"
    return "EQUITY"


def _smart_round(value: float) -> float:
    if value is None or not np.isfinite(value) or value == 0:
        return 0.0
    av = abs(value)
    if av >= 1000:
        return round(value, 2)
    if av >= 1:
        return round(value, 4)
    if av >= 0.01:
        return round(value, 6)
    return round(value, 8)


def _validate_df(df: Any) -> Optional[pd.DataFrame]:
    """Return df if it's a usable OHLCV frame, else None."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None
    cols = {c.lower() for c in df.columns}
    if not all(c in cols for c in _REQUIRED_COLS):
        return None
    # Normalise to lowercase column names without mutating caller's frame.
    out = df.rename(columns={c: c.lower() for c in df.columns})
    if len(out) < _MIN_BARS:
        return None
    # Drop rows with any NaN in the required columns
    out = out.dropna(subset=list(_REQUIRED_COLS))
    if len(out) < _MIN_BARS:
        return None
    return out


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
         period: int = 14) -> np.ndarray:
    n = len(close)
    if n < 2:
        return np.zeros(n)
    prev_close = np.concatenate(([close[0]], close[:-1]))
    tr = np.maximum.reduce([
        high - low,
        np.abs(high - prev_close),
        np.abs(low - prev_close),
    ])
    # Wilder smoothing via pandas EMA-like rolling mean
    s = pd.Series(tr).rolling(window=period, min_periods=1).mean().to_numpy()
    return s


# --------------------------------------------------------------------------- #
#  STRATEGY 1: Volume-Weighted Candle Sequence
# --------------------------------------------------------------------------- #
# Detects N consecutive bars where:
#   1. Volume is in the top quartile of a rolling window, AND
#   2. Price direction is consistent (all up or all down)
# Entry fires on the *break* bar that confirms the sequence.
#
# Backtest champion params (from tiered_test_results.json):
#   tp_atr_mult = 1.5, sl_atr_mult = 1.0
# --------------------------------------------------------------------------- #

_VWCANDLE_DEFAULTS = {
    "seq_min": 3,            # minimum consecutive volume+direction bars
    "seq_max": 6,            # confidence saturates here
    "vol_window": 20,        # rolling window for top-quartile volume
    "vol_quantile": 0.75,    # top-quartile cutoff
    "atr_period": 14,
    "tp_atr_mult": 1.5,
    "sl_atr_mult": 1.0,
}


def volume_weighted_candle_sequence(
    data: Dict[str, pd.DataFrame],
    **kwargs: Any,
) -> List[Dict[str, Any]]:
    """Volume-weighted candle sequence breakout strategy.

    Parameters
    ----------
    data: dict[str, pd.DataFrame]
        Maps symbol -> OHLCV DataFrame (lowercase columns:
        open / high / low / close / volume).
    **kwargs: optional overrides for any key in `_VWCANDLE_DEFAULTS`,
        plus `timeframe` (str, default "4h").

    Returns
    -------
    list[dict] of signal dicts (see module docstring).
    """
    if os.getenv("VWCANDLE_DISABLED", "0") == "1":
        return []
    if not data or not isinstance(data, dict):
        return []

    cfg = dict(_VWCANDLE_DEFAULTS)
    for k in cfg:
        if k in kwargs:
            cfg[k] = kwargs[k]
    timeframe = kwargs.get("timeframe", "4h")

    out: List[Dict[str, Any]] = []
    for symbol, raw_df in data.items():
        df = _validate_df(raw_df)
        if df is None:
            continue

        close = df["close"].to_numpy(dtype=float)
        high = df["high"].to_numpy(dtype=float)
        low = df["low"].to_numpy(dtype=float)
        volume = df["volume"].to_numpy(dtype=float)
        n = len(close)

        # Rolling top-quartile volume threshold
        vol_thresh = (
            pd.Series(volume)
            .rolling(window=cfg["vol_window"], min_periods=cfg["vol_window"])
            .quantile(cfg["vol_quantile"])
            .to_numpy()
        )

        # Bar direction: +1 up, -1 down, 0 doji
        direction = np.sign(close - np.concatenate(([close[0]], close[:-1])))

        # Walk back from last bar to find consecutive same-direction high-vol bars
        last = n - 1
        if not np.isfinite(vol_thresh[last]):
            continue

        last_dir = direction[last]
        if last_dir == 0:
            continue
        if volume[last] < vol_thresh[last]:
            continue

        seq_len = 1
        for i in range(last - 1, max(last - cfg["seq_max"], -1), -1):
            if direction[i] != last_dir:
                break
            if not np.isfinite(vol_thresh[i]):
                break
            if volume[i] < vol_thresh[i]:
                break
            seq_len += 1

        if seq_len < cfg["seq_min"]:
            continue

        # Volume z-score across recent window for confidence boost
        vol_window = volume[max(0, last - cfg["vol_window"] + 1): last + 1]
        vmean = float(np.mean(vol_window))
        vstd = float(np.std(vol_window))
        vol_z = (volume[last] - vmean) / vstd if vstd > 1e-9 else 0.0

        atr = _atr(high, low, close, cfg["atr_period"])
        atr_val = float(atr[last])
        if atr_val <= 0:
            continue

        price = float(close[last])
        if price <= 0:
            continue

        if last_dir > 0:
            direction_label = "LONG"
            tp = price + cfg["tp_atr_mult"] * atr_val
            sl = price - cfg["sl_atr_mult"] * atr_val
        else:
            direction_label = "SHORT"
            tp = price - cfg["tp_atr_mult"] * atr_val
            sl = price + cfg["sl_atr_mult"] * atr_val

        risk = abs(price - sl)
        rr = abs(tp - price) / risk if risk > 1e-9 else 0.0

        # Confidence: base 0.55 + sequence-length bonus + vol_z bonus
        seq_bonus = 0.05 * (seq_len - cfg["seq_min"])  # +0.05 per extra bar
        vol_bonus = 0.05 * max(0.0, min(vol_z, 3.0))   # cap z at 3
        confidence = max(0.50, min(0.95, 0.55 + seq_bonus + vol_bonus))

        out.append({
            "symbol": symbol,
            "direction": direction_label,
            "signal_type": "BUY" if direction_label == "LONG" else "SELL",
            "strategy": "volume_weighted_candle_sequence",
            "asset_class": _infer_asset_class(symbol),
            "category": "incubator_grad",
            "timeframe": timeframe,
            "entry_price": _smart_round(price),
            "stop_loss": _smart_round(sl),
            "take_profit": _smart_round(tp),
            "confidence": round(confidence, 3),
            "risk_reward": round(rr, 2),
            "generated_at": _now_iso(),
            "source_system": "incubator_grad",
            "reason": (
                f"VW-candle sequence: {seq_len} consecutive {direction_label} "
                f"bars in top-{int(cfg['vol_quantile']*100)}% volume "
                f"(vol_z={vol_z:.2f}, atr={atr_val:.4f})"
            ),
        })

    return out


# --------------------------------------------------------------------------- #
#  STRATEGY 2: Market Structure + Volume
# --------------------------------------------------------------------------- #
# Detects HH/HL/LH/LL structure shifts (CHoCH / BOS) confirmed by volume
# expansion above a rolling 20-bar volume MA.
#
# Ported from `baby_strategies/market_structure_volume.py` (single-symbol
# class API) to the multi-symbol functional API expected by alpha_engine.
# --------------------------------------------------------------------------- #

_MSV_DEFAULTS = {
    "swing_lookback": 5,
    "volume_ma_period": 20,
    "volume_threshold": 1.5,   # vol > 1.5x rolling MA
    "atr_period": 14,
    "tp_atr_mult": 2.5,
    "sl_atr_mult": 1.0,
    "min_swings": 2,
}


def _find_structure_pivots(high: np.ndarray, low: np.ndarray,
                           lookback: int) -> tuple:
    """Return (swing_highs, swing_lows) as lists of (index, price) tuples."""
    swing_highs: List[tuple] = []
    swing_lows: List[tuple] = []
    n = len(high)
    for i in range(lookback, n - lookback):
        window_h = high[i - lookback: i + lookback + 1]
        window_l = low[i - lookback: i + lookback + 1]
        if high[i] == window_h.max():
            swing_highs.append((i, float(high[i])))
        if low[i] == window_l.min():
            swing_lows.append((i, float(low[i])))
    return swing_highs, swing_lows


def market_structure_volume(
    data: Dict[str, pd.DataFrame],
    **kwargs: Any,
) -> List[Dict[str, Any]]:
    """Market structure (BOS/CHoCH) + volume confirmation strategy.

    See module docstring for schema and rollback envs.
    """
    if os.getenv("MSV_DISABLED", "0") == "1":
        return []
    if not data or not isinstance(data, dict):
        return []

    cfg = dict(_MSV_DEFAULTS)
    for k in cfg:
        if k in kwargs:
            cfg[k] = kwargs[k]
    timeframe = kwargs.get("timeframe", "4h")

    out: List[Dict[str, Any]] = []
    for symbol, raw_df in data.items():
        df = _validate_df(raw_df)
        if df is None:
            continue

        high = df["high"].to_numpy(dtype=float)
        low = df["low"].to_numpy(dtype=float)
        close = df["close"].to_numpy(dtype=float)
        volume = df["volume"].to_numpy(dtype=float)
        n = len(close)

        atr = _atr(high, low, close, cfg["atr_period"])
        vol_ma = (
            pd.Series(volume)
            .rolling(window=cfg["volume_ma_period"], min_periods=1)
            .mean()
            .to_numpy()
        )

        last = n - 1
        price = float(close[last])
        cur_vol = float(volume[last])
        cur_atr = float(atr[last])
        cur_vol_ma = float(vol_ma[last])
        if cur_atr <= 0 or cur_vol_ma <= 0 or price <= 0:
            continue

        swing_highs, swing_lows = _find_structure_pivots(
            high, low, cfg["swing_lookback"]
        )
        if len(swing_highs) < cfg["min_swings"] or len(swing_lows) < cfg["min_swings"]:
            continue

        last_sh_idx, last_sh = swing_highs[-1]
        prev_sh_idx, prev_sh = swing_highs[-2]
        last_sl_idx, last_sl = swing_lows[-1]
        prev_sl_idx, prev_sl = swing_lows[-2]

        vol_ratio = cur_vol / cur_vol_ma
        vol_confirmed = vol_ratio > cfg["volume_threshold"]
        if not vol_confirmed:
            continue

        signal: Optional[Dict[str, Any]] = None

        # Bullish BOS: break above prev_sh after a LH (last_sh <= prev_sh)
        if price > prev_sh and last_sh <= prev_sh:
            breakout_strength = (price - prev_sh) / cur_atr
            confidence = 0.50 + min(0.30, breakout_strength * 0.30) + \
                min(0.15, (vol_ratio - 1.0) * 0.10)
            confidence = max(0.50, min(0.95, confidence))
            tp = price + cfg["tp_atr_mult"] * cur_atr
            sl = last_sl - cfg["sl_atr_mult"] * cur_atr * 0.5
            signal = {
                "direction": "LONG",
                "signal_type": "BUY",
                "tp": tp,
                "sl": sl,
                "confidence": confidence,
                "reason": (
                    f"Bullish BOS above {prev_sh:.4f} with {vol_ratio:.2f}x volume "
                    f"(strength={breakout_strength:.2f} ATR)"
                ),
            }

        # Bearish BOS: break below prev_sl after a HL (last_sl >= prev_sl)
        elif price < prev_sl and last_sl >= prev_sl:
            breakout_strength = (prev_sl - price) / cur_atr
            confidence = 0.50 + min(0.30, breakout_strength * 0.30) + \
                min(0.15, (vol_ratio - 1.0) * 0.10)
            confidence = max(0.50, min(0.95, confidence))
            tp = price - cfg["tp_atr_mult"] * cur_atr
            sl = last_sh + cfg["sl_atr_mult"] * cur_atr * 0.5
            signal = {
                "direction": "SHORT",
                "signal_type": "SELL",
                "tp": tp,
                "sl": sl,
                "confidence": confidence,
                "reason": (
                    f"Bearish BOS below {prev_sl:.4f} with {vol_ratio:.2f}x volume "
                    f"(strength={breakout_strength:.2f} ATR)"
                ),
            }

        if signal is None:
            continue

        risk = abs(price - signal["sl"])
        rr = abs(signal["tp"] - price) / risk if risk > 1e-9 else 0.0

        out.append({
            "symbol": symbol,
            "direction": signal["direction"],
            "signal_type": signal["signal_type"],
            "strategy": "market_structure_volume",
            "asset_class": _infer_asset_class(symbol),
            "category": "incubator_grad",
            "timeframe": timeframe,
            "entry_price": _smart_round(price),
            "stop_loss": _smart_round(signal["sl"]),
            "take_profit": _smart_round(signal["tp"]),
            "confidence": round(signal["confidence"], 3),
            "risk_reward": round(rr, 2),
            "generated_at": _now_iso(),
            "source_system": "incubator_grad",
            "reason": signal["reason"],
        })

    return out


# --------------------------------------------------------------------------- #
#  __main__: synthetic-data smoke backtest
# --------------------------------------------------------------------------- #

def _synthetic_ohlcv(n: int = 365 * 6, seed: int = 0,
                     spike_every: int = 30) -> pd.DataFrame:
    """Generate synthetic OHLCV with embedded volume spikes + structure shifts."""
    rng = np.random.default_rng(seed)
    # Geometric Brownian-ish walk with regime shifts every ~60 bars
    n_regimes = max(1, n // 60)
    drift_per_regime = rng.normal(0.0001, 0.001, n_regimes)
    drifts = np.repeat(drift_per_regime, 60)[:n]
    if len(drifts) < n:
        drifts = np.concatenate([drifts, np.full(n - len(drifts), drifts[-1])])
    rets = rng.normal(0, 0.02, n) + drifts
    close = 100.0 * np.exp(np.cumsum(rets))
    high = close * (1 + np.abs(rng.normal(0, 0.008, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.008, n)))
    open_ = close * (1 + rng.normal(0, 0.003, n))
    volume = rng.uniform(100, 500, n)
    # Embed volume spikes every `spike_every` bars
    spike_idx = np.arange(spike_every, n, spike_every)
    volume[spike_idx] *= rng.uniform(2.5, 4.5, len(spike_idx))
    df = pd.DataFrame({
        "open": open_, "high": high, "low": low, "close": close,
        "volume": volume,
    })
    return df


def _smoke_backtest(strategy_fn, symbol: str = "SOLUSDT") -> Dict[str, Any]:
    """Walk synthetic data bar-by-bar, fire signals, score with next-bar dir."""
    df = _synthetic_ohlcv(seed=42)
    n = len(df)
    n_signals = 0
    hits = 0
    confidences: List[float] = []
    # Walk every 5 bars to keep it cheap
    for end in range(_MIN_BARS, n - 1, 5):
        window = df.iloc[:end + 1]
        sigs = strategy_fn({symbol: window})
        for s in sigs:
            n_signals += 1
            confidences.append(s["confidence"])
            next_close = float(df["close"].iloc[end + 1])
            entry = float(s["entry_price"])
            if s["direction"] == "LONG" and next_close > entry:
                hits += 1
            elif s["direction"] == "SHORT" and next_close < entry:
                hits += 1
    hit_rate = hits / n_signals if n_signals else 0.0
    avg_conf = float(np.mean(confidences)) if confidences else 0.0
    return {
        "n_signals": n_signals,
        "hit_rate": round(hit_rate, 3),
        "avg_confidence": round(avg_conf, 3),
    }


if __name__ == "__main__":
    print("=" * 60)
    print("incubator_grad_strategies -- synthetic backtest")
    print("=" * 60)
    for name, fn in [
        ("volume_weighted_candle_sequence", volume_weighted_candle_sequence),
        ("market_structure_volume", market_structure_volume),
    ]:
        result = _smoke_backtest(fn)
        print(f"\n[{name}]")
        for k, v in result.items():
            print(f"  {k:18s} = {v}")
