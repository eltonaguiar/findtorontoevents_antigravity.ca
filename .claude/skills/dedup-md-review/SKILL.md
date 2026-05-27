---
name: dedup-md-review
description: Content-dedup markdown paths before batch review — returns canonical (shortest-path) files so the same report is never read twice. Handles Windows E:\ paths, worktree copies, and stdin/file lists.
---

# /dedup-md-review — Review many .MD files without reading duplicates

## When to use

- User pastes 90+ paths including `reports/foo.md` AND `.claude/worktrees/agent-*/reports/foo.md`
- Before a swarm or EAGLE audit reads a batch of 90-day plans / gap analysis reports
- Auto-discovering reports across worktrees but only reading one copy each

## Preferred tool: `tools/dedup_md_files.py`

Byte-exact SHA-256 dedup. Shortest repo-relative path wins (canonical `reports/` over worktree copies).

### From a user-pasted Windows path list

```bash
cat <<'EOF' > /tmp/paths.txt
E:\findtorontoevents_antigravity.ca\reports\asset_class_90day_plan_BOND_2026-05-15.md
E:\findtorontoevents_antigravity.ca\.claude\worktrees\ipo-backtest\reports\asset_class_90day_plan_BOND_2026-05-15.md
EOF

python3 tools/dedup_md_files.py --from-file /tmp/paths.txt
```

### Auto-discover 90-day plans

```bash
python3 tools/dedup_md_files.py \
  --glob 'reports/asset_class_90day_plan_*.md' \
  --glob 'reports/90day_gap_analysis_2026-05-15.md' \
  --glob '.claude/worktrees/**/reports/asset_class_90day_plan_*.md'
```

### JSON output (pipe to review scripts)

```bash
python3 tools/dedup_md_files.py --from-file /tmp/paths.txt --json \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(x['canonical'] for x in d['canonical']))"
```

### Stdin (paste paths directly)

```bash
python3 tools/dedup_md_files.py --from-stdin <<'EOF'
reports/foo.md
.claude/worktrees/agent-abc/reports/foo.md
EOF
```

## Alternate: repo-wide walk (`tools/dedup_md_review.py`)

Use when you don't have an explicit path list — walks entire repo:

```bash
python3 tools/dedup_md_review.py --list          # unique paths only
python3 tools/dedup_md_review.py --report        # show duplicate groups
python3 tools/dedup_md_review.py --dupes-only    # files with ≥2 copies
```

## Output interpretation

```
CANONICAL (9 unique of 81 input):
  reports/90day_gap_analysis_2026-05-15.md                 (9 copies)
  ...
DUPLICATES SUPPRESSED: 72
```

- **Shortest path** = canonical (tiebreak: lexicographic)
- If two copies differ by even one byte, both appear as separate canonicals (intentional)
- Missing paths reported separately; run does not crash

## Workflow for EAGLE / strategy audits

1. Run dedup on the pasted path list → get 9 canonical paths
2. Read **only** canonical paths under `reports/`
3. Cross-reference live data: `audit_dashboard/data/money_ready_verdict.json`, `incidents_enhancements_feed.json`
4. Never cite worktree copy paths in deliverables — always cite shortest `reports/` path

## Related

- `.claude/skills/dedup-md-files/SKILL.md` — alias skill, same underlying script
- `tools/dedup_md_files.py` — primary (content hash + Windows path normalize)
- `tools/dedup_md_review.py` — repo walk variant
