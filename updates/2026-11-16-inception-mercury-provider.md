# 2026-11-16 — Inception Labs Mercury added to the local LiteLLM proxy (`:4000`)

**Request:** add Inception Labs "mercury" as a provider under `http://localhost:4000/v1`, reusing the credentials
already present in the Kilo Code setup.

## Where the credential actually was

`~/dbpasses.txt` line 316/317 — and the format is the reason two earlier greps missed it:

```
INCEPTION_AI_KEY
sk_…            ← value on the NEXT line, no '='
```

`tools/start_litellm_proxy.sh` already handles that shape: it calls
`parse_key "INCEPTION_AI_KEY" INCEPTION_API_KEY`, so the launcher exports the secret as **`INCEPTION_API_KEY`**
(label→value pattern). Nothing needed to be added to the launcher.

The Kilo Code copy lives in VS Code's encrypted SecretStorage (`state.vscdb`), which is why no plaintext key turned up
there — `dbpasses.txt` is the usable source.

## What was added

`litellm_config.yaml`, in an idempotent marker block:

```yaml
# BEGIN inception-mercury (managed by session work — safe to edit)
  - {model_name: ULTRA_PAID_MERCURY, litellm_params: {model: 'openai/mercury-2',  api_base: https://api.inceptionlabs.ai/v1, api_key: os.environ/INCEPTION_API_KEY}}
  - {model_name: mercury-direct,     litellm_params: {model: 'openai/mercury-2',  api_base: https://api.inceptionlabs.ai/v1, api_key: os.environ/INCEPTION_API_KEY}}
# END inception-mercury
```

`ULTRA_PAID_MERCURY` was also appended to `AGY_LLM_GATEWAY_MODELS` in `~/.config/agy-litellm/env`, so the CLI, the IDE
extension and the App picker all list it (36 models total).

Inception exposes `mercury-2`, `mercury-2.5`, `mercury-3`, `mercury-decide`. `mercury-2` is the tested default; naming
in the config comment (`legacy mercury` is cutoff-gated) is why the 2.x line is used.

## Verification

- Credential validity checked **at the provider**, not locally: `GET https://api.inceptionlabs.ai/v1/models` returned the
  four model ids and a `POST /chat/completions` with `mercury-2` returned a completion for model `mercury-2`.
- Config: `litellm_config.yaml` still parses; 133 `model_list` entries; the two mercury aliases are present.
- `tools/start_litellm_proxy.sh` passes `bash -n`, and its `parse_key "INCEPTION_AI_KEY" …` line is the export path.
- Proxy **not restarted** (pid 3518861, uptime 105,789 s) — consistent with the standing instruction that other agents
  are using `:4000`. The alias appears in `/v1/models` on the next start:

  ```bash
  bash tools/start_litellm_proxy.sh        # or: systemctl --user restart litellm-4000.service
  curl -s localhost:4000/v1/models -H 'Authorization: Bearer sk-1234' | grep -i mercury
  ```

## Credential hygiene note

While locating the key, one masked dump printed the raw value: the masking helper assumed `KEY=value`, so a bare value
line fell through as context. The value never reached any repository, patch file or commit — it exists only in
`~/dbpasses.txt` (mode unchanged) and in the transient `/tmp/inception_key` (0600, used for the API test). If this
session transcript is shared outside the machine, rotate the key at Inception's console.
## Follow-up: the rest of the Mercury line

Inception's `/models` lists four ids, but they are not all chat models. Each was probed with a real
`POST /v1/chat/completions`:

| Alias | Upstream model | Chat completion | Notes |
|---|---|---|---|
| `ULTRA_PAID_MERCURY` | `mercury-2` | OK (18-22 tokens) | primary alias |
| `ULTRA_PAID_MERCURY_2_5` | `mercury-2.5` | OK | added |
| `ULTRA_PAID_MERCURY_3` | `mercury-3` | OK | added |
| `mercury-direct` | `mercury-2` | OK | direct-target alias |
| ~~`ULTRA_PAID_MERCURY_DECIDE`~~ | `mercury-decide` | **HTTP 400** — `Model must be one of the following …` | listed by `/models` but not accepted for chat; **not** registered |

`mercury-decide` was briefly added, then removed from both the config and the agy list — shipping an alias that always
400s is worse than not having it. If Inception later accepts it (or documents it as a routing endpoint with a different
payload), re-add one line to the marker block.

The remaining three aliases are in `AGY_LLM_GATEWAY_MODELS` (38 entries), so the CLI, IDE extension and App picker list
them. Config parses cleanly at 135 `model_list` entries, the marker block is idempotent, and the block contains zero
literal keys.

Still **not restarted** (proxy up ~1.2 days): the aliases are served from the next `tools/start_litellm_proxy.sh` start,
per the standing instruction that other agents are using `:4000`.

Note on Mercury responses: the live probes consumed tokens but returned an empty `message.content` string, so these
models appear to put their visible text elsewhere (reasoning/thinking field) — worth checking the first time you call one
through the proxy, since a client that only reads `content` may print nothing.

## Why Mercury looked like it "returns empty content"

Not a proxy bug. Mercury is a reasoning model: it spends completion tokens thinking before it emits text. At
`max_tokens=16` the whole budget went to reasoning (`finish_reason: length`, `completion_tokens_details.reasoning_tokens`
= 16/16) and `message.content` came back `null`. At 64 tokens it answered `HELLO THERE` with 50 reasoning tokens; at 2048,
69 reasoning tokens and the same answer. Reasoning is returned as `reasoning_details` (`type: reasoning.encrypted`,
`mrt1_v1_…`) plus a top-level `reasoning_summary`.

Two consequences baked into the config:

- every mercury deployment now carries `max_tokens: 2048` in `litellm_params`, so a client that omits `max_tokens` does not
  get a reasoning-only, empty-content completion;
- a client that streams will see `delta.reasoning_details` chunks and little or no `delta.content` until reasoning ends —
  that is upstream behaviour, not something to patch over.

### `mercury-coder` / `mercury-coder-small` are account-gated

Registered briefly, then removed after probing:

```
403 model_access_denied: Model `mercury-coder` is only available to accounts created before February 24, 2026.
Please use Mercury 2 or Mercury Edit models instead.
```

Final mercury aliases: `ULTRA_PAID_MERCURY`, `ULTRA_PAID_MERCURY_2_5`, `ULTRA_PAID_MERCURY_3`, `mercury-direct`
(agy list back to 37 models, 3 ollama aliases intact).
