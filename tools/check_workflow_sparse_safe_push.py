#!/usr/bin/env python3
"""
Fail if any workflow uses .github/scripts/safe_push.sh but a sparse-checkout block omits .github/
(so the script is missing on the runner). Full checkout (no sparse-checkout) is OK.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF_DIR = ROOT / ".github" / "workflows"


def main() -> int:
    errors: list[str] = []
    for path in sorted(WF_DIR.glob("*.yml")):
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if not any("safe_push.sh" in ln for ln in lines):
            continue
        i = 0
        while i < len(lines):
            if re.match(r"^\s*sparse-checkout:\s*\|?\s*$", lines[i]):
                block: list[str] = []
                base_indent = len(lines[i]) - len(lines[i].lstrip())
                i += 1
                while i < len(lines):
                    ln = lines[i]
                    if not ln.strip():
                        block.append(ln)
                        i += 1
                        continue
                    cur = len(ln) - len(ln.lstrip())
                    if cur > base_indent:
                        block.append(ln)
                        i += 1
                        continue
                    break
                body = "\n".join(block)
                if body.strip() and ".github" not in body:
                    errors.append(f"{path.name}: sparse-checkout missing .github/ but references safe_push.sh")
                continue
            i += 1

    if errors:
        print("check_workflow_sparse_safe_push: FAIL", file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    print("check_workflow_sparse_safe_push: OK (no sparse+safe_push conflicts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
