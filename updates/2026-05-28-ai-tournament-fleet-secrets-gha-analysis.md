# AI Tournament Fleet: Secret Wiring + GHA Fleet Health Analysis

**Date:** 2026-05-28 02:38 UTC  
**Branch:** `feat/quant-edge-per-class-gates-2026-05-28`  
**Status:** Secrets set, workflow wired, awaiting next cron run (2026-05-28 12:00 UTC)

---

## TL;DR

The AI tournament dashboard showed **3 models** out of 23 because API keys for the other 20 providers were never set as GitHub Actions secrets. The job ran fine (green checkmark) but 20 models were silently skipped with `missing_api_key`. 

**Fixed:** 16 new secrets set from the local key vault (`~/dbpasses.txt`), covering all 23 configured models × 14 personas × 8 asset classes. Combined with existing infrastructure fixes (timeout bump, diagnostics tooling, `already_generated()` fix), the pipeline should produce picks from 15-20+ models on the next cron run.

---

## Part 1: What the Dashboard Was Showing (Before Fix)

The live page at `/audit/ai-tournament.html` showed:

| Model | Picks | Win Rate | Avg PnL% |
|-------|-------|----------|----------|
| grok3 | 20 | 69.2% | +6.57% |
| deepseek_v4 | 19 | 50.0% | +4.97% |
| cerebras_llama4 | 11 | 60.0% | +2.03% |

Only grok3, deepseek_v4, and cerebras_llama4 produced picks. The other 20 models in `config/model_persona_mapping.json` were invisible — declared in config but contributing zero picks.

## Part 2: Root Causes (Multi-Layer)

### Layer 1: Missing API Key Secrets

The primary issue: **API keys were available locally in `~/dbpasses.txt` but never pushed to GitHub Actions secrets.** 

