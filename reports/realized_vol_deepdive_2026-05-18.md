# realized_vol30 — cost-adjusted timing-signal deep-dive

Signal: hold the ETF next week when realized_vol30 is in the top 33% of its trailing 104-week distribution; else cash. Round-trip cost 5 bps. No look-ahead.

| ETF | strat Sharpe | B&H Sharpe | strat CAGR | B&H CAGR | strat MDD | B&H MDD | time in mkt |
|---|---|---|---|---|---|---|---|
| SPY | 0.49 | 0.66 | +5.8% | +10.5% | -48% | -55% | 43% |
| QQQ | 0.48 | 0.73 | +5.8% | +14.0% | -50% | -51% | 36% |
| IWM | 0.39 | 0.54 | +5.0% | +10.2% | -40% | -58% | 35% |
| GLD | 0.37 | 0.66 | +3.8% | +10.4% | -22% | -45% | 35% |
| SLV | 0.30 | 0.52 | +4.2% | +12.1% | -61% | -75% | 34% |
| XLK | 0.40 | 0.64 | +4.9% | +12.2% | -49% | -56% | 36% |
| XLE | 0.09 | 0.44 | -0.3% | +8.7% | -74% | -69% | 39% |
| EEM | 0.48* | 0.38 | +6.8% | +6.3% | -39% | -63% | 39% |
| TLT | 0.21 | 0.28 | +1.6% | +3.0% | -29% | -48% | 34% |
| HYG | 0.53 | 0.61 | +3.0% | +5.4% | -10% | -21% | 23% |

`*` = strategy Sharpe beats buy-and-hold. **1/10 ETFs**, cost-adjusted.

## Pooled by year — strategy vs buy-hold (summed weekly returns)

| year | strat | B&H | strat wins? |
|---|---|---|---|
| 1995 | +0.0% | +8.0% | no |
| 1996 | +19.8% | +24.0% | no |
| 1997 | +23.6% | +22.3% | yes |
| 1998 | +48.6% | +35.5% | yes |
| 1999 | +19.1% | +15.9% | yes |
| 2000 | +1.9% | -8.7% | yes |
| 2001 | +20.7% | -1.2% | yes |
| 2002 | -3.3% | -96.0% | yes |
| 2003 | -2.3% | +152.8% | no |
| 2004 | +4.2% | +45.6% | no |
| 2005 | +40.8% | +113.5% | no |
| 2006 | +70.9% | +66.1% | yes |
| 2007 | +15.0% | +121.5% | no |
| 2008 | -79.8% | -181.5% | yes |
| 2009 | +107.4% | +320.2% | no |
| 2010 | +0.0% | +189.5% | no |
| 2011 | +52.2% | +80.5% | no |
| 2012 | +68.6% | +124.0% | no |
| 2013 | -16.3% | +45.9% | no |
| 2014 | +8.0% | +54.3% | no |
| 2015 | -55.3% | -89.3% | yes |
| 2016 | +109.4% | +191.6% | no |
| 2017 | +4.8% | +164.3% | no |
| 2018 | -10.9% | -43.5% | yes |
| 2019 | +98.4% | +197.8% | no |
| 2020 | +323.3% | +231.4% | yes |
| 2021 | +6.6% | +100.9% | no |
| 2022 | +28.0% | -67.6% | yes |
| 2023 | +39.0% | +135.8% | no |
| 2024 | +2.3% | +167.9% | no |
| 2025 | +181.8% | +315.8% | no |
| 2026 | +19.6% | +89.5% | no |

**Verdict: NOT a tradeable edge — strategy beats buy-hold Sharpe on 1/10 ETFs and wins 12/32 pooled years (cost 5bps).**
realized_vol30 timing does not beat passive holding once costs are paid — it is the 7th candidate to fail. The in-house edge search is exhausted; next move is new signal sources.