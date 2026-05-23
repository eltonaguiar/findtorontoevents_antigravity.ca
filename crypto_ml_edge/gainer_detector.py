"""
Gainer Detector — Pre-pump + Breakout Detection (Phase 4)
==========================================================
Detects two categories of high-momentum crypto signals:

  1. Pre-pump: coins showing historical pre-pump patterns (volume ramp,
     BB squeeze, oversold RSI) BEFORE a 20%+ daily move has occurred.
  2. Breakout: coins already in early-stage explosive moves right now.

Design contracts
----------------
* Source label: every signal carries ``source="gainer_detector"`` — never
  confused with ``source="edge_engine"`` (GAIN-04).
* Zero lookahead: ``PrePumpModel.build_pre_pump_features()`` extracts
  features from bars STRICTLY before the event bar (GAIN-02).
* Same validation as Edge Engine: walk-forward folds + DSR gate (GAIN-05).
* Separate storage: ``data/gainer_events.parquet`` (GAIN-01).

Requirements implemented
------------------------
GAIN-01  GainerCollector.collect_daily_gainers / build_historical_gainers
GAIN-02  PrePumpModel.build_pre_pump_features (no lookahead)
GAIN-03  BreakoutDetector.scan
GAIN-04  "source": "gainer_detector" on every signal dict
GAIN-05  PrePumpModel.train uses WalkForwardSplit + validate_model
"""

from __future__ import annotations

import time
import warnings
import numpy as np
import pandas as pd
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from .config import (
    BINANCE_SPOT_BASE,
    DATA_DIR,
    CACHE_TTL_HOURS,
    GAINER_MIN_MOVE_PCT,
    GAINER_LOOKBACK_HOURS,
    GAINER_HISTORY_DAYS,
)
from .data_fetcher import fetch_klines
from .validation import WalkForwardSplit, validate_model


# ─── Constants ────────────────────────────────────────────────────────────────

GAINER_DB_PATH = DATA_DIR / "gainer_events.parquet"

# Pre-pump feature set (12 features — within FEAT-06 budget of 10-20)
PRE_PUMP_FEATURE_NAMES: list[str] = [
    "vol_accel_6h",          # Volume acceleration: mean(last 6h vol) / mean(24h vol)
    "vol_accel_3h",          # Tighter window: mean(last 3h vol) / mean(24h vol)
    "bb_width_squeeze",      # BB width percentile rank (low = compressed = squeeze)
    "bb_width_change",       # Rate of change of BB width (narrowing = pre-pump)
    "rel_vol_spike",         # Current bar volume / 20-period avg volume
    "rsi_level",             # RSI at pre-pump window (oversold recovery pattern)
    "rsi_slope_6h",          # RSI rising from oversold (slope over 6 bars)
    "price_compress_ratio",  # (high - low range) / ATR — low = price tightening
    "ret_24h_pre",           # 24h return BEFORE event (context: was it already rising?)
    "ret_6h_pre",            # 6h return leading into event window
    "vol_trend_direction",   # +1 if volume monotonically increasing over 6h else -1
    "obv_divergence",        # OBV rising while price flat/declining (accumulation)
]

# Breakout scan warm-up: 20 bars minimum
BREAKOUT_WARMUP_BARS = 22


# ─── Low-level OHLCV helpers (private) ────────────────────────────────────────

def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period, min_periods=period).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    return 100.0 - (100.0 / (1.0 + rs))


def _atr(high: pd.Series, low: pd.Series, close: pd.Series,
         period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def _bollinger_width(close: pd.Series, period: int = 20,
                     num_std: float = 2.0) -> pd.Series:
    """BB width = (upper - lower) / middle, normalised by price level."""
    sma = _sma(close, period)
    std = close.rolling(period, min_periods=period).std()
    upper = sma + num_std * std
    lower = sma - num_std * std
    return (upper - lower) / (sma + 1e-10)


def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff())
    direction.iloc[0] = 0.0
    return (direction * volume).cumsum()


# ═══════════════════════════════════════════════════════════════════════════════
# GAIN-01: GAINER COLLECTOR
# ═══════════════════════════════════════════════════════════════════════════════

