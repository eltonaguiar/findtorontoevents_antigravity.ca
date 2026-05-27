# md-dedup — Deduplicate .MD Files Across Worktrees
**Skill:** `/md-dedup`
**Purpose:** When given a list of .md file paths (potentially with duplicates across `.claude/worktrees/` or other directories), quickly identify unique files and select the shortest path for each unique file. Never read the same file content twice.

---

## When to Use
- User provides a long list of file paths (E:\ or /mnt/ based) with potential duplicates across worktrees
- User wants to "review a bunch of .MD but quickly avoid reviewing the same file twice"
- Need to identify the canonical (shortest-path) copy of each unique file

## Algorithm

### Step 1: Parse and Normalize Paths
1. Strip Windows drive letters: `E:\` → `/mnt/e/`, `C:\` → `/mnt/c/`
2. Normalize to absolute workspace paths
3. Group files by basename (filename without directory path)

### Step 2: Identify Duplicates
For each group of files sharing a basename:
1. Compute SHA256 hash of **first 500 bytes** of each file
2. Also check **file size** (quick proxy for identity)
3. Files with matching hash AND matching size → TRUE DUPLICATES
4. Files with matching basename but different hash/size → VARIANTS (different content, flag separately)

### Step 3: Select Canonical Path
For each group of true duplicates:
1. **Keep the shortest path** (fewest characters = closest to root, usually `reports/` over `.claude/worktrees/agent-xxx/`)
2. If shortest path is `reports/` → that's the canonical version
3. If worktree path is shorter (unlikely but handle) → note as non-canonical
4. Drop all other paths

### Step 4: Output
```
## Unique Files (no duplicates found)
- /mnt/e/findtorontoevents_antigravity.ca/reports/file_A.md
- /mnt/e/findtorontoevents_antigravity.ca/reports/file_B.md

## Deduplicated (one kept, rest dropped)
- KEPT:   reports/asset_class_90day_plan_CRYPTO_2026-05-15.md
- DROP:   .claude/worktrees/agent-xxx/reports/asset_class_90day_plan_CRYPTO_2026-05-15.md
- DROP:   .claude/worktrees/agent-yyy/reports/asset_class_90day_plan_CRYPTO_2026-05-15.md

## Variants (same basename, different content — DO NOT deduplicate)
- /mnt/.../file_X.md (2048 bytes, hash: abc123)
- /mnt/.../file_X.md (2100 bytes, hash: def456)

## STATS
- Total input files: 72
- Unique files: 18
- Duplicates removed: 54
- Variants (flagged): 0
- Files to review: 18
```

## Implementation

```python
import os
import hashlib
import glob as glob_module

def md_dedup(paths_or_patterns, workspace_root=None):
    """
    Deduplicate .md files across provided paths.
    
    Args:
        paths_or_patterns: list of file paths or glob patterns
        workspace_root: optional base directory for normalization
    
    Returns:
        dict with keys: unique, deduped, variants, stats
    """
    if workspace_root is None:
        workspace_root = os.getcwd()
    
    # Step 1: Expand globs, parse all paths
    all_files = []
    for p in paths_or_patterns:
        # Normalize Windows paths
        p = p.replace('E:\\', '/mnt/e/').replace('C:\\', '/mnt/c/')
        if '*' in p or '?' in p:
            expanded = glob_module.glob(p, recursive=True)
            all_files.extend(expanded)
        elif os.path.isfile(p):
            all_files.append(p)
    
    all_files = sorted(set(all_files))
    
    # Step 2: Group by basename
    basename_groups = {}
    for f in all_files:
        basename = os.path.basename(f)
        basename_groups.setdefault(basename, []).append(f)
    
    # Step 3: Hash + compare
    def file_fingerprint(path):
        try:
            size = os.path.getsize(path)
            with open(path, 'rb') as fh:
                head = fh.read(500)
            h = hashlib.sha256(head).hexdigest()
            return (size, h)
        except Exception:
            return None
    
    unique = []
    deduped = {'kept': [], 'dropped': []}
    variants = []
    
    for basename, paths in basename_groups.items():
        if len(paths) == 1:
            unique.append(paths[0])
            continue
        
        # Group by fingerprint
        fp_groups = {}
        for p in paths:
            fp = file_fingerprint(p)
            if fp is None:
                continue
            fp_groups.setdefault(fp, []).append(p)
        
        for fp, group in fp_groups.items():
            if len(group) == 1:
                unique.append(group[0])
            elif len(group) > 1:
                # Sort by path length (shortest first = canonical)
                group.sort(key=len)
                deduped['kept'].append(group[0])
                deduped['dropped'].extend(group[1:])
        
        # Check for variants (same basename, different content)
        if len(fp_groups) > 1:
            variants.append({basename: [p for group in fp_groups.values() for p in group]})
    
    return {
        'unique': sorted(set(unique)),
        'deduped': deduped,
        'variants': variants,
        'stats': {
            'total_input': len(all_files),
            'unique': len(set(unique)),
            'kept': len(deduped['kept']),
            'dropped': len(deduped['dropped']),
            'variants': len(variants),
            'files_to_review': len(set(unique)) + len(deduped['kept']) + sum(len(v.get(k, [])) for v in variants for k in v if v.get(k))
        }
    }
```

## Usage Examples

### Basic: Dedup a list of paths
```
/md-dedup reports/asset_class_90day_plan_*
/md-dedup reports/ .claude/worktrees/agent-*
```

### From user-provided E:\ paths
User pastes a list like:
```
E:\findtorontoevents_antigravity.ca\reports\90day_gap_analysis_2026-05-15.md
E:\findtorontoevents_antigravity.ca\.claude\worktrees\ipo-backtest\reports\90day_gap_analysis_2026-05-15.md
```

→ Parse: normalize to `/mnt/e/findtorontoevents_antigravity.ca/...`
→ Hash both: same content?
→ KEEP: `reports/90day_gap_analysis_2026-05-15.md` (shorter path)
→ DROP: `.claude/worktrees/ipo-backtest/reports/...` (worktree copy)

### For the user's specific case
The user listed ~80 paths across 9+ worktrees. The 9 reports/ files are unique (no true duplicates found in the canonical repo — the `.claude/worktrees/` may not exist locally or files are already deduped). The skill handles both cases:
- **Worktrees exist locally**: True dedup via hash comparison
- **Worktrees don't exist locally**: Reports are already unique — output is all 9 reports/ paths

## Edge Cases
- **Binary files**: `file_fingerprint` returns None → skip
- **Large files**: Only hash first 500 bytes + size → fast, minimal I/O
- **Empty files**: size=0 hash=empty string → handled correctly
- **Permission errors**: fingerprint returns None → skip gracefully

## Integration
- Works with `read_multiple_files` after dedup to read only canonical paths
- Works with `glob` to expand patterns before dedup
- Output format is directly usable as a file list for further processing
