# Asset Class Edge Audit — findtorontoevents.ca
## Multi-Model Consensus + Quality Tier Gating Verification

**Generated:** 2026-05-25T15:08 UTC  
**Data window:** 2026-05-16 to 2026-05-21 (6 days, 1,117 resolved picks)  
**Models queried:** 5 via NVIDIA NIM API (Kimi K2.6, GPT-OSS-120B, GLM-5.1, Nemotron Super 49B v1.5, Mistral Nemotron)  
**Status:** CORRECTED — original v1 contained DATA_QUALITY_LEAKAGE artifact

---

## ⚠️ CRITICAL CORRECTION: COMMODITY "STABLE_EDGE" WAS DATA_QUALITY_LEAKAGE

The COMMODITY PF=4.31 / WR=58.4% that the 5 NIM models were shown and ranked #1 was **pre-dedup COT look-ahead leakage** (H-101, M-095). Three independent AI engines (Codex 90%, Gemini 95%, Grok 87%) classified it as DATA_QUALITY_LEAKAGE the same day. The 5 NIM models were **not shown this leakage evidence** — they re-derived a known-bad signal.

### Pre-Dedup vs Post-Dedup Collapse

| Metric | Pre-Dedup (LEAKAGE) | Post-Dedup (Ground Truth) | Source |
|--------|---------------------|---------------------------|--------|
| COMMODITY PF | 4.31 | 0.12–0.31 | `reports/commodity_deep_dive_swarm_2026-05-16.md` |
| COMMODITY WR | 58.4% | 5–10.7% | Same |
| CT=F cotton picks | 230 closed | 2 unique tradeable events | 14.4 picks/date average → massive re-emission |
| Policy-clean n | 9,346 (MySQL DB) | 28 (JSON ledgers) | `reports/2026-05-25_policy_clean_vs_top_edges_funnel.md` |

### Root Cause
CFTC COT (Commitment of Traders) data has a Tuesday-to-Friday publication lag. The `multi_asset_copytrader` system used Tuesday settlement data as if it were available on Tuesday, creating a 72-hour look-ahead window. `COT_PUBLICATION_LAG_DAYS=3` guard now marks pre-publication COT data as invalid, but was not applied retroactively.

### Policy-Clean Verdict (2026-05-24, from `money_ready_verdict.json`)

| Asset Class | n | WR | PF | Status |
|-------------|---|------|-----|--------|
| COMMODITY | 28 | 10.7% | 0.31 | INSUFFICIENT_DATA (drifted from WATCH) |
| EQUITY | 33 | 33.3% | 0.90 | INSUFFICIENT_DATA |
| CRYPTO | 728 | 43.4% | 1.14 | NOT_READY |
| FOREX | 53 | 39.6% | 0.55 | NOT_READY (drifted from WATCH) |
| ETF | 2 | 50.0% | 12.0 | INSUFFICIENT_DATA (n=2) |
| BOND | 8 | 0.0% | 0.00 | INSUFFICIENT_DATA |

**ZERO asset classes are money-ready.** CRYPTO passes DSR/SPA/PBO but fails WR (<50%), PF (<1.50), MDD (100%), and CVAR (-87%).

---

## Quality Tier Gating: The 648/0 Claim — VERIFIED WITH MAJOR CAVEAT

### The Claim (Roo/DeepSeek session)
> "648 un-gated picks went 0-for-648 destroying -825% PnL; 300 gated picks generated +994% — quality tier is near-perfect binary classifier."

### Verified Numbers (from `performance_report_2026-05-16_to_2026-05-21.json`)

| Bucket | n | Wins | WR | Total PnL | exit_reason pattern |
|--------|---|------|-----|-----------|---------------------|
| **Ungated** | | | | | |
| moderate_confidence | 455 | 13 | 2.9% | — | 94.5% SL_HIT |
| low_confidence_or_unverified | 193 | 35 | 18.1% | — | 58.5% SL_HIT, 41.5% TIME_EXIT |
| **Ungated total** | **648** | **48** | **7.4%** | **-825.1%** | |
| | | | | | |
| **Gated** | | | | | |
| profitable_tp | 292 | 292 | 100.0% | — | 100% TP_HIT |
| profitable_tp_low | 150 | 150 | 100.0% | — | 100% TP_HIT |
| elite_a_high_conf | 8 | 7 | 87.5% | — | 7/8 TP_HIT, 1/8 SL_HIT |
| elite_b_good_conf | 3 | 2 | 66.7% | — | |
| alpha_verified | 16 | 5 | 31.2% | — | 11/16 SL_HIT, 5/16 TP_HIT |
| **Gated total** | **469** | **456** | **97.2%** | **+1366.4%** | |

**Numeric verdict:** The 648 → 0 claim is slightly inaccurate. It's actually 648 → 48 (7.4% WR), not 0. The gated cohort is 469 (not 300) with 97.2% WR and +1366.4% PnL. The binary separation is real and extreme — but the explanation is simpler than "near-perfect classifier."

