#!/usr/bin/env python3
"""H-033 EQUITY residualized overnight-return cross-sectional reversal — research.

OPT-IN RESEARCH SIDECAR. No production wiring. No caller in quality_gates.py,
dashboard_generator.py, or any pick-generation / scoring path. It fetches free
yfinance data, runs the pre-registered signal through the edge-stability
harness (imported UNMODIFIED), and writes a report — nothing else.

------------------------------------------------------------------------------
PRE-REGISTERED HYPOTHESIS (registry key tier2_2026_05_19, id H-033)
------------------------------------------------------------------------------
Each trading day D, for a fixed basket of liquid large/mid-cap US equities:
  * overnight return  ON_i  = open_D / close_{D-1} - 1
  * market overnight  MKT   = cross-sectional mean of ON across the basket on D
  * residualize       resid_i = ON_i - beta_i * MKT
        beta_i from a STRICTLY-PAST rolling 60-day regression of ON_i on MKT
        (day D excluded).
  * cross-sectionally rank residuals:
        LONG  the bottom-quintile residuals (most-negative overnight surprise)
        SHORT the top-quintile residuals    (most-positive overnight surprise)
  * ENTER at the open of D, EXIT at the close of D (intraday hold, 1 day).

Continuous-position multi-asset book: every instrument-day in a ranked quintile
is one resolved record. signal_z (the score the harness reads) = |residual
z-score| on quintile days, 0 otherwise. The harness eff then answers exactly
the H-033 question: do the extreme-residual cross-sectional picks separate
winners from losers stably across walk-forward windows?

STRICT NO-LOOK-AHEAD: beta uses only ON pairs from D-61..D-1; the overnight
return uses close_{D-1} and open_D, both known at the open of D; the trade
enters at open_D and exits at close_D — no future bar is read.

------------------------------------------------------------------------------
THE VERDICT GATE
------------------------------------------------------------------------------
Records fed through tools/edge_stability_harness.evaluate() UNMODIFIED.
ADMISSIBLE iff |eff| >= 0.30, same sign, >= 3 of 5 walk-forward 14-day windows.
A 30bps round-trip post-cost gate: cost-survival = fraction of QUALIFYING
quintile picks whose |gross return| exceeds 30bps; verdict downgraded if
cost-survival < 60%. A gaudy in-sample WR is NOT a pass.

    python tools/h033_overnight_xs_reversal.py [--quick] [--json]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        if hasattr(_s, "reconfigure"):
            try:
                _s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                pass

import edge_stability_harness as harness  # noqa: E402

CACHE = ROOT / "tools" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)
CACHE_FILE = CACHE / "h033_overnight_cache.json"

# ---- Pre-registered tunables (signal family fixed — no per-window search) ----
BETA_LOOKBACK = 60         # strictly-past rolling overnight-beta regression
QUINTILE = 0.20            # top / bottom quintile of cross-sectional residuals
WINDOW_DAYS = 14
HARNESS_FIELD = "signal_z"
POST_COST_BPS = 30
COST_SURVIVAL_MIN = 0.60
MIN_BASKET_DAY = 10        # need >=10 names with data on a day to rank a quintile

# Fixed pre-registered basket of liquid large/mid-cap US equities (deep
# yfinance history, tight spreads). Fixed in advance — no post-hoc selection.
BASKET_FULL = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "JPM",
               "BAC", "WMT", "XOM", "CVX", "JNJ", "PG", "KO", "PEP", "DIS",
               "NFLX", "INTC", "AMD", "CSCO", "ORCL", "CRM", "ADBE", "QCOM",
               "TXN", "HD", "MCD", "NKE", "COST", "UNH", "PFE", "MRK", "ABBV",
               "T", "VZ", "C", "GS", "MS", "CAT"]
BASKET_QUICK = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "JPM",
                "BAC", "WMT", "XOM", "JNJ"]


# ===========================================================================
# Data fetch — yfinance daily OHLCV
# ===========================================================================
def fetch_yf_ohlcv(ticker: str, period: str = "10y") -> list[dict]:
    """yfinance daily OHLCV bars, ascending by date. [] on failure.

    auto_adjust=False — we need RAW open/close so the overnight return
    open_D/close_{D-1} is the genuine session-gap, not a split-adjusted artefact.
    """
    import warnings
    warnings.filterwarnings("ignore")
    try:
        import yfinance as yf
    except ImportError:
        return []
    df = None
    for _ in range(3):
        try:
            df = yf.download(ticker, period=period, interval="1d",
                             progress=False, auto_adjust=False)
        except Exception:  # noqa: BLE001
            df = None
        if df is not None and len(df) >= BETA_LOOKBACK + 30:
            break
        time.sleep(2)
    if df is None or len(df) < BETA_LOOKBACK + 30:
        return []
    out = []
    cols = {c[0] if isinstance(c, tuple) else c: c for c in df.columns}
    for idx, row in df.iterrows():
        try:
            d = idx.date().isoformat() if hasattr(idx, "date") else str(idx)[:10]
            o = float(row[cols["Open"]]); c = float(row[cols["Close"]])
        except (KeyError, TypeError, ValueError):
            continue
        if o > 0 and c > 0:
            out.append({"date": d, "open": o, "close": c})
    return out


def load_data(tickers: list[str], use_cache: bool = True) -> dict[str, list[dict]]:
    cache: dict = {}
    if use_cache and CACHE_FILE.exists():
        try:
            cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            cache = {}
    out: dict[str, list[dict]] = {}
    for tk in tickers:
        cached = cache.get(tk)
        if cached and len(cached) >= BETA_LOOKBACK + 30:
            out[tk] = cached
            print(f"#   {tk}: {len(cached)} bars (cache)", file=sys.stderr)
            continue
        print(f"# fetching {tk} ...", file=sys.stderr)
        bars = fetch_yf_ohlcv(tk)
        if bars:
            out[tk] = bars
            cache[tk] = bars
            print(f"#   {tk}: {len(bars)} bars", file=sys.stderr)
        else:
            print(f"#   {tk}: SKIP (fetch failed / thin)", file=sys.stderr)
        time.sleep(0.4)
    try:
        CACHE_FILE.write_text(json.dumps(cache), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    return out


# ===========================================================================
# Signal math (pure, network-free)
# ===========================================================================
def _ols_beta(xs: list[float], ys: list[float]) -> float:
    """Slope of y on x via least squares; 0.0 if degenerate."""
    n = len(xs)
    if n < 10:
        return 0.0
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 0:
        return 0.0
    sxy = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    return sxy / sxx


def build_book(data: dict[str, list[dict]]) -> list[dict]:
    """Build the continuous cross-sectional resolved-record book.

    For each ticker, align bars by date; compute the overnight-return series.
    Then for each common trading day D, residualize each name's overnight
    return against the cross-sectional market overnight move and rank.

    Every (ticker, day-D) pair is one resolved record. The record is a
    winner/loser of the H-033 trade direction (LONG bottom-quintile residual,
    SHORT top-quintile, FLAT mid). signal_z = |residual z| on quintile days,
    0 on mid-quintile days.
    """
    # per-ticker overnight series: list of (date, on_ret, open, close)
    series: dict[str, list[tuple]] = {}
    for tk, bars in data.items():
        seq = []
        for i in range(1, len(bars)):
            prev_c = bars[i - 1]["close"]
            o = bars[i]["open"]
            c = bars[i]["close"]
            if prev_c <= 0 or o <= 0:
                continue
            on_ret = o / prev_c - 1.0
            seq.append((bars[i]["date"], on_ret, o, c))
        if len(seq) >= BETA_LOOKBACK + 20:
            series[tk] = seq

    # index each ticker series by date for fast cross-section assembly
    by_date_idx: dict[str, dict[str, int]] = {}
    for tk, seq in series.items():
        by_date_idx[tk] = {row[0]: j for j, row in enumerate(seq)}

    all_dates = sorted({d for tk in series for d in by_date_idx[tk]})
    records: list[dict] = []

    # Precompute, ONCE, the cross-sectional market overnight move for every
    # date — the mean of ON across ALL basket names present on that date. This
    # is the same market series used both for day-D residualization and for the
    # strictly-past beta regression; computing it once keeps the book build
    # O(days x names x lookback) instead of O(days x names^2 x lookback).
    mkt_by_date: dict[str, float] = {}
    for ds in all_dates:
        vals = []
        for tk, seq in series.items():
            j = by_date_idx[tk].get(ds)
            if j is not None:
                vals.append(seq[j][1])
        if vals:
            mkt_by_date[ds] = statistics.fmean(vals)

    for ds in all_dates:
        # cross-section present on day D: names with >= BETA_LOOKBACK prior obs
        present = []
        for tk, seq in series.items():
            j = by_date_idx[tk].get(ds)
            if j is None or j < BETA_LOOKBACK:
                continue
            present.append((tk, j))
        if len(present) < MIN_BASKET_DAY:
            continue
        # market overnight move on day D = precomputed cross-sectional mean
        mkt = mkt_by_date.get(ds)
        if mkt is None:
            continue
        # residualize each name with its STRICTLY-PAST overnight beta.
        # beta_i regresses ON_i on the market overnight move over D-61..D-1;
        # both legs use only data strictly before D — no look-ahead.
        resids = []
        for tk, j in present:
            seq = series[tk]
            past_on = [seq[k][1] for k in range(j - BETA_LOOKBACK, j)]
            past_mkt = [mkt_by_date.get(seq[k][0], 0.0)
                        for k in range(j - BETA_LOOKBACK, j)]
            beta = _ols_beta(past_mkt, past_on)
            on_i = seq[j][1]
            resid = on_i - beta * mkt
            resids.append((tk, j, resid))
        if len(resids) < MIN_BASKET_DAY:
            continue
        # cross-sectional standardisation of residuals on day D
        rv = [r for _, _, r in resids]
        mr = statistics.fmean(rv)
        sr = statistics.pstdev(rv) or 1e-9
        rv_sorted = sorted(rv)
        n = len(rv_sorted)
        lo_thr = rv_sorted[max(0, int(n * QUINTILE) - 1)]
        hi_thr = rv_sorted[min(n - 1, int(n * (1 - QUINTILE)))]
        for tk, j, resid in resids:
            seq = series[tk]
            o = seq[j][2]
            c = seq[j][3]
            z = (resid - mr) / sr
            if resid <= lo_thr:           # bottom quintile -> LONG (fade neg)
                direction = 1
                signal_z = abs(z)
            elif resid >= hi_thr:         # top quintile -> SHORT (fade pos)
                direction = -1
                signal_z = abs(z)
            else:                          # mid -> flat / non-qualifying
                direction = 0
                signal_z = 0.0
            gross_ret = (c / o - 1.0) * direction   # intraday open->close
            qualifies = direction != 0
            if qualifies:
                status = "WON" if gross_ret > 0 else "LOST"
            else:
                # mid-quintile day: still a record for book density but it is a
                # FLAT no-trade — resolve neutrally on its tiny intraday move so
                # the harness sees it as noise (signal_z=0) not a phantom loss.
                status = "WON" if (c / o - 1.0) > 0 else "LOST"
            records.append({
                "status": status,
                "resolved_at": ds,
                "timestamp": ds,
                HARNESS_FIELD: signal_z,
                "gross_ret": round(gross_ret, 6),
                "direction": direction,
                "qualifies": qualifies,
                "instrument": tk,
            })
    return records


# ===========================================================================
# Harness wiring (harness imported UNMODIFIED — loader patched for one call)
# ===========================================================================
def harness_verdict(records: list[dict], window_days: int = WINDOW_DAYS) -> dict:
    orig_load = harness._load
    try:
        harness._load = lambda: records  # type: ignore[assignment]
        verdict = harness.evaluate(HARNESS_FIELD, window_days)
        admissible = harness.is_admissible(HARNESS_FIELD, window_days)
    finally:
        harness._load = orig_load  # type: ignore[assignment]
    verdict["admissible_via_is_admissible"] = admissible
    return verdict


def _signal_recs(records: list[dict]) -> list[dict]:
    sig = [r for r in records if r.get("qualifies")]
    return sig if sig else records


def cost_survival(records: list[dict], bps: int = POST_COST_BPS) -> float:
    sig = _signal_recs(records)
    if not sig:
        return 0.0
    thr = bps / 10000.0
    return round(sum(1 for r in sig if abs(r.get("gross_ret", 0.0)) > thr) / len(sig), 4)


def pooled_wr(records: list[dict]) -> float | None:
    res = [r for r in _signal_recs(records) if r["status"] in ("WON", "LOST")]
    if not res:
        return None
    return round(sum(1 for r in res if r["status"] == "WON") / len(res), 4)


def net_edge_summary(records: list[dict], bps: int = POST_COST_BPS) -> dict:
    sig = _signal_recs(records)
    if not sig:
        return {"gross_mean_ret": None, "net_mean_ret": None, "n_signal_days": 0}
    grs = [r.get("gross_ret", 0.0) for r in sig]
    gross = statistics.fmean(grs)
    return {"gross_mean_ret": round(gross, 6),
            "net_mean_ret": round(gross - bps / 10000.0, 6),
            "n_signal_days": len(sig)}


# ===========================================================================
# Verdict assembly
# ===========================================================================
def assemble_verdict(records: list[dict]) -> dict:
    h = (harness_verdict(records)
         if len(records) >= harness.MIN_WINDOW_N
         else {"admissible": False, "windows_scored": 0,
               "reason": f"INSUFFICIENT DATA — {len(records)} records, harness "
                         f"needs >= {harness.MIN_WINDOW_N}/window"})
    cs = cost_survival(records)
    ne = net_edge_summary(records)
    scored = h.get("windows_scored", 0)
    harness_pass = h.get("admissible", False)
    cost_pass = cs >= COST_SURVIVAL_MIN
    if scored < harness.MIN_STABLE_WINDOWS:
        verdict = "UNTESTED"
    elif harness_pass and cost_pass:
        verdict = "ADMISSIBLE"
    else:
        verdict = "REJECTED"
    return {
        "verdict": verdict,
        "n": len(records),
        "n_signal_days": ne.get("n_signal_days", 0),
        "windows_scored": scored,
        "windows_strong": h.get("windows_strong"),
        "per_window_eff": [e["eff"] for e in h.get("per_window_eff", [])],
        "sign": h.get("sign"),
        "same_sign_ok": (h.get("sign") in ("+", "-")) and harness_pass,
        "harness_admissible": harness_pass,
        "harness_reason": h.get("reason"),
        "pooled_wr": pooled_wr(records),
        "gross_mean_ret": ne["gross_mean_ret"],
        "net_mean_ret": ne["net_mean_ret"],
        "cost_survival": cs,
        "cost_survival_pass": cost_pass,
    }


# ===========================================================================
# Report
# ===========================================================================
def render_report(res: dict) -> str:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    v = res["verdict_block"]
    recs = res["records"]
    effs = " ".join(f"{e:+.2f}" if e is not None else "n/a"
                    for e in v["per_window_eff"])
    next_step = {
        "ADMISSIBLE": "Re-test on a fresh out-of-sample equity period, add full "
                      "commission + bid-ask + open/close auction-slippage modelling, "
                      "run a deflated-Sharpe / SPA multiple-testing correction, then "
                      "operator review. Harness pass is necessary, not sufficient. "
                      "No wiring.",
        "REJECTED": "Clean kill. The residualized overnight-return cross-sectional "
                    "reversal does not separate winners from losers with a stable "
                    "sign across enough 14-day windows (or fails the 30bps cost "
                    "gate). Do not wire or size. Archive as a tested failure.",
        "UNTESTED": "Honest non-verdict — the harness did not get >= 3 scored "
                    "14-day windows. Blocker is sample coverage, not design.",
    }[v["verdict"]]
    out = [
        "# H-033 EQUITY residualized overnight-return cross-sectional reversal — 2026-05-19",
        "",
        f"_Generated {ts} by `tools/h033_overnight_xs_reversal.py`._",
        "",
        "**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** Fetches free "
        "yfinance data, runs the pre-registered signal through "
        "`edge_stability_harness` (imported UNMODIFIED), writes this report.",
        "",
        "## Pre-registered hypothesis (registry `tier2_2026_05_19` / H-033)",
        "",
        "Each trading day D rank a fixed basket of liquid large/mid-cap US "
        "equities by their overnight return `open_D/close_{D-1}-1` RESIDUALIZED "
        "against the cross-sectional market overnight move (overnight beta from a "
        "strictly-past 60-day regression). LONG the bottom-quintile residuals, "
        "SHORT the top-quintile; enter at the open of D, exit at the close of D.",
        "",
        "**No-look-ahead:** beta uses only D-61..D-1; the overnight return uses "
        "`close_{D-1}` and `open_D` both known at the open of D; entry open_D, "
        "exit close_D — no future bar read.",
        "",
        "## Data",
        "",
        "- yfinance daily OHLCV (raw open + close, `auto_adjust=False`), free, "
        "no key. Cached to `tools/cache/h033_overnight_cache.json`.",
        f"- Fixed basket tickers with usable history: {len(res['per_tk'])}.",
        f"- Continuous cross-sectional resolved records: **{len(recs)}**.",
        f"- Of which qualifying top/bottom-quintile picks: "
        f"**{v['n_signal_days']}**.",
        "",
        "## Harness verdict (THE gate — harness imported UNMODIFIED)",
        "",
        f"- per-window eff (new->old): `{effs}`",
        f"- windows scored: {v['windows_scored']}  (strong: {v['windows_strong']})",
        f"- sign: `{v['sign']}`  same-sign ok: {v['same_sign_ok']}",
        f"- harness `is_admissible()`: {v['harness_admissible']}",
        f"- harness reason: {v['harness_reason']}",
        "",
        "## Edge & cost survival (over the qualifying quintile picks)",
        "",
        (f"- pooled WR: {v['pooled_wr']*100:.2f}%"
         if v['pooled_wr'] is not None else "- pooled WR: n/a"),
        f"- gross mean per-trade return: {v['gross_mean_ret']}",
        f"- net mean per-trade return (after 30bps): {v['net_mean_ret']}",
        f"- cost-survival (|gross| > 30bps): {v['cost_survival']*100:.1f}%  "
        f"(gate >= {COST_SURVIVAL_MIN*100:.0f}%: "
        f"{'PASS' if v['cost_survival_pass'] else 'FAIL'})",
        "",
        f"## VERDICT: **{v['verdict']}**",
        "",
        next_step,
        "",
    ]
    return "\n".join(out)


# ===========================================================================
# Orchestration
# ===========================================================================
def run(quick: bool) -> dict:
    basket = BASKET_QUICK if quick else BASKET_FULL
    data = load_data(basket)
    records = build_book(data)
    per_tk: dict[str, dict] = {}
    for tk in data:
        trec = [r for r in records if r["instrument"] == tk]
        wins = sum(1 for r in trec if r["status"] == "WON")
        sig = sum(1 for r in trec if r.get("qualifies"))
        per_tk[tk] = {"n": len(trec), "sig": sig, "wins": wins}
    v = assemble_verdict(records)
    return {"records": records, "per_tk": per_tk, "verdict_block": v}


def json_summary(res: dict) -> dict:
    v = res["verdict_block"]
    return {
        "hypothesis": "H-033", "asset_class": "EQUITY",
        "family": "residualized_overnight_return_xs_reversal",
        "verdict": v["verdict"], "n": v["n"],
        "n_signal_days": v["n_signal_days"],
        "windows_scored": v["windows_scored"],
        "windows_strong": v["windows_strong"],
        "per_window_eff": v["per_window_eff"],
        "sign": v["sign"], "same_sign_ok": v["same_sign_ok"],
        "pooled_wr": v["pooled_wr"],
        "gross_mean_ret": v["gross_mean_ret"],
        "net_mean_ret": v["net_mean_ret"],
        "cost_survival": v["cost_survival"],
        "cost_survival_pass": v["cost_survival_pass"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true",
                    help="smaller basket for a fast smoke run")
    ap.add_argument("--json", dest="as_json", action="store_true")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "reports" / "h033_overnight_xs_reversal_2026-05-19.md")
    args = ap.parse_args()

    res = run(args.quick)
    summary = json_summary(res)

    if args.as_json:
        print(json.dumps(summary, indent=2, default=str))
        return 0

    report = render_report(res)
    args.out.write_text(report, encoding="utf-8")
    print(f"# wrote {args.out}", file=sys.stderr)
    print(report)
    print("\nJSON SUMMARY:")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
