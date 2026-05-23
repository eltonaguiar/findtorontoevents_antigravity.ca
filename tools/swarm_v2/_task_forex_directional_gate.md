# Task: FOREX Directional Gate (LONG bias kill/penalty)

Implement a directional bias quality gate for the FOREX asset class to restore statistical edge (per `reports/forex_mutation_autopsy_20260515.md` and `reports/asset_class_action_items_2026-05-15.md`).

## Problem (from recent May 15-16 MDs)
- FOREX live PF ~0.79-0.81, WR~52% but negative expectancy (avg loss > win).
- Autopsy on n=148 recent resolved picks: LONG = 119 trades, WR 29.4%, PF 0.80 (primary drag, 70% wrong direction).
- SHORT = 29 trades, PF 8.11 (edge exists despite small sample).
- Current gates have no FOREX direction awareness. `BLOCKED_ASSET_STRATEGY_PAIRS` has zero FOREX entries for direction. `quality_gates.py` has symbol/strategy blocks and score floors but no `direction == "Long"` logic for FOREX.
- Result: the class emits mostly losing LONGs; SHORT edge is under-utilized. This is the highest-leverage "mutation" per the three-axis autopsy and 90-day plans (small PR, structure exists).

**References (concrete):**
- `reports/forex_mutation_autopsy_20260515.md` (Axis 2: Direction table, recommendations for score penalty on FOREX LONG).
- `reports/asset_class_action_items_2026-05-15.md` ("Wire a directional gate — autopsy ... BLOCKED_ASSET_STRATEGY_TRIPLES exists but has zero FOREX entries. Highest-leverage move; pure mutation.").
- `reports/asset_class_90day_plan_FOREX_2026-05-15.md` (LONG 80% volume 29.4% WR; recommend directional gate + symbol allowlist).
- `audit_trail/quality_gates.py` (BLOCKED_ASSET_STRATEGY_PAIRS ~1867, passes_active_gate, FOREX score floors at 353-437, existing asset_class blocks).
- `alpha_engine/config.py` (FOREX_SYMBOLS, possible direction bias config).
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

## Where to implement
Primary: `audit_trail/quality_gates.py`

Secondary (wiring): `alpha_engine/scanner.py` or `non_crypto_agent/` if direction is passed to the gate evaluator; `audit_dashboard/data/` for any config.

Add to `BLOCKED_ASSET_STRATEGY_PAIRS` or a new `FOREX_DIRECTIONAL_PENALTY` / `BLOCKED_DIRECTIONS_BY_CLASS` for cleanliness (prefer minimal change: extend existing PAIRS or add a dedicated `passes_forex_directional_gate` called from the main gate function).

## What to build (design spec for swarm workers)
1. New function (or extension):
   ```python
   def passes_forex_directional_gate(pick: dict) -> tuple[bool, str]:
       """
       Returns (passes: bool, reason: str).
       If FOREX and direction == "Long" and not in allowlist or below threshold:
           return False, "FOREX LONG bias drag (autopsy 2026-05-15: 29.4% WR / PF 0.80)"
       """
   ```
   - Gated behind env `FOREX_DIRECTIONAL_GATE_ENABLED` (default "1").
   - Configurable penalty or hard block via `FOREX_LONG_PENALTY` or `FOREX_LONG_BLOCK` in `data_quality_gates.yaml` or config.py.
   - For starters: hard block LONG for FOREX unless the strategy is in a small allowlist of proven SHORT-biased or direction-agnostic (e.g. `["alpha_engine_fast", "signal_validation"]` from autopsy survivors) **or** confidence >= 0.80 + elite_score >= 80.
   - Pure stdlib + existing imports. Match the return convention of neighboring gates (`passes_active_gate` etc.).

2. Wire the check early in the active gate evaluation path (before or inside the function that checks `BLOCKED_ASSET_STRATEGY_PAIRS` and asset_class floors). Update docstrings and the FOREX section comments.

3. Update `BLOCKED_ASSET_STRATEGY_PAIRS` or add a parallel `BLOCKED_FOREX_LONG_STRATEGIES` set (for the worst LONG-only drags identified in autopsy: dxy-reversal-scout, fx_smart_carry... if they are LONG heavy).

4. No behavior change for SHORT or non-FOREX.

## Tests (pytest, add to existing test file or new)
- `test_forex_directional_gate.py` or extend `tests/test_quality_gates.py`.
- Cases:
  - FOREX + Long + low conf -> blocked, reason contains "LONG bias".
  - FOREX + Short -> passes.
  - FOREX + Long + high elite/conf in allowlist -> passes.
  - Env var = "0" -> always passes.
  - Non-FOREX -> unaffected.
- Use the `_verify_n_reproducible.py` pattern if metrics involved.

## Acceptance (for PR + swarm validation)
- After change, a re-run of `compute_per_class_clean_metrics.py` or dashboard regen should show improved FOREX PF/WR on forward window (fewer LONG drags).
- No regression on other classes.
- The gate appears in audit logs / smart_picks_by_asset.FOREX.
- Matches the "mutate-before-kill" protocol in CLAUDE.md / MUTATION_THREE_AXIS.

## Swarm worker guidance (for coding_swarm / research_swarm / hierarchical)
- Researcher: re-read the 3 autopsy axes + 90day FOREX plan + quality_gates.py FOREX sections.
- Code generators: implement the gate function + wiring + tests.
- Test writers + reviewers: ensure the gate is strict on LONG drag but preserves any proven LONG survivors.
- Impact analyzer: quantify expected PF lift (from autopsy: removing LONG drag lifts class WR/PF significantly).
- PR review swarm: generate the PR body citing the exact MDs and autopsy tables.

This is a small, high-impact, pure-mutation PR that directly attacks the "no statistical edge" problem for FOREX (the worst class per all May 2026 reports).

**Owner:** Use `swarm coding tools/swarm_v2/_task_forex_directional_gate.md --agents 4 --strict` (or hierarchical for the full design-to-PR flow).

**Related sibling tasks (create in same batch):**
- _task_forex_symbol_gate.md (BLOCKED_SYMBOLS_BY_CLASS for NZDUSD/EURJPY/USDCHF + boost AUDUSD/AUDJPY)
- _task_equity_vix_regime_gate.md (merge the VIX<22 branch from equity_vix_regime_breakthrough_20260513.md)
- _task_kill_gate_wiring.md (wire evaluate_kill into passes_active_gate)
- _task_forex_real_cot.md (replace price-zscore proxy with real CFTC via cftc_cot_fetcher)

These 4 + the existing penny/futures tasks cover the highest-leverage unimplemented items from the May 15-16 asset class action items and 90-day plans for restoring per-class statistical edge (PF>1.5 / positive expectancy where possible).
