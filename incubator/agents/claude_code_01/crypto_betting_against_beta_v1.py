"""Betting Against Beta (BAB) — Adapted for Single-Symbol Crypto.

Based on Frazzini & Pedersen (2014):
"Betting Against Beta"
Published in Journal of Financial Economics, 111(1), 1-25.

Original insight: Across asset classes, low-beta assets deliver higher
risk-adjusted returns than high-beta assets because leverage-constrained
investors overweight risky assets, pushing up prices of high-beta securities
and depressing expected returns.

Single-symbol adaptation: Since we cannot rank across assets, we use
REALIZED VOLATILITY REGIMES as a proxy for the beta state of the asset
at different points in time. When the asset is in a LOW-VOLATILITY regime
(short-term vol << long-term vol), it behaves like a "low-beta" asset --
calm, underpriced risk premium, favorable entry. When in a HIGH-VOLATILITY
regime, the asset is "high-beta" -- overpriced, crowded, mean-reversion risk.

Documented Sharpe: 0.8-1.5 (original cross-asset BAB factor).

Signal logic:
  1. Compute trailing realized vol over 20d (short) and 60d (long).
  2. Vol ratio = short_vol / long_vol classifies the regime.
  3. Low-vol regime (ratio < 0.8): LONG with elevated confidence.
  4. High-vol regime (ratio > 1.3): SHORT or flat.
  5. Normal regime: trade only with EMA trend confirmation.
  6. Bollinger %B filter favors entries near the lower band in low-vol.
  7. Confidence scales inversely with the vol ratio.
  8. TP/SL are ATR-based and asymmetric (wider TP in calm markets).
"""

import numpy as np
import pandas as pd
from typing import List
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


