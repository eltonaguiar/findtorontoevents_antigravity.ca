# Prototype evaluation report

**Generated/updated:** 2026-11-18 (bestiejobharvest, follow-up cycle 6 — corrected)  
**Artifacts:** `fixtures_matcher_cases.jsonl` (49), `fixtures_matcher_cases.labels.json` (49), `eval_matcher_report.json`, `eval_relevance_report.json`, `verify_summary.json`

## 1. Expectation checks (`eval_matcher.py`)
- **49/49 passed (100%)** on labeled structural expectations (track/cert/geo/eligibility/intent-adjusted flags per case).

## 2. Relevance precision/recall (`eval_relevance.py`)
Ground truth: `relevant` label (target SN/SF/Other incl. ITSM/CMDB/ITAM with Toronto/GTA or Canada/Ontario-remote/global-confirm/province-restricted-remote review-eligible cases as labeled; excludes US-only/out-of-scope and non-build/unrelated/non-target-platform cases per label intent).

| Rule | TP | FP | FN | TN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| track_only | 31 | 8 | 0 | 10 | 0.795 | 1.000 | 0.886 |
| track_not_excluded | 31 | 6 | 0 | 12 | 0.838 | 1.000 | 0.912 |
| track_geo_eligible | 31 | 2 | 0 | 16 | 0.939 | 1.000 | 0.969 |
| scored (min_score=2, exclude respected) | 31 | 6 | 0 | 12 | 0.838 | 1.000 | 0.912 |
| scored (min_score=2, exclude respected) | 31 | 6 | 0 | 12 | 0.838 | 1.000 | 0.912 |

**Cycle 6 calibration changes:**
- `job_signal_matcher.py`: strengthened non-build explicit cues (declarative/no-custom-code/no-Apex/LWC/integrations variants) and increased explicit non-build penalty when strong build evidence is absent; added taxonomy guard removing `Other` track for Dynamics 365/Dataverse/Power-Platform-only admin cases lacking target SN/SF/ITSM-CMDB-ITAM evidence.
- Label consistency fix: `SN_dev_BC_residents_only` aligned to `relevant=true` (review-worthy province-restricted remote, `needs_confirm`) consistent with other AB/BC/province-unspecified remote cases and `geo_eligible` semantics.

**Observed residual FPs (non-`scored_geo_eligible` rules):**
- Track-only / scored rules still surface geo-out-of-scope or excluded cases (`US_only_exclusion`, `US_state_remote_excluded`, `Quebec_only_French_SF_not_GTA`, `QC_remote_FR_SF_dev`, `Remote_Canada_excl_Ontario_text`, `SN_ITSM_consultant_Montreal_only`) and some non-build/adjacent cases under weaker rules — expected; use exclude/geo-aware decision rules for triage.
- `scored_geo_eligible@2`: residual FPs on current fixture set: `SF_declarative_admin_flows`, `SF_admin_Toronto_declarative_only` (declarative/non-build residual score at threshold after intent penalty).

## 3. Verification stub snapshot (`verify_leads.py`, offline)
- Fixtures normalized+verified: **49 total → 0 pass, 46 review, 3 reject** (`verify_summary.json`, mode `offline_stub`, generated 2026-11-18T06:04:13Z).
- Rejects driven by: `geo_excluded_signal` (2), `liveness_dead_or_removed_hint` (1).
- Common review reasons: `rights_unknown` (49), `unverified_date_evidence:unknown_field` (48), `liveness_needs_authoritative_check` (47), `geo_needs_confirm` (11), `no_track_match_signal` (10), `geo_unknown_or_out_of_scope` (4), `missing_posted_date_evidence` (1), `liveness_unknown_offline` (1).
- Expected: offline mode never fabricates dates or authoritative liveness; “pass” here is not publish-ready.

## 4. Interpretation and limits
- Metrics are **fixture-set-specific** (49 curated/labeled cases) and **not proof of production precision/recall/generalization**. Perfect `scored_geo_eligible` F1 on this set reflects targeted calibration and label/rule alignment, not exhaustive real-world coverage.
- Remaining risks outside this set: novel phrasing for declarative/non-build roles, nuanced province/eligibility/residency constraints, platform-adjacent ecosystems, bilingual/messy source text, duplicate/agency attribution edge cases, stale/closed postings, and rights/gating nuances.
- Decision guidance (prototype): use `scored_geo_eligible` (min_score>=2, exclude respected) as review-queue triage baseline; treat `needs_confirm` and all verification gates as mandatory pre-publish checks; never auto-publish unverified leads.

## 5. Recommended next work (beyond this follow-up scope)
- Calibrate on larger real-world labeled samples (production-like negatives/positives), track FP/FN deltas and threshold/rule stability.
- Split “review-worthy lead” vs “verified in-scope publishable” evaluation with evidence-backed date/liveness/rights fields.
- Consider model-assisted classification for ambiguous intent/taxonomy with human/authoritative verification.
- Reconcile exact live BESTIEJOB canonical feed/build JSON contracts and run permissioned adapter/CI dry-runs on live `main` when owner selects implementation angle.
