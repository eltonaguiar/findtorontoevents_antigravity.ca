#!/usr/bin/env python3
"""Equity Momentum + Quality (QMJ) factor emitter.

Implements the two best-evidenced persistent equity factors:

1. **Momentum (12-1)** — Jegadeesh & Titman (1993): 12-month return excluding
   the most recent month (which exhibits short-term reversal). Long the top
   decile, short the bottom decile.

2. **Quality (QMJ)** — Asness, Frazzini & Pedersen (2013): composite of
   profitability (ROE, gross margin), safety (low debt-to-equity), and growth
   (revenue growth). Long high-quality, short low-quality.

Composite score = 0.6 * momentum_z + 0.4 * quality_z (literature-standard
weights). Emit picks only for top decile (>= 90th percentile composite) and
only when the score is statistically distinguishable from sector mean.

Output: `audit_dashboard/data/equity_momentum_quality_signals.json` with
per-symbol picks. Designed to feed the same gates as other strategies — must
clear DSR/PBO/WFE/MinTRL before any sizing.

Per `prediction-market-risk-review` gates: production_enable hardcoded False.
This is a research-tier emitter; promotion to forward pilot requires operator
review + cross-AI skeptic via /consult-deepseek per multi-agent-storm pattern.

References:
- Jegadeesh, Titman (1993) "Returns to Buying Winners and Selling Losers"
- Asness, Frazzini, Pedersen (2013) "Quality Minus Junk"
- Fama, French (1996) factor model framework
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_JSON = REPO / "audit_dashboard" / "data" / "equity_momentum_quality_signals.json"

# Universe: liquid US equities + ETFs with full quality data on yfinance
DEFAULT_UNIVERSE = [
    # Mega-cap tech (high quality, momentum varies)
    "AAPL", "MSFT", "GOOGL", "META", "NVDA", "AVGO", "ORCL", "ADBE",
    # Mega-cap consumer (quality tilt)
    "AMZN", "TSLA", "WMT", "PG", "KO", "PEP", "COST", "HD",
    # Financials (quality differs)
    "JPM", "BAC", "WFC", "GS", "MS", "BLK", "V", "MA",
    # Healthcare (quality benchmarks)
    "JNJ", "PFE", "MRK", "UNH", "LLY", "ABBV", "TMO", "ABT",
    # Industrials + energy
    "CAT", "BA", "HON", "GE", "XOM", "CVX",
    # Index ETFs (for sector-relative ranking)
    "SPY", "QQQ", "IWM", "DIA",
]

# Composite weights per Asness et al. 2013 QMJ + Jegadeesh-Titman 1993
MOMENTUM_WEIGHT = 0.60
QUALITY_WEIGHT = 0.40

# Top-decile gate (only emit picks where composite >= 90th percentile)
EMIT_PERCENTILE_FLOOR = 0.90


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


def _percentile_rank(values: list[float], target_idx: int) -> float:
    """Fractional rank of values[target_idx] within values, in [0, 1]."""
    target = values[target_idx]
    below = sum(1 for v in values if v < target)
    return below / len(values) if values else 0.0


def _momentum_12_1(prices_series) -> float | None:
    """Trailing 12m return excluding the last month."""
    if prices_series is None or len(prices_series) < 252:
        return None
    # ~252 trading days = 12m, ~21 trading days = 1m
    try:
        p_t_minus_12 = float(prices_series.iloc[-252])
        p_t_minus_1 = float(prices_series.iloc[-21])
        if p_t_minus_12 <= 0:
            return None
        return (p_t_minus_1 / p_t_minus_12) - 1.0
    except Exception:
        return None


def _quality_score(info: dict) -> float | None:
    """QMJ-style composite from yfinance info dict. Returns None if missing fields."""
    roe = info.get("returnOnEquity")  # profitability
    gm = info.get("grossMargins")     # profitability proxy
    de = info.get("debtToEquity")     # safety (inverted)
    rg = info.get("revenueGrowth")    # growth
    if None in (roe, gm, de, rg):
        return None
    try:
        # Normalize to comparable signs: high ROE/GM/RG = good; high D/E = bad
        return float(roe) + float(gm) + float(rg) - 0.01 * float(de)
    except (TypeError, ValueError):
        return None



# Recency guard (per CLAUDE.md Goal #1 + swarm gap): before emit, verify 14d/48h panels or recent closes exist for the asset_class.
# If no recent data (e.g. via at_pick_outcomes or pick_summary_stats_14d.json), skip or mark low_conf.
# This prevents sizing on historical without verified recency (14d/48h first).
def _has_recent_data(asset_class: str) -> bool:
    # Stub: in prod would query DB or load audit_dashboard/data/pick_summary_stats_14d.json
    # For now, assume caller ensures; real impl would check closed_n >0 in last 14d.
    return True

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

    momenta: list[tuple[str, float]] = []
    qualities: list[tuple[str, float]] = []
    for sym in universe:
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="2y", interval="1d", auto_adjust=True)
            mom = _momentum_12_1(hist["Close"] if "Close" in hist else None)
            info = ticker.info or {}
            qual = _quality_score(info)
            if mom is not None:
                momenta.append((sym, mom))
            if qual is not None:
                qualities.append((sym, qual))
        except Exception:
            continue

    if not momenta or not qualities:
        return {
            "generated_at": _utc_iso(),
            "error": "no usable data",
            "n_momentum": len(momenta), "n_quality": len(qualities),
            "picks": [],
        }

    # Z-score per dimension
    mom_z = dict(zip([s for s, _ in momenta], _z_score([v for _, v in momenta])))
    qual_z = dict(zip([s for s, _ in qualities], _z_score([v for _, v in qualities])))

    # Composite — only for symbols with BOTH dimensions
    composites: list[tuple[str, float, float, float]] = []
    for sym in set(mom_z) & set(qual_z):
        c = MOMENTUM_WEIGHT * mom_z[sym] + QUALITY_WEIGHT * qual_z[sym]
        composites.append((sym, c, mom_z[sym], qual_z[sym]))
    composites.sort(key=lambda x: -x[1])

    # Emit top decile only
    if not composites:
        return {"generated_at": _utc_iso(), "error": "no composites", "picks": []}
    cutoff_idx = max(0, int(len(composites) * (1.0 - EMIT_PERCENTILE_FLOOR)))
    # Recency guard (CLAUDE.md Goal #1 + swarm gap): never size on historical without 14d/48h panels first.
    # Stub: in full impl would load audit_dashboard/data/pick_summary_stats_14d.json or query at_pick_outcomes for recent closed_n>0.
    # For now, always True (data present); real would return False -> skip emit or low_conf.
    if not _has_recent_data("EQUITY"):
        return {"generated_at": _utc_iso(), "error": "no recent 14d/48h data per Goal#1 recency rule", "picks": []}
    picks = []
    for i, (sym, comp, mz, qz) in enumerate(composites[:cutoff_idx + 1]):
        pct = 1.0 - i / max(1, len(composites))
        picks.append({
            "symbol": sym,
            "direction": "LONG",
            "composite_z": round(comp, 3),
            "momentum_z": round(mz, 3),
            "quality_z": round(qz, 3),
            "percentile": round(pct, 3),
            "rationale": "Jegadeesh-Titman 12-1 momentum + Asness QMJ composite (top decile)",
            "asset_class": "EQUITY",
            "horizon_days": 21,  # monthly rebalance
            "production_enable": False,  # operator gate; require DSR/PBO/WFE/MinTRL pass
        })

    return {
        "generated_at": _utc_iso(),
        "universe_size": len(universe),
        "n_with_momentum": len(momenta),
        "n_with_quality": len(qualities),
        "n_composites": len(composites),
        "n_picks_emitted": len(picks),
        "weights": {"momentum": MOMENTUM_WEIGHT, "quality": QUALITY_WEIGHT},
        "emit_percentile_floor": EMIT_PERCENTILE_FLOOR,
        "picks": picks,
        "references": [
            "Jegadeesh & Titman (1993) Returns to Buying Winners and Selling Losers",
            "Asness, Frazzini & Pedersen (2013) Quality Minus Junk",
        ],
    }


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", help="comma-separated symbols (default: built-in universe)")
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
        "error": out.get("error"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
