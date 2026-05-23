#!/usr/bin/env python3
"""
Weekly HF audit report (action plan §6) — real inputs only.

Reads when present:
  - audit_dashboard/data/dashboard_data.json (active + recent_closed summary)
  - alpha_engine/data/smart_picks.json
  - alpha_engine/data/pick_audit_log.json

Writes:
  - alpha_engine/data/hf_weekly_audit_report.json (default)

No invented metrics: Sharpe / turnover omitted if insufficient closed PnL rows.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO / "alpha_engine" / "data" / "hf_weekly_audit_report.json"
DASH = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
SMART = REPO / "alpha_engine" / "data" / "smart_picks.json"
AUDIT_LOG = REPO / "alpha_engine" / "data" / "pick_audit_log.json"


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    v = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return math.sqrt(v)


def _sharpe_like(pnls_pct: list[float]) -> float | None:
    """Rough daily-style Sharpe proxy from pnl_pct list; None if n < 10."""
    if len(pnls_pct) < 10:
        return None
    xs = [p / 100.0 for p in pnls_pct]
    mu, sig = _mean(xs), _std(xs)
    if sig <= 1e-12:
        return None
    return round((mu / sig) * math.sqrt(252), 4)


def _asset_class_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    c: Counter[str] = Counter()
    for p in rows:
        if not isinstance(p, dict):
            continue
        ac = str(p.get("asset_class") or "CRYPTO").upper()
        c[ac] += 1
    return dict(c)


def build_report(repo: Path = REPO) -> dict[str, Any]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report: dict[str, Any] = {
        "version": 1,
        "generated_at_utc": now,
        "sources_read": [],
        "dashboard": None,
        "smart_picks_engine": None,
        "pick_audit_log": None,
        "closed_book": None,
    }

    dash_path = repo / "audit_dashboard" / "data" / "dashboard_data.json"
    if dash_path.is_file():
        report["sources_read"].append(str(dash_path.relative_to(repo)))
        try:
            doc = json.loads(dash_path.read_text(encoding="utf-8", errors="replace"))
            picks = doc.get("picks") or {}
            active = picks.get("active") or []
            closed = picks.get("recent_closed") or []
            if isinstance(active, list):
                ac_active = _asset_class_counts(active)
            else:
                ac_active = {}
            pnls = []
            wins = 0
            for p in closed if isinstance(closed, list) else []:
                if not isinstance(p, dict):
                    continue
                pnl = p.get("pnl_pct")
                if pnl is None:
                    continue
                try:
                    v = float(pnl)
                except (TypeError, ValueError):
                    continue
                pnls.append(v)
                if v > 0:
                    wins += 1
            n = len(pnls)
            wr = round(100.0 * wins / n, 2) if n else None
            avg_pnl = round(_mean(pnls), 4) if n else None
            sh = _sharpe_like(pnls)
            report["dashboard"] = {
                "active_count": len(active) if isinstance(active, list) else 0,
                "active_by_asset_class": ac_active,
                "recent_closed_count": n,
                "recent_closed_wr_pct": wr,
                "recent_closed_avg_pnl_pct": avg_pnl,
                "recent_closed_sharpe_proxy": sh,
            }
            report["closed_book"] = {
                "note": "Sharpe is a coarse proxy on pnl_pct series; not annualized trade frequency.",
            }
        except (json.JSONDecodeError, OSError, TypeError) as e:
            report["dashboard"] = {"error": str(e)}

    smart_path = repo / "alpha_engine" / "data" / "smart_picks.json"
    if smart_path.is_file():
        report["sources_read"].append(str(smart_path.relative_to(repo)))
        try:
            sp = json.loads(smart_path.read_text(encoding="utf-8", errors="replace"))
            picks = sp.get("picks") or []
            report["smart_picks_engine"] = {
                "generated_at": sp.get("generated_at"),
                "picks_count": len(picks) if isinstance(picks, list) else 0,
                "total_scored": sp.get("total_scored"),
                "excluded_reasons": sp.get("excluded_reasons"),
                "method": sp.get("method"),
            }
        except (json.JSONDecodeError, OSError, TypeError) as e:
            report["smart_picks_engine"] = {"error": str(e)}

    log_path = repo / "alpha_engine" / "data" / "pick_audit_log.json"
    if log_path.is_file():
        report["sources_read"].append(str(log_path.relative_to(repo)))
        try:
            lg = json.loads(log_path.read_text(encoding="utf-8", errors="replace"))
            entries = lg.get("entries") or []
            tail = entries[-20:] if isinstance(entries, list) else []
            merged_excluded: Counter[str] = Counter()
            for e in tail:
                if not isinstance(e, dict):
                    continue
                er = e.get("excluded_reasons")
                if isinstance(er, dict):
                    for k, v in er.items():
                        try:
                            merged_excluded[str(k)] += int(v)
                        except (TypeError, ValueError):
                            pass
            report["pick_audit_log"] = {
                "entries_total": len(entries) if isinstance(entries, list) else 0,
                "last_20_excluded_rollups": dict(merged_excluded),
                "last_run_hf_gates_enabled": tail[-1].get("hf_quality_gates_enabled")
                if tail
                else None,
            }
        except (json.JSONDecodeError, OSError, TypeError) as e:
            report["pick_audit_log"] = {"error": str(e)}

    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Build HF weekly audit JSON from real dashboard/smart/audit files")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT, help="Output JSON path")
    args = ap.parse_args()
    r = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(r, indent=2), encoding="utf-8")
    print("Wrote", args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
