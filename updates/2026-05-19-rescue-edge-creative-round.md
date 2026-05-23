# Rescue edge creative round (2026-05-19)

## What

Multi-phase AI run (cloud question-factory → curated questions → local Ollama execute) to invent **creative diagnostic questions** per asset class for failing predictions on `/audit`, grounded in daily-ideas corpus + 11/11 killed harness hypotheses.

## Files added

- `reports/DAILY_IDEAS_DIGEST_FOR_RESCUE_2026-05-19.md`
- `reports/RESCUE_CURATED_QUESTIONS_2026-05-19.md`
- `reports/RESCUE_EDGE_CREATIVE_2026-05-19.md`
- `docs/swarm_prompts/RESCUE_QUESTION_FACTORY_v1.md`
- `docs/swarm_prompts/RESCUE_EDGE_EXECUTE_v1.md`
- `tools/rescue_edge_round.py`
- `tools/model_grill_sequential.py` — prompts `rescue_factory`, `rescue_execute`; waves `rescue_cloud`, `rescue_local`; staged prompts prefer `swarm_runs/_prompts/`

## Runs

| Phase | Dir | Result |
|-------|-----|--------|
| Cloud factory | `swarm_runs/model-grill/20260519T221642Z` | 4/5 OK (Qwen3.6-max timeout) |
| Local execute | `swarm_runs/model-grill/20260519T222015Z` | 3/4 OK (`deepseek-r1:14b` fail) |

## Verification

- `python tools/rescue_edge_round.py --phase curate --cloud-dir swarm_runs/model-grill/20260519T221642Z` → writes curated MD
- Cloud/local manifests under respective `manifest.json`

## Not done

- Qwen3.6-max retry with `--api-timeout 300`
- USB `gemma3:12b` local pass (optional)
- Harness pre-registration for H-035 tick (operator)
