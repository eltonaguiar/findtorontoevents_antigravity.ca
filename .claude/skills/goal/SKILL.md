---
name: goal
description: Set a persistent standing objective that survives across turns and auto-continues until a judge confirms it is done. Use when the user says "/goal", "set a goal", "keep working until X", "work toward X autonomously", or wants Claude to self-continue toward an objective without re-prompting each turn. Subcommands - status, pause, resume, clear. Aliases - goal, standing-objective, autocontinue.
---

# /goal — Persistent standing objective

Port of the Hermes Agent `/goal` feature (https://hermes-agent.nousresearch.com/docs/user-guide/features/goals) to Claude Code. A goal is a standing objective that survives across turns. After each working turn a lightweight judge decides whether the goal is satisfied; if not, work auto-continues until done, paused, or the turn budget runs out.

## Subcommands

| Invocation | Action |
|---|---|
| `/goal <text>` | Set or replace the active goal, then immediately begin work |
| `/goal` or `/goal status` | Show current goal, state, and turns used |
| `/goal pause` | Halt auto-continuation without clearing the goal |
| `/goal resume` | Resume the loop; turn counter resets to 0 |
| `/goal clear` | Remove the goal entirely |

## State

State lives in `.claude/goal_state.json`, keyed by `goal:<session_id>` so concurrent Claude instances do not clobber each other. Manage it ONLY via the helper — never hand-edit the JSON:

```bash
python .claude/skills/goal/goal_state.py <action> --session <SID> [...]
```

Use a stable session id for `<SID>` — the Claude Code session id if available, else a short slug derived from the goal text. Reuse the SAME id for every call within one goal loop.

Goal record fields: `text`, `state`, `turns_used`, `max_turns` (default 20), `created_utc`, `updated_utc`, `last_reason`.

States: `active` → `paused` (user halt) → `achieved` (judge done) → `budget_exhausted` (turns_used ≥ max_turns).

## The loop

When invoked as `/goal <text>`:

1. **Set** the goal: `goal_state.py set --session <SID> --text "<text>" [--max-turns N]`.
2. **Work** one turn toward the goal — real tool calls, edits, commits. Not a status narration.
3. **Tick** the counter: `goal_state.py tick --session <SID>`.
4. **Judge** your own most-recent work against the goal text. Emit a strict verdict object — `{"done": <bool>, "reason": "<one sentence>"}` — then record it: `goal_state.py judge --session <SID> --done <bool> --reason "<reason>"`.
5. **Decide:**
   - `done=true` → stop. Report the goal achieved with the reason.
   - `done=false` and state is `budget_exhausted` → stop. Report `⏸ Goal paused — N/N turns used`; ask the user to `/goal resume` or refine.
   - `done=false` and budget remains → **auto-continue**: call `ScheduleWakeup` with `delaySeconds` matched to the work (60–270s if polling external state, 1200s+ if genuinely idle) and `prompt` set to `/goal continue` so the next firing re-enters this loop. Then continue working in the current turn if possible.

When invoked as `/goal continue` (the auto-continuation): skip step 1, re-read state with `status`, and resume from step 2. If state is `paused`, `achieved`, or `budget_exhausted`, do nothing and report why.

## The judge

The judge is a self-evaluation, kept honest by being structured. Inputs: the goal text + your recent work this turn. Output: exactly `{"done": <bool>, "reason": "<one-sentence rationale>"}`.

- `done=true` ONLY when the goal is genuinely, verifiably satisfied — verification run, tests green, file written, PR opened. "I think it's probably fine" is `done=false`.
- The `reason` names the concrete evidence (a command output, a file path, a test result), not a feeling.
- When unsure, `done=false` — a wasted continuation turn is cheaper than a falsely-closed goal.

## Quick reference

```bash
SID="my-goal-slug"
python .claude/skills/goal/goal_state.py set    --session "$SID" --text "Get CI green on main" --max-turns 20
python .claude/skills/goal/goal_state.py status --session "$SID"
python .claude/skills/goal/goal_state.py tick   --session "$SID"
python .claude/skills/goal/goal_state.py judge  --session "$SID" --done false --reason "2 jobs still failing"
python .claude/skills/goal/goal_state.py pause  --session "$SID"
python .claude/skills/goal/goal_state.py resume --session "$SID"
python .claude/skills/goal/goal_state.py clear  --session "$SID"
```

## Common mistakes

- **Narrating instead of working.** A turn must produce real progress (edits, commands, commits), not a description of intent. The judge evaluates work, not plans.
- **Optimistic judging.** Marking `done=true` without verification defeats the feature. Evidence before `done`.
- **Forgetting the wakeup.** If `done=false` and budget remains, you MUST schedule the continuation — otherwise the goal silently stalls until the user re-prompts.
- **Drifting session ids.** A new id mid-loop starts a fresh counter and orphans the old goal. Reuse one id.
- **Ignoring pause.** If state is `paused`, never auto-continue — the user halted it deliberately.
- **Infinite goals.** Goals that can never satisfy the judge ("keep improving forever") burn the whole budget. Phrase goals with a checkable done-condition.
