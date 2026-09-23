#!/usr/bin/env python3
"""
tools/check_stalled_producers.py (v2.0)
======================================
GH Actions health-step that FAILS the audit-dashboard cron when any
canonical data producer has gone stale (silent-noop producer stall — see
updates/2026-06-23-money-maker-ready-june11-edition.md appendix A).

Why v2.0 (was v1.0..v1.2 for 2026-06-23 money-maker audit)
----------------------------------------------------------
v1.x checked file freshness ONLY via local disk mtime. That worked for
git-tracked files synced via `git pull`, but FALSELY reported staleness
for the 7 audit-pipeline JSON files that are EXPLICITLY excluded from
`git add` (audit-dashboard.yml lines 918-922) and EXPLICITLY gitignored
— they live ONLY on the 3 live FTP mirrors after step 49 "Deploy to all
3 FTP sites in parallel" pushes them. My LAN checkout being 3,936 commits
behind `origin/main` made v1.x always-report-RED even when the cron was
genuinely publishing fresh data.

v2.0 splits the default table into two:

* `LOCAL_FILES`  — git-tracked files (mtime check on disk via `git pull`).
* `REMOTE_FILES` — gitignored / FTP-only files (HTTP `Last-Modified`
  probe against the canonical mirror `findtorontoevents.ca`, with
  fallback to `tdotevent.ca` then `torontoevent.net`).

Each kind uses the same `FileHealth` dataclass so `--json` output is
uniform. Exit-code semantics still apply (see below). New exit code 6
means "all REMOTE mirrors unreachable / timed out / 5xx".

Author: Buffy via /money-maker-ready-June112026edition audit 2026-06-23
        v2.0 re-published under /money-maker-ready-2026-06-24-edition.
License: repo-internal (MIT-equivalent).
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict

REPO_ROOT = Path(__file__).resolve().parent.parent


# Live mirror order: canonical first; tdotevent.ca + torontoevent.net
# are CNAME clones maintained by the same FTP-deploy step. Probe them
# in order; succeed on first 200-with-Last-Modified.
DEFAULT_MIRRORS: Tuple[str, ...] = (
    "https://findtorontoevents.ca/audit/data/{rel}",
    "https://tdotevent.ca/audit/data/{rel}",
    "https://torontoevent.net/audit/data/{rel}",
)
DEFAULT_REQUEST_TIMEOUT_S = 12.0


@dataclass(frozen=True)
class CanonicalFile:  # LOCAL — git-tracked, mtime-checked
    rel_path: str
    default_max_age_h: float
    why: str


@dataclass(frozen=True)
class RemoteFile:  # REMOTE — gitignored, HTTP-Last-Modified-checked
    rel_path: str
    default_max_age_h: float
    why: str
    mirrors: Tuple[str, ...] = DEFAULT_MIRRORS


# Files that ARE git-tracked (so `git pull` brings them onto the LAN disk).
LOCAL_FILES: Tuple[CanonicalFile, ...] = (
    CanonicalFile("audit_dashboard/data/audit_surface_truth.json",      4.0,
                  "surface-truth reconciliation (git-tracked, LAN mtime)"),
    CanonicalFile("audit_dashboard/data/nav_surface_edge_matrix.json",  4.0,
                  "NAV-by-surface edge matrix (git-tracked, LAN mtime)"),
)

# Files that ARE NOT git-tracked (FTP-only deploys). Verified by
# `git cat-file -e origin/main:<path>` → false for ALL of these.
REMOTE_FILES: Tuple[RemoteFile, ...] = (
    RemoteFile("audit_dashboard/data/dashboard_data.json",        2.0,
               "main payload / 18MB (FTP-only; gitignored per .gitignore L216)"),
    RemoteFile("audit_dashboard/data/money_ready_verdict.json",   2.0,
               "honest intrabar-truth per class (FTP-only via step 49)"),
    RemoteFile("audit_dashboard/data/pick_funnel_90d.json",       2.0,
               "pick funnel 90d window (FTP-only)"),
    RemoteFile("audit_dashboard/data/pick_funnel_today.json",     2.0,
               "today's funnel (FTP-only)"),
    RemoteFile("audit_dashboard/data/walkforward_results.json",   6.0,
               "OOS folds (FTP-only; writes are heavier)"),
    RemoteFile("audit_dashboard/data/fwd_vs_bt_divergence.json",  6.0,
               "backtest overfit detector (FTP-only)"),
    RemoteFile("entry_conditions_forward.json",                   2.0,
               "sigma-geometry entry sidecar (FTP-only, repo root)"),
)


@dataclass
class FileHealth:
    path: str
    kind: str            # "local" | "remote"
    status: str          # "ok" | "stale" | "missing" | "unreadable" | "unreachable"
    age_h: Optional[float]
    threshold_h: float
    mtime_utc: Optional[str]    # ISO 8601 (LOCAL mtime OR REMOTE Last-Modified parsed)
    size_kb: Optional[float]
    why: str
    note: Optional[str] = field(default=None)
    probe_url: Optional[str] = field(default=None)  # URL that succeeded for REMOTE

    def is_failing(self) -> bool:
        return self.status in ("stale", "missing", "unreadable", "unreachable")


# ---------------------------------------------------------------------------
# Local-disk check (mtime)
# ---------------------------------------------------------------------------

def _safe_resolve(repo_root: Path, rel_path: str) -> Tuple[Path, bool]:
    """Resolve (repo_root / rel_path); reject anything that escapes repo."""
    try:
        resolved = (repo_root / rel_path).resolve()
    except (OSError, RuntimeError):
        return Path(""), False
    is_inside = resolved.is_relative_to(repo_root.resolve())
    return (resolved if is_inside else Path("")), is_inside


def _check_local(cf: CanonicalFile, threshold_h: float, repo_root: Path) -> FileHealth:
    resolved, is_inside = _safe_resolve(repo_root, cf.rel_path)
    if not is_inside:
        return FileHealth(
            path=cf.rel_path, kind="local", status="missing", age_h=None,
            threshold_h=threshold_h, mtime_utc=None, size_kb=None,
            why=cf.why, note="path-traversal-blocked",
        )
    if not resolved.exists():
        return FileHealth(
            path=cf.rel_path, kind="local", status="missing", age_h=None,
            threshold_h=threshold_h, mtime_utc=None, size_kb=None,
            why=cf.why,
        )
    try:
        st = resolved.stat()
    except OSError as e:
        return FileHealth(
            path=cf.rel_path, kind="local", status="unreadable", age_h=None,
            threshold_h=threshold_h, mtime_utc=None, size_kb=None,
            why=cf.why, note=f"OSError: {type(e).__name__}: {e}",
        )
    age_h = (datetime.now(timezone.utc).timestamp() - st.st_mtime) / 3600
    status = "ok" if age_h <= threshold_h else "stale"
    return FileHealth(
        path=cf.rel_path, kind="local", status=status, age_h=round(age_h, 2),
        threshold_h=threshold_h,
        mtime_utc=datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
        size_kb=round(st.st_size / 1024, 1),
        why=cf.why,
    )


# ---------------------------------------------------------------------------
# Remote HTTP probe (LAST-MODIFIED)
# ---------------------------------------------------------------------------

def _try_one_url(url: str, timeout_s: float) -> Tuple[Optional[datetime], Optional[int], Optional[str]]:
    """Returns (lastmod_dt | None, content_length | None, error_msg | None).

    Uses HEAD with redirect-follow and short timeout. urllib raises on
    non-2xx by default; we suppress that and read status manually.
    """
    # urllib3 / wakomoted behind CDN sometimes title-cases ("Last-modified")
    # or lowercases headers; normalize to lowercase for robust lookup.
    opener = urllib.request.build_opener()
    req = urllib.request.Request(url, method="HEAD")
    req.add_header("User-Agent", "check_stalled_producers/2.0 (+repo-internal)")
    try:
        with opener.open(req, timeout=timeout_s) as resp:
            head = {k.lower(): v for k, v in resp.headers.items()}
            lastmod_raw = head.get("last-modified")
            cl_raw = head.get("content-length")
            lastmod = parsedate_to_datetime(lastmod_raw) if lastmod_raw else None
            cl = int(cl_raw) if (cl_raw and cl_raw.isdigit()) else None
            return lastmod, cl, None
    except urllib.error.HTTPError as e:
        return None, None, f"HTTPError {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return None, None, f"URLError: {e.reason}"
    except (OSError, TimeoutError) as e:
        return None, None, f"{type(e).__name__}: {e}"
    except ValueError as e:
        return None, None, f"Last-Modified parse failed: {e}"


def _check_remote(rf: RemoteFile, threshold_h: float) -> FileHealth:
    """Probe mirrors in order. First 200-with-Last-Modified wins.

    Failure modes (recorded in FileHealth.status):
      - missing      → ALL mirrors returned HTTP 404 (server says no file)
      - unreachable  → ANY non-404 failure (timeout / 5xx / network /
                       200-OK-but-no-Last-Modified)
      - stale        → responded 200 but Last-Modified > threshold
      - ok           → responded 200 and Last-Modified within threshold

    Mirrors are probed in order; the first successful 200-with-Last-Modified
    wins. If that mirror is FRESH, we trust it (canonical source of truth)
    even if mirror #2 is stale (avoids spurious RED on partial deploys).
    """
    errs: List[str] = []
    for tmpl in rf.mirrors:
        url = tmpl.format(rel=rf.rel_path)
        lastmod, cl, err = _try_one_url(url, DEFAULT_REQUEST_TIMEOUT_S)
        if err is None and lastmod is not None:
            age_h = (datetime.now(timezone.utc) - lastmod).total_seconds() / 3600
            status = "ok" if age_h <= threshold_h else "stale"
            return FileHealth(
                path=rf.rel_path, kind="remote", status=status,
                age_h=round(age_h, 2), threshold_h=threshold_h,
                mtime_utc=lastmod.isoformat(),
                size_kb=round(cl / 1024, 1) if cl else None,
                why=rf.why, probe_url=url,
            )
        # Capture per-mirror error for end-of-loop classification.
        # Error is None iff server returned 200 but lacked Last-Modified;
        # in that case the probe is "soft-failed" (count as unreachable,
        # NOT as missing).
        errs.append(err or "200-OK-but-no-Last-Modified")
    all_404 = bool(errs) and all(e.startswith("HTTPError 404") for e in errs)
    return FileHealth(
        path=rf.rel_path, kind="remote",
        status="missing" if all_404 else "unreachable",
        age_h=None, threshold_h=threshold_h, mtime_utc=None, size_kb=None,
        why=rf.why,        note="; ".join(errs)[:300],
    )


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def check_all(repo_root: Path, thresholds: Dict[str, float]) -> List[FileHealth]:
    out: List[FileHealth] = []
    for cf in LOCAL_FILES:
        h = thresholds.get(cf.rel_path, cf.default_max_age_h)
        out.append(_check_local(cf, h, repo_root))
    for rf in REMOTE_FILES:
        h = thresholds.get(rf.rel_path, rf.default_max_age_h)
        out.append(_check_remote(rf, h))
    return out


def _parse_table_overrides(raw: List[str]) -> Dict[str, float]:
    """ --threshold-override path=hours per-arg; rejects empty components. """
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


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render_text(healths: List[FileHealth]) -> str:
    rows: List[str] = []
    rows.append(f"{'KIND':<7} {'FILE':<54} {'STATUS':<12} {'AGE(h)':>8} {'THR(h)':>8}  {'SIZE(KB)':>8}  WHY")
    rows.append("-" * 120)
    for h in healths:
        age = "—" if h.age_h is None else f"{h.age_h:.2f}"
        size = "—" if h.size_kb is None else f"{h.size_kb:.1f}"
        note = f"  //{h.note}" if h.note else ""
        rows.append(
            f"{h.kind:<7} {h.path:<54} {h.status:<12} {age:>8} {h.threshold_h:>8.1f}  {size:>8}  {h.why}{note}"
        )

    ok = sum(1 for h in healths if h.status == "ok")
    stale = sum(1 for h in healths if h.status == "stale")
    bad = sum(1 for h in healths if h.status in ("missing", "unreadable", "unreachable"))
    rows.append("")
    rows.append(
        f"RESULT: ok={ok}  stale={stale}  missing_or_unreadable_or_unreachable={bad}  total={len(healths)}"
    )
    failing = [h for h in healths if h.is_failing()]
    if failing:
        rows.append("FAILING PATH(S):")
        for h in failing:
            extra = f"  ({h.note})" if h.note else ""
            age = "—" if h.age_h is None else f"{h.age_h}h"
            mt = h.mtime_utc or "—"
            probe = f" probe={h.probe_url}" if h.probe_url else ""
            rows.append(f"  - {h.path}  kind={h.kind}  status={h.status}  age={age}  mtime={mt}{probe}{extra}")
    return "\n".join(rows)


def render_json(healths: List[FileHealth]) -> str:
    return json.dumps([asdict(h) for h in healths], indent=2) + "\n"


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=(
            "GH Actions health-step (v2.0) that fails the audit-dashboard cron "
            "if any canonical data producer has gone stale. v2.0 splits the "
            "default table into LOCAL_FILES (mtime) vs REMOTE_FILES (HTTP "
            "Last-Modified probe against live FTP mirrors). See "
            "updates/2026-06-23-stalled-producer-detector.md for architecture."
        ),
    )
    ap.add_argument("--repo-root", default=str(REPO_ROOT),
                    help=f"Repo root (default: {REPO_ROOT})")
    ap.add_argument("--strict", action="store_true",
                    help="Use 1.0h threshold everywhere. Mutually exclusive with --threshold-hours.")
    ap.add_argument("--threshold-hours", type=float, default=None,
                    help="Override default thresholds globally. Mutually exclusive with --strict.")
    ap.add_argument("--threshold-override", action="append", default=[],
                    help="Per-file override: path=hours (can repeat).")
    ap.add_argument("--json", action="store_true",
                    help="Emit JSON (for GH Actions $GITHUB_OUTPUT or parsing).")
    ap.add_argument("--no-http", action="store_true",
                    help="Skip REMOTE probes (treat them as not-configured); "
                         "useful for offline CI runners or air-gapped envs.")
    args = ap.parse_args(argv)

    if args.strict and args.threshold_hours is not None:
        print("ERROR: --strict and --threshold-hours are mutually exclusive.",
              file=sys.stderr)
        return 5

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.exists():
        print(f"ERROR: repo root does not exist: {repo_root}", file=sys.stderr)
        return 3

    thresholds: Dict[str, float] = {}
    if args.strict:
        for cf in LOCAL_FILES:
            thresholds[cf.rel_path] = 1.0
        for rf in REMOTE_FILES:
            thresholds[rf.rel_path] = 1.0
    if args.threshold_hours is not None:
        for cf in LOCAL_FILES:
            thresholds[cf.rel_path] = args.threshold_hours
        for rf in REMOTE_FILES:
            thresholds[rf.rel_path] = args.threshold_hours
    try:
        overrides = _parse_table_overrides(args.threshold_override)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 4

    known_paths = {cf.rel_path for cf in LOCAL_FILES} | {rf.rel_path for rf in REMOTE_FILES}
    unknown_overrides = [p for p in overrides if p not in known_paths]
    for p in unknown_overrides:
        print(f"WARN: --threshold-override path not in any table, ignored: {p}", file=sys.stderr)
        overrides.pop(p, None)
    thresholds.update(overrides)

    out: List[FileHealth] = []
    for cf in LOCAL_FILES:
        h = thresholds.get(cf.rel_path, cf.default_max_age_h)
        out.append(_check_local(cf, h, repo_root))
    if args.no_http:
        for rf in REMOTE_FILES:
            out.append(FileHealth(
                path=rf.rel_path, kind="remote", status="unreachable",
                age_h=None, threshold_h=thresholds.get(rf.rel_path, rf.default_max_age_h),
                mtime_utc=None, size_kb=None, why=rf.why,
                note="skipped: --no-http",
            ))
    else:
        for rf in REMOTE_FILES:
            h = thresholds.get(rf.rel_path, rf.default_max_age_h)
            out.append(_check_remote(rf, h))

    if args.json:
        print(render_json(out))
    else:
        print(render_text(out))

    n_unreachable = sum(1 for h in out if h.status == "unreachable")
    n_missing = sum(1 for h in out if h.status == "missing")
    n_stale = sum(1 for h in out if h.status == "stale")
    if n_unreachable > 0:
        return 6
    if n_missing > 0:
        return 2
    if n_stale > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
