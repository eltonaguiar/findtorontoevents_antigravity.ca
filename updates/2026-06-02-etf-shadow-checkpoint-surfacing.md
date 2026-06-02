# ETF shadow-checkpoint surfacing

## Findings

- The ETF honesty strip on `/audit` was flattening the promotion ladder into a single `n<100` blocker line.
- The underlying ETF admit artifacts already carried a separate `shadow_checkpoint_ready` state, but the dashboard payload path was dropping it before render.
- That made the operator view less honest: it implied the only missing gate was the final forward sample, when the sleeve can also still be stuck at the intermediate shadow checkpoint.

## What changed

1. `tools/strategy_admissibility_report.py` now preserves `shadow_checkpoint_ready` and `shadow_blockers` when building the verified-lab candidate payload.
2. `alpha_engine/verified_promotion_gate.py` now mirrors those same fields in `verified_edge_status.json` without dropping the file's existing summary contract.
3. `audit_dashboard/dashboard_enhancements.js` now renders `shadow checkpoint ready|pending` beside the ETF best-pilot line.

## Current ETF truth

- Best candidate: `etf_dual_momentum`
- Walk-forward verdict: `PASS`
- Forward status: `0/100` closed, open symbol `XLE`
- Promotion status: not ready
- Shadow checkpoint status: `false`

## Why it matters

This is a reporting honesty fix, not a performance fix. It prevents operators from reading the ETF sleeve as "almost ready except for n<100" when the intermediate checkpoint is still not cleared.

## Next steps

1. Decide whether ETF shadow blockers should be explicitly enumerated in the source admit artifact instead of only carrying a boolean.
2. Keep accumulating ETF pilot evidence until the sleeve has real forward sample, not just lab confidence.
3. Once ETF pilot sample is large enough, re-check whether the promotion gate and the dashboard still agree on every field before any live merge.

## Verification

```bash
python3 -c "import py_compile; py_compile.compile('tools/strategy_admissibility_report.py', doraise=True); py_compile.compile('alpha_engine/verified_promotion_gate.py', doraise=True)"
node -c audit_dashboard/dashboard_enhancements.js
python3 -c "from alpha_engine.verified_promotion_gate import build_edge_status; edge=build_edge_status(); assert edge['best_forward_candidate']['shadow_checkpoint_ready'] is False"
git diff --check
```
