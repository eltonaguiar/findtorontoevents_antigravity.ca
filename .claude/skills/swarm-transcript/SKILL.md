---
name: swarm-transcript
description: Alias for swarm-transcript-scan — chunks a long Claude Code session transcript and audits it for missed/unfinished action items. Use when the user types /swarm-transcript (with or without a -scan / -review / -summary suffix), "scan the transcript", "did I miss anything in this chat".
---

# /swarm-transcript — alias of /swarm-transcript-scan

Thin alias. The canonical skill is **`swarm-transcript-scan`**. The user has
typed this command as `/swarm-transcript`, `/swarm-transcript-scan`,
`/swarm-transcript-review`, and `/swarm-transcript -summary` — all of them
mean the same thing and all resolve here.

## What to do

Invoke the `swarm-transcript-scan` skill and follow its steps exactly. Short
form:

1. Pick the transcript — if the user gave a path use it, else the most
   recent session JSONL:
   ```bash
   ls -t "$HOME/.claude/projects/"*/*.jsonl 2>/dev/null | head -5
   ```
2. Run the scanner from the repo root:
   ```bash
   python tools/swarm/transcript_action_scan.py <transcript.jsonl> \
       --out reports/transcript_scan_<id>.md
   ```
3. Report the `## OPEN (...)` section + chunk/turn/provider counts.

## Caveats (same as swarm-transcript-scan)

- Status is chunk-local — expect false-OPEN inflation.
- Single-transcript blind — cross-check OPEN items against `git log`, merged
  PRs, and the live TodoWrite before treating any as real.
- The OPEN list is **leads to verify**, not a to-do list to execute.

Full documentation: `.claude/skills/swarm-transcript-scan/SKILL.md`.
Sibling alias: `.claude/skills/swarm-transcript-review/SKILL.md`.
