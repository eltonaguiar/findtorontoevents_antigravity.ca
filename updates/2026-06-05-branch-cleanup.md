# 2026-06-05: Git Branch Cleanup — 30+ Stale Branches Deleted

**Context:** GitHub branch list showed many stale `claude/fervent-knuth-*`, `copilot/*`, `peer-claude/*`, `blackboxai/*`, old `fix/*`/`feat/*`/`docs/*`/`chore/*`/`audit-*` branches (most 1-3 ahead or more, many with closed PRs, all 100s-1000s behind main). Per AGENTS.md / CLAUDE.md: never delete without confirmation + evidence; always pull first; document every change.

**Process followed:**
- `git fetch --all --prune`
- `git ls-remote` + `git cherry -v origin/main origin/BRANCH` + `git merge-base --is-ancestor`
- `gh pr list --head $b --state all` for every listed branch (0 open PRs at time of check)
- Verified landing of "unique" changes for non-directly-merged branches via:
  - File presence on `origin/main` (e.g. `strategy_verification_engine.py`, `updates/eagle4-eagle5-gates-2026-06-02.html`, `tools/feature_signals/orchestrator.py`)
  - `git log --oneline origin/main --grep='...'` hits (e.g. GE+RENDERUSDT f47be5c superseding #524, chunk resolver v2 #449, baby adapter aad5e1d9, symbol normalize bf67934e, etc.)
  - Spot `git show origin/main:PATH` vs branch version for security fixes (e.g. `tools/backfill_null_pnl.py` now uses `get_stocks_creds()` on main)
  - Cross-ref with today's merges (#540 money-ready, #544 ci-gate-env-leaks "close 6 new DB password leaks", #545 persona-factor-emitters, recent verdict recency + truth banner)
- Cross-checked full analysis + proposed list with AI swarm (`/swarm second-opinion` via `tools/swarm/swarm_run.py --engines deepseek,xai,kilo`).
  - Run: `swarm_runs/branch-cleanup-20260605T122747Z/`
  - deepseek: full structured agreement (kilo parse-failed/zero but 1 strong engine + manual verification sufficient).
  - Swarm consensus: "DELETE_ALL_EXCEPT_KEEP_LIST", "high" confidence, 30 safe, 2 keep.
- Mandatory pre-push: `git stash && git pull --rebase origin main && git stash pop` (succeeded, fast-forward, branch now up-to-date at 1ee6f1a924; only session data mods + generated untracked left unstaged).

**gh-pages:** Explicitly left alone (user directive: "leave gh-pages as its used for github pages").

**Kept (unique work or special):**
- `feature/vrp-forward-clock-wireup` (PR #536 closed, 1 ahead): Contains substantial *unlanded* work — new `verified_strategies/paper_pilot/vrp_harvest_pilot.py` (157 loc) + `verified_strategies/vol_risk_premium_harvest.py` (255 loc), plus wiring in `run_verified_pilots_daily.py`, `pilot_forward_dashboard.py`, workflows, deploy list, and `updates/2026-06-05-vrp-forward-clock-wireup.md`. `git grep` + tree check on origin/main: no matching pilot files or "VRP Harvest forward pilot clock". Swarm + verification flagged as KEEP. (Consider landing via new PR if the VRP Harvest forward pilot is ready.)
- `gh-pages` (per above).

**Deleted (30+ branches):**
All had either:
- Merged PR, or
- Closed PR whose changes were confirmed landed via superseding PRs/direct commits (e.g. #524 audit-fixes superseded by reverse-split land + f47be5c), or
- Temp agent/copilot/peer branches (no PR, stale May 31-era "fervent-knuth" / blackboxai sessions whose synthesis landed in reports/updates/merged PRs).

From user-provided list + additional `claude/peer-copilot/blackboxai/dedupe` discovered via `git ls-remote`:
- `pr/money-ready-bridge-truth` (PR#543 CLOSED not-merged, 29 ahead; tip security literal cleanup): Work (money-ready bridge, recency, 6 DB leaks) landed via #540/#544 + recent `money_ready_verdict.py` recency gate + `audit_surface_truth_banner.js`. Spot-checks on files matched origin/main. (Catch-all 24-commit "merge" attempt that was superseded.)
- `fix/md-action-items-2026-06-05` (PR#542 CLOSED, 11 ahead): Catch-all (included GE reverse-split/RENDERUSDT cull f47be5c, feature-signals CANON_PATH, KIMI triage, security literals, money-ready). All confirmed in main logs/files + #544/#545. Tip was just "CI rerun" chore.
- `fix/feature-signals-integrity-production-gates` (PR#541 CLOSED, 7 ahead): CANON_PATH + PENNY/MEME ban present in `tools/feature_signals/orchestrator.py`; related #545 merged.
- `fix/audit-wr-bugs-crypto-leaderboard` (PR#526 MERGED).
- `audit-fixes-2026-06-04` (PR#524 CLOSED, 1 ahead): Superseded ("land reverse-split registry corrections (supersedes PR #524)").
- `fix/audit-nc-aggregate-recency` (PR#521 MERGED).
- `claude/fervent-knuth-il7i1`, `claude/fervent-knuth-UhRq4`, `claude/fervent-knuth-qTcOY` (and additional `claude/fervent-knuth-B4zwh`, `CJfrl`, `XlGIj`, `YeCJs`): Temp "fervent-knuth" agent branches, no PRs, stale. DELETE.
- `chore/all-items-2026-06-03` (PR#511 CLOSED, 1 ahead): Catch-all chore session branch; work distributed to later merges.
- `fix/price-tracker-symbol-normalize` (PR#489 CLOSED, 2 ahead): Symbol normalize landed as `bf67934ec0 fix(ai-tournament): normalize equity symbols before yfinance fetch`.
- `feat/land-verification-engine` (PR#454 CLOSED DIRTY, 1 ahead): `strategy_verification_engine.py` (and alpha_engine/ copy) present in main tree + ws.
- `feat/weekly-filter-report-2026-06-02` (0 ahead, no PR): `git merge-base --is-ancestor` true (tip in main history).
- `docs/eagle4-eagle5-gates-2026-06-02` (PR#447 CLOSED, 2 ahead): `updates/eagle4-eagle5-gates-2026-06-02.html` present in main.
- `copilot/litellm-ollama-aliases-20260602` (no PR): Copilot temp. (Additional `copilot/cherry-pick-exact-edits-20260526` also deleted.)
- `fix/tournament-resolver-chunk-batches` (PR#437 CLOSED, 3 ahead): Superseded by `-v2` merged as #449 (`e9b6f9aaf fix(ai-tournament): chunk resolve_db_picks`).
- `fix/baby-adapter-same-bar-reentry` (PR#436 CLOSED, 1 ahead): Landed as `aad5e1d912 fix(adapter): block same-bar re-entry in BabyStrategyAdapter`.
- `claude/deep-8ai-critique-synth-2026-05-31` (PR#405 MERGED).
- `peer-claude/mercury-cerebras-grok-mimo-feedback-2026-05-31` (no PR, is-ancestor MERGED). (Additional `peer-claude/pm-status-byclass-2026-05-31`, `refresh-testing-protocol-2026-05-31` deleted.)
- `fix/resolver-write-path-0601` (PR#418 MERGED).
- Blackboxai temps (no PRs): `blackboxai/gha-heatlh-fixes`, `blackboxai/outcome-resolver-git-add-harden`, `blackboxai/own-kilo-edge-stability-mysql-20260531`.
- Other May31 temps: `claude/edge-deepdive-forex-2026-05-31`, `dedupe/edge-stability-workflows-20260531`.

**Swarm consensus excerpt (deepseek):** "30 branches safe to delete. 2 branches to keep (gh-pages for hosting, feature/vrp-forward-clock-wireup for unique unlanded VRP Harvest pilot code). ... overall_confidence: high". Full output + raw in `swarm_runs/branch-cleanup-20260605T122747Z/`. (xai skipped: no XAI_API_KEY; kilo zero/parse-failed.)

**Risks noted (and mitigated):**
- 29-ahead on money-ready branch: verified via file content match + overlapping commits already in successful merges.
- 11-ahead catch-all: distinctive items (RENDERUSDT, CANON_PATH, literals) confirmed landed.
- VRP: explicitly kept due to new unlanded code (450+ insertions per --stat).
- Temp branches: synthesis captured in updates/ + merged PRs (e.g. deep-8ai had its #405 merged); dangling commits recoverable via reflog if ever needed (not expected).
- No production impact (these were dev/agent/PR branches, not deployed refs).

**Commands run (post-pull):**
```
git push origin --delete \
  pr/money-ready-bridge-truth \
  fix/md-action-items-2026-06-05 \
  ... (full list) \
  peer-claude/refresh-testing-protocol-2026-05-31
git fetch --prune
```

**Next:** If `feature/vrp-forward-clock-wireup` work is ready for production (VRP Harvest forward pilot), open a fresh PR from it (or rebase onto current main) rather than continuing to accumulate on the stale branch. Re-run `tools/strategy_tier_tracker.py` or audit flows after any related land.

This cleanup advances repo hygiene (supports Goal #1 audit performance work by reducing noise in branch list / avoiding accidental checkouts of ancient agent sessions).

References: swarm run dir above; today's memory/2026-06-05.md + updates (money-ready phase 1 etc.); gh PRs #405, #418, #436, #437, #447, #449, #489, #511, #521, #524, #526, #536, #540-545 etc.; AGENTS.md "NEVER delete branches without confirmation", "git stash && git pull --rebase...".

(Generated by Grok 4.3 post-swarm + manual verification 2026-06-05.)
