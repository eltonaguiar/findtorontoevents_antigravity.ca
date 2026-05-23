"""
FundingRateExtreme - Contrarian Funding Rate Strategy
======================================================

Created by: web_ai
Date: 2026-03-28

Strategy Logic:
- Entry when: Funding rate z-score exceeds +/-2.0 (extreme leverage imbalance)
- BUY (contrarian) when funding z-score < -2.0 (shorts overleveraged) AND RSI < 45
- SELL (contrarian) when funding z-score > 2.0 (longs overleveraged) AND RSI > 55
- Exit when: TP = 2.5x ATR, SL = 1.5x ATR
- Risk management: Z-score threshold + RSI confirmation prevents false contrarian entries

Unique Value Proposition:
Funding rate extremes reflect crowded positioning in perpetual futures.
When funding is extremely positive, longs are paying shorts — overleveraged
longs get liquidated on any dip. When extremely negative, shorts are paying
longs — overleveraged shorts get squeezed on any bounce. The existing
funding_momentum strategy has 58.7% WR on 92 trades; this adds z-score
normalization and RSI confirmation for higher-quality contrarian entries.

Expected Regime: Mean-reversion after crowded positioning extremes.
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
    "XRPUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT",
]


class FundingRateExtremeStrategy:
    """
    Contrarian funding rate extremes with RSI confirmation.

    Detects extreme funding rate z-scores (crowded leverage) and takes
    the opposite side. Requires RSI confirmation to avoid fighting
    strong trends.

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
        self.zscore_window = self.params.get('zscore_window', 30)
        self.zscore_threshold = self.params.get('zscore_threshold', 2.0)
        self.rsi_buy_max = self.params.get('rsi_buy_max', 45)
        self.rsi_sell_min = self.params.get('rsi_sell_min', 55)
        self.tp_atr = self.params.get('tp_atr', 2.5)
        self.sl_atr = self.params.get('sl_atr', 1.5)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        """
        Main signal generation method.

        Args:
            data: DataFrame with columns [open, high, low, close, volume]
                  and optionally [funding_rate].
            symbol: Trading pair being analyzed

        Returns:
            List of Signal objects (empty if no signal)
        """
        # Ensure we have funding_rate column
        if 'funding_rate' not in data.columns:
            funding = self._fetch_funding_rate(symbol)
            if funding is None or funding.empty:
                return []
            data = data.copy()
            data['funding_rate'] = funding.reindex(data.index, method='ffill')

        # Validate minimum data length
        min_len = self.zscore_window + self.atr_period + self.rsi_period + 10
        if len(data) < min_len:
            return []

        # Drop rows where funding_rate is NaN
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

        # Current values
        current_zscore = fr_zscore.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_price = data['close'].iloc[-1]
        current_atr = atr.iloc[-1]

        if pd.isna(current_zscore) or pd.isna(current_rsi) or pd.isna(current_atr):
            return []

        # Confidence: 0.55 + abs(z_score - 2) * 0.1, capped at 0.85
        def calc_confidence(z):
            return min(0.55 + (abs(z) - self.zscore_threshold) * 0.1, 0.85)

        signals = []

        # BUY: extreme negative funding (shorts overleveraged) + RSI < 45
        if current_zscore < -self.zscore_threshold and current_rsi < self.rsi_buy_max:
            confidence = calc_confidence(current_zscore)
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 2),
                entry_price=round(current_price, 2),
                take_profit=round(current_price + current_atr * self.tp_atr, 2),
                stop_loss=round(current_price - current_atr * self.sl_atr, 2),
                reason=f"FundingZscore={current_zscore:.2f} RSI={current_rsi:.1f} shorts_overleveraged"
            ))

        # SELL: extreme positive funding (longs overleveraged) + RSI > 55
        elif current_zscore > self.zscore_threshold and current_rsi > self.rsi_sell_min:
            confidence = calc_confidence(current_zscore)
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 2),
                entry_price=round(current_price, 2),
                take_profit=round(current_price - current_atr * self.tp_atr, 2),
                stop_loss=round(current_price + current_atr * self.sl_atr, 2),
                reason=f"FundingZscore={current_zscore:.2f} RSI={current_rsi:.1f} longs_overleveraged"
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
                url = f"{base}/fapi/v1/fundingRate?symbol={symbol}&limit=8"
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if data:
                        idx = pd.to_datetime([r['fundingTime'] for r in data], unit='ms')
                        return pd.Series(
                            [float(r['fundingRate']) for r in data],
                            index=idx
                        )
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
# BACKTEST - Walk-forward on 90 days of 1h data
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

    page = 0
    while current_start < end_ms:
        page += 1
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
                        current_start = end_ms  # signal done
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
                        current_start = end_ms  # signal done
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


