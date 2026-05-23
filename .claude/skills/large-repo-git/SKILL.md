---
name: large-repo-git
description: Safe, fast git operations for large repositories that time out on naive commands. Covers: status, fetch, diff, log, sync-from-remote, find-files, and avoid-kills. Use when any git operation is slow, killed, or timing out. Aliases - bigrepo, git-fast, repo-sync, git-safe, large-repo
---

# large-repo-git — Fast git for large repos

This repo is large (~18MB dashboard JSON, 200+ strategy files, coinglass DB, binary assets). Naive commands like `git status -uall`, `find /mnt/c/...`, and `git fetch` without `--depth` will time out or get killed. This skill is the safe replacement for every common git operation.

---

## Rule #1 — Never use these commands on this repo

| ❌ Dangerous (will kill/timeout) | ✅ Safe replacement |
|----------------------------------|---------------------|
| `git status -uall` | `git status --short` (no `-u` flag) |
| `find /mnt/c/... -type f` | `git ls-files --others --exclude-standard \| head -20` |
| `find . -name "*.py"` | `git ls-files "*.py" \| head -30` |
| `git diff` (full) | `git diff --stat` then `git diff -- <specific_file>` |
| `git log` (no limit) | `git log --oneline -10` |
| `git fetch` (full) | `git fetch --depth=1 origin main` |
| `git clone` (full) | `git clone --depth=1 --filter=blob:none` |
| `grep -r pattern .` | `git grep pattern` (respects .gitignore, faster) |
| `wc -l` on large files | `head -5 file` + `git show --stat HEAD:file` |
| `git diff HEAD~50` | `git diff HEAD~5 --stat` (always bound the range) |

---

## Rule #2 — WSL path discipline

When running from WSL (`/mnt/c/...` paths), the Windows filesystem is 10-30× slower than native Linux paths. Symptoms: `Task killed in 1m26s`, `Task killed in 2m0s`.

```bash
# BAD — WSL accessing Windows FS, slow
cd /mnt/c/findtorontoevents_antigravity.ca && git status

# GOOD — same thing, explicit timeout awareness
cd /mnt/c/findtorontoevents_antigravity.ca && timeout 20 git status --short
```

If you repeatedly hit kills, the agent should be running from the **Windows side** (PowerShell / cmd), not WSL. Native Windows git is faster on this repo.

---

## Status (safe)

```bash
# What's modified (tracked files only — fast)
git status --short

# Staged vs unstaged counts only
git diff --name-only | wc -l
git diff --cached --name-only | wc -l

# Untracked sample (first 10 only — never drain all)
git ls-files --others --exclude-standard | head -10
```

---

## Fetch / Pull (safe)

```bash
# Shallow fetch — gets latest without full history download
git fetch --depth=1 origin main

# Fast-forward pull (no rebase drama, no merge commit)
git pull --ff-only origin main

# Full safe sync sequence (stash → pull → pop)
git stash && git pull --rebase origin main && git stash pop

# Check how far behind we are WITHOUT fetching
git rev-list --count HEAD..origin/main   # requires prior fetch
```

---

## Diff (safe)

```bash
# What changed — stats only first
git diff --stat
git diff --cached --stat

# Then drill into one file
git diff -- path/to/specific_file.py

# Compare to origin without full fetch
git diff HEAD origin/main --stat   # after fetch --depth=1
```

---

## Log (safe)

```bash
# Recent commits
git log --oneline -10

# Since a specific date (avoids full history traversal)
git log --oneline --since="2 days ago"

# Changes in one file
git log --oneline -5 -- audit_trail/quality_gates.py

# Commits ahead of origin
git log --oneline origin/main..HEAD
```

---

## Find files (safe)

```bash
# Find tracked Python files (fast — uses git index)
git ls-files "*.py" | head -30

# Find tracked files containing a pattern (fast — uses git index)
git grep -l "BLOCKED_ASSET_STRATEGY_PAIRS" | head -20

# Find recently modified tracked files
git diff --name-only HEAD~5

# Find untracked files (sample only)
git ls-files --others --exclude-standard | head -20
```

---

## Sync from remote (full workflow)

Use this instead of any ad-hoc fetch+pull sequence:

```bash
# 1. Check if we need to pull at all
git fetch --depth=1 origin main
git rev-list --count HEAD..origin/main   # 0 = already up to date

# 2. If behind, safe pull
git stash
git pull --rebase origin main
git stash pop

# 3. Verify
git log --oneline -3
```

---

## Push (safe)

```bash
# Always unset stale GITHUB_TOKEN first (this repo has a known expired PAT in env)
unset GITHUB_TOKEN

# Push
git push origin main

# If rejected (remote has new commits):
git stash && git pull --rebase origin main && git stash pop && git push origin main
```

**Known issue on this repo:** `GITHUB_TOKEN` env var may contain an expired PAT (`github_pat_11AJHZILQ...`). Always `unset GITHUB_TOKEN` before push. If `gh auth status` shows the env var token, run `Remove-Item Env:GITHUB_TOKEN` in PowerShell (or `unset GITHUB_TOKEN` in bash) to fall back to the keyring token.

---

## Commit (safe)

```bash
# Add specific files only — never `git add -A` on this repo
# (coinglass.db, dashboard_data.json, binary assets will bloat the commit)
git add path/to/specific_file.py path/to/another_file.md

# Commit with heredoc (avoids quoting issues)
git commit -m "$(cat <<'EOF'
feat(scope): what changed and why

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Large file traps to avoid

| File | Size | Why dangerous |
|------|------|---------------|
| `audit_dashboard/data/dashboard_data.json` | ~18MB | Never `cat` — use `python -c "import json; d=json.load(open(...))"` with targeted key access |
| `coinglass_strategies/data/coinglass.db` | ~27MB | Binary — never diff, never cat |
| `audit_dashboard/index.html` | ~4MB | Auto-generated — never edit |
| `logs/cross_pc_protocol/events.jsonl` | Growing | Tail only: `tail -20 logs/...` |

Read large JSON files with targeted key access:

```bash
python -c "
import json
from pathlib import Path
d = json.loads(Path('audit_dashboard/data/dashboard_data.json').read_text(encoding='utf-8'))
# Access only what you need:
print(d.get('generated_at'))
print(list(d.get('performance', {}).get('asset_class_health', {}).keys()))
"
```

---

## When commands are killed — diagnosis

If a command is killed (Task killed in Xs), work through this checklist:

1. **Add `timeout N`** — wrap command: `timeout 15 git status --short`
2. **Check if running in WSL on Windows FS** — if path is `/mnt/c/...`, move to PowerShell
3. **Scope the command** — add `| head -N` or `-- specific_file` to limit output
4. **Avoid `find`** — use `git ls-files` instead
5. **Avoid unscoped `git diff`** — always add `--stat` first, then drill into one file
6. **Check if large file is being read** — check if the killed command touches the 18MB dashboard JSON or 27MB DB

---

## Companion skills

- `/check-gh-actions` — verify CI after push
- `/cross-pc-health` — gateway pre-flight
- `/large-repo-read` — safe read patterns for large JSON/log files (see below)
