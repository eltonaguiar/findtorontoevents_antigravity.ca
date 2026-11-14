# Final findings — scratch-hippodraco (final_v4, 2026-11-14T21:50Z)

This is the **consolidated “next round should be the very final review”** note: it merges what was found in copied `final_v3` bundles, the main checkout’s recent (last ~24h) financial-prediction-related changes, remote git snapshots, and the standing conclusions from prior `final_2026_11_14` / `final_v2` work.

---

## 1) Executive verdict (unchanged in substance, with fresh caution)
- **No statistically valid, costed, OOS-proven “true profitability” is demonstrated today** for any asset class under the project’s own gates (per prior `money_ready_verdict.json` context: no class MONEY_READY; benchmark proof snapshot showed `n_pass_95 == 0`). Treat any live “winners” as **hypotheses only** until Phase A/B regeneration on canonical truth passes gates.
- **Real progress signals exist in code churn (last 24h):** work on **stop-fill realism** (`audit_trail/stop_fill.py`, `tools/stop_fill_replay.py`, tests), **per-class cost gates** (`tools/per_class_cost_gate.py`, tests), **resolver/generator behavior** (`audit_trail/universal_pick_resolver.py`, `audit_trail/dashboard_generator.py`), plus **COT contrarian** backtest artifacts/tests. This aligns with the biggest failure modes called out in `final_v3` themes (TP/SL/bar-close realism, costs/friction, data integrity). But **code changes ≠ validated edge** until backtests are walk-forward/OOS with realistic fills/costs and no lookahead/survivorship leaks.
- **Multiple `final_v3` snapshots exist locally** (main repo, finpredict worktree, hilarious-seer worktree). They overlap but are not byte-identical in structure/content. A “final” review must pick a **single source of truth** for decisions or explicitly reconcile diffs (see §2).

---

## 2) `final_v3` review (copied bundles)
### 2.1 Inventory (from this bundle)
- `01-final_v3-review/main-repo/` (46 files): includes `00_common_themes/{BUGS,DEEP_INVESTIGATION}.md`, `01_plan/*`, `02_subq/COVERAGE_AND_COMPARISON.md`, `03_focus/*`, `05_evidence/*` (stop-fill/cost-gate replays and reports), `childlike-airport/*`, `feat-stop-fill-cost-gate-final-v3/*`, `quant-audit-2026-11-14/*`.
- `01-final_v3-review/finpredict-worktree/` (6 files): minimal `finpredict/{README,PLAN,FOCUS_DECISION,subq/*}`.
- `01-final_v3-review/hilarious-seer-worktree/` (39 files): larger set including `hilarious-seer/*`, `finpredict/*`, `quant-audit-2026-11-14/*`, plus plans/themes/evidence similar to main repo naming.

### 2.2 Themes consistent across copies (high level)
- **Execution realism:** TP/SL/bar-close assumptions and short-side edge cases; `final_v3` evidence artifacts (`stop_fill_*`) and recent `stop_fill*` code changes indicate active hardening. Still requires confirmation that **production resolvers** use the same logic as replay/backtest paths (no “paper vs real” divergence).
- **Costs/friction:** cost gates and general fixes plans appear repeatedly; recent `per_class_cost_gate.py` + tests are promising, but thresholds must map to **real fees/slippage/funding/roll** per class (not placeholders).
- **Data integrity/survivorship/zombies:** recurring in deep investigation themes (matches prior v2/v4: ghosts, expired-in-active confusion, unit issues historically). Must remain paired with “mark not delete” and canonical ledger discipline unless a reviewed migration says otherwise.
- **Mutual funds:** treated as a **focus/subset screen** in some `final_v3` branches (`MUTUAL_FUNDS_SUBSET.md`, `MUTUAL_FUND_SCREEN.md`) and explored in recent untracked MF backtest artifacts in main checkout (`tools/mutual_fund_backtest.py`, `tests/test_mf_walkforward_backtest.py`, many `audit_dashboard/data/mf_backtest_cache/*.csv` untracked). However, prior audits stated **no production MF pipeline / prototype-only in some contexts**. Any MF “profitability” narrative is **speculative until** EOD/NAV pipeline, distributions, expenses, and walk-forward OOS are proven.

### 2.3 Concrete files worth reading first (inside the bundle)
- Main repo: `01-final_v3-review/main-repo/00_common_themes/DEEP_INVESTIGATION.md`, `BUGS.md`, `01_plan/GENERAL_FIXES.md`, `01_plan/ASSET_CLASS_FIXES.md`, `feat-stop-fill-cost-gate-final-v3/*`, evidence under `05_evidence/`.
- Hilarious-seer copy: compare `hilarious-seer/` and `finpredict/` subfolders against main repo for contradictions (different authorship snapshots).
- Finpredict worktree copy: `finpredict/PLAN.md`, `FOCUS_DECISION.md` (minimal) — sanity check alignment with main.

---

## 3) Uncommitted / recently modified (last ~24h) — financial prediction focus
From `02-uncommitted-last24h/FINANCIAL_PREDICTION_RECENT_CHANGES.md` (derived from mtime scan + git status snapshot):

