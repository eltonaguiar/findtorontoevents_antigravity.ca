---
description: Start the rotating LiteLLM proxy on :4000 (background). Idempotent — refuses if already running.
---

Start the LiteLLM rotating-fallback proxy.

1. Check if already running: `pgrep -af 'litellm.*litellm_config'`
   - If a PID is found, STOP. Tell the user it's already up, show the PID + `curl -s http://localhost:4000/health/readiness`, and suggest `/restartvllmp` if they want to recycle.
2. Otherwise launch: `bash tools/start_litellm_proxy.sh --background`
3. Wait 6 seconds, then verify with `curl -s -m 5 http://localhost:4000/health/readiness`.
4. Report: PID, key-load count, health status, and the Roo/Kilo settings snippet (`base_url=http://localhost:4000/v1`, `model=hybrid-model`, `api_key=anything`).
5. If the health endpoint doesn't respond within 10s, tail `/tmp/litellm_proxy.log` and surface the last error.

Reference: `.claude/skills/litellm-proxy/SKILL.md`
