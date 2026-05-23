"""Forex Range Breakout - 20-bar range breakout with volatility expansion filter.
Identify 20-bar range (highest high - lowest low). LONG when close breaks above range high
AND ATR > ATR_SMA20 (volatility expansion). SHORT when breaks below.
TP: range height, SL: 50% of range height.
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List

SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "EURJPY", "GBPJPY", "NZDUSD"]

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class ForexRangeBreakoutStrategy:
    def __init__(self, p=None):
        self.p = p or {}
        self.range_period = self.p.get('range_period', 20)
        self.atr_period = self.p.get('atr_period', 14)
        self.atr_sma_period = self.p.get('atr_sma_period', 20)
        self.tp_range_mult = self.p.get('tp_range_mult', 1.0)
        self.sl_range_mult = self.p.get('sl_range_mult', 0.5)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "EURUSD") -> List[Signal]:
        min_len = self.range_period + self.atr_sma_period + 20
        if len(data) < min_len:
            return []

        close = data['close']
        high = data['high']
        low = data['low']

        # 20-bar range (excluding current bar)
        range_high = high.rolling(self.range_period).max().shift(1)
        range_low = low.rolling(self.range_period).min().shift(1)
        range_height = range_high - range_low

        atr = self._atr(data)
        atr_sma = atr.rolling(self.atr_sma_period).mean()

        cp = close.iloc[-1]
        rh = range_high.iloc[-1]
        rl = range_low.iloc[-1]
        rht = range_height.iloc[-1]
        ca = atr.iloc[-1]
        ca_sma = atr_sma.iloc[-1]

        if pd.isna(rh) or pd.isna(ca) or pd.isna(ca_sma) or ca_sma == 0 or rht == 0:
            return []

        vol_expanding = ca > ca_sma
        if not vol_expanding:
            return []

        vol_ratio = ca / ca_sma
        signals = []

        if cp > rh:
            breakout_strength = (cp - rh) / rht if rht > 0 else 0
            conf = min(0.58 + breakout_strength * 0.5 + (vol_ratio - 1) * 0.15, 0.88)
            tp = cp + rht * self.tp_range_mult
            sl = cp - rht * self.sl_range_mult
            signals.append(Signal(
                symbol, "BUY", round(conf, 2), round(cp, 6),
                round(tp, 6), round(sl, 6),
                f"Range breakout UP rng={rht:.5f} ATRx={vol_ratio:.2f}"
            ))
        elif cp < rl:
            breakout_strength = (rl - cp) / rht if rht > 0 else 0
            conf = min(0.58 + breakout_strength * 0.5 + (vol_ratio - 1) * 0.15, 0.88)
            tp = cp - rht * self.tp_range_mult
            sl = cp + rht * self.sl_range_mult
            signals.append(Signal(
                symbol, "SELL", round(conf, 2), round(cp, 6),
                round(tp, 6), round(sl, 6),
                f"Range breakout DN rng={rht:.5f} ATRx={vol_ratio:.2f}"
            ))

        return signals

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
    strat = ForexRangeBreakoutStrategy()
    max_hold = 10

    all_trades = []

    for sym, ticker in yf_symbols.items():
        print(f"\n--- {sym} ({ticker}) ---")
        try:
            df = yf.download(ticker, period="1y", interval="1d", progress=False)
        except Exception as e:
            print(f"  Download failed: {e}")
            continue

        if df.empty or len(df) < 60:
            print(f"  Insufficient data ({len(df)} bars)")
            continue

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        df.columns = [c.lower() for c in df.columns]
        if 'adj close' in df.columns and 'close' in df.columns:
            df['close'] = df['adj close']
        df = df.dropna(subset=['close', 'high', 'low'])

        trades = []
        i = 60
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
