#!/usr/bin/env python3
"""
DSR (Deflated Sharpe Ratio) — thin wrapper for h037_forward_verification.py
============================================================================
Exports deflated_sharpe_ratio() using the canonical implementation in
tools/deflated_sharpe.py (Harvey-Liu / Bailey-Lopez de Prado).
"""

from __future__ import annotations

import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from alpha_engine.deflated_sharpe import deflated_sharpe_ratio as _dsr_impl

# Re-export so h037_forward_verification.py can do:
#   from tools.dsr import deflated_sharpe_ratio
deflated_sharpe_ratio = _dsr_impl