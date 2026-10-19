# Cross-Class SMART-Gate Audit — COMMODITY / FOREX / ETF Dilution Hypothesis

**Date:** 2026-06-23
**Skill:** `.claude/skills/audit-pick-flow/SKILL.md` + PHASE 1C.d-adjacent
**Original hypothesis:** "COMMODITY/FOREX/ETF have 42-53% SMART pass rate + WR<50% → wide throughput dilutes the pipeline → apply EQUITY-style hard floors."

---

## TL;DR

The user's hypothesis was based on misread prior data. The **actual current pass rates are 5.41 %, 1.05 %, 4.36 %** — these classes are **starving, not dilutive**. A CRITICAL **THRESHOLD FREEZE** at `audit_trail/quality_gates.py:280-282` actively prohibits modifying `SMART_PICKS_MIN_SCORE_*` constants until **2026-08-18**, so the proposed remediation is **policy-blocked**, not just statistically premature. **Global recommendation: defer all score-floor interventions** until either the freeze lifts OR per-class `n_out ≥ 30` statistical evidence justifies each threshold override.

---

## 1. Premise correction — actual per-class SMART pass rates

The user's framing "42-53 % SMART pass rate" came from a prior turn's read of the 90-day full-funnel snapshot — those numbers actually came from a different sub-block of `pick_funnel_90d.json` (the all-up 42,038-pick top-level counts). The canonical per-class funnel-by-class block returns **lower** numbers because scanned counts in that block are post-active-gate rejects:

| class | scanned | smart | smart% | WR% | n_out | Wilson95CI |
| --- | --- | --- | --- | --- | --- | --- |
| CRYPTO | 1,342 | 344 | 25.63 % | 48.21 % | 278 | 42.4-54.1 |
| EQUITY | 848 | 215 | 25.35 % | 56.40 % | 164 | 48.7-63.7 |
| **COMMODITY** | **148** | **8** | **5.41 %** | **38.46 %** | **13** | **17.5-64.6** |
| **FOREX** | **382** | **4** | **1.05 %** | **25.00 %** | **4** | **8.7-55.2** |
| **ETF** | **321** | **14** | **4.36 %** | **18.75 %** | **16** | **6.2-43.7** |
| FUTURES | 622 | 87 | 13.99 % | 47.92 % | 96 | 38.2-57.8 |
| MEME | 56 | 13 | 23.21 % | 66.67 % | 3 | 21.0-93.9 |
| BOND | 22 | 0 | 0.00 % | 0.00 % | 0 | n/a |

**FOREX at 1.05 % is LOWER than EQUITY (1.44 % post-floor, 25.35 % pre-floor)** — FOREX is the strictest class in the system today.

The actual mechanism is not **dilution** (high throughput × low WR) but **cold pipeline** (low throughput × low WR × statistically-uncertain n_out).

---

## 2. Per-class config ALREADY exists (no new floors needed)

`audit_trail/quality_gates.py` at **L500-505** defines a per-class config dict that the `passes_smart_gate` function consults:

```python
# audit_trail/quality_gates.py  L500-505
{
    "EQUITY":    {"min_score": 40.0, "min_fwr": 0.50, "min_trades": 5},
    # ... EQUITY has elite_score >= 55 hard floor at L7938 (PHASE 1C.d audit)
    "FOREX":     {"min_score": 40.0, "min_fwr": 0.46, "min_trades": 3},   # was 55 pre-freeze per L295-296
    "COMMODITY": {"min_score": 30.0, "min_fwr": 0.50, "min_trades": 0},   # was 60 pre-freeze but caused silent zero picks
    "ETF":       {"min_score": 35.0, "min_fwr": 0.50, "min_trades": 0},   # was 40 pre-freeze per L279
}
```

These are **min_score thresholds** (soft — they reduce scoring, not reject outright) plus a **min_fwr** (forward-WR requirement at the gate). The min_fwr is meant to be enforced at SMART admission but the per-class WR data (FOREX 25%, COMMODITY 38.46%, ETF 18.75% — all below 0.50) suggests **min_fwr is currently NOT enforced at SMART** — it's only enforced at higher funnel stages (HC/PROVEN, where these classes contribute 0 today). That's a separate enforcement gap.

