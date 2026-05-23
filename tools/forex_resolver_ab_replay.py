#!/usr/bin/env python3
"""FOREX resolver A/B replay tool — panel-renegotiated thresholds (2026-04-29).

Action item #3 from `reports/PANEL_REVIEW_2026_04_29_OPERATION_PHENOMENAL_FOLLOWUPS.md`.

Read-only analysis tool: filters FOREX picks from dashboard data, replays the current
resolver (Sub-A) against an alternative |pnl| >= 5bp noise threshold (Sub-B), then
scores against renegotiated panel thresholds:

    Overall PF (Sub-B)        >= 1.5
    Overall Sharpe lift       >= +0.5  (Sub-B - Sub-A, daily-trade approx)
    Non-JPY PF (Sub-B)        >= 5.0   (preserved from original spec)
    JPY PF (Sub-B)            >= 1.0   (NEW; can't go below break-even)
    Each sub-book n           >= 30

If the JPY sub-book PF drops below 1.0 even when overall + non-JPY pass, the A/B is
REJECTED. (Panel: don't let strong non-JPY mask a weak JPY collapse.)

Stdlib only. Does NOT modify any production code or env flags.

Usage:
    py -3 tools/forex_resolver_ab_replay.py
    py -3 tools/forex_resolver_ab_replay.py --start-date 2026-03-01 --end-date 2026-04-29
    py -3 tools/forex_resolver_ab_replay.py --noise-bps 5 --output reports/my_ab.md
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

# ----------------------------------------------------------------------------
# Constants — panel-renegotiated acceptance criteria (2026-04-29)
# ----------------------------------------------------------------------------
ACCEPT_OVERALL_PF = 1.5
ACCEPT_OVERALL_SHARPE_LIFT = 0.5
ACCEPT_NON_JPY_PF = 5.0
ACCEPT_JPY_PF = 1.0
ACCEPT_MIN_N = 30

# Annualization for daily-trade Sharpe approximation.
TRADING_DAYS = 252

# pnl_pct in dashboard_data.json is stored in PERCENT units (0.30 = 0.30%, i.e. 30bp).
# 1bp = 0.01 (in pnl_pct units). So 5bp = 0.05.
PCT_PER_BP = 0.01

DEFAULT_PICKS_SOURCE = "audit_dashboard/data/dashboard_data.json"
DEFAULT_ASSET_CLASS = "FOREX"
DEFAULT_START_DATE = "2026-02-01"
DEFAULT_NOISE_BPS = 5

REPO_ROOT = Path(__file__).resolve().parent.parent


# ----------------------------------------------------------------------------
# Pick filtering
# ----------------------------------------------------------------------------

def load_recent_closed(picks_source: Path) -> list[dict]:
    """Load picks.recent_closed list from dashboard_data.json."""
    with picks_source.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("picks", {}).get("recent_closed", []) or []


def is_jpy_pair(symbol: str) -> bool:
    """Return True if the FOREX symbol is a JPY-pair.

    Matches symbols ending with `JPY=X` (yfinance form) or any symbol containing
    the `JPY` substring (covers JPYUSD, USDJPY, etc.). Returns False for empty.
    """
    if not symbol:
        return False
    return "JPY" in symbol.upper()


def parse_pick_date(pick: dict) -> date | None:
    """Best-effort ISO date parse from `closed_at`, then `timestamp`, then `entry_time`."""
    for key in ("closed_at", "timestamp", "entry_time"):
        raw = pick.get(key)
        if not raw or not isinstance(raw, str):
            continue
        # Try YYYY-MM-DD slice first (works for ISO-8601 + bare-date forms).
        head = raw[:10]
        try:
            return date.fromisoformat(head)
        except ValueError:
            continue
    return None


def filter_picks(
    picks: Iterable[dict],
    asset_class: str,
    start: date,
    end: date,
) -> list[dict]:
    """Filter to asset_class within [start, end] with valid pnl_pct + direction."""
    out = []
    for p in picks:
        if (p.get("asset_class") or "").upper() != asset_class.upper():
            continue
        pnl = p.get("pnl_pct")
        if not isinstance(pnl, (int, float)):
            continue
        if not isinstance(p.get("direction"), str):
            continue
        d = parse_pick_date(p)
        if d is None or d < start or d > end:
            continue
        out.append(p)
    return out


# ----------------------------------------------------------------------------
# Stat computation
# ----------------------------------------------------------------------------

def compute_stats(pnls: list[float]) -> dict:
    """Compute n, WR, sum, mean, std, gross_win, gross_loss, PF, Sharpe.

    Empty input returns zeros. Single-sample input returns std=0 and Sharpe=0
    (Sharpe is mean/std * sqrt(252) but std=0 → return 0 to avoid div-by-zero).
    """
    n = len(pnls)
    if n == 0:
        return {
            "n": 0,
            "wr_pct": 0.0,
            "sum_pnl_pct": 0.0,
            "mean_pnl_pct": 0.0,
            "std_pnl_pct": 0.0,
            "gross_win": 0.0,
            "gross_loss": 0.0,
            "pf": 0.0,
            "sharpe": 0.0,
        }
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]
    gross_win = sum(wins)
    gross_loss = sum(losses)  # negative
    total = sum(pnls)
    mean_v = total / n
    if n >= 2:
        std_v = statistics.pstdev(pnls)
    else:
        std_v = 0.0
    if abs(gross_loss) > 1e-12:
        pf = gross_win / abs(gross_loss)
    elif gross_win > 0:
        pf = float("inf")
    else:
        pf = 0.0
    if std_v > 1e-12:
        sharpe = (mean_v / std_v) * math.sqrt(TRADING_DAYS)
    else:
        sharpe = 0.0
    wr_pct = 100.0 * len(wins) / n
    return {
        "n": n,
        "wr_pct": wr_pct,
        "sum_pnl_pct": total,
        "mean_pnl_pct": mean_v,
        "std_pnl_pct": std_v,
        "gross_win": gross_win,
        "gross_loss": gross_loss,
        "pf": pf,
        "sharpe": sharpe,
    }


def split_cohorts(picks: list[dict]) -> dict[str, list[dict]]:
    """Split into overall / jpy / non_jpy cohorts."""
    return {
        "overall": list(picks),
        "jpy": [p for p in picks if is_jpy_pair(p.get("symbol") or "")],
        "non_jpy": [p for p in picks if not is_jpy_pair(p.get("symbol") or "")],
    }


def apply_noise_filter(picks: list[dict], noise_threshold_pct: float) -> list[dict]:
    """Sub-B: drop picks with |pnl_pct| < threshold (treated as noise/no edge)."""
    return [p for p in picks if abs(p.get("pnl_pct") or 0.0) >= noise_threshold_pct]


def cohort_stats(picks: list[dict]) -> dict:
    pnls = [float(p.get("pnl_pct") or 0.0) for p in picks]
    return compute_stats(pnls)


# ----------------------------------------------------------------------------
# Acceptance criteria
# ----------------------------------------------------------------------------

def _safe_finite(x: float) -> float:
    """Treat +inf as a very large finite number for comparison purposes only.

    A PF of inf (no losses) trivially exceeds any threshold; we keep the report
    text faithful but pass the threshold check.
    """
    if math.isinf(x):
        return float("1e18") if x > 0 else float("-1e18")
    return x


def evaluate_acceptance(
    sub_a: dict[str, dict],
    sub_b: dict[str, dict],
) -> dict:
    """Apply renegotiated panel thresholds. Return per-sub-book + overall verdicts.

    Per-sub-book verdict:
      - INSUFFICIENT_SAMPLE if Sub-B n < ACCEPT_MIN_N
      - ACCEPTED if its PF threshold met
      - REJECTED otherwise
    Overall verdict (panel rule):
      - ACCEPTED iff overall, non_jpy, jpy all ACCEPTED AND
        overall Sharpe lift (Sub-B - Sub-A) >= +0.5
      - REJECTED if any sub-book REJECTED (JPY collapse cannot be masked)
      - INSUFFICIENT_SAMPLE if any sub-book INSUFFICIENT and none REJECTED
    """
    pf_thresholds = {
        "overall": ACCEPT_OVERALL_PF,
        "non_jpy": ACCEPT_NON_JPY_PF,
        "jpy": ACCEPT_JPY_PF,
    }

    per_cohort: dict[str, dict] = {}
    for cohort, threshold in pf_thresholds.items():
        n_b = sub_b[cohort]["n"]
        pf_b = sub_b[cohort]["pf"]
        if n_b < ACCEPT_MIN_N:
            verdict = "INSUFFICIENT_SAMPLE"
            reason = f"Sub-B n={n_b} < {ACCEPT_MIN_N}"
        elif _safe_finite(pf_b) >= threshold:
            verdict = "ACCEPTED"
            reason = f"PF={pf_b:.3f} >= {threshold}"
        else:
            verdict = "REJECTED"
            reason = f"PF={pf_b:.3f} < {threshold}"
        per_cohort[cohort] = {"verdict": verdict, "reason": reason, "threshold": threshold}

    sharpe_lift = sub_b["overall"]["sharpe"] - sub_a["overall"]["sharpe"]
    sharpe_pass = sharpe_lift >= ACCEPT_OVERALL_SHARPE_LIFT

    # Compose overall verdict per panel rule.
    cohort_verdicts = [per_cohort[c]["verdict"] for c in ("overall", "non_jpy", "jpy")]
    if "REJECTED" in cohort_verdicts or not sharpe_pass:
        overall_verdict = "REJECTED"
        if "REJECTED" in cohort_verdicts:
            failing = [c for c in ("overall", "non_jpy", "jpy") if per_cohort[c]["verdict"] == "REJECTED"]
            overall_reason = f"sub-book(s) REJECTED: {', '.join(failing)}"
        else:
            overall_reason = (
                f"Sharpe lift {sharpe_lift:+.3f} < +{ACCEPT_OVERALL_SHARPE_LIFT}"
            )
    elif "INSUFFICIENT_SAMPLE" in cohort_verdicts:
        overall_verdict = "INSUFFICIENT_SAMPLE"
        failing = [c for c in ("overall", "non_jpy", "jpy") if per_cohort[c]["verdict"] == "INSUFFICIENT_SAMPLE"]
        overall_reason = f"sub-book(s) under sample minimum: {', '.join(failing)}"
    else:
        overall_verdict = "ACCEPTED"
        overall_reason = "all sub-books pass + Sharpe lift target met"

    return {
        "per_cohort": per_cohort,
        "sharpe_lift": sharpe_lift,
        "sharpe_pass": sharpe_pass,
        "overall_verdict": overall_verdict,
        "overall_reason": overall_reason,
    }


# ----------------------------------------------------------------------------
# Top-symbol drag (for Sub-A diagnostic)
# ----------------------------------------------------------------------------

def top_negative_symbols(picks: list[dict], top_k: int = 5) -> list[tuple[str, int, float]]:
    """Return [(symbol, n, sum_pnl_pct), ...] for the top-K most negative-sum symbols."""
    by_sym: dict[str, list[float]] = {}
    for p in picks:
        sym = p.get("symbol") or "?"
        pnl = p.get("pnl_pct")
        if not isinstance(pnl, (int, float)):
            continue
        by_sym.setdefault(sym, []).append(float(pnl))
    rows = [(sym, len(vs), sum(vs)) for sym, vs in by_sym.items()]
    rows.sort(key=lambda r: r[2])  # most negative first
    return rows[:top_k]


# ----------------------------------------------------------------------------
# Markdown report
# ----------------------------------------------------------------------------

def _fmt_pf(pf: float) -> str:
    if math.isinf(pf):
        return "inf"
    if math.isnan(pf):
        return "nan"
    return f"{pf:.3f}"


def _fmt_sharpe(s: float) -> str:
    if math.isinf(s) or math.isnan(s):
        return "n/a"
    return f"{s:.3f}"


def _check(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def render_report(
    *,
    start: date,
    end: date,
    noise_bps: int,
    total_n: int,
    after_noise_n: int,
    sub_a: dict[str, dict],
    sub_b: dict[str, dict],
    accept: dict,
    sub_a_picks: list[dict],
) -> str:
    cohorts_in_order = ("overall", "non_jpy", "jpy")
    pf_thresholds = {
        "overall": ACCEPT_OVERALL_PF,
        "non_jpy": ACCEPT_NON_JPY_PF,
        "jpy": ACCEPT_JPY_PF,
    }

    lines: list[str] = []
    lines.append(f"# FOREX Resolver A/B Replay — {start.isoformat()} to {end.isoformat()}")
    lines.append("")
    lines.append(
        f"_Generated by `tools/forex_resolver_ab_replay.py` on "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}._  "
        f"Noise threshold (Sub-B): |pnl| >= {noise_bps}bp."
    )
    lines.append("")

    # Verdict
    lines.append("## Verdict")
    lines.append(
        f"- **Overall**: {accept['overall_verdict']} — {accept['overall_reason']}"
    )
    lines.append(
        f"- **Non-JPY sub-book**: {accept['per_cohort']['non_jpy']['verdict']} — "
        f"{accept['per_cohort']['non_jpy']['reason']}"
    )
    lines.append(
        f"- **JPY sub-book**: {accept['per_cohort']['jpy']['verdict']} — "
        f"{accept['per_cohort']['jpy']['reason']}"
    )
    lines.append("")

    # Sample
    pct_kept = (100.0 * after_noise_n / total_n) if total_n else 0.0
    lines.append("## Sample")
    lines.append(f"- Total FOREX picks in window: {total_n}")
    lines.append(
        f"- After noise filter (|pnl| >= {noise_bps}bp): {after_noise_n} "
        f"({after_noise_n}/{total_n} = {pct_kept:.1f}%)"
    )
    lines.append("")

    # Stats per cohort
    lines.append("## Stats per cohort")
    lines.append("")
    lines.append("| Cohort | Resolver | n | WR | sum_pnl_pct | PF | Sharpe |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    for cohort in cohorts_in_order:
        for label, table in (("Sub-A (current)", sub_a), ("Sub-B (5bp filter)", sub_b)):
            s = table[cohort]
            lines.append(
                f"| {cohort} | {label} | {s['n']} | {s['wr_pct']:.1f}% | "
                f"{s['sum_pnl_pct']:+.4f} | {_fmt_pf(s['pf'])} | {_fmt_sharpe(s['sharpe'])} |"
            )
    lines.append("")

    # Acceptance criteria
    lines.append("## Acceptance criteria check")
    overall_pf_ok = (
        sub_b["overall"]["n"] >= ACCEPT_MIN_N
        and _safe_finite(sub_b["overall"]["pf"]) >= ACCEPT_OVERALL_PF
    )
    non_jpy_pf_ok = (
        sub_b["non_jpy"]["n"] >= ACCEPT_MIN_N
        and _safe_finite(sub_b["non_jpy"]["pf"]) >= ACCEPT_NON_JPY_PF
    )
    jpy_pf_ok = (
        sub_b["jpy"]["n"] >= ACCEPT_MIN_N
        and _safe_finite(sub_b["jpy"]["pf"]) >= ACCEPT_JPY_PF
    )
    n_ok = all(sub_b[c]["n"] >= ACCEPT_MIN_N for c in cohorts_in_order)
    lines.append(
        f"- Overall PF (Sub-B) >= {ACCEPT_OVERALL_PF}: "
        f"**{_check(overall_pf_ok)}** (PF={_fmt_pf(sub_b['overall']['pf'])})"
    )
    lines.append(
        f"- Overall Sharpe lift (Sub-B - Sub-A) >= +{ACCEPT_OVERALL_SHARPE_LIFT}: "
        f"**{_check(accept['sharpe_pass'])}** (lift={accept['sharpe_lift']:+.3f})"
    )
    lines.append(
        f"- Non-JPY PF (Sub-B) >= {ACCEPT_NON_JPY_PF}: "
        f"**{_check(non_jpy_pf_ok)}** (PF={_fmt_pf(sub_b['non_jpy']['pf'])})"
    )
    lines.append(
        f"- JPY PF (Sub-B) >= {ACCEPT_JPY_PF}: "
        f"**{_check(jpy_pf_ok)}** (PF={_fmt_pf(sub_b['jpy']['pf'])})"
    )
    lines.append(f"- All sub-books n >= {ACCEPT_MIN_N}: **{_check(n_ok)}**")
    lines.append("")

    # Sample-size shifts
    lines.append("## Sample-size shifts")
    lines.append("")
    lines.append("| Sub-book | Sub-A n | Sub-B n | Dropped as noise |")
    lines.append("|---|---:|---:|---:|")
    for cohort in cohorts_in_order:
        a_n = sub_a[cohort]["n"]
        b_n = sub_b[cohort]["n"]
        lines.append(f"| {cohort} | {a_n} | {b_n} | {a_n - b_n} |")
    lines.append("")

    # Top-symbol drag (Sub-A)
    lines.append("## Top symbols by drag (Sub-A)")
    lines.append("")
    drag = top_negative_symbols(sub_a_picks, top_k=5)
    if not drag:
        lines.append("_No data._")
    else:
        lines.append("| Symbol | n | sum_pnl_pct |")
        lines.append("|---|---:|---:|")
        for sym, n, total in drag:
            lines.append(f"| {sym} | {n} | {total:+.4f} |")
    lines.append("")

    # Recommendation
    lines.append("## Recommendation")
    if accept["overall_verdict"] == "ACCEPTED":
        lines.append(
            f"- All cohorts PASS: ship the {noise_bps}bp threshold via env flag "
            f"`PNL_NOISE_THRESHOLD_BPS={noise_bps}` (opt-in)."
        )
    elif (
        accept["per_cohort"]["non_jpy"]["verdict"] == "ACCEPTED"
        and accept["per_cohort"]["overall"]["verdict"] == "ACCEPTED"
        and accept["per_cohort"]["jpy"]["verdict"] == "REJECTED"
    ):
        lines.append(
            "- Non-JPY PASS but JPY FAIL: scope the threshold to non-JPY pairs only "
            "(env flag with symbol allowlist)."
        )
    elif accept["overall_verdict"] == "INSUFFICIENT_SAMPLE":
        lines.append(
            "- Insufficient sample for at least one sub-book. Wait for more closed "
            "FOREX picks before re-running."
        )
    else:
        lines.append(
            "- Multiple cohorts FAIL: keep current threshold; investigate the "
            "rejected sub-book(s) for structural data-quality issues "
            "(yfinance live-close bug, asset-class-gating, JPY-pair pricing)."
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "_Acceptance thresholds renegotiated per "
        "`reports/PANEL_REVIEW_2026_04_29_OPERATION_PHENOMENAL_FOLLOWUPS.md` item #3 "
        "(4/4 risk-flag vote)._"
    )
    lines.append("")
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="FOREX resolver A/B replay (panel-renegotiated thresholds).",
    )
    p.add_argument(
        "--picks-source",
        type=Path,
        default=REPO_ROOT / DEFAULT_PICKS_SOURCE,
        help=f"path to dashboard_data.json (default: {DEFAULT_PICKS_SOURCE})",
    )
    p.add_argument(
        "--asset-class",
        default=DEFAULT_ASSET_CLASS,
        help=f"asset class to filter (default: {DEFAULT_ASSET_CLASS})",
    )
    p.add_argument(
        "--start-date",
        default=DEFAULT_START_DATE,
        help="ISO start date inclusive (default: 2026-02-01)",
    )
    p.add_argument(
        "--end-date",
        default=date.today().isoformat(),
        help="ISO end date inclusive (default: today)",
    )
    p.add_argument(
        "--noise-bps",
        type=int,
        default=DEFAULT_NOISE_BPS,
        help="Sub-B noise filter threshold in basis points (default: 5)",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="report output path "
        "(default: reports/forex_resolver_ab_<start>_<end>.md)",
    )
    return p.parse_args(argv)


def run(args: argparse.Namespace) -> dict:
    start = date.fromisoformat(args.start_date)
    end = date.fromisoformat(args.end_date)
    if end < start:
        raise SystemExit(f"--end-date {end} precedes --start-date {start}")

    noise_threshold_pct = args.noise_bps * PCT_PER_BP

    picks_source = args.picks_source
    if not picks_source.exists():
        raise SystemExit(f"picks source not found: {picks_source}")

    all_picks = load_recent_closed(picks_source)
    sub_a_picks = filter_picks(all_picks, args.asset_class, start, end)
    sub_b_picks = apply_noise_filter(sub_a_picks, noise_threshold_pct)

    sub_a_cohorts = split_cohorts(sub_a_picks)
    sub_b_cohorts = split_cohorts(sub_b_picks)

    sub_a_stats = {c: cohort_stats(sub_a_cohorts[c]) for c in ("overall", "jpy", "non_jpy")}
    sub_b_stats = {c: cohort_stats(sub_b_cohorts[c]) for c in ("overall", "jpy", "non_jpy")}

    accept = evaluate_acceptance(sub_a_stats, sub_b_stats)

    output = args.output
    if output is None:
        output = REPO_ROOT / "reports" / f"forex_resolver_ab_{start.isoformat()}_{end.isoformat()}.md"
    output = Path(output)

    md = render_report(
        start=start,
        end=end,
        noise_bps=args.noise_bps,
        total_n=len(sub_a_picks),
        after_noise_n=len(sub_b_picks),
        sub_a=sub_a_stats,
        sub_b=sub_b_stats,
        accept=accept,
        sub_a_picks=sub_a_picks,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(md, encoding="utf-8")

    return {
        "output": output,
        "accept": accept,
        "sub_a": sub_a_stats,
        "sub_b": sub_b_stats,
        "total_n": len(sub_a_picks),
        "after_noise_n": len(sub_b_picks),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run(args)
    accept = result["accept"]
    print(f"VERDICT: {accept['overall_verdict']} — {accept['overall_reason']}")
    print(f"  overall: {accept['per_cohort']['overall']['verdict']} "
          f"({accept['per_cohort']['overall']['reason']})")
    print(f"  non_jpy: {accept['per_cohort']['non_jpy']['verdict']} "
          f"({accept['per_cohort']['non_jpy']['reason']})")
    print(f"  jpy:     {accept['per_cohort']['jpy']['verdict']} "
          f"({accept['per_cohort']['jpy']['reason']})")
    print(f"  Sharpe lift: {accept['sharpe_lift']:+.3f} "
          f"(threshold +{ACCEPT_OVERALL_SHARPE_LIFT})")
    print(f"Report: {result['output']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
