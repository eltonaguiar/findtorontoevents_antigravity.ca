"""
Protective Momentum Strategy
Sources:
  - Triton Quantitative Trading, Q1 2025 Quant League Winner (14.88% OOS quarterly return)
    Protective momentum with efficient frontier selection + integrated risk hedging
  - Lake Forest College, Q3 2025 Quant League Winner (Sharpe 3.93)
    Multi-indicator contrarian + momentum signals across crypto and equities

Framework:
  1. Multi-factor momentum: RSI trend + MACD histogram + Volume confirmation
  2. Contrarian overlay: Fade extreme readings (overbought/oversold)
  3. Protective hedging: Reduce position size when volatility spikes
  4. Regime filter: ATR-based volatility state detection

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

class ProtectiveMomentumStrategy:
    """
    Multi-factor protective momentum with contrarian fade at extremes.
    Triton Quant Trading (14.88% OOS) + Lake Forest College (Sharpe 3.93).
    """
    NAME = "protective_momentum"
    DESCRIPTION = "Multi-factor momentum (RSI+MACD+Volume) with contrarian fade at extremes and volatility-based position protection"
    ENTRY_RULES = (
        "LONG: RSI(14) > 50 AND rising, MACD histogram positive AND increasing, "
        "volume > 1.5x 20-bar avg, close > EMA(50); "
        "CONTRARIAN LONG: RSI < 25 AND MACD histogram turning up (extreme oversold fade); "
        "SHORT: inverse conditions"
    )
    EXIT_RULES = "TP = 2x ATR (momentum) or 1.5x ATR (contrarian); SL = 1.5x ATR; volatility > 2x avg reduces strength 50%"
    ACADEMIC_SOURCE = (
        "Triton Quantitative Trading, Q1 2025 Quant League (14.88% OOS return, protective momentum); "
        "Lake Forest College, Q3 2025 Quant League (Sharpe 3.93, multi-indicator contrarian+momentum); "
        "Gemini Deep Research Report on Championship-Winning Strategies (Mar 2026)"
    )
    EXPECTED_WR = "50-60%"
    EXPECTED_TRADES_PER_YEAR = "40-80 per symbol"

    def __init__(self, vol_protection_mult: float = 2.0, contrarian_rsi: float = 25.0,
                 vol_confirm_mult: float = 1.5):
        self.vol_protection_mult = vol_protection_mult  # ATR spike threshold for protection
        self.contrarian_rsi = contrarian_rsi            # RSI threshold for contrarian fade
        self.vol_confirm_mult = vol_confirm_mult        # Volume confirmation multiplier

    def generate_signals(self, df: pd.DataFrame, symbol: str = "UNKNOWN") -> list[dict]:
        """Generate protective momentum signals with contrarian overlay."""
        if len(df) < 100:
            return []

        df = df.copy()

        # --- RSI(14) ---
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1.0 / 14, min_periods=14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0 / 14, min_periods=14, adjust=False).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        # --- MACD (12, 26, 9) ---
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        macd_signal = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - macd_signal

        # --- EMA(50) for trend ---
        ema50 = df['close'].ewm(span=50, adjust=False).mean()

        # --- Volume moving average ---
        vol_ma = df['volume'].rolling(window=20).mean()

        # --- ATR(14) ---
        hl = df['high'] - df['low']
        hc = np.abs(df['high'] - df['close'].shift())
        lc = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        atr = true_range.ewm(alpha=1.0 / 14, min_periods=14, adjust=False).mean()

        # --- ATR moving average for volatility regime ---
        atr_ma = atr.rolling(window=50).mean()

        signals = []

        for i in range(60, len(df)):
            if any(pd.isna(x) for x in [rsi.iloc[i], macd_hist.iloc[i], ema50.iloc[i],
                                          vol_ma.iloc[i], atr.iloc[i], atr_ma.iloc[i]]):
                continue

            curr_close = float(df['close'].iloc[i])
            curr_rsi = float(rsi.iloc[i])
            prev_rsi = float(rsi.iloc[i - 1])
            curr_macd_hist = float(macd_hist.iloc[i])
            prev_macd_hist = float(macd_hist.iloc[i - 1])
            curr_ema50 = float(ema50.iloc[i])
            curr_vol = float(df['volume'].iloc[i])
            curr_vol_ma = float(vol_ma.iloc[i])
            curr_atr = float(atr.iloc[i])
            curr_atr_ma = float(atr_ma.iloc[i])

            # --- Volatility protection: reduce strength when ATR spikes ---
            vol_regime_elevated = curr_atr > self.vol_protection_mult * curr_atr_ma
            strength_modifier = 0.5 if vol_regime_elevated else 1.0

            # --- Volume confirmation ---
            volume_confirmed = curr_vol > self.vol_confirm_mult * curr_vol_ma if curr_vol_ma > 0 else False

            stop_dist = 1.5 * curr_atr

            # ============================================
            # MOMENTUM SIGNALS (trend-following)
            # ============================================

            # LONG MOMENTUM: RSI rising above 50, MACD hist positive & increasing, above EMA50, volume
            if (curr_rsi > 50 and curr_rsi > prev_rsi and
                curr_macd_hist > 0 and curr_macd_hist > prev_macd_hist and
                curr_close > curr_ema50 and volume_confirmed):

                entry_price = curr_close
                tp = entry_price + 2.0 * curr_atr
                sl = entry_price - stop_dist

                base_strength = int(min(100, 40 + (curr_rsi - 50) * 0.8
                                        + (curr_macd_hist / curr_atr) * 20))
                strength = max(1, int(base_strength * strength_modifier))

                protection_tag = " [VOL PROTECTED -50%]" if vol_regime_elevated else ""

                signals.append({
                    "symbol": symbol,
                    "side": "LONG",
                    "entry_price": float(entry_price),
                    "take_profit": float(tp),
                    "stop_loss": float(sl),
                    "strength": strength,
                    "reason": (
                        f"Protective Momentum LONG: RSI={curr_rsi:.1f} rising, "
                        f"MACD hist={curr_macd_hist:.4f} positive+increasing, "
                        f"Vol={curr_vol/curr_vol_ma:.1f}x avg, above EMA(50)"
                        f"{protection_tag}"
                    ),
                    "strategy": self.NAME,
                })

            # SHORT MOMENTUM: RSI falling below 50, MACD hist negative & decreasing, below EMA50
            elif (curr_rsi < 50 and curr_rsi < prev_rsi and
                  curr_macd_hist < 0 and curr_macd_hist < prev_macd_hist and
                  curr_close < curr_ema50 and volume_confirmed):

                entry_price = curr_close
                tp = entry_price - 2.0 * curr_atr
                sl = entry_price + stop_dist

                base_strength = int(min(100, 40 + (50 - curr_rsi) * 0.8
                                        + abs(curr_macd_hist / curr_atr) * 20))
                strength = max(1, int(base_strength * strength_modifier))

                protection_tag = " [VOL PROTECTED -50%]" if vol_regime_elevated else ""

                signals.append({
                    "symbol": symbol,
                    "side": "SHORT",
                    "entry_price": float(entry_price),
                    "take_profit": float(tp),
                    "stop_loss": float(sl),
                    "strength": strength,
                    "reason": (
                        f"Protective Momentum SHORT: RSI={curr_rsi:.1f} falling, "
                        f"MACD hist={curr_macd_hist:.4f} negative+decreasing, "
                        f"Vol={curr_vol/curr_vol_ma:.1f}x avg, below EMA(50)"
                        f"{protection_tag}"
                    ),
                    "strategy": self.NAME,
                })

            # ============================================
            # CONTRARIAN SIGNALS (extreme fades)
            # ============================================

            # CONTRARIAN LONG: Extreme oversold + MACD turning up
            elif (curr_rsi < self.contrarian_rsi and
                  curr_macd_hist > prev_macd_hist and  # Histogram turning up
                  volume_confirmed):

                entry_price = curr_close
                tp = entry_price + 1.5 * curr_atr  # Tighter TP for contrarian
                sl = entry_price - stop_dist

                base_strength = int(min(100, 50 + (self.contrarian_rsi - curr_rsi) * 2))
                strength = max(1, int(base_strength * strength_modifier))

                signals.append({
                    "symbol": symbol,
                    "side": "LONG",
                    "entry_price": float(entry_price),
                    "take_profit": float(tp),
                    "stop_loss": float(sl),
                    "strength": strength,
                    "reason": (
                        f"CONTRARIAN Fade: RSI={curr_rsi:.1f} extreme oversold (<{self.contrarian_rsi}), "
                        f"MACD hist turning up ({prev_macd_hist:.4f}→{curr_macd_hist:.4f}), "
                        f"Vol={curr_vol/curr_vol_ma:.1f}x avg"
                    ),
                    "strategy": self.NAME,
                })

            # CONTRARIAN SHORT: Extreme overbought + MACD turning down
            elif (curr_rsi > (100 - self.contrarian_rsi) and
                  curr_macd_hist < prev_macd_hist and
                  volume_confirmed):

                entry_price = curr_close
                tp = entry_price - 1.5 * curr_atr
                sl = entry_price + stop_dist

                base_strength = int(min(100, 50 + (curr_rsi - (100 - self.contrarian_rsi)) * 2))
                strength = max(1, int(base_strength * strength_modifier))

                signals.append({
                    "symbol": symbol,
                    "side": "SHORT",
                    "entry_price": float(entry_price),
                    "take_profit": float(tp),
                    "stop_loss": float(sl),
                    "strength": strength,
                    "reason": (
                        f"CONTRARIAN Fade: RSI={curr_rsi:.1f} extreme overbought (>{100 - self.contrarian_rsi}), "
                        f"MACD hist turning down ({prev_macd_hist:.4f}→{curr_macd_hist:.4f}), "
                        f"Vol={curr_vol/curr_vol_ma:.1f}x avg"
                    ),
                    "strategy": self.NAME,
                })

        return signals
