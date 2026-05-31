# Phase-2 Performance Audit — BOND

Author: peer_claude (Opus 4.7) — 2026-05-31
Source: `ejaguiar1_stocks.trading_picks` (live), `audit_dashboard/data/pf_registry.json`.
Filter: `LOWER(category)='bond'`. Read-only.

## Class-aggregate

**Primary cohort — `closed_at IS NOT NULL` (the same filter the dashboard / pf_registry uses):**

| n | WR | PF | avg_pnl | MDD | worst | best |
|---|---|---|---|---|---|---|
| 5 | 60.0% | 362.6 | 1.020% | n/a (no equity curve in this pass) | -0.0141% | 5.000% |

**T2 verdict per axis (n>=100 / WR>=50 / PF>=1.5 / MDD<20):** `n FAIL (5«100)` · `WR PASS (60)` · `PF PASS (362)` · `MDD n/a` → **OVERALL: INSUFF-N FAIL** (PF is a 1-trade artifact; ignore).

**Sensitivity cohort — `status IN ('WON','LOST','TP_HIT','SL_HIT','TIME_EXIT','EXPIRED')`** (includes 125 BOND picks where the outcome was resolved but `closed_at` was never stamped — see Anomaly #1 below):

| n | WR | PF | avg_pnl |
|---|---|---|---|
| 130 | 2.31% | 1.085 | 0.003% |

**T2 verdict (sensitivity cohort):** `n PASS (130)` · `WR FAIL (2.3«50)` · `PF FAIL (1.085«1.5)` · `MDD n/a` → **OVERALL: FAIL.** This is the more honest view: 117 of 130 resolved picks are TIME_EXIT at exactly 0.000% PnL, and the only real losers (-0.58% to -0.84%) come from `bond_mean_reversion`, `bond_yield_curve_slope`, and `bond_yield_momentum`.

## Per-strategy table (resolved-status cohort, all n>=1 shown)

| strategy | n | wins | losses | timeouts | WR | avg_pnl | PF | worst | best | T2 verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| cta_cross_asset_tsmom | 53 | 0 | 0 | 53 | 0.00% | 0.000 | n/a | 0.00 | 0.00 | FAIL (100% TIME_EXIT, no edge) |
| futures_ema_stack_momentum | 36 | 0 | 0 | 36 | 0.00% | 0.000 | n/a | 0.00 | 0.00 | FAIL (100% TIME_EXIT, no edge) |
| non_crypto_consensus | 9 | 0 | 0 | 9 | 0.00% | 0.000 | n/a | 0.00 | 0.00 | INSUFF-N + 100% TIME_EXIT |
| futures_bb_mean_reversion | 8 | 0 | 0 | 8 | 0.00% | 0.000 | n/a | 0.00 | 0.00 | INSUFF-N + 100% TIME_EXIT |
| futures_momentum | 8 | 3 | 1 | 4 | 37.50% | 0.637 | 362.6 | -0.0141 | 5.000 | INSUFF-N (PF is a 1-trade artifact, n=8) |
| cta_golden_cross_200 | 6 | 0 | 0 | 6 | 0.00% | 0.000 | n/a | 0.00 | 0.00 | INSUFF-N + 100% TIME_EXIT |
| bond_mean_reversion | 3 | 0 | 3 | 0 | 0.00% | -0.610 | 0.000 | -0.8367 | -0.3957 | INSUFF-N + FAIL (-61% avg PnL — looks like leverage or % misformat) |
| bond_yield_curve_slope | 3 | 0 | 3 | 0 | 0.00% | -0.832 | 0.000 | -0.8371 | -0.8271 | INSUFF-N + FAIL (-83% avg PnL — likely PnL-units bug) |
| bond_yield_momentum | 3 | 0 | 3 | 0 | 0.00% | -0.602 | 0.000 | -0.6210 | -0.5831 | INSUFF-N + FAIL (-60% avg PnL — likely PnL-units bug) |
| etf_rsi2_pullback | 1 | 0 | 0 | 1 | 0.00% | 0.000 | n/a | 0.00 | 0.00 | INSUFF-N (only 1 pick) |

> No BOND strategy reaches n>=100. No strategy has both n>=10 and a meaningful PF. The `futures_momentum::ZN=F` cohort has the only real wins (3/5 closed = TP_HIT @ 5.000%/0.057%/0.056%) but n=8 total — not graduation-worthy.

## Promotable to T2 (PASS all axes)

**None.** Every BOND strategy fails the n>=100 axis. The closed_at-NOT-NULL view's superficial PF=362 is driven by ONE 5%-PnL trade.

## Watchlist (1-2 axes failing or thin sample)

- **`futures_momentum` (ZN=F only)** — n=8 resolved (5 closed_at-stamped), WR 37.5%, PF=362.6 (1-trade artifact). The only BOND strategy with ANY wins. Worth growing the sample before any verdict. Currently 5 OPEN positions — let the next 20-30 close and re-audit.
- **`cta_cross_asset_tsmom`** — n=53 resolved, but 100% TIME_EXIT @ 0.000% PnL. Either the resolver is closing trades at entry price (TP/SL never hit) or the strategy's TP/SL are unreachable in a typical hold window. Investigate before promotion.
- **`futures_ema_stack_momentum`** — same pattern as above, n=36, 100% TIME_EXIT @ 0%. Same investigation.

## Dead / retire candidates

- **`bond_mean_reversion`** — 3/3 LOST, avg PnL -61%. The magnitude (-0.40 to -0.84 = -40% to -84%) suggests either a units bug (pnl_pct stored as raw fraction with the "pct" name) or genuine catastrophic losses on a tiny sample. **Recommend immediate kill UNLESS units bug is confirmed**, in which case fix the units writer first then re-audit.
- **`bond_yield_curve_slope`** — 3/3 LOST, avg PnL -83%. Same units-bug suspicion, same kill recommendation.
- **`bond_yield_momentum`** — 3/3 LOST, avg PnL -60%. Same.
- All three above currently have OPEN positions (MUB, TLT, IEF, HYG, JNK, BNDX, TIP, EMB, AGG). If units are correct, **kill before more losses land**.

## pf_registry divergences

| metric | DB (closed_at NOT NULL) | pf_registry.by_asset_class | DB (resolved status) | divergence |
|---|---|---|---|---|
| BOND n | 5 | 2 | 130 | registry undercounts by 60% even vs the same filter |
| BOND wins | 3 | 0 | 3 | registry shows zero wins, DB shows 3 TP_HITs |
| BOND PF | 362.6 | 0.0 | 1.085 | registry rebuilt off `bond_scanner::IEF` only (2 losses) — top_source filter excludes `futures_momentum::ZN=F::multi_asset_copytrader` |
| BOND strategies | 10 distinct (resolved) | 1 (`bond_scanner`) | — | registry's `by_asset_class_strategy` shows only `bond_scanner` (n=2). **Real strategy mix (futures_momentum, cta_cross_asset_tsmom, futures_ema_stack_momentum, bond_mean_reversion, bond_yield_*) is invisible to the registry.** |

**Root cause hypothesis (must verify before fix-PR):** `pf_registry` is likely re-aggregating from a frozen snapshot or applying a `source_system='bond_scanner'`-only filter. The CLAUDE.md note that "BOND INSUFF-N (PF 0 / WR 0% / n=8)" matches an even older snapshot. **The dashboard is materially under-reporting BOND activity** — 130 resolved picks reduced to 2 in the registry.

## Anomalies flagged (per post-#158/#166 honest-counts directive)

1. **`closed_at IS NULL` while status is resolved — 125 BOND rows.** Same plumbing pattern as the pre-#166 EQUITY mistag bug. Affects every strategy in the table above except `futures_momentum` (the only one whose closer stamps `closed_at`). This silently halves-or-worse the visible BOND sample. **Filing as candidate INCIDENT_BOND#1** (follow-up only, no code change in this READ-ONLY pass).
2. **`pnl_pct` magnitude bug suspect (-40% to -84% on 9 picks across 3 bond_* strategies).** Either (a) pnl is fraction-not-percent here, or (b) these are genuine -60% losses on leveraged ETF positions with no SL. Either way it warrants a units audit on the BOND closer path.
3. **ID/symbol mismatch:** `iso_regime_terminal_GBPUSD=X_2674967031` has symbol=IEF, category=bond. ID came from a stale ISO-regime FOREX template. Not a pricing bug, but a clue that the id-minter is leaking across asset classes.
4. **`ZN=F` correctly tagged BOND** (10Y T-Note futures underlying = US Treasury). Confirmed not a mistag. No action.
5. **`cta_cross_asset_tsmom` + `futures_ema_stack_momentum`: 89 picks, 100% TIME_EXIT, 100% PnL=0.000.** Strong smell of a resolver that closes at entry price when the holding window expires before either TP or SL trades. Same family of resolver bug that PR #158 (SHIBUSDT) fixed for CRYPTO. **Candidate INCIDENT_BOND#2.**

## Recommendation

1. **Do not graduate any BOND strategy to T2 LIVE.** Class is unfit on the n axis and (under the honest resolved-status view) on the WR + PF axes.
2. **Next graduation candidate (eventual):** `futures_momentum::ZN=F::multi_asset_copytrader` — the only strategy with real wins (3 TP_HIT in 5 closed). Let the 5 OPEN positions close out, target n>=30 before re-audit, and verify the 5.000% TP_HIT isn't a tick-size / TP-snap artifact.
3. **Next kill candidates (pending units-verification):** `bond_mean_reversion`, `bond_yield_curve_slope`, `bond_yield_momentum` — three losing-only strategies whose realized PnL magnitudes (-40 to -84%) are either catastrophic or a units bug. Audit first, kill or rescale TP/SL second.
4. **Plumbing fix #1 (BLOCKER for any future BOND audit):** stamp `closed_at` whenever a resolved-status outcome lands. 125 BOND rows are currently invisible to the dashboard/registry.
5. **Plumbing fix #2:** investigate why `pf_registry` only sees `bond_scanner::IEF (n=2)` when the DB has 10 distinct strategies and 130 resolved picks under `category='bond'`.
