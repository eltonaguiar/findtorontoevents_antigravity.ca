# Shadow lane safety enforcement (2026-06-21)

## What was broken

PR #631 enabled `CRYPTO_RSI5070_SHADOW_ENABLE=1` so the `crypto_rsi5070_us` lead can accrue forward-n. The shadow tagger (`tag_rsi5070_shadow`) and futures/baby monitor taggers set `_monitor_mode=True` and `_sizing_override="zero"`, but **no production code enforced those flags**:

- `position_multiplier` stayed at default 1.0 in `production_scanner.py`
- `get_position_size()` in `position_sizing.py` ignored shadow tags
- `/audit` active-pick filter (`_filter_active_picks_with_gate`) allowed monitor picks through to the published payload
- `passes_smart_gate` had no shadow exclusion (only score penalties for `forward_test_only`)

Comments in `quality_gates.py` said "The sizing layer must respect _sizing_override" — but it was documentation-only.

## What changed

1. **`audit_trail/quality_gates.py`**
   - Added `is_shadow_monitor_pick()`, `enforce_sizing_override()`
   - Ported `tag_rsi5070_shadow` + `_rsi5070_shadow_match` from main (was missing on worktree branch)
   - `passes_smart_gate`: hard-block shadow/monitor picks after active gate

2. **`audit_trail/dashboard_generator.py`**
   - `_filter_active_picks_with_gate`: exclude `_monitor_mode` / `_sizing_override=zero` from published active list

3. **`alpha_engine/production_scanner.py`**
   - Step 6o: call `enforce_sizing_override()` on all active picks before `premium_signals.json` / Discord

4. **`alpha_engine/position_sizing.py`**
   - `get_position_size()`: return 0 USD with `capped_by=shadow_monitor_lane` for shadow picks

5. **`tests/test_shadow_monitor_safety.py`** — 8 tests

## Verification

```bash
python3 -c "import py_compile; py_compile.compile('audit_trail/quality_gates.py', doraise=True)"
python3 -m pytest tests/test_shadow_monitor_safety.py -q
# 8 passed
```

## CFA/FRM value note

The FRM/CFA cheat-sheet review (prior session) found ~70% already implemented. The one actionable gap it surfaced — **TP/SL reachability / honest sizing** — aligns with this fix: shadow lanes must not receive capital or surface as recommendations while accruing measurement-n.
