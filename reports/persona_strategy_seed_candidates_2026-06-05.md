# Persona / Model Strategy Seed Candidates — 2026-06-05

DB: `ejaguiar1_stocks` (live). Credentials via `tools.db_env.get_stocks_creds()`.
Window: all-time inclusive of all currently-resolved rows. Date span on tournament side is **2026-05-21 → 2026-06-05** (~15 days only).

## Headline reality check

- **No `model_id × persona_id × asset_class` cell reaches n≥30** in `tournament_picks`. Max cell n = 18 (`grok3 × breakout_scanner × CRYPTO`).
- Lowering to **n≥10 AND WR≥55% AND PF≥1.2** yields exactly **1** cell: `grok3 × reflexivity_trader × CRYPTO` (n=11, WR 72.7%, PF 5.27, mean +6.48%, 2026-05-23 → 2026-06-04, only 7 distinct days). **Single-window artifact risk is HIGH** — entire universe spans 15 days, no out-of-sample.
- Tournament closed-n = 1,748 total; **4,154 rows in `MISPRICED_ENTRY` are excluded** (untradeable backfill noise). Watch for this when re-running queries.
- Real seed surface is in `trading_picks` (strategy-level) and `at_pick_outcomes` (resolved/version-tagged), not in model×persona cells.

## Top 25 models (n≥20, closed only, FOREX |pnl|≤0.30 filter)

| model_id | n | WR% | PF | mean_pnl | dates |
|---|---:|---:|---:|---:|---|
| grok3 | 52 | 67.3 | 2.91 | +3.85 | 05-21..06-04 |
| kimi_direct | 50 | 66.0 | 2.80 | +1.69 | 05-22..06-04 |
| command_a | 46 | 56.5 | 0.86 | -0.27 | 05-22..06-04 |
| gemini_2_5_flash | 51 | 54.9 | 1.15 | +0.32 | 05-22..06-04 |
| minimax_m2_5 | 46 | 54.3 | 0.92 | -0.14 | 05-22..06-05 |
| gpt5_chat | 42 | 52.4 | 0.69 | -1.08 | 05-22..06-05 |
| ring26_1t | 50 | 52.0 | 1.10 | +0.16 | 05-22..06-04 |
| llama4_scout | 54 | 51.9 | 0.99 | -0.02 | 05-22..06-04 |
| glm4_7_flash | 46 | 52.2 | 1.10 | +0.15 | 05-22..06-04 |
| deepseek_r1 | 59 | 50.8 | 1.13 | +0.30 | 05-22..06-05 |
| grok4_3 | 54 | 46.3 | 1.80 | +1.32 | 05-22..06-05 |
| cursor_agent | 62 | 45.2 | 1.25 | +0.45 | 05-21..06-04 |
| claude_opus_4_7 | 54 | 44.4 | 1.19 | +0.32 | 05-22..06-04 |
| llama4_maverick | 48 | 43.8 | 1.19 | +0.30 | 05-22..06-03 |
| mistral_large | 54 | 35.2 | 1.23 | +0.52 | 05-22..06-04 |
| gh_models_gpt4o | 40 | 37.5 | 1.35 | +0.80 | 05-28..06-04 |
| gemini_2_5_pro | 56 | 42.9 | 0.64 | -0.74 | 05-22..06-04 |
| deepseek_v4_flash | 44 | 45.5 | 0.99 | -0.03 | 05-22..06-05 |
| grok3_direct | 48 | 41.7 | 1.00 | -0.00 | 05-22..06-05 |
| mercury | 50 | 40.0 | 1.02 | +0.05 | 05-22..06-04 |
| deepseek_v3 | 66 | 37.9 | 0.57 | -1.60 | 05-22..06-05 |
| qwen3_6_max | 49 | 30.6 | 0.56 | -0.89 | 05-22..06-04 |
| gpt4_1 | 42 | 35.7 | 0.68 | -0.66 | 05-22..06-05 |
| mistral_small | 51 | 35.3 | 0.34 | -2.17 | 05-22..06-04 |
| aimlapi_gpt4o | 46 | 43.5 | 0.76 | -0.88 | 05-28..06-05 |

Top performers (`grok3`, `kimi_direct`) carry the headline AI-tournament WR. Per MEMORY entry **AI-tournament WR artifact 2026-06-03**, these high-WR figures are partially a **single-snapshot resolver artifact**; treat as suggestive, not validated.

## Top 22 personas (n≥20)

