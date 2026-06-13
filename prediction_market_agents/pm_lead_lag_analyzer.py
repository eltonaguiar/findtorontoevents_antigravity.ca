#!/usr/bin/env python3
"""
pm_lead_lag_analyzer.py — IDEA-H lead/lag analysis (DAILY_IDEAS 2026-05-24 build plan)
======================================================================================
For each macro prediction market with >=20 daily odds snapshots (captured by
pm_odds_history.py), cross-correlates daily odds CHANGES against underlying daily
returns at lags -3..+3 and classifies the market as:

  LEADING    — best |r| >= 0.30 at lag k >= +1 (today's odds move correlates with
               FUTURE underlying returns → usable as a signal input)
  COINCIDENT — best |r| >= 0.30 at lag 0
  REACTIVE   — best |r| >= 0.30 at lag k <= -1 (odds follow the market → discard
               for trading per DAILY_IDEAS IDEA-H)
  NO_SIGNAL  — no lag reaches |r| >= 0.30

Underlyings tested per market: TLT (long-duration bonds) and EURUSD=X (USD leg) —
the two instruments pm_macro_overlay.py actually trades on Fed-rate consensus.

Output: prediction_market_agents/data/pm_leadlag_report.json (always rewritten with
a fresh generated_at, even when history is insufficient, so freshness checks work).

Leakage note: this is a DESCRIPTIVE report computed entirely from past snapshots.
Any future consumer that gates picks on these verdicts must only use a report
generated strictly before the pick timestamp.

OPT-IN SIDECAR per CLAUDE.md Wire-Up Rule: emits no picks, changes no production
behavior. Follow-up wiring (source-weight adjustment) is named in the PR body.

Self-test (no network): python prediction_market_agents/pm_lead_lag_analyzer.py --self-test
"""

from __future__ import annotations

import json
import logging
import math
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_FILE = DATA_DIR / "pm_odds_history.jsonl"
REPORT_FILE = DATA_DIR / "pm_leadlag_report.json"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [pm_leadlag] %(message)s")

MIN_DAILY_POINTS = 20      # per DAILY_IDEAS IDEA-H: ">20 daily data points"
MIN_PAIRED_POINTS = 10     # minimum aligned (Δodds, return) pairs per lag
LAGS = range(-3, 4)        # k in -3..+3 per the build plan
R_THRESHOLD = 0.30         # Pearson |r| floor per the build plan
UNDERLYINGS = ["TLT", "EURUSD=X"]


def _pearson(xs: list[float], ys: list[float]) -> Optional[float]:
    n = len(xs)
    if n < 3 or n != len(ys):
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None
    return cov / (sx * sy)


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta (Numerical Recipes)."""
    tiny = 1e-30
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, 200):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 3e-7:
            break
    return h


def _betai(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
             + a * math.log(x) + b * math.log(1.0 - x))
    bt = math.exp(lbeta)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def _pearson_pvalue(r: float, n: int) -> Optional[float]:
    """Two-tailed p-value for a Pearson r under H0: rho=0 (Student-t, df=n-2)."""
    df = n - 2
    if df <= 0:
        return None
    if abs(r) >= 1.0:
        return 0.0
    t2 = (r * r) * df / (1.0 - r * r)
    return _betai(0.5 * df, 0.5, df / (df + t2))


def load_history(path: Path = HISTORY_FILE) -> dict[tuple[str, str], dict[str, float]]:
    """Return {(platform, market_id): {date: prob}} keeping one prob per date."""
    series: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    if not path.exists():
        return series
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                key = (row["platform"], str(row["market_id"]))
                series[key].setdefault(row["date"], float(row["prob"]))
            except Exception:
                continue
    return series


def fetch_underlying_returns(symbol: str, start: str, end: str) -> dict[str, float]:
    """Daily {date: pct_return} for symbol over [start, end] via yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        logger.warning("yfinance unavailable — cannot fetch %s", symbol)
        return {}
    try:
        end_plus = (datetime.strptime(end, "%Y-%m-%d") + timedelta(days=5)).strftime("%Y-%m-%d")
        hist = yf.Ticker(symbol).history(start=start, end=end_plus, interval="1d")
        closes = [(idx.strftime("%Y-%m-%d"), float(c)) for idx, c in hist["Close"].items()]
    except Exception as exc:
        logger.warning("yfinance fetch failed for %s: %s", symbol, exc)
        return {}
    rets: dict[str, float] = {}
    for (d_prev, c_prev), (d_cur, c_cur) in zip(closes, closes[1:]):
        if c_prev > 0:
            rets[d_cur] = (c_cur - c_prev) / c_prev
    return rets


