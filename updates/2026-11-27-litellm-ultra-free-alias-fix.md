# LiteLLM proxy: `ULTRA_FREE_CLOUD_FAST` model-not-found fix (2026-11-27)

## What was broken

1. **Kilo/opencode could not use the local proxy.** It requested
   `model=ULTRA_FREE_CLOUD_FAST` (provider `litellm-local`, base `http://localhost:4000`),
   and the router had no such model group:

   ```
   ProviderModelNotFoundError: Model not found: litellm-local/ULTRA_FREE_CLOUD_FAST
   ```
   and server-side:
   ```
   ProxyModelNotFoundError: 400: Invalid model name passed in model=ULTRA_FREE_CLOUD_FAST
   ```

   Only `free-mode*`, `hybrid-model*`, `paid-mode*` and `ULTRA_PAID_*` existed, so every
   request from Kilo (including session compaction) died immediately.

2. **The running proxy was wedged.** A `litellm --config litellm_config.yaml --port 4000`
   process held the port in LISTEN but `/health` returned no response (curl code `000`),
   so clients timed out rather than getting an error.

## What changed

`litellm_config.yaml` only:

- Added alias groups that Kilo's config asks for, each backed by verified free upstreams
  (Groq llama-3.1-8b primary+alt, NVIDIA NIM llama-3.1-8b, Gemini 2.5-flash-lite):
  `ULTRA_FREE_CLOUD_FAST`, `ULTRA_FREE_CLOUD`, `ULTRA_FREE_NVIDIA`,
  `ULTRA_FREE_TOOLS`, `ULTRA_FREE_CLOUD_TOOLS`.
- Added `router_settings.fallbacks` entries so each new alias escalates to
  `free-mode-fast` / `free-mode` / `free-mode-large` instead of surfacing the raw
  upstream error.

Two self-inflicted YAML breaks were fixed during the same session (both caused the
proxy to abort at startup):

- `ULTRA_FREE_LOCAL_FAST` used `openai/${OLLAMA_MODEL:-qwen2.5:7b}` — a colon inside a
  flow mapping. Entry removed.
- `- ULTRA_FREE_CLOUD_TOOLS:["..."]` was missing the space after the colon, making the
  value a plain string (`ValueError: Item ... is not a dictionary`). Fixed.

Proxy restarted with `tools/start_litellm_proxy.sh --background` (50/51 keys loaded).

## How it was verified

- `python3 -c "import yaml; yaml.safe_load(open('litellm_config.yaml'))"` → parses,
  144 model entries, 13 fallback rules, 0 malformed rules.
- `GET http://127.0.0.1:4000/health` → **200**.
- Live completion on the previously-missing model:
  ```
  POST /v1/chat/completions {"model":"ULTRA_FREE_CLOUD_FAST", ...}
  → {"model":"ULTRA_FREE_CLOUD_FAST", "choices":[{"message":{"content":"OK"}}], ...}
  ```
- Startup log clean: no `ValueError`, `ParserError`, or `Application startup failed`.

Rollback copies kept next to the config:
`litellm_config.yaml.bak-ultrafree-*` and `litellm_config.yaml.bak-fixkeys-20261127-114448`.

## Follow-up: dead-model cleanup applied (2026-11-27 ~12:05Z)

- **Proxy**: commented 16 dead deployments (`ULTRA_PAID_OLLAMA_LOKER_V2_1_CLD_CDR_480B` 410 Gone,
  `claude-haiku-direct` invalid_request, `novita-deepseek-v4-pro-direct` no balance,
  `hybrid-model-large` 12/13 deployments failing). Fallback rules pruned to surviving groups only
  (0 dangling). Restarted under `setsid` so it survives shell exit; `/health/liveliness` 200,
  chat 200 on `ULTRA_FREE_CLOUD_FAST`, `free-mode`, `hybrid-model`, `paid-mode`.
- **Kilo** (`~/.config/kilo/kilo.jsonc`): disabled 12 paid/no-refresh providers (topnotch, openrouter,
  aihubmix, apinex, kimi, kimi-coding-plan, inception, cohere, opencode-zen, publicai,
  vllm-diffusiongemma, topnotch-localonly); corrected the vLLM model ids to the aliases the servers
  actually serve. JSONC validated after edit (one bad insertion was rolled back from backup).
- **Audit report**: `/home/eaguiar2015/DEADMODELS_2026-11-27.MD`; results also pushed to COMS
  (`mentions/all`) with Hermes asked to run the hourly operator reminder.
