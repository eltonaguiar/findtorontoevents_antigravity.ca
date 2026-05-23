# FUTURES Asset Class Deep-Dive Autopsy
**Date:** 2026-05-18  
**Trigger:** FUTURES PF=0.104, WR=4.7%, n=127 (policy-clean) — below deep-dive threshold per CLAUDE.md  
**Analyst:** Hermes Agent (automated)  
**Data source:** `audit_dashboard/data/pf_registry.json` (generated 2026-05-18T06:32:45Z), `alpha_engine/data/closed_picks.json`

---

## 1. Headline Numbers (pf_registry views)

| View | n | WR% | PF | Sum PnL% |
|------|---|-----|----|----------|
| `by_asset_class_raw` (all closed) | 221 | 3.2% | 0.075 | −559% |
| `by_asset_class` (deduped, no policy) | 127 | 4.7% | 0.110 | −302% |
| `by_asset_class_policy_clean` (deduped + policy) | 12 | 16.7% | 1.010 | +0.17% |
| `by_asset_class_policy_clean_net` (+ slippage) | 12 | 16.7% | 0.956 | −0.79% |

**Key interpretation:** The policy-clean view (n=12) looks superficially near-breakeven, but only because the two primary draining strategies — `futures_momentum` and `multi_asset_copytrader` — were placed into MONITORED mode on 2026-05-18 and are excluded from policy-clean counts. The raw/deduped view (n=127, PF=0.110) is the honest representation of FUTURES' true track record. The context figure of PF=0.104 / WR=4.7% / n=129 from the hourly dashboard aligns with this deduped view.

---

## 2. Per-Source Autopsy

### 2.1 Primary Driver: `futures_momentum` (source_system: `multi_asset_copytrader`)

This is the **catastrophic driver**. The `futures_momentum` strategy is reverse-engineered from `multi_asset_copytrader` signals routed as `source_strategy_type: reverse_engineered_multi_asset`. All 201 FUTURES picks in this cohort share a single source system.

**Aggregate statistics (closed_picks.json, all time):**

| Metric | Value |
|--------|-------|
| n | 201 |
| WR | 2.0% (4 wins / 197 losses) |
| PF | 0.035 |
| Sum PnL | −553.5% |
| Avg PnL per pick | −2.75% |
| Avg loss per SL hit | −2.91% |
| Avg win per TP hit | +5.00% |
| Breakeven WR required | **37.5%** (at 3% SL / 5% TP) |
| Gap below breakeven | **−35.5 percentage points** |

**Structural note:** Every single pick uses an identical 3% SL / 5% TP structure (RR=1.67). The breakeven WR is 37.5%. At the observed 2.0% WR, the mathematical expected value is −2.84% per pick, making the strategy intrinsically unviable — not a tuning problem, but a signal-quality failure.

**Exit reason breakdown:**

| Exit Reason | n | WR% |
|-------------|---|-----|
| `SL_HIT_REPLAY` | 197 | 0.0% |
| `TP_HIT_REPLAY` | 4 | 100.0% |

97.5% of all picks hit the stop loss. This is not noise variance — it is a systematic directional failure.

**Date range:** 2026-04-28 to 2026-05-15 (18 active trading days)

**Direction breakdown:**

| Direction | n | WR% | PF |
|-----------|---|-----|----|
| LONG (BUY) | 147 | 2.0% | 0.036 |
| SHORT (SELL) | 54 | 1.9% | 0.032 |

Both directions are equally catastrophic. There is no viable directional subset.

---

### 2.2 Secondary Strategy: `futures_bb_mean_reversion`

| Metric | Value |
|--------|-------|
| n | 2 |
| WR | 100% (2/2) |
| Sum PnL | +16.9% |
| Symbols | CT=F (Cotton) only |
| Dates | 2026-05-05, 2026-05-12 |

This strategy is in the allowlist (`SMART_PICKS_ALLOWLIST`) with a minimum score of 35. With n=2 on a single symbol, this is statistically insufficient to declare edge. Both wins are SHORT positions on CT=F. No conclusions should be drawn from 2 picks.

---

### 2.3 Active Picks (Not Yet Closed): `futures_connors_rsi2`

As of 2026-05-18, 4 active FUTURES picks exist under `futures_connors_rsi2`:
- ES=F LONG (entry 2026-05-18)
- NQ=F LONG (entry 2026-05-18)
- YM=F LONG (entry 2026-05-18)
- RTY=F LONG (entry 2026-05-18)