def _odds_changes(prob_by_date: dict[str, float]) -> list[tuple[str, float]]:
    dates = sorted(prob_by_date)
    return [(d_cur, prob_by_date[d_cur] - prob_by_date[d_prev])
            for d_prev, d_cur in zip(dates, dates[1:])]


def analyze_market(prob_by_date: dict[str, float],
                   returns_by_symbol: dict[str, dict[str, float]]) -> list[dict]:
    """Cross-correlate one market's Δodds against each underlying at every lag."""
    changes = _odds_changes(prob_by_date)
    results = []
    for symbol, rets in returns_by_symbol.items():
        if not rets:
            continue
        trading_days = sorted(rets)
        day_index = {d: i for i, d in enumerate(trading_days)}
        best_lag, best_r, best_n = None, 0.0, 0
        per_lag = {}
        for k in LAGS:
            xs, ys = [], []
            for date, delta in changes:
                if date not in day_index:
                    continue
                j = day_index[date] + k
                if 0 <= j < len(trading_days):
                    xs.append(delta)
                    ys.append(rets[trading_days[j]])
            r = _pearson(xs, ys) if len(xs) >= MIN_PAIRED_POINTS else None
            per_lag[str(k)] = {"r": round(r, 4) if r is not None else None, "n": len(xs)}
            if r is not None and abs(r) > abs(best_r):
                best_lag, best_r, best_n = k, r, len(xs)
        if best_lag is None:
            verdict = "INSUFFICIENT_PAIRS"
        elif abs(best_r) < R_THRESHOLD:
            verdict = "NO_SIGNAL"
        elif best_lag >= 1:
            verdict = "LEADING"
        elif best_lag == 0:
            verdict = "COINCIDENT"
        else:
            verdict = "REACTIVE"
        best_p = (_pearson_pvalue(best_r, best_n)
                  if best_lag is not None and best_n > 2 else None)
        results.append({
            "underlying": symbol,
            "verdict": verdict,
            "best_lag": best_lag,
            "best_r": round(best_r, 4) if best_lag is not None else None,
            "best_p_uncorrected": round(best_p, 5) if best_p is not None else None,
            "n_pairs": best_n,
            "per_lag": per_lag,
        })
    return results


