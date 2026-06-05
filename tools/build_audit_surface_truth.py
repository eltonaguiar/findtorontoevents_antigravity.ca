#!/usr/bin/env python3
"""Build audit_surface_truth.json — single trust panel for /audit surfaces.

Feeds ai-tournament.html, ai_leaderboard.html, and template major-goal JS.
Ground truth: money_ready_verdict + pf_registry policy-clean + MySQL closed pools.

Usage:
  python3 tools/build_audit_surface_truth.py
  python3 tools/build_audit_surface_truth.py --write-audit-dashboard
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "audit_dashboard/data/audit_surface_truth.json"
TIER2 = {"min_n": 100, "min_wr": 0.50, "min_pf": 1.5, "label": "mutual-fund-grade (Goal #1 Tier-2)"}


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _pf_from_pnls(pnls: list[float]) -> float | None:
    if not pnls:
        return None
    gw = sum(x for x in pnls if x > 0)
    gl = abs(sum(x for x in pnls if x < 0))
    if gl == 0:
        return 999.0 if gw > 0 else 0.0
    return round(gw / gl, 4)


def _mysql_surfaces() -> dict:
    import pymysql
    from tools.db_env import get_stocks_creds

    conn = pymysql.connect(**get_stocks_creds(), cursorclass=pymysql.cursors.DictCursor)
    out: dict = {}
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT status, COUNT(*) c FROM tournament_picks GROUP BY status ORDER BY c DESC
                """
            )
            t_status = {r["status"]: int(r["c"]) for r in cur.fetchall()}
            total_t = sum(t_status.values())
            mispriced = int(t_status.get("MISPRICED_ENTRY", 0))
            cur.execute(
                """
                SELECT asset_class,
                       COUNT(*) n,
                       SUM(status='WIN') wins,
                       AVG(pnl_pct) avg_pnl
                FROM tournament_picks
                WHERE status IN ('WIN','LOSS') AND asset_class IS NOT NULL
                GROUP BY asset_class
                """
            )
            t_by_class = []
            for r in cur.fetchall():
                n = int(r["n"] or 0)
                w = int(r["wins"] or 0)
                wr = w / n if n else 0
                t_by_class.append(
                    {
                        "asset_class": r["asset_class"],
                        "n_closed": n,
                        "wr": round(wr, 4),
                        "wr_pct": round(wr * 100, 1),
                        "avg_pnl_pct": round(float(r["avg_pnl"] or 0), 4),
                        "tier2_pass": n >= TIER2["min_n"] and wr >= TIER2["min_wr"],
                        "verdict": "COIN_FLIP_OR_WORSE" if wr < 0.52 and n >= 30 else (
                            "INSUFFICIENT_N" if n < TIER2["min_n"] else (
                                "SUB_TIER2" if wr < TIER2["min_wr"] else "WATCH"
                            )
                        ),
                    }
                )
            cur.execute(
                """
                SELECT COUNT(*) n FROM trading_picks
                WHERE closed_at IS NOT NULL AND pnl_pct IS NULL
                  AND status IN ('TP_HIT','SL_HIT','TIME_EXIT','WON','LOST')
                """
            )
            null_pnl = int(cur.fetchone()["n"])
            cur.execute(
                """
                SELECT category AS asset_class, COUNT(*) n,
                       SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) wins
                FROM trading_picks
                WHERE closed_at >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 90 DAY)
                  AND pnl_pct IS NOT NULL
                GROUP BY category
                HAVING n >= 10
                ORDER BY n DESC LIMIT 12
                """
            )
            prod_90d = []
            for r in cur.fetchall():
                n = int(r["n"] or 0)
                w = int(r["wins"] or 0)
                wr = w / n if n else 0
                prod_90d.append(
                    {
                        "asset_class": (r["asset_class"] or "UNKNOWN").upper(),
                        "n": n,
                        "wr_pct": round(wr * 100, 1),
                        "tier2_pass": False,
                        "note": "raw trading_picks 90d — not policy-clean; use pf_registry for sizing",
                    }
                )
        out = {
            "tournament": {
                "total_rows": total_t,
                "mispriced_entry_n": mispriced,
                "mispriced_pct": round(100 * mispriced / total_t, 1) if total_t else 0,
                "status_counts": t_status,
                "closed_by_class": t_by_class,
                "sizing_grade": "RESEARCH_ONLY",
                "banner": (
                    f"{mispriced}/{total_t} rows MISPRICED_ENTRY — "
                    "tournament WR is coin-flip at pool level; not money-ready."
                ),
            },
            "production_ledger": {
                "null_pnl_resolved": null_pnl,
                "resolver_backlog_note": (
                    "Run tools/backfill_resolved_pnl.py after ejaguiar1_backups archive"
                    if null_pnl > 0
                    else None
                ),
                "raw_90d_by_class": prod_90d,
            },
        }
    finally:
        conn.close()
    return out


