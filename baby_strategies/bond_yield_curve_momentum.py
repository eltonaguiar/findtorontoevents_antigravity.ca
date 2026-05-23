"""
Bond Yield-Curve Duration-Momentum Strategy
============================================
Target symbols: TLT, IEF, SHY, BND (bond ETFs).

Goal: grow BOND sample size from n=11 → n≥100 (T2 charter floor) while maintaining
T2-grade profit factor (≥1.5) and win rate (≥50%).

Edge rationale
--------------
Bond ETF prices move inversely to yields.  Three regime signals drive this strategy:

  A. BULL regime (TLT LONG):
       TLT SMA(50) > SMA(200)  — bond prices in long-term uptrend (yields falling)
       AND RSI(14) in [45, 65] — not overbought, momentum confirmed

  B. BEAR / DEFENSIVE regime (SHY LONG):
       TLT SMA(50) < SMA(200)  — bond prices below long-term trend (yields rising)
       AND TLT RSI(14) < 55    — downward momentum not yet exhausted

  C. YIELD CURVE STEEPENING overlay (IEF LONG):
       20-day rate-of-change of (TLT / SHY ratio) > 0  — curve steepening proxy
       Added on top of A or B when the spread is expanding.

Each ETF uses its own OHLCV DataFrame.  The `generate_signals` method accepts a
`data_dict` mapping ticker → DataFrame, to allow cross-asset ratio computation.

TP = 1.5× ATR(14)
SL = 0.8× ATR(14)

Minimum dataset: 210 bars (≥ SMA200 warm-up + 10 bars of ratio history).
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
    """Simple (non-Wilder) rolling ATR — identical to commodity_trend_pullback_rsi."""
    h = df["high"].astype(float)
    l = df["low"].astype(float)
    c = df["close"].astype(float)
    tr = pd.concat(
        [(h - l), (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder RSI via EWM."""
    delta = close.diff()
    up = delta.clip(lower=0.0)
    dn = (-delta).clip(lower=0.0)
    ma_up = up.ewm(alpha=1.0 / period, adjust=False).mean()
    ma_dn = dn.ewm(alpha=1.0 / period, adjust=False).mean()
    rs = ma_up / ma_dn.replace(0.0, 1e-12)
    return 100.0 - (100.0 / (1.0 + rs))


def _sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(period, min_periods=period).mean()


# ---------------------------------------------------------------------------
# Signal dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Signal:
    symbol: str
    side: str                   # "LONG" only in this strategy (no shorting bonds)
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
class BondMomentumParams:
    sma_fast: int           # Fast SMA for regime (default 50)
    sma_slow: int           # Slow SMA for regime (default 200)
    rsi_bull_min: float     # RSI lower bound in bull regime
    rsi_bull_max: float     # RSI upper bound in bull regime
    rsi_bear_max: float     # RSI upper bound in bear/defensive regime
    tp_atr_mult: float
    sl_atr_mult: float
    max_hold_days: int
    curve_roc_period: int   # Look-back for TLT/SHY ratio ROC (steepening proxy)
    min_bars: int


_BASE = BondMomentumParams(
    sma_fast=50,
    sma_slow=200,
    rsi_bull_min=45.0,
    rsi_bull_max=65.0,
    rsi_bear_max=55.0,
    tp_atr_mult=1.5,
    sl_atr_mult=0.8,
    max_hold_days=20,
    curve_roc_period=20,
    min_bars=210,
)

