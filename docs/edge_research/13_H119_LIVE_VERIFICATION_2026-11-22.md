# H-119 non-promotable flag: is it live, or merely pushed?

Date: 2026-11-22 · Verdict up front: **PUSHED, NOT LIVE.** The commit exists on
`origin/push/h119-nonpromotable` (`78b9794ad77775d72847913a851f1b00c38faaf5`) but is **not merged into
`origin/main`**, and `origin/main`'s H-119 entry carries no `promotable` key. "Pushed" and "live" are
different claims; this document does not conflate them.

All commands were run in `/home/eaguiar2015/findtorontoevents_antigravity.ca` on 2026-11-22.

## 1. The branch exists on origin

```
$ git ls-remote origin 'refs/heads/push/*'
68d887c864115a0de1d24aa7d7aebfe27e7726f9	refs/heads/push/edge-research-p0
78b9794ad77775d72847913a851f1b00c38faaf5	refs/heads/push/h119-nonpromotable
532413a292efc788597b7aaf885bb7f6383eddcb	refs/heads/push/n1-n8-research-integrity
```

Confirmed: `push/h119-nonpromotable` exists on origin at sha **`78b9794ad77775d72847913a851f1b00c38faaf5`**.

## 2. The commit contains only the H-119 hunk, in one file

```
$ git log --oneline -1 78b9794ad77
78b9794ad77 H-119: mark non-promotable (only this hunk; other authors' registry entries left unstaged)

$ git show --stat --oneline 78b9794ad77
78b9794ad77 H-119: mark non-promotable (only this hunk; other authors' registry entries left unstaged)
 reports/hypothesis_registry.json | 4 +++-
 1 file changed, 3 insertions(+), 1 deletion(-)

$ git diff-tree --no-commit-id --name-only -r 78b9794ad77
reports/hypothesis_registry.json
```

The actual diff hunk:

```
$ git show 78b9794ad77 -- reports/hypothesis_registry.json
commit 78b9794ad77775d72847913a851f1b00c38faaf5
Author: github-actions[bot] <eaguiar2015@users.noreply.github.com>
Date:   Sun Nov 22 11:42:14 2026 +0000

    H-119: mark non-promotable (only this hunk; other authors' registry entries left unstaged)
    ...

diff --git a/reports/hypothesis_registry.json b/reports/hypothesis_registry.json
index 2cb91a40571..b5157adedd8 100644
--- a/reports/hypothesis_registry.json
+++ b/reports/hypothesis_registry.json
@@ -1961,7 +1961,9 @@
    "registered_at": "2026-06-13",
    "data_sample_lock": "at_signal_outcomes intrabar, n=108 as of 2026-06-13 16:19Z",
    "result": "n=108: gross PF 1.53 ... (unchanged long line) ...",
-   "kill_reason": null
+   "kill_reason": null,
+   "promotable": false,
+   "promotable_reason": "Not a pod: reports/audit3_confirmatory.json has no pod for H-119, and forward_gate_block promotes only manifest pods (alpha_engine/audit3_tribunal.py:1603-1654) - non-pod hypotheses are reported under hypotheses[] and can never promote a cell. Marked non-promotable by the N3 orphan resolution 2026-11-22. Its 430 forward rows stay useful accruing evidence for the lead, but cannot gate a promotion; the same-date gate also fails on net PF CI-LB 0.9213<=1.0, IR 0.043<0.5, benchmark coverage 0.798<0.90."
   },
   {
    "id": "H-120",
```

Only `promotable` and `promotable_reason` are added to the H-119 entry, and `kill_reason` gains a trailing
comma. Nothing else in the file is touched by this commit.

## 3. The other authors' hypotheses are NOT in the commit

A JSON-level comparison of the parent blob against the committed blob:

```
$ git show 78b9794ad77^:reports/hypothesis_registry.json > /tmp/reg_parent.json
$ git show 78b9794ad77:reports/hypothesis_registry.json  > /tmp/reg_commit.json
$ python3 ...   # load both, index hypotheses by id, compare

parent entries 137 commit entries 137
ids added  : []
ids removed: []
entries changed: ['H-119']
   H-119 changed keys: ['promotable', 'promotable_reason']
     promotable = false
     promotable_reason = "Not a pod: reports/audit3_confirmatory.json has no pod for H-119, and forward_gate_block promotes only manifest pods (a...
top-level keys changed: []
```

Presence check of the other authors' ids (`committed` = in the commit blob, `worktree` = in the current
working-tree copy, which is the dirty one):

