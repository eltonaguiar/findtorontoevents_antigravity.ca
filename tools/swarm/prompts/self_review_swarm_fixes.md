# Self-Review: Swarm PR #818 Gap Fixes

You are reviewing 3 code changes applied to the swarm tooling to close gaps from PR #818 (Swarm Resilience). Review them and output your verdict as JSON.

## Files Changed

### 1. tools/swarm/worker_runner.py — Empty-envelope retry
Added retry-on-empty-output to `call_gemini`, `call_opencode_or_kilo`, and `call_copilot`. Pattern:
```python
rc, out, err = _run(cmd, ...)
if rc == 0 and not out.strip():
    time.sleep(1)
    rc, out, err = _run(cmd, ...)  # single retry
```
Before this fix, CLI engines returning rc=0 with 0-byte output would silently fail. The transient CLI init race (observed in swarm_runs/_calls.jsonl) now gets one recovery attempt.

### 2. tools/swarm/swarm_run.py — Pre-flight API key skip
Added a block that imports ENGINE_KEY_ENVS from config_loader and skips API engines with missing keys before dispatching workers. This saves 2-10s per engine that would otherwise fail with "no key in env". Skips are logged clearly; return code 5 if all engines are skipped.

### 3. tools/swarm/config_loader.py — Key-env alias sync
Added CEREBRAS_API_KEY_PAID and CEREBRAS_API_KEY_FREE to cerebras entry (previously only had CEREBRAS_API, CEREBRAS_API_KEY, CERBRAS_FREE_ITHINK). Added OPENROUTER_API_KEY to openrouter entry (previously only had OPENROUTER). Now matches the key resolution order in api_consult.py PROVIDERS.

## Review Tasks

1. Read the 3 modified files
2. Verify each fix is correctly implemented
3. Check for regressions or missed edge cases
4. Output JSON:
```json
{
  "verdict": "APPROVE" or "CHANGES_REQUESTED",
  "per_file": {
    "worker_runner.py": {"ok": true/false, "notes": "..."},
    "swarm_run.py": {"ok": true/false, "notes": "..."},
    "config_loader.py": {"ok": true/false, "notes": "..."}
  },
  "overall_notes": "..."
}
```

Files to read:
- tools/swarm/worker_runner.py (functions: call_gemini, call_opencode_or_kilo, call_copilot)
- tools/swarm/swarm_run.py (pre-flight check block after "return 3")
- tools/swarm/config_loader.py (ENGINE_KEY_ENVS for cerebras and openrouter)
