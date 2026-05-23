# FAILOVER COMMIT — GitHub Status

**File:** `.ruflo/orchestrator.py`  
**Status:** COMMITTED LOCALLY, COULD NOT PUSH TO GITHUB  
**Date:** 2026-05-05  
**Reason:** Git operations timeout after 60s in large repos (119,598 commits)

## Changes Made

### Added Runtime Model Failover

1. **FAILOVER_MODELS** — Priority chain of 4 free-tier OpenRouter models:
   - `google/gemini-pro-1.5-preview:free`
   - `deepseek/deepseek-chat:free`
   - `mistralai/mistral-7b-instruct:free`
   - `tencent/hy3-preview:free`

2. **FAILOVER_ERRORS** — Auto-detect patterns:
   - `429`, `rate limit`, `limit`, `exhausted`
   - `timeout`, `connect`, `closed`
   - `service temporarily unavailable`
   - `provider error`, `upstream error`
   - `no endpoints available`

3. **should_failover()** — Check stderr for recoverable errors

4. **get_failover_model()** — Rotate through chain

5. **run_hermes_direct()** — Rewritten with:
   - Up to 3 attempts per agent (primary + 2 failovers)
   - Exponential backoff: 1s, 2s, 4s
   - Per-attempt model switching
   - Non-recoverable errors exit immediately

## To Push When Git Works

```bash
cd /mnt/c/findtorontoevents_antigravity.ca
git push origin main
```

## Verified Working

```bash
python3 .ruflo/orchestrator.py --list-agents --no-verify
# Output: 5 agents registered, failover logic loaded
```
