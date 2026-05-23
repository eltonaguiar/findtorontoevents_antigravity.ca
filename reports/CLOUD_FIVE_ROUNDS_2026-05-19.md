# Cloud five-round analysis — money-ready pipeline (2026-05-19)

**Runs:** `swarm_runs/model-grill/20260519T205610Z` … `20260519T205851Z`  
**Total:** **19/19 OK** (0 cloud failures)  
**Posture:** 11/11 daily-bar causal hypotheses killed · paper-only · `pf_registry` canonical

---

## Round scorecard

| Round | Wave | Prompt | Models | OK | Top intel |
|-------|------|--------|--------|-----|-----------|
| **1** | paid | `narrow` (DB/GHA) | Grok, Mercury-2, DeepSeek | 3/3 | DeepSeek **4**, Grok **4** |
| **2** | paid | `master` (full consult) | Grok, Mercury-2, DeepSeek | 3/3 | DeepSeek **4** |
| **3** | ring | `harvest` (per-class) | OR/free, Ring-2.6, Ling-2.6, Ling-flash | 4/4 | Ring **3** |
| **4** | ring | `r2` (methodology) | same OpenRouter quartet | 4/4 | OR/free **4** |
| **5** | cloud_deep | `r3` (worst-strategy / mutation) | Grok, DeepSeek, Ring, DS-v4-flash, Qwen3.6-max | 5/5 | Qwen3.6-max **4** |

**Fastest high-quality:** Grok ~3–8s (narrow/r3) · DeepSeek ~15–37s (narrow/master) · Qwen3.6-max ~98s (deepest mutation design)

---

## Cross-round consensus (trust these themes)

### 1. No class is live money-ready

Every paid + ring round agrees: **reject** EQUITY/ETF/BOND “ready today” from registry PF alone. Ring harvest: *“11/11 killed. Zero surviving causal edges.”*

### 2. Highest ROI = emitter hygiene + harness discipline (not new scanners)

| Theme | Rounds | wire_target |
|-------|--------|-------------|
| Enforce whitelist | 1, 5 | `alpha_engine/emitter_whitelist.py` → `EMITTER_WHITELIST_ENFORCE=1` |
| Registry → consensus mask | 5 | `ml_consensus/consensus.py` + `forward_validator.py` |
| Harness before capital | 2, 4 | `tools/edge_stability_harness.py`, `tools/fdr_control.py` |
| Canonical dashboard PF | 1, 2 | `audit_trail/dashboard_generator.py` |

### 3. Only funded *new* edge bet: CRYPTO intraday / tick

| Model | Hypothesis sketch |
|-------|-------------------|
| DeepSeek master | M-107 — 5m volume-weighted reversal (not daily-bar) |
| Ring harvest | UTXO age-cohort / microstructure (low P) |
| Local round 2 | **H-035** — Binance aggTrade imbalance (preferred — already in merged plan) |

**Action:** Pre-register **H-035** in `reports/hypothesis_registry.json`; build `tools/binance_aggtrade_fetcher.py`.

### 4. Per-class narrowing (stop vs keep)

| Class | Stop (consensus) | Keep / probe |
|-------|------------------|--------------|
| **CRYPTO** | `quan_engine` volume, funding arb, killed on-chain counts | Whitelist seeds; intraday H-035; `mercury2-scan`, incubator |
| **EQUITY** | PEAD, copytrader toxic, new daily-bar families | Shadow floors; forward n→100; H-032/E1 after pre-reg |
| **COMMODITY** | `cta_replicator`, COT/roll-yield daily | `multi_asset_cot` slices; term-structure **mutation** (Qwen r3) before live |
| **FOREX** | `multi_asset_copytrader` | `cta_replicator` paper slice; mutation protocol before kill |
| **ETF** | flow noise until n≥100 | Ring: ETF premium arb **highest P(~12%)** — still needs harness |
| **BOND** | yield-curve PEAD variants | `etf-bond-scanner` paper only |

