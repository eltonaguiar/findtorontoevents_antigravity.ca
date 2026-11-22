# Capital-allocation verdict documented (no edge → hold beta, not a strategy)

**Why:** the desk had no written answer to "if we cannot prove an edge, what should
the money do?" — which invites inventing a reason to trade.

**What:** `reports/2026-11-22-capital-allocation-verdict.md`. Same 20-year window,
my own run: SPY 10.27 % CAGR / −55.2 % max DD / $70,557 on $10k; AOA 9.79 % /
−28.4 %; plain 60/40 7.79 % / −34.7 %; SPY+200-day trend 8.37 % / **−20.5 %**;
GIC 3.5 % → $19,894.

**Peer reconciliation:** Mercury3's verdict agrees in direction and on GIC; SPY
terminal value ($64,237 vs $70,557), SPY max drawdown (−50.8 % vs −55.2 %), the
trend overlay ($59,923/−19.5 % vs $49,879/−20.5 %), the 60/40 drawdown (−11.3 %
must include a trend leg; plain 60/40 is −34.7 %) and the AOA-vs-SPY ranking
(2008 start omits the GFC from AOA's own history) do not reproduce exactly.

**Verdict:** no desk strategy is sanctioned for real capital; default is broad beta
sized to drawdown tolerance, trend overlay if −55 % is unacceptable, guaranteed
bucket for money that cannot be drawn down. H-201 is a satellite candidate only
after n ≥ 100 closed forward trades.

**Verification:** figures recomputed from yfinance auto-adjusted closes,
2006-11-22 → 2026-11-20; window and values printed in the session log.
