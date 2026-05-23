# Swarm Critical Fixes — 2026-05-05

Source: `swarm_runs/RUFLO_TOOLS_SWARM_COMPREHENSIVE_REVIEW.md`

## CRITICAL: Cost Overrun (swarm_run.py)

**Root cause:** `estimate_cost_usd()` used a flat gpt-4o-mini rate for openrouter regardless of `OPENROUTER_MODEL` env var. A user setting `OPENROUTER_MODEL=anthropic/claude-opus-4` would see a $0.01 cost estimate when actual spend was ~$150.

**Fix:**
- Added `OPENROUTER_MODEL_RATES` dict with 22 model-specific rates from openrouter.ai pricing (OpenAI, Anthropic, Google, DeepSeek, xAI, Meta, Mistral, free-tier models)
- Added `_get_openrouter_model()` helper (reads `OPENROUTER_MODEL` env)
- Added `_lookup_openrouter_cost(model_tag)` with resolution order: exact match → provider-prefix fallback → 10x unknown-safety multiplier → gpt-4o-mini fallback
- Modified `estimate_cost_usd()` to route openrouter through `_lookup_openrouter_cost()`

**Functional verification:**
```
default openrouter (gpt-4o-mini):    $0.0028
claude-opus-4 override:              $0.3375  ← 120x correction ✓
deepseek + openrouter + xai mix:     $0.0701
unknown model (10x safety margin):   $0.0259
```

## HIGH: Thread Safety (orchestrator.py)

**Root cause:** `run_swarm_audit()` used bare `results = {}` shared across threads without any synchronization. Multiple threads writing simultaneously could cause dict corruption or lost results.

**Fix:** Added `results_lock = threading.Lock()` protecting all reads/writes to the shared `results` dict in the parallel audit path.

## HIGH: HTTP Deadline Enforcement (api_consult.py)

**Root cause:** `_post()` had per-request timeout (`timeout=180`) but no overall call-budget enforcement. Multiple retries with exponential backoff (1s → 2s → 4s) could accumulate to exceed intended time limits.

**Fix:**
- Added `DEFAULT_HTTP_TIMEOUT = 60` (per-attempt cap in seconds)
- Added `DEFAULT_MAX_TOTAL_DURATION = 180` (total across all attempts)
- Added `_deadline` parameter to `_post()` with `time.time() + DEFAULT_MAX_TOTAL_DURATION` as default
- Added `remaining = deadline - time.time()` check before each attempt
- Per-request timeout clamped to `min(timeout, max(5, int(remaining * 0.8)))` to leave 20% headroom
- Raises `TimeoutError` if deadline exceeded before next attempt

## MEDIUM: Key Sanitization Gaps (orchestrator.py + api_consult.py)

**Root cause:** `sanitize_keys()` had 10 patterns, missing modern key formats. Leak risk for Anthropic sk-ant-*, Gemini AIza*, GitHub fine-grained PATs, JWT tokens, MongoDB conn strings, PEM private keys, Azure endpoints.

**Fix:** Expanded both `sanitize_keys()` (orchestrator.py) and `_sanitize_for_log()` (api_consult.py) from 10 to 22 patterns covering:
- OpenAI: `sk-*`, `sk-proj-*`
- Anthropic: `sk-ant-*`, `sk-ant-api03-*`
- Cerebras/xAI proprietary formats
- Gemini/Google: `AIza*`, `GOOGLE_API_KEY`
- GitHub: `github_pat_*`, `ghp_/ghs_/gho_/ghu_/ghr_`
- JWT: `eyJ...eyJ...*`
- MongoDB: `mongodb://user:pass@host`
- Bearer tokens, generic API keys, PEM private keys, Azure endpoints

## Also Fixed: Duplicate Dict Key

Removed duplicate `\"openrouter\"` key in `COST_PER_1K_TOKENS` (Python dicts silently keep last value on duplicate keys — no crash but confusing to future editors).

## Verification

- All 3 files: syntax check passes (`ast.parse`)
- swarm_run.py: functional test confirms 120x cost correction
- orchestrator.py: thread safety verified by review
- api_consult.py: deadline enforcement verified by review

**Commit:** `8b5d8542e97` on `fix/swarm-cerebras-sdk-fallback-2026-05-05`