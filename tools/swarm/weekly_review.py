"""Weekly swarm-pick review.

Reads `audit_dashboard/data/swarm_picks.json`, computes per-consensus-tier
and per-model win-rate + profit-factor + R-multiple over the last 7 days
(default; override via --days). Writes:
- `reports/swarm_review/YYYY_WW.md` (human-readable summary)
- `audit_dashboard/data/swarm_leaderboard.json` (model -> live WR/PF for
  future fanouts to weight by)

Run: `python tools/swarm/weekly_review.py [--days N] [--all]`
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.swarm.swarm_pick_schema import load_store, atomic_write_store

STORE_PATH = REPO_ROOT / "audit_dashboard" / "data" / "swarm_picks.json"
LEADERBOARD_PATH = REPO_ROOT / "audit_dashboard" / "data" / "swarm_leaderboard.json"
REPORTS_DIR = REPO_ROOT / "reports" / "swarm_review"


def _pnl_pct(p: dict) -> float | None:
    o = p.get("outcome")
    if o is None:
        return None
    return o.get("pnl_pct")


def _win(p: dict) -> bool | None:
    pnl = _pnl_pct(p)
    if pnl is None:
        return None
    return pnl > 0


def _stats(picks: list[dict]) -> dict:
    resolved = [p for p in picks if _win(p) is not None]
    wins = [p for p in resolved if _win(p)]
    losses = [p for p in resolved if not _win(p)]
    gross_win = sum(_pnl_pct(p) for p in wins if _pnl_pct(p) is not None)
    gross_loss = abs(sum(_pnl_pct(p) for p in losses if _pnl_pct(p) is not None))
    wr = len(wins) / len(resolved) * 100 if resolved else 0.0
    pf = gross_win / gross_loss if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0)
    return {
        "n_total": len(picks),
        "n_resolved": len(resolved),
        "n_open": len(picks) - len(resolved),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(wr, 1),
        "profit_factor": round(pf, 2) if pf != float("inf") else None,
        "gross_win_pct": round(gross_win, 2),
        "gross_loss_pct": round(gross_loss, 2),
    }


def _per_tier(picks: list[dict]) -> dict[str, dict]:
    by_tier: dict[str, list[dict]] = defaultdict(list)
    for p in picks:
        by_tier[p["consensus_tier"]].append(p)
    return {t: _stats(ps) for t, ps in by_tier.items()}


def _per_class(picks: list[dict]) -> dict[str, dict]:
    by_class: dict[str, list[dict]] = defaultdict(list)
    for p in picks:
        by_class[p["asset_class"]].append(p)
    return {c: _stats(ps) for c, ps in by_class.items()}


def _per_model(picks: list[dict]) -> tuple[dict[str, dict], dict[str, dict]]:
    """Returns ({persona_name -> stats}, {underlying_model -> stats}).

    A model's pick is counted as WIN if its vote matched the pick's filled
    direction AND the pick won. LOSS if its vote matched direction AND pick
    lost. Picks where the model voted SKIP or against direction are excluded
    from that model's resolved set.
    """
    persona_picks: dict[str, list[tuple[dict, str]]] = defaultdict(list)
    model_picks: dict[str, list[tuple[dict, str]]] = defaultdict(list)
    for p in picks:
        direction = p["direction"]
        for v in p["models_consulted"]:
            if v["vote"] != direction:
                continue
            persona_picks[v["name"]].append((p, "agree"))
            model_picks[v.get("underlying_model", "unknown")].append((p, "agree"))

    def stats_for(rows: list[tuple[dict, str]]) -> dict:
        ps = [p for p, _ in rows]
        return _stats(ps)

    return ({k: stats_for(v) for k, v in persona_picks.items()},
            {k: stats_for(v) for k, v in model_picks.items()})


def _filter_window(picks: list[dict], days: int | None) -> list[dict]:
    if days is None:
        return picks
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out = []
    for p in picks:
        try:
            t = datetime.fromisoformat(p["created_at"])
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            if t >= cutoff:
                out.append(p)
        except Exception:
            continue
    return out


def write_report(picks: list[dict], window_label: str, out_path: Path) -> None:
    overall = _stats(picks)
    by_tier = _per_tier(picks)
    by_class = _per_class(picks)
    by_persona, by_model = _per_model(picks)

    lines = [f"# Swarm Pick Weekly Review — {window_label}",
             f"\nGenerated: {datetime.now(timezone.utc).isoformat()}",
             f"\n## Overall ({overall['n_total']} picks, {overall['n_resolved']} resolved, {overall['n_open']} open)\n",
             f"- Win rate: {overall['win_rate_pct']}%",
             f"- Profit factor: {overall['profit_factor']}",
             f"- Wins / Losses: {overall['wins']} / {overall['losses']}",
             f"- Gross win pct: {overall['gross_win_pct']}, gross loss pct: {overall['gross_loss_pct']}\n"]

    lines.append("## Per consensus tier\n")
    lines.append("| Tier | n | resolved | WR% | PF | wins | losses |")
    lines.append("|---|---|---|---|---|---|---|")
    for tier in ["unanimous", "strong", "moderate", "single", "control"]:
        s = by_tier.get(tier)
        if s:
            lines.append(f"| {tier} | {s['n_total']} | {s['n_resolved']} | {s['win_rate_pct']} | {s['profit_factor']} | {s['wins']} | {s['losses']} |")

    lines.append("\n## Per asset class\n")
    lines.append("| Class | n | resolved | WR% | PF | wins | losses |")
    lines.append("|---|---|---|---|---|---|---|")
    for c, s in sorted(by_class.items()):
        lines.append(f"| {c} | {s['n_total']} | {s['n_resolved']} | {s['win_rate_pct']} | {s['profit_factor']} | {s['wins']} | {s['losses']} |")

    lines.append("\n## Per persona (vote-agreed with filled direction)\n")
    lines.append("| Persona | agreed_picks | resolved | WR% | PF |")
    lines.append("|---|---|---|---|---|")
    for name, s in sorted(by_persona.items(), key=lambda kv: -kv[1].get("win_rate_pct", 0)):
        lines.append(f"| {name} | {s['n_total']} | {s['n_resolved']} | {s['win_rate_pct']} | {s['profit_factor']} |")

    lines.append("\n## Per underlying model\n")
    lines.append("| Model | agreed_picks | resolved | WR% | PF |")
    lines.append("|---|---|---|---|---|")
    for m, s in sorted(by_model.items(), key=lambda kv: -kv[1].get("win_rate_pct", 0)):
        lines.append(f"| {m} | {s['n_total']} | {s['n_resolved']} | {s['win_rate_pct']} | {s['profit_factor']} |")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_leaderboard(picks: list[dict], path: Path) -> None:
    _, by_model = _per_model(picks)
    by_persona, _ = _per_model(picks)
    overall = _stats(picks)
    path.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall": overall,
        "by_persona": by_persona,
        "by_underlying_model": by_model,
        "by_tier": _per_tier(picks),
        "by_asset_class": _per_class(picks),
    }, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7, help="Rolling window days (default 7)")
    parser.add_argument("--all", action="store_true", help="All-time (override --days)")
    args = parser.parse_args()

    picks = load_store(STORE_PATH)
    if not picks:
        print("No picks in store.")
        return

    window_days = None if args.all else args.days
    windowed = _filter_window(picks, window_days)
    now = datetime.now(timezone.utc)
    iso = now.isocalendar()
    label = "all-time" if args.all else f"{iso.year}_W{iso.week:02d}"
    out_path = REPORTS_DIR / f"{label}.md"
    write_report(windowed, label, out_path)
    write_leaderboard(windowed, LEADERBOARD_PATH)
    print(f"Report: {out_path}")
    print(f"Leaderboard: {LEADERBOARD_PATH}")
    print(f"Window: {label} ({len(windowed)} picks of {len(picks)} total)")


if __name__ == "__main__":
    main()
