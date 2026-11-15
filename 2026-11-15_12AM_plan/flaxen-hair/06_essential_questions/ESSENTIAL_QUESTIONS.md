# ESSENTIAL QUESTIONS FOR FINDING A PROFITABLE ALGORITHM

**Worktree:** flaxen-hair_2026-11-15T0020 | **Date:** 2026-11-15T00:27Z | **Repo:** findtorontoevents_antigravity.ca

---

## Data Integrity Questions (MUST ASK FIRST)

### Entry Price Integrity
1. **Is entry_price the actual fill price?** Or was it sampled from a different time?
2. **Was entry on the signal bar or the next bar?** Signal-bar entry is look-ahead biased.
3. **Was entry_price contaminated?** In this repo, entry_price is ~29% clean (37% >10% off bar, 7% >50%).
4. **Was entry_price systematically biased?** (~+1.3% bias inflates SHORT / deflates LONG)

### Exit Price Integrity
5. **Is exit_price the actual fill price?** Or an idealized price?
6. **Did price hit stop-loss before take-profit intraday?** Intrabar replay needed.
7. **Were stop-loss and take-profit levels realistic?** Or were they set after the fact?

### Data Quality Questions
8. **Were reverse-splits and price-feed bugs removed?** (e.g., CADJPY +428%, NZDUSD -100%)
9. **Were expired picks counted as non-wins?** Old methods dropped them, inflating WR from ~6% to 58.8%.
10. **Was data deduplicated?** Same symbol + strategy + timestamp appearing multiple times.
11. **Was data from banned sources excluded?** Some strategies produce garbage but still emit picks.
12. **Is the data stale?** Prices frozen at entry, no refresh for days/weeks.

### Sample Size Questions
13. **Is n ≥ 100 for a class verdict?** Below this, label INSUFFICIENT-N.
14. **Is n ≥ 30 per filter bucket?** Below this, results are noise.
15. **Are there ≥3 distinct months with n≥30/month?** Single-month results are selection bias.
16. **Is the time span ≥ 3 months?** Shorter periods cannot establish edge.

---

## Statistical Validity Questions

### Statistical Significance
17. **Does the strategy pass Bonferroni/FDR correction?** Multiple testing penalty.
18. **Is the Deflated Sharpe Ratio ≥ 0.95?** Multiple testing adjusted Sharpe.
19. **Is the Probabilistic Sharpe Ratio > 0.80?** Probability that true Sharpe > 0.
20. **Does the bootstrap 95% CI for PF exclude 1.0?** (PF_lower > 1.0)
21. **Does walk-forward show ≥60% profitable folds?** Stability across time.
22. **Is mean OOS PF > 1.2?** Out-of-sample performance.

### Robustness Questions
23. **Does performance hold across market regimes?** Bull, bear, sideways.
24. **Does performance hold across time periods?** First-half PF ≈ second-half PF.
25. **Is performance stable after removing the best day?** Single-day dependence kills edge.
26. **Is performance robust to 2-day execution lag?** Execution friction kills edge.
27. **Does performance survive transaction costs?** Commissions, slippage, spread.
28. **Does performance survive bid-ask spreads?** Especially important for illiquid assets.

### Cross-Validation Questions
29. **Does the strategy pass cross-source validation?** >60% from one source = concentration, not edge.
30. **Does the strategy pass outlier cap?** PF over ~10 usually means a few corrupt rows.
31. **Does the strategy pass anomaly exclusion?** Rows where resolved_at < submitted_at are impossible.
32. **Does the strategy pass intrabar replay?** TP may have hit SL first intraday.

---

## Implementation Questions

### Execution Feasibility
33. **Can the strategy be executed in real-time?** Or is it backtest-only?
35. **Can signals be executed at assumed prices?** Or do they require better fills?
36. **What is the capacity limit?** How much capital before edge decays?
37. **What is the correlation with existing positions?** Avoid concentration.
38. **What is the maximum drawdown scenario?** Can you survive it?

### Process Integrity Questions
39. **Was the hypothesis pre-registered?** Or is it data mining?
40. **Has it been walk-forward tested?** Not just one backtest.
41. **Has it been tested on truly out-of-sample data?** Not data used for development.
42. **Has it been tested across multiple market regimes?** Bull, bear, sideways.
43. **Is there a kill switch?** At what loss level do you stop?
44. **Is there a position sizing rule?** 1-2% risk per trade, quarter-Kelly max.

---

## Asset Class Specific Questions

### Crypto-Specific
45. **Is entry_price clean?** (~29% clean in this repo; systematic +1.3% bias)
46. **Do positions resolve?** (~90% never resolve in this repo)
47. **Is intrabar OHLC data available?** (≥180d 1h bars needed; only ~30d today)
48. **Are funding rates accounted for?** Funding rate arb is not directional alpha.
49. **Are exchange fees included?** Crypto fees can be significant.

### Equity-Specific
50. **Is the benchmark appropriate?** SPY total return, not zero.
51. **Are costs included?** Commissions, slippage, spread.
52. **Is the strategy regime-dependent?** Works in bull, fails in bear.

### ETF-Specific
53. **Is expense ratio ≤ 0.20%?** For mutual funds.
| 54. | Is AUM ≥ $1B? | For liquidity |
| 55. | Is turnover ≤ 20%? | Lower transaction costs |
| 56. | Is tracking error ≤ 0.25%? | For index funds |

### Forex-Specific
57. **Are all pairs spot FX?** 17.7% of rows in this repo were NOT spot FX.
58. **Is the allowlist enforced?** No forex strategies in PROVEN_STRATEGIES whitelist.

### Commodity/Bond/Futures-Specific
59. **Is n ≥ 60?** Below min_trades threshold.
| 60. | Is COT data fresh? | Weekly CFTC publication |
| 61. | Are Treasury yields current? | FRED data needed for bonds |

---

## Decision Gate Questions (Before Any Capital Allocation)

| Question | Pass/Fail | Required Answer |
|----------|-----------|-----------------|
| Is PnL calculated from real entry/exit prices? | | Yes |
| Are all required fields present (no blanks)? | | Yes |
| Is n ≥ 100 for class verdict? | | Yes |
| Is PF ≥ 1.5 after costs? | | Yes |
| Is WR > 50% (EXPIRED-inclusive)? | | Yes |
| Is Sharpe > 0.5 after costs? | | Yes |
| Is Max Drawdown < 15%? | | Yes |
| Is DSR ≥ 0.95? | | Yes |
| Is forward sample n ≥ 100? | | Yes |
| Has walk-forward been tested? | | Yes |
| Is regime robustness confirmed? | | Yes |
| Are costs (commission, slippage, spread) included? | | Yes |
| Is cross-source concentration < 60%? | | Yes |
| Has intrabar replay been performed? | | Yes |
| Is there a kill switch defined? | | Yes |
| Is position sizing ≤ 2% risk per trade? | | Yes |

**If ANY answer is "No", do NOT allocate capital.**

---
