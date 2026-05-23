#!/usr/bin/env python3
"""H-031 COMMODITY agricultural harvest-seasonality — calendar-window research.

OPT-IN RESEARCH SIDECAR. No production wiring. No caller in quality_gates.py,
dashboard_generator.py, or any pick-generation / scoring path. It fetches free
yfinance data, runs the pre-registered signal through the edge-stability
harness, and writes a report — nothing else.

------------------------------------------------------------------------------
PRE-REGISTERED HYPOTHESIS (registry key local_harvest_2026_05_19, id H-031)
------------------------------------------------------------------------------
Calendar-anchored corn (ZC=F) and wheat (ZW=F) harvest-cycle directional
windows. Grain futures carry a documented harvest seasonality: supply peaks
at harvest depress prices; scarcity into the next planting supports them.

THE LOOK-AHEAD-FREE DESIGN — the critical part:

  1. The full ZC=F / ZW=F daily history is split at a fixed cut date into:
       * TRAINING years  (everything strictly before the cut), and
       * TEST years       (the cut date onward — the out-of-sample period).
  2. From the TRAINING YEARS ONLY, each calendar MONTH is scored by its mean
     daily return across all training years. The directional sign for that
     month (+1 long / -1 short) and the very fact that the month is traded
     are derived purely from pre-sample data. No test-year bar touches the
     calendar / sign decision.
  3. Those fixed monthly calendar windows + signs are then applied UNCHANGED
     to the TEST years. Every test-year trading day inside a traded month is
     one resolved record: gross return = next-day close-to-close move times
     the pre-registered sign for that month.

This is genuinely look-ahead-free: the calendar and the directional bet are
frozen from the training period before any test-year data is seen.

A continuous record per test-year trading-day is used so the harness gets the
density it needs. signal_z = standardised distance into the traded month
(conviction proxy — early/late-month positioning).

------------------------------------------------------------------------------
THE VERDICT GATE
------------------------------------------------------------------------------
Records are fed through tools/edge_stability_harness.evaluate() UNMODIFIED.
ADMISSIBLE iff |eff| >= 0.30, same sign, >= 3 of 5 walk-forward 14-day windows.
A 30bps post-cost gate is applied. COMMODITY seasonal windows are sparse — if
the harness scores < MIN_STABLE_WINDOWS windows the verdict is UNTESTED
(data-gap), NOT a clean reject.

    python tools/h031_harvest_seasonality.py [--json]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import date, datetime, timezone
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
CACHE_FILE = CACHE / "h031_harvest_cache.json"

# ---------------------------------------------------------------------------
# Pre-registered tunables.
# ---------------------------------------------------------------------------
# In-sample / out-of-sample split. Calendar windows + signs are learned from
# bars STRICTLY BEFORE this cut date; the harness verdict is computed on bars
# from this date onward. The cut is fixed in advance.
TRAIN_TEST_CUT = "2019-01-01"
TICKERS = ["ZC=F", "ZW=F"]    # corn, wheat front-month continuous futures
WINDOW_DAYS = 14
HARNESS_FIELD = "signal_z"
POST_COST_BPS = 30
COST_SURVIVAL_MIN = 0.60
# A month is traded if its training-year mean daily return is at least this
# many bps/day in magnitude — a minimum economic-signal floor so we do not
# trade calendar noise.
MONTH_SIGNAL_FLOOR_BPS = 2.0


# ===========================================================================
# Data fetch — yfinance daily OHLCV
# ===========================================================================
def fetch_yf_ohlcv(ticker: str) -> list[dict]:
    """yfinance daily OHLCV bars, ascending by date. [] on failure."""
    import warnings
    warnings.filterwarnings("ignore")
    try:
        import yfinance as yf
    except ImportError:
        return []
    df = None
    for _ in range(3):
        try:
            df = yf.download(ticker, period="max", interval="1d",
                             progress=False, auto_adjust=True)
        except Exception:  # noqa: BLE001
            df = None
        if df is not None and len(df) >= 250:
            break
        time.sleep(2)
    if df is None or len(df) < 250:
        return []
    out = []
    cols = {c[0] if isinstance(c, tuple) else c: c for c in df.columns}
    for idx, row in df.iterrows():
        try:
            d = idx.date().isoformat() if hasattr(idx, "date") else str(idx)[:10]
            c = float(row[cols["Close"]])
        except (KeyError, TypeError, ValueError):
            continue
        if c > 0:
            out.append({"date": d, "close": c})
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
        if cached and len(cached) >= 250:
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
            print(f"#   {tk}: SKIP (fetch failed)", file=sys.stderr)
        time.sleep(0.4)
    try:
        CACHE_FILE.write_text(json.dumps(cache), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    return out


# ===========================================================================
# Signal math (pure, network-free)
# ===========================================================================
def daily_returns(bars: list[dict]) -> list[dict]:
    """Attach next-day close-to-close return to each bar. The return on bar i
    is realised over [i, i+1) — it is the outcome of a position opened at the
    close of i. The last bar carries no return."""
    out = []
    for i in range(len(bars) - 1):
        b = bars[i]
        ret = bars[i + 1]["close"] / b["close"] - 1.0
        out.append({"date": b["date"], "ret": ret})
    return out


def learn_calendar_from_training(rets: list[dict], cut: str) -> dict[int, dict]:
    """Learn the per-month directional calendar from TRAINING YEARS ONLY.

    rets entries dated strictly before `cut` are the training sample. For each
    calendar month 1..12 compute the mean daily next-day return across all
    training years. The traded sign for the month = sign of that mean; the
    month is traded only if |mean| >= MONTH_SIGNAL_FLOOR_BPS bps/day.

    Returns {month: {"sign": +1/-1, "train_mean_bps": x, "train_n": n}} for the
    traded months only. NO test-year data is read here — strictly pre-sample.
    """
    by_month: dict[int, list[float]] = {m: [] for m in range(1, 13)}
    for r in rets:
        if r["date"] >= cut:
            continue   # test-year bar — never feeds the calendar
        m = int(r["date"][5:7])
        by_month[m].append(r["ret"])
    calendar: dict[int, dict] = {}
    floor = MONTH_SIGNAL_FLOOR_BPS / 10000.0
    for m, vals in by_month.items():
        if len(vals) < 20:
            continue
        mean = statistics.fmean(vals)
        if abs(mean) < floor:
            continue   # below the economic-signal floor — not traded
        calendar[m] = {
            "sign": 1 if mean > 0 else -1,
            "train_mean_bps": round(mean * 10000.0, 3),
            "train_n": len(vals),
        }
    return calendar


def build_test_records(rets: list[dict], cut: str, calendar: dict[int, dict],
                        ticker: str) -> list[dict]:
    """Apply the FROZEN training calendar to the out-of-sample TEST years.

    Every test-year (date >= cut) trading day whose month is a traded month in
    `calendar` becomes one resolved record:
      * direction = the pre-registered sign for that month (frozen from training)
      * gross_ret = next-day close-to-close return * direction
      * signal_z  = standardised day-of-month position (conviction proxy)
    No test-year data influenced the calendar or the sign — look-ahead-free.
    """
    records: list[dict] = []
    for r in rets:
        if r["date"] < cut:
            continue
        m = int(r["date"][5:7])
        spec = calendar.get(m)
        if spec is None:
            continue
        direction = spec["sign"]
        gross_ret = r["ret"] * direction
        dom = int(r["date"][8:10])
        # signal_z: standardised position within the month (1..~31 -> z)
        signal_z = abs((dom - 16.0) / 9.0)
        status = "WON" if gross_ret > 0 else "LOST"
        records.append({
            "status": status,
            "resolved_at": r["date"],
            "timestamp": r["date"],
            HARNESS_FIELD: signal_z,
            "gross_ret": round(gross_ret, 6),
            "direction": direction,
            "month": m,
            "instrument": ticker,
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


def cost_survival(records: list[dict], bps: int = POST_COST_BPS) -> float:
    if not records:
        return 0.0
    thr = bps / 10000.0
    return round(sum(1 for r in records
                     if abs(r.get("gross_ret", 0.0)) > thr) / len(records), 4)


def pooled_wr(records: list[dict]) -> float | None:
    res = [r for r in records if r["status"] in ("WON", "LOST")]
    if not res:
        return None
    return round(sum(1 for r in res if r["status"] == "WON") / len(res), 4)


def net_edge_summary(records: list[dict], bps: int = POST_COST_BPS) -> dict:
    if not records:
        return {"gross_mean_ret": None, "net_mean_ret": None}
    grs = [r.get("gross_ret", 0.0) for r in records]
    gross = statistics.fmean(grs)
    return {"gross_mean_ret": round(gross, 6),
            "net_mean_ret": round(gross - bps / 10000.0, 6)}


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
    # COMMODITY seasonal windows are sparse — < MIN_STABLE_WINDOWS scored
    # windows is an honest UNTESTED data-gap, not a clean reject.
    if scored < harness.MIN_STABLE_WINDOWS:
        verdict = "UNTESTED"
    elif harness_pass and cost_pass:
        verdict = "ADMISSIBLE"
    else:
        verdict = "REJECTED"
    return {
        "verdict": verdict,
        "n": len(records),
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
_MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def render_report(res: dict) -> str:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    v = res["verdict_block"]
    recs = res["records"]
    cal = res["calendar"]
    effs = " ".join(f"{e:+.2f}" if e is not None else "n/a"
                    for e in v["per_window_eff"])
    next_step = {
        "ADMISSIBLE": "Re-test on a still-fresher out-of-sample window, add full "
                      "futures-roll + slippage cost modelling, run a deflated-"
                      "Sharpe / SPA correction, then operator review. Harness "
                      "pass is necessary, not sufficient. No wiring.",
        "REJECTED": "The frozen harvest calendar was applied out-of-sample and "
                    "the harness rendered a real verdict — the seasonal sign "
                    "does not separate winners stably across enough 14-day "
                    "windows (or fails the cost gate). Clean kill. No wiring.",
        "UNTESTED": "Honest data-gap non-verdict. COMMODITY harvest-seasonal "
                    "windows are sparse — the out-of-sample period did not give "
                    "the harness >= 3 scored 14-day windows. Not a pass and not "
                    "a clean fail; the blocker is sample coverage. A longer "
                    "out-of-sample period or more grain contracts would help.",
    }[v["verdict"]]
    out = [
        "# H-031 COMMODITY agricultural harvest-seasonality — 2026-05-19",
        "",
        f"_Generated {ts} by `tools/h031_harvest_seasonality.py`._",
        "",
        "**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** No caller in "
        "`quality_gates.py`, `dashboard_generator.py`, or any pick / scoring "
        "path. Fetches free yfinance data, runs the pre-registered signal "
        "through `edge_stability_harness` (imported unmodified), writes this "
        "report.",
        "",
        "## Pre-registered hypothesis (registry `local_harvest_2026_05_19` / H-031)",
        "",
        "Calendar-anchored corn (ZC=F) + wheat (ZW=F) harvest-cycle directional "
        "windows. The directional sign for each calendar month and the very "
        "decision to trade it are derived **only from training years strictly "
        "before the fixed cut date**, then applied **unchanged** to the "
        "out-of-sample test years — genuinely look-ahead-free.",
        "",
        f"- train/test cut: **{TRAIN_TEST_CUT}** (training = before; test = "
        f"on/after).",
        f"- a month is traded iff its training-year mean daily return is "
        f">= {MONTH_SIGNAL_FLOOR_BPS} bps/day in magnitude.",
        "",
        "## Frozen calendar learned from TRAINING years only",
        "",
    ]
    for tk, mc in cal.items():
        if mc:
            parts = ", ".join(
                f"{_MONTHS[m]} {'LONG' if s['sign']>0 else 'SHORT'} "
                f"({s['train_mean_bps']:+.1f}bps/d, n={s['train_n']})"
                for m, s in sorted(mc.items()))
            out.append(f"- **{tk}**: {parts}")
        else:
            out.append(f"- **{tk}**: no month cleared the "
                       f"{MONTH_SIGNAL_FLOOR_BPS}bps/day floor in training.")
    out += [
        "",
        "## Data",
        "",
        "- yfinance daily OHLCV for ZC=F / ZW=F, free, no key. Cached to "
        "`tools/cache/h031_harvest_cache.json`.",
        f"- Out-of-sample test-year resolved records: **{len(recs)}**.",
        "",
        "## Harness verdict (THE gate — harness imported UNMODIFIED)",
        "",
        f"- per-window eff (new->old): `{effs}`",
        f"- windows scored: {v['windows_scored']}  (strong: {v['windows_strong']})",
        f"- sign: `{v['sign']}`  same-sign ok: {v['same_sign_ok']}",
        f"- harness `is_admissible()`: {v['harness_admissible']}",
        f"- harness reason: {v['harness_reason']}",
        "",
        "## Edge & cost survival (out-of-sample test years)",
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
def run() -> dict:
    data = load_data(TICKERS)
    records: list[dict] = []
    calendar: dict[str, dict] = {}
    for tk, bars in data.items():
        rets = daily_returns(bars)
        cal = learn_calendar_from_training(rets, TRAIN_TEST_CUT)
        calendar[tk] = cal
        records.extend(build_test_records(rets, TRAIN_TEST_CUT, cal, tk))
    v = assemble_verdict(records)
    return {"records": records, "calendar": calendar, "verdict_block": v}


def json_summary(res: dict) -> dict:
    v = res["verdict_block"]
    return {
        "hypothesis": "H-031", "asset_class": "COMMODITY",
        "family": "agricultural_harvest_seasonality",
        "verdict": v["verdict"], "n": v["n"],
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
    ap.add_argument("--json", dest="as_json", action="store_true")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "reports" /
                            "h031_harvest_seasonality_2026-05-19.md")
    args = ap.parse_args()

    res = run()
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
