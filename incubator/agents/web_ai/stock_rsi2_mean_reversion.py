"""Stock RSI(2) Mean Reversion - Connors RSI(2) strategy. LONG when RSI(2) < 10 AND price
> SMA(200). SHORT when RSI(2) > 90 AND price < SMA(200). Very short-term mean reversion.
TP: 1.5x ATR, SL: 1.0x ATR."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "META", "GOOGL", "AMZN", "AMD"]

class StockRSI2MeanReversionStrategy:
    def __init__(self, p=None):
        self.p = p or {}
        self.rsi_period = self.p.get('rsi_period', 2)
        self.sma_period = self.p.get('sma_period', 200)
        self.atr_period = self.p.get('atr_period', 14)
        self.rsi_oversold = self.p.get('rsi_oversold', 10)
        self.rsi_overbought = self.p.get('rsi_overbought', 90)
        self.tp_atr = self.p.get('tp_atr', 1.5)
        self.sl_atr = self.p.get('sl_atr', 1.0)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "AAPL") -> List[Signal]:
        if len(data) < self.sma_period + 10:
            return []
        close = data['close'].iloc[-1]
        rsi2 = self._rsi(data['close'], self.rsi_period).iloc[-1]
        sma200 = data['close'].rolling(self.sma_period).mean().iloc[-1]
        atr = self._atr(data).iloc[-1]
        if pd.isna(rsi2) or pd.isna(sma200) or pd.isna(atr) or atr <= 0:
            return []
        # LONG: RSI(2) < 10, price above SMA(200) (uptrend pullback)
        if rsi2 < self.rsi_oversold and close > sma200:
            conf = min(0.65 + (self.rsi_oversold - rsi2) * 0.02, 0.90)
            return [Signal(symbol, "BUY", round(conf, 2), round(close, 2),
                           round(close + atr * self.tp_atr, 2),
                           round(close - atr * self.sl_atr, 2),
                           f"RSI2={rsi2:.1f} >SMA200 MeanRev")]
        # SHORT: RSI(2) > 90, price below SMA(200) (downtrend bounce)
        if rsi2 > self.rsi_overbought and close < sma200:
            conf = min(0.65 + (rsi2 - self.rsi_overbought) * 0.02, 0.90)
            return [Signal(symbol, "SELL", round(conf, 2), round(close, 2),
                           round(close - atr * self.tp_atr, 2),
                           round(close + atr * self.sl_atr, 2),
                           f"RSI2={rsi2:.1f} <SMA200 MeanRev")]
        return []

    def _rsi(self, prices, n):
        d = prices.diff()
        g = d.where(d > 0, 0).rolling(n).mean()
        l = (-d.where(d < 0, 0)).rolling(n).mean()
        return 100 - (100 / (1 + g / l))

    def _atr(self, d):
        tr = pd.concat([d['high'] - d['low'],
                        abs(d['high'] - d['close'].shift()),
                        abs(d['low'] - d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()


if __name__ == "__main__":
    import yfinance as yf

    BACKTEST_SYMBOLS = SYMBOLS
    MAX_HOLD = 5
    strat = StockRSI2MeanReversionStrategy()

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
        if len(df) < 220:
            print(f"  Insufficient data for {sym}"); continue

        trades = []
        i = 210
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
    print(f"STOCK RSI(2) MEAN REVERSION BACKTEST SUMMARY")
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
