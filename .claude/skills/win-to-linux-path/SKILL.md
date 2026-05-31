---
name: win-to-linux-path
description: Resolve a Windows path (or a whole pasted list of them) to the equivalent Linux file in this repo, verifying each exists on disk. Handles E:\findtorontoevents_antigravity.ca\... -> /home/eaguiar2015/findtorontoevents_antigravity.ca/..., maps .claude/.qwen worktree copies that only exist on Windows back to the main-tree file, fuzzy-matches by basename, and flags external paths (Program Files, AppData, other drives) that have no repo equivalent. Triggers - "/win-to-linux-path", "what's the linux path for E:\...", "convert these windows paths", "find the equivalent linux file(s)". Aliases - win2linux, winpath, w2l, windows-path.
---

# win-to-linux-path — Windows path → Linux file resolver

## When to use

- The user pastes one or many `E:\findtorontoevents_antigravity.ca\...` (or `C:\...`) paths and wants the file(s) **on this Linux box**.
- A tool/log/peer references a Windows path and you need to open the real file here.
- You need to know which pasted paths actually exist locally vs. which are Windows-only worktree copies or external (Program Files / AppData) paths with no equivalent.

## The mapping

| Windows | Linux |
|---|---|
| `E:\findtorontoevents_antigravity.ca\` | `/home/eaguiar2015/findtorontoevents_antigravity.ca/` |
| `\` separators | `/` separators |
| `E:\Program Files...`, `C:\Users\...\AppData\...`, other drives | **no equivalent** (external) |
| `...\.claude\worktrees\<id>\reports\foo.md` (often Windows-only) | mapped to the **main-tree** `reports/foo.md`, or a live `.qwen/worktrees/<id>/...` if present |

## How

Run the helper — it translates, verifies existence on disk, and falls back intelligently.
The script lives **inside this skill dir** (not `tools/`, which is a hot shared tree where
fresh untracked files get swept into a peer's `git stash -u` or branch switch). Set `SK` once:

```bash
SK=.claude/skills/win-to-linux-path/win2linux_path.py

# One or more paths as args (quote them — backslashes + spaces)
python3 "$SK" 'E:\findtorontoevents_antigravity.ca\reports\SUPREME_PLAN_90days.md'

# A pasted multi-line blob (the common case)
python3 "$SK" --from-file /tmp/winpaths.txt
cat /tmp/winpaths.txt | python3 "$SK" --from-stdin

# Only the resolved paths that exist, one per line (pipe into xargs/Read)
python3 "$SK" --from-stdin --exists-only

# JSON for downstream tooling
python3 "$SK" --from-file /tmp/winpaths.txt --json
```

When the user pastes a big list in chat, write it to a temp file (or pipe via stdin) and run with `--from-file` / `--from-stdin` rather than passing 200 args.

## Output legend

```
✓  /home/.../reports/SUPREME_PLAN_90days.md                exact translate, exists
✓~ /home/.../tools/generate_90day_plan_pages.py [WORKTREE] Windows worktree copy absent here → mapped to main tree
≈  E:\...\foo.md  + candidate: /home/.../reports/foo.md    no exact path; fuzzy basename match(es)
✗  would be: /home/.../reports/foo.md (does not exist)     translated cleanly but nothing on disk
—  EXTERNAL — no Linux equivalent in repo                  Program Files / AppData / other drive
```

Exit code `0` = every input resolved to an existing path; `3` = at least one was EXTERNAL / MISSING / fuzzy-only (expected when the list includes Program Files or AppData paths).

## Resolution order (per path)

1. **DIRECT** — `REPO_ROOT/<relpath>` exists.
2. **WORKTREE** — strip a `.claude|.qwen/worktrees/<id>/` prefix → the main-tree copy.
3. **WT_SWAP** — same subpath under any worktree dir that actually exists on this box.
4. **FUZZY** — search the repo by basename (skips `.git`, `node_modules`, `build`, …); returns shortest-path candidate first.
5. **EXTERNAL / MISSING** — outside the repo, or translated but absent.

## Notes

- The Windows checkout uses `.claude\worktrees\`; this Linux box uses `.qwen/worktrees/`. Worktree-scoped paths usually won't translate 1:1 — the tool deliberately falls back to the canonical main-tree file, which is almost always what you want to read.
- Repo root is hard-coded to `/home/eaguiar2015/findtorontoevents_antigravity.ca` in `win2linux_path.py`; edit the `REPO_ROOT` constant if the checkout moves.
- Related: `/dedup-md-files` (content-dedup a list once you've resolved the paths).
