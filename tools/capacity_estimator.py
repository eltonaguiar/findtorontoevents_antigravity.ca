"""Almgren-Chriss capacity estimator — per-strategy USD capacity at zero edge.

Why this exists
---------------
Today the audit reports per-trade PnL, WR, Sharpe — but not the order
size at which the strategy's edge gets eaten by market impact. A 5%
edge that survives only at $1k notional is a hobby; the same edge at
$1M is a fund. Without a capacity column the audit cannot distinguish.

Almgren-Chriss square-root market impact:

    slippage_bps(Q) = lambda * sigma * sqrt(Q / ADV) * 10000

We solve for the order size Q at which the realised slippage equals the
strategy's after-cost expected edge in basis points:

    Q_capacity_usd = (after_cost_edge_bps / (lambda * sigma * 10000))^2 * ADV_usd

Inputs:
  - lambda    Almgren liquidity constant. Default 0.5 (matches
              `alpha_engine/slippage_model.py` DEFAULT_K).
  - sigma     Per-strategy realised volatility, daily fraction. Computed
              from per-pick ATR / entry_price * sqrt(252) where ATR
              available; falls back to per-asset-class realised PnL std
              when ATR is missing.
  - ADV_usd   30-day average daily dollar volume. Looked up via
              yfinance when the symbol is recognised; falls back to a
              per-asset-class default ADV from a small lookup.
  - edge_bps  Strategy's after-cost mean PnL in basis points (mean
              pnl_pct * 100).

If after_cost_edge_bps <= 0 (negative-edge strategy), capacity = 0
(can't trade size you don't have edge for).

Wiring status: OPT-IN SIDECAR. No production caller. A follow-up PR
adds a `capacity_usd` column on `audit_dashboard/template.html`.

Caveats
-------
1. yfinance ADV lookup is best-effort. When network is unavailable or
   the symbol unknown, we fall back to a per-asset-class default. The
   fallbacks (`tools/data/asset_class_default_adv.json` if present,
   else hard-coded) are conservative — likely understate true CRYPTO
   capacity by 3-10x.
2. Almgren-Chriss is a single-period impact model. It says nothing
   about temporary vs permanent impact splits, decay, or queue
   position. For institutional implementation use a multi-period
   model (Obizhaeva-Wang, Forsyth, etc.); this first cut is enough
   to surface "capacity << current AUM" red flags.
3. lambda = 0.5 is a reasonable default for retail-sized US equities
   per `alpha_engine/slippage_model.py:DEFAULT_K`. CRYPTO perps and
   FX both have higher effective lambda — adjust per asset class
   in a follow-up.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PICKS_PATH = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO_ROOT / "tools" / "data" / "capacity_estimator_results.json"
OUT_MD_DIR = REPO_ROOT / "reports"
DEFAULT_LAMBDA = 0.5
DEFAULT_MIN_N = 20
TRADING_DAYS = 252.0

# Per-asset-class fallback ADV in USD when yfinance lookup fails or is
# disabled. Conservative estimates — happy to be wrong on the low side.
FALLBACK_ADV_USD: dict[str, float] = {
    "CRYPTO": 5_000_000_000.0,    # $5B (mid-cap perp pair)
    "EQUITY": 200_000_000.0,      # $200M (mid-cap US stock)
    "ETF": 500_000_000.0,         # $500M (sector ETF)
    "FOREX": 1_000_000_000.0,     # $1B (G10 cross)
    "COMMODITY": 100_000_000.0,   # $100M (CME futures)
    "BOND": 100_000_000.0,
    "UNKNOWN": 100_000_000.0,
}


def _safe_float(x: Any) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return v


def per_class_realised_vol(picks: list[dict]) -> dict[str, float]:
    """Per-asset-class realised vol, daily-fraction units, computed from
    the std of pnl_pct/100 across all closed picks in that class.

    This is the fallback used when no per-pick ATR is available.
    """
    by_class: dict[str, list[float]] = defaultdict(list)
    for p in picks:
        pnl = _safe_float(p.get("pnl_pct"))
        if pnl is None:
            continue
        klass = (p.get("asset_class") or "UNKNOWN").upper()
        by_class[klass].append(pnl / 100.0)
    out: dict[str, float] = {}
    for klass, vals in by_class.items():
        if len(vals) < 2:
            out[klass] = 0.02  # 2% daily fallback
            continue
        mu = sum(vals) / len(vals)
        var = sum((v - mu) ** 2 for v in vals) / (len(vals) - 1)
        out[klass] = math.sqrt(max(var, 1e-12))
    return out


def estimate_strategy_sigma(picks: list[dict],
                            class_vol_fallback: dict[str, float]) -> float:
    """Per-strategy daily sigma. Uses ATR/price * sqrt(252) where ATR is
    available on at least 5 picks, otherwise the per-class realised vol
    fallback.
    """
    atr_estimates: list[float] = []
    klass = "UNKNOWN"
    for p in picks:
        atr = _safe_float(p.get("atr"))
        entry = _safe_float(p.get("entry_price"))
        klass = (p.get("asset_class") or klass).upper()
        if atr is not None and entry is not None and entry > 0:
            atr_estimates.append((atr / entry) * math.sqrt(TRADING_DAYS))
    if len(atr_estimates) >= 5:
        return float(sum(atr_estimates) / len(atr_estimates))
    return class_vol_fallback.get(klass, 0.02)


def lookup_adv_usd(symbol: str, asset_class: str,
                   adv_overrides: dict[str, float] | None = None) -> tuple[float, str]:
    """Return (ADV_usd, source_tag). yfinance lookup is intentionally
    optional — when offline or yfinance not installed, fall back.

    `adv_overrides` lets callers (tests + future per-symbol cache) inject
    deterministic values without touching the network.
    """
    klass = (asset_class or "UNKNOWN").upper()
    if adv_overrides and symbol in adv_overrides:
        return adv_overrides[symbol], f"override:{symbol}"
    try:
        import yfinance as yf  # type: ignore
        info = yf.Ticker(symbol).info or {}
        avg_vol = info.get("averageDailyVolume10Day") or info.get("averageVolume")
        last_price = info.get("regularMarketPrice") or info.get("currentPrice")
        if avg_vol and last_price:
            return float(avg_vol) * float(last_price), f"yfinance:{symbol}"
    except Exception:
        pass
    return FALLBACK_ADV_USD.get(klass, FALLBACK_ADV_USD["UNKNOWN"]), f"fallback:{klass}"


def capacity_usd(edge_bps: float, sigma: float, adv_usd: float,
                 lambda_const: float = DEFAULT_LAMBDA) -> float:
    """Capacity in USD where Almgren-Chriss slippage equals edge.

    capacity = (edge_bps / (lambda * sigma * 10000))^2 * ADV_usd
    """
    if edge_bps <= 0 or sigma <= 0 or adv_usd <= 0 or lambda_const <= 0:
        return 0.0
    denom = lambda_const * sigma * 10000.0
    if denom <= 0:
        return 0.0
    ratio = edge_bps / denom
    return float(ratio * ratio * adv_usd)


def estimate_strategy(picks: list[dict],
                       class_vol_fallback: dict[str, float],
                       lambda_const: float = DEFAULT_LAMBDA,
                       min_n: int = DEFAULT_MIN_N,
                       adv_overrides: dict[str, float] | None = None) -> dict | None:
    """Per-strategy capacity estimate. Returns None if n<min_n."""
    n = len(picks)
    if n < min_n:
        return None
    pnls = [_safe_float(p.get("pnl_pct")) for p in picks
            if _safe_float(p.get("pnl_pct")) is not None]
    if len(pnls) < min_n:
        return None
    mean_pnl_pct = sum(pnls) / len(pnls)
    edge_bps = mean_pnl_pct * 100.0  # pct -> bps

    # Pick a representative symbol for ADV lookup: the highest-frequency one
    sym_counts: dict[str, int] = defaultdict(int)
    for p in picks:
        sym = p.get("symbol")
        if sym:
            sym_counts[sym] += 1
    top_symbol = max(sym_counts, key=sym_counts.get) if sym_counts else ""
    klass = (picks[0].get("asset_class") if picks else "UNKNOWN") or "UNKNOWN"
    klass = klass.upper()

    sigma = estimate_strategy_sigma(picks, class_vol_fallback)
    adv_usd, adv_source = lookup_adv_usd(top_symbol, klass, adv_overrides)
    cap = capacity_usd(edge_bps, sigma, adv_usd, lambda_const)

    return {
        "n": int(len(picks)),
        "n_with_pnl": int(len(pnls)),
        "asset_class": klass,
        "top_symbol": top_symbol,
        "mean_pnl_pct": round(mean_pnl_pct, 6),
        "edge_bps": round(edge_bps, 4),
        "sigma_daily": round(sigma, 6),
        "adv_usd": round(adv_usd, 2),
        "adv_source": adv_source,
        "lambda": lambda_const,
        "capacity_usd": round(cap, 2),
        "capacity_bucket": _capacity_bucket(cap),
    }


def _capacity_bucket(usd: float) -> str:
    if usd <= 0:
        return "ZERO (negative-edge)"
    if usd < 100_000:
        return "TOY (<$100k)"
    if usd < 1_000_000:
        return "RETAIL ($100k-$1M)"
    if usd < 10_000_000:
        return "PROP ($1M-$10M)"
    if usd < 100_000_000:
        return "FUND ($10M-$100M)"
    return "INSTITUTIONAL (>$100M)"


def analyze_all(picks: list[dict],
                lambda_const: float = DEFAULT_LAMBDA,
                min_n: int = DEFAULT_MIN_N,
                adv_overrides: dict[str, float] | None = None) -> dict:
    by_strategy: dict[str, list[dict]] = defaultdict(list)
    for p in picks:
        by_strategy[p.get("strategy") or "unknown"].append(p)
    class_vol_fallback = per_class_realised_vol(picks)

    out: list[dict] = []
    for strat, sub in by_strategy.items():
        r = estimate_strategy(sub, class_vol_fallback, lambda_const, min_n,
                              adv_overrides)
        if r is None:
            continue
        r["strategy"] = strat
        out.append(r)
    out.sort(key=lambda r: -r["capacity_usd"])

    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "config": {"lambda": lambda_const, "min_n": min_n,
                   "fallback_adv_usd": FALLBACK_ADV_USD},
        "n_strategies": len(out),
        "class_vol_fallback": {k: round(v, 6) for k, v in class_vol_fallback.items()},
        "strategies": out,
    }


def write_markdown(summary: dict, path: Path) -> None:
    cfg = summary["config"]
    rows = summary["strategies"]
    lines: list[str] = []
    lines.append(f"# Capacity Estimator — {summary['generated'][:10]}")
    lines.append("")
    lines.append("Generated by `tools/capacity_estimator.py` — opt-in sidecar.")
    lines.append("")
    lines.append(
        "Per-strategy USD capacity via Almgren-Chriss square-root impact: "
        f"`slippage_bps = {cfg['lambda']} * sigma * sqrt(Q / ADV) * 10000`. "
        "`capacity_usd` = order size at which slippage equals the strategy's "
        "after-cost edge. Strategies with negative edge get capacity = 0."
    )
    lines.append("")
    lines.append("## Top 20 by capacity")
    lines.append("")
    lines.append("| Strategy | n | edge bps | sigma | ADV (USD) | capacity (USD) | bucket |")
    lines.append("|---|---:|---:|---:|---:|---:|---|")
    for r in rows[:20]:
        lines.append(
            f"| {r['strategy']} | {r['n']} | {r['edge_bps']:.1f} | "
            f"{r['sigma_daily']:.4f} | {r['adv_usd']:,.0f} | "
            f"{r['capacity_usd']:,.0f} | {r['capacity_bucket']} |"
        )
    lines.append("")
    lines.append("## Capacity bucket distribution")
    buckets: dict[str, int] = defaultdict(int)
    for r in rows:
        buckets[r["capacity_bucket"]] += 1
    lines.append("")
    lines.append("| Bucket | Count |")
    lines.append("|---|---:|")
    for b, c in sorted(buckets.items(), key=lambda x: -x[1]):
        lines.append(f"| {b} | {c} |")
    lines.append("")
    lines.append("## Wiring plan")
    lines.append("")
    lines.append(
        "Sidecar artifact only. Follow-up PR adds `capacity (USD)` column "
        "to `audit_dashboard/template.html` strategy table — the column "
        "answers the dispositive sizing question 'how much can I run this "
        "strategy for before edge erodes?'"
    )
    lines.append("")
    with path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lambda-const", type=float, default=DEFAULT_LAMBDA)
    ap.add_argument("--min-n", type=int, default=DEFAULT_MIN_N)
    ap.add_argument("--no-network", action="store_true",
                    help="Skip yfinance lookup; use fallback ADV always")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    with PICKS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data.get("picks", {}).get("recent_closed", [])

    overrides: dict[str, float] | None = None
    if args.no_network:
        # Force fallback by passing all-overrides empty + skipping network
        overrides = {"_force_fallback_only_marker": -1.0}

    summary = analyze_all(picks, args.lambda_const, args.min_n, overrides)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    md_path = OUT_MD_DIR / f"capacity_estimator_{datetime.now(timezone.utc).strftime('%Y_%m_%d')}.md"
    write_markdown(summary, md_path)

    if not args.quiet:
        print(f"strategies: {summary['n_strategies']}")
        for r in summary["strategies"][:10]:
            print(f"  {r['strategy']:<35} cap={r['capacity_usd']:>12,.0f} "
                  f"({r['capacity_bucket']})")
        print(f"JSON: {OUT_JSON}")
        print(f"MD:   {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
