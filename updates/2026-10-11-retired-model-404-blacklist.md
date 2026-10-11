# free-mode served a retired model on every request (2026-10-11)

## Symptom

`free-mode` (via the local LiteLLM proxy on `:4000`) intermittently failed with:

```
litellm.NotFoundError: Vertex_ai_betaException - b'{
    "error": {"code": 404,
      "message": "This model models/gemini-2.5-pro is no longer available to new users.
                  Please update your code to use models/gemini-3.1-pro-preview ..."}
}'
```

## Root cause

Two independent problems compounded.

**1. A dead model was still in the config.** Nine entries across three groups pointed at
models Google no longer serves to this account:

| group | dead models |
|---|---|
| `free-mode` | `gemini-2.5-pro`, `gemini-2.0-flash`, `gemini-2.0-flash-lite` |
| `free-mode-large` | same three |
| `hybrid-model-large` | same three |

**2. The blacklist could not see the failure.** `tools/litellm_smart_cooldown._classify()` handled
401 / 429 / 5xx / quota, but a 404 fell through to `"other"` — and `"other"` is deliberately **not**
in `BLACKLIST_CATEGORIES`. So the retired model was never parked and `simple-shuffle` re-picked it on
**every** request. The blacklist was working perfectly for 429s; it was simply blind to this class of
error.

A trap worth recording: **the provider's model-list endpoint still lists `gemini-2.5-pro`.** Querying
`GET /v1beta/models` reports it as available, yet the same key is refused at inference time. So a
config-time model-list check does *not* catch this — only the runtime error does.

## Fix

**`tools/litellm_smart_cooldown.py`** — new `dead_model` category for 404 / "not found" /
"no longer available" / "no longer supported" / "decommissioned" / "unknown model" / "does not
exist", checked *before* the generic `bad_request` branch so it cannot be swallowed.

**`tools/litellm_call_blacklist.py`**
- `dead_model` added to `BLACKLIST_CATEGORIES`.
- New per-category park window: `dead_model` parks for **300 calls** (a transient rate-limit still
  parks for 30). A retired model does not come back on its own, so parking it for the same duration
  as a 429 would just let it resurface ~10x more often. Override with
  `LITELLM_BLACKLIST_CALLS_DEAD`.
- `_selftest` gained check 7 (now 7/7) asserting a retired-model 404 blacklists *and* gets the
  longer window.

**`litellm_config.yaml`** — removed the nine dead entries, with a comment recording why (so nobody
re-adds them from the provider's model list).

## Verification

| Check | Result |
|---|---|
| `_classify(404 retired)` | `'dead_model'`, blacklistable=**True**, window **300** |
| `selftest` | **7/7 PASS** |
| `patchtest` | PASS (both Router hooks + fail-open) |
| config YAML parses | OK, 127 deployments |
| dead deployment entries remaining | **0** (the 5 grep hits are the explanatory comments) |
| `free-mode` deployments after cleanup | 39, **0** dead models |

**Live end-to-end proof.** A temporary `deadmodel-test` group containing only
`gemini/gemini-2.5-pro` was added, the proxy restarted, and one request sent:

```
http=404
{"error":{"message":"litellm.NotFoundError: GeminiException - {...code: 404,
  'This model models/gemini-2.5-pro is no longer available to new users...'"}}
```

Blacklist state immediately after:

```
category=dead_model remaining_calls=300 hits=1   (by deployment id)
category=dead_model remaining_calls=300 hits=1   (by composite key)
```

The temporary group was then removed and the proxy restarted (verified: 0 occurrences, readiness 200).
Before the fix this same error classified as `other`, was not parked, and recurred on every request.

## Files

| File | Change |
|---|---|
| `tools/litellm_smart_cooldown.py` | new `dead_model` classification |
| `tools/litellm_call_blacklist.py` | category added, 300-call window, selftest check 7 |
| `litellm_config.yaml` | 9 dead deployments removed |
