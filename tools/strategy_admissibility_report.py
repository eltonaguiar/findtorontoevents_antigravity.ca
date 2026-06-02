#!/usr/bin/env python3
"""
Unified strategy admissibility + edge-location report for /audit dashboards.

Reads local audit JSON (money_ready, tournament, nav surface, pilots) and
optionally live pf_portfolios roster. Writes:

  audit_dashboard/data/strategy_admissibility.json
  audit_dashboard/data/verified_edge_status.json  (--write only)

Usage:
  python3 tools/strategy_admissibility_report.py
  python3 tools/strategy_admissibility_report.py --write
  python3 tools/strategy_admissibility_report.py --write --fetch-live-portfolios
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "audit_dashboard" / "data"
REPORTS = ROOT / "reports"

ROOT_CAUSES: Dict[str, str] = {
    "CRYPTO": (
        "Policy-clean PF 0.89 (n~377): bulk scanner loss-skew; lab VWAP/Bollinger WF PASS "
        "but opt-in only. Proven pick_funnel cell (RR1.0-1.5 LONG) is subset — aggregate loses."
    ),
    "EQUITY": (
        "PF 0.33: regime_terminal 40% concentration; no verified sleeve merged. "
        "Faber TAA lab OK — forward pilot accumulating."
    ),
    "FOREX": (
        "PF 0.48, small n: carry lab thin; 14d raw shows high WR / PF 0.10 (EXPIRED mislabel). "
        "Not a data-feed outage — resolver/label issue."
    ),
    "ETF": (
        "Best lab candidate: dual momentum Tier-2 (PF 1.60, n=104). Live policy-clean n=3 — "
        "need forward n>=100 before merge."
    ),
    "COMMODITY": (
        "n=4 policy-clean; COT strategies dead post-leakage. Vol-scaled cross-mom lab Sharpe ~0.88."
    ),
    "BOND": (
        "Zero policy-clean rows; HYG/LQD momentum lab promising — insufficient live sample."
    ),
    "FUTURES": (
        "n=13, PF 0.52; futures_connors_rsi2 TIME_EXIT zombie — resolver not alpha."
    ),
}


def _load(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_key(key: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", key or "")


def audit_live_portfolios(fetch_live: bool) -> Dict[str, Any]:
    """Count open/empty portfolios from live or skip."""
    out: Dict[str, Any] = {
        "source": "skipped",
        "total": 0,
        "with_open": 0,
        "empty": 0,
        "missing_json": 0,
        "empty_keys": [],
        "top_open": [],
    }
    if not fetch_live:
        out["source"] = "local_hint"
        out["note"] = "Pass --fetch-live-portfolios to curl findtorontoevents.ca roster"
        return out

    base = "https://findtorontoevents.ca/audit/data/"
    req = urllib.request.Request(
        base + "pf_portfolios.json",
        headers={"User-Agent": "strategy-admissibility-report/1.0"},
    )
    try:
        roster = json.loads(urllib.request.urlopen(req, timeout=45).read())
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        out["error"] = str(exc)
        return out

    items = roster.get("portfolios", [])
    out["source"] = "live"
    out["generated_at"] = roster.get("generated_at")
    out["total"] = len(items)

    open_rows: List[tuple] = []
    for p in items:
        key = p.get("portfolio_key", "")
        url = base + "pf_portfolio_" + _safe_key(key) + ".json"
        try:
            detail = json.loads(
                urllib.request.urlopen(
                    urllib.request.Request(url, headers={"User-Agent": "strategy-admissibility-report/1.0"}),
                    timeout=25,
                ).read()
            )
        except Exception:
            out["missing_json"] += 1
            continue
        pos = detail.get("positions", [])
        op = [x for x in pos if str(x.get("status", "")).lower() == "open"]
        if not pos:
            out["empty"] += 1
            out["empty_keys"].append(key)
        elif op:
            out["with_open"] += 1
            open_rows.append((key, len(op), p.get("model_id"), p.get("risk_appetite")))
        # all closed historical — not counted as empty

    open_rows.sort(key=lambda x: -x[1])
    out["top_open"] = [
        {"portfolio_key": k, "open": n, "model_id": m, "risk_appetite": a}
        for k, n, m, a in open_rows[:10]
    ]
    out["pf_html_empty_ui_causes"] = [
        "Invisible Unicode in ?key= breaks fetch (fixed in pf.html 2026-06-02)",
        "15 models seeded but zero tournament picks ingested (command_a, groq_kimi_k2, etc.)",
        "portfolio_mix__* books are all-closed shadow history — 0 open is expected",
    ]
    return out


def load_money_ready() -> Dict[str, Any]:
    raw = _load(DATA / "money_ready_verdict.json") or {}
    classes: Dict[str, Any] = {}
    for cls, v in (raw.get("classes") or {}).items():
        if not isinstance(v, dict):
            continue
        classes[cls] = {
            "n": v.get("n_resolved", v.get("n")),
            "wr": v.get("wr"),
            "pf": v.get("pf"),
            "mdd": v.get("mdd"),
            "verdict": v.get("verdict"),
            "top_source": v.get("top_source"),
            "top_source_share": v.get("top_source_share"),
            "root_cause": ROOT_CAUSES.get(cls, ""),
        }
    summary = raw.get("summary") or {}
    return {
        "generated_at": raw.get("generated_at"),
        "money_ready_classes": summary.get("money_ready", []),
        "n_classes": summary.get("n_classes"),
        "by_class": classes,
    }


def load_tournament_edge() -> Dict[str, Any]:
    lb = _load(DATA / "ai_tournament_leaderboard.json") or {}
    rows = lb.get("leaderboard", lb.get("models", []))
    if not isinstance(rows, list):
        rows = []

    def score(r: dict) -> float:
        return float(r.get("pf_ci_lo", r.get("profit_factor", 0)) or 0)

    credible = [
        r for r in rows
        if int(r.get("n_resolved", r.get("n", 0)) or 0) >= 30
        and score(r) >= 1.2
    ]
    top = sorted(rows, key=score, reverse=True)[:12]
    return {
        "generated_at": lb.get("generated_at"),
        "surface": "/audit/ai-tournament.html + pf.html",
        "trust_level": "paper_only — separate universe from Smart Picks",
        "top_by_pf_ci_lo": [
            {
                "model_id": r.get("model_id", r.get("model")),
                "pf_ci_lo": r.get("pf_ci_lo"),
                "pf": r.get("profit_factor", r.get("pf")),
                "wr": r.get("win_rate", r.get("wr")),
                "n": r.get("n_resolved", r.get("n")),
            }
            for r in top
        ],
        "credible_n30_pf_ci_1_2": [
            {
                "model_id": r.get("model_id"),
                "pf_ci_lo": r.get("pf_ci_lo"),
                "n": r.get("n_resolved", r.get("n")),
            }
            for r in sorted(credible, key=score, reverse=True)
        ],
        "best_credible": "deepseek_v4 (pf_ci_lo~2.5, n~208) — tournament paper edge, NOT money-ready production",
    }


def load_pick_funnel_edge() -> Dict[str, Any]:
    nav = _load(DATA / "nav_surface_edge_matrix.json") or {}
    surfaces = nav.get("surfaces", [])
    surface_verdicts = []
    smart_crypto = None
    for s in surfaces if isinstance(surfaces, list) else []:
        if not isinstance(s, dict):
            continue
        surface_verdicts.append({
            "id": s.get("id"),
            "label": s.get("label"),
            "verdict": s.get("verdict"),
            "edge_classes": s.get("edge_classes", []),
        })
        if s.get("id") == "smart_picks":
            for row in s.get("rows", []):
                if row.get("asset_class") == "CRYPTO":
                    smart_crypto = row

    top = _load(DATA / "top_edges_per_class.json") or {}
    crypto_proven = (top.get("by_class") or {}).get("CRYPTO", {}).get("top_edges_proven", [])

    rec = _load(DATA / "pick_summary_stats_2w.json") or {}
    rec14 = {}
    for cls, v in (rec.get("by_class") or {}).items():
        if isinstance(v, dict):
            rec14[cls] = {
                "wr_pct": v.get("wr_shrunk_pct", v.get("wr_pct")),
                "pf": v.get("pf"),
                "caveats": v.get("caveats", []),
            }

    return {
        "surface": "/audit/pick_funnel.html",
        "trust_level": "discovery — DISPUTED cells; do not size without policy-clean",
        "nav_surfaces_all_no_edge": all(
            s.get("verdict") == "no-edge" for s in surface_verdicts
        ),
        "surface_verdicts": surface_verdicts,
        "smart_picks_crypto_cell": smart_crypto,
        "proven_cells_crypto": crypto_proven[:2],
        "recency_14d_by_class": rec14,
    }


def load_pilot_status() -> Dict[str, Any]:
    dash = _load(REPORTS / "pilot_forward_dashboard.json") or {}
    wf = _load(ROOT / "verified_strategies" / "WALKFORWARD_REPORT.json") or {}
    return {
        "surface": "verified_strategies lab + forward pilots (not on main /audit banner yet)",
        "trust_level": "promotion candidate after forward n>=100",
        "dashboard": dash,
        "walkforward_verdicts": {
            k: v.get("verdict") if isinstance(v, dict) else v
            for k, v in wf.items()
            if k not in ("generated_at", "timestamp")
        },
    }


def build_report(fetch_live_portfolios: bool) -> Dict[str, Any]:
    mr = load_money_ready()
    return {
        "schema_version": "1.0",
        "generated_at": _now(),
        "methodology_doc": "docs/BACKTEST_ADMISSIBILITY_STANDARD.md",
        "quant_review": "reports/quant_strategy_root_cause_review_2026-06-02.md",
        "executive_answers": {
            "need_more_time": (
                "Only for forward pilots (ETF DM, crypto VWAP/Bollinger, Faber) — n<100. "
                "NOT for bulk production: CRYPTO/EQUITY/FOREX already n>=32 policy-clean and PF<1."
            ),
            "strategies_suck": (
                "Bulk production book: yes for capital (PF<1). Lab/tournament: mixed — "
                "isolated edges exist but gated off or separate universe."
            ),
            "doing_wrong": [
                "Engine split: real_data_backtest lacks WF/DSR/costs for 25/31 academic strategies",
                "Sizing on raw vs policy-clean metrics",
                "Breadth over depth (88 strategies, most unvalidated)",
                "Tournament edge conflated with Smart Picks production",
            ],
            "dna_mutate": "Per-sleeve mutate (Faber, commodity vol-scale) — not class-wide invert",
            "invert": "Rare; never Connors crypto (loss-skew not wrong sign)",
            "data_feeds": "Secondary; FRED carry fixed via curl cache; live pain is pick quality + methodology",
        },
        "live_money_ready": mr,
        "edge_surfaces": {
            "audit_main": {
                "url": "https://findtorontoevents.ca/audit/",
                "trust": "ONLY surface for real-money sizing",
                "money_ready_count": len(mr.get("money_ready_classes") or []),
                "summary": "0/9 classes money-ready on policy-clean net",
            },
            "ai_tournament": load_tournament_edge(),
            "pick_funnel": load_pick_funnel_edge(),
            "verified_lab": load_pilot_status(),
        },
        "portfolio_audit": audit_live_portfolios(fetch_live_portfolios),
        "admissibility_pipeline": [
            "M-107 pre-register",
            "Real OHLCV",
            "Purged WF + costs (rigorous_backtest_harness)",
            "DSR/PBO/SPA",
            "Block bootstrap",
            "Forward virtual n>=100",
            "Shadow → money_ready_verdict",
        ],
        "next_actions": [
            "Run python3 tools/strategy_admissibility_report.py --write --fetch-live-portfolios daily",
            "Do not enable scanner merge until pilot_forward_dashboard any_promotion_ready",
            "Route academic adapters off real_data_backtest onto rigorous harness",
            "Size only on money_ready_verdict policy-clean — ignore raw registry PF",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Strategy admissibility + edge map report")
    ap.add_argument("--write", action="store_true", help="Write audit_dashboard/data JSON files")
    ap.add_argument(
        "--fetch-live-portfolios",
        action="store_true",
        help="Curl live pf_portfolios.json for open-position audit",
    )
    ap.add_argument(
        "--refresh-pilots",
        action="store_true",
        help="Run pilot_forward_dashboard.py before building report",
    )
    args = ap.parse_args()

    if args.refresh_pilots:
        subprocess.call([sys.executable, str(ROOT / "tools" / "pilot_forward_dashboard.py")], cwd=str(ROOT))

    report = build_report(args.fetch_live_portfolios)
    out_path = DATA / "strategy_admissibility.json"
    print(json.dumps(report, indent=2)[:4000])
    if len(json.dumps(report)) > 4000:
        print("... [truncated stdout; full payload in JSON file]")

    if args.write:
        DATA.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote {out_path}")

        sys.path.insert(0, str(ROOT))
        from alpha_engine.verified_promotion_gate import build_edge_status

        edge = build_edge_status()
        edge["strategy_admissibility"] = out_path.name
        edge["portfolio_audit"] = report.get("portfolio_audit")
        edge["edge_surfaces_summary"] = {
            "audit_main": report["edge_surfaces"]["audit_main"],
            "tournament_best": report["edge_surfaces"]["ai_tournament"].get("best_credible"),
            "pick_funnel_nav_all_no_edge": report["edge_surfaces"]["pick_funnel"].get(
                "nav_surfaces_all_no_edge"
            ),
        }
        edge_path = DATA / "verified_edge_status.json"
        edge_path.write_text(json.dumps(edge, indent=2), encoding="utf-8")
        print(f"Wrote {edge_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