SYMBOL_PRESETS: dict[str, BondMomentumParams] = {
    # TLT — long-duration; use exactly the bull-regime gate
    "TLT": BondMomentumParams(
        sma_fast=50,
        sma_slow=200,
        rsi_bull_min=45.0,
        rsi_bull_max=65.0,
        rsi_bear_max=55.0,
        tp_atr_mult=1.5,
        sl_atr_mult=0.8,
        max_hold_days=20,
        curve_roc_period=20,
        min_bars=210,
    ),
    # IEF — intermediate duration; slightly looser RSI window
    "IEF": BondMomentumParams(
        sma_fast=50,
        sma_slow=200,
        rsi_bull_min=43.0,
        rsi_bull_max=67.0,
        rsi_bear_max=57.0,
        tp_atr_mult=1.5,
        sl_atr_mult=0.8,
        max_hold_days=20,
        curve_roc_period=20,
        min_bars=210,
    ),
    # SHY — short-duration defensive; wider ATR multiples for narrow price range
    "SHY": BondMomentumParams(
        sma_fast=50,
        sma_slow=200,
        rsi_bull_min=45.0,
        rsi_bull_max=65.0,
        rsi_bear_max=55.0,
        tp_atr_mult=1.8,
        sl_atr_mult=0.9,
        max_hold_days=20,
        curve_roc_period=20,
        min_bars=210,
    ),
    # BND — aggregate bond market; treat like IEF
    "BND": BondMomentumParams(
        sma_fast=50,
        sma_slow=200,
        rsi_bull_min=43.0,
        rsi_bull_max=67.0,
        rsi_bear_max=57.0,
        tp_atr_mult=1.5,
        sl_atr_mult=0.8,
        max_hold_days=20,
        curve_roc_period=20,
        min_bars=210,
    ),
}

# Symbols this strategy is allowed to trade
ALLOWED_SYMBOLS: frozenset[str] = frozenset({"TLT", "IEF", "SHY", "BND"})


# ---------------------------------------------------------------------------
# Strategy class
# ---------------------------------------------------------------------------

