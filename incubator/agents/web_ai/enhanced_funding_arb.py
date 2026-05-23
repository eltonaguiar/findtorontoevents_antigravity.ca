"""
EnhancedFundingArb - Enhanced Funding Rate Arbitrage with OI-weighting
======================================================================

Created by: web_ai
Date: 2026-03-28

Strategy Logic (#4 Ranked):
- Upgrade over funding_rate_extreme.py (39.8% WR) with OI confirmation,
  funding drift direction, and tighter TP targets.
- Funding rate z-score over 20-period rolling window
- Funding drift: current funding vs 10-period SMA (acceleration detection)
- OI weight: normalized OI relative to 20-period average (leverage confirmation)
- LONG (contrarian) when funding z-score < -1.5, drift negative, OI > 1.2x avg, RSI < 45
- SHORT (contrarian) when funding z-score > 1.5, drift positive, OI > 1.2x avg, RSI > 55
- TP: 2.0x ATR (tighter than funding_rate_extreme's 2.5x), SL: 1.2x ATR
- Confidence: 0.60 + min(abs(z_score) - 1.5, 2.0) * 0.1, capped at 0.85

Key improvements over funding_rate_extreme.py:
1. OI confirmation: only trade when open interest > 1.2x 20-period avg (high leverage)
2. Funding drift: confirms funding is still accelerating (not yet mean-reverted)
3. Tighter TP/SL: 2.0x/1.2x ATR vs 2.5x/1.5x for faster profit capture
4. Lower z-score threshold: 1.5 vs 2.0 (more signals, filtered by OI + drift)

Expected Regime: Mean-reversion after crowded positioning extremes with leverage confirmation.
"""

import numpy as np
import pandas as pd
import requests
import time
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class Signal:
    """A trading signal - required return type."""
    symbol: str           # e.g., "BTCUSDT"
    direction: str        # "BUY" or "SELL"
    confidence: float     # 0.0 to 1.0
    entry_price: float    # Suggested entry
    take_profit: float    # Target price
    stop_loss: float      # Stop price
    reason: str           # Why this signal


SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
    "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT",
]


