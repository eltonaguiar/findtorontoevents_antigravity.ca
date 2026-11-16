#!/usr/bin/env python3
"""Add timeout-minutes per job block when missing (formatting-preserving)."""
from __future__ import annotations

import sys
from pathlib import Path

WORKFLOWS = Path(".github/workflows")


def add_job_timeout(text: str, minutes: int = 30) -> tuple[str, bool]:
    lines = text.split("\n")
    out = []
    i = 0
    inserted = False
    n = len(lines)
    while i < n:
        line = lines[i]
        out.append(line)
        # Detect a job key: exactly 2-space indent, "name:", under jobs:
        if line.startswith("  ") and not line.startswith("   ") and line.rstrip().endswith(":"):
            # Collect the job block
            j = i + 1
            block = []
            while j < n:
                nxt = lines[j]
                if nxt.strip() == "":
                    block.append(nxt)
                    j += 1
                    continue
                indent = len(nxt) - len(nxt.lstrip())
                if indent <= 2 and nxt.rstrip().endswith(":"):
                    break
                if indent < 2:
                    break
                block.append(nxt)
                j += 1
            block_text = "\n".join(block)
            if "timeout-minutes:" not in block_text and "runs-on:" in block_text:
                new_block = []
                for bl in block:
                    new_block.append(bl)
                    if bl.strip().startswith("runs-on:"):
                        indent = bl[: len(bl) - len(bl.lstrip())]
                        new_block.append(f"{indent}timeout-minutes: {minutes}")
                        inserted = True
                out.extend(new_block)
                i = j
                continue
            out.extend(block)
            i = j
            continue
        i += 1
    return "\n".join(out), inserted


def main() -> int:
    for name in sys.argv[1:]:
        p = WORKFLOWS / name
        if not p.exists():
            print(f"SKIP missing: {name}")
            continue
        text = p.read_text(encoding="utf-8")
        new, changed = add_job_timeout(text)
        if changed:
            p.write_text(new, encoding="utf-8")
            print(f"OK {name}")
        else:
            print(f"NOCHANGE {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
