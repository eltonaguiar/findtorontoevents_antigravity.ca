# Swarm + Ruflo Independent Code Review — Bug Report (2026-05-05)

**Scope:** Independent audit of `tools/swarm/` and `.ruflo/` (orchestrator, worker_runner, swarm_run, swarm_followup, api_consult, config_loader, session_manager, safety, swarm_inspect, swarm_stats, swarm_janitor, _engine_overrides, and the ruflo orchestrator/agents).

**Result:** 1 confirmed bug fixed, 3 observations documented. (PR #822 by Copilot already fixed 4 additional bugs.)

---

## Bug 1 — `.ruflo/orchestrator.py`: Malformed JSON example in bug_hunter goal (medium)

**File:** `.ruflo/orchestrator.py` line 249

**What was broken:**
The `bug_hunter` agent's goal string contained a malformed JSON example:
```python
"Return JSON: {\"bugs\": [{\"file\", \"line\", \"severity\", \"fix\"}]}"
```

The keys in the JSON object example were separated by commas instead of colons — `"file\"` should be `"file\": \"<path>\"`. This was misleading for the agent and could cause it to emit similarly malformed JSON.

**Fix applied:**
```python
"Return JSON: {\"bugs\": [{\"file\": \"<path>\", \"line\": \"<num>\", \"severity\": \"<HIGH|MEDIUM|LOW>\", \"fix\": \"<description>\"}]}"
```

**Why it matters:**
The bug_hunter agent reads its goal text and tries to match the JSON shape. A malformed example increases the chance the agent emits invalid JSON, which then requires expensive fallback parsing in `worker_runner.py:_extract_json_object()`.

---

## Observation 1 — `orchestrator.py`: `verify_hermes()` returns `True` even when binary exits non-zero

**File:** `.ruflo/orchestrator.py` lines 313-328

```python
def verify_hermes():
    try:
        result = subprocess.run([HERMES_BIN, "--version"], ...)
        if result.returncode == 0:
            version = result.stdout.strip() or result.stderr.strip()
            print(f"[ORCHESTRATOR] Hermes: {version}")
            return True
    except Exception as e:
        print(f"[ORCHESTRATOR] ERROR: Hermes not accessible: {e}")
        return False
    print(f"[ORCHESTRATOR] ERROR: Hermes returned non-zero exit code")
    return False  # <-- this is never reached!
```

The `return False` on line 328 is unreachable — if `returncode != 0`, the function falls through to the error print but still returns `None` (which is truthy in Python). 

**Why not fixed:** The current code still works because `None` is treated as falsy in the `if not verify_hermes()` check in `main()`. The fix is cosmetic/defensive.

---

## Observation 2 — `orchestrator.py`: `run_hermes_tmux()` always waits full timeout

**File:** `.ruflo/orchestrator.py` lines 426-484

The `run_hermes_tmux()` fallback uses `time.sleep(timeout)` to wait for the tmux session to complete. Even if the agent finishes in 30 seconds, the function waits the full timeout (default 300s).

**Why not fixed:** This is a known limitation of the tmux fallback path. A proper fix would poll `tmux list-sessions` to detect completion, but the tmux path is already a last-resort fallback. Not worth the complexity.

---

## Observation 3 — `worker_runner.py`: `_extract_json_object()` may return None silently

**File:** `tools/swarm/worker_runner.py` lines 273-308

The function has 4 fallback strategies for extracting JSON from engine output. If all fail, it returns `None`. The caller in `main()` checks `if obj is None:` and builds a fallback envelope — but if the raw output was actually valid JSON that just didn't have the expected keys, the function might incorrectly return `None`.

**Why not fixed:** The current behavior is defensive — returning `None` forces the fallback envelope which preserves the raw output in `commentary_text`. A false negative (saying "not JSON" when it actually was) is better than a false positive (saying "valid JSON" when it isn't).

---

## Summary of fixes (this PR + PR #822)

| Bug | File | Severity | Status |
|-----|------|----------|--------|
| Stale ALL_ENGINES in swarm_followup.py | tools/swarm/swarm_followup.py | Critical | Fixed in PR #822 |
| Duplicate try/except in swarm_run.py | tools/swarm/swarm_run.py | Medium | Fixed in PR #822 |
| transport_status = "200" vs "ok" | tools/swarm/api_consult.py | Low | Fixed in PR #822 |
| KeyError not caught in _load_yaml_config | swarm_run.py + swarm_followup.py | Medium | Fixed in PR #822 |
| Malformed JSON example in bug_hunter goal | .ruflo/orchestrator.py | Medium | **Fixed in this PR** |

---

## Testing

- `tests/test_swarm_tooling.py` — 2/2 tests pass ✅
- Python syntax check (`py_compile`) — all 5 files pass ✅
