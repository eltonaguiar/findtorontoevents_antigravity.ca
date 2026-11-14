# Local Uncommitted Files — Last 24 Hours (Financial Prediction)

**Date:** 2026-11-14T21:50Z  
**Worktree:** finpredict-v4  
**Scope:** Uncommitted files modified/created in last 24 hours related to financial prediction

---

## 1. finpredict-v4 Worktree (Current)

### New Files (Untracked)

| File | Size | Purpose | Status |
|------|------|---------|--------|
| `alpha_engine/statistical_scoring_framework.py` | ~580 lines | Statistical scoring framework for pilot validation | **Uncommitted** — needs review |
| `research/PROFITABLE_SCORING_FRAMEWORK.md` | ~200 lines | Research doc on scoring framework design | **Uncommitted** — needs review |
| `research/tradingview_contest_winner_research_2026-11-14.md` | ~300 lines | TradingView contest winner strategy research | **Uncommitted** — needs review |
| `final_2026_11_14/finpredict-v4/01_local_peers/PEER_SUMMARIES.md` | ~250 lines | Peer summaries from final_2026_11_14 round | **Uncommitted** — archived |
| `final_2026_11_14/finpredict-v4/02_remote_github/REMOTE_ACTIVITY.md` | ~200 lines | Remote GitHub activity review | **Uncommitted** — archived |
| `final_2026_11_14/finpredict-v4/03_recent_commits/COMMIT_LOG.md` | ~150 lines | Recent commits detail | **Uncommitted** — archived |
| `final_2026_11_14/finpredict-v4/04_modified_files/FILE_CHANGES.md` | ~200 lines | File change heatmap | **Uncommitted** — archived |
| `final_2026_11_14/finpredict-v4/05_consolidated_findings/CONSOLIDATED_REPORT.md` | ~400 lines | Consolidated findings | **Uncommitted** — archived |
| `final_v2/finpredict-v4/01_peer_deep_dive/MISSED_INSIGHTS_AND_CORRECTIONS.md` | ~350 lines | Peer deep dive with corrections | **Uncommitted** — archived |
| `final_v2/finpredict-v4/02_per_asset_class_pathways/PATHWAYS_TO_PROFITABILITY.md` | ~500 lines | Per-asset-class pathways | **Uncommitted** — archived |
| `final_v2/finpredict-v4/03_profitability_framework/STATISTICAL_GATES_AND_FRAMEWORK.md` | ~450 lines | Statistical gates framework | **Uncommitted** — archived |
| `final_v2/finpredict-v4/04_final_recommendations/PRIORITIZED_ACTION_PLAN.md` | ~550 lines | Prioritized action plan | **Uncommitted** — archived |
| `final_v2/finpredict-v4/05_risk_controls_and_governance/RISK_CONTROLS_AND_GOVERNANCE.md` | ~400 lines | Risk controls and governance | **Uncommitted** — archived |

### Code Files Requiring Attention

#### `alpha_engine/statistical_scoring_framework.py`
- **Status:** Uncommitted, untested
- **Purpose:** Bootstrap validation, random-entry null model, cost-inclusive expectancy
- **Risk:** May duplicate `tools/per_class_cost_gate.py` (shipped by quant-audit in final_v3)
- **Recommendation:** Compare with quant-audit's `tools/per_class_cost_gate.py` + `tools/stop_fill_replay.py` before committing. If redundant, merge or discard.

#### `research/PROFITABLE_SCORING_FRAMEWORK.md`
- **Status:** Uncommitted
- **Purpose:** Research notes on scoring framework
- **Risk:** May overlap with final_v3's `03_profitability_framework/STATISTICAL_GATES_AND_FRAMEWORK.md`
- **Recommendation:** Merge into final_v4 synthesis; no need for separate file.

#### `research/tradingview_contest_winner_research_2026-11-14.md`
- **Status:** Uncommitted
- **Purpose:** TradingView winner archetypes (High-WR Grinders vs High-R:R Snipers)
- **Value:** Unique insight not present in any peer work
- **Recommendation:** Keep and reference in final_v4 risk controls document.

---

## 2. Other Worktrees (Uncommitted Financial Files)

### hilarious-seer (Last 24h)

