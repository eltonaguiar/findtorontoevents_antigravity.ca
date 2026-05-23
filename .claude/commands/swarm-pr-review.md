---
description: Multi-model PR review swarm. Get 3 specialists to review open PRs, find issues one model would miss, then let Claude decide.
argument-hint: [PR#|all|open] [--consensus]
---

User invoked `/swarm pr-review $ARGUMENTS`.

## Parse arguments

- **empty or `open`** → Review ALL open PRs
- **`all`** → Review all open PRs + last 5 closed PRs
- **`<number>`** → Review specific PR (e.g., `845`)
- **`--consensus`** → Also run a consensus synthesis pass after reviews

## Workflow (this is THE primary daily workflow)

```
  ┌─────────────────┐
  │  1. LIST PRs     │  gh pr list --state open
  └────────┬────────┘
           │
  ┌────────▼────────┐
  │  2. SWARM REVIEW │  3 specialists × each PR
  │     - Mercury    │  Architecture, UX, structure
  │     - Grok       │  Cost, risk, quantitative impact
  │     - Claude     │  Data flow, docs, integration
  └────────┬────────┘
           │
  ┌────────▼────────┐
  │  3. CONSENSUS    │  What did 2+ specialists agree on?
  │     Report       │  What are the disagreements?
  └────────┬────────┘
           │
  ┌────────▼────────┐
  │  4. SMART AGENT  │  A stronger model (Claude/kilo)
  │     DECIDES      │  reviews consensus + diffs
  │                  │  then recommends: merge / fix / close
  └─────────────────┘
```

## Step 1: Get PR list

```bash
gh pr list --state open --json number,title,author,url,headRefName --limit 20
```

If `$ARGUMENTS` is a number, filter to just that PR.

## Step 2: Swarm review each PR

For EACH open PR, deploy 3 parallel specialists via `delegate_task`:

**Agent 1 — Mercury (Architecture/UX):**
```
Context: "You are Mercury-v1, an architecture and code quality specialist.
Review PR #[N] for: code structure, naming conventions, test coverage,
maintainability, and potential regressions.

PR Title: [title]
Branch: [branch]

Read the diff with: gh pr diff [N]

Workspace: /mnt/c/findtorontoevents_antigravity.ca/

Output JSON only:
{
  'pr': N,
  'specialist': 'mercury',
  'verdict': 'approve|request_changes|needs_discussion',
  'issues': [{'severity': 'critical|high|medium|low', 'file': 'path', 'line': N, 'comment': 'text'}],
  'summary': 'one paragraph overall assessment'
}"
Goal: "Review PR #[N] architecture and code quality"
Role: leaf
Toolsets: ["terminal", "file"]
```

**Agent 2 — Grok (Cost/Risk/Quant):**
```
Same structure but focus on: performance impact, cost implications,
security risks, data integrity, error handling, edge cases.
```

**Agent 3 — Claude (Data/Docs/Integration):**
```
Same structure but focus on: documentation gaps, integration patterns,
data flow correctness, API contract changes, backward compatibility.
```

Batch PRs: if there are 6 open PRs, process them in groups of 3
(each group = 3 agents, so 3 concurrent delegate_task calls).

## Step 3: Consensus report

After all specialists report, build a consensus table:

```
PR REVIEW CONSENSUS REPORT
═══════════════════════════

PR #845 — "Add memo coin resolver"
  Mercury: APPROVE    — clean architecture, good test coverage
  Grok:    APPROVE    — low risk, good error handling
  Claude:  APPROVE    — docs updated, integration clean
  CONSENSUS: 3/3 APPROVE → Safe to merge ✓

PR #844 — "Fix audit dashboard"
  Mercury: REQUEST_CHANGES — missing tests for new code path
  Grok:    APPROVE    — no security issues, low risk
  Claude:  REQUEST_CHANGES — breaking change to /api/audit endpoint
  CONSENSUS: 2/3 REQUEST_CHANGES → Needs fixes before merge ✗
  Issues:  - Missing tests (Mercury)
           - Breaking API change (Claude)

PR #843 — "Update swarm orchestrator"
  Mercury: APPROVE
  Grok:    NEEDS_DISCUSSION — potential memory leak in continuous mode
  Claude:  APPROVE
  CONSENSUS: 2/3 APPROVE, 1 flag → Merge with caution ⚠
  Flag: memory leak concern from Grok — needs manual inspection
```

## Step 4: Smart agent decision

After consensus, invoke ONE stronger model to make the final call:

```bash
python tools/swarm/swarm_run.py \
    --prompt-file tools/swarm/prompts/pr_review_batch.md \
    --engines claude \
    --out-dir swarm_runs/pr-decision-$(date -u +%Y%m%dT%H%M%SZ)
```

The smart agent gets:
- All specialist reports
- The actual PR diffs
- The consensus summary
- Instructions: "Based on specialist consensus + your own review,
  recommend: MERGE, REQUEST_CHANGES, or CLOSE for each PR.
  If consensus is 3/3 APPROVE, you can merge directly.
  If any specialist flagged REQUEST_CHANGES, explain what needs fixing."

## Output

After the full pipeline, show:

1. **Consensus table** (the one above)
2. **Smart agent decisions** with reasoning
3. **Action items** — what needs human review before proceeding
4. **Commands to run** — e.g., `gh pr merge 845`, `gh pr comment 844`

## Memory note

PR review results ARE persisted in two places:
- `swarm_runs/pr-decision-<timestamp>/` — raw engine responses
- `tools/swarm/session_manager.py` — SQLite session history

Re-running `/swarm pr-review` on the same PRs will show prior review
context. This means subsequent reviews can catch regressions against
prior findings. USE THIS to your advantage — the swarm gets smarter
with each review cycle on the same codebase.
