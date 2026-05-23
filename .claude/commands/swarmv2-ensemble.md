---
description: Enhanced ensemble-voting swarm for predictions and decisions.
---

Run the v2 ensemble swarm. From `tools/swarm_v2`:

```
python -m swarms.cli.main ensemble "<task>" [--agents 5] [--confidence-threshold 0.8]
```

Pipeline: register N agents -> parallel predict with confidence -> weighted aggregate (majority / average+CI / distribution blend) -> expand if CI too wide.
Output: aggregated prediction, confidence interval, individual votes, dissenting opinions.
