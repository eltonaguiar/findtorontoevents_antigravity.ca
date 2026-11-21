#!/usr/bin/env python3
"""H-149 -- EQUITY mid-cap gross profitability (registered 2026-11-21).

Renumbered from H-146 on 2026-11-21.  Another agent pre-registered H-146 as the
ETF `execution_cost_gate` in a block covering H-144..H-148 (see
plans/2026-11-20-residual-mean-reversion-hypotheses.md), so this entry moved to
H-149 = max observed id across origin/main, this branch, and the working tree,
plus one.  The hypothesis itself is unchanged.

PRE-REGISTERED SPEC (filed before any data was read)
    Signal      GP/A = latest 10-K gross profit / latest 10-K total assets.
    Universe    US common stocks whose market cap, measured AT the rebalance
                date from point-in-time shares outstanding x that day's close,
                falls in $2B-$10B.
    Hold        40 trading days (midpoint of the pre-registered 20-60 band).
    Benchmark   MKT / SMB / HML / RMW (not re-derived here; see limits).

LOOK-AHEAD GUARD
    Every fundamental fact carries the SEC `filed` date on which it became
    public.  A fact is usable at rebalance date D only if filed < D, strictly.
    This is the whole point of using XBRL companyfacts instead of yfinance:
    yfinance returns today's restated statements with no filing date, so it
    cannot satisfy this rule and is not used for fundamentals.

WHAT THIS TOOL MEASURES
    The record series is the FULL cross-section: at every month end, each
    in-band name contributes one record carrying its GP/A z-score and its
    forward net return.  That is what the edge-stability harness needs -- it
    asks whether the score separates winners from losers across time.  The
    actual trading rule (long the top decile) is scored separately and
    reported, but it is far too sparse to reach harness density.

HARNESS
    tools/edge_stability_harness.py is imported UNMODIFIED from its file path
    and its own _windows()/_window_eff() do the bucketing and effect size.
    --self-check asserts EFF_MIN / MIN_WINDOW_N / MIN_STABLE_WINDOWS still hold
    their published values, so "unmodified" is verified rather than promised.

Usage:
    python tools/h149_midcap_gross_profitability.py --sample-n 150 --seed 149
    python tools/h149_midcap_gross_profitability.py --self-check
    python tools/h149_midcap_gross_profitability.py --no-network   # cache only
"""
from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import os
import random
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CACHE = ROOT / "tools" / "cache" / "sec_companyfacts"
OUT_JSON = ROOT / "reports" / "h149_midcap_gross_profitability_2026-11-21.json"

SEC_UA = os.environ.get(
    "SEC_USER_AGENT", "antigravity-research contact@findtorontoevents.ca")
COMPANYFACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

CAP_LO, CAP_HI = 2.0e9, 10.0e9
HOLD_DAYS = 40
MIN_IN_BAND = 5          # a rebalance with fewer names has no usable cross-section
TOP_DECILE_Z = 1.2816    # 90th percentile of the standard normal
STRESS_COST_MULT = 2.0
COST_SURVIVAL_MIN = 0.60


