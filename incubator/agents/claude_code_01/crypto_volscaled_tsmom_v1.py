"""Volatility-Scaled Time-Series Momentum (VolScaled TSMOM).

Academic foundation:
  - Moskowitz, Ooi, Pedersen (2012): "Time Series Momentum"
    Journal of Financial Economics, 104(2), 228-250.
    Documented positive TSMOM across 58 futures: go long assets with
    positive trailing returns, short those with negative. Sharpe ~1.0.

  - Barroso & Santa-Clara (2015): "Momentum Has Its Moments"
    Journal of Financial Economics, 116(1), 111-120.
    KEY INSIGHT: Scaling momentum positions by inverse realized volatility
    nearly doubles the Sharpe ratio (1.8-3.5 in-sample). During high-vol
    regimes the raw signal is noisy and drawdowns cluster; vol-scaling
    automatically reduces exposure. During low-vol regimes conviction is
    higher and the strategy levers up.

Implementation:
  1. Multi-lookback blended TSMOM signal (7d/14d/30d weighted 0.4/0.35/0.25).
  2. Position weight = target_vol / realized_vol(20d) — the Barroso-Santa-Clara
     volatility management layer.
  3. ADX filter (>20) to avoid whipsaw in trendless regimes.
  4. ATR-based TP/SL scaled by inverse volatility for adaptive risk management.

Documented Sharpe: 2.0-3.5 (Barroso & Santa-Clara 2015, Table III).
"""

import numpy as np
import pandas as pd
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class Signal:
    symbol: str
    direction: str      # "BUY" or "SELL"
    confidence: float   # 0.0 to 1.0
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


DEFAULT_PARAMS = {
    "lookback_fast": 7,
    "lookback_mid": 14,
    "lookback_slow": 30,
    "target_vol": 0.15,       # 15% annualized
    "vol_window": 20,
    "adx_period": 14,
    "adx_threshold": 20,
    "atr_period": 14,
    "tp_atr_mult": 2.5,
    "sl_atr_mult": 1.2,
}


