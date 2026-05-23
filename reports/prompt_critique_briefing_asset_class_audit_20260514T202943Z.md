# Prompt critique

## Summary verdict
`NEEDS_SCAFFOLDING`

The prompt has a solid skeleton but lacks critical constraints that will cause high variance across engines. The main issues are: (1) engines cannot actually access the referenced files, (2) the JSON schema is underspecified, (3) the task mixes analysis with file-checking that's impossible to perform.

## Suggested rewrites

- **"Read the full optimization review at `updates/2026-05-14-per-asset-class-prediction-optimization-review.md`. Then also check the actual data files..."** → Remove or replace with: "Assume the findings in the SYSTEM STATE and ARCHITECTURE FINDINGS sections are verified. Do NOT attempt to access external files. Base your assessment solely on the data provided in this prompt."

- **"Be data-driven. Check the actual numbers in the code and data files. Do NOT guess. If you can't verify something, say so explicitly."** → Replace with: "Base your analysis exclusively on the SYSTEM STATE table and ARCHITECTURE FINDINGS listed above. If you need data not provided, state 'Cannot verify from given data' rather than fabricating."

- **The JSON output schema** → Add explicit constraints: "For `agree` and `disagree` arrays, use exact finding numbers (e.g., 'finding1', 'finding2') as they appear in the ARCHITECTURE FINDINGS section. For `do_first`, `do_later`, `skip` arrays, use exact proposal IDs (P1-P8, Q2). Limit `risks` to maximum 5 items. Limit `alternative_approaches` to maximum 3 items."

- **"validation_of_findings" → "missing"** → Add: "Only include findings that are DIRECTLY contradicted by the SYSTEM STATE table. For example, if a finding claims COMMODITY has no boosters but the table shows PF=4.03, that's a valid observation, not a contradiction."

## Overlooked topics (consider adding)

- **Trade-off analysis between proposals**: Which proposals conflict with each other? (e.g., P4 normalization might break P2/P8 boosters)
- **Implementation complexity estimate**: Which proposals are quick wins vs. multi-week engineering efforts?
- **Dependency ordering**: Some proposals must be implemented before others (e.g., P6 should precede P2 since P2 assumes no liquidity penalty)
- **Backtesting requirement**: Which proposals need historical simulation before production deployment?
- **Monitoring/rollback plan**: How to detect if a change degrades performance

## Ambiguities flagged

- **"stable" / "stressed" / "thin_sample"** — No definition of what these statuses mean or how they were determined
- **"PF"** — Not defined. Profit Factor? Performance Factor? Different engines may assume different meanings
- **"score"** — What's the range? Is 60 good or bad? The prompt says "a score of 60 means different edge quality" but doesn't say what 60 means in any class
- **"Elite Floor"** — Not defined. What does lowering it from 65→55 actually change?
- **"P5" is missing** — The proposals jump from P4 to P6. Engines may hallucinate a P5 or question data integrity
- **"Q2"** — What does Q2 mean vs P proposals? Different classification scheme without explanation

## Estimated variance reduction
`HIGH (>30%)`

Without file access and with ambiguous schema, engines will produce wildly different outputs. Some will fabricate file contents, others will refuse, others will guess. Fixing the file-access issue and tightening the schema would dramatically reduce variance.

## Best engine for THIS prompt
**deepseek** — Best at following structured JSON schemas and admitting uncertainty rather than fabricating data. Also handles multi-condition logic well for the prioritization task.