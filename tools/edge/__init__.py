"""Per-asset-class edge-stability + latest-pick performance analysis.

Backward-looking complement to the forward-looking research orchestrator
in `tools/research/`. Measures whether SHIPPED strategies have CONSISTENT
edge across multiple time windows (7d / 30d / 90d / all-time), flags
latest-pick decay or lift, surfaces per-class consistency verdicts on
`/audit/edge_stability.html`.

Reuses metric helpers from `alpha_engine/walk_forward_validator.py` +
`tools/edge_decay_monitor.py` — no duplicate WR/PF math.
"""
