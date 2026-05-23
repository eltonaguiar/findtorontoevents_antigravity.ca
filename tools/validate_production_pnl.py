#!/usr/bin/env python3
"""
Validate production PnL records for suspicious values.

Checks:
- zero/near-zero pnl (likely unresolved/noise)
- extreme outliers (default outside [-95, +300] %)

Writes report to: alpha_engine/data/pnl_validation_report.json
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "alpha_engine" / "data"
OUT = DATA_DIR / "pnl_validation_report.json"

ZERO_BAND = 0.01
MIN_PNL = -95.0
MAX_PNL = 300.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_float(v: Any) -> float | None:
    try:
        f = float(v)
        if f != f:
            return None
        return f
    except Exception:
        return None


def _extract_pnl(item: Dict[str, Any]) -> float | None:
    for key in ("pnl_pct", "realized_pnl_pct", "total_pnl_pct", "pnl"):
        if key in item:
            f = _to_float(item.get(key))
            if f is not None:
                if 0 < abs(f) < 1:
                    f *= 100.0
                return f
    return None


def _classify(pnl: float) -> str:
    if -ZERO_BAND <= pnl <= ZERO_BAND:
        return "ZERO_OR_NEAR_ZERO"
    if pnl < MIN_PNL or pnl > MAX_PNL:
        return "EXTREME_OUTLIER"
    return ""


def _scan_file(path: Path) -> Tuple[int, List[Dict[str, Any]]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return 0, []

    items: List[Dict[str, Any]] = []
    if isinstance(raw, list):
        items = [x for x in raw if isinstance(x, dict)]
    elif isinstance(raw, dict):
        for k in ("closed_picks", "closed", "resolved_picks", "picks", "active_picks"):
            if isinstance(raw.get(k), list):
                items.extend([x for x in raw[k] if isinstance(x, dict)])
        if not items:
            items = [raw]

    anomalies: List[Dict[str, Any]] = []
    checked = 0
    for idx, item in enumerate(items):
        pnl = _extract_pnl(item)
        if pnl is None:
            continue
        checked += 1
        kind = _classify(pnl)
        if kind:
            anomalies.append(
                {
                    "index": idx,
                    "kind": kind,
                    "pnl_pct": round(pnl, 6),
                    "symbol": item.get("symbol", item.get("pair", "")),
                    "strategy": item.get("strategy", item.get("source", "")),
                    "status": item.get("status", ""),
                }
            )
    return checked, anomalies


def main() -> None:
    patterns = [
        "*closed*.json",
        "*resolved*.json",
        "*portfolio*.json",
        "*picks*.json",
    ]
    files: List[Path] = []
    for p in patterns:
        files.extend(DATA_DIR.glob(p))
    files = sorted(set(files))

    summary = {
        "generated_at": _now(),
        "thresholds": {"zero_band": ZERO_BAND, "min_pnl": MIN_PNL, "max_pnl": MAX_PNL},
        "files_scanned": len(files),
        "records_checked": 0,
        "anomalies_found": 0,
        "files": [],
    }

    for f in files:
        checked, anomalies = _scan_file(f)
        if checked == 0 and not anomalies:
            continue
        summary["records_checked"] += checked
        summary["anomalies_found"] += len(anomalies)
        summary["files"].append(
            {
                "file": str(f.relative_to(ROOT)),
                "records_checked": checked,
                "anomalies": anomalies[:200],
                "anomaly_count": len(anomalies),
            }
        )

    OUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"PnL validation complete. checked={summary['records_checked']} anomalies={summary['anomalies_found']}")
    print(f"Report: {OUT}")


if __name__ == "__main__":
    main()

