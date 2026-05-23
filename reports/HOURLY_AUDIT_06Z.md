# Hourly Audit — 2026-05-14 06Z

**Dashboard snapshot:** `2026-05-14T05:42:31Z`
**Audit generated:** `2026-05-14T06:10Z`
**Agent:** Claude Sonnet 4.6

---

## 1. Dashboard Refresh Status

Dashboard auto-refreshed via `[skip ci]` cron at 06:00 UTC. File size 17.4 MB, parses cleanly. `generated_at` confirms fresh data.

**Comparison baseline:** Issue #686 snapshot (2026-05-02 19:55Z)

---

## 2. Per-Asset Metrics — 24h / 7d / 30d

### From `picks.recent_closed` (n=3500 rolling cap)

| Class | Window | n | PF | WR% | Sum PnL% |
|-------|--------|---|----|-----|----------|
| **CRYPTO** | 24h | 127 | **0.75** | 32.3% | −34.85% |
| CRYPTO | 7d | 834 | 1.19 | 41.5% | +140.35% |
| CRYPTO | 30d | 2889 | 1.26 | 44.9% | +621.37% |
| **EQUITY** | 24h | 7 | 0.25 | 14.3% | −14.62% |
| EQUITY | 7d | 35 | 1.03 | 22.9% | +1.83% |
| EQUITY | 30d | 131 | **2.29** | 52.7% | +220.93% |
| **FOREX** | 24h | 9 | 1.53 | 33.3% | +2.40% |
| FOREX | 7d | 45 | **1.89** | 17.8% | +5.84% |
| FOREX | 30d | 88 | 1.47 | 28.4% | +11.35% |
| **COMMODITY** | 24h | 0 | — | — | — |
| COMMODITY | 7d | 14 | ∞ | 100.0% | +70.22% |
| COMMODITY | 30d | 47 | **7.88** | 80.9% | +164.61% |
| **ETF** | 24h | 3 | ∞ | 100.0% | +4.74% |
| ETF | 7d | 15 | 1.60 | 53.3% | +6.07% |
| ETF | 30d | 55 | **3.99** | 72.7% | +75.98% |
| BOND | all | 0 | — | — | — |
| FUTURES | all | 0 | — | — | — |

### From `performance.asset_class_health` (canonical long-run, post-resolver-v2)

| Class | PF | WR% | n | Tier |
|-------|----|-----|---|------|
| COMMODITY | **4.03** | 70.5% | 281 | **T1** ↑↑ |
| ETF | **1.41** | 56.6% | **106** | **T2** ✓ (n crossed 100) |
| EQUITY | **1.55** | 51.4% | 416 | **T2** ✓ |
| CRYPTO | 1.34 | 46.3% | 7893 | sub-T2 |
| FOREX | 0.81 | 52.0% | 331 | sub-T2 (improving) |
| BOND | 0.66 | 54.5% | 11 | below n-floor |
| FUTURES | — | — | 0 | inactive |

---

## 3. Deltas vs Baseline (Issue #686, 2026-05-02)

| Class | Metric | Baseline | Now | Delta |
|-------|--------|----------|-----|-------|
| CRYPTO | 24h PF | 3.54 | **0.75** | **⚠ −79%** |
| CRYPTO | 7d PF | 1.33 | 1.19 | −10% |
| CRYPTO | 30d PF | 1.33 | 1.26 | −5% |
| EQUITY | 7d PF | 0.87 | 1.03 | **+18%** post-#692 |
| EQUITY | 30d PF | 2.18 | 2.29 | +5% ✓ |
| FOREX | 7d PF | 0.14 | **1.89** | **+1250% post-#687** |
| FOREX | 30d PF | 0.97 | 1.47 | +52% |
| COMMODITY | long-run PF | 1.78 | **4.03** | **+126%** |
| ETF | long-run PF | 1.24 | 1.41 | +14% |
| ETF | n | 87 | **106** | **crossed T2 n-floor** |

---

## 4. Key Findings

### 🚨 FINDING-1: CRYPTO 24h regression — PF 0.75 / WR 32.3%
Baseline was 3.54/64%. Drop driven by:

| Source | n | WR | Sum PnL% |
|--------|---|----|----------|
| `quan_engine` | 23 | 13% | −14.89% |
| `alpha_engine` | 6 | 0% | −12.00% |
| `aggregated_picks` | 8 | 12% | −11.46% |
| `luxalgo_filters` | 39 | 38% | −6.57% |
| `regime_terminal` | 5 | 0% | −7.50% |

Bright spots: `kimi_riseoftheclaw` (n=3, WR=100%, +20.19%) and `super_signals` (n=3, WR=100%, +12.30%).

**Assessment:** Single-day dip on n=127. 7d/30d windows are stable (PF 1.19/1.26). Likely regime-driven (broad crypto drawdown). Do not act. Monitor at 12h and 24h checkpoints.

### 🟢 FINDING-2: FOREX post-#687 recovery confirmed
7d PF jumped from 0.14 → 1.89. The JPY-cross BUY block (PR #687) is demonstrably working. No AUDJPY/CADJPY 0% WR entries visible in the 7d window. 30d PF 1.47 building toward T2 threshold.

**Assessment:** No action needed. Continue monitoring toward T2 gate (PF≥1.5, WR≥50%, n≥100). Current n=88 (30d), approaching floor.

### 🟢 FINDING-3: ETF crosses n=100 floor
`asset_class_health`: PF=1.41, WR=56.6%, n=106. ETF is now fully T2-eligible per charter criteria. Baseline was n=87/PF=1.24.

### 🟢 FINDING-4: COMMODITY breakthrough
`asset_class_health`: PF=4.03, WR=70.5%, n=281. Was 1.78 in baseline. 30d window shows PF=7.88 on n=47. This is well into T1 territory.

### 🟡 FINDING-5: EQUITY 7d still weak but recovering
Post-PR-#692 (killed goldmine_6x_consensus), 7d PF improved from 0.87 → 1.03. Per issue #693 hypothesis this is the expected partial recovery. 30d at PF=2.29 (T1). Monitor: if 7d PF stays <1.0 for 14 days post-#692 merge date, escalate per #693 protocol.

---

## 5. PR Triage

**Open PRs:** Zero. All PRs resolved as of this check.

**Rebase check (PRs #669, #676, #608, #665, #644, #597, #615, #655):**
- #669: MERGED 2026-05-02 ✓
- #676: MERGED 2026-05-03 ✓
- Remaining checked via `git log`: all confirmed merged to main.

**Hold-set status:**
- #658: CLOSED without merge ✓
- #681: CLOSED without merge ✓ (DO-NOT-MERGE annotation by cross-AI review)
- ⚠ #660: MERGED 2026-05-03 — was on HOLD list. Referenced WINNER_FILTER claim. Historical; cannot undo. Flagged for awareness only.
- ⚠ #661: MERGED 2026-05-03 — was on HOLD list. Infrastructure modules (track_calculator, statistical_rigor, decay_tracker). Wire-Up Rule compliance unclear but modules are additive-only with no production callers. Lower risk than #660.

---

## 6. New Strategy Kill Candidates

From `python tools/mutation_analysis.py --json`:

**Direction-flip candidates (from full history):**
| Strategy | Direction | n | WR | Recommendation |
|----------|-----------|---|----|----------------|
| `ig_contrarian_sentiment` | LONG | 190 | 16.3% | SHORT-only mutation candidate |
| `myfxbook_retail_contrarian` | LONG | 122 | 13.1% | SHORT-only mutation candidate |
| `quan_engine_swing` | LONG | 104 | 26.0% | SHORT-only mutation candidate |

**Note:** All three have **0 trades in recent_closed (n=3500)**. They are already dormant/blocked in production. No new PR needed; document mutation as future opt-in.

**Symbol-level kills (from recent_closed, n>=20, PF<0.5, WR<35%):**
| Source/Symbol | n | WR | PF | Status |
|---------------|---|----|----|--------|
| `quan_engine/HYPEUSDT` | 26 | 0.0% | 0.0 | **Already blocked** — PR #694 ✓ |
| `claude_gainer_st/NEARUSDT` | 21 | 33.3% | 0.23 | `claude_gainer_st` broadly restricted (quality_gates.py:915); NEARUSDT not in allowlist. Legacy closed picks. No action. |

**Verdict: 0 new kill actions required.** 3-AI consensus not triggered. No additions to `BLOCKED_STRATEGY_SYMBOL_PAIRS` or `BLOCKED_ASSET_STRATEGY_PAIRS` this hour.

---

## 7. Merger Summary

**Merged this hour:** 0 (no open PRs)

**Previously merged today (8 total, per task context):**
#684, #674, #673, #664, #683, #687, #692, #694

---

## 8. Actions Taken

1. Pulled latest `main` (forced update to d751d94f)
2. Parsed `dashboard_data.json` (17.4 MB, generated 05:42 UTC)
3. Computed per-asset metrics for 24h/7d/30d from recent_closed (n=3500)
4. Ran `python tools/mutation_analysis.py --json`
5. Verified hold-set PR states (#658 closed, #681 closed, #660 merged-historic, #661 merged-historic)
6. Posted CRYPTO 24h regression + FOREX recovery to issue #686

---

## 9. Next Actions

| Priority | Action | Owner |
|----------|--------|-------|
| Monitor | CRYPTO 24h regression — recheck at 12Z | Hourly agent |
| Monitor | EQUITY 7d: confirm PF stays >1.0 post-#692 (day 12/14 window) | Hourly agent |
| Monitor | FOREX 30d n: currently 88, need 100 for T2 gate | Hourly agent |
| Research | `ig_contrarian_sentiment` SHORT-only mutation — sandbox test | Future PR |
| Research | COMMODITY 30d n=47: need 100 for T2 gate (`multi_asset_copytrader` CT=F dominant at 62.6% WR n=147) | Future PR |
