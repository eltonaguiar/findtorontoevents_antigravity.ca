"""Stock Volume Breakout - LONG when close breaks above 20-day high AND volume > 2x avg
AND ADX > 25. Momentum breakout with volume confirmation. TP: 3.0x ATR, SL: 1.5x ATR."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "META", "GOOGL", "AMZN", "AMD"]

class StockVolumeBreakoutStrategy:
    def __init__(self, p=None):
        self.p = p or {}
        self.breakout_period = self.p.get('breakout_period', 20)
        self.vol_lookback = self.p.get('vol_lookback', 20)
        self.vol_mult = self.p.get('vol_mult', 2.0)
        self.adx_period = self.p.get('adx_period', 14)
        self.adx_threshold = self.p.get('adx_threshold', 25)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 3.0)
        self.sl_atr = self.p.get('sl_atr', 1.5)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "AAPL") -> List[Signal]:
        min_bars = max(self.breakout_period, self.vol_lookback, self.adx_period * 2) + 10
        if len(data) < min_bars:
            return []
        close = data['close'].iloc[-1]
        high_20 = data['high'].iloc[-(self.breakout_period + 1):-1].max()
        vol_avg = data['volume'].iloc[-(self.vol_lookback + 1):-1].mean()
        curr_vol = data['volume'].iloc[-1]
        if vol_avg <= 0:
            return []
        vol_ratio = curr_vol / vol_avg
        adx = self._adx(data).iloc[-1]
        atr = self._atr(data).iloc[-1]
        if pd.isna(adx) or pd.isna(atr) or atr <= 0:
            return []
        # Breakout: close > 20-day high, volume > 2x avg, ADX > 25
        if close > high_20 and vol_ratio > self.vol_mult and adx > self.adx_threshold:
            conf = min(0.60 + (vol_ratio - self.vol_mult) * 0.04 + (adx - self.adx_threshold) * 0.005, 0.90)
            return [Signal(symbol, "BUY", round(max(conf, 0.60), 2), round(close, 2),
                           round(close + atr * self.tp_atr, 2),
                           round(close - atr * self.sl_atr, 2),
                           f"Breakout H20={high_20:.2f} Vol={vol_ratio:.1f}x ADX={adx:.0f}")]
        return []

    def _adx(self, data):
        high, low, close = data['high'], data['low'], data['close']
        n = self.adx_period
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        atr = tr.rolling(n).mean()
        plus_di = 100 * (plus_dm.rolling(n).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(n).mean() / atr)
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        return dx.rolling(n).mean()

    def _atr(self, d):
        tr = pd.concat([d['high'] - d['low'],
                        abs(d['high'] - d['close'].shift()),
                        abs(d['low'] - d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()


if __name__ == "__main__":
    import yfinance as yf

    BACKTEST_SYMBOLS = SYMBOLS
    MAX_HOLD = 10
    strat = StockVolumeBreakoutStrategy()

    all_trades = []
    for sym in BACKTEST_SYMBOLS:
        print(f"\n{'='*50}")
        print(f"Fetching {sym} (2 years daily)...")
        df = yf.download(sym, period="2y", interval="1d", progress=False)
        if df.empty:
            print(f"  No data for {sym}, skipping"); continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        df.columns = [c.lower() for c in df.columns]
        df = df.reset_index(drop=True)
        if len(df) < 70:
            print(f"  Insufficient data for {sym}"); continue

        trades = []
        i = 50
        while i < len(df):
            window = df.iloc[:i + 1].copy()
            sigs = strat.generate_signals(window, symbol=sym)
            if sigs:
                sig = sigs[0]
                entry_price = sig.entry_price
                direction = sig.direction
                exit_price = None
                for j in range(i + 1, min(i + 1 + MAX_HOLD, len(df))):
                    bar_high = df['high'].iloc[j]
                    bar_low = df['low'].iloc[j]
                    if direction == "BUY":
                        if bar_low <= sig.stop_loss:
                            exit_price = sig.stop_loss; break
                        if bar_high >= sig.take_profit:
                            exit_price = sig.take_profit; break
                    else:
                        if bar_high >= sig.stop_loss:
                            exit_price = sig.stop_loss; break
                        if bar_low <= sig.take_profit:
                            exit_price = sig.take_profit; break
                if exit_price is None:
                    exit_idx = min(i + MAX_HOLD, len(df) - 1)
                    exit_price = df['close'].iloc[exit_idx]
                if direction == "BUY":
                    pnl_pct = (exit_price - entry_price) / entry_price * 100
                else:
                    pnl_pct = (entry_price - exit_price) / entry_price * 100
                trades.append({'symbol': sym, 'dir': direction, 'entry': entry_price,
                               'exit': exit_price, 'pnl_pct': pnl_pct,
                               'conf': sig.confidence, 'reason': sig.reason})
                i += MAX_HOLD + 1
            else:
                i += 1

        print(f"  {sym}: {len(trades)} trades")
        for t in trades:
            print(f"    {t['dir']} {t['symbol']} @ {t['entry']:.2f} -> {t['exit']:.2f}  "
                  f"PnL={t['pnl_pct']:+.2f}%  conf={t['conf']}  {t['reason']}")
        all_trades.extend(trades)

    print(f"\n{'='*50}")
    print(f"STOCK VOLUME BREAKOUT BACKTEST SUMMARY")
    print(f"{'='*50}")
    if all_trades:
        pnls = [t['pnl_pct'] for t in all_trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        wr = len(wins) / len(pnls) * 100 if pnls else 0
        avg_pnl = np.mean(pnls)
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0.001
        pf = gross_profit / gross_loss
        print(f"Total trades : {len(all_trades)}")
        print(f"Win rate     : {wr:.1f}%")
        print(f"Profit factor: {pf:.2f}")
        print(f"Avg PnL      : {avg_pnl:+.2f}%")
        print(f"Best trade   : {max(pnls):+.2f}%")
        print(f"Worst trade  : {min(pnls):+.2f}%")
        buy_trades = [t for t in all_trades if t['dir'] == 'BUY']
        sell_trades = [t for t in all_trades if t['dir'] == 'SELL']
        print(f"BUY trades   : {len(buy_trades)}")
        print(f"SELL trades  : {len(sell_trades)}")
    else:
        print("No trades generated.")
