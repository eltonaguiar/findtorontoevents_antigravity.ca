# 2026-05-17 FOREX Directional Gate + swarm_v2 Designs for Asset Class Statistical Edge

**Date:** 2026-05-17  
**Problem:** Persistent struggle to achieve statistical edge (PF > 1.5 / positive expectancy / Tier-2 floor) per asset class, especially FOREX (live PF ~0.79-0.81 despite 52% WR; negative expectancy because LONGs are 70% wrong per recent autopsy).  
**Root cause (from review of past week MDs):** Many high-leverage "pure mutation" action items from `reports/asset_class_action_items_2026-05-15.md`, `reports/asset_class_90day_plan_FOREX_2026-05-15.md`, `reports/forex_mutation_autopsy_20260515.md` (May 15-16) remain unimplemented:
  - No FOREX directional gate (LONG 29.4% WR / PF 0.80 drag vs SHORT PF 8.11 edge).
  - No symbol-level gate for bad pairs (NZDUSD PF0.32, EURJPY 0.20, USDCHF 0 wins).
  - EQUITY VIX-regime gate branch exists but unmerged (biggest single PF lever per equity_vix_regime_breakthrough_20260513.md).
  - `kill_gate.evaluate_kill()` not wired into `passes_active_gate`.
  - COT proxy still price-zscore, not real CFTC data.
  - BOND elite floor too high (n=11 blocker).
  - Several of these had partial `_task_*.md` in `tools/swarm_v2/` (futures_classify, penny_meme_gate) but the FOREX and VIX ones did not.

**Review performed:** Read `memory/2026-05-16.md`, `reports/asset_class_action_items_2026-05-15.md` (full), `reports/asset_class_90day_plan_FOREX_2026-05-15.md`, `reports/forex_mutation_autopsy_20260515.md`, related deep_dive and 90day plans for other classes (May 12-16 files). Confirmed the scoreboard (FOREX stressed, sizing_allowed=false) and the exact "Top action items" lists.

**Design using tools/swarm_v2:**  
Created two new task definition files in the existing swarm_v2 framework (which already had the pattern for action items via `_task_penny_meme_gate.md` and `_task_futures_classify.md`, plus full research/coding/pr_review/hierarchical engines, workers, memory, CLI):
- `tools/swarm_v2/_task_forex_directional_gate.md` — full spec for the gate (env-gated, elite/conf bar, references exact autopsy tables, swarm worker guidance for researcher + coding_swarm + pr_review_swarm).
- `tools/swarm_v2/_task_forex_symbol_gate.md` — companion for symbol allow/block list (BOOST AUDUSD/AUDJPY, KILL the three worst).

These task files are the "design" consumable by `swarm coding ...` or `swarm hierarchical ...` (the framework's research_swarm + coding_swarm + test_writer will produce the code, tests, impact analysis, and PR body when LLM keys are available).

**Implementation (the fix itself):**
- Added the FOREX directional gate logic directly in `audit_trail/quality_gates.py` inside `passes_active_gate` (right after the M-049 safety gate, fail-open, env `FOREX_DIRECTIONAL_GATE_ENABLED` default ON).
- Logic: for FOREX + Long (or "buy"), require elite_score >=75 **or** confidence >=0.75; otherwise reject with clear log. Matches the "highest-leverage move" called for in the May 15 action items.
- No behavior change for SHORT or other classes.
- This directly attacks the LONG drag that is keeping the class PF <1.

**Verification / Test:**
- Module imports cleanly (`python3 -c "from audit_trail.quality_gates import passes_active_gate; print('ok')" `).
- Manual unit test via Python REPL: constructed FOREX Long pick with elite=60 → rejected; elite=80 → passed; Short → passed; non-FOREX → unaffected.
- No other files touched in this minimal change. The gate is now live for the next scanner / active_picks run.
- (Full swarm run would also generate dedicated pytest + backtest delta on FOREX picks.)

**PR preparation (as requested):**
- Branch: `feature/forex-directional-edge-swarm-v2-2026-05-17`
- Commits include:
  1. The two new `_task_*.md` design files (how future edge items will be tackled via swarm_v2).
  2. The gate implementation in quality_gates.py.
  3. This updates/ MD (per AGENTS.md "every code fix MUST be documented in a .MD").
- PR title/body will cite the exact autopsy tables, action items MD, and "implements the top FOREX mutation from the May 15-16 statistical edge review using the swarm_v2 design pattern".
- Ready for `git push` + PR creation once user approves (only own changes; no forbidden scripts).

**Impact on statistical edge per asset class:**
- Immediate reduction in FOREX LONG volume (the 119-trade drag in the autopsy slice).
- Expected lift in class PF/WR/expectancy on forward window (SHORT edge preserved and amplified).
- Companion symbol gate (in the task design) will further clean the universe.
- Demonstrates the swarm_v2 workflow for the entire list of unimplemented items in the recent 90-day plans and action_items MD (VIX for EQUITY, kill_gate wiring, real COT, BOND floor, etc. can follow the same _task_ + swarm coding pattern).

**Next (per the designs):**
- Run `swarm coding tools/swarm_v2/_task_forex_directional_gate.md` (and the symbol one) when LLM backends are configured — it will produce the full tested implementation + PR artifacts.
- Create the remaining sibling tasks for VIX-regime, kill_gate wiring, real COT.
- Re-measure FOREX asset_class_health after a few days of the gate being live.
- Merge the EQUITY VIX branch (another high-impact item from the same May 15 review).

This directly addresses the user's observation that "we are struggling to find a statistical edge per asset class" by turning the recent documented action items into actionable swarm_v2 designs + concrete code.

**Files changed (own only):**
- tools/swarm_v2/_task_forex_directional_gate.md (new design)
- tools/swarm_v2/_task_forex_symbol_gate.md (new design)
- audit_trail/quality_gates.py (implementation)
- updates/2026-05-17-forex-directional-gate-and-swarm-v2-design.md (this doc)

All per AGENTS.md (reviewed recent MDs, documented, no push, used existing swarm_v2 framework for the design).

The statistical edge work for the other classes (EQUITY VIX, BOND n, etc.) is now queued in the same swarm_v2 task format.