#!/usr/bin/env python3
"""Summarize latest active picks and BT/forward enrichment (read-only).

Reads audit_trail/data/dashboard_payload.json (committed or CI output).
Use after dashboard_generator runs to verify bt_win_rate / tooltips line up.

  python tools/latest_picks_summary.py
  python tools/latest_picks_summary.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "audit_trail" / "data" / "dashboard_payload.json"

_ALIAS = {"multi_asset_futures_connors_rsi2": "connors_rsi2"}


def _norm_key(name: str) -> str:
    if not name:
        return ""
    return re.sub(r"[_\-\s]+", "", name.lower()).strip()


def _candidates(pick: dict, strat_name: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    def add(x: str) -> None:
        x = (x or "").strip()
        if not x or x in seen:
            return
        seen.add(x)
        out.append(x)

    add(strat_name)
    pid = str(pick.get("id") or "")
    if "::" in pid:
        prefix = pid.split("::", 1)[0].strip()
        if prefix and re.match(r"^[A-Za-z][A-Za-z0-9_]*$", prefix):
            add(prefix)
    for key in list(out):
        a = _ALIAS.get(key)
        if a:
            add(a)
    return out


def _resolve_lb(strat_lookup: dict, pick: dict, strat_name: str) -> dict | None:
    for cand in _candidates(pick, strat_name):
        row = strat_lookup.get(cand) or strat_lookup.get(_norm_key(cand))
        if row:
            return row
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="print JSON only")
    args = ap.parse_args()

    if not PAYLOAD.exists():
        print("Missing", PAYLOAD, file=sys.stderr)
        return 1

    data = json.loads(PAYLOAD.read_text(encoding="utf-8"))
    active = (data.get("picks") or {}).get("active") or []
    lb_list = data.get("leaderboard") or []
    strat_lookup: dict[str, dict] = {}
    for s in lb_list:
        name = (s.get("strategy") or "").strip()
        if not name:
            continue
        strat_lookup[name] = s
        nk = _norm_key(name)
        if nk and nk not in strat_lookup:
            strat_lookup[nk] = s

    with_bt_payload = sum(1 for p in active if p.get("bt_win_rate") is not None)
    resolved_bt = 0
    sample = []
    for p in sorted(active, key=lambda x: -(x.get("score") or 0))[:15]:
        sn = p.get("strategy") or ""
        row = _resolve_lb(strat_lookup, p, sn)
        bt = row.get("bt_wr") if row else None
        if bt is not None or (row and (row.get("bt_trades") or 0) > 0):
            resolved_bt += 1
        sample.append(
            {
                "symbol": p.get("symbol"),
                "strategy": sn,
                "id": p.get("id"),
                "score": p.get("score"),
                "payload_bt_win_rate": p.get("bt_win_rate"),
                "resolved_bt_wr": bt,
                "resolved_bt_trades": (row or {}).get("bt_trades"),
                "leaderboard_strategy": (row or {}).get("strategy"),
            }
        )

    total = len(active)
    fixable = 0
    for p in active:
        sn = p.get("strategy") or ""
        row = _resolve_lb(strat_lookup, p, sn)
        if p.get("bt_win_rate") is None and row and row.get("bt_wr") is not None:
            fixable += 1

    out = {
        "payload_path": str(PAYLOAD),
        "generated_at": data.get("generated_at"),
        "active_count": total,
        "active_with_bt_win_rate_in_payload": with_bt_payload,
        "top15_would_have_resolved_bt_row": resolved_bt,
        "active_would_gain_bt_after_resolver": fixable,
        "top_by_score": sample,
    }

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print("Payload:", PAYLOAD)
        print("generated_at:", out["generated_at"])
        print("active:", total)
        print("bt_win_rate set in payload:", with_bt_payload)
        print("top 15 by score: resolved to LB row with BT:", resolved_bt, "/ 15")
        print("active picks that would get bt_wr after resolver:", fixable)
        print("--- top 15 by score ---")
        for row in sample:
            print(
                row["symbol"],
                "| strat:",
                (row["strategy"] or "")[:40],
                "| id:",
                str(row["id"])[:50],
                "| payload BT:",
                row["payload_bt_win_rate"],
                "| resolved:",
                row["resolved_bt_wr"],
                "| LB key:",
                row["leaderboard_strategy"],
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
