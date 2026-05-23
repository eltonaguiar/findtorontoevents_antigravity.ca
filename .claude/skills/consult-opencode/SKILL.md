---
name: consult-opencode
description: Get a second opinion from opencode via its headless CLI. Use when the user says "/consult-opencode", "ask opencode", "opencode second opinion", or wants an outside model's take on a question, plan, or code.
---
# consult-opencode
Query opencode for a second opinion, non-interactively.
## When to use
User asks "ask opencode" / "/consult-opencode" / second opinion from opencode.
## The one command that works
`powershell -NoProfile -Command 'Set-Location $env:TEMP; opencode run "PROMPT"'`

The model's reply is printed directly to stdout as plain text. The entire
trimmed stdout is the answer.
## Why each flag is mandatory
| Flag | Purpose |
|------|---------|
| `Set-Location $env:TEMP` (via PowerShell) | Runs the CLI from a clean temp directory outside any repository — prevents opencode discovering repo-local config / `AGENTS.md` / rules that pollute the opinion or break headless mode. |
| `run "PROMPT"` | One-shot headless execution: sends the message, receives the reply, prints to stdout, exits. |
## Verify alive
`powershell -NoProfile -Command 'Set-Location $env:TEMP; opencode run "reply with exactly: PONG"'`
## Known issues
- **Repo CWD pollution** — starting inside a git repo loads project config/tools. `Set-Location $env:TEMP` is mandatory for an uncontaminated opinion.
- **Authentication required** — if the command returns an auth/permission error, opencode has no model provider configured. Run `opencode` interactively once to set up a provider / API key; subsequent headless calls succeed.
- **May HANG with no output** — if no provider is configured, `opencode run` can block silently instead of erroring (observed 2026-05-17). Always run with a timeout (~120s); a timeout with empty output means the CLI needs interactive provider setup first. NOT yet verified working headless on this machine.
- For a cross-vendor opinion, opencode + DeepSeek Reasoner is a strong pairing.
