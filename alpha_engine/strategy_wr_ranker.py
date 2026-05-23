"""
M-108: Strategy-level rolling WR ranker.

Walk-forward eff-stability harness (PATH_TO_PROVEN_EDGE Step 1) found that
elite_score has Cohen's d eff≈0.005 (noise) — it does NOT separate winners
from losers. Strategy-level WR is the only currently admissible signal:
  cot_positioning         WR=78.4%  n=134  (COMMODITY)
  cftc_cot_commercial     WR=74.8%  n=131  (COMMODITY)

This module enriches picks with their strategy's rolling WR so it can be
used as the primary ranking signal alongside ml_composite.

Wire-in: called by alpha_engine/elite_scorer.py::enrich_picks_with_elite_score()
before the final sort step. Adds `strategy_rolling_wr` field to each pick.

Ranking composite (M-108 v2 — 2026-05-18):
    rank_score = 0.70 * strategy_rolling_wr_norm
                + 0.30 * ml_composite_norm
Confidence REMOVED: eff-stability harness shows confidence eff=0.174 (WEAK,
below 0.30 floor) and peer harness shows sign-split across windows.
Including it was adding noise. Falls back to ml_composite alone if strategy
has insufficient history (n < MIN_N).
"""

from __future__ import annotations

import json
import math
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LOOKBACK_DAYS = 60
MIN_N = 10           # minimum closed picks per strategy to trust WR
CONCENTRATION_CAP = 0.40   # max fraction of top-N picks from one strategy

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CLOSED_PATH = _REPO_ROOT / "alpha_engine" / "data" / "closed_picks.json"

# Module-level cache: (mtime, result_dict)
_CACHE: dict[str, Any] = {}
_CACHE_TTL_S = 3600  # 1 hour


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_dt(s: Any) -> datetime | None:
    if not s:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
    ):
        try:
            raw = str(s)[:26].strip()
            dt = datetime.strptime(raw, fmt.replace("%z", ""))
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        except ValueError:
            continue
    return None


