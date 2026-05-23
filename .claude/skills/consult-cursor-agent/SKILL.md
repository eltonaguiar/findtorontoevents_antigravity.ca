---
name: consult-cursor-agent
description: Get a second opinion from Cursor Agent via its headless CLI (the `agent` command). Use when the user says "/consult-cursor-agent", "ask cursor-agent", "cursor-agent second opinion", or wants an outside model's take on a question, plan, or code.
---
# consult-cursor-agent
Query Cursor Agent for a second opinion, non-interactively.
## When to use
User asks "ask cursor-agent" / "/consult-cursor-agent" / second opinion from Cursor Agent.
## The one command that works
`powershell -NoProfile -Command 'Set-Location $env:TEMP; agent -p "PROMPT" --output-format json --trust --yolo'`

Output is one JSON object; the answer is the **`.result`** field
(`{"type":"result","subtype":"success","result":"...","usage":{...}}`).
Verified working 2026-05-17.
## Why each flag is mandatory
| Flag | Purpose |
|------|---------|
| `Set-Location $env:TEMP` (via PowerShell) | Runs the CLI from a clean temp directory outside any repository — prevents `agent` discovering repo-local `.cursor/` rules / config that pollute the opinion or break headless mode. |
| `-p "PROMPT"` | Non-interactive print mode (also `--print`). Without it the CLI starts an interactive session. |
| `--output-format json` | Returns one machine-readable JSON object instead of TTY/streaming text. |
| `--trust` | Grants headless tool access so the agent runs without interactive trust prompts. |
| `--yolo` (or `--force`) | Auto-approves edits and commands. Without it the headless run blocks waiting for confirmation. |
## Verify alive
`powershell -NoProfile -Command 'Set-Location $env:TEMP; agent -p "reply with exactly: PONG" --output-format json --trust --yolo'`
## Known issues
- **Repo CWD pollution** — starting inside a git repo loads `.cursor/` project settings/tools. `Set-Location $env:TEMP` is mandatory for an uncontaminated opinion.
- **Authentication required** — if the command returns an auth/permission error, the Cursor Agent CLI was never logged in. Run `agent` interactively once to complete login; subsequent headless calls succeed.
- The command is `agent` (also installed as `cursor-agent`).
