"""
Inverse RSI Momentum Confluence
================================
Original: st_rsi_momentum_confluence -- 0% WR, -49.2% PnL, 17 trades
Original logic: RSI + momentum confluence -> LONG
Inverse: same signal -> SHORT (fade the RSI momentum confluence)

Rationale: The original strategy consistently loses because RSI+momentum
confluence in crypto often marks local tops (momentum exhaustion), not
continuation. Fading it should capture mean-reversion profits.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Optional
import requests
import time


@dataclass
class Signal:
    symbol: str
    direction: str       # "BUY" or "SELL"
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class InverseRSIMomentumConfluenceStrategy:
    """
    Fades the RSI + Momentum confluence signal.

    Original detects: RSI > 60 AND price momentum (ROC) > threshold -> BUY
    Inverse: same conditions -> SELL (short) because confluence marks exhaustion.
    Also inverts the oversold side: RSI < 40 AND negative ROC -> BUY (fade panic).
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.rsi_period = self.params.get('rsi_period', 14)
        self.roc_period = self.params.get('roc_period', 10)
        self.rsi_ob = self.params.get('rsi_overbought', 70)   # tight: only extreme readings
        self.rsi_os = self.params.get('rsi_oversold', 30)     # tight: only extreme readings
        self.roc_threshold = self.params.get('roc_threshold', 0.04)  # strong momentum req
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr = self.params.get('tp_atr', 2.0)
        self.sl_atr = self.params.get('sl_atr', 1.2)
        self.cooldown = self.params.get('cooldown', 6)  # min bars between signals

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_len = max(self.rsi_period, self.roc_period, self.atr_period) + 20
        if len(data) < min_len:
            return []

        rsi = self._calculate_rsi(data['close'], self.rsi_period)
        roc = data['close'].pct_change(self.roc_period)
        atr = self._calculate_atr(data)

        signals = []
        last_signal_bar = -self.cooldown
        for i in range(min_len, len(data)):
            if i - last_signal_bar < self.cooldown:
                continue

            cur_rsi = rsi.iloc[i]
            cur_roc = roc.iloc[i]
            cur_atr = atr.iloc[i]
            cur_price = data['close'].iloc[i]

            if pd.isna(cur_rsi) or pd.isna(cur_roc) or pd.isna(cur_atr) or cur_atr == 0:
                continue

            # Also require RSI was recently more extreme (confirmation of exhaustion)
            prev_rsi = rsi.iloc[i - 3:i]
            if prev_rsi.isna().any():
                continue

            # Original would BUY on RSI>70 + strong momentum -> INVERSE: SELL
            if cur_rsi > self.rsi_ob and cur_roc > self.roc_threshold:
                # Extra filter: RSI must be declining from peak (exhaustion confirmed)
                if prev_rsi.max() > cur_rsi:
                    confidence = min((cur_rsi - self.rsi_ob) / 30 * 0.6 + 0.4, 0.95)
                    signals.append(Signal(
                        symbol=symbol,
                        direction="SELL",
                        confidence=round(confidence, 2),
                        entry_price=cur_price,
                        take_profit=round(cur_price - cur_atr * self.tp_atr, 2),
                        stop_loss=round(cur_price + cur_atr * self.sl_atr, 2),
                        reason=f"INV_RSI_MOM: RSI={cur_rsi:.1f} ROC={cur_roc:.3f} -> fade bullish confluence"
                    ))
                    last_signal_bar = i

            # Original would SELL on RSI<30 + strong neg momentum -> INVERSE: BUY
            elif cur_rsi < self.rsi_os and cur_roc < -self.roc_threshold:
                # Extra filter: RSI must be rising from bottom (capitulation exhaustion)
                if prev_rsi.min() < cur_rsi:
                    confidence = min((self.rsi_os - cur_rsi) / 30 * 0.6 + 0.4, 0.95)
                    signals.append(Signal(
                        symbol=symbol,
                        direction="BUY",
                        confidence=round(confidence, 2),
                        entry_price=cur_price,
                        take_profit=round(cur_price + cur_atr * self.tp_atr, 2),
                        stop_loss=round(cur_price - cur_atr * self.sl_atr, 2),
                        reason=f"INV_RSI_MOM: RSI={cur_rsi:.1f} ROC={cur_roc:.3f} -> fade bearish confluence"
                    ))
                    last_signal_bar = i

        return signals

    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_atr(self, data: pd.DataFrame) -> pd.Series:
        high, low, close = data['high'], data['low'], data['close']
        tr = pd.concat([
            high - low,
            abs(high - close.shift()),
            abs(low - close.shift())
        ], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()


# ==============================================================================
# BACKTEST
# ==============================================================================

def fetch_binance_klines(symbol: str, interval: str = "4h", days: int = 180) -> pd.DataFrame:
    """Fetch klines with 3+ endpoint failover per CLAUDE.md rules."""
    endpoints = [
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://api2.binance.com",
        "https://api3.binance.com",
    ]
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - days * 24 * 60 * 60 * 1000
    all_data = []
    cur = start_ms

    while cur < end_ms:
        success = False
        for base in endpoints:
            try:
                url = f"{base}/api/v3/klines"
                resp = requests.get(url, params={
                    "symbol": symbol, "interval": interval,
                    "startTime": cur, "limit": 1000
                }, timeout=10)
                if resp.status_code == 200:
                    rows = resp.json()
                    if rows:
                        all_data.extend(rows)
                        cur = rows[-1][0] + 1
                        success = True
                        break
            except Exception:
                continue
        if not success:
            break
        time.sleep(0.2)

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_vol', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    for c in ['open', 'high', 'low', 'close', 'volume']:
        df[c] = df[c].astype(float)
    df = df.drop_duplicates(subset='open_time').sort_values('open_time').reset_index(drop=True)
    return df


def backtest_walk_forward(strategy, data: pd.DataFrame, symbol: str, lookahead: int = 12):
    """Walk-forward backtest: check TP/SL within lookahead bars."""
    signals = strategy.generate_signals(data, symbol)
    results = []

    for sig in signals:
        entry_idx = data.index[data['close'] == sig.entry_price].tolist()
        if not entry_idx:
            # Find closest
            entry_idx = (data['close'] - sig.entry_price).abs().idxmin()
        else:
            entry_idx = entry_idx[0]

        for j in range(entry_idx + 1, min(entry_idx + lookahead + 1, len(data))):
            bar_high = data['high'].iloc[j]
            bar_low = data['low'].iloc[j]

            if sig.direction == "SELL":
                if bar_low <= sig.take_profit:
                    pnl_pct = (sig.entry_price - sig.take_profit) / sig.entry_price * 100
                    results.append({"symbol": symbol, "direction": sig.direction,
                                    "pnl_pct": pnl_pct, "outcome": "TP"})
                    break
                elif bar_high >= sig.stop_loss:
                    pnl_pct = -(sig.stop_loss - sig.entry_price) / sig.entry_price * 100
                    results.append({"symbol": symbol, "direction": sig.direction,
                                    "pnl_pct": pnl_pct, "outcome": "SL"})
                    break
            else:  # BUY
                if bar_high >= sig.take_profit:
                    pnl_pct = (sig.take_profit - sig.entry_price) / sig.entry_price * 100
                    results.append({"symbol": symbol, "direction": sig.direction,
                                    "pnl_pct": pnl_pct, "outcome": "TP"})
                    break
                elif bar_low <= sig.stop_loss:
                    pnl_pct = -(sig.entry_price - sig.stop_loss) / sig.entry_price * 100
                    results.append({"symbol": symbol, "direction": sig.direction,
                                    "pnl_pct": pnl_pct, "outcome": "SL"})
                    break
        else:
            # Expired without TP/SL
            exit_price = data['close'].iloc[min(entry_idx + lookahead, len(data) - 1)]
            if sig.direction == "SELL":
                pnl_pct = (sig.entry_price - exit_price) / sig.entry_price * 100
            else:
                pnl_pct = (exit_price - sig.entry_price) / sig.entry_price * 100
            results.append({"symbol": symbol, "direction": sig.direction,
                            "pnl_pct": pnl_pct, "outcome": "EXPIRED"})

    return results


if __name__ == "__main__":
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT"]
    strategy = InverseRSIMomentumConfluenceStrategy()
    all_results = []

    print("=" * 70)
    print("BACKTEST: inverse_rsi_momentum_confluence")
    print("  Original: 0% WR, -49.2% PnL -> expecting inverse to profit")
    print("=" * 70)

    for sym in symbols:
        print(f"\nFetching {sym} 4h data (180 days)...")
        df = fetch_binance_klines(sym, "4h", 180)
        if df.empty:
            print(f"  SKIP {sym}: no data")
            continue
        print(f"  Got {len(df)} bars")
        results = backtest_walk_forward(strategy, df, sym)
        all_results.extend(results)

        wins = [r for r in results if r['pnl_pct'] > 0]
        losses = [r for r in results if r['pnl_pct'] <= 0]
        wr = len(wins) / len(results) * 100 if results else 0
        avg_pnl = np.mean([r['pnl_pct'] for r in results]) if results else 0
        print(f"  {sym}: {len(results)} trades, WR={wr:.1f}%, avg PnL={avg_pnl:.2f}%")

    # Summary
    print("\n" + "=" * 70)
    print("OVERALL SUMMARY")
    print("=" * 70)
    if all_results:
        total = len(all_results)
        wins = [r for r in all_results if r['pnl_pct'] > 0]
        losses = [r for r in all_results if r['pnl_pct'] <= 0]
        wr = len(wins) / total * 100
        gross_profit = sum(r['pnl_pct'] for r in wins) if wins else 0
        gross_loss = abs(sum(r['pnl_pct'] for r in losses)) if losses else 0.001
        pf = gross_profit / gross_loss if gross_loss > 0 else 999
        avg_pnl = np.mean([r['pnl_pct'] for r in all_results])
        print(f"  Trades: {total}")
        print(f"  Win Rate: {wr:.1f}%")
        print(f"  Profit Factor: {pf:.2f}")
        print(f"  Avg PnL: {avg_pnl:.2f}%")
        print(f"  Gross Profit: {gross_profit:.2f}%  |  Gross Loss: {gross_loss:.2f}%")
        # Per-symbol breakdown
        print("\n  Per-symbol breakdown:")
        for sym in symbols:
            sym_results = [r for r in all_results if r['symbol'] == sym]
            if sym_results:
                sw = [r for r in sym_results if r['pnl_pct'] > 0]
                swr = len(sw) / len(sym_results) * 100
                savg = np.mean([r['pnl_pct'] for r in sym_results])
                sgp = sum(r['pnl_pct'] for r in sw) if sw else 0
                sgl = abs(sum(r['pnl_pct'] for r in sym_results if r['pnl_pct'] <= 0))
                spf = sgp / sgl if sgl > 0 else 999
                print(f"    {sym}: {len(sym_results)} trades, WR={swr:.1f}%, PF={spf:.2f}, avg={savg:.2f}%")

        # With asymmetric TP:SL (2.0:1.2), breakeven WR ~37.5%
        # Primary: PF > 1.2 AND 30+ trades. Secondary: WR > 50% nice-to-have
        verdict = "KEEP" if pf > 1.2 and total >= 30 else "REJECT"
        print(f"  Verdict: {verdict} (need PF>1.2, 30+ trades; breakeven WR~37.5% with 2.0:1.2 TP:SL)")
        if verdict == "KEEP" and wr < 50:
            print(f"  Note: WR {wr:.1f}% < 50% but profitable due to asymmetric TP:SL ratio")
    else:
        print("  No trades generated.")
