# FX Carry Trade (LRV 2011)

## Citation

Lustig, H., Roussanov, N., & Verdelhan, A. (2011).
**Common Risk Factors in Currency Markets**.
*Review of Financial Studies*, 24(11), 3731-3777.
DOI: 10.1093/rfs/hhr068

## Concrete Rules

| Item | Spec |
|---|---|
| Universe | G10 vs USD: AUD, CAD, CHF, EUR, GBP, JPY, NOK, NZD, SEK (9 crosses) |
| Signal | Short-rate differential vs USD: `carry_i = r_i - r_USD` (FRED 3M interbank) |
| Selection | Rank monthly; long top-3, short bottom-3, equal weight per side |
| Position size | Equal-weight within basket; net beta ~0 to broad USD |
| Leverage | 5x notional/equity default (capital-efficient FX baseline) |
| Rebalance | Monthly (1st calendar day or first business day after FRED publication lag) |
| Crisis filter | 3M realized vol of JPY/USD > 6% annualized -> halve leverage |
| Data | FRED API (St. Louis Fed); see `G10_RATE_SERIES` / `G10_SPOT_SERIES` |

## Statistical Gate (cursor framework)

- **n floor:** >=500 trade-months before any live promotion
- **Wilson 95% LB on WR > 0.50** required
- **Bonferroni alpha:** 0.05 / 7 = ~0.00714 (7-strategy build wave)
- **Bootstrap CI on PF & Sharpe** (1k resamples, BCa)
- **Walk-forward:** 5y train / 1y test rolling
- Paper-pilot ONLY until gate is cleared; never writes to `ejaguiar1_*`

## Expected Performance (academic)

| Metric | LRV 2011 in-sample | Live expectation |
|---|---|---|
| Sharpe | 0.7-0.9 | 0.4-0.6 (post-cost) |
| Skew | strongly negative | -0.8 to -1.5 |
| MDD | 25-35% (2008) | 15-25% with crisis filter |
| Hit-rate | 55-60% months | 50-55% post-cost |

## Crisis Handling (AI-refined)

Per Grok consult (`ai_consult_grok.txt`):
- JPY/USD vol is acceptable proxy but G10 FX-vol index is preferable upgrade
- 6% threshold too sensitive; **8-10% annualized recommended**
- Halving may be insufficient in tail events (Oct-08, Mar-20) — **force flat** on hard breach
- Add 25-delta JPY risk-reversal spike (<= -2%) as 2nd-axis skew filter
- Use 1M realized vol for responsiveness, 3M for confirmation

**Planned v2 upgrade:** dual-threshold filter — halve at 8% vol, flat at 12% vol OR RR<-2%.

## Files

- `strategy.py` - signal computation + pick generation
- `paper_pilot_harness.py` - persist picks to JSON sandbox
- `tests.py` - unit tests (10 tests, all pass)
- `ai_consult_grok.txt` - verbatim crisis-handling consult

## Promotion Gate Checklist

- [ ] n_closed >= 500 paper trade-months
- [ ] Wilson LB WR > 0.50
- [ ] PF > 1.15 with bootstrap LB > 1.0 at alpha=0.05/7
- [ ] Crisis-filter v2 (RR + vol composite) validated on 2008 + 2020 hold-outs
- [ ] MDD <= 20% on walk-forward
