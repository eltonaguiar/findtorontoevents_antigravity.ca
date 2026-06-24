#!/usr/bin/env python3
"""
tools/check_stalled_producers.py
================================
GH Actions health-step that FAILS the audit-dashboard cron when any
canonical data producer has gone stale (silent-noop producer stall — see
updates/2026-06-23-money-maker-ready-june11-edition.md appendix A).

Why this exists
---------------
The `audit-dashboard.yml` cron has been reporting `conclusion: success`
while `dashboard_data.json`, `pick_funnel_90d.json`,
`walkforward_results.json`, `fwd_vs_bt_divergence.json`, and
`entry_conditions_forward.json` have gone stale since 2026-06-03
(~20 days at first detected). The cron's narrow per-job-scope success
masks a downstream "publish into disk" silent no-op, likely fed by a
stale `MYSQL_PASSWORD` GHActions secret vs the LAN-rotated DB creds.

Per the `/money-maker-ready` skill v1.1 §0 (Freshness preflight — fail
fast if `dashboard_data.json::generated_at` > 2h), this tool is the
canonical health-step that automates that check inline at the cron,
turning today's main/silent-stall into a loud `exit 1`.

Usage
-----
  # Default (run from repo root): enforce 2h on all nine canonical files
  python3 tools/check_stalled_producers.py

  # JSON output for GH Actions `>> $GITHUB_OUTPUT`
  python3 tools/check_stalled_producers.py --json

  # Strict (1h threshold everywhere)
  python3 tools/check_stalled_producers.py --strict

  # Custom override (e.g. the audit ran 4h ago, we want a half-life check)
  python3 tools/check_stalled_producers.py --threshold-hours 4

  # Per-file override (path=hours, repeatable)
  python3 tools/check_stalled_producers.py \
    --threshold-override audit_dashboard/data/walkforward_results.json=6

Exit codes
----------
  0 — all files within freshness window
  1 — at least one file STALE (mtime > threshold, file present)
  2 — at least one file MISSING (no path on disk) OR UNREADABLE (stat() raises)
  3 — repo root not found (config error)
  4 — bad `--threshold-override` parse
  5 — argument conflict: both `--strict` AND `--threshold-hours` passed

FileHealth.status values: `"ok" | "stale" | "missing" | "unreadable"`.
Python 3.9+ required (uses `Path.is_relative_to` strictly).

Author: Buffy via /money-maker-ready-June112026edition audit 2026-06-23
License: repo-internal (MIT-equivalent).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple, List, Dict

REPO_ROOT = Path(__file__).resolve().parent.parent


# Per project idiom: small dataclass for canonical-file metadata.
@dataclass(frozen=True)
class CanonicalFile:
    rel_path: str
    default_max_age_h: float
    why: str


DEFAULT_FILE_TABLE: Tuple[CanonicalFile, ...] = (
    CanonicalFile("audit_dashboard/data/dashboard_data.json",           2.0, "main payload / 18MB"),
    CanonicalFile("audit_dashboard/data/money_ready_verdict.json",      2.0, "honest intrabar-truth per class"),
    CanonicalFile("audit_dashboard/data/pick_funnel_90d.json",          2.0, "pick funnel 90d window"),
    CanonicalFile("audit_dashboard/data/pick_funnel_today.json",        2.0, "today's funnel"),
    CanonicalFile("audit_dashboard/data/walkforward_results.json",      6.0, "OOS folds (writes are heavier)"),
    CanonicalFile("audit_dashboard/data/fwd_vs_bt_divergence.json",     6.0, "backtest overfit detector"),
    CanonicalFile("entry_conditions_forward.json",                      2.0, "sigma-geometry entry sidecar"),
    CanonicalFile("audit_dashboard/data/audit_surface_truth.json",      4.0, "surface-truth reconciliation"),
    CanonicalFile("audit_dashboard/data/nav_surface_edge_matrix.json",  4.0, "NAV-by-surface edge matrix"),
)


@dataclass
class FileHealth:
    path: str
    status: str            # "ok" | "stale" | "missing" | "unreadable"
    age_h: Optional[float] # None if missing/unreadable
    threshold_h: float
    mtime_utc: Optional[str]
    size_kb: Optional[float]
    why: str
    note: Optional[str] = field(default=None)  # error info for unreadable

    def is_failing(self) -> bool:
        return self.status in ("stale", "missing", "unreadable")


def _safe_resolve(repo_root: Path, rel_path: str) -> Tuple[Path, bool]:
    """Resolve (repo_root / rel_path); reject anything that escapes repo.

    Requires Python 3.9+ (uses `Path.is_relative_to` strictly). The Py<3.9
    string-prefix fallback was deliberately removed — a sub-path string
    collision (`/repo/root_old/...` matching `/repo/root/`) is a real
    foot-gun, and the project runs Py3.11+ per its idioms.
    """
    try:
        resolved = (repo_root / rel_path).resolve()
    except (OSError, RuntimeError):
        return Path(""), False
    is_inside = resolved.is_relative_to(repo_root.resolve())
    return (resolved if is_inside else Path("")), is_inside


def _check_one(cf: CanonicalFile, threshold_h: float, repo_root: Path) -> FileHealth:
    resolved, is_inside = _safe_resolve(repo_root, cf.rel_path)
    if not is_inside:
        return FileHealth(
            path=cf.rel_path, status="missing", age_h=None,
            threshold_h=threshold_h, mtime_utc=None, size_kb=None,
            why=cf.why, note="path-traversal-blocked",
        )
    if not resolved.exists():
        return FileHealth(
            path=cf.rel_path, status="missing", age_h=None,
            threshold_h=threshold_h, mtime_utc=None, size_kb=None,
            why=cf.why,
        )
    try:
        st = resolved.stat()
    except OSError as e:
        return FileHealth(
            path=cf.rel_path, status="unreadable", age_h=None,
            threshold_h=threshold_h, mtime_utc=None, size_kb=None,
            why=cf.why, note=f"OSError: {type(e).__name__}: {e}",
        )
    age_h = (datetime.now(timezone.utc).timestamp() - st.st_mtime) / 3600
    status = "ok" if age_h <= threshold_h else "stale"
    return FileHealth(
        path=cf.rel_path, status=status, age_h=round(age_h, 2),
        threshold_h=threshold_h,
        mtime_utc=datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
        size_kb=round(st.st_size / 1024, 1),
        why=cf.why,
    )


def _parse_table_overrides(raw: List[str]) -> Dict[str, float]:
    """ `--threshold-override path=hours` per-arg; rejects empty path/value. """
    out: Dict[str, float] = {}
    if not raw:
        return out
    for r in raw:
        if "=" not in r:
            raise ValueError(f"--threshold-override expects path=hours, got: {r!r}")
        path, hrs = r.split("=", 1)
        path = path.strip()
        if not path:
            raise ValueError(f"--threshold-override path component empty: {r!r}")
        try:
            hours = float(hrs.strip())
        except ValueError as e:
            raise ValueError(f"--threshold-override hours not numeric in {r!r}: {e}") from e
        if hours < 0:
            raise ValueError(f"--threshold-override hours must be non-negative: {r!r}")
        out[path] = hours
    return out


def check_all(repo_root: Path, thresholds: Dict[str, float]) -> List[FileHealth]:
    out: List[FileHealth] = []
    for cf in DEFAULT_FILE_TABLE:
        h = thresholds.get(cf.rel_path, cf.default_max_age_h)
        out.append(_check_one(cf, h, repo_root))
    return out


def render_text(healths: List[FileHealth]) -> str:
    rows: List[str] = []
    rows.append(f"{'FILE':<54} {'STATUS':<12} {'AGE(h)':>8} {'THR(h)':>8}  SIZE(KB)  WHY")
    rows.append("-" * 110)
    for h in healths:
        age = "—" if h.age_h is None else f"{h.age_h:.2f}"
        size = "—" if h.size_kb is None else f"{h.size_kb:.1f}"
        note = f"  //{h.note}" if h.note else ""
        rows.append(
            f"{h.path:<54} {h.status:<12} {age:>8} {h.threshold_h:>8.1f}  {size:>8}  {h.why}{note}"
        )

    ok = sum(1 for h in healths if h.status == "ok")
    stale = sum(1 for h in healths if h.status == "stale")
    missing = sum(1 for h in healths if h.status in ("missing", "unreadable"))
    rows.append("")
    rows.append(f"RESULT: ok={ok}  stale={stale}  missing_or_unreadable={missing}  total={len(healths)}")
    bad = [h for h in healths if h.is_failing()]
    if bad:
        rows.append("FAILING PATH(S):")
        for h in bad:
            extra = f"  ({h.note})" if h.note else ""
            age = "—" if h.age_h is None else f"{h.age_h}h"
            rows.append(f"  - {h.path}  status={h.status}  age={age}  mtime={h.mtime_utc or '—'}{extra}")
    return "\n".join(rows)


def render_json(healths: List[FileHealth]) -> str:
    return json.dumps([asdict(h) for h in healths], indent=2) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=(
            "GH Actions health-step that fails the audit-dashboard cron "
            "if any canonical data producer has gone stale. Per "
            "/money-maker-ready skill v1.1 §0 freshness preflight."
        ),
    )
    ap.add_argument(
        "--repo-root", default=str(REPO_ROOT),
        help=f"Repo root (default: {REPO_ROOT})",
    )
    ap.add_argument(
        "--strict", action="store_true",
        help="Use 1.0h threshold everywhere (default threshold is 2h per skill §0). "
             "Mutually exclusive with --threshold-hours (exit 5 if both given).",
    )
    ap.add_argument(
        "--threshold-hours", type=float, default=None,
        help="Override default 2h threshold globally. Mutually exclusive with --strict (exit 5).",
    )
    ap.add_argument(
        "--threshold-override", action="append", default=[],
        help="Per-file override: path=hours (can repeat), e.g. "
             "'audit_dashboard/data/walkforward_results.json=6.0'. "
             "Empty path component or non-numeric hours → exit 4.",
    )
    ap.add_argument(
        "--json", action="store_true",
        help="Emit JSON (for GH Actions `$GITHUB_OUTPUT` or downstream parsing)",
    )
    args = ap.parse_args(argv)

    # Conflict detection: --strict and --threshold-hours are mutually exclusive.
    if args.strict and args.threshold_hours is not None:
        print(
            "ERROR: --strict and --threshold-hours are mutually exclusive; "
            "use one or the other (NOT both) to avoid silent priority overwrite.",
            file=sys.stderr,
        )
        return 5

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.exists():
        print(f"ERROR: repo root does not exist: {repo_root}", file=sys.stderr)
        return 3

    # Build effective thresholds. Priority: per-file override > global > strict.
    thresholds: Dict[str, float] = {}
    if args.strict:
        for cf in DEFAULT_FILE_TABLE:
            thresholds[cf.rel_path] = 1.0
    if args.threshold_hours is not None:
        for cf in DEFAULT_FILE_TABLE:
            thresholds[cf.rel_path] = args.threshold_hours
    try:
        overrides = _parse_table_overrides(args.threshold_override)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 4

    # Warn (stderr) + drop any override with an unknown path (would be no-op).
    known_paths = {cf.rel_path for cf in DEFAULT_FILE_TABLE}
    unknown_overrides = [p for p in overrides if p not in known_paths]
    for p in unknown_overrides:
        print(
            f"WARN: --threshold-override path not in DEFAULT_FILE_TABLE, ignored: {p}",
            file=sys.stderr,
        )
        overrides.pop(p, None)
    thresholds.update(overrides)

    # NOTE: no try/except around `check_all` on purpose. Programming bugs in
    # `check_all` (TypeError, AttributeError, KeyError, etc.) should propagate
    # as a loud stack trace, NOT be silently caught as an "exit 6 → unknown
    # failure mode" — per project hygiene "no unnecessary try/catch blocks".
    # The OSError protection already lives in `_check_one`.
    healths = check_all(repo_root, thresholds)

    if args.json:
        print(render_json(healths))
    else:
        print(render_text(healths))

    n_missing = sum(1 for h in healths if h.status in ("missing", "unreadable"))
    n_stale = sum(1 for h in healths if h.status == "stale")
    if n_missing > 0:
        return 2
    if n_stale > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
