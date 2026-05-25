---
description: Show LiteLLM proxy status — process, health, key-load count, registered model groups, recent log tail.
---

Report LiteLLM proxy status. Run these in parallel and summarize:

1. `pgrep -af 'litellm.*litellm_config'` — PID(s) and command line
2. `curl -s -m 3 http://localhost:4000/health/readiness` — health JSON
3. `curl -s -m 3 http://localhost:4000/v1/models | python3 -c "import sys,json;d=json.load(sys.stdin);print('\\n'.join(sorted({m['id'] for m in d['data']})))"` — registered model group names
4. `tail -15 /tmp/litellm_proxy.log` — recent log lines (look for cooldown / 429 / RateLimit / error markers)
5. `grep -c 'keys loaded' /tmp/litellm_proxy.log; grep 'keys loaded' /tmp/litellm_proxy.log | tail -1` — last reported key-load count (target: 15/15)

Format the summary as: RUNNING/DOWN · PID · uptime · health · key-count · model-group list · any errors from recent log.

If down, tell the user to run `/startvllmp`.
