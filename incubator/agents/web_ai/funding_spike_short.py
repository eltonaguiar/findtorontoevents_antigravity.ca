"""
Funding Spike Short (Contrarian)
=================================

Created by: web_ai
Date: 2026-04-01

Strategy Logic:
- SHORT when funding rate > 0.008% (longs overleveraged, ~P90 threshold)
  AND RSI(14) > 55 AND close > EMA(20) (positive momentum = greedy market).
- Contrarian: when everyone is long and paying elevated funding,
  the market is primed for a squeeze / reversal.
- TP = 2.0x ATR, SL = 1.2x ATR
- 6-bar cooldown between signals

Note: Binance funding rate API is only available for futures pairs.
This strategy fetches funding rates from the futures API with failover.

Unique Value Proposition:
Pure on-chain / exchange microstructure signal. High funding = crowded
long positioning. Combined with RSI > 55 to confirm the greedy bias
is still active (catching the top, not the correction).
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


class FundingSpikeShortStrategy:
    """
    Short when funding rate spikes (longs overleveraged) with RSI confirmation.
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.funding_threshold = self.params.get('funding_threshold', 0.00008)  # 0.008% (~P90)
        self.rsi_period = self.params.get('rsi_period', 14)
        self.rsi_min = self.params.get('rsi_min', 55)
        self.ema_period = self.params.get('ema_period', 20)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr = self.params.get('tp_atr', 2.0)
        self.sl_atr = self.params.get('sl_atr', 1.2)
        self.cooldown = self.params.get('cooldown', 6)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        """Generate signals. data must have 'funding_rate' column if available."""
        min_len = max(self.rsi_period, self.ema_period, self.atr_period) + 20
        if len(data) < min_len:
            return []

        rsi = self._calculate_rsi(data['close'], self.rsi_period)
        atr = self._calculate_atr(data)
        ema = data['close'].ewm(span=self.ema_period, adjust=False).mean()

        has_funding = 'funding_rate' in data.columns

        signals: List[Signal] = []
        last_signal_bar = -self.cooldown

        for i in range(min_len, len(data)):
            if i - last_signal_bar < self.cooldown:
                continue

            cur_rsi = rsi.iloc[i]
            cur_atr = atr.iloc[i]
            cur_close = data['close'].iloc[i]
            cur_ema = ema.iloc[i]

            if any(pd.isna(v) for v in [cur_rsi, cur_atr, cur_ema]):
                continue
            if cur_atr <= 0:
                continue

            # Check funding rate
            if has_funding:
                cur_funding = data['funding_rate'].iloc[i]
                if pd.isna(cur_funding):
                    continue
            else:
                continue  # No funding data, skip

            # SHORT: high funding + RSI > 55 + price above EMA (greedy market)
            if (cur_funding > self.funding_threshold and
                    cur_rsi > self.rsi_min and
                    cur_close > cur_ema):
                conf = min(0.60 + (cur_funding - self.funding_threshold) * 200, 0.92)
                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(conf, 2),
                    entry_price=cur_close,
                    take_profit=round(cur_close - cur_atr * self.tp_atr, 2),
                    stop_loss=round(cur_close + cur_atr * self.sl_atr, 2),
                    reason=f"FUNDING_SPIKE rate={cur_funding*100:.3f}% RSI={cur_rsi:.1f}"
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


def fetch_funding_rates(symbol: str, days: int = 180) -> pd.DataFrame:
    """Fetch historical funding rates from Binance futures API with failover."""
    endpoints = [
        "https://fapi.binance.com",
        "https://fapi1.binance.com",
        "https://fapi2.binance.com",
    ]
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - days * 24 * 60 * 60 * 1000
    all_data = []
    cur = start_ms

    while cur < end_ms:
        success = False
        for base in endpoints:
            try:
                resp = requests.get(f"{base}/fapi/v1/fundingRate", params={
                    "symbol": symbol, "startTime": cur, "limit": 1000
                }, timeout=10)
                if resp.status_code == 200:
                    rows = resp.json()
                    if rows:
                        all_data.extend(rows)
                        cur = rows[-1]['fundingTime'] + 1
                        success = True
                        break
            except Exception:
                continue
        if not success:
            break
        time.sleep(0.2)

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data)
    df['fundingRate'] = df['fundingRate'].astype(float)
    df['fundingTime'] = df['fundingTime'].astype(int)
    return df


def merge_funding_with_klines(klines_df: pd.DataFrame,
                               funding_df: pd.DataFrame) -> pd.DataFrame:
    """Merge funding rates into kline data using forward-fill."""
    if funding_df.empty:
        klines_df['funding_rate'] = np.nan
        return klines_df

    # Map each kline to the most recent funding rate
    funding_times = funding_df['fundingTime'].values
    funding_rates = funding_df['fundingRate'].values

    rates = []
    for ot in klines_df['open_time']:
        # Find most recent funding rate before this candle
        mask = funding_times <= ot
        if mask.any():
            idx = np.where(mask)[0][-1]
            rates.append(funding_rates[idx])
        else:
            rates.append(np.nan)

    klines_df['funding_rate'] = rates
    return klines_df


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
    strategy = FundingSpikeShortStrategy()
    all_results = []

    print("=" * 74)
    print("BACKTEST: Funding Spike Short (Contrarian)")
    print("  Funding > 0.008% (~P90) + RSI(14) > 55 + price > EMA(20)")
    print("  TP=2.0x ATR | SL=1.2x ATR | Cooldown=6 bars | Lookahead=12")
    print("=" * 74)

    for sym in BACKTEST_SYMBOLS:
        print(f"\nFetching {sym} 4h data (180 days)...")
        df = fetch_binance_klines(sym, "4h", 180)
        if df.empty:
            print(f"  SKIP {sym}: no kline data")
            continue
        print(f"  Got {len(df)} bars")

        print(f"  Fetching {sym} funding rates...")
        funding_df = fetch_funding_rates(sym, 180)
        if funding_df.empty:
            print(f"  WARN {sym}: no funding data, skipping")
            continue
        print(f"  Got {len(funding_df)} funding records")

        df = merge_funding_with_klines(df, funding_df)
        valid_funding = df['funding_rate'].notna().sum()
        print(f"  Merged: {valid_funding}/{len(df)} bars have funding data")

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