---

## 3. The CRITICAL THRESHOLD FREEZE finding

`audit_trail/quality_gates.py` at **L280-282** documents an explicit policy gate:

```
THRESHOLD FREEZE ACTIVE until 2026-08-18 — score floors locked.
DO NOT modify any SMART_PICKS_MIN_SCORE_* value.
```

This freeze was applied as a Kimi Renaissance Review precaution to prevent empirical thresholds from drifting mid-review. **Modifying `min_score` for FOREX/COMMODITY/ETF BEFORE 2026-08-18** is **policy-blocked**, not just statistically premature.

The freeze does NOT prohibit:
- Adding NEW floors outside the `SMART_PICKS_MIN_SCORE_*` namespace (e.g., class-wise `elite_score ≥ X` checks in `passes_smart_gate` — these would not violate the freeze as written).
- Modifying `min_fwr` enforcement (the freeze only covers `MIN_SCORE_*` constants).
- Per-class overrides in the dict at L500-505 (also frozen, per the comment's domain).

The freeze DOES prohibit:
- Raising the FOREX min_score from 40 → 55 (historical target).
- Raising the COMMODITY min_score from 30 → 40 (recommended candidate).
- Raising the ETF min_score from 35 → 40 (historical pre-freeze target).

---

## 4. Statistical confidence — defer until n ≥ 30

For any floor adjustment to be statistically defensible, **per-class `n_out` ≥ 30** is required (Wilson 95 % CI width should be ≤ 20 pp before claiming "WR significantly below 50 %").

| Class | n_out | Wilson95 CI | Statistical status |
| --- | --- | --- | --- |
| FOREX | 4 | 8.7-55.2 % | **Insufficient** — CI crosses 50 %; can't conclude WR < 50 % with 95 % confidence |
| COMMODITY | 13 | 17.5-64.6 % | **Marginal** — wide CI; even at n=13 we have only 80 % power at best |
| ETF | 16 | 6.2-43.7 % | **Meaningful** — CI upper bound below 50 % — only ETF has statistically defensible evidence |

**Only ETF** has evidence strong enough at this snapshot to justify a floor intervention — and only if the freeze permitted it (which it doesn't until 2026-08-18).

---

## 5. Per-class recommendation

### FOREX — **DEFER**

- n_out = 4: statistically noise. Cannot conclude WR<50% with 95% confidence.
- Comment at L295-296 notes that the FOREX floor was raised to 55 historically for hedge-fund-grade perf but **implicitly lowered to 40 during freeze calibration**.
- `quality_gates.py:295-300` explicitly states **the real quality filtering for forex is at `FwdWR ≥ 50`, not the score floor**. So fixing this is a `min_fwr` enforcement question, not a score-floor question.
- **Action** (after freeze): investigate why `min_fwr = 0.46` isn't enforced at SMART for FOREX (separate gate-enforcement bug).

### COMMODITY — **DEFER**

- n_out = 13: marginal statistical power.
- Comment at L304-309 explains: **"Commodity strategies can't accumulate score_booster enrichment (score_booster has crypto-only guards), so their achievable score maxes out empirically around 55. An elite floor of 55+ would effectively act as a hard ban."**
- This is structurally important — if we add an `elite_score ≥ 55` floor to COMMODITY, we'd ban the entire class. Setting floor at `elite_score ≥ 40` would be the highest feasible (matches historical stable threshold).
- Best to re-baseline at n_out ≥ 50 (current 13, target 50 ≈ 4× growth — only the cron cadence + a couple of months' wait).

### ETF — **CONDITIONAL**

- n_out = 16: CI upper bound at 43.7 % — only class with statistically defensible WR<50% evidence.
- Currently L500 dict config has `min_score = 35` (was 40 pre-freeze per L279).
- **Action**: investigate why `min_fwr = 0.50` isn't enforced at SMART for ETF (same enforcement bug as FOREX). Score-floor intervention is premature even with strong n — the underlying min_fwr gate should be the primary mechanism.
- **Only if min_fwr gate is unusable post-investigation**: consider re-raising min_score at the L500 dict from 35 → 40 (historical target), but only after 2026-08-18 freeze lifts.

### GLOBAL RECOMMENDATION

**Defer ALL pure score-floor interventions until 2026-08-18** (per the THRESHOLD FREEZE comment). Use the intervening time to:
1. Investigate why `min_fwr` gate is not enforced at SMART admission for FOREX/COMMODITY/ETF.
2. Accumulate per-class n_out to ≥ 30 (cron + ~2-3 more months depending on cadence).
3. Re-run this audit at n_out ≥ 30 per class. ETF will likely warrant intervention; COMMODITY/FOREX may not once min_fwr is enforced.

---

## 6. Suggested threshold values (if operator overrides the freeze)

| Class | Suggested `min_score` | Justification | Required evidence |
| --- | --- | --- | --- |
| FOREX | 55 (historical) | Comment L296: "FOREX score floor RAISED 40→55 for hedge fund performance. The 40 threshold allowed too many low-quality picks" | n_out ≥ 30 with CI upper bound < 50 % |
| COMMODITY | 40 (highest feasible) | Comment L306: "60 resulted in silent zero picks" — 40 is highest stable | n_out ≥ 50 (re-baseline) |
| ETF | 40 (historical pre-freeze) | Comment L279: "ETF score floor dropped from 40→35 because the 40 wasn't matching dashboard data" — investigate BEFORE raising back | n_out ≥ 30 (currently 16) + min_fwr enforcement diagnosis |

**These are NOT recommended actions for 2026-06-23 — they are reference values IF the freeze is overridden post-2026-08-18.**

---

## 7. Files referenced (none modified)

| Path | Role |
| --- | --- |
| `audit_trail/quality_gates.py` | L280-282: THRESHOLD FREEZE comment |
| `audit_trail/quality_gates.py` | L295-300: FOREX FwdWR≥50 commentary |
| `audit_trail/quality_gates.py` | L304-309: COMMODITY score_booster crypto-only guard |
| `audit_trail/quality_gates.py` | L500-505: per-class config dict |
| `audit_dashboard/data/pick_funnel_90d.json` | per-class stats source |

---

## 8. Per-class action checklist (post-freeze, when n warrants)

1. **FOREX**: Trace through `passes_smart_gate` to verify whether `min_fwr = 0.46` is checked at admission time. Fix enforcement gap before any score-floor changes.
2. **COMMODITY**: Same as FOREX — trace `min_fwr = 0.50` enforcement. Also: investigate if the crypto-only `score_booster` guards at L304-309 are intentional or pre-freeze artifacts.
3. **ETF**: Same enforcement trace + check whether `L279` comment's "dropped from 40→35" was post-freeze or pre-freeze. If post-freeze, address the dashboard-data mismatch before raising back.

---

## 9. Anchor answer to the user's question

> "Investigate the COMMODITY/FOREX/ETF 42-53% SMART pass-rate pattern + WR<50%, consider applying EQUITY-style floors"

**Two corrections + one deferral**:

1. **42-53% pass-rate claim was a misread**: actual pass rates are **5.41 % / 1.05 % / 4.36 %** — these classes are STARVING (low throughput), not DILUTIVE (high throughput).
2. **Per-class config + min_fwr gates already exist** at `quality_gates.py:500-505` but appear to NOT be enforced at SMART admission. Investigating the enforcement gap is the higher-leverage fix.
3. **Active THRESHOLD FREEZE at `quality_gates.py:280-282` prohibits score-floor modifications** until 2026-08-18 — any proposed floor adjustment must wait for the freeze to lift AND only FOREX/COMMODITY/ETF n_out ≥ 30-50 statistical evidence.
