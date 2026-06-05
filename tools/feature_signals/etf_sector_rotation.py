#!/usr/bin/env python3
"""ETF Sector Rotation + Momentum emitter.

Implements two complementary tactical-allocation models:

1. **Absolute Momentum (Faber 2007)** — only hold risky assets when their
   12-1 month return exceeds the risk-free rate. Below threshold, rotate to
   cash (SHY) as a defensive posture. This is the canonical timing filter
   from Faber's "Quantitative Approach to Tactical Asset Allocation".

2. **Relative Momentum (Antonacci 2014 Dual Momentum)** — within the sector
   ETF universe, rank by 6-month return and long the top quartile.

Composite: equal-weight long-only top-quartile basket of sector ETFs whose
12-1 absolute momentum exceeds the risk-free rate. Monthly rebalance horizon
(21 trading days). If absolute momentum gate fails for the whole universe,
emit SHY (defensive cash proxy) only.

Universe: 11 SPDR sector ETFs (XLK/XLF/XLV/XLE/XLP/XLY/XLI/XLB/XLU/XLRE/XLC),
broad-market (SPY/QQQ/IWM), and macro alternatives (GLD/TLT/SHY).

Per `prediction-market-risk-review` + memory project-etf-pilot-day1-2026-06-02:
production_enable hardcoded False. Complementary (not duplicate) to the
existing `etf_verified_dual_momentum` lab-Tier-2 candidate — different signal
horizon (6m relative vs lab's variant) + broader sector universe.

Anti-fabrication: per feedback-subagent-stat-fabrication-2026-06-05, if
yfinance returns no data for a symbol, the symbol is reported with an error
flag rather than imputed. No returns are ever invented.

References:
- Faber (2007) "A Quantitative Approach to Tactical Asset Allocation"
- Antonacci (2014) "Dual Momentum Investing"
- Jegadeesh & Titman (1993) cross-sectional momentum foundation
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_JSON = REPO / "audit_dashboard" / "data" / "etf_sector_rotation_signals.json"

# Sector ETFs (SPDR Select Sector) — the rotation universe
SECTOR_ETFS = [
    "XLK",   # Technology
    "XLF",   # Financials
    "XLV",   # Healthcare
    "XLE",   # Energy
    "XLP",   # Consumer Staples
    "XLY",   # Consumer Discretionary
    "XLI",   # Industrials
    "XLB",   # Materials
    "XLU",   # Utilities
    "XLRE",  # Real Estate
    "XLC",   # Communications
]

# Broad-market + macro alternatives for diversification
BROAD_ETFS = ["SPY", "QQQ", "IWM"]
MACRO_ETFS = ["GLD", "TLT"]  # gold, long bonds — alt risk-on/risk-off signals
CASH_PROXY = "SHY"  # defensive position when absolute momentum fails

DEFAULT_UNIVERSE = SECTOR_ETFS + BROAD_ETFS + MACRO_ETFS + [CASH_PROXY]

# Risk-free rate proxy (3-month T-bill yield, currently ~4-5% — Faber threshold).
# Conservative annualized hurdle; tunable via CLI.
RISK_FREE_ANNUAL = 0.045  # 4.5% — within ^TNX 3m proxy band per spec

# Antonacci relative momentum: top quartile = 25th percentile and above
TOP_QUARTILE_FLOOR = 0.75

# Rebalance horizon (Faber/Antonacci canonical monthly cadence)
HORIZON_DAYS = 21


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _momentum_12_1(prices_series) -> float | None:
    """Trailing 12m return excluding the last month (Faber/Antonacci absolute mom)."""
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


def _momentum_6m(prices_series) -> float | None:
    """Trailing 6m return (Antonacci relative momentum ranking signal)."""
    if prices_series is None or len(prices_series) < 126:
        return None
    try:
        p_t_minus_6 = float(prices_series.iloc[-126])
        p_t = float(prices_series.iloc[-1])
        if p_t_minus_6 <= 0:
            return None
        return (p_t / p_t_minus_6) - 1.0
    except Exception:
        return None


def scan(universe: list[str] | None = None,
         risk_free_annual: float = RISK_FREE_ANNUAL) -> dict:
    universe = universe or DEFAULT_UNIVERSE
    try:
        import yfinance as yf
    except ImportError:
        return {
            "generated_at": _utc_iso(),
            "error": "yfinance not installed",
            "picks": [],
        }

    # Faber absolute momentum hurdle: annualized RF → 11-month equivalent
    # (12-1 mom is approximately 11 months of return)
    rf_hurdle = (1.0 + risk_free_annual) ** (11.0 / 12.0) - 1.0

    abs_mom: dict[str, float] = {}
    rel_mom: dict[str, float] = {}
    errors: list[dict] = []

    for sym in universe:
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="2y", interval="1d", auto_adjust=True)
            if hist is None or hist.empty or "Close" not in hist:
                errors.append({"symbol": sym, "error": "no price data"})
                continue
            closes = hist["Close"]
            m12 = _momentum_12_1(closes)
            m6 = _momentum_6m(closes)
            if m12 is None or m6 is None:
                errors.append({"symbol": sym, "error": "insufficient history"})
                continue
            abs_mom[sym] = m12
            rel_mom[sym] = m6
        except Exception as e:
            errors.append({"symbol": sym, "error": f"{type(e).__name__}: {e}"})
            continue

    if not abs_mom:
        return {
            "generated_at": _utc_iso(),
            "error": "no usable data",
            "errors": errors,
            "picks": [],
        }

    # Apply Faber absolute momentum gate: only sectors/broad ETFs with
    # 12-1 momentum > RF qualify. Macro/cash always candidates separately.
    risky_universe = [s for s in abs_mom if s in (SECTOR_ETFS + BROAD_ETFS + MACRO_ETFS)]
    qualified = [s for s in risky_universe if abs_mom[s] > rf_hurdle]

    picks = []

    if not qualified:
        # Defensive: emit cash proxy only (Faber rotation rule)
        if CASH_PROXY in abs_mom:
            picks.append({
                "symbol": CASH_PROXY,
                "direction": "LONG",
                "weight": 1.0,
                "absolute_momentum_12_1": round(abs_mom[CASH_PROXY], 4),
                "relative_momentum_6m": round(rel_mom.get(CASH_PROXY, 0.0), 4),
                "percentile": 1.0,
                "rationale": ("Faber 2007 defensive cash position — no risky ETF "
                              "cleared absolute momentum hurdle"),
                "asset_class": "ETF",
                "horizon_days": HORIZON_DAYS,
                "production_enable": False,
            })
        gate_status = "DEFENSIVE_CASH"
    else:
        # Antonacci relative momentum: rank qualified by 6m return, take top quartile
        ranked = sorted(qualified, key=lambda s: -rel_mom[s])
        n_q = len(ranked)
        # Top quartile cutoff: at least 1, ceil(25% of qualified)
        n_keep = max(1, -(-n_q // 4))  # ceil(n_q/4)
        top = ranked[:n_keep]
        equal_weight = 1.0 / len(top)
        for i, sym in enumerate(top):
            pct = 1.0 - (i / max(1, n_q))
            picks.append({
                "symbol": sym,
                "direction": "LONG",
                "weight": round(equal_weight, 4),
                "absolute_momentum_12_1": round(abs_mom[sym], 4),
                "relative_momentum_6m": round(rel_mom[sym], 4),
                "percentile": round(pct, 3),
                "rationale": ("Antonacci 2014 Dual Momentum: passed Faber absolute "
                              "momentum (12-1 > RF) + top-quartile 6m relative momentum"),
                "asset_class": "ETF",
                "horizon_days": HORIZON_DAYS,
                "production_enable": False,
            })
        gate_status = "RISK_ON"

    return {
        "generated_at": _utc_iso(),
        "universe_size": len(universe),
        "n_with_data": len(abs_mom),
        "n_errors": len(errors),
        "errors": errors,
        "risk_free_annual": risk_free_annual,
        "rf_hurdle_11m_equivalent": round(rf_hurdle, 4),
        "gate_status": gate_status,
        "n_qualified_absolute": len(qualified) if qualified else 0,
        "n_picks_emitted": len(picks),
        "top_quartile_floor": TOP_QUARTILE_FLOOR,
        "picks": picks,
        "references": [
            "Faber (2007) A Quantitative Approach to Tactical Asset Allocation",
            "Antonacci (2014) Dual Momentum Investing",
            "Jegadeesh & Titman (1993) Returns to Buying Winners and Selling Losers",
        ],
    }


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", help="comma-separated symbols (default: built-in)")
    ap.add_argument("--risk-free", type=float, default=RISK_FREE_ANNUAL,
                    help=f"annualized risk-free rate (default: {RISK_FREE_ANNUAL})")
    ap.add_argument("--write", action="store_true",
                    help="write to audit_dashboard/data/")
    args = ap.parse_args()
    uni = args.universe.split(",") if args.universe else None
    out = scan(uni, risk_free_annual=args.risk_free)
    if args.write:
        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUT_JSON.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print(f"wrote {OUT_JSON.relative_to(REPO)}")
    print(json.dumps({
        "gate_status": out.get("gate_status"),
        "n_picks": len(out.get("picks", [])),
        "picks": [(p["symbol"], p.get("weight")) for p in out.get("picks", [])],
        "n_errors": out.get("n_errors", 0),
        "error": out.get("error"),
    }, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