| File | Status | Purpose |
|------|--------|---------|
| `tools/stop_fill_replay.py` | **Committed to final_v3** | Stop fill replay harness |
| `tools/per_class_cost_gate.py` | **Committed to final_v3** | Per-class 3× cost gate |
| `tools/hc_gates_python.py` | **Committed to final_v3** | Gate wiring |
| `tools/cot_contrarian_backtest.py` | **Committed to final_v3** | COT contrarian test |
| `tests/test_stop_fill.py` | **Committed to final_v3** | 20 unit tests |
| `tests/test_per_class_cost_gate.py` | **Committed to final_v3** | 18 unit tests |
| `tests/test_cot_contrarian_backtest.py` | **Committed to final_v3** | COT tests |
| `updates/2026-11-14-stop-fill-cost-gate-cot.md` | **Committed to final_v3** | Fix documentation |
| `final_v3/hilarious-seer/` | **Committed to main** | Peer final_v3 deliverable |

**Note:** All hilarious-seer code was committed to `origin/main` via `feat/stop-fill-cost-gate-final-v3` branch. No uncommitted code remains.

### quant-audit-2026-11-14 (Last 24h)

| File | Status | Purpose |
|------|--------|---------|
| `audit_trail/stop_fill.py` | **Committed to main** | Gap-aware fill module |
| `audit_trail/universal_pick_resolver.py` | **Committed to main** | Resolver gap-aware fill flag |
| `tools/per_class_cost_gate.py` | **Committed to main** | Cost gate |
| `tools/hc_gates_python.py` | **Committed to main** | Gate wiring |
| `tools/stop_fill_replay.py` | **Committed to main** | Replay harness |
| `tools/cot_contrarian_backtest.py` | **Committed to main** | COT test |
| `final_v3/quant-audit-2026-11-14/` | **Committed to main** | Peer final_v3 deliverable |

**Note:** All quant-audit code was committed. The `feat/stop-fill-cost-gate-final-v3` branch was pushed to origin.

---

## 3. Files Modified in Main Repo (Last 24h, Financial Prediction)

From `git log` and file timestamps:

| File | Change | Commit | Purpose |
|------|--------|--------|---------|
| `audit_trail/universal_pick_resolver.py` | +57 lines | `feat/stop-fill-cost-gate-final-v3` | Gap-aware fill pricing |
| `tools/hc_gates_python.py` | +33 lines | `feat/stop-fill-cost-gate-final-v3` | Per-class cost gate wiring |
| `audit_trail/dashboard_generator.py` | +12 lines | `feat/stop-fill-cost-gate-final-v3` | After-cost net fallback |
| `tools/per_class_cost_gate.py` | New | `feat/stop-fill-cost-gate-final-v3` | Cost gate builder |
| `tools/stop_fill_replay.py` | New | `feat/stop-fill-cost-gate-final-v3` | Replay harness |
| `updates/2026-11-14-stop-fill-cost-gate-cot.md` | New | `feat/stop-fill-cost-gate-final-v3` | Documentation |
| `final_v3/` | New directory | Multiple commits | Peer final_v3 deliverables |

---

## 4. Risk Assessment: Uncommitted Code

| File | Risk | Action |
|------|------|--------|
| `alpha_engine/statistical_scoring_framework.py` | Medium — may duplicate quant-audit work | Compare with `tools/per_class_cost_gate.py`; merge or discard |
| `research/PROFITABLE_SCORING_FRAMEWORK.md` | Low — research notes | Merge into final_v4 synthesis |
| `research/tradingview_contest_winner_research_2026-11-14.md` | Low — unique insight | Keep; reference in risk controls |
| `final_2026_11_14/` | None — archived round | Can be deleted or kept for history |
| `final_v2/` | None — archived round | Can be deleted or kept for history |

---

## 5. Recommendation

1. **Do NOT commit `statistical_scoring_framework.py` without comparing** to quant-audit's `tools/per_class_cost_gate.py` + `tools/stop_fill_replay.py`. If it duplicates functionality, discard it.
2. **Merge research docs** into final_v4 synthesis rather than keeping as separate uncommitted files.
3. **Clean up archived rounds** (`final_2026_11_14/`, `final_v2/`) after final_v4 is complete — they are no longer needed.
4. **All peer code is committed.** The only uncommitted financial-prediction code is in finpredict-v4's worktree.

---

*Reviewed by: finpredict-v4*  
*Date: 2026-11-14T21:50Z*
