# 2026-11-24 — Worktree / empty-folder cleanup audit

**Scope:** home directory of this Linux box (`/home/eaguiar2015`), the 51 registered git worktrees
of `findtorontoevents_antigravity.ca`, and stray clones / empty shell folders on `/home`.

**Goal:** delete only what is provably recoverable (already on GitHub) or provably empty, never
touch anything the OS or a running agent depends on, and surface everything that is *not* backed up
as a risk.

**Verification method (per item, not by inspection of names):**
- `git status --porcelain` → modified / untracked counts
- `git status --porcelain --ignored` → gitignored files that `worktree remove` would silently drop
- `git branch -r --contains HEAD` → are the commits actually on a remote?
- `git ls-remote --heads origin` (302 heads) → does the branch name exist upstream?
- `lsof +D <path>` + `ps -eo cmd` → is a live process using this directory?

---

## Policy applied

| Condition | Action |
|---|---|
| 0 modified, 0 untracked, 0 ignored, HEAD on a remote ref | **delete** (commits live in the shared object store) |
| Only ignored `__pycache__` / `.pytest_cache` / `fred_cache` | **delete** (regenerable) |
| Only dirt is machine-local `.mcp.json` / `.cursor/mcp.json` (MCP servers stripped locally) | **restore from HEAD, then delete** |
| Real modified or untracked content | **keep + report** |
| Live file descriptors (agent running) | **keep** |
| No remote at all, or commits not on any remote | **keep + report as unbacked risk** |
| Empty directory tree | **delete** |
| Orphan directory whose only payload differs from the repo copy | **quarantine, do not delete** |

> `git worktree remove` deletes the *checkout* only. Committed work survives in
> `findtorontoevents_antigravity.ca/.git`. Only uncommitted/untracked/ignored files are lost —
> which is why those were counted explicitly.

---

## Deleted — 21 units, ~19 GB

### 1. Dead worktree records (directory already gone)
`/tmp/cells`, `/tmp/pr1046b`, `/tmp/pr1067` — removed with `git worktree prune -v`.

### 2. Fully clean worktrees, commits on remote (7)
| Path | Size |
|---|---|
| `.local/share/kilo/worktree-pool/…/candied-ruby` | 1.4 G |
| `.local/share/kilo/worktree-pool/…/melodious-lavender` | 1.4 G |
| `.local/share/kilo/worktree-pool/…/resolute-bar` | 1.4 G |
| `.worktrees/reconcile` | 1.3 G |
| `.worktrees/pristine-main` | 1.4 G |
| `.roo/worktrees/eltonsxyzdragon` | 426 M |
| `audit-fix-worktree` | 477 M |

### 3. Clean worktrees, only regenerable caches ignored (4)
`.kilo/worktrees/review-main`, `.kilo/worktrees/vanilla-handsaw-audit3`,
`.kilo/worktrees/vh-hotfix`, `.worktrees/cost-status-corrections`.

Ignored content was exclusively `__pycache__/`, `.pytest_cache/`, `alpha_engine/data/fred_cache/`.

### 4. Machine-local config dirt only — config restored from HEAD first (7)
`.worktrees/feat/cohort-reconciliation-followup`, `.worktrees/ghcopilot-btc-mtm-guard`,
`.worktrees/ghcopilot-ftp-credentials`, `.worktrees/ghcopilot-fund-strategy-profile`,
`.worktrees/ghcopilot-grok-scorecard`, `.worktrees/ghcopilot-symbol-durability`,
`.worktrees/health-fix`.

Each carried the same 2-file diff: `.mcp.json` and `.cursor/mcp.json` had their `mcpServers` block
replaced with `{}`. That is machine-local state, **not** authored work, and the committed version is
the complete one. Restored with `git checkout -- .mcp.json .cursor/mcp.json` before removal.

### 5. Duplicate full clones, byte-identical or fully contained in origin (4)
| Path | Size | Evidence |
|---|---|---|
| `wired-in-research` | 1.5 G | HEAD == `origin/main`, 0 dirty |
| `wired-in-research-temp` | 1.5 G | HEAD == `origin/main`, 0 dirty |
| `wired-in-repo` | 6.4 G | 0 dirty, HEAD contained in 2 remote refs |
| `gha-fix-shallow` | 44 M | 0 dirty, HEAD contained in 2 remote refs (separate repo `findtorontoevents.ca`) |

Each was checked for open file descriptors and live processes immediately before deletion (0/0).

### 6. Empty shell folders (2)
`~/blobstopper`, `~/nvidia-workbench` — contained **zero files**, only empty directories.

### 7. Zero-byte untracked junk in repo root (2)
`scanner_lifecycle.log`, `probabilistic_sharpe.log`.

