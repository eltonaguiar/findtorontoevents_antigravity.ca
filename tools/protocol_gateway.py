#!/usr/bin/env python3
"""CLI entrypoint for cross-PC protocol gateway."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cross_pc_protocol.gateway import main


if __name__ == "__main__":
    raise SystemExit(main())
