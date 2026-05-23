---
description: Audit a swarm run dir — per-engine response sizes + suspect flags. Defaults to latest.
argument-hint: [run_dir]
---

Run:
```
python tools/swarm/swarm_inspect.py $ARGUMENTS
```

If `$ARGUMENTS` is empty, use `--latest`.

Show the inspector's table verbatim. Do not summarize. The user wants to see exact byte counts per engine so they can spot dummy/empty/credit-exhausted responses at a glance.

If suspect count > 0, list the suspect engines + which raw files to read for diagnosis (the inspector already does this — just preserve the output).