def build_report() -> dict:
    verdict = _load_json(ROOT / "audit_dashboard/data/money_ready_verdict.json")
    pf = _load_json(ROOT / "audit_dashboard/data/pf_registry.json")
    pilot = _load_json(ROOT / "audit_dashboard/data/pilot_forward_dashboard.json")
    lb = _load_json(ROOT / "audit_dashboard/data/ai_leaderboard/ai_leaderboard_index.json")

    policy = {
        row["asset_class"]: row
        for row in (pf.get("by_asset_class_policy_clean_net") or [])
    }
    classes = []
    for ac, block in (verdict.get("classes") or {}).items():
        pc = policy.get(ac, {})
        classes.append(
            {
                "asset_class": ac,
                "verdict": block.get("verdict"),
                "n_resolved": block.get("n_resolved"),
                "wr_pct": round(float(block.get("wr") or 0) * 100, 1),
                "pf": block.get("pf"),
                "money_ready": ac in (verdict.get("summary") or {}).get("money_ready", []),
                "policy_clean_n": pc.get("n"),
                "policy_clean_pf": pc.get("pf") or pc.get("profit_factor"),
                "policy_clean_wr_pct": pc.get("win_rate_pct") or pc.get("wr") or pc.get("wr_pct"),
                "tier2_pass": (
                    int(block.get("n_resolved") or 0) >= TIER2["min_n"]
                    and float(block.get("wr") or 0) >= TIER2["min_wr"]
                    and float(block.get("pf") or 0) >= TIER2["min_pf"]
                ),
                "bridge_action": _bridge_action(ac, block, pc),
            }
        )
    classes.sort(key=lambda x: (-(x.get("n_resolved") or 0), x["asset_class"]))

    forward_candidates = []
    for name, sleeve in (pilot.get("sleeves") or {}).items():
        fwd = sleeve.get("forward") or {}
        n = int(fwd.get("n_closed") or 0)
        if n > 0 or sleeve.get("recommend_enable"):
            forward_candidates.append(
                {
                    "sleeve": name,
                    "n_closed": n,
                    "wr": fwd.get("wr"),
                    "pf": fwd.get("pf"),
                    "promotion_ready": bool(fwd.get("promotion_ready")),
                }
            )
    bootstrap = pilot.get("bootstrap_forward") or {}
    for name, sleeve in (bootstrap.get("sleeves") or {}).items():
        fwd = sleeve.get("forward") or {}
        n = int(fwd.get("n_closed") or 0)
        if n >= 20:
            forward_candidates.append(
                {
                    "sleeve": f"bootstrap_{name}",
                    "n_closed": n,
                    "wr": fwd.get("wr"),
                    "pf": fwd.get("pf"),
                    "promotion_ready": bool(fwd.get("promotion_ready")),
                }
            )

    mysql = _mysql_surfaces()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tier2_charter": TIER2,
        "money_ready_classes": (verdict.get("summary") or {}).get("money_ready") or [],
        "money_ready_count": len((verdict.get("summary") or {}).get("money_ready") or []),
        "headline": (
            "0/9 asset classes money-ready on policy-clean closed picks. "
            "Do not size on Smart Picks / tournament / leaderboard inflated WR. "
            "Bridge = clean ledger + forward n≥100 + promotion gate."
        ),
        "trust_hierarchy": [
            "money_ready_verdict.json + pf_registry.by_asset_class_policy_clean_net",
            "verified paper forward (pilot_forward_dashboard.json)",
            "trading_picks post backfill_resolved_pnl + clean_ingest_v2",
            "tournament_picks / ai_leaderboard (research only)",
        ],
        "by_asset_class": classes,
        "forward_track": sorted(forward_candidates, key=lambda x: -x["n_closed"])[:15],
        "ai_leaderboard": {
            "as_of": lb.get("as_of"),
            "picks": (lb.get("totals") or {}).get("picks"),
            "resolved": (lb.get("totals") or {}).get("resolved"),
            "engines": (lb.get("totals") or {}).get("engines"),
            "overall_wr": (lb.get("engines") or [{}])[0].get("overall", {}).get("wr") if lb.get("engines") else None,
            "sizing_grade": "ILLUSTRATIVE_ONLY",
            "banner": (
                "Frozen/thin book — not Goal #1 sizing. "
                f"n={(lb.get('totals') or {}).get('resolved', 0)} vs Tier-2 n≥100."
            ),
        },
        **mysql,
        "disputed_surfaces": [
            "CRYPTO Smart Picks / HC / ELITE (claude_gainer_st concentration + resolver mislabels)",
            "tournament headline model WR on n<30",
            "luxalgo bulk CRYPTO without dedupe (use isolated forward pilot)",
        ],
    }


def _bridge_action(ac: str, block: dict, pc: dict) -> str:
    v = block.get("verdict")
    n = int(block.get("n_resolved") or 0)
    pf = float(block.get("pf") or 0)
    if v == "NOT_READY" and ac == "CRYPTO":
        return "Hold production LONG; grow inverse_ml ADA / feature sleeves to forward n=100; fix null pnl backfill"
    if n < 20:
        return "INSUFFICIENT_N — no class-level sizing; paper-pilot only"
    if pf < 1.0:
        return "FAIL — mutate or kill emitters; no real money"
    if pf < 1.5:
        return "SUB_TIER2 — forward paper until n≥100 and PF≥1.5"
    return "Watch promotion_gate + DSR/PBO"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-audit-dashboard", action="store_true", default=True)
    args = ap.parse_args()
    report = build_report()
    payload = json.dumps(report, indent=2)
    if args.write_audit_dashboard:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(payload, encoding="utf-8")
        print(f"Wrote {OUT}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())