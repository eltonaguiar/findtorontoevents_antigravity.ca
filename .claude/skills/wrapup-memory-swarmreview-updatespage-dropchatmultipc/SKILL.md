---
name: wrapup-memory-swarmreview-updatespage-dropchatmultipc
description: End-of-session super-wrap. Use when the user says "/wrapup_memory_swarmreview_updatespage_dropchatmultipc", "/wrapup", "wrap up the chat", "finish and hand off", or wants the full close-out sequence — transcript-review → commit everything → save summary to agentmemory + holographic memory → drop a findtorontoevents.ca/updates card → /dropchat-multipc. Aliases — wrapup, session-wrap, handoff-wrap.
---

# wrapup — full session close-out + cross-PC handoff

One command that runs the complete end-of-session wrap so nothing is dropped,
all work is durable, and peers + future sessions inherit a clean handoff.

## Operating frame (run this FIRST)

Before wrapping, make sure work is actually finished. Set a goal and proceed:

> Set a goal and proceed; continue until all tasks and follow-up tasks are
> completed — authorized to continue autonomously until everything is handled.
> Only when genuinely done, run the wrap sequence below.

Use the `goal` skill for the standing objective. Use subagents for independent
work; if a task is unclear, consult the agent swarm (`tools/swarm/swarm_run.py`)
or `/consult-grok`. "Genuinely done" = every actionable item is done or is
honestly blocked on a named external precondition (time-gated CI, operator
decision, paid data). A time-gated wait is not a dropped task — name it and move
to wrap.

## The wrap sequence — 5 steps, in order

### Step 1 — Transcript review (catch dropped items)
Invoke the `swarm-transcript-review` skill (alias of `swarm-transcript-scan`):
chunk the session JSONL, enumerate every action item DONE/OPEN/UNCLEAR.
Cross-check each `OPEN` against `git log` + the live work — expect false-OPEN
inflation. Execute any genuinely-open + actionable item now; for each item that
is NOT actionable, state why (done already / time-gated / operator-gated).

### Step 2 — Commit everything to GitHub main
Every report, tool, skill, registry change, doc produced this session must be on
`origin/main` so other PCs can pull it. This repo is drift-heavy — commit via
the GitHub contents/blob API against `origin/main`, NOT local git. For peer-hot
files use fetch-origin-patch (fetch origin content, re-apply the change, commit)
— never push a wholesale drift-stale local file. **Censor check before every
commit:** no DB passwords, no PATs (`ghp_*`/`github_pat_*`), no FTP passwords —
creds must be env-var-only. Verify a sample of deliverables landed on `main`.

### Step 3 — Save the summary to BOTH memory systems
Build a tight summary: **achievements**, **findings**, **remaining action items**
(each tagged done / time-gated / operator-gated).
- **agentmemory** (`http://localhost:3111`) — `POST /agentmemory/remember` one
  fact per durable finding, with `metadata` tags. Start the server first if
  down (see the `agentmemory` skill).
- **holographic memory** (`agent_shared_memory.json`) — append to `decisions`
  (1 entry: the session verdict) + `learnings` (per non-obvious lesson); bump
  `_meta.last_updated` / `updated_by`; commit the file to `main`.
- Also update the personal `MEMORY.md` auto-memory if a project-state fact
  changed — update the existing memory file, do not duplicate.

### Step 4 — Drop an update card on findtorontoevents.ca/updates
Add one `<div class="update-entry">` card to `updates/index.html` (it is ~3.4MB
— edit via the git BLOB API: blob → tree → commit → patch ref; capture
subprocess output as BYTES, decode utf-8 errors='replace' — Windows cp1252
crashes on the big file). The card states the session's honest outcome in
plain language for the public page. Then FTP-deploy `updates/index.html` to
50webs (`/findtorontoevents.ca/updates/index.html`, creds in env vars
`FTP_SERVER`/`FTP_USER`/`FTP_PASS`) so the live site reflects it.

### Step 5 — /dropchat-multipc
Invoke the `dropchat-multipc` skill: build the `session-summary/v1` payload from
this session's real commits/PRs/files/decisions, broadcast `SESSION_SUMMARY` to
`all` via the gateway (`192.168.2.32:8788`, `--runtime claude`), verify the send
landed (`protocol_inspect tail`), drain the DM + broadcast inboxes, triage any
peer messages. Log to `CHATBIBLE_FAILURE.MD` if the bus is unreachable.

## Output to operator

A compact close-out: transcript-scan OPEN count + what was handled; commit count
+ verify-sample result; agentmemory facts stored + holographic entries added;
updates card + FTP-deploy status; dropchat broadcast id + inbox counts; and the
honest remaining-items list (done / time-gated / operator-gated).

## Anti-patterns

- Do NOT skip Step 1 — wrapping without the transcript scan is how mid-session
  asks get silently dropped.
- Do NOT commit drift-stale local copies of peer-hot files — fetch-origin-patch.
- Do NOT echo any secret in a commit or in chat.
- Do NOT mark a time-gated wait as "done" — name the precondition.
- Do NOT fabricate a summary — gather commits/PRs/files from real `git`/`gh`.

## Companion skills
`swarm-transcript-review`, `dropchat-multipc`, `agentmemory`,
`holographic-memory`, `goal`.
