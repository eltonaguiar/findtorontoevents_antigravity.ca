"""sentiment_macro_contrarian — sentiment + FRED macro overlay strategy.

Generalizes ``st_fear_greed_contrarian`` (PF 4.22, n=96, WR 75% per
``reports/forward_edge_audit_2026-05-02.json``) by REQUIRING macro alignment
on top of sentiment extremes. The hypothesis: contrarian-on-fear works best
when the macro regime supports a mean-reversion trade — buying CRYPTO panic
into a strong-USD/risk-off tape historically faded; buying CRYPTO panic into
weak-USD reflation has a much higher base rate. Likewise, EQUITY VIX-spike
buys without curve check leave you long into late-cycle inversion gaps.

Asset coverage:
  - CRYPTO  : Alternative.me Fear/Greed Index (FGI). BUY when FGI < 25 AND
              regime.usd != 'strong'. SHORT path intentionally not exposed
              (CRYPTO greed-extreme shorts have weaker base rate without an
              additional regime guard; see research-optimizations.md).
  - EQUITY/ETF : VIX (VIXCLS via FRED). BUY when VIX > 25 AND
                 regime.curve != 'inverted'. SELL/SHORT when VIX < 12 AND
                 regime.vol == 'low' AND regime.curve == 'inverted'
                 (late-cycle complacency — Coibion-Gorodnichenko 2015 +
                 Adrian-Estrella-Shin curve-leading-recession literature).

Confidence model:
  - Sentiment-only fire (macro absent / unknown): conf 0.55-0.62
  - Sentiment + macro alignment (BOTH conditions hot): conf 0.65-0.78

Rollback / kill switch:
  SENTIMENT_MACRO_DISABLED=1   -> module returns [] (no-op).

Wiring Plan (Wire-Up Rule compliance):
  STATUS: WIRED (T2.3, 2026-05-09). Registered into
  ``alpha_engine/confluence_strategies.py::run_confluence_strategies`` via
  module-level import + dispatch-list append guarded by env
  ``SENTIMENT_MACRO_WIRED`` (default "1") AND module's own
  ``SENTIMENT_MACRO_DISABLED`` rollback (default "0"). Production callers
  reach run_confluence_strategies through ``alpha_engine/scanner.py`` and
  ``alpha_engine/production_scanner.py`` (no further wiring needed).

  Follow-ups (not yet wired):
  1. Asset-class router (``alpha_engine/strategy_router.py`` or scanner
     per-asset dispatch): route CRYPTO data to fear_greed branch, EQUITY/ETF
     data to VIX branch (currently both branches share one call).
  2. Acceptance criteria for promotion to default-on: 4-week live run with
     n>=40, WR>=55%, macro-aligned subset PF >= sentiment-only PF + 0.5.

References:
  - st_fear_greed_contrarian baseline: reports/forward_edge_audit_2026-05-02.json
  - FRED macro context module:        alpha_engine/fred_macro_context.py
  - Carry signal-dict shape parity:   alpha_engine/forex_strategies.py:carry_trade
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Graceful degradation if scientific stack absent ────────────────────────
try:
    import numpy as np  # noqa: F401
    import pandas as pd
    _PANDAS_OK = True
except Exception as _exc:  # pragma: no cover
    logger.warning("sentiment_macro_contrarian: pandas/numpy unavailable (%s); module is no-op", _exc)
    _PANDAS_OK = False

_FG_HISTORY_PATH = Path(__file__).resolve().parent.parent / "audit_dashboard" / "data" / "fear_greed_history.json"

# Tier sets for EQUITY/ETF dispatch — copied (not imported) so the module
# stays importable even if elite_scorer fails to load.
_TIER1_EQUITY = {
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA",
    "BRKB", "JPM", "V", "WMT", "XOM", "JNJ", "UNH", "LLY", "AVGO", "MA",
    "HD", "PG",
}
_TIER1_ETF = {
    "SPY", "QQQ", "IWM", "DIA", "VOO", "VTI", "IVV",
    "EEM", "EFA",
    "GLD", "SLV", "TLT", "HYG", "LQD",
    "XLF", "XLE", "XLK", "XLV",
}


def _disabled() -> bool:
    return os.environ.get("SENTIMENT_MACRO_DISABLED", "0") == "1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm_symbol(sym: str) -> str:
    s = (sym or "").upper()
    if s.endswith("=X"):
        s = s[:-2]
    return s.replace("-", "").replace("/", "").replace(".", "").replace("USDT", "").replace("USD", "")


def _is_crypto(sym: str) -> bool:
    s = (sym or "").upper()
    return ("USDT" in s) or s.endswith("-USD") or s.endswith("USD") and any(
        c in s for c in ("BTC", "ETH", "SOL", "AVAX", "LINK", "DOGE", "ADA", "DOT", "XRP", "BNB")
    )


def _is_equity_or_etf(sym: str) -> bool:
    norm = _norm_symbol(sym)
    return norm in _TIER1_EQUITY or norm in _TIER1_ETF


def _load_fear_greed(kwarg_val: Any) -> int | None:
    """Resolve FGI from kwarg first, else fear_greed_history.json."""
    if isinstance(kwarg_val, int):
        return kwarg_val
    if isinstance(kwarg_val, dict):
        try:
            return int(kwarg_val["data"][0]["value"])
        except (KeyError, IndexError, TypeError, ValueError):
            pass
    try:
        if _FG_HISTORY_PATH.exists():
            blob = json.loads(_FG_HISTORY_PATH.read_text(encoding="utf-8"))
            data = blob.get("data") or blob if isinstance(blob, dict) else blob
            if isinstance(data, list) and data:
                return int(data[0].get("value"))
            if isinstance(blob, dict) and "current" in blob:
                return int(blob["current"])
    except Exception as exc:
        logger.debug("fear_greed_history load failed: %s", exc)
    return None


def _load_macro() -> dict:
    try:
        from alpha_engine.fred_macro_context import get_macro_context
        return get_macro_context() or {}
    except Exception as exc:
        logger.debug("fred_macro_context load failed: %s", exc)
        return {}


def _tp_sl(price: float, direction: str, tp_pct: float, sl_pct: float) -> tuple[float, float]:
    if direction == "BUY":
        return round(price * (1 + tp_pct), 6), round(price * (1 - sl_pct), 6)
    return round(price * (1 - tp_pct), 6), round(price * (1 + sl_pct), 6)


def _emit(symbol: str, direction: str, asset_class: str, entry: float,
          fgi: int | None, vix: float | None, regime: dict, aligned: bool,
          reason: str) -> dict:
    tp_pct = 0.05 if asset_class == "CRYPTO" else 0.04
    sl_pct = 0.03 if asset_class == "CRYPTO" else 0.025
    tp, sl = _tp_sl(entry, direction, tp_pct, sl_pct)
    base_conf = 0.58 if not aligned else 0.70
    if asset_class == "CRYPTO" and fgi is not None and fgi < 15:
        base_conf += 0.05
    if asset_class != "CRYPTO" and vix is not None and vix > 35:
        base_conf += 0.05
    conf = round(min(0.78, max(0.55, base_conf)), 3)
    return {
        "symbol": symbol,
        "direction": direction,
        "strategy": "sentiment_macro_contrarian",
        "asset_class": asset_class,
        "category": "crypto" if asset_class == "CRYPTO" else "equity",
        "timeframe": "1d",
        "entry_price": round(entry, 6),
        "stop_loss": sl,
        "take_profit": tp,
        "confidence": conf,
        "generated_at": _now_iso(),
        "extra": {
            "fear_greed_value": fgi,
            "vix": vix,
            "macro_regime": regime,
            "macro_aligned": aligned,
        },
        "reason": reason,
    }


def sentiment_macro_contrarian(data: dict, **kwargs) -> list[dict]:
    """Sentiment + FRED macro contrarian dispatcher.

    Args:
        data: {symbol: pd.DataFrame OHLCV} keyed by ticker.
        kwargs:
            fear_greed: int | dict — current Alternative.me FGI (overrides file).
            macro: dict — pre-fetched macro snapshot (overrides FRED call).

    Returns:
        List of signal dicts (see module docstring for schema).
    """
    if _disabled() or not _PANDAS_OK or not data:
        return []

    fgi = _load_fear_greed(kwargs.get("fear_greed"))
    macro = kwargs.get("macro") or _load_macro()
    regime = (macro.get("regime") if isinstance(macro, dict) else {}) or {}
    indicators = (macro.get("indicators") if isinstance(macro, dict) else {}) or {}
    vix = None
    try:
        vix_entry = indicators.get("VIXCLS") or {}
        if vix_entry.get("value") is not None:
            vix = float(vix_entry["value"])
    except Exception:
        vix = None

    usd = regime.get("usd")
    curve = regime.get("curve")
    vol = regime.get("vol")

    signals: list[dict] = []
    for symbol, df in data.items():
        if df is None or len(df) < 5:
            continue
        try:
            entry = float(df["Close"].iloc[-1])
        except Exception:
            continue
        if not entry or entry <= 0:
            continue

        if _is_crypto(symbol):
            if fgi is None or fgi >= 25:
                continue
            aligned = (usd in ("weak", "neutral")) and usd != "strong"
            # Hard requirement: macro must NOT be 'strong USD' for crypto BUY.
            if usd == "strong":
                continue
            macro_aligned = (usd == "weak")
            reason = (f"FGI={fgi} extreme-fear; usd_regime={usd or 'unknown'}; "
                      f"macro_aligned={macro_aligned}")
            signals.append(_emit(symbol, "BUY", "CRYPTO", entry, fgi, vix,
                                 regime, macro_aligned, reason))
            continue

        if _is_equity_or_etf(symbol):
            if vix is None:
                continue
            asset_class = "EQUITY" if _norm_symbol(symbol) in _TIER1_EQUITY else "ETF"
            # BUY: extreme fear + curve not inverted
            if vix > 25 and curve != "inverted":
                macro_aligned = curve in ("flat", "steep")
                reason = (f"VIX={vix:.1f} extreme-fear; curve={curve or 'unknown'}; "
                          f"macro_aligned={macro_aligned}")
                signals.append(_emit(symbol, "BUY", asset_class, entry, fgi, vix,
                                     regime, macro_aligned, reason))
                continue
            # SHORT: complacency + low vol + inverted curve (late-cycle)
            if vix < 12 and vol == "low" and curve == "inverted":
                reason = (f"VIX={vix:.1f} complacency; vol={vol}; curve={curve} "
                          f"(late-cycle short)")
                signals.append(_emit(symbol, "SELL", asset_class, entry, fgi, vix,
                                     regime, True, reason))
                continue

    return signals


__all__ = ["sentiment_macro_contrarian"]


# ──────────────────────────────────────────────────────────────────────────
# Synthetic backtest (run via: python -m alpha_engine.sentiment_macro_contrarian)
# ──────────────────────────────────────────────────────────────────────────
def _synthetic_backtest() -> dict:
    if not _PANDAS_OK:
        return {"error": "pandas unavailable"}
    rng = np.random.default_rng(42)
    n = 200
    base = 100.0
    rets = rng.normal(0.001, 0.02, n)
    closes = base * np.cumprod(1 + rets)
    df = pd.DataFrame({
        "Open": closes,
        "High": closes * (1 + rng.uniform(0, 0.01, n)),
        "Low": closes * (1 - rng.uniform(0, 0.01, n)),
        "Close": closes,
        "Volume": rng.integers(1e6, 1e7, n),
    }, index=pd.date_range("2025-01-01", periods=n, freq="D"))

    data = {"BTC-USDT": df.copy(), "SPY": df.copy()}
    # Event 1: extreme fear FGI=15 -> CRYPTO BUY
    fear_signals = sentiment_macro_contrarian(data, fear_greed=15, macro={
        "regime": {"usd": "weak", "curve": "steep", "vol": "elevated"},
        "indicators": {"VIXCLS": {"value": 30.0, "date": "2025-09-01"}},
    })
    # Event 2: extreme greed FGI=82 -> CRYPTO no fire (only fear path implemented)
    greed_signals = sentiment_macro_contrarian(data, fear_greed=82, macro={
        "regime": {"usd": "neutral", "curve": "flat", "vol": "low"},
        "indicators": {"VIXCLS": {"value": 11.0, "date": "2025-09-02"}},
    })
    # Event 3: late-cycle complacency -> EQUITY SHORT
    complacency_signals = sentiment_macro_contrarian({"SPY": df.copy()}, fear_greed=55, macro={
        "regime": {"usd": "neutral", "curve": "inverted", "vol": "low"},
        "indicators": {"VIXCLS": {"value": 11.0, "date": "2025-09-03"}},
    })

    all_signals = fear_signals + greed_signals + complacency_signals
    # Quick TP/SL hit-rate estimate at 5%/3% (CRYPTO) vs 4%/2.5% (EQUITY).
    # Synthetic: assume normal returns -> P(reach +TP before -SL) ~ SL/(TP+SL).
    wr_estimates = []
    for s in all_signals:
        tp_pct = abs(s["take_profit"] - s["entry_price"]) / s["entry_price"]
        sl_pct = abs(s["stop_loss"] - s["entry_price"]) / s["entry_price"]
        wr_estimates.append(sl_pct / (tp_pct + sl_pct))
    wr_est = round(sum(wr_estimates) / len(wr_estimates), 3) if wr_estimates else None

    return {
        "n_signals": len(all_signals),
        "fear_event_signals": len(fear_signals),
        "greed_event_signals": len(greed_signals),
        "complacency_short_signals": len(complacency_signals),
        "wr_estimate_random_walk": wr_est,
        "sample_signal": all_signals[0] if all_signals else None,
    }


if __name__ == "__main__":
    import pprint
    print("=== sentiment_macro_contrarian synthetic backtest ===")
    if not _PANDAS_OK:
        print("pandas unavailable — module is no-op stub")
        raise SystemExit(0)
    # Try real macro pull (no-op if FRED_API_KEY missing).
    real_macro = _load_macro()
    print(f"FRED snapshot keys: {list(real_macro.keys()) if real_macro else 'unavailable'}")
    result = _synthetic_backtest()
    pprint.pprint(result)
