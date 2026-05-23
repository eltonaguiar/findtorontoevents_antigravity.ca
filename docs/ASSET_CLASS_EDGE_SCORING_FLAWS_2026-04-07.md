# Asset class edge & scoring flaws — deep dive

**Generated:** see `tools/analyze_asset_class_edge_flaws.py`
**Data:** `e:/findtorontoevents_antigravity.ca/tools/data/snapshots/dashboard_data_2026-04-06T225846Z.json`
**Closed picks analyzed:** 3500

Machine-readable: `tools/data/asset_class_edge_flaws_analysis.json`

---

## Executive summary

- **CRYPTO** (~85% of closes) is **slightly profitable on average** with **strong smart_score tail** (top vs bottom smart quintile ~39pp win-rate spread) and Spearman(smart, PnL) ≈ **0.26**, while **elite_score is almost flat** vs PnL (~0.07) — elite mix is mis-specified or redundant for crypto.
- **EQUITY** is **deeply negative on average** (~−0.78% mean) with **low win rate** (~35%) even though **elite_score ranks outcomes** (ρ ≈ **0.35**) better than smart_score — scoring can sort names, but **what gets traded** (strategies like dividend/value/earnings scouts) is **toxic**; need **allowlist / gates**, not only reweighting.
- **FOREX** is **negative mean**, **weak headline score** vs PnL (ρ ≈ **0.02**), and **confidence is noise or inverse** — **recalibrate or drop confidence** for FX; treat as **experimental** until discrimination improves.
- **Strategy tails:** crypto **`st_rsi_momentum_confluence`** shows large negative mean with high n; equity **dividend/value/earnings** clusters dominate the losers table — align with rolling **strategy expectancy** penalties in `quality_gates` / registry.
- **Deeper cuts (this run):** §2.1 **LONG vs SHORT** by asset; §2.2 top **`source_system`** buckets with **ρ(smart)** vs **ρ(ml)** vs **ρ(score)** (detect feeds where ML composite adds no rank info); §2.3 **exit_reason** mix (TP/SL/expiry concentration).

---

## 1. Summary

| Type | Count |
|------|------:|
| Structured **edges** | 6 |
| Structured **flaws** | 5 |

### Edges (actionable signals)
- **cross_asset_score_ic_rank** — `{"type": "cross_asset_score_ic_rank", "strongest_smart_spearman": {"asset": "CRYPTO", "rho": 0.25901, "n": 2855}, "strongest_elite_spearman": {"asset": "EQUITY", "rho": 0.34604, "n": 471}, "note": "Use asset-conditioned composite weights (elite vs smart) — see per-class table."}`
- **smart_outranks_elite_crypto** — `{"type": "smart_outranks_elite_crypto", "asset_class": "CRYPTO", "spearman_smart": 0.25901, "spearman_elite": 0.07151, "n": 2855}`
- **smart_quintile_strong_tail** — `{"type": "smart_quintile_strong_tail", "asset_class": "CRYPTO", "q5_minus_q1_wr_pp": 38.71, "q5_minus_q1_mean_pnl_pp": 1.5073, "n": 2855}`
- **elite_outranks_smart_non_crypto** — `{"type": "elite_outranks_smart_non_crypto", "asset_class": "EQUITY", "spearman_elite": 0.34604, "spearman_smart": 0.21693, "n": 471}`
- **smart_quintile_strong_tail** — `{"type": "smart_quintile_strong_tail", "asset_class": "EQUITY", "q5_minus_q1_wr_pp": 27.07, "q5_minus_q1_mean_pnl_pp": 2.3242, "n": 471}`
- **smart_quintile_strong_tail** — `{"type": "smart_quintile_strong_tail", "asset_class": "FOREX", "q5_minus_q1_wr_pp": 22.19, "q5_minus_q1_mean_pnl_pp": 0.6848, "n": 147}`