*Verify workflow names against* `reports/LOCAL_LLM_ROUND2_CODEBASE_NARROW_2026-05-19.md` *— cloud models hallucinate `crypto_picks.yml` style paths.*

### 5. Strategy / backtest / mutation / APIs

| Lever | Verdict | Notes |
|-------|---------|-------|
| New daily strategies | **No** (freeze M-107) | Exception: one intraday CRYPTO family |
| More backtesting | **Yes** | `ejaguiar1_backtests`, genome/incubator GHA |
| Better backtesting | **Yes** | Walk-forward, costs, FDR (`tools/fdr_control.py`), dedup |
| DNA mutation | **Conditional** | Qwen r3: mutate toxic pairs on **universe/horizon/filter** axis; harness sign-stability required |
| More free APIs | **Targeted** | Binance aggTrade (CRYPTO); not broad API sprawl |

---

## Best ideas by round (repo-grounded, de-hallucinated)

### Round 1 — narrow (DeepSeek + Grok)

- Table-level STOP/KEEP by killed family + toxic pairs
- **T1-06** style: mandatory `hypothesis_id`, `bar_freq`, `policy_clean` on inserts

### Round 2 — master (DeepSeek)

- **P0:** Harness gate before any capital allocator
- **P1:** Immutable killed-list in hypothesis registry
- **P2:** Intraday pipeline branch for CRYPTO/COMMODITY
- Worst pair autopsy: **(CRYPTO, quan_engine)** → mutate horizon to intraday / vol-gated

### Round 3 — harvest (Ring-2.6)

- ETF relative-value dislocation = **highest 12mo P(T2)** among classes (~12%) — still unproven
- COMMODITY: ~1% — COT/roll-yield menu exhausted
- CRYPTO: ~2% unless non-forbidden microstructure family

### Round 4 — methodology (OR/free)

- End-to-end funnel: emitter → dedup → resolver → pf_registry cohort → harness → forward CSV
- **FDR ≤ 0.10** before “proven” label
- Stop rules: eff fail 2 windows → kill; confidence>1 → clamp + flag

### Round 5 — worst-strategy (Qwen3.6-max)

- Mutation table for `quan_engine`/CRYPTO, `cta_replicator`/COMMODITY, `copytrader`/FOREX+EQUITY
- **`EMITTER_WHITELIST_FROM_REGISTRY`** integration design (consensus + forward_validator)
- Acceptance: sign-stability ≥0.65 rolling 60d; OOS PF≥1.15; kill switch to audit trail

---

## Model routing guide (cloud)

| Task | Model |
|------|--------|
| Brutal per-class verdict | **DeepSeek** `deepseek-chat` |
| Fast executive summary | **Grok** `grok-3-latest` |
| Draft / breadth | **Mercury-2** (verify — often overclaims Y) |
| Novel hypothesis angles | **Ring-2.6-1t** |
| Methodology / funnel spec | **openrouter/free** (surprisingly strong on r2) |
| Mutation + whitelist architecture | **qwen/qwen3.6-max-preview** |

---

## Outputs on disk

| Round | Directory |
|-------|-----------|
| 1 | `swarm_runs/model-grill/20260519T205610Z/` |
| 2 | `swarm_runs/model-grill/20260519T205647Z/` |
| 3 | `swarm_runs/model-grill/20260519T205706Z/` |
| 4 | `swarm_runs/model-grill/20260519T205752Z/` |
| 5 | `swarm_runs/model-grill/20260519T205851Z/` |

Log: `reports/_cloud5_rounds_log.txt`

---

## P0 next actions (merged with `MERGED_ACTION_PLAN_2026-05-19.md`)

1. `EMITTER_WHITELIST_ENFORCE=1` after 7d shadow metrics  
2. Pre-register **H-035** + Binance tick fetcher  
3. Wire Qwen r5 design: registry-driven mask in `ml_consensus/consensus.py`  
4. ETF premium arb probe (Ring idea) — harness only, paper track  
5. Operator: resolver GHA backfill (desktop MySQL blocked)

**Do not:** promote registry PF to live; re-run killed families; trust Mercury “money-ready Y” without harness.
