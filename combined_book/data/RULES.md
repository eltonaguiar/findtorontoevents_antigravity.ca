# Combined-Book Paper-Trade Rules (frozen)

- Starting capital: $100,000 (fixed).
- Rebalance cadence: monthly.
- Per-sleeve weight cap: 40%.
- Sleeve combination: inverse-volatility weights.
- Trade cost: 10 bps per trade (trend sleeve).
- Target book volatility cap: 5% annualized, selected by the pre-registered rule:
  pick the highest target in 5%-10% whose pre-2016 backtest max drawdown stays within
  the -15% kill limit. 6% hit -16.5%, so 5% wins. Run on pre-2016 data only.
- Put-write sleeve: tradeable proxy XYLD; backtest series CBOE PUT index.
- Trend sleeve may hold net-short bond stance; borrow cost modeled or flagged unmodeled.
- Uninvested cash earns 0%.
- Go-live gate (all must pass): >=100 months; PF >= 1.5; win rate >= 50%; worst DD
  no deeper than -20%. Reported alongside: Wilson 95% CI, binomial p-value,
  bootstrapped PF (seeded), Sharpe vs SPY, random-entry percentile, Deflated Sharpe.
- Kill criteria (either kills): live paper DD worse than -15%; OR at >=24 months any of
  PF < 1.0, win rate < 50%, Sharpe <= 0, bootstrap P(PF <= 1) > 0.5.

RULES_HASH=9bfdc2156ae01e1334705cfae80587fbfdd4191b15500ee65f0f4d4ec0979cd1
