# Hourly Audit — 2026-05-21 17Z

**Generated:** 2026-05-21T17:10Z  
**Dashboard snapshot:** `2026-05-21T12:18:29Z` — 5th consecutive stale hour (13Z–17Z same cron). Next refresh expected ~17Z–18Z.  
**Refs:** issues #685 #686 #693 | baseline: issue #686 initial snapshot 2026-05-02

---

## 1. Dashboard Refresh Status

Dashboard has **not refreshed** since 12:18Z (confirmed: `meta` field empty, COMMODITY sample pick `closed_at` matches earlier cron). All per-asset numbers below are from the same snapshot as 13Z–16Z audits. Pending cron expected ~17–18Z; next audit should catch the refresh.

---

## 2. Per-Asset Health (asset_class_health — authoritative pre-computed)

| Class | PF | WR% | n | 30d WR% | Status | Sizing | vs Baseline |
|-------|-----|-----|---|---------|--------|--------|-------------|
| CRYPTO | 1.356 | 48.1% | 1054 | 45.9% | stable | ✅ allowed | PF in range (baseline 7d 1.33) |
| EQUITY | 0.703 | 35.7% | 56 | 48.6% | candidate | ❌ blocked | ⚠️ PF below 1.0; circuit_breaker OK |
| FOREX | **2.900** | **54.9%** | 153 | 58.2% | stable | ✅ allowed | ✅ Dramatic recovery (baseline 7d 0.14 pre-#687) |
| COMMODITY | 1.422 | 52.5% | 59 | 41.6% | candidate | ❌ blocked | Within baseline range |
| ETF | 11.995 | 50.0% | 2 | 59.6% | insufficient | ❌ blocked | n=2 (meaningless PF) |
| BOND | 0.000 | 0.0% | 6 | — | insufficient | ❌ blocked | Cold start |
| FUTURES | 0.956 | 16.7% | 12 | 100% (n=2) | thin_sample | ❌ blocked | Monitor |
| PENNY_STOCK | 0.000 | 0.0% | 1 | — | insufficient | ❌ blocked | — |

### Deltas vs documented baseline (issue #686 initial, 2026-05-02)

| Class | Baseline | Now | Delta | Action |
|-------|----------|-----|-------|--------|
| CRYPTO 7d PF | 1.33 | 1.356 (all-time) | +0.026 | Stable ✅ |
| CRYPTO 24h PF | 3.54 | 2.436 (last 16Z read, same snapshot) | No change | Same cron |
| EQUITY 7d PF | 0.87 | 0.703 (all-time) | −0.167 | ⚠️ Worsened; goldmine_6x killed (#692); circuit_breaker OK |
| EQUITY 30d WR | 55.9% | 48.6% | −7.3pp | Monitor per issue #693 |
| FOREX 7d PF | 0.14 | 2.900 | **+2.76** | ✅ PR #687 working, 17th hr ≥1.0 streak |
| COMMODITY PF | 1.78 | 1.422 | −0.358 | FINDING-52 drain ongoing (roll-off ~2026-05-23) |

---

## 3. Per-Asset Strategy Breakdowns (from recent_closed, n=3500)

### CRYPTO (n=2835 in recent_closed)

Top strategies (n≥20, sorted by n):

| Strategy | n | WR% | PF | Signal |
|----------|---|-----|----|--------|
| luxalgo_confluence | 719 | 45.1% | 1.055 | Borderline; watch for PF<1.0 |
| unknown | 499 | 34.7% | 1.244 | Classification; not actionable |
| st_fear_greed_contrarian | 270 | **63.7%** | **2.558** | ✅ Elite |
| claude_ml_moderate_mut | 97 | 53.6% | 1.866 | ✅ Good |
| crypto_mtf_ema_slope_alignment_v1 | 89 | 47.2% | 1.070 | Marginal |
| signal_engine_momentum_mut | 72 | 38.9% | 1.140 | OK |
| crypto_kalman_trend_residual_reversion_v1 | 68 | 55.9% | 1.463 | ✅ Good |
| atr_percentile_gate | 61 | 62.3% | 1.330 | ✅ Good |
| mega_mutation_macd_rsi_m048 | 44 | **72.7%** | **5.545** | ✅ Elite |
| keltner_compression_expansion_sol_v1 | 36 | 36.1% | 0.899 | ⚠️ Sub-1.0; monitor |
| mega_mutation_ema_momentum_m006 | 33 | 45.5% | 0.803 | ⚠️ Sub-1.0; approaching kill |
| MomentumEMA | 24 | 37.5% | 0.965 | ⚠️ Borderline |
| **claude_ml_conservative_mut** | **20** | **20.0%** | **0.545** | 🔴 WR<35%, approaching kill gate (PF>0.5 so no auto-post yet) |

**Flag:** `claude_ml_conservative_mut` n=20, WR=20%, PF=0.545. One more similar-size batch and PF likely falls below 0.5. Monitor next hour.

### EQUITY (n=313 in recent_closed)

| Strategy | n | WR% | PF | Signal |
|----------|---|-----|----|--------|
| stocks_rsi2_pullback | 51 | 39.2% | 1.003 | Marginal; was 35.7% at 7d (issue #693) |
| rs-breakout-scout | 24 | 66.7% | 4.534 | ✅ Elite |
| vol-contraction-scout | 16 | 68.8% | 3.296 | ✅ Good |
| donchian-stock-breakout | 14 | 78.6% | 7.134 | ✅ Elite |
| macd-hidden-div-scout | 11 | **27.3%** | **0.254** | 🔴 n<20 gate but WR dire; escalate at n=20 |
| mtf-align-scout | 9 | 77.8% | 5.572 | ✅ Elite |
| call-surge-scout | 5 | 20.0% | 0.217 | n<20; monitor |

**EQUITY circuit_breaker status:** NOT breached. 30d WR=48.6% vs lower bound 14.6%. Recovery path per issue #693: wait for 14d PF ≥1.5 post-#692.

### FOREX (n=143 in recent_closed)

| Strategy | n | WR% | PF | Signal |
|----------|---|-----|----|--------|
| ig_contrarian_sentiment | 46 | **63.0%** | **2.618** | ✅ Elite — FOREX anchor post-kill |
| forex-rsi-ema-scout | 22 | 54.5% | 1.676 | ✅ Good |
| MeanReversionBB | 22 | 31.8% | ~inf* | *PF inflated (zero-sum losses); sumPnL=+16.6% from wins |
| unknown | 21 | 33.3% | 0.929 | Classification; borderline |
| carry_trade_momentum | 3 | 33.3% | 0.354 | n<20; remnant post-forex_carry_momentum kill |

*MeanReversionBB: 7 positive-pnl wins + 15 zero-pnl trades → PF denominator near zero; real signal is +16.6% sumPnL on n=22.

**FOREX 17th consecutive hour ≥1.0 post-PR-#687 confirmed.**  
`forex_carry_momentum` and `forex_rsi2_mean_reversion` absent from data — kills effective.

---

## 4. New Kill Candidates (mutation_analysis.py run 17:09Z)

### NEW FINDING-54: `cta_replicator × NG=F` — SYMBOL KILL CANDIDATE

**Evidence from mutation_analysis.py `--symbols` section:**

| Symbol | n | WR | Avg PnL |
|--------|---|-----|--------|
| NG=F (Natural Gas Futures) | **24** | **0.0%** | −0.03% |

- **Kill gate check:** n=24 ≥ 20 ✅ | WR=0.0% < 35% ✅ | Pattern match: FUTURES commodity symbol (consistent with cta_replicator losing on energy/commodity futures: CL=F 19.1% WR n=47, ZC=F 0% WR n=8) ✅
- **Protocol:** Requires 3-AI consensus before adding to `BLOCKED_STRATEGY_SYMBOL_PAIRS`. Currently 1/3 (this audit). **Posted to issue #686.**
- **Candidate block:** `("cta_replicator", "NG=F")` in `audit_trail/quality_gates.py:BLOCKED_STRATEGY_SYMBOL_PAIRS`

### Directional mutation candidates (not kill-gate but flagged)

| Strategy | SHORT WR | LONG WR | Spread | n SHORT | n LONG | Action |
|----------|----------|---------|--------|---------|--------|--------|
| ig_contrarian_sentiment | 60.3% | 16.5% | 44pp | 58 | 200 | SHORT-only mutation sandbox |
| myfxbook_retail_contrarian | 50.0% | 13.7% | 36pp | 14 | 124 | SHORT-only mutation sandbox |
| cta_cross_asset_tsmom | 50.9% | 29.4% | 21pp | 175 | 85 | Monitor |

*(These require 3-axis mutation test per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` before sandbox promotion.)*

---

## 5. PR Triage

| PR | Title | CI | Reviews | Mergeable | Action |
|----|-------|----|---------|-----------|--------|
| **#1294** | audit(hourly): 16Z | 3/3 ✅ | Greptile COMMENTED only | clean | **MERGED ✅** |
| **#1292** | feat(B10): UEPS KPI sidecar (CI-green attempt) | test(3.11) ❌ | Greptile COMMENTED only | blocked | **HOLD** — test fail |
| **#1287** | feat(b10): UEPS KPI panel Path B | test(3.11) ❌ | Greptile COMMENTED only | blocked | **HOLD** — test fail + large-file missing diffs |
| **#1279** | docs: AGENTS.md cloud agent note | n/a | n/a | DRAFT | **HOLD** — draft |

**HOLD set (#660 #658 #681 #661):** Absent from open PR list ✅  
**Rebase-list (#669 #676 #608 #665 #644 #597 #615 #655):** All merged/closed per 16Z audit ✅  
**Plan v2.1 guardrails:** No PRs citing PF 5.81 / ml_score 0.90 / WINNER_FILTER ✅

### #1292 test failure — root cause
CI reports `test (3.11)` FAILURE on run `26239236282`. The PR body confirms it restored 19 original tests + 4 new B10 tests. The failure likely stems from the same signature mismatch that plagued #1287 (functions `_collect_system_stats`, `_compute_verified_alpha_summary` etc. called with wrong arg counts). **Pytest not installable in this environment** — cannot reproduce locally. Next step: PR author must re-examine test signatures against current `audit_trail/dashboard_generator.py` function definitions.

---

## 6. FINDING-52 Status (multi_asset_copytrader × COMMODITY)

Per 16Z audit: n=37, WR=8.1%, PF=0.243, sumPnL=−108.07%. Meets all kill gates.  
**Votes: 1/3 (this session).** Awaiting Kimi + Copilot/Cursor votes before `BLOCKED_ASSET_STRATEGY_PAIRS` addition.  
**Roll-off ETA:** ~2026-05-23 (legacy drain expected to clear naturally).

---

## 7. FINDING-53 Status (battleground × CRYPTO)

n=18, WR=16.7%. Still 2 trades from n=20 gate. **Monitor only.**

---

## Summary

| Item | Count |
|------|-------|
| PRs merged this hour | 1 (#1294) |
| PRs on hold | 3 (#1292, #1287, #1279) |
| New kill candidates | 1 (FINDING-54: cta_replicator×NG=F) |
| Confirmed findings | FINDING-52 (1/3 votes), FINDING-53 (monitor) |
| Dashboard refresh | ❌ Stale (same 12:18Z snapshot, 5th hr) |
| FOREX post-#687 streak | ✅ 17 consecutive hours PF≥1.0 |
| EQUITY circuit_breaker | ✅ Not breached (30d WR=48.6%) |
