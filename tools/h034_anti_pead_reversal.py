#!/usr/bin/env python3
"""H-034 EQUITY anti-PEAD 1-day post-earnings over-reaction reversal — research.

OPT-IN RESEARCH SIDECAR. No production wiring. No caller in quality_gates.py,
dashboard_generator.py, or any pick-generation / scoring path. It fetches free
yfinance data, runs the pre-registered signal through the edge-stability
harness (imported UNMODIFIED), and writes a report — nothing else.

------------------------------------------------------------------------------
PRE-REGISTERED HYPOTHESIS (registry key tier2_2026_05_19, id H-034)
------------------------------------------------------------------------------
OPPOSITE SIGN to killed H-010 (PEAD drift). For each earnings announcement on
day d for a fixed basket of liquid large/mid-cap US equities:
  * earnings-reaction GAP = close_d / close_{d-1} - 1  (the day-of reaction).
  * on day d+1 FADE the over-reaction:
        SHORT names whose GAP was a strong POSITIVE spike (gap-up overshoot)
        LONG  names whose GAP was a strong NEGATIVE spike (gap-down overshoot)
  * ENTER at the open of d+1, EXIT at the close of d+2 (1-day hold).
  * 'strong' = |GAP| in the top tercile of that name's OWN past earnings gaps
    (strictly-past, the current event excluded) — a name-relative filter.

Every earnings event is one resolved record. signal_z (the score the harness
reads) = |GAP z-score| against the name's strictly-past earnings-gap
distribution, gated to 0 on non-strong (non-qualifying) events. The harness eff
then answers exactly the H-034 question: do the strong-gap (over-reaction)
events separate winners from losers stably?

WHY THIS IS NOT H-010: H-010 uses the EPS SURPRISE (SUE), goes WITH the surprise
sign, holds 20-60 days (DRIFT). H-034 uses the day-of PRICE GAP, trades AGAINST
the gap sign, holds 1 day (REVERSAL). Opposite direction, different input, 30x
shorter horizon. A kill of the drift does not pre-decide the 1-day reversal.

STRICT NO-LOOK-AHEAD: GAP uses close_{d-1} and close_d both known at the close
of d; the strong-gap tercile uses only the name's earnings strictly before this
event; entry is the open of d+1, exit the close of d+2 — no future bar read.

------------------------------------------------------------------------------
THE VERDICT GATE
------------------------------------------------------------------------------
Records fed through tools/edge_stability_harness.evaluate() UNMODIFIED.
ADMISSIBLE iff |eff| >= 0.30, same sign, >= 3 of 5 walk-forward 14-day windows.
A 30bps round-trip post-cost gate is applied. A gaudy in-sample WR is NOT a
pass. Earnings events are quarterly per name: < 5 scored harness windows ->
UNTESTED (data-gap), not REJECTED.

    python tools/h034_anti_pead_reversal.py [--quick] [--json]
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
PRICE_CACHE = CACHE / "h034_price_cache.json"
EARN_CACHE = CACHE / "h034_earnings_cache.json"

# ---- Pre-registered tunables (signal family fixed — no per-window search) ----
STRONG_TERCILE = 2.0 / 3.0   # |GAP| must exceed the name's past 2/3 quantile
MIN_PRIOR_EVENTS = 4         # need >=4 past earnings gaps to define the tercile
WINDOW_DAYS = 14
HARNESS_FIELD = "signal_z"
POST_COST_BPS = 30
COST_SURVIVAL_MIN = 0.60

# Fixed pre-registered basket of liquid large/mid-cap US equities — deep
# yfinance history + quarterly earnings. Fixed in advance, no post-hoc pick.
BASKET_FULL = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "JPM",
               "BAC", "WMT", "XOM", "CVX", "JNJ", "PG", "KO", "PEP", "DIS",
               "NFLX", "INTC", "AMD", "CSCO", "ORCL", "CRM", "ADBE", "QCOM",
               "TXN", "HD", "MCD", "NKE", "COST", "UNH", "PFE", "MRK", "ABBV",
               "T", "VZ", "C", "GS", "MS", "CAT", "BA", "GE", "F", "GM",
               "UBER", "PYPL", "SBUX", "MU", "AMAT", "LRCX"]
BASKET_QUICK = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "JPM",
                "INTC", "AMD", "NFLX", "DIS"]


# ===========================================================================
# Data fetch — yfinance daily OHLCV + earnings dates
# ===========================================================================
def fetch_yf_ohlcv(ticker: str, period: str = "10y") -> list[dict]:
    """yfinance daily OHLCV bars, ascending by date. [] on failure.

    auto_adjust=False — gaps must be the genuine session gap, not split-adjusted.
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
        if df is not None and len(df) >= 200:
            break
        time.sleep(2)
    if df is None or len(df) < 200:
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