### 🚨 CRITICAL CAVEAT: Quality Buckets Are Post-Hoc (Circular) Labels

The `quality_bucket` field in the performance report does **NOT** come from the production quality gate code in [`audit_trail/quality_gates.py`](audit_trail/quality_gates.py:1) (which uses SMART/ACTIVE/REJECTED taxonomy). The source code that assigns these bucket labels was **not found in any tracked Python file** in the repository.

The bucket taxonomy (`profitable_tp`, `moderate_confidence`, `elite_a_high_conf`, etc.) appears in only two places:
1. The generated JSON at [`audit_trail/data/performance_report_2026-05-16_to_2026-05-21.json`](audit_trail/data/performance_report_2026-05-16_to_2026-05-21.json:199)
2. The seed incident tracker at [`tools/audit_pick_funnel/seed_incidents_enhancements.py`](tools/audit_pick_funnel/seed_incidents_enhancements.py:227) — which itself notes: *"the bucket may be circularly defined by 'failed all upstream gates'"*

**Evidence of circularity:**

| Bucket | Unique Exit Reasons | Dominant Pattern | Circular? |
|--------|---------------------|------------------|-----------|
| `profitable_tp` | 1 (TP_HIT only) | 292/292 TP_HIT | ✅ **Yes** — literally "all TP_HIT picks" |
| `profitable_tp_low` | 1 (TP_HIT only) | 150/150 TP_HIT | ✅ **Yes** — "remaining TP_HIT picks with lower PnL" |
| `moderate_confidence` | 2 | 430/455 SL_HIT (94.5%) | ✅ **Near-circular** — "picks that hit stop loss" |
| `elite_a_high_conf` | 2 | 7/8 TP_HIT | ⚠️ Partially independent — has actual `elite_grade: "A"` field |
| `alpha_verified` | 2 | 11/16 SL_HIT (68.8%) | ❌ **Not circular** — has both wins and losses |

**Bottom line on quality tiers:** The 97.2% WR for "gated" picks is heavily inflated because 442 of 469 gated picks (94%) come from `profitable_tp` + `profitable_tp_low` — which are **defined as** "picks that hit take-profit." This is a tautology, not a classifier. The meaningful gating is in `elite_a_high_conf` (n=8, WR=87.5%) and `alpha_verified` (n=16, WR=31.2%) — too small to draw conclusions.

### Asset Class Isolation

The performance report contains **zero COMMODITY picks** and 1,057 of 1,117 are CRYPTO. This means:
- The quality bucket analysis is a **CRYPTO-only phenomenon** — not contaminated by COT leakage
- The COT leakage and the quality-tier gating are **two independent issues**

---

## Source System Analysis (6-Day Window, CRYPTO-Dominant)

### Sources With Highest Gated-Ratio

| Source System | Total | Gated | Gated% | Notes |
|---------------|-------|-------|--------|-------|
| revival_kimi | 7 | 6 | 85.7% | n too small |
| ai_challenge_kimi_moonshot | 8 | 6 | 75.0% | n too small |
| aggregated_picks | 58 | 43 | 74.1% | Interesting — signal aggregation may filter noise |
| ai_challenge_claude | 7 | 4 | 57.1% | n too small |
| alpha_engine | 82 | 44 | 53.7% | Production workhorse |
| kimi_signal_tracking | 168 | 90 | 53.6% | Highest volume gated producer |
| ml_crypto_pred | 118 | 56 | 47.5% | ML predictions filtering OK |

**Caveat:** Gated-ratio is inflated by the circular `profitable_tp` bucket. These numbers reflect "how often does this source hit TP" rather than "how good is this source at picking."

### Sources Dominating Ungated (Loss) Buckets

| Source System | moderate_confidence | low_confidence | Total Loss |
|---------------|---------------------|----------------|------------|
| quan_engine | 80 | 0 | 80 |
| dna_winner_picks | 57 | 0 | 57 |
| ml_crypto_pred | 53 | 9 | 62 |
| kimi_signal_tracking | 0 | 70 | 70 |
| signal_validation | 0 | 48 | 48 |
| ml_crypto_pred_v12 | 0 | 48 | 48 |

`s/kimi_signal_tracking` appears in **both** the top-gated AND top-ungated lists — it produces 168 picks with a bimodal outcome distribution (90 TP_HIT, 70 low_confidence TIME_EXIT). This suggests the system has two distinct operating modes or signal types.

---

## NVIDIA NIM Multi-Model Consensus — RE-ASSESSED

### Original Responses (Pre-Correction)

All 5 models were shown the pre-dedup dataset where COMMODITY PF=4.31. Their rankings:

