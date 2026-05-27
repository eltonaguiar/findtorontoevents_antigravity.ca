---
title: "PR Set Plan + Items I Cannot Solve Without [X]"
date: 2026-05-27 04:00 UTC
status: PR #8 opened; PR #9, #10 planned but deferred (context budget + MiMo running PRs in parallel)
---

# PR Set Plan & Explicit Blockers

## PRs OPENED this session

| PR | Title | Status | Peer review |
|---|---|---|---|
| #3 | outcome-resolver gitadd freeze fix | ✅ Merged | swarm passed |
| #4 | 13-workflow sweep (same git-add bug) | ✅ Merged | swarm passed |
| #5 | Phase 1.2 + 1.4 backfill audit trail + MySQL SQL | ✅ Merged | self-review |
| #6 | 23-model AI tournament fleet + 14 new GH secrets | ✅ Merged | swarm passed |
| #7 | round-2 git-add sweep (3 more workflows) | ✅ Merged | subagent identified |
| **#8** | **nightly ML gatekeeper A/B training (matrix)** | **🟡 OPEN** | **deepseek MERGE_WITH_NOTES → amended** |

## PRs PLANNED but deferred

Two are queued but I'm deferring rather than rushing them because:
1. MiMo v2.5 Pro session is running the SAME "create PR set" instructions in parallel — duplication risk
2. Each needs careful code (not just config edits) and proper peer-review cycles
3. The 3-hour wakeup at 04:51 UTC will review whatever MiMo opened, then I'll decide which to still build vs which MiMo already did

### PR #9 — Permutation test scaffold (NEW-24 P0)

**Scope**: Add `tools/permutation_test.py` that:
1. Loads a strategy's closed picks from MySQL
2. Computes baseline PF
3. Shuffles outcome labels 1,000× and re-computes PF each time
4. Asserts real PF is in the 99th percentile of the shuffle distribution
5. Returns `PROMOTED | REJECTED_OVERFIT | INSUFF_N` verdict
6. Wire into `audit_trail/quality_gates.py::passes_smart_gate` as a new check (gated by env flag for safe rollout)

**Why P0**: Cross-AI consensus (DeepSeek + MiMo v1 + MiMo v2.5 + RooCode + me) all flag this as highest-priority new control. Without it, every "promising strategy" survives only on small-sample luck.

**Estimated work**: ~200 lines Python + tests + workflow wire-up + impact .MD. 2-3h.

