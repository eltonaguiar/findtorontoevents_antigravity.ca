# Addendum: Cross-Check Corrections to Peer Review (Claude Opus 4.7)

**Date:** 2026-05-02  
**Original Review:** `updates/2026-05-02-hedge-fund-package-peer-review.md`  
**Cross-Checker:** Claude Opus 4.7 (1M context)  
**Status:** 5 of 5 cross-check findings validated — corrections applied below

---

## Summary

Claude's cross-check of my peer review found **5 material errors or omissions** that future reviewers should know before acting on the recommendations. The original review's net verdict (A-, conditional approval) stands, but the action priorities and evidence citations require correction.

---

## Correction 1: Signal Quality ML — "Not Wired" Was Misleading

**Original Claim:** "Signal Quality ML Predictor is the single highest-ROI integration (4-6 hours, +5-15pp WR)" — described as "already implemented, just not wired."

**Cross-Check Finding:** The **producer/training side IS wired**:
- `scanner.py:2631-2640` — model training pipeline
- `scanner.py:4483-4485` — model inference hooks
- 3 GitHub Actions workflows for train/monitor

The **filter/scorer side** (applying the quality score to gate picks before dashboard display) is the unwired part. Calling the entire module "not wired" overstated the integration gap and understated the engineering that already exists.

**Corrected Assessment:** Integration effort is likely **2-3 hours** (wire filter side only), not 4-6 hours. The +5-15pp WR claim is unchanged but should be validated against the already-trained model's actual ROC-AUC on recent data before deployment.

---

## Correction 2: "5 Critical Errors Caught" Table Is Restated, Not Fresh

**Original Claim:** Presented the corrected gate table as my own synthesis.

**Cross-Check Finding:** The table is **verbatim restatement** from:
- `FOOLPROOF_ACTION_PLAN.md` Section 1.1 (not on this branch)
- `quant_verification.md` Section 3.1 (not on this branch)

**Issue:** These source documents are not committed to `kimi/hedge-fund-docs-2026-05-02-v2`, so anyone reading the review on this branch cannot verify the citations. The citation trail is broken.

**Corrected Assessment:** The corrections are valid, but my review should have:
1. Explicitly cited `FOOLPROOF_ACTION_PLAN.md` and `quant_verification.md` as the source documents
2. Noted that these documents exist in the Downloads package but are not yet on this branch
3. Recommended committing the verification documents to the branch before merging

**Action:** Either cherry-pick `FOOLPROOF_ACTION_PLAN.md` and `quant_verification.md` onto this branch, or rewrite the review to treat the original PR as the only available evidence and flag the corrections as "pending verification document availability."

---

## Correction 3: Internal Inconsistency — I Accepted a Small-Sample Claim While Rejecting Another

**Original Claim:** I correctly demolished the S-Tier n=14 "Renaissance-grade" claim, but **uncritically accepted** the quant verification's n=99 "1.5-2.0 R:R band: PF 5.81, Kelly +47.2%" claim.

**Cross-Check Finding:** Claude's per-asset-perf subagent found that the **5,963-trade reality contradicts the n=99 shadow-sample claim**:
- Full dataset: WR 31.1%, PnL -976.7%
- Shadow n=99 claim: PF 5.81, Kelly +47.2%

**This is the same statistical hazard I criticized in the original PR** — small-sample selection bias in a subset that may not represent the full population. The shadow-blocked dataset (n=500, only 253 resolved) is subject to severe survivorship bias.

**Corrected Assessment:** The R:R 1.5-2.0 band claim is **unverified at scale**. Recommendations:
1. Do NOT trust the PF 5.81 / Kelly +47.2% figures for capital allocation
2. The "keep floor at 1.5, add ceiling at 2.0" recommendation is **directionally plausible** but not empirically proven
3. Run the band analysis on the **full 5,963-trade dataset** before deploying any R:R gate changes
4. The safest immediate action: keep current floor, do NOT add new marginal bands, and collect 200+ trades in each R:R band before threshold adjustment

---

## Correction 4: Orphan List Has ~40-60% False-Positive Rate

**Original Claim:** 14 orphaned modules identified; top 5 prioritized for integration.

**Cross-Check Finding:** **3 of 5 sampled top-priority modules are already wired** (not orphans):

| Module | Original Status | Cross-Check Reality |
|---|---|---|
| `signal_quality_ml.py` | "Orphan — never integrated" | **Producer side wired** in scanner.py + 3 GHAs |
| `audit_impact_tracker.py` | "Orphan — no CI references" | **Referenced in CI** (audit trail workflow) |
| `meta_model_trainer.py` | "Orphan — no imports" | **Imported by dashboard generator** (v2.1+) |
| `alpha_vs_beta_benchmark.py` | Orphan | **Confirmed orphan** ✓ |
| `meta_model_chatgpt.py` | Orphan | **Confirmed orphan** ✓ |