| persona | n | WR% | PF | mean_pnl |
|---|---:|---:|---:|---:|
| risk_parity | 141 | 52.5 | 0.90 | -0.12 |
| momentum_breakout | 134 | 50.0 | 1.03 | +0.05 |
| ml_pattern | 128 | 39.8 | 0.79 | -0.43 |
| trend_continuation | 118 | 50.0 | 1.32 | +0.52 |
| deep_value | 112 | 47.3 | 0.79 | -0.37 |
| macro_sentiment | 101 | 42.6 | 0.85 | -0.30 |
| carry_trade | 71 | 39.4 | 0.49 | -0.70 |
| relative_strength | 61 | 49.2 | 0.93 | -0.13 |
| dividend_compound | 59 | 49.2 | 0.85 | -0.24 |
| multi_tf_confluence | 56 | 42.9 | 1.08 | +0.17 |
| stat_arb | 49 | 44.9 | 1.09 | +0.22 |
| inflation_hedge | 49 | 40.8 | 0.85 | -0.26 |
| regime_adaptive | 47 | 53.2 | 1.76 | +1.09 |
| pivot_catcher | 47 | 40.4 | 0.49 | -4.31 |
| liquidity_grazer | 44 | 43.2 | 1.14 | +0.72 |
| weather_hedge | 40 | 40.0 | 1.45 | +1.18 |
| **oversold_bounce** | **35** | **57.1** | **1.77** | **+1.17** |
| systematic_momentum | 29 | 51.7 | 1.53 | +1.29 |
| vol_arb | 24 | 66.7 | 3.33 | +2.33 |
| macro_hedge | 23 | 60.9 | 2.72 | +3.22 |
| extreme_fear | 20 | 25.0 | 0.66 | -1.12 |
| breakout_scanner | 20 | 40.0 | 0.99 | -0.03 |

**Only persona meeting n≥30 / WR≥55 / PF≥1.2 (asset-agnostic):** `oversold_bounce` (n=35, 57.1% WR, PF 1.77). `vol_arb` and `macro_hedge` look great but are under-powered (n<30).

## Model × persona × asset_class cells (n≥10, WR≥55%, PF≥1.2)

| model_id | persona | class | n | WR% | PF | mean | dates | distinct_days |
|---|---|---|---:|---:|---:|---:|---|---:|
| grok3 | reflexivity_trader | CRYPTO | 11 | 72.7 | 5.27 | +6.48 | 05-23..06-04 | 7 |

Only one survivor, and **7 distinct trading days** out of 12 calendar days — this is one cluster of trades, not a regime-tested signal.

## Strategy-level surface (trading_picks, n≥30 closed)

Top by n (asset-class noted; full list 25 rows in source data):

| strategy | category | source_system | n | WR% | PF |
|---|---|---|---:|---:|---:|
| ig_contrarian_sentiment | forex | multi_asset_copytrader | 3300 | 51.6 | 1.14 |
| myfxbook_retail_contrarian | forex | multi_asset_copytrader | 2364 | 52.4 | 1.17 |
| **non_crypto_consensus** | **commodity** | non_crypto_consensus | **738** | **66.8** | **2.86** |
| non_crypto_consensus | forex | non_crypto_consensus | 1983 | 54.6 | 1.39 |
| cta_commodity_momentum_term | commodity | cta_replicator | 2031 | 48.8 | 1.63 |
| cta_cross_asset_tsmom | forex | cta_replicator | 731 | 53.4 | 1.51 |
| forex_rsi2_mean_reversion | forex | multi_asset_copytrader | 1851 | 52.9 | 1.45 |
| prediction_market_consensus | crypto | prediction_market_agents | 2725 | 47.2 | 1.12 |

`non_crypto_consensus / commodity` is the standout — large-n, high WR, high PF. Verify resolver_version + date span before treating as edge.

## at_pick_outcomes — passing cells (n≥30, WR≥55, PF≥1.2, excluding `signflip_purge_20260`)

| strategy | asset_class | resolver_version | n | WR% | PF |
|---|---|---|---:|---:|---:|
| hs_lb_None | crypto | universal_v2 | 261 | 56.7 | 3.26 |
| MeanReversionBB | equity | universal_v2 | 214 | 55.6 | 1.88 |
| (empty strategy) | CRYPTO | backfill_2026-06-01 | 184 | 66.8 | 4.33 |
| prediction_market_consensus | CRYPTO | backfill_2026-06-01 | 89 | 89.9 | 24.51 |
| luxalgo_confluence | crypto | universal_v2 | 67 | 83.6 | 7.81 |
| luxalgo_confluence | CRYPTO | backfill_widened_202 | 39 | 74.4 | 4.88 |
| ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | CRYPTO | backfill_widened_202 | 39 | 64.1 | 4.34 |
| ml_enhanced_DYDXUSDT_15m_D_ensemble_stack | CRYPTO | backfill_widened_202 | 34 | 94.1 | 10.36 |
| ml_enhanced_RENDERUSDT_4h_D_ensemble_stack | CRYPTO | backfill_widened_202 | 34 | 58.8 | 2.32 |
| battleground_ml_relaxed_mut | crypto | universal_v2 | 31 | 71.0 | 4.35 |
| claude_ml_moderate_mut | crypto | universal_v2 | 31 | 61.3 | 2.74 |