### 8. Quarantined, not deleted (1)
`~/findtoradioevents_antigravity.ca` — a typo'd shell of empty directories. Its single payload file
(`…/02_per_asset_class_profitability/commodities/README.md`) **hashes differently** from the
repo copy (`50d20645…` vs `f3ec9cbf…`), so it was moved to
`~/.cleanup-quarantine-2026-11-24/` together with the repo version for comparison.

---

## Kept — and why (unbacked risks)

Nothing in this section was pushed. `AGENTS.md` forbids pushing branches whose files were authored
by other agents/tools, so these are reported with the command to remediate.

### A. Worktrees with real uncommitted work
| Path | Changes | Note |
|---|---|---|
| `.kilo/worktrees/vanilla-handsaw` | 2 modified | **IN USE — 16 open file descriptors.** Never delete while an agent holds it. |
| `.kilo/worktrees/moneyresearch` | 1 staged | `PEER_REVIEW_BUFFY.md` (367 lines) staged, not committed |
| `.worktrees/cis-vr-coding-guide` | 112 modified | branch not on remote |
| `.worktrees/fc-weather-deploy` | 111 modified | |
| `.worktrees/mental-health-resource-enrichment` | 111 modified | branch not on remote |
| `.worktrees/feat/cohort-reconciliation` | 10 + 1 untracked | |
| `.worktrees/pf-gate-main` | **UU conflict** on `alpha_engine/audit3_tribunal.py` | unresolved merge |
| `wt-ci` (detached) | 17 modified | |
| `wt-reason` | 14 modified | |
| `fix-passes-active-gate` | 29 + 4 untracked | |
| `p0-audit-json-2026-11-16` | 2 + 3 untracked | |
| `p0-repair`, `wt-why-tooltip`, `wt-nemotron-moneyready` | 1 each | |
| `fix-db-ghost-rows-and-freshness`, `quant-risk-improvements`, `wt-freebuff-moneyready`, `wt-audit-prediction-system` | untracked files only | |
| `feat-minimax-next-steps`, `copilot-weather-tv-2026-11-01`, `copilot-financial-review-20261115`, `quant-audit-2026-11-14`, `recent-picks-stats`, `weather-compact-layouts`, `subq-independent-review-20261012`, `movies-repair-main`, `audit2-deploy`, `ensure-your-files-are-on-the-remote-github`, `vh-mainport` | 0–2 | branch name not on origin — commits only reachable via other remote refs or not at all |

### B. Clones holding work that exists nowhere else
| Path | Size | Risk |
|---|---|---|
| `~/repo-clean` | 5.8 G | **`git remote` is empty — zero remotes.** 11 changes incl. 6 untracked docs (`PUSH_INSTRUCTIONS.md`, `GIT_HISTORY_REWRITE_SUMMARY.md`, `GITHUB_SUPPORT_TICKET_DRAFT.md`, 2 `updates/`, a cleanup script). |
| `~/findtorontoevents_antigravity_ca` | 6.0 G | 1 commit `2c3a4796d0d` ("fix(ci): triage workflow fleet, kill 3 dead crons…") present on **no** remote branch. |
| `~/bestiejob` | 578 M | 161 modified + 441 untracked; HEAD on no remote branch. |

### C. Non-git directories with unbacked content
| Path | Size | Files |
|---|---|---|
| `~/work` | 271 M | 4 887 |
| `~/mylabclone` | 54 M | 3 591 |
| `~/GHACTIONS_2026-11-16` | 39 M | 30 (partly contained in the unpushed commit above) |
| `~/SWARM_Nov162026` | 24 M | 31 |
| `~/ebond-work` | 8.5 M | 1 502 |
| `~/scratch` | 7.5 M | 43 |
| `~/EBOND-lab-screenshots`, `~/audit_tmp`, `~/backups`, `~/dropchat-multipc`, `~/fte-scrub-artifacts-2026-11-12`, `~/git-scrub-archive-2026-05-23` | < 0.5 M each | 1–11 |

---

## Tracked zero-byte junk still in the repo root (needs a commit, not a filesystem delete)

`⚠️`, `=2`, `=3`, `5`, `$.ci_run_id`, `$.regime_label`, `Last`, `Repo:`, `Mutation`, `Total:`,
`__init__.py`, `cqp_vote_*.txt` (4), `temp_full_science_report.txt`.

These are *tracked*, so removing them is a repo change: `git rm` + commit. Left in place because the
working tree already carries 95 unrelated modifications from other agents and mixing them would
violate "only push your own changes".

---

## Result

| Metric | Before | After |
|---|---|---|
| Registered worktrees | 51 | **30** |
| `/home` used | 579 G | **549 G** |
| `/home` available | 291 G | **320 G** |

≈ 30 GB reclaimed. No OS path, package directory, or `~/.config`-style directory was touched; only
git worktrees, git clone duplicates, empty shell directories, and two zero-byte untracked logs.
Nothing was pushed to any remote.