def run(history_path: Path = HISTORY_FILE, report_path: Path = REPORT_FILE,
        returns_override: Optional[dict[str, dict[str, float]]] = None) -> dict:
    series = load_history(history_path)
    eligible = {k: v for k, v in series.items() if len(v) >= MIN_DAILY_POINTS}
    skipped = {f"{p}:{m}": len(v) for (p, m), v in series.items() if len(v) < MIN_DAILY_POINTS}

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "pm_lead_lag_analyzer",
        "methodology": (
            f"Pearson r of daily odds-change vs underlying daily return at lags -3..+3. "
            f"Gates: >={MIN_DAILY_POINTS} daily snapshots/market, >={MIN_PAIRED_POINTS} aligned pairs/lag, "
            f"|r|>={R_THRESHOLD} for a verdict. LEADING = best lag >= +1 (odds precede returns)."
        ),
        "history_file": str(history_path),
        "markets_tracked": len(series),
        "markets_eligible": len(eligible),
        "markets_below_min_days": skipped,
        "markets": [],
    }

    if not eligible:
        report["status"] = "INSUFFICIENT_HISTORY"
        report_path.write_text(json.dumps(report, indent=2, default=str))
        logger.info("No market has >=%d daily points yet (%d tracked) — report says so",
                    MIN_DAILY_POINTS, len(series))
        return report

    all_dates = sorted({d for v in eligible.values() for d in v})
    if returns_override is not None:
        returns_by_symbol = returns_override
    else:
        returns_by_symbol = {
            sym: fetch_underlying_returns(sym, all_dates[0], all_dates[-1])
            for sym in UNDERLYINGS
        }

    for (platform, market_id), prob_by_date in sorted(eligible.items()):
        report["markets"].append({
            "platform": platform,
            "market_id": market_id,
            "n_days": len(prob_by_date),
            "first_date": min(prob_by_date),
            "last_date": max(prob_by_date),
            "correlations": analyze_market(prob_by_date, returns_by_symbol),
        })

    # Multiple-testing correction. Each market reports the BEST of 7 lags x each
    # underlying, so the raw |r|>=0.30 verdict is optimistic twice over (best-of-7
    # selection + many markets). Bonferroni-correct across every reported
    # correlation result so a LEADING verdict that survives is trustworthy.
    all_results = [c for m in report["markets"] for c in m["correlations"]
                   if c.get("best_r") is not None]
    n_tests = len(all_results)
    bonf_alpha = 0.05 / n_tests if n_tests else 0.05
    for c in all_results:
        p = c.get("best_p_uncorrected")
        c["bonferroni_significant"] = bool(p is not None and p < bonf_alpha)

    leading = [c for m in report["markets"] for c in m["correlations"]
               if c["verdict"] == "LEADING"]
    leading_sig = [c for c in leading if c.get("bonferroni_significant")]
    report["status"] = "OK"
    report["n_correlation_tests"] = n_tests
    report["bonferroni_alpha"] = round(bonf_alpha, 6)
    report["leading_count"] = len(leading)
    report["leading_bonferroni_significant_count"] = len(leading_sig)
    report["caveat"] = (
        "LEADING verdicts use the build-plan threshold |r|>=0.30 WITHOUT correction. "
        "With n_correlation_tests best-of-7-lag comparisons, treat only "
        "bonferroni_significant=true rows as candidate signals; the rest are "
        "consistent with noise. None are tradeable until they survive a held-out "
        "forward window (no look-ahead) per docs/MUTATION_THREE_AXIS_PROTOCOL.md."
    )
    report_path.write_text(json.dumps(report, indent=2, default=str))
    logger.info("Analyzed %d markets: %d LEADING (raw |r|>=%.2f), %d survive Bonferroni "
                "(alpha=%.2g over %d tests) -> %s",
                len(report["markets"]), len(leading), R_THRESHOLD,
                len(leading_sig), bonf_alpha, n_tests, report_path)
    return report


def _self_test() -> int:
    """Synthetic check: odds that lead returns by 1 day must classify LEADING."""
    import random
    rng = random.Random(42)
    base = datetime(2026, 1, 5)
    dates = [(base + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(40)]
    deltas = [rng.uniform(-0.05, 0.05) for _ in dates]
    prob, probs = 0.5, {}
    for d, dl in zip(dates, deltas):
        prob = min(0.95, max(0.05, prob + dl))
        probs[d] = round(prob, 4)
    # Return on day t+1 mirrors odds change on day t (odds LEAD by 1 day)
    rets = {}
    for i in range(1, len(dates)):
        rets[dates[i]] = (probs[dates[i - 1]] - probs[dates[i - 2]] if i >= 2 else 0.0) * 0.5 \
            + rng.uniform(-0.001, 0.001)

    tmp_hist = DATA_DIR / "_selftest_history.jsonl"
    tmp_report = DATA_DIR / "_selftest_report.json"
    with tmp_hist.open("w") as fh:
        for d in dates:
            fh.write(json.dumps({"date": d, "platform": "kalshi", "market_id": "TEST",
                                 "prob": probs[d]}) + "\n")
    try:
        report = run(tmp_hist, tmp_report, returns_override={"TLT": rets})
        verdicts = [c for m in report["markets"] for c in m["correlations"]]
        assert verdicts, "no correlations computed"
        v = verdicts[0]
        assert v["verdict"] == "LEADING", f"expected LEADING, got {v['verdict']} (lag={v['best_lag']} r={v['best_r']})"
        assert v["best_lag"] == 1, f"expected best_lag=1, got {v['best_lag']}"
        print(f"SELF-TEST PASS: verdict={v['verdict']} lag={v['best_lag']} r={v['best_r']} n={v['n_pairs']}")
        return 0
    finally:
        tmp_hist.unlink(missing_ok=True)
        tmp_report.unlink(missing_ok=True)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(_self_test())
    try:
        run()
    except Exception as exc:  # sidecar must never break the calling workflow
        logger.error("pm_lead_lag_analyzer failed: %s", exc)
        sys.exit(0)
