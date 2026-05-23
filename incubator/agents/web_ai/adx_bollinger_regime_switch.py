"""
ADX-Bollinger Regime Switcher
==============================

Created by: web_ai
Date: 2026-03-28
Rank: #3 from research pipeline

Strategy Logic:
- Detect market regime using ADX(14)
- Three modes:
  IDLE      (ADX < 15): No trades -- market too directionless
  MEAN_REV  (ADX 15-25): Buy at lower BB + RSI<35, sell at upper BB + RSI>65
                          TP = middle BB, SL = 1.5x ATR
  BREAKOUT  (ADX > 25 + BB breach): Long if close > upper BB (momentum),
                          Short if close < lower BB. TP = 2.5x ATR, SL = 1.2x ATR
- Confidence: 0.60 base + 0.02 * ADX above threshold (cap 0.85)
- 4-bar cooldown between signals

Unique Value Proposition:
Most strategies pick one regime and fail in the other.  This uses ADX to
classify the regime first, then applies the appropriate sub-strategy
(mean-reversion vs breakout).  The IDLE gate prevents whipsaws in
trendless chop.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Optional
import requests
import time


@dataclass
class Signal:
    """A trading signal - required return type."""
    symbol: str           # e.g., "BTCUSDT"
    direction: str        # "BUY" or "SELL"
    confidence: float     # 0.0 to 1.0
    entry_price: float    # Suggested entry
    take_profit: float    # Target price
    stop_loss: float      # Stop price
    reason: str           # Why this signal
    mode: str = ""        # MEAN_REV or BREAKOUT


class ADXBollingerRegimeSwitchStrategy:
    """
    ADX-based regime detection with dual Bollinger Band sub-strategies.

    Required methods:
    - __init__(self, params): Initialize parameters
    - generate_signals(self, data, symbol): Return List[Signal]
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        # ADX
        self.adx_period = self.params.get('adx_period', 14)
        self.adx_idle = self.params.get('adx_idle', 15)
        self.adx_breakout = self.params.get('adx_breakout', 25)
        # Bollinger Bands
        self.bb_period = self.params.get('bb_period', 20)
        self.bb_std = self.params.get('bb_std', 2.2)
        # RSI
        self.rsi_period = self.params.get('rsi_period', 14)
        self.rsi_os = self.params.get('rsi_oversold', 35)
        self.rsi_ob = self.params.get('rsi_overbought', 65)
        # ATR
        self.atr_period = self.params.get('atr_period', 14)
        # TP / SL
        self.mr_sl_atr = self.params.get('mr_sl_atr', 1.5)      # mean-rev SL
        self.bo_tp_atr = self.params.get('bo_tp_atr', 2.5)      # breakout TP
        self.bo_sl_atr = self.params.get('bo_sl_atr', 1.2)      # breakout SL
        # Cooldown
        self.cooldown = self.params.get('cooldown', 4)

    # ------------------------------------------------------------------
    # Signal generation (walk-forward safe: emits signals per-bar)
    # ------------------------------------------------------------------
    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        min_len = self.bb_period + self.adx_period + 20
        if len(data) < min_len:
            return []

        # Pre-compute indicator series
        adx = self._calculate_adx(data)
        rsi = self._calculate_rsi(data['close'], self.rsi_period)
        atr = self._calculate_atr(data)
        bb_mid = data['close'].rolling(self.bb_period).mean()
        bb_std = data['close'].rolling(self.bb_period).std()
        bb_upper = bb_mid + self.bb_std * bb_std
        bb_lower = bb_mid - self.bb_std * bb_std

        signals: List[Signal] = []
        last_signal_bar = -self.cooldown

        for i in range(min_len, len(data)):
            # Cooldown enforcement
            if i - last_signal_bar < self.cooldown:
                continue

            cur_adx = adx.iloc[i]
            cur_rsi = rsi.iloc[i]
            cur_atr = atr.iloc[i]
            cur_close = data['close'].iloc[i]
            cur_bb_upper = bb_upper.iloc[i]
            cur_bb_lower = bb_lower.iloc[i]
            cur_bb_mid = bb_mid.iloc[i]

            if any(pd.isna(v) for v in [cur_adx, cur_rsi, cur_atr,
                                         cur_bb_upper, cur_bb_lower, cur_bb_mid]):
                continue
            if cur_atr <= 0:
                continue

            # --- IDLE: ADX < 15 -> skip ---
            if cur_adx < self.adx_idle:
                continue

            # --- MEAN REVERSION: 15 <= ADX <= 25 ---
            if cur_adx <= self.adx_breakout:
                adx_above = cur_adx - self.adx_idle
                conf = min(0.60 + 0.02 * adx_above, 0.85)

                # BUY: close near lower BB + RSI oversold
                if cur_close <= cur_bb_lower and cur_rsi < self.rsi_os:
                    signals.append(Signal(
                        symbol=symbol,
                        direction="BUY",
                        confidence=round(conf, 2),
                        entry_price=cur_close,
                        take_profit=round(cur_bb_mid, 2),
                        stop_loss=round(cur_close - cur_atr * self.mr_sl_atr, 2),
                        reason=(f"MR_BUY ADX={cur_adx:.1f} RSI={cur_rsi:.1f} "
                                f"close<lowerBB"),
                        mode="MEAN_REV"
                    ))
                    last_signal_bar = i

                # SELL: close near upper BB + RSI overbought
                elif cur_close >= cur_bb_upper and cur_rsi > self.rsi_ob:
                    signals.append(Signal(
                        symbol=symbol,
                        direction="SELL",
                        confidence=round(conf, 2),
                        entry_price=cur_close,
                        take_profit=round(cur_bb_mid, 2),
                        stop_loss=round(cur_close + cur_atr * self.mr_sl_atr, 2),
                        reason=(f"MR_SELL ADX={cur_adx:.1f} RSI={cur_rsi:.1f} "
                                f"close>upperBB"),
                        mode="MEAN_REV"
                    ))
                    last_signal_bar = i

            # --- BREAKOUT: ADX > 25 + BB breach ---
            else:
                adx_above = cur_adx - self.adx_breakout
                conf = min(0.60 + 0.02 * adx_above, 0.85)

                # LONG momentum: close > upper BB
                if cur_close > cur_bb_upper:
                    signals.append(Signal(
                        symbol=symbol,
                        direction="BUY",
                        confidence=round(conf, 2),
                        entry_price=cur_close,
                        take_profit=round(cur_close + cur_atr * self.bo_tp_atr, 2),
                        stop_loss=round(cur_close - cur_atr * self.bo_sl_atr, 2),
                        reason=(f"BO_LONG ADX={cur_adx:.1f} close>upperBB "
                                f"ATR={cur_atr:.2f}"),
                        mode="BREAKOUT"
                    ))
                    last_signal_bar = i

                # SHORT momentum: close < lower BB
                elif cur_close < cur_bb_lower:
                    signals.append(Signal(
                        symbol=symbol,
                        direction="SELL",
                        confidence=round(conf, 2),
                        entry_price=cur_close,
                        take_profit=round(cur_close - cur_atr * self.bo_tp_atr, 2),
                        stop_loss=round(cur_close + cur_atr * self.bo_sl_atr, 2),
                        reason=(f"BO_SHORT ADX={cur_adx:.1f} close<lowerBB "
                                f"ATR={cur_atr:.2f}"),
                        mode="BREAKOUT"
                    ))
                    last_signal_bar = i

        return signals

    # ------------------------------------------------------------------
    # Indicator helpers
    # ------------------------------------------------------------------
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

    def _calculate_adx(self, data: pd.DataFrame) -> pd.Series:
        """Wilder-style ADX(14)."""
        high = data['high']
        low = data['low']
        close = data['close']
        n = self.adx_period

        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

        tr = pd.concat([
            high - low,
            abs(high - close.shift()),
            abs(low - close.shift())
        ], axis=1).max(axis=1)

        # Wilder smoothing (EMA with alpha = 1/n)
        atr_smooth = tr.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
        plus_di = 100 * plus_dm.ewm(alpha=1 / n, min_periods=n, adjust=False).mean() / atr_smooth
        minus_di = 100 * minus_dm.ewm(alpha=1 / n, min_periods=n, adjust=False).mean() / atr_smooth

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, 1e-10)
        adx = dx.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
        return adx


