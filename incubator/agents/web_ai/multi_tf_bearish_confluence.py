"""
Multi-Timeframe Bearish Confluence
====================================

Created by: web_ai
Date: 2026-04-01

Strategy Logic:
- SHORT when 1h trend is down (EMA8 < EMA21 on 1h data)
  AND 4h RSI > 60 (overbought bounce within a downtrend)
  AND ATR expanding (current ATR > ATR SMA20 -- volatility picking up).
- Multi-timeframe bearish confluence: higher TF shows overbought bounce,
  lower TF confirms the downtrend is intact.
- TP = 2.0x ATR, SL = 1.0x ATR (tight SL for high RR)
- 6-bar cooldown between signals

Unique Value Proposition:
Most single-TF strategies miss context. This uses 1h for trend direction
and 4h for overbought detection -- shorting the relief rally in a confirmed
downtrend. The expanding ATR filter ensures we trade when volatility
favors reaching TP quickly.
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


class MultiTFBearishConfluenceStrategy:
    """
    Multi-timeframe bearish confluence: 1h downtrend + 4h overbought bounce.
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.ema_fast = self.params.get('ema_fast', 8)
        self.ema_slow = self.params.get('ema_slow', 21)
        self.rsi_period = self.params.get('rsi_period', 14)
        self.rsi_ob = self.params.get('rsi_overbought', 60)
        self.atr_period = self.params.get('atr_period', 14)
        self.atr_sma_period = self.params.get('atr_sma_period', 20)
        self.tp_atr = self.params.get('tp_atr', 2.0)
        self.sl_atr = self.params.get('sl_atr', 1.0)
        self.cooldown = self.params.get('cooldown', 6)

    def generate_signals_mtf(self, data_1h: pd.DataFrame, data_4h: pd.DataFrame,
                              symbol: str = "BTCUSDT") -> List[Signal]:
        """Generate signals using both 1h and 4h data."""
        min_len_1h = max(self.ema_slow, self.atr_period) + 20
        min_len_4h = max(self.rsi_period, self.atr_period, self.atr_sma_period) + 20

        if len(data_1h) < min_len_1h or len(data_4h) < min_len_4h:
            return []

        # 1h indicators
        ema_fast_1h = data_1h['close'].ewm(span=self.ema_fast, adjust=False).mean()
        ema_slow_1h = data_1h['close'].ewm(span=self.ema_slow, adjust=False).mean()

        # 4h indicators
        rsi_4h = self._calculate_rsi(data_4h['close'], self.rsi_period)
        atr_4h = self._calculate_atr(data_4h)
        atr_sma_4h = atr_4h.rolling(self.atr_sma_period).mean()

        # Build 1h trend lookup: map 4h open_time to 1h trend state
        # For each 4h bar, check the 1h EMA state at that time
        signals: List[Signal] = []
        last_signal_bar = -self.cooldown

        for i in range(min_len_4h, len(data_4h)):
            if i - last_signal_bar < self.cooldown:
                continue

            cur_rsi = rsi_4h.iloc[i]
            cur_atr = atr_4h.iloc[i]
            cur_atr_sma = atr_sma_4h.iloc[i]
            cur_close = data_4h['close'].iloc[i]
            cur_4h_time = data_4h['open_time'].iloc[i] if 'open_time' in data_4h.columns else i

            if any(pd.isna(v) for v in [cur_rsi, cur_atr, cur_atr_sma]):
                continue
            if cur_atr <= 0:
                continue

            # Find corresponding 1h bar (closest before 4h open_time)
            if 'open_time' in data_1h.columns and 'open_time' in data_4h.columns:
                mask = data_1h['open_time'] <= cur_4h_time
                if mask.sum() < self.ema_slow + 5:
                    continue
                idx_1h = data_1h[mask].index[-1]
            else:
                # Fallback: use proportional index (4h bar i ~ 1h bar i*4)
                idx_1h = min(i * 4, len(data_1h) - 1)
                if idx_1h < self.ema_slow + 5:
                    continue

            # 1h trend: EMA8 < EMA21 = downtrend
            trend_down_1h = ema_fast_1h.iloc[idx_1h] < ema_slow_1h.iloc[idx_1h]

            # 4h RSI overbought bounce
            rsi_ob = cur_rsi > self.rsi_ob

            # ATR expanding
            atr_expanding = cur_atr > cur_atr_sma

            if trend_down_1h and rsi_ob and atr_expanding:
                conf = min(0.60 + 0.01 * (cur_rsi - self.rsi_ob), 0.90)
                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(conf, 2),
                    entry_price=cur_close,
                    take_profit=round(cur_close - cur_atr * self.tp_atr, 2),
                    stop_loss=round(cur_close + cur_atr * self.sl_atr, 2),
                    reason=f"MTF_BEAR 1h_down 4h_RSI={cur_rsi:.1f} ATR_exp={cur_atr/cur_atr_sma:.2f}"
                ))
                last_signal_bar = i

        return signals

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        """Single-TF fallback: simulate MTF using the 4h data only.
        Approximate 1h trend by using shorter EMA on 4h data."""
        min_len = max(self.ema_slow, self.rsi_period, self.atr_period, self.atr_sma_period) + 20
        if len(data) < min_len:
            return []

        # Use shorter EMA spans on 4h to approximate 1h trend
        ema_fast = data['close'].ewm(span=self.ema_fast, adjust=False).mean()
        ema_slow = data['close'].ewm(span=self.ema_slow, adjust=False).mean()
        rsi = self._calculate_rsi(data['close'], self.rsi_period)
        atr = self._calculate_atr(data)
        atr_sma = atr.rolling(self.atr_sma_period).mean()

        signals: List[Signal] = []
        last_signal_bar = -self.cooldown

        for i in range(min_len, len(data)):
            if i - last_signal_bar < self.cooldown:
                continue

            cur_rsi = rsi.iloc[i]
            cur_atr = atr.iloc[i]
            cur_atr_sma = atr_sma.iloc[i]
            cur_close = data['close'].iloc[i]

            if any(pd.isna(v) for v in [cur_rsi, cur_atr, cur_atr_sma]):
                continue
            if cur_atr <= 0:
                continue

            trend_down = ema_fast.iloc[i] < ema_slow.iloc[i]
            rsi_ob = cur_rsi > self.rsi_ob
            atr_expanding = cur_atr > cur_atr_sma

            if trend_down and rsi_ob and atr_expanding:
                conf = min(0.60 + 0.01 * (cur_rsi - self.rsi_ob), 0.90)
                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(conf, 2),
                    entry_price=cur_close,
                    take_profit=round(cur_close - cur_atr * self.tp_atr, 2),
                    stop_loss=round(cur_close + cur_atr * self.sl_atr, 2),
                    reason=f"MTF_BEAR EMA8<21 RSI={cur_rsi:.1f} ATR_exp={cur_atr/cur_atr_sma:.2f}"
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

