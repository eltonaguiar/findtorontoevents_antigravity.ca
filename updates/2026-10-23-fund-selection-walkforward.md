# Fund Selection Walk-Forward Backtest — OPENCODE_BEAM (2026-10-23)

> **⚠️ NOT FINANCIAL ADVICE (NFA).** Research/education only. Not a recommendation to buy/sell any fund or account. Past performance ≠ future results. DYOR.

## Question (ELI5)

Grok said every asset class fails after ~150 strategies and a boring index fund wins. We tested whether *any* simple rule for picking mutual funds/ETFs — low fees, past returns, high Sharpe, small drops, sector rotation, "obscure winner" hunt — would have actually beaten "just buy the index" when you only used data available *at the time*, not the future.

## Methodology (quant-reviewer grade)

1. **Universe:** 118 tickers (US mutual funds, ETFs, Canadian ETFs, sector SPDRs, bond/commodity/REIT). ~9 failed download and were excluded. **Survivorship bias note:** only funds that still exist today are in the list — this BIASES *in favor* of fund-picking (dead losers are missing). If rules still cannot beat SPY here, the real-world result is worse.
2. **Walk-forward design:** For each year-end Y from 2005 through 2024 (n=19 rebalances after early-drop):
   - Using only prices up to 31-Dec Y, rank all funds with ≥2 years history.
   - Rules tested: 12-month momentum; 3-year CAGR; 3-year Sharpe; least-negative 3-year max drawdown; blend (z-score average of those three); top sector SPDR by 12m momentum; lowest published fee; free/0%-fee subset momentum; "obscure" subset momentum (Fidelity obscure + Avantis + factor ETFs); always-SPY / always-VTI / always-VOO / always-cheapest-index / always-cheapest-Canadian; equal-weight all funds.
   - Hold the pick for exactly 1 year. Measure forward 1y, 3y, 5y returns.
3. **Costs applied:** each fund's published annual fee (MER/ER, %) as annual drag + **0.20% one-time switch cost** for rules that rotate (always_* and equal_all have no switch cost).
4. **Benchmark:** always-SPY (same walk-forward, no switch cost).
5. **Significance:** 4,000-run block bootstrap of the *year-by-year difference* in chained CAGR vs SPY. Label "YES" only if the 95% CI of the difference chain is strictly > 0.
6. **Data source:** Yahoo Finance daily adjusted close, 1995-01-01 to 2026-10-22. Script: run inline (reproducible from tickers + fees dict below). Output JSON: `audit_dashboard/data/fund_wf_deep.json`.

## Results (net of fees + switch cost)

| Rule | n | Avg 1y | vs SPY avg | Beat SPY % | Chained CAGR | 95% CI vs SPY | Significant? |
|------|---|--------|------------|------------|--------------|---------------|--------------|
| mom12 | 19 | 2.4% | −9.8% | 32% | −2.1% | [−20.2,−2.9] | no |
| mom3y | 19 | 6.6% | −5.6% | 32% | 1.7% | [−20.6,+2.3] | no |
| sharpe3y | 19 | 4.0% | −8.1% | 37% | 3.8% | [−17.9,−1.0] | no |
| low_mdd | 19 | 1.5% | −10.6% | 21% | 1.5% | [−18.7,−4.4] | no |
| blend | 19 | 2.7% | −9.4% | 21% | −0.9% | [−17.2,−3.9] | no |
| sector_rot | 19 | 13.6% | +1.5% | 53% | 11.0% | [−5.4,+7.0] | **no** |
| lowest_fee | 19 | 9.1% | −3.0% | 53% | 7.8% | [−8.7,+1.0] | no |
| free_0pct | 19 | 10.5% | −1.6% | 53% | 9.0% | [−5.7,+0.3] | no |
| obscure_mom | 19 | 4.0% | −8.2% | 16% | 0.3% | [−16.2,−2.2] | no |
| equal_all | 19 | 9.1% | −3.1% | 31% | 8.2% | [−5.9,−0.5] | no |
| always_spy | 19 | 12.1% | 0 | — | 10.6% | — | baseline |
| always_vti | 19 | 12.2% | +0.0% | 32% | 10.6% | [−0.7,+0.7] | no |
| **always_voo** | 15 | 15.1% | **+0.1%** | **93%** | 14.1% | **[+0.02,+0.19]** | **YES** |
| **always_fx** | 19 | 12.6% | **+0.5%** | **84%** | 11.0% | **[+0.10,+0.83]** | **YES** |
| always_xeqt | 19 | 8.9% | −3.2% | 37% | 7.7% | [−7.6,+0.6] | no |

**always_fx** = each year buy the cheapest of FXAIX/FSKAX/VTSAX/VTI available (effectively "always hold the cheapest broad US index"). **always_voo** = "always hold VOO" (S&P 500 ETF with lower fee than SPY).

## Plain-English conclusion

1. **No fund-picking rule beat the index with statistical significance.** Every rule that *tries to pick* (momentum, Sharpe, low-drawdown, blend, obscure, free, sector rotation) failed the 95% CI test against SPY. Several were *significantly worse* (mom12, low_mdd, blend, obscure_mom).
2. **The only "significant" wins are not skill — they are just holding a cheap S&P 500 fund.** VOO and FXAIX beat SPY mainly because their fees are lower (0.03% / 0.015% vs 0.0945%). That is a fee arbitrage, not a selection edge. The correct lesson: **use the cheapest broad index you can buy.**
3. **Sector rotation does not clear the bar.** +1.5%/yr average looks nice but the 95% CI is [−5.4, +7.0] — it includes zero. Grok's "9.5% vs 8.3%" is directionally real in this universe but **not statistically proven** under fees + bootstrap.
4. **The "obscure secret winner" hunt failed.** High-fee obscure funds underperformed badly. Worst offender picked by momentum: **MIDSX (MFS Mid-Cap Value, 1.00% fee)** — full-history CAGR **0.05%**, max drawdown **−89.7%**. Not a secret winner; a secret disaster.
5. **Free 0% funds (FNILX, FZROX, FZILX) are fine but do not beat the index** — they *are* the index with zero fee. Using them vs SPY saves ~0.08%/yr; that is real but tiny.
6. **Canadian staples full-history (where available):** VFV.TO 17.2% CAGR / 14y, XUS.TO 16.5% / 14y, XEQT.TO 14.4% / 7y, VBAL.TO 7.7% / 9y. These are index products; the high CAGR is the US equity bull market, not manager skill.

## SPIVA context

S&P's SPIVA reports consistently show ~85–90% of active US large-cap managers underperform the S&P 500 over 15 years. Our walk-forward of *rules* (a proxy for active selection) matches: only the passive "hold the cheap index" arms showed any significant edge, and only vs a *higher-fee* index.

## What this means for the user (CA)

- **Starter (from $1):** XEQT (all-equity, 0.20% MER) on Wealthsimple TFSA if you accept ~30% drops; VBAL (60/40, 0.24% MER, −21% historical worst) if you would panic-sell.
- **Cheapest S&P 500 in CAD:** VFV.TO (0.09%) or XUS.TO (0.07%) — our data shows the "fee wins" lesson applies across the border.
- **US equivalent:** VOO or FXAIX/FSKAX/FNILX if your broker has them — lower fee than SPY is the only "edge" we can prove.
- **No mutual fund we tested is a shocking secret winner.** The boring low-fee index is the evidence-backed answer.

## Reproduce

Tickers + fee table are in the script output path `audit_dashboard/data/fund_wf_deep.json` (picks_by_year included). Random seed 42 for bootstrap. Data: Yahoo Finance.

