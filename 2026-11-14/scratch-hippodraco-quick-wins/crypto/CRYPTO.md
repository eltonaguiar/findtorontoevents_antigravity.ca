# CRYPTO Quick Wins
Audit: §4.1 — recent_closed PF 0.81 (n=1,966), intrabar PF 0.92 / WR 35.9% (n=3,705) **NOT_READY**; CRYPTO is 44,480 of 50,735 `at_signal_outcomes` rows and carries the worst zombie load. Headline: stop quoting crypto edge until QW-CRYPTO-1..3 land.

## QW-CRYPTO-1 · Drain crypto zombies first (S–M)
- **Problem:** `active_raw` CRYPTO median age ~89d in prior audits (2,055h all-class here); hundreds of EXPIRED `BTCUSDT/XRPUSDT/NEARUSDT` (inverse mutations since 2026-07-13) with `pnl=0, current_price=None`; NEARUSDT SHORT stored −99.0 vs recomputed −146.2 (cap artefact).
- **Fix:** Run QW-ALL-4 drain scoped to CRYPTO first (largest, stalest cohort): tombstone `pnl_pct=NULL`, never 0. Cap display PnL at −99 and show `pnl_capped:true` where applied instead of silent −99.0.
- **Verify:** CRYPTO OPEN count and `active_raw` median age collapse; no EXPIRED in active arrays (contract test c).

## QW-CRYPTO-2 · Unit-fix the crypto outcomes ledger (M, part of QW-ALL-2)
- **Problem:** CRYPTO mismatch rows dominate the 5,400 (e.g. ETHUSDT fraction-style prints mixed with percent prints); CRYPTO max |pnl| 18,611%.
- **Fix:** Per-class guarded backfill (recompute from entry/exit) for CRYPTO first; reject >+500/−99 at write (QW-ALL-3).
- **Verify:** Post-backfill CRYPTO recomputed PF moves from published 0.93 toward the honest window figure; publish the delta in the fix doc — expect it to get worse, that's the truth arriving.

## QW-CRYPTO-3 · Retire the placeholder LightGBM SHORT machine (S)
- **Problem:** `lightgbm_ensemble.py:5-14,119,224-225,244,285-286` — never trained, predictions are zeros, zero defaults to SHORT. Any path consuming it emits SHORT bias on no evidence.
- **Fix:** Either train it properly (out of quick-win scope) or hard-disable: return `NO_SIGNAL` on untrained state and add a startup assert that a fitted model file exists before the ensemble can emit. Grep consumers and gate them.
- **Verify:** Unit test: untrained ensemble emits no direction; no SHORT originates from a zero prediction.

## QW-CRYPTO-4 · Claude Gainer lookahead + synthetic fallback (M)
- **Problem:** `claude_gainer_ml/train_model.py:562-564,629-667` uses today's ATH/mcap/sector momentum as features for historical days; `:1080-1086` trains on synthetic pump data on API failure and saves as production.
- **Fix (quick subset):** Fail-closed — on API failure, abort training (no save). Point-in-time feature fix is the follow-up (not quick). Until then stamp the model card `lookahead_suspect:true` and exclude its score from smart-pick gating (it currently shows `status:active`, cv_auc 0.6877 from May).
- **Verify:** Simulated API failure produces no new model file; payload no longer presents it as clean active.

## QW-CRYPTO-5 · TP-before-SL honesty for crypto exits (M)
- **Problem:** Same-bar TP+SL records TP first (`alpha_engine/forward_validator.py:1281-1302`; `crypto_gainer_ml/live_predictor.py:908-924`) — inflates crypto WR where 1h/15m bars span both levels.
- **Fix:** Where intrabar path is unresolvable mark `intrabar_ambiguous` (column already exists in `trading_picks`) and exclude ambiguous rows from headline WR/PF (report separately).
- **Verify:** Ambiguous share published per class; headline WR recomputed without them.

## QW-CRYPTO-1b · Root-caused: `forward_validator.py:1375-1384` writes fraction (subagent-verified)
The unit mix is not random: `alpha_engine/forward_validator.py:1375-1384` computes `pnl_pct` as a raw fraction rounded 6dp, while the resolver writes percent (`universal_pick_resolver.py:286-306`). Fix at the emitter: align the validator to percent (or write `pnl_unit` explicitly), backfill by recompute-from-prices with dry-run + `pnl_pct_pre_backfill` snapshot, **then** delete the generator ×100 guess (`dashboard_generator.py:8065-8072`). Verify: CRYPTO mismatch count → 0; PF 0.81-vs-0.93 gap becomes explainable (window vs ledger). Effort M (8–12h, shared with FOREX).

## QW-CRYPTO-3b · Gatekeeper leakage ON by default (subagent)
Flip `_drop_leakage_enabled()` (`ml_gatekeeper/gatekeeper.py:95-97`) so `_LEAKAGE_FEATURE_INDICES=(5,6,19,30)` mask by default (opt-out `ML_GATE_DROP_LEAKAGE=0`); chronological-sort before TimeSeriesSplit (`:230-253`); retrain and publish the honest AUC (expect a drop from the 0.571 fold-1 baseline — that drop is the point). Verify: leakage importances zero in the new bundle.

## QW-CRYPTO-4b · Walkforward stale-flag, don't re-run the broken one (subagent)
Extend `_compute_data_freshness()` (`dashboard_generator.py:3187-3227`) to check the walkforward artifact age (>30d → `walkforward_stale:true` + STALE badge). Explicitly do **not** "refresh" by re-running the current overlapping-fold validator — a fresher wrong number is worse than a flagged stale one.

## Status update (2026-11-14 ~18:00Z peer-merge)
- **QW-CRYPTO-3b IMPLEMENTED by finpredict-v3** (commit `d8c8dd25581`, leakage default-on + 4 tests) — reported as now on `origin/main`; verify ancestry + coordinator sign-off (production change shipped during a read-only audit). Retrain/honest-AUC publication still open.
- **Adopted from finpredict-v4:** AI-Challenge zombie registry (5 picks OPEN since 2026-03-15, NEAR SHORT +143% through SL) as a third zombie store beyond MySQL/`active_raw`; RSI5070 shadow condition n=430 net PF 1.113 CI-lb 0.916 → explicitly not promotable; live-Binance check showed dashboard understates all 3 SHORT PnLs (NEAR +2.74 claimed vs +3.46 live) because prices freeze at entry — reinforces QW-ALL-7.
- **Rejected:** v4 crypto QUICK_WINS destructive mass-EXPIRED writes and "invert ML confidence" (numbers in no evidence file).

## Peer addendum (flaxen-hair CR-1/CR-3, verified files exist)
- `coinglass_strategies/` has 13 OPEN positions, max opened 2026-11-06, vs `MAX_HOLD_HOURS=48` (`coinglass_strategies/config.py:69`); `monitor_positions()` only runs from `cmd_portfolio()` (`scanner.py:38`). Quick win: call expiry on every scan; on Binance-451 price failure mark `price_unavailable` instead of skipping resolution forever. Adopt flaxen's expiry **with pnl NULL**, not their `pnl_pct=0` snippet.
- `INSERT OR IGNORE` on `signal_id` silently drops dupes (`coinglass_strategies/ratio_store.py`) — log skipped inserts; add uuid suffix (QW-ALL also).
- `quantum_fusion_crypto_engine.py` is mock/simulated — label it in docs, exclude from any performance surface.
