# KILOCODE_OPENRMIMO — Cross-AI Convergence Handoff
## 2026-05-26 → 2026-05-27 session

Five independent AI agents produced overlapping audits of `/audit`, `/audit/hyrotrader`, `/audit/ai-tournament.html`. This file captures **what they all agreed on** (= signal) vs **where they disagreed** (= where to investigate more).

## Participating agents

| Agent | Working dir / model | Key contribution |
|---|---|---|
| **Claude Opus 4.7** (this session) | findtorontoevents_antigravity.ca | 5 merged PRs (#3-#7), 14 new GH secrets, 23-model fleet, retraction discipline (TICK 15) |
| **RooCode** (vllm server) | parallel | Audit-quality analysis + kilocode-improvement skill scaffold |
| **MiMo v2 Flash via OpenRouter** | parallel | Best-practices framework + per-class scorecard |
| **Kilo Code (vllm server)** | parallel | Strategy reverse-engineering + consult-swarm skill rewrite |
| **Two subagents + DeepSeek consult** | Claude-spawned | World-class benchmark + gameplan + strategy reverse-engineering |

## CONSENSUS — all 5 agents agree

### 1. We are NOT world-class today.

Hard data (canonical `pf_registry.json::by_asset_class_policy_clean_net`, fresh):
- CRYPTO: n=210, WR 31%, PF 0.96, total_pnl -0.86%
- FOREX: n=11, WR 9%, PF 0.20
- FUTURES: n=11, WR 9%, PF 0.47
- EQUITY/COMMODITY/ETF/BOND: missing from canonical (INSUFF-N filtered)
- `money_ready_verdict.json::summary.money_ready = []` and `watch = []`

World-class benchmark: Renaissance Sharpe 2.0+ / WR 70%, Two Sigma Sharpe 1.5+, AQR 0.8-1.2, Citadel 1.0+. We are below all of them on every class with data.

### 2. Only 3 strategies show genuinely unsaturated edge.

| Strategy | DSR | n (raw / deduped) | Verdict |
|---|---:|---|---|
| **COMMODITY: cot_positioning SHORT** (CT=F) | 1.0 | 137 / **5** | SHADOW_INSUFFICIENT_N (Claude TICK 15 caught 26x over-emission) |
| **CRYPTO: ml_crypto_predictor** | >=0.95 | 255 | EDGE_LIKELY_REAL — needs slippage adjustment |
| **EQUITY: stocks_rsi2_pullback** | 0.994 | 70 | EDGE_LIKELY_REAL — bull-regime-dependent, recent PF 0.76 |

The dashboard's "78.9% CRYPTO Smart-Picks" number is the EXPIRED→WON mislabel trap, not edge.

AI Tournament: grok3 is the only model with PF lower-95-CI > 1.0 (n=13 resolved, BUILDING).

### 3. The biggest mistake is treating the 23-model ensemble as robustness.

DeepSeek consult (verbatim): *"They are optimizing for in-sample Sharpe via a massive model ensemble that memorizes noise, while data contamination (38.97% PnL mismatch, 56,559 ghost rows, frozen validator) makes all backtests unreliable. They mistake model complexity for robustness."*

All 5 agents independently flagged this. Strip to 1 simple CRYPTO model on clean data before adding any more.

## CONSENSUS — first 14-day gameplan

1. **Stop adding strategies. Fix data first.** Resolver chain green today. Apply Phase 1.2 relabel SQL (pending user MySQL run). Run db_health.json `won_pnl_contradiction` autopsy (2,595 WON rows averaging -40% PnL).
2. **Permutation test the 3 EDGE_LIKELY_REAL strategies.** Shuffle target labels 1,000 times, retrain, require real PF in 99th percentile of noise.
3. **Strip to 1 simple CRYPTO model.** 3-5 features, linear, strict 20% holdout never retrained. Beat the 23-model ensemble OOS or kill the ensemble.

## CONSENSUS — spend / cut

ADD spend on:
- Senior quant with live-trading track record (3-month audit)
- Tick-level CRYPTO data (Coinbase/Binance nanosecond timestamps)
- Compute for Monte Carlo permutation + bootstrap (NOT more models)

CUT:
- 20 of 23 model API subs (keep top-3 by OOS Sharpe — likely zero)
- All FOREX/FUTURES/EQUITY/COMMODITY/ETF/BOND dev until CRYPTO data is clean
- Regime gates + ML composite scoring layers (complexity without evidence)

## DISAGREEMENT — where agents split

| Question | Claude (this session) | RooCode | MiMo | Kilo Code | DeepSeek |
|---|---|---|---|---|---|
| Is COT positioning currently usable? | NO — SHADOW_INSUFF (n=5 deduped) | NEEDS_CLEANUP | PROMISING after cleanup | PROBATION-ready | n/a |
| 90-day single bet | CRYPTO (data volume) | n/a | COMMODITY | n/a | CRYPTO |
| Mercury pipeline | Switched to Together AI (PR #6) | n/a | n/a | n/a | Recommend kill |
| AI Tournament value | High-conviction once n>=30/model | Promising | Universe-mismatch risk | n/a | Skeptical until permutation-tested |

## ACTION items merged across all 5 agents

### Tier 1 (this week — DO)
- [x] PR #3-#7 merged (resolver fix + 13-workflow sweep + 23-model fleet + audit-trail + round-2 sweep)
- [x] 14 GH secrets set (NVIDIA, Groq, Together, Fireworks, etc.)
- [x] Outcome resolver workflow green (29h freeze ended)
- [x] consult-swarm skill created (.claude/skills/consult-swarm/SKILL.md — Kilo Code's rewrite)
- [x] Subagent reports written (5 reports in reports/2026-05-27_*.md)
- [ ] **USER MySQL run**: tools/relabel_closed_picks_mysql.sql (6,093 row CLOSED→WON/LOST relabel)
- [ ] **USER**: Set 3 more GH secrets (OPENAI_API_KEY, ANTHROPIC_API_KEY, INCEPTION_API_KEY) — keys not in dbpasses.txt

### Tier 2 (next 14 days)
- [ ] Permutation test on 3 EDGE_LIKELY_REAL strategies
- [ ] Simple-baseline CRYPTO model: 3-5 features, linear, strict OOS
- [ ] db_health autopsy: characterize the 2,595 WON+negative-PnL rows
- [ ] CT=F COT: wait for n>=20 unique CFTC releases (~Aug 2026)
- [ ] stocks_rsi2_pullback: add SPY>200SMA gate, RSI<5 entry filter, 2xATR stop
- [ ] AI tournament min_n_to_rank=30 reachable: ~Jul 2026 at current 23-model daily emission

### Tier 3 (90-day)
- [ ] AQR-tier (Sharpe 0.8-1.2) realistic only after clean data + 1-year live track
- [ ] If CRYPTO + simple-model doesn't reach PF 1.2 by Aug 2026, pivot to execution-only (market making, latency arb)

## CRITICAL LESSON LEARNED (Claude TICK 15)

The 230-trade CT=F COT cohort I called "Tier-1 candidate" in TICKs 9/11/12 was **26x over-emitted**. Real deduped n=5, WR 40%, cum -$51.29. Never accept a strategy n that exceeds the natural cadence of its signal source (CFTC COT releases weekly → max ~4 trades/month/symbol, not 230 in 22 days). The dashboard's `cot_paper_pilot_status.json` had the deduped truth all along.

This applies everywhere: always check the dedup view + the over_emission_ratio field before drawing edge conclusions.

## FOR THE NEXT AI READING THIS

1. **Read this file first.** It's the cross-AI consensus.
2. **Don't add more models.** 23 is already overkill; ensemble noise > signal until simple-baseline beats it.
3. **Don't trust raw aggregates.** Check the `_dedup` or `_policy_clean_net` views first.
4. **The 3 EDGE_LIKELY_REAL strategies need permutation testing.** Schedule it before any sizing decision.
5. **Data integrity (P0 #4/#5/#6/#7) must be 100% green before believing ANY new backtest.** db_health.json shows the live truth.

— Signed: Claude Opus 4.7, 2026-05-27 03:25 UTC. Co-authors: RooCode, MiMo v2 Flash, Kilo Code, DeepSeek v4 Flash.
