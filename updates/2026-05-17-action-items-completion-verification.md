# Action-Items Completion + Verification — 2026-05-17

**Goal session:** `action-items-20260517` (claude-desktop, Claude Opus 4.7)
Completing/verifying the action items captured from the arena.ai audit + swarm review.

## Status table

| # | Item | Status | Evidence |
|---|------|--------|----------|
| a | −0.91 corr: synthetic `seed=42` data in `comprehensive_backtest.py` | ✅ **FIXED** | `_try_load_real_klines` added; `load_or_generate_data` now fetches real OHLCV via the Binance-failover chain first, synthetic only as fallback. Verified: BTC loads 92 real bars (last close ~$81k); SPY falls back to synthetic. Commit `42597be0a9a`. |
| b | ATR dynamic TP/SL helper | ✅ **ALREADY DONE** | `alpha_engine/adaptive_tp_sl.py` (952 lines) already implements ATR-based per-symbol/per-strategy TP/SL and is wired into `production_scanner.py`. The swarm's "regime-adaptive ratios" extra was explicitly flagged as overfit — intentionally NOT added. |
| c | EQUITY emission gap | ◐ **ROOT-CAUSED, no safe quick fix** | See below. |
| d | YM=F mislabeled `asset_class=EQUITY` | ✅ **FIXED** | `futures_strategies.py` now stamps `asset_class="FUTURES"` on all 4 pick-dict sites. Commit `33690a66afc`. Stale `active_picks.json` entry self-heals on next hourly regen. |
| e | `tv-account-switch` stale selector | ✅ **FIXED** | Hash-agnostic `div[class*="middle-"][class*="hasTitle-"]` selector + pointer-event open in `tv-account-switch` + `tv-paper-trade`. Commit `e47ecd6cd04`. |
| f | Verify PFE limit-order fill | ⏳ **TIME-BLOCKED** | Equity market closed (weekend). Resting limit `Buy 120 PFE @ 24.85` — verify after Monday 14:30 UTC open. |
| g | Do not push grok contaminated branch | ✅ **DONE** | `feature/forex-edge-gates-swarm-v2-2026-05-17` left unpushed; warning logged in `CLAUDETOGROK.MD`. |

## Item (c) — EQUITY emission gap, root cause

The weekly filter reported "EQUITY: 0 qualifying picks (elite_score≥60)". Investigated
`alpha_engine/data/active_picks.json` (n=66, post-regen):

- **10 EQUITY picks live** — not zero. But every one scores low:
  - `YM=F` elite 57 — actually an index *future* (`futures_connors_rsi2`), mislabeled
    EQUITY; fixed by item (d), self-heals next regen.
  - `JNJ` elite 29 (`smart_money_accumulation`).
  - 7× `stocks_rsi2_pullback` (GOOGL/AMZN/TSLA/PFE/MRK/LLY/RIOT) — **all at an
    identical flat elite_score of 20.8**.
- **0 reach elite_score ≥ 60.**

Root cause (two parts, neither a one-line fix):
1. **elite_score systematically under-credits equity picks.** Seven distinct
   `stocks_rsi2_pullback` setups collapsing to the *same* 20.8 score indicates the
   scorer is hitting a floor / missing equity-specific features (cf. the null-features
   pattern in `project_ml_null_features_crisis`).
2. **Strategy mismatch.** The historical EQUITY edge (resolved PF 1.65 / WR 53.2 /
   n=393) came from `multi_asset_copytrader` + `aggregated_picks` — which currently
   emit CRYPTO-heavy. The strategies emitting EQUITY *now* (`stocks_rsi2_pullback`,
   `smart_money_accumulation`) are not the ones that built the edge.

**Recommendation (scoped OUT of this goal loop — needs validation, not a rushed fix):**
audit the elite_score formula's equity branch for a missing-feature floor, and
check why `multi_asset_copytrader`/`aggregated_picks` stopped emitting EQUITY. Both
are scoring/pipeline changes that must be walk-forward validated before shipping —
not safe as a blind goal-turn edit.

## Summary

5 of 7 items closed (a, b, d, e, g). (f) is time-blocked until Monday. (c) is
root-caused with a concrete recommendation but its fix is a validated scoring change
deliberately not rushed.
