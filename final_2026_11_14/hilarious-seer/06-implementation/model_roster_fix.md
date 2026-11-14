# Model Roster Fix — Remove Broken Entries

**Date:** 2026-11-14
**Worktree:** hilarious-seer
**File:** `config/api_model_roster.json`

---

## Problem

The Kilo provider/model roster contained entries that return "Model not found" errors when invoked via the Task subagent tool or other model-routing code:

- `stepfun/step-3.5-flash` → "Model not found: nous/stepfun/step-5-preview" (related stepfun family)
- `upstage/solar-pro-3` → "Model not found: nous/upstage/solar-mini4" (related upstage family)

These entries were in the `openrouter` provider's model list at lines 104 and 107 of `config/api_model_roster.json`.

## Fix

Removed both broken entries from the `openrouter.models` array:

```diff
-        "stepfun/step-3.5-flash",
         "arcee-ai/trinity-large-preview",
         "moonshotai/kimi-k2.5",
-        "upstage/solar-pro-3",
         "minimax/minimax-m2-her",
```

## Verification

- File still parses as valid JSON
- Remaining model count in openrouter block: 361 entries (was 363)
- No other `stepfun/` or `upstage/` entries remain in the file

## Related Notes

- `tools/swarm/ENGINE_KEY_ENVS.py` still references `"stepfun": ["STEPFUN_API_KEY"]` — this is for environment key mapping only and does not cause model-not-found errors
- `litellm_config.yaml` references `openai/stepfun-ai/step-3.5-flash` with a Bluesminds API base — this is a separate LiteLLM proxy config and was not modified

## Next Steps

- Re-run `model-discovery` skill to refresh the full provider roster and verify all remaining models are callable
- Consider adding a CI check that pings every model in `api_model_roster.json` and flags 404/Model Not Found entries