# ─────────────────────────────────────────────────────────── HTTP / cache ──
def _http_json(url: str, timeout: int = 60) -> dict:
    req = urllib.request.Request(url, headers={
        "User-Agent": SEC_UA,
        "Accept-Encoding": "gzip, deflate",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    return json.loads(raw)


def _urlopen_text(url: str, timeout: int = 60) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": SEC_UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    return raw.decode("utf-8", "replace")


# ───────────────────────────────────────────────────────────── XBRL facts ──
_ANNUAL_FORMS = frozenset({"10-K", "10-K/A", "20-F", "20-F/A"})


def _series(facts: dict, taxonomy: str, tag: str, units: tuple[str, ...]) -> list[dict]:
    node = (facts.get("facts") or {}).get(taxonomy, {}).get(tag)
    if not isinstance(node, dict):
        return []
    out: list[dict] = []
    for unit, arr in (node.get("units") or {}).items():
        if unit not in units or not isinstance(arr, list):
            continue
        for f in arr:
            if not isinstance(f, dict):
                continue
            end, filed, val = f.get("end"), f.get("filed"), f.get("val")
            if not end or not filed or val is None:
                continue
            try:
                v = float(val)
            except (TypeError, ValueError):
                continue
            out.append({
                "end": str(end),
                "filed": str(filed),
                "val": v,
                "form": str(f.get("form") or ""),
                "fy": f.get("fy"),
                "fp": f.get("fp"),
            })
    # one value per (end, filed): later amendment wins
    dedup: dict[tuple[str, str], dict] = {}
    for r in out:
        dedup[(r["end"], r["filed"])] = r
    return sorted(dedup.values(), key=lambda r: (r["filed"], r["end"]))


def extract_cik(companyfacts: dict) -> dict:
    """Compact, cacheable per-company fact set. Keeps only what GP/A needs."""
    annual_gp = [r for r in _series(companyfacts, "us-gaap", "GrossProfit", ("USD",))
                  if r["form"] in _ANNUAL_FORMS]
    annual_assets = [r for r in _series(companyfacts, "us-gaap", "Assets", ("USD",))
                     if r["form"] in _ANNUAL_FORMS]
    shares = _series(companyfacts, "dei",
                     "EntityCommonStockSharesOutstanding", ("shares",))
    return {
        "gross_profit": annual_gp,
        "assets": annual_assets,
        "shares": shares,
    }


def load_company_facts(cik: int, refresh: bool = False,
                       allow_network: bool = True) -> dict | None:
    cache_path = CACHE / f"CIK{cik:010d}.json"
    if cache_path.exists() and not refresh:
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    if not allow_network:
        return None
    try:
        cf = _http_json(COMPANYFACTS.format(cik=cik))
    except Exception as exc:  # noqa: BLE001
        print(f"  ! CIK {cik}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return None
    compact = extract_cik(cf)
    if not (compact["gross_profit"] and compact["assets"]):
        return None
    CACHE.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(compact), encoding="utf-8")
    return compact


# ───────────────────────────────────────────────────────── point-in-time ──
def _latest_filed_before(series: list[dict], asof: str) -> dict | None:
    """Latest observation whose filing date is STRICTLY before `asof`."""
    best = None
    for r in series:
        if r["filed"] < asof:
            best = r
        else:
            break          # series is sorted by filed
    return best


def gpa_at(facts: dict, asof: str) -> tuple[float, float] | None:
    """Return (GP/A, shares outstanding) as known strictly before `asof`."""
    gp = _latest_filed_before(facts["gross_profit"], asof)
    assets = _latest_filed_before(facts["assets"], asof)
    sh = _latest_filed_before(facts["shares"], asof)
    if not gp or not assets or not sh:
        return None
    if assets["val"] <= 0 or sh["val"] <= 0:
        return None
    return gp["val"] / assets["val"], sh["val"]


# ─────────────────────────────────────────────────────────────── helpers ──
def _round_trip_bp() -> tuple[float, str]:
    """EQUITY round-trip cost in basis points, from the repo's slip model."""
    try:
        from alpha_engine import charter_slippage as cs  # type: ignore
        for fn in ("round_trip_bp", "get_round_trip_bp", "bp_for_class",
                   "slippage_bp_for_class"):
            f = getattr(cs, fn, None)
            if not callable(f):
                continue
            for args in (("EQUITY",), ("EQUITY", "DEFAULT"), ()):
                try:
                    v = f(*args)
                except Exception:  # noqa: BLE001
                    continue
                if isinstance(v, (int, float)) and 0 <= float(v) < 500:
                    return float(v), f"alpha_engine.charter_slippage.{fn}"
    except Exception:  # noqa: BLE001
        pass
    return 20.0, "declared fallback 20bp round-trip (slippage model not importable)"


def _zscore(vals: list[float]) -> list[float]:
    if len(vals) < 2:
        return [0.0] * len(vals)
    m = sum(vals) / len(vals)
    var = sum((v - m) ** 2 for v in vals) / len(vals)
    sd = var ** 0.5
    if sd <= 1e-12:
        return [0.0] * len(vals)
    return [(v - m) / sd for v in vals]


def load_harness():
    """Import edge_stability_harness UNMODIFIED from its file path."""
    path = ROOT / "tools" / "edge_stability_harness.py"
    spec = importlib.util.spec_from_file_location("_esh_h149", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def harness_self_check(H) -> dict:
    published = {"EFF_MIN": 0.30, "MIN_WINDOW_N": 80, "MIN_STABLE_WINDOWS": 3}
    got = {k: getattr(H, k, None) for k in published}
    return {"published": published, "observed": got,
            "unmodified": got == published}


# ─────────────────────────────────────────────────────────── record build ──
def build_records(names: list[dict], closes, idx, rebal_dates: list,
                  cost_bp: float) -> tuple[list[dict], dict]:
    records: list[dict] = []
    stats = {"rebalances": 0, "skipped_sparse": 0, "in_band_total": 0,
             "rebalances_used": 0}
    n_idx = len(idx)
    for D in rebal_dates:
        asof = D.strftime("%Y-%m-%d")
        rows: list[tuple[float, dict]] = []
        for nm in names:
            got = gpa_at(nm["facts"], asof)
            if got is None:
                continue
            gpa, shares = got
            if nm["ticker"] not in closes.columns:
                continue
            px = closes[nm["ticker"]].asof(D)
            if px is None or px != px or px <= 0:   # NaN-safe
                continue
            cap = shares * float(px)
            if not (CAP_LO <= cap <= CAP_HI):
                continue
            rows.append((gpa, nm))
        stats["rebalances"] += 1
        if len(rows) < MIN_IN_BAND:
            stats["skipped_sparse"] += 1
            continue
        stats["rebalances_used"] += 1
        stats["in_band_total"] += len(rows)
        zs = _zscore([g for g, _ in rows])
        i = idx.get_loc(D)
        j = i + HOLD_DAYS
        if j >= n_idx:
            continue
        exit_date = idx[j].strftime("%Y-%m-%d")
        for (gpa, nm), z in zip(rows, zs):
            p0 = closes[nm["ticker"]].iloc[i]
            p1 = closes[nm["ticker"]].iloc[j]
            if not (p0 == p0) or not (p1 == p1) or p0 <= 0:
                continue
            gross_pct = (p1 / p0 - 1.0) * 100.0
            net_pct = gross_pct - cost_bp / 100.0
            records.append({
                "ticker": nm["ticker"],
                "entry_date": asof,
                "resolved_at": exit_date,
                "status": "WON" if net_pct > 0 else "LOST",
                "pnl_pct": net_pct,
                "gross_pct": gross_pct,
                "gpa_score": z,
                "gpa_raw": gpa,
            })
    return records, stats


# ─────────────────────────────────────────────────────────────── verdict ──
def evaluate(records: list[dict], H, window_days: int = 14) -> dict:
    windows = [w for w in H._windows(records, window_days)
               if len(w) >= H.MIN_WINDOW_N]
    per_window = [{"window": k, "n": len(w), "eff": H._window_eff(w, "gpa_score")}
                  for k, w in enumerate(windows)]
    scored = [r for r in per_window if r["eff"] is not None]
    strong = [r for r in scored if abs(r["eff"]) >= H.EFF_MIN]
    pos = [r for r in strong if r["eff"] > 0]
    neg = [r for r in strong if r["eff"] < 0]
    same = pos if len(pos) >= len(neg) else neg
    same_sign = len(same) >= H.MIN_STABLE_WINDOWS and len(same) == len(strong)
    gross = sum(r["gross_pct"] for r in records) / len(records) if records else 0.0
    net = sum(r["pnl_pct"] for r in records) / len(records) if records else 0.0
    survival = (net / gross) if gross > 0 else None
    admissible = bool(same_sign and survival is not None
                      and survival >= COST_SURVIVAL_MIN)
    if len(scored) >= 5:
        verdict = "ADMISSIBLE" if admissible else "REJECTED"
    else:
        verdict = "UNTESTED"
    return {
        "windows_with_min_n": len(windows),
        "windows_scored": len(scored),
        "windows_strong": len(strong),
        "strong_positive": len(pos),
        "strong_negative": len(neg),
        "same_sign_stable": same_sign,
        "sign": ("+" if (same_sign and same and same[0]["eff"] > 0)
                 else "-" if same_sign else "mixed"),
        "per_window_eff": per_window,
        "gross_edge_pct": round(gross, 4),
        "net_edge_pct": round(net, 4),
        "cost_survival": (round(survival, 3) if survival is not None else None),
        "admissible": admissible,
        "verdict": verdict,
    }


def top_decile_book(records: list[dict]) -> dict:
    sel = [r for r in records if r["gpa_score"] >= TOP_DECILE_Z]
    bot = [r for r in records if r["gpa_score"] <= -TOP_DECILE_Z]
    def _m(xs):
        return round(sum(x["pnl_pct"] for x in xs) / len(xs), 4) if xs else None
    def _wr(xs):
        return round(100.0 * sum(1 for x in xs if x["pnl_pct"] > 0) / len(xs), 2) if xs else None
    return {
        "rule": f"long every in-band name with gpa_zscore >= {TOP_DECILE_Z}",
        "n_top": len(sel), "net_mean_pct_top": _m(sel), "wr_top": _wr(sel),
        "n_bottom": len(bot), "net_mean_pct_bottom": _m(bot), "wr_bottom": _wr(bot),
        "long_short_net_pct": (
            round(_m(sel) - _m(bot), 4) if (sel and bot) else None),
    }


def density_gap(records: list[dict], H, window_days: int = 14) -> dict:
    """How far the series is from harness density, in exact units."""
    if not records:
        return {"scorable": False}
    n_reb = len({r["entry_date"] for r in records})
    per_reb = len(records) / n_reb if n_reb else 0
    need_per_window = H.MIN_WINDOW_N
    windows = len(H._windows(records, window_days))
    need_total = need_per_window * max(windows, 1)
    per_reb_needed = (need_total / n_reb) if n_reb else None
    return {
        "records": len(records),
        "rebalances_contributing": n_reb,
        "records_per_rebalance": round(per_reb, 2),
        "windows_at_window_days": windows,
        "records_needed_for_min_n_per_window": need_total,
        "records_per_rebalance_needed": (round(per_reb_needed, 1)
                                         if per_reb_needed else None),
        "names_needed_to_reach_density": (
            round(per_reb_needed / per_reb, 1) if per_reb and per_reb_needed else None),
        "shortfall_records": max(0, need_total - len(records)),
    }


# ──────────────────────────────────────────────────────────────── main ──
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample-n", type=int, default=150,
                    help="CIKs drawn from the SEC ticker file")
    ap.add_argument("--seed", type=int, default=149)
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--window-days", type=int, default=14)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--no-network", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument("--out", default=str(OUT_JSON))
    args = ap.parse_args()

    H = load_harness()
    chk = harness_self_check(H)
    print(f"# harness constants observed={chk['observed']} unmodified={chk['unmodified']}",
          file=sys.stderr)
    if not chk["unmodified"]:
        print("FATAL: edge_stability_harness thresholds are not the published "
              "values — refusing to report a verdict against a modified gate.",
              file=sys.stderr)
        return 2
    if args.self_check:
        print(json.dumps(chk, indent=2))
        return 0

    # ---- universe: random sample of currently registered SEC filers --------
    CACHE.mkdir(parents=True, exist_ok=True)
    tpath = CACHE / "company_tickers.json"
    if tpath.exists() and not args.refresh:
        tickers = json.loads(tpath.read_text(encoding="utf-8"))
    elif args.no_network:
        print("FATAL: no cached ticker file and --no-network set", file=sys.stderr)
        return 2
    else:
        tickers = json.loads(_urlopen_text(TICKERS_URL))
        tpath.write_text(json.dumps(tickers), encoding="utf-8")

    pool = sorted(
        ({"cik": int(v["cik_str"]), "ticker": str(v["ticker"]).upper(),
          "title": v.get("title", "")} for v in tickers.values()),
        key=lambda d: d["cik"])
    random.Random(args.seed).shuffle(pool)
    sample = pool[: args.sample_n]
    print(f"# universe: {len(pool)} SEC filers, random sample of {len(sample)} "
          f"(seed={args.seed})", file=sys.stderr)

    names: list[dict] = []
    for k, ent in enumerate(sample, 1):
        facts = load_company_facts(ent["cik"], refresh=args.refresh,
                                   allow_network=not args.no_network)
        if facts and len(facts["gross_profit"]) >= 2 and len(facts["assets"]) >= 2:
            names.append({"ticker": ent["ticker"], "cik": ent["cik"],
                          "title": ent["title"], "facts": facts})
        if k % 25 == 0:
            print(f"  .. {k}/{len(sample)} fetched, {len(names)} usable",
                  file=sys.stderr)
    print(f"# usable names with >=2 annual 10-K GP and Assets: {len(names)}",
          file=sys.stderr)
    if not names:
        print("FATAL: no usable names — nothing to test (DATA_GAP).", file=sys.stderr)
        return 2

    # ---- prices ------------------------------------------------------------
    import pandas as pd
    import yfinance as yf

    tickers_list = [n["ticker"] for n in names]
    print(f"# downloading daily prices for {len(tickers_list)} tickers",
          file=sys.stderr)
    raw = yf.download(tickers_list, start=args.start, end=args.end,
                      interval="1d", progress=False, auto_adjust=True,
                      threads=True)
    if raw is None or raw.empty:
        print("FATAL: no price data returned", file=sys.stderr)
        return 2
    closes = raw["Close"] if hasattr(raw.columns, "nlevels") and raw.columns.nlevels > 1 else raw
    closes = closes.dropna(axis=1, how="all")
    idx = closes.index
    if len(idx) < HOLD_DAYS + 30:
        print("FATAL: price history too short", file=sys.stderr)
        return 2
    have = set(closes.columns)
    names = [n for n in names if n["ticker"] in have]
    print(f"# names with price data: {len(names)}", file=sys.stderr)

    # month-end trading days
    rebal_dates = (pd.DataFrame({"d": idx}).groupby([idx.year, idx.month])["d"]
                   .max().tolist())
    rebal_dates = [d for d in rebal_dates
                   if pd.Timestamp(args.start) <= d <= pd.Timestamp(args.end)]
    print(f"# rebalance dates: {len(rebal_dates)} "
          f"({rebal_dates[0].date()} .. {rebal_dates[-1].date()})", file=sys.stderr)

    cost_bp, cost_src = _round_trip_bp()
    print(f"# round-trip cost: {cost_bp} bp ({cost_src})", file=sys.stderr)

    records, stats = build_records(names, closes, idx, rebal_dates, cost_bp)
    print(f"# records: {len(records)} from {stats['rebalances_used']} usable "
          f"rebalances ({stats['skipped_sparse']} skipped as sparse)",
          file=sys.stderr)

    res = evaluate(records, H, args.window_days)
    book = top_decile_book(records)
    gap = density_gap(records, H, args.window_days)

    # stress cost
    stress_records, _ = build_records(names, closes, idx, rebal_dates,
                                     cost_bp * STRESS_COST_MULT)
    stress = evaluate(stress_records, H, args.window_days)

    payload = {
        "hypothesis": "H-149",
        "formerly": "H-146 (renumbered 2026-11-21: id collision with ETF execution_cost_gate)",
        "asset_class": "EQUITY",
        "family": "mid_cap_gross_profitability",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": {
            "signal": "GP/A = latest 10-K GrossProfit / latest 10-K Assets",
            "universe": f"US SEC filers with PIT market cap in ${CAP_LO/1e9:.0f}B-${CAP_HI/1e9:.0f}B at rebalance",
            "hold_trading_days": HOLD_DAYS,
            "rebalance": "month end",
            "look_ahead_guard": "fundamental fact usable only if filed < rebalance date (strict)",
            "cost_round_trip_bp": cost_bp,
            "cost_source": cost_src,
            "stress_cost_bp": cost_bp * STRESS_COST_MULT,
            "window_days": args.window_days,
            "sample_n": args.sample_n,
            "seed": args.seed,
        },
        "harness": {
            "module": "tools/edge_stability_harness.py (imported unmodified)",
            "constants": chk["observed"],
            "constants_unmodified": chk["unmodified"],
        },
        "data": {
            "sec_filers_in_pool": len(pool),
            "sampled_ciks": len(sample),
            "names_usable_fundamentals": len(names),
            "rebalances_total": stats["rebalances"],
            "rebalances_used": stats["rebalances_used"],
            "rebalances_skipped_sparse": stats["skipped_sparse"],
            "in_band_observations": stats["in_band_total"],
            "records": len(records),
        },
        "result": res,
        "stress_result": {k: stress[k] for k in
                          ("verdict", "admissible", "windows_scored", "net_edge_pct",
                           "gross_edge_pct", "cost_survival", "sign")},
        "top_decile_book": book,
        "density_gap": gap,
        "limits": [
            "Universe is a random sample of CURRENTLY REGISTERED SEC filers. Firms "
            "that delisted and stopped filing entirely are under-represented, so "
            "survivorship bias is reduced but not eliminated.",
            "Cross-section includes financials and REITs, for which GP/A is not "
            "meaningful; per-name noise dilution is not corrected.",
            "MKT/SMB/HML/RMW are declared as the benchmark but are NOT regressed "
            "out here, so a strong factor tilt could masquerade as a signal.",
            "GP/A is built from annual 10-K only; intra-year filing updates are "
            "not used, which lags the signal by up to a year.",
        ],
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print()
    print(f"VERDICT  {res['verdict']}   admissible={res['admissible']}")
    print(f"  windows scored={res['windows_scored']}  with>={H.MIN_WINDOW_N}="
          f"{res['windows_with_min_n']}  strong={res['windows_strong']} "
          f"({res['strong_positive']}+/{res['strong_negative']}-)  sign={res['sign']}")
    print(f"  gross edge={res['gross_edge_pct']}%  net={res['net_edge_pct']}%  "
          f"cost survival={res['cost_survival']}")
    print(f"  top-decile net mean={book['net_mean_pct_top']}% "
          f"(n={book['n_top']}) vs bottom={book['net_mean_pct_bottom']}% "
          f"(n={book['n_bottom']})  L/S={book['long_short_net_pct']}%")
    if res["verdict"] == "UNTESTED":
        print(f"  DATA GAP: {gap.get('shortfall_records')} more records needed; "
              f"{gap.get('names_needed_to_reach_density')}x the current name count "
              f"would reach {H.MIN_WINDOW_N}/window")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