class GainerCollector:
    """Collects and stores historical top-gainer events."""

    def collect_daily_gainers(
        self,
        min_move_pct: float = GAINER_MIN_MOVE_PCT,
        min_volume_usd: float = 1_000_000.0,
    ) -> pd.DataFrame:
        """
        Fetch today's top gainers from Binance 24hr ticker.

        Only returns pairs with:
        - 24h price change >= min_move_pct (default 20%)
        - 24h quote volume >= min_volume_usd (default $1M)

        Returns DataFrame with columns:
            symbol, pair, change_24h_pct, volume_24h_usd, price, date_utc
        Sorted by change_24h_pct descending.
        """
        url = f"{BINANCE_SPOT_BASE}/api/v3/ticker/24hr"
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            tickers = resp.json()
        except Exception as e:
            print(f"[GainerCollector] API error: {e}")
            return pd.DataFrame()

        gainers = []
        now_utc = datetime.now(timezone.utc).date()

        for t in tickers:
            sym = t.get("symbol", "")
            if not sym.endswith("USDT"):
                continue
            change = float(t.get("priceChangePercent", 0))
            volume = float(t.get("quoteVolume", 0))
            price  = float(t.get("lastPrice", 0))
            if change >= min_move_pct and volume >= min_volume_usd:
                gainers.append({
                    "symbol": sym,
                    "pair":   sym,
                    "change_24h_pct":  change,
                    "volume_24h_usd":  volume,
                    "price":           price,
                    "date_utc":        str(now_utc),
                })

        if not gainers:
            return pd.DataFrame()

        df = pd.DataFrame(gainers)
        df.sort_values("change_24h_pct", ascending=False, inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def build_historical_gainers(
        self,
        symbols: Optional[List[str]] = None,
        days: int = GAINER_HISTORY_DAYS,
        min_move_pct: float = GAINER_MIN_MOVE_PCT,
    ) -> pd.DataFrame:
        """
        Build historical dataset of 20%+ daily gainer events.

        Method:
          For each symbol, fetch hourly OHLCV going back `days` days.
          Scan day-over-day returns (using daily resampled OHLCV) to
          identify bars where the 24h return exceeded min_move_pct.
          For each identified gainer event, record:
            - symbol, event_date, peak_gain_pct
            - The event_bar index (position in the 1h series)
          This dataset is then consumed by PrePumpModel.train().

        CRITICAL: We mark only the event bar — no pre-pump features are
        captured here. That is PrePumpModel.build_pre_pump_features()'s job.
        Separating these steps makes it impossible to accidentally include
        post-event data in the feature window.

        Args:
            symbols: list of Binance pairs, e.g. ["BTCUSDT", ...].
                     If None, fetches a broad universe from the 24hr ticker.
            days:    how many calendar days of history to scan.
            min_move_pct: minimum 24h move threshold to count as a gainer event.

        Returns DataFrame with columns:
            symbol, event_bar_idx (int), event_ts (UTC), peak_gain_pct
        """
        if symbols is None:
            symbols = self._get_broad_universe(max_symbols=100)

        # 1h bars for `days` days
        candles_needed = days * 24
        events: list[dict] = []

        for i, symbol in enumerate(symbols):
            print(f"  [{i+1}/{len(symbols)}] Scanning {symbol} for gainer events...")
            ohlcv = fetch_klines(symbol, "1h", limit=candles_needed, cache=True)
            if ohlcv.empty or len(ohlcv) < 48:
                continue

            # Identify gainer events using 24h rolling return on the 1h series
            # close.pct_change(24) at bar T = return from T-24 to T (no lookahead)
            ret_24h = ohlcv["close"].pct_change(24) * 100.0

            for bar_idx in range(24, len(ohlcv)):
                gain = ret_24h.iloc[bar_idx]
                if pd.isna(gain) or gain < min_move_pct:
                    continue
                events.append({
                    "symbol":        symbol,
                    "event_bar_idx": bar_idx,
                    "event_ts":      ohlcv.index[bar_idx],
                    "peak_gain_pct": float(gain),
                })

            if (i + 1) % 10 == 0:
                time.sleep(0.5)

        if not events:
            return pd.DataFrame()

        df = pd.DataFrame(events)
        df.sort_values(["symbol", "event_ts"], inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def save_gainer_db(self, df: pd.DataFrame) -> None:
        """Save gainer events to crypto_ml_edge/data/gainer_events.parquet."""
        if df.empty:
            print("[GainerCollector] Empty DataFrame — nothing saved.")
            return
        GAINER_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(GAINER_DB_PATH, index=False)
        print(f"[GainerCollector] Saved {len(df)} gainer events → {GAINER_DB_PATH}")

    def load_gainer_db(self) -> pd.DataFrame:
        """Load previously saved gainer events. Returns empty DataFrame if not found."""
        if not GAINER_DB_PATH.exists():
            return pd.DataFrame()
        try:
            return pd.read_parquet(GAINER_DB_PATH)
        except Exception as e:
            print(f"[GainerCollector] Failed to load gainer DB: {e}")
            return pd.DataFrame()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _get_broad_universe(self, max_symbols: int = 100) -> List[str]:
        """Fetch top-N USDT pairs by 24h volume from Binance."""
        url = f"{BINANCE_SPOT_BASE}/api/v3/ticker/24hr"
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            tickers = [
                t for t in resp.json()
                if t.get("symbol", "").endswith("USDT")
                and float(t.get("quoteVolume", 0)) > 1_000_000
            ]
            tickers.sort(key=lambda t: float(t["quoteVolume"]), reverse=True)
            return [t["symbol"] for t in tickers[:max_symbols]]
        except Exception as e:
            print(f"[GainerCollector] Universe fetch error: {e}")
            return []


# ═══════════════════════════════════════════════════════════════════════════════
# GAIN-02: PRE-PUMP MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class PrePumpModel:
    """
    Identifies patterns common in the hours BEFORE a 20%+ daily move.

    ZERO LOOKAHEAD GUARANTEE
    ------------------------
    build_pre_pump_features(ohlcv, event_bar) extracts features from bars
    [event_bar - GAINER_LOOKBACK_HOURS  ..  event_bar - 1] inclusive.
    The event bar itself is NEVER included in the feature window.
    The test suite verifies this by injecting a spike at event_bar and
    confirming that features computed from the prior window are unchanged.
    """

    def __init__(self):
        self._model = None          # trained classifier (sklearn-compatible)
        self._validation_result: Optional[dict] = None

    # ── Feature extraction ────────────────────────────────────────────────────

    def build_pre_pump_features(
        self,
        ohlcv: pd.DataFrame,
        event_bar: int,
        lookback_hours: int = GAINER_LOOKBACK_HOURS,
    ) -> dict:
        """
        Extract features from the N hours BEFORE a pump event.

        CRITICAL contract: this function reads ohlcv up to index
        ``event_bar - 1`` only. It never reads ``event_bar`` or beyond.

        Args:
            ohlcv:         Full 1h OHLCV DataFrame (indexed by timestamp).
            event_bar:     Integer position of the gainer event bar (the bar
                           where the 24h return first crossed the threshold).
                           Features are extracted from bars
                           [event_bar - lookback_hours .. event_bar - 1].
            lookback_hours: Window size (default: GAINER_LOOKBACK_HOURS = 6).

        Returns:
            dict of feature_name -> float value.
            Returns an empty dict if there is insufficient history.
        """
        # Safety: enforce the lookahead-free window boundary
        window_end = event_bar - 1       # EXCLUSIVE of event_bar
        window_start = event_bar - lookback_hours  # 6 bars before event

        min_required = max(lookback_hours + 24, 26)  # need ATR/BB lookback
        if event_bar < min_required or window_start < 0:
            return {}

        # Context window: enough prior bars for indicators, but cap at event_bar - 1
        ctx_start = max(0, window_end - 100)  # 100 bars of context
        ctx_end   = window_end + 1            # pandas slice end (exclusive)
        ctx = ohlcv.iloc[ctx_start:ctx_end].copy()

        if len(ctx) < 25:
            return {}

        c = ctx["close"]
        v = ctx["volume"]
        h = ctx["high"]
        l = ctx["low"]

        # Map window positions into the ctx-local frame
        # ctx.iloc[-1] = ohlcv.iloc[window_end] = last bar before event
        # ctx.iloc[-lookback_hours:] = the pre-pump window [window_start..window_end]
        win = ctx.iloc[-lookback_hours:]   # The 6-bar pre-pump window
        ctx_full = ctx                     # Full 100-bar context for baselines

        # ── Feature 1 & 2: Volume acceleration ─────────────────────────────
        # vol_accel = mean volume in window / mean volume over prior 24h
        baseline_24h_vol = ctx_full["volume"].iloc[-24:].mean()
        if baseline_24h_vol < 1e-10:
            return {}

        vol_accel_6h = win["volume"].mean() / (baseline_24h_vol + 1e-10)
        win_3h = ctx.iloc[-3:]
        vol_accel_3h = win_3h["volume"].mean() / (baseline_24h_vol + 1e-10)

        # ── Feature 3 & 4: Bollinger Band width (squeeze) ──────────────────
        bb_width_series = _bollinger_width(c, period=20)
        bb_width_now = float(bb_width_series.iloc[-1])
        # Percentile rank of current BB width over the context window
        bb_width_history = bb_width_series.dropna()
        if len(bb_width_history) < 5:
            bb_squeeze_rank = 0.5
        else:
            bb_squeeze_rank = float(
                (bb_width_history < bb_width_now).sum() / len(bb_width_history)
            )
        # Rate of change: bb_width 6 bars ago vs now (negative = narrowing)
        bb_6h_ago = float(bb_width_series.iloc[-lookback_hours]
                          if len(bb_width_series) >= lookback_hours else bb_width_now)
        bb_width_change = (bb_width_now - bb_6h_ago) / (bb_6h_ago + 1e-10)

        # ── Feature 5: Relative volume spike ───────────────────────────────
        vol_sma20 = float(_sma(v, 20).iloc[-1])
        rel_vol_spike = float(v.iloc[-1]) / (vol_sma20 + 1e-10)

        # ── Feature 6 & 7: RSI level and slope ─────────────────────────────
        rsi_series = _rsi(c, period=14)
        rsi_now = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else 50.0
        rsi_6h_ago = float(rsi_series.iloc[-lookback_hours]
                           if len(rsi_series) >= lookback_hours else rsi_now)
        rsi_slope_6h = (rsi_now - rsi_6h_ago) / (lookback_hours + 1e-10)

        # ── Feature 8: Price compression ratio ─────────────────────────────
        # Measures how tight the recent range is relative to ATR
        # (low value = price coiling, common pre-pump)
        atr_series = _atr(h, l, c, period=14)
        atr_now = float(atr_series.iloc[-1]) if not pd.isna(atr_series.iloc[-1]) else 1.0
        recent_range = float(win["high"].max() - win["low"].min())
        # Normalise by atr_now * lookback so the ratio is dimensionless
        price_compress_ratio = recent_range / (atr_now * lookback_hours + 1e-10)

        # ── Feature 9 & 10: Pre-event momentum ─────────────────────────────
        # ret_24h_pre: 24h return ending at window_end (last bar before event)
        if len(ctx_full) >= 25:
            ret_24h_pre = float(
                (c.iloc[-1] - c.iloc[-25]) / (c.iloc[-25] + 1e-10)
            )
        else:
            ret_24h_pre = 0.0
        ret_6h_pre = float(
            (c.iloc[-1] - c.iloc[-lookback_hours]) / (c.iloc[-lookback_hours] + 1e-10)
        )

        # ── Feature 11: Volume trend direction ─────────────────────────────
        # +1 if volume is monotonically increasing across the 6h window, else -1
        win_vols = win["volume"].values
        is_rising = all(win_vols[i] <= win_vols[i+1] for i in range(len(win_vols)-1))
        vol_trend_direction = 1.0 if is_rising else -1.0

        # ── Feature 12: OBV divergence ──────────────────────────────────────
        # Positive divergence: OBV rising while price flat/declining
        obv_series = _obv(c, v)
        obv_slope = float(obv_series.iloc[-1] - obv_series.iloc[-lookback_hours])
        price_slope = float(c.iloc[-1] - c.iloc[-lookback_hours])
        # Normalise both by their window means to make dimensionless
        obv_norm = abs(float(obv_series.iloc[-lookback_hours:]
                             .mean())) + 1e-10
        price_norm = abs(float(c.mean())) + 1e-10
        obv_divergence = (obv_slope / obv_norm) - (price_slope / price_norm)

        return {
            "vol_accel_6h":         float(vol_accel_6h),
            "vol_accel_3h":         float(vol_accel_3h),
            "bb_width_squeeze":     float(bb_squeeze_rank),
            "bb_width_change":      float(bb_width_change),
            "rel_vol_spike":        float(rel_vol_spike),
            "rsi_level":            float(rsi_now),
            "rsi_slope_6h":         float(rsi_slope_6h),
            "price_compress_ratio": float(price_compress_ratio),
            "ret_24h_pre":          float(ret_24h_pre),
            "ret_6h_pre":           float(ret_6h_pre),
            "vol_trend_direction":  float(vol_trend_direction),
            "obv_divergence":       float(obv_divergence),
        }

    # ── Training ──────────────────────────────────────────────────────────────

    def train(
        self,
        gainer_events: pd.DataFrame,
        all_ohlcv: Dict[str, pd.DataFrame],
        n_trials: int = 3,
    ) -> dict:
        """
        Train a pre-pump classifier with walk-forward + DSR validation.

        Uses the same rigorous validation as the Edge Engine (GAIN-05):
        - WalkForwardSplit (5 folds, purge gap, embargo)
        - validate_model (DSR gate at p >= 0.95)
        - Cost-adjusted Sharpe

        Args:
            gainer_events: DataFrame from GainerCollector.build_historical_gainers().
                           Must have columns: symbol, event_bar_idx, event_ts, peak_gain_pct
            all_ohlcv:     Dict of {symbol: ohlcv_df} loaded for all symbols.
            n_trials:      Number of model variants (capped at MAX_MODEL_VARIANTS).

        Returns:
            dict with keys: verdict, model, validation_result, feature_importances,
                            n_events_used, n_events_skipped
        """
        try:
            from sklearn.ensemble import GradientBoostingClassifier
            from sklearn.preprocessing import StandardScaler
        except ImportError as e:
            raise ImportError(
                "scikit-learn is required for PrePumpModel training: "
                "pip install scikit-learn"
            ) from e

        if gainer_events.empty:
            return {"verdict": "FAIL", "fail_reasons": ["No gainer events provided"]}

        # ── Build feature matrix from historical events ───────────────────────
        X_rows: list[dict] = []
        y: list[float] = []
        event_times: list[pd.Timestamp] = []
        n_skipped = 0

        for _, row in gainer_events.iterrows():
            symbol = row["symbol"]
            bar_idx = int(row["event_bar_idx"])
            ohlcv = all_ohlcv.get(symbol)
            if ohlcv is None or ohlcv.empty:
                n_skipped += 1
                continue

            feats = self.build_pre_pump_features(ohlcv, bar_idx)
            if not feats:
                n_skipped += 1
                continue

            X_rows.append(feats)
            # Label: next-bar forward return (did the pump continue?)
            if bar_idx + 1 < len(ohlcv):
                next_ret = (ohlcv["close"].iloc[bar_idx + 1] -
                            ohlcv["close"].iloc[bar_idx]) / (
                    ohlcv["close"].iloc[bar_idx] + 1e-10
                )
                y.append(float(next_ret))
            else:
                y.append(0.0)
            event_times.append(row["event_ts"])

        n_used = len(X_rows)
        if n_used < 50:
            return {
                "verdict": "FAIL",
                "fail_reasons": [
                    f"Too few events for training: {n_used} (need >= 50). "
                    f"Run build_historical_gainers with more history or symbols."
                ],
                "n_events_used":    n_used,
                "n_events_skipped": n_skipped,
            }

        X_df = pd.DataFrame(X_rows)[PRE_PUMP_FEATURE_NAMES]
        y_arr = np.array(y)
        ts_idx = pd.DatetimeIndex(event_times)

        # ── Walk-forward validation ───────────────────────────────────────────
        splitter = WalkForwardSplit(
            n_samples=n_used,
            timestamps=ts_idx,
        )
        # Try to verify regime coverage (only possible if data spans 2022)
        try:
            splitter.verify_regime_coverage()
        except RuntimeError as exc:
            warnings.warn(str(exc), stacklevel=2)

        oos_returns: list[float] = []
        best_model = None
        best_fold_sharpe = -np.inf

        scaler = StandardScaler()

        for fold in splitter.folds:
            X_train = X_df.iloc[fold.train_start:fold.train_end].values
            y_train = y_arr[fold.train_start:fold.train_end]
            X_test  = X_df.iloc[fold.test_start:fold.test_end].values
            y_test  = y_arr[fold.test_start:fold.test_end]

            if len(X_train) < 20 or len(X_test) < 5:
                continue

            X_train_sc = scaler.fit_transform(X_train)
            X_test_sc  = scaler.transform(X_test)

            model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=3,
                learning_rate=0.05,
                random_state=42,
            )
            # Binary label: 1 if next-bar return positive
            y_train_bin = (y_train > 0).astype(int)
            model.fit(X_train_sc, y_train_bin)

            # OOS: signal = model confidence; return = y_test
            probs = model.predict_proba(X_test_sc)[:, 1]
            # Hold when model is confident (prob > 0.55); return is y_test
            signal = (probs > 0.55).astype(float)
            fold_returns = signal * y_test
            oos_returns.extend(fold_returns.tolist())

            fold_mean = np.mean(fold_returns) if len(fold_returns) else -np.inf
            if fold_mean > best_fold_sharpe:
                best_fold_sharpe = fold_mean
                best_model = model

        if not oos_returns or best_model is None:
            return {
                "verdict": "FAIL",
                "fail_reasons": ["Walk-forward produced no OOS returns"],
                "n_events_used":    n_used,
                "n_events_skipped": n_skipped,
            }

        # ── DSR gate ──────────────────────────────────────────────────────────
        oos_arr = np.array(oos_returns)
        # Gainer events are short-hold; assume ~365 events/year as trade freq
        trades_per_year = max(n_used / (GAINER_HISTORY_DAYS / 365.0), 1.0)
        validation = validate_model(
            returns=oos_arr,
            n_trials=min(n_trials, 10),
            pair="BTCUSDT",        # conservative: use BTC costs as proxy
            trades_per_year=trades_per_year,
            bars_per_year=8760,    # 1h base
        )

        self._validation_result = validation

        feature_importance = dict(zip(
            PRE_PUMP_FEATURE_NAMES,
            best_model.feature_importances_.tolist(),
        ))

        if validation["verdict"] == "PASS":
            self._model = best_model
            self._scaler = scaler

        return {
            "verdict":             validation["verdict"],
            "model":               best_model,
            "validation_result":   validation,
            "feature_importances": feature_importance,
            "n_events_used":       n_used,
            "n_events_skipped":    n_skipped,
        }

    # ── Inference ─────────────────────────────────────────────────────────────

    def predict(self, current_features: dict) -> dict:
        """
        Score the current market state for pre-pump probability.

        Args:
            current_features: dict from build_pre_pump_features() for the
                               CURRENT bar (i.e., event_bar = len(ohlcv) - 1).

        Returns:
            dict with keys:
                pre_pump_probability (float 0-1),
                confidence (str: "high" / "medium" / "low"),
                features_used (int),
                model_trained (bool)
        """
        if self._model is None:
            return {
                "pre_pump_probability": 0.0,
                "confidence":           "low",
                "features_used":        0,
                "model_trained":        False,
            }

        if not current_features:
            return {
                "pre_pump_probability": 0.0,
                "confidence":           "low",
                "features_used":        0,
                "model_trained":        True,
            }

        try:
            from sklearn.preprocessing import StandardScaler
        except ImportError:
            return {"pre_pump_probability": 0.0, "confidence": "low",
                    "features_used": 0, "model_trained": True}

        row = np.array([current_features.get(f, 0.0)
                        for f in PRE_PUMP_FEATURE_NAMES]).reshape(1, -1)
        row_sc = self._scaler.transform(row)
        prob = float(self._model.predict_proba(row_sc)[0, 1])

        if prob >= 0.70:
            confidence = "high"
        elif prob >= 0.55:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "pre_pump_probability": prob,
            "confidence":           confidence,
            "features_used":        len(PRE_PUMP_FEATURE_NAMES),
            "model_trained":        True,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GAIN-03: BREAKOUT DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════

class BreakoutDetector:
    """
    Detects pairs already showing early-stage explosive breakout moves.

    Scans for four simultaneous conditions (rule-based, no training required):
      1. Volume spike:      Current bar volume > 5x 20-period average
      2. Price breakout:    Close above the 20-period rolling high
      3. ATR expansion:     Current ATR > 2x average ATR over the past 20 periods
      4. Momentum confirm:  2+ consecutive green candles with rising volume

    All four conditions are scored; ``strength`` is the fraction satisfied [0, 1].
    """

    # Thresholds (tuneable)
    VOL_SPIKE_MULTIPLIER   = 5.0   # vol > 5x avg
    PRICE_HIGH_PERIOD      = 20    # breakout above N-bar high
    ATR_EXPANSION_MULT     = 2.0   # ATR > 2x avg ATR
    CONSEC_GREEN_MIN       = 2     # minimum consecutive green candles
    MIN_STRENGTH           = 0.5   # at least 2 of 4 conditions

    def scan(
        self,
        ohlcv_dict: Dict[str, pd.DataFrame],
        min_strength: float = MIN_STRENGTH,
    ) -> List[dict]:
        """
        Scan all pairs for breakout signals.

        Args:
            ohlcv_dict:   {symbol: ohlcv_df} — each df has [open, high, low, close, volume]
                          indexed by UTC timestamp, sorted ascending.
            min_strength: Minimum fraction of conditions satisfied (default 0.5 = 2/4).

        Returns:
            List of signal dicts, each with:
            {
                "source":      "gainer_detector",
                "signal_type": "breakout",
                "symbol":      str,
                "strength":    float [0, 1],
                "confidence":  str,
                "conditions":  dict (which conditions fired),
                "features":    dict (raw numeric values),
            }
            Sorted by strength descending.
        """
        signals: list[dict] = []

        for symbol, ohlcv in ohlcv_dict.items():
            if ohlcv is None or len(ohlcv) < BREAKOUT_WARMUP_BARS:
                continue

            sig = self._check_breakout(symbol, ohlcv)
            if sig is not None and sig["strength"] >= min_strength:
                signals.append(sig)

        signals.sort(key=lambda s: s["strength"], reverse=True)
        return signals

    def _check_breakout(self, symbol: str, ohlcv: pd.DataFrame) -> Optional[dict]:
        """Evaluate breakout conditions for a single pair. Returns signal dict or None."""
        c = ohlcv["close"]
        h = ohlcv["high"]
        l = ohlcv["low"]
        v = ohlcv["volume"]
        o = ohlcv["open"]

        # Need at least PRICE_HIGH_PERIOD + 2 bars
        if len(ohlcv) < self.PRICE_HIGH_PERIOD + 2:
            return None

        # ── Condition 1: Volume spike ─────────────────────────────────────────
        # Use last 2 bars (to catch a spike that just started)
        vol_avg_20 = float(_sma(v, 20).iloc[-1])
        current_vol_max = float(v.iloc[-2:].max())
        vol_ratio = current_vol_max / (vol_avg_20 + 1e-10)
        cond_vol_spike = vol_ratio >= self.VOL_SPIKE_MULTIPLIER

        # ── Condition 2: Price above N-bar high ───────────────────────────────
        # The rolling high is computed over bars [T-N .. T-1] (shift by 1 to
        # exclude the current bar, preventing trivial self-comparison).
        rolling_high_excl = h.shift(1).rolling(
            self.PRICE_HIGH_PERIOD, min_periods=self.PRICE_HIGH_PERIOD
        ).max()
        prev_high = float(rolling_high_excl.iloc[-1])
        current_close = float(c.iloc[-1])
        cond_price_breakout = (
            not pd.isna(prev_high) and current_close > prev_high
        )

        # ── Condition 3: ATR expansion ────────────────────────────────────────
        atr_series = _atr(h, l, c, period=14)
        current_atr = float(atr_series.iloc[-1])
        avg_atr_20 = float(_sma(atr_series, 20).iloc[-1])
        cond_atr_expansion = (
            not pd.isna(current_atr)
            and not pd.isna(avg_atr_20)
            and avg_atr_20 > 1e-10
            and current_atr >= self.ATR_EXPANSION_MULT * avg_atr_20
        )

        # ── Condition 4: Consecutive green candles with rising volume ─────────
        n_consec = self.CONSEC_GREEN_MIN + 1  # look at last 3 bars
        tail = ohlcv.iloc[-n_consec:]
        greens = (tail["close"] > tail["open"]).values
        vols   = tail["volume"].values
        # All green AND volume increasing bar-by-bar
        consec_green = all(greens)
        rising_vol   = all(vols[i] <= vols[i+1] for i in range(len(vols)-1))
        cond_momentum = consec_green and rising_vol

        # ── Aggregate score ───────────────────────────────────────────────────
        conditions = {
            "vol_spike":       cond_vol_spike,
            "price_breakout":  cond_price_breakout,
            "atr_expansion":   cond_atr_expansion,
            "consec_momentum": cond_momentum,
        }
        n_fired = sum(conditions.values())
        strength = n_fired / len(conditions)

        if n_fired == 0:
            return None

        if strength >= 0.75:
            confidence = "high"
        elif strength >= 0.50:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "source":      "gainer_detector",
            "signal_type": "breakout",
            "symbol":      symbol,
            "strength":    float(strength),
            "confidence":  confidence,
            "conditions":  conditions,
            "features": {
                "vol_ratio_vs_20avg":     float(vol_ratio),
                "close_vs_20bar_high":    float(current_close / (prev_high + 1e-10)),
                "atr_vs_20avg_atr":       float(current_atr / (avg_atr_20 + 1e-10)),
                "consec_green_rising_vol": float(cond_momentum),
                "current_vol":            float(v.iloc[-1]),
                "current_close":          float(current_close),
            },
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GAIN-01 + GAIN-04: GAINER ENGINE (unified interface)
# ═══════════════════════════════════════════════════════════════════════════════

class GainerEngine:
    """
    Unified interface for the gainer detector subsystem.

    This is the single entry point callers should use. It wires together
    GainerCollector, PrePumpModel, and BreakoutDetector, and guarantees
    that every emitted signal carries ``source="gainer_detector"`` (GAIN-04).
    """

    def __init__(self):
        self.collector  = GainerCollector()
        self.pre_pump   = PrePumpModel()
        self.breakout   = BreakoutDetector()

    def run_scan(
        self,
        ohlcv_dict: Dict[str, pd.DataFrame],
        funding_dict: Optional[Dict[str, pd.DataFrame]] = None,
        pre_pump_threshold: float = 0.55,
        breakout_min_strength: float = BreakoutDetector.MIN_STRENGTH,
    ) -> List[dict]:
        """
        Run both pre-pump and breakout detection and return all signals.

        This is the live scan path. ``ohlcv_dict`` should contain the most
        recent OHLCV for all candidate pairs, indexed to the current bar.

        Args:
            ohlcv_dict:             {symbol: ohlcv_df}
            funding_dict:           Optional {symbol: funding_df} (unused today but
                                    reserved for future funding-enhanced pre-pump model)
            pre_pump_threshold:     Minimum pre-pump probability to emit a signal.
            breakout_min_strength:  Minimum fraction of breakout conditions fired.

        Returns:
            List of signal dicts. Every dict is guaranteed to have:
            {
                "source":      "gainer_detector",   # GAIN-04
                "signal_type": "pre_pump" | "breakout",
                "symbol":      str,
                "confidence":  str,
                "features":    dict,
                # plus signal_type-specific fields
            }
            Pre-pump signals additionally carry "pre_pump_probability".
            Breakout signals additionally carry "strength" and "conditions".
            Sorted by confidence (high > medium > low) then signal_type.
        """
        signals: list[dict] = []

        # ── Breakout scan (always runs — no training required) ────────────────
        breakout_signals = self.breakout.scan(
            ohlcv_dict, min_strength=breakout_min_strength
        )
        signals.extend(breakout_signals)

        # ── Pre-pump scan (only if model has been trained) ────────────────────
        if self.pre_pump._model is not None:
            for symbol, ohlcv in ohlcv_dict.items():
                if ohlcv is None or len(ohlcv) < 30:
                    continue
                # Extract features for the CURRENT bar (last bar in ohlcv)
                # We pass event_bar = len(ohlcv) - 1 so features are drawn
                # from bars [len-1-LOOKBACK .. len-2] — zero lookahead.
                cur_event_bar = len(ohlcv) - 1
                feats = self.pre_pump.build_pre_pump_features(ohlcv, cur_event_bar)
                if not feats:
                    continue
                pred = self.pre_pump.predict(feats)
                prob = pred["pre_pump_probability"]
                if prob >= pre_pump_threshold:
                    signals.append({
                        "source":               "gainer_detector",
                        "signal_type":          "pre_pump",
                        "symbol":               symbol,
                        "confidence":           pred["confidence"],
                        "pre_pump_probability": prob,
                        "features":             feats,
                    })

        # ── Sort: high confidence first, then breakout before pre_pump ────────
        confidence_rank = {"high": 0, "medium": 1, "low": 2}
        signals.sort(key=lambda s: (
            confidence_rank.get(s.get("confidence", "low"), 2),
            0 if s["signal_type"] == "breakout" else 1,
        ))

        return signals