# ==============================================================================
# BINANCE DATA FETCHER (3+ endpoint failover per CLAUDE.md)
# ==============================================================================

def fetch_binance_klines(symbol: str, interval: str = "4h",
                         days: int = 180) -> pd.DataFrame:
    """Fetch klines with mandatory multi-endpoint failover."""
    endpoints = [
        "https://api.binance.com", "https://api1.binance.com",
        "https://api2.binance.com", "https://api3.binance.com",
    ]
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - days * 24 * 60 * 60 * 1000
    all_data = []
    cur = start_ms

    while cur < end_ms:
        success = False
        for base in endpoints:
            try:
                resp = requests.get(f"{base}/api/v3/klines", params={
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


# ==============================================================================
# WALK-FORWARD BACKTESTER
# ==============================================================================

def backtest_walk_forward(strategy, data, symbol, lookahead=12):
    """Track TP/SL hit within lookahead bars; record mode."""
    signals = strategy.generate_signals(data, symbol)
    results = []

    for sig in signals:
        entry_idx = (data['close'] - sig.entry_price).abs().idxmin()

        for j in range(entry_idx + 1, min(entry_idx + lookahead + 1, len(data))):
            bar_high = data['high'].iloc[j]
            bar_low = data['low'].iloc[j]

            if sig.direction == "SELL":
                if bar_low <= sig.take_profit:
                    pnl_pct = (sig.entry_price - sig.take_profit) / sig.entry_price * 100
                    results.append({"symbol": symbol, "direction": sig.direction,
                                    "pnl_pct": pnl_pct, "outcome": "TP",
                                    "mode": sig.mode})
                    break
                elif bar_high >= sig.stop_loss:
                    pnl_pct = -(sig.stop_loss - sig.entry_price) / sig.entry_price * 100
                    results.append({"symbol": symbol, "direction": sig.direction,
                                    "pnl_pct": pnl_pct, "outcome": "SL",
                                    "mode": sig.mode})
                    break
            else:  # BUY
                if bar_high >= sig.take_profit:
                    pnl_pct = (sig.take_profit - sig.entry_price) / sig.entry_price * 100
                    results.append({"symbol": symbol, "direction": sig.direction,
                                    "pnl_pct": pnl_pct, "outcome": "TP",
                                    "mode": sig.mode})
                    break
                elif bar_low <= sig.stop_loss:
                    pnl_pct = -(sig.entry_price - sig.stop_loss) / sig.entry_price * 100
                    results.append({"symbol": symbol, "direction": sig.direction,
                                    "pnl_pct": pnl_pct, "outcome": "SL",
                                    "mode": sig.mode})
                    break
        else:
            # Expired -- mark-to-market at lookahead bar
            exit_price = data['close'].iloc[min(entry_idx + lookahead, len(data) - 1)]
            if sig.direction == "SELL":
                pnl_pct = (sig.entry_price - exit_price) / sig.entry_price * 100
            else:
                pnl_pct = (exit_price - sig.entry_price) / sig.entry_price * 100
            results.append({"symbol": symbol, "direction": sig.direction,
                            "pnl_pct": pnl_pct, "outcome": "EXPIRED",
                            "mode": sig.mode})

    return results


def print_mode_breakdown(results, mode_label):
    """Print stats for a specific mode (MEAN_REV or BREAKOUT)."""
    subset = [r for r in results if r['mode'] == mode_label]
    if not subset:
        print(f"    {mode_label}: 0 trades")
        return
    wins = [r for r in subset if r['pnl_pct'] > 0]
    losses = [r for r in subset if r['pnl_pct'] <= 0]
    wr = len(wins) / len(subset) * 100
    avg_pnl = np.mean([r['pnl_pct'] for r in subset])
    gross_profit = sum(r['pnl_pct'] for r in wins) if wins else 0
    gross_loss = abs(sum(r['pnl_pct'] for r in losses)) if losses else 0.001
    pf = gross_profit / gross_loss if gross_loss > 0 else 999
    tp_ct = len([r for r in subset if r['outcome'] == 'TP'])
    sl_ct = len([r for r in subset if r['outcome'] == 'SL'])
    exp_ct = len([r for r in subset if r['outcome'] == 'EXPIRED'])
    print(f"    {mode_label}: {len(subset)} trades | WR={wr:.1f}% | "
          f"PF={pf:.2f} | avgPnL={avg_pnl:.2f}% | "
          f"TP={tp_ct} SL={sl_ct} EXP={exp_ct}")


# ==============================================================================
# MAIN BACKTEST
# ==============================================================================

if __name__ == "__main__":
    SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
    strategy = ADXBollingerRegimeSwitchStrategy()
    all_results = []

    print("=" * 74)
    print("BACKTEST: ADX-Bollinger Regime Switcher  (#3 ranked strategy)")
    print("  ADX(14), BB(20, 2.2), RSI(14), ATR(14)")
    print("  Modes: IDLE (ADX<15) | MEAN_REV (15-25) | BREAKOUT (>25)")
    print("  Cooldown: 4 bars | Lookahead: 12 bars | Data: 180d 4h")
    print("=" * 74)

    for sym in SYMBOLS:
        print(f"\nFetching {sym} 4h data (180 days)...")
        df = fetch_binance_klines(sym, "4h", 180)
        if df.empty:
            print(f"  SKIP {sym}: no data")
            continue
        print(f"  Got {len(df)} bars")

        results = backtest_walk_forward(strategy, df, sym)
        all_results.extend(results)

        if results:
            wins = [r for r in results if r['pnl_pct'] > 0]
            wr = len(wins) / len(results) * 100
            avg_pnl = np.mean([r['pnl_pct'] for r in results])
            print(f"  {sym}: {len(results)} trades, WR={wr:.1f}%, "
                  f"avg PnL={avg_pnl:.2f}%")
            print_mode_breakdown(results, "MEAN_REV")
            print_mode_breakdown(results, "BREAKOUT")
        else:
            print(f"  {sym}: 0 trades")

    # ------------------------------------------------------------------
    # Overall summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 74)
    print("OVERALL SUMMARY")
    print("=" * 74)
    if all_results:
        total = len(all_results)
        wins = [r for r in all_results if r['pnl_pct'] > 0]
        losses = [r for r in all_results if r['pnl_pct'] <= 0]
        wr = len(wins) / total * 100
        gross_profit = sum(r['pnl_pct'] for r in wins) if wins else 0
        gross_loss = abs(sum(r['pnl_pct'] for r in losses)) if losses else 0.001
        pf = gross_profit / gross_loss if gross_loss > 0 else 999
        avg_pnl = np.mean([r['pnl_pct'] for r in all_results])
        total_pnl = sum(r['pnl_pct'] for r in all_results)

        print(f"  Total Trades : {total}")
        print(f"  Win Rate     : {wr:.1f}%")
        print(f"  Profit Factor: {pf:.2f}")
        print(f"  Avg PnL/trade: {avg_pnl:.2f}%")
        print(f"  Total PnL    : {total_pnl:.2f}%")
        print(f"  Gross Profit : {gross_profit:.2f}%")
        print(f"  Gross Loss   : {gross_loss:.2f}%")

        print("\n  -- Mode Breakdown (all symbols) --")
        print_mode_breakdown(all_results, "MEAN_REV")
        print_mode_breakdown(all_results, "BREAKOUT")

        print("\n  -- Outcome Distribution --")
        for outcome in ["TP", "SL", "EXPIRED"]:
            ct = len([r for r in all_results if r['outcome'] == outcome])
            print(f"    {outcome}: {ct} ({ct / total * 100:.1f}%)")

        # Direction breakdown
        buys = [r for r in all_results if r['direction'] == 'BUY']
        sells = [r for r in all_results if r['direction'] == 'SELL']
        if buys:
            buy_wr = len([r for r in buys if r['pnl_pct'] > 0]) / len(buys) * 100
            print(f"\n  BUY  trades: {len(buys)}, WR={buy_wr:.1f}%")
        if sells:
            sell_wr = len([r for r in sells if r['pnl_pct'] > 0]) / len(sells) * 100
            print(f"  SELL trades: {len(sells)}, WR={sell_wr:.1f}%")

        verdict = "KEEP" if wr > 50 and pf > 1.2 and total >= 30 else "REVIEW"
        print(f"\n  Verdict: {verdict} (need WR>50%, PF>1.2, 30+ trades)")
    else:
        print("  No trades generated.")
