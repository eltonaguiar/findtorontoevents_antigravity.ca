# Action Items Remaining — 2026-04-22

**Context sources:**
- `findings.txt` — 2,495-line peer-session transcript (paper trading + placeholder diagnosis)
- `agent notes.txt` — 20,159-line peer-session log (ship-week test run, blocker list)
- `reports/INTEGRATIONS_BENCHMARK_2026_04_22.md` — live findings on 5,135 closed picks
- `reports/PLAN_BLOCKER2_PLUS_BENCHMARK_2026_04_22.md` + `_ADDENDUM_2026_04_22.md`
- Current branch: `fix/reject-exempt-safety-gate` (pushed); ship-week work on `feat/ship-week-integrations-2026-04-21`
- Active paper positions on `HIGHFWWRABV55_SCOREABOVE50_V4`: DOTUSDT Short, HYPEUSDT Long (both with TP/SL)

---

## P0 — Live / time-sensitive

### A1. Monitor the two paper positions until close
- **What:** DOTUSDT Short @ 1.292 (TP 1.240, SL 1.318) and HYPEUSDT Long @ 40.936 (TP 42.570, SL 40.120) on `HIGHFWWRABV55_SCOREABOVE50_V4`.
- **Why:** These are the first trades on this account post-Blocker-2 diagnosis. Their outcomes back-validate the HYPEUSDT (n=647, fwd_wr=99.8%) and DOTUSDT (n=34, fwd_wr=67.6%) strategy stats — and will start earning real `forward_wr` values on these specific clones.
- **Next action:** No edit required; TP/SL are wired. Check via `mcp__tradingview-desktop__tv_health_check` before any session-close. When they close, log outcomes to `project_paper_trades_2026_04_22.md` memory.
- **Owner:** whoever has TV open + CDP live.

