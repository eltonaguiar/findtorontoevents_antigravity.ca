#!/usr/bin/env python3
"""Stub one missing module-level name so the next runtime error becomes visible.

DIAGNOSTIC ONLY. Used to enumerate how many distinct defects main's tribunal has,
one crash at a time, in an isolated worktree. Nothing here is proposed for main.

Usage: stub_missing_name.py <file> <name>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
name = sys.argv[2]
src = path.read_text()

if re.search(rf'(^|\n)(def |class |{re.escape(name)}\s*=)', src.split("def build_report")[0]):
    print(f"{name} already defined above build_report — not stubbing")
    raise SystemExit(0)

used_as_call = re.search(rf'\b{re.escape(name)}\s*\(', src) is not None
if used_as_call:
    stub = (f'def {name}(*args, **kwargs):\n'
            f'    """DIAGNOSTIC STUB — real definition missing on main."""\n'
            f'    return max(int(args[0]), 1) if args and isinstance(args[0], int) else None\n\n\n')
else:
    stub = f'{name} = None  # DIAGNOSTIC STUB — real definition missing on main\n\n'

anchor = "def build_report("
if anchor in src:
    src = src.replace(anchor, stub + anchor, 1)
else:
    src = src.rstrip() + "\n\n" + stub

path.write_text(src)
import ast
ast.parse(src)
print(f"stubbed {name} ({'callable' if used_as_call else 'value'}) before build_report")
