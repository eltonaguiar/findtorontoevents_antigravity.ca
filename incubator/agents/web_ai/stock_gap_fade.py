"""Stock Gap Fade - Fades overnight gaps on US equities. When stock opens >2% above
previous close AND RSI(14) > 65, SHORT (gap will fill). When opens >2% below AND RSI < 35,
LONG. TP: 50% of gap size, SL: 100% of gap size (1:0.5 R:R but high WR)."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "META", "GOOGL", "AMZN", "AMD"]

class StockGapFadeStrategy:
    def __init__(self, p=None):
        self.p = p or {}
        self.gap_threshold = self.p.get('gap_threshold', 2.0)
        self.rsi_period = self.p.get('rsi_period', 14)
        self.rsi_overbought = self.p.get('rsi_overbought', 65)
        self.rsi_oversold = self.p.get('rsi_oversold', 35)
        self.tp_gap_pct = self.p.get('tp_gap_pct', 0.50)
        self.sl_gap_pct = self.p.get('sl_gap_pct', 1.00)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "AAPL") -> List[Signal]:
        if len(data) < self.rsi_period + 10:
            return []
        prev_close = data['close'].iloc[-2]
        curr_open = data['open'].iloc[-1]
        curr_close = data['close'].iloc[-1]
        if prev_close <= 0:
            return []
        gap_pct = (curr_open / prev_close - 1) * 100
        rsi = self._rsi(data['close'], self.rsi_period).iloc[-1]
        if pd.isna(rsi):
            return []
        gap_size = abs(curr_open - prev_close)
        # Gap UP fade (SHORT)
        if gap_pct >= self.gap_threshold and rsi > self.rsi_overbought:
            tp = curr_open - gap_size * self.tp_gap_pct
            sl = curr_open + gap_size * self.sl_gap_pct
            conf = min(0.60 + (gap_pct - self.gap_threshold) * 0.03 + (rsi - self.rsi_overbought) * 0.005, 0.88)
            return [Signal(symbol, "SELL", round(max(conf, 0.55), 2), round(curr_open, 2),
                           round(tp, 2), round(sl, 2),
                           f"GapUp={gap_pct:.1f}% RSI={rsi:.0f} FADE")]
        # Gap DOWN fade (LONG)
        if gap_pct <= -self.gap_threshold and rsi < self.rsi_oversold:
            tp = curr_open + gap_size * self.tp_gap_pct
            sl = curr_open - gap_size * self.sl_gap_pct
            conf = min(0.60 + (abs(gap_pct) - self.gap_threshold) * 0.03 + (self.rsi_oversold - rsi) * 0.005, 0.88)
            return [Signal(symbol, "BUY", round(max(conf, 0.55), 2), round(curr_open, 2),
                           round(tp, 2), round(sl, 2),
                           f"GapDown={gap_pct:.1f}% RSI={rsi:.0f} FADE")]
        return []

    def _rsi(self, prices, n):
        d = prices.diff()
        g = d.where(d > 0, 0).rolling(n).mean()
        l = (-d.where(d < 0, 0)).rolling(n).mean()
        return 100 - (100 / (1 + g / l))


if __name__ == "__main__":
    import yfinance as yf

    BACKTEST_SYMBOLS = SYMBOLS
    MAX_HOLD = 5
    strat = StockGapFadeStrategy()

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
        if len(df) < 50:
            print(f"  Insufficient data for {sym}"); continue

        trades = []
        i = 30
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
    print(f"STOCK GAP FADE BACKTEST SUMMARY")
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
