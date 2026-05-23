"""
Inverse MACD Crossover
=======================
Original: macd_crossover -- 28.9% WR, -75.0% PnL, 45 trades, 32 symbols
Original logic: MACD bullish cross -> BUY, bearish cross -> SELL
Inverse: fade every MACD crossover signal

Rationale: Classic MACD crossovers are LAGGING indicators. In crypto's fast
moves, by the time MACD crosses, the move is often exhausted. Fading them
captures the mean reversion after the lag-induced false signal.

Special filter: Only fade when RSI is in 40-60 range (neutral zone), avoiding
fading genuinely extreme moves.
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


class InverseMACDCrossoverStrategy:
    """
    Fades MACD crossover signals with RSI neutral-zone filter.

    - MACD bearish cross (line crosses BELOW signal) -> go LONG (fade it)
    - MACD bullish cross (line crosses ABOVE signal) -> go SHORT (fade it)
    - Only when RSI is 40-60 (neutral zone -- avoids fading extremes)
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.fast_period = self.params.get('fast_period', 12)
        self.slow_period = self.params.get('slow_period', 26)
        self.signal_period = self.params.get('signal_period', 9)
        self.rsi_period = self.params.get('rsi_period', 14)
        self.rsi_low = self.params.get('rsi_low', 40)
        self.rsi_high = self.params.get('rsi_high', 60)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr = self.params.get('tp_atr', 2.0)
        self.sl_atr = self.params.get('sl_atr', 1.2)
        self.cooldown = self.params.get('cooldown', 8)
        self.vol_ma_period = self.params.get('vol_ma_period', 20)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_len = self.slow_period + self.signal_period + self.rsi_period + 10
        if len(data) < min_len:
            return []

        close = data['close']
        ema_fast = close.ewm(span=self.fast_period, adjust=False).mean()
        ema_slow = close.ewm(span=self.slow_period, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.signal_period, adjust=False).mean()
        rsi = self._calculate_rsi(close, self.rsi_period)
        atr = self._calculate_atr(data)
        vol_ma = data['volume'].rolling(self.vol_ma_period).mean()

        signals = []
        last_signal_bar = -self.cooldown
        for i in range(min_len, len(data)):
            if i - last_signal_bar < self.cooldown:
                continue

            cur_macd = macd_line.iloc[i]
            prev_macd = macd_line.iloc[i - 1]
            cur_signal = signal_line.iloc[i]
            prev_signal = signal_line.iloc[i - 1]
            cur_rsi = rsi.iloc[i]
            cur_atr = atr.iloc[i]
            cur_price = close.iloc[i]
            cur_vol = data['volume'].iloc[i]
            cur_vol_ma = vol_ma.iloc[i]

            if pd.isna(cur_rsi) or pd.isna(cur_atr) or cur_atr == 0:
                continue
            if pd.isna(cur_vol_ma) or cur_vol_ma == 0:
                continue

            # RSI neutral zone filter (per spec)
            if not (self.rsi_low <= cur_rsi <= self.rsi_high):
                continue

            # Volume filter: only fade on below-average volume crosses (weak signal)
            # High-volume crosses might be legit; low-volume ones are noise to fade
            if cur_vol > cur_vol_ma * 1.5:
                continue  # skip strong-volume crosses

            # Detect MACD crosses
            bullish_cross = prev_macd <= prev_signal and cur_macd > cur_signal
            bearish_cross = prev_macd >= prev_signal and cur_macd < cur_signal

            if bullish_cross:
                # Original: bullish cross -> BUY. INVERSE: -> SELL (fade it)
                confidence = 0.65
                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=confidence,
                    entry_price=cur_price,
                    take_profit=round(cur_price - cur_atr * self.tp_atr, 2),
                    stop_loss=round(cur_price + cur_atr * self.sl_atr, 2),
                    reason=f"INV_MACD: bullish_cross RSI={cur_rsi:.1f} vol_ratio={cur_vol/cur_vol_ma:.1f} -> SHORT"
                ))
                last_signal_bar = i

            elif bearish_cross:
                # Original: bearish cross -> SELL. INVERSE: -> BUY (fade it)
                confidence = 0.65
                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=confidence,
                    entry_price=cur_price,
                    take_profit=round(cur_price + cur_atr * self.tp_atr, 2),
                    stop_loss=round(cur_price - cur_atr * self.sl_atr, 2),
                    reason=f"INV_MACD: bearish_cross RSI={cur_rsi:.1f} vol_ratio={cur_vol/cur_vol_ma:.1f} -> LONG"
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
    strategy = InverseMACDCrossoverStrategy()
    all_results = []

    print("=" * 70)
    print("BACKTEST: inverse_macd_crossover")
    print("  Original: 28.9% WR, -75.0% PnL -> expecting inverse to profit")
    print("  RSI filter: only fade when RSI 40-60 (neutral zone)")
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
