#!/usr/bin/env python3
"""Publish AUDIT_HF_MULTICLASS_FLEET_REVIEW to alpha_engine_bus."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REDIS_CLI = "C:/Users/zerou/redis-bus/redis-cli.exe"
PORT = 6379
REPO = Path(__file__).resolve().parent.parent
DOC = "docs/AUDIT_HF_MULTICLASS_FLEET_REVIEW_2026-04-07.md"
ARTIFACT = REPO / "tools" / "data" / "audit_active_book_analysis.json"


def run_redis_cmd(args):
    cmd = [REDIS_CLI, "-p", str(PORT)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    stats = {}
    if ARTIFACT.is_file():
        with open(ARTIFACT, "r", encoding="utf-8") as f:
            data = json.load(f)
        va = data.get("verified_alpha_summary_counts") or {}
        stats = {
            "active_count": data.get("active_count"),
            "smart_picks_count": data.get("smart_picks_count"),
            "va_active": va.get("active_count"),
            "va_smart": va.get("smart_count"),
            "recent_closed": data.get("recent_closed_count"),
        }
    envelope = {
        "bus_topic": "AUDIT_HF_MULTICLASS_FLEET_REVIEW",
        "from": "cursor-composer",
        "ts": ts,
        "summary": (
            "Fleet review: CRYPTO dominates closed (2820) vs EQUITY/FOREX/commodity/ETF/futures tiny n in user CSV export 2026-04-06. "
            "Exit mix SL-heavy vs TP — fix TP/SL unity + calibration. Smart=0 common (strict passes_smart_gate). "
            "VA separate cohort. HF path: narrow surface, anti-overfit, DSR/FDR, paper fills join. See docs MD. "
            "GitHub: eltonaguiar/findtorontoevents_antigravity.ca"
        ),
        "doc_path_repo_relative": DOC,
        "related_artifacts": [
            "audit_trail/quality_gates.py",
            "audit_trail/dashboard_generator.py",
            "HEDGE_FUND_ENHANCEMENT_PLAN.md",
            "docs/AUDIT_CRYPTO_PREDICTION_TP_SL_QUALITY_2026-04-02.md",
            "C:/Users/zerou/Downloads/antigravity_closed_picks_2026-04-06.csv",
            "C:/Users/zerou/Downloads/antigravity_active_picks_2026-04-06.csv",
        ],
        "dashboard_snapshot_stats": stats,
        "csv_export_note": (
            "Aggregated from antigravity_*_2026-04-06.csv: closed by AC; exit SL/SL_HIT vs TP/TP_HIT; "
            "paper-trading-orders CSVs in Downloads were empty on agent read — verify exporter."
        ),
        "action_required": (
            "Read docs/AUDIT_HF_MULTICLASS_FLEET_REVIEW_2026-04-07.md; P0 narrow surface + TP/SL module + smart funnel; "
            "fix paper order CSV export; join fills to pick IDs."
        ),
    }
    body = json.dumps(envelope, separators=(",", ":"))
    _, code = run_redis_cmd(["PUBLISH", "alpha_engine_bus", body])
    short = "AUDIT_HF_MULTICLASS_FLEET_REVIEW | %s" % ts
    run_redis_cmd(["LPUSH", "bus:broadcast:log", short])
    run_redis_cmd(["LTRIM", "bus:broadcast:log", "0", "99"])
    print("[OK]" if code == 0 else "[WARN]", short)
    if code != 0:
        import sys
        print("Envelope:\n", body, file=sys.stderr)
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