def fetch_earnings_dates(ticker: str) -> list[str]:
    """yfinance earnings announcement DATES, ascending. [] on failure.

    H-034 uses ONLY the announcement date — not the EPS surprise. The signal is
    the day-of price gap, so all that is needed is when the announcement landed.
    """
    import warnings
    warnings.filterwarnings("ignore")
    try:
        import yfinance as yf
    except ImportError:
        return []
    try:
        tk = yf.Ticker(ticker)
        df = tk.get_earnings_dates(limit=80)   # ~20 yrs of quarterly history
    except Exception:  # noqa: BLE001
        return []
    if df is None or len(df) == 0:
        return []
    dates = set()
    for idx, _ in df.iterrows():
        try:
            d = idx.date().isoformat() if hasattr(idx, "date") else str(idx)[:10]
            dates.add(d)
        except Exception:  # noqa: BLE001
            continue
    return sorted(dates)


def load_data(tickers: list[str], use_cache: bool = True):
    pcache: dict = {}
    ecache: dict = {}
    if use_cache and PRICE_CACHE.exists():
        try:
            pcache = json.loads(PRICE_CACHE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pcache = {}
    if use_cache and EARN_CACHE.exists():
        try:
            ecache = json.loads(EARN_CACHE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            ecache = {}
    prices: dict[str, list[dict]] = {}
    earnings: dict[str, list[str]] = {}
    for tk in tickers:
        cp = pcache.get(tk)
        if cp and len(cp) >= 200:
            prices[tk] = cp
            print(f"#   {tk}: {len(cp)} bars (cache)", file=sys.stderr)
        else:
            print(f"# fetching prices {tk} ...", file=sys.stderr)
            bars = fetch_yf_ohlcv(tk)
            if bars:
                prices[tk] = bars
                pcache[tk] = bars
                print(f"#   {tk}: {len(bars)} bars", file=sys.stderr)
            else:
                print(f"#   {tk}: SKIP prices", file=sys.stderr)
            time.sleep(0.4)
        ce = ecache.get(tk)
        if ce and len(ce) >= MIN_PRIOR_EVENTS + 2:
            earnings[tk] = ce
            print(f"#   {tk}: {len(ce)} earnings dates (cache)", file=sys.stderr)
        else:
            print(f"# fetching earnings {tk} ...", file=sys.stderr)
            ed = fetch_earnings_dates(tk)
            if ed:
                earnings[tk] = ed
                ecache[tk] = ed
                print(f"#   {tk}: {len(ed)} earnings dates", file=sys.stderr)
            else:
                print(f"#   {tk}: SKIP earnings", file=sys.stderr)
            time.sleep(0.4)
    try:
        PRICE_CACHE.write_text(json.dumps(pcache), encoding="utf-8")
        EARN_CACHE.write_text(json.dumps(ecache), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    return prices, earnings


# ===========================================================================
# Signal math (pure, network-free)
# ===========================================================================
def _quantile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, max(0, int(q * len(sorted_vals))))
    return sorted_vals[idx]


def backtest_ticker(tk: str, bars: list[dict], earn_dates: list[str]) -> list[dict]:
    """Build the H-034 resolved-record series for one ticker.

    For each earnings date d that maps to a bar with a d-1 prior bar and d+1,
    d+2 future bars:
      * GAP = close_d / close_{d-1} - 1  (the day-of earnings reaction).
      * the event QUALIFIES (is a 'strong over-reaction') iff |GAP| exceeds the
        top-tercile quantile of the name's OWN past earnings gaps (>= 4 priors,
        the current event excluded — strictly-past).
      * direction FADES the gap: SHORT (-1) if GAP > 0, LONG (+1) if GAP < 0.
      * ENTER at the open of d+1, EXIT at the close of d+2.
      * signal_z = |GAP z-score| against the name's strictly-past earnings-gap
        distribution on qualifying events, 0 otherwise.

    Every earnings event is one record (continuous-position book). The harness
    eff measures whether the strong-gap (qualifying) events separate winners.

    STRICT NO-LOOK-AHEAD: GAP uses close_{d-1}, close_d (known at close of d);
    the tercile/z use only earnings strictly before this event; entry open d+1,
    exit close d+2.
    """
    by_date = {b["date"]: i for i, b in enumerate(bars)}
    records: list[dict] = []
    prior_gaps: list[float] = []   # the name's earnings gaps seen so far (asc)

    for ed in earn_dates:
        # map the announcement date to a trading-day index. yfinance earnings
        # dates can land on a non-trading day or after-hours — snap to the
        # first bar on/after the announcement date as day d.
        i = by_date.get(ed)
        if i is None:
            i = next((k for k, b in enumerate(bars) if b["date"] >= ed), None)
        if i is None or i < 1 or i + 2 >= len(bars):
            continue
        close_dm1 = bars[i - 1]["close"]
        close_d = bars[i]["close"]
        if close_dm1 <= 0:
            continue
        gap = close_d / close_dm1 - 1.0
        # ----- strong-gap qualification from STRICTLY-PAST own earnings gaps ---
        qualifies = False
        signal_z = 0.0
        if len(prior_gaps) >= MIN_PRIOR_EVENTS:
            absp = sorted(abs(g) for g in prior_gaps)
            thr = _quantile(absp, STRONG_TERCILE)
            mean_abs = statistics.fmean(absp)
            sd_abs = statistics.pstdev(absp) or 1e-9
            if abs(gap) > thr and thr > 0:
                qualifies = True
                signal_z = abs((abs(gap) - mean_abs) / sd_abs)
        # ----- FADE the gap: SHORT a gap-up, LONG a gap-down -----
        direction = -1 if gap > 0 else 1
        entry = bars[i + 1]["open"]
        exit_px = bars[i + 2]["close"]
        if entry > 0:
            gross_ret = (exit_px / entry - 1.0) * direction
            status = "WON" if gross_ret > 0 else "LOST"
            records.append({
                "status": status,
                "resolved_at": bars[i + 2]["date"],
                "entry_date": bars[i + 1]["date"],
                "timestamp": bars[i]["date"],
                HARNESS_FIELD: signal_z,
                "gross_ret": round(gross_ret, 6),
                "gap": round(gap, 6),
                "direction": direction,
                "qualifies": qualifies,
                "instrument": tk,
            })
        # the current event joins the name's history AFTER it is recorded
        prior_gaps.append(gap)
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
    per_tk = res["per_tk"]
    effs = " ".join(f"{e:+.2f}" if e is not None else "n/a"
                    for e in v["per_window_eff"])
    next_step = {
        "ADMISSIBLE": "Re-test on a fresh out-of-sample period, add full "
                      "commission + bid-ask + earnings-day slippage modelling, run "
                      "a deflated-Sharpe / SPA multiple-testing correction, then "
                      "operator review. Harness pass is necessary, not sufficient. "
                      "No wiring.",
        "REJECTED": "Clean kill. The anti-PEAD 1-day post-earnings reversal does "
                    "not separate winners from losers with a stable sign across "
                    "enough 14-day windows (or fails the 30bps cost gate). The "
                    "negation of H-010 also fails. Do not wire or size. Archive "
                    "as a tested failure.",
        "UNTESTED": "Honest non-verdict — the harness did not get >= 3 scored "
                    "14-day windows. Earnings events are quarterly per name, so "
                    "even a 50-name basket gives sparse 14-day windows; the "
                    "blocker is event density, not design.",
    }[v["verdict"]]
    out = [
        "# H-034 EQUITY anti-PEAD 1-day post-earnings over-reaction reversal — 2026-05-19",
        "",
        f"_Generated {ts} by `tools/h034_anti_pead_reversal.py`._",
        "",
        "**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** Fetches free "
        "yfinance data, runs the pre-registered signal through "
        "`edge_stability_harness` (imported UNMODIFIED), writes this report.",
        "",
        "## Pre-registered hypothesis (registry `tier2_2026_05_19` / H-034)",
        "",
        "OPPOSITE-SIGN to killed H-010 (PEAD drift). For each earnings "
        "announcement on day d, measure the day-of price gap "
        "`GAP = close_d/close_{d-1}-1`. On day d+1 FADE the over-reaction: "
        "SHORT a strong gap-up, LONG a strong gap-down; enter at the open of "
        "d+1, exit at the close of d+2. 'Strong' = |GAP| above the name's own "
        "past-earnings top-tercile.",
        "",
        "**Why this is NOT H-010:** H-010 uses the EPS SURPRISE (SUE), trades "
        "WITH the surprise sign, holds 20-60 days (a DRIFT). H-034 uses the "
        "day-of PRICE GAP, trades AGAINST the gap sign, holds 1 day (a "
        "REVERSAL). Opposite direction, different input, ~30x shorter horizon.",
        "",
        "**No-look-ahead:** GAP uses `close_{d-1}` and `close_d` (known at the "
        "close of d); the strong-gap tercile uses only earnings strictly before "
        "this event; entry open d+1, exit close d+2.",
        "",
        "## Data",
        "",
        "- yfinance daily OHLCV + `get_earnings_dates`, free, no key. Cached to "
        "`tools/cache/h034_price_cache.json` + `h034_earnings_cache.json`.",
        f"- Fixed basket tickers with usable price + earnings history: "
        f"{len(per_tk)}.",
        f"- Earnings-event resolved records (continuous book): **{len(recs)}**.",
        f"- Of which qualifying strong-gap (over-reaction) events: "
        f"**{v['n_signal_days']}**.",
        "",
    ]
    if per_tk:
        out += ["| ticker | events | strong-gap | wins | WR |",
                "|---|---|---|---|---|"]
        for k, pv in per_tk.items():
            wr = f"{pv['wr']*100:.1f}%" if pv.get("wr") is not None else "n/a"
            out.append(f"| {k} | {pv['n']} | {pv['sig']} | {pv['wins']} | {wr} |")
        out.append("")
    out += [
        "## Harness verdict (THE gate — harness imported UNMODIFIED)",
        "",
        f"- per-window eff (new->old): `{effs}`",
        f"- windows scored: {v['windows_scored']}  (strong: {v['windows_strong']})",
        f"- sign: `{v['sign']}`  same-sign ok: {v['same_sign_ok']}",
        f"- harness `is_admissible()`: {v['harness_admissible']}",
        f"- harness reason: {v['harness_reason']}",
        "",
        "## Edge & cost survival (over the qualifying strong-gap events)",
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
    prices, earnings = load_data(basket)
    records: list[dict] = []
    per_tk: dict[str, dict] = {}
    for tk in basket:
        bars = prices.get(tk)
        ed = earnings.get(tk)
        if not bars or not ed:
            continue
        trec = backtest_ticker(tk, bars, ed)
        records.extend(trec)
        wins = sum(1 for r in trec if r["status"] == "WON")
        sig = sum(1 for r in trec if r.get("qualifies"))
        per_tk[tk] = {"n": len(trec), "sig": sig, "wins": wins,
                      "wr": round(wins / len(trec), 4) if trec else None}
    v = assemble_verdict(records)
    return {"records": records, "per_tk": per_tk, "verdict_block": v}


def json_summary(res: dict) -> dict:
    v = res["verdict_block"]
    return {
        "hypothesis": "H-034", "asset_class": "EQUITY",
        "family": "anti_pead_oneday_postearnings_reversal",
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
                    default=ROOT / "reports" / "h034_anti_pead_reversal_2026-05-19.md")
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
