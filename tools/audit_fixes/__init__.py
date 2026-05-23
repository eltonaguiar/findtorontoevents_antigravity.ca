"""
Audit Critical Fixes
=====================
Implementation of the top-priority fixes from the Forensic Quantitative Audit.

Modules:
    pick_gate           — 8-gate validation (DSR, binomial, DD breaker, turnover)
    multi_tier_stoploss — 3-tier stop system (hard + trailing + time exit)
    enhanced_metrics    — Missing metrics (DD duration, IR, PSI drift, VIF)
    fixed_label_builder — Fixed-threshold labeling (replaces broken adaptive labels)
    config_fixes        — Corrected production config values

Usage:
    from tools.audit_fixes.pick_gate import PickGate, gate_picks
    from tools.audit_fixes.multi_tier_stoploss import MultiTierStopLoss
    from tools.audit_fixes.enhanced_metrics import compute_enhanced_metrics
    from tools.audit_fixes.fixed_label_builder import build_fixed_labels
"""