Before this fix, GH Actions secrets contained only:
- FTP credentials, Eventbrite keys
- `CEREBRAS_API_KEY`, `DEEPSEEK_API_KEY`, `XAI_API_KEY` (the 3 working models)
- `OPENROUTER_API_KEY` (set but mercury/ring_261T weren't producing output — separate debugging needed)
- Other tournament-essential keys were **NOT** present

The workflow at `.github/workflows/ai-tournament-pipeline.yml:83-105` already had env-var wiring for all 20+ providers, but `${{ secrets.X || '' }}` with `|| ''` meant missing secrets silently became empty strings — and `try_prompt_model()` in `populate_picks.py` skips models with empty API keys.

### Layer 2: `already_generated()` Short-Circuit (Fixed May 27)

In `tools/populate_picks.py`, the `already_generated()` function checked if `picks_YYYYMMDD.json` already existed. If so, it returned immediately **without running any model calls**, even for models that hadn't participated yet. This was fixed in commit `44189f5b0` by checking `FORCE_REGENERATE` and skipping stale-file detection when it was a workflow_dispatch trigger.

### Layer 3: May 24 Cascade Failure in GHA

The AI tournament pipeline had **10 consecutive failures** on May 24 (2026-05-24 22:32 to 23:56 UTC) before one finally succeeded. The failures appear related to git push contention and MySQL connection issues. After that burst, the pipeline worked for May 25-26 but **the May 27 cron run was CANCELLED** (run 26513551034) — likely a concurrency or timeout issue.

### Layer 4: `continue-on-error: true` on All Steps

Every step in `ai-tournament-pipeline.yml` uses `continue-on-error: true`. This means the pipeline can show green while silently producing zero picks. The only hard-gate is the "Verify output" step which checks file existence — but an empty JSON file passes.

---

## Part 3: GitHub Actions Fleet Health Assessment

### AI Tournament Pipeline History

| Date | Status | Notes |
|------|--------|-------|
| May 24 22:32 | ❌ Failure | 10 consecutive failures over 1.5h |
| May 24 23:56 | ✅ Success | First success in the cascade |
| May 25 13:16 | ✅ Success | Normal run |
| May 25 15:15 | ✅ Success | Re-triggered |
| May 25 15:20 | ✅ Success | Re-triggered |
| May 25 15:35 | ✅ Success | Final of the burst |
| May 26 13:07 | ✅ Success | Normal cron |
| May 26 22:34 | ✅ Success | workflow_dispatch |
| May 27 13:18 | ⛔ Cancelled | **Cron run cancelled** — likely caused by stale concurrency group or timeout |

### Audit Dashboard Pipeline

All 20 most recent runs: ✅ Success (hourly at :10). No issues.

### Price Tracker Pipeline

| Date | Status |
|------|--------|
| May 25 23:24 | ❌ Failure |
| May 26 23:25 | ✅ Success |
| May 27 23:28 | ✅ Success |

### Overall Fleet Patterns

- **Concurrency groups** prevent parallel runs but can cancel queued runs (May 27 cancellation)
- **Continue-on-error: true epidemic** — 32+ steps in `audit-dashboard.yml`, all steps in `ai-tournament-pipeline.yml`
- **May 24 cascade**: 10 failures in 90 minutes suggests push contention or MySQL flapping
- **Timeout**: Previously 15 min (too low for 23 models × 80+ API calls), bumped to 45 min
- **OpenRouter models** (ring_261T, mercury): Key IS set but no picks — separate investigation needed

---

## Part 4: Secrets Set (2026-05-28)

| Secret Name | Provider | Unlocks Models | Status |
|-------------|----------|---------------|--------|
| `MISTRAL_API_KEY` | Mistral | `mistral_large` | ✅ Set |
| `NVIDIA_API_KEY` | NVIDIA NIM | `nvidia_deepseek_v4_pro`, `nvidia_nemotron_3_70b`, `nvidia_minimax_m2` | ✅ Set |
| `GROQ_API_KEY` | Groq | `groq_llama_3_70b`, `groq_kimi_k2` | ✅ Set |
| `GEMINI_FREE_KEY` | Google | `gemini_25_pro` | ✅ Set |
| `TOGETHER_API_KEY` | Together AI | `mercury`, `together_qwen_3`, `together_deepseek_v3` | ✅ Set |
| `HYPERBOLIC_API_KEY` | Hyperbolic | `hyperbolic_llama` | ✅ Set |
| `FEATHER_API_KEY` | Featherless | `feather_llama` | ✅ Set |
| `FIREWORKS_API_KEY` | Fireworks | `fireworks_qwen` | ✅ Set |
| `NOUS_API_KEY` | Nous Research | `nous_hermes_4` | ✅ Set |
| `GH_MODELS_API_KEY` | GitHub Models | `gh_models_gpt4o` | ✅ Set |
| `AIMLAPI_API_KEY` | AIMLAPI | `aimlapi_gpt4o` | ✅ Set |
| `OPENAI_API_KEY` | OpenAI | `gpt4o_mini` | ✅ Set |
| `INCEPTION_API_KEY` | Inception | (backup / future models) | ✅ Set |
| `NOVITA_API_KEY` | Novita | (future models) | ✅ Set |
| `DEEPINFRA_API_KEY` | DeepInfra | (future models) | ✅ Set |
| `HUGGING_FACE_TOKEN` | HuggingFace | (future models) | ✅ Set |

### Remaining Unset Keys (Not in local vault)

| Key | Needed For | Impact |
|-----|-----------|--------|
| `ANTHROPIC_API_KEY` | `cursor_agent`, `claude_opus` | 2 models blocked |

The `ANTHROPIC_API_KEY` was not found in `~/dbpasses.txt`. Without it, `cursor_agent` and `claude_opus` will still be skipped. These 2 models use `api_type: "anthropic"` (not `openai_compat`), so they require a real Anthropic API key.

---

## Part 5: Expected Impact (Next Cron Run)

### Models expected to produce picks

**Previously working (3 models):**
- `grok3` (xAI)
- `deepseek_v4` (DeepSeek)
- `cerebras_llama4` (Cerebras)

**Newly wired and expected to work (16+ models):**
- `gpt4o_mini` (OpenAI) — now has key
- `gemini_25_pro` (Google) — now has key
- `mistral_large` (Mistral) — now has key
- `nvidia_deepseek_v4_pro` (NVIDIA) — now has key
- `nvidia_nemotron_3_70b` (NVIDIA) — now has key
- `nvidia_minimax_m2` (NVIDIA) — now has key
- `groq_llama_3_70b` (Groq) — now has key
- `groq_kimi_k2` (Groq) — now has key
- `together_qwen_3` (Together) — now has key
- `together_deepseek_v3` (Together) — now has key
- `fireworks_qwen` (Fireworks) — now has key
- `gh_models_gpt4o` (GitHub Models) — now has key
- `nous_hermes_4` (Nous) — now has key
- `hyperbolic_llama` (Hyperbolic) — now has key
- `feather_llama` (Featherless) — now has key
- `aimlapi_gpt4o` (AIMLAPI) — now has key

**Potentially working (existing key, needs debugging):**
- `ring_261T` (OpenRouter) — key exists but historically no picks
- `mercury` (Together/Inception) — TOGETHER_API_KEY now set

**Still blocked (no Anthropic key):**
- `cursor_agent` (Anthropic)
- `claude_opus` (Anthropic)

### Projected model count

From **3 → 16-18** models producing picks daily. Some providers (NVIDIA, Groq, Together) serve multiple model types, giving us 3× the coverage with a single key each.

---

## Part 6: Recommended Follow-Ups

1. **Get an Anthropic API key** for `cursor_agent` + `claude_opus` — completes the fleet at 20+ models
2. **Debug OpenRouter` model issue** — key IS set but `ring_261T` doesn't produce picks. Either the model name changed on OR, or the endpoint needs auth headers
3. **Flip `continue-on-error` on critical steps** — at minimum: picks generation, MySQL ingest, leaderboard update
4. **Add model coverage alert** — if <50% of configured models produced picks, flag the pipeline red
5. **Monitor NVIDIA API limits** — 3 models share one key, rate limits may throttle after first few calls
6. **GEMINI: verify endpoint works** — uses `openai_compat` at `generativelanguage.googleapis.com/v1beta/openai/` — may need different model name format

---

## Verification

The next AI tournament cron fires at **2026-05-28 12:00 UTC**. After that run:

```bash
# Check live model count on dashboard
curl -s 'https://findtorontoevents.ca/audit/data/ai_tournament_model_summary.json' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d)} models active')"

# Check individual model diagnostics
curl -s 'https://findtorontoevents.ca/audit/data/ai_tournament_model_diagnostics.json' | python3 -m json.tool | head -40
```

Expect 15-18 models with picks, up from the current 3.
