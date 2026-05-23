# HEDGE_FUND_ENHANCEMENT_PR_2026_05_02 - Codebase Gap Review

Date: 2026-05-02  
Scope: Compare `HEDGE_FUND_ENHANCEMENT_PR_2026_05_02` recommendations against the current repository implementation and propose practical next steps.

## Inputs Reviewed

- `C:/Users/zerou/Downloads/HEDGE_FUND_ENHANCEMENT_PR_2026_05_02.docx` (via extracted artifacts)
- `.tmp_research/kimi_docx_extracted.txt`
- `.tmp_research/kimi_docx_tables.txt`
- `.tmp_research/kimi_pr658_master.md`
- `reports/KIMI_DOCX_VS_PR658_GAPS_2026_05_02.md`

## Current-State Mapping (DOCX vs Code)

| Recommendation Theme | Status | Evidence in Repo | Notes |
|---|---|---|---|
| Keep/relax high-confidence winner blocking | Partial | `alpha_engine/forward_validator.py` uses `WINNER_FILTER` with `confidence_max: 0.85` and `rr_min: 1.5`; `audit_dashboard/hc_filter.js` no longer uses prior confidence dead-band gate | High-confidence filtering still exists in Python path even though dashboard JS path was relaxed |
| Replace `elite_score` as primary crypto quality gate with ML-based signal | Partial | `audit_trail/quality_gates.py` has ML paths but `SMART_PICKS_MIN_ML_SCORE = 0.0`; `config/hf_quality_gates.json` keeps `min_elite_score` while `enabled` is false | Not fully aligned to DOCX recommendation of explicit ML thresholding as primary gate |
| Lower R:R floor from 1.5 to 1.25 | Missing (active paths) | `audit_trail/quality_gates.py` keeps `SMART_PICKS_MIN_RR = 1.5`; `alpha_engine/forward_validator.py` winner filter uses `rr_min: 1.5` | Optional JSON has different values, but main enforcement remains 1.5 |
| `forward_wr` pipeline and strat-level metrics | Implemented | `audit_dashboard/hc_filter.js` and `audit_trail/quality_gates.py` consume `strat_fwd_wr` / `forward_wr` / trade counts | Forward metrics are actively used in gating logic |
| Move to symbol-direction track metrics (`track_wr`) | Partial | `sym_track_wr` appears in `audit_trail/dashboard_generator.py` and `audit_trail/quality_gates.py`; standalone `track_wr` is not uniformly canonical | Direction-aware tracking exists but not as a single normalized universal field across all paths |
| Resolver reliability and force-close behavior | Partial | `updates/2026-05-02-audit-report-enhancements.md` identifies concrete resolver fixes; not all recommendations confirmed as landed | Reliability work is documented but should be validated in code/tests before broad gate relaxation |

## Key Contradictions or Stale Assumptions

1. The DOCX framing implies some filters are absent or hidden; in current code, `WINNER_FILTER` is explicit and active in `alpha_engine/forward_validator.py`.
2. The DOCX implies immediate simple swap from `elite_score` to `ml_score`; actual code has mixed gate layers and disabled/optional config paths, so behavior is more fragmented than a single threshold change.
3. The DOCX recommends R:R floor 1.25 as a quick change, but active enforcement remains 1.5 in core gate paths.

## Suggested Priority Actions

## P0 - Evidence and Safety First

- Confirm resolver health and data integrity before gate loosening:
  - verify unresolved-pick rates and fallback behavior in `alpha_engine/outcome_resolver.py`
  - verify post-fix stability in recent audit outputs before changing thresholds
- Add/verify tests that specifically cover:
  - retry cap and force-close behavior
  - forward metric propagation to gating payloads
  - high-confidence pick handling through both Python and JS gate paths

## P1 - Gate Alignment

- Align `WINNER_FILTER` confidence cap with current HC policy (or remove fully), but do it intentionally in one place with telemetry:
  - `alpha_engine/forward_validator.py`
- Introduce explicit ML floor with guardrails in smart gate path:
  - `audit_trail/quality_gates.py`
- Decide and enforce one R:R floor policy across all active gates:
  - `audit_trail/quality_gates.py`
  - `alpha_engine/forward_validator.py`
  - supporting config files in `config/`

## P2 - Schema and Metric Normalization

- Standardize forward/track fields so all gating and dashboard layers consume a consistent tuple-level metric (strategy/symbol/direction):
  - producer/normalizer in pipeline
  - consumer alignment in `audit_dashboard/hc_filter.js`, `audit_trail/quality_gates.py`, and dashboard generators
- Add a compatibility map for legacy aliases and a single canonical output contract.

## Practical Implementation Order

1. Resolver correctness + regression tests.
2. Gate telemetry visibility (block reasons and confidence/R:R distributions).
3. Controlled gate recalibration (ML floor, confidence ceiling, R:R floor) with one change per release step.
4. Track-metric normalization and dashboard parity updates.

## Final Recommendation

The DOCX is directionally strong on identifying gate misalignment risk, but the repository state shows mixed gate ownership and partial prior fixes. The fastest safe path is not a single global threshold flip; it is a staged alignment:

- stabilize resolver + metric integrity,
- unify active gate definitions,
- then apply the DOCX threshold ideas with measurement and rollback criteria.
