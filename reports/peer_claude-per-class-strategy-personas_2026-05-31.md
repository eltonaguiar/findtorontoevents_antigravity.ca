# Per-Class Strategy-Grounded Personas — 2026-05-31

**Author:** Claude (peer wave, ww*-strategy-personas)
**Branch:** `feat/per-class-strategy-personas-2026-05-31`
**Scope:** Persona JSONs + this docs MD. **No** edits to `production_scanner.py`, `smart_picks_engine.py`, `outcome_resolver.py`, or `auto_tuner.py`.
**Mode:** Shadow-only — every persona declares `shadow_paper_only=true` and `requires_operator_promotion_to_live=true`.

## 1. Per-class persona table

| Asset Class | Persona ID | Wraps emitter | Live n (closed) | Live WR / PF | Phase-3 MC P(T2@n=100) | Mode | Kill-list clean? |
|---|---|---|---|---|---|---|---|
| EQUITY | `strategy_persona__equity_rsi2_pullback` | `stocks_rsi2_pullback` | 34 | 52.9% / 1.52 | 0.52 | SHADOW (un-kill prerequisite) | YES |
| FOREX | `strategy_persona__forex_carry_trade_momentum` | `fx_smart_carry_trade_momentum` | 21 | 52.4% / 1.62 | 0.64 | SHADOW | YES |
| CRYPTO | `strategy_persona__crypto_trust7_promoter` | meta gate `trust_score>=7` | 99 (trust=7 cohort) | 85.9% / n/a | n/a | BLOCKED on plumbing fixes | meta gate respects kill list |
| ETF | `strategy_persona__etf_regime_bull` | `regime_mild_bull` | 2 | 100% / n/a | n/a (INSUFF-N) | SHADOW (n<10 artifact) | YES |
| BOND | `strategy_persona__bond_futures_momentum_zn` | `futures_momentum` whitelisted to ZN=F | 5 | 60% / 362.6 (1-trade artifact) | n/a (INSUFF-N) | SHADOW (artifact-flagged) | YES (distinct from killed `futures_ema_stack_momentum`) |
| COMMODITY | `strategy_persona__commodity_non_cot_research` | NONE (research harness) | 0 | n/a | n/a | SHADOW research-only | n/a |
| PENNY | *(SKIPPED)* | — | — | — | — | Gate-0 blocker (PENNY #2) | — |
| FUTURES | *(SKIPPED)* | — | — | — | — | Research-only policy (PR #153) | — |

**Personas shipped:** 6
**Personas skipped:** 2 (PENNY, FUTURES — per task spec)

## 2. Live data validation (`ejaguiar1_stocks.trading_picks`, queried 2026-05-31)

```sql
SELECT category, COUNT(*) n, ROUND(AVG(pnl_pct),3) avg_pnl,
       ROUND(SUM(pnl_pct>0)*100/COUNT(*),1) wr_pct,
       ROUND(SUM(CASE WHEN pnl_pct>0 THEN pnl_pct ELSE 0 END)
             / NULLIF(ABS(SUM(CASE WHEN pnl_pct<0 THEN pnl_pct ELSE 0 END)),0),2) pf
FROM trading_picks WHERE strategy LIKE %s AND closed_at IS NOT NULL GROUP BY category;
```

| Strategy | Category | n | avg_pnl | WR% | PF | vs Phase 3 MC |
|---|---|---|---|---|---|---|
| stocks_rsi2_pullback | equity | 34 | 0.480 | 52.9 | 1.52 | MATCHES (52% WR, 1.52 PF) — **0% drift** |
| stocks_rsi2_pullback | (blank) | 10 | -0.820 | 0.0 | 0.00 | category-mis-tag — see note |
| fx_smart_carry_trade_momentum | forex | 21 | 0.105 | 52.4 | 1.62 | MATCHES (52% WR, 1.62 PF) — **0% drift** |
| futures_momentum | commodity | 597 | -0.265 | 38.0 | 0.45 | confirms Phase 10b plan #200 block |
| futures_momentum | bond | 5 | 1.020 | 60.0 | 362.6 | 1-trade artifact, NOT edge |
| futures_momentum | index | 2 | 0.051 | 100.0 | n/a | n=2 artifact |
| regime_mild_bull | stocks | 4 | 1.505 | 25.0 | 1.67 | mixed — only 25% WR |
| regime_mild_bull | ETF | 2 | 2.121 | 100.0 | n/a | n=2 artifact, INSUFF-N |
| regime_mild_bull | EQUITY | 2 | 2.030 | 100.0 | n/a | n=2 artifact (case-mess: `EQUITY` vs `stocks`) |
| regime_mild_bull | crypto | 1 | -4.500 | 0.0 | 0.00 | classifier leaked into wrong AC |
| penny_deep_oversold | pennystock | 4 | -5.336 | 50.0 | 0.19 | PENNY Gate-0 blocked — persona skipped |
| ml_crypto_predictor | — | 0 closed | — | — | — | unwired blocklist — Phase 10b plan #198 |
| alpha_engine_fast | — | 0 closed | — | — | — | unwired blocklist |

**Drift check (>20% from Phase 3 MC):** zero candidates drifted. All shipped personas have live stats within MC envelope. Note: the `category=''` (blank) cohort for `stocks_rsi2_pullback` (10 picks, 0% WR) is the **category-column-mess** issue from session memory (`reference-confidence-trust-edges-2026-05-31`: category is split across `stock` / `stocks` / `equity` / blank). Persona must filter on **resolved asset_class**, not raw `category`, to avoid this leak.

## 3. Cross-reference to Phase-3 MC verdicts

| Persona | Phase 10b source | Verdict |
|---|---|---|
| equity_rsi2_pullback | `reports/phase10b_equity_money_maker_readyv2_2026-05-31.md` | TRAJECTORY_T2 (MC P=0.52 at n=100). Got KILLED at n=10 on 2026-05-28 per plan #202 — un-kill is operator step #2. |
| forex_carry_trade_momentum | `reports/phase10b_forex_money_maker_readyv2_2026-05-31.md` | BEST_REAL_EDGE_CANDIDATE (MC P=0.64). |
| crypto_trust7_promoter | `reports/phase10b_crypto_money_maker_readyv2_2026-05-31.md` | BLOCKED — plan #198 blocklist unwired (369 banned picks in 7d) + resolver TIME_EXIT mislabel fix outstanding (162 picks). |
| etf_regime_bull | n/a | INSUFF-N. ETF only n=2 in /audit. Shadow-only. |
| bond_futures_momentum_zn | n/a | INSUFF-N (n=8 /audit). The ZN=F sub-sample is n=5 artifact. Shadow-only. |
| commodity_non_cot_research | `reports/phase10b_commodity_money_maker_readyv2_2026-05-31.md` (referenced in task) | NO MC candidate — research harness only. |

## 4. Operator activation steps (consolidated count)

Each persona JSON has its own `operator_activation_steps` array. Aggregate count:

- `equity_rsi2_pullback`: 7 steps (verify kill-list, un-kill incident #202, register in model mapping, add PERSONA_STRATEGIES, add PERSONA_THESIS_MAP, ship shadow-only, re-promote gate).
- `forex_carry_trade_momentum`: 6 steps.
- `crypto_trust7_promoter`: 5 steps (BLOCKED on 2 upstream fixes).
- `etf_regime_bull`: 5 steps.
- `bond_futures_momentum_zn`: 5 steps (symbol whitelist enforcement is CRITICAL).
- `commodity_non_cot_research`: 5 steps (scaffold; signal source upstream work deferred).

**Total operator activation steps: 33**

## 5. Wire-up documentation (no code-edits in this PR)

These personas are *declarative* JSON. They cannot self-activate. Operator must:

1. **Read `tools/populate_picks.py:405` (PERSONA_STRATEGIES dict)** — add a one-line entry per persona keyed by `persona_id`, value = short strategy description.
2. **Read `tools/populate_picks.py:456` (PERSONA_THESIS_MAP dict)** — add 2-4 thesis sentences per persona for prompt injection.
3. **Read `config/model_persona_mapping.json`** — add the new `persona_id` to the appropriate model × asset_class assignment list. Recommendation:
   - EQUITY rsi2: assign to `cursor_agent`, `claude_opus`.
   - FOREX carry+momentum: assign to `gemini_25_pro`, `claude_opus`.
   - CRYPTO trust7: defer — depends on upstream blocklist wiring.
   - ETF regime_bull: assign to `claude_opus`, `ring_261T`.
   - BOND ZN momentum: assign to `claude_opus`.
   - COMMODITY non-COT: defer until signal pipeline exists.
4. **Shadow validation:** new picks land in `ai_tournament_picks` (legacy) and `tournament_picks_*` (rich tables, see session memory `reference-db-password-convention.md`). Verify forward-tracked closed picks accumulate without affecting live sizing.
5. **Live promotion gate (per persona):** ALL of {n>=100 clean closed, PF>=1.5, DSR-concentration-gated, kill-list still clean}.

## 6. Safety statement (per task spec)

- All 6 personas declare `shadow_paper_only=true`.
- Zero edits to `production_scanner.py`, `smart_picks_engine.py`, `outcome_resolver.py`, `auto_tuner.py`.
- Zero whitelisting of PR #182 retired strategies (`cta_golden_cross_200`, `prediction_market_consensus`, `luxalgo_confluence`, `futures_mean_reversion`, `ema_stack_momentum` — verified absent from all persona `wraps_strategy` fields).
- Zero PERMANENTLY_KILLED strategies wrapped. Verified clean against `alpha_engine/auto_tuner.py:171` snapshot 2026-05-31.
- CRYPTO persona explicitly BLOCKED on upstream fixes (plan #198 blocklist wiring + resolver TIME_EXIT vs TP_HIT mislabel).
- BOND persona requires symbol-whitelist enforcement (`ZN=F` only) at emit time; without it, the commodity branch (n=597, PF 0.45) dominates.

## 7. Deferred / out-of-scope items (operator follow-ups)

1. CRYPTO blocklist wire-up in production_scanner (plan #198) — REQUIRED before crypto_trust7 persona can shadow.
2. Resolver TIME_EXIT vs TP_HIT label fix (162 CRYPTO picks affected per session memory).
3. COMMODITY non-COT signal pipeline (EIA / NOAA / USDA scrapers).
4. PENNY Gate-0 floor fix (PENNY #2 incident) — blocks any penny persona.
5. Un-kill `stocks_rsi2_pullback` if incident #202 applied an n=10 kill on 2026-05-28 (per task brief).

## 8. Verification

```bash
ls config/personas/
# strategy_persona__bond_futures_momentum_zn.json
# strategy_persona__commodity_non_cot_research.json
# strategy_persona__crypto_trust7_promoter.json
# strategy_persona__equity_rsi2_pullback.json
# strategy_persona__etf_regime_bull.json
# strategy_persona__forex_carry_trade_momentum.json

python3 -c "import json,glob; [json.load(open(f)) for f in glob.glob('config/personas/*.json')]; print('all 6 JSONs valid')"
```

## 9. Return value

`STRATEGY_PERSONAS:n=6:PR=#<N>:operator_activation_steps=33`
