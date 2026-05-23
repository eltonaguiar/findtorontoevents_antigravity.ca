---
description: Resume one engine from a saved session id with a follow-up prompt.
argument-hint: <engine> <session-id> <prompt-file>
---

Parse `$ARGUMENTS` as `<engine> <session-id> <prompt-file>`. If any missing, fail with usage and run `/swarm sessions list` so the user can pick a session.

Build out-file path: `swarm_runs/_resume/<engine>_<UTC-timestamp>.json`.

Run:
```
python tools/swarm/worker_runner.py \
    --engine <engine> \
    --prompt-file <prompt-file> \
    --out-file <out-file> \
    --from-session <session-id> \
    --persist-session
```

Show:
- The worker's stdout (final out-file path).
- File size of the .raw.txt (response bytes).
- First 500 chars of the response.
- Any suspect flags via `python tools/swarm/swarm_inspect.py <out-file's parent dir>`.

The user uses this to chain N turns on the same engine without re-paying the full prompt cache cost.
