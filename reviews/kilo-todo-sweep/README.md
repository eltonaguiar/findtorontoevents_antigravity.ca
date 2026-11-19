KILO TODO SWEEP — REVIEW COPY
=============================
Branch: feat/kilo-todo-sweep-clean (SHA: 07b020459e1)
Pushed: origin/feat/kilo-todo-sweep-clean
Status: Ready for fleet review / mirror by other agents

PURPOSE
-------
This folder contains my (Kilo's) TODO sweep changes isolated under a
review subfolder so the fleet can review each agent's contribution
independently before any merge into main. Other agents are invited to
mirror this structure: reviews/<agent>-<task>/ with their changed files.

FILES (8, no conflicts with main)
---------------------------------
audit_dashboard/data/audit2_pods.json        [NEW]  T12 — audit2 PODS extracted from audit2.js JS literal
audit_dashboard/data/value_screener_picks.json [NEW] T10 — value screener methodology + empty picks array
reports/backtesting_methodology_audit_2026-06-02.md [NEW] T13 — stub for missing citation target
updates/2026-11-19-audit3-todo-sweep.md       [NEW] Full documentation of all 16 TODO items closed
audit_dashboard/audit3.html                    [MOD] T7 — G8 renders "not evaluated" when selection_alpha unavailable
audit_trail/dashboard_generator.py             [MOD] T5 — pnl_methodology_note reconciliation (3 conflicting PnL methods)
reports/TACTICAL_ROTATION_EDGE_2026-07-04.md   [MOD] T17 — claim retracted: NOT REPRODUCED at stated Sharpe 0.88 / MaxDD −19%
reports/hypothesis_registry.json               [MOD] T15/T16 — H-142 risk-parity + H-143 sector-rotation pods pre-registered

TODO ITEMS CLOSED (16 of 16)
----------------------------
T4 volume_ratio_at_entry persistence        → alpha_engine/forward_observations_ingest.py (+ forward_validator.py) — NOT IN THIS FOLDER (main owns alpha_engine/*)
T5 PnL methodology reconciliation           → audit_trail/dashboard_generator.py
T6 required_n on class rows                 → alpha_engine/audit3_tribunal.py — NOT IN THIS FOLDER (main owns alpha_engine/*)
T7 G8 "not evaluated" rendering             → audit_dashboard/audit3.html
T8 catch-all reasons for non-promotions     → alpha_engine/audit3_tribunal.py — NOT IN THIS FOLDER (main owns alpha_engine/*)
T9 FORCE_CLOSED TP/SL/time buckets          → alpha_engine/audit3_tribunal.py — NOT IN THIS FOLDER (main owns alpha_engine/*)
T10 value_screener_picks.json               → audit_dashboard/data/value_screener_picks.json
T11 scored_share capped at 100%             → alpha_engine/audit3_tribunal.py — NOT IN THIS FOLDER (main owns alpha_engine/*)
T12 audit2_pods.json                        → audit_dashboard/data/audit2_pods.json
T13 backtesting_methodology stub            → reports/backtesting_methodology_audit_2026-06-02.md
T15 H-142 risk-parity pod                   → reports/hypothesis_registry.json
T16 H-143 sector-rotation pod               → reports/hypothesis_registry.json
T17 TACTICAL_ROTATION_EDGE retraction       → reports/TACTICAL_ROTATION_EDGE_2026-07-04.md
T19 ETF slippage derivation                 → reports/TAA_SETTLE_2026-11-19.md (not in this folder — report text)
T20 4x cost gate (MATERIALITY_COST_FRACTION)→ alpha_engine/audit3_tribunal.py — NOT IN THIS FOLDER (main owns alpha_engine/*)
T21 CRYPTO/COMMODITY blocked at ingestion   → alpha_engine/forward_observations_ingest.py — NOT IN THIS FOLDER (main owns alpha_engine/*)

NOTES
-----
- Files marked "NOT IN THIS FOLDER" touch alpha_engine/* which main owns per the fleet file map (docs/COLLABORATION_PROTOCOL_2026-11-19.md). Those live in PR #965 (feat/audit3-p0-p1-correctness) pending fleet merge resolution.
- 200 tests pass on the source branch (1 xfailed known bug, 1 xpassed known bug — pre-existing).
- No force-push without operator go.

MERGING
-------
1. Review each file in this folder against main.
2. If satisfied, merge feat/kilo-todo-sweep-clean into main (clean cherry-pick, no conflicts).
3. Other agents mirror: reviews/<agent>-<task>/ on their own branches, then merge.

COMS
----
Reply to: inbox/gx10-c9b9/findtorontoevents_antigravity-ca/kilo
