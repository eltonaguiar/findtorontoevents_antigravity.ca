# Deep Audit: Picks, Asset-Class Drift, and Root Causes (2026-04-28)

## Scope

This deep-dive answers the active questions about:
- Why some tile stats look disconnected from active picks
- Why high historical WR/PF systems have near-zero active exposure
- Why non-crypto classes (FOREX/COMMODITY/FUTURES/ETF/BOND) look broken or underrepresented
- Where we likely have hidden alpha if we tweak filters/entry rules
- Which free data sources and open-source libraries can add immediate signal quality

Primary focus: Goal #1 (asset-class performance quality on /audit).

## Methodology

### Data sources used
1. `audit_dashboard/data/dashboard_data.json` (live dashboard payload snapshot)
2. `reports/hedge_fund_performance_review_summary_2026_04_27.md`
3. `reports/hedge_fund_performance_review_detailed_2026_04_27.md`
4. `reports/action_B_resolver_2026_04_27.md`
5. `reports/resolver_fix_implementation_2026_04_28.md`
6. `audit_trail/quality_gates.py` (gating and non-crypto probation logic)

### Repro steps
- Generated a deterministic metrics extract with:
  - `tools/_tmp_deep_metrics.ps1`
- Output artifact:
  - `reports/deep_audit_metrics_2026_04_28_main.json`

### Definitions
- `WR(w/l)` = wins / (wins + losses)
- `PF` = sum(profit pnl_pct rows) / abs(sum(loss pnl_pct rows))
- `Last-100 by asset` = first 100 closed rows per asset class in the payload order

Important caveat:
- Non-crypto history still has resolver contamination risk (documented in Workstream B). Interpret FOREX/COMMODITY with caution until historical re-resolve is complete.

## Executive Findings

1. **S-tier mismatch is real.**
   - Current payload has **zero S-tier** in extreme conviction (`S: 0, A: 1, B: 8`) and no active S-tier rows.
   - If a tile still shows "S-tier 13W/1L", that is very likely stale derivation/cache or a different aggregation window than active picks.

2. **`mega_mutation` can look great historically and still have no active picks.**
   - Closed stats: `n=15, WR=73.3%, PF=3.91`
   - Active stats: `0`
   - Variants are sparse (`mega_mutation_macd_rsi_m048: 11`, `mega_mutation_ema_momentum_m006: 5`) and currently not emitting picks that survive gate stack.

3. **`copy_trader_highscore` is a hidden positive sleeve with no active allocation.**
   - Closed stats: `n=10, WR=70.0%, PF=6.08, sum_pnl=20.47`
   - Active stats: `0`
   - This is likely under-deployed due low emission frequency and/or gate routing, not bad edge.

4. **`claude_ml_moderate_mutation` appears not wired into current closed/active corpus.**
   - Closed stats: `n=0`
   - Active stats: `0`
   - If UI still reports this source, that likely indicates stale label plumbing or alias mismatch.

5. **Non-crypto exposure is still structurally under-activated.**
   - Active by asset: `CRYPTO 31, FOREX 7, COMMODITY 2, EQUITY 1, ETF 0, BOND 0`
   - Closed by asset includes `ETF 83, BOND 17, FUTURES 2` but active is zero for ETF/BOND.

6. **Futures count is truly tiny in the current canonical payload.**
   - Closed FUTURES: `2` (both wins, but total pnl rounds to `0.0`), likely too small for any robust inference.

## Why the Weird Mismatches Happen

## 1) Tile-vs-active metric mismatch

Root cause pattern:
- Some dashboard views aggregate historical cohorts, while active tables are post-gate snapshots.
- If cohort/tile logic uses a different source object or stale cache than active picks, you get contradictory views (ex: historical S-tier wins vs no S-tier active rows).

Evidence:
- `extreme_conviction` in current payload: S=0
- `systems_13_1` search on current systems: none

Implication:
- The user-observed `13W/1L` stat likely came from a different snapshot/metric path than current active feed.

## 2) High PF/WR with no active picks (mega_mutation, copy_trader_highscore)

Root causes:
- Low signal frequency + high selectivity gates = empty active despite positive historical.
- Non-crypto and weaker classes incur extra probation/rejection logic in `quality_gates.py`.
- Active feed is not a "top historical edge" list; it is "what passes now" under current gate stack.

Implication:
- Historical quality is not enough. A strategy must also emit fresh, compliant rows under current rule set.