def _vectorized_backtest(klines: pd.DataFrame, sym: str, max_hold: int = 24):
    """Vectorized signal detection + sequential trade simulation."""
    strategy = FundingRateExtremeStrategy()
    atr_period = strategy.atr_period
    rsi_period = strategy.rsi_period
    zscore_window = strategy.zscore_window

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

    warmup = zscore_window + atr_period + rsi_period + 10
    trades = []
    i = warmup

    while i < len(klines):
        z = fr_zscore.iloc[i]
        r = rsi.iloc[i]
        a = atr.iloc[i]
        p = close.iloc[i]

        if pd.isna(z) or pd.isna(r) or pd.isna(a):
            i += 1
            continue

        direction = None
        if z < -2.0 and r < 45:
            direction = "BUY"
        elif z > 2.0 and r > 55:
            direction = "SELL"

        if direction is None:
            i += 1
            continue

        conf = min(0.55 + (abs(z) - 2.0) * 0.1, 0.85)
        tp_price = p + a * 2.5 if direction == "BUY" else p - a * 2.5
        sl_price = p - a * 1.5 if direction == "BUY" else p + a * 1.5

        exit_price = None
        exit_reason = None
        for j in range(1, max_hold + 1):
            if i + j >= len(klines):
                break
            bh = klines.iloc[i + j]['high']
            bl = klines.iloc[i + j]['low']
            if direction == "BUY":
                if bh >= tp_price:
                    exit_price, exit_reason = tp_price, "TP"
                    break
                if bl <= sl_price:
                    exit_price, exit_reason = sl_price, "SL"
                    break
            else:
                if bl <= tp_price:
                    exit_price, exit_reason = tp_price, "TP"
                    break
                if bh >= sl_price:
                    exit_price, exit_reason = sl_price, "SL"
                    break

        if exit_price is None:
            exit_idx = min(i + max_hold, len(klines) - 1)
            exit_price = klines.iloc[exit_idx]['close']
            exit_reason = "TIMEOUT"

        pnl = (exit_price - p) / p * 100 if direction == "BUY" else (p - exit_price) / p * 100

        trades.append({
            'symbol': sym, 'direction': direction, 'confidence': round(conf, 2),
            'entry': round(p, 2), 'exit': round(exit_price, 2),
            'pnl_pct': round(pnl, 4), 'exit_reason': exit_reason,
            'reason': f"FundingZscore={z:.2f} RSI={r:.1f}",
        })
        i += max_hold  # skip ahead
        continue

    return trades


if __name__ == "__main__":
    """Backtest: 90 days, 1h bars, 24-bar max hold."""
    import sys

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

        funding = _fetch_all_funding(sym, 90)
        if funding.empty:
            print(f"  No funding data for {sym}, skipping", flush=True)
            continue

        # Merge funding into klines (forward-fill 8h funding to 1h bars)
        klines = klines.copy()
        klines['funding_rate'] = funding.reindex(klines.index, method='ffill')

        print(f"  {len(funding)} funding records, range: [{funding.min():.6f}, {funding.max():.6f}]", flush=True)

        trades = _vectorized_backtest(klines, sym, max_hold)
        all_trades.extend(trades)
        print(f"  {len(trades)} trades found", flush=True)

    # ---- Results ----
    print("\n" + "=" * 60, flush=True)
    print("FUNDING RATE EXTREME - BACKTEST RESULTS", flush=True)
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
        pf = (wins['pnl_pct'].sum() / abs(losses['pnl_pct'].sum())) if len(losses) and losses['pnl_pct'].sum() != 0 else float('inf')

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
            print(f"  {sym}: {len(sub)} trades, WR={swr:.0f}%, PnL={sub['pnl_pct'].sum():.2f}%", flush=True)

        print(f"\nBy exit reason:", flush=True)
        for reason in df['exit_reason'].unique():
            sub = df[df['exit_reason'] == reason]
            print(f"  {reason}: {len(sub)} trades, avg={sub['pnl_pct'].mean():.3f}%", flush=True)

        print(f"\nSample trades:", flush=True)
        for _, t in df.head(5).iterrows():
            print(f"  {t['symbol']} {t['direction']} conf={t['confidence']:.2f} "
                  f"pnl={t['pnl_pct']:+.3f}% ({t['exit_reason']}) {t['reason']}", flush=True)
