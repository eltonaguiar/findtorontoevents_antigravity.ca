---
description: Enhanced multi-agent coding swarm (generate -> test -> review -> revise -> verify).
---

Run the v2 coding swarm. From `tools/swarm_v2`:

```
python -m swarms.cli.main coding <task-file> [--agents 3] [--strict]
```

Pipeline: decompose -> parallel generate -> mandatory tests -> review -> revise (<=3) -> verify.
Parameters: `--agents N` parallel generators, `--strict` enforces 90%+ coverage, `--models` comma list.
Output: code artifacts + tests + review comments, stored in swarm memory for future search.

Apply the winning diff yourself or hand it to a `cavecrew-builder` subagent — the swarm writes JSON artifacts, it does not auto-commit.
