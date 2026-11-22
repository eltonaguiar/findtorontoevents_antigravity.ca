#!/usr/bin/env python3
"""H-151 -- net share issuance, the pre-registered test. Not the signal check.

The spec is frozen in reports/hypothesis_registry.json as H-151 (registered
2026-11-22, status PRE_REGISTERED, empty result). This file runs exactly that:

  universe  US common stock, price >= $3, market cap $100M-$10B at formation
  signal    NIS = ln(shares_t / shares_{t-4q}), dei:EntityCommonStockSharesOutstanding
            from the most recent companyfacts filing available at formation
  split     drop a name-quarter when the shares ratio sits within 1.5% of k or 1/k
            for k in {2,3,4,5,6,7,8,10,15,20} -- companyfacts is NOT split adjusted,
            so a 2-for-1 otherwise reads as +100% issuance
  book      quintiles by NIS, equal weight, bottom (net repurchasers) long,
            top (net issuers) short, one-month hold, rebalance at month end
  entry     next session OPEN after the month-end close
  exit      close of the next month end
  cost      10 bp per side, 20 bp round trip per leg; 2x stress reported, not gated
  gate      edge_stability_harness UNMODIFIED, FF4 alpha t >= 2, appraisal >= 0.5,
            >= 100 names per leg, >= 36 months, cost survival >= 0.60

Two sign conventions have to be stated because they are easy to get silently wrong.

1. `gpa_score` in each record is -z(NIS), not +z(NIS). edge_stability_harness
   measures whether HIGHER scores win more often, and the hypothesis says higher
   issuance LOSES, so the score must point toward expected return. The field name
   is kept as `gpa_score` only because that is the key H-149's evaluate() reads;
   `nis_z` and `nis_raw` carry the unflipped signal alongside it.

2. The long leg is the BOTTOM quintile. A positive long-short spread is therefore
   the hypothesis, and the harness sign must come out '+' for a pass.

A gate that fails is reported as a failed gate. The min-100-names-per-leg gate in
particular is a real constraint on a 756-name cache and is not relaxed here.
"""
from __future__ import annotations

import argparse
import bisect
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "tools" / "cache" / "sec_companyfacts"
OUT_JSON = ROOT / "reports" / "h151_net_issuance_2026-11-22.json"

# --- the frozen gates (reports/hypothesis_registry.json, H-151) -------------
EFF_FLOOR = 0.3
MIN_WINDOWS_ADMISSIBLE = 3
COST_SURVIVAL_MIN = 0.60
SLIPPAGE_BPS = 10.0            # per side -> 20 bp round trip per leg
MIN_NAMES_PER_LEG = 100
MIN_MONTHS = 36
ALPHA_T_MIN = 2.0
APPRAISAL_MIN = 0.5
STRESS_COST_MULT = 2.0

# --- universe (data_sample_lock) -------------------------------------------
CAP_LO, CAP_HI = 1e8, 1e10
MIN_PRICE = 3.0

# --- split guard (frozen_rules) --------------------------------------------
SPLIT_K = (2, 3, 4, 5, 6, 7, 8, 10, 15, 20)
SPLIT_TOL = 0.015
WINSOR_PCT = (1, 99)
LOOKBACK_MIN_DAYS, LOOKBACK_MAX_DAYS = 330, 400


def _load(name: str, filename: str):
    path = ROOT / "tools" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


H149 = _load("_h149_for_h151", "h149_midcap_gross_profitability.py")
H150 = _load("_h150_for_h151", "h150_gpa_backtest.py")


# ────────────────────────────────────────────────────────── share facts ──
def load_facts(cik: int) -> dict | None:
    """Cached compact companyfacts, no network. Missing cache = missing name."""
    path = CACHE / f"CIK{cik:010d}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:                     # noqa: BLE001 - corrupt cache entry
        return None


