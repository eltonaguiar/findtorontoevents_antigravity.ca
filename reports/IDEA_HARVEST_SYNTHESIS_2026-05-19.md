# Idea harvest synthesis — 2026-05-19 (first API wave)

**Runs:** `swarm_runs/idea-harvest/20260519T063911Z/` — **11/19 API models OK**  
**Local batch:** in progress (`idea_harvest_mega.py --tier local`)

## Executive verdict (consensus: Grok, DeepSeek, Inception)

**No asset class is money-ready for live capital today.** The harvest is **emitter hygiene**, not new causal alpha.

| Class | Money-ready? | Best engines agree |
|-------|--------------|-------------------|
| CRYPTO | **No** | Toxic volume from `quan_engine`; seed strategies exist but class PF ~0.5 clean |
| EQUITY | **No** | n too small; halt until n≥50 @ PF≥1.3 |
| COMMODITY | **No** (closest) | Whitelist `multi_asset_cot` + `multi_asset_copytrader`; block `cta_replicator` on COMMODITY |
| ETF | **No** | No clean population in registry |
| FOREX | **No** | `cta_replicator` micro-slice OK; class aggregate still negative |
| BOND | **No** | Suspend emissions |

**Reject without harness:** OpenRouter free router claiming EQUITY/ETF/BOND “money-ready today” — registry PF ≠ admissible edge.

---

## Top harvest ideas (actionable, repo-grounded)

### 1. `EMITTER_WHITELIST_FROM_REGISTRY` (Grok — highest signal)

- **wire_target:** `ml_consensus/consensus.py`, `alpha_engine/forward_validator.py`, pick save path (`NOW.py` / `sync_all_picks_to_mysql.py`)
- **mechanism:** Only emit (asset_class, source_system) pairs with clean PF≥1.4, WR≥55%, n≥50 in `pf_registry`
- **acceptance_test:** 60d post-deploy: no (class, strategy) with n≥20 and PF<1.2; class aggregates PF≥1.35 on ≥150 new deduped closes

### 2. `TOXIC_STRATEGY_KILL_SWITCH` (Grok)

- **wire_target:** `tools/build_pf_registry.py` + writers for `quan_engine`, `cta_replicator`, `multi_asset_copytrader`
- **kill examples:** `quan_engine` on CRYPTO, `cta_replicator` on COMMODITY, `multi_asset_copytrader` on FOREX/EQUITY
- **acceptance_test:** After 200 closes, worst three pairs contribute <5% of n; class PF +0.4 vs baseline

### 3. `FAST_LOCAL_RULE_DISTILL` (Grok)

- **wire_target:** new `local_fast_filter.py` in hot path before ML/LLM scoring
- **acceptance_test:** 300 filtered closes: PF≥1.55, WR≥52%, n≥100; <5ms latency

### 4. DeepSeek per-class filters (register before backtest)

| id | Class | Change |
|----|-------|--------|
| `crypto_vol_filter_v1` | CRYPTO | Regime filter excluding high-vol 2022–23 |
| `equity_liquidity_momentum_v1` | EQUITY | ADV>$10M + 90d OOS |
| `forex_carry_trend_v1` | FOREX | Carry-adjusted Sharpe, no pair dominance |

---

## Models that ran successfully (API wave 1)

| Model | Time | Notes |
|-------|------|-------|
| grok-wsl-supergrok | 143s | **Best depth** — emitter whitelist |
| deepseek-chat | 17s | Brutal per-class + 3 harvest |
| xai-grok3 | 11s | Aligns paper-only |
| inception-mercury2 | 2s | Fast, data-layer first |
| openrouter/free | 18s | **Discard** money-ready Y on equity (false) |
| groq-llama33-70b | 1.4s | Generic paths — low signal |
| or-nemotron-nano-free | 12s | OK |
| pollinations | 16s | OK |
| sm-llm7 | — | OK |
| sm-mistral | — | OK |
| sm-mistral-codestral | — | OK |

**Failed:** Ring 2.6 (now paid on OpenRouter), several `:free` model IDs 404/400. **HF router:** 402 credits depleted.

---

## Next steps

1. Let **local Ollama sweep** finish → merges into `harvest_ideas.json`.
2. Fix OpenRouter model IDs (use `openrouter/free` or paid Ring if budget OK).
3. Pre-register top 3 ideas in `reports/hypothesis_registry.json` before any backtest.
4. Implement **#1 EMITTER_WHITELIST** as week-1 engineering (highest consensus).

**Repro:**
```powershell
python tools/idea_harvest_mega.py --tier api --no-pull --skip-import
python tools/idea_harvest_mega.py --tier local --no-pull --skip-import
```
