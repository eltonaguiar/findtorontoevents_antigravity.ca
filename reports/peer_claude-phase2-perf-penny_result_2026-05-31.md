# Phase-2 Performance Audit — PENNY

Date: 2026-05-31
Source: `ejaguiar1_stocks.trading_picks` (live), `audit_dashboard/data/pf_registry.json`
Filter: `LOWER(category) IN ('penny','pennystock') AND closed_at IS NOT NULL`

## TL;DR
PENNY is the thinnest class on the dashboard: **n=8 closed** total (vs T2 floor of 100). Class-aggregate is **FAIL on every axis** (WR 25%, PF 0.17, avg_pnl -3.56%). Zero strategies meet T2 minimums. No graduation candidates. Sample is too thin to retire individual strategies on stats alone — but the dominant strategy `penny_deep_oversold` shows asymmetric tails (worst -14.6%, best +3.3%) consistent with classic penny-stock left-skew that no edge has cleared.

## Class-aggregate
```
n=8  WR=25.00%  PF=0.169  avg_pnl=-3.564%
worst=-14.627%  best=+3.260%   MDD-proxy (single-trade worst) ≈ 14.6%
```
T2 status:
- n >= 100  → **FAIL** (INSUFF-N, 8/100)
- PF >= 1.5 → **FAIL** (0.169)
- WR >= 50% → **FAIL** (25%)
- MDD < 20% → PASS on proxy (14.6%) but meaningless at n=8

## Per-strategy table
| strategy | n | WR | PF | avg_pnl | T2 verdict |
|---|---|---|---|---|---|
| penny_deep_oversold | 4 | 50.00% | 0.192 | -5.336% | INSUFF-N + PF FAIL |
| ema_stack_momentum | 1 | 0% | n/a | n/a (null pnl) | INSUFF-N + FAIL |
| multi_sigma_reversal | 1 | 0% | 0.000 | -3.600% | INSUFF-N + FAIL |
| volume_profile_poc_reversion | 1 | 0% | n/a (EXPIRED 0%) | 0.000% | INSUFF-N |
| autocorrelation_exploiter | 1 | 0% | n/a (EXPIRED 0%) | 0.000% | INSUFF-N |

(All `n >= 10` filter dropped — universe is too thin to apply it; full strategy list shown.)

## Promotable to T2 (PASS all axes)
- **None.** No strategy clears even one HF-grade axis at meaningful n.

## Watchlist (1-2 axes failing or thin sample)
- `penny_deep_oversold` (n=4) — only strategy with hits (2 TP wins on AMC/MARA), but losers are catastrophic (-14.6% IONQ, -11.8% RIOT). WR 50% disguises PF 0.19 because losers are ~5x the winners. Re-evaluate after n>=30 with **mandatory tighter stop on momentum names**.

## Dead/retire candidates
- Not retirable on stats alone (n=1 each). Recommend leaving in passive scan but **block sizing**:
  - `multi_sigma_reversal` (1 loss, -3.6%)
  - `ema_stack_momentum` (1 loss, null pnl — resolver/data issue)
  - `volume_profile_poc_reversion`, `autocorrelation_exploiter` — both EXPIRED at 0% (no signal evidence)

## pf_registry divergences
Registry `by_asset_class_policy_clean_net` for `PENNY_STOCK`: `n=1, WR=0, PF=0.0, top_source='multi_asset_scanner'`.
Raw DB shows n=8 across 5 strategies. Divergence is explained by aggressive policy-clean filter dropping 7/8 picks (including the only winners under `penny_deep_oversold` → `institutional_picks_engine`).

**Flag:** the policy-clean filter is hiding the strategy with the highest hit rate (`penny_deep_oversold`, 50% WR) and surfacing only `multi_asset_scanner` (1 pick, 0% WR). This is a **registry-coverage gap, not a leakage signal** — but it means the dashboard's PENNY readout misrepresents the actual signal mix. Recommend audit of `policy_clean` gates against `institutional_picks_engine` and `alpha_engine_fast` (the two engines that produced 7/8 picks but were dropped).

`fractal_decay_penny` appears in registry (`by_asset_class_strategy[87]`) but has **zero rows in `trading_picks` under penny categories** — dormant strategy. Worth backfilling history if it ever produced picks elsewhere.

## Symbol anomaly scan
- Zero crypto-suffix symbols (`USDT`/`USD`/`BTC`/`ETH`) tagged penny — **PR #158 SHIBUSDT resolver fix and PR #166 EQUITY mistag backfill held**.
- All 8 symbols are NASDAQ/NYSE equity tickers (AMC, IONQ, MARA, RIOT, NIO, SOFI, SNDL) — boundary with mid-cap EQUITY is fuzzy (IONQ market cap ≫ penny threshold). Consider tightening category gate at pick-emit time.

## Recommendation
1. **No graduation.** PENNY remains INSUFF-N across the board; do not size up.
2. **Next graduation candidate (medium-term):** `penny_deep_oversold` — only strategy with any wins; needs n>=30 + a **hard stop redesign** (current -14.6% tail kills the PF despite 50% WR). Pair with mandatory ATR-based SL.
3. **Kill (soft):** `multi_sigma_reversal` and `ema_stack_momentum` for PENNY — block emission for this class while leaving the strategies active for EQUITY where they have richer samples. Do not retire registry-wide on n=1.
4. **Fix surfacing:** audit the registry's policy-clean filter — surfacing the worst single-pick strategy while hiding `penny_deep_oversold` distorts the public dashboard.