def backtest_walk_forward(strategy, data_4h, data_1h, symbol, lookahead=12, use_mtf=True):
    """Backtest with optional multi-timeframe data."""
    if use_mtf and data_1h is not None and not data_1h.empty:
        signals = strategy.generate_signals_mtf(data_1h, data_4h, symbol)
    else:
        signals = strategy.generate_signals(data_4h, symbol)

    results = []
    data = data_4h  # TP/SL checked on 4h bars

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
    strategy = MultiTFBearishConfluenceStrategy()
    all_results = []

    print("=" * 74)
    print("BACKTEST: Multi-TF Bearish Confluence")
    print("  1h: EMA(8) < EMA(21) (downtrend)")
    print("  4h: RSI(14) > 60 (overbought bounce) + ATR expanding")
    print("  TP=2.0x ATR | SL=1.0x ATR | Cooldown=6 bars | Lookahead=12")
    print("=" * 74)

    for sym in BACKTEST_SYMBOLS:
        print(f"\nFetching {sym} 4h data (180 days)...")
        df_4h = fetch_binance_klines(sym, "4h", 180)
        if df_4h.empty:
            print(f"  SKIP {sym}: no 4h data")
            continue
        print(f"  Got {len(df_4h)} 4h bars")

        print(f"  Fetching {sym} 1h data (180 days)...")
        df_1h = fetch_binance_klines(sym, "1h", 180)
        if df_1h.empty:
            print(f"  WARN {sym}: no 1h data, using single-TF fallback")
            df_1h = None
        else:
            print(f"  Got {len(df_1h)} 1h bars")

        results = backtest_walk_forward(strategy, df_4h, df_1h, sym, use_mtf=(df_1h is not None))
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
