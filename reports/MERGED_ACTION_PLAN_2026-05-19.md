# Merged Action Plan — Money-Ready Pipeline (2026-05-19)

**Synthesized from:** 30+ model consults (Grok SuperGrok, DeepSeek, xAI, Inception, OpenRouter, Groq, LLM7, Mistral, local Ollama sweep), `reports/NEXT_MOVES_2026-05-19.md`, `reports/QUANT_RESCUE_SWARM_VERDICT_2026-05-19_cursor.md`, `reports/FEEDBACK_AND_ACTIONS_2026-05-19.md`, `reports/MACRO_WHY_NO_EDGE_2026-05-18.md`, `reports/hypothesis_registry.json`, and peer plans (`MASTER_ACTION_PLAN_2026-05-18.md` — **superseded for live-money claims**).

**North star:** Tier-2 charter per class — PF≥1.5, WR≥50%, MDD<20%, n≥100 clean post-dedup. **Today:** paper-only everywhere except narrow forward tracks.

---

## Executive verdict (do not re-litigate)

| Claim | Verdict | Source |
|-------|---------|--------|
| 11/11 pre-registered **daily-bar causal** hypotheses killed | **Settled** | `edge_stability_harness.py`, registry |
| `pf_registry` shows high PF for some classes | **Ledger only** — not harness-admissible edge | Grok, DeepSeek, quant rescue |
| EQUITY/ETF/BOND "money-ready today" | **Reject** for live capital | Claude/OpenCode dissent vs 11/11 |
| CRYPTO `mega_mutation` n=72 PF~2.19 | **Paper track only** until forward harness | Registry + swarm |
| COMMODITY micro-slices (cot, copytrader) | **Conditional** — whitelist emitters, not class-wide | Grok pf_registry autopsy |
| FOREX `cta_replicator` slice | **Paper probe** — buried under toxic volume | Grok |
| New edge = intraday/tick crypto microstructure | **Only bet worth funding** (5–20% P(admissible)) | Grok Q4, xAI, DeepSeek |

**Supersedes:** `MASTER_ACTION_PLAN_2026-05-18.md` "CRYPTO MONEY_READY" row — harness + 11/11 kill take precedence until forward proof.

---

## Tier 0 — This session shipped (tools + docs)

| Artifact | Purpose |
|----------|---------|
| `tools/ollama_import_gguf.py` | Ollama-only GGUF import via blob-path Modelfiles |
| `tools/idea_harvest_mega.py` | Multi-model API + local harvest orchestrator |
| `tools/ollama_gpu_push_benchmark.py` | Tiny→giant GPU/CPU benchmark matrix |
| `tools/local_gguf_ollama_consult.py` | Ollama-only consult runner |
| `swarm_runs/_prompts/MONEY_READY_*.md` | Canonical harvest prompts |
| `BENCHMARK_LOCALAI_DESKTOP.md` | Local model timing log |
| `reports/IDEA_HARVEST_SYNTHESIS_2026-05-19.md` | API wave-1 synthesis |

---

## Tier 1 — Data integrity (Days 1–2) — **unblocks every verdict**

*Merged from NEXT_MOVES #1–4, quant rescue week-1, Grok EMITTER_WHITELIST.*

| ID | Action | wire_target | Acceptance test |
|----|--------|-------------|-----------------|
| **T1-01** | Clamp/reject `confidence` >1.0 at emission | pick writers + `sync_all_picks_to_mysql.py` | Zero rows with confidence>1 in new inserts |
| **T1-02** | Dedup guard before `at_raw_picks` append | emitter layer + `dedup_hash` | Re-emission rate <5% on 200 new closes |
| **T1-03** | Dashboard reads **only** `pf_registry.json` policy_clean_net | `audit_trail/dashboard_generator.py`, tiles | Raw tile PF within 0.15 of canonical per class |
| **T1-04** | Run scale-mismatch backfill `--apply` | `tools/backfill_resolver_scale_mismatch.py` | HG=F corrupt row fixed; .bak preserved |
| **T1-05** | Widen harness ledger scope (32 files) | `tools/edge_stability_harness.py` | `ensemble`/`st_fear_greed` cohorts visible |
| **T1-06** | Mandatory insert fields: `hypothesis_id`, `bar_freq`, `policy_clean` | schema + writers | 100% new rows populated |

---

## Tier 2 — Emitter hygiene (Days 2–4) — **highest ROI from AI harvest**

*Grok #1 + #2; supersedes "promote CRYPTO to live" from older master plan.*

| ID | Action | wire_target | Acceptance test |
|----|--------|-------------|-----------------|
| **T2-01** | **Emitter whitelist** from pf_registry | `ml_consensus/consensus.py`, `alpha_engine/forward_validator.py` | Toxic (class,strategy) pairs with n≥20 & PF<1.2 → 0% of new n |
| **T2-02** | **Kill switch** worst pairs | `tools/build_pf_registry.py` + `BLOCKED_ASSET_STRATEGY_PAIRS` | Block: `quan_engine`/CRYPTO, `cta_replicator`/COMMODITY, `multi_asset_copytrader`/FOREX,EQUITY |
| **T2-03** | `local_fast_filter.py` (80-line hot path) | new module before ML scoring | 300 filtered closes: PF≥1.55, WR≥52%, <5ms |
| **T2-04** | Halt FUTURES emitter | config + workflow gate | n=12 class frozen; no new FUTURES picks |
| **T2-05** | Freeze **new** non-crypto daily-bar hypotheses | `reports/hypothesis_registry.json` M-107 | No new H-* daily families outside crypto until probe result |

