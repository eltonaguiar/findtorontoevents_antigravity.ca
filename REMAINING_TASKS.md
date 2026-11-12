# REMAINING_TASKS.md
# Swarm Consolidation: Remaining Tasks (Institutional-Grade Transition)

This document tracks the final a few items needed to meet the `CORE_READY` state and complete the production wiring.

## 1. CORE_READY Checklist (Main Branch)
- [x] `requirements.txt` present on main.
- [x] `cli/swarm_picker.py` present on main.
- [x] `core/v2/` modules present on main.
- [x] `tools/swarm/worker_runner.py:9` cleaned (Inception removed).
- [x] `tools/swarm/worker_runner.py:55` cleaned (Inception removed from `API_ENGINES`).

## 2. Wiring Phase (Surgical Integration)
- [ ] **Branch Setup**: Checkout `wiring` branch based on `origin/scrub/inception-mercury-2026-11-12`.
- [ ] **Transport Unification**: Replace all legacy `swarm_run.py` / `api_consult.py` logic with `SWARM_CONSOLIDATED/core/transport.py`.
- [ ] **Worker Import Shift**: Update all workers to use the consolidated package structure.
- [ ] **Call-site Replacements**:
    - `tools/agent_run.sh`
    - `tools/audit_pick_funnel/run_swarm_verdict.py`
    - `tools/research/orchestrator.py`
    - `.ruflo/orchestrator.py`
- [ ] **Cleanup**: Delete `tools/swarm_v2/swarms/core/llm_client.py` after import sweep.

## 3. Verification & Stabilization
- [ ] **Smoke Test**: End-to-end run for each swarm type (v1, v2, Ruflo) via consolidated core.
- [ ] **Regression Audit**: Ensure no "orphan" legacy providers are still being called.
- [ ] **Proxy Validation**: Confirm all production workers hit the LiteLLM proxy consistently.