### 3.1 Resolver / dashboard / PnL plumbing (high impact)
- `audit_trail/universal_pick_resolver.py` (2026-11-14 ~21:29Z) — core resolution logic; changes here can change realized PnL classification.
- `audit_trail/dashboard_generator.py` (~21:30Z) — published stats/feeds; must stay consistent with resolver + canonical ledger.
- `tools/live_pnl_tracker.py`, `tools/backfill_missing_exit_prices.py`, `tools/sync_summary_picks_json.py` (noted modified in git status / recent context) — **`summary_picks` math was a known bug class** (WR>100%) in prior audits; any touch requires regression checks against `tools/sync_summary_picks_json.py` fixes already discussed.

### 3.2 Stop-fill realism + cost gates (aligns with final_v3)
- `audit_trail/stop_fill.py`, `tools/stop_fill_replay.py`, tests `tests/test_stop_fill.py`, `tests/test_per_class_cost_gate.py`, `tools/per_class_cost_gate.py`, `tools/hc_gates_python.py` — **active work in the right place** (execution realism + class costs). Treat new results as provisional until replay uses production-parity data paths and OOS samples.

### 3.3 Research artifacts (new/updated)
- `reports/cot_contrarian_2026-11-14.json` + `tools/cot_contrarian_backtest.py` + `tests/test_cot_contrarian_backtest.py` — COT contrarian research. Requires full statistical protocol: hypothesis pre-registration (or explicit exploratory label), OOS, costs, multiple-testing discipline if many variants tested.
- Untracked in main checkout (per captured listing): `alpha_engine/pilot_verified_edges.py`, `alpha_engine/bootstrap_verified_edges.py`, `audit_dashboard/data/bootstrap_verified_edges*.json`, `pilot_verified_edges_shadow.json`, and **many `final_2026_11_14/*` / `final_v2/*` / `quant-audit-*` markdown bundles** plus MF backtest scripts/tests and large `mf_backtest_cache/*.csv` sets. These are **documentation/research artifacts** unless promoted into reviewed code paths.

### 3.4 ML / gatekeeper (watch items)
- `ml_gatekeeper/gatekeeper.py` appears as modified in git status snapshot (main checkout). Prior audits warned: leakage-default flips require **retrain + bundle parity + A/B/test cleanup** before trusting production behavior. Any recent changes must be reviewed against that checklist.

### 3.5 Data freshness snapshots observed
- `audit_dashboard/data/money_ready_verdict.json`: **2026-11-14 18:23Z** (recent)
- `audit_dashboard/data/benchmark_ledger_proof.json`: **2026-11-12 20:19Z** (older). **Do not treat benchmark proof as current** without regeneration aligned to latest truth/cost fixes.

---

## 4) Remote GitHub (git-only)
- `origin` fetched; `origin/main` advanced (`7e5dfea1783..1aa4a769201`) per fetch note. See `03-remote-github/` copies.
- Prior review branches of interest remain referenced in history (e.g. `docs/scratch-hippodraco-audit-2026-11-14`) — verify merge/PR state on GitHub.
- **Recommendation:** before “final” sign-off, run `git fetch origin --prune` and compare `origin/main` against the main checkout for `audit_trail/*`, `tools/per_class_cost_gate.py`, `tools/stop_fill_replay.py`, `ml_gatekeeper/*` to ensure what you audited is what is pushed.

---

## 5) Consolidated “very final review” checklist (actionable)
**A. Canonicalize artifacts**
- [ ] Declare **one** `final_v3` source of truth (recommend: main repo `final_v3/` unless a worktree copy has explicitly superseding signed review) and archive the others under a note.
- [ ] Record commit SHA(s) of `audit_trail/*`, `tools/*cost*`, `tools/*stop_fill*`, `alpha_engine/*resolver*` reviewed.

**B. Data + truth (Phase A/B spirit)**
- [ ] Re-run/verify PnL unit contract, backlog/zombie handling, and `summary_picks` math after recent resolver/dashboard/sync edits.
- [ ] Regenerate `money_ready_verdict.json` and **regenerate `benchmark_ledger_proof.json`** (it is stale relative to Nov 14 verdict timestamp).
- [ ] Ensure freshness surfaced in public payloads matches resolver lanes (no false “fresh”).

**C. Realism (stop-fill + costs)**
- [ ] Confirm `stop_fill_replay.py` / `stop_fill.py` behavior matches production resolution path (same bar semantics, same timezone assumptions).
- [ ] Validate `per_class_cost_gate.py` thresholds against real fee/slippage/funding/roll assumptions per class (document assumptions in code comments or a short MD).
- [ ] Any “edge” from `reports/cot_contrarian_2026-11-14.json` must be labeled **exploratory** until OOS + costs + MT correction + walk-forward are done.

**D. ML / gatekeeper**
- [ ] If `ml_gatekeeper/gatekeeper.py` changed: require retrain/bundle parity, drop-leakage defaults documented, A/B sleeves tested — or revert to last known-good with documented rationale.

**E. Promotion rule**
- [ ] **No size-up** without: canonical ledger rebuilt, costs modeled, OOS/walk-forward, DSR/SPA/PBO with real `nb_trials`, paired benchmark regenerated and interpreted correctly, Charter §4 checklist passed for the specific class.

---

## 6) Bottom line
- The **direction of recent work is correct** (stop-fill, costs, resolver hygiene, COT exploration as data).  
- The **blockers to “true profitability” claims remain**: canonical truth + OOS + MT correction + regenerated benchmarks + honest freshness.  
- Until those are done, treat all current performance narratives as **pre-evidence** and use this bundle’s `RISK_AND_VETO_LIST.md` to prevent destructive or misleading “fixes.”