## 3) Non-crypto classes look coin-flippy or worse

Root causes:
- Resolver contamination (especially FOREX/COMMODITY historical labels) is documented and significant.
- A large portion of non-crypto rows are gate-thin and class-probationed before they can become active.
- Active non-crypto floors require enough forward sample and class-specific WR thresholds.

Implication:
- Reported WR without resolver-normalized history can overstate or distort true edge.

## Hidden Gem Insights (Overlooked)

## Gem A: `copy_trader_highscore` looks stronger than its allocation suggests

- `n=10, WR=70.0%, PF=6.08`
- Active count = 0

Opportunity:
- Add a controlled deployment lane: when `copy_trader_highscore` emits and passes minimum trust/sanity checks, allow small fixed allocation even if broader source group is sparse.

## Gem B: FOREX is not uniformly bad; the edge is concentrated

Top FOREX strategies by sample:
- `forex_rsi2_mean_reversion`: `n=559, WR=51.0%, PF=3.62, sum_pnl=34.39`
- `non_crypto_consensus`: `n=106, WR=57.8%, PF=1.47` but near-zero sum pnl

Opportunity:
- Stop treating FOREX as monolithic.
- Keep/expand only high-sample profitable clusters (`forex_rsi2_mean_reversion`) and kill drag families (`Breakout Momentum`, weak CTA slices).

## Gem C: Commodity alpha appears concentrated in one strategy, with major poison pills

Top COMMODITY strategies:
- `futures_momentum`: `n=488, WR=45.9%, PF=1.29, sum_pnl=16.11` (workhorse)
- `cta_commodity_momentum_term`: `n=46, PF=0.02`
- `cot_positioning`: `n=10, WR=0%`
- `cftc_cot_commercial_signal`: `n=9, WR=11.1%, PF=0.01`

Opportunity:
- Hard-demote or kill the poison-pill commodity families; preserve and test around `futures_momentum`.

## Gem D: R:R >= 1.5 is not helping FOREX in this dataset

- FOREX all: `n=802, PF=1.35`
- FOREX with `R:R >= 1.5`: `n=59, PF=0.87, sum_pnl=-2.95`
- FOREX with `R:R < 1.5`: `n=743, PF=1.53, sum_pnl=32.21`

Interpretation:
- The current R:R threshold is likely selecting structurally weaker setup family in FOREX.

Actionable tweak:
- Remove hard R:R>=1.5 for FOREX; replace with strategy-conditional R:R policy.

## Gem E: ETF/BOND have enough closed rows to start controlled active re-entry

- ETF closed `83`, BOND closed `17`, active both `0`

Opportunity:
- Add a very small experimental active lane for ETF (not bond yet) using strict source whitelist + forward sample gate.

## Root-Cause Matrix and Actions

| Symptom | Root cause | Fix (concrete) | Priority |
|---|---|---|---|
| S-tier historical but no S-tier active | Different metric paths / stale cohort display | Force tile aggregation from same payload object as active table; add generated_at and query hash in UI | P0 |
| Mega mutation strong history, 0 active | Sparse emission + gate mismatch | Add strategy-specific fallback lane for `mega_mutation_macd_rsi_m048` with hard risk cap | P1 |
| copy_trader_highscore 70% WR, 0 active | Under-routed source in active feed | Add source-specific active quota (small), require trust + min fwd trades | P1 |
| Forex appears unstable | Resolver + mixed strategy quality | Complete historical re-resolve, then prune to profitable subfamilies only | P0 |
| Commodity low quality | Poison strategies polluting class | Kill or hard-demote `cta_commodity_momentum_term`, `cot_positioning`, `cftc_cot_commercial_signal` | P0 |
| ETF/BOND no active | Probation + thin sample gates | Enable ETF micro-allocation lane with strict guardrails; keep bond in observation mode | P2 |

## Filter and Entry-Criteria Tweaks (Candidate)

## Tweak 1: FOREX class policy
- Replace global FOREX R:R filter with strategy-level policy:
  - `forex_rsi2_mean_reversion`: allow lower R:R if forward WR and PF are strong
  - weak breakout/CTA variants: stricter R:R and confidence floors

Expected effect:
- Avoid killing the profitable core while removing drag families.

## Tweak 2: COMMODITY strategy carve-out
- Keep `futures_momentum` on reduced risk budget.
- Block commodity strategies with `PF < 0.3` and `n >= 20` until retrained.

