"""
Volume Climax Reversal
=======================

Created by: web_ai
Date: 2026-04-01

Strategy Logic:
- SHORT when volume > 3x 20-bar avg AND close < open (bearish engulfing
  on volume climax) AND RSI > 50. The blow-off top pattern.
  TP = 2.5x ATR, SL = 1.5x ATR.
- LONG when volume > 3x 20-bar avg AND close > open (bullish climax)
  AND RSI < 50. Capitulation reversal / selling climax.
  TP = 2.5x ATR, SL = 1.5x ATR.
- 4-bar cooldown between signals

Unique Value Proposition:
Volume climax events are rare but high-probability. The 3x volume
threshold ensures we only catch genuine capitulation / blow-off events,
not normal noise. RSI filter confirms the directional bias. Dual-direction
but SHORT-biased per peer intel (shorts have 81.8% WR).
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


SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT",
    "ALGOUSDT", "SUIUSDT", "FETUSDT", "AVAXUSDT", "DOTUSDT",
    "LINKUSDT", "MATICUSDT"
]


class VolumeClimaxReversalStrategy:
    """
    Reversal on extreme volume spikes with directional candle confirmation.
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.vol_sma_period = self.params.get('vol_sma_period', 20)
        self.vol_multiplier = self.params.get('vol_multiplier', 3.0)
        self.rsi_period = self.params.get('rsi_period', 14)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr = self.params.get('tp_atr', 2.5)
        self.sl_atr = self.params.get('sl_atr', 1.5)
        self.cooldown = self.params.get('cooldown', 4)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_len = max(self.vol_sma_period, self.rsi_period, self.atr_period) + 20
        if len(data) < min_len:
            return []

        rsi = self._calculate_rsi(data['close'], self.rsi_period)
        atr = self._calculate_atr(data)
        vol_sma = data['volume'].rolling(self.vol_sma_period).mean()

        signals: List[Signal] = []
        last_signal_bar = -self.cooldown

        for i in range(min_len, len(data)):
            if i - last_signal_bar < self.cooldown:
                continue

            cur_rsi = rsi.iloc[i]
            cur_atr = atr.iloc[i]
            cur_close = data['close'].iloc[i]
            cur_open = data['open'].iloc[i]
            cur_vol = data['volume'].iloc[i]
            cur_vol_sma = vol_sma.iloc[i]

            if any(pd.isna(v) for v in [cur_rsi, cur_atr, cur_vol_sma]):
                continue
            if cur_atr <= 0 or cur_vol_sma <= 0:
                continue

            vol_ratio = cur_vol / cur_vol_sma

            # Volume climax: > 3x average
            if vol_ratio < self.vol_multiplier:
                continue

            # SHORT: bearish candle (close < open) + RSI > 50 (blow-off top)
            if cur_close < cur_open and cur_rsi > 50:
                conf = min(0.60 + 0.05 * (vol_ratio - self.vol_multiplier), 0.92)
                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(conf, 2),
                    entry_price=cur_close,
                    take_profit=round(cur_close - cur_atr * self.tp_atr, 2),
                    stop_loss=round(cur_close + cur_atr * self.sl_atr, 2),
                    reason=f"VOL_CLIMAX_SHORT vol={vol_ratio:.1f}x RSI={cur_rsi:.1f} bearish_candle"
                ))
                last_signal_bar = i

            # LONG: bullish candle (close > open) + RSI < 50 (capitulation)
            elif cur_close > cur_open and cur_rsi < 50:
                conf = min(0.55 + 0.05 * (vol_ratio - self.vol_multiplier), 0.88)
                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(conf, 2),
                    entry_price=cur_close,
                    take_profit=round(cur_close + cur_atr * self.tp_atr, 2),
                    stop_loss=round(cur_close - cur_atr * self.sl_atr, 2),
                    reason=f"VOL_CLIMAX_LONG vol={vol_ratio:.1f}x RSI={cur_rsi:.1f} bullish_candle"
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
# BINANCE DATA FETCHER (3+ endpoint failover per CLAUDE.md)
# ==============================================================================

def fetch_binance_klines(symbol: str, interval: str = "4h",
                         days: int = 180) -> pd.DataFrame:
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


