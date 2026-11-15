# STOCKS / EQUITY

**Scan footprint:** 2,233 flagged files.

**Closed-ledger measurement:**

| n | mean | median | WR | PF |
|---:|---:|---:|---:|---:|
| 690 | +0.46% | −0.18% | 47.5% | 1.23 |

**Verdict: PROMISING, unproven.** Same fat-tail profile as crypto with a much smaller sample.
690 rows is adequate for a first test, not for a promotion.

**What has been tried:** momentum (`equity_momentum_backtest`), PEAD/anti-PEAD, VIX regime
overlays, yield-curve gates, sector rotation (ETF side), Piotski F-score (with a documented
look-ahead caveat), penny scans, insider/OpenInsider signals, magic formula, 200-DMA timing.

**Documented kills in this class** (`state/forward_test/plan.json`, `killed_in_backtest`):
`RSI2_SPY` (0.21% CAGR, SR −0.64, DSR 0.00), `DUALMOM_2` (−2.57%/yr vs matched exposure),
`DUALMOM_3` (+2.55% IS then −6.34% OOS), `SIXTY_FORTY` (−3.03%/yr vs 60/40). These four are the
best-documented negative results in the repo — do not re-test them without a new mechanism.

**What is missing:**
- excess vs SPY on the 690 rows (the single most valuable missing number in this audit);
- clustered t: if the winners concentrate on a few dates, the class is one market episode;
- survivorship control: the universe is rebuilt from gainers, so the sample is survivors.

**Next experiment:** SPY-excess + clustered t on the 690 rows. Then, only if the CI excludes
zero, a walk-forward on a fixed universe (no daily rebuild) to remove the survivor filter.
