#!/usr/bin/env python3
"""Make alpha_engine/audit3_tribunal.py RUNNABLE in an isolated worktree.

DIAGNOSTIC HARNESS — every change here is labelled and none of it is proposed for
main as-is. Its only purpose is to get the module past its own crash so the sleeve
PF gate can be exercised end to end. Each defect it works around is a real finding
recorded in reports/TRIBUNAL_MAIN_BROKEN_2026-11-19.md.

Defects handled, in the order they block execution:
  1. duplicate argparse registrations (5 flags, not 1)
  2. undefined required_n / mde_pct in evaluate_cell
  3. build_report() called with require_alpha= which its signature lacks
  4. build_report() calling global_trial_count() which is undefined

For (3) and (4) the harness prefers the real definition (import / parameter) and
falls back to a clearly-marked stub only when nothing exists, because inventing
DSR semantics would silently change grading numbers.

Usage: diagnostic_repair.py alpha_engine/audit3_tribunal.py
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "alpha_engine/audit3_tribunal.py")
src = path.read_text()
log: list[str] = []

# ---- 1. duplicate argparse registrations -----------------------------------
opt_re = re.compile(r'add_argument\(\s*"(--[A-Za-z0-9_-]+)"')
lines = src.split("\n")
seen: set[str] = set()
out: list[str] = []
dropped: list[str] = []
i = 0
while i < len(lines):
    m = opt_re.search(lines[i])
    if m and m.group(1) in seen and lines[i].lstrip().startswith(("ap.", "parser.")):
        dropped.append(m.group(1))
        depth = lines[i].count("(") - lines[i].count(")")
        i += 1
        while depth > 0 and i < len(lines):
            depth += lines[i].count("(") - lines[i].count(")")
            i += 1
        continue
    if m:
        seen.add(m.group(1))
    out.append(lines[i])
    i += 1
if dropped:
    src = "\n".join(out)
    log.append(f"1. dropped duplicate argparse registrations: {sorted(set(dropped))}")

# ---- 2. required_n / mde_pct ----------------------------------------------
if not re.search(r'(^|[^a-z_])required_n\s*=', src):
    if "import math" not in src:
        src = src.replace("import json", "import json\nimport math", 1)
    anchor = "    out = dict(label)"
    block = '''    # DIAGNOSTIC HARNESS: required_n / mde_pct were referenced but never defined
    # on main (merge 764fec86df2 dropped what 1ed98e59aaa added).
    required_n = None
    mde_pct = None
    _sd = float(boot.get("sd") or 0.0) if isinstance(boot, dict) else 0.0
    _mean = float(boot.get("mean") or 0.0) if isinstance(boot, dict) else 0.0
    if n >= 2 and _sd > 0 and _mean != 0:
        try:
            required_n = int(math.ceil((2.8 * _sd / abs(_mean)) ** 2))
            mde_pct = round(2.8 * _sd / math.sqrt(n), 4)
        except (ValueError, ZeroDivisionError):
            required_n, mde_pct = None, None
'''
    src = src.replace(anchor, block + anchor, 1)
    log.append("2. restored required_n / mde_pct (formula from 1ed98e59aaa)")

# ---- 3. require_alpha kwarg VS signature ----------------------------------
tree = ast.parse(src)
sig: set[str] | None = None
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == "build_report":
        sig = {a.arg for a in node.args.args} | {a.arg for a in node.args.kwonlyargs}
        break
if sig is not None and "require_alpha" not in sig:
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "build_report"]
    for call in calls:
        seg = ast.get_source_segment(src, call)
        if not seg or "require_alpha" not in seg:
            continue
        start = src.index(seg)
        new = re.sub(r"\s*require_alpha\s*=\s*[^,()]+(?:\([^()]*\))?,?", "", seg, count=1)
        src = src[:start] + new + src[start + len(seg):]
        log.append("3. dropped require_alpha= from the build_report() call "
                   "(signature lacks it; alpha gate NOT enforced in this run)")
        break

# ---- 4. global_trial_count ------------------------------------------------
if re.search(r'\bglobal_trial_count\(', src) and "def global_trial_count" not in src:
    defined_in = None
    for cand in Path("alpha_engine").glob("*.py"):
        try:
            if re.search(r'def global_trial_count', cand.read_text(errors="replace")):
                defined_in = cand
                break
        except OSError:
            continue
    if defined_in:
        mod = f"alpha_engine.{defined_in.stem}"
        src = src.replace("import json", f"import json\nfrom {mod} import global_trial_count  # DIAGNOSTIC", 1)
        log.append(f"4. imported global_trial_count from {mod}")
    else:
        # Insert at module level BEFORE build_report, because appending to the end
        # of the file places the def after `raise SystemExit(main())` and it never runs.
        stub = ('def global_trial_count(n_trials_local: int) -> int:\n'
                '    """DIAGNOSTIC STUB: real definition missing on main. Returns the local\n'
                '    count unchanged, which changes DSR semantics — do not merge this."""\n'
                '    return max(int(n_trials_local), 1)\n\n\n')
        anchor = "def build_report("
        if anchor in src:
            src = src.replace(anchor, stub + anchor, 1)
        else:
            src += "\n\n" + stub
        log.append("4. STUBBED global_trial_count (no definition found anywhere) — "
                   "DSR semantics altered; diagnostic only")

path.write_text(src)
ast.parse(path.read_text())

print("diagnostic repair:")
for entry in log or ["nothing to do"]:
    print(f"  - {entry}")
print("  parses cleanly")

# Report any remaining undefined names we can detect statically.
tree = ast.parse(path.read_text())
assigned = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
defined = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
imported = set()
for n in ast.walk(tree):
    if isinstance(n, ast.ImportFrom):
        imported |= {(a.asname or a.name) for a in n.names}
    elif isinstance(n, ast.Import):
        imported |= {(a.asname or a.name.split(".")[0]) for a in n.names}
import builtins
known = assigned | defined | imported | set(dir(builtins))
missing = sorted({n.id for n in ast.walk(tree)
                  if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)} - known)
if missing:
    print(f"  still-undefined names (may include module-level globals): {missing[:12]}")
