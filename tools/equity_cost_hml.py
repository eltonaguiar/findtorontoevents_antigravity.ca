#!/usr/bin/env python3
"""Measure EQUITY round-trip execution cost on OUR universe, point-in-time,
net of the verified Questrade schedule. Records n.

WHY THIS FILE EXISTS
    The HML pre-registration (docs/preregistration/HML_VALUE_TEST_2026-11-22.md)
    is blocked on B2: EQUITY cost was never measured. Two constants in the repo
    disagree 5x -- ASSUMED 5.0 bp in tools/measured_cost_recost.py and
    alpha_engine/cost_model.py, versus COST_BP_PRIMARY = 25.0 in
    tools/pod_equity_breakout_backtest.py. Neither is a measurement, so any
    "net of cost" figure built on either is a choice of constant.

WHAT IS MEASURED vs WHAT IS READ OFF A TARIFF
    Measured here, from our own bars:
      * Corwin & Schultz (2012) effective spread on consecutive DAILY high/low
      * Roll (1984) on daily return autocovariance (structurally valid only
        when that autocovariance is negative; recorded, not assumed)
      * a hard per-bar upper bound: bid and ask both lie inside [low, high], so
        the round-trip spread cannot exceed the bar's high-low range
    Read off Questrade's published tariff (verified 2026-11-23, see
    QUESTRADE_SOURCE). These are a broker's own posted prices, not estimates:
      * stock/ETF buy  = $0
      * stock/ETF sell = $0
      * ECN            = $0 on smart-routed orders (direct-routed only)
      * SEC fee        = 0.0000206 x sell notional  -> 0.206 bp, SELL SIDE ONLY
      * FX             = 1.5%, but only on currency conversion, and a USD
                         account avoids it entirely -> modelled as 0, with the
                         non-avoided case reported as an explicit sensitivity

WHAT THIS DELIBERATELY DOES NOT DO
    * It does not import a "realistic" slippage constant. For an equal-weight
      monthly book in S&P 500 names, participation is computed as a fraction of
      ADV so the reader can see whether impact is negligible or not; it is not
      silently added.
    * It does not claim the universe is point-in-time. It is NOT: the ticker
      list is today's S&P 500, so it is survivor-conditioned and skewed toward
      LIQUID names. Measured cost is therefore a LOWER BOUND on a true PIT
      universe's cost. `survivorship` is written into the output.

Read-only. No orders. Not investment advice.

Usage:
    python3 tools/equity_cost_hml.py                 # fetch+cache, measure, write
    python3 tools/equity_cost_hml.py --offline       # cache only
    python3 tools/equity_cost_hml.py --limit 120     # smaller universe
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CACHE = ROOT / "data" / "cache" / "hml_daily"
OUT = ROOT / "reports" / "equity_cost_hml.json"
EARNINGS = ROOT / "data" / "earnings"

# ---------------------------------------------------------------- tariff
# Verified 2026-11-23 from questrade.com's own pages:
#   https://www.questrade.com/pricing/self-directed-commissions-plans-fees/transaction
#   https://www.questrade.com/pricing-fees
# Commissions table: "Stock Trade - Buy | Free", "Stock Trade - Sell | Free",
# "ETF Trade - Buy | Free", "ETF Trade - Sell | Free".
# ECN: "Orders for Canadian securities: No ECN fees. Orders for US securities:
# No ECN fees except..." and those exceptions require DIRECT ROUTED orders.
# SEC: "calculated at 0.0000206 x the value of the trade" on SALES of US
# securities. Currency Conversion (USD/CAD): 1.5%.
QUESTRADE_SOURCE = {
    "transaction_fees": "https://www.questrade.com/pricing/self-directed-commissions-plans-fees/transaction",
    "pricing": "https://www.questrade.com/pricing-fees",
    "verified_utc": "2026-11-23",
}
COMMISSION_PER_SHARE = 0.0          # "Stock Trade - Buy / Sell | Free"
COMMISSION_MIN = 0.0
COMMISSION_MAX = 0.0
ECN_PER_SHARE = 0.0                 # smart-routed orders incur none
SEC_FEE_RATE = 0.0000206            # x sell notional -> 0.206 bp on the sell leg
FX_CONVERSION = 0.015               # only when converting currency; avoided in USD acct
FX_MODE = "USD_ACCOUNT_ASSUMED_0BP"
FX_SENSITIVITY_BP = FX_CONVERSION * 1e4   # 150 bp if NOT avoided

# The two repo constants this measurement replaces, kept for the delta line.
REPO_ASSUMED_BP = {"measured_cost_recost/cost_model": 5.0,
                   "pod_equity_breakout_backtest": 25.0}


def universe(limit: int | None = None) -> list[str]:
    """Our equity universe = the S&P 500 ticker list the repo already tracks."""
    if not EARNINGS.is_dir():
        return []
    syms = sorted(p.name for p in EARNINGS.iterdir()
                  if p.is_dir() and p.name.isupper() and 1 <= len(p.name) <= 5)
    return syms[:limit] if limit else syms


def load_daily(sym: str, offline: bool = False) -> list[dict]:
    """Daily OHLCV, cached. Never raises; a missing symbol returns []."""
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"{sym}.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:                                  # noqa: BLE001
            pass
    if offline:
        return []
    try:
        warnings.filterwarnings("ignore")
        import yfinance as yf
        df = yf.download(sym, period="5y", interval="1d", progress=False,
                         auto_adjust=False, threads=False)
        if df is None or len(df) == 0:
            return []
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = [c[0] for c in df.columns]
        rows = []
        for idx, r in df.iterrows():
            try:
                o, h, l, c, v = (float(r["Open"]), float(r["High"]), float(r["Low"]),
                                 float(r["Close"]), float(r.get("Volume", 0) or 0))
            except Exception:                              # noqa: BLE001
                continue
            if min(o, h, l, c) <= 0 or not all(map(math.isfinite, (o, h, l, c, v))):
                continue
            rows.append({"date": str(idx)[:10], "o": o, "h": h, "l": l,
                         "c": c, "v": v})
        if rows:
            p.write_text(json.dumps(rows))
        return rows
    except Exception:                                      # noqa: BLE001
        return []


def load_intraday(sym: str, offline: bool = False) -> list[dict]:
    """1-minute bars, last ~5 sessions, cached.

    Daily bars CANNOT measure spread for liquid large caps: Corwin-Schultz and
    Roll both assume the observed range/autocovariance is dominated by the
    spread, and on multi-year daily bars the volatility term swamps it. Measured
    empirically on this universe, daily CS returned 0.00 bp for 25/25 names.
    Minute bars restore the ratio the estimators need.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"{sym}_1m.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:                                  # noqa: BLE001
            pass
    if offline:
        return []
    try:
        warnings.filterwarnings("ignore")
        import yfinance as yf
        df = yf.download(sym, period="5d", interval="1m", progress=False,
                         auto_adjust=False, threads=False)
        if df is None or len(df) == 0:
            return []
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = [c[0] for c in df.columns]
        rows = []
        for idx, r in df.iterrows():
            try:
                h, l, c = float(r["High"]), float(r["Low"]), float(r["Close"])
            except Exception:                              # noqa: BLE001
                continue
            if min(h, l, c) <= 0 or not all(map(math.isfinite, (h, l, c))):
                continue
            rows.append({"ts": str(idx), "h": h, "l": l, "c": c})
        if rows:
            p.write_text(json.dumps(rows))
        return rows
    except Exception:                                      # noqa: BLE001
        return []


