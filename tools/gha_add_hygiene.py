#!/usr/bin/env python3
"""Add concurrency + timeout-minutes to workflows that lack them.

Formatting-preserving textual insertion:
- concurrency block inserted immediately before the top-level `jobs:` key
- timeout-minutes inserted directly after each job's `runs-on:` line

Only touches files where the block/field is absent. Idempotent.

Usage:
  python tools/gha_add_hygiene.py [--timeout N] [--cancel-in-progress true|false] \
      <workflow.yml> [...]

Defaults: --timeout 30, --cancel-in-progress true.
Use --cancel-in-progress false for workflows that push to main or run long
backtests (a superseded run should be allowed to finish its push).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

WORKFLOWS = Path(".github/workflows")


def _concurrency_block(cancel_in_progress: bool) -> str:
    return (
        "concurrency:\n"
        "  group: ${{ github.workflow }}-${{ github.ref }}\n"
        f"  cancel-in-progress: {'true' if cancel_in_progress else 'false'}\n"
    )


def add_concurrency(text: str, cancel_in_progress: bool = True) -> tuple[str, bool]:
    if "\nconcurrency:" in text or text.startswith("concurrency:"):
        return text, False
    lines = text.split("\n")
    out = []
    inserted = False
    for line in lines:
        if not inserted and line.rstrip() == "jobs:":
            out.append(_concurrency_block(cancel_in_progress).rstrip("\n"))
            out.append("")
            inserted = True
        out.append(line)
    return "\n".join(out), inserted


def _has_job_level_timeout(text: str) -> bool:
    """True if any timeout-minutes is at job-level indent (<=4 spaces).
    Step-level timeouts (8+ spaces, under a step) do not count."""
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("timeout-minutes:"):
            indent = len(line) - len(line.lstrip())
            if indent <= 4:
                return True
    return False


def add_timeouts(text: str, minutes: int = 30) -> tuple[str, bool]:
    if _has_job_level_timeout(text):
        return text, False
    lines = text.split("\n")
    out = []
    inserted = False
    for line in lines:
        out.append(line)
        stripped = line.strip()
        if stripped.startswith("runs-on:"):
            indent = line[: len(line) - len(line.lstrip())]
            out.append(f"{indent}timeout-minutes: {minutes}")
            inserted = True
    return "\n".join(out), inserted


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--cancel-in-progress", default="true", choices=["true", "false"])
    ap.add_argument("targets", nargs="+")
    args = ap.parse_args()

    cancel = args.cancel_in_progress == "true"
    changed = []
    for name in args.targets:
        p = WORKFLOWS / name
        if not p.exists():
            print(f"SKIP missing: {name}")
            continue
        text = p.read_text(encoding="utf-8")
        new, c1 = add_concurrency(text, cancel)
        new, c2 = add_timeouts(new, args.timeout)
        if new != text:
            p.write_text(new, encoding="utf-8")
            changed.append((name, c1, c2))
            print(f"OK {name}: concurrency={c1} timeout={c2}")
        else:
            print(f"NOCHANGE {name}")
    print(f"\nChanged {len(changed)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