This is a distinct strategy from `futures_momentum`. These picks were generated today (the same day as this report), have no closed-pick history in this cohort, and are not present in the pf_registry. **No verdict possible on `futures_connors_rsi2` yet.** It is a new entrant.

---

## 3. Per-Symbol Breakdown (futures_momentum only)

### 3.1 All symbols in FUTURES asset_class

The context referred to CL=F, NG=F, ZC=F. These symbols do **not** appear in the FUTURES asset_class in `closed_picks.json`. They appear instead under COMMODITY (asset_class=COMMODITY), routed through different strategies (`cta_cross_asset_tsmom`, `cta_commodity_momentum_term`). The actual FUTURES picks use soft-commodity futures routed via `multi_asset_copytrader`.

**Full symbol breakdown (futures_momentum, n=201):**

| Symbol | n | WR% | PF | Sum PnL% | Commodity |
|--------|---|-----|----|----------|-----------|
| CT=F | 57 | 0.0% | 0.000 | −169.7% | Cotton |
| SI=F (LONG) | 33 | 3.0% | 0.052 | −91.0% | Silver |
| HG=F | 33 | 0.0% | 0.000 | −87.7% | Copper |
| KC=F | 22 | 4.5% | 0.079 | −58.0% | Coffee |
| ZW=F | 15 | 13.3% | 0.256 | −29.0% | Wheat |
| SI=F (SHORT) | 12 | 0.0% | 0.000 | −36.0% | Silver |
| PL=F (SHORT) | 10 | 0.0% | 0.000 | −30.0% | Platinum |
| GC=F (SHORT) | 10 | 0.0% | 0.000 | −25.2% | Gold |
| PL=F (LONG) | 9 | 0.0% | 0.000 | −26.9% | Platinum |

**Note on CL=F, NG=F, ZC=F (context claim):** These symbols are present in `closed_picks.json` under COMMODITY, not FUTURES. Their stats are:
- CL=F (COMMODITY): n=47, WR=19.1%, PF=0.395, strategy=`cta_cross_asset_tsmom`
- NG=F (COMMODITY): n=25, WR=0.0%, PF=0.000, strategy=`cta_cross_asset_tsmom` / `combined_confidence`
- ZC=F (COMMODITY): n=8, WR=0.0%, PF=0.000, strategy=`cta_commodity_momentum_term`

These are COMMODITY class failures, not FUTURES class failures — they feed into the COMMODITY deep-dive, not this one.

### 3.2 Worst offenders in the FUTURES class

1. **CT=F (Cotton):** 57 picks, 0/57 wins. Largest loss contributor (−169.7%). The strategy consistently fades moves that don't mean-revert.
2. **HG=F (Copper):** 33 picks, 0/33 wins (−87.7%). Complete failure, both directions.
3. **SI=F combined:** 45 picks total, 1 win (2.2%), −127% combined loss.

### 3.3 Symbols with any viability signal

ZW=F (Wheat) is the least bad: n=15, WR=13.3%, PF=0.256. Still 35+ percentage points below breakeven. No viable sub-cohort.

---

## 4. Sub-Cohort Search: Is There Any WR>40% AND n≥20 Subset?

**Answer: NO.**

All symbol × direction combinations were exhausted. The most trades in any single sub-cohort is CT=F LONG (n=57, WR=0.0%). The highest WR in any sub-cohort with n≥15 is ZW=F LONG (n=15, WR=13.3%). No sub-cohort approaches the 37.5% breakeven threshold, let alone 40%.

**By confidence band:**
- All picks share confidence 0.641–0.750 (avg 0.721), elite_score 24–53 (avg 29.6). There is no confidence threshold that separates winners from losers.

**By volume ratio (vol_ratio in `extra` field):**
- Winning picks avg vol_ratio=5.3x vs losing picks avg 8.4x. A vol_ratio<6 filter slightly enriches the win rate but the absolute numbers remain catastrophic (4 wins out of ~70 low-vol picks = ~6%).

**Forward WR:**
- `forward_wr=0.0` on ALL 201 picks. The strategy has never generated a positive forward signal in this time window.

---

## 5. Root Cause Analysis

### 5.1 The signal logic

`futures_momentum` generates trend-following signals: LONG when 20d momentum is positive and price is below 50d SMA, SHORT when momentum is negative. This is a momentum-with-MA-filter strategy.