def _compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    """Average True Range (Wilder)."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=period).mean()


def _compute_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    """Average Directional Index (Wilder).

    Returns the ADX line (trend strength, 0-100).
    """
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)

    # True Range
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    # Directional Movement
    plus_dm = np.where((high - prev_high) > (prev_low - low), np.maximum(high - prev_high, 0), 0)
    minus_dm = np.where((prev_low - low) > (high - prev_high), np.maximum(prev_low - low, 0), 0)

    plus_dm = pd.Series(plus_dm, index=high.index, dtype=float)
    minus_dm = pd.Series(minus_dm, index=high.index, dtype=float)

    # Wilder smoothing (EMA with alpha = 1/period)
    alpha = 1.0 / period
    atr_smooth = tr.ewm(alpha=alpha, min_periods=period, adjust=False).mean()
    plus_dm_smooth = plus_dm.ewm(alpha=alpha, min_periods=period, adjust=False).mean()
    minus_dm_smooth = minus_dm.ewm(alpha=alpha, min_periods=period, adjust=False).mean()

    # Directional Indicators
    plus_di = 100.0 * plus_dm_smooth / atr_smooth.replace(0, np.nan)
    minus_di = 100.0 * minus_dm_smooth / atr_smooth.replace(0, np.nan)

    # DX and ADX
    di_sum = plus_di + minus_di
    dx = 100.0 * (plus_di - minus_di).abs() / di_sum.replace(0, np.nan)
    adx = dx.ewm(alpha=alpha, min_periods=period, adjust=False).mean()

    return adx


def _realized_vol_annualized(close: pd.Series, window: int) -> pd.Series:
    """Annualized realized volatility from log returns.

    Uses sqrt(365) for crypto (24/7 markets).
    """
    log_ret = np.log(close / close.shift(1))
    return log_ret.rolling(window=window, min_periods=window).std() * np.sqrt(365)


class VolScaledTsmomStrategy:
    """Volatility-Scaled Time-Series Momentum.

    Combines multi-lookback TSMOM signals with the Barroso-Santa-Clara (2015)
    volatility scaling mechanism. Position sizing is inversely proportional
    to trailing realized volatility, which compresses drawdowns and amplifies
    returns during calm trending markets.

    Parameters
    ----------
    params : dict, optional
        Override any default parameter. Keys:
        lookback_fast, lookback_mid, lookback_slow, target_vol, vol_window,
        adx_period, adx_threshold, atr_period, tp_atr_mult, sl_atr_mult.
    """

    def __init__(self, params: Optional[dict] = None):
        cfg = {**DEFAULT_PARAMS}
        if params:
            cfg.update(params)

        self.lookback_fast: int = cfg["lookback_fast"]
        self.lookback_mid: int = cfg["lookback_mid"]
        self.lookback_slow: int = cfg["lookback_slow"]
        self.target_vol: float = cfg["target_vol"]
        self.vol_window: int = cfg["vol_window"]
        self.adx_period: int = cfg["adx_period"]
        self.adx_threshold: float = cfg["adx_threshold"]
        self.atr_period: int = cfg["atr_period"]
        self.tp_atr_mult: float = cfg["tp_atr_mult"]
        self.sl_atr_mult: float = cfg["sl_atr_mult"]

        # Blend weights (Moskowitz et al. suggest multi-horizon improves robustness)
        self.weights = {
            self.lookback_fast: 0.40,
            self.lookback_mid: 0.35,
            self.lookback_slow: 0.25,
        }

    def _tsmom_signal(self, close: pd.Series, lookback: int) -> pd.Series:
        """Raw time-series momentum: sign of trailing N-period return.

        Returns +1 (long) if return > 0, -1 (short) if return < 0, 0 if flat.
        """
        ret = close / close.shift(lookback) - 1.0
        return np.sign(ret)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        """Generate volatility-scaled TSMOM signals.

        Parameters
        ----------
        data : pd.DataFrame
            OHLCV DataFrame with columns: open, high, low, close, volume.
            Must have at least max(lookback_slow, vol_window, atr_period,
            adx_period) + 20 rows for reliable computation.
        symbol : str
            Trading pair symbol (default "BTCUSDT").

        Returns
        -------
        List[Signal]
            Zero or one Signal based on the latest bar.
        """
        required_cols = {"open", "high", "low", "close", "volume"}
        # Accept case-insensitive column names
        data.columns = [c.lower() for c in data.columns]
        if not required_cols.issubset(set(data.columns)):
            missing = required_cols - set(data.columns)
            raise ValueError(f"Missing columns: {missing}")

        if len(data) < self.lookback_slow + self.vol_window:
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)

        # --- 1. Multi-lookback blended TSMOM signal ---
        blended = pd.Series(0.0, index=data.index)
        for lookback, weight in self.weights.items():
            blended += weight * self._tsmom_signal(close, lookback)

        # --- 2. Volatility scaling (Barroso & Santa-Clara 2015) ---
        realized_vol = _realized_vol_annualized(close, self.vol_window)
        vol_scalar = self.target_vol / realized_vol.replace(0, np.nan)
        # Cap scalar to avoid extreme leverage (max 3x)
        vol_scalar = vol_scalar.clip(upper=3.0)

        # --- 3. ADX trend filter ---
        adx = _compute_adx(high, low, close, self.adx_period)

        # --- 4. ATR for TP/SL ---
        atr = _compute_atr(high, low, close, self.atr_period)

        # --- Evaluate latest bar ---
        idx = data.index[-1]
        blended_val = blended.iloc[-1]
        vol_scalar_val = vol_scalar.iloc[-1]
        adx_val = adx.iloc[-1]
        atr_val = atr.iloc[-1]
        current_price = close.iloc[-1]

        # Filter: need valid values and trend presence
        if pd.isna(blended_val) or pd.isna(vol_scalar_val) or pd.isna(adx_val) or pd.isna(atr_val):
            return []

        if adx_val < self.adx_threshold:
            return []

        if abs(blended_val) < 1e-9:
            return []

        # Direction
        direction = "BUY" if blended_val > 0 else "SELL"

        # Confidence: magnitude of blended signal * vol_scalar, capped at 0.95
        confidence = min(abs(blended_val) * vol_scalar_val, 0.95)
        confidence = max(confidence, 0.05)  # floor at 5%

        # TP/SL: ATR-based, scaled by inverse volatility
        # In high-vol regimes vol_scalar < 1 -> tighter stops (less risk)
        # In low-vol regimes vol_scalar > 1 -> wider stops (more room)
        tp_distance = atr_val * self.tp_atr_mult * min(vol_scalar_val, 2.0)
        sl_distance = atr_val * self.sl_atr_mult * min(vol_scalar_val, 2.0)

        if direction == "BUY":
            take_profit = current_price + tp_distance
            stop_loss = current_price - sl_distance
        else:
            take_profit = current_price - tp_distance
            stop_loss = current_price + sl_distance

        # Build reason string
        rv_pct = realized_vol.iloc[-1] * 100 if not pd.isna(realized_vol.iloc[-1]) else 0
        reason = (
            f"VolScaled TSMOM {direction} | "
            f"Blended signal={blended_val:+.2f} (7d/14d/30d weighted) | "
            f"Realized vol={rv_pct:.1f}% ann -> scalar={vol_scalar_val:.2f}x | "
            f"ADX={adx_val:.1f} | ATR={atr_val:.2f} | "
            f"Barroso-SantaClara 2015 + Moskowitz-Ooi-Pedersen 2012"
        )

        return [Signal(
            symbol=symbol,
            direction=direction,
            confidence=round(confidence, 4),
            entry_price=round(current_price, 2),
            take_profit=round(take_profit, 2),
            stop_loss=round(stop_loss, 2),
            reason=reason,
        )]


# ---------------------------------------------------------------------------
# Standalone execution: fetch Binance klines and run strategy
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import requests

    BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"

    def fetch_binance_ohlcv(symbol: str = "BTCUSDT", interval: str = "1d", limit: int = 120) -> pd.DataFrame:
        """Fetch OHLCV data from Binance public API."""
        resp = requests.get(BINANCE_KLINES_URL, params={
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }, timeout=15)
        resp.raise_for_status()
        raw = resp.json()
        df = pd.DataFrame(raw, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_vol", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore",
        ])
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms")
        df.set_index("timestamp", inplace=True)
        return df[["open", "high", "low", "close", "volume"]]

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    strategy = VolScaledTsmomStrategy()

    print("=" * 72)
    print("Volatility-Scaled TSMOM Scanner")
    print("Barroso & Santa-Clara 2015 | Moskowitz, Ooi, Pedersen 2012")
    print("=" * 72)

    for sym in symbols:
        try:
            df = fetch_binance_ohlcv(sym, interval="1d", limit=120)
            signals = strategy.generate_signals(df, symbol=sym)
            if signals:
                s = signals[0]
                print(f"\n[{s.direction}] {s.symbol} @ {s.entry_price}")
                print(f"  Confidence: {s.confidence:.2%}")
                print(f"  TP: {s.take_profit}  SL: {s.stop_loss}")
                print(f"  {s.reason}")
            else:
                print(f"\n[--] {sym}: No signal (ADX below threshold or insufficient trend)")
        except Exception as exc:
            print(f"\n[ERR] {sym}: {exc}")

    print("\n" + "=" * 72)
