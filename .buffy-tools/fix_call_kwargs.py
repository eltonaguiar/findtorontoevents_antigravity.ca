#!/usr/bin/env python3
"""Drop keyword arguments from a call that the callee's signature does not accept.

The PF-gate patch was generated against a branch whose build_report() took extra
keyword arguments that current main's build_report() does not define, so replaying
it produced `TypeError: build_report() got an unexpected keyword argument
'require_alpha'`. This removes only those foreign kwargs, leaving the call intact.

Usage: fix_call_kwargs.py <file> <callee_name>
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
callee = sys.argv[2]
src = path.read_text()
tree = ast.parse(src)

sig: set[str] | None = None
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == callee:
        a = node.args
        sig = {x.arg for x in a.args} | {x.arg for x in a.kwonlyargs}
        break
if sig is None:
    print(f"{callee}() not found in {path}")
    raise SystemExit(1)

removed = []
# Work backwards so earlier offsets stay valid.
for node in sorted((n for n in ast.walk(tree)
                    if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Name)
                    and n.func.id == callee),
                   key=lambda n: n.lineno, reverse=True):
    foreign = [k for k in node.keywords if k.arg and k.arg not in sig]
    if not foreign:
        continue
    seg = ast.get_source_segment(src, node)
    if not seg:
        continue
    start = src.index(seg, 0) if seg in src else -1
    if start < 0:
        continue
    new_seg = seg
    for k in foreign:
        new_seg = re.sub(rf"\s*{re.escape(k.arg)}\s*=\s*[^,()]+(?:\([^()]*\))?,?", "", new_seg, count=1)
        removed.append(k.arg)
    src = src[:start] + new_seg + src[start + len(seg):]

if not removed:
    print(f"no foreign kwargs on {callee}() — nothing to do")
else:
    path.write_text(src)
    print(f"removed from {callee}(): {sorted(set(removed))}")

# Verify the result still parses.
ast.parse(path.read_text())
print("parses cleanly after edit")
