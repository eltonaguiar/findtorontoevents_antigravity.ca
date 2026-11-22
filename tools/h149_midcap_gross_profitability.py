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
import io
import json
import os
import random
import re
import sys
import zipfile
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
TOP_QUINTILE_Z = 0.8416   # 80th percentile: the book the pre-registered spec holds
MIN_BOOK_N = 5            # a formation with fewer top-quintile names is not a portfolio
DELIST_HAIRCUT_PCT = -30.0  # Shumway/Warther convention for a performance delisting:
                           # exit at the last available close, then charge the penalty


# ──────────────────────────────────────────────────────────────── prices ──
def _download_closes(tickers: list[str], start: str, end: str,
                     chunk: int = 80, retries: int = 3):
    """Download adjusted daily closes in chunks, keeping whatever survives.

    One yf.download call for ~600 tickers is throttled or silently truncated by
    Yahoo, which loses every name at once. Chunking with a pause and a retry
    degrades to "some chunks fewer tickers" instead of "no price data".
    """
    import time

    import pandas as pd
    import yfinance as yf

    tickers = list(dict.fromkeys(tickers))
    frames = []
    for i in range(0, len(tickers), chunk):
        part = tickers[i:i + chunk]
        for attempt in range(1, retries + 1):
            try:
                raw = yf.download(part, start=start, end=end, interval="1d",
                                  progress=False, auto_adjust=True, threads=True)
            except Exception as exc:  # noqa: BLE001 - network layer varies
                print(f"  .. prices chunk {i//chunk+1} attempt {attempt} raised "
                      f"{type(exc).__name__}: {exc}", file=sys.stderr)
                raw = None
            if raw is not None and not getattr(raw, "empty", True):
                df = raw["Close"] if getattr(raw.columns, "nlevels", 1) > 1 else raw
                frames.append(df)
                print(f"  .. prices {min(i + chunk, len(tickers))}/{len(tickers)} "
                      f"({df.shape[1]} tickers returned in chunk {i//chunk+1})",
                      file=sys.stderr)
                break
            time.sleep(2 * attempt)
        else:
            print(f"  .. prices chunk {i//chunk+1}: no data after {retries} tries",
                  file=sys.stderr)
        time.sleep(1.0)
    if not frames:
        return None
    out = pd.concat(frames, axis=1)
    return out.loc[:, ~out.columns.duplicated()].dropna(axis=1, how="all")


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
                  cost_bp: float,
                  delist_haircut_pct: float = DELIST_HAIRCUT_PCT) -> tuple[list[dict], dict]:
    records: list[dict] = []
    stats = {"rebalances": 0, "skipped_sparse": 0, "in_band_total": 0,
             "rebalances_used": 0, "delisted": 0}
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
            series = closes[nm["ticker"]]
            p0 = series.iloc[i]
            if not (p0 == p0) or p0 <= 0:
                continue
            p1 = series.iloc[j]
            delisted = False
            if not (p1 == p1):
                # the series ends inside the holding window: this is a delisting,
                # not a missing observation. Skipping it truncates the left tail,
                # which is exactly where the losers live.
                traded = series.iloc[i + 1:j + 1].dropna()
                if traded.empty:
                    continue          # entered and never traded again: no exit price
                p1 = traded.iloc[-1]
                delisted = True
                stats["delisted"] += 1
            gross_pct = (p1 / p0 - 1.0) * 100.0
            if delisted:
                gross_pct += delist_haircut_pct
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
                "delisted": delisted,
            })
    return records, stats



# ───────────────────────────────────────────────────── factor regression ──
FF5_URL = ("https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
           "F-F_Research_Data_5_Factors_2x3_CSV.zip")
FF_CACHE = ROOT / "tools" / "cache" / "ff5_monthly.csv"
FACTOR_COLS = ("Mkt-RF", "SMB", "HML", "RMW")


