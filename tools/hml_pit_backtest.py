#!/usr/bin/env python3
"""HML (value) measurement test -- runs ONCE against the frozen rule in
docs/preregistration/HML_VALUE_TEST_2026-11-22.md.

FROZEN RULE (not modifiable by this file)
    Kill the family if EITHER:
      1. OOS annualised net return on committed capital <= 4.32%, OR
      2. the one-sided 95% upper bound of that return <= 4.32%.
    The bar is 4.32% (= tools/capacity_model.py HURDLE_TBILL_APR = 0.0432),
    not a rounded 4.3%.

POINT-IN-TIME DISCIPLINE
    A fundamental is usable at date t only if
        period_end + REPORTING_LAG_DAYS <= t
    This is what stops a 10-K filed in February from being traded in December.
    Violating it is the single easiest way to manufacture a value premium.

WHAT IS HONESTLY LIMITED, AND DISCLOSED IN THE OUTPUT
  * SURVIVORSHIP: the ticker list is today's S&P 500, so the cheap (long) leg
    is missing the names that delisted or went bankrupt -- precisely the names
    value investing is supposed to own. Measured HML is therefore biased
    UPWARD. This is the residual part of blocker B1 that data cannot fix here.
  * DEPTH: fundamentals reach back only ~4-5 annual periods / ~7 quarters. A
    monthly test over that window has very few independent observations, so the
    "upper bound <= 4.32%" arm of the kill rule may be unreachable by
    construction. The power calculation is reported rather than glossed over.

Read-only. No orders. Not investment advice.

Usage:
    python3 tools/hml_pit_backtest.py
    python3 tools/hml_pit_backtest.py --limit 150 --lag 90
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PRICE_CACHE = ROOT / "data" / "cache" / "hml_daily"
FUND_CACHE = ROOT / "data" / "cache" / "hml_fundamentals"
COST_JSON = ROOT / "reports" / "equity_cost_hml.json"
OUT = ROOT / "reports" / "hml_result.json"
EARNINGS = ROOT / "data" / "earnings"

HURDLE = 0.0432                 # frozen: capacity_model.HURDLE_TBILL_APR
REPORTING_LAG_DAYS = 90         # conservative (large accelerated: 60d 10-K / 40d 10-Q)
N_QUINTILES = 5


def universe(limit: int | None = None) -> list[str]:
    if not EARNINGS.is_dir():
        return []
    syms = sorted(p.name for p in EARNINGS.iterdir()
                  if p.is_dir() and p.name.isupper() and 1 <= len(p.name) <= 5)
    return syms[:limit] if limit else syms


def load_prices(sym: str) -> list[dict]:
    p = PRICE_CACHE / f"{sym}.json"
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text())
    except Exception:                                       # noqa: BLE001
        return []


def load_fundamentals(sym: str) -> list[dict]:
    """Annual book equity + shares, each stamped with its fiscal period end.

    Uses Ordinary Shares Number, NOT Share Issued: the latter is mis-reported
    by 2x for some dual-class names (XOM 2026-03-31 read 8.02B vs a true 4.14B).
    Ordinary Shares Number is validated against marketCap at ratio 1.000.
    """
    FUND_CACHE.mkdir(parents=True, exist_ok=True)
    p = FUND_CACHE / f"{sym}.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:                                   # noqa: BLE001
            return []
    try:
        warnings.filterwarnings("ignore")
        import yfinance as yf
        bs = yf.Ticker(sym).balance_sheet
        if bs is None or len(bs.columns) == 0:
            return []
        out = []
        for col in bs.columns:
            eq = None
            for key in ("Stockholders Equity", "Common Stock Equity",
                        "Total Equity Gross Minority Interest"):
                if key in bs.index:
                    v = bs.loc[key, col]
                    if v == v and v is not None:      # NaN-safe
                        eq = float(v)
                        break
            sh = None
            if "Ordinary Shares Number" in bs.index:
                v = bs.loc["Ordinary Shares Number", col]
                if v == v and v is not None:
                    sh = float(v)
            if eq and sh and eq > 0 and sh > 0:
                out.append({"period_end": str(col)[:10],
                            "book_equity": eq, "shares": sh})
        out.sort(key=lambda r: r["period_end"])
        if out:
            p.write_text(json.dumps(out))
        return out
    except Exception:                                       # noqa: BLE001
        return []


def month_ends(dates: list[str]) -> list[str]:
    """Last observed trading date of each calendar month."""
    seen: dict[str, str] = {}
    for d in sorted(dates):
        seen[d[:7]] = d
    return [seen[k] for k in sorted(seen)]


def fundamental_asof(funds: list[dict], date: str, lag: int) -> dict | None:
    """Most recent fundamental whose period_end + lag <= date. No look-ahead."""
    cutoff = (datetime.strptime(date, "%Y-%m-%d")
              - timedelta(days=lag)).strftime("%Y-%m-%d")
    usable = [f for f in funds if f["period_end"] <= cutoff]
    return usable[-1] if usable else None


def price_asof(prices: list[dict], date: str) -> float | None:
    lo, hi = 0, len(prices) - 1
    best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if prices[mid]["date"] <= date:
            best = prices[mid]["c"]
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def build_panel(syms: list[str], lag: int):
    prices, funds = {}, {}
    for s in syms:
        p = load_prices(s)
        if len(p) >= 250:
            prices[s] = p
        f = load_fundamentals(s)
        if f:
            funds[s] = f
    common = sorted(set(prices) & set(funds))
    if not common:
        return {}, {}, []
    alldates = [d for s in common for d in (prices[s][0]["date"], prices[s][-1]["date"])]
    return prices, funds, (common, min(alldates), max(alldates))


def round_trip_cost_bp(cost_path: Path) -> tuple[float, dict]:
    """Use the CONSERVATIVE (higher) measured spread, plus the SEC fee.

    Rationale: understating cost flatters a strategy, so between the Corwin-
    Schultz median and the Roll median we take the larger as the headline.
    """
    if not cost_path.exists():
        return 0.0, {"status": "MISSING"}
    try:
        c = json.loads(cost_path.read_text())
    except Exception:                                       # noqa: BLE001
        return 0.0, {"status": "UNREADABLE"}
    sp = c.get("spread_bp", {})
    cs = sp.get("corwin_schultz_median")
    roll = sp.get("roll_median")
    vals = [v for v in (cs, roll) if isinstance(v, (int, float))]
    base = max(vals) if vals else 0.0
    sec = c.get("questrade_tariff", {}).get("sec_fee_bp")
    if sec is None:
        sec = c.get("cost_round_trip_bp", {}).get("sec_fee_bp", 0.0)
    return base + sec, {"spread_component_bp": base, "sec_bp": sec,
                        "cs": cs, "roll": roll,
                        "source": "reports/equity_cost_hml.json"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--lag", type=int, default=REPORTING_LAG_DAYS)
    a = ap.parse_args()

    syms = universe(a.limit)
    if not syms:
        print("::error:: empty universe")
        return 2
    built = build_panel(syms, a.lag)
    prices, funds, info = built
    if not info:
        print("::error:: no symbol had BOTH prices and fundamentals")
        return 1
    common, d0, d1 = info
    print(f"universe {len(syms)} -> usable {len(common)}  ({d0} .. {d1}), "
          f"reporting lag {a.lag}d")

    rt_bp, cost_detail = round_trip_cost_bp(COST_JSON)
    print(f"round-trip cost IN: {rt_bp:.2f} bp "
          f"(conservative max-of-estimators + SEC)")

    # monthly rebalance grid from the first date on which ANY fundamental is usable
    ref = [d for d in month_ends([p["date"] for s in common for p in prices[s]])]
    grid = [d for d in ref if any(fundamental_asof(funds[s], d, a.lag) for s in common)]
    if len(grid) < 4:
        print(f"::error:: only {len(grid)} rebalance dates with usable fundamentals")
        OUT.write_text(json.dumps({"status": "INSUFFICIENT_DEPTH",
                                   "n_dates": len(grid)}, indent=2))
        return 1

    rows = []
    for i in range(len(grid) - 1):
        t, t1 = grid[i], grid[i + 1]
        cand = []
        for s in common:
            f = fundamental_asof(funds[s], t, a.lag)
            if not f:
                continue
            px = price_asof(prices[s], t)
            if not px or px <= 0:
                continue
            bm = f["book_equity"] / (f["shares"] * px)
            if not (math.isfinite(bm) and bm > 0):
                continue
            px1 = price_asof(prices[s], t1)
            if not px1 or px1 <= 0:
                continue
            cand.append({"s": s, "bm": bm, "ret": px1 / px - 1})
        if len(cand) < N_QUINTILES * 2:
            continue
        cand.sort(key=lambda r: r["bm"])
        k = max(1, len(cand) // N_QUINTILES)
        cheap, expensive = cand[-k:], cand[:k]
        r_long = statistics.mean([c["ret"] for c in cheap])
        r_short = statistics.mean([c["ret"] for c in expensive])
        # turnover: fraction of each leg that changed versus the previous month
        rows.append({"date": t, "n_ranked": len(cand), "k": k,
                     "long": [c["s"] for c in cheap],
                     "short": [c["s"] for c in expensive],
                     "gross": r_long - r_short})

    if len(rows) < 4:
        print(f"::error:: only {len(rows)} usable rebalances")
        OUT.write_text(json.dumps({"status": "INSUFFICIENT_REBALANCES",
                                   "n": len(rows)}, indent=2))
        return 1

    # turnover -> cost, charged on traded fraction of the long-short book
    for i, r in enumerate(rows):
        if i == 0:
            r["turnover"] = 1.0                     # opening the book
        else:
            prev = rows[i - 1]
            ch = (len(set(r["long"]) ^ set(prev["long"]))
                  + len(set(r["short"]) ^ set(prev["short"])))
            denom = len(r["long"]) + len(r["short"])
            r["turnover"] = ch / denom if denom else 0.0
        r["cost"] = r["turnover"] * rt_bp / 1e4
        r["net"] = r["gross"] - r["cost"]

    nets = [r["net"] for r in rows]
    n = len(nets)
    mean_m = statistics.mean(nets)
    sd_m = statistics.stdev(nets) if n > 1 else 0.0
    ann = mean_m * 12
    se_ann = (sd_m / math.sqrt(n)) * 12
    ub95 = ann + 1.645 * se_ann                 # one-sided 95% upper bound
    gross_ann = statistics.mean([r["gross"] for r in rows]) * 12

    kill_1 = ann <= HURDLE
    kill_2 = ub95 <= HURDLE
    verdict = ("KILL" if (kill_1 or kill_2) else "SURVIVES(power-limited)")

    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "rule": {"hurdle_annual": HURDLE,
                 "kill_if_point_le_hurdle": kill_1,
                 "kill_if_ub95_le_hurdle": kill_2,
                 "verdict": verdict,
                 "source": "docs/preregistration/HML_VALUE_TEST_2026-11-22.md"},
        "result": {"n_months": n, "gross_ann": round(gross_ann, 5),
                   "net_ann": round(ann, 5), "se_ann": round(se_ann, 5),
                   "upper_bound_95_ann": round(ub95, 5),
                   "mean_monthly_net": round(mean_m, 6),
                   "sd_monthly_net": round(sd_m, 6),
                   "avg_turnover": round(statistics.mean(
                       [r["turnover"] for r in rows]), 4)},
        "cost": {"round_trip_bp_used": round(rt_bp, 4), **cost_detail},
        "power": {"n_months": n, "se_ann": round(se_ann, 5),
                  "note": ("with this few independent months the 95% upper "
                           "bound is wide; the ub<=hurdle arm of the rule is "
                           "hard to satisfy for ANY true effect")},
        "limitations": {
            "survivorship": "universe is today's S&P 500 -> HML biased UPWARD",
            "depth": f"{n} monthly rebalances only",
            "is_point_in_time_fundamentals": True,
            "reporting_lag_days": a.lag,
        },
        "months": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))

    print()
    print(f"REBALANCES      n_months={n}   avg turnover {out['result']['avg_turnover']:.1%}")
    print(f"GROSS annual    {gross_ann:+.2%}")
    print(f"NET   annual    {ann:+.2%}   (SE {se_ann:.2%})")
    print(f"95% UPPER BND   {ub95:+.2%}   [hurdle {HURDLE:.2%}]")
    print(f"kill#1 point<=hurdle : {kill_1}")
    print(f"kill#2 ub95<=hurdle  : {kill_2}")
    print(f"VERDICT         {verdict}")
    print(f"written: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