def share_series(facts: dict, idx) -> list[dict]:
    """[(avail_pos, end_ts, val)] sorted by avail_pos.

    avail_pos is the index position of the first trading session >= filed date.
    A fact is usable at formation position i only when avail_pos + 1 <= i, i.e.
    the file has been public for at least one full session. Period end dates are
    never used as availability dates (frozen point_in_time rule).
    """
    import pandas as pd

    raw = facts.get("shares") or []
    per_end: dict[str, dict] = {}
    for r in raw:
        try:
            end, filed, val = r["end"], r["filed"], float(r["val"])
        except (KeyError, TypeError, ValueError):
            continue
        if val <= 0:
            continue
        # latest filing wins for a given period end (restatement)
        prev = per_end.get(end)
        if prev is None or str(filed) > str(prev["filed"]):
            per_end[end] = {"end": end, "filed": filed, "val": val}
    out = []
    for rec in per_end.values():
        filed_ts = pd.Timestamp(rec["filed"])
        pos = int(idx.searchsorted(filed_ts, side="left"))
        if pos >= len(idx):
            continue
        out.append({"avail_pos": pos, "end_ts": pd.Timestamp(rec["end"]),
                    "val": rec["val"], "end": rec["end"]})
    out.sort(key=lambda r: r["avail_pos"])
    return out


def nis_at(series: list[dict], i: int) -> dict | None:
    """Net share issuance at formation position i, or None."""
    avail = [r["avail_pos"] for r in series]
    k = bisect.bisect_right(avail, i - 1)      # usable: avail_pos + 1 <= i
    if k < 2:
        return None
    usable = series[:k]
    now = max(usable, key=lambda r: (r["end_ts"], r["avail_pos"]))
    old_pool = [r for r in usable
                if LOOKBACK_MIN_DAYS <= (now["end_ts"] - r["end_ts"]).days <= LOOKBACK_MAX_DAYS]
    if not old_pool:
        return None
    old = max(old_pool, key=lambda r: (r["end_ts"], r["avail_pos"]))
    ratio = now["val"] / old["val"]
    if ratio <= 0:
        return None
    return {"ratio": ratio, "nis": __import__("math").log(ratio),
            "shares_now": now["val"], "end_now": now["end"],
            "end_old": old["end"], "shares_old": old["val"],
            "gap_days": (now["end_ts"] - old["end_ts"]).days}


def split_suspect(ratio: float) -> bool:
    """True when the ratio is within 1.5% of a whole split factor or its inverse."""
    for k in SPLIT_K:
        if abs(ratio / k - 1.0) <= SPLIT_TOL:
            return True
        if abs(ratio * k - 1.0) <= SPLIT_TOL:
            return True
    return False


# ───────────────────────────────────────────────────────── statistics ──
def _pct(vals, p):
    s = sorted(vals)
    if not s:
        return None
    k = (len(s) - 1) * p / 100.0
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def winsorise(vals: list[float]) -> list[float]:
    lo, hi = _pct(vals, WINSOR_PCT[0]), _pct(vals, WINSOR_PCT[1])
    if lo is None or hi is None or hi <= lo:
        return list(vals)
    return [min(max(v, lo), hi) for v in vals]


def _month_end_positions(idx) -> list[int]:
    import pandas as pd
    ser = pd.Series(range(len(idx)), index=idx)
    return [int(v) for v in ser.groupby([idx.year, idx.month]).max().tolist()]


