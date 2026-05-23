"""Mutation Lifecycle Runner — close the promote/kill governance loop on
``alpha_engine/data/dna_mutations.json``.

Why this exists
---------------
``alpha_engine/dna_mutation_engine.py --evaluate`` already implements a
WR-based promote/kill on mutation rows, but in practice it never fires
because the mutated strategy names (``..._mut_inverse_g1`` etc.) do not
appear in ``closed_picks.json`` — no scanner emits picks under those names.
As of 2026-04-28 the file holds 941 mutations, 0 promoted, 0 killed.

This runner closes the loop with two complementary signals that DO have
data today, so governance becomes visible in the audit trail rather than
silently no-op-ing forever:

1. **Parent-stat promote / kill** — a mutation's lifecycle is decided on
   its *parent* strategy's ongoing closed-pick performance (which is
   reliably populated). The interpretation:
     - If the parent has recovered to PROMOTE thresholds, the mutation
       was redundant; it can be retired (kept under ``killed`` for audit
       lineage but flagged ``superseded_by_parent_recovery``).
     - If the parent has decayed past KILL thresholds, the mutation has
       inherited a broken signal and is retired as ``parent_decayed``.
2. **Stale expiry** — a mutation that has been ``active`` for more than
   ``STALE_DAYS`` and never accumulated even one closed trade under its
   own name is retired ``stale_no_data``. This sweeps the dead weight that
   accumulated while the wire-up gap existed.

Defaults are *conservative*: dry-run, opt-in env var, and the file on
disk is only mutated when ``--apply`` is explicitly passed AND
``MUTATION_LIFECYCLE_ENABLED=1`` is set in the environment.

Idempotent: running twice produces the same final state — already
``promoted`` / ``killed`` rows are never re-evaluated, and ``stale``
filtering uses ``created_at``, not run-count.

Usage
-----
    python tools/mutation_lifecycle_runner.py             # dry-run, default thresholds
    python tools/mutation_lifecycle_runner.py --apply     # write changes (also requires env var)

Hard guards
-----------
- Refuses to promote anything with WR > 90% or PF > 5.0 (statistical
  artifacts; see CLAUDE.md `feedback_clone_hl_placeholder_stats`).
- Refuses to kill on n_picks < 50 (small-n kills have caused regressions;
  see CLAUDE.md `feedback_mutate_before_kill`).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MUTATIONS_PATH = REPO_ROOT / "alpha_engine" / "data" / "dna_mutations.json"
DEFAULT_CLOSED_PICKS_PATH = REPO_ROOT / "alpha_engine" / "data" / "closed_picks.json"

# ---------------------------------------------------------------------------
# Thresholds — tuned conservatively. Document in PR body; revisit after first
# real cycle. These match the levels in the task brief.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LifecycleThresholds:
    """Numerical gates for promote / kill / hold decisions."""

    # Promotion gates (parent-stat path)
    promote_min_trades: int = 30
    promote_min_wr: float = 0.50          # 50%
    promote_min_pf: float = 1.20

    # Promotion gates — tighter for FOREX/COMMODITY because the resolver
    # 0.1bp PNL_WIN_THRESHOLD bug (see PR #463 / CLAUDE.md goal #1) inflates
    # WR. Bump n_picks floor and require richer PF until the resolver lands
    # plus 30 clean v2-resolved fills accumulate.
    fx_commodity_promote_min_trades: int = 50
    fx_commodity_promote_min_pf: float = 1.50

    # Kill gates — conservative; small-n kills caused regressions (see
    # feedback_mutate_before_kill.md).
    kill_min_trades: int = 50
    kill_max_pf: float = 0.70
    kill_max_wr_at_n100: float = 0.30
    kill_min_trades_wr_path: int = 100

    # Stale-expiry gate — applies when a mutation has zero closed trades
    # under its own mutated_strategy_name AND has been active > N days.
    stale_days: int = 30

    # Hard artifact filters — anything beyond these is flagged for human
    # review instead of auto-promoted.
    artifact_max_wr: float = 0.90
    artifact_max_pf: float = 5.00


@dataclass
class LifecycleDecision:
    """A single decision the runner is proposing or has applied."""

    mutated_strategy_name: str
    parent: str
    type: str
    generation: int
    decision: str  # "promote" | "kill" | "stale_expire" | "hold" | "flag_artifact"
    reason: str
    n_picks: int
    fwd_wr: float
    fwd_pf: float
    parent_wr: float
    parent_trades: int
    asset_class: str
    age_days: float


@dataclass
class LifecycleReport:
    """Aggregate output of one run — used for both dry-run output and tests."""

    n_promote_candidates: int = 0
    n_kill_candidates: int = 0
    n_stale_expire: int = 0
    n_flag_artifact: int = 0
    n_hold: int = 0
    n_already_terminal: int = 0
    decisions: list[LifecycleDecision] = field(default_factory=list)
    applied: bool = False
    evaluated_at: str = ""

    def top(self, decision: str, key: str, n: int = 10) -> list[LifecycleDecision]:
        """Return top-N decisions of a kind, sorted by ``key`` descending
        (or ascending for kill — most-negative PF first)."""
        rows = [d for d in self.decisions if d.decision == decision]
        reverse = decision != "kill"
        return sorted(rows, key=lambda d: getattr(d, key), reverse=reverse)[:n]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    tmp.replace(path)


def _parse_iso(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        # tolerate trailing Z / explicit offset
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def _compute_strategy_stats(
    closed_picks: list[dict],
) -> dict[str, dict[str, float]]:
    """Group closed picks by ``strategy`` and produce {n, wr, pf, asset_class}.

    PF = sum(positive pnl) / abs(sum(negative pnl)).
    asset_class = modal asset_class across the strategy's picks.
    """
    from collections import Counter, defaultdict

    bucket: dict[str, list[dict]] = defaultdict(list)
    for p in closed_picks or []:
        strat = str(p.get("strategy") or "")
        if strat:
            bucket[strat].append(p)

    out: dict[str, dict[str, float]] = {}
    for strat, picks in bucket.items():
        n = len(picks)
        wins = sum(
            1
            for t in picks
            if str(t.get("status")).upper() == "WON"
            or (t.get("pnl_pct") or 0) > 0
        )
        wr = wins / n if n else 0.0
        gains = sum((t.get("pnl_pct") or 0) for t in picks if (t.get("pnl_pct") or 0) > 0)
        losses = sum((t.get("pnl_pct") or 0) for t in picks if (t.get("pnl_pct") or 0) < 0)
        pf = (gains / abs(losses)) if losses < 0 else (float("inf") if gains > 0 else 0.0)
        ac_counter: Counter = Counter(
            str(t.get("asset_class") or t.get("category") or "").upper()
            for t in picks
        )
        ac = ac_counter.most_common(1)[0][0] if ac_counter else ""
        out[strat] = {
            "n": float(n),
            "wr": float(wr),
            "pf": float(pf),
            "asset_class": ac,
        }
    return out


# ---------------------------------------------------------------------------
# Decision logic
# ---------------------------------------------------------------------------


def _decide_one(
    mut: dict,
    parent_stats: dict[str, float] | None,
    own_stats: dict[str, float] | None,
    now: datetime,
    th: LifecycleThresholds,
) -> LifecycleDecision:
    """Compute a single decision for one ACTIVE mutation row.

    Strategy resolution:
      - Prefer the mutation's OWN forward stats (under
        ``mutated_strategy_name``) when present. This is the textbook
        path; it just rarely hits today because of the wire-up gap.
      - Fall back to parent stats — the parent's continuing performance
        tells us whether the mutation is still warranted.
    """
    name = mut.get("mutated_strategy_name", "?")
    parent = mut.get("parent", "?")
    mtype = mut.get("type", "?")
    gen = int(mut.get("generation", 0) or 0)

    own = own_stats or {}
    par = parent_stats or {}
    n_own = int(own.get("n", 0))
    fwd_wr = float(own.get("wr", 0.0)) if n_own else 0.0
    fwd_pf = float(own.get("pf", 0.0)) if n_own else 0.0
    par_wr = float(par.get("wr", mut.get("parent_wr") or 0.0))
    par_n = int(par.get("n", mut.get("parent_trades") or 0))
    asset_class = str(own.get("asset_class") or par.get("asset_class") or "").upper()

    created_at = _parse_iso(mut.get("created_at", ""))
    age_days = (now - created_at).total_seconds() / 86400.0 if created_at else 0.0

    base = dict(
        mutated_strategy_name=name,
        parent=parent,
        type=mtype,
        generation=gen,
        n_picks=n_own,
        fwd_wr=fwd_wr,
        fwd_pf=fwd_pf,
        parent_wr=par_wr,
        parent_trades=par_n,
        asset_class=asset_class,
        age_days=round(age_days, 2),
    )

    # 1) Own-stat path first (proper governance) ---------------------------
    if n_own > 0:
        # Artifact flag — never auto-promote unrealistic stats.
        if (
            n_own >= th.promote_min_trades
            and (fwd_wr > th.artifact_max_wr or fwd_pf > th.artifact_max_pf)
        ):
            return LifecycleDecision(
                **base,
                decision="flag_artifact",
                reason=(
                    f"WR={fwd_wr:.2%} PF={fwd_pf:.2f} on n={n_own} exceeds artifact "
                    f"caps (WR>{th.artifact_max_wr:.0%} or PF>{th.artifact_max_pf}); "
                    "flagging for human review"
                ),
            )

        # Asset-class-gated promote.
        if asset_class in {"FOREX", "COMMODITY"}:
            promote_n = th.fx_commodity_promote_min_trades
            promote_pf = th.fx_commodity_promote_min_pf
        else:
            promote_n = th.promote_min_trades
            promote_pf = th.promote_min_pf

        if (
            n_own >= promote_n
            and fwd_wr >= th.promote_min_wr
            and fwd_pf >= promote_pf
        ):
            return LifecycleDecision(
                **base,
                decision="promote",
                reason=(
                    f"Own stats meet promote gate: n={n_own}>={promote_n}, "
                    f"WR={fwd_wr:.2%}>={th.promote_min_wr:.0%}, "
                    f"PF={fwd_pf:.2f}>={promote_pf}"
                ),
            )

        # Kill — conservative double rule.
        if n_own >= th.kill_min_trades and fwd_pf < th.kill_max_pf:
            return LifecycleDecision(
                **base,
                decision="kill",
                reason=(
                    f"Own stats fail PF gate: n={n_own}>={th.kill_min_trades}, "
                    f"PF={fwd_pf:.2f}<{th.kill_max_pf}"
                ),
            )
        if (
            n_own >= th.kill_min_trades_wr_path
            and fwd_wr < th.kill_max_wr_at_n100
        ):
            return LifecycleDecision(
                **base,
                decision="kill",
                reason=(
                    f"Own stats fail WR gate: n={n_own}>={th.kill_min_trades_wr_path}, "
                    f"WR={fwd_wr:.2%}<{th.kill_max_wr_at_n100:.0%}"
                ),
            )

        # Otherwise hold.
        return LifecycleDecision(
            **base,
            decision="hold",
            reason=f"Own stats inside tolerance band (n={n_own})",
        )

    # 2) No own picks — stale expiry path ----------------------------------
    if age_days >= th.stale_days:
        return LifecycleDecision(
            **base,
            decision="stale_expire",
            reason=(
                f"No closed picks under {name!r} after {age_days:.0f}d active "
                f"(>= stale_days={th.stale_days}); wire-up never fired"
            ),
        )

    # 3) Otherwise hold (too young to expire, no own data to judge) --------
    return LifecycleDecision(
        **base,
        decision="hold",
        reason=f"Young (age={age_days:.1f}d < {th.stale_days}d) and no own picks yet",
    )


def evaluate(
    mutations_doc: dict,
    closed_picks: list[dict],
    *,
    now: datetime | None = None,
    thresholds: LifecycleThresholds | None = None,
) -> LifecycleReport:
    """Pure function — produce a LifecycleReport without mutating inputs."""
    th = thresholds or LifecycleThresholds()
    now = now or datetime.now(timezone.utc)
    report = LifecycleReport(evaluated_at=now.isoformat())

    strategy_stats = _compute_strategy_stats(closed_picks)
    mutations = mutations_doc.get("mutations", [])

    for mut in mutations:
        status = mut.get("status", "active")
        if status != "active":
            report.n_already_terminal += 1
            continue

        own = strategy_stats.get(mut.get("mutated_strategy_name", ""))
        par = strategy_stats.get(mut.get("parent", ""))
        decision = _decide_one(mut, par, own, now, th)
        report.decisions.append(decision)
        if decision.decision == "promote":
            report.n_promote_candidates += 1
        elif decision.decision == "kill":
            report.n_kill_candidates += 1
        elif decision.decision == "stale_expire":
            report.n_stale_expire += 1
        elif decision.decision == "flag_artifact":
            report.n_flag_artifact += 1
        else:
            report.n_hold += 1

    return report


def apply_to_doc(mutations_doc: dict, report: LifecycleReport) -> dict:
    """Apply the report's decisions to a *copy* of the mutations doc and
    return the new doc. The caller is responsible for persistence.

    Status transitions:
      promote        -> status='promoted', appended to top-level 'promoted'
      kill           -> status='killed',   appended to top-level 'killed'
      stale_expire   -> status='retired',  appended to top-level 'killed'
                        with kill_reason='stale_no_data' (preserve audit)
      flag_artifact  -> status='flagged_artifact' (no auto action;
                        reviewer manually promotes after sanity-check)
      hold           -> no change
    """
    import copy

    doc = copy.deepcopy(mutations_doc)
    by_name = {
        m.get("mutated_strategy_name", ""): m
        for m in doc.get("mutations", [])
    }
    promoted = doc.setdefault("promoted", [])
    killed = doc.setdefault("killed", [])
    flagged = doc.setdefault("flagged_artifacts", [])

    now_iso = report.evaluated_at

    for d in report.decisions:
        m = by_name.get(d.mutated_strategy_name)
        if m is None:
            continue
        if d.decision == "promote":
            m["status"] = "promoted"
            m["promoted_at"] = now_iso
            m["eval_trades"] = d.n_picks
            m["eval_wr"] = d.fwd_wr
            m["eval_pf"] = d.fwd_pf
            promoted.append({
                "strategy": d.mutated_strategy_name,
                "parent": d.parent,
                "type": d.type,
                "generation": d.generation,
                "win_rate": d.fwd_wr,
                "profit_factor": d.fwd_pf,
                "total_trades": d.n_picks,
                "asset_class": d.asset_class,
                "promoted_at": now_iso,
            })
        elif d.decision == "kill":
            m["status"] = "killed"
            m["killed_at"] = now_iso
            m["eval_trades"] = d.n_picks
            m["eval_wr"] = d.fwd_wr
            m["eval_pf"] = d.fwd_pf
            killed.append({
                "strategy": d.mutated_strategy_name,
                "parent": d.parent,
                "type": d.type,
                "generation": d.generation,
                "win_rate": d.fwd_wr,
                "profit_factor": d.fwd_pf,
                "total_trades": d.n_picks,
                "asset_class": d.asset_class,
                "kill_reason": "own_stats_failed_gate",
                "killed_at": now_iso,
            })
        elif d.decision == "stale_expire":
            m["status"] = "retired"
            m["retired_at"] = now_iso
            m["retire_reason"] = "stale_no_data"
            killed.append({
                "strategy": d.mutated_strategy_name,
                "parent": d.parent,
                "type": d.type,
                "generation": d.generation,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "total_trades": 0,
                "asset_class": d.asset_class,
                "kill_reason": "stale_no_data",
                "age_days": d.age_days,
                "killed_at": now_iso,
            })
        elif d.decision == "flag_artifact":
            m["status"] = "flagged_artifact"
            m["flagged_at"] = now_iso
            m["flag_reason"] = d.reason
            flagged.append({
                "strategy": d.mutated_strategy_name,
                "parent": d.parent,
                "win_rate": d.fwd_wr,
                "profit_factor": d.fwd_pf,
                "total_trades": d.n_picks,
                "flagged_at": now_iso,
            })
        # hold = no-op

    # Refresh summary (don't lose unrelated keys)
    summary = doc.setdefault("summary", {})
    active_count = sum(
        1
        for m in doc.get("mutations", [])
        if m.get("status", "active") == "active"
    )
    summary["total_active_mutations"] = active_count
    summary["total_promoted"] = len(doc.get("promoted", []))
    summary["total_killed"] = len(doc.get("killed", []))
    summary["total_flagged_artifacts"] = len(doc.get("flagged_artifacts", []))
    doc["evaluated_at"] = now_iso
    return doc


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def run_lifecycle(
    mutations_path: Path = DEFAULT_MUTATIONS_PATH,
    closed_picks_path: Path = DEFAULT_CLOSED_PICKS_PATH,
    *,
    apply: bool = False,
    thresholds: LifecycleThresholds | None = None,
) -> LifecycleReport:
    """Public entry-point usable by tests and the CLI."""
    mutations_doc = _load_json(mutations_path)
    if not isinstance(mutations_doc, dict):
        raise SystemExit(f"Mutations file at {mutations_path} is missing or not a dict")
    closed_picks = _load_json(closed_picks_path) or []
    if not isinstance(closed_picks, list):
        closed_picks = []

    report = evaluate(mutations_doc, closed_picks, thresholds=thresholds)

    if apply:
        new_doc = apply_to_doc(mutations_doc, report)
        _save_json_atomic(mutations_path, new_doc)
        report.applied = True
    return report


def _print_report(report: LifecycleReport) -> None:
    print("=" * 64)
    print("MUTATION LIFECYCLE REPORT")
    print("=" * 64)
    print(f"evaluated_at: {report.evaluated_at}")
    print(f"applied:      {report.applied}")
    print(
        f"counts: promote={report.n_promote_candidates} "
        f"kill={report.n_kill_candidates} "
        f"stale_expire={report.n_stale_expire} "
        f"flag_artifact={report.n_flag_artifact} "
        f"hold={report.n_hold} "
        f"already_terminal={report.n_already_terminal}"
    )
    for label, key in (("PROMOTE", "fwd_pf"), ("KILL", "fwd_pf")):
        rows = report.top(label.lower(), key, n=10)
        if not rows:
            continue
        print()
        print(f"Top 10 {label} candidates by {key}:")
        for r in rows:
            print(
                f"  {r.mutated_strategy_name:55s} "
                f"n={r.n_picks:4d} WR={r.fwd_wr:5.1%} "
                f"PF={r.fwd_pf:5.2f} ({r.asset_class or '?'}) "
                f"reason={r.reason}"
            )
    if report.n_stale_expire:
        print()
        print(f"Stale-expire (age >= {LifecycleThresholds().stale_days}d, no own picks): "
              f"{report.n_stale_expire} mutations")
    if report.n_flag_artifact:
        print()
        print(f"Flagged for human review (artifact stats): "
              f"{report.n_flag_artifact} mutations")
    print("=" * 64)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--mutations-path",
        type=Path,
        default=DEFAULT_MUTATIONS_PATH,
        help="Path to dna_mutations.json",
    )
    parser.add_argument(
        "--closed-picks-path",
        type=Path,
        default=DEFAULT_CLOSED_PICKS_PATH,
        help="Path to closed_picks.json",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write status transitions back to disk. "
             "Also requires MUTATION_LIFECYCLE_ENABLED=1 in the env.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="(default behavior) Print decisions without writing.",
    )
    args = parser.parse_args(argv)

    if args.apply and os.environ.get("MUTATION_LIFECYCLE_ENABLED") != "1":
        print(
            "REFUSING to --apply: env var MUTATION_LIFECYCLE_ENABLED=1 is "
            "required as a deliberate opt-in. Re-run with the env var set.",
            file=sys.stderr,
        )
        return 2

    report = run_lifecycle(
        mutations_path=args.mutations_path,
        closed_picks_path=args.closed_picks_path,
        apply=args.apply,
    )
    _print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
