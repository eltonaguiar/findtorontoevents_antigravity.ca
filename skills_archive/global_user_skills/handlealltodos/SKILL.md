---
name: handlealltodos
description: Autonomously work through every outstanding TODO / action item in the session until done, then sweep the conversation for anything missed. Use when the user says "/handlealltodos", "handle all todos", "finish the backlog", "clear all action items". Wraps the /goal loop with a chat-sweep + escalate-to-AI rule.
---

# handlealltodos

Standing objective: handle ALL outstanding action items, then sweep the
conversation for anything missed, escalating to external AIs when unsure.

## When invoked

1. **Assemble the action-item list.** Gather from:
   - the current `TodoWrite` list,
   - the conversation — any user ask not yet finished,
   - open items in `reports/` / `docs/` produced this session,
   - `TODO` / `FIXME` / "next steps" the session surfaced.
   Write the consolidated list into `TodoWrite`.

2. **Invoke the `goal` skill** (via the `Skill` tool, skill name `goal`) with an
   objective of this shape:
   > "Handle every outstanding action item: <enumerated list>. After each item,
   > re-scan the chat for remaining work. If a step is unclear or a decision is
   > ambiguous, get a second/third opinion before proceeding. Stop only when all
   > items are done + verified, or a real blocker needs the user."

3. **Work the /goal loop.** Each turn = real edits / commands / commits, then
   tick + judge, auto-continue until done.

## Rules

- A turn must produce **real progress**, not a status narration. The judge
  evaluates work.
- **Verify before `done`** — tests pass, `py_compile` clean, file written,
  command output confirmed. "Probably fine" is `done=false`.
- Respect repo safety (CLAUDE.md): branch before committing, `py_compile` not
  live generators, never stomp peer work, pull before push.
- **Irreversible / outward-facing actions** (deploy, force-push, delete, send) —
  confirm with the user first; do not guess.
- If the repo is in heavy peer storm-commit churn, work in an isolated git
  worktree.

## Escalation ladder — when a step is unclear

Do NOT guess. Climb the ladder:

1. `/swarm-second-opinion` — 3-engine consensus (deepseek + xai + kilo).
2. `/consult-grok`, `/consult-gemini`, `/consult-codex`, `/consult-cursor-agent`,
   `/consult-opencode`, `/consult-kilo` — single-model opinions; ask 2-3 and
   compare.
3. Still unclear, or the decision is irreversible → **ask the user**.

Record which opinion was used and why in the relevant report/commit.

## Done condition

All assembled action items are completed AND verified, and a final chat re-scan
surfaces nothing new. Then report the closed list with evidence per item.