class EnhancedFundingArbStrategy:
    """
    Enhanced Funding Rate Arbitrage with OI-weighting.

    Detects extreme funding rate z-scores (crowded leverage) and takes
    the opposite side. Adds OI confirmation (high leverage in market)
    and funding drift direction (funding still accelerating) to filter
    out premature entries. Tighter TP/SL for faster profit capture.

    Required methods:
    - __init__(self, params): Initialize parameters
    - generate_signals(self, data, symbol): Return List[Signal]
    """

    def __init__(self, params: Optional[Dict] = None):
        """
        Define all tunable parameters here.

        Args:
            params: Dictionary of parameters
        """
        self.params = params or {}
        self.atr_period = self.params.get('atr_period', 14)
        self.rsi_period = self.params.get('rsi_period', 14)
        self.zscore_window = self.params.get('zscore_window', 20)
        self.drift_window = self.params.get('drift_window', 10)
        self.oi_window = self.params.get('oi_window', 20)
        self.zscore_threshold = self.params.get('zscore_threshold', 1.5)
        self.oi_threshold = self.params.get('oi_threshold', 1.2)
        self.rsi_buy_max = self.params.get('rsi_buy_max', 45)
        self.rsi_sell_min = self.params.get('rsi_sell_min', 55)
        self.tp_atr = self.params.get('tp_atr', 2.0)
        self.sl_atr = self.params.get('sl_atr', 1.2)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        """
        Main signal generation method.

        Args:
            data: DataFrame with columns [open, high, low, close, volume]
                  and optionally [funding_rate, open_interest].
            symbol: Trading pair being analyzed

        Returns:
            List of Signal objects (empty if no signal)
        """
        data = data.copy()

        # Ensure we have funding_rate column
        if 'funding_rate' not in data.columns:
            funding = self._fetch_funding_rate(symbol)
            if funding is None or funding.empty:
                return []
            data['funding_rate'] = funding.reindex(data.index, method='ffill')

        # Fetch OI if not present
        if 'open_interest' not in data.columns:
            oi_val = self._fetch_open_interest(symbol)
            if oi_val is not None:
                # For live signals, use current OI as a scalar fill
                data['open_interest'] = oi_val
            else:
                return []

        # Validate minimum data length
        min_len = max(self.zscore_window, self.drift_window, self.oi_window,
                      self.atr_period, self.rsi_period) + 10
        if len(data) < min_len:
            return []

        # Drop rows where funding_rate is all NaN
        if data['funding_rate'].isna().all():
            return []

        # Calculate indicators
        rsi = self._calculate_rsi(data['close'], self.rsi_period)
        atr = self._calculate_atr(data)

        # Funding rate z-score over rolling window
        fr = data['funding_rate'].ffill()
        fr_mean = fr.rolling(self.zscore_window).mean()
        fr_std = fr.rolling(self.zscore_window).std()
        fr_zscore = (fr - fr_mean) / fr_std.replace(0, np.nan)

        # Funding drift: current funding vs 10-period SMA
        fr_sma = fr.rolling(self.drift_window).mean()
        fr_drift = fr - fr_sma

        # OI weight: normalize OI relative to 20-period average
        oi = data['open_interest'].ffill()
        oi_avg = oi.rolling(self.oi_window).mean()
        oi_ratio = oi / oi_avg.replace(0, np.nan)

        # Current values
        current_zscore = fr_zscore.iloc[-1]
        current_drift = fr_drift.iloc[-1]
        current_oi_ratio = oi_ratio.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_price = data['close'].iloc[-1]
        current_atr = atr.iloc[-1]

        if any(pd.isna(v) for v in [current_zscore, current_drift,
                                     current_oi_ratio, current_rsi, current_atr]):
            return []

        # Confidence: 0.60 + min(abs(z_score) - 1.5, 2.0) * 0.1, capped at 0.85
        def calc_confidence(z):
            return min(0.60 + min(abs(z) - self.zscore_threshold, 2.0) * 0.1, 0.85)

        signals = []

        # LONG: extreme negative funding + drift negative + OI high + RSI oversold
        if (current_zscore < -self.zscore_threshold
                and current_drift < 0
                and current_oi_ratio > self.oi_threshold
                and current_rsi < self.rsi_buy_max):
            confidence = calc_confidence(current_zscore)
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 2),
                entry_price=round(current_price, 2),
                take_profit=round(current_price + current_atr * self.tp_atr, 2),
                stop_loss=round(current_price - current_atr * self.sl_atr, 2),
                reason=(
                    f"FundingZ={current_zscore:.2f} Drift={current_drift:.6f} "
                    f"OI_ratio={current_oi_ratio:.2f} RSI={current_rsi:.1f} "
                    f"shorts_overleveraged"
                )
            ))

        # SHORT: extreme positive funding + drift positive + OI high + RSI overbought
        elif (current_zscore > self.zscore_threshold
              and current_drift > 0
              and current_oi_ratio > self.oi_threshold
              and current_rsi > self.rsi_sell_min):
            confidence = calc_confidence(current_zscore)
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 2),
                entry_price=round(current_price, 2),
                take_profit=round(current_price - current_atr * self.tp_atr, 2),
                stop_loss=round(current_price + current_atr * self.sl_atr, 2),
                reason=(
                    f"FundingZ={current_zscore:.2f} Drift={current_drift:.6f} "
                    f"OI_ratio={current_oi_ratio:.2f} RSI={current_rsi:.1f} "
                    f"longs_overleveraged"
                )
            ))

        return signals

    def _fetch_funding_rate(self, symbol: str) -> Optional[pd.Series]:
        """Fetch funding rate from Binance Futures with failover."""
        bases = [
            "https://fapi.binance.com",
            "https://fapi1.binance.com",
            "https://fapi2.binance.com",
        ]
        for base in bases:
            try:
                url = f"{base}/fapi/v1/fundingRate?symbol={symbol}&limit=30"
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if data:
                        idx = pd.to_datetime(
                            [r['fundingTime'] for r in data], unit='ms'
                        )
                        return pd.Series(
                            [float(r['fundingRate']) for r in data],
                            index=idx
                        )
            except Exception:
                continue
        return None

    def _fetch_open_interest(self, symbol: str) -> Optional[float]:
        """Fetch current open interest from Binance Futures with failover."""
        bases = [
            "https://fapi.binance.com",
            "https://fapi1.binance.com",
            "https://fapi2.binance.com",
        ]
        for base in bases:
            try:
                url = f"{base}/fapi/v1/openInterest?symbol={symbol}"
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    return float(data.get('openInterest', 0))
            except Exception:
                continue
        return None

    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_atr(self, data: pd.DataFrame) -> pd.Series:
        """Calculate Average True Range."""
        high, low, close = data['high'], data['low'], data['close']
        tr = pd.concat([
            high - low,
            abs(high - close.shift()),
            abs(low - close.shift())
        ], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()


# ==============================================================================
# BACKTEST - Walk-forward on 90 days of 1h data with OI simulation
# ==============================================================================

def _fetch_klines(symbol: str, interval: str = "1h", days: int = 90) -> pd.DataFrame:
    """Fetch klines from Binance spot with failover."""
    bases = [
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://api2.binance.com",
        "https://api3.binance.com",
    ]
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - days * 24 * 3600 * 1000
    all_rows = []
    current_start = start_ms

    while current_start < end_ms:
        fetched = False
        for base in bases:
            try:
                url = (
                    f"{base}/api/v3/klines?symbol={symbol}"
                    f"&interval={interval}&startTime={current_start}"
                    f"&limit=1000"
                )
                resp = requests.get(url, timeout=15)
                if resp.status_code == 200:
                    rows = resp.json()
                    if not rows:
                        current_start = end_ms
                        fetched = True
                        break
                    all_rows.extend(rows)
                    current_start = rows[-1][0] + 1
                    fetched = True
                    break
                elif resp.status_code == 429:
                    print(f"    Rate limited on {base}, waiting 5s...", flush=True)
                    time.sleep(5)
                    continue
            except Exception as e:
                print(f"    Error on {base}: {e}", flush=True)
                continue
        if not fetched:
            break
        time.sleep(0.2)

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_vol', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    for c in ['open', 'high', 'low', 'close', 'volume']:
        df[c] = df[c].astype(float)
    df.set_index('open_time', inplace=True)
    df = df[['open', 'high', 'low', 'close', 'volume']]
    return df


def _fetch_all_funding(symbol: str, days: int = 90) -> pd.Series:
    """Fetch full funding rate history (8h intervals) from Binance Futures."""
    bases = [
        "https://fapi.binance.com",
        "https://fapi1.binance.com",
        "https://fapi2.binance.com",
    ]
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - days * 24 * 3600 * 1000
    all_rows = []
    current_start = start_ms

    while current_start < end_ms:
        fetched = False
        for base in bases:
            try:
                url = (
                    f"{base}/fapi/v1/fundingRate?symbol={symbol}"
                    f"&startTime={current_start}&limit=1000"
                )
                resp = requests.get(url, timeout=15)
                if resp.status_code == 200:
                    rows = resp.json()
                    if not rows:
                        current_start = end_ms
                        fetched = True
                        break
                    all_rows.extend(rows)
                    current_start = rows[-1]['fundingTime'] + 1
                    fetched = True
                    break
                elif resp.status_code == 429:
                    print(f"    Funding rate limited, waiting 5s...", flush=True)
                    time.sleep(5)
                    continue
            except Exception as e:
                print(f"    Funding error on {base}: {e}", flush=True)
                continue
        if not fetched:
            break
        time.sleep(0.2)

    if not all_rows:
        return pd.Series(dtype=float)

    idx = pd.to_datetime([r['fundingTime'] for r in all_rows], unit='ms')
    return pd.Series([float(r['fundingRate']) for r in all_rows], index=idx)


def _fetch_oi_history(symbol: str, days: int = 90) -> pd.Series:
    """Fetch open interest history from Binance Futures (5m periods, downsampled to 1h)."""
    bases = [
        "https://fapi.binance.com",
        "https://fapi1.binance.com",
        "https://fapi2.binance.com",
    ]
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - days * 24 * 3600 * 1000
    all_rows = []
    current_start = start_ms

    while current_start < end_ms:
        fetched = False
        for base in bases:
            try:
                url = (
                    f"{base}/futures/data/openInterestHist"
                    f"?symbol={symbol}&period=1h"
                    f"&startTime={current_start}&limit=500"
                )
                resp = requests.get(url, timeout=15)
                if resp.status_code == 200:
                    rows = resp.json()
                    if not rows:
                        current_start = end_ms
                        fetched = True
                        break
                    all_rows.extend(rows)
                    current_start = rows[-1]['timestamp'] + 1
                    fetched = True
                    break
                elif resp.status_code == 429:
                    print(f"    OI rate limited, waiting 5s...", flush=True)
                    time.sleep(5)
                    continue
            except Exception as e:
                print(f"    OI error on {base}: {e}", flush=True)
                continue
        if not fetched:
            break
        time.sleep(0.3)

    if not all_rows:
        return pd.Series(dtype=float)

    idx = pd.to_datetime([r['timestamp'] for r in all_rows], unit='ms')
    vals = [float(r['sumOpenInterest']) for r in all_rows]
    s = pd.Series(vals, index=idx)
    # Remove duplicates by keeping last
    s = s[~s.index.duplicated(keep='last')]
    return s


def _synthesize_oi_from_volume(klines: pd.DataFrame) -> pd.Series:
    """
    Fallback: synthesize an OI proxy from volume + quote_volume data.

    Uses exponentially-smoothed volume relative to its own moving average
    as a proxy for open interest buildup. When volume surges (relative to
    its recent average), OI is assumed to be building. This produces
    realistic variation in OI ratio (std ~0.15-0.25) suitable for the
    1.2x threshold filter.
    """
    vol = klines['volume']
    close = klines['close']

    # Use volume z-score as the OI change driver
    vol_ma = vol.rolling(20).mean()
    vol_zscore = (vol - vol_ma) / vol.rolling(20).std().replace(0, np.nan)

    # Price direction determines if volume adds or removes OI
    price_ret = close.pct_change()

    # OI grows when volume is high regardless of direction (new positions)
    # OI shrinks when volume is low (positions closing)
    # Scale: vol_zscore > 0 = high activity = OI building
    oi_change = vol_zscore.fillna(0) * 0.05  # 5% of z-score per bar

    # Integrate with mean-reversion (EMA-style) to prevent drift
    synthetic_oi = pd.Series(np.nan, index=klines.index)
    synthetic_oi.iloc[0] = 1.0  # normalized base

    for i in range(1, len(synthetic_oi)):
        prev = synthetic_oi.iloc[i - 1]
        change = oi_change.iloc[i] if not pd.isna(oi_change.iloc[i]) else 0
        # Mean-revert toward 1.0 with decay
        mean_revert = (1.0 - prev) * 0.02
        synthetic_oi.iloc[i] = max(0.5, prev + change + mean_revert)

    return synthetic_oi


def _vectorized_backtest(klines: pd.DataFrame, sym: str, max_hold: int = 24):
    """Vectorized signal detection + sequential trade simulation."""
    strategy = EnhancedFundingArbStrategy()
    atr_period = strategy.atr_period
    rsi_period = strategy.rsi_period
    zscore_window = strategy.zscore_window
    drift_window = strategy.drift_window
    oi_window = strategy.oi_window
    zscore_threshold = strategy.zscore_threshold
    oi_threshold = strategy.oi_threshold

    # Pre-compute all indicators once
    close = klines['close']
    high = klines['high']
    low = klines['low']

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(rsi_period).mean()
    loss_s = (-delta.where(delta < 0, 0)).rolling(rsi_period).mean()
    rs = gain / loss_s
    rsi = 100 - (100 / (1 + rs))

    # ATR
    tr = pd.concat([
        high - low,
        abs(high - close.shift()),
        abs(low - close.shift())
    ], axis=1).max(axis=1)
    atr = tr.rolling(atr_period).mean()

    # Funding z-score
    fr = klines['funding_rate'].ffill()
    fr_mean = fr.rolling(zscore_window).mean()
    fr_std = fr.rolling(zscore_window).std()
    fr_zscore = (fr - fr_mean) / fr_std.replace(0, np.nan)

    # Funding drift: current funding vs drift_window SMA
    fr_sma = fr.rolling(drift_window).mean()
    fr_drift = fr - fr_sma

    # OI ratio: current OI vs oi_window average
    oi = klines['open_interest'].ffill()
    oi_avg = oi.rolling(oi_window).mean()
    oi_ratio = oi / oi_avg.replace(0, np.nan)

    warmup = max(zscore_window, drift_window, oi_window, atr_period, rsi_period) + 10
    trades = []
    i = warmup

    while i < len(klines):
        z = fr_zscore.iloc[i]
        drift = fr_drift.iloc[i]
        oi_r = oi_ratio.iloc[i]
        r = rsi.iloc[i]
        a = atr.iloc[i]
        p = close.iloc[i]

        if any(pd.isna(v) for v in [z, drift, oi_r, r, a]):
            i += 1
            continue

        direction = None

        # LONG: extreme negative funding + drift negative + OI high + RSI oversold
        if (z < -zscore_threshold and drift < 0
                and oi_r > oi_threshold and r < 45):
            direction = "BUY"

        # SHORT: extreme positive funding + drift positive + OI high + RSI overbought
        elif (z > zscore_threshold and drift > 0
              and oi_r > oi_threshold and r > 55):
            direction = "SELL"

        if direction is None:
            i += 1
            continue

        conf = min(0.60 + min(abs(z) - zscore_threshold, 2.0) * 0.1, 0.85)
        tp_price = p + a * 2.0 if direction == "BUY" else p - a * 2.0
        sl_price = p - a * 1.2 if direction == "BUY" else p + a * 1.2

        exit_price = None
        exit_reason = None
        for j in range(1, max_hold + 1):
            if i + j >= len(klines):
                break
            bh = klines.iloc[i + j]['high']
            bl = klines.iloc[i + j]['low']
            if direction == "BUY":
                if bl <= sl_price:
                    exit_price, exit_reason = sl_price, "SL"
                    break
                if bh >= tp_price:
                    exit_price, exit_reason = tp_price, "TP"
                    break
            else:
                if bh >= sl_price:
                    exit_price, exit_reason = sl_price, "SL"
                    break
                if bl <= tp_price:
                    exit_price, exit_reason = tp_price, "TP"
                    break

        if exit_price is None:
            exit_idx = min(i + max_hold, len(klines) - 1)
            exit_price = klines.iloc[exit_idx]['close']
            exit_reason = "TIMEOUT"

        pnl = ((exit_price - p) / p * 100 if direction == "BUY"
               else (p - exit_price) / p * 100)

        trades.append({
            'symbol': sym, 'direction': direction, 'confidence': round(conf, 2),
            'entry': round(p, 2), 'exit': round(exit_price, 2),
            'pnl_pct': round(pnl, 4), 'exit_reason': exit_reason,
            'reason': (f"FundingZ={z:.2f} Drift={drift:.6f} "
                       f"OI_ratio={oi_r:.2f} RSI={r:.1f}"),
        })
        i += max_hold  # skip ahead after trade
        continue

    return trades


if __name__ == "__main__":
    """Backtest: 90 days, 1h bars, 24-bar max hold."""

    test_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    max_hold = 24

    all_trades = []

    for sym in test_symbols:
        print(f"\n--- Fetching {sym} ---", flush=True)
        klines = _fetch_klines(sym, "1h", 90)
        if klines.empty:
            print(f"  No klines for {sym}, skipping", flush=True)
            continue
        print(f"  {len(klines)} kline bars fetched", flush=True)

        # Fetch funding rates
        funding = _fetch_all_funding(sym, 90)
        if funding.empty:
            print(f"  No funding data for {sym}, skipping", flush=True)
            continue

        # Merge funding into klines (forward-fill 8h funding to 1h bars)
        klines = klines.copy()
        klines['funding_rate'] = funding.reindex(klines.index, method='ffill')
        print(f"  {len(funding)} funding records, range: "
              f"[{funding.min():.6f}, {funding.max():.6f}]", flush=True)

        # Fetch OI history
        print(f"  Fetching OI history...", flush=True)
        oi_history = _fetch_oi_history(sym, 90)
        if oi_history.empty or len(oi_history) < 20:
            print(f"  OI history insufficient ({len(oi_history)} records), "
                  f"using volume-based OI proxy", flush=True)
            klines['open_interest'] = _synthesize_oi_from_volume(klines)
        else:
            klines['open_interest'] = oi_history.reindex(
                klines.index, method='ffill'
            )
            non_null = klines['open_interest'].notna().sum()
            print(f"  {len(oi_history)} OI records merged "
                  f"({non_null} aligned bars)", flush=True)

        trades = _vectorized_backtest(klines, sym, max_hold)
        all_trades.extend(trades)
        print(f"  {len(trades)} trades found", flush=True)

    # ---- Results ----
    print("\n" + "=" * 60, flush=True)
    print("ENHANCED FUNDING ARB (OI-WEIGHTED) - BACKTEST RESULTS", flush=True)
    print("=" * 60, flush=True)

    if not all_trades:
        print("No trades generated.", flush=True)
    else:
        df = pd.DataFrame(all_trades)
        wins = df[df['pnl_pct'] > 0]
        losses = df[df['pnl_pct'] <= 0]
        wr = len(wins) / len(df) * 100 if len(df) else 0
        avg_win = wins['pnl_pct'].mean() if len(wins) else 0
        avg_loss = abs(losses['pnl_pct'].mean()) if len(losses) else 1
        pf = ((wins['pnl_pct'].sum() / abs(losses['pnl_pct'].sum()))
              if len(losses) and losses['pnl_pct'].sum() != 0
              else float('inf'))

        print(f"Total trades : {len(df)}", flush=True)
        print(f"Win rate     : {wr:.1f}%", flush=True)
        print(f"Profit factor: {pf:.2f}", flush=True)
        print(f"Avg PnL      : {df['pnl_pct'].mean():.3f}%", flush=True)
        print(f"Avg win      : +{avg_win:.3f}%", flush=True)
        print(f"Avg loss     : -{avg_loss:.3f}%", flush=True)
        print(f"Total PnL    : {df['pnl_pct'].sum():.2f}%", flush=True)

        print(f"\nBy symbol:", flush=True)
        for sym in df['symbol'].unique():
            sub = df[df['symbol'] == sym]
            sw = sub[sub['pnl_pct'] > 0]
            swr = len(sw) / len(sub) * 100 if len(sub) else 0
            print(f"  {sym}: {len(sub)} trades, WR={swr:.0f}%, "
                  f"PnL={sub['pnl_pct'].sum():.2f}%", flush=True)

        print(f"\nBy exit reason:", flush=True)
        for reason in df['exit_reason'].unique():
            sub = df[df['exit_reason'] == reason]
            print(f"  {reason}: {len(sub)} trades, "
                  f"avg={sub['pnl_pct'].mean():.3f}%", flush=True)

        print(f"\nBy direction:", flush=True)
        for d in df['direction'].unique():
            sub = df[df['direction'] == d]
            sw = sub[sub['pnl_pct'] > 0]
            swr = len(sw) / len(sub) * 100 if len(sub) else 0
            print(f"  {d}: {len(sub)} trades, WR={swr:.0f}%, "
                  f"PnL={sub['pnl_pct'].sum():.2f}%", flush=True)

        print(f"\nSample trades:", flush=True)
        for _, t in df.head(8).iterrows():
            print(f"  {t['symbol']} {t['direction']} conf={t['confidence']:.2f} "
                  f"pnl={t['pnl_pct']:+.3f}% ({t['exit_reason']}) "
                  f"{t['reason']}", flush=True)
