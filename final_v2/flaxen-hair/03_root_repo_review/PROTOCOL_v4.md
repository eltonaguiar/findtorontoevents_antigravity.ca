# Protocol v4 — Crypto Funding-Rate Carry

**Status:** locked before any v4 result is inspected.
**Family:** market-neutral carry (the last documented edge testable with available keyless data).

## Hypothesis

Perpetual funding is a fee paid by the crowded side. A delta-neutral position (long spot, short
perp) can harvest positive funding. If funding persists, a diversified basket of high-funding
perps should earn a positive, low-beta return net of costs.

## Data

- Binance USD-M perpetual funding history (`fapi/v1/fundingRate`), 8-hour intervals, paginated.
- Universe: 30 liquid USDT perps (same list as v3 crypto).
- Daily funding = sum of the day's intervals. Symbols with <21 days of history are excluded at
  rebalance.
- Cash: 13-week T-bill (Treasury.gov).
- Funding data starts ~2019-09; train **2020-01-01..2023-12-31**, OOS **2024-01-01..last**.

## Candidates (cumulative N = 20 + 3 = 23)

| ID | Rule | Rebalance |
|---|---|---|
| H21 | Long spot/short perp on the **top 5** symbols by trailing 7-day funding, only if funding >0; equal weight | weekly |
| H22 | BTC only: long spot/short perp when trailing 7-day BTC funding >0, else cash | weekly |
| H23 | Top 10 positive-funding symbols, equal weight | weekly |

## Costs and execution

- 10 bps per side on notional changes (spot + perp legs assumed netted into one 10 bps charge;
  this is optimistic — a 20 bps sensitivity is reported).
- Signal at close t; position from t+1.
- No basis PnL modeled (delta-neutral assumption); funding is the return. Basis/liquidation risk
  is declared, not modeled.

## Gates

1. OOS net Sharpe ≥1.0.
2. OOS net CAGR > cash CAGR (T-bill).
3. ≥30 weekly rebalances in OOS.
4. DSR ≥0.95 at cumulative N=23.
5. Bootstrap 5th-percentile Sharpe >0.
6. 2× cost Sharpe ≥0.5.
7. Execution lag (5 days) Sharpe ≥1.0.
8. PBO/SPA reported; with 3 candidates PBO is underpowered and cannot alone prove.

Failure → NOT_PROVED. This family is expected to have a lower Sharpe than v1/v2's retrospective
H10 but a more credible economic basis; the burden of proof is unchanged.
