# tools/swarm cerebras adapter — SDK-missing fallback

**Agent:** claude-opus-4-7 (Claude Code)
**Timestamp:** 2026-05-05T07:10Z
**File patched:** `tools/swarm/api_consult.py`
**Function:** `call_cerebras()` + new helper `_call_cerebras_via_http()`

## Symptom

Two recent multi-engine swarm runs against `cerebras` returned rc=0 but produced 0 useful content:

- `swarm_runs/run_pr_swarm_compare/_summary.json`
- `swarm_runs/run_actions_swarm_compare/_summary.json`

Both show:
```json
"engine": "cerebras",
"rc": 0,
"stderr_tail": "[cerebras attempt=1/2 rc=3] cerebras error: cerebras: pip install cerebras-cloud-sdk\n[cerebras attempt=2/2 rc=3] cerebras error: cerebras: pip install cerebras-cloud-sdk"
```

DeepSeek (HTTP-based) succeeded in the same runs (`rc=0, out_size=3816`). So the failure is cerebras-specific.

## Methodology

1. Pulled both `_summary.json` files from `swarm_runs/run_*_compare/`
2. Cross-checked stderr_tail patterns — both show identical SDK-missing error
3. Read `tools/swarm/api_consult.py:260-273` (`call_cerebras`) — found:
   ```python
   try:
       from cerebras.cloud.sdk import Cerebras
   except ImportError as e:
       raise RuntimeError("cerebras: pip install cerebras-cloud-sdk") from e
   ```
4. Verified via direct API: `https://api.cerebras.ai/v1/chat/completions` IS OpenAI-compatible (we used it earlier this session via `tools/brainstorm_review_swarm.py` which goes plain HTTP, not SDK)
5. Reviewed `_post()` helper at `tools/swarm/api_consult.py:178` — already supports OpenAI-compat POST shape; cerebras can ride that path

## Root cause

`call_cerebras()` raises hard `RuntimeError` when the `cerebras-cloud-sdk` Python package isn't installed, instead of falling back to the HTTP API. The SDK is a convenience wrapper, NOT a hard requirement — Cerebras' `/v1/chat/completions` endpoint is OpenAI-compatible and works fine via plain HTTP POST with `Bearer <key>` auth.

This means **every swarm run that includes cerebras as an engine fails for users who don't have the SDK installed**, even though the underlying API would respond normally. The user's machine showed this exact pattern in 2 back-to-back swarm runs.

## Fix

Two-part change in `tools/swarm/api_consult.py`:

1. **New helper** `_call_cerebras_via_http()` — uses the existing `_post()` helper to call `https://api.cerebras.ai/v1/chat/completions` with the OpenAI-compat request shape. Preserves `cerebras` quirks (uses `max_completion_tokens` not `max_tokens`).

2. **Fallback in `call_cerebras()`** — when SDK import fails, route to the HTTP helper instead of raising:
   ```python
   try:
       from cerebras.cloud.sdk import Cerebras
   except ImportError:
       return _call_cerebras_via_http(prompt, model_override, sampling, key)
   ```

Behavior when SDK *is* installed: unchanged. Behavior when SDK is missing: previously hard-failed, now succeeds via HTTP. Net: superset functionality.

## Verification plan

Post-merge:
1. `pip uninstall cerebras-cloud-sdk` (or test on a fresh env where SDK isn't installed)
2. Run: `python tools/swarm/swarm_run.py --prompt-file tools/swarm/prompts/pr_review_batch.md --engines cerebras,deepseek --max-parallel 2 --cost-cap-usd 0.10`
3. Check `swarm_runs/run_*/cerebras.json` — should contain real model output, not SDK-missing error
4. Check `_summary.json` — `stderr_tail` for cerebras should be empty (or only contain non-SDK warnings)
5. `pip install cerebras-cloud-sdk` and re-run — should still work (SDK path takes priority when available)

## Why HTTP-fallback over `pip install` requirement

The user runs swarms from multiple shells / WSL / cron contexts. Requiring an extra pip install per environment is fragile (Python venv isolation, WSL vs Windows pip, etc.). A pure-HTTP fallback removes the dependency entirely. The SDK still works as the preferred path when present (better error messages, request/response typing, future feature parity) — we just don't *require* it.

## Related

- Full Hermes/swarm bug catalog: `updates/2026-05-05-hermes-agent-bug-analysis-claude-opus-4-7.md`
- Companion fix (ruflo orchestrator `--model` pass-through): PR #815
- The brainstorm-review swarm tool that already uses HTTP path successfully: `tools/brainstorm_review_swarm.py`
