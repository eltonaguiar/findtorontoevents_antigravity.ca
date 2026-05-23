# Double-check synthesis — 2026-05-19

Cross-review of prior harvests + R1/R2/R3 grill runs.

## Sources merged

- `reports/IDEA_HARVEST_SYNTHESIS_2026-05-19.md`
- `reports/MERGED_ACTION_PLAN_2026-05-19.md`
- `reports/QUANT_RESCUE_SWARM_VERDICT_2026-05-19_cursor.md`
- `swarm_runs/model-grill/20260519T*/` manifests

## R1 — Gap analysis (consensus)

| Gap | Action |
|-----|--------|
| Dashboard tiles ≠ `pf_registry` canonical | Wire tiles + red banner on mismatch |
| Confidence >1.0 on CRYPTO rows | Clamp at ingestion |
| Dedup before `at_raw_picks` | 5-min bucket / dedup_hash |
| Harness reads 1/32 ledger files | Widen `edge_stability_harness.py` scope |
| No intraday pre-registered family | H-035 tick probe (Binance 1m) |

## Contradictions — REJECT

| Claim | Source | Verdict |
|-------|--------|---------|
| EQUITY/ETF/BOND live money-ready today | Mercury-2, Pollinations, OpenRouter free | **REJECT** — 11/11 daily causal kill; registry PF ≠ harness |
| OpenRouter free "all classes ready" | Wave-1 harvest | **REJECT** |
| Meta-labeling on daily noise | Generic local LLMs | **REJECT** for new families |

## Net-new ideas (not in top-3 harvest list)

1. **`HARNESS_LEDGER_CI`** — `tools/build_pf_registry.py` → sha256 in CI; dashboard 404 fix for `pf_registry.json` on live `/audit`
2. **`INTRADAY_SCHEMA_SIDE_TABLE`** — parquet 1m OHLCV + aggTrade; no backfill into sample
3. **`RESOLVE_TS_GT_EMISSION_AUDIT`** — SQL audit query in NEXT_MOVES tier 1

## Week-1 sequence (7 bullets)

1. Emitter whitelist + toxic kill switch (P0)
2. Confidence clamp + dedup guard
3. Dashboard → canonical registry only
4. Halt FUTURES emitter
5. Pre-register H-035 intraday hypothesis
6. Binance tick fetcher (paper table only)
7. Forward-track `mega_mutation` — forward harness is verdict

## R2/R3 model outputs

- **DeepSeek (R2 methodology):** Funnel emitter→resolver→harness; intraday-only new family — **aligned**
- **Ring (R3 worst-strategy):** Mutations for quan_engine, cta_replicator, copytrader — **useful** if pre-registered

## Remaining action items

| Priority | Item | Owner |
|----------|------|-------|
| P0 | Wire whitelist in `ml_consensus` + `forward_validator` | Engineering |
| P1 | Fix local grill: Ollama HTTP API path | Tooling |
| P1 | Re-probe Cerebras/Groq (403 from roster HTTP; api_consult may still work) | Ops |
| P2 | Ring on MASTER prompt + score vs DeepSeek | Research |
| P2 | HF/Chutes credits or drop from roster | Ops |
