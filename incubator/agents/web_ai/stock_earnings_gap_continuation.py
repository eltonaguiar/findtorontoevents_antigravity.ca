"""Stock Earnings Gap Continuation - After a >5% earnings gap up with volume >3x avg,
go LONG on the first pullback to EMA(9). TP: 2.5x ATR, SL: 1.2x ATR.
Exploits post-earnings momentum drift with controlled pullback entry."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

SYMBOLS = ["AAPL", "MSFT", "NVDA", "META", "GOOGL", "TSLA", "AMD", "CRM"]

class StockEarningsGapContinuationStrategy:
    def __init__(self, p=None):
        self.p = p or {}
        self.gap_threshold = self.p.get('gap_threshold', 5.0)
        self.vol_mult = self.p.get('vol_mult', 3.0)
        self.vol_lookback = self.p.get('vol_lookback', 20)
        self.ema_period = self.p.get('ema_period', 9)
        self.atr_period = self.p.get('atr_period', 14)
        self.pullback_window = self.p.get('pullback_window', 10)
        self.tp_atr = self.p.get('tp_atr', 2.5)
        self.sl_atr = self.p.get('sl_atr', 1.2)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "AAPL") -> List[Signal]:
        min_bars = max(self.vol_lookback, self.ema_period, self.atr_period) + self.pullback_window + 10
        if len(data) < min_bars:
            return []
        close = data['close'].iloc[-1]
        low = data['low'].iloc[-1]
        ema9 = data['close'].ewm(span=self.ema_period, adjust=False).mean()
        atr = self._atr(data).iloc[-1]
        if pd.isna(atr) or atr <= 0:
            return []
        # Look back up to pullback_window bars for an earnings-like gap event
        for lookback in range(2, self.pullback_window + 1):
            if len(data) < lookback + self.vol_lookback + 2:
                continue
            gap_idx = len(data) - lookback
            gap_open = data['open'].iloc[gap_idx]
            prev_close = data['close'].iloc[gap_idx - 1]
            gap_vol = data['volume'].iloc[gap_idx]
            vol_avg = data['volume'].iloc[gap_idx - self.vol_lookback:gap_idx].mean()
            if prev_close <= 0 or vol_avg <= 0:
                continue
            gap_pct = (gap_open / prev_close - 1) * 100
            vol_ratio = gap_vol / vol_avg
            gap_close = data['close'].iloc[gap_idx]
            # Earnings gap: >5% gap up, volume >3x, close > open (bullish)
            if gap_pct >= self.gap_threshold and vol_ratio >= self.vol_mult and gap_close > gap_open:
                # Check if current bar is a pullback to EMA(9)
                curr_ema = ema9.iloc[-1]
                # Pullback: low touches or goes below EMA(9) but close is above it
                if low <= curr_ema * 1.005 and close >= curr_ema * 0.995:
                    conf = min(0.62 + (gap_pct - self.gap_threshold) * 0.02 + (vol_ratio - self.vol_mult) * 0.03, 0.88)
                    return [Signal(symbol, "BUY", round(max(conf, 0.60), 2), round(close, 2),
                                   round(close + atr * self.tp_atr, 2),
                                   round(close - atr * self.sl_atr, 2),
                                   f"EarningsGap={gap_pct:.1f}% Vol={vol_ratio:.1f}x PB->EMA9")]
        return []

    def _atr(self, d):
        tr = pd.concat([d['high'] - d['low'],
                        abs(d['high'] - d['close'].shift()),
                        abs(d['low'] - d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()


if __name__ == "__main__":
    import yfinance as yf

    BACKTEST_SYMBOLS = SYMBOLS
    MAX_HOLD = 10
    strat = StockEarningsGapContinuationStrategy()

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
                    if bar_low <= sig.stop_loss:
                        exit_price = sig.stop_loss; break
                    if bar_high >= sig.take_profit:
                        exit_price = sig.take_profit; break
                if exit_price is None:
                    exit_idx = min(i + MAX_HOLD, len(df) - 1)
                    exit_price = df['close'].iloc[exit_idx]
                pnl_pct = (exit_price - entry_price) / entry_price * 100
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
    print(f"STOCK EARNINGS GAP CONTINUATION BACKTEST SUMMARY")
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