# ---------------------------------------------------------------- measures
def corwin_schultz(highs: list[float], lows: list[float]) -> dict:
    """Corwin & Schultz (2012) effective spread, consecutive bar pairs.

    Returns the full proportional bid-ask spread in bp; a round trip pays it
    once, so this IS the round-trip spread cost. Reports the per-pair MEDIAN,
    which is robust to the single negative outliers CS routinely produces, and
    the fraction floored at zero (a high rate means the estimate is
    noise-limited and should not be trusted).
    """
    vals = []
    k = 3 - 2 * math.sqrt(2)
    for i in range(len(highs) - 1):
        h1, l1, h2, l2 = highs[i], lows[i], highs[i + 1], lows[i + 1]
        if min(h1, l1, h2, l2) <= 0:
            continue
        b = math.log(h1 / l1) ** 2 + math.log(h2 / l2) ** 2
        H, L = max(h1, h2), min(l1, l2)
        if L <= 0:
            continue
        g = math.log(H / L) ** 2
        try:
            a = (math.sqrt(2 * b) - math.sqrt(b)) / k - math.sqrt(g / k)
            s = 2 * (math.exp(a) - 1) / (1 + math.exp(a))
        except (ValueError, OverflowError):
            continue
        vals.append(s * 1e4)
    if not vals:
        return {"n_pairs": 0, "median_bp": None, "frac_floored": None}
    vals.sort()
    floored = sum(1 for v in vals if v <= 0) / len(vals)
    return {"n_pairs": len(vals),
            "median_bp": max(0.0, statistics.median(vals)),
            "p25_bp": vals[len(vals) // 4],
            "p75_bp": vals[3 * len(vals) // 4],
            "frac_floored": floored,
            "usable": floored < 0.5}


def roll_estimator(closes: list[float]) -> dict:
    """Roll (1984): 2*sqrt(-cov(r_t, r_{t-1})). Valid only if cov < 0."""
    r = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))
         if closes[i - 1] > 0 and closes[i] > 0]
    if len(r) < 30:
        return {"n": len(r), "bp": None, "structurally_valid": False}
    m = statistics.mean(r)
    x = [v - m for v in r]
    cov = sum(x[i] * x[i - 1] for i in range(1, len(x))) / (len(x) - 1)
    acf1 = cov / (sum(v * v for v in x) / (len(x) - 1))
    return {"n": len(r),
            "bp": 2 * math.sqrt(-cov) * 1e4 if cov < 0 else None,
            "acf1": acf1, "structurally_valid": cov < 0}


