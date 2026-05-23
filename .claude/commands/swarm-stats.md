---
description: Per-engine historical call stats from swarm_runs/_calls.jsonl.
---

Run:
```
python tools/swarm/swarm_stats.py
```

Show the table verbatim. Highlight any engine flagged ZOMBIE_OUTPUT / LOW_OK_RATE / ERRORING / UNUSED.

The user is looking at this to decide which engines to trust on the next swarm run.