**Direction-momentum alignment is 100%** (all picks correctly follow the momentum direction), which means the signal is being applied as designed. The catastrophic loss is not a logic bug — it is a market-condition failure.

### 5.2 Why trend-following is failing

The 3%/5% SL/TP structure implies the strategy expects price to continue in the momentum direction by 5% before reversing 3%. With a 2% WR:
- Either these soft-commodity futures are in mean-reverting (not trending) regimes.
- Or the entry timing is systematically wrong (entering near exhaustion, not breakout).

**Evidence:** The `extra.sma_50` vs `entry_price` relationship shows picks are being entered when price is near the SMA — not after a clean momentum breakout. Combined with high vol_ratio (volume spikes), this pattern is consistent with entering on exhaustion spikes rather than clean trend starts.

### 5.3 The classification issue

The symbols in FUTURES (CT=F, SI=F, HG=F, KC=F, ZW=F, PL=F, GC=F) are soft commodities and metals — they belong economically in COMMODITY. Their routing to FUTURES asset_class via `multi_asset_copytrader` creates a classification artifact: the COMMODITY class (which has genuinely positive edge on CT=F under `cftc_cot_commercial_signal`) looks clean, while FUTURES absorbs the catastrophic `futures_momentum` signal.

---

## 6. Hard-Disable vs. Surgical Block Analysis

### Current state (as of 2026-05-18):
Both `futures_momentum` and `multi_asset_copytrader` (in FUTURES) were moved from hard-block to **MONITORED mode** by operator decision on 2026-05-18 (`MONITORED_FUTURES_STRATEGIES` in `quality_gates.py`, lines 2852–2877). Picks are tagged `_monitor_mode=True, _sizing_override=zero` — they pass gates but are not sized for real capital.

### Analysis: Hard-disable vs. surgical block

**Arguments for hard-disable (like FOREX):**
- n=201, WR=2.0%, PF=0.035 — the evidence base is already sufficient to declare no edge. FOREX was hard-disabled at similar metrics.
- 0% WR on CT=F (n=57), HG=F (n=33). These are not sampling noise.
- The theoretical model (momentum trend-following on soft commodities) requires 37.5% WR at current RR. Market conditions would need to change structurally to reach that threshold.
- No sub-cohort (symbol, direction, confidence, vol_ratio) shows WR>15%.

**Arguments for surgical block (per-symbol/strategy):**
- `futures_bb_mean_reversion` (n=2, WR=100%) and `futures_connors_rsi2` (n=4, just opened) are distinct strategies that should not be collaterally blocked.
- The MONITORED mode (current state) allows data accumulation without real capital risk — it threads the needle.
- ZW=F LONG at 13.3% WR is the best single sub-cohort, and it has n=15 — not enough to rule out, not enough to confirm.

**Recommendation (evidence-based, no code changes made):**

The operator should consider two options:

**Option A: Full surgical hard-block on futures_momentum + multi_asset_copytrader/FUTURES** (stronger, like FOREX)
- Evidence: 201 picks, 2% WR, 0% on largest symbols (CT=F, HG=F), symmetric failure across direction. The monitor adds no new information because the signal logic cannot approach breakeven without a regime change that would require its own detection mechanism.
- Risk: If a commodity futures trend regime returns, the strategy cannot self-activate.

**Option B: Continue MONITORED mode with emergency escalation trigger** (current state, more conservative)
- Review at 2026-07-18 per `MONITORED_FUTURES_STRATEGIES.review_date`.
- Add emergency re-block if any 7-day window completes with PF<0.5 (as specified in `escalation_wr_floor=0.10`).
- Risk: 60 more days of data accumulation at 2–3 picks/day = ~120 more tagged picks that go nowhere.

---

## 7. Proposed `BLOCKED_ASSET_STRATEGY_PAIRS` Entries (Evidence Only, Operator Approval Required)

The following entries are supported by the data. **Do NOT add these without operator approval.** The operator must also decide whether to override the 2026-05-18 MONITOR decision.

