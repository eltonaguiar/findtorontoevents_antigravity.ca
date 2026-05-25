"""Unified audit testing framework.

Import everything from the framework with:
    from tools.audit_test_framework import AuditTest, <TestClasses>..., run_audit_tests
"""

from .base import AuditTest
from .tests import (
    AssetClassificationCheck,
    BacktestTableCheck,
    DataFreshnessCheck,
    DbHealthCheck,
    GhostRowCount,
    OpenBloatCheck,
    PnLIntegrityCheck,
    SignalOutcomesCheck,
    WonPnlContradiction,
)
from .runner import run_audit_tests

__all__ = [
    "AuditTest",
    "DbHealthCheck",
    "GhostRowCount",
    "OpenBloatCheck",
    "PnLIntegrityCheck",
    "WonPnlContradiction",
    "DataFreshnessCheck",
    "AssetClassificationCheck",
    "SignalOutcomesCheck",
    "BacktestTableCheck",
    "run_audit_tests",
]
