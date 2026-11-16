# Non-main branch GitHub Actions — diagnosis

**Generated:** 2026-11-15 22:47 EST · **Repo:** `eltonaguiar/findtorontoevents_antigravity.ca`
**Companion report:** [`NONMAINBRANCHES.md`](../../NONMAINBRANCHES.md) (are the branches themselves needed)
**Evidence:** 1,000-run API window (53 non-main runs), all 212 non-main refs walked via `git ls-tree`,
trigger blocks parsed from workflow files, `gh-pages` tree inspected.

---

## 1. Headline

| Measure | Value |
|---|---|
| Non-main branches | **212** |
| Non-main runs in the sampled window | **53** (vs ~947 on `main`) |
| Non-main branches that produced **any** run | **9** |
| Branches carrying workflow files that no longer exist on `main` | **211 of 212** |
| Distinct stale workflow files carried across branches | **15 names, ~9 per branch** |
| Non-main runs that feed a deployed artifact | **6** — all `pages build and deployment` on `gh-pages` |
| Non-main runs that gate a merge | **33** — `pull_request` checks |
| Non-main runs that were dead workflows resurrected | **2 failures** (§4) |

**Verdict:** non-main Actions activity is **~5% of total volume and almost entirely harmless**, but it is
**not free**: 211 branches carry ~1,880 stale workflow definitions that can fire on push, and two of them
did exactly that on 2026-11-16 01:51 — running workflows that were deliberately deleted from `main`.

---

## 2. What actually runs on non-main branches

Event split of the 53 non-main runs:

| Event | Runs | What it means |
|---|---|---|
| `pull_request` | **33** | PR checks. Gates merges. No artifact. |
| `push` | **14** | Branch-local workflow files execute — including stale copies. |
| `dynamic` | **6** | GitHub Pages build+deploy on `gh-pages`. |

By workflow:

| Workflow | Runs | Event | Feeds |
|---|---|---|---|
| Branch Large File Duplicate Guard | 9 | push | its own "job health page" commit — **all 9 cancelled, zero output** |
| No stale DB passwords | 8 | pull_request | PR check only |
| DB Password Leak Guard | 8 | pull_request | PR check only |
| Conflict Marker Check | 8 | pull_request | PR check only |
| masking-policy-lint | 7 | pull_request | PR check only |
| **pages build and deployment** | **6** | dynamic | **the live GitHub Pages site** |
| Secret Scan (M-043) | 2 | pull_request | PR check only |
| Audit Drift Telemetry | 2 | push | writes audit telemetry (2 successes) |
| `.github/workflows/mysql-q001-sync.yml` | 1 | push | **FAILURE — dead workflow, see §4** |
| `.github/workflows/ml-gatekeeper-ab-bootstrap.yml` | 1 | push | **FAILURE — dead workflow, see §4** |
| Audit Frontend Manifest | 1 | push | cancelled |

---

## 3. Where each class of non-main run feeds

**3a. `pull_request` checks (33 runs) → the merge gate, nothing else.**
These run the workflow definition from the PR head/base merge, so they always execute `main`'s current
lint suite (`Conflict Marker Check`, `DB Password Leak Guard`, `No stale DB passwords`,
`masking-policy-lint`, `Secret Scan`). They write no artifacts and publish nothing. They exist to
answer one question: *may this branch merge?* Cost is 5 short jobs per PR push — the cheapest thing in
the repo and the only non-main activity that is clearly load-bearing for correctness.

**3b. `push` on a feature branch (14 runs) → whatever that branch carries.**
This is the dangerous class. A push to a branch executes the workflow files **as they exist on that
branch**, so the ~9 legacy files each branch still carries are live code paths. Two mechanisms make
them mostly inert but not reliably so:

- `schedule:` triggers **never fire from a non-default branch** — GitHub only schedules from `main`,
  so the 8 schedule-driven legacy files cannot wake up on their own.
- `push:` and `pull_request:` triggers **do** fire per-branch. On the 12 branches sampled,
  `mysql-q001-sync.yml` is `schedule,workflow_dispatch` only — but see §4, where it ran anyway.

**3c. `gh-pages` → the published site (6 runs, all success).**
`gh-pages` is the only non-main branch with a real production feed. It holds 8 files
(`index.html`, `live_picks.json`, `big_mover_widget.html`, `generate_dashboard.py`,
`big_mover_payload_schema.json`, `backtest_dashboard.py`, `__init__.py`, `.nojekyll`) and **zero
workflow files**. The `pages build and deployment` runs are the Pages service's own `dynamic` event,
not a repo workflow. **Deleting this branch breaks the live site.**

---