class BettingAgainstBetaStrategy:
    """Betting Against Beta adapted for single-symbol crypto volatility regimes.

    Parameters
    ----------
    short_vol_window : int
        Lookback for short-term realized volatility (default 20).
    long_vol_window : int
        Lookback for long-term realized volatility (default 60).
    low_vol_threshold : float
        Vol ratio below which we consider the asset in a low-vol (low-beta)
        regime and go long (default 0.8).
    high_vol_threshold : float
        Vol ratio above which we consider the asset in a high-vol (high-beta)
        regime and go short or stay flat (default 1.3).
    ema_fast : int
        Fast EMA period for trend confirmation in normal regime (default 50).
    ema_slow : int
        Slow EMA period for trend confirmation in normal regime (default 200).
    bb_period : int
        Bollinger Band lookback (default 20).
    bb_std : float
        Bollinger Band standard deviation multiplier (default 2.0).
    atr_period : int
        ATR lookback for TP/SL calculation (default 14).
    tp_atr_mult : float
        Take-profit distance in ATR multiples -- wider for low-vol regimes
        where calmer, larger moves are expected (default 3.0).
    sl_atr_mult : float
        Stop-loss distance in ATR multiples -- kept tight to preserve
        the risk-adjusted edge (default 1.0).
    """

    def __init__(self, params=None):
        p = params or {}
        self.short_vol_window = p.get('short_vol_window', 20)
        self.long_vol_window = p.get('long_vol_window', 60)
        self.low_vol_threshold = p.get('low_vol_threshold', 0.8)
        self.high_vol_threshold = p.get('high_vol_threshold', 1.3)
        self.ema_fast = p.get('ema_fast', 50)
        self.ema_slow = p.get('ema_slow', 200)
        self.bb_period = p.get('bb_period', 20)
        self.bb_std = p.get('bb_std', 2.0)
        self.atr_period = p.get('atr_period', 14)
        self.tp_atr_mult = p.get('tp_atr_mult', 3.0)
        self.sl_atr_mult = p.get('sl_atr_mult', 1.0)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _realized_vol(returns: pd.Series, window: int) -> pd.Series:
        """Annualized realized volatility (rolling std of log returns)."""
        return returns.rolling(window).std() * np.sqrt(365)

    @staticmethod
    def _ema(series: pd.Series, span: int) -> pd.Series:
        return series.ewm(span=span, adjust=False).mean()

    @staticmethod
    def _bollinger_pct_b(
        close: pd.Series, period: int, num_std: float
    ) -> pd.Series:
        """Bollinger Band %B: (price - lower) / (upper - lower).

        Returns 0 at the lower band, 1 at the upper band.
        """
        mid = close.rolling(period).mean()
        std = close.rolling(period).std()
        upper = mid + num_std * std
        lower = mid - num_std * std
        band_width = upper - lower
        pct_b = (close - lower) / band_width.replace(0, np.nan)
        return pct_b

    @staticmethod
    def _atr(
        high: pd.Series, low: pd.Series, close: pd.Series, period: int
    ) -> pd.Series:
        """Average True Range."""
        prev_close = close.shift(1)
        tr = pd.concat(
            [
                high - low,
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        return tr.rolling(period).mean()

    def _compute_confidence(self, vol_ratio: float, pct_b: float) -> float:
        """Map vol ratio and Bollinger %B to a confidence score in [0, 1].

        Lower vol_ratio  -> higher confidence (low-beta = better edge).
        Lower %B         -> higher confidence (near lower band = value).
        """
        # Vol component: linear mapping from ratio to [0.5, 1.0]
        # At ratio=0.5 -> 1.0; at ratio=0.8 -> 0.5
        vol_conf = np.clip(1.0 - (vol_ratio - 0.3) / 1.0, 0.3, 1.0)

        # Band component: reward entries near the lower band
        # %B=0 -> 1.0 bonus; %B=0.5 -> 0.5; %B=1.0 -> 0.0
        band_conf = np.clip(1.0 - pct_b, 0.0, 1.0) if not np.isnan(pct_b) else 0.5

        # Weighted blend (vol regime is the primary signal)
        confidence = 0.7 * vol_conf + 0.3 * band_conf
        return round(float(np.clip(confidence, 0.0, 1.0)), 4)

    # ------------------------------------------------------------------
    # Main signal generation
    # ------------------------------------------------------------------

    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        """Generate BAB signals from OHLCV data.

        Parameters
        ----------
        data : pd.DataFrame
            Must contain columns: ``close``, ``high``, ``low``.
            Index should be datetime-like; rows in chronological order.
        symbol : str
            Trading pair symbol (default ``"BTCUSDT"``).

        Returns
        -------
        List[Signal]
            Zero or one Signal based on the latest bar's regime.
        """
        signals: List[Signal] = []

        min_rows = self.long_vol_window + self.ema_slow + 5
        if len(data) < min_rows:
            return signals

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)

        # --- Indicators ---
        log_returns = np.log(close / close.shift(1))

        short_vol = self._realized_vol(log_returns, self.short_vol_window)
        long_vol = self._realized_vol(log_returns, self.long_vol_window)
        vol_ratio = (short_vol / long_vol.replace(0, np.nan)).dropna()

        if vol_ratio.empty:
            return signals

        ema_f = self._ema(close, self.ema_fast)
        ema_s = self._ema(close, self.ema_slow)
        pct_b = self._bollinger_pct_b(close, self.bb_period, self.bb_std)
        atr = self._atr(high, low, close, self.atr_period)

        # --- Latest values ---
        latest_idx = data.index[-1]
        current_price = float(close.iloc[-1])
        current_vol_ratio = float(vol_ratio.iloc[-1])
        current_pct_b = float(pct_b.iloc[-1]) if not np.isnan(pct_b.iloc[-1]) else 0.5
        current_atr = float(atr.iloc[-1]) if not np.isnan(atr.iloc[-1]) else 0.0
        ema_fast_now = float(ema_f.iloc[-1])
        ema_slow_now = float(ema_s.iloc[-1])
        trend_bullish = ema_fast_now > ema_slow_now

        if current_atr <= 0:
            return signals

        # --- Regime classification ---
        direction = None
        reason_parts: List[str] = []

        if current_vol_ratio < self.low_vol_threshold:
            # LOW-VOL REGIME  ->  "low beta" state  ->  LONG
            direction = "BUY"
            reason_parts.append(
                f"LOW-VOL regime (vol_ratio={current_vol_ratio:.3f} "
                f"< {self.low_vol_threshold})"
            )
            # Prefer entries near the lower Bollinger band
            if current_pct_b < 0.3:
                reason_parts.append(
                    f"BB %B={current_pct_b:.2f} near lower band (value zone)"
                )
            elif current_pct_b > 0.8:
                # Near upper band in low vol -- still valid but lower confidence
                reason_parts.append(
                    f"BB %B={current_pct_b:.2f} near upper band (caution)"
                )

        elif current_vol_ratio > self.high_vol_threshold:
            # HIGH-VOL REGIME  ->  "high beta" state  ->  SHORT
            direction = "SELL"
            reason_parts.append(
                f"HIGH-VOL regime (vol_ratio={current_vol_ratio:.3f} "
                f"> {self.high_vol_threshold})"
            )
            if current_pct_b > 0.7:
                reason_parts.append(
                    f"BB %B={current_pct_b:.2f} near upper band (overextended)"
                )

        else:
            # NORMAL REGIME  ->  trade only with trend confirmation
            if trend_bullish:
                direction = "BUY"
                reason_parts.append(
                    f"NORMAL regime (vol_ratio={current_vol_ratio:.3f}) "
                    f"with bullish trend (EMA{self.ema_fast} > EMA{self.ema_slow})"
                )
            elif not trend_bullish:
                direction = "SELL"
                reason_parts.append(
                    f"NORMAL regime (vol_ratio={current_vol_ratio:.3f}) "
                    f"with bearish trend (EMA{self.ema_fast} < EMA{self.ema_slow})"
                )

        if direction is None:
            return signals

        # --- Confidence ---
        if direction == "BUY":
            confidence = self._compute_confidence(current_vol_ratio, current_pct_b)
        else:
            # For shorts, invert %B in confidence (high %B = better short entry)
            confidence = self._compute_confidence(
                current_vol_ratio, 1.0 - current_pct_b
            )

        # Normal-regime trades get a confidence haircut (weaker edge)
        if self.low_vol_threshold <= current_vol_ratio <= self.high_vol_threshold:
            confidence *= 0.7

        confidence = round(float(np.clip(confidence, 0.0, 1.0)), 4)

        # --- TP / SL (asymmetric, ATR-based) ---
        if direction == "BUY":
            tp = round(current_price + self.tp_atr_mult * current_atr, 2)
            sl = round(current_price - self.sl_atr_mult * current_atr, 2)
        else:
            tp = round(current_price - self.tp_atr_mult * current_atr, 2)
            sl = round(current_price + self.sl_atr_mult * current_atr, 2)

        reason = (
            f"BAB [{direction}] | "
            + " | ".join(reason_parts)
            + f" | TP/SL ratio={self.tp_atr_mult/self.sl_atr_mult:.1f}R"
        )

        signals.append(
            Signal(
                symbol=symbol,
                direction=direction,
                confidence=confidence,
                entry_price=current_price,
                take_profit=tp,
                stop_loss=sl,
                reason=reason,
            )
        )

        return signals


# ------------------------------------------------------------------
# Convenience runner
# ------------------------------------------------------------------

def fetch_binance_ohlcv(
    symbol: str = "BTCUSDT",
    interval: str = "1d",
    limit: int = 300,
) -> pd.DataFrame:
    """Fetch OHLCV from Binance public API (no key needed)."""
    import requests

    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    raw = resp.json()
    df = pd.DataFrame(
        raw,
        columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_vol", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore",
        ],
    )
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df.set_index("open_time", inplace=True)
    return df


if __name__ == "__main__":
    print("=" * 70)
    print("Betting Against Beta (Frazzini & Pedersen 2014) -- Crypto Adaptation")
    print("=" * 70)

    symbol = "BTCUSDT"
    df = fetch_binance_ohlcv(symbol, interval="1d", limit=300)
    print(f"\nFetched {len(df)} daily bars for {symbol}")

    strategy = BettingAgainstBetaStrategy()
    sigs = strategy.generate_signals(df, symbol=symbol)

    if sigs:
        for s in sigs:
            print(f"\n  Symbol:     {s.symbol}")
            print(f"  Direction:  {s.direction}")
            print(f"  Confidence: {s.confidence}")
            print(f"  Entry:      {s.entry_price}")
            print(f"  TP:         {s.take_profit}")
            print(f"  SL:         {s.stop_loss}")
            print(f"  Reason:     {s.reason}")
    else:
        print("\n  No signal generated (insufficient data or neutral regime).")

    print()