def _ff_monthly(refresh: bool = False) -> dict:
    """Monthly Fama-French 5-factor returns as {"YYYYMM": {factor: float}}."""
    if FF_CACHE.exists() and not refresh:
        text = FF_CACHE.read_text(encoding="utf-8")
    else:
        raw = urllib.request.urlopen(
            urllib.request.Request(FF5_URL, headers={"User-Agent": SEC_UA}),
            timeout=60).read()
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            name = [n for n in zf.namelist() if n.lower().endswith(".csv")][0]
            text = zf.read(name).decode("latin-1")
        FF_CACHE.parent.mkdir(parents=True, exist_ok=True)
        FF_CACHE.write_text(text, encoding="utf-8")
        print(f"  .. fetched FF5 monthly factors -> {FF_CACHE.name}", file=sys.stderr)
    out = {}
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if not parts or not re.fullmatch(r"\d{6}", parts[0]):
            continue                      # header, copyright lines and annual rows
        try:
            out[parts[0]] = {c: float(parts[1 + i]) / 100.0
                             for i, c in enumerate(FACTOR_COLS)}
            out[parts[0]]["RF"] = float(parts[5]) / 100.0
        except (ValueError, IndexError):
            continue
    return out


def _ols(rows: list) -> dict | None:
    """Excess return on [1, MKT, SMB, HML, RMW]: plain OLS, classical t-stats.

    Twelve observations is the floor for a five-parameter fit to mean anything.
    """
    import numpy as np
    if len(rows) < 12:
        return None
    y = np.array([r["y"] for r in rows])
    X = np.array([[1.0] + [r[c] for c in FACTOR_COLS] for r in rows])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = len(y) - X.shape[1]
    if dof <= 1:
        return None
    try:
        cov = (float(resid @ resid) / dof) * np.linalg.inv(X.T @ X)
    except np.linalg.LinAlgError:
        return None
    se = np.sqrt(np.diag(cov))
    ss_tot = float(((y - y.mean()) ** 2).sum())
    names = ("const",) + FACTOR_COLS
    return {
        "n_months": len(rows),
        "alpha_pct_monthly": round(100.0 * float(beta[0]), 4),
        "alpha_t": round(float(beta[0] / se[0]), 2) if se[0] > 0 else None,
        "alpha_pct_annualised": round(100.0 * ((1.0 + float(beta[0])) ** 12 - 1.0), 2),
        "betas": {c: round(float(beta[1 + i]), 3) for i, c in enumerate(FACTOR_COLS)},
        "t_stats": {n: (round(float(beta[k] / se[k]), 2) if se[k] > 0 else None)
                    for k, n in enumerate(names)},
        "r_squared": round(1.0 - float(resid @ resid) / ss_tot, 3) if ss_tot > 0 else None,
    }