## Verification commands

```bash
cd /home/eaguiar2015/findtorontoevents_antigravity.ca
git worktree list                     # 30 entries
git worktree prune -v                 # no output = nothing stale left
df -h /home
ls ~/.cleanup-quarantine-2026-11-24/  # quarantined typo shell + repo README for diff
```

## Follow-ups (not executed, need authorisation)

```bash
# repo-clean has no remote at all
git -C ~/repo-clean remote add origin git@github.com:eltonaguiar/findtorontoevents_antigravity.ca.git

# the one orphan commit in the 6G clone - push on its own branch, do not merge
git -C ~/findtorontoevents_antigravity_ca push origin HEAD:refs/heads/ghactions-triage-2026-11-16
```

For each unbacked worktree branch, `git push -u origin <branch>` from inside that worktree makes the
branch ref backup explicit.

---

## Pass 2 — junk files, caches, git garbage

### Git garbage — the biggest single win
`git count-objects -vH` reported `size-garbage: 7.08 GiB`. Cause: five `.git/objects/pack/tmp_pack_*`
files abandoned by interrupted `git repack` runs. Verified with `lsof` that no process held them
open, then deleted them. Reclaimed **7,253 MB**; `size-garbage` is now `0 bytes`.

### Cache directories
Deleted `__pycache__`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, `.hypothesis` from the main
repo and 28 of 29 linked worktrees. 496 MB measured, 411 MB reclaimed (du block accounting).
Skipped `.kilo/worktrees/vanilla-handsaw` — a live agent holds open file descriptors there.
Caches regenerate on the next import; nothing is lost.

### Zero-byte junk at repo root
Removed with `git rm` (this commit): `⚠️`, `=2`, `=3`, `5`, `$.ci_run_id`, `$.regime_label`,
`temp_full_science_report.txt`, plus four empty `cqp_vote_*.txt` vote files. These are shell
redirect accidents — `> =2` instead of `2>`, `> $.ci_run_id` where `$CI_RUN_ID` was intended.

Deliberately kept:
- `__init__.py` — zero bytes, but added on purpose by PR #977, not an accident.
- the six `cqp_vote_*.txt` files that contain real vote output.
- four zero-byte root files whose names begin with a space (` Last`, ` Mutation`, ` Repo:`, ` Total:`)
  were transient — they disappeared between the audit and the deletion pass, recreated and removed
  by a live process. Nothing to delete.

### Follow-up worth doing
Whatever script writes `cqp_vote_*.txt` into the repo root should get those paths in `.gitignore`,
and its `$.ci_run_id` / `$.regime_label` redirects should be quoted (`"$CI_RUN_ID"`), otherwise the
junk returns and gets committed again.

---

## Pass 3 — stop the junk from coming back

### generator bug 1: `temp_full_science.py` wrote to a hardcoded Windows path
Both write sites used `open('E:/findtorontoevents_antigravity.ca/...')` for `docs/CHATWITHIT.md`
and `temp_full_science_report.txt`. On Windows that lands in the repo root; anywhere else it
silently creates a bogus `E:/` tree. Replaced with paths derived from
`Path(__file__).resolve().parent`, so output follows the checkout instead of one machine's drive
layout. Verified with `py_compile`.

### generator bug 2: no live generator for the other junk — so gitignore it at the root
`rg --no-ignore` over the whole tree (including gitignored dirs) found **zero** code that writes
`cqp_vote_*` or references `CI_RUN_ID`. The files came from ad-hoc shell loops run with
CWD = repo root, e.g. `llm ... > cqp_vote_$model.txt` and `> $.ci_run_id` with `$CI_RUN_ID`
unset (unset var → literal `$.ci_run_id` filename). There is no script to patch, so the durable
fix is a root-anchored ignore block:

```
/\$.*
/=*
/⚠️*
/ *
/cqp_vote_*.txt
/temp_full_science_report.txt
```

Verification — `git check-ignore -v` against synthetic probes:
- ` TestProbe` → matched `/ *` (leading-space names; these were tracked once)
- `=2` → matched `/=*`
- `$.ci_run_id` → matched `/\$.*`
- `cqp_vote_probe.txt` → matched `/cqp_vote_*.txt`
- `temp_full_science_report.txt` → matched the exact path
- `⚠️probe` → matched after widening `/⚠️` to `/⚠️*`

Negative controls (must NOT be ignored, and were not):
- `reports/cqp_vote_probe.txt` — `reports/CONSENSUS_QUICK_PICKS_2026-06-02.md` documents raw votes
  at `reports/cqp_vote_*.txt`, so the subdir name must stay usable.
- `tools/clean_git_history_comprehensive.sh` — no subdirectory file is swallowed.

All six probes were deleted after the check. Every pattern is `/`-anchored so it can only ever
match the repo root.
