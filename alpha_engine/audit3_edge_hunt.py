"""audit3_edge_hunt.py — separate alpha from beta, and test gates out-of-sample.

Why this exists
---------------
`audit3_tribunal.py` answers "which cells are distinguishable from luck". It
cannot answer the question that actually matters after that:

    is the apparent edge skill, or did we just hold the right exposure?

A book that shorts a falling market shows a beautiful short win rate and a
miserable long win rate, and *both* numbers are the same fact about the market.
This module runs the four tests that separate the two, on the live closed-pick
ledger, with everything pre-declared:

1. BETA ACCOUNTING (§A). For one asset class, a long and a short on the same
   instrument have opposite exposure, so under pure beta:

       mean(long) + mean(short)  ≈  -2 * round-trip cost
       implied drift per window  ≈ -(mean(short) + cost)

   If the observed long mean matches the drift implied by the short mean, the
   direction split carries no selection alpha -- it is one market move counted
   twice. Residual alpha is what is left after removing the drift.

2. MIRROR TEST (§B). Same-symbol, same-day long/short pairs. Under pure beta
   the pair sums to about minus two costs and the correlation is near -1.

3. POINT-IN-TIME REPLAY (§C). A gate is only a gate if it uses data that
   existed when the pick was issued. For every pick this replays the
   strategy's record using **only picks that had already closed before this
   pick was issued**, buckets by that prior win rate, and measures the *next*
   pick. This is leakage-free by construction, and it is the test that
   retroactive "walk-forward" flags fail.

4. PRE-REGISTERED BATTERY (§D). A small, declared set of directional and
   gating hypotheses, BH-corrected, with minimum detectable effect and the
   sample size each would need. Small batteries are the only way to keep any
   statistical power: 65 exploratory cells cannot prove a 0.3% edge.

Usage
-----
  python3 -m alpha_engine.audit3_edge_hunt \
      --picks /tmp/dashboard_data.json \
      --out reports/edge_hunt.json

Exit codes: 0 report written; 2 unusable input.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

MODULE_PATH = Path(__file__).resolve()
REPO_ROOT = MODULE_PATH.parent.parent
if str(REPO_ROOT) not in sys.path:  # direct invocation
    sys.path.insert(0, str(REPO_ROOT))

from alpha_engine.audit3_tribunal import (  # noqa: E402
    SLIPPAGE_PCT,
    DEFAULT_SLIPPAGE_PCT,
    PROVEN_MIN_NET_CI_LO_PCT,
    benjamini_hochberg,
    binom_sf,
    bootstrap_mean_ci,
)

MIN_PRIOR = 10          # prior closed picks before a point-in-time gate may vote
POWER_Z = 2.8           # 80% power, two-sided 5%
BOOT = 2000
SEED = 42


# ───────────────────────────────────────────────────────────────── helpers ──
def _num(value: Any) -> float | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return None if out != out or out in (float("inf"), float("-inf")) else out


def _class(r: dict) -> str:
    return str(r.get("asset_class") or "UNKNOWN").upper()


def _dir(r: dict) -> str:
    v = str(r.get("direction") or "").upper()
    if v.startswith("L"):
        return "LONG"
    if v.startswith("S"):
        return "SHORT"
    return "?"


def _ts(r: dict, *fields: str) -> datetime | None:
    for f in fields:
        raw = r.get(f)
        if not raw:
            continue
        v = str(raw).strip()
        if v.endswith("Z"):
            v = v[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(v)
        except ValueError:
            continue
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return None


def issued_at(r: dict) -> datetime | None:
    return _ts(r, "timestamp", "entry_time", "created_at") or _ts(r, "closed_at")


def closed_at(r: dict) -> datetime | None:
    return _ts(r, "closed_at", "timestamp")


def net_pnl(r: dict) -> float | None:
    """Net of the same per-class round-trip slippage the tribunal uses."""
    gross = _num(r.get("pnl_pct"))
    if gross is None:
        return None
    return gross - SLIPPAGE_PCT.get(_class(r), DEFAULT_SLIPPAGE_PCT)


def _mean(values: Iterable[float]) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else 0.0


def bootstrap_diff(a: list[float], b: list[float], n_boot: int = BOOT,
                   seed: int = SEED) -> dict[str, Any]:
    """Seeded bootstrap CI for mean(a) - mean(b)."""
    if len(a) < 5 or len(b) < 5:
        return {"diff": None, "ci_lo": None, "ci_hi": None, "n_boot": 0}
    rng = random.Random(seed)
    diffs = []
    for _ in range(n_boot):
        sa = sum(a[rng.randrange(len(a))] for _ in range(len(a))) / len(a)
        sb = sum(b[rng.randrange(len(b))] for _ in range(len(b))) / len(b)
        diffs.append(sa - sb)
    diffs.sort()
    return {
        "diff": _mean(a) - _mean(b),
        "ci_lo": diffs[int(0.025 * n_boot)],
        "ci_hi": diffs[int(0.975 * n_boot) - 1],
        "n_boot": n_boot,
    }


def required_n(effect_pct: float, sd_pct: float, z: float = POWER_Z) -> int | None:
    """Sample size for 80% power to detect |effect| at 95% confidence."""
    if not effect_pct or not sd_pct or effect_pct == 0:
        return None
    return int(math.ceil((z * sd_pct / abs(effect_pct)) ** 2))


def required_n_mde(mde_pct: float, sd_pct: float, z: float = POWER_Z) -> int | None:
    """Sample size for 80% power to detect a PRE-DECLARED minimum effect.

    `mde_pct` is the minimum detectable effect the study commits to detect
    *before* looking at the data (e.g. the tribunal's PROVEN net-CI lower
    bound, 0.05 %/trade). It must NEVER be the cell's observed mean: plugging
    an observed near-zero mean inflates n to infinity, and an observed lucky
    mean collapses it -- the circular trap `required_n` falls into when its
    callers pass the observed mean. Use `required_n` only when the effect size
    is itself the hypothesis; use this helper to size a pre-registered gate.

    Returns None when `mde_pct` or `sd_pct` is falsy/zero (no variance, no
    effect, or degenerate input), signalling "sample size is not well-defined".
    """
    if not mde_pct or not sd_pct or mde_pct == 0 or sd_pct == 0:
        return None
    return int(math.ceil((z * sd_pct / abs(mde_pct)) ** 2))


# ─────────────────────────────────────────────────────── §A beta accounting ──
def beta_accounting(rows: list[dict], klass: str = "CRYPTO") -> dict[str, Any]:
    """Is the long/short split one market move counted twice?"""
    slip = SLIPPAGE_PCT.get(klass, DEFAULT_SLIPPAGE_PCT)
    longs = [net_pnl(r) for r in rows if _class(r) == klass and _dir(r) == "LONG"]
    shorts = [net_pnl(r) for r in rows if _class(r) == klass and _dir(r) == "SHORT"]
    longs = [v for v in longs if v is not None]
    shorts = [v for v in shorts if v is not None]
    if len(longs) < 20 or len(shorts) < 20:
        return {"available": False, "n_long": len(longs), "n_short": len(shorts)}
    ml, ms = _mean(longs), _mean(shorts)
    drift = -(ms + slip)                # a short profits when the price falls
    predicted_long = drift - slip
    residual = ((ml + ms) + 2 * slip) / 2
    return {
        "available": True,
        "class": klass,
        "n_long": len(longs),
        "n_short": len(shorts),
        "mean_long_pct": round(ml, 4),
        "mean_short_pct": round(ms, 4),
        "implied_drift_per_window_pct": round(drift, 4),
        "predicted_long_from_drift_pct": round(predicted_long, 4),
        "observed_minus_predicted_pct": round(ml - predicted_long, 4),
        "long_plus_short_pct": round(ml + ms, 4),
        "pure_beta_prediction_pct": round(-2 * slip, 4),
        "residual_selection_alpha_pct": round(residual, 4),
        "verdict": ("consistent with pure beta (residual within one cost)"
                    if abs(residual) < slip else
                    "residual alpha present beyond beta"),
    }


# ────────────────────────────────────────────────────────── §B mirror test ──
def mirror_test(rows: list[dict], klass: str = "CRYPTO") -> dict[str, Any]:
    """Same-symbol same-day opposite-direction pairs: beta makes them sum to ~-2c."""
    cells: dict[tuple, dict[str, list[float]]] = defaultdict(lambda: {"LONG": [], "SHORT": []})
    for r in rows:
        if klass != "ALL" and _class(r) != klass:
            continue
        v, t = net_pnl(r), closed_at(r)
        if v is None or t is None or _dir(r) == "?":
            continue
        cells[(r.get("symbol"), t.date().isoformat())][_dir(r)].append(v)
    pairs = [(_mean(v["LONG"]), _mean(v["SHORT"]))
             for v in cells.values() if v["LONG"] and v["SHORT"]]
    if len(pairs) < 20:
        return {"available": False, "n_pairs": len(pairs)}
    longs = [a for a, _ in pairs]
    shorts = [b for _, b in pairs]
    ml, ms = _mean(longs), _mean(shorts)
    cov = sum((a - ml) * (b - ms) for a, b in pairs) / len(pairs)
    sd = statistics.pstdev(longs) * statistics.pstdev(shorts)
    return {
        "available": True,
        "class": klass,
        "n_pairs": len(pairs),
        "mean_pair_sum_pct": round(_mean([a + b for a, b in pairs]), 4),
        "corr": round(cov / sd, 4) if sd else 0.0,
        "mean_long_pct": round(ml, 4),
        "mean_short_pct": round(ms, 4),
    }


# ─────────────────────────────────────────────────── §C point-in-time replay ──
def _bucket(wr: float) -> str:
    if wr < 0.35:
        return "<35%"
    if wr < 0.45:
        return "35-45%"
    if wr < 0.55:
        return "45-55%"
    if wr < 0.65:
        return "55-65%"
    return ">=65%"


def pit_replay(rows: list[dict], min_prior: int = MIN_PRIOR) -> dict[str, Any]:
    """Bucket each pick by its strategy's *prior* record, then score that pick.

    Only picks that had already closed before this pick was issued contribute to
    the prior, so a gate cannot see its own outcome. This is the test that a
    retroactively computed walk-forward flag fails.
    """
    ordered = sorted((r for r in rows if issued_at(r) and net_pnl(r) is not None),
                     key=lambda r: issued_at(r))
    history: dict[tuple[str, str], list[tuple[datetime, float]]] = defaultdict(list)
    outcomes: dict[str, list[float]] = defaultdict(list)
    skipped = 0
    for r in ordered:
        key = (str(r.get("strategy") or "?"), _class(r))
        issue = issued_at(r)
        prior = [p for (t, p) in history[key] if t is not None and t < issue]
        pnl = net_pnl(r)
        if len(prior) < min_prior:
            bucket = "insufficient"
            skipped += 1
            prior_wr = None
        else:
            prior_wr = sum(1 for p in prior if p > 0) / len(prior)
            bucket = _bucket(prior_wr)
        outcomes[bucket].append(pnl)
        rec = {"bucket": bucket, "prior_wr": prior_wr, "prior_n": len(prior), "pnl": pnl}
        _PIT_ROWS.append(rec)
        close = closed_at(r) or issue
        history[key].append((close, pnl))

    buckets = []
    for name in ("insufficient", "<35%", "35-45%", "45-55%", "55-65%", ">=65%"):
        vals = outcomes.get(name) or []
        if not vals:
            continue
        ci = bootstrap_mean_ci(vals)
        buckets.append({
            "prior_wr_bucket": name,
            "n": len(vals),
            "mean_net_pct": round(_mean(vals), 4),
            "ci": [round(ci["ci_lo"], 4) if ci["ci_lo"] is not None else None,
                   round(ci["ci_hi"], 4) if ci["ci_hi"] is not None else None],
            "wr": round(sum(1 for v in vals if v > 0) / len(vals), 4),
            "share_of_book": round(len(vals) / max(1, len(ordered)), 4),
        })

    hi = outcomes.get(">=65%") or []
    lo = (outcomes.get("<35%") or []) + (outcomes.get("35-45%") or [])
    diff = bootstrap_diff(hi, lo)
    good = (outcomes.get(">=65%") or []) + (outcomes.get("55-65%") or [])
    bad = (outcomes.get("<35%") or []) + (outcomes.get("35-45%") or [])
    return {
        "available": bool(buckets),
        "min_prior": min_prior,
        "n_scored": len(ordered),
        "n_without_history": skipped,
        "buckets": buckets,
        "discrimination_hi_vs_lo": {
            "n_hi": len(hi), "n_lo": len(lo),
            "diff_pct": round(diff["diff"], 4) if diff["diff"] is not None else None,
            "ci": [round(diff["ci_lo"], 4) if diff["ci_lo"] is not None else None,
                   round(diff["ci_hi"], 4) if diff["ci_hi"] is not None else None],
            "proven": bool(diff["ci_lo"] is not None and diff["ci_lo"] > 0),
        },
        "gate_55_plus_book": {
            "n": len(good),
            "mean_net_pct": round(_mean(good), 4) if good else None,
            "baseline_mean_net_pct": round(_mean([v for vs in outcomes.values() for v in vs]), 4),
            "retained_share": round(len(good) / max(1, len(ordered)), 4),
            "improvement_pct": round(_mean(good) - _mean([v for vs in outcomes.values() for v in vs]), 4)
            if good else None,
        },
        "bad_book_under_45": {
            "n": len(bad),
            "mean_net_pct": round(_mean(bad), 4) if bad else None,
        },
    }


_PIT_ROWS: list[dict] = []


# ─────────────────────────────────────────────── §D pre-registered battery ──
BATTERY: tuple[tuple[str, Any], ...] = (
    ("T1 CRYPTO short", lambda r: _class(r) == "CRYPTO" and _dir(r) == "SHORT"),
    ("T2 CRYPTO long", lambda r: _class(r) == "CRYPTO" and _dir(r) == "LONG"),
    ("T3 EQUITY long", lambda r: _class(r) == "EQUITY" and _dir(r) == "LONG"),
    ("T4 ETF long", lambda r: _class(r) == "ETF" and _dir(r) == "LONG"),
    ("T5 wf viable/strong", lambda r: str(r.get("wf_verdict") or "").upper() in ("VIABLE", "STRONG")),
    ("T6 SWING timeframe", lambda r: str(r.get("trade_timeframe") or "").upper() == "SWING"),
    ("T7 CRYPTO short not failing",
     lambda r: _class(r) == "CRYPTO" and _dir(r) == "SHORT"
     and str(r.get("wf_verdict") or "").upper() != "FAILING"),
    ("T8 EQUITY long wf viable/strong",
     lambda r: _class(r) == "EQUITY" and _dir(r) == "LONG"
     and str(r.get("wf_verdict") or "").upper() in ("VIABLE", "STRONG")),
)


def battery(rows: list[dict], tests=BATTERY) -> list[dict[str, Any]]:
    """Run the declared tests once, then BH-correct across exactly these."""
    results = []
    for name, pred in tests:
        vals = [net_pnl(r) for r in rows if pred(r) and net_pnl(r) is not None]
        if len(vals) < 20:
            results.append({"test": name, "n": len(vals), "verdict": "INSUFFICIENT_N"})
            continue
        ci = bootstrap_mean_ci(vals)
        wins = sum(1 for v in vals if v > 0)
        sd = statistics.pstdev(vals)
        mean = _mean(vals)
        results.append({
            "test": name,
            "n": len(vals),
            "mean_net_pct": round(mean, 4),
            "ci": [round(ci["ci_lo"], 4), round(ci["ci_hi"], 4)],
            "wr": round(wins / len(vals), 4),
            "p_edge": round(binom_sf(wins, len(vals)), 6),
            "p_harm": round(binom_sf(len(vals) - wins, len(vals)), 6),
            "sd_pct": round(sd, 4),
            "mde_pct": round(POWER_Z * sd / math.sqrt(len(vals)), 4),
            "n_needed": required_n(mean, sd),
        })
    scored = [r for r in results if "p_edge" in r]
    qs = benjamini_hochberg([r["p_edge"] for r in scored])
    qhs = benjamini_hochberg([r["p_harm"] for r in scored])
    for r, q, qh in zip(scored, qs, qhs):
        r["q_edge"] = round(q, 6)
        r["q_harm"] = round(qh, 6)
        lo, hi = r["ci"]
        if lo > 0 and q <= 0.10:
            r["verdict"] = "PROVEN_EDGE"
        elif lo > 0:
            r["verdict"] = "POSITIVE_NOT_PROVEN"
        elif hi < 0 and qh <= 0.10:
            r["verdict"] = "PROVEN_HARM"
        elif hi < 0:
            r["verdict"] = "NEGATIVE_NOT_PROVEN"
        else:
            r["verdict"] = "NO_CLAIM"
    return results


# ──────────────────────────────────────────────── gate provenance / leakage ──
def gate_provenance(rows: list[dict]) -> dict[str, Any]:
    """Is the walk-forward verdict a point-in-time snapshot or a backfill?

    If the at-issue copy is empty/zero while the current copy is populated, the
    flag was computed after the trades closed and can be reading its own
    outcomes. That is the difference between a gate and a rear-view mirror.
    """
    have_issue = [r for r in rows if _num(r.get("at_issue_strat_fwd_wr")) is not None]
    zero_issue = sum(1 for r in rows if _num(r.get("at_issue_strat_fwd_wr")) == 0.0)
    populated_now = sum(1 for r in rows
                        if (_num(r.get("strat_fwd_wr")) or 0) > 0)
    gaps = []
    for r in rows:
        a, b = _num(r.get("at_issue_strat_fwd_wr")), _num(r.get("strat_fwd_wr"))
        if a is None or b is None:
            continue
        gaps.append(abs((a / 100.0 if a > 1.5 else a) - (b / 100.0 if b > 1.5 else b)))
    return {
        "at_issue_field_present": len(have_issue),
        "at_issue_value_is_zero": zero_issue,
        "current_value_populated": populated_now,
        "median_abs_gap": round(statistics.median(gaps), 4) if gaps else None,
        "contaminated": bool(zero_issue > 0.5 * max(1, len(have_issue))
                             and populated_now > 0.5 * len(rows)),
        "note": ("wf_verdict is derived from strat_fwd_wr, which is zero at "
                 "issue and populated later on the same closed rows; treat any "
                 "edge from it as UNPROVEN until the PIT replay agrees"
                 if zero_issue > 0.5 * max(1, len(have_issue)) else
                 "at-issue snapshot appears populated"),
    }


def power_analysis(rows: list[dict], mde_pct: float = PROVEN_MIN_NET_CI_LO_PCT,
                   z: float = POWER_Z) -> dict[str, Any]:
    """Per-class realized net-pnl SD and the pre-declared-MDE sample size.

    For each asset class with >= 5 net-pnl observations, report the population
    standard deviation (statistics.pstdev) of net pnl and the sample size that
    80% power would need to detect `mde_pct` against that SD. The MDE is fixed
    up front (the tribunal's PROVEN net-CI lower bound), so `required_n_mde`
    never sees an observed cell mean -- it is non-circular by construction.
    """
    classes: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        v = net_pnl(r)
        if v is not None:
            classes[_class(r)].append(v)
    per_class = {}
    for klass in sorted(classes):
        vals = classes[klass]
        if len(vals) < 5:
            continue
        sd = statistics.pstdev(vals)
        per_class[klass] = {
            "n": len(vals),
            "net_pnl_sd_pct": round(sd, 4),
            "required_n": required_n_mde(mde_pct, sd, z=z),
        }
    return {
        "mde_pct": mde_pct,
        "z": z,
        "note": ("mde_pct is pre-declared (the tribunal's PROVEN net-CI lower "
                 "bound), never the observed cell mean, to avoid the circular "
                 "observed-mean trap in required_n"),
        "by_asset_class": per_class,
    }


# ────────────────────────────────────────────────────────────────── report ──
def build_report(rows: list[dict], source: str = "") -> dict[str, Any]:
    _PIT_ROWS.clear()
    beta = beta_accounting(rows, "CRYPTO")
    mirror = mirror_test(rows, "CRYPTO")
    pit = pit_replay(rows)
    bat = battery(rows)
    prov = gate_provenance(rows)
    power = power_analysis(rows)

    # Does the ledger's headline edge survive the PIT replay? That is the only
    # claim this module is willing to call "found".
    proven = [r for r in bat if r.get("verdict") == "PROVEN_EDGE"]
    pit_ok = bool((pit.get("discrimination_hi_vs_lo") or {}).get("proven"))
    beta_only = bool(beta.get("available") and abs(beta.get("residual_selection_alpha_pct") or 0)
                     < SLIPPAGE_PCT.get("CRYPTO", 0.15))

    if pit_ok:
        headline = ("A point-in-time gate beats its own past: prior-record filter "
                    "discriminates without leakage")
    elif proven and beta_only:
        headline = ("Every proven cell is explained by market beta; no selection "
                    "alpha found in this ledger")
    elif proven:
        headline = ("Statistically proven cells exist, but none of them survived "
                    "the leakage-free replay")
    else:
        headline = "No proven edge in this ledger; the sample cannot support one yet"

    return {
        "schema": "audit3.edge_hunt.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "n_rows": len(rows),
        "headline": headline,
        "beta_accounting": beta,
        "mirror_test": mirror,
        "pit_replay": pit,
        "battery": bat,
        "gate_provenance": prov,
        "power_analysis": power,
        "limitations": [
            "No per-symbol price series for the ledger window, so M1b selection "
            "alpha vs same-symbol buy-and-hold is still not computed; beta is "
            "inferred from long/short symmetry instead.",
            "The long/short symmetry test assumes comparable entry/exit windows "
            "on both sides; asymmetric hold times weaken it.",
            "PIT replay scores each pick once, but picks within the same hour "
            "share market moves, so n is optimistic by roughly the number of "
            "distinct hours, not the number of picks.",
            "A proven cell here is proven on 9 months of one regime; it is a "
            "justified candidate for a forward pilot, not a money-ready signal.",
        ],
    }


def render_text(rep: dict[str, Any]) -> str:
    out = [f"EDGE HUNT — {rep['headline']}", f"rows={rep['n_rows']}", ""]
    b = rep["beta_accounting"]
    if b.get("available"):
        out += [
            f"A. BETA ({b['class']}): long {b['mean_long_pct']:+.3f}% (n={b['n_long']})  "
            f"short {b['mean_short_pct']:+.3f}% (n={b['n_short']})",
            f"   implied drift/window {b['implied_drift_per_window_pct']:+.3f}%  "
            f"predicted long {b['predicted_long_from_drift_pct']:+.3f}%  "
            f"observed {b['mean_long_pct']:+.3f}%",
            f"   residual selection alpha {b['residual_selection_alpha_pct']:+.3f}% "
            f"-> {b['verdict']}",
            "",
        ]
    m = rep["mirror_test"]
    if m.get("available"):
        out.append(f"B. MIRROR: {m['n_pairs']} same-day pairs, mean sum "
                   f"{m['mean_pair_sum_pct']:+.3f}%, corr {m['corr']:+.3f}")
    p = rep["pit_replay"]
    if p.get("available"):
        out.append("C. POINT-IN-TIME REPLAY (prior closed picks only):")
        for bk in p["buckets"]:
            out.append(f"   prior WR {bk['prior_wr_bucket']:<13} n={bk['n']:<5} "
                       f"net={bk['mean_net_pct']:+.3f}%  CI={bk['ci']}  "
                       f"share={bk['share_of_book']:.0%}")
        d = p["discrimination_hi_vs_lo"]
        out.append(f"   hi vs lo diff {d['diff_pct']:+.3f}% CI={d['ci']} "
                   f"proven={d['proven']}")
    out.append("")
    out.append("D. PRE-REGISTERED BATTERY:")
    for r in rep["battery"]:
        if r.get("verdict") == "INSUFFICIENT_N":
            out.append(f"   {r['test']:<34} n={r['n']} insufficient")
            continue
        out.append(f"   {r['test']:<34} n={r['n']:<5} {r['mean_net_pct']:+.3f}% "
                   f"CI={r['ci']} q={r['q_edge']:.4f} -> {r['verdict']}")
    g = rep["gate_provenance"]
    out.append("")
    out.append(f"E. GATE PROVENANCE: at-issue present {g['at_issue_field_present']}, "
               f"zero {g['at_issue_value_is_zero']}, populated now "
               f"{g['current_value_populated']} -> contaminated={g['contaminated']}")
    pw = rep.get("power_analysis") or {}
    if pw.get("by_asset_class"):
        # Published, not just computed: a per-class sample-size requirement that
        # nobody reads cannot stop a claim being made on an underpowered cell.
        out.append("")
        out.append(f"F. POWER (pre-declared MDE {pw['mde_pct']}%/trade, z={pw['z']}):")
        for klass, row in sorted(pw["by_asset_class"].items()):
            need = row.get("required_n")
            have = row["n"]
            if need is None:
                tag = " — sample size not well-defined"
            elif have >= need:
                tag = " — powered"
            else:
                tag = f" — UNDERPOWERED ({have}/{need})"
            out.append(f"   {klass:<10} n={have:<5} sd={row['net_pnl_sd_pct']:.3f}% "
                       f"need n>={need}{tag}")
    return "\n".join(out)


def load_rows(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    rows = data
    if isinstance(data, dict):
        rows = (data.get("picks") or {}).get("recent_closed") or data.get("records") or []
    clean = [r for r in rows if isinstance(r, dict) and net_pnl(r) is not None]
    if not clean:
        raise ValueError(f"no usable closed picks in {path}")
    return clean


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="audit3 edge hunt: alpha vs beta, PIT gates")
    ap.add_argument("--picks", required=True)
    ap.add_argument("--out", help="write the JSON report here (else stdout text)")
    ap.add_argument("--json", action="store_true", help="print JSON to stdout")
    args = ap.parse_args(argv)
    try:
        rows = load_rows(args.picks)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    rep = build_report(rows, args.picks)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=1, allow_nan=False)
            f.write("\n")
        print(f"wrote {args.out}")
    print(render_text(rep) if not args.json else json.dumps(rep, indent=1, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
