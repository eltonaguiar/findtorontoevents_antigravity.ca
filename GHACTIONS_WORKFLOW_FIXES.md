# GHACTIONS WORKFLOW FIXES

## Summary
- Total workflows: 357
- No permissions: 50
- git push: 31
- git push without contents: write: 1 (sports-smoke-and-e2e.yml)
- No timeout-minutes: 0
- No concurrency: 2 (_dynamic-runner-template.yml, gha-scan-job.yml)
- Scheduled: 310
- workflow_dispatch: 350
- Old action refs: 0
- Unpinned uses: 0

## Findings
All 357 YAML files parse cleanly. Zero old-action refs (checkout/setup-python/cache/upload-artifact all >=v4); zero unpinned uses.

### Push-without-permission file
- sports-smoke-and-e2e.yml — lacks contents: write permission despite using git push.

### No-permissions files (50)
See /tmp/wf_find.json for exact list.

### No concurrency (2)
- _dynamic-runner-template.yml
- gha-scan-job.yml

## Blocked items
- proof_protocol wiring (#18): BLOCKED — no runner exists.

## Reproducibility
Commands used:
- ls .github/workflows/*.yml | wc -l → 357
- grep -rl 'git push' .github/workflows/*.yml → 31 files
- python3 YAML parse + permission audit → 50 no-perms, 1 push-without-perm, 2 no-concurrency, 0 old refs, 0 unpinned
EOF