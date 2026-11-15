# Algorithm Specification — FOREX

**Worktree:** scratch-hippodraco  
**Asset Class:** FOREX  
**Status:** BLOCKED  
**T2 Gate Status:** Not cleared — current verdict NOT_READY

---

## 1. Current Money-Ready Verdict (2026-11-15T00:05)

| Metric | Value |
|--------|-------|
| n_resolved | 612 |
| WR | 32.19% |
| PF | 0.6596 |
| Verdict | NOT_READY |

**Note:** The figure "PF 0.077, true 14d WR ~5%" cited elsewhere is a **stale 2026-06-08 snapshot** from `money-maker-readyv2/SKILL.md` Layer A, not the current verdict. Current PF is 0.66 (still far below 1.5 T2 floor).

---

## 2. Why BLOCKED

FOREX is active but poor. Clean cohort analysis shows WR 8.5%, PF 0.63 (from prior analysis). The current verdict shows PF 0.66, WR 32.2% — still far below T2 thresholds.

## 3. Blockers (must be resolved before unblocking)

| Blocker | Detail | Required Action |
|---------|--------|-----------------|
| Sub-floor PF | Clean cohort PF 0.63; current verdict PF 0.66 | Mutation protocol in progress; evaluate LONG-direction block |
| Spread costs | Spread ~1–2 pips = ~4bp/side; rollover/funding if overnight | Model realistic costs; most retail FX pipelines underestimate |
| Multiple testing | Many FOREX strategies tested; no DSR ≥ 0.5 survivor | Correct nb_trials; SPA/White's RC |
| Drift alert | KS_D = 6.6× critical in prior reads | Do not unblock while drift_alert TRUE |
| Silent LONG bias | KeyError/direction handling bugs fixed partially; must not default to LONG | Fix sync fallback paths; use OTHER-bucket + log unknowns |

**Block mechanism:** FOREX is in `BLOCKED_ASSET_CLASSES` in `quality_gates.py` (set contains {FOREX, COMMODITY, FUTURES, BOND}).

## 4. Hypothetical Specification (for when unblocked)

**Strategy:** `fx-contrarian-sentiment`  
**Universe:** EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF  
**Direction:** SHORT-axis bias (SHORT-axis 57% WR vs LONG 21% on `ig_contrarian_sentiment`, 36pp spread — from prior analysis, unverifiable from current sources)  
**Cost model:** 8 bps round-trip (spread ~1-2 pips + rollover if overnight)  
**Benchmark:** Flat cash (direction signals have no natural buy-and-hold)  
**T2 gate:** PF ≥ 1.5, WR ≥ 50%, MDD ≤ 20%, n ≥ 100  

**Probability of profitability:** VERY LOW.

---

## 5. Do Not

- Do not unblock FOREX while drift_alert is TRUE.
- Do not trust "FOREX 14d WR 64% / PF 2.43" — clean data shows much lower.
- Do not default silently to LONG; use OTHER-bucket for unknown directions.

---
