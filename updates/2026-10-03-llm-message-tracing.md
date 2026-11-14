# LLM Message Tracing — find which provider served a given message

**Date:** 2026-10-03
**Status:** Implemented + verified. Not committed.
**Goal:** "I send a message containing a marker (e.g. `xyzdragon`), and you tell me which provider/model answered it."

## Problem

`free-mode-large` is a LiteLLM **model group** (a label). On a successful call the proxy
recorded nothing about the real upstream that served it, so a message marker could not be
traced after the fact. The only existing state file (`/tmp/litellm_cooldown_state.json`)
captures **failures only**.

## What was built

### 1. `tools/litellm_message_log.py` (new)
A LiteLLM `CustomLogger` registered in `litellm_config.yaml`:

```yaml
litellm_settings:
  callbacks:
    - tools.litellm_smart_cooldown.smart_cooldown
    - tools.litellm_message_log.message_log
```

Writes one JSON object per request attempt to `/tmp/litellm_messages.jsonl`
(success **and** failure, including each fallback hop), capturing:

`ts, status, call_id (== x-litellm-call-id), trace_id, requested_group, real_model, model_id,
provider, api_base, prompt_tokens, completion_tokens, total_tokens, response_cost,
duration_ms, prompt, last_user, prompt_chars, response`

Fields were verified against litellm 1.86.0's `StandardLoggingPayload` TypedDict
(`litellm/types/utils.py`), not guessed.

Privacy switch: `LITELLM_MESSAGE_LOG_CONTENT=0` stores metadata only (no message bodies,
keeps `prompt_sha256_8` for correlation). Other knobs: `LITELLM_MESSAGE_LOG`,
`LITELLM_MESSAGE_LOG_MAX_CHARS`, `LITELLM_MESSAGE_LOG_MAX_BYTES` (50 MB rotation).

### 2. `tools/llm_message_sweep.py` (new)
One command to trace a marker across every local surface:

```bash
python3 tools/llm_message_sweep.py --marker xyzdragon
```

| Surface | Source | Can match text? |
|---|---|---|
| `litellm` | `/tmp/litellm_messages.jsonl` | yes (prompt + response) |
| `opencode` | `~/.local/share/opencode/opencode.db` (`part.data` → `message` → model) | yes |
| `openwebui` | `docker cp open-webui:/app/backend/data/webui.db` → `chat.chat` JSON | yes |
| `vllm` | `/tmp/vllm_serve.log` | yes (if request logging enabled) |
| `ollama` | `journalctl -u ollama` | **no** — advisory/time-correlation only |

Exit code 0 if matched, 1 otherwise.

## Bug found and fixed during testing

First version head-truncated the prompt to 2000 chars. **opencode sends ~85 KB** of system
prompt + history, so the user's actual message (at the very end) was silently cut off and
never searchable — which is exactly why the `awagon123` marker could not be found.

Fix: `prompt` is now **tail**-truncated (newest turns survive) and a dedicated `last_user`
field carries the final user message untruncated.

## Verification (all run, output observed)

| Test | Result |
|---|---|
| 45-char prompt marker `xyzdragon` | matched → `gemini/gemma-4-31b-it` |
| 21,643-char system prompt + `zzmarker999` at end | matched → `gemini/gemini-3-flash-preview` |
| `awagon123` (sent from opencode) | matched on surface `opencode`, role=user |
| Negative control (marker nowhere) | not found, exit code 1 |
| `LITELLM_MESSAGE_LOG_CONTENT=0` | no `prompt` field stored, `prompt_sha256_8` present |

## Key environment finding

opencode's provider config (`~/.config/opencode/opencode.jsonc`) maps:

```jsonc
"eltonsvllm-free": { "options": { "baseURL": "http://localhost:4000/v1" }, ... }
```

So **opencode traffic does go through the LiteLLM proxy** — the earlier "missing" marker was
a truncation bug, not a routing problem. (Open WebUI on :3000 is separate and points at
Ollama, not the proxy.)

## Limitations

- No backfill: the LiteLLM log only covers traffic since 2026-10-03 22:33.
- Ollama cannot be content-matched (it does not log prompt text). Use the opencode/Open WebUI
  DBs for those chats, which store the message + model.
- vLLM content matching requires starting it with request logging (`--enable-request-logging`);
  by default only the model-load lines are present.
- Messages sent to a remote/cloud endpoint (not through a local surface) are untraceable.

## Files touched

- `tools/litellm_message_log.py` (new)
- `tools/llm_message_sweep.py` (new)
- `litellm_config.yaml` (callbacks list: added the message logger)

**Not committed / not pushed** — left in the working tree for review.
