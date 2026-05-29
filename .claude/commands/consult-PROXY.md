---
description: Fan a prompt to N AIs through the local LiteLLM proxy (:4000) via freellm.py — team (CombineTeam), debate (DebateTeam), or per-file (FileTeam) swarm. Outputs .MD files. Use for "/consult-PROXY", "proxy swarm", "debate via proxy", "ask the proxy team".
---

Invoke the `consult-PROXY` skill. Read `.claude/skills/consult-PROXY/SKILL.md` and follow it.

Arguments after the command select the mode:
- `team   "<question>"`  → CombineTeam: ask N AIs the same question (default)
- `debate "<topic>"`     → DebateTeam: multi-round structured debate
- `file   "<prompt>" <paths...>` → FileTeam: divide files across AIs
- bare prompt with no mode word → defaults to `team`.

Before fanning out: confirm the proxy is up (`curl -s -m3 http://localhost:4000/health/liveliness`); if down, tell the user to run `/startvllmp`. For any prompt about asset-class / pick performance, you MUST pull the numbers locally and embed them verbatim (proxy models have no browser access — never let them claim to fetch findtorontoevents.ca).