```python
# futures_momentum: n=201 closed, WR=2.0%, PF=0.035, all symbols affected.
# Breakeven requires 37.5% WR; gap is −35.5pp. No sub-cohort is viable.
# Previously in PERMANENTLY_KILLED_STRATEGIES (2026-05-06) and MONITORED (2026-05-18).
# Evidence: reports/deep_dive_futures_2026_05_18.md §3, §4
("FUTURES", "futures_momentum"),

# multi_asset_copytrader × FUTURES: all 201 futures_momentum picks route through this
# source_system. Blocking at strategy level above is sufficient; this is defense-in-depth.
# Evidence: reports/deep_dive_futures_2026_05_18.md §2.1
("FUTURES", "multi_asset_copytrader"),

# Per-symbol surgical blocks (if operator prefers surgical over full strategy block):
# CT=F × futures_momentum: n=57, WR=0.0%, PF=0.000. Largest loss contributor.
("FUTURES", "futures_momentum", "CT=F"),
# HG=F × futures_momentum: n=33, WR=0.0%, PF=0.000.
("FUTURES", "futures_momentum", "HG=F"),
# SI=F × futures_momentum: n=45, WR=2.2%, PF=0.035. Near-zero edge.
("FUTURES", "futures_momentum", "SI=F"),
# KC=F × futures_momentum: n=22, WR=4.5%, PF=0.079.
("FUTURES", "futures_momentum", "KC=F"),
# PL=F × futures_momentum: n=19, WR=0.0%, PF=0.000.
("FUTURES", "futures_momentum", "PL=F"),
# GC=F × futures_momentum: n=10, WR=0.0%, PF=0.000.
("FUTURES", "futures_momentum", "GC=F"),
```

---

## 8. External Replication Options

The following external benchmarks can be used to validate whether the underlying market has any structural edge, independent of this codebase's signal quality:

| Benchmark | Description | Edge Hypothesis |
|-----------|-------------|-----------------|
| **DBMF (iM DBi Managed Futures ETF)** | Replicates top CTA managers' futures exposure | If DBMF WR>50% over the study window, the market edge exists but this strategy misses it |
| **KMLM (KFA Mount Lucas Managed Futures)** | Trend-following across commodity/financial futures | Direct analog to futures_momentum concept |
| **SocGen CTA Index** | Institutional CTA benchmark | Monthly performance; compare to our window Apr-May 2026 |
| **Barclay CTA Index** | Broader CTA universe | Check if Apr-May 2026 was a negative trend period for CTAs generally |
| **MyFXBook (commodity futures section)** | Live CTA performance | Spot-check if soft commodities (Cotton/Coffee/Wheat) are trending anywhere |

**Preliminary hypothesis:** Apr-May 2026 may be a globally poor period for commodity trend-following (mean-reverting regime). If DBMF/KMLM also show negative returns in this window, the failure is market-condition-driven and the 2026-07-18 review date is appropriate. If DBMF/KMLM are positive, the failure is strategy-specific (signal generation or execution timing).

---

## 9. 30/60/90 Day Rescue Plan

### 30-Day (through 2026-06-18)
- **Do nothing to production code** — MONITOR mode is already in place, zero capital at risk.
- **Log weekly WR** on `futures_momentum` for the monitoring window. Target: any week with WR>10% is notable.
- **Cross-check DBMF/KMLM returns** for Apr-May 2026 to determine if this is market-condition failure or signal failure.
- **Evaluate `futures_bb_mean_reversion`** — if it accumulates 10+ picks at WR>50%, it becomes the viable FUTURES strategy.
- **Evaluate `futures_connors_rsi2`** — the 4 picks opened 2026-05-18 will close within days. Track outcomes.

### 60-Day (through 2026-07-18)
- **Scheduled review** per `MONITORED_FUTURES_STRATEGIES.review_date`.
- **Decision gate:** if WR remains <10% over monitoring window (escalation_wr_floor=0.10), hard-block both strategies and remove from MONITORED.
- **Signal redesign option:** If market-condition hypothesis is confirmed, build a regime detector (COT commercial net positioning on soft commodities as a regime filter) that activates `futures_momentum` only in trending regimes. Reference: `multi_asset_cot` pipeline for COT data sourcing.
- **Symbol reclassification:** Consider reclassifying CT=F, SI=F, HG=F, KC=F picks under COMMODITY when routed through `multi_asset_copytrader`. This would expose the true COMMODITY contamination and allow CT=F's genuine edge (via `cftc_cot_commercial_signal`, WR=85%, n=234) to be properly tracked.

