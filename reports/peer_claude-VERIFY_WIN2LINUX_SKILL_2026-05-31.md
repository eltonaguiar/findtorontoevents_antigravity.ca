# Verify /win-to-linux-path Skill — 2026-05-31

## Verdict: **EXISTS** (fully functional, already merged via PR #395)

## Canonical Implementation

- **Skill manifest**: `.claude/skills/win-to-linux-path/SKILL.md`
- **Script**: `.claude/skills/win-to-linux-path/win2linux_path.py`
- **Merged**: commit `10013d10a` (PR #395 `claude/win-to-linux-path-skill`)

Note: `tools/win2linux_path.py` does **NOT** exist — the script lives under `.claude/skills/win-to-linux-path/` only. `tools/dedup_md_files.py` exists but is a separate concern (content-dedup of MD files; does not do Windows->Linux path normalization).

## Test (3 sample Windows paths)

Input:
```
E:\findtorontoevents_antigravity.ca\reports\SUPREME_PLAN_90days.md
E:\findtorontoevents_antigravity.ca\reports\asset_class_90day_plan_CRYPTO_2026-05-15.md
E:\findtorontoevents_antigravity.ca\.claude\worktrees\agent-a4e9a70f56bcd2a26\reports\SUPREME_PLAN_90days.md
```

Output:
```
[OK] /home/eaguiar2015/findtorontoevents_antigravity.ca/reports/SUPREME_PLAN_90days.md
[OK] /home/eaguiar2015/findtorontoevents_antigravity.ca/reports/asset_class_90day_plan_CRYPTO_2026-05-15.md
[OK~] /home/eaguiar2015/findtorontoevents_antigravity.ca/reports/SUPREME_PLAN_90days.md  [WORKTREE: worktree copy not present; mapped to main tree]

3/3 resolved to an existing path.
```

All 3 paths verified on disk. Worktree-copy fallback to main tree works as designed.

## Recommendation to Peer Claude

**Use the existing skill** — do NOT rebuild. Invoke as `/win-to-linux-path` or call the script directly:

```bash
python3 .claude/skills/win-to-linux-path/win2linux_path.py --from-file <paths.txt>
```

If peer has additional features (JSON output, basename fuzzy-match improvements, integration with dedup_md_files.py), those should land as a **patch on the existing `.claude/skills/win-to-linux-path/win2linux_path.py`**, not a new file at `tools/win2linux_path.py`. The skill location is canonical.

## Status flags

- skill_exists: **true**
- tools_script_exists: **false**
- test_passed: **true** (3/3 resolved including worktree fallback)
- recommendation: **use_existing**
