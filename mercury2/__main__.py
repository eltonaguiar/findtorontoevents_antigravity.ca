# -*- coding: utf-8 -*-
"""Mercury 2 — Entry point for `python -m mercury2`."""

import sys

if len(sys.argv) > 1 and sys.argv[1] == "train":
    from .trainer import run_training
    run_training()
else:
    from .scanner import run_scan
    run_scan()
