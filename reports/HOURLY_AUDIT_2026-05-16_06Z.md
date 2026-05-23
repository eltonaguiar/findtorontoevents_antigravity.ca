# Hourly Audit — 2026-05-16 06Z

**Generated:** 2026-05-16T06:13Z  
**Dashboard snapshot:** 2026-05-16T05:24:41Z (payload_lag ~49min, fresh)  
**Main SHA:** 4ca7fd2a  
**Context:** Issues #685 (resolver-rescope DONE), #686 (per-asset attribution), #693 (EQUITY divergence — CLOSED 2026-05-13)

---

## 1. Dashboard Refresh Status

- Pulled from origin/main: 3 files changed (gainer_capture_picks.json, gainer_portfolio_state.json, gha-hourly-monitor)
- Dashboard generated_at: `2026-05-16T05:24:41Z` — fresh, within 1h
- GHA status: DEGRADED (unchanged per `updates/gha-hourly-monitor-2026-05-16.md`)

---

## 2. Long-Run Asset Class Health (asset_class_health)

Source: `performance.asset_class_health` in dashboard_data.json (2026-05-16T05:24Z)

| Class | PF | WR% | n | Status | Delta vs CLAUDE.md baseline | Delta vs 05Z |
|---|---|---|---|---|---|---|
| CRYPTO | **1.35** | 47.2% | 7,565 | stable | +0.10 | +0.04 |
| EQUITY | **1.65** | 53.2% | 393 | stable | +0.24 | +0.09 |
| FOREX | **0.85** | 57.8% | 251 | watch (sizing OFF) | +0.58 | -0.01 |
| ETF | **2.25** | 66.7% | 75 | candidate | +1.01 | +0.93 |
| COMMODITY | n/a | 0.0% | **0** | insufficient_data | WARN DROP from 2.57 (05Z) | significant |
| BOND | 0.66 | 54.5% | 11 | thin_sample | — | — |
| FUTURES | n/a | 100% | 2 | insufficient_data | — | — |

### WARN: COMMODITY n=0 anomaly
Previous 05Z audit reported COMMODITY PF=2.57 (long-run). Now shows n=0 / insufficient_data. The windowed analysis (30d from picks) confirms COMMODITY picks *do* exist (n=65, PF=1.974). This is a pipeline/display issue — the `asset_class_health` resolver may have dropped COMMODITY into a different classification bucket. Monitor; do not treat as a performance regression. 7d and 30d picks-based metrics remain valid.

---

## 3. Windowed Per-Asset Metrics (computed from picks.recent_closed)

Source: `picks.recent_closed` (n=3500), computed vs dashboard generated_at (05:24Z)

### 24h Window

| Class | n | WR% | PF | Sum PnL% | Status |
|---|---|---|---|---|---|
| CRYPTO | 100 | 34.0% | **0.832** | -24.44% | SUB-1 (2nd+ consecutive cycle) |
| EQUITY | 4 | 25.0% | 0.049 | -3.64% | n<10 ignore |
| FOREX | 9 | 33.3% | **1.22** | +1.18% | recovering |
| COMMODITY | 5 | 20.0% | 0.465 | -9.67% | n<10 ignore |
| ETF | 2 | 0.0% | 0.0 | -12.07% | n<10 ignore |

### 7d Window

