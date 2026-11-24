"""Append-only hit log for the audit3 denylist.

The denylist fails open and is otherwise invisible: without a record of *why* a
pick was dropped, the "one-week shadow review" cannot be done. This module
appends one compact line per denial so the review can count what the gate is
actually blocking.

Safety:
* append-only JSONL; on growth past ``MAX_BYTES`` it keeps the last
  ``KEEP_LINES`` lines (no unbounded file);
* respects ``AUDIT3_DENYLIST_DISABLED`` (the test-suite kill switch) and
  ``AUDIT3_DENYLIST_HIT_LOG`` (set to ``0``/``off`` to disable, or a path);
* never raises: a logging failure must not block emission.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

REPO = Path(__file__).resolve().parent.parent
# Written under alpha_engine/data/ on purpose: the scanner workflows
# (alpha-engine-live.yml) already `git add alpha_engine/data/`, so the log is
# committed without any new workflow step. Under reports/ it was written on the
# CI runner and thrown away with the runner, which is why the weekly review had
# no data.
DEFAULT_PATH = REPO / "alpha_engine" / "data" / "audit3_denylist_hits.jsonl"
MAX_BYTES = 5_000_000
KEEP_LINES = 5_000


def hit_log_path() -> Path:
    raw = os.environ.get("AUDIT3_DENYLIST_HIT_LOG", "").strip()
    return Path(raw) if raw else DEFAULT_PATH


def enabled() -> bool:
    if str(os.environ.get("AUDIT3_DENYLIST_DISABLED", "")).strip().lower() in {
            "1", "true", "yes", "on"}:
        return False
    raw = os.environ.get("AUDIT3_DENYLIST_HIT_LOG", "").strip().lower()
    return raw not in {"0", "off", "false", "no"}


def record(pick: Mapping[str, Any], reason: str, *, path: Path | str | None = None,
           now: float | None = None) -> bool:
    """Append one denial record. Returns True if a line was written."""
    if not reason or not enabled():
        return False
    target = Path(path) if path is not None else hit_log_path()
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now or time.time())),
        "strategy": str(pick.get("strategy") or "")[:120],
        "symbol": str(pick.get("symbol") or "")[:40],
        "asset_class": str(pick.get("asset_class") or "")[:20],
        "direction": str(pick.get("direction") or "")[:10],
        "source_system": str(pick.get("source_system") or "")[:80],
        "reason": str(reason)[:300],
    }
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")
        _rotate_if_needed(target)
        return True
    except Exception:  # pragma: no cover - logging must never block emission
        return False


def _rotate_if_needed(target: Path) -> None:
    try:
        if target.stat().st_size <= MAX_BYTES:
            return
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        target.write_text("\n".join(lines[-KEEP_LINES:]) + "\n", encoding="utf-8")
    except Exception:  # pragma: no cover
        return


def summarize(path: Path | str | None = None) -> dict[str, Any]:
    target = Path(path) if path is not None else hit_log_path()
    out: dict[str, Any] = {"path": str(target), "n": 0, "by_strategy": {},
                           "by_symbol": {}, "by_class": {}, "first_ts": None,
                           "last_ts": None}
    if not target.exists():
        return out
    by_s: Counter[str] = Counter()
    by_sym: Counter[str] = Counter()
    by_c: Counter[str] = Counter()
    first = last = None
    for line in target.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except ValueError:
            continue
        out["n"] += 1
        by_s[str(r.get("strategy") or "?")] += 1
        by_sym[str(r.get("symbol") or "?")] += 1
        by_c[str(r.get("asset_class") or "?")] += 1
        ts = r.get("ts")
        first = first or ts
        last = ts or last
    out.update(by_strategy=dict(by_s.most_common(20)),
               by_symbol=dict(by_sym.most_common(20)),
               by_class=dict(by_c.most_common()),
               first_ts=first, last_ts=last)
    return out


def main(argv: list[str] | None = None) -> int:
    """Print the weekly review: what the denylist blocked, by reason/class."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", help="hit log (default: AUDIT3_DENYLIST_HIT_LOG or "
                                   "alpha_engine/data/audit3_denylist_hits.jsonl)")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args(argv)
    out = summarize(args.path)
    if args.json:
        print(json.dumps(out, indent=1))
        return 0 if out["n"] else 1
    if not out["n"]:
        print(f"no denials recorded yet ({out['path']})")
        return 1
    print(f"{out['n']} denials  {out['first_ts']} → {out['last_ts']}")
    print("by class   :", out["by_class"])
    print("by strategy:", list(out["by_strategy"].items())[:10])
    print("by symbol  :", list(out["by_symbol"].items())[:10])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
