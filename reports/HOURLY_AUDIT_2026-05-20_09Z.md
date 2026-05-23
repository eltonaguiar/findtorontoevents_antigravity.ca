# Hourly Audit — 2026-05-20 09Z

**Generated:** 2026-05-20 ~09:12Z  
**Auditor:** Claude Sonnet 4.6 (claude-code session)  
**Previous audit:** PR #1259 (08Z 2026-05-20) — merged ✅ this hour  
**Snapshot:** `audit_dashboard/data/dashboard_data.json` @ 2026-05-20T04:13:12Z  
**Snapshot age at audit time:** ~5h — **STALE** (>120min threshold; no cron refresh since 04:13Z)  
**Note:** The expected 08:15Z cron refresh has not yet landed on main. 09:15Z cron push expected. All window metrics computed from the same 04:13Z snapshot; 24h PF changes vs prior audits reflect window slide (picks from ~09Z yesterday dropped out of 24h frame).

---

## Issues read

| Issue | Title | Status |
|-------|-------|--------|
| #685 | Resolver-rescope claims obsolete; remaining moves operational/multi-week | Open — no action (resolver work DONE per issue body) |
| #686 | Goal-#1 quality regression: per-asset live-data attribution | Open — active tracking |
| #693 | EQUITY 7d/14d/30d PF degradation monitor | Closed 2026-05-13 — PR #692 (goldmine_6x kill) resolved |

**Issue #685 reminder:** Auto-close/REQUEST_CHANGES any PR claiming "widen re-resolve scope" — work is done.  
**Issue #693:** Closed. EQUITY 7d remains weak (PF 0.641) but goldmine_6x is confirmed dead. Monitor per issue #693 recommendation (stocks_rsi2_pullback if WR stays <40% on n≥20).

---

## Task 1 — Per-asset windowed metrics (snapshot 2026-05-20T04:13:12Z, window end ~09:00Z)

| Class | 24h PF | 24h n | 7d PF | 7d n | 30d PF | 30d n | Status |
|-------|--------|-------|-------|------|--------|-------|--------|
| CRYPTO | 0.617 | 133 | 1.193 | 1005 | 1.340 | 2788 | 24h regressed (0.826→0.617) — window slide, not new trades |
| EQUITY | 0.075 | 16 | 0.641 | 45 | 1.419 | 146 | Unchanged vs 08Z; 7d sub-floor, 30d T2 candidate |
| FOREX | 1.278 | 7 | 1.313 | 17 | 2.515 | 93 | 7d slight uptick (1.272→1.313); post-#687 recovery holding |
| COMMODITY | 0.000 | 16 | 0.097 | 38 | 0.962 | 73 | All windows sub-1.0 — FINDING-22 + FINDING-28 active |
| ETF | 0.000 | 1 | 1.233 | 16 | 1.917 | 50 | Stable |
| BOND | 0.000 | 3 | 0.000 | 3 | 0.000 | 3 | n<10 — insufficient for verdict |
| FUTURES | — | 0 | — | 0 | inf | 2 | n too small |

### Delta vs 08Z

| Class | Window | 08Z | 09Z | Delta | Cause |
|-------|--------|-----|-----|-------|-------|
| CRYPTO | 24h PF | 0.826 | 0.617 | **-0.209** | Window slide: good picks from 2026-05-19 ~07-09Z rolled out of frame |
| FOREX | 7d PF | 1.272 | 1.313 | +0.041 | Minor window slide, 1 pick dropped out |
| All other | all | unchanged | unchanged | 0 | Same snapshot, negligible slide at 7d/30d |

### Delta vs issue #686 baseline (2026-05-02T19:55Z)

