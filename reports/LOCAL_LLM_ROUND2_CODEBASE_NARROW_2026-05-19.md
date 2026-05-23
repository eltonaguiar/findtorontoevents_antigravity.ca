# Local LLM round 2 — codebase / DB / GHA narrowing (2026-05-19)

**Prompt:** `docs/swarm_prompts/CODEBASE_NARROW_v1.md`  
**Runs:** `swarm_runs/model-grill/20260519T204627Z/` (5 locals), `20260519T205019Z/` (32B), `20260519T205415Z/` (Grok)  
**Hardware:** RTX 5070 12GB · 32GB RAM · Ollama HTTP `num_predict≥900`, `num_ctx` 4096 (14B) / 2048 (32B/MoE)

---

## Model scorecard (this round)

| Model | Elapsed | OK | Intel (1–5) | Notes |
|-------|---------|-----|-------------|-------|
| **mistral-nemo:latest** | 14s | Y | 4 | Fast; some generic funnel names |
| **qwen2.5-coder:14b-instruct-q4_K_M** | 22s | Y | 4 | Best repo-shaped tables (verify paths!) |
| **deepseek-r1:32b** | 225s | Y | 4 | Slow hybrid; good strategy/backtest matrix |
| **qwen3:14b** | 20s | Y | 3 | Solid CRYPTO block; partial output |
| **deepseek-r1:14b** | 22s | Y | 3 | Reasoning style; hallucinated `daily_*.yml` |
| **mixtral:8x7b** | 99s | Y | 1 | Short; invented `*_scanner.py` names |
| **grok-3-latest** (cloud) | 17s | Y | 3 | Right *themes*; several fake workflow filenames |
| **qwen3:8b** (new pull) | 8s | N | 0 | **Empty body** — same class of bug as `qwen3.5:9b` |

**Recommendation for next local batch:** `mistral-nemo` (breadth) → `qwen2.5-coder:14b` or `qwen3:14b` (depth) → `deepseek-r1:32b` overnight batch only.

---

## Verified repo map (use this — not model hallucinations)

Models often invent `crypto_pick_pipeline.yml` / `equity_forward.yml`. **Real** spine:

### MySQL

| DB | Tables / use |
|----|----------------|
| `ejaguiar1_stocks` | `at_raw_picks`, resolver outcomes, active pick sync |
| `ejaguiar1_backtests` | Strategy runs, DNA/mutation backtests, incubator results |

### GitHub Actions (per-class touchpoints)

| Class | Workflows (verified paths) |
|-------|---------------------------|
| **All** | `.github/workflows/audit-dashboard.yml` (resolver, `pf_registry`, deploy `/audit`) |
| **All** | `.github/workflows/money-ready-registry-gate.yml`, `walkforward-gate.yml` |
| **CRYPTO** | `mercury2-scan.yml`, `crypto-ml-edge.yml`, `dynamic-alpha-engine.yml`, `incubator-strategies.yml` |
| **CRYPTO** | `genome-daily-pipeline.yml`, `dna_strategy_pipeline.yml`, `baby-strat-forward-paper.yml` |
| **EQUITY** | `growth-stock-screener-daily.yml`, `momentum-tracker.yml`, `swing_screener_daily.yml` |
| **ETF/BOND** | `etf-bond-scanner.yml` |
| **COMMODITY** | `incubator-strategies.yml`, commodity paths in `audit-dashboard` env blocks |
| **FOREX** | Shadow/rescue env in `audit-dashboard.yml` (see `FOREX_RESCUE_*` reports) |
| **Ops** | `asset-class-freshness-watchdog.yml`, `cross-db-audit.yml`, `resolver-step5-6-backfill.yml` |

**Narrowing lever (all classes):** reduce **emitter volume** at source (`alpha_engine/*`, `mercury2/`, `copy_trader_intel/`) + **whitelist** (`emitter_whitelist.py`) — not new fictional per-class YAML.

---

## Consensus: strategy / backtest / mutation / APIs

