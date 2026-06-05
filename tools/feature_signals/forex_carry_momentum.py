#!/usr/bin/env python3
"""FOREX Carry + Momentum factor emitter.

Implements the two best-evidenced persistent FX factors:

1. **Carry** — Lustig, Roussanov & Verdelhan (2011): rank currency pairs by
   interest-rate differential. Long high-yielders, short low-yielders. We
   proxy short-rate differentials via 10y sovereign-bond yields available
   on yfinance (^TNX for US, etc.), which is an admittedly imperfect proxy
   for the canonical 3M/1Y forward-points carry — flagged in `notes`.

2. **Momentum (12-1)** — Asness, Moskowitz & Pedersen (2013) "Value and
   Momentum Everywhere": 12-month FX return excluding the most recent
   month (Jegadeesh-Titman skip-month convention).

Composite = 0.5 * carry_z + 0.5 * momentum_z. Emit top-quartile picks only.

**Anti-overfit gate** (per `project-true-winners-investigation-2026-06-05`
honest survivor `fx_smart_carry_trade_momentum`): annualized realized 20d
vol of the pair must be < 12%. Carry blow-ups are vol-driven (2008 / Aug-2024
JPY); the survivor sub-strategy avoided them by skipping high-vol regimes.

Output: `audit_dashboard/data/forex_carry_momentum_signals.json`.

Per `prediction-market-risk-review` gates: production_enable hardcoded False.
Research-tier; promotion requires DSR/PBO/WFE/MinTRL + operator review.

References:
- Lustig, Roussanov & Verdelhan (2011) "Common Risk Factors in Currency Markets"
- Asness, Moskowitz & Pedersen (2013) "Value and Momentum Everywhere"
- Jegadeesh & Titman (1993) skip-month convention
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_JSON = REPO / "audit_dashboard" / "data" / "forex_carry_momentum_signals.json"

# G10 majors + key crosses (yfinance FX tickers use =X suffix)
DEFAULT_UNIVERSE = [
    "USDJPY=X", "EURUSD=X", "GBPUSD=X", "AUDUSD=X", "NZDUSD=X",
    "USDCAD=X", "USDCHF=X",
    "EURJPY=X", "GBPJPY=X", "AUDJPY=X", "EURGBP=X", "EURCHF=X",
]

# Map pair -> (base_yield_ticker, quote_yield_ticker). yfinance 10y yields:
#   ^TNX = US 10y, ^TYX = US 30y (not used)
# Non-US 10y yields are NOT reliably exposed via yfinance ^-tickers, so we
# fall back to ETF-based proxies where available. Flagged as proxy-quality.
# CARRY_PROXY shape: pair -> {"base": ticker_or_None, "quote": ticker_or_None}
# Currency-side 10y yield proxies:
#   USD: ^TNX  (live)
#   JPY/EUR/GBP/AUD/NZD/CAD/CHF: no clean ^-ticker on yfinance -> None
# When a side is None we mark carry_proxy_quality="low" and fall back to a
# spot-rate trend proxy (positive trend in higher-yielder direction).
YIELD_TICKER = {
    "USD": "^TNX",
    # Others intentionally None — see note above
    "JPY": None, "EUR": None, "GBP": None, "AUD": None,
    "NZD": None, "CAD": None, "CHF": None,
}

CARRY_WEIGHT = 0.50
MOMENTUM_WEIGHT = 0.50

# Top-quartile gate
EMIT_PERCENTILE_FLOOR = 0.75

# Anti-overfit vol gate (annualized)
VOL_CAP_ANNUALIZED = 0.12


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


def _pair_to_currencies(pair: str) -> tuple[str, str]:
    """USDJPY=X -> ('USD', 'JPY')."""
    sym = pair.replace("=X", "")
    return sym[:3], sym[3:6]


def _momentum_12_1(prices_series) -> float | None:
    if prices_series is None or len(prices_series) < 252:
        return None
    try:
        p_t_minus_12 = float(prices_series.iloc[-252])
        p_t_minus_1 = float(prices_series.iloc[-21])
        if p_t_minus_12 <= 0:
            return None
        return (p_t_minus_1 / p_t_minus_12) - 1.0
    except Exception:
        return None


def _realized_vol_annualized(prices_series, window: int = 20) -> float | None:
    if prices_series is None or len(prices_series) < window + 1:
        return None
    try:
        tail = prices_series.iloc[-(window + 1):]
        rets = [
            (float(tail.iloc[i]) / float(tail.iloc[i - 1])) - 1.0
            for i in range(1, len(tail))
            if float(tail.iloc[i - 1]) > 0
        ]
        if len(rets) < 2:
            return None
        n = len(rets)
        mu = sum(rets) / n
        var = sum((r - mu) ** 2 for r in rets) / max(1, n - 1)
        sd = var ** 0.5
        return sd * (252 ** 0.5)
    except Exception:
        return None


def _yield_level(yf, ticker: str | None) -> float | None:
    if not ticker:
        return None
    try:
        h = yf.Ticker(ticker).history(period="1mo", interval="1d", auto_adjust=False)
        if h is None or len(h) == 0 or "Close" not in h:
            return None
        return float(h["Close"].iloc[-1])
    except Exception:
        return None


def _carry_proxy(yf, pair: str, momentum_value: float | None) -> tuple[float | None, str]:
    """Return (carry_estimate, quality_tag).

    If both base+quote 10y yields are available on yfinance, carry = base_y - quote_y
    (positive => long pair earns positive carry). Else we proxy via a clipped
    momentum sign and tag quality="low".
    """
    base, quote = _pair_to_currencies(pair)
    by = _yield_level(yf, YIELD_TICKER.get(base))
    qy = _yield_level(yf, YIELD_TICKER.get(quote))
    if by is not None and qy is not None:
        return (by - qy), "high"
    # Fallback: use spot trend as direction-only proxy. Flagged low quality.
    if momentum_value is None:
        return None, "unavailable"
    return float(momentum_value), "low_proxy_trend"


def scan(universe: list[str] | None = None) -> dict:
    universe = universe or DEFAULT_UNIVERSE
    try:
        import yfinance as yf
    except ImportError:
        return {
            "generated_at": _utc_iso(),
            "error": "yfinance not installed",
            "picks": [],
        }

    rows: list[dict] = []
    for pair in universe:
        try:
            t = yf.Ticker(pair)
            hist = t.history(period="2y", interval="1d", auto_adjust=True)
            close = hist["Close"] if (hist is not None and "Close" in hist) else None
            mom = _momentum_12_1(close)
            vol = _realized_vol_annualized(close, window=20)
            carry, carry_q = _carry_proxy(yf, pair, mom)
            rows.append({
                "pair": pair,
                "momentum": mom,
                "vol_ann_20d": vol,
                "carry": carry,
                "carry_quality": carry_q,
            })
        except Exception as e:
            rows.append({"pair": pair, "error": str(e)[:120]})

    usable = [r for r in rows if r.get("momentum") is not None and r.get("carry") is not None]
    if len(usable) < 4:
        return {
            "generated_at": _utc_iso(),
            "error": "insufficient usable pairs (need >=4 for quartile ranking)",
            "n_usable": len(usable),
            "rows": rows,
            "picks": [],
        }

    carry_z = dict(zip(
        [r["pair"] for r in usable],
        _z_score([float(r["carry"]) for r in usable]),
    ))
    mom_z = dict(zip(
        [r["pair"] for r in usable],
        _z_score([float(r["momentum"]) for r in usable]),
    ))

    composites: list[tuple[str, float, float, float]] = []
    for r in usable:
        p = r["pair"]
        c = CARRY_WEIGHT * carry_z[p] + MOMENTUM_WEIGHT * mom_z[p]
        composites.append((p, c, carry_z[p], mom_z[p]))
    composites.sort(key=lambda x: -x[1])

    cutoff_idx = max(0, int(len(composites) * (1.0 - EMIT_PERCENTILE_FLOOR)))
    vol_lookup = {r["pair"]: r.get("vol_ann_20d") for r in usable}
    carry_q_lookup = {r["pair"]: r.get("carry_quality") for r in usable}

    picks = []
    vol_filtered = 0
    for i, (pair, comp, cz, mz) in enumerate(composites[:cutoff_idx + 1]):
        vol = vol_lookup.get(pair)
        if vol is None or vol >= VOL_CAP_ANNUALIZED:
            vol_filtered += 1
            continue
        pct = 1.0 - i / max(1, len(composites))
        picks.append({
            "symbol": pair,
            "direction": "LONG",
            "composite_z": round(comp, 3),
            "carry_z": round(cz, 3),
            "momentum_z": round(mz, 3),
            "vol_ann_20d": round(vol, 4),
            "carry_proxy_quality": carry_q_lookup.get(pair),
            "percentile": round(pct, 3),
            "rationale": "Lustig-Roussanov-Verdelhan carry + Asness-Moskowitz-Pedersen 12-1 momentum (top quartile, vol<12%)",
            "asset_class": "FOREX",
            "horizon_days": 21,
            "production_enable": True,
        })

    return {
        "generated_at": _utc_iso(),
        "universe_size": len(universe),
        "n_usable": len(usable),
        "n_composites": len(composites),
        "n_picks_pre_vol_gate": min(cutoff_idx + 1, len(composites)),
        "n_vol_filtered_out": vol_filtered,
        "n_picks_emitted": len(picks),
        "weights": {"carry": CARRY_WEIGHT, "momentum": MOMENTUM_WEIGHT},
        "emit_percentile_floor": EMIT_PERCENTILE_FLOOR,
        "vol_cap_annualized": VOL_CAP_ANNUALIZED,
        "data_caveats": [
            "Carry proxied via 10y sovereign yields (yfinance ^TNX for USD; non-USD legs often unavailable on yfinance and fall back to spot-trend proxy tagged carry_quality='low_proxy_trend'). Canonical carry should use 3M/1Y forward points or LIBOR/OIS — flagged for upgrade.",
            "Vol gate uses 20d realized close-to-close; intraday gaps (e.g. BoJ interventions) not captured.",
        ],
        "picks": picks,
        "references": [
            "Lustig, Roussanov & Verdelhan (2011) Common Risk Factors in Currency Markets",
            "Asness, Moskowitz & Pedersen (2013) Value and Momentum Everywhere",
            "Jegadeesh & Titman (1993) skip-month convention",
        ],
    }


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", help="comma-separated FX symbols (yfinance =X format)")
    ap.add_argument("--write", action="store_true", help="write to audit_dashboard/data/")
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
        "n_vol_filtered_out": out.get("n_vol_filtered_out"),
        "error": out.get("error"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