```
H-2026-11-20-01 committed=0 worktree=1
H-2026-11-20-02 committed=0 worktree=1
H-2026-11-20-03 committed=0 worktree=1
H-2026-11-20-04 committed=0 worktree=1
H-2026-11-20-05 committed=0 worktree=1
H-2026-11-20-06 committed=0 worktree=1
H-2026-11-22-COMMODITY-TREND10M committed=0 worktree=1
H-2026-11-22-EQUITY-TREND10M committed=0 worktree=1
H-144 committed=1 worktree=2
H-145 committed=1 worktree=2
H-146 committed=0 worktree=1
H-147 committed=0 worktree=1
H-148 committed=0 worktree=1
```

Note on H-144/H-145: `committed=1` is their *pre-existing* entry, present in the parent already (the JSON
diff above shows no ids added or removed). The `worktree=2` count is because another author added a second,
differently-scoped entry for each in the working tree. Those additions are not in the commit: the JSON diff
reports `ids added: []`.

The committed registry has **137** hypothesis entries (same as its parent); the dirty working-tree copy has
**116**. The two counts are not comparable as "others removed entries" — the working tree is a different,
concurrently edited snapshot, not a descendant of this commit's blob. What matters is the JSON diff:
against its own parent, the commit changed exactly one entry, H-119, and only its `promotable*` keys.

## 4. The ledger is untouched

The ledger file is [`reports/forward_observations.jsonl`](../../reports/forward_observations.jsonl) (432 rows;
`reports/audit3_ledger.json` does not exist in this repo). Expected md5 `fb4c12cf33fe18153661669df5540a55`:

```
$ md5sum reports/forward_observations.jsonl
fb4c12cf33fe18153661669df5540a55  reports/forward_observations.jsonl

$ sha256sum reports/forward_observations.jsonl
da3f416ba9e371722648baa4846f10049a66d444ba944f1af666592ca02bd8d6  reports/forward_observations.jsonl
```

**Matches** the pre-change value `fb4c12cf33fe18153661669df5540a55` in the working tree and at `HEAD`:

```
--- HEAD ---      fb4c12cf33fe18153661669df5540a55  -
--- worktree ---  fb4c12cf33fe18153661669df5540a55  reports/forward_observations.jsonl
```

The commit also did not change the ledger: the ledger blob at `78b9794ad77` is byte-identical to its parent
(both `dcd3228e5840900307275aedafa40408`, 447 rows). The working tree's copy differs from that
(`fb4c12cf...`, 432 rows) for unrelated reasons outside this commit.

## 5. Merged into main, or merely pushed?

**Merely pushed. Not merged.**

```
$ git ls-remote origin refs/heads/main
6f595416daa23282a008d9ac7391e1ad37cdf714	refs/heads/main

$ git fetch origin main && git merge-base --is-ancestor 78b9794ad77 origin/main; echo $?
NOT MERGED: 78b9794ad77 is NOT an ancestor of origin/main
```

And the flag is absent from main's registry:

```
$ git show origin/main:reports/hypothesis_registry.json | python3 ...
keys: ['acceptance_criteria', 'asset_class', 'data_sample_lock', 'description', 'economic_prior',
       'family', 'id', 'kill_reason', 'registered_at', 'result', 'status', 'test_statistic']
promotable: <absent>

$ git log origin/main --oneline -S 'promotable_reason' -- reports/hypothesis_registry.json
(no output)
```

`origin/main` is `8dc0fe805b1` (per the fetch above; the earlier `ls-remote` in this session saw `6f595416daa`
before the fetch). Either way: no commit carrying `promotable_reason` is on main.

## 6. Working-tree registry state

`reports/hypothesis_registry.json` is **not** dirty in this workspace:

```
$ git status --short -- reports/hypothesis_registry.json
(no output)
```

…yet its content differs from both the commit blob and `origin/main`'s blob (worktree md5
`8271dda12407af6db2e887c42270b8d5`; commit blob `b531001ebb0f61cc972bd1792c7d871b`; parent blob
`69e59c0531b4fc40e8d76a61db628d0d`). That means this workspace's HEAD already contains other agents'
registry edits, which are unrelated to this commit. The point stands regardless: **the on-origin state is
what matters**, and on origin the H-119 `promotable: false` flag exists only on the unmerged branch.

## Blunt answer

**Is it live? No. Is it pushed? Yes.** The H-119 non-promotable flag is on
`origin/push/h119-nonpromotable` at `78b9794ad77775d72847913a851f1b00c38faaf5`, a single-file commit that
changes only H-119's `promotable`/`promotable_reason`, with the ledger untouched
(`fb4c12cf33fe18153661669df5540a55`). It is not on `origin/main`, so any system reading main still sees
H-119 without the flag.
