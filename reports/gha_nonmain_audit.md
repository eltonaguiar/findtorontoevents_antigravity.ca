# Non-main branch run audit

- Runs scanned: **1200** (2026-11-15T20:36:09Z → 2026-11-16T03:47:32Z)
- Non-main runs: **54** (4.5%)
- Events: `{'pull_request': 33, 'push': 14, 'dynamic': 7}`
- Conclusions: `{'success': 40, 'None': 1, 'cancelled': 11, 'failure': 2}`
- Duplicate groups (same workflow+commit run >1x): **0**, extra runs **0**, wasted **0 min**

## Non-main workflows

| workflow | runs | conclusions | feed |
|---|---|---|---|
| `branch-large-file-dup-guard.yml` | 9 | `Counter({'cancelled': 8, 'None': 1})` | artifact |
| `no-stale-db-passwords.yml` | 8 | `Counter({'success': 7, 'cancelled': 1})` | PR gate |
| `db-password-leak-guard.yml` | 8 | `Counter({'success': 8})` | PR gate |
| `conflict-marker-check.yml` | 8 | `Counter({'success': 7, 'cancelled': 1})` | PR gate |
| `masking-policy-lint.yml` | 7 | `Counter({'success': 7})` | PR gate |
| `pages-build-deployment` | 7 | `Counter({'success': 7})` | built-in/no local file |
| `secret-scan.yml` | 2 | `Counter({'success': 2})` | built-in/no local file |
| `audit-drift-telemetry.yml` | 2 | `Counter({'success': 2})` | artifact |
| `mysql-q001-sync.yml` | 1 | `Counter({'failure': 1})` | built-in/no local file |
| `ml-gatekeeper-ab-bootstrap.yml` | 1 | `Counter({'failure': 1})` | built-in/no local file |
| `audit-frontend-manifest.yml` | 1 | `Counter({'cancelled': 1})` | — |

## Branches by verdict

| verdict | count |
|---|---|
| unmerged_work | 199 |
| merged_or_identical | 13 |
| unknown | 1 |
