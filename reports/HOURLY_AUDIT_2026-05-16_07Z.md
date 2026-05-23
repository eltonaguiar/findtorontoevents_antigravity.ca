# Hourly Audit — 2026-05-16 07Z

**Generated:** 2026-05-16T07:xx UTC  
**Dashboard snapshot:** 2026-05-16T06:07:50Z (fresh, ~1h lag)  
**Auditor:** Claude Sonnet 4.6 (Claude Code)  
**Session priority:** Goal #1 (audit performance)

---

## 1. Dashboard Refresh Status

- Pull from origin/main: **16 data files updated** (incubator_picks, kalshi_signals, polymarket_signals, prediction_market picks/whales, scheduled_pick_check, copy_trader_intel, prediction_market_agents data, strategy_prover_results)
- Dashboard JSON generated at `2026-05-16T06:07:50Z` — fresh, within 1h SLA
- No schema errors detected; `asset_class_health` n counts valid except COMMODITY (n=0 anomaly — pipeline classification issue, carries over from 06Z)

---

## 2. Per-Asset Windowed Metrics (computed from `picks.recent_closed`, n=3481 with timestamps)

| Class | 24h n | 24h PF | 24h WR | 7d n | 7d PF | 7d WR | 30d n | 30d PF | 30d WR | Long-run PF (asset_class_health) |
|---|---|---|---|---|---|---|---|---|---|---|
| **CRYPTO** | 95 | **0.81** | 33.7% | 759 | 1.262 | 44.0% | 2808 | 1.292 | 46.0% | 1.35 / n=7554 |
| **EQUITY** | 4 | 0.049 | 25.0% | 26 | 0.75 | 19.2% | 102 | 2.587 | 54.9% | 1.65 / n=393 |
| **FOREX** | 9 | 1.22 | 33.3% | 26 | **1.597** | 19.2% | 48 | 2.297 | 33.3% | 0.85 / n=251 |
| **COMMODITY** | 5 | 0.465 | 20.0% | 27 | 0.638 | 29.6% | 65 | 1.974 | 56.9% | N/A (n=0 anomaly) |
| **ETF** | 2 | N/A | 0.0% | 13 | 0.656 | 46.2% | 49 | 2.547 | 71.4% | 2.25 / n=75 |
| **BOND** | 0 | N/A | N/A | 0 | N/A | N/A | 0 | N/A | N/A | 0.66 / n=11 |
| **FUTURES** | 0 | N/A | N/A | 1 | N/A | 100% | 2 | N/A | 100% | N/A / n=2 |

*FOREX 7d WR=19.2% with PF=1.597: low win-count but asymmetric win/loss (few large winners). Plausible trend-following regime on small n=26 sample — not a contradiction.*

---

## 3. Deltas vs CLAUDE.md Baselines

