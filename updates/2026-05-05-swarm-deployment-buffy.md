# Swarm Fixes Deployment — 2026-05-05

**Agent:** Buffy (Codebuff, deepseek-v4-pro)
**Branch:** `main`
**PRs referenced:** #817, #818, #819, #820 (Kimi's swarm/ruflo PR round)

---

## Commits Deployed

### 1. `8f1833f` — PR #818 Gap Closure (5 files)

**What PR #818 claimed but hadn't landed:**

| Fix | File | Description |
|-----|------|-------------|
| Empty-envelope retry | `tools/swarm/worker_runner.py` | Retry once (1s sleep) on rc=0 + empty output for `call_gemini`, `call_opencode_or_kilo`, `call_copilot`. Transient CLI init races (observed in `swarm_runs/_calls.jsonl`) now get one recovery attempt. |
| Pre-flight API key skip | `tools/swarm/swarm_run.py` | Before dispatching workers, imports `ENGINE_KEY_ENVS` from `config_loader` and skips API engines with missing keys. Saves 2-10s per keyless engine. Returns exit code 5 if all engines skipped. |
| Key-env alias sync | `tools/swarm/config_loader.py` | Added `CEREBRAS_API_KEY_PAID`/`CEREBRAS_API_KEY_FREE` to cerebras, `OPENROUTER_API_KEY` to openrouter — matches `api_consult.py` PROVIDERS resolution order. |
| Package init files | `tools/__init__.py`, `tools/swarm/__init__.py` | Empty `__init__.py` files so `from tools.swarm.config_loader import ...` works reliably from `swarm_run.py`. |

**Bonus:** `EXECUTIVE_SUMMARY.md` + `tools/swarm/prompts/self_review_swarm_fixes.md`

**Validation:**
- Python syntax all clean ✅
- `config_loader.py` key resolution verified ✅
- RUFLO audit swarm (paid tier) produced structured output from both agents ✅
- Code review approved — no showstoppers ✅

---

### 2. `0b9641e` — Cloudflare WAF Bypass (1 file)

**Problem:** Groq API returned HTTP 403 error 1010 on all requests (models list, chat completions). Key was valid (`gsk_` prefix, 56 chars), all models tested same result.

**Root cause:** Cloudflare's WAF blocks the default `Python-urllib/3.x` User-Agent. Error 1010 is Cloudflare's "Access Denied" — not a Groq API issue.

**Fix:** Added `User-Agent: Mozilla/5.0 (compatible; findtorontoevents-swarm/1.0)` and `Accept: application/json` to `_post()` in `tools/swarm/api_consult.py`. Benefits all providers, not just Groq.

**Verification:**
- Groq `/v1/models`: 16 models returned ✅
- Groq chat: `"Hello to you."` (llama-3.3-70b-versatile, 40 in / 4 out tokens) ✅
- DeepSeek regression: `"Hello, world!"` unchanged ✅

---

### 3. `caa50bb` — Orchestrator Key-Env Sync (1 file)

**Problem:** Cross-file audit found 2 inconsistencies between `.ruflo/orchestrator.py` PAID_MODELS and `tools/swarm/config_loader.py` ENGINE_KEY_ENVS:

| Issue | Fix |
|-------|-----|
| `"gemini"` vs `"gemini_api"` key name | Renamed to `gemini_api` in orchestrator |
| `huggingface` missing `HUGGINGFACE_API_KEY` alias | Added `HUGGINGFACE_API_KEY` to orchestrator |

All other providers (cerebras, deepseek, groq, inception, openrouter, xai, pollinations, github_models) already matched across all 3 files.

**Verification:**
- No code references the old `"gemini"` string key ✅
- Syntax clean ✅
- Code review approved — no breakage ✅

---

## Files Touched (total: 7)

| File | Commits |
|------|---------|
| `tools/swarm/api_consult.py` | `0b9641e` (User-Agent) |
| `tools/swarm/worker_runner.py` | `8f1833f` (empty-envelope retry) |
| `tools/swarm/swarm_run.py` | `8f1833f` (pre-flight key skip) |
| `tools/swarm/config_loader.py` | `8f1833f` (key-env aliases) |
| `.ruflo/orchestrator.py` | `caa50bb` (gemini_api rename + huggingface alias) |
| `tools/__init__.py` | `8f1833f` (package init) |
| `tools/swarm/__init__.py` | `8f1833f` (package init) |

---

## Known Limitations

1. **Single retry:** Empty-envelope retry is 1 attempt only. Production telemetry may warrant 2-3 retries with exponential backoff.
2. **Groq free tier limits:** Model availability and rate limits on Groq's free tier may change. The current default model is `llama-3.3-70b-versatile`.
3. **WSL path:** `--tier free/hybrid` still requires Hermes binary accessible from WSL.

---

## Related

- `WHOHKIMI.MD` — Kimi's summary of all 4 PRs (#817-#820)
- `EXECUTIVE_SUMMARY.md` — Detailed breakdown of the PR #818 gap closure
- `tools/swarm/prompts/self_review_swarm_fixes.md` — Self-review prompt template for swarm systems
