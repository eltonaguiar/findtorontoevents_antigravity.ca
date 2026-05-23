"""VIX regime gate (opt-in sidecar) — EQUITY momentum overlay.

Per `reports/equity_vix_regime_breakthrough_20260513.md`:
  EQUITY top-5 12-1m momentum + VIX<22 filter delivers PF 4.55 / Sharpe 1.98 /
  MDD 16.8% over 11y (vs baseline PF 2.82 / Sharpe 1.34 / MDD 24.2%).

Used by:
  - `audit_trail/quality_gates.py::passes_smart_gate` when env
    `VIX_REGIME_GATE_ENABLED=1` (default 1, ON) and asset_class == EQUITY.

Cache: VIX fetch is 4h-cached in-memory; ~1 fetch per process per day.
Falls back to "permissive" (gate doesn't reject) if VIX fetch fails — fail-open.

Reversibility: env-flag flip. Default-off preserves current behavior.

## Wiring Plan (per CLAUDE.md Wire-Up Rule)

| Field | Value |
|---|---|
| Target caller | `audit_trail/quality_gates.py::passes_smart_gate` |
| Default | `VIX_REGIME_GATE_ENABLED=1` (ON) |
| Behavior when ON | EQUITY picks rejected when current VIX > threshold (default 22) |
| Threshold tunable | `VIX_REGIME_GATE_THRESHOLD` env (default 22.0) |
| Audit trail | sets `pick['_hf_quality_gate_reason'] = 'vix_regime_high_vol'` |
| Shadow mode | Operator runs with flag OFF first to log would-be-rejects; flip ON after 7d shadow log shows clean signal |

NFA — backtest-derived, not production-validated.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

_VIX_CACHE: tuple[int, Optional[float]] | None = None
_YC_CACHE: tuple[int, Optional[float]] | None = None
_CACHE_TTL_SEC = 4 * 3600


def _fetch_vix_now() -> Optional[float]:
    """Fetch latest ^VIX close. Returns None on any failure."""
    try:
        import yfinance as yf
        df = yf.download("^VIX", period="5d", interval="1d",
                         progress=False, auto_adjust=True)
        if df.empty:
            return None
        close_col = df["Close"] if "Close" in df.columns else df.iloc[:, 0]
        if hasattr(close_col, "iloc"):
            v = close_col.iloc[-1]
            if hasattr(v, "iloc"):
                v = v.iloc[0]
            return float(v) if v is not None else None
        return None
    except Exception as exc:  # noqa: BLE001 — fail-open by design
        logger.debug("VIX fetch failed (fail-open): %s", exc)
        return None


def get_cached_vix() -> Optional[float]:
    """Get cached VIX or fetch fresh."""
    global _VIX_CACHE
    now = int(time.time())
    if _VIX_CACHE is not None:
        cached_at, cached_val = _VIX_CACHE
        if now - cached_at < _CACHE_TTL_SEC:
            return cached_val
    fresh = _fetch_vix_now()
    _VIX_CACHE = (now, fresh)
    return fresh


def reset_cache() -> None:
    """Test helper — clear module-level cache."""
    global _VIX_CACHE
    _VIX_CACHE = None


def is_vix_above_threshold(threshold: Optional[float] = None) -> bool:
    """True iff current VIX > threshold. Returns False on fetch failure (fail-open)."""
    if threshold is None:
        try:
            threshold = float(os.environ.get("VIX_REGIME_GATE_THRESHOLD", "22.0"))
        except (ValueError, TypeError):
            threshold = 22.0
    vix = get_cached_vix()
    if vix is None:
        return False
    return vix > threshold


def _fetch_yc_now() -> Optional[float]:
    """Fetch latest 10y-5y yield-curve spread (^TNX - ^FVX). Returns None on failure."""
    try:
        import yfinance as yf
        df = yf.download(["^TNX", "^FVX"], period="5d", interval="1d",
                         progress=False, auto_adjust=True)
        if df.empty:
            return None
        close = df["Close"] if "Close" in df.columns else df
        tnx = close["^TNX"].dropna().iloc[-1] if "^TNX" in close.columns else None
        fvx = close["^FVX"].dropna().iloc[-1] if "^FVX" in close.columns else None
        if tnx is None or fvx is None:
            return None
        return float(tnx) - float(fvx)
    except Exception as exc:  # noqa: BLE001 — fail-open by design
        logger.debug("YC fetch failed (fail-open): %s", exc)
        return None


def get_cached_yc() -> Optional[float]:
    """Get cached YC spread or fetch fresh."""
    global _YC_CACHE
    now = int(time.time())
    if _YC_CACHE is not None:
        cached_at, cached_val = _YC_CACHE
        if now - cached_at < _CACHE_TTL_SEC:
            return cached_val
    fresh = _fetch_yc_now()
    _YC_CACHE = (now, fresh)
    return fresh


def is_yc_below_threshold(threshold: Optional[float] = None) -> bool:
    """True iff current YC spread < threshold. Returns False on fetch failure (fail-open)."""
    if threshold is None:
        try:
            threshold = float(os.environ.get("YC_REGIME_GATE_MIN_SPREAD", "0.0"))
        except (ValueError, TypeError):
            threshold = 0.0
    yc = get_cached_yc()
    if yc is None:
        return False
    return yc < threshold


def should_reject_combined(pick: dict) -> bool:
    """Combined VIX + YC regime gate (2-of-2 filter).

    Per reports/equity_vix_yc_combined_super_breakthrough_20260513.md:
    EQUITY VIX<22 AND YC>0 backtest: PF 4.98 / Sharpe 2.08 / MDD 16.8% / n=79.
    Better risk-adjusted than VIX-only or YC-only.

    Returns True iff:
      - env `YC_REGIME_GATE_ENABLED=1` (default 1 — enabled; set to 0 to disable)
      - asset_class in (EQUITY, ETF)
      - current YC < threshold OR current VIX > threshold (either bad)

    Otherwise False (don't gate).
    """
    # 2026-05-16: Default changed to "1" (enabled). Combined VIX+YC delivers
    # PF 4.98 / Sharpe 2.08 vs VIX-only PF 4.55 per equity_vix_yc_combined_super_breakthrough_20260513.md.
    flag = os.environ.get("YC_REGIME_GATE_ENABLED", "1").strip().lower()
    if flag not in ("1", "true", "yes", "on", "t", "y"):
        return False
    ac = str(pick.get("asset_class", "") or "").strip().upper()
    if ac not in ("EQUITY", "ETF"):
        return False
    # Combined: reject if EITHER signal bad (AND-of-passes pattern)
    if is_vix_above_threshold():
        return True
    if is_yc_below_threshold():
        return True
    return False


def reset_yc_cache() -> None:
    """Test helper — clear YC cache."""
    global _YC_CACHE
    _YC_CACHE = None


def should_reject_equity_pick(pick: dict) -> bool:
    """Decide if an EQUITY or ETF pick should be rejected per VIX regime gate.

    Extended 2026-05-13 to cover ETF asset_class:
    Per reports/etf_vix_regime_breakthrough_20260513.md, ETF sector-rotation
    delivers TIER-1 PF (3.91) + Sharpe (1.93) + MDD (8.1%) under same VIX<20
    filter that delivers EQUITY TIER-1. Pattern transfers.

    Modes (VIX_REGIME_GATE_ENABLED env var):
      "1" / "true" / "yes" / "on" / "t" / "y" — ACTIVE: picks rejected when VIX > threshold
      "shadow" / "log_only"                     — SHADOW: logs a WARNING but returns False
                                                    (pick not rejected; lets operators observe
                                                    what would be blocked without live impact)
      anything else (incl. "0" / unset default) — OFF: gate is no-op
    """
    flag = os.environ.get("VIX_REGIME_GATE_ENABLED", "1").strip().lower()
    ac = str(pick.get("asset_class", "") or "").strip().upper()

    if flag in ("shadow", "log_only"):
        # Shadow mode: observe without enforcing
        if ac in ("EQUITY", "ETF") and is_vix_above_threshold():
            symbol = pick.get("symbol", pick.get("ticker", "UNKNOWN"))
            vix_val = get_cached_vix()
            logger.warning(
                "VIX regime gate SHADOW: would reject pick for symbol=%s, VIX=%.2f (threshold=%.1f)",
                symbol,
                vix_val if vix_val is not None else float("nan"),
                float(os.environ.get("VIX_REGIME_GATE_THRESHOLD", "22.0")),
            )
        return False

    if flag not in ("1", "true", "yes", "on", "t", "y"):
        return False
    if ac not in ("EQUITY", "ETF"):
        return False
    if is_vix_above_threshold():
        return True
    return False
