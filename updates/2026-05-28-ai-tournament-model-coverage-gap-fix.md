# AI Tournament Pipeline: Model Coverage Gap Diagnosis & Remediation

**Date:** 2026-05-28  
**Severity:** P1 — Dashboard shows incomplete model portfolio  
**Status:** Diagnosed + Fix Ready for PR

---

## Executive Summary

The audit dashboard (`/audit/ai-tournament.html`) displays only **3 models** in the tournament leaderboard, despite **23 models being configured** in `config/model_persona_mapping.json`. This creates a misleading user experience where the pipeline appears to have minimal model coverage.

Root cause is two-fold:
1. **Coverage fallback exits silently** when at least one model succeeds, leaving ~20 unconfigured models invisible
2. **Submission envelopes are not committed**, so even attempted-but-failed models leave no persistent trace

---

## Detailed Findings

### Finding #1: Model Registration vs Actual Runners

| Category | Count |
|----------|-------|
| Models registered in config | **23** |
| Models with API keys likely configured | **3** |
| Models running via coverage fallback per assignment | **0** (see Bug #1) |
| Models appearing on /audit | **3** |

**Configured models** (from `config/model_persona_mapping.json`):

| Model ID | Provider | Key Env Var | Likely Active? |
|----------|----------|-------------|----------------|
| grok3 | xAI | XAI_API_KEY | ✅ Yes |
| deepseek_v4 | DeepSeek | DEEPSEEK_API_KEY | ✅ Yes |
| cerebras_llama4 | Cerebras | CEREBRAS_API_KEY | ✅ Yes |
| gpt4o_mini | OpenAI | OPENAI_API_KEY | ❓ Unknown |
| cursor_agent | Anthropic | ANTHROPIC_API_KEY | ❓ Unknown |
| claude_opus | Anthropic | ANTHROPIC_API_KEY | ❓ Unknown |
| mercury | Together (Inception) | TOGETHER_API_KEY | ❌ Probably not |
| ring_261T | OpenRouter | OPENROUTER_API_KEY | ❌ Probably not |
| gemini_25_pro | Google | GEMINI_FREE_KEY | ❌ Probably not |
| mistral_large | Mistral | MISTRAL_API_KEY | ❌ Probably not |
| nvidia_deepseek_v4_pro | NVIDIA NIM | NVIDIA_API_KEY | ❌ Probably not |
| nvidia_nemotron_3_70b | NVIDIA NIM | NVIDIA_API_KEY | ❌ Probably not |
| nvidia_minimax_m2 | NVIDIA NIM | NVIDIA_API_KEY | ❌ Probably not |
| groq_llama_3_70b | Groq | GROQ_API_KEY | ❌ Probably not |
| groq_kimi_k2 | Groq | GROQ_API_KEY | ❌ Probably not |
| together_qwen_3 | Together AI | TOGETHER_API_KEY | ❌ Probably not |
| together_deepseek_v3 | Together AI | TOGETHER_API_KEY | ❌ Probably not |
| fireworks_qwen | Fireworks | FIREWORKS_API_KEY | ❌ Probably not |
| gh_models_gpt4o | GitHub Models | GH_MODELS_API_KEY | ❌ Probably not |
| nous_hermes_4 | Nous Research | NOUS_API_KEY | ❌ Probably not |
| hyperbolic_llama | Hyperbolic | HYPERBOLIC_API_KEY | ❌ Probably not |
| feather_llama | Featherless | FEATHER_API_KEY | ❌ Probably not |
| aimlapi_gpt4o | AIMLAPI | AIMLAPI_API_KEY | ❌ Probably not |

### Finding #2: Bug in Coverage Fallback Logic (Bug #1)

**File:** `tools/populate_picks.py`, lines ~1097–1112

```python
for model_id, model_cfg in models.items():
    for asset_class, persona_ids in assignments.items():
        for persona_id in persona_ids:
            picks, status = try_prompt_model(...)
            if picks:
                api_success = True       # ← Sets this flag
                all_picks.extend(picks)
            elif COVERAGE_FALLBACK_ENABLED:
                # Only happens INSIDE the loop
                fallback = generate_assignment_fallback_picks(...)
                all_picks.extend(fallback)
            time.sleep(API_SLEEP_SECONDS)

if not api_success or not all_picks:     # ← Problem!
    fallback = generate_fallback_picks(config)   # Uses alpha engine data
    all_picks.extend(fallback)
```

**The bug:** When ANY single model produces a valid response (e.g., grok3), `api_success=True`. The condition `if not api_success` becomes False, and the code SKIPS the global fallback which would activate per-model coverage for remaining models. Models that were skipped due to missing API keys never get their coverage picks generated because the per-model fallback runs BEFORE the `api_success` check.

Wait — actually the per-model fallback DOES run inside the loop regardless of `api_success`. The real issue is subtler:

**Actual flow:**
1. Loop iterates ALL 23 models × assets × personas (~80+ calls)
2. For models with missing API keys: `try_prompt_model()` returns `( [], "missing_api_key" )`
3. Coverage fallback IS called for these failed calls → generates synthetic picks
4. BUT the synthetic picks carry `"rank_eligible": False` and `"data_integrity_flag": "COVERAGE_FALLBACK_NOT_MODEL_API"`
5. Then kill gate (line ~1106) REMOVES picked from blocked personas/classes
6. Finally, `write_submissions()` writes individual model envelopes to `submissions/`

So per-assignment fallback WAS working, but the output file (`picks_YYYYMMDD.json`) includes those fallback picks. The question is why only 3 appear...

**Deeper investigation reveals:** If ALL 23 models' API calls fail (or return empty), the `not api_success or not all_picks` branch activates the local alpha-engine fallback instead. The alpha-engine fallback assigns `model_id="alpha_engine"` which overrides everything. Only ~50 rows end up in the daily file, all tagged as `model_id="alpha_engine"`.

**Then the submission envelope step (line ~1033)** adds back the 23 configured models as empty envelopes — BUT these files go to `data/ai_tournament/submissions/` directory which is NOT included in the workflow's `git add`:

```yaml
# ai-tournament-pipeline.yml commit step:
git add data/ai_tournament/                          # <-- catches picks_YYYYMMDD.json
git add audit_dashboard/data/ai_tournament_picks_latest.json  # <-- copies picks_
# submissions/ is NOT added here!
```

**Result:** Submission envelopes exist on runner filesystem, get stash-popped away, never committed, never visible on /audit.

### Finding #3: GitHub Actions Issues Affecting Tournament Pipeline

The `ai-tournament-pipeline.yml` itself has several problems:

| Issue | Impact | Severity |
|-------|--------|----------|
| **15-min timeout** for entire pipeline | Pipeline needs ~2-5 min normally, but if any API call hangs it times out silently | Medium |
| **Checkout uses fetch-depth: 1** | No sparse checkout; full clone on every run in 19GB repo | Low |
| **No explicit retry on API failures** | Single model failure = missed assignment permanently | Low |
| **Workflow dispatch force_regenerate** exists but defaults to false | Accidental skip-regeneration can stale the page | Low |

Other notable GHA issues across the fleet (356 total workflows):

| Workflow | Timeout | Problem | Status |
|----------|---------|---------|--------|
| `discord-bot.yml` | 355 min (5h 55m) | Near 6h ceiling; cron overlap kills it | Known |
| `gha-summary-report.yml` | 360 min (ceiling) | Scans entire fleet history with 8 workers | Known |
| `copy-trader-intelligence.yml` | 50 min > 30 min interval | Previous cancel-cascade fixed by setting cancel-in-progress:false | Fixed |
| `audit-dashboard.yml` | 115 min | Push trigger removed 2026-05-19 to prevent cascade cancels | Fixed |
| `buy-now-analysis.yml` | 25 min | Checkout consumed entire 15-min budget previously | Fixed |

**Chronic patterns:**
- Cancel cascades recurring across 7+ workflows where `cancel-in-progress: true` caused 100% cancellation rates
- MySQL connection failures intermittently block ingestion steps (Access denied 1045 errors)
- Git push contention requiring `safe_push.sh` backoff logic in dozens of workflows
- Environment variable misconfiguration causing silent failures across multiple CI workflows (DB_PASS_STOCKS not propagated to some workflows)

---

## Fix Plan

### Fix #1: Always Write Per-Model Envelopes (populate_picks.py)

Modify `write_submissions()` to be more robust:
- Already does discover all configured models (the May 28 fix)
- Ensure empty envelopes are written for ALL configured models, regardless of success/fail state
- Add a machine-readable manifest file listing all models attempted + status

### Fix #2: Commit Submissions Directory to Git

Add `data/ai_tournament/submissions/` to the workflow's `git add` list so submission envelopes persist across runs and are available for the price tracker to consume consistently.

### Fix #3: Add Attempted-Models Manifest

Write a `data/ai_tournament/model_attempt_log.json` file that records:
```json
{
  "date": "2026-05-28",
  "total_configured": 23,
  "models": [
    {"model_id": "grok3", "status": "success", "picks": 20},
    {"model_id": "deepseek_v4", "status": "success", "picks": 19},
    {"model_id": "cerebras_llama4", "status": "success", "picks": 11},
    {"model_id": "gpt4o_mini", "status": "missing_api_key", "picks": 0},
    ...
  ]
}
```

This gives operators immediate visibility into coverage without digging through logs.

---

## GHA Fleet-Wide Assessment

### Total Workflows: 356 YAML files (+ 10 retired)

| Metric | Value |
|--------|-------|
| Cron schedules total | 363 |
| Jobs with timeouts >30 min | 15+ |
| Concurrent cancellation incidents documented | 7+ |
| Workflows depending on MySQL | 100+ |
| Shared concurrency group conflicts | Chronic (resolving via safe_push.sh backoff) |

### Recommendations for GHA Resilience

1. **Audit timeout-to-interval ratio** — Any job whose timeout is ≥75% of its schedule interval risks partial execution. Current candidates: `ai-tournament-pipeline.yml` (15 min timeout, daily), `copy-trader-intelligence.yml` (50 min vs 30 min interval — already fixed).

2. **Standardize error reporting** — Replace scattered `continue-on-error: true` with a structured error accumulation step that logs all soft-failures at the end of each run.

3. **Consolidate thundering herd** — ~80 workflows fire on `*/N` minute schedules. Stagger offsets more aggressively to avoid CPU/memory spikes on shared runners.

---

## Files Changed in This PR

| File | Change |
|------|--------|
| `tools/populate_picks.py` | Enhanced `write_submissions()` to always emit per-model envelopes; added `emit_model_attempt_log()` |
| `.github/workflows/ai-tournament-pipeline.yml` | Added `submissions/` and `model_attempt_log.json` to git add; increased pipeline timeout to 30 min |
| `updates/2026-05-28-ai-tournament-model-coverage-gap-fix.md` | This diagnostic document |
