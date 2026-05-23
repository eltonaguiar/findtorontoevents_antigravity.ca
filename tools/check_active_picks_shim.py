#!/usr/bin/env python3
"""
Shim for broken invocations like: python /tmp/check_active_picks.py (Windows).
Install copies to E:\\tmp and C:\\tmp via install_check_active_picks_shim.ps1.

Or run this file directly — it runs the real check_active_picks from this repo.
"""
from __future__ import annotations

import os
import runpy
import sys


def _find_repo() -> str:
    env = os.environ.get("FTE_ANTIGRAVITY_ROOT")
    if env:
        base = os.path.abspath(env)
        if os.path.isdir(os.path.join(base, "alpha_engine")):
            return base
    here = os.path.dirname(os.path.abspath(__file__))
    base = os.path.dirname(here)
    if os.path.isdir(os.path.join(base, "alpha_engine")):
        return base
    for candidate in (
        r"E:\findtorontoevents_antigravity.ca",
        r"C:\findtorontoevents_antigravity.ca",
    ):
        if os.path.isdir(os.path.join(candidate, "alpha_engine")):
            return candidate
    raise SystemExit(
        "Cannot find repo with alpha_engine/. "
        "Set FTE_ANTIGRAVITY_ROOT to your clone path."
    )


def main() -> None:
    repo = _find_repo()
    script = os.path.join(repo, "alpha_engine", "check_active_picks.py")
    if not os.path.isfile(script):
        raise SystemExit("Missing {0}".format(script))
    os.chdir(repo)
    sys.argv[0] = script
    runpy.run_path(script, run_name="__main__")


if __name__ == "__main__":
    main()
