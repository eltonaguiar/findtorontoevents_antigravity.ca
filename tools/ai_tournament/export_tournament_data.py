#!/usr/bin/env python3
"""
Export the rich AI-tournament DB tables to JSON for the static dashboard.

Reads tournament_picks / tournament_model_stats / tournament_gameplans /
tournament_persona_stats from ejaguiar1_stocks, re-skins the generic DB
persona slugs with our original personas (config/tournament_personas.json),
converts timestamps to EST, and writes:

  audit_dashboard/data/tournament_leaderboard.json
  audit_dashboard/data/tournament_picks.json
  audit_dashboard/data/tournament_personas.json
  audit_dashboard/data/tournament_gameplans.json

The DB tables are fed by an external generator; this exporter never mutates
them — the original-persona identity is a render-time overlay only.

Usage:  DB_PASS_STOCKS=... python tools/ai_tournament/export_tournament_data.py
"""
from __future__ import annotations
import json, os, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import pymysql
except ImportError:
    print("pymysql required: pip install pymysql"); sys.exit(1)

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "config" / "tournament_personas.json"
OUTDIR = REPO / "audit_dashboard" / "data"
EST = timezone(timedelta(hours=-4))  # America/New_York, EDT (May)


def to_est(val) -> str | None:
    """Parse a UTC ISO/MySQL datetime and return 'YYYY-MM-DD HH:MM EST'."""
    if not val:
        return None
    s = str(val).strip().replace("Z", "+00:00")
    for fmt in (None, "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.fromisoformat(s) if fmt is None else datetime.strptime(s[:19], fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(EST).strftime("%Y-%m-%d %H:%M EST")
        except (ValueError, TypeError):
            continue
    return None


def jsafe(v):
    """JSON-safe scalar (Decimal -> float, datetime -> iso)."""
    import decimal
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, datetime):
        return v.isoformat()
    return v


def parse_list(v):
    """entry_criteria etc. are stored as JSON-array strings."""
    if isinstance(v, list):
        return v
    if not v:
        return []
    try:
        out = json.loads(v)
        return out if isinstance(out, list) else [str(out)]
    except (json.JSONDecodeError, TypeError):
        return [s.strip() for s in str(v).split(";") if s.strip()]


