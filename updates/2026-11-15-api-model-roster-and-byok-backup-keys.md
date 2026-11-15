# API Model Roster & BYOK Backup Keys Update (2026-11-15)

## What Was Broken
1. **Stale / Retired Default Model IDs in `tools/api_model_roster.py` and `tools/swarm_models.py`**:
   - **Groq (`groq`)**: Default model `llama-3.3-70b-versatile` was retired upstream (returning `HTTP 404: The model llama-3.3-70b-versatile does not exist`), and `tools/api_model_roster.py` lacked `extra_headers={"User-Agent": "Mozilla/5.0"}`, causing Cloudflare `HTTP 403: error code: 1010` during probes.
   - **Kimi / Moonshot (`kimi`)**: Default model `moonshot-v1-32k` was retired upstream (returning `HTTP 404: Not found the model moonshot-v1-32k`), and `PLATFORM_KIMI_AI_CONSOLE_API` was not listed in `key_envs` / `env_vars`.
   - **DeepSeek (`deepseek`)**: `/models` now serves `deepseek-v4-pro` and `deepseek-flash`; `models_url` was `None` in `tools/api_model_roster.py`.
   - **LLM7 (`llm7`)**: Default model `qwen2.5-coder-32b` returned `HTTP 400: Model 'qwen2.5-coder-32b' is currently unavailable`.
   - **Reasoning Response Parsing (`tools/api_model_roster.py`)**: Reasoning models (`kimi-k3.1-pro`, `deepseek-v4-pro`, `openai/gpt-oss-120b`) populate `message.reasoning_content` (or `reasoning`) on short `max_tokens` ping probes when `message.content` is empty.
2. **IDE `chatLanguageModels.json` Missing Backup Providers**:
   - Local IDE `chatLanguageModels.json` (`Code\User\chatLanguageModels.json` and `Antigravity\User\chatLanguageModels.json`) only had `LocalVLLM` and `Inception Mercury` configured, lacking the 5 backup providers (`Kimi`, `Groq`, `DeepSeek`, `LLM7 Free`, `OpenRouter`).

## What Changed
1. **`tools/api_model_roster.py`**:
   - Updated `groq` default model to `qwen/qwen3.8-27b` and added `extra_headers={"User-Agent": "Mozilla/5.0"}`.
   - Updated `deepseek` `models_url` to `https://api.deepseek.com/models` and default model to `deepseek-flash`.
   - Updated `kimi` `key_envs` to include `PLATFORM_KIMI_AI_CONSOLE_API`, `models_url` to `https://api.moonshot.ai/v1/models`, and default model to `kimi-k3.1-pro`.
   - Updated `llm7` default model to `DeepSeek-V4-Flash-0731`.
   - Updated `http_chat()` response extraction to fall back to `reasoning_content` / `reasoning` when `content` is empty.
2. **`tools/swarm_models.py`**:
   - Updated `deepseek` to `deepseek-v4-pro` and added `deepseek-flash` (`tier="fast"`).
   - Updated `groq` to `openai/gpt-oss-120b` + added `groq-qwen` (`qwen/qwen3.8-27b`) with `User-Agent: Mozilla/5.0`.
   - Updated `kimi` to `kimi-k3.1-pro` + added `kimi-code` (`kimi-k2.7-code`) and `PLATFORM_KIMI_AI_CONSOLE_API` env resolution.
   - Updated `llm7` to `DeepSeek-V4-Flash-0731` and `openrouter` to `deepseek/deepseek-v4-flash:free`.
3. **`config/api_model_roster.json`**:
   - Re-probed `groq`, `deepseek`, `kimi`, `llm7`, and `openrouter` with live `/models` discovery and `/chat/completions` ping verification.
4. **Local Machine Environment & IDE BYOK Configs (Not Tracked in Git)**:
   - Updated `HKCU\Environment` with all 10 env var aliases for the 5 backup keys.
   - Wrote `chatLanguageModels.json` (8 provider blocks) to `AppData\Roaming\Code\User\`, `AppData\Roaming\Antigravity\User\`, and `.config\Code\User\`.

## Verification
- Ran `python tools/api_model_roster.py --probe <slug>` across `groq`, `deepseek`, `kimi`, `llm7`, and `openrouter`: all 5 returned `key=Y` and `ping=OK` (`HTTP 200`).
- Ran `python -m py_compile tools/api_model_roster.py tools/swarm_models.py`.