def factor_regression(records: list, cost_note: str = "") -> dict:
    """Is the quality book alpha, or MKT/SMB/HML/RMW exposure in disguise?

    The pre-registered benchmark is the FF 4-factor set, so the honest question
    is whether the intercept survives those four. Returns are already net of the
    round-trip cost charged in build_records().
    """
    try:
        ff = _ff_monthly()
    except Exception as exc:                      # noqa: BLE001 - network shape varies
        return {"available": False, "reason": f"{type(exc).__name__}: {exc}"}
    if not ff:
        return {"available": False, "reason": "FF5 file parsed to zero rows"}

    by_date = {}
    for r in records:
        by_date.setdefault(r["entry_date"], []).append(r)

    obs = []
    for d in sorted(by_date):
        sel = [r for r in by_date[d] if r["gpa_score"] >= TOP_QUINTILE_Z]
        if len(sel) < MIN_BOOK_N:
            continue
        book_pct = sum(r["pnl_pct"] for r in sel) / len(sel)
        # a 40-trading-day return restated as a monthly equivalent
        monthly = (1.0 + book_pct / 100.0) ** (21.0 / HOLD_DAYS) - 1.0
        y, m = int(d[:4]), int(d[5:7]) + 1
        if m == 13:
            y, m = y + 1, 1
        key = f"{y}{m:02d}"
        fac = ff.get(key)
        if fac is None:
            continue                              # factor file does not reach this month
        obs.append({"month": key, "y": monthly - fac["RF"], "book_n": len(sel),
                    **{c: fac[c] for c in FACTOR_COLS}})

    overlapping = _ols(obs)
    if overlapping is None:
        return {"available": False,
                "reason": (f"only {len(obs)} usable monthly formation(s) with >={MIN_BOOK_N} "
                           "top-quintile names and factor data; 12 needed"),
                "usable_formations": len(obs)}
    # 40 trading days is ~2 months, so every 2nd formation breaks the overlap
    non_overlapping = _ols(obs[::2])
    return {
        "available": bool(overlapping),
        "source": ("Fama-French 5 factors (2x3), monthly, Ken French data library; "
                   f"cached at {FF_CACHE.relative_to(ROOT)}"),
        "model": "r_book - RF = alpha + b*MKT + s*SMB + h*HML + r*RMW",
        "book": f"equal-weight names with gpa_zscore >= {TOP_QUINTILE_Z} (top quintile)",
        "return_conversion": (f"{HOLD_DAYS}-trading-day net return compounded to a monthly "
                              f"equivalent at 21/{HOLD_DAYS}"),
        "month_assignment": "factor month = month AFTER formation (the month held)",
        "overlapping": overlapping,
        "non_overlapping": non_overlapping,
        "overlap_note": ("consecutive formations overlap by ~10 trading days, so the full series "
                         "is autocorrelated; the every-2nd-month fit is the one to trust for "
                         "significance and both are reported"),
        "cost_note": cost_note,
        "interpretation_rule": ("alpha_t >= 2 with the four factors partialled out means the tilt "
                                "is not mere factor exposure; alpha_t near 0 with high R2 means "
                                "it is"),
    }


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
    ap.add_argument("--sample-n", type=int, default=1900,
                    help="CIKs drawn from the SEC ticker file. ~33%% of random "
                         "filers clear the annual-10-K GrossProfit+Assets filter, "
                         "so 1900 is sized to land near 600 usable names and "
                         "~80 records per 14-day harness window")
    ap.add_argument("--seed", type=int, default=149)
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--window-days", type=int, default=14)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--no-network", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument("--out", default=str(OUT_JSON))
    ap.add_argument("--no-factors", action="store_true",
                    help="skip the Fama-French regression instead of fetching factors")
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
    names_before_prices = len(names)
    print(f"# usable names with >=2 annual 10-K GP and Assets: {len(names)}",
          file=sys.stderr)
    if not names:
        print("FATAL: no usable names — nothing to test (DATA_GAP).", file=sys.stderr)
        return 2

    # ---- prices ------------------------------------------------------------
    import pandas as pd
    import yfinance as yf

    tickers_list = [n["ticker"] for n in names]
    print(f"# downloading daily prices for {len(tickers_list)} tickers in chunks",
          file=sys.stderr)
    closes = _download_closes(tickers_list, args.start, args.end)
    if closes is None or closes.empty:
        print("FATAL: no price data returned", file=sys.stderr)
        return 2
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

    # what the declared delisting convention actually changes
    delisted = [r for r in records if r.get("delisted")]
    no_haircut, _ = build_records(names, closes, idx, rebal_dates, cost_bp,
                                  delist_haircut_pct=0.0)
    book_nh = top_decile_book(no_haircut)
    delisting = {
        "rule": ("a name whose price series ends inside the holding window exits at its last "
                 "available close and is charged a declared haircut; names with no price at the "
                 "rebalance (never enterable) are still dropped and counted separately"),
        "haircut_pct": DELIST_HAIRCUT_PCT,
        "records_exiting_on_last_trade": len(delisted),
        "pct_of_records": round(100.0 * len(delisted) / max(1, len(records)), 2),
        "mean_pnl_pct_delisted": (round(sum(r["pnl_pct"] for r in delisted) / len(delisted), 4)
                                  if delisted else None),
        "bottom_bucket_with_haircut": {"n": book["n_bottom"],
                                       "net_mean_pct": book["net_mean_pct_bottom"]},
        "bottom_bucket_without_haircut": {"n": book_nh["n_bottom"],
                                          "net_mean_pct": book_nh["net_mean_pct_bottom"]},
        "names_never_priceable": names_before_prices - len(names),
    }
    print(f"# delisting: {len(delisted)} record(s) exit on last trade "
          f"({delisting['pct_of_records']}%); bottom bucket "
          f"{book_nh['net_mean_pct_bottom']}% -> {book['net_mean_pct_bottom']}%",
          file=sys.stderr)
    gap = density_gap(records, H, args.window_days)

    # stress cost
    stress_records, _ = build_records(names, closes, idx, rebal_dates,
                                     cost_bp * STRESS_COST_MULT)
    stress = evaluate(stress_records, H, args.window_days)

    if args.no_factors:
        fr = {"available": False, "reason": "skipped by --no-factors"}
    else:
        print("# factor regression: excess return on MKT/SMB/HML/RMW", file=sys.stderr)
        fr = factor_regression(records, cost_note=f"{cost_bp} bp round-trip")

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
            "fundamentals_yield_pct": round(100.0 * len(names) / max(1, len(sample)), 1),
            "rebalances_total": stats["rebalances"],
            "rebalances_used": stats["rebalances_used"],
            "records_exiting_on_last_trade": stats["delisted"],
            "rebalances_skipped_sparse": stats["skipped_sparse"],
            "in_band_observations": stats["in_band_total"],
            "records": len(records),
        },
        "result": res,
        "stress_result": {k: stress[k] for k in
                          ("verdict", "admissible", "windows_scored", "net_edge_pct",
                           "gross_edge_pct", "cost_survival", "sign")},
        "top_decile_book": book,
        "factor_regression": fr,
        "delisting": delisting,
        "density_gap": gap,
        "limits": [
            "Universe is a random sample of CURRENTLY REGISTERED SEC filers. Firms "
            "that delisted and stopped filing entirely are under-represented, so "
            "survivorship bias is reduced but not eliminated.",
            "Cross-section includes financials and REITs, for which GP/A is not "
            "meaningful; per-name noise dilution is not corrected.",
            "MKT/SMB/HML/RMW are now regressed out on a monthly series built from these "
            "same records, but the fit inherits every other limitation listed here: it can "
            "separate factor exposure from alpha, it cannot rescue a book whose per-window "
            "eff flips sign.",
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
    if fr.get("available"):
        ov, nov = fr["overlapping"], fr["non_overlapping"]
        print(f"  factor alpha={ov['alpha_pct_monthly']}%/mo (t={ov['alpha_t']}) "
              f"betas={ov['betas']}  R2={ov['r_squared']}  n={ov['n_months']}")
        if nov:
            print(f"  non-overlapping alpha={nov['alpha_pct_monthly']}%/mo "
                  f"(t={nov['alpha_t']}, n={nov['n_months']})")
    else:
        print(f"  factor regression unavailable: {fr.get('reason')}")
    if res["verdict"] == "UNTESTED":
        print(f"  DATA GAP: {gap.get('shortfall_records')} more records needed; "
              f"{gap.get('names_needed_to_reach_density')}x the current name count "
              f"would reach {H.MIN_WINDOW_N}/window")
    if delisted:
        print(f"  delisting: {len(delisted)} exit(s) on last trade, mean "
              f"{delisting['mean_pnl_pct_delisted']}%  bottom bucket "
              f"{delisting['bottom_bucket_without_haircut']['net_mean_pct']}% -> "
              f"{delisting['bottom_bucket_with_haircut']['net_mean_pct']}%")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
