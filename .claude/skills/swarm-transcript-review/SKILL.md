---
name: swarm-transcript-review
description: Alias for swarm-transcript-scan — audits a long chat transcript for missed/unfinished action items. Use when the user types /swarm-transcript-review or /swarm-transcript-scan.
---

# /swarm-transcript-review — alias of /swarm-transcript-scan

This is a thin alias. The canonical skill is **`swarm-transcript-scan`** —
both names do the same thing: chunk a session JSONL transcript and run each
chunk through the swarm LLM to enumerate every action item with a
`DONE / OPEN / UNCLEAR` status, so a request made mid-session is not silently
dropped.

## What to do

Invoke the `swarm-transcript-scan` skill and follow its steps exactly. In
short:

1. Pick the transcript — if the user gave a path use it, else default to the
   most recent session JSONL:
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

Full documentation lives in `.claude/skills/swarm-transcript-scan/SKILL.md`.
