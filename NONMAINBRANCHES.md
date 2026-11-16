# NON-MAIN BRANCHES — are they needed?

**Refreshed:** 2026-11-16 04:05Z (supersedes the 2026-11-15 22:47 EST audit; that analysis is kept at
[`GHACTIONS_2026-11-16/2026-11-15_22-47_EST_nonmain/NONMAIN_GH_ACTIONS_DIAGNOSIS.md`](GHACTIONS_2026-11-16/2026-11-15_22-47_EST_nonmain/NONMAIN_GH_ACTIONS_DIAGNOSIS.md)
and remains correct on population and prefix mix).
**Companion:** [`GHACTIONS_NONMAIN_BRANCH_RUNS.MD`](GHACTIONS_NONMAIN_BRANCH_RUNS.MD) — what runs, what
it feeds, duplicate analysis.
**Method:** `GET /branches` (213 live), `GET /compare/main...<branch>` for all of them, `git
for-each-ref` for ref dates, `git cat-file` on every branch tip, `GET /pulls?state=open`.
Evidence: `reports/gha_nonmain_audit.json`.

---

## 1. The numbers (refreshed)

| Measure | Value |
|---|---|
| Live remote branches | **213** (1 `main` + **212** non-main) |
| Remote-tracking refs in this clone | 223 → ~10 stale locals for branches already deleted upstream |
| Fully merged (`ahead_by = 0`, excluding `main`) | **12** |
| Unmerged (`ahead_by > 0`) | **199** |
| Open pull requests | **0** |
| Touched in the last 24h | **23** |
| Last commit 90–180 days ago | **102** |
| Last commit > 180 days | 0 *by ref date in this clone* |
| Branches carrying the 3 renamed `.disabled` workflows | **212 of 213** (636 file references) |
| Branches that produced any Actions run in 7h | **9** |
| Branches that feed a live deployment | **1** (`gh-pages`) |

Merged/identical (safe by the rule, `ahead 0`):

```
backup/gha-audit-2026-11-16            chore/scrape-events-11pm-toronto
feat/audit-dashboard-go-live-20261022  feat/kimi-stop-record-b4-spy
feat/micro-hold-fix-20261022           feat/stop-fill-cost-gate-final-v3
feat/systematic-entry-cell-miner       fix/p0-safe-fixes-2026-11-14-main
nemotron-june-2026-audit               nemotron/audit-copy-trader-stale-check
rescue/ddee81a6e9                      rescue/ff726af5ae
```

`backup/gha-audit-2026-11-16` is 0-ahead by the rule but is someone's backup from today — leave it
unless its owner releases it.

---

## 2. Which are genuinely needed

**Needed regardless of anything else — 1:**

- **`gh-pages`** — the published Pages source (`.nojekyll` present). Deleting it takes the Pages site
  down.

**Needed right now — ~23 + worktree branches:**

- The 23 refs touched in the last 24h are live work. More importantly, this machine has **60+
  registered worktrees** (`git worktree list`) pointing at feature branches — deleting one of those
  breaks an active agent's checkout. The earlier "needed — exactly one" verdict was correct about
  *merges* and wrong about *machines*.

**Needed while a PR is open — 0 today.** No branch is currently a PR head.

**Needed by exception:** `archive/*`, `backup/*`, `rescue/*` (deliberate recovery pointers).

**Not needed — 12 merged.** Their commits are all in `main`; only fork-lag copies remain.

**Not needed — 199 unmerged with no PR.** This is the uncomfortable number: 199 branches contain work
`main` does not have, and **none of it is proposed anywhere**. A branch is a proposal; 199 proposals
with no PR is storage, not collaboration.

**Likely not needed — the `claude/fervent-knuth-*` set (~96).** Agent scratch sessions, mostly June,
no PRs, no worktrees on this machine. Highest-value cleanup after the merged set.

---

## 3. Why surplus branches cost this repo specifically

