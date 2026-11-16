# NON-MAIN BRANCHES — are they needed?

**Generated:** 2026-11-15 22:47 EST · **Repo:** `eltonaguiar/findtorontoevents_antigravity.ca`
**Companion report:** [`GHACTIONS_2026-11-16/2026-11-15_22-47_EST_nonmain/NONMAIN_GH_ACTIONS_DIAGNOSIS.md`](GHACTIONS_2026-11-16/2026-11-15_22-47_EST_nonmain/NONMAIN_GH_ACTIONS_DIAGNOSIS.md)

---

## 1. The numbers

| Measure | Value |
|---|---|
| Non-main branches | **212** |
| Already merged into `main` | **13** |
| Unmerged | **199** |
| Oldest branch commit | **2026-06-05** (163 days) |
| Branches committed to in the last 2 days | 15 |
| Branches carrying workflow files deleted from `main` | **211 of 212** |
| Branches with any Actions run in the sampled window | **9** |
| Branches that feed a live deployment | **1** (`gh-pages`) |

Population by prefix:

| Prefix | Count | Reading |
|---|---|---|
| `claude/*` | **96** | agent scratch branches, e.g. `claude/fervent-knuth-09ksmm`. No PRs open. |
| `feat/*` | 32 | feature work, mostly June–July |
| `fix/*` | 23 | bugfix branches, mostly recent (2026-11-15/16) |
| `rescue/*` | 4 | |
| `opencode/*` | 4 | |
| `docs/*` | 3 | |
| `audit/*` | 2 | |
| `wired-in/*`, `nemotron/*` | 4 | |
| singles | 44 | `wiring`, `videos-pipeline`, `bestiejobs-v3`, etc. |

---

## 2. Which branches are genuinely needed

**Needed — exactly one:**

- **`gh-pages`** — the published site source. 8 files (`index.html`, `live_picks.json`,
  `big_mover_widget.html`, `generate_dashboard.py`, `big_mover_payload_schema.json`,
  `backtest_dashboard.py`, `__init__.py`, `.nojekyll`), no workflows of its own. Pages builds it via
  the `dynamic` event (6 successful runs in the window). **Deleting it takes the site down.**

**Needed while a PR is open:**

- Any `fix/*` or `feat/*` branch with an open PR. As of this report **there are zero open PRs**, so
  strictly speaking none are needed today. Keep the handful from 2026-11-15/16 that agents are still
  working (e.g. `hermes/forex-session-window-fix`, which carries an unmerged forex fix).

**Not needed — 13 merged branches:**

Their work is already in `main`. They exist only because nothing deletes head branches on merge.
Their stale workflow copies are pure liability.

**Not needed — the 96 `claude/*` scratch branches:**

Agent scratch (`claude/fervent-knuth-*`). No open PRs, mostly June. Nothing references them.
They are the single largest source of the 1,880 stale workflow definitions.

**Probably not needed — unmerged `feat/*` older than 30 days:**

June–July experiments with no PR and no recent commits. Before deleting, confirm nothing references
them (they are recoverable from GitHub's branch-deletion grace period, but not indefinitely).

---

## 3. Why are they not needed (the argument)

1. **They carry no unique code that matters.** 13 are already merged. The rest are either agent
   scratch or abandoned experiments, none with an open PR. If a branch held something valuable, it
   would have a PR — the repo has none open.
2. **They actively cause harm.** Every branch keeps its own copy of ~9 workflow files that `main`
   deleted as dead. Those copies can fire on push. On 2026-11-16 01:51 two of them did:
   `mysql-q001-sync.yml` and `ml-gatekeeper-ab-bootstrap.yml` both ran and **both failed** on a
   branch. Workflows cannot be retired from the repo while branches still carry copies.
3. **Fixes do not propagate.** The Branch Large File Duplicate Guard was fixed on `main`
   (PR #821: timeout 15→180, push→weekly). The 9 branch runs of that guard are **still** dying,
   because each branch executes its own old copy. Every workflow fix has to be re-applied per ref,
   forever, unless the ref is deleted.
4. **They dilute every audit.** 212 refs × 355-file trees is why a branch-vs-main comparison takes
   minutes of tree-walking and why "which workflows exist?" has no single answer.
5. **They cost merge/rebase friction.** Bots push `main` every ~60s; stale branches re-conflict
   `.claude/skills` paths (case-insensitive collision) and force merge strategies instead of rebase.

---

## 4. Why keep any of them

| Branch class | Why it must stay |
|---|---|
| `gh-pages` | It *is* the deployment target. Removing it removes the site. |
| Active `fix/*` with unmerged verified work | Deleting loses the diff; e.g. the forex session-window fix is verified but unmerged. |
| Branches referenced by an open PR or a docs link | A PR that targets a deleted branch cannot be reopened cleanly. |

Nothing else earns its keep.

---

## 5. Recommended dispositions (safe, ordered)

| Order | Action | Count | Risk |
|---|---|---|---|
| 1 | Delete branches already merged into `main` | 13 | none — work is in `main` |
| 2 | Enable *Settings → General → Automatically delete head branches* | — | none — stops the pile-up |
| 3 | Delete `claude/*` scratch branches older than 30 days | ≤96 | low — agent scratch, no PRs |
| 4 | Delete unmerged `feat/*`/`rescue/*` older than 60 days with no PR | ~30 | low — abandoned experiments |
| 5 | Keep `gh-pages` permanently | 1 | — |
| 6 | Keep `fix/*` from the last 7 days until their PR merges | ~10 | — |
| 7 | Re-run this analysis monthly; target < 30 branches | — | — |

**Expected result:** 212 → roughly **25–30** branches, ~1,880 stale workflow definitions → near zero,
and branch-vs-main comparisons become instant.

**Do not** try to fix stale workflow files branch-by-branch. Deleting the ref is the only durable
remedy, because `main`'s deletions never reach an existing branch.

---

## 6. Safety notes

- Branch deletion on GitHub is recoverable for a limited window (the branch's commits remain reachable
  by SHA until GC). Record the SHAs before deleting anything unmerged.
- No branch should be deleted while an open PR targets it. Verified: **0 open PRs** at the time of
  this report.
- `gh-pages` is excluded from every recommendation above.
- This report deletes nothing. It proposes dispositions only.
