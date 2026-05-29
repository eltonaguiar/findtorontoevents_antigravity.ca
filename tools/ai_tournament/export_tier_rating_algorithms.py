#!/usr/bin/env python3
"""
export_tier_rating_algorithms.py — DB → JSON exporter for the AI-tournament
"tier-rating algorithms" panel on /audit/ai-tournament.html.

The page fetches data/tier_rating_algorithms.json and renders one card per
(model × asset_class). That file was a MANUAL capture and went missing, so the
panel is stuck on its loading spinner. This exports the live source table
`tournament_rating_algorithms` (ejaguiar1_stocks) into the exact shape the page
expects: {"entries":[{model_id, asset_class, algorithm, features:[...]}]}.

Run in CI (ai-tournament-pipeline.yml) so the panel auto-refreshes daily.
Usage: python3 tools/ai_tournament/export_tier_rating_algorithms.py [--out PATH]
"""
from __future__ import annotations
import argparse, json, sys, pathlib as _pl
sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[2]))
from datetime import datetime, timezone
from pathlib import Path

OUT_DEFAULT = Path("audit_dashboard/data/tier_rating_algorithms.json")

def _features_to_list(features_raw):
    """features column is a JSON string with weights + per-feature defs → readable list."""
    try:
        f = json.loads(features_raw) if isinstance(features_raw, str) else (features_raw or {})
    except Exception:
        return []
    out = []
    feats = f.get("features") if isinstance(f, dict) else None
    if isinstance(feats, list):
        for it in feats:
            if isinstance(it, dict):
                nm = it.get("name", "?"); w = it.get("weight")
                out.append(f"{nm} ({w}%)" if w is not None else str(nm))
    elif isinstance(f, dict) and isinstance(f.get("weights"), dict):
        out = [f"{k} ({v}%)" for k, v in f["weights"].items()]
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    ap.add_argument("--generated-at", default=None, help="ISO ts (CI passes one); else now()")
    args = ap.parse_args()
    from tools.db_env import get_stocks_creds
    import pymysql
    conn = pymysql.connect(**get_stocks_creds()); cur = conn.cursor()
    cur.execute("DESCRIBE tournament_rating_algorithms")
    cols = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT * FROM tournament_rating_algorithms ORDER BY asset_class, model_id")
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    entries = []
    for r in rows:
        algo_bits = []
        if r.get("signature_insight"): algo_bits.append(str(r["signature_insight"]))
        try:
            fj = json.loads(r["features"]) if isinstance(r.get("features"), str) else {}
            if isinstance(fj, dict) and fj.get("scoring"): algo_bits.append(f"scoring: {fj['scoring']}")
        except Exception:
            pass
        entries.append({
            "model_id": r.get("model_id"),
            "asset_class": r.get("asset_class"),
            "provider": r.get("provider"),
            "algorithm": " — ".join(algo_bits) if algo_bits else (r.get("source_ref") or ""),
            "features": _features_to_list(r.get("features")),
            "floor_score": r.get("floor_score"),
            "source_ref": r.get("source_ref"),
        })
    payload = {
        "schema_version": "tier-rating/v1",
        "generated_at": args.generated_at or (datetime.now(timezone.utc).isoformat()),
        "source": "tournament_rating_algorithms (ejaguiar1_stocks)",
        "n": len(entries),
        "entries": entries,
    }
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    print(f"wrote {out} — {len(entries)} entries across "
          f"{len(set(e['asset_class'] for e in entries))} asset classes, "
          f"{len(set(e['model_id'] for e in entries))} models")

if __name__ == "__main__":
    main()