1. **They make workflow fixes non-propagating.** `main` fixed
   `branch-large-file-dup-guard` (push → weekly). Branch copies still have `push:
   branches-ignore: [main]`, and a push runs *that branch's* file — so 9 non-main runs appeared in 7
   hours, 8 cancelled. Fixing `main` again cannot help.
2. **They resurrect retired workflows.** 212 branches carry `secret-scan.yml`,
   `mysql-q001-sync.yml`, `ml-gatekeeper-ab-bootstrap.yml`, all `.disabled` on `main`. Four runs in 7
   hours, **two failures**. See the P0 in the companion report.
3. **They carry pathological CI variants.** The named eight (per `BRANCH_AUDIT.md`) still have the
   old no-timeout / `cancel-in-progress: true` guard; any push there burns a runner and produces
   nothing.
4. **They dilute every audit.** "Which workflows exist?" has no single answer; 212 trees must be
   walked to answer it.
5. **They create merge friction** in a repo where bots push `main` every ~60s.

Note the correction to a common assumption: **schedules do not fire from non-main branches**, so
branch copies cost nothing while idle. The cost is entirely on **push** (the guard) and on **orphan
registrations** that still match a branch's file. That is why deleting branches is effective but not
urgent, and why disabling registrations is urgent but not destructive.

---

## 4. Recommended dispositions (safe, ordered)

| Order | Action | Count | Risk |
|---|---|---|---|
| **0** | **Disable the 3 orphan workflow registrations by id** (companion report §4) | 3 | none — reversible |
| 1 | Delete branches whose `ahead_by = 0` (exclude `main`, `gh-pages`, backups) | 12 | none — work is in `main` |
| 2 | Enable *Settings → Automatically delete head branches* | — | none — stops the pile-up |
| 3 | Owner merge-back of `main` into the 8 actively-pushed branches carrying bad guard copies | 8 | needs owner consent |
| 4 | Delete `claude/fervent-knuth-*` scratch branches >30 days, **after** worktree exclusion | ≤96 | low |
| 5 | Review the 90–180 day dormant set in batches of 20 | ≤102 | low, needs sign-off |
| 6 | Re-run this analysis monthly; target <30 branches | — | — |

Expected: 213 → ~200 immediately (12 merged + stale local refs pruned), → ~100 after session
branches, with the orphan runs gone at step 0 regardless of how many branches remain.

---

## 5. Candidate generation (read-only — deletes nothing)

```bash
python3 -c "
import json
for r in json.load(open('reports/gha_nonmain_audit.json'))['branches']['rows']:
    if r['ahead_by']==0 and r['branch'] not in ('main','gh-pages'):
        print(r['branch'])" | sort > /tmp/merged.txt

git worktree list --porcelain | awk '/^branch /{sub("refs/heads/","",$2); print $2}' | sort > /tmp/wt.txt
comm -23 /tmp/merged.txt /tmp/wt.txt      # the only lines safe to delete today

# dormant review (oldest first):
git for-each-ref --sort=committerdate \
  --format='%(committerdate:short) %(refname:short)' refs/remotes/origin \
  | grep -vE 'origin/(main|gh-pages)$' | head -60
```

Deletion is then one deliberate `git push origin --delete <branch>` per line, by the owner.
**Nothing was deleted by this audit.**

---

## 6. Limitations

- Ages come from ref committer dates in a shallow/partial clone; "0 older than 180 days" describes
  this clone, not necessarily the remote.
- `ahead_by = 0` proves no unique commits, not zero sentimental/agentic value.
- Worktree mapping covers **this machine only**; other agents may hold worktrees on branches that look
  abandoned here.
- The ~10 stale local tracking refs can be pruned with `git remote prune origin` (not run).
- Prefix counts (96 `claude/*`, 32 `feat/*`, …) are from the 22:47 EST audit and were not re-derived
  here; population totals above were re-measured.
