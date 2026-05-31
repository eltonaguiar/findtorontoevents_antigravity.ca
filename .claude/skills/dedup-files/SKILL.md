---
name: dedup-files
description: Use when handed a SET of files to review/audit and you want to avoid reviewing the same content twice — finds byte-identical and near-identical (reformatted/lightly-edited) files so you review one representative per cluster. Triggers — "/dedup-files", "are these files duplicates", "check file hashes for dups", "which of these are the same", "dedup before review", "find duplicate reports/docs". Aliases — dedup, dup-check, dedup-review, file-dups.
---

# dedup-files — duplicate detector to avoid double-reviewing

This repo is a storm-commit firehose of `reports/*.md`, `updates/*.md`, deep-dive
docs, and generated artifacts. Many are byte-identical copies or lightly-edited
reformats of each other. Reviewing two copies of the same content is wasted
effort. This skill groups a file set into duplicate clusters so you review **one
representative per cluster**.

Tool: `tools/dedup_files.py` (stdlib-only, zero deps, cross-platform).

## Two modes

| Mode | Flag | What it catches | How |
|------|------|-----------------|-----|
| exact | *(default)* | byte-for-byte identical files | SHA-256 (size-bucketed first, so it's fast) |
| similar | `--similar` | reformatted / whitespace / lightly-edited dups | normalized-token Jaccard overlap `>= --threshold` (default 0.90) |

Start with **exact** (unambiguous, instant). Escalate to **similar** when you
suspect reformatted copies (e.g. the deleted `md-dedup` family of docs).

## Steps

1. **Run from repo root** so relative globs resolve:
   ```bash
   python tools/dedup_files.py reports/*.md                  # exact dups
   python tools/dedup_files.py --recurse reports/ updates/   # recurse dirs
   python tools/dedup_files.py --similar --threshold 0.85 docs/   # near-dups
   ```
   Inputs can be files, dirs, or globs — mixed freely. `--recurse` walks dirs.
   For a big pasted list of paths, pipe it in: `... --from-file -` (or
   `--from-file paths.txt`).

2. **Read the clusters.** Each `[n]` block is one duplicate group, and the
   shortest path in each is tagged `<- canonical (shortest path)`. In `--similar`
   mode the `~ score` lines show pairwise overlap so you can sanity-check the
   threshold.

3. **Review the minimal set.** The footer prints the **minimal review set** =
   the canonical (shortest-path) file per duplicate group + every unique file.
   Review only those; note the skipped copies as "duplicate of <canonical>".
   For just that list (one path per line, scriptable): add `--review-set`.

4. **`--json`** for machine consumption (includes `groups[].canonical` and the
   `review_set`). Exit code **1** if any duplicate group found, **0** if all
   unique — chains as a gate: `python tools/dedup_files.py ... && echo "all unique"`.

### Shortest-path / canonical selection

When the same file exists in dozens of places (e.g. `TESTING_PROTOCOL.MD` copied
into every `.worktrees/agent-xxxx/`), the canonical pick is the one with the
**fewest path components, then shortest string** — i.e. the repo-root copy, not a
deep worktree copy. `--review-set` collapses all those copies to that one path so
you review the source of truth once. Example:
```bash
# 80 TESTING_PROTOCOL.MD copies across worktrees -> the few real distinct files
python tools/dedup_files.py --from-file paths.txt --review-set
```

## When NOT to use

- Finding duplicate *code logic* across functions — that's a refactor concern,
  use graphify / code search, not file hashing.
- Comparing two specific files line-by-line — use `git diff --no-index a b`.
- Deduping data rows inside one file — out of scope.

## Caveats (validated by deepseek + xai second-opinion)

- **similar mode is O(n²)** in pairwise comparisons. The tool **refuses** over
  `--max-similar` files (default 2000); narrow inputs or raise the cap. Exact
  mode is cheap (size-bucketed, hashes only same-size files) — no such limit.
- Token Jaccard ignores order and structure — two docs with the same vocabulary
  but opposite conclusions can score high. **Always eyeball flagged near-dups**
  before declaring them redundant; only **exact mode is a hard guarantee**.
- `--threshold`: 0.95+ ≈ trivial reformats only; 0.80 ≈ same topic, different
  wording (more false positives). Tune per batch.
- **Binary files** are auto-skipped in similar mode (null-byte sniff) so they
  don't false-cluster; exact mode hashes them fine.
- **Symlinks are skipped** during dir traversal (avoids cycles + link/target
  double-count). **Hardlinks** and **empty files** legitimately hash-collide and
  WILL be grouped — expected for audit dedup, just be aware.
- Read failures (perms, races) are skipped silently, not crashed.