## 4. Redundancy finding: the dead workflows resurrect on branches

The single worst concrete finding. On 2026-11-16 01:51, branch
`fix/disable-dead-workflows-2026-11-16` — a branch whose *purpose* was to disable dead workflows —
triggered:

| Run | Conclusion |
|---|---|
| `.github/workflows/mysql-q001-sync.yml` | **failure** |
| `.github/workflows/ml-gatekeeper-ab-bootstrap.yml` | **failure** |

Both files were **deleted from `main` as dead** (they are absent from main's 355 workflow files) and
survive only as branch copies. Their display name is the raw file path because neither YAML has a
`name:` key — a reliable tell for an abandoned workflow.

The irony is the diagnosis: **a branch cannot be "clean" of a workflow that its own history still
carries.** Disabling a workflow on `main` removes it from `main` only; every existing branch keeps its
copy and can re-run it the next time anyone pushes there.

*Honest limit:* that branch has since been deleted, so the exact `on:` block that admitted a `push`
event cannot be re-read. On 12 sampled branches the same file is `schedule,workflow_dispatch` only,
which would **not** admit a push — so the branch likely carried a locally modified trigger. Marked
**UNVERIFIED**; the two failed runs themselves are certain.

---

## 5. Duplicates and redundancies, ranked

| # | Redundancy | Scale | Cost | Fix |
|---|---|---|---|---|
| 1 | Stale workflow copies on every branch (`mysql-q001-sync`, `ml-gatekeeper-ab-bootstrap`, `secret-scan`, `meme-scanner-fixed`, `daily-price-refresh`, `db-freshness-check`, `cross-db-consistency`, `live_trading_canada_free`, `torontoevent-backtest-and-deploy-ROOCODE`) | **211 branches × ~9 files ≈ 1,880 definitions** | Wakes up dead jobs on push; two already failed | Delete merged/abandoned branches (§6) — a branch copy cannot be patched from `main` |
| 2 | Branch Large File Duplicate Guard on branches | 9 runs, **9 cancelled**, 0 results | Pure runner burn, zero output | Fixed on `main` (PR #821: timeout 15→180, push→weekly). The branch runs keep dying because **each branch runs its own old copy** — only deleting branches removes them |
| 3 | `mermaid-test-deploy.yml` on 10 doc branches | 10 branches | Fails at "Deploy to GH Pages" | Gone from `main`; dies with the branches |
| 4 | 96 `claude/*` scratch branches | 96 branches, ~9 stale files each | Dormant but armed | Delete — they are agent scratch, oldest from 2026-06-05 |
| 5 | PR lint suite re-running 5 workflows per branch push | 33 runs | Low, and load-bearing | Keep |

**Note on fix #2:** the guard was fixed on `main`, and that fix will **not** reach the 211 branches.
A branch executes its own copy. This is the structural reason branch sprawl makes workflow hygiene
impossible: every fix has to be re-applied per ref, or the ref has to go.

---

## 6. Proposed actions

1. **Delete the 13 branches already merged into `main`.** Their work is in `main`; their stale
   workflow copies are pure liability. Zero risk.
2. **Delete the 96 `claude/*` scratch branches** (oldest 2026-06-05) and the abandoned
   `feat/*` experiments older than 30 days that are not merged and have no open PR. This removes
   ~90% of the stale-definition surface.
3. **Keep `gh-pages`** — it is the site. Never delete.
4. **Keep active `fix/*` branches** while their PR is open; delete on merge (configure
   "automatically delete head branches" so it stops accumulating).
5. **Do not attempt to patch stale workflow files branch-by-branch.** Deleting the ref is the only
   durable fix, because `main`'s deletions do not propagate.
6. **Optional hardening:** add a repo ruleset restricting `push` triggers on non-default branches, or
   a lint workflow that fails if `.github/workflows/` on a branch differs from `main` — but that adds
   more CI, so deletion is the cheaper answer.

---

## 7. Reproduction

```bash
# stale workflow files per branch (free, no API)
git for-each-ref --format='%(refname:short)' refs/remotes/antigravity | grep -v HEAD | while read r; do
  git ls-tree -r --name-only "$r" | grep '^\.github/workflows/.*\.ya\?ml$'
done | sed 's|.github/workflows/||' | sort | uniq -c | sort -rn

# non-main runs (API)
curl -s -H "Authorization: token $TOKEN" \
  "https://api.github.com/repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs?per_page=100" \
  | python -c "import json,sys; [print(r['head_branch'],r['event'],r['conclusion'],r['name']) for r in json.load(sys.stdin)['workflow_runs'] if r['head_branch']!='main']"
```
