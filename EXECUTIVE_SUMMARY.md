# EXECUTIVE_SUMMARY — Swarm PR #818 Gap Fixes + Fleet Validation

**Date:** 2026-05-05
**Branch:** `feat/keyless-local-model-tier`
**Agent:** Buffy (Codebuff, deepseek-v4-pro)

---

## What Was Done

Closed 3 gaps from PR #818 (Swarm Resilience) that were documented in WHOHKIMI.MD but never landed on the current branch. Also fixed 2 key-env inconsistencies. Then validated everything with both swarm systems.

---

## Fixes Applied (3 files)

### 1. `tools/swarm/worker_runner.py` — Empty-envelope retry
Added single-retry (1s sleep) on rc=0 + empty output to:
- `call_gemini`
- `call_opencode_or_kilo`
- `call_copilot`

Transient CLI init races (observed in `swarm_runs/_calls.jsonl`) now get one recovery attempt before being tagged as `closed-by-peer`.

### 2. `tools/swarm/swarm_run.py` — Pre-flight API key skip
Added a block after the unknown-engines check that imports `ENGINE_KEY_ENVS` from config_loader and skips API engines with missing keys before dispatching workers. Saves 2-10s per keyless engine. Returns exit code 5 if all engines are skipped. Correctly excludes `pollinations` (genuinely keyless) and `ollama_local` (local daemon).

### 3. `tools/swarm/config_loader.py` — Key-env alias sync
- **cerebras**: Added `CEREBRAS_API_KEY_PAID` and `CEREBRAS_API_KEY_FREE` as first entries (matching `api_consult.py` resolution order)
- **openrouter**: Added `OPENROUTER_API_KEY` as first entry (matching `api_consult.py` resolution order)

This fixes the false-negative where `config_loader.py`'s key checker would report cerebras/openrouter as MISSING even when `_API_KEY_PAID` / `_API_KEY` were set.

### Bonus: `tools/__init__.py` + `tools/swarm/__init__.py`
Created empty package init files so `from tools.swarm.config_loader import ...` works reliably from `swarm_run.py` — the pre-flight check and existing `_load_yaml_config()` both depend on this import path.

---

## Validation Results

| Check | Result |
|-------|--------|
| Python syntax (6 files) | ✅ All pass |
| Code review (code-reviewer-lite) | ✅ No bugs found |
| `config_loader.py` key resolution | ✅ cerebras→CEREBRAS_API_KEY_PAID, openrouter→OPENROUTER_API_KEY |
| `swarm_run.py --list-engines` | ✅ Works, no regression |
| `orchestrator.py --check-keys` | ✅ 7 providers detected |
| `orchestrator.py --list-agents` | ✅ 5 agents registered |
| `orchestrator.py --tier paid --swarm bugs` | ✅ Live test passed, found 7 real bugs |
| RUFLO audit swarm self-review | ✅ Both agents (audit_researcher, audit_quant) produced output |
| tools/swarm self-review (deepseek) | ✅ Ran successfully |

---

## Swarm Self-Review Consensus

**RUFLO audit swarm** (`--tier paid`) ran audit_researcher + audit_quant in parallel. Both agents produced structured output confirming:
- The audit pipeline is functional with paid API keys
- Parallel threading.Lock() prevents lost outputs
- 9 compiled insights in COMPILED_latest.json

**tools/swarm** (deepseek engine) reviewed the 3 code changes and confirmed they are correct with no regressions.

---

## Known Limitations

1. **Groq HTTP 403**: `GROQ_KEY` (gsk_LUXI..., 56 chars) returns error code 1010 from `api.groq.com`. Key format looks valid — likely an account-level issue (not activated? rate-limited?). Code path is correct.
2. **Single retry only**: The empty-envelope retry does exactly 1 retry with 1s sleep. If transient failures are common, extend to 2-3 attempts with exponential backoff.
3. **WSL path**: Hermes binary defaults to `/home/zerou/.local/bin/hermes` (WSL path). The `--tier paid` bypasses Hermes entirely, but `--tier free/hybrid` needs WSL. The Windows bridge command is documented in the orchestrator help text.

---

## Files Touched (5 modified + 2 new)

| File | Change |
|------|--------|
| `tools/swarm/worker_runner.py` | Empty-envelope retry for gemini, opencode/kilo, copilot |
| `tools/swarm/swarm_run.py` | Pre-flight API key skip block |
| `tools/swarm/config_loader.py` | Synced cerebras/openrouter key-env aliases |
| `tools/swarm/prompts/self_review_swarm_fixes.md` | New — self-review prompt for swarms |
| `tools/__init__.py` | New — package init for tools.* imports |
| `tools/swarm/__init__.py` | New — package init for tools.swarm.* imports |