| Question | Verdict | Evidence |
|----------|---------|----------|
| **New strategies?** | **No** (daily-bar); **one** CRYPTO intraday probe only | 11/11 killed; H-035 |
| **More backtesting?** | **Yes** — targeted | `ejaguiar1_backtests`, `tools/edge_stability_harness.py`, incubator/genome workflows |
| **Better backtesting?** | **Yes** — P0 | Walk-forward, costs, leakage, scale-mismatch backfill (T1-04) |
| **DNA mutation?** | **Pause** class-wide | `tools/mutation_analysis.py` only after toxic pairs blocked; mutate-before-kill for FOREX |
| **More free APIs?** | **Minimal** | Binance aggTrade/1m for H-035; Odds API sports separate (Goal #2) |

---

## Per asset class — actionable narrowing

### CRYPTO
- **Stop:** `quan_engine` emissions, killed daily families, volume without whitelist.
- **Keep:** `mercury2-scan`, elite seeds (`crypto_rsi_whaleconfirmed_v1`), forward paper tracks in `audit-dashboard`.
- **Backtest:** incubator + genome pipelines; widen harness ledger (T1-05).
- **New edge:** **H-035** tick imbalance — `tools/` Binance fetcher + pre-register in `hypothesis_registry.json`.

### EQUITY
- **Stop:** new daily-bar hypotheses (M-107 freeze T2-05); low-n momentum noise.
- **Keep:** shadow floors (`EQUITY_SHADOW_FLOOR_50`), `top_n_rank_backtest.py` replay in audit-dashboard.
- **Backtest:** more **forward** samples, not new scanners — n→100 clean.
- **Mutation:** H-032 / E1 liquidity-shock only after harness pre-register.

### COMMODITY
- **Stop:** `cta_replicator` on COMMODITY (toxic).
- **Keep:** `multi_asset_cot`, copytrader whitelist slices; incubator commodity arms.
- **Backtest:** seasonality H-031 via harness, not live promotion.

### ETF / BOND
- **Stop:** broad emission until n≥100; use `etf-bond-scanner` outputs for paper only.
- **Keep:** `etf-bond-scanner.yml` + registry reads.

### FOREX
- **Stop:** `multi_asset_copytrader`; daily-bar rescue without mutation protocol.
- **Keep:** `cta_replicator` slice (paper); shadow rescue paths in audit-dashboard env.
- **Mutation:** required before kill — `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

### FUTURES
- **Stop:** new picks (T2-04 halt) until coverage panel green.

---

## Repo-grounded ideas (merged, all models)

| ID | wire_target | acceptance_test (60d) |
|----|-------------|------------------------|
| `EMITTER_WHITELIST_ENFORCE` | `alpha_engine/emitter_whitelist.py` | 0 new picks from toxic pairs after enforce=1 |
| `H035_BINANCE_INTRADAY` | new `tools/binance_aggtrade_fetcher.py` + registry | Harness pre-reg + paper track n≥30 |
| `HARNESS_LEDGER_WIDEN` | `tools/edge_stability_harness.py` | ensemble/st_fear_greed cohorts visible |
| `AUDIT_DASHBOARD_CANONICAL_PF` | `audit_trail/dashboard_generator.py` | Tile PF within 0.15 of `pf_registry` |
| `GHA_RESOLVER_BACKFILL` | `resolver-step5-6-backfill.yml` | Operator dry-run then APPLY (desktop MySQL blocked) |
| `FOREX_MUTATION_GATE` | `tools/mutation_analysis.py` + docs | Deep-dive report before any FOREX kill |

---

## Fresh models tried / skipped

| Model | Action | Result |
|-------|--------|--------|
| `qwen3:8b` | `ollama pull` + narrow | Pulled OK; **empty generate** — do not use for harvest |
| `qwen3:14b`, `deepseek-r1:14b`, `mistral-nemo` | Already installed | **Best interactive stack** |
| `deepseek-r1:32b` | narrow @ ctx 2048 | **Works** ~225s, intel=4 |
| `mixtral:8x7b` | narrow | OK but shallow (intel=1) |
| `gemma3:27b` | Not pulled | ~17GB Q4 — marginal vs 14B on 12GB VRAM |
| Cloud `grok-3` | narrow | Fast sanity check; verify paths against table above |

---

## Commands

```powershell
cd e:\findtorontoevents_antigravity.ca
python tools/model_grill_sequential.py --wave local_variety --prompt narrow
python tools/model_grill_sequential.py --job ollama:deepseek-r1:32b --prompt narrow
python tools/borderline_model_lab.py   # VRAM matrix
```

**Outputs:** `swarm_runs/model-grill/20260519T204627Z/manifest.json`
