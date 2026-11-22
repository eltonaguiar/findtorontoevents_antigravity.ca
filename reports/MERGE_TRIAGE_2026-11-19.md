# Merge triage — which in-flight work goes through, and how

**Author:** Buffy · **Date:** 2026-11-19 · **Base measured:** `origin/main` = `6b8eea1a1e1`
**Related:** `reports/PEER_REVIEW_OF_ALL_DESIGNS_BUFFY_2026-11-19.md`, `reports/PEER_CROSSCHECK_BUFFY_2026-11-19.md`

## The headline

**PR #965 (`feat/audit3-p0-p1-correctness`) must not be merged as a branch merge, and
neither must `feat/audit-review-organization-2026-11-19`.** Both sit **1,555 commits
behind** `origin/main`, and main has since *independently implemented* the mechanisms
those branches carry. A branch merge would not add those mechanisms — it would
**delete** main's newer versions of them.

This is not a style objection. Here is the mechanism-by-mechanism count in
`alpha_engine/audit3_tribunal.py`:

| Mechanism | `origin/main` | PR #965 branch | Direction |
|---|---:|---:|---|
| `global_trial_count` (global-n DSR) | **6** | 0 | branch would **remove** it |
| `provenance_id` | **1** | 0 | branch would **remove** it |
| `alpha_gate_report` | **10** | 0 | branch would **remove** it |
| `G8` | 2 | **6** | branch genuinely adds detail |
| `selection_alpha` | 8 | 10 | branch adds 2 |

So of the five deltas the branch claims to deliver, **three already exist on main and
are richer there**, and two are real. Resolving 15 conflicted files by hand, keeping
"my side" wholesale, is how those three get silently reverted — which is exactly the
silent-file-revert hazard this repo has already been burned by.

## The correct resolution for PR #965

Do not merge. Do not rebase 1,555 commits. **Replay only the deltas main lacks**, as a
fresh patch off `origin/main`:

1. `G8` gate detail and `G9` cost-stress gate — the two mechanisms main does not have
   at branch depth.
2. Blocklist wiring in `forward_validator.py` / `forward_observations_ingest.py`.
3. `audit_dashboard/audit2.html` + `audit2.js` + `tests/test_audit2_page_deploy.py`
   — a new page, purely additive, no conflict with main's renderer.
4. `.github/workflows/audit3-denylist-watchdog.yml` — new file, purely additive.

Everything else in that branch is either already on main or superseded by it. Verify
each replay with the same greps in the table above; a replay that *lowers* main's
`global_trial_count` count is a revert, not a merge.

## Per-branch decisions

Verdict vocabulary: **GO** (merge), **REPLAY** (re-apply deltas onto main), **SPLIT**
(merge the safe half, hold the rest), **HOLD** (needs a named fix first), **BACKUP**
(keep as a backup branch, never merge).

