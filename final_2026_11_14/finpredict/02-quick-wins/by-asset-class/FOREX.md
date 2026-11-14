# FOREX — quick wins

## 1. Purge the 11 frozen "phantom" closed rows (M / H)
- **Problem:** 11 closed FOREX rows (pnl 0.0, `exit_reason=UNKNOWN`, `exit_price==entry_price`, Mar 2026) survive the validity filter. `_is_valid_resolved_pick()` does not reject them: `pnl==0` passes (:4867), `exit==entry` passes (:4903), `exit_reason=UNKNOWN` only dropped (:4942) when no close-marker — these have one.
- **Fix:** Quarantine (not delete): add a validity clause to `_is_valid_resolved_pick()` that excludes rows where `exit_reason in ("", "UNKNOWN") AND pnl_pct==0 AND exit_price==entry_price` for non-crypto — mark them `VOID`/phantom and retain them for audit. No hard delete.
- **Targets:** `audit_trail/dashboard_generator.py` `_is_valid_resolved_pick()` (:4850) or pre-pass in `_build_recent_closed_picks()` (:6948); resolve-vs-purge in `alpha_engine/outcome_resolver.py` (:1180/:2660).
- **Caution:** do NOT wire `alpha_engine/forced_resolution.py` (research-only, survivorship-bias warning).
- **Verify:** `recent_closed` FOREX count drops by 11; no `UNKNOWN + pnl 0 + exit==entry` rows remain.

## 2. Refresh-or-drop the stale `stock_forex_prices.json` fallback (M / M–H)
- **Problem:** `stock_forex_prices.json` (deployed copy 217d stale) is consumed as fallback with no freshness check → FX active picks resolve `current==entry`.
- **Fix:** In `_fetch_yfinance_price()` parse `updated_at` and skip the file fallback when >24h; apply the same age-guard to other consumers; ensure the fresh file ships with the data glob.
- **Targets:** `alpha_engine/outcome_resolver.py:413` (fallback :424–437); `alpha_engine/production_scanner.py:2362` (write :2538); `continuous_improvement_monitor.py:392`; `multi_asset_test_portfolios.py:105`.
- **Verify:** fake `updated_at` >24h → resolver ignores file, returns live yfinance (or `None`), not stale price.

## 3. Tighten FOREX consensus threshold (S / L–M)
- **Problem:** `_min_agreement_for_pick()` returns `1` for FOREX → single-source signals pass "consensus".
- **Fix:** raise FOREX min agreement to 2, or require non-empty `current_price` before emitting a FOREX consensus pick.
- **Targets:** `copy_trader_intel/non_crypto_consensus.py:134` (`_min_agreement_for_pick`) / `:150` (`consensus_vote`).
- **Verify:** rerun `run_consensus()` → FOREX count reflects multi-source only.
