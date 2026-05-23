#!/usr/bin/env python3
"""Aggregate closed picks from JSON_PICK_SOURCES; rank strategies by asset class (real data).

Usage (repo root):
  python tools/research_strategy_by_asset_class.py
  python tools/research_strategy_by_asset_class.py --min-trades 15 --top 4 --json

Output: stdout summary; optional --json for structured top picks.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from audit_trail.dashboard_generator import (  # noqa: E402
    JSON_PICK_SOURCES,
    _derive_asset_class,
)


def _load_closed_list(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return []
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if isinstance(raw, dict):
        for k in ("picks", "closed", "trades", "data"):
            v = raw.get(k)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
    return []


def _pick_uid(pick: dict, source_system: str) -> str:
    pid = pick.get("id") or pick.get("pick_id") or ""
    sym = str(pick.get("symbol") or "")
    ts = str(pick.get("closed_at") or pick.get("timestamp") or pick.get("exit_date") or "")
    strat = str(pick.get("strategy") or "")
    return f"{source_system}|{pid}|{sym}|{ts}|{strat}"


def _pnl_pct(pick: dict) -> float:
    for k in ("pnl_pct", "realized_pnl_pct", "pnlPct", "exit_pnl_pct"):
        if pick.get(k) is None:
            continue
        try:
            return float(pick[k])
        except (TypeError, ValueError):
            continue
    return 0.0


def _is_resolved(pick: dict) -> bool:
    pnl = _pnl_pct(pick)
    st = str(pick.get("status") or pick.get("outcome") or "").upper()
    if st in ("OPEN", "PENDING"):
        return False
    if st in ("WIN", "LOSS", "TP_HIT", "SL_HIT", "CLOSED", "RESOLVED"):
        return True
    return pnl != 0.0


def _row_stats(rows: list[dict]) -> tuple[int, float, float, float]:
    """resolved_count, win_rate_pct, profit_factor, total_pnl."""
    wins = losses = 0
    gw = gl = 0.0
    pnl_sum = 0.0
    for p in rows:
        x = _pnl_pct(p)
        pnl_sum += x
        if x > 0:
            wins += 1
            gw += x
        elif x < 0:
            losses += 1
            gl += abs(x)
    resolved = wins + losses
    wr = (100.0 * wins / resolved) if resolved else 0.0
    pf = (gw / gl) if gl > 0 else (99.0 if gw > 0 else 0.0)
    return resolved, wr, pf, pnl_sum


def collect_picks() -> list[tuple[str, dict]]:
    """List of (source_system, pick)."""
    out: list[tuple[str, dict]] = []
    for entry in JSON_PICK_SOURCES:
        if len(entry) == 3:
            sys_name, _active, closed_rel = entry
        else:
            continue
        if not closed_rel:
            continue
        path = ROOT / closed_rel
        for pick in _load_closed_list(path):
            out.append((sys_name, pick))
    return out


def aggregate_asset_classes(
    min_trades: int,
) -> dict[str, dict]:
    """Roll up deduped resolved picks by asset_class (for reliability comparison)."""
    seen: set[str] = set()
    by_ac: dict[str, list[dict]] = defaultdict(list)

    for source_system, pick in collect_picks():
        if not _is_resolved(pick):
            continue
        uid = _pick_uid(pick, source_system)
        if uid in seen:
            continue
        seen.add(uid)
        sym = str(pick.get("symbol") or "")
        strat = str(pick.get("strategy") or "").strip()
        ac = _derive_asset_class(sym, pick, source_system, strat or "unknown")
        by_ac[ac].append(pick)

    out: dict[str, dict] = {}
    for ac, picks in sorted(by_ac.items()):
        n, wr, pf, pnl = _row_stats(picks)
        if n < min_trades:
            continue
        out[ac] = {
            "asset_class": ac,
            "resolved_trades": n,
            "win_rate_pct": round(wr, 2),
            "profit_factor": round(min(pf, 99.0), 2),
            "total_pnl_pct": round(pnl, 1),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-trades", type=int, default=12)
    ap.add_argument("--top", type=int, default=4)
    ap.add_argument(
        "--min-wr",
        type=float,
        default=0.0,
        help="Minimum win rate %% (0=off). E.g. 50 for HF-style cut.",
    )
    ap.add_argument(
        "--min-pf",
        type=float,
        default=0.0,
        help="Minimum profit factor (0=off). E.g. 1.05 for edge cut.",
    )
    ap.add_argument(
        "--asset-summary",
        action="store_true",
        help="Print aggregate WR/PF by asset class (deduped closed picks), then exit.",
    )
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.asset_summary:
        agg = aggregate_asset_classes(args.min_trades)
        if args.json:
            print(json.dumps(agg, indent=2))
            return 0
        print(
            "Asset-class rollup (deduped, min_trades=%s, pnl>0=win)\n"
            % args.min_trades
        )
        rows = sorted(
            agg.values(),
            key=lambda r: (r["win_rate_pct"], r["resolved_trades"]),
            reverse=True,
        )
        for r in rows:
            print(
                "  %(asset_class)s | n=%(resolved_trades)s WR=%(win_rate_pct)s%% "
                "PF=%(profit_factor)s total_pnl%%=%(total_pnl_pct)s"
                % r
            )
        if not rows:
            print("  (no asset class met min_trades — try --min-trades 5)")
        return 0

    seen: set[str] = set()
    by_ac_strat: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))

    for source_system, pick in collect_picks():
        if not _is_resolved(pick):
            continue
        uid = _pick_uid(pick, source_system)
        if uid in seen:
            continue
        seen.add(uid)
        sym = str(pick.get("symbol") or "")
        strat = str(pick.get("strategy") or "").strip()
        if not strat:
            continue
        ac = _derive_asset_class(sym, pick, source_system, strat)
        by_ac_strat[ac][strat].append(pick)

    ranking: dict[str, list[dict]] = {}
    for ac, strats in sorted(by_ac_strat.items()):
        rows = []
        for strat, picks in strats.items():
            n, wr, pf, pnl = _row_stats(picks)
            if n < args.min_trades:
                continue
            if args.min_wr > 0 and wr + 1e-6 < args.min_wr:
                continue
            if args.min_pf > 0 and pf + 1e-6 < args.min_pf:
                continue
            score = wr * min(3.0, (pf ** 0.35)) if pf > 0 else wr
            rows.append(
                {
                    "asset_class": ac,
                    "strategy": strat[:56] + ("..." if len(strat) > 56 else ""),
                    "strategy_full": strat,
                    "trades": n,
                    "wr_pct": round(wr, 1),
                    "pf": round(min(pf, 99.0), 2),
                    "total_pnl_pct": round(pnl, 1),
                    "score": round(score, 2),
                }
            )
        rows.sort(key=lambda r: (r["score"], r["trades"], r["pf"]), reverse=True)
        ranking[ac] = rows[: args.top]

    if args.json:
        print(json.dumps(ranking, indent=2))
        return 0

    print("Strategy research by asset class (closed JSON feeds, deduped, min_trades=%s)" % args.min_trades)
    print("sources: JSON_PICK_SOURCES closed paths; asset via _derive_asset_class\n")
    for ac in sorted(ranking.keys()):
        top = ranking[ac]
        if not top:
            continue
        print("=== %s (top %s) ===" % (ac, args.top))
        for i, r in enumerate(top, 1):
            print(
                "  %d. %s | n=%s WR=%s%% PF=%s pnl=%s%%"
                % (i, r["strategy"], r["trades"], r["wr_pct"], r["pf"], r["total_pnl_pct"])
            )
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
