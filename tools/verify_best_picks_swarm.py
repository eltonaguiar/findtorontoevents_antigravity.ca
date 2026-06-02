#!/usr/bin/env python3
"""Swarm-review best-pick claims against local audit JSON (no fabricated stats)."""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "best_picks_swarm_review_2026-06-02.json"
PROXY = "http://localhost:4000/v1"

# EAGLE3 tournament directional table (resolved picks, source: EAGLE3_2026-06-02_minimax-m3-free.MD)
EAGLE3_DIRECTIONAL = [
    {"asset_class": "CRYPTO", "direction": "LONG", "wr": 0.33, "n": 216, "note": "production bug — scanner emits LONG"},
    {"asset_class": "CRYPTO", "direction": "SHORT", "wr": 0.67, "n": 216, "note": "tournament edge — flip target"},
    {"asset_class": "EQUITY", "direction": "LONG", "wr": 0.75, "n": None, "note": "LONG-only per EAGLE3"},
    {"asset_class": "ETF", "direction": "LONG", "wr": 0.88, "n": None, "note": "LONG-only per EAGLE3"},
]

EAGLE3_SYMBOLS = [
    {"asset_class": "ETF", "symbols": ["EEM", "IWM", "GLD"], "note": "EEM 93%, IWM 75%, GLD 68% WR in EAGLE3"},
    {"asset_class": "EQUITY", "symbols": ["BAC", "JPM", "MSFT", "NVDA"], "note": "LONG bias tournament whitelist"},
    {"asset_class": "CRYPTO", "symbols": ["BTCUSDT", "ETHUSDT"], "note": "SHORT-only after flip"},
]

LAB_SLEEVE = {
    "strategy_id": "etf_verified_dual_momentum",
    "lab_pf": 1.60,
    "lab_wr": 0.538,
    "lab_n": 104,
    "wf_oos_pf": 1.21,
    "wf_oos_n": 32,
    "wf_verdict": "PASS",
    "live_etf_n": 3,
    "tier": "SHADOW_PAPER_ONLY",
    "source": "reports/multi_class_strategy_lab_2026-06-02.md",
}


def _load(p: Path):
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def build_evidence_pack() -> dict:
    pack = {"generated_at": datetime.now(timezone.utc).isoformat(), "sources": []}

    mr_path = ROOT / "audit_dashboard/data/money_ready_verdict.json"
    mr = _load(mr_path)
    if mr:
        pack["money_ready"] = {
            "path": str(mr_path.relative_to(ROOT)),
            "generated_at": mr.get("generated_at"),
            "money_ready_count": len((mr.get("summary") or {}).get("money_ready") or []),
            "classes": {
                k: {
                    "n_resolved": v.get("n_resolved"),
                    "wr": v.get("wr"),
                    "pf": v.get("pf"),
                    "verdict": v.get("verdict"),
                }
                for k, v in (mr.get("classes") or {}).items()
                if isinstance(v, dict)
            },
        }
        pack["sources"].append(pack["money_ready"]["path"])

    lb_path = ROOT / "audit_dashboard/data/ai_tournament_leaderboard.json"
    lb = _load(lb_path)
    if lb:
        top = []
        for m in (lb.get("models") or [])[:6]:
            if not isinstance(m, dict):
                continue
            top.append({
                "model_id": m.get("model_id"),
                "n_resolved": m.get("n_resolved"),
                "wr": m.get("wr"),
                "pf": m.get("pf"),
                "tier": m.get("tier"),
                "rank": m.get("rank"),
            })
        pack["tournament_leaderboard"] = {
            "path": str(lb_path.relative_to(ROOT)),
            "generated_at": lb.get("generated_at"),
            "min_n_to_rank": lb.get("min_n_to_rank"),
            "top_models": top,
        }
        pack["sources"].append(pack["tournament_leaderboard"]["path"])

    pack["eagle3_directional"] = {
        "path": "EAGLE3_2026-06-02_minimax-m3-free.MD",
        "rows": EAGLE3_DIRECTIONAL,
        "symbol_whitelist": EAGLE3_SYMBOLS,
    }
    pack["sources"].append(pack["eagle3_directional"]["path"])

    pack["lab_sleeve"] = LAB_SLEEVE
    pack["sources"].append(LAB_SLEEVE["source"])

    t_path = ROOT / "audit_dashboard/data/ai_tournament_picks_latest.json"
    t = _load(t_path)
    if t:
        picks = t if isinstance(t, list) else t.get("picks", [])
        n_with_outcome = sum(
            1
            for pk in picks
            if str(pk.get("outcome", "")).upper() in ("WON", "LOST", "LOSS", "WIN")
        )
        pack["tournament_picks_export"] = {
            "path": str(t_path.relative_to(ROOT)),
            "total_picks": len(picks),
            "resolved_in_export": n_with_outcome,
            "note": "Export has null outcomes — use leaderboard + EAGLE3 for symbol/direction stats",
        }
        pack["sources"].append(pack["tournament_picks_export"]["path"])

    return pack


def swarm_review(evidence: dict) -> str:
    prompt = f"""You are reviewing a "best picks" list for findtorontoevents.ca/audit.

RULES:
- Use ONLY the JSON evidence below. Do not invent WR/PF.
- Distinguish three surfaces: (A) production /audit money_ready, (B) AI tournament paper book, (C) verified lab shadow sleeve.
- For each claimed pick, say SUPPORT / WEAK / REJECT and cite which evidence block.
- Output markdown with sections: Verdict table, Stats explained (why each metric matters), ELI5 (one simple sentence per feedback point).

Claims to verify:
1. deepseek_v4 / gpt4o tournament models — paper watch only (leaderboard)
2. CRYPTO SHORT direction — EAGLE3 67% WR vs LONG 33% (n=216 tournament)
3. ETF symbols EEM, IWM, GLD — EAGLE3 symbol table (tournament, not production n=3)
4. EQUITY symbols BAC, JPM, MSFT, NVDA — EAGLE3 LONG bias (production EQUITY PF 0.33 FAIL)
5. ETF dual momentum lab — PF 1.60 n=104, WF PASS OOS PF 1.21 — shadow only until forward n>=30
6. Production /audit — 0 money_ready classes; CRYPTO NOT_READY PF 0.92

EVIDENCE:
{json.dumps(evidence, indent=2)[:16000]}
"""
    body = json.dumps(
        {
            "model": "hybrid-model",
            "messages": [
                {"role": "system", "content": "Quant auditor. No fabricated numbers."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 2500,
            "temperature": 0.1,
        }
    ).encode()
    req = urllib.request.Request(
        f"{PROXY}/chat/completions",
        data=body,
        headers={"Authorization": "Bearer local", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode())
    return data["choices"][0]["message"]["content"]


def main():
    evidence = build_evidence_pack()
    try:
        review = swarm_review(evidence)
        evidence["swarm_review_markdown"] = review
        evidence["swarm_ok"] = True
    except Exception as e:
        evidence["swarm_error"] = str(e)
        evidence["swarm_ok"] = False
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")
    if evidence.get("swarm_ok"):
        print(evidence["swarm_review_markdown"][:1200])


if __name__ == "__main__":
    main()
