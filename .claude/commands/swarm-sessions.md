---
description: Inspect sqlite session sidecar (list active, show by id, expire old).
argument-hint: [list|show <id>|expire]
---

Parse `$ARGUMENTS`:
- empty or `list` → `python tools/swarm/session_manager.py list`
- `show <id>` → `python tools/swarm/session_manager.py show <id>`
- `expire` → `python tools/swarm/session_manager.py expire`

Print output verbatim. The session_id values shown can be passed to `/swarm resume` or `--from-session` flags on `worker_runner.py` / `swarm_run.py`.
