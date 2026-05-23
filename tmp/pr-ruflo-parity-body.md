## Summary
Fixes a critical documentation-code mismatch where `RUFLO_SWARM_GUIDE.MD`, slash commands, and `wizard.py` described CLI flags that did not exist in `orchestrator.py`.

## Issues Fixed
1. **Missing `--tier` flag** — Docs described `free|paid|hybrid` tiers but only free worked. Now implemented:
   - `free`: Hermes + OpenRouter free models (default, existing behavior)
   - `paid`: Direct `api_consult.py` calls bypassing Hermes
   - `hybrid`: Paid first, free fallback on failure
2. **Missing `--check-keys` flag** — `swarm-ruflo.md` referenced it; now prints a ✅/❌ table of paid API key availability.
3. **Missing `--swarm all`** — `wizard.py` and guide referenced it; now runs all 4 swarms in one shot.
4. **`wizard.py` hardcoded path** — Same `REPO_ROOT` portability issue as `orchestrator.py`.

## Evidence
See `updates/2026-05-05-ruflo-cli-parity-evidence.md` for full methodology, cross-reference audit, and regression risk assessment.

## Verification
- Python syntax check passes for both modified files.
- `python3 .ruflo/orchestrator.py --check-keys` prints expected key status.
- `python3 .ruflo/orchestrator.py --help` shows new flags.
- Default `--tier free` preserves 100% existing behavior.
