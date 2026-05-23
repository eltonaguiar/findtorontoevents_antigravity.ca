# Strict Weekly Real-Money Filter - 2026-05-16

**Generated:** 2026-05-16T05:10:32+00:00
**Dashboard source:** `audit_dashboard/data/dashboard_data.json` generated `2026-05-16T04:04:25.838063+00:00` (age 1.10h, FRESH)
**Rule:** no class is marked tradeable unless it clears n>=100, WR>=50%, PF>=1.5, positive expectancy, no concentration block/warn, no readiness sizing block, and no bad worst walk-forward fold.
**Sizing rule:** Kelly is computed with `alpha_engine.kelly_position_sizer.compute_position_size()` at $10,000 / quarter-Kelly, then capped by `docs/PERFORMANCE_CHARTER.md` swing max position size of 1% per trade.

## Verdict Table

| Class | Verdict | n | WR | PF | Exp | OOS WR | Concentration | Readiness | Kelly $ / % | Operational $ | Fails |
|---|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---|
| EQUITY | FILTER_READY_SMALL_SIZE | 425 | 51.5% | 1.56 | 0.90 | 62.2% | OK Classic Momentum / AMD (11.62%) | T2_CHARTER_MET | $462.50 / 4.62% | $100.00 | none |
| COMMODITY | RESEARCH_ONLY | 337 | 62.6% | 2.57 | 1.89 | -- | WARN cot_positioning / CT=F (75.24%) | RENAISSANCE_TIER | $954.23 / 9.54% | $0.00 | concentration_WARN, readiness_sizing_blocked |
| ETF | RESEARCH_ONLY | 107 | 57.0% | 1.32 | 0.35 | 75.0% | OK intermarket-flow-scout / XLE (19.74%) | T3_ELIGIBLE | $345.77 / 3.46% | $0.00 | PF<1.5, readiness_sizing_blocked |
| CRYPTO | RESEARCH_ONLY | 7885 | 46.5% | 1.31 | 0.35 | 45.7% | OK luxalgo_confluence / BTCUSDT (9.42%) | T3_ELIGIBLE | $275.08 / 2.75% | $0.00 | PF<1.5, WR<50, readiness_sizing_blocked, bad_worst_fold |
| FOREX | RESEARCH_ONLY | 311 | 54.7% | 0.86 | -0.05 | -- | OK cta_fx_multifactor / USDJPY=X (39.75%) | SUB_T2 | $0.00 / 0.00% | $0.00 | PF<1.5, expectancy<=0, readiness_sizing_blocked |
| BOND | RESEARCH_ONLY | 11 | 54.5% | 0.66 | -0.14 | 56.2% | WARN betting-against-beta / TLT (78.92%) | INSUFFICIENT_SAMPLE | $0.00 / 0.00% | $0.00 | n<100, PF<1.5, expectancy<=0, concentration_WARN, readiness_sizing_blocked, bad_worst_fold |
| FUTURES | RESEARCH_ONLY | 2 | 100.0% | -- | 8.45 | -- | BLOCK futures_bb_mean_reversion / CT=F (100.0%) | INSUFFICIENT_SAMPLE | $0.00 / 0.00% | $0.00 | n<100, PF<1.5, concentration_BLOCK, readiness_sizing_blocked |

## Filters To Use This Week

### EQUITY: only class cleared for small live sizing

- Evidence: n=425, WR=51.5%, PF=1.56, expectancy=0.90, OOS WR=62.2%, worst fold WR=42.5%.
- Filter: `asset_class=EQUITY`, `status=OPEN`, prefer `top_strategy=Classic Momentum` and do not exceed 1% of account per swing trade.
- Kelly says $462.50 (4.62%) on class stats; operational cap is $100.00 per $10k account by charter.
- Current dashboard payload has `picks.active` count = 0; if the UI shows no matching open EQUITY picks, take no trade rather than broadening the filter.

### Research-only classes

- `COMMODITY`: concentration_WARN, readiness_sizing_blocked. Headline stats: n=337, WR=62.6%, PF=2.57. Do not size until blockers clear.
- `ETF`: PF<1.5, readiness_sizing_blocked. Headline stats: n=107, WR=57.0%, PF=1.32. Do not size until blockers clear.
- `CRYPTO`: PF<1.5, WR<50, readiness_sizing_blocked, bad_worst_fold. Headline stats: n=7885, WR=46.5%, PF=1.31. Do not size until blockers clear.
- `FOREX`: PF<1.5, expectancy<=0, readiness_sizing_blocked. Headline stats: n=311, WR=54.7%, PF=0.86. Do not size until blockers clear.
- `BOND`: n<100, PF<1.5, expectancy<=0, concentration_WARN, readiness_sizing_blocked, bad_worst_fold. Headline stats: n=11, WR=54.5%, PF=0.66. Do not size until blockers clear.
- `FUTURES`: n<100, PF<1.5, concentration_BLOCK, readiness_sizing_blocked. Headline stats: n=2, WR=100.0%, PF=--. Do not size until blockers clear.

## Top Candidate Systems To Keep Watching

### EQUITY
- No single-class dashboard system with n>=20 and complete PF/WR/expectancy metrics found in this payload.

### COMMODITY
- `multi_asset_cot`: n=131, WR=79.4%, PF=4.72, expectancy=3.11, MDD=79.97, active=0, status=monitoring, stale_days=0.2.

### ETF
- No single-class dashboard system with n>=20 and complete PF/WR/expectancy metrics found in this payload.

### CRYPTO
- `mega_mutation`: n=165, WR=58.8%, PF=2.43, expectancy=1.61, MDD=44.59, active=0, status=monitoring, stale_days=0.2.
- `claude_gainer`: n=32, WR=56.2%, PF=2.23, expectancy=2.51, MDD=33.48, active=0, status=monitoring, stale_days=2.2.
- `ml_crypto_pred`: n=40, WR=22.5%, PF=1.86, expectancy=0.81, MDD=19.52, active=18, status=active, stale_days=0.0.
- `baby_strats_forward`: n=1896, WR=46.7%, PF=1.45, expectancy=0.18, MDD=29.99, active=0, status=monitoring, stale_days=0.1.
- `mercury2`: n=363, WR=39.7%, PF=1.43, expectancy=0.43, MDD=46.61, active=0, status=monitoring, stale_days=0.8.

### FOREX
- No single-class dashboard system with n>=20 and complete PF/WR/expectancy metrics found in this payload.

### BOND
- No single-class dashboard system with n>=20 and complete PF/WR/expectancy metrics found in this payload.

## Current Pick Availability

- `picks.active` in `dashboard_data.json`: 0.
- `smart_picks_feed.generated_at`: `2026-04-30T02:56:20.805030+00:00`. This is stale relative to the dashboard and was not used for live trade recommendations.
- If there are no open picks matching the strict filter, the correct action is cash.

## Next Work

- Build `tools/filter_generator.py` to emit this same strict gate as machine-readable JSON for dashboard/API consumption.
- For COMMODITY, recompute post-COT-dedup results excluding CT=F before any sizing change.
- For ETF, continue accumulating until PF>=1.5 or derive a stronger sub-filter with n>=100.
- For CRYPTO, derive system-level filters only; class-wide CRYPTO fails WR/PF and has bad worst-fold behavior.
