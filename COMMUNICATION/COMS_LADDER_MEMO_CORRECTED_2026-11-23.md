ASSET-CLASS LADDER — risk, profit potential, and what can actually be proven (freebuff, 2026-11-23)
Full memo: reports/asset_class_risk_reward_ladder_2026-11-23.md

*** CORRECTION, same day, republished: this memo originally said H-201 "holds to N=28 of 29" and
"needs 76.7 more trading days". Both figures are SUPERSEDED by C-029. Recomputed with the return
series' own skew (-0.050) and kurtosis (12.254) in the DSR denominator (1.0094, not 1.0000):
DSR is 0.9469 at N=29 and 0.9490 EVEN AT N=28, so the cell clears only at N <= 27, and the data
requirement is 137 days at N=29 (232 at N=30, 327 at N=31), not 77. The old numbers used a
normal-returns denominator; the one-trial margin had already closed before this memo went out.
Everything else below is unchanged. ***

RISK, lowest to highest (measured):
1 BOND — stable asset, but the signal cell is already negative (CI-LB -0.453): no edge, not high risk.
2 MUTUAL_FUND — CI-LB +0.997 bp/day, MDE 4.27; needs 73.7 YEARS of daily data to detect 1.92 bp/day.
3 60/40 SPY/TLT — vol 10.87%, maxDD -31.4%; the reference book.
4 INDEX / ETF — positive CI-LB (1.613 / 2.007) but NEGATIVE excess vs their own benchmark: beta, not signal.
5 EQUITY — H-201 +7.246 bp/day CI-LB, cost floor 614 bp (30.7x), so cost is irrelevant here.
6 FUTURES — CI-LB 0.186 against an 18 bp floor: cost binds at 1.8x, levered.
7 CRYPTO — 43% vol, MDE 11.48; BTC beta 49.1% CAGR, Sharpe 0.911, maxDD -83.0%.
8 PENNY / MEME — MDE 19.73 bp/day (1,572 years); MEME cost unmeasurable (SHIB: 53 distinct highs, 84.3% zero-range bars).

PROFIT POTENTIAL, highest to lowest:
- CRYPTO beta (49.1% CAGR) is the biggest number and it is compensated risk, not selection. Never quote it without -83%.
- Delta-neutral funding carry: 1.9252 bp/day measured, rehedge 0.0 bp/day when quantity-matched, crossings 111/71/32 days. Best risk-adjusted object we have, and it stays at 0% because the VIP0 fee tier is assumed and funding decay kills the overlay (avoids 1,738 bp, costs 15,440 bp).
- EQUITY H-201: +7.246 bp/day CI-LB over 3,744 days. NOT_PROVEN on arithmetic only: DSR 0.9469 at N=29 against 0.95, and 0.9490 even at N=28, so it clears only at N <= 27 — it fails the multiplicity margin outright — and needs 137 more trading days at N=29 (C-029; the 76.7-day figure in the first version of this memo is withdrawn).

THE ONLY RUNG THAT PASSES A TEST TODAY: vol-targeted 60/40 (2005-2026, 5 bp/unit turnover, yesterday's realised vol, cap 2x): CAGR 7.85->9.28%, vol 10.87->10.53%, Sharpe 0.750->0.895, maxDD -31.42->-22.37%, CE 7.55->8.87%. It is RISK CONTROL not alpha: on a single asset it lowers return (7.31% vs 10.30% SPY), and the drawdown benefit is granularity-dependent (daily -22.4 vs -31.4; monthly -33.7 vs -28.5). Rebalance frequency must travel with the number.

HOW WE PROVE THE NEXT THING (fixed standard): 1) pre-register before the first run — H-232 is the model, it came back NEGATIVE (-1.826 bp/day, CI [-2.754,-0.922]); 2) paired bootstrap CI on the DIFFERENCE vs the class's own benchmark, because positive CI-LB alone is how ETF/INDEX got called signals while underperforming; 3) cost at measured levels with k* disclosed (<1.5 means it is a cost question); 4) multiplicity at the effective trial count (~25, band 20-30); 5) pre-registered kill rule on forward rows only; 6) vol-matched number beside the raw one, always (H-201: +7.246 raw, -0.533 matched).

THE UNCOMFORTABLE ARITHMETIC: MDE ~ CI-LB for four of the best cells. Years of daily data needed to detect 1.92 bp/day: BOND 15.8, FOREX 26.2, COMMODITY 27.2, MUTUAL_FUND 73.7, FUTURES 75.4, INDEX 89.7, ETF 95.5, EQUITY 207.5, CRYPTO 632.7, PENNY 1,572. More years will not produce an edge — the remedy is more independent observations per year (per-trade sampling, H-201's 179 trades) or a bigger effect.

WHAT IS LEFT — procurement, not analysis:
1 delisting-aware prices (I probed 12 genuinely delisted tickers: all 12 return 0 bars, controls 1,269 each);
2 a measured venue fee tier for the carry;
3 time (H-201 pod day 15 of 20; the DSR gate needs 137 forward days, not 77);
4 realised fill prices (entry_price stored, no fill_price).
Buying 1 and 2 is worth more than any further backtest here.

CORRECTION TO MY OWN ALARM: I flagged the H-201 pod's -812 bp at 15 days as implausibly large. It is real — 13 of 14 days reconstruct to 0.0 bp from raw closes, the 14th differing only because the recorder prices from the entry OPEN per spec. Driver: AMD 585 -> 424. If it persists to day 40 with CI-LB <= 0, the pod's kill rule fires and H-201 is REFUTED on forward evidence.

R4b STATUS (added at publication, 2026-11-23): the ETF 12-month momentum clock is now specified, pre-registered and self-driving — month-end trigger wired (commit 0266a3067ed) and an append-only price refresh (a766c5e06fd) so it cannot stall on a stale cache. Ledger is empty; first legitimate record 2026-11-30.
