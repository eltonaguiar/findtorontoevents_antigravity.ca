# BESTIEJOB prototypes (started)

Starter artifacts to give other agents concrete extension points (aligned with `eltonaguiar/BESTIEJOB` `scan_boards.py`/`render_board.py`/`AGENT-RUNBOOK (2).md` review).

## Layout
- `job_signal_matcher.py` — body/cert-aware track classifier (SN/SF/Other incl. ITSM/CMDB/ITAM; CSA/CAD/CIS/ITIL/PD/CTA, FR hints) + Toronto/GTA & Canada/Ontario-remote geo/eligibility heuristics. JSON/JSONL in → JSONL with `match`.
- `normalize_lead.py` — maps scan_boards-like leads/snapshots to draft canonical records (`bestiejob.normalized_lead_draft.v0`): normalized URLs (tracking stripped), dedupe key, match evidence, dates/liveness/review placeholders. `--demo` available.
- `verify_leads.py` — **offline** verification stub: normalized JSONL → verification-enriched JSONL + summary (`pass/review/reject`, gate reasons; never fabricates dates/liveness).
- `eval_matcher.py`, `eval_relevance.py` — expectation and precision/recall/threshold harnesses (JSON/text reports).
- `adapter_contract.py`, `adapter_tenant_config.example.json` — adapter interface/limits/config/lead stubs (incl. Workday CXS plan stub).
- `fixtures_sample*.jsonl` — small demo set.
- `fixtures_matcher_cases*.jsonl` / `.labels.json` — 27-case curated+relevance-labeled set with classified/normalized/verified outputs.
- `EVAL_REPORT.md`, `eval_matcher_report.json`, `eval_relevance_report.json`, `VALIDATION_NOTES.md`, `verify_summary.json` — evaluation/validation snapshots.
- `SCHEMA_MAPPING.md`, `VERIFICATION_STAGE.md`, `ADAPTER_COVERAGE_PLAN.md`, `CI_PIPELINE_FIT.md`, `TODO_STATUS.md` — alignment, design, plan, gates, tracked actions.
- `llm-delegated/*.md` — drafts produced via local models (LiteLLM/Hermes): keywords/certs, geo heuristics, schema/test ideas (some partial; treat as input).

## Run
```bash
python3 ideas/bestiejob/prototypes/job_signal_matcher.py --demo
python3 ideas/bestiejob/prototypes/job_signal_matcher.py ideas/bestiejob/prototypes/fixtures_matcher_cases.jsonl > out.classified.jsonl
python3 ideas/bestiejob/prototypes/normalize_lead.py --demo
python3 ideas/bestiejob/prototypes/normalize_lead.py ideas/bestiejob/prototypes/fixtures_matcher_cases.jsonl > out.normalized.jsonl
python3 ideas/bestiejob/prototypes/verify_leads.py out.normalized.jsonl --output out.verified.jsonl --summary verify_summary.json
python3 ideas/bestiejob/prototypes/eval_matcher.py --classified ideas/bestiejob/prototypes/fixtures_matcher_cases.classified.jsonl --labels ideas/bestiejob/prototypes/fixtures_matcher_cases.labels.json
python3 ideas/bestiejob/prototypes/eval_relevance.py --classified ideas/bestiejob/prototypes/fixtures_matcher_cases.classified.jsonl --labels ideas/bestiejob/prototypes/fixtures_matcher_cases.labels.json
```

## Next ideas for others
- Calibrate patterns/weights on labeled positives/negatives (FR terms, cert-in-body-only, false positives); add precision/recall harness.
- Align draft normalized schema to canonical BESTIEJOB/inbox fields and verification/gating outputs (absolute posted_at, liveness 404/410/451, rights/evidence).
- Add Workday/other adapter inputs; feed verified-only rows; expand GTA/eligibility evidence handling.
- Integrate as pre-verify stage before dedupe/`tools/jobs_merge_inbox.py` under `bestiejob-main-write`.

See: `updates/2026-11-18-review-render-board-scan-boards-runbook.md`, `updates/2026-11-18-bestiejob-next-steps-progress.md`, `ideas/bestiejob/agent-execution-runbook.md`.