**Whitelist seeds (Grok pf_registry, May 2026):**
- CRYPTO: `crypto_rsi_whaleconfirmed_v1` (PF~1.58, n~89) — gate `quan_engine`
- COMMODITY: `multi_asset_cot`, `multi_asset_copytrader` — block `cta_replicator` on COMMODITY
- FOREX: `cta_replicator` only (PF~3.17 clean n~103) — block copytrader on FOREX

---

## Tier 3 — The one edge bet (Days 5–14) — paper only

*Merged from NEXT_MOVES #5–6, quant rescue, FEEDBACK H-032 miner capitulation **vs** intraday imbalance — register ONE.*

| ID | Action | Notes |
|----|--------|-------|
| **T3-01** | Pre-register **H-035** (example): signed volume imbalance / liquidation reversion at **tick** resolution | NOT on killed-family list; `bar_freq=intraday` |
| **T3-02** | Binance 1m + aggTrade → parquet/MySQL | `tools/` new fetcher; top 10–12 perps |
| **T3-03** | 2–4 week **probe** through harness | Stop if no window clears eff/sign/cost |
| **T3-04** | Optional: H-033 EQUITY overnight XS reversal, H-034 anti-PEAD 1d | Secondary; only after T1–T2 green |

**Do NOT week-1:** universe widening; meta-labeling on daily noise; promote registry PF to live.

**Swarm candidate (register separately):** BTC miner capitulation / hash ribbon (FEEDBACK_AND_ACTIONS) — physical constraint thesis; requires user sign-off before backtest (M-107).

---

## Tier 4 — Forward tracks (ongoing)

| ID | Track | Action |
|----|-------|--------|
| **T4-01** | `mega_mutation` | Paper ledger only; forward harness is verdict |
| **T4-02** | `st_fear_greed_contrarian` | Re-harness at n~400 (~10 weeks) |
| **T4-03** | H-001 COT | WATCH — 2/3 windows; live testing 10% Kelly; re-check 2026-05-26 |

---

## Tier 5 — Infra / deploy (value regardless)

| ID | Action | Source |
|----|--------|--------|
| **T5-01** | Deploy `pf_registry.json` + `money_ready_filter.js` to `/audit` | NEXT_MOVES #11 |
| **T5-02** | Stage B writer flip after dry-runs | NEXT_MOVES #9 |
| **T5-03** | FUTURES resolver orphan fix | `alpha_engine_unified` in `SYSTEM_SOURCES` |
| **T5-04** | HF router credits depleted — use Groq/OpenRouter/Ollama | This session |

---

## Local AI stack (operational)

| Use case | Model | tok/s (RTX 5070) |
|----------|--------|------------------|
| Bulk screen | `smollm2:1.7b`, `llama3.2:1b` | 165–266 |
| Balanced harvest | `qwen2.5-coder:7b` | ~118 |
| Deep tables | `qwen2.5-coder:14b-instruct-q4_K_M` | ~62 |
| Reasoning 14B | `qwen3:14b` + `num_gpu=99`, `num_predict≥1200` | ~185s |
| 32B hybrid | `deepseek-r1:32b` | 52/48 CPU/GPU, slow |
| 70B+ | `gpt-oss:120b-cloud` or Grok API | not local VRAM |

**Commands:** `python tools/idea_harvest_mega.py --tier all` · `python tools/ollama_gpu_push_benchmark.py --phase all`

---

## Hypothesis registry — status snapshot

- **KILLED (harness):** H-006–H-020 family (funding, COT directional, netflow, cross-exchange, etc.) — see registry `status: KILLED`
- **LIVE_TESTING:** H-001 COT (COMMODITY) — do not confuse with class-wide edge
- **SHADOW:** H-002 PEAD, H-003 ETF momentum (harness rejected), H-004 inventory surprise (implemented, backtest pending)
- **FAILED_ARCHIVED:** H-005 FUTURES momentum inversion test

**Rule M-107:** Any new family (H-035+) → commit registry **before** any backtest.

---

## Conflicts resolved (merged plans)

| Older plan | This plan |
|------------|-----------|
| MASTER 2026-05-18: CRYPTO MONEY_READY live | → Paper + emitter whitelist first |
| quickest-path: 10 ml_enhanced cohorts admissible | → Narrower; 11/11 causal kill + Grok toxic-volume autopsy |
| FEEDBACK: BTC hash ribbon as H-032 | → Queue as **optional** H-036; intraday probe is primary |
| Ring/OpenRouter "EQUITY ready" | → **Rejected** for live |

---

## Week-1 checklist (copy-paste)

- [ ] T1-01 … T1-06 data integrity
- [ ] T2-01 emitter whitelist wired
- [ ] T2-02 toxic pair kill switch
- [ ] T2-04 halt FUTURES emitter
- [ ] T3-01 pre-register intraday hypothesis
- [ ] T3-02 Binance tick fetcher
- [ ] T4-01 mega_mutation paper table live
- [ ] T5-01 deploy audit aux files

**Reproducers:** `reports/QUANT_RESCUE_SWARM_VERDICT_2026-05-19_cursor.md` · `python tools/edge_stability_harness.py` · `python tools/idea_harvest_mega.py --tier api`

---

*Generated 2026-05-19. Supersedes conflicting "money-ready today" claims until harness clears a new family.*
