#!/usr/bin/env python3
"""Daily Top-Picks Filter from AI Tournament Robust Panel.

Produces the curated daily real-money filter recommended in
`reports/weekly_filter_2026-06-03T23-02Z.md`. Pulls OPEN picks from
the 6 robust models that pass all 6 VETTED-STATS checks, ranks them
by a composite score (confidence + model PF), and emits the top N.

ROBUST PANEL (per money_ready_verdict + AI tournament leaderboard
audited 2026-06-03):
  deepseek_v4         n=271 WR=57.9% PF=3.50
  claude_haiku_4_5    n= 85 WR=69.4% PF=3.69
  cursor_agent        n=123 WR=65.0% PF=3.13
  gpt4o               n=265 WR=57.7% PF=2.90
  deepseek_r1         n=172 WR=61.1% PF=2.89
  mercury             n=110 WR=58.2% PF=2.77

⚠ ACTIVE DISPUTED BANNER on /audit/ai-tournament.html: these WR/PF
numbers were computed against a once-daily spot-snapshot resolver that
inflates WR by 10-20pts vs intrabar OHLC. As of 2026-06-04 the intrabar
fix is live (PRs #512, f273b6db57, 893c660c10, 4fd7cb4c69) but CRYPTO
REPLAY coverage is still being validated. Until CRYPTO REPLAY rows
land in DB at parity with non-crypto classes, treat sizing as paper-only.

Usage:
  python tools/daily_top_picks_filter.py                  # top 10, JSON
  python tools/daily_top_picks_filter.py --top 5           # top 5
  python tools/daily_top_picks_filter.py --asset CRYPTO    # CRYPTO only
  python tools/daily_top_picks_filter.py --markdown        # markdown table
  python tools/daily_top_picks_filter.py --kelly-cap 0.02  # cap Quarter-Kelly at 2%
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pymysql

# Per the operator's institutional sizing norm: never exceed 2% per pick
# regardless of Quarter-Kelly's mathematical answer. PF>2.5 + WR>57% +
# 2% SL implies Quarter-Kelly is ~10-13% — far above the prudent cap.
DEFAULT_KELLY_CAP_PCT = 0.02

# The 6 robust models that passed all 6 VETTED-STATS checks on 2026-06-03.
# Snapshot per audit_dashboard/data/ai_tournament_leaderboard.json. Each
# entry: {model_id: (n_resolved, wr_pct, pf, kelly_cap_pct_implied)}.
# Implied Kelly is from PF/WR assuming avg_loss=2% (typical SL distance).
ROBUST_PANEL = {
    "deepseek_v4":      {"n": 271, "wr": 0.579, "pf": 3.50, "raw_kelly": 0.1035},
    "claude_haiku_4_5": {"n": 85,  "wr": 0.694, "pf": 3.69, "raw_kelly": 0.1265},
    "cursor_agent":     {"n": 123, "wr": 0.650, "pf": 3.13, "raw_kelly": 0.1107},
    "gpt4o":            {"n": 265, "wr": 0.577, "pf": 2.90, "raw_kelly": 0.0947},
    "deepseek_r1":      {"n": 172, "wr": 0.611, "pf": 2.89, "raw_kelly": 0.0999},
    "mercury":          {"n": 110, "wr": 0.582, "pf": 2.77, "raw_kelly": 0.0930},
}

# Confidence string → numeric weight for ranking
CONFIDENCE_WEIGHT = {"HIGH": 1.0, "MEDIUM": 0.7, "LOW": 0.4}


def get_conn():
    """Connect to ejaguiar1_stocks via canonical helper (no hardcoded literals)."""
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    try:
        from tools.db_env import get_stocks_creds  # noqa: WPS433
        return pymysql.connect(**get_stocks_creds(), connect_timeout=20)
    except Exception:
        pw = os.environ.get("DB_PASS_STOCKS") or os.environ.get("MYSQL_PASSWORD")
        if not pw:
            print("ERR: no DB password resolvable (set DB_PASS_STOCKS)",
                  file=sys.stderr)
            sys.exit(2)
        return pymysql.connect(
            host="mysql.50webs.com", user="ejaguiar1_stocks",
            password=pw, database="ejaguiar1_stocks",
            port=3306, connect_timeout=20,
        )


def pull_open_picks_from_panel(conn, asset_class: str | None) -> list[dict]:
    """Get all OPEN picks from the robust panel."""
    model_ids = list(ROBUST_PANEL.keys())
    placeholders = ",".join(["%s"] * len(model_ids))
    sql = f"""SELECT id, model_id, asset_class, symbol, direction,
                     entry_price, take_profit, stop_loss, confidence,
                     thesis, submitted_at
              FROM tournament_picks
              WHERE status='OPEN'
                AND model_id IN ({placeholders})"""
    params: list = list(model_ids)
    if asset_class:
        sql += " AND asset_class = %s"
        params.append(asset_class.upper())
    sql += " ORDER BY submitted_at DESC LIMIT 500"
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute(sql, params)
        return list(cur.fetchall())


def score_pick(pick: dict) -> float:
    """Composite score: (model_PF * confidence_weight * recency_factor).

    Higher = better. Recency: picks submitted in last 24h get full weight,
    older picks get progressively less. Confidence: HIGH=1.0, MEDIUM=0.7,
    LOW=0.4. Model PF: the historical robust-panel PF for this model_id.
    """
    model_stats = ROBUST_PANEL.get(pick["model_id"], {})
    model_pf = float(model_stats.get("pf", 1.0))
    conf = CONFIDENCE_WEIGHT.get(
        str(pick.get("confidence", "")).upper(), 0.5,
    )
    # Recency: pick days = (now - submitted_at). Within 1d → 1.0, 7d → ~0.5,
    # 14d (max window) → ~0.0.
    try:
        if isinstance(pick.get("submitted_at"), str):
            ts = datetime.fromisoformat(pick["submitted_at"].replace("Z", "+00:00"))
        else:
            ts = pick["submitted_at"]
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - ts).total_seconds() / 86400
        recency = max(0.0, min(1.0, 1.0 - (age_days - 1) / 13)) if age_days > 1 else 1.0
    except Exception:
        recency = 0.5
    return model_pf * conf * recency


def position_size_pct(model_id: str, kelly_cap: float) -> float:
    """Return position size as fraction of account (capped at kelly_cap)."""
    raw = ROBUST_PANEL.get(model_id, {}).get("raw_kelly", 0.01)
    return min(raw, kelly_cap)


def render_markdown(picks: list[dict], kelly_cap: float) -> str:
    lines = [
        "# Daily Top-Picks Filter — " + datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "",
        f"Source: AI tournament robust panel (6 models, kelly_cap={kelly_cap*100:.1f}%)",
        "",
        "⚠ DISPUTED banner active on /audit/ai-tournament.html — these WR/PF",
        "values are from a once-daily snapshot resolver. CRYPTO intrabar fix",
        "is live (PRs #512/f273b6db57/893c660c10/4fd7cb4c69) but coverage",
        "still validating. Treat sizing as paper-only until institutional",
        "WR/PF parity verified.",
        "",
        "| # | Symbol | Class | Dir | Entry | TP | SL | Conf | Model | Size% | Thesis |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, p in enumerate(picks, 1):
        size = position_size_pct(p["model_id"], kelly_cap) * 100
        thesis = (p.get("thesis") or "")[:80].replace("|", "\\|")
        lines.append(
            f"| {i} | {p['symbol']} | {p['asset_class']} | "
            f"{p.get('direction','?')} | {p.get('entry_price','')} | "
            f"{p.get('take_profit','')} | {p.get('stop_loss','')} | "
            f"{p.get('confidence','?')} | {p['model_id']} | "
            f"{size:.2f}% | {thesis} |"
        )
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--top", type=int, default=10,
                    help="Number of picks to surface (default 10)")
    ap.add_argument("--asset", type=str, default=None,
                    help="Filter by asset_class (CRYPTO/EQUITY/ETF/etc)")
    ap.add_argument("--kelly-cap", type=float, default=DEFAULT_KELLY_CAP_PCT,
                    help="Cap per-pick size as fraction of account (default 0.02 = 2%%)")
    ap.add_argument("--markdown", action="store_true",
                    help="Emit markdown table instead of JSON")
    ap.add_argument("--out", type=str, default=None,
                    help="Output file (default: stdout)")
    args = ap.parse_args()

    conn = get_conn()
    try:
        all_picks = pull_open_picks_from_panel(conn, args.asset)
    finally:
        conn.close()

    # Deduplicate by (symbol, direction) — if multiple robust models agree
    # on the same trade, keep the highest-PF model's pick.
    by_key: dict[tuple, dict] = {}
    for p in all_picks:
        key = (p["symbol"], p["direction"])
        if key not in by_key:
            by_key[key] = p
        else:
            existing = ROBUST_PANEL.get(by_key[key]["model_id"], {}).get("pf", 0)
            new = ROBUST_PANEL.get(p["model_id"], {}).get("pf", 0)
            if new > existing:
                by_key[key] = p

    ranked = sorted(by_key.values(), key=score_pick, reverse=True)[:args.top]

    if args.markdown:
        out = render_markdown(ranked, args.kelly_cap)
    else:
        out = json.dumps({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "n_robust_panel_picks_open": len(all_picks),
            "n_after_dedup": len(by_key),
            "n_returned": len(ranked),
            "kelly_cap_pct": args.kelly_cap,
            "robust_panel": list(ROBUST_PANEL.keys()),
            "disputed_banner_active": True,
            "picks": [
                {**{k: (str(v) if isinstance(v, datetime) else v)
                    for k, v in p.items()},
                 "score": score_pick(p),
                 "size_pct": position_size_pct(p["model_id"], args.kelly_cap)}
                for p in ranked
            ],
        }, indent=2, default=str)

    if args.out:
        Path(args.out).write_text(out, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(out)


if __name__ == "__main__":
    main()
