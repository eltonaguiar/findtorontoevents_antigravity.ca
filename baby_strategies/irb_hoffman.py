"""
Inventory Retracement Bar (IRB) Strategy — Rob Hoffman Framework
Source: Rob Hoffman, 23-time International Trading Competition Winner
Backtested: 62% WR on BTC 15-min, 206% net return (1:1.5 R:R, 2% risk)
Pine reference: UCS_Rob_Hoffman_Inventory_Retracement_Bar by UCSgears

Framework:
  1. Trend filter: EMA(5) > EMA(20) > SMA(50) ribbon for longs (inverse for shorts)
  2. IRB detection: Wick >= 45% of candle range (institutional retracement footprint)
  3. Breakout entry: Price breaks IRB extreme within 20 bars (temporal decay)
  4. Trailing stops: Breakeven at 1:1, 50% lock at 1.5:1, 90% lock at structure

Google Gemini Deep Research Report (Mar 2026):
  "Advanced Quantitative Framework for Systematic Cryptocurrency Trading:
   Evaluating Championship-Winning Algorithmic Strategies"
"""

import pandas as pd
import numpy as np


SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]

class IRBHoffmanStrategy:
    """
    Inventory Retracement Bar — institutional liquidity exhaustion + trend continuation.
    Rob Hoffman, 23x international trading champion. 62% WR BTC 15m backtested.
    """
    NAME = "irb_hoffman"
    DESCRIPTION = "Hoffman IRB: 45% wick threshold detects institutional retracement, enters on breakout with EMA ribbon trend filter"
    ENTRY_RULES = (
        "LONG: EMA(5) > EMA(20) > SMA(50) ribbon AND IRB detected (wick >= 45% range, "
        "open+close in lower 55%) AND price breaks above IRB high within 20 bars; "
        "SHORT: EMA(5) < EMA(20) < SMA(50) AND IRB (lower wick >= 45%) AND price breaks below IRB low within 20 bars"
    )
    EXIT_RULES = "SL = 1 tick below IRB low (long) / above IRB high (short); TP = 1.5x risk; trailing: BE at 1:1, 50% lock at 1.5:1"
    ACADEMIC_SOURCE = (
        "Rob Hoffman, 23x Intl Trading Champion (62% WR BTC 15m, 206% return); "
        "Pine: UCS_RH_IRB by UCSgears; "
        "Gemini Deep Research Report on Championship-Winning Strategies (Mar 2026)"
    )
    EXPECTED_WR = "55-65%"
    EXPECTED_TRADES_PER_YEAR = "30-60 per symbol"

    def __init__(self, wick_pct: float = 0.45, temporal_decay: int = 20, rr_ratio: float = 1.5):
        self.wick_pct = wick_pct          # Minimum wick as fraction of range (0.45 = 45%)
        self.temporal_decay = temporal_decay  # Max bars to wait for breakout entry
        self.rr_ratio = rr_ratio          # Risk:Reward ratio for TP

    def generate_signals(self, df: pd.DataFrame, symbol: str = "UNKNOWN") -> list[dict]:
        """Generate IRB Hoffman signals with trend filter + temporal decay entry."""
        if len(df) < 55:
            return []

        df = df.copy()

        # --- Trend Filter: EMA(5), EMA(20), SMA(50) ribbon ---
        ema5 = df['close'].ewm(span=5, adjust=False).mean()
        ema20 = df['close'].ewm(span=20, adjust=False).mean()
        sma50 = df['close'].rolling(window=50).mean()

        # --- ATR(14) for minimum range filter ---
        hl = df['high'] - df['low']
        hc = np.abs(df['high'] - df['close'].shift())
        lc = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        atr = true_range.ewm(alpha=1.0 / 14, min_periods=14, adjust=False).mean()

        signals = []
        pending_setups = []  # Track pending IRB setups awaiting breakout

        for i in range(50, len(df)):
            if pd.isna(sma50.iloc[i]) or pd.isna(atr.iloc[i]):
                continue
        
            curr_high = float(df['high'].iloc[i])
            curr_low = float(df['low'].iloc[i])
            curr_open = float(df['open'].iloc[i])
            curr_close = float(df['close'].iloc[i])
            curr_ema5 = float(ema5.iloc[i])
            curr_ema20 = float(ema20.iloc[i])
            curr_sma50 = float(sma50.iloc[i])
            curr_atr = float(atr.iloc[i])
            curr_vol = float(v[i])
        
            candle_range = curr_high - curr_low
        
            # Skip tiny candles (less than 0.1x ATR — noise)
            if candle_range < 0.1 * curr_atr:
                # Still check pending setups for breakout
                self._check_breakouts(i, df, pending_setups, signals, symbol, atr)
                continue
        
            # --- Volume filter (require ≥1.2× 20‑period average) ---
            if i >= 20:
                avg_vol = np.mean(v[i-20:i])
                if curr_vol < 1.2 * avg_vol:
                    # Low volume – skip IRB detection for this bar
                    self._check_breakouts(i, df, pending_setups, signals, symbol, atr)
                    continue
        
            # --- Regime filter (ATR percentile & HMA slope) ---
            if i >= 100:
                # ATR percentile rank over last 100 candles
                atr_window = atr[i-100:i]
                atr_rank = np.sum(atr_window <= curr_atr) / len(atr_window)
                # Require moderate‑to‑high volatility
                if atr_rank < 0.3:
                    self._check_breakouts(i, df, pending_setups, signals, symbol, atr)
                    continue
                # HMA slope (using EMA(21) as proxy)
                hma = _ema(c, 21)
                if i >= 21:
                    hma_slope = np.sign(hma[i] - hma[i-1])
                    # For LONG require positive slope, for SHORT require negative slope
                    if (bullish_ribbon and hma_slope <= 0) or (bearish_ribbon and hma_slope >= 0):
                        self._check_breakouts(i, df, pending_setups, signals, symbol, atr)
                        continue
        
            # --- Determine trend regime ---
            bullish_ribbon = curr_ema5 > curr_ema20 > curr_sma50
            bearish_ribbon = curr_ema5 < curr_ema20 < curr_sma50
        
            # --- IRB Detection (from Pine: UCS_RH_IRB) ---
            body = abs(curr_close - curr_open)
            top_of_body = max(curr_open, curr_close)
            bottom_of_body = min(curr_open, curr_close)
        
            # Body must be less than wick_pct of range (large wick)
            body_small = body < self.wick_pct * candle_range
        
            if body_small:
                # LONG setup: open & close in lower portion, long upper wick
                # Pine: high > y and close < y and open < y where y = high - 0.45 * range
                y_threshold = curr_high - self.wick_pct * candle_range
                irb_long = (curr_close < y_threshold and curr_open < y_threshold
                            and bullish_ribbon)
        
                # SHORT setup: open & close in upper portion, long lower wick
                # Pine: low < x and close > x and open > x where x = low + 0.45 * range
                x_threshold = curr_low + self.wick_pct * candle_range
                irb_short = (curr_close > x_threshold and curr_open > x_threshold
                             and bearish_ribbon)
        
                if irb_long:
                    pending_setups.append({
                        'side': 'LONG',
                        'bar_index': i,
                        'irb_high': curr_high,
                        'irb_low': curr_low,
                        'wick_pct_actual': (curr_high - top_of_body) / candle_range,
                    })
        
                if irb_short:
                    pending_setups.append({
                        'side': 'SHORT',
                        'bar_index': i,
                        'irb_high': curr_high,
                        'irb_low': curr_low,
                        'wick_pct_actual': (bottom_of_body - curr_low) / candle_range,
                    })
        
            # --- Check pending setups for breakout entry ---
            self._check_breakouts(i, df, pending_setups, signals, symbol, atr)
        
        return signals

    def _check_breakouts(self, current_bar: int, df: pd.DataFrame,
                         pending_setups: list, signals: list, symbol: str,
                         atr: pd.Series):
        """Check if any pending IRB setups have triggered breakout entry."""
        expired = []

        for setup in pending_setups:
            bars_elapsed = current_bar - setup['bar_index']

            # Temporal decay: discard after N bars
            if bars_elapsed > self.temporal_decay:
                expired.append(setup)
                continue

            # Don't trigger on the setup bar itself
            if bars_elapsed < 1:
                continue

            curr_high = float(df['high'].iloc[current_bar])
            curr_low = float(df['low'].iloc[current_bar])
            curr_close = float(df['close'].iloc[current_bar])
            curr_atr = float(atr.iloc[current_bar])

            if setup['side'] == 'LONG':
                # Entry: price breaks above IRB high
                if curr_high > setup['irb_high']:
                    entry_price = setup['irb_high']  # Enter at IRB high (limit)
                    stop_loss = setup['irb_low']      # Stop below IRB low
                    risk = entry_price - stop_loss

                    if risk <= 0 or risk < 0.1 * curr_atr:
                        expired.append(setup)
                        continue

                    take_profit = entry_price + self.rr_ratio * risk

                    strength = int(min(100, 50 + setup['wick_pct_actual'] * 80
                                       + min(bars_elapsed, 5) * 2))

                    signals.append({
                        "symbol": symbol,
                        "side": "LONG",
                        "entry_price": float(entry_price),
                        "take_profit": float(take_profit),
                        "stop_loss": float(stop_loss),
                        "strength": strength,
                        "reason": (
                            f"IRB Hoffman: Bullish EMA ribbon, "
                            f"wick={setup['wick_pct_actual']:.0%} of range, "
                            f"breakout above IRB high={entry_price:.4f} "
                            f"after {bars_elapsed} bars, "
                            f"R:R=1:{self.rr_ratio}"
                        ),
                        "strategy": self.NAME,
                    })
                    expired.append(setup)

            elif setup['side'] == 'SHORT':
                # Entry: price breaks below IRB low
                if curr_low < setup['irb_low']:
                    entry_price = setup['irb_low']    # Enter at IRB low
                    stop_loss = setup['irb_high']      # Stop above IRB high
                    risk = stop_loss - entry_price

                    if risk <= 0 or risk < 0.1 * curr_atr:
                        expired.append(setup)
                        continue

                    take_profit = entry_price - self.rr_ratio * risk

                    strength = int(min(100, 50 + setup['wick_pct_actual'] * 80
                                       + min(bars_elapsed, 5) * 2))

                    signals.append({
                        "symbol": symbol,
                        "side": "SHORT",
                        "entry_price": float(entry_price),
                        "take_profit": float(take_profit),
                        "stop_loss": float(stop_loss),
                        "strength": strength,
                        "reason": (
                            f"IRB Hoffman: Bearish EMA ribbon, "
                            f"wick={setup['wick_pct_actual']:.0%} of range, "
                            f"breakout below IRB low={entry_price:.4f} "
                            f"after {bars_elapsed} bars, "
                            f"R:R=1:{self.rr_ratio}"
                        ),
                        "strategy": self.NAME,
                    })
                    expired.append(setup)

        for s in expired:
            if s in pending_setups:
                pending_setups.remove(s)
