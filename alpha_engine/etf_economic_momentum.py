"""ETF Economic Momentum strategy.

Source: ``reports/edge_research_synthesis_2026_05_12.md`` (Grok-4 idea #2).
Expected: PF 1.65, 12h horizon, FRED-driven macro overlay on liquid ETFs.

Per CLAUDE.md Wire-Up Rule: this is OPT-IN sidecar, default OFF behind
``ETF_ECONOMIC_MOMENTUM_ENABLED=1``. No production caller wires it yet;
``config.py`` family registration is deferred to the wire-up PR.

Logic:
  LONG when ISM (NAPM) > 50 AND M2 YoY > 0 AND GDP momentum z-score > 0.5.
  SHORT when ISM (NAPM) < 50 AND GDP momentum z-score < -0.5.
  No signal in the neutral band.

Universe: SPY, QQQ, IWM, EFA, EEM, XLF, XLK, XLE.
Confidence: 0.55-0.75, scaled by macro signal strength.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger("etf_economic_momentum")

STRATEGY_NAME = "etf_economic_momentum"
ETF_UNIVERSE: tuple[str, ...] = (
    "SPY", "QQQ", "IWM", "EFA", "EEM", "XLF", "XLK", "XLE",
)

ISM_LONG_THRESHOLD = 50.0
ISM_SHORT_THRESHOLD = 50.0
GDP_LONG_Z = 0.5
GDP_SHORT_Z = -0.5

CONFIDENCE_FLOOR = 0.55
CONFIDENCE_CEIL = 0.75


def is_enabled() -> bool:
    """Honor ETF_ECONOMIC_MOMENTUM_ENABLED env. Default OFF."""
    return os.environ.get("ETF_ECONOMIC_MOMENTUM_ENABLED", "0").strip().lower() in (
        "1", "true", "yes", "on",
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _scale_confidence(z_abs: float, m2_yoy: float | None) -> float:
    """Map signal strength to ``[CONFIDENCE_FLOOR, CONFIDENCE_CEIL]``."""
    base = CONFIDENCE_FLOOR
    # z up to 2 standard deviations adds up to +0.15
    base += min(0.15, max(0.0, (z_abs - 0.5) * 0.10))
    if m2_yoy is not None and m2_yoy > 0:
        base += min(0.05, m2_yoy * 0.5)  # small M2 expansion kicker
    return round(max(CONFIDENCE_FLOOR, min(CONFIDENCE_CEIL, base)), 2)


def _build_pick(symbol: str, direction: str, *, confidence: float, reason: str,
                extras: dict[str, Any]) -> dict[str, Any]:
    return {
        "strategy": STRATEGY_NAME,
        "symbol": symbol,
        "category": "etf",
        "signal_type": direction,
        "confidence": confidence,
        "reason": reason,
        "timeframe": "12h",
        "extra": extras,
        "timestamp": _now_iso(),
    }


def evaluate_macro(
    *,
    fred_module: Any | None = None,
) -> dict[str, Any]:
    """Pull ISM (NAPM), M2 YoY, GDP momentum z-score from FRED.

    ``fred_module`` injectable for tests. Returns dict with raw values +
    a ``signal`` field in ``{'LONG', 'SHORT', 'NEUTRAL'}``.
    """
    if fred_module is None:
        from tools import fred_data_fetcher as fred_module  # type: ignore

    napm_rec = fred_module.fetch_series("NAPM")
    napm_obs = napm_rec.get("observations") or []
    ism_value: float | None = None
    if napm_obs:
        try:
            ism_value = float(sorted(napm_obs, key=lambda r: r["date"])[-1]["value"])
        except (KeyError, TypeError, ValueError):
            ism_value = None

    m2_yoy = fred_module.compute_yoy_growth("M2SL")
    gdp_z = fred_module.compute_momentum_zscore("GDPC1", lookback_days=4 * 365)

    signal = "NEUTRAL"
    if ism_value is not None and gdp_z is not None:
        if (ism_value > ISM_LONG_THRESHOLD
                and (m2_yoy is None or m2_yoy > 0)
                and gdp_z > GDP_LONG_Z):
            signal = "LONG"
        elif ism_value < ISM_SHORT_THRESHOLD and gdp_z < GDP_SHORT_Z:
            signal = "SHORT"

    return {
        "ism": ism_value,
        "m2_yoy": m2_yoy,
        "gdp_momentum_z": gdp_z,
        "signal": signal,
    }


def generate_picks(
    *,
    universe: tuple[str, ...] = ETF_UNIVERSE,
    fred_module: Any | None = None,
    macro_evaluator: Callable[..., dict[str, Any]] | None = None,
    force: bool = False,
) -> list[dict[str, Any]]:
    """Produce LONG/SHORT picks for the ETF universe based on macro regime.

    Returns ``[]`` when the env gate is OFF (unless ``force=True``) or when
    the macro regime is NEUTRAL / data is missing.
    """
    if not force and not is_enabled():
        logger.info("ETF_ECONOMIC_MOMENTUM_ENABLED not set; returning [].")
        return []

    evaluator = macro_evaluator or evaluate_macro
    macro = evaluator(fred_module=fred_module)
    direction = macro.get("signal")
    if direction not in ("LONG", "SHORT"):
        return []

    gdp_z = macro.get("gdp_momentum_z")
    if gdp_z is None:
        return []
    confidence = _scale_confidence(abs(float(gdp_z)), macro.get("m2_yoy"))

    side = "BUY" if direction == "LONG" else "SELL"
    ism = macro.get("ism")
    m2 = macro.get("m2_yoy")
    ism_txt = f"{ism:.1f}" if ism is not None else "N/A"
    m2_txt = f"{m2:+.1%}" if m2 is not None else "N/A"
    reason = (
        f"Macro regime {direction}: ISM={ism_txt}, "
        f"GDP z={gdp_z:+.2f}, M2 YoY={m2_txt}"
    )

    picks: list[dict[str, Any]] = []
    for symbol in universe:
        picks.append(_build_pick(
            symbol,
            side,
            confidence=confidence,
            reason=reason,
            extras={
                "ism": ism,
                "m2_yoy": m2,
                "gdp_momentum_z": gdp_z,
                "regime": direction,
            },
        ))
    return picks


if __name__ == "__main__":  # pragma: no cover
    import json
    out = generate_picks(force=True)
    print(json.dumps({"n_picks": len(out), "first": out[:1]}, indent=2, default=str))
