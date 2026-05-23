#!/usr/bin/env python3
"""
Walk-forward grid search on score × trust × forward WR (stdlib only).

Maps closed_picks.json fields: score, trust_score|trust_score_1, strat_fwd_wr|forward_wr,
pnl_pct, exit_time. Thresholds are exploratory — not the same as HF tier rules.

  python tools/walk_forward_thresholds.py
  python tools/walk_forward_thresholds.py --json-out audit_trail/data/walk_forward_report.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from itertools import product
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _parse_exit_dt(p: dict) -> datetime | None:
    for key in ("exit_time", "closed_at", "close_date"):
        raw = p.get(key)
        if not raw:
            continue
        s = str(raw).replace("Z", "+00:00")
        if "T" not in s and " " in s:
            s = s.replace(" ", "T")
        try:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                dt = dt.replace(tzinfo=None)
            return dt
        except (ValueError, TypeError):
            continue
    return None


def _wr(outcomes: list[float]) -> float:
    return sum(outcomes) / len(outcomes) if outcomes else 0.0


def _pnl_stats(pnls: list[float]) -> dict[str, float]:
    if not pnls:
        return {"expectancy": 0.0, "profit_factor": 0.0}
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gp = sum(wins)
    gl = abs(sum(losses))
    return {
        "expectancy": round(sum(pnls) / len(pnls), 6),
        "profit_factor": round(gp / gl, 4) if gl > 1e-12 else float("inf"),
    }


def _row_fields(r: dict) -> tuple[float, float, float, float, bool]:
    """Map closed-book rows to score / trust / forward-WR for threshold search.

    Many exports leave ``score`` and ``trust_score`` at 0; we fall back to
    ``ml_composite_score`` / ``elite_score`` and ``consensus_pct`` (scaled to 0–5).
    """
    sc = float(r.get("score") or 0)
    if sc <= 0:
        sc = float(r.get("ml_composite_score") or r.get("elite_score") or 0)
    tr = float(r.get("trust_score") or r.get("trust_score_1") or 0)
    if tr <= 0 and r.get("consensus_pct") is not None:
        tr = float(r.get("consensus_pct") or 0) * 5.0
    fw = float(r.get("strat_fwd_wr") or r.get("forward_wr") or 0)
    if fw > 1.5:
        fw = fw / 100.0
    pnl = float(r.get("pnl_pct") or 0)
    won = pnl > 0
    return sc, tr, fw, pnl, won


def optimize_thresholds(
    rows: list[dict],
    *,
    score_range: range | None = None,
    trust_range: range | None = None,
    fwd_wr_range: list[float] | None = None,
    min_trades: int = 10,
) -> dict[str, Any] | None:
    # Include 0: many closed-book exports have score unset (0); thresholds then reduce to trust/fwd.
    score_range = score_range or range(0, 86, 5)
    trust_range = trust_range or range(0, 7)
    fwd_wr_range = fwd_wr_range or [
        0.0,
        0.05,
        0.10,
        0.20,
        0.30,
        0.35,
        0.38,
        0.40,
        0.45,
        0.50,
        0.55,
    ]

    best: dict[str, Any] | None = None
    best_score = -1e9

    n_rows = len(rows) or 1
    for sc_min, tr_min, fw_min in product(score_range, trust_range, fwd_wr_range):
        selected: list[dict] = []
        for r in rows:
            sc, tr, fw, _, _ = _row_fields(r)
            if sc >= sc_min and tr >= tr_min and fw >= fw_min:
                selected.append(r)
        if len(selected) < min_trades:
            continue

        pnls = [float(x.get("pnl_pct") or 0) for x in selected]
        outcomes = [1.0 if p > 0 else 0.0 for p in pnls]
        wr = _wr(outcomes)
        stats = _pnl_stats(pnls)
        mean_pnl = sum(pnls) / len(pnls)
        var = sum((p - mean_pnl) ** 2 for p in pnls) / len(pnls)
        std = var**0.5
        sharpe = mean_pnl / (std + 1e-8)
        composite = sharpe * 100 + wr * 10 + len(selected) * 0.01
        # Penalize trivial "take ~all rows" when thresholds are all at floor (no real filter).
        frac = len(selected) / n_rows
        if sc_min == 0 and tr_min == 0 and fw_min == 0.0 and frac > 0.92:
            composite -= 500.0

        if composite > best_score:
            best_score = composite
            best = {
                "min_score": sc_min,
                "min_trust": tr_min,
                "min_fwd_wr": fw_min,
                "n_trades": len(selected),
                "win_rate": round(wr, 4),
                **stats,
                "sharpe_proxy": round(sharpe, 4),
            }

    return best


def walk_forward(
    rows: list[dict],
    *,
    train_days: int = 60,
    test_days: int = 21,
) -> list[dict[str, Any]]:
    dated: list[tuple[datetime, dict]] = []
    for r in rows:
        dt = _parse_exit_dt(r)
        if dt is None:
            continue
        dated.append((dt, r))
    dated.sort(key=lambda x: x[0])
    if len(dated) < 40:
        return [{"error": "insufficient dated rows", "n": len(dated)}]

    start = dated[0][0]
    end = dated[-1][0]
    train_delta = timedelta(days=train_days)
    test_delta = timedelta(days=test_days)
    step = test_delta

    results: list[dict[str, Any]] = []
    cursor = start
    # Require full train+test inside [start, end]
    while True:
        if cursor + train_delta + test_delta > end:
            break
        train_end = cursor + train_delta
        test_end = train_end + test_delta
        train = [r for dt, r in dated if cursor <= dt < train_end]
        test = [r for dt, r in dated if train_end <= dt < test_end]
        if len(train) < 25 or len(test) < 8:
            cursor += step
            continue
        best = optimize_thresholds(train)
        if not best:
            cursor += step
            continue
        oos = [
            r
            for r in test
            if _row_fields(r)[0] >= best["min_score"]
            and _row_fields(r)[1] >= best["min_trust"]
            and _row_fields(r)[2] >= best["min_fwd_wr"]
        ]
        oos_pnls = [float(x.get("pnl_pct") or 0) for x in oos]
        oos_out = [1.0 if p > 0 else 0.0 for p in oos_pnls]
        results.append(
            {
                "train": "%s -> %s" % (cursor.date(), train_end.date()),
                "test": "%s -> %s" % (train_end.date(), test_end.date()),
                "in_sample": best,
                "oos_n": len(oos),
                "oos_wr": round(_wr(oos_out), 4) if oos_out else None,
                "oos_expectancy": round(sum(oos_pnls) / len(oos_pnls), 6) if oos_pnls else None,
            }
        )
        cursor += step

    # Fallback: short calendar span — single chronological 70/30 split by count (still time-ordered)
    if not results and len(dated) >= 40:
        split_i = int(len(dated) * 0.7)
        train = [r for _, r in dated[:split_i]]
        test = [r for _, r in dated[split_i:]]
        if len(train) >= 25 and len(test) >= 8:
            best = optimize_thresholds(train)
            if best:
                oos = [
                    r
                    for r in test
                    if _row_fields(r)[0] >= best["min_score"]
                    and _row_fields(r)[1] >= best["min_trust"]
                    and _row_fields(r)[2] >= best["min_fwd_wr"]
                ]
                oos_pnls = [float(x.get("pnl_pct") or 0) for x in oos]
                oos_out = [1.0 if p > 0 else 0.0 for p in oos_pnls]
                results.append(
                    {
                        "mode": "chronological_split_70_30",
                        "train_n": len(train),
                        "test_n": len(test),
                        "in_sample": best,
                        "oos_n": len(oos),
                        "oos_wr": round(_wr(oos_out), 4) if oos_out else None,
                        "oos_expectancy": round(sum(oos_pnls) / len(oos_pnls), 6) if oos_pnls else None,
                    }
                )

    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--closed-path",
        type=Path,
        default=_REPO / "alpha_engine" / "data" / "closed_picks.json",
    )
    ap.add_argument("--json-out", type=Path, default=None)
    ap.add_argument("--train-days", type=int, default=60)
    ap.add_argument("--test-days", type=int, default=21)
    args = ap.parse_args()

    if not args.closed_path.is_file():
        print("Missing %s" % args.closed_path, file=sys.stderr)
        return 1

    data = json.loads(args.closed_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return 1

    results = walk_forward(data, train_days=args.train_days, test_days=args.test_days)
    if not results:
        print("No walk-forward windows (need longer dated history or relax train/test days).")
    for r in results[:12]:
        print(json.dumps(r, indent=2, default=str))
    if len(results) > 12:
        print("... (%s windows total)" % len(results))

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
        print("Wrote %s" % args.json_out)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
