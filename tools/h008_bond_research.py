#!/usr/bin/env python3
"""H-008 redesign — BOND 2s10s slope-momentum CONTINUOUS-POSITION backtest.

OPT-IN RESEARCH SIDECAR. No production wiring. No caller in quality_gates.py,
dashboard_generator.py, or any pick-generation / scoring path. It reads market
data and writes a report — nothing else.

------------------------------------------------------------------------------
WHY THIS MODULE EXISTS
------------------------------------------------------------------------------
Fork 2 (tools/new_signal_research.py) registered H-008 as UNTESTED, not failed.
Reason: it modelled the 2s10s slope-momentum signal as SPARSE DISCRETE PICKS
(one synthetic pick per |z|>=1 threshold crossing). The 2s10s slope moves
slowly, so those crossings cluster: the harness's 14-day windows could not
collect >= 80 resolved events with >= 15 winners + >= 15 losers, and it scored
< 3 windows. That is a backtest-DESIGN limitation, not a data limitation —
FRED DGS2/DGS10 carries 40+ years of daily data.

THE REDESIGN (this module):
  * CONTINUOUS-POSITION book. Every trading day the strategy holds a directional
    position in EACH bond instrument, sized by the slope-momentum signal. There
    is no |z| threshold and no sparse event filter — every instrument-day is a
    resolved record. This makes the record stream DENSE and uniform in time, so
    the harness's fixed 14-day windows fill up.
  * CROSS-SECTIONAL BREADTH. ~10 Treasury duration instruments (futures +
    duration-laddered Treasury ETFs). With ~10 trading days per 14-day window
    and ~10 instruments, each window collects ~100 instrument-day records —
    comfortably past the harness MIN_WINDOW_N=80 / 15-W + 15-L floor.
  * STRICT NO-LOOK-AHEAD. The slope-momentum signal for a position dated D is
    computed from 2s10s slope observations STRICTLY BEFORE D. The realized
    return is the close-to-next-close return of the instrument over [D, D+1).

------------------------------------------------------------------------------
THE VERDICT GATE
------------------------------------------------------------------------------
Records are fed through tools/edge_stability_harness.evaluate() — the SAME
admissibility gate EDGE_VERDICT_2026-05-18.md names as the only gate that
counts. ADMISSIBLE iff |eff| >= 0.30, same sign, >= 3 of 5 walk-forward
14-day windows.

A gaudy in-sample Sharpe is NOT a pass. Only the harness verdict counts. After
four straight kills the base rate is poor; this module reports the harness
verdict honestly whichever way it lands.

    python tools/h008_bond_research.py [--quick] [--json]
                                       [--out reports/h008_bond_2s10s_redesign_2026-05-18.md]
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Windows UTF-8
if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        if hasattr(_s, "reconfigure"):
            try:
                _s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                pass

import edge_stability_harness as harness  # noqa: E402

# ---------------------------------------------------------------------------
# Tunables (pre-registered: the signal family is fixed, no per-window search).
# ---------------------------------------------------------------------------
SLOPE_MOM_LOOKBACK = 10   # slope-momentum = N-day change of the 2s10s slope
Z_ROLL = 60               # rolling z-score look-back (STRICTLY past observations)
WINDOW_DAYS = 14          # walk-forward window length (harness default)
HARNESS_FIELD = "signal_z"  # the conviction-magnitude score the harness reads


# ===========================================================================
# Data fetch
# ===========================================================================
def fetch_fred_series(series_id: str) -> dict[str, float]:
    """FRED daily observations keyed by ISO date. Uses FRED_API_KEY if present,
    falls back to the keyless fredgraph CSV endpoint. 40+ yr history requested.
    """
    import os
    key = os.environ.get("FRED_API_KEY", "").strip()
    if key:
        url = (f"https://api.stlouisfed.org/fred/series/observations"
               f"?series_id={series_id}&api_key={key}&file_type=json"
               f"&observation_start=1980-01-01")
        try:
            with urllib.request.urlopen(url, timeout=45) as r:  # noqa: S310
                data = json.loads(r.read().decode("utf-8", "replace"))
            out = {}
            for obs in data.get("observations", []):
                try:
                    out[obs["date"]] = float(obs["value"])
                except (KeyError, TypeError, ValueError):
                    continue  # FRED encodes missing as "."
            if out:
                return out
        except Exception:  # noqa: BLE001
            pass
    # keyless fallback
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    try:
        with urllib.request.urlopen(url, timeout=45) as r:  # noqa: S310
            text = r.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for line in text.splitlines()[1:]:
        parts = line.split(",")
        if len(parts) >= 2:
            try:
                out[parts[0]] = float(parts[1])
            except (ValueError, IndexError):
                continue
    return out


def fetch_yf_close(ticker: str, period: str = "max") -> dict[str, float]:
    """yfinance daily close keyed by ISO date. {} on failure."""
    import warnings
    warnings.filterwarnings("ignore")
    try:
        import yfinance as yf
    except ImportError:
        return {}
    df = None
    for _ in range(3):
        try:
            df = yf.download(ticker, period=period, interval="1d",
                             progress=False, auto_adjust=True)
        except Exception:  # noqa: BLE001
            df = None
        if df is not None and len(df) >= 60:
            break
        time.sleep(3)
    if df is None or len(df) < 60:
        return {}
    close = df["Close"]
    if hasattr(close, "columns"):
        close = close.iloc[:, 0]
    out = {}
    for idx, val in close.items():
        try:
            v = float(val)
        except (TypeError, ValueError):
            continue
        d = idx.date() if hasattr(idx, "date") else None
        if d is not None and v > 0:
            out[d.isoformat()] = v
    return out


# ===========================================================================
# Signal math (pure, network-free — unit-tested)
# ===========================================================================
def compute_slope(dgs2: dict[str, float], dgs10: dict[str, float]):
    """2s10s slope = DGS10 - DGS2 on the common dated grid.

    Returns (dates_sorted, slope_list) aligned by index. Pure function.
    """
    dates = sorted(set(dgs2) & set(dgs10))
    slope = [dgs10[d] - dgs2[d] for d in dates]
    return dates, slope


def slope_momentum(slope: list[float], lookback: int) -> list[float]:
    """N-day change of the slope. Index i = slope[i] - slope[i-lookback].

    Entry i<lookback carries 0.0 (insufficient history). Pure function — uses
    only past slope values relative to index i, so no look-ahead.
    """
    return [slope[i] - slope[i - lookback] if i >= lookback else 0.0
            for i in range(len(slope))]


def rolling_z(series: list[float], idx: int, roll: int):
    """Z-score of series[idx] vs the `roll` STRICTLY-PAST observations.

    Returns None when fewer than `roll` past observations exist or the past
    window has zero dispersion. Pure function — series[idx] itself is excluded
    from the mean/sd, only series[idx-roll:idx] feeds them, so no look-ahead.
    """
    if idx < roll:
        return None
    window = series[idx - roll:idx]
    mu = statistics.fmean(window)
    sd = statistics.pstdev(window)
    if sd <= 0:
        return None
    return (series[idx] - mu) / sd


# ===========================================================================
# Continuous-position backtest
# ===========================================================================
# Treasury duration ladder. Futures first (the genuine bond instruments), then
# duration-laddered Treasury ETFs which give far longer + cleaner yfinance
# history and the cross-sectional breadth the harness windows need.
BOND_INSTRUMENTS_FULL = [
    ("ZT=F", "2y T-note future"),
    ("ZF=F", "5y T-note future"),
    ("ZN=F", "10y T-note future"),
    ("ZB=F", "30y T-bond future"),
    ("SHY", "1-3y Treasury ETF"),
    ("IEI", "3-7y Treasury ETF"),
    ("IEF", "7-10y Treasury ETF"),
    ("TLH", "10-20y Treasury ETF"),
    ("TLT", "20+y Treasury ETF"),
    ("GOVT", "broad Treasury ETF"),
]
BOND_INSTRUMENTS_QUICK = [
    ("IEF", "7-10y Treasury ETF"),
    ("TLT", "20+y Treasury ETF"),
    ("SHY", "1-3y Treasury ETF"),
    ("ZN=F", "10y T-note future"),
]


def build_signal_z_by_date(dgs2: dict[str, float],
                           dgs10: dict[str, float]) -> dict[str, float]:
    """Map ISO date -> slope-momentum z-score, computed STRICTLY from the past.

    For yield date d (index i), z = rolling_z(slope_momentum, i, Z_ROLL). The
    z at index i uses slope-momentum values at indices [i-Z_ROLL, i] only, and
    each slope-momentum value at index j uses slope[j] and slope[j-LOOKBACK] —
    all <= j <= i. Nothing at index > i is touched. No look-ahead.
    """
    dates, slope = compute_slope(dgs2, dgs10)
    mom = slope_momentum(slope, SLOPE_MOM_LOOKBACK)
    z_by_date: dict[str, float] = {}
    for i, d in enumerate(dates):
        z = rolling_z(mom, i, Z_ROLL)
        if z is not None:
            z_by_date[d] = z
    return z_by_date


def latest_signal_on_or_before(z_by_date: dict[str, float],
                               sorted_z_dates: list[str],
                               position_date: str):
    """Most recent slope-momentum z STRICTLY BEFORE position_date.

    Treasury yields publish with a one-day settle lag and the strategy can only
    act on yesterday's curve. We therefore require the signal date to be
    STRICTLY LESS than the position date — the position taken on day D is
    driven by the curve as of the last day < D. No look-ahead.
    """
    import bisect
    idx = bisect.bisect_left(sorted_z_dates, position_date) - 1
    if idx < 0:
        return None
    return z_by_date[sorted_z_dates[idx]]


def backtest_continuous(dgs2: dict[str, float], dgs10: dict[str, float],
                        price_by_inst: dict[str, dict[str, float]]) -> dict:
    """Continuous-position 2s10s slope-momentum backtest.

    For every (instrument, trading day D) with a next bar D+1:
      * signal_z = slope-momentum z as of the last curve date < D (no look-ahead)
      * direction: steepening momentum (z>0) historically coincides with rising
        yields / FALLING bond prices -> SHORT the bond (-1); flattening (z<0)
        -> LONG (+1). z==0 -> flat, skipped.
      * raw_ret = close(D+1)/close(D) - 1
      * signed_ret = raw_ret * direction
      * record: status WON iff signed_ret>0; score field signal_z = |z|
        (conviction magnitude — a real edge makes high-conviction days win).

    Returns the synthetic resolved-record list + a daily-aggregate equity curve
    for an honest (non-verdict) in-sample Sharpe sanity figure.
    """
    z_by_date = build_signal_z_by_date(dgs2, dgs10)
    sorted_z_dates = sorted(z_by_date)
    if not sorted_z_dates:
        return {"records": [], "equity": [], "per_inst": {},
                "error": "no slope-momentum z computed"}

    records: list[dict] = []
    per_inst: dict[str, dict] = {}
    # daily signed return aggregated equal-weight across the book
    daily_book: dict[str, list[float]] = {}

    for inst, prices in price_by_inst.items():
        pdates = sorted(prices)
        n = wins = 0
        for j in range(len(pdates) - 1):
            d = pdates[j]
            d_next = pdates[j + 1]
            z = latest_signal_on_or_before(z_by_date, sorted_z_dates, d)
            if z is None:
                continue
            direction = -1 if z > 0 else (1 if z < 0 else 0)
            if direction == 0:
                continue
            p0, p1 = prices[d], prices[d_next]
            if p0 <= 0:
                continue
            raw_ret = p1 / p0 - 1.0
            signed_ret = raw_ret * direction
            status = "WON" if signed_ret > 0 else "LOST"
            n += 1
            wins += int(status == "WON")
            # the harness buckets by resolved_at; resolution is realised at D+1
            records.append({
                "status": status,
                "resolved_at": d_next,
                "entry_date": d,
                "timestamp": d,
                HARNESS_FIELD: abs(z),
                "signed_ret": round(signed_ret, 6),
                "direction": direction,
                "instrument": inst,
            })
            daily_book.setdefault(d_next, []).append(signed_ret)
        per_inst[inst] = {"n": n, "wins": wins,
                          "wr": round(wins / n, 4) if n else None}

    # equal-weight daily book return -> in-sample Sharpe (sanity only, NOT the verdict)
    eq_dates = sorted(daily_book)
    daily_rets = [statistics.fmean(daily_book[d]) for d in eq_dates]
    return {
        "records": records,
        "per_inst": per_inst,
        "equity_dates": eq_dates,
        "daily_rets": daily_rets,
    }


def in_sample_sharpe(daily_rets: list[float]) -> float | None:
    """Annualised Sharpe of the equal-weight daily book. SANITY FIGURE ONLY —
    explicitly not the admissibility verdict (a gaudy Sharpe is not a pass).
    """
    if len(daily_rets) < 30:
        return None
    mu = statistics.fmean(daily_rets)
    sd = statistics.pstdev(daily_rets)
    if sd <= 0:
        return None
    return round((mu / sd) * math.sqrt(252), 3)


# ===========================================================================
# Harness wiring
# ===========================================================================
def harness_verdict(records: list[dict], window_days: int = WINDOW_DAYS) -> dict:
    """Run synthetic records through edge_stability_harness.evaluate() by
    patching its loader for this call only. The harness logic itself is reused
    verbatim — same windowing, same eff, same is_admissible() threshold.
    """
    orig_load = harness._load
    try:
        harness._load = lambda: records  # type: ignore[assignment]
        verdict = harness.evaluate(HARNESS_FIELD, window_days)
        admissible = harness.is_admissible(HARNESS_FIELD, window_days)
    finally:
        harness._load = orig_load  # type: ignore[assignment]
    verdict["admissible_via_is_admissible"] = admissible
    return verdict


# ===========================================================================
# Report
# ===========================================================================
def render_report(res: dict) -> str:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    recs = res.get("records", [])
    h = res.get("harness", {})
    adm = h.get("admissible", False)
    flag = "ADMISSIBLE" if adm else "REJECTED"
    sharpe = res.get("in_sample_sharpe")

    out = [
        "# H-008 BOND 2s10s — Continuous-Position Redesign — 2026-05-18",
        "",
        f"_Generated {ts} by `tools/h008_bond_research.py`._",
        "",
        "**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** No caller in "
        "`quality_gates.py`, `dashboard_generator.py`, or any pick-generation / "
        "scoring path. Reads market data, writes this report — nothing else.",
        "",
        "## Why a redesign",
        "",
        "Fork 2 (`tools/new_signal_research.py`) left H-008 **UNTESTED**, not "
        "failed: it modelled the 2s10s slope-momentum signal as sparse discrete "
        "picks (one per `|z|>=1` crossing). The 2s10s slope moves slowly, so "
        "those crossings cluster — the harness's 14-day windows could not gather "
        "the >= 80 resolved events (>= 15 winners + >= 15 losers) they need and "
        "it scored < 3 windows. That is a backtest-*design* limit, not a data "
        "limit: FRED DGS2/DGS10 carries 40+ years of daily data.",
        "",
        "## The redesign",
        "",
        "- **Continuous-position book.** Every trading day the strategy holds a "
        "directional position in *each* bond instrument, driven by the slope-"
        "momentum signal. No `|z|` threshold, no sparse event filter — every "
        "instrument-day is a resolved record, so the record stream is dense and "
        "uniform in time and the harness's fixed 14-day windows fill.",
        "- **Cross-sectional breadth.** A Treasury duration ladder (futures + "
        "duration-laddered Treasury ETFs) so each 14-day window (~10 trading "
        "days) collects ~10 instruments x ~10 days of records — past the "
        "`MIN_WINDOW_N=80` / 15-W + 15-L floor.",
        "- **Strict no-look-ahead.** The slope-momentum z for a position dated D "
        "is computed from 2s10s slope observations *strictly before* D (yields "
        "settle with a one-day lag). The realised return is close(D)->close(D+1).",
        "",
        "## Signal",
        "",
        "- 2s10s slope = `DGS10 - DGS2` (FRED, daily).",
        f"- slope-momentum = {SLOPE_MOM_LOOKBACK}-day change of the slope.",
        f"- `signal_z` = rolling {Z_ROLL}-observation z-score of slope-momentum, "
        "strictly-past window.",
        "- direction: steepening momentum (z>0) -> SHORT bonds (rising yields / "
        "falling prices); flattening (z<0) -> LONG bonds.",
        "- harness score field = `|signal_z|` (conviction magnitude — a real "
        "edge makes high-conviction days separate winners from losers).",
        "",
        f"## Data",
        "",
        f"- **Yields:** FRED DGS2 / DGS10 (daily, 40+ yr requested from 1980).",
        f"- **Prices:** yfinance daily close — Treasury futures + duration ETFs.",
        f"- **Sample:** {len(recs)} instrument-day resolved records.",
        "",
    ]
    pi = res.get("per_inst", {})
    if pi:
        out += ["| instrument | records | wins | WR |", "|---|---|---|---|"]
        for k, v in pi.items():
            wr = f"{v['wr']*100:.1f}%" if v.get("wr") is not None else "n/a"
            out.append(f"| {k} | {v.get('n',0)} | {v.get('wins',0)} | {wr} |")
        out.append("")

    if sharpe is not None:
        out += [
            "## In-sample Sharpe (sanity figure ONLY — not the verdict)",
            "",
            f"Equal-weight daily book annualised Sharpe: **{sharpe}**. "
            "This is reported for honesty/context. Per `EDGE_VERDICT_2026-05-18.md` "
            "a gaudy in-sample Sharpe is **not** a pass — only the harness "
            "walk-forward verdict below counts.",
            "",
        ]

    out += ["## Harness verdict (THE gate)", ""]
    if "per_window_eff" in h:
        effs = " ".join(
            (f"{e['eff']:+.2f}" if e["eff"] is not None else "n/a")
            for e in h["per_window_eff"])
        out += [
            f"- per-window eff (new->old): `{effs}`",
            f"- windows scored: {h.get('windows_scored')}  "
            f"(strong {h.get('windows_strong')}: "
            f"+{h.get('strong_positive')}/-{h.get('strong_negative')})",
            f"- `is_admissible()`: {h.get('admissible_via_is_admissible')}",
            f"- **{flag}** — {h.get('reason', 'n/a')}",
            "",
        ]
        if h.get("windows_scored", 0) >= harness.MIN_STABLE_WINDOWS:
            out.append("- **classification: TESTED — the harness rendered a real "
                        "eff-stability verdict.** The continuous-position redesign "
                        "achieved the window density Fork 2 could not.")
        else:
            out.append(f"- **classification: STILL UNTESTED — only "
                        f"{h.get('windows_scored')} scored window(s); harness "
                        f"needs >= {harness.MIN_STABLE_WINDOWS}.**")
    else:
        out.append(f"- **{flag}** — {h.get('reason', 'n/a')}")
    out.append("")

    out += ["## Honest conclusion", ""]
    scored = h.get("windows_scored", 0)
    if adm:
        out += [
            "**H-008 CLEARED `edge_stability_harness`.** This is the first signal "
            "to pass the walk-forward gate. Against a poor base rate (four "
            "straight kills) this must be treated as a **research candidate, not "
            "a green light.** Before any wiring or sizing it still needs: "
            "(a) re-test on a fresh out-of-sample period, (b) full transaction-"
            "cost / slippage modelling (futures roll cost, bid-ask), (c) a "
            "deflated-Sharpe / SPA multiple-testing correction, (d) operator "
            "review. The harness is necessary, not sufficient — `cot_positioning` "
            "passed DSR + SPA and was still a leakage artifact. No wiring here.",
        ]
    elif scored >= harness.MIN_STABLE_WINDOWS:
        out += [
            "**H-008 was TESTED and REJECTED.** The continuous-position redesign "
            "succeeded at its job — it gave the harness the window density Fork 2 "
            "could not, so the harness rendered a *real* eff-stability verdict. "
            "The verdict is a fail: the slope-momentum signal does not separate "
            "winners from losers with a stable sign across enough 14-day windows. "
            "This is a clean kill, not a data-coverage gap — the fifth in the "
            "EDGE_VERDICT kill-loop. The economic prior (slope momentum proxies "
            "the rate regime) is reasonable, but a sound prior is not an edge. "
            "BOND 2s10s does **not** clear the harness; nothing is wired or sized.",
        ]
    else:
        out += [
            "**H-008 is STILL UNTESTED.** Even the continuous-position redesign "
            "did not give the harness >= 3 scored 14-day windows. This is an "
            "honest non-verdict, not a pass and not a clean fail. The remaining "
            "blocker is genuine sample coverage, not design.",
        ]
    out.append("")
    return "\n".join(out)


# ===========================================================================
# Orchestration
# ===========================================================================
def run(quick: bool) -> dict:
    print("# fetching FRED DGS2 / DGS10 ...", file=sys.stderr)
    dgs2 = fetch_fred_series("DGS2")
    dgs10 = fetch_fred_series("DGS10")
    if not dgs2 or not dgs10:
        return {"records": [], "harness": {"admissible": False,
                "reason": "FRED DGS2/DGS10 fetch failed"},
                "error": "FRED fetch failed"}
    print(f"#   DGS2={len(dgs2)} obs  DGS10={len(dgs10)} obs", file=sys.stderr)

    instruments = BOND_INSTRUMENTS_QUICK if quick else BOND_INSTRUMENTS_FULL
    price_by_inst: dict[str, dict[str, float]] = {}
    for tk, label in instruments:
        print(f"# fetching {tk} ({label}) ...", file=sys.stderr)
        px = fetch_yf_close(tk)
        if len(px) >= 60:
            price_by_inst[tk] = px
            print(f"#   {tk}: {len(px)} bars", file=sys.stderr)
        else:
            print(f"#   {tk}: SKIP (only {len(px)} bars)", file=sys.stderr)
        time.sleep(0.5)

    if not price_by_inst:
        return {"records": [], "harness": {"admissible": False,
                "reason": "no bond instrument prices fetched"},
                "error": "no prices"}

    bt = backtest_continuous(dgs2, dgs10, price_by_inst)
    recs = bt.get("records", [])
    res = {
        "records": recs,
        "per_inst": bt.get("per_inst", {}),
        "in_sample_sharpe": in_sample_sharpe(bt.get("daily_rets", [])),
        "dgs2_obs": len(dgs2),
        "dgs10_obs": len(dgs10),
    }
    if len(recs) < harness.MIN_WINDOW_N:
        res["harness"] = {"admissible": False,
                          "reason": f"INSUFFICIENT DATA — {len(recs)} records, "
                                    f"harness needs >= {harness.MIN_WINDOW_N}/window",
                          "windows_scored": 0}
    else:
        res["harness"] = harness_verdict(recs)
    return res


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true",
                    help="smaller instrument set for a fast smoke run")
    ap.add_argument("--json", dest="as_json", action="store_true")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "reports" / "h008_bond_2s10s_redesign_2026-05-18.md")
    args = ap.parse_args()

    res = run(args.quick)

    if args.as_json:
        slim = {k: v for k, v in res.items() if k != "records"}
        slim["n_records"] = len(res.get("records", []))
        print(json.dumps(slim, indent=2, default=str))
        return 0

    report = render_report(res)
    args.out.write_text(report, encoding="utf-8")
    print(f"# wrote {args.out}", file=sys.stderr)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
