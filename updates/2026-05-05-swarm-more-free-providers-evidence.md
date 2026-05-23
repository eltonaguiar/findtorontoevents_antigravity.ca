# Swarm More Free Providers — Evidence & Methodology

**Date:** 2026-05-05  
**Branch:** `fix/swarm-more-free-providers-2026-05-05`  
**Files changed:** `tools/swarm/api_consult.py`, `tools/swarm/worker_runner.py`, `tools/swarm/swarm_run.py`, `tools/swarm/safety.py`, `tools/swarm/config_loader.py`, `.ruflo/orchestrator.py`  
**Backups:** `backups/2026-05-05-swarm-providers/`  

---

## Issues Found

### 1. `groq` and `huggingface` Already in `api_consult.py` but NOT Wired into `swarm_run.py` / `safety.py` (CRITICAL)

**What was broken:**  
`api_consult.py` already had `groq` and `huggingface` provider definitions. `worker_runner.py` already listed them in `API_ENGINES`. However:
- `swarm_run.py` did **not** include them in `ALL_ENGINES` or `COST_PER_1K_TOKENS`
- `safety.py` did **not** include them in `ENGINE_REQUIRED_KEYS`

This meant `isolated_env("groq")` would drop `GROQ_API_KEY` / `GROQ_KEY` from the subprocess environment, causing `api_consult.py` to fail with `groq: no key in env` even when the key was set in the parent shell.

**Evidence:**
- `tools/swarm/config_loader.py` already mapped `groq` and `huggingface` keys.
- `python3 tools/swarm/config_loader.py` shows `groq OK`.
- But `safety.py` `ENGINE_REQUIRED_KEYS` had no entry for `groq` → `isolated_env("groq")` returned only `ALWAYS_KEEP` vars.

---

### 2. Missing Truly Free / No-Key Providers (HIGH)

**What was broken:**  
When all API keys are exhausted or missing, the swarm has no fallback. OpenRouter free-tier models frequently return HTTP 404. Ollama local requires installation. There was no "zero-config, zero-key" API provider.

**Fix applied:** Added three new providers to `api_consult.py`:

| Provider | Key Required | Free Tier | Best For |
|----------|-------------|-----------|----------|
| **Pollinations** | ❌ None | Unlimited (rate-limited) | True last-resort fallback |
| **GitHub Models** | `GITHUB_TOKEN` | Free for GitHub users | Reliable gpt-4o-mini |
| **Google AI Studio (Gemini)** | `GEMINI_API_KEY` | 250 req/day (Flash) | Fast, long context |

**Pollinations** is the standout — it accepts HTTP requests with **no Authorization header at all**. This required a small patch to `call_openai_compat()` and `_post()` to skip auth when `key_envs` is empty.

---

### 3. Missing Presets for Free-Tier Discovery (MEDIUM)

**What was broken:**  
Users couldn't easily discover which engines work without paid keys. The existing presets (`all-paid-api`, `all-keyless-local`) didn't cover the new free-API landscape.

**Fix applied:** Added `all-free-api` preset:
```python
"all-free-api": ["groq", "gemini_api", "github_models", "pollinations", "ollama_local"]
```

---

## Files Changed & What Was Done

| File | Change |
|------|--------|
| `tools/swarm/api_consult.py` | Added `gemini`, `github_models`, `pollinations` to `PROVIDERS`. Added sampling defaults. Made `_post()` auth optional for keyless providers. Updated `SUPPORTED_PROVIDERS`. |
| `tools/swarm/worker_runner.py` | Added `gemini_api`, `github_models`, `pollinations` to `API_ENGINES`. |
| `tools/swarm/swarm_run.py` | Added `groq`, `huggingface`, `gemini_api`, `github_models`, `pollinations` to `ALL_ENGINES`. Added cost estimates. Added `all-free-api` preset. |
| `tools/swarm/safety.py` | Added `groq`, `huggingface`, `nous`, `openrouter`, `gemini_api`, `github_models`, `pollinations` to `ENGINE_REQUIRED_KEYS`. |
| `tools/swarm/config_loader.py` | Added `github_models`, `pollinations` to `ENGINE_KEY_ENVS`. |
| `.ruflo/orchestrator.py` | Added `gemini`, `github_models`, `pollinations` to `PAID_MODELS`. Updated `_paid_provider_for_role()` and `run_paid_api()` to handle zero-key providers. |

---

## Methodology

1. **Key inventory:** Ran `python3 tools/swarm/config_loader.py` to see which keys were already present. Found `GROQ_KEY`, `HUGGINGFACE_API`, `ANTHROPIC_API_KEY`, `KIMI_API_KEY` already set but not fully wired.
2. **Cross-reference audit:** Compared `api_consult.py PROVIDERS` against `swarm_run.py ALL_ENGINES`, `safety.py ENGINE_REQUIRED_KEYS`, and `worker_runner.py API_ENGINES`. Found mismatches.
3. **Provider research:** Searched for free OpenAI-compatible APIs. Selected Pollinations (no key), GitHub Models (free for GitHub users), and Google AI Studio (generous free tier) based on reliability and OpenAI-compat support.
4. **Implementation:** Added providers to `api_consult.py` using the existing `call_openai_compat()` path. Patched auth logic for keyless providers.
5. **Verification:**
   - `python3 -c "import py_compile; py_compile.compile('tools/swarm/api_consult.py', doraise=True)"` ✓
   - Same syntax check passed for all 6 modified files.

---

## Regression Risk

- **Low.** Pollinations, GitHub Models, and Gemini API are purely additive — they don't change existing provider behavior. The auth-optional patch in `_post()` only triggers when `key` is `None`, which only happens for `pollinations` (and any future keyless providers).
- The `safety.py` additions only expand the env vars passed to subprocesses; they don't remove any.
