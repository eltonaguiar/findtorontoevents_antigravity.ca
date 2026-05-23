# Notes For Freebuff / Copilot

## What I fixed

I added a real keyless local-model path so Ruflo and swarm runs are not blocked when free API keys are exhausted or missing.

Main changes:
- Added `ollama_local` support in `tools/swarm/api_consult.py`.
- Wired `ollama_local` into `tools/swarm/worker_runner.py` as a supported API engine.
- Added `ollama_local` to swarm runner presets/cost tables in `tools/swarm/swarm_run.py`.
- Allowed local ollama env passthrough in `tools/swarm/safety.py`.
- Added Ruflo tier routing in `.ruflo/orchestrator.py` so it can use:
  - `--tier free`
  - `--tier paid`
  - `--tier hybrid`
  - `--tier local`
  - `--tier auto`
- Fixed Ruflo dispatch drift where swarm functions were already passing `tier=...` into `run_agent(...)` even though that function did not yet accept the `tier` argument.
- Switched Ruflo local defaults to lightweight local models so smoke runs are less likely to timeout.

## Why I fixed it

The latest swarm/Ruflo issue pattern pointed at provider/key exhaustion and missing no-key fallback options.

That left two failure modes:
- Free API routes still required keys and could fail when quotas or keys were unavailable.
- Ruflo had partial tier plumbing that could break at runtime instead of cleanly falling back.

The new local tier gives the repo a path that does not require any remote API key at all, as long as local `ollama` is installed and a model such as `llama3.2:3b` is present.

## How it was checked

Validation performed:
- Python compile check across the changed files.
- `python .ruflo/orchestrator.py --check-keys --no-verify`
- `python .ruflo/orchestrator.py --swarm github --tier local --no-verify --timeout 120`

Observed result:
- The local-tier GitHub hygiene run completed and saved an insight file under `swarm_runs/ruflo-insights/`.

## Backup created before this note

Before adding this note, I created a backup branch at the existing commit:
- `backup/keyless-local-model-tier-pre-notes-2026-05-05`

## Current feature branch

- `feat/keyless-local-model-tier`

## Operational note

For keyless execution, the expected local setup is:
- `ollama` installed on the machine
- a lightweight model available locally, preferably `llama3.2:3b`

Recommended examples:
- `python .ruflo/orchestrator.py --swarm github --tier local --no-verify --timeout 120`
- `python .ruflo/orchestrator.py --swarm all --tier auto --timeout 120`
