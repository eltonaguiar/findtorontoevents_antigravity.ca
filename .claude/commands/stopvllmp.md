---
description: Stop the LiteLLM rotating proxy on :4000.
---

Stop the LiteLLM rotating-fallback proxy.

1. `pgrep -af 'litellm.*litellm_config'` — capture PID(s) for reporting.
2. `pkill -f 'litellm.*litellm_config' || true`
3. Wait 2s, then re-`pgrep` to confirm gone.
4. `curl -s -m 3 http://localhost:4000/health/readiness` — should now fail (connection refused). If it still responds, something else is bound to :4000; flag it.
5. Report: killed PID(s), confirmation port is free, log location (`/tmp/litellm_proxy.log`) preserved for inspection.
