# 2026-11-27 — Provider model refresh, dead-provider removal, free-first proxy

Follow-up to `updates/2026-11-27-litellm-ultra-free-alias-fix.md`. This pass re-read every
provider's **live model catalogue** (not just chat probes) because several "dead model id"
failures turned out to be **version retirements**, not dead keys.

## 1. Model ids that were retired upstream (replaced)

| Provider | Retired id | Evidence | Replacement (verified 200) |
|---|---|---|---|
| Groq | `llama-3.1-8b-instant` | chat → `404 model does not exist`; absent from the 11-model `/models` listing | `openai/gpt-oss-20b` (12 proxy deployments swapped) |
| Groq | `openai/gpt-oss-120b` (earlier 403) | now answers **200** on both keys | kept; plus `qwen/qwen3.8-27b`, `allam-2-7b` |
| Cloudflare Workers AI | `@cf/qwen/qwen3-30b-a3b-fp8` | 410 Gone; absent from the 337-model catalogue | `@cf/qwen/qwen3.8-27b`, `@cf/deepseek-ai/deepseek-v4.1-flash-1017`, `@cf/zai-org/glm-5.3` |
| HuggingFace router | `deepseek-ai/DeepSeek-R1` | `400 not supported by any provider you have enabled` | `deepseek-ai/DeepSeek-R1-0528` |
| OpenRouter | `inclusionai/ring-2.6-1t` | `404 no longer available as a free model` | `nvidia/nemotron-3.5-lightning:free`, `google/gemma-4-31b-it:free` |

Groq's live catalogue is now only: `gpt-oss-120b`, `gpt-oss-20b`, `qwen/qwen3.8-27b`,
`allam-2-7b`, `gpt-oss-safeguard-20b`, `llama-prompt-guard-2-*`, `whisper-*`, `orpheus-*`.
Every `llama-3.x`/`qwen3-32b`/`kimi-k2` id we previously used is gone.

## 2. Providers removed entirely (both proxy and Kilo)