| Class | Window | Baseline | 09Z | Delta |
|-------|--------|----------|-----|-------|
| CRYPTO | 24h PF | 2.65 | 0.617 | -2.033 (n grew: 85→133; mix changed) |
| CRYPTO | 7d PF | 1.21 | 1.193 | -0.017 stable |
| EQUITY | 7d PF | 0.87 | 0.641 | -0.229 worsening |
| EQUITY | 30d PF | 2.18 | 1.419 | -0.761 declining |
| FOREX | 7d PF | 0.14 | 1.313 | +1.173 PR #687 impact |
| FOREX | 30d PF | 0.97 | 2.515 | +1.545 dramatic recovery |
| COMMODITY | 30d PF | ~1.78 | 0.962 | ~-0.82 new degradation |

### Delta vs documented baseline (CLAUDE.md / issue tracker)

- CRYPTO 24h PF 3.54 (baseline) → 0.617 (09Z) — sustained decline; 7d/30d stable
- EQUITY 7d 0.87 (baseline) → 0.641 — continued deterioration
- FOREX 7d 0.14 (baseline) → 1.313 — post-#687 recovery confirmed
- COMMODITY degraded below baseline in all windows

---

## Task 2 — PR triage

### Open PRs at time of audit

| PR | Title | Mergeable | CI | Reviews | Action |
|----|-------|-----------|-----|---------|--------|
| #1259 | audit: 08Z hourly 2026-05-20 | unknown (transient) | 0 runs ([skip ci]) | greptile COMMENTED only | **MERGED** ✅ |

**Merged this hour: #1259**

