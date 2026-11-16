#!/usr/bin/env python3
"""Add concurrency + timeout-minutes to workflows that lack them.

Formatting-preserving textual insertion:
- concurrency block inserted immediately before the top-level `jobs:` key
- timeout-minutes inserted directly after each job's `runs-on:` line

Only touches files where the block/field is absent. Idempotent.
"""
from __future__ import annotations

import sys
from pathlib import Path

WORKFLOWS = Path(".github/workflows")

CONCURRENCY_BLOCK = """concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

"""


def add_concurrency(text: str) -> tuple[str, bool]:
    if "\nconcurrency:" in text or text.startswith("concurrency:"):
        return text, False
    lines = text.split("\n")
    out = []
    inserted = False
    for line in lines:
        if not inserted and line.rstrip() == "jobs:":
            out.append(CONCURRENCY_BLOCK.rstrip("\n"))
            out.append("")
            inserted = True
        out.append(line)
    return "\n".join(out), inserted


def add_timeouts(text: str, minutes: int = 30) -> tuple[str, bool]:
    if "timeout-minutes:" in text:
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
    targets = sys.argv[1:]
    if not targets:
        print("usage: add_hygiene.py <workflow.yml> [...]")
        return 1
    changed = []
    for name in targets:
        p = WORKFLOWS / name
        if not p.exists():
            print(f"SKIP missing: {name}")
            continue
        text = p.read_text(encoding="utf-8")
        new, c1 = add_concurrency(text)
        new, c2 = add_timeouts(new)
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