**Blocker**: Needs read access to MySQL `trading_picks` table to load real closed picks. Either:
- (a) User runs the script locally against MySQL and pipes results to a JSON the workflow reads, OR
- (b) MySQL creds in GH secrets (already there: `DB_PASS_STOCKS` per workflows I've seen)

### PR #10 — Anti-overfit page INSUFF-N badge (P1 #4)

**Scope**: Add an "INSUFF-N (n<100)" badge to `audit_dashboard/anti_overfit.html` for any strategy row where `n_decisive < 100`, AND reorder so n≥100 rows show first.

**Why**: P1 #4 incident says CRYPTO ML strategies with DSR≥0.9995 are shown without insufficient-n badges; this misleads. Also a MiMo recommendation.

**Estimated work**: ~80 lines HTML/JS + 30 lines in `audit_trail/dashboard_generator.py` to compute the badge field. 1-1.5h.

**Blocker**: Would need to either (a) wait for next audit-dashboard cron to refresh the page, or (b) trigger the workflow_dispatch manually post-merge. Easy.

## Items I CANNOT SOLVE without [X] — explicit blockers

These are the gaps where I lack the access/permission/data to make a single-PR fix. Each names the specific access required.

### Needs MySQL write access (user runs SQL at maintenance window)

| # | Action | Why I can't | Status |
|---|---|---|---|
| 1 | Run `tools/relabel_closed_picks_mysql.sql` | Need INSERT/UPDATE on `ejaguiar1_stocks.trading_picks` | Script READY in repo since session start; gates downstream |
| 2 | Apply incidents-update SQL from `reports/2026-05-27_incidents_state_update_post_mimo.md` | Need UPDATE on `ejaguiar1_stocks.incidents` | Block of 5 RESOLVE + 13 INSERT statements |
| 3 | Restart `forward_validator` to drain 29M open-position backlog | Need to run a process on a server I don't have access to | P0 #13 — gates EVERY downstream WR/PF calculation |
| 4 | Deduplicate 56,559 ghost rows (top cohort: 20,474 MATICUSDT) | Need `DELETE FROM trading_picks WHERE ...` privilege | Same — corrupts every aggregate |
| 5 | Re-resolve 2,531 WON rows with negative PnL | Need to run `tools/re_resolve_historical_v2.py` against MySQL | Even after Phase 1.2 relabel, the WON-with-negative-PnL rows may not all be the same set |
| 6 | Extend Phase 1.4 trust_score backfill to MySQL | I wrote the local-JSON version; SQL counterpart needs `UPDATE trading_picks SET trust_score = ... WHERE ...` with the same logic as `alpha_engine/trust_score.py::compute_trust_score` | Currently only the JSON view is populated |

### Needs `~/dbpasses.txt` API key that doesn't exist

| # | Action | Missing key | Workaround |
|---|---|---|---|
| 7 | Wake up `gpt4o_mini`, `cursor_agent`, `claude_opus` tournament personas | `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` (no equivalent in dbpasses) | Get keys from platform.openai.com / console.anthropic.com, then `gh secret set` |
| 8 | Wake up `mistral_large` | `MISTRAL_API_KEY` (dbpasses has `MISTRAL API KEY` with spaces but I already grabbed it) | Already set in PR #6 |
| 9 | Switch mercury OFF dead OpenRouter quota to working `INCEPTION_API_KEY` | No `INCEPTION_API_KEY` in dbpasses | PR #6 already redirects mercury to Together AI as workaround; INCEPTION is the cleaner path |
| 10 | Re-key OpenRouter top-up | Account at openrouter.ai needs credit (~$5-10) | User decision |

### Needs strategy-author judgment (not just code)

| # | Action | Why I can't decide | Recommended owner |
|---|---|---|---|
| 11 | Promote `pead_equity` SHADOW → probation | Need to know the human-authored gate file and whether MiMo's 62.2% OOS WR matches the canonical `walkforward.by_class` figure | Strategy owner / dashboard admin |
| 12 | Kill `quan_engine_scalp` from emission | Per CLAUDE.md: requires `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (export closed CSV → `python tools/mutation_analysis.py`). I haven't run those. | Strategy owner with closed-pick CSV access |
| 13 | Add `forex_carry` to non_crypto_policy allowlist | Claimed 55-60% WR not yet verified per CLAUDE.md investigation rule (kill-before-investigate inverse applies) | Verify in shadow first |

### Needs cross-PC coordination

| # | Action | Why I can't | Status |
|---|---|---|---|
| 14 | Lift the `pause-remote-2026-05-22` freeze in MEMORY.md | User's other PC was rewriting git history; need user's go-ahead | User decision |
| 15 | Reconcile RooCode's `kilocode-improvement` skill, Kilo Code's `kilo-audit-sync` skill, and my `consult-swarm` / `PeerReviewSwarmOptions` skills into a unified skill registry | Cross-agent coordination | Defer to wrapup |

## Operational items needing investigation before code change

These I COULD code-fix but the investigation work isn't done:

| # | Action | What investigation is missing |
|---|---|---|
| 16 | Fix `claude_gainer_ml` "Models not found" — likely loader path mismatch | Trace which loader call fails (`live_scanner.py` vs `claude_gainer_ml/inference.py`) — needs to be run locally |
| 17 | Fix `mercury2` cwd bug — workflow says `joblib not found` but model exists | Need to run the workflow_dispatch and capture stack trace |
| 18 | Fix `ml-feedback-retrain` cold-start | Trainer has no path when `outcome_feedback_model.joblib` doesn't exist; need to add the initial-train branch |
| 19 | Fix `consensus_pick_builder.py` (active_picks.json is 0 keys despite copy-trader pipeline running) | Need to run locally + trace why merge fails |

## Recommended sequence for next session

1. **Review what MiMo's parallel session built** (4:51 UTC wakeup will sweep open PRs)
2. **If MiMo built PR #9 or PR #10**: review + merge or amend
3. **If MiMo did NOT build them**: build them per the scope above
4. **Then tackle "investigation needed" items 16-19** — those are CI loader path bugs that need a one-shot diagnostic workflow_dispatch + log read
5. **User actions** (1-15) are user-supervised; not code work
