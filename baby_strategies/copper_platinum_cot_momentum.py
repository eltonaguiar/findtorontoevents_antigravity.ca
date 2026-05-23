"""
Copper & Platinum — COT-proxy Momentum Strategy
================================================
Target symbols: HG=F (copper), PL=F (platinum).
These are the ONLY two commodity futures currently whitelisted (energy/agro/other metals
are blacklisted).

Edge rationale
--------------
CFTC Commitment of Traders data has a week-long lag and is not directly feed-able via
yfinance, so we use a *price-based COT proxy*: commercials (smart money) are typically
*net short* in rising markets (they hedge forward production).  When the market is
*rising* yet the momentum signal shows price is NOT yet overbought — a zone where
commercials are likely beginning to cover shorts — we get a high-probability LONG setup.

Concrete entry conditions (all must be true):
  1. EMA(20) > EMA(50)  — short-term trend above medium-term trend (momentum)
  2. 45 ≤ RSI(14) ≤ 60  — confirmed momentum, NOT overbought (commercials still covering)
  3. Price > EMA(50)    — don't buy below trend spine

TP = 2.0× ATR(14)
SL = 1.0× ATR(14)

Symbol presets differ slightly because copper and platinum have different volatility
profiles and contract sizes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import pandas as pd


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _coerce(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise column names to lowercase; flatten MultiIndex if present."""
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = [str(c[0]).lower() for c in out.columns]
    else:
        out.columns = [str(c).lower() for c in out.columns]
    return out


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Wilder-smoothed Average True Range."""
    h = df["high"].astype(float)
    l = df["low"].astype(float)
    c = df["close"].astype(float)
    tr = pd.concat(
        [(h - l), (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder RSI via EWM (matches TradingView / most platforms)."""
    delta = close.diff()
    up = delta.clip(lower=0.0)
    dn = (-delta).clip(lower=0.0)
    ma_up = up.ewm(alpha=1.0 / period, adjust=False).mean()
    ma_dn = dn.ewm(alpha=1.0 / period, adjust=False).mean()
    rs = ma_up / ma_dn.replace(0.0, 1e-12)
    return 100.0 - (100.0 / (1.0 + rs))


def _ema(close: pd.Series, span: int) -> pd.Series:
    return close.ewm(span=span, adjust=False).mean()


# ---------------------------------------------------------------------------
# Signal dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Signal:
    symbol: str
    side: str                   # "LONG" | "SHORT"
    entry_price: float
    take_profit: float
    stop_loss: float
    strength: int               # 0-100
    reason: str
    strategy: str


# ---------------------------------------------------------------------------
# Per-symbol parameter presets
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CotMomentumParams:
    rsi_min: float          # Lower bound of momentum lane
    rsi_max: float          # Upper bound — avoid overbought entries
    ema_fast: int           # Fast EMA span (default 20)
    ema_slow: int           # Slow EMA span (default 50)
    tp_atr_mult: float      # Take-profit = entry + tp_atr_mult × ATR
    sl_atr_mult: float      # Stop-loss   = entry - sl_atr_mult × ATR
    max_hold_days: int
    min_bars: int           # Minimum bars needed before first signal


_BASE = CotMomentumParams(
    rsi_min=45.0,
    rsi_max=60.0,
    ema_fast=20,
    ema_slow=50,
    tp_atr_mult=2.0,
    sl_atr_mult=1.0,
    max_hold_days=15,
    min_bars=60,
)

SYMBOL_PRESETS: dict[str, CotMomentumParams] = {
    # Copper — higher volatility, tighter RSI window, slightly wider TP
    "HG=F": CotMomentumParams(
        rsi_min=45.0,
        rsi_max=60.0,
        ema_fast=20,
        ema_slow=50,
        tp_atr_mult=2.0,
        sl_atr_mult=1.0,
        max_hold_days=15,
        min_bars=60,
    ),
    # Platinum — lower liquidity, give RSI a bit more room on the upside
    "PL=F": CotMomentumParams(
        rsi_min=45.0,
        rsi_max=62.0,
        ema_fast=20,
        ema_slow=50,
        tp_atr_mult=2.0,
        sl_atr_mult=1.0,
        max_hold_days=15,
        min_bars=60,
    ),
}

# Whitelisted symbols — only these two are allowed through production gates
ALLOWED_SYMBOLS: frozenset[str] = frozenset({"HG=F", "PL=F"})


# ---------------------------------------------------------------------------
# Strategy class
# ---------------------------------------------------------------------------

