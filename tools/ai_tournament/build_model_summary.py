"""
Build ai_tournament_model_summary.json from ai_tournament_picks_latest.json.

The model summary table on /audit/ai-tournament.html consumes this file.
Previously hand-maintained — now regenerated nightly by the AI tournament
pipeline workflow so it can't go stale relative to the picks snapshot.

Output schema (consumed by audit_dashboard/ai-tournament.html::loadModelSummary):
{
  "generated_at": ISO-8601 UTC,
  "n_models": int,
  "n_picks_total": int,
  "n_resolved": int,
  "models": [
    { model_id, total_picks, resolved, wins, losses,
      win_rate_pct, avg_pnl_pct, last_pick, personas, asset_classes }, ...
  ]
}
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PICKS = REPO / "audit_dashboard" / "data" / "ai_tournament_picks_latest.json"
OUT = REPO / "audit_dashboard" / "data" / "ai_tournament_model_summary.json"
CONFIG = REPO / "config" / "model_persona_mapping.json"


def _pnl(p: dict) -> float | None:
    for k in ("pnl_pct", "unrealized_pnl_pct"):
        v = p.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def _rank_excluded(p: dict) -> bool:
    return p.get("rank_eligible", True) is False or p.get("generation_source") == "coverage_fallback"


def _new_model(model_id: str, provider: str = "", declared: bool = False) -> dict:
    return {
        "model_id": model_id,
        "provider": provider,
        "total_picks": 0,
        "scored_picks": 0,
        "coverage_fallback_picks": 0,
        "resolved": 0,
        "wins": 0,
        "losses": 0,
        "_pnls": [],
        "_personas": set(),
        "_classes": set(),
        "last_pick": None,
        "has_data": False,
        "_declared": declared,
    }


def build() -> dict:
    picks = json.loads(PICKS.read_text()) if PICKS.exists() else []
    by_model: dict[str, dict] = {}

    if CONFIG.exists():
        try:
            cfg = json.loads(CONFIG.read_text())
            for mid, model_cfg in (cfg.get("models") or {}).items():
                by_model[mid] = _new_model(mid, model_cfg.get("provider", ""), declared=True)
        except Exception:
            pass

    for p in picks:
        mid = p.get("model_id") or "unknown"
        m = by_model.setdefault(mid, _new_model(mid, p.get("provider", ""), declared=False))
        if p.get("provider") and not m.get("provider"):
            m["provider"] = p.get("provider")
        m["has_data"] = True
        m["total_picks"] += 1
        if p.get("persona_id"):
            m["_personas"].add(p["persona_id"])
        if p.get("asset_class"):
            m["_classes"].add(p["asset_class"])
        ts = p.get("submitted_at") or ""
        if ts and (m["last_pick"] is None or ts > m["last_pick"]):
            m["last_pick"] = ts
        if _rank_excluded(p):
            m["coverage_fallback_picks"] += 1
            continue
        m["scored_picks"] += 1
        status = p.get("status")
        if status in ("WIN", "LOSS", "EXPIRED"):
            m["resolved"] += 1
            pnl = _pnl(p)
            if pnl is not None:
                m["_pnls"].append(pnl)
            if status == "WIN" or (pnl is not None and pnl > 0):
                m["wins"] += 1
            else:
                m["losses"] += 1

    out_models = []
    for m in by_model.values():
        resolved = m["resolved"]
        wins = m["wins"]
        pnls = m["_pnls"]
        out_models.append(
            {
                "model_id": m["model_id"],
                "provider": m["provider"],
                "total_picks": m["total_picks"],
                "scored_picks": m["scored_picks"],
                "coverage_fallback_picks": m["coverage_fallback_picks"],
                "resolved": resolved,
                "wins": wins,
                "losses": m["losses"],
                "win_rate_pct": round(100.0 * wins / resolved, 1) if resolved else 0.0,
                "avg_pnl_pct": round(sum(pnls) / len(pnls), 2) if pnls else 0.0,
                "last_pick": m["last_pick"],
                "personas": len(m["_personas"]),
                "asset_classes": len(m["_classes"]),
                "has_data": m["has_data"],
            }
        )
    out_models.sort(key=lambda x: (x["total_picks"], x["model_id"]), reverse=True)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_models": len(out_models),
        "n_picks_total": sum(m["total_picks"] for m in out_models),
        "n_scored_picks": sum(m["scored_picks"] for m in out_models),
        "n_coverage_fallback_picks": sum(m["coverage_fallback_picks"] for m in out_models),
        "n_resolved": sum(m["resolved"] for m in out_models),
        "models": out_models,
    }


def main() -> None:
    if not PICKS.exists():
        print(f"[model_summary] no picks file at {PICKS} — writing configured model shell")
    summary = build()
    OUT.write_text(json.dumps(summary, indent=2))
    print(
        f"[model_summary] wrote {OUT.relative_to(REPO)} "
        f"({summary['n_models']} models, {summary['n_picks_total']} picks, "
        f"{summary['n_resolved']} resolved)"
    )


if __name__ == "__main__":
    main()
