"""
Fixes V2 — Live Performance Analysis Fixes
=============================================
Data-driven fixes based on analysis of 3,242 closed picks.

Modules:
    ghost_pick_cleaner      — Remove 663 MATIC placeholder rows (0% WR)
    time_of_day_filter      — Block entries during 08-11 UTC death zone (20% WR)
    confidence_recalibrator — Fix anti-predictive confidence above 0.65
    regime_enforcer         — Enforce position scaling by regime (87.7% panic ignored)
    stop_loss_widener       — Widen stops (46.8% SL hit rate is too high)
"""
