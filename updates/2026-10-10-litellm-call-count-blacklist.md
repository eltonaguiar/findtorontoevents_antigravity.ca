# LiteLLM proxy: call-count provider blacklist (2026-10-10)

## What was broken

Users hit intermittent failures through the local LiteLLM proxy (`:4000`):

```
Provider: openai (proxy)
Model: free-mode
OpenAI completion error: Connection error
```

LiteLLM's built-in cooldown is **time-based** (`allowed_fails: 1` + `cooldown_time: 65`). A provider
that is genuinely down — dead key, exhausted quota, upstream outage — is therefore retried again
~65 seconds later, on every subsequent request, forever. With `routing_strategy: simple-shuffle` the
router keeps re-picking the dead provider, so a persistent fraction of requests failed even though
healthy providers were available.

Worse, the pre-existing `tools/litellm_smart_cooldown.py` **only recorded** failures to a state file
for the operator. Its own docstring said so: *"LiteLLM's router still owns the live cooldown via
cooldown_time."* Nothing enforced the classification.

## What changed

**New: `tools/litellm_call_blacklist.py`** — a call-count (not time-based) provider blacklist.

- When a deployment fails in a way that means *the provider is unhealthy* (`dead_key`, `rate_limit`,
  `server_error`, `daily_quota_cf`, `monthly_quota_hf`, `quota` — reusing
  `litellm_smart_cooldown._classify`), it is removed from the candidate pool for the next **30 client
  API calls**.
- Request-specific faults (400s, context-window overflow, content policy) deliberately do **not**
  blacklist a provider.
- Counts *client* requests, not retry attempts: `async_pre_call_hook` advances a global counter and
  returns `None`, so request `data` is never modified.
- **Fail-open**: if filtering would empty the candidate pool, the unfiltered pool is returned — the
  blacklist can never convert a working request into a failure.
- **Never raises**: every hook swallows its own exceptions, so a bug degrades to "no blacklist",
  never to "proxy broken".
- State is persisted to `/tmp/litellm_blacklist_state.json` with atomic writes + a cross-process
  lock (the proxy and CLI both touch this file).

**`litellm_config.yaml`** (+8 lines) — registers the callback in `litellm_settings.callbacks`.

**CLI**

```bash
python3 tools/litellm_call_blacklist.py status     # who is parked + remaining calls
python3 tools/litellm_call_blacklist.py clear      # un-park everyone
python3 tools/litellm_call_blacklist.py selftest   # offline logic test
python3 tools/litellm_call_blacklist.py stress --calls 40 --down 40
```

Knobs: `LITELLM_BLACKLIST_CALLS` (default 30), `LITELLM_BLACKLIST_ENABLE=0`,
`LITELLM_BLACKLIST_STATE`.

## The non-obvious bug found while building this

**You must patch TWO Router methods.** On litellm 1.86.0 the *primary* deployment-selection path calls
`Router.async_get_healthy_deployments` (**no leading underscore**), while retries and the scheduler
call `Router._async_get_healthy_deployments`. Patching only the underscore variant produces the worst
possible failure mode: no errors, correct-looking diagnostics, filters computing correctly — and
blacklisted providers still being routed. Only the primary path was being exercised for normal
traffic, so 40 blacklisted deployments still served requests.

Both are now patched:

```
router patch: installed=True classes=['litellm.router.Router[async_get_healthy_deployments, _async_get_healthy_deployments]']
```

## Verification

**1. Offline logic — `selftest` (6/6 PASS)**

Not-blacklisted initially; a 429 blacklists it; a sibling deployment is unaffected; a 400/context
error does *not* blacklist; the entry expires after exactly 30 counted calls (still parked at 29,
released at 30); the composite-key path (no `model_id` available) also works.

**2. Router-hook regression — `patchtest` (no proxy needed)**

Reproduces the exact bug. Blacklist one of 3 deployments → the **primary list hook** pool shrinks
3 → 2 with that deployment excluded; the **retry tuple hook** excludes it too; blacklisting all
three returns the full pool (fail-open). This test exists so the two-method bug cannot silently
regress again.

**3. Live hook — the running proxy counts calls**

3 live `POST /v1/chat/completions` → `call_seq` advanced `0 → 3` exactly (proves
`async_pre_call_hook` fires once per client request), all HTTP 200 (no regression).

**4. Live enforcement** — 40 of 42 `free-mode` deployments parked; the proxy's own debug records
`free-mode healthy=42 kept=2 filtered_out=40`, i.e. the filter genuinely runs on the hot path.

**5. Acceptance test — `stress --calls 40 --down 40` → PASS**

40 of 42 providers simulated down, then 40 consecutive calls:

```
RESULT: successes=40/40 max_consecutive_failures=0 (limit 3) fail_open_overrides=0 -> PASS
```

`fail_open_overrides=0` is the important part: the parked providers were genuinely avoided, the run
never had to stand down, and not one call failed.

## Fail-open semantics (important caveat)

If *every* remaining candidate for a group is parked, the blacklist stands down and returns the
unfiltered pool. This is deliberate — a request must still be *attempted* rather than guaranteed to
fail — but it means "a parked provider is never served" is **not** an unconditional guarantee.

A strict 8-request test first reported "violations" for exactly this reason: the two non-parked
`groq` deployments were already excluded by LiteLLM's own cooldown, so the 40 parked ids *were* the
entire healthy pool → `kept=0` → fail-open → parked providers were retried. All 8 requests still
succeeded. The initial "FAILED" verdict was a flawed assertion, not a broken filter.

Fail-open is now observable rather than silent: it increments a counter in the state file, prints a
`FAIL-OPEN` warning to stderr, is shown by `status` and in the `stress` summary, and is reset by
`clear`.

## Files

| File | Change |
|---|---|
| `tools/litellm_call_blacklist.py` | new — blacklist module + CLI (`status`/`clear`/`selftest`/`patchtest`/`stress`) |
| `litellm_config.yaml` | +8 lines — callback registration |
| `.claude/skills/litellm-proxy/SKILL.md` | documents the blacklist + the two-method gotcha |

## Operational note

The blacklist is enforced in-process, so it is **per-proxy-instance** in memory but shared on disk.
Restarting the proxy reloads state from the JSON file; `clear` empties it immediately.
