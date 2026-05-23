"""Forex RSI(2) Bounce - Mean reversion on extreme RSI(2) readings.
LONG when RSI(2) < 5 AND price > EMA(200). SHORT when RSI(2) > 95 AND price < EMA(200).
Very tight: TP 1.0x ATR(14), SL 0.8x ATR. High frequency, small wins.
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List

SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "EURJPY", "GBPJPY", "NZDUSD"]

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class ForexRSI2BounceStrategy:
    def __init__(self, p=None):
        self.p = p or {}
        self.rsi_period = self.p.get('rsi_period', 2)
        self.ema_period = self.p.get('ema_period', 200)
        self.rsi_long_th = self.p.get('rsi_long_th', 5)
        self.rsi_short_th = self.p.get('rsi_short_th', 95)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 1.0)
        self.sl_atr = self.p.get('sl_atr', 0.8)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "EURUSD") -> List[Signal]:
        min_len = self.ema_period + 20
        if len(data) < min_len:
            return []

        close = data['close']
        rsi = self._rsi(close, self.rsi_period)
        ema200 = close.ewm(span=self.ema_period, adjust=False).mean()
        atr = self._atr(data)

        r, cp, e200, ca = rsi.iloc[-1], close.iloc[-1], ema200.iloc[-1], atr.iloc[-1]
        if pd.isna(r) or pd.isna(ca) or ca == 0:
            return []

        signals = []
        if r < self.rsi_long_th and cp > e200:
            conf = min(0.65 + (self.rsi_long_th - r) * 0.06, 0.92)
            tp = cp + ca * self.tp_atr
            sl = cp - ca * self.sl_atr
            signals.append(Signal(
                symbol, "BUY", round(conf, 2), round(cp, 6),
                round(tp, 6), round(sl, 6),
                f"RSI2={r:.1f}<{self.rsi_long_th} price>EMA200"
            ))
        elif r > self.rsi_short_th and cp < e200:
            conf = min(0.65 + (r - self.rsi_short_th) * 0.06, 0.92)
            tp = cp - ca * self.tp_atr
            sl = cp + ca * self.sl_atr
            signals.append(Signal(
                symbol, "SELL", round(conf, 2), round(cp, 6),
                round(tp, 6), round(sl, 6),
                f"RSI2={r:.1f}>{self.rsi_short_th} price<EMA200"
            ))

        return signals

    def _rsi(self, p, n):
        d = p.diff()
        g = d.where(d > 0, 0).rolling(n).mean()
        l = (-d.where(d < 0, 0)).rolling(n).mean()
        return 100 - (100 / (1 + g / l))

    def _atr(self, d):
        tr = pd.concat([
            d['high'] - d['low'],
            abs(d['high'] - d['close'].shift()),
            abs(d['low'] - d['close'].shift())
        ], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()


if __name__ == "__main__":
    import yfinance as yf

    yf_symbols = {
        "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X",
        "AUDUSD": "AUDUSD=X", "USDCAD": "USDCAD=X", "EURJPY": "EURJPY=X",
        "GBPJPY": "GBPJPY=X", "NZDUSD": "NZDUSD=X"
    }
    strat = ForexRSI2BounceStrategy()
    max_hold = 5  # short hold for mean reversion

    all_trades = []

    for sym, ticker in yf_symbols.items():
        print(f"\n--- {sym} ({ticker}) ---")
        try:
            df = yf.download(ticker, period="1y", interval="1d", progress=False)
        except Exception as e:
            print(f"  Download failed: {e}")
            continue

        if df.empty or len(df) < 220:
            print(f"  Insufficient data ({len(df)} bars)")
            continue

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        df.columns = [c.lower() for c in df.columns]
        if 'adj close' in df.columns and 'close' in df.columns:
            df['close'] = df['adj close']
        df = df.dropna(subset=['close', 'high', 'low'])

        trades = []
        i = 210
        while i < len(df):
            window = df.iloc[:i+1]
            sigs = strat.generate_signals(window, symbol=sym)
            if not sigs:
                i += 1
                continue

            sig = sigs[0]
            entry_price = sig.entry_price
            direction = sig.direction

            exit_price = None
            exit_reason = "max_hold"
            for j in range(1, max_hold + 1):
                if i + j >= len(df):
                    break
                bar = df.iloc[i + j]
                if direction == "BUY":
                    if bar['low'] <= sig.stop_loss:
                        exit_price = sig.stop_loss; exit_reason = "SL"; break
                    if bar['high'] >= sig.take_profit:
                        exit_price = sig.take_profit; exit_reason = "TP"; break
                else:
                    if bar['high'] >= sig.stop_loss:
                        exit_price = sig.stop_loss; exit_reason = "SL"; break
                    if bar['low'] <= sig.take_profit:
                        exit_price = sig.take_profit; exit_reason = "TP"; break

            if exit_price is None:
                end_idx = min(i + max_hold, len(df) - 1)
                exit_price = df.iloc[end_idx]['close']

            if direction == "BUY":
                pnl_pct = (exit_price - entry_price) / entry_price * 100
            else:
                pnl_pct = (entry_price - exit_price) / entry_price * 100

            trades.append({
                'symbol': sym, 'direction': direction,
                'entry': entry_price, 'exit': exit_price,
                'pnl_pct': pnl_pct, 'reason': exit_reason,
                'confidence': sig.confidence
            })
            i += max_hold + 1

        all_trades.extend(trades)

        if trades:
            wins = [t for t in trades if t['pnl_pct'] > 0]
            losses = [t for t in trades if t['pnl_pct'] <= 0]
            wr = len(wins) / len(trades) * 100
            avg_pnl = np.mean([t['pnl_pct'] for t in trades])
            gross_profit = sum(t['pnl_pct'] for t in wins) if wins else 0
            gross_loss = abs(sum(t['pnl_pct'] for t in losses)) if losses else 0.001
            pf = gross_profit / gross_loss
            print(f"  Trades: {len(trades)}  WR: {wr:.1f}%  PF: {pf:.2f}  Avg PnL: {avg_pnl:.3f}%")
            for t in trades:
                print(f"    {t['direction']} {t['reason']:8s}  PnL={t['pnl_pct']:+.3f}%  conf={t['confidence']}")
        else:
            print("  No trades generated")

    print("\n=== AGGREGATE RESULTS ===")
    if all_trades:
        wins = [t for t in all_trades if t['pnl_pct'] > 0]
        losses = [t for t in all_trades if t['pnl_pct'] <= 0]
        wr = len(wins) / len(all_trades) * 100
        avg_pnl = np.mean([t['pnl_pct'] for t in all_trades])
        gross_profit = sum(t['pnl_pct'] for t in wins) if wins else 0
        gross_loss = abs(sum(t['pnl_pct'] for t in losses)) if losses else 0.001
        pf = gross_profit / gross_loss
        print(f"Total trades: {len(all_trades)}  WR: {wr:.1f}%  PF: {pf:.2f}  Avg PnL: {avg_pnl:.3f}%")
        buy_ct = sum(1 for t in all_trades if t['direction'] == 'BUY')
        sell_ct = sum(1 for t in all_trades if t['direction'] == 'SELL')
        print(f"BUY: {buy_ct}  SELL: {sell_ct}")
    else:
        print("No trades generated across all pairs")
