#!/usr/bin/env python3
"""Walk-forward CI gate.

Blocks merging strategies with backtest WR > 85% unless they pass walk-forward
validation. Justification: r=-0.91 inverse correlation between BT WR and FWD WR
(see ``alpha_engine/data/backtest_forward_correlation.json``).

Schema:
- Backtest input: ``incubator/backtest_results/*.json`` (or any json passed via
  --backtest) with shape ``{"results": [{"strategy_name": str,
  "win_rate": 0.0..1.0, ...}, ...]}``. Also accepts ``win_rate`` already in
  percent (>1.5 treated as percent).
- Walk-forward input: ``alpha_engine/data/walkforward_results.json`` with shape
  ``{"strategies": [{"strategy": str, "verdict":
  "ELITE|STRONG|VIABLE|MARGINAL|FAILING", ...}, ...]}``. A strategy is
  considered PROVEN iff verdict in {ELITE, STRONG, VIABLE}.

Gate logic:
- bt_wr <= 85 -> pass (no gate).
- bt_wr > 85 AND walkforward verdict in PROVEN_VERDICTS -> pass.
- bt_wr > 85 AND walkforward missing/FAILING/MARGINAL -> fail (exit 1).
- No backtest data -> warn, no gate.

Rollback:
    WALKFORWARD_GATE_DISABLED=1 python tools/check_walkforward_gate.py
makes the script no-op (exit 0).

Exit:
    0 = all strategies pass / disabled / no data
    1 = one or more high-BT-WR strategies failed walk-forward
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_BACKTEST = REPO_ROOT / "incubator" / "backtest_results"
DEFAULT_WALKFORWARD = REPO_ROOT / "alpha_engine" / "data" / "walkforward_results.json"

WR_THRESHOLD_PCT = 85.0
PROVEN_VERDICTS = {"ELITE", "STRONG", "VIABLE"}


def _normalize_wr(raw: Any) -> float | None:
    """Normalize win_rate to 0..100 percent. Returns None on invalid."""
    if raw is None:
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    # Walk-forward stores percent (e.g. 75.7); incubator stores fraction (0.5484).
    # Heuristic: anything <= 1.5 is treated as a fraction.
    if v <= 1.5:
        v = v * 100.0
    return v


def changed_backtest_files(diff_base: str) -> set[Path] | None:
    """Return resolved paths of backtest jsons added/modified vs *diff_base*.

    Used to make the gate diff-aware: a PR should only be gated on the
    strategies it actually adds or changes, not on every pre-existing
    incubator file. Returns ``None`` on any git failure (caller falls back
    to evaluating everything — fail-safe, never silently skips the gate).
    """
    try:
        out = subprocess.run(
            [
                "git", "-C", str(REPO_ROOT), "diff", "--name-only",
                "--diff-filter=AM", f"{diff_base}...HEAD", "--",
                "incubator/backtest_results/",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"[walkforward-gate] WARNING: git diff failed ({exc}); "
              "falling back to full evaluation.")
        return None
    if out.returncode != 0:
        print(f"[walkforward-gate] WARNING: git diff exit {out.returncode} "
              f"({out.stderr.strip()[:120]}); falling back to full evaluation.")
        return None
    files: set[Path] = set()
    for line in out.stdout.splitlines():
        line = line.strip()
        if line.endswith(".json"):
            files.add((REPO_ROOT / line).resolve())
    return files


def load_backtest_results(
    path: Path,
    only_files: set[Path] | None = None,
) -> dict[str, float]:
    """Return {strategy_name: bt_wr_pct}. Accepts a file or a directory of jsons.

    On directory input, the latest WR per strategy wins (sorted by mtime).

    If *only_files* is given, files whose resolved path is not in that set are
    skipped — this is how the diff-aware gate restricts evaluation to the
    strategies a PR actually changed.
    """
    out: dict[str, float] = {}
    if not path.exists():
        return out

    files: Iterable[Path]
    if path.is_dir():
        files = sorted(path.glob("*.json"), key=lambda p: p.stat().st_mtime)
    else:
        files = [path]

    for fp in files:
        if only_files is not None and fp.resolve() not in only_files:
            continue
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(results, list):
            continue
        for row in results:
            if not isinstance(row, dict):
                continue
            name = row.get("strategy_name") or row.get("strategy")
            if not name:
                continue
            wr = _normalize_wr(row.get("win_rate"))
            if wr is None:
                continue
            # latest mtime wins
            out[name] = wr
    return out


def load_walkforward(path: Path) -> dict[str, str]:
    """Return {strategy_name: verdict}. Empty if file missing."""
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    out: dict[str, str] = {}
    for row in data.get("strategies", []):
        if not isinstance(row, dict):
            continue
        name = row.get("strategy")
        verdict = row.get("verdict")
        if name and verdict:
            out[str(name)] = str(verdict).upper()
    return out


def evaluate(
    backtest: dict[str, float],
    walkforward: dict[str, str],
    wr_threshold: float = WR_THRESHOLD_PCT,
) -> dict[str, Any]:
    gated: list[dict[str, Any]] = []
    passed: list[str] = []
    skipped_low_wr: list[str] = []

    for strat, bt_wr in backtest.items():
        if bt_wr <= wr_threshold:
            skipped_low_wr.append(strat)
            continue
        verdict = walkforward.get(strat)
        if verdict in PROVEN_VERDICTS:
            passed.append(strat)
        else:
            gated.append(
                {
                    "strategy": strat,
                    "bt_wr": round(bt_wr, 2),
                    "walkforward_verdict": verdict or "MISSING",
                    "reason": (
                        f"bt_wr={bt_wr:.1f}% > {wr_threshold:.0f}% but "
                        f"walkforward verdict is {verdict or 'MISSING'} "
                        f"(need one of {sorted(PROVEN_VERDICTS)})"
                    ),
                }
            )

    return {
        "gated": gated,
        "passed": passed,
        "skipped_low_wr": skipped_low_wr,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Walk-forward CI gate")
    parser.add_argument(
        "--backtest",
        type=Path,
        default=DEFAULT_BACKTEST,
        help="Path to a backtest results json file or a directory of them.",
    )
    parser.add_argument(
        "--walkforward",
        type=Path,
        default=DEFAULT_WALKFORWARD,
        help="Path to walkforward_results.json.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=WR_THRESHOLD_PCT,
        help="BT WR threshold (percent) above which the gate fires.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable summary on stdout.",
    )
    parser.add_argument(
        "--diff-base",
        default=None,
        help=(
            "Git ref (e.g. origin/main). When set, the gate only evaluates "
            "strategies whose incubator/backtest_results/*.json files were "
            "added or modified vs this ref — so a PR is gated on what it "
            "changes, not on every pre-existing incubator file."
        ),
    )
    args = parser.parse_args(argv)

    if os.environ.get("WALKFORWARD_GATE_DISABLED") == "1":
        print("[walkforward-gate] DISABLED via WALKFORWARD_GATE_DISABLED=1 (no-op).")
        return 0

    only_files: set[Path] | None = None
    if args.diff_base:
        changed = changed_backtest_files(args.diff_base)
        if changed is None:
            # git failed — fail-safe: evaluate everything rather than skip.
            print("[walkforward-gate] diff-base unavailable — evaluating all "
                  "backtest results.")
        elif not changed:
            print(f"[walkforward-gate] no changed backtest files vs "
                  f"{args.diff_base} — gate not applicable. PASS.")
            if args.json:
                print(json.dumps({"status": "no_changed_files",
                                  "gated": [], "passed": []}))
            return 0
        else:
            print(f"[walkforward-gate] diff-aware: {len(changed)} changed "
                  f"backtest file(s) vs {args.diff_base}.")
            only_files = changed

    backtest = load_backtest_results(args.backtest, only_files=only_files)
    walkforward = load_walkforward(args.walkforward)

    if not backtest:
        print(
            f"[walkforward-gate] WARNING: no backtest data at {args.backtest}; "
            "skipping gate.",
        )
        if args.json:
            print(json.dumps({"status": "no_data", "gated": [], "passed": []}))
        return 0

    result = evaluate(backtest, walkforward, wr_threshold=args.threshold)

    summary = {
        "gated_count": len(result["gated"]),
        "passed_count": len(result["passed"]),
        "missing_data_count": 0 if backtest else 1,
        "skipped_low_wr_count": len(result["skipped_low_wr"]),
        "threshold_pct": args.threshold,
        "total_backtest_strategies": len(backtest),
        "walkforward_strategies": len(walkforward),
    }

    print("[walkforward-gate] summary:")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    if result["gated"]:
        print("\n[walkforward-gate] GATED strategies:")
        for row in result["gated"]:
            print(
                f"  - {row['strategy']}: bt_wr={row['bt_wr']}% "
                f"verdict={row['walkforward_verdict']} :: {row['reason']}"
            )

    if args.json:
        print(json.dumps({"summary": summary, **result}, indent=2))

    return 1 if result["gated"] else 0


if __name__ == "__main__":
    sys.exit(main())