def high_low_bound(rows: list[dict]) -> float | None:
    """Median (high-low)/close in bp -- a HARD upper bound on round-trip spread."""
    if not rows:
        return None
    vals = [(r["h"] - r["l"]) / r["c"] * 1e4 for r in rows if r["c"] > 0]
    return statistics.median(vals) if vals else None


def measure_symbol(sym: str, rows: list[dict], intraday: list[dict]) -> dict:
    if len(rows) < 60:
        return {"symbol": sym, "status": "INSUFFICIENT_BARS", "n_bars": len(rows)}
    cs = corwin_schultz([r["h"] for r in intraday], [r["l"] for r in intraday]) \
        if len(intraday) >= 60 else {"median_bp": None, "frac_floored": None,
                                     "n_pairs": 0, "usable": False}
    roll = roll_estimator([r["c"] for r in intraday]) if len(intraday) >= 60 \
        else {"bp": None, "structurally_valid": False, "n": 0}
    adv_usd = statistics.median([r["c"] * r["v"] for r in rows if r["v"] > 0]) \
        if any(r["v"] > 0 for r in rows) else None
    return {"symbol": sym, "status": "OK", "n_bars": len(rows),
            "n_intraday": len(intraday),
            "cs_bp": cs["median_bp"], "cs_n_pairs": cs["n_pairs"],
            "cs_frac_floored": cs["frac_floored"], "cs_usable": cs["usable"],
            "roll_bp": roll["bp"], "roll_valid": roll["structurally_valid"],
            "hl_upper_bound_bp": high_low_bound(rows), "adv_usd": adv_usd,
            "first": rows[0]["date"], "last": rows[-1]["date"]}


def questrade_cost_bp(spread_bp: float) -> dict:
    """Round-trip cost in bp = measured spread + the tariff's non-zero terms."""
    sec_buy = 0.0                                   # SEC fee is sales-only
    sec_sell = SEC_FEE_RATE * 1e4                   # 0.206 bp on the sell leg
    fx_bp = 0.0 if FX_MODE.startswith("USD_ACCOUNT") else FX_SENSITIVITY_BP
    commission_bp = 0.0                             # $0 both sides
    ecn_bp = 0.0                                    # $0 smart-routed
    total = spread_bp + commission_bp + ecn_bp + sec_buy + sec_sell + fx_bp
    return {"spread_bp": round(spread_bp, 4),
            "commission_bp": commission_bp, "ecn_bp": ecn_bp,
            "sec_fee_bp": round(sec_sell, 4), "fx_bp": fx_bp,
            "total_bp": round(total, 4)}