| Class | Metric | Baseline | Now | Delta | Status |
|---|---|---|---|---|---|
| CRYPTO | 24h PF | 3.54 | **0.81** | -2.73 | ALERT: 3rd consecutive sub-1.0 24h cycle |
| CRYPTO | 7d PF | 1.33 | 1.262 | -0.07 | Stable, minor drift |
| CRYPTO | 30d PF | 1.33 | 1.292 | -0.04 | Stable, minor drift |
| EQUITY | 7d PF | 0.87 | 0.75 | -0.12 | Declining (watch, below n>=20 kill gate) |
| EQUITY | 30d PF | 1.41-2.18 | **2.587** | +0.37 to +1.18 | T1 zone, structural edge intact |
| FOREX | 7d PF | 0.14 (pre-#687) | **1.597** | +1.46 | PRs #687+#692 confirmed effective |
| FOREX | 30d PF | 0.97 (pre-#687) | **2.297** | +1.33 | T1 zone, recovering |
| COMMODITY | 30d PF | 1.78 | 1.974 | +0.19 | T2 confirmed, n=0 anomaly in long-run health (pipeline issue) |
| ETF | Long-run PF | 1.24 | **2.25** | +1.01 | T1 zone |

---

## 4. CRYPTO 24h Alert — 3rd Consecutive Sub-1.0 Cycle

| Cycle | 24h PF |
|---|---|
| 05Z | 0.86 |
| 06Z | 0.832 |
| **07Z** | **0.81** |

**Alert gate triggers at 3 consecutive cycles.** 7d PF (1.262) and 30d PF (1.292) remain above 1.0 and stable, indicating this is regime-driven short-term weakness, not structural degradation. 24h n=95 includes all current active strategies; no single outlier identified in hourly breakdown (14:00Z batch: 62 CRYPTO closes at 25.8% WR was the bulk driver, likely a correlated market flush).

**Recommended action:** Monitor-only at 08Z cycle. If 24h PF remains sub-1.0 at 08Z (4th consecutive), post to issue #686 for strategy-attribution deep-dive. Do NOT kill strategies based on 24h data alone.

---

## 5. 30d Tier Status (Goal #1 scorecard)

| Class | 30d PF | 30d WR | Tier Status |
|---|---|---|---|
| EQUITY | 2.587 | 54.9% | T1 (PF>2 / WR>55) |
| ETF | 2.547 | 71.4% | T1 |
| FOREX | 2.297 | 33.3% | T1 PF (WR low due to small n=48; sizing still OFF per CLAUDE.md) |
| COMMODITY | 1.974 | 56.9% | T2 |
| CRYPTO | 1.292 | 46.0% | sub-T2 (PF target >1.5 / WR target >50) |
| BOND | unclear | N/A | n=0 in 30d window, n=11 long-run |

**Progress:** EQUITY and ETF hit T1 criteria. COMMODITY solid T2. FOREX 30d PF in T1 range but WR=33.3% on n=48 is too small to confirm — maintain sizing-off.

---

## 6. PR Triage

### Open PRs
Only 2 open PRs exist in the queue (confirmed via list_pull_requests pages 1+2):
- **#1101** — audit/hourly-06z-v2 audit tracking PR (prior cycle). No CI required; informational.
- **#1100** — audit/hourly-05z audit tracking PR (prior cycle). No CI required; informational.

**Merges this cycle: 0** — queue is clean.

### HOLD Set Status
| PR | Title | State | Notes |
|---|---|---|---|
| #660 | P0 Emergency Gate Fixes (Plan v2.1) | MERGED 2026-05-03 | HOLD violation (pre-existing). Config changes orphan-consumed; hf_quality_gates.json enabled:false effectively neutered impact. Flagged by 06Z audit. |
| #658 | Comprehensive Audit (Plan v2.1) | Closed (not merged) | Safe. |
| #681 | Strategy Decay Guard | Closed (not merged) | Safe. |
| #661 | Infrastructure v2.0 (Plan v2.1) | MERGED 2026-05-03 | HOLD violation (pre-existing). New modules are callers-absent (Wire-Up Rule violation); orphan modules, no production path impact. Flagged by 06Z audit. |

Cannot reverse past merges. Operator should review alpha_engine/track_calculator.py, alpha_engine/statistical_rigor.py, alpha_engine/decay_tracker.py for any active callers that could alter production scoring.

### Rebase Candidate PRs (#669 #676 #608 #665 #644 #597 #615 #655)
All closed (confirmed by empty page-2 PR list). No action required.

---

## 7. New Mutation Analysis Findings

Ran `python tools/mutation_analysis.py --json`. New finding vs 06Z carried list:

### NEW: forex_rsi2_mean_reversion LONG direction (kill candidate)

| Criterion | Value | Gate |
|---|---|---|
| n (LONG direction) | **108** | >= 20 |
| WR (LONG direction) | **7.4%** | < 35% |
| Pattern match | FOREX strategy, same class as #692 forex_carry_momentum kill | Matches |

All 3 kill criteria met. forex_rsi2_mean_reversion SHORT has WR=34.8% on n=23 (viable).

**Action: Posted to issue #686 for 3-AI consensus before adding to BLOCKED_ASSET_STRATEGY_PAIRS.**
Proposed block: ("FOREX", "forex_rsi2_mean_reversion", "LONG") — direction-specific, not full strategy kill.

### Carried from 06Z (pending 3-AI consensus, no change)

| Candidate | Type | n | WR | Notes |
|---|---|---|---|---|
| (CRYPTO, ensemble) | strategy | 41 | 24.4% | Symbol-allowlist mutation preferred over full block |
| (rapid_fire, UUSDT) | symbol block | 34 | 0% | Meets all criteria |
| (cta_replicator, NG=F) | symbol block | 24 | 0% | Meets all criteria |
| (ig_contrarian_sentiment, LONG) | direction restrict | 197 | 16.8% | Meets all criteria |
| (myfxbook_retail_contrarian, LONG) | direction restrict | 123 | 13.8% | Meets all criteria |

### New candidates below kill gate (monitor only)
- (quan_engine_swing, LONG) — n=104 WR=26% — WR<35% but need PF check; add to watchlist
- (cta_cross_asset_tsmom, LONG) — n=84 WR=29.8% — watch for further decay

---

## 8. Issue #685 / #693 Status

- **#685** (resolver-rescope obsolete): Confirmed done. No new PRs claiming 'widen re-resolve scope' in queue.
- **#693** (EQUITY 7d/14d/30d divergence): Closed 2026-05-13. Post-#692 goldmine_6x kill still working through 7d window. EQUITY 7d PF=0.75 vs baseline 0.87 — slight further decline. 30d PF=2.587 strong. Monitor at 14d window next.

---

## 9. Actions Taken This Cycle

1. Pulled latest main (16 files updated)
2. Computed per-asset 24h/7d/30d windowed metrics
3. Verified HOLD set states (#660+#661 merged pre-cycle, cannot reverse)
4. Confirmed rebase candidates all closed
5. Ran mutation_analysis.py — identified 1 new kill candidate
6. Posted new kill candidate to issue #686 (forex_rsi2_mean_reversion LONG)
7. CRYPTO 24h alert gate triggered (3rd consecutive) — documented

---

## 10. Next Cycle Guidance (08Z)

- **Priority check**: CRYPTO 24h PF — if 4th consecutive sub-1.0, open strategy-attribution deep-dive on issue #686
- **EQUITY 7d**: If drops below 0.60, run mutation analysis on stocks_rsi2_pullback (currently WR=19.2% on 7d window, n=26 — close to kill threshold)
- **COMMODITY 7d PF=0.638**: 3rd straight weak 7d reading. 30d=1.974 (T2) protects. If 7d PF <0.5 at 08Z, run attribution on active COMMODITY strategies.
- **forex_rsi2_mean_reversion LONG**: Await 2 more AI voices on #686 before adding to BLOCKED list

---

_Generated by Claude Sonnet 4.6 (Claude Code) — 2026-05-16T07Z_
