# Strategy harvest + meta-debate round (2026-05-19)

## What

Per-asset-class **top-10 strategy tables** from `pf_registry` + codebase config spec, fed into cloud **Prosecutor/Defense/Judge** meta-debate and local Ollama execute pass.

## Files

- `tools/build_top10_strategies_per_class.py` — regenerates TOP10 MD
- `tools/strategy_harvest_round.py` — build → cloud debate → local execute → synthesis
- `reports/TOP10_STRATEGIES_PER_ASSET_CLASS_2026-05-19.md`
- `reports/STRATEGY_HARVEST_SYNTHESIS_2026-05-19.md`
- `docs/swarm_prompts/META_DEBATE_PER_CLASS_v1.md`
- `docs/swarm_prompts/STRATEGY_HARVEST_EXECUTE_v1.md`
- `tools/model_grill_sequential.py` — `meta_debate`, `strategy_harvest`, `harvest_cloud`, `harvest_local` waves

## Runs

| Phase | Dir | Result |
|-------|-----|--------|
| Cloud debate | `swarm_runs/model-grill/20260519T223418Z` | 3/4 (Qwen timeout) |
| Local execute | `swarm_runs/model-grill/20260519T223720Z` | 3/3 |

## Verify

```powershell
python tools/build_top10_strategies_per_class.py
python tools/strategy_harvest_round.py --phase all
```
