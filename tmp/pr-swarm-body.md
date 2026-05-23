## Summary
Adds two resilience improvements to the swarm runner, addressing failure patterns seen in the latest runs (2026-05-04/05).

## Issues Fixed
1. **Pre-flight API Key Check** — `swarm_run.py` now skips API engines (`deepseek`, `cerebras`, `xai`, `nous`, `openrouter`, etc.) when their required API key env vars are missing. Previously these engines would spawn, retry, and fail with `no key in env`, wasting time and cluttering `_calls.jsonl`.
2. **Empty Envelope Retry** — CLI engines (`kilo`, `opencode`, `gemini`, `copilot`, `kimi`) occasionally return `rc=0` with zero output due to transient initialization races. `worker_runner.py` now retries once with a 1-second backoff before giving up.

## Also on this branch
- Cerebras SDK fallback to OpenAI-compatible HTTP (already committed) — when `cerebras-cloud-sdk` is not installed, falls back to plain HTTP instead of hard-failing.

## Evidence
See `updates/2026-05-05-swarm-resilience-fixes-evidence.md` for full methodology, log excerpts, and regression risk assessment.

## Verification
- Python syntax check passes for both modified files.
- No breaking changes to CLI interface or output schema.
