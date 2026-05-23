"""Regime-Filtered Momentum Strategy (EQUITY + ETF).

Closes the `regime_aware_momentum` gap surfaced by audit-round boilerplate
cycle (no production def existed per
docs/strategy-audit-rounds/COVERAGE_VALIDATION_2026-05-09.md).

Combines two well-replicated edges:
  1. Asness 12-1 momentum (Asness, Frazzini, Pedersen 2013): cross-section
     winners minus losers, computed on (close[-21] / close[-252]) - 1 to
     skip the most recent month and dodge short-term reversal.
  2. FRED macro regime gate via alpha_engine.fred_macro_context: gate LONGs
     to flat/steep curve + non-elevated VIX (Estrella & Hardouvelis 1991
     show inverted curve precedes recessions; vol spikes break momentum).

Universe: TIER1_EQUITY + TIER1_ETF from alpha_engine/elite_scorer.py.

Output schema matches the rest of alpha_engine/equity_strategies.py family:
  symbol, direction, strategy, asset_class, category, timeframe,
  entry_price, stop_loss, take_profit, confidence, regime_context.

Wiring plan (Wire-Up Rule compliance):
  STATUS: WIRED (T2.3, 2026-05-09). Registered into
  ``alpha_engine/equity_strategies.py::_RAW_EQUITY_STRATEGIES`` (which is
  then wrapped by ``_wrap_with_factor_model`` into ``EQUITY_STRATEGIES``)
  via best-effort import + idempotent dict assignment guarded by module's
  own ``REGIME_MOMENTUM_DISABLED=1`` rollback. Production callers
  (``alpha_engine/scanner.py``, ``alpha_engine/production_scanner.py``)
  iterate ``EQUITY_STRATEGIES`` at scanner.py:1962, so no further wiring
  needed. The factor-model wrapper calls ``fn(data)`` only -- compatible
  because this function's ``**kwargs`` are optional.

  Gap noted: ``non_crypto_consensus.py`` is missing on 2026-05-09; the
  equity_strategies registry is the next-best caller per CLAUDE.md
  Wire-Up Rule. If/when non_crypto_consensus is restored, prefer
  registering there for asset-class-aware dispatch.

  Follow-ups:
  1. dashboard_generator surfaces `regime_context` snapshot inside
     pick.extra so /audit can render the gating decision.
  2. Audit acceptance for promotion to default-on: 7-day shadow run with
     no >10% n drop on EQUITY/ETF asset class; macro_gated skip-log
     observable; PF>1.0.

Rollback:
  REGIME_MOMENTUM_DISABLED=1 -> regime_filtered_momentum() returns [].
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---- Universe (mirrored from elite_scorer; defensive fallback if import fails)
try:
    from alpha_engine.elite_scorer import TIER1_EQUITY, TIER1_ETF  # type: ignore
except Exception:  # pragma: no cover
    try:
        from elite_scorer import TIER1_EQUITY, TIER1_ETF  # type: ignore
    except Exception:
        TIER1_EQUITY = {
            'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'NVDA', 'TSLA',
            'BRKB', 'JPM', 'V', 'WMT', 'XOM', 'JNJ', 'UNH', 'LLY', 'AVGO',
            'MA', 'HD', 'PG',
        }
        TIER1_ETF = {
            'SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'VTI', 'IVV', 'EEM', 'EFA',
            'GLD', 'SLV', 'TLT', 'HYG', 'LQD', 'XLF', 'XLE', 'XLK', 'XLV',
        }

# ---- FRED macro context (graceful degradation if unavailable)
_HAS_MACRO = False
try:
    from alpha_engine.fred_macro_context import get_macro_context  # type: ignore
    _HAS_MACRO = True
except Exception:  # pragma: no cover
    try:
        from fred_macro_context import get_macro_context  # type: ignore
        _HAS_MACRO = True
    except Exception:
        def get_macro_context(refresh: bool = False) -> dict:  # type: ignore
            return {}


_STRATEGY_NAME = "regime_filtered_momentum"
_TIMEFRAME = "1d"
_STOP_LOSS_PCT = 0.08   # 8% trailing stop
_TAKE_PROFIT_PCT = 0.15  # 15% target
_MIN_MOM_ABS = 0.05      # |mom| > 5% to enter
_TOP_N = 5
_LOOKBACK = 252
_SKIP = 21


def _disabled() -> bool:
    return os.environ.get("REGIME_MOMENTUM_DISABLED", "0") == "1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _asset_class(symbol: str) -> str:
    return "ETF" if symbol in TIER1_ETF else "EQUITY"


def _category(symbol: str, asset_class: str) -> str:
    if asset_class == "ETF":
        return "etf"
    return "stock"


def _compute_momentum(df: pd.DataFrame) -> float | None:
    """Asness 12-1: (close[-21] / close[-252]) - 1, skip latest month."""
    if df is None or len(df) < _LOOKBACK + 1:
        return None
    col = "Close" if "Close" in df.columns else ("close" if "close" in df.columns else None)
    if col is None:
        return None
    close = df[col]
    try:
        c_skip = float(close.iloc[-(_SKIP + 1)])
        c_old = float(close.iloc[-_LOOKBACK])
    except Exception:
        return None
    if not np.isfinite(c_skip) or not np.isfinite(c_old) or c_old <= 0:
        return None
    return (c_skip / c_old) - 1.0


def _last_close(df: pd.DataFrame) -> float | None:
    col = "Close" if "Close" in df.columns else ("close" if "close" in df.columns else None)
    if col is None:
        return None
    try:
        v = float(df[col].iloc[-1])
    except Exception:
        return None
    return v if np.isfinite(v) and v > 0 else None


def _evaluate_regime(macro: dict) -> tuple[bool, bool, dict]:
    """Return (long_allowed, short_allowed, regime_snapshot).

    LONG: curve in {flat, steep} AND vol != elevated
    SHORT: curve == inverted AND vol == elevated
    Default permissive (LONG only) when macro is empty / unavailable.
    """
    if not macro:
        return True, False, {"_macro_unavailable": True}
    regime = (macro.get("regime") or {}) if isinstance(macro, dict) else {}
    curve = str(regime.get("curve") or "unknown")
    vol = str(regime.get("vol") or "unknown")
    usd = str(regime.get("usd") or "unknown")

    long_ok = curve in {"flat", "steep"} and vol != "elevated"
    short_ok = curve == "inverted" and vol == "elevated"
    snap = {
        "curve": curve, "vol": vol, "usd": usd,
        "as_of": macro.get("as_of"),
        "_macro_unavailable": False,
    }
    return long_ok, short_ok, snap


def _build_signal(symbol: str, mom: float, entry: float,
                  direction: str, regime_snap: dict) -> dict:
    asset_class = _asset_class(symbol)
    cat = _category(symbol, asset_class)
    if direction == "LONG":
        sl = round(entry * (1 - _STOP_LOSS_PCT), 4)
        tp = round(entry * (1 + _TAKE_PROFIT_PCT), 4)
    else:
        sl = round(entry * (1 + _STOP_LOSS_PCT), 4)
        tp = round(entry * (1 - _TAKE_PROFIT_PCT), 4)
    confidence = float(np.clip(abs(mom) / 0.20, 0.50, 0.95))
    sig = {
        "symbol": symbol,
        "direction": direction,
        "strategy": _STRATEGY_NAME,
        "asset_class": asset_class,
        "category": cat,
        "timeframe": _TIMEFRAME,
        "entry_price": round(entry, 4),
        "stop_loss": sl,
        "take_profit": tp,
        "confidence": round(confidence, 3),
        "regime_context": regime_snap,
        "extra": {
            "momentum_12_1": round(mom, 4),
            "stop_pct": _STOP_LOSS_PCT,
            "tp_pct": _TAKE_PROFIT_PCT,
        },
        "timestamp": _now_iso(),
    }
    if regime_snap.get("_macro_unavailable"):
        sig["_macro_unavailable"] = True
    return sig


def regime_filtered_momentum(data: dict[str, pd.DataFrame], **kwargs) -> list[dict]:
    """Generate regime-gated 12-1 momentum signals on EQUITY+ETF universe.

    kwargs:
      macro_context: optional pre-computed dict from get_macro_context();
        primarily for tests / backtests.
    """
    if _disabled():
        return []
    if not data:
        return []

    macro = kwargs.get("macro_context")
    if macro is None:
        try:
            macro = get_macro_context() if _HAS_MACRO else {}
        except Exception as exc:
            logger.warning("get_macro_context failed: %s", exc)
            macro = {}

    long_ok, short_ok, regime_snap = _evaluate_regime(macro)

    universe = (TIER1_EQUITY | TIER1_ETF) & set(data.keys())
    scored: list[tuple[str, float]] = []
    for sym in universe:
        mom = _compute_momentum(data[sym])
        if mom is None:
            continue
        scored.append((sym, mom))

    if not scored:
        return []

    scored.sort(key=lambda x: x[1], reverse=True)
    signals: list[dict] = []

    if long_ok:
        for sym, mom in scored[:_TOP_N]:
            if mom < _MIN_MOM_ABS:
                continue
            entry = _last_close(data[sym])
            if entry is None:
                continue
            signals.append(_build_signal(sym, mom, entry, "LONG", regime_snap))

    if short_ok:
        for sym, mom in scored[-_TOP_N:]:
            if -mom < _MIN_MOM_ABS:  # need mom < -0.05
                continue
            entry = _last_close(data[sym])
            if entry is None:
                continue
            signals.append(_build_signal(sym, mom, entry, "SHORT", regime_snap))

    return signals


__all__ = ["regime_filtered_momentum"]


# =========================================================================
# Backtest harness (synthetic)
# =========================================================================
def _synth_bars(seed: int, days: int, drift: float, vol: float,
                reversal_at: int | None = None) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rets = rng.normal(drift, vol, size=days)
    if reversal_at is not None and 0 < reversal_at < days:
        rets[reversal_at:] = -rets[reversal_at:] * 0.6
    price = 100.0 * np.exp(np.cumsum(rets))
    idx = pd.date_range("2024-01-01", periods=days, freq="B")
    return pd.DataFrame({
        "Open": price * (1 - 0.001),
        "High": price * (1 + 0.003),
        "Low": price * (1 - 0.003),
        "Close": price,
        "Volume": rng.integers(1_000_000, 5_000_000, size=days),
    }, index=idx)


def _mock_macro(curve: str, vol: str, usd: str = "neutral") -> dict:
    return {
        "as_of": _now_iso(),
        "regime": {"curve": curve, "vol": vol, "usd": usd},
        "indicators": {},
    }


def _run_backtest() -> dict:
    """Synthetic 5 symbols x 600 days, rotate 4 regimes, monthly rebalance."""
    syms = ["AAPL", "SPY", "QQQ", "TLT", "GLD"]
    cfg = [
        (1, 0.0009, 0.012, None),
        (2, 0.0006, 0.010, 400),
        (3, 0.0008, 0.011, None),
        (4, -0.0002, 0.009, None),
        (5, 0.0003, 0.014, 300),
    ]
    days = 600
    data_full = {s: _synth_bars(seed, days, drift, vol_, rev)
                 for s, (seed, drift, vol_, rev) in zip(syms, cfg)}

    regimes = [
        ("steep", "low"),
        ("flat", "normal"),
        ("inverted", "elevated"),
        ("inverted", "normal"),
    ]

    rebal_idx = list(range(_LOOKBACK + _SKIP + 5, days - 21, 21))
    hits = 0
    total = 0
    monthly_rets: list[float] = []
    rebals: list[dict] = []

    for i, t in enumerate(rebal_idx):
        slice_data = {s: df.iloc[: t + 1] for s, df in data_full.items()}
        curve, vol_lbl = regimes[i % len(regimes)]
        macro = _mock_macro(curve, vol_lbl)
        sigs = regime_filtered_momentum(slice_data, macro_context=macro)
        rebals.append({"t": t, "regime": (curve, vol_lbl), "n_signals": len(sigs)})

        if not sigs:
            monthly_rets.append(0.0)
            continue

        port_ret = []
        for s in sigs:
            sym = s["symbol"]
            df = data_full[sym]
            if t + 21 >= len(df):
                continue
            entry = float(df["Close"].iloc[t])
            exitp = float(df["Close"].iloc[t + 21])
            r = (exitp / entry) - 1.0
            if s["direction"] == "SHORT":
                r = -r
            port_ret.append(r)
            total += 1
            if r > 0:
                hits += 1
        if port_ret:
            monthly_rets.append(float(np.mean(port_ret)))
        else:
            monthly_rets.append(0.0)

    arr = np.array(monthly_rets, dtype=float)
    if arr.std() > 1e-9 and len(arr) > 1:
        sharpe = float(arr.mean() / arr.std() * np.sqrt(12))
    else:
        sharpe = 0.0
    hit_rate = hits / total if total else 0.0

    return {
        "n_rebalances": len(rebal_idx),
        "n_signals_total": total,
        "hit_rate": round(hit_rate, 4),
        "monthly_mean_pct": round(float(arr.mean()) * 100, 4),
        "monthly_std_pct": round(float(arr.std()) * 100, 4),
        "sharpe_annualized_eqweight": round(sharpe, 3),
        "rebalance_log": rebals[:6],
    }


if __name__ == "__main__":
    import json
    res = _run_backtest()
    print(json.dumps(res, indent=2, default=str))
