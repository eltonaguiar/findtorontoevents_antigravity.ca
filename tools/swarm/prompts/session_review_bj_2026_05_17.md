# Session BJ — Swarm Review Request
# Date: 2026-05-17
# Session: BJ (following BI — deepseek APPROVE)

## Context

Session BJ: M-019 Portfolio MDD hard-cap per Charter §7.
All sessions through BI have returned deepseek APPROVE.

## Session BJ Deliverables

### 1. M-019: Portfolio MDD Hard-Cap per Charter §7 (DONE)

Commit: bf8e62fe97

**Problem:** Charter §7 defines Tier 2 MDD ≤ 20% as a hard limit. Gate 4
(profit_lock) in portfolio_gates.py already blocked new picks when winners
were unlocked, but had no enforcement of the maximum portfolio drawdown limit.

**Implementation:**

*portfolio_gates.py:*
- `GATE4_MDD_LIMIT_PCT = 20.0` — constant near existing Gate 4 thresholds
- MDD check at TOP of `gate4_profit_lock()` before existing unlocked-winner logic:
  - Filters positions to `pick.get("account")` only (correct isolation)
  - Computes `avg_unrealized_pnl_pct` across account positions
  - If `avg_unrealized < -20.0%` → returns `{"gate": "4_mdd_hard_cap", "verdict": "REJECT", ...}`
  - Kill-switch: `PORTFOLIO_MDD_GATE_ENABLED=0` (env var, default ON)
  - Fail-open: gate only runs when `all_positions` is non-empty AND matching account positions exist
  - Threshold is strict `<` (exactly -20.0% passes through)

**Design rationale:**
- Placed before profit-lock check so MDD hard-cap takes precedence
- Account-scoped isolation (same pattern as existing Gate 4 account filtering)
- Fail-open on empty positions: no positions = no block (avoids blocking day-1 accounts)
- Shadow mode NOT used: this is a risk gate, not a signal gate; Charter §7 is a hard limit

**Tests (7 passing):**
```
tests/test_m019_portfolio_mdd.py::test_mdd_limit_constant PASSED
tests/test_m019_portfolio_mdd.py::test_mdd_blocks_when_avg_below_threshold PASSED
tests/test_m019_portfolio_mdd.py::test_mdd_approves_when_avg_above_threshold PASSED
tests/test_m019_portfolio_mdd.py::test_mdd_exactly_at_threshold_is_approved PASSED
tests/test_m019_portfolio_mdd.py::test_kill_switch_disables_mdd_gate PASSED
tests/test_m019_portfolio_mdd.py::test_empty_positions_is_fail_open PASSED
tests/test_m019_portfolio_mdd.py::test_mdd_gate_only_considers_matching_account PASSED
7 passed in 0.16s
```

### 2. Current M-item Status

Sessions BC→BJ completed: M-012, M-028, M-033, M-020, M-007(stale), M-004,
M-005(stale), M-019.

Genuine remaining PENDING S-effort items:
- M-015: Decay-alert REDUCE soft-demote framework (M-effort, skip for now)
- M-016: Live-vs-backtest drift circuit breaker (M-effort, skip for now)
- Larger M-items (M-effort, skip for now): M-003, M-009, M-010, M-011

**No remaining autonomous S-effort items in the MASTER_ACTION_PLAN.**

### 3. Pending User Approvals (unchanged from all prior sessions)

1. Block `('COMMODITY', 'cta_replicator')` — 83 losing picks (WR=12%), 0 CT=F picks
2. Raise COMMODITY concentration cap to ≥0.85

## Questions for Swarm

1. **M-019 MDD computation:** The gate uses `avg_unrealized_pnl_pct` across all
   account positions. An alternative is `sum_unrealized_pnl_pct / initial_account_value`.
   Is the avg-across-positions approach appropriate given that `unrealized_pnl_pct` is
   a per-position percentage? Or does this conflate different position sizes?

2. **No shadow mode for MDD gate:** Unlike M-004 and M-028, M-019 defaults to enforce
   (not shadow) because it enforces a Charter-defined hard limit. Is this appropriate?
   Or should we add a shadow-mode default for observability before full enforcement?

3. **Session BJ APPROVE?:** 7/7 tests pass, syntax OK, fail-open preserved,
   MASTER_ACTION_PLAN updated DONE. Is this APPROVE?

4. **No remaining S-effort items:** All S-effort M-items are now DONE or confirmed
   stale. M-effort items (M-015/M-016/M-003/M-009-M-011) require substantial multi-file
   work. What should the autonomous session focus on next?
   - Re-run CI health check and fix any newly broken tests
   - Cross-DB consistency work (M-005 was stale; was there genuine consistency debt?)
   - New S-effort items derived from current dashboard performance numbers
   - EQUITY AMD reassessment (n≥20 trigger)

## Verification

- commit: bf8e62fe97 (feat(M-019): portfolio MDD hard-cap per Charter §7 in Gate 4)
- tests: `python -m pytest tests/test_m019_portfolio_mdd.py -v` → 7 passed
- syntax: `python -m py_compile audit_trail/portfolio_gates.py` → SYNTAX OK
- Prior verdicts: AZ through BI all deepseek APPROVE
