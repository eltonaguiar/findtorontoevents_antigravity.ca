# Mutual-fund and low-capital screen

This is a screening framework, not personal investment advice or a guarantee of profit. The referenced local NAV/price caches and ranker outputs are dated and do not establish current fees or availability. Verify each prospectus, sponsor page, brokerage minimum, and Canadian tax treatment before acting.

## Separate the four meanings of “less money”

1. **Investor purchase minimum:** minimum initial investment, recurring contribution, or fractional-share amount.
2. **Annual cost:** expense ratio, loads, 12b-1/distribution fees, redemption fees, brokerage commissions, currency conversion, and spread.
3. **Fund size:** AUM. AUM is not the amount an individual must invest; low AUM can create closure/liquidation risk.
4. **Maintenance:** trading frequency, rebalancing, tax reporting, and monitoring.

## Suggested screening order

- Broad, diversified index exposure rather than sector/thematic products.
- Expense ratio ideally <=0.10%, with <=0.20% as a practical outer screen.
- No front/back load, 12b-1 fee, or avoidable transaction/redemption fee.
- Initial and recurring minimum that fits the account (prefer $0-$1,000 where available); verify broker-specific fractional purchase support.
- Prefer established funds with substantial AUM and stable share-class history; do not use a tiny AUM target as a proxy for low required capital.
- Low turnover and a simple buy-and-hold or target-date index structure for low maintenance.
- Compare total-return history to the correct category/index after fees; do not rank on raw past return or a predictive model trained on survivor-only funds.

## Product types, not promises

- A broad-market open-end index mutual fund can be low-cost but may have a broker-specific minimum or transfer restrictions.
- A target-date index fund can reduce ongoing allocation work, but its glide path, fees, and availability must fit the investor.
- A money-market or Treasury fund is a cash-management choice, not a long-term equity growth substitute.
- **VTI is an ETF, not a mutual fund.** It may be a low-minimum alternative at brokers offering fractional ETF purchases. If the requirement is strictly mutual funds, compare the broker's eligible total-market/index share classes instead.
- The current remote peer package names Fidelity- and Vanguard-related examples. Treat ticker fees/minimums there as unverified snapshots, not current product facts or personalized recommendations.

## Repo treatment

- Keep `MUTUAL_FUND` marked `NOT_BUILT` in the prediction ledger.
- If useful, add a separate monthly benchmark/allocation sleeve with NAV date, next-NAV execution, distributions, fees, and input hashes.
- Do not count passive market beta or Treasury carry as a prediction-system win.
- Existing caches: 46 NAV-cache CSVs and 71 backtest-cache CSVs, latest dates in October 2026. Existing walk-forward outputs are dated 2026-10-23 and do not prove which cache snapshot produced them.

