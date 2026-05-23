# Top 10 strategies per asset class (pf_registry)

**Generated:** 2026-05-19T22:34Z  
**Registry snapshot:** `2026-05-19T20:58:20Z`  
**Canonical view:** `by_asset_class_policy_clean_net`  
**Ranking:** `by_asset_class_strategy` sorted by profit_factor (prefer n≥5).

## Codebase configuration spec (for meta-prompts / debate)

| Knob | Value / path |
|------|----------------|
| PF source | `audit_dashboard/data/pf_registry.json` |
| Dedup key | strategy(source_system\|strategy), symbol, direction, trade_date, entry~2p |
| Emitter gate | `alpha_engine/emitter_whitelist.py` — `EMITTER_REGISTRY_GATE=1`, enforce off by default |
| Hardcoded toxic pairs | quan_engine/CRYPTO; cta_replicator/COMMODITY; multi_asset_copytrader/FOREX,EQUITY |
| Harness | `tools/edge_stability_harness.py` — 11/11 daily-bar causal **KILLED** |
| Quarantine | `audit_dashboard/data/quarantine_manifest.json` size_caps + blocked pairs |
| Strategy families | `alpha_engine/config.py` → `STRATEGY_FAMILIES` |

### Class size caps (quarantine_manifest)

- **CRYPTO:** max_risk 10% — Per Grok 2026-05-12 rescue plan + ML inversion -16.67pp on CRYPTO holdout
- **EQUITY:** max_risk 25% — T2 candidate; PF 1.41 / WR 52.7% on n=421
- **COMMODITY:** max_risk 25% — CT=F factor-beta sleeve (not alpha); CTA-crowding cap per AQR R3 review
- **ETF:** max_risk 20% — Borderline T2; emission audit pending
- **FOREX:** max_risk 0% — Sub-floor PF 0.27 / WR 45.6% on n=1169; class-blocked per hedge_fund_sprint until SHORT-only rehab clears
- **BOND:** max_risk 20% — Quality-T2 (PF 1.72) but n=18 sub-floor; ramping post-FRED fix

## CRYPTO

**Class policy_clean_net:** n=1127 | PF=0.659 | WR=44.3656% | MDD=1.0

| Rank | Strategy | n | WR% | PF | Family | Flags |
|------|----------|---|-----|-----|--------|-------|
| 1 | `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` | 31 | 96.8 | 60.545 | — | — |
| 2 | `ml_enhanced_BNBUSDT_15m_B_lightgbm` | 19 | 89.5 | 58.819 | — | — |
| 3 | `ml_enhanced_INJUSDT_1d_B_lightgbm` | 28 | 96.4 | 41.520 | — | — |
| 4 | `ml_enhanced_FETUSDT_1d_B_lightgbm` | 44 | 56.8 | 9.427 | — | — |
| 5 | `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` | 47 | 61.7 | 3.943 | — | — |
| 6 | `ml_enhanced_STRKUSDT_15m_D_ensemble_stack` | 29 | 89.7 | 3.771 | — | — |
| 7 | `drawdown_recovery_rsi_eth` | 9 | 55.6 | 3.322 | — | — |
| 8 | `st_atr_vol_breakout` | 7 | 57.1 | 3.296 | — | — |
| 9 | `proven_vwap_mean_reversion` | 5 | 60.0 | 3.094 | — | — |
| 10 | `ml_enhanced_RENDERUSDT_4h_D_ensemble_stack` | 37 | 56.8 | 2.120 | — | — |

**Rescue candidates (CRYPTO):** `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack`, `ml_enhanced_INJUSDT_1d_B_lightgbm`, `ml_enhanced_FETUSDT_1d_B_lightgbm`

## EQUITY

**Class policy_clean_net:** n=5 | PF=0.253 | WR=20.0% | MDD=0.129189