### 90-Day (through 2026-08-18)
- If 60-day review re-blocks both strategies: **close FUTURES chapter** — remove from MONITORED, add to PERMANENTLY_KILLED_STRATEGIES, update dashboard to show FUTURES as NOT_READY with a tombstone explanation.
- If regime detector is built and validated: **paper-trade futures_momentum with COT filter** on a 30-day paper window before considering live.
- If `futures_bb_mean_reversion` or `futures_connors_rsi2` reach n=30 with WR>50%: **promote to paper-live** with zero-sized picks and alert on 7-day WR degradation.

---

## 10. Risk Register

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| MONITORED picks accidentally sized for real capital | CRITICAL | Low (code enforces `_sizing_override=zero`) | Verify `is_futures_monitored()` check in pick-sizing path |
| `futures_connors_rsi2` (ES/NQ/YM/RTY=F) has no historical track record | HIGH | Medium (new strategy, no closed picks) | Do not size until n≥30 with WR≥50%; add to REQUIRES_WALKAHEAD_AUDIT |
| Symbol classification bleed (CT=F appears in both FUTURES and COMMODITY) | MEDIUM | Confirmed | See §5.3; audit dashboard may double-count CT=F picks |
| Market regime recovers, FUTURES stays blocked | MEDIUM | Medium | 2026-07-18 review date addresses this; DBMF cross-check is leading indicator |
| `futures_bb_mean_reversion` (n=2) gets promoted prematurely | MEDIUM | Low | Minimum n=10 before any promotion decision |

---

## 11. Acceptance Criteria for FUTURES Graduation to MONEY_READY

Per CLAUDE.md Tier 2 minimum (PF>1.5 / WR>50% / MDD<20%):

| Criterion | Required | Current |
|-----------|----------|---------|
| n (clean, post-noise-filter) | ≥100 | 12 (policy-clean) |
| WR | ≥50% | 4.7% (deduped, all) |
| PF | ≥1.5 | 0.110 (deduped, all) |
| MDD | <20% | Not computed (all picks are forward_test_only) |
| Clean source (no forward_test_only) | Required | 0/203 picks have forward_test_only=False |
| At least 1 viable strategy with n≥50 | Required | 0 strategies meet this bar |

**Verdict: FUTURES is NOT_READY. The gap to Tier 2 is not a tuning gap — it is a structural absence of edge in the current active strategy set.**

---

## 12. Data Sources and Reproducers

```bash
# Run these from repo root to reproduce key numbers

# FUTURES by strategy (raw)
python -c "
import json; from collections import defaultdict
picks = json.load(open('alpha_engine/data/closed_picks.json'))
futures = [p for p in picks if p.get('asset_class')=='FUTURES']
by_s = defaultdict(list)
for p in futures: by_s[p.get('strategy')].append(p)
for s,ps in by_s.items():
    wins=sum(1 for p in ps if (p.get('pnl_pct') or 0)>0)
    print(f'{s}: n={len(ps)}, WR={wins/len(ps)*100:.1f}%, pnl={sum((p.get(\"pnl_pct\") or 0) for p in ps):.4f}')
"

# FUTURES by symbol (futures_momentum only)
python -c "
import json; from collections import defaultdict
picks = json.load(open('alpha_engine/data/closed_picks.json'))
fm = [p for p in picks if p.get('asset_class')=='FUTURES' and p.get('strategy')=='futures_momentum']
by_s = defaultdict(list)
for p in fm: by_s[p.get('symbol')].append(p)
for s,ps in sorted(by_s.items(), key=lambda x: -len(x[1])):
    wins=sum(1 for p in ps if (p.get('pnl_pct') or 0)>0)
    print(f'{s}: n={len(ps)}, WR={wins/len(ps)*100:.1f}%')
"

# pf_registry FUTURES views
python -c "
import json
pf = json.load(open('audit_dashboard/data/pf_registry.json'))
for key in ['by_asset_class_raw','by_asset_class','by_asset_class_policy_clean','by_asset_class_policy_clean_net']:
    for item in pf[key]:
        if item.get('asset_class')=='FUTURES':
            print(f'{key}: n={item[\"n\"]}, WR={item[\"win_rate_pct\"]:.1f}%, PF={item[\"profit_factor\"]}')
"
```

---

*Report generated: 2026-05-18. Operator approval required before any changes to `BLOCKED_ASSET_STRATEGY_PAIRS` or `PERMANENTLY_KILLED_STRATEGIES`.*
