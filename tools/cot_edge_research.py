#!/usr/bin/env python3
"""COT edge research — does real CFTC commercial positioning predict returns?

Swarm-endorsed (deepseek+xai+cerebras, 2026-05-17, Option B): rebuild the COT
signal on REAL CFTC data only — no RSI proxy. This script is the *test* before
any strategy is wired: it answers, walk-forward, whether the commercial-net
COT z-score actually predicts forward futures returns.

Method (no look-ahead):
  1. Real COT history from data/cftc_cot/<C>_latest.json (commercial long/short
     per weekly report — fetched via tools/cftc_cot_fetcher.py --limit 700).
  2. commercial_net = comm_long_all - comm_short_all. A 52-week rolling z-score
     uses ONLY weeks strictly before the signal week.
  3. COT report (Tuesday data) is published the following Friday — entry is the
     weekly close AFTER the report date, never the report week itself.
  4. Classic COT: commercials are the informed hedgers. z >= +Z LONG, z <= -Z
     SHORT. Forward return measured N weeks after entry.
  5. Edge = hit-rate (signed forward return agrees with the signal) + mean
     signed return, pooled and per-contract, then split by year for stability.

Price: yfinance weekly close for the contract's yf_ticker.

    python tools/cot_edge_research.py [--z 1.5] [--fwd-weeks 4] [--out report.md]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COT_DIR = ROOT / "data" / "cftc_cot"

# Bond contracts (ZB/ZN/ZT) excluded — their Socrata legacy series is stale
# (ends 2022-02). Current-data contracts only.
CONTRACTS = ("GC", "SI", "HG", "NQ", "YM")
ROLL = 52          # rolling z-score window (weeks)


def _ci(v):
    try:
        return int(float(str(v).replace(",", "")))
    except (TypeError, ValueError):
        return None


def load_cot(contract: str) -> tuple[str, list[tuple[str, int]]]:
    """Return (yf_ticker, [(report_date, commercial_net), ...] sorted ASC)."""
    path = COT_DIR / f"{contract}_latest.json"
    d = json.loads(path.read_text(encoding="utf-8"))
    yf_ticker = d.get("yf_ticker", f"{contract}=F")
    series = []
    for row in d.get("rows", []):
        dt = str(row.get("report_date") or row.get("report_date_as_yyyy_mm_dd") or "")[:10]
        lng, sht = _ci(row.get("comm_positions_long_all")), _ci(row.get("comm_positions_short_all"))
        if len(dt) == 10 and lng is not None and sht is not None:
            series.append((dt, lng - sht))
    series.sort(key=lambda x: x[0])
    # de-dup by date (keep last)
    seen: dict[str, int] = {}
    for dt, net in series:
        seen[dt] = net
    return yf_ticker, sorted(seen.items())


def fetch_weekly_close(ticker: str) -> dict[str, float]:
    """yfinance weekly close keyed by ISO date string."""
    import time
    import warnings
    warnings.filterwarnings("ignore")
    import yfinance as yf
    # period="max" + single-call avoids the throttle that start=/rapid-loop hits;
    # retry once if a throttled response comes back near-empty.
    df = None
    for attempt in range(3):
        df = yf.download(ticker, period="max", interval="1wk",
                         progress=False, auto_adjust=True)
        if df is not None and len(df) >= 50:
            break
        time.sleep(5)
    if df is None or len(df) < 50:
        return {}
    close = df["Close"]
    if hasattr(close, "columns"):     # MultiIndex columns (yfinance >=0.2) -> DataFrame
        close = close.iloc[:, 0]
    out = {}
    for idx, val in close.items():    # Series: idx = Timestamp, val = float
        try:
            v = float(val)
        except (TypeError, ValueError):
            continue
        d = idx.date() if hasattr(idx, "date") else None
        if d is not None:
            out[str(d)] = v
    return out


def _next_close_on_or_after(prices: dict[str, float], dates_sorted: list[str], iso: str):
    """First (date, close) with date > iso — the post-publish entry bar."""
    import bisect
    i = bisect.bisect_right(dates_sorted, iso)
    if i >= len(dates_sorted):
        return None
    d = dates_sorted[i]
    return d, prices[d]


def research(z_thresh: float, fwd_weeks: int) -> dict:
    results = {"contracts": {}, "pooled": [], "by_year": {}}
    for c in CONTRACTS:
        yf_ticker, cot = load_cot(c)
        if len(cot) < ROLL + fwd_weeks + 5:
            results["contracts"][c] = {"skip": f"only {len(cot)} COT weeks"}
            continue
        prices = fetch_weekly_close(yf_ticker)
        if not prices:
            results["contracts"][c] = {"skip": "no price"}
            continue
        pdates = sorted(prices)
        signals = []
        nets = [n for _, n in cot]
        for i in range(ROLL, len(cot) - 1):
            window = nets[i - ROLL:i]            # strictly past
            mu, sd = statistics.fmean(window), statistics.pstdev(window)
            if sd <= 0:
                continue
            z = (nets[i] - mu) / sd
            if abs(z) < z_thresh:
                continue
            report_date = cot[i][0]
            entry = _next_close_on_or_after(prices, pdates, report_date)
            if not entry:
                continue
            entry_date, entry_px = entry
            ei = pdates.index(entry_date)
            if ei + fwd_weeks >= len(pdates):
                continue
            exit_px = prices[pdates[ei + fwd_weeks]]
            if entry_px <= 0:
                continue
            fwd_ret = exit_px / entry_px - 1.0
            direction = 1 if z > 0 else -1   # commercials net-long extreme => LONG
            signed = fwd_ret * direction      # >0 = signal correct
            rec = {"date": report_date, "z": round(z, 2), "dir": direction,
                   "fwd_ret": round(fwd_ret, 4), "signed": round(signed, 4),
                   "year": report_date[:4]}
            signals.append(rec)
            results["pooled"].append(rec)
            results["by_year"].setdefault(report_date[:4], []).append(rec)
        if signals:
            hit = sum(1 for s in signals if s["signed"] > 0) / len(signals)
            results["contracts"][c] = {
                "n": len(signals), "hit_rate": round(hit, 3),
                "mean_signed": round(statistics.fmean(s["signed"] for s in signals), 4),
            }
        else:
            results["contracts"][c] = {"n": 0}
    return results


def render(r: dict, z_thresh: float, fwd_weeks: int) -> str:
    pooled = r["pooled"]
    out = [f"# COT Edge Research — real CFTC commercial positioning",
           "",
           f"Signal: 52-week commercial-net z-score, |z| >= {z_thresh}, trade WITH "
           f"commercials. Forward return measured {fwd_weeks} weeks after the "
           f"post-publish entry bar. No look-ahead.", ""]
    if not pooled:
        out.append("**No signals generated.**")
        return "\n".join(out)
    hit = sum(1 for s in pooled if s["signed"] > 0) / len(pooled)
    mean_signed = statistics.fmean(s["signed"] for s in pooled)
    out += [f"## Pooled — n={len(pooled)} signals",
            f"- hit-rate (forward return agrees with signal): **{hit*100:.1f}%**",
            f"- mean signed forward return: **{mean_signed*100:+.2f}%** per signal",
            f"- a real edge needs hit-rate > 55% AND mean signed > 0 AND year-stable.",
            "",
            "## Per contract", "", "| contract | n | hit-rate | mean signed |",
            "|---|---|---|---|"]
    for c, v in r["contracts"].items():
        if "skip" in v:
            out.append(f"| {c} | — | — | skipped: {v['skip']} |")
        elif v.get("n"):
            out.append(f"| {c} | {v['n']} | {v['hit_rate']*100:.1f}% | "
                        f"{v['mean_signed']*100:+.2f}% |")
        else:
            out.append(f"| {c} | 0 | — | no signals |")
    out += ["", "## By year — stability check", "",
            "| year | n | hit-rate | mean signed |", "|---|---|---|---|"]
    pos_years = neg_years = 0
    for yr in sorted(r["by_year"]):
        ys = r["by_year"][yr]
        yhit = sum(1 for s in ys if s["signed"] > 0) / len(ys)
        ymean = statistics.fmean(s["signed"] for s in ys)
        pos_years += ymean > 0
        neg_years += ymean <= 0
        out.append(f"| {yr} | {len(ys)} | {yhit*100:.1f}% | {ymean*100:+.2f}% |")
    out += ["",
            f"**Year stability: {pos_years} positive / {neg_years} non-positive.** "
            + ("Edge is year-stable — candidate for the harness."
               if pos_years >= 2 * max(neg_years, 1) and hit > 0.55 and mean_signed > 0
               else "NOT year-stable / sub-threshold — COT z-score is not a usable edge "
                    "at these parameters.")]
    return "\n".join(out)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--z", type=float, default=1.5)
    ap.add_argument("--fwd-weeks", type=int, default=4)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    r = research(args.z, args.fwd_weeks)
    report = render(r, args.z, args.fwd_weeks)
    if args.out:
        args.out.write_text(report, encoding="utf-8")
        print(f"# wrote {args.out}", file=sys.stderr)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