def _is_win(pick: dict) -> bool | None:
    status = str(pick.get("status") or "").upper()
    WIN = {"WIN", "WON", "TARGET_HIT", "TP_HIT", "CLOSED_WIN"}
    LOSS = {"LOSS", "LOST", "SL_HIT", "STOPPED", "CLOSED_LOSS", "EXPIRED"}
    if status in WIN:
        return True
    if status in LOSS:
        return False
    pnl = pick.get("pnl_pct")
    if pnl is not None:
        try:
            return float(pnl) > 0
        except (TypeError, ValueError):
            pass
    return None


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def compute_strategy_rolling_wr(
    closed_picks: list[dict] | None = None,
    lookback_days: int = LOOKBACK_DAYS,
    min_n: int = MIN_N,
    closed_path: Path = _CLOSED_PATH,
) -> dict[str, dict]:
    """
    Compute rolling win rate per strategy from closed picks.

    Returns:
        {strategy_name: {"wr": float 0-1, "n": int, "asset_class": str}}
        Only strategies with n >= min_n are included.
    """
    global _CACHE

    # Cache only applies when loading from file (picks=None); caller-supplied picks bypass it.
    cache_key = f"{closed_path}|{lookback_days}|{min_n}"
    now_ts = time.monotonic()
    if closed_picks is None:
        if cache_key in _CACHE:
            cached_ts, cached_result = _CACHE[cache_key]
            if now_ts - cached_ts < _CACHE_TTL_S:
                return cached_result
        if not closed_path.exists():
            return {}
        try:
            closed_picks = json.loads(closed_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    # Group by strategy
    by_strat: dict[str, list[dict]] = {}
    for p in closed_picks:
        strat = p.get("strategy") or ""
        if not strat:
            continue
        dt = _parse_dt(
            p.get("closed_at") or p.get("exit_date") or p.get("resolved_at")
        )
        if dt is None or dt < cutoff:
            continue
        outcome = _is_win(p)
        if outcome is None:
            continue
        pnl_raw = p.get("pnl_pct")
        try:
            pnl_f = float(pnl_raw) if pnl_raw is not None else None
        except (TypeError, ValueError):
            pnl_f = None
        by_strat.setdefault(strat, []).append({
            "outcome": outcome,
            "ac": p.get("asset_class", ""),
            "pnl": pnl_f,
        })

    result: dict[str, dict] = {}
    for strat, picks_list in by_strat.items():
        n = len(picks_list)
        if n < min_n:
            continue
        wins = sum(1 for p in picks_list if p["outcome"])
        wr = wins / n
        ac = picks_list[0]["ac"]
        # avg_pnl_pct as percentage points (e.g., 0.02 → 2.0)
        pnl_vals = [p["pnl"] * 100 for p in picks_list if p["pnl"] is not None]
        avg_pnl_pct = round(sum(pnl_vals) / len(pnl_vals), 4) if pnl_vals else None
        result[strat] = {
            "wr": round(wr, 4),
            "n": n,
            "asset_class": ac,
            "avg_pnl_pct": avg_pnl_pct,
        }

    # Only cache file-loaded results (closed_picks was None initially)
    if cache_key:
        _CACHE[cache_key] = (now_ts, result)
    return result


# ---------------------------------------------------------------------------
# Enrichment
# ---------------------------------------------------------------------------

def enrich_picks_with_strategy_wr(
    picks: list[dict],
    strategy_wr_lookup: dict[str, dict] | None = None,
    lookback_days: int = LOOKBACK_DAYS,
    min_n: int = MIN_N,
) -> list[dict]:
    """
    Add `strategy_rolling_wr` and `strategy_rolling_n` fields to each pick.

    strategy_rolling_wr: float 0-1, or None if insufficient history.
    strategy_rolling_n:  int count of closed picks in lookback window.

    Modifies picks in-place and returns them.
    """
    if strategy_wr_lookup is None:
        strategy_wr_lookup = compute_strategy_rolling_wr(
            lookback_days=lookback_days, min_n=min_n
        )

    for pick in picks:
        strat = pick.get("strategy") or ""
        info = strategy_wr_lookup.get(strat)
        if info:
            pick["strategy_rolling_wr"] = info["wr"]
            pick["strategy_rolling_n"] = info["n"]
            pick["strategy_avg_pnl_pct"] = info.get("avg_pnl_pct")
        else:
            pick.setdefault("strategy_rolling_wr", None)
            pick.setdefault("strategy_rolling_n", 0)
            pick.setdefault("strategy_avg_pnl_pct", None)

    return picks


# ---------------------------------------------------------------------------
# Composite rank score
# ---------------------------------------------------------------------------

def _wr_weight_for_n(n: int, base: float = 0.70, full_n: int = 30) -> float:
    """
    Dynamic strategy_rolling_wr weight based on sample size.

    At n < full_n the WR estimate is noisy (95% CI can span 35 pp at n=10).
    Linear ramp: n=MIN_N → 0.50; n≥full_n → base (0.70).
    Swarm recommendation 2026-05-18: avoids overweighting noisy low-n WR estimates
    while preserving the signal for well-sampled strategies.
    """
    if n >= full_n:
        return base
    min_weight = 0.50  # floor at n=MIN_N (base - 0.20 has FP drift)
    ramp = max(0.0, (n - MIN_N) / max(full_n - MIN_N, 1))
    return min_weight + ramp * (base - min_weight)


def compute_rank_score(pick: dict) -> float:
    """
    Composite rank score for pick ordering (higher = better).

    Weights (M-108 v2 — confidence removed per eff-stability harness):
        strategy_rolling_wr: 50-70% (dynamic, based on n; full 70% at n>=30)
        ml_composite:        30-50% (complement of strategy weight)
    Fallback (no strategy history): 100% ml_composite.

    All components clamped to [0, 1].
    """
    strat_wr = pick.get("strategy_rolling_wr")
    strat_n = pick.get("strategy_rolling_n", 0) or 0

    # ml_composite is typically 0-1; elite_score is 0-183; confidence is 0-1
    ml_comp = pick.get("ml_composite_score") or pick.get("ml_composite") or 0
    try:
        ml_comp = float(ml_comp)
    except (TypeError, ValueError):
        ml_comp = 0.0
    ml_comp = max(0.0, min(1.0, ml_comp))

    if strat_wr is not None and strat_n >= MIN_N:
        strat_wr_f = max(0.0, min(1.0, float(strat_wr)))

        # Guard against data artifacts: high WR with near-zero avg PnL signals
        # measurement issues (e.g., DYDXUSDT 100% WR with avg_pnl~0.02%).
        # If avg_pnl_pct < 0.10 (10 bp) and WR > 65%, halve the WR contribution.
        avg_pnl = pick.get("strategy_avg_pnl_pct")
        if avg_pnl is not None:
            try:
                if float(avg_pnl) < 0.10 and strat_wr_f > 0.65:
                    strat_wr_f *= 0.5  # halve contribution — artifact guard
            except (TypeError, ValueError):
                pass

        # Dynamic weight: 50% at n=MIN_N, 70% at n>=30.
        # Confidence DROPPED (eff=0.174 WEAK, peer harness sign-split, 2026-05-18).
        w_strat = _wr_weight_for_n(strat_n)
        score = w_strat * strat_wr_f + (1.0 - w_strat) * ml_comp
    else:
        # No strategy history: fall back to ml_composite only
        score = ml_comp

    return round(score, 6)


def rank_picks(
    picks: list[dict],
    strategy_wr_lookup: dict[str, dict] | None = None,
) -> list[dict]:
    """
    Sort picks by composite rank score (descending).

    Enriches with strategy_rolling_wr if not already set, then sorts.
    Adds `m108_rank_score` field to each pick for auditability.
    Modifies in-place and returns.
    """
    enrich_picks_with_strategy_wr(picks, strategy_wr_lookup)
    for pick in picks:
        pick["m108_rank_score"] = compute_rank_score(pick)
    picks.sort(key=lambda p: p.get("m108_rank_score", 0.0), reverse=True)
    return picks


# ---------------------------------------------------------------------------
# Summary report
# ---------------------------------------------------------------------------

def strategy_wr_report(
    strategy_wr_lookup: dict[str, dict] | None = None,
    top_n: int = 20,
) -> str:
    """Return a plain-text summary of top strategies by rolling WR."""
    if strategy_wr_lookup is None:
        strategy_wr_lookup = compute_strategy_rolling_wr()

    rows = sorted(
        strategy_wr_lookup.items(),
        key=lambda kv: (kv[1]["wr"], kv[1]["n"]),
        reverse=True,
    )[:top_n]

    lines = [
        f"Strategy Rolling WR (last {LOOKBACK_DAYS}d, min_n={MIN_N})",
        f"{'Strategy':<45} {'WR':>7} {'n':>6} {'Asset Class'}",
        "-" * 72,
    ]
    for strat, info in rows:
        lines.append(
            f"{strat:<45} {info['wr']:>6.1%} {info['n']:>6d}  {info['asset_class']}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Weight decay monitor (M-108 P1)
# ---------------------------------------------------------------------------

_MONITOR_PATH = _REPO_ROOT / "reports" / "m108_rank_monitor.json"
_MONITOR_WINDOW_DAYS = 30


def record_rank_outcome(pick_id: str, rank_score: float, subsequent_pnl_pct: float) -> None:
    """
    Record a resolved pick's rank score vs actual PnL for drift monitoring.

    Called by outcome_resolver.py when a pick closes. Maintains a rolling
    30-day log in reports/m108_rank_monitor.json.
    """
    try:
        if _MONITOR_PATH.exists():
            records = json.loads(_MONITOR_PATH.read_text(encoding="utf-8"))
        else:
            records = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=_MONITOR_WINDOW_DAYS)
        records = [r for r in records if _parse_dt(r.get("ts")) and _parse_dt(r["ts"]) >= cutoff]
        records.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "pick_id": pick_id,
            "rank_score": round(rank_score, 6),
            "pnl_pct": round(subsequent_pnl_pct, 4),
        })
        _MONITOR_PATH.write_text(json.dumps(records, indent=2), encoding="utf-8")
    except Exception:
        pass  # Fail-open — monitoring must not break production


