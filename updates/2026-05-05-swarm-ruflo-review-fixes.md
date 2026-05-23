# SWARM + RUFLO Review Fixes (tools/swarm, .ruflo, swarm_runs)

Date: 2026-05-05
Reviewer: GitHub Copilot (GPT-5.3-Codex)

## Scope Reviewed

- tools/swarm core runtime and provider wiring
- .ruflo orchestrator/provider integration touchpoints
- swarm_runs evidence (historical failures and error patterns)

## Bugs Found

### 1) Provider alias mismatch: gemini_api engine could not run

What was broken:
- tools/swarm uses engine name gemini_api (in worker and run presets)
- tools/swarm/api_consult.py accepted provider gemini (not gemini_api)
- Result: any run using gemini_api failed at CLI provider validation instead of making an API call

Why this is a real bug:
- Engine lists and presets must be executable end-to-end
- A mismatched provider name turns a configured engine into a guaranteed failure path

Fix:
- Added provider alias mapping in tools/swarm/api_consult.py:
  - gemini_api -> gemini
- Updated provider resolution in main() so dispatch and errors use the resolved provider

### 2) Key isolation mismatch: valid API keys could be dropped in worker subprocesses

What was broken:
- tools/swarm/safety.py ENGINE_REQUIRED_KEYS was behind current key alias usage
- openrouter allowed OPENROUTER but omitted OPENROUTER_API_KEY
- cerebras omitted CEREBRAS_API_KEY_PAID and CEREBRAS_API_KEY_FREE

Why this is a real bug:
- worker_runner.py launches API consult calls with isolated_env(engine)
- Missing aliases in isolated env means API key exists in parent shell but is not visible to worker subprocess
- This causes avoidable no-key failures

Evidence in swarm_runs:
- swarm_runs/_calls.jsonl contains repeated openrouter failures checked against only ('OPENROUTER',)
- This pattern is consistent with alias drift and env filtering mismatch

Fix:
- Updated tools/swarm/safety.py:
  - openrouter now passes OPENROUTER_API_KEY, OPENROUTER, OPENROUTER_MODEL
  - cerebras now passes CEREBRAS_API_KEY_PAID, CEREBRAS_API_KEY_FREE, CEREBRAS_API, CEREBRAS_API_KEY, CERBRAS_FREE_ITHINK, CEREBRAS_MODEL

## Files Changed

- tools/swarm/api_consult.py
- tools/swarm/safety.py

## Verification

1. Syntax:
- python -m py_compile tools/swarm/safety.py tools/swarm/api_consult.py

2. Provider alias runtime behavior:
- "ping" | python tools/swarm/api_consult.py --provider gemini_api -
- Result: provider resolves and fails with expected key error (not invalid provider)

3. Safety env passthrough checks:
- Verified OPENROUTER_API_KEY appears in isolated_env('openrouter')
- Verified CEREBRAS_API_KEY_PAID/CEREBRAS_API_KEY_FREE passthrough in isolated_env('cerebras')

## Feedback / Recommended Follow-ups

1. Add a small parity test that diffs:
- tools/swarm/swarm_run.py ALL_ENGINES
- tools/swarm/worker_runner.py API_ENGINES + CLI_ENGINES
- tools/swarm/api_consult.py SUPPORTED_PROVIDERS (+ aliases)
- tools/swarm/safety.py ENGINE_REQUIRED_KEYS
- tools/swarm/config_loader.py ENGINE_KEY_ENVS

This would catch the exact class of drift fixed here before merge.

2. Add a preflight self-check command in tools/swarm (for CI and local):
- Validate engine/provider names
- Validate key-env alias parity
- Emit actionable mismatch report

3. Normalize terminology:
- Prefer one canonical label for Gemini across all files (gemini_api externally, gemini internal alias is fine)

## PR Intent

This PR is intentionally narrow: only concrete runtime bugs with direct execution impact were changed. No behavior-only refactors or formatting-only edits were included.
