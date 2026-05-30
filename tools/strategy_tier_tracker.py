"""strategy_tier_tracker.py — per-strategy x asset-class hedge-fund-tier tracker.

Read-only. Pulls every strategy from `audit_dashboard/data/pf_registry.json`
(the canonical PF/WR source, slippage-modeled and resolver-flicker-aware) and
emits a markdown table per asset class with each strategy's tier label per
CLAUDE.md MAJOR GOALS.

Tier thresholds (must match docs/AGENT_QUICKSTART_AUDIT_AND_STRATEGIES.md):
  Tier 1 — Renaissance:    PF > 2.0, WR > 55%, n >= 30
  Tier 2 — Institutional:  PF > 1.5, WR > 50%, n >= 30
  Tier 3 — Marginal:       PF > 1.2, WR > 45%, n >= 30
  Sub-T3 / FAIL:           anything else (incl. n < 30 -> INSUFFICIENT_DATA)

Usage:
  python3 tools/strategy_tier_tracker.py
  python3 tools/strategy_tier_tracker.py --class CRYPTO
  python3 tools/strategy_tier_tracker.py --min-n 30 --out /tmp/tracker.md
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PF_REGISTRY = Path("audit_dashboard/data/pf_registry.json")
STRAT_KEY = "by_asset_class_strategy_policy_clean_net"
CLASS_KEY = "by_asset_class_policy_clean_net"


def tier_label(row: dict, min_n: int = 30) -> str:
    """Return one of T1/T2/T3/FAIL/INSUFF_N for a pf_registry strategy row."""
    n = row.get("n") or 0
    if n < min_n:
        return f"INSUFF_N (n={n})"
    pf = row.get("profit_factor")
    wr = row.get("win_rate_pct")
    if pf is None or wr is None:
        return "UNDEFINED"
    # MDD not present per-strategy in pf_registry — only PF/WR/n here.
    if pf > 2.0 and wr > 55:
        return "T1 (Renaissance)"
    if pf > 1.5 and wr > 50:
        return "T2 (Institutional)"
    if pf > 1.2 and wr > 45:
        return "T3 (Marginal)"
    return "FAIL"


def class_verdict(row: dict) -> str:
    """One-line summary of class aggregate."""
    n = row.get("n") or 0
    pf = row.get("profit_factor")
    wr = row.get("win_rate_pct")
    if n < 50:
        return f"INSUFFICIENT_DATA (n={n})"
    if pf is None or wr is None:
        return "UNDEFINED"
    label = tier_label({"n": n, "profit_factor": pf, "win_rate_pct": wr}, min_n=50)
    return f"{label}  (n={n}, PF={pf:.2f}, WR={wr:.1f}%)"


def fmt(v, w=8, prec=3):
    if v is None:
        return "—".ljust(w)
    if isinstance(v, float):
        return f"{v:.{prec}f}".ljust(w)
    return str(v).ljust(w)


def build_report(reg: dict, class_filter: str | None, min_n: int) -> str:
    out: list[str] = []
    ts = datetime.now(timezone.utc).isoformat()
    out.append(f"# Strategy Tier Tracker — {ts}")
    out.append("")
    out.append(f"Source: `{PF_REGISTRY}` generated `{reg.get('generated_utc', 'unknown')}`")
    out.append("")
    out.append("Tier thresholds (CLAUDE.md MAJOR GOALS): T1 PF>2.0/WR>55; T2 PF>1.5/WR>50; T3 PF>1.2/WR>45; min n=30 for any tier.")
    out.append("")

    class_aggs_list = reg.get(CLASS_KEY, []) or []
    class_aggs = {r.get("asset_class"): r for r in class_aggs_list if isinstance(r, dict)}

    strat_rows = reg.get(STRAT_KEY, []) or []
    by_class: dict[str, list[dict]] = {}
    for r in strat_rows:
        if not isinstance(r, dict):
            continue
        ac = r.get("asset_class", "UNKNOWN")
        if class_filter and ac.upper() != class_filter.upper():
            continue
        by_class.setdefault(ac, []).append(r)

    if not by_class:
        out.append("_(no strategies matched the filter)_")
        return "\n".join(out)

    for ac in sorted(by_class):
        out.append(f"## {ac}")
        out.append("")
        if ac in class_aggs:
            out.append(f"**Class verdict:** {class_verdict(class_aggs[ac])}")
            out.append("")
        out.append("| Strategy | n | wins | losses | WR% | PF | Tier | Note |")
        out.append("|---|---:|---:|---:|---:|---:|---|---|")
        rows = sorted(
            by_class[ac],
            key=lambda r: (
                -(r.get("n") or 0),
                -(r.get("profit_factor") or 0),
            ),
        )
        for r in rows:
            tier = tier_label(r, min_n=min_n)
            note = r.get("pf_undefined_reason") or ""
            out.append(
                f"| `{r.get('strategy','?')}` | {fmt(r.get('n'),4,0)}"
                f"| {fmt(r.get('wins'),4,0)}| {fmt(r.get('losses'),4,0)}"
                f"| {fmt(r.get('win_rate_pct'),6,1)}| {fmt(r.get('profit_factor'),6,2)}"
                f"| {tier} | {note} |"
            )
        out.append("")

    out.append("---")
    out.append("Read-only report. Source of truth is pf_registry.json; do not recompute PF from raw picks.")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--class", dest="cls", default=None, help="Restrict to one asset class (e.g. CRYPTO)")
    ap.add_argument("--min-n", type=int, default=30, help="Minimum n for any tier label (default 30)")
    ap.add_argument("--out", default=None, help="Output path (default reports/strategy_tier_tracker_<utc>.md)")
    ap.add_argument("--no-write", action="store_true", help="Print to stdout only; do not write a file")
    args = ap.parse_args()

    if not PF_REGISTRY.exists():
        print(f"ERROR: {PF_REGISTRY} not found. Run from repo root.", file=sys.stderr)
        return 2
    reg = json.loads(PF_REGISTRY.read_text())

    md = build_report(reg, args.cls, args.min_n)
    print(md)

    if not args.no_write:
        out = Path(args.out) if args.out else Path(
            f"reports/strategy_tier_tracker_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.md"
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md)
        print(f"\n[strategy_tier_tracker] wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
