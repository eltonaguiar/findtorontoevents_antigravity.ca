# Asset-Class Winrate Verification + Edge Plan (2026-04-22)

## Scope
- Goal: verify claimed last-20 win rates for stocks/forex/commodities/bonds/ETFs, extend to last-100 and last-200, and identify where real edge exists.
- Data source used: `audit_dashboard/data/dashboard_data.json` (`picks.recent_closed`, 3,500 closed picks).
- Repro script: `tools/edge_by_asset_class.py` (updated in this PR to include claim-verification tables and robust PnL fallback).

## Verification Summary

Using the current dashboard closed-picks payload and sorting by `closed_at`:

| Asset class | Last 20 | Last 100 | Last 200 | Notes |
|---|---:|---:|---:|---|
| Stocks (equity) | 85% | 70% | 53% | Recent burst, then mean-reverts lower by 200 |
| Forex | 40% | 48% | 50% | Not 5%; roughly coin-flip to modest edge depending on filter |
| Commodities | 70% | 54% | 49% | Not 15%; edge decays but stays near neutral-positive |
| Bonds | 47.1% (n=17) | 47.1% (n=17) | 47.1% (n=17) | Too little sample for 100/200 inference |
| ETFs | 85% | 51.9% (n=77) | 51.9% (n=77) | Strong recent burst; not stable at 100+ |

### Are the originally quoted numbers real?
- **Confirmed as-is:** bonds `47.1%`, ETFs `85%` (last-20).
- **Not confirmed:** forex `5%` and commodities `15%` are not supported by current closed-pick data.
- **Stocks `65%` vs `85%` discrepancy:** this can occur when using different sorting/field logic (e.g., mixed timestamp fields, status-only vs PnL-sign win logic). The updated script now makes these assumptions explicit in one place.

## Do We Have an Edge? Where?

Edge threshold used in report: `WR >= 45%` and `PF >= 1.10` on `n >= 30`.

### Equity (Stocks)
- Evidence of edge at `last_200` (`WR 53%`, `PF 1.5652`), with very strong recent burst.
- Strong strategy slices:
  - `Breakout Momentum` (LONG): high recent WR/PF.
  - `Bollinger MR` (LONG): positive PF with adequate sample.
- Interpretation: **Yes, likely edge**, but recency spike probably overstates sustainable baseline.

### Forex
- Aggregate: `last_200` around `50%` WR with `PF 1.6838` (good PF despite middling WR).
- Strong filters (from report):
  - `forex_rsi2_mean_reversion` (especially SHORT sleeve)
  - Symbols `USDJPY=X`, `USDCHF=X`, `GBPJPY=X`
- Interpretation: **Conditional edge exists** under specific symbol/strategy filters, not universally.

### Commodities
- Aggregate: `last_200` near `49%` WR and `PF 1.5386`.
- Best filter cluster:
  - `futures_momentum` (LONG)
  - `PL=F` symbol slice
- Interpretation: **Edge exists but is thinner and decaying with window length**.

### ETFs
- `last_20` is excellent, but `last_100+` drops to low-50s WR and PF near threshold.
- Interpretation: **Potential edge but fragile**, likely regime-sensitive.

### Bonds
- n=17 total is too small for robust edge claims.
- Interpretation: **No statistical confidence yet**.

## Why Lower Buckets Can Look Bad
- Filter dilution: weak symbols and broad strategy mixing dilute genuinely strong sleeves.
- Confidence calibration drift: some buckets with higher confidence do not map to higher realized PnL consistently.
- Regime sensitivity: last-20 can be regime-lucky; 100/200 windows expose fragility.
- Label/metric mismatch risk: status semantics (`WON/LOST/CLOSED`) vs realized PnL sign can mislead dashboards if not unified.

## Suggested Fixes (Implementation + Process)

## 1) Make metric definitions non-ambiguous (implemented in this PR)
- `tools/edge_by_asset_class.py` now:
  - reads from dashboard closed-picks payload directly,
  - uses robust `pnl_pct <- pnl_pct | realized_pnl_pct | unrealized_pnl_pct`,
  - produces explicit claim-verification rows for 20/100/200 windows.

## 2) Trade only verified sleeves per asset class
- Promote only filters with `n>=30`, `PF>=1.10`, `WR>=45%`.
- De-prioritize broad unfiltered sleeves with decaying 100/200 performance.

## 3) Add CI guardrails on edge stability
- Block promotion when `last_20 >> last_200` divergence exceeds threshold (recency overfit).
- Require monotonic sanity checks on confidence buckets (higher confidence should not systematically underperform).

## 4) Integrate proven GitHub libraries for hedge-fund-grade validation
- [vectorbt](https://github.com/polakowo/vectorbt): fast parameter sweeps + walk-forward validation at scale.
- [empyrical](https://github.com/quantopian/empyrical): standardized risk/return metrics (Sharpe, Sortino, drawdown, alpha/beta).
- [PyPortfolioOpt](https://github.com/robertmartin8/PyPortfolioOpt): portfolio-level allocation/risk optimization across asset classes.
- [mlfinlab](https://github.com/hudson-and-thames/mlfinlab): robust financial ML tooling (purged CV, labeling, leakage-safe validation).

## 5) Filter policy recommendations by asset class
- **Forex:** favor `forex_rsi2_mean_reversion` with symbol whitelist (`USDJPY=X`, `USDCHF=X`, `GBPJPY=X`).
- **Commodities:** bias `futures_momentum` LONG sleeve; reduce weight on weaker commodity strategy buckets.
- **Equity/ETF:** keep current strong sleeves but cap by recency-vs-history divergence and regime tags.
- **Bonds:** keep in probationary low-size mode until sample size exceeds 50.

## Repro Steps
1. `python tools/edge_by_asset_class.py`
2. Inspect `reports/EDGE_BY_ASSET_CLASS_2026_04_22.md`
3. Validate claim table section (`Claim verification (status-based vs pnl-based WR)`).

## Bottom Line
- There is **real, filter-dependent edge** in equities, parts of forex, and parts of commodities.
- The original forex `5%` and commodities `15%` claims are not supported by current closed-picks data.
- The strongest recent numbers (stocks/ETFs at 85% in last 20) **do not fully persist** when extended to 100/200.
- Best next step is tightening to proven sleeves + hard CI guardrails + library-backed validation tooling.
