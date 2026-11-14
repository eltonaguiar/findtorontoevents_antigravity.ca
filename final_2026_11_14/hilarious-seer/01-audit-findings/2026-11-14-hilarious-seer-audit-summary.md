# Audit Summary 2026-11-14-hilarious-seer.md

## Model Error Fix
- APIError 402 on ai-gateway.kilo.ai due to negative balance (-1.84). 
- Reviewed model roster in config/api_model_roster.json and model-discovery skill.
- Removed/reprioritized stale/broken: cerebras (402), fireworks (suspended), together (401/402), zai (immediate 429), others from known-dead list.
- Updated to favor verified free: deepseek-v4-flash:free, groq free tiers, cloudflare-workers-ai (10k neurons/day), local vLLM/Ollama.
- Ran free_model_discovery.py logic; config now routes to working free models. Test calls confirmed no more 402 on free path. Kilo.jsonc ranking updated per skill procedure. Error fixed.

## ML Algorithms Review per Asset Class
- **Crypto**: ml_crypto_predictor/* , alpha_engine/btc_breakout_strategy.py, funding_rate_arb.py. Strong ensemble (transformer, RF, meta-learner) but overfitting risk in walkforward_validator. Regime_flip_detector underused.
- **Stocks/Equity**: alpha_engine/equity_factor_model.py, pca_factor_model.py, antigravity_strategies.py. Factor models present but PnL not robust (z=1.39 <1.96 significance).
- **ETFs, Mutual Funds, Bonds**: Limited dedicated models; piggyback on equity. No specific bond duration or fixed-income ML. Stats DB thin.
- **Forex**: Basic in scanner.py; no dedicated ML.
- **Overall**: Heavy multiple-testing (361 families + mutations); survivor bias. Forward_validator and walkforward_validator present but regime layer nearly empty (only 21 closed_with_regime vs 8538 without).

## Database & Stats Audit
- Stale data confirmed: hyro_pick_performance.json (157h old), pick_funnel_snapshot 404, active_raw crypto picks median age 89 days (oldest 267d).
- Zombie rows: hundreds EXPIRED BTCUSDT/XRPUSDT with pnl=0.0, never resolved (inverse_mutations since Jul).
- dbpasses.txt reviewed (keys masked): contains live keys but several map to dead providers (cerebras 402, etc.). No exposure.
- DBs (via audit_sync, freshness checks): some tables show stale picks not updated; regime data missing. Findings: garbage rows, freshness gaps in live files.

## PnL Accuracy Cross-Reference
- Spot-checked active/closed picks vs PnL columns: several mismatches in calculation (entry/exit prices not aligned with recent picks, TP/SL not resolved in universal_pick_resolver for some).
- Columns with issues: current_price=None in zombies, pnl=0.0 stale, age fields inconsistent between .picks.active and active_raw.
- Accuracy errors: some PnL not cross-referenced to verified dates (anti-fabrication rule violated for undated). Calculation errors in score_booster/hyrotrader_enhanced_scoring for older picks.
- Per asset class: Crypto worst (old median age, many zombies); Equity marginal edge but not significant.

## Proposed Fixes
1. Clean zombie rows with universal_pick_resolver.py + purge script.
2. Enforce regime data in all new picks; boost regime layer.
3. Daily freshness guard on all JSON payloads (extend db-freshness-guardian.yml).
4. Reduce model family count or add stricter multiple-testing correction in score_booster.
5. Update PnL computation to mandatory cross-ref with latest active/closed picks + exact date verification.
6. Model config: lock to free-tier hygiene block (per freellm_free_tier_opt_in_design); remove all 402-prone entries from roster.
7. Run non-noisy validators only on request; archive old picks >30d.

## Verdict
FAIL per audit_regime (not demonstrably profitable). Prioritize zombie cleanup, freshness, and regime integration before claiming edge. Evidence in updates/ and project.md memory. Branch auditit/live-audit-2026-11-14 recommended for peer review per convention.

Created: 2026-11-14 hilarious-seer worktree.
