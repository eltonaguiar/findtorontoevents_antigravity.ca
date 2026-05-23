"""
ALPHA_ENGINE -- BOND Yield Curve Inversion Strategy
====================================================
Macro strategy: enter long-duration bonds (TLT/IEF) when the 10Y-2Y Treasury
spread (FRED series T10Y2Y) inverts (< 0) AND is deepening (>5bp drop over 30d).
Optional SHORT TLT (or LONG TBT) when curve steepens (spread > 0 AND >10bp rise
over 30d).

Reference: reports/edge_research_synthesis_2026_05_12.md (Grok-4 #4, exp PF 1.8).
BOND class currently n=11 paper-only; this strategy stays paper_only=True until
BOND realized n >= 100.

DEFAULT-OFF gated on env BOND_YIELD_CURVE_INVERSION_ENABLED=1.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# FRED fetcher: prefer tools/fred_data_fetcher.py if/when PR-J ships it,
# otherwise fall back to existing alpha_engine.bond_data_fred.fetch_fred_series.
# Final fallback returns None gracefully.
# ---------------------------------------------------------------------------
def _fetch_t10y2y(lookback_days: int = 120) -> Optional[list[dict]]:
    """Return list of {'date','value'} for T10Y2Y over last N days, or None."""
    end = datetime.utcnow().date()
    start = end - timedelta(days=lookback_days)
    # 1) prefer tools.fred_data_fetcher (PR-J), if present
    try:
        from tools.fred_data_fetcher import fetch_series  # type: ignore
        rows = fetch_series("T10Y2Y", start.isoformat(), end.isoformat())
        if rows:
            return rows
    except Exception:
        pass
    # 2) fall back to alpha_engine.bond_data_fred
    try:
        try:
            from bond_data_fred import fetch_fred_series  # type: ignore
        except ImportError:
            from alpha_engine.bond_data_fred import fetch_fred_series
        rows = fetch_fred_series("T10Y2Y", start.isoformat(), end.isoformat())
        return rows or None
    except Exception as e:
        logger.info("T10Y2Y fetch failed: %s", e)
        return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _enabled() -> bool:
    return os.getenv("BOND_YIELD_CURVE_INVERSION_ENABLED", "0").strip().lower() in (
        "1", "true", "yes", "on",
    )


# ---------------------------------------------------------------------------
# Core strategy
# ---------------------------------------------------------------------------
def bond_yield_curve_inversion(
    data: Optional[dict] = None,
    rows: Optional[list[dict]] = None,
) -> list[dict]:
    """Generate BOND picks from 10Y-2Y spread (T10Y2Y) regime.

    Args:
        data: ignored (kept for registry signature parity with other bond strats).
        rows: optional pre-fetched T10Y2Y series (list of {'date','value'} in pp).
              Mainly used for testing without FRED network access.

    Returns:
        List of pick dicts. Always paper_only=True until BOND n>=100.
    """
    if not _enabled():
        return []

    series = rows if rows is not None else _fetch_t10y2y(lookback_days=120)
    if not series or len(series) < 31:
        return []

    # values in percentage points (pp); 0.01 pp == 1bp
    values = [float(r["value"]) for r in series if r.get("value") is not None]
    if len(values) < 31:
        return []

    spread_now = values[-1]
    spread_30d_ago = values[-31]
    delta_30d_pp = spread_now - spread_30d_ago  # pp; negative == deepening
    delta_30d_bp = delta_30d_pp * 100.0  # bp

    inverted = spread_now < 0.0
    deepening = delta_30d_bp < -5.0   # >5bp drop
    steepening = delta_30d_bp > 10.0  # >10bp rise

    direction: Optional[str] = None
    primary_symbol: Optional[str] = None
    secondary_symbol: Optional[str] = None
    reason: str = ""
    if inverted and deepening:
        direction = "BUY"
        primary_symbol = "TLT"
        secondary_symbol = "IEF"
        reason = (
            f"10Y-2Y inverted ({spread_now:.2f}pp) and deepening "
            f"({delta_30d_bp:+.1f}bp / 30d) -> long duration"
        )
    elif (not inverted) and steepening:
        direction = "SELL"
        primary_symbol = "TLT"
        secondary_symbol = "TBT"
        reason = (
            f"10Y-2Y positive ({spread_now:.2f}pp) and steepening "
            f"({delta_30d_bp:+.1f}bp / 30d) -> short duration"
        )

    if direction is None:
        return []

    # confidence scales 0.55..0.70 with |delta_30d_bp|
    mag = min(abs(delta_30d_bp), 40.0) / 40.0
    confidence = round(0.55 + 0.15 * mag, 2)

    base_pick = {
        "strategy": "bond_yield_curve_inversion",
        "category": "bond",
        "asset_class": "BOND",
        "signal_type": direction,
        "confidence": confidence,
        "reason": reason,
        "timeframe": "12h",
        "paper_only": True,
        "exit_rules": {
            "steepens_back_above_zero": True,
            "max_hold_days": 90,
        },
        "extra": {
            "spread_now_pp": round(spread_now, 4),
            "spread_30d_ago_pp": round(spread_30d_ago, 4),
            "delta_30d_bp": round(delta_30d_bp, 2),
            "series": "T10Y2Y",
        },
        "timestamp": _now_iso(),
    }

    picks: list[dict] = []
    primary = dict(base_pick); primary["symbol"] = primary_symbol; primary["role"] = "primary"
    picks.append(primary)
    if secondary_symbol:
        secondary = dict(base_pick); secondary["symbol"] = secondary_symbol; secondary["role"] = "secondary"
        secondary["confidence"] = round(max(0.55, confidence - 0.05), 2)
        picks.append(secondary)
    # Defensive SHY pick only when inverted (flight-to-quality short end)
    if direction == "BUY":
        shy = dict(base_pick); shy["symbol"] = "SHY"; shy["role"] = "defensive"
        shy["confidence"] = 0.55
        picks.append(shy)
    return picks


# Registry-style export (mirrors BOND_STRATEGIES pattern in bond_strategies.py)
BOND_YIELD_CURVE_INVERSION_STRATEGIES: dict[str, callable] = {
    "bond_yield_curve_inversion": bond_yield_curve_inversion,
}
