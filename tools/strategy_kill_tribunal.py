#!/usr/bin/env python3
"""strategy_kill_tribunal.py — weekly auto-kill tribunal (P1-B, 2026-06-13).

Reads intrabar-resolved at_signal_outcomes (90d default), classifies each
strategy × asset_class as KILL / PROBATION / KEEP, writes JSON report, and
optionally appends KILL verdicts to emitter_audit.json recommended_actions.

Usage:
  python3 tools/strategy_kill_tribunal.py --dry-run
  python3 tools/strategy_kill_tribunal.py --apply   # requires TRIBUNAL_APPLY=1
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import pymysql  # noqa: E402
from tools.db_env import get_stocks_creds  # noqa: E402

REPORT_DIR = os.path.join(REPO_ROOT, "reports")
AUDIT_FILE = os.path.join(REPO_ROOT, "audit_trail", "data", "emitter_audit.json")
_KEEP = ("host", "user", "password", "database", "port", "connect_timeout")

# Master-loop do-not-relitigate unless n≥100 AND wr<40% (auto-override).
DO_NOT_AUTO_KILL = frozenset({
    "luxalgo_confluence",
})

AUTO_KILL_OVERRIDE_N = 100
AUTO_KILL_OVERRIDE_WR = 0.40


def classify_verdict(n: int, wr: float, pf: float) -> str:
    if n >= 30 and wr < 0.35 and pf < 0.8:
        return "KILL"
    if n >= 15 and (wr < 0.40 or pf < 1.0):
        return "PROBATION"
    return "KEEP"


def _should_kill(strategy: str, n: int, wr: float) -> bool:
    s = (strategy or "").strip().lower()
    if s in DO_NOT_AUTO_KILL:
        if n >= AUTO_KILL_OVERRIDE_N and wr < AUTO_KILL_OVERRIDE_WR:
            return True
        return False
    return True


def fetch_cohort(days: int = 90) -> list[dict]:
    creds = {k: v for k, v in get_stocks_creds().items() if k in _KEEP}
    conn = pymysql.connect(**creds, cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT UPPER(asset_class) AS asset_class,
               strategy,
               COUNT(*) AS n,
               SUM(intrabar_status = 'TP_HIT') AS wins,
               ROUND(SUM(CASE WHEN intrabar_pnl_pct > 0 THEN intrabar_pnl_pct ELSE 0 END)
                     / NULLIF(SUM(CASE WHEN intrabar_pnl_pct < 0 THEN -intrabar_pnl_pct ELSE 0 END), 0), 4) AS pf
        FROM at_signal_outcomes
        WHERE intrabar_resolved_at IS NOT NULL
          AND intrabar_status IN ('TP_HIT', 'SL_HIT')
          AND intrabar_resolved_at >= UTC_TIMESTAMP() - INTERVAL %s DAY
        GROUP BY UPPER(asset_class), strategy
        HAVING n >= 1
        ORDER BY n DESC
        """,
        (days,),
    )
    rows = []
    for r in cur.fetchall():
        n = int(r["n"] or 0)
        wins = int(r["wins"] or 0)
        wr = wins / n if n else 0.0
        pf = float(r["pf"]) if r["pf"] is not None else 0.0
        strat = (r["strategy"] or "").strip()
        ac = (r["asset_class"] or "UNKNOWN").upper()
        verdict = classify_verdict(n, wr, pf)
        entry = {
            "strategy": strat,
            "asset_class": ac,
            "n": n,
            "wr": round(wr, 4),
            "wr_pct": round(100.0 * wr, 1),
            "pf": pf,
            "verdict": verdict,
        }
        if verdict == "KILL" and not _should_kill(strat, n, wr):
            entry["verdict"] = "PROBATION"
            entry["override_note"] = "do-not-relitigate list — demoted from KILL"
        rows.append(entry)
    conn.close()
    return rows


def build_report(days: int = 90) -> dict:
    rows = fetch_cohort(days=days)
    kills = [r for r in rows if r["verdict"] == "KILL"]
    probation = [r for r in rows if r["verdict"] == "PROBATION"]
    keep = [r for r in rows if r["verdict"] == "KEEP"]
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": days,
        "source": "at_signal_outcomes.intrabar_* (TP_HIT/SL_HIT only)",
        "rules": {
            "KILL": "n>=30 AND WR<35% AND PF<0.8",
            "PROBATION": "n>=15 AND (WR<40% OR PF<1.0)",
            "KEEP": "else",
        },
        "kills": kills,
        "probation": probation,
        "keep_count": len(keep),
        "summary": {
            "n_evaluated": len(rows),
            "n_kill": len(kills),
            "n_probation": len(probation),
            "n_keep": len(keep),
        },
    }


def apply_kills(report: dict) -> list[str]:
    if os.environ.get("TRIBUNAL_APPLY", "0") != "1":
        raise RuntimeError("TRIBUNAL_APPLY=1 required for --apply")

    kill_strats = sorted({r["strategy"] for r in report.get("kills", []) if r.get("strategy")})
    if not kill_strats:
        return []

    os.makedirs(os.path.dirname(AUDIT_FILE), exist_ok=True)
    audit: dict = {}
    if os.path.isfile(AUDIT_FILE):
        try:
            with open(AUDIT_FILE, encoding="utf-8") as f:
                audit = json.load(f)
        except (json.JSONDecodeError, OSError):
            audit = {}

    recs = audit.setdefault("recommended_actions", {})
    force_kill = recs.setdefault("force_kill", [])
    existing = {str(s).lower() for s in force_kill if isinstance(s, str)}
    added = []
    for s in kill_strats:
        if s.lower() not in existing:
            force_kill.append(s)
            existing.add(s.lower())
            added.append(s)

    audit["last_tribunal_apply"] = report.get("generated_at")
    audit["tribunal_kill_count"] = len(kill_strats)
    with open(AUDIT_FILE, "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2)
    return added


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--apply", action="store_true", help="Append KILLs to emitter_audit (needs TRIBUNAL_APPLY=1)")
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()

    report = build_report(days=args.days)
    os.makedirs(REPORT_DIR, exist_ok=True)
    out_path = os.path.join(
        REPORT_DIR,
        f"strategy_tribunal_{dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d')}.json",
    )
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    if args.stdout:
        print(json.dumps(report, indent=2))
    else:
        s = report["summary"]
        print(f"wrote {out_path}: kill={s['n_kill']} probation={s['n_probation']} keep={s['n_keep']}")

    if args.apply:
        added = apply_kills(report)
        print(f"emitter_audit force_kill appended: {added}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
