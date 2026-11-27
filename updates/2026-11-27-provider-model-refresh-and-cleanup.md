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

## 11. LLM7 — confirmed no free tier, wallet at $0.00, fully removed

`GET https://api.llm7.io/v1/balance` on both stored keys (they belong to the same account,
`zerounderscore@gmail.com`):

```json
{"email":"zerounderscore@gmail.com","balance_usd":"0.00000000"}
```

Catalogue evidence across all 84 models: **zero** with a `0` input price (range $0.01–$7.00 per
1M tokens), no `tier: free` entries (only `pro`/`turbo`), and 79/84 flagged `usage_based_only`.
The 5 exceptions (`codestral-latest`, `gpt-oss:120b`, `gpt-oss:20b`, `kimi-k2.7-code`,
`minimax-m3`) are cheaper, not free — `codestral-latest` at $0.01/1M is the only one that answers on
a zero balance, and it throttles to `429` after one request. Anonymous access lists the same paid
catalogue, so there is no keyless free pool either.

Removed: the proxy deployment (earlier this pass), the Kilo provider, and now the leftover
launcher plumbing (`parse_key "LLM7_API_KEY_FREE"` + the `LLM7_API_KEY` pre-flight entry).
Verified: 0 `llm7` references in `litellm_config.yaml` deployments, the generated spillover config,
the running proxy's `/v1/models`, and `kilo.jsonc`.

## 13. Gemini 2.x retirement + Bluesminds moved to paid-only

**What "migrate Gemini" meant:** not a cosmetic version bump. Per the sourced listing, the Gemini
2.5 Pro/Flash **free tier shuts down 2026-12-01**, and `gemini-2.5-flash` already returns
`429 You exceeded your current quota` on our key. "Migrate" = change only the model string on the
same endpoint/key, to ids that are live and free today.

| Old id | Deployments | New id | Live check |
|---|---|---|---|
| `gemini-2.5-flash` | 12 | `gemini-3.5-flash-lite` | direct 200 with content |
| `gemini-2.5-flash-lite` / `2.0-flash*` | 10 | `gemini-3.1-flash-lite` | direct 200 with content |
| `gemini-3-flash-preview` | 2 | `gemini-3.5-flash-lite` | old id 429 on free tier |
| `gemini-2.5-pro` | 2 | unchanged | `gemini-3.1-pro-preview` 429s on this tier |

`gemini-3.6-flash`/`3.8-flash` returned 503 (overloaded) and `gemini-3.5-flash` timed out, so they
were not used.

**Bluesminds** has $98.93 allocated, so it now backs **paid pools only** — the three `llama-3.1-8b`
deployments were removed from `free-mode`, `free-mode-fast` and `free-mode-tools`; remaining
Bluesminds deployments are in `paid-mode`, `paid-mode-fast`, `paid-mode-large`.
Caveat: with the real key every configured Bluesminds id returns
`503 No available channel for model …` — the account's model ids have changed, so the paid entries
need their ids refreshed from `GET /v1/models` before they can answer.

**Newly tested and rejected** (valid key, no budget — not wired): Requesty (402 org balance, 760
models listed), Routeway (402 insufficient balance, 278 models), SiliconFlow `.com` (402 balance,
80 models). Scaleway auth works but every chat is `423 model_locked`; OVH stays 429 even after a
70 s cooldown at its 2 RPM/IP.

## 14. Cohere + Bluesminds re-check (both keys valid; why they still can't carry traffic)

**Cohere** — `COHERE API KEY` (masked `coher…`, dbpasses): `GET /v2/models` **200, 20 models**, but
every chat is
`429 You are using a Trial key, which is limited to 1000 API calls / month`.
So the key is alive and the allowance is real, it is just **spent for this month**. It is a monthly
reset, so it can be re-added on the 1st — left out of the config until then.

**Bluesminds** — `BLUESMIND API KEY` (masked `sk-EbS…`, dbpasses line 286, 51 chars): key is **valid**
and a single request returns **200** with `nvidia/nemotron-3.5-lightning-30b-a3b`.
`/v1/dashboard/billing/subscription` → `has_payment_method: true`, no spend cap; `/usage` →
`total_usage: 107.1328`. Two things had made it look dead:

1. **Every previously configured id is retired** — `gpt-5-chat`, `grok-4.20-fast`, `kimi-k2.6`,
   `kimi-k2.5`, `grok-code-fast-1`, `MiniMax-M2`, `gpt-oss-120b`, `step-3.5-flash`, `glm-5.1` all
   returned `503 No available channel`. Live ids from `GET /v1/models` (27) are `nvidia/*`,
   `meta/*`, `moonshotai/kimi-k3` (410 EOL), `z-ai/glm-5.3-flash`, `google/diffusiongemma-26b-a4b-it`.
   Many of those are EOL too (`410 The model … has reached its end of life`).
2. **Burst rate limiting** — my 7-way parallel probe produced
   `429 You have reached the total request limit: maximum …`; sequential calls succeed.

All 14 Bluesminds deployments (paid-mode, paid-mode-fast, paid-mode-large) now point at
`openai/nvidia/nemotron-3.5-lightning-30b-a3b`, the one id verified 200 end-to-end.

**Caveat for callers:** that model is a reasoning model — it returns its text in
`reasoning_content` and `content: null` unless `max_tokens` is large enough for it to finish
thinking. Callers must send a generous `max_tokens` (or read `reasoning_content`).

Verified after restart: liveliness 200; `free-mode`, `free-mode-fast`, `free-mode-tools`,
`paid-mode`, `paid-mode-large` all 200; Bluesminds free-tier deployments remain removed.

## 15. Cohere monthly re-check and the COMS roster crash fix

**Cohere re-check (scheduled).** `tools/cohere_monthly_recheck.py` probes the trial key once and,
because the allowance is a *monthly* 1000 calls, puts it back automatically when it starts answering:

- probe: `POST https://api.cohere.com/v2/chat` (`command-r-plus-08-2024`, `max_tokens: 8`);
- `200` → insert the `cohere/command-r-plus-08-2024` deployments into `free-mode` and
  `free-mode-large` (key from `os.environ/COHERE_API_KEY`, which the launcher already parses from
  `COHERE_TRIAL_API_KEY`), restart the proxy, verify `free-mode`, write `reports/cohere_recheck_state.json`;
- `429` → change nothing, record `quota_exhausted`;
- `401/403` → record `key_rejected`, change nothing (a new key is a human decision);
- `--dry-run` probes without touching config; `--no-restart` wires but leaves the process alone.

Installed cron (user crontab): `15 9 1 * * … python3 tools/cohere_monthly_recheck.py >> logs/cohere_recheck.log 2>&1`
— 09:15 on the 1st, i.e. after the quota resets at month boundary.
Verified: `--dry-run` on 2026-11-27 returned 429 → `status: quota_exhausted`, no config change, exit 0.

**COMS roster crash.** `COMS roster` died with
`AttributeError: 'str' object has no attribute 'get'` from `take(obj)` in
`AGENT_FOLDERFRAMEWORK/COMMUNICATION/coms`: a retained `registry/#` payload can be a bare JSON
string, and `take()` assumed every payload parses to an object. Fixed with a
`if not isinstance(obj, dict): return` guard at the top of `take()`, so one malformed row cannot
blank the whole roster. `bash -n` passes and `COMS roster` now prints the table.
Pushed for review: `eltonaguiar/AGENT_FOLDERFRAMEWORK` branch `fix/coms-roster-nonobject-guard`,
PR https://github.com/eltonaguiar/AGENT_FOLDERFRAMEWORK/pull/12 (only `COMMUNICATION/coms` changed).
`coms.ps1` does not share the bug — its `ConvertFrom-Json` result is accessed as a property, which
yields `$null` rather than throwing.

**Bluesminds end-to-end.** With `max_tokens: 1200` a real prompt through the proxy returned useful
prose: `paid-mode` → 218 chars, `paid-mode-large` → 246 chars, and directly against Bluesminds the
`nvidia/nemotron-3.5-lightning-30b-a3b` deployment returned 267 chars of content with 2034 chars of
`reasoning_content` (497 completion tokens). `GET /model/info` shows all 14 Bluesminds deployments
registered under `paid-mode` / `paid-mode-fast` / `paid-mode-large`.
