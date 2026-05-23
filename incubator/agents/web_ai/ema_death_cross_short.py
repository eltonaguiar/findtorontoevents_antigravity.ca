"""
EMA Death Cross Short
======================

Created by: web_ai
Date: 2026-04-01

Strategy Logic:
- SHORT when EMA(9) crosses below EMA(21) AND ADX(14) > 20
  (confirming a real trend, not noise).
- Classic death cross with trend strength confirmation.
- TP = 2.5x ATR, SL = 1.5x ATR
- 4-bar cooldown between signals

Unique Value Proposition:
Plain EMA crossovers generate massive whipsaws in ranging markets.
The ADX > 20 gate ensures we only short when the cross happens in
a confirmed trending environment. SHORT-biased per peer intel
showing 81.8% WR on shorts.
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


class EMADeathCrossShortStrategy:
    """
    Short on EMA(9) crossing below EMA(21) with ADX > 20 confirmation.
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.ema_fast = self.params.get('ema_fast', 9)
        self.ema_slow = self.params.get('ema_slow', 21)
        self.adx_period = self.params.get('adx_period', 14)
        self.adx_threshold = self.params.get('adx_threshold', 20)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr = self.params.get('tp_atr', 2.5)
        self.sl_atr = self.params.get('sl_atr', 1.5)
        self.cooldown = self.params.get('cooldown', 4)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_len = max(self.ema_slow, self.adx_period * 3, self.atr_period) + 20
        if len(data) < min_len:
            return []

        ema_fast = data['close'].ewm(span=self.ema_fast, adjust=False).mean()
        ema_slow = data['close'].ewm(span=self.ema_slow, adjust=False).mean()
        adx = self._calculate_adx(data)
        atr = self._calculate_atr(data)

        signals: List[Signal] = []
        last_signal_bar = -self.cooldown

        for i in range(min_len, len(data)):
            if i - last_signal_bar < self.cooldown:
                continue

            cur_adx = adx.iloc[i]
            cur_atr = atr.iloc[i]
            cur_close = data['close'].iloc[i]
            cur_ema_fast = ema_fast.iloc[i]
            cur_ema_slow = ema_slow.iloc[i]
            prev_ema_fast = ema_fast.iloc[i - 1]
            prev_ema_slow = ema_slow.iloc[i - 1]

            if any(pd.isna(v) for v in [cur_adx, cur_atr, cur_ema_fast, cur_ema_slow,
                                         prev_ema_fast, prev_ema_slow]):
                continue
            if cur_atr <= 0:
                continue

            # Death cross: EMA(9) crosses below EMA(21)
            cross_down = prev_ema_fast >= prev_ema_slow and cur_ema_fast < cur_ema_slow

            if cross_down and cur_adx > self.adx_threshold:
                conf = min(0.60 + 0.01 * (cur_adx - self.adx_threshold), 0.90)
                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(conf, 2),
                    entry_price=cur_close,
                    take_profit=round(cur_close - cur_atr * self.tp_atr, 2),
                    stop_loss=round(cur_close + cur_atr * self.sl_atr, 2),
                    reason=f"DEATH_CROSS EMA9<EMA21 ADX={cur_adx:.1f}"
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

    def _calculate_adx(self, data: pd.DataFrame) -> pd.Series:
        high = data['high']
        low = data['low']
        close = data['close']
        n = self.adx_period

        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

        tr = pd.concat([
            high - low,
            abs(high - close.shift()),
            abs(low - close.shift())
        ], axis=1).max(axis=1)

        atr_smooth = tr.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
        plus_di = 100 * plus_dm.ewm(alpha=1 / n, min_periods=n, adjust=False).mean() / atr_smooth
        minus_di = 100 * minus_dm.ewm(alpha=1 / n, min_periods=n, adjust=False).mean() / atr_smooth

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, 1e-10)
        adx = dx.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
        return adx


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
    strategy = EMADeathCrossShortStrategy()
    all_results = []

    print("=" * 74)
    print("BACKTEST: EMA Death Cross Short")
    print("  EMA(9) crosses below EMA(21) + ADX(14) > 20")
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
            print(f"  {sym}: {len(results)} trades, WR={wr:.1f}%, avg PnL={avg_pnl:.2f}%")
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