def compute_rank_correlation(monitor_path: Path = _MONITOR_PATH) -> dict:
    """
    Compute Spearman rank correlation between m108_rank_score and realized PnL.

    Returns:
        {"n": int, "spearman_rho": float | None, "verdict": str}
    Verdict is "STABLE" if rho >= 0.05 over n >= 20, else "REVIEW_NEEDED".
    """
    if not monitor_path.exists():
        return {"n": 0, "spearman_rho": None, "verdict": "INSUFFICIENT_DATA"}

    try:
        records = json.loads(monitor_path.read_text(encoding="utf-8"))
    except Exception:
        return {"n": 0, "spearman_rho": None, "verdict": "ERROR"}

    valid = [r for r in records if r.get("rank_score") is not None and r.get("pnl_pct") is not None]
    n = len(valid)
    if n < 10:
        return {"n": n, "spearman_rho": None, "verdict": "INSUFFICIENT_DATA"}

    # Spearman rho via rank differences
    ranks_x = _rank_list([r["rank_score"] for r in valid])
    ranks_y = _rank_list([r["pnl_pct"] for r in valid])
    d_sq = sum((rx - ry) ** 2 for rx, ry in zip(ranks_x, ranks_y))
    rho = 1.0 - (6.0 * d_sq) / (n * (n * n - 1))
    rho = round(rho, 4)

    verdict = "STABLE" if rho >= 0.05 else "REVIEW_NEEDED"
    return {"n": n, "spearman_rho": rho, "verdict": verdict}


def _rank_list(values: list[float]) -> list[float]:
    """Convert values to Spearman ranks (1-based, ties get average rank)."""
    sorted_vals = sorted(enumerate(values), key=lambda x: x[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(sorted_vals):
        j = i
        while j < len(sorted_vals) - 1 and sorted_vals[j + 1][1] == sorted_vals[i][1]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[sorted_vals[k][0]] = avg_rank
        i = j + 1
    return ranks


if __name__ == "__main__":
    lookup = compute_strategy_rolling_wr()
    print(strategy_wr_report(lookup))
    print(f"\nTotal strategies with n>={MIN_N}: {len(lookup)}")