| Provider | Why |
|---|---|
| `publicai` | 403 Forbidden |
| `opencode-zen` | 403 Forbidden |
| `cohere` | trial key = 1000 calls/**month**, no daily refresh |
| `llm7` | **no free tier exists**: 84 models, all `tier=pro|turbo`, `usage_based_only=true`; 3 of 4 chat probes `402 balance too low` (only `codestral-latest` answers) |
| `topnotch`, `aihubmix`, `apinex`, `kimi`, `kimi-coding-plan`, `inception` | paid / no-refresh quotas, already disabled in the previous pass — now deleted outright |
| proxy `ULTRA_PAID_OLLAMA_LOKER_*`, `ULTRA_PAID_MERCURY*` | paid token plans, no daily refresh |

Kilo: **24 providers / 27 disabled**. Proxy: **19 groups**. No dangling fallback targets.

## 3. SubQ — own endpoint

`api.subq.ai/v1` + `subq-savant-1.4`:
- paid token (label `SUBQ Token ($5  free credit+$20 more added )`) → **200**
- `SUBQ FREE` key → `403 model_not_allowed`

Wired as proxy group `subq-savant-direct` and as one `paid-mode` deployment. The `subq-snap-*`
ids are not chat models and were dropped from the rotation.

## 4. Rebuilt `hybrid-model-large`

Deleted the 13-deployment build (12/13 dead) and rebuilt from upstreams that returned 200 today:
`groq/openai/gpt-oss-120b`, `groq/qwen/qwen3.8-27b`, `gemini-2.5-flash`, `mistral-small-latest`,
`deepseek/deepseek-chat`. Fallback added to `free-mode-large`/`free-mode`.

## 5. Free-first spend policy

- `ALLOW_PAID_SPILLOVER` now defaults to **0** in `tools/start_litellm_proxy.sh`.
- Free-group fallback chains no longer contain paid targets:
  - `free-mode → free-mode-large`
  - `free-mode-large → free-mode`
  - `free-mode-fast → free-mode, free-mode-large`
  - `free-mode-tools → free-mode-fast, free-mode`
  - `hybrid-model → free-mode-large, free-mode`
- Paid pools (`paid-mode*`) remain reachable only when a client asks for them by name.

## 6. Monitor + launcher fixes

- Health gate now uses `/health/liveliness` (the full `/health` performs upstream checks and hangs).
- **Startup bug found and fixed:** with spillover disabled the launcher wrote its temporary config
  to `/tmp`, which made LiteLLM resolve the `tools.litellm_smart_cooldown` callback relative to
  `/tmp` → `ImportError: Could not import smart_cooldown` → proxy refused to start. The generated
  config now lives beside `litellm_config.yaml` (and is gitignored).
- `parse_key` label containing `$5/$20` had to be escaped (`\$5`) or `set -u` aborted the script.

## 7. Verification (2026-11-27, live)

- `GET /health/liveliness` → **200**, PID 470050, keys loaded **51/52**, spillover **DISABLED**.
- Chat 200 on: `ULTRA_FREE_CLOUD_FAST`, `ULTRA_FREE_CLOUD`, `ULTRA_FREE_NVIDIA`, `ULTRA_FREE_TOOLS`,
  `free-mode`, `free-mode-fast`, `free-mode-tools`, `free-mode-large`, `hybrid-model`,
  `hybrid-model-large`, `subq-savant-direct`, `paid-mode` — 12/12.
- Kilo JSONC re-parsed after every edit; vLLM entries resolve to the ids the servers actually serve
  (`:8000` → `Qwen3.6-35B-A3B-NVFP4`, `:8001` → `diffusiongemma-26B-A4B-NVFP4`; the `:8002` entry
  now points at `:8001`).

## 8. Still blocked (not fixable by config)

- **OpenRouter** key has credits on the account (529.23 total / 509.32 used) but the **key itself**
  carries a $45 total limit with $45.25 spent → `limit_remaining: 0` → every call is
  `403 Key limit exceeded`. `:free` models additionally return
  `429 free-models-per-day-high-balance`. **The key limit must be raised in the OpenRouter console**
  before the free deployments can serve.
- **`ollama-local`**: timeout raised to 600 s, but loading any model still fails with
  `CUDA error: out of memory` — the GPU is fully held by the two vLLM servers. Raising the timeout
  does not help; it needs VRAM freed or CPU inference.
- **aimlapi** key still returns `ALL_TIME_LIMIT_EXCEEDED`; the paid key backs a single `paid-mode`
  deployment only.

## 9. Follow-up verification (same day)

- **ollama-local resolved** — the failures were cold-load latency, not death. All 8 configured
  models answer **200** on `:11434/v1/chat/completions` with the 600 s timeout: qwen2.5:7b 4.3 s,
  llama3.1:8b 2.1 s, gemma3:12b 7.9 s, qwen2.5:14b 5.8 s, qwen2.5-coder:14b 3.5 s,
  qwen3:30b-a3b 7.5 s, deepseek-r1:32b 11.2 s, qwen3.5:35b-a3b 13.8 s. The three qwen3/r1 ids are
  thinking models and need a generous `max_tokens` (deepseek-r1:32b returns
  `"2 plus 2 equals 4."` at 300 tokens). `CUDA OOM` is transient — the GB10 has 121 GB unified
  memory, ~78 GB of it held by the two vLLM engines, so a cold 24-35 GB model can collide with
  cache growth and fall back to partial CPU offload.
- **OpenRouter cannot be fixed from here**: the key is not a provisioning key
  (`GET /api/v1/keys` → 401), so its `limit_usd: 45` / `limit_remaining: 0` cap can only be
  changed in the console. `:free` models are separately `429 free-models-per-day-high-balance`.
  Both stored OpenRouter labels are the same key, so there is no spare key to switch to.

## 10. Mistral — integrated, blocked on workspace billing (2026-11-27)

All three `mstrl_…` keys authenticate (`GET /v1/models` → 200, 51 models) but **every chat call
returns 402 `billing_no_api_budget_configured`** ("You need a subscription to access this API"),
on `mistral-small-latest`, `open-mistral-nemo`, `ministral-3b-latest`, `mistral-medium-latest`,
`open-mixtral-8x22b`. `mistral-large-latest` returns 403 `tier_not_allowed` instead — so the key's
workspace has a subscription tier but **no API budget configured**.

Confirmed by four independent paths, ruling out config/SDK problems:
- raw `curl` to `https://api.mistral.ai/v1/chat/completions`
- official `@mistralai/mistralai` 3.5.0 (`SDKError` status 403/402 with the same bodies)
- OpenAI SDK with `base_url="https://api.mistral.ai/v1"`
- LiteLLM `mistral/mistral-small-latest` (`MistralException` 402)

Wiring done so it works the moment the budget is set: the launcher parses
`MISTRAL_API_KEY_NEW_NOV27:` into `MISTRAL_API_KEY_NEW`, and the six key-duplicated deployments
were cut to three (`free-mode`, `free-mode-tools`, `hybrid-model-large`) all using that key.
The key itself lives only in `~/dbpasses.txt` (outside the repo); no credential is in this commit.

Remaining action is account-side: set an API budget at console.mistral.ai, and prefer
`mistral-medium-latest`/`mistral-small-latest` over `mistral-large-latest` on this tier.
