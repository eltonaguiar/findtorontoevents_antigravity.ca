"""
Inverse ATR Regime RSI
=======================
Original: atr_regime_rsi -- 19.4% WR, -18.9% PnL, 31 trades
Original logic: Low-vol regime (ATR < rolling avg * threshold) AND RSI < 35 -> BUY
Inverse: same conditions -> SELL (short)
Also inverse the high-vol side: High-vol + RSI > 65 (original would avoid) -> BUY

Rationale: In crypto, low-vol + oversold RSI often precedes further breakdown
(capitulation phase), not recovery. The original's mean-reversion assumption
fails because crypto low-vol regimes can be distribution, not accumulation.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Optional
import requests
import time


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class InverseATRRegimeRSIStrategy:
    """
    Fades the ATR regime + RSI mean-reversion signal.

    Original: low-vol + RSI<35 -> BUY (mean reversion)
    Inverse: low-vol + RSI<35 -> SELL (expect further breakdown)
    Bonus: high-vol + RSI>65 -> BUY (breakout continuation)
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.rsi_period = self.params.get('rsi_period', 14)
        self.rsi_os = self.params.get('rsi_oversold', 30)    # tighter
        self.rsi_ob = self.params.get('rsi_overbought', 70)   # tighter
        self.atr_period = self.params.get('atr_period', 14)
        self.regime_lookback = self.params.get('regime_lookback', 50)
        self.vol_threshold_low = self.params.get('vol_threshold_low', 0.8)  # stricter low-vol
        self.vol_threshold_high = self.params.get('vol_threshold_high', 1.5)  # clear high-vol
        self.tp_atr = self.params.get('tp_atr', 2.0)
        self.sl_atr = self.params.get('sl_atr', 1.2)
        self.cooldown = self.params.get('cooldown', 12)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_len = self.regime_lookback + self.atr_period + self.rsi_period + 10
        if len(data) < min_len:
            return []

        rsi = self._calculate_rsi(data['close'], self.rsi_period)
        atr = self._calculate_atr(data)
        atr_ma = atr.rolling(self.regime_lookback).mean()

        signals = []
        last_signal_bar = -self.cooldown
        for i in range(min_len, len(data)):
            if i - last_signal_bar < self.cooldown:
                continue

            cur_rsi = rsi.iloc[i]
            cur_atr = atr.iloc[i]
            cur_atr_ma = atr_ma.iloc[i]
            cur_price = data['close'].iloc[i]

            if pd.isna(cur_rsi) or pd.isna(cur_atr) or pd.isna(cur_atr_ma) or cur_atr_ma == 0:
                continue

            atr_ratio = cur_atr / cur_atr_ma
            is_low_vol = atr_ratio < self.vol_threshold_low
            is_high_vol = atr_ratio > self.vol_threshold_high

            # Check price trend confirmation (5-bar slope)
            if i < 5:
                continue
            price_slope = (data['close'].iloc[i] - data['close'].iloc[i - 5]) / data['close'].iloc[i - 5]

            # INVERSE of original: low-vol + oversold + downtrend -> SELL
            if is_low_vol and cur_rsi < self.rsi_os and price_slope < -0.01:
                confidence = min((self.rsi_os - cur_rsi) / self.rsi_os * 0.8 + 0.2, 0.95)
                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 2),
                    entry_price=cur_price,
                    take_profit=round(cur_price - cur_atr * self.tp_atr, 2),
                    stop_loss=round(cur_price + cur_atr * self.sl_atr, 2),
                    reason=f"INV_ATR_RSI: LowVol ATR_ratio={atr_ratio:.2f} RSI={cur_rsi:.1f} slope={price_slope:.3f} -> SHORT"
                ))
                last_signal_bar = i

            # INVERSE bonus: high-vol + overbought + uptrend -> BUY continuation
            elif is_high_vol and cur_rsi > self.rsi_ob and price_slope > 0.02:
                confidence = min((cur_rsi - self.rsi_ob) / 30 * 0.6 + 0.3, 0.90)
                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 2),
                    entry_price=cur_price,
                    take_profit=round(cur_price + cur_atr * self.tp_atr, 2),
                    stop_loss=round(cur_price - cur_atr * self.sl_atr, 2),
                    reason=f"INV_ATR_RSI: HighVol ATR_ratio={atr_ratio:.2f} RSI={cur_rsi:.1f} slope={price_slope:.3f} -> LONG"
                ))
                last_signal_bar = i

        return signals

    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_atr(self, data: pd.DataFrame) -> pd.Series:
        high, low, close = data['high'], data['low'], data['close']
        tr = pd.concat([
            high - low,
            abs(high - close.shift()),
            abs(low - close.shift())
        ], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()


# ==============================================================================
# BACKTEST
# ==============================================================================

def fetch_binance_klines(symbol: str, interval: str = "4h", days: int = 180) -> pd.DataFrame:
    endpoints = [
        "https://api.binance.com", "https://api1.binance.com",
        "https://api2.binance.com", "https://api3.binance.com",
    ]
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - days * 24 * 60 * 60 * 1000
    all_data = []
    cur = start_ms

    while cur < end_ms:
        success = False
        for base in endpoints:
            try:
                resp = requests.get(f"{base}/api/v3/klines", params={
                    "symbol": symbol, "interval": interval,
                    "startTime": cur, "limit": 1000
                }, timeout=10)
                if resp.status_code == 200:
                    rows = resp.json()
                    if rows:
                        all_data.extend(rows)
                        cur = rows[-1][0] + 1
                        success = True
                        break
            except Exception:
                continue
        if not success:
            break
        time.sleep(0.2)

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_vol', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    for c in ['open', 'high', 'low', 'close', 'volume']:
        df[c] = df[c].astype(float)
    df = df.drop_duplicates(subset='open_time').sort_values('open_time').reset_index(drop=True)
    return df


def backtest_walk_forward(strategy, data, symbol, lookahead=12):
    signals = strategy.generate_signals(data, symbol)
    results = []

    for sig in signals:
        entry_idx = (data['close'] - sig.entry_price).abs().idxmin()

        for j in range(entry_idx + 1, min(entry_idx + lookahead + 1, len(data))):
            bar_high = data['high'].iloc[j]
            bar_low = data['low'].iloc[j]

            if sig.direction == "SELL":
                if bar_low <= sig.take_profit:
                    pnl_pct = (sig.entry_price - sig.take_profit) / sig.entry_price * 100
                    results.append({"symbol": symbol, "direction": sig.direction,
                                    "pnl_pct": pnl_pct, "outcome": "TP"})
                    break
                elif bar_high >= sig.stop_loss:
                    pnl_pct = -(sig.stop_loss - sig.entry_price) / sig.entry_price * 100
                    results.append({"symbol": symbol, "direction": sig.direction,
                                    "pnl_pct": pnl_pct, "outcome": "SL"})
                    break
            else:
                if bar_high >= sig.take_profit:
                    pnl_pct = (sig.take_profit - sig.entry_price) / sig.entry_price * 100
                    results.append({"symbol": symbol, "direction": sig.direction,
                                    "pnl_pct": pnl_pct, "outcome": "TP"})
                    break
                elif bar_low <= sig.stop_loss:
                    pnl_pct = -(sig.entry_price - sig.stop_loss) / sig.entry_price * 100
                    results.append({"symbol": symbol, "direction": sig.direction,
                                    "pnl_pct": pnl_pct, "outcome": "SL"})
                    break
        else:
            exit_price = data['close'].iloc[min(entry_idx + lookahead, len(data) - 1)]
            if sig.direction == "SELL":
                pnl_pct = (sig.entry_price - exit_price) / sig.entry_price * 100
            else:
                pnl_pct = (exit_price - sig.entry_price) / sig.entry_price * 100
            results.append({"symbol": symbol, "direction": sig.direction,
                            "pnl_pct": pnl_pct, "outcome": "EXPIRED"})

    return results


if __name__ == "__main__":
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT"]
    strategy = InverseATRRegimeRSIStrategy()
    all_results = []

    print("=" * 70)
    print("BACKTEST: inverse_atr_regime_rsi")
    print("  Original: 19.4% WR, -18.9% PnL -> expecting inverse to profit")
    print("=" * 70)

    for sym in symbols:
        print(f"\nFetching {sym} 4h data (180 days)...")
        df = fetch_binance_klines(sym, "4h", 180)
        if df.empty:
            print(f"  SKIP {sym}: no data")
            continue
        print(f"  Got {len(df)} bars")
        results = backtest_walk_forward(strategy, df, sym)
        all_results.extend(results)

        wins = [r for r in results if r['pnl_pct'] > 0]
        losses = [r for r in results if r['pnl_pct'] <= 0]
        wr = len(wins) / len(results) * 100 if results else 0
        avg_pnl = np.mean([r['pnl_pct'] for r in results]) if results else 0
        print(f"  {sym}: {len(results)} trades, WR={wr:.1f}%, avg PnL={avg_pnl:.2f}%")

    print("\n" + "=" * 70)
    print("OVERALL SUMMARY")
    print("=" * 70)
    if all_results:
        total = len(all_results)
        wins = [r for r in all_results if r['pnl_pct'] > 0]
        losses = [r for r in all_results if r['pnl_pct'] <= 0]
        wr = len(wins) / total * 100
        gross_profit = sum(r['pnl_pct'] for r in wins) if wins else 0
        gross_loss = abs(sum(r['pnl_pct'] for r in losses)) if losses else 0.001
        pf = gross_profit / gross_loss if gross_loss > 0 else 999
        avg_pnl = np.mean([r['pnl_pct'] for r in all_results])
        print(f"  Trades: {total}")
        print(f"  Win Rate: {wr:.1f}%")
        print(f"  Profit Factor: {pf:.2f}")
        print(f"  Avg PnL: {avg_pnl:.2f}%")
        print(f"  Gross Profit: {gross_profit:.2f}%  |  Gross Loss: {gross_loss:.2f}%")
        verdict = "KEEP" if wr > 50 and pf > 1.2 and total >= 30 else "REJECT"
        print(f"  Verdict: {verdict} (need WR>50%, PF>1.2, 30+ trades)")
    else:
        print("  No trades generated.")