HOLD set (#660 #658 #681 #661): absent from open PRs ✅  
Author-rebase watch PRs (#669 #676 #608 #665 #644 #597 #615 #655): absent ✅

**Note on PR #1259 merge:** `mergeable_state` returned "unknown" (transient — GitHub hadn't recomputed after main moved forward with [skip ci] scan commits). Content was 2 markdown report files with no overlap to any scan commits. 0 CI check runs because the branch commits carry `[skip ci]` tags (consistent with prior hourly audit branches). Greptile review was COMMENTED, not REQUEST_CHANGES. Threshold issues flagged by Greptile are addressed in Task 5 below.

---

## Task 3 — Author rebases check

PRs #669, #676, #608, #665, #644, #597, #615, #655 — all absent from open PR list. No action required.

---

## Task 4 — New strategy kills (mutation_analysis.py output)

### Kill criteria: PF < 0.5 AND WR < 35% AND n ≥ 20

Strategies meeting all three criteria in 7d window:

| Strategy | Class | 7d n | 7d WR | 7d PF | 7d Sum | Status |
|----------|-------|------|-------|-------|--------|--------|
| `cftc_cot_commercial_signal` | COMMODITY | 20 | 5.0% | 0.113 | -65.79% | FINDING-22 — awaiting 3-AI consensus |

Strategies meeting 2/3 criteria (watch list):

| Strategy | Class | 7d n | 7d WR | 7d PF | 7d Sum | Gap |
|----------|-------|------|-------|-------|--------|-----|
| `crypto_mtf_ema_slope_alignment_v1` | CRYPTO | 27 | 33.3% | 0.505 | — | PF 1% above floor (FINDING-27) |
| `futures_momentum` | COMMODITY | 17 | 11.8% | 0.087 | -52.81% | n=3 below floor (FINDING-28) |

No new strategies crossed all three thresholds this hour. No auto-kills triggered.

### Mutation analysis axis highlights (unchanged from 08Z — same data)

**Axis 1 — direction split (LONG vs SHORT):**
- `ig_contrarian_sentiment`: SHORT 60.3% vs LONG 16.5% (44pp) — LONG-only kill mutation candidate
- `myfxbook_retail_contrarian`: SHORT 50% vs LONG 13.7% (36pp) — same
- `quan_engine_swing`: SHORT 60% vs LONG 26% (34pp) — same
- `cta_cross_asset_tsmom`: SHORT 52% vs LONG 29.4% (23pp)

**Axis 3 — symbol variance:**
- `cta_replicator`: NG=F 0% WR (n=24), ZC=F 0% (n=8) — symbol-allowlist candidates
- `quan_engine`: MATICUSDT, ONDOUSDT, SOLUSDT worst performers
- `multi_asset_copytrader`: PL=F, GC=F, HG=F all 0% WR

All require full mutation protocol before any action.

---

## Task 5 — Findings update

### FINDING-22 (continuing) — `cftc_cot_commercial_signal × COMMODITY`
- 7d: n=20, WR=5.0%, PF=0.113, sum=-65.79%
- All three kill criteria met
- Status: **awaiting 3-AI consensus** (no new consensus received this hour)
- Next: post to issue #686 requesting AI consensus if no response by 10Z

### FINDING-25 (continuing) — `quan_engine` symbol failures
- `× XRPUSDT`: n=13, WR=0.0% — below n=20 floor, unchanged
- `× DOGEUSDT`: n=12, WR=8.3% — below n=20 floor, unchanged
- `× ETCUSDT`: n=5, WR=0% — far below floor
- Status: **monitor only** — check at 10Z when snapshot refreshes

### FINDING-27 (continuing + threshold correction)
- `crypto_mtf_ema_slope_alignment_v1`: 7d n=27, WR=33.3%, PF=0.505
- **Greptile flagged contradiction in 08Z report:** Task 4 said n≥30 to promote; Task 5 said "any next-snapshot PF drop below 0.5."
- **Correction (this report):** Standard kill threshold is `WR<35% AND PF<0.5 AND n≥20` per CLAUDE.md. The n≥30 reference in 08Z was a documentation error. Current PF=0.505 is above the 0.5 floor → **WATCH only**. Escalate to kill-candidate if PF drops below 0.5 on n≥20.

### FINDING-28 (new) — `futures_momentum × COMMODITY`
- 7d: n=17, WR=11.8%, PF=0.087, sum=-52.81%
- PF (0.087) and WR (11.8%) fully sub-floor; n=17 is 3 short of the 20-floor
- COMMODITY 7d cron data is stale — new picks may push n past 20 on next snapshot
- **Status: watch** — escalate to FINDING-22-equivalent if n≥20 on next snapshot refresh

### Greptile ensemble (FINDING-1 from retroactive 05-19 report) — disposition
- Greptile flagged missing resolution for `ensemble` strategy (n=31, WR=19.4%, PF=0.279 in 05-19 report)
- 09Z check: `ml_enhanced_ARBUSDT_1h_D_ensemble_stack` has n=2 in 7d window — different strategy or different window
- Broader 7d scan shows no ensemble-class strategy with n≥20
- **Assessment:** The 05-19 retroactive finding likely references an all-time or 30d window that has shifted. The `ensemble` variant in the 05-19 report requires follow-up against the 30d window in a dedicated session. Not blocking this PR.

---

## Kill verifications

| Strategy | 7d n | Status |
|----------|------|--------|
| `forex_carry_momentum` | 0 | ✅ DEAD (PR #692) |
| `goldmine_6x_consensus` | 0 | ✅ DEAD (PR #692) |
| `cftc_cot` (PR #683) | 0 | ✅ DEAD |
| `forex_rsi2_mean_reversion` | 0 | ✅ DEAD (PR #692) |
| `quan_engine/HYPEUSDT` | 53 | ⚠️ Gate bypass (P1) — PF=1.727 positive, no action |

---

## Summary

- **Snapshot:** STALE ~5h (04:13Z, no cron refresh since)
- **Merged:** PR #1259 (08Z) ✅
- **New findings:** FINDING-28 (futures_momentum × COMMODITY, n=17 approaching kill threshold)
- **Threshold fix:** FINDING-27 escalation condition corrected to standard WR<35%+PF<0.5+n≥20
- **Kill candidates confirmed dead:** 4/4 (forex_carry_momentum, goldmine_6x_consensus, cftc_cot, forex_rsi2_mean_reversion)
- **Pending 3-AI consensus:** FINDING-22 only
- **Action required next hour:** await snapshot refresh; check FINDING-28 n count; check FINDING-25 symbol counts; post FINDING-22 consensus request to issue #686 if still at 1 AI

---

_Generated by Claude Code — session_01Y1Mi8KfHwjbPc866N3Tikc_
