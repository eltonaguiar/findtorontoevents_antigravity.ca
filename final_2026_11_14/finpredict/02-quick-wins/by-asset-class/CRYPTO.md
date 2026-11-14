# CRYPTO — quick wins

## 1. Wire live Binance mirror-failover into the dashboard fetch (S / H)
- **Problem:** `_fetch_prices_with_failover()` only tries geo-blocked endpoints, so the fetch fails and `current_price == entry_price` survives (83% frozen).
- **Fix:** Prepend `alpha_engine.universal_price_enricher._fetch_all_binance_prices()` (iterates `BINANCE_SPOT_MIRRORS`) to the fetcher and merge results; falls through on failure.
- **Targets:** `audit_trail/dashboard_generator.py:1179`; reuse `alpha_engine/universal_price_enricher.py:172` + `:52`.
- **Verify:** rebuild → frozen-at-0% crypto fraction drops from ~83% toward single digits.

## 2. Stop coercing `None` entry → `0.0` (S / H)
- **Problem:** `merge_into_active_picks()` does `entry_price = get("entry_price") or 0`, producing `XRPUSDT SHORT entry=0.0` garbage.
- **Fix:** Leave `entry_price` as `None`, keep `status == "SIGNAL"` when no real entry; `_snapshot_prediction_market_entry()` backfills from live quote.
- **Targets:** `alpha_engine/prediction_market_consensus.py:589` (+ `:478`, `:489`).
- **Verify:** `grep -c '"entry_price": 0'` → 0.

## 3. Entry-price sanity gate (S / H)
- **Problem:** `BTCUSDT entry=0.3322`/`1.334` pass because the gate only rejects `<=0` and `>1M`.
- **Fix:** In `passes_active_gate()`, add a CRYPTO band check (entry must be within 0.5×–2× the symbol's known Binance price); emit `_entry_reason`.
- **Targets:** `audit_trail/quality_gates.py:9082` (entry block in `passes_active_gate` @ `:6739`); `MAX_ENTRY_PRICE` @ `:2375`.
- **Verify:** known garbage rows return `False` with reason.

## 4. Label unquoted rows (don't show 0% as "live") (S / H)
- **Problem:** No-quote picks keep `current==entry` and render as 0% — indistinguishable from flat.
- **Fix:** In `_enrich_live_pnl()` "no quote" branch stamp `_unquoted=True`, `pnl_pct=None`; `_pick_pnl_pct()` returns `None` when `current==entry` and no quote.
- **Targets:** `audit_trail/dashboard_generator.py:1753` (branch in `_enrich_live_pnl` @ `:1618`); `:481` (`_pick_pnl_pct`).
- **Verify:** offline build → `_unquoted` set, `pnl_pct is None`; big-mover rollup stops counting them as 0%.

## 5. Kalshi refresh-or-drop + stop `entry_price: 0` (M / M)
- **Problem:** `kalshi_signal_agent` hardcodes `entry_price: 0`; snapshot ~7 months stale; 4 picks frozen.
- **Fix:** (a) change `entry_price: 0` → `None` in the agent signal dict; (b) exclude `kalshi_signal_agent` rows older than ~7d in the gate; use `alpha_engine.kalshi_signals.generate_kalshi_picks()` (fetches real entry via `_fetch_price`).
- **Targets:** `prediction_market_agents/kalshi_signal_agent.py:489`; `alpha_engine/kalshi_signals.py:621/:650`; `audit_trail/quality_gates.py:6739`.
- **Verify:** re-run `scan_kalshi()` → entry is `null`; stale rows excluded.

## 6. Detect & exclude the flat-3% placeholder cohort (M / M)
- **Problem:** `signal_validation` (117), `macd_rsi_confluence` (138), `meanreversionbb` (111) + siblings: every win exactly 3.00%, zero losers = fallback TP stamped as realized PnL.
- **Fix:** Add placeholder-P/L detector at closed-pick ingest: when a strategy's closed rows are all `pnl_pct == fallback_TP` with 100% WR and no `exit_price`, stamp `_placeholder_stats=True` and exclude from WR/PF rollups.
- **Targets:** `dashboard_generator.py:7516` (`_coerce_closed_zero_pnl_from_outcome`), normalization `:8040–8081`, fallback TP `:8102`; blocklist seam `alpha_engine/strategy_blocklist.py:270–292`.
- **Verify:** the three cohorts stop reporting 100% WR / +3.00% flat.
- **Note:** the 3% value is *indirect* (via `_ac_defaults` fallback TP) — key the detector on "all wins == fallback TP%", not a magic `3.0`.

## 7. Flag the forward-scanner seeded batch as "unpriced seed" (S / M)
- **Problem:** 127 OPEN picks seeded 2026-11-12 12:15–12:19 are 96.9% frozen.
- **Fix:** At ingest of `forward_signal_scanner.py` picks, stamp `_seeded_at` + `_unquoted=True` until first successful price refresh (via QW-1).
- **Targets:** `incubator/backtest_team/forward_signal_scanner.py`; flag consumed by `dashboard_generator.py:1618`.
- **Verify:** with Binance reachable, the 127 picks get `current != entry` and clear the flag.
