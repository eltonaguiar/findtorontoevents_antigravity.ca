#!/usr/bin/env python3
"""
Rolling Spearman IC monitor per source_system on recent closed picks.

Reads audit_dashboard/data/dashboard_data.json when present (real data only).
Writes tools/data/rolling_ic_monitor.json with per-source IC and pause hints.

No placeholder pick rows — if the dashboard file is missing or empty, exits 0
with a note in the output JSON.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_DASH = _REPO / "audit_dashboard" / "data" / "dashboard_data.json"
_OUT = _REPO / "tools" / "data" / "rolling_ic_monitor.json"


def _spearman(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n != len(ys) or n < 5:
        return None
    def ranks(vals: list[float]) -> list[float]:
        indexed = sorted(enumerate(vals), key=lambda t: t[1])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and indexed[j + 1][1] == indexed[i][1]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[indexed[k][0]] = avg_rank
            i = j + 1
        return r
    rx, ry = ranks(xs), ranks(ys)
    mean_x = sum(rx) / n
    mean_y = sum(ry) / n
    num = sum((rx[i] - mean_x) * (ry[i] - mean_y) for i in range(n))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in rx))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ry))
    if den_x == 0 or den_y == 0:
        return None
    return num / (den_x * den_y)


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload: dict = {
        "generated_at": ts,
        "source": str(_DASH),
        "rows_used": 0,
        "per_source": {},
        "note": "",
    }
    if not _DASH.is_file():
        payload["note"] = "dashboard_data.json not found — no IC computed"
        _OUT.parent.mkdir(parents=True, exist_ok=True)
        _OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 0

    try:
        doc = json.loads(_DASH.read_text(encoding="utf-8", errors="replace"))
    except (json.JSONDecodeError, OSError) as e:
        payload["note"] = "failed to read dashboard: %s" % e
        _OUT.parent.mkdir(parents=True, exist_ok=True)
        _OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 0

    closed = (
        (doc.get("picks") or {}).get("recent_closed")
        or doc.get("recent_closed")
        or []
    )
    if not isinstance(closed, list) or not closed:
        payload["note"] = "no recent_closed rows"
        _OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 0

    by_src: dict[str, list[tuple[float, float]]] = {}
    for row in closed:
        if not isinstance(row, dict):
            continue
        src = str(row.get("source_system") or row.get("source") or "").strip()
        if not src:
            continue
        try:
            sc = float(row.get("score") or row.get("smart_score") or 0)
            pnl = float(
                row.get("pnl_pct")
                or row.get("pnl_percent")
                or row.get("realized_pnl_pct")
                or 0
            )
        except (TypeError, ValueError):
            continue
        by_src.setdefault(src, []).append((sc, pnl))

    per: dict[str, dict] = {}
    for src, pairs in by_src.items():
        if len(pairs) < 20:
            continue
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        ic = _spearman(xs, ys)
        if ic is None:
            continue
        action = "ok"
        if ic < -0.05:
            action = "auto_pause_suggested"
        elif ic < 0.05:
            action = "reduce_allocation_suggested"
        per[src] = {
            "n": len(pairs),
            "spearman_ic": round(ic, 4),
            "action": action,
        }

    payload["rows_used"] = len(closed)
    payload["per_source"] = per
    payload["note"] = "IC from score vs realized pnl_pct on recent_closed"
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"generated_at": ts, "sources": len(per)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