**Two resolver-version cohorts dominate:** `universal_v2` (the trustable post-M-067 resolver) and `backfill_2026-06-01` / `backfill_widened_202*` (post-hoc backfills — DO NOT trust until backfill methodology is audited). `universal_v2` cells (`hs_lb_None`, `MeanReversionBB`, `luxalgo_confluence`, `battleground_ml_relaxed_mut`, `claude_ml_moderate_mut`) are the cleanest seeds. The 89.9% / PF 24.51 `prediction_market_consensus` figure under `backfill_2026-06-01` is implausible vs. the trading_picks 47.2% WR for the same strategy — flag as resolver artifact.

## SQL used

```sql
-- Closed predicate
status IN ('WIN','LOSS','CLOSED','TP_HIT','SL_HIT','LOST','TIME_EXIT','WON','EXPIRED')
-- Forex outlier exclusion
(asset_class<>'FOREX' OR pnl_pct IS NULL OR pnl_pct <= 0.30)

-- 1. Top models
SELECT model_id, COUNT(*) n,
  ROUND(AVG(CASE WHEN status IN ('WIN','WON','TP_HIT') OR pnl_pct>0 THEN 1.0 ELSE 0.0 END)*100,1) wr,
  ROUND(SUM(CASE WHEN pnl_pct>0 THEN pnl_pct ELSE 0 END) /
        NULLIF(-SUM(CASE WHEN pnl_pct<0 THEN pnl_pct ELSE 0 END),0),2) pf,
  ROUND(AVG(pnl_pct),3) mean_pnl,
  MIN(submitted_at) d_in, MAX(COALESCE(resolved_at,submitted_at)) d_out
FROM tournament_picks
WHERE <closed> AND <forex_excl>
GROUP BY model_id HAVING n>=20 ORDER BY n DESC LIMIT 25;

-- 2. Top personas (same shape, GROUP BY persona_id, persona_id<>'' )

-- 3. Cells
SELECT model_id, persona_id, asset_class, COUNT(*) n, <wr>, <pf>, <mean>,
  MIN(DATE(submitted_at)) d_in, MAX(DATE(COALESCE(resolved_at,submitted_at))) d_out,
  COUNT(DISTINCT DATE(submitted_at)) distinct_days
FROM tournament_picks
WHERE <closed> AND <forex_excl>
GROUP BY model_id, persona_id, asset_class
HAVING n>=10 AND wr>=55 AND pf>=1.2
ORDER BY n DESC, pf DESC;

-- 4. trading_picks strategy view
SELECT strategy, category, source_system, COUNT(*) n, <wr>, <pf>
FROM trading_picks WHERE <closed>
GROUP BY strategy, category, source_system HAVING n>=30
ORDER BY n DESC LIMIT 25;

-- 5. at_pick_outcomes
SELECT strategy, asset_class, resolver_version, COUNT(*) n, <wr>, <pf>
FROM at_pick_outcomes
WHERE status IN ('WON','LOST','EXPIRED')
  AND (resolver_version IS NULL OR resolver_version <> 'signflip_purge_20260')
  AND (asset_class<>'FOREX' OR pnl_pct IS NULL OR pnl_pct<=0.30)
GROUP BY strategy, asset_class, resolver_version
HAVING n>=30 AND wr>=55 AND pf>=1.2
ORDER BY n DESC LIMIT 25;
```

## Verdict (inventory only — no strategy proposals)

1. **Tournament side is too young / too sparse to seed cells.** Entire dataset spans 15 days, max cell n=18, single n≥10 survivor (`grok3 × reflexivity_trader × CRYPTO`) covers 7 trading days.
2. **Persona surface has 1 viable global persona seed:** `oversold_bounce` (n=35, WR 57.1, PF 1.77) — class-agnostic, but distribution across classes still needs decomposition.
3. **Real seed material lives in `at_pick_outcomes` `universal_v2` cohort:** `hs_lb_None / crypto` (261), `MeanReversionBB / equity` (214), `luxalgo_confluence / crypto` (67), `battleground_ml_relaxed_mut`, `claude_ml_moderate_mut`. These have trustable resolver versioning.
4. **Reject as resolver-artifact-suspect for now:** anything under `backfill_2026-06-01` or `backfill_widened_202*` resolver_version (notably the 89.9% / PF 24.51 prediction_market_consensus cell) until backfill methodology is audited. Aligns with MEMORY entry `AI-tournament WR artifact 2026-06-03`.
5. **Grok3 + kimi_direct dominate model leaderboard,** but per `AI-tournament WR artifact 2026-06-03`, the WR is partly a single-snapshot resolver artifact — do not derive new strategies from these models in isolation; require intrabar-OHLC re-resolution.