# ==============================================================================
# WALK-FORWARD BACKTESTER
# ==============================================================================

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
                    results.append({"symbol": symbol, "direction": "SELL",
                                    "pnl_pct": pnl_pct, "outcome": "TP"})
                    break
                elif bar_high >= sig.stop_loss:
                    pnl_pct = -(sig.stop_loss - sig.entry_price) / sig.entry_price * 100
                    results.append({"symbol": symbol, "direction": "SELL",
                                    "pnl_pct": pnl_pct, "outcome": "SL"})
                    break
            else:
                if bar_high >= sig.take_profit:
                    pnl_pct = (sig.take_profit - sig.entry_price) / sig.entry_price * 100
                    results.append({"symbol": symbol, "direction": "BUY",
                                    "pnl_pct": pnl_pct, "outcome": "TP"})
                    break
                elif bar_low <= sig.stop_loss:
                    pnl_pct = -(sig.entry_price - sig.stop_loss) / sig.entry_price * 100
                    results.append({"symbol": symbol, "direction": "BUY",
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


# ==============================================================================
# MAIN BACKTEST
# ==============================================================================

if __name__ == "__main__":
    BACKTEST_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT"]
    strategy = VolumeClimaxReversalStrategy()
    all_results = []

    print("=" * 74)
    print("BACKTEST: Volume Climax Reversal")
    print("  SHORT: vol>3x + bearish candle + RSI>50 (blow-off top)")
    print("  LONG:  vol>3x + bullish candle + RSI<50 (capitulation)")
    print("  TP=2.5x ATR | SL=1.5x ATR | Cooldown=4 bars | Lookahead=12")
    print("=" * 74)

    for sym in BACKTEST_SYMBOLS:
        print(f"\nFetching {sym} 4h data (180 days)...")
        df = fetch_binance_klines(sym, "4h", 180)
        if df.empty:
            print(f"  SKIP {sym}: no data")
            continue
        print(f"  Got {len(df)} bars")

        results = backtest_walk_forward(strategy, df, sym)
        all_results.extend(results)

        if results:
            wins = [r for r in results if r['pnl_pct'] > 0]
            wr = len(wins) / len(results) * 100
            avg_pnl = np.mean([r['pnl_pct'] for r in results])
            shorts = [r for r in results if r['direction'] == 'SELL']
            longs = [r for r in results if r['direction'] == 'BUY']
            print(f"  {sym}: {len(results)} trades ({len(shorts)}S/{len(longs)}L), "
                  f"WR={wr:.1f}%, avg PnL={avg_pnl:.2f}%")
        else:
            print(f"  {sym}: 0 trades")

    print("\n" + "=" * 74)
    print("OVERALL SUMMARY")
    print("=" * 74)
    if all_results:
        total = len(all_results)
        wins = [r for r in all_results if r['pnl_pct'] > 0]
        losses = [r for r in all_results if r['pnl_pct'] <= 0]
        wr = len(wins) / total * 100
        gross_profit = sum(r['pnl_pct'] for r in wins) if wins else 0
        gross_loss = abs(sum(r['pnl_pct'] for r in losses)) if losses else 0.001
        pf = gross_profit / gross_loss if gross_loss > 0 else 999
        avg_pnl = np.mean([r['pnl_pct'] for r in all_results])
        total_pnl = sum(r['pnl_pct'] for r in all_results)

        print(f"  Total Trades : {total}")
        print(f"  Win Rate     : {wr:.1f}%")
        print(f"  Profit Factor: {pf:.2f}")
        print(f"  Avg PnL/trade: {avg_pnl:.2f}%")
        print(f"  Total PnL    : {total_pnl:.2f}%")

        # Direction breakdown
        shorts = [r for r in all_results if r['direction'] == 'SELL']
        longs = [r for r in all_results if r['direction'] == 'BUY']
        if shorts:
            sw = len([r for r in shorts if r['pnl_pct'] > 0])
            print(f"\n  SHORT trades: {len(shorts)}, WR={sw/len(shorts)*100:.1f}%")
        if longs:
            lw = len([r for r in longs if r['pnl_pct'] > 0])
            print(f"  LONG  trades: {len(longs)}, WR={lw/len(longs)*100:.1f}%")

        print("\n  -- Per-Symbol Breakdown --")
        for sym in BACKTEST_SYMBOLS:
            sym_r = [r for r in all_results if r['symbol'] == sym]
            if sym_r:
                sw = len([r for r in sym_r if r['pnl_pct'] > 0])
                swr = sw / len(sym_r) * 100
                savg = np.mean([r['pnl_pct'] for r in sym_r])
                print(f"    {sym}: {len(sym_r)} trades, WR={swr:.1f}%, avgPnL={savg:.2f}%")

        print("\n  -- Outcome Distribution --")
        for outcome in ["TP", "SL", "EXPIRED"]:
            ct = len([r for r in all_results if r['outcome'] == outcome])
            print(f"    {outcome}: {ct} ({ct / total * 100:.1f}%)")

        verdict = "KEEP" if pf > 1.1 else "DISCARD"
        print(f"\n  Verdict: {verdict} (need PF>1.1)")
    else:
        print("  No trades generated.")
