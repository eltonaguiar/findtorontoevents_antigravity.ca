# INVERSE_ML BTC 15m sleeve mode — forward n→100 fast path

**Date:** 2026-06-06

## Goal

Grow `inverse_ml_enhanced_BTCUSDT_15m_D` forward decisive closes from ~52 to **n≥100** without enabling real-money sizing.

## Enable sleeve-only CRYPTO mode

```bash
export INVERSE_ML_BTC_15M_ENABLED=1
```

When set:

| Layer | Behavior |
|-------|----------|
| `passes_active_gate()` | Blocks all CRYPTO picks except `inverse_ml_enhanced_BTCUSDT_15m_D` and `inverse_ml_enhanced_ADAUSDT_15m_D` |
| `mysql_trading_sync.py` | Suppresses non-sleeve CRYPTO rows before `trading_picks` upsert |
| Non-CRYPTO classes | Unchanged |

Disable: `INVERSE_ML_BTC_15M_ENABLED=0` (default).

## Wiring shipped

1. `passes_inverse_ml_sleeve_gate` wired in `audit_trail/quality_gates.py::passes_active_gate`
2. `alpha_engine/data/ml_reviver_picks.json` registered in `JSON_PICK_SOURCES` + `SYSTEM_SOURCES` (resolver TP/SL/TIME_EXIT)
3. `category=CRYPTO` + `asset_class=CRYPTO` on ml_reviver picks (merger + integrator + emitter)
4. GHA `ml-strategy-reviver.yml` merger fixed (`alpha_engine/ml_reviver_merger.py`, was writing to wrong `data/` path)
5. `tools/inverse_ml_forward_fastpath.py` — status + backfill commands

## Close picks faster

1. **Backfill NULL pnl** (recovers decisive n from already-closed rows):

```bash
python3 tools/backfill_resolved_pnl.py --dry-run --strategy inverse_ml_enhanced_BTCUSDT_15m_D
python3 tools/backfill_resolved_pnl.py --apply --strategy inverse_ml_enhanced_BTCUSDT_15m_D
```

2. **Emit + resolve loop** (every 2h via `ml-strategy-reviver.yml` + universal resolver):

```bash
python alpha_engine/ml_strategy_reviver.py
python alpha_engine/ml_reviver_merger.py
python audit_trail/universal_pick_resolver.py   # or GHA resolver workflow
INVERSE_ML_BTC_15M_ENABLED=1 python alpha_engine/mysql_trading_sync.py
```

3. **Paper pilot** (virtual forward, does not count toward DB n):

```bash
python3 verified_strategies/paper_pilot/inverse_ml_btc_forward_pilot.py
```

## Verify

```bash
python3 tools/inverse_ml_forward_fastpath.py --strategy inverse_ml_enhanced_BTCUSDT_15m_D
python3 tools/bootstrap_forward_stats.py --write
python3 tools/forward_n100_tracker.py
pytest tests/test_asset_class.py tests/test_emitter_whitelist.py -q
```

## Estimated closes needed

- Target: **100** decisive closes (`pnl_pct` non-null, non-zero)
- Current (2026-06-06): **~52** resolved rows, **~51** with NULL/zero pnl → backfill can surface ~50 decisive immediately
- **~48–50** new live closes still required after backfill (at ~2–4 closes/day → ~12–25 days)

## Production safety

- `production_enable: false` on paper pilots
- `money_ready_verdict.json` `freeze_promotions` still governs capital
- Sleeve flag is **admission + sync filter only** — not a sizing override