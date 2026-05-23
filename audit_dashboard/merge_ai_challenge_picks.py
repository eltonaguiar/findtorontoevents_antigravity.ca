#!/usr/bin/env python3
"""
Merge 4 AI Challenge round picks into unified active_picks.json per curator.
Runs in audit-dashboard workflow to feed picks into dashboard_generator.py.

Each curator's round files (e.g. claude_top_picks_round1..round5.json) are
merged into a single flat-array active_picks.json that the dashboard can ingest.

Picks with outcome=PENDING or status=ACTIVE are treated as active.
Picks with outcome in (TP_HIT, SL_HIT, CLOSED) go to closed_picks.json.
"""
import json
import os
import glob
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent  # audit_dashboard/
DATA = ROOT / "data"

# Map curator prefix → system name for dashboard
CURATORS = {
    "claude":       "ai_challenge_claude",
    "grok":         "ai_challenge_grok",
    "kimi":         "ai_challenge_kimi_moonshot",
    "ag":           "ai_challenge_antigravity",
    "mercury":      "ai_challenge_mercury",
    "predictable":  "ai_challenge_predictable",
    "scanner":      "ai_challenge_scanner",
}


def _load_round_files(prefix: str) -> list:
    """Load all round files for a curator prefix, sorted by round number."""
    pattern = str(DATA / f"{prefix}_top_picks_round*.json")
    files = sorted(glob.glob(pattern))
    all_picks = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, FileNotFoundError):
            continue

        round_num = data.get("round", 0)
        curator_name = data.get("curator", prefix)
        generated_at = data.get("generated_at", "")
        methodology = data.get("methodology", "")

        # Extract picks array
        picks = data.get("picks", [])
        for p in picks:
            # Normalize to dashboard-expected schema
            pick = {
                "symbol": p.get("symbol", ""),
                "direction": p.get("direction", "LONG"),
                "signal_type": "BUY" if p.get("direction", "LONG") == "LONG" else "SELL",
                "entry_price": p.get("entry_price", 0),
                "take_profit": p.get("take_profit", 0),
                "stop_loss": p.get("stop_loss", 0),
                "confidence": p.get("confidence", 0.5),
                "strategy": p.get("strategy", "unknown"),
                "status": "OPEN" if p.get("outcome", "PENDING") == "PENDING" else "CLOSED",
                "outcome": p.get("outcome", "PENDING"),
                "pnl_pct": float(p.get("pnl_pct", 0) or 0),
                "round": round_num,
                "rank": p.get("rank", 0),
                "curator": curator_name,
                "methodology": methodology,
                "rationale": p.get("rationale", ""),
                "statistical_basis": p.get("statistical_basis", ""),
                "risk_reward": p.get("risk_reward", 0),
                "generated_at": generated_at,
                "ml_score": p.get("ml_score", p.get("confidence", 0.5)),
            }
            # Add kelly sizing if present
            kelly = p.get("kelly_sizing", {})
            if kelly:
                pick["position_pct"] = kelly.get("position_pct", 0)
                pick["quarter_kelly"] = kelly.get("quarter_kelly", 0)

            all_picks.append(pick)
    return all_picks


def merge_all():
    """Merge all curator round files into per-curator active/closed pick files."""
    timestamp = datetime.now(timezone.utc).isoformat()
    summary = {}

    for prefix, system_name in CURATORS.items():
        picks = _load_round_files(prefix)
        if not picks:
            continue

        active = [p for p in picks if p.get("outcome", "PENDING") == "PENDING"]
        closed = [p for p in picks if p.get("outcome", "PENDING") != "PENDING"]

        # Write active picks
        active_path = DATA / f"{system_name}_active_picks.json"
        with open(active_path, "w", encoding="utf-8") as f:
            json.dump(active, f, indent=2, default=str)

        # Write closed picks (if any)
        if closed:
            closed_path = DATA / f"{system_name}_closed_picks.json"
            with open(closed_path, "w", encoding="utf-8") as f:
                json.dump(closed, f, indent=2, default=str)

        summary[system_name] = {
            "active": len(active),
            "closed": len(closed),
            "total_rounds": len(set(p.get("round", 0) for p in picks)),
            "latest_round": max((p.get("round", 0) for p in picks), default=0),
        }
        print(f"  {system_name}: {len(active)} active, {len(closed)} closed from {summary[system_name]['total_rounds']} rounds")

    # Write summary
    summary_path = DATA / "ai_challenge_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({"generated_at": timestamp, "curators": summary}, f, indent=2)

    print(f"\nAI Challenge merge complete: {len(summary)} curators processed")
    return summary


if __name__ == "__main__":
    merge_all()
