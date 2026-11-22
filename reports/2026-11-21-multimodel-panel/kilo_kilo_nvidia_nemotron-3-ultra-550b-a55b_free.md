
> code · nvidia/nemotron-3-ultra-550b-a55b:free

**CRYPTO** — blocked. Structural blocker: net expectancy −0.38% with 95% CI [−0.647, −0.114] excludes zero on the wrong side across 6836 picks; 629-cell multiple-testing search space guarantees false positives. No strategy family can overcome this without a regime filter that survives forward test.

**COMMODITY** — blocked. Structural blocker: policy-clean PF 0.29 on 48 picks (H-101 COT T+3 lag removed look-ahead; M-095 cotton 14× re-emission inflates n). Any commodity strategy citing PF>1.0 on current data is contaminated.

**EQUITY** — Strategy: SPY 5-day mean reversion. Universe: S&P 500 constituents. Signal: RSI(2) < 10 at close. Entry: next open. Exit: close of day 2 or RSI(2) > 90. Holding: max 2 days. Sizing: 1% equity risk per trade, vol-targeted to 15% annualized. Benchmark: SPY total return.
Falsification: forward n≥100, net expectancy ≤ 0 at 2× slippage (i.e., CI upper bound ≤ 0).
Confidence: 35. Not higher because 955-pick CI [−0.516, +0.720] includes zero; 19-cell search space; no regime filter tested.

**ETF** — Strategy: Sector momentum rotation. Universe: 11 SPDR sector ETFs. Signal: 63-day return rank. Entry: month-end close, long top 3 sectors equal-weight. Exit: next month-end rebalance. Holding: ~21 days. Sizing: 2% portfolio risk per sector, cash remainder. Benchmark: SPY total return.
Falsification: forward n≥100, information ratio vs SPY < 0.5 at 2× slippage.
Confidence: 30. Not higher because 589 picks show −0.003% net; 12-cell search; sector momentum has decayed post-2020.

**FOREX** — Strategy: G10 carry with vol control. Universe: G10 spot vs USD. Signal: 3-month carry rank (IRS differential). Entry: week-end roll, long top 3 yield / short bottom 3. Exit: weekly rebalance. Holding: 5–7 days. Sizing: vol-target 10% annualized, max 5% per leg. Benchmark: DXY.
Falsification: forward n≥100, net expectancy ≤ 0 at 2× slippage.
Confidence: 25. Not higher because 264 picks, CI includes zero; 18-cell search; carry crashes in risk-off regimes unaddressed.

**BOND** — Strategy: 2s10s steepener on curve compression. Universe: US Treasury futures (TU, TY). Signal: 2s10s spread < 5 bps. Entry: receive 2y / pay 10y DV01-neutral at next open. Exit: spread > 25 bps or 30 calendar days. Holding: max 30 days. Sizing: $50k DV01 per leg. Benchmark: AGG total return.
Falsification: forward n≥100, net expectancy ≤ 0 at 2× slippage.
Confidence: 20. Not higher because n=37 below floor; 2-cell search; curve regime since 2022 is structural, not cyclical.

**No class clears the bar as configured.** The single configuration change most likely to reveal real edge: **increase holding period to 20–60 days and benchmark against asset-class factor models (not index total return)** — current tests force high-turnover noise trading; edges in equity/ETF/FX/bonds are factor-timing, not day-trading.
