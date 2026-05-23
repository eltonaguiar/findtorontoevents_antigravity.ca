"""Forex Carry Momentum - Combine carry trade logic with triple EMA momentum.
LONG pairs where RSI(14) > 55 AND EMA(20) > EMA(50) AND EMA(50) > EMA(100).
SHORT when RSI(14) < 45 AND EMA(20) < EMA(50) < EMA(100).
Triple EMA alignment with momentum confirmation. TP: 2.0x ATR, SL: 1.5x ATR.
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List

SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "EURJPY", "GBPJPY", "NZDUSD"]

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class ForexCarryMomentumStrategy:
    def __init__(self, p=None):
        self.p = p or {}
        self.ema_fast = self.p.get('ema_fast', 20)
        self.ema_mid = self.p.get('ema_mid', 50)
        self.ema_slow = self.p.get('ema_slow', 100)
        self.rsi_period = self.p.get('rsi_period', 14)
        self.rsi_long_th = self.p.get('rsi_long_th', 55)
        self.rsi_short_th = self.p.get('rsi_short_th', 45)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.0)
        self.sl_atr = self.p.get('sl_atr', 1.5)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "EURUSD") -> List[Signal]:
        min_len = self.ema_slow + self.rsi_period + 20
        if len(data) < min_len:
            return []

        close = data['close']
        ef = close.ewm(span=self.ema_fast, adjust=False).mean()
        em = close.ewm(span=self.ema_mid, adjust=False).mean()
        es = close.ewm(span=self.ema_slow, adjust=False).mean()
        rsi = self._rsi(close, self.rsi_period)
        atr = self._atr(data)

        ef_v, em_v, es_v = ef.iloc[-1], em.iloc[-1], es.iloc[-1]
        r = rsi.iloc[-1]
        cp = close.iloc[-1]
        ca = atr.iloc[-1]

        if pd.isna(r) or pd.isna(ca) or ca == 0 or any(pd.isna(v) for v in [ef_v, em_v, es_v]):
            return []

        bullish_stack = ef_v > em_v > es_v
        bearish_stack = ef_v < em_v < es_v

        # Measure trend strength via EMA separation
        ema_spread = abs(ef_v - es_v) / cp * 100 if cp > 0 else 0

        signals = []
        if bullish_stack and r > self.rsi_long_th:
            mom_extra = (r - self.rsi_long_th) * 0.005
            conf = min(0.58 + ema_spread * 3 + mom_extra, 0.90)
            tp = cp + ca * self.tp_atr
            sl = cp - ca * self.sl_atr
            signals.append(Signal(
                symbol, "BUY", round(conf, 2), round(cp, 6),
                round(tp, 6), round(sl, 6),
                f"CarryMom BULL EMA20>50>100 RSI={r:.0f} spread={ema_spread:.3f}%"
            ))
        elif bearish_stack and r < self.rsi_short_th:
            mom_extra = (self.rsi_short_th - r) * 0.005
            conf = min(0.58 + ema_spread * 3 + mom_extra, 0.90)
            tp = cp - ca * self.tp_atr
            sl = cp + ca * self.sl_atr
            signals.append(Signal(
                symbol, "SELL", round(conf, 2), round(cp, 6),
                round(tp, 6), round(sl, 6),
                f"CarryMom BEAR EMA20<50<100 RSI={r:.0f} spread={ema_spread:.3f}%"
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
    strat = ForexCarryMomentumStrategy()
    max_hold = 12

    all_trades = []

    for sym, ticker in yf_symbols.items():
        print(f"\n--- {sym} ({ticker}) ---")
        try:
            df = yf.download(ticker, period="1y", interval="1d", progress=False)
        except Exception as e:
            print(f"  Download failed: {e}")
            continue

        if df.empty or len(df) < 130:
            print(f"  Insufficient data ({len(df)} bars)")
            continue

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        df.columns = [c.lower() for c in df.columns]
        if 'adj close' in df.columns and 'close' in df.columns:
            df['close'] = df['adj close']
        df = df.dropna(subset=['close', 'high', 'low'])

        trades = []
        i = 130
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
