# Swarm Smoke Runner Fix

## What Was Broken

The quick audit attachment smoke test exposed two `tools/swarm` reliability issues:

- `swarm_run.py` only loaded `.env` through YAML config mode, so flag-mode API runs could fail after `isolated_env()` dropped keys that were never hydrated into `os.environ`.
- `.env` hydration skipped keys that existed in the parent shell as empty strings, which could leave an API engine like `xai` with no usable key even when `.env` had one.
- The Copilot adapter invoked `copilot -p` with repo custom instructions enabled, allowing a small review prompt to turn into an unrelated local command-execution attempt.

## What Changed

- `tools/swarm/swarm_run.py` now loads `.env` before resolving engines in all invocation modes.
- `tools/swarm/config_loader.py` now treats empty parent-shell values as unset and fills them from `.env`.
- `tools/swarm/worker_runner.py` now bypasses the Windows npm `.cmd` shim and invokes the packaged `copilot.exe` directly, preserving multiline prompts and cmd metacharacters while keeping non-interactive, silent text mode with custom instructions and user prompts disabled for deterministic smoke/review output.

## Verification

Re-run the same Copilot, Mercury/Inception, and Grok smoke prompt with:

```powershell
python tools/swarm/swarm_run.py --prompt-file "swarm_runs/audit_attachment_smoke_prompt_2026_05_03.md" --engines copilot,inception,xai --out-dir "swarm_runs/audit_attachment_smoke_2026_05_03_rerun" --max-parallel 3
python tools/swarm/swarm_inspect.py "swarm_runs/audit_attachment_smoke_2026_05_03_rerun"
python tests/test_swarm_tooling.py
```
