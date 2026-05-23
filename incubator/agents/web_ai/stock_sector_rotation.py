"""Stock Sector Rotation - Compare ETF performance: XLK (tech), XLE (energy), XLF (finance),
XLV (health). LONG the strongest sector ETF when it's above its 50-SMA and RSI < 70.
TP: 2.0x ATR, SL: 1.5x ATR."""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float; take_profit: float; stop_loss: float; reason: str

SYMBOLS = ["XLK", "XLE", "XLF", "XLV"]

class StockSectorRotationStrategy:
    def __init__(self, p=None):
        self.p = p or {}
        self.momentum_period = self.p.get('momentum_period', 20)
        self.sma_period = self.p.get('sma_period', 50)
        self.rsi_period = self.p.get('rsi_period', 14)
        self.rsi_max = self.p.get('rsi_max', 70)
        self.atr_period = self.p.get('atr_period', 14)
        self.tp_atr = self.p.get('tp_atr', 2.0)
        self.sl_atr = self.p.get('sl_atr', 1.5)

    def generate_signals(self, sector_data: dict, symbol: str = None) -> List[Signal]:
        """sector_data: dict of {symbol: pd.DataFrame} for each sector ETF."""
        min_bars = max(self.sma_period, self.momentum_period, self.rsi_period) + 10
        # Calculate momentum for each sector
        momentum = {}
        for sym, data in sector_data.items():
            if len(data) < min_bars:
                continue
            ret = (data['close'].iloc[-1] / data['close'].iloc[-(self.momentum_period + 1)] - 1) * 100
            momentum[sym] = ret
        if not momentum:
            return []
        # Pick strongest sector
        best_sym = max(momentum, key=momentum.get)
        data = sector_data[best_sym]
        close = data['close'].iloc[-1]
        sma50 = data['close'].rolling(self.sma_period).mean().iloc[-1]
        rsi = self._rsi(data['close'], self.rsi_period).iloc[-1]
        atr = self._atr(data).iloc[-1]
        if pd.isna(rsi) or pd.isna(sma50) or pd.isna(atr) or atr <= 0:
            return []
        # LONG: strongest sector, above SMA50, RSI < 70 (not overbought)
        if close > sma50 and rsi < self.rsi_max:
            mom_val = momentum[best_sym]
            conf = min(0.60 + mom_val * 0.01 + (self.rsi_max - rsi) * 0.003, 0.88)
            return [Signal(best_sym, "BUY", round(max(conf, 0.55), 2), round(close, 2),
                           round(close + atr * self.tp_atr, 2),
                           round(close - atr * self.sl_atr, 2),
                           f"SectorLeader mom={mom_val:.1f}% RSI={rsi:.0f}")]
        return []

    def generate_signals_single(self, data: pd.DataFrame, symbol: str = "XLK") -> List[Signal]:
        """Single-symbol interface for compatibility."""
        return self.generate_signals({symbol: data}, symbol)

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

    MAX_HOLD = 10
    strat = StockSectorRotationStrategy()

    # Download all sector ETFs
    print("Downloading sector ETF data (2 years daily)...")
    sector_dfs = {}
    for sym in SYMBOLS:
        print(f"  Fetching {sym}...")
        df = yf.download(sym, period="2y", interval="1d", progress=False)
        if df.empty:
            print(f"  No data for {sym}, skipping"); continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        df.columns = [c.lower() for c in df.columns]
        df = df.reset_index(drop=True)
        sector_dfs[sym] = df

    if len(sector_dfs) < 2:
        print("Insufficient sector data"); exit()

    min_len = min(len(d) for d in sector_dfs.values())
    # Trim all to same length
    for sym in sector_dfs:
        sector_dfs[sym] = sector_dfs[sym].iloc[-min_len:].reset_index(drop=True)

    all_trades = []
    i = 70
    while i < min_len:
        # Build windowed data for each sector
        windowed = {sym: sector_dfs[sym].iloc[:i + 1].copy() for sym in sector_dfs}
        sigs = strat.generate_signals(windowed)
        if sigs:
            sig = sigs[0]
            sym = sig.symbol
            entry_price = sig.entry_price
            exit_price = None
            sdf = sector_dfs[sym]
            for j in range(i + 1, min(i + 1 + MAX_HOLD, min_len)):
                bar_high = sdf['high'].iloc[j]
                bar_low = sdf['low'].iloc[j]
                if bar_low <= sig.stop_loss:
                    exit_price = sig.stop_loss; break
                if bar_high >= sig.take_profit:
                    exit_price = sig.take_profit; break
            if exit_price is None:
                exit_idx = min(i + MAX_HOLD, min_len - 1)
                exit_price = sdf['close'].iloc[exit_idx]
            pnl_pct = (exit_price - entry_price) / entry_price * 100
            all_trades.append({'symbol': sym, 'dir': 'BUY', 'entry': entry_price,
                               'exit': exit_price, 'pnl_pct': pnl_pct,
                               'conf': sig.confidence, 'reason': sig.reason})
            print(f"  BUY {sym} @ {entry_price:.2f} -> {exit_price:.2f}  "
                  f"PnL={pnl_pct:+.2f}%  {sig.reason}")
            i += MAX_HOLD + 1
        else:
            i += 1

    print(f"\n{'='*50}")
    print(f"STOCK SECTOR ROTATION BACKTEST SUMMARY")
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
        # Sector breakdown
        for sym in SYMBOLS:
            sym_trades = [t for t in all_trades if t['symbol'] == sym]
            if sym_trades:
                sym_wr = len([t for t in sym_trades if t['pnl_pct'] > 0]) / len(sym_trades) * 100
                print(f"  {sym}: {len(sym_trades)} trades, WR={sym_wr:.0f}%")
    else:
        print("No trades generated.")
