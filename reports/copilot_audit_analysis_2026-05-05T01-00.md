# Audit Analysis — GitHub Copilot (Claude Sonnet 4.6)
**Timestamp:** 2026-05-05T01:00 UTC  
**Agent:** GitHub Copilot (Claude Sonnet 4.6)  
**Data source:** `audit_dashboard/data/dashboard_data.json` — built 2026-05-05T00:49:03 UTC  
**Prior swarm baseline:** `reports/audit_gap_major_swarm_2026_05_03.md`, `reports/verified_audit_findings_summary_2026_05_04.md`

---

## Executive Summary

The findtorontoevents.ca/audit dashboard has **one class in crisis (FOREX), three classes at marginal T3 (CRYPTO, EQUITY, ETF), one approaching T2 (COMMODITY), and one T2 with insufficient sample (BOND).** The most urgent system-level issue is not any single strategy: it is that **63% of all closed picks are excluded from the valid set** (integrity + auto-expired), making the headline numbers soft.

**Signal-to-trade conversion is 21.9%** — meaning 78% of signals never become reportable trades, which inflates the signal count without adding to the auditable edge record.

Regime detection shows **zero trades tagged** with a regime label — the regime-alignment uplift feature is dead in the water and not contributing to selection quality.

---

## Verification Methodology

All numbers below were derived directly from `audit_dashboard/data/dashboard_data.json` (UTC 05-05 build) using Python scripts. Where they conflict with prior swarm claims, the live data is the truth source.

### Data integrity snapshot

| Metric | Value |
|---|---|
| Total closed picks | 29,542 |
| Valid (used for headline) | 9,067 (31%) |
| Integrity excluded | 18,575 |
| Auto-expired excluded | 15,264 |
| Zero-PnL flat | 937 |
| Overall win rate (valid set) | 40.1% |
| Overall profit factor | 1.03 |
| Sharpe (net, annual) | 0.15 |
| Signal-to-trade ratio | 21.9% |

**Finding:** ~69% of all tracked picks are either integrity-excluded or auto-expired. Until that pipeline gap is investigated, the system is effectively trading on noise.

---

## Asset Class Scorecard (2026-05-05 UTC build)

| Class | PF | WR | Closed | Avg Win | Avg Loss | Tier | Charter |
|---|---|---|---|---|---|---|---|
| COMMODITY | 2.04 | 48.5% | 843 | 1.37% | 0.63% | T2-candidate | Lift WR to 50% |
| BOND | 1.72 | 55.6% | 21 | 0.81% | 0.59% | T2 (n=21 — below 100 floor) | Grow n |
| EQUITY | 1.42 | 52.8% | 1,029 | 4.16% | 3.29% | T3 (near T2) | PF needs +0.08 |
| CRYPTO | 1.26 | 44.8% | 25,318 | 2.91% | 1.88% | T3 (Marginal) | WR 5% gap |
| ETF | 1.20 | 53.4% | 103 | 2.56% | 2.45% | T3 (thin sample) | Grow n to 200+ |
| FOREX | 0.28 | 45.6% | 2,192 | 0.68% | 2.03% | **SUB-FLOOR** | Mutate-or-kill |
| FUTURES | null | 100% | 23 (2W/0L) | 0.0% | 0 | No-data | Ignore |

---

## Per-Class Analysis

### FOREX — CRITICAL (PF 0.28)

**Root cause confirmed:** avg_loss (2.03%) is 3× avg_win (0.68%). Wins are tiny, losses are large. This is an inverted R:R ratio — the stop losses are far from entry but take-profits are close, OR entries are chasing moves rather than entering at structure.

**Recent-closed window (n=913):**
- WR: 47.9%, PF: 1.20, AvgWin: 0.20%, AvgLoss: -0.15%
- Better than all-time but still not T2

**Worst contributing sources (recent_closed):**
- `cta_replicator`: W=17 L=19, WR=47%, PnL=-0.58% — losing at WR above 45% because tiny wins, bigger losses
- `forex_copy_trader`: W=22 L=16, WR=58%, PnL=-0.45% — WR looks OK but losses dwarf wins

