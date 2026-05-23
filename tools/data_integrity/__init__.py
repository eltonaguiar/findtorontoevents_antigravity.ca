"""Diagnostic scripts for pick ledger data integrity.

These scripts are READ-ONLY. They do NOT modify live pick data, filters,
gates, or strategy code. Each script exits non-zero when a configurable
threshold is breached so it can be wired into CI later.
"""
