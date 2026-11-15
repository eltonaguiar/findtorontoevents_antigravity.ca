# Bonds Plan — TLT/BND sma200

**Gap:** TLT sma200 negative Sharpe (-1.19 vs -0.46), loses wealth; BND also loses. Class blocked by missing FRED_API_KEY (no COT/macro data). Shadow WR 2.34%, PF 1.085, verdict FAIL.

**Simulation:** TLT/BND/IEH/LQD sma200, weekly shift(1), 10bp + spread, 60/40 split, wealth gate vs ETF B&H. Optionally wire FRED to unblock macro data.

**Expected verdict:** REJECT (matches existing harness).

**Deliverables:** experiments/bonds_sma200_oos_protocol.py, proof/*.

**Verdict:** REJECT unless an ETF beats B&H wealth >1% AND passes protocol.
