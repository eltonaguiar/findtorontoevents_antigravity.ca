# Forex Plan — sma200 on majors

**Gap:** No dedicated forex sma200 backtest exists; shadow WR 6.82%, money_ready NOT_READY, ^DXY n=0. Blocked by insufficient/clean data.

**Simulation:** major pairs (EURUSD, GBPUSD, USDJPY, AUDUSD, NZDUSD) sma200, weekly shift(1), 10bp + estimated spread, 60/40 split, wealth gate vs pair B&H.

**Expected verdict:** REJECT / INSUFFICIENT_DATA. Purpose: close the coverage gap with protocol-grade evidence; do not chase.

**Deliverables:** experiments/forex_sma200_oos_protocol.py, proof/*.

**Verdict:** REJECT unless a pair beats B&H wealth >1% and passes all gates.
