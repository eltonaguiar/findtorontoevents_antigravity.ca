"""
Inverse LuxAlgo Confluence
===========================
Original: luxalgo_confluence -- 34.1% WR, -44.2% PnL, 126 trades, 16 symbols
Original logic: Multi-indicator confluence (EMA trend + RSI + Stoch + MACD alignment) -> BUY/SELL
Inverse: when all indicators align for BUY -> SELL, and vice versa

Rationale: LuxAlgo-style confluence uses many lagging indicators. When ALL agree,
the move is typically over-extended and due for reversal. The 34.1% WR proves
the consensus signal is systematically wrong -- fading it should yield ~66% WR.
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


class InverseLuxAlgoConfluenceStrategy:
    """
    Fades the multi-indicator confluence signal (LuxAlgo style).

    Original confluence checks:
    1. EMA trend (20/50 cross)
    2. RSI momentum
    3. Stochastic %K/%D
    4. MACD histogram direction

    When 3+ indicators agree -> original enters. INVERSE: fade that entry.
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.ema_fast = self.params.get('ema_fast', 20)
        self.ema_slow = self.params.get('ema_slow', 50)
        self.rsi_period = self.params.get('rsi_period', 14)
        self.stoch_period = self.params.get('stoch_period', 14)
        self.stoch_smooth = self.params.get('stoch_smooth', 3)
        self.macd_fast = self.params.get('macd_fast', 12)
        self.macd_slow = self.params.get('macd_slow', 26)
        self.macd_signal = self.params.get('macd_signal', 9)
        self.confluence_min = self.params.get('confluence_min', 3)  # 3/4 with RSI extreme filter
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr = self.params.get('tp_atr', 2.0)
        self.sl_atr = self.params.get('sl_atr', 1.2)
        self.cooldown = self.params.get('cooldown', 12)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_len = max(self.ema_slow, self.macd_slow + self.macd_signal,
                      self.stoch_period + self.stoch_smooth, self.rsi_period) + 20
        if len(data) < min_len:
            return []

        close = data['close']
        high = data['high']
        low = data['low']

        # Calculate all indicators
        ema_f = close.ewm(span=self.ema_fast, adjust=False).mean()
        ema_s = close.ewm(span=self.ema_slow, adjust=False).mean()

        rsi = self._calculate_rsi(close, self.rsi_period)

        # Stochastic
        lowest_low = low.rolling(self.stoch_period).min()
        highest_high = high.rolling(self.stoch_period).max()
        stoch_k = 100 * (close - lowest_low) / (highest_high - lowest_low + 1e-10)
        stoch_d = stoch_k.rolling(self.stoch_smooth).mean()

        # MACD
        macd_ema_f = close.ewm(span=self.macd_fast, adjust=False).mean()
        macd_ema_s = close.ewm(span=self.macd_slow, adjust=False).mean()
        macd_line = macd_ema_f - macd_ema_s
        macd_sig = macd_line.ewm(span=self.macd_signal, adjust=False).mean()
        macd_hist = macd_line - macd_sig

        atr = self._calculate_atr(data)

        signals = []
        last_signal_bar = -self.cooldown
        for i in range(min_len, len(data)):
            if i - last_signal_bar < self.cooldown:
                continue
            cur_price = close.iloc[i]
            cur_atr = atr.iloc[i]

            if pd.isna(cur_atr) or cur_atr == 0:
                continue

            # Count bullish votes
            bull_votes = 0
            bear_votes = 0

            # 1. EMA trend
            if ema_f.iloc[i] > ema_s.iloc[i]:
                bull_votes += 1
            else:
                bear_votes += 1

            # 2. RSI
            cur_rsi = rsi.iloc[i]
            if pd.isna(cur_rsi):
                continue
            if cur_rsi > 50:
                bull_votes += 1
            else:
                bear_votes += 1

            # 3. Stochastic
            cur_k = stoch_k.iloc[i]
            cur_d = stoch_d.iloc[i]
            if pd.isna(cur_k) or pd.isna(cur_d):
                continue
            if cur_k > cur_d and cur_k > 50:
                bull_votes += 1
            elif cur_k < cur_d and cur_k < 50:
                bear_votes += 1

            # 4. MACD histogram
            cur_hist = macd_hist.iloc[i]
            prev_hist = macd_hist.iloc[i - 1]
            if pd.isna(cur_hist) or pd.isna(prev_hist):
                continue
            if cur_hist > 0 and cur_hist > prev_hist:
                bull_votes += 1
            elif cur_hist < 0 and cur_hist < prev_hist:
                bear_votes += 1

            # Original: when confluence_min indicators agree -> trade that direction
            # INVERSE: fade it
            if bull_votes >= self.confluence_min and cur_rsi > 65:
                # Original would BUY. INVERSE: SELL -- only when RSI confirms overextension
                confidence = min(bull_votes / 4 * 0.8 + 0.1, 0.95)
                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 2),
                    entry_price=cur_price,
                    take_profit=round(cur_price - cur_atr * self.tp_atr, 2),
                    stop_loss=round(cur_price + cur_atr * self.sl_atr, 2),
                    reason=f"INV_LUXALGO: {bull_votes}/4 bullish confluence RSI={cur_rsi:.1f} -> SHORT (fade)"
                ))
                last_signal_bar = i

            elif bear_votes >= self.confluence_min and cur_rsi < 35:
                # Original would SELL. INVERSE: BUY -- only when RSI confirms oversold
                confidence = min(bear_votes / 4 * 0.8 + 0.1, 0.95)
                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 2),
                    entry_price=cur_price,
                    take_profit=round(cur_price + cur_atr * self.tp_atr, 2),
                    stop_loss=round(cur_price - cur_atr * self.sl_atr, 2),
                    reason=f"INV_LUXALGO: {bear_votes}/4 bearish confluence RSI={cur_rsi:.1f} -> LONG (fade)"
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
    strategy = InverseLuxAlgoConfluenceStrategy()
    all_results = []

    print("=" * 70)
    print("BACKTEST: inverse_luxalgo_confluence")
    print("  Original: 34.1% WR, -44.2% PnL -> expecting inverse to profit")
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

        # Per-symbol breakdown
        print("\n  Per-symbol breakdown:")
        for sym in symbols:
            sym_results = [r for r in all_results if r['symbol'] == sym]
            if sym_results:
                sw = [r for r in sym_results if r['pnl_pct'] > 0]
                swr = len(sw) / len(sym_results) * 100
                savg = np.mean([r['pnl_pct'] for r in sym_results])
                print(f"    {sym}: {len(sym_results)} trades, WR={swr:.1f}%, avg={savg:.2f}%")

        verdict = "KEEP" if wr > 50 and pf > 1.2 and total >= 30 else "REJECT"
        print(f"\n  Verdict: {verdict} (need WR>50%, PF>1.2, 30+ trades)")
    else:
        print("  No trades generated.")
