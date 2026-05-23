#!/usr/bin/env python3
"""
A3.1 — Model Regression Gate
==============================
Compares current model metrics (win_rate, profit_factor) against the previous
committed version.  Exits with code 1 if either metric regresses by more than
the allowed threshold (default 5%).

Intended as a CI step in ml-model-autotraining.yml BEFORE the model-commit
step.  If this script exits non-zero, the commit step is skipped.

How it works:
  1. Read "current" metrics from alpha_engine/data/model_metadata_{name}.json
     (written by tools/write_model_metadata.py after training).
  2. Read "previous" metrics from the same path at git HEAD~1 using
     `git show HEAD~1:<path>`.  Falls back to the last git tag that matches
     the model name if HEAD~1 does not have the file.
  3. Compare win_rate and profit_factor (if present).  Also compares accuracy
     as a secondary signal.
  4. Exit 0 (pass) or 1 (regression detected).

Usage:
  python tools/model_regression_check.py --model-name ml_consensus
  python tools/model_regression_check.py --model-name ml_consensus --threshold 0.05

Arguments:
  --model-name  Name matching the metadata file: model_metadata_{name}.json
  --threshold   Maximum allowed fractional regression (default 0.05 = 5%).
                E.g. 0.05 means new_metric >= old_metric * 0.95 is OK.
  --metadata-dir  Directory containing model_metadata files (default: alpha_engine/data)
  --allow-missing  Exit 0 (pass) if the previous metadata is absent instead
                   of failing.  Useful for the first ever training run.

Exit codes:
  0  — No regression detected (or previous metadata absent with --allow-missing).
  1  — Regression detected OR unexpected error (details printed to stderr).
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DEFAULT_METADATA_DIR = Path("alpha_engine/data")
_DEFAULT_THRESHOLD = 0.05  # 5%

# Metrics where HIGHER is better (regression = new < old - tolerance)
_HIGHER_IS_BETTER = ["win_rate", "accuracy", "sharpe", "profit_factor"]


# ── Core comparison logic ─────────────────────────────────────────────────────


def load_current_metadata(model_name: str, metadata_dir: Path) -> Optional[dict]:
    """Load the metadata JSON written by the current training run."""
    path = metadata_dir / f"model_metadata_{model_name}.json"
    if not path.is_file():
        logger.warning("Current metadata not found: %s", path)
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_previous_metadata(model_name: str, metadata_dir: Path) -> Optional[dict]:
    """Load the previous committed metadata from git HEAD~1."""
    rel_path = (metadata_dir / f"model_metadata_{model_name}.json").as_posix()
    # Try HEAD~1 first
    raw = _git_show(f"HEAD~1:{rel_path}")
    if raw is None:
        # Fall back to the most recent tag that contains this file
        raw = _git_show_from_latest_tag(rel_path)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("Previous metadata JSON decode error: %s", exc)
        return None


def _git_show(ref_path: str) -> Optional[str]:
    """Run `git show <ref_path>` and return stdout, or None on failure."""
    try:
        result = subprocess.run(
            ["git", "show", ref_path],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return result.stdout
        return None
    except Exception:
        return None


def _git_show_from_latest_tag(rel_path: str) -> Optional[str]:
    """Try to find the file from the latest git tag."""
    try:
        tags = subprocess.run(
            ["git", "tag", "--sort=-creatordate"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if tags.returncode != 0:
            return None
        for tag in tags.stdout.strip().splitlines():
            raw = _git_show(f"{tag.strip()}:{rel_path}")
            if raw is not None:
                return raw
    except Exception:
        pass
    return None


def compare_metrics(
    current: dict,
    previous: dict,
    threshold: float,
) -> tuple[bool, list[str]]:
    """Compare current vs previous model metrics.

    Returns:
        (passed: bool, messages: list[str])
        passed=True means no regression beyond threshold.
    """
    curr_metrics: dict = current.get("metrics", {})
    prev_metrics: dict = previous.get("metrics", {})

    messages: list[str] = []
    any_regression = False

    curr_model = current.get("model_name", "?")
    prev_commit = previous.get("git_commit", "?")[:8]
    curr_commit = current.get("git_commit", "?")[:8]

    messages.append(
        f"Comparing {curr_model}: current={curr_commit} vs previous={prev_commit}"
    )

    for metric in _HIGHER_IS_BETTER:
        curr_val = _to_float(curr_metrics.get(metric))
        prev_val = _to_float(prev_metrics.get(metric))

        if curr_val is None and prev_val is None:
            continue  # Not tracked — skip
        if prev_val is None:
            messages.append(f"  {metric}: prev=N/A, curr={curr_val:.4f} — skip (no baseline)")
            continue
        if curr_val is None:
            messages.append(f"  {metric}: prev={prev_val:.4f}, curr=N/A — WARN (metric disappeared)")
            continue

        floor = prev_val * (1.0 - threshold)
        pct_change = (curr_val - prev_val) / max(abs(prev_val), 1e-9) * 100.0

        if curr_val >= floor:
            status = "OK"
        else:
            status = f"REGRESSION (delta={pct_change:+.1f}%, floor={floor:.4f})"
            any_regression = True

        messages.append(
            f"  {metric}: prev={prev_val:.4f}, curr={curr_val:.4f} "
            f"({pct_change:+.1f}%) — {status}"
        )

    return (not any_regression), messages


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ── CLI ───────────────────────────────────────────────────────────────────────


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="A3.1: CI gate — fail if new model metrics regress vs committed version.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--model-name", required=True, help="Model identifier (e.g. ml_consensus).")
    p.add_argument(
        "--threshold",
        type=float,
        default=_DEFAULT_THRESHOLD,
        help="Max allowed fractional regression (0.05 = 5%%).",
    )
    p.add_argument(
        "--metadata-dir",
        default=str(_DEFAULT_METADATA_DIR),
        help="Directory containing model_metadata_*.json files.",
    )
    p.add_argument(
        "--allow-missing",
        action="store_true",
        help="Pass (exit 0) if previous metadata is absent (first run).",
    )
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    metadata_dir = Path(args.metadata_dir)

    # 1. Load current metrics
    current = load_current_metadata(args.model_name, metadata_dir)
    if current is None:
        print(
            f"ERROR: Current metadata not found for '{args.model_name}' in {metadata_dir}.\n"
            "       Run tools/write_model_metadata.py after training before this check.",
            file=sys.stderr,
        )
        return 1

    # 2. Load previous metrics
    previous = load_previous_metadata(args.model_name, metadata_dir)
    if previous is None:
        if args.allow_missing:
            print(
                f"INFO: No previous metadata for '{args.model_name}' — first run, gate passes."
            )
            return 0
        else:
            print(
                f"ERROR: No previous metadata found for '{args.model_name}'.\n"
                "       Use --allow-missing on the first training run.",
                file=sys.stderr,
            )
            return 1

    # 3. Compare
    passed, messages = compare_metrics(current, previous, args.threshold)

    for msg in messages:
        print(msg)

    if passed:
        print(f"\nRESULT: PASS — no regression beyond {args.threshold:.0%} threshold.")
        return 0
    else:
        print(
            f"\nRESULT: FAIL — metric regression exceeds {args.threshold:.0%} threshold.\n"
            "        Skipping model commit to protect production.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