| Rank | Strategy | n | WR% | PF | Family | Flags |
|------|----------|---|-----|-----|--------|-------|
| 1 | `multi_asset_copytrader` | 47 | 36.2 | 0.912 | — | — |
| 2 | `stocks_rsi2_pullback` | 2 | 50.0 | 0.750 | — | — |
| 3 | `auto_dna_mutation` | 1 | 0.0 | 0.000 | — | — |
| 4 | `regime_terminal` | 1 | 0.0 | 0.000 | — | — |
| 5 | `copy_trader_intel` | 1 | 100.0 | — | — | — |
| 6 | `futures_connors_rsi2` | 1 | 100.0 | — | — | — |

**Rescue candidates (EQUITY):** none pass PF≥1.2 n≥20 non-toxic in this slice — mutation or new hypothesis required.

## COMMODITY

**Class policy_clean_net:** n=55 | PF=1.424 | WR=54.5455% | MDD=0.52391

| Rank | Strategy | n | WR% | PF | Family | Flags |
|------|----------|---|-----|-----|--------|-------|
| 1 | `multi_asset_cot` | 58 | 58.6 | 1.598 | — | — |
| 2 | `multi_asset_copytrader` | 64 | 46.9 | 1.124 | — | — |
| 3 | `cta_replicator` | 68 | 14.7 | 0.283 | — | — |
| 4 | `combined_confidence_strategy` | 6 | 16.7 | 0.256 | — | — |
| 5 | `cot_positioning` | 1 | 0.0 | 0.000 | — | — |

**Rescue candidates (COMMODITY):** `multi_asset_cot`

## ETF

**Class policy_clean_net:** n=2 | PF=11.995 | WR=50.0% | MDD=0.0204

| Rank | Strategy | n | WR% | PF | Family | Flags |
|------|----------|---|-----|-----|--------|-------|
| 1 | `etf_all_strategies` | 1 | 0.0 | 0.000 | — | — |
| 2 | `etf_scanner` | 1 | 100.0 | — | — | — |

**Rescue candidates (ETF):** none pass PF≥1.2 n≥20 non-toxic in this slice — mutation or new hypothesis required.

## FOREX

**Class policy_clean_net:** n=148 | PF=1.491 | WR=56.0811% | MDD=0.043379

| Rank | Strategy | n | WR% | PF | Family | Flags |
|------|----------|---|-----|-----|--------|-------|
| 1 | `cta_replicator` | 109 | 64.2 | 2.514 | — | — |
| 2 | `combined_confidence_strategy` | 15 | 46.7 | 1.057 | — | — |
| 3 | `alpha_engine` | 43 | 27.9 | 0.594 | — | — |
| 4 | `multi_asset_scanner` | 15 | 26.7 | 0.306 | — | — |
| 5 | `multi_asset_copytrader` | 325 | 11.1 | 0.160 | — | — |
| 6 | `prediction_market_agents` | 1 | 0.0 | 0.000 | — | — |

**Rescue candidates (FOREX):** `cta_replicator`

## BOND

**Class policy_clean_net:** n=5 | PF=0.000 | WR=0.0% | MDD=0.479416

| Rank | Strategy | n | WR% | PF | Family | Flags |
|------|----------|---|-----|-----|--------|-------|
| 1 | `bond_scanner` | 4 | 0.0 | 0.000 | — | — |
| 2 | `cta_replicator` | 1 | 0.0 | 0.000 | — | — |

**Rescue candidates (BOND):** none pass PF≥1.2 n≥20 non-toxic in this slice — mutation or new hypothesis required.

## Meta-prompt usage

Feed this file to:
- `docs/swarm_prompts/META_DEBATE_PER_CLASS_v1.md` (cloud: argue rescue vs kill per rank)
- `docs/swarm_prompts/STRATEGY_HARVEST_EXECUTE_v1.md` (local: P0 wire plan)

Regenerate: `python tools/build_top10_strategies_per_class.py`
