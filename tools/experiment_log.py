#!/usr/bin/env python3
"""Git-tracked experiment log (JSON Lines) for reproducibility audit trail.

Mercury / HEDGE_FUND_ENHANCEMENT_PLAN.md §1 — one JSON object per line in
``tools/data/experiment_log.jsonl``.  Schema: ``tools/schemas/experiment_entry.schema.json``.

Examples::

    python tools/experiment_log.py log \\
        --experiment-id wf_ml60_20260402 \\
        --metrics '{\"sharpe_ann\": 1.1, \"n_trades\": 120}' \\
        --outcome promoted \\
        --notes \"After purged K-Fold embargo=7d\"

    python tools/experiment_log.py tail --limit 15

From code::

    from pathlib import Path
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools.experiment_log import append_experiment

    append_experiment(
        experiment_id=\"deflated_sharpe_rerun\",
        metrics={\"strategies_surviving\": 25},
        related_tools=[\"tools/deflated_sharpe.py\"],
    )
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_LOG = _REPO_ROOT / "tools" / "data" / "experiment_log.jsonl"
_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "experiment_entry.schema.json"


def _git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()[:40]
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def append_experiment(
    experiment_id: str,
    metrics: Dict[str, Any],
    *,
    agent: str = "",
    model_type: str = "",
    hyperparams: Optional[Dict[str, Any]] = None,
    feature_set_version: str = "",
    data_version: str = "",
    backtest_window: str = "",
    outcome: str = "unknown",
    notes: str = "",
    related_tools: Optional[List[str]] = None,
    log_path: Optional[Path] = None,
    git_sha: Optional[str] = None,
) -> Path:
    """Append one validated record as a single JSON line. Returns path written."""
    if not experiment_id or not str(experiment_id).strip():
        raise ValueError("experiment_id is required")
    if metrics is None:
        raise ValueError("metrics must be a dict (may be empty)")

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sha = git_sha if git_sha is not None else _git_sha()

    entry: Dict[str, Any] = {
        "experiment_id": experiment_id.strip(),
        "timestamp_utc": ts,
        "metrics": metrics,
    }
    if agent:
        entry["agent"] = agent
    if sha:
        entry["git_sha"] = sha
    if model_type:
        entry["model_type"] = model_type
    if hyperparams:
        entry["hyperparams"] = hyperparams
    if feature_set_version:
        entry["feature_set_version"] = feature_set_version
    if data_version:
        entry["data_version"] = data_version
    if backtest_window:
        entry["backtest_window"] = backtest_window
    if outcome and outcome != "unknown":
        entry["outcome"] = outcome
    if notes:
        entry["notes"] = notes
    if related_tools:
        entry["related_tools"] = related_tools

    _validate_entry(entry)

    path = log_path or _DEFAULT_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return path


def _validate_entry(entry: Dict[str, Any]) -> None:
    """Required-field check (stdlib only — full schema in JSON file for CI/docs)."""
    for key in ("experiment_id", "timestamp_utc", "metrics"):
        if key not in entry:
            raise ValueError("missing required field: %s" % key)
    if not isinstance(entry["metrics"], dict):
        raise ValueError("metrics must be a dict")
    oc = entry.get("outcome")
    allowed = (
        "accepted",
        "rejected",
        "promoted",
        "aborted",
        "in_progress",
        "unknown",
    )
    if oc is not None and oc not in allowed:
        raise ValueError("outcome must be one of %s" % (allowed,))


def read_tail(log_path: Optional[Path] = None, limit: int = 20) -> List[Dict[str, Any]]:
    path = log_path or _DEFAULT_LOG
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    tail = lines[-limit:] if limit > 0 else lines
    out: List[Dict[str, Any]] = []
    for line in tail:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            out.append({"_parse_error": True, "_raw": line[:200]})
    return out


def _cmd_log(args: argparse.Namespace) -> int:
    metrics: Dict[str, Any] = {}
    mj = (args.metrics_json or "").strip()
    if mj:
        metrics = json.loads(mj)
    append_experiment(
        args.experiment_id,
        metrics,
        agent=args.agent or "",
        model_type=args.model_type or "",
        feature_set_version=args.feature_set_version or "",
        data_version=args.data_version or "",
        backtest_window=args.backtest_window or "",
        outcome=args.outcome or "unknown",
        notes=args.notes or "",
        related_tools=(
            [t.strip() for t in args.related_tools.split(",") if t.strip()]
            if args.related_tools
            else None
        ),
        log_path=Path(args.log_file) if args.log_file else None,
    )
    print("logged -> %s" % (args.log_file or _DEFAULT_LOG))
    return 0


def _cmd_tail(args: argparse.Namespace) -> int:
    rows = read_tail(Path(args.log_file) if args.log_file else None, args.limit)
    print(json.dumps(rows, indent=2, ensure_ascii=False))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("log", help="append one experiment row")
    pl.add_argument("--experiment-id", required=True)
    pl.add_argument("--metrics", dest="metrics_json", default="", help="JSON object string")
    pl.add_argument("--agent", default="")
    pl.add_argument("--model-type", default="")
    pl.add_argument("--feature-set-version", default="")
    pl.add_argument("--data-version", default="")
    pl.add_argument("--backtest-window", default="")
    pl.add_argument(
        "--outcome",
        default="unknown",
        choices=(
            "accepted",
            "rejected",
            "promoted",
            "aborted",
            "in_progress",
            "unknown",
        ),
    )
    pl.add_argument("--notes", default="")
    pl.add_argument("--related-tools", default="", help="comma-separated paths")
    pl.add_argument("--log-file", default="", help="override default jsonl path")
    pl.set_defaults(func=_cmd_log)

    pt = sub.add_parser("tail", help="print last N entries as JSON array")
    pt.add_argument("--limit", type=int, default=20)
    pt.add_argument("--log-file", default="")
    pt.set_defaults(func=_cmd_tail)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