Expected effect:
- Immediate left-tail reduction without deleting entire asset class.

## Tweak 3: Active allocation guardrail
- Add source-level min/max active slots by empirical edge and sample quality:
  - floor for high-PF sparse winners (`copy_trader_highscore`)
  - ceiling for high-volume low-quality emitters

Expected effect:
- Prevent starvation of high-quality sparse systems.

## Tweak 4: Resolver integrity gate (must-have)
- Do not use non-crypto class WR as policy input until v2 historical re-resolve lands and noise-share check passes.

Expected effect:
- Prevent policy churn based on contaminated labels.

## Free Data APIs to Add (High ROI)

## FOREX / Macro
1. **FRED API** (free): rates, DXY proxies, macro regime context
2. **BIS/central bank data** (free): REER/value style features
3. **Alpha Vantage FX_DAILY** (free tier): secondary OHLC validation feed

## Commodities / Futures
1. **CFTC Socrata COT API** (free): positioning regime features
2. **FRED commodity series** (free): macro trend overlays
3. **Stooq free EOD feed** (free): fallback price validation

## Prediction markets / copytrader
1. **Polymarket API/subgraph** (free): market-implied probability features
2. **Kalshi API** (free/public docs): event-probability factors
3. **Myfxbook public performance endpoints** (free with account): trader-level filters

## GitHub Libraries That Can Improve Value

1. **vectorbt**: fast parameter sweeps and walk-forward evaluation
2. **empyrical / pyfolio-reloaded**: robust risk decomposition, factor-like diagnostics
3. **ruptures**: change-point detection for concept drift in strategy cohorts
4. **arch**: volatility regime modeling for dynamic sizing
5. **hmmlearn** (or pomegranate): explicit market regime latent state modeling

Integration warning:
- Wire these libs into production scoring path (not sidecar-only), otherwise they become orphan modules with zero live impact.

## Direct Answers to Your Specific Questions

1. **"Why crypto S-tier 13W/1L but no active picks?"**
   - In current canonical payload, S-tier active is zero (`S=0`). So that 13/1 is not from the same current active dataset.

2. **"Why mega_mutation 76.5% WR / PF 4.62 but only 1 active pick?"**
   - In current payload it is `n=15, WR=73.3, PF=3.91`, and **0 active**. This is a sparse historical edge that currently has no rows passing active gates.

3. **"Is mega active pick winning/probable?"**
   - There are no active mega rows in the current payload, so there is nothing to evaluate live right now.

4. **"repeat with copy_trader_highscore"**
   - Closed edge looks strong (`70% WR, PF 6.08`) but active is zero. This is under-allocation, not proven failure.

5. **"repeat with claude_ml_moderate_mutation"**
   - No active and no closed rows in current payload (`n=0`). Likely naming/wiring mismatch or stale UI reference.

6. **"why only 2 futures closed?"**
   - Because canonical closed payload currently only has 2 FUTURES rows. This indicates feed scarcity and/or class-routing constraints into FUTURES label.

7. **"why no active ETF/bonds?"**
   - Current gate stack + probation behavior + thin active emissions; ETF/BOND are present in closed history but not surviving into active rows.

8. **"commodities 6% WR / forex 15% WR (wtf)"**
   - Current per-asset last-100 does **not** reproduce those exact values (`FOREX last-100 wr_wl ~60.2%, COMMODITY ~46.9% in this payload).
   - This strongly suggests metric-window mismatch or stale tile source.

## Final Prioritized Action Plan

1. **P0**: Enforce single-source-of-truth for tiles + active table (same payload object, same time window).
2. **P0**: Finish resolver historical re-resolve, then rerun edge validation.
3. **P0**: Commodity poison-strategy demotion (`cta_commodity_momentum_term`, `cot_positioning`, `cftc_cot_commercial_signal`).
4. **P1**: Add controlled active allocation lane for `copy_trader_highscore`.
5. **P1**: FOREX strategy-level gate split (do not globally enforce R:R>=1.5).
6. **P2**: ETF micro-allocation lane with strict risk cap and sample threshold.

## Verification Appendix

All headline numbers in this report are reproducible from:
- `tools/_tmp_deep_metrics.ps1`
- `reports/deep_audit_metrics_2026_04_28_main.json`

If desired, next step is to convert this into a CI guard script that fails when tile and active metrics diverge beyond tolerance.
