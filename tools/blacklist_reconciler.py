"""Blacklist reconciler — cross-check `quality_gates.py::BLOCKED_SOURCE_SYSTEMS`
comment-cited stats against current `audit_dashboard/data/dashboard_data.json::systems`.

Catches stale-blacklist cases where resolver-v2 (or any downstream metric change)
silently exonerated a blocked strategy without anyone re-validating the
blacklist. See report `reports/ml_crypto_pred_v12_resurrection_candidate_2026-05-13.md`
for the failure mode this protects against.

Output: `audit_dashboard/data/blacklist_reconciliation.json` with per-strategy:
- name
- blacklist_comment (raw text from quality_gates.py)
- live_pf, live_wr, live_n, live_status
- verdict: KILL_CONFIRMED / RESURRECTION_CANDIDATE / NO_LIVE_DATA / MUTATE_FIRST

Acceptance gates (CLAUDE.md tier targets):
- RESURRECTION_CANDIDATE: live_pf >= 1.5 AND live_wr >= 50 AND live_n >= 30
- MUTATE_FIRST: live_pf >= 1.2 BUT live_wr < 50 (mutation candidate per
  docs/MUTATION_THREE_AXIS_PROTOCOL.md)
- KILL_CONFIRMED: live_pf < 1.0 (blacklist still correct)
- NO_LIVE_DATA: strategy not in `systems` block

Run: `python tools/blacklist_reconciler.py` (writes JSON + prints summary).
GHA cron: see `.github/workflows/blacklist_reconciler.yml` (TODO).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
QG_PATH = REPO_ROOT / "audit_trail" / "quality_gates.py"
SYSTEMS_PATH = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_PATH = REPO_ROOT / "audit_dashboard" / "data" / "blacklist_reconciliation.json"

RESURRECT_PF = 1.5
RESURRECT_WR = 50.0
RESURRECT_N = 30
MUTATE_PF = 1.2


def parse_blacklist() -> list[dict]:
    """Parse BLOCKED_SOURCE_SYSTEMS set in quality_gates.py.

    Each entry is a quoted name optionally followed by a comment.
    Returns: [{name, comment, blacklist_pf, blacklist_wr, blacklist_n}].
    """
    src = QG_PATH.read_text(encoding="utf-8")
    # Find the BLOCKED_SOURCE_SYSTEMS = { ... } block
    m = re.search(r"BLOCKED_SOURCE_SYSTEMS\s*=\s*\{(.*?)^\}", src, re.MULTILINE | re.DOTALL)
    if not m:
        raise RuntimeError("BLOCKED_SOURCE_SYSTEMS block not found")
    block = m.group(1)
    out = []
    # Match: "name",  # comment
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith('"') and not line.startswith("#"):
            continue
        # Skip pure-comment lines (no entry on them)
        if line.startswith("#"):
            continue
        # Match: "name",[optional comment]
        entry_m = re.match(r'"([^"]+)"\s*,?\s*(#\s*(.*))?', line)
        if not entry_m:
            continue
        name = entry_m.group(1)
        comment = entry_m.group(3) or ""
        rec = {"name": name, "comment": comment}
        # Extract numbers from comment heuristically
        pf_m = re.search(r"PF\s*([\d.]+)", comment, re.IGNORECASE)
        wr_m = re.search(r"([\d.]+)\s*%\s*WR", comment, re.IGNORECASE)
        n_m = re.search(r"([\d,]+)\s*trades", comment, re.IGNORECASE)
        rec["blacklist_pf"] = float(pf_m.group(1)) if pf_m else None
        rec["blacklist_wr"] = float(wr_m.group(1)) if wr_m else None
        rec["blacklist_n"] = int(n_m.group(1).replace(",", "")) if n_m else None
        out.append(rec)
    return out


def load_systems() -> dict[str, dict]:
    if not SYSTEMS_PATH.exists():
        return {}
    d = json.loads(SYSTEMS_PATH.read_text(encoding="utf-8"))
    by_name = {}
    for s in d.get("systems", []):
        by_name[s.get("name", "")] = s
    return by_name


def classify(live: dict, blacklist_pf: float | None) -> str:
    """Verdict per spec."""
    if not live:
        return "NO_LIVE_DATA"
    pf = float(live.get("profit_factor") or 0)
    wr = float(live.get("win_rate") or 0)
    n = int(live.get("closed_picks") or 0)
    if pf >= RESURRECT_PF and wr >= RESURRECT_WR and n >= RESURRECT_N:
        return "RESURRECTION_CANDIDATE"
    if pf >= MUTATE_PF and wr < RESURRECT_WR and n >= RESURRECT_N:
        return "MUTATE_FIRST"
    return "KILL_CONFIRMED"


def reconcile() -> dict:
    entries = parse_blacklist()
    systems = load_systems()
    rows = []
    counts = {"KILL_CONFIRMED": 0, "RESURRECTION_CANDIDATE": 0,
              "MUTATE_FIRST": 0, "NO_LIVE_DATA": 0}
    for e in entries:
        live = systems.get(e["name"], {})
        verdict = classify(live, e["blacklist_pf"])
        counts[verdict] += 1
        row = {
            **e,
            "live_pf": live.get("profit_factor"),
            "live_wr": live.get("win_rate"),
            "live_n": live.get("closed_picks"),
            "live_pnl_pct": live.get("total_pnl_pct"),
            "live_status": live.get("status"),
            "live_last_signal_at": live.get("last_signal_at"),
            "verdict": verdict,
        }
        rows.append(row)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": counts,
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print summary but don't write JSON.")
    args = parser.parse_args()
    result = reconcile()
    print(f"Reconciled {len(result['rows'])} blacklist entries:")
    for k, v in result["summary"].items():
        print(f"  {k}: {v}")
    print()
    # Highlight reversals
    for r in result["rows"]:
        if r["verdict"] in {"RESURRECTION_CANDIDATE", "MUTATE_FIRST"}:
            print(f"  * {r['verdict']}: {r['name']:30} blacklist_PF={r['blacklist_pf']} "
                  f"live_PF={r['live_pf']} live_WR={r['live_wr']} live_n={r['live_n']} "
                  f"silent_since={r['live_last_signal_at']}")
    if args.dry_run:
        print("\nDRY-RUN: no write.")
        return
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT_PATH.with_suffix(OUT_PATH.suffix + ".tmp")
    tmp.write_text(json.dumps(result, indent=2), encoding="utf-8")
    import os
    os.replace(tmp, OUT_PATH)
    print(f"\nWrote {OUT_PATH}")


if __name__ == "__main__":
    main()
