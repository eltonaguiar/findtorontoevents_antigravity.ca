#!/usr/bin/env python3
"""Asset-class measurability report.

Answers one question before any profitability claim: for each asset class,
how many closed picks carry a *verified* mark, and what does the class look
like once fabricated flat closes are removed?

A "forged" close is a terminal row whose exit_price equals entry_price, or
whose pnl_pct is exactly 0. Those rows carry no price information: they are
the resolver writing TIME_EXIT without ever marking to market. Including them
as 0.0% is what makes classes look like coin flips.

Usage:
    python3 tools/asset_class_measurability.py [--payload PATH] [--out PATH]

Exit code is always 0 - this is a report, not a gate. Use
tools/pnl_zero_validator.py for the pass/fail gate.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

DEFAULT_PAYLOAD = "audit_dashboard/data/dashboard_data.json"
DEFAULT_OUT = "reports/asset_class_measurability.json"

OPEN_STATUSES = {"OPEN", "ACTIVE", ""}
MIN_MEASURABLE_N = 30


def _rows(obj, out):
    """Collect pick-shaped dicts anywhere in the payload."""
    if isinstance(obj, dict):
        if (
            "symbol" in obj
            and ("asset_class" in obj or "category" in obj)
            and ("pnl_pct" in obj or "exit_price" in obj or "status" in obj)
        ):
            out.append(obj)
        for value in obj.values():
            _rows(value, out)
    elif isinstance(obj, list):
        for value in obj:
            _rows(value, out)


def _f(value):
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _is_forged(row, pnl) -> bool:
    entry, exit_ = _f(row.get("entry_price")), _f(row.get("exit_price"))
    if entry is not None and exit_ is not None and entry == exit_:
        return True
    return pnl == 0.0


def _summarise(pnls: list[float]) -> dict:
    n = len(pnls)
    if n == 0:
        return {"n": 0}
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    ordered = sorted(pnls)
    tail_n = max(1, int(round(0.05 * n)))
    cvar95 = statistics.fmean(ordered[:tail_n])
    equity, peak, max_dd = 0.0, 0.0, 0.0
    for p in pnls:  # chronological as emitted; compounded, never additive
        equity += equity * (p / 100.0) if equity else p / 100.0
        peak = max(peak, equity)
        max_dd = min(max_dd, equity - peak)
    mean = statistics.fmean(pnls)
    sd = statistics.pstdev(pnls) if n > 1 else 0.0
    win_rate = 100.0 * len(wins) / n
    payoff = (gross_win / len(wins)) / (gross_loss / len(losses)) if wins and losses and gross_loss else None
    return {
        "n": n,
        "win_rate_pct": round(win_rate, 2),
        "profit_factor": round(gross_win / gross_loss, 4) if gross_loss else None,
        "mean_pnl_pct": round(mean, 4),
        "sd_pnl_pct": round(sd, 4),
        "payoff_ratio": round(payoff, 3) if payoff else None,
        # Kelly for a discrete win/loss bet; -1.0 is the correct size when <= 0.
        "kelly_fraction": round(win_rate / 100.0 - (1 - win_rate / 100.0) / payoff, 4) if payoff else None,
        "cvar95_pct": round(cvar95, 4),
        "max_drawdown_pct_compounded": round(100.0 * max_dd, 2),
        "sharpe_per_trade": round(mean / sd, 4) if sd else None,
    }


def build(payload_path: Path) -> dict:
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    found: list[dict] = []
    _rows(payload, found)

    buckets: dict[str, dict] = defaultdict(lambda: {"closed": 0, "forged": 0, "pnls": []})
    for row in found:
        if str(row.get("status") or "").upper() in OPEN_STATUSES:
            continue
        cls = str(row.get("asset_class") or row.get("category") or "UNKNOWN").upper()
        pnl = _f(row.get("pnl_pct"))
        bucket = buckets[cls]
        bucket["closed"] += 1
        if _is_forged(row, pnl):
            bucket["forged"] += 1
        elif pnl is not None:
            bucket["pnls"].append(pnl)

    health = (payload.get("performance") or {}).get("asset_class_health") or {}
    classes = {}
    for cls, bucket in sorted(buckets.items(), key=lambda kv: -kv[1]["closed"]):
        stats = _summarise(bucket["pnls"])
        real_n = stats.get("n", 0)
        contamination = 100.0 * bucket["forged"] / bucket["closed"] if bucket["closed"] else 0.0
        if real_n == 0:
            verdict = "UNMEASURABLE_NO_VERIFIED_MARKS"
        elif real_n < MIN_MEASURABLE_N:
            verdict = "UNMEASURABLE_THIN_N"
        elif contamination > 50.0:
            verdict = "PARTIAL_HIGH_CONTAMINATION"
        else:
            verdict = "MEASURABLE"
        classes[cls] = {
            "closed_rows": bucket["closed"],
            "forged_flat_rows": bucket["forged"],
            "contamination_pct": round(contamination, 1),
            "verified": stats,
            "measurability": verdict,
            "dashboard_reports": health.get(cls),
            "dashboard_pf_agrees": (
                None
                if not health.get(cls) or stats.get("profit_factor") is None
                else abs(float(health[cls].get("profit_factor") or 0) - stats["profit_factor"]) < 0.15
            ),
        }

    total_closed = sum(c["closed_rows"] for c in classes.values())
    total_forged = sum(c["forged_flat_rows"] for c in classes.values())
    return {
        "payload": str(payload_path),
        "generated_at": payload.get("generated_at"),
        "method": "verified marks only: closed rows minus exit_price==entry_price and pnl_pct==0",
        "totals": {
            "closed_rows": total_closed,
            "forged_flat_rows": total_forged,
            "contamination_pct": round(100.0 * total_forged / total_closed, 1) if total_closed else 0.0,
            "classes_seen": len(classes),
            "classes_measurable": sum(1 for c in classes.values() if c["measurability"].startswith("MEASURABLE")),
        },
        "classes": classes,
    }


def render(report: dict) -> str:
    lines = [
        f"payload      {report['payload']}",
        f"generated_at {report['generated_at']}",
        "",
        f"{'class':<14}{'closed':>8}{'forged':>8}{'contam':>8}{'verified':>9}{'WR%':>7}{'PF':>7}{'Sharpe/tr':>11}  measurability",
    ]
    for cls, c in report["classes"].items():
        v = c["verified"]
        pf = v.get("profit_factor")
        wr = v.get("win_rate_pct")
        sharpe = v.get("sharpe_per_trade")
        lines.append(
            f"{cls:<14}{c['closed_rows']:>8}{c['forged_flat_rows']:>8}"
            f"{c['contamination_pct']:>7.0f}%{v.get('n', 0):>9}"
            f"{(f'{wr:.0f}' if wr is not None else '-'):>7}"
            f"{(f'{pf:.2f}' if pf is not None else '-'):>7}"
            f"{(f'{sharpe:.3f}' if sharpe is not None else '-'):>11}"
            f"  {c['measurability']}"
        )
    t = report["totals"]
    lines += [
        "",
        f"TOTAL closed={t['closed_rows']}  forged={t['forged_flat_rows']} "
        f"({t['contamination_pct']}%)  measurable classes={t['classes_measurable']}/{t['classes_seen']}",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload", default=DEFAULT_PAYLOAD)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    path = Path(args.payload)
    if not path.exists():
        print(f"[error] payload not found: {path}")
        return 2

    report = build(path)
    print(render(report))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
