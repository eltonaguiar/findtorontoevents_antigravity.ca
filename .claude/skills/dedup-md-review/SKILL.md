# Dedup .MD Review Skill

Use when you need to review a bunch of .MD files but avoid reviewing the same file twice.

## How it works

1. Walks the entire repo finding all `.md` files
2. Groups by SHA256 content hash (fallback: basename+size)
3. For duplicates, keeps the shortest path (prioritizes `reports/` root)

## Usage

```bash
# List unique .MD files (no duplicates)
python3 tools/dedup_md_review.py --list

# Show duplicate groups
python3 tools/dedup_md_review.py --report

# Show only files that have duplicates
python3 tools/dedup_md_review.py --dupes-only

# List unique files, git-ignored aware, output to file
python3 tools/dedup_md_review.py --list > unique_md_files.txt
```

## Output

- `--list`: one unique file path per line, sorted
- `--report`: groups of duplicates with count per SHA256 hash
- `--dupes-only`: only files that exist in ≥2 copies

## Known duplicates

The `.claude/worktrees/agent-*/reports/` directories contain mirrored copies of the canonical `reports/*.md` files. The canonical source is always the shortest path.
