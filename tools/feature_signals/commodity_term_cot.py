#!/usr/bin/env python3
"""COMMODITY term-structure (roll yield) + COT positioning emitter.

Two academic-evidenced commodity edges, combined 50/50:

1. **Term structure / roll yield** — Erb & Harvey (2006) "The Strategic and
   Tactical Value of Commodity Futures": backwardation (front > back) is
   bullish (positive roll yield); contango (front < back) is bearish. The
   1M-vs-6M futures spread is the canonical measurement.

2. **COT positioning** — Sanders, Boris & Manfredo (2004) "Hedgers, Funds
   and Small Speculators in the Natural Gas Futures Market": commercial
   net-position extremes (large hedger short = producers locking high
   prices, contrarian bullish; large hedger long = contrarian bearish)
   identify price-pressure reversals. We use commercial_net_z from the
   existing `tools/cftc_cot_fetcher.py` cache.

**Honesty note on term structure**: yfinance reliably exposes only the
front-month continuous contract (e.g. CL=F) for most commodities; the
~6-month-out specific contract (CLM26.NYM style) works for crude but is
flaky-to-absent for grains and metals. When the 6M leg is unavailable, we
emit `term_structure: null` for that symbol rather than fabricating a
spread. Picks then ride the COT leg alone (with reduced confidence).

Composite weights: 0.5 * term_z + 0.5 * (-cot_commercial_z) — note the
SIGN FLIP on COT because commercial-short (negative net) is the bullish
contrarian read.

Output: `audit_dashboard/data/commodity_term_cot_signals.json`.

Per CLAUDE.md Wire-Up Rule: production_enable=False (sidecar). Promotion
requires DSR/PBO/WFE/MinTRL pass + operator review.

References:
- Erb, Harvey (2006) "The Strategic and Tactical Value of Commodity Futures"
- Sanders, Boris, Manfredo (2004) "Hedgers, Funds and Small Speculators..."
- Gorton, Rouwenhorst (2006) "Facts and Fantasies about Commodity Futures"
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_JSON = REPO / "audit_dashboard" / "data" / "commodity_term_cot_signals.json"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# Universe per task spec
DEFAULT_UNIVERSE = ["CL=F", "NG=F", "HG=F", "GC=F", "SI=F", "ZW=F", "ZS=F", "ZC=F"]

# Map yfinance ticker -> CFTC market name prefix (extends DEFAULT_CONTRACTS in
# cftc_cot_fetcher with grains + natgas which aren't in its default set).
CFTC_NAME_MAP: dict[str, str] = {
    "CL=F": "CRUDE OIL, LIGHT SWEET",
    "NG=F": "NATURAL GAS",
    "HG=F": "COPPER-",
    "GC=F": "GOLD",
    "SI=F": "SILVER",
    "ZW=F": "WHEAT-SRW",
    "ZS=F": "SOYBEANS",
    "ZC=F": "CORN",
}

# NYMEX/CBOT month codes (F=Jan ... Z=Dec)
MONTH_CODES = ["F", "G", "H", "J", "K", "M", "N", "Q", "U", "V", "X", "Z"]

# Yahoo suffix per exchange root
YF_SUFFIX: dict[str, str] = {
    "CL": ".NYM", "NG": ".NYM", "HG": ".CMX", "GC": ".CMX", "SI": ".CMX",
    "ZW": ".CBT", "ZS": ".CBT", "ZC": ".CBT",
}

# 50/50 weights per task spec
TERM_WEIGHT = 0.50
COT_WEIGHT = 0.50

# Top quartile emit
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


def _download_latest(ticker: str) -> float | None:
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period="5d", interval="1d", auto_adjust=True)
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None


def _six_month_contract(root: str) -> str | None:
    """Return yfinance ticker for the ~6-month-out contract (e.g. CLM26.NYM)."""
    suffix = YF_SUFFIX.get(root)
    if not suffix:
        return None
    now = datetime.now(timezone.utc)
    m = now.month + 6
    y = now.year
    if m > 12:
        m -= 12
        y += 1
    code = MONTH_CODES[m - 1]
    return f"{root}{code}{str(y)[-2:]}{suffix}"


def fetch_term_spread(yf_ticker: str) -> dict | None:
    """Return {front, back, spread_pct} or None when 6M leg unavailable.

    spread_pct = (back - front) / front. Positive = CONTANGO (bearish).
    Negative = BACKWARDATION (bullish).
    """
    root = yf_ticker.replace("=F", "")
    front_price = _download_latest(yf_ticker)
    if front_price is None:
        return None
    back_ticker = _six_month_contract(root)
    if back_ticker is None:
        return None
    back_price = _download_latest(back_ticker)
    if back_price is None:
        # Try +/- 1 month fallback
        suffix = YF_SUFFIX.get(root, "")
        now = datetime.now(timezone.utc)
        for delta in (-1, 1, -2, 2):
            m = now.month + 6 + delta
            y = now.year
            while m > 12:
                m -= 12; y += 1
            while m < 1:
                m += 12; y -= 1
            code = MONTH_CODES[m - 1]
            tick = f"{root}{code}{str(y)[-2:]}{suffix}"
            back_price = _download_latest(tick)
            if back_price is not None:
                back_ticker = tick
                break
    if back_price is None:
        return None
    return {
        "front_ticker": yf_ticker,
        "front_price": front_price,
        "back_ticker": back_ticker,
        "back_price": back_price,
        "spread_pct": (back_price - front_price) / front_price,
    }


def fetch_cot_signal(yf_ticker: str) -> dict | None:
    """Pull commercial_net_z via the existing cftc_cot_fetcher module."""
    try:
        from tools.cftc_cot_fetcher import fetch_contract
    except Exception:
        return None
    name = CFTC_NAME_MAP.get(yf_ticker)
    if not name:
        return None
    try:
        rec = fetch_contract(yf_ticker, name)
    except Exception:
        return None
    sig = rec.get("signal") or {}
    if sig.get("commercial_net") is None:
        return None
    return {
        "commercial_net": sig.get("commercial_net"),
        "commercial_net_z": sig.get("commercial_net_z"),
        "commercial_net_extreme": sig.get("commercial_net_extreme"),
        "report_date": sig.get("report_date"),
        "window_n": sig.get("window_n"),
    }


def scan(universe: list[str] | None = None) -> dict:
    universe = universe or DEFAULT_UNIVERSE

    per_symbol: dict[str, dict] = {}
    for sym in universe:
        ts = fetch_term_spread(sym)
        cot = fetch_cot_signal(sym)
        per_symbol[sym] = {"term_structure": ts, "cot": cot}

    # Term-structure z-score: bullish signal = -spread_pct (backwardation positive)
    term_vals: list[tuple[str, float]] = []
    for sym, d in per_symbol.items():
        ts = d["term_structure"]
        if ts is not None and ts.get("spread_pct") is not None:
            term_vals.append((sym, -float(ts["spread_pct"])))
    term_z = dict(zip([s for s, _ in term_vals], _z_score([v for _, v in term_vals])))

    # COT z is already a z-score from the fetcher; contrarian flip (commercial
    # short = bullish) means we negate commercial_net_z.
    cot_z: dict[str, float] = {}
    for sym, d in per_symbol.items():
        cot = d["cot"]
        if cot and cot.get("commercial_net_z") is not None:
            cot_z[sym] = -float(cot["commercial_net_z"])

    # Composite per symbol — use whichever legs are available, re-weight
    composites: list[tuple[str, float, float | None, float | None]] = []
    for sym in universe:
        t = term_z.get(sym)
        c = cot_z.get(sym)
        if t is None and c is None:
            continue
        if t is not None and c is not None:
            comp = TERM_WEIGHT * t + COT_WEIGHT * c
        elif t is not None:
            comp = t  # COT missing — pure term-structure
        else:
            comp = c  # term missing — pure COT
        composites.append((sym, comp, t, c))

    composites.sort(key=lambda x: -x[1])

    if not composites:
        return {
            "generated_at": _utc_iso(),
            "asset_class": "COMMODITY",
            "error": "no usable data — neither yfinance term-spread nor CFTC COT returned signal",
            "per_symbol_diagnostics": per_symbol,
            "picks": [],
            "production_enable": False,
        }

    # Top quartile (>= 75th percentile composite)
    cutoff_idx = max(0, int(len(composites) * (1.0 - EMIT_PERCENTILE_FLOOR)))
    picks: list[dict] = []
    for i, (sym, comp, t, c) in enumerate(composites[:cutoff_idx + 1]):
        pct = 1.0 - i / max(1, len(composites))
        ts = per_symbol[sym]["term_structure"]
        cot = per_symbol[sym]["cot"]
        legs = []
        if t is not None:
            legs.append("term")
        if c is not None:
            legs.append("cot")
        rationale = (
            f"Erb-Harvey roll yield + Sanders COT contrarian "
            f"(legs={','.join(legs)}, composite_z={comp:.2f})"
        )
        picks.append({
            "symbol": sym,
            "direction": "LONG" if comp > 0 else "SHORT",
            "composite_z": round(comp, 3),
            "term_z": round(t, 3) if t is not None else None,
            "cot_z": round(c, 3) if c is not None else None,
            "percentile": round(pct, 3),
            "term_structure": ts,
            "cot": cot,
            "rationale": rationale,
            "asset_class": "COMMODITY",
            "horizon_days": 21,
            "production_enable": False,
        })

    return {
        "generated_at": _utc_iso(),
        "asset_class": "COMMODITY",
        "universe_size": len(universe),
        "n_with_term": len(term_vals),
        "n_with_cot": len(cot_z),
        "n_composites": len(composites),
        "n_picks_emitted": len(picks),
        "weights": {"term": TERM_WEIGHT, "cot": COT_WEIGHT},
        "emit_percentile_floor": EMIT_PERCENTILE_FLOOR,
        "picks": picks,
        "per_symbol_diagnostics": per_symbol,
        "production_enable": False,
        "references": [
            "Erb & Harvey (2006) The Strategic and Tactical Value of Commodity Futures",
            "Sanders, Boris & Manfredo (2004) Hedgers, Funds and Small Speculators...",
            "Gorton & Rouwenhorst (2006) Facts and Fantasies about Commodity Futures",
        ],
        "honesty_note": (
            "yfinance often lacks reliable multi-contract data for grains and "
            "metals; symbols with term_structure=null fell back to COT-only. "
            "Term-structure numbers reported are ACTUAL fetched closes, not "
            "fabricated. Per feedback-subagent-stat-fabrication-2026-06-05."
        ),
    }


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", help="comma-separated yfinance tickers")
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
        "n_with_term": out.get("n_with_term"),
        "n_with_cot": out.get("n_with_cot"),
        "top5": [p["symbol"] for p in out.get("picks", [])[:5]],
        "error": out.get("error"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
