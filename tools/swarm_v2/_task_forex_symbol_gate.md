# Task: FOREX Symbol Gate (kill bad pairs, boost good ones)

Implement a symbol-level quality gate for FOREX to eliminate the worst drags identified in the May 2026 mutation autopsy and restore class-level statistical edge.

## Problem
From `reports/forex_mutation_autopsy_20260515.md` (Axis 1 — Symbol) and `reports/asset_class_action_items_2026-05-15.md`:
- KILL: NZDUSD=X (16.7% WR, PF 0.32), EURJPY=X (PF 0.20), USDCHF=X (0 wins).
- BOOST: AUDUSD=X (PF 3.55), AUDJPY=X (PF 2.45).
- Current: No `BLOCKED_SYMBOLS_BY_CLASS["FOREX"]` or equivalent wired in `quality_gates.py` or scanner. Bad symbols continue to emit and drag the class PF below 1 despite 52% WR headline.

The 90-day FOREX plan and action items explicitly call this out as a "pure mutation" companion to the directional gate.

## Where
- `audit_trail/quality_gates.py` (add `BLOCKED_SYMBOLS_BY_CLASS` or `is_blocked_forex_symbol()` and wire in `passes_active_gate` and smart_picks path).
- Possibly `alpha_engine/config.py` for the allow/block lists (to keep tunable).
- Update `audit_dashboard/data/data_quality_gates.yaml` if it has FOREX section.

## What to build
1. Add data structure (in quality_gates.py or config):
   ```python
   BLOCKED_SYMBOLS_BY_CLASS = {
       "FOREX": {"NZDUSD=X", "EURJPY=X", "USDCHF=X", ...},
       # ...
   }
   BOOSTED_SYMBOLS_BY_CLASS = {
       "FOREX": {"AUDUSD=X", "AUDJPY=X"},
   }
   ```

2. Function:
   ```python
   def passes_forex_symbol_gate(pick: dict) -> tuple[bool, str]:
       sym = pick.get("symbol", "").upper()
       ac = pick.get("asset_class", "").upper()
       if ac == "FOREX":
           if sym in BLOCKED... : return False, f"FOREX symbol {sym} killed per 2026-05-15 autopsy"
           if sym in BOOSTED... : # perhaps bonus score or allow lower bar
               ...
   ```

3. Wire into the main active gate and any pre-emission filters. Make configurable via env `FOREX_SYMBOL_GATE_ENABLED`.

4. Update comments in the FOREX section of the file referencing the autopsy tables.

## Tests
- Hard block on bad symbols, pass on good + majors.
- Case insensitive, =X suffix handling.
- Env disable.
- No impact on other classes.

## Swarm usage
Use `swarm coding tools/swarm_v2/_task_forex_symbol_gate.md` after the directional one (or in hierarchical swarm with researcher pulling the exact tables from the autopsy MD).

This + the directional gate + real COT task will give FOREX a fighting chance at positive expectancy / PF>1 without adding volume.

**Batch with:** _task_forex_directional_gate.md (already created), _task_forex_real_cot.md (create next), and the existing _task_penny_meme_gate.md / _task_futures_classify.md from the same May 15 action items list.
