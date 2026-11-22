#!/usr/bin/env python3
"""Repair the two P0 defects in alpha_engine/audit3_tribunal.py.

Defect 1: argparse option registered twice -> ArgumentError at parse time, before
          any row is read. Keeps the FIRST registration, drops later duplicates.
Defect 2: evaluate_cell builds the cell dict with required_n and mde_pct, but
          neither name is assigned anywhere on main. Commit 1ed98e59aaa added the
          computation; merge 764fec86df2 kept the uses and dropped it. Restored
          here with the identical formula:
              required_n = int(math.ceil((2.8 * sd / abs(mean_net)) ** 2))
              mde_pct   = round(2.8 * sd / math.sqrt(n), 4)

Run inside a checkout:  python3 repair_tribunal_p0.py alpha_engine/audit3_tribunal.py
Idempotent: safe to run twice.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "alpha_engine/audit3_tribunal.py")
src = path.read_text()
changed = []

# ---- Defect 1: duplicate argparse registrations -----------------------------
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
    lines = out
    src = "\n".join(lines)
    changed.append(f"dropped duplicate argparse registrations: {sorted(set(dropped))}")

# ---- Defect 2: missing required_n / mde_pct --------------------------------
if not re.search(r'(^|[^a-z_])required_n\s*=', src):
    if "import math" not in src:
        src = src.replace("import json", "import json\nimport math", 1)
        changed.append("added 'import math'")

    anchor = "    out = dict(label)"
    if anchor not in src:
        print("FAIL: could not find 'out = dict(label)' anchor")
        sys.exit(1)

    block = '''    # --- P0 repair: required_n / mde_pct were referenced but never defined.
    # Restored with the formula from 1ed98e59aaa (see reports/TRIBUNAL_MAIN_BROKEN).
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
    changed.append("restored required_n / mde_pct computation")

path.write_text(src)

# ---- verify it compiles ----------------------------------------------------
import ast
ast.parse(path.read_text())
print("repair report:")
for c in changed or ["nothing to do (already repaired)"]:
    print(f"  - {c}")
print("  parses cleanly")
