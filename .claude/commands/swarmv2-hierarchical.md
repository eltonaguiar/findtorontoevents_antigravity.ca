---
description: Enhanced hierarchical swarm (Strategic -> Tactical -> Execution layers).
---

Run the v2 hierarchical swarm. From `tools/swarm_v2`:

```
python -m swarms.cli.main hierarchical "<task>" [--strategists 2] [--tacticians 3]
```

Pipeline: strategic macro signals -> tactical asset-specific predictions (conditioned) -> execution validation + sizing -> risk-controller veto.
Output: per-layer signals, final execution plan, risk assessment.
