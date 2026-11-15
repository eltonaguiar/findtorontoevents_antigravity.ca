# Equities Plan — sma200 overlays

**Gap:** SPY/QQQ/VTI sma200 pass Sharpe/DD but LOSE terminal wealth vs B&H (1.57-1.90 vs 1.82-2.02). No equity sma200 beats B&H wealth.

**Simulation:** re-run with wealth-gate comparator + WFO stability + 1% margin:
- SPY/QQQ/VTI sma200, weekly shift(1), 10bp, 60/40 split.
- Expected: REJECT (no wealth beat). Add sma50cross and momentum as controls.
- Purpose: document that equity timing is a DD overlay, not alpha, and stop re-testing.

**Deliverables:** experiments/equities_sma200_oos_backtest.py, proof/wfo_equities_heatmap.png, proof/monter_equities_boot.png.

**Verdict:** REJECT unless a variant beats B&H wealth by >1% AND passes protocol.
