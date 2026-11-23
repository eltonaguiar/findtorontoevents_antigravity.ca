RANKED-LIST DRAFT (copilot, 2026-11-23) -- supersedes the ranked section of notes/per-asset-class-plan-copilot-2026-11-23
ONE CHANGE SINCE THE 02:05Z PLAN: R2b crypto funding/carry has been MEASURED and it is DEAD. Everything else stands.

CRITERION: risk-adjusted NET return on committed capital, net of measured cost, against the 4.32% programme hurdle (tools/capacity_model.py HURDLE_TBILL_APR = 0.0432).
TIE-BREAKS, in order: (1) cost CERTAINTY -- measured beats assumed; (2) PIT data quality; (3) sample depth n; (4) capacity.

RANK | CLASS | THE NUMBER THAT DECIDES IT | VERDICT
-----|-------|----------------------------|--------
 1 | ETFs | Sharpe 0.44 (best of 5 classes), MaxDD -25.9% (shallowest return-generating), measured cost 1-2bp, PIT clean, no borrow, no FX. n=24 over 5y. | CANDIDATE
 2 | STOCKS passive index | Sharpe 0.29, but ACTIVE value is DEAD: HML gross +0.11%/yr, net +0.02%/yr, 44 monthly rebalances, 186 names, killed on frozen arm 1. | CANDIDATE (passive only) / active DEAD
 3 | COMMODITIES | Sharpe 0.22 but PF 0.31, WR 11%, n=28, one contract 57% of book. Prices not roll-adjusted. | DEAD
 4 | CRYPTO funding/carry (R2b) | Gross 3.57%/yr, cost 0.50%, NET 3.07%/yr vs 4.32% hurdle. 4235 intervals, 5 symbols, 218 days. Fails by 1.25pp. | DEAD (new today)
 5 | PREDICTION MARKETS | No scored test yet. Correct metric is Brier/log-loss + calibration slope, NOT Sharpe. Data present (data/kalshi_snapshots, polymarket/kalshi modules). | CANDIDATE
 6 | FOREX | Sharpe -0.03, PF 0.55, WR 40%, n=53, USDJPY 55% concentration. Measured cost 7.53bp (upper bound). | DEAD
 7 | BONDS | n=8. PF 0/WR 0%. Cannot rank a class on 8 observations. | UNKNOWN
 8 | CRYPTO directional | Sharpe -0.21 (worst), MDD -87.8%, ret -14.9%/yr, AND the ledger is broken: 1864 duplicate signal-ts groups, EXPIRED->WON mislabels. Worst on both axes. | DEAD

TOP THREE, AND HOW A HUMAN SHOULD HOLD THEM:
 1. ETFs -> BUY AND HOLD a broad index ETF. NOT entry-with-TP/SL: there is no timing edge to justify turnover against a 4.32% hurdle, and the only candidate timing rule (R4b) is unproven and forward-only until ~2031.
 2. STOCKS -> BUY AND HOLD an index. Do NOT run HML or any active single-name selection: our own test says the gross premium is +0.11%/yr, i.e. absent BEFORE cost is applied.
 3. COMMODITIES -> DO NOT HOLD on our evidence. Reopen only with roll-adjusted continuous series.

WHY ETF IS #1 AND IT IS NOT CLOSE: every class is judged net of a 4.32% hurdle, and only ETF combines (a) the best risk-adjusted return, (b) a cost we have MEASURED at 1-2bp rather than assumed, (c) prices that are PIT-clean, and (d) no borrow and no FX exposure. The other classes have to overcome a fee and execution disadvantage before any alpha discussion starts.

BUYABLE-4 FEE ARITHMETIC (explicitly requested; $100k held 10 years). Trade costs are OUR verified Questrade tariff; MER ranges are published industry ranges and are marked INFO because WE HAVE NOT MEASURED THEM.
 STOCKS: direct = $0 commission + measured 4.98bp round trip + $0 ongoing -> ~$50-500 one-off, turnover dependent. ETF wrapper ~$1,000-2,000 (0.03-0.20% MER). Index mutual fund ~$3,000-6,000 (0.30-0.60% MER + $9.95/trade). Active mutual fund ~$15,000-22,000 (1.5-2.2% MER + $9.95/trade).
 ETFs: the ETF IS the exposure, so the comparison is wrapper cost only: 0.03-0.25% MER, $0 commission, 1-2bp spread -> the cheapest buyable vehicle we can actually execute.
 BONDS: direct bonds need a $5,000 minimum, carry no MER, but retail-size bid-ask is wide and UNMEASURED -> direct bond cost is UNKNOWN. Bond ETF ~500-3,500 (0.05-0.35% MER + 1-2bp). Bond index MF ~3,000-6,000. Active bond MF ~10,000-15,000 (1.0-1.5% MER).
 MUTUAL FUNDS: $9.95/trade is the only trade cost, so the ENTIRE decision is MER. Index MF 0.30-0.60% vs active 1.5-2.2% -> the active manager must beat the index by ~1.2-1.9%/yr BEFORE tax just to tie. We have no evidence any manager we can select does that, and we have 0 INVESTABLE and 0/55 surviving deflation to suggest we would not detect it if they did.
 FOUR-WAY RESULT: ETF wins on every axis we can measure. Direct holding wins ONLY if you have a proven edge, which we do not. Index mutual fund is acceptable where no ETF exists. Active mutual fund is dominated by ~1.2-1.9%/yr of fee drag with no demonstrated offset.

WHAT WOULD CHANGE THIS RANKING, STATED IN ADVANCE:
 - ETF: only a forward-proven timing rule (R4b), earliest ~2031. Nothing else.
 - PREDICTION MARKETS: a proper calibration test could move it above BONDS/FOREX quickly, because its metric is different (Brier vs market-implied baseline, not Sharpe).
 - BONDS: needs n>=100 with a PIT store; currently unrankable, not merely bad.
 - COMMODITIES: needs roll-adjusted history before any re-test is meaningful.
 - CRYPTO: needs the ledger repaired (duplicate signal-ts, EXPIRED->WON) before ANY crypto result can be believed; carry already failed on clean data.

THE UNCOMFORTABLE CONCLUSION, unchanged: 0 INVESTABLE, 0/55 surviving deflation at SR*=1.014, 146-trial debt. The rational action is to MINIMISE FEES on a diversified ETF and treat every active row above as unproven. Fee minimisation is the one edge we can prove -- it is arithmetic, not alpha.

ZERO CAPITAL SANCTIONED. NOT INVESTMENT ADVICE.
