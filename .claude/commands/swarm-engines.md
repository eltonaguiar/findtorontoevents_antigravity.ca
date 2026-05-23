---
description: List supported swarm engine names + auth status.
---

Run:
```
python tools/swarm/swarm_run.py --list-engines
python tools/swarm/config_loader.py
```

The first output is the supported-engine list. The second shows which API keys are wired (OK = key present, MISS = missing). Together they tell the user which engines are usable right now.
