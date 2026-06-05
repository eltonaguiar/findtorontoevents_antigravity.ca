# Grok MASTERPLAN Phase 2 — Shipped 2026-06-05

## Non-LLM feature signals

- Package: `tools/feature_signals/` (`orchestrator.py`)
- Emitters: funding rate extremes (Binance), VIX regime overlay (ETF), commodity 20d momentum (CL=F, NG=F)
- Output: `audit_dashboard/data/feature_signals_latest.json`
- **Wired:** `alpha_engine/production_scanner.py` merges via `merge_feature_signals()` when `FEATURE_SIGNALS_ENABLED=1` (default ON)
- CI: `.github/workflows/feature-signals-hourly.yml` (hourly refresh + commit)

## Clean ingest enforcement (opt-in)

- `alpha_engine/mysql_trading_sync.py` skips rows when `CLEAN_INGEST_V2_ENFORCE=1`
- Default OFF until parity audit at n=1000

## Tournament freeze

- `ai-tournament-pipeline.yml` job gated on repo variable `AI_TOURNAMENT_PIPELINE_ENABLED=true` (default skip)
- GitHub API: workflow already disabled on remote

## Tier-2 ladder in phase3 report

- `tools/phase3_promotion_readiness.py` adds `tier2_luxalgo_confluence` via `evaluate_forward_tier2()`

## Verify

```bash
python3 -m tools.feature_signals.orchestrator
python3 -m py_compile tools/feature_signals/orchestrator.py
python3 tools/phase3_promotion_readiness.py
```

## Operator

- Enable tournament only with `gh variable set AI_TOURNAMENT_PIPELINE_ENABLED true` after forward proof
- Turn on DB clean ingest: `CLEAN_INGEST_V2_ENFORCE=1` on mysql sync job after backup + parity