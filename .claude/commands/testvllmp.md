---
description: Fire N test requests through hybrid-model and report which upstreams served them (proves rotation is working).
argument-hint: "[count] — default 6"
---

Test the LiteLLM proxy's rotation. Default count = 6 (override with $ARGUMENTS).

For each request:
- POST `http://localhost:4000/v1/chat/completions` with `model=hybrid-model`, prompt `"1+1? one word"`, max_tokens=20, `Authorization: Bearer anything`
- Capture response headers into `/tmp/h$i.txt` and body into `/tmp/b$i.txt`
- Extract `x-litellm-model-api-base` (the upstream that served) and `x-litellm-attempted-retries`
- Parse `choices[0].message.content` for the reply

Then summarize:
- Success rate (N/N)
- Distinct upstreams hit (rotation diversity)
- Any retries > 0 (means rotation kicked in for that request)
- Any failures and their error class

If success rate < 100%, tail the proxy log: `tail -30 /tmp/litellm_proxy.log | grep -iE '429|RateLimit|cooldown|Error|api\\.[a-z]+\\.'`

Tell the user which providers are healthy + which are cooling down.
