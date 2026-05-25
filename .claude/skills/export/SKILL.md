# export — Export Chat Transcript to Markdown

**Invocation:** `/export [path] [--summary]`

## What it does

Creates a clean, well-structured `.md` file containing an export of the current conversation/session.

This is useful for:
- Creating durable session records (as used in the ongoing goal work)
- Handing off context to other agents or future sessions
- Archiving important design discussions, code reviews, or decision logs
- Feeding into other tools (e.g., `swarm-transcript-review`)

## Usage

```bash
/export                              # Default: transcripts/session-YYYY-MM-DD-HHMM.md
/export my-notes.md                  # Custom relative path
/export reports/2026-05-25-export.md # Specific location
/export --summary                    # Shorter version (decisions + artifacts only)
/export --full                       # Explicit full version (default)
```

## Behavior

When invoked, you (the AI) should:

1. Generate a high-quality markdown document of the **current session**.
2. Use the `write` tool (or terminal `cat > file`) to actually create the file.
3. Create the `transcripts/` directory automatically if it doesn't exist and no path is provided.
4. Make the export useful and self-contained.

### Recommended Export Structure (Full)

```markdown
# Session Export — [Date/Time]

**Session ID / Context:** ...
**Participants:** Human + Grok 4.3
**Goal / Focus:** ...

## Summary
(2-4 paragraph overview of what was accomplished)

## Key Decisions
- ...

## Artifacts Created / Modified
- `path/to/file.md` — description
- ...

## Important Outputs / Findings
...

## Open Questions / Next Steps
- ...

## Raw Transcript Notes (optional, if useful)
...
```

### Recommended Export Structure (Summary)

Use when `--summary` is passed:
- Focus only on decisions, files changed, and concrete outcomes.
- Much shorter.

## Implementation Notes

- The export should be **human-readable and useful** — not a raw dump of every token.
- Prioritize clarity, structure, and actionability.
- When the user has been working on a long-running goal or complex task (e.g., multi-round swarm reviews), the export should capture the state of that work.
- You have access to the `write` tool and can create directories as needed.
- If the user provides a path, respect it exactly (create parent dirs if necessary).
- Default location: `transcripts/session-YYYY-MM-DD-HHMM.md` (use current UTC time).

## Examples of Good Use

- End of a long design session
- After completing a multi-round swarm review (as in recent usage)
- Before handing off to another agent or machine
- When the user wants a durable record of decisions

## Related Skills

- `wrapup-memory-swarmreview-updatespage-dropchatmultipc` — heavier end-of-session wrap
- `dropchat-multipc` — cross-PC handoff
- `swarm-transcript-review` / `swarm-transcript-scan` — for analyzing transcripts

---

**This skill is intentionally lightweight and on-demand.** It complements (but does not replace) the more automated wrap-up flows.