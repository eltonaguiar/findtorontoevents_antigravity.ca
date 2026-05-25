---
description: Tail the LiteLLM proxy log, highlighting rotation / rate-limit / cooldown events.
argument-hint: "[lines] — default 50"
---

Show recent LiteLLM proxy activity. Default lines = 50 (override with $ARGUMENTS).

1. `tail -n ${ARGUMENTS:-50} /tmp/litellm_proxy.log`
2. Then a filtered re-pass to surface the interesting events:
   `tail -n 500 /tmp/litellm_proxy.log | grep -iE '429|RateLimit|cooldown|AuthenticationError|TimeoutError|InternalServerError|fallback|api\\.[a-z]+\\.(com|net|cloud|ai|xyz)'`
3. Summarize:
   - which upstreams are currently in cooldown
   - any recurring error pattern (one provider repeatedly 401ing → key dead)
   - request volume in the window
