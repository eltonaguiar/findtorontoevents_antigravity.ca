# Phase-2 Performance Audit — EQUITY

Date: 2026-05-31
Source: `ejaguiar1_stocks.trading_picks` (live), `category IN ('equity','stock','stocks')`
Cross-check: `audit_dashboard/data/pf_registry.json` (generated 2026-05-31; canonical view = `by_asset_class_policy_clean_net`)
Author: peer Claude (Opus 4.7), read-only

## Universe summary
- Total EQUITY rows: **2,288** (equity 2,001 / stock 23 / stocks 264)
- Open / unresolved: ACTIVE 130 + OPEN 371 = 501
- **Closed (this audit's denominator)**: 1,787 rows where `closed_at IS NOT NULL AND status IN ('TP_HIT','LOST','TIME_EXIT','EXPIRED')`
- Of which `pnl_pct IS NOT NULL`: **129** (the rest have NULL pnl — see Anomaly #1 below)
- Crypto-suffix leak scan (`%USDT|%USDC|%BTC|%ETH`): **0 hits** — PR #166 backfill held.

## Class-aggregate (raw, all closed rows with non-null pnl)

| metric | value | T2 target | verdict |
|---|---|---|---|
| n | 131 | ≥100 | PASS |
| TP_HIT WR (strict) | 27.5% (36/131) | ≥50% | FAIL |
| PnL>0 WR | 31.3% (41/131) | ≥50% | FAIL |
| PF (gross W / |gross L|) | **0.708** | ≥1.5 | FAIL |
| avg pnl_pct | -0.449% | >0 | FAIL |
| sum pnl_pct | -38.16% | >0 | FAIL |
| best / worst | +7.53% / -46.63% | — | tail-heavy |
| MDD proxy (per-trade equity-curve peak-to-trough) | **79.0%** | <20% | FAIL |

**Class verdict: FAIL on every T2 axis.** Not graduatable.

Registry cross-check (canonical `by_asset_class_policy_clean_net`):
- registry: n=40, WR=27.5%, PF=0.142
- this audit (raw): n=131, WR=31.3%, PF=0.708
- Divergence driver: registry applies a **2bp spot-flicker filter** (drops 1,043 of 1,763 closed rows as resolver artifacts) + dedup + policy-exclusions. After those filters the EQUITY surviving sample is n=40 and PF collapses further. **Both readings agree: class is sub-T2 by a wide margin.**

## Per-strategy table (n ≥ 10, closed rows)

| strategy | n | PnL_WR | TP_WR | PF | avg_pnl | T2 verdict | Notes |
|---|---|---|---|---|---|---|---|
| `stocks_rsi2_pullback` | 34 | **52.94%** | 52.94% | **1.522** | +0.480% | **PASS on PF & WR axes** — FAIL on n (<100) | best EQUITY edge in the book; T2-grade if scale holds |
| `regime_accumulation` | 14 | 35.71% | 35.71% | 0.433 | -2.886% | FAIL | tail event: worst=-46.6% (single 46% loser dominates) |
| `regime_mild_bear` | 22 | 0.00% | 0.00% | 0.000 | -2.623% | FAIL | 0 wins; structural problem (regime gate emits losers only) |
| `regime_strong_bear` | 10 | — | 0.00% | — | NULL | FAIL | all 10 closed rows have NULL pnl_pct — see Anomaly #1 |

## Strategies with n < 10 (insufficient sample, info only)

| strategy | n | PnL_WR | PF | avg_pnl |
|---|---|---|---|---|
| vix_reversal | 9 | 33.3% | 0.31 | -0.004% |
| smart_money_accumulation | 6 | 0.0% | 0.000 | -5.4% (large losers) |
| regime_mild_bull | 6 | 50% | 2.575 | +1.768% (promising but thin) |
| autocorrelation_exploiter | 4 | 0% | 0.000 | -0.18% |
| markov_zone_transition | 4 | 100% | NULL (no losses) | +0.43% |
| vt_equity_two_day_rsi_reversal | 4 | — | — | thin |
| connors_rsi2_scanner | 3 | 100% | NULL | +0.011% |
| hyperopt_connors_rsi2 | 3 | 33% | 0.29 | -2.43% |
| widened_tp_momentum_carry | 2 | 50% | 0.09 | -2.91% |
| fast_rsi2_extended | 2 | 50% | 7.9 | +0.003% (single big winner) |
| extreme_oversold_bounce | 2 | 50% | 1.01 | +0.018% |
| regime_strong_bull | 1 | 100% | NULL | +7.5% |

## Promotable to T2 (PASS all axes)
- **None.** No EQUITY strategy clears the full T2 bar (PF≥1.5, WR≥50, MDD<20, n≥100).

## Watchlist (PASS on edge axes, FAIL on sample size)
- **`stocks_rsi2_pullback`** — clearest graduation candidate. PF 1.52 / PnL-WR 53% / 34 closed picks / max DD per-trade ≤5%. **3× more picks (need 66 more) and a stable PF would graduate this to LIVE T2.** Source: `alpha_engine` (n=34 in source mix). Action: keep it enabled, do **not** widen TP/SL until n≥100.
- `regime_mild_bull` — PF 2.575 at n=6. Watch; do not size.

## Dead / retire candidates
- **`regime_mild_bear`** — 22 picks, 0 wins, PF=0. The gate is structurally emitting only losers. RECOMMEND demoting via `STRATEGY_INVESTIGATION_BEFORE_KILL.md` (export closed CSV → `mutation_analysis.py`); if the three-axis mutation can't recover edge, add to `BLOCKED_SOURCE_SYSTEMS`.
- **`regime_strong_bear`** — 10 closed rows, all NULL pnl_pct. Either kill the strategy or fix the resolver (Anomaly #1). Cannot trade what cannot be measured.
- **`smart_money_accumulation`** — 6 picks, 0 wins, mean -5.4%. Thin but directionally bad; watchlist→kill if next 10 picks don't reverse.
- **`regime_accumulation`** — 14 picks, 36% WR, dominated by one -46.6% loser. PF 0.43. If the -46% is a real fill (not a resolver bug), the strategy has unhedged tail risk and should be size-capped or killed.

## pf_registry divergences (>10%)

| strategy | this audit (raw) | registry (policy_clean_net) | divergence | likely cause |
|---|---|---|---|---|
| EQUITY class agg | n=131, PF=0.708 | n=40, PF=0.142 | n -69%, PF -80% | registry's 2bp spot-flicker filter drops 1,043 of 1,763 closed rows; small-magnitude wins survive less than small-magnitude losses → PF compresses further |
| `stocks_rsi2_pullback` | n=34, WR=53%, PF=1.52 | n=10, WR=30%, PF=0.032 | n -71%, PF -98% | 24 of 34 wins are sub-2bp pnl_pct → flagged as resolver spot-flicker and removed. **Investigate**: is `stocks_rsi2_pullback` legitimately a tiny-edge / high-frequency strategy where 2bp wins ARE real (TP=1-3bp), or is the resolver flat-exiting via TIME_EXIT at entry price? If real, the 2bp threshold is killing the only EQUITY edge we have. |
| `multi_asset_copytrader` | (n<10 in audit n≥10 filter) | n=11, PF=0.18 | — | only appears in registry view; sub-T2 either way |
| `regime_terminal` (source_system, not a strategy) | grouped differently | n=16 PF=0.69 | — | check naming convention |

**P1 action**: validate the 2bp spot-flicker filter against EQUITY's `stocks_rsi2_pullback`. If that strategy legitimately targets <10bp moves, the filter is hiding real PF and should be made strategy-aware (e.g. threshold = min(TP_pct / 3, 2bp)).

## Anomalies (P0/P1 flags)

1. **NULL pnl_pct on closed EQUITY rows (P0).** Status breakdown of NULL pnl on closed picks: LOST 55, EXPIRED 13, TP_HIT 0, TIME_EXIT 1, ACTIVE 15, OPEN 319. **55 LOST rows with no pnl_pct** is a resolver-coverage gap — these picks closed as losers but the magnitude was never written. They are invisible to PF math. Owner action: extend the EQUITY resolver path that PR #158 patched for crypto (SHIBUSDT) to backfill `pnl_pct` on `status='LOST'`. Until then, the true class PF is likely **worse** than 0.708 (we're missing 55 losses from the denominator side).
2. **`regime_strong_bear` 10 closed with NULL pnl (P1).** Strategy is uninstrumented; cannot be evaluated or killed safely.
3. **MDD proxy of 79% (P1).** Even on a 131-row sample, the cumulative pnl curve peaked at +39% then drew down to -38%. This is a per-trade-cumsum proxy not a portfolio MDD, but it indicates the class is regime-fragile (probably bear-regime mass losses dominate).
4. **No crypto-suffix leaks (good).** PR #166 backfill held; zero EQUITY rows with `%USDT/USDC/BTC/ETH` symbols.

## Recommendation (1-2 lines)

**Graduate-candidate (post-validation)**: `stocks_rsi2_pullback` — keep enabled, push n from 34 → 100, then re-audit; if PF holds ≥1.5 it is EQUITY's first T2 strategy. **Kill-candidate**: `regime_mild_bear` (0/22 wins is structural, not noise) — open a mutation review per `MUTATION_THREE_AXIS_PROTOCOL.md` and if no axis recovers edge, add to `BLOCKED_SOURCE_SYSTEMS`.

**Blocking P0**: the 55 closed-LOST rows with NULL pnl_pct must be backfilled before any EQUITY tier verdict can be trusted. The registry's 2bp spot-flicker filter must be re-validated against `stocks_rsi2_pullback`'s actual TP target.
