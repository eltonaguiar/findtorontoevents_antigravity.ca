#!/usr/bin/env python3
"""Forward n→100 tracker — Tier-2 progress for verified paper sleeves.

Reads pilot_forward_dashboard.json + paper pilot state files. Emits:
  - reports/forward_n100_tracker_latest.json
  - reports/forward_n100_tracker_latest.md

Does not mutate PROMOTED_STRATEGIES.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT_JSON = ROOT / "reports/forward_n100_tracker_latest.json"
OUT_MD = ROOT / "reports/forward_n100_tracker_latest.md"
TARGET_N = 100


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _track_row(
    sleeve_id: str,
    *,
    forward_n: int,
    pf: float | None,
    wr_pct: float | None,
    source: str,
    tier2: dict | None = None,
    extra: dict | None = None,
) -> dict:
    n_remaining = max(0, TARGET_N - forward_n)
    blockers: list[str] = []
    if forward_n < TARGET_N:
        blockers.append(f"n {forward_n}/{TARGET_N} ({n_remaining} to go)")
    if pf is not None and pf < 1.5:
        blockers.append(f"pf {pf} < 1.5")
    if wr_pct is not None and wr_pct < 50.0:
        blockers.append(f"wr {wr_pct}% < 50%")
    if tier2 and not tier2.get("passed"):
        blockers.extend(tier2.get("blockers") or [])
    row = {
        "sleeve": sleeve_id,
        "forward_n": forward_n,
        "n_remaining": n_remaining,
        "pct_to_target": round(100 * forward_n / TARGET_N, 1) if TARGET_N else 0,
        "pf": pf,
        "win_rate_pct": wr_pct,
        "source": source,
        "tier2": tier2 or {},
        "blockers": blockers,
        "at_target_n": forward_n >= TARGET_N,
        "tier2_pass": bool(tier2 and tier2.get("passed")),
    }
    if extra:
        row.update(extra)
    return row


def build_tracker() -> dict:
    pilot = _load(ROOT / "audit_dashboard/data/pilot_forward_dashboard.json")
    lux = _load(ROOT / "verified_strategies/paper_pilot/luxalgo_confluence_state.json")
    ada = _load(ROOT / "verified_strategies/paper_pilot/inverse_ml_ada_state.json")
    macd = _load(ROOT / "verified_strategies/paper_pilot/macd_rsi_m048_state.json")

    sleeves: list[dict] = []

    for key, block in (pilot.get("sleeves") or {}).items():
        fwd = block.get("forward") or {}
        n = int(fwd.get("n_closed") or 0)
        wr = fwd.get("wr")
        wr_pct = float(wr) * 100 if wr is not None else None
        pf = fwd.get("pf")
        pf_f = float(pf) if pf is not None else None
        sleeves.append(
            _track_row(
                key,
                forward_n=n,
                pf=pf_f,
                wr_pct=wr_pct,
                source=str(fwd.get("source") or "pilot_forward_dashboard"),
            )
        )

    bootstrap = pilot.get("bootstrap_forward") or {}
    for key, block in (bootstrap.get("sleeves") or {}).items():
        if any(s["sleeve"] == key for s in sleeves):
            continue
        fwd = block.get("forward") or {}
        n = int(fwd.get("n_closed") or 0)
        wr = fwd.get("wr")
        sleeves.append(
            _track_row(
                key,
                forward_n=n,
                pf=float(fwd["pf"]) if fwd.get("pf") is not None else None,
                wr_pct=float(wr) * 100 if wr is not None else None,
                source="bootstrap_forward",
            )
        )

    if lux:
        n = int(lux.get("rolling_30d_n_closed") or 0)
        tier2 = {}
        try:
            from audit_trail.promotion_gate import evaluate_forward_tier2

            pnls = [float(x) for x in (lux.get("rolling_30d_pnls") or []) if x is not None]
            if pnls:
                tier2 = evaluate_forward_tier2(pnls)
        except Exception as exc:
            tier2 = {"error": str(exc)}
        sleeves.append(
            _track_row(
                "luxalgo_confluence_pilot",
                forward_n=n,
                pf=lux.get("rolling_30d_pf"),
                wr_pct=(lux.get("rolling_30d_wr") or 0) * 100,
                source="luxalgo_confluence_state",
                tier2=tier2,
                extra={
                    "promotion_status": lux.get("promotion_status"),
                    "day_count": lux.get("day_count"),
                },
            )
        )

    if ada:
        db = ada.get("forward_db") or {}
        virt = ada.get("forward_virtual") or {}
        sleeves.append(
            _track_row(
                "inverse_ml_ada_15m_db",
                forward_n=int(db.get("n_closed") or 0),
                pf=db.get("pf"),
                wr_pct=(db.get("wr") or 0) * 100,
                source=str(db.get("source") or "mysql"),
                tier2=ada.get("tier2_db"),
            )
        )
        sleeves.append(
            _track_row(
                "inverse_ml_ada_15m_virtual",
                forward_n=int(virt.get("n_closed") or 0),
                pf=virt.get("pf"),
                wr_pct=(virt.get("wr") or 0) * 100,
                source="paper_log",
                tier2=ada.get("tier2_virtual"),
            )
        )

    if macd:
        n = int(macd.get("rolling_30d_n_closed") or 0)
        sleeves.append(
            _track_row(
                "macd_rsi_m048",
                forward_n=n,
                pf=macd.get("rolling_30d_pf"),
                wr_pct=(macd.get("rolling_30d_wr") or 0) * 100,
                source="macd_rsi_m048_state",
                extra={"day_count": macd.get("day_count")},
            )
        )

    sleeves.sort(key=lambda r: (-r["forward_n"], r["sleeve"]))
    closest = sleeves[0] if sleeves else None
    tier2_ready = [s for s in sleeves if s.get("tier2_pass")]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_n": TARGET_N,
        "tier2_charter": "n>=100, WR>=55%, PF>=1.4 (evaluate_forward_tier2)",
        "closest_to_n100": closest,
        "any_tier2_pass": len(tier2_ready) > 0,
        "tier2_pass_sleeves": [s["sleeve"] for s in tier2_ready],
        "sleeves": sleeves,
        "operator_note": (
            "luxalgo n=827 is deduped DB history, not isolated forward pilot clock — "
            "use promotion_status SHADOW until day_count>=30 and rolling metrics pass. "
            "ADA DB n may lag bootstrap (36) if strategy rows pre-filter; trust bootstrap + virtual log."
        ),
    }


def _to_md(report: dict) -> str:
    lines = [
        "# Forward n→100 tracker",
        "",
        f"**Generated:** {report.get('generated_at')}",
        f"**Target:** n={report.get('target_n')} | {report.get('tier2_charter')}",
        "",
        "| Sleeve | n | remaining | WR% | PF | tier2 pass |",
        "|--------|---|-----------|-----|-----|------------|",
    ]
    for s in report.get("sleeves") or []:
        t2 = "yes" if s.get("tier2_pass") else "no"
        lines.append(
            f"| {s['sleeve']} | {s['forward_n']} | {s['n_remaining']} | "
            f"{s.get('win_rate_pct', '—')} | {s.get('pf', '—')} | {t2} |"
        )
    c = report.get("closest_to_n100")
    if c:
        lines.extend(
            [
                "",
                f"**Closest:** `{c['sleeve']}` at n={c['forward_n']} ({c['n_remaining']} to go)",
            ]
        )
    lines.extend(["", report.get("operator_note", "")])
    return "\n".join(lines) + "\n"


def main() -> int:
    report = build_tracker()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    OUT_MD.write_text(_to_md(report), encoding="utf-8")
    c = report.get("closest_to_n100") or {}
    print(
        f"[forward_n100] wrote {OUT_JSON.name} — closest={c.get('sleeve')} "
        f"n={c.get('forward_n')}/{TARGET_N}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())