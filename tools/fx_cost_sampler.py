#!/usr/bin/env python3
"""Sample live FX top-of-book (bid/ask) from Tiingo and record spread diagnostics.

Purpose: measure real FOREX round-trip cost instead of assuming it. Samples are
repeated over a window so a thin / reopened book can be distinguished from a
representative one (wide + high sample-to-sample variance + a frozen price = thin).

Endpoint: https://api.tiingo.com/tiingo/fx/top?tickers=<csv>&token=$TIINGO_API_KEY
Each row carries quoteTimestamp (UTC), bidPrice, askPrice, midPrice.

Two modes, ONE implementation:

  legacy (default) - poll for --minutes at --interval, dump raw samples plus a
    per-pair summary. This is the mode that produced the Sunday-reopen upper bound.

  --overlap - the representative-session measurement, safe to run unattended:
      * only samples inside the London/NY overlap (13:00-16:00 UTC, Mon-Fri);
      * keeps polling until every pair has >= --until-samples plausible quotes;
      * classifies every pair REPRESENTATIVE / FROZEN / WIDE / NO_QUOTE /
        INSUFFICIENT_N with the rule that produced the verdict recorded verbatim;
      * aggregates a representative cost;
      * chains the FX mean-reversion re-run to that cost and writes a strategy
        verdict from an ALLOWLIST that cannot contain INVESTABLE;
      * writes reports/cost_measurement_forex/FOREX_COST_<YYYYMMDD>_overlap.{json,md}
        (a blocked run never overwrites a MEASURED_REPRESENTATIVE artifact).

Usage:
    python3 tools/fx_cost_sampler.py --minutes 20 --interval 45 \
        --out reports/cost_measurement_forex/fx_top_of_book_samples.json
    python3 tools/fx_cost_sampler.py --overlap --until-samples 30 --interval 20 \
        --max-minutes 12
    python3 tools/fx_cost_sampler.py --overlap --dry-run          # no network, prints
    python3 tools/fx_cost_sampler.py --overlap --self-test        # rule fixtures
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # AGENTS.md: direct-script invocation has no package
    sys.path.insert(0, str(ROOT))

PAIRS = ["eurusd", "gbpusd", "usdjpy", "audusd", "usdcad", "usdchf", "eurgbp", "eurjpy"]
MAJORS = ["eurusd", "gbpusd", "usdjpy", "audusd", "usdcad", "usdchf"]
ENDPOINT = "https://api.tiingo.com/tiingo/fx/top"

# ---------------------------------------------------------------- overlap rules
# Every constant below is restated verbatim inside the emitted artifact so the
# judgement is auditable rather than asserted.
OVERLAP_START_UTC_HOUR = 13
OVERLAP_END_UTC_HOUR = 16
MIN_SAMPLES = 30
FROZEN_MAX_DISTINCT_FRAC = 0.10   # distinct spread values / n below this = frozen
FROZEN_MIN_DISTINCT = 3          # ... and never call a pair frozen below this count
FROZEN_MAX_IDENTICAL_RUN = 10    # 10 consecutive identical bid/ask = frozen
STALE_QUOTE_SECONDS = 300.0      # vendor quoteTimestamp older than this = frozen
WIDE_ABS_BP = 8.0               # a G10 pair wider than this round trip is WIDE
WIDE_DISPERSION_RATIO = 0.50     # IQR / median above this = unstable = WIDE
BREAK_EVEN_BP_DOCUMENTED = 4.3038
DECISION_OUT_DIR = ROOT / "reports" / "cost_measurement_forex"

# The auto-promote guard. This tuple is the enforcement point: no code path may
# write a strategy verdict outside it, and INVESTABLE is not in it.
ALLOWED_STRATEGY_VERDICTS = (
    "NOT_INVESTABLE",
    "HUMAN_REVIEW_REQUIRED",
    "BLOCKED_NO_REPRESENTATIVE_SESSION",
    "UNCHANGED_UNKNOWN",
)

# Labelling only - never used to suppress sampling. A fixed-date holiday run
# still polls; it is just labelled when the book comes back empty.
FIXED_DATE_HOLIDAYS = {
    (1, 1), (5, 1), (7, 1), (7, 4), (12, 24), (12, 25), (12, 26), (12, 31),
}

RULES_DOC = {
    "session_window": (
        "in-window iff weekday(Mon-Fri) AND 13:00 <= UTC hour < 16:00. "
        "GitHub cron is UTC; the window is fixed in UTC year-round."
    ),
    "min_samples": f"a pair needs n >= {MIN_SAMPLES} plausible quotes to be judged",
    "no_quote": "n_plausible == 0",
    "insufficient_n": f"0 < n_plausible < {MIN_SAMPLES}",
    "frozen": (
        f"distinct spread values < max({FROZEN_MIN_DISTINCT}, "
        f"{FROZEN_MAX_DISTINCT_FRAC:.0%} of n) OR longest run of identical bid/ask >= "
        f"{FROZEN_MAX_IDENTICAL_RUN} OR median vendor quote age > {STALE_QUOTE_SECONDS:.0f}s. "
        "A pair that returns one price for dozens of polls is frozen, not tight - "
        "it is never reported as a 0-sd bargain."
    ),
    "wide": (
        f"median full spread > {WIDE_ABS_BP} bp OR IQR/median > {WIDE_DISPERSION_RATIO} "
        "(unstable book)"
    ),
    "verdict_order": "NO_QUOTE -> INSUFFICIENT_N -> FROZEN -> WIDE -> REPRESENTATIVE (first match wins)",
    "decision_cost": (
        "median of the per-pair medians over the REPRESENTATIVE pairs of the probe "
        "universe (the traded universe is 55 crosses, so the all-pairs median is the "
        "honest basis); the USD-major median-of-medians is reported alongside"
    ),
    "strategy_verdict": (
        "NOT_INVESTABLE iff measured decision cost > break-even (derived from the re-run, "
        "not hardcoded); otherwise HUMAN_REVIEW_REQUIRED. The allowlist is "
        f"{list(ALLOWED_STRATEGY_VERDICTS)} - INVESTABLE is unreachable by construction."
    ),
}


# ---------------------------------------------------------------- transport
def fetch(tickers: list[str], token: str, timeout: int = 20) -> list[dict]:
    url = f"{ENDPOINT}?tickers={','.join(tickers)}&token={token}"
    req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


# ---------------------------------------------------------------- small helpers
def _pct(sorted_vals: list[float], q: float) -> float | None:
    """Linear-interpolation percentile; no numpy dependency."""
    n = len(sorted_vals)
    if n == 0:
        return None
    if n == 1:
        return float(sorted_vals[0])
    pos = (n - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return float(sorted_vals[int(pos)])
    return float(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo))


def _parse_ts(s) -> datetime | None:
    if not s:
        return None
    text = str(s).strip().replace("Z", "+00:00")
    try:
        d = datetime.fromisoformat(text)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def session_state(now: datetime) -> dict:
    weekday = now.weekday() < 5
    in_window = weekday and OVERLAP_START_UTC_HOUR <= now.hour < OVERLAP_END_UTC_HOUR
    if in_window:
        label, reason = "LONDON_NY_OVERLAP", (
            f"weekday {now.strftime('%A')} {now.hour:02d}:xx UTC inside 13:00-16:00 UTC")
    elif not weekday:
        label, reason = "WEEKEND", (
            f"{now.strftime('%A')} - FX week closed or reopening; the overlap is Mon-Fri "
            "13:00-16:00 UTC")
    else:
        label, reason = "OUTSIDE_OVERLAP", (
            f"weekday but {now.hour:02d}:xx UTC is outside 13:00-16:00 UTC")
    holiday = (now.month, now.day) in FIXED_DATE_HOLIDAYS
    return {
        "now_utc": now.isoformat(),
        "weekday": weekday,
        "utc_hour": now.hour,
        "in_window": in_window,
        "label": label,
        "reason": reason,
        "holiday_suspected_fixed_date": holiday,
        "holiday_note": ("fixed-date holiday list is a LABEL only (approximate; no FX "
                         "calendar is bundled) and never suppresses sampling"
                         if holiday else ""),
    }


# ---------------------------------------------------------------- sampling loop
def sample_loop(pairs: list[str], token: str, interval: float, max_minutes: float,
                until_samples: int | None, max_polls: int | None,
                max_consecutive_errors: int = 5) -> dict:
    """Poll until the deadline / sample target. Records every poll, never raises."""
    started = datetime.now(timezone.utc)
    deadline = time.time() + max_minutes * 60
    samples: list[dict] = []
    plausible = {p: 0 for p in pairs}
    n = 0
    consecutive_errors = 0
    api_unreachable = False

    while True:
        if n > 0:
            if time.time() >= deadline:
                break
            if until_samples is not None and all(c >= until_samples for c in plausible.values()):
                break
            if max_polls is not None and n >= max_polls:
                break
        local_ts = datetime.now(timezone.utc).isoformat()
        try:
            rows = fetch(pairs, token)
        except Exception as exc:  # noqa: BLE001 - record and continue
            samples.append({"local_ts": local_ts, "error": repr(exc)})
            n += 1
            consecutive_errors += 1
            if consecutive_errors >= max_consecutive_errors:
                api_unreachable = True
                break
            time.sleep(interval)
            continue
        consecutive_errors = 0
        for row in rows:
            bid, ask = row.get("bidPrice"), row.get("askPrice")
            mid = row.get("midPrice")
            if mid is None and bid and ask:
                mid = (bid + ask) / 2.0
            rec = {
                "local_ts": local_ts,
                "quote_ts": row.get("quoteTimestamp"),
                "pair": row.get("ticker"),
                "bid": bid,
                "ask": ask,
                "mid": mid,
                "bid_size": row.get("bidSize"),
                "ask_size": row.get("askSize"),
            }
            if bid and ask and mid and ask > bid > 0:
                rec["spread"] = ask - bid
                rec["full_spread_bp"] = (ask - bid) / mid * 1e4
                rec["half_spread_bp"] = (ask - bid) / 2.0 / mid * 1e4
                rec["plausible"] = True
                plausible[str(rec["pair"]).lower()] = plausible.get(
                    str(rec["pair"]).lower(), 0) + 1
            else:
                rec["plausible"] = False
            samples.append(rec)
        n += 1
        print(f"[{n}] {local_ts} rows={len(rows)}", flush=True)
        if time.time() < deadline:
            time.sleep(interval)

    return {
        "window_start_utc": started.isoformat(),
        "window_end_utc": datetime.now(timezone.utc).isoformat(),
        "poll_count": n,
        "samples": samples,
        "api_unreachable": api_unreachable,
    }


# ---------------------------------------------------------------- per-pair stats
def per_pair_stats(samples: list[dict], pair: str) -> dict:
    rows = [s for s in samples if str(s.get("pair", "")).lower() == pair]
    ok = [s for s in rows if s.get("plausible")]
    vals = sorted(float(s["full_spread_bp"]) for s in ok)
    n = len(vals)
    stats: dict = {
        "n": n,
        "n_raw": len(rows),
        "min": None, "p25": None, "median": None, "p75": None, "max": None,
        "mean": None, "sd": None, "sd_pop": None, "iqr": None,
        "distinct_spreads": 0, "distinct_mids": 0, "max_identical_run": 0,
        "median_quote_age_s": None,
    }
    if n:
        stats.update({
            "min": vals[0], "p25": _pct(vals, 0.25), "median": _pct(vals, 0.50),
            "p75": _pct(vals, 0.75), "max": vals[-1],
            "mean": statistics.fmean(vals),
            "sd": statistics.stdev(vals) if n > 1 else 0.0,
            "sd_pop": statistics.pstdev(vals) if n > 1 else 0.0,
            "distinct_spreads": len({round(v, 10) for v in vals}),
            "distinct_mids": len({round(float(s["mid"]), 10) for s in ok}),
        })
        stats["iqr"] = stats["p75"] - stats["p25"]
        # Longest run of an unchanged quote OR an unchanged spread. A book that
        # reprices the mid by a hair while the spread never moves is still frozen.
        run = best = 1
        prev = None
        for s in ok:
            key = (round(float(s["bid"]), 10), round(float(s["ask"]), 10),
                   round(float(s["full_spread_bp"]), 10))
            if key == prev:
                run += 1
            else:
                run, prev = 1, key
            best = max(best, run)
        stats["max_identical_run"] = best
        ages = []
        for s in ok:
            qt, lt = _parse_ts(s.get("quote_ts")), _parse_ts(s.get("local_ts"))
            if qt and lt:
                ages.append(max(0.0, (lt - qt).total_seconds()))
        if ages:
            stats["median_quote_age_s"] = statistics.median(ages)
    return stats


def classify(stats: dict) -> tuple[str, str]:
    """Return (verdict, rule). First match wins; every rule is explicit."""
    n = stats["n"]
    if n == 0:
        return "NO_QUOTE", "n_plausible == 0"
    if n < MIN_SAMPLES:
        return "INSUFFICIENT_N", f"n={n} < min_samples={MIN_SAMPLES}"
    distinct_floor = max(FROZEN_MIN_DISTINCT, math.ceil(FROZEN_MAX_DISTINCT_FRAC * n))
    if stats["distinct_spreads"] < distinct_floor:
        return "FROZEN", (f"distinct_spreads={stats['distinct_spreads']} < "
                          f"{distinct_floor} (max({FROZEN_MIN_DISTINCT}, "
                          f"{FROZEN_MAX_DISTINCT_FRAC:.0%} of n={n}))")
    if stats["max_identical_run"] >= FROZEN_MAX_IDENTICAL_RUN:
        return "FROZEN", (f"longest identical bid/ask run={stats['max_identical_run']} >= "
                          f"{FROZEN_MAX_IDENTICAL_RUN}")
    age = stats["median_quote_age_s"]
    if age is not None and age > STALE_QUOTE_SECONDS:
        return "FROZEN", f"median vendor quote age={age:.0f}s > {STALE_QUOTE_SECONDS:.0f}s"
    if stats["median"] > WIDE_ABS_BP:
        return "WIDE", f"median={stats['median']:.3f}bp > {WIDE_ABS_BP}bp"
    ratio = (stats["iqr"] / stats["median"]) if stats["median"] else 0.0
    if ratio > WIDE_DISPERSION_RATIO:
        return "WIDE", f"IQR/median={ratio:.3f} > {WIDE_DISPERSION_RATIO} (unstable)"
    return "REPRESENTATIVE", (f"n={n}>= {MIN_SAMPLES}, distinct={stats['distinct_spreads']}, "
                              f"max_run={stats['max_identical_run']}, "
                              f"median={stats['median']:.3f}bp<={WIDE_ABS_BP}bp, "
                              f"IQR/median={ratio:.3f}<={WIDE_DISPERSION_RATIO}")


def aggregate(pair_stats: dict[str, dict], pairs: list[str]) -> dict:
    rep = [p for p in pairs if pair_stats[p]["verdict"] == "REPRESENTATIVE"]
    all_vals = sorted(v for p in pairs for v in
                      [pair_stats[p]["median"]] * 1 if pair_stats[p]["median"] is not None)
    out: dict = {
        "n_pairs": len(pairs),
        "n_representative_pairs": len(rep),
        "representative_pairs": rep,
        "verdict_counts": {},
        "decision_cost_bp": None,
        "decision_cost_basis": None,
        "usd_majors_median_of_medians_bp": None,
        "all_representative_pairs_median_bp": None,
        "all_representative_pairs_mean_bp": None,
        "all_representative_pairs_range_bp": None,
        "all_pairs_median_of_medians_bp": None,
    }
    counts: dict[str, int] = {}
    for p in pairs:
        v = pair_stats[p]["verdict"]
        counts[v] = counts.get(v, 0) + 1
    out["verdict_counts"] = counts
    if all_vals:
        out["all_pairs_median_of_medians_bp"] = _pct(all_vals, 0.50)
    if not rep:
        return out
    meds = {p: pair_stats[p]["median"] for p in rep}
    majors = [p for p in rep if p in MAJORS]
    all_med = _pct(sorted(meds.values()), 0.50)
    out.update({
        "all_representative_pairs_median_bp": all_med,
        "all_representative_pairs_mean_bp": statistics.fmean(meds.values()),
        "all_representative_pairs_range_bp": [min(meds.values()), max(meds.values())],
        "usd_majors_median_of_medians_bp": (
            _pct(sorted(meds[p] for p in majors), 0.50) if majors else None),
        "usd_majors_representative": majors,
        "decision_cost_bp": all_med,
        "decision_cost_basis": (
            "median of per-pair medians over REPRESENTATIVE probe pairs "
            f"(n={len(rep)}) - the all-pairs basis, matching the 55-cross traded universe"),
    })
    return out


# ---------------------------------------------------------------- strategy chain
def run_strategy_chain(cost_bp: float, shuffles: int, seed: int) -> dict:
    """Re-run FX mean-reversion at the freshly measured cost. Read-only."""
    from tools.fx_meanrev_research import run as run_meanrev

    res = run_meanrev(cost_bp=cost_bp, n_shuffles=shuffles, seed=seed)
    st = res["universes"]["primary"]["stats"]
    gross = st["mean_gross_bp"]
    clo, chi = st["ci95_net_bp_window_clustered"]
    return {
        "state": "RAN",
        "module": "tools/fx_meanrev_research.py",
        "universe": "primary (dedup_55)",
        "seed": seed,
        "n_shuffles": shuffles,
        "cost_bp_round_trip": cost_bp,
        "break_even_bp_derived_from_run": gross,
        "break_even_bp_documented": BREAK_EVEN_BP_DOCUMENTED,
        "break_even_drift_bp": gross - BREAK_EVEN_BP_DOCUMENTED,
        "cost_minus_break_even_bp": cost_bp - gross,
        "mean_gross_bp": gross,
        "mean_net_bp": st["mean_net_bp"],
        "mean_net_bp_2x": st["mean_net_bp_2x"],
        "ci95_net_bp": st["ci95_net_bp"],
        "ci95_net_bp_window_clustered": [clo, chi],
        "ci_window_clustered_includes_zero": bool(clo <= 0.0 <= chi),
        "n_pair_rebalances": st["n_pair_rebalances"],
        "n_rebalance_windows": st["n_rebalance_windows"],
        "research_runner_gates": res["gates"],
        "research_runner_verdict_at_cost": res["verdict"],
        "research_runner_verdict_note": (
            "recorded for context ONLY - it is never copied into strategy_verdict; "
            "CANDIDATE/WEAK are research states, not investability"),
    }


def decide_strategy_verdict(status: str, chain: dict | None) -> dict:
    """The only place a strategy verdict is produced, and it is allowlist-bound."""
    if status != "MEASURED_REPRESENTATIVE":
        return {
            "strategy_verdict": "BLOCKED_NO_REPRESENTATIVE_SESSION",
            "rule": "no representative session -> no verdict move",
            "verdict_changed": False,
        }
    if not chain or chain.get("state") != "RAN":
        return {
            "strategy_verdict": "UNCHANGED_UNKNOWN",
            "rule": "session measured but the strategy re-run did not complete -> no new information",
            "verdict_changed": False,
        }
    cost = chain["cost_bp_round_trip"]
    be = chain["break_even_bp_derived_from_run"]
    ci_includes_zero = chain["ci_window_clustered_includes_zero"]
    if cost > be:
        return {
            "strategy_verdict": "NOT_INVESTABLE",
            "rule": (f"measured cost {cost:.4f} bp > break-even {be:.4f} bp "
                     "(derived from this run)"),
            "verdict_changed": True,
            "ci_caveat": (f"window-clustered CI at this cost is "
                          f"{chain['ci95_net_bp_window_clustered']}; it "
                          f"{'still includes' if ci_includes_zero else 'excludes'} zero"),
        }
    return {
        "strategy_verdict": "HUMAN_REVIEW_REQUIRED",
        "rule": (f"measured cost {cost:.4f} bp <= break-even {be:.4f} bp - never "
                 "auto-promoted"
                 + ("; window-clustered CI excludes zero, a human must confirm"
                    if not ci_includes_zero
                    else "; window-clustered CI still includes zero, so it is still not closable")),
        "verdict_changed": False,
    }


def guard_verdict(decision: dict) -> dict:
    """Hard stop before anything is written. Raises on an unallowlisted verdict."""
    v = decision.get("strategy_verdict")
    if v == "INVESTABLE":
        raise RuntimeError("auto-promote guard: INVESTABLE is not writable by this tool")
    if v not in ALLOWED_STRATEGY_VERDICTS:
        raise RuntimeError(f"auto-promote guard: verdict {v!r} not in allowlist "
                           f"{ALLOWED_STRATEGY_VERDICTS}")
    decision["guard"] = {
        "enforced_in": "tools/fx_cost_sampler.py::guard_verdict (called before every write)",
        "allowlist": list(ALLOWED_STRATEGY_VERDICTS),
        "investable_reachable": False,
        "why": ("a machine that can promote a strategy to investable is a machine that "
                "can launder a bug into a position"),
    }
    return decision


# ---------------------------------------------------------------- artifact render
def render_md(p: dict) -> str:
    L: list[str] = []
    L.append(f"# FOREX cost - London/NY overlap measurement ({p['run_date']})\n")
    L.append(f"**Status: `{p['status']}`**"
             + (f" - block reason `{p['block_reason']}`" if p.get("block_reason") else "")
             + f" - generated {p['generated_utc']}\n")
    L.append(f"- **Endpoint:** `{p['endpoint']}` via [`tools/fx_cost_sampler.py`](../../tools/fx_cost_sampler.py)")
    L.append(f"- **Session check:** {p['session']['reason']} -> `{p['session']['label']}` "
             f"(in-window: {p['session']['in_window']})")
    L.append(f"- **Sampling:** {p['poll_count']} polls, {p['interval_seconds']}s apart, "
             f"target n>={p['min_samples_target']} plausible quotes per pair")
    L.append(f"- **Commission:** `{p['commission']}` - {p['commission_note']}")
    L.append("- **Strategy verdict:** "
             f"`{p['strategy_decision']['strategy_verdict']}` - {p['strategy_decision']['rule']}")
    L.append(f"- **Verdict moves by this tool:** {p['verdict_moves_by_this_tool']}\n")

    L.append("## Rules (verbatim, so the judgement is auditable)\n")
    for k, v in p["rules"].items():
        L.append(f"- **{k}:** {v}")
    L.append("")

    L.append("## Per-pair (full spread = round trip, bp of mid)\n")
    L.append("| pair | n | min | p25 | median | p75 | max | mean | sd | distinct spreads | distinct mids | max identical run | median quote age s | verdict | rule |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for pair, s in p["per_pair"].items():
        def f(x, d=3):
            return "-" if x is None else (f"{x:.{d}f}" if isinstance(x, float) else str(x))
        L.append(f"| {pair} | {s['n']} | {f(s['min'])} | {f(s['p25'])} | {f(s['median'])} | "
                 f"{f(s['p75'])} | {f(s['max'])} | {f(s['mean'])} | {f(s['sd'])} | "
                 f"{s['distinct_spreads']} | {s['distinct_mids']} | {s['max_identical_run']} | "
                 f"{f(s['median_quote_age_s'], 1)} | **{s['verdict']}** | {s['rule']} |")
    L.append("")

    a = p["aggregate"]
    L.append("## Aggregate\n")
    L.append(f"- verdict counts: `{a['verdict_counts']}`")
    L.append(f"- representative pairs: {a['n_representative_pairs']} / {a['n_pairs']}"
             + (f" ({', '.join(a['representative_pairs'])})" if a["representative_pairs"] else ""))
    L.append(f"- **decision cost:** {a['decision_cost_bp']} bp"
             + (f" - {a['decision_cost_basis']}" if a["decision_cost_basis"] else ""))
    L.append(f"- USD-major median-of-medians: {a['usd_majors_median_of_medians_bp']} bp")
    L.append(f"- all representative pairs: median {a['all_representative_pairs_median_bp']} bp, "
             f"mean {a['all_representative_pairs_mean_bp']} bp, "
             f"range {a['all_representative_pairs_range_bp']} bp")
    L.append(f"- all pairs median-of-medians: {a['all_pairs_median_of_medians_bp']} bp\n")

    L.append("## Chained FX mean-reversion re-run\n")
    c = p.get("strategy_chain") or {}
    if c.get("state") != "RAN":
        L.append(f"- not run: `{c.get('state', 'ABSENT')}`"
                 + (f" ({c['error']})" if c.get("error") else "")
                 + "\n")
    else:
        L.append(f"- cost applied: **{c['cost_bp_round_trip']:.4f} bp** round trip")
        L.append(f"- break-even (derived from this run): **{c['break_even_bp_derived_from_run']:.4f} bp** "
                 f"(documented {c['break_even_bp_documented']} bp, drift {c['break_even_drift_bp']:+.4f})")
        L.append(f"- cost - break-even: **{c['cost_minus_break_even_bp']:+.4f} bp**")
        L.append(f"- mean gross {c['mean_gross_bp']:.4f} bp -> mean net **{c['mean_net_bp']:.4f} bp** "
                 f"(2x cost: {c['mean_net_bp_2x']:.4f} bp)")
        L.append(f"- plain CI95 net: {c['ci95_net_bp']}")
        L.append(f"- **window-clustered CI95 net: {c['ci95_net_bp_window_clustered']}** - "
                 f"includes zero: **{c['ci_window_clustered_includes_zero']}**")
        L.append(f"- n = {c['n_pair_rebalances']} pair-rebalances over {c['n_rebalance_windows']} windows")
        L.append(f"- research runner verdict at this cost: `{c['research_runner_verdict_at_cost']}` "
                 f"({c['research_runner_verdict_note']})\n")

    L.append("## Strategy decision\n")
    d = p["strategy_decision"]
    L.append(f"- **verdict written: `{d['strategy_verdict']}`**")
    L.append(f"- rule: {d['rule']}")
    if d.get("ci_caveat"):
        L.append(f"- CI caveat: {d['ci_caveat']}")
    g = d["guard"]
    L.append(f"- guard: allowlist {g['allowlist']} enforced in `{g['enforced_in']}`; "
             f"INVESTABLE reachable: **{g['investable_reachable']}** - {g['why']}\n")

    L.append("## Programme state\n")
    L.append(f"- {p['programme_tally']}")
    L.append(f"- {p['fx_meanrev_state']}")
    L.append(f"- {p['verdict_moves_by_this_tool']}\n")
    L.append("## Provenance\n")
    L.append(f"- raw samples: `{p.get('raw_samples_path') or '(none - dry run)'}`")
    L.append(f"- does not overwrite: {', '.join(p['does_not_overwrite'])}")
    L.append(f"- kept previous artifact: {p.get('kept_previous_artifact') or 'no'}")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- overlap run
def run_overlap(args) -> int:
    now = datetime.now(timezone.utc)
    pairs = [x.strip().lower() for x in args.pairs.split(",") if x.strip()]
    sess = session_state(now)
    token = os.environ.get("TIINGO_API_KEY")

    sampled = {"samples": [], "poll_count": 0, "api_unreachable": False,
               "window_start_utc": now.isoformat(), "window_end_utc": now.isoformat()}
    if args.dry_run:
        print("dry run: no network, no token required", file=sys.stderr)
    elif not sess["in_window"] and not args.ignore_session:
        print(f"off session ({sess['label']}: {sess['reason']}) - not polling; "
              "writing a BLOCKED artifact", file=sys.stderr)
    elif not token:
        print("TIINGO_API_KEY not set - not polling; writing a BLOCKED artifact",
              file=sys.stderr)
    else:
        sampled = sample_loop(pairs, token, args.interval, args.max_minutes,
                             args.until_samples, args.max_polls)

    samples = sampled["samples"]
    pair_stats: dict[str, dict] = {}
    for p in pairs:
        st = per_pair_stats(samples, p)
        st["verdict"], st["rule"] = classify(st)
        pair_stats[p] = st
    agg = aggregate(pair_stats, pairs)
    agg["decision_cost_bp"] = (None if agg["decision_cost_bp"] is None
                               else round(float(agg["decision_cost_bp"]), 6))

    # ---- status (explicit; the no-representative case is never averaged in)
    any_quote = any(pair_stats[p]["n"] > 0 for p in pairs)
    if not sess["in_window"] and not args.ignore_session:
        status, block_reason = "BLOCKED_NO_REPRESENTATIVE_SESSION", f"OFF_SESSION_{sess['label']}"
    elif args.dry_run and not samples:
        status, block_reason = "BLOCKED_NO_REPRESENTATIVE_SESSION", "DRY_RUN_NO_SAMPLES"
    elif sampled["api_unreachable"] and not any_quote:
        status, block_reason = "BLOCKED_NO_REPRESENTATIVE_SESSION", "API_UNREACHABLE"
    elif not token and not args.dry_run:
        status, block_reason = "BLOCKED_NO_REPRESENTATIVE_SESSION", "NO_TIINGO_API_KEY"
    elif agg["n_representative_pairs"] == 0:
        if not any_quote:
            status = "BLOCKED_NO_REPRESENTATIVE_SESSION"
            block_reason = ("HOLIDAY_SUSPECTED_NO_QUOTES"
                            if sess["holiday_suspected_fixed_date"] else "NO_QUOTES")
        elif agg["verdict_counts"].get("INSUFFICIENT_N", 0) == len(pairs):
            status, block_reason = "BLOCKED_NO_REPRESENTATIVE_SESSION", "INSUFFICIENT_SAMPLES"
        else:
            status, block_reason = "BLOCKED_NO_REPRESENTATIVE_SESSION", "ALL_PAIRS_FROZEN_OR_WIDE"
    else:
        status, block_reason = "MEASURED_REPRESENTATIVE", None

    # ---- chained re-run (only when there is a representative number to feed it)
    chain: dict | None = None
    if status == "MEASURED_REPRESENTATIVE" and not args.no_chain and not args.dry_run:
        try:
            chain = run_strategy_chain(agg["decision_cost_bp"], args.chain_shuffles, args.seed)
        except Exception as exc:  # noqa: BLE001 - never crash the job on the chain
            chain = {"state": "CHAIN_FAILED", "error": repr(exc)}
    elif args.no_chain:
        chain = {"state": "SKIPPED_NO_CHAIN_FLAG"}

    decision = guard_verdict(decide_strategy_verdict(status, chain))

    run_date = now.strftime("%Y%m%d")
    out_json = Path(args.out or (DECISION_OUT_DIR / f"FOREX_COST_{run_date}_overlap.json"))
    out_md = Path(args.out_md or out_json.with_suffix(".md"))

    payload = {
        "schema": "forex_cost_overlap.v1",
        "asset_class": "FOREX",
        "item": "M2-residual",
        "run_date": run_date,
        "generated_utc": now.isoformat(),
        "status": status,
        "block_reason": block_reason,
        "session": sess,
        "endpoint": ENDPOINT,
        "pairs": pairs,
        "majors": MAJORS,
        "interval_seconds": args.interval,
        "max_minutes": args.max_minutes,
        "min_samples_target": args.until_samples,
        "poll_count": sampled["poll_count"],
        "window_start_utc": sampled["window_start_utc"],
        "window_end_utc": sampled["window_end_utc"],
        "api_unreachable": sampled["api_unreachable"],
        "commission": "COMMISSION_UNKNOWN",
        "commission_note": ("Tiingo top-of-book exposes bid/ask only; a retail commission "
                            "cannot be determined from this feed and is NOT assumed zero. "
                            "Round-trip cost here is SPREAD ONLY."),
        "round_trip_definition": ("round_trip_bp = full_spread_bp = (ask-bid)/mid*1e4 "
                                  "(cross the spread on entry and on exit)"),
        "rules": RULES_DOC,
        "per_pair": pair_stats,
        "aggregate": agg,
        "strategy_chain": chain,
        "strategy_decision": decision,
        "programme_tally": "0 INVESTABLE / 8 NOT_INVESTABLE / 6 UNKNOWN",
        "fx_meanrev_state": ("FX mean-reversion remains UNKNOWN until a representative "
                             "weekday cost exists AND the window-clustered CI excludes zero"),
        "verdict_moves_by_this_tool": (
            "none by default - a blocked run changes no verdict; a measured run may write "
            "NOT_INVESTABLE or HUMAN_REVIEW_REQUIRED, never INVESTABLE, and never edits "
            "the programme tally"),
        "does_not_overwrite": [
            "reports/cost_measurement_forex/FOREX_COST_20261122.json",
            "reports/cost_measurement_forex/FOREX_COST_20261122.md",
            "reports/cost_measurement_forex/fx_top_of_book_samples.json",
            "reports/cost_measurement_forex/fx_top_of_book_samples_window2.json",
        ],
        "raw_samples_path": None,
        "kept_previous_artifact": None,
    }

    # ---- a blocked run must never clobber a good measurement
    if not args.dry_run and out_json.exists():
        try:
            prev = json.loads(out_json.read_text())
        except Exception:  # noqa: BLE001
            prev = {}
        if prev.get("status") == "MEASURED_REPRESENTATIVE" and status != "MEASURED_REPRESENTATIVE":
            stamp = now.strftime("%H%M")
            payload["kept_previous_artifact"] = str(out_json)
            out_json = out_json.with_name(f"FOREX_COST_{run_date}_overlap_blocked_{stamp}.json")
            out_md = out_json.with_suffix(".md")

    if not args.dry_run or args.out or args.out_md:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        if samples:
            raw = out_json.with_name(f"fx_overlap_samples_{now.strftime('%Y%m%dT%H%M')}Z.json")
            raw.write_text(json.dumps({
                "endpoint": ENDPOINT, "pairs": pairs,
                "window_start_utc": sampled["window_start_utc"],
                "window_end_utc": sampled["window_end_utc"],
                "interval_seconds": args.interval,
                "poll_count": sampled["poll_count"],
                "samples": samples,
            }, indent=2))
            payload["raw_samples_path"] = str(raw.relative_to(ROOT) if raw.is_relative_to(ROOT) else raw)
        out_json.write_text(json.dumps(payload, indent=2))
        out_md.write_text(render_md(payload))
        print(f"\nwrote {out_json}\nwrote {out_md}")
    else:
        print(json.dumps({k: payload[k] for k in
                          ("status", "block_reason", "session", "aggregate",
                           "strategy_decision")}, indent=2))

    # Console summary
    print(f"\n=== {status}" + (f" ({block_reason})" if block_reason else "") + " ===")
    for p in pairs:
        s = pair_stats[p]
        if s["n"]:
            print(f"{p}: n={s['n']} med={s['median']:.3f} p25={s['p25']:.3f} "
                  f"p75={s['p75']:.3f} sd={s['sd']:.3f} distinct={s['distinct_spreads']} "
                  f"max_run={s['max_identical_run']} -> {s['verdict']}")
        else:
            print(f"{p}: n=0 -> {s['verdict']}")
    print(f"decision cost: {agg['decision_cost_bp']} bp | "
          f"verdict: {decision['strategy_verdict']}")
    # Chain outcome - the failure must be visible in the Actions log, not only
    # in the committed artifact. stdout only: nothing here changes any value.
    if chain is None:
        why = ("dry run" if args.dry_run else
               f"status {status}" + (f" ({block_reason})" if block_reason else ""))
        print(f"strategy chain: NOT RUN - {why}")
    elif chain.get("state") == "RAN":
        print(f"strategy chain: RAN (cost applied "
              f"{chain.get('cost_bp_round_trip')} bp round trip)")
    else:
        print(f"WARNING: strategy chain did NOT complete: {chain.get('state')}"
              + (f" - {chain['error']}" if chain.get("error") else ""))
        print("NOTE: cost measurement is unaffected; strategy verdict requires the chain.")
    return 0


# ---------------------------------------------------------------- self test
def self_test() -> int:
    """Classifier fixtures: a frozen series is caught, a healthy one passes."""
    def series(spreads: list[float], mids: list[float] | None = None) -> list[dict]:
        out = []
        for i, sp in enumerate(spreads):
            mid = (mids[i] if mids else 1.10 + i * 1e-5)
            out.append({"pair": "eurusd", "plausible": True, "mid": mid,
                        "bid": mid - sp / 2e4 * mid, "ask": mid + sp / 2e4 * mid,
                        "full_spread_bp": sp, "local_ts": "2026-11-23T14:00:00+00:00",
                        "quote_ts": "2026-11-23T14:00:00+00:00"})
        return out

    import random
    rng = random.Random(7)
    cases = {
        "frozen_one_price": series([3.826] * 40, mids=[1.10] * 40),
        "frozen_low_distinct": series([5.0] * 37 + [5.1, 5.2, 5.3], mids=[1.10] * 40),
        "frozen_spread_jittering_mid": series([5.0] * 40),
        "wide_unstable": series([2.0 + rng.random() * 30 for _ in range(40)]),
        "healthy": series([1.2 + rng.random() * 0.6 for _ in range(40)]),
        "no_quote": [],
        "insufficient": series([1.5] * 10),
    }
    expected = {"frozen_one_price": "FROZEN", "frozen_low_distinct": "FROZEN",
                "frozen_spread_jittering_mid": "FROZEN",
                "wide_unstable": "WIDE", "healthy": "REPRESENTATIVE",
                "no_quote": "NO_QUOTE", "insufficient": "INSUFFICIENT_N"}
    bad = 0
    for name, samples in cases.items():
        st = per_pair_stats(samples, "eurusd")
        v, rule = classify(st)
        ok = v == expected[name]
        bad += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'} {name}: {v} (expected {expected[name]}) - {rule}")
    return 0 if bad == 0 else 1


# ---------------------------------------------------------------- legacy run
def run_legacy(args) -> int:
    token = os.environ.get("TIINGO_API_KEY")
    if not token:
        print("TIINGO_API_KEY not set", file=sys.stderr)
        return 2
    pairs = [p.strip().lower() for p in args.pairs.split(",") if p.strip()]
    res = sample_loop(pairs, token, args.interval, args.minutes, None, None)
    samples = res["samples"]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "endpoint": ENDPOINT,
        "pairs": pairs,
        "window_start_utc": res["window_start_utc"],
        "window_end_utc": res["window_end_utc"],
        "interval_seconds": args.interval,
        "poll_count": res["poll_count"],
        "samples": samples,
    }, indent=2))

    print("\n=== per-pair diagnostics (full spread, bp of mid) ===")
    agg: dict[str, dict] = {}
    for p in pairs:
        st = per_pair_stats(samples, p)
        if not st["n"]:
            print(f"{p}: NO PLAUSIBLE QUOTES (n_raw={st['n_raw']})")
            continue
        agg[p] = {k: st[k] for k in ("n", "min", "p25", "median", "p75", "max",
                                    "mean", "sd", "sd_pop", "distinct_spreads",
                                    "distinct_mids", "max_identical_run",
                                    "median_quote_age_s")}
        a = agg[p]
        print(f"{p}: n={a['n']} min={a['min']:.3f} med={a['median']:.3f} "
              f"max={a['max']:.3f} mean={a['mean']:.3f} sd={a['sd']:.3f} "
              f"distinct={a['distinct_spreads']}")
    summary_path = out.with_name(out.stem + "_summary.json")
    summary_path.write_text(json.dumps(agg, indent=2))
    print(f"\nwrote {out} and {summary_path}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--minutes", type=float, default=20.0)
    ap.add_argument("--interval", type=float, default=45.0)
    ap.add_argument("--out", default=None,
                    help="legacy default: reports/cost_measurement_forex/fx_top_of_book_samples.json")
    ap.add_argument("--pairs", default=",".join(PAIRS))
    ap.add_argument("--overlap", action="store_true",
                    help="representative-session mode (session-gated, classified, chained)")
    ap.add_argument("--until-samples", type=int, default=MIN_SAMPLES,
                    help="stop once every pair has this many plausible quotes")
    ap.add_argument("--max-minutes", type=float, default=12.0)
    ap.add_argument("--max-polls", type=int, default=None)
    ap.add_argument("--out-md", default="")
    ap.add_argument("--ignore-session", action="store_true",
                    help="sample even outside the overlap (diagnostics only)")
    ap.add_argument("--dry-run", action="store_true",
                    help="no network, no token; prints and (with --out) writes a BLOCKED artifact")
    ap.add_argument("--no-chain", action="store_true",
                    help="skip the FX mean-reversion re-run")
    ap.add_argument("--chain-shuffles", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.overlap:
        return run_overlap(args)
    if not args.out:
        args.out = "reports/cost_measurement_forex/fx_top_of_book_samples.json"
    return run_legacy(args)


if __name__ == "__main__":
    raise SystemExit(main())