def main() -> None:
    cfg = json.loads(CONFIG.read_text())
    personas = cfg["personas"]
    gmap = {k: v for k, v in cfg["generic_persona_map"].items() if not k.startswith("_")}

    def original(slug: str) -> str:
        """Generic DB persona slug -> our original persona id."""
        return gmap.get(slug, slug)

    pw = os.environ.get("DB_PASS_STOCKS", "")
    conn = pymysql.connect(host="mysql.50webs.com", user="ejaguiar1_stocks",
                           password=pw, database="ejaguiar1_stocks", port=3306,
                           connect_timeout=25, cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(timezone.utc).isoformat()

    # ---- picks ----
    cur.execute("""SELECT model_id, persona_id, asset_class, symbol, direction,
                          entry_price, take_profit, stop_loss, thesis, rationale,
                          strategy_name, entry_criteria, catalyst, exit_criteria,
                          risk_factors, confidence, timeframe, status, exit_price,
                          pnl_pct, exit_reason, submitted_at, resolved_at,
                          data_integrity_flag
                   FROM tournament_picks ORDER BY submitted_at DESC""")
    PER_MODEL_CAP = 25  # keep the page payload light; rows are DESC by submitted_at
    seen_per_model: dict[str, int] = {}
    picks = []
    for r in cur.fetchall():
        mid = r["model_id"]
        if seen_per_model.get(mid, 0) >= PER_MODEL_CAP:
            continue
        seen_per_model[mid] = seen_per_model.get(mid, 0) + 1
        op = original(r["persona_id"] or "")
        pinfo = personas.get(op, {})
        picks.append({
            "model_id": r["model_id"],
            "persona_id": op,
            "persona_name": pinfo.get("name", r["persona_id"]),
            "persona_category": pinfo.get("category", ""),
            "db_persona_slug": r["persona_id"],
            "asset_class": r["asset_class"],
            "symbol": r["symbol"],
            "direction": r["direction"],
            "entry_price": jsafe(r["entry_price"]),
            "take_profit": jsafe(r["take_profit"]),
            "stop_loss": jsafe(r["stop_loss"]),
            "thesis": r["thesis"] or "",
            "rationale": r["rationale"] or "",
            "strategy_name": pinfo.get("strategy_name", r["strategy_name"] or ""),
            "entry_criteria": parse_list(r["entry_criteria"]),
            "catalyst": r["catalyst"] or "",
            "exit_criteria": parse_list(r["exit_criteria"]),
            "risk_factors": parse_list(r["risk_factors"]),
            "confidence": r["confidence"] or "",
            "timeframe": r["timeframe"] or "",
            "status": r["status"],
            "exit_price": jsafe(r["exit_price"]),
            "pnl_pct": jsafe(r["pnl_pct"]),
            "exit_reason": r["exit_reason"] or "",
            "opened_at_est": to_est(r["submitted_at"]),
            "closed_at_est": to_est(r["resolved_at"]),
            "submitted_at": jsafe(r["submitted_at"]),
            "resolved_at": jsafe(r["resolved_at"]),
            "data_integrity_flag": r["data_integrity_flag"] or "",
        })
    (OUTDIR / "tournament_picks.json").write_text(json.dumps(
        {"generated_at": generated, "n_picks": len(picks), "picks": picks}, indent=1))
    print(f"tournament_picks.json: {len(picks)} picks")

    # ---- model leaderboard ----
    cur.execute("""SELECT model_id, provider, persona_count, asset_class_coverage,
                          n_picks, n_resolved, n_wins, n_losses, wr, wr_ci_lo, wr_ci_hi,
                          pf, pf_ci_lo, pf_ci_hi, score, tier, rank_position,
                          expected_return, sharpe FROM tournament_model_stats
                   ORDER BY score DESC""")
    models = []
    for r in cur.fetchall():
        models.append({k: jsafe(v) for k, v in r.items()})
    (OUTDIR / "tournament_leaderboard.json").write_text(json.dumps(
        {"generated_at": generated, "n_models": len(models),
         "min_n_to_rank": 30, "scoring_formula": "lower95(WR) x lower95(PF)",
         "models": models}, indent=1))
    print(f"tournament_leaderboard.json: {len(models)} models")

    # ---- gameplans ----
    cur.execute("""SELECT model_id, persona_id, asset_class, philosophy,
                          timeframe_pref, entry_conditions, tp_methodology,
                          sl_methodology, exit_triggers, position_sizing,
                          max_risk_per_trade, preferred_markets, asset_class_notes
                   FROM tournament_gameplans""")
    gameplans = []
    for r in cur.fetchall():
        op = original(r["persona_id"] or "")
        gameplans.append({
            "model_id": r["model_id"],
            "persona_id": op,
            "persona_name": personas.get(op, {}).get("name", r["persona_id"]),
            "asset_class": r["asset_class"],
            "philosophy": r["philosophy"] or "",
            "timeframe_pref": r["timeframe_pref"] or "",
            "entry_conditions": parse_list(r["entry_conditions"]),
            "tp_methodology": r["tp_methodology"] or "",
            "sl_methodology": r["sl_methodology"] or "",
            "exit_triggers": parse_list(r["exit_triggers"]),
            "position_sizing": r["position_sizing"] or "",
            "max_risk_per_trade": r["max_risk_per_trade"] or "",
            "preferred_markets": parse_list(r["preferred_markets"]),
            "asset_class_notes": r["asset_class_notes"] or "",
        })
    (OUTDIR / "tournament_gameplans.json").write_text(json.dumps(
        {"generated_at": generated, "n_gameplans": len(gameplans),
         "gameplans": gameplans}, indent=1))
    print(f"tournament_gameplans.json: {len(gameplans)} gameplans")

    # ---- persona roster + aggregate stats ----
    cur.execute("""SELECT persona_id, asset_class, SUM(n_picks) n_picks,
                          SUM(n_resolved) n_resolved, SUM(n_wins) n_wins,
                          SUM(n_losses) n_losses FROM tournament_persona_stats
                   GROUP BY persona_id, asset_class""")
    agg: dict[str, dict] = {}
    for r in cur.fetchall():
        op = original(r["persona_id"] or "")
        a = agg.setdefault(op, {"n_picks": 0, "n_resolved": 0, "n_wins": 0,
                                "n_losses": 0, "asset_classes": set()})
        a["n_picks"] += int(r["n_picks"] or 0)
        a["n_resolved"] += int(r["n_resolved"] or 0)
        a["n_wins"] += int(r["n_wins"] or 0)
        a["n_losses"] += int(r["n_losses"] or 0)
        if r["asset_class"]:
            a["asset_classes"].add(r["asset_class"])

    roster = []
    for pid, pinfo in personas.items():
        a = agg.get(pid, {})
        nres = a.get("n_resolved", 0)
        roster.append({
            "id": pid,
            "name": pinfo["name"],
            "category": pinfo["category"],
            "tagline": pinfo["tagline"],
            "philosophy": pinfo["philosophy"],
            "signature_metrics": pinfo["signature_metrics"],
            "asset_focus": pinfo["asset_focus"],
            "risk_posture": pinfo["risk_posture"],
            "preferred_timeframe": pinfo["preferred_timeframe"],
            "strategy_name": pinfo["strategy_name"],
            "n_picks": a.get("n_picks", 0),
            "n_resolved": nres,
            "n_wins": a.get("n_wins", 0),
            "wr": round(a.get("n_wins", 0) / nres, 4) if nres else None,
            "active_asset_classes": sorted(a.get("asset_classes", [])),
        })
    (OUTDIR / "tournament_personas.json").write_text(json.dumps(
        {"generated_at": generated, "schema_version": cfg["schema_version"],
         "attribution": cfg["attribution"], "categories": cfg["categories"],
         "n_personas": len(roster), "personas": roster}, indent=1))
    print(f"tournament_personas.json: {len(roster)} personas")

    # ---- winner patterns ----
    cur.execute("""SELECT pattern_name, pattern_type, description, observed_wr,
                          sample_size, confidence_score, model_ids, persona_ids,
                          asset_classes, first_observed, last_observed
                   FROM tournament_winner_patterns ORDER BY confidence_score DESC, sample_size DESC""")
    patterns = []
    for r in cur.fetchall():
        patterns.append({
            "pattern_name": r["pattern_name"],
            "pattern_type": r["pattern_type"],
            "description": r["description"] or "",
            "observed_wr": jsafe(r["observed_wr"]),
            "sample_size": int(r["sample_size"] or 0),
            "confidence_score": jsafe(r["confidence_score"]),
            "model_ids": parse_list(r["model_ids"]),
            "persona_ids": parse_list(r["persona_ids"]),
            "asset_classes": parse_list(r["asset_classes"]),
            "first_observed": jsafe(r["first_observed"]),
            "last_observed": jsafe(r["last_observed"]),
        })
    (OUTDIR / "tournament_winner_patterns.json").write_text(json.dumps(
        {"generated_at": generated, "n_patterns": len(patterns),
         "caveat": ("Patterns flagged by the tournament's pattern-derivation pass over the "
                    "synthetic-seed pool. Sample sizes and confidence_score vary widely — "
                    "tiny-n patterns are research signal, not evidence. Read the n and "
                    "confidence columns before reading the WR."),
         "patterns": patterns}, indent=1))
    print(f"tournament_winner_patterns.json: {len(patterns)} patterns")

    conn.close()
    print("export complete.")


if __name__ == "__main__":
    main()
