# Hourly Audit — 2026-05-19 05Z

**Generated:** 2026-05-19T05:10Z  
**Dashboard snapshot:** 2026-05-19T04:40:41Z (auto-refresh via [skip ci] confirmed)  
**Session context:** Post-8-PR merge day (#684, #674, #673, #664, #683, #687, #692, #694)

---

## 1. Dashboard Refresh Status

Dashboard file: `audit_dashboard/data/dashboard_data.json`  
File mtime: 2026-05-19 05:07 UTC (fresh — hourly cron working)  
Data generated_at: 2026-05-19T04:40:41Z  
recent_closed pool: n=3,500

---

## 2. Per-Asset Performance — 24h / 7d / 30d

Computed from `picks.recent_closed`, closed_at timestamps vs dashboard generated_at.

| Class | Window | n | WR% | PF | sumPnL% | Delta vs Baseline |
|-------|--------|---|-----|-----|---------|-------------------|
| CRYPTO | 24h | 246 | 50.8 | 1.156 | +38.6 | ↓ baseline 64% WR / PF 3.54 |
| CRYPTO | 7d | 1013 | 43.5 | 1.025 | +24.9 | ↓ baseline PF 1.33 |
| CRYPTO | 30d | 2900 | 46.1 | 1.264 | +640.6 | ≈ baseline PF 1.33 |
| EQUITY | 24h | 5 | 0.0 | 0.000 | -20.7 | ⚠ n too small |
| EQUITY | 7d | 15 | 13.3 | 0.238 | -40.5 | ↓ worse than issue#693 0.87 |
| EQUITY | 30d | 95 | 50.5 | 1.939 | +126.6 | ↑ recovered vs 14d=1.05 |
| FOREX | 24h | 8 | 37.5 | 1.274 | +1.4 | ↑↑ from 0.00 PF (pre-#687) |
| FOREX | 7d | 19 | 31.6 | 1.315 | +2.3 | ↑↑ from PF 0.14 (issue#686) |
| FOREX | 30d | 93 | 48.4 | 2.543 | +30.0 | ↑↑ far above baseline 0.97 |
| COMMODITY | 24h | 8 | 25.0 | 0.180 | -22.9 | ⚠ cftc_cot bleed (already blocked) |
| COMMODITY | 7d | 23 | 13.0 | 0.193 | -56.3 | ⚠ cftc_cot bleed (see §4) |
| COMMODITY | 30d | 57 | 54.4 | 1.747 | +63.4 | ≈ baseline PF 1.78 |
| BOND | all | 0 | — | — | — | insufficient_data per asset_class_health |
| ETF | 24h | 9 | 11.1 | 1.887 | +11.5 | n too small |
| ETF | 7d | 20 | 25.0 | 0.989 | -0.4 | 7d soft; 30d solid |
| ETF | 30d | 49 | 57.1 | 2.005 | +43.8 | ↑ improving |
| FUTURES | 7d | 1 | 100.0 | inf | +8.7 | n too small |

### Asset Class Health (from `performance.asset_class_health` — rolling window)

| Class | Status | n | WR% | PF | Circuit Breaker |
|-------|--------|---|-----|-----|------------------|
| CRYPTO | stable | 1686 | 45.8 | 1.227 | OK |
| FOREX | stable | 144 | 57.6 | 1.643 | OK (no_backtest) |
| COMMODITY | candidate | 52 | 57.7 | 1.731 | OK |
| EQUITY | insufficient_data | 6 | 33.3 | 0.259 | OK (realized_wr_30d=57.1%) |
| ETF | insufficient_data | 1 | 100.0 | — | OK |
| BOND | insufficient_data | 1 | 0.0 | 0.0 | cold_start |
| FUTURES | thin_sample | 14 | 14.3 | 0.030 | cold_start |

---

## 3. PR Triage

**Open PRs:** `gh pr list --state open` returned **0 open PRs**.

No merges performed. HOLD set (#660 #658 #681 #661 — Plan v2.1 fabricated stats family) is moot — all already closed or not present.

**Author rebase check list** (#669 #676 #608 #665 #644 #597 #615 #655): all confirmed absent from open PR list — previously closed/merged.

---

## 4. New Findings

### FINDING-1: `ensemble` (mercury2/CRYPTO) — Kill Candidate Threshold Met

**Thresholds met:** n=31 in 7d ≥ 20, WR=19.4% < 35%, PF=0.279 < 0.5.

- 7d: n=31, WR=19.4%, PF=0.279, sumPnL=-36.95%
- 30d: n=133, WR=36.8%, PF=0.942, sumPnL=-7.82% (sub-breakeven)
- Source: `mercury2` (not in BLOCKED_SOURCE_SYSTEMS; penalized -10 in score table at quality_gates.py:4914)
- Notable loser symbols: SAHARAUSDT (2× large losses), SHIBUSDT (3× losses), PIXELUSDT (2× losses)
- **Action:** Post to issue #686 for 3-AI consensus. Do NOT add to BLOCKED_ASSET_STRATEGY_PAIRS unilaterally.
- **Pattern match to existing kills:** Similar to `ml_bg_ensemble` (0% WR, already blocked). Directionally consistent.

### FINDING-2: `ig_contrarian_sentiment` LONG direction — Mutation Candidate

From `python tools/mutation_analysis.py`:
- SHORT: WR=60.3%, n=58 — **elite**
- LONG: WR=16.5%, n=200 — **catastrophic**
- Spread: 44pp — largest directional spread in the system

**Action:** Add to BLOCKED_DIRECTION_TRIPLES as `("FOREX", "ig_contrarian_sentiment", "LONG")` or equivalent. This is not a kill — the SHORT side has strong edge. Needs 3-AI consensus per protocol.

### FINDING-3: COMMODITY 7d blowout — Already-Blocked Source Decay

`cftc_cot_commercial_signal` 7d: n=18, WR=5.6%, PF=0.133, sumPnL=-54.76%.

- This strategy is **already in BLOCKED_SOURCE_SYSTEMS** (quality_gates.py:2038, added 2026-05-16).
- The 7d blowout is historical closed picks from before the block. No new action required.
- 30d PF=1.838 confirms the strategy had genuine edge prior to the recent regime break.
- COMMODITY 30d (PF 1.747) remains above T2 floor — class is not at risk.

### FINDING-4: FOREX Major Recovery — PR #687 Effect Confirmed

Pre-#687 (issue #686): FOREX 7d PF=0.14, WR=10.7%, dominated by forex_carry_momentum (WR 1.8%) and forex_rsi2_mean_reversion (WR 10.9%).

Post-#687 (today): FOREX 7d PF=1.315, WR=31.6%. FOREX 30d PF=2.543.

Current 7d FOREX breakdown (n=19):
- `ig_contrarian_sentiment`: n=8, WR=37.5%, PF=1.39
- `unknown`: n=8, WR=37.5%, PF=1.281

The catastrophic strategies (forex_carry_momentum, forex_rsi2_mean_reversion) have zero fresh trades in 7d — confirms PR #692 kill was effective.

### FINDING-5: EQUITY 7d Continuing Decline (Issue #693 Monitor)

Issue #693 documented 30d→14d→7d PF: 2.18→1.05→0.87.

Today: 7d n=15, WR=13.3%, PF=0.238. Worse than prior snapshot.
But: 30d PF=1.939 (improved vs the 2.18→1.05 collapse sequence).

Only 7d strategy with n≥3: `macd-hidden-div-scout` (n=3, WR=0%, sumPnL=-14.82%).

`goldmine_6x_consensus` kill (PR #692) has cleared the 7d window — its trades have aged out. The 7d weakness is now concentrated in `macd-hidden-div-scout`. Sample n=3 is below the kill threshold (need n≥20). **Monitor only per issue #693 recommendation.**

### FINDING-6: CRYPTO `crypto_mtf_ema_slope_alignment_v1` — Watch, Not Kill

- 7d: n=20, WR=25.0%, PF=0.404 — meets n≥20 threshold but 30d PF=1.145 (positive)
- 30d is positive, suggesting a recent regime break rather than structural failure
- Already has a BLOCKED_DIRECTION_TRIPLES entry for SHORTs (quality_gates.py)
- **Action:** Watch. Post as data point in #686. Do NOT add to BLOCKED_ASSET_STRATEGY_PAIRS yet.

---

## 5. Mutation Analysis — Full Output Summary

`python tools/mutation_analysis.py` key outputs:

**Section 1 — Direction flips (WR spread ≥ 24pp):**
| Strategy | SHORT WR | SHORT n | LONG WR | LONG n | Spread |
|----------|----------|---------|---------|--------|--------|
| `ig_contrarian_sentiment` | 60.3% | 58 | 16.5% | 200 | 44pp |
| `myfxbook_retail_contrarian` | 50.0% | 14 | 13.7% | 124 | 36pp |
| `combined_confidence` | 55.6% | 9 | 8.3% | 12 | 47pp |
| `quan_engine_swing` | 60.0% | 5 | 26.0% | 104 | 34pp |
| `forex_rsi2_mean_reversion` | 34.8% | 23 | 6.8% | 117 | 28pp |
| `cta_cross_asset_tsmom` | 53.0% | 168 | 29.4% | 85 | 24pp |

**Section 3 — Symbol variance (worst symbols per system):**
- `cta_replicator`: NG=F (0% WR, n=24), ZC=F (0% WR, n=8) → symbol-block candidates
- `multi_asset_copytrader`: PL=F, GC=F, HG=F (0% WR each) → already partially addressed
- `quan_engine`: HYPEUSDT (WR=41.6%, n=553) — PR #694 symbol-block just merged ✓

---

## 6. Actions Taken This Hour

- Pulled origin/main (forced update confirmed, working tree clean)
- Computed 24h/7d/30d per-asset metrics from fresh dashboard_data.json
- Ran `python tools/mutation_analysis.py` — 2 new directional mutation candidates identified
- 0 PRs merged (no open PRs)
- 2 findings posted to issue #686

---

## 7. Issue Comments Filed

- **Issue #686**: FINDING-1 (`ensemble` kill candidate) + FINDING-2 (`ig_contrarian_sentiment` LONG direction) + FINDING-4 (FOREX recovery) posted for 3-AI consensus

---

## 8. Next-Hour Priorities

1. Watch EQUITY 7d — if `macd-hidden-div-scout` reaches n≥20 in 7d, escalate to mutation analysis
2. Watch `ensemble`/mercury2 — if 3-AI consensus reached, prepare BLOCKED_ASSET_STRATEGY_PAIRS PR
3. CRYPTO 24h PF 1.156 is well below the 3.54 baseline — check if `quan_engine` HYPEUSDT block (PR #694) is propagating into fresh picks
4. `ig_contrarian_sentiment` LONG block — prepare draft PR for review

---

*Audit branch:* `audit/hourly-05z-claude`  
*References:* issue #685 (resolver done), issue #686 (live quality), issue #693 (EQUITY monitor — closed)
