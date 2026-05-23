"""Online Beta-Bernoulli WR posterior with persisted state across runs.

Why this exists
---------------
The static `tools/wr_posterior.py` re-fits from the full closed-pick log
on every run. That's wasteful: a strategy with n=10,000 picks has its
posterior re-aggregated from scratch hourly. Worse, the calibrator
docstring documents this as the "drift over time" caveat — calibrators
are stale the moment they're fit.

This module persists the running (alpha, beta) posterior state per
strategy keyed by a stable `last_seen_pick_idx` cursor. On each run we:

1. Load prior state from `tools/data/wr_posterior_online_state.json`.
2. Read the closed-pick log; pick rows are processed in their stable
   index order (the order they appear in `picks.recent_closed`).
3. For each strategy: take only picks with index > last_seen_pick_idx,
   update Beta(alpha, beta) by += wins / += losses.
4. Write back the new state including `last_seen_pick_idx`, `n_total`,
   posterior summary statistics (mean, 95% CI, P(WR>50%)) reused from
   `tools/wr_posterior.py:posterior_stats` via importlib.
5. Optionally maintain an append-only history file
   `tools/data/wr_posterior_online_history.jsonl` with one entry per
   run per strategy showing how the posterior evolved.

This makes the run idempotent: replaying with the same closed-pick log
twice does not double-count picks because `last_seen_pick_idx` advances
monotonically.

Drift detection (cheap, no extra state required)
------------------------------------------------
Each entry records the rolling-update delta — change in posterior mean
since prior run. If `abs(delta_mean) > drift_threshold` (default 0.05),
emit a `drift_flag` for that strategy. This catches strategies whose WR
posterior is shifting fast — earlier than the lifetime-rolling
`wr_posterior_timeseries` decay tracker.

Wiring status: OPT-IN SIDECAR. No production caller. Future PR will
hook this into the same hourly cron that writes the payload, so the
audit table can show a `posterior (online)` column with always-fresh
credible intervals.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PICKS_PATH = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
STATE_PATH = REPO_ROOT / "tools" / "data" / "wr_posterior_online_state.json"
HISTORY_PATH = REPO_ROOT / "tools" / "data" / "wr_posterior_online_history.jsonl"

DEFAULT_ALPHA0 = 0.5  # Jeffreys prior, matches wr_posterior.py
DEFAULT_BETA0 = 0.5
DEFAULT_DRIFT_THRESHOLD = 0.05  # 5pp shift in posterior mean -> flag


def _load_posterior_stats():
    spec = importlib.util.spec_from_file_location(
        "wr_posterior", REPO_ROOT / "tools" / "wr_posterior.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.posterior_stats


def _safe_float(x: Any) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if v != v:  # NaN
        return None
    return v


def load_state(path: Path = STATE_PATH) -> dict[str, Any]:
    """Cold-start safe: returns empty state when file missing or unreadable."""
    if not path.exists():
        return {"strategies": {}, "schema_version": 1}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"strategies": {}, "schema_version": 1}
    if not isinstance(data, dict) or "strategies" not in data:
        return {"strategies": {}, "schema_version": 1}
    return data


def save_state(state: dict[str, Any], path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, default=str)


def append_history(entries: list[dict], path: Path = HISTORY_PATH) -> None:
    if not entries:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, sort_keys=True, default=str) + "\n")


def update_posteriors(picks: list[dict],
                      prior_state: dict[str, Any],
                      alpha0: float = DEFAULT_ALPHA0,
                      beta0: float = DEFAULT_BETA0,
                      drift_threshold: float = DEFAULT_DRIFT_THRESHOLD,
                      posterior_stats=None) -> tuple[dict[str, Any], list[dict]]:
    """Pure function: prior_state + picks -> (new_state, history_entries).

    Idempotent on `last_seen_pick_idx`: if a pick's stable index has
    already been ingested, it's skipped.

    `posterior_stats` defaults to the function imported from
    tools/wr_posterior.py; tests inject a deterministic fake.
    """
    if posterior_stats is None:
        posterior_stats = _load_posterior_stats()

    by_strategy_picks: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for idx, p in enumerate(picks):
        pnl = _safe_float(p.get("pnl_pct"))
        if pnl is None:
            continue
        strat = p.get("strategy") or "unknown"
        win = 1 if pnl > 0 else 0
        by_strategy_picks[strat].append((idx, win))

    now_iso = datetime.now(timezone.utc).isoformat()
    history_entries: list[dict] = []
    new_state = {
        "schema_version": prior_state.get("schema_version", 1),
        "alpha0": alpha0,
        "beta0": beta0,
        "last_run_at": now_iso,
        "strategies": dict(prior_state.get("strategies", {})),
    }

    for strat, idx_wins in by_strategy_picks.items():
        prior = new_state["strategies"].get(strat, {
            "alpha": alpha0,
            "beta": beta0,
            "last_seen_pick_idx": -1,
            "n_total": 0,
            "first_seen_at": now_iso,
        })
        prior_mean = (prior["alpha"]
                      / (prior["alpha"] + prior["beta"]))
        last_idx = int(prior.get("last_seen_pick_idx", -1))
        new_alpha = float(prior["alpha"])
        new_beta = float(prior["beta"])
        n_added = 0
        for idx, win in idx_wins:
            if idx <= last_idx:
                continue  # idempotency: already counted
            if win:
                new_alpha += 1.0
            else:
                new_beta += 1.0
            n_added += 1
            if idx > last_idx:
                last_idx = idx

        new_total = int(prior.get("n_total", 0)) + n_added
        new_mean = new_alpha / (new_alpha + new_beta)
        delta_mean = new_mean - prior_mean
        drift_flag = abs(delta_mean) > drift_threshold

        stats = posterior_stats(int(new_alpha - alpha0), new_total, alpha0=alpha0, beta0=beta0)

        new_state["strategies"][strat] = {
            "alpha": float(new_alpha),
            "beta": float(new_beta),
            "last_seen_pick_idx": int(last_idx),
            "n_total": int(new_total),
            "first_seen_at": prior.get("first_seen_at", now_iso),
            "last_updated_at": now_iso,
            "posterior_mean": round(new_mean, 6),
            "posterior_mean_prior": round(prior_mean, 6),
            "delta_mean": round(delta_mean, 6),
            "drift_flag": drift_flag,
            "p_above_50": round(stats.get("p_wr_above_50", 0.0), 6),
            "ci_low_95": round(stats.get("ci_low_95", 0.0), 6),
            "ci_high_95": round(stats.get("ci_high_95", 1.0), 6),
        }

        if n_added > 0:
            history_entries.append({
                "ts_utc": now_iso,
                "strategy": strat,
                "n_added": n_added,
                "n_total": new_total,
                "alpha": new_alpha,
                "beta": new_beta,
                "posterior_mean": new_mean,
                "delta_mean": delta_mean,
                "drift_flag": drift_flag,
            })

    return new_state, history_entries


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--alpha0", type=float, default=DEFAULT_ALPHA0)
    ap.add_argument("--beta0", type=float, default=DEFAULT_BETA0)
    ap.add_argument("--drift-threshold", type=float,
                    default=DEFAULT_DRIFT_THRESHOLD)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    with PICKS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data.get("picks", {}).get("recent_closed", [])

    prior_state = load_state()
    new_state, history = update_posteriors(picks, prior_state,
                                            args.alpha0, args.beta0,
                                            args.drift_threshold)
    save_state(new_state)
    append_history(history)

    if not args.quiet:
        n_strat = len(new_state["strategies"])
        n_drift = sum(1 for s in new_state["strategies"].values()
                      if s.get("drift_flag"))
        print(f"strategies: {n_strat}, drift-flagged: {n_drift}, "
              f"history-entries-written: {len(history)}")
        for s_id, s in sorted(new_state["strategies"].items(),
                              key=lambda kv: -abs(kv[1].get("delta_mean", 0)))[:10]:
            flag = "DRIFT" if s.get("drift_flag") else " ok  "
            print(f"  [{flag}] {s_id:<35} mean={s['posterior_mean']:.3f} "
                  f"delta={s['delta_mean']:+.3f} n={s['n_total']}")
        print(f"State: {STATE_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
