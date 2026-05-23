#!/usr/bin/env python3
"""Render sidecar promotion status as a markdown table.

Reads ``audit_dashboard/data/dashboard_data.json::sidecar_promotion_status``
and writes a markdown report to ``docs/SIDECAR_STATUS.md`` (overwriting).

Operators get a CLI-readable surface for promotion-gate readiness without
needing to crack open the dashboard JSON or load /audit in a browser.

Refs: 3b08476fb56 (sidecar promotion tracker backend +
audit_trail/dashboard_generator.py:_compute_sidecar_promotion_status).

Usage:
    python tools/render_sidecar_status_md.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_PATH = REPO_ROOT / "docs" / "SIDECAR_STATUS.md"

STATUS_BADGE = {
    "PROMOTED": "🟢 PROMOTED",
    "READY_TO_PROMOTE": "🚀 READY_TO_PROMOTE",
    "BELOW_GATE": "🟡 BELOW_GATE",
    "INCUBATING": "🔵 INCUBATING",
}

# Sort ordering: PROMOTED first, then READY_TO_PROMOTE (newest = highest n),
# then BELOW_GATE, then INCUBATING.
STATUS_ORDER = {
    "PROMOTED": 0,
    "READY_TO_PROMOTE": 1,
    "BELOW_GATE": 2,
    "INCUBATING": 3,
}


def _fmt_num(v: Any, suffix: str = "") -> str:
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if f != f:  # NaN
        return "—"
    if abs(f - int(f)) < 1e-9:
        return f"{int(f)}{suffix}"
    return f"{f:.2f}{suffix}"


def _sort_key(item: tuple[str, dict]) -> tuple:
    name, entry = item
    status = entry.get("status", "INCUBATING")
    order = STATUS_ORDER.get(status, 99)
    # Within READY_TO_PROMOTE we want "newest" (highest n) first → negate n.
    n = entry.get("n") or 0
    return (order, -n, name)


def render_markdown(payload: dict, generated_at: str | None) -> str:
    """Render the markdown report. ``payload`` is the sidecar_promotion_status dict."""
    gen = generated_at or "unknown"
    lines: list[str] = []
    lines.append(f"# Sidecar Promotion Status — {gen}")
    lines.append("")

    if not payload:
        lines.append("_No sidecar promotion data available._")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(
            "Source: `audit_dashboard/data/dashboard_data.json::sidecar_promotion_status` · "
            "Regen: `python tools/render_sidecar_status_md.py`"
        )
        lines.append("")
        return "\n".join(lines)

    # Counts per status
    counts = {"PROMOTED": 0, "READY_TO_PROMOTE": 0, "BELOW_GATE": 0, "INCUBATING": 0}
    for entry in payload.values():
        s = entry.get("status", "INCUBATING")
        counts[s] = counts.get(s, 0) + 1

    summary_parts = [
        f"🟢 PROMOTED: {counts['PROMOTED']}",
        f"🚀 READY_TO_PROMOTE: {counts['READY_TO_PROMOTE']}",
        f"🟡 BELOW_GATE: {counts['BELOW_GATE']}",
        f"🔵 INCUBATING: {counts['INCUBATING']}",
    ]
    lines.append("**Summary:** " + " · ".join(summary_parts))
    lines.append("")

    lines.append(
        "| Strategy | Status | n | WR | PF | Gate (n/wr/pf) | ETA days | Days since first trade |"
    )
    lines.append(
        "| --- | --- | ---: | ---: | ---: | --- | ---: | ---: |"
    )

    for name, entry in sorted(payload.items(), key=_sort_key):
        status = entry.get("status", "INCUBATING")
        badge = STATUS_BADGE.get(status, status)
        n = _fmt_num(entry.get("n"))
        wr = _fmt_num(entry.get("wr"), "%")
        pf = _fmt_num(entry.get("pf"))
        gate = (
            f"{_fmt_num(entry.get('gate_n'))}"
            f" / {_fmt_num(entry.get('gate_wr'), '%')}"
            f" / {_fmt_num(entry.get('gate_pf'))}"
        )
        eta = _fmt_num(entry.get("eta_to_promotion_days"))
        days = _fmt_num(entry.get("days_since_first_trade"))
        lines.append(f"| `{name}` | {badge} | {n} | {wr} | {pf} | {gate} | {eta} | {days} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "Source: `audit_dashboard/data/dashboard_data.json::sidecar_promotion_status` · "
        "Backend: `audit_trail/dashboard_generator.py::_compute_sidecar_promotion_status` · "
        "Regen: `python tools/render_sidecar_status_md.py`"
    )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    data_path = DATA_PATH
    out_path = OUT_PATH
    if argv:
        if len(argv) >= 1 and argv[0]:
            data_path = Path(argv[0])
        if len(argv) >= 2 and argv[1]:
            out_path = Path(argv[1])

    if not data_path.exists():
        print(f"ERROR: dashboard data not found at {data_path}", file=sys.stderr)
        return 1

    with data_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    payload = data.get("sidecar_promotion_status") or {}
    generated_at = data.get("generated_at")

    md = render_markdown(payload, generated_at)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(f"Wrote {out_path} ({len(payload)} sidecar entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
