# Session BQ — Swarm Review Request
# Date: 2026-05-17
# Session: BQ (following BP — deepseek APPROVE)

## Context

Session BQ: M-010 Phase 2 — wire passes_tier_gate() into tv-paper-trade execution path.
All prior sessions (AZ through BP) returned deepseek APPROVE.

## Session BQ Deliverables

### 1. M-010 Phase 2: Swarm Tier Gate Wiring (DONE)

Commit: 468c844ffc

**Implementation:** Two deliverables:

**A. `tools/swarm/get_eligible_picks.py`** — filter script (new file, 117 lines)
- Reads `audit_dashboard/data/swarm_picks.json` via `load_store()`
- Calls `passes_tier_gate(pick, min_tier=...)` on each pick
- Returns (eligible, blocked) tuple
- Flags: `--min-tier` (default "strong"), `--open-only` (exclude resolved),
  `--out-file`, `--summary`
- Kill-switch: `SWARM_TIER_GATE_ENABLED=0` → all picks pass (inherited from Phase 1)

**B. `.claude/skills/tv-paper-trade/SKILL.md`** — new "Swarm Tier Gate" section added
before the existing "Placing a Trade / Step 1" section.
- Instructs agents: when placing swarm-originated picks, run
  `get_eligible_picks.py --open-only` first
- Documents tier semantics (strong = ≥66%/≥3 models; unanimous = ≥95%/≥3)
- Blocked picks must be logged as `m010_tier_gate_blocked`, not placed

**Tests: 12/12 pass** (`tests/test_m010_phase2_eligible_picks.py`)
- strong/unanimous eligible at strong gate
- moderate/single/control blocked at strong gate
- moderate eligible at moderate gate
- mixed batch 2-eligible 3-blocked
- open_only excludes resolved picks from scope
- open_only all-resolved → empty
- open_only=False includes resolved
- kill-switch passes all picks regardless of tier
- empty input → empty output

## Remaining Genuinely PENDING M-items (unchanged from BP)

- M-003: PCG-5 portfolio gate (complex, requires TV skill + correlation_regime.json)
- M-011: Wave 1.5 truth-layer (PHP peer coordination required)
- M-021: COT lag-corrected re-run (PR #941 lag patch dependency)
- M-036: ETF universe expansion (accumulation lag, no code needed)
- M-039: Cross-commodity spread (L effort — research module + roll handling)

## Questions for Swarm

1. **M-010 Phase 2 design:** The wiring is a filter script + SKILL.md instructions
   rather than a hard code-level call from tv-paper-trade to passes_tier_gate().
   This is because tv-paper-trade is an MCP/skill workflow (not a Python script),
   so the enforcement is instruction-level. Is this an acceptable wiring pattern,
   or should there be an additional code-level guard?

2. **Remaining M-items assessment:** M-003 (PCG-5 portfolio gate stack) is the
   last implementable complex item. M-011/021 are blocked by external deps.
   M-036/039 are L-effort or accumulation lag. Should M-003 be attempted in the
   next session, or should the goal loop judge done=true given all actionable
   S/M items are now exhausted?

3. **Session BQ APPROVE?:** M-010 Phase 2 complete — 12 new tests pass,
   get_eligible_picks.py functional, SKILL.md updated. No regressions. Is this APPROVE?

## Verification

- Commit: 468c844ffc (M-010-p2)
- Full test run: `python -m pytest tests/test_m010_swarm_tier_gate.py tests/test_m010_phase2_eligible_picks.py -v` → 21 passed
- Prior verdicts: AZ through BP all deepseek APPROVE
