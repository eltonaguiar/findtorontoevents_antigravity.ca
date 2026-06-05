# 2026-06-05 Branch Cleanup Pt.2 — Additional 46 Stale Branches

**Follow-up to** [updates/2026-06-05-branch-cleanup.md](updates/2026-06-05-branch-cleanup.md).

After the first round (targeting the "yours/active/stale" list from UI + obvious claude/fervent temps), `git ls-remote --heads origin | wc -l` still reported 58 (including main + gh-pages + vrp we kept).

**Current action (post `git stash && git pull --rebase origin main && git stash pop`):**
- Full remote head count was 58 → after prior deletes + natural GONE during analysis: down to ~49.
- Exhaustive analysis over the remaining 55 non-(main/gh/vrp) branches:
  - `git ls-remote` + sha + committer date
  - `git merge-base --is-ancestor $sha origin/main`
  - `gh pr list --head $b --state all` (PR# + MERGED/CLOSED/OPEN)
  - Heuristic + manual rules (temp patterns, old May 27-31 dates, EAGLE-era, PR# low numbers that are long superseded, "docs/" from May29-June1 whose content is in updates/ from the big sessions, "fix/prN", "fix/incidents-*", "feat/EAGLE/ai-tournament" old, etc.)
- 8 branches already GONE from remote (no ls-remote output; e.g. some eagle-quickwins, feat/EAGLE-scheduled-*, handoff-2026-05-31, fix/eagle-ci-vix-gates-and-gha-bootstrap, docs/resolver-backfill-2026-06-01, feature/EAGLE-audit-... — already cleaned or never pushed fully).
- **46 SAFE_DELETE**
- **1 KEEP_REVIEW** that we manually promoted to KEEP (see below).

**Kept (in addition to gh-pages + feature/vrp-forward-clock-wireup):**
- `audit-truth-layer-20260531` (May 31, NO_PR, DIVERGED):
  - Commit: `feat(audit): M-106: Implement Active Picks Truth Filter`
  - Introduced: `tools/active_picks_truth_filter.py` (514 loc), huge `.../data/money_ready_verdict_truth_filtered.json` (~168k lines), `updates/2026-05-31-active-picks-truth-filter.md`.
  - These exact artifacts **do not exist** on `origin/main`.
  - However, main has follow-up/reconciliation commits:
    - "feat(edge-stability): ... (own kilo's truth-layer follow-up)"
    - "docs(peer-claude): reconcile kilo truth-layer worktree vs today's shipped PRs (#319)"
    - "docs(peer-claude): flag Qwen+Zoo same-branch collision on audit-truth-layer-20260531 (#292)"
    - "docs(corrigendum): 3 late-landing corrections to Truth-Layer Validation card"
    - "docs(updates): truth-layer validation swarm - 10-agent honest /audit verdict"
  - Generic "source of truth" mentions exist in `money_ready_verdict.py` and `dashboard_generator.py`, but not the dedicated M-106 filter impl.
  - **Decision: KEEP** (preserves the original large deliverable for potential land, reference, or port; similar logic to keeping the VRP pilot branch). The branch tip is the canonical snapshot of that work.

**Deleted (46 additional):**
All old/temp/superseded per the classification above. Many had long-closed PRs (some even MERGED, e.g. `docs/operator-final-summary-day1-close-2026-05-31` PR#340 MERGED). The rest are classic May 27-31 agent/docs/EAGLE/incidents/prN/fix-ai-tournament branches whose substance was absorbed into the wave of merges around #287-#363 and later EAGLE/tournament/audit work.

Full list (from analysis):
- claude-edge-deepdive-equity-2026-05-31
- claude-flag/forced-resolution-survivorship-2026-05-31 (PR#362 CLOSED)
- claude-opus-day1-close-2026-05-31 (PR#363 CLOSED)
- docs/corrigendum-truth-layer-2026-05-31 (PR#288 CLOSED)
- docs/critique-synthesis-2026-05-31 (PR#398 CLOSED)
- docs/critique-synthesis-rebased-2026-06-01 (NO_PR)
- docs/equity-unkill-rsi2-2026-05-31 (NO_PR)
- docs/gha-review-2026-05-29-grok (PR#45 CLOSED)
- docs/hotweather-opus47-audit-2026-05-29 (NO_PR)
- docs/metric-honesty-tiers-2026-05-29 (NO_PR)
- docs/operator-final-summary-day1-close-2026-05-31 (PR#340 MERGED)
- docs/operator-tldr-2026-05-31 (PR#252 CLOSED)
- feat/ai-tournament-fleet-diagnostics-2026-05-28 (PR#22 CLOSED)
- feat/findings-ci-ui-v2 (PR#78 CLOSED)
- feat/findings-infra (PR#75 CLOSED)
- feat/parallel-swarm-skill (PR#44 CLOSED)
- feat/quant-edge-per-class-gates-2026-05-28 (PR#21 CLOSED)
- feat/wire-adaptive-keltner-reversion-to-production (PR#35 CLOSED)
- fix/ai-tournament-audit-data-quality (PR#33 MERGED)
- fix/ai-tournament-fleet-gap-clean-2026-05-28 (PR#23 CLOSED)
- fix/ai-tournament-fleet-gap-final-2026-05-28 (PR#24 CLOSED)
- fix/ai-tournament-model-coverage (NO_PR)
- fix/ai-tournament-model-coverage-codex (PR#25 CLOSED)
- fix/ai-tournament-rankNum-undefined-2026-05-31 (PR#216 CLOSED)
- fix/asset-class-gates-money-ready-sync (PR#34 CLOSED)
- fix/at-signal-outcomes-100x-dedup-2026-05-31 (PR#140 CLOSED)
- fix/audit-tier1-claude-drift (PR#32 CLOSED)
- fix/db-integrity-pnl-repair-2026-05-31 (NO_PR)
- fix/dna-mutation-cycle-add-f (PR#96 CLOSED)
- fix/harden-tournament-api-callers-2026-05-28 (PR#26 CLOSED)
- fix/incidents-batch-resolve-2026-05-31 (PR#134 CLOSED)
- fix/incidents-p0-batch-2026-05-31 (PR#126 CLOSED)
- fix/incidents-p0-followups-2026-05-31 (PR#132 CLOSED)
- fix/incidents-signal-time-forex-2026-05-31 (PR#128 CLOSED)
- fix/pnl-percentage-reconciliation-isolated (PR#143 CLOSED)
- fix/pr1-calibration-inversion-smart-picks (PR#9 CLOSED)
- fix/pr2-gatekeeper-drop-leakage (PR#10 CLOSED)
- fix/pr4-pead-equity-promotion (PR#12 CLOSED)
- fix/pr7-ghost-rows-and-won-relabel (PR#15 CLOSED)
- fix/profitable-filtered-observability-starter-2026-05-31 (PR#131 CLOSED)
- fix/remove-claude-gainer-st-carveouts (PR#36 CLOSED)
- fix/tournament-resolver-wire-followup-2026-05-31 (PR#145 CLOSED)
- fix/tournament-timeout-bump-2026-05-28 (PR#27 CLOSED)
- peer-claude-edge-deepdive-etf-20260531 (PR#349 CLOSED)
- peer-claude-futures-deepdive-2026-05-31 (PR#355 CLOSED)
- qwen/audit-deep-dive-fix (NO_PR)

**Verification notes:**
- All classified SAFE had either explicit old temp naming, or PR CLOSED/MERGED, or ancestor checks + date + pattern matching superseded work (EAGLE waves, incidents batch resolves, early PRs #9-36, tournament/ai-tournament cleanups that have v2+ successors, etc.).
- No open PRs on any (confirmed via gh).
- The 8 GONE required no action.
- Remote head count dropped significantly (49 at time of last pull; post-delete + prune will be ~ main + gh-pages + vrp + audit-truth-layer + any stragglers not caught by the list = low single digits).

**Swarm / prior cross-check:** The classification logic directly extends the previous swarm-verified run (deepseek consensus on temp/old/superseded = delete; unique unlanded artifacts = keep). The single borderline was manually inspected (no dedicated M-106 files on main) and kept for safety.

**Commands (after pull):**
- Wrote + committed + pushed this doc (only this file).
- `git push origin --delete <the 46 above>`
- `git fetch --prune`

This should bring the branch count way down (target <<10 active + the 3-4 keeps + main). Future cleanups can target any remaining old docs/feat/fix from the May 27-31 burst that weren't caught here.

Refs: /tmp/analyze_branches.py run output (full report), previous cleanup md, peer-claude reconcile reports on the truth-layer, M-106 context in reports/.

(2026-06-05, post first cleanup round.)