**Corrected Assessment:** The code archaeology report's orphan detection methodology (grep for imports/CI references) has a **high false-positive rate** due to:
- Dynamic imports not caught by static grep
- CI workflow references in `.github/workflows/` subdirectories not searched
- Dashboard generator v2.1+ imports not visible in v1.x codebase snapshots

**Action before integration:** Run `python -c "import module"` for each claimed orphan and check for `ModuleNotFoundError` vs successful import. Only true import failures are orphans.

---

## Correction 5: Forex Analysis Ignored the 2,047-Trade Post-Fix Bleed

**Original Claim:** "The forex forensic analysis is exemplary" based on n=273 trusted-filter validation (WR 48.7%, PF 3.59).

**Cross-Check Finding:** The **unfiltered post-resolver-fix performance** tells a different story:
- **n = 2,047 trades**
- **PF = 0.26**
- **PnL = -1025%**

The n=273 "trusted filter" subset was **cherry-picked** — it excludes the majority of post-fix trades that still bleed capital. The resolver bug fix eliminated the 0% WR measurement artifact, but it did **not** fix the underlying strategy's negative expectancy.

**Corrected Assessment:** Forex is **not recovered**. The true state is:
- Pre-fix: 0% WR was a measurement artifact (correctly diagnosed)
- Post-fix: True WR is still sub-40% at scale; the strategy is structurally unprofitable
- The n=273 trusted-filter slice is not representative of live performance

**Action:** Do NOT declare forex "recovered" or allocate capital. Treat forex as **still in FAIL tier** until:
1. Full 2,047-trade dataset shows PF > 1.2 for 100+ consecutive trades
2. New strategies (G10 carry, momentum hybrid) are backtested and paper-traded
3. Trusted-filter criteria are validated as stable predictors of live performance

---

## Revised Priority Action List

### Removed from Day 1 (No Longer Supported by Evidence)
- ~~Fix R:R gate: Floor 1.5, ceiling 2.0 (bandpass filter)~~ — **Unverified at scale; n=99 claim contradicts n=5,963 reality**
- ~~Fix ml_score threshold: >= 0.90 (not 0.82)~~ — **Still valid, but source document not on branch**

### Retained Day 1 (Still Valid)
1. **Verify Signal Quality ML filter side wiring** — 2-3 hours, actual effort lower than claimed
2. **Enable gates in SOFT mode** for 2 weeks — independent of threshold values
3. **Extend tracking window** from 24h to 120h — data quality issue, not strategy issue
4. **Run orphan validation** (`python -c "import X"`) before prioritizing integration

### Added Day 1 (New from Cross-Check)
5. **Re-run R:R band analysis on full 5,963-trade dataset** — do not trust n=99 shadow sample
6. **Acknowledge forex is still FAIL tier** — do not allocate capital based on n=273 cherry-pick
7. **Commit FOOLPROOF_ACTION_PLAN.md and quant_verification.md** to this branch to fix citation trail

---

## Net Verdict (Revised)

**Original:** A- conditional approval.  
**Revised:** **B+ conditional approval** — the 5 corrections reduce confidence in the action priorities but do not invalidate the core finding that independent verification prevented damaging gate changes.

**What remains valuable:**
- The verification mechanism itself (catching original PR errors)
- The QA audit's 37 data quality issues
- The UI/UX redesign recommendations
- The corrected capital cap ($1M until PSR > 0.95)
- The multiple-testing correction call-out
- The live-execution / shadow-block data-gap callout

**What requires re-verification:**
- R:R bandpass filter recommendation (scale mismatch: n=99 vs n=5,963)
- Orphan module prioritization (40-60% false-positive rate)
- Forex recovery status (n=273 cherry-pick vs n=2,047 reality)
- Signal Quality ML integration effort (2-3 hours, not 4-6)

---

## Recommendation for PR #678

Land the peer review as documentation evidence, but **pin this addendum** so future reviewers:
1. Do not re-derive the orphan-wired error
2. Do not trust the n=99 R:R band claim for capital allocation
3. Do not declare forex recovered based on the trusted-filter slice
4. Verify Signal Quality ML wiring before estimating integration effort

**Signed:** Kimi Code CLI (Quantitative Audit)  
**Cross-check validated by:** Claude Opus 4.7  
**Date:** 2026-05-02
