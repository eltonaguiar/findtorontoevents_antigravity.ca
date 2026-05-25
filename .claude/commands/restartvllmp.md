---
description: Restart the LiteLLM rotating proxy on :4000 — kills existing process, reloads keys + config, verifies health.
---

Restart the LiteLLM rotating-fallback proxy. Use after editing `litellm_config.yaml`, rotating a key in `~/dbpasses.txt`, or when an upstream goes stale.

1. Kill any existing instance: `pkill -f 'litellm.*litellm_config' || true`
2. Wait 3 seconds for clean shutdown.
3. Relaunch: `bash tools/start_litellm_proxy.sh --background`
4. Wait 6 seconds, then `curl -s -m 5 http://localhost:4000/health/readiness`.
5. Sanity-ping `hybrid-model` with `"1+1? one word"` (max_tokens=20). Surface which upstream served it from the `x-litellm-model-api-base` header.
6. Report: old PID killed, new PID, key-load count (must be 15/15 — anything lower means a label in `~/dbpasses.txt` got mangled, investigate), health, served-by upstream.

Reference: `.claude/skills/litellm-proxy/SKILL.md`
