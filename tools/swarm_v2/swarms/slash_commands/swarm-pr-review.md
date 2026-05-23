# /swarm-pr-review

Multi-agent PR review with impact analysis and risk assessment.

## Usage
```
/swarm-pr-review <repo> [--pr N] [--all-open]
```

## Pipeline
1. **Fetch** — PR title, description, diff, files changed
2. **Impact Analysis** — Blast radius, breaking changes, dependency graph
3. **Code Review** — Quality, security, patterns, test coverage
4. **Risk Assessment** — Rollback complexity, deployment risk
5. **Aggregate** — Weighted scores → approve/reject recommendation

## Parameters
- `--pr N` — Specific PR number
- `--all-open` — Review all open PRs

## Output
- Impact score (0-100)
- Risk level (low/medium/high/critical)
- Affected files and modules
- Breaking changes list
- Recommendations
- Approved: true/false