class BondYieldCurveMomentumStrategy:
    """
    Duration-momentum strategy for bond ETFs (TLT, IEF, SHY, BND).

    Two call patterns are supported:

    1. Single-symbol (for back-compat with the baby-strategy runner)::

        strat = BondYieldCurveMomentumStrategy()
        signals = strat.generate_signals(df_tlt, symbol="TLT")

    2. Multi-asset (preferred — enables the curve-steepening IEF overlay)::

        strat = BondYieldCurveMomentumStrategy()
        signals = strat.generate_signals(
            {"TLT": df_tlt, "SHY": df_shy, "IEF": df_ief}
        )
    """

    NAME = "bond_yield_curve_momentum"

    def __init__(
        self,
        sma_fast: int | None = None,
        sma_slow: int | None = None,
        rsi_bull_min: float | None = None,
        rsi_bull_max: float | None = None,
        rsi_bear_max: float | None = None,
        tp_atr_mult: float | None = None,
        sl_atr_mult: float | None = None,
        max_hold_days: int | None = None,
        curve_roc_period: int | None = None,
        symbol_presets: Mapping[str, BondMomentumParams] | None = None,
        force_global_params: bool = False,
    ) -> None:
        self._global = BondMomentumParams(
            sma_fast=int(sma_fast if sma_fast is not None else _BASE.sma_fast),
            sma_slow=int(sma_slow if sma_slow is not None else _BASE.sma_slow),
            rsi_bull_min=float(rsi_bull_min if rsi_bull_min is not None else _BASE.rsi_bull_min),
            rsi_bull_max=float(rsi_bull_max if rsi_bull_max is not None else _BASE.rsi_bull_max),
            rsi_bear_max=float(rsi_bear_max if rsi_bear_max is not None else _BASE.rsi_bear_max),
            tp_atr_mult=float(tp_atr_mult if tp_atr_mult is not None else _BASE.tp_atr_mult),
            sl_atr_mult=float(sl_atr_mult if sl_atr_mult is not None else _BASE.sl_atr_mult),
            max_hold_days=int(max_hold_days if max_hold_days is not None else _BASE.max_hold_days),
            curve_roc_period=int(curve_roc_period if curve_roc_period is not None else _BASE.curve_roc_period),
            min_bars=_BASE.min_bars,
        )
        self._presets: Mapping[str, BondMomentumParams] = (
            symbol_presets if symbol_presets is not None else SYMBOL_PRESETS
        )
        self._force_global = bool(force_global_params)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _params_for(self, symbol: str) -> BondMomentumParams:
        if self._force_global:
            return self._global
        return self._presets.get(symbol.upper(), self._global)

    def _curve_steepening(
        self, tlt_close: pd.Series, shy_close: pd.Series, period: int
    ) -> pd.Series:
        """
        Compute a boolean Series indicating yield-curve steepening.

        Proxy: 20-day rate-of-change of (TLT / SHY price ratio).
        A rising ratio means TLT is outperforming SHY → long end yields falling
        faster than short end → curve is steepening (or flattening inversion is
        unwinding).  We define steepening as ROC > 0 over `period` days.
        """
        # Align on common index
        ratio = tlt_close / shy_close.reindex(tlt_close.index).ffill()
        roc = ratio.pct_change(periods=period)
        return roc > 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_signals(
        self,
        data: pd.DataFrame | dict[str, pd.DataFrame],
        symbol: str | None = None,
    ) -> list[dict]:
        """
        Generate bond regime signals.

        Parameters
        ----------
        data:
            Either a single OHLCV DataFrame (pass `symbol` too), or a dict mapping
            ticker strings → OHLCV DataFrames.  Multi-asset dict is preferred because
            it enables the IEF curve-steepening overlay.
        symbol:
            Required only when `data` is a DataFrame (single-symbol path).

        Returns
        -------
        List of signal dicts with keys:
            symbol, side, entry_price, take_profit, stop_loss, strength,
            reason, strategy, max_hold_days, timestamp, bar_index
        """
        if isinstance(data, dict):
            return self._generate_multi(data)
        # Single-symbol fallback
        if symbol is None:
            raise ValueError("`symbol` is required when `data` is a DataFrame")
        return self._generate_single(_coerce(data), symbol.upper())

    # ------------------------------------------------------------------
    # Single-symbol path
    # ------------------------------------------------------------------

    def _generate_single(self, df: pd.DataFrame, symbol: str) -> list[dict]:
        if symbol not in ALLOWED_SYMBOLS:
            return []

        p = self._params_for(symbol)
        required = {"open", "high", "low", "close", "volume"}
        if not required.issubset(df.columns) or len(df) < p.min_bars:
            return []

        close = df["close"].astype(float)
        sma50 = _sma(close, p.sma_fast)
        sma200 = _sma(close, p.sma_slow)
        rsi14 = _rsi(close, 14)
        atr14 = _atr(df, 14)

        out: list[dict] = []

        for i in range(p.min_bars, len(df)):
            if pd.isna(atr14.iloc[i]) or pd.isna(rsi14.iloc[i]):
                continue
            if pd.isna(sma50.iloc[i]) or pd.isna(sma200.iloc[i]):
                continue

            c = float(close.iloc[i])
            a = float(atr14.iloc[i])
            if a <= 0.0:
                continue

            s50 = float(sma50.iloc[i])
            s200 = float(sma200.iloc[i])
            rsi = float(rsi14.iloc[i])
            bull_regime = s50 > s200
            bear_regime = not bull_regime

            signal_sym: str | None = None
            reason_extra: str = ""
            strength: int = 60

            if symbol == "TLT":
                if bull_regime and p.rsi_bull_min <= rsi <= p.rsi_bull_max:
                    signal_sym = "TLT"
                    reason_extra = f"BULL: SMA50>{p.sma_slow}SMA, RSI={rsi:.1f}"
                    strength = 68
            elif symbol == "SHY":
                if bear_regime and rsi < p.rsi_bear_max:
                    signal_sym = "SHY"
                    reason_extra = f"DEFENSIVE: SMA50<{p.sma_slow}SMA, RSI={rsi:.1f}"
                    strength = 62
            elif symbol in ("IEF", "BND"):
                # Without cross-asset ratio we just use the bull regime gate
                if bull_regime and p.rsi_bull_min <= rsi <= p.rsi_bull_max:
                    signal_sym = symbol
                    reason_extra = f"BULL: SMA50>{p.sma_slow}SMA, RSI={rsi:.1f}"
                    strength = 63

            if signal_sym is not None:
                tp = c + a * p.tp_atr_mult
                sl = c - a * p.sl_atr_mult
                out.append(
                    {
                        "symbol": signal_sym,
                        "side": "LONG",
                        "entry_price": round(c, 6),
                        "take_profit": round(tp, 6),
                        "stop_loss": round(sl, 6),
                        "strength": strength,
                        "reason": (
                            f"Bond duration-momentum ({reason_extra}) "
                            f"ATR={a:.4f} [{signal_sym}]"
                        ),
                        "strategy": self.NAME,
                        "max_hold_days": p.max_hold_days,
                        "timestamp": df.index[i],
                        "bar_index": i,
                    }
                )

        return out

    # ------------------------------------------------------------------
    # Multi-asset path (preferred — enables cross-asset curve overlay)
    # ------------------------------------------------------------------

    def _generate_multi(self, data_dict: dict[str, pd.DataFrame]) -> list[dict]:
        """
        Process TLT, SHY, IEF (and optionally BND) together.

        Logic per bar:
          1. Compute TLT regime (bull / bear) from TLT SMA50 vs SMA200.
          2. Bull regime  → TLT LONG if RSI in [rsi_bull_min, rsi_bull_max].
          3. Bear regime  → SHY LONG if TLT RSI < rsi_bear_max.
          4. Curve steepening (TLT/SHY ROC > 0 over 20 days) → IEF LONG overlay
             regardless of regime (added independently of TLT/SHY signal).
        """
        # Normalise all dataframes
        cleaned: dict[str, pd.DataFrame] = {}
        for sym, df in data_dict.items():
            su = sym.upper()
            if su in ALLOWED_SYMBOLS:
                cleaned[su] = _coerce(df)

        if "TLT" not in cleaned:
            # Without TLT we can't compute regime or curve; fall back per-symbol
            out: list[dict] = []
            for sym, df in cleaned.items():
                out.extend(self._generate_single(df, sym))
            return out

        tlt_df = cleaned["TLT"]
        p_tlt = self._params_for("TLT")
        required = {"open", "high", "low", "close", "volume"}

        if not required.issubset(tlt_df.columns) or len(tlt_df) < p_tlt.min_bars:
            return []

        tlt_close = tlt_df["close"].astype(float)
        tlt_sma50 = _sma(tlt_close, p_tlt.sma_fast)
        tlt_sma200 = _sma(tlt_close, p_tlt.sma_slow)
        tlt_rsi = _rsi(tlt_close, 14)
        tlt_atr = _atr(tlt_df, 14)

        # Yield-curve steepening: TLT/SHY ratio ROC
        curve_steepen: pd.Series | None = None
        if "SHY" in cleaned:
            shy_close = cleaned["SHY"]["close"].astype(float)
            curve_steepen = self._curve_steepening(tlt_close, shy_close, p_tlt.curve_roc_period)

        out: list[dict] = []

        for i in range(p_tlt.min_bars, len(tlt_df)):
            if pd.isna(tlt_atr.iloc[i]) or pd.isna(tlt_rsi.iloc[i]):
                continue
            if pd.isna(tlt_sma50.iloc[i]) or pd.isna(tlt_sma200.iloc[i]):
                continue

            tlt_c = float(tlt_close.iloc[i])
            tlt_a = float(tlt_atr.iloc[i])
            if tlt_a <= 0.0:
                continue

            s50 = float(tlt_sma50.iloc[i])
            s200 = float(tlt_sma200.iloc[i])
            rsi = float(tlt_rsi.iloc[i])
            ts = tlt_df.index[i]
            bull_regime = s50 > s200

            # ---- Signal A: TLT LONG in bull regime ----
            if bull_regime and p_tlt.rsi_bull_min <= rsi <= p_tlt.rsi_bull_max:
                tp = tlt_c + tlt_a * p_tlt.tp_atr_mult
                sl = tlt_c - tlt_a * p_tlt.sl_atr_mult
                out.append(
                    {
                        "symbol": "TLT",
                        "side": "LONG",
                        "entry_price": round(tlt_c, 6),
                        "take_profit": round(tp, 6),
                        "stop_loss": round(sl, 6),
                        "strength": 68,
                        "reason": (
                            f"Bond BULL: TLT SMA50>{p_tlt.sma_slow}SMA, "
                            f"RSI={rsi:.1f} in [{p_tlt.rsi_bull_min},{p_tlt.rsi_bull_max}], "
                            f"ATR={tlt_a:.4f} [TLT]"
                        ),
                        "strategy": self.NAME,
                        "max_hold_days": p_tlt.max_hold_days,
                        "timestamp": ts,
                        "bar_index": i,
                    }
                )

            # ---- Signal B: SHY LONG in bear regime ----
            if not bull_regime and rsi < p_tlt.rsi_bear_max and "SHY" in cleaned:
                shy_df = cleaned["SHY"]
                p_shy = self._params_for("SHY")
                if required.issubset(shy_df.columns) and len(shy_df) > i:
                    shy_close_series = shy_df["close"].astype(float)
                    shy_c = float(shy_close_series.iloc[i]) if i < len(shy_close_series) else None
                    shy_atr_series = _atr(shy_df, 14)
                    shy_a = (
                        float(shy_atr_series.iloc[i])
                        if i < len(shy_atr_series) and not pd.isna(shy_atr_series.iloc[i])
                        else None
                    )
                    if shy_c is not None and shy_a is not None and shy_a > 0.0:
                        tp = shy_c + shy_a * p_shy.tp_atr_mult
                        sl = shy_c - shy_a * p_shy.sl_atr_mult
                        out.append(
                            {
                                "symbol": "SHY",
                                "side": "LONG",
                                "entry_price": round(shy_c, 6),
                                "take_profit": round(tp, 6),
                                "stop_loss": round(sl, 6),
                                "strength": 62,
                                "reason": (
                                    f"Bond DEFENSIVE: TLT SMA50<{p_tlt.sma_slow}SMA, "
                                    f"TLT RSI={rsi:.1f}<{p_tlt.rsi_bear_max} [SHY]"
                                ),
                                "strategy": self.NAME,
                                "max_hold_days": p_shy.max_hold_days,
                                "timestamp": ts,
                                "bar_index": i,
                            }
                        )

            # ---- Signal C: IEF LONG on curve steepening (independent overlay) ----
            steepening = (
                bool(curve_steepen.iloc[i])
                if curve_steepen is not None and i < len(curve_steepen) and not pd.isna(curve_steepen.iloc[i])
                else False
            )
            if steepening and "IEF" in cleaned:
                ief_df = cleaned["IEF"]
                p_ief = self._params_for("IEF")
                if required.issubset(ief_df.columns) and len(ief_df) > i:
                    ief_close_series = ief_df["close"].astype(float)
                    ief_rsi_series = _rsi(ief_close_series, 14)
                    ief_atr_series = _atr(ief_df, 14)
                    ief_c = float(ief_close_series.iloc[i]) if i < len(ief_close_series) else None
                    ief_rsi_val = (
                        float(ief_rsi_series.iloc[i])
                        if i < len(ief_rsi_series) and not pd.isna(ief_rsi_series.iloc[i])
                        else None
                    )
                    ief_a = (
                        float(ief_atr_series.iloc[i])
                        if i < len(ief_atr_series) and not pd.isna(ief_atr_series.iloc[i])
                        else None
                    )
                    if (
                        ief_c is not None
                        and ief_a is not None
                        and ief_a > 0.0
                        and ief_rsi_val is not None
                        and p_ief.rsi_bull_min <= ief_rsi_val <= p_ief.rsi_bull_max
                    ):
                        tp = ief_c + ief_a * p_ief.tp_atr_mult
                        sl = ief_c - ief_a * p_ief.sl_atr_mult
                        out.append(
                            {
                                "symbol": "IEF",
                                "side": "LONG",
                                "entry_price": round(ief_c, 6),
                                "take_profit": round(tp, 6),
                                "stop_loss": round(sl, 6),
                                "strength": 63,
                                "reason": (
                                    f"Curve steepening overlay: TLT/SHY ROC(20)>0, "
                                    f"IEF RSI={ief_rsi_val:.1f} in [{p_ief.rsi_bull_min},{p_ief.rsi_bull_max}] [IEF]"
                                ),
                                "strategy": self.NAME,
                                "max_hold_days": p_ief.max_hold_days,
                                "timestamp": ts,
                                "bar_index": i,
                            }
                        )

        return out