| Class | n | WR% | PF | Sum PnL% | Delta vs baseline | Status |
|---|---|---|---|---|---|---|
| CRYPTO | 770 | 43.9% | **1.264** | +189.33% | stable | above T2 floor |
| EQUITY | 26 | 19.2% | **0.75** | -9.04% | -0.12 vs 0.87 | still declining |
| FOREX | 26 | 19.2% | **1.597** | +3.65% | +1.457 vs 0.14 | PRs #687/#692 confirmed |
| COMMODITY | 27 | 29.6% | **0.638** | -24.33% | n/a | cot tail closes (PR #683) |
| ETF | 13 | 46.2% | **0.656** | -7.14% | n/a | weak 7d, strong 30d |
| FUTURES | 1 | 100% | inf | +8.70% | n<10 ignore | — |

### 30d Window

| Class | n | WR% | PF | Sum PnL% | Tier |
|---|---|---|---|---|---|
| CRYPTO | 2,824 | 45.9% | **1.287** | +700.53% | sub-T2 |
| EQUITY | 102 | 54.9% | **2.587** | +195.67% | **T1** |
| FOREX | 48 | 33.3% | **2.297** | +16.47% | T1 zone |
| COMMODITY | 65 | 56.9% | **1.974** | +88.85% | **T2** |
| ETF | 49 | 71.4% | **2.547** | +52.80% | **T1** |
| FUTURES | 2 | 100% | inf | +16.89% | insufficient n |

---

## 4. Delta Table vs CLAUDE.md Documented Baselines

| Class | Window | Baseline PF | Current PF | Delta | Notes |
|---|---|---|---|---|---|
| CRYPTO | 24h | 3.54 | 0.832 | **-2.71** | ALERT: 2nd+ consecutive sub-1.0. 3-cycle gate approaching |
| CRYPTO | 7d | 1.33 | 1.264 | -0.07 | Minor drift, within noise |
| CRYPTO | 30d | 1.33 | 1.287 | -0.04 | Stable |
| EQUITY | 7d | 0.87 | 0.750 | -0.12 | Continuing decline |
| EQUITY | 30d | 2.18 | 2.587 | +0.41 | T1 confirmed |
| FOREX | 7d | 0.14 | 1.597 | **+1.46** | PRs #687+#692 confirmed |
| FOREX | 30d | 0.97 | 2.297 | +1.33 | T1 zone |

---

## 5. Strategy Attribution — 7d Worst Drags

Source: picks.recent_closed last 7d

| Strategy | Class | n | WR% | PF | Sum PnL% | Kill Protocol Status |
|---|---|---|---|---|---|---|
| `ensemble` | CRYPTO | 41 | 24.4% | 0.435 | -32.54% | Meets n>=20 + WR<35% + PF<0.5. 05Z flagged to issue #686. Score penalty -10 in place. Symbol-allowlist mutation recommended. Awaiting 3-AI consensus (voice 1: Claude Sonnet 4.6) |
| `cot_positioning` | COMMODITY | 14 | 35.7% | 0.619 | -15.01% | n<20 — monitor only |
| `macd-hidden-div-scout` | EQUITY/ETF | 3 | 0.0% | 0.0 | -9.83% | n<10 — ignore |
| `cftc_cot_commercial_signal` | COMMODITY | 13 | 23.1% | 0.666 | -9.32% | n<20 — monitor only |
| `price-accel-scout` | EQUITY | 2 | 0.0% | 0.0 | -8.45% | n<10 — ignore |
| `drawdown_recovery_rsi_sol` | CRYPTO | 7 | 0.0% | 0.0 | -7.00% | n<20 — monitor |
| `rs-breakout-scout` | EQUITY/ETF | 5 | 40.0% | 0.436 | -7.00% | n<10 — ignore |

**Best 7d performers:**
- `luxalgo_confluence` [CRYPTO]: n=177, WR=51.4%, PF=1.339, +71.62%
- `macd_rsi_m048` [CRYPTO]: n=14, WR=57.1%, PF=3.078, +34.85%
- `claude_ml_moderate_mut` [CRYPTO]: n=19, WR=57.9%, PF=2.065, +17.30%

---

## 6. Mutation Analysis (python tools/mutation_analysis.py --json)

### Direction-flip candidates (pending 3-AI consensus — carried from prior audits)

| Strategy | Direction | n | WR | SHORT WR | Spread | Action |
|---|---|---|---|---|---|---|
| `ig_contrarian_sentiment` | LONG | 197 | 16.8% | 61.4% (n=57) | 45pp | Sandbox SHORT-only |
| `myfxbook_retail_contrarian` | LONG | 123 | 13.8% | 50.0% (n=14) | 36pp | Sandbox SHORT-only |
| `quan_engine_swing` | LONG | 104 | 26.0% | 60.0% (n=5) | 34pp | Watch |
| `cta_cross_asset_tsmom` | LONG | 84 | 29.8% | 52.4% (n=164) | 23pp | Watch |
| `forex_rsi2_mean_reversion` | LONG | 108 | 7.4% | 34.8% (n=23) | 27pp | Watch |

All LONG arms flagged as avg_pnl -0.00%; all SHORT arms positive or break-even. Per CLAUDE.md kill protocol: need 3+ AI consensus before adding to BLOCKED_ASSET_STRATEGY_PAIRS.

### Symbol-variance candidates (pending 3-AI consensus — carried)

| System | Symbol | WR | n | Notes |
|---|---|---|---|---|
| `rapid_fire` | UUSDT | 0.0% | 34 | Meets all criteria (n>=20, WR<35%, pattern match). |
| `cta_replicator` | NG=F | 0.0% | 24 | Meets criteria. CL=F borderline (WR 19.1%, n=47). |
| `quan_engine` | HYPEUSDT | 41.6% | 553 | Already blocked PR #694. |

### New from this 06Z run
None above the kill gate not already flagged in prior audits. Ensemble (CRYPTO) is the primary active candidate.

---

## 7. CRYPTO 24h Alert Assessment

| Cycle | 24h PF | Status |
|---|---|---|
| 05Z | 0.86 | sub-1.0 (prior audit) |
| 06Z (now) | **0.832** | sub-1.0 (2nd consecutive) |

Three-consecutive-cycle gate requires one more sub-1.0 reading. 7d PF=1.264 and 30d PF=1.287 remain stable. Do not act. Flag at 07Z if PF remains below 1.0.

---

## 8. PR Triage

### Open PRs
- **#1100** (`audit/hourly-05z`): Previous hourly audit tracking PR. No action needed.

### Triage-list PRs (per task instruction)
All 8 triage-list PRs are already resolved:

| PR | Status |
|---|---|
| #669 | Merged 2026-05-02 |
| #676 | Merged 2026-05-03 |
| #608 | Merged 2026-05-03 |
| #665 | Merged 2026-05-02 |
| #644 | Merged 2026-05-03 |
| #597 | Merged 2026-05-03 |
| #615 | Merged 2026-05-03 |
| #655 | Closed without merge 2026-05-03 |

### HOLD set status (VIOLATIONS FOUND)

| PR | Expected | Actual |
|---|---|---|
| #660 | NEVER MERGE | **MERGED 2026-05-03T21:55Z** — Plan v2.1 fabricated stats |
| #658 | NEVER MERGE | Closed without merge 2026-05-03 |
| #681 | NEVER MERGE | Closed without merge 2026-05-03 |
| #661 | NEVER MERGE | **MERGED 2026-05-03T21:53Z** — Plan v2.1 infrastructure modules |

Flag: #660 (emergency gate fixes citing Plan v2.1 stats) and #661 (track_calculator/statistical_rigor/decay_tracker from Plan v2.1 family) were merged despite HOLD. Cannot reverse. Impact:
- #660 introduced `config/per_asset_thresholds.json` + modified `config/hf_quality_gates.json` with Plan v2.1 thresholds.
- #661 added `alpha_engine/track_calculator.py`, `statistical_rigor.py`, `decay_tracker.py` — orphan modules (Wire-Up Rule not met, no production callers).
- Recommend operator audit of `config/hf_quality_gates.json` for any enabled:true thresholds from #660.

### Merged this cycle: 0 (PR queue was already clean)

---

## 9. Kill Candidates in 3-AI Pending State (no changes this cycle)

1. `(CRYPTO, ensemble)` — symbol-allowlist mutation (posted 05Z, voice 1)
2. `(rapid_fire, UUSDT)` — symbol block (posted 07Z 2026-05-15, voice 1)
3. `(cta_replicator, NG=F)` — symbol block (posted 07Z 2026-05-15, voice 1)
4. Direction-restrict: `ig_contrarian_sentiment` LONG, `myfxbook_retail_contrarian` LONG (posted 06Z-07Z 2026-05-15, voice 1)

None have reached 3-AI consensus. No BLOCKED list changes made this cycle.

---

## 10. Issue Cross-Reference

| Issue | Status | This cycle |
|---|---|---|
| #685 (resolver-rescope) | OPEN — DONE per body | No action needed |
| #686 (per-asset attribution) | OPEN | 05Z comment already posted; no new comment this cycle |
| #693 (EQUITY divergence) | CLOSED 2026-05-13 | Confirmed: EQUITY 30d PF=2.587 (T1). goldmine_6x kill was sufficient. |

---

## 11. Summary

| Item | Finding |
|---|---|
| Dashboard refresh | Fresh (05:24Z) |
| PRs merged | 0 (queue clean) |
| HOLD violations | #660 + #661 were merged 2026-05-03 (cannot reverse, flag for operator) |
| New kill candidates | 0 new this cycle |
| CRYPTO 24h | PF=0.832 (2nd sub-1.0 cycle); 7d/30d stable |
| EQUITY 7d | PF=0.75 (declining); 30d PF=2.587 (T1 intact) |
| FOREX | 7d PF=1.597 (+1.46 vs baseline 0.14) — PRs #687+#692 confirmed |
| COMMODITY 7d | PF=0.638 (cot tail closes); 30d PF=1.974 (T2) |
| ETF | Long-run PF=2.25 (T1 zone), n=75 |

**Next cycle (07Z):** If CRYPTO 24h PF remains <1.0, trigger 3-consecutive alert and run source attribution. Watch EQUITY 7d for recovery signal post-#692.

---

_Generated by Claude Sonnet 4.6 (Claude Code) — 2026-05-16T06:13Z_  
_Refs: issues #685, #686, #693 | dashboard generated_at 2026-05-16T05:24:41Z_
