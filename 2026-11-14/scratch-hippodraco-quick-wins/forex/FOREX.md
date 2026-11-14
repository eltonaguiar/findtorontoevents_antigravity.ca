# FOREX Quick Wins
Audit: §4.1 — recent_closed PF 0.63, intrabar PF 0.66 / WR 32.2% (n=612) **NOT_READY**, worst liquid class; expectancy ≈ −0.34%/trade before costs. DB `trading_picks` FOREX is the single largest zombie category (43,056 OPEN).

## QW-FOREX-1 · Drain the FOREX zombie mountain (M, part of QW-ALL-4)
- **Problem:** 43k FOREX OPEN rows (oldest 2026-04-03) vs 379 closed in 30d. Any FOREX "active" stat is meaningless.
- **Fix:** Class-scoped drain after CRYPTO; FOREX max-hold is short (intraday/swing) so grace ×4 still clears nearly all of it.
- **Verify:** FOREX OPEN → hundreds, not tens of thousands; 30d closed:opened ratio published.

## QW-FOREX-2 · Costs will flip the sign — wire the cost model for FX first (M)
- **Problem:** No spread/swap/commission in forward PnL (`alpha_engine/forward_validator.py:1278-1279` only 5–10bp TP/SL slippage; `alpha_engine/cost_model.py:61-73` unused). At −0.34% expectancy, realistic FX costs (spread+swap on 1.5%/1% TP/SL geometry) decide whether any FX strategy is viable. `slippage_validation` already flags `forex_rsi2_mean_reversion` slippage = 48.5% of its PnL (CRITICAL).
- **Fix:** Quick subset: apply per-pair spread table + overnight swap for holds >24h in the resolver's closed-PnL path for FOREX only; republish `after_cost_net_per_trade` (field already exists on picks) as the headline FX expectancy.
- **Verify:** FX expectancy republished net-of-cost; strategies whose edge dies are auto-demoted by existing gates.

## QW-FOREX-3 · Stop the 6-letter = FOREX classifier trap (S)
- **Problem:** `alpha_engine/config.py:1127-1132` labels any 6-letter alpha string FOREX (and 1–5 letters EQUITY); explicit emitter `category` overrides symbol evidence (`asset_class.py:236-237`). Misclassified rows poison per-class PF.
- **Fix:** Require a known FX pair/currency-code check before the length heuristic; symbol evidence beats emitter category; log reclassifications. Unify on `alpha_engine/asset_class.py` (childlike-airport independently identifies it as canonical).
- **Verify:** Reclassification report count; no equity ticker lands in FOREX on the fixture set.

## QW-FOREX-4 · Fraction-unit rows are concentrated in FX (S, part of QW-ALL-2)
- **Problem:** FOREX outcomes are ~80% small-value (fraction-style) rows; the generator ×100 guess is most dangerous exactly here (genuine 0.05–0.09% trades).
- **Fix:** FX backfill strictly by recompute-from-prices guard; manual-review queue for rows without usable entry/exit. Do **not** use magnitude heuristics.
- **Verify:** Sampled FX rows (USDCHF audit case: stored 0.0088 vs calc 0.881) match after fix.

## QW-FOREX-6 · Subagent-refined fixes (verified file:line)
- **Root cause (shared with CRYPTO):** `forward_validator.py:1375-1384` writes fraction; align to percent + backfill + remove generator guess. Marginal cost ~4h if done with CRYPTO.
- **Price precision:** `audit_trail/fetch_stock_prices.py:23` rounds everything to 2dp — a ~40-pip error on EURUSD. Round by instrument: 5dp for `=X`/FX pairs (`asset_class.py:152-156` detection), 2dp otherwise. Verify: EURUSD stored at 5dp, hand-calc matches <0.01pp.
- **Costs (parameterised already):** `cost_model.py` has FOREX 1.5bp exec + 0.5bp slippage (`:18,34`, `get_total_bps :56-58`, `apply_costs :61-73`) — wire into `forward_validator.py:1374-1389` storing gross+net. Unit trap: `apply_costs` expects decimal — convert explicitly after the percent fix. Quarantine `forex_rsi2_mean_reversion` from live emission until cost-adjusted PF>1. Verify: 50-pick sample net == gross −0.02%.
- **Conflicting hold rules:** resolver FOREX max-hold 72h (`universal_pick_resolver.py:39-47`) vs validator `_NON_CRYPTO_MIN_HOLD["forex"]=2.0d` (`forward_validator.py:1328-1336`) — one pick, two fates. Unify on 72h with a CI test asserting the constants agree.
- **Benchmark:** `benchmark_closed_ledger.py:66-76` FOREX→SPY is meaningless; map FOREX→DXY (`DX-Y.NYB`) and make paired bootstrap direction-aware for SHORT ledgers (`:357,123-159`); extend `tests/test_benchmark_closed_ledger.py`. Also tag/exclude hardcoded XAU/XAG fallback prices (`dashboard_generator.py:1453-1464`).

## Status update (2026-11-14 ~18:00Z peer-merge)
- **PR#6 block is bypassed (finpredict-v4, adopted):** the 2 live FOREX picks come from `non_crypto_consensus`, which evades `strategy_blocklist.py` (not FOREX-named); v2 adds the allowlist has **0 call sites / 0/277 rows pass**. Consensus still ingests retired `forex_rsi2_mean_reversion` — exactly the strategy QW-FOREX-3-section flags for 48.5% slippage. Make the block observable/shadow before assuming it blocks; remove retired inputs from consensus.
- **Date-only timestamps:** FOREX `entry_time` date-only in **105/277** rows (v2) — reject date-only at ingest (`dashboard_generator.py:8136-8154`); ages/PnL windows on those rows are fabricated precision.
- **Peer-implemented:** FX `KeyError:'LONG'` scanner crash fixed by finpredict (direction normalisation) — same trap family as QW-FOREX-3's classifier work; weekend-FX caveat: Nov 14 2026 is a Saturday, "live" FX comparisons are Friday closes.

## QW-FOREX-5 · Demote, don't promote, until PF>1 net (S, config)
- **Problem:** FOREX `asset_class_summary.thresholdPass=false`, forward WR 0.0 on the displayed panel, yet FX picks still reach `picks.active` (2 of 20).
- **Fix:** Quick config gate: FX strategies require intrabar PF ≥1.0 (n≥30) to surface as smart/active picks; others stay research-only. Reuses `money_ready_verdicts` (already NOT_READY).
- **Verify:** Active panel FX count reflects only qualifying strategies; verdict cited on the card.
