# Asset-class performance hardening (audit + Hyrotrader) — 2026-04-22

## What was broken

1. **`config/hc_gate_params.json` drifted** from `audit_dashboard/hc_filter.js` / `tools/dashboard_hc_rules.py`: missing per-asset-class forward WR and score floors, retired `ai_challenge_*` entries, and incomplete `signalGroups`. Deployed `/audit` fetches partial JSON; without a full file, overrides did not match the documented Mercury2 HC contract.

2. **`pnl_pct` ingest** used a flat ±100% cap in `_normalize_pick`, which was appropriate for catching bad equity labels but **flattened legitimate crypto tails**. Forex/equity rows could still show absurd percentages when upstream data was corrupt; resolver used ±500% without asset-aware semantics.

3. **`quan_engine_scalp`** remained publishable on new symbols despite symbol-pair blocks and RCA evidence of class-wide negative edge.

4. **Hyrotrader enhanced scoring** used one RSI ladder for all assets; ML blend treated cross-strategy fuzzy matches like exact matches.

## What we changed

| Area | Change |
|------|--------|
| HC config | Rewrote [`config/hc_gate_params.json`](config/hc_gate_params.json) as the full superset (per-class WR/score floors, `forexRelaxedWRMinPct`, updated `signalGroups` / `corrPairs`, `_doc` pointer). |
| PnL sanity | New [`audit_trail/pnl_ingest_sanity.py`](audit_trail/pnl_ingest_sanity.py): crypto `[-99, 500]%`, non-crypto `[-100, 200]%`. Applied in [`audit_trail/dashboard_generator.py`](audit_trail/dashboard_generator.py) (`_normalize_pick`) and [`audit_trail/universal_pick_resolver.py`](audit_trail/universal_pick_resolver.py). Clamped rows get `pnl_pct_ingest_clamped` + `pnl_pct_pre_clamp`. Removed redundant ±500 hard cap in resolver in favor of this module. |
| Upstream gate | Added `("CRYPTO", "quan_engine_scalp")` to `BLOCKED_ASSET_STRATEGY_PAIRS` in [`audit_trail/quality_gates.py`](audit_trail/quality_gates.py). |
| Hyrotrader | [`alpha_engine/hyrotrader_enhanced_scoring.py`](alpha_engine/hyrotrader_enhanced_scoring.py): RSI bands via `normalize_asset_class` (forex 28/72, crypto 30/68 long overbought penalty 7); ML blend **85/15** when cross-strategy match vs **70/30** exact. |

## Verification

- `python -m py_compile` on all touched `.py` files — **pass**
- `python tools/validate_dashboard_parity.py` — **exit 0** (existing tier/heuristic disagreements on historical rows unchanged in nature)
- `python tools/validate_hf_by_asset_class.py` — **exit 0**

## Rollback

- Revert `config/hc_gate_params.json` to prior partial file (restores old behavior; not recommended).
- Remove `quan_engine_scalp` row from `BLOCKED_ASSET_STRATEGY_PAIRS` if a rehabilitated variant is promoted with investigation docs per `TESTING_PROTOCOL.MD`.