### Flaws (scoring / product gaps)
- **elite_effectively_uninformative_crypto** — `{"type": "elite_effectively_uninformative_crypto", "asset_class": "CRYPTO", "spearman_elite": 0.07151, "spearman_smart": 0.25901, "n": 2855, "detail": "Elite score barely covaries with PnL on crypto; do not weight elite heavily in crypto composite."}`
- **confidence_weak_vs_pnl** — `{"type": "confidence_weak_vs_pnl", "asset_class": "EQUITY", "spearman_pnl": 0.01794, "n": 471, "detail": "Raw confidence barely ranks realized PnL in this window."}`
- **equity_negative_mean_structural_universe** — `{"type": "equity_negative_mean_structural_universe", "asset_class": "EQUITY", "mean_pnl_pct": -0.7788, "n": 471, "spearman_elite": 0.34604, "detail": "Elite ranks outcomes but the traded equity subset still bleeds — tighten universe / strategy allowlist, not only composite weights."}`
- **confidence_weak_vs_pnl** — `{"type": "confidence_weak_vs_pnl", "asset_class": "FOREX", "spearman_pnl": -0.08763, "n": 147, "detail": "Raw confidence barely ranks realized PnL in this window."}`
- **bleeding_asset_class_weak_score_discrimination** — `{"type": "bleeding_asset_class_weak_score_discrimination", "asset_class": "FOREX", "mean_pnl_pct": -0.2787, "score_spearman": 0.01687, "n": 147, "detail": "Pool loses on average but headline score does not separate winners well."}`

---

## 2. Per–asset-class outcomes & score correlation

| Asset | n | WR % | Mean PnL % | ρ(smart) | ρ(ml) | ρ(elite) | ρ(conf) |
|-------|--:|-----:|-----------:|---------:|------:|---------:|--------:|
| CRYPTO | 2855 | 48.51 | 0.2208 | 0.259 | 0.190 | 0.072 | 0.152 |
| EQUITY | 471 | 35.46 | -0.7788 | 0.217 | 0.333 | 0.346 | 0.018 |
| FOREX | 147 | 31.29 | -0.2787 | 0.127 | 0.017 | 0.097 | -0.088 |
| COMMODITY | 12 | 8.33 | -0.6966 | — | — | — | — |
| ETF | 12 | 41.67 | -0.9511 | — | — | — | — |
| FUTURES | 3 | 0.0 | -0.4489 | — | — | — | — |

### 2.1 Direction split (LONG vs SHORT)

**CRYPTO**

| Direction | n | WR % | Mean PnL % |
|-----------|--:|-----:|------------:|
| LONG | 2572 | 50.19 | 0.279 |
| SHORT | 283 | 33.22 | -0.3084 |

**EQUITY**

| Direction | n | WR % | Mean PnL % |
|-----------|--:|-----:|------------:|
| LONG | 467 | 35.76 | -0.7719 |
| SHORT | 4 | 0.0 | -1.5864 |

**FOREX**

| Direction | n | WR % | Mean PnL % |
|-----------|--:|-----:|------------:|
| LONG | 131 | 32.82 | -0.277 |
| SHORT | 16 | 18.75 | -0.2932 |

**COMMODITY**

| Direction | n | WR % | Mean PnL % |
|-----------|--:|-----:|------------:|
| LONG | 6 | 16.67 | -0.6437 |
| SHORT | 6 | 0.0 | -0.7495 |

**ETF**

| Direction | n | WR % | Mean PnL % |
|-----------|--:|-----:|------------:|
| LONG | 12 | 41.67 | -0.9511 |

**FUTURES**

| Direction | n | WR % | Mean PnL % |
|-----------|--:|-----:|------------:|
| LONG | 3 | 0.0 | -0.4489 |

### 2.2 Top `source_system` feeds (by volume) + score–PnL ρ

Min **n = 25** per row. Shows whether **ML composite** tracks PnL inside each feed.

**CRYPTO**

| source_system | n | WR % | Mean PnL % | ρ(smart) | ρ(ml) | ρ(score) |
|---------------|--:|-----:|-----------:|---------:|------:|---------:|
| alpha_engine | 1120 | 40.89 | 0.0276 | 0.015 | 0.049 | 0.049 |
| claude_gainer_st | 809 | 63.16 | 0.5166 | 0.476 | 0.266 | 0.266 |
| rapid_fire | 207 | 50.24 | 0.478 | 0.232 | 0.128 | 0.120 |
| baby_strats_forward | 173 | 45.09 | -0.034 | 0.358 | -0.044 | -0.044 |
| luxalgo_filters | 154 | 40.91 | -0.046 | 0.108 | -0.044 | -0.044 |
| ml_crypto_pred | 124 | 29.84 | -0.504 | -0.167 | -0.324 | -0.324 |
| dna_winner_picks | 62 | 54.84 | 0.7032 | 0.267 | -0.052 | -0.052 |
| mercury2 | 52 | 51.92 | 0.8108 | -0.014 | -0.014 | -0.014 |
| battleground | 36 | 30.56 | -0.2008 | 0.165 | 0.479 | 0.479 |

**EQUITY**

| source_system | n | WR % | Mean PnL % | ρ(smart) | ρ(ml) | ρ(score) |
|---------------|--:|-----:|-----------:|---------:|------:|---------:|
| stocks_competition | 236 | 33.9 | -0.937 | 0.153 | 0.438 | 0.438 |
| kimi_riseoftheclaw | 179 | 38.55 | -0.3837 | 0.237 | 0.226 | 0.226 |

**FOREX**

| source_system | n | WR % | Mean PnL % | ρ(smart) | ρ(ml) | ρ(score) |
|---------------|--:|-----:|-----------:|---------:|------:|---------:|
| stocks_competition | 50 | 40.0 | -0.5354 | 0.314 | -0.183 | -0.183 |
| kimi_riseoftheclaw | 49 | 24.49 | -0.1363 | 0.081 | -0.029 | -0.029 |

### 2.3 Exit reason mix (top drivers)

**CRYPTO**
- `SL` — **22.8%** of closes (n=651)
- `EXPIRED` — **17.55%** of closes (n=501)
- `SL_HIT` — **16.04%** of closes (n=458)
- `TP` — **13.38%** of closes (n=382)
- `TP_HIT` — **11.14%** of closes (n=318)
- `TIME_EXIT` — **6.41%** of closes (n=183)

**EQUITY**
- `SL_HIT` — **26.33%** of closes (n=124)
- `EXPIRED` — **16.99%** of closes (n=80)
- `TIME_EXIT (7d)` — **8.92%** of closes (n=42)
- `TP_HIT` — **8.49%** of closes (n=40)
- `LOST` — **3.82%** of closes (n=18)
- `GRADE_GATE` — **1.27%** of closes (n=6)

**FOREX**
- `EXPIRED` — **34.01%** of closes (n=50)
- `SL_HIT` — **10.2%** of closes (n=15)
- `PURGE_FOREX_PENNY` — **8.84%** of closes (n=13)
- `GRADE_GATE` — **5.44%** of closes (n=8)
- `Max hold exceeded (22d > 14d)` — **3.4%** of closes (n=5)
- `TIME_EXIT` — **2.72%** of closes (n=4)

**COMMODITY**
- `PRICE_RESOLVED` — **33.33%** of closes (n=4)
- `STOP_LOSS` — **25.0%** of closes (n=3)
- `GRADE_GATE` — **8.33%** of closes (n=1)
- `SL_HIT` — **8.33%** of closes (n=1)
- `CIRCUIT_BREAKER` — **8.33%** of closes (n=1)
- `TAKE_PROFIT` — **8.33%** of closes (n=1)

**ETF**
- `Max hold exceeded (22d > 15d)` — **50.0%** of closes (n=6)
- `GRADE_GATE` — **16.67%** of closes (n=2)
- `Strategy underperforming - removed from portf...` — **16.67%** of closes (n=2)
- `STOP_LOSS` — **8.33%** of closes (n=1)
- `Strategy disabled - no hyperopt backing` — **8.33%** of closes (n=1)

**FUTURES**
- `STOP_LOSS` — **33.33%** of closes (n=1)
- `Max hold exceeded (22d > 10d)` — **33.33%** of closes (n=1)
- `Strategy underperforming - removed from portf...` — **33.33%** of closes (n=1)

---

## 3. Strategy tails (worst mean PnL, min n)

### CRYPTO — worst

| Strategy | n | WR % | Mean PnL % |
|----------|--:|-----:|------------:|
| st_rsi_momentum_confluence | 108 | 12.04 | -2.6301 |
| ml_enhanced_FETUSDT_15m_B_lightgbm | 6 | 50.0 | -2.1456 |
| ml_enhanced_AVAXUSDT_15m_D_ensemble_stack | 6 | 33.33 | -1.2548 |
| ml_enhanced_ADAUSDT_15m_B_lightgbm | 5 | 40.0 | -1.2089 |
| macd_crossover | 30 | 33.33 | -0.6441 |
| crypto_keltner_compression_expansion_v1 | 5 | 0.0 | -0.6432 |
| vwap_deviation_reversion_eth_v1 | 8 | 25.0 | -0.628 |
| keltner_compression_expansion_sol_v1 | 8 | 12.5 | -0.6152 |

### EQUITY — worst

| Strategy | n | WR % | Mean PnL % |
|----------|--:|-----:|------------:|
| Dividend Aristocrats | 7 | 0.0 | -6.1971 |
| Value + Quality | 31 | 9.68 | -4.199 |
| Earnings Drift | 17 | 11.76 | -3.4559 |
| Consecutive Beats | 29 | 13.79 | -3.4166 |
| hh-hl-scout | 10 | 20.0 | -3.1759 |
| intermarket-flow-scout | 8 | 12.5 | -2.1228 |
| call-surge-scout | 12 | 16.67 | -2.0863 |
| ema-ribbon | 5 | 20.0 | -1.9471 |

### ETF — worst

| Strategy | n | WR % | Mean PnL % |
|----------|--:|-----:|------------:|
| extreme_oversold_bounce | 5 | 0.0 | -3.0969 |

### FOREX — worst

| Strategy | n | WR % | Mean PnL % |
|----------|--:|-----:|------------:|
| community_london_breakout_v2_forex | 8 | 0.0 | -0.982 |
| Breakout Momentum | 23 | 26.09 | -0.867 |
| ML Ranker | 14 | 35.71 | -0.4921 |
| dxy-reversal-scout | 10 | 20.0 | -0.1911 |
| carry-trade-momentum | 15 | 26.67 | -0.1442 |
| MomentumEMA | 6 | 33.33 | -0.1417 |
| forex-rsi-ema-scout | 8 | 25.0 | -0.1329 |
| unknown | 13 | 30.77 | -0.0178 |

---

## 4. Recommendations (from this run)

1. **Weight elite more on non-crypto** where Spearman(elite) > Spearman(smart); keep **smart_score–first** for crypto.
2. **Down-weight or recalibrate confidence** where |ρ| < 0.1 with large n.
3. **Tighten gates** on asset classes with negative mean PnL and weak score discrimination (see `bleeding_asset_class_weak_score_discrimination`).
4. **Strategy rehab / bans** for recurring names in §3 worst tables.
5. Re-run this script whenever `dashboard_data.json` is regenerated.

---

## 5. Redis bus

Topic **`ASSET_CLASS_EDGE_SCORING_FLAWS`** — publish via `python tools/bus_post_asset_class_edge_study.py`.
