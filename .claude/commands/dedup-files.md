---
description: Find duplicate / near-duplicate files in a set and emit the minimal review set (shortest path per content cluster) so you don't review the same content twice.
---

Detect duplicate files so review effort isn't wasted on identical/near-identical copies.

Wraps `tools/dedup_files.py`. Full guidance: `.claude/skills/dedup-files/SKILL.md`.

Arguments in `$ARGUMENTS` = the files/dirs/globs to scan (and any flags). If empty, ask the user what set of files to dedup.

1. **Run from repo root.** Default to exact (SHA-256) mode:
   ```bash
   python tools/dedup_files.py $ARGUMENTS
   ```
   - Dirs need `--recurse` to walk. Many pasted paths → pipe them: `... --from-file -`.
   - Reformatted/near-dups → add `--similar [--threshold 0.85]` (refuses >2000 files; that's O(n²)).
   - Scriptable minimal list → `--review-set` (one path per line). Machine output → `--json`.

2. **Report** the duplicate groups, the `<- canonical (shortest path)` pick per group, and the **minimal review set** (canonical per cluster + every unique file). Exit code 1 = dups found, 0 = all unique.

3. **Recommend** reviewing only the minimal set; note skipped copies as "duplicate of <canonical>". For near-dups, remind the user only exact mode is a hard guarantee — eyeball flagged similars.
