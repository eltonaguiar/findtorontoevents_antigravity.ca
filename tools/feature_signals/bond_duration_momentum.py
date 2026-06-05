#!/usr/bin/env python3
"""BOND duration momentum factor emitter.

Implements the persistent bond factor evidenced by:
- Ilmanen (2011) "Expected Returns" — duration premium
- Asness, Moskowitz, Pedersen (2013) "Value and Momentum Everywhere" —
  12-1 momentum works across asset classes including bonds
- Lee (1997) term premium structure

Sleeve name: `bond_duration_momentum` (intentionally NOT `bond_yield_momentum`
which appears in historical BLOCKED_SOURCE_SYSTEMS — name collision avoided).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_JSON = REPO / "audit_dashboard" / "data" / "bond_duration_momentum_signals.json"

DEFAULT_UNIVERSE = [
    "TLT", "IEF", "SHY", "TIP", "LQD", "HYG", "AGG", "BIL",
]

MOMENTUM_WEIGHT = 0.60
CARRY_WEIGHT = 0.40
EMIT_PERCENTILE_FLOOR = 0.75


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _z_score(values: list[float]) -> list[float]:
    if not values:
        return []
    n = len(values)
    mu = sum(values) / n
    var = sum((x - mu) ** 2 for x in values) / max(1, n - 1)
    sd = var ** 0.5
    if sd < 1e-12:
        return [0.0] * n
    return [(x - mu) / sd for x in values]


def _momentum_12_1(prices_series) -> float | None:
    if prices_series is None or len(prices_series) < 252:
        return None
    try:
        p12 = float(prices_series.iloc[-252])
        p1 = float(prices_series.iloc[-21])
        if p12 <= 0:
            return None
        return (p1 / p12) - 1.0
    except Exception:
        return None


def _carry_proxy(info: dict) -> float | None:
    for k in ("yield", "yieldFiveYearAverageDirect", "trailingAnnualDividendYield"):
        v = info.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def scan(universe: list[str] | None = None) -> dict:
    universe = universe or DEFAULT_UNIVERSE
    try:
        import yfinance as yf
    except ImportError:
        return {"generated_at": _utc_iso(), "error": "yfinance not installed", "picks": []}

    momenta: list[tuple[str, float]] = []
    carries: list[tuple[str, float]] = []
    errors: list[dict] = []
    for sym in universe:
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="2y", interval="1d", auto_adjust=True)
            mom = _momentum_12_1(hist["Close"] if "Close" in hist else None)
            info = ticker.info or {}
            carry = _carry_proxy(info)
            if mom is not None:
                momenta.append((sym, mom))
            if carry is not None:
                carries.append((sym, carry))
            if mom is None and carry is None:
                errors.append({"symbol": sym, "reason": "no_usable_data"})
        except Exception as exc:
            errors.append({"symbol": sym, "reason": str(exc)[:80]})

    if not momenta:
        return {"generated_at": _utc_iso(), "error": "no momentum data",
                "n_momentum": 0, "errors": errors, "picks": []}

    mom_z = dict(zip([s for s, _ in momenta], _z_score([v for _, v in momenta])))
    carry_z = dict(zip([s for s, _ in carries], _z_score([v for _, v in carries])))

    composites: list[tuple[str, float, float, float | None]] = []
    for sym in mom_z:
        m = mom_z[sym]
        c = carry_z.get(sym)
        composite = MOMENTUM_WEIGHT * m + (CARRY_WEIGHT * c if c is not None else 0.0)
        composites.append((sym, composite, m, c))
    composites.sort(key=lambda x: -x[1])

    if not composites:
        return {"generated_at": _utc_iso(), "error": "no composites", "picks": []}

    cutoff_idx = max(0, int(len(composites) * (1.0 - EMIT_PERCENTILE_FLOOR)))
    picks = []
    for i, (sym, comp, mz, cz) in enumerate(composites[:cutoff_idx + 1]):
        pct = 1.0 - i / max(1, len(composites))
        picks.append({
            "symbol": sym,
            "direction": "LONG",
            "composite_z": round(comp, 3),
            "momentum_z": round(mz, 3),
            "carry_z": round(cz, 3) if cz is not None else None,
            "carry_quality": "real" if cz is not None else "missing_proxy_only_mom",
            "percentile": round(pct, 3),
            "rationale": "Ilmanen duration premium + Asness-Moskowitz-Pedersen 12-1 momentum (top quartile)",
            "asset_class": "BOND",
            "horizon_days": 21,
            "production_enable": False,
        })

    return {
        "generated_at": _utc_iso(),
        "universe_size": len(universe),
        "n_with_momentum": len(momenta),
        "n_with_carry": len(carries),
        "n_composites": len(composites),
        "n_picks_emitted": len(picks),
        "weights": {"momentum": MOMENTUM_WEIGHT, "carry": CARRY_WEIGHT},
        "emit_percentile_floor": EMIT_PERCENTILE_FLOOR,
        "errors": errors,
        "picks": picks,
        "references": [
            "Ilmanen (2011) Expected Returns",
            "Asness, Moskowitz & Pedersen (2013) Value and Momentum Everywhere",
        ],
    }


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", help="comma-separated symbols")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    uni = args.universe.split(",") if args.universe else None
    out = scan(uni)
    if args.write:
        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUT_JSON.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print(f"wrote {OUT_JSON.relative_to(REPO)}")
    print(json.dumps({
        "n_picks": len(out.get("picks", [])),
        "top5": [p["symbol"] for p in out.get("picks", [])[:5]],
        "error": out.get("error"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
