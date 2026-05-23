## Summary
Fixes three critical issues found in the latest Ruflo swarm runs (2026-05-05).

## Issues Fixed
1. **Model Passthrough Bug** — `hermes chat` was not receiving `--model`, causing `HTTP 404: No endpoints found for .` on all agent runs. Fixed by passing `--model` explicitly + adding a 3-attempt failover chain.
2. **Thread Safety** — `run_swarm_audit()` wrote to a shared `results` dict from multiple threads without `threading.Lock()`. Added a lock.
3. **Hardcoded REPO_ROOT** — Replaced `/mnt/c/findtorontoevents_antigravity.ca` with `Path(__file__).resolve().parent.parent` for portability.

## Evidence
See `updates/2026-05-05-ruflo-orchestrator-fixes-evidence.md` for full methodology, log excerpts, and regression risk assessment.

## Verification
- Python syntax check passes.
- No breaking changes to CLI interface.
