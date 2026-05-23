"""
CROSS-ASSET VARIANT 2: Keltner Compression-Expansion Generic
=============================================================
Origin: DOGE-specific Keltner is BANNED but generic
`crypto_keltner_compression_expansion_v1` hits 66.7% WR (STRONG).

This variant trades ALL liquid crypto, not just DOGE:
  BTC, ETH, SOL, BNB, XRP, AVAX, NEAR, SUI, ADA, DOT, ATOM, APT,
  LINK, UNI, AAVE, DOGE, SHIB, PEPE, WIF, BONK

Strategy:
  - Keltner Channel (EMA 20, ATR 14, mult 1.5)
  - Compression detection: channel width < 80-bar min * 1.05
  - Expansion breakout: price closes above/below band after compression
  - HMA trend filter (period 21) for direction confirmation
  - Volatility gate: skip when ATR z-score > 2.5 (extreme volatility)
  - TP: 1.0x ATR (wider than evolved 0.5x to suit generic crypto)
  - SL: 2.0x ATR (wide stops survive crypto wicks)

Status: CANDIDATE
Registered in battleground incubator STRATEGY_REGISTRY.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Universe: All liquid crypto (not just DOGE)
# ---------------------------------------------------------------------------
GENERIC_CRYPTO_UNIVERSE = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "AVAXUSDT", "NEARUSDT", "SUIUSDT", "ADAUSDT", "DOTUSDT",
    "ATOMUSDT", "APTUSDT", "LINKUSDT", "UNIUSDT", "AAVEUSDT",
    "DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "WIFUSDT", "BONKUSDT",
]

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
EMA_PERIOD = 20
ATR_PERIOD = 14
CHANNEL_MULT = 1.5
COMP_WINDOW = 80
TP_ATR_MULT = 1.0
SL_ATR_MULT = 2.0
MAX_HOLD = 24
HMA_PERIOD = 21
VOL_GATE_EXTREME = 2.5
TREND_STRENGTH_MIN = 0.001

STRATEGY_META = {
    "name": "keltner_compression_generic_v1",
    "status": "CANDIDATE",
    "origin": "cross_asset_mutation",
    "banned_parent": "keltner_doge_specific (BANNED)",
    "proven_sibling": "crypto_keltner_compression_expansion_v1 (66.7% WR STRONG)",
    "asset_class": "crypto",
    "universe": GENERIC_CRYPTO_UNIVERSE,
    "tp_atr_mult": TP_ATR_MULT,
    "sl_atr_mult": SL_ATR_MULT,
}


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _hma(series: pd.Series, period: int) -> pd.Series:
    """Hull Moving Average."""
    half = max(1, period // 2)
    sqrt_p = max(1, int(np.sqrt(period)))
    wma_half = series.ewm(span=half, adjust=False).mean()
    wma_full = series.ewm(span=period, adjust=False).mean()
    diff = 2 * wma_half - wma_full
    return diff.ewm(span=sqrt_p, adjust=False).mean()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class KeltnerCompressionGenericV1:
    """Keltner Compression-Expansion for ALL liquid crypto."""

    name = "keltner_compression_generic_v1"
    status = "CANDIDATE"

    def __init__(self):
        self.params = {
            "ema_period": EMA_PERIOD,
            "atr_period": ATR_PERIOD,
            "channel_mult": CHANNEL_MULT,
            "comp_window": COMP_WINDOW,
            "tp_atr_mult": TP_ATR_MULT,
            "sl_atr_mult": SL_ATR_MULT,
            "max_hold": MAX_HOLD,
            "hma_period": HMA_PERIOD,
            "vol_gate_extreme": VOL_GATE_EXTREME,
        }

    def generate_signals(self, data: dict, symbol: str) -> list[dict]:
        """Generate signals from OHLCV dict data.

        Args:
            data: dict with keys 'close', 'high', 'low', 'volume' (lists of floats)
            symbol: e.g. 'BTCUSDT'

        Returns:
            list of signal dicts compatible with battleground pick format
        """
        close = data.get("close", [])
        high = data.get("high", [])
        low = data.get("low", [])

        min_len = max(EMA_PERIOD, ATR_PERIOD, COMP_WINDOW, HMA_PERIOD) + 10
        if len(close) < min_len:
            return []

        close_s = pd.Series(close, dtype=float)
        high_s = pd.Series(high, dtype=float)
        low_s = pd.Series(low, dtype=float)

        # Keltner Channel
        mid = _ema(close_s, EMA_PERIOD)
        atr_val = _atr(high_s, low_s, close_s, ATR_PERIOD)
        upper = mid + CHANNEL_MULT * atr_val
        lower = mid - CHANNEL_MULT * atr_val

        # Channel width (normalized)
        width = (upper - lower) / mid
        width_min = width.rolling(window=COMP_WINDOW, min_periods=COMP_WINDOW).min()

        # HMA trend filter
        hma_val = _hma(close_s, HMA_PERIOD)

        # Current values
        price = float(close_s.iloc[-1])
        cur_atr = float(atr_val.iloc[-1])
        cur_upper = float(upper.iloc[-1])
        cur_lower = float(lower.iloc[-1])
        cur_width = float(width.iloc[-1])
        cur_width_min = float(width_min.iloc[-1]) if not pd.isna(width_min.iloc[-1]) else cur_width
        cur_hma = float(hma_val.iloc[-1]) if not pd.isna(hma_val.iloc[-1]) else price

        if cur_atr == 0 or pd.isna(cur_atr):
            return []

        # Volatility gate
        atr_mean = float(atr_val.rolling(COMP_WINDOW).mean().iloc[-1])
        atr_std = float(atr_val.rolling(COMP_WINDOW).std().iloc[-1])
        atr_zscore = (cur_atr - atr_mean) / atr_std if atr_std > 0 else 0.0
        if atr_zscore > VOL_GATE_EXTREME:
            return []

        # Compression detection
        is_compressed = cur_width <= cur_width_min * 1.05
        prev_width = float(width.iloc[-2]) if len(width) > 1 else cur_width
        prev_wmin = float(width_min.iloc[-2]) if (len(width_min) > 1 and not pd.isna(width_min.iloc[-2])) else prev_width
        was_compressed = prev_width <= prev_wmin * 1.05
        just_expanded = was_compressed and cur_width > cur_width_min * 1.10

        if not (is_compressed or just_expanded):
            return []

        # Trend direction from HMA
        prev_hma = float(hma_val.iloc[-2]) if len(hma_val) > 1 else cur_hma
        hma_dir = cur_hma - prev_hma

        # Trend strength check
        if abs(hma_dir) / price < TREND_STRENGTH_MIN:
            return []

        signals = []

        # LONG: price breaks above upper Keltner + HMA trending up
        if price > cur_upper and hma_dir > 0:
            tp = price + TP_ATR_MULT * cur_atr
            sl = price - SL_ATR_MULT * cur_atr
            signals.append({
                "strategy": self.name,
                "symbol": symbol,
                "direction": "LONG",
                "signal_type": "BUY",
                "entry_price": round(price, 8),
                "take_profit": round(tp, 8),
                "stop_loss": round(sl, 8),
                "confidence": min(0.80, 0.60 + abs(atr_zscore) * 0.05),
                "reason": f"Keltner compression breakout UP, width={cur_width:.4f}, ATR_z={atr_zscore:.2f}",
                "status": "CANDIDATE",
                "created_at": _now_iso(),
            })

        # SHORT: price breaks below lower Keltner + HMA trending down
        elif price < cur_lower and hma_dir < 0:
            tp = price - TP_ATR_MULT * cur_atr
            sl = price + SL_ATR_MULT * cur_atr
            signals.append({
                "strategy": self.name,
                "symbol": symbol,
                "direction": "SHORT",
                "signal_type": "SELL",
                "entry_price": round(price, 8),
                "take_profit": round(tp, 8),
                "stop_loss": round(sl, 8),
                "confidence": min(0.80, 0.60 + abs(atr_zscore) * 0.05),
                "reason": f"Keltner compression breakout DOWN, width={cur_width:.4f}, ATR_z={atr_zscore:.2f}",
                "status": "CANDIDATE",
                "created_at": _now_iso(),
            })

        return signals

    def backtest(self, data: dict, symbol: str) -> dict:
        """Simple vectorized backtest on OHLCV data."""
        close = data.get("close", [])
        high = data.get("high", [])
        low = data.get("low", [])

        min_len = max(EMA_PERIOD, ATR_PERIOD, COMP_WINDOW, HMA_PERIOD) + 10
        if len(close) < min_len:
            return {"trades": 0, "win_rate": 0, "symbol": symbol}

        close_s = pd.Series(close, dtype=float)
        high_s = pd.Series(high, dtype=float)
        low_s = pd.Series(low, dtype=float)

        mid = _ema(close_s, EMA_PERIOD)
        atr_val = _atr(high_s, low_s, close_s, ATR_PERIOD)
        upper = mid + CHANNEL_MULT * atr_val
        lower = mid - CHANNEL_MULT * atr_val
        width = (upper - lower) / mid
        width_min = width.rolling(window=COMP_WINDOW, min_periods=COMP_WINDOW).min()
        hma_val = _hma(close_s, HMA_PERIOD)

        trades = []
        pos = 0
        entry_price = 0.0
        entry_atr = 0.0
        bars_held = 0

        for i in range(min_len, len(close_s)):
            price = float(close_s.iloc[i])
            cur_atr = float(atr_val.iloc[i])
            cur_upper = float(upper.iloc[i])
            cur_lower = float(lower.iloc[i])
            cur_w = float(width.iloc[i])
            cur_wmin = float(width_min.iloc[i]) if not pd.isna(width_min.iloc[i]) else cur_w
            cur_hma = float(hma_val.iloc[i]) if not pd.isna(hma_val.iloc[i]) else price
            prev_hma = float(hma_val.iloc[i - 1]) if not pd.isna(hma_val.iloc[i - 1]) else cur_hma

            if pos != 0:
                bars_held += 1
                pnl_pct = (price / entry_price - 1) * pos * 100

                tp_hit = pnl_pct >= TP_ATR_MULT * entry_atr / entry_price * 100
                sl_hit = pnl_pct <= -SL_ATR_MULT * entry_atr / entry_price * 100
                time_stop = bars_held >= MAX_HOLD

                if tp_hit or sl_hit or time_stop:
                    reason = "TP" if tp_hit else ("SL" if sl_hit else "TIME")
                    trades.append({"pnl_pct": pnl_pct, "reason": reason})
                    pos = 0
                    bars_held = 0
                continue

            # Check for entry
            compressed = cur_w <= cur_wmin * 1.05
            prev_w = float(width.iloc[i - 1]) if i > 0 else cur_w
            prev_wmin = float(width_min.iloc[i - 1]) if (i > 0 and not pd.isna(width_min.iloc[i - 1])) else prev_w
            was_comp = prev_w <= prev_wmin * 1.05
            expanded = was_comp and cur_w > cur_wmin * 1.10

            if not (compressed or expanded):
                continue

            hma_dir = cur_hma - prev_hma
            if abs(hma_dir) / price < TREND_STRENGTH_MIN:
                continue

            if cur_atr == 0:
                continue

            # Volatility gate
            atr_mean = float(atr_val.iloc[max(0, i - COMP_WINDOW):i + 1].mean())
            atr_std = float(atr_val.iloc[max(0, i - COMP_WINDOW):i + 1].std())
            atr_z = (cur_atr - atr_mean) / atr_std if atr_std > 0 else 0
            if atr_z > VOL_GATE_EXTREME:
                continue

            if price > cur_upper and hma_dir > 0:
                pos = 1
                entry_price = price
                entry_atr = cur_atr
                bars_held = 0
            elif price < cur_lower and hma_dir < 0:
                pos = -1
                entry_price = price
                entry_atr = cur_atr
                bars_held = 0

        wins = [t for t in trades if t["pnl_pct"] > 0]
        win_rate = len(wins) / len(trades) * 100 if trades else 0
        avg_pnl = np.mean([t["pnl_pct"] for t in trades]) if trades else 0

        return {
            "symbol": symbol,
            "trades": len(trades),
            "win_rate": round(win_rate, 1),
            "avg_pnl_pct": round(float(avg_pnl), 2),
            "wins": len(wins),
            "losses": len(trades) - len(wins),
        }
