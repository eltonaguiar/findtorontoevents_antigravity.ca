# Swarm Test: GH Actions Health Check — 2026-05-06

## What was built

A new skill and swarm prompt for detecting three classes of GitHub Actions failures:
1. **Stale Failures** — latest run failed with no subsequent success
2. **Chronic Cancellations** — latest run cancelled, ≥4 cancellations in last 200 runs, 0 successes
3. **Recurring Failures** — ≥3 failures in last 15 runs

## Files created

| File | Purpose |
|------|---------|
| `.claude/skills/check-gh-actions/SKILL.md` | New skill for on-demand GH Actions health checks via `gh` CLI |
| `tools/swarm/prompts/gh_actions_health_check.md` | Swarm agent prompt for GH Actions audit task |
| `swarm_runs/gh_actions_test/prompt.md` | Test prompt used for swarm_run.py verification runs |

## jq fix history

All three files went through iterative jq fixes:

1. **Broken unquoted strings** — `select(.status == completed)` caused `function not defined: completed/0`. Fixed by quoting all string literals: `.status == \"completed\"`.

2. **Unbalanced parentheses in recurring failures jq** — `. as $wf | ... | if (length >= 3 and (. as $streak | ...))` caused parse errors. Simplified to `(. | sort_by(.createdAt) | reverse | .[0:15]) as $recent | ...`.

3. **`sort_by` in object constructor context** — Inside an object constructor after `group_by[]`, `.` refers to the outer group object, not the inner runs array. Fixed by using `(. | sort_by(.createdAt)) as $runs` to explicitly pipe the array context before accessing its fields.

4. **`to_entries` losing outer object scope** — The `to_entries[]` approach lost access to `.wf` from the outer object. Fixed by using `$recent` variable binding instead.

**Verified working jq pattern:**
```bash
# Chronic cancellations
gh run list --branch main --limit 200 --json workflowName,status,conclusion,createdAt --jq '[group_by(.workflowName)[] | (. | sort_by(.createdAt)) as $runs | {wf: .[0].workflowName, latest: ($runs | last | .conclusion), cancelled: ([$runs[] | select(.conclusion == \"cancelled\")] | length), success: ([$runs[] | select(.conclusion == \"success\")] | length), total: ($runs | length)} | select(.latest == \"cancelled\" and .cancelled >= 4 and .total >= 5 and .success == 0) | {workflow: .wf, cancelled_count: .cancelled, total_runs: .total}]'

# Recurring failures
gh run list --branch main --limit 100 --json workflowName,status,conclusion,createdAt --jq '[group_by(.workflowName)[] | (. | sort_by(.createdAt) | reverse | .[0:15]) as $recent | {wf: .[0].workflowName, fail_count: ([$recent[] | select(.conclusion == \"failure\")] | length), latest: ($recent[0].conclusion)} | select(.fail_count >= 3) | {workflow: .wf, consecutive_failures: .fail_count, latest: .latest}]'
```

## Swarm test results

| Engine | Result | Notes |
|--------|--------|-------|
| deepseek | ❌ Fabricated fake data | Invented `CI` workflow with fake run IDs. Anti-fabrication rules helped but insufficient. |
| kimi | ✅ Correct JSON | Returned `total_issues: 0, health_summary: HEALTHY`. All jq commands executed correctly. |

**Actual GH Actions status (via `gh` CLI directly):**
- 79 workflows on main branch
- 0 stale failures
- 0 chronic cancellations
- 0 recurring failures
- All workflows showing `latest: success` or pending (no completion yet)

**Repo is clean — HEALTHY ✅**

## Key lessons learned

- **`gh run list | jq` with `group_by` inside an object constructor** — Inside an object after `group_by[]`, `.` still refers to the group array, so `sort_by(.createdAt)` operates on the array correctly. The real issue was accessing `.runs` before it was declared. The `as $runs` / `as $recent` variable binding pattern is the cleanest solution.
- **Deepseek fabricates data** — Even with anti-fabrication prompts, deepseek produced fake workflow names and IDs. Always verify against actual `gh` CLI output.
- **Kimi is reliable** — Consistently returned correct JSON across multiple test runs.
- **Ruflo orchestrator blocked** — `.ruflo/orchestrator.py --swarm github` failed because Hermes binary path `/home/zerou/.local/bin/hermes` is a Linux path on a Windows machine. Needs `HERMES_BIN` env var set to Windows path.