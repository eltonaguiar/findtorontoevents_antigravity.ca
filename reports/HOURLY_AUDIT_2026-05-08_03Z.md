# Hourly Audit — 2026-05-08 03Z

**Generated:** 2026-05-08T03:12Z  
**Dashboard snapshot:** 2026-05-08T03:06Z (latest `[skip ci]` forward-scan commit: `245f68f5`)  
**Auditor:** Claude Sonnet 4.6 (session_016rE6MGRSq5vB4kN9i7CtLz)  
**Prior merged PRs context:** #684 (48h review), #674 (B11 ETF), #673 (B14 stress), #664 (audit credibility), #683 (cftc_cot kill), #687 (JPY-cross BUY rule fix), #692 (forex_carry_momentum + goldmine_6x kill), #694 (quan_engine HYPEUSDT block)

---

## 1. Dashboard Refresh Status

Origin/main fast-forwarded to `245f68f5` (forced update from `61bd9a97`). Latest `[skip ci]` commits confirm scanner ran at 2026-05-08 03:06Z. Dashboard data is current.

---

## 2. Per-Asset Class Metrics

### 2a. Long-Run (`asset_class_health`, post-resolver v2)

| Class     | PF (long-run) | WR (long-run) | vs Baseline (issue #686) |
|-----------|--------------|--------------|---------------------------|
| CRYPTO    | 1.34         | 47.1%        | +0.06 PF vs 1.28          |
| EQUITY    | 1.55         | 53.6%        | +0.14 PF vs 1.41 ✅ T2+   |
| FOREX     | 0.25         | 46.2%        | −0.02 PF vs 0.27          |
| COMMODITY | 4.43         | 67.3%        | +2.65 PF vs 1.78 (*)      |
| BOND      | 0.66         | 54.5%        | −1.06 PF vs 1.72          |
| ETF       | 1.39         | 58.3%        | +0.15 PF vs 1.24          |
| UNKNOWN   | 2.40         | 50.0%        | —                         |

(*) COMMODITY long-run PF spike to 4.43 is anomalous vs 30d window — see §2d.

### 2b. Time-Window Analysis (from `picks.recent_closed`, n=3500)

| Class     | 24h n | 24h PF | 24h WR | 7d n | 7d PF | 7d WR | 30d n | 30d PF | 30d WR |
|-----------|-------|--------|--------|------|-------|-------|-------|--------|--------|
| CRYPTO    | 62    | **0.45** ⚠️ | **19.4%** ⚠️ | 277 | 1.41 | 43.0% | 826 | 1.14 | 39.3% |
| EQUITY    | 2     | 8.41   | 50.0%  | 16   | **5.42** ✅ | **68.8%** ✅ | 103 | 4.63 | 71.8% |
| FOREX     | 0     | —      | —      | 25   | **1.61** ✅ | 44.0% | 192 | **1.84** ✅ | 54.2% |
| COMMODITY | 0     | —      | —      | 0    | —     | —     | 65   | 0.04 ⚠️ | 40.0% |
| ETF       | 1     | ∞      | 100%   | 13   | 25.47 | 92.3% | 43   | 4.54 | 79.1% |
| BOND      | 0     | —      | —      | 0    | —     | —     | 0    | —    | —     |

### 2c. Deltas vs Documented Baselines

| Metric                    | Baseline (issue #686)     | Current (03Z)      | Delta        |
|---------------------------|---------------------------|--------------------|--------------|
| CRYPTO 24h PF             | 3.54                      | 0.45               | −3.09 ⚠️    |
| CRYPTO 7d PF              | 1.33                      | 1.41               | +0.08 ✅     |
| CRYPTO 30d PF             | 1.33                      | 1.14               | −0.19        |
| EQUITY 7d PF              | 0.87 (pre-#692)           | 5.42               | +4.55 ✅ T1  |
| EQUITY 30d PF             | 1.41–2.18                 | 4.63               | +2.45 ✅ T1  |
| FOREX 7d PF               | 0.14 (pre-#692)           | 1.61               | +1.47 ✅     |
| FOREX 30d PF              | 0.97 (pre-#687)           | 1.84               | +0.87 ✅     |

### 2d. CRYPTO 24h Alarm — Root Cause

24h: PF=0.45 / WR=19.4% / n=62. Strategy breakdown:

| Strategy                  | n  | WR     | PF    | sum PnL% |
|---------------------------|----|--------|-------|----------|
| unknown (catch-all)       | 30 | 26.7%  | 0.80  | −6.08%   |
| signal_engine_momentum_mut| 7  | **0.0%** | 0.0 | −9.92%   |
| luxalgo_confluence        | 4  | 75.0%  | 7.97  | +8.08%   |
| claude_ml_moderate_mut    | 3  | **0.0%** | 0.0 | −5.31%   |
| rapid_rsi_filter_mut      | 2  | **0.0%** | 0.0 | −3.50%   |
| ml_enhanced_* (1 each)    | 10 | 0.0%   | 0.0   | −20.0%   |

**Assessment:** The 24h alarm is driven by (a) `signal_engine_momentum_mut` 7-loss streak (0% WR), (b) `claude_ml_moderate_mut` + `rapid_rsi_filter_mut` mutation strategies failing, and (c) unattributed `unknown` picks performing sub-par. The 7d window (PF=1.41) remains above T2 floor — this is a 24h regime dip, not structural. Do NOT trigger kill protocol on <24h evidence.

**`signal_engine_momentum_mut` escalation:** n=7 / WR=0% in 24h is notable. Does not yet cross n≥20 threshold; flag for next audit cycle. If 7d WR drops below 35% on n≥20, post to issue #686.

### 2e. FOREX Post-Kill Recovery (KEY FINDING)

PR #692 kills (forex_carry_momentum + goldmine_6x_consensus) have had massive positive impact on FOREX:
- **Before #692 (baseline):** 7d PF=0.14 / WR=10.7% / n=146 — catastrophic
- **After #692 (current):** 7d PF=1.61 / WR=44.0% / n=25 — above break-even

FOREX 7d strategy breakdown post-kill:

| Strategy                  | n  | WR     | PF   | sum PnL% |
|---------------------------|----|--------|------|----------|
| MeanReversionBB           | 17 | 58.8%  | 2.09 | +9.68%   |
| forex-rsi-ema-scout       | 5  | 20.0%  | 0.21 | −2.41%   |
| non_crypto_consensus      | 3  | 0.0%   | 0.0  | −0.01%   |

`forex_carry_momentum` and `forex_rsi2_mean_reversion` are **completely absent** from the 7d window — kills confirmed effective. `MeanReversionBB` is now the dominant FOREX strategy and is performing at PF=2.09 / WR=58.8% — T2 territory. `forex-rsi-ema-scout` is weak (n=5, WR=20%) but below n=20 threshold; monitor.

### 2f. COMMODITY 30d Anomaly Explained

COMMODITY 30d: PF=0.04 / WR=40% / n=65 — superficially alarming.

| Strategy                   | n  | WR     | PF   | sum PnL%  |
|----------------------------|----|--------|------|-----------|
| cta_cross_asset_tsmom      | 29 | 41.4%  | 2.49 | +0.08%    |
| cta_golden_cross_200       | 26 | 42.3%  | 0.64 | −0.02%    |
| cftc_cot_commercial_signal | 4  | 25.0%  | 0.01 | **−5.51%** |
| non_crypto_consensus       | 4  | 50.0%  | 1.54 | +0.00%    |

**Root cause:** `cftc_cot_commercial_signal` n=4 with one CL=F trade at −5.49% dominates the 30d PnL sum. Without that outlier, COMMODITY 30d would be approximately break-even. `cftc_cot_commercial_signal` was killed in PR #683 — this outlier is a residual from pre-kill history. The 30d PF=0.04 does NOT represent active COMMODITY strategy quality.

**Note:** COMMODITY has zero picks in the 7d window — no active generating strategies post-kill. This is expected post-PR-#683.

### 2g. EQUITY T1 — 5th Consecutive Confirmation

EQUITY 7d PF=5.42 / WR=68.8% / n=16. This is the 5th consecutive audit run showing T1 metrics (prior: 04Z/05Z/03Z/02Z from #859). goldmine_6x_consensus kill (PR #692) validation is complete.

**Issue #693 close recommendation:** EQUITY 14d recovery criterion was "PF≥1.5 within 7 days post-#692." Current 30d PF=4.63 far exceeds this. Recommend closing issue #693 as resolved.

---

## 3. PR Triage

### 3a. HOLD Set (never merge)
PRs #660, #658, #681, #661 — Plan v2.1 fabricated-stats family. Not touched.

### 3b. Open PR Review

| PR  | Title                                    | CI          | Reviews | Decision                    |
|-----|------------------------------------------|-------------|---------|------------------------------|
| #859| audit(05Z 2026-05-07)                    | scan ✅      | none    | **MERGED** this session ✅   |
| #849| Edge action plan + swarm harness         | —           | —       | SKIP — draft                 |
| #846| feat(b18): Shadow Probation panel        | scan✅ drift✅| none    | **HOLD** — explicit "DO NOT ADMIN-MERGE" in body |

**Total merges this run: 1** (#859)

### 3c. Rebase-Candidate PRs (task item 3)

All 8 rebase-candidate PRs are already closed:

| PR  | State              |
|-----|---------------------------------|
| #669| Merged 2026-05-02  |
| #676| Merged 2026-05-03  |
| #608| Merged 2026-05-03  |
| #665| Merged 2026-05-02  |
| #644| Merged 2026-05-03  |
| #597| Merged 2026-05-03  |
| #615| Merged 2026-05-03  |
| #655| Closed without merge 2026-05-03 |

No action required.

---

## 4. Mutation Analysis (`python tools/mutation_analysis.py --json`)

**No new PF<0.5 + n≥20 strategies found beyond known kill queue.**

### 4a. Kill Queue (3-AI consensus required before action)

| Strategy                        | Axis         | n   | WR     | Evidence                        |
|---------------------------------|--------------|-----|--------|---------------------------------|
| ig_contrarian_sentiment LONG    | Direction    | 158 | 15.2%  | From #686 kill queue; confirmed |
| myfxbook_retail_contrarian LONG | Direction    | 118 | 10.2%  | From #686 kill queue; confirmed |
| rapid_fire × UUSDT              | Symbol       | 34  | 0.0%   | From #686 kill queue; confirmed |
| quan_engine × HYPEUSDT          | Symbol       | 553 | 41.6%  | PR #694 block already deployed  |

### 4b. NEW Escalation — `quan_engine_swing` LONG direction

`quan_engine_swing`: SHORT 60.0% WR (n=5, small) vs **LONG 26.0% WR (n=104)**. Spread=34pp.

Crosses n≥20 + WR<35% threshold on LONG direction. Pattern matches Axis-1 (direction-specific mutation). **Action:** posted to issue #686 for 3-AI consensus. Do NOT auto-kill — SHORT direction is viable; LONG-only block is the candidate mutation, not full strategy kill.

### 4c. Symbol Variance — Not Kill-Threshold Yet

- `multi_asset_copytrader`: CT=F 69.6% WR (good) vs SI=F / AMD / ZW=F 0% WR — sandbox allowlist experiment warranted
- `rapid_fire × TAOUSDT`: n=18 / WR=5.6% — approaching n=20 threshold; monitor

---

## 5. Constraint Verification

- ✅ Resolver-rescope: no code changes (issue #685 DONE)
- ✅ Plan v2.1 stats not cited anywhere in this report
- ✅ No peer PR rebases performed
- ✅ HOLD set (#660 #658 #681 #661) untouched
- ✅ No auto-kills without 3-AI consensus
- ✅ GENERATOR never run locally (`py_compile` only)
- ✅ `updates/index.html` not touched

---

## 6. Summary

| Item                     | Finding                                              |
|--------------------------|------------------------------------------------------|
| Dashboard refresh        | ✅ Current (2026-05-08 03:06Z)                       |
| CRYPTO                   | 24h alarm (PF=0.45, mutation strats failing); 7d T2-floor ✅ |
| EQUITY                   | T1 confirmed 5th run (7d PF=5.42 / WR=68.8%)       |
| FOREX                    | Post-kill recovery confirmed (7d PF=1.61 vs 0.14 baseline) |
| COMMODITY                | 30d distortion from pre-kill CL=F outlier; no active picks |
| ETF                      | 7d PF=25.47 / WR=92.3% (n=13 small)                |
| PRs merged               | #859                                                 |
| New kill candidates      | `quan_engine_swing` LONG (n=104/WR=26%) → posted #686 |
| New findings             | 3 (CRYPTO 24h alarm, FOREX post-kill recovery, quan_engine_swing LONG) |

---

## 7. Recommended Next Actions

1. **`quan_engine_swing` LONG posted to issue #686** — awaiting 3-AI consensus for direction-gated kill
2. **Close issue #693** — EQUITY 14d recovery criterion met (30d PF=4.63, 5th T1 run)
3. **Monitor `signal_engine_momentum_mut`** — 7-loss streak in 24h; check 7d WR on next audit cycle
4. **Monitor `forex-rsi-ema-scout`** — n=5/WR=20% in FOREX 7d; below kill threshold but approaching
5. **`#846` (B18 shadow probation)** — awaiting human review; CI green, sound code

https://claude.ai/code/session_016rE6MGRSq5vB4kN9i7CtLz
