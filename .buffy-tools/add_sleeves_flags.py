#!/usr/bin/env python3
"""Insert the two argparse flags the sleeve block consumes.

The PF-gate patch adds code that reads `args.sleeves` and `args.benchmark`, but on
current main neither flag is registered, so the module aborts at parse time with
"unrecognized arguments: --sleeves". Run this inside a checkout before testing.
"""
from pathlib import Path

p = Path("alpha_engine/audit3_tribunal.py")
src = p.read_text()

if '"--sleeves"' in src:
    print("flags already present")
    raise SystemExit(0)

anchor = 'ap.add_argument("--picks"'
idx = src.index(anchor)
line_start = src.rfind("\n", 0, idx) + 1
indent = src[line_start:idx]

addition = (
    f'{indent}ap.add_argument("--sleeves", help="dashboard_data.json: flag top sleeves "\n'
    f'{indent}                "the tribunal does not score, or whose PF is implausible")\n'
    f'{indent}ap.add_argument("--benchmark", help="benchmark closed-ledger sidecar "\n'
    f'{indent}                "(random-entry MC timing null)")\n'
)

p.write_text(src[:line_start] + addition + src[line_start:])
print(f"inserted --sleeves and --benchmark before --picks (indent={indent!r})")