### A2. Decide what to do with the clone-seed fix
- **What:** My commit `0945e18d52` on `fix/reject-exempt-safety-gate` zeroes `forward_trades` / `forward_wr` / `forward_validated` / `elite_score` / `elite_grade` at seed time in `copy_trader_intel/strategy_clone_generator.py:492-498`. The local working copy was reverted (intentional per system reminder) — so the commit on the branch is currently ahead of the working copy.
- **Why it matters:** If the branch merges, the next clone-gen run will seed zeros. If the user has changed approach (e.g., wants to keep marketing WR visible but tag it differently), the commit should be amended or reverted before merge.
- **Next action:** Confirm with user which way to go:
  - (i) merge `fix/reject-exempt-safety-gate` as-is (my commit + peer's `EXEMPT_FROM_SAFETY_GATES` hard-reject),
  - (ii) keep the commit but add a separate UI-layer fix that shows clone marketing WR with an "UNVALIDATED" badge,
  - (iii) drop my commit and take a different approach (add a `clone_seed_stats: true` flag, filter out in UI).
- **Files:** `copy_trader_intel/strategy_clone_generator.py:492-498`, branch `fix/reject-exempt-safety-gate`.

---

## P1 — This week

### B1. Split `feat/ship-week-integrations-2026-04-21` into reviewable PRs
- **What:** Per `agent notes.txt`, that branch has 15 commits from 5 different agents — too big for one review. 14 new sidecar modules (codebuff 4 + me 11 + nuedxoi6 infra) coexist cleanly (1198 tests pass) but need to land as discrete, reviewable units.
- **Suggested split:**
  - PR-A: `alpha_engine/{tsfresh,interpret,skforecast,flaml,pyod,bt,skfolio,feature_engine,imbalanced_learn}_integration.py` + `purged_cv_core.py` + `mlfinlab_integration.py` + facade at `alpha_engine/integrations/` + 11 test files + `tools/demo_next_phase_integrations.py` + `NEXT_PHASE_INTEGRATION_STATUS.md` (my 11-module kit).
  - PR-B: codebuff's 4 rejected-but-kept modules (whatever those are).
  - PR-C: nuedxoi6's infra (Docker Compose + CI/CD + feature drift auto-retraining, per their peer summary).
  - PR-D: the `enhanced_edge_detector.py` bridge fix (was re-emitted with `IndentationError` at line 126 per agent notes — needs fix or delete).
- **Gating:** PR #301 (resolver fix) must merge first per `agent notes.txt` blocker list.

### B2. Unblock / sequence PR #301 (resolver fix)
- **What:** `agent notes.txt` lists "PR #301 (resolver fix) must merge before any metric-consuming PR" as a BLOCKER.
- **Why:** Any PR that consumes strategy metrics (including the ship-week kit's `purged_cv_core` + `interpret` work) will read stale resolver output until #301 merges.
- **Next action:** Check `gh pr view 301`, identify what's holding it, unblock.

### B3. Reconcile `alpha_engine/finrl_agent.py` with `rl_agent/DEPRECATED.md`
- **What:** `agent notes.txt` flags a policy collision — FinRL integration was added while an `rl_agent/DEPRECATED.md` file says RL-agent work is deprecated.
- **Why:** Conflicting signals to future contributors. Either un-deprecate, or remove the FinRL addition, or clarify the scope distinction in a single authoritative doc.
- **Owner hint:** whoever authored the `rl_agent/DEPRECATED.md` file originally.

### B4. Fix the underlying Blocker-2 root cause not addressed by A2
- **What:** Beyond the seed-time placeholder fix, the audit UI still shows `clone_hl_copy_*` picks with elite_grade badges based on *any* source's `elite_score` field. If A2 lands, new clones will show "UNGRADED" but existing ledger rows still have "A"/"B"/"C" from the prior marketing-WR seeding.
- **Next action:** Write a one-shot migration script that zeros `elite_score`/`elite_grade` on existing rows where `source_system == 'copy_trader_intel'` AND `strat_fwd_trades == 0`. Don't touch rows that have earned real stats.
- **Files:** `alpha_engine/data/active_picks.json`, `alpha_engine/data/closed_picks.json`. Take a backup first.

### B5. Benchmark follow-through: address the three pathological findings
From `reports/INTEGRATIONS_BENCHMARK_2026_04_22.md`:
1. **`confidence` correlates −0.087 with wins.** Either invert the sign at feature-derivation time (short-term fix) or rebuild the confidence estimator with purged-K-Fold CV on closed trades (proper fix). Ticket: `project_confidence_rebuild_2026_04_22.md`.
2. **EBM out-of-sample acc 0.6735 < 0.7028 majority-class baseline.** Current feature set doesn't separate wins. Need: triple-barrier labels, regime-aware features, or both. Start with adding `market_regime` (HMM 7-state) as a feature and re-run the benchmark.
3. **97.3% of closed volume is `quan_engine`.** Add a portfolio-level constraint at execution: no single `source_system` exceeds 60% of open entries. Enforce at the execution gate, not at generation (per `feedback_gate_at_execution_not_generation.md`).

---

## P2 — Next week

### C1. Restore the 11 integration wrapper modules (or accept they're only on the ship-week branch)
- **What:** The 11 `alpha_engine/*_integration.py` modules + `alpha_engine/integrations/` facade + `tools/demo_next_phase_integrations.py` + `NEXT_PHASE_INTEGRATION_STATUS.md` exist on `feat/ship-week-integrations-2026-04-21` but were wiped from the local working copy by branch-switch + stash race mid-session. Only `.pyc` bytecode remains on main's working tree.
- **Decision to make:** Either (i) merge PR-A from B1 to bring them back to main, or (ii) accept that they live only on the feature branch until that's merged.

### C2. Address the `enhanced_edge_detector.py` IndentationError
- **What:** Per `agent notes.txt`, "enhanced_edge_detector.py now exists but bridge is newly broken with IndentationError at line 126." Roocode/Mercury scratch re-emitted with fabricated claims per the same doc.
- **Next action:** Either fix the file or delete it if it was Mercury-generated vaporware. Check: `git log --oneline alpha_engine/enhanced_edge_detector.py` to see who wrote it and when.

### C3. CI graceful-fallback smoke test
- **What:** `agent notes.txt` lists a MEDIUM todo: CI should prove the 11-module kit still imports cleanly when each optional library (tsfresh, interpret, etc.) is absent.
- **Next action:** Add a GitHub Actions job that runs `py -c "from alpha_engine.integrations import available_integrations; print(available_integrations())"` in a minimal-install container.

### C4. `macro_data_pipeline` plumbing
- **What:** `ml_ranker.FEATURES` was frozen in Phase 20; macro features are unwired.
- **Next action:** Check if `alpha_engine/data_providers/macro_data_pipeline.py` is complete (it's untracked in current git status). If so, thread it into the frozen FEATURES list through a feature-flag gate.

### C5. Market-making contract audit
- **What:** `agent notes.txt` notes: "Market-making contract (maker fills ≠ directional picks)." Maker fills shouldn't be treated as directional picks for WR computation.
- **Next action:** Find where maker fills flow into pick outcomes; tag them `side_effect: maker_fill` and exclude from WR calcs.

---

## P3 — Defer

### D1. Delete Mercury/Roocode scratch
- **What:** "Active sabotage: IndentationError + fabricated claims re-emitted" per `agent notes.txt`. Low priority but toxic.
- **Next action:** Identify all files authored by Mercury/Roocode scratch, audit each, delete or document.

### D2. Per-module READMEs for the 11 integrations
- Thin docs per wrapper module. Lower priority than wiring them into callers.

### D3. Lint pass

### D4. Audit nuedxoi6's 2,608-line infra docs (docs-only vs real infra?)

---

## State snapshot

**On `fix/reject-exempt-safety-gate` (pushed to origin):**
- `0945e18d52` — my clone-seed placeholder fix (reverted in local working copy per system reminder; commit still on remote)
- `c8e83a4259` — peer's `EXEMPT_FROM_SAFETY_GATES` hard-reject

**On `main` (pushed to origin):**
- `reports/INTEGRATIONS_BENCHMARK_2026_04_22.md`
- `reports/PLAN_BLOCKER2_PLUS_BENCHMARK_2026_04_22.md`

**On `feat/ship-week-integrations-2026-04-21` (pushed to origin):**
- 11 integration wrapper modules + facade + tests + demo + NEXT_PHASE_INTEGRATION_STATUS.md + 4 codebuff modules + nuedxoi6 infra (all tested green: 1198 pass / 4 skipped / 0 failures)

**Active paper trades on `HIGHFWWRABV55_SCOREABOVE50_V4`:**
- DOTUSDT Short 151.90 @ 1.292 (TP 1.240 / SL 1.318)
- HYPEUSDT Long 1.0 @ 40.936 (TP 42.570 / SL 40.120)

**Peers last seen active (per `findings.txt` list_peers):**
- `ro09ivi8` — infra audit, action-1 diff proposal awaiting auth
- `aehct8hx` — earnings catalyst filter prototype (`alpha_engine/catalyst_filter.py`)
- `nuedxoi6` — Docker Compose + CI/CD + feature-drift retraining
- `vzu7oh3k` — me (this session's earlier state, now idle post-benchmark)
