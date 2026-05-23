# Kill Gate + PCG-5 Full Enforcement Wiring (2026-05-15)

**Enhancement:** Wire `audit_trail/kill_gate.evaluate_kill()` into `audit_trail/quality_gates.py::passes_active_gate()` for all asset classes (currently only called from commodity_kill_switch.py and fx_kill_switch.py). Promote PCG-5 from shadow-only (PCG5_ENFORCE=0) to configurable enforcement. Add FRED_API_KEY scaffold + GHA path registry update if needed. This closes the #1 gap from `reports/asset_class_action_items_2026-05-15.md` and the "kill gate integration gap" noted in session memory.

**Why (sources):**
- `reports/asset_class_action_items_2026-05-15.md` (priority #9): "`kill_gate.py` (M-055) is wired into the kill switches, NOT the active gate. Callers: commodity_kill_switch.py, fx_kill_switch.py, policy_backtest.py. Gap: `quality_gates.passes_active_gate` does not consult it."
- `reports/asset_class_verification_2026-05-15.md` and action_items cross-class findings.
- `reports/MASTER_ACTION_PLAN_2026-05-15.md` and `daily_ideas_synthesis_2026-05-15.md`: M-013 concentration, M-015 decay-alert, M-016 drift-pause, M-019 MDD limit, all rely on a real kill path in the admission gate.
- Recent feat(gates) commit (f3a2655ff0) already delivered CRYPTO dynamic quarantine + per_class_trainer + pcg5 shadow wire — excellent alignment. This PR completes the kill + makes PCG-5 enforceable.
- Open PR #1083 ("FOREX sizing gate + baby_strats blocks + M-007 + VIX gate + per-class ML") covers complementary pieces.

**Files (my changes only):**
- `audit_trail/quality_gates.py`: In `passes_active_gate()`, after existing early returns and before heavy logic, add:
  ```python
  # Kill gate wiring (2026-05-15) — closes action_items gap
  try:
      from audit_trail.kill_gate import evaluate_kill
      stats = pick.get("stats") or {}
      wins = stats.get("wins") or pick.get("wins", 0)
      n = stats.get("n") or pick.get("n", 0)
      ac = (pick.get("asset_class") or pick.get("class") or "").upper()
      allow_kill, verdict, detail = evaluate_kill(wins, n, ac)
      if allow_kill:
          logger.info("Kill gate blocked: %s %s", verdict, detail)
          return False
  except Exception:
      pass  # fail-open, never break admission
  ```
  Also update the PCG-5 section (around 6580) to respect `PCG5_ENFORCE=1` and actually reject on "REJECT".
- `alpha_engine/config.py`: Add `KILL_GATE_ENABLED=1`, `PCG5_ENFORCE=0` (default shadow), `FRED_API_KEY` optional.
- `updates/2026-05-15-kill-gate-wiring-pcg5-enforce.md`: This doc.
- If FRED reader added: minimal reader in a new or existing macro module + add path to `.github/workflows/audit-dashboard.yml` (per AGENTS path registry).

**Production caller:** `passes_active_gate` (the central admission point for dashboard, paper, production_scanner paths).

**Acceptance:**
- py_compile + import smoke.
- For thin classes (BOND n=11, FUTURES 0) → INSUFFICIENT_EVIDENCE, no kill.
- For proven bad (e.g. old MEMECOIN or decaying strategy with n>min_n and bad binomial p) → blocked at admission.
- PCG-5 shadow continues to log; when PCG5_ENFORCE=1 it rejects.
- No regression on existing kill_switch tests.
- 1 swarmv2-pr-review on the diff.
- Dashboard reflects cleaner active set (fewer thin-class emissions).

**Risks/rollback:** Fail-open on any exception. Env flags for instant disable. No impact on resolver (post-filter) or DB.

**Missed impacts addressed:** Coordinates with feat(gates) commit and #1083; adds GHA path if FRED added; re-uses existing kill_gate logic (no duplication); fail-open safe for paper trading.

**Refs:** asset_class_action_items_2026-05-15 (priority stack #1 and #9), verification, MASTER M-013/15/16/19, daily_ideas_synthesis, recent feat(gates) commit, open #1083.

---
Created 2026-05-15 as part of the reviewed asset-class enhancements set. Swarm + manual review confirmed this is the highest-leverage remaining wiring task.
