"""Per-asset quality monitor for /audit payloads."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

ASSET_CLASSES = ("CRYPTO", "EQUITY", "FOREX", "COMMODITY", "FUTURES", "BOND", "ETF")
MIN_ACTIVE_FOR_ENFORCEMENT = 10
QUALITY_GATE_MODE = os.getenv("QUALITY_GATE_MODE", "warn").strip().lower() or "warn"
FLOORS = {
    "CRYPTO": {"min_avg_score": 65.0, "min_forward_wr": 0.62},
    "EQUITY": {"min_avg_score": 40.0, "min_forward_wr": 0.50},
    "FOREX": {"min_avg_score": 40.0, "min_forward_wr": 0.46},
    "COMMODITY": {"min_avg_score": 40.0, "min_forward_wr": 0.50},
    "FUTURES": {"min_avg_score": 45.0, "min_forward_wr": 0.50},
    "BOND": {"min_avg_score": 35.0, "min_forward_wr": 0.50},
    "ETF": {"min_avg_score": 40.0, "min_forward_wr": 0.50},
}


def _norm_asset_class(value: Any) -> str:
    ac = str(value or "").upper().strip()
    return {
        "COMMODITIES": "COMMODITY",
        "BONDS": "BOND",
        "ETFS": "ETF",
        "STOCK": "EQUITY",
        "STOCKS": "EQUITY",
    }.get(ac, ac)


def _float(value: Any) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 3) if values else 0.0


def load_payload(payload_path: Path) -> dict[str, Any]:
    if not payload_path.exists():
        raise FileNotFoundError(f"Payload not found: {payload_path}")
    return json.loads(payload_path.read_text(encoding="utf-8"))


def build_summary(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    existing = payload.get("asset_class_summary") or payload.get("assetClassSummary")
    if isinstance(existing, dict) and existing:
        out: dict[str, dict[str, Any]] = {}
        for ac in ASSET_CLASSES:
            row = existing.get(ac) or {}
            out[ac] = {
                "activeCount": int(row.get("activeCount") or 0),
                "smartCount": int(row.get("smartCount") or 0),
                "avgScore": float(row.get("avgScore") or 0.0),
                "forwardWR": float(row.get("forwardWR") or 0.0),
                "thresholdPass": bool(row.get("thresholdPass")),
            }
        return out

    picks = payload.get("picks") or {}
    active = picks.get("active") or []
    smart = picks.get("smart_picks") or []
    active_by: dict[str, list[dict[str, Any]]] = {ac: [] for ac in ASSET_CLASSES}
    smart_by: dict[str, int] = {ac: 0 for ac in ASSET_CLASSES}
    for row in active:
        ac = _norm_asset_class(row.get("asset_class"))
        if ac in active_by:
            active_by[ac].append(row)
    for row in smart:
        ac = _norm_asset_class(row.get("asset_class"))
        if ac in smart_by:
            smart_by[ac] += 1

    summary: dict[str, dict[str, Any]] = {}
    for ac in ASSET_CLASSES:
        scores = [_float(r.get("score")) for r in active_by[ac]]
        fwrs: list[float] = []
        for row in active_by[ac]:
            val = _float(row.get("forward_wr", row.get("forward_win_rate")))
            if val is None:
                continue
            if val > 1.0:
                val = val / 100.0
            fwrs.append(val)
        summary[ac] = {
            "activeCount": len(active_by[ac]),
            "smartCount": smart_by[ac],
            "avgScore": _mean([v for v in scores if v is not None]),
            "forwardWR": _mean(fwrs),
            "thresholdPass": False,
        }
    return summary


def evaluate_violations(summary: dict[str, dict[str, Any]]) -> list[str]:
    violations: list[str] = []
    for ac in ASSET_CLASSES:
        row = summary.get(ac) or {}
        active_count = int(row.get("activeCount") or 0)
        smart_count = int(row.get("smartCount") or 0)
        avg_score = float(row.get("avgScore") or 0.0)
        forward_wr = float(row.get("forwardWR") or 0.0)
        floors = FLOORS[ac]
        if active_count < MIN_ACTIVE_FOR_ENFORCEMENT:
            continue
        if smart_count == 0:
            violations.append(f"{ac}: active>={MIN_ACTIVE_FOR_ENFORCEMENT} but smartCount=0")
        if avg_score < floors["min_avg_score"]:
            violations.append(
                f"{ac}: avgScore {avg_score:.2f} < floor {floors['min_avg_score']:.2f}"
            )
        if forward_wr <= 0:
            violations.append(f"{ac}: forwardWR missing/zero for enforced class")
        elif forward_wr < floors["min_forward_wr"]:
            violations.append(
                f"{ac}: forwardWR {forward_wr:.3f} < floor {floors['min_forward_wr']:.3f}"
            )
    return violations


def print_table(summary: dict[str, dict[str, Any]]) -> None:
    print("Asset Class | Active | Smart | AvgScore | ForwardWR | ThresholdPass")
    print("----------- | ------:| -----:| --------:| ---------:| :-----------")
    for ac in ASSET_CLASSES:
        row = summary.get(ac) or {}
        print(
            f"{ac:11} | {int(row.get('activeCount') or 0):6d} | "
            f"{int(row.get('smartCount') or 0):5d} | "
            f"{float(row.get('avgScore') or 0.0):8.2f} | "
            f"{float(row.get('forwardWR') or 0.0):9.3f} | "
            f"{'pass' if row.get('thresholdPass') else 'fail'}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Per-asset quality monitor")
    parser.add_argument(
        "--payload",
        default="audit_trail/data/dashboard_payload.json",
        help="Path to dashboard payload JSON",
    )
    parser.add_argument(
        "--check-per-asset",
        action="store_true",
        help="Evaluate per-asset quality floors and optionally fail",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="Optional file path to write monitor output JSON",
    )
    args = parser.parse_args()

    payload = load_payload(Path(args.payload))
    summary = build_summary(payload)
    violations = evaluate_violations(summary)
    for ac in ASSET_CLASSES:
        row = summary[ac]
        floors = FLOORS[ac]
        active_count = int(row.get("activeCount") or 0)
        row["thresholdPass"] = bool(
            active_count == 0
            or (
                active_count < MIN_ACTIVE_FOR_ENFORCEMENT
                or (
                    int(row.get("smartCount") or 0) > 0
                    and float(row.get("avgScore") or 0.0) >= floors["min_avg_score"]
                    and (
                        float(row.get("forwardWR") or 0.0) == 0.0
                        or float(row.get("forwardWR") or 0.0) >= floors["min_forward_wr"]
                    )
                )
            )
        )

    print_table(summary)
    if violations:
        print("\nViolations:")
        for violation in violations:
            print(f"- {violation}")
    else:
        print("\nNo per-asset violations detected.")

    report = {
        "mode": QUALITY_GATE_MODE,
        "minActiveForEnforcement": MIN_ACTIVE_FOR_ENFORCEMENT,
        "floors": FLOORS,
        "summary": summary,
        "violations": violations,
    }
    if args.output_json:
        out = Path(args.output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.check_per_asset and QUALITY_GATE_MODE == "hard" and violations:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
