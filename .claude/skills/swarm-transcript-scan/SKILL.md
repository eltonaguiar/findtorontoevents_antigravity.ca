---
name: swarm-transcript-scan
description: Scan a long Claude Code session transcript for action items / TODOs the session may have dropped. Use when the user says "/swarm-transcript-scan", "scan the transcript", "did I miss any action items", "find missed TODOs in this chat", or wants a long chat audited for unfinished work. Wraps tools/swarm/transcript_action_scan.py.
---

# /swarm-transcript-scan — missed-action-item auditor for long chats

A Claude Code session in this repo routinely produces 4–12 MB JSONL
transcripts — far past any LLM context window — so a request the user made
mid-session can be silently dropped. This skill chunks a transcript and runs
each chunk through the swarm LLM to enumerate every action item + a
`DONE / OPEN / UNCLEAR` status.

Tool: `tools/swarm/transcript_action_scan.py` (built 2026-05-17, PR #1141).

## Steps

1. **Pick the transcript.** If the user gave a path, use it. Otherwise default
   to the most recent session JSONL:
   ```bash
   ls -t "$HOME/.claude/projects/"*/*.jsonl 2>/dev/null | head -5
   ```
   On Windows the projects dir is
   `C:/Users/<user>/.claude/projects/<project-slug>/`. The largest, most
   recently-modified `.jsonl` is usually the live session. List sizes so the
   user can confirm which one (`wc -c` / `wc -l`).

2. **Run the scanner FROM THE REPO ROOT** (it resolves `ROOT` via
   `Path(__file__).parents[2]` — running a copy from elsewhere breaks the
   `swarms` import):
   ```bash
   python tools/swarm/transcript_action_scan.py <transcript.jsonl> \
       --out reports/transcript_scan_<id>.md
   ```
   Optional flags: `--chunk-chars N` (default 6000; keep ≤7000 for the
   keyless LLM7 fallback's ~8000-char cap), `--provider <name>` (force a
   specific swarm provider; default auto-detect).

3. **Report.** Show the `## OPEN (...)` section of the generated report and
   the chunk/turn/provider counts. State the caveats explicitly (below) so
   OPEN items are not actioned blindly.

## What the tool does

- Parses the JSONL into clean user/assistant text turns — `tool_use`,
  `tool_result`, and harness `system-reminder` blocks are discarded (~90% of
  bytes, 0% of intent).
- Char-budget chunks the turns.
- Per chunk, an LLM lists every action item with `DONE / OPEN / UNCLEAR`.
- Aggregates + de-dupes; `DONE` in any later chunk wins over an earlier `OPEN`.
- Backend = `tools/swarm_v2` `LLMClient` — auto-detects a keyed provider,
  falls back to the keyless LLM7.io provider, so it runs zero-config.

## Caveats — do NOT action OPEN items blindly

- **Status is chunk-local.** An item OPEN early and DONE late only reconciles
  if both chunks phrase it identically. Expect false-OPEN inflation.
- **Single-transcript blind.** Open in session A, done in session B → shows
  OPEN. Cross-check against `git log`, merged PRs, and the live TodoWrite
  before treating an OPEN item as real.
- Dedup is lexical, so the OPEN count is an upper bound.

Treat the OPEN list as *leads to verify*, not a to-do list to execute.

## Improvement backlog (v2)

Add a second "reconcile" pass: feed all per-chunk extracted items (now small
enough for one context) to one LLM call for semantic dedup + latest-mention-
wins status. Tag each item with its chunk index for recency ranking.