| Branch | Ahead | Behind | Files | Verdict |
|---|---:|---:|---:|---|
| `audit3-forward-unmatched-visibility` | 1 | 373 | 3 | **GO** — smallest safe code merge |
| `fix/crypto-sim-net-grading-2026-11-19` | 1 | 325 | 1 | **GO** — one file, net grading, 17 tests pass |
| `docs/audit2-3-review-corrected` | 1 | 537 | 4 | **GO** — docs only, zero code |
| `publish/buffy-crosscheck-debate-2026-11-19` | 1 | 139 | 5 | **GO** — my own; docs + one tool |
| `fix/sleeve-implausible-pf-2026-11-19` | 24 | 1555 | 64 | **REPLAY** — take my 5 files only, not the inherited 23 |
| `feat/audit3-p0-p1-correctness` (PR #965) | 2 | 1555 | 23 | **REPLAY** — 2 real deltas, 3 regressions |
| `fix/audit3-alpha-scope` | 4 | 1555 | 14 | **REPLAY** — child of #965; same rule |
| `feat/audit-review-organization-2026-11-19` | 23 | 1555 | 60 | **SPLIT** — docs half GO; screeners HOLD |
| `preserve/auditcopytrader-*` | — | — | — | **BACKUP** — that is their purpose |
| `feat/ghcopilot-fund-strategy-profile` | 274,881 | 4,186 | 0 | **BACKUP** — unrelated history, unmergeable |

### Why `fix/sleeve-implausible-pf` is a REPLAY, not a GO

I cut it from opencode's branch, so it carries their 23 commits as ancestors. Merging
it would drag that whole branch in. The five files that are actually mine must go as a
patch: `alpha_engine/audit3_tribunal.py` (PF gate hunk only), `tools/assert_surface_parity.py`,
`reports/surface_parity.json`, `reports/PEER_REVIEW_OF_ALL_DESIGNS_BUFFY_2026-11-19.md`,
`updates/2026-11-19-surface-parity-assertion-and-sleeve-pf-gate.md`.

### Why the review-organization branch is a SPLIT

It has a genuinely good half and a genuinely dangerous half.

- **Good (docs, merge freely):** the design-debate docs, the peer-review request, and
  the security commit `24323e441a0 security: remove hardcoded DB password from 14 files`.
- **HOLD (code):** `bond_screener.py`, `commodity_screener.py`, `mutual_fund_screener_runner.py`
  were marked "money-ready YES 8/8 pass" on **placeholder expense ratios**. Placeholder
  inputs cannot produce a real verdict. Hold until the ratios are fetched live.
- **HOLD (code):** `confidence_recalibrator.py` is a hand-written lookup fitted on the
  sample it scores. In-sample by construction. Keep the interface, not the numbers.

## The security item is half-fixed

`b5f42b39ec1` wrote a plaintext DB password into 14 tracked files on a public repo. The
branch tip is now clean (0 literal `AUDIT_DB_PASS = '...'` matches), but:

- the value is **still in git history** on that branch — rotation is required regardless;
- `tools/run_daily_resolver_hygiene.sh` on that branch **still hardcodes a literal**.

Merging the tip does not un-leak anything. Rotation is the fix, and it is a human action.

## Settled in passing

**kilo's volume-context A/B vote is already decided.** The sidecar (option B) landed on
main as `04e4862e7e9 feat(data): sidecar mode for volume context (no ALTER on the
critical table) + approach doc`. No vote is needed; the question is closed in favour of
the answer that avoids an ALTER on the 51k-row hot table.

## Merge order (safest first)

1. `docs/audit2-3-review-corrected` — docs, zero risk.
2. `fix/crypto-sim-net-grading-2026-11-19` — 1 file, tested.
3. `audit3-forward-unmatched-visibility` — 3 files, small, isolated.
4. `publish/buffy-crosscheck-debate-2026-11-19` — docs + 1 tool.
5. Replay the PF gate hunk onto main (5 files).
6. Replay the G8/G9 + audit2-page deltas from #965.
7. Screeners last, after expense ratios are real.

## Who executes

Per `AGENTS.md` ("Never push commits that include files you didn't create or modify"),
I verify and publish the decision; **branch owners execute their own merge**. I will
drive any step the operator explicitly hands me. Each step lands as its own PR so a
revert is one click, not an archaeology project.

## Reconciliation with kilo's policy doc (landed after this analysis)

kilo independently published `docs/WORK_PRESERVATION_AND_MERGE_POLICY_2026-11-19.md` on
main at `5a26f9ac52b`, reaching the **same verdict on PR #965** ("DO NOT MERGE… would
revert the landed measurement work") from a different evidence path — they compared
mechanism *names* (`GLOBAL_TRIAL_FLOOR`, `n_trials_local`, `dsr_local`, `provenance_id`,
`require_alpha`); I compared *counts* of `global_trial_count`, `provenance_id` and
`alpha_gate_report`. Two independent methods, same answer — stronger than either alone.

Where the documents differ, mine is additive and theirs stands:

- **Backup namespace — adopt theirs.** kilo uses `refs/backup/<YYYYMMDD>/<name>`. My tool
  now writes to that same namespace and no longer creates `refs/heads/backup/*`, so a
  backup can never appear as a branch or be mistaken for a merge candidate.
- **Their two incidents are real, and mine are no substitute.** A worktree directory
  vanished with 21 uncommitted files; the shared main worktree was left with `MERGE_HEAD`
  set and 13 unresolved conflicts. My tool would have saved the first and can snapshot
  the second, but neither replaces their rule: **never leave a MERGE_HEAD dangling.**
- **My tool adds two things theirs does not:** a secret-pattern guard that refuses to push
  a snapshot (paths only, never values — directly relevant after `b5f42b39ec1` leaked a
  DB password) and a `--max-mb` size guard. Theirs adds an untracked-file tarball that
  mine does not produce.

## Conflict surface of my own branches

Every artifact I own was deliberately kept off shared files:

| Branch | Files | Shared code touched? | Merge risk |
|---|---|---:|---|
| `publish/buffy-review-packet-2026-11-19` | docs + 2 new tools | **none** | none — cannot revert code |
| `fix/sleeve-implausible-pf-2026-11-19` | `alpha_engine/audit3_tribunal.py` | **yes** | **conflicts** — replay, don't merge |

For the one branch that does touch shared code, the PF-gate hunk is published as a
standalone patch at `reports/patches/2026-11-19-sleeve-implausible-pf.patch`, so a reviewer
can inspect and apply the intent against *current* main without adopting the branch or its
23 inherited ancestors. Expect hunks to need relocation: the patch was generated against
that branch's base, not against today's main.
