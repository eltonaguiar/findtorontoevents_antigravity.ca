---
name: dedup-md-files
description: Content-dedup a list of markdown paths (handles many worktree copies of the same report). Returns the canonical (shortest-path) file per unique content hash so a reviewer doesn't read the same .md N times.
---

# /dedup-md-files — Get the canonical set of unique .md paths

## When to use

- The user pasted a long list of `.md` paths that includes `reports/foo.md` AND many `.claude/worktrees/agent-*/reports/foo.md` copies.
- Before reading a batch of report files, you want to skip duplicates.
- Auto-discovering reports across worktrees but only reading one copy each.

## How

The skill wraps `tools/dedup_md_files.py` which:
1. Normalizes Windows backslash paths + drive letters to repo-relative POSIX paths.
2. SHA-256 hashes each file's content.
3. Groups by hash; for each group, picks the **shortest path** as canonical (tiebreak lexical).
4. Returns one line per canonical file with its `(N copies)` count.

## Invocation

**From a user-pasted Windows path list** (typical case):

```bash
cat <<'EOF' > /tmp/paths.txt
E:\findtorontoevents_antigravity.ca\reports\asset_class_90day_plan_BOND_2026-05-15.md
E:\findtorontoevents_antigravity.ca\.claude\worktrees\ipo-backtest\reports\asset_class_90day_plan_BOND_2026-05-15.md
... (etc)
EOF

python3 tools/dedup_md_files.py --from-file /tmp/paths.txt
```

**Auto-discover all 90-day plan files across worktrees:**

```bash
python3 tools/dedup_md_files.py \
  --glob 'reports/**/*.md' \
  --glob '.claude/worktrees/**/reports/**/*.md'
```

**JSON mode (pipe to another tool):**

```bash
python3 tools/dedup_md_files.py --from-file /tmp/paths.txt --json | jq -r '.canonical[].canonical'
```

**Paths-only mode (direct canonical file list, one per line):**

```bash
python3 tools/dedup_md_files.py --from-file /tmp/paths.txt --paths-only
```

## What "shortest path" means

Given identical content at:
- `reports/foo.md` (12 chars)
- `.claude/worktrees/agent-abc/reports/foo.md` (44 chars)

The skill picks `reports/foo.md`. Worktree copies are demoted automatically because they have longer paths. If two non-worktree copies tie, the lexicographically-smaller one wins (deterministic).

## Output

```
CANONICAL (9 unique of 81 input):
  reports/90day_gap_analysis_2026-05-15.md                 (9 copies)
  reports/asset_class_90day_plan_BOND_2026-05-15.md        (9 copies)
  reports/asset_class_90day_plan_COMMODITY_2026-05-15.md   (9 copies)
  reports/asset_class_90day_plan_CRYPTO_2026-05-15.md      (9 copies)
  reports/asset_class_90day_plan_EQUITY_2026-05-15.md      (9 copies)
  reports/asset_class_90day_plan_ETF_2026-05-15.md         (9 copies)
  reports/asset_class_90day_plan_FOREX_2026-05-15.md       (9 copies)
  reports/asset_class_90day_plan_FUTURES_2026-05-15.md     (9 copies)
  reports/asset_class_90day_plan_PENNY_MEME_2026-05-15.md  (9 copies)

DUPLICATES SUPPRESSED: 72
```

## Notes

- The dedup is **byte-exact** (SHA-256). If two worktrees diverged the .md content even by a single space, they will appear as separate canonicals — that's intentional. Use `--show-dupes` to inspect groupings.
- Windows path normalization handles `E:\path\with\spaces.md` and `C:/forward/slashes.md` both.
- Missing/unreadable paths are reported separately (don't crash the run).