| Model | COMMODITY Rank | CRYPTO Rank | EQUITY Rank | Notes |
|-------|---------------|-------------|-------------|-------|
| Kimi K2.6 | #1 | #2 | #3 | Endorsed COMMODITY as "statistically robust" |
| GPT-OSS-120B | #1 | #2 | #3 | Called COMMODITY "the only deployable class" |
| GLM-5.1 | #1 | #2 | #3 | Recommended full allocation to COMMODITY |
| Nemotron Super 49B | #1 | #2 | — | Flagged concentration risk but still ranked COMMODITY #1 |
| Mistral Nemotron | #1 | #2 | #3 | "COMMODITY is clearly the edge" |

**All 5 models converged on the same wrong answer** because they were all shown the same contaminated data. This is a textbook example of **shared-input bias**: multi-model consensus is worthless when all models receive identical corrupted inputs.

### What They Should Have Seen

| Asset Class | True PF (post-policy) | True WR | Verdict |
|-------------|----------------------|---------|---------|
| COMMODITY | 0.31 | 10.7% | INSUFFICIENT_DATA — CT=F concentration at 57% |
| EQUITY | 0.90 | 33.3% | INSUFFICIENT_DATA — AMD concentration at 39% |
| CRYPTO | 1.14 | 43.4% | NOT_READY — MDD=100%, CVAR=-87% |
| FOREX | 0.55 | 39.6% | NOT_READY |

### Lessons Learned

1. **Multi-model consensus does not protect against data poisoning.** If the input data is wrong, N models will produce N wrong answers.
2. **Every consult-nvidiamodels prompt must include a leakage-context block** listing known data-quality incidents (H-101, M-095, etc.) that intersect the asset class being analyzed.
3. **The consult-nvidiamodels skill** ([`skills_archive/global_user_skills/consult-nvidiamodels/SKILL.md`](skills_archive/global_user_skills/consult-nvidiamodels/SKILL.md)) has been updated to require this leakage-context block.

---

## ETF: The Only Non-Leakage Bright Spot

The `regime_adaptive x ETF` pair was flagged by Roo's session as the only persona-asset pair passing all statistical gates (Wilson CI 49.7–91.8%, binomial significance + positive PnL + positive Sharpe). However:

- **Policy-clean data:** n=2, WR=50.0%, PF=12.0 (`money_ready_verdict.json`)
- **Status:** INSUFFICIENT_DATA — n too small for any statistical conclusion
- **Concentration:** 100% in ARKK, capped
- **Prior 30d ETF PF=3.88** exists as a "STRONG RECENT" regime-shift thesis but lacks sufficient closed trades

**Verdict:** Worth monitoring but not actionable yet. Needs ≥20 closed trades before any deployment decision.

---

## Summary: What's Real vs What Was Leakage

| Finding | Original Claim | Corrected | Confidence |
|---------|---------------|-----------|------------|
| COMMODITY PF | 4.31 (STABLE_EDGE) | 0.31 (INSUFFICIENT_DATA) | ✅ Confirmed H-101/M-095 |
| COMMODITY WR | 58.4% | 10.7% | ✅ Confirmed post-dedup |
| Quality tier gating | 0/648 un-gated | 48/648 un-gated (7.4% WR) | ⚠️ Numbers real but buckets circular |
| Gated WR | ~100% | 97.2% (94% from circular TP buckets) | ⚠️ Inflated by tautology |
| CRYPTO PF | 1.14 | 1.14 (NOT_READY) | ✅ Consistent |
| EQUITY PF | 0.90 | 0.90 (INSUFFICIENT_DATA) | ✅ Consistent |
| ANY class money-ready | — | **ZERO** | ✅ Confirmed by pf_registry |
| ETF edge | Wilson CI 49.7-91.8% | n=2, INSUFFICIENT_DATA | ⚠️ Real signal, too few trades |

---

## Action Items

1. **HARD BLOCK:** Any system that bases COMMODITY sizing on pre-dedup COT data must be disabled until `COT_PUBLICATION_LAG_DAYS=3` guard is verified in production.
2. **QUALITY TIER FIX:** Replace the post-hoc `quality_bucket` classification with the production `quality_gates.py` SMART/ACTIVE/REJECTED taxonomy so gating claims are testable pre-hoc.
3. **CONSULT SKILL UPDATE:** [`consult-nvidiamodels/SKILL.md`](skills_archive/global_user_skills/consult-nvidiamodels/SKILL.md) now includes mandatory leakage-context block in every prompt template.
4. **kimi_signal_tracking AUDIT:** This source appears in both top-gated AND top-ungated lists — investigate its bimodal output pattern.
5. **aggregated_picks DEEP DIVE:** 74.1% gated-ratio on 58 picks suggests signal aggregation may be a real edge multiplier — validate on 30d/90d windows.
6. **ETF MONITOR:** Track regime_adaptive ETF picks; reassess at n≥20 closed trades.
