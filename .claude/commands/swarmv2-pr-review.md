---
description: Enhanced multi-agent PR review (impact analysis + code review + risk assessment).
---

Run the v2 PR-review swarm. From `tools/swarm_v2`:

```
python -m swarms.cli.main pr-review <repo> [--pr N] [--all-open]
```

Pipeline: fetch PR -> impact analysis (blast radius, breaking changes) -> code review -> risk assessment -> aggregate to approve/reject.
Output: impact score 0-100, risk level, affected modules, breaking-changes list, recommendation.

Distinct from `/swarm-pr-review` (the original `tools/swarm` engine) — this is the v2 `tools/swarm_v2` engine.
