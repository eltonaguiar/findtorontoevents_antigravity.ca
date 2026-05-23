"""Cointegration-Based Pairs Trading / Statistical Arbitrage for Crypto.

Academic Foundation:
    - Vidyamurthy, G. (2004). "Pairs Trading: Quantitative Methods and Analysis."
      Wiley Finance. The seminal reference on cointegration-based pairs trading.
    - Gatev, E., Goetzmann, W., & Rouwenhorst, K. (2006). "Pairs Trading:
      Performance of a Relative-Value Arbitrage Rule." Review of Financial Studies,
      19(3), 797-827. Documented 11% annual excess returns on US equities.
    - Krauss, C. (2017). "Statistical Arbitrage Pairs Trading Strategies: Review
      and Outlook." Journal of Economic Surveys, 31(2), 513-545. Comprehensive
      review showing Sharpe ratios of 1.6-2.5 across asset classes.
    - Do, B. & Faff, R. (2010). "Does Simple Pairs Trading Still Work?"
      Financial Analysts Journal, 66(4), 83-95. Confirms persistent mean-reversion
      alpha in spread-based strategies.

Adaptation for Single-Symbol Forward Scanner:
    Classical cointegration requires two co-moving assets. Since the forward scanner
    delivers one symbol's OHLCV at a time, we construct a synthetic "fair value"
    from a blend of long-term trend estimators (EMA-50, EMA-200, cumulative VWAP
    proxy) and measure the normalized spread of price vs. this fair value.

    The z-score of that spread follows the same statistical mechanics as a pairs
    spread: if the spread is stationary (verified via half-life test), z-score
    excursions beyond +/-2 sigma tend to revert. This is mathematically equivalent
    to an Ornstein-Uhlenbeck mean-reverting process.

Half-Life Filter:
    We regress spread(t) on spread(t-1) to estimate the AR(1) coefficient beta.
    Half-life = -ln(2) / ln(beta). We only trade when half-life < 30 bars,
    ensuring mean reversion is fast enough to capture within a reasonable horizon.

Documented Performance: Sharpe 1.6-2.5 (Krauss 2017 survey across implementations).

Parameters:
    ema_fast: 50        — Fast EMA for fair value blend
    ema_slow: 200       — Slow EMA for fair value blend
    zscore_window: 60   — Rolling window for z-score calculation
    entry_zscore: 2.0   — Z-score threshold for entry (long at -2, short at +2)
    exit_zscore: 0.5    — Z-score threshold for exit (mean reversion target)
    stop_zscore: 3.5    — Z-score threshold for stop loss
    max_half_life: 30   — Maximum half-life in bars for trade eligibility
    atr_period: 14      — ATR period for volatility reference
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
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


class CointegrationPairsStrategy:
    """Statistical arbitrage strategy using price-vs-fair-value spread z-scores.

    Constructs a synthetic fair value from EMA(50), EMA(200), and a cumulative
    VWAP proxy. Measures the normalized spread between price and fair value,
    computes a rolling z-score, and trades mean reversion when the spread is
    statistically extended (|z| > 2.0) and the half-life confirms fast reversion.
    """

    def __init__(self, params: Optional[Dict] = None):
        p = params or {}
        self.ema_fast = p.get('ema_fast', 50)
        self.ema_slow = p.get('ema_slow', 200)
        self.zscore_window = p.get('zscore_window', 60)
        self.entry_zscore = p.get('entry_zscore', 2.0)
        self.exit_zscore = p.get('exit_zscore', 0.5)
        self.stop_zscore = p.get('stop_zscore', 3.5)
        self.max_half_life = p.get('max_half_life', 30)
        self.atr_period = p.get('atr_period', 14)

        # Fair value blend weights (EMA fast, EMA slow, VWAP proxy)
        self.fv_weights = p.get('fv_weights', [0.3, 0.3, 0.4])

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        """Generate cointegration-based mean reversion signals.

        Args:
            data: DataFrame with columns [open, high, low, close, volume].
                  Index should be datetime or sequential integer.
            symbol: Trading pair symbol (e.g. "BTCUSDT").

        Returns:
            List of Signal objects. Typically 0 or 1 signal per call.
        """
        signals: List[Signal] = []

        min_bars = self.ema_slow + self.zscore_window + 10
        if len(data) < min_bars:
            return signals

        close = data['close'].astype(float).values
        high = data['high'].astype(float).values
        low = data['low'].astype(float).values
        volume = data['volume'].astype(float).values

        # --- Step 1: Compute fair value components ---
        ema_fast = self._ema(close, self.ema_fast)
        ema_slow = self._ema(close, self.ema_slow)
        vwap_proxy = self._cumulative_vwap(close, high, low, volume)

        # Weighted blend for fair value
        w = self.fv_weights
        fair_value = w[0] * ema_fast + w[1] * ema_slow + w[2] * vwap_proxy

        # --- Step 2: Compute normalized spread ---
        # Avoid division by zero
        valid_mask = fair_value > 0
        spread = np.where(valid_mask, (close - fair_value) / fair_value, 0.0)

        # --- Step 3: Rolling z-score of spread ---
        zscore = self._rolling_zscore(spread, self.zscore_window)

        # --- Step 4: Half-life filter ---
        # Use the last zscore_window * 2 bars of spread for regression
        lookback = min(self.zscore_window * 2, len(spread) - 1)
        recent_spread = spread[-lookback:]
        half_life = self._compute_half_life(recent_spread)

        if half_life is None or half_life <= 0 or half_life > self.max_half_life:
            return signals

        # --- Step 5: ATR for reference ---
        atr = self._atr(high, low, close, self.atr_period)
        current_atr = atr[-1] if len(atr) > 0 else 0.0

        # --- Step 6: Current values ---
        current_close = close[-1]
        current_zscore = zscore[-1]
        current_fair_value = fair_value[-1]

        if np.isnan(current_zscore) or current_fair_value <= 0:
            return signals

        # --- Step 7: Generate signals based on z-score ---
        # Spread std for converting z-score targets to price levels
        spread_window = spread[-self.zscore_window:]
        spread_std = np.std(spread_window, ddof=1)
        spread_mean = np.mean(spread_window)

        if spread_std <= 0:
            return signals

        # LONG signal: z-score < -entry_zscore (price undervalued vs fair value)
        if current_zscore < -self.entry_zscore:
            confidence = self._zscore_to_confidence(abs(current_zscore))

            # TP: price at z-score = 0 (full reversion to fair value)
            tp_spread = spread_mean
            tp_price = current_fair_value * (1.0 + tp_spread)

            # SL: price at z-score = -stop_zscore
            sl_spread = spread_mean - self.stop_zscore * spread_std
            sl_price = current_fair_value * (1.0 + sl_spread)

            # Sanity: TP must be above entry, SL must be below entry
            if tp_price <= current_close:
                tp_price = current_close * 1.01
            if sl_price >= current_close:
                sl_price = current_close * 0.97

            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_close, 6),
                take_profit=round(tp_price, 6),
                stop_loss=round(sl_price, 6),
                reason=(
                    f"Cointegration mean reversion LONG: z-score={current_zscore:.2f} "
                    f"(threshold=-{self.entry_zscore}), half-life={half_life:.1f} bars, "
                    f"fair_value={current_fair_value:.2f}, spread_std={spread_std:.6f}, "
                    f"ATR={current_atr:.2f}"
                )
            ))

        # SHORT signal: z-score > +entry_zscore (price overvalued vs fair value)
        elif current_zscore > self.entry_zscore:
            confidence = self._zscore_to_confidence(abs(current_zscore))

            # TP: price at z-score = 0 (full reversion to fair value)
            tp_spread = spread_mean
            tp_price = current_fair_value * (1.0 + tp_spread)

            # SL: price at z-score = +stop_zscore
            sl_spread = spread_mean + self.stop_zscore * spread_std
            sl_price = current_fair_value * (1.0 + sl_spread)

            # Sanity: TP must be below entry, SL must be above entry
            if tp_price >= current_close:
                tp_price = current_close * 0.99
            if sl_price <= current_close:
                sl_price = current_close * 1.03

            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_close, 6),
                take_profit=round(tp_price, 6),
                stop_loss=round(sl_price, 6),
                reason=(
                    f"Cointegration mean reversion SHORT: z-score={current_zscore:.2f} "
                    f"(threshold=+{self.entry_zscore}), half-life={half_life:.1f} bars, "
                    f"fair_value={current_fair_value:.2f}, spread_std={spread_std:.6f}, "
                    f"ATR={current_atr:.2f}"
                )
            ))

        return signals

    # ---- Internal helpers ----

    @staticmethod
    def _ema(values: np.ndarray, period: int) -> np.ndarray:
        """Compute exponential moving average."""
        result = np.full_like(values, np.nan, dtype=float)
        if len(values) < period:
            return result
        # Seed with SMA
        result[period - 1] = np.mean(values[:period])
        multiplier = 2.0 / (period + 1)
        for i in range(period, len(values)):
            result[i] = values[i] * multiplier + result[i - 1] * (1.0 - multiplier)
        return result

    @staticmethod
    def _cumulative_vwap(close: np.ndarray, high: np.ndarray,
                         low: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Compute a rolling VWAP proxy using typical price * volume.

        Uses an expanding window reset every 200 bars to avoid stale anchoring
        in long time series.
        """
        typical_price = (high + low + close) / 3.0
        reset_period = 200
        vwap = np.full_like(close, np.nan, dtype=float)

        for start in range(0, len(close), reset_period):
            end = min(start + reset_period, len(close))
            segment_tp = typical_price[start:end]
            segment_vol = volume[start:end]

            cum_tp_vol = np.cumsum(segment_tp * segment_vol)
            cum_vol = np.cumsum(segment_vol)

            # Avoid division by zero
            safe_vol = np.where(cum_vol > 0, cum_vol, 1.0)
            vwap[start:end] = cum_tp_vol / safe_vol

        return vwap

    @staticmethod
    def _rolling_zscore(series: np.ndarray, window: int) -> np.ndarray:
        """Compute rolling z-score of a series."""
        zscore = np.full_like(series, np.nan, dtype=float)
        for i in range(window - 1, len(series)):
            window_slice = series[i - window + 1:i + 1]
            mean = np.mean(window_slice)
            std = np.std(window_slice, ddof=1)
            if std > 1e-12:
                zscore[i] = (series[i] - mean) / std
            else:
                zscore[i] = 0.0
        return zscore

    @staticmethod
    def _compute_half_life(spread: np.ndarray) -> Optional[float]:
        """Estimate mean-reversion half-life via AR(1) regression.

        Regresses spread(t) on spread(t-1):
            spread(t) = alpha + beta * spread(t-1) + epsilon

        Half-life = -ln(2) / ln(beta)

        Returns None if regression is degenerate or beta >= 1 (no mean reversion).
        """
        if len(spread) < 10:
            return None

        y = spread[1:]
        x = spread[:-1]

        # OLS: beta = cov(x, y) / var(x)
        x_mean = np.mean(x)
        y_mean = np.mean(y)
        cov_xy = np.mean((x - x_mean) * (y - y_mean))
        var_x = np.var(x, ddof=0)

        if var_x < 1e-20:
            return None

        beta = cov_xy / var_x

        # beta must be in (0, 1) for mean reversion
        if beta <= 0 or beta >= 1.0:
            return None

        half_life = -np.log(2) / np.log(beta)
        return half_life

    @staticmethod
    def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
             period: int) -> np.ndarray:
        """Compute Average True Range."""
        tr = np.maximum(
            high[1:] - low[1:],
            np.maximum(
                np.abs(high[1:] - close[:-1]),
                np.abs(low[1:] - close[:-1])
            )
        )
        # Prepend NaN for first bar
        tr = np.concatenate([[np.nan], tr])

        atr = np.full_like(close, np.nan, dtype=float)
        if len(tr) < period + 1:
            return atr

        # Seed with SMA of true range
        atr[period] = np.nanmean(tr[1:period + 1])
        for i in range(period + 1, len(close)):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period

        return atr

    def _zscore_to_confidence(self, abs_zscore: float) -> float:
        """Convert absolute z-score magnitude to confidence [0, 1].

        Maps z-score range [entry_zscore, stop_zscore] to confidence [0.5, 0.95].
        Higher z-score = more extreme deviation = higher confidence in reversion.
        """
        min_z = self.entry_zscore
        max_z = self.stop_zscore
        min_conf = 0.50
        max_conf = 0.95

        if abs_zscore <= min_z:
            return min_conf
        if abs_zscore >= max_z:
            return max_conf

        ratio = (abs_zscore - min_z) / (max_z - min_z)
        return min_conf + ratio * (max_conf - min_conf)


# --- Standalone test / demo ---

if __name__ == "__main__":
    print("=" * 70)
    print("Cointegration Pairs Strategy — Standalone Test")
    print("=" * 70)

    try:
        import requests
        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": "BTCUSDT",
            "interval": "1h",
            "limit": 500
        }
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        raw = resp.json()

        df = pd.DataFrame(raw, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_vol', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
        df.set_index('timestamp', inplace=True)

        strategy = CointegrationPairsStrategy()
        signals = strategy.generate_signals(df, "BTCUSDT")

        if signals:
            for s in signals:
                print(f"\n  {s.direction} {s.symbol}")
                print(f"  Confidence : {s.confidence}")
                print(f"  Entry      : {s.entry_price}")
                print(f"  TP         : {s.take_profit}")
                print(f"  SL         : {s.stop_loss}")
                print(f"  Reason     : {s.reason}")
        else:
            print("\n  No signals — spread z-score within normal range or")
            print("  half-life exceeds threshold (market not mean-reverting).")

    except Exception as e:
        print(f"\n  Live test skipped: {e}")
        print("  (Requires internet + Binance API access)")

    print("\n" + "=" * 70)
