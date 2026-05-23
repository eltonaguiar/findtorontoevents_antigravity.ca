# 2026-05-05 Keyless Local Model Tier Integration

## What was broken

Ruflo and swarm workflows were still heavily dependent on API-keyed providers (OpenRouter and paid APIs), with no first-class keyless local path.

Observed issues:
- Local/no-key execution was not a supported provider in `tools/swarm/api_consult.py`.
- `worker_runner.py` and `swarm_run.py` could not select a dedicated keyless local provider engine.
- `.ruflo/orchestrator.py` had tier plumbing drift (`run_swarm_*` called `run_agent(..., tier=...)` while `run_agent` did not accept `tier`), which could fail runtime execution.
- Ruflo local attempts defaulted to heavier local models, increasing timeout risk for smoke runs.

## What changed

### 1) Added keyless local provider support in swarm API layer
- File: `tools/swarm/api_consult.py`
- Added `ollama_local` provider path that uses local `ollama run` and requires no API key.
- Added `OLLAMA_LOCAL_MODEL`/`OLLAMA_MODEL` fallback resolution.
- Extended sampling mapping so `max_tokens` correctly maps to `num_predict` for local ollama.
- Updated provider registry/CLI routing to expose `--provider ollama_local`.

### 2) Wired keyless engine into worker + runner
- File: `tools/swarm/worker_runner.py`
- Added `ollama_local` to `API_ENGINES` so worker dispatch can invoke it.

- File: `tools/swarm/swarm_run.py`
- Added `ollama_local` to `ALL_ENGINES`.
- Added `all-keyless-local` preset.
- Added zero-cost estimate entry for local ollama.

- File: `tools/swarm/safety.py`
- Added `ollama_local` env passthrough tuple (`OLLAMA_LOCAL_MODEL`, `OLLAMA_MODEL`, `OLLAMA_HOST`) for isolated worker runs.

### 3) Added Ruflo keyless local tier and stabilized tier dispatch
- File: `.ruflo/orchestrator.py`
- Made `REPO_ROOT` dynamic (`Path(__file__).resolve().parent.parent`) for cross-env portability.
- Added `API_CONSULT` path wiring.
- Added `LOCAL_MODELS` defaults (lightweight `llama3.2:3b`) to reduce timeout/cold-start failures.
- Added `run_local_no_key()` to execute agents through `api_consult.py --provider ollama_local`.
- Added/kept paid tier helper logic (`check_paid_keys`, `print_key_status`, `run_paid_api`) and role-provider mapping.
- Fixed `run_agent()` signature and dispatch to support tiers: `free`, `paid`, `hybrid`, `local`, `auto`.
- Updated CLI tier choices/help text and Hermes verification gating (`free|hybrid|auto` only).

## Evidence and methodology

### Methodology
1. Read current orchestrator and swarm API runner code paths.
2. Verified provider and engine registries (`api_consult`, `worker_runner`, `swarm_run`, `safety`) for keyless support gaps.
3. Implemented end-to-end integration from provider invocation to orchestration tier selection.
4. Ran compile and runtime smoke checks.

### Verification commands and outcomes
- `python -m py_compile tools/swarm/api_consult.py tools/swarm/worker_runner.py tools/swarm/swarm_run.py tools/swarm/safety.py .ruflo/orchestrator.py`
  - Result: success (no syntax errors).

- `python .ruflo/orchestrator.py --check-keys --no-verify`
  - Result: printed detected paid providers and key envs.

- `python .ruflo/orchestrator.py --swarm github --tier local --no-verify --timeout 120`
  - Result: success; generated local-tier insight file and compiled insights.

### Notes
- Local tier requires `ollama` installed/running and at least one local model available (defaults to `llama3.2:3b`).
- The new local path intentionally avoids any API key dependency.