def impact_bp(notional_per_name: float, adv_usd: float | None) -> dict:
    """Participation as a fraction of ADV. Reported, not auto-added to cost."""
    if not adv_usd or adv_usd <= 0:
        return {"participation": None, "note": "ADV unavailable"}
    part = notional_per_name / adv_usd
    return {"participation": part,
            "note": "negligible impact if participation < 1%"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--notional", type=float, default=20_000.0,
                    help="USD per name (equal weight), for participation only")
    a = ap.parse_args()

    syms = universe(a.limit)
    print(f"universe: {len(syms)} tickers from {EARNINGS.relative_to(ROOT)}")
    if not syms:
        print("::error:: no universe found")
        return 2

    recs, missing = [], []
    for i, s in enumerate(syms, 1):
        rows = load_daily(s, offline=a.offline)
        if not rows:
            missing.append(s)
            continue
        intra = load_intraday(s, offline=a.offline)
        recs.append(measure_symbol(s, rows, intra))
        if i % 25 == 0:
            print(f"  ...{i}/{len(syms)} measured")

    ok = [r for r in recs if r.get("status") == "OK"]
    cs_rows = [r for r in ok if r.get("cs_usable") and r.get("cs_bp") is not None]
    if not cs_rows:
        print("::error:: no symbol produced a USABLE Corwin-Schultz spread")
        out = {"generated_utc": datetime.now(timezone.utc).isoformat(),
               "n_universe": len(syms), "n_measured": len(ok),
               "n_spread_usable": 0, "missing": missing,
               "status": "NO USABLE SPREAD",
               "note": "CS floored to zero on >50% of pairs for every symbol"}
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(out, indent=2))
        return 1

    cs_med = statistics.median([r["cs_bp"] for r in cs_rows])
    roll_valid = [r["roll_bp"] for r in ok if r.get("roll_valid") and r["roll_bp"]]
    hl_med = statistics.median([r["hl_upper_bound_bp"] for r in ok
                                if r.get("hl_upper_bound_bp")])
    n_bar_days = sum(r["n_bars"] for r in ok)
    n_intraday = sum(r["n_intraday"] for r in ok)

    cost = questrade_cost_bp(cs_med)
    advs = [r["adv_usd"] for r in ok if r.get("adv_usd")]
    adv_median = statistics.median(advs) if advs else None
    imp = impact_bp(a.notional, adv_median)

    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "OK",
        "universe": {
            "source": "data/earnings/<TICKER> directories (S&P 500 list)",
            "n_universe": len(syms), "n_measured": len(ok),
            "n_spread_usable": len(cs_rows),
            "n_missing": len(missing), "missing_sample": missing[:10],
            "n_bar_days_daily": n_bar_days, "n_bars_1min": n_intraday,
            "daily_first": min(r["first"] for r in ok),
            "daily_last": max(r["last"] for r in ok),
        },
        "survivorship": {
            "is_point_in_time": False,
            "why": "ticker list is today's S&P 500; survivors are more liquid",
            "direction": "measured cost is a LOWER BOUND on a true PIT universe",
        },
        "time_mismatch": {
            "spread_measured_at": "last ~5 trading sessions (intraday window)",
            "applied_to": "a 2022-2026 backtest",
            "direction": "spreads have broadly compressed, so using current "
                         "spreads mildly UNDERSTATES historical cost",
            "why_not_backfilled": "minute bars are only available for recent "
                                  "sessions from the free providers",
        },
        "spread_bp": {
            "corwin_schultz_median": round(cs_med, 4),
            "corwin_schultz_n_usable": len(cs_rows),
            "corwin_schultz_p25": round(statistics.median(
                [r["cs_bp"] for r in cs_rows]), 4),
            "roll_median": round(statistics.median(roll_valid), 4) if roll_valid else None,
            "roll_n_valid": len(roll_valid),
            "roll_note": "Roll is upward-biased by volatility; corroboration only",
            "high_low_upper_bound_median": round(hl_med, 4) if hl_med else None,
        },
        "questrade_tariff": {
            "source": QUESTRADE_SOURCE,
            "commission_per_share": COMMISSION_PER_SHARE,
            "ecn_per_share_smart_routed": ECN_PER_SHARE,
            "sec_fee_rate": SEC_FEE_RATE,
            "fx_mode": FX_MODE, "fx_bp": cost["fx_bp"],
            "fx_sensitivity_if_not_avoided_bp": FX_SENSITIVITY_BP,
        },
        "cost_round_trip_bp": cost,
        "participation": imp | {"notional_per_name_usd": a.notional,
                                "adv_median_usd": adv_median},
        "replaces_assumed_constants_bp": REPO_ASSUMED_BP,
        "per_symbol": sorted(ok, key=lambda r: r["cs_bp"]),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))

    print()
    print(f"MEASURED  n_names={len(ok)}  n_spread_usable={len(cs_rows)}  "
          f"n_daily_bars={n_bar_days}  n_1min_bars={n_intraday}")
    print(f"  daily history {out['universe']['daily_first']} -> "
          f"{out['universe']['daily_last']}")
    print(f"  Corwin-Schultz (1-min)  median {cs_med:.2f} bp  "
          f"usable {len(cs_rows)}/{len(ok)}")
    if roll_valid:
        print(f"  Roll (1-min, valid)     median {statistics.median(roll_valid):.2f} bp"
              f"   n_valid={len(roll_valid)}")
    if hl_med:
        print(f"  High-low upper bound    median {hl_med:.2f} bp  (loose, sanity only)")
    print(f"  Questrade: commission {cost['commission_bp']} + ECN {cost['ecn_bp']}"
          f" + SEC {cost['sec_fee_bp']} + FX {cost['fx_bp']}")
    print(f"  ROUND TRIP TOTAL        {cost['total_bp']:.2f} bp")
    print(f"  (if FX not avoided:     {cost['total_bp'] + FX_SENSITIVITY_BP:.2f} bp)")
    print(f"  vs repo constants:      {REPO_ASSUMED_BP}")
    if adv_median:
        print(f"  participation @ ${a.notional:,.0f}/name = "
              f"{imp['participation']:.6%} of median ADV ${adv_median:,.0f}")
    print(f"written: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
