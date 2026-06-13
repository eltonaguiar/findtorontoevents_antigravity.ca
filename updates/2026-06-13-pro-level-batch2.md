# Pro-Level Batch 2 — luxalgo emission, gap-fade replay, tribunal UI

**Date:** 2026-06-13  
**Branch:** `feat/pro-level-batch2-2026-06-13`  
**Includes:** cherry-pick of batch 1 (#586) + new items below

## Added in batch 2

1. **P0-1 luxalgo SHORT fallback** — `june2026_research_candidates.py` emits NEAR/SOL/AVAX SHORT when scanner empty
2. **P1-4 gap-fade replay** — `tools/replay_commodity_gap_fade_intrabar.py`
3. **Probation sleeve bypass** — picks-now gate exempts luxalgo probation sym×dir from CRYPTO class FAIL demotion
4. **Tribunal UI** — collapsible panel on `/audit` loads `strategy_tribunal_latest.json`
5. **Tribunal JSON** — weekly job writes dashboard copy for UI

## Verification

```bash
pytest tests/test_pro_level_intrabar_gate.py tests/test_pro_level_batch2.py -q  # 17 passed
node tools/check_syntax.js audit_dashboard/template.html
python3 tools/replay_commodity_gap_fade_intrabar.py --stdout  # needs DB
```