# ───────────────────────────────────────────────────────────── build ──
def build(names: list[dict], closes, opens, idx, month_ends: list[int],
          cost_bp: float, haircut_pct: float) -> tuple[list[dict], list[dict], dict]:
    n_idx = len(idx)
    records: list[dict] = []
    months: list[dict] = []
    stats = {"formations": 0, "formations_used": 0, "skipped_sparse": 0,
             "skipped_no_exit": 0, "skipped_split": 0, "skipped_no_lookback": 0,
             "in_band_total": 0, "delisted": 0, "missing_open": 0,
             "leg_sizes": []}
    for m_pos, i in enumerate(month_ends):
        if i + 1 >= n_idx:
            continue
        stats["formations"] += 1
        asof = idx[i].strftime("%Y-%m-%d")
        rows = []
        for nm in names:
            got = nis_at(nm["series"], i)
            if got is None:
                stats["skipped_no_lookback"] += 1
                continue
            if split_suspect(got["ratio"]):
                stats["skipped_split"] += 1
                continue
            tk = nm["ticker"]
            if tk not in closes.columns or tk not in opens.columns:
                continue
            px = float(closes[tk].iloc[i])
            if not (px == px) or px <= MIN_PRICE - 1e-9:
                continue
            cap = got["shares_now"] * px
            if not (CAP_LO <= cap <= CAP_HI):
                continue
            rows.append((got["nis"], nm, cap))
        if len(rows) < 5 * MIN_NAMES_PER_LEG // 5:      # >= one quintile with 1 name
            stats["skipped_sparse"] += 1
            continue
        # exit = close of the next month end
        nxt = [m for m in month_ends[m_pos + 1:] if m > i + 1]
        if not nxt:
            stats["skipped_no_exit"] += 1
            continue
        entry_pos, exit_pos = i + 1, nxt[0]
        stats["formations_used"] += 1
        stats["in_band_total"] += len(rows)

        nis_vals = winsorise([r[0] for r in rows])
        zs = H149._zscore(nis_vals)
        order = sorted(range(len(rows)), key=lambda j: nis_vals[j])
        qsize = len(order) / 5.0
        quint = {}
        for rank, j in enumerate(order):
            quint[j] = min(int(rank // qsize), 4)

        hold_days = exit_pos - entry_pos
        formed: list[dict] = []
        for j, ((nis_raw, nm, cap), z) in enumerate(zip(rows, zs)):
            tk = nm["ticker"]
            p0 = float(opens[tk].iloc[entry_pos])
            if not (p0 == p0) or p0 <= 0:
                stats["missing_open"] += 1
                continue
            p1 = float(closes[tk].iloc[exit_pos])
            delisted = False
            if not (p1 == p1):
                traded = closes[tk].iloc[entry_pos + 1:exit_pos + 1].dropna()
                if traded.empty:
                    continue
                p1, delisted = float(traded.iloc[-1]), True
                stats["delisted"] += 1
            gross_pct = (p1 / p0 - 1.0) * 100.0
            if delisted:
                gross_pct += haircut_pct
            net_pct = gross_pct - cost_bp / 100.0
            rec = {"ticker": tk, "entry_date": asof,
                   "resolved_at": idx[exit_pos].strftime("%Y-%m-%d"),
                   "status": "WON" if net_pct > 0 else "LOST",
                   "pnl_pct": net_pct, "gross_pct": gross_pct,
                   # score points toward EXPECTED RETURN, so it is -z(NIS)
                   "gpa_score": -z, "nis_z": z, "nis_raw": nis_raw,
                   "nis_winsorised": nis_vals[j], "quintile": quint[j],
                   "delisted": delisted, "hold_days": hold_days}
            formed.append(rec)
            records.append(rec)
        if not formed:
            continue
        long_leg = [r for r in formed if r["quintile"] == 0]
        short_leg = [r for r in formed if r["quintile"] == 4]
        if not long_leg or not short_leg:
            continue
        stats["leg_sizes"].append([len(long_leg), len(short_leg)])
        months.append({
            "formation": asof, "resolved_at": idx[exit_pos].strftime("%Y-%m-%d"),
            "n_long": len(long_leg), "n_short": len(short_leg),
            "long_net_pct": round(sum(r["pnl_pct"] for r in long_leg) / len(long_leg), 4),
            "short_net_pct": round(sum(r["pnl_pct"] for r in short_leg) / len(short_leg), 4),
            "universe_net_pct": round(sum(r["pnl_pct"] for r in formed) / len(formed), 4),
            "ls_net_pct": round((sum(r["pnl_pct"] for r in long_leg) / len(long_leg))
                                - (sum(r["pnl_pct"] for r in short_leg) / len(short_leg)), 4),
            "hold_days": hold_days,
        })
    return records, months, stats


# ──────────────────────────────────────────────────────── factor fit ──
def factor_fit(months: list[dict]) -> dict:
    """FF4 on the monthly long-short series (the month held)."""
    try:
        ff = H149._ff_monthly()
    except Exception as exc:              # noqa: BLE001 - network shape varies
        return {"available": False, "reason": f"{type(exc).__name__}: {exc}"}
    if not ff:
        return {"available": False, "reason": "FF5 file parsed to zero rows"}
    obs = []
    for m in months:
        y, mo = int(m["formation"][:4]), int(m["formation"][5:7]) + 1
        if mo == 13:
            y, mo = y + 1, 1
        key = f"{y}{mo:02d}"
        fac = ff.get(key)
        if fac is None:
            continue
        # long-short is already a spread: hold it at face value, no compounding
        obs.append({"month": key, "y": m["ls_net_pct"] / 100.0,
                    **{c: fac[c] for c in H149.FACTOR_COLS}})
    overlapping = H149._ols(obs)
    if overlapping is None:
        return {"available": False,
                "reason": f"only {len(obs)} months with factor data; 12 needed",
                "usable_months": len(obs)}
    non_overlapping = H149._ols(obs[::2])
    alpha_m = overlapping["alpha_pct_monthly"] / 100.0
    resid = []
    for r in obs:
        fitted = sum(overlapping["betas"][c] * r[c] for c in H149.FACTOR_COLS)
        resid.append(r["y"] - alpha_m - fitted)
    dof = max(len(resid) - 5, 1)
    sd_resid = (sum(x * x for x in resid) / dof) ** 0.5
    appraisal = (alpha_m / sd_resid * (12 ** 0.5)) if sd_resid > 0 else None
    raw = [m["ls_net_pct"] for m in months]
    mean_raw = sum(raw) / len(raw)
    sd_raw = (sum((x - mean_raw) ** 2 for x in raw) / max(len(raw) - 1, 1)) ** 0.5
    ir_raw = (mean_raw / sd_raw * (12 ** 0.5)) if sd_raw > 0 else None
    diffs = [m["long_net_pct"] - m["universe_net_pct"] for m in months]
    dm = sum(diffs) / len(diffs)
    dv = sum((x - dm) ** 2 for x in diffs) / max(len(diffs) - 1, 1)
    ir_univ = (dm / (dv ** 0.5) * (12 ** 0.5)) if dv > 0 else None
    return {
        "available": True,
        "model": "ls_net = alpha + b*MKT + s*SMB + h*HML + r*RMW",
        "month_assignment": "factor month = month AFTER formation (the month held)",
        "overlapping": overlapping,
        "non_overlapping": non_overlapping,
        "appraisal_ratio_ff4": round(appraisal, 3) if appraisal is not None else None,
        "ir_long_short_raw": round(ir_raw, 3) if ir_raw is not None else None,
        "ir_long_leg_vs_universe": round(ir_univ, 3) if ir_univ is not None else None,
        "tracking_error_monthly_pct": round(100.0 * sd_resid, 4),
        "ir_basis": ("appraisal ratio = monthly alpha / sd(FF4 residuals) * sqrt(12); "
                     "the model-free IR of the raw spread is reported beside it because "
                     "the FF4 fit can absorb part of the signal"),
    }


# ─────────────────────────────────────────────────────────── verdict ──
def verdict_of(harness: dict, months: list[dict], factors: dict, stats: dict) -> dict:
    alpha_t = ((factors.get("overlapping") or {}).get("alpha_t")
               if factors.get("available") else None)
    appraisal = factors.get("appraisal_ratio_ff4") if factors.get("available") else None
    raw_spread = (sum(m["ls_net_pct"] for m in months) / len(months)) if months else None
    leg_sizes = stats.get("leg_sizes") or []
    median_leg = None
    if leg_sizes:
        flat = sorted(min(a, b) for a, b in leg_sizes)
        median_leg = flat[len(flat) // 2]
    alt_t = ((factors.get("non_overlapping") or {}).get("alpha_t")
             if factors.get("available") else None)
    alt_alpha = ((factors.get("non_overlapping") or {}).get("alpha_pct_monthly")
                 if factors.get("available") else None)
    alpha_pct = ((factors.get("overlapping") or {}).get("alpha_pct_monthly")
                 if factors.get("available") else None)
    same_sign_alpha = (alpha_pct is not None and alt_alpha is not None
                       and (alpha_pct >= 0) == (alt_alpha >= 0))
    gates = {
        "harness_admissible_positive": bool(harness.get("admissible")
                                            and harness.get("sign") == "+"),
        "min_names_per_leg_100": bool(median_leg is not None
                                      and median_leg >= MIN_NAMES_PER_LEG),
        "min_months_36": len(months) >= MIN_MONTHS,
        "cost_survival_ge_0_60": (harness.get("cost_survival") is not None
                                  and harness["cost_survival"] >= COST_SURVIVAL_MIN),
        "factor_alpha_t_ge_2": (alpha_t is not None and alpha_t >= ALPHA_T_MIN),
        "appraisal_ge_0_5": (appraisal is not None and appraisal >= APPRAISAL_MIN),
        "appraisal_sign_matches_spread": (appraisal is not None and raw_spread is not None
                                          and (appraisal >= 0) == (raw_spread >= 0)),
        "raw_spread_positive": (raw_spread is not None and raw_spread > 0),
        "alpha_fit_sign_stable": same_sign_alpha,
    }
    passed = all(gates.values())
    failed = [k for k, v in gates.items() if not v]
    return {
        "gates": gates,
        "failed_gates": failed,
        "passed": passed,
        "verdict": "PROVEN_CANDIDATE" if passed else "NOT_PROVEN",
        "measured": {"raw_ls_spread_net_pct": round(raw_spread, 4) if raw_spread is not None else None,
                     "alpha_pct_monthly": alpha_pct, "alpha_t": alpha_t,
                     "appraisal_ratio_ff4": appraisal,
                     "median_names_per_leg": median_leg,
                     "months": len(months),
                     "harness_sign": harness.get("sign"),
                     "harness_verdict": harness.get("verdict"),
                     "cost_survival": harness.get("cost_survival")},
        "rule": ("every frozen gate must pass. Any single failure is NOT_PROVEN; the "
                 "spec is not re-ranked after seeing the result."),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", default="2015-01-01")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--window-days", type=int, default=14)
    ap.add_argument("--min-months", type=int, default=36)
    ap.add_argument("--max-names", type=int, default=0,
                    help="0 = every cached filer (the lock names no sample size)")
    ap.add_argument("--no-factors", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument("--out", default=str(OUT_JSON))
    args = ap.parse_args()

    H = H149.load_harness()
    chk = H149.harness_self_check(H)
    print(f"# harness observed={chk['observed']} unmodified={chk['unmodified']}",
          file=sys.stderr)
    if not chk["unmodified"]:
        print("FATAL: harness thresholds differ from published values", file=sys.stderr)
        return 2
    if args.self_check:
        print(json.dumps({"harness": chk, "split_k": SPLIT_K, "split_tol": SPLIT_TOL,
                          "lookback_days": [LOOKBACK_MIN_DAYS, LOOKBACK_MAX_DAYS],
                          "slippage_bps_per_side": SLIPPAGE_BPS,
                          "min_names_per_leg": MIN_NAMES_PER_LEG,
                          "min_months": args.min_months}, indent=2))
        return 0

    import pandas as pd

    tpath = CACHE / "company_tickers.json"
    tickers = json.loads(tpath.read_text(encoding="utf-8"))
    cik_to_tk = {}
    for v in tickers.values():
        try:
            cik_to_tk[int(v["cik_str"])] = str(v["ticker"]).upper()
        except (KeyError, TypeError, ValueError):
            continue
    cached = []
    for p in sorted(CACHE.glob("CIK*.json")):
        try:
            cik = int(p.stem.replace("CIK", ""))
        except ValueError:
            continue
        if cik in cik_to_tk:
            cached.append({"cik": cik, "ticker": cik_to_tk[cik]})
    if args.max_names:
        cached = cached[: args.max_names]
    print(f"# cached filers with a ticker: {len(cached)}", file=sys.stderr)

    closes = H149._download_closes([c["ticker"] for c in cached], args.start, args.end)
    opens = H150._download_field([c["ticker"] for c in cached], args.start, args.end, "Open")
    if closes is None or closes.empty or opens is None or opens.empty:
        print("FATAL: price download failed -- DATA_GAP, nothing tested", file=sys.stderr)
        return 2
    idx = closes.index
    opens = opens.reindex(idx)

    names = []
    for ent in cached:
        tk = ent["ticker"]
        if tk not in closes.columns or tk not in opens.columns:
            continue
        facts = load_facts(ent["cik"])
        if not facts or not facts.get("shares"):
            continue
        ser = share_series(facts, idx)
        if len(ser) < 2:
            continue
        names.append({"ticker": tk, "cik": ent["cik"], "series": ser})
    print(f"# names with share facts and prices: {len(names)}", file=sys.stderr)
    if not names:
        print("FATAL: no names", file=sys.stderr)
        return 2

    cost_bp = 2 * SLIPPAGE_BPS       # 10 bp per side, round trip per leg
    month_ends = [m for m in _month_end_positions(idx)
                  if pd.Timestamp(args.start) <= idx[m] <= pd.Timestamp(args.end)]
    print(f"# {len(month_ends)} month ends; cost {cost_bp} bp round trip per leg",
          file=sys.stderr)

    records, months, stats = build(names, closes, opens, idx, month_ends,
                                   cost_bp, H149.DELIST_HAIRCUT_PCT)
    print(f"# records {len(records)} from {stats['formations_used']} formations "
          f"({stats['skipped_split']} split-suspect drops, "
          f"{stats['skipped_no_lookback']} no 12m lookback)", file=sys.stderr)
    if not records:
        print("FATAL: no records", file=sys.stderr)
        return 2

    harness = H149.evaluate(records, H, args.window_days)
    factors = ({"available": False, "reason": "--no-factors"}
               if args.no_factors else factor_fit(months))
    ver = verdict_of(harness, months, factors, stats)

    rec2, months2, _ = build(names, closes, opens, idx, month_ends,
                             cost_bp * STRESS_COST_MULT, H149.DELIST_HAIRCUT_PCT)
    stress = H149.evaluate(rec2, H, args.window_days)
    stress_spread = (sum(m["ls_net_pct"] for m in months2) / len(months2)) if months2 else None

    payload = {
        "hypothesis": "H-151 net share issuance (bottom-minus-top quintile, one-month hold)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": "tools/h151_net_issuance.py",
        "registry_status_at_run": "PRE_REGISTERED (result empty)",
        "harness": {"module": "tools/edge_stability_harness.py (imported unmodified)",
                    "self_check": chk, "result": harness},
        "spec": {"universe": f"US common stock, price >= ${MIN_PRICE}, cap "
                             f"${CAP_LO:,.0f}-${CAP_HI:,.0f} at formation",
                 "signal": "NIS = ln(shares_t / shares_{t-4q}), dei:EntityCommonStockSharesOutstanding",
                 "point_in_time": "a filing is usable from filed date + 1 trading session",
                 "split_guard": {"k": list(SPLIT_K), "tol": SPLIT_TOL,
                                 "drops": stats["skipped_split"]},
                 "winsorise_pct": list(WINSOR_PCT),
                 "book": "quintiles, bottom long / top short, equal weight, one-month hold",
                 "entry": "next session OPEN after the month-end close",
                 "exit": "close of the next month end",
                 "slippage_bps_per_side": SLIPPAGE_BPS,
                 "round_trip_bp_per_leg": cost_bp,
                 "window_days": args.window_days,
                 "date_range": [args.start, args.end],
                 "score_convention": "gpa_score = -z(NIS) so that higher score = expected "
                                     "higher return, which is what the harness measures"},
        "universe": {"cached_filers_with_ticker": len(cached),
                     "names_with_share_facts_and_prices": len(names),
                     "records": len(records),
                     "formations_used": stats["formations_used"],
                     "stats": {k: v for k, v in stats.items() if k != "leg_sizes"}},
        "book": {"months": months,
                 "raw_ls_spread_net_pct": ver["measured"]["raw_ls_spread_net_pct"],
                 "median_names_per_leg": ver["measured"]["median_names_per_leg"],
                 "long_leg_wr_pct": (round(100.0 * sum(1 for r in records
                                                       if r["quintile"] == 0 and r["pnl_pct"] > 0)
                                           / max(sum(1 for r in records if r["quintile"] == 0), 1), 2))},
        "factor_regression": factors,
        "cost_stress_2x": {"round_trip_bp_per_leg": cost_bp * STRESS_COST_MULT,
                           "result": stress,
                           "raw_ls_spread_net_pct": (round(stress_spread, 4)
                                                     if stress_spread is not None else None)},
        "verdict": ver,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print()
    print(f"months {len(months)}, records {len(records)}, median leg "
          f"{ver['measured']['median_names_per_leg']} names")
    print(f"long-short raw net {ver['measured']['raw_ls_spread_net_pct']}%/month "
          f"(2x-cost stress {payload['cost_stress_2x']['raw_ls_spread_net_pct']}%)")
    print(f"harness {harness['verdict']} windows {harness['windows_scored']} "
          f"strong {harness['windows_strong']} sign {harness['sign']} "
          f"cost_survival {harness['cost_survival']}")
    if factors.get("available"):
        ov = factors["overlapping"]
        print(f"FF4 alpha {ov['alpha_pct_monthly']}%/mo t={ov['alpha_t']} R2 {ov['r_squared']} "
              f"appraisal {factors['appraisal_ratio_ff4']}")
    print(f"VERDICT: {ver['verdict']} — failed gates {ver['failed_gates']}")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