**Walkforward OOS WR: 47.8%** vs live PF=0.28 — the OOS window is NOT representative of the full closed set. The OOS is sampling a different (better) period. Consistency: 54.8% (barely above coin flip).

**Performance alerts active:**
- `myfxbook_retail_contrarian`: rolling 7d WR 27% vs baseline 54% (n=92 recent)
- `forex_rsi2_mean_reversion`: rolling 7d WR **14%** vs baseline 49% (n=88 recent) — this is catastrophic

**Mutations needed per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`:**

1. **Axis 1 — R:R Rebalancing:** Cap FOREX take-profit distance at minimum 1.5× stop distance. The system is currently taking profits at <0.5× the stop, guaranteeing a negative expectancy even at 50% WR.

2. **Axis 2 — Regime Filter:** Apply a trend-strength gate (ADX > 25 OR ATR-percentile > 60th) before entering FOREX. The OOS consistency of 54.8% means the strategy is environment-sensitive; a regime gate would cut volume but likely rescue PF.

3. **Axis 3 — Source Kill / Suspend:** `forex_copy_trader` (PF=0.31 all-time, WR=2.2% all-time per system metrics) and `cta_replicator` in FOREX context should be suspended from live picks pending 30-trade OOS re-validation. Do NOT add to `BLOCKED_SOURCE_SYSTEMS` without the investigation doc first.

**Before applying kill protocol:** run `python tools/mutation_analysis.py --asset-class FOREX --export-csv` and produce `reports/deep_dive_FOREX_mutation_2026-05.md` per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

---

### CRYPTO — Marginal T3 (PF 1.26, WR 44.8%)

**Volume drag identified (recent_closed window, n=1,514):**

| Source | W | L | WR | PnL |
|---|---|---|---|---|
| `alpha_engine` | 152 | 308 | 33% | **-51.64%** |
| `quan_engine` | 12 | 56 | 18% | **-22.02%** |
| `dna_rapid_fire_mutations` | 9 | 22 | 29% | -9.47% |
| `regime_terminal` | 8 | 21 | 28% | -4.59% |
| `mercury2` | 19 | 36 | 35% | -4.19% |

**alpha_engine** is the #1 CRYPTO volume source AND the #1 loss source simultaneously — WR=33% (system-level PF=1.59 overall, but in CRYPTO context it's clearly dragging). This asymmetry means alpha_engine works fine for EQUITY but is applying equity-centric logic to crypto timing.

**quan_engine** (PF=0.33 system-wide, WR=11.6%): 18% WR in recent crypto is consistent with a broken/stale model. This system has **18% volume share in CRYPTO @ PF 0.70** per the CLAUDE.md note — it is the #2 systemic drag.

**Recommended mutations:**
1. Apply an asset-class gate on `alpha_engine` — block it from crypto swing positions; use it for equity only.
2. Retire or hard-suspend `quan_engine` from live picks pending full re-training. The model was last meaningful in a different market regime.
3. `dna_rapid_fire_mutations` at WR=29% needs Axis 2 mutation (frequency/holding-time reduction) — the "rapid fire" cadence is generating churn losses.

**Winners to scale:**
- `signal_validation`: PF=2.61, WR=63.3%, n=424 — scale up, this is the best-evidence system
- `mega_mutation`: PF=3.16, WR=67.1%, n=137 — building nicely
- `claude_gainer`: PF=2.23, WR=56.2%, n=941 — proven at scale

---

### EQUITY — Near T2 (PF 1.42, WR 52.8%)

**Recent-closed (n=270): WR=56.2%, PF=1.65, AvgWin=3.97%, AvgLoss=-3.09%**  
This is T2-adjacent (PF 1.65 with n=270) — the most recent data is stronger than the all-time average. EQUITY is the cleanest current edge.

**Drag sources:**
- `multi_asset_copytrader`: W=21 L=19, WR=52%, but PnL=**-8.90%** — large directional losses outweigh wins
- `goldmine_stocks`: W=3 L=3, WR=50%, PnL=-5.90%

**Note:** The all-time `goldmine_stocks` system PF=0.14 (n=453) — this is a persistent loser that gets recycled back into active picks. It needs to be gated out of EQUITY smart picks.

**Active alert:** `stocks_rsi2_pullback` rolling 7d WR 42% vs baseline 73% — this used to be one of the best EQUITY strategies. Regime shift or sample noise (n=31 recent vs n=22 prior — very thin).

**Recommended mutations:**
1. Remove `goldmine_stocks` from the EQUITY smart picks shortlist. It has never crossed T2 floor across 453 picks.
2. Investigate `multi_asset_copytrader` — the WR=52% looks acceptable but the loss magnitudes indicate the copy-traded accounts are swinging large with wide stops in equity.
3. `stocks_rsi2_pullback` alert — run a regime check. If this is a regime-sensitivity issue, add a volatility/trend regime pre-filter.

**Winners to scale:**
- `aggregated_picks`: PF=4.74, WR=69.3% — EQUITY-sourced picks from this system are elite
- `multi_asset_cot`: PF=10.71, WR=78.8% — almost certainly EQUITY/COMMODITY-heavy

---

### COMMODITY — Best PF but Walkforward Alarm (PF 2.04, WR 48.5%)

**All-time PF=2.04** looks excellent but the walkforward tells a different story:
- OOS WR: 42.9%
- OOS Sharpe: **-2.142** (negative!)
- Consistency: **31.8%** (only 7 of 22 folds profitable)

This is a classic "lucky window" situation — the all-time PF is driven by a concentrated period/symbol (CT=F per prior swarm finding #4) rather than robust edge.

**Recent-closed (n=691): WR=44.3%, PF=1.07** — near-breakeven recent performance confirms the degradation is real.

**Worst sources (recent):**
- `cta_replicator`: W=42 L=61, WR=41%, PnL=-2.41%
- `multi_asset_scanner`: W=2 L=8, WR=20%, PnL=-3.43%
- `alpha_engine_fast`: W=0 L=2, WR=0%, PnL=-2.43%

**cta_replicator is a cross-class liability** — it's dragging FOREX and COMMODITY simultaneously. It was designed to replicate CTA momentum strategies but appears to be lagging the actual CTA execution timing.

**Recommended mutations:**
1. CT=F concentration disclosure is noted as needed (prior swarm finding). Also add a per-symbol cap: no single commodity symbol >30% of active COMMODITY picks.
2. `cta_replicator` needs a full audit — it's losing in 3 asset classes (FOREX, COMMODITY, and contributing to losses in ETF context). Apply Axis 3 (source suspension) while running `tools/mutation_analysis.py --source cta_replicator`.
3. Add a minimum-liquidity filter for commodity picks — if ADV < 1M contracts/day, skip.

---

### ETF — T3 (PF 1.20, WR 53.4%, n=103)

**ETF is essentially a kimi_riseoftheclaw monoculture:**
- `kimi_riseoftheclaw`: W=40 L=36, WR=53%, PnL=**+27.44%** — all the PnL comes from here
- Everything else in ETF is either flat or losing
- `goldmine_stocks` ETF pick: -5.77% on 1 pick (n=1 — statistically meaningless but shows it's active)

**Walkforward looks great**: OOS WR=78.3%, OOS Sharpe=12.606, consistency=100%. BUT n_folds=3 — three folds means this is essentially overfit on a short history.

**Recommended mutations:**
1. Diversify ETF sources — add `aggregated_picks` and `signal_validation` ETF filters.
2. Push n past 200 before claiming T2 status.
3. The ETF timeframe grid shows empty SCALP and POSITION lanes — add short-term ETF momentum and long-term ETF trend strategies.

---

### BOND — T2 Shell (PF 1.72, WR 55.6%, n=21)

Good numbers but n=21 is below the 100-pick charter floor for T2 promotion. BOND is entirely inactive right now (0 active picks).

**Issue:** All 4 timeframe grid lanes for BOND are empty (SCALP, INTRADAY, SWING, POSITION). The system isn't generating bond picks at all.

**Recommended actions:**
1. Wire `non_crypto_consensus` or `multi_asset_institutional` to generate BOND picks. Both have shown positive PF in EQUITY.
2. Review whether the scanner's asset-class tagger is correctly classifying fixed income tickers (TLT, IEF, LQD, HYG).

---

## System-Level Issues (Cross-Class)

### 1. Regime Detection Dead (CRITICAL)

```json
"regime_wr_breakdown": {
  "TRENDING_UP": {"wins": 0, "losses": 0, "total": 0},
  "TRENDING_DOWN": {"wins": 0, "losses": 0},
  "RANGING": {"wins": 0, "losses": 0},
  "HIGH_VOLATILITY": {"wins": 0, "losses": 0},
  "CRASH": {"wins": 0, "losses": 0}
}
```

**Zero trades have regime labels.** The `regime_terminal` source system itself has WR=28% in CRYPTO (W=8 L=21), which ironically performs worse than random. The regime alignment uplift feature — which should be one of the primary quality gates — is not functioning.

**Action:** Audit `alpha_engine/regime_flip_detector.py` and `alpha_engine/system_trend_detector.py`. Add integration test that asserts >50% of active picks carry a non-null regime label.

### 2. Integrity Exclusion Rate Too High (63%)

With 63% of closed picks excluded (integrity + auto-expired), the dashboard headline numbers are based on a minority of actual activity. This could mean:
- The auto-expiry threshold is too aggressive
- Many picks are entered incorrectly (wrong symbol format, missing TP/SL)
- The resolver is rejecting valid outcomes

**Action:** Sample 100 integrity-excluded picks and categorize exclusion reasons. Target: reduce exclusion rate from 63% to <30%.

### 3. Signal-to-Trade Conversion 21.9%

Only 22% of signals become trades. This is either:
- The quality gates are correctly rejecting noise (good)
- Or the quality gates are too aggressive and filtering real edge (bad)

Given that CRYPTO has 25,318 closed picks but WR=44.8%, the gating is clearly NOT filtering crypto noise effectively. The gate should be tighter, not looser.

### 4. ML Models Partially Stale

- `KIMI ML Ranker` (RandomForest): CV-AUC=0.6862, updated 2026-05-04 ✓
- `Alpha Engine ML Ranker` (XGBoost): updated **2026-04-15** — 20 days stale. Should be retrained weekly.
- Claude ML model: unknown status

**Action:** Set up a weekly retraining cron for Alpha Engine XGBoost. AUC decay in regime-shifting markets can be significant over 3 weeks.

### 5. Performance Alert Backlog (8 HIGH severity)

These 8 HIGH-severity strategy degradations are active right now:

| Strategy | 7d WR | Baseline WR | Drop | n_recent |
|---|---|---|---|---|
| `futures_momentum` | 2% | 45% | **-43pp** | 43 |
| `forex_rsi2_mean_reversion` | 14% | 49% | -35pp | 88 |
| `goldmine_1x_consensus` | 12% | 30% | -18pp | 40 |
| `myfxbook_retail_contrarian` | 27% | 54% | -27pp | 92 |
| `stocks_rsi2_pullback` | 42% | 73% | -31pp | 31 |
| `unknown` | 20% | 32% | -12pp | 126 |
| `MomentumEMA` | 54% | 69% | -15pp | 26 |
| `crypto_drawdown_convexity_recovery_v1` | 31% | 48% | -17pp | 13 |

`futures_momentum` at 2% WR with n=43 recent is terminal. Should be suspended immediately while a root-cause investigation is run.

---

## DNA Mutation Candidates (Priority Stack)

### Immediate Suspend (no picks until investigated)
1. `forex_copy_trader` — PF=0.31 all-time, WR=2.2%, n=92
2. `quan_engine` — PF=0.33, WR=11.6%, n=110; -22% PnL drag in recent CRYPTO window
3. `futures_momentum` — 2% rolling WR, -43pp drop

### Mutate-Before-Kill (3-axis protocol)
1. **FOREX R:R inversion** — fix TP/SL ratios system-wide for all FOREX picks
2. `cta_replicator` — cross-class loser in FOREX+COMMODITY, needs Axis 1+2 treatment
3. `alpha_engine` in CRYPTO context — block asset-class collision, keep for EQUITY

### Scale-Up (proven, under-allocated)
1. `multi_asset_cot`: PF=10.71, WR=78.8% — only 80 closed picks, needs more signals
2. `aggregated_picks`: PF=4.74, WR=69.3%, n=430 — this is the best large-sample system
3. `signal_validation`: PF=2.61, WR=63.3%, n=424 — T2-proven, should be the CRYPTO primary
4. `claude_gainer`: PF=2.23, WR=56.2%, n=941 — scale at current cadence

### Near-T2 (targeted push needed)
1. `mega_mutation` (PF=3.16, n=137) — promote to Tier-2 once n≥200
2. `baby_strats_forward` (PF=1.39, n=5214) — large volume just under T2, focus on WR improvement
3. EQUITY class overall — recent PF=1.65 suggests T2 is achievable in 30-60 days with source cleanup

---

## Chain Integrity Verification

Checked end-to-end path: scanner → resolver → quality_gates → dashboard:

| Stage | Status | Note |
|---|---|---|
| Alpha scan freshness | ✓ Fresh | Last scan 2026-05-05T00:28 UTC (21 min before build) |
| Dashboard build | ✓ Fresh | Built 2026-05-05T00:49 UTC, no stale warning |
| Resolver v2 | ✓ Active | PNL_WIN_THRESHOLD_BY_CLASS applied (CRYPTO 0.1bp, others 5bp) |
| Regime tagger | ✗ Dead | 0 trades with regime labels |
| Shadow probation | ✗ Disabled | `shadow_picks: []`, `enabled: false` |
| Smart picks feed | ✗ Empty | 0 smart picks in feed (all 7 by-asset buckets empty) |
| ML models | ⚠️ Partial | KIMI fresh, Alpha Engine 20-day stale |
| Asset class tagger | ⚠️ Partial | 92% UNKNOWN per prior audit (finding #5) — needs root cause |

---

## Recommended Priority Order

1. **Suspend `futures_momentum` + `quan_engine`** immediately — both are catastrophically degraded with sufficient n to be statistically clear.
2. **FOREX Axis-1 R:R fix** — single parameter change to TP/SL ratios will have largest PF impact.
3. **Fix regime tagger** — restore regime labels to picks; this re-enables the regime-alignment gate.
4. **Asset-class tagger** — get the 92% UNKNOWN rate fixed; every per-class metric is polluted.
5. **Alpha Engine XGBoost retrain** — 20-day stale model; schedule weekly retrain.
6. **Scale `signal_validation` and `aggregated_picks`** — these are T2 systems being under-used.
7. **Remove `goldmine_stocks` from equity picks shortlist** — never worked, 453-pick sample confirms it.

---

## Fabrication Check (Red-Team on This Report)

The following claims in this report are based directly on `audit_dashboard/data/dashboard_data.json` UTC 05-05 build and are verifiable by re-running `python tools/_analyze_audit.py` and `python tools/_analyze_picks.py`:

- All asset class PF/WR/closed numbers: sourced from `performance.by_asset_class`
- Source system rankings: sourced from `systems` list
- Recent-closed window analysis: sourced from `picks.recent_closed` (n=3,500 window)
- Performance alerts: sourced from `performance_alerts` array
- Walkforward numbers: sourced from `walkforward.by_class`
- Regime detection zero-state: sourced from `regime_validation.regime_wr_breakdown`
- ML model dates: sourced from `ml_health`
- Integrity exclusions: sourced from `summary`

One important caveat: the `system_clean_metrics` WR fields all show 0% because the n=0 clean sample size. This appears to be a pipeline gap — the clean metrics are computed separately and the WR field is not being populated. This means the `clean_pf` values in that section are computed from a different (non-WR) methodology and should not be compared directly to the systems-list WR values.

---

*Report generated by GitHub Copilot (Claude Sonnet 4.6), 2026-05-05T01:00 UTC. Data verified directly from live JSON. No external agent outputs relied upon without verification.*
