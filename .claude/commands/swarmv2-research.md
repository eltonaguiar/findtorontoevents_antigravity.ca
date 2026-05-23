---
description: Enhanced multi-agent deep research swarm with epistemic triangulation.
---

Run the v2 research swarm. From `tools/swarm_v2`:

```
python -m swarms.cli.main research "<topic>" [--depth 3-5] [--route A|B|C|D]
```

Pipeline: decompose topic -> 3-5 parallel researchers -> cross-verify -> resolve contradictions -> synthesize.
Routes: A=wide, B=focused, C=file-only, D=file-augmented.
Output: findings with confidence scores, consensus claims, disputed claims, knowledge gaps, sources. Stored in swarm memory.
