# Asset Class Deep Dive: CRYPTO

**Source:** scratch-hippodraco research session  
**Date:** 2026-11-15T07:00Z  
**Status:** HIGH VOLUME, LOW PROFITABILITY — Needs infrastructure fixes

## Current State

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| n (resolved) | 3,705 | ≥100 | PASS |
| WR | 35.87% | ≥50% | FAIL |
| PF | 0.9196 | ≥1.5 | FAIL |
| Expectancy | -0.058445 | >0 | FAIL |
| MDD | 100.09% | ≤20% | FAIL |
| Intrabar truth | WR drops 52.3%→42.9% | N/A | FAIL |
| OHLCV depth | ~30 days 1h | ≥180 days | FAIL |

## Strategies Identified in Repo

| Strategy | File | WR | PF | n | Status |
|----------|------|-----|-----|-----|--------|
| ml_enhanced_INJUSDT_1d_B_lightgbm | `ml_crypto_predictor/**` | 100% | unknown | 27 | n too small |
| ml_enhanced_FETUSDT_1d_B_lightgbm | `ml_crypto_predictor/**` | 100% | unknown | 25 | n too small |
| ml_enhanced_DYDXUSDT_15m_D_ensemble_stack | `ml_crypto_predictor/**` | 96.8% | unknown | 31 | n too small |
| ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | `ml_crypto_predictor/**` | 85.3% | unknown | 34 | n too small |
| st_fear_greed_contrarian | `alpha_engine/crypto_strategies.py` | 94% | unknown | unknown | unvalidated |
| funding_rate_arb | `alpha_engine/funding_rate_arb.py` | unknown | unknown | unknown | unvalidated |
| btc_breakout_strategy | `alpha_engine/btc_breakout_strategy.py` | unknown | unknown | unknown | unvalidated |
| ml_enhanced_APEUSDT_1d_D_ensemble_stack | blocked | unknown | unknown | unknown | quarantined |
| crypto_soc_proxy_decoupling | blocked | unknown | unknown | unknown | quarantined |
| crypto_soc_delta_divergence | blocked | unknown | unknown | unknown | quarantined |
| crypto_soc_orderflow_absorption | blocked | unknown | unknown | unknown | quarantined |

## Key Issues

1. **Intrabar truth gap**: 26.4% of TP_HITs hit SL first — resolver uses end-of-bar not intrabar
2. **No OHLCV depth**: Only ~30 days of 1h bars, need ≥180 days
3. **Toxic sources**: CRYPTO appears once in entire forward set (profitable-approach gate)
4. **Multiple variants**: 68+ strategies tested, ~34 expected false positives at p=5%
5. **No walk-forward**: All backtests in-sample
7. **Cost model**: 30bps round-trip (high for crypto)

## Recommended Next Steps

1. Backfill OHLCV to ≥180 days 1h bars
2. Run intrabar replay (reresolve_intrabar.py) on all crypto picks
3. Test funding-rate mean reversion strategy
4. Test BTC/ETH pairs trading (market-neutral)
5. Apply multiple testing correction (68+ variants tested)
