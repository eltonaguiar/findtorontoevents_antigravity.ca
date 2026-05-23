#!/usr/bin/env python3
"""Generate per-asset-class freshness + quality snapshot from dashboard ledger.

Outputs:
  - JSON artifact for automation / CI
  - Markdown report for human review

Schema additions (B3 2026-05-01):
  ``empty_timeframe_lanes`` — list of ``{"asset_class": str, "timeframe": str}``
  dicts for every standard lane with 0 active picks. Computed from
  ``picks.active`` in the dashboard payload. A lane is "empty" when no pick
  in the active book carries that ``(asset_class, timeframe)`` pair.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Standard lanes the dashboard is expected to cover. Cells absent from the
# active book are "empty lanes" and flagged in the artifact.
_STANDARD_ASSET_CLASSES = ("CRYPTO", "EQUITY", "FOREX", "BOND", "ETF", "COMMODITY")
_STANDARD_TIMEFRAMES = ("SCALP", "INTRADAY", "SWING", "POSITION")


def _parse_iso(ts: Any) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _safe_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _age_days(last_ts: datetime | None, now: datetime) -> float | None:
    if last_ts is None:
        return None
    raw = (now - last_ts).total_seconds() / 86400.0
    return round(max(0.0, raw), 2)


def _class_rows(picks: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in picks:
        ac = str(p.get("asset_class") or "UNKNOWN").upper()
        by_class[ac].append(p)

    rows: list[dict[str, Any]] = []
    for ac in sorted(by_class):
        rows_raw = by_class[ac]
        pnl_vals: list[float] = []
        last_closed: datetime | None = None
        last_seen: datetime | None = None
        for r in rows_raw:
            v = _safe_float(r.get("pnl_pct"))
            if v is not None:
                pnl_vals.append(v)
            cts = _parse_iso(r.get("closed_at"))
            tss = _parse_iso(r.get("timestamp"))
            if cts and (last_closed is None or cts > last_closed):
                last_closed = cts
            if tss and (last_seen is None or tss > last_seen):
                last_seen = tss

        n = len(pnl_vals)
        wins = [v for v in pnl_vals if v > 0]
        losses = [v for v in pnl_vals if v < 0]
        wr = (len(wins) / n * 100.0) if n else 0.0
        gp = sum(wins)
        gl = abs(sum(losses))
        pf = gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0)
        avg = (sum(pnl_vals) / n) if n else 0.0
        rows.append(
            {
                "asset_class": ac,
                "n": n,
                "win_rate_pct": round(wr, 2),
                "profit_factor": round(pf, 3),
                "avg_pnl_pct": round(avg, 4),
                "last_closed_at": last_closed.isoformat() if last_closed else None,
                "last_closed_age_days": _age_days(last_closed, now),
                "last_pick_ts": last_seen.isoformat() if last_seen else None,
                "last_pick_age_days": _age_days(last_seen, now),
            }
        )
    return rows


def _empty_timeframe_lanes(
    active_picks: list[dict[str, Any]],
    asset_classes: tuple[str, ...] = _STANDARD_ASSET_CLASSES,
    timeframes: tuple[str, ...] = _STANDARD_TIMEFRAMES,
) -> list[dict[str, str]]:
    """Return standard lanes with 0 active picks.

    A "lane" is a ``(asset_class, timeframe)`` pair. Each active pick
    contributes to the lane identified by its ``asset_class`` and ``timeframe``
    fields (both uppercased; unknown values are ignored for the emptiness
    check but the lane itself is still evaluated against the standard set).
    """
    covered: set[tuple[str, str]] = set()
    for p in active_picks:
        ac = str(p.get("asset_class") or "").upper()
        tf = str(p.get("timeframe") or "").upper()
        if ac in asset_classes and tf in timeframes:
            covered.add((ac, tf))
    return [
        {"asset_class": ac, "timeframe": tf}
        for ac in asset_classes
        for tf in timeframes
        if (ac, tf) not in covered
    ]


def build_report(input_path: Path, stale_days: float, now: datetime) -> dict[str, Any]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    picks_section = payload.get("picks") or {}

    closed_picks = picks_section.get("recent_closed") or []
    if not isinstance(closed_picks, list):
        closed_picks = []
    closed_picks = [p for p in closed_picks if isinstance(p, dict)]

    active_picks = picks_section.get("active") or []
    if not isinstance(active_picks, list):
        active_picks = []
    active_picks = [p for p in active_picks if isinstance(p, dict)]

    rows = _class_rows(closed_picks, now)
    stale_classes = [
        r["asset_class"]
        for r in rows
        if r["last_closed_age_days"] is None or r["last_closed_age_days"] > stale_days
    ]
    empty_lanes = _empty_timeframe_lanes(active_picks)
    return {
        "generated_at": now.isoformat(),
        "input_path": str(input_path),
        "stale_days_threshold": stale_days,
        "asset_classes": rows,
        "stale_asset_classes": stale_classes,
        "empty_timeframe_lanes": empty_lanes,
    }


def _to_markdown(d: dict[str, Any]) -> str:
    lines = [
        "# Asset-Class Freshness Snapshot",
        "",
        f"- Generated: `{d['generated_at']}`",
        f"- Input: `{d['input_path']}`",
        f"- Stale threshold (days): `{d['stale_days_threshold']}`",
        "",
        "## Per Class",
        "",
        "| Asset Class | n | WR% | PF | Avg PnL | Last Closed Age (d) | Last Pick Age (d) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in d["asset_classes"]:
        lines.append(
            f"| {r['asset_class']} | {r['n']} | {r['win_rate_pct']:.2f} | {r['profit_factor']:.3f} | "
            f"{r['avg_pnl_pct']:.4f} | {r['last_closed_age_days']} | {r['last_pick_age_days']} |"
        )
    stale_txt = ", ".join(d["stale_asset_classes"]) if d["stale_asset_classes"] else "None"
    empty_lanes = d.get("empty_timeframe_lanes", [])
    if empty_lanes:
        empty_txt = ", ".join(f"{l['asset_class']}×{l['timeframe']}" for l in empty_lanes)
    else:
        empty_txt = "None"
    lines.extend(
        [
            "",
            "## Stale Classes",
            "",
            stale_txt,
            "",
            "## Empty Timeframe Lanes (⚠ 0 active picks)",
            "",
            empty_txt,
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default="audit_dashboard/data/dashboard_data.json")
    ap.add_argument("--stale-days", type=float, default=2.0)
    ap.add_argument("--json-out", default="reports/asset_class_freshness_latest.json")
    ap.add_argument("--md-out", default="reports/asset_class_freshness_latest.md")
    ap.add_argument("--warn-only", action="store_true")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    input_path = Path(args.input)
    report = build_report(input_path, args.stale_days, now)

    json_out = Path(args.json_out)
    md_out = Path(args.md_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_out.write_text(_to_markdown(report), encoding="utf-8")

    print(f"Wrote: {json_out}")
    print(f"Wrote: {md_out}")
    if report["stale_asset_classes"] and not args.warn_only:
        print(f"Stale asset classes: {', '.join(report['stale_asset_classes'])}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