class CopperPlatinumCotMomentumStrategy:
    """
    COT-proxy momentum strategy for HG=F (copper) and PL=F (platinum).

    Usage::

        from baby_strategies.copper_platinum_cot_momentum import (
            CopperPlatinumCotMomentumStrategy,
        )
        strat = CopperPlatinumCotMomentumStrategy()
        signals = strat.generate_signals(df, symbol="HG=F")
    """

    NAME = "copper_platinum_cot_momentum"

    def __init__(
        self,
        rsi_min: float | None = None,
        rsi_max: float | None = None,
        ema_fast: int | None = None,
        ema_slow: int | None = None,
        tp_atr_mult: float | None = None,
        sl_atr_mult: float | None = None,
        max_hold_days: int | None = None,
        symbol_presets: Mapping[str, CotMomentumParams] | None = None,
        force_global_params: bool = False,
    ) -> None:
        self._global = CotMomentumParams(
            rsi_min=float(rsi_min if rsi_min is not None else _BASE.rsi_min),
            rsi_max=float(rsi_max if rsi_max is not None else _BASE.rsi_max),
            ema_fast=int(ema_fast if ema_fast is not None else _BASE.ema_fast),
            ema_slow=int(ema_slow if ema_slow is not None else _BASE.ema_slow),
            tp_atr_mult=float(tp_atr_mult if tp_atr_mult is not None else _BASE.tp_atr_mult),
            sl_atr_mult=float(sl_atr_mult if sl_atr_mult is not None else _BASE.sl_atr_mult),
            max_hold_days=int(max_hold_days if max_hold_days is not None else _BASE.max_hold_days),
            min_bars=_BASE.min_bars,
        )
        self._presets: Mapping[str, CotMomentumParams] = (
            symbol_presets if symbol_presets is not None else SYMBOL_PRESETS
        )
        self._force_global = bool(force_global_params)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _params_for(self, symbol: str) -> CotMomentumParams:
        if self._force_global:
            return self._global
        key = symbol.upper().strip()
        return self._presets.get(key, self._global)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_signals(self, df: pd.DataFrame, symbol: str = "HG=F") -> list[dict]:
        """
        Generate signals for a single symbol.

        Parameters
        ----------
        df:
            OHLCV DataFrame with daily bars.  Index should be DatetimeIndex.
            Columns must include open / high / low / close / volume
            (case-insensitive; MultiIndex is handled).
        symbol:
            Ticker string.  Must be in ALLOWED_SYMBOLS or no signals are returned.

        Returns
        -------
        List of signal dicts, each containing:
            symbol, side, entry_price, take_profit, stop_loss, strength,
            reason, strategy, max_hold_days, timestamp, bar_index
        """
        sym_upper = symbol.upper().strip()

        # Whitelist gate — only copper and platinum are allowed
        if sym_upper not in ALLOWED_SYMBOLS:
            return []

        df = _coerce(df)
        required_cols = {"open", "high", "low", "close", "volume"}
        p = self._params_for(sym_upper)
        if not required_cols.issubset(df.columns) or len(df) < p.min_bars:
            return []

        close = df["close"].astype(float)
        ema_fast = _ema(close, p.ema_fast)
        ema_slow = _ema(close, p.ema_slow)
        rsi14 = _rsi(close, 14)
        atr14 = _atr(df, 14)

        out: list[dict] = []

        for i in range(p.min_bars, len(df)):
            if pd.isna(atr14.iloc[i]) or pd.isna(rsi14.iloc[i]):
                continue

            c = float(close.iloc[i])
            a = float(atr14.iloc[i])
            if a <= 0.0:
                continue

            ef = float(ema_fast.iloc[i])
            es = float(ema_slow.iloc[i])
            rsi = float(rsi14.iloc[i])

            # --- Entry conditions ---
            # 1. EMA(20) > EMA(50): short-term momentum above medium-term spine
            ema_cross = ef > es
            # 2. Price above EMA(50): don't buy below the trend anchor
            above_spine = c > es
            # 3. RSI in the momentum lane (not overbought, not stalled)
            rsi_ok = p.rsi_min <= rsi <= p.rsi_max

            if ema_cross and above_spine and rsi_ok:
                tp = c + a * p.tp_atr_mult
                sl = c - a * p.sl_atr_mult

                # Strength heuristic: higher score when RSI is centred in the lane
                # and EMA spread is wide (trend conviction)
                rsi_centre = 1.0 - abs(rsi - 52.5) / 15.0   # peaks at RSI=52.5
                ema_spread_pct = (ef - es) / es if es > 0 else 0.0
                spread_score = min(ema_spread_pct / 0.02, 1.0)  # caps at 2% spread
                strength = int(55 + 20 * rsi_centre * 0.5 + 20 * spread_score * 0.5)
                strength = max(55, min(85, strength))

                out.append(
                    {
                        "symbol": sym_upper,
                        "side": "LONG",
                        "entry_price": round(c, 6),
                        "take_profit": round(tp, 6),
                        "stop_loss": round(sl, 6),
                        "strength": strength,
                        "reason": (
                            f"COT-proxy momentum: EMA{p.ema_fast}>{p.ema_slow}, "
                            f"RSI={rsi:.1f} in [{p.rsi_min},{p.rsi_max}], "
                            f"ATR={a:.4f} [{sym_upper}]"
                        ),
                        "strategy": self.NAME,
                        "max_hold_days": p.max_hold_days,
                        "timestamp": df.index[i],
                        "bar_index": i,
                    }
                )

        return out
