#!/usr/bin/env python3
"""Funding carry: opportunity-frequency analysis (episode-duration distribution).

Pre-declared in updates/2026-11-22-funding-carry-opportunity-frequency.md §0 BEFORE
this was run. This script only MEASURES how long funding episodes last; it does not
re-derive cost (45.524 bp is measured and settled) and does not compute strategy
returns. Read-only over the existing cached funding pulls - no network access.

Episode rules (all fixed in advance):
  A (headline): maximal contiguous run of settled 8h intervals with funding rate > 0.
  B (sensitivity): the carry backtest's pre-declared trailing-24h-positive mask
     (decision at interval i uses funding up to i only; hold the next interval).
  C (sensitivity): maximal contiguous run with funding rate > 1 bp per 8h.

Thresholds: BREAKEVEN_DAYS = 16.398 (cost amortised), HURDLE_DAYS = 90.

Usage:
  python3 tools/funding_carry_opportunity_frequency.py
  python3 tools/funding_carry_opportunity_frequency.py --out reports/foo.json
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "reports" / "funding_carry_raw"
OUT_JSON = ROOT / "reports" / "funding_carry_opportunity_frequency_20261122.json"

# The five assets with measured spot cost (same set as the carry backtest).
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]

INTERVALS_PER_DAY = 3              # funding every 8h
INTERVAL_MS = 8 * 3600 * 1000
GAP_TOLERANCE_MS = 3600 * 1000     # >8h+1h between records ends an episode (data gap)
TRAILING_INTERVALS = 3             # 24h trailing funding for rule B

BREAKEVEN_DAYS = 16.398            # pair cost 45.524 bp / mean funding per day (settled)
HURDLE_DAYS = 90.0                # only pre-declared hold with net APR > 4.32% T-bills
SUFFICIENT_PER_SYMBOL_YEAR = 4     # pre-declared bar: >=1 qualifying episode per quarter

THRESHOLD_BP = 1e-4                # rule C: 1 bp per 8h

# Capacity from 18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md
CAPACITY_USD = {"XRPUSDT": 29_438, "BTCUSDT": 774_000, "ETHUSDT": 344_000,
                "BNBUSDT": 83_000, "SOLUSDT": 69_000}
# Net APR at the hurdle-clearing hold (90d) and at 30d, from funding_carry_20261122.json
# aggregate table (docs 08 / 15). Used only for the capacity x duration arithmetic.
NET_APR_AT_90D = 0.0624
NET_APR_AT_30D = 0.0242


def load_funding(sym: str) -> pd.DataFrame:
    raw = json.loads((RAW_DIR / f"funding_{sym}.json").read_text())
    df = pd.DataFrame(raw)
    df["ts"] = pd.to_datetime(df["fundingTime"].astype("int64"), unit="ms", utc=True)
    df["rate"] = df["fundingRate"].astype(float)
    return df[["ts", "rate"]].sort_values("ts").drop_duplicates("ts").reset_index(drop=True)


def runs_from_mask(df: pd.DataFrame, mask: np.ndarray) -> list[dict]:
    """Maximal contiguous runs where mask is True and records are contiguous in time."""
    ts_ms = (df["ts"].astype("int64") // 1_000_000).to_numpy()
    episodes, i, n = [], 0, len(mask)
    while i < n:
        if not mask[i]:
            i += 1
            continue
        j = i
        while (j + 1 < n and mask[j + 1]
               and (ts_ms[j + 1] - ts_ms[j]) <= INTERVAL_MS + GAP_TOLERANCE_MS):
            j += 1
        days = (j - i + 1) / INTERVALS_PER_DAY
        episodes.append({"start": str(df["ts"].iloc[i]), "end": str(df["ts"].iloc[j]),
                         "n_intervals": int(j - i + 1), "days": float(days)})
        i = j + 1
    return episodes


def rule_a_mask(rate: np.ndarray) -> np.ndarray:
    return rate > 0


def rule_b_mask(rate: np.ndarray) -> np.ndarray:
    """Trailing 24h sum > 0, known at i -> hold interval i+1 (matches the backtest)."""
    n = len(rate)
    trail = np.convolve(rate, np.ones(TRAILING_INTERVALS), "full")
    trail_sum = np.full(n, np.nan)
    trail_sum[TRAILING_INTERVALS - 1:] = trail[: n - TRAILING_INTERVALS + 1]
    mask = np.zeros(n, dtype=bool)
    mask[1:] = trail_sum[:-1] > 0
    return mask


def rule_c_mask(rate: np.ndarray) -> np.ndarray:
    return rate > THRESHOLD_BP


def dist_stats(episodes: list[dict], years: float) -> dict:
    d = np.array([e["days"] for e in episodes], dtype=float)
    n = len(d)
    out = {"n_episodes": int(n), "years": round(years, 3)}
    if n == 0:
        out.update({"p50": None, "p75": None, "p90": None, "p95": None, "p99": None,
                    "max": None, "frac_gt_breakeven": 0.0, "frac_gt_hurdle": 0.0,
                    "n_gt_breakeven": 0, "n_gt_hurdle": 0,
                    "qualifying_per_year": 0.0})
        return out
    out.update({
        "p50": float(np.quantile(d, 0.50)), "p75": float(np.quantile(d, 0.75)),
        "p90": float(np.quantile(d, 0.90)), "p95": float(np.quantile(d, 0.95)),
        "p99": float(np.quantile(d, 0.99)), "max": float(d.max()),
        "mean": float(d.mean()),
        "n_gt_breakeven": int((d >= BREAKEVEN_DAYS).sum()),
        "n_gt_hurdle": int((d >= HURDLE_DAYS).sum()),
        "frac_gt_breakeven": float((d >= BREAKEVEN_DAYS).mean()),
        "frac_gt_hurdle": float((d >= HURDLE_DAYS).mean()),
        "qualifying_per_year": float((d >= BREAKEVEN_DAYS).sum() / years) if years > 0 else 0.0,
        "total_episode_days": float(d.sum()),
        "exchange_identity_days": None,  # see main(): sum over disjoint rules == window
    })
    return out


def aggregate(all_episodes: list[dict], total_years: float) -> dict:
    return dist_stats(all_episodes, total_years)


def capacity_arithmetic(freq: dict) -> dict:
    """Maximum annual dollar return implied by qualifying opportunities x capacity x net APR.

    Two readings, both reported:
      (i)  per-episode: each qualifying episode earns net APR at 90d over its duration,
           on XRP's capacity (the binding symbol).
      (ii) annualised-exposure: qualifying episodes per year x their mean duration
           (capped at the year) x capacity x net APR at 90d.
    Deliberately optimistic: assumes every qualifying episode earns the 90d net APR and
    that capacity is available in full for each one.
    """
    ep_days = freq["episodes_days"]
    qual_days = [x for x in ep_days if x >= BREAKEVEN_DAYS]
    cap = CAPACITY_USD["XRPUSDT"]
    per_episode = [cap * NET_APR_AT_90D * (x / 365.0) for x in qual_days]
    exposure_days = min(365.0, sum(qual_days))
    return {
        "capacity_usd": cap,
        "net_apr_at_90d": NET_APR_AT_90D,
        "net_apr_at_30d": NET_APR_AT_30D,
        "n_qualifying_episodes": len(qual_days),
        "qualifying_episode_days_total": float(sum(qual_days)),
        "usd_per_qualifying_episode_mean": float(np.mean(per_episode)) if per_episode else 0.0,
        "usd_per_qualifying_episode_max": float(np.max(per_episode)) if per_episode else 0.0,
        "usd_total_from_qualifying_episodes": float(sum(per_episode)),
        "usd_if_full_year_at_capacity_90d": cap * NET_APR_AT_90D,
        "usd_if_full_year_at_capacity_30d": cap * NET_APR_AT_30D,
        "usd_exposure_capped_year": cap * NET_APR_AT_90D * (exposure_days / 365.0),
        "exposure_days": float(exposure_days),
        "xrp_tbill_hurdle_usd_full_year": cap * 0.0432,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="*", default=SYMBOLS)
    ap.add_argument("--out", default=str(OUT_JSON))
    a = ap.parse_args()

    rules = {"A_positive": rule_a_mask, "B_trailing24h": rule_b_mask, "C_gt_1bp": rule_c_mask}
    per_rule: dict[str, dict] = {}
    for rname, fn in rules.items():
        per_sym, all_eps, total_years = {}, [], 0.0
        for sym in a.symbols:
            df = load_funding(sym)
            years = (df["ts"].iloc[-1] - df["ts"].iloc[0]).total_seconds() / (365.25 * 86400)
            eps = runs_from_mask(df, fn(df["rate"].to_numpy()))
            all_eps.extend(eps)
            total_years += years
            per_sym[sym] = dist_stats(eps, years)
            per_sym[sym]["window"] = f"{df['ts'].iloc[0].date()}..{df['ts'].iloc[-1].date()}"
        agg = aggregate(all_eps, total_years)
        agg["episodes_days"] = [e["days"] for e in all_eps]
        per_rule[rname] = {"per_symbol": per_sym, "aggregate": agg}

    # capacity x duration arithmetic on the headline rule's aggregate
    cap_arith = capacity_arithmetic(per_rule["A_positive"]["aggregate"])

    summary = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "breakeven_days": BREAKEVEN_DAYS,
        "hurdle_days": HURDLE_DAYS,
        "sufficient_per_symbol_year": SUFFICIENT_PER_SYMBOL_YEAR,
        "source": "reports/funding_carry_raw/funding_<SYM>.json (Binance fapi/v1/fundingRate, cached)",
        "pair_cost_bp_reference": 45.524,
        "rules": {k: {"per_symbol": v["per_symbol"],
                      "aggregate": {kk: vv for kk, vv in v["aggregate"].items()
                                    if kk != "episodes_days"}}
                  for k, v in per_rule.items()},
        "capacity_arithmetic": cap_arith,
    }
    Path(a.out).write_text(json.dumps(summary, indent=1))

    # ---- console report
    print(f"break-even {BREAKEVEN_DAYS}d, hurdle {HURDLE_DAYS}d, bar {SUFFICIENT_PER_SYMBOL_YEAR}/sym/yr")
    for rname in rules:
        print(f"\n== rule {rname} ==")
        ag = per_rule[rname]["aggregate"]
        print(f"  aggregate n={ag['n_episodes']} p50={ag['p50']} p75={ag['p75']} p90={ag['p90']} "
              f"p95={ag['p95']} p99={ag['p99']} max={ag['max']}")
        if ag["n_episodes"]:
            print(f"  frac>=16.398d={ag['frac_gt_breakeven']:.4f} ({ag['n_gt_breakeven']}/{ag['n_episodes']})  "
                  f"frac>=90d={ag['frac_gt_hurdle']:.4f} ({ag['n_gt_hurdle']}/{ag['n_episodes']})  "
                  f"qualifying/yr={ag['qualifying_per_year']:.2f}")
        for sym, s in per_rule[rname]["per_symbol"].items():
            if s["n_episodes"]:
                print(f"    {sym:<8} n={s['n_episodes']:>4} p50={s['p50']:8.3f} p90={s['p90']:8.3f} "
                      f"p99={s['p99']:8.3f} max={s['max']:8.3f} "
                      f">=BE {s['n_gt_breakeven']:>3} ({s['frac_gt_breakeven']:.3f}) "
                      f">=90d {s['n_gt_hurdle']:>3} q/yr={s['qualifying_per_year']:.2f}")
            else:
                print(f"    {sym:<8} n=0")
    print(f"\ncapacity arithmetic (XRP ${CAPACITY_USD['XRPUSDT']:,}):")
    for k, v in cap_arith.items():
        print(f"  {k}: {v}")
    print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
