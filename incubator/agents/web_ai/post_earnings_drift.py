"""Post-Earnings Announcement Drift (PEAD) - Exploits the well-documented anomaly where
stocks drift in the direction of earnings surprise for 30-60 days. Approximated via
volume surge + price gap detection as proxy for earnings events."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "MA",
           "XOM", "JNJ", "PG", "HD", "UNH"]

class PostEarningsDriftStrategy:
    def __init__(self, p=None):
        self.p = p or {}
        self.vol_lookback = self.p.get('vol_lookback', 20)
        self.vol_mult = self.p.get('vol_mult', 3.0)
        self.body_pct = self.p.get('body_pct', 0.02)
        self.rsi_period = self.p.get('rsi_period', 14)
        self.atr_period = self.p.get('atr_period', 14)
        self.sma_period = self.p.get('sma_period', 50)
        self.tp_atr = self.p.get('tp_atr', 3.0)
        self.sl_atr = self.p.get('sl_atr', 1.5)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "AAPL") -> List[Signal]:
        min_bars = max(self.sma_period, self.vol_lookback, self.atr_period) + 10
        if len(data) < min_bars:
            return []
        o, c, v = data['open'].iloc[-1], data['close'].iloc[-1], data['volume'].iloc[-1]
        # Earnings-like event: volume > 3x 20-day avg AND |close-open|/open > 2%
        vol_avg = data['volume'].iloc[-(self.vol_lookback + 1):-1].mean()
        if vol_avg <= 0:
            return []
        vol_ratio = v / vol_avg
        body_ratio = abs(c - o) / o if o > 0 else 0
        if vol_ratio < self.vol_mult or body_ratio < self.body_pct:
            return []
        # Indicators
        rsi = self._rsi(data['close'], self.rsi_period).iloc[-1]
        atr = self._atr(data).iloc[-1]
        sma50 = data['close'].rolling(self.sma_period).mean().iloc[-1]
        if pd.isna(rsi) or pd.isna(atr) or pd.isna(sma50) or atr <= 0:
            return []
        # Confidence: 0.60 + (volume_ratio - 3) * 0.05, capped at 0.85
        conf = min(0.60 + (vol_ratio - 3) * 0.05, 0.85)
        conf = round(max(conf, 0.60), 2)
        positive = c > o
        # BUY: positive surprise, close > SMA50, RSI < 70
        if positive and c > sma50 and rsi < 70:
            return [Signal(symbol, "BUY", conf, round(c, 2),
                           round(c + atr * self.tp_atr, 2),
                           round(c - atr * self.sl_atr, 2),
                           f"PEAD+ vol={vol_ratio:.1f}x body={body_ratio:.1%} RSI={rsi:.0f}")]
        # SELL: negative surprise, close < SMA50, RSI > 30
        if not positive and c < sma50 and rsi > 30:
            return [Signal(symbol, "SELL", conf, round(c, 2),
                           round(c - atr * self.tp_atr, 2),
                           round(c + atr * self.sl_atr, 2),
                           f"PEAD- vol={vol_ratio:.1f}x body={body_ratio:.1%} RSI={rsi:.0f}")]
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

    BACKTEST_SYMBOLS = ["AAPL", "MSFT", "NVDA", "META", "TSLA"]
    MAX_HOLD = 20  # bars — drift trades hold longer
    strat = PostEarningsDriftStrategy()

    all_trades = []
    for sym in BACKTEST_SYMBOLS:
        print(f"\n{'='*50}")
        print(f"Fetching {sym} (2 years daily)...")
        df = yf.download(sym, period="2y", interval="1d", progress=False)
        if df.empty:
            print(f"  No data for {sym}, skipping"); continue
        # Flatten multi-level columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        df.columns = [c.lower() for c in df.columns]
        df = df.reset_index(drop=True)
        if len(df) < 70:
            print(f"  Insufficient data for {sym}"); continue

        trades = []
        i = 60  # start after enough lookback
        while i < len(df):
            window = df.iloc[:i + 1].copy()
            sigs = strat.generate_signals(window, symbol=sym)
            if sigs:
                sig = sigs[0]
                entry_price = sig.entry_price
                direction = sig.direction
                # Walk forward to check TP/SL/max-hold
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
                i += MAX_HOLD + 1  # skip hold period
            else:
                i += 1

        print(f"  {sym}: {len(trades)} trades")
        for t in trades:
            print(f"    {t['dir']} {t['symbol']} @ {t['entry']:.2f} -> {t['exit']:.2f}  "
                  f"PnL={t['pnl_pct']:+.2f}%  conf={t['conf']}  {t['reason']}")
        all_trades.extend(trades)

    # Summary
    print(f"\n{'='*50}")
    print(f"PEAD BACKTEST SUMMARY")
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
