# 03 — Branch Cleanup Manifest (outcome: HELD, 0 deletions)

**STAMP:** 2026-11-15_21-45_EST_ghactions · analysis 02:44–02:55 UTC · read-only; nothing deleted.
Method + tables produced by the branch-manifest sweep over all **215 `origin/*` refs** (origin/HEAD
excluded), tree-based (`git diff --raw --no-abbrev --no-renames` + per-file blob-OID equality,
`A`=branch-only, `M`=present-and-different, `D`=main-only) because the clone is **shallow** —
merge-base/cherry unavailable below the graft line.

## Verdict summary

| Verdict | Count | Action |
|---|---|---|
| PROTECTED | 36 | never delete (patterns: main, gh-pages, backup/gha-audit-2026-11-16, hermes/*, wired-in/*; +30 worktree-checked-out incl. 15 rescue-list names) |
| KEEP-WORK | 32 | carry unmerged work (lost-work rescue list — includes provably LOST June tools) |
| KEEP-OTHER | 147 | unique-content not certifiably empty (51 listed + 96 `claude/fervent-knuth-*`) |
| **DELETE-CANDIDATE** | **0** | **none certifiable — see gate below** |

## Why zero (the honest answer to "can branches be cleaned up for the most part?")

Every one of the 215 branches shows **≥1,015 code/config files present-and-different vs
current main** (main has drifted 1.0k–23.3k files from every fork point), and all show 5.8k–23.3k
`D` entries (main-only paths). Under the prescribed conservative test, zero-unique can NEVER be
certified in this state — the mass M-drift is overwhelmingly "main is newer", but without
ancestry (merge-base / `git cherry`) that direction is unprovable per file. Deleting on the
strength of that assumption is exactly how lost-work happens (49 branches here already carry
unmerged work, incl. tools absent from main entirely).

**What IS true today:** nothing on GitHub actually runs from these branches except
`mermaid-test-deploy.yml` on `wiring` (push-triggered). The other ~159 stale-branch workflow
copies are schedule-only → zero runtime (schedules fire only from the default branch). The
cleanup is cosmetic/namespace hygiene, not queue relief — the queue fixes landed separately
(cron stagger + FTP race guards).

## Rerun gate (produces real candidates)

1. `git fetch --shallow-since=2026-05-01 origin` (bounded deepen; restarted 02:56 UTC as a
   background job — full `--unshallow` attempt died earlier) or `git fetch --unshallow origin`.
2. Re-run classification with ancestry: DELETE iff `git log --cherry-pick --right-only --no-merges
   origin/main...<branch>` is empty AND branch tree adds no code/config path vs main AND >30d old.
3. Expected yield after the rerun: most of the 96 `claude/fervent-knuth-*` (Jun–Sep session
   scratch) + the June-era `plan/` `refute/` `pr/` namespace + Oct-stale `rescue/` `docs/` rows —
   anything whose M-drift proves to be "main is newer". KEEP-WORK (32) + PROTECTED (36) stay
   regardless; pr/145 needs a deliberate decision (anomaly 1).
4. Deletion execution rules: capture full tip SHA per branch (undo map: `git push origin
   <sha>:refs/heads/<branch>` restores), delete via `git push origin --delete`, batch ≤25/run,
   document in this file's successor.

## Rescue list (51 branches = never delete) — condensed

- **KEEP-WORK (32):** feat/{artifact-detector-ci, ast-reviewer-codemod-2026-11-12,
  contract-test-cold-merge-2026-06-22, crypto-onchain-fundamental-gates, enable-rsi5070-shadow-lane,
  finpredict-final-v001, forex-consensus-winner-2026-06-13, forex-pilot-tracker-2026-06-13,
  gha-actions-health, hermes-web-menu-entry-2026-11-12, intrabar-replay-noncrypto-2026-06-13,
  pead-earnings-cache-wiring, pead-equity-probation, pm-odds-history-leadlag-2026-06-12,
  pro-level-batch-2026-06-13, retired-provider-guard-2026-11-12, safe-patch-helper-2026-11-12,
  systematic-entry-cell-miner, walkforward-strategy-eval}, fix/{assetclass-cache-live-core-stats,
  audit-p0-truth, blacklist-save-active-picks, blob-guard-per-branch-concurrency-2026-11-15,
  ci-tests-drift-reconciliation, etf-short-gate-vix-combos-2026-11-15,
  feature-signals-safe-push-followup-2026-11-15, gha-backup-verify-dedup-2026-11-15,
  js-reference-accuracy-audit, kilo-ci-tests-backup-verify, oct10-thumbnail-crop-age-gate},
  hilarious-seer-to-main, oc/fund-walkforward-review-fixes
- **PROTECTED∩rescue (18):** 15 worktree checkouts (feat/{audit-edge-hunt-session-docs,
  b1-backfill-price-guard-…, b5-forward-track-tool-…, crypto-null-pnl-backfill-…,
  ghcopilot-fund-strategy-profile, minimax-next-steps-batch, p0-m036b-long-block-luxalgo,
  p0-next-steps-batch}, fix/{ci-backup-verify-and-dupguard, fc-category-persist-…,
  ghcopilot-btc-mtm-guard, ghcopilot-ftp-credential-loading, grok-quickfixes-dsr-resolver,
  pick-reason-audit-push, stale-tag-defects}) + hermes/forex-session-window-fix,
  wired-in/buffy-2026-11-15, wired-in/buffy-gh-actions-fix-2026-11-15
- **Missing from origin (1):** pr/145 — local ref only + `refs/pull/145/head` on GitHub;
  carries active `alpha-engine-bond.yml` (a 6-line delta of main's `.disabled` twin). Needs a
  deliberate keep-as-PR / push-as-branch / archive decision.

## Anomalies (carried forward)

1. `pr/145` namespace confusion (above).
2. **Secret-named files on main** (inherited by all branches; zero branch deltas):
   `favcreators/docs/api/.env.events`, `favcreators/public/api/.env.events` (291 B, 4
   value-bearing lines, no token-shaped strings) — **human review recommended** (likely config,
   not secrets). Separately verified earlier: real FTP/DB credentials live at
   `sam-repo/main` (different remote `eltonaguiar/ALT_PARALLELSWARM_SAM`) — rotation recommended.
3. `ghactions-v*` / `sam-repo/*` / `freellm/*` patterns match no origin refs (local worktree
   branches / other remotes) — expected.
4. Rename-skew: A-counts slightly overstate new content (stale pre-rename copies like
   `cross-db-consistency.yml` count as branch-only) — conservative direction (keep).
5. Full row-level table (215 rows) was produced in the sweep run; counts above are the
   contract. Rerun (gate above) regenerates it with ancestry-aware verdicts.
