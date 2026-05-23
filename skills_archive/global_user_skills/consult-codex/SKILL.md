---
name: consult-codex
description: Get a second opinion from OpenAI Codex via its headless CLI. Use when the user says "/consult-codex", "ask codex", "codex second opinion", or wants an outside model's take on a question, plan, or code.
---
# consult-codex
Query OpenAI Codex for a second opinion, non-interactively.
## When to use
User asks "ask codex" / "/consult-codex" / second opinion from Codex.
## The one command that works
`powershell -NoProfile -Command 'Set-Location $env:TEMP; codex exec --yolo --json "PROMPT"'`

Output is an NDJSON event stream (one JSON object per line). The final assistant
response is in the last event; the answer text is in its `text` field (or the
primary content property of the final record).
## Why each flag is mandatory
| Flag | Purpose |
|------|---------|
| `Set-Location $env:TEMP` (via PowerShell) | Runs the CLI from a clean temp directory outside any repository — prevents Codex discovering repo-local config / rules / MCP servers that pollute the opinion or break headless mode. |
| `exec` | One-shot non-interactive subcommand (alias `codex e`). Without it options forward to the interactive CLI. |
| `--yolo` (or `--ask-for-approval never`) | Auto-approves all actions. Without it the CLI prompts on first tool use and hangs. |
| `--json` | Emits NDJSON instead of human-readable output so the caller can parse the event stream reliably. |
## Verify alive
`powershell -NoProfile -Command 'Set-Location $env:TEMP; codex exec --yolo --json "reply with exactly: PONG"'`
## Known issues
- **Repo CWD pollution** — starting inside a git repo loads project settings/tools. `Set-Location $env:TEMP` is mandatory for an uncontaminated opinion.
- **Authentication required** — if the command returns an auth/permission error or empty output, the CLI was never logged in. Run `codex` interactively once to complete login / API-key setup; subsequent headless calls succeed.
