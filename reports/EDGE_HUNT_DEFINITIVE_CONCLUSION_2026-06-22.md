# Edge-hunt — DEFINITIVE CONCLUSION (2026-06-22)
**Author:** claude-opus · capstone of the multi-day autonomous money-ready + alt-data effort

## The finding, established beyond doubt
**Every signal tested dissolves under proper power or correct clustering. There is no extractable edge in any data-feasible source available to this program.** This is not an assumption or a "needs more data" excuse — every promising lead was explicitly powered up / adversarially verified, and every one dissolved:

| Candidate | apparent | under proper power / scrutiny |
|---|---|---|
| crypto strategy book | various | dead at 11x scale (PF 0.07-0.94) |
| cg_whale_divergence | CI-LB 2.05 | 4-day concentration artifact |
| equity 5-day reversal (H-126) | CI-LB 1.24 | clustering artifact -> 0.99 |
| equity momentum (H-133) | PF 1.86 | n_eff=16 (n-starved) |
| crypto funding MR/carry (H-130/131) | — | refuted (PF 0.64/0.84) |
| crypto cointegration (H-132) | — | IS broke OOS (PF 0.32) |
| COT commercial-hedger (H-134/135) | PF 1.07-1.25 | sub-bar at n_eff=207 (real but weak) |
| commodity TSMOM (H-136) | PF 1.09 | regime-unstable (IS/OOS 0.76/1.59) |
| commodity X-sectional (H-137) | — | LOSING at n_eff=239 (PF 0.86) |
| **insider-buy drift (H-138)** | **PF 1.66** | **dissolved on repower: n 46->87 -> PF 1.055, IS/OOS 0.50/1.86** |

The recurring mechanism of every false positive: small-sample optimism, single-name/few-day concentration, clustering that inflates significance, or a recent-regime artifact. Properly powered + correctly clustered, none survive.

## Lasting value delivered (autonomous)
- **Honest, rigorous verdicts** (H-126..H-138, 13 hypotheses) — the program now KNOWS what doesn't work, at proper power, instead of chasing it. ~25 commits.
- **2 alt-data feeds revived + maintained** (insider, COT) with weekly workflows.
- **2 new price feeds built**: `futures_daily_ohlcv` (5yr, 11 commodities), `equity_daily_ohlcv` (5yr, 38 tickers) — reusable for any future test.
- **Root constraints documented**: price-path coverage (crypto 181d, daily_prices frozen), resolver-keyspace gap, dead alt-data feeds.

## The honest bottom line
The money-ready program is **not edge-constrained by lack of analysis or rigor** (both are now exhaustive) **— it has no edge to extract from its current data.** The only genuine paths forward are operator/infra + calendar-time:
1. Restore `daily_prices` + broaden the equity universe (the price-side gap that n-starved equity).
2. Fix the resolver-keyspace gap (honest measurement at scale).
3. Let the maintained feeds accrue forward (months) — though note even the insider lead dissolved under power, so forward accrual is not guaranteed to surface edge.
4. Accept the money-protecting verdict: 0/10, no sizeable trustworthy edge — and do not size on any of the dissolved leads.

Autonomous edge-hunting is definitively complete. Remaining work is operator action or a new domain (e.g., Goal #2 sports).
