---
description: Enhanced swarm to detect failed/flaky/cancelled/stale GitHub Actions jobs.
---

Run the v2 GitHub Actions swarm. From `tools/swarm_v2`:

```
python -m swarms.cli.main actions <repo> [--since 30d] [--notify]
```

Detects: failed (consecutive fail, no later success), flaky (intermittent pass/fail), cancelled (frequently cancelled), stale (not run in > N days).
Output: per-category job lists, blast-radius assessment, actionable recommendations.
