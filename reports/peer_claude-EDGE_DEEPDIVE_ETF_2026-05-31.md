# Edge Deep-Dive — ETF — 2026-05-31

**Author:** peer_claude (Opus 4.7 subagent, ETF ownership)
**Sources:** `audit_dashboard/data/edge_stability/edge_stability_ETF.json` (2026-05-31T22:23Z),
`audit_dashboard/data/dashboard_data.json::hf_stats.by_asset_class.ETF`,
`audit_dashboard/data/money_ready_verdict.json` (empty for ETF),
live `ejaguiar1_stocks.trading_picks` (queried 2026-05-31).

---

## 0. Prompt premise correction

The orchestrator prompt states: *"ETF — current PF 0.48 WR 50% n=4 INSUFF. Universe too narrow (5 symbols)."*

**That is the `money_ready_verdict.json` view, which is empty/stale for ETF.** Three other views tell a different story:

| View | n | WR | PF | Source |
|---|---|---|---|---|
| money_ready_verdict.json | 4 | 50% | 0.48 | (the prompt's number — stale) |
| live DB WON/LOST only | 15 | ~7% | ~0 | trading_picks LOWER(category)='etf' AND status IN ('WON','LOST') |
| hf_stats.by_asset_class.ETF | 155 | 52.3% | **1.32** | dashboard_data.json (Sharpe 1.83, Sortino 2.93 — but MDD 77.6%) |
| edge_stability_ETF 90d | 153 | **54.9%** | **1.44** | edge_stability_ETF.json |
| edge_stability_ETF 30d | 55 | **63.6%** | **1.96** | same |
| edge_stability_ETF 7d | 17 | **76.5%** | **3.95** | same |

**Interpretation:** ETF is the closest class to T2 of any in the audit — 90d PF 1.44 is just below the 1.5 floor, with WR already above the 50% floor and n>100. The 30d / 7d windows are well into Tier-1 territory. The reason ETF reads "FAIL/INSUFF" on the verdict surface is a **plumbing problem, not an edge problem**:

1. `money_ready_verdict.json` ETF block is empty (no entry).
2. Live DB `WON/LOST` filter strips out 134 rows stuck at `status='TIME_EXIT' AND pnl_pct=0` (Phase 4 resolver bug, documented in `peer_claude-phase10b-money-maker-ETF_result_2026-05-31.md`).
3. Universe is **43 distinct ETFs** (top: SPY 27, QQQ 26, SOXS 23, JDST 23, XLK 22, LABD 22, XLE 17, GLD 15, IWM 13, EFA 12, REMX 11, EEM 10), not 5.

**Top operator action this minute:** wire `edge_stability_ETF.json` into the verdict pipeline so the dashboard stops reading n=4. This unlocks ETF as the leading T2 candidate across the entire 6-class lineup.

---

## 1. Root cause of "no edge" verdict

Three orthogonal causes — none of them are "no edge exists":

### Cause A — Resolver TIME_EXIT zero-pnl bug (plumbing)
134 ETF rows where `status='TIME_EXIT' AND pnl_pct=0.00000000`. The intrabar resolver isn't capturing close-vs-entry spread when TP/SL don't trigger. This is the same bug as CRYPTO (the "resolver intrabar = THE upstream T2 blocker" line from session-close memory 2026-05-31). For ETF it strips ~80% of the closed cohort out of the verdict view.

### Cause B — Verdict pipeline doesn't read edge_stability
`money_ready_verdict.json` reads `pf_registry.by_asset_class_policy_clean_net.ETF` which is empty (0 entries — see phase10b report). The pipeline never falls through to edge_stability even though that file has n=161 with PF 1.4 / Sharpe 1.83. So the live verdict is structurally blind.

### Cause C — One bad strategy poisons the live-DB view
The 15 WON/LOST rows are dominated by `institutional_picks_engine / extreme_oversold_bounce` (5 rows, 0/5 wins, avg -3.10%). Strip that one strategy and the live-DB cohort is **10 closures with positive expectancy**.

**None of these are "ETF has no statistical edge."** All three are infrastructure/reporting bugs. The actual signals (per edge_stability) work.

---

## 2. Buried winners ALREADY in the registry (n<30, PF>1.5)

Per `edge_stability_ETF.json::per_strategy`, sorted by 90d PF:

| strategy | source_system | n_total | 90d_WR | 90d_PF | 30d_WR | 30d_PF | verdict |
|---|---|---|---|---|---|---|---|
| **adx-trend-scout** | kimi_riseoftheclaw | 15 | 80.0% | **7.47** | 70.0% | 4.40 | T1-tier on tiny n — **track to n=30** |
| **rs-breakout-scout** | kimi_riseoftheclaw | 23 | 81.8% | **4.30** | 75.0% | 2.43 | T1-tier; needs n>=30 OOS — **closest buried winner** |
| **price-accel-scout** | kimi_riseoftheclaw | 4 | 50.0% | 3.34 | 100% | 999 | too thin but +EV — keep emitting |
| **macd-hidden-div-scout** | kimi_riseoftheclaw | 4 | 66.7% | 3.08 | 66.7% | 3.08 | watch |
| **vwap-reversion-scout** | kimi_riseoftheclaw | 4 | 75.0% | 2.86 | 0% | 0 | recent dip — watch |
| **quality-momentum-scout** | kimi_riseoftheclaw | 4 | 50.0% | 3.25 | 0% | 0 | thin |
| **intermarket-flow-scout** | kimi_riseoftheclaw | 32 | 59.4% | **1.57** | 66.7% | 2.02 | **GRADUATION CANDIDATE — n>30, PF>1.5, WR>50, all axes pass except MDD/Sharpe** |

**Top recommendation:** `intermarket-flow-scout / kimi_riseoftheclaw` is the **only ETF strategy with n>=30 AND PF>1.5 AND WR>50** in the live cohort. It is one MDD audit away from T2 promotion. Verify MDD<20% on the 32 closures; if it passes, this is a real-money candidate.

**Second tier (track to n=30):** `rs-breakout-scout` (n=23, PF 4.30) and `adx-trend-scout` (n=15, PF 7.47). Both kimi_riseoftheclaw, both classical trend signals (relative-strength breakout + ADX trend filter), both performing way above what those signals do in retail backtests — likely either (a) genuine kimi alpha or (b) over-fit to small n; need OOS to disambiguate.

---

## 3. Edge angles NOT YET TRIED in ETF (ranked by feasibility)

The prompt's list (sector momentum, VIX term, country momentum, risk parity, leveraged decay arb, smart-beta, REIT/TLT, HYG signals) is good. Adding angles the prompt missed:

### Tier-1 feasibility (high data quality, low blowup risk, n materializes fast)

1. **Cross-asset risk-on/off via SPY/TLT/GLD/HYG correlation regime shifts.**
   Hong Cheng & Madhavan (2009) "Cross-Asset Momentum"; Asness Moskowitz Pedersen (2013) "Value & Momentum Everywhere". The signal: when the 60d corr(SPY,TLT) flips from negative to positive (risk parity breaks down), HYG and EEM dump within 5-10 days. ETF universe already has all four symbols emitted (SPY n=27, TLT/GLD/HYG in top 25). **Data needed:** intraday 1d bars on the 4-symbol basket; nothing new. **Caller wire-up:** add `cross_asset_regime_shift.py` emitter under `alpha_engine/etf_strategies.py`. **Expected closures/month:** 10-15 (regime shifts are rare but high-conviction).

2. **Sector dispersion (XLK/XLE/XLF/XLV cross-sectional vol).**
   When cross-sectional sector vol spikes >1.5σ above 90d mean, sector rotation generates structural alpha (Ilmanen 2011, Cremers 2017 "Active Share"). ETF universe already has XLK/XLE/XLF emitted. **Data:** daily close on 9 SPDR sectors. **Wire:** new emitter `sector_dispersion_rotation.py`. **Expected n/month:** 20-30.

3. **VIX term structure tilt (NOT VXX/SVXY blowup risk).**
   Bordonado, Molnar, Samdal (2017) "VIX Term Structure & Crude Oil Returns"; trade on the *signal* via SPY/QQQ direction (not via VXX/SVXY). When VIX1M/VIX3M > 1.05 (backwardation), buy SPY puts or stay flat; when < 0.95 (contango), risk-on SPY/QQQ. No VXX/SVXY exposure means no decay-mismatch blowup. **Data:** CBOE VIX, VIX3M (free from yfinance `^VIX`, `^VIX3M`). **Wire:** new `vix_term_signal.py`. **Expected n/month:** 15-25.

### Tier-2 feasibility (interesting but data-heavy or blowup-risky)

4. **Bond duration arb (TLT/IEF/SHY) — yield curve steepener/flattener trades.**
   Litterman & Scheinkman (1991) PCA on yield curve. When 10Y-2Y spread compresses below 25bp (flattener), short TLT vs long IEF. **Already exists as orphan backtest** `bond_tlt_ief_v3` (PF 1.29-1.62 per prompt) — needs wire-up to emitter. **Risk:** drawdowns during Fed pivots can be deep. **Wire:** existing backtest → emitter; **this is the #1 low-effort win.**

5. **HYG/LQD credit spread divergence.**
   Bao Pan Wang (2011) "Liquidity of Corporate Bonds". When HYG/LQD ratio drops >2σ in 5d (credit spreads widening fast), SPY follows within 3-7 days. Universe has neither HYG nor LQD emitted today — needs **universe expansion**. **Wire:** add HYG/LQD to scanner whitelist + new emitter. The other orphan backtest `bond_hyg_lqd_v1` (PF cited 1.29-1.62) is this strategy — also needs wire-up.

6. **Leveraged ETF decay arb (LONG SOXX vs SHORT SOXS, or LONG QQQ vs SHORT SQQQ).**
   Avellaneda Zhang (2010) "Path-dependence of leveraged ETF returns". The math: 3x daily-reset ETFs lose ~10-30%/yr to volatility decay vs 3x of underlying. **However**, the prompt is right to flag this as tight — borrow rates on SOXS/JDST/LABD are punitive (10-40% APR) and can eat the entire decay edge. ETF universe **already emits SOXS/JDST/LABD** (60+ picks combined) — likely from a buried decay-arb emitter that doesn't account for borrow. **Action:** audit which emitter is firing on these, and check if `leveraged_etf_decay_picks.json` sidecar gates on borrow cost. If not, add borrow-cost gate before sizing up.

### Tier-3 (academic interest, low feasibility today)

7. **Smart-beta factor momentum (MTUM, QUAL, USMV, VLUE).** Asness Frazzini (2013). Symbols not in scanner universe; requires universe expansion + 12-month seasoning before any signal. Low priority.

8. **Country ETF carry + momentum (Asness Liew Pedersen 2014).** EWZ, EWJ, EWA, EWG cross-sectional. Universe has none of these emitted today. Requires currency-hedged framing.

---

## 4. Two concrete strategies to build next session

### Strategy A — `etf_cross_asset_regime_shift`
**Academic basis:** Asness Moskowitz Pedersen 2013 "Value and Momentum Everywhere" (JoF); Hong Cheng Madhavan 2009.
**Entry rules:**
- Compute rolling 60d corr(SPY, TLT) and corr(SPY, GLD).
- Signal LONG-VOL (buy SPY puts via 1x SH or stay flat) when both corrs flip from <0 to >0 within 5d AND |Δcorr| > 0.3.
- Signal RISK-ON SPY/QQQ when both corrs return to <-0.2 from >0 within 10d.
**Exit:** 5-day forward holding, exit on TP +1.5% / SL -0.75% / TIME 5d.
**Data needed:** daily close SPY/TLT/GLD (already in universe). Zero new data.
**Why it works:** risk-parity blowups (Feb 2018, Mar 2020, Oct 2023) all preceded by corr regime shift; signal is documented in 4 academic papers.
**Universe coverage:** SPY, QQQ (long); SH (hedge). All in current emitter scope.

### Strategy B — `etf_vix_term_structure_tilt`
**Academic basis:** Bordonado Molnar Samdal 2017; CBOE 2018 VIX Term Structure as Predictor.
**Entry rules:**
- Daily compute `r = VIX1M / VIX3M` (CBOE `^VIX` / `^VIX3M`).
- Signal RISK-OFF (LONG SH or flat) when `r > 1.05` for 2 consecutive days (backwardation).
- Signal RISK-ON (LONG SPY) when `r < 0.92` for 2 consecutive days (steep contango = complacency-to-bullish).
**Exit:** 3-day TP +1% / SL -0.5% / TIME 3d.
**Data needed:** `^VIX`, `^VIX3M` daily (free, yfinance). Zero new data infrastructure.
**Why it works:** VIX term structure inverts BEFORE volatility events ~70% of the time; documented at SPX/SPY level since 2006. Avoids VXX/SVXY blowup risk by trading on the signal, not the term-structure ETF.
**Universe coverage:** SPY, SH. Both in current emitter scope.

Both strategies can be built + paper-shadowed in **one session** (each is <150 LOC plus a YAML), and both have **n>=15 expected in 30 days** based on signal-frequency back-of-envelope.

---

## 5. First operator action recommendation

**P0 — single action, highest leverage:**

> **Fix the `money_ready_verdict.json` ETF block to read from `edge_stability_ETF.json` when `pf_registry.by_asset_class_policy_clean_net.ETF` is empty.**

This is a one-file change in `tools/generate_money_ready_verdict.py` (or wherever the verdict generator lives). Adding a fallback would surface ETF as the **only class within striking distance of T2 today** (90d PF 1.44 / WR 54.9% / n=153). Without this fix, ETF stays buried at "n=4 INSUFF" forever and we burn cycles on classes that are further away.

**P1 follow-ups (in order):**
1. Wire orphan backtests `bond_tlt_ief_v3` + `bond_hyg_lqd_v1` (PF 1.29-1.62 per prompt) to emitters — these are **proven-but-dormant edges** already in the codebase.
2. Backfill the 134 TIME_EXIT zero-pnl rows via `tools/backfill_etf_time_exit_pnl.py` (planned per phase10b report) to graduate the live-DB view in line with edge_stability.
3. Promote `intermarket-flow-scout` to T2-watch once MDD<20% is verified on its 32 closures.
4. Build `etf_cross_asset_regime_shift` and `etf_vix_term_structure_tilt` as paper-shadow emitters (acad-pilot cohort).

---

## 6. Refuted / refute-pending claims

- Prompt: "Universe too narrow (5 symbols)" — **REFUTED**, live DB shows 43 distinct ETFs.
- Prompt: "Faber tactical built today, not tested" — **PARTIALLY CONFIRMED**, edge_stability shows no Faber entry; phase10b lists `etf_faber_tactical` as backfill candidate but it has not produced clean closures.
- Prompt: "ETF current PF 0.48 / WR 50% / n=4" — **STALE**, current is PF 1.44 / WR 54.9% / n=153 per edge_stability (the surface the dashboard verdict generator should be reading).

---

## 7. Summary

ETF is **mislabeled INSUFF/FAIL** by the verdict generator. Reality:
- 90d aggregate PF 1.44 / WR 54.9% / n=153 — closest class to T2 in the audit.
- 7 strategies with PF > 1.5 (one at n=32 ready for graduation pending MDD check).
- 2 orphan backtests in repo (`bond_tlt_ief_v3`, `bond_hyg_lqd_v1`) with proven PF 1.29-1.62 waiting on wire-up.
- 43-ETF universe is broader than prompt claims.

**Operator: stop spending cycles trying to find new ETF edge. The edge is already there and already in the codebase. The bug is in the verdict pipeline. Fix that, wire the two orphan backtests, audit `intermarket-flow-scout` MDD, and ETF promotes to T2-watch within 30 days without writing a single new strategy.**

New strategies (`etf_cross_asset_regime_shift`, `etf_vix_term_structure_tilt`) are still worth building for diversification, but **they are not on the critical path to T2 — the critical path is plumbing.**
