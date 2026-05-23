"""Forex Session Momentum - London/NY overlap momentum strategy.
Exploits the highest-volatility window in forex (13:00-17:00 UTC).
When a strong directional move starts with EMA alignment and volume expansion, ride momentum.
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "EURJPY", "GBPJPY", "NZDUSD"]

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

class ForexSessionMomentumStrategy:
    def __init__(self, p=None):
        self.p = p or {}
        self.ema_fast = self.p.get('ema_fast', 8)
        self.ema_slow = self.p.get('ema_slow', 21)
        self.atr_period = self.p.get('atr_period', 14)
        self.atr_avg_period = self.p.get('atr_avg_period', 20)
        self.mom_bars = self.p.get('mom_bars', 4)
        self.mom_threshold = self.p.get('mom_threshold', 0.15)
        self.vol_expansion = self.p.get('vol_expansion', 1.2)
        self.tp_atr = self.p.get('tp_atr', 1.8)
        self.sl_atr = self.p.get('sl_atr', 1.0)
        self.base_conf = self.p.get('base_conf', 0.60)
        self.max_conf = self.p.get('max_conf', 0.85)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "EURUSD") -> List[Signal]:
        min_len = max(self.ema_slow, self.atr_avg_period + self.atr_period, self.mom_bars) + 10
        if len(data) < min_len:
            return []

        close = data['close']
        ema_f = close.ewm(span=self.ema_fast, adjust=False).mean()
        ema_s = close.ewm(span=self.ema_slow, adjust=False).mean()
        atr = self._atr(data)
        atr_avg = atr.rolling(self.atr_avg_period).mean()

        # 4-bar momentum as percentage
        momentum = (close - close.shift(self.mom_bars)) / close.shift(self.mom_bars) * 100

        ef, es = ema_f.iloc[-1], ema_s.iloc[-1]
        ca, cam = atr.iloc[-1], atr_avg.iloc[-1]
        mom = momentum.iloc[-1]
        cp = close.iloc[-1]

        if pd.isna(mom) or pd.isna(ca) or pd.isna(cam) or cam == 0:
            return []

        vol_ok = ca > cam * self.vol_expansion
        if not vol_ok:
            return []

        signals = []
        abs_mom = abs(mom)

        if ef > es and mom > self.mom_threshold:
            # BUY signal
            extra_mom = (mom - self.mom_threshold) / 0.1
            conf = min(self.base_conf + 0.05 * extra_mom, self.max_conf)
            tp = cp + ca * self.tp_atr
            sl = cp - ca * self.sl_atr
            signals.append(Signal(
                symbol, "BUY", round(conf, 2), round(cp, 6),
                round(tp, 6), round(sl, 6),
                f"EMA8>21 mom={mom:+.2f}% ATRx={ca/cam:.2f}"
            ))

        elif ef < es and mom < -self.mom_threshold:
            # SELL signal
            extra_mom = (abs_mom - self.mom_threshold) / 0.1
            conf = min(self.base_conf + 0.05 * extra_mom, self.max_conf)
            tp = cp - ca * self.tp_atr
            sl = cp + ca * self.sl_atr
            signals.append(Signal(
                symbol, "SELL", round(conf, 2), round(cp, 6),
                round(tp, 6), round(sl, 6),
                f"EMA8<21 mom={mom:+.2f}% ATRx={ca/cam:.2f}"
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

    yf_symbols = {"EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X"}
    strat = ForexSessionMomentumStrategy()
    max_hold = 12

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

        # Flatten multi-level columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]

        df.columns = [c.lower() for c in df.columns]
        if 'adj close' in df.columns and 'close' in df.columns:
            df['close'] = df['adj close']
        df = df.dropna(subset=['close', 'high', 'low'])

        trades = []
        i = 60  # start after enough lookback
        while i < len(df):
            window = df.iloc[:i+1]
            sigs = strat.generate_signals(window, symbol=sym)
            if not sigs:
                i += 1
                continue

            sig = sigs[0]
            entry_price = sig.entry_price
            direction = sig.direction

            # Walk forward to check TP/SL hit or max hold
            exit_price = None
            exit_reason = "max_hold"
            for j in range(1, max_hold + 1):
                if i + j >= len(df):
                    break
                bar = df.iloc[i + j]
                if direction == "BUY":
                    if bar['low'] <= sig.stop_loss:
                        exit_price = sig.stop_loss
                        exit_reason = "SL"
                        break
                    if bar['high'] >= sig.take_profit:
                        exit_price = sig.take_profit
                        exit_reason = "TP"
                        break
                else:  # SELL
                    if bar['high'] >= sig.stop_loss:
                        exit_price = sig.stop_loss
                        exit_reason = "SL"
                        break
                    if bar['low'] <= sig.take_profit:
                        exit_price = sig.take_profit
                        exit_reason = "TP"
                        break

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

            # Skip forward past trade duration
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

    # --- Aggregate ---
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
