# risk_parity_researcher — HRP degenerate without date-pivoted matrix

_Generated: 2026-05-02T04:02:15.958373+00:00_

**Question:** rp_001 — Does HRP beat equal-weight?

**Result:** Returned [('multi_asset_copytrader', 0.2), ('quan_engine', 0.2), ('unknown', 0.2), ('cta_replicator', 0.2), ('rapid_fire', 0.2)] — exact equal-weight by accident. Per-source-trade-stream representation has near-zero pairwise correlations; HRP needs a date-aligned matrix.

**Wire-up:** in `alpha_engine/regime_position_sizer.py`, build `pd.DataFrame(index=dates, columns=sources, values=daily_pnl)` before calling `hrp_allocate`.

