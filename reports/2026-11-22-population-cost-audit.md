# Cost-adjusted FULL population — 10 registry cells

Source: `audit_dashboard/data/pf_registry.json` view `by_asset_class_policy_clean`. Expectancy is exact under a uniform per-trade cost; net PF is an approximation that holds while every winner exceeds the cost, so read it as slightly optimistic; net WR is an upper bound.

| class | n | cost bp | PF gross | PF net (approx) | WR | exp gross % | exp net % | breakeven cost bp |
|---|---|---|---|---|---|---|---|---|
| CRYPTO | 22,864 | 20 | 0.2656 | -0.3635 | 41.2% | -0.0464 | -0.2464 | -4.6 |
| FOREX | 468 | 8 | 0.1778 | -0.2361 | 33.1% | -0.0275 | -0.1075 | -2.8 |
| EQUITY | 217 | 10 | 0.6206 | -0.1222 | 38.7% | -0.0159 | -0.1159 | -1.6 |
| COMMODITY | 35 | 12 | 0.3528 | -0.2749 | 31.4% | -0.0156 | -0.1356 | -1.6 |
| ETF | 32 | 10 | 1.8846 | 0.4662 | 62.5% | +0.0499 | -0.0501 | +5.0 |
| FUTURES | 17 | 12 | 1.3519 | -0.2995 | 35.3% | +0.0041 | -0.1159 | +0.4 |
| MEME | 10 | 15 | 0.0264 | -0.0665 | 10.0% | -0.0632 | -0.2132 | -6.3 |
| PENNY_STOCK | 4 | 15 | 0.1922 | -0.4417 | 50.0% | -0.0534 | -0.2034 | -5.3 |
| BOND | 2 | 10 | None | None | 100.0% | +0.0200 | -0.0800 | +2.0 |
| CHEAP_STOCKS | 2 | 15 | 0.3972 | -0.0664 | 50.0% | -0.0910 | -0.2410 | -9.1 |
