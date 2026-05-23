---
description: Multi-agent audit of GitHub Actions. Find failures, stale workflows, missed optimizations. Catches what a single agent misses.
argument-hint: [--deep] [--fix]
---

User invoked `/swarm actions-audit $ARGUMENTS`.

## Why swarm > single agent for Actions audit

A single agent tends to look at Actions from ONE angle:
- "Are they passing or failing?" (surface-level)
- "What's the YAML look like?" (code-level only)

A swarm of 3 specialists each sees DIFFERENT optimization opportunities:

| Specialist       | What they catch                                                  |
|------------------|------------------------------------------------------------------|
| Mercury (DevOps) | Workflow structure, caching, parallel jobs, conditional steps     |
| Grok (Cost)      | Run time, compute waste, runner tier optimization, billing leaks |
| Claude (Quality) | Missing tests, stale fixtures, coverage gaps, security scans     |

A single agent would miss at least one of these dimensions.

## Pipeline

### Step 1: Gather raw data

Run these commands in parallel:

```bash
# Recent workflow runs (last 20)
gh run list --limit 20 --json name,status,conclusion,createdAt,updatedAt,databaseId,workflowName,event,headBranch

# All workflows
gh api repos/{owner}/{repo}/actions/workflows --jq '.workflows[] | {id, name, state, path, updated_at}'

# Failed runs (last 30 days)
gh run list --status failure --limit 50 --json name,conclusion,createdAt,databaseId,headBranch

# Workflow files
find .github/workflows -name "*.yml" -o -name "*.yaml" | head -20
```

### Step 2: Deploy 3 specialist agents

**Agent 1 — Mercury (DevOps/Structure):**
```
Context: "You are Mercury-v1, a DevOps specialist reviewing GitHub Actions.

Analyze these workflow files and recent run data for:
1. Workflows that haven't run in 30+ days (stale)
2. Workflows with high failure rates (>20%)
3. Missing caching (actions/cache for node_modules, pip, etc)
4. Sequential jobs that could be parallelized
5. Missing conditional execution (skip on docs-only changes, etc)
6. Unnecessary full checkout depths
7. Redundant workflow triggers

Workspace: /mnt/c/findtorontoevents_antigravity.ca/
Read workflow files from: .github/workflows/

Output JSON only:
{
  'specialist': 'mercury',
  'stale_workflows': [{'file': 'path', 'last_run': 'date', 'days_stale': N}],
  'failure_rates': [{'workflow': 'name', 'fail_rate': 0.XX, 'last_10_runs': 'pass/fail pattern'}],
  'optimizations': [
    {'type': 'caching|parallelization|conditional|runner|depth', 'file': 'path', 'impact': 'high|medium|low', 'change': 'specific suggestion'}
  ]
}"

Goal: "Audit GitHub Actions for structural optimizations and stale workflows"
Role: leaf
Toolsets: ["terminal", "file"]
```

**Agent 2 — Grok (Cost/Performance):**
```
Same structure, focus on:
1. Estimated run time per workflow (from updatedAt - createdAt)
2. Workflows using ubuntu-latest when smaller runners would suffice
3. Dependency install patterns (npm ci vs npm install, --frozen-lockfile)
4. Matrix strategy waste (testing on too many OS/node versions)
5. Repeated expensive steps across workflows
6. Missing artifact caching causing redundant downloads
7. Scheduled workflows that run too frequently

Output: cost/optimization focused JSON
```

**Agent 3 — Claude (Quality/Security):**
```
Same structure, focus on:
1. Missing security scans (CodeQL, Dependabot, Snyk, etc)
2. Workflows without proper permission scoping
3. Missing test coverage in CI
4. Stale test fixtures or snapshot tests that never update
5. Missing linting/formatting checks
6. Deploy workflows without proper approval gates
7. Secrets handling issues (exposed in logs, missing masks)

Output: quality/security focused JSON
```

### Step 3: Synthesize findings

After all 3 specialists report, build an ACTIONS AUDIT REPORT:

```
GITHUB ACTIONS AUDIT REPORT
═══════════════════════════

OVERVIEW
  Total workflows: N
  Active (last 30 days): N
  Stale (30+ days): N
  Failure rate >20%: N

TOP 5 QUICK WINS (by impact)
  1. [optimization] — estimated saving: X min/run or $X/month
  2. [optimization]
  ...

STALE WORKFLOWS (not run in 30+ days)
  - [workflow]: last run [date]. Consider: remove, fix trigger, or archive

HIGH-FAILURE WORKFLOWS
  - [workflow]: 40% failure rate (4/10). Root cause: [analysis]

SECURITY GAPS
  - Missing: [scan type]
  - Issue: [specific problem]

STRUCTURAL OPTIMIZATIONS
  - [file]: [specific change with expected impact]

CONSENSUS (what 2+ specialists agreed on):
  - [finding 1] (Mercury + Grok agreed)
  - [finding 2] (all 3 agreed)
```

### Step 4: If `--fix` flag

For each consensus finding, generate the actual YAML diff:

```bash
# Show proposed changes
gh pr diff <workflow-file>

# Apply fixes (create a branch)
git checkout -b chore/actions-audit-$(date +%Y%m%d)
# Apply changes...
git commit -m "chore(actions): apply swarm audit optimizations"
```

Always show the diff before applying. Never auto-push.

## Memory note

Actions audit results ARE persisted:
- `swarm_runs/actions-audit-<timestamp>/` — raw specialist reports
- `tools/swarm/session_manager.py` — session history

Subsequent audits can compare against prior findings to track:
- Which optimizations were implemented
- Whether failure rates improved
- New issues that appeared since last audit

This is where the swarm's persistent memory becomes valuable —
it can say "Last audit found X, you fixed it, now we see Y improved
but Z got worse." A single agent can't do that.
