# hmm_regime_researcher — out-of-scope without macro factor history

_Generated: 2026-05-02T04:02:15.958373+00:00_

**Question:** hmm_001 — 4-state HMM, conditional Sharpe in worst regime?

**Result:** Out of scope for the static `closed_picks` snapshot. Requires 5y of (VIX z-score, DXY momentum, BTC RV, 10y-2y slope).

**Forward finding:** With n=41 picks on the only BH-FDR survivor (`multi_asset_cot`), regime decomposition is data-thin. Expand history to n≥200 first.

**Wire-up:** `alpha_engine/system_trend_detector.py` — gated by data sufficiency.

